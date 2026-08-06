"""Repository layer — data access behind protocols. No business rules.

Imports `core` only. `services/` and `ai/` call in; this layer never calls out to them.

Recommended layout:
  repositories/vector.py      — VectorStore (pgvector + in-memory) behind a protocol
  repositories/embeddings.py  — Embedder (Voyage + Fake) behind a protocol
  repositories/<entity>.py    — relational data access

Conventions: repositories/CLAUDE.md. Cross-cutting rules: docs/architecture.md.
"""
