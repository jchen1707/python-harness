"""HTTP layer (FastAPI): routers and route modules. Transport only, no business logic.

Calls `services/`. Must not import `repositories/` or touch a database session.

Conventions: api/AGENTS.md. Cross-cutting rules: docs/architecture.md.
"""
