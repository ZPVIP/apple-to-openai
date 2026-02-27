"""
Apple Intelligence OpenAI-Compatible API Server

Exposes Apple's on-device Foundation Model via an OpenAI-compatible
chat completions API, enabling integration with any client that speaks
the OpenAI protocol.
"""

import asyncio
import json
import time
import uuid
import hmac
from typing import List, Optional, Tuple

import apple_fm_sdk as fm
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Settings

# ---------------------------------------------------------------------------
# App & config initialization
# ---------------------------------------------------------------------------

settings = Settings()
app = FastAPI(title="Apple Intelligence OpenAI-Compatible API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_ID = "apple-intelligence"
MAX_PROMPT_CHARS = 10000  # ~2,000 tokens input, leaving ~2,000 tokens for output (4,096 total)

# Validate SDK is available (graceful degradation)
try:
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Warning: Foundation model not available: {reason}")
except Exception as e:
    is_available = False
    reason = str(e)
    print(f"Warning: Failed to initialize Foundation model: {e}")

# Concurrency tracking
concurrency_limiter = asyncio.Semaphore(settings.max_concurrency)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = MODEL_ID
    messages: List[Message]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_messages(messages: List[Message], max_chars: int = MAX_PROMPT_CHARS) -> List[Message]:
    """Keep system message(s) + as many recent messages as fit within *max_chars*."""
    system_msgs = [m for m in messages if m.role == "system"]
    non_system = [m for m in messages if m.role != "system"]

    budget = max_chars
    for m in system_msgs:
        budget -= len(m.content)

    kept: list[Message] = []
    for m in reversed(non_system):
        cost = len(f"{m.role}: {m.content}\n")
        if budget - cost < 0 and kept:
            break
        budget -= cost
        kept.append(m)
    kept.reverse()
    return system_msgs + kept


def build_prompt(messages: List[Message]) -> Tuple[Optional[str], str]:
    """
    Extract system instructions and build conversational prompt.
    Returns (instructions, conversational_prompt).
    """
    messages = truncate_messages(messages)
    
    system_parts = []
    conversational_parts = []

    for m in messages:
        if m.role == "system":
            if m.content:
                system_parts.append(m.content)
        elif m.role == "user":
            conversational_parts.append(f"User: {m.content}")
        elif m.role == "assistant":
            conversational_parts.append(f"Assistant: {m.content}")
        else:
            conversational_parts.append(f"{m.role}: {m.content}")

    instructions = "\n\n".join(system_parts) if system_parts else None
    
    prompt = (
        "You are answering the final user request in the following conversation.\n"
        "Return only the assistant response.\n\n" 
        + "\n".join(conversational_parts) 
        + "\nAssistant:"
    )

    return instructions, prompt


def _completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:12]}"


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunk(chunk_id: str, delta: dict, finish_reason: Optional[str] = None) -> dict:
    return {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }


def map_sdk_error(exc: Exception, prompt: str) -> JSONResponse:
    name = exc.__class__.__name__

    if name == "ExceededContextWindowSizeError":
        ascii_chars = sum(1 for c in prompt if ord(c) < 128)
        non_ascii_chars = len(prompt) - ascii_chars
        msg = (
            f"This model's maximum context length (4,096 tokens) has been exceeded. "
            f"Your prompt has {len(prompt)} characters "
            f"({ascii_chars} ASCII, {non_ascii_chars} non-ASCII)."
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": msg,
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": "context_length_exceeded",
                }
            },
        )
    elif name == "AssetsUnavailableError":
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": "Model assets unavailable. Ensure Apple Intelligence is downloaded.",
                    "type": "server_error",
                    "code": "assets_unavailable",
                }
            },
        )
    elif name == "RateLimitedError":
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": "Rate limited by Apple Foundation Model.",
                    "type": "rate_limit_error",
                    "code": "rate_limited",
                }
            },
        )
    elif name in ("GuardrailViolationError", "RefusalError"):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": str(exc),
                    "type": "invalid_request_error",
                    "code": "guardrail_violation",
                }
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": f"Apple Foundation Model error: {exc}",
                "type": "server_error",
                "code": "provider_error",
            }
        },
    )


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------


