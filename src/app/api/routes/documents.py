"""Documents controller — transport only (architecture §1).

Parses/validates input, calls one service, shapes the response. No business logic,
no direct repository/SDK access.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_document_service
from app.repositories.documents import Document, Hit
from app.services.documents import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

ServiceDep = Annotated[DocumentService, Depends(get_document_service)]


class DocumentCreate(BaseModel):
    """Request body for creating a document."""

    text: str = Field(min_length=1)


class DocumentOut(BaseModel):
    """Response model for a document."""

    id: int
    text: str

    @classmethod
    def from_domain(cls, doc: Document) -> DocumentOut:
        return cls(id=doc.id, text=doc.text)


class HitOut(BaseModel):
    """Response model for a single search result."""

    document: DocumentOut
    score: int

    @classmethod
    def from_domain(cls, hit: Hit) -> HitOut:
        return cls(document=DocumentOut.from_domain(hit.document), score=hit.score)


class SearchResponse(BaseModel):
    """Response model for a search query."""

    query: str
    results: list[HitOut]


@router.post("", response_model=DocumentOut, status_code=201)
async def create_document(body: DocumentCreate, service: ServiceDep) -> DocumentOut:
    doc = await service.add(body.text)
    return DocumentOut.from_domain(doc)


# Declared before "/{doc_id}" so the literal path wins over the int path param.
@router.get("/search", response_model=SearchResponse)
async def search_documents(
    service: ServiceDep,
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int | None, Query(ge=1)] = None,
) -> SearchResponse:
    hits = await service.search(q, limit)
    return SearchResponse(query=q, results=[HitOut.from_domain(h) for h in hits])


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: int, service: ServiceDep) -> DocumentOut:
    doc = await service.get(doc_id)
    return DocumentOut.from_domain(doc)
