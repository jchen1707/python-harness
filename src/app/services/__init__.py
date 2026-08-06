"""Service layer — business logic and orchestration. Decides what happens.

Imports `ai/`, `repositories/` and `core/`. Must not import `api/`.

Applied AI is NOT here. Retrieval, reranking, agent orchestration and their evals live
in `ai/`, a layer of its own between services and repositories.

Recommended layout:
  services/<domain>.py    — domain services

Conventions: services/CLAUDE.md. Cross-cutting rules: docs/architecture.md.
"""
