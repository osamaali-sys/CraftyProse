# CraftyProse Architecture Proposal

**Phase:** 3 (architecture) and 4 (architectural review)
**Date:** 2026-09-24
**Status:** **Approved 2026-09-25**, with the decisions recorded in §22.1. Amendments from that approval are marked *[approved amendment]* in the sections they affect.
**Inputs:** `docs/extraction/01-extraction-report.md` (cited as *ER §n*). Decision records: `03-decision-records.md` (cited as *ADR-n*).

---

## 1. Design principles

Each principle exists because the predecessor failed without it (ER §14).

| # | Principle | Failure it prevents |
|---|---|---|
| 1 | **Knowledge before writing.** The writer states only claims from the ledger or EIS. | Hallucinated facts that "sound right" |
| 2 | **Verify, don't trust.** Gates consume only what the engine computed or checked. | A's 109/100 confidence; B's self-resolved findings |
| 3 | **The author is never the judge.** Reviews are separate, engine-executed calls. | B's rubber-stamped reviews |
| 4 | **Binary gates and blocking findings. No compensating scores.** | A defect traded against polish |
| 5 | **Proportional rigor.** Content type × claim criticality sets the evidence bar. | A's one-size 10-component package |
| 6 | **A check runs where its defect can be fixed.** | B's human-writing check at the review stage |
| 7 | **Artifact-first and reproducible from disk.** | Lost state, unexplainable releases |
| 8 | **Minimum necessary complexity.** Every component names the failure mode it prevents; anything that can't is cut. | 124 agents, 16 reviewer seats, 13 gates |
| 9 | **Humans decide topic (optional) and release (default).** | Unreviewed publication |

---

## 2. System overview

```text
                 ┌─────────────────────────── EIS ───────────────────────────┐
                 │  Context        Evidence         Permission    Standards  │
                 │  brand, voice,  snapshots,       approved      failure    │
                 │  audiences,     evidence items,  claims,       patterns,  │
                 │  offerings      claims ledger    guardrails,   writing    │
                 │                                  open qs       patterns,  │
                 │  Memory: content log, learning log             sources    │
                 └──────────▲──────────────▲───────────────▲──────────▲──────┘
                            │ declared context slices (least context)  │ records
 request ──► ORCHESTRATOR  (state machine · budgets · gate runner · event log)
                            │
   INTAKE ─► RESEARCH ─► PLAN ─► DRAFT ─► REVIEW ─► RELEASE ─► (human) RELEASED
      ▲          ▲          ▲              │  ▲
      │          └── research more ────────┤  │
   needs_input                             ▼  │
                                         REVISE ┘ (bounded)
                            │
        role executors (LLM)   deterministic validators   independent judges (LLM)
                            │           ▲
                     content-type specification (goal, anatomy, evidence,
                     discoverability, judges, release format)
```

**Responsibilities:**
- **Orchestrator:** owns state, sequencing, budgets and gate execution. It never writes content.
- **EIS:** owns truth, permission, voice and standards. It never moves work.
- **Roles:** propose artifacts. They never pass their own gates.
- **Validators:** deterministic pass/fail.
- **Judges:** findings.
- **Content-type specs:** parameterize all of the above without conditionals in the core.

---

## 3. EIS: the Editorial Intelligence System

### 3.1 Definition and authority

EIS is the governed context and judgment layer. It is the **only** channel through which facts, permissions, voice and quality criteria enter the pipeline, and it records every judgment made against them.

| EIS domain | Question it answers | Contents | Enforced by |
|---|---|---|---|
| **Context** | Who are we, who are we speaking to, how do we sound? | Brand profile, offerings and linkable pages, audiences, voice profile, samples, before/after pairs | Context slices; writing judge |
| **Evidence** | What is true about the world? | Source snapshots (content-addressed), evidence items (verbatim excerpts), claims ledger | Research and draft validators; evidence judge |
| **Permission** | What may we say? | Approved first-party claims, forbidden claims, guardrails, open questions and contradictions | Guardrail validators; claim rules; intake checks |
| **Standards** | What is good, and what is a defect? | Editorial principles, failure-pattern library, writing-pattern catalog, source-authority rules, judge rubrics | Validators; judges; revision instructions |
| **Memory** | What have we said, and what keeps going wrong? | Content log (released pieces), learning log (findings by pattern) | Intake repetition check; learning report |

**Outside EIS (deliberately):** workflow state, budgets, LLM runtime, rendering. EIS is knowledge and rules. Mixing orchestration into it is how A ended up with "EIS gates" enforced by nothing.

### 3.2 Brand workspace (EIS context and permission)

The knowledge-doc schema from lineage C, the only EIS form proven in production, is made machine-readable. TOML is read with stdlib `tomllib` (ADR-011).

```text
workspace/brands/<brand_id>/
  brand.toml          identity, positioning, markets/locale, offerings[], linkable_pages[] (url, title, topics)
  audiences.toml      personas: who, problems, questions, objections, vocabulary, sophistication
  voice.toml          speaker (company "we" | named author), register, personality, rules[],
                      lexicon.prefer[{term, instead_of, reason}], lexicon.avoid[{term, reason, alternative}],
                      punctuation policy (e.g. em_dash = "avoid" | "allow" | "match_samples"), spelling locale,
                      formatting preferences
  voice/samples/*.md  approved human-written samples (these outrank generic style rules)
  voice/pairs/*.md    before/after rewrites that show the voice
  claims.toml         approved first-party claims: id, statement, kind, source/approver, approved_on,
                      expires_on, allowed phrasings; forbidden claims with reasons
  guardrails.toml     rules: forbidden_term | forbidden_pattern | banned_topic | required_disclosure |
                      speaker_policy; applies_to (content types); severity; message
  open_questions.toml unresolved facts/contradictions; blocks_topics[]
  content_log.jsonl   released pieces: date, work_id, type, title, primary question, topics, url
```

A `brand init` command scaffolds these files with guided comments, adapting A's voice-discovery interview (ER §17 Voice). A brand with no voice samples still works, but the release record flags that voice was judged against rules only.

### 3.3 Standards (shipped with the engine)

```text
craftyprose/eis/standards/
  principles.md             objective hierarchy: truth > usefulness > expertise > specificity > trust > discoverability
  failure_patterns.toml     id, category, name, definition, default_severity, detector (deterministic|judge:<name>),
                            remediation, good/bad example (generic, fictional)
  writing_patterns.toml     human-writing catalog (§10): id, family, detector, weight, mode overrides,
                            false-positive notes, remediation
  source_rules.toml         authority classes and domain/type rules; excluded categories
```

