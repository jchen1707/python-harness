"""Unit tests for `app.core.logging`.

`build_processors` is the testable seam for the renderer decision. The `request_id` surfacing
(via `merge_contextvars`) is tested in `test_middleware.py`, and the route's `noun.verb` log
is guarded in `tests/api/test_health.py`. Plan: BAC-4 test-plan.md.
"""

from __future__ import annotations

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer

from app.core.logging import build_processors


def test_build_processors_includes_merge_contextvars() -> None:
    processors = build_processors("INFO")

    assert structlog.contextvars.merge_contextvars in processors


def test_build_processors_json_renderer_for_info() -> None:
    processors = build_processors("INFO")

    assert isinstance(processors[-1], JSONRenderer)


def test_build_processors_console_renderer_for_debug() -> None:
    processors = build_processors("DEBUG")

    assert isinstance(processors[-1], ConsoleRenderer)
