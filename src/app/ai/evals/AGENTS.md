# Conventions — `ai/evals/`

Offline measurement of AI behaviour. An eval answers "did this change make the system
better?" A test answers "does this code still work?" They are different, and they do not
replace each other.

## Dependency rule

`evals` may import **any** layer — `ai`, `services`, `repositories`, `core`. Nothing
imports `evals`.

This is the one documented exception to the dependency direction in `../AGENTS.md`. It
holds because `evals` is not on the request path: it measures the system from outside, so
it cannot create a cycle at runtime. No runtime code may depend on it.

## Why evals exist here

Retrieval, reranking and prompts have no correct output that a unit test can assert. They
have a *distribution* of better and worse outputs. Only a measured set tells you which
direction a change moved.

Do not tune a prompt or a retriever by reading a few examples. It is the fastest way to
overfit to the examples you happened to read.

## The dataset

- Keep the dataset in version control beside the code it measures. An eval you cannot
  reproduce is an anecdote.
- Write the expected output by hand, or review every generated label. An unreviewed
  synthetic set measures the generator, not the system.
- Include the failures you have already fixed. An eval set is a regression suite for
  behaviour.
- Include hard negatives: near-miss documents that must **not** be retrieved. A set with
  only positives cannot detect a retriever that returns everything.
- Keep a held-out split you do not look at while tuning.

## Metrics

Choose the metric for the layer under test. Do not report a single overall score.

| Layer | Metric |
| --- | --- |
| Retrieval | Recall@k, MRR — did the right document arrive at all? |
| Reranking | nDCG@k, MRR — is the right document near the top? |
| Generation | Faithfulness to the retrieved context, answer relevance |
| End to end | Task success rate, plus cost and latency per request |

Always report cost and latency next to quality. A change that improves accuracy by one
point and triples the bill is a decision, not an improvement.

## Rules

- Fix the seed and record the model id, the prompt version and the dataset version with
  every result. A result without them cannot be compared to another.
- Compare against the previous run, not against an absolute target. The question is
  whether the change helped.
- Report the distribution, not just the mean. A mean hides a change that helps most cases
  and breaks a few badly.
- An LLM-as-judge is itself a system under test. Calibrate it against human labels before
  you trust it, and pin its model version.
- Evals cost money and take time. Mark them `integration` so the default `uv run pytest`
  stays offline and fast.

## When to run

Run the eval set before merging any change to chunking, embedding, retrieval, reranking,
tool definitions or a prompt. Put the before-and-after numbers in the pull request.
