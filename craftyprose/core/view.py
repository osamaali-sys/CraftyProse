"""Read-only access to a work item for validators, routers and producers.

Stages never get write access to state or artifacts. The engine is the only
writer, which is what lets gates trust what they read.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .files import read_json, read_text
from .state import WorkState
from .validation import Check, GateResult
from .workitem import WorkItem

if TYPE_CHECKING:  # pragma: no cover
    from .stages import StageRegistry


class WorkView:
    def __init__(self, item: WorkItem, state: WorkState, registry: "StageRegistry | None") -> None:
        self._item = item
        self._registry = registry
        # A private copy, so nothing a stage does to it reaches the real state.
        self.state = WorkState.from_dict(state.to_dict())

    @property
    def work_id(self) -> str:
        return self.state.work_id

    def request_text(self) -> str:
        return read_text(self._item.request_path)

    def accepted_meta(self, stage: str) -> dict[str, Any] | None:
        meta = self.state.accepted.get(stage)
        return dict(meta) if meta else None

    def accepted(self, stage: str) -> Any:
        """The parsed artifact accepted for ``stage``, or None."""
        meta = self.state.accepted.get(stage)
        if not meta:
            return None
        if self._registry is None:
            raise RuntimeError("reading artifacts needs a stage registry")
        fmt = self._registry[stage].fmt
        text = self._item.read_submission(stage, fmt, meta["version"])
        return json.loads(text) if fmt == "json" else text

    def current_draft(self) -> str | None:
        if not self.state.has_draft:
            return None
        return self._item.read_draft(self.state.draft_version)

    def human_inputs(self) -> list[str]:
        return self._item.human_inputs()

    def last_failures(self, stage: str) -> tuple[Check, ...]:
        """Failed blocking checks from this stage's most recent gate run, if it failed."""
        last = self.state.last_gate.get(stage)
        if not last or last["passed"]:
            return ()
        record = read_json(self._item.validation_path(stage, last["version"]))
        return tuple(GateResult.from_dict(record["gate"]).failures)
