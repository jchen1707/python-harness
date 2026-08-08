#!/usr/bin/env python
"""PostToolUse(Edit|Write) hook: format and autofix the file that was just edited.

Deliberately non-blocking — it always exits 0. Formatting is a fixup, not a gate;
the gate is the Stop hook in verify.py. Keeping this advisory means a formatting
hiccup can never wedge a turn.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
from pathlib import Path

# `--unfixable F401`: never auto-remove an unused import. This hook fires after every
# single edit, so in a batch it runs between the edit that adds an import and the edit
# that adds the import's first use — an F401 autofix at that moment deletes the import
# and the next edit references an undefined name. The Stop gate still runs plain
# `ruff check .`, so a genuinely unused import fails the turn and gets removed
# deliberately. Pinned by tests/test_format_hook.py.
FIX_ARGS: tuple[str, ...] = ("check", "--fix", "--unfixable", "F401")


def run(args: list[str], cwd: str) -> None:
    # Advisory hook: never fail the turn over formatting.
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(args, cwd=cwd or None, capture_output=True, timeout=60, check=False)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw or Path(raw).suffix != ".py":
        return 0

    cwd = payload.get("cwd", "")
    run(["uv", "run", "ruff", "format", raw], cwd)
    run(["uv", "run", "ruff", *FIX_ARGS, raw], cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
