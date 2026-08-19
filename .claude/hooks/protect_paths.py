#!/usr/bin/env python
"""PreToolUse hook: refuse edits to human-owned paths.

Exit 2 is the ONLY exit code that blocks a tool call; stderr becomes the reason
Claude sees. Exit 1 would let the write through with a warning, which is the most
common hook bug.

**The matcher must cover every tool that can write a file, not just `Edit|Write`.**
A hook matcher is a case-sensitive regex over the tool name, so `Edit|Write` misses
`NotebookEdit` and every MCP write tool — including `mcp__pyright-lsp__edit_file`,
which this repo enables in `.mcp.json`. A protected path is only protected on the
tool surfaces the matcher names. See `.claude/settings.json`.

Claude sends `tool_input.file_path`. Codex sends an `apply_patch` body in
`tool_input.command`. The hook accepts both forms.
"""

from __future__ import annotations

import json
import posixpath
import sys
from fnmatch import fnmatch
from typing import Any

# Globs matched against the repo-relative, forward-slashed path.
PROTECTED: tuple[tuple[str, str], ...] = (
    (".env", "holds real secrets and is gitignored"),
    (".env.*", "holds real secrets and is gitignored"),
    ("**/migrations/**", "schema migrations are irreversible - a human applies these"),
    ("**/generated/**", "generated output; change the generator instead"),
    ("uv.lock", "regenerate with `uv lock`, never hand-edit"),
)

ALLOWED = (".env.example",)

PATCH_PATH_PREFIXES = ("*** Add File: ", "*** Update File: ", "*** Delete File: ")


def relative_path(raw: str, project_dir: str) -> str:
    path = raw.replace("\\", "/")
    root = project_dir.replace("\\", "/").rstrip("/")
    if root and path.lower().startswith(root.lower() + "/"):
        path = path[len(root) + 1 :]
    # removeprefix, not lstrip: lstrip("./") would strip the leading dot of a
    # dotfile, turning ".env" into "env" and silently defeating the match.
    return posixpath.normpath(path).removeprefix("./")


def edited_paths(tool_input: object) -> list[str]:
    """Return paths from Claude file tools or a Codex apply_patch call."""
    if not isinstance(tool_input, dict):
        return []
    values: dict[str, Any] = tool_input
    raw = values.get("file_path")
    if isinstance(raw, str):
        return [raw]

    patch = values.get("command", values.get("patch"))
    if not isinstance(patch, str):
        return []
    return [
        line.removeprefix(prefix)
        for line in patch.splitlines()
        for prefix in PATCH_PATH_PREFIXES
        if line.startswith(prefix)
    ]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # Never block because the hook itself failed to parse.

    for raw in edited_paths(payload.get("tool_input")):
        path = relative_path(raw, payload.get("cwd", ""))
        name = posixpath.basename(path)

        if name in ALLOWED:
            continue

        for pattern, why in PROTECTED:
            if fnmatch(path, pattern) or fnmatch(name, pattern):
                # ASCII only: hook stderr is decoded by the harness, and a Windows
                # console codepage can mangle non-ASCII on the way out.
                print(
                    f"Refusing to edit {path} - {why}.\n"
                    "Ask the user to make this change, or explain why it is required.",
                    file=sys.stderr,
                )
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
