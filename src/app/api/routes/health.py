"""Expose the application health check."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Describe an application that can serve requests."""

    status: Literal["ok"]


@router.get("/healthz", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Report that the application is up."""
    return HealthResponse(status="ok")
