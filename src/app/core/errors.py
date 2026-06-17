"""Domain error types, mapped to HTTP responses in the ``api`` layer (architecture §6).

No business logic here — just typed errors that services raise and controllers
translate into status codes. Keeping them in ``core`` avoids reverse dependencies.
"""

from __future__ import annotations


class NoteError(Exception):
    """Base class for note-domain errors."""


class EmptyNoteError(NoteError):
    """Raised when note text is empty or whitespace-only after stripping."""


class NoteNotFoundError(NoteError):
    """Raised when a requested note id does not exist."""

    def __init__(self, note_id: int) -> None:
        super().__init__(f"note not found: id={note_id}")
        self.note_id = note_id
