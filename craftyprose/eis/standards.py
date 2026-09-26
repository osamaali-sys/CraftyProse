"""The failure-pattern library and editorial principles (architecture §3.3)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..core.findings import PATTERN_ID_RE, SEVERITIES
from ..core.schema import SchemaError, load_toml

STANDARDS_DIR = Path(__file__).with_name("standards")
DETECTORS = ("deterministic", "judge")

# Which judge owns each pattern prefix (ADR-007). ST patterns are deterministic only.
JUDGE_FOR_PREFIX = {"EV": "evidence", "RK": "evidence", "ED": "editorial", "DS": "editorial",
                    "HW": "writing", "VO": "writing"}


class StandardsError(SchemaError):
    pass


@dataclass(frozen=True)
class Pattern:
    id: str
    name: str
    severity: str
    detectors: tuple[str, ...]
    definition: str
    remediation: str
    example: str = ""

    @property
    def prefix(self) -> str:
        return self.id.split("-", 1)[0]

    @property
    def judge(self) -> str | None:
        return JUDGE_FOR_PREFIX.get(self.prefix) if "judge" in self.detectors else None


@dataclass(frozen=True)
class Library:
    version: str
    patterns: dict[str, Pattern]

    def get(self, pattern_id: str) -> Pattern:
        if pattern_id not in self.patterns:
            raise StandardsError(f"unknown failure pattern {pattern_id!r}")
        return self.patterns[pattern_id]

    def for_judge(self, judge: str) -> tuple[Pattern, ...]:
        return tuple(p for p in self.patterns.values() if p.judge == judge)


def load_library(path: Path | None = None) -> Library:
    path = path or STANDARDS_DIR / "failure_patterns.toml"
    t = load_toml(path)
    version = t.str("version")
    patterns: dict[str, Pattern] = {}
    for p in t.tables("patterns"):
        pattern = Pattern(
            id=p.str("id"), name=p.str("name"), severity=p.str("severity", choices=SEVERITIES),
            detectors=p.str_list("detectors", required=True, nonempty=True, choices=DETECTORS),
            definition=p.str("definition"), remediation=p.str("remediation"),
            example=p.str("example", required=False, nonempty=False),
        )
        p.finish()
        if not PATTERN_ID_RE.match(pattern.id):
            raise StandardsError(f"{p.where}: id {pattern.id!r} doesn't use a known prefix")
        if pattern.id in patterns:
            raise StandardsError(f"{p.where}: duplicate pattern id {pattern.id!r}")
        if pattern.prefix == "ST" and "judge" in pattern.detectors:
            raise StandardsError(f"{p.where}: ST patterns are deterministic only")
        patterns[pattern.id] = pattern
    t.finish()
    return Library(version, patterns)


@lru_cache(maxsize=1)
def library() -> Library:
    """The bundled library, loaded once."""
    return load_library()


def principles() -> str:
    return (STANDARDS_DIR / "principles.md").read_text(encoding="utf-8")
