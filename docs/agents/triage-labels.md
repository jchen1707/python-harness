# Triage Labels

The skills speak in terms of canonical triage roles: two **category** roles and five
**state** roles. Every triaged issue carries exactly one of each. This file maps those roles
to the actual label strings used in this repo's issue tracker.

## Category roles

| Role in mattpocock/skills | Label in our tracker | Meaning                     |
| ------------------------- | -------------------- | --------------------------- |
| `bug`                     | `Bug`                | Something is broken         |
| `enhancement`             | `Feature`            | New feature or improvement  |

## State roles

| Role in mattpocock/skills | Label in our tracker | Meaning                                  |
| ------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`            | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`              | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`         | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`         | `ready-for-human`    | Requires human implementation            |
| `wontfix`                 | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the
corresponding label string from these tables.

Edit the right-hand columns to match whatever vocabulary you actually use.

## Note for this repo

The tracker is **Linear** (see `issue-tracker.md`). All seven labels exist in the workspace.
The five state labels live under a **`Triage`** parent group; the category labels are
ungrouped workspace labels.

State labels are **labels**, not workflow states — applying one does not move the issue
across the board. Set the Linear workflow state explicitly when the role implies one.

### `Improvement` is not a triage category

The workspace also has an `Improvement` label predating this mapping. Triage does **not**
apply it: the skill requires exactly one category role per issue, and both `Feature` and
`Improvement` would map to `enhancement`, producing two categories on one issue. `Feature`
is the single `enhancement` target. `Improvement` stays available for manual use.

### Editing labels needs the Linear UI

The Linear MCP server exposes `create_issue_label` but **no update or delete** for labels.
Renaming a label, fixing a description, or removing one has to happen in the Linear UI
(Settings → Labels) — an agent session cannot do it. Only the mapping tables above are
editable from here.
