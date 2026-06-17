"""Offline unit tests for InMemoryNoteRepository (architecture §8).

Uses the real in-memory repository directly — no fakes needed. Async tests run under
pytest-asyncio's ``asyncio_mode=auto`` (no explicit marks required).
"""

from __future__ import annotations

import asyncio

from app.repositories.notes import InMemoryNoteRepository


async def test_add_assigns_monotonic_ids() -> None:
    repo = InMemoryNoteRepository()
    first = await repo.add("a")
    second = await repo.add("b")
    third = await repo.add("c")
    assert first.id == 1
    assert second.id == 2
    assert third.id == 3
    assert first.text == "a"


async def test_list_returns_insertion_order_and_empty_initially() -> None:
    repo = InMemoryNoteRepository()
    assert await repo.list() == []
    await repo.add("first")
    await repo.add("second")
    notes = await repo.list()
    assert [n.text for n in notes] == ["first", "second"]


async def test_get_returns_note_or_none() -> None:
    repo = InMemoryNoteRepository()
    created = await repo.add("hello")
    assert await repo.get(created.id) == created
    assert await repo.get(999) is None


async def test_concurrent_adds_yield_unique_ids() -> None:
    repo = InMemoryNoteRepository()
    n = 50
    notes = await asyncio.gather(*(repo.add(f"n{i}") for i in range(n)))
    ids = {note.id for note in notes}
    assert len(ids) == n  # no collisions — the Lock guards the counter (§13)
    assert ids == set(range(1, n + 1))
