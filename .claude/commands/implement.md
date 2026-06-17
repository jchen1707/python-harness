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
6. **Update the plans (append-only — never launder the contract).** The signed-off plan
   is a contract, not a worklog. As you complete steps, tick them done in
   `.claude/plans/plan.md` / `test-plan.md`, but do NOT rewrite the approved
   **Goal / Approach / Steps** to match what you actually built. Record every divergence
   in an append-only `## Deviations` section ("Step N planned X, implemented Y, because
   Z"), leaving the original approved text intact, so the plan tells the plan-vs-reality
   story rather than just final reality.
7. **Open a PR automatically.** Once the Definition-of-Done gates pass, ship the work
   without prompting: commit the changes on the feature branch (minimal, per-layer
   commits), push it, then open a PR with `gh pr create` against the base branch the plan
   was built off of. Never commit straight to `main`. The PR body must summarize what
   shipped AND carry over any **material** deviations from the `## Deviations` section —
   `plan.md` is gitignored, so the PR is the durable record of approved-vs-shipped. If a
   gate is still red, fix the root cause first; do not open a PR over failing checks.

## Handling plan deviations
The plan was signed off by the user, so deviating from it changes something they
approved. Classify before you act:
- **Material deviation** — anything that changes the **Approach**, a public
  interface/signature, layer boundaries, the **sync/async** decision, scope, or anything
  in the plan's **Open questions** (or that the user explicitly weighed in on at
  sign-off). **STOP and re-confirm with the user** (`AskUserQuestion`) before building it.
  Do not silently rewrite the plan to match — that retroactively voids the sign-off.
- **Immaterial deviation** — a function name, a file split, an extra private helper, or
  fixing an obvious bug in the plan's pseudocode. Proceed, but log it in the plan's
  `## Deviations` section. This is the latitude implementation is expected to have;
  halting on it just kills autonomy.

Rough test: *would the user have wanted to weigh in on this?* If yes, it's material. If a
deviation reveals the plan was systematically wrong (a recurring shape of mistake, not a
one-off), capture the lesson with `/retro` so planning improves.

`plan.md` and `test-plan.md` are gitignored — local working artifacts, not committed.
