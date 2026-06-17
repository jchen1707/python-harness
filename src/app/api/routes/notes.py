"""Notes HTTP routes — transport only (architecture §1).

Parse/validate input with Pydantic, call the injected NoteService, shape responses.
Service domain errors are mapped to HTTP status codes here; no business logic lives in
this layer.

Error mapping:
  - missing/invalid request field → Pydantic 422 (at the boundary)
  - empty/whitespace-only text      → EmptyNoteError → 400 (domain validation, §4/§6)
  - unknown note id                 → NoteNotFoundError → 404
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_note_service
from app.core.errors import EmptyNoteError, NoteNotFoundError
from app.repositories.notes import Note
from app.services.notes import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])


class CreateNoteRequest(BaseModel):
    """Request body for creating a note. Structural validation only (presence/type)."""

    text: str


@router.post("", response_model=Note, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: CreateNoteRequest,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> Note:
    """Create a note from the request text."""
    try:
        return await service.create_note(payload.text)
    except EmptyNoteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[Note])
async def list_notes(service: Annotated[NoteService, Depends(get_note_service)]) -> list[Note]:
    """List all notes in insertion order."""
    return await service.list_notes()


@router.get("/{note_id}", response_model=Note)
async def get_note(
    note_id: int,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> Note:
    """Fetch one note by id; 404 if it does not exist."""
    try:
        return await service.get_note(note_id)
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
