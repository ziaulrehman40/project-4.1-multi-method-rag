"""Demo command: answer a question from the knowledge graph and show the trace.

    python manage.py graph_query "How fast must a breach be reported and to whom?"

Not used in production; a quick way to eyeball graph retrieval + the cited node/edge trace.
"""

from django.core.management.base import BaseCommand

from kg.answer import answer


class Command(BaseCommand):
    help = "Answer a question from the knowledge graph and print the node/edge trace."

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+")
        parser.add_argument("--seeds", type=int, default=5)
        parser.add_argument("--hops", type=int, default=1)

    def handle(self, *args, **options):
        question = " ".join(options["question"])
        result = answer(question, seeds=options["seeds"], hops=options["hops"])

        self.stdout.write(f"Q: {question}\n\nANSWER:\n{result['answer']}\n")
        self.stdout.write("TRACE (edges used):")
        for t in result["trace"]:
            self.stdout.write(
                f"  [{t['n']}] ({t['subject']}) -[{t['predicate']}]-> ({t['object']})"
                f"  — {t['source']}, {t['section']}"
            )
        m = result["metrics"]
        self.stdout.write(
            f"\nedges {m['edges_used']} · tokens {m['total_tokens']} · "
            f"est. ${m['est_cost_usd']} · {m['latency_ms']} ms · {m['model']}"
        )
