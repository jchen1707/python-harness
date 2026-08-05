#!/usr/bin/env python
"""SessionEnd hook: distil what the session learned the hard way into the second brain.

A hook is a shell command with no model of its own, so it cannot judge which mistakes
taught something. This one does the deterministic half — locate the vault, extract the
transcript, gather git context, write the file — and shells out to a headless
`claude -p` for the one part that needs judgement.

**It writes nothing when the session taught nothing.** An empty note is worse than no
note: it dilutes the directory every later search has to sift. The distiller is told to
emit a single sentinel when there is no real lesson, and that path exits silently.

Configure with `CLAUDE_LEARNINGS_DIR` (absolute path to the notes directory). Unset means
disabled, which is the right default for a harness other people clone — nobody inherits a
path to somebody else's vault. Set it in **user** settings, not this repo's committed
`.claude/settings.json`.

| Variable | Effect |
| --- | --- |
| `CLAUDE_LEARNINGS_DIR` | Where notes are written. Unset -> hook does nothing. |
| `CLAUDE_LEARNINGS_OFF=1` | Disable without unsetting the directory. |
| `CLAUDE_LEARNINGS_MODEL` | Model for the distillation. Default `sonnet`. |
| `CLAUDE_LEARNINGS_SKIP=1` | Recursion guard; set on the child, never set by hand. |

The recursion guard matters: the `claude -p` we spawn fires its own SessionEnd when it
finishes. Without the guard that is an infinite regress of sessions distilling sessions.

Never blocks. Every failure path exits 0 — a second brain that cannot be written is not a
reason to interfere with ending a session.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

MODEL = os.environ.get("CLAUDE_LEARNINGS_MODEL", "sonnet")
NO_LEARNINGS = "NO_LEARNINGS"

# The distiller reads text only, so it needs no tools. Cap what we send: transcripts run
# to megabytes, and the tail is where fixes land.
MAX_TRANSCRIPT_CHARS = 60_000
DISTILL_TIMEOUT = 240

PROMPT = f"""You are writing a note for an engineer's personal knowledge base, recording
what a coding session taught them. Someone will read this months from now with no memory
of the session.

Below is a transcript, plus the git context of what changed.

Extract only **technical learnings that came from a mistake, a wrong assumption, or
friction that was then resolved**. The value is in what was believed, why it was wrong,
and what turned out to be true.

Ignore: what the session accomplished, features shipped, files touched, anything that
reads like a changelog. That is recoverable from git. A learning is not.

Split the findings into exactly these two sections:

## Implementation learnings

Low-level and concrete. Tool flags and their real behaviour, API and config semantics,
environment and platform quirks, error messages and what actually causes them, commands
that do not do what their name implies.

## Architecture & design learnings

Higher-level and transferable. Why a structure resisted a change, where a boundary was
drawn wrongly, a design tension and how it resolved, a rule that turned out to have an
exception, a process or workflow that broke down and why.

Rules:
- Every entry states the wrong belief and the correction. "X, not Y — because Z."
- Be specific. Name the tool, flag, file or concept. A vague lesson teaches nothing.
- Omit a section entirely if nothing qualifies. Do not pad it.
- No preamble, no closing summary. Start at the first `##` heading.
- If the session contained no genuine learning of either kind — no mistakes, only
  routine work — reply with exactly `{NO_LEARNINGS}` and nothing else.

Output GitHub-flavoured Markdown. Do not include front matter; it is added for you."""


def run(args: list[str], cwd: str | None = None, timeout: int = 30) -> str:
    """Run a command and return stdout, or an empty string on any failure."""
    try:
        result = subprocess.run(
            args, cwd=cwd or None, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def git_context(cwd: str) -> str:
    """Branch, recent commits and dirty files — the facts a model should not have to infer."""
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd) or "(unknown)"
    log = run(["git", "log", "--oneline", "-15"], cwd)
    status = run(["git", "status", "--porcelain"], cwd)
    parts = [f"Branch: {branch}"]
    if log:
        parts.append(f"Recent commits:\n{log}")
    if status:
        parts.append(f"Uncommitted:\n{status}")
    return "\n\n".join(parts)


def extract_text(block: object) -> str:
    """Pull readable text out of one content block, whatever shape it arrived in."""
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            return block["text"]
        if block.get("type") == "tool_use" and isinstance(block.get("name"), str):
            return f"[tool: {block['name']}]"
    return ""


def read_transcript(path: str) -> str:
    """Flatten the transcript JSONL into plain text, keeping the most recent tail."""
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    lines: list[str] = []
    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role", "?")
        content = message.get("content")
        blocks = content if isinstance(content, list) else [content]
        text = " ".join(t for t in (extract_text(b) for b in blocks) if t).strip()
        if text:
            lines.append(f"{role}: {text}")

    joined = "\n".join(lines)
    return joined[-MAX_TRANSCRIPT_CHARS:] if len(joined) > MAX_TRANSCRIPT_CHARS else joined


def distil(transcript: str, context: str) -> str:
    """Ask a headless Claude for the lessons. Empty string means 'write nothing'."""
    child_env = {**os.environ, "CLAUDE_LEARNINGS_SKIP": "1"}
    payload = f"{PROMPT}\n\n=== GIT CONTEXT ===\n{context}\n\n=== TRANSCRIPT ===\n{transcript}"
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", MODEL],
            input=payload,
            capture_output=True,
            text=True,
            timeout=DISTILL_TIMEOUT,
            check=False,
            env=child_env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"session_learnings: could not distil ({exc})", file=sys.stderr)
        return ""

    if result.returncode != 0:
        print(f"session_learnings: claude exited {result.returncode}", file=sys.stderr)
        return ""

    body = result.stdout.strip()
    return "" if not body or body.startswith(NO_LEARNINGS) else body


def note_path(directory: Path, project: str, session_id: str) -> Path:
    """Dated, project-scoped, session-suffixed so two sessions a day cannot collide."""
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    short = re.sub(r"[^a-zA-Z0-9]", "", session_id)[:8] or "session"
    return directory / f"{stamp} {project} {short}.md"


def main() -> int:
    if os.environ.get("CLAUDE_LEARNINGS_SKIP") == "1":
        return 0  # We are the distiller's own session ending. Do not recurse.
    if os.environ.get("CLAUDE_LEARNINGS_OFF") == "1":
        return 0

    directory_raw = os.environ.get("CLAUDE_LEARNINGS_DIR", "").strip()
    if not directory_raw:
        return 0  # Not configured -> not this clone's business.

    directory = Path(directory_raw)
    if not directory.is_dir():
        print(f"session_learnings: {directory} is not a directory", file=sys.stderr)
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd = payload.get("cwd", "") or os.getcwd()
    transcript = read_transcript(payload.get("transcript_path", ""))
    if len(transcript) < 500:
        return 0  # Too short to have taught anything.

    body = distil(transcript, git_context(cwd))
    if not body:
        return 0

    project = Path(cwd).name or "session"
    session_id = str(payload.get("session_id", ""))
    target = note_path(directory, project, session_id)
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M")
    front = (
        "---\n"
        f"date: {stamp}\n"
        f"project: {project}\n"
        f"session: {session_id}\n"
        "tags: [project-learnings, session-retro]\n"
        "---\n\n"
        f"# {project} — session learnings ({stamp})\n\n"
    )

    try:
        target.write_text(front + body + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"session_learnings: could not write {target} ({exc})", file=sys.stderr)
        return 0

    print(f"session_learnings: wrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
