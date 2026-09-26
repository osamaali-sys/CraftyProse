"""Loop budgets (architecture §5.4). Every loop ends in escalation, never forever."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping


@dataclass(frozen=True)
class Budgets:
    max_attempts_per_stage: int = 3  # gate failures of one stage before a human is needed
    max_revisions: int = 3  # review -> revise/research loops per work item
    max_judge_reruns: int = 2  # re-runs of a judge whose output failed validation

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"budget {f.name} must be a positive integer, got {value!r}")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Budgets":
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"unknown budget setting(s) {unknown}")
        return cls(**dict(data))
