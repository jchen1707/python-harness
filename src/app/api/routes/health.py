"""Health-check route — `/healthz` returns a Pydantic model.

The route is `def` (no I/O). It emits one structured log named `noun.verb` in the past tense
with a bound key, not a formatted string. The edge-bound `request_id` surfaces on this log
line because the middleware bound it and anyio copies contextvars into the worker thread
that runs a sync route.

Conventions: api/CLAUDE.md.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health-check response body."""

    status: str = "ok"


@router.get("/healthz", response_model=HealthResponse)
def check_health() -> HealthResponse:
    """Return the application health status."""
    logger.info("health.checked", status="ok")
    return HealthResponse()
