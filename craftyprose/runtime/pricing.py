"""Cost computation from a versioned pricing table (ADR-016).

Anything without a price is reported as unpriced. A cost total is marked
``complete`` only when every token class and tool use was priced.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .llm import Usage

DEFAULT_PRICING_PATH = Path(__file__).with_name("pricing.toml")
_PRICE_FIELDS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")


@dataclass(frozen=True)
class ModelPrice:
    input: float
    output: float
    cache_read: float
    cache_write_5m: float
    cache_write_1h: float


@dataclass(frozen=True)
class Cost:
    usd: float  # the priced portion
    complete: bool
    unpriced: tuple[str, ...] = ()


@dataclass(frozen=True)
class Pricing:
    version: str
    source: str
    models: Mapping[str, ModelPrice] = field(default_factory=dict)
    server_tools: Mapping[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "Pricing":
        with open(path or DEFAULT_PRICING_PATH, "rb") as fh:
            data = tomllib.load(fh)
        models = {}
        for name, prices in data.get("models", {}).items():
            missing = [f for f in _PRICE_FIELDS if f not in prices]
            if missing:
                raise ValueError(f"pricing for {name} is missing {missing}")
            models[name] = ModelPrice(**{f: float(prices[f]) for f in _PRICE_FIELDS})
        tools = {name: float(v) for name, v in data.get("server_tools", {}).items()}
        return cls(version=str(data["version"]), source=str(data.get("source", "")), models=models, server_tools=tools)

    def cost(self, model: str, usage: Usage, server_tool_uses: Mapping[str, int] | None = None) -> Cost:
        unpriced: list[str] = []
        usd = 0.0
        price = self.models.get(model)
        tokens_used = usage.total_input_tokens + usage.output_tokens
        if price is None:
            if tokens_used:
                unpriced.append(f"model:{model}")
        else:
            usd += (
                usage.input_tokens * price.input
                + usage.output_tokens * price.output
                + usage.cache_read_input_tokens * price.cache_read
                + usage.cache_creation_5m_input_tokens * price.cache_write_5m
                + usage.cache_creation_1h_input_tokens * price.cache_write_1h
            ) / 1_000_000
        for tool, count in sorted((server_tool_uses or {}).items()):
            if not count:
                continue
            if tool in self.server_tools:
                usd += count * self.server_tools[tool]
            else:
                unpriced.append(f"server_tool:{tool}")
        return Cost(usd=round(usd, 6), complete=not unpriced, unpriced=tuple(unpriced))
