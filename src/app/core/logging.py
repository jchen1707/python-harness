"""Structlog configuration (architecture §6).

Called once from the app factory at startup. Never ``print()``. Bound loggers carry
context; for concurrent attribution bind a ``request_id``/``task_id`` — structlog reads
``contextvars`` automatically (§13).
"""

from __future__ import annotations

import logging

import structlog


def configure_logging() -> None:
    """Configure structlog + stdlib logging once per process.

    Idempotent: safe to call from the app factory lifespan on every startup. Uses a
    console renderer for readable local output (swap for ``JSONRenderer`` in prod).
    """
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
