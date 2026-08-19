"""Guardrail tests for this repository's half of the shared enforcement layer.

The hooks are layer A now — one Node implementation in `harness`, vendored under
`.agents/vendor/harness/hooks/`. Their behaviour is tested there, by a suite this file
runs rather than duplicates. What is left here is the half that is irreducibly ours, and
it fails silently in exactly the way it always did:

- **The config.** The hooks read every path they act on from `harness.config.json`. A
  dropped entry does not error; the gate simply stops watching that directory, and every
  other test still passes. This is what `tests/test_verify_hook.py` used to pin against
  literals, for the same reason and in the same way.
- **The wiring.** A hook matcher is a case-sensitive regex over the tool name. Narrowing
  one disables its guard with no signal at all. `tests/test_hook_matchers.py` pinned this;
  the assertions move, the property does not.
- **The deny list.** `permissions.deny` is evaluated by the harness at no cost and covers
  the shell readers a hook is not asked about. It is layer B and stays here, exactly as
  `tests/test_secret_paths.py` had it.

`.agents/hooks/` is gone with those files. The one thing that must not go with it is the
habit of asserting against literals rather than against the constant under test: reading
the same list the hook reads would make a dropped entry pass vacuously.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

PROJECT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((PROJECT / "harness.config.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((PROJECT / ".claude" / "settings.json").read_text(encoding="utf-8"))
CODEX = json.loads((PROJECT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
HOOKS_DIR = PROJECT / ".agents" / "vendor" / "harness" / "hooks"

HOOK_CONFIG: dict[str, Any] = CONFIG["hooks"]


# --------------------------------------------------------------------------------------
# Layer A's own suite, run from here
# --------------------------------------------------------------------------------------


def test_the_shared_hook_suite_passes_against_this_checkout() -> None:
    """Run layer A's suite as part of this repo's Definition of Done.

    The meta-repo's cross-stack job asks whether a *new* layer A breaks this stack. This
    asks the other half: whether the layer A this stack has pinned still works here, on
    this platform. CI runs the gates on Windows as well as Linux, and the hooks are full
    of platform-specific decisions — shell quoting, path separators, text decoding — that
    only a Windows run can actually check.
    """
    suite = HOOKS_DIR / "hooks.test.mjs"
    assert suite.exists(), "the vendored layer A ships no hook suite — run `vendor_sync.py sync`"
    node = shutil.which("node")
    assert node is not None, (
        "node is not on PATH. This repo declares Node in .nvmrc: the hooks that enforce "
        "its gates are JavaScript, and have been since the shared harness took them over."
    )

    result = subprocess.run(  # noqa: S603
        [node, "--test", str(suite)],
        cwd=HOOKS_DIR,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        "the shared hook suite fails against this checkout:\n"
        + "\n".join((result.stdout + result.stderr).strip().splitlines()[-30:])
    )


def test_node_is_declared_rather_than_assumed() -> None:
    """This repo ran `full-review.js` for months with no `.nvmrc` and no `package.json`.

    An undeclared dependency is one nobody installs on purpose and nobody knows to keep.
    The hooks made it load-bearing, so it is declared.
    """
    assert (PROJECT / ".nvmrc").read_text(encoding="utf-8").strip() == "22"


# --------------------------------------------------------------------------------------
# The Stop gate's pathspec
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        # The application and its tests.
        "src",
        "tests",
        # The vendored hooks themselves. They are what enforces the gates, and an edit to
        # them — a sync, most often — has to run the suite that proves they still work.
        ".agents/vendor/harness/hooks",
    ],
)
def test_the_gate_watches_every_directory_it_must(path: str) -> None:
    assert path in HOOK_CONFIG["gatedPaths"], (
        f"{path} is not in hooks.gatedPaths — a change there ends the turn ungated"
    )


@pytest.mark.parametrize(
    "path",
    [
        # Configures ruff, mypy and pytest. A change here breaks every gate at once while
        # touching no Python.
        "pyproject.toml",
        # Declares the gates, the gated paths and the protected files. Since phase 5 it can
        # break the entire enforcement layer without touching a line of code.
        "harness.config.json",
        # Wires the hooks. A broken matcher disables a guard while everything still passes.
        ".claude/settings.json",
        # Resolves the Linear credential at connection time. Python that ruff and mypy
        # check, named as a file because it is not under a gated directory.
        ".agents/mcp_headers.py",
        # harness:agnostic
        ".codex/config.toml",
        ".codex/hooks.json",
        # /harness:agnostic
    ],
)
def test_the_gate_watches_every_file_that_defines_it(path: str) -> None:
    assert path in HOOK_CONFIG["gatedFiles"], (
        f"{path} is not in hooks.gatedFiles — it can break the gates while they stay green"
    )


def test_the_gate_reads_both_languages_this_repo_now_enforces_in() -> None:
    """Python is the application; the hooks are `.mjs`. Dropping either half goes quiet."""
    assert ".py" in HOOK_CONFIG["gatedExtensions"]
    assert ".mjs" in HOOK_CONFIG["gatedExtensions"], (
        "the vendored hooks are .mjs — without this, editing one ends the turn ungated"
    )


def test_prose_stays_out_of_the_gate() -> None:
    """Markdown is what sessions churn on; gating it burns the 8-block override budget."""
    assert ".md" not in HOOK_CONFIG["gatedExtensions"]
    assert not any(f.endswith(".md") for f in HOOK_CONFIG["gatedFiles"])


# --------------------------------------------------------------------------------------
# Protected paths and the formatter
# --------------------------------------------------------------------------------------


def protected_globs() -> set[str]:
    return {entry["glob"] for entry in HOOK_CONFIG["protected"]}


@pytest.mark.parametrize(
    "glob",
    [
        "**/migrations/**",
        "**/generated/**",
        "uv.lock",
        # Editing a vendored file is the drift the freshness check exists to catch. Better
        # to refuse the write than to report it a commit later.
        ".agents/vendor/**",
    ],
)
def test_this_repo_declares_its_protected_paths(glob: str) -> None:
    assert glob in protected_globs()


def test_env_is_not_declared_here_because_it_cannot_be_removed() -> None:
    """`.env` is a built-in floor in `protect_paths.mjs`, not a config entry.

    A guard whose config goes missing and quietly protects nothing is worse than no guard.
    Declaring it here as well would suggest it could be un-declared.
    """
    assert not any(glob.startswith(".env") for glob in protected_globs())


def test_every_protected_entry_says_what_to_do_instead() -> None:
    """The `why` is the whole message the agent receives; "protected" invites a retry."""
    for entry in HOOK_CONFIG["protected"]:
        assert entry.get("why"), f"{entry['glob']} gives no reason"
        assert len(entry["why"]) > 20, f"{entry['glob']}: {entry['why']!r} is not a reason"


def test_the_formatter_never_removes_an_unused_import() -> None:
    """`--unfixable F401` must ride along with `--fix`, as one flag-value pair.

    The hook fires after every single edit. In a batch it runs between the edit that adds
    an import and the edit that adds the import's first use; an F401 autofix at that moment
    deletes the import and the next edit references an undefined name. The Stop gate still
    runs plain `ruff check .`, so a genuinely unused import fails the turn and gets removed
    deliberately. This was `tests/test_format_hook.py`; the flag moved into config and the
    trap did not.
    """
    python = next(e for e in HOOK_CONFIG["formatters"] if ".py" in e["match"])
    fix = next(argv for argv in python["run"] if "--fix" in argv)
    assert fix[fix.index("--unfixable") + 1] == "F401", f"--unfixable does not cover F401: {fix}"
    assert "check" in fix, "the flag is pinned on a command that no longer runs ruff check"


def test_the_formatter_still_formats() -> None:
    python = next(e for e in HOOK_CONFIG["formatters"] if ".py" in e["match"])
    assert any("format" in argv for argv in python["run"])


# --------------------------------------------------------------------------------------
# The wiring: which tool calls each guard actually sees
# --------------------------------------------------------------------------------------

# Tools that can put bytes on disk. `NotebookEdit` writes `.ipynb`; an MCP server can
# expose a write under any name, so the matcher covers the verbs rather than a fixed list.
MUST_MATCH = (
    "Edit",
    "Write",
    "NotebookEdit",
    "mcp__filesystem__write_file",
    "mcp__filesystem__edit_file",
    "mcp__memory__create_entities",
    "mcp__patch__apply_patch",
)

# Tools that can copy a secret into the transcript without writing a byte. Defect 1 was
# that the guard covering these was wired into the Codex adapter and nowhere else.
SECRET_SURFACE = ("Read", "Bash")


def matchers(config: dict[str, Any], event: str, script: str) -> list[str]:
    """Every matcher configured for `event` whose hooks run `script`."""
    return [
        group["matcher"]
        for group in config["hooks"][event]
        if "matcher" in group and script in json.dumps(group["hooks"])
    ]


@pytest.mark.parametrize("config", [SETTINGS, CODEX], ids=["claude", "codex"])
@pytest.mark.parametrize("tool", MUST_MATCH)
def test_the_write_guards_cover_every_tool_that_can_write(
    config: dict[str, Any], tool: str
) -> None:
    """A write tool outside the matcher is a write the guard never sees.

    Asserted per harness, because the two configs are edited separately and only one of
    them is the one you are looking at when you narrow a matcher.
    """
    for script in ("protect_paths.mjs", "format_edited.mjs"):
        found = matchers(config, "PreToolUse" if "protect" in script else "PostToolUse", script)
        assert any(re.search(pattern, tool) for pattern in found), (
            f"the {script} matcher does not cover {tool}. Matchers: {found}"
        )


@pytest.mark.parametrize("config", [SETTINGS, CODEX], ids=["claude", "codex"])
@pytest.mark.parametrize("tool", SECRET_SURFACE)
def test_the_secret_guard_covers_the_read_surface(config: dict[str, Any], tool: str) -> None:
    """The deny list stops the shell readers it can name. The hook reads the command.

    Wiring it for one harness and not the other is exactly what defect 1 was: Codex refused
    these calls and Claude Code did not, and no test could tell, because "PreToolUse ignores
    reads" was the property being asserted.
    """
    found = matchers(config, "PreToolUse", "protect_paths.mjs")
    assert any(re.search(pattern, tool) for pattern in found), (
        f"a secret can be read through {tool} without the guard seeing the call. Matchers: {found}"
    )


@pytest.mark.parametrize("config", [SETTINGS, CODEX], ids=["claude", "codex"])
@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Bash"])
def test_the_formatter_is_not_run_on_a_read(config: dict[str, Any], tool: str) -> None:
    found = matchers(config, "PostToolUse", "format_edited.mjs")
    assert not any(re.search(pattern, tool) for pattern in found), (
        f"the formatter fires on the read-only tool {tool}"
    )


@pytest.mark.parametrize("config", [SETTINGS, CODEX], ids=["claude", "codex"])
@pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop", "SessionEnd"])
def test_every_lifecycle_event_is_still_wired(config: dict[str, Any], event: str) -> None:
    """The tests above pass vacuously if a guard is deleted: `any([])` is False, so the
    read-only assertion holds and the coverage assertion is the only thing left to fail.
    Pin each event separately so removing one reports as removal."""
    assert config["hooks"].get(event), f"no {event} hook is configured at all"


@pytest.mark.parametrize("config", [SETTINGS, CODEX], ids=["claude", "codex"])
def test_every_hook_points_into_the_vendored_layer_a(config: dict[str, Any]) -> None:
    """A hook that still points at `.agents/hooks/` points at a directory that is gone."""
    wiring = json.dumps(config["hooks"])
    assert ".agents/hooks/" not in wiring, "a hook still points at the deleted Python scripts"
    for script in ("protect_paths.mjs", "format_edited.mjs", "verify.mjs"):
        assert f"vendor/harness/hooks/{script}" in wiring, f"{script} is not wired"


def test_codex_distils_outside_its_three_second_budget() -> None:
    """`claude -p` takes minutes; Codex gives SessionEnd three seconds.

    Running the distiller inline there means it is killed every time, and a killed
    distiller looks exactly like a session that taught nothing. The adapter forwards to a
    detached child instead.
    """
    stanza = json.dumps(CODEX["hooks"]["SessionEnd"])
    assert "codex_session_learnings.mjs" in stanza
    assert 'session_learnings.mjs"' not in stanza.replace("codex_session_learnings.mjs", "")


def test_codex_carries_a_windows_variant_for_every_hook() -> None:
    """`$(...)` is not command substitution in `cmd.exe`; without the variant the hook
    never starts, and a hook that cannot start is a hook that silently stops enforcing."""
    for event, groups in CODEX["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                assert hook.get("commandWindows"), f"{event} has no Windows command"


# --------------------------------------------------------------------------------------
# The deny list — layer B, and it stays here
# --------------------------------------------------------------------------------------

# `.env` variants that hold real values. Enumerated rather than globbed as `.env.*`: a glob
# would also deny `.env.example`, which is committed, holds no values, and is the file an
# agent reads to learn which keys exist. A rule with false positives gets deleted, and a
# deleted rule protects nothing.
SECRET_READ_RULES = (
    "Read(./.env)",
    "Read(./.env.local)",
    "Read(./.env.*.local)",
    "Read(./.env.development)",
    "Read(./.env.production)",
    "Read(./.env.staging)",
    "Read(./.env.test)",
)

# Bash reaches the same bytes without the Read tool. Prefix matching makes this a speed bump
# rather than a wall — `sed -n p .env` still gets through — so it is defence in depth behind
# `.gitignore`, the gitleaks pre-commit hook and the shared command guard, not the primary
# control. Read `docs/agents/secrets.md` before adding a rule here.
BASH_RULES = (
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
    "Bash(env)",
    "Bash(printenv:*)",
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
    "Bash(echo $LINEAR_API_KEY:*)",
    'Bash(echo "$LINEAR_API_KEY":*)',
    "Bash(echo ${LINEAR_API_KEY}:*)",
    "Bash(echo $env:LINEAR_API_KEY:*)",
    "Bash(echo $GH_TOKEN:*)",
    'Bash(echo "$GH_TOKEN":*)',
    "Bash(echo ${GH_TOKEN}:*)",
    "Bash(echo $env:GH_TOKEN:*)",
    "Bash(python -c:*)",
    "Bash(python3 -c:*)",
    "Bash(uv run python -c:*)",
    "Bash(node -e:*)",
    "Bash(node -p:*)",
)


@pytest.mark.parametrize("rule", [*SECRET_READ_RULES, *BASH_RULES])
def test_the_deny_list_still_carries_every_rule(rule: str) -> None:
    """A missing rule here is a key in the transcript, which rotation is the only fix for."""
    assert rule in SETTINGS["permissions"]["deny"], f"{rule} is not in permissions.deny"


def test_the_example_file_stays_readable() -> None:
    """`.env.example` is committed and holds no values. Denying it would be a false
    positive, and the enumeration above exists precisely to avoid one."""
    assert not any(".env.example" in rule for rule in SETTINGS["permissions"]["deny"])


def test_the_secret_variables_the_hook_watches_match_the_ones_denied() -> None:
    """The deny list names the careless spellings; the hook catches the rest. Both need the
    same variable names, and only one of them is obvious when a new secret is introduced."""
    denied = json.dumps(SETTINGS["permissions"]["deny"])
    for name in HOOK_CONFIG["secretVars"]:
        assert name in denied, f"{name} is watched by the hook but absent from permissions.deny"
