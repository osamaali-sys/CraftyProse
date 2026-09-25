# CraftyProse Content Engine Extraction Report

**Phase:** 1 (repository archaeology) and 2 (methodology extraction)
**Date:** 2026-09-24
**Status:** Complete. Feeds `docs/architecture/02-architecture-proposal.md`.
**Evidence:** every behavioral claim marked **[verified]** was reproduced by running code. Scripts and outputs are in `docs/extraction/evidence/`.

---

## 0. The answer in one page

> *What did we learn from the Click Savvy content engine that is worth carrying into CraftyProse, why is it worth carrying, and how should CraftyProse implement it differently?*

The "Click Savvy content engine" is three separate attempts by the same owner. Each attempt fixed the previous one's biggest weakness and introduced a new one.

| Lineage | Where | What it is | Strongest idea | Fatal weakness |
|---|---|---|---|---|
| **A. Click Savvy OS / EIS** (Jul 2026) | `Downloads/ClickSavvy-SEO-main` | 18 EIS standards (7,343 lines), 124 agent prompts, 4,136 lines of Python services | The editorial discipline: knowledge before writing, claims tied to evidence, structured rejection, a failure taxonomy | Almost nothing runs. The services crash on their own demos, the confidence gate authorizes invented evidence with a score of 109/100, there are no tests, and practice diverged from the standards **[verified]** |
| **B. Metanous content engine** (Sep 16–18 2026) | `Documents/Metanous/content-engine` | A 10-stage gated pipeline in stdlib Python with 71 passing tests | Deterministic gates, artifact-first state, immutable history, bounded revision loops | The same model wrote and reviewed. Reviews are validated only for format, so they rubber-stamp. The one real run went from brief to "final" in 9.5 minutes, and its output was later judged strongly AI-written **[verified]** |
| **C. Harmony Homes skills** (Sep 24 2026) | `Documents/Harmony homes` | Two Claude skills (`content-humanizer`, `harmony-blog-engine`) plus a structured client knowledge doc | A knowledge base as the single source of truth, `[CONFIRM]` markers instead of guesses, a 33-pattern humanizer with a marketing mode, and a human choosing the topic | No code, no tests, one client. Enforcement is the model checking its own work |

**What is worth carrying, and why:**

