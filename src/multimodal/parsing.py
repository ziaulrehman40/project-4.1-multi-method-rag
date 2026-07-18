"""Parse a PDF into typed items for multimodal indexing.

Three item kinds, each handled the way it's most faithfully represented:
- table : extracted with PyMuPDF find_tables() as markdown (exact rows/columns preserved).
- text  : prose only — text blocks that do NOT overlap a table region (so garbled table
          cells never leak into the prose and skew retrieval).
- image : figure images (charts, heatmaps, equations) with the section heading + caption
          they sit under, captured from block positions for context.
"""

from dataclasses import dataclass

import fitz  # PyMuPDF


# A text block whose font is at least this large is treated as a section heading.
HEADING_MIN_FONT = 13.0


@dataclass
class ParsedItem:
    kind: str  # "text" | "table" | "image"
    page: int
    text: str = ""            # prose, table markdown, or (for images) the caption/context
    context: str = ""         # images: "Section heading — nearest caption"
    image_bytes: bytes = b""  # images: raw PNG bytes
    figure_index: int = 0     # images: stable index within the page (for de-duping later)


def _block_text(block):
    """Join all spans of a text block into one string."""
    return " ".join(span["text"] for line in block["lines"] for span in line["spans"]).strip()


def _block_font(block):
    """Largest font size in a text block (used to detect headings)."""
    return max((span["size"] for line in block["lines"] for span in line["spans"]), default=0.0)


def _tables(page):
    """Return (markdown_list, rect_list) for the page's tables."""
    markdowns, rects = [], []
    for table in page.find_tables().tables:
        markdowns.append(table.to_markdown())
        rects.append(fitz.Rect(table.bbox))
    return markdowns, rects


def _prose(page, table_rects):
    """Prose = every word NOT geometrically inside a table, reconstructed in reading order.

    We filter at the WORD level (not the block level) to guarantee no prose is lost: a word is
    dropped only if its own centre falls inside a table region — never merely because it shared
    a block with a table. `get_text("words")` yields tuples
    (x0, y0, x1, y1, word, block_no, line_no, word_no); we drop table words, then re-join the
    survivors line by line (grouped by block+line) to preserve the original reading order.
    """
    kept = []
    for x0, y0, x1, y1, word, block_no, line_no, word_no in page.get_text("words"):
        centre = fitz.Point((x0 + x1) / 2, (y0 + y1) / 2)
        if any(table_rect.contains(centre) for table_rect in table_rects):
            continue  # this word belongs to a table (captured as markdown) -> skip
        kept.append((block_no, line_no, word_no, word))

    kept.sort()  # reading order: by block, then line, then word position
    lines, current_key, current_words = [], None, []
    for block_no, line_no, _word_no, word in kept:
        if (block_no, line_no) != current_key:
            if current_words:
                lines.append(" ".join(current_words))
            current_key, current_words = (block_no, line_no), []
        current_words.append(word)
    if current_words:
        lines.append(" ".join(current_words))
    return "\n".join(lines)


def _images_with_context(page, page_no):
    """Extract figure images, each tagged with its running section heading + nearest caption.

    We walk the page's blocks top-to-bottom: text blocks update the "current section"
    (if heading-sized) and the "nearest caption" (any text); an image block then inherits
    whatever context preceded it.
    """
    ordered = sorted(page.get_text("dict")["blocks"], key=lambda b: b["bbox"][1])

    items = []
    section = ""
    caption = ""
    figure_index = 0
    for block in ordered:
        if block["type"] == 0:
            text = _block_text(block)
            if not text:
                continue
            caption = text
            if _block_font(block) >= HEADING_MIN_FONT:
                section = text
        elif block["type"] == 1 and isinstance(block.get("image"), (bytes, bytearray)):
            context = " — ".join(part for part in (section, caption) if part)
            items.append(
                ParsedItem(
                    kind="image",
                    page=page_no,
                    context=context,
                    image_bytes=bytes(block["image"]),
                    figure_index=figure_index,
                )
            )
            figure_index += 1
    return items


def parse_pdf(path):
    """Parse a PDF file into a flat list of ParsedItems (tables, prose, images).

    TODO (cross-page continuity): each page is parsed independently, so content that spans a
    page boundary is split — a table continuing onto the next page becomes two separate
    tables, a paragraph broken across pages becomes two prose blocks, and an image's caption
    on the previous page is missed. A fuller version would stitch adjacent-page tables with
    matching columns, merge trailing/leading prose across the break, and carry the running
    section heading across pages. Acceptable for the small sample PDF; revisit for real docs.
    """
    items = []
    document = fitz.open(path)
    for page_index in range(document.page_count):
        page = document[page_index]
        page_no = page_index + 1

        table_markdowns, table_rects = _tables(page)
        for markdown in table_markdowns:
            items.append(ParsedItem(kind="table", page=page_no, text=markdown))

        prose = _prose(page, table_rects)
        if prose:
            items.append(ParsedItem(kind="text", page=page_no, text=prose))

        items.extend(_images_with_context(page, page_no))
    return items
