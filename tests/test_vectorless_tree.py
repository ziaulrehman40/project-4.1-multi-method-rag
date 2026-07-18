import pytest

from vectorless.models import DocumentNode
from vectorless.tree import build_document_tree, parse_sections


SAMPLE = """# Policy Title

Intro paragraph before any section.

## Section A

Text of A.

### Section A.1

Text of A.1.

## Section B

Text of B.
"""


def test_parse_sections_extracts_levels_titles_content_and_preamble():
    preamble, sections = parse_sections(SAMPLE)

    # No text before the first heading, so preamble is empty; the intro is the H1's content.
    assert preamble == ""
    assert [(s["level"], s["title"]) for s in sections] == [
        (1, "Policy Title"),
        (2, "Section A"),
        (3, "Section A.1"),
        (2, "Section B"),
    ]
    assert sections[0]["content"] == "Intro paragraph before any section."
    assert sections[1]["content"] == "Text of A."


def test_parse_sections_captures_true_preamble():
    preamble, sections = parse_sections("Front matter line.\n\n# Title\n\nBody.")
    assert preamble == "Front matter line."
    assert sections[0]["title"] == "Title"


@pytest.mark.django_db
def test_build_document_tree_creates_correct_hierarchy():
    count = build_document_tree("doc.md", SAMPLE)
    assert count == 5  # root + H1 + A + A.1 + B

    root = DocumentNode.objects.get(source="doc.md", level=0)
    assert root.parent is None and root.title == "doc.md"

    h1 = DocumentNode.objects.get(title="Policy Title")
    assert h1.parent == root and h1.level == 1

    a = DocumentNode.objects.get(title="Section A")
    a1 = DocumentNode.objects.get(title="Section A.1")
    b = DocumentNode.objects.get(title="Section B")
    assert a.parent == h1 and b.parent == h1        # siblings under the H1
    assert a1.parent == a                            # nested under A
    assert a1.path == "doc.md › Policy Title › Section A › Section A.1"


@pytest.mark.django_db
def test_rebuild_replaces_previous_nodes():
    build_document_tree("doc.md", SAMPLE)
    build_document_tree("doc.md", "# New\n\n## Only Section\n\nBody.")

    titles = set(DocumentNode.objects.filter(source="doc.md").values_list("title", flat=True))
    assert "Section A" not in titles
    assert {"doc.md", "New", "Only Section"} <= titles
