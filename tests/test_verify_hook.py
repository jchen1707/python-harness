"""Guardrail tests for the Stop-hook gate filter (`.claude/hooks/verify.py`).

The hook decides whether ending a turn should run the Definition of Done gates.
Getting that decision wrong is silent in both directions: too narrow and broken
code ships ungated, too wide and prose work burns toward the 8-block override.

These stay offline — `git` is stubbed, so nothing here touches the real repo state.
"""

from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HOOK_PATH = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "verify.py"


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    """Load the hook by path — `.claude/hooks` is not an importable package."""
    spec = importlib.util.spec_from_file_location("_verify_hook_under_test", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stub_git(stdout: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Replace subprocess.run with one returning a canned `git status --porcelain`."""

    def _run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    return _run


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (" M src/app/main.py", "src/app/main.py"),
        ("?? tests/test_new.py", "tests/test_new.py"),
        ("A  .claude/hooks/verify.py", ".claude/hooks/verify.py"),
        # Renames report both sides; only the destination exists on disk.
        ("R  src/app/old.py -> src/app/new.py", "src/app/new.py"),
        # Paths with special characters come back quoted.
        ('?? "src/app/a b.py"', "src/app/a b.py"),
        ('R  "src/old name.py" -> "src/new name.py"', "src/new name.py"),
    ],
)
def test_porcelain_path_extracts_the_file_on_disk(
    hook: ModuleType, line: str, expected: str
) -> None:
    assert hook.porcelain_path(line) == expected


@pytest.mark.parametrize(
    "status_line",
    [
        " M src/app/main.py",
        " M tests/test_smoke.py",
        # The regression this guards: hooks are Python the gates check, and were
        # previously outside the filter entirely.
        " M .claude/hooks/format_edited.py",
        # Config that defines the gates — breaks them while touching no Python.
        " M pyproject.toml",
        # Wires the hooks; its matchers are pinned by tests/test_hook_matchers.py,
        # so a broken edit here fails pytest without touching any Python.
        " M .claude/settings.json",
    ],
)
def test_gated_paths_trigger_the_gates(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch, status_line: str
) -> None:
    monkeypatch.setattr(hook.subprocess, "run", stub_git(status_line + "\n"))
    assert hook.gated_change("") is True


@pytest.mark.parametrize(
    "stdout",
    [
        "",  # nothing changed
        " M README.md\n M docs/architecture.md\n",  # prose ends freely
        " M .claude/plans/plan.md\n",  # plans too
        " M .claude/settings.local.json\n",  # personal config stays ungated
    ],
)
def test_ungated_changes_end_the_turn_freely(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    monkeypatch.setattr(hook.subprocess, "run", stub_git(stdout))
    assert hook.gated_change("") is False


def test_git_is_asked_about_every_gated_path(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pathspec must name each gated location explicitly.

    Asserted against literals rather than GATED_PATHS: dropping an entry from the
    constant would make a self-referential check pass vacuously, while git would
    silently stop reporting that directory and the gate would go quiet.
    """
    captured: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hook.subprocess, "run", _run)
    hook.gated_change("")

    argv = captured[0]
    for expected in (
        "src",
        "tests",
        ".claude/hooks",
        "pyproject.toml",
        ".claude/settings.json",
        ".claude/mcp_headers.py",
    ):
        assert expected in argv, f"{expected} missing from the git pathspec"


def test_subprocess_decodes_as_utf8(hook: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocess output must be decoded explicitly, never via `text=True`.

    `text=True` decodes with the locale codec — cp1252 on Windows — so an em-dash in
    ruff or mypy output comes back as mojibake in the very message the gate echoes
    back when it blocks. Caught in the wild; this pins the fix.
    """
    captured: list[dict[str, Any]] = []

    def _run(_cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hook.subprocess, "run", _run)
    hook.gated_change("")

    kwargs = captured[0]
    assert kwargs.get("encoding") == "utf-8"
    assert "text" not in kwargs, "text=True re-introduces locale decoding"


def test_git_failure_does_not_block(hook: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """If we cannot tell what changed, end the turn rather than block it forever."""

    def _boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise OSError("git not found")

    monkeypatch.setattr(hook.subprocess, "run", _boom)
    assert hook.gated_change("") is False
