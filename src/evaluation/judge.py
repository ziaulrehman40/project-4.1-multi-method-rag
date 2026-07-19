"""LLM-as-judge for answer quality (the RAG-triad idea, two dimensions).

- faithfulness (1-5): is the candidate answer supported by the retrieved EVIDENCE, or did it
  hallucinate? (reference-free — grades grounding.)
- correctness (1-5): does the candidate match the REFERENCE (gold) answer? (reference-based.)

Splitting the two tells you *why* a technique scored low: bad retrieval (low faithfulness is
possible even so) vs a wrong/incomplete answer (low correctness). Caveats: LLM judges can be
lenient or biased, and a 3-question set isn't statistically robust — treat as indicative.
"""

import logging
import os
import time

from django.conf import settings
from google import genai
from google.genai import types
from llm_json import loads_lenient


logger = logging.getLogger("evaluation.judge")

MODEL = settings.GEMINI_MODEL
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0


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
    """Return {faithfulness, correctness, reasoning}; retries transient errors."""
    prompt = _prompt(question, reference, candidate, evidence)
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            data = loads_lenient(response.text)
            return {
                "faithfulness": float(data.get("faithfulness", 0)),
                "correctness": float(data.get("correctness", 0)),
                "reasoning": str(data.get("reasoning", "")),
            }
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("evaluation.judge.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise JudgeError(f"judging failed after {MAX_RETRIES} attempts: {last_error}")
