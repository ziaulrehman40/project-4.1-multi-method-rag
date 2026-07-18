"""Reasoning-based navigation: the LLM picks relevant sections from the table of contents.

We show the LLM only section titles + breadcrumb paths (no content — that's the efficiency
point), and it returns the indices of the sections most likely to contain the answer. Our
trees are shallow, so one call over the whole TOC suffices; deep documents would use
iterative descent instead.
"""

import json
import logging
import os
import time

from django.conf import settings
from google import genai
from google.genai import types

from .models import DocumentNode


logger = logging.getLogger("vectorless.nav")

MODEL = settings.GEMINI_MODEL
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0
DEFAULT_MAX_SECTIONS = 5


class NavigationError(RuntimeError):
    """Navigation failed at the provider boundary or produced unparseable output."""


def _toc_nodes():
    # Section nodes across all documents (skip the level-0 filename roots).
    return list(DocumentNode.objects.exclude(level=0).order_by("source", "position"))


def _generate_json(prompt):
    """Call Gemini for JSON output; retry transient 503/429 with backoff."""
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return response.text
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("vectorless.nav.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise last_error


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
        indices = json.loads(_generate_json(prompt))
    except Exception as error:
        raise NavigationError(f"navigation failed: {error}") from error

    selected = []
    for index in indices[:max_sections]:
        if isinstance(index, int) and 0 <= index < len(nodes):
            selected.append(nodes[index])
    return selected
