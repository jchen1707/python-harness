"""FastAPI dependency providers — wiring between app.state and handlers (architecture §2).

Concrete implementations are constructed once in the app factory lifespan and stored on
``app.state``; these providers read them back so handlers depend on the injected service,
not on a global. Tests override ``get_note_service`` to inject a fresh in-memory repo.
"""

from __future__ import annotations

from fastapi import Request

from app.services.notes import NoteService


def get_note_service(request: Request) -> NoteService:
    """Return the NoteService built at startup and stored on app.state."""
    service: NoteService = request.app.state.note_service
    return service
