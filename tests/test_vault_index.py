"""Guardrail tests for the whole-vault indexer (`.claude/hooks/vault_index.py`).

The index is the only thing an agent reads before deciding which notes to open, so its
failures are silent in the expensive direction: a note with a blank or wrong row is a note
that never gets retrieved, and nothing reports it. The vault is the user's own writing —
the indexer never gets to demand a particular shape from it.

These stay offline. Every test builds a throwaway vault under `tmp_path`; nothing here
reads the real one.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HOOK_PATH = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "vault_index.py"


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    """Load the module by path — `.claude/hooks` is not an importable package."""
    spec = importlib.util.spec_from_file_location("_vault_index_under_test", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_front_matter_reads_both_tag_shapes(hook: ModuleType) -> None:
    """The vault uses inline `[a, b]` and indented block sequences interchangeably.

    Handling only one shape silently drops the tags of every note using the other, and a
    tagless row still looks like a valid row.
    """
    inline = hook.front_matter("---\ntags: [ai, claude-code]\nupdated: 2026-08-03\n---\n\nBody")
    assert inline["tags"] == "ai, claude-code"
    assert inline["updated"] == "2026-08-03"

    block = hook.front_matter("---\ntags:\n  - hashmap\n  - easy\n---\n\nBody")
    assert block["tags"] == "hashmap, easy"


def test_unterminated_front_matter_is_not_front_matter(hook: ModuleType) -> None:
    """A note opening with a horizontal rule is body text, not metadata.

    `Getting Hired/Behavioral/General.md` starts this way. Parsing greedily to end of file
    would turn the whole note into one bogus field.
    """
    assert hook.front_matter("---\n\nJust a rule, then prose that never closes it.\n") == {}


def test_description_prefers_the_written_summary(hook: ModuleType) -> None:
    """A `summary:` field beats anything inferred, so the hook's own notes index well."""
    text = "---\nsummary: MCP config location and subprocess encoding.\n---\n\n## Heading\n\nProse."
    assert hook.describe(text) == "MCP config location and subprocess encoding."


@pytest.mark.parametrize(
    ("note", "expected"),
    [
        # Headings, bullets and table rows say nothing about what a note covers.
        (
            "# Caching\n\n- a bullet\n\nCaching keeps expensive results close to the reader.\n",
            "Caching keeps expensive results close to the reader.",
        ),
        # Obsidian callouts wrap the informative text in markup.
        (
            "> [!question] How do you handle conflict at work?\n",
            "How do you handle conflict at work?",
        ),
        # Links and emphasis are noise around real prose.
        (
            "Companion to [[Agentic Coding Workflow]] and **the** hooks note it links.\n",
            "Companion to Agentic Coding Workflow and the hooks note it links.",
        ),
    ],
)
def test_description_is_derived_when_there_is_no_summary(
    hook: ModuleType, note: str, expected: str
) -> None:
    """Most of the vault has no front matter at all.

    An indexer that only describes annotated notes would have covered 20 of 50 notes on
    the day it shipped, which is the failure that makes an index not worth reading.
    """
    assert hook.describe(note) == expected


def test_a_bullet_nested_in_a_callout_is_still_a_bullet(hook: ModuleType) -> None:
    """The behavioural notes hide their bullets two levels inside a callout.

    Testing the raw line for noise lets `>> - **Now:** current role` through as prose,
    and a half-sentence of answer scaffolding becomes the note's description.
    """
    note = (
        "> [!question] Why do you want to work here?\n"
        ">> [!success]- Answer\n"
        ">> - **Now:** current role, focus, one line on what you are good at\n"
    )
    assert hook.describe(note) == "Why do you want to work here?"


def test_a_shared_pointer_line_does_not_become_the_description(hook: ModuleType) -> None:
    """Whole folders open with the same "Refer to [[Template]]" line.

    Taking it verbatim gives a dozen unrelated notes an identical description, which is
    the one thing that makes an index useless: it cannot be used to choose between rows.
    """
    note = (
        "Follows [[Getting Hired/LeetCode/Framework|the interview framework]].\n"
        "\n"
        "Given an array of integers nums and a target, return the indices of the pair.\n"
    )
    assert hook.describe(note).startswith("Given an array")


def test_a_pointer_is_still_better_than_nothing(hook: ModuleType) -> None:
    """Some notes are only a pointer. An empty row loses the note entirely, so the
    pointer is kept as the fallback rather than discarded."""
    assert hook.describe("Refer to [[Template]] for guidance on answer delivery.\n") == (
        "Refer to Template for guidance on answer delivery."
    )


@pytest.mark.parametrize(
    ("note", "expected"),
    [
        # A checklist or a set of takeaways is a whole genre of note in this vault.
        (
            "# Prompt caching\n\n- cache the system prompt, not the user turn\n- measure hit rate\n",
            "Prompt caching · cache the system prompt, not the user turn · measure hit rate",
        ),
        # An outline the user never filled in still says what the note is about.
        (
            "# Retro\n\n## What went well\n\n## What to change\n",
            "Retro · What went well · What to change",
        ),
    ],
)
def test_a_note_of_only_headings_and_bullets_still_gets_a_description(
    hook: ModuleType, note: str, expected: str
) -> None:
    """Returning "" here hides a real note from the only file an agent reads first.

    `search-second-brain` reads a blank row as an empty stub and is told not to open it,
    so a bullet-list note would be skipped on the strength of a description the indexer
    declined to derive.
    """
    assert hook.describe(note) == expected


