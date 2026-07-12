from rag.chunking import recursive_chunks


def test_empty_text_yields_no_chunks():
    assert recursive_chunks("   ") == []


def test_long_text_splits_into_bounded_chunks():
    text = ("Data protection requires diligence. " * 200).strip()
    chunks = recursive_chunks(text, max_chars=300, overlap=50)

    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    assert all(c.strip() for c in chunks)


def test_short_text_is_one_chunk():
    assert recursive_chunks("A single short paragraph.") == ["A single short paragraph."]


def test_bare_heading_is_packed_with_following_content():
    # The naive split("\n\n") failure: a heading alone. Recursive packing should
    # merge it with the paragraph that follows instead of emitting a tiny chunk.
    text = "## Personal Data Breaches\n\nA breach must be reported within 72 hours."
    chunks = recursive_chunks(text, max_chars=200, overlap=0)

    assert len(chunks) == 1
    assert "Personal Data Breaches" in chunks[0]
    assert "72 hours" in chunks[0]


def test_consecutive_chunks_share_overlap():
    text = " ".join(f"sentence{i}." for i in range(100))
    chunks = recursive_chunks(text, max_chars=120, overlap=40)

    assert len(chunks) >= 2
    # Some tail of an earlier chunk should reappear at the start of the next.
    tail = chunks[0][-20:]
    assert any(tail_word in chunks[1] for tail_word in tail.split())
