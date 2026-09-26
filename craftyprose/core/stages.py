"""Stage definitions: how a stage plugs into the core.

A ``StageDef`` gives a stage's artifact format, its deterministic validators,
its router (which picks the next step from the lifecycle's allowed routes) and,
for engine-run stages, a producer that makes the artifact through the metered
LLM. Content types, prompts and EIS plug in here in later milestones; the core
never branches on them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable

from .lifecycle import DRAFT_STAGES, STAGES, Route
from .validation import Check, GateResult, ValidationResult

if TYPE_CHECKING:  # pragma: no cover
    from ..runtime.metering import BoundLLM
    from .config import EngineConfig
    from .view import WorkView

FORMATS = ("json", "markdown")


@dataclass(frozen=True)
class GateContext:
    work_id: str
    stage: str
    artifact: Any
    view: "WorkView"
    config: "EngineConfig"


@dataclass(frozen=True)
class RouteContext:
    work_id: str
    stage: str
    artifact: Any
    gate: GateResult
    view: "WorkView"
    config: "EngineConfig"


@dataclass(frozen=True)
class ProduceContext:
    work_id: str
    stage: str
    view: "WorkView"
    llm: "BoundLLM"
    feedback: tuple[Check, ...]  # failed checks from this stage's last gate run
    config: "EngineConfig"


Validator = Callable[[GateContext], ValidationResult]
Router = Callable[[RouteContext], Route]
Producer = Callable[[ProduceContext], Any]


@dataclass(frozen=True)
class StageDef:
    name: str
    fmt: str
    router: Router
    validators: tuple[Validator, ...] = ()
    producer: Producer | None = None
    draft_field: str | None = None  # revise: the JSON field holding the revised draft
    binds_draft: bool = False  # the artifact must name the draft it was made from

    def __post_init__(self) -> None:
        if self.name not in STAGES:
            raise ValueError(f"unknown stage {self.name!r}")
        if self.fmt not in FORMATS:
            raise ValueError(f"stage {self.name}: format must be one of {FORMATS}")
        if self.name == "draft" and self.fmt != "markdown":
            raise ValueError("the draft stage produces markdown")
        if self.name == "revise" and (self.fmt != "json" or not self.draft_field):
            raise ValueError("the revise stage produces JSON with a draft_field")
        if self.name not in DRAFT_STAGES and self.draft_field:
            raise ValueError(f"stage {self.name} does not produce drafts")
        if self.binds_draft and self.fmt != "json":
            raise ValueError("draft binding needs a JSON artifact")


class StageRegistry:
    """Exactly one definition for each of the seven lifecycle stages."""

    def __init__(self, stages: Iterable[StageDef]) -> None:
        by_name: dict[str, StageDef] = {}
        for s in stages:
            if s.name in by_name:
                raise ValueError(f"stage {s.name!r} defined twice")
            by_name[s.name] = s
        missing = [s for s in STAGES if s not in by_name]
        if missing:
            raise ValueError(f"stage registry is missing {missing}")
        self._stages = by_name

    def __getitem__(self, name: str) -> StageDef:
        return self._stages[name]

    def __contains__(self, name: str) -> bool:
        return name in self._stages
