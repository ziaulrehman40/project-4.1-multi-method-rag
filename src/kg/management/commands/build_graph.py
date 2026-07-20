"""Build the knowledge graph from the sample documents.

Idempotent and shell-free-friendly (same pattern as ingest_docs): per document it compares a
hash of content + model, and only re-extracts when something changed — so redeploys don't
burn LLM calls but content/model changes do rebuild.
"""

import hashlib

from django.core.management.base import BaseCommand

from corpus import document_text, iter_documents
from llm import active_generation_model

from kg.extraction import ExtractionError, extract_triples
from kg.graph import embed_relationships, persist_triples
from kg.models import Entity, GraphSource, Relationship


class Command(BaseCommand):
    help = "Extract triples from the sample documents and build the knowledge graph."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Rebuild even if unchanged.")

    def handle(self, *args, **options):
        paths = iter_documents()  # shared corpus: markdown + PDF (rendered to text)
        if not paths:
            self.stdout.write("No documents found in sample-docs/; nothing to build.")
            return

        for path in paths:
            text = document_text(path)
            # Include the generation model so a model/provider change re-extracts.
            fingerprint = f"{text}::{active_generation_model()}"
            content_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

            record = GraphSource.objects.filter(source=path.name).first()
            if record and record.content_hash == content_hash and not options["force"]:
                self.stdout.write(f"{path.name}: unchanged, skipping.")
                continue

            try:
                triples = extract_triples(text, source=path.name)
            except ExtractionError as error:
                self.stderr.write(self.style.WARNING(f"{path.name}: {error}; skipping."))
                continue

            count = persist_triples(triples, source=path.name)
            embed_relationships(source=path.name)  # embed edges for semantic seed-finding
            GraphSource.objects.update_or_create(
                source=path.name,
                defaults={"content_hash": content_hash, "triple_count": count},
            )
            self.stdout.write(f"{path.name}: {count} relationships.")

        self.stdout.write(
            f"\nGraph: {Entity.objects.count()} entities, "
            f"{Relationship.objects.count()} relationships."
        )
