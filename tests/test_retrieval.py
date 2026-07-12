import pytest
from django.contrib.postgres.search import SearchVector

from rag.models import DocumentChunk
from rag.retrieval import _rrf, dense_search, hybrid_search, sparse_search


pytestmark = pytest.mark.django_db


def _unit(index, dim=3072):
    """A 3072-dim one-hot vector with a 1.0 at `index`."""
    vector = [0.0] * dim
    vector[index] = 1.0
    return vector


def _seed(source, text, axis):
    return DocumentChunk.objects.create(source=source, ordinal=0, text=text, embedding=_unit(axis))


# --------------------------------------------------------------------------------- RRF

def test_rrf_orders_by_fused_rank():
    # The worked example from the lesson: dense=[A,B,C], sparse=[C,A,D].
    fused = _rrf([["A", "B", "C"], ["C", "A", "D"]], k=0)
    assert [item for item, _ in fused] == ["A", "C", "B", "D"]
    scores = dict(fused)
    assert scores["A"] == pytest.approx(1.5)          # 1/1 + 1/2
    assert scores["C"] == pytest.approx(1 / 3 + 1)    # 1/3 + 1/1


# ------------------------------------------------------------------------------- dense

def test_dense_search_returns_nearest_first(monkeypatch):
    _seed("a.md", "about breaches", 0)
    _seed("b.md", "about payments", 1)
    monkeypatch.setattr("rag.retrieval.embed_query", lambda _q: [0.9, 0.1] + [0.0] * 3070)

    hits = dense_search("anything", k=2)
    assert [h.source for h in hits] == ["a.md", "b.md"]
    assert hits[0].distance < hits[1].distance


# ------------------------------------------------------------------------------ sparse

def test_sparse_search_finds_keyword_match():
    _seed("a.md", "A personal data breach must be reported within 72 hours.", 0)
    _seed("b.md", "Payment card data must be encrypted at rest.", 1)
    DocumentChunk.objects.update(search_vector=SearchVector("text"))

    hits = sparse_search("breach reporting deadline", k=3)
    assert hits and hits[0].source == "a.md"
    # A query with no matching keywords returns nothing (not a fuzzy match).
    assert sparse_search("xylophone", k=3) == []


# ------------------------------------------------------------------------------ hybrid

def test_hybrid_merges_dense_and_sparse(monkeypatch):
    a = _seed("a.md", "breach reporting within 72 hours", 0)
    b = _seed("b.md", "payment card data encryption", 1)
    DocumentChunk.objects.update(search_vector=SearchVector("text"))
    # Query embeds closest to A (dense) while the keyword "payment" matches B (sparse).
    monkeypatch.setattr("rag.retrieval.embed_query", lambda _q: _unit(0))

    hits = hybrid_search("payment", k=5)
    ids = [h.id for h in hits]
    assert a.id in ids and b.id in ids  # dense surfaced A, sparse surfaced B
    scores = [h.rrf_score for h in hits]
    assert scores == sorted(scores, reverse=True)  # ordered by fused score
