#!/usr/bin/env python
"""SessionEnd hook: distil what the session learned the hard way into the second brain.

A hook is a shell command with no model of its own, so it cannot judge which mistakes
taught something. This one does the deterministic half — locate the vault, extract the
transcript, gather git context, write the file — and shells out to a headless
`claude -p` for the one part that needs judgement.

**It writes nothing when the session taught nothing.** An empty note is worse than no
note: it dilutes the directory every later search has to sift. The distiller is told to
emit a single sentinel when there is no real lesson, and that path exits silently.

Configure with `OBSIDIAN_VAULT_DIRECTORY` (absolute path to the vault). The hook writes to
its `Project Learnings` child. Unset means disabled, which is the right default for a
harness other people clone. Set it in **user** settings, not this repo's committed
`.claude/settings.json`.

| Variable | Effect |
| --- | --- |
| `OBSIDIAN_VAULT_DIRECTORY` | Vault root. The hook writes to `Project Learnings`. |
| `CLAUDE_LEARNINGS_OFF=1` | Disable without unsetting the directory. |
| `CLAUDE_LEARNINGS_MODEL` | Model for the distillation. Default `sonnet`. |
| `CLAUDE_LEARNINGS_SKIP=1` | Recursion guard; set on the child, never set by hand. |

This hook also refreshes the whole-vault index, and does so **unconditionally** — notes
written by hand in Obsidian between sessions need indexing whether or not this particular
session produced a learning of its own.

**One note per session, overwritten.** A session distils more than once — resumed and
ended again, or recovered while still open — and naming each write from the current date
turned one session's lessons into several near-identical notes. `note_path` reuses the
note that session already has.

The recursion guard matters: the `claude -p` we spawn fires its own SessionEnd when it
finishes. Without the guard that is an infinite regress of sessions distilling sessions.
The guard covers the child *ending*; it does nothing about the transcript the child
leaves behind, which holds the prompt and the finished note. Distilling that transcript
returns the note again under a second session id. Two things stop it: the distiller runs
outside the repo (`DISTILLER_HOME`) so new child transcripts land where nothing scans,
and `is_distiller_transcript` recognises the ones already on disk.

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

# Sibling module in this directory. Hooks run as `python <abs path>/session_learnings.py`,
# so `.agents/hooks` is sys.path[0] and this resolves wherever the harness starts. mypy and
# pyright are told about the directory in pyproject.toml (`mypy_path` / `[tool.pyright]`).
import vault_index

MODEL = os.environ.get("CLAUDE_LEARNINGS_MODEL", "sonnet")
NO_LEARNINGS = "NO_LEARNINGS"
SUMMARY_PREFIX = "SUMMARY:"

# The distiller is itself a Claude Code session, so it writes its own transcript next to
# the real ones. That transcript contains the prompt *and* the finished note, so anything
# that distils it produces a copy of a note the vault already holds. This mark opens the
# prompt, which makes the child transcript identifiable: `is_distiller_transcript` reads
# the first user message and tests for it.
#
# The test is `startswith` on the first user message, not a search of the file. This repo
# edits this hook, so the mark appears as ordinary text in real sessions about it. Only a
# session whose opening prompt *is* the distillation prompt is a distiller session.
DISTILLER_MARK = "[claude-learnings-distiller]"

# Child transcripts written before the mark existed. They are still on disk, and they are
# precisely the ones the recovery script would re-distil, so recognising the mark alone
# fixes nothing that has already happened. This is the opening sentence the prompt carried
# then; a real session does not begin with it.
LEGACY_DISTILLER_OPENING = "You are writing a note for an engineer's personal knowledge base"

DISTILLER_OPENINGS = (DISTILLER_MARK, LEGACY_DISTILLER_OPENING)

# Where the distiller runs. `claude -p` files its transcript under the project directory
# for its cwd, so running it in the repo drops a child transcript into the same directory
# the recovery script scans. A fixed neutral directory keeps them out of every repo's
# backlog, and loads none of the repo's own hooks into the child.
DISTILLER_HOME = Path.home() / ".claude" / "learnings-distiller"

# The index is what a search reads first, so it must be cheap. One row per note, and no
# note bodies. `_INDEX` sorts to the top of the folder and reads as machinery, not as a
# learning — the same reason `.out-of-scope/README.md` announces that it is not a record.
INDEX_NAME = "_INDEX.md"
BASE_NAME = "LLM.base"

# The distiller reads text only, so it needs no tools. Cap what we send: transcripts run
# to megabytes, and the tail is where fixes land.
MAX_TRANSCRIPT_CHARS = 60_000
DISTILL_TIMEOUT = 240

# Below this a transcript is too short to have taught anything.
MIN_TRANSCRIPT_CHARS = 500

# Header for the note this session already has, when it is being distilled again.
PRIOR_NOTE_HEADER = "=== NOTE ALREADY WRITTEN FOR THIS SESSION ==="

PROMPT = f"""{DISTILLER_MARK}

The line above marks this call for the harness. Ignore it. Do not repeat it in your reply.

