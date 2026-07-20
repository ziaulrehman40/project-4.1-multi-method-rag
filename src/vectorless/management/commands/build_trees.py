"""Build document section trees from the sample documents (no LLM).

Idempotent and content-hash guarded like the other stages: rebuilds only when a document
changed. Parsing is cheap and LLM-free, but the guard keeps redeploys from needless churn.
"""

import hashlib

from django.core.management.base import BaseCommand

from corpus import document_text, iter_documents
from vectorless.models import DocumentNode, TreeSource
from vectorless.tree import build_document_tree


class Command(BaseCommand):
    help = "Parse the sample documents into section trees (DocumentNode rows)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Rebuild even if unchanged.")

    def handle(self, *args, **options):
        paths = iter_documents()  # shared corpus: markdown + PDF (rendered to text)
        if not paths:
            self.stdout.write("No documents found in sample-docs/; nothing to build.")
            return

        for path in paths:
            text = document_text(path)
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

            record = TreeSource.objects.filter(source=path.name).first()
            if record and record.content_hash == content_hash and not options["force"]:
                self.stdout.write(f"{path.name}: unchanged, skipping.")
                continue

            count = build_document_tree(path.name, text)
            TreeSource.objects.update_or_create(
                source=path.name,
                defaults={"content_hash": content_hash, "node_count": count},
            )
            self.stdout.write(f"{path.name}: {count} nodes.")

        self.stdout.write(f"\nTree: {DocumentNode.objects.count()} nodes total.")
