"""Application factory — the composition root.

`create_app` is the one place that constructs `Settings` for the server. Tests inject
`settings` so they do not read the environment. There is no module-level `app`, so importing
`app.main` does not read the environment or construct `Settings`.

Run with `uv run uvicorn app.main:create_app --factory --reload`.

Conventions: docs/architecture.md (layering, app factory).
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Constructs `Settings` only when none is passed in, so tests inject settings and never
    read the environment. No service or repository may construct `Settings`.
    """
    # Required fields have no default, but pydantic-settings reads them from the
    # environment at construction, so Settings() is valid at runtime.
    settings = settings or Settings()  # type: ignore[call-arg]
    configure_logging(settings.log_level)
    app = FastAPI(title="python-harness")
    app.add_middleware(RequestIdMiddleware)
    app.include_router(api_router)
    return app