You are writing a note for an engineer's personal knowledge base, recording
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
- If the session contained no genuine learning of either kind — no mistakes, only
  routine work — reply with exactly `{NO_LEARNINGS}` and nothing else.

If a `{PRIOR_NOTE_HEADER}` section follows, it is your own earlier note for this same
session, written from an earlier part of it. Your reply replaces that file. Keep every
learning it holds, and add what the transcript below teaches on top. State each learning
once. The transcript you receive is only the most recent part of the session, so the
earlier note is the only record of what came before it.

Start your reply with one line, exactly in this form:

{SUMMARY_PREFIX} <one sentence naming the topics covered, under 25 words>

That line is the only thing a search reads before deciding whether to open this note, so
name the concrete subjects — the tool, the system, the concept. Write "mypy file scope and
stacked-PR merge targets", not "various tooling lessons".

Then a blank line, then the first `##` heading. No other preamble, no closing summary.

Output GitHub-flavoured Markdown. Do not include front matter; it is added for you."""


def run(args: list[str], cwd: str | None = None, timeout: int = 30) -> str:
    """Run a command and return stdout, or an empty string on any failure.

    `encoding` is explicit on purpose: `text=True` alone decodes with the *locale*
    codec, which is cp1252 on Windows, so any UTF-8 the child emits comes back as
    mojibake (`—` arriving as `â€"`).
    """
    try:
        result = subprocess.run(
            args,
            cwd=cwd or None,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
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
        if block.get("type") in {"text", "input_text", "output_text"} and isinstance(
            block.get("text"), str
        ):
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
            payload = entry.get("payload")
            message = payload if isinstance(payload, dict) and "role" in payload else None
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


def first_user_message(path: str, max_lines: int = 50) -> str:
    """Text of the transcript's first user message, or "" if it has none.

    Bounded on purpose. A real transcript runs to megabytes, and the opening prompt is
    within the first few entries of any of them.
    """
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as handle:
            for index, line in enumerate(handle):
                if index >= max_lines:
                    break
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    payload = entry.get("payload")
                    message = payload if isinstance(payload, dict) and "role" in payload else None
                if not isinstance(message, dict) or message.get("role") != "user":
                    continue
                content = message.get("content")
                blocks = content if isinstance(content, list) else [content]
                return " ".join(t for t in (extract_text(b) for b in blocks) if t).strip()
    except OSError:
        return ""
    return ""


def is_distiller_transcript(path: str) -> bool:
    """True when this transcript is one of our own `claude -p` distillation calls.

    Such a transcript holds the prompt and the finished note, so distilling it returns
    that note again — the same lesson under a second session id. Every note the vault
    gained twice in identical form came from here.
    """
    return first_user_message(path).startswith(DISTILLER_OPENINGS)


def distil(transcript: str, context: str, prior: str = "") -> str:
    """Ask a headless Claude for the lessons. Empty string means 'write nothing'.

    `prior` is the note this session already has, when it is being distilled a second
    time. It is passed back in because the reply overwrites that note, and the transcript
    only carries the most recent `MAX_TRANSCRIPT_CHARS` — so without it, a resumed session
    loses everything its first distillation found.
    """
    child_env = {**os.environ, "CLAUDE_LEARNINGS_SKIP": "1"}
    earlier = f"\n\n{PRIOR_NOTE_HEADER}\n{prior}" if prior.strip() else ""
    payload = (
        f"{PROMPT}\n\n=== GIT CONTEXT ===\n{context}{earlier}\n\n=== TRANSCRIPT ===\n{transcript}"
    )

    # Run outside the repo so the child's own transcript files under a project directory
    # nothing scans. The distiller reads text and uses no tools, so it needs no repo.
    try:
        DISTILLER_HOME.mkdir(parents=True, exist_ok=True)
        home = str(DISTILLER_HOME)
    except OSError:
        home = None  # Fall back to the inherited cwd; is_distiller_transcript still holds.

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", MODEL],
            input=payload,
            cwd=home,
            capture_output=True,
            encoding="utf-8",  # Not text=True: see run(). The model emits em-dashes.
            errors="replace",
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


def short_id(session_id: str) -> str:
    """The session id as it appears in a note filename."""
    return re.sub(r"[^a-zA-Z0-9]", "", session_id)[:8] or "session"


def existing_note(directory: Path, session_id: str) -> Path | None:
    """The note already written for this session, whatever date it carries.

    Matching ignores the date prefix on purpose. The session id is the identity; the
    date is only how the folder sorts.
    """
    found = sorted(directory.glob(f"* {short_id(session_id)}.md"))
    return found[0] if found else None


def note_path(directory: Path, project: str, session_id: str) -> Path:
    """Where this session's note goes. One note per session, overwritten in place.

    A session distils more than once — it is resumed and ends again, or the recovery
    script reaches a transcript that was still open. Naming the file from
    `datetime.now()` every time makes each of those a *new* note, so one session's
    lessons land in the vault two and three times over and every search returns them
    repeatedly. Reusing the existing note keeps the newest distillation and one file.
    """
    found = existing_note(directory, session_id)
    if found is not None:
        return found
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    return directory / f"{stamp} {project} {short_id(session_id)}.md"


def split_summary(body: str) -> tuple[str, str]:
    """Separate the `SUMMARY:` line from the note body. Missing prefix is not fatal."""
    first, _, rest = body.partition("\n")
    if first.strip().startswith(SUMMARY_PREFIX):
        return first.strip()[len(SUMMARY_PREFIX) :].strip(), rest.lstrip("\n")
    return "", body


def read_front_matter(path: Path) -> dict[str, str]:
    """Front matter of one note, or an empty dict if it has none or cannot be read.

    The parsing itself lives in `vault_index.front_matter` — one parser, so the index
    this hook writes and the whole-vault index cannot disagree about what a note says.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    return vault_index.front_matter(text)


