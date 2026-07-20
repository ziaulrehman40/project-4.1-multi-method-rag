"""Retrieval metrics — computed from the ordered source list a technique returned vs the
gold (expected) sources. No LLM involved; these grade the *retrieval* half only.

All three apply the SAME top-`k` cutoff (DEFAULT_K) before scoring, so techniques that return
long lists (e.g. the graph's many edges) aren't unfairly favoured over ones that return a few
chunks — the comparison is genuinely "did the right doc appear in the top k?".
"""

DEFAULT_K = 5


def hit_at_k(retrieved_sources, gold_sources, k=DEFAULT_K):
    """hit@k: 1.0 if ANY gold source appears in the top-k retrieved sources, else 0.0.

    The coarsest signal — "did the right document show up at all?".
    """
    gold = set(gold_sources)
    return 1.0 if any(source in gold for source in retrieved_sources[:k]) else 0.0


def recall_at_k(retrieved_sources, gold_sources, k=DEFAULT_K):
    """recall@k: fraction of gold sources found in the top-k (|gold ∩ top-k| / |gold|).

    Stricter than hit@k when a question needs evidence from more than one source.
    """
    gold = set(gold_sources)
    if not gold:
        return 0.0
    return len(gold & set(retrieved_sources[:k])) / len(gold)


def mrr(retrieved_sources, gold_sources, k=DEFAULT_K):
    """Mean Reciprocal Rank (per question): 1/rank of the FIRST relevant source in the top-k.

    Top result relevant -> 1.0, second -> 0.5, third -> 0.33, none -> 0.0. Unlike hit@k,
    this rewards putting the right source HIGH, not just somewhere in the list.
    """
    gold = set(gold_sources)
    for rank, source in enumerate(retrieved_sources[:k], start=1):
        if source in gold:
            return 1.0 / rank
    return 0.0
