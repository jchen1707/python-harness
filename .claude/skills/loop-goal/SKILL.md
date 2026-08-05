---
name: loop-goal
description: Run a standing goal until a stated condition holds — doc sweep, architecture satisfaction, logging coverage, test coverage, dependency freshness. Use when the user wants work driven to completion rather than one pass, or names one of the goals below.
argument-hint: "[goal name or a custom stop condition]"
disable-model-invocation: true
---

A standing goal is work with a **stop condition** instead of a task list. You keep
going until the condition holds, not until one pass finishes.

`disable-model-invocation` is set deliberately: these loops edit code and burn
tokens over many turns. Starting one must be the user's explicit act.

## Protocol

1. **State the stop condition first**, in one sentence, and get agreement if
   `$ARGUMENTS` was vague. A loop with a fuzzy condition never terminates.
2. **Open a progress file** at `.claude/plans/loop-<goal>.md` (gitignored). It
   survives compaction, which the conversation does not. Record:
   - the stop condition, verbatim
   - a checklist of areas, each `pending` / `done` / `skipped (reason)`
   - what changed each pass, one line per pass
3. **Work one area per pass.** Smallest useful unit. After each: run `/verify`,
   commit if green, update the progress file.
4. **Re-read the progress file at the start of every pass.** Trust it over your
   memory of the conversation — after a compaction it is the only accurate record.
5. **Stop when the condition holds.** Report what changed, what you skipped and
   why. If you cannot reach the condition, say so plainly and stop; do not loop
   on something unreachable.

## Guardrails

- **Never loop on a condition you cannot measure.** "Until the architecture is
  good" is not a condition; "until no module in `services/` imports from `api/`"
  is. Convert vague goals before starting.
- **Cap the passes.** Default 10. Stop and report progress at the cap rather than
  continuing silently.
- **Never `git push` or open a PR from inside a loop** unless the goal explicitly
  says to. Committing to the working branch is fine.
- If two consecutive passes produce no change, stop — you have converged or you
  are stuck, and both mean the loop is over.

## Goals

Each names its own stop condition. Use these verbatim unless the user overrides.

| Goal | Stop condition |
| --- | --- |
| `docs` | Every claim in `CLAUDE.md`, `README.md` and `docs/architecture.md` matches the code; every documented command runs; no reference to a deleted file or command |
| `architecture` | No layering violation (`api` → `services` → `repositories` → `config`, no reverse deps); every cross-layer dependency goes through a protocol in `repositories/`; `/verify` green |
| `logging` | Every error path and every external call (DB, LLM, embeddings, HTTP) emits a structlog event with bound context; no bare `except: pass`; no `print()` |
| `tests` | Every public function in `src/app/` has at least one test exercising a real behaviour; every test failure mode from the test plan is covered; `uv run pytest` green |
| `deps` | Every dependency in `pyproject.toml` is used; nothing used is missing; the approved-stack list in `CLAUDE.md` matches what is installed |

## Running unattended

To run without stopping for input, pass the goal and a turn budget, and rely on
the `Stop` hook (`.claude/hooks/verify.py`) to keep the loop honest — it blocks
the turn while the Definition of Done fails, so a pass cannot end on broken code.

Note the harness overrides a `Stop` hook after **8 consecutive blocks**. If a pass
hits that, the loop is stuck on something it cannot fix: stop and report, do not
start another pass.
