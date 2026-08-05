import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const meta = {
  name: 'full-review',
  description:
    'Fan out a diff to independent reviewers (standards, spec, security, tests, async, simplicity), then fan in to one deduplicated ranked report.',
}

// Fan-in at a barrier: every axis reviews the SAME diff in its own context, then a
// single synthesiser reconciles them. The synthesiser never reviews the code itself —
// it only judges and merges what came back. Keeping those jobs apart is the point;
// a reviewer that also ranks tends to rank its own findings first.

const BASE = process.env.REVIEW_BASE || 'main'

// Two axes also exist as standalone subagents in `.claude/agents/`. Those definitions
// are the single source of truth — this workflow reads their bodies rather than
// restating them, so `/security-reviewer` and the `security` axis cannot drift apart.
// Resolved relative to this file, not the cwd, so it holds wherever the runner starts.
const AGENT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'agents')

/**
 * Body of a subagent definition, with its YAML frontmatter stripped.
 *
 * Falls back to a one-line brief if the definition is missing or unreadable — a deleted
 * agent file should degrade this axis, not take down the whole review.
 */
function agentPrompt(name, fallback) {
  try {
    const raw = readFileSync(join(AGENT_DIR, `${name}.md`), 'utf8')
    const body = raw.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '').trim()
    return body || fallback
  } catch {
    return fallback
  }
}

const AXES = [
  {
    label: 'standards',
    prompt: `Review the diff against this repo's documented standards in docs/architecture.md and CLAUDE.md. Layering (api -> services -> repositories -> config, no reverse deps), interfaces over concrete deps, Pydantic for all I/O, secrets only in app.config.Settings, structlog never print(), types on every public function. Report violations only.`,
  },
  {
    label: 'spec',
    // Shared with the `spec-checker` subagent. It expects the caller to name the diff
    // range and the spec source, so both are supplied below.
    prompt:
      agentPrompt(
        'spec-checker',
        `Check the diff against the acceptance criteria of its originating ticket. Report unmet or partially met criteria, and anything implemented that was never asked for.`,
      ) +
      `\n\n---\n\nThe diff range is \`${BASE}...HEAD\`. Resolve the spec source yourself: ` +
      `take the Linear ticket id from the branch name or commit trailers and fetch the ` +
      `ticket, per docs/agents/issue-tracker.md. Do not accept a summary of the ticket ` +
      `from anyone — read it from the tracker, so the criteria you check against are the ` +
      `ones actually filed. If no ticket resolves, report "no spec available" and stop.`,
  },
  {
    label: 'security',
    // Shared with the `security-reviewer` subagent.
    prompt:
      agentPrompt(
        'security-reviewer',
        `Security pass over the diff: secrets outside Settings, injection (SQL, command, prompt), unvalidated input bypassing Pydantic, missing authz, unsafe deserialization, missing timeouts on outbound httpx. Only reachable issues. Give the attack path for each.`,
      ) + `\n\n---\n\nThe diff range is \`${BASE}...HEAD\`.`,
  },
  {
    label: 'tests',
    prompt: `Does the diff have tests that would fail if the behaviour regressed? Flag: new behaviour with no test, tests asserting on internals rather than seams, tautological tests that recompute the expected value the way the code does, and tests that need network or a DB but are not marked integration.`,
  },
  {
    label: 'async',
    prompt: `Check the sync/async boundary per CLAUDE.md: blocking calls on the event loop, fake-async (async def that never awaits), missing asyncio.to_thread around blocking I/O, unbounded concurrency with no semaphore, per-call client construction instead of a pooled one, and un-awaited coroutines.`,
  },
  {
    label: 'simplicity',
    prompt: `Is anything more complicated than the problem requires? Speculative abstraction, an interface with one implementation and no test double, duplicated logic that wants extracting, dead code. Do NOT propose architecture rewrites — only cuts that make the diff smaller while keeping behaviour.`,
  },
]

const FINDING_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'summary', 'severity'],
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          summary: { type: 'string' },
          why_it_matters: { type: 'string' },
        },
      },
    },
  },
}

const reviews = await pipeline(AXES, (axis) =>
  agent(
    `Review \`git diff ${BASE}...HEAD\` in this repo.\n\n${axis.prompt}\n\n` +
      `Report only real problems. An empty findings array is a valid, useful result — ` +
      `do not manufacture findings to look thorough.`,
    { label: axis.label, schema: FINDING_SCHEMA },
  ),
)

const all = AXES.flatMap((axis, i) =>
  (reviews[i]?.findings ?? []).map((f) => ({ ...f, axis: axis.label })),
)

if (all.length === 0) {
  return `No findings across ${AXES.length} axes for ${BASE}...HEAD.`
}

return await agent(
  `Below are findings from ${AXES.length} independent reviewers of the same diff. ` +
    `Produce ONE report:\n` +
    `1. Merge duplicates — the same defect found by several axes is one finding; keep the clearest wording and note which axes agreed (agreement raises confidence).\n` +
    `2. Drop anything that is a style preference already enforced by ruff or mypy.\n` +
    `3. Rank by severity, then by how many axes independently found it.\n` +
    `4. For each: file:line, one-sentence defect, why it matters, and the smallest fix.\n\n` +
    `Do not add findings of your own — you have not read the diff.\n\n` +
    JSON.stringify(all, null, 2),
  { label: 'synthesise' },
)
