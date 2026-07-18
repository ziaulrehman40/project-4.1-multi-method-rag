"""Demo command: answer a question via multimodal retrieval and show the evidence used.

    python manage.py multimodal_query "Which incident category was most common?"

Not used in production; a quick way to eyeball cross-modal retrieval + the vision answer.
"""

from django.core.management.base import BaseCommand

from multimodal.answer import answer


class Command(BaseCommand):
    help = "Answer a question via multimodal retrieval (text + tables + figures)."

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+")
        parser.add_argument("-k", type=int, default=5)

    def handle(self, *args, **options):
        question = " ".join(options["question"])
        result = answer(question, k=options["k"])

        self.stdout.write(f"Q: {question}\n\nANSWER:\n{result['answer']}\n")
        self.stdout.write("EVIDENCE USED:")
        for t in result["trace"]:
            desc = t["context"] if t["kind"] == "image" else t["text"][:70].replace("\n", " ")
            self.stdout.write(f"  [{t['n']}] {t['kind']} (p{t['page']}): {desc}")
        m = result["metrics"]
        self.stdout.write(
            f"\nevidence {m['evidence_used']} · tokens {m['total_tokens']} · "
            f"est. ${m['est_cost_usd']} · {m['latency_ms']} ms · {m['model']}"
        )
