# Apple Intelligence OpenAI-Compatible API

A lightweight API server that exposes Apple's **on-device Foundation Model** (Apple Intelligence) through an **OpenAI-compatible** chat completions endpoint. Any client that speaks the OpenAI protocol — ChatGPT UIs, IDE plugins, CLI tools — can connect and use Apple Intelligence running entirely on your Mac.

## Features

- **OpenAI-compatible** `/v1/chat/completions` (streaming & non-streaming)
- **`/v1/models`** endpoint for model discovery
- **100 % on-device** — no API keys, no cloud, no per-token cost
- **CORS enabled** — works from browser-based clients
- Runs via a single `uv run` command

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Mac** | Apple Silicon (M1 or later) |
| **macOS** | Tahoe **26.0** or later |
| **Xcode** | **26.0** or later (agree to the Xcode and Apple SDKs agreement) |
| **RAM** | 8 GB minimum (16 GB recommended) |
| **Storage** | ≥ 7 GB free for on-device model download |
| **Python** | 3.13+ |

### 1. Enable Apple Intelligence

1. Open **System Settings** → **Apple Intelligence & Siri**.
2. Click **Turn on Apple Intelligence**.
3. Wait for the on-device model to finish downloading (keep your Mac on Wi-Fi and power).
4. Ensure Siri language is set to a supported language (e.g. English).

> **Note:** If the option is greyed out, ensure your Mac meets all hardware requirements and is running a supported macOS version. In some regions you may need to set your region to "United States" under **System Settings → General → Language & Region**.

---

## Environment Setup (from scratch)

### 2. Install Xcode

Download [Xcode 26.0+](https://developer.apple.com/xcode/) from the Mac App Store or the Apple Developer website. After installation, open Xcode once and agree to the license agreement.

Then install the Command Line Tools:

```bash
xcode-select --install
```

### 3. Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the printed instructions to add Homebrew to your `PATH` (usually involves adding a line to `~/.zprofile`).

### 4. Install Python 3.13+

```bash
brew install python@3.13
```

Verify:

```bash
python3 --version   # Should print 3.13.x or later
```

### 5. Install `uv` (recommended Python project manager)

```bash
brew install uv
```

Or via the standalone installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

---

## Installation

We'll create a workspace directory in your home folder and set up both the Apple Foundation Models SDK and this API server.

### 6. Clone the Apple Foundation Models SDK

The SDK is **not** on PyPI — it must be built from source. You only need to **clone** it here; the API project will build and link it automatically in the next step.

```bash
mkdir -p ~/apple-intelligence && cd ~/apple-intelligence

git clone https://github.com/apple/python-apple-fm-sdk
```

### 7. Clone & Set Up This Project

```bash
cd ~/apple-intelligence

git clone https://github.com/ZPVIP/apple-to-openai
cd apple-to-openai

uv sync
```

`uv sync` will:
1. Create a `.venv` in the project directory
2. Automatically build & install the SDK from the sibling `../python-apple-fm-sdk` directory (configured as a path dependency in `pyproject.toml`)
3. Install all other dependencies (`fastapi`, `uvicorn`, etc.)

Your directory structure should look like:

```
~/apple-intelligence/
├── python-apple-fm-sdk/          # Apple's official SDK (cloned in step 6)
└── apple-to-openai/                 # This project (cloned in step 7)
```

---

## Running the Server

### Option A — Recommended (via project script)

```bash
cd ~/apple-intelligence/apple-to-openai
uv run apple-to-openai
```

This starts the server on `0.0.0.0:8000` by default.

**Available flags:**

| Flag | Description | Default |
|---|---|---|
| `--host` | Bind address | `0.0.0.0` or `APPLE_AI_HOST` |
| `--port` | Port number | Auto-detected or `APPLE_AI_PORT` |
| `--reload` | Auto-reload on code changes (dev mode) | off |

Example:

```bash
uv run apple-to-openai --port 9000 --reload
```

### Option B — Via `python -m`

```bash
uv run python __main__.py
# or
uv run python __main__.py --port 9000
```

### Option C — Direct uvicorn (manual)

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## Configuration

You can configure the server using environment variables. It is highly recommended to create a `.env` file in the project root to fix your port and other settings.

| Environment Variable | Description | Default |
|---|---|---|
| `APPLE_AI_HOST` | Bind address | `0.0.0.0` |
| `APPLE_AI_PORT` | Port number (if empty, auto-detects free port) | `None` |
| `APPLE_AI_MAX_CONCURRENCY` | Max simultaneous requests to Foundation Model | `4` |
| `APPLE_AI_REQUEST_TIMEOUT` | Timeout in seconds | `30.0` |
| `APPLE_AI_API_KEY` | Optional Bearer token for authentication | `None` |

**Security Note on `APPLE_AI_HOST`:**
By default, the server binds to `0.0.0.0`, allowing other devices on your local network (LAN) to connect to your Mac and use your Apple Intelligence. If you want to restrict access to *only your local machine*, set `APPLE_AI_HOST=127.0.0.1`.

**Why set a fixed port?**
By default, the server will scan for an available port starting at `8000`. If `8000` is already in use by another app, it might start on `8001`, `8002`, etc. This means you would need to constantly update the URL in your AI clients (Chatbox, OpenCode, etc.). Setting a fixed port in `.env` prevents this.

**Example `.env` file:**
```env
APPLE_AI_PORT=8002
APPLE_AI_MAX_CONCURRENCY=4
APPLE_AI_REQUEST_TIMEOUT=30.0
```

---

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### List Models

```bash
curl http://localhost:8000/v1/models
```

### Chat Completion (streaming)

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "apple-intelligence",
    "messages": [{"role": "user", "content": "What is Apple Intelligence?"}],
    "stream": true
  }'
