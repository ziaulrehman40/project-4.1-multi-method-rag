from pathlib import Path

import pytest
from django.conf import settings

from multimodal import index as index_mod
from multimodal.index import _markdown_blocks, build_from_markdown, build_from_pdf
from multimodal.models import MultimodalChunk
from multimodal.parsing import ParsedItem, parse_pdf


PDF = Path(settings.BASE_DIR) / "sample-docs" / "compliance-metrics.pdf"


# ------------------------------------------------------------------- parsing (real PDF)

def test_parse_pdf_separates_tables_prose_and_images():
    items = parse_pdf(str(PDF))
    kinds = {i.kind for i in items}
    assert {"table", "text", "image"} <= kinds

    # Table captured as markdown with real structure.
    table = next(i for i in items if i.kind == "table")
    assert "|" in table.text and "Severity" in table.text

    # Prose must NOT contain the jumbled table rows (bbox filtering worked).
    prose = " ".join(i.text for i in items if i.kind == "text")
    assert "Critical" not in prose and "24 hours" not in prose

    # Images carry bytes + context (section/caption).
    images = [i for i in items if i.kind == "image"]
    assert images and all(i.image_bytes for i in images)
    assert any(i.context for i in images)


# --------------------------------------------------------------- build (mocked embeddings)

@pytest.mark.django_db
def test_build_creates_typed_chunks_and_paired_image_rows(monkeypatch):
    fake_items = [
        ParsedItem(kind="table", page=1, text="|A|B|\n|---|---|\n|1|2|"),
        ParsedItem(kind="text", page=1, text="Some prose about breaches."),
        ParsedItem(kind="image", page=2, context="Reported Incidents — chart",
                   image_bytes=b"PNGDATA", figure_index=0),
    ]
    monkeypatch.setattr(index_mod, "parse_pdf", lambda path: fake_items)
    monkeypatch.setattr(index_mod, "embed_text", lambda t: [0.1] + [0.0] * 3071)
    monkeypatch.setattr(index_mod, "embed_image", lambda b, **k: [0.2] + [0.0] * 3071)

    build_from_pdf("doc.pdf", "ignored")

    assert MultimodalChunk.objects.filter(kind="table").count() == 1
    assert MultimodalChunk.objects.filter(kind="text").count() >= 1
    # One figure -> two image rows (image-embedded + caption-embedded), shared figure_key.
    image_rows = MultimodalChunk.objects.filter(kind="image")
    assert image_rows.count() == 2
    assert image_rows.values("figure_key").distinct().count() == 1
    assert all(r.image_b64 for r in image_rows)  # base64 stored for the UI


@pytest.mark.django_db
def test_build_skips_caption_row_when_no_context(monkeypatch):
    monkeypatch.setattr(index_mod, "parse_pdf",
                        lambda path: [ParsedItem(kind="image", page=1, context="",
                                                 image_bytes=b"X", figure_index=0)])
    monkeypatch.setattr(index_mod, "embed_image", lambda b, **k: [0.2] + [0.0] * 3071)

    build_from_pdf("doc.pdf", "ignored")
    assert MultimodalChunk.objects.filter(kind="image").count() == 1  # no caption row


def test_markdown_blocks_splits_tables_from_prose():
    text = "Intro prose.\n\n|A|B|\n|---|---|\n|1|2|\n\nMore prose."
    blocks = _markdown_blocks(text)
    assert [kind for kind, _ in blocks] == ["text", "table", "text"]
    table = next(content for kind, content in blocks if kind == "table")
    assert table.startswith("|A|B|")


@pytest.mark.django_db
def test_build_from_markdown_creates_text_and_table_chunks_no_images(monkeypatch):
    monkeypatch.setattr(index_mod, "embed_text", lambda t: [0.1] + [0.0] * 3071)
    md = "## Access\n\nSome prose about access control.\n\n|Ctl|Status|\n|---|---|\n|C-1|Done|"

    build_from_markdown("policy.md", md)

    assert MultimodalChunk.objects.filter(source="policy.md", kind="table").count() == 1
    assert MultimodalChunk.objects.filter(source="policy.md", kind="text").count() >= 1
    assert MultimodalChunk.objects.filter(source="policy.md", kind="image").count() == 0
