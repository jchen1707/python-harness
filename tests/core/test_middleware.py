"""Unit tests for `app.core.middleware.RequestIdMiddleware`.

Test the middleware directly against a fake inner ASGI app — no HTTP client. The fake
app records the contextvars snapshot during the request. Plan: BAC-4 test-plan.md.
"""

from __future__ import annotations

from typing import Any

import structlog
from starlette.types import Message, Receive, Scope, Send
from structlog.typing import EventDict

from app.core.middleware import RequestIdMiddleware


def _scope(headers: dict[str, str] | None = None) -> Scope:
    raw = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return {"type": "http", "headers": raw}


class FakeASGIApp:
    """Records the `request_id` seen in contextvars during the request."""

    def __init__(self) -> None:
        self.seen: dict[str, object] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.seen = dict(structlog.contextvars.get_contextvars())
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b""})


async def _send_noop(message: Message) -> None:
    del message


async def _receive_empty() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


async def test_middleware_binds_request_id_when_absent() -> None:
    inner = FakeASGIApp()
    middleware = RequestIdMiddleware(inner)

    await middleware(_scope(), _receive_empty, _send_noop)

    rid = inner.seen.get("request_id")
    assert isinstance(rid, str)
    assert rid != ""


async def test_middleware_preserves_incoming_request_id() -> None:
    inner = FakeASGIApp()
    middleware = RequestIdMiddleware(inner)

    await middleware(_scope({"X-Request-ID": "rid-abc"}), _receive_empty, _send_noop)

    assert inner.seen.get("request_id") == "rid-abc"


async def test_middleware_generates_id_for_empty_header() -> None:
    inner = FakeASGIApp()
    middleware = RequestIdMiddleware(inner)

    await middleware(_scope({"X-Request-ID": "   "}), _receive_empty, _send_noop)

    rid = inner.seen.get("request_id")
    assert isinstance(rid, str)
    assert rid.strip() != ""


async def test_middleware_clears_contextvars_after_request() -> None:
    inner = FakeASGIApp()
    middleware = RequestIdMiddleware(inner)

    await middleware(_scope({"X-Request-ID": "rid-abc"}), _receive_empty, _send_noop)

    assert "request_id" not in structlog.contextvars.get_contextvars()


async def test_bound_request_id_surfaces_in_log_events() -> None:
    structlog.contextvars.clear_contextvars()
    events: list[dict[str, Any]] = []

    def capture(_logger: Any, _method_name: str, event_dict: EventDict) -> str:
        # `merge_contextvars` has already merged the bound `request_id` into the dict.
        events.append(dict(event_dict))
        # Return a string: structlog's default PrintLogger calls logger.info(<result>).
        return str(event_dict.get("event", ""))

    structlog.configure(
        processors=[structlog.contextvars.merge_contextvars, capture],
    )

    class LoggingApp:
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            log = structlog.get_logger("inner")
            log.info("inner.event")
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b""})

    middleware = RequestIdMiddleware(LoggingApp())

    try:
        await middleware(_scope({"X-Request-ID": "rid-xyz"}), _receive_empty, _send_noop)
        assert events
        assert events[0]["event"] == "inner.event"
        assert events[0]["request_id"] == "rid-xyz"
    finally:
        structlog.reset_defaults()
