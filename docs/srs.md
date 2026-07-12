# Software Requirements Specification (SRS)

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for **Multi Method RAG**, a learning application
that answers questions over a fixed set of compliance documents using four different
retrieval techniques and lets them be compared side by side. It is for the builder and
the reviewing mentor.

### 1.2 Scope
The product is a single deployed web application with an authenticated, compliance-themed
chatbot and four pluggable retrieval methods over the same documents: embedding-based RAG,
knowledge-graph RAG, vectorless (reasoning-based) RAG, and multimodal RAG. It exposes each
method transparently (retrieved evidence, scores, tokens, cost, latency), a dedicated query
page, a four-way comparison view, and an evaluation harness scoring retrieval and answer
quality against a small gold Q&A set. It is built in sequenced stages, each deployed and
kept live.

### 1.3 Definitions and Terms
- **RAG** — Retrieval-Augmented Generation: retrieve relevant source text, then generate a
  grounded answer with an LLM.
- **Chunk** — a slice of a document that is embedded and retrieved as a unit.
- **Embedding** — a vector representation of text used for similarity search.
- **Vector store** — a database that indexes embeddings for nearest-neighbour search (pgvector).
- **Reranker** — a second-pass model that reorders retrieved candidates by relevance.
- **Citation** — a reference from an answer back to the source chunk/section it came from.
- **Vectorless RAG** — retrieval by LLM navigation of a document tree, no embeddings/chunking.
- **Evaluation set** — gold questions with known answers, used to score each technique.

## 2. Overall Description

### 2.1 Product Perspective
A standalone app built on the provided `sample-docs/` (GDPR, PCI-DSS, SOC2 excerpts). It is a
learning deliverable, not production infrastructure. A later project wraps these techniques as
tools behind an agent; that is out of scope here.

### 2.2 User Classes and Characteristics
- **Learner/operator** — the authenticated user who runs conversations and inspects each
  technique. Full-stack proficient; learning RAG.
- **Mentor/reviewer** — reviews the deployed app, docs, tests, and proof, and hears the
  presentation.

### 2.3 Assumptions and Constraints
- Models: Google Gemini (Flash for generation, `gemini-embedding-001` for text embeddings,
  multimodal embeddings in Stage 4), on the free tier; provider is swappable.
- Persistence: PostgreSQL with the `pgvector` extension, used in dev, test, and production.
- Stack: Django (templates + HTMX), no DRF/SPA; functional over polished UI.
- Delivered in stages 0–5, each with a test-first lifecycle and a live HTTPS deployment.
- Secrets and configuration come from environment variables, never committed.

## 3. Specific Requirements

### 3.1 Functional Requirements
1. **Auth** — users log in/out; all chat and retrieval views require authentication.
2. **Chat (Stage 0)** — create, list, open, rename, delete conversations; persisted,
   owner-scoped, chronological message history; one Gemini Flash call per user message.
3. **Embedding RAG (Stage 1)** — ingest and chunk documents (fixed/recursive/semantic
   comparison), embed and store in pgvector, dense + hybrid (sparse/BM25) retrieval, a
   reranking step, and answers with citations.
4. **Knowledge-graph RAG (Stage 2)** — extract triplets, build/persist a graph, graph-based
   retrieval, answer generation with node/edge traceability, interactive graph visual.
5. **Vectorless RAG (Stage 3)** — build a document tree, LLM-guided navigation, page/section
   citations, navigation-path visual, no vector store or chunking.
6. **Multimodal RAG (Stage 4)** — parse and retrieve tables/images/equations with multimodal
   embeddings; show parsed evidence.
7. **Query, comparison, evaluation (Stage 5)** — a per-technique query page, a four-way
   comparison view for one question, and an evaluation harness scoring retrieval hit-rate and
   answer quality over a gold Q&A set.
8. **Transparency** — every technique surfaces its retrieved evidence, scores, token usage,
   cost, and latency in the UI.

### 3.2 Non-Functional Requirements
- **Security** — authentication on all app views; object-level owner scoping (404 otherwise);
  POST + CSRF for state changes; HTTPS, HSTS, and secure cookies in production; secrets in env.
- **Reliability** — a failed LLM call rolls back so no partial turn is stored; `/health/`
  reports live DB connectivity.
- **Testability** — test-first automated tests per stage against the known sample docs; LLM
  calls mocked in tests (no external calls).
- **Observability** — structured request/LLM logging without message text or secrets.
- **Portability** — containerized (Docker + Gunicorn + WhiteNoise); deployable to any
  Python-friendly host with managed Postgres.

### 3.3 External Interface Requirements
- **Google Gemini API** — text generation and (text/multimodal) embeddings via `google-genai`.
- **PostgreSQL + pgvector** — relational persistence and vector similarity search.
- **Hosting platform** — TLS termination and managed Postgres (e.g. Render + Neon/Supabase).

## 4. Appendices

- Brief and stage definitions: `README.md`.
- Phased build/learning plan: `LEARNING_PLAN.md`.
- Per-stage design, requirements, test plan, and reflection: `docs/`.
- Current implemented scope: **Stage 0** (deployed). Stages 1–5 pending.
