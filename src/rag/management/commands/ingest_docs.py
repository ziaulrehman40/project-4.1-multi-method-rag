"""Ingest sample documents into the vector store.

Idempotent and shell-free-friendly: safe to run on every container start. For each
source file it compares a hash of (content + chunking params) against what was last
ingested and re-embeds only when the content or the chunking config changed, so
redeploys don't burn embedding API calls but switching strategy does re-ingest.

Defaults to the `recursive` strategy: `semantic` embeds every sentence to find
boundaries, which would quickly exhaust the free-tier embedding quota.
"""

import hashlib
from pathlib import Path

from django.conf import settings
from django.contrib.postgres.search import SearchVector
from django.core.management.base import BaseCommand
from django.db import transaction

from rag.chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP, STRATEGIES, chunk
from rag.embeddings import embed_texts
from rag.models import DocumentChunk, IngestedDocument


SKIP_FILES = {"README.md"}


class Command(BaseCommand):
    help = "Chunk, embed, and store sample documents (idempotent, hash-guarded)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Re-ingest even if unchanged.")
        parser.add_argument("--strategy", choices=STRATEGIES, default="recursive")
        parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
        parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)

    def handle(self, *args, **options):
        docs_dir = Path(settings.BASE_DIR) / "sample-docs"
        paths = sorted(p for p in docs_dir.glob("*.md") if p.name not in SKIP_FILES)
        if not paths:
            self.stdout.write("No documents found in sample-docs/; nothing to ingest.")
            return

        for path in paths:
            self._ingest_file(path, options)

    def _ingest_file(self, path, options):
        text = path.read_text(encoding="utf-8")
        # Fold the chunking config into the hash so changing strategy/size re-ingests.
        fingerprint = f"{text}::{options['strategy']}:{options['max_chars']}:{options['overlap']}"
        content_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

        record = IngestedDocument.objects.filter(source=path.name).first()
        if record and record.content_hash == content_hash and not options["force"]:
            self.stdout.write(f"{path.name}: unchanged, skipping.")
            return

        chunks = chunk(
            text,
            strategy=options["strategy"],
            max_chars=options["max_chars"],
            overlap=options["overlap"],
            embed_fn=embed_texts,  # only used by the semantic strategy
        )
        if not chunks:
            self.stdout.write(f"{path.name}: no chunks produced, skipping.")
            return

        vectors = embed_texts(chunks)

        with transaction.atomic():
            DocumentChunk.objects.filter(source=path.name).delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(source=path.name, ordinal=index, text=chunk_text, embedding=vector)
                    for index, (chunk_text, vector) in enumerate(zip(chunks, vectors))
                ]
            )
            # Build the full-text (sparse) vector from the stored text for keyword search.
            DocumentChunk.objects.filter(source=path.name).update(
                search_vector=SearchVector("text")
            )
            IngestedDocument.objects.update_or_create(
                source=path.name,
                defaults={"content_hash": content_hash, "chunk_count": len(chunks)},
            )

        self.stdout.write(
            f"{path.name}: ingested {len(chunks)} chunks ({options['strategy']}, "
            f"max_chars={options['max_chars']})."
        )
