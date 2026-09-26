"""Named, explainable gate checks.

A validator returns a ``ValidationResult``: a list of named checks, each passing
or failing with a detail message. A failed *blocking* check fails the gate. A
failed *advisory* check is recorded and passed downstream (judges must
acknowledge advisories in their jurisdiction), but it does not fail the gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""
    blocking: bool = True
    pattern_id: str | None = None
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Check":
        return cls(**data)


class ValidationResult:
    """The checks one validator ran. ``add`` returns ``self`` so calls chain."""

    def __init__(self, validator: str) -> None:
        self.validator = validator
        self.checks: list[Check] = []

    def add(
        self,
        name: str,
        passed: bool,
        detail: str = "",
        *,
        blocking: bool = True,
        pattern_id: str | None = None,
        location: str | None = None,
    ) -> "ValidationResult":
        self.checks.append(Check(name, bool(passed), detail, blocking, pattern_id, location))
        return self

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.blocking)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.blocking and not c.passed]

    @property
    def advisories(self) -> list[Check]:
        return [c for c in self.checks if not c.blocking and not c.passed]

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator": self.validator,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationResult":
        result = cls(data["validator"])
        result.checks = [Check.from_dict(c) for c in data["checks"]]
        return result

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        state = "PASS" if self.passed else "FAIL"
        return f"<ValidationResult {self.validator}: {state} ({len(self.checks)} checks)>"


Validator = Callable[[Any], ValidationResult]


class GateResult:
    """Every validator result for one submission."""

    def __init__(self, stage: str, version: int, results: Iterable[ValidationResult]) -> None:
        self.stage = stage
        self.version = version
        self.results = list(results)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[Check]:
        return [c for r in self.results for c in r.failures]

    @property
    def advisories(self) -> list[Check]:
        return [c for r in self.results for c in r.advisories]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "version": self.version,
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GateResult":
        return cls(data["stage"], data["version"], [ValidationResult.from_dict(r) for r in data["results"]])
