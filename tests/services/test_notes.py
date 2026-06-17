"""Offline unit tests for NoteService (architecture §8).

The service is constructed over the real in-memory repository (the protocol's offline
impl); one test also uses a hand-written fake to prove the service depends on the
``NoteRepository`` protocol, not the concrete class (§2).
"""

from __future__ import annotations

import pytest

from app.core.errors import EmptyNoteError, NoteNotFoundError
from app.repositories.notes import InMemoryNoteRepository, Note
from app.services.notes import NoteService


async def test_create_note_strips_text() -> None:
    service = NoteService(InMemoryNoteRepository())
    note = await service.create_note("  hi  ")
    assert note.text == "hi"
    assert note.id == 1


async def test_create_note_rejects_empty_text() -> None:
    service = NoteService(InMemoryNoteRepository())
    with pytest.raises(EmptyNoteError):
        await service.create_note("")


async def test_create_note_rejects_whitespace_only_text() -> None:
    service = NoteService(InMemoryNoteRepository())
    with pytest.raises(EmptyNoteError):
        await service.create_note("   \t  ")


async def test_get_note_raises_when_missing() -> None:
    service = NoteService(InMemoryNoteRepository())
    with pytest.raises(NoteNotFoundError):
        await service.get_note(42)


async def test_get_note_returns_existing() -> None:
    service = NoteService(InMemoryNoteRepository())
    created = await service.create_note("hello")
    fetched = await service.get_note(created.id)
    assert fetched == created


async def test_list_notes_returns_all() -> None:
    service = NoteService(InMemoryNoteRepository())
    await service.create_note("a")
    await service.create_note("b")
    notes = await service.list_notes()
    assert [n.text for n in notes] == ["a", "b"]


async def test_service_accepts_protocol_compliant_fake() -> None:
    """The service depends on the NoteRepository protocol, not the concrete class."""

    class _FakeRepo:
        async def add(self, text: str) -> Note:
            return Note(id=1, text=text)

        async def list(self) -> list[Note]:
            return [Note(id=1, text="x")]

        async def get(self, note_id: int) -> Note | None:
            return Note(id=note_id, text="x") if note_id == 1 else None

    service = NoteService(_FakeRepo())
    assert (await service.create_note("x")).id == 1
    assert await service.get_note(1) == Note(id=1, text="x")
    with pytest.raises(NoteNotFoundError):
        await service.get_note(2)
