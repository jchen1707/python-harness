"""Notes repository — data access behind a protocol (architecture §2, §8).

``Note`` is the persisted model; ``NoteRepository`` is the storage-agnostic protocol the
service depends on; ``InMemoryNoteRepository`` is the offline/dev impl used by unit tests
and the smoke app. A DB-backed impl can be added later without touching the service.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from pydantic import BaseModel


class Note(BaseModel):
    """A persisted note."""

    id: int
    text: str


class NoteRepository(Protocol):
    """Storage-agnostic notes access. Services depend on this protocol, not a class."""

    async def add(self, text: str) -> Note: ...
    async def list(self) -> list[Note]: ...
    async def get(self, note_id: int) -> Note | None: ...


class InMemoryNoteRepository:
    """In-memory notes store: dict + monotonic id counter, Lock-guarded (§13).

    FastAPI handlers run concurrently on one event loop; the lock guards the
    read-modify-write on the counter so concurrent adds never collide or lose updates.
    """

    def __init__(self) -> None:
        self._notes: dict[int, Note] = {}
        self._next_id: int = 1
        self._lock: asyncio.Lock = asyncio.Lock()

    async def add(self, text: str) -> Note:
        async with self._lock:
            note = Note(id=self._next_id, text=text)
            self._notes[note.id] = note
            self._next_id += 1
            return note

    async def list(self) -> list[Note]:
        async with self._lock:
            return [self._notes[i] for i in sorted(self._notes)]

    async def get(self, note_id: int) -> Note | None:
        async with self._lock:
            return self._notes.get(note_id)
