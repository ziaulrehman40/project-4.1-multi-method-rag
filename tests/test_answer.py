from types import SimpleNamespace

import pytest

from rag import answer as answer_mod
from rag.answer import AnswerError, answer
from rag.reranking import RerankOutcome


def _chunk(source, ordinal, text, **scores):
    return SimpleNamespace(source=source, ordinal=ordinal, text=text, **scores)


def _wire(monkeypatch, chunks, reranked=True):
    monkeypatch.setattr(answer_mod, "hybrid_search", lambda q, k: chunks)
    monkeypatch.setattr(
        answer_mod, "rerank", lambda q, cs, top_n: RerankOutcome(chunks=chunks, reranked=reranked)
    )


def test_answer_builds_cited_result_with_metrics(monkeypatch):
    chunks = [_chunk("gdpr.md", 4, "Report a breach within 72 hours.", rerank_score=9.0)]
    _wire(monkeypatch, chunks)
    monkeypatch.setattr(
        answer_mod,
        "_generate",
        lambda prompt: ("Report within 72 hours [1].", {
            "input_tokens": 100, "output_tokens": 20, "total_tokens": 120
        }),
    )

    result = answer("How fast must a breach be reported?")

    assert result["answer"] == "Report within 72 hours [1]."
    assert result["sources"][0] == {
        "n": 1, "source": "gdpr.md", "ordinal": 4,
        "text": "Report a breach within 72 hours.", "score": 9.0, "method": "rerank",
    }
    assert result["rerank_status"] == "applied"
    m = result["metrics"]
    assert m["total_tokens"] == 120 and m["embedding_dim"] == 3072 and m["est_cost_usd"] >= 0


def test_answer_marks_status_failed_when_rerank_fails(monkeypatch):
    chunks = [_chunk("gdpr.md", 0, "text", rrf_score=0.03)]
    _wire(monkeypatch, chunks, reranked=False)
    monkeypatch.setattr(answer_mod, "_generate", lambda p: ("answer", {
        "input_tokens": 1, "output_tokens": 1, "total_tokens": 2
    }))

    result = answer("q")
    assert result["rerank_status"] == "failed"
    assert result["sources"][0]["method"] == "hybrid"  # fell back to retrieval score


def test_answer_can_skip_rerank(monkeypatch):
    chunks = [_chunk("a.md", 0, "t", rrf_score=0.03), _chunk("b.md", 1, "u", rrf_score=0.02)]
    monkeypatch.setattr(answer_mod, "hybrid_search", lambda q, k: chunks)

    def rerank_must_not_run(*a, **k):
        raise AssertionError("rerank must not run when disabled")

    monkeypatch.setattr(answer_mod, "rerank", rerank_must_not_run)
    monkeypatch.setattr(answer_mod, "_generate", lambda p: ("a", {
        "input_tokens": 1, "output_tokens": 1, "total_tokens": 2
    }))

    result = answer("q", top_n=1, rerank_enabled=False)
    assert result["rerank_status"] == "off"
    assert len(result["sources"]) == 1  # top_n applied directly to retrieval order


def test_answer_raises_on_generation_failure(monkeypatch):
    _wire(monkeypatch, [_chunk("a.md", 0, "t", rerank_score=1.0)])

    def boom(prompt):
        raise RuntimeError("provider down")

    monkeypatch.setattr(answer_mod, "_generate", boom)
    with pytest.raises(AnswerError):
        answer("q")
