"""
Example configuration for Cricket Companion RAG bot.

Copy this file to `config.py` and fill in real values. `config.py` is
ignored by .gitignore so secrets won't be committed.
"""

# OpenAI / LLM
OPENAI_API_KEY = "your-openai-api-key-here"

# Optional: if you use a different provider, specify keys here
# PROVIDER_API_KEY = "..."

# Paths (keep these local; large indexes should not be committed)
VECTOR_STORE_DIR = r"./index"            # where vector DB files (faiss, vectors.json) are stored
EMBEDDINGS_DIR = r"./Cricket Data/embeddings"

# Server settings
HOST = "127.0.0.1"
PORT = 8000

# Optional: local database (e.g., SQLite) for caching sessions
DATABASE_PATH = r"./data/app.db"

# App behavior flags
DEBUG = True

# Replace with any other secrets you need (e.g., third-party keys)

# Note: Do NOT commit real secrets. Keep them in `config.py` or environment variables.
