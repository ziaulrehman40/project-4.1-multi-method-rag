"""Demo command: inspect what retrieval returns for a question.

    python manage.py rag_query "How fast must a breach be reported?"
    python manage.py rag_query "Article 33 breach" --method sparse
    python manage.py rag_query "..." --method dense

Not used in production; a quick way to eyeball and compare retrieval methods from the CLI.
"""

from django.core.management.base import BaseCommand

from rag.retrieval import search


class Command(BaseCommand):
    help = "Retrieve the nearest document chunks for a question and print them."

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+", help="The question to retrieve for.")
        parser.add_argument("-k", type=int, default=5, help="How many chunks to return.")
        parser.add_argument(
            "--method",
            choices=["dense", "sparse", "hybrid"],
            default="hybrid",
        )

    def handle(self, *args, **options):
        question = " ".join(options["question"])
        hits = search(question, method=options["method"], k=options["k"])
        if not hits:
            self.stdout.write("No chunks found. Have you run `ingest_docs`?")
            return
        self.stdout.write(f"Query ({options['method']}): {question}\n")
        for hit in hits:
            # Different methods annotate a different score; show whichever is present.
            if hasattr(hit, "rrf_score"):
                score = f"rrf {hit.rrf_score:.4f}"
            elif hasattr(hit, "distance"):
                score = f"distance {hit.distance:.3f}"
            else:
                score = f"rank {hit.rank:.3f}"
            snippet = hit.text[:300] + ("..." if len(hit.text) > 300 else "")
            self.stdout.write(f"\n[{score}] {hit.source} (chunk #{hit.ordinal})\n{snippet}")
