#!/usr/bin/env python
"""Recover second-brain learnings from sessions that never fired SessionEnd.

`session_learnings.py` runs only when a session ends cleanly. A terminal that is
closed, killed, or simply left open never distils, and the loss is silent — the
transcript sits in `~/.claude/projects/<project>/` with no note in the vault and
nothing reporting the gap. This script finds those transcripts and distils them
through the same pipeline the hook uses.

Run it from the repo whose sessions you want to recover:

    uv run python .claude/hooks/distil_backlog.py          # dry run: list only
    uv run python .claude/hooks/distil_backlog.py --run    # distil (spends tokens)

Dry run is the default because each distillation is a `claude -p` call that costs
real tokens. `--limit` caps how many transcripts one invocation processes.

`--audit` runs the opposite direction: it reads the vault and reports notes that should
not be there. Two writer bugs put duplicates in the vault before they were fixed, and
fixing a writer does not remove what it already wrote.

    uv run python .claude/hooks/distil_backlog.py --audit         # report only
    uv run python .claude/hooks/distil_backlog.py --audit --run   # delete echo notes

Two caveats, both accepted:

- A session that is **still open** shows up in the backlog too — it has a transcript
  and no note. Distilling it writes a partial note. When the session later ends,
  SessionEnd overwrites that same note with the full one, on any date: `note_path`
  keys the file on the session id, not on the day it ran.
- `git_context` reads the repo as it is *now*, not as it was when the session ran.
  The transcript carries the real history; the git context is only framing.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Sibling module: hooks run as `python <abs path>/distil_backlog.py`, so `.claude/hooks`
# is sys.path[0]. mypy and pyright find it via pyproject.toml (mypy_path / extraPaths).
import session_learnings


def project_slug(cwd: Path) -> str:
    """The directory name Claude Code uses for a project's transcripts.

    Every character that is not a letter or digit becomes `-`, so
    `C:\\Users\\x\\repo` and `/home/x/repo` both map the way the harness maps them.
    """
    return re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


def transcripts_dir(cwd: Path) -> Path:
    """Where Claude Code keeps this project's session transcripts."""
    return Path.home() / ".claude" / "projects" / project_slug(cwd)


def has_note(directory: Path, session_id: str) -> bool:
    """True when any learnings note exists for this session, whatever its date."""
    return session_learnings.existing_note(directory, session_id) is not None


def backlog(transcripts: Path, directory: Path) -> list[Path]:
    """Transcripts worth distilling, newest first.

    Two exclusions. A session that already has a note needs no second one. A transcript
    written by the distiller itself holds the prompt and the finished note, so distilling
    it copies a note the vault already has under a new session id — the single largest
    source of duplicates before this filter existed.
    """
    if not transcripts.is_dir():
        return []
    missing = [
        path
        for path in transcripts.glob("*.jsonl")
        if not has_note(directory, path.stem)
        and not session_learnings.is_distiller_transcript(str(path))
    ]
    return sorted(missing, key=lambda p: p.stat().st_mtime, reverse=True)


def projects_root() -> Path:
    """Where Claude Code keeps every project's transcripts."""
    return Path.home() / ".claude" / "projects"


def distiller_ids(root: Path) -> set[str]:
    """Short ids of every transcript the distiller wrote, across all projects.

    One vault serves several repos, so an echo note in it can come from any of them.
    Scanning only the current project's transcripts leaves the rest unexplained, and an
    unexplained note is one the audit has to leave alone.
    """
    return {
        session_learnings.short_id(path.stem)
        for path in root.glob("*/*.jsonl")
        if session_learnings.is_distiller_transcript(str(path))
    }


