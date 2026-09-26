"""The LLM adapter contract shared by every runtime (ADR-012)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Protocol

from ..core.files import canonical_json, sha256_text


class LLMError(RuntimeError):
    """A model call failed (transport, refusal, missing replay fixture, ...)."""


@dataclass(frozen=True)
class Block:
    """One piece of context. Cacheable blocks form the stable prompt prefix."""

    name: str
    text: str
    cacheable: bool = False


@dataclass(frozen=True)
class LLMRequest:
    role: str
    system: str
    task: str
    context: tuple[Block, ...] = ()
    schema: Mapping[str, Any] | None = None  # JSON Schema for structured output
    tools: tuple[str, ...] = ()  # tool names the role may use, e.g. "web_search"
    model: str | None = None  # filled from configuration when unset

    def key(self) -> str:
        """Content hash identifying this request; replay fixtures are keyed by it."""
        return sha256_text(canonical_json({
            "role": self.role,
            "system": self.system,
            "task": self.task,
            "context": [asdict(b) for b in self.context],
            "schema": self.schema,
            "tools": list(self.tools),
            "model": self.model,
        }))


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0  # uncached input only
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_5m_input_tokens: int = 0
    cache_creation_1h_input_tokens: int = 0

    @property
    def total_input_tokens(self) -> int:
        return (self.input_tokens + self.cache_read_input_tokens
                + self.cache_creation_5m_input_tokens + self.cache_creation_1h_input_tokens)

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class ToolUse:
    name: str
    server: bool  # True for provider-run tools such as web search/fetch


@dataclass(frozen=True)
class LLMResponse:
    model: str
    text: str | None = None
    data: Mapping[str, Any] | None = None  # parsed structured output
    usage: Usage = field(default_factory=Usage)
    tool_uses: tuple[ToolUse, ...] = ()
    stop_reason: str = "end_turn"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "text": self.text,
            "data": dict(self.data) if self.data is not None else None,
            "usage": self.usage.to_dict(),
            "tool_uses": [asdict(t) for t in self.tool_uses],
            "stop_reason": self.stop_reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LLMResponse":
        return cls(
            model=data["model"],
            text=data.get("text"),
            data=data.get("data"),
            usage=Usage(**data.get("usage", {})),
            tool_uses=tuple(ToolUse(**t) for t in data.get("tool_uses", [])),
            stop_reason=data.get("stop_reason", "end_turn"),
        )


class LLM(Protocol):
    adapter_name: str

    def run(self, request: LLMRequest) -> LLMResponse: ...
