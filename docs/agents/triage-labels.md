# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Note for this repo

The tracker is **Linear** (see `issue-tracker.md`). These five are **labels**, not workflow
states — applying one does not move the issue across the board.

They do **not** yet exist in the Linear workspace; the defaults were kept because there was
no existing vocabulary to map around. Labels can't be created over the MCP server in every
Linear plan, so create them once in the Linear UI (Settings → Labels), or let `/triage`
create them on first use if your workspace permits it:

| Label | Description |
| --- | --- |
| `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | Fully specified, ready for an AFK agent |
| `ready-for-human` | Requires human implementation |
| `wontfix` | Will not be actioned |

If your team already uses different names, edit the right-hand column in the table above
rather than creating duplicates.
