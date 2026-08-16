---
name: full-review
description: Fan out one diff to nine independent review agents, then consolidate their findings into one ranked report. Use for broad branch or pull-request reviews that need standards, specification, security, tests, async, simplicity, design, performance, and cost coverage.
---

# Full review

Review one diff on nine independent axes. Keep review and consolidation in separate contexts.

## Select the diff

Use the base from `$ARGUMENTS` when present. Otherwise, use `REVIEW_BASE`, then `main`.

Use the same `git diff <base>...HEAD` range for every reviewer. Report the range in the final output.

Stop when the base does not resolve. Ask the user for the correct base.

## Fan out

Spawn one read-only subagent for each row.

| Axis | Agent |
| --- | --- |
| Standards | `standards-reviewer` |
| Specification | `spec-checker` |
| Security | `security-reviewer` |
| Tests | `test-reviewer` |
| Async | `async-reviewer` |
| Simplicity | `simplicity-reviewer` |
| Design | `design-reviewer` |
| Performance | `perf-reviewer` |
| Cost | `cost-reviewer` |

Tell each agent to read its matching file under `.agents/agents/`. That file owns the review rules.

Give each agent the diff range. Do not give `spec-checker` a ticket summary.

Tell each agent to return only real defects. An empty result is valid.

Use this result shape:

```json
{
  "findings": [
    {
      "file": "path/to/file.py",
      "line": 12,
      "severity": "high",
      "summary": "One sentence.",
      "why_it_matters": "One sentence."
    }
  ]
}
```

Allow only `critical`, `high`, `medium`, or `low` severity.

Start all agents concurrently when capacity permits. If capacity is full, start the remaining agents when a slot opens.

Wait for every agent. Do not consolidate partial results.

If an agent fails, retry it once. Report the missing axis when the retry fails.

## Fan in

Start a fresh synthesis agent after all reviewers finish. Give it only the reviewer results and axis labels.

Tell the synthesis agent to perform these actions:

1. Merge findings that describe the same defect.
2. Keep the clearest wording from duplicate findings.
3. Record every axis that reported each merged finding.
4. Remove style findings already enforced by Ruff or mypy.
5. Rank findings by severity, then by reviewer agreement.
6. Give the smallest safe fix for each finding.
7. Add no new findings.

The synthesis agent must not inspect the diff. Use the primary agent only when a fresh agent is unavailable.

## Report

Return `No findings` when every completed axis returns an empty list.

Otherwise, report each finding with these fields:

- Severity
- File and line
- Defect
- Impact
- Smallest fix
- Agreeing axes

End with the reviewed range and completed axes. List any axis that failed after its retry.