Pattern categories give each judge a disjoint jurisdiction:

| Category | Prefix | Detector |
|---|---|---|
| Evidence and claims | `EV-` | Deterministic + evidence judge |
| Editorial value | `ED-` | Editorial judge |
| Discoverability | `DS-` | Deterministic + editorial judge |
| Human writing | `HW-` | Deterministic + writing judge |
| Voice | `VO-` | Deterministic lexicon + writing judge |
| Structure and format | `ST-` | Deterministic |
| Risk and compliance | `RK-` | Deterministic guardrails + evidence judge |

A's 52 patterns are rewritten generically (ER §17 Review). Duplicate IDs are removed, and any pattern that rewards invented specifics (named technicians, first-person experience quotas, "original research markers") is removed. A unit test enforces unique IDs and valid detector references.

### 3.4 Context slices

Every stage and judge declares the EIS slice it receives. The slice is assembled by the engine, hashed and recorded, so a run is reproducible and the stable part is cacheable (§14). Least context is also what makes judges independent: the writing judge never sees the ledger, and the evidence judge never sees the voice samples.

---

## 4. Claim and evidence model

### 4.1 Claim kinds and rules

| Kind | Example | Evidence rule | Release rule |
|---|---|---|---|
| `statistic` | "41% of buyers…" | ≥1 verified evidence item whose excerpt contains the number | Numbers in the sentence must match the claim or excerpt (§7, D8) |
| `third_party_fact` | "The regulation took effect in 2025" | ≥1 verified evidence item | — |
| `first_party_fact` | "We operate in three cities" | Must reference a non-expired approved claim in `claims.toml` | Otherwise `confirm`: cannot release |
| `marketing_claim` | "Setup takes one afternoon" | Must be an approved claim | Otherwise `confirm` |
| `testimonial` | A customer quote | Approved claim with attribution | Verbatim only |
| `inference` | "So budgets will tighten" | Premises (claim IDs) must be verified | Must read as reasoning, not fact (evidence judge) |
| `interpretation` / `opinion` | The brand's stance | None; attributed to the speaker | Must not be phrased as external fact (evidence judge) |

**Criticality:**
- `critical` means health, legal, financial or safety (YMYL). It requires ≥2 evidence items from ≥2 independent publishers, at least one primary, and fires the relevant `required_disclosure` guardrails.
- `core` means central to the argument.
- `supporting` means context.

**Confidence** is derived by rule, not scored (ADR-004):

| Level | Rule |
|---|---|
| **high** | Verified excerpt, from a primary source or from ≥2 independent secondary sources, and within the recency limit |
| **medium** | A single secondary source, or a primary source beyond the recency limit |
| **low** | Tertiary sources only. Not allowed for `critical`. For `core`, the evidence judge must see hedged phrasing |

The reasons are stored with the claim.

### 4.2 Provenance chain

```text
claim {id, text, kind, criticality, status, confidence, confidence_reasons, scope{jurisdiction, as_of, population}, phrasing_constraints}
  └─ evidence {id, source_id, excerpt (verbatim), locator, relation: supports | contradicts | qualifies}
       └─ source {id, snapshot_sha256, url, title, publisher, published_date, retrieved_at,
                  authority_class: primary | secondary | tertiary | excluded,
                  classification_basis: rule id | judge override + reason, independence_group}
            └─ snapshot  workspace/evidence/snapshots/<sha256>.txt  (+ .meta.json)
  └─ usage: draft sentences carrying {C#}  (computed)
```

**Snapshots are fetched by the engine, never typed by a model.** Either the engine fetches the URL itself or it lifts the content from the web-fetch tool result block the API returns, not from model text. User-supplied documents (reports, interview notes) become snapshots with a declared authority class. This single decision closes the fabricated-source and fabricated-quote holes in both predecessors (ER §9).

### 4.3 Research gate (deterministic)

| Rule | Check | On failure |
|---|---|---|
| R1 | Each excerpt (after whitespace, quote and case normalization) is a substring of its snapshot | Evidence item rejected (`EV-EXCERPT-NOT-FOUND`) |
| R2 | No `excluded` source supports a third-party claim | Rejected |
| R3 | Evidence counts and independence meet kind × criticality rules | Claim `unsupported` |
| R4 | First-party and marketing claims resolve to approved, unexpired EIS claims | Claim `confirm` |
| R5 | Inference premises exist and are verified | Claim `unsupported` |
| R6 | `contradicts` evidence marks the claim `conflicted` | Plan must disclose or exclude it |
| R7 | Source age within content-type limits | Confidence downgrade |
| R8 | Every brief `required_claim` is covered or declared a gap | Research attempt, then `blocked` |

The evidence judge then runs in **ledger mode**: does each excerpt support its claim in scope, magnitude and direction? This catches misread sources before any drafting cost.

---

## 5. Lifecycle and state machine

### 5.1 Stages

| # | Stage | Role | Artifact | Deterministic gate | Judgment |
|---|---|---|---|---|---|
| 1 | **Intake** | Intake planner | `brief.json` (+ `questions` if insufficient) | Required fields per type; audience resolves to EIS or is described; objective and reader outcome present; not a banned topic; not blocked by an open question; repetition check against the content log | — |
| 2 | **Research** | Researcher (+ engine fetch) | `sources.json`, `evidence.json`, `claims.json`, `gaps.json` | R1–R8 (§4.3) | Evidence judge, ledger mode |
| 3 | **Plan** | Strategist | `plan.json`: objective, angle, differentiation, information hierarchy, arguments→claims, sections→arguments, allowed claims, gaps/conflicts handling, discoverability targets | Every section maps to arguments (or is an anatomy element); every argument cites allowed claims; no open blocking gap; every conflict handled; anatomy satisfiable | — |
| 4 | **Draft** | Writer | `drafts/draft-vN.md` with `{C#}` markers | Structure, claim coverage, number consistency, guardrails, voice lexicon, hard writing tells, discoverability, length (§7) | — |
| 5 | **Review** | 3 independent judges | `reviews/round-N/*.json` + `deterministic.json` | Judge-output validation (§8.3) | Findings |
| 6 | **Revise** | Writer (revision mode) | `revisions/revision-vN.json` → `draft-vN+1` | Resolution accounting, change verification, no new facts, all draft checks (§9) | Back to review |
| 7 | **Release** | — | `release/` package + `release_record.json` | Final gate (§11) | Human approval |

