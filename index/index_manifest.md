# DIE Knowledge Base Index

- Embedding Model: sentence-transformers/all-MiniLM-L6-v2
- Vector Dimension: 384
- Index Type: HNSWFlat
- Distance Metric: Cosine
- Total Documents: 316
- Total Chunks: 1082
- Total Vectors: 1082
- Last Indexed: 2026-02-10T10:52:26.723108+00:00
- Version: v1.0

## Index Configuration

| Parameter | Value |
|-----------|-------|
| HNSW M | 32 |
| EF Construction | 200 |
| EF Search | 128 |
| Chunk Size (target) | 200-400 tokens |
| Chunk Overlap | 30 tokens |
| Deduplication | SHA-256 hash-based |

## Deduplication

- Unique content hashes: 1082
- Guarantees: Safe re-indexing, no duplicated vectors, incremental updates

## Storage

| File | Purpose |
|------|---------|
| faiss.index | Binary FAISS vector index |
| chunks.json | Chunk ID → text + metadata mapping |
| vectors.json | Vector ID → chunk ID mapping |
| metadata.md | Human-readable metadata summary |
| index_manifest.md | This file — index config & stats |
