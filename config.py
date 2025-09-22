# config.py
import os

# Data directory (point to where your 265 JSON files live)
DATA_DIR = r"C:\Users\muham\OneDrive\Desktop\Cricket"

# FAISS index base path (will create two files: .faiss and _metadata.pkl)
INDEX_PATH = os.path.join(DATA_DIR, "faiss_index")

# Embedding model and cache
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_CACHE_DIR = os.path.join(DATA_DIR, "model_cache")

# Device preference: "cuda" or "cpu"
DEVICE = "cuda"

# Chunking parameters
CHUNK_SIZE = 1200        # characters in a full-text chunk (we chunk by chars)
CHUNK_OVERLAP = 300

# Local OpenAI-compatible LLM (Ollama or similar)
OPENAI_API_BASE = "http://localhost:11434/v1"   # change if needed
OPENAI_API_KEY = "ollama"
LLM_MODEL = "llama3.1:8b"

# LLM behavior
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 800

# Local paths ensure exist
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