This is 7 stages where B had 10 and A had 14 phases and 13 gates. Brief and editorial objective are merged; strategy and outline become the plan; the review panel replaces the separate fact-check, editorial, human-writing and final-review stages (ADR-006).

### 5.2 Statuses

```text
in_progress(stage) ─┬─► needs_input          intake insufficient or conflicting; questions listed; resumes on `answer`
                    ├─► blocked              evidence rules can't be met; options listed (add sources, narrow claims, reject)
                    ├─► requires_human_review budgets exhausted without a critical defect
                    ├─► rejected             human rejection, or a critical defect persists after the revision budget
                    └─► ready_for_release ──► released (human `approve --by <name>`)
```

### 5.3 Gate outcomes

| Condition | Outcome |
|---|---|
| Brief lacks audience, objective or reader outcome; request ambiguous | **STOP** → `needs_input` (return to intake) |
| Topic banned by guardrails or blocked by an open question | **STOP** → `needs_input` with the rule cited |
| Required claim has no verifiable evidence | **RESEARCH MORE** (attempt budget), then `blocked` |
| Evidence contradicts evidence | **INVESTIGATE**: the plan must disclose or exclude; otherwise `blocked` |
| Excerpt not in snapshot, or excluded source | **BLOCK** that evidence item |
| Factual sentence without a marker, or a number that doesn't match its evidence | **BLOCK** → revise |
| Major editorial, human-writing or voice finding | **REVISE** |
| A finding needs evidence the ledger lacks | **RESEARCH MORE** (targeted), then plan update, then revise |
| Same defect persists across 2 revisions, or budget exhausted | **REJECT** (critical persists) / `requires_human_review` |
| Final gate fails | **DO NOT RELEASE** |

### 5.4 Budgets

These are inherited from B (ER §13 P5):
- **Attempts per stage: 3.** Counts gate failures of a submission.
- **Revision rounds: 3.** Counts review→revise loops, including research-more loops.
- **Judge re-runs for invalid output: 2 per round.**

All are configurable per content type.

---

## 6. Roles (the LLM agents)

Seven roles. Each has a single mission and a declared context slice. **No role passes its own gate. No role judges its own output.**

| Role | Mission | Receives | Produces | Authority | Tools | Fails when |
|---|---|---|---|---|---|---|
| **Intake planner** | Turn a request into an actionable brief, or ask the right questions | Request, brand summary, audiences, guardrails, open questions, content log, content-type spec | `brief.json`, `questions[]` | Proposes; engine decides sufficiency | — | Missing audience or objective → `needs_input` |
| **Researcher** | Find sources and extract verbatim evidence for the brief's claims | Brief, required claims, source rules, existing snapshots | Source URLs/documents, excerpts, proposed claims, gaps, conflicts | Proposes; engine fetches and verifies | Web search; web fetch | Excerpts not found; coverage unmet |
| **Strategist** | Decide what the piece says and in what order | Brief, verified ledger, audience, voice summary, type anatomy, content log | `plan.json` | Proposes; plan gate | — | Unmapped arguments; unhandled gaps |
| **Writer** | Write the draft; revise against findings | Plan, allowed claims (text + phrasing constraints), voice profile + samples, type spec; in revision mode, open findings with remediation | Draft; revision + resolutions | Proposes | — | Invalid markers; new facts; unchanged "fixes" |
| **Evidence judge** | Does every factual statement say only what its evidence supports? | Draft with markers, ledger (claims, excerpts, source metadata), deterministic claim warnings | Findings `EV-*`, `RK-*` | Blocking findings | — | Invalid quotes; incomplete rubric |
| **Editorial judge** | Is this worth reading for this audience and purpose? | Draft (markers stripped), brief, plan objective and angle, audience, type spec, brand summary, content-log titles | Findings `ED-*`, `DS-*` | Blocking findings | — | Same |
| **Writing judge** | Does it read like a specific human in this brand's voice? | Draft (markers stripped), voice profile + samples + pairs, deterministic writing report | Findings `HW-*`, `VO-*` | Blocking findings | — | Same |

Every role inherits the missing/conflicting-input contract from A's EI agents (ER §5):
- Missing input → say so; never fabricate.
- Conflicting input → surface both; never choose silently.
- Blocked → `blocked`, never "complete".

**Why not more roles:**
- SEO/AEO is deterministic rules plus one editorial rubric section.
- Fact-checking is the evidence judge.
- "Humanization" is the writing judge plus targeted revision.
- Legal is claim criticality plus guardrails plus the evidence judge's `RK-*` jurisdiction.
- A final reviewer is the final gate, which is code.

**Why not fewer:** merging any two judges puts two jurisdictions in one context. That recreates the author-and-judge problem at a smaller scale, and it makes findings harder to route to the right remediation.

---

## 7. Deterministic validators vs intelligent evaluation

The rule (ADR-002): **if code can check it reliably, code checks it, and the judge is told the result instead of being asked.**

### 7.1 Deterministic (blocking unless marked advisory)

