# Project 4.1: Multi Method RAG

| Field | Detail |
|---|---|
| Project Number | 4.1 |
| Project Name | Multi Method RAG |
| Tier | Senior |
| Deadline | 10 working days (2 weeks) from your start date |
| Status | Active |
| Tags | RAG, Embeddings, Vector Databases, Knowledge Graphs, Vectorless Retrieval, Multimodal RAG, Chunking, Reranking, Evaluation, Test Driven Development, Prompt Engineering, Git Workflow |

---

## Overview

You are building Multi Method RAG: one small web application that answers questions about a set of documents, and lets you swap between four different ways of doing retrieval and see exactly how each one behaves.

This is a practice and reference project. The point is not to ship a product. The point is to build each retrieval technique yourself, once, on the same documents, so you understand what each one actually does, where it shines, and where it breaks. By the end you will have a single app where you can ask the same question four different ways and watch the chunks, the reasoning, the token usage, and the answer change in front of you.

Keep it light and move fast. You are encouraged to use AI heavily to accelerate the build. The sooner you get each stage working, the sooner you learn from it. Aim for 10 working days (2 weeks).

The theme is compliance document Q&A (questions about policy documents such as PCI DSS, GDPR, or SOC2), because those documents are realistic, structured, and table-heavy, which makes the differences between techniques easy to see. A small set of sample documents is already provided for you in `sample-docs/`.

---

## Covered Areas

| Category | Area |
|---|---|
| AI and LLM Fundamentals | Embeddings and Vector Search |
| AI and LLM Fundamentals | RAG Architecture |
| AI and LLM Fundamentals | Knowledge Graphs |
| AI and LLM Fundamentals | Chunking and Retrieval Quality |
| AI and LLM Fundamentals | Evaluation |
| Programming and Stack Fundamentals | API Construction |
| Programming and Stack Fundamentals | Data Persistence |
| SDLC and Engineering Practices | Test Driven Development |
| SDLC and Engineering Practices | Development Lifecycle |
| SDLC and Engineering Practices | Version Control |
| Communication and Client Readiness | Technical Explanation |

Communication and Client Readiness is trained through the Review and Presentation section below, alongside the build, not as separate work.

---

## What Is Tested

By the end of this project, you should be able to show, on request:

- Four working retrieval techniques answering the same questions over the same documents: embedding-based RAG, knowledge-graph RAG, vectorless (reasoning-based) RAG, and multimodal RAG.
- A frontend that makes each technique transparent: the retrieved chunks, the pre- and post-processing steps, token usage, cost, latency, and the technique's own visual.
- A single RAG query page to run one technique in full, and a comparison view to run all four side by side.
- An evaluation harness that scores the techniques against a known question and answer set.
- Automated tests written test-first at each stage, passing against the provided sample documents.
- Evidence of a full lifecycle: short design notes, an architecture sketch, tests, and a reflection per stage.
- The ability to explain, in plain language and without notes, how each technique works and when you would choose it.

## What Is Learned

- How embedding-based retrieval works end to end: chunking, embeddings, a vector store, similarity search, reranking, and citations.
- How a knowledge graph is built from text and how graph retrieval differs from vector retrieval.
- What "vectorless" retrieval means: reasoning over a document tree instead of matching vectors, and why that gives traceable answers.
- How multimodal RAG handles tables, images, and equations that plain-text RAG misses.
- Why chunking strategy, reranking, and hybrid search change retrieval quality, seen directly rather than described.
- How to evaluate retrieval instead of guessing, using a small gold question and answer set.
- What it feels like to write a test before the code, at each stage, against known inputs.

## What Is Practiced

- Building the same capability four ways and comparing them honestly on real numbers.
- Test driven development at every stage, with AI writing the first failing test against the known sample documents.
- Making a system observable: surfacing what happens inside retrieval, not just the final answer.
- Reading an open-source project's architecture to understand a technique, then implementing your own version.
- The full lifecycle in miniature, once per stage: a short design note, a diagram, tests, and a reflection.
- Explaining technical trade-offs clearly, out loud and in writing.

---

