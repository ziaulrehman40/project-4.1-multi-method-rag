# Reflection

## Stage 0

**Confidence score:** 9/10 for the implemented and automated scope; deployment proof pending.

### What worked

Keeping all provider behavior in `chat.gemini.generate_reply(history)` made the chat views
small and the LLM test deterministic. Owner-scoped lookups are centralized and exercised
against every conversation endpoint, which protects the most important authorization rule.
The server-rendered flow works without JavaScript while HTMX adds an append-in-place chat UX.

### What was notable

The repository already contained an embedding/Qdrant prototype even though Stage 0 forbids
retrieval. Removing it was necessary to make the delivered stage truthful, not merely to
avoid calling it. Postgres.app was installed but stopped, and the required pytest packages
were absent from the venv; both were resolved before the green run.

### What to improve next

Repeat the full browser acceptance path on the HTTPS deployment and save its screenshot.
In Stage 1, introduce retrieval behind the existing seam with its own test-first ingestion
and observability work rather than expanding the Stage 0 views.
