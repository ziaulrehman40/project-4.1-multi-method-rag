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


# (Retry/backoff now lives in the llm provider and is covered by tests/test_llm.py.)


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


# ----------------------------------------------------- apply_rebuild (one-time reset latch)

@pytest.mark.django_db
def test_apply_rebuild_is_a_one_shot_latch(monkeypatch):
    """REBUILD_VERSION gates a single forced graph rebuild: unset = no-op, a new value forces
    once and records itself, and re-running the same value skips (the prod one-time reset)."""
    from django.core.management import call_command

    from kg.management.commands import apply_rebuild as cmd
    from kg.models import RebuildMarker

    forced = {"n": 0}
    monkeypatch.setattr(cmd, "call_command",
                        lambda name, **opts: forced.__setitem__("n", forced["n"] + 1))

    # 1) Unset: nothing forced, no marker written.
    monkeypatch.delenv("REBUILD_VERSION", raising=False)
    call_command("apply_rebuild")
    assert forced["n"] == 0 and not RebuildMarker.objects.exists()

    # 2) New value: forces exactly once and records the marker.
    monkeypatch.setenv("REBUILD_VERSION", "openai-1")
    call_command("apply_rebuild")
    assert forced["n"] == 1
    assert RebuildMarker.objects.get(key=cmd.MARKER_KEY).value == "openai-1"

    # 3) Same value again: already applied, so it skips (no second force).
    call_command("apply_rebuild")
    assert forced["n"] == 1
