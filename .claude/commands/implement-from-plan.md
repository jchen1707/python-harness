---
description: Hand .claude/plans/plan.md + test-plan.md to the /implement skill as its spec, with this repo's uv gates pinned (terminal 2, implementation model)
argument-hint: "[path to a plan file, or blank for .claude/plans/plan.md]"
---

Two-terminal workflow — **terminal 2 (implementation model)**. This is a thin adapter
over the vendored `/implement` skill: that skill implements "a spec or set of tickets"
but does **not** know about this repo's plan files or its `uv`-based gates. This command
supplies both.

1. **Locate the plans.** Default to `.claude/plans/plan.md` and
   `.claude/plans/test-plan.md`; if `$ARGUMENTS` names a path, use that as the
   implementation plan and look for a sibling `test-plan.md`.
   - If `plan.md` is missing, **STOP** and tell the user to run `/plan` in terminal 1
     first. Do not improvise a plan here — planning is a separate, signed-off step.
   - If `test-plan.md` is missing, ask the user whether to proceed without it or go
     back to `/plan`. Don't silently skip the test plan.
2. **Read both files in full** before doing anything else. The plan is the source of
   truth: do not re-plan or re-scope it. If a Step looks wrong or impossible, flag it
   to the user and ask — don't quietly substitute your own approach.
3. **Confirm the branch.** `/plan` creates the feature branch off the user's chosen
   base. Run `git branch --show-current`; if you're on `main`, stop and ask which
   branch to use — per CLAUDE.md, direct commits to `main` need explicit user request.
4. **Invoke `/implement` with the plans as the spec.** Say explicitly that the spec is
   `.claude/plans/plan.md` plus `.claude/plans/test-plan.md`, and pass along:
   - the numbered **Steps** from `plan.md` as the task list (build it with `TaskCreate`,
     one task per Step, marking each in_progress/complete as you go);
   - the **test cases** from `test-plan.md` as the cases to drive `/tdd` with, and the
     **seams** it names as the pre-agreed seams (`/tdd` requires seams be confirmed
     before any test is written — the test plan is that confirmation);
   - the **Open questions** from `plan.md`, to raise with the user rather than guess.
5. **Pin the gates — this repo is Python, not TypeScript.** The vendored skills say
   "run typechecking" and "run the test suite" generically. Here that means:
   - typecheck: `uv run mypy` · lint: `uv run ruff check .` · format:
     `uv run ruff format --check .`
   - a single test file: `uv run pytest tests/test_<name>.py`
   - full suite: `uv run pytest` (and `uv run pytest -m integration` for DB-backed
     work, which needs Docker + `uv sync --extra app`)
   - Ignore any instruction to use `npm`, `tsc`, `vitest`, Husky, or `lint-staged`.
     `/setup-pre-commit` and `/setup-ts-deep-modules` do not apply to this repo.
6. **Finish to the Definition of Done** (CLAUDE.md): all gates clean, no secrets, no
   `print()`, new behavior tested, then `/code-review` with the merge-base as the fixed
   point (`git merge-base HEAD main`) and no Standards findings outstanding.
7. **Update the plans as you go** — tick off Steps in `plan.md` and cases in
   `test-plan.md` as they land, so an interrupted session can resume from the files.
8. **Commit and stop.** `/implement` commits to the current branch. Opening the PR is a
   separate, explicit step — run `gh pr create` only if the user asks. Report what
   landed, what's left, and anything the plan got wrong.
