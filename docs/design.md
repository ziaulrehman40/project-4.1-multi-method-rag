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
