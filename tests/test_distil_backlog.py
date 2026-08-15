"""Guardrail tests for the learnings recovery script (`.agents/hooks/distil_backlog.py`).

The SessionEnd hook only distils sessions that end cleanly; this script recovers the
rest. Its selection logic is what these tests pin: picking the wrong transcripts is
silent in both directions — re-distilling a noted session wastes a model call, and
skipping an unnoted one is exactly the data loss the script exists to prevent.

Offline by construction: nothing here reaches the distiller, which shells out to a
model and cannot be pinned by a unit test.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

HOOK_DIR = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    """Load the script by path — `.agents/hooks` is not an importable package.

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


def test_backlog_excludes_the_distillers_own_transcripts(
    script: ModuleType, tmp_path: Path
) -> None:
    """Every distillation is a `claude -p` call that files a transcript of its own.

    Those transcripts hold the prompt and the finished note, and none of them has a note
    keyed to its session id — so an unfiltered backlog re-distils each one into a copy of
    a note the vault already has. In this project's transcript directory they outnumbered
    the real sessions two to one.
    """
    transcripts = tmp_path / "transcripts"
    notes = tmp_path / "notes"
    transcripts.mkdir()
    notes.mkdir()

    prompt = script.session_learnings.PROMPT
    for name, first_user_text in (
        ("aaaaaaaa-1111-2222-3333-444444444444.jsonl", "Fix the flaky test."),
        ("bbbbbbbb-1111-2222-3333-444444444444.jsonl", f"{prompt}\n\n=== TRANSCRIPT ===\nuser: x"),
    ):
        entry = {
            "message": {"role": "user", "content": [{"type": "text", "text": first_user_text}]}
        }
        (transcripts / name).write_text(json.dumps(entry) + "\n", encoding="utf-8")

    remaining = script.backlog(transcripts, notes)

    assert [p.name for p in remaining] == ["aaaaaaaa-1111-2222-3333-444444444444.jsonl"]


def write_note(directory: Path, name: str, session: str) -> Path:
    """A learnings note shaped the way the SessionEnd hook writes one."""
    path = directory / name
    path.write_text(
        f"---\ndate: 2026-08-07 10:00\nproject: demo\nsession: {session}\n"
        "summary: A lesson.\ntags: [project-learnings]\n---\n\n## Implementation learnings\n\n"
        "- Something.\n",
        encoding="utf-8",
    )
    return path


def write_transcript(path: Path, first_user_text: str) -> None:
    """A transcript shaped the way Claude Code writes them."""
    entry = {"message": {"role": "user", "content": [{"type": "text", "text": first_user_text}]}}
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")


def test_a_note_from_the_distillers_own_session_is_reported_as_an_echo(
    script: ModuleType, tmp_path: Path
) -> None:
    """The distiller's transcript holds the finished note, so distilling it copied that
    note into the vault under the child's session id. Fixing the writer stops new ones and
    removes none of the copies already written, so the audit has to find them."""
    notes = tmp_path / "notes"
    project = tmp_path / "projects" / "some-repo"
    notes.mkdir()
    project.mkdir(parents=True)

    write_note(notes, "2026-08-07 demo aaaaaaaa.md", "aaaaaaaa-1111-2222-3333-444444444444")
    write_note(notes, "2026-08-08 demo bbbbbbbb.md", "bbbbbbbb-1111-2222-3333-444444444444")
    write_transcript(project / "aaaaaaaa-1111-2222-3333-444444444444.jsonl", "Fix the flaky test.")
    write_transcript(
        project / "bbbbbbbb-1111-2222-3333-444444444444.jsonl",
        f"{script.session_learnings.PROMPT}\n\n=== TRANSCRIPT ===\nuser: x",
    )

    found = script.echo_notes(notes, tmp_path / "projects")

    assert [p.name for p in found] == ["2026-08-08 demo bbbbbbbb.md"]


def test_echo_detection_reads_every_projects_transcripts(
    script: ModuleType, tmp_path: Path
) -> None:
    """One vault serves several repos, so an echo note in it can come from any of them.

    Scanning only the current project's transcripts would leave every other repo's echo
    notes unexplained, and an unexplained note is one the audit must not touch.
    """
    notes = tmp_path / "notes"
    other = tmp_path / "projects" / "another-repo"
    notes.mkdir()
    other.mkdir(parents=True)

    write_note(notes, "2026-08-08 other bbbbbbbb.md", "bbbbbbbb-1111-2222-3333-444444444444")
    write_transcript(
        other / "bbbbbbbb-1111-2222-3333-444444444444.jsonl",
        f"{script.session_learnings.PROMPT}\n\n=== TRANSCRIPT ===\nuser: x",
    )

    found = script.echo_notes(notes, tmp_path / "projects")

    assert [p.name for p in found] == ["2026-08-08 other bbbbbbbb.md"]


