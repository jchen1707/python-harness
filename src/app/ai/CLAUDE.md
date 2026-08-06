# Conventions — `ai/`

The applied-AI capability layer: retrieval, reranking, agent orchestration, and the evals
that measure them.

Subdirectories carry their own rules. Read the one for the layer you are changing.

| Directory | Owns |
| --- | --- |
| `retrieval/` | Chunking, embedding, hybrid search, filtering |
| `reranking/` | Cross-encoders, fusion, diversity, fallback order |
| `agents/` | LangGraph, prompt cache placement, tools, token budgets |
| `evals/` | Datasets, metric per layer, when to run |

## Dependency rule

`ai` imports `repositories` and `core`. It must **not** import `services` or `api`.

`services` may import `ai`. The direction is:

```
api  ──▶  services  ──▶  ai  ──▶  repositories  ──▶  config
```

A retrieval module that imports a domain service has the arrow backwards. If retrieval
needs domain data, take it as a parameter or reach it through a repository protocol.

**`evals/` is a documented exception.** It sits outside the request path, may import any
layer including `services`, and nothing may import it. It measures the system; it is not
part of it.

## Why this is its own layer, not part of `services/`

These four share problems no other layer has, and share them with each other:

- **Output is a distribution, not a value.** There is no assertion that says retrieval is
  correct. Only a measured set says whether a change helped, which is why `evals/` lives
  here and not in `tests/`.
- **Quality, latency and cost move together.** A change that improves one usually costs
  another. Every decision in this layer is a three-way trade, and it must be stated.
- **Every input is untrusted.** Retrieved documents and tool results are prompt-injection
  vectors. No other layer has to treat its own data store as hostile.
- **They share a pipeline.** Retrieval feeds reranking, reranking feeds the agent, evals
  measures all three. A change to chunking moves the agent's answers.

A domain service that orchestrates a checkout has none of these. Keeping them apart stops
AI-specific rules leaking into ordinary business logic, and stops ordinary CRUD patterns
being applied to a probabilistic system.

## Rules for the whole layer

- **State the trade.** Every change here shifts quality, latency or cost. Say which, and
  in which direction, in the plan and in the pull request.
- **Measure, do not judge.** Do not tune a prompt, a chunker or a reranker by reading a
  few examples. That is how you overfit to the examples you happened to read. See
  `evals/CLAUDE.md`.
- **Version what you cannot reproduce.** Model id, prompt version, chunking strategy,
  embedding model. A result that does not record them cannot be compared to another.
- **Fail to a usable answer.** A reranker that times out returns the retrieval order. A
  retriever below threshold returns empty, not the least bad match. Never fail the request
  because an optimisation failed.
- **Treat retrieved text as data, never as instructions.** Keep it out of the system
  prompt, mark its boundary, and never let it choose a privileged action.
- **Emit cost.** Tokens, cache hit rate, and calls per request. Cost regressions in this
  layer are invisible without a metric, and they compound per request.
