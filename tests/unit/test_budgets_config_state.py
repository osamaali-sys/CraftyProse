import shutil
import tempfile
import unittest
from pathlib import Path

from craftyprose.core.budgets import Budgets
from craftyprose.core.config import DEFAULT_MODEL, ConfigError, EngineConfig
from craftyprose.core.events import EventLog
from craftyprose.core.lifecycle import Status
from craftyprose.core.stages import StageDef, StageRegistry
from craftyprose.core.state import Pause, WorkState
from tests.helpers import advance_to, make_registry


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-unit-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class BudgetsTest(unittest.TestCase):
    def test_defaults(self):
        b = Budgets()
        self.assertEqual((b.max_attempts_per_stage, b.max_revisions, b.max_judge_reruns), (3, 3, 2))

    def test_invalid_values(self):
        for bad in (0, -1, True, "3", 2.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Budgets(max_revisions=bad)
        with self.assertRaises(ValueError):
            Budgets.from_mapping({"max_revision": 2})


class ConfigTest(TempDirCase):
    def write(self, text: str) -> Path:
        path = self.tmp / "craftyprose.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_file_gives_defaults(self):
        config = EngineConfig.load(self.tmp / "absent.toml")
        self.assertEqual(config.budgets, Budgets())
        self.assertEqual(config.model_for("anything"), DEFAULT_MODEL)

    def test_loads_budgets_models_and_pricing_path(self):
        config = EngineConfig.load(self.write(
            '[budgets]\nmax_revisions = 2\n[models]\njudge_writing = "claude-sonnet-5"\n[pricing]\nfile = "p.toml"\n'))
        self.assertEqual(config.budgets.max_revisions, 2)
        self.assertEqual(config.model_for("judge_writing"), "claude-sonnet-5")
        self.assertEqual(config.model_for("writer"), DEFAULT_MODEL)
        self.assertEqual(config.pricing_path, self.tmp / "p.toml")

    def test_typos_are_errors(self):
        for text in ('[budget]\nmax_revisions = 2\n', '[budgets]\nmax_revision = 2\n',
                     '[pricing]\npath = "x"\n', '[models]\nwriter = ""\n'):
            with self.subTest(text=text), self.assertRaises(ConfigError):
                EngineConfig.load(self.write(text))


class StateTest(unittest.TestCase):
    def test_round_trip_including_pause(self):
        s = WorkState("W-20260925-001", "northwind", "blog_article", Status.NEEDS_INPUT, "intake",
                      "t0", "t1", revision_allowance=3,
                      pause=Pause(Status.NEEDS_INPUT, "intake", "no audience", {"q": ["who?"]}, "t1"))
        again = WorkState.from_dict(s.to_dict())
        self.assertEqual(again.to_dict(), s.to_dict())
        self.assertIs(again.status, Status.NEEDS_INPUT)

    def test_unknown_schema_is_refused(self):
        s = WorkState("W-20260925-001", "b", "t", Status.IN_PROGRESS, "intake", "t0", "t0", revision_allowance=3)
        data = s.to_dict()
        data["schema"] = 99
        with self.assertRaises(ValueError):
            WorkState.from_dict(data)


class EventLogTest(TempDirCase):
    def test_sequence_is_shared_by_every_handle(self):
        path = self.tmp / "events.jsonl"
        a, b = EventLog(path, lambda: "t"), EventLog(path, lambda: "t")
        a.append("one")
        b.append("two")
        a.append("three")
        self.assertEqual([e["seq"] for e in a.read()], [1, 2, 3])


class RegistryTest(unittest.TestCase):
    def test_registry_needs_every_stage_exactly_once(self):
        make_registry()  # complete
        stages = [StageDef(n, "json", router=advance_to("x")) for n in ("intake", "research")]
        with self.assertRaises(ValueError):
            StageRegistry(stages)
        full = list(make_registry()._stages.values())
        with self.assertRaises(ValueError):
            StageRegistry(full + [full[0]])

    def test_stage_def_shape_rules(self):
        r = advance_to("review")
        with self.assertRaises(ValueError):
            StageDef("publish", "json", router=r)
        with self.assertRaises(ValueError):
            StageDef("draft", "json", router=r)
        with self.assertRaises(ValueError):
            StageDef("revise", "json", router=r)  # no draft_field
        with self.assertRaises(ValueError):
            StageDef("plan", "json", router=r, draft_field="draft")
        with self.assertRaises(ValueError):
            StageDef("draft", "markdown", router=r, binds_draft=True)


if __name__ == "__main__":
    unittest.main()
