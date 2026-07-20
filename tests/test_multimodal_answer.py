import base64

import pytest

from llm import Generation, Image
from multimodal import answer as answer_mod
from multimodal.answer import _build_contents, answer
from multimodal.models import MultimodalChunk


pytestmark = pytest.mark.django_db


def _vec(x):
    return [x] + [0.0] * 3071


def _chunk(kind, page, text="", figure_key="", image_b64="", vec=0.0, context=""):
    return MultimodalChunk.objects.create(
        source="d.pdf", page=page, kind=kind, text=text, context=context,
        image_b64=image_b64, figure_key=figure_key, embedding=_vec(vec),
    )


def test_retrieve_dedupes_figures_by_figure_key(monkeypatch):
    from multimodal.retrieval import retrieve
    # A figure's two rows (image + caption) both embedded near the query axis.
    _chunk("image", 2, figure_key="f1", image_b64="AAA", vec=1.0, context="chart")
    _chunk("image", 2, figure_key="f1", image_b64="AAA", vec=0.99, context="chart")
    _chunk("text", 1, text="prose", vec=0.9)
    monkeypatch.setattr("multimodal.retrieval.embed_text", lambda q: _vec(1.0))

    results = retrieve("q", k=5)
    figure_rows = [r for r in results if r.figure_key == "f1"]
    assert len(figure_rows) == 1  # the paired figure rows collapse to one


def test_build_contents_passes_images_as_parts():
    png = base64.b64encode(b"PNGBYTES").decode()
    chunks = [
        _chunk("text", 1, text="Some prose.", vec=0.1),
        _chunk("image", 2, figure_key="f1", image_b64=png, vec=0.2, context="incident chart"),
    ]
    parts = _build_contents("Which is highest?", chunks, max_images=3)
    # There must be an actual Image part in the multimodal prompt (provider-agnostic).
    assert any(isinstance(p, Image) for p in parts)
    assert any(isinstance(p, str) and "Some prose." in p for p in parts)


def test_answer_builds_trace_and_metrics(monkeypatch):
    _chunk("image", 2, figure_key="f1", image_b64=base64.b64encode(b"x").decode(),
           vec=1.0, context="chart")
    monkeypatch.setattr("multimodal.retrieval.embed_text", lambda q: _vec(1.0))
    monkeypatch.setattr(answer_mod, "run_generation",
                        lambda parts, **kw: Generation(text="Phishing [1].", input_tokens=200,
                                                       output_tokens=5, total_tokens=205))

    result = answer("Which category was most common?")
    assert result["answer"] == "Phishing [1]."
    assert result["trace"][0]["kind"] == "image"
    assert result["metrics"]["evidence_used"] == 1 and result["metrics"]["total_tokens"] == 205
