# CraftyProse

A content engine for business and marketing content. It researches, plans, writes, reviews independently, revises against specific defects, and releases only what passes real gates.

## Status

**Architecture approved 2026-09-25.** Milestone M1 (core engine) is built and tested.

| Phase | State |
|---|---|
| 1. Repository archaeology | Done |
| 2. Methodology extraction | Done |
| 3. Architecture | Approved |
| 4. Architectural review | Approved (decisions in proposal §22.1) |
| 5. Build | M1 core done ([progress note](docs/progress/M1-core.md)); M2 next |
| 6–7. Validate, adversarial QA | Not started |

## Run the tests

Python 3.11 or later, no dependencies:

```bash
python -m unittest discover -s tests -t .
```

The suite never touches the network.

## Read in this order

1. [`docs/extraction/01-extraction-report.md`](docs/extraction/01-extraction-report.md): what the three predecessor lineages did, what actually worked (with evidence), and the reuse/rebuild matrix.
2. [`docs/architecture/02-architecture-proposal.md`](docs/architecture/02-architecture-proposal.md): the approved engine design. §20 is the architectural review; §22.1 records the approval decisions.
3. [`docs/architecture/03-decision-records.md`](docs/architecture/03-decision-records.md): why each major choice was made, and what was rejected.

## Evidence

`docs/extraction/evidence/` holds the scripts used to test predecessor behavior, with their captured output. See its README for how to re-run them.
