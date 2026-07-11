# Learning Plan: Multi Method RAG

This plan follows the project README and assumes strong full-stack experience but little or no prior RAG experience.

The main principle is: learn each concept just before building the stage that needs it. Avoid a long theory phase before coding, but do not build blind either.

Useful README sections:

- [Overview](README.md#overview)
- [What Is Tested](README.md#what-is-tested)
- [What Is Learned](README.md#what-is-learned)
- [How to Learn This](README.md#how-to-learn-this)
- [The Exact Brief](README.md#the-exact-brief)
- [Project Phases](README.md#project-phases)
- [How to Start Building](README.md#how-to-start-building)

## Recommendation

Start with learning, but keep it narrow and stage-based.

Do not build the skeleton app before understanding the basic RAG mental model. You need enough context to make good architecture choices for Stage 0. But also do not try to learn all four RAG methods before writing code. That will be too abstract.

Recommended flow:

```text
short concept sprint -> light design note -> failing test -> build -> visible demo -> reflection
```

This matches the README's [Project Phases](README.md#project-phases): Plan, Build, Test, Show.

## Project Workflow and Deliverables (from README "How this works")

This governs *how* the work is delivered, alongside the stage sequence below.

- **Work in a fork.** Fork the project repository and do all work inside your fork. Do not push to the upstream org repo.
- **Commit per stage** and save proof (a link or screenshot) into `proof/` as each stage completes.
- **One-time docs setup:** write a short `docs/srs.md` (requirements spec) early, and maintain `docs/system-diagram.drawio` as a simple architecture diagram that evolves each stage.
- **Keep `LEARNING_LOG.md` updated**, one entry per area, produced with the teach-me skill.
- **Final deliverable:** fill in `PRESENTATION.md` with every link, artifact, and proof.
- **Before the call:** add your mentor as a collaborator on your fork, then schedule and present.

## Phase 0: RAG Orientation

README links:

- [Overview](README.md#overview)
- [What Is Learned](README.md#what-is-learned)
- [How to Learn This](README.md#how-to-learn-this)

Goal: understand the big picture before creating the app skeleton.

Learn:

- What RAG means.
- Why retrieval is separate from generation.
- What a document, chunk, embedding, vector store, retriever, reranker, citation, and evaluation set are.
- Why this project compares four retrieval methods over the same documents.

Use the local teaching skill:

```text
teach me RAG architecture
```

Hands-on work:

- Inspect the files in `sample-docs/`.
- Write a short note in `LEARNING_LOG.md` explaining RAG in your own words.
- Add the first short section to `docs/design.md`: what the app will do at a high level.

Exit criteria:

- You can explain why the app needs both a normal chat layer and separate retrieval methods.
- You can describe the four retrieval methods at a high level without implementation details.

## Phase 1: Stage 0 - App Skeleton and Chat

README links:

- [Stage 0: App skeleton and chat](README.md#stage-0-app-skeleton-and-chat)
- [Recommended Stack](README.md#recommended-stack)
- [Requirements and Scope](README.md#requirements-and-scope)

Goal: build the foundation that every later RAG method plugs into.

Learn:

- How to call Gemini Flash from the backend.
- How to track latency, token usage, and estimated cost.
- How the app should represent conversations and messages.

Use the local teaching skill if needed:

```text
teach me LLM API calls
```

Build:

- Chat CRUD: create, read, update, delete conversations.
- Persisted chat history.
- One plain Gemini Flash response with no retrieval.
- Basic frontend page for conversations.
- Deployment from the beginning, as required by the README.

Test first:

- Conversation can be created.
- Message can be added.
- Chat history can be loaded.
- Conversation can be renamed or updated.
- Conversation can be deleted.
- LLM call can be mocked in tests.

Show:

- A live URL with Stage 0 working.
- A short proof item in `proof/`.
- A short reflection in `docs/reflection.md`.

Exit criteria:

- The app works as a normal chatbot.
- There is no RAG yet.
- The codebase has a clear place where retrieval methods will later plug in.

## Phase 2: Stage 1 - Embedding-Based RAG

README links:

- [Stage 1: Embedding-based RAG](README.md#stage-1-embedding-based-rag-pgvector-or-qdrant)
- [Frontend transparency](README.md#frontend-transparency-applies-to-every-technique)
- [What Is Learned](README.md#what-is-learned)

Goal: build the classic RAG pipeline end to end.

Learn:

- Embeddings.
- Vector similarity.
- Chunking strategies.
- Vector stores.
- Hybrid search.
- Reranking.
- Citations.

Use the local teaching skill:

```text
teach me embeddings and vector search
teach me chunking and reranking
```

Build:

- Document ingestion from `sample-docs/`.
- Fixed, recursive, and semantic chunking comparison.
- Embeddings using `gemini-embedding-001`.
- One vector store: pgvector or Qdrant.
- Dense retrieval.
- Hybrid search: dense plus sparse or BM25.
- Reranking.
- Answer generation with citations.
- UI panel showing chunks, boundaries, scores, token usage, cost, latency, and embedding dimensions.

Test first:

- Documents are parsed.
- Chunks are created with expected metadata.
- Embeddings are stored.
- Query retrieves relevant chunks.
- Answer includes citations.
- Reranker changes or confirms ranking.

Show:

- Ask the same compliance question and inspect retrieved chunks.
- Save proof in `proof/`.
- Add design, requirements, test-plan, and reflection notes.

Exit criteria:

- You can explain why similarity search can work even when the exact words differ.
- You can explain where classic vector RAG can fail.

## Phase 3: Stage 2 - Knowledge Graph RAG

README links:

- [Stage 2: Knowledge-graph RAG](README.md#stage-2-knowledge-graph-rag)
- [Frontend transparency](README.md#frontend-transparency-applies-to-every-technique)

Goal: retrieve through relationships instead of only vector similarity.

Learn:

- Subject-predicate-object triplets.
- Entity extraction.
- Relationship extraction.
- Graph construction.
- Graph traversal for retrieval.

Use the local teaching skill:

```text
teach me knowledge graph RAG
```

Reference from the README:

- https://github.com/robert-mcdermott/ai-knowledge-graph

Build:

- Triplet extraction from the sample documents.
- Graph persistence.
- Graph retrieval for questions.
- Answer generation using graph evidence.
- Interactive graph visual in the UI.
- Trace of which nodes and edges were used.

Test first:

- Known entities are extracted.
- Known relationships are extracted.
- Graph contains expected nodes and edges.
- A graph query returns relevant evidence.
- Answer cites graph-backed source sections.

Show:

- Compare one question against Stage 1 and Stage 2.
- Save graph screenshot or proof.
- Update docs and reflection.

Exit criteria:

- You can explain when graph retrieval is better than vector retrieval.
- You can explain the risk of bad LLM-extracted relationships.

## Phase 4: Stage 3 - Vectorless RAG

README links:

- [Stage 3: Vectorless RAG](README.md#stage-3-vectorless-rag-reasoning-based)
- [What Is Learned](README.md#what-is-learned)

Goal: build retrieval without vector embeddings and without chunking.

Learn:

- Relevance versus similarity.
- Document trees.
- Page-level and section-level navigation.
- Traceable reasoning paths.

Use the local teaching skill:

```text
teach me vectorless RAG
```

Reference from the README:

- https://github.com/VectifyAI/PageIndex

Build:

- A document tree from the sample documents.
- LLM-guided navigation over the tree.
- Traceable page or section citations.
- UI visual showing the navigation path.
- No vector database and no chunking for this method.

Test first:

- Document tree is built correctly.
- Query navigation selects expected sections.
- Answer cites page or section evidence.
- The method does not depend on vector search.

Show:

- Ask a question where exact traceability matters.
- Save proof and update docs.

Exit criteria:

- You can explain why vectorless retrieval may be easier to audit.
- You can explain why it may be slower or more expensive.

## Phase 5: Stage 4 - Multimodal RAG

README links:

- [Stage 4: Multimodal RAG](README.md#stage-4-multimodal-rag)
- [Frontend transparency](README.md#frontend-transparency-applies-to-every-technique)

Goal: handle information that plain text retrieval misses, especially tables.

Learn:

- Why tables, images, and equations are hard for plain text RAG.
- Multimodal document parsing.
- Multimodal embeddings.
- How to show parsed visual evidence in the UI.

Use the local teaching skill:

```text
teach me multimodal RAG
```

Reference from the README:

- https://github.com/HKUDS/RAG-Anything

Build:

- Table, image, and equation extraction where present.
- Multimodal embeddings using `gemini-embedding-2`, or the closest available model if the API has changed.
- Retrieval over multimodal evidence.
- UI panel showing parsed tables/images/equations and selected evidence.

Test first:

- Tables are detected.
- Table content can be retrieved.
- Multimodal evidence is linked to source documents.
- A table-heavy question gets better evidence than plain text retrieval.

Show:

- Ask a table-based compliance question.
- Compare with embedding RAG.
- Save proof and update docs.

Exit criteria:

- You can explain why text-only RAG often misses table meaning.
- You can explain the extra cost and complexity of multimodal retrieval.

## Phase 6: Stage 5 - Query Page, Comparison, and Evaluation

README links:

- [Stage 5: RAG query page, comparison, and evaluation](README.md#stage-5-rag-query-page-comparison-and-evaluation)
- [What Is Tested](README.md#what-is-tested)
- [How this works](README.md#how-this-works)

Goal: turn the four methods into a clear comparison and evaluation tool.

Learn:

- Gold question and answer sets.
- Retrieval hit rate.
- Answer quality scoring.
- Latency and cost comparison.
- How to explain trade-offs clearly.

Use the local teaching skill:

```text
teach me RAG evaluation
```

Build:

- A dedicated RAG query page for one method at a time.
- A comparison view that runs the same question through all four methods.
- An evaluation harness over a small gold Q&A set.
- Score display per method.
- Final links and proof in `PRESENTATION.md`.

Test first:

- Each method can be run through one common interface.
- Comparison executes all four methods.
- Evaluation harness scores expected questions.
- Results include retrieval hit rate, answer quality, latency, and cost.

Show:

- Run one question through all four techniques.
- Run the evaluation set.
- Fill `PRESENTATION.md`.

Exit criteria:

- You can explain which retrieval method you would choose for a given scenario and why.
- The app demonstrates the differences using real outputs, not just descriptions.

## Suggested 10-Day Schedule

This is aggressive but matches the README's two-week target.

| Day | Focus | Main Output |
|---|---|---|
| 1 | RAG orientation, sample docs, stack choice | `LEARNING_LOG.md`, initial design note |
| 2 | Stage 0 app skeleton and chat | Deployed plain chatbot |
| 3 | Stage 1 embeddings, chunking, vector store | Ingestion and vector retrieval |
| 4 | Stage 1 hybrid search, reranking, citations, UI | Working embedding RAG |
| 5 | Stage 2 graph extraction and storage | Knowledge graph data |
| 6 | Stage 2 graph retrieval and visual | Working graph RAG |
| 7 | Stage 3 vectorless document tree | Working vectorless RAG |
| 8 | Stage 4 multimodal parsing and retrieval | Working multimodal RAG |
| 9 | Stage 5 comparison and evaluation harness | Side-by-side results |
| 10 | Cleanup, docs, proof, presentation | Final submission package |

## Per-Stage Checklist

Use this checklist for every stage.

- Read the matching README section.
- Run one `teach me ...` session for the core concept.
- Save the learning wrap-up in `LEARNING_LOG.md`.
- Add or update the stage section in `docs/requirements.md`.
- Add or update the stage section in `docs/design.md`.
- Add or update `docs/test-plan.md`.
- Update `docs/system-diagram.drawio` to reflect the new stage.
- Write the failing test first.
- Build the smallest working version.
- Make the internal process visible in the UI.
- Record proof in `proof/`.
- Add a short reflection in `docs/reflection.md`.
- Commit the stage.

## First Next Step

Start with:

```text
teach me RAG architecture
```

After that, inspect `sample-docs/`, choose the stack, and begin Stage 0.
