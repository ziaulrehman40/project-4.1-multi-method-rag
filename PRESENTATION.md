# Project Submission

Fill this file in as you go. This is what you submit and what you present from on your call.

## Candidate

- Name: Zia Ul Rehman
- Date submitted: (fill at submission)

## Links

- Live URL: https://zia-rag-4-1.onrender.com/
- Repository: https://github.com/ziaulrehman40/project-4.1-multi-method-rag
- Project board: (optional)
- Loom walkthrough video: (add before presenting)

## Artifacts

- Software Requirements Specification (in docs): docs/srs.md
- System diagram (in docs): docs/system-diagram.drawio
- Screenshots and other proof (in proof): proof/

## Proof of learning

One line per skill: what you learned and your confidence from one to three. Pull these from LEARNING_LOG.md. (Confidence values below are a starting point — adjust to your own.)

- RAG architecture (confidence 3): clarified retrieval vs. generation, why the "G" defines RAG, and that answer truthfulness is bounded by retrieval/ingestion quality.
- Embedding RAG (confidence 3): chunking strategy trade-offs, dense + sparse hybrid retrieval fused with RRF, and LLM reranking with a non-silent fallback.
- Knowledge-graph RAG (confidence 2): LLM triple extraction, entity resolution, and seed-by-embedding + graph traversal for a cited, auditable reasoning trace.
- Vectorless RAG (confidence 2): letting the LLM navigate a document's section tree (no embeddings) and answer only from opened sections, with the navigation path as the citation.
- Multimodal RAG (confidence 2): parsing PDF text/tables/figures, cross-modal embedding so a text query retrieves a chart image, and a vision model answering from pixels.
- Evaluation (confidence 3): retrieval metrics (hit@k / recall@k / MRR with a uniform k cutoff) plus an LLM-as-judge for faithfulness/correctness, and why a shared corpus is required for a fair four-way comparison.
- LLM provider adapter (confidence 3): isolating all SDK calls behind one interface so generation swaps (Gemini / Groq / OpenAI) with no call-site changes, with centralised transient-only retry and per-provider cost/limits.
- Production & guardrails (confidence 2): shell-free idempotent startup on Render, an env-gated one-time rebuild latch, and abuse/cost guardrails (question-length + output-token caps) for a paid key.

## Summary

This is one Django app that answers questions about a small set of compliance documents four different ways — embedding RAG, knowledge-graph RAG, vectorless (reasoning-based) RAG, and multimodal RAG — over a single shared corpus, with a query page, a side-by-side comparison view, and an evaluation harness that scores each technique on retrieval and answer quality. Every technique exposes its own transparency (retrieved chunks and scores, the graph/tree/figure evidence, token usage, cost, and latency). All LLM calls go through a provider adapter, so generation can be swapped between Gemini, Groq, and OpenAI without touching the techniques while embeddings stay on Gemini. The biggest lessons were that a RAG answer is only as good as its retrieval and ingestion, and that a fair comparison of techniques demands the same corpus and honest, apples-to-apples metrics.

## Stage progress

- [x] Stage 0 — App skeleton and chat (deployed, tested)
- [x] Stage 1 — Embedding-based RAG (chunking comparison, hybrid search, reranking, cited answers, transparency)
- [x] Stage 2 — Knowledge-graph RAG (LLM triple extraction, graph store, seed+traverse retrieval, cited trace, interactive graph visual)
- [x] Stage 3 — Vectorless RAG (document tree, LLM navigation over the TOC, cited answer, navigation-path tree visual)
- [x] Stage 4 — Multimodal RAG (PDF tables/figures, gemini-embedding-2 cross-modal retrieval, vision answer over charts, inline figure evidence)
- [x] Stage 5 — Query page, four-way comparison, evaluation harness (retrieval + LLM-judge metrics over a shared corpus)

## Beyond the brief

- LLM provider adapter (`llm/`): generation swappable across Gemini / Groq / OpenAI with no call-site changes; embeddings stay on Gemini (pgvector dimension-locked).
- Shared corpus so the four-way comparison is genuinely apples-to-apples.
- Abuse/cost guardrails for a paid key (question-length + output-token caps; transient-only retry).
- Shell-free one-time rebuild latch (`REBUILD_VERSION`) for Render.
