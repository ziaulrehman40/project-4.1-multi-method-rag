"""Index the shared corpus into multimodal chunks.

Indexes the SAME documents as the text techniques so Stage 5 compares fairly: PDFs get
text/table/figure chunks; markdown files get text/table chunks (no figures). Idempotent and
content-hash guarded (content + embedding model): re-embeds only when a document or the model
changes.
"""

import hashlib

from django.core.management.base import BaseCommand

from corpus import iter_documents
from multimodal.embeddings import MODEL
from multimodal.index import build_from_markdown, build_from_pdf
from multimodal.models import MultimodalChunk, MultimodalSource


class Command(BaseCommand):
    help = "Parse, embed, and store the shared corpus for multimodal retrieval."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Rebuild even if unchanged.")

    def handle(self, *args, **options):
        paths = iter_documents()  # shared corpus: PDFs (text+tables+figures) + markdown (text+tables)
        if not paths:
            self.stdout.write("No documents found in sample-docs/; nothing to index.")
            return

        for path in paths:
            content_hash = hashlib.sha256(path.read_bytes() + MODEL.encode()).hexdigest()
            record = MultimodalSource.objects.filter(source=path.name).first()
            if record and record.content_hash == content_hash and not options["force"]:
                self.stdout.write(f"{path.name}: unchanged, skipping.")
                continue

            if path.suffix.lower() == ".pdf":
                count = build_from_pdf(path.name, str(path))
            else:
                count = build_from_markdown(path.name, path.read_text(encoding="utf-8"))
            MultimodalSource.objects.update_or_create(
                source=path.name,
                defaults={"content_hash": content_hash, "chunk_count": count},
            )
            self.stdout.write(f"{path.name}: {count} chunks.")

        by_kind = {k: MultimodalChunk.objects.filter(kind=k).count() for k in ("text", "table", "image")}
        self.stdout.write(f"\nMultimodal chunks: {by_kind}")
