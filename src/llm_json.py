"""Lenient JSON parsing for LLM output.

Even with response_mime_type=application/json, models occasionally emit small quirks —
markdown code fences or a trailing comma before a closing bracket (e.g. `[2,]` or `[,]`
when they mean "nothing"). `loads_lenient` cleans those before json.loads so a cosmetic
quirk doesn't crash a whole technique.
"""

import json
import re


def loads_lenient(text):
    cleaned = text.strip()
    # Strip a ```json ... ``` (or bare ```) fence if the model wrapped the output.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned).strip()
    # Remove a trailing comma directly before a closing ] or } (with optional whitespace).
    cleaned = re.sub(r",(\s*[\]}])", r"\1", cleaned)
    return json.loads(cleaned)
