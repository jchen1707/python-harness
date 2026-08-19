"""Guardrail tests for the `v2` → `main` generator (`.agents/transform/`).

`main` is a build artifact. That only holds while the build actually runs, and the failure
mode of a generator nobody tests is the one it was built to end: `main` silently stops
matching `v2` and the two diverge again, this time without anyone editing `main` to notice.

These tests run the real generator over the real working tree. They assert the properties
`main` must have — no canonical directory, no second-harness adapter, no dangling reference
to either — rather than a fixed file list, which would need editing every time the harness
gains a file.

The gates of the generated tree are checked in CI rather than here: running `ruff`, `mypy`
and `pytest` inside a generated copy from within `pytest` is a recursion nobody needs.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = REPO_ROOT / ".agents" / "transform"


@pytest.fixture(scope="module")
def generator() -> ModuleType:
    """Load the generator by path — `.agents/transform` is not an importable package."""
    spec = importlib.util.spec_from_file_location(
        "_generate_main_under_test", TRANSFORM / "generate_main.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(generator: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The `main` tree, built from this working tree by the real generator."""
    destination = tmp_path_factory.mktemp("generated") / "main"
    manifest = json.loads((TRANSFORM / "transform.json").read_text(encoding="utf-8"))
    generator.generate(REPO_ROOT, destination, manifest)
    return destination


def test_the_canonical_directory_is_gone(generated: Path) -> None:
    """`main` is the Claude-specific branch. `.agents/` is the neutral one's whole point."""
    assert not (generated / ".agents").exists()
    assert not (generated / ".codex").exists()


def test_the_adapter_symlinks_became_real_files(generated: Path) -> None:
    """A symlink into `.agents/` is a dangling link once `.agents/` is dropped.

    `.claude/workflows` is no longer in the list: `full-review.js` is layer A now, and on
    this branch the plugin supplies it. Nothing is left under `.agents/workflows/` to link.
    """
    for relative in (".claude/hooks", ".claude/agents"):
        path = generated / relative
        assert path.is_dir(), f"{relative} is missing"
        assert not path.is_symlink(), f"{relative} is still a symlink"
    assert (generated / ".claude/hooks/verify.py").is_file()
    assert not (generated / ".claude/workflows").exists()


def test_layer_a_arrives_once_on_main(generated: Path) -> None:
    """The plugin and the stubs must not both supply a skill.

    On `v2` a thin stub under `.agents/skills/<name>/` is how a harness that discovers
    skills by directory finds the shared one in the vendored tree. On `main` the plugin
    supplies the real thing, so every stub has to be dropped — two skills of one name is
    worse than none, because which one answers is not something anybody can see.
    """
    survivors = [
        path.parent.name
        for path in (generated / ".claude/skills").glob("*/SKILL.md")
        if ".agents/vendor/harness" in path.read_text(encoding="utf-8")
    ]
    assert not survivors, (
        f"layer A stubs reached main: {sorted(survivors)}. Add each to `drop` in "
        f"transform.json — the plugin already supplies them."
    )


def test_nothing_points_at_a_directory_that_no_longer_exists(generated: Path) -> None:
    """The rewrite is only as good as its coverage.

    A path written as `Path(...) / ".agents" / "hooks"` carries no slash, so a substitution
    on `.agents/` misses it — and the miss is invisible until the hook fails to load at
    runtime. This walks the whole tree instead of trusting the rules.
    """
    offenders: list[str] = []
    for path in sorted(generated.rglob("*")):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.suffix not in {".py", ".md", ".json", ".toml", ".js", ".sh", ".yml"}
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(generated).as_posix()
        for needle in (".agents/", '".agents"', "'.agents'", ".codex/", '".codex"'):
            # Prose recording why a rule exists may name the directory it removed.
            if needle in text and not relative.startswith("tests/test_hook_matchers"):
                offenders.append(f"{relative}: {needle}")
    assert not offenders, "generated main references removed paths:\n  " + "\n  ".join(offenders)


def test_every_instruction_file_is_a_claude_file(generated: Path) -> None:
    """`AGENTS.md` becomes `CLAUDE.md`, and the pointer stub it replaces is gone."""
    assert not list(generated.rglob("AGENTS.md"))
    root = (generated / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@AGENTS.md" not in root, "the root file is still the pointer stub"
    assert len(root.splitlines()) > 4, "the root file is still the pointer stub"


def test_no_region_marker_survives_the_build(generated: Path) -> None:
    """A marker left in the output means a region was never resolved."""
    offenders = [
        path.relative_to(generated).as_posix()
        for path in sorted(generated.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and path.suffix in {".py", ".md", ".json", ".toml", ".js", ".sh", ".yml"}
        and "harness:" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not offenders, f"unresolved harness regions in: {offenders}"


def test_a_stale_manifest_stops_the_build(generator: ModuleType, tmp_path: Path) -> None:
    """The safety argument for generating a branch.

    A generator that skips what it cannot find is worse than the hand-maintenance it
    replaced, because nobody reads a tree that builds.
    """
    manifest = json.loads((TRANSFORM / "transform.json").read_text(encoding="utf-8"))
    manifest["drop"].append("does/not/exist")
    with pytest.raises(generator.TransformError):
        generator.generate(REPO_ROOT, tmp_path / "main", manifest)


def test_a_submodule_is_not_copied_as_a_file(generator: ModuleType, tmp_path: Path) -> None:
    """`harness` mounts both stacks as submodules, and `ls-files` lists them like files.

    A gitlink entry names a commit in another repository, so there is nothing to copy —
    and the directory it stands for is a directory, which is what the old code handed to
    `shutil.copy2`. The build died on a `git submodule add` in the parent repo. This is
    the fixture that keeps it dead.
    """

    def git(*args: str, cwd: Path) -> None:
        # Every argument is a literal or a tmp_path this test just made, and
        # `protocol.file.allow` is needed because git refuses a local-path submodule
        # by default.
        subprocess.run(  # noqa: S603
            ["git", "-c", "protocol.file.allow=always", *args],  # noqa: S607
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    child = tmp_path / "child"
    child.mkdir()
    git("init", "-q", "-b", "main", cwd=child)
    (child / "README.md").write_text("child\n", encoding="utf-8")
    git("add", "-A", cwd=child)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init", cwd=child)

    parent = tmp_path / "parent"
    parent.mkdir()
    git("init", "-q", "-b", "v2", cwd=parent)
    (parent / "AGENTS.md").write_text("# parent\n", encoding="utf-8")
    git("submodule", "add", "-q", str(child), "child", cwd=parent)
    git("add", "-A", cwd=parent)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init", cwd=parent)

    destination = tmp_path / "main"
    generator.generate(parent, destination, {"drop": [], "substitutions": []})

    assert (destination / "CLAUDE.md").exists()
    assert (destination / ".gitmodules").exists(), "the parent's own file must survive"
    assert not (destination / "child").exists(), "a gitlink is a commit, not content"
