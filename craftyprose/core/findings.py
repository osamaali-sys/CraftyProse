"""Findings: located, pattern-coded defects that drive revision.

Three rules close holes found in the predecessor (ER §8.2):

* Verdicts are computed by the engine from severities (``verdict_of``). A judge
  that says "pass" while reporting a major finding does not pass.
* Resolution is never declared. Judge output may not carry ``resolved``,
  ``verdict``, ``status`` or ``source``; those fields are engine-owned, and a
  finding carrying them is rejected.
* Every finding has a fingerprint (pattern + section + normalized quote), so the
  engine can tell across rounds whether a defect was resolved, persisted or is new.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

SEVERITIES = ("critical", "major", "minor")
BLOCKING_SEVERITIES = ("critical", "major")

# Jurisdiction prefixes (architecture §3.3).
PATTERN_CATEGORIES = ("EV", "ED", "DS", "HW", "VO", "ST", "RK")
PATTERN_ID_RE = re.compile(r"^(%s)-[A-Z0-9]+(?:-[A-Z0-9]+)*$" % "|".join(PATTERN_CATEGORIES))

ENGINE_OWNED_KEYS = frozenset({"resolved", "verdict", "status", "source"})
_FINDING_KEYS = frozenset(
    {"pattern_id", "severity", "problem", "required_correction", "location", "evidence", "requires_new_evidence"}
)
_LOCATION_KEYS = frozenset({"section", "quote"})
_QUOTE_CHARS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


class FindingError(ValueError):
    """A finding is malformed or claims an engine-owned field."""


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.translate(_QUOTE_CHARS)).strip().lower()


@dataclass(frozen=True)
class Location:
    section: str | None = None
    quote: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"section": self.section, "quote": self.quote}


@dataclass(frozen=True)
class Finding:
    pattern_id: str
    severity: str
    source: str
    problem: str
    required_correction: str
    location: Location = field(default_factory=Location)
    evidence: str = ""
    requires_new_evidence: bool = False

    def __post_init__(self) -> None:
        if not PATTERN_ID_RE.match(self.pattern_id or ""):
            raise FindingError(
                f"pattern_id {self.pattern_id!r} must look like '<{'|'.join(PATTERN_CATEGORIES)}>-NAME'"
            )
        if self.severity not in SEVERITIES:
            raise FindingError(f"severity {self.severity!r} must be one of {SEVERITIES}")
        if not (self.source or "").strip():
            raise FindingError("source must be set by the engine")
        if not (self.problem or "").strip():
            raise FindingError("problem must be non-empty")
        if not (self.required_correction or "").strip():
            raise FindingError("required_correction must be non-empty")

    @property
    def blocking(self) -> bool:
        return self.severity in BLOCKING_SEVERITIES

    @property
    def fingerprint(self) -> str:
        key = "|".join(
            [self.pattern_id, normalize_text(self.location.section), normalize_text(self.location.quote)]
        )
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "severity": self.severity,
            "source": self.source,
            "problem": self.problem,
            "required_correction": self.required_correction,
            "location": self.location.to_dict(),
            "evidence": self.evidence,
            "requires_new_evidence": self.requires_new_evidence,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Any, *, source: str) -> "Finding":
        """Parse untrusted finding data (e.g. judge output). ``source`` comes from the engine."""
        if not isinstance(data, dict):
            raise FindingError("finding must be an object")
        claimed = sorted(ENGINE_OWNED_KEYS & data.keys())
        if claimed:
            raise FindingError(f"finding sets engine-owned field(s) {claimed}; resolution and verdicts are computed")
        unknown = sorted(data.keys() - _FINDING_KEYS)
        if unknown:
            raise FindingError(f"finding has unknown field(s) {unknown}")
        loc = data.get("location") or {}
        if not isinstance(loc, dict):
            raise FindingError("location must be an object")
        bad_loc = sorted(loc.keys() - _LOCATION_KEYS)
        if bad_loc:
            raise FindingError(f"location has unknown field(s) {bad_loc}")
        requires_new = data.get("requires_new_evidence", False)
        if not isinstance(requires_new, bool):
            raise FindingError("requires_new_evidence must be a boolean")
        return cls(
            pattern_id=data.get("pattern_id", ""),
            severity=data.get("severity", ""),
            source=source,
            problem=data.get("problem", ""),
            required_correction=data.get("required_correction", ""),
            location=Location(section=loc.get("section"), quote=loc.get("quote")),
            evidence=data.get("evidence", "") or "",
            requires_new_evidence=requires_new,
        )


def verdict_of(findings: Iterable[Finding]) -> str:
    """Engine-computed verdict: any critical or major finding fails."""
    return "fail" if any(f.blocking for f in findings) else "pass"
