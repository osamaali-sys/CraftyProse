import contextlib
import io
import json
import unittest

from craftyprose.cli import main
from tests.helpers import EngineTestCase


class CliTest(EngineTestCase):
    def cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):  # argparse writes usage errors to stderr itself
            code = main(["--workspace", str(self.workspace), *args], out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_new_status_list_events(self):
        request = self.tmp / "request.md"
        request.write_text("Write a LinkedIn post about onboarding.", encoding="utf-8")
        code, out, _ = self.cli("new", str(request), "--brand", "northwind", "--type", "linkedin_post")
        self.assertEqual(code, 0)
        work_id = out.split()[1]
        code, out, _ = self.cli("status", work_id)
        self.assertEqual((code, json.loads(out)["stage"]), (0, "intake"))
        code, out, _ = self.cli("list")
        self.assertIn(work_id, out)
        self.assertIn("linkedin_post", out)
        code, out, _ = self.cli("events", work_id)
        self.assertEqual(json.loads(out)[0]["event"], "created")

    def test_usage_and_approval_after_a_run(self):
        engine = self.make_engine()
        work_id = self.new_item(engine)
        self.run_until(engine, work_id, "never")
        code, out, _ = self.cli("usage", work_id)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["llm"]["calls"], 6)
        code, out, _ = self.cli("approve", work_id, "--by", "Osama")
        self.assertEqual(code, 0)
        self.assertIn("approved by Osama", out)

    def test_refusals_and_usage_errors(self):
        code, _, err = self.cli("status", "W-20260925-001")
        self.assertEqual(code, 1)
        self.assertIn("no work item", err)
        engine = self.make_engine()
        work_id = self.new_item(engine)
        code, _, err = self.cli("approve", work_id, "--by", "Osama")
        self.assertEqual(code, 1)
        self.assertIn("ready for release", err)
        code, _, _ = self.cli("approve", work_id)  # --by is required
        self.assertEqual(code, 2)
        code, out, _ = self.cli("reject", work_id, "--by", "Osama", "--reason", "not needed")
        self.assertEqual((code, out.strip()), (0, f"{work_id} rejected"))


if __name__ == "__main__":
    unittest.main()
