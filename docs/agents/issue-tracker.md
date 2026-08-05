# Issue tracker: Linear

Issues, specs and tickets for this repo live in **Linear**, reached over MCP. **Pull
requests stay on GitHub** — Linear holds the work item, GitHub holds the diff.

## Connecting

Linear comes from the **claude.ai account connector**, not from a repo-level `.mcp.json`.
It follows the account, so it is already available in every project once connected — there
is nothing to approve per repo.

- Check it with `/mcp`; it appears as **claude.ai Linear**.
- MCP servers load at **session start**. Connecting mid-session does not make the tools
  available until you restart.
- If it is absent, connect Linear in your claude.ai connector settings.

## Discovering the tools

**List the tools before first use rather than assuming names.** The prefix depends on how
Linear is connected — an account connector and a project server expose the same service
under different names — and the surface changes between releases.

`/mcp` shows the connected servers and their tools. Match the operation you need from the
table below to what is actually offered.

## Conventions

| Operation | What to call |
| --- | --- |
| **Create an issue** | the create-issue tool — needs `team`; set `title`, `description` (markdown), optional `labels`, `project` |
| **Read an issue** | the get-issue tool, with the identifier (`ENG-123`) |
| **List issues** | the list-issues tool — filter by `team`, `state`, `assignee`, `label` |
| **Comment** | the create-comment tool, with the issue id and markdown `body` |
| **Apply/remove labels** | the update-issue tool, setting the `labels` array |
| **Change state** | the update-issue tool, with the target workflow state |
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

Get the issue by identifier, then read its comments for the discussion.

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
