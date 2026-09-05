# ── Cricket World Cup RAG — Backend (Render free-plan ready) ──────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    APP_ENV=render \
    OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/app/.hf-cache \
    FASTEMBED_CACHE_PATH=/app/.fastembed-cache

WORKDIR /app

# curl is only needed for the container healthcheck. No compilers: every
# dependency in requirements.txt ships manylinux wheels, and gcc/g++ would
# add ~200MB to the image for nothing.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# NOTE: requirements.txt only — requirements-local.txt pulls in torch, which
# does not fit in the 512MB free plan.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image at build time. Without this,
# every fresh container (every Render restart, and the free plan spins down
# after 15 idle minutes) re-downloads it from the Hugging Face Hub on the first
# request — adding 10-20s of network calls right when live traffic arrives.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# Copy code + prebuilt index (FAISS + BM25 ship with the image).
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=20s --start-period=90s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
