"""Run the evaluation harness over the gold set and print a per-technique summary.

WARNING: this makes many LLM calls (gold x 4 techniques x (answer + judge)). On the Gemini
free tier (~20 requests/day) a full run can hit the daily quota and stop partway — that's
expected; partial results are still stored and shown on the results page (/rag/eval/).
"""

from django.core.management.base import BaseCommand

from evaluation.harness import run_evaluation
from evaluation.reporting import summarise


class Command(BaseCommand):
    help = "Run the RAG evaluation harness over the gold set (stores a versioned run)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "Evaluation makes many LLM calls; the free tier (~20/day) may cap a full run."
        ))
        run = run_evaluation()
        self.stdout.write(f"\nEvalRun #{run.id} ({run.model}) — completed={run.completed}\n")
        self.stdout.write(f"{'technique':12} {'hit@k':>6} {'recall':>7} {'mrr':>5} "
                          f"{'faith':>6} {'correct':>8} {'ms':>7} {'errors':>7}")
        for s in summarise(run):
            self.stdout.write(
                f"{s['technique']:12} {s['hit_at_k']:.2f}   {s['recall_at_k']:.2f}    "
                f"{s['mrr']:.2f}  {s['faithfulness']:.1f}    {s['correctness']:.1f}     "
                f"{s['latency_ms']:.0f}  {s['errors']:>5}"
            )
