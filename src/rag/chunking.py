"""Recursive character chunking.

Splits text along a priority list of separators (paragraph → line → sentence → word),
then greedily packs the resulting pieces into chunks up to `max_chars`, carrying a small
overlap between consecutive chunks so meaning that straddles a boundary is not lost.

This avoids the "bare heading becomes its own tiny chunk" failure of naive `split("\\n\\n")`
by packing small pieces together into meaningful units.
"""

DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP = 150
SEPARATORS = ["\n\n", "\n", ". ", " "]


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
    """Return a list of non-empty chunk strings, each <= max_chars."""
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
        # Seed the next chunk with an overlap tail from the one just closed.
        if overlap and chunks:
            tail = chunks[-1][-overlap:]
            current = f"{tail} {piece}".strip()
        else:
            current = piece
    if current:
        chunks.append(current)
    return chunks
