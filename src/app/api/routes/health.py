"""Health check route — transport only (architecture §1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness probe body."""

    status: str
    app: str


@router.get("/healthz", response_model=HealthResponse)
async def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Report liveness and the configured app name."""
    return HealthResponse(status="ok", app=settings.app_name)
