"""
Cricket World Cup RAG — Configuration
=======================================
Central configuration for embedding model, FAISS index, BM25 hybrid search,
chunking, re-ranking, and all tunable parameters. Production-grade defaults.
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
BM25_INDEX_PATH = INDEX_DIR / "bm25.pkl"
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
FAISS_HNSW_M = 32  # Number of connections per node
FAISS_EF_CONSTRUCTION = 200  # Construction-time search depth
FAISS_EF_SEARCH = 128  # Query-time search depth
FAISS_METRIC = "cosine"  # Cosine similarity via inner product on normalized vectors

# ────────────────────────────────────────────────────────────
# BM25 HYBRID SEARCH CONFIGURATION
# ────────────────────────────────────────────────────────────
BM25_ENABLED = True
BM25_K1 = 1.5  # Term frequency saturation
BM25_B = 0.75  # Document length normalization
BM25_WEIGHT = 0.35  # Weight of BM25 score in hybrid search (0-1)
SEMANTIC_WEIGHT = 0.65  # Weight of semantic (FAISS) score in hybrid search

# ────────────────────────────────────────────────────────────
# RE-RANKING CONFIGURATION
# ────────────────────────────────────────────────────────────
RERANK_ENABLED = True
RERANK_TOP_N = 15  # Number of candidates to re-rank from initial retrieval
RERANK_METADATA_BOOST = {
    "year_match": 0.15,        # Chunk mentions the same year as query
    "team_match": 0.10,        # Chunk mentions the same team
    "player_match": 0.10,      # Chunk mentions the same player
    "type_match": 0.05,        # Chunk type matches query type
    "memorable_moments": 0.08, # Boost memorable moments files
}

# ────────────────────────────────────────────────────────────
# CHUNKING CONFIGURATION
# ────────────────────────────────────────────────────────────
CHUNK_SIZE_MIN = 150  # Minimum tokens per chunk (lowered for more granular retrieval)
CHUNK_SIZE_MAX = 500  # Maximum tokens per chunk (raised for more context)
CHUNK_SIZE_TARGET = 300  # Target tokens per chunk
CHUNK_OVERLAP = 50  # Overlap tokens between consecutive chunks (increased for continuity)

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
    r"^=== ",               # Rich context section markers
    r"^\d+\.\s+",           # Numbered list items
    r"^FIRST INNINGS",      # Match play-by-play markers
    r"^SECOND INNINGS",
    r"^THE SUPER OVER",
    r"^BOUNDARY COUNTBACK",
    r"^IMPORTANT CLARIFICATIONS",
    r"^TOP MEMORABLE MOMENTS",
    r"^RECORDS SET",
    r"^MAJOR UPSETS",
    r"^TOURNAMENT FORMAT",
    r"^KEY UNUSUAL EVENTS",
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
    "match_embedding",       # Cricket-specific
    "tournament_summary",    # Cricket-specific
    "player_statistics",     # Cricket-specific
    "match_index",           # Cricket-specific: match listing
    "memorable_moments",     # Cricket-specific: rich narratives
    "cross_tournament",      # Cricket-specific: cross-tournament facts
    "records_and_facts",     # Cricket-specific: all-time records
    "qa_pair",               # Cricket Q&A pairs
}

# ────────────────────────────────────────────────────────────
# SEARCH CONFIGURATION
# ────────────────────────────────────────────────────────────
SEARCH_TOP_K_DEFAULT = 25  # Increased for better recall
SEARCH_TOP_K_MAX = 80
SEARCH_SCORE_THRESHOLD = 0.03  # Lowered to catch more potentially relevant chunks

# Query type-specific search parameters
QUERY_SEARCH_PARAMS = {
    "statistical": {"top_k": 30, "score_threshold": 0.03, "bm25_weight": 0.40},
    "comparative": {"top_k": 30, "score_threshold": 0.03, "bm25_weight": 0.35},
    "match_specific": {"top_k": 20, "score_threshold": 0.04, "bm25_weight": 0.40},
    "tournament": {"top_k": 25, "score_threshold": 0.03, "bm25_weight": 0.30},
    "player": {"top_k": 30, "score_threshold": 0.03, "bm25_weight": 0.35},
    "general": {"top_k": 25, "score_threshold": 0.04, "bm25_weight": 0.30},
}

# Ranking weights (for re-ranking stage)
RANKING_COSINE_WEIGHT = 0.75
RANKING_RECENCY_WEIGHT = 0.15
RANKING_METADATA_WEIGHT = 0.10

# Recency decay half-life in days
RECENCY_HALF_LIFE_DAYS = 365

# Context assembly
MAX_CONTEXT_CHARS = 14000  # Max characters to send to LLM
MAX_CONTEXT_CHUNKS = 30  # Max chunks to include

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
