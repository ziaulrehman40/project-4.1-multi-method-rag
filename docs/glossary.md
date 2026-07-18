# Glossary

Plain-language definitions of terms used across this project.

## Core RAG

- **RAG (Retrieval-Augmented Generation)** — find relevant source text first, then have an
  LLM generate an answer grounded in it. Retrieval finds; generation composes.
- **Chunk** — a slice of a document that is embedded and retrieved as one unit.
- **Chunking strategy** — how you cut documents into chunks: *fixed* (by size), *recursive*
  (by structure: paragraph → line → sentence), *semantic* (by meaning shifts).
- **Overlap** — repeating a bit of the previous chunk at the start of the next, so meaning
  that straddles a boundary isn't lost.
- **Embedding** — a fixed-length list of numbers (a vector) representing a piece of text or
  an image, arranged so that similar meaning lands close together.
- **Vector** — the list of numbers an embedding produces (e.g. 3072 numbers).
- **Dense vector** — an embedding: almost every number is non-zero (meaning, packed).
- **Sparse vector** — a keyword representation: mostly zeros, non-zero only for words present.
- **Cosine similarity / distance** — how close two vectors point; the standard "how similar"
  measure. Small distance = similar.
- **Vector store** — a database that indexes vectors for nearest-neighbour search (we use
  pgvector, the Postgres extension).
- **Top-k** — keep the k best-scoring results.
- **Provenance** — where a piece of retrieved content came from (document, section, page) —
  used for citations.
- **Idempotent** — safe to run repeatedly with the same result; our build commands skip work
  when inputs are unchanged (via a content hash).

## Retrieval methods

- **Hybrid search** — combine dense (semantic) and sparse (keyword) retrieval.
- **BM25** — a classic keyword ranking formula (keyword frequency weighted by rarity).
- **RRF (Reciprocal Rank Fusion)** — merge two ranked lists using each item's *rank*
  (score = sum of 1/(k+rank)), so score scales don't need to match.
- **Reranking** — a second, more precise pass that re-scores retrieved candidates (here, an
  LLM scores each candidate's relevance) and reorders them.
- **Knowledge graph** — facts stored as nodes (entities) and edges (relationships).
- **Triple** — one fact as (subject, predicate, object), e.g. (breach, reported to, authority).
- **Entity / node** — a "thing" in the graph. **Relationship / edge** — a link between two.
- **Entity resolution** — collapsing different wordings of the same thing to one node.
- **Hop** — one step along a graph edge. **Traversal** — walking the graph.
- **Vectorless RAG** — retrieval by LLM *reasoning* over a document's structure (its section
  tree), with no embeddings or chunking.
- **Document tree** — the section hierarchy of a document (root → headings → subheadings).
- **Adjacency list** — the standard way to store a tree in a relational DB: each row has a
  `parent` pointing at another row.

## Multimodal / PDF parsing

- **Multimodal** — handling more than text (here: tables, images, equations).
- **Cross-modal retrieval** — a text query matching an image (possible because
  `gemini-embedding-2` puts text and images in the *same* vector space).
- **Prose** — ordinary running paragraph text, as opposed to a table or a figure. In parsing
  we separate "prose" from "tables" and "images".
- **bbox (bounding box)** — the rectangle `(x0, y0, x1, y1)` giving a block's position on the
  page. We use table bboxes to *subtract* table regions from the prose.
- **Block** — a unit PyMuPDF returns from a page: a text block (type 0) or an image block
  (type 1), each with a bbox.
- **`find_tables()`** — PyMuPDF's table detector; we render detected tables to markdown to
  preserve exact rows/columns.
- **Figure** — a chart, heatmap, or equation image extracted from the PDF.
- **Caption / context** — the section heading + nearby text a figure sits under, captured so
  the figure has meaning and a citation.
- **base64** — a way to encode binary (an image) as text, so we can store a figure in the DB
  and show it in HTML via a `data:` URI without a separate file server.

## Models / infra

- **pgvector** — Postgres extension adding a `vector` column type + similarity search.
- **gemini-embedding-001** — text-only embedding model (Stages 1–3).
- **gemini-embedding-2** — multimodal embedding model: embeds text *and* images (Stage 4).
- **HTMX** — a small library that lets HTML swap in server responses without a full reload
  (our chat updates use it).
