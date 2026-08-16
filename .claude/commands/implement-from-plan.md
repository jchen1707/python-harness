---
description: Hand the branch's plan.md + test-plan.md (under .agents/plans/) to the /implement skill as its spec, with this repo's uv gates pinned (terminal 2, implementation model)
argument-hint: "[path to a plan file, or blank to resolve from the current branch]"
---

Two-terminal workflow — **terminal 2 (implementation model)**. This is a thin adapter
over the vendored `/implement` skill: that skill implements "a spec or set of tickets"
but does **not** know about this repo's plan files or its `uv`-based gates. This command
supplies both.

1. **Locate the plans.** Derive the plan directory from the current branch: take
   `git branch --show-current`, replace each `/` with `-`, and read
   `.agents/plans/<branch-slug>/plan.md` + `test-plan.md` (e.g. branch
   `feat/BAC-412-vector-store` → `.agents/plans/feat-BAC-412-vector-store/`). If
   `$ARGUMENTS` names a path, that wins as the implementation plan, with a sibling
   `test-plan.md`. If the per-branch directory does not exist, fall back to the legacy
   `.agents/plans/plan.md` + `test-plan.md`.
   - If no plan is found in any of those places, **STOP** and tell the user to run
     `/plan` in terminal 1 first. Do not improvise a plan here — planning is a
     separate, signed-off step.
   - If `test-plan.md` is missing, ask the user whether to proceed without it or go
     back to `/plan`. Don't silently skip the test plan.
2. **Read both files in full** before doing anything else. The plan is the source of
   truth: do not re-plan or re-scope it. If a Step looks wrong or impossible, flag it
   to the user and ask — don't quietly substitute your own approach.
3. **Confirm the branch.** `/plan` creates the feature branch off the user's chosen
   base. Run `git branch --show-current`; if you're on `main`, stop and ask which
   branch to use — per AGENTS.md, direct commits to `main` need explicit user request.
4. **Invoke `/implement` with the plans as the spec.** Say explicitly that the spec is
   the resolved `plan.md` plus `test-plan.md` (name their full paths), and pass along:
   - the numbered **Steps** from `plan.md` as the task list (build it with `TaskCreate`,
     one task per Step, marking each in_progress/complete as you go);
   - the **test cases** from `test-plan.md` as the cases to drive `/tdd` with, and the
     **seams** it names as the pre-agreed seams (`/tdd` requires seams be confirmed
     before any test is written — the test plan is that confirmation);
   - the **Open questions** from `plan.md`, to raise with the user rather than guess.
5. **Pin the gates — this repo is Python, not TypeScript.** The plugin skills say "run
   typechecking" and "run the test suite" generically, and reach for `npm`, `tsc`,
   `vitest`, Husky and `lint-staged`, none of which exist here. Wherever a skill says
   that, substitute the `uv` commands from **AGENTS.md → Commands** (the authoritative
   list, loaded every session); for a single file, `uv run pytest tests/test_<name>.py`.
6. **Finish to the Definition of Done** (AGENTS.md). Run `/verify` for the evidence —
   paste the real output rather than asserting the gates passed. Then `/code-review`
   with the merge-base as the fixed point (`git merge-base HEAD main`) and no Standards
   findings outstanding. The `Stop` hook re-runs the gates independently, so a turn
   cannot end on failing Python under `src/` or `tests/`.
7. **Update the plans as you go** — tick off Steps in `plan.md` and cases in
   `test-plan.md` as they land, so an interrupted session can resume from the files.
8. **Commit and stop.** `/implement` commits to the current branch. Opening the PR is a
   separate, explicit step — run `gh pr create` only if the user asks. Report what
   landed, what's left, and anything the plan got wrong.
