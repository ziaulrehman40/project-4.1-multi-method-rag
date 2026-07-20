"""Establish an evaluation run on deploy (Render free tier has no shell).

The `evaluate` command is expensive (~gold x 4 techniques x (answer + judge) LLM calls), so we
do NOT re-run it on every redeploy. This runs it only when there's something to establish:

- no EvalRun exists yet (first deploy → populate the results page), or
- EVAL_VERSION is set and differs from the stored marker (bump it to force a fresh run, e.g.
  after changing the corpus or the provider). Same one-shot latch as `apply_rebuild`.

Wired into the Docker CMD as a BACKGROUND, non-fatal step: it never delays gunicorn binding
and never crash-loops the container — a failed/partial run just shows on the results page.
"""

import os

from django.core.management.base import BaseCommand

from evaluation.harness import run_evaluation
from evaluation.models import EvalRun
from kg.models import RebuildMarker


MARKER_KEY = "eval_version"


class Command(BaseCommand):
    help = "Run the evaluation once if none exists yet (or when EVAL_VERSION changes)."

    def handle(self, *args, **options):
        version = os.environ.get("EVAL_VERSION", "").strip()
        marker = RebuildMarker.objects.filter(key=MARKER_KEY).first()
        version_satisfied = bool(version) and marker is not None and marker.value == version

        if EvalRun.objects.exists() and (not version or version_satisfied):
            self.stdout.write("Evaluation run already present; skipping.")
            return

        self.stdout.write("Establishing an evaluation run…")
        try:
            run = run_evaluation()
        except Exception as error:  # never let a deploy-time eval crash startup
            self.stderr.write(self.style.WARNING(f"ensure_eval: evaluation failed ({error}); skipping."))
            return

        if version:
            RebuildMarker.objects.update_or_create(key=MARKER_KEY, defaults={"value": version})
        self.stdout.write(self.style.SUCCESS(
            f"EvalRun #{run.id} ({run.model}) completed={run.completed}."))
