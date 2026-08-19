"""Codex adapter tests for shared lifecycle enforcement."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROJECT = Path(__file__).resolve().parents[1]
HOOKS = PROJECT / ".agents" / "hooks"
CODEX_HOOKS = PROJECT / ".codex" / "hooks.json"


def load_hook(name: str) -> ModuleType:
    """Load one shared hook by path."""
    spec = importlib.util.spec_from_file_location(f"_{name}_under_test", HOOKS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("Read", {"file_path": ".env"}),
        ("Bash", {"command": "env"}),
        ("Bash", {"command": "echo $GH_TOKEN"}),
        ("Bash", {"command": "python -c 'import os'"}),
        ("Bash", {"command": "cat .env"}),
    ],
)
def test_codex_secret_guard_blocks_transcript_exposure(
    monkeypatch: pytest.MonkeyPatch, tool_name: str, tool_input: dict[str, str]
) -> None:
    hook = load_hook("protect_secrets")
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    assert hook.main() == 2


@pytest.mark.parametrize(
    "tool_input",
    [
        {"file_path": ".env.example"},
        {"command": "uv run pytest"},
        {"command": "git status --short"},
    ],
)
def test_codex_secret_guard_allows_normal_work(
    monkeypatch: pytest.MonkeyPatch, tool_input: dict[str, str]
) -> None:
    hook = load_hook("protect_secrets")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": tool_input})))
    assert hook.main() == 0


def test_codex_wires_all_portable_hooks() -> None:
    """Codex must enable every shared hook that accepts its payload format."""
    config = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
    hooks = config["hooks"]
    assert {"PreToolUse", "PostToolUse", "Stop", "SessionEnd"} <= hooks.keys()
    commands = [
        handler["command"]
        for groups in hooks.values()
        for group in groups
        for handler in group["hooks"]
    ]
    for script in (
        "protect_paths.py",
        "protect_secrets.py",
        "format_edited.py",
        "verify.py",
        "codex_session_learnings.py",
    ):
        assert any(script in command for command in commands)


def test_codex_test_writer_requires_a_linked_worktree() -> None:
    """The writable test agent must reject the primary checkout."""
    adapter = (PROJECT / ".codex/agents/test-writer.toml").read_text(encoding="utf-8")
    assert "git rev-parse --git-dir" in adapter
    assert "git rev-parse --git-common-dir" in adapter
    assert "Refuse" in adapter


def test_every_layer_a_command_and_skill_is_discoverable() -> None:
    """Codex discovers skills by directory, and layer A is not in that directory.

    The shared commands and skills live in the vendored tree, which nothing globs. A thin
    stub under `.agents/skills/<name>/` is what makes them reachable — and the failure of
    a missing one is that the command simply is not there, with no error anywhere saying
    why. `.claude/commands/` no longer exists: on `main` the plugin supplies these.
    """
    vendor = PROJECT / ".agents/vendor/harness"
    shared = {path.stem for path in (vendor / "commands").glob("*.md")}
    shared |= {path.parent.name for path in (vendor / "skills").glob("*/SKILL.md")}
    assert shared, "no layer A commands or skills vendored -- run vendor_sync.py sync"

    stubs = {path.parent.name for path in (PROJECT / ".agents/skills").glob("*/SKILL.md")}
    assert shared <= stubs, f"layer A with no discoverable stub: {sorted(shared - stubs)}"
