# M1: Core (progress note)

**Date:** 2026-09-25 · **Branch:** `m1-core` (baseline `8413caf` on `main`) · **Result:** 104 tests pass, no network.

## Scope

The approved M1 scope (architecture §19): artifacts, state machine, statuses, gates, findings, events, budgets, CLI skeleton and `ReplayLLM`, plus metering from the first milestone (decision D1, ADR-016). No stage content, EIS, prompts or providers. Those are M2–M8.

## Behavior implemented

| Area | Behavior |
|---|---|
| Lifecycle | The 7 approved stages and their allowed transitions are fixed in `core/lifecycle.py`. The engine refuses any route a router asks for outside them, and pauses for a person instead |
| Statuses | `in_progress`, `needs_input`, `blocked`, `requires_human_review`, `rejected`, `ready_for_release`, `released` |
| Submissions | Persisted before gating; immutable, numerically versioned; refused (and not persisted) when the item isn't in progress, the stage isn't current, or an outside party submits a review or release artifact |
| Gates | Built-in checks (parse, object, non-empty, revised draft present, draft binding) plus stage validators. Every run is recorded in `validations/`. A crashing validator fails closed. Advisory checks are recorded and returned without blocking |
| Acceptance | A passed draft or revision is promoted to the next draft version before routing. Failed submissions never become current |
| Budgets | Attempts per stage (gate failures and producer failures) escalate to `requires_human_review`. Review→revise and review→research both count against the revision budget |
| Findings | Strict parsing. `resolved`, `verdict`, `status` and `source` are rejected as engine-owned. The verdict is computed from severities; fingerprints are stable across whitespace, case and quote style |
| Draft binding | Review artifacts carry the SHA of the draft they judged. The engine stamps it and verifies it, and a stale binding fails the gate |
| Human actions | `approve --by` (the only path to `released`, with an approval record), `reject --by --reason`, `resume --by [--note] [--grant-revisions]` |
| LLM contract | `LLMRequest` / `LLMResponse` / `Usage` / `ToolUse`; content-hash request keys |
| ReplayLLM | Keyed mode (any prompt change is a miss) and scripted mode; misses raise, never improvise |
| Metering | Every call through the engine is recorded: stage, role, adapter, requested and actual model, latency, five token classes, client and server tool uses, stop reason, cost, pricing version, errors. Unpriced models and tools are reported as unpriced, not zero. `usage` adds gate runs, stage wall time, attempts and revisions |
| CLI | `new`, `status`, `events`, `usage`, `list`, `approve`, `reject`, `resume` |
| Tests | Socket guard: the suite fails any test that tries to open a network connection |

## Tests

| Suite | Tests | Covers |
|---|---|---|
| `tests/unit` | 55 | Files and work-item layout, validation results, findings, lifecycle routes, budgets, config, state, events, stage registry, replay, pricing, metering, network guard |
| `tests/integration` | 39 | Engine creation, full lifecycle to `ready_for_release`, approval, external submissions, gate failures and records, attempt escalation, producer feedback, malformed artifacts, failing producers and routers, revision loop and promotion, revision budget and grants, research-more path, draft binding, pause/resume, rejection, CLI |
| `tests/regression` | 10 | Predecessor failures: author-submitted reviews, forged release, self-resolved findings, pass-with-major verdict, draft persistence, missing validation records, lexicographic version sort, state that can't survive disk, gate deadlock, crashing validator |

Run: `python -m unittest discover -s tests -t .` (about 7 s).

## Decisions discovered during implementation

None of these changes an accepted ADR.

1. **Every artifact is versioned**, not only drafts and reviews (architecture §15 updated, marked as an implementation refinement). This is stricter immutability. State records which version of each stage is accepted.
2. **Engine-only stages are a lifecycle rule** (review, release), not a per-stage flag. A stage definition can't opt out of ADR-001.
3. **A gate check can be blocking or advisory.** Blocking failures send the stage back to its producer with the failed checks as feedback, under the attempt budget. Advisories travel downstream for judges to acknowledge (J4, M6).
4. **Producer failures count as attempts.** An LLM error, replay miss or wrong artifact type is a failed attempt, so repeated provider failure escalates to a person like any other failure (§16).
5. **Routing failures pause instead of crashing.** A router bug or disallowed route leaves the accepted artifact in place and pauses at `requires_human_review` with the reason.
6. **`answer` became `resume --note`.** Architecture §5.2 said `needs_input` "resumes on `answer`". One human command now resumes any paused state, storing the note as a versioned human input the stage can read.
7. **Line endings are pinned to LF** (`.gitattributes`), and the engine normalizes newlines before hashing, so content hashes match across platforms.

## Open for a later milestone (flagged, not changed)

- **Where deterministic draft-quality defects go.** Architecture §7 runs D1–D8 at the draft and revise gates (retry the stage with feedback). §5.1 also lists a deterministic report inside the review round. M1 supports both mechanisms. The choice will be made in M5/M6 with evidence. If it requires changing ADR-006 or ADR-008, it comes back for approval first.

## Unresolved issues

- **Web search and web fetch prices are not in the pricing table** (they weren't in the cached reference). Research cost will show `cost_complete: false` until the published rates are confirmed and added to `runtime/pricing.toml`.
- **The pricing table is a 2026-06-24 snapshot**; it needs verifying against the published page before costs are relied on.
- **Single-writer assumption.** There's no file locking; one engine process per workspace.
- **Event and metering logs are re-read to number each new line.** This is correct across handles, and fine at the scale of one work item; it would need an index if logs grew to thousands of lines.
- **Approval identity can't be verified** (ADR-013); the approval record says so.
- **No production stages yet**, so the CLI can't run or submit stages. That arrives with M4 (intake and plan) and `ManualLLM`. `AnthropicLLM` is M8.

## Next

M2: the EIS brand workspace, context slices, guardrail compiler, content-type loader with the five approved specs, a fictional example brand, and standards files with ID tests.
