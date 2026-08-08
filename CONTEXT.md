# Support Document Search

The domain glossary for this repo. It fixes the words we use for searching internal
support documents and returning cited passages.

Started during `/grill-with-docs` on BAC-2. Add a term when a discussion resolves one.

## Language

### The corpus

**Document**:
One uploaded PDF file, with its pages and its visibility. The unit a citation names.
_Avoid_: File, article, doc, source document

**Page**:
One page of a document. The unit a citation points to.

**Chunk**:
A span of about 200 words inside a single page. The unit we embed and store. A chunk
never crosses a page boundary.
_Avoid_: Segment, block, window, split

**Visibility**:
Whether a document may reach a customer. It is `internal` or `external`. A property of
the document, set when the document is uploaded.
_Avoid_: Access level, permission, sensitivity, classification

**Corpus**:
The whole set of indexed documents.
_Avoid_: Knowledge base, index, library

### Searching

**Query**:
The question text a support agent sends.
_Avoid_: Search term, prompt, question

**Passage**:
A chunk returned to the agent, with its file name, page number and score. The product
returns passages.
_Avoid_: Snippet, excerpt, result text, extract

**Answer**:
Prose written by a model that responds to a query. **This system never produces one.**
The term is defined here only to keep it separate from a passage. A support agent writes
the customer reply themselves, from the passages.

**Citation**:
The file name and page number attached to a passage, so a human can verify it in the
original PDF.
_Avoid_: Reference, link, source link

**Support agent**:
A member of the Support team who queries the corpus. The only user of this system.
_Avoid_: User, operator, agent

> **Note on "agent".** Unqualified, "agent" in this repo's workflow docs means a Claude
> Code dev-workflow subagent. Say **support agent** for the human, and **application
> agent** for a LangGraph agent under `src/app/ai/agents/`. See `docs/agents/domain.md`.

### Measuring

**Gold set**:
The fixed list of queries, each paired with the one document that answers it. It defines
what a correct result is.
_Avoid_: Test set, eval set, ground truth, benchmark

**Recall@5**:
The share of gold-set queries whose correct document appears in the top five passages.
The single quality number for this system.
