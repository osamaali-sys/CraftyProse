import shutil
import tempfile
import unittest
from pathlib import Path

from craftyprose.runtime.llm import LLMError, LLMRequest, LLMResponse, ToolUse, Usage
from craftyprose.runtime.metering import MeteredLLM, aggregate, read_records
from craftyprose.runtime.pricing import ModelPrice, Pricing
from craftyprose.runtime.replay import ReplayLLM
from tests.helpers import StepTimer

OPUS = ModelPrice(input=5.0, output=25.0, cache_read=0.5, cache_write_5m=6.25, cache_write_1h=10.0)
PRICING = Pricing(version="test", source="test", models={"claude-opus-5": OPUS})


class PricingTest(unittest.TestCase):
    def test_token_classes_are_priced_separately(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, cache_read_input_tokens=1_000_000,
                      cache_creation_5m_input_tokens=1_000_000, cache_creation_1h_input_tokens=1_000_000)
        cost = PRICING.cost("claude-opus-5", usage)
        self.assertAlmostEqual(cost.usd, 5 + 25 + 0.5 + 6.25 + 10)
        self.assertTrue(cost.complete)

    def test_unknown_model_is_unpriced_not_free(self):
        cost = PRICING.cost("claude-future-9", Usage(input_tokens=100))
        self.assertFalse(cost.complete)
        self.assertEqual(cost.unpriced, ("model:claude-future-9",))

    def test_unpriced_server_tools_are_reported(self):
        cost = PRICING.cost("claude-opus-5", Usage(input_tokens=1_000_000), {"web_search": 3})
        self.assertAlmostEqual(cost.usd, 5.0)
        self.assertFalse(cost.complete)
        self.assertEqual(cost.unpriced, ("server_tool:web_search",))

    def test_priced_server_tools_add_cost(self):
        pricing = Pricing("t", "t", {"claude-opus-5": OPUS}, {"web_search": 0.01})
        cost = pricing.cost("claude-opus-5", Usage(), {"web_search": 3})
        self.assertAlmostEqual(cost.usd, 0.03)
        self.assertTrue(cost.complete)

    def test_bundled_pricing_table_loads(self):
        pricing = Pricing.load()
        self.assertIn("claude-opus-5", pricing.models)
        self.assertEqual(pricing.models["claude-opus-5"].output, 25.0)
        self.assertEqual(dict(pricing.server_tools), {})  # unpriced until confirmed


class MeteringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-meter-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "metrics" / "llm_calls.jsonl"

    def meter(self, llm) -> MeteredLLM:
        models = {"judge_writing": "claude-sonnet-5"}
        return MeteredLLM(llm, PRICING, model_for=lambda role: models.get(role, "claude-opus-5"),
                          now=lambda: "2026-09-25T09:00:00.000Z", timer=StepTimer(0.5))

    def test_every_call_is_recorded_with_its_context(self):
        response = LLMResponse(model="claude-opus-5", text="x",
                               usage=Usage(input_tokens=2000, output_tokens=500, cache_read_input_tokens=8000),
                               tool_uses=(ToolUse("web_search", True), ToolUse("web_search", True), ToolUse("lookup", False)))
        bound = self.meter(ReplayLLM(script={"researcher": [response]})).bind(self.path, "W-20260925-001", "research")
        bound.run(LLMRequest(role="researcher", system="s", task="t"))
        [record] = read_records(self.path)
        self.assertEqual((record.seq, record.work_id, record.stage, record.role, record.adapter),
                         (1, "W-20260925-001", "research", "researcher", "replay"))
        self.assertEqual((record.requested_model, record.model), ("claude-opus-5", "claude-opus-5"))
        self.assertEqual(record.latency_ms, 500.0)
        self.assertEqual(record.server_tool_uses, {"web_search": 2})
        self.assertEqual(record.client_tool_calls, {"lookup": 1})
        self.assertAlmostEqual(record.cost_usd, (2000 * 5 + 500 * 25 + 8000 * 0.5) / 1e6)
        self.assertFalse(record.cost_complete)  # web search has no price
        self.assertEqual(record.pricing_version, "test")

    def test_model_comes_from_configuration_by_role(self):
        llm = ReplayLLM(script={"judge_writing": [LLMResponse(model="claude-sonnet-5", text="ok")]})
        self.meter(llm).bind(self.path, "W-20260925-001", "review").run(LLMRequest(role="judge_writing", system="s", task="t"))
        self.assertEqual(llm.requests[0].model, "claude-sonnet-5")
        self.assertEqual(read_records(self.path)[0].requested_model, "claude-sonnet-5")

    def test_failed_calls_are_recorded_and_raised(self):
        bound = self.meter(ReplayLLM(script={})).bind(self.path, "W-20260925-001", "draft")
        with self.assertRaises(LLMError):
            bound.run(LLMRequest(role="writer", system="s", task="t"))
        [record] = read_records(self.path)
        self.assertIn("ReplayMiss", record.error)
        self.assertEqual(record.stop_reason, "error")

    def test_aggregate_groups_and_flags_unpriced(self):
        responses = [LLMResponse(model="claude-opus-5", text="a", usage=Usage(1000, 100)),
                     LLMResponse(model="claude-future-9", text="b", usage=Usage(1000, 100))]
        meter = self.meter(ReplayLLM(script={"writer": responses}))
        meter.bind(self.path, "W", "draft").run(LLMRequest(role="writer", system="s", task="t"))
        meter.bind(self.path, "W", "revise").run(LLMRequest(role="writer", system="s", task="t2"))
        summary = aggregate(read_records(self.path))
        self.assertEqual(summary["calls"], 2)
        self.assertEqual(summary["input_tokens"], 2000)
        self.assertEqual(set(summary["by_stage"]), {"draft", "revise"})
        self.assertEqual(set(summary["by_model"]), {"claude-opus-5", "claude-future-9"})
        self.assertEqual(summary["by_role"]["writer"]["calls"], 2)
        self.assertFalse(summary["cost_complete"])
        self.assertEqual(summary["unpriced"], ["model:claude-future-9"])
        self.assertEqual([r.seq for r in read_records(self.path)], [1, 2])


if __name__ == "__main__":
    unittest.main()
