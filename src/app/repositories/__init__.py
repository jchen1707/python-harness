"""Repository layer — data access behind interfaces.

Services (`services/`) call repositories; repositories talk to storage and external
APIs and expose protocols (never business logic).

Recommended layout:
  repositories/vector.py      — VectorStore (pgvector + in-memory) behind a protocol
  repositories/embeddings.py  — Embedder (Voyage + Fake) behind a protocol
  repositories/<entity>.py    — relational data access

See docs/architecture.md -> Layering and -> Interfaces over implementations.
"""
