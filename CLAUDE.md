# CraftyProse: notes for Claude sessions

CraftyProse is a gated content engine for business and marketing content. It researches, plans, writes, reviews independently, revises against specific defects, and prepares releases that a person approves. Python ≥ 3.11, stdlib only (the `anthropic` SDK is an optional extra for milestone M8).

## Read first

1. `docs/architecture/02-architecture-proposal.md`: the **approved** design (approved 2026-09-25). §22.1 lists the approval decisions D1–D10; §19 is the milestone plan.
2. `docs/architecture/03-decision-records.md`: ADR-001 to ADR-016, all **Accepted**.
3. `docs/progress/M1-core.md` and `docs/progress/M2-eis.md`: what each milestone built, what was decided along the way, and what's unresolved.
4. `docs/extraction/01-extraction-report.md`: why the design is what it is (lessons from the predecessor code).

## Status (2026-09-26)

- **M1 core:** merged to `main` via PR #1 (`9777cf5`).
- **M2 EIS + content types:** on branch `m2-eis`. See `git log` for whether it has been committed, pushed or merged.
- **Next: M3 evidence (architecture §4, §19).**
  - A research-provider adapter (ADR-015): Anthropic web search/fetch plus user-supplied documents.
  - Engine-fetched, content-addressed snapshots.
  - Verbatim excerpt verification (R1).
  - `eis/standards/source_rules.toml` (authority classes, excluded sources).
  - The claim-kind × criticality rules R2–R8, rule-derived confidence, and the research gate.
  - Evidence may only come from content the engine retrieved or the user supplied.
- Then M4 intake + plan (with `ManualLLM`), M5 draft checks + writing-pattern catalog + calibration corpus, M6 judges + revision, M7 release, M8 `AnthropicLLM` and live runs.

## Standing rules from the owner

- **Don't change an accepted ADR silently.** If implementation evidence says one must change, stop at that decision and explain the evidence first.
- **Minimum scope.** Build the smallest complete version of each milestone. Add no agents, stages, dependencies or infrastructure without a concrete need.
- **Test-first.** Tests are written alongside the code. The normal suite never touches the network or the API; `tests/__init__.py` blocks sockets. Deterministic LLM behavior uses `ReplayLLM` fixtures.
- **Metering from the start; no premature cost optimization.** Unpriced models and tools are reported as unpriced, never as zero.
- **Release.** Every content type needs human approval. The engine may reach `ready_for_release` but never releases or publishes in v1. Flagged, unconfirmed, unsupported or blocked claims never enter the releasable package.
- **Human-writing revision is targeted, never an unconditional rewrite.** Check it for factual drift, evidence drift, claim changes and new unsupported facts.
- **Human-writing corpus.** Use material the owner has rights to first, then licensed or public-domain material. Never assume scraped text is human. Every sample keeps provenance and rights metadata (`eis/provenance.py`).
- **Test material.**
  - No Harmony Homes material, ever.
  - The Metanous work item W-20260916-001 and its drafts may be used as **known-AI adversarial fixtures**, not as a detector-gaming target. They live outside this repo at `C:\Users\mohdo\Documents\Metanous\content\W-20260916-001`. This repo is **public**, so ask before copying them in.
- **Milestone reports** cover: files created/changed, tests added, behavior implemented, test results, unresolved issues, and decisions discovered during implementation.

## Working conventions

- **Run tests:** `python -m unittest discover -s tests -t .` from the repo root (about 15 s).
- **Layout:**
  - `craftyprose/core/`: state machine, gates, findings, artifacts, schema reader.
  - `craftyprose/runtime/`: LLM contract, replay, pricing, metering.
  - `craftyprose/eis/`: brand workspace, guardrails, context slices, standards.
  - `craftyprose/content_types/`: loader plus `specs/*.toml`.
  - `examples/workspace/brands/fernhill/`: a fictional brand used by the tests.
- **Invariants to keep:**
  - Submissions are persisted before gating, and every gate run is recorded.
  - Review and release artifacts are engine-only.
  - A passed revision becomes the draft before routing.
  - Findings can't carry `resolved`, `verdict`, `status` or `source`.
  - Verdicts are computed from severity.
  - The lifecycle's allowed routes are fixed in `core/lifecycle.py`.
- **Style:** match the surrounding code. Plain docstrings that explain why; no new dependencies.
- **Line endings:** pinned to LF (`.gitattributes`). The engine normalizes newlines before hashing.
- **Git workflow:**
  - One branch per milestone (`m3-evidence`, ...) from `main`.
  - End commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - The `gh` CLI isn't installed. To open a PR, use the GitHub compare page (`https://github.com/osamaali-sys/CraftyProse/compare/main...<branch>?expand=1`) in the in-app browser, which has been signed in as `osamaali-sys`.
  - To merge, a local `git merge --no-ff <branch> -m "Merge pull request #N from osamaali-sys/<branch>"` pushed to `main` marks the PR as merged.
  - Commit, push and merge only when asked.

## Open items carried forward

- **Where deterministic draft-quality defects go** (gate retry vs review-round finding) is deferred to M5/M6. If it affects ADR-006 or ADR-008, it goes back for approval.
- **Web search/fetch prices** aren't in `runtime/pricing.toml` (cached from 2026-06-24); they need confirming.
- **No verified human voice samples yet;** the example brand's samples are synthetic.
- **Single-writer assumption** (no file locking).
