"""Run the gold set through every technique and record scored results.

QUOTA CAVEAT: a full run makes many LLM calls — roughly
    len(gold) x 4 techniques x (answer pipeline calls + 1 judge call).
On a rate-limited provider (e.g. a free tier) even the small gold set can hit a daily/minute
cap, so a run may stop partway. The harness degrades gracefully: any technique/judge failure is
recorded as an EvalResult with `error` set (scores left at 0) and the run continues;
`EvalRun.completed` reflects whether every cell scored cleanly.
"""

import base64

from llm import Image, active_generation_model, get_generation_provider

from .gold import GOLD
from .judge import judge
from .metrics import hit_at_k, mrr, recall_at_k
from .models import EvalResult, EvalRun
from .registry import run_all


def _evidence_images(evidence):
    """Figure images from a technique's evidence, capped at the provider's per-call limit, so
    the judge can grade a chart answer against the actual pixels (mainly multimodal)."""
    max_images = get_generation_provider().max_images
    images = [Image(data=base64.b64decode(e["image_b64"]))
              for e in evidence if e.get("image_b64")]
    return images[:max_images]


def run_evaluation(gold=GOLD):
    """Execute one evaluation run and return the EvalRun (with results attached)."""
    # Label the run with the ACTIVE generation model so runs are comparable across providers.
    run = EvalRun.objects.create(model=active_generation_model())
    all_clean = True

    for item in gold:
        for result in run_all(item["question"]):
            base = {
                "run": run, "technique": result["technique"],
                "question": item["question"], "qtype": item["type"],
            }
            if result["error"]:  # technique itself failed (e.g. quota)
                EvalResult.objects.create(**base, error=result["error"][:300])
                all_clean = False
                continue

            retrieved = result["sources"]
            gold_sources = item["expected_sources"]
            evidence_text = "\n".join(e["detail"] for e in result["evidence"])
            evidence_images = _evidence_images(result["evidence"])
            try:
                scores = judge(item["question"], item["expected_answer"],
                               result["answer"], evidence_text, images=evidence_images)
            except Exception as error:  # judging failed -> record retrieval metrics only
                EvalResult.objects.create(
                    **base, error=f"judge: {error}"[:300],
                    hit_at_k=hit_at_k(retrieved, gold_sources),
                    recall_at_k=recall_at_k(retrieved, gold_sources),
                    mrr=mrr(retrieved, gold_sources),
                    latency_ms=result["metrics"].get("latency_ms", 0.0),
                    est_cost_usd=result["metrics"].get("est_cost_usd", 0.0),
                )
                all_clean = False
                continue

            EvalResult.objects.create(
                **base,
                hit_at_k=hit_at_k(retrieved, gold_sources),
                recall_at_k=recall_at_k(retrieved, gold_sources),
                mrr=mrr(retrieved, gold_sources),
                faithfulness=scores["faithfulness"],
                correctness=scores["correctness"],
                latency_ms=result["metrics"].get("latency_ms", 0.0),
                est_cost_usd=result["metrics"].get("est_cost_usd", 0.0),
            )

    run.completed = all_clean
    run.save(update_fields=["completed"])
    return run