def test_one_session_holding_several_notes_is_reported_as_a_split(
    script: ModuleType, tmp_path: Path
) -> None:
    """Dating each write afresh gave one session a new note every time it distilled.

    `note_path` stops new ones. These are the files that bug already wrote, and nothing
    else in the harness can find them.
    """
    notes = tmp_path / "notes"
    notes.mkdir()
    write_note(notes, "2026-08-06 demo aaaaaaaa.md", "aaaaaaaa-1111-2222-3333-444444444444")
    write_note(notes, "2026-08-07 demo aaaaaaaa.md", "aaaaaaaa-1111-2222-3333-444444444444")
    write_note(notes, "2026-08-07 demo cccccccc.md", "cccccccc-1111-2222-3333-444444444444")

    found = script.split_sessions(notes)

    assert list(found) == ["aaaaaaaa"]
    assert [p.name for p in found["aaaaaaaa"]] == [
        "2026-08-06 demo aaaaaaaa.md",
        "2026-08-07 demo aaaaaaaa.md",
    ]


def test_a_note_is_grouped_by_its_front_matter_not_its_filename(
    script: ModuleType, tmp_path: Path
) -> None:
    """A note renamed by hand in Obsidian keeps its `session:` field, and that field is
    the identity. Grouping on the filename alone would report the rename as a new
    session and hide a real duplicate."""
    notes = tmp_path / "notes"
    notes.mkdir()
    write_note(notes, "2026-08-06 demo aaaaaaaa.md", "aaaaaaaa-1111-2222-3333-444444444444")
    write_note(notes, "Grilling lessons.md", "aaaaaaaa-1111-2222-3333-444444444444")

    assert list(script.split_sessions(notes)) == ["aaaaaaaa"]


def test_audit_deletes_nothing_without_run(script: ModuleType, tmp_path: Path) -> None:
    """The audit reads the user's own vault, so acting is opt-in like the rest of this
    script. A dry run that deleted would make the tool unsafe to point at a vault."""
    notes = tmp_path / "notes"
    project = tmp_path / "projects" / "some-repo"
    notes.mkdir()
    project.mkdir(parents=True)
    write_note(notes, "2026-08-08 demo bbbbbbbb.md", "bbbbbbbb-1111-2222-3333-444444444444")
    write_transcript(
        project / "bbbbbbbb-1111-2222-3333-444444444444.jsonl",
        f"{script.session_learnings.PROMPT}\n\n=== TRANSCRIPT ===\nuser: x",
    )

    assert script.run_audit(notes, tmp_path / "projects", delete=False) == 0
    assert (notes / "2026-08-08 demo bbbbbbbb.md").exists()


def test_audit_run_removes_echoes_and_keeps_split_notes(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An echo note is an artifact — its lesson is already in the vault under the session
    that learned it. A split note is a real distillation of a real session, so which
    learnings survive a merge is a judgement this tool must not make.

    The vault variables are cleared because a delete rebuilds the indexes, and this
    machine has a real vault configured. A unit test must not write to it.
    """
    monkeypatch.delenv("CLAUDE_LEARNINGS_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_VAULT_DIR", raising=False)
    notes = tmp_path / "notes"
    project = tmp_path / "projects" / "some-repo"
    notes.mkdir()
    project.mkdir(parents=True)

    write_note(notes, "2026-08-06 demo aaaaaaaa.md", "aaaaaaaa-1111-2222-3333-444444444444")
    write_note(notes, "2026-08-07 demo aaaaaaaa.md", "aaaaaaaa-1111-2222-3333-444444444444")
    write_note(notes, "2026-08-08 demo bbbbbbbb.md", "bbbbbbbb-1111-2222-3333-444444444444")
    write_transcript(
        project / "bbbbbbbb-1111-2222-3333-444444444444.jsonl",
        f"{script.session_learnings.PROMPT}\n\n=== TRANSCRIPT ===\nuser: x",
    )

    assert script.run_audit(notes, tmp_path / "projects", delete=True) == 0

    remaining = sorted(p.name for p in notes.glob("*.md"))
    assert remaining == [
        "2026-08-06 demo aaaaaaaa.md",
        "2026-08-07 demo aaaaaaaa.md",
        "_INDEX.md",
    ]


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