```

### Chat Completion (non-streaming)

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "apple-intelligence",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

---

## Connecting Clients

Point any OpenAI-compatible client at:

```
Base URL: http://localhost:8000/v1
API Key:  any-string-works  (or your APPLE_AI_API_KEY if set)
Model:    apple-intelligence
```

Examples of compatible clients:

- [Open WebUI](https://github.com/open-webui/open-webui)
- [ChatBox](https://chatboxai.app/)
- [BoltAI](https://boltai.com/)
- IDE plugins (Continue, Cursor, Copilot alternatives)
- Any tool using the OpenAI Python/JS SDK

### OpenCode Configuration

To connect the Apple Foundation Model to OpenCode, add the following to your `opencode.jsonc` (in your project or `~/.config/opencode/opencode.jsonc`):

> **Note on `limit`**: The Apple Foundation Model internally enforces a strict 4096-token limit. Providing the `limit` setting below tells OpenCode to actively chunk context before sending it to the API, preventing "Context Exceeded" errors upstream.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "apple-fm-local": {
      "name": "Apple FM Local",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://127.0.0.1:8000/v1"
      },
      "models": {
        "apple-intelligence": {
          "name": "Apple Intelligence",
          "tool_call": false,
          "limit": { "context": 4096, "output": 2048 }
        }
      }
    }
  },
  "model": "apple-fm-local/apple-intelligence"
}
```

Restart OpenCode and select `apple-fm-local/apple-intelligence`.

---

## Streaming Format

The server follows the OpenAI streaming spec with two additional compatibility enhancements:

1. **First chunk** sends the assistant role:
   ```json
   {"delta": {"role": "assistant"}}
   ```
2. **Before the finish chunk**, an empty-content chunk is sent:
   ```json
   {"delta": {"content": ""}}
   ```
3. **Finish chunk** with `"finish_reason": "stop"`
4. **`data: [DONE]`** sentinel

This ensures compatibility with clients that expect the role announcement and/or an explicit empty-content signal.

---

## Project Structure

```
apple-to-openai/
├── server.py          # FastAPI application & endpoints
├── __main__.py        # python -m entry point
├── pyproject.toml     # Project metadata & dependencies
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

---

## Limitations

### Context Window

The on-device Apple Foundation Model has a **4,096-token** context window (input + output combined). The model estimates the total token usage before generating a response — if the combined input and expected output would exceed the limit, the request is rejected.

| Language | ~Max Input Length | 1 Token ≈ |
|---|---|---|
| **English** | ~20,000 characters | 5 characters |
| **Chinese** | ~6,400 characters (汉字) | 1.6 characters |
| **Mixed** | Somewhere in between | — |

In practice, this means:

- **Summarization / short answers**: The expected output is small, so the input can be quite long (close to the max above).
- **Story continuation / long essays**: The model anticipates a long output, leaving less room for input. A 15,000-character English prompt asking for a detailed essay may already be rejected, even though the same length would succeed if only a short summary is requested.

> **Note:** If the context window is exceeded, the server returns an OpenAI-compatible `context_length_exceeded` error (HTTP 400) instead of crashing.

> **Note:** For multi-turn conversations, the server automatically truncates older messages to fit within the character limit — it keeps the system prompt and the most recent messages, discarding the oldest ones first. See `truncate_messages()` in `server.py`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Foundation model not available` | Ensure Apple Intelligence is enabled and the model has finished downloading |
| `apple_fm_sdk` install fails | Ensure you're on macOS 26.0+ with Xcode 26.0+ installed |
| `No solution found` during `uv sync` | Make sure `python-apple-fm-sdk` is cloned as a sibling directory |
| Port already in use | Use `--port <other-port>` or kill the existing process |
| Streaming not working in client | Verify client supports SSE; try non-streaming mode first |

## License

[Apache License 2.0](LICENSE)

*If you modify or use this project, you must include the original copyright notice and a copy of the Apache 2.0 license. This ensures attribution to this original repository.*
