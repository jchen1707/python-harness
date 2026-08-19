"""Mechanical checks that the rule files agree with each other and with the tree.

Rules are stated in more than one file on purpose. A reviewer subagent runs in a fresh
context and path-scoped `AGENTS.md` files do not load unless it reads them, so each
reviewer carries the rules it checks. That redundancy is load-bearing.

The cost is drift: two copies stay plausible while disagreeing, and nothing notices. It
has already happened — `standards-reviewer` kept the pre-`ai/` layering rule and would
have missed the exact violation it exists to catch.

These tests make that drift loud. They are the same shape as the pathspec assertion in
`test_verify_hook.py`: check against a literal, so a silent divergence fails the suite
instead of going quiet.

Offline by construction — file reads only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# The single source of truth for the layer order. Changing the architecture means
# changing this line and every file the test then reports.
CANONICAL_LAYERS = ("api", "services", "ai", "repositories", "config")

LAYER_WORDS = frozenset(CANONICAL_LAYERS) | {"core"}

# Rule files carry the chain in prose (`api` → `services`) and in fenced diagrams
# (api ──▶ services), so both arrow forms count.
ARROW = re.compile(r"──▶|->|→")

# Directories that are not ours to police.
EXCLUDED = (
    "/.venv/",
    "/node_modules/",
    "/.claude/plugins/",
    "/.agents/plans/",
    "/.git/",
    # Layer A. Generated, pinned by sha, and owned in `harness` — see the docstring
    # on `rule_files`.
    "/.agents/vendor/",
)


def rule_files() -> list[Path]:
    """Every file in **this repo** that states or restates a rule.

    `.agents/workflows/*.js` used to be in this list because the workflow embedded
    fallback reviewer prompts that restated the layering rule — and that fallback is how
    the pre-`ai/` chain survived after every Markdown copy was fixed, in the one copy that
    fires precisely when the good copy is missing. Layer A removed the fallbacks entirely
    rather than keeping them correct, so the file is gone and so is the pattern.

    The vendored tree is deliberately absent. It is generated, pinned by sha and policed
    upstream; a finding against it is not actionable here, and editing it to satisfy this
    test would break the freshness check on the next sync. `docs/agents/subagents/*.md` is
    present instead — that is where this repo now states the rules a reviewer checks.
    """
    patterns = (
        "AGENTS.md",
        "README.md",
        "docs/**/*.md",
        "src/**/AGENTS.md",
        "tests/AGENTS.md",
        ".agents/agents/*.md",
        ".agents/skills/*/SKILL.md",
        ".out-of-scope/*.md",
    )
    found: set[Path] = set()
    for pattern in patterns:
        for path in REPO_ROOT.glob(pattern):
            posix = "/" + path.as_posix().replace(REPO_ROOT.as_posix() + "/", "")
            if not any(skip in posix for skip in EXCLUDED) and path.is_file():
                found.add(path)
    return sorted(found)


def layer_chain(line: str) -> tuple[str, ...] | None:
    """Extract the layer sequence from one line, or None if it states no chain.

    Takes the *first* layer word in each arrow-separated segment. A trailing clause
    ("`config`, no reverse deps; ... a protocol in `repositories/`") would otherwise
    contribute its last word and corrupt the chain.
    """
    if len(ARROW.findall(line)) < 3:
        return None
    chain: list[str] = []
    for segment in ARROW.split(line):
        words = re.findall(r"[a-z_]+", segment.lower())
        hit = next((w for w in words if w in LAYER_WORDS), None)
        if hit is not None:
            chain.append(hit)
    return tuple(chain) if len(chain) >= 3 else None


def test_layering_rule_is_stated_identically_everywhere() -> None:
    """Every copy of the layering chain must match the canonical order.

    This is the regression that motivated the file: three files kept
    `api -> services -> repositories -> config` after `ai/` became a layer.
    """
    disagreements: list[str] = []
    copies = 0
    for path in rule_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            chain = layer_chain(line)
            if chain is None:
                continue
            copies += 1
            if chain != CANONICAL_LAYERS:
                rel = path.relative_to(REPO_ROOT).as_posix()
                disagreements.append(f"{rel}:{number} states {' -> '.join(chain)}")

    assert copies > 0, "found no statement of the layering rule at all — did the glob break?"
    assert not disagreements, (
        f"layering rule disagrees with {' -> '.join(CANONICAL_LAYERS)} in "
        f"{len(disagreements)} place(s):\n  " + "\n  ".join(disagreements)
    )


def test_every_convention_file_is_indexed() -> None:
    """A leaf `AGENTS.md` nobody points at is a rule nobody reads.

    Scope, stated precisely: this asserts each file is referenced *somewhere* in root
    `AGENTS.md` and *somewhere* in `docs/architecture.md`. It does not pin which table.
    Root mentions most paths twice — once in the directory index, once in the reference
    table — so deleting one row leaves the other and the check still passes.

    That is the guarantee worth having here. Catching a file that fell out of every
    index is the failure that silently orphans a rule; policing which of two tables
    holds it would couple the test to formatting that is allowed to change.
    """
    root = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    arch = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    orphans: list[str] = []
    convention_files = [*sorted(REPO_ROOT.glob("src/**/AGENTS.md")), REPO_ROOT / "tests/AGENTS.md"]
    for path in convention_files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        directory = rel.rsplit("/AGENTS.md", 1)[0]
        if directory not in root and rel not in root:
            orphans.append(f"{rel} missing from AGENTS.md")
        if rel not in arch:
            orphans.append(f"{rel} missing from docs/architecture.md")

    assert not orphans, "convention files not indexed:\n  " + "\n  ".join(orphans)


# harness:agnostic
def test_claude_files_import_agents_rules() -> None:
    """Claude compatibility files must import the canonical rules explicitly."""
    agents_files = [REPO_ROOT / "AGENTS.md", *sorted(REPO_ROOT.glob("src/**/AGENTS.md"))]
    agents_files.append(REPO_ROOT / "tests/AGENTS.md")

    failures: list[str] = []
    for agents_file in agents_files:
        claude_file = agents_file.with_name("CLAUDE.md")
        if not claude_file.exists():
            failures.append(f"{claude_file.relative_to(REPO_ROOT)} is missing")
            continue
        lines = claude_file.read_text(encoding="utf-8").splitlines()
        if "@AGENTS.md" not in lines or len(lines) > 4:
            failures.append(f"{claude_file.relative_to(REPO_ROOT)} does not import AGENTS.md")

    assert not failures, "invalid Claude compatibility files:\n  " + "\n  ".join(failures)


def test_every_review_axis_resolves_to_a_definition() -> None:
    """Every axis `full-review` runs must have something to run.

    The axes come from two places now. Eight shared frames live in the vendored layer A
    and the workflow names them; the ninth is this repo's own, named in
    `harness.config.json` and defined under `.agents/agents/`. An axis that resolves to
    neither is the failure the whole split has to be checked against — the review still
    runs, on nothing, and reports a confident clean.
    """
    config = json.loads((REPO_ROOT / "harness.config.json").read_text(encoding="utf-8"))
    review = config["review"]
    vendor = REPO_ROOT / ".agents/vendor/harness"
    workflow = (vendor / "workflows/full-review.js").read_text(encoding="utf-8")

    shared = set(re.findall(r"agent: '([a-z-]+)'", workflow))
    ninth = review["ninthAxis"]["agent"]
    axes = shared | {ninth}

    missing = [a for a in sorted(shared) if not (vendor / "agents" / f"{a}.md").is_file()]
    assert not missing, f"shared axes with no frame in the vendored tree: {missing}"

    own = REPO_ROOT / review["agentDir"] / f"{ninth}.md"
    assert own.is_file(), f"the ninth axis {ninth!r} has no definition at {own}"

    codex = {path.stem for path in (REPO_ROOT / ".codex/agents").glob("*.toml")}
    assert axes <= codex, f"axes with no Codex adapter: {sorted(axes - codex)}"

    skill = (vendor / "skills/full-review/SKILL.md").read_text(encoding="utf-8")
    assert "ninthAxis" in skill, "the portable skill no longer explains where the ninth comes from"


def test_every_shared_frame_has_this_repos_half() -> None:
    """A frame that defers its checklist here cannot review without it."""
    config = json.loads((REPO_ROOT / "harness.config.json").read_text(encoding="utf-8"))
    checklists = REPO_ROOT / config["review"]["checklistDir"]
    frames = sorted((REPO_ROOT / ".agents/vendor/harness/agents").glob("*.md"))

    missing = [
        frame.stem
        for frame in frames
        if "docs/agents/subagents/" in frame.read_text(encoding="utf-8")
        and not (checklists / frame.name).is_file()
    ]
    assert not missing, (
        f"frames with no checklist in {config['review']['checklistDir']}: {missing}. "
        f"Each would review on general advice and report a confident clean."
    )


def test_layer_a_stubs_are_dropped_from_main() -> None:
    """A stub that survives the transform collides with the plugin's real skill.

    On `v2` the stub is how a harness that discovers skills by directory reaches the
    vendored one. On `main` the plugin supplies it, so every stub has to be in
    `transform.json`'s drop list — and forgetting one is silent: two skills of the same
    name, with nothing saying which answers.
    """
    manifest = json.loads(
        (REPO_ROOT / ".agents/transform/transform.json").read_text(encoding="utf-8")
    )
    dropped = set(manifest["drop"])
    stubs = [
        path.parent.name
        for path in (REPO_ROOT / ".agents/skills").glob("*/SKILL.md")
        if ".agents/vendor/harness" in path.read_text(encoding="utf-8")
    ]
    missing = [name for name in stubs if f".claude/skills/{name}" not in dropped]
    assert not missing, f"layer A stubs missing from transform.json's drop list: {sorted(missing)}"


# Generated at runtime and gitignored, so absent on a clean checkout. A doc naming one
# is correct; the file simply is not committed. Checking these makes the test pass or
# fail on local leftovers rather than on the repo — which is what happened: it was green
# locally off a stale `/plan` artifact and red on CI.
# /harness:agnostic
GENERATED_PREFIXES = (".agents/plans/",)


@pytest.mark.parametrize("doc", ["AGENTS.md", "README.md", "docs/architecture.md"])
def test_referenced_markdown_paths_exist(doc: str) -> None:
    """A pointer to a moved file is worse than no pointer: it reads as authoritative.

    Only committed `.md` targets are checked. These docs also name files deliberately
    not written yet (`src/app/main.py`) and files generated per session
    (`.agents/plans/plan.md`); neither is broken.
    """
    text = (REPO_ROOT / doc).read_text(encoding="utf-8")
    # harness:agnostic
    pattern = re.compile(
        r"`((?:src/app|tests|docs|\.agents|\.claude|\.out-of-scope)[\w/.\-]*?\.md)`"
    )
    # /harness:agnostic
    # harness:claude
    # pattern = re.compile(r"`((?:src/app|tests|docs|\.claude|\.out-of-scope)[\w/.\-]*?\.md)`")
    # /harness:claude

    missing = sorted(
        {
            m
            for m in pattern.findall(text)
            if not m.startswith(GENERATED_PREFIXES) and not (REPO_ROOT / m).exists()
        }
    )
    assert not missing, f"{doc} points at files that do not exist:\n  " + "\n  ".join(missing)
