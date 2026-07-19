"""Gold question-and-answer set for evaluation.

Kept to THREE questions on purpose: the Gemini free tier allows ~20 generate requests/day,
and one full run is roughly gold_size x 4 techniques x (answer pipeline + judge) — so even
three questions can approach the daily cap. Each question is tagged by the capability it
tests, so results can be reported per category (showing each technique's strength).
"""

GOLD = [
    {
        "type": "semantic",  # meaning match — embedding RAG's strength
        "question": "How quickly must a personal data breach be reported, and to whom?",
        "expected_answer": "Without undue delay and no later than 72 hours after becoming "
                           "aware of it, to the supervisory authority.",
        "expected_sources": ["gdpr-excerpt.md"],
    },
    {
        "type": "structural",  # "what's in section X" — vectorless/graph strength
        "question": "What rights does a data subject have?",
        "expected_answer": "Rights include being informed, access, rectification, erasure, "
                           "restriction, data portability, and to object.",
        "expected_sources": ["gdpr-excerpt.md"],
    },
    {
        "type": "multimodal",  # answer lives in a chart image — multimodal's strength
        "question": "Which security incident category was most common in 2025?",
        "expected_answer": "Phishing (the highest bar in the incidents-by-category chart).",
        "expected_sources": ["compliance-metrics.pdf"],
    },
]
