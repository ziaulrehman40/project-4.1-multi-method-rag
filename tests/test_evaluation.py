import pytest

from evaluation import harness as harness_mod
from evaluation import judge as judge_mod
from evaluation.harness import run_evaluation
from evaluation.metrics import hit_at_k, mrr, recall_at_k
from evaluation.models import EvalResult, EvalRun
from evaluation.reporting import by_category, summarise


# ------------------------------------------------------------------------- metrics

def test_hit_recall_mrr():
    assert hit_at_k(["a.md", "b.md"], ["b.md"]) == 1.0
    assert hit_at_k(["a.md"], ["b.md"]) == 0.0
    assert recall_at_k(["a.md", "b.md"], ["a.md", "c.md"]) == 0.5   # 1 of 2 gold retrieved
    assert mrr(["x.md", "gold.md"], ["gold.md"]) == 0.5             # first relevant at rank 2
    assert mrr(["gold.md", "x.md"], ["gold.md"]) == 1.0
    assert mrr(["x.md"], ["gold.md"]) == 0.0


# --------------------------------------------------------------- harness (mocked LLM)

_GOLD = [{"type": "semantic", "question": "q?", "expected_answer": "ref",
          "expected_sources": ["gdpr-excerpt.md"]}]


@pytest.mark.django_db
def test_run_evaluation_scores_and_stores(monkeypatch):
    def fake_run_all(question):
        return [{"technique": "embedding", "label": "Embedding RAG", "answer": "A",
                 "evidence": [{"detail": "e"}], "sources": ["gdpr-excerpt.md"],
                 "metrics": {"latency_ms": 12.0, "est_cost_usd": 0.001}, "error": None}]

    monkeypatch.setattr(harness_mod, "run_all", fake_run_all)
    monkeypatch.setattr(harness_mod, "judge",
                        lambda q, ref, cand, ev: {"faithfulness": 5.0, "correctness": 4.0, "reasoning": "ok"})

    run = run_evaluation(gold=_GOLD)

    assert run.completed is True
    result = EvalResult.objects.get(run=run, technique="embedding")
    assert result.hit_at_k == 1.0 and result.mrr == 1.0
    assert result.faithfulness == 5.0 and result.correctness == 4.0


@pytest.mark.django_db
def test_run_evaluation_records_technique_error(monkeypatch):
    def failing_run_all(question):
        return [{"technique": "graph", "label": "Knowledge Graph", "answer": "",
                 "evidence": [], "sources": [], "metrics": {}, "error": "quota exhausted"}]

    monkeypatch.setattr(harness_mod, "run_all", failing_run_all)
    run = run_evaluation(gold=_GOLD)

    assert run.completed is False  # a cell errored
    assert EvalResult.objects.get(run=run).error == "quota exhausted"


@pytest.mark.django_db
def test_summarise_and_by_category(monkeypatch):
    monkeypatch.setattr(harness_mod, "run_all", lambda q: [
        {"technique": "embedding", "label": "E", "answer": "A", "evidence": [{"detail": "e"}],
         "sources": ["gdpr-excerpt.md"], "metrics": {"latency_ms": 10, "est_cost_usd": 0}, "error": None}])
    monkeypatch.setattr(harness_mod, "judge",
                        lambda *a: {"faithfulness": 5.0, "correctness": 3.0, "reasoning": ""})
    run = run_evaluation(gold=_GOLD)

    summary = summarise(run)
    assert summary[0]["technique"] == "embedding" and summary[0]["correctness"] == 3.0
    cats = by_category(run)
    assert cats["rows"][0]["type"] == "semantic"


@pytest.mark.django_db
def test_eval_page_renders_latest_run(client, user):
    from django.urls import reverse
    run = EvalRun.objects.create(model="m", completed=True)
    EvalResult.objects.create(run=run, technique="embedding", question="q", qtype="semantic",
                              hit_at_k=1.0, recall_at_k=1.0, mrr=1.0, faithfulness=5.0, correctness=4.0)

    response = client.get(reverse("rag-eval-page"))
    assert response.status_code == 200
    assert b"embedding" in response.content and b"semantic" in response.content


def test_judge_parses_scores(monkeypatch):
    from unittest.mock import Mock

    from llm import Generation

    provider = Mock()
    provider.generate_json.return_value = (
        {"faithfulness": 4, "correctness": 5, "reasoning": "good"}, Generation(text=""))
    monkeypatch.setattr(judge_mod, "get_generation_provider", lambda: provider)

    scores = judge_mod.judge("q", "ref", "cand", "evidence")
    assert scores["faithfulness"] == 4.0 and scores["correctness"] == 5.0
