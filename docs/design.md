# Design

Design decisions, one short section per stage.

## Architecture

```
Browser ──HTTP/HTMX──► Django (templates + views)
                          │
                          ├── django.contrib.auth  (login gate)
                          ├── ORM ──► Postgres (existing DB; pgvector enabled for Stage 1)
                          └── chat.gemini ──► Gemini Flash (one call, no retrieval yet)
```

Retrieval methods (Stages 1–4) will plug in behind the `chat.gemini` seam and a future
`retrieval` package. Stage 0 itself contains no document loading or retrieval code.

## Main Components

- `config/` — Django project (settings via env, urls, wsgi).
- `chat/` — the one app: `Conversation` + `Message` models, CRUD views, templates, Gemini client.
- `chat/gemini.py` — the single seam where the LLM (and later, retrieval) is called. Mockable in tests.

## Data Flow (Stage 0)

1. User logs in (Django auth).
2. User creates/opens a `Conversation`.
3. User posts a message → saved as a `Message(role="user")`.
4. `chat.gemini.generate_reply()` calls the current Gemini Flash model (via the
   `gemini-flash-latest` alias) with the conversation history.
5. Reply saved as `Message(role="assistant")` and rendered (HTMX swaps in the new turn).

## Key Decisions

| Decision | Reason | Alternatives Considered |
|---|---|---|
| Django templates + HTMX, no DRF/SPA | Functional > polished (README); one language; no build step | React SPA + DRF (more moving parts) |
| Django built-in auth, not Supabase Auth | Server-rendered app; one identity system; `@login_required` is enough; guards the public deploy | Supabase Auth (JWT bridging friction) |
| Existing Postgres (with `pgvector`) | Already available; same engine dev→prod; `pgvector` carries into Stage 1 with no migration | Supabase, Render Postgres, SQLite |
| Postgres everywhere via `DATABASE_URL` | One engine dev/test/prod — no SQLite/Postgres drift | SQLite for local (faster but divergent) |
| One `chat.gemini` seam | Later stages plug retrieval in here without touching chat CRUD | Scatter LLM calls across views |

## Security and failure boundaries

- Every chat view requires authentication; every object-level action queries by both ID and owner.
- State-changing endpoints accept POST only and use Django CSRF protection, including HTMX requests.
- Secrets, database URLs, allowed hosts, and trusted origins are environment configuration.
- A user message is persisted before Gemini is called. If Gemini fails, no synthetic assistant
  answer or half-complete user turn is stored; the transaction rolls back and the UI preserves
  the draft for retry.

## Stage 0 deployment shape

The container installs pinned dependencies, collects static files, applies migrations on
startup, and serves Django through Gunicorn. TLS and the managed Postgres service sit at the
hosting platform boundary. WhiteNoise serves versioned static assets inside the container.
The unauthenticated `/health/` endpoint checks live database connectivity for the host.

## Development observability

Console logs cover request lifecycle/timing, authenticated user IDs, conversation CRUD,
message persistence, Gemini model/call timing, and health checks. Logs use counts and IDs;
they deliberately exclude message/response content, API keys, credentials, cookies, and tokens.
`DJANGO_LOG_LEVEL` defaults to `DEBUG` in development and `INFO` in production.

## Stage 1 — Embedding RAG (retrieval)

The `rag` app holds retrieval, kept separate from the `chat` generation seam. Pipeline:
`sample-docs → chunk → embed (gemini-embedding-001, 3072-dim) → pgvector → cosine top-k`.

- **Chunking** (`rag/chunking.py`) — three strategies behind a `chunk(strategy=...)` dispatcher:
  `fixed` (size-blind baseline), `recursive` (separator hierarchy + sentence-aware overlap;
  the default), and `semantic` (sentence-embedding boundary detection). For these markdown
  docs recursive is the sweet spot; semantic isolates specific facts but embeds every
  sentence, so it is not used for automatic ingestion (free-tier quota).
- **Storage** — `DocumentChunk.embedding` is a pgvector `VectorField(3072)`. No ANN index:
  pgvector indexes cap at 2000 dims and the corpus is tiny, so an exact cosine scan is used.
- **Ingestion** (`ingest_docs`) — idempotent, guarded by a hash of content + chunking params
  (so changing strategy/size re-ingests). Runs on container start; no shell needed on Render.
