from types import SimpleNamespace

import pytest

from rag import embeddings


class _FakeClient:
    def __init__(self, fail_times=0):
        self.batch_sizes = []
        self._fail_times = fail_times
        self.models = SimpleNamespace(embed_content=self._embed)

    def _embed(self, model, contents):
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("Cannot send a request, as the client has been closed.")
        self.batch_sizes.append(len(contents))
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.0] * 3072) for _ in contents]
        )


def test_large_input_is_split_into_batches(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(embeddings, "_client", lambda: fake)

    vectors = embeddings.embed_texts([f"text {i}" for i in range(70)])

    assert len(vectors) == 70
    assert all(len(v) == 3072 for v in vectors)
    # 70 items at MAX_BATCH=32 -> 32 + 32 + 6
    assert fake.batch_sizes == [32, 32, 6]


def test_transient_error_is_retried(monkeypatch):
    fake = _FakeClient(fail_times=1)
    monkeypatch.setattr(embeddings, "_client", lambda: fake)
    monkeypatch.setattr(embeddings.time, "sleep", lambda _s: None)

    vectors = embeddings.embed_texts(["hello"])

    assert len(vectors) == 1


def test_gives_up_after_max_retries(monkeypatch):
    fake = _FakeClient(fail_times=99)
    monkeypatch.setattr(embeddings, "_client", lambda: fake)
    monkeypatch.setattr(embeddings.time, "sleep", lambda _s: None)

    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed_texts(["hello"])
