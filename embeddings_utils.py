"""
World Cup Chatbot — Embeddings Utilities
==========================================
Lightweight module for loading/managing the FAISS index,
generating embeddings, and mapping queries to relevant
document snippets from the World Cup dataset (2003–2023).

Reuses existing Embedding/ modules (EmbeddingGenerator, FAISSVectorStore,
IngestionPipeline, TextChunker) to stay DRY.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Embedding.embeddings import EmbeddingGenerator
from Embedding.vector_store import FAISSVectorStore
from Embedding.chunking import TextChunker, Chunk
from Embedding.ingestion import IngestionPipeline

from config import (
    INDEX_DIR,
    CRICKET_EMBEDDINGS_DIR,
    CRICKET_METADATA_DIR,
    CHUNKS_JSON_PATH,
    SEARCH_TOP_K_DEFAULT,
    SEARCH_SCORE_THRESHOLD,
    LOG_LEVEL,
)

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class EmbeddingsManager:
    """
    Manages the FAISS index, embeddings, and semantic search
    for the World Cup chatbot.

    Responsibilities:
        - Load / initialize FAISS index + chunk mappings
        - Embed user queries
        - Perform semantic search → return ranked snippets
        - Rebuild index from Cricket Data if needed
        - Provide index statistics
    """

    def __init__(self, index_dir: Optional[Path] = None):
        self._index_dir = Path(index_dir) if index_dir else INDEX_DIR
        self._embedder: Optional[EmbeddingGenerator] = None
        self._store: Optional[FAISSVectorStore] = None
        self._pipeline: Optional[IngestionPipeline] = None
        self._chunker: Optional[TextChunker] = None
        self._initialized = False

    # ────────────────────────────────────────────────────────
    # INITIALIZATION
    # ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        Load the embedding model, FAISS index, and chunk mappings.
        If no index exists on disk, creates a fresh one.
        """
        if self._initialized:
            return

        logger.info("Initializing EmbeddingsManager...")

        self._index_dir.mkdir(parents=True, exist_ok=True)

        # Core components (reuse existing modules)
        self._embedder = EmbeddingGenerator()
        self._store = FAISSVectorStore(index_dir=self._index_dir)
        self._store.initialize()
        self._chunker = TextChunker()
        self._pipeline = IngestionPipeline(
            embedding_generator=self._embedder,
            vector_store=self._store,
            chunker=self._chunker,
        )

        self._initialized = True
        stats = self.get_stats()
        logger.info(
            f"EmbeddingsManager ready — "
            f"{stats['total_vectors']} vectors, "
            f"{stats['total_chunks']} chunks"
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                "EmbeddingsManager not initialized. Call initialize() first."
            )

    # ────────────────────────────────────────────────────────
    # SEMANTIC SEARCH
    # ────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = SEARCH_TOP_K_DEFAULT,
        score_threshold: float = SEARCH_SCORE_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search over the FAISS index.

        Args:
            query: User question / search text.
            top_k: Maximum results to return.
            score_threshold: Minimum cosine similarity to include.

        Returns:
            List of dicts with keys:
                text, file_name, score, chunk_type, section_title, tags
        """
        self._ensure_initialized()

        if self._store.total_vectors == 0:
            logger.warning("Index is empty — no vectors to search")
            return []

        # Embed query
        query_vector = self._embedder.embed_query(query)

        # Search FAISS
        raw_results = self._store.search(query_vector, top_k=top_k)

        # Resolve chunks and filter by score
        results = []
        for vector_id, chunk_id, score in raw_results:
            if score < score_threshold:
                continue

            chunk = self._pipeline.get_chunk(chunk_id)
            if not chunk:
                continue

            results.append({
                "text": chunk.text,
                "file_name": chunk.metadata.file_name,
                "score": round(float(score), 4),
                "chunk_type": chunk.metadata.chunk_type,
                "section_title": chunk.metadata.section_title,
                "tags": chunk.metadata.tags,
                "chunk_id": chunk.chunk_id,
            })

        logger.info(
            f"Search for '{query[:60]}...' → "
            f"{len(results)} results (top_k={top_k}, threshold={score_threshold})"
        )
        return results

    def multi_search(
        self,
        queries: List[str],
        top_k: int = SEARCH_TOP_K_DEFAULT,
        score_threshold: float = SEARCH_SCORE_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """
        Perform multiple searches and merge results, deduplicating by chunk_id.
        Useful for cross-tournament or multi-aspect queries.

        Args:
            queries: List of search queries.
            top_k: Max results per query.
            score_threshold: Minimum similarity.

        Returns:
            Merged, deduplicated list of results sorted by score.
        """
        self._ensure_initialized()
        seen_chunks = set()
        all_results = []

        for q in queries:
            results = self.search(q, top_k=top_k, score_threshold=score_threshold)
            for r in results:
                if r["chunk_id"] not in seen_chunks:
                    seen_chunks.add(r["chunk_id"])
                    all_results.append(r)

        # Sort by score descending
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results

    def get_context_text(
        self,
        query: str,
        top_k: int = 8,
        score_threshold: float = SEARCH_SCORE_THRESHOLD,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Get formatted context text for RAG prompt construction.

        Args:
            query: User question.
            top_k: Number of chunks to retrieve.
            score_threshold: Minimum similarity.

        Returns:
            (context_text, sources) — ready for LLM prompt injection.
        """
        results = self.search(query, top_k=top_k, score_threshold=score_threshold)

        if not results:
            return "", []

        context_parts = []
        sources = []

        for r in results:
            context_parts.append(
                f"[Source: {r['file_name']} | Type: {r['chunk_type']} | Score: {r['score']}]\n{r['text']}"
            )
            sources.append({
                "file": r["file_name"],
                "score": r["score"],
                "type": r["chunk_type"],
                "title": r["section_title"],
            })

        context_text = "\n\n---\n\n".join(context_parts)
        return context_text, sources

    def multi_query_context(
        self,
        queries: List[str],
        top_k: int = 8,
        score_threshold: float = SEARCH_SCORE_THRESHOLD,
        max_total: int = 30,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Get context from multiple search queries, merged and deduplicated.
        Ensures diverse coverage by including results from each query.

        Args:
            queries: List of search queries.
            top_k: Max results per query.
            score_threshold: Minimum similarity.
            max_total: Maximum total results to include.

        Returns:
            (context_text, sources)
        """
        results = self.multi_search(queries, top_k=top_k, score_threshold=score_threshold)
        results = results[:max_total]

        if not results:
            return "", []

        context_parts = []
        sources = []

        for r in results:
            context_parts.append(
                f"[Source: {r['file_name']} | Type: {r['chunk_type']} | Score: {r['score']}]\n{r['text']}"
            )
            sources.append({
                "file": r["file_name"],
                "score": r["score"],
                "type": r["chunk_type"],
                "title": r["section_title"],
            })

        context_text = "\n\n---\n\n".join(context_parts)
        return context_text, sources

    # ────────────────────────────────────────────────────────
    # INDEX MANAGEMENT
    # ────────────────────────────────────────────────────────

    def build_index(self, force_rebuild: bool = False) -> Dict[str, int]:
        """
        Build (or rebuild) the FAISS index from the Cricket Data embeddings.

        If index already exists and force_rebuild=False, only new
        (non-duplicate) content is added incrementally.

        Args:
            force_rebuild: If True, wipe and rebuild from scratch.

        Returns:
            Ingestion statistics dict.
        """
        self._ensure_initialized()

        if force_rebuild:
            logger.warning("Force rebuild requested — resetting index")
            self._store.reset()
            # Also clear chunks.json so dedup starts fresh
            chunks_path = Path(INDEX_DIR) / "chunks.json"
            if chunks_path.exists():
                chunks_path.unlink()
                logger.info("Cleared chunks.json for full rebuild")
            self._pipeline = IngestionPipeline(
                embedding_generator=self._embedder,
                vector_store=self._store,
                chunker=self._chunker,
            )

        logger.info("Building index from Cricket World Cup dataset...")
        stats = self._pipeline.ingest_cricket_dataset(
            tags=["cricket", "world_cup"]
        )

        logger.info(
            f"Index build complete — "
            f"{stats.get('chunks_created', 0)} new chunks, "
            f"{stats.get('vectors_added', 0)} new vectors"
        )
        return stats

    def add_document(
        self,
        file_path: str,
        source_type: str = "document",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Incrementally add a single document to the index.
        Useful for adding new World Cup data without full rebuild.

        Args:
            file_path: Path to the document file.
            source_type: Type of source document.
            tags: Optional tags.

        Returns:
            Ingestion stats.
        """
        self._ensure_initialized()

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        tags = tags or ["cricket", "world_cup"]
        result = self._pipeline.ingest_file(
            file_path=path,
            source_type=source_type,
            tags=tags,
        )

        # Persist
        self._store.save()
        self._pipeline._save_chunks()
        logger.info(f"Added '{path.name}' → {result.get('vectors_added', 0)} vectors")
        return result

    # ────────────────────────────────────────────────────────
    # UTILITIES
    # ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._initialized:
            return {"initialized": False}

        return {
            "initialized": True,
            "total_vectors": self._store.total_vectors if self._store else 0,
            "total_chunks": self._pipeline.total_chunks if self._pipeline else 0,
            "index_dir": str(self._index_dir),
            "index_file_exists": (self._index_dir / "faiss.index").exists(),
            "chunks_file_exists": (self._index_dir / "chunks.json").exists(),
            "embedding_model": self._embedder._model_name if self._embedder else None,
            "embedding_dimension": self._embedder.dimension if self._embedder else None,
        }

    @property
    def is_ready(self) -> bool:
        """Check if index is initialized and has vectors."""
        return self._initialized and self._store is not None and self._store.total_vectors > 0

    @property
    def total_vectors(self) -> int:
        return self._store.total_vectors if self._store else 0

    @property
    def total_chunks(self) -> int:
        return self._pipeline.total_chunks if self._pipeline else 0
