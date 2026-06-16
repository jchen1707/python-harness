"""Service layer — business logic and orchestration.

Controllers (`api/`) call services; services call repositories (`repositories/`)
and external capabilities, apply domain rules, and drive workflows.

Recommended layout:
  services/agents/        — agent orchestration (LangGraph + langchain-anthropic)
  services/retrieval.py   — RAG retrieval orchestration (compose embedder + store)
  services/<domain>.py    — domain services

See docs/architecture.md -> Layering.
"""
