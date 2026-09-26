"""Engine configuration: ``<workspace>/craftyprose.toml``.

    [budgets]
    max_attempts_per_stage = 3
    max_revisions = 3
    max_judge_reruns = 2

    [models]
    default = "claude-opus-5"
    # per-role overrides, e.g. judge_writing = "claude-opus-5"

    [pricing]
    file = "pricing.toml"   # optional; relative to this file

Unknown sections or keys are errors, so a typo can't silently fall back to a default.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .budgets import Budgets

DEFAULT_MODEL = "claude-opus-5"
_SECTIONS = {"budgets", "models", "pricing"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class EngineConfig:
    budgets: Budgets = field(default_factory=Budgets)
    models: Mapping[str, str] = field(default_factory=lambda: {"default": DEFAULT_MODEL})
    pricing_path: Path | None = None

    def model_for(self, role: str) -> str:
        return self.models.get(role) or self.models.get("default") or DEFAULT_MODEL

    @classmethod
    def load(cls, path: Path) -> "EngineConfig":
        if not path.exists():
            return cls()
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        unknown = sorted(set(data) - _SECTIONS)
        if unknown:
            raise ConfigError(f"{path}: unknown section(s) {unknown}")
        try:
            budgets = Budgets.from_mapping(data.get("budgets", {}))
        except ValueError as exc:
            raise ConfigError(f"{path}: {exc}") from exc
        models = {"default": DEFAULT_MODEL, **data.get("models", {})}
        bad = sorted(k for k, v in models.items() if not isinstance(v, str) or not v)
        if bad:
            raise ConfigError(f"{path}: model names must be non-empty strings: {bad}")
        pricing = data.get("pricing", {})
        unknown_pricing = sorted(set(pricing) - {"file"})
        if unknown_pricing:
            raise ConfigError(f"{path}: unknown pricing key(s) {unknown_pricing}")
        pricing_path = (path.parent / pricing["file"]) if "file" in pricing else None
        return cls(budgets=budgets, models=models, pricing_path=pricing_path)
