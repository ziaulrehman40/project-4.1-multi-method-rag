"""Env-gated, one-time forced rebuild of generation-derived artifacts.

Prod (Render) has no shell, so we can't run `build_graph --force` by hand. Instead, bump the
`REBUILD_VERSION` env var to a new value: on the next boot this command notices the value
differs from the stored marker, force-rebuilds the *only* generation-derived artifact — the
knowledge graph — and records the new value so subsequent restarts/replicas don't re-force.

Deliberately NOT forced here: text/multimodal embeddings and section trees. Embeddings stay on
Gemini (dimension-locked) and are unaffected by a generation-provider swap, so re-embedding
would only waste Gemini quota. The graph is generation-derived (LLM triple extraction), so it
is the one thing a provider swap should re-run for a fair cross-technique comparison.
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from kg.models import RebuildMarker


MARKER_KEY = "rebuild_version"


class Command(BaseCommand):
    help = "One-time forced rebuild of the knowledge graph, gated by REBUILD_VERSION."

    def handle(self, *args, **options):
        version = os.environ.get("REBUILD_VERSION", "").strip()
        if not version:
            self.stdout.write("REBUILD_VERSION not set; no one-time reset requested.")
            return

        marker = RebuildMarker.objects.filter(key=MARKER_KEY).first()
        if marker and marker.value == version:
            self.stdout.write(f"One-time rebuild '{version}' already applied; skipping.")
            return

        self.stdout.write(
            self.style.WARNING(f"Applying one-time rebuild '{version}': "
                               "forcing knowledge-graph re-extraction…")
        )
        call_command("build_graph", force=True)
        RebuildMarker.objects.update_or_create(key=MARKER_KEY, defaults={"value": version})
        self.stdout.write(self.style.SUCCESS(f"One-time rebuild '{version}' complete."))
