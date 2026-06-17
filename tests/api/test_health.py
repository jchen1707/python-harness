"""Offline unit tests for GET /healthz (architecture §8)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings


def test_healthz_returns_ok_and_app_name(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": get_settings().app_name}
