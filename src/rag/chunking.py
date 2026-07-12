"""Document chunking strategies.

Three strategies, from crudest to most meaning-aware:

- fixed:     slice into fixed-size character windows with overlap. Blind to structure
             (may cut mid-sentence/word). The naive baseline.
- recursive: split on a hierarchy of separators (paragraph -> line -> sentence -> word),
             preferring the largest natural boundary that fits, then pack with word-aware
             overlap. Structure-aware; a good default.
- semantic:  split where meaning shifts, detected from sentence embeddings. Topically
             coherent chunks, but embeds every sentence (expensive) and needs a threshold.

Use `chunk(text, strategy=...)` to dispatch. `semantic` needs an `embed_fn` injected so it
is testable without the real embedding API.
"""

import math
import re


DEFAULT_MAX_CHARS = 500
DEFAULT_OVERLAP = 100
SEPARATORS = ["\n\n", "\n", ". ", " "]


# --------------------------------------------------------------------------- helpers

def _overlap_tail(text, overlap):
    """Return trailing whole sentence(s) to seed the next chunk's overlap.

    Sentence-aware so the next chunk always starts at a sentence boundary (not mid-word or
    mid-sentence). Includes the last complete sentence always, then earlier sentences while
    they fit the `overlap` budget — so the overlap may exceed `overlap` by up to one sentence.
    Falls back to a word-aware character tail only when the text has no sentence boundary.
    """
    if overlap <= 0 or not text:
        return ""
    sentences = _split_sentences(text)
    if not sentences:
        tail = text[-overlap:]
        space = tail.find(" ")
        return tail[space + 1 :].strip() if space != -1 else tail.strip()

    tail_sentences = [sentences[-1]]
    total = len(sentences[-1])
    for sentence in reversed(sentences[:-1]):
        if total + len(sentence) + 1 > overlap:
            break
        tail_sentences.insert(0, sentence)
        total += len(sentence) + 1
    return " ".join(tail_sentences)


def _cosine(a, b):
    # cosine similarity = dot product divided by the product of the two vector lengths.
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _percentile(values, pct):
    """Linear-interpolated percentile of `values` (pct in 0..100)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)  # fractional index of the percentile
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return ordered[int(rank)]
    # rank falls between two samples: blend them by how far along it sits.
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _split_sentences(text):
    # Break on sentence terminators followed by whitespace, and on newlines.
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


# ------------------------------------------------------------------------ strategies

def fixed_chunks(text, max_chars=DEFAULT_MAX_CHARS, overlap=DEFAULT_OVERLAP):
    """Fixed-size character windows with overlap. Structure-blind baseline."""
    text = text.strip()
    if not text:
        return []
    step = max(1, max_chars - overlap)
    chunks = []
    for start in range(0, len(text), step):
        window = text[start : start + max_chars].strip()
        if window:
            chunks.append(window)
        if start + max_chars >= len(text):
            break
    return chunks


def _split_recursive(text, max_chars, separators):
    """Break text into atomic pieces, each <= max_chars where possible."""
    if len(text) <= max_chars:
        return [text]
    if not separators:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
    separator, *rest = separators
    pieces = []
    for part in text.split(separator):
        if not part:
            continue
        if len(part) <= max_chars:
            pieces.append(part)
        else:
            pieces.extend(_split_recursive(part, max_chars, rest))
    return pieces


def recursive_chunks(text, max_chars=DEFAULT_MAX_CHARS, overlap=DEFAULT_OVERLAP):
    """Structure-aware split + greedy pack with word-aware overlap."""
    text = text.strip()
    if not text:
        return []

    pieces = _split_recursive(text, max_chars, SEPARATORS)
    chunks = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        tail = _overlap_tail(chunks[-1], overlap) if chunks else ""
        current = f"{tail} {piece}".strip() if tail else piece
    if current:
        chunks.append(current)
    return chunks


def semantic_chunks(
    text,
    embed_fn,
    threshold_percentile=90,
    buffer=1,
    max_chars=DEFAULT_MAX_CHARS,
):
    """Split where meaning shifts, using sentence embeddings.

    `embed_fn(list[str]) -> list[vector]` is injected (so tests can mock it). A boundary is
    placed where the cosine *distance* between consecutive sentence embeddings lands in the
    top (100 - threshold_percentile)% of all distances — i.e. the sharpest topic jumps.
    `buffer` blends each sentence with its neighbours before embedding to reduce noise.
    Any resulting chunk larger than `max_chars` is recursively re-split to respect token limits.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return [text.strip()] if text.strip() else []

    # Blend each sentence with `buffer` neighbours on each side for smoother comparisons.
    windows = [
        " ".join(sentences[max(0, i - buffer) : i + buffer + 1])
        for i in range(len(sentences))
    ]
    vectors = embed_fn(windows)

    # Distance between each adjacent pair; a large distance == a topic boundary.
    distances = [1 - _cosine(vectors[i], vectors[i + 1]) for i in range(len(vectors) - 1)]
    threshold = _percentile(distances, threshold_percentile)  # only the sharpest jumps qualify
    # A boundary sits *before* sentence i+1 wherever that gap is a top-percentile jump.
    boundaries = {i + 1 for i, d in enumerate(distances) if d >= threshold and d > 0}

    groups = []
    current = []
    for i, sentence in enumerate(sentences):
        if i in boundaries and current:
            groups.append(" ".join(current))
            current = []
        current.append(sentence)
    if current:
        groups.append(" ".join(current))

    # Safety: keep every chunk within max_chars (protects the embedding token limit).
    chunks = []
    for group in groups:
        if len(group) <= max_chars:
            chunks.append(group)
        else:
            chunks.extend(recursive_chunks(group, max_chars=max_chars))
    return chunks


# ------------------------------------------------------------------------- dispatcher

STRATEGIES = ("fixed", "recursive", "semantic")


def chunk(
    text,
    strategy="recursive",
    max_chars=DEFAULT_MAX_CHARS,
    overlap=DEFAULT_OVERLAP,
    embed_fn=None,
):
    if strategy == "fixed":
        return fixed_chunks(text, max_chars, overlap)
    if strategy == "recursive":
        return recursive_chunks(text, max_chars, overlap)
    if strategy == "semantic":
        if embed_fn is None:
            raise ValueError("semantic chunking requires an embed_fn")
        return semantic_chunks(text, embed_fn, max_chars=max_chars)
    raise ValueError(f"unknown chunking strategy: {strategy!r} (choose from {STRATEGIES})")
