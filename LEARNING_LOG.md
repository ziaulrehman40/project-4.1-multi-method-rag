# Learning Log

One entry per skill. Use the Learning Sprint wrap up from your teach-me skill: a confidence score from one to three, and two or three sentences on what clicked and what is still shaky.

| Date | Skill | Confidence (1-3) | Reflection |
|---|---|---|---|
| Jul 11, 2026 | RAG architecture | 3 | Basic concepts of RAG are mature now, i had some miss-understandings which are clear. And also the teach me skill has been very helpful too. |
| Jul 12 2026 | embeddings and vector search | 3 | Basic concepts of embeddings, how to chunk with basis techniques |
| Jul 12 2026 | Chunking strategies | 3 | 3 main chunking strategies are clear now, semantic chunking though powerful is not cheap, when docs are structured, recursive/headlines aware chunking makes more sense |
| Jul 12 2026 | Hybrid Search | 3 | Using a mix of vector search and fullt ext kind fo search(BM25), or dense and sparse search is really useful for finding better matches |
| Jul 12 2026 | Re-ranking | 3 | Asking specialized tools to re-rank a small number of top matching chunks of text is also a smart way of achieving ebtter accuracy at less cost |
| Jul 13 2026 | Knowledge Graphs | 3 | I didn't know what are knowledge graphs in depth, but now I understand them better, and how they are built actually. |
| Jul 13 2026 | Triplets extraction, facts extraction | 2.5 | Maybe there are more ways of extracting fats and these kind of plants. But for now, using an LLM seems fine. |
| Jul 14 2026 | Searching/matching in knowledge graph | 2.5 | Different approaches to matching and finding relevant nodes and facts is a bit tricky, we need to balance this as per the data size, quality and other factors probably |
| Jul 14 2026 | local vs global search concept | 2.5 | A very useful concept for large doc searches, the concept of communities and summaries to get to sections of relevant text is actual production grade idea |
| Jul 16 2026 | Vectorless RAG - Concept | 3 | An interesting approach, though very limited useful usecases |
| Jul 18, 2026 | Vectorless RAG - buildup | 2 | Interesting techniques like maintaining summaries at different node levels with help of LLM etc, but i think this side may have much more than this, sounds too simple and anive for complex tasks |
| Jul 18 2026 | Multimodal RAG techniques | 2.5 | A bigger universe, got an intro and understanding to kick things off where needed |
| Jul 18 2026 | PDF chunking | 2 | Much more fun due to page splits, images, multipage tables etc, AI was shying from some items, i had to let it relax as the main asks of the project were being met |
| Jul 19, 2026 | Multimodal RAG - vision answer | 2 | Retrieved figures go to a vision model as real images, so it answers "which category is highest" from the chart pixels; text techniques only have the surrounding prose. |
| Jul 19, 2026 | RAG evaluation & metrics | 2 | hit@k / recall@k / MRR grade retrieval and an LLM-judge grades faithfulness/correctness; a fair four-way comparison needs the SAME corpus and a uniform top-k cutoff, else the scores are artifacts. |
| Jul 19, 2026 | LLM-as-judge | 2 | A rubric-scored judge is convenient but biased (self-eval, leniency); hardening the parse and showing it the figure images made multimodal scoring honest. |
