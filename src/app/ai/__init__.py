"""Applied-AI capability layer: retrieval, reranking, agent orchestration, evals.

Imports `repositories/` and `core/`. Must never import `services/` or `api/` — services
call into this layer, not the reverse.

  ai/retrieval/  — chunking, embedding, hybrid search, filtering
  ai/reranking/  — cross-encoders, fusion, diversity
  ai/agents/     — LangGraph orchestration
  ai/evals/      — offline measurement; may import any layer, nothing imports it

Conventions: ai/CLAUDE.md, which also explains why this is separate from services/.
Cross-cutting rules: docs/architecture.md.
"""
