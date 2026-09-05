"""
FastAPI Server for Cricket World Cup RAG Chatbot
=================================================
Production-ready API server that serves the RAG chatbot and
static frontend files.

Endpoints:
    POST /chat          — Send a question, get an answer
    GET  /status        — Get system status and stats
    POST /build         — Rebuild the FAISS + BM25 index
    POST /clear-history — Clear conversation history
    GET  /health        — Simple health check

Run:
    python server.py
    # or
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import APP_ENV, CROSS_ENCODER_RERANK
from main import CricketChatbot

# Allowed frontend origins. Defaults to "*" (all origins) since this is a public
# read-only API with no credentials. Set ALLOWED_ORIGINS env var to a comma-separated
# list of specific origins to restrict access (e.g. "https://myapp.vercel.app").
_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
ALLOWED_ORIGINS = ["*"] if _origins_env in ("", "*") else [
    o.strip() for o in _origins_env.split(",") if o.strip()
]
PORT = int(os.getenv("PORT", "8000"))

# ────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server")

# Suppress noisy HTTP logs from model loading
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub.utils._http").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("fastembed").setLevel(logging.WARNING)

# ────────────────────────────────────────────────────────────
# CHATBOT SINGLETON
# ────────────────────────────────────────────────────────────

chatbot = CricketChatbot()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize chatbot on startup, cleanup on shutdown."""
    logger.info("🏏 Starting Cricket World Cup RAG Server...")
    try:
        chatbot.initialize()
        logger.info("✅ Chatbot initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chatbot: {e}")
        raise
    yield
    logger.info("🏏 Shutting down Cricket World Cup RAG Server...")


# ────────────────────────────────────────────────────────────
# FASTAPI APP
# ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Cricket World Cup RAG Chatbot",
    description="AI-powered chatbot for ICC Cricket World Cup queries (2003–2023)",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — origins configured via the ALLOWED_ORIGINS env var (no wildcard in prod).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for /chat endpoint."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The cricket question to ask",
        examples=["Who won the 2011 World Cup?"],
    )


class ChatResponse(BaseModel):
    """Response body for /chat endpoint."""
    answer: str
    query_type: str
    sources: list
    search_results: int
    processing_time: float


class BuildRequest(BaseModel):
    """Request body for /build endpoint."""
    force_rebuild: bool = Field(
        default=False,
        description="If True, rebuild even if index already exists",
    )


class BuildResponse(BaseModel):
    """Response body for /build endpoint."""
    message: str
    stats: dict


class StatusResponse(BaseModel):
    """Response body for /status endpoint."""
    status: str
    details: dict


# ────────────────────────────────────────────────────────────
# API ENDPOINTS
# ────────────────────────────────────────────────────────────


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a cricket question through the full RAG pipeline.
    Returns an answer with sources and metadata.
    """
    try:
        logger.info(f"📨 Question: {request.question[:80]}...")
        result = chatbot.ask(request.question)
        logger.info(
            f"✅ Answered in {result['processing_time']}s "
            f"({result['query_type']}, {result['search_results']} sources)"
        )
        return ChatResponse(**result)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        raise HTTPException(status_code=503, detail="The server is still starting up — please try again in a few seconds.")
    except Exception as e:
        logger.error(f"Unexpected error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your question. Please try again in a moment.",
        )


@app.get("/status", response_model=StatusResponse)
async def status():
    """Get chatbot system status and statistics."""
    try:
        details = chatbot.get_status()
        return StatusResponse(status="ok", details=details)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build", response_model=BuildResponse)
async def build_index(request: BuildRequest):
    """
    Build or rebuild the FAISS + BM25 search index.
    This processes all cricket data files and creates embeddings.
    """
    try:
        logger.info(f"🔨 Building index (force_rebuild={request.force_rebuild})...")
        stats = chatbot.build_index(force_rebuild=request.force_rebuild)
        logger.info(f"✅ Index built: {stats}")
        return BuildResponse(
            message="Index built successfully",
            stats=stats,
        )
    except Exception as e:
        logger.error(f"Error building index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear-history")
async def clear_history():
    """Clear the conversation history."""
    try:
        chatbot.clear_history()
        return {"message": "Conversation history cleared"}
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Simple health check endpoint (also used by the Render health check)."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        # Which runtime profile is active — handy for confirming a deploy is
        # actually running the lightweight path and not trying to load torch.
        "environment": APP_ENV,
        "cross_encoder": CROSS_ENCODER_RERANK,
    }


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream a chat response via Server-Sent Events (SSE).
    Events: meta (query info), token (text chunk), done (final stats).
    """
    import asyncio

    def generate():
        try:
            for event_type, data in chatbot.ask_stream(request.question):
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            import json
            logger.error(f"Stream error: {e}", exc_info=True)
            friendly = "Something went wrong while generating a response. Please try again in a moment."
            yield f"event: error\ndata: {json.dumps({'error': friendly})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ────────────────────────────────────────────────────────────
# ROOT
# ────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """API info. The frontend is deployed separately (Vercel)."""
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
        "environment": APP_ENV,
    }


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("🏏 Launching Cricket World Cup RAG Server on port %d", PORT)
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False, log_level="info")
