import pytest

from kg import extraction
from kg.extraction import ExtractionError, Triple, _canonical, extract_triples
from kg.graph import persist_triples
from kg.models import Entity, Relationship


# ------------------------------------------------------------------- extraction (no DB)

def test_canonical_lowercases_and_collapses_whitespace():
    assert _canonical("  Data   Controller ") == "data controller"


def test_extract_parses_canonicalises_and_tags_provenance(monkeypatch):
    raw = (
        '[{"subject": "Data Controller", "predicate": "Must Report To", '
        '"object": "Supervisory Authority", "section": "Breaches"}]'
    )
    monkeypatch.setattr(extraction, "_generate_json", lambda prompt: raw)

    triples = extract_triples("some text", source="gdpr.md")

    assert triples == [
        Triple("data controller", "must report to", "supervisory authority", "gdpr.md", "Breaches")
    ]


def test_extract_skips_incomplete_triples(monkeypatch):
    raw = '[{"subject": "a", "predicate": "rel", "object": "b"}, {"subject": "x", "object": "y"}]'
    monkeypatch.setattr(extraction, "_generate_json", lambda prompt: raw)

    triples = extract_triples("t", source="s.md")
    assert len(triples) == 1  # the one missing a predicate is dropped


def test_extract_raises_on_unparseable_output(monkeypatch):
    monkeypatch.setattr(extraction, "_generate_json", lambda prompt: "not json")
    with pytest.raises(ExtractionError):
        extract_triples("t", source="s.md")


def test_generate_json_retries_transient_errors(monkeypatch):
    from types import SimpleNamespace

    calls = {"n": 0}

    def make_client(api_key):
        def generate_content(model, contents, config):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("503 UNAVAILABLE: high demand")  # transient
            return SimpleNamespace(text="[]")

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    monkeypatch.setattr(extraction.genai, "Client", make_client)
    monkeypatch.setattr(extraction.time, "sleep", lambda _s: None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    assert extraction._generate_json("prompt") == "[]"
    assert calls["n"] == 2  # failed once, retried, succeeded


# ------------------------------------------------------------------ persistence (DB)

pytestmark_db = pytest.mark.django_db


@pytest.mark.django_db
def test_persist_creates_deduped_entities_and_edges():
    triples = [
        Triple("breach", "reported to", "authority", "gdpr.md", "Breaches"),
        Triple("breach", "reported within", "72 hours", "gdpr.md", "Breaches"),
    ]
    count = persist_triples(triples, source="gdpr.md")

    assert count == 2
    # "breach" appears in both triples but is a single node.
    assert Entity.objects.filter(name="breach").count() == 1
    assert Entity.objects.count() == 3  # breach, authority, 72 hours
    edge = Relationship.objects.get(predicate="reported to")
    assert edge.source == "gdpr.md" and edge.section == "Breaches"


@pytest.mark.django_db
def test_persist_is_idempotent_per_source():
    triples = [Triple("a", "rel", "b", "doc.md", "S")]
    persist_triples(triples, source="doc.md")
    persist_triples(triples, source="doc.md")  # re-run

    assert Relationship.objects.filter(source="doc.md").count() == 1
    assert Entity.objects.count() == 2


@pytest.mark.django_db
def test_rebuild_prunes_orphaned_entities():
    persist_triples([Triple("old", "rel", "gone", "doc.md", "")], source="doc.md")
    # Rebuild the same source with a different fact: 'old'/'gone' are now orphaned.
    persist_triples([Triple("new", "rel", "fresh", "doc.md", "")], source="doc.md")

    names = set(Entity.objects.values_list("name", flat=True))
    assert names == {"new", "fresh"}
