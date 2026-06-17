---
description: Review recent changes against the architectural standards
---

Perform a standards-adherence review of the current / uncommitted changes.

1. Run `git status` and `git diff` (and `git diff --cached`) to see what changed.
2. Read `docs/architecture.md` and the "Architectural standards" + "Definition of
   Done" sections of `CLAUDE.md`.
3. For each changed file, check it against the standards:
   - Correct layer (`api` / `agents` / `rag` / `core` / `config`) and no cross-layer
     leaks or reverse dependencies.
   - Async-first for I/O; Pydantic models for all external I/O.
   - Dependencies behind interfaces/protocols with swappable implementations.
   - Config/secrets via `app.config.Settings` — no hardcoded secrets, no scattered
     env reads in logic.
   - Public functions typed; `disallow_untyped_defs` satisfied.
   - Structlog logging; no `print()`; no swallowed exceptions.
   - Tests cover new behavior; no network in unit tests.
   - The approved stack is used (FastAPI, LangGraph + langchain-anthropic, Voyage
     embeddings, Postgres + pgvector). New frameworks require updating CLAUDE.md +
     docs/architecture.md first.

Report findings as a per-standard PASS/FAIL checklist with file:line evidence.
Propose fixes for any FAILs. Do not apply fixes unless asked.