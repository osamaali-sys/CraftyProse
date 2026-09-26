import unittest

from craftyprose.eis.guardrails import Guardrails
from craftyprose.eis.standards import library
from tests.helpers import BrandTestCase


class GuardrailTest(BrandTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.g = Guardrails.from_workspace(self.load())

    def failed(self, text, content_type="blog_article"):
        return {c.name for c in self.g.check_text(text, content_type).failures}

    def test_clean_text_passes(self):
        text = "We start with the runs that can't move. Most customers are dispatching from the board within two weeks."
        self.assertEqual(self.failed(text), set())

    def test_forbidden_terms_match_whole_terms_case_insensitively(self):
        self.assertIn("guardrail:no-competitor-names", self.failed("Unlike tanager  routes, we..."))
        self.assertNotIn("guardrail:no-competitor-names", self.failed("Tanager Routesmith is a person."))

    def test_banned_topics_apply_to_content_too(self):
        self.assertIn("guardrail:no-pricing", self.failed("Our pricing is simple."))
        # no stemming: list the variants you mean
        self.assertNotIn("guardrail:no-pricing", self.failed("Fuel prices went up."))

    def test_forbidden_patterns(self):
        self.assertIn("guardrail:no-unapproved-speed-claims", self.failed("Dispatch takes 30% less time."))
        self.assertNotIn("guardrail:no-unapproved-speed-claims", self.failed("30 drivers use it."))

    def test_required_disclosure_only_when_triggered(self):
        disclosure = "This isn't legal advice. Check the hours-of-service rules that apply to your drivers."
        self.assertNotIn("guardrail:hours-of-service", self.failed("Plan the first hour."))
        self.assertIn("guardrail:hours-of-service", self.failed("Plan breaks around hours of service."))
        ok = f"Plan breaks around hours of service.\n\n{disclosure.upper().replace(' ', '  ')}"
        self.assertNotIn("guardrail:hours-of-service", self.failed(ok))

    def test_speaker_policy_ignores_quotations(self):
        self.assertIn("guardrail:company-voice", self.failed("I think the board helps."))
        self.assertIn("guardrail:company-voice", self.failed("It saved my morning."))
        quoted = 'Dana told us, "I stopped reading addresses."\n\n> My drivers noticed first.\n\nWe agree.'
        self.assertNotIn("guardrail:company-voice", self.failed(quoted))

    def test_forbidden_claims(self):
        self.assertIn("forbidden_claim:on-time-guarantee", self.failed("Enjoy guaranteed on-time delivery."))

    def test_rules_can_be_scoped_to_content_types(self):
        self.append("guardrails.toml", '\n[[rules]]\nid = "no-hashtags"\ntype = "forbidden_pattern"\n'
                                       "pattern = '#\\w+'\nmessage = \"No hashtags.\"\napplies_to = [\"blog_article\"]\n")
        g = Guardrails.from_workspace(self.load())
        text = "Dispatch smarter #logistics"
        self.assertIn("guardrail:no-hashtags", {c.name for c in g.check_text(text, "blog_article").failures})
        self.assertNotIn("guardrail:no-hashtags", {c.name for c in g.check_text(text, "linkedin_post").failures})

    def test_failures_carry_known_pattern_ids_and_block(self):
        result = self.g.check_text("I think our pricing beats Tanager Routes by 30% less time.", "blog_article")
        self.assertFalse(result.passed)
        ids = {c.pattern_id for c in result.failures}
        self.assertEqual(ids, {"RK-BANNED-TOPIC", "RK-FORBIDDEN-TERM", "RK-SPEAKER-POLICY", "RK-FORBIDDEN-PATTERN"})
        for pattern_id in ids:
            library().get(pattern_id)
        self.assertTrue(all(c.blocking for c in result.checks))
        self.assertIn("Tanager Routes", next(c.detail for c in result.failures if c.pattern_id == "RK-FORBIDDEN-TERM"))


class TopicCheckTest(BrandTestCase):
    def test_banned_topics_and_open_questions_block_a_request(self):
        g = Guardrails.from_workspace(self.load())
        result = g.check_topic("Write a post comparing our pricing and TMS integration options.", "blog_article")
        self.assertEqual({c.name for c in result.failures}, {"guardrail:no-pricing", "open_question:tms-integrations"})
        self.assertIn("RK-BLOCKED-BY-OPEN-QUESTION", {c.pattern_id for c in result.failures})
        self.assertTrue(g.check_topic("Write about planning the first hour.", "blog_article").passed)

    def test_a_resolved_question_no_longer_blocks(self):
        self.edit("open_questions.toml", 'status = "open"', 'status = "resolved"')
        g = Guardrails.from_workspace(self.load())
        self.assertTrue(g.check_topic("TMS integration guide", "blog_article").passed)


if __name__ == "__main__":
    unittest.main()
