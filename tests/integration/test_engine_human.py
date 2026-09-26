import unittest

from craftyprose.core.engine import EngineError
from craftyprose.core.lifecycle import Route, Status
from craftyprose.core.stages import StageDef
from tests.helpers import MAJOR_FINDING, EngineTestCase, happy_script, make_registry, producer_for, reply


def ask_for_audience(ctx):
    if not ctx.view.human_inputs():
        return Route.pause(Status.NEEDS_INPUT, "the request names no audience",
                           {"questions": ["Who is this for?"]})
    return Route.advance("research")


class PauseAndResumeTest(EngineTestCase):
    def registry(self):
        return make_registry(intake=StageDef("intake", "json", router=ask_for_audience, producer=producer_for("planner")))

    def test_needs_input_then_resume_with_an_answer(self):
        engine = self.make_engine(happy_script(planner=[reply({"topic": "t"}), reply({"topic": "t", "audience": "ops leads"})]),
                                  registry=self.registry())
        work_id = self.new_item(engine)
        engine.run_stage(work_id)
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.NEEDS_INPUT)
        self.assertEqual(state.pause.details, {"questions": ["Who is this for?"]})
        self.assertFalse(engine.run_stage(work_id).ok)

        state = engine.resume(work_id, by="Osama", note="Operations leads at mid-size logistics firms.")
        self.assertEqual((state.status, state.stage, state.pause), (Status.IN_PROGRESS, "intake", None))
        self.assertEqual(engine.view(work_id).human_inputs(), ["Operations leads at mid-size logistics firms.\n"])
        self.assertTrue(engine.run_stage(work_id).ok)
        self.assertEqual(engine.status(work_id).stage, "research")
        resumed = self.events_named(engine, work_id, "resumed")[0]
        self.assertEqual((resumed["by"], resumed["previous_pause"]["status"]), ("Osama", "needs_input"))

    def test_blocked_research_can_resume(self):
        registry = make_registry(research=StageDef(
            "research", "json", producer=producer_for("researcher"),
            router=lambda ctx: Route.pause(Status.BLOCKED, "no verifiable source for a required claim")))
        engine = self.make_engine(registry=registry)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        self.assertEqual(engine.status(work_id).status, Status.BLOCKED)
        engine.resume(work_id, by="Osama", note="Added the annual report as a source.")
        self.assertEqual(engine.status(work_id).status, Status.IN_PROGRESS)

    def test_resume_rules(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        with self.assertRaises(EngineError):
            engine.resume(work_id, by="Osama")  # not paused
        engine.submit(work_id, "intake", "{}")  # force failures to pause it
        engine.submit(work_id, "intake", "{}")
        engine.submit(work_id, "intake", "{}")
        self.assertEqual(engine.status(work_id).status, Status.REQUIRES_HUMAN_REVIEW)
        with self.assertRaises(EngineError):
            engine.resume(work_id, by=" ")
        with self.assertRaises(EngineError):
            engine.resume(work_id, by="Osama", grant_revisions=-1)
        state = engine.resume(work_id, by="Osama")
        self.assertEqual(state.attempts["intake"], 0)


class RejectTest(EngineTestCase):
    def test_a_person_can_reject_any_unfinished_item(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        with self.assertRaises(EngineError):
            engine.reject(work_id, by="Osama", reason="")
        state = engine.reject(work_id, by="Osama", reason="The brief changed.")
        self.assertEqual(state.status, Status.REJECTED)
        with self.assertRaises(EngineError):
            engine.reject(work_id, by="Osama", reason="again")
        with self.assertRaises(EngineError):
            engine.resume(work_id, by="Osama")

    def test_released_work_cannot_be_rejected(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        engine.approve(work_id, by="Osama")
        with self.assertRaises(EngineError):
            engine.reject(work_id, by="Osama", reason="too late")

    def test_review_can_reject_automatically(self):
        registry = make_registry(review=StageDef("review", "json", producer=producer_for("judge"), binds_draft=True,
                                                 router=lambda ctx: Route.reject("a critical defect persisted")))
        engine = self.make_engine(happy_script(judge=[reply({"findings": [MAJOR_FINDING]})]), registry=registry)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.REJECTED)
        self.assertEqual(self.events_named(engine, work_id, "rejected")[0]["by"], "engine")


if __name__ == "__main__":
    unittest.main()
