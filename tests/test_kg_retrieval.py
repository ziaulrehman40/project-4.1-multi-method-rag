import pytest

from kg import answer as answer_mod
from kg.answer import answer
from kg.graph import edge_sentence
from kg.models import Entity, Relationship
from kg.retrieval import graph_search


pytestmark = pytest.mark.django_db


def _unit(index, dim=3072):
    vector = [0.0] * dim
    vector[index] = 1.0
    return vector


def _edge(subj, pred, obj, axis, source="doc.md", section="S"):
    s, _ = Entity.objects.get_or_create(name=subj)
    o, _ = Entity.objects.get_or_create(name=obj)
    return Relationship.objects.create(
        subject=s, predicate=pred, object=o, source=source, section=section,
        embedding=_unit(axis),
    )


def test_edge_sentence_reads_subject_predicate_object():
    edge = _edge("breach", "reported to", "authority", 0)
    assert edge_sentence(edge) == "breach reported to authority"


def test_graph_search_seeds_by_similarity_then_expands(monkeypatch):
    # Seed edge points along axis 0; a connected edge shares the "breach" node.
    seed = _edge("breach", "reported within", "72 hours", 0)
    connected = _edge("breach", "reported to", "authority", 1)   # shares 'breach'
    _edge("unrelated", "is", "island", 2)                        # not connected

    # Query embeds closest to the seed edge (axis 0).
    monkeypatch.setattr("kg.retrieval.embed_query", lambda _q: _unit(0))

    edges = graph_search("how fast to report a breach", seeds=1, hops=1)
    ids = [e.id for e in edges]

    assert edges[0].id == seed.id            # seed first (most similar)
    assert connected.id in ids               # 1-hop expansion picked up the neighbour
    # 'unrelated' shares no node with the seed, so it is not pulled in.
    assert all(e.subject.name != "unrelated" for e in edges)


def test_graph_search_respects_max_edges(monkeypatch):
    for i in range(6):
        _edge("hub", f"rel{i}", f"obj{i}", i)  # all share the 'hub' node
    monkeypatch.setattr("kg.retrieval.embed_query", lambda _q: _unit(0))

    edges = graph_search("q", seeds=1, hops=1, max_edges=3)
    assert len(edges) == 3


def test_answer_builds_cited_trace(monkeypatch):
    _edge("breach", "reported within", "72 hours", 0)
    monkeypatch.setattr("kg.retrieval.embed_query", lambda _q: _unit(0))
    monkeypatch.setattr(
        answer_mod, "_generate",
        lambda prompt: ("Report within 72 hours [1].", {
            "input_tokens": 50, "output_tokens": 10, "total_tokens": 60
        }),
    )

    result = answer("how fast?", seeds=1, hops=0)

    assert result["answer"] == "Report within 72 hours [1]."
    assert result["trace"][0]["subject"] == "breach"
    assert result["trace"][0]["source"] == "doc.md"
    assert result["metrics"]["edges_used"] == 1 and result["metrics"]["total_tokens"] == 60
