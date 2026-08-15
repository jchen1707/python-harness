#!/usr/bin/env python
"""Launch session distillation outside Codex's three-second SessionEnd limit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    script = Path(__file__).with_name("session_learnings.py")
    try:
        process = subprocess.Popen(
            [sys.executable, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if process.stdin is not None:
            process.stdin.write(json.dumps(payload).encode("utf-8"))
            process.stdin.close()
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
