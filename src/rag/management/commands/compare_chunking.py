"""Compare chunking strategies on the sample documents.

    python manage.py compare_chunking
    python manage.py compare_chunking --max-chars 500 --overlap 100

For each document, runs fixed / recursive / semantic and prints how many chunks each
produces, their size distribution, and a preview of each chunk's start so you can eyeball
coherence. `semantic` calls the embedding API (one call per document), so this costs a few
requests. Read-only: it does not touch the stored vectors.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from rag.chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP, STRATEGIES, chunk
from rag.embeddings import embed_texts


SKIP_FILES = {"README.md"}


class Command(BaseCommand):
    help = "Show how each chunking strategy splits the sample documents."

    def add_arguments(self, parser):
        parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
        parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
        parser.add_argument("--preview", type=int, default=150, help="Preview chars per chunk.")

    def handle(self, *args, **options):
        docs_dir = Path(settings.BASE_DIR) / "sample-docs"
        paths = sorted(p for p in docs_dir.glob("*.md") if p.name not in SKIP_FILES)

        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.stdout.write(f"\n{'=' * 70}\n{path.name}\n{'=' * 70}")
            for strategy in STRATEGIES:
                chunks = chunk(
                    text,
                    strategy=strategy,
                    max_chars=options["max_chars"],
                    overlap=options["overlap"],
                    embed_fn=embed_texts,
                )
                sizes = [len(c) for c in chunks]
                stats = (
                    f"count={len(chunks)} "
                    f"min={min(sizes)} avg={sum(sizes) // len(sizes)} max={max(sizes)}"
                    if sizes
                    else "count=0"
                )
                self.stdout.write(f"\n--- {strategy.upper()}: {stats} ---")
                for i, c in enumerate(chunks):
                    preview = " ".join(c[: options["preview"]].split())
                    self.stdout.write(f"  #{i} ({len(c)}c): {preview}...")
