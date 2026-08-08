"""Guardrail tests for the learnings recovery script (`.claude/hooks/distil_backlog.py`).

The SessionEnd hook only distils sessions that end cleanly; this script recovers the
rest. Its selection logic is what these tests pin: picking the wrong transcripts is
silent in both directions — re-distilling a noted session wastes a model call, and
skipping an unnoted one is exactly the data loss the script exists to prevent.

Offline by construction: nothing here reaches the distiller, which shells out to a
model and cannot be pinned by a unit test.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

HOOK_DIR = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    """Load the script by path — `.claude/hooks` is not an importable package.

    The directory goes on `sys.path` for the load because the script imports
    `session_learnings` (which imports `vault_index`) as sibling top-level modules.
    """
    sys.path.insert(0, str(HOOK_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "_distil_backlog_under_test", HOOK_DIR / "distil_backlog.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(HOOK_DIR))
    return module


def test_project_slug_matches_the_harness_convention(script: ModuleType) -> None:
    """Claude Code names a project's transcript directory by replacing every
    non-alphanumeric character with `-`. Diverging from that convention makes the
    script look in a directory that does not exist and report an empty backlog."""
    assert script.project_slug(Path("/home/user/my repo")) == "-home-user-my-repo"


def test_backlog_returns_only_sessions_without_a_note(script: ModuleType, tmp_path: Path) -> None:
    """A noted session must not be re-distilled; an unnoted one must not be skipped."""
    transcripts = tmp_path / "transcripts"
    notes = tmp_path / "notes"
    transcripts.mkdir()
    notes.mkdir()

    (transcripts / "aaaaaaaa-1111-2222-3333-444444444444.jsonl").write_text("{}", encoding="utf-8")
    (transcripts / "bbbbbbbb-1111-2222-3333-444444444444.jsonl").write_text("{}", encoding="utf-8")
    # The note's date differs from today on purpose: matching must key on the
    # session id alone, or every note older than a day reads as missing.
    (notes / "2026-08-06 demo aaaaaaaa.md").write_text("---\n---\n", encoding="utf-8")

    remaining = script.backlog(transcripts, notes)

    assert [p.name for p in remaining] == ["bbbbbbbb-1111-2222-3333-444444444444.jsonl"]


def test_backlog_is_empty_when_the_transcripts_dir_is_missing(
    script: ModuleType, tmp_path: Path
) -> None:
    """A repo whose project dir was never created has nothing to recover — not an error."""
    assert script.backlog(tmp_path / "nope", tmp_path) == []


def test_dry_run_is_the_default_and_writes_nothing(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each distillation is a paid model call, so acting must require --run."""
    transcripts = tmp_path / "transcripts"
    notes = tmp_path / "notes"
    transcripts.mkdir()
    notes.mkdir()
    (transcripts / "cccccccc-1111.jsonl").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("CLAUDE_LEARNINGS_DIR", str(notes))
    monkeypatch.setattr(script, "transcripts_dir", lambda _cwd: transcripts)

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dry run must never reach the distiller")

    monkeypatch.setattr(script.session_learnings, "distil_transcript", _explode)

    assert script.main([]) == 0
    assert list(notes.glob("*.md")) == []


def test_short_transcript_produces_no_note_without_calling_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`distil_transcript` must reject a too-short transcript before spending tokens.

    Pinned here rather than in test_session_learnings.py because the recovery path is
    what feeds arbitrary old transcripts in bulk; the SessionEnd path sees one at a time.
    """
    sys.path.insert(0, str(HOOK_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "_session_learnings_for_backlog_test", HOOK_DIR / "session_learnings.py"
        )
        assert spec is not None
        assert spec.loader is not None
        learnings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(learnings)
    finally:
        sys.path.remove(str(HOOK_DIR))

    transcript = tmp_path / "tiny.jsonl"
    transcript.write_text('{"message": {"role": "user", "content": "hi"}}\n', encoding="utf-8")

    def _explode(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("a short transcript must never reach the distiller")

    monkeypatch.setattr(learnings, "distil", _explode)

    result = learnings.distil_transcript(str(transcript), "tiny", str(tmp_path), tmp_path)

    assert result is None
    assert list(tmp_path.glob("*.md")) == []
