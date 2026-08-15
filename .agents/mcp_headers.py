#!/usr/bin/env python
"""`headersHelper` for the remote MCP servers in `.mcp.json`.

Claude Code runs this script at connection time. It reads a JSON object of headers from
stdout and merges it into the request. It re-runs the script on reconnect, and on a
rejected credential it re-runs and retries the call once. The harness consumes stdout
itself, so the token never enters the transcript.

**Why this exists instead of `"Authorization": "Bearer ${LINEAR_API_KEY}"`.** A `${VAR}`
header needs the key in Claude Code's own environment. The Bash tool is a child process
and inherits that environment, so `echo $LINEAR_API_KEY` prints the key. A key printed
into a transcript must be rotated. Reading from the OS credential store instead means the
variable does not exist, so no careless command finds it.

**This does not put the key out of reach.** Bash runs as the same user and can run the
same lookup this script runs. What it removes is the *ambient* copy — the one that leaks
by accident, which is how this machine lost a key before. See `docs/agents/secrets.md`.

Usage: `uv run --no-sync python .agents/mcp_headers.py <slot>`

`<slot>` names the credential, not the provider, so two repositories hold two keys for the
same service. That is what binds this repository to its own Linear workspace while
`frontend-development-harness` keeps its own, with neither able to drift the other.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Slot names come from committed config, but they reach a shell, so this script validates
# them rather than trusting them. Lowercase letters, digits and dashes only.
SLOT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# A credential short enough to be a mistake rather than a key. An empty read would emit
# `Bearer ` and fail at the API with an opaque 401, which reads as "the key is wrong"
# rather than "the store is empty".
MINIMUM_LENGTH = 8

# Claude Code allows the helper 10 seconds. Fail inside that window, not at it.
LOOKUP_TIMEOUT_SECONDS = 8


def credential_path(slot: str, home: Path | None = None) -> Path:
    """Where the DPAPI-encrypted credential for `slot` lives on Windows."""
    root = home if home is not None else Path.home()
    return root / ".claude" / "mcp-credentials" / f"{slot}.cred"


def lookup_command(platform: str, slot: str, home: Path | None = None) -> list[str]:
    """The credential lookup command for a platform, as an argv list.

    Windows has no credential CLI that prints a password, so the value is stored as a
    DPAPI-encrypted string. `ConvertFrom-SecureString` binds it to this user on this
    machine: the file is inert to anyone else, and to this user on another machine.
    """
    if platform == "win32":
        # Single quotes make a PowerShell literal, where `'` is escaped by doubling.
        literal = str(credential_path(slot, home)).replace("'", "''")
        script = "; ".join(
            [
                "$ErrorActionPreference='Stop'",
                f"$enc=(Get-Content -Raw -LiteralPath '{literal}').Trim()",
                "$sec=ConvertTo-SecureString $enc",
                "$b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)",
                "try{[Runtime.InteropServices.Marshal]::PtrToStringAuto($b)}"
                "finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)}",
            ]
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
    if platform == "darwin":
        return ["security", "find-generic-password", "-s", f"claude-mcp-{slot}", "-w"]
    return ["secret-tool", "lookup", "service", f"claude-mcp-{slot}"]


def headers(token: str) -> dict[str, str]:
    """The headers Claude Code merges into the connection.

    Separated from the lookup so a test asserts the shape without a real credential.
    """
    return {"Authorization": f"Bearer {token}"}


def fail(message: str) -> int:
    """Write a diagnostic and return the failure code.

    A diagnostic names the slot and never the value. This runs with the credential in
    scope, so anything it prints is a candidate for a log the user later pastes.
    """
    sys.stderr.write(f"mcp-headers: {message}\n")
    return 1


def main(argv: list[str], platform: str = sys.platform) -> int:
    """Resolve the slot named in `argv[1]` and write its headers to stdout."""
    slot = argv[1] if len(argv) > 1 else ""
    if not SLOT_PATTERN.match(slot):
        return fail("usage: mcp_headers.py <slot>, where slot is lowercase letters, digits, dashes")

    command = lookup_command(platform, slot)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=LOOKUP_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return fail(f'could not run {command[0]} for slot "{slot}"')

    if result.returncode != 0:
        return fail(f'no credential stored for slot "{slot}"')

    token = (result.stdout or "").strip()
    if len(token) < MINIMUM_LENGTH:
        return fail(f'credential for slot "{slot}" is empty or truncated; store it again')

    sys.stdout.write(json.dumps(headers(token)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
