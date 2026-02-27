"""
Entry point for `python -m apple_intelligence_openai_api`.
"""

import argparse
import socket

import uvicorn


def _find_available_port(host: str, start_port: int, max_attempts: int = 100) -> int:
    """Scan from *start_port* upward and return the first port that is free."""
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


def main():
    parser = argparse.ArgumentParser(
        description="Apple Intelligence OpenAI-Compatible API Server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    port = _find_available_port(args.host, args.port)
    uvicorn.run("server:app", host=args.host, port=port, reload=args.reload)


if __name__ == "__main__":
    main()
