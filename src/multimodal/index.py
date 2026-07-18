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
