"""ReplayLLM: deterministic, offline responses for tests (decision D9).

Two modes:

* **keyed**: responses are looked up by ``LLMRequest.key()``. Any change to a
  prompt, context or schema changes the key, so a stale fixture fails loudly
  instead of silently answering a different question.
* **scripted**: an ordered list of responses per role, for lifecycle tests where
  the exact prompt is not what is under test.

A request with no fixture raises ``ReplayMiss``; replay never improvises.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Mapping, Sequence

from ..core.files import read_json, write_json_atomic
from .llm import LLMError, LLMRequest, LLMResponse


class ReplayMiss(LLMError):
    pass


class ReplayLLM:
    adapter_name = "replay"

    def __init__(
        self,
        fixtures: Mapping[str, LLMResponse] | None = None,
        *,
        script: Mapping[str, Sequence[LLMResponse]] | None = None,
    ) -> None:
        if (fixtures is None) == (script is None):
            raise ValueError("give exactly one of fixtures (keyed mode) or script (scripted mode)")
        self._fixtures = dict(fixtures) if fixtures is not None else None
        self._script = {role: deque(items) for role, items in (script or {}).items()}
        self.requests: list[LLMRequest] = []

    @classmethod
    def from_dir(cls, folder: Path) -> "ReplayLLM":
        fixtures = {}
        for path in sorted(folder.glob("*.json")):
            record = read_json(path)
            fixtures[record["key"]] = LLMResponse.from_dict(record["response"])
        return cls(fixtures)

    def run(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self._fixtures is not None:
            key = request.key()
            if key not in self._fixtures:
                raise ReplayMiss(f"no replay fixture for role {request.role!r} (key {key[:12]}...)")
            return self._fixtures[key]
        queue = self._script.get(request.role)
        if not queue:
            raise ReplayMiss(f"scripted replay has no response left for role {request.role!r}")
        return queue.popleft()

    def remaining(self) -> dict[str, int]:
        return {role: len(q) for role, q in self._script.items()}


def save_fixture(folder: Path, request: LLMRequest, response: LLMResponse) -> Path:
    """Write a keyed fixture file (used when recording live calls)."""
    key = request.key()
    path = folder / f"{request.role}-{key[:16]}.json"
    write_json_atomic(path, {
        "key": key,
        "request": {"role": request.role, "model": request.model, "task": request.task},
        "response": response.to_dict(),
    })
    return path
