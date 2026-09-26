import unittest

from craftyprose.core.lifecycle import (
    EDGES,
    ENGINE_ONLY_STAGES,
    STAGES,
    Route,
    RouteError,
    Status,
    check_route,
)


class LifecycleShapeTest(unittest.TestCase):
    def test_seven_stages_in_approved_order(self):
        self.assertEqual(STAGES, ("intake", "research", "plan", "draft", "review", "revise", "release"))
        self.assertEqual(set(EDGES), set(STAGES))
        for targets in EDGES.values():
            self.assertTrue(targets <= set(STAGES))

    def test_reviews_and_releases_are_engine_only(self):
        self.assertEqual(ENGINE_ONLY_STAGES, {"review", "release"})


class CheckRouteTest(unittest.TestCase):
    def test_allowed_advances(self):
        allowed = [("intake", "research", False), ("research", "plan", False), ("plan", "draft", False),
                   ("draft", "review", True), ("review", "revise", True), ("review", "research", True),
                   ("review", "release", True), ("revise", "review", True), ("plan", "revise", True)]
        for src, dst, has_draft in allowed:
            with self.subTest(f"{src}->{dst}"):
                check_route(src, Route.advance(dst), has_draft=has_draft)

    def test_disallowed_advances(self):
        for src, dst in [("intake", "draft"), ("research", "review"), ("draft", "release"),
                         ("revise", "release"), ("release", "review"), ("intake", "intake")]:
            with self.subTest(f"{src}->{dst}"), self.assertRaises(RouteError):
                check_route(src, Route.advance(dst), has_draft=True)

    def test_a_second_draft_goes_through_revise(self):
        with self.assertRaises(RouteError):
            check_route("plan", Route.advance("draft"), has_draft=True)
        with self.assertRaises(RouteError):
            check_route("plan", Route.advance("revise"), has_draft=False)

    def test_pause_rules(self):
        check_route("intake", Route.pause(Status.NEEDS_INPUT, "no audience"), has_draft=False)
        check_route("research", Route.pause(Status.BLOCKED, "no evidence"), has_draft=False)
        with self.assertRaises(RouteError):
            check_route("intake", Route.pause(Status.RELEASED, "nope"), has_draft=False)
        with self.assertRaises(RouteError):
            check_route("intake", Route.pause(Status.NEEDS_INPUT, ""), has_draft=False)

    def test_only_release_marks_ready_and_only_review_rejects(self):
        check_route("release", Route.ready_for_release(), has_draft=True)
        with self.assertRaises(RouteError):
            check_route("review", Route.ready_for_release(), has_draft=True)
        check_route("review", Route.reject("critical defect persisted"), has_draft=True)
        with self.assertRaises(RouteError):
            check_route("draft", Route.reject("bad"), has_draft=True)
        with self.assertRaises(RouteError):
            check_route("review", Route.reject(""), has_draft=True)

    def test_unknown_action_and_stage(self):
        with self.assertRaises(RouteError):
            check_route("intake", Route("teleport"), has_draft=False)
        with self.assertRaises(RouteError):
            check_route("publish", Route.advance("review"), has_draft=False)


if __name__ == "__main__":
    unittest.main()
