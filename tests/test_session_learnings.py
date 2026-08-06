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
