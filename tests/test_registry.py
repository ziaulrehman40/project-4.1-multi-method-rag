import pytest

from evaluation import registry
from evaluation.registry import run_all, run_technique


def _fake_embedding(question):
    return {"answer": "A [1].",
            "sources": [{"source": "gdpr.md", "ordinal": 4, "text": "72 hours"}],
            "metrics": {"total_tokens": 10, "model": "m"}}


def _fake_graph(question):
    return {"answer": "G [1].",
            "trace": [{"subject": "breach", "predicate": "reported to", "object": "authority",
                       "source": "gdpr.md", "section": "Breaches"}],
            "metrics": {"total_tokens": 12, "model": "m"}}


def test_run_technique_normalises_shape(monkeypatch):
    monkeypatch.setitem(registry.ADAPTERS, "embedding", ("Embedding RAG", registry._embedding))
    monkeypatch.setattr(registry, "_embedding_answer", _fake_embedding)

    result = run_technique("embedding", "q")
    assert result["technique"] == "embedding"
    assert result["answer"] == "A [1]."
    assert result["sources"] == ["gdpr.md"]                # ordered source ids for eval
    assert result["evidence"][0]["label"] == "gdpr.md #4"  # display item
    assert result["error"] is None


def test_run_technique_isolates_failure(monkeypatch):
    def boom(question):
        raise RuntimeError("provider down")

    monkeypatch.setattr(registry, "_graph_answer", boom)
    result = run_technique("graph", "q")
    assert result["error"] and "provider down" in result["error"]
    assert result["answer"] == "" and result["sources"] == []  # empty, not a crash


def test_run_all_runs_every_technique(monkeypatch):
    monkeypatch.setattr(registry, "_embedding_answer", _fake_embedding)
    monkeypatch.setattr(registry, "_graph_answer", _fake_graph)
    monkeypatch.setattr(registry, "_vectorless_answer",
                        lambda q: {"answer": "V", "trace": [{"title": "t", "path": "p", "source": "s.md"}],
                                   "metrics": {}})
    monkeypatch.setattr(registry, "_multimodal_answer",
                        lambda q: {"answer": "M", "trace": [{"kind": "image", "page": 2, "text": "",
                                   "context": "chart", "source": "d.pdf", "image_b64": "AA"}],
                                   "metrics": {}})

    results = run_all("q")
    assert [r["technique"] for r in results] == ["embedding", "graph", "vectorless", "multimodal"]
    assert all(r["error"] is None for r in results)


@pytest.mark.django_db
def test_query_page_renders_result(client, user, monkeypatch):
    from django.urls import reverse
    monkeypatch.setattr(registry, "_embedding_answer", _fake_embedding)

    response = client.post(reverse("rag-query-page"), {"technique": "embedding", "question": "q?"})
    assert response.status_code == 200
    assert b"Embedding RAG" in response.content and b"A [1]." in response.content


@pytest.mark.django_db
def test_compare_page_runs_all(client, user, monkeypatch):
    from django.urls import reverse
    monkeypatch.setattr(registry, "_embedding_answer", _fake_embedding)
    monkeypatch.setattr(registry, "_graph_answer", _fake_graph)
    monkeypatch.setattr(registry, "_vectorless_answer",
                        lambda q: {"answer": "V", "trace": [], "metrics": {}})
    monkeypatch.setattr(registry, "_multimodal_answer",
                        lambda q: {"answer": "M", "trace": [], "metrics": {}})

    response = client.post(reverse("rag-compare-page"), {"question": "q?"})
    assert response.status_code == 200
    assert b"Embedding RAG" in response.content and b"Knowledge Graph" in response.content
