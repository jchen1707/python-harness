"""Service layer — business logic and orchestration.

Controllers (`api/`) call services; services call the AI layer (`ai/`), repositories
(`repositories/`) and external capabilities, apply domain rules, and drive workflows.

Recommended layout:
  services/<domain>.py    — domain services

Applied AI is NOT here. Retrieval, reranking, agent orchestration and their evals live
in `ai/`, which is its own layer between services and repositories. See ai/CLAUDE.md.

See docs/architecture.md -> Layering.
"""
