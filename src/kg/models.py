from django.db import models
from pgvector.django import VectorField


class Entity(models.Model):
    """A node in the knowledge graph. `name` is the canonical (lowercased) form, so the
    same entity referenced with different wording collapses to one node (entity resolution).
    """

    name = models.CharField(max_length=300, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Relationship(models.Model):
    """An edge: subject --[predicate]--> object, with provenance (source doc + section)."""

    subject = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="outgoing")
    predicate = models.CharField(max_length=200)
    object = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="incoming")
    source = models.CharField(max_length=200)
    section = models.CharField(max_length=300, blank=True)
    # Embedding of the edge as a sentence ("subject predicate object"), for semantic
    # seed-finding at query time. Populated at build; nullable until then. No ANN index
    # (small graph -> exact cosine scan; pgvector indexes also cap at 2000 dims < 3072).
    embedding = VectorField(dimensions=3072, null=True)

    class Meta:
        # Same fact from the same document is stored once.
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "predicate", "object", "source"],
                name="unique_relationship_per_source",
            )
        ]

    def __str__(self):
        return f"({self.subject}) -[{self.predicate}]-> ({self.object})"


class GraphSource(models.Model):
    """Idempotency record: skip re-extracting a document whose content + model are unchanged."""

    source = models.CharField(max_length=200, unique=True)
    content_hash = models.CharField(max_length=64)
    triple_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source} ({self.triple_count} triples)"


class RebuildMarker(models.Model):
    """Durable, shell-free "one-time op" latch. Prod has no shell, so a forced rebuild is
    triggered by bumping the REBUILD_VERSION env var: `apply_rebuild` compares it to the
    stored value here and, on a mismatch, force-rebuilds the generation-derived artifact
    (the knowledge graph) exactly once — surviving restarts and replicas."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=200)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}={self.value}"
