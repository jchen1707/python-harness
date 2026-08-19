#!/usr/bin/env python
"""Stop hook: refuse to end the turn while the Definition of Done is failing.

Smart by design — the gates only run when the turn touched something that can
actually make them fail. That is the line: **code the gates check, plus the config
that defines the gates**. Prose, plans and docs still end freely, so writing work
never burns toward the 8-consecutive-block override Claude Code applies to Stop
hooks.

Three path groups qualify (see GATED_PATHS / GATED_FILES):

- `src/`, `tests/` — the application and its tests.
- `.agents/hooks/` — these scripts. They are Python, ruff lints them and mypy type
  checks them, so a broken edit here fails the same gates as `src/`. Leaving them
  out meant the enforcement layer was the one thing the walk-away gate could not
  catch.
- `pyproject.toml` — configures ruff, mypy and pytest. A change here can break
  every gate at once while touching no Python at all.
- `.claude/settings.json` — wires the hooks themselves, and the pytest suite pins
  its matchers (`tests/test_hook_matchers.py`). A broken matcher edit fails the
  gates while touching no Python, so it belongs in the gated set for the same
  reason `pyproject.toml` does.
- `.agents/mcp_headers.py` — resolves the Linear credential at connection time. It
  is Python that ruff and mypy check, and it sits outside `.agents/hooks/` because
  it is not a hook, so it is named as a file rather than covered by a directory.

The tradeoff this balances: widening the filter costs some override budget on
config work, but the excluded set that motivated the original narrow filter —
markdown, plans, docs — is still excluded, and those are what sessions actually
churn on. Editing a hook or the tool config is rare and deserves the gate.

Convergence matters: every gate here is one Claude can actually fix. A check that
can never pass just wastes 8 turns of tokens before being overridden anyway.

Escape hatch: set HARNESS_SKIP_VERIFY=1 to disable for a session. The legacy
CLAUDE_SKIP_VERIFY name remains supported.
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

# Directories whose .py files the gates check. See the module docstring.
GATED_PATHS: tuple[str, ...] = ("src", "tests", ".agents/hooks")

# Individual files that configure the gates themselves; a change breaks them
# without touching any Python.
GATED_FILES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        ".agents/mcp_headers.py",
        ".claude/settings.json",
        # harness:agnostic
        ".codex/config.toml",
        ".codex/hooks.json",
        # /harness:agnostic
    }
)


def porcelain_path(line: str) -> str:
    """Extract the path from one `git status --porcelain` line.

    Format is two status chars, a space, then the path. Renames and copies read
    `old -> new`; the destination is the one that exists on disk. Paths containing
    special characters are quoted.
    """
    entry = line[3:].strip()
    return entry.rpartition(" -> ")[2].strip().strip('"')


def gated_change(cwd: str) -> bool:
    """True if the turn touched gated Python or the tool config that gates it."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", *GATED_PATHS, *sorted(GATED_FILES)],
            cwd=cwd or None,
            capture_output=True,
            # Explicit, not text=True: that decodes with the locale codec (cp1252 on
            # Windows), mangling any non-ASCII path git reports back.
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False  # Can't tell -> don't block.

    for line in result.stdout.splitlines():
        path = porcelain_path(line)
        if path.endswith(".py") or path in GATED_FILES:
            return True
    return False


def tail(text: str) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-MAX_LINES:])


def main() -> int:
    if os.environ.get("HARNESS_SKIP_VERIFY") == "1" or os.environ.get("CLAUDE_SKIP_VERIFY") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    cwd = payload.get("cwd", "")
    if not gated_change(cwd):
        return 0

    for label, args in GATES:
        try:
            result = subprocess.run(
                args,
                cwd=cwd or None,
                capture_output=True,
                # ruff and mypy emit em-dashes and curly quotes in diagnostics; decoding
                # them with the locale codec corrupts the very message we echo back.
                encoding="utf-8",
                errors="replace",
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
