import datetime as dt
import unittest

from craftyprose.content_types.loader import Catalog
from craftyprose.eis.context import ROLES, SLICES, build_slice
from tests.helpers import AS_OF, BrandTestCase


class ContextSliceTest(BrandTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.catalog = Catalog()
        self.blog = self.catalog.get("blog_article")

    def slice(self, role, ws=None, as_of=AS_OF, ct=None):
        return build_slice(ws or self.load(), role, ct or self.blog, as_of=as_of)

    @staticmethod
    def text(s) -> str:
        return "\n".join(b.text for b in s.blocks)

    def test_every_role_has_a_declared_slice(self):
        self.assertEqual(set(SLICES), set(ROLES))
        for role in ROLES:
            s = self.slice(role)
            self.assertEqual([b.name for b in s.blocks], [f"eis/{p}" for p in SLICES[role]])
            self.assertTrue(all(b.cacheable for b in s.blocks))

    def test_the_writing_judge_never_sees_claims_or_guardrails(self):
        text = self.text(self.slice("judge_writing"))
        self.assertIn("Fewer call-ins", text)  # voice samples
        self.assertNotIn("support answers the phone", text)
        self.assertNotIn("Guardrails", text)

    def test_the_evidence_judge_never_sees_voice_samples(self):
        text = self.text(self.slice("judge_evidence"))
        self.assertIn("support answers the phone", text)
        self.assertNotIn("Fewer call-ins", text)
        self.assertNotIn("Before and after", text)

    def test_judges_see_only_their_own_patterns(self):
        writing = self.text(self.slice("judge_writing"))
        self.assertIn("HW-CONTRAST-FRAME", writing)
        self.assertNotIn("EV-UNSUPPORTED-CLAIM", writing)
        evidence = self.text(self.slice("judge_evidence"))
        self.assertIn("EV-UNSUPPORTED-CLAIM", evidence)
        self.assertIn("RK-UNLICENSED-ADVICE", evidence)
        self.assertNotIn("HW-", evidence)

    def test_expired_claims_are_left_out_and_counted(self):
        text = self.text(self.slice("writer"))
        self.assertNotIn("spreadsheet migration", text)
        self.assertIn("1 approved claim(s) are expired or not yet valid", text)
        earlier = self.text(self.slice("writer", as_of=dt.date(2026, 5, 1)))
        self.assertIn("spreadsheet migration", earlier)

    def test_slices_are_deterministic(self):
        self.assertEqual(self.slice("writer").sha256, self.slice("writer").sha256)

    def test_a_voice_change_only_changes_slices_that_include_voice(self):
        before = {role: self.slice(role).sha256 for role in ROLES}
        self.edit("voice.toml", '"calm"', '"calm", "wry"')
        after = {role: self.slice(role).sha256 for role in ROLES}
        changed = {r for r in ROLES if before[r] != after[r]}
        self.assertEqual(changed, {"writer", "judge_writing", "strategist"})

    def test_content_type_is_part_of_every_slice(self):
        post = self.catalog.get("linkedin_post")
        for role in ROLES:
            with self.subTest(role):
                self.assertNotEqual(self.slice(role).sha256, self.slice(role, ct=post).sha256)
        self.assertIn("hook at most 200 characters", self.text(self.slice("writer", ct=post)))

    def test_unknown_role(self):
        with self.assertRaises(ValueError):
            self.slice("editor_in_chief")


if __name__ == "__main__":
    unittest.main()
