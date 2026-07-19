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


def _prompt(question, reference, candidate, evidence):
    return (
        "You are grading a RAG answer. Score two dimensions from 1 (poor) to 5 (excellent).\n"
        "- faithfulness: is the CANDIDATE ANSWER supported by the EVIDENCE (no invented facts)?\n"
        "- correctness: does the CANDIDATE ANSWER match the REFERENCE ANSWER?\n\n"
        f"QUESTION:\n{question}\n\nREFERENCE ANSWER:\n{reference}\n\n"
        f"EVIDENCE:\n{evidence or '(none)'}\n\nCANDIDATE ANSWER:\n{candidate}\n\n"
        'Return ONLY JSON: {"faithfulness": <1-5>, "correctness": <1-5>, "reasoning": "<one sentence>"}'
    )


def judge(question, reference, candidate, evidence):
    """Return {faithfulness, correctness, reasoning} via the configured provider."""
    prompt = _prompt(question, reference, candidate, evidence)
    try:
        data, _ = get_generation_provider().generate_json([prompt])
    except Exception as error:
        raise JudgeError(f"judging failed: {error}") from error
    return {
        "faithfulness": float(data.get("faithfulness", 0)),
        "correctness": float(data.get("correctness", 0)),
        "reasoning": str(data.get("reasoning", "")),
    }
