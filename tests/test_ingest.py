import pytest
from django.core.management import call_command

from rag.models import DocumentChunk, IngestedDocument


pytestmark = pytest.mark.django_db


def _fake_embed(texts):
    # Deterministic 3072-dim vectors, one per input text.
    return [[float(len(t) % 7)] + [0.0] * 3071 for t in texts]


def test_ingest_creates_chunks_with_embeddings(monkeypatch):
    embed_calls = []

    def spy(texts):
        embed_calls.append(len(texts))
        return _fake_embed(texts)

    monkeypatch.setattr("rag.management.commands.ingest_docs.embed_texts", spy)

    call_command("ingest_docs")

    assert DocumentChunk.objects.count() > 0
    assert IngestedDocument.objects.count() > 0
    sample = DocumentChunk.objects.first()
    assert len(sample.embedding) == 3072
    assert embed_calls, "embeddings should have been generated on first ingest"


def test_ingest_is_idempotent_on_unchanged_docs(monkeypatch):
    def counting(texts, _state={"n": 0}):
        _state["n"] += 1
        return _fake_embed(texts)

    monkeypatch.setattr("rag.management.commands.ingest_docs.embed_texts", counting)

    call_command("ingest_docs")
    first_count = DocumentChunk.objects.count()

    # Second run: nothing changed, so no re-embedding and no duplicate chunks.
    def fail_if_called(texts):
        raise AssertionError("embed_texts must not be called for unchanged docs")

    monkeypatch.setattr("rag.management.commands.ingest_docs.embed_texts", fail_if_called)
    call_command("ingest_docs")

    assert DocumentChunk.objects.count() == first_count


def test_changing_strategy_reingests(monkeypatch):
    calls = {"n": 0}

    def spy(texts):
        calls["n"] += 1
        return _fake_embed(texts)

    monkeypatch.setattr("rag.management.commands.ingest_docs.embed_texts", spy)

    call_command("ingest_docs", strategy="recursive")
    after_first = calls["n"]

    # Same content but a different chunking config -> must re-embed, not skip.
    call_command("ingest_docs", strategy="fixed")
    assert calls["n"] > after_first
