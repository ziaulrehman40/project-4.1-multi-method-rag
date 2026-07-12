import pytest

from rag.chunking import (
    chunk,
    fixed_chunks,
    recursive_chunks,
    semantic_chunks,
)


# ------------------------------------------------------------------- fixed / recursive

def test_empty_text_yields_no_chunks():
    assert recursive_chunks("   ") == []
    assert fixed_chunks("   ") == []


def test_fixed_chunks_are_bounded():
    text = "word " * 500
    chunks = fixed_chunks(text, max_chars=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_recursive_short_text_is_one_chunk():
    assert recursive_chunks("A single short paragraph.") == ["A single short paragraph."]


def test_recursive_bare_heading_packs_with_following_content():
    text = "## Personal Data Breaches\n\nA breach must be reported within 72 hours."
    chunks = recursive_chunks(text, max_chars=200, overlap=0)
    assert len(chunks) == 1
    assert "Personal Data Breaches" in chunks[0] and "72 hours" in chunks[0]


def test_recursive_overlap_starts_at_sentence_boundary():
    # Overlap is sentence-aware: every chunk after the first begins at a sentence start
    # (fixes both the "o longer" mid-word bug and mid-sentence starts).
    sentences = [f"Rule {i} states a distinct compliance requirement plainly." for i in range(40)]
    text = " ".join(sentences)
    chunks = recursive_chunks(text, max_chars=250, overlap=80)
    assert len(chunks) >= 2
    for c in chunks[1:]:
        assert c[0].isupper()  # begins at a capitalised sentence boundary, not a fragment


# ---------------------------------------------------------------------------- semantic

def _keyword_embedder(texts):
    """Deterministic stand-in for the embedding API: topic -> axis."""
    vectors = []
    for t in texts:
        if "breach" in t:
            vectors.append([1.0, 0.0, 0.0])
        elif "payment" in t:
            vectors.append([0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return vectors


def test_semantic_cuts_at_topic_shift():
    text = (
        "A breach must be reported quickly. "
        "The breach notification goes to the authority. "
        "Payment card data must be encrypted. "
        "Payment keys are rotated yearly."
    )
    chunks = semantic_chunks(text, _keyword_embedder, threshold_percentile=50, buffer=0)
    assert len(chunks) == 2
    assert "breach" in chunks[0] and "Payment" in chunks[1]


def test_semantic_single_sentence_returns_one_chunk():
    assert semantic_chunks("Only one sentence here.", _keyword_embedder) == [
        "Only one sentence here."
    ]


# -------------------------------------------------------------------------- dispatcher

def test_dispatcher_routes_by_strategy():
    text = "Sentence one. Sentence two. Sentence three."
    assert chunk(text, strategy="fixed", max_chars=15)
    assert chunk(text, strategy="recursive", max_chars=15)
    assert chunk(text, strategy="semantic", max_chars=100, embed_fn=_keyword_embedder)


def test_semantic_without_embed_fn_raises():
    with pytest.raises(ValueError):
        chunk("some text", strategy="semantic")


def test_unknown_strategy_raises():
    with pytest.raises(ValueError):
        chunk("some text", strategy="banana")
