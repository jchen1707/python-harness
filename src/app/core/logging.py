"""Structured logging — structlog configured once by the app factory.

`configure_logging` sets structlog up once. `build_processors` returns the processor chain
so the renderer decision (JSON vs human-readable) is unit-testable without capturing IO.

The chain starts with `merge_contextvars`, which surfaces the edge-bound `request_id` on
every later log line in the request. The renderer is `ConsoleRenderer` (human-readable) in
development (`DEBUG`) and `JSONRenderer` otherwise.

Conventions: core/CLAUDE.md (Logging).
"""

from __future__ import annotations

import logging

import structlog
from structlog.typing import Processor


def build_processors(log_level: str) -> list[Processor]:
    """Return the structlog processor chain for the given log level.

    `merge_contextvars` surfaces the edge-bound `request_id` on later log lines. The
    renderer is `ConsoleRenderer` in development (`DEBUG`) and `JSONRenderer` otherwise.
    """
    renderer: Processor
    if log_level.upper() == "DEBUG":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        renderer,
    ]


def configure_logging(log_level: str) -> None:
    """Configure structlog once, and set the stdlib root logger level.

    The root level governs stdlib loggers that propagate to root. Uvicorn's own loggers
    carry their own levels with propagation disabled, so they are not governed here; set
    their levels through uvicorn's `--log-level` instead.
    """
    structlog.configure(processors=build_processors(log_level))
    logging.getLogger().setLevel(log_level.upper())
