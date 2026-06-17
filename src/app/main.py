"""FastAPI app factory + lifespan (architecture §1, §2).

``create_app()`` wires concrete implementations (in-memory repo + service) onto
``app.state`` at startup and includes the routers. Handlers resolve dependencies via
``app.api.deps``, which read from ``app.state`` — so the app is the single composition
root. The module-level ``app`` lets uvicorn import ``app.main:app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, notes
from app.config import get_settings
from app.core.logging import configure_logging
from app.repositories.notes import InMemoryNoteRepository
from app.services.notes import NoteService


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: configure logging and build the in-memory notes service on app.state."""
    configure_logging()
    app.state.note_service = NoteService(InMemoryNoteRepository())
    yield


def create_app() -> FastAPI:
    """Construct the FastAPI app: lifespan + routers, no per-call wiring."""
    app = FastAPI(title=get_settings().app_name, lifespan=_lifespan)
    app.include_router(health.router)
    app.include_router(notes.router)
    return app


app = create_app()
