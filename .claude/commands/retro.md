---
description: Capture a lesson from a bug or tool-friction so future sessions go smoother
---

Run a quick retrospective on friction hit during this session and write durable
**lessons** to the memory store so the same trap is avoided next time. "Friction"
means: a bug that took real effort to diagnose, an approach that failed before the
one that worked, or difficulty using a tool — wrong flags, Windows/PowerShell
quirks, env/setup gotchas, API misuse, or a command that didn't do what its name
implied.

The argument optionally names a specific lesson to capture; if empty, scan the
session for any: `$ARGUMENTS`.

For each durable, non-obvious lesson:

1. **Decide if it's worth saving.** Keep only what would have saved real time had
   you known it up front. Skip anything the repo already records (code, git history,
   `AGENTS.md`, `docs/architecture.md`) or that mattered only to this one task.
2. **Check for an existing memory** first — scan `MEMORY.md`. Update that file
   rather than duplicating it; delete one that turns out to be wrong.
3. **Write the lesson to the memory store** at
   `~/.claude/projects/<project-slug>/memory/`
   as one file with frontmatter, then add a one-line pointer to `MEMORY.md`:
   - `name`: `lesson-<short-kebab-slug>`.
   - `type`: `feedback` for a "how to work here" lesson; `reference` for an
     environment / tool / external-API gotcha (a pointer to the fix).
   - Body: state the lesson in a line or two (the symptom + what actually worked).
     For `feedback`, follow the store's convention with **Why:** (the root cause /
     why it happens) and **How to apply:** (the concrete thing to do next time to
     avoid it). Link related memories with `[[name]]`.
4. **Escalate if it's recurring or procedural.** A one-off fact stays a memory. But
   if the lesson is a repeatable procedure or a standard everyone working here should
   follow, propose promoting it:
   - a repeatable workflow → a new slash command in `.claude/commands/`;
   - a durable standard or stack/tooling rule → an edit to `AGENTS.md` or
     `docs/architecture.md`.
   Memories are cheap and reversible — write them directly. Promotions to a command
   or to `AGENTS.md` / docs are more invasive — propose the change and confirm before
   applying it.

Report what you captured and any promotion you propose. See the "Context & memory
management" section of `AGENTS.md`; `/context` flags friction you haven't captured yet.
