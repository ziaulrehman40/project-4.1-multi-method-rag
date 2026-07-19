"""Knowledge-graph triple extraction: turn document text into (subject, predicate, object).

An LLM reads the text and returns structured facts, each tagged with its source document and
section for provenance. The prompt guards the two failure modes: hallucinated facts and
inconsistent entity phrasing (which would fragment the graph).

`extract_triples(text, source)` is granularity-agnostic — pass a whole document (default) or a
single chunk. Entity/predicate canonicalisation here is light (lowercase/whitespace); full
entity de-duplication across the corpus happens when the graph is built (Increment 2).
"""

import logging
import os
import time
from dataclasses import dataclass

from django.conf import settings
from google import genai
from google.genai import types
from llm_json import loads_lenient


logger = logging.getLogger("kg.extract")

MODEL = settings.GEMINI_MODEL
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    source: str       # document filename
    section: str = ""  # nearest heading, for section-level citations


class ExtractionError(RuntimeError):
    """Triple extraction failed at the provider boundary or produced unparseable output."""


def _canonical(name):
    """Light normalisation so the same entity/relation matches: lowercase, collapse spaces."""
    return " ".join(str(name).strip().lower().split())


def _build_prompt(text):
    return (
        "Extract factual relationships from the compliance policy text below as "
        "subject-predicate-object triples.\n"
        "Rules:\n"
        "- Extract ONLY facts explicitly stated in the text. Do not infer or add outside knowledge.\n"
        "- Use short, canonical noun phrases for subject and object, and reuse identical phrasing "
        "whenever you refer to the same thing.\n"
        "- Keep predicates short and consistent (e.g. 'must be reported to', 'must be encrypted').\n"
        "- Include the nearest section heading each fact came from.\n\n"
        'Return ONLY a JSON array: [{"subject": "...", "predicate": "...", "object": "...", '
        '"section": "..."}, ...]\n\n'
        f"Text:\n{text}"
    )


def _generate_json(prompt):
    """Call Gemini for JSON output; retry transient errors (e.g. 503/429) with backoff.

    Returns the raw text. Split out so tests can mock it.
    """
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Strong client reference (a temporary genai.Client is GC'd mid-request).
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return response.text
        except Exception as error:  # transient: high-demand 503, rate-limit 429, network
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("kg.extract.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise last_error


def extract_triples(text, source):
    """Extract provenance-tagged triples from `text`. Raises ExtractionError on failure."""
    try:
        data = loads_lenient(_generate_json(_build_prompt(text)))
    except Exception as error:
        raise ExtractionError(f"extraction failed for {source}: {error}") from error

    triples = []
    for item in data:
        subject = _canonical(item.get("subject", ""))
        predicate = _canonical(item.get("predicate", ""))
        obj = _canonical(item.get("object", ""))
        if subject and predicate and obj:  # skip incomplete triples
            triples.append(
                Triple(
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    source=source,
                    # Section is asked to LLM to add, nearest section heading in the text against this fact. If not found, it will be empty string.
                    section=str(item.get("section", "")).strip(),
                )
            )
    return triples
