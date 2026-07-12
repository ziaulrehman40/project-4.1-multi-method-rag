# Test Plan

## Stage 0 objective and scope

Confirm the authentication gate, owner isolation, complete conversation lifecycle,
persisted chronological history, and the single mockable Gemini call. Retrieval and real
Gemini network behavior are deliberately excluded from automated tests.

## Test environment

- Python 3.14.5, Django 6.0.7, pytest 9.1.1, pytest-django 4.12.0.
- HTMX 2.0.10 and google-genai 2.11.0 (latest stable releases verified 2026-07-11).
- Local Postgres.app database; pytest creates and drops its isolated test database.
- `chat.gemini.generate_reply` is replaced with a `Mock` for message submission.

## Automated test cases

| ID | Description | Expected result | Status |
|---|---|---|---|
| M-01 | Create conversation with defaults | Owner, default title, and timestamps are set | Pass |
| M-02 | Create two messages | Related messages read in creation order | Pass |
| M-03 | Delete conversation | Related messages cascade-delete | Pass |
| V-01 | Anonymous list request | Redirects to `/login/?next=/` | Pass |
| V-02 | Create conversation | Owned record is created and detail redirect returned | Pass |
| V-03 | Load detail history | Each persisted user and assistant message is rendered exactly once | Pass |
| V-04 | Submit a message | Both roles persist; mock called once with full history | Pass |
| V-05 | Rename conversation | Title changes | Pass |
| V-06 | Delete conversation | Record disappears and no longer renders in list | Pass |
| V-07 | Access another owner's conversation | Detail/message/rename/delete each return 404 | Pass (4 cases) |
| V-08 | Access every chat route anonymously | Each route redirects to login before object handling | Pass (6 cases) |
| V-09 | Submit via HTMX | Partial contains both messages and no page wrapper | Pass |
| V-10 | Gemini provider fails | Turn rolls back, draft survives, and UI returns 502 | Pass |
| G-01 | Map history at provider seam | Roles map to Gemini roles and exactly one SDK call occurs | Pass |
| G-02 | Gemini returns no text | Seam raises an explicit error | Pass |
| G-03 | Gemini SDK call fails | Seam wraps the provider error for safe view handling | Pass |
| H-01 | Request `/health/` anonymously | Endpoint executes a DB query and returns healthy JSON | Pass |
| L-01 | Complete an HTTP request | Safe method/path/user/status/timing metadata is logged | Pass |
| L-02 | Raise an unhandled request error | Exception metadata and traceback are logged | Pass |
| L-03 | Complete a Gemini call | Model/count/timing metadata is logged without content or keys | Pass |

Run: `.venv/bin/python -m pytest -q` with the Stage 0 environment configured.
Initial Stage 0 result: **13 passed**. Post-audit result: **32 passed**, including
all-route authentication, HTMX partials, full-history payloads, provider mapping/failure
atomicity, blank input, and database health.

## Manual acceptance and known gaps

Required click path: anonymous gate → login → create → chat → reload/history → rename →
delete, plus a second-user ownership URL. The local database and server are prepared, but
the automated environment exposed no controllable browser, so visual click-through remains
to be repeated on the deployed host. The live HTTPS smoke test and screenshot also require
the selected host account. Django's production check intentionally retains HSTS subdomain
and preload advisories: enabling either is unsafe until a real domain and all of its
subdomains are under this deployment's HTTPS control.

## Stage 1 — Embedding RAG

Retrieval is tested with the embedding API mocked, so tests are deterministic and offline.

| ID | Description | Expected result | Status |
|---|---|---|---|
| CK-01 | Fixed chunks bounded by max_chars | Every chunk within the size limit | Pass |
| CK-02 | Recursive packs a bare heading with its content | No tiny heading-only chunk | Pass |
| CK-03 | Recursive overlap is sentence-aware | Each later chunk starts at a sentence boundary | Pass |
| CK-04 | Semantic cuts at a topic shift | Groups split where meaning changes | Pass |
| CK-05 | Dispatcher routing / bad-strategy errors | Correct strategy chosen; errors raised | Pass |
| IN-01 | Ingest creates chunks with 3072-dim embeddings | Chunks stored with vectors | Pass |
| IN-02 | Ingest idempotent on unchanged docs | Second run re-embeds nothing | Pass |
| IN-03 | Changing strategy re-ingests | Different chunking config forces re-embed | Pass |
| EM-01 | Large input split into batches (<=32) | Correct batch sizes, order preserved | Pass |
| EM-02 | Transient embedding error retried / gives up | Retries then succeeds; raises after max | Pass |
| RT-01 | Dense retrieval returns nearest chunk first | Ordered by cosine distance; respects k | Pass |
| RT-02 | Sparse retrieval finds keyword match; no fuzzy match | Keyword chunk first; unrelated query returns none | Pass |
| RT-03 | RRF fuses two ranked lists by rank | Lesson example fuses to A, C, B, D with expected scores | Pass |
| RT-04 | Hybrid merges dense + sparse | Both methods' chunks present, ordered by fused score | Pass |
| IN-04 | Ingest populates full-text search_vector | Every chunk has a non-null search_vector | Pass |
| RR-01 | Rerank reorders by score and keeps top-n | Candidates ordered by LLM score; top-n returned | Pass |
| RR-02 | Rerank fallback is not silent | On failure: retrieval order, reranked=False, warning logged | Pass |
| RR-03 | Rerank handles empty input | Returns empty, reranked=True | Pass |
| AN-01 | answer() builds cited result + metrics | Numbered sources, inline citations, token/latency/cost/dim | Pass |
| AN-02 | answer() propagates reranked=False | Falls back to retrieval score/method | Pass |
| AN-03 | answer() raises on generation failure | AnswerError raised (view rolls back) | Pass |
| CH-01 | Embedding technique routes to RAG + stores metadata | Assistant message technique=embedding, metadata persisted, latest question only | Pass |
| CH-02 | Plain technique does not call RAG | Plain path used; RAG not invoked | Pass |
