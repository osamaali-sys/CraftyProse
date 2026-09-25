import json
import unittest

from craftyprose.core.lifecycle import Route, Status
from craftyprose.core.stages import StageDef
from craftyprose.core.validation import ValidationResult
from tests.helpers import EngineTestCase, advance_to, happy_script, make_registry, producer_for, reply


def advisory_validator(ctx):
    return ValidationResult("style").add("sentence_variety", False, "sentences are uniform", blocking=False,
                                         pattern_id="HW-UNIFORM-RHYTHM")


def crashing_validator(ctx):
    raise KeyError("oops")


class GateFailureTest(EngineTestCase):
    def test_failed_submission_is_persisted_and_recorded_but_not_accepted(self):
        engine = self.make_engine(happy_script(planner=[reply({"subject": "no topic key"})]))
        work_id = self.new_item(engine)
        result = engine.run_stage(work_id)
        self.assertFalse(result.ok)
        self.assertEqual([f["name"] for f in result.failures], ["has_topic"])
        root = self.item_dir(work_id)
        self.assertTrue((root / "submissions" / "intake" / "intake-v1.json").exists())
        record = json.loads((root / "validations" / "intake-v1.json").read_text(encoding="utf-8"))
        self.assertFalse(record["passed"])
        self.assertEqual(record["origin"], "engine")
        state = engine.status(work_id)
        self.assertNotIn("intake", state.accepted)
        self.assertEqual((state.stage, state.attempts["intake"]), ("intake", 1))

    def test_every_gate_run_is_recorded(self):
        engine = self.make_engine(happy_script(planner=[reply({"x": 1}), reply({"topic": "onboarding"})]))
        work_id = self.new_item(engine)
        engine.run_stage(work_id)
        engine.run_stage(work_id)
        names = sorted(p.name for p in (self.item_dir(work_id) / "validations").iterdir())
        self.assertEqual(names, ["intake-v1.json", "intake-v2.json"])
        state = engine.status(work_id)
        self.assertEqual(state.accepted["intake"]["version"], 2)
        self.assertEqual(state.attempts["intake"], 0)  # a pass resets the stage's attempts

    def test_attempt_budget_escalates_to_a_person(self):
        engine = self.make_engine(happy_script(planner=[reply({"x": 1})] * 3))
        work_id = self.new_item(engine)
        for _ in range(3):
            result = engine.run_stage(work_id)
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.REQUIRES_HUMAN_REVIEW)
        self.assertIn("attempt budget of 3 used", state.pause.reason)
        self.assertFalse(engine.run_stage(work_id).ok)
        self.assertFalse(engine.submit(work_id, "intake", '{"topic": "x"}').ok)
        self.assertIn("attempt budget", result.message)

    def test_the_producer_is_told_why_its_last_submission_failed(self):
        seen = []

        def produce(ctx):
            seen.append([c.name for c in ctx.feedback])
            return producer_for("planner")(ctx)

        registry = make_registry(intake=StageDef("intake", "json", router=advance_to("research"), producer=produce,
                                                 validators=(make_registry()["intake"].validators)))
        engine = self.make_engine(happy_script(planner=[reply({"x": 1}), reply({"topic": "t"})]), registry=registry)
        work_id = self.new_item(engine)
        engine.run_stage(work_id)
        engine.run_stage(work_id)
        self.assertEqual(seen, [[], ["has_topic"]])

    def test_malformed_artifacts_fail_named_checks(self):
        cases = {
            "invalid JSON": ("intake", "{not json", "artifact_parses"),
            "JSON array": ("intake", "[1, 2]", "artifact_is_object"),
        }
        for label, (stage, text, check) in cases.items():
            with self.subTest(label):
                engine = self.make_engine()
                work_id = self.new_item(engine)
                result = engine.submit(work_id, stage, text)
                self.assertEqual([f["name"] for f in result.failures], [check])

    def test_empty_markdown_draft_fails(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "draft")
        result = engine.submit(work_id, "draft", "  \n ")
        self.assertEqual([f["name"] for f in result.failures], ["artifact_not_empty"])
        self.assertEqual(engine.status(work_id).draft_version, 0)

    def test_a_crashing_validator_fails_closed(self):
        registry = make_registry(intake=StageDef("intake", "json", router=advance_to("research"),
                                                 producer=producer_for("planner"), validators=(crashing_validator,)))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        result = engine.run_stage(work_id)
        self.assertFalse(result.ok)
        self.assertEqual(result.failures[0]["name"], "validator_error")
        self.assertIn("KeyError", result.failures[0]["detail"])

    def test_advisories_are_recorded_without_blocking(self):
        registry = make_registry(intake=StageDef("intake", "json", router=advance_to("research"),
                                                 producer=producer_for("planner"), validators=(advisory_validator,)))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        result = engine.run_stage(work_id)
        self.assertTrue(result.ok)
        self.assertEqual(result.advisories[0]["pattern_id"], "HW-UNIFORM-RHYTHM")
        record = json.loads((self.item_dir(work_id) / "validations" / "intake-v1.json").read_text(encoding="utf-8"))
        self.assertTrue(record["passed"])


class ProducerAndRouterFailureTest(EngineTestCase):
    def test_a_failing_producer_counts_as_an_attempt_and_writes_no_submission(self):
        engine = self.make_engine(happy_script(planner=[]))  # replay has nothing to say
        work_id = self.new_item(engine)
        result = engine.run_stage(work_id)
        self.assertFalse(result.ok)
        self.assertEqual(engine.status(work_id).attempts["intake"], 1)
        failure = self.events_named(engine, work_id, "producer_failed")[0]
        self.assertIn("ReplayMiss", failure["error"])
        self.assertFalse((self.item_dir(work_id) / "submissions").exists())
        self.assertEqual(engine.usage(work_id)["llm"]["errors"], 1)

    def test_a_producer_returning_the_wrong_type_fails(self):
        registry = make_registry(draft=StageDef("draft", "markdown", router=advance_to("review"),
                                                producer=lambda ctx: {"not": "markdown"}))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "draft")
        self.assertFalse(engine.run_stage(work_id).ok)
        self.assertIn("markdown", self.events_named(engine, work_id, "producer_failed")[0]["error"])

    def test_a_disallowed_route_stops_for_a_person(self):
        registry = make_registry(intake=StageDef("intake", "json", router=lambda ctx: Route.advance("draft"),
                                                 producer=producer_for("planner")))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        result = engine.run_stage(work_id)
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.REQUIRES_HUMAN_REVIEW)
        self.assertIn("not an allowed transition", state.pause.reason)
        self.assertTrue(result.ok)  # the artifact itself passed its gate and stays accepted
        self.assertIn("intake", state.accepted)

    def test_a_crashing_router_stops_for_a_person(self):
        def broken(ctx):
            raise RuntimeError("router bug")

        registry = make_registry(intake=StageDef("intake", "json", router=broken, producer=producer_for("planner")))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        engine.run_stage(work_id)
        self.assertIn("router bug", engine.status(work_id).pause.reason)


if __name__ == "__main__":
    unittest.main()
