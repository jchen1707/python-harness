"""FastAPI dependency providers (architecture §1, §5).

Expose request-scoped access to services wired at app startup. Controllers depend on
these, not on concrete construction.
"""

from __future__ import annotations

from fastapi import Request

from app.services.documents import DocumentService


def get_document_service(request: Request) -> DocumentService:
    """Return the ``DocumentService`` wired into ``app.state`` at startup."""
    service: DocumentService = request.app.state.document_service
    return service
