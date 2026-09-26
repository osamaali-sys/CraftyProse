# M2: EIS and content types (progress note)

**Date:** 2026-09-26 · **Branch:** `m2-eis` (from `main` at `9777cf5`, after PR #1) · **Result:** 189 tests pass (85 new), no network.

## Scope

The approved M2 scope (architecture §19):
- the EIS brand workspace
- context slices
- the guardrail compiler
- the content-type loader with the five approved specs (decision D4)
- a fictional example brand
- the standards files, with ID tests

The engine doesn't consume any of this yet. The stages that use it start in M4.

## Behavior implemented

| Area | Behavior |
|---|---|
| Brand workspace (`eis/workspace.py`) | Loads `brand.toml`, `audiences.toml` and `voice.toml` (required), plus `claims.toml`, `guardrails.toml`, `open_questions.toml`, `content_log.jsonl`, voice samples and before/after pairs (optional). Every error names the file and key; missing required files are listed by path |
| Strict schema (`core/schema.py`) | A shared TOML reader. Unknown keys, wrong types, empty required values, bad ranges, bad URLs and bad dates are errors, so a typo can't fall back to a default |
| Provenance (`eis/provenance.py`) | Voice samples and pairs carry author, source, `human_written`, `how_known`, rights (owned, licensed, public_domain, synthetic), license, added by and added on. Synthetic text can't be marked human. A human-written sample must say how that's known, and licensed samples must name the license. The M5 calibration corpus will use the same record (decision D3) |
| Claims | Approved first-party claims (fact, marketing, testimonial) with approver, dates and allowed wording; expired claims are never usable. Testimonials need attribution. Forbidden claims are matched by phrase or regex |
| Contradictions (`eis/contradictions.py`) | Six deterministic checks: term both preferred and avoided; preferred term forbidden by a guardrail; approved claim using a forbidden term; approved claim matching a forbidden claim; approved non-testimonial claim using an avoided term; "I" voice against a no-first-person rule; em-dash policy contradicted by the samples |
| Guardrails (`eis/guardrails.py`) | Compiled to named, blocking checks tagged with pattern IDs: forbidden terms, forbidden patterns, banned topics, required disclosures (only when triggered), and speaker policy (ignoring quotations and blockquotes). Also forbidden claims, plus a topic check that blocks banned topics and topics tied to open questions. Rules can be scoped to content types |
| Context slices (`eis/context.py`) | One declared slice per role (7 roles), rendered deterministically, hashed and marked cacheable. The writing judge gets voice only. The evidence judge gets claims and guardrails but no voice. Each judge gets only its own failure patterns |
| Content types (`content_types/`) | One strict loader and five specs: `blog_article`, `thought_leadership`, `linkedin_post`, `landing_page`, `email_newsletter`. Anatomy uses a fixed element vocabulary with count and length ranges. A spec that turns off human approval is refused (decision D5) |
| Standards (`eis/standards/`) | `principles.md` (the objective hierarchy) and `failure_patterns.toml`: 84 patterns in 7 jurisdictions. IDs are unique and prefixed, and structure patterns are deterministic only |
| Example brand | `examples/workspace/brands/fernhill`: a fictional courier-software brand. All names, figures and `.example` URLs are invented, and its voice samples are marked synthetic |
| CLI | `brand init` scaffolds files with empty required values, so `brand check` names each field until it's filled. `brand check` validates and lists contradictions. `types` lists the content types. `new` refuses an unknown type or a broken brand before creating anything |

## Tests added (85)

| Suite | New | Covers |
|---|---|---|
| Unit | 78 | Schema reader; workspace loading and every validation rule; provenance rules; the six contradiction types (plus the non-contradiction cases); every guardrail type, scoping, quotations, topic checks; the five specs and every spec-validation rule; slice contents, isolation, determinism and change propagation; pattern library integrity; every pattern ID used in the code exists |
| Integration | 6 | `types`, `brand check` (clean and contradictory), `brand init` then check, `new` refusing a bad type or brand |
| Regression | 1 | No predecessor identity (agency, clients, regions, vertical terms) anywhere in the engine or examples. Verified by planting a client name and watching it fail |

Run: `python -m unittest discover -s tests -t .` (about 14 s).

## Decisions discovered during implementation

None of these changes an accepted ADR.

1. **Spec shape refined from the §12 sketch.**
   - `[length]` is a unit plus a range.
   - Anatomy has `counts`, `fields` and `limits` subtables.
   - `min_verified_claims` became `min_supported_claims`, because it also counts approved first-party claims.
   - `jsonld` lists the types emitted when their content exists; the sketch's `"FAQPage?"` notation is gone.
2. **Writing modes stay at three** (reference, marketing, shortform). Thought leadership uses `reference`: every writing pattern applies at full strength, and voice still comes from the voice profile. I didn't add an "essay" mode.
3. **Guardrail terms match whole words or phrases with no stemming.** Authors list the variants they mean ("price", "pricing"). This keeps checks predictable and avoids false hits, such as "prices" in a sentence about fuel.
4. **Slices include the editorial principles and each judge's pattern subset.** These are EIS standards the judges apply, so they belong in the cacheable prefix.
5. **Only one speaker policy exists** (`no_first_person_singular`). Others are added when a brand needs one.
6. **`new` validates the brand and type first.** This happens in the CLI, so the core stays brand-agnostic. Intake (M4) will still turn contradictions into `needs_input` questions rather than refusals.
7. **The example brand was renamed** from the sketched `northwind-studio` to `fernhill`, to avoid a well-known vendor sample name.

## Unresolved issues

- **No verified human voice samples yet.** The example brand's samples are synthetic, and the slices say so. Real brands need samples with known provenance before voice judging means much (decision D3).
- **Guardrail regexes come from brand authors** and run unbounded. That's acceptable for trusted authors, but a pathological pattern could be slow.
- **Contradiction checks cover only the known cases.** Others (e.g. a register at odds with a rule) will be surfaced by the intake planner in M4.
- **The content-log repetition check** is part of intake (M4); M2 only loads the log.
- **Packaging data files** (`specs/*.toml`, `standards/*`) are declared in `pyproject.toml` but a built wheel hasn't been tested.

## Next

M3: evidence. Engine-fetched snapshots, excerpt verification, source-authority rules (`source_rules.toml`), the claim rules R1–R8, and the research gate behind the research-provider adapter (ADR-015).
