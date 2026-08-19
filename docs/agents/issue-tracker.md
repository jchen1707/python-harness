# Issue tracker: Linear — this repo

**Shared doctrine is provided by the `harness` plugin**, at
`${CLAUDE_PLUGIN_ROOT}/docs/agents/issue-tracker.md` — connecting, tool discovery, the
operation table, status sync, wayfinding, the AI-authorship disclaimer and the
spec-correction procedure. Read it first.

This file records only what is true in **this** repo.

## Workspace and team

|              | Value                                                        |
| ------------ | ------------------------------------------------------------ |
| Workspace    | **Development** (`development-jchen`)                        |
| Default team | **Backend**, key `BAC` — issue ids read `BAC-12`             |
| Sibling team | Frontend, key `FRO` — `frontend-harness` files there, not us |

Create issues in **Backend** unless the work is plainly frontend.

Name branches `<type>/BAC-<num>-<slug>` (e.g. `feat/BAC-412-vector-store`). The Spec axis of
a review resolves the ticket from that prefix, so a branch named with the wrong one silently
loses the axis.

## Repo-specific notes

- The **Standards** axis of `/code-review` reads `docs/architecture.md` (authoritative) plus
  the summary in `CLAUDE.md`. Those override the skill's generic smell baseline.
- Definition of Done lives in `CLAUDE.md`; `/verify` runs those gates and prints evidence.
