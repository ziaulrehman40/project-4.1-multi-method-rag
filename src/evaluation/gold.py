"""Gold question-and-answer set for evaluation.

All four techniques build over the SAME corpus (see corpus.py), so every question is a fair
four-way comparison: each technique HAS the source document and either retrieves it or doesn't.
The set spans all four documents and is tagged by the capability it tests:

- semantic / structural / table questions are answerable by every technique (the text of the
  PDF's tables reaches the text techniques via the markdown rendition).
- the `figure` question's answer lives ONLY in a chart's pixels, so multimodal should win it
  while the text techniques have the surrounding prose but not the numbers — the honest
  demonstration of what multimodal adds.

Kept small on purpose: a full run is gold_size x 4 techniques x (answer pipeline + judge), so
a rate-limited provider can hit a quota. Add or change questions freely.
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
        "type": "structural",  # "how must X be protected" — spread across the PCI policy
        "question": "How must the primary account number (PAN) be protected when stored?",
        "expected_answer": "Stored PAN must be rendered unreadable using strong cryptography.",
        "expected_sources": ["pci-dss-excerpt.md"],
    },
    {
        "type": "structural",  # control-table lookup in the SOC 2 policy
        "question": "How often must privileged access be reviewed?",
        "expected_answer": "Every three months.",
        "expected_sources": ["soc2-excerpt.md"],
    },
    {
        "type": "table",  # answer lives in a PDF table (reaches text techniques via rendition)
        "question": "Within how long must a Critical incident be notified?",
        "expected_answer": "Within 24 hours.",
        "expected_sources": ["compliance-metrics.pdf"],
    },
    {
        "type": "figure",  # answer lives ONLY in a chart image — multimodal's strength
        "question": "Which security incident category was most common in 2025?",
        "expected_answer": "Phishing (the highest bar in the incidents-by-category chart).",
        "expected_sources": ["compliance-metrics.pdf"],
    },
]