def test_prose_and_pointers_still_outrank_the_outline(hook: ModuleType) -> None:
    """The outline is the last resort, not a competitor.

    A sentence the user wrote describes the note better than its own headings, and the
    fallback must not start winning against one.
    """
    with_prose = "# Caching\n\n- a bullet\n\nCaching keeps expensive results close.\n"
    assert hook.describe(with_prose) == "Caching keeps expensive results close."

    with_pointer = "- a bullet\n\nRefer to [[Template]] for guidance on answer delivery.\n"
    assert hook.describe(with_pointer) == "Refer to Template for guidance on answer delivery."


def test_a_note_with_no_readable_text_is_still_blank(hook: ModuleType) -> None:
    """The blank row has to keep meaning something, or the index gains noise instead.

    11 of the vault's notes are 0-byte stubs. A fallback that invented text for those
    would make every row look equally informative.
    """
    assert hook.describe("") == ""
    assert hook.describe("\n\n   \n") == ""


def test_notes_skips_generated_and_non_prose_folders(hook: ModuleType, tmp_path: Path) -> None:
    """Excalidraw notes are base64 payloads and indexes are machinery; neither is a note."""
    (tmp_path / "Upskilling").mkdir()
    (tmp_path / "Upskilling" / "Caching.md").write_text("Caching notes.", encoding="utf-8")
    (tmp_path / "Excalidraw").mkdir()
    (tmp_path / "Excalidraw" / "Drawing.md").write_text("base64...", encoding="utf-8")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "notes.md").write_text("config", encoding="utf-8")
    (tmp_path / "_VAULT_INDEX.md").write_text("generated", encoding="utf-8")
    (tmp_path / "_INDEX.md").write_text("generated", encoding="utf-8")

    found = [p.relative_to(tmp_path).as_posix() for p in hook.notes(tmp_path)]
    assert found == ["Upskilling/Caching.md"]


def test_build_escapes_pipes_so_a_note_cannot_break_the_table(
    hook: ModuleType, tmp_path: Path
) -> None:
    """A description containing `|` would split into extra columns and corrupt every row
    after it — from a note doing nothing more unusual than mentioning a shell pipe."""
    (tmp_path / "Shell.md").write_text(
        "Pipe stdout with cmd | grep foo when you want fewer lines.\n", encoding="utf-8"
    )
    table = [line for line in hook.build(tmp_path).splitlines() if line.startswith("| `")]

    assert len(table) == 1
    assert "\\|" in table[0]
    assert table[0].count("|") - table[0].count("\\|") == 4  # 4 unescaped delimiters, 3 cells


def test_build_lists_every_note_exactly_once(hook: ModuleType, tmp_path: Path) -> None:
    """The count in the header is what a reader trusts to know the index is complete."""
    (tmp_path / "a").mkdir()
    for name in ("a/One.md", "a/Two.md", "Three.md"):
        (tmp_path / name).write_text(
            "Some prose long enough to describe the note.", encoding="utf-8"
        )

    rendered = hook.build(tmp_path)
    assert "3 notes." in rendered
    assert rendered.count("| `") == 3


def test_vault_dir_falls_back_to_the_parent_of_the_learnings_dir(
    hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The common layout is a learnings folder inside a vault.

    Requiring a second variable to state something already derivable is configuration the
    user would have to get right for the index to appear at all.
    """
    learnings = tmp_path / "Project Learnings"
    learnings.mkdir()
    monkeypatch.delenv("CLAUDE_VAULT_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_LEARNINGS_DIR", str(learnings))

    assert hook.vault_dir() == tmp_path


def test_index_is_written_with_lf_endings(
    hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """More than one repo writes this vault now, and they must agree on line endings.

    `write_text` translates every `\\n` to `os.linesep` unless told otherwise, so a
    Windows writer emits CRLF and a Linux one LF. With a single writer that never
    surfaced; with several, the whole file is rewritten whenever the platform changes,
    and every line reads as modified to Obsidian, OneDrive and git alike.

    Asserted on bytes: decoded text is exactly where the difference disappears.
    """
    (tmp_path / "Note.md").write_text("Prose long enough to describe a note.", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_VAULT_DIR", str(tmp_path))

    written = hook.refresh()

    assert written is not None
    assert b"\r" not in written.read_bytes()


def test_no_vault_configured_is_silent(hook: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """A clone with no second brain must not have its sessions disturbed by this."""
    monkeypatch.delenv("CLAUDE_VAULT_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_LEARNINGS_DIR", raising=False)

    assert hook.vault_dir() is None
    assert hook.refresh() is None
