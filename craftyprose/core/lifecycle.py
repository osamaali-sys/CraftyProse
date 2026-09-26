"""The approved seven-stage lifecycle (architecture §5, ADR-006).

Stages and their allowed transitions are fixed here. A stage's router chooses a
route, and the engine refuses any route this module doesn't allow, so no stage
implementation can invent a path around a gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

STAGES = ("intake", "research", "plan", "draft", "review", "revise", "release")

# Allowed stage-to-stage moves. Research can be re-entered from review
# ("research more"), and plan leads back to revise when a draft already exists.
EDGES: dict[str, frozenset[str]] = {
    "intake": frozenset({"research"}),
    "research": frozenset({"plan"}),
    "plan": frozenset({"draft", "revise", "research"}),
    "draft": frozenset({"review"}),
    "review": frozenset({"revise", "research", "release"}),
    "revise": frozenset({"review"}),
    "release": frozenset(),
}

# Moves that start a revision loop and count against the revision budget.
REVISION_ENTRIES = frozenset({("review", "revise"), ("review", "research")})

# Review and release artifacts are produced by the engine itself. They can't be
# submitted from outside, which keeps reviews independent of authors (ADR-001).
ENGINE_ONLY_STAGES = frozenset({"review", "release"})

# Stages whose accepted artifact becomes the next draft version.
DRAFT_STAGES = frozenset({"draft", "revise"})


class Status(str, Enum):
    IN_PROGRESS = "in_progress"
    NEEDS_INPUT = "needs_input"
    BLOCKED = "blocked"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    REJECTED = "rejected"
    READY_FOR_RELEASE = "ready_for_release"
    RELEASED = "released"


PAUSED_STATUSES = frozenset({Status.NEEDS_INPUT, Status.BLOCKED, Status.REQUIRES_HUMAN_REVIEW})
TERMINAL_STATUSES = frozenset({Status.REJECTED, Status.RELEASED})


class RouteError(ValueError):
    """A router asked for a transition the lifecycle doesn't allow."""


@dataclass(frozen=True)
class Route:
    action: str  # advance | pause | ready_for_release | reject
    to_stage: str | None = None
    status: Status | None = None
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def advance(cls, to_stage: str, reason: str = "") -> "Route":
        return cls("advance", to_stage=to_stage, reason=reason)

    @classmethod
    def pause(cls, status: Status, reason: str, details: dict[str, Any] | None = None) -> "Route":
        return cls("pause", status=status, reason=reason, details=details or {})

    @classmethod
    def ready_for_release(cls, reason: str = "") -> "Route":
        return cls("ready_for_release", reason=reason)

    @classmethod
    def reject(cls, reason: str) -> "Route":
        return cls("reject", reason=reason)


def check_route(from_stage: str, route: Route, *, has_draft: bool) -> None:
    """Raise ``RouteError`` unless ``route`` is allowed from ``from_stage``."""
    if from_stage not in EDGES:
        raise RouteError(f"unknown stage {from_stage!r}")
    if route.action == "advance":
        if route.to_stage not in EDGES[from_stage]:
            raise RouteError(f"{from_stage} -> {route.to_stage} is not an allowed transition")
        if route.to_stage == "draft" and has_draft:
            raise RouteError("a draft already exists; changes go through revise")
        if route.to_stage == "revise" and not has_draft:
            raise RouteError("there is no draft to revise")
    elif route.action == "pause":
        if route.status not in PAUSED_STATUSES:
            raise RouteError(f"pause status must be one of {[s.value for s in PAUSED_STATUSES]}")
        if not route.reason:
            raise RouteError("a pause needs a reason")
    elif route.action == "ready_for_release":
        if from_stage != "release":
            raise RouteError("only the release stage can mark work ready for release")
    elif route.action == "reject":
        if from_stage != "review":
            raise RouteError("automatic rejection is only decided at review")
        if not route.reason:
            raise RouteError("a rejection needs a reason")
    else:
        raise RouteError(f"unknown route action {route.action!r}")