## Prerequisites

You should already be comfortable with the following. If one is rusty, ask your AI Instructor for a fast revision and a few check questions, then move on.

- Basic programming in at least one language
- Building and calling a simple web API
- Basic Git: clone, commit, push, branch
- What an LLM API call is (sending a prompt, getting a response)

### Setting up your AI Instructor and troubleshooting partner

Two ready-made skills are included in `skills/`. Add both to your Claude project before you start.

- **Learning agent** (`skills/teach-me/SKILL.md`). Say "teach me" and a topic, for example "teach me embeddings", and it walks you through it, has you do the work, and asks for a confidence score at the end. Save that in `LEARNING_LOG.md`.
- **Troubleshooting agent** (`skills/troubleshoot/SKILL.md`). Describe what broke and it guides you to the cause instead of handing you the fix.

---

## How to Learn This

Learn each concept just before you build the matching stage. Use your AI Instructor first for a fast interactive explanation, then confirm against the official documentation. The open-source repositories listed in each stage are samples of how other people have implemented the technique: read them for approach and usage, then build your own version.

| Topic | Learn With Your AI Instructor | Reference and Documentation |
|---|---|---|
| Embeddings and vector search | Ask it to explain what an embedding is and how similarity search works, then quiz you | Your chosen vector store's docs (pgvector or Qdrant) |
| Chunking, hybrid search, reranking | Ask it to explain why chunk size and reranking change answer quality | Your framework's retrieval docs |
| Knowledge graphs from text | Ask it to explain subject-predicate-object triplets and graph retrieval | Sample repo in Stage 2 |
| Vectorless, reasoning-based retrieval | Ask it to explain relevance versus similarity, and tree-based navigation | Sample repo in Stage 3 |
| Multimodal RAG | Ask it to explain how tables and images are parsed and retrieved | Sample repo in Stage 4 |
| Evaluating retrieval | Ask it to help you design a small gold question and answer set | Your framework's evaluation docs |
| Test driven development | Ask it to write a failing test first for each stage, then make it pass | Your test framework's docs |

### Work manually first, then let AI accelerate

Before you generate a stage, understand the technique: sketch the flow, or talk it through with your AI Instructor. Once you understand it, using a coding agent to accelerate the actual build is expected and encouraged. What matters is that you can explain your own system afterward, in your own words, without notes.

---

## Recommended Stack

This project can be built in any stack or language you choose.

- **Models (recommended, free):** Google Gemini. A free-tier Gemini Flash model for the LLM, and the Gemini embedding models for embeddings (`gemini-embedding-001` for text, `gemini-embedding-2` for multimodal in Stage 4). Google provides a free usage limit on the embedding models. See the Google AI docs at https://ai.google.dev/gemini-api/docs/embeddings. Any other model or embedding provider is acceptable if you prefer.
- **Framework:** your choice. LangChain is a common fit for RAG work, but not required.
- **Vector store (Stage 1):** your choice of pgvector or Qdrant.
- **Frontend and backend:** your choice. Keep the frontend simple. This is not a design project; it is a transparency project.

### Reference UIs to study, not rebuild

Two mature open-source RAG apps are worth deploying and clicking through, to see how a good RAG interface surfaces chunks, citations, and settings. Borrow the good ideas.

- Open WebUI
- AnythingLLM: https://github.com/mintplex-labs/anything-llm

---

## The Exact Brief

Build one application, over the provided `sample-docs/`, in five stages. Each stage is demoable, tested, and (from Stage 0) deployed. Build the stages in order.

### Stage 0: App skeleton and chat

Set up the app in your framework of choice. Build a working chatbot over the compliance theme with **complete chat CRUD and history**: create, read, update, and delete conversations, with persisted history. One LLM call to a free Gemini Flash model. No retrieval yet. Deploy to a live URL now, and keep it live as you add stages. Write your first tests test-first.

### Stage 1: Embedding-based RAG (pgvector or Qdrant)

Ingest the sample documents, chunk them, embed with `gemini-embedding-001`, store, retrieve, and answer with citations. Pick **either pgvector or Qdrant**. Include:
- A chunking-strategy comparison (fixed, recursive, semantic).
- Hybrid search (dense plus sparse or BM25).
- A reranking step.

