"""Aggregate an EvalRun's per-cell results into summary tables for display.

- summarise(): per-technique averages across the whole gold set (overall leaderboard).
- by_category(): correctness per (question-type x technique) — shows each technique winning
  in its own lane (semantic / structural / multimodal), which is the project's thesis.
"""

from collections import defaultdict

TECHNIQUE_ORDER = ["embedding", "graph", "vectorless", "multimodal"]


def _avg(items, attr):
    return sum(getattr(i, attr) for i in items) / len(items) if items else 0.0


def summarise(run):
    grouped = defaultdict(list)
    for result in run.results.all():
        grouped[result.technique].append(result)

    summary = []
    for technique, items in grouped.items():
        # Average only over cleanly-scored cells — a failed cell (quota/judge error) is stored
        # with 0.0 scores, so counting it would drag the leaderboard down artificially. Errors
        # are surfaced separately; cost is summed over ALL cells (the call still cost money).
        scored = [i for i in items if not i.error]
        summary.append({
            "technique": technique,
            "n": len(items),
            "errors": sum(1 for i in items if i.error),
            "hit_at_k": _avg(scored, "hit_at_k"),
            "recall_at_k": _avg(scored, "recall_at_k"),
            "mrr": _avg(scored, "mrr"),
            "faithfulness": _avg(scored, "faithfulness"),
            "correctness": _avg(scored, "correctness"),
            "latency_ms": _avg(scored, "latency_ms"),
            "est_cost_usd": sum(i.est_cost_usd for i in items),
        })
    summary.sort(key=lambda s: TECHNIQUE_ORDER.index(s["technique"])
                 if s["technique"] in TECHNIQUE_ORDER else 99)
    return summary


def by_category(run):
    """Correctness per (question-type x technique), as template-friendly rows.

    Returns {techniques: [...], rows: [{type, cells: [{technique, correctness}]}]}.
    """
    results = list(run.results.all())
    types = sorted({r.qtype for r in results})
    techniques = [t for t in TECHNIQUE_ORDER if any(r.technique == t for r in results)]

    rows = []
    for qtype in types:
        cells = []
        for technique in techniques:
            matches = [r for r in results
                       if r.qtype == qtype and r.technique == technique and not r.error]
            cells.append({"technique": technique,
                          "correctness": _avg(matches, "correctness") if matches else None})
        rows.append({"type": qtype, "cells": cells})
    return {"techniques": techniques, "rows": rows}
