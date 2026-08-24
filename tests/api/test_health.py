"""Health behaviour at the HTTP edge."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings


@pytest.fixture
def application(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/support")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    sys.modules.pop("app.main", None)
    module = importlib.import_module("app.main")
    return cast(FastAPI, module.app)


async def test_health_reports_that_the_application_is_up(application: FastAPI) -> None:
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_request_id_is_bound_to_request_logs(
    application: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    request_id = "test-request-123"
    transport = ASGITransport(app=application)
    capsys.readouterr()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz", headers={"X-Request-ID": request_id})

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    completed = next(event for event in events if event["event"] == "request.completed")
    assert completed["request_id"] == request_id
    assert response.status_code == 200


async def test_development_request_logs_are_human_readable(
    application: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.main import create_app

    settings = cast(Settings, application.state.settings)
    development_app = create_app(settings, development=True)
    transport = ASGITransport(app=development_app)
    capsys.readouterr()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    output = capsys.readouterr().out
    assert "request.completed" in output
    assert not output.lstrip().startswith("{")
    assert response.status_code == 200