| ID | Check | Stage |
|---|---|---|
| S1 | Artifact schema, required fields, IDs unique, references resolve | All |
| S2 | Heading hierarchy, required anatomy elements, section count, length range (words or characters per type) | Draft, revise |
| D1 | Every `{C#}` resolves to a claim in `plan.allowed_claims` | Draft, revise |
| D2 | **Factual-sentence coverage.** Strong signals (%, currency, "study/survey/report/according to", superlatives such as best/leading/only/#1/fastest) require a marker. Weak signals (bare numbers, comparatives) produce advisories the evidence judge must address | Draft, revise |
| D3 | No marker points at a `confirm`/`conflicted`/`unsupported` claim unless the plan's handling allows it | Draft, revise |
| **D8** | **Number consistency.** Every numeric token in a marked sentence appears, normalized, in the referenced claim or its excerpts. Numbers in unmarked sentences fall under D2 | Draft, revise |
| G1 | Guardrails: forbidden terms/patterns, banned topics, speaker policy (e.g. no personal names), required disclosures present when a trigger fires | Intake, draft, revise, release |
| V1 | Voice lexicon: avoided terms absent; punctuation policy (e.g. em dash) | Draft, revise |
| H1 | Hard writing tells (chat residue, knowledge-cutoff disclaimers, placeholder text, generic AI opener or closer) | Draft, revise |
| H2 | Writing-pattern clusters and densities (§10): **advisory**, escalating to blocking above the calibrated "egregious" threshold | Draft, revise |
| DS1 | Discoverability per type: title/meta length ranges; primary question in title or H1 and intro; FAQ headings phrased as questions; keyword density **ceiling**; internal links ⊆ EIS linkable pages; no generic anchors | Draft, revise |
| R* | Research rules R1–R8 | Research |
| J* | Judge-output validation (§8.3) | Review |
| X* | Revision accounting (§9) | Revise |
| F* | Final gate (§11) | Release |

### 7.2 Intelligent evaluation (judges)

These things are judged, not computed:
- Whether an excerpt supports a sentence in scope, magnitude and direction.
- Overstatement.
- Inference presented as fact.
- Audience fit, purpose, substance, originality, argument quality, nuance, usefulness.
- Search-intent match and answer quality.
- Prose texture, paragraph-scale formula, specificity and replaceability.
- Voice match against samples.

---

## 8. Review panel and independence

### 8.1 Execution

The three judges run **in parallel, as separate engine-executed LLM calls.** Each call gets a fresh context holding its role prompt, rubric, its EIS slice and the artifacts it is entitled to see. It never sees the author's conversation, reasoning or notes (ADR-001). Judges may use a different model or effort level from authors (configuration).

### 8.2 Judge output (schema-constrained)

```json
{
  "judge": "editorial",
  "criteria": [{"id": "ED-C3", "verdict": "fail", "basis": "Section 2 restates the intro without new information."}],
  "acknowledgements": [{"deterministic_id": "H2:contrast-frame-density", "decision": "confirm", "reason": "..."}],
  "findings": [{
    "pattern_id": "ED-GENERIC-ANGLE",
    "severity": "major",
    "location": {"section": "Why it matters", "quote": "exact text copied from the draft"},
    "problem": "...", "evidence": "...", "required_correction": "...",
    "requires_new_evidence": false
  }],
  "strongest_weakness": "Always required, including on a pass."
}
```

The engine adds `draft_sha256`, `round` and `model`. **The judge does not declare the verdict; the engine computes it** from severities: any critical or major finding means fail.

### 8.3 Judge-output validation (deterministic): the anti-rubber-stamp layer

| Check | Purpose |
|---|---|
| J1 | Schema valid (structured outputs make this near-certain; still verified) |
| J2 | **Every finding's `quote` appears verbatim in the reviewed draft** | Rejects hallucinated findings |
| J3 | **Every rubric criterion answered with a basis** | A pass must show its work |
| J4 | **Every deterministic advisory in the judge's jurisdiction acknowledged** (confirm or dismiss, with reason) | Closes B's lost-semantic-findings gap; dismissals recorded |
| J5 | `pattern_id` exists and belongs to the judge's jurisdiction | Keeps judges in their lane |
| J6 | `strongest_weakness` non-empty and quotes or names a location | Forces the adversarial read |

Invalid output is re-run (budget 2). If it's still invalid, the item goes to `requires_human_review`, never to a pass.

### 8.4 Calibration

Judges are the least verifiable component, and this proposal says so plainly. Mitigations:
- A golden set of drafts with seeded defects (uncited statistic, overstatement, generic angle, formulaic paragraphs, voice drift).
- A replay-based test suite that pins pipeline behavior.
- An opt-in live eval (`craftyprose eval judges`) that measures detection and false-alarm rates per judge before thresholds or prompts change.

---

## 9. Revision system

**Input** is every open blocking finding from any source: deterministic, judge or research. The revision planner groups findings by location and root pattern and attaches remediation text from the pattern library. It sends a finding flagged `requires_new_evidence` to **research more**, not to the writer, because rewriting can't create evidence.

**Writer output:** the full revised draft plus one resolution per finding: `changed`, `removed` or `disputed` (with a reason, allowed once per finding).

**Revision gate (deterministic):**

| Check | Closes |
|---|---|
| X1 | Every open blocking finding has a resolution | B's revision ignoring human-writing findings |
| X2 | For `changed`/`removed`, the finding's quote no longer appears verbatim | "Resolved" with unchanged text (ER §8.2) |
| X3 | All draft validators re-run on the revised draft | Revision breaking structure or coverage |
| X4 | **No new facts.** Markers ⊆ allowed claims; D8 number consistency; new proper-noun sequences absent from the ledger and EIS are flagged | Humanizing that fabricates (C's concern, made deterministic) |
| X5 | Headings, links and primary-question placement preserved unless a finding targeted them | SEO structure lost in rewrites |
| X6 | Change-size advisory when the revised share of text is far larger than the findings' scope | Drift from wholesale rewrites; judges are told |
| X7 | **Claim-change check** *[approved amendment]*: claim markers added, removed or moved to a different sentence are listed. Removing a claim the plan requires fails. Any claim-bearing sentence whose wording changed is sent to the evidence judge for re-verification in the next round | Evidence drift: a sentence keeps its marker but no longer says what the evidence supports |
| X8 | **Collateral-change record** *[approved amendment]*: paragraphs outside every finding's location that changed are listed in the revision record, and the reviser must justify each one in its resolutions | Correct content rewritten for no reason |

**Human-writing revision rule** *[approved amendment]*: a revision triggered by human-writing or voice findings is **targeted, never an unconditional rewrite**. The reviser changes only what the findings locate, plus the minimum surrounding text needed for flow (justified under X8). Every such revision passes X4 (no new facts), X7 (claim and evidence drift) and D8 (number consistency) before re-review.

**Resolution is computed, never declared.** After revision, *all* judges re-review the new draft; revisions can introduce defects anywhere. Each finding gets a fingerprint (pattern ID + section + normalized quote), and the engine classifies it:
- **resolved:** absent in the new round
- **persistent:** reported again
- **new:** first appearance; tagged a **regression** if it lies in a revised region

Rules:
- Persistent across 2 revisions → escalate.
- Critical persistent after the budget → `rejected`.
- More new findings than resolved in a round → oscillation warning in the record.

A `disputed` resolution goes to the next round with the dispute text only; the judge upholds or withdraws.

---

## 10. Human-writing layer (first-class)

**Goal:** writing that reads as a specific person or brand speaking to a specific reader, and stays true. It is not a detector score (ADR-009).

| Layer | Mechanism | Source |
|---|---|---|
| **1. Prevention** | The writer receives voice samples and pairs, the lexicon, and a compact avoid-list from the catalog. Content-type anatomy states each element's purpose, never a template ("answer-first intro", not "three bullets then a table") | C voice §6; lesson from A's GCV |
| **2. Deterministic detection** | `writing_patterns.toml`: ~40 patterns in families (content inflation, staging and signposting, contrast frames incl. "X is not Y. It is Z", triads, aphorisms and profundity, staccato runs, chat residue, filler, hedging stacks, transition stacking, synonym cycling, paragraph-shape repetition, sentence-opening repetition). Output is per-pattern hits with locations, plus **cluster scores** per section: a flag when ≥3 families converge (C's "clusters, not isolated tells") | C 33 patterns, B checks, W-001 misses |
| **3. Mode awareness** | Modes `reference`, `marketing` and `shortform` alter thresholds and meanings (in marketing mode, concrete benefit claims and CTAs are expected and generic superlatives become "make concrete", per C). Short-form skips statistics that are meaningless under ~300 words | C marketing mode |
| **4. Judgment** | The writing judge's rubric: per-paragraph specificity/replaceability ("could this paragraph appear in five unrelated pieces?"), manufactured profundity, paragraph-scale formula, rhythm, voice match citing sample sentences. It must acknowledge every H2 advisory | B rubric, C self-questions |
| **5. Remediation** | Targeted revision with pattern remediation: restructure rather than synonym-swap; preserve markers and SEO structure; **X4 no-new-facts** check | B guidance, C rules |
| **6. Calibration** | `tests/corpora/human/` and `tests/corpora/ai/`. Tests assert **zero blocking hits on the human corpus** and bounded advisory rates, and **minimum detection on the AI corpus**. Thresholds change only with a corpus re-run. *[approved amendment]* Every sample carries a provenance and rights record: author/source, how it's known to be human- or AI-written, rights basis (owned, licensed, public domain), license, date and added-by. Sample priority is owned, then licensed or public domain; scraped text of unknown authorship is never assumed human. Samples are added through a corpus interface, with no architecture change. The known-AI set includes Metanous W-20260916-001, used as adversarial evaluation material, never as a detector-gaming target | Fixes B's circular calibration |

**Not included:** an unconditional "humanizer" rewrite of every draft. C did this. It risks fact drift and homogenized prose, and targeted revision gets the benefit without the risk (ADR-009). **Never included:** AI-detector APIs as a gate.

---

## 11. Release

**Final gate (deterministic):**

| Check | Rule |
|---|---|
| F1 | Latest draft passes every blocking deterministic check |
| F2 | The latest review round includes every judge required by the type spec, **bound to the latest draft's sha256**, engine-executed |
| F3 | Zero open critical or major findings (computed); minor findings listed in the record |
| F4 | No `confirm`/`conflicted`/`unsupported` claim used; no `[CONFIRM]` text. *[approved amendment]* Flagged, unconfirmed, unsupported or blocked claims **never enter the releasable package**. If one was omitted, the release record lists it for the human; it is not in the content |
| F5 | Guardrails and required disclosures pass on the rendered output |
| F6 | Budgets respected; content-log repetition checked |

**Release package (deterministic rendering):**
- **Final content.** Internal `{C#}` markers are converted to the type's citation style (inline links, footnotes, a sources note, or removed). This resolves A's contradiction, where Constitution §3.3 kept evidence IDs internal but GCV-009 required them in published text.
- **SEO block:** title, slug, meta, primary question, internal links.
- **JSON-LD generated from the content, not by a model:** Article/BlogPosting, FAQPage, Breadcrumb as the type specifies.
- **Sources list.**
- **`release_record.json`:** gates run, judges and models, rounds, findings resolved/persistent/new, open minors, dismissed advisories, voice-sample availability, independence flag. This is the explanation of why the piece was released.

The status becomes `ready_for_release`. `approve --by <name>` sets `released`, records the approver and appends to the content log. The engine can't prove a human typed the command; that limitation is recorded rather than hidden (ADR-013).

**Derivatives:** a new work item of another type, e.g. a LinkedIn post from a released article, can reuse the source item's verified ledger. This replaces C's repurposing pack with properly gated pieces.

---

## 12. Content-type modules

The shape is **core + type specification + optional type rules.** Generic validators read spec parameters, so the core has no per-type conditionals (ADR-005).

```toml
# craftyprose/content_types/specs/blog_article.toml
id = "blog_article"
goal = "educate"                       # educate | persuade | position | convert | nurture | engage | announce
[length]        words = [900, 1600]
[anatomy]
required        = ["title", "answer_first_intro", "body_sections", "cta"]
optional        = ["faq", "how_we_work"]
body_sections   = [3, 7]
[evidence]
third_party_required = true
min_verified_claims  = 3
max_source_age_years = { statistic = 3, default = 5 }
[discoverability]
enabled = true
primary_question_required = true
title_chars = [30, 65]
meta_description_chars = [120, 160]
keyword_density_max = 0.025
internal_links = [1, 4]
jsonld = ["BlogPosting", "FAQPage?"]
[human_writing]  mode = "marketing"
[review]         judges = ["evidence", "editorial", "writing"]
[release]        format = "markdown"; citation_style = "inline_links"
[approval]       required = true
```

**Initial types (proposed, decision D4):**

| Type | Goal | Distinctive rules |
|---|---|---|
| `blog_article` | Educate | Answer-first intro, question-led sections, FAQ optional, discoverability on |
| `thought_leadership` | Position | Plan must state a thesis and address a counter-position; evidence rigor high; footnote citations; discoverability light |
| `linkedin_post` | Engage | 400–2,200 chars; hook before the fold (type rule); no headings; first-party insight allowed without third-party evidence, but any statistic still needs evidence; `shortform` writing mode |
| `landing_page` | Convert | Hero, subhead, value points (2–6, never forced to 3), proof only from approved claims/testimonials, objection handling, one primary CTA; `marketing` mode |
| `email_newsletter` | Nurture | Subject and preheader character ranges; one primary CTA; discoverability off |

**Next, with no core change:** `service_page`, `product_page`, `faq_page`, `case_study` (which requires approved outcome claims and a client-approval guardrail).

---

## 13. SEO / AEO / discoverability

- **Deterministic presence and ceilings, never repetition quotas.** Primary question present once in title/H1 and intro; density **maximum**; heading hierarchy; FAQ questions as questions; meta ranges; internal links must be real EIS pages. A's exact-count rules (meta 150–155 characters, keyword in H1 + first 100 words + H2 + conclusion + meta, CTAs at 25/50/75%) are dropped.
- **Editorial rubric section `DS-*`:** intent match, answer quality in the first sentences of each section, self-contained answer paragraphs (helps AI answer engines), entity clarity (brand and offering named unambiguously).
- **Structured data is generated deterministically** from the final content at release.
- **Priority rule:** a discoverability finding can't be resolved by removing evidence, voice or substance. X5 and the editorial judge enforce this, and `principles.md` puts discoverability last in the objective hierarchy.

---

## 14. Runtime and LLM integration

```python
class LLM(Protocol):
    def run(self, role: str, system: str, context: list[Block], task: str,
            schema: dict | None = None, tools: list | None = None) -> RoleResult: ...
```

| Implementation | Use |
|---|---|
| `AnthropicLLM` | Default runtime. Model per role from config (default `claude-opus-5`; the judge model may differ). Adaptive thinking; effort per role. JSON artifacts via structured outputs (`output_config.format`). **Prompt caching** with the stable prefix (role prompt + rubric + EIS brand/voice slice) first and volatile work-item artifacts after the breakpoint. Streaming for long drafts. Refusal stop-reason handling with server-side fallback. Research uses the web search and web fetch server tools; fetched documents are taken from tool-result blocks, never model text |
| `ReplayLLM` | Tests and CI: recorded responses keyed by role + input hash; no network |
| `ManualLLM` | "Driven mode" (B-style): writes the role prompt to `staging/`, an external agent or human submits the artifact. **Judges in driven mode are marked `independent: false`**, and the release policy can refuse them (decision D1) |

**Cost (rough, unmeasured):** a long-form piece with 1–2 revision rounds is on the order of several dollars in API cost at Opus-tier prices. This will be measured in the build and reported per piece in the release record.

**Metering from the first milestone** *[approved amendment]*: every LLM call goes through a metering wrapper, whatever the adapter. It records work item, stage, role, adapter, model, latency, input/output/cache tokens, client tool calls, server tool uses (web search/fetch), stop reason and cost. Cost comes from a versioned pricing table; a model or tool with no price is reported as *unpriced*, never as zero. Per-item summaries add attempts, revisions and stage wall time. Cost is measured but not optimized yet.

**Research provider adapter** *[approved amendment]*: research runs through a provider interface. The first providers are Anthropic web search/fetch and user-supplied documents. Evidence may only come from content the engine retrieved or the user supplied, whatever the provider (§4.2).

---

## 15. Artifacts and work-item layout

```text
workspace/
  craftyprose.toml                models/effort per role, budgets, release policy, network
  brands/<brand_id>/...           EIS context and permission (§3.2)
  evidence/snapshots/             content-addressed source text + metadata (shared across items)
  learning.jsonl                  one line per finding: pattern, type, stage, outcome
  work/<W-YYYYMMDD-NNN>/
    request.md
    state.json                    status, stage, attempts, revision budget, accepted versions, draft sha
    events.jsonl                  append-only: every submission, gate run, routing, pause, approval
    submissions/<stage>/<stage>-vN.{json,md}   every submission, including failed ones; immutable
    validations/<stage>-vN.json                every gate run on submission vN (B documented this; now it's true)
    drafts/draft-vN.md                         accepted drafts only; a passed revision becomes the next draft
    human/input-vN.md                          answers and notes from people (resume --note)
    metrics/llm_calls.jsonl                    one metering record per LLM call (ADR-016)
    release/  approval.json (human approval) + the release package (M7)
```

*[implementation refinement, M1]* Every stage's artifact is versioned, including the brief, research, plan, review and release artifacts, rather than keeping single-file "stable" artifacts as B did. `state.json` records which version of each stage is accepted. This is stricter immutability than the sketch above it replaced, and it's how the engine keeps failed submissions without letting them become current. Each stage produces one artifact per submission: research is a single JSON document holding sources, evidence, claims and gaps, and a review round is a single document holding every judge's output plus the deterministic report.

This inherits B's atomic writes, persist-before-validate, immutable versions and draft-persistence invariant, with a numeric version sort (ER §17).

---

## 16. Failure handling

| Failure | Behavior |
|---|---|
| Malformed artifact / invalid JSON | Gate failure with named checks; attempt counted; the artifact is still persisted |
| Missing EIS file or empty brand | Intake refuses with the exact missing path (C: "stop and say so; do not write from memory") |
| Contradictory brand instructions (e.g. voice says "casual", guardrail forbids contractions) | Intake detects conflicting rules (deterministic for known pairs; planner surfaces others) → `needs_input` |
| Network or fetch failure | Research records the source as unfetched; the claim can't verify; no silent fallback to model memory |
| LLM refusal / timeout / rate limit | Retried per SDK policy, then fallback model, then `requires_human_review` with the stop reason |
| Judge output invalid | Re-run ×2, then `requires_human_review` |
| Budget exhaustion | `requires_human_review` or `rejected` (critical persists) with a defect report |
| Crash mid-stage | Resume from `state.json`; persisted artifacts intact |

---

## 17. Testing strategy

| Layer | What | Examples |
|---|---|---|
| Unit | Each validator, claim rule, detector, spec loader, renderer. B's pattern: valid fixture + one deviation | D8 catches "82%" when the excerpt says "72%" |
| Contract | Artifact schemas; judge-output validator; spec schema | A finding quote not in the draft is rejected |
| Integration | Full lifecycle per content type with `ReplayLLM`; every gate outcome and status | Happy path to `ready_for_release` for 3 types |
| **Adversarial** (`tests/adversarial/`) | One test per way to produce bad content while believing it succeeded | See list below |
| **Regression** | Every predecessor failure encoded as a test | Draft persistence; self-resolved finding; zero-resolution revision; wrong-stage writing check; fabricated URL; composite-score bypass (no composites exist) |
| Calibration | Writing detector vs corpora; source classification vs labeled domains | 0 blocking hits on human corpus |
| Live (opt-in) | Judge detection on seeded defects; end-to-end generation demos | `craftyprose eval judges` |

**Adversarial suite (initial):**
- fabricated source URL
- excerpt not in snapshot
- quote altered by one word
- excluded source type
- misquoted number
- uncited statistic
- superlative without evidence
- first-party claim not approved
- expired approved claim
- conflicting sources not disclosed
- vague request
- no audience
- banned topic
- topic blocked by an open question
- contradictory voice rules
- repeated topic
- keyword stuffing
- template-shaped draft that passes structure
- AI-cluster prose
- hallucinated judge finding
- rubber-stamp judge (empty criteria)
- judge verdict inconsistent with findings
- revision that claims a fix but changes nothing
- revision that introduces a new statistic
- revision that drops headings and links
- reviews bound to a stale draft hash
- oscillating revisions
- budget exhaustion
- malformed artifacts
- missing EIS
- crash and resume

---

## 18. Directory layout

```text
CraftyProse/
  pyproject.toml      Python ≥ 3.11; runtime dependency: anthropic (optional extra)
  README.md
  craftyprose/
    cli.py
    core/          state.py orchestrator.py artifacts.py gates.py findings.py events.py budgets.py
    eis/           workspace.py context.py claims.py evidence.py fetch.py learning.py
                   standards/{principles.md, failure_patterns.toml, writing_patterns.toml, source_rules.toml}
    stages/        intake.py research.py plan.py draft.py review.py revise.py release.py   (+ prompts/)
    validators/    brief.py research.py plan.py structure.py claims.py guardrails.py voice.py
                   writing.py discoverability.py judge_output.py revision.py final.py
    judges/        base.py evidence.py editorial.py writing.py  rubrics/*.toml
    content_types/ loader.py specs/*.toml rules/*.py
    runtime/       llm.py anthropic_llm.py replay_llm.py manual_llm.py
    render/        citations.py jsonld.py package.py
  examples/workspace/brands/fernhill/           fictional brand for demos and tests (renamed from northwind-studio in M2; see docs/progress/M2-eis.md)
  tests/           unit/ contract/ integration/ adversarial/ regression/ calibration/ corpora/ fixtures/
  docs/            extraction/ architecture/ guides/
```

---

## 19. Build plan (Phase 5), test-first per milestone

| Milestone | Delivers | Exit criteria |
|---|---|---|
| M1 Core | Artifacts, state machine, statuses, gates, findings, events, budgets, CLI skeleton, `ReplayLLM` | Unit + regression tests for B's proven behaviors and B's bypasses (now failing correctly) |
| M2 EIS | Workspace loader, context slices, guardrail compiler, content-type loader, fictional example brand, standards files with ID tests | Missing/contradictory EIS adversarial tests pass |
| M3 Evidence | Fetch + snapshots, excerpt verification, source rules, claim rules R1–R8, research gate | Evidence adversarial tests pass |
| M4 Intake + plan | Stages, prompts, gates, `needs_input` flow | Vague/banned/blocked/repeat tests pass |
| M5 Draft checks | Structure, D1–D3, D8, guardrails, voice lexicon, discoverability, writing detectors + calibration harness | Calibration thresholds met on corpora |
| M6 Review + revise | Judges, rubrics, judge-output validation, review rounds, revision planner, X1–X6, defect lifecycle, research-more path | Judge and revision adversarial tests pass |
| M7 Release | Final gate, rendering, JSON-LD, release record, approval, content and learning logs | End-to-end replay runs for all initial types |
| M8 Live | `AnthropicLLM`, live end-to-end demos on 3 types, judge eval, cost measurement | Demonstrated generations with release records |
| Phase 6–7 | Full validation, then a dedicated adversarial QA pass ("how could this produce bad content while believing it succeeded?") | Findings fixed or documented |

---

## 20. Architectural review (Phase 4)

### 20.1 Inherited concepts

| Concept | From | Where in CraftyProse |
|---|---|---|
| Knowledge before writing | A §2, B, C | Plan and allowed claims; writer can't research |
| Evidence tiers, excluded sources, criticality | A 02/13 | `source_rules.toml`, claim rules |
| Knowledge gaps and contradictions | A 11, B, C §11 | `gaps.json`, `open_questions.toml`, `conflicted` status |
| Expertise elements (trade-offs, mistakes, warnings, examples) | A 11 | Plan argument types; used when evidence supports them |
| Voice profile with reasons; samples outrank rules | A 08, C §6 | `voice.toml`, samples, pairs |
| Failure-pattern taxonomy | A 15 | `failure_patterns.toml` |
| Trust-test questions | A 06 | Editorial rubric |
| Artifact-first, immutable, persist-before-validate, budgets, draft-persistence invariant | B | Core |
| Finding schema and severity semantics | B | Findings (extended) |
| Aggregate final gate, no weighted score | B | Final gate |
| Knowledge base as source of truth; stop if missing | B, C | EIS workspace |
| `[CONFIRM]` instead of fabrication | C | `confirm` claim status |
| Humanizer patterns, modes, clusters, false-positive list | C | Writing catalog and modes |
| Human topic choice; topic log | C | Optional `pitch`; content log |
| Content types with their own goal and gates | A 16 | Type specs |

### 20.2 Improved concepts

| Concept | Predecessor form | CraftyProse form | Why |
|---|---|---|---|
| Confidence | 0–100 weighted; self-reported (109/100) | Rule-derived categorical with reasons | Explainable; can't be gamed by inputs |
| Coverage | Self-declared % / ≥3 markers | Sentence-level factual detection + number consistency | Catches uncited and misquoted facts |
| Source verification | Placeholders / none | Engine-fetched snapshots + verbatim excerpt check | Closes fabricated sources and quotes |
| Review | Same-session self-review; format-only gate | Independent judges + judge-output validation | Closes rubber stamp |
| Resolution | Declared by reviser or reviewer | Computed by re-review with fingerprints | Closes self-resolution |
| Human writing | Uncalibrated regex at the wrong stage; or a full rewrite pass | Cluster detection at the draft gate + judge + targeted revision + corpora | Measurable, fixable, fact-safe |
| Knowledge package | 10 mandatory components | Proportional plan per content type | A LinkedIn post can be done properly |
| SEO | Exact counts and placements | Presence + ceilings + deterministic JSON-LD | Discoverable without stuffing |
| Approval | Honor-system CLI | Approver recorded; `ready_for_release` vs `released`; limitation documented | Honest audit trail |
| `validations/` | Documented, not written | Every gate run recorded, with a test | Documented behavior is tested behavior |

### 20.3 New concepts

- Judge independence as architecture (engine-executed, least context, optional different model).
- Judge-output validation (quotes exist, rubric complete, advisories acknowledged, engine-computed verdict, mandatory strongest weakness).
- Claim-kind taxonomy with per-kind evidence and release rules.
- Number-consistency check (D8) and no-new-facts check (X4).
- Review-to-draft hash binding.
- Defect lifecycle (resolved/persistent/new/regression) and oscillation detection.
- `needs_input` and `blocked` statuses: a first-class "stop and ask".
- Research-more routing from review findings.
- Context slices (least context) with hashing for reproducibility and caching.
- Calibration corpora for the writing detector.
- Guardrails compiled to checks; contradiction detection in brand rules.
- Derivative work items reusing a verified ledger.
- A release record that explains why something was released.

### 20.4 Removed concepts

| Removed | Reason |
|---|---|
| 11-reviewer board, 5 HQF evaluators, unanimity, 70% target rejection rate | Overlapping seats; a quota is a metric to game; 3 disjoint judges cover the jurisdictions |
| Composite scores (CES, GCV composite, confidence 0–100, voice ≥90) | Scores let defects trade against polish |
| Writer declaration | Self-attestation verifies nothing |
| Template-forcing validators (trade-off table, decision framework, mistake/warning/tip counts, CTA positions, first-person experience markers, original-research markers) | They produce formula and invite fabrication |
| Express/Standard/Authority paths, 13 numbered gates | Replaced by type specs + criticality |
| Knowledge graph, asset library, evergreen webhooks, learning curator | Deferred; content-addressed snapshots and a learning log cover near-term needs |
| Unconditional humanizer rewrite pass | Fact drift, homogenization; targeted revision instead |
| Universal em-dash ban | A voice policy, not a law |
| Agency operations, dashboard, kanban, scheduler, email ingest, 124 agent prompts | Outside the engine |
| All client, brand, region and vertical specifics in core | Belong in EIS workspaces |

### 20.5 Unresolved (technical uncertainty, investigated during the build)

1. **Judge reliability.** Detection and false-alarm rates are unknown until measured on seeded defects. The architecture contains the risk (validation, independence), but it can't eliminate it.
2. **Factual-sentence detector precision (D2).** The strong/weak signal split is a hypothesis to calibrate. Too strict produces marker noise; too loose misses claims.
3. **Writing-detector thresholds.** They depend on the corpora (decision D3).
4. **Fetch coverage.** JavaScript-heavy pages and PDFs may need the API's web-fetch tool rather than a stdlib fetch.
5. **Cost and latency per piece.** To be measured in M8.
6. **Short-form writing signals.** Which patterns are meaningful under 300 words needs evidence.
7. **Named-entity check (X4).** A proper-noun heuristic will have false positives; it starts advisory.

---

## 21. Licensing and data hygiene

- No client data (Harmony knowledge, Click Savvy vault, emails) enters CraftyProse. The example brand is fictional.
- The writing-pattern catalog is **rewritten in our own words**. C's catalog credits Wikipedia's "Signs of AI writing" (CC BY-SA 4.0) and an upstream skill whose license is unknown. CraftyProse cites Wikipedia as a reference and copies no text from either.
- Lineage B's W-20260916-001 drafts (the owner's own content) are approved as known-AI adversarial fixtures (decision D2).

---

## 22. Approval gate

### 22.1 Decisions as approved (2026-09-25)

| # | Approved decision |
|---|---|
| D1 | The Anthropic API is the production LLM interface. The `AnthropicLLM` / `ReplayLLM` / `ManualLLM` adapter architecture stays. Cost is not optimized early; the engine is **metered from the first milestone** (tokens, calls, models, tool calls, latency, revisions, cost per item) (§14) |
| D2 | W-20260916-001 and its drafts may be used as **known-AI adversarial evaluation material**, not as a target for gaming detectors. No Harmony Homes material |
| D3 | The human corpus prioritizes known human-written material the owner has rights to, then explicitly licensed or public-domain material. **Scraped text is never assumed human.** Samples are added through a corpus interface, and every sample keeps provenance and rights metadata (§10) |
| D4 | Blog article, thought leadership, LinkedIn post, landing page and email newsletter, implemented as **declarative specifications over one core** (§12) |
| D5 | **Every type requires human approval. The engine may reach `ready_for_release` but never releases or publishes in v1.** Flagged, unconfirmed, unsupported or blocked claims never enter the releasable package (§11 F4) |
| D6 | Anthropic web search/fetch plus user-supplied documents, **behind a research-provider adapter**. Evidence comes only from content the engine retrieved or the user supplied (§14) |
| D7 | Git initialized before implementation, with a clean baseline commit; no elaborate Git/CI infrastructure yet |
| D8 | *(added at approval)* Human-writing revision is **targeted, never an unconditional rewrite**. Correct content is preserved, and every revision is checked for factual drift, evidence drift, claim changes and new unsupported facts (§9 X4, X7, X8) |
| D9 | *(added at approval)* Test-first. The normal test suite never needs the network or the API; deterministic tests use `ReplayLLM` fixtures |
| D10 | *(added at approval)* Build the smallest complete implementation of the seven-stage architecture first. No new agents, stages, dependencies or infrastructure unless implementation shows a concrete need. **An ADR that implementation evidence says must change is raised with that evidence before proceeding, never changed silently** |

### 22.2 Decisions as originally proposed (for the record)

| # | Decision | Options | Recommendation |

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **D1** | **Execution mode** | (a) Autonomous: the engine calls the Claude API for every role; judges are independent. (b) Driven only: an external agent runs stages (B-style); independence can't be guaranteed. (c) Both, with release requiring independent judges | **(c)**, built autonomous-first. It needs an Anthropic API key and has per-piece cost (§14). Tests never call the API |
| **D2** | **Predecessor text as fixtures** | Use W-20260916-001 drafts as the known-AI calibration sample? | Yes, if you agree. Nothing from Harmony |
| **D3** | **Human-writing corpus** | Genuinely human business writing we have rights to: your own pre-2023 writing, public-domain business prose, or samples you license | Your own writing plus public-domain prose to start. This is the biggest open input |
| **D4** | **Initial content types** | The five in §12, or a different set | `blog_article`, `thought_leadership`, `linkedin_post`, `landing_page`, `email_newsletter` |
| **D5** | **Release policy** | Human approval required for all types? May `[CONFIRM]` items reach the human? | Approval required for all; confirmations may reach the human, flagged, never auto-released |
| **D6** | **Research tooling** | Anthropic web search/fetch server tools; stdlib fetch; third-party APIs (Tavily/Firecrawl need keys) | Anthropic server tools + stdlib fetch + user-supplied documents |
| **D7** | **Repository** | Initialize git in `CraftyProse/`? | Yes, before M1 |

Each milestone ends with passing tests and a short progress note.
