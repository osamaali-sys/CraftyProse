"""Append-only event log (``events.jsonl``): what happened, when, and why."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .files import append_line


class EventLog:
    def __init__(self, path: Path, now: Callable[[], str]) -> None:
        self.path = path
        self._now = now

    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        # The sequence number comes from the file, so every handle on the same
        # log agrees on it.
        entry = {"seq": len(self.read()) + 1, "ts": self._now(), "event": event, **fields}
        append_line(self.path, json.dumps(entry, ensure_ascii=False, sort_keys=True))
        return entry

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
