"""Knowledge-graph triple extraction: turn document text into (subject, predicate, object).

An LLM reads the text and returns structured facts, each tagged with its source document and
section for provenance. The prompt guards the two failure modes: hallucinated facts and
inconsistent entity phrasing (which would fragment the graph).

`extract_triples(text, source)` is granularity-agnostic — pass a whole document (default) or a
single chunk. Entity/predicate canonicalisation here is light (lowercase/whitespace); full
entity de-duplication across the corpus happens when the graph is built (Increment 2).
"""

import logging
from dataclasses import dataclass

from llm import get_generation_provider
from llm_json import loads_lenient


logger = logging.getLogger("kg.extract")


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
    """Generate JSON text via the configured provider. Returns raw text (parsed by caller).

    Name kept so tests can mock it; retry lives in the provider.
    """
    return get_generation_provider().generate([prompt], json_mode=True).text


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
