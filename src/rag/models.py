from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from pgvector.django import VectorField


# gemini-embedding-001 returns 3072-dim vectors by default.
EMBEDDING_DIM = 3072


class IngestedDocument(models.Model):
    """Tracks what has been ingested so ingestion is idempotent.

    Keyed by source filename with a content hash, so startup ingestion re-embeds
    only when a document's contents actually change (no wasted API calls per deploy).
    """

    source = models.CharField(max_length=200, unique=True)
    content_hash = models.CharField(max_length=64)
    chunk_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source} ({self.chunk_count} chunks)"


class DocumentChunk(models.Model):
    """One retrievable chunk of a source document plus its embedding.

    No approximate-nearest-neighbour index is declared on `embedding`: pgvector's
    ivfflat/hnsw indexes cap at 2000 dimensions, and our vectors are 3072-dim. The
    sample-docs corpus is tiny, so an exact sequential cosine scan is both fast and
    more accurate than an approximate index. If the corpus grows large, switch to
    reduced-dimension embeddings (Matryoshka) or halfvec and add an HNSW index.
    """

    source = models.CharField(max_length=200)
    ordinal = models.IntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    # Sparse/keyword side of hybrid search: a Postgres full-text vector built from `text`.
    # Populated at ingest; queried with SearchQuery + SearchRank (see rag/retrieval.py).
    search_vector = SearchVectorField(null=True)

    class Meta:
        ordering = ["source", "ordinal"]
        indexes = [
            models.Index(fields=["source"]),
            GinIndex(fields=["search_vector"]),  # fast keyword lookup
        ]

    def __str__(self):
        return f"{self.source}#{self.ordinal}: {self.text[:40]}"
