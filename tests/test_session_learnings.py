"""Guardrail tests for the SessionEnd hook's vault writes (`.claude/hooks/session_learnings.py`).

The hook writes into the user's own notes, from more than one repo now. Its failures are
silent in the direction that matters: a malformed index still looks like an index, and
nothing downstream reports that a note went missing from it.

These cover the write path only — the distillation shells out to a model and is not
something a unit test can pin. Offline by construction: every test builds a throwaway
notes directory under `tmp_path`.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

HOOK_DIR = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    """Load the hook by path — `.claude/hooks` is not an importable package.

    The directory goes on `sys.path` for the load because the hook imports `vault_index`
    as a sibling top-level module. That resolves at runtime because Python puts the
    running script's own directory there; importing it here has to reproduce that.
    """
    sys.path.insert(0, str(HOOK_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "_session_learnings_under_test", HOOK_DIR / "session_learnings.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(HOOK_DIR))
    return module


def write_note(directory: Path, name: str, summary: str, project: str = "demo") -> None:
    """A note shaped the way the hook writes them."""
    (directory / name).write_text(
        f"---\ndate: 2026-08-06 10:00\nproject: {project}\nsummary: {summary}\n"
        f"tags: [project-learnings, session-retro]\n---\n\n## Implementation learnings\n\nBody.\n",
        encoding="utf-8",
    )


def write_transcript(path: Path, first_user_text: str) -> None:
    """A transcript shaped the way Claude Code writes them."""
    lines = [
        json.dumps({"type": "queue-operation"}),
        json.dumps(
            {"message": {"role": "user", "content": [{"type": "text", "text": first_user_text}]}}
        ),
        json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_a_second_distillation_overwrites_the_session_note(
    hook: ModuleType, tmp_path: Path
) -> None:
    """One session owns one note, whatever date the second distillation runs on.

    A session distils twice whenever it is resumed and ends again, or recovered while
    still open. Naming the file from the current date made each of those a new note, so
    the same lessons landed in the vault repeatedly and every search returned them
    repeatedly.
    """
    write_note(tmp_path, "2026-08-06 demo abc12345.md", "The first distillation.")

    target = hook.note_path(tmp_path, "demo", "abc12345-1111-2222-3333-444444444444")

    assert target == tmp_path / "2026-08-06 demo abc12345.md"


def test_redistilling_a_session_carries_its_earlier_note_forward(
    hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Overwriting a session's note must not throw away what the first pass found.

    The distiller only ever sees the last `MAX_TRANSCRIPT_CHARS` of a session. A long
    session resumed and ended again is distilled from a different part of itself, so the
    second note holds different lessons, not the same ones. Overwriting without passing
    the earlier note back deletes a whole set of learnings silently.
    """
    write_note(tmp_path, "2026-08-06 demo abc12345.md", "Earlier.")
    (tmp_path / "2026-08-06 demo abc12345.md").write_text(
        "---\ndate: 2026-08-06 10:00\nproject: demo\nsummary: Earlier.\n---\n\n"
        "## Implementation learnings\n\n- Windows write_text emits CRLF.\n",
        encoding="utf-8",
    )
    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, "Do the work. " + "padding. " * 200)

    seen: dict[str, str] = {}

    def _capture(_transcript: str, _context: str, prior: str = "") -> str:
        seen["prior"] = prior
        return "SUMMARY: Both lessons.\n\n## Implementation learnings\n\n- Two things.\n"

    monkeypatch.setattr(hook, "distil", _capture)

    target = hook.distil_transcript(str(transcript), "abc12345-1111", str(tmp_path), tmp_path)

    assert target == tmp_path / "2026-08-06 demo abc12345.md"
    assert "Windows write_text emits CRLF." in seen["prior"]
    assert "summary:" not in seen["prior"]


def test_a_new_session_gets_a_dated_note(hook: ModuleType, tmp_path: Path) -> None:
    """The date prefix is how the folder sorts, so a first note still carries one."""
    write_note(tmp_path, "2026-08-06 demo abc12345.md", "Another session's lesson.")

    target = hook.note_path(tmp_path, "demo", "ffffffff-1111-2222-3333-444444444444")

    assert target.parent == tmp_path
    assert target.name.endswith(" demo ffffffff.md")
    assert re.match(r"^\d{4}-\d{2}-\d{2} ", target.name)


