"""Demo command: answer a question via vectorless navigation and show the path taken.

    python manage.py tree_query "How fast must a breach be reported?"

Not used in production; a quick way to eyeball which sections the LLM navigated to.
"""

from django.core.management.base import BaseCommand

from vectorless.answer import answer


class Command(BaseCommand):
    help = "Answer a question via document-tree navigation and print the navigation path."

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+")
        parser.add_argument("--max-sections", type=int, default=5)

    def handle(self, *args, **options):
        question = " ".join(options["question"])
        result = answer(question, max_sections=options["max_sections"])

        self.stdout.write(f"Q: {question}\n\nANSWER:\n{result['answer']}\n")
        self.stdout.write("NAVIGATION PATH (sections opened):")
        for t in result["trace"]:
            self.stdout.write(f"  [{t['n']}] {t['path']}")
        m = result["metrics"]
        self.stdout.write(
            f"\nsections {m['sections_opened']} · tokens {m['total_tokens']} · "
            f"est. ${m['est_cost_usd']} · {m['latency_ms']} ms · {m['model']}"
        )
