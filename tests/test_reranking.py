from types import SimpleNamespace

from rag import reranking
from rag.reranking import rerank


def _chunks(*texts):
    # Lightweight stand-ins; rerank only needs `.text` and sets `.rerank_score`. No DB.
    return [SimpleNamespace(text=t) for t in texts]


def test_rerank_reorders_by_score_and_keeps_top_n(monkeypatch):
    chunks = _chunks("A", "B", "C")
    # B most relevant, then C, then A.
    monkeypatch.setattr(reranking, "_score_with_gemini", lambda q, cs: [3.0, 9.0, 5.0])

    outcome = rerank("q", chunks, top_n=2)

    assert outcome.reranked is True
    assert [c.text for c in outcome.chunks] == ["B", "C"]
    assert outcome.chunks[0].rerank_score == 9.0


def test_rerank_falls_back_and_flags_on_failure(monkeypatch, caplog):
    chunks = _chunks("A", "B", "C")

    def boom(q, cs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(reranking, "_score_with_gemini", boom)

    with caplog.at_level("WARNING"):
        outcome = rerank("q", chunks, top_n=2)

    # Not silent: flagged as not-reranked, note set, and a warning was logged.
    assert outcome.reranked is False
    assert outcome.note and "provider unavailable" in outcome.note
    assert [c.text for c in outcome.chunks] == ["A", "B"]  # original retrieval order preserved
    assert any("rerank.fallback" in r.message for r in caplog.records)


def test_rerank_empty_input():
    outcome = rerank("q", [], top_n=3)
    assert outcome.chunks == [] and outcome.reranked is True
