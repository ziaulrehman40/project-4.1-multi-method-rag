from django.db import models


class DocumentNode(models.Model):
    """A node in a document's section tree (adjacency list).

    The document itself is the root (level 0); markdown headings nest beneath it by level.
    The LLM navigates this tree at query time instead of matching embeddings. `path` is the
    breadcrumb used as the citation (we have no page numbers in markdown).
    """

    source = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    title = models.CharField(max_length=300)
    level = models.IntegerField()  # 0 = document root, 1 = '#', 2 = '##', ...
    content = models.TextField(blank=True)
    path = models.CharField(max_length=600)  # e.g. "gdpr.md › Personal Data Breaches"
    position = models.IntegerField(default=0)  # document reading order (also sibling order)

    class Meta:
        ordering = ["source", "position"]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return self.path


class TreeSource(models.Model):
    """Idempotency record: skip rebuilding a document's tree when its content is unchanged."""

    source = models.CharField(max_length=200, unique=True)
    content_hash = models.CharField(max_length=64)
    node_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source} ({self.node_count} nodes)"
