"""Tests for the shared corpus — the Stage-5 fairness backbone. If the README leaked into the
corpus, or PDFs stopped rendering to text, every technique's eval would be silently biased with
no other failing test, so these guard that boundary directly."""

import corpus
from multimodal.parsing import render_markdown


def test_iter_documents_includes_md_and_pdf_and_excludes_readme():
    names = [p.name for p in corpus.iter_documents()]
    assert "gdpr-excerpt.md" in names          # a policy doc (text techniques)
    assert "compliance-metrics.pdf" in names   # the figure/table PDF (multimodal)
    assert "README.md" not in names            # corpus README must not be ingested
    assert names == sorted(names)              # deterministic order


def test_document_text_markdown_is_returned_verbatim():
    path = corpus.corpus_dir() / "gdpr-excerpt.md"
    assert corpus.document_text(path) == path.read_text(encoding="utf-8")


def test_document_text_renders_pdf_to_markdown_with_headings_and_tables():
    path = corpus.corpus_dir() / "compliance-metrics.pdf"
    rendered = corpus.document_text(path)
    assert "## " in rendered          # headings recovered (vectorless tree needs them)
    assert "|" in rendered            # at least one table rendered as markdown
    assert "Incident" in rendered     # real PDF content reached the text techniques
    # document_text delegates to the multimodal parser for PDFs.
    assert rendered == render_markdown(str(path))
