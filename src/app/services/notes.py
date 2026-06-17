"""Notes service — business logic over the NoteRepository protocol (architecture §1).

The controller calls this; this calls the repository. Depends on the protocol, not the
in-memory class, so storage can be swapped without touching business logic (§2).
"""

from __future__ import annotations

import structlog

from app.core.errors import EmptyNoteError, NoteNotFoundError
from app.repositories.notes import Note, NoteRepository


class NoteService:
    """Domain operations on notes, delegating persistence to a repository."""

    def __init__(self, repo: NoteRepository) -> None:
        self._repo = repo
        self._log = structlog.get_logger().bind(component="note_service")

    async def create_note(self, text: str) -> Note:
        """Validate, strip, persist, and return a new note.

        Raises EmptyNoteError if the text is empty or whitespace-only after stripping.
        """
        stripped = text.strip()
        if not stripped:
            raise EmptyNoteError("note text must not be empty")
        note = await self._repo.add(stripped)
        self._log.info("note_created", note_id=note.id, text=note.text)
        return note

    async def list_notes(self) -> list[Note]:
        """Return all notes in insertion order."""
        return await self._repo.list()

    async def get_note(self, note_id: int) -> Note:
        """Return one note; raise NoteNotFoundError if it does not exist."""
        note = await self._repo.get(note_id)
        if note is None:
            raise NoteNotFoundError(note_id)
        return note
