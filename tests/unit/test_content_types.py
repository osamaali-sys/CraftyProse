import shutil
import tempfile
import unittest
from pathlib import Path

from craftyprose.content_types.loader import SPECS_DIR, Catalog, ContentTypeError, load_spec

APPROVED_TYPES = {"blog_article", "thought_leadership", "linkedin_post", "landing_page", "email_newsletter"}


class ApprovedSpecsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = Catalog()

    def test_exactly_the_approved_types_ship(self):
        self.assertEqual(set(self.catalog.ids()), APPROVED_TYPES)

    def test_every_type_requires_human_approval(self):
        for ct in self.catalog.types.values():
            with self.subTest(ct.id):
                self.assertTrue(ct.approval_required)

    def test_every_type_uses_all_three_judges(self):
        for ct in self.catalog.types.values():
            with self.subTest(ct.id):
                self.assertEqual(set(ct.judges), {"evidence", "editorial", "writing"})

    def test_type_specific_shape(self):
        blog = self.catalog.get("blog_article")
        self.assertEqual((blog.length_unit, blog.length), ("words", (900, 1600)))
        self.assertTrue(blog.discoverability.enabled and blog.discoverability.primary_question_required)
        self.assertEqual(blog.anatomy.counts["body_sections"], (3, 7))
        self.assertEqual(blog.anatomy.intro_max_sentences, 3)
        self.assertEqual(blog.evidence.max_age("statistic"), 3)
        self.assertEqual(blog.evidence.max_age("third_party_fact"), 5)

        post = self.catalog.get("linkedin_post")
        self.assertEqual((post.length_unit, post.length), ("characters", (400, 2200)))
        self.assertFalse(post.discoverability.enabled)
        self.assertFalse(post.anatomy.headings)
        self.assertEqual((post.anatomy.hook_max_chars, post.writing_mode, post.release_format), (200, "shortform", "plain_text"))
        self.assertFalse(post.evidence.third_party_required)

        tl = self.catalog.get("thought_leadership")
        self.assertIn("counter_position", tl.anatomy.required)
        self.assertEqual(tl.writing_mode, "reference")

        page = self.catalog.get("landing_page")
        self.assertEqual(page.anatomy.counts["value_points"], (2, 6))  # never forced to exactly three
        self.assertIn("proof", page.anatomy.required)

        email = self.catalog.get("email_newsletter")
        self.assertEqual(email.anatomy.fields, {"subject": (25, 60), "preheader": (40, 110)})

    def test_unknown_type(self):
        with self.assertRaises(ContentTypeError):
            self.catalog.get("podcast_script")


class SpecValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-spec-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.base = (SPECS_DIR / "blog_article.toml").read_text(encoding="utf-8")

    def spec(self, text: str, name: str = "blog_article") -> Path:
        path = self.tmp / f"{name}.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def assert_invalid(self, text: str, fragment: str, name: str = "blog_article"):
        with self.assertRaises(ContentTypeError) as ctx:
            load_spec(self.spec(text, name))
        self.assertIn(fragment, str(ctx.exception))

    def test_the_base_spec_is_valid(self):
        load_spec(self.spec(self.base))

    def test_approval_cannot_be_turned_off(self):
        self.assert_invalid(self.base.replace("[approval]\nrequired = true", "[approval]\nrequired = false"),
                            "requires human approval")

    def test_id_must_match_file(self):
        self.assert_invalid(self.base, "must match the file name", name="blog_post")

    def test_unknown_keys(self):
        self.assert_invalid(self.base.replace("[review]\n", "[review]\nstrict = true\n"), "strict")
        self.assert_invalid(self.base + "\nseo_score_min = 90\n", "seo_score_min")

    def test_anatomy_rules(self):
        self.assert_invalid(self.base.replace('"cta"]', '"call_to_action"]'), "unknown value")
        self.assert_invalid(self.base.replace('optional = ["faq", "how_we_work"]', 'optional = ["faq", "cta"]'),
                            "both required and optional")
        self.assert_invalid(self.base.replace("faq = [3, 5]", "faq = [3, 5]\ntitle = [1, 1]"), "isn't a count element")
        self.assert_invalid(self.base.replace('optional = ["faq", "how_we_work"]', 'optional = ["how_we_work"]'),
                            "isn't in this type's anatomy")
        self.assert_invalid(self.base.replace("body_sections = [3, 7]", "body_sections = [7, 3]"), "min <= max")
        self.assert_invalid(self.base.replace('required = ["title", "answer_first_intro", "body_sections", "cta"]',
                                              'required = ["title", "body_sections", "cta"]'),
                            "needs an answer_first_intro")

    def test_review_release_and_evidence_rules(self):
        self.assert_invalid(self.base.replace('judges = ["evidence", "editorial", "writing"]', 'judges = ["seo"]'),
                            "unknown value")
        self.assert_invalid(self.base.replace('format = "markdown"', 'format = "plain_text"'), "can't use headings")
        self.assert_invalid(self.base.replace("statistic = 3\ndefault = 5", "statistic = 3"), "max_source_age_years.default")
        self.assert_invalid(self.base.replace('mode = "marketing"', 'mode = "detector_proof"'), "must be one of")

    def test_disabled_discoverability_takes_no_settings(self):
        text = self.base.replace("[discoverability]\nenabled = true", "[discoverability]\nenabled = false")
        self.assert_invalid(text, "unknown key")


if __name__ == "__main__":
    unittest.main()
