"""The shared document corpus.

All four retrieval techniques build over the SAME set of documents, so Stage 5 compares them
fairly — the README's premise is "the same questions over the same documents". Markdown files
are used as-is; PDFs are rendered to markdown (headings + prose + tables) via the multimodal
parser, so the text techniques (embedding / graph / vectorless) see the PDF's text and tables
too. Only the figure PIXELS remain exclusive to multimodal — the honest advantage that stage
is meant to demonstrate.
"""

from pathlib import Path

from django.conf import settings


SKIP_FILES = {"README.md"}


def corpus_dir():
    return Path(settings.BASE_DIR) / "sample-docs"


def iter_documents():
    """Every corpus document (markdown + PDF), sorted by name, README excluded."""
    directory = corpus_dir()
    paths = [p for p in directory.glob("*.md") if p.name not in SKIP_FILES]
    paths += list(directory.glob("*.pdf"))
    return sorted(paths, key=lambda p: p.name)


def document_text(path):
    """Return `path`'s content as markdown text: .md as-is, .pdf rendered to markdown.

    Used by the text techniques so they ingest the full corpus (including the PDF's text and
    tables). Multimodal keeps its own PDF parser (it also needs the figure pixels)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from multimodal.parsing import render_markdown  # local import: PyMuPDF only when needed
        return render_markdown(str(path))
    return path.read_text(encoding="utf-8")
