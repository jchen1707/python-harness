"""Aggregate API router — includes one router per resource.

The app factory mounts this aggregate. Adding a route file means registering its router
here. This sets the pattern for later route files.

Conventions: api/CLAUDE.md.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
