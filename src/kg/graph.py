"""Persist extracted triples into the entity/relationship graph.

Entity resolution here is exact-canonical-match (`get_or_create` by canonical name), which
collapses same-worded entities to one node. Fuzzier merging (synonyms/aliases) is a possible
later enhancement.
"""

from django.db import transaction

from rag.embeddings import embed_texts  # reuse Stage 1 embedding client

from .extraction import extract_triples
from .models import Entity, Relationship


def edge_sentence(relationship):
    """Render an edge as a natural-language fact for embedding: 'subject predicate object'."""
    return f"{relationship.subject.name} {relationship.predicate} {relationship.object.name}"


def _prune_orphan_entities():
    # Remove entities left with no edges after a rebuild (never referenced anywhere).
    Entity.objects.filter(outgoing__isnull=True, incoming__isnull=True).delete()


def persist_triples(triples, source):
    """Upsert entities and relationships for `source`; returns the relationship count.

    Rebuilds this source's edges (delete then recreate) so re-running is idempotent.
    """
    with transaction.atomic():
        Relationship.objects.filter(source=source).delete()
        for triple in triples:
            subject, _ = Entity.objects.get_or_create(name=triple.subject)
            obj, _ = Entity.objects.get_or_create(name=triple.object)
            Relationship.objects.get_or_create(
                subject=subject,
                predicate=triple.predicate,
                object=obj,
                source=source,
                defaults={"section": triple.section},
            )
        _prune_orphan_entities()
    return Relationship.objects.filter(source=source).count()


def embed_relationships(source):
    """Embed every edge of `source` (as a sentence) for semantic seed-finding."""
    relationships = list(
        Relationship.objects.filter(source=source).select_related("subject", "object")
    )
    if not relationships:
        return
    vectors = embed_texts([edge_sentence(r) for r in relationships])
    for relationship, vector in zip(relationships, vectors):
        relationship.embedding = vector
    Relationship.objects.bulk_update(relationships, ["embedding"])


def build_from_text(text, source):
    """Extract triples from `text`, persist them, and embed the edges. Returns edge count."""
    triples = extract_triples(text, source)
    count = persist_triples(triples, source)
    embed_relationships(source)
    return count
