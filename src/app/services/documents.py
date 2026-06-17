"""Document service — business logic over the ``DocumentRepository`` (architecture §1).

Owns query parsing and limit bounds; delegates storage/matching to the injected
repository protocol. Knows nothing about HTTP.
"""

from __future__ import annotations

import structlog

from app.core.errors import NotFoundError
from app.repositories.documents import Document, DocumentRepository, Hit

log = structlog.get_logger(__name__)


class DocumentService:
    """Add, fetch, and search documents behind the repository protocol."""

    def __init__(
        self,
        repository: DocumentRepository,
        *,
        default_limit: int,
        max_limit: int,
    ) -> None:
        self._repo = repository
        self._default_limit = default_limit
        self._max_limit = max_limit

    async def add(self, text: str) -> Document:
        doc = await self._repo.add(text)
        log.info("document_added", doc_id=doc.id)
        return doc

    async def get(self, doc_id: int) -> Document:
        doc = await self._repo.get(doc_id)
        if doc is None:
            raise NotFoundError(f"document {doc_id} not found")
        return doc

    async def search(self, query: str, limit: int | None = None) -> list[Hit]:
        terms = query.lower().split()
        if not terms:
            return []
        bounded = self._bounded_limit(limit)
        hits = await self._repo.search(terms, bounded)
        log.info("document_search", terms=terms, limit=bounded, results=len(hits))
        return hits

    def _bounded_limit(self, limit: int | None) -> int:
        if limit is None:
            return self._default_limit
        return max(1, min(limit, self._max_limit))
