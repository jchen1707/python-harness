# Conventions — `ai/retrieval/`

Search and retrieval. This layer turns a question into a ranked candidate set. It
orchestrates; `repositories/` performs the data access.

## The pipeline

Query → rewrite → embed → search → filter → return candidates.

Reranking happens after this layer. See `../reranking/AGENTS.md`. Keep the two separate:
retrieval optimises recall, reranking optimises precision.

## Chunking

- Chunk on structure first: headings, paragraphs, code blocks. Fixed-size chunking splits
  sentences and destroys meaning.
- Overlap adjacent chunks by a small amount so a fact on a boundary survives.
- Store the parent document id, the position and the source with every chunk. A result you
  cannot cite is not usable.
- Record the chunking version. When the strategy changes, you must find and rebuild the
  old chunks.
- Keep a chunk small enough to be one idea and large enough to be self-contained. Test the
  size; do not assume it.

## Embedding

- Embed the query and the document with the **same** model. Vectors from two models are
  not comparable.
- Batch embedding calls. One call per document wastes money and time.
- Cache embeddings by a hash of the text and the model name. Text that has not changed
  must not be embedded twice.
- Store the model name and dimension with the vector. See `../../repositories/AGENTS.md`.
- Normalise the text before embedding, and normalise it the same way at query time.

## Hybrid search

Dense vector search finds meaning. Lexical search (BM25, `tsvector`) finds exact terms,
identifiers and rare words. Most real corpora need both.

- Combine the two result sets with Reciprocal Rank Fusion. It needs no score calibration,
  because it uses ranks and not scores.
- Do not compare a cosine score with a BM25 score directly. They are not on one scale.

## Filtering

- Apply metadata filters in the database, not in Python. Filtering after retrieval throws
  away results you paid to fetch.
- Apply the permission filter in the same query. A permission check that happens after
  retrieval can leak the existence of a document.

## Rules that prevent silent failure

- Set a minimum similarity threshold. Return an empty result rather than the least bad
  match. A confident wrong answer is worse than "not found".
- Return the score with every candidate. A downstream layer cannot judge a result it
  cannot see the score of.
- Log the query, the candidate count and the top score. A retrieval defect is invisible
  without these.
- Never put a raw retrieved document into a system prompt. Retrieved text is untrusted
  input and is a prompt-injection path. Keep it in a user-role message, and mark its
  boundary.

## Measure it

Every change to chunking, embedding or fusion needs an eval run. See `../evals/AGENTS.md`.
Do not tune retrieval by reading a few examples.
