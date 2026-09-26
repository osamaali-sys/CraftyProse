"""Shared test scaffolding: a fixed clock, stub stages driven by ReplayLLM, and an
engine test case. Stub stages stand in for the real stages built in M2 to M7;
they exercise the core, not content logic."""
from __future__ import annotations

import datetime as dt
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from craftyprose.core.config import EngineConfig
from craftyprose.core.engine import Engine
from craftyprose.core.findings import Finding, verdict_of
from craftyprose.core.lifecycle import Route
from craftyprose.core.stages import StageDef, StageRegistry
from craftyprose.core.validation import ValidationResult
from craftyprose.runtime.llm import LLMRequest, LLMResponse, ToolUse, Usage
from craftyprose.runtime.replay import ReplayLLM


class FixedClock:
    def __init__(self, start: datetime = datetime(2026, 9, 25, 9, 0, tzinfo=timezone.utc),
                 step: timedelta = timedelta(seconds=1)) -> None:
        self.now = start
        self.step = step

    def __call__(self) -> datetime:
        value = self.now
        self.now += self.step
        return value


class StepTimer:
    """Each reading advances 0.25 s, so latencies are deterministic."""

    def __init__(self, step: float = 0.25) -> None:
        self.t = 0.0
        self.step = step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def reply(data: dict | None = None, text: str | None = None, *, model: str = "claude-opus-5",
          tools: tuple[ToolUse, ...] = (), **usage: int) -> LLMResponse:
    base = {"input_tokens": 1000, "output_tokens": 200}
    base.update(usage)
    return LLMResponse(model=model, text=text, data=data, usage=Usage(**base), tool_uses=tools)


def producer_for(role: str):
    def produce(ctx):
        response = ctx.llm.run(LLMRequest(role=role, system=f"stub {role}", task=f"produce {ctx.stage}"))
        return response.text if response.text is not None else dict(response.data)
    produce.__name__ = f"produce_{role}"
    return produce


def require_keys(*keys: str):
    def validate(ctx) -> ValidationResult:
        result = ValidationResult("require_keys")
        for key in keys:
            result.add(f"has_{key}", key in ctx.artifact, f"missing '{key}'")
        return result
    return validate


def review_router(ctx) -> Route:
    findings = [Finding.from_dict(f, source="judge:stub") for f in ctx.artifact.get("findings", [])]
    if any(f.requires_new_evidence for f in findings):
        return Route.advance("research", "a finding needs new evidence")
    if verdict_of(findings) == "fail":
        return Route.advance("revise", "blocking findings")
    return Route.advance("release", "review passed")


def plan_router(ctx) -> Route:
    return Route.advance("revise" if ctx.view.state.has_draft else "draft")


def advance_to(stage: str):
    def route(_ctx) -> Route:
        return Route.advance(stage)
    route.__name__ = f"advance_to_{stage}"
    return route


def ready(_ctx) -> Route:
    return Route.ready_for_release("all gates passed")


def make_registry(**overrides: StageDef) -> StageRegistry:
    stages = {
        "intake": StageDef("intake", "json", router=advance_to("research"), producer=producer_for("planner"),
                           validators=(require_keys("topic"),)),
        "research": StageDef("research", "json", router=advance_to("plan"), producer=producer_for("researcher")),
        "plan": StageDef("plan", "json", router=plan_router, producer=producer_for("strategist")),
        "draft": StageDef("draft", "markdown", router=advance_to("review"), producer=producer_for("writer")),
        "review": StageDef("review", "json", router=review_router, producer=producer_for("judge"), binds_draft=True),
        "revise": StageDef("revise", "json", router=advance_to("review"), producer=producer_for("writer"),
                           draft_field="draft"),
        "release": StageDef("release", "json", router=ready, producer=producer_for("release")),
    }
    stages.update(overrides)
    return StageRegistry(stages.values())


MAJOR_FINDING = {
    "pattern_id": "ED-GENERIC-ANGLE",
    "severity": "major",
    "problem": "The angle could appear in any competitor's post.",
    "required_correction": "Tie the angle to the brand's verified claims.",
    "location": {"section": "Intro", "quote": "In today's world"},
}


def happy_script(**extra: list[LLMResponse]) -> dict[str, list[LLMResponse]]:
    script: dict[str, list[LLMResponse]] = {
        "planner": [reply({"topic": "onboarding"})],
        "researcher": [reply({"claims": []})],
        "strategist": [reply({"sections": ["one"]})],
        "writer": [reply(text="# Title\n\nFirst draft.\n")],
        "judge": [reply({"findings": []})],
        "release": [reply({"package": "ok"})],
    }
    for role, responses in extra.items():
        script[role] = responses
    return script


class EngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.clock = FixedClock()
        self.timer = StepTimer()

    @property
    def workspace(self) -> Path:
        return self.tmp / "workspace"

    def make_engine(self, script: dict[str, list[LLMResponse]] | None = None, *,
                    registry: StageRegistry | None = None, config: EngineConfig | None = None) -> Engine:
        return Engine(self.workspace, registry=registry or make_registry(),
                      llm=ReplayLLM(script=script if script is not None else happy_script()),
                      config=config, clock=self.clock, timer=self.timer)

    def new_item(self, engine: Engine) -> str:
        return engine.new("Write a post about onboarding.", brand_id="northwind", content_type="blog_article").work_id

    def run_until(self, engine: Engine, work_id: str, stage: str, limit: int = 20) -> None:
        for _ in range(limit):
            state = engine.status(work_id)
            if state.stage == stage or state.status.value != "in_progress":
                return
            result = engine.run_stage(work_id)
            if not result.ok:
                self.fail(f"stage run failed: {result.message}")
        self.fail(f"did not reach {stage}")

    def item_dir(self, work_id: str) -> Path:
        return self.workspace / "work" / work_id

    def events_named(self, engine: Engine, work_id: str, name: str) -> list[dict[str, Any]]:
        return [e for e in engine.events(work_id) if e["event"] == name]


# ---------------------------------------------------------------- EIS helpers
REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_WORKSPACE = REPO_ROOT / "examples" / "workspace"
AS_OF = dt.date(2026, 9, 26)


class BrandTestCase(unittest.TestCase):
    """Copies the fictional example brand into a temp workspace so a test can change one file."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-eis-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.workspace = self.tmp / "workspace"
        shutil.copytree(EXAMPLE_WORKSPACE, self.workspace)
        self.brand_root = self.workspace / "brands" / "fernhill"

    def edit(self, name: str, old: str, new: str) -> None:
        path = self.brand_root / name
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise AssertionError(f"{old!r} not in {name}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def append(self, name: str, text: str) -> None:
        path = self.brand_root / name
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def write(self, name: str, text: str) -> None:
        path = self.brand_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def load(self):
        from craftyprose.content_types.loader import Catalog
        from craftyprose.eis.workspace import load_brand
        return load_brand(self.workspace, "fernhill", content_types=Catalog().ids())
