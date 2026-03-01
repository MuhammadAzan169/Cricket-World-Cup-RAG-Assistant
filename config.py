"""
DIE Knowledge Base — Configuration
====================================
Central configuration for embedding model, FAISS index, chunking,
and all tunable parameters. Production-grade defaults.
"""

import os
from pathlib import Path

# ────────────────────────────────────────────────────────────
# PATH CONFIGURATION
# ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
KNOWLEDGE_BASE_ROOT = Path(__file__).resolve().parent

# Cricket dataset paths
CRICKET_DATA_DIR = PROJECT_ROOT / "Cricket Data"
CRICKET_EMBEDDINGS_DIR = CRICKET_DATA_DIR / "embeddings"
CRICKET_METADATA_DIR = CRICKET_DATA_DIR / "metadata"
CRICKET_CLEANED_DIR = CRICKET_DATA_DIR / "cleaned_matches"
CRICKET_STATS_DIR = CRICKET_DATA_DIR / "statistical_analysis"

# Knowledge base storage
DOCUMENTS_RAW_DIR = KNOWLEDGE_BASE_ROOT / "documents" / "raw"
DOCUMENTS_PROCESSED_DIR = KNOWLEDGE_BASE_ROOT / "documents" / "processed"
INDEX_DIR = KNOWLEDGE_BASE_ROOT / "index"

FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_JSON_PATH = INDEX_DIR / "chunks.json"
VECTORS_JSON_PATH = INDEX_DIR / "vectors.json"
METADATA_MD_PATH = INDEX_DIR / "metadata.md"
INDEX_MANIFEST_PATH = INDEX_DIR / "index_manifest.md"

# ────────────────────────────────────────────────────────────
# EMBEDDING MODEL CONFIGURATION
# ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Free, local model
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE = 32  # Smaller batch for local model

# ────────────────────────────────────────────────────────────
# FAISS INDEX CONFIGURATION
# ────────────────────────────────────────────────────────────
FAISS_INDEX_TYPE = "HNSWFlat"
FAISS_HNSW_M = 32  # Number of connections per node (higher = more accurate, more memory)
FAISS_EF_CONSTRUCTION = 200  # Construction-time search depth
FAISS_EF_SEARCH = 128  # Query-time search depth
FAISS_METRIC = "cosine"  # Cosine similarity via inner product on normalized vectors

# ────────────────────────────────────────────────────────────
# CHUNKING CONFIGURATION
# ────────────────────────────────────────────────────────────
CHUNK_SIZE_MIN = 200  # Minimum tokens per chunk
CHUNK_SIZE_MAX = 400  # Maximum tokens per chunk
CHUNK_SIZE_TARGET = 300  # Target tokens per chunk
CHUNK_OVERLAP = 30  # Overlap tokens between consecutive chunks

# Semantic boundary markers (regex patterns)
SECTION_BREAK_PATTERNS = [
    r"^#{1,6}\s",           # Markdown headings
    r"^={3,}$",             # Separator lines
    r"^-{3,}$",             # Separator lines
    r"^\*{3,}$",            # Separator lines
    r"^Match Summary:",     # Cricket embedding section
    r"^Batting Highlights:",
    r"^Bowling Highlights:",
    r"^Captain Performance:",
    r"^Key Moments:",
    r"^Result:",
    r"^ICC Cricket World Cup",
    r"^Player:",            # Player stats sections
    r"^Team Standings:",
    r"^Captains:",
    r"^Team Performance",   # Tournament summary sections
    r"^Head-to-Head",       # Head-to-head records
    r"^Captain Performance —",
    r"^Overall Statistics:",
    r"^Innings Analysis —",
    r"^Player Analysis:",
    r"^Key Insights:",
    r"^Statistical Analysis:",
    r"^Match:",             # Match index entries
]

# ────────────────────────────────────────────────────────────
# CHUNK TYPES
# ────────────────────────────────────────────────────────────
CHUNK_TYPES = {
    "document_section",
    "table",
    "meeting_transcript",
    "image_ocr",
    "csv_group",
    "excel_sheet",
    "summary",
    "match_embedding",      # Cricket-specific
    "tournament_summary",   # Cricket-specific
    "player_statistics",    # Cricket-specific
    "match_index",          # Cricket-specific: match listing
}

# ────────────────────────────────────────────────────────────
# SEARCH CONFIGURATION
# ────────────────────────────────────────────────────────────
SEARCH_TOP_K_DEFAULT = 20
SEARCH_TOP_K_MAX = 80
SEARCH_SCORE_THRESHOLD = 0.05  # Minimum cosine similarity to include (lowered for better recall)

# Ranking weights
RANKING_COSINE_WEIGHT = 0.75
RANKING_RECENCY_WEIGHT = 0.15
RANKING_METADATA_WEIGHT = 0.10

# Recency decay half-life in days
RECENCY_HALF_LIFE_DAYS = 365

# ────────────────────────────────────────────────────────────
# SOURCE TYPES
# ────────────────────────────────────────────────────────────
SUPPORTED_SOURCE_TYPES = {
    "document",
    "meeting",
    "image",
    "csv",
    "excel",
}

# ────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("KB_LOG_LEVEL", "INFO")