### Stage 2: Knowledge-graph RAG

Extract subject-predicate-object triplets from the documents with an LLM, build a knowledge graph, do graph-based retrieval, and show an interactive graph visual.
- Sample of how others have done it: https://github.com/robert-mcdermott/ai-knowledge-graph

### Stage 3: Vectorless RAG (reasoning-based)

Build reasoning-based retrieval with no vector database and no chunking: the LLM navigates a document tree and returns traceable, page or section-cited answers.
- Sample of how others have done it: https://github.com/VectifyAI/PageIndex

### Stage 4: Multimodal RAG

Handle the parts plain-text RAG misses: tables, images, and equations. Use `gemini-embedding-2` (multimodal). Compliance documents are table-heavy, so this stage pays off.
- Sample of how others have done it: https://github.com/HKUDS/RAG-Anything

### Stage 5: RAG query page, comparison, and evaluation

This is the final deliverable and where the project ends.
- A dedicated **RAG query page** to run one question against any single technique and inspect it in full.
- A **comparison view** that runs the same question through all four techniques side by side.
- An **evaluation harness**: a small gold question and answer set over the sample documents, scoring retrieval hit-rate and answer quality per technique.

---

## Requirements and Scope

**In scope:**
- One app, the four retrieval techniques above, built in sequence on the provided sample documents.
- Chat with full CRUD and history (Stage 0).
- Full frontend transparency for every technique (see below).
- Test-first automated tests at each stage, run against the known sample documents.
- A dedicated RAG query page, a four-way comparison view, and an evaluation harness.
- Light lifecycle docs per stage, and a live deployed URL from Stage 0 onward.

**Out of scope for this project (these are later projects):**
- An agent that decides which technique to use. That is the next project: a single agent that uses these techniques as tools, on its own page, exposed as an MCP server.
- Multi-agent orchestration. That is the project after.
- A polished, designed frontend. Functional and transparent is enough.
- Production-grade infrastructure beyond a simple live deployment.

### Frontend transparency (applies to every technique)

Every technique must be visible in the UI, so it can be tested and showcased. For each answer, show:
- The retrieved chunks, with their boundaries and similarity or relevance scores.
- The pre-processing and post-processing steps applied.
- Token usage, cost, and latency.
- Embedding dimensions where relevant.
- The technique's own visual: the knowledge graph, the vectorless document tree, the multimodal parse, and an embedding-dimension view for embedding RAG.

---

## Project Phases

Run each of the five stages as a small, complete lifecycle rather than one big build at the end.

1. **Plan.** A short requirements and design note for the stage, and an architecture sketch. Kept light.
2. **Build.** Implement the stage. Use AI to accelerate once you understand the technique.
3. **Test.** Write the tests test-first, against the known sample documents, and make them pass.
4. **Show.** Confirm the technique is visible in the UI, deploy, and write a short reflection.

Artifacts, kept light: `docs/design.md` and `docs/requirements.md` grow one short section per stage, `docs/test-plan.md` lists what each stage tests, `docs/reflection.md` gets a few lines per stage, and `docs/system-diagram.drawio` holds a simple evolving architecture diagram.

---

## How this works

- Fork the project repository that has been shared with you.
- Work through the stages in order, inside your fork.
- Commit as you finish each stage, and save proof (a link or screenshot) into `proof/`.
- Keep `LEARNING_LOG.md` updated, one entry per area, produced with your teach-me skill.
- When everything is done, fill in `PRESENTATION.md` with every link, artifact, and proof.
- Add your mentor as a collaborator on your fork, schedule a call, and present.

## Repository structure

