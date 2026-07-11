# Requirements

## Stage 0 — App Skeleton and Chat

### Problem and user

The learning project needs a durable, authenticated chat foundation before retrieval
methods are introduced. A learner must be able to demonstrate a normal compliance-themed
chatbot, inspect persisted history, and later replace the generation seam without rewriting
conversation management.

### Functional scope

- A user can log in and log out using Django authentication.
- An authenticated user can create, list, open, rename, and delete conversations.
- User and assistant messages persist in chronological order in Postgres.
- Each submitted user message produces exactly one call to Gemini Flash through
  `chat.gemini.generate_reply(history)`.
- All conversation lookups are scoped to the authenticated owner and return 404 to other users.
- HTMX progressively enhances message submission; ordinary form POST and redirects still work.

### Quality and operational requirements

- Django 6.0 templates + HTMX; no DRF, SPA, streaming, or WebSockets.
- Configuration and secrets come from environment variables (`.env`/`.env.local` in development).
- Postgres is used in development, tests, and production.
- Gemini is mocked in automated tests; tests never make external LLM calls.
- Gunicorn and WhiteNoise support container deployment over HTTPS at the hosting layer.

### Explicitly out of scope

Retrieval, sample-document ingestion, embeddings, chunking, vector search, citations, and
retrieval observability are Stage 1 or later. The old embedding prototype was removed so
Stage 0 contains no hidden retrieval path. The pgvector extension is enabled locally only
as database readiness for Stage 1 and is not referenced by application code.

### Definition of done

- [x] Login-gated conversation CRUD and persisted message history.
- [x] Owner scoping and 404 behavior.
- [x] One plain Gemini Flash call per submitted message through one seam.
- [x] Test-first suite passes against Postgres with a mocked LLM.
- [x] Container/deployment configuration is present.
- [ ] Live HTTPS deployment verified and URL/screenshot saved in `proof/` (requires host account).

### Plan deviation

The detailed plan names `gemini-2.5-flash`, but on 2026-07-11 the Gemini API returned
404 and said that model was unavailable to new users. The README's provider requirement
is the higher-priority, model-family-level baseline, so the implementation uses Google's
`gemini-flash-latest` alias. The single-call behavior and provider seam are unchanged.
