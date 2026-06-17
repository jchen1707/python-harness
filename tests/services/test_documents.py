"""Service-layer unit tests (offline — in-memory repository, no network/DB)."""

from __future__ import annotations

import pytest

from app.core.errors import NotFoundError
from app.repositories.documents import InMemoryDocumentRepository
from app.services.documents import DocumentService


def _service() -> DocumentService:
    repo = InMemoryDocumentRepository(seed=["alpha beta", "alpha alpha gamma", "delta"])
    return DocumentService(repo, default_limit=5, max_limit=10)


async def test_search_ranks_by_match_count() -> None:
    hits = await _service().search("alpha")
    assert [h.document.id for h in hits] == [2, 1]
    assert hits[0].score == 2


async def test_search_empty_query_returns_nothing() -> None:
    assert await _service().search("   ") == []


async def test_search_respects_max_limit() -> None:
    hits = await _service().search("alpha", limit=100)
    assert len(hits) <= 10


async def test_get_missing_raises_not_found() -> None:
    with pytest.raises(NotFoundError):
        await _service().get(999)


async def test_add_then_get_roundtrip() -> None:
    service = _service()
    doc = await service.add("new document")
    fetched = await service.get(doc.id)
    assert fetched.text == "new document"
