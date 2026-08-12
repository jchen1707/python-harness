"""Guardrail tests for the two halves of secret containment.

`protect_paths.py` stops an agent **writing** `.env`. Nothing stopped it **reading** one.
A read is the worse failure: the literal key lands in the transcript, in context, and in
the request body, and no later edit removes it. Rotation is the only remedy.

The read block cannot live in the PreToolUse matcher. `tests/test_hook_matchers.py` pins
that matcher to write tools only, because both hooks shell out to `uv run` and firing them
on every Read and Bash would tax the whole session. So the read block lives in
`permissions.deny`, which the harness evaluates natively at no cost.

Deny rules are asserted as literal strings, not by simulating the match. That is the same
weakest-assumption choice `test_hook_matchers.py` makes: pin which rules our config
carries, and leave the matching semantics to the harness that owns them.

The file rules cover only one store. `GH_TOKEN` lives in an OS user variable, so the
session inherits it and every Bash subprocess inherits it in turn. No file rule reaches
that path. The environment rules below close the whole-environment dumps, the common
single-variable expansions, and the inline interpreters.

`LINEAR_API_KEY` no longer lives in the environment at all: `.mcp.json` resolves the key
through `.claude/mcp_headers.py` at connection time, so no variable exists to read. Its
rules stay because they cost nothing and would catch a re-introduction.
`tests/test_mcp_headers.py` pins the config that keeps the variable gone.

Read `docs/agents/secrets.md` before adding a rule here. It states what this layer cannot
do: prefix matching cannot cover every spelling of a shell expansion, so these rules stop
an accident and not an intent. Removing the value from the environment is the only
complete fix, and that is what the credential store does.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROJECT = Path(__file__).resolve().parents[1]
SETTINGS = PROJECT / ".claude" / "settings.json"
HOOK_PATH = PROJECT / ".claude" / "hooks" / "protect_paths.py"

# `.env` variants that hold real values. Enumerated rather than globbed as `.env.*`:
# a glob would also deny `.env.example`, which is committed, holds no values, and is the
# file an agent reads to learn which keys exist. A rule with false positives gets deleted,
# and a deleted rule protects nothing.
SECRET_READ_RULES = (
    "Read(./.env)",
    "Read(./.env.local)",
    "Read(./.env.*.local)",
    "Read(./.env.development)",
    "Read(./.env.production)",
    "Read(./.env.staging)",
    "Read(./.env.test)",
)

# Bash reaches the same bytes without the Read tool. Prefix matching makes this a speed
# bump rather than a wall — `sed -n p .env` still gets through — so it is defence in
# depth behind `.gitignore` and the gitleaks pre-commit hook, not the primary control.
BASH_READER_RULES = (
    "Bash(cat .env:*)",
    "Bash(cat ./.env:*)",
    "Bash(type .env:*)",
    "Bash(more .env:*)",
    "Bash(less .env:*)",
    "Bash(head .env:*)",
    "Bash(tail .env:*)",
    "Bash(nl .env:*)",
    "Bash(strings .env:*)",
    "Bash(Get-Content .env:*)",
    "Bash(gc .env:*)",
    # A whole-environment dump exposes every key the session inherited, including the
    # OS user variables that CLAUDE.md tells the user to store secrets in.
    "Bash(env)",
    "Bash(printenv:*)",
)

# `.env` is not the only store. `GH_TOKEN` lives in an OS user variable, so the session
# inherits it and every Bash subprocess inherits it in turn. `env` and `printenv` were the
# only dumps blocked. These are the rest of the whole-environment dumps, across both
# shells the harness uses: POSIX sh through the Bash tool, and PowerShell.
ENV_DUMP_RULES = (
    "Bash(set)",
    "Bash(export)",
    "Bash(export -p:*)",
    "Bash(declare -x:*)",
    "Bash(typeset -x:*)",
    "Bash(compgen -e:*)",
    "Bash(Get-ChildItem Env:*)",
    "Bash(gci Env:*)",
    "Bash(ls Env:*)",
    "Bash(dir Env:*)",
    "Bash(Get-Variable:*)",
)

# Reading one variable needs no dump at all. Prefix matching cannot cover every spelling
# of an expansion, so these cover the careless ones rather than the determined ones. The
# quoted and braced forms are listed because they are what a shell writes by habit.
# The `LINEAR_API_KEY` entries guard a variable that should no longer exist; keep them so
# a change that reintroduces the `${VAR}` header does not also reopen the read path.
SINGLE_VAR_RULES = (
    "Bash(echo $LINEAR_API_KEY:*)",
    'Bash(echo "$LINEAR_API_KEY":*)',
    "Bash(echo ${LINEAR_API_KEY}:*)",
    "Bash(echo $env:LINEAR_API_KEY:*)",
    "Bash(echo $GH_TOKEN:*)",
    'Bash(echo "$GH_TOKEN":*)',
    "Bash(echo ${GH_TOKEN}:*)",
    "Bash(echo $env:GH_TOKEN:*)",
)

# An inline interpreter reaches the same environment and defeats every rule above, because
# the variable name need not appear in the command at all. This repo runs scripts through
# `uv run python <file>`, so denying the `-c` and `-e` forms costs nothing it uses.
INLINE_INTERPRETER_RULES = (
    "Bash(python -c:*)",
    "Bash(python3 -c:*)",
    "Bash(uv run python -c:*)",
    "Bash(node -e:*)",
    "Bash(node -p:*)",
)


def deny_rules() -> list[str]:
    """Every rule configured under `permissions.deny`."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    rules: list[str] = settings["permissions"]["deny"]
    return rules


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    """Load the hook by path — `.claude/hooks` is not an importable package."""
    spec = importlib.util.spec_from_file_location("_protect_paths_under_test", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def block_write(hook: ModuleType, monkeypatch: pytest.MonkeyPatch, path: str) -> int:
    """Run the hook against one write payload and return its exit code."""
    payload = json.dumps({"tool_input": {"file_path": path}, "cwd": str(PROJECT)})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    code: int = hook.main()
    return code


@pytest.mark.parametrize("rule", SECRET_READ_RULES)
def test_reading_a_secret_file_is_denied(rule: str) -> None:
    """A missing rule here is a key in the transcript, which rotation is the only fix for."""
    assert rule in deny_rules(), (
        f"{rule} is not in permissions.deny — that file can be read into context."
    )


@pytest.mark.parametrize("rule", BASH_READER_RULES)
def test_reading_a_secret_file_through_bash_is_denied(rule: str) -> None:
    """Denying the Read tool alone leaves `cat .env` wide open."""
    assert rule in deny_rules(), f"{rule} is not in permissions.deny."


@pytest.mark.parametrize("rule", ENV_DUMP_RULES)
def test_dumping_the_environment_is_denied(rule: str) -> None:
    """`.env` rules protect a file. An OS user variable is in no file at all."""
    assert rule in deny_rules(), (
        f"{rule} is not in permissions.deny — that dump exposes every inherited key."
    )


@pytest.mark.parametrize("rule", SINGLE_VAR_RULES)
def test_reading_one_secret_variable_is_denied(rule: str) -> None:
    """Blocking the dumps alone leaves `echo $LINEAR_API_KEY` wide open."""
    assert rule in deny_rules(), f"{rule} is not in permissions.deny."


@pytest.mark.parametrize("rule", INLINE_INTERPRETER_RULES)
def test_inline_interpreters_are_denied(rule: str) -> None:
    """An inline interpreter reads the environment without naming the variable."""
    assert rule in deny_rules(), f"{rule} is not in permissions.deny."


def test_the_example_file_stays_readable() -> None:
    """`.env.example` is committed and holds no values. Denying it would be a false
    positive, and the enumeration above exists precisely to avoid one."""
    assert not any(".env.example" in rule for rule in deny_rules())


@pytest.mark.parametrize("path", [".env", ".env.local", str(PROJECT / ".env")])
def test_writing_a_secret_file_is_refused(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """Exit 2 is the only code that blocks a tool call; exit 1 lets the write through."""
    assert block_write(hook, monkeypatch, path) == 2


def test_writing_the_example_file_is_allowed(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert block_write(hook, monkeypatch, ".env.example") == 0
