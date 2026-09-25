"""Predecessor failures, encoded so they can't come back.

Each test names the failure it pins, citing the extraction report
(docs/extraction/01-extraction-report.md) and the evidence probes in
docs/extraction/evidence/. Failures that belong to later milestones (excerpt
verification, claim coverage, writing checks, judge-output validation, revision
accounting) get their regression tests in those milestones.
"""
import json
import unittest

from craftyprose.core.findings import Finding, FindingError, verdict_of
from craftyprose.core.lifecycle import Status
from craftyprose.core.workitem import WorkItem
from tests.helpers import MAJOR_FINDING, EngineTestCase, happy_script, reply


class RubberStampTest(EngineTestCase):
    """ER §8.2: the Metanous author submitted its own reviews; zero-finding
    "pass" reviews reached approval (probe_metanous_gate_bypasses, case 9)."""

    def test_reviews_cannot_be_submitted_by_authors(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "review")
        forged = json.dumps({"findings": [], "draft_sha256": engine.status(work_id).draft_sha256})
        result = engine.submit(work_id, "review", forged)  # origin defaults to external
        self.assertFalse(result.ok)
        self.assertIn("produced by the engine", result.message)
        self.assertFalse((self.item_dir(work_id) / "submissions" / "review").exists())
        self.assertEqual(engine.status(work_id).stage, "review")

    def test_release_cannot_be_submitted_from_outside(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "release")
        self.assertFalse(engine.submit(work_id, "release", '{"package": "forged"}').ok)
        self.assertEqual(engine.status(work_id).status, Status.IN_PROGRESS)


class SelfResolvedFindingTest(unittest.TestCase):
    """ER §8.2: a critical 'fabricated statistic' finding marked resolved:true by
    its own reviewer was approved (probe_metanous_gate_bypasses, case 8)."""

    def test_findings_cannot_declare_themselves_resolved(self):
        with self.assertRaises(FindingError):
            Finding.from_dict({**MAJOR_FINDING, "severity": "critical", "resolved": True}, source="judge:evidence")

    def test_a_pass_verdict_with_a_major_finding_is_a_fail(self):
        with self.assertRaises(FindingError):  # a judge can't set the verdict at all
            Finding.from_dict({**MAJOR_FINDING, "verdict": "pass"}, source="judge:editorial")
        finding = Finding.from_dict(MAJOR_FINDING, source="judge:editorial")
        self.assertEqual(verdict_of([finding]), "fail")


class DraftPersistenceTest(EngineTestCase):
    """ER §13 P6: Metanous's real bug. A passed revision stayed in revisions/,
    so reviews re-checked the old draft and approval published it."""

    def test_passed_revision_is_the_draft_that_reaches_release(self):
        revised = "# Title\n\nRevised text.\n"
        engine = self.make_engine(happy_script(
            judge=[reply({"findings": [MAJOR_FINDING]}), reply({"findings": []})],
            writer=[reply(text="# Title\n\nFirst draft.\n"), reply({"draft": revised})]))
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        engine.approve(work_id, by="Osama")
        approval = json.loads((self.item_dir(work_id) / "release" / "approval.json").read_text(encoding="utf-8"))
        state = engine.status(work_id)
        self.assertEqual(engine.view(work_id).current_draft(), revised)
        self.assertEqual(approval["draft_version"], 2)
        self.assertEqual(approval["draft_sha256"], state.draft_sha256)
        self.assertEqual(state.accepted["review"]["draft_sha256"], state.draft_sha256)


class RecordKeepingTest(EngineTestCase):
    """ER §8.2 / D14: Metanous documented that every gate run is written to
    validations/, but submit() never wrote it."""

    def test_every_gate_run_is_on_disk(self):
        engine = self.make_engine(happy_script(planner=[reply({"x": 1}), reply({"topic": "t"})]))
        work_id = self.new_item(engine)
        self.assertFalse(engine.run_stage(work_id).ok)  # intake v1 fails its gate
        self.run_until(engine, work_id, "never")
        validations = sorted(p.name for p in (self.item_dir(work_id) / "validations").iterdir())
        submissions = sorted(p.name.rsplit(".", 1)[0]
                             for p in (self.item_dir(work_id) / "submissions").rglob("*-v*.*"))
        self.assertEqual([v.rsplit(".", 1)[0] for v in validations], submissions)
        self.assertIn("intake-v1.json", validations)  # the failed run too


class VersionSortTest(unittest.TestCase):
    """ER §14 D15: Metanous chose the latest draft by string sort, so draft-v10
    would sort before draft-v2."""

    def test_latest_is_numeric(self):
        import shutil
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        item = WorkItem(tmp / "W-20260925-001")
        for i in range(1, 12):
            item.put_draft(f"draft {i}")
        self.assertEqual(WorkItem.latest_version(tmp / "W-20260925-001" / "drafts", "draft", "md"), 11)
        self.assertEqual(item.read_draft(11), "draft 11")


class StateSurvivesDiskTest(EngineTestCase):
    """ER §8.1: Click Savvy's KPService saved enums as 'KPStatus.DRAFT' and
    crashed on its second write; its ExecutionEngine kept state only in memory."""

    def test_every_operation_starts_from_disk(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        engine.run_stage(work_id)
        fresh = self.make_engine(happy_script())  # a new process, in effect
        state = fresh.status(work_id)
        self.assertEqual((state.status, state.stage), (Status.IN_PROGRESS, "research"))
        raw = json.loads((self.item_dir(work_id) / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["status"], "in_progress")  # plain values, not enum reprs


class NoDeadlockTest(EngineTestCase):
    """ER §8.1: Click Savvy's ExecutionEngine could never pass gate 0 or gate 1
    (probe_clicksavvy_infrastructure, case 8)."""

    def test_first_stage_advances_after_its_gate_passes(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.assertTrue(engine.run_stage(work_id).ok)
        self.assertEqual(engine.status(work_id).stage, "research")


class CrashingValidatorTest(EngineTestCase):
    """ER §8.1: Click Savvy's GCV couldn't be constructed (NameError). A broken
    check must fail the gate, never be skipped."""

    def test_a_validator_that_raises_blocks_the_gate(self):
        from craftyprose.core.stages import StageDef
        from tests.helpers import advance_to, make_registry, producer_for

        def broken(ctx):
            raise NameError("FirstPersonExperienceValidator")

        registry = make_registry(intake=StageDef("intake", "json", router=advance_to("research"),
                                                 producer=producer_for("planner"), validators=(broken,)))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        result = engine.run_stage(work_id)
        self.assertFalse(result.ok)
        self.assertIn("NameError", result.failures[0]["detail"])
        self.assertEqual(engine.status(work_id).stage, "intake")


if __name__ == "__main__":
    unittest.main()
