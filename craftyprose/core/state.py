"""Persistent state of one work item (``state.json``)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .lifecycle import Status

STATE_SCHEMA = 1


@dataclass
class Pause:
    status: Status
    stage: str
    reason: str
    details: dict[str, Any]
    at: str

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "stage": self.stage, "reason": self.reason,
                "details": self.details, "at": self.at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pause":
        return cls(Status(data["status"]), data["stage"], data["reason"], data.get("details", {}), data["at"])


@dataclass
class WorkState:
    work_id: str
    brand_id: str
    content_type: str
    status: Status
    stage: str
    created: str
    updated: str
    revision_allowance: int
    revision_count: int = 0
    attempts: dict[str, int] = field(default_factory=dict)
    # stage -> {"version": n, "sha256": ..., "draft_sha256": ...} of the accepted submission
    accepted: dict[str, dict[str, Any]] = field(default_factory=dict)
    # stage -> {"version": n, "passed": bool} of the most recent gate run
    last_gate: dict[str, dict[str, Any]] = field(default_factory=dict)
    draft_version: int = 0
    draft_sha256: str | None = None
    pause: Pause | None = None
    approval: dict[str, Any] | None = None

    @property
    def has_draft(self) -> bool:
        return self.draft_version > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": STATE_SCHEMA,
            "work_id": self.work_id,
            "brand_id": self.brand_id,
            "content_type": self.content_type,
            "status": self.status.value,
            "stage": self.stage,
            "created": self.created,
            "updated": self.updated,
            "revision_allowance": self.revision_allowance,
            "revision_count": self.revision_count,
            "attempts": self.attempts,
            "accepted": self.accepted,
            "last_gate": self.last_gate,
            "draft_version": self.draft_version,
            "draft_sha256": self.draft_sha256,
            "pause": self.pause.to_dict() if self.pause else None,
            "approval": self.approval,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkState":
        if data.get("schema") != STATE_SCHEMA:
            raise ValueError(f"unsupported state schema {data.get('schema')!r}")
        return cls(
            work_id=data["work_id"],
            brand_id=data["brand_id"],
            content_type=data["content_type"],
            status=Status(data["status"]),
            stage=data["stage"],
            created=data["created"],
            updated=data["updated"],
            revision_allowance=data["revision_allowance"],
            revision_count=data["revision_count"],
            attempts=dict(data["attempts"]),
            accepted=dict(data["accepted"]),
            last_gate=dict(data["last_gate"]),
            draft_version=data["draft_version"],
            draft_sha256=data["draft_sha256"],
            pause=Pause.from_dict(data["pause"]) if data["pause"] else None,
            approval=data["approval"],
        )
