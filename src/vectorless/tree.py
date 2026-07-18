"""Parse a markdown document into a section tree (no LLM, no embeddings — pure structure).

`parse_sections` extracts the heading hierarchy; `build_document_tree` persists it as
DocumentNode rows (adjacency list) with a synthetic document root.
"""

import re

from django.db import transaction

from .models import DocumentNode


HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def parse_sections(text):
    """Return (preamble, sections) where sections is an ordered list of
    {level, title, content} and preamble is any text before the first heading.
    """
    preamble_lines = []
    sections = []
    current = None
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            current = {"level": len(match.group(1)), "title": match.group(2).strip(), "lines": []}
            sections.append(current)
        elif current is None:
            preamble_lines.append(line)
        else:
            current["lines"].append(line)

    for section in sections:
        section["content"] = "\n".join(section.pop("lines")).strip()
    return "\n".join(preamble_lines).strip(), sections


def build_document_tree(source, text):
    """Persist `source`'s section tree as DocumentNode rows. Rebuilds (delete + recreate)."""
    preamble, sections = parse_sections(text)

    with transaction.atomic():
        DocumentNode.objects.filter(source=source).delete()

        position = 0
        root = DocumentNode.objects.create(
            source=source, parent=None, title=source, level=0,
            content=preamble, path=source, position=position,
        )
        # Stack of open ancestors by increasing level; the root (level 0) always stays.
        stack = [root]
        for section in sections:
            position += 1
            # Pop ancestors that are same-or-deeper than this heading, so the parent is
            # the nearest shallower node.
            while len(stack) > 1 and stack[-1].level >= section["level"]:
                stack.pop()
            parent = stack[-1]
            node = DocumentNode.objects.create(
                source=source, parent=parent, title=section["title"], level=section["level"],
                content=section["content"], path=f"{parent.path} › {section['title']}",
                position=position,
            )
            stack.append(node)

    return DocumentNode.objects.filter(source=source).count()
