"""LLM-as-judge for answer quality (the RAG-triad idea, two dimensions).

- faithfulness (1-5): is the candidate answer supported by the retrieved EVIDENCE, or did it
  hallucinate? (reference-free — grades grounding.)
- correctness (1-5): does the candidate match the REFERENCE (gold) answer? (reference-based.)

Splitting the two tells you *why* a technique scored low: bad retrieval (low faithfulness is
possible even so) vs a wrong/incomplete answer (low correctness). Caveats: LLM judges can be
lenient or biased, and a 3-question set isn't statistically robust — treat as indicative.
"""

import logging

from llm import get_generation_provider


logger = logging.getLogger("evaluation.judge")


class JudgeError(RuntimeError):
    """Judging failed at the provider boundary or produced unparseable output."""


def _prompt(question, reference, candidate, evidence, has_images):
    image_note = (" Figures the answer relied on are attached as images — judge faithfulness "
                  "against them too.") if has_images else ""
    return (
        "You are grading a RAG answer. Score two dimensions from 1 (poor) to 5 (excellent).\n"
        "- faithfulness: is the CANDIDATE ANSWER supported by the EVIDENCE (no invented facts)?"
        f"{image_note}\n"
        "- correctness: does the CANDIDATE ANSWER match the REFERENCE ANSWER?\n\n"
        f"QUESTION:\n{question}\n\nREFERENCE ANSWER:\n{reference}\n\n"
        f"EVIDENCE:\n{evidence or '(none)'}\n\nCANDIDATE ANSWER:\n{candidate}\n\n"
        'Return ONLY JSON: {"faithfulness": <1-5>, "correctness": <1-5>, "reasoning": "<one sentence>"}'
    )


def _score(data, key):
    """Coerce and validate a rubric score to a float in [1, 5]; raise if missing/invalid."""
    if key not in data:
        raise JudgeError(f"judge omitted '{key}'")
    try:
        value = float(data[key])
    except (TypeError, ValueError) as error:
        raise JudgeError(f"non-numeric '{key}': {data[key]!r}") from error
    if not 1.0 <= value <= 5.0:
        raise JudgeError(f"'{key}' out of range: {value}")
    return value


def judge(question, reference, candidate, evidence, *, images=None):
    """Return {faithfulness, correctness, reasoning} via the configured provider.

    `images` (list of llm.Image) are the figures the answer used — passed to the model so a
    chart answer is graded against the pixels, not just its sparse text caption."""
    parts = [_prompt(question, reference, candidate, evidence, has_images=bool(images))]
    parts.extend(images or [])
    try:
        data, _ = get_generation_provider().generate_json(parts)
    except Exception as error:
        raise JudgeError(f"judging failed: {error}") from error
    if not isinstance(data, dict):
        raise JudgeError(f"judge returned non-object: {type(data).__name__}")
    return {
        "faithfulness": _score(data, "faithfulness"),
        "correctness": _score(data, "correctness"),
        "reasoning": str(data.get("reasoning", "")),
    }
