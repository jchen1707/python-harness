"""Reranking — reorders a candidate set for precision.

Runs after `ai/retrieval/`. Always keeps the retrieval order as a fallback: a reranker
that fails or times out must not fail the request.

Conventions: reranking/CLAUDE.md.
"""
