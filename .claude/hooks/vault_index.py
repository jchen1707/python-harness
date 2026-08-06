#!/usr/bin/env python
"""Build an agent-readable index of the whole vault, not only the learnings folder.

An Obsidian `.base` file is a **query**, evaluated by Obsidian's own UI. An agent that
reads `LLM.base` gets the query definition back, never its results — so a Base makes the
vault browsable for a human and does nothing at all for retrieval by Claude. The
agent-readable half has to be generated Markdown. `session_learnings.py` already writes
one for the learnings folder; this writes one for every note in the vault.

**Rows are derived, not required.** Most hand-written notes carry no front matter, and an
index that only lists notes with a `summary:` field would start out covering a fraction
of the vault and silently stay there. Front matter is used when present and inferred when
not: the description falls back to the first line of real prose.

Configure with `CLAUDE_VAULT_DIR`. Unset falls back to the parent of
`CLAUDE_LEARNINGS_DIR`, so the usual layout — a learnings folder sitting inside a vault —
needs no new configuration. Both unset means there is no vault, and this does nothing.

Refresh by hand with `uv run python .claude/hooks/vault_index.py`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

INDEX_NAME = "_VAULT_INDEX.md"

# Folders holding no indexable prose. `.obsidian` is editor config; an Excalidraw note is
# a base64 drawing payload wearing a `.md` extension, so its "first line of prose" is
# kilobytes of encoded binary.
SKIP_DIRS = frozenset({".obsidian", ".trash", ".git", "Excalidraw", "Attachments"})

# Generated indexes, this one included. Indexing an index yields a row that says nothing
# and grows every time the thing it describes does.
SKIP_NAMES = frozenset({INDEX_NAME, "_INDEX.md"})

MAX_DESC = 160

# Shortest line worth treating as a description. Below this it is a fragment — a stray
# word, a table cell — and the next line is a better answer.
MIN_DESC = 25

# Lines that carry no information about what a note covers: headings, bullets, table rows
# and rules, fences, images, and front-matter delimiters.
NOISE = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+\.\s|\||```|!\[|-{3,}\s*$|={3,}\s*$)")

# A short line built around a wikilink points at another note rather than describing this
# one. Whole folders here open with a shared pointer — "Refer to [[Template]] for
# guidelines", "Follows [[Framework]] — one section per step" — which would hand a dozen
# unrelated notes the same description and make the index useless for choosing between
# them. Long lines are exempt: those carry their own content after the reference.
CROSS_REFERENCE = re.compile(r"\[\[")
CROSS_REFERENCE_MAX = 100


def unquote(line: str) -> str:
    """Strip blockquote and Obsidian callout markers, keeping the text inside.

    Separate from `strip_markdown` because the noise test has to run on the *unwrapped*
    line: a bullet nested in a callout (`>> - **Now:** ...`) is still a bullet, and
    testing the raw line lets it through as though it were prose.
    """
    line = re.sub(r"^\s*>+\s*", "", line)
    return re.sub(r"^\[![a-z]+\][-+]?\s*", "", line, flags=re.IGNORECASE)


def strip_markdown(line: str) -> str:
    """Reduce one line of Markdown to the text a human would read aloud."""
    line = unquote(line)
    line = re.sub(r"!?\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", line)  # wikilink
    line = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", line)  # inline link
    line = re.sub(r"[*_`~]+", "", line)  # emphasis and code ticks
    return line.strip()


def front_matter(text: str) -> dict[str, str]:
    """Parse the flat `key: value` front matter these notes use.

    Deliberately not a YAML parser: the harness has no runtime dependencies. Block
    sequences (`tags:` then an indented `- hashmap`) fold into a comma-joined string,
    because inline `[a, b]` and block form are the only two shapes the vault contains and
    callers want one of them.
    """
    if not text.startswith("---"):
        return {}
    _, _, after = text.partition("---\n")
    block, closed, _ = after.partition("\n---")
    if not closed:
        return {}  # Unterminated front matter is body text that happens to start with a rule.

    fields: dict[str, str] = {}
    key = ""
    for line in block.splitlines():
        item = re.match(r"\s+-\s+(.*)", line)
        if item and key:
            fields[key] = f"{fields[key]}, {item.group(1).strip()}".lstrip(", ")
            continue
        name, colon, value = line.partition(":")
        if colon:
            key = name.strip()
            fields[key] = value.strip().strip("[]")
    return fields


def body(text: str) -> str:
    """The note with its front matter removed."""
    if not text.startswith("---"):
        return text
    _, _, after = text.partition("---\n")
    _, closed, rest = after.partition("\n---")
    return rest if closed else text


def truncate(text: str) -> str:
    """Collapse whitespace and cut to MAX_DESC on a word boundary."""
    text = " ".join(text.split())
    if len(text) <= MAX_DESC:
        return text
    return text[:MAX_DESC].rsplit(" ", 1)[0] + "…"


def describe(text: str) -> str:
    """One line saying what a note covers.

    A `summary:` field wins: the SessionEnd hook writes one, and anything hand-written
    beats anything inferred. Otherwise take the first line of real prose.
    """
    summary = front_matter(text).get("summary", "")
    if summary:
        return truncate(summary)

    pointer = ""
    for quoted in body(text).splitlines():
        raw = unquote(quoted)
        if NOISE.match(raw):
            continue
        line = strip_markdown(raw)
        if len(line) < MIN_DESC:
            continue
        if CROSS_REFERENCE.search(raw) and len(line) < CROSS_REFERENCE_MAX:
            pointer = pointer or line  # Keep looking, but do not come back empty-handed.
            continue
        return truncate(line)
    return truncate(pointer)


def notes(vault: Path) -> list[Path]:
    """Every indexable note in the vault, ordered by path."""
    found: list[Path] = []
    for path in vault.rglob("*.md"):
        relative = path.relative_to(vault)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]):
            continue
        if path.name in SKIP_NAMES:
            continue
        found.append(path)
    return sorted(found, key=lambda p: p.relative_to(vault).as_posix().lower())


def build(vault: Path) -> str:
    """Render the whole index. Pure: reads notes, returns Markdown, writes nothing."""
    rows: list[tuple[str, str, str]] = []
    for path in notes(vault):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # A note we cannot read is one row missing, not a failed index.
        rows.append(
            (
                path.relative_to(vault).as_posix(),
                front_matter(text).get("tags", ""),
                describe(text),
            )
        )

    lines = [
        "---",
        "tags: [vault-index]",
        "---",
        "",
        "# Vault index",
        "",
        "Generated - do not edit. Rebuilt by `vault_index.py` when a Claude Code session",
        "ends in the repo that installs it. Notes written from anywhere else appear here",
        "only after the next such session. Run that hook directly to refresh sooner.",
        "",
        "One row per note. Read this first, then open only the notes whose row matches.",
        "Reading every note to answer one question is the cost this file exists to avoid.",
        "",
        "Paths are relative to the vault root, so a row is directly readable. The",
        "session notes under `Project Learnings/` carry a second, richer index in",
        "`Project Learnings/_INDEX.md`, which adds their date and originating project.",
        "",
        f"{len(rows)} notes.",
        "",
        "| Note | Tags | What it covers |",
        "| --- | --- | --- |",
    ]
    for path_text, tags, description in rows:
        cells = (f"`{path_text}`", tags, description)
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    return "\n".join(lines) + "\n"


def vault_dir() -> Path | None:
    """The vault root, or None when no vault is configured or the path is not a directory."""
    raw = os.environ.get("CLAUDE_VAULT_DIR", "").strip()
    if not raw:
        learnings = os.environ.get("CLAUDE_LEARNINGS_DIR", "").strip()
        if not learnings:
            return None
        raw = str(Path(learnings).parent)
    path = Path(raw)
    return path if path.is_dir() else None


def refresh() -> Path | None:
    """Rebuild the index. Returns the file written, or None if there was nothing to do.

    Never raises. This runs from a SessionEnd hook, and a vault that cannot be indexed is
    not a reason to interfere with ending a session.
    """
    vault = vault_dir()
    if vault is None:
        return None
    target = vault / INDEX_NAME
    try:
        # newline="\n": the default translates every \n to os.linesep, so a Windows
        # writer emits CRLF and a Linux one LF. One writer never surfaced that; several
        # repos sharing a vault rewrite the file end to end whenever the platform changes.
        target.write_text(build(vault), encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"vault_index: could not write {target} ({exc})", file=sys.stderr)
        return None
    return target


def main() -> int:
    written = refresh()
    if written is None:
        print(
            "vault_index: no vault configured - set CLAUDE_VAULT_DIR or CLAUDE_LEARNINGS_DIR",
            file=sys.stderr,
        )
        return 0
    print(f"vault_index: wrote {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
