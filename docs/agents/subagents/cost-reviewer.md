# Cost checklist — python-harness

The stack half of the shared `cost-reviewer` frame. The frame carries the discipline — name
the call volume, judge only avoidable spend; this is what the defaults are here.

**`src/app/ai/agents/CLAUDE.md` is the authority.** Read it; this is the summary.

- **Default model is `claude-opus-5`**; `claude-sonnet-5` is for high-volume routine work.
  Opus on a classifier, a router, a summariser or a retry path is spend with no gain.
- **Model ids come from `Settings.anthropic_model`**, never inline as strings, so the choice
  stays reviewable in one place.
- **Adaptive thinking** (`thinking: {"type": "adaptive"}`) is the supported control. Passing
  `temperature`, `top_p`, `top_k` or `budget_tokens` alongside it returns 400 — a failed call
  that costs latency and retried spend.
- **Unbounded LangGraph cycles.** A cycle with no iteration cap can spend without limit on a
  single request.
- **Re-embedding unchanged content.** Embeddings are stable for stable text; re-embedding on
  every ingest run, or per-document calls where the API takes a batch, is direct waste.
- **`top-k` set well above what the prompt actually uses**, and whole documents passed where
  retrieved chunks would do.
- **Missing streaming on long outputs.** Not a token cost, but it holds a connection and a
  task for the full generation, and `CLAUDE.md` requires it.

The client-side half of the shared frame — over-fetching, refetch churn, N+1 requests — has no
equivalent here. There is no browser. Skip it rather than inventing an analogue.