def note_key(path: Path) -> str:
    """The session a note belongs to, as it appears in a filename.

    The `session:` field is the real identity. The filename suffix is the fallback: it
    is derived from the same id, and it is all a note written before that field existed
    carries.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return path.stem.rsplit(" ", 1)[-1]
    session = session_learnings.vault_index.front_matter(text).get("session", "")
    return session_learnings.short_id(session) if session else path.stem.rsplit(" ", 1)[-1]


def notes_by_session(directory: Path) -> dict[str, list[Path]]:
    """Every learnings note, grouped by the session that produced it, oldest first.

    Generated indexes are excluded: they describe the notes rather than being one.
    """
    generated = {session_learnings.INDEX_NAME, session_learnings.vault_index.INDEX_NAME}
    groups: dict[str, list[Path]] = {}
    for note in sorted(directory.glob("*.md")):
        if note.name in generated:
            continue
        groups.setdefault(note_key(note), []).append(note)
    return groups


def echo_notes(directory: Path, root: Path) -> list[Path]:
    """Notes whose session id belongs to the distiller, not to a real session.

    Every distillation is itself a `claude -p` session, so it files a transcript holding
    the prompt *and* the finished note. Distilling that transcript returned the note a
    second time under the child's id. These notes are artifacts of the bug: the lesson in
    each one is already in the vault under the session that truly learned it.
    """
    ids = distiller_ids(root)
    return [notes[0] for key, notes in sorted(notes_by_session(directory).items()) if key in ids]


def split_sessions(directory: Path) -> dict[str, list[Path]]:
    """Sessions holding more than one note, because each write was dated afresh.

    Reported, never deleted. Both files are real distillations of one session, taken from
    different parts of it, so which learnings survive a merge is a judgement the tool
    cannot make. `note_path` stops new ones; these are the ones already written.
    """
    return {
        key: notes for key, notes in sorted(notes_by_session(directory).items()) if len(notes) > 1
    }


def run_audit(directory: Path, root: Path, delete: bool) -> int:
    """Report duplicate notes, and delete the ones that are provably artifacts."""
    echoes = echo_notes(directory, root)
    splits = split_sessions(directory)

    if not echoes and not splits:
        print("distil_backlog: no duplicate notes found")
        return 0

    if echoes:
        print(f"distil_backlog: {len(echoes)} note(s) written from the distiller's own transcript:")
        for note in echoes:
            print(f"  {note.name}")

    if splits:
        print(f"distil_backlog: {len(splits)} session(s) holding more than one note:")
        for key, notes in splits.items():
            print(f"  {key}: {', '.join(note.name for note in notes)}")
        print("  Merge these by hand. Each file distils a different part of one session.")

    if not delete:
        print("Re-run with --audit --run to delete the distiller's own notes.")
        return 0

    removed = 0
    for note in echoes:
        try:
            note.unlink()
        except OSError as exc:
            print(f"distil_backlog: could not delete {note.name} ({exc})", file=sys.stderr)
            continue
        print(f"distil_backlog: deleted {note.name}")
        removed += 1

    if removed:
        session_learnings.rebuild_index(directory)
        session_learnings.vault_index.refresh()
    print(f"distil_backlog: deleted {removed} of {len(echoes)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recover second-brain learnings from sessions that never fired SessionEnd."
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="distil the backlog (default is a dry run that only lists it)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="max transcripts to distil in one invocation (default 5)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="report duplicate notes already in the vault instead of distilling",
    )
    args = parser.parse_args(argv)

    directory_raw = os.environ.get("CLAUDE_LEARNINGS_DIR", "").strip()
    if not directory_raw:
        print("distil_backlog: CLAUDE_LEARNINGS_DIR is not set", file=sys.stderr)
        return 1
    directory = Path(directory_raw)
    if not directory.is_dir():
        print(f"distil_backlog: {directory} is not a directory", file=sys.stderr)
        return 1

    if args.audit:
        return run_audit(directory, projects_root(), args.run)

    cwd = Path.cwd()
    candidates = backlog(transcripts_dir(cwd), directory)[: max(args.limit, 0)]
    if not candidates:
        print("distil_backlog: no undistilled transcripts found")
        return 0

    if not args.run:
        print(f"distil_backlog: {len(candidates)} transcript(s) without a note (dry run):")
        for path in candidates:
            print(f"  {path.name}")
        print("Re-run with --run to distil them. Each one is a `claude -p` call.")
        return 0

    wrote = 0
    for path in candidates:
        target = session_learnings.distil_transcript(str(path), path.stem, str(cwd), directory)
        if target is None:
            print(f"distil_backlog: no lesson in {path.name}")
        else:
            print(f"distil_backlog: wrote {target}")
            wrote += 1

    if wrote:
        session_learnings.rebuild_index(directory)
        session_learnings.vault_index.refresh()
    print(f"distil_backlog: {wrote} of {len(candidates)} produced a note")
    return 0


if __name__ == "__main__":
    sys.exit(main())
