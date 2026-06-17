---
description: Read .claude/plans/plan.md + test-plan.md, build a fresh task list, and implement to the Definition of Done (terminal 2, implementation model)
---

Two-terminal workflow — **terminal 2 (implementation model)**. Read the plan and test
plan written and signed off in terminal 1, build a fresh task list from them, and
implement the rest. Do not re-plan from scratch — the plan is the source of truth;
only flag issues back.

1. **Read the plans** — read `.claude/plans/plan.md` and `.claude/plans/test-plan.md`
   (or the path in `$ARGUMENTS` if given). If `plan.md` is missing, stop and tell the
   user to run `/plan` in terminal 1 first. If `test-plan.md` is missing, ask the user
   whether to proceed or to go back to `/plan` for it.
2. **Build the implementation task list** — create one `TaskCreate` task per numbered
   **Step** in the plan, plus the test cases from `test-plan.md` and a final `Verify`
   task. Work them in order, marking each in_progress/complete.
3. **Implement** — for each step, write code in the correct layer (`api` / `services`
   / `repositories` / `config`), types on every public function, Pydantic for I/O,
   async for I/O, dependencies behind interfaces. No `print()` (use structlog); no
   hardcoded secrets.
4. **Write the tests** — implement the cases from `test-plan.md` (unit offline by
   default; integration marked `integration`). New behavior must have tests.
5. **Verify** — run the gates per the plan's Verification section and CLAUDE.md
   Definition of Done: `/lint`, then `/test` (then `uv run pytest -m integration` for
   DB-backed work), then `/review`. Fix root causes; don't paper over failures.
6. **Update the plans** — as you complete steps, update `.claude/plans/plan.md` and
   `test-plan.md` (mark items done, note deviations or follow-ups) so they reflect reality.
7. **Commit** — only when asked; keep changes minimal and per-layer. Ship substantive
   changes via a PR, not a direct commit to `main`.

`plan.md` and `test-plan.md` are gitignored — local working artifacts, not committed.
