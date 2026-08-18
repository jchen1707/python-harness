"""Guardrail test for the PreToolUse and PostToolUse matchers in `.claude/settings.json`.

A hook matcher is a case-sensitive regex over the **tool name**. Every guard depends on it
entirely: `protect_paths.py` cannot block a write it never sees, `format_edited.py` cannot
format a file it is never told about, and `protect_secrets.py` cannot refuse a read that
never reaches it. Narrowing a matcher disables its guard silently — every other test still
passes, the hook still runs on the tools it does match, and nothing reports the gap.

That is the same failure `tests/test_verify_hook.py` exists to prevent for `GATED_PATHS`.
This file does it for the matchers.

Asserted per **guard** rather than per event, because the two guards on `PreToolUse` want
opposite things from the same event: the write guard must not fire on reads, and the read
guard must. Asserting the event as a whole is what let `protect_secrets.py` ship wired into
`.codex/hooks.json` and nowhere else — the Claude side had no read-side matcher at all, and
no test could tell, because "PreToolUse ignores reads" was the asserted property.

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

# Read-only tools. Matching these would run the write guards on every search in the session.
MUST_NOT_MATCH = ("Read", "Grep", "Glob", "Bash", "mcp__linear__list_issues")

# Tools that can copy a secret into the transcript without writing a byte.
SECRET_SURFACE = ("Read", "Bash")

# Each guard, the event it runs on, and the script that identifies its matcher group.
WRITE_GUARDS = [("PreToolUse", "protect_paths.py"), ("PostToolUse", "format_edited.py")]
READ_GUARD = ("PreToolUse", "protect_secrets.py")


def matchers(event: str, script: str) -> list[str]:
    """Every matcher configured for `event` whose hooks run `script`."""
    settings: dict[str, Any] = json.loads(SETTINGS.read_text(encoding="utf-8"))
    groups = settings["hooks"][event]
    return [
        group["matcher"]
        for group in groups
        if "matcher" in group and script in json.dumps(group["hooks"])
    ]


@pytest.mark.parametrize(("event", "script"), WRITE_GUARDS)
@pytest.mark.parametrize("tool", MUST_MATCH)
def test_matcher_covers_every_tool_that_can_write(event: str, script: str, tool: str) -> None:
    """A write tool outside the matcher is a write the guard never sees.

    `protect_paths.py` documents this as a rule in its own docstring. A docstring does not
    fail a build, so the rule is pinned here instead.
    """
    assert any(re.search(pattern, tool) for pattern in matchers(event, script)), (
        f"the {script} matcher does not cover {tool} — the guard will not run for it. "
        f"Matchers: {matchers(event, script)}"
    )


@pytest.mark.parametrize(("event", "script"), WRITE_GUARDS)
@pytest.mark.parametrize("tool", MUST_NOT_MATCH)
def test_write_guards_leave_read_only_tools_alone(event: str, script: str, tool: str) -> None:
    """Both write guards shell out to `uv run`. Firing them on reads would tax every search."""
    assert not any(re.search(pattern, tool) for pattern in matchers(event, script)), (
        f"the {script} matcher matches the read-only tool {tool}."
    )


@pytest.mark.parametrize("tool", SECRET_SURFACE)
def test_the_secret_guard_covers_the_read_surface(tool: str) -> None:
    """The deny list stops the shell readers it can name. This stops the rest.

    A deny entry is a literal pattern; `protect_secrets.py` reads the command. Wiring it
    for one harness and not the other is what defect 1 was: Codex refused these calls and
    Claude Code did not.
    """
    event, script = READ_GUARD
    assert any(re.search(pattern, tool) for pattern in matchers(event, script)), (
        f"the {script} matcher does not cover {tool} — a secret can be read through it "
        f"without the guard seeing the call. Matchers: {matchers(event, script)}"
    )


@pytest.mark.parametrize(("event", "script"), [*WRITE_GUARDS, READ_GUARD])
def test_every_guard_is_still_configured(event: str, script: str) -> None:
    """The tests above pass vacuously if a guard is deleted: `any([])` is False, so the
    read-only assertion holds and the coverage assertion is the only thing left to fail.
    Pin each guard's existence separately so removing one reports as removal."""
    assert matchers(event, script), f"no {event} hook runs {script} at all"
