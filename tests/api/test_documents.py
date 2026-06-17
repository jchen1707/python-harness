"""API-layer unit tests (offline — FastAPI TestClient against the app factory)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_document(client: TestClient) -> None:
    created = client.post("/documents", json={"text": "brand new note"})
    assert created.status_code == 201
    doc_id = created.json()["id"]

    fetched = client.get(f"/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.json()["text"] == "brand new note"


def test_get_missing_returns_404(client: TestClient) -> None:
    assert client.get("/documents/4242").status_code == 404


def test_search_returns_ranked_results(client: TestClient) -> None:
    resp = client.get("/documents/search", params={"q": "service"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "service"
    assert len(body["results"]) >= 1
    assert "score" in body["results"][0]


def test_search_requires_query(client: TestClient) -> None:
    assert client.get("/documents/search").status_code == 422
