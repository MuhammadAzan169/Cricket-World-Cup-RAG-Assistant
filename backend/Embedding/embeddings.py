"""
Cricket World Cup RAG — Embedding Generator
============================================
Embedding generation using a quantized ONNX export of
sentence-transformers/all-MiniLM-L6-v2, served via fastembed/onnxruntime
instead of torch + sentence-transformers. The torch stack alone resides
at 300-400MB+ RAM just from import — too much headroom to spare on a
512MB Render instance, where it was causing OOM kills on real requests.
Handles batching and normalization.

Vector dimension: 384
Similarity metric: Cosine (via normalized inner product)
"""

import logging
import os
from typing import List

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    EMBEDDING_BATCH_SIZE,
    LOG_LEVEL,
)

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class EmbeddingGenerator:
    """
    Generates normalized embeddings using a fastembed/onnxruntime-backed
    ONNX export of sentence-transformers/all-MiniLM-L6-v2.

    Features:
        - Local model, no API costs, no torch dependency
        - Automatic batching for efficiency
        - L2 normalization for cosine similarity via inner product
        - Input validation
        - Deterministic output (same input → same embedding)
    """

    def __init__(self):
        self._model_name = EMBEDDING_MODEL
        self._dimension = EMBEDDING_DIMENSION
        self._batch_size = EMBEDDING_BATCH_SIZE
        self._model = None

    @property
    def model(self):
        """Lazy-initialize the fastembed ONNX model."""
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                logger.info(f"Loading embedding model: {self._model_name}")
                self._model = TextEmbedding(model_name=self._model_name, threads=1)
            except ImportError:
                raise ImportError(
                    "fastembed package required. Install with: pip install fastembed"
                )
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2-normalize vectors for cosine similarity via inner product."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        return vectors / norms

    def _validate_input(self, text: str) -> str:
        """Validate and sanitize input text."""
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")
        text = text.strip()
        if not text:
            raise ValueError("Empty text cannot be embedded")
        # Replace null bytes
        text = text.replace("\x00", " ")
        return text

    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate a normalized embedding for a single text.

        Args:
            text: Input text to embed.

        Returns:
            np.ndarray of shape (384,), L2-normalized.
        """
        text = self._validate_input(text)
        embeddings = np.array(list(self.model.embed([text])), dtype=np.float32)
        return self._normalize(embeddings)[0]

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate normalized embeddings for a batch of texts.
        Automatically processes in batches for efficiency.

        Args:
            texts: List of input texts.

        Returns:
            np.ndarray of shape (len(texts), 384), L2-normalized.
        """
        if not texts:
            return np.zeros((0, self._dimension), dtype=np.float32)

        validated = [self._validate_input(t) for t in texts]

        logger.info(f"Embedding {len(validated)} texts in batches of {self._batch_size}...")

        # fastembed handles batching internally via batch_size
        vectors = np.array(
            list(self.model.embed(validated, batch_size=self._batch_size)),
            dtype=np.float32,
        )
        return self._normalize(vectors)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query. Alias for embed_single with query semantics.

        Args:
            query: Search query text.

        Returns:
            np.ndarray of shape (384,), L2-normalized.
        """
        return self.embed_single(query)
