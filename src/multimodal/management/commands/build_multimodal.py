"""Index the sample PDFs into multimodal chunks.

Idempotent and content-hash guarded (content + embedding model), like ingest_docs /
build_graph: re-embeds only when a PDF or the model changes.
"""

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from multimodal.embeddings import MODEL
from multimodal.index import build_from_pdf
from multimodal.models import MultimodalChunk, MultimodalSource


class Command(BaseCommand):
    help = "Parse, embed, and store the sample PDFs for multimodal retrieval."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Rebuild even if unchanged.")

    def handle(self, *args, **options):
        docs_dir = Path(settings.BASE_DIR) / "sample-docs"
        paths = sorted(docs_dir.glob("*.pdf"))
        if not paths:
            self.stdout.write("No PDFs found in sample-docs/; nothing to index.")
            return

        for path in paths:
            content_hash = hashlib.sha256(path.read_bytes() + MODEL.encode()).hexdigest()
            record = MultimodalSource.objects.filter(source=path.name).first()
            if record and record.content_hash == content_hash and not options["force"]:
                self.stdout.write(f"{path.name}: unchanged, skipping.")
                continue

            count = build_from_pdf(path.name, str(path))
            MultimodalSource.objects.update_or_create(
                source=path.name,
                defaults={"content_hash": content_hash, "chunk_count": count},
            )
            self.stdout.write(f"{path.name}: {count} chunks.")

        by_kind = {k: MultimodalChunk.objects.filter(kind=k).count() for k in ("text", "table", "image")}
        self.stdout.write(f"\nMultimodal chunks: {by_kind}")
