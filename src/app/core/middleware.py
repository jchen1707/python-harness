"""Request-id middleware — binds `request_id` to structlog contextvars at the edge.

Pure ASGI middleware (not Starlette `BaseHTTPMiddleware`, which has known lifespan and
contextvar propagation issues). On each HTTP request it reads the inbound `X-Request-ID`
header when present and non-empty, else generates a `uuid4` hex; binds `request_id` for the
request; and removes the `request_id` binding in `finally` so it does not leak across
requests. Other contextvars bound outside the request are left untouched.

`merge_contextvars` (in the logging chain) then surfaces the bound `request_id` on every
later log line in that request.

Conventions: core/CLAUDE.md (Logging — bind `request_id` at the edge).
"""

from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

_REQUEST_ID_HEADER = b"x-request-id"


class RequestIdMiddleware:
    """Pure ASGI middleware that binds a `request_id` for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        incoming = _read_header(scope, _REQUEST_ID_HEADER)
        request_id = incoming.strip() or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            await self._app(scope, receive, send)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")


def _read_header(scope: Scope, name: bytes) -> str:
    """Return the decoded header value for `name`, or an empty string when absent.

    HTTP headers are latin-1 encoded. Returns `""` when the header is not present.
    """
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return ""