```
project-4.1-multi-method-rag/
  README.md              This brief. Read it, do not edit it.
  PRESENTATION.md        Your submission. All links, artifacts, and proof go here.
  LEARNING_LOG.md        One short wrap up per area you learn.
  sample-docs/           The provided compliance documents to build against.
  skills/
    teach-me/SKILL.md       Your learning agent (provided).
    troubleshoot/SKILL.md   Your troubleshooting agent (provided).
  proof/                  Screenshots and other evidence go here.
  docs/
    srs.md                Short requirements spec.
    requirements.md       Requirements notes, one short section per stage.
    design.md             Design decisions, one short section per stage.
    system-diagram.drawio Simple evolving architecture diagram.
    test-plan.md          What each stage tests.
    reflection.md         A few lines of reflection per stage.
  src/                    Your application code.
  tests/                  Your automated tests.
  .github/workflows/      Your CI workflow.
  Dockerfile
  .gitignore
  LICENSE
```

## How to Start Building

1. Fork the repository into your own account.
2. Read this brief in full before writing any code.
3. Set up your AI Instructor from `skills/` and get your free Gemini API key.
4. Look at the provided `sample-docs/` so you know exactly what you are retrieving over.
5. Build Stage 0, deploy it, and confirm chat CRUD and history work.
6. Move through Stages 1 to 5 in order. Write the test first at each stage. Keep the technique visible in the UI.
7. Confirm a clean clone of your finished repository runs from your README alone.

---

## Definition of Done

- [ ] Clean clone runs from the README alone, with a live URL
- [ ] Stage 0: chat with full CRUD and persisted history works
- [ ] Stage 1: embedding RAG (pgvector or Qdrant) with chunking comparison, hybrid search, and reranking
- [ ] Stage 2: knowledge-graph RAG with an interactive graph visual
- [ ] Stage 3: vectorless, reasoning-based RAG with traceable citations
- [ ] Stage 4: multimodal RAG handling tables and images
- [ ] Stage 5: RAG query page, four-way comparison view, and an evaluation harness with per-technique scores
- [ ] Every technique is visible in the UI: chunks, pre and post-processing, token usage, cost, latency, and its own visual
- [ ] Test-first automated tests at each stage pass against the provided sample documents
- [ ] Light lifecycle docs completed: requirements, design, diagram, test plan, reflection, one section per stage
- [ ] `LEARNING_LOG.md` has an entry for every area in Covered Areas
- [ ] `PRESENTATION.md` completed with every link, artifact, and proof
- [ ] Loom video recorded and linked in `PRESENTATION.md`
- [ ] Mentor added as a collaborator, live presentation scheduled and completed

---

## Review and Presentation

When your Definition of Done checklist is complete, submit in three formats:

1. **Written.** `PRESENTATION.md`: the live URL, the repository link, the Loom link, and a short note on each area you learned.
2. **Video.** A short Loom walkthrough: ask one question, run it through all four techniques, and explain what changes between them.
3. **Live.** A call with your mentor. Walk through the app live, run the comparison, and answer questions without notes.

---

## Bonus Practice Activities

Optional unless your mentor points you toward one.

- **Write a comparison article.** After Stage 5, write a short post comparing the four techniques on your own numbers: where each won, where each broke, and when you would pick each. This is strong portfolio and profile material.
- **Daily speaking practice with Gemini Live.** If communication is an area to work on, spend ten minutes a day explaining the technique you built that day to Gemini Live, then take its feedback.

---

## Interview Gap-Check Questions

You should be able to answer all of these comfortably before considering the project finished.

1. Walk through what happens, end to end, from a question to a cited answer in your embedding RAG stage.
2. What actually changes when you switch from fixed to semantic chunking, and how did you see it in your own results?
3. What does reranking do, and what did it change on your sample documents?
4. How is knowledge-graph retrieval different from vector retrieval? When would you reach for the graph?
5. Explain "vectorless" retrieval. Why can it give more traceable answers than embedding RAG?
6. What does multimodal RAG catch on these documents that plain-text RAG misses?
7. Pick one question from your gold set. How did the four techniques score, and why do you think they differed?
8. Pick one test. Why does it exist, and was it written before or after the code? Why?
9. If a client asked you to pick one technique for their compliance documents, which would you choose and why?
10. What would you do differently if you started this lab again?

If you cannot answer these comfortably, you are assigned another practice variant in the same RAG cluster until the gap closes.
