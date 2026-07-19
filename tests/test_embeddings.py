import pytest

from rag import embeddings


class _FakeEmbeddingProvider:
    def __init__(self, fail=False):
        self.batch_sizes = []
        self.fail = fail

    def embed_texts(self, texts, *, model=None):
        if self.fail:
            raise RuntimeError("provider down")
        self.batch_sizes.append(len(texts))
        return [[0.0] * 3072 for _ in texts]

    def embed_image(self, image, *, model=None):
        return [0.0] * 3072


def test_large_input_is_split_into_batches(monkeypatch):
    fake = _FakeEmbeddingProvider()
    monkeypatch.setattr(embeddings, "get_embedding_provider", lambda: fake)

    vectors = embeddings.embed_texts([f"text {i}" for i in range(70)])

    assert len(vectors) == 70
    assert fake.batch_sizes == [32, 32, 6]  # MAX_BATCH slicing


def test_failure_is_wrapped_as_embedding_error(monkeypatch):
    monkeypatch.setattr(embeddings, "get_embedding_provider", lambda: _FakeEmbeddingProvider(fail=True))
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed_texts(["a"])
