# Project Brief

Internal tracking metadata for mentors. Not read by the resource building the project.

- **Tier:** Senior
- **Categories and subcategories targeted:** AI and LLM Fundamentals (Embeddings and Vector Search, RAG Architecture, Knowledge Graphs, Chunking and Retrieval Quality, Evaluation); Programming and Stack Fundamentals (API Construction, Data Persistence); SDLC and Engineering Practices (Test Driven Development, Development Lifecycle, Version Control); Communication and Client Readiness (Technical Explanation)
- **Role, seniority, and technical tags:** RAG, embeddings, vector databases, knowledge graphs, vectorless retrieval, multimodal RAG, evaluation, TDD
- **Start date:** [date]
- **End date:** [date]

## What This Project Teaches

Hands-on depth in retrieval. The resource builds four retrieval techniques (embedding-based RAG, knowledge-graph RAG, vectorless reasoning-based RAG, multimodal RAG) on the same document set, makes each one observable in the UI, and evaluates them against a known question and answer set. It is a practice and reference build, not a placement gate.

## Relationship to the library

Decimal variant in the same RAG cluster as Project 4 (The Knowledge Keeper). Project 4 is the lighter single-technique RAG project; Project 4.1 is the deeper multi-technique lab. This is a named practice-and-reference build (generalized, forkable by any resource), not a gap-check retry of Project 4.

Follow-on projects (not part of 4.1):
- Next: a single agent that uses these four retrieval techniques as tools, on its own page, exposed as an MCP server.
- After: multi-agent orchestration (for example LangGraph).

## Assessment Criteria

On successful completion, the resource can build and explain each of the four retrieval techniques, justify chunking, reranking, and hybrid-search choices from their own measured results, evaluate retrieval quality rather than guess at it, and choose a technique for a given document set and defend the choice. They can also demonstrate test-first discipline against known inputs.

## Definition of Done

- [ ] Clean clone runs from the README alone, with a live URL
- [ ] All five stages complete (chat with CRUD and history, embedding RAG, knowledge-graph RAG, vectorless RAG, multimodal RAG, plus the query page, comparison view, and evaluation harness)
- [ ] Every technique is observable in the UI (chunks, pre and post-processing, token usage, cost, latency, technique visual)
- [ ] Test-first tests pass against the provided sample documents
- [ ] CI is green
- [ ] Light lifecycle docs completed, one section per stage
- [ ] Presentation checkpoint completed
- [ ] Assessment criteria checked against actual performance

## Showcase

Live URL plus a short Loom: one question run through all four techniques side by side, explaining what changes between them. A written technique-comparison article is a strong optional portfolio and profile asset.

## Depth of Learning

Depth, not surface. The resource implements each technique themselves (using the linked repos only as reference examples), makes internals visible, and measures results. Suited to a resource ready to move fast across several retrieval approaches at once.

## Intended Use Case

A generalized, reusable lab any resource can fork to learn and compare RAG techniques on a realistic, table-heavy compliance-document theme. Sample documents are provided so results are deterministic and testable.
