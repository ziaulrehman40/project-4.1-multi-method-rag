from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .registry import ADAPTERS, run_all, run_technique, technique_choices


@login_required
@require_http_methods(["GET", "POST"])
def query_page(request):
    """Run one technique against a question and inspect it in full."""
    selected = request.POST.get("technique", "embedding")
    question = request.POST.get("question", "").strip()
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
    question = request.POST.get("question", "").strip()
    results = run_all(question) if request.method == "POST" and question else None
    return render(request, "evaluation/compare.html", {
        "question": question, "results": results,
    })
