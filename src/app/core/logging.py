"""Configure structured application logging."""

import sys
from uuid import uuid4

import structlog
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.types import Processor


def configure_logging(log_level: str, *, development: bool | None = None) -> None:
    """Configure structlog for the current process."""
    if development is None:
        development = sys.stderr.isatty()

    renderer: Processor
    if development:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


async def bind_request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Bind one request ID until the request completes."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
        structlog.get_logger().info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response
    finally:
        structlog.contextvars.clear_contextvars()
