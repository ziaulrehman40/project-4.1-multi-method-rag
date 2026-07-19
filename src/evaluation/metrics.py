"""Retrieval metrics — computed from the ordered source list a technique returned vs the
gold (expected) sources. No LLM involved; these grade the *retrieval* half only.
"""


def hit_at_k(retrieved_sources, gold_sources):
    """hit@k: 1.0 if ANY gold source appears among the retrieved sources, else 0.0.

    The coarsest signal — "did the right document show up at all?".
    """
    gold = set(gold_sources)
    return 1.0 if any(source in gold for source in retrieved_sources) else 0.0


def recall_at_k(retrieved_sources, gold_sources):
    """recall@k: what FRACTION of the gold sources were retrieved (|gold ∩ retrieved| / |gold|).

    Stricter than hit@k when a question needs evidence from more than one source.
    """
    gold = set(gold_sources)
    if not gold:
        return 0.0
    return len(gold & set(retrieved_sources)) / len(gold)


def mrr(retrieved_sources, gold_sources):
    """Mean Reciprocal Rank (per question): 1/rank of the FIRST relevant source.

    Top result relevant -> 1.0, second -> 0.5, third -> 0.33, none -> 0.0. Unlike hit@k,
    this rewards putting the right source HIGH, not just somewhere in the list.
    """
    gold = set(gold_sources)
    for rank, source in enumerate(retrieved_sources, start=1):
        if source in gold:
            return 1.0 / rank
    return 0.0
