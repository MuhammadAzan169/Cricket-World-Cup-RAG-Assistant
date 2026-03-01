"""
DIE Knowledge Base — FAISS Vector Store
==========================================
Production-grade FAISS index management with HNSWFlat,
cosine similarity, incremental insert, and disk persistence.

Index: HNSWFlat (HNSW graph with flat storage)
Distance: Inner Product on L2-normalized vectors (= Cosine similarity)
Dimension: 384
"""

import json
import logging
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import (
    EMBEDDING_DIMENSION,
    FAISS_INDEX_PATH,
    FAISS_HNSW_M,
    FAISS_EF_CONSTRUCTION,
    FAISS_EF_SEARCH,
    CHUNKS_JSON_PATH,
    VECTORS_JSON_PATH,
    INDEX_DIR,
    LOG_LEVEL,
)

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class FAISSVectorStore:
    """
    FAISS-backed vector store with HNSWFlat index.

    Features:
        - HNSWFlat index for fast approximate nearest neighbor search
        - Cosine similarity via inner product on normalized vectors
        - Incremental insert (add vectors without rebuilding)
        - Atomic disk persistence with fail-safe writes
        - Thread-safe operations
        - Vector ID ↔ chunk ID mapping
    """

    def __init__(
        self,
        index_dir: Optional[Path] = None,
        dimension: int = EMBEDDING_DIMENSION,
        hnsw_m: int = FAISS_HNSW_M,
        ef_construction: int = FAISS_EF_CONSTRUCTION,
        ef_search: int = FAISS_EF_SEARCH,
    ):
        self._index_dir = Path(index_dir) if index_dir else INDEX_DIR
        self._dimension = dimension
        self._hnsw_m = hnsw_m
        self._ef_construction = ef_construction
        self._ef_search = ef_search

        self._index = None
        self._vector_to_chunk: Dict[int, str] = {}  # vector_id → chunk_id
        self._chunk_to_vector: Dict[str, int] = {}   # chunk_id → vector_id
        self._lock = threading.Lock()
        self._next_id = 0

        # Ensure index directory exists
        self._index_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self._index_path = self._index_dir / "faiss.index"
        self._chunks_path = self._index_dir / "chunks.json"
        self._vectors_path = self._index_dir / "vectors.json"

    @property
    def faiss(self):
        """Lazy import of faiss."""
        try:
            import faiss
            return faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu package required. Install with: pip install faiss-cpu"
            )

    @property
    def is_initialized(self) -> bool:
        return self._index is not None

    @property
    def total_vectors(self) -> int:
        if self._index is None:
            return 0
        return self._index.ntotal

    @property
    def dimension(self) -> int:
        return self._dimension

    def initialize(self, force_new: bool = False) -> None:
        """
        Initialize the FAISS index. Load from disk if exists,
        otherwise create a new HNSWFlat index.

        Args:
            force_new: If True, discard existing index and create fresh.
        """
        with self._lock:
            if not force_new and self._index_path.exists():
                self._load_from_disk()
            else:
                self._create_new_index()

    def _create_new_index(self) -> None:
        """Create a fresh HNSWFlat index."""
        faiss = self.faiss

        # HNSWFlat with inner product (cosine on normalized vectors)
        self._index = faiss.IndexHNSWFlat(self._dimension, self._hnsw_m, faiss.METRIC_INNER_PRODUCT)
        self._index.hnsw.efConstruction = self._ef_construction
        self._index.hnsw.efSearch = self._ef_search

        self._vector_to_chunk = {}
        self._chunk_to_vector = {}
        self._next_id = 0

        logger.info(
            f"Created new FAISS HNSWFlat index: "
            f"dim={self._dimension}, M={self._hnsw_m}, "
            f"efConstruction={self._ef_construction}, efSearch={self._ef_search}"
        )

    def _load_from_disk(self) -> None:
        """Load FAISS index and mappings from disk."""
        faiss = self.faiss

        try:
            self._index = faiss.read_index(str(self._index_path))
            self._index.hnsw.efSearch = self._ef_search

            # Load vector ↔ chunk mappings
            if self._vectors_path.exists():
                with open(self._vectors_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
                self._vector_to_chunk = {int(k): v for k, v in mapping.get("vector_to_chunk", {}).items()}
                self._chunk_to_vector = mapping.get("chunk_to_vector", {})
                self._next_id = max(self._vector_to_chunk.keys(), default=-1) + 1
            else:
                self._vector_to_chunk = {}
                self._chunk_to_vector = {}
                self._next_id = self._index.ntotal

            logger.info(
                f"Loaded FAISS index from disk: "
                f"{self._index.ntotal} vectors, "
                f"{len(self._vector_to_chunk)} mappings"
            )
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}. Creating new index.")
            self._create_new_index()

    def add_vectors(
        self,
        vectors: np.ndarray,
        chunk_ids: List[str],
    ) -> List[int]:
        """
        Add vectors to the FAISS index with chunk ID mapping.

        Args:
            vectors: np.ndarray of shape (N, 384), L2-normalized.
            chunk_ids: List of chunk IDs corresponding to each vector.

        Returns:
            List of assigned vector IDs.
        """
        if vectors.shape[0] != len(chunk_ids):
            raise ValueError(
                f"Vector count ({vectors.shape[0]}) != chunk_id count ({len(chunk_ids)})"
            )
        if vectors.shape[1] != self._dimension:
            raise ValueError(
                f"Vector dimension ({vectors.shape[1]}) != expected ({self._dimension})"
            )

        if not self.is_initialized:
            self.initialize()

        with self._lock:
            vectors = vectors.astype(np.float32)
            assigned_ids = []

            for i in range(vectors.shape[0]):
                chunk_id = chunk_ids[i]

                # Skip if chunk already indexed
                if chunk_id in self._chunk_to_vector:
                    assigned_ids.append(self._chunk_to_vector[chunk_id])
                    continue

                vector_id = self._next_id
                self._next_id += 1

                # Add to FAISS (HNSWFlat uses sequential add)
                self._index.add(vectors[i : i + 1])

                # Update mappings
                self._vector_to_chunk[vector_id] = chunk_id
                self._chunk_to_vector[chunk_id] = vector_id
                assigned_ids.append(vector_id)

            logger.info(f"Added {len(assigned_ids)} vectors to FAISS index")
            return assigned_ids

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
    ) -> List[Tuple[int, str, float]]:
        """
        Search for nearest neighbors in the FAISS index.

        Args:
            query_vector: np.ndarray of shape (384,), L2-normalized.
            top_k: Number of results to return.

        Returns:
            List of (vector_id, chunk_id, similarity_score) tuples,
            sorted by descending similarity.
        """
        if not self.is_initialized:
            self.initialize()

        if self._index.ntotal == 0:
            return []

        with self._lock:
            query = query_vector.reshape(1, -1).astype(np.float32)
            effective_k = min(top_k, self._index.ntotal)

            distances, indices = self._index.search(query, effective_k)

            results = []
            for i in range(effective_k):
                idx = int(indices[0][i])
                score = float(distances[0][i])

                if idx < 0:  # FAISS returns -1 for not-found
                    continue

                chunk_id = self._vector_to_chunk.get(idx, f"unknown_{idx}")
                results.append((idx, chunk_id, score))

            return results

    def save(self) -> None:
        """
        Persist FAISS index and mappings to disk.
        Uses atomic writes with temp files to prevent corruption.
        """
        if not self.is_initialized:
            logger.warning("No index to save")
            return

        with self._lock:
            self._index_dir.mkdir(parents=True, exist_ok=True)

            # Atomic write: write to temp, then rename
            tmp_index = self._index_path.with_suffix(".index.tmp")
            tmp_vectors = self._vectors_path.with_suffix(".json.tmp")

            try:
                # Save FAISS index
                self.faiss.write_index(self._index, str(tmp_index))

                # Save mappings
                mapping = {
                    "vector_to_chunk": {str(k): v for k, v in self._vector_to_chunk.items()},
                    "chunk_to_vector": self._chunk_to_vector,
                    "next_id": self._next_id,
                    "total_vectors": self._index.ntotal,
                    "dimension": self._dimension,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }
                with open(tmp_vectors, "w", encoding="utf-8") as f:
                    json.dump(mapping, f, indent=2)

                # Atomic rename
                if tmp_index.exists():
                    shutil.move(str(tmp_index), str(self._index_path))
                if tmp_vectors.exists():
                    shutil.move(str(tmp_vectors), str(self._vectors_path))

                logger.info(
                    f"Saved FAISS index: {self._index.ntotal} vectors → {self._index_path}"
                )

            except Exception as e:
                # Cleanup temp files on failure
                for tmp in [tmp_index, tmp_vectors]:
                    if tmp.exists():
                        tmp.unlink()
                logger.error(f"Failed to save FAISS index: {e}")
                raise

    def get_chunk_id(self, vector_id: int) -> Optional[str]:
        """Get chunk ID for a vector ID."""
        return self._vector_to_chunk.get(vector_id)

    def has_chunk(self, chunk_id: str) -> bool:
        """Check if a chunk ID is already indexed."""
        return chunk_id in self._chunk_to_vector

    def get_stats(self) -> dict:
        """Get index statistics."""
        return {
            "total_vectors": self.total_vectors,
            "dimension": self._dimension,
            "index_type": "HNSWFlat",
            "hnsw_m": self._hnsw_m,
            "ef_construction": self._ef_construction,
            "ef_search": self._ef_search,
            "metric": "cosine",
            "mappings_count": len(self._vector_to_chunk),
            "index_file_exists": self._index_path.exists(),
        }

    def reset(self) -> None:
        """Delete the index and all mappings. Destructive."""
        with self._lock:
            self._create_new_index()
            # Remove files
            for path in [self._index_path, self._vectors_path]:
                if path.exists():
                    path.unlink()
            logger.warning("FAISS index reset — all vectors deleted")
