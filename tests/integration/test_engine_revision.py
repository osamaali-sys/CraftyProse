import unittest

from craftyprose.core.budgets import Budgets
from craftyprose.core.config import EngineConfig
from craftyprose.core.lifecycle import Route, Status
from craftyprose.core.stages import StageDef
from tests.helpers import MAJOR_FINDING, EngineTestCase, happy_script, make_registry, producer_for, reply, review_router

REVISED = "# Title\n\nSecond draft, grounded in the brand's own claims.\n"
REVISION = {"draft": REVISED, "resolutions": [{"fingerprint": "x", "action": "changed"}]}


def failing_then_passing_review():
    return [reply({"findings": [MAJOR_FINDING]}), reply({"findings": []})]


class RevisionLoopTest(EngineTestCase):
    def test_blocking_review_routes_to_revise_and_the_revision_becomes_the_draft(self):
        drafts_seen_by_review = []

        def review_producer(ctx):
            drafts_seen_by_review.append(ctx.view.current_draft())
            return producer_for("judge")(ctx)

        registry = make_registry(review=StageDef("review", "json", router=review_router,
                                                 producer=review_producer, binds_draft=True))
        script = happy_script(judge=failing_then_passing_review(),
                              writer=[reply(text="# Title\n\nFirst draft.\n"), reply(REVISION)])
        engine = self.make_engine(script, registry=registry)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")

        state = engine.status(work_id)
        self.assertEqual(state.status, Status.READY_FOR_RELEASE)
        self.assertEqual((state.draft_version, state.revision_count), (2, 1))
        self.assertEqual(engine.view(work_id).current_draft(), REVISED)
        # the second review saw the revised text, not the first draft
        self.assertEqual(drafts_seen_by_review, ["# Title\n\nFirst draft.\n", REVISED])
        self.assertEqual([e["draft_version"] for e in self.events_named(engine, work_id, "draft_promoted")], [1, 2])

    def test_a_failed_revision_is_not_promoted(self):
        script = happy_script(judge=[reply({"findings": [MAJOR_FINDING]})],
                              writer=[reply(text="# Title\n\nFirst draft.\n"), reply({"resolutions": []})])
        engine = self.make_engine(script)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "revise")
        result = engine.run_stage(work_id)
        self.assertFalse(result.ok)
        self.assertEqual(result.failures[0]["name"], "revised_draft_present")
        state = engine.status(work_id)
        self.assertEqual((state.draft_version, state.stage), (1, "revise"))
        self.assertEqual(engine.view(work_id).current_draft(), "# Title\n\nFirst draft.\n")

    def test_the_revision_budget_ends_in_human_review_and_a_grant_continues(self):
        config = EngineConfig(budgets=Budgets(max_revisions=1))
        script = happy_script(judge=[reply({"findings": [MAJOR_FINDING]})] * 3 + [reply({"findings": []})],
                              writer=[reply(text="# T\n\nOne.\n"), reply({"draft": "# T\n\nTwo.\n"}),
                                      reply({"draft": "# T\n\nThree.\n"})])
        engine = self.make_engine(script, config=config)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.REQUIRES_HUMAN_REVIEW)
        self.assertEqual((state.stage, state.revision_count), ("review", 1))
        self.assertIn("revision budget used (1 of 1)", state.pause.reason)

        engine.resume(work_id, by="Osama", note="One more pass is fine.", grant_revisions=1)
        self.run_until(engine, work_id, "never")  # review 3 fails -> revise -> review 4 passes
        state = engine.status(work_id)
        self.assertEqual(state.status, Status.READY_FOR_RELEASE)
        self.assertEqual((state.revision_count, state.revision_allowance, state.draft_version), (2, 2, 3))

    def test_research_more_counts_as_a_revision_and_returns_through_plan_to_revise(self):
        needs_evidence = {**MAJOR_FINDING, "pattern_id": "EV-UNSUPPORTED-CLAIM", "requires_new_evidence": True}
        script = happy_script(
            judge=[reply({"findings": [needs_evidence]}), reply({"findings": []})],
            researcher=[reply({"claims": []}), reply({"claims": ["C9"]})],
            strategist=[reply({"sections": ["one"]}), reply({"sections": ["one", "two"]})],
            writer=[reply(text="# T\n\nOne.\n"), reply({"draft": "# T\n\nOne, now supported.\n"})],
        )
        engine = self.make_engine(script)
        work_id = self.new_item(engine)
        order = []
        while engine.status(work_id).status is Status.IN_PROGRESS:
            order.append(engine.status(work_id).stage)
            self.assertTrue(engine.run_stage(work_id).ok)
        self.assertEqual(order, ["intake", "research", "plan", "draft", "review",
                                 "research", "plan", "revise", "review", "release"])
        state = engine.status(work_id)
        self.assertEqual((state.status, state.revision_count, state.draft_version),
                         (Status.READY_FOR_RELEASE, 1, 2))

    def test_plan_cannot_start_a_second_draft(self):
        registry = make_registry(plan=StageDef("plan", "json", router=lambda ctx: Route.advance("draft"),
                                               producer=producer_for("strategist")))
        needs_evidence = {**MAJOR_FINDING, "requires_new_evidence": True}
        script = happy_script(judge=[reply({"findings": [needs_evidence]})],
                              researcher=[reply({})] * 2, strategist=[reply({})] * 2)
        engine = self.make_engine(script, registry=registry)
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        state = engine.status(work_id)
        self.assertEqual((state.status, state.stage), (Status.REQUIRES_HUMAN_REVIEW, "plan"))
        self.assertIn("draft already exists", state.pause.reason)


class DraftBindingTest(EngineTestCase):
    def test_review_records_the_draft_it_judged(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "release")
        state = engine.status(work_id)
        self.assertEqual(state.accepted["review"]["draft_sha256"], state.draft_sha256)

    def test_a_review_of_a_stale_draft_fails_its_gate(self):
        stale = {"findings": [], "draft_sha256": "0" * 64}
        engine = self.make_engine(happy_script(judge=[reply(stale)]))
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "review")
        result = engine.run_stage(work_id)
        self.assertFalse(result.ok)
        self.assertEqual(result.failures[0]["name"], "draft_binding")


if __name__ == "__main__":
    unittest.main()
