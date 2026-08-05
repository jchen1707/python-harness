# Issue tracker: Linear

Issues, specs and tickets for this repo live in **Linear**, reached through the Linear MCP
server declared in `.mcp.json` (`https://mcp.linear.app/mcp`). **Pull requests stay on
GitHub** — Linear holds the work item, GitHub holds the diff.

> **First run:** the MCP server uses OAuth. Run `/mcp` and authenticate `linear` once per
> machine before any skill that writes to the tracker. Until then every operation below
> fails with an auth error.

## Discovering the tools

Linear's MCP tools are exposed as `mcp__linear__<tool>`. **List them before first use**
rather than assuming names — the server's surface changes between releases:

- In session: `/mcp` shows the connected servers and their tools.
- The names below are the expected ones; if a call fails with "unknown tool", re-check
  against `/mcp` and use what's actually offered.

## Conventions

| Operation | How |
| --- | --- |
| **Create an issue** | `mcp__linear__create_issue` — needs `team`; set `title`, `description` (markdown), optional `labels`, `project` |
| **Read an issue** | `mcp__linear__get_issue` with the identifier (`ENG-123`) |
| **List issues** | `mcp__linear__list_issues` — filter by `team`, `state`, `assignee`, `label` |
| **Comment** | `mcp__linear__create_comment` with the issue id and markdown `body` |
| **Apply/remove labels** | `mcp__linear__update_issue`, setting the `labels` array |
| **Change state** | `mcp__linear__update_issue` with the target workflow state |
| **Close** | move to the team's Done/Cancelled state — Linear has no separate close verb |

Issue identifiers are `TEAM-NUMBER` (e.g. `ENG-4521`), not bare integers. A reference like
`#42` in conversation is **not** a Linear id — ask which team it belongs to rather than
guessing.

## Labels vs workflow states

Linear separates **workflow state** (Backlog / Todo / In Progress / Done — a single value
that drives the board) from **labels** (many per issue). The five canonical triage roles in
`triage-labels.md` are **labels**, not states. Applying `ready-for-agent` does not move the
issue across the board; set the state explicitly when the role implies one.

## When a skill says "publish to the issue tracker"

Create a Linear issue in the default team. Put the spec in the issue `description` as
markdown. If the skill produced a document longer than fits comfortably, put the summary
and acceptance criteria in the description and link the full document.

## When a skill says "fetch the relevant ticket"

`mcp__linear__get_issue` with the identifier, then `mcp__linear__list_comments` (or the
comments included in the issue payload) for the discussion.

## Wayfinding operations

Used by `/wayfinder`. The **map** is one issue; **tickets** are its children.

- **Map** — an issue labelled `wayfinder:map` holding the Notes / Decisions-so-far / Fog body.
- **Child ticket** — a Linear **sub-issue** of the map (`parent` field), labelled
  `wayfinder:<type>` (`research` / `prototype` / `grilling` / `task`).
- **Blocking** — Linear has native issue relations: use the **blocks / blocked-by**
  relation rather than a text convention. A ticket is unblocked when every blocker
  reaches a completed state.
- **Frontier query** — the map's sub-issues that are not Done, have no unresolved
  blocked-by relation, and no assignee; first in map order wins.
- **Claim** — assign the issue to the current user; this is the session's first write.
- **Resolve** — comment the answer, move to Done, then append a pointer to the map's
  Decisions-so-far.

## Repo-specific notes

- The **Standards** axis of `/code-review` reads `docs/architecture.md` (authoritative)
  plus the summary in `CLAUDE.md`. Those override the skill's generic smell baseline.
- The **Spec** axis resolves the originating ticket from the Linear id in the branch name
  or commit trailer. Name branches `<type>/<TEAM-NUM>-<slug>` (e.g.
  `feat/ENG-412-vector-store`) so the link is mechanical.
- Definition of Done lives in `CLAUDE.md`; `/verify` runs those gates and prints evidence.