- **Embedding resilience** (`rag/embeddings.py`) — batches (<=32) and retries with backoff;
  holds a strong client reference (a temporary `genai.Client` is GC'd mid-request).
- **Hybrid search** (`rag/retrieval.py`) — `dense_search` (pgvector cosine) + `sparse_search`
  (Postgres full-text on a `search_vector` column, populated at ingest) fused by Reciprocal
  Rank Fusion (`_rrf`, rank-based so the two score scales don't need normalising). Dense
  handles meaning, sparse handles exact terms/IDs. Note: the sparse ranker is Postgres's
  built-in full-text rank (TF-IDF-family), not literal BM25 — sufficient because RRF only
  uses rank order. `search(method="dense"|"sparse"|"hybrid")` dispatches.
- **Reranking** (`rag/reranking.py`) — a precision pass over the retrieved pool: an
  LLM-as-reranker (Gemini) scores each candidate's relevance to the query 0–10 in one call,
  reorders, and keeps top-n. Chosen over a dedicated cross-encoder to avoid heavy deps on the
  free tier / Render. Fallback is explicit, not silent: on failure it logs a warning and
  returns retrieval order with `reranked=False` (a `RerankOutcome`) so the caller/UI can flag it.
- **Answer + citations** (`rag/answer.py`) — `answer(question, rerank_enabled=True)` runs hybrid
  retrieve → optional rerank → a grounded, numbered prompt → Gemini answer with inline `[n]`
  citations. Returns a JSON dict (answer, sources, `rerank_status`, metrics:
  tokens/latency/est. cost/embedding dim) stored on the chat `Message`. `rerank_status` is
  `applied` / `failed` (non-silent fallback) / `off` (rerank skipped to save quota). Retrieval
  uses only the latest question (Stage 1 scope).
- **Transparency UI** — integrated into the chat, not a separate page. A per-message technique
  selector (`plain` / `embedding`) plus a rerank checkbox route generation in
  `chat.views.message_create`; assistant messages persist `technique` + `metadata`, and
  `_message.html` renders a collapsible panel (sources with scores/method, tokens, cost,
  latency, embedding dim; a warning when reranking failed, a note when it was off). The
  dedicated per-technique query + 4-way comparison page is Stage 5.
- **Model config** — the generation model is centralised in `settings.GEMINI_MODEL`
  (env `GEMINI_MODEL`, default `gemini-2.5-flash-lite` for its more generous free-tier daily
  quota). Chat, rerank, and answers all read it; embeddings use `gemini-embedding-001`.

## Stage 2 — Knowledge-Graph RAG (extraction + graph)

The `kg` app builds a graph of facts instead of matching by vector similarity.

- **Extraction** (`kg/extraction.py`) — `extract_triples(text, source)` prompts Gemini for
  `(subject, predicate, object, section)` triples as JSON, guarded against hallucination
  ("only facts stated in the text") and fragmentation ("reuse identical phrasing"). Light
  canonicalisation (lowercase/whitespace). Per-document by default (few LLM calls) but works
  per-chunk too. Retries transient 503/429 with backoff.
- **Graph model** (`kg/models.py`) — `Entity` (unique canonical name = node), `Relationship`
  (subject/predicate/object edge with `source`+`section` provenance, unique per source),
  `GraphSource` (content+model hash for idempotent rebuilds). Stored in plain Postgres tables;
  traversal will use recursive CTEs (no graph extension, portable across PG versions).
- **Build** (`kg/graph.py` + `build_graph` command) — extract → upsert entities (exact-canonical
  entity resolution via `get_or_create`) → create edges → prune orphaned entities. Idempotent,
  hash-guarded like `ingest_docs`.
- **Retrieval** (`kg/retrieval.py`) — lightweight local search: each edge is embedded as a
  sentence at build time (`Relationship.embedding`, reusing `rag.embeddings`); `graph_search`
  finds the top seed edges by cosine similarity to the question, then traverses `hops` steps to
  gather the connected subgraph (capped at `max_edges`).
- **Answer + trace** (`kg/answer.py`) — presents the subgraph edges as numbered facts with
  `source`/`section`, Gemini answers citing `[n]`, and the returned `trace` is the exact edges
  used (nodes + predicate + provenance) — graph RAG's auditability edge. `graph_query` command
  exposes it from the CLI. Retries transient 503/429.
- **Pending in Stage 2:** interactive graph visual wired into the chat technique selector.
