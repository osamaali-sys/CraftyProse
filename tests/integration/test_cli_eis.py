import contextlib
import io
import shutil
import unittest

from craftyprose.cli import main
from tests.helpers import EXAMPLE_WORKSPACE, BrandTestCase


class CliEisTest(BrandTestCase):
    def cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["--workspace", str(self.workspace), *args], out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_types_lists_the_approved_specs(self):
        code, out, _ = self.cli("types")
        self.assertEqual(code, 0)
        for type_id in ("blog_article", "thought_leadership", "linkedin_post", "landing_page", "email_newsletter"):
            self.assertIn(type_id, out)

    def test_brand_check_passes_for_the_example(self):
        code, out, _ = self.cli("brand", "check", "fernhill")
        self.assertEqual(code, 0, out)
        self.assertIn("0 human-written", out)
        self.assertTrue(out.strip().endswith("ok"))

    def test_brand_check_reports_contradictions(self):
        self.edit("guardrails.toml", '"Blue Heron Dispatch"]', '"Blue Heron Dispatch", "dispatcher"]')
        code, out, _ = self.cli("brand", "check", "fernhill")
        self.assertEqual(code, 1)
        self.assertIn("contradiction C-PREFERRED-FORBIDDEN", out)

    def test_brand_init_scaffolds_files_that_must_be_filled_in(self):
        code, out, _ = self.cli("brand", "init", "newco")
        self.assertEqual(code, 0)
        root = self.workspace / "brands" / "newco"
        for name in ("brand.toml", "audiences.toml", "voice.toml", "claims.toml", "guardrails.toml", "open_questions.toml"):
            self.assertTrue((root / name).exists(), name)
        code, _, err = self.cli("brand", "check", "newco")
        self.assertEqual(code, 1)
        self.assertIn("brand.toml", err)
        self.assertIn("must not be empty", err)
        code, _, err = self.cli("brand", "init", "newco")
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)

    def test_new_checks_the_brand_and_type_first(self):
        request = self.tmp / "request.md"
        request.write_text("Write a post about reassigning runs.", encoding="utf-8")
        code, _, err = self.cli("new", str(request), "--brand", "fernhill", "--type", "podcast")
        self.assertEqual(code, 1)
        self.assertIn("unknown content type", err)
        code, _, err = self.cli("new", str(request), "--brand", "nobody", "--type", "linkedin_post")
        self.assertEqual(code, 1)
        self.assertIn("no brand workspace", err)
        self.assertFalse((self.workspace / "work").exists())  # nothing was created
        code, out, _ = self.cli("new", str(request), "--brand", "fernhill", "--type", "linkedin_post")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("created W-"))

    def test_the_example_workspace_itself_is_untouched_by_tests(self):
        self.assertFalse((EXAMPLE_WORKSPACE / "work").exists())
        self.assertFalse((EXAMPLE_WORKSPACE / "brands" / "newco").exists())


if __name__ == "__main__":
    unittest.main()
