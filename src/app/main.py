"""FastAPI application factory and lifespan (architecture §1, §5, §6).

Wires concrete implementations at composition time and maps domain errors to HTTP
responses. ``uv run uvicorn app.main:app --reload`` serves the module-level ``app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import documents
from app.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.core.logging import configure_logging
from app.repositories.documents import InMemoryDocumentRepository
from app.services.documents import DocumentService

_SEED_DOCS = [
    "controller service repository layering",
    "retrieval augmented generation with pgvector",
    "async first fastapi service",
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app, wiring concrete implementations at composition time."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = InMemoryDocumentRepository(seed=_SEED_DOCS)
        app.state.document_service = DocumentService(
            repository,
            default_limit=settings.search_default_limit,
            max_limit=settings.search_max_limit,
        )
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(documents.router)

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
