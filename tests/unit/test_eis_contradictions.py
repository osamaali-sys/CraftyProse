import unittest

from craftyprose.eis.contradictions import find_contradictions
from tests.helpers import BrandTestCase


class ContradictionTest(BrandTestCase):
    def ids(self):
        return [c.id for c in find_contradictions(self.load())]

    def test_the_example_brand_is_consistent(self):
        self.assertEqual(self.ids(), [])

    def test_a_term_both_preferred_and_avoided(self):
        self.append("voice.toml", '\n[[lexicon.avoid]]\nterm = "dispatcher"\nreason = "x"\n')
        self.assertIn("C-LEXICON-BOTH", self.ids())

    def test_a_preferred_term_that_a_guardrail_forbids(self):
        self.edit("guardrails.toml", 'terms = ["Tanager Routes", "Blue Heron Dispatch"]',
                  'terms = ["Tanager Routes", "Blue Heron Dispatch", "run"]')
        self.assertIn("C-PREFERRED-FORBIDDEN", self.ids())

    def test_an_approved_claim_that_uses_a_forbidden_term(self):
        self.edit("claims.toml", "Fernhill is built for courier firms", "Unlike Tanager Routes, Fernhill is built for courier firms")
        self.assertIn("C-CLAIM-FORBIDDEN-TERM", self.ids())

    def test_an_approved_claim_that_matches_a_forbidden_claim(self):
        self.edit("claims.toml", "Most new customers are dispatching", "With guaranteed on-time delivery, most new customers are dispatching")
        self.assertIn("C-CLAIM-FORBIDDEN-CLAIM", self.ids())

    def test_an_approved_claim_using_an_avoided_term(self):
        self.edit("claims.toml", "Most new customers are dispatching", "Most new customers switch seamlessly and are dispatching")
        self.assertNotIn("C-CLAIM-AVOIDED-TERM", self.ids())  # 'seamlessly' isn't the avoided word 'seamless'
        self.edit("claims.toml", "switch seamlessly", "have a seamless switch")
        self.assertIn("C-CLAIM-AVOIDED-TERM", self.ids())

    def test_testimonials_may_use_avoided_terms(self):
        self.edit("claims.toml", "We stopped reading addresses", "It was seamless. We stopped reading addresses")
        self.assertNotIn("C-CLAIM-AVOIDED-TERM", self.ids())

    def test_an_I_voice_with_a_no_first_person_rule(self):
        self.edit("voice.toml", 'mode = "company"\nname = ""\npronoun = "we"', 'mode = "author"\nname = "Sam"\npronoun = "I"')
        self.assertIn("C-SPEAKER-PRONOUN", self.ids())

    def test_em_dash_policy_against_the_samples(self):
        self.edit("voice/samples/call-ins.md", "The ones left are", "The ones left — the ones that matter — are")
        self.assertIn("C-EM-DASH-SAMPLES", self.ids())
        self.edit("voice.toml", 'em_dash = "avoid"', 'em_dash = "match_samples"')
        self.assertNotIn("C-EM-DASH-SAMPLES", self.ids())


if __name__ == "__main__":
    unittest.main()
