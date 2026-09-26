"""The orchestrator: deterministic state machine for work items.

The engine owns state and transitions. It never writes content. A submission
(from an engine-run producer or, for authoring stages, from outside) is:

1. refused if the item isn't in progress, the stage isn't current, or the stage
   is engine-only and the submission came from outside;
2. persisted as a new immutable version, before anything else can fail;
3. gated: built-in checks, then the stage's validators, every run recorded;
4. on failure, counted against the stage's attempt budget (then escalated);
5. on success, accepted; a draft or revision is promoted to the next draft
   version *before* routing, so later stages always see the corrected text;
6. routed by the stage's router, but only along routes the lifecycle allows,
   with revision loops counted against the revision budget.

The engine can mark work ``ready_for_release``. Only ``approve``, a human action
that names the approver, marks it ``released`` (decision D5). The engine can't
verify that a person, rather than a script, ran ``approve``; the approval record
states who was named (ADR-013).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..runtime.llm import LLM
from ..runtime.metering import MeteredLLM, aggregate, read_records
from ..runtime.pricing import Pricing
from .config import EngineConfig
from .events import EventLog
from .files import to_json_text, write_json_atomic, write_text_atomic
from .lifecycle import (
    DRAFT_STAGES,
    ENGINE_ONLY_STAGES,
    PAUSED_STATUSES,
    REVISION_ENTRIES,
    TERMINAL_STATUSES,
    Status,
    check_route,
)
from .stages import GateContext, ProduceContext, RouteContext, StageDef, StageRegistry
from .state import Pause, WorkState
from .validation import GateResult, ValidationResult
from .view import WorkView
from .workitem import WorkItem

WORK_ID_RE = re.compile(r"^W-\d{8}-\d{3}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
ORIGINS = ("engine", "external")


class EngineError(RuntimeError):
    pass


class UnknownWorkItem(EngineError):
    pass


@dataclass(frozen=True)
class SubmitResult:
    ok: bool
    work_id: str
    stage: str
    status: str
    next_stage: str
    message: str
    version: int | None = None
    failures: tuple[dict[str, Any], ...] = ()
    advisories: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "work_id": self.work_id, "stage": self.stage, "status": self.status,
            "next_stage": self.next_stage, "message": self.message, "version": self.version,
            "failures": list(self.failures), "advisories": list(self.advisories),
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Engine:
    def __init__(
        self,
        workspace: Path,
        *,
        registry: StageRegistry | None = None,
        llm: LLM | None = None,
        config: EngineConfig | None = None,
        pricing: Pricing | None = None,
        clock: Callable[[], datetime] = _utc_now,
        timer: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.workspace = Path(workspace)
        self.registry = registry
        self.config = config or EngineConfig.load(self.workspace / "craftyprose.toml")
        self._clock = clock
        self._timer = timer
        self.meter: MeteredLLM | None = None
        if llm is not None:
            self.meter = MeteredLLM(
                llm,
                pricing or Pricing.load(self.config.pricing_path),
                model_for=self.config.model_for,
                now=self._now,
                timer=timer,
            )

    # ------------------------------------------------------------------ basics
    @property
    def work_root(self) -> Path:
        return self.workspace / "work"

    def _now(self) -> str:
        return self._clock().astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _item(self, work_id: str) -> WorkItem:
        if not WORK_ID_RE.match(work_id or ""):
            raise UnknownWorkItem(f"not a work id: {work_id!r}")
        item = WorkItem(self.work_root / work_id)
        if not item.exists():
            raise UnknownWorkItem(f"no work item {work_id}")
        return item

    def _events(self, item: WorkItem) -> EventLog:
        return EventLog(item.events_path, self._now)

    def _save(self, item: WorkItem, state: WorkState) -> None:
        state.updated = self._now()
        item.save_state(state)

    def _stage(self, name: str) -> StageDef:
        if self.registry is None:
            raise EngineError("this operation needs a stage registry")
        return self.registry[name]

    def status(self, work_id: str) -> WorkState:
        return self._item(work_id).load_state()

    def view(self, work_id: str) -> WorkView:
        item = self._item(work_id)
        return WorkView(item, item.load_state(), self.registry)

    def events(self, work_id: str) -> list[dict[str, Any]]:
        return self._events(self._item(work_id)).read()

    def list(self) -> list[str]:
        if not self.work_root.exists():
            return []
        return sorted(p.name for p in self.work_root.iterdir() if WORK_ID_RE.match(p.name) and (p / "state.json").exists())

    # --------------------------------------------------------------- creation
    def new(self, request_text: str, *, brand_id: str, content_type: str) -> WorkState:
        if not (request_text or "").strip():
            raise EngineError("the request is empty")
        for label, value in (("brand_id", brand_id), ("content_type", content_type)):
            if not SLUG_RE.match(value or ""):
                raise EngineError(f"{label} must be a lowercase slug, got {value!r}")
        item = self._allocate()
        now = self._now()
        write_text_atomic(item.request_path, request_text.strip() + "\n")
        state = WorkState(
            work_id=item.work_id, brand_id=brand_id, content_type=content_type,
            status=Status.IN_PROGRESS, stage="intake", created=now, updated=now,
            revision_allowance=self.config.budgets.max_revisions,
        )
        item.save_state(state)
        self._events(item).append("created", stage="intake", brand_id=brand_id, content_type=content_type)
        return state

    def _allocate(self) -> WorkItem:
        date = self._clock().astimezone(timezone.utc).strftime("%Y%m%d")
        self.work_root.mkdir(parents=True, exist_ok=True)
        taken = [int(p.name[-3:]) for p in self.work_root.glob(f"W-{date}-*") if WORK_ID_RE.match(p.name)]
        seq = max(taken, default=0) + 1
        while True:
            if seq > 999:
                raise EngineError(f"more than 999 work items on {date}")
            root = self.work_root / f"W-{date}-{seq:03d}"
            try:
                root.mkdir()
                return WorkItem(root)
            except FileExistsError:
                seq += 1

    # ------------------------------------------------------------- submission
    def submit(self, work_id: str, stage: str, text: str, *, origin: str = "external") -> SubmitResult:
        """Submit an artifact for the current stage. ``text`` is JSON or Markdown."""
        if origin not in ORIGINS:
            raise EngineError(f"origin must be one of {ORIGINS}")
        item = self._item(work_id)
        state = item.load_state()
        events = self._events(item)

        refusal = self._refusal(state, stage, origin)
        if refusal:
            events.append("submission_refused", stage=stage, origin=origin, reason=refusal)
            return self._result(False, state, stage, refusal)
        sdef = self._stage(stage)

        ref = item.put_submission(stage, sdef.fmt, text)
        events.append("submitted", stage=stage, version=ref.version, origin=origin, sha256=ref.sha256)

        artifact, gate = self._run_gate(item, state, sdef, ref.version, ref.path.read_text(encoding="utf-8"))
        item.record_validation(stage, ref.version, {
            "work_id": work_id, "stage": stage, "version": ref.version, "origin": origin,
            "at": self._now(), "passed": gate.passed, "gate": gate.to_dict(),
        })
        state.last_gate[stage] = {"version": ref.version, "passed": gate.passed}
        failures = tuple(c.to_dict() for c in gate.failures)
        advisories = tuple(c.to_dict() for c in gate.advisories)

        if not gate.passed:
            events.append("gate_failed", stage=stage, version=ref.version,
                          checks=[c["name"] for c in failures])
            message = self._count_attempt(state, stage, events, "gate failed")
            self._save(item, state)
            return self._result(False, state, stage, message, ref.version, failures, advisories)

        events.append("gate_passed", stage=stage, version=ref.version, advisories=len(advisories))
        state.attempts[stage] = 0
        accepted: dict[str, Any] = {"version": ref.version, "sha256": ref.sha256}
        if sdef.binds_draft:
            accepted["draft_sha256"] = artifact.get("draft_sha256")
        state.accepted[stage] = accepted

        if stage in DRAFT_STAGES:
            draft_text = artifact if stage == "draft" else artifact[sdef.draft_field]
            draft = item.put_draft(draft_text)
            state.draft_version, state.draft_sha256 = draft.version, draft.sha256
            events.append("draft_promoted", stage=stage, draft_version=draft.version, sha256=draft.sha256)

        self._save(item, state)  # acceptance is durable before routing runs
        message = self._route(item, state, sdef, artifact, gate, events)
        self._save(item, state)
        return self._result(True, state, stage, message, ref.version, failures, advisories)

    def _refusal(self, state: WorkState, stage: str, origin: str) -> str | None:
        if state.status is not Status.IN_PROGRESS:
            return f"work item is {state.status.value}, not in progress"
        if stage != state.stage:
            return f"the current stage is {state.stage!r}, not {stage!r}"
        if origin == "external" and stage in ENGINE_ONLY_STAGES:
            return f"{stage} artifacts are produced by the engine and can't be submitted from outside"
        return None

    def _run_gate(self, item: WorkItem, state: WorkState, sdef: StageDef, version: int,
                  text: str) -> tuple[Any, GateResult]:
        builtin = ValidationResult("engine")
        artifact: Any = None
        parsed = False
        if sdef.fmt == "json":
            try:
                artifact = json.loads(text)
                builtin.add("artifact_parses", True)
                parsed = True
            except json.JSONDecodeError as exc:
                builtin.add("artifact_parses", False, f"invalid JSON: {exc}")
            if parsed:
                is_obj = isinstance(artifact, dict)
                builtin.add("artifact_is_object", is_obj, "" if is_obj else "a JSON artifact must be an object")
                parsed = is_obj
        else:
            artifact = text
            parsed = bool(text.strip())
            builtin.add("artifact_not_empty", parsed, "" if parsed else "the artifact is empty")

        if parsed and sdef.draft_field:
            value = artifact.get(sdef.draft_field)
            ok = isinstance(value, str) and bool(value.strip())
            builtin.add("revised_draft_present", ok, "" if ok else f"'{sdef.draft_field}' must hold the complete revised draft")
            parsed = parsed and ok
        if parsed and sdef.binds_draft:
            bound = artifact.get("draft_sha256")
            ok = state.has_draft and bound == state.draft_sha256
            builtin.add("draft_binding", ok, "" if ok else
                        f"artifact names draft {str(bound)[:12]} but the current draft is {str(state.draft_sha256)[:12]}")

        results = [builtin]
        if parsed:
            view = WorkView(item, state, self.registry)
            ctx = GateContext(state.work_id, sdef.name, artifact, view, self.config)
            for validator in sdef.validators:
                name = getattr(validator, "__name__", type(validator).__name__)
                try:
                    results.append(validator(ctx))
                except Exception as exc:  # a crashing validator never passes a gate
                    results.append(ValidationResult(name).add("validator_error", False, f"{type(exc).__name__}: {exc}"))
        return artifact, GateResult(sdef.name, version, results)

    def _count_attempt(self, state: WorkState, stage: str, events: EventLog, what: str) -> str:
        used = state.attempts.get(stage, 0) + 1
        state.attempts[stage] = used
        limit = self.config.budgets.max_attempts_per_stage
        if used >= limit:
            reason = f"{stage}: {what} {used} time(s); attempt budget of {limit} used"
            self._pause(state, Status.REQUIRES_HUMAN_REVIEW, stage, reason, {"attempts": used}, events)
            return reason
        return f"{stage}: {what} (attempt {used} of {limit}); fix and resubmit"

    def _pause(self, state: WorkState, status: Status, stage: str, reason: str,
               details: dict[str, Any], events: EventLog) -> None:
        state.status = status
        state.pause = Pause(status, stage, reason, details, self._now())
        events.append("paused", stage=stage, status=status.value, reason=reason, details=details)

    def _route(self, item: WorkItem, state: WorkState, sdef: StageDef, artifact: Any,
               gate: GateResult, events: EventLog) -> str:
        stage = sdef.name
        view = WorkView(item, state, self.registry)
        try:
            route = sdef.router(RouteContext(state.work_id, stage, artifact, gate, view, self.config))
            check_route(stage, route, has_draft=state.has_draft)
        except Exception as exc:  # a broken router or a disallowed route stops for a person
            reason = f"{stage}: routing failed ({type(exc).__name__}: {exc})"
            self._pause(state, Status.REQUIRES_HUMAN_REVIEW, stage, reason, {}, events)
            return reason

        if route.action == "advance":
            to = route.to_stage
            if (stage, to) in REVISION_ENTRIES:
                if state.revision_count >= state.revision_allowance:
                    reason = (f"revision budget used ({state.revision_count} of {state.revision_allowance}); "
                              f"review wanted {to}: {route.reason}")
                    self._pause(state, Status.REQUIRES_HUMAN_REVIEW, stage, reason,
                                {"wanted": to, "revision_count": state.revision_count}, events)
                    return reason
                state.revision_count += 1
            state.stage = to
            events.append("routed", stage=stage, to=to, reason=route.reason, revision_count=state.revision_count)
            return f"{stage} passed; next stage: {to}"
        if route.action == "pause":
            self._pause(state, route.status, stage, route.reason, route.details, events)
            return f"{stage}: {route.status.value}: {route.reason}"
        if route.action == "ready_for_release":
            state.status = Status.READY_FOR_RELEASE
            events.append("ready_for_release", stage=stage, reason=route.reason,
                          draft_version=state.draft_version, draft_sha256=state.draft_sha256)
            return "ready for release; a person must approve it"
        state.status = Status.REJECTED  # route.action == "reject"
        events.append("rejected", stage=stage, by="engine", reason=route.reason)
        return f"rejected: {route.reason}"

    # ------------------------------------------------------------ run a stage
    def run_stage(self, work_id: str) -> SubmitResult:
        """Produce the current stage's artifact through the metered LLM, then submit it."""
        item = self._item(work_id)
        state = item.load_state()
        if state.status is not Status.IN_PROGRESS:
            return self._result(False, state, state.stage, f"work item is {state.status.value}, not in progress")
        sdef = self._stage(state.stage)
        if sdef.producer is None:
            raise EngineError(f"stage {sdef.name!r} has no producer; submit its artifact instead")
        if self.meter is None:
            raise EngineError("running a stage needs an LLM adapter")

        events = self._events(item)
        view = WorkView(item, state, self.registry)
        ctx = ProduceContext(work_id, sdef.name, view, self.meter.bind(item.metrics_path, work_id, sdef.name),
                             view.last_failures(sdef.name), self.config)
        events.append("stage_run_started", stage=sdef.name, feedback=len(ctx.feedback))
        t0 = self._timer()
        try:
            artifact = sdef.producer(ctx)
            text = self._serialize(sdef, artifact, state)
        except Exception as exc:
            duration = round((self._timer() - t0) * 1000, 3)
            events.append("producer_failed", stage=sdef.name, error=f"{type(exc).__name__}: {exc}", duration_ms=duration)
            message = self._count_attempt(state, sdef.name, events, "producer failed")
            self._save(item, state)
            return self._result(False, state, sdef.name, message)
        result = self.submit(work_id, sdef.name, text, origin="engine")
        events.append("stage_run_finished", stage=sdef.name, ok=result.ok,
                      duration_ms=round((self._timer() - t0) * 1000, 3))
        return result

    @staticmethod
    def _serialize(sdef: StageDef, artifact: Any, state: WorkState) -> str:
        if sdef.fmt == "markdown":
            if not isinstance(artifact, str):
                raise TypeError(f"stage {sdef.name} must produce markdown text")
            return artifact
        if sdef.binds_draft and isinstance(artifact, dict) and "draft_sha256" not in artifact:
            artifact = {**artifact, "draft_sha256": state.draft_sha256}
        return to_json_text(artifact)

    # ---------------------------------------------------------- human actions
    def approve(self, work_id: str, *, by: str) -> WorkState:
        """Human release. The only path to ``released``."""
        item = self._item(work_id)
        state = item.load_state()
        if state.status is not Status.READY_FOR_RELEASE:
            raise EngineError(f"only work that is ready for release can be approved (status: {state.status.value})")
        approver = (by or "").strip()
        if not approver:
            raise EngineError("approval must name the person approving")
        now = self._now()
        record = {
            "work_id": work_id,
            "approved_by": approver,
            "approved_at": now,
            "draft_version": state.draft_version,
            "draft_sha256": state.draft_sha256,
            "release_submission": state.accepted.get("release"),
            "note": "The engine records the name given; it can't verify who ran the command.",
        }
        write_json_atomic(item.approval_path, record)
        state.approval = record
        state.status = Status.RELEASED
        self._save(item, state)
        self._events(item).append("approved", stage=state.stage, by=approver)
        return state

    def reject(self, work_id: str, *, by: str, reason: str) -> WorkState:
        item = self._item(work_id)
        state = item.load_state()
        if state.status in TERMINAL_STATUSES:
            raise EngineError(f"work item is already {state.status.value}")
        if not (by or "").strip() or not (reason or "").strip():
            raise EngineError("a rejection needs the person's name and a reason")
        state.status = Status.REJECTED
        self._save(item, state)
        self._events(item).append("rejected", stage=state.stage, by=by.strip(), reason=reason.strip())
        return state

    def resume(self, work_id: str, *, by: str, note: str = "", grant_revisions: int = 0) -> WorkState:
        """Continue a paused item at the stage where it paused. A note is kept as human input."""
        item = self._item(work_id)
        state = item.load_state()
        if state.status not in PAUSED_STATUSES:
            raise EngineError(f"only paused work can be resumed (status: {state.status.value})")
        if not (by or "").strip():
            raise EngineError("resuming must name the person")
        if not isinstance(grant_revisions, int) or grant_revisions < 0:
            raise EngineError("grant_revisions must be a non-negative integer")
        events = self._events(item)
        input_version = None
        if note.strip():
            input_version = item.put_human_input(note.strip() + "\n").version
        previous = state.pause.to_dict() if state.pause else None
        state.status = Status.IN_PROGRESS
        state.pause = None
        state.attempts[state.stage] = 0
        state.revision_allowance += grant_revisions
        self._save(item, state)
        events.append("resumed", stage=state.stage, by=by.strip(), grant_revisions=grant_revisions,
                      human_input_version=input_version, previous_pause=previous)
        return state

    # ---------------------------------------------------------------- metrics
    def usage(self, work_id: str) -> dict[str, Any]:
        """Per-item measurement: LLM calls, tokens, cost, latency, attempts, revisions."""
        item = self._item(work_id)
        state = item.load_state()
        summary = aggregate(read_records(item.metrics_path))
        gate_runs: dict[str, dict[str, int]] = {}
        stage_runs: dict[str, dict[str, Any]] = {}
        for e in self._events(item).read():
            if e["event"] in ("gate_passed", "gate_failed"):
                runs = gate_runs.setdefault(e["stage"], {"passed": 0, "failed": 0})
                runs["passed" if e["event"] == "gate_passed" else "failed"] += 1
            elif e["event"] in ("stage_run_finished", "producer_failed"):
                runs = stage_runs.setdefault(e["stage"], {"runs": 0, "wall_ms": 0.0})
                runs["runs"] += 1
                runs["wall_ms"] = round(runs["wall_ms"] + e.get("duration_ms", 0.0), 3)
        return {
            "work_id": work_id,
            "status": state.status.value,
            "stage": state.stage,
            "llm": summary,
            "revisions": {"used": state.revision_count, "allowed": state.revision_allowance},
            "attempts_current": dict(state.attempts),
            "gate_runs": gate_runs,
            "stage_runs": stage_runs,
            "draft_version": state.draft_version,
        }

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _result(ok: bool, state: WorkState, stage: str, message: str, version: int | None = None,
                failures: tuple = (), advisories: tuple = ()) -> SubmitResult:
        return SubmitResult(ok, state.work_id, stage, state.status.value, state.stage, message,
                            version, failures, advisories)
