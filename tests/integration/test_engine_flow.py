import json
import unittest

from craftyprose.core.engine import EngineError, UnknownWorkItem
from craftyprose.core.lifecycle import Status
from tests.helpers import EngineTestCase


class CreationTest(EngineTestCase):
    def test_new_creates_the_work_item_layout(self):
        engine = self.make_engine()
        state = engine.new("  Write about onboarding.  ", brand_id="northwind", content_type="blog_article")
        self.assertEqual(state.work_id, "W-20260925-001")
        self.assertEqual((state.status, state.stage), (Status.IN_PROGRESS, "intake"))
        root = self.item_dir(state.work_id)
        self.assertEqual((root / "request.md").read_text(encoding="utf-8"), "Write about onboarding.\n")
        self.assertTrue((root / "state.json").exists())
        self.assertEqual([e["event"] for e in engine.events(state.work_id)], ["created"])
        self.assertEqual(state.revision_allowance, 3)

    def test_ids_are_sequential_per_day(self):
        engine = self.make_engine()
        ids = [self.new_item(engine) for _ in range(3)]
        self.assertEqual(ids, ["W-20260925-001", "W-20260925-002", "W-20260925-003"])
        self.assertEqual(engine.list(), ids)

    def test_new_rejects_bad_input(self):
        engine = self.make_engine()
        with self.assertRaises(EngineError):
            engine.new("   ", brand_id="northwind", content_type="blog_article")
        for brand, ctype in (("North Wind", "blog_article"), ("northwind", "Blog"), ("", "blog_article")):
            with self.subTest(brand=brand, ctype=ctype), self.assertRaises(EngineError):
                engine.new("Write.", brand_id=brand, content_type=ctype)

    def test_unknown_work_items(self):
        engine = self.make_engine()
        for work_id in ("W-20260925-999", "../etc", "", "W-1"):
            with self.subTest(work_id=work_id), self.assertRaises(UnknownWorkItem):
                engine.status(work_id)


class HappyPathTest(EngineTestCase):
    def test_a_clean_run_reaches_ready_for_release_but_is_never_released(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        result = engine.run_stage(work_id)  # nothing more for the engine to do
        self.assertFalse(result.ok)
        self.assertIn("ready_for_release", result.message)
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.READY_FOR_RELEASE)
        self.assertEqual(state.stage, "release")
        self.assertEqual(state.draft_version, 1)
        self.assertIsNone(state.approval)
        self.assertFalse((self.item_dir(work_id) / "release" / "approval.json").exists())

    def test_stage_order(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        order = []
        while engine.status(work_id).status is Status.IN_PROGRESS:
            order.append(engine.status(work_id).stage)
            self.assertTrue(engine.run_stage(work_id).ok)
        self.assertEqual(order, ["intake", "research", "plan", "draft", "review", "release"])

    def test_human_approval_releases_and_records_the_approver(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        with self.assertRaises(EngineError):
            engine.approve(work_id, by="Osama")  # not ready yet
        self.run_until(engine, work_id, "never")
        with self.assertRaises(EngineError):
            engine.approve(work_id, by="   ")
        state = engine.approve(work_id, by="Osama")
        self.assertEqual(state.status, Status.RELEASED)
        record = json.loads((self.item_dir(work_id) / "release" / "approval.json").read_text(encoding="utf-8"))
        self.assertEqual(record["approved_by"], "Osama")
        self.assertEqual(record["draft_sha256"], state.draft_sha256)
        self.assertIn("can't verify", record["note"])
        with self.assertRaises(EngineError):
            engine.approve(work_id, by="Osama")  # already released
        self.assertEqual(self.events_named(engine, work_id, "approved")[0]["by"], "Osama")

    def test_run_stage_is_metered_and_summarized(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        usage = engine.usage(work_id)
        llm = usage["llm"]
        self.assertEqual(llm["calls"], 6)
        self.assertEqual(set(llm["by_stage"]), {"intake", "research", "plan", "draft", "review", "release"})
        self.assertEqual(llm["input_tokens"], 6000)
        self.assertEqual(llm["output_tokens"], 1200)
        self.assertAlmostEqual(llm["cost_usd"], 6 * (1000 * 5 + 200 * 25) / 1e6)
        self.assertTrue(llm["cost_complete"])
        self.assertEqual(llm["by_model"]["claude-opus-5"]["calls"], 6)
        self.assertEqual(usage["revisions"], {"used": 0, "allowed": 3})
        self.assertEqual(usage["gate_runs"]["draft"], {"passed": 1, "failed": 0})
        self.assertEqual(usage["stage_runs"]["review"]["runs"], 1)
        self.assertGreater(usage["stage_runs"]["review"]["wall_ms"], 0)
        self.assertGreater(llm["latency_ms"], 0)


class ExternalSubmissionTest(EngineTestCase):
    def test_authoring_stages_accept_external_submissions(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        result = engine.submit(work_id, "intake", '{"topic": "onboarding"}')
        self.assertTrue(result.ok, result.message)
        self.assertEqual(engine.status(work_id).stage, "research")
        self.assertEqual(self.events_named(engine, work_id, "submitted")[0]["origin"], "external")

    def test_wrong_stage_and_paused_items_are_refused(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        result = engine.submit(work_id, "research", "{}")
        self.assertFalse(result.ok)
        self.assertIn("current stage is 'intake'", result.message)
        engine.reject(work_id, by="Osama", reason="off-brief")
        self.assertIn("rejected", engine.submit(work_id, "intake", '{"topic": "x"}').message)
        self.assertEqual([e["event"] for e in engine.events(work_id)].count("submission_refused"), 2)

    def test_origin_must_be_known(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        with self.assertRaises(EngineError):
            engine.submit(work_id, "intake", "{}", origin="judge")


if __name__ == "__main__":
    unittest.main()
