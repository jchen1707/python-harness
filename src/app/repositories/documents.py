"""Document repository — data access behind a Protocol (architecture §2).

The in-memory implementation keeps unit tests offline and serves as a quickstart; a
real implementation (e.g. Postgres / pgvector) can be substituted without touching
the service layer, because the service depends on the ``DocumentRepository`` protocol.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class Document(BaseModel):
    """A stored document."""

    id: int
    text: str


class Hit(BaseModel):
    """A search result: a document and its keyword-match score."""

    document: Document
    score: int = Field(ge=0)


class DocumentRepository(Protocol):
    """Storage-agnostic document access. Depend on this, not a concrete class."""

    async def add(self, text: str) -> Document: ...

    async def get(self, doc_id: int) -> Document | None: ...

    async def search(self, terms: list[str], limit: int) -> list[Hit]: ...


class InMemoryDocumentRepository:
    """In-memory ``DocumentRepository`` for tests and quickstart."""

    def __init__(self, seed: list[str] | None = None) -> None:
        self._docs: dict[int, Document] = {}
        self._next_id = 1
        for text in seed or []:
            self._insert(text)

    def _insert(self, text: str) -> Document:
        doc = Document(id=self._next_id, text=text)
        self._docs[doc.id] = doc
        self._next_id += 1
        return doc

    async def add(self, text: str) -> Document:
        return self._insert(text)

    async def get(self, doc_id: int) -> Document | None:
        return self._docs.get(doc_id)

    async def search(self, terms: list[str], limit: int) -> list[Hit]:
        hits: list[Hit] = []
        for doc in self._docs.values():
            haystack = doc.text.lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                hits.append(Hit(document=doc, score=score))
        # Rank by score desc, then id asc for a stable order.
        hits.sort(key=lambda h: (-h.score, h.document.id))
        return hits[:limit]
