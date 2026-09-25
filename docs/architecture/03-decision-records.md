# CraftyProse Architecture Decision Records

Status of every record: **Accepted 2026-09-25** (`02-architecture-proposal.md` §22.1). ADR-015 and ADR-016 record decisions added at approval. *ER §n* refers to `docs/extraction/01-extraction-report.md`.

**Change rule:** an accepted ADR changes only through a new or superseding record. If implementation evidence shows an ADR must change, the evidence is presented and approved first.

---

## ADR-001: The engine executes reviews; an author never judges its own work

- **Problem.** In lineage B, one model session wrote, fact-checked, edited and final-reviewed. Gates validated only the review's JSON format. The one real run went from brief to "final" in 9.5 minutes with glowing reviews, then failed external review for reading as AI-written. Probes show that zero-finding reviews and self-resolved critical findings reach approval (ER §8.2).
- **Alternatives.**
  1. Keep self-review with stricter prompts.
  2. Require a human reviewer at every stage.
  3. Run reviews as separate, engine-executed calls with least context and validate their output.
- **Decision.** Option 3. Judges are fresh LLM calls made by the engine, seeing only their declared artifacts and EIS slice.
- **Reason.** Prompts can't make a model see what its own context has already rationalized. Humans at every stage recreate A's committee cost. Separate calls are cheap and give real independence.
- **Tradeoffs.** It needs API access and costs money per round. Judges can still be wrong, which ADR-007 and the calibration evals address.
- **Consequences.** A "driven mode", where an external agent executes stages, can't guarantee independence. Its reviews are marked `independent: false` and release policy decides whether to accept them.

## ADR-002: Binary gates and blocking findings; no composite scores

- **Problem.** A's weighted composites (confidence 0–100, CES, voice ≥90) are gameable. Fake evidence scored 109/100 because the weights summed to 1.10. A score also lets an unsupported claim be offset by good structure.
- **Alternatives.**
  1. Fix the formulas.
  2. Combine scores with hard floors.
  3. Use categorical pass/fail validators plus severity-ranked findings, where any critical or major finding blocks.
- **Decision.** Option 3. Scores may appear in reports as diagnostics only, and nothing gates on them.
- **Reason.** B's final gate uses this shape and is the part that held. Binary checks explain themselves.
- **Tradeoffs.** It's less "nuanced". A draft with many minor findings passes (they're listed in the release record).
- **Consequences.** Severity calibration in the failure-pattern library becomes important and is tested.

## ADR-003: Evidence is verified against engine-fetched snapshots

