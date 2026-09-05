#!/usr/bin/env python3
"""
Cricket World Cup RAG Assistant - Local Application Runner
==========================================================
One command to run the WHOLE thing locally: the FastAPI backend (RAG pipeline,
local embedding model, local cross-encoder re-ranker) and the static frontend,
already wired to talk to each other.

    python app.py

    python app.py --no-browser          # don't open a browser tab
    python app.py --backend-port 8001   # move the API off 8000
    python app.py --frontend-port 3000  # move the site off 5500
    python app.py --backend-only        # API only (e.g. you serve the UI yourself)
    python app.py --check               # verify the setup, then exit

This runner is deliberately dependency-free (stdlib only) and never talks to
the deployed Render backend - everything runs on this machine.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

DEFAULT_BACKEND_PORT = int(os.environ.get("PORT", "8000"))
DEFAULT_FRONTEND_PORT = 5500

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
GREEN, YELLOW, RED, CYAN = "\033[32m", "\033[33m", "\033[31m", "\033[36m"

PLACEHOLDER_KEYS = {"", "your-api-key-here", "your_api_key_here"}


def log(msg: str, colour: str = "") -> None:
    print(f"{colour}{msg}{RESET}", flush=True)


# ---------------------------------------------------------------------
# ENVIRONMENT
# ---------------------------------------------------------------------


def load_env_file(path: Path) -> dict:
    """Minimal .env parser. The real process env always wins over this."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key:
            values[key] = val
    return values


def has_api_key(env: dict) -> bool:
    """The backend needs LLM_API_KEY or any OPENROUTER_API_KEY* to start."""
    merged = {**env, **os.environ}
    for key, val in merged.items():
        if key == "LLM_API_KEY" or key.startswith("OPENROUTER_API_KEY"):
            if val and val.strip() not in PLACEHOLDER_KEYS:
                return True
    return False


def preflight() -> bool:
    """Check that everything needed for a local run is present."""
    ok = True

    if not BACKEND_DIR.is_dir():
        log(f"x Missing backend directory: {BACKEND_DIR}", RED)
        return False
    if not FRONTEND_DIR.is_dir():
        log(f"x Missing frontend directory: {FRONTEND_DIR}", RED)
        return False

    missing = []
    for module, package in [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn[standard]"),
        ("dotenv", "python-dotenv"),
        ("openai", "openai"),
        ("fastembed", "fastembed"),
        ("faiss", "faiss-cpu"),
        ("rank_bm25", "rank-bm25"),
        ("numpy", "numpy"),
    ]:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        log(f"x Missing Python packages: {', '.join(missing)}", RED)
        log("  Install them with:  pip install -r backend/requirements-local.txt", YELLOW)
        ok = False
    else:
        log("+ Python dependencies installed", GREEN)

    # Optional local-only extra: the torch cross-encoder re-ranker.
    try:
        __import__("sentence_transformers")
        log("+ Cross-encoder re-ranker available (local high-quality mode)", GREEN)
    except ImportError:
        log("- Cross-encoder re-ranker not installed; falling back to metadata "
            "re-ranking. Install with: pip install -r backend/requirements-local.txt", DIM)

    index_dir = BACKEND_DIR / "index"
    if (index_dir / "faiss.index").exists() and (index_dir / "chunks.json").exists():
        log("+ Prebuilt search index found", GREEN)
    else:
        log("- No prebuilt index; the backend will build one on first run "
            "(takes a few minutes). You can also POST /build.", YELLOW)

    env_file = BACKEND_DIR / ".env"
    env = load_env_file(env_file)
    if not env_file.exists():
        log(f"x Missing {env_file}", RED)
        log("  Create it with:  cp backend/.env.example backend/.env", YELLOW)
        ok = False
    elif not has_api_key(env):
        log("x No LLM API key found in backend/.env", RED)
        log("  Set LLM_API_KEY (get one at https://openrouter.ai/keys)", YELLOW)
        ok = False
    else:
        log("+ LLM API key configured", GREEN)

    return ok


# The backend must be reachable from the LAN (uvicorn binds 0.0.0.0), while the
# dev static server stays on loopback. Bind checks have to use the exact same
# host, or a port already taken on 0.0.0.0 looks free when probed on 127.0.0.1.
BACKEND_HOST = "0.0.0.0"
FRONTEND_HOST = "127.0.0.1"


def port_is_free(port: int, host: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(preferred: int, host: str, label: str, tries: int = 20) -> "int | None":
    """Use `preferred` if it is free, otherwise walk upwards to the next free port."""
    for offset in range(tries):
        port = preferred + offset
        if port_is_free(port, host):
            if offset:
                log(f"- Port {preferred} is in use; running the {label} on {port} instead.",
                    YELLOW)
            return port
    log(f"x No free port for the {label} in range {preferred}-{preferred + tries - 1}.", RED)
    return None


# ---------------------------------------------------------------------
# FRONTEND
# ---------------------------------------------------------------------


def write_frontend_config(backend_port: int) -> None:
    """
    Generate frontend/js/config.js so the local UI talks to the LOCAL backend.

    This is the same file Vercel generates at build time via build.mjs. Doing it
    here in Python means a local run needs no Node.js install at all.
    """
    api_base = f"http://localhost:{backend_port}"
    config_path = FRONTEND_DIR / "js" / "config.js"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "// AUTO-GENERATED for local development by app.py - do not edit by hand.\n"
        "// In production this file is regenerated by build.mjs from API_BASE_URL.\n"
        "window.APP_CONFIG = {\n"
        f"  API_BASE_URL: {json.dumps(api_base)},\n"
        "};\n",
        encoding="utf-8",
    )
    log(f"+ Frontend configured to use API at {api_base}", GREEN)


