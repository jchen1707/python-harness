"""Offline unit tests for the /notes routes (architecture §8).

The ``client`` fixture overrides the note service with a fresh in-memory repo per test,
so each test starts from an empty store. Error mapping follows the controller contract:
empty/whitespace text → 400 (domain), missing field → 422 (Pydantic boundary), unknown
id → 404.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_note_returns_201_with_body(client: TestClient) -> None:
    response = client.post("/notes", json={"text": "hello"})
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["text"] == "hello"


def test_list_notes_after_creates(client: TestClient) -> None:
    client.post("/notes", json={"text": "first"})
    client.post("/notes", json={"text": "second"})
    response = client.get("/notes")
    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 2
    assert [n["text"] for n in notes] == ["first", "second"]


def test_get_note_existing_and_missing(client: TestClient) -> None:
    created = client.post("/notes", json={"text": "x"}).json()
    note_id = created["id"]
    ok = client.get(f"/notes/{note_id}")
    assert ok.status_code == 200
    assert ok.json()["text"] == "x"
    missing = client.get("/notes/999")
    assert missing.status_code == 404


def test_create_note_empty_text_returns_400(client: TestClient) -> None:
    """Empty/whitespace text passes Pydantic (a valid str) but fails domain validation → 400."""
    assert client.post("/notes", json={"text": ""}).status_code == 400
    assert client.post("/notes", json={"text": "   "}).status_code == 400


def test_create_note_missing_field_returns_422(client: TestClient) -> None:
    """A missing request field fails Pydantic validation at the boundary → 422."""
    assert client.post("/notes", json={}).status_code == 422


def test_empty_store_lists_as_empty_array(client: TestClient) -> None:
    response = client.get("/notes")
    assert response.status_code == 200
    assert response.json() == []
