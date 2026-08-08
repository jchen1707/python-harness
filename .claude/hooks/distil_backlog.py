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

Two caveats, both accepted:

- A session that is **still open** shows up in the backlog too — it has a transcript
  and no note. Distilling it writes a partial note; when the session later ends on
  the same UTC day, SessionEnd overwrites it with the full one. Across a day
  boundary the two notes coexist and the older one is yours to delete.
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
    short = re.sub(r"[^a-zA-Z0-9]", "", session_id)[:8] or "session"
    return any(directory.glob(f"* {short}.md"))


def backlog(transcripts: Path, directory: Path) -> list[Path]:
    """Transcripts with no matching note, newest first."""
    if not transcripts.is_dir():
        return []
    missing = [p for p in transcripts.glob("*.jsonl") if not has_note(directory, p.stem)]
    return sorted(missing, key=lambda p: p.stat().st_mtime, reverse=True)


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
    args = parser.parse_args(argv)

    directory_raw = os.environ.get("CLAUDE_LEARNINGS_DIR", "").strip()
    if not directory_raw:
        print("distil_backlog: CLAUDE_LEARNINGS_DIR is not set", file=sys.stderr)
        return 1
    directory = Path(directory_raw)
    if not directory.is_dir():
        print(f"distil_backlog: {directory} is not a directory", file=sys.stderr)
        return 1

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