async def stream_response(session, prompt: str, instructions: Optional[str]):
    """Yield SSE chunks via real Apple Foundation Model streaming."""
    cid = _completion_id()
    created_at = int(time.time())

    # 1 — role announcement
    yield _sse(_chunk(cid, {"role": "assistant"}))

    # 2 — stream content
    try:
        async with concurrency_limiter:
            async with asyncio.timeout(settings.request_timeout):
                previous_text = ""
                # stream_response yields the accumulated string at each snapshot
                async for snapshot in session.stream_response(prompt):
                    snapshot_text = str(snapshot)
                    delta = snapshot_text.removeprefix(previous_text)
                    if not delta:
                        delta = snapshot_text
                    
                    previous_text = snapshot_text
                    
                    if delta:
                        yield _sse(_chunk(cid, {"content": delta}))
                        await asyncio.sleep(0.001)

    except TimeoutError:
        yield _sse({"error": {"message": "Request timed out", "type": "timeout_error"}})
        return
    except Exception as exc:
        err_res = map_sdk_error(exc, prompt)
        err_dict = json.loads(err_res.body.decode("utf-8"))
        yield _sse(err_dict)
        return

    # 3 — empty content
    yield _sse(_chunk(cid, {"content": ""}))

    # 4 — finish reason
    yield _sse(_chunk(cid, {}, finish_reason="stop"))

    # 5 — usage statistics
    prompt_tokens = estimate_tokens(instructions or "") + estimate_tokens(prompt)
    completion_tokens = estimate_tokens(previous_text)
    
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    
    yield _sse({
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created_at,
        "model": MODEL_ID,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "usage": usage
    })

    # 6 — done
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


async def verify_auth(authorization: Optional[str] = Header(default=None)):
    if not settings.api_key:
        return
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    if not is_available:
        return JSONResponse(status_code=503, content={"status": "unavailable", "reason": reason})
    return {"status": "ok"}


@app.post("/v1/chat/completions", dependencies=[Depends(verify_auth)])
async def chat_completions(req: ChatCompletionRequest):
    if not is_available:
        return JSONResponse(
            status_code=503, 
            content={"error": {"message": f"Model unavailable: {reason}", "type": "server_error"}}
        )

    instructions, prompt = build_prompt(req.messages)
    session = fm.LanguageModelSession(instructions=instructions)

    if req.stream:
        return StreamingResponse(
            stream_response(session, prompt, instructions),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    try:
        async with concurrency_limiter:
            async with asyncio.timeout(settings.request_timeout):
                response = await session.respond(prompt)
                completion_text = str(response)
    except TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"error": {"message": "Request timed out", "type": "timeout_error"}}
        )
    except Exception as exc:
        return map_sdk_error(exc, prompt)

    prompt_tokens = estimate_tokens(instructions or "") + estimate_tokens(prompt)
    completion_tokens = estimate_tokens(completion_text)

    return {
        "id": _completion_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": completion_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@app.get("/v1/models", dependencies=[Depends(verify_auth)])
async def list_models():
    if not is_available:
        return JSONResponse(
            status_code=503, 
            content={"error": {"message": f"Model unavailable: {reason}", "type": "server_error"}}
        )

    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": 0,
                "owned_by": "apple",
            }
        ],
    }


@app.get("/v1/models/{model_id}", dependencies=[Depends(verify_auth)])
async def retrieve_model(model_id: str):
    if model_id != MODEL_ID:
        raise HTTPException(status_code=404, detail="Model not found")

    if not is_available:
        raise HTTPException(status_code=503, detail=f"Model unavailable: {reason}")

    return {
        "id": MODEL_ID,
        "object": "model",
        "created": 0,
        "owned_by": "apple",
    }


# ---------------------------------------------------------------------------
# CLI entry point (used by `apple-to-openai` script defined in pyproject.toml)
# ---------------------------------------------------------------------------


def _find_available_port(host: str, start_port: int, max_attempts: int = 100) -> int:
    """Scan from *start_port* upward and return the first port that is free."""
    import socket

    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                print(f"Port {port} is already in use, trying {port + 1}...")
    raise RuntimeError(
        f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}"
    )


def cli():
    """Launch the server via ``apple-to-openai`` console script."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Apple Intelligence OpenAI-Compatible API Server"
    )
    
    # CLI args override environment variables if explicitly passed
    parser.add_argument("--host", default=settings.host, help=f"Bind address (default: {settings.host})")
    parser.add_argument("--port", type=int, default=settings.port, help="Port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    # Determine port
    if args.port is not None:
        port = args.port
    elif settings.port is not None:
        port = settings.port
    else:
        # Auto-find port if not configured
        default_port = 8000
        port = _find_available_port(args.host, default_port)
        if port != default_port:
            print(f"\n💡 TIP: Create a .env file and set `APPLE_AI_PORT={port}` to always use this port.\n")

    uvicorn.run("server:app", host=args.host, port=port, reload=args.reload)