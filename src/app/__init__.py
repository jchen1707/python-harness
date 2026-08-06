"""python-harness application package (scaffold).

This is a harness, not an implementation. Each subpackage carries its own `CLAUDE.md`
with the conventions that govern it; read that file before changing code in it.

  api/           HTTP edge — transport only
  services/      business logic and orchestration
  ai/            applied AI — retrieval, reranking, agents, evals
  repositories/  data access behind protocols
  core/          cross-cutting: Settings, logging, metrics, errors

Still to write: `config.py` (the only reader of the environment) and `main.py` (the
app factory).

Layering, and every rule that spans directories: docs/architecture.md.
"""

__version__ = "0.1.0"
