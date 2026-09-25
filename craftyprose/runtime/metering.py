"""Metering: one record per LLM call, whatever the adapter (ADR-016).

``MeteredLLM`` wraps an adapter. The engine binds it to a work item and stage
(``bind``) and hands the bound meter to stage producers, so a producer can't
make an unmetered call through the engine.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Iterable

from ..core.files import append_line
from .llm import LLM, LLMRequest, LLMResponse
from .pricing import Pricing


@dataclass(frozen=True)
class CallRecord:
    seq: int
    work_id: str
    stage: str
    role: str
    adapter: str
    requested_model: str
    model: str
    request_key: str
    started_at: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_5m_input_tokens: int
    cache_creation_1h_input_tokens: int
    client_tool_calls: dict[str, int]
    server_tool_uses: dict[str, int]
    stop_reason: str
    cost_usd: float
    cost_complete: bool
    unpriced: list[str]
    pricing_version: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_records(path: Path) -> list[CallRecord]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return [CallRecord(**json.loads(line)) for line in fh if line.strip()]


class MeteredLLM:
    def __init__(
        self,
        inner: LLM,
        pricing: Pricing,
        *,
        model_for: Callable[[str], str],
        now: Callable[[], str],
        timer: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.inner = inner
        self.pricing = pricing
        self.model_for = model_for
        self.now = now
        self.timer = timer

    def bind(self, metrics_path: Path, work_id: str, stage: str) -> "BoundLLM":
        return BoundLLM(self, metrics_path, work_id, stage)


class BoundLLM:
    """A meter bound to one work item and stage. This is what producers receive."""

    def __init__(self, meter: MeteredLLM, metrics_path: Path, work_id: str, stage: str) -> None:
        self._meter = meter
        self._path = metrics_path
        self.work_id = work_id
        self.stage = stage

    def run(self, request: LLMRequest) -> LLMResponse:
        m = self._meter
        if request.model is None:
            request = replace(request, model=m.model_for(request.role))
        started_at = m.now()
        t0 = m.timer()
        try:
            response = m.inner.run(request)
        except Exception as exc:
            self._write(request, None, started_at, (m.timer() - t0) * 1000, f"{type(exc).__name__}: {exc}")
            raise
        self._write(request, response, started_at, (m.timer() - t0) * 1000, None)
        return response

    def _write(self, request: LLMRequest, response: LLMResponse | None, started_at: str,
               latency_ms: float, error: str | None) -> None:
        m = self._meter
        usage = response.usage if response else None
        client = Counter(t.name for t in (response.tool_uses if response else ()) if not t.server)
        server = Counter(t.name for t in (response.tool_uses if response else ()) if t.server)
        model = response.model if response else (request.model or "")
        if response:
            cost = m.pricing.cost(model, usage, server)
            cost_usd, complete, unpriced = cost.usd, cost.complete, list(cost.unpriced)
        else:
            cost_usd, complete, unpriced = 0.0, True, []
        record = CallRecord(
            seq=len(read_records(self._path)) + 1,
            work_id=self.work_id,
            stage=self.stage,
            role=request.role,
            adapter=getattr(m.inner, "adapter_name", type(m.inner).__name__),
            requested_model=request.model or "",
            model=model,
            request_key=request.key(),
            started_at=started_at,
            latency_ms=round(latency_ms, 3),
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            cache_read_input_tokens=usage.cache_read_input_tokens if usage else 0,
            cache_creation_5m_input_tokens=usage.cache_creation_5m_input_tokens if usage else 0,
            cache_creation_1h_input_tokens=usage.cache_creation_1h_input_tokens if usage else 0,
            client_tool_calls=dict(client),
            server_tool_uses=dict(server),
            stop_reason=response.stop_reason if response else "error",
            cost_usd=cost_usd,
            cost_complete=complete,
            unpriced=unpriced,
            pricing_version=m.pricing.version,
            error=error,
        )
        append_line(self._path, json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True))


_TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
                 "cache_creation_5m_input_tokens", "cache_creation_1h_input_tokens")


def _bucket() -> dict[str, Any]:
    return {"calls": 0, "errors": 0, "latency_ms": 0.0, "cost_usd": 0.0, **{f: 0 for f in _TOKEN_FIELDS}}


def aggregate(records: Iterable[CallRecord]) -> dict[str, Any]:
    """Totals overall and by role, stage and model."""
    total = _bucket()
    groups: dict[str, dict[str, dict[str, Any]]] = {"by_role": {}, "by_stage": {}, "by_model": {}}
    client: Counter = Counter()
    server: Counter = Counter()
    unpriced: set[str] = set()
    complete = True
    for r in records:
        for bucket in (total,
                       groups["by_role"].setdefault(r.role, _bucket()),
                       groups["by_stage"].setdefault(r.stage, _bucket()),
                       groups["by_model"].setdefault(r.model or "(none)", _bucket())):
            bucket["calls"] += 1
            bucket["errors"] += 1 if r.error else 0
            bucket["latency_ms"] = round(bucket["latency_ms"] + r.latency_ms, 3)
            bucket["cost_usd"] = round(bucket["cost_usd"] + r.cost_usd, 6)
            for f in _TOKEN_FIELDS:
                bucket[f] += getattr(r, f)
        client.update(r.client_tool_calls)
        server.update(r.server_tool_uses)
        unpriced.update(r.unpriced)
        complete = complete and r.cost_complete
    return {
        **total,
        **groups,
        "client_tool_calls": dict(client),
        "server_tool_uses": dict(server),
        "cost_complete": complete,
        "unpriced": sorted(unpriced),
    }