class FrontendHandler(http.server.SimpleHTTPRequestHandler):
    """Static file server for the frontend, mirroring the Vercel rewrites."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        # Mirror vercel.json: /chat-page -> /chatbot.html, plus cleanUrls, so a
        # link that works in production also works here.
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean in ("/chat-page", "/chat-page/"):
            path = "/chatbot.html"
        elif clean not in ("", "/") and not Path(clean).suffix:
            candidate = FRONTEND_DIR / (clean.strip("/") + ".html")
            if candidate.is_file():
                path = "/" + clean.strip("/") + ".html"
        return super().translate_path(path)

    def end_headers(self) -> None:
        # Never cache during development - stale JS/CSS is a nasty time sink.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        pass  # keep the console readable; uvicorn already logs the API


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_frontend(port: int) -> ThreadedHTTPServer:
    server = ThreadedHTTPServer((FRONTEND_HOST, port), FrontendHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---------------------------------------------------------------------
# BACKEND
# ---------------------------------------------------------------------


def start_backend(port: int, frontend_port: int, reload: bool) -> subprocess.Popen:
    """Launch uvicorn as a child process with backend/ as its working dir."""
    env = os.environ.copy()
    env.setdefault("APP_ENV", "local")  # enables the local-only heavy models
    env["PORT"] = str(port)
    env.setdefault(
        "ALLOWED_ORIGINS",
        ",".join(f"http://{host}:{frontend_port}" for host in ("localhost", "127.0.0.1")),
    )
    env.setdefault("PYTHONUNBUFFERED", "1")

    cmd = [
        sys.executable, "-m", "uvicorn", "server:app",
        "--host", BACKEND_HOST,
        "--port", str(port),
        "--log-level", "info",
    ]
    if reload:
        cmd.append("--reload")

    return subprocess.Popen(cmd, cwd=str(BACKEND_DIR), env=env)


def wait_for_backend(port: int, process: subprocess.Popen, timeout: float = 300.0) -> bool:
    """Poll /health until the backend is up (the first run loads the models)."""
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1.0)
    return False


def stop_backend(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete Cricket World Cup RAG Assistant locally."
    )
    parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open a browser tab automatically.")
    parser.add_argument("--backend-only", action="store_true",
                        help="Run only the API server.")
    parser.add_argument("--reload", action="store_true",
                        help="Auto-reload the backend on code changes.")
    parser.add_argument("--check", action="store_true",
                        help="Run the environment checks and exit.")
    args = parser.parse_args()

    log("\n" + "=" * 62, CYAN)
    log(f"{BOLD}  Cricket World Cup RAG Assistant - local runner{RESET}", CYAN)
    log("=" * 62 + "\n", CYAN)

    if not preflight():
        log("\nx Setup incomplete - fix the items above and run again.\n", RED)
        return 1
    if args.check:
        log("\n+ Everything looks good. Run `python app.py` to start.\n", GREEN)
        return 0

    api_port = find_free_port(args.backend_port, BACKEND_HOST, "API")
    if api_port is None:
        return 1
    web_port = args.frontend_port
    if not args.backend_only:
        found = find_free_port(args.frontend_port, FRONTEND_HOST, "web app")
        if found is None:
            return 1
        web_port = found
        write_frontend_config(api_port)

    log("\n-> Starting backend (loading embedding model + search index)...", CYAN)
    backend = start_backend(api_port, web_port, args.reload)

    frontend: ThreadedHTTPServer | None = None
    try:
        if not wait_for_backend(api_port, backend):
            log("\nx The backend failed to start. See the log above for the reason.\n", RED)
            return 1
        log(f"+ Backend ready at http://localhost:{api_port}", GREEN)

        url = f"http://localhost:{api_port}/docs"
        if not args.backend_only:
            try:
                frontend = start_frontend(web_port)
            except OSError as exc:
                # Losing the static server is annoying but not fatal - the API
                # is up, so keep running instead of tearing everything down.
                log(f"x Could not serve the frontend on port {web_port}: {exc}", RED)
            else:
                url = f"http://localhost:{web_port}/"
                log(f"+ Frontend ready at {url}", GREEN)

        log("\n" + "=" * 62, CYAN)
        if frontend is not None:
            log(f"  Web app   {BOLD}http://localhost:{web_port}/{RESET}", CYAN)
            log(f"  Chatbot   {BOLD}http://localhost:{web_port}/chatbot.html{RESET}", CYAN)
        log(f"  API       http://localhost:{api_port}", CYAN)
        log(f"  API docs  http://localhost:{api_port}/docs", CYAN)
        log("=" * 62, CYAN)
        log("  Press Ctrl+C to stop.\n", DIM)

        if not args.no_browser:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()

        backend.wait()  # block until the backend exits or the user interrupts
    except KeyboardInterrupt:
        log("\n\n-> Shutting down...", YELLOW)
    finally:
        if frontend is not None:
            frontend.shutdown()
            frontend.server_close()
        stop_backend(backend)
        log("+ Stopped.\n", GREEN)

    return 0


if __name__ == "__main__":
    sys.exit(main())
