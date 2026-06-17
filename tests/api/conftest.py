"""Shared fixtures for api-layer tests.

Each test gets a fresh in-memory note service by overriding the ``get_note_service``
dependency, so tests never share state and stay hermetic (architecture §8).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_note_service
from app.main import create_app
from app.repositories.notes import InMemoryNoteRepository
from app.services.notes import NoteService


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient whose /notes routes resolve to a fresh in-memory service per test."""
    application = create_app()
    service = NoteService(InMemoryNoteRepository())
    application.dependency_overrides[get_note_service] = lambda: service
    with TestClient(application) as test_client:
        yield test_client
