# Conventions — `ai/reranking/`

Reranking reorders a candidate set for precision. Retrieval gives recall; this layer
decides what reaches the model or the user.

## Why it is separate

A retriever is fast and approximate, so it can search a large corpus. A reranker is slow
and accurate, so it can only look at a few candidates. Keeping them apart lets you
retrieve wide and rerank narrow.

## Rules

- Rerank a shortlist, not the corpus. Retrieve `k` candidates and rerank them, where `k`
  is a few tens. Reranking hundreds of candidates costs more than the precision it buys.
- A cross-encoder reads the query and the document together, which is why it is more
  accurate than a bi-encoder and why it cannot be pre-computed. Expect the latency.
- Always keep the retrieval order as a fallback. If the reranker fails or times out,
  return the retrieved order. Never fail the request because reranking failed.
- Set a timeout on the reranker. It is on the request path.
- Return both scores: the retrieval score and the rerank score. You cannot diagnose a bad
  result from one number.
- Truncate a document to the reranker's input limit deliberately. Silent truncation drops
  the end of every long document, which is often where the answer is.

## Choosing a strategy

| Situation | Use |
| --- | --- |
| Small shortlist, precision matters | Cross-encoder reranker |
| Several retrievers to combine | Reciprocal Rank Fusion, then rerank |
| Freshness or authority matters | Score blend, with the weights written down |
| Latency budget is very tight | No reranker; tune retrieval instead |

Write down the weights of any score blend, and the reason for each. An unexplained
weighted sum becomes impossible to change safely.

## Diversity

When results are near-duplicates, the top of the list wastes the model's context on one
fact. Apply Maximal Marginal Relevance, or deduplicate by document id, before returning.

## Measure it

A reranker that is not measured is a guess. Track nDCG and MRR against a labelled set
before and after any change. See `../evals/CLAUDE.md`.