- **Problem.** Neither predecessor checks that a source says what it's claimed to say. A's excerpt extractor returns unrelated text. B checks only that a URL begins with `http`, so a fabricated URL passes.
- **Alternatives.**
  1. Trust the researcher.
  2. Have a judge read sources.
  3. The engine obtains source text itself (its own fetch, the API's web-fetch tool-result block, or a user-supplied document), stores it content-addressed, and verifies every excerpt as a normalized substring. A judge then checks semantic support.
- **Decision.** Option 3.
- **Reason.** A substring check is deterministic, cheap and impossible to talk past. It turns "hallucinated quote" from a judgment into a fact.
- **Tradeoffs.** Pages that can't be fetched can't support claims. Some sites block fetches, and PDFs need extraction.
- **Consequences.** Research can end `blocked`. That is correct behavior, and the user can supply documents instead.

## ADR-004: Claim kind × criticality sets the evidence bar; confidence is rule-derived

- **Problem.** A's knowledge package demanded 10 components and confidence ≥95 for every artifact, which is unattainable for a LinkedIn post and meaningless as computed. B's `is_fact` flag could be flipped to dodge support requirements.
- **Alternatives.**
  1. One universal bar.
  2. Per-content-type bars only.
  3. Per claim: kind (statistic, third-party fact, first-party fact, marketing claim, testimonial, inference, opinion) plus criticality (critical/core/supporting), with content-type overrides.
- **Decision.** Option 3. Confidence is high, medium or low, derived by stated rules with the reasons stored.
- **Reason.** Risk lives in individual claims, not documents. First-party claims need approval, not citations, and YMYL claims need independent primary evidence.
- **Tradeoffs.** Claim classification can be wrong. The evidence judge checks that a claim's kind matches its phrasing (e.g. an inference stated as fact).
- **Consequences.** EIS needs an approved-claims registry (`claims.toml`), inherited from C's "approved proof points".

## ADR-005: Content types are declarative specifications, with optional rule plugins

- **Problem.** The engine must support many types without a conditional tree. A's governance matrix had the right idea but no mechanism. B's only type-specific rule was a word count.
- **Alternatives.**
  1. A subclass per type.
  2. A giant workflow with branches.
  3. TOML specs read by generic validators, plus small per-type rule modules for anything parameters can't express.
- **Decision.** Option 3.
- **Reason.** Adding a type becomes adding a file, and the core stays type-agnostic.
- **Tradeoffs.** Spec expressiveness is limited; some rules will need plugins.
- **Consequences.** A spec schema and loader with validation, plus a test that every spec loads and every referenced judge and rule exists.

## ADR-006: Seven stages

- **Problem.** A had 14 phases and 13 gates, and B had 10 stages. Several stages were separate roles performing the same reasoning (brief vs editorial objective, strategy vs outline, four sequential review stages).
- **Alternatives.** Keep B's 10 stages, or merge by dependency and jurisdiction.
- **Decision.** Intake → research → plan → draft → review (panel) → revise → release.
- **Reason.** Stage boundaries now fall where dependencies change: before research, after research, before writing, after writing. The parallel review panel replaces four serial reviews.
- **Tradeoffs.** The plan artifact is larger. A weak angle is caught at review rather than at a separate plan review.
- **Consequences.** A plan-review judge can be added later if measurement shows weak plans are expensive.

## ADR-007: Three judges with disjoint jurisdictions

- **Problem.** A specified 16 reviewer seats with overlap, unanimity and a 70% target rejection rate. B's editorial reviewer also judged "AI quality", overlapping the human-writing reviewer.
- **Alternatives.**
  1. One judge.
  2. Many specialist judges.
  3. Three judges: evidence (`EV`, `RK`), editorial (`ED`, `DS`), writing (`HW`, `VO`).
- **Decision.** Option 3, with jurisdictions enforced by pattern-ID prefix (judge-output check J5).
- **Reason.** Each judge needs a different context slice: the ledger, the brief and audience, or the voice samples. One judge would mix them. Many judges would duplicate reasoning and cost.
- **Tradeoffs.** A defect on a boundary (e.g. a generic paragraph that is also uncited) may be reported twice. Fingerprints group duplicates.
- **Consequences.** Rejection rate is an observed outcome, never a target.

## ADR-008: Resolution is computed by re-review; defects have a lifecycle

- **Problem.** In B, findings could be marked `resolved: true` by their own reviewer, and a revision with zero resolutions and unchanged text passed.
- **Alternatives.** Trust resolution notes; have a judge confirm each resolution; or re-review the new draft fully and diff findings.
- **Decision.** After every revision, all judges re-review. Findings are fingerprinted (pattern + section + normalized quote) and classified resolved, persistent, new or regression. The revision gate also requires each changed/removed finding's quote to be gone from the text.
- **Reason.** This measures what changed rather than trusting a description of it, and it catches regressions a targeted re-check would miss.
- **Tradeoffs.** Full re-review costs more than targeted re-checks.
- **Consequences.** Persistent defects escalate after two revisions; oscillation is visible in the release record.

## ADR-009: Human writing is detected by calibrated clusters and judged by an independent writing judge; there is no unconditional humanizer pass and no detector score

- **Problem.** B's detector passes known-AI text and was calibrated on a fixture edited until it passed. It also runs at a stage where its defects can't be fixed. C's humanizer is sound but rewrites every draft, which risks drift from the facts, and it runs unenforced.
- **Alternatives.**
  1. Detector APIs.
  2. Deterministic rules only.
  3. A judge only.
  4. An unconditional rewrite pass.
  5. Deterministic cluster detection at the draft gate, calibrated on human and AI corpora, plus a writing judge that must acknowledge every advisory, plus targeted revision with a no-new-facts check.
- **Decision.** Option 5.
- **Reason.** Deterministic rules alone miss paragraph-scale formula. Judges alone are unmeasured. Detectors optimize the wrong target. Targeted revision fixes what's wrong without re-generating what's right.
- **Tradeoffs.** It needs a human-writing corpus with rights (decision D3). The thresholds are empirical.
- **Consequences.** Threshold changes require a corpus re-run, enforced by tests. At approval (D8) this became an explicit rule: human-writing revision is targeted, preserves correct content, and is checked for factual drift, evidence drift, claim changes and new unsupported facts (proposal §9, X4, X7, X8).

## ADR-010: Drafts carry internal claim markers; release converts them

- **Problem.** A's Constitution keeps evidence IDs internal, while its GCV-009 required inline `EVD-` IDs in published text. B's `[S#]` markers stayed in the text.
- **Decision.** Drafts use `{C#}` markers pointing at ledger claims. At release, the renderer converts them to the content type's citation style (inline links, footnotes, a sources note, or none).
- **Reason.** Machine-checkable coverage during production, reader-appropriate citation at release.
- **Consequences.** The writer and reviser must preserve markers, which X1/X3 enforce; the writing and editorial judges see marker-stripped text.

## ADR-011: Python ≥ 3.11, stdlib-first; TOML for EIS and specs, JSON for artifacts, Markdown for drafts

- **Problem.** Choose a runtime that is durable and simple. B's stdlib-only constraint served it well. A depended on bs4, several SaaS APIs and a bespoke agent runtime.
- **Alternatives.** Stdlib only; a Pydantic/YAML stack; TypeScript.
- **Decision.** Python ≥ 3.11 on the stdlib, using `tomllib` for reading specs and brand files and hand-written validators in B's `ValidationResult` style. The only runtime dependency is `anthropic`, as an optional extra.
- **Reason.** The predecessor code knowledge is Python. `tomllib` removes the YAML dependency, and fewer dependencies mean fewer failure modes.
- **Tradeoffs.** No schema library, so validators are more verbose. TOML is slightly less familiar to non-engineers than YAML.
- **Consequences.** The engine can't *write* TOML with the stdlib, so brand scaffolding emits templates as text.

## ADR-012: LLM access through one adapter: Anthropic by default, replay for tests, manual for driven mode

- **Problem.** B never called models, so review independence was impossible. Tests must never depend on the network.
- **Decision.** A `run(role, system, context, task, schema, tools)` protocol with three implementations:
  - `AnthropicLLM`: model and effort per role, structured outputs for JSON artifacts, prompt caching of the stable EIS prefix, web search/fetch server tools for research, refusal handling.
  - `ReplayLLM`: recorded fixtures.
  - `ManualLLM`: staging files, driven mode.
- **Reason.** One seam for testing, cost control and model choice.
- **Consequences.** Recorded fixtures must be refreshed when prompts change, and a test detects stale fixtures by input hash.

## ADR-013: The engine prepares releases; a human releases them

- **Problem.** B's `approve` is a CLI command any agent can run, so "humans own the last call" was not enforceable.
- **Decision.** The final gate yields `ready_for_release` with a full release record. `approve --by <name>` records the approver and moves the item to `released`. The record states that the engine can't verify who ran the command.
- **Reason.** An honest limitation beats a false guarantee. Separating ready from released keeps automated pipelines from publishing by default.
- **Consequences.** Publishing integrations (CMS and others) are out of scope for v1; release produces a package.

## ADR-014: Discoverability is presence plus ceilings, with deterministic structured data

- **Problem.** A's SEO rules demanded exact placements and counts (keyword in H1 + first 100 words + H2 + conclusion + meta; meta 150–155 characters; CTAs at 25/50/75%), which pushes toward stuffing and templates. Its brief chose copy by keyword count.
- **Decision.** Deterministic checks for presence (primary question in title/H1 and intro), length ranges and ceilings (keyword density maximum), real internal links (EIS pages only) and heading structure. Intent and answer quality go to the editorial judge. JSON-LD is generated from final content.
- **Reason.** SEO must not override usefulness, truth or voice, so rules can require things to be present but can never require repetition.
- **Consequences.** A discoverability finding can't be resolved by removing evidence or voice (revision check X5).

## ADR-015: Research runs behind a provider adapter; evidence only from retrieved or supplied content

- **Problem.** Research must not be tied to one provider, and the evidence rule (ADR-003) must hold whatever provider is used.
- **Decision.** Research goes through a provider interface. The first providers are Anthropic web search/fetch and user-supplied documents. A provider returns retrieved documents; the engine stores and hashes them as snapshots. Model-written text is never accepted as source content.
- **Reason.** Approval decision D6.
- **Consequences.** Adding a provider (e.g. a search API with its own fetcher) needs no core change. Every provider is subject to the same excerpt verification.

## ADR-016: Metering from the first milestone

- **Problem.** Cost and quality tradeoffs can't be judged without measurement, and retrofitting instrumentation after the build misses early behavior.
- **Decision.** Every LLM call is recorded through a metering wrapper around whichever adapter is in use. The record covers work item, stage, role, adapter, model, latency, token classes, client tool calls, server tool uses, stop reason and cost. Cost comes from a versioned pricing table, and anything without a price is reported as unpriced, never as zero. Per-item summaries add attempts, revisions and stage wall time.
- **Reason.** Approval decision D1: measure, don't optimize yet.
- **Consequences.** Replay fixtures carry recorded usage, so metering is exercised by the normal test suite. The pricing table must be kept current with published rates.
