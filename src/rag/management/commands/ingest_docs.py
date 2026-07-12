"""Ingest sample documents into the vector store.

Idempotent and shell-free-friendly: safe to run on every container start. For each
source file it compares a content hash against what was last ingested and re-embeds
only changed (or new) documents, so redeploys don't burn embedding API calls.
"""

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from rag.chunking import recursive_chunks
from rag.embeddings import embed_texts
from rag.models import DocumentChunk, IngestedDocument


SKIP_FILES = {"README.md"}


class Command(BaseCommand):
    help = "Chunk, embed, and store sample documents (idempotent, content-hash guarded)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-ingest every document even if its content is unchanged.",
        )

    def handle(self, *args, **options):
        docs_dir = Path(settings.BASE_DIR) / "sample-docs"
        paths = sorted(p for p in docs_dir.glob("*.md") if p.name not in SKIP_FILES)
        if not paths:
            self.stdout.write("No documents found in sample-docs/; nothing to ingest.")
            return

        for path in paths:
            self._ingest_file(path, force=options["force"])

    def _ingest_file(self, path, force):
        text = path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        record = IngestedDocument.objects.filter(source=path.name).first()
        if record and record.content_hash == content_hash and not force:
            self.stdout.write(f"{path.name}: unchanged, skipping.")
            return

        chunks = recursive_chunks(text)
        if not chunks:
            self.stdout.write(f"{path.name}: no chunks produced, skipping.")
            return

        vectors = embed_texts(chunks)

        with transaction.atomic():
            DocumentChunk.objects.filter(source=path.name).delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        source=path.name,
                        ordinal=index,
                        text=chunk,
                        embedding=vector,
                    )
                    for index, (chunk, vector) in enumerate(zip(chunks, vectors))
                ]
            )
            IngestedDocument.objects.update_or_create(
                source=path.name,
                defaults={"content_hash": content_hash, "chunk_count": len(chunks)},
            )

        self.stdout.write(f"{path.name}: ingested {len(chunks)} chunks.")
