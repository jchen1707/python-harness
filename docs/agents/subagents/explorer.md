# Codebase map — python-harness

The stack half of the shared `explorer` frame. The frame carries the method and the output
shape; this is where to look and what the same idea is called here.

A single Python package, not a monorepo. The multi-context `CONTEXT-MAP.md` layout does not
apply.

```
src/app/
├── api/            ← routes; the outermost layer
├── services/       ← orchestration; calls into ai/ and repositories/
├── ai/             ← retrieval, reranking, agents, evals (each with its own CLAUDE.md)
├── repositories/   ← the protocols — Embedder, VectorStore, Tool — and their implementations
└── config/         ← Settings; the only place the environment is read
tests/              ← offline unit tests
tests/integration/  ← testcontainers, marked `integration`
docs/architecture.md ← standards and the architectural decision record
docs/agents/        ← the stack half of layer A, including this file
```

Every layer directory carries its own `CLAUDE.md`. Those are path-scoped: reading one tells
you the conventions for that layer and nothing else.

## Synonyms to try before reporting nothing

- A **retrieval** thing may be `retriever`, `search`, `vector`, `embedding` or `chunk`.
- A **model call** may be `anthropic`, `llm`, `chat`, `agent` or `graph`.
- A **protocol** may be the name itself (`Embedder`) or the concrete implementation
  (`OpenAIEmbedder`, `FakeEmbedder`).
- **Config** is `Settings`, not `config` or `env`.

## Prefer the language server

`pyright` is available as an MCP server, and `CLAUDE.md` has a section on preferring it over
grep. `findReferences` distinguishes a call from a mention in a comment or a docstring; grep
does not.

A confident "nowhere" is the most expensive answer you can give. Say which names you tried.
