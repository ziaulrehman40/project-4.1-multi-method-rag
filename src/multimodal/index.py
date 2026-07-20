"""Index a PDF into multimodal chunks: parse -> embed (text & images) -> store in pgvector.

Per figure we store TWO rows sharing a `figure_key`: one embedded from the image itself
(cross-modal match) and one embedded from its caption/context text (recall boost when the
question matches the surrounding words). Retrieval de-duplicates by `figure_key`.
"""

import base64

from django.db import transaction

from rag.chunking import recursive_chunks  # reuse Stage 1 chunker for prose

from .embeddings import embed_image, embed_text
from .models import MultimodalChunk
from .parsing import parse_pdf


def _rows_for_item(item, source):
    """Build the MultimodalChunk row(s) for one parsed item (embeds inline)."""
    if item.kind == "table":
        return [MultimodalChunk(source=source, page=item.page, kind="table",
                                text=item.text, embedding=embed_text(item.text))]

    if item.kind == "text":
        # Chunk prose so long sections embed sharply (same rationale as Stage 1).
        return [
            MultimodalChunk(source=source, page=item.page, kind="text",
                            text=chunk, embedding=embed_text(chunk))
            for chunk in recursive_chunks(item.text)
        ]

    # image: an image-embedded row + a caption-embedded row (shared figure_key).
    b64 = base64.b64encode(item.image_bytes).decode("ascii")
    figure_key = f"{source}-p{item.page}-f{item.figure_index}"
    rows = [
        MultimodalChunk(source=source, page=item.page, kind="image", text=item.context,
                        context=item.context, image_b64=b64, figure_key=figure_key,
                        embedding=embed_image(item.image_bytes)),
    ]
    if item.context:
        rows.append(
            MultimodalChunk(source=source, page=item.page, kind="image", text=item.context,
                            context=item.context, image_b64=b64, figure_key=figure_key,
                            embedding=embed_text(item.context))
        )
    return rows


def build_from_pdf(source, path):
    """Parse, embed, and store a PDF's chunks (rebuild: delete + recreate). Returns the count."""
    items = parse_pdf(path)
    with transaction.atomic():
        MultimodalChunk.objects.filter(source=source).delete()
        rows = []
        for item in items:
            rows.extend(_rows_for_item(item, source))
        MultimodalChunk.objects.bulk_create(rows)
    return MultimodalChunk.objects.filter(source=source).count()


def _markdown_blocks(text):
    """Split markdown into ('table' | 'text', content) blocks. A block is a run of non-blank
    lines; it's a table if its lines are pipe-rows, else prose — so markdown tables are indexed
    as `table` chunks (parity with the PDF parser) and everything else as `text`."""
    blocks, buffer, is_table = [], [], False
    for line in text.splitlines():
        if not line.strip():
            if buffer:
                blocks.append(("table" if is_table else "text", "\n".join(buffer)))
                buffer = []
            continue
        line_is_table = line.lstrip().startswith("|")
        if buffer and line_is_table != is_table:  # prose/table boundary within a run -> flush
            blocks.append(("table" if is_table else "text", "\n".join(buffer)))
            buffer = []
        if not buffer:
            is_table = line_is_table
        buffer.append(line)
    if buffer:
        blocks.append(("table" if is_table else "text", "\n".join(buffer)))
    return blocks


def build_from_markdown(source, text):
    """Index a markdown document as multimodal text/table chunks (no figures). Rebuild.

    Lets multimodal cover the SAME corpus as the text techniques — it just has no figure pixels
    to add for markdown sources."""
    rows = []
    for kind, content in _markdown_blocks(text):
        content = content.strip()
        if not content:
            continue
        if kind == "table":
            rows.append(MultimodalChunk(source=source, page=1, kind="table",
                                        text=content, embedding=embed_text(content)))
        else:
            rows.extend(
                MultimodalChunk(source=source, page=1, kind="text", text=chunk,
                                embedding=embed_text(chunk))
                for chunk in recursive_chunks(content)
            )
    with transaction.atomic():
        MultimodalChunk.objects.filter(source=source).delete()
        MultimodalChunk.objects.bulk_create(rows)
    return MultimodalChunk.objects.filter(source=source).count()
