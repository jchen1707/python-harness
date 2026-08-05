#!/usr/bin/env python
"""Stop hook: refuse to end the turn while the Definition of Done is failing.

Smart by design — the gates only run when the turn actually touched Python under
`src/` or `tests/`. Doc, config and plan edits end freely, so prose work never
burns toward the 8-consecutive-block override that Claude Code applies to Stop
hooks.

Convergence matters: every gate here is one Claude can actually fix. A check that
can never pass just wastes 8 turns of tokens before being overridden anyway.

Escape hatch: set CLAUDE_SKIP_VERIFY=1 to disable for a session.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

GATES: tuple[tuple[str, list[str]], ...] = (
    ("ruff check", ["uv", "run", "ruff", "check", "."]),
    ("ruff format --check", ["uv", "run", "ruff", "format", "--check", "."]),
    ("mypy", ["uv", "run", "mypy"]),
    ("pytest", ["uv", "run", "pytest", "-q"]),
)

MAX_LINES = 40


def python_changed(cwd: str) -> bool:
    """True if any .py file under src/ or tests/ differs from HEAD or is untracked."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "tests"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False  # Can't tell -> don't block.

    # Porcelain format: 2 status chars, a space, then the path.
    return any(line[3:].strip().strip('"').endswith(".py") for line in result.stdout.splitlines())


def tail(text: str) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-MAX_LINES:])


def main() -> int:
    if os.environ.get("CLAUDE_SKIP_VERIFY") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd = payload.get("cwd", "")
    if not python_changed(cwd):
        return 0

    for label, args in GATES:
        try:
            result = subprocess.run(
                args,
                cwd=cwd or None,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"Could not run `{label}`: {exc}", file=sys.stderr)
            return 0  # Tooling problem, not a code problem -> don't block.

        if result.returncode != 0:
            output = tail(result.stdout + result.stderr) or "(no output)"
            # ASCII only - see protect_paths.py.
            print(
                f"Definition of Done is failing at `{label}`. Fix this before "
                f"finishing. Do not summarise the failure as if it were done.\n\n"
                f"{output}",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
