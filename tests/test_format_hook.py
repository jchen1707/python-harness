"""Guardrail test for the PostToolUse formatter (`.claude/hooks/format_edited.py`).

The hook fires after every single edit. In a batch of edits it runs between the
edit that adds an import and the edit that adds the import's first use. At that
moment the import is unused, so an F401 autofix removes it and the next edit
references an undefined name. `--unfixable F401` is what prevents that, and
dropping it re-opens the trap silently — the hook still runs, every test still
passes, and the failure only shows up as a broken file mid-batch. So the flag is
pinned here, the same way `tests/test_verify_hook.py` pins `GATED_PATHS`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HOOK_PATH = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "format_edited.py"


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    """Load the hook by path — `.claude/hooks` is not an importable package."""
    spec = importlib.util.spec_from_file_location("_format_hook_under_test", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fix_never_removes_an_unused_import(hook: ModuleType) -> None:
    """`--unfixable F401` must ride along with `--fix`, as one flag-value pair."""
    args = tuple(hook.FIX_ARGS)
    assert "--fix" in args, "the hook no longer autofixes at all — that is a different design"
    index = args.index("--unfixable")
    assert args[index + 1] == "F401", f"--unfixable does not cover F401: {args}"


def test_fix_still_runs_ruff_check(hook: ModuleType) -> None:
    """The args must still invoke `ruff check`; pinning a flag on a dead command is no pin."""
    assert next(iter(hook.FIX_ARGS)) == "check"
