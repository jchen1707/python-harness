---
name: prune-rules
description: Audit the rule files for drift, duplication and dead rules, then refine them. Use when a rule file has grown, after a stack or tooling change, or when rules contradict each other.
---

Rule files decay. They grow faster than they shrink, they duplicate each other, and they
keep rules for tools the project no longer uses. A rule nobody follows teaches an agent
that rules are optional.

This skill audits them and proposes repairs. The focus is `$ARGUMENTS`; if empty, audit
all of them.

## The rule files

| File | Scope |
| --- | --- |
| `CLAUDE.md` | Root. Loaded every session. |
| `docs/architecture.md` | Cross-cutting standards only. |
| `src/app/*/CLAUDE.md` | Per-layer conventions, path-scoped. |
| `src/app/ai/CLAUDE.md` | Why AI is its own layer; rules covering all of it. |
| `src/app/ai/*/CLAUDE.md` | Retrieval, reranking, agents, evals. |
| `tests/CLAUDE.md` | Test conventions. |
| `docs/agents/*.md` | Tracker and triage conventions — the repo-specific half only. |
| `.claude/agents/*.md` | Subagent definitions, also the `full-review` axes. |
| `.claude/skills/*/SKILL.md` | Repo-owned skills — including this one. |

**Glob the tree, do not trust this table.** It is itself a rule file and can go stale; an
audit that reads only the paths listed here will miss whatever moved since it was written.
That has already happened once, when the AI layers moved out of `services/`.

## What to look for

**Duplication.** The same rule stated in two files. Two copies drift, and nothing detects
it — the copies stay plausible while disagreeing. Keep one, and point the other at it.

**Wrong altitude.** A cross-layer invariant sitting in a leaf file, or a single-layer
detail sitting in `architecture.md`. Nested `CLAUDE.md` files are **path-scoped**: an
agent working in `api/` never loads `repositories/CLAUDE.md`. A rule that must hold
everywhere belongs in `architecture.md` or root `CLAUDE.md`, or it is not enforced where
it matters.

**Dead rules.** A rule about a library, a command or a file that no longer exists. Verify
before deleting: read `pyproject.toml`, run the command, look for the path.

**Contradictions.** Two files that give different answers. This is the highest-value find,
because it means an agent is currently obeying whichever it happened to read. Report both
and say which is newer.

**Tooling overlap.** A rule that ruff or mypy already enforces. Delete it. A rule the
tooling enforces is noise in a prompt, and it dilutes the rules that need a human to
follow them.

**Unverifiable rules.** "Write clean code." "Be thoughtful." They cost context and change
no behaviour. Replace with something checkable or cut.

**Missing rationale.** A rule with no reason is a rule that gets deleted by the next
person who finds it inconvenient. If the reason is not obvious, add one line. If nobody
can remember the reason, that is a candidate for deletion.

**Staleness.** Counts, versions and file lists in prose go out of date silently. Check
every number against the thing it describes.

## Method

1. **Read the files in the focus area.** All of them, before proposing anything. A
   duplication finding needs both copies.
2. **Verify each claim you doubt** against the repo. Do not report a rule as dead because
   you do not recognise it — check `pyproject.toml`, the file tree, the command's
   `--help`.
3. **Group findings by repair**, not by file. "This rule appears in three places" is one
   finding.
4. **Propose, then wait.** Present the findings with the proposed edit for each, and stop.
   Deleting a rule someone relies on is worse than leaving a stale one.
5. **Apply only what is approved**, and re-run `/verify` if any file the gates read has
   changed.

## Deprecating, not just deleting

When a rule is being withdrawn but code still follows it, do not delete it silently. Mark
it, give the replacement, and give a date:

```markdown
> **Deprecated 2026-08-05.** Use `Annotated[T, Depends(...)]`. The old form fails ruff
> B008. This note is removed once no call site uses it.
```

Delete the note when the last call site is gone. A deprecation with no removal condition
becomes permanent.

## What not to do

- **Do not rewrite for style.** The task is correctness and duplication, not prose taste.
  A rule that reads awkwardly but is followed beats a beautiful one that is not.
- **Do not delete a rule because it is inconvenient.** It exists for a reason you may not
  have hit yet. If the reason is not written down, ask before cutting.
- **Do not add rules.** This skill removes and consolidates. Adding is a separate,
  deliberate act.
- **Do not touch `.out-of-scope/`.** Those are decisions, not rules.

## Report

Lead with the count by category, then each finding: the files, the exact text, the
proposed repair, and the reason. End with what you checked and found healthy — a clean
audit is a useful result and should be said plainly, not padded into findings.