def test_the_distillers_own_transcript_produces_no_note(
    hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The distiller is a Claude Code session, so it writes a transcript of its own.

    That transcript holds the distillation prompt and the finished note. Distilling it
    hands the model a document that already contains the answer, and the note comes back
    a second time under the child's session id. It was the largest single source of
    duplicate notes in the vault.
    """
    transcript = tmp_path / "child.jsonl"
    write_transcript(transcript, hook.PROMPT + "\n\n=== TRANSCRIPT ===\nuser: something")

    def _explode(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("the distiller must not be run on its own transcript")

    monkeypatch.setattr(hook, "distil", _explode)

    assert hook.distil_transcript(str(transcript), "child", str(tmp_path), tmp_path) is None
    assert list(tmp_path.glob("*.md")) == []


def test_a_child_transcript_from_before_the_mark_is_recognised(
    hook: ModuleType, tmp_path: Path
) -> None:
    """The duplicate notes came from transcripts the old prompt wrote, with no mark.

    Those files are still on disk, and they are exactly what the recovery script would
    distil next. Recognising only the mark would fix nothing that has already happened.
    """
    transcript = tmp_path / "legacy.jsonl"
    write_transcript(
        transcript,
        "You are writing a note for an engineer's personal knowledge base, recording\nwhat a"
        " coding session taught them.",
    )

    assert hook.is_distiller_transcript(str(transcript)) is True


def test_a_session_that_merely_mentions_the_mark_is_still_distilled(
    hook: ModuleType, tmp_path: Path
) -> None:
    """This repo edits this hook, so the mark appears as ordinary text in real sessions.

    Searching the file for it would make every session about the second brain invisible
    to the recovery script. Only a session whose opening prompt *is* the distillation
    prompt is the distiller's own.
    """
    transcript = tmp_path / "real.jsonl"
    write_transcript(transcript, f"Why does {hook.DISTILLER_MARK} appear in the prompt?")

    assert hook.is_distiller_transcript(str(transcript)) is False


def test_learnings_index_is_written_with_lf_endings(hook: ModuleType, tmp_path: Path) -> None:
    """Two repos write this vault now, and they have to agree on line endings.

    `write_text` translates every `\\n` to `os.linesep` unless told otherwise, so a
    Windows writer emits CRLF and a Linux one LF. Whichever wrote last rewrites the file
    end to end, and every line reads as modified to Obsidian, OneDrive and git alike.
    """
    write_note(tmp_path, "2026-08-06 demo abc12345.md", "A lesson worth keeping.")

    hook.rebuild_index(tmp_path)

    assert b"\r" not in (tmp_path / "_INDEX.md").read_bytes()


def test_index_row_is_built_from_the_note_front_matter(hook: ModuleType, tmp_path: Path) -> None:
    """The summary is the only thing a search reads before deciding to open a note.

    Parsing now goes through `vault_index.front_matter`, so this also pins that the two
    indexes cannot disagree about what a note says.
    """
    write_note(tmp_path, "2026-08-06 demo abc12345.md", "MCP config lives in .mcp.json.")

    hook.rebuild_index(tmp_path)
    index = (tmp_path / "_INDEX.md").read_text(encoding="utf-8")

    assert "1 notes." in index
    assert "MCP config lives in .mcp.json." in index
    assert "[[2026-08-06 demo abc12345]]" in index


def test_index_is_rebuilt_not_appended(hook: ModuleType, tmp_path: Path) -> None:
    """An append-only index drifts the moment a note is renamed or deleted by hand.

    A stale index is worse than none: a search that trusts it silently misses notes, and
    the vault is edited in Obsidian far more often than it is written by the hook.
    """
    write_note(tmp_path, "2026-08-06 demo aaaaaaaa.md", "First lesson.")
    hook.rebuild_index(tmp_path)

    (tmp_path / "2026-08-06 demo aaaaaaaa.md").unlink()
    write_note(tmp_path, "2026-08-06 other bbbbbbbb.md", "Second lesson.", project="other")
    hook.rebuild_index(tmp_path)

    index = (tmp_path / "_INDEX.md").read_text(encoding="utf-8")
    assert "First lesson." not in index
    assert "Second lesson." in index
    assert "1 notes." in index


def test_a_note_without_front_matter_is_skipped(hook: ModuleType, tmp_path: Path) -> None:
    """Hand-written notes land in this folder too. A row of empty columns is noise."""
    write_note(tmp_path, "2026-08-06 demo abc12345.md", "A real lesson.")
    (tmp_path / "Scratch.md").write_text("Something jotted down in Obsidian.\n", encoding="utf-8")

    hook.rebuild_index(tmp_path)

    assert "1 notes." in (tmp_path / "_INDEX.md").read_text(encoding="utf-8")


def test_the_vault_index_is_rebuilt_even_when_the_session_taught_nothing(
    hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`vault_index.refresh()` has to run above every early return in `main`.

    The vault gains hand-written notes between sessions, and most sessions distil no
    learning at all. If the refresh sits below the early returns, `_VAULT_INDEX.md` only
    updates on sessions that happened to write a note — so the file an agent reads first
    goes stale for exactly the notes the user wrote themselves.

    Driven through `main` rather than by reading the source, so it pins the behaviour and
    not the line number. `CLAUDE_LEARNINGS_DIR` is unset here, which returns early well
    before anything is distilled.
    """
    (tmp_path / "Handwritten.md").write_text(
        "A note the user wrote in Obsidian, never seen by the hook.\n", encoding="utf-8"
    )
    monkeypatch.delenv("CLAUDE_LEARNINGS_SKIP", raising=False)
    monkeypatch.delenv("CLAUDE_LEARNINGS_OFF", raising=False)
    monkeypatch.delenv("CLAUDE_LEARNINGS_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_VAULT_DIR", str(tmp_path))

    assert hook.main() == 0

    index = (tmp_path / "_VAULT_INDEX.md").read_text(encoding="utf-8")
    assert "Handwritten.md" in index
