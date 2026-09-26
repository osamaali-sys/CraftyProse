import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from craftyprose.runtime.llm import Block, LLMRequest, LLMResponse, ToolUse, Usage
from craftyprose.runtime.replay import ReplayLLM, ReplayMiss, save_fixture

REQUEST = LLMRequest(role="writer", system="You write.", task="Write the draft.",
                     context=(Block("brief", "topic: onboarding", cacheable=True),),
                     schema={"type": "object"}, tools=("web_search",), model="claude-opus-5")
RESPONSE = LLMResponse(model="claude-opus-5", text="# Draft", usage=Usage(input_tokens=10, output_tokens=5),
                       tool_uses=(ToolUse("web_search", server=True),))


class KeyedReplayTest(unittest.TestCase):
    def test_exact_request_replays(self):
        llm = ReplayLLM({REQUEST.key(): RESPONSE})
        self.assertEqual(llm.run(REQUEST), RESPONSE)
        self.assertEqual(llm.requests, [REQUEST])

    def test_any_change_to_the_request_misses(self):
        llm = ReplayLLM({REQUEST.key(): RESPONSE})
        variants = {
            "task": replace(REQUEST, task="Write it again."),
            "system": replace(REQUEST, system="You edit."),
            "context": replace(REQUEST, context=(Block("brief", "topic: pricing", cacheable=True),)),
            "cacheability": replace(REQUEST, context=(Block("brief", "topic: onboarding"),)),
            "schema": replace(REQUEST, schema={"type": "array"}),
            "tools": replace(REQUEST, tools=()),
            "model": replace(REQUEST, model="claude-sonnet-5"),
            "role": replace(REQUEST, role="judge"),
        }
        for label, variant in variants.items():
            with self.subTest(label), self.assertRaises(ReplayMiss):
                llm.run(variant)

    def test_fixture_files_round_trip(self):
        tmp = Path(tempfile.mkdtemp(prefix="craftyprose-replay-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        save_fixture(tmp, REQUEST, RESPONSE)
        self.assertEqual(ReplayLLM.from_dir(tmp).run(REQUEST), RESPONSE)


class ScriptedReplayTest(unittest.TestCase):
    def test_responses_come_in_order_per_role(self):
        first, second = LLMResponse(model="m", text="1"), LLMResponse(model="m", text="2")
        llm = ReplayLLM(script={"writer": [first, second]})
        self.assertEqual(llm.run(REQUEST).text, "1")
        self.assertEqual(llm.run(REQUEST).text, "2")
        with self.assertRaises(ReplayMiss):
            llm.run(REQUEST)
        with self.assertRaises(ReplayMiss):
            llm.run(replace(REQUEST, role="judge"))

    def test_exactly_one_mode(self):
        with self.assertRaises(ValueError):
            ReplayLLM()
        with self.assertRaises(ValueError):
            ReplayLLM({}, script={})


class ResponseSerializationTest(unittest.TestCase):
    def test_round_trip(self):
        response = LLMResponse(model="m", data={"a": 1}, usage=Usage(1, 2, 3, 4, 5),
                               tool_uses=(ToolUse("fetch", server=False),), stop_reason="max_tokens")
        self.assertEqual(LLMResponse.from_dict(response.to_dict()), response)


if __name__ == "__main__":
    unittest.main()