def prior_note(target: Path) -> str:
    """Body of the note this session already has, or "" when there is none.

    Front matter is stripped: the distiller is asked for a body, and handing it back the
    `summary:` line it wrote invites it to reproduce that line inside the note.
    """
    try:
        return vault_index.body(target.read_text(encoding="utf-8", errors="replace")).strip()
    except OSError:
        return ""


def rebuild_index(directory: Path) -> None:
    """Regenerate `_INDEX.md` from every note's front matter.

    Rebuilt rather than appended. An append-only index drifts the moment a note is
    edited, renamed or deleted by hand, and a stale index is worse than none — a search
    that trusts it silently misses notes.
    """
    rows: list[tuple[str, str, str, str]] = []
    for note in sorted(directory.glob("*.md"), reverse=True):
        if note.name == INDEX_NAME:
            continue
        fields = read_front_matter(note)
        if not fields:
            continue
        rows.append(
            (
                fields.get("date", ""),
                fields.get("project", ""),
                fields.get("summary", ""),
                note.stem,
            )
        )

    lines = [
        "---",
        "tags: [project-learnings-index]",
        "---",
        "",
        "# Learnings index",
        "",
        "Generated by the `SessionEnd` hook. Do not edit: it is rebuilt on every write.",
        "",
        "Search this file first, then open only the notes whose summary matches. Reading",
        "every note to answer one question is the cost this index exists to avoid.",
        "",
        f"{len(rows)} notes.",
        "",
        "| Date | Project | Summary | Note |",
        "| --- | --- | --- | --- |",
    ]
    for date, project, summary, stem in rows:
        clean = summary.replace("|", "\\|")
        lines.append(f"| {date} | {project} | {clean} | [[{stem}]] |")

    try:
        # newline="\n": see the note on the same call in vault_index.refresh(). Every
        # writer of this vault must agree on the line ending or the file churns.
        (directory / INDEX_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"session_learnings: could not write index ({exc})", file=sys.stderr)


def distil_transcript(
    transcript_path: str, session_id: str, cwd: str, directory: Path
) -> Path | None:
    """Distil one transcript into a dated note. Returns the note path, or None.

    None means the transcript belongs to the distiller itself, was too short, taught no
    lesson, or could not be written — the caller cannot tell which, and does not need to:
    in every case there is no note to index. Shared by the SessionEnd path (`main`) and
    the recovery path (`distil_backlog.py`), so the two cannot drift on what a note is.
    """
    if is_distiller_transcript(transcript_path):
        return None

    transcript = read_transcript(transcript_path)
    if len(transcript) < MIN_TRANSCRIPT_CHARS:
        return None

    project = Path(cwd).name or "session"
    target = note_path(directory, project, session_id)

    body = distil(transcript, git_context(cwd), prior_note(target))
    if not body:
        return None  # Nothing new. Any note this session already has stays as it is.

    summary, body = split_summary(body)
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M")
    front = (
        "---\n"
        f"date: {stamp}\n"
        f"project: {project}\n"
        f"session: {session_id}\n"
        f"summary: {summary}\n"
        "tags: [project-learnings, session-retro]\n"
        "---\n\n"
        f"# {project} — session learnings ({stamp})\n\n"
    )

    try:
        target.write_text(front + body + "\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"session_learnings: could not write {target} ({exc})", file=sys.stderr)
        return None
    return target


def main() -> int:
    if os.environ.get("CLAUDE_LEARNINGS_SKIP") == "1":
        return 0  # We are the distiller's own session ending. Do not recurse.
    if os.environ.get("CLAUDE_LEARNINGS_OFF") == "1":
        return 0

    # Unconditional, and before every early return below: the vault gains hand-written
    # notes between sessions, and those need indexing even when this session distilled
    # nothing. Returns None and stays quiet when no vault is configured.
    vault_index.refresh()

    vault = vault_index.vault_dir()
    if vault is None:
        return 0  # Not configured -> not this clone's business.

    directory = vault / "Project Learnings"
    if not directory.is_dir():
        print(f"session_learnings: {directory} is not a directory", file=sys.stderr)
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd = payload.get("cwd", "") or os.getcwd()
    target = distil_transcript(
        payload.get("transcript_path", ""), str(payload.get("session_id", "")), cwd, directory
    )
    if target is None:
        return 0

    rebuild_index(directory)
    print(f"session_learnings: wrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
