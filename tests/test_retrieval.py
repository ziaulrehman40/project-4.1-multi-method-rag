import pytest

from rag.models import DocumentChunk
from rag.retrieval import retrieve


pytestmark = pytest.mark.django_db


def _unit(index, dim=3072):
    """A 3072-dim one-hot vector (unit length) with a 1.0 at `index`."""
    vector = [0.0] * dim
    vector[index] = 1.0
    return vector


def test_retrieve_returns_nearest_chunk_first(monkeypatch):
    DocumentChunk.objects.create(source="a.md", ordinal=0, text="about breaches", embedding=_unit(0))
    DocumentChunk.objects.create(source="b.md", ordinal=0, text="about payments", embedding=_unit(1))
    DocumentChunk.objects.create(source="c.md", ordinal=0, text="about access", embedding=_unit(2))

    # Query vector points mostly along axis 0 -> chunk "a.md" is closest by cosine.
    query_vector = [0.9, 0.1] + [0.0] * 3070
    monkeypatch.setattr("rag.retrieval.embed_query", lambda _q: query_vector)

    hits = retrieve("anything", k=2)

    assert [h.source for h in hits] == ["a.md", "b.md"]
    assert hits[0].distance < hits[1].distance  # nearer chunk has smaller cosine distance


def test_retrieve_respects_k(monkeypatch):
    for i in range(5):
        DocumentChunk.objects.create(source=f"{i}.md", ordinal=0, text=f"chunk {i}", embedding=_unit(i))
    monkeypatch.setattr("rag.retrieval.embed_query", lambda _q: _unit(0))

    assert len(retrieve("q", k=3)) == 3
