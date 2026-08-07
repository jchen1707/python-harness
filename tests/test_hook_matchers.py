"""Guardrail test for the PreToolUse and PostToolUse matchers in `.claude/settings.json`.

A hook matcher is a case-sensitive regex over the **tool name**. Both guards depend on it
entirely: `protect_paths.py` cannot block a write it never sees, and `format_edited.py`
cannot format a file it is never told about. Narrowing the matcher disables both silently
— every test still passes, the hooks still run on the tools they do match, and nothing
reports the gap.

That is the same failure `tests/test_verify_hook.py` exists to prevent for `GATED_PATHS`.
This file does it for the matchers.

Deliberately asserted with `re.search` rather than `re.match`, the weakest assumption
available: the point is to pin which tool names our own config covers, not to re-implement
the harness's matching rules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"

# Tools that can put bytes on disk. `NotebookEdit` writes `.ipynb`; an MCP server can
# expose a write under any name, so the matcher covers the verbs rather than a fixed list.
MUST_MATCH = (
    "Edit",
    "Write",
    "NotebookEdit",
    "mcp__filesystem__write_file",
    "mcp__filesystem__edit_file",
    "mcp__memory__create_entities",
    "mcp__patch__apply_patch",
)

# Read-only tools. Matching these would run both hooks on every search in the session.
MUST_NOT_MATCH = ("Read", "Grep", "Glob", "Bash", "mcp__linear__list_issues")

GUARDED_EVENTS = ("PreToolUse", "PostToolUse")


def matchers(event: str) -> list[str]:
    """Every matcher string configured for one hook event."""
    settings: dict[str, Any] = json.loads(SETTINGS.read_text(encoding="utf-8"))
    groups = settings["hooks"][event]
    return [group["matcher"] for group in groups if "matcher" in group]


@pytest.mark.parametrize("event", GUARDED_EVENTS)
@pytest.mark.parametrize("tool", MUST_MATCH)
def test_matcher_covers_every_tool_that_can_write(event: str, tool: str) -> None:
    """A write tool outside the matcher is a write neither guard ever sees.

    `protect_paths.py` documents this as a rule in its own docstring. A docstring does not
    fail a build, so the rule is pinned here instead.
    """
    assert any(re.search(pattern, tool) for pattern in matchers(event)), (
        f"{event} matcher does not cover {tool} — `protect_paths` and `format_edited` "
        f"will not run for it. Matchers: {matchers(event)}"
    )


@pytest.mark.parametrize("event", GUARDED_EVENTS)
@pytest.mark.parametrize("tool", MUST_NOT_MATCH)
def test_matcher_leaves_read_only_tools_alone(event: str, tool: str) -> None:
    """Both hooks shell out to `uv run`. Firing them on reads would tax every search."""
    assert not any(re.search(pattern, tool) for pattern in matchers(event)), (
        f"{event} matcher matches the read-only tool {tool}."
    )


@pytest.mark.parametrize("event", GUARDED_EVENTS)
def test_the_guarded_events_are_still_configured(event: str) -> None:
    """The tests above pass vacuously if an event is deleted: `any([])` is False, so the
    read-only assertion holds and the write assertion is the only thing left to fail.
    Pin the event's existence separately so removing it reports as removal."""
    assert matchers(event), f"no {event} hook is configured at all"
