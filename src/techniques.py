"""Shared helpers for the four retrieval techniques.

Before this, each technique's answer.py copied the same generation call, cost constants,
est-cost maths, latency timing, metrics-dict assembly, and a bespoke error class. Nothing
discriminated those per-technique error classes (the chat view caught them identically, the
eval registry caught bare Exception), so they are collapsed into one `TechniqueError`.
"""

import time

from llm import active_generation_model, get_generation_provider


class TechniqueError(RuntimeError):
    """A retrieval technique failed to produce an answer (retrieval, embedding, or generation)."""


def run_generation(parts, *, max_tokens=None):
    """One generation call through the active provider. `parts` is a prompt string or a list of
    str/Image parts (multimodal). Returns the `Generation`. This is the seam technique tests
    mock, so the answer pipelines can be exercised without a live provider."""
    if isinstance(parts, str):
        parts = [parts]
    return get_generation_provider().generate(parts, max_tokens=max_tokens)


def finalize_metrics(generation, start, **extra):
    """The metrics dict every technique reports: token usage + latency + estimated cost + model.

    Cost uses the ACTIVE provider's own per-1M rates, so the Stage-5 cost comparison is honest
    when the provider is swapped (before, one hardcoded Gemini rate was applied to every
    provider). `extra` carries the technique's own count (edges_used / sections_opened / …)."""
    provider = get_generation_provider()
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    est_cost = (generation.input_tokens / 1_000_000 * provider.input_usd_per_1m
                + generation.output_tokens / 1_000_000 * provider.output_usd_per_1m)
    return {
        "input_tokens": generation.input_tokens,
        "output_tokens": generation.output_tokens,
        "total_tokens": generation.total_tokens,
        "latency_ms": latency_ms,
        "est_cost_usd": round(est_cost, 6),
        "model": active_generation_model(),
        **extra,
    }
