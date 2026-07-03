# Sample Documents

These are the documents you build every retrieval technique against. They are deliberately small and known, so your results are repeatable and your tests can assert on specific answers.

**Important:** these files are illustrative, simplified policy excerpts written for this exercise. They are not official or complete versions of any real standard. Do not treat them as compliance advice. They exist only to give you realistic, structured, table-containing text to retrieve over.

## Files

- `pci-dss-excerpt.md` — illustrative payment-security controls, with a requirements table.
- `gdpr-excerpt.md` — illustrative data-protection principles and data-subject rights.
- `soc2-excerpt.md` — illustrative trust-service criteria, with a controls table.

## Suggested gold question and answer set

Use questions like these for your Stage 5 evaluation harness. Because the documents are known, the expected answer and its source are known too, so you can score each technique honestly.

| # | Question | Expected source | Expected answer (short) |
|---|---|---|---|
| 1 | How often must access rights be reviewed? | pci-dss-excerpt.md, Requirement 7 | At least every six months |
| 2 | What is the minimum password length required? | pci-dss-excerpt.md, controls table | 12 characters |
| 3 | What are the six data-protection principles listed? | gdpr-excerpt.md | Lawfulness, purpose limitation, data minimisation, accuracy, storage limitation, integrity and confidentiality |
| 4 | Within how many hours must a personal data breach be reported? | gdpr-excerpt.md, breach section | 72 hours |
| 5 | Which trust-service criteria are in scope? | soc2-excerpt.md, criteria table | Security, Availability, Confidentiality |
| 6 | How long are audit logs retained? | soc2-excerpt.md, controls table | 12 months |

Add or change questions freely. A table question (2, 5, 6) is useful for showing the difference the multimodal stage makes.

## Adding your own

You can convert these to PDF, or drop in your own short policy documents, as long as you keep a known answer set so retrieval stays testable.
