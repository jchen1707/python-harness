"""Cross-cutting concerns: Settings, structlog, Prometheus metrics, error types.

Every layer may import `core`. It imports none of them — a `core` module that imports
a service creates a cycle.

Conventions: core/AGENTS.md. Cross-cutting rules: docs/architecture.md.
"""
