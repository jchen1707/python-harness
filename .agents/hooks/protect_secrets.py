#!/usr/bin/env python
"""Block common Codex reads that would copy a secret into the transcript."""

from __future__ import annotations

import json
import posixpath
import re
import sys
from typing import Any

SECRET_FILES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.development",
        ".env.production",
        ".env.staging",
        ".env.test",
    }
)

ENV_DUMPS = re.compile(
    r"^(?:env|printenv|set|export(?:\s+-p)?|declare\s+-x|typeset\s+-x|compgen\s+-e|"
    r"Get-ChildItem\s+Env:|gci\s+Env:|ls\s+Env:|dir\s+Env:|Get-Variable)(?:\s|$)",
    re.IGNORECASE,
)
SECRET_EXPANSIONS = re.compile(r"(?:LINEAR_API_KEY|GH_TOKEN)", re.IGNORECASE)
INLINE_INTERPRETERS = re.compile(
    r"^(?:python|python3|uv\s+run\s+python)\s+-c(?:\s|$)|^node\s+-(?:e|p)(?:\s|$)"
)


def input_values(value: object) -> dict[str, Any]:
    """Return a typed view of a hook tool input."""
    return value if isinstance(value, dict) else {}


def secret_path(values: dict[str, Any]) -> str | None:
    """Return a protected secret path from a read-tool input."""
    for key in ("file_path", "path"):
        raw = values.get(key)
        if not isinstance(raw, str):
            continue
        name = posixpath.basename(raw.replace("\\", "/"))
        if name in SECRET_FILES or (name.startswith(".env.") and name.endswith(".local")):
            return raw
    return None


def unsafe_command(values: dict[str, Any]) -> str | None:
    """Return the reason for an unsafe shell command."""
    command = values.get("command")
    if not isinstance(command, str):
        return None
    stripped = command.strip()
    if ENV_DUMPS.match(stripped):
        return "the command dumps environment variables"
    if SECRET_EXPANSIONS.search(stripped):
        return "the command references a protected secret variable"
    if INLINE_INTERPRETERS.match(stripped):
        return "inline interpreters can read inherited secrets"
    if re.search(
        r"(?:cat|type|more|less|head|tail|nl|strings|Get-Content|gc)\s+\.?/?\.env(?:\s|$)", stripped
    ):
        return "the command reads a secret file"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    values = input_values(payload.get("tool_input"))
    path = secret_path(values)
    reason = unsafe_command(values)
    if path is None and reason is None:
        return 0

    detail = f"reading {path} would expose a secret" if path is not None else str(reason)
    print(f"Refusing tool call - {detail}.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
