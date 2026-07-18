from django.db import models
from pgvector.django import VectorField


class MultimodalChunk(models.Model):
    """A retrievable unit from a PDF: prose text, a markdown table, or a figure image.

    All kinds share one 3072-dim embedding space (gemini-embedding-2), so a text query can
    match an image. Images are stored as base64 so the UI can display the parsed evidence
    without a media server. `figure_key` groups the two rows we create per figure (one
    embedded from the image, one from its caption text) so retrieval can de-duplicate.
    """

    KIND_CHOICES = [("text", "text"), ("table", "table"), ("image", "image")]

    source = models.CharField(max_length=200)
    page = models.IntegerField()
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    text = models.TextField(blank=True)      # prose / table markdown / image caption+context
    context = models.CharField(max_length=600, blank=True)  # images: section heading + caption
    image_b64 = models.TextField(blank=True)  # images: base64 PNG for display
    figure_key = models.CharField(max_length=200, blank=True)
    embedding = VectorField(dimensions=3072)

    class Meta:
        ordering = ["source", "page", "id"]
        indexes = [models.Index(fields=["source"])]

    def __str__(self):
        return f"{self.source} p{self.page} [{self.kind}]"


class MultimodalSource(models.Model):
    """Idempotency record: skip re-parsing/re-embedding a PDF whose content + model are unchanged."""

    source = models.CharField(max_length=200, unique=True)
    content_hash = models.CharField(max_length=64)
    chunk_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source} ({self.chunk_count} chunks)"
