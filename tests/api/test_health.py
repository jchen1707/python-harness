"""Unit tests for the `/healthz` route.

Test through `httpx.AsyncClient` with an `ASGITransport` against the app from
`create_app(test_settings)` — no server started. Plan: BAC-4 test-plan.md.
"""

from __future__ import annotations

import httpx
from structlog.testing import capture_logs

from app.core.config import Settings
from app.main import create_app


def _test_settings() -> Settings:
    # pydantic coerces a str into the SecretStr field at runtime.
    return Settings(database_url="postgresql://test", voyage_api_key="test-key")  # type: ignore[arg-type]


async def test_health_returns_200() -> None:
    app = create_app(_test_settings())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_response_is_pydantic_model() -> None:
    app = create_app(_test_settings())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert set(response.json().keys()) == {"status"}


async def test_health_route_logs_noun_verb() -> None:
    app = create_app(_test_settings())
    transport = httpx.ASGITransport(app=app)

    with capture_logs() as logs:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/healthz")

    health_events = [e for e in logs if e["event"] == "health.checked"]
    assert len(health_events) == 1
    assert health_events[0]["status"] == "ok"


def test_main_has_no_module_level_app() -> None:
    """The factory pattern means importing `app.main` must not construct the app.

    A module-level `app = create_app()` would read the environment at import and break
    test collection. This pins that decision.
    """
    import app.main

    assert not hasattr(app.main, "app")
