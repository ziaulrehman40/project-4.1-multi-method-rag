"""Persist extracted triples into the entity/relationship graph.

Entity resolution here is exact-canonical-match (`get_or_create` by canonical name), which
collapses same-worded entities to one node. Fuzzier merging (synonyms/aliases) is a possible
later enhancement.
"""

from django.db import transaction

from .extraction import extract_triples
from .models import Entity, Relationship


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


def build_from_text(text, source):
    """Extract triples from `text` and persist them. Returns the relationship count."""
    triples = extract_triples(text, source)
    return persist_triples(triples, source)
