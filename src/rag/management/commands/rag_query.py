"""Demo command: inspect what vector retrieval returns for a question.

    python manage.py rag_query "How fast must a breach be reported?"

Not used in production; a quick way to eyeball retrieval quality from the CLI.
"""

from django.core.management.base import BaseCommand

from rag.retrieval import retrieve


class Command(BaseCommand):
    help = "Retrieve the nearest document chunks for a question and print them."

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+", help="The question to retrieve for.")
        parser.add_argument("-k", type=int, default=5, help="How many chunks to return.")

    def handle(self, *args, **options):
        question = " ".join(options["question"])
        hits = retrieve(question, k=options["k"])
        if not hits:
            self.stdout.write("No chunks found. Have you run `ingest_docs`?")
            return
        self.stdout.write(f"Query: {question}\n")
        for hit in hits:
            self.stdout.write(
                f"[{hit.distance:.3f}] {hit.source}#{hit.ordinal}: {hit.text[:90]}..."
            )
