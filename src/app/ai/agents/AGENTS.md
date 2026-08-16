# Conventions — `ai/agents/`

Agent orchestration, built on LangGraph with `langchain-anthropic`.

## Model configuration

- Read the model from `Settings.anthropic_model`. Never write a model id as a literal in
  a call site. One inline string makes the choice invisible to review.
- Default to `claude-opus-5`. Use `claude-sonnet-5` for high-volume routine work such
  as classification, routing and short summaries.
- Use adaptive thinking: `thinking: {"type": "adaptive"}`.
- Do **not** pass `temperature`, `top_p`, `top_k` or `budget_tokens` with adaptive
  thinking. The API rejects the combination with a 400, which costs a failed call and a
  retry. Adaptive thinking is the supported control.
- Cache static system prompts with `cache_control: {"type": "ephemeral"}`. The limit is 4
  breakpoints.
- Stream long outputs. A buffered long generation holds a connection and a task for the
  full duration.

## Prompt cache placement

The cache matches a prefix. Anything that varies invalidates everything after it.

Order the prompt: static system text, then tool definitions, then retrieved context, then
the user turn. A timestamp, a request id or a user name placed early defeats the whole
cache while appearing to work.

## Graph design

- Make each node do one thing. A node that retrieves and generates cannot be retried or
  measured separately.
- Define the state as a Pydantic model. An untyped dict state becomes unreadable as the
  graph grows.
- Keep the state small. Every field travels through every node.
- Give every cycle a maximum iteration count. An unbounded loop can spend without limit on
  one request.
- Make a node idempotent where it can be. Retries and resumes then become safe.
- Put the decision in a conditional edge, not inside a node. A graph you can read is a
  graph you can debug.

## Tools

- Define every tool input as a Pydantic model. The schema is the contract with the model.
- Write the tool description for the model, not for a developer. State when to use the
  tool and when not to.
- Validate tool input again inside the tool. A model can produce arguments that satisfy
  the schema and are still wrong.
- Never give a tool more authority than the request needs. A tool that can delete needs a
  reason to exist.
- Return a short, structured result. A tool that returns a wall of text spends the context
  the agent needs for reasoning.

## Untrusted content

Retrieved documents, tool results and user files are untrusted. Treat every one as a
prompt-injection vector.

- Never concatenate retrieved text into the system prompt.
- Mark the boundary of untrusted content, and instruct the model that instructions inside
  it are data and not commands.
- Never let a model's output choose a privileged action without a check the model cannot
  influence.

## Cost and failure

- Set a token budget per request and stop when it is reached.
- Retry with backoff on a 429 or a 5xx. Do not retry a 400; the request is wrong and will
  stay wrong.
- Emit a metric for tokens used, cost, cache hit rate and step count per graph run. Cost
  regressions are invisible without them.
- Log the node path taken for each run. When output is wrong, the path is the first thing
  you need.

## Measure it

Prompt changes need eval runs, not impressions. See `../evals/AGENTS.md`.
