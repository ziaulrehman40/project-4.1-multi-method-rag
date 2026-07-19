"""Reasoning-based navigation: the LLM picks relevant sections from the table of contents.

We show the LLM only section titles + breadcrumb paths (no content — that's the efficiency
point), and it returns the indices of the sections most likely to contain the answer. Our
trees are shallow, so one call over the whole TOC suffices; deep documents would use
iterative descent instead.
"""

import logging

from llm import get_generation_provider
from llm_json import loads_lenient

from .models import DocumentNode


logger = logging.getLogger("vectorless.nav")

DEFAULT_MAX_SECTIONS = 5


class NavigationError(RuntimeError):
    """Navigation failed at the provider boundary or produced unparseable output."""


def _toc_nodes():
    # Section nodes across all documents (skip the level-0 filename roots).
    return list(DocumentNode.objects.exclude(level=0).order_by("source", "position"))


def _generate_json(prompt):
    """Generate JSON text via the configured provider (raw text; parsed by caller)."""
    return get_generation_provider().generate([prompt], json_mode=True).text


def navigate(question, max_sections=DEFAULT_MAX_SECTIONS):
    """Return the sections the LLM judged most likely to answer the question (most relevant first)."""
    nodes = _toc_nodes()
    if not nodes:
        return []

    listing = "\n".join(f"[{i}] {node.path}" for i, node in enumerate(nodes))
    prompt = (
        "You are navigating a table of contents to find where a question is answered. "
        "Reason about which sections would contain the answer.\n\n"
        f"Question: {question}\n\nSections:\n{listing}\n\n"
        f"Return ONLY a JSON array of the indices (at most {max_sections}) of the sections "
        "most likely to contain the answer, most relevant first, e.g. [2, 5]."
    )
    try:
        indices = loads_lenient(_generate_json(prompt))
    except Exception as error:
        raise NavigationError(f"navigation failed: {error}") from error

    selected = []
    for index in indices[:max_sections]:
        if isinstance(index, int) and 0 <= index < len(nodes):
            selected.append(nodes[index])
    return selected
