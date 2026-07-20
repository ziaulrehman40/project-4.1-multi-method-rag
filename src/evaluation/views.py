from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .models import EvalRun
from .registry import ADAPTERS, run_all, run_technique, technique_choices
from .reporting import by_category, summarise


@login_required
@require_http_methods(["GET", "POST"])
def query_page(request):
    """Run one technique against a question and inspect it in full."""
    selected = request.POST.get("technique", "embedding")
    question = request.POST.get("question", "").strip()[: settings.MAX_QUESTION_CHARS]  # guardrail
    result = None
    if request.method == "POST" and question and selected in ADAPTERS:
        result = run_technique(selected, question)
    return render(request, "evaluation/query.html", {
        "choices": technique_choices(), "selected": selected,
        "question": question, "result": result,
    })


@login_required
@require_http_methods(["GET", "POST"])
def compare_page(request):
    """Run the same question through all four techniques, side by side."""
    question = request.POST.get("question", "").strip()[: settings.MAX_QUESTION_CHARS]  # guardrail
    results = run_all(question) if request.method == "POST" and question else None
    return render(request, "evaluation/compare.html", {
        "question": question, "results": results,
    })


@login_required
@require_GET
def eval_results(request):
    """Show the latest evaluation run (read-only; the run itself is a management command,
    so we never trigger the expensive eval on a page load)."""
    run = EvalRun.objects.order_by("-created_at").first()
    return render(request, "evaluation/eval.html", {
        "run": run,
        "summary": summarise(run) if run else None,
        "categories": by_category(run) if run else None,
    })