1. **Knowledge before writing (A, B, C).** Every failure mode that matters, such as a hallucinated statistic or generic filler, starts when the writer is also the researcher. All three lineages converge on this principle.
2. **Claims as first-class objects with provenance (A's design, B's partial implementation).** A claim you can't trace can't be checked, and a claim that can't be checked can't be gated.
3. **Explicit unknowns (A's knowledge gaps, B's `uncertainty`/`gaps`, C's `[CONFIRM]` and open questions).** Of every mechanism in the predecessor, this one best prevents confident fabrication.
4. **Gates are code; a score never compensates for a blocking defect (B).** B's aggregate final gate is the right shape. A's weighted composites were the wrong shape, and the 109/100 result shows why.
5. **Artifact-first, versioned, reproducible from disk (B).** This is proven by tests and by a real bug B found and fixed: the draft-persistence invariant.
6. **Defect-driven revision with a finding schema and severity semantics (B).** It worked once in production: fact-check finding FC-1 was raised, revised and re-checked.
7. **A failure-pattern taxonomy shared by reviewers, validators, revision and learning (A).** It gives the system a vocabulary for why something failed.
8. **Human writing as pattern clusters plus specificity plus voice, never as a detector score (B's standard, C's humanizer).**
9. **Voice discovered from evidence (A's voice profile, C's before/after pairs and word lists).**
10. **Content types as specifications, each with its own goal, knowledge needs and gates (A's governance matrix).**

**What CraftyProse must do differently:**

1. **Independent evaluation.** B's central lesson, learned the hard way: the author cannot be the judge. Reviews run as separate engine-executed calls that see artifacts, not the author's reasoning. Review verdicts are checked for substance: quoted evidence must exist in the draft, rubric criteria must be answered, and deterministic warnings must be addressed. A well-formed JSON verdict is not enough.
2. **Deterministic verification wherever the predecessor trusted self-report.** Excerpts must appear in fetched source snapshots. Every factual sentence must carry a claim marker. Resolution is computed by re-review, never declared by the reviewer or reviser. Reviews are bound to the hash of the draft they judged.
3. **Evidence rules scaled to content type and claim criticality.** A replaces the 10-component, confidence-≥95 package that no LinkedIn post could ever satisfy.
4. **No template-forcing validators.** A's GCV required a trade-off table, a numbered decision framework, three mistakes, two severity-labeled warnings, CTAs at 25/50/75% and first-person "in my experience" markers. Validators like that manufacture the formulaic, fabricated-experience content the constitution forbids.
5. **Human-writing detection calibrated on real corpora.** B's validator passes a draft with 11 "X is not Y. It is Z" constructions, and its own "clean" fixture is saturated with the same pattern **[verified]**.
6. **Minimum necessary complexity.** This means 7 LLM roles instead of 124 agents or 16 reviewer seats, and 7 stages instead of 13 gates.

---

## 1. Scope and method

**Inspected in full:** all 18 EIS standards and 7 draft standards; all Python in `infrastructure/`; the EIS agents; content agents; content workflows, templates, QA checklist, ADRs and project state config (A). The whole Metanous engine, its tests, docs, implementation reports and the one real work item (B). Both Harmony skills and the knowledge doc's section structure (C).

**Executed:** A's services (all self-tests plus targeted probes), B's test suite (71/71 pass), and probes against B's gates and human-writing validator.

**Deliberately not inspected:**
- `03-VAULT/internal/inbox/` (9,754 ingested email files). This is business correspondence, not engine code.
- The content of the Harmony knowledge doc and marketing briefs. I read only its section headings, to learn the schema. This is client data and must not enter CraftyProse.
- The React/Express dashboard. `DASHBOARD_CURRENT_STATE.md` describes it, but its code is not in the repository.

**Assumption to confirm:** you named "the Click Savvy content-engine codebase". EIS lives in lineage A, but B and C are clearly its successors: same owner, same concepts, and B's reports reference A's ideas. I treated all three as the predecessor.

---

## 2. Repository map

### Lineage A: `ClickSavvy-SEO-main` (10,191 files)

| Path | Files | Contents | Engine-relevant? |
|---|---|---|---|
| `docs/editorial-intelligence-system/` | 18 + 7 | EIS v1.0 standards 00–16 (two numbered 11), v0.1 draft standards | **Core** |
| `infrastructure/` | 6 .py | `evidence/service.py`, `knowledge/kp_service.py`, `execution/engine.py`, `validation/gcv.py` + `gcv_validators.py`, `writing/declaration.py` | **Core (implementation)** |
| `agents/editorial-intelligence/` | 4 | EI lead, business-opportunity miner, knowledge-package assembler, readiness scoring | **Core** |
| `01-AGENTS/content/` | 15 | 13 content agents, `CONTENT-DEPARTMENT-EIS-INTEGRATION.md` (1,009 lines), sprint plan | **Core** |
| `01-AGENTS/{aeo,keywords,research,competitor}/` | ~30 | SEO/AEO specialist prompts | Partial (discoverability knowledge) |
| `01-AGENTS/{sales,finance,legal,ops,client-success,web,local,links,technical,ecommerce,analytics,audit,strategy,executive,internal}` | ~80 | Agency operations | No |
| `02-INSTRUCTIONS/` | 27 | Team instructions, quality standards, data flow | Partial |
| `05-QUALITY/qa-checklist.md`, `06-TEMPLATES/content-brief.md`, `07-WORKFLOWS/content-sprint.md` | 3 | QA scoring (3/5 passes), brief template, content workflow | Partial |
| `docs/click-savvy-os/` | 15 | Vision, architecture, ADRs 001–010, roadmap, sprint | Context (lessons in the ADRs) |
| `skills/`, `scheduler/`, `10-SCRIPTS/`, `config/`, `.hermes*`, `.obsidian` | ~30 | Tool-skill YAML, cron jobs, email ingest, backup, project state machine | No |
| `03-VAULT/` | 9,903 | Obsidian vault: 9,754 emails, dashboard notes, kanban, brand/legal | No |
| `04-OUTPUT/` | 8 | One real brief (Harmony Homes move-out cleaning), internal test outputs | Evidence of practice |

### Lineage B: `Metanous/content-engine` (≈4,600 lines)

| Path | Lines | Contents |
|---|---|---|
| `engine/orchestrator.py` | 427 | State machine: `new`, `submit`, `approve`, `reject`, `build_ctx`, routing, budgets |
| `engine/stages.py` | 561 | Stage registry and 10 stage prompts |
| `engine/artifacts.py` | 226 | Atomic writes, versioning, state, history |
| `engine/models.py`, `config.py`, `cli.py` | 369 | `ValidationResult`, text helpers, thresholds, CLI |
| `engine/validators/` (13 modules) | 1,842 | Brief, sources, claims, strategy, outline, structure, citations, metadata, revision, final, artifacts, human_writing (1,121) |
| `tests/` | 1,177 | 71 tests: validators, orchestrator lifecycle, fixtures |
| `docs/ARCHITECTURE.md`, `HUMAN_WRITING_STANDARD.md` | 529 | Design notes and the human-writing standard |
| `../content/W-20260916-001/` | — | The one real work item: brief → research → … → final, awaiting approval |

### Lineage C: `Harmony homes`

| Path | Contents |
|---|---|
| `.claude/skills/content-humanizer/SKILL.md` | 33-pattern AI-tell catalog with reference and marketing modes, SEO preservation, no-fabrication rules |
| `_to install/harmony-blog-engine/SKILL.md` | Weekly cycle: pitch 3 options, draft the chosen one, humanize, fact-check, deliver a docx pack, log it |
| `Harmony homes knowledge.docx` | Client knowledge base, 13 sections plus an appendix (schema only examined) |
| `Harmony blog log.md` | Published and pitched topics, used to avoid repetition |

---

## 3. Content-engine boundary

Everything that decides **what to say, whether it is true, how it should sound, and whether it may be released** is inside the engine. Everything that runs an agency is outside it.

| Inside the engine (studied) | Outside the engine (not carried) |
|---|---|
| EIS standards; knowledge packages; evidence; voice; editorial review; failure patterns; human-quality framework; artifact governance; legal-risk rules | Sales, finance, legal operations, client success, onboarding |
| Research methodology; brief, strategy, outline, draft and review stages | Kanban, dashboard, scheduler, email ingest, backups, Obsidian vault |
| Deterministic validators and gates; revision loop; approval | Hermes/AionUI runtime, OpenRouter free-tier model strategy |
| Discoverability rules (SEO/AEO structure, schema, answer-first) | Technical SEO audits, link building, GBP, e-commerce feeds, rank tracking, reporting |
| Human-writing detection and remediation | ROI trackers, per-article pricing, content-velocity quotas |

---

## 4. EIS map: what EIS actually was

### 4.1 EIS as specified (lineage A)

EIS ("Editorial Intelligence System") is a constitution plus 17 standards. Its self-described purpose is editorial sovereignty: nothing, including a client request, overrides it. Stripped of ceremony, it specifies five things:

| Function | Standards | Essence |
|---|---|---|
| **Principles** | 00 Constitution, 14 Excellence | Objective hierarchy: Truth > Usefulness > Expertise > Specificity > Trust > SEO. Non-negotiables: no hallucinated facts, fabricated experience, fake case studies, keyword stuffing or filler. |
| **Knowledge** | 11 Knowledge Package, 03 Research, 12 Asset Library, 04 Graph | A per-topic package of 10 intelligence components (business, industry, regional, customer, search, competitor, evidence, expertise, gaps, editorial objective). This is the only artifact that authorizes writing. |
| **Evidence and confidence** | 02 Evidence, 13 Confidence | Evidence items with tiers, excluded source types, verbatim excerpts, criticality roles, coverage ≥90%, confidence ≥95, and drift states. |
| **Judgment** | 05 Editorial Review, 06 Human Quality, 08 Voice, 10 GCV, 11 Legal, 15 Failure Patterns | 11 blind reviewers with veto power; a 5-question trust test; a voice score ≥90; 38 automated validators (as documented); YMYL legal review; a 52-pattern failure taxonomy (three IDs used twice). |
| **Lifecycle and learning** | 01 Lifecycle, 07 Learning, 09 Evergreen, 16 Artifact Governance | 14 phases, 13 gates, 3 content paths, learning signals, drift monitoring, per-artifact-type governance. |

**Implementation status:** 14 of the 18 standards say "Architecture — Not Yet Implemented". Three say "Ready for Implementation" and one says "Frozen". The Python services implement fragments of 02, 11, 13, 01 and 10, and none of them works end-to-end (§8).

### 4.2 EIS as practiced (lineages B and C)

The later lineages never mention "EIS", but they implement its useful core:

| EIS function | B (Metanous) | C (Harmony) |
|---|---|---|
| Source of truth about the brand | `knowledge-base/` read by the brief stage ("use only facts from the knowledge base") | Knowledge doc, re-read every run; the engine stops if it is unreachable |
| Approved first-party claims | Not separated | §4 "Approved proof points", with customer quotes |
| Guardrails | Prompt rules | §2 "Non-negotiable guardrails" and skill hard rules (no pricing, no unlaunched brand names, company voice only) |
| Audience | `brief.target_audience` | §5 "Who we write for" |
| Voice | `brief.tone/voice` (one line each) | §6 personality, writing rules, words to use/avoid, **before/after pairs**, humanizer pass |
| Evidence | `research.json` sources and findings (`is_fact`, `confidence`, `uncertainty`, `conflicts`, `gaps`) | "Every claim traces to the knowledge doc or a linked source; otherwise `[CONFIRM]`" |
| Knowledge gaps | `gaps`, `unresolved_uncertainties` | §11 "Open questions and contradictions to resolve" |
| Strategy and anatomy | `strategy.json` (angle, hierarchy, evidence map) | §8 pillars, formats for search and AI answers, **anatomy of every post** |
| Quality criteria | Stage prompts plus validators | §10.2 checklist |
| Memory across pieces | None | Blog log and topic bank |

### 4.3 What EIS accomplished and what it should become

**The actual contribution of EIS** is a coherent answer to "what must be known, allowed and true before content is written, and what must be judged before it is released." That answer is correct. The implementation strategy was wrong: exhaustive, numeric, human-committee-shaped, and not proportional to the content.

**For CraftyProse, EIS should be the governed context and judgment layer.** It holds what is true, what is allowed, who we speak to and as whom, what the piece is for, and what "good" and "defective" mean. It supplies each stage with a declared slice of that context and records every judgment against it. EIS does not move work (orchestration does) and it does not write (agents do). Detailed boundaries are in the architecture proposal, §3.

---

## 5. Agent map

| Lineage | Agents | Structure | Observations |
|---|---|---|---|
| A | 124 prompt files in 19 teams; 13 content agents; 4 EI agents; specified reviewer seats: 11 editorial board + 5 HQF evaluators | Prompt files read by one runtime (Hermes) that "becomes" each agent | Duplicates: `blog-writer` vs `seo-blog-writer`, two `outreach-writer`s (ADR-010 admits this). 5 of the 11 board roles reappear as HQF evaluators. EI agents reference `system/teamlead-base` and `contracts/artifact-contract`, which don't exist. The blog writer "researches for freshness", which contradicts the EIS rule that writers don't research. |
| B | 10 stage prompts (brief, research, strategy, outline, draft, factcheck, editorial, human_writing, final_review, revision) | One model session executes every stage through a CLI; the engine never calls a model | The writer, fact-checker, editor and final reviewer are the same session with the same context. This is the root cause of the rubber-stamp failure (§8.2). |
| C | 2 skills (humanizer; blog engine with 3 modes) | A human drives it in chat | Small and effective; judgment is self-applied. |

**Pattern worth keeping (A, EI agents):** explicit failure handling in agent contracts:
- *Missing inputs* → emit a missing-inputs note with exact paths; do not fabricate.
- *Conflicting data* → surface both sides under "Conflicting Findings"; do not choose a winner.
- *Tool blocked* → `status: blocked`, never `complete`.

---

## 6. Workflow map

| Lineage | Lifecycle | Gates | Loops and escalation |
|---|---|---|---|
| A (spec) | Discovery ×6 → evidence → KP assembly → research review → confidence → editorial board → writing → SEO layer → AEO layer → quality validation → voice → publish → evergreen → learning | 13 (0–12), all "hard"; paths Express/Standard/Authority | Max 2 retries per gate, then escalate to a department lead; 70% first-review rejection is a target |
| A (practice) | `content-sprint.md`: calendar → SERP top-10 → brief → write → meta → FAQ → optimize → QA (3/5 passes). "4–8 publish-ready articles in a single session", logged at "$500–$800 per article" | 1 advisory | Below 3/5, back to writing |
| B | brief → research → strategy → outline → draft → factcheck → editorial → human_writing → final_review → final → **human approve** | 13 deterministic validators plus review verdicts plus aggregate final gate | Attempts budget 3 per stage and revisions budget 3, each ending in `requires_human_review`; a revision returns to factcheck |
| C | pitch 3 options → **human picks** → draft to anatomy → humanize (marketing mode) → fact trace and checklist → docx pack → log | Model-run checklist, dash scan, `[CONFIRM]` list | Human reviews the pack |

The contradiction between A's constitution and A's practice is itself a finding. The constitution bans "content velocity quotas" and puts SEO last, yet the working workflow optimizes for articles per session and SERP-mirroring. The one real brief (`04-OUTPUT/blog/move-in-move-out-cleaning-brief.md`) assigns nine secondary keywords to one post and picks its meta description because it "includes 5+ gap keywords." **Standards that are not enforced in the path of work do not govern the work.**

---

## 7. Artifact map

| Artifact | A (spec / implemented) | B | C | CraftyProse fate |
|---|---|---|---|---|
| Request / brief | Strategy brief (spec) | `request.md`, `brief.json` | Chosen pitch | **Brief** (adapted) |
| Knowledge package | 10 components (implemented, broken) | Split across `research.json` and `strategy.json` | Knowledge doc plus pitch | **Knowledge package** (proportional) |
| Evidence | Evidence item YAML (implemented, broken) | `research.sources/findings` | Source list | **Source snapshots, evidence items, claims ledger** |
| Confidence report | 0–100 composite | — | — | Replaced by rule-derived categorical confidence |
| Outline | — | `outline.md` | Pitch outline | Folded into the plan |
| Draft | Draft article plus writer declaration | `drafts/draft-vN.md` | Draft | **Draft** with internal claim markers |
| Reviews | 11 verdicts, HQF scorecards, voice scorecard, GCV report, CES | `reviews/<stage>-vN.json` | — | **Review round** (3 judges plus deterministic report) bound to draft hash |
| Revision | — | `revisions/revision-vN.json` | — | **Revision** with a resolution ledger |
| Validation record | Gate transition JSONL | `validations/` (documented, not written on submit **[verified]**) | — | **Every gate run recorded** |
| Release | Publication archive | `approved/final.md`, `approval.json` | Docx pack: post, SEO block, FAQ, photo brief, repurposing, sources, `[CONFIRM]` list | **Release package** plus decision record |
| Cross-piece memory | Learning signals, KAL (spec) | — | Blog log | **Content log and learning log** |

---

## 8. Validator and gate map (verified behavior)

### 8.1 Lineage A: `infrastructure/`

| Component | Claimed role | Actual behavior **[verified]** |
|---|---|---|
| `GCVEngine` ("38 validators" per its docs) | Final automated quality gate | **Cannot be constructed.** `NameError: FirstPersonExperienceValidator`. `gcv_validators.py` has no imports and `gcv.py` never imports it. Duplicate IDs silently overwrite validators (GCV-016, -023, -029, -037). |
| GCV-001 trade-offs | Detects comparison tables | Iterates the characters of the joined header string, so a real Pros/Cons table fails. |
| GCV-009 evidence refs | Every claim has an inline `EVD-` id | Treats any sentence over 30 characters containing "is" (including "this") as a factual claim. It also requires evidence IDs in published text, which contradicts Constitution §3.3 ("Evidence IDs never appear in published content"). |
| `EvidenceService.ingest_evidence` | Evidence ingestion | **Always crashes** (`TypeError: access_date`). When claim overlap is low, the excerpt extractor returns the first 5,000 characters of any source as "supporting evidence". Drift checks and excerpt verification are placeholders that return "unchanged" or `True`. |
| `KPService` | KP lifecycle and confidence gate | **Cannot reload its own files.** Enums are saved as `"KPStatus.DRAFT"`, so the second write crashes. Confidence is computed from self-reported `evidence_confidence`, and coverage from a self-declared `coverage_status`. The component weights sum to **1.10**. Result: **fake evidence ID plus self-declared 99 gives a score of 109, status "authorized"**. |
| `ExecutionEngine` | Enforce all gates | **Deadlocks.** Gate N is marked passed only when you move to N+1, and moving to N+1 requires N to be passed. Its own self-test fails at gates 0 and 1. State is in memory only. "Artifacts verified" means a string key exists (`# TODO: Add artifact validity checks`). Express paths can't skip gates because sequencing is strictly +1. |
| `WriterDeclarationService` | "The critical enforcement point that prevents hallucination" | The writer sets seven booleans, including `no_fabrication = True`, and signs with an HMAC secret derived from the writer ID plus a hard-coded salt. It can't reload its own saved files, and it never examines the draft. |
| `05-QUALITY/qa-checklist.md` | Delivery gate | 3/5 is "acceptable, deliver". |

`CONTENT-DEPARTMENT-EIS-INTEGRATION.md` §5 is titled "Regression analysis — proof of no bypass paths". No code or test backs that claim.

### 8.2 Lineage B: Metanous validators and gates

| Gate | What it checks | Holds? |
|---|---|---|
| `validate_brief` | Required fields, allowed content type, no placeholders | Yes |
| `validate_sources` | ≥3 sources, ≥2 domains, URL format, ratings, findings reference sources | Structure only. A **fabricated URL passes**, because sources are never fetched **[verified]**. |
| `validate_claims` | Factual findings have sources; low-confidence findings state uncertainty; draft has ≥3 markers | A model can avoid support requirements by labeling a fact `is_fact: false`. |
| `validate_citations` | Every marker resolves; no duplicate IDs | **15 uncited statistics pass** once three valid markers exist **[verified]**. |
| `validate_structure`, `validate_metadata`, `validate_outline`, `validate_strategy` | Structure, frontmatter, sections, evidence map | Yes (structure) |
| `validate_findings_format` | Review JSON shape | Yes, but this is the *only* gate on review stages. |
| `validate_human_writing` | 11 deterministic prose checks | Runs at the review stage, not the draft stage. A draft opening with "In today's rapidly evolving landscape" **passes the draft gate**. The check then fails the reviewer's submission three times and escalates to a human without the draft ever being revised **[verified]**. Its semantic findings are computed in memory and never persisted or shown to the reviewer. |
| `validate_revision` | Blocking findings resolved; revised draft re-validated | Only collects factcheck and editorial findings. After a human-writing failure, a revision with **zero resolutions and unchanged text passes** **[verified]**. |
| `validate_final` | Re-runs deterministic gates; all verdicts pass; no unresolved blocking findings; budget | Trusts a `resolved: true` flag on the finding. A **critical "fabricated statistic" finding marked resolved by its own reviewer is approved** **[verified]**. Zero-finding "pass" reviews are also approved **[verified]**. |
| Human `approve` | "Humans own the last call" | A CLI command. Nothing distinguishes a human from the agent running it. |

**Empirical evidence of the rubber stamp.** Work item W-20260916-001's history shows brief at 04:11:45, research at 04:13:09 (84 s), draft at 04:14:42, fact-check fail at 04:15:31, revision at 04:16:07 (36 s), fact-check pass at 04:19:56, editorial pass at 04:20:35 (39 s) and final review pass at 04:21:09. That's 9 min 38 s from creation to "final". The editorial review praised the piece ("fit to brief is strong… no hype"). External review then rejected it for reading strongly AI-generated, which prompted the human-writing layer. **Gates that validate the format of a self-review cannot catch what the self-reviewer can't see.**

### 8.3 Lineage C

Checks are instructions to the model: fact-trace every claim to the knowledge doc or a source, run the §10.2 checklist, scan for em/en dashes, list `[CONFIRM]` items. The human reads the docx pack before publishing. There's no automated enforcement, but the human step is real because the human publishes.

---

## 9. Research and evidence architecture

| Concept | A | B | C | Assessment |
|---|---|---|---|---|
| Source tiers (primary/secondary/tertiary) and **excluded** sources (unattributed blogs, forums, marketing materials, competitor sites, AI-generated content, "common knowledge") | Specified; URL-substring classifier implemented | Self-rated `authority: high/medium/low` | "Only use what can be sourced" | **Keep the taxonomy**, with deterministic classification rules and recorded overrides |
| Verbatim excerpt plus location | Specified; extractor returns arbitrary text | Not required | Not required | **Keep and enforce deterministically** against a stored snapshot |
| Claim criticality (critical: safety/legal/financial; core; supporting; background) with minimum evidence per role | Specified | Implicit in the fact-check severity | — | **Keep**; drives evidence requirements |
| Fact vs interpretation | — | `is_fact`, `uncertainty`, `conflicts`, `gaps` | Knowledge doc vs `[CONFIRM]` | **Extend** to a claim-kind taxonomy (architecture §4) |
| Coverage | ≥90% (self-declared) | ≥3 markers | Manual | **Rebuild**: every factual sentence carries a marker (deterministic detection) |
| Confidence | 0–100 weighted formula | high/medium/low self-rated | — | **Rule-derived categorical**, with the reasons shown |
| Conflicts / contradiction | `disputed` state (spec) | `conflicts` field | §11 contradictions | **Keep**: a conflict blocks until resolved or disclosed |
| Drift and evergreen | Specified; checks are placeholders | — | "Re-verify dates with web search" | **Defer**, keeping content hashes so re-verification is possible later |
| Evidence ID scheme | `EVD-<client>-<topic>-<date>-<seq>` | `S#`/`F#` | — | Work-local IDs plus content-addressed snapshots |

**Key gap in all three:** none of them checks that a source actually says what it is claimed to say. B's architecture doc is candid about it: "whether a source says what it is claimed to say is the reviewer's judgment." That judgment was made by the same session that wrote the research.

---

## 10. Human-writing architecture

| Aspect | A | B | C |
|---|---|---|---|
| Stance | "AI detection is irrelevant; optimize for human value" | "Not to game detectors; produce naturally human, expert writing" | "Remove AI tells while preserving facts, SEO and voice" |
| Detection | None | 11 deterministic checks (generic intro/conclusion, not-X-but-Y, triads, filler, hooks, sentence/paragraph CV, template repetition, transitions) plus 8 heuristic semantic categories (profundity, staging, inflation, one-line closers, paragraph-scale, specificity, replaceability, voice fingerprint) | 33 patterns in 5 families (content, language, style, communication, filler), with "what NOT to flag" and a **clusters, not isolated tells** rule |
| Judgment | HQF trust test (value, not prose texture) | Model review with a rich rubric, second-pass "read it aloud" | Two self-questions: "What still makes this obviously AI-generated?" and "Does the rewrite state any fact not in the source?" |
| Context sensitivity | — | None | **Reference vs marketing mode**: 9 patterns switch from "delete" to "make concrete and keep the sell" |
| Voice | Voice profile (spec) | Fingerprint stats for reviewer awareness | **A writing sample outranks the rules**, including the em-dash ban |
| Remediation | — | Targeted revision guidance ("do not synonym-swap; restructure paragraphs") | Full rewrite pass on every draft |
| Calibration | — | One work item plus a fixture that was edited until it passed | Production use on one client |

**Verified weaknesses in B's detector:**
- The calibration draft (externally judged AI) **passes all 11 deterministic checks**. It contains 11 "X is not Y. It is Z" contrasts, and the validator's regex matches **0**, because it only matches "not X, but Y" with a comma.
- The test suite's "clean" fixture contains 5 such contrasts, plus "Governance is a discipline, not a document" and, in the same fixture, "It is not a document. It is a discipline." The standard says it was "updated for paragraph variation", i.e. edited until the validator passed. The validator is calibrated to accept the pattern it should reject.
- The three-part-list regex matches only Title Case lists, missing "speed, cost, and quality".
- The specificity check counts `AWS|Azure|GCP|Kubernetes…` as concrete markers, which couples it to Metanous's domain.
- Filler terms include ordinary words such as "foundation" and "key factor". Transition counting includes "while" and "however". False positives are likely in business prose, and no measurement exists.
- Two implementation reports disagree about the calibration result (0 semantic findings vs HW-PARA-SCALE-1).

**What C gets right that B doesn't:** mode awareness, clusters over single tells, an explicit false-positive list, voice samples as the authority, and the no-new-facts check on rewrites. **What B gets right that C doesn't:** it runs as code, it blocks, and it produces structured findings for targeted revision instead of an unconditional rewrite.

---

## 11. Testing architecture

| Lineage | Tests | Strengths | Gaps |
|---|---|---|---|
| A | **None.** The sprint plan's "definition of done" lists `pytest` suites that were never written | — | Everything; no module survives its own demo |
| B | 71 `unittest` tests, all passing | Fixture builders express "one deviation from a valid artifact"; end-to-end lifecycle over a temp root; a regression test pinning the draft-persistence bug | No adversarial tests (every bypass in §8.2 passes silently); no tests of review substance; HW fixture calibration is circular; no false-positive measurement |
| C | None | — | — |

---

## 12. Important dependencies

| Lineage | Runtime | External services | Constraint that shaped the design |
|---|---|---|---|
| A | Hermes/AionUI agent runtime, Python services, bs4 | Firecrawl, Tavily, OpenRouter **free tier** (ADR-008: Gemini Flash, DeepSeek R1, Nemotron, Qwen) | Weak free models plausibly drove the heavy procedural structure and the belief that more checklists mean more quality |
| B | Python 3.13 stdlib only | None (model-agnostic; an OpenCode session drives the CLI) | "Should still run in five years", which is a good constraint |
| C | Claude account skills, pandoc, python-docx (implicit) | Web search | Chat-driven; one client |

---

## 13. Historical and proven design patterns

Proven means demonstrated by tests, by a real run, or by production use. Specified means designed but never exercised.

| # | Pattern | Evidence | Status |
|---|---|---|---|
| P1 | Artifact-first stages; each handoff is a file | B: 71 tests; W-001 fully reconstructible from disk | **Proven** |
| P2 | Immutable versioned drafts, reviews and revisions; stable single-shot artifacts | B tests `test_versioned_reviews_and_drafts`, `test_stable_names…` | **Proven** |
| P3 | Persist before validate | B `submit()`; tests | **Proven** |
| P4 | Named checks with per-check detail (`ValidationResult`) | B, all validators | **Proven** |
| P5 | Two budgets (attempts vs revisions) ending in human escalation, not infinite loops | B `test_revision_budget_exhausted`, `test_bad_brief_counts_attempts` | **Proven** |
| P6 | Draft-persistence invariant: a passed revision becomes the latest draft before advancing | B: a real bug, fixed, pinned by a regression test | **Proven (learned by failure)** |
| P7 | Aggregate final gate that re-runs everything; no weighted score | B `validate_final`; design note: "a score invites trading an unsupported claim against good prose" | **Proven (shape)**, with holes |
| P8 | Finding schema: id, severity, location, problem, evidence, required correction; critical/major block | B; W-001 FC-1 raised, resolved, re-checked | **Proven once** |
| P9 | Knowledge base as source of truth, re-read each run; stop if missing | B brief prompt; C blog engine | **Proven in use** |
| P10 | `[CONFIRM]` / `pending` instead of fabrication | C production; A v0.1 standards ("mark pending rather than fabricating") | **Proven in use** |
| P11 | Missing inputs / conflicting findings / blocked ≠ complete | A EI agents | Specified |
| P12 | Human chooses among pitched options | C weekly cycle | **Proven in use** |
| P13 | Cross-piece log to prevent topic repetition | C blog log | **Proven in use** |
| P14 | Humanizer with modes, clusters and false-positive list | C production | **Proven in use** (unmeasured) |
| P15 | Deliverable pack (post, SEO block, FAQ, photo brief, repurposing, sources, confirm list) | C | **Proven in use** |
| P16 | Failure pattern taxonomy with IDs, severity, detector and remediation | A standard 15 | Specified (well-structured) |
| P17 | Expertise package (trade-offs, frameworks, mistakes with root cause, warnings, examples, terminology), each item evidence-linked | A standard 11 | Specified |
| P18 | Evidence tiers, excluded source types, claim criticality | A standard 02 | Specified |
| P19 | Voice profile with reasons for each preferred/avoided term; discovery interview | A standard 08; C §6 before/after | Specified (A) / in use (C) |
| P20 | Content-type governance: each type has goal, required knowledge, gate | A standard 16; B `MIN_WORDS_BY_TYPE` | Specified / minimal |
| P21 | Quality gates as code, promoted from warning to blocking after calibration | A ADR-004 | Decided, never built |

---

## 14. Technical debt and failure modes

| # | Debt / failure mode | Lineage | Evidence | Lesson for CraftyProse |
|---|---|---|---|---|
| D1 | Specification far ahead of implementation | A | 14 of 18 standards "Not Yet Implemented"; services crash | Build thin and complete before broad; every standard ships with the code and test that enforce it |
| D2 | Numeric composites as gates | A | Confidence 109/100; CES; voice ≥90 from front matter | Categorical verdicts plus blocking findings; scores are diagnostics only |
| D3 | Self-reported inputs to gates | A, B | `evidence_confidence`, `coverage_status`, `voice_score`, `resolved: true`, writer declarations | A gate may consume only what the engine computed or verified |
| D4 | Author = judge | B | Same session writes and reviews; W-001; rubber-stamp probe | Independent, engine-executed judges |
| D5 | Validators that force a template | A | GCV-001–007, 014, E-E-A-T markers | Content-type anatomy states purpose; evidence decides which expertise elements appear |
| D6 | Validators that reward fabrication | A | "≥3 first-person experience markers", "≥2 original research markers", named-technician patterns | Specifics must come from EIS or evidence; the engine checks new specifics against both |
| D7 | Internal contradiction | A | Constitution §3.3 vs GCV-009 | Internal claim markers in drafts, stripped or converted at release |
| D8 | Reviewer proliferation and quotas | A | 11 + 5 seats, unanimity, 70% target rejection rate | 3 judges with disjoint jurisdictions; rejection rate is an outcome, never a target |
| D9 | Proportionality failure | A | 10 components and confidence ≥95 for every artifact, including a GBP post | Evidence rules by content type and claim criticality |
| D10 | Checks at the wrong stage | B | HW gate on the review stage | A check runs where its defect can be fixed |
| D11 | Partial resolution accounting | B | Revision ignores HW/final findings | Every open blocking finding from every source must be resolved, and the engine verifies resolution |
| D12 | Unverifiable sources | A, B | Placeholders; URL-prefix check | Fetch, snapshot, hash, verify excerpts |
| D13 | Claim coverage by count | B | 15 uncited stats pass | Sentence-level factual-claim detection |
| D14 | Documented-but-absent behavior | B | `validations/` not written on submit; README says it is | Tests assert documented behavior |
| D15 | Lexicographic version sort | B | Documented limitation | Numeric sort |
| D16 | Circular calibration | B | Fixture edited until it passed | Separate calibration corpora (human vs AI), with measured false-positive and detection rates |
| D17 | Hard-coded domain and client terms | A, B | `clicksavvy.com`, Phoenix/Dubai/Arcadia/JVC, HVAC terms, `AWS\|Azure` specificity markers | No brand, region or vertical in the core; all of it lives in EIS |
| D18 | Duplicate IDs | A | GCV-016/023/029/037; FP-0503/0703/1003 twice | IDs unique by test |
| D19 | Practice diverging from principle | A | Content-sprint velocity, keyword-driven brief | Principles live in the path of work as enforced gates |
| D20 | Honor-system human approval | B | Agent can run `approve` | Record the approver; separate "ready_for_release" from "released"; state the limitation plainly |

---

## 15. Predecessor-specific components (strip)

- **Identity and branding:** Click Savvy, Hermes/AionUI, Metanous, Harmony Homes, "agency", `clicksavvy.com`, `harmonyhomes.ae`, the Editorial Oath, "Constitution" framing.
- **Clients and examples:** Acme Plumbing and every Phoenix/Arizona example (ROC licenses, APS/SRP, water hardness, Arcadia), every Dubai example (DEWA, Ejari, JVC, Harmony services), Metanous's AI-agent article content, HVAC/plumbing terminology lists, named people ("Maria Santos").
- **Agency operating model:** departments, team leads, kanban, SLAs in business hours, reviewer qualification registries, retention periods, quarterly audits, Architecture Review Board, sales/finance/legal agents, ROI per article.
- **Environment workarounds:** the free-tier model strategy, OpenCode command wrappers, the Obsidian vault layout, `.hermes` state, email ingest.
- **Harmony hard rules:** no pricing, no hotel brand names, no religious framing, specific unlaunched brand names. These are client guardrails; the *mechanism* (guardrails in EIS, compiled to checks) is generic.

---

## 16. Reusable components

**Near-verbatim reuse is justified only for small, proven, generic utilities** (rewritten in CraftyProse style, with tests):
- B `models.ValidationResult` (named-check aggregate)
- B `artifacts._atomic_write` (write-temp-then-rename)
- B frontmatter, heading and word-count helpers
- B versioned-artifact persistence (with numeric sort)
- B budget and escalation logic in the orchestrator

**Everything else is reused as knowledge**, meaning concepts, taxonomies and rubrics rebuilt in CraftyProse's own words. See the matrix below.

---

## 17. Reuse / Adapt / Rebuild / Discard matrix

Decisions: **REUSE** (carry with minimal change) · **ADAPT** (useful; modify) · **REBUILD** (methodology valuable; implement cleanly) · **DISCARD** (unnecessary, broken, coupled or redundant) · **DEFER** (valid concept; not needed for a first complete engine).

### Orchestration and artifacts

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| B orchestrator state machine | Deterministic stage progression | 71 tests; W-001 | Yes | **REBUILD** | Shape proven; stage set, statuses (`needs_input`, `blocked`, `ready_for_release`) and judge execution change |
| B artifact store (atomic, versioned, persist-before-validate) | Crash safety, full history | Tests | Yes | **REUSE** | Small, correct; fix numeric sort |
| B `ValidationResult` | Explainable gate results | Every validator | Yes | **REUSE** | Exactly right |
| B attempts / revisions budgets | Bounded loops | Tests | Yes | **REUSE** | Proven |
| B draft-persistence invariant | Reviews examine the revised text | Real bug + regression test | Yes | **REUSE** | Keep the test |
| B aggregate final gate | No skipped or trusted checks | Tests; bypasses found | Yes | **ADAPT** | Add draft-hash binding, computed resolution, all judges |
| B `validations/` records | "It passed" is backed by a record | Not actually written on submit | Yes | **ADAPT** | Record every gate run |
| B human `approve` | Human owns release | Honor system | Yes | **ADAPT** | Approver identity, release policy per content type |
| A `ExecutionEngine` | Enforce gates | Deadlocks | Partly | **DISCARD** | Broken; nothing salvageable beyond "hard gates can't be overridden" |
| A 13 gates / 3 content paths | Gate sequencing by risk | Never ran | Partly | **DISCARD** | Replaced by per-type specs plus claim criticality |
| A immutable audit log | Traceability | JSONL append works | Yes | **ADAPT** | Event log per work item |

### EIS: context and knowledge

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| A Constitution objective hierarchy + non-negotiables | Priority when goals conflict | Principle only | Yes | **ADAPT** | Becomes CraftyProse editorial principles; drop the ceremony |
| A Knowledge Package (10 components, ≥95) | Writer never guesses | Never produced | Partly | **REBUILD** | Keep the idea; make components proportional to content type |
| A Expertise Package structure | Genuine expertise signals | Spec | Yes | **ADAPT** | Optional, evidence-backed elements; never mandated counts |
| A Editorial Objective | Singular purpose, reader outcome, must/must-not include | Spec | Yes | **ADAPT** | Part of the brief |
| A Knowledge Gaps (blocking flags) | Explicit unknowns | Spec; B `gaps`; C open questions | Yes | **REUSE** (concept) | Validated by three lineages |
| A confidence formula (standard 13) | Computed confidence | Produces 109 | No | **DISCARD** | Replaced by rule-derived categorical confidence |
| A `KPService`, `EvidenceService` code | Persistence of KP / evidence | Crash | — | **DISCARD** | Broken |
| A Knowledge Graph (04), Asset Library (12) | Cross-client reuse | Never built | Partly | **DEFER** | Content-addressed snapshots give most of the reuse value |
| A Learning System (07) | Improve over time | Never built | Yes | **REBUILD (minimal)** | A learning log of finding pattern IDs with an aggregate report |
| A Evergreen Monitoring (09) | Drift after publication | Placeholders | Yes | **DEFER** | Keep hashes so a re-verify command is possible later |
| C knowledge doc schema | Brand source of truth | Production | Yes (schema) | **ADAPT** | Becomes the EIS brand workspace |
| C approved proof points | Which first-party claims may be made | Production | Yes | **ADAPT** | Approved-claims registry |
| C open questions and contradictions | Block topics that depend on unresolved facts | Production | Yes | **ADAPT** | Brand-level gaps |
| C blog log / topic bank | Avoid repetition | Production | Yes | **ADAPT** | Content log |
| A Business Opportunity MVP | Content tied to business value | Spec | Partly | **ADAPT** | Folded into brief `business_goal`; not a separate artifact |

### Evidence and claims

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| A evidence tiers + excluded sources + criticality minimums | Source quality | Spec | Yes | **ADAPT** | Deterministic classification rules plus recorded judge overrides |
| A evidence ID scheme | Traceability | Spec | Partly | **REBUILD** | Work-local IDs + content hashes; no client slugs |
| B `research.json` schema (`is_fact`, `uncertainty`, `conflicts`, `gaps`) | Separate fact from interpretation | Used in W-001 | Yes | **ADAPT** | Extended into a claim-kind taxonomy |
| B `[S#]/[F#]` markers resolve | No dangling citations | Tests | Yes | **ADAPT** | Claim markers `{C#}` plus sentence-level coverage |
| Verbatim excerpt verification | Source says what we claim | Nowhere implemented | Yes | **REBUILD (new)** | Fetch, snapshot, hash, substring-verify |
| A drift monitoring | Stale evidence | Placeholders | Yes | **DEFER** | Not needed for first release |

### Voice

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| A Voice Profile structure | No generic voice | Spec; C in use | Yes | **ADAPT** | Keep lexicon-with-reasons, audience address, formatting; drop 1–10 tone scores |
| A voice interview guide | Voice discovered, not invented | Spec | Mostly | **ADAPT** | Generic brand-intake questionnaire |
| A voice compliance scorer (≥90) | Measure voice | Never built; reads front matter | No | **DISCARD** | Unmeasurable as specified; judge compares against samples instead |
| C before/after pairs, writing samples | Calibrate voice | Production | Yes | **REUSE** (concept) | Samples outrank rules |
| C em-dash ban | Common AI tell | Production (one client) | Partly | **ADAPT** | A voice-profile punctuation policy, not universal |

### Review, quality and revision

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| A 11-reviewer board + 5 HQF evaluators, unanimity, 70% target | Rigor | Never ran | Partly | **REBUILD** | 3 independent judges with disjoint jurisdictions |
| A Human Trust Test (5 questions) | Value-centric quality | Spec | Yes | **ADAPT** | Editorial judge rubric; Q5 becomes "specific to this brand and audience" |
| A Failure Pattern Library | Shared defect vocabulary | Spec | Mostly | **REBUILD** | Generic examples, unique IDs, fabrication-inducing patterns removed, detector per pattern |
| B finding schema + severity semantics | Actionable findings | W-001 | Yes | **REUSE + extend** | Add `pattern_id`, `quote`, `fingerprint` |
| B review stage prompts | Review criteria | W-001 (rubber-stamped) | Yes | **ADAPT** | Rubric content kept; executed independently |
| B revision stage + resolution list | Targeted fixes | Tests; bypass found | Yes | **ADAPT** | Resolution verified by re-review and diff |
| A GCV structural/technical validators (headings, meta, alt text, https, canonical) | Mechanical correctness | Not runnable | Yes | **REBUILD (subset)** | Ranges instead of exact counts; only where the content type needs them |
| A GCV content validators (trade-offs, framework, mistakes, warnings, tips, experience markers, CTA positions, regional markers) | Force expertise | Not runnable; template-forcing | No | **DISCARD** | They manufacture formula and fabricated experience |
| A CES composite | One publish score | Spec | No | **DISCARD** | Scores trade defects against polish |
| A Writer Declaration | Prevent hallucination | Self-attestation | No | **DISCARD** | Replaced by deterministic verification |
| A QA checklist (3/5) | Delivery gate | In use | No | **DISCARD** | Mediocre passes by design |
| A Legal & Compliance standard (YMYL tiers, disclaimers, affiliation disclosure, license claims) | Legal risk | Spec | Mostly | **ADAPT** | Claim criticality rules + brand guardrails + required disclosures |

### Human writing

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| B deterministic HW checks | Catch mechanical AI patterns | Passes known-AI text | Mostly | **ADAPT** | Repair patterns, run at draft stage, persist findings, calibrate |
| B HW review rubric (specificity, replaceability, profundity, staging, paragraph-scale) | Judgment-level AI feel | Correct content; self-applied | Yes | **ADAPT** | Writing-judge rubric |
| B HW revision guidance | Natural rewrite, not synonym swap | Spec | Yes | **ADAPT** | Revision instructions |
| C 33-pattern humanizer catalog, modes, clusters rule, false-positive list | Remove AI tells without losing sell | Production | Mostly | **ADAPT** | Rewritten in our words (derived from Wikipedia "Signs of AI writing", CC BY-SA; see architecture §21) |
| C "no new facts" self-question | Humanizing must not fabricate | Production | Yes | **REBUILD** | Deterministic diff: new numbers/entities vs ledger and EIS |
| C unconditional humanizer rewrite of every draft | Polish | Production | Partly | **DISCARD** (as default) | Targeted revision only; avoid fact drift and homogenization |

### Workflow, content types and discoverability

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| A Content Artifact Governance matrix | Many types, one intelligence | Spec | Yes | **ADAPT** | Content-type specification files |
| C post anatomy + "formats that work for search and AI answers" | Structure that ranks and reads | Production | Mostly | **ADAPT** | Blog/article type spec |
| C pitch-3-options mode | Human picks the topic | Production | Yes | **ADAPT** | Optional `pitch` command before intake |
| C deliverable pack | Everything publishing needs | Production | Yes | **ADAPT** | Release package |
| A content-sprint workflow | Velocity | In use | No | **DISCARD** | Contradicts principles |
| A SEO/AEO agents (7 AEO, 6 keyword) | Discoverability | Prompts | Partly | **DISCARD as agents** | Knowledge folded into deterministic discoverability rules plus an editorial rubric section |
| A structured-data expectations per page type | Schema completeness | Spec | Yes | **ADAPT** | JSON-LD generated deterministically at release |

### Agents, prompts, tests and infrastructure

| Component | Problem solved | Evidence it worked | Generic? | Decision | Reason |
|---|---|---|---|---|---|
| A 124 agent prompts | Run an agency | Some usage | No | **DISCARD** | Content knowledge mined into this report |
| A EI failure-handling contract | No fabrication on missing or conflicting input | Spec | Yes | **REUSE** (concept) | Every role inherits it |
| B stage prompts | Model instructions | W-001 | Mostly | **ADAPT** | Rewritten; context slices; brand-agnostic |
| B test harness and fixture pattern | Precise tests | 71 tests | Yes | **REUSE** (pattern) | Plus adversarial suite and calibration corpora |
| A skills YAML, scheduler, kanban, email ingest, dashboard, Obsidian vault, backups, Hermes config | Agency tooling | Various | No | **DISCARD** | Out of scope |
| A ADR-008 free-tier model strategy | Cost | — | No | **DISCARD** | Model choice becomes per-role configuration |

---

## 18. Methodology extraction (Phase 2)

These are the methods that made the predecessor effective, or that its failures proved necessary. Each is phrased as a rule CraftyProse enforces.

| # | Methodology | Source | Rule in CraftyProse |
|---|---|---|---|
| M1 | **Knowledge before writing** | A §2, B stages, C knowledge doc | The writer receives a knowledge package and may state only claims in the ledger or EIS. The writer does not research. |
| M2 | **Claims are objects with provenance** | A 02, B findings | Every factual sentence carries a claim marker. Every claim has a kind, a criticality and evidence appropriate to both. |
| M3 | **Unknowns are explicit** | A gaps, B uncertainty, C `[CONFIRM]` | Gaps and conflicts are artifacts. A blocking gap stops the work, and an unverifiable claim can't be released. |
| M4 | **Gates are code; findings are judgment; no score compensates** | B final gate, A ADR-004 | Deterministic validators pass or fail. Judges emit findings. Any open critical or major finding blocks release. |
| M5 | **Evaluate independently** | B's failure | Judges run as separate, engine-executed calls with only the artifacts they need. The author's context never reaches them. |
| M6 | **Verify rather than trust** | A's and B's failures | Gates consume only engine-computed facts: excerpt found in snapshot, marker coverage, draft hash, resolution by re-review. |
| M7 | **Defect-driven revision with accounting** | B revision, A failure patterns | Revision addresses listed findings. The engine tracks each finding as resolved, persistent or new, and persistent defects escalate. |
| M8 | **Artifact-first, immutable history** | B | Every stage writes a versioned artifact, and every gate run and decision is recorded. |
| M9 | **Bounded loops, human escalation** | B | Attempts and revisions are budgeted; exhaustion yields `requires_human_review` or `rejected`, never an infinite loop. |
| M10 | **Voice is discovered and evidenced** | A 08, C §6 | Voice comes from brand samples, lexicon with reasons and before/after pairs. Samples outrank generic style rules. |
| M11 | **Human writing = clusters + specificity + voice** | B standard, C humanizer | Deterministic cluster detection, calibrated on corpora, plus a writing-judge rubric. No detector scores. |
| M12 | **Content types are specifications** | A 16, C anatomy | Each type declares goal, anatomy, length, evidence profile, discoverability profile, applicable judges and release format. |
| M13 | **SEO/AEO is a constrained overlay** | A §1.2, A 01 Phase 8 | Discoverability rules enforce presence and ceilings (anti-stuffing), never repetition quotas, and may not remove evidence, voice or substance. |
| M14 | **Guardrails are rules, not reminders** | C hard rules, A 11 Legal | Brand guardrails compile to deterministic checks (forbidden terms, banned topics, required disclosures). |
| M15 | **Human judgment where it matters** | C topic choice, B approval | Humans choose topics (optional) and approve release (default). They are not required inside every loop. |
| M16 | **Shared failure vocabulary** | A 15 | Every finding cites a pattern ID. Validators, judges, revision and learning use the same IDs. |
| M17 | **Standards live in the path of work** | A's practice-principle gap | No standard exists without the validator, judge rubric or test that enforces it. |

---

## Appendix A: Evidence index

| File | What it demonstrates |
|---|---|
| `evidence/probe_clicksavvy_infrastructure.py` + `.out.txt` | GCV can't be constructed; trade-off validator broken; claim extractor over-matches; evidence ingest crashes; excerpt fallback returns unrelated text; KP can't round-trip; fake evidence scores 109 "authorized" (weights sum to 1.10); execution engine deadlocks; declarations can't reload and examine nothing |
| `evidence/probe_metanous_human_writing.py` + `.out.txt` | Known-AI draft passes the deterministic gate; 11 contrasts missed; "clean" fixture contains the pattern; uncited statistics pass; fabricated URL passes |
| `evidence/probe_metanous_gate_bypasses.py` + `.out.txt` | HW defect at the wrong stage escalates without revision; zero-resolution revision passes; self-resolved critical finding approved; rubber-stamp reviews approved |
| `evidence/metanous_test_suite.out.txt` | B's 71 tests pass |

## Appendix B: Size reference

| Item | Size |
|---|---|
| A EIS standards (18 files) | 7,343 lines; plus 7 draft standards, 221 lines |
| A infrastructure Python | 4,136 lines, 0 tests |
| A agent prompt files | 128 (124 agents) |
| B engine | 3,425 lines; tests 1,177 lines (71 tests) |
| C skills | 2 SKILL.md files; knowledge doc 13 sections + appendix |
