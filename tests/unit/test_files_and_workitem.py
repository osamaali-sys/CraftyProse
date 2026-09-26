import shutil
import socket
import tempfile
import unittest
from pathlib import Path

from craftyprose.core.files import normalize_newlines, read_json, sha256_text, write_json_atomic, write_text_atomic
from craftyprose.core.workitem import WorkItem
from tests import NetworkAccessError


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-unit-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class AtomicWriteTest(TempDirCase):
    def test_write_replaces_content_and_leaves_no_temp_files(self):
        path = self.tmp / "a" / "file.txt"
        write_text_atomic(path, "one")
        write_text_atomic(path, "two")
        self.assertEqual(path.read_text(encoding="utf-8"), "two")
        self.assertEqual([p.name for p in path.parent.iterdir()], ["file.txt"])

    def test_json_round_trip(self):
        path = self.tmp / "data.json"
        write_json_atomic(path, {"b": 1, "a": "é"})
        self.assertEqual(read_json(path), {"b": 1, "a": "é"})

    def test_newlines_are_normalized_so_hashes_are_platform_independent(self):
        self.assertEqual(normalize_newlines("a\r\nb\rc"), "a\nb\nc")
        self.assertEqual(sha256_text(normalize_newlines("x\r\ny")), sha256_text("x\ny"))


class WorkItemTest(TempDirCase):
    def setUp(self) -> None:
        super().setUp()
        self.item = WorkItem(self.tmp / "W-20260925-001")

    def test_versions_sort_numerically(self):
        for i in range(11):
            self.item.put_submission("draft", "markdown", f"version {i + 1}")
        folder = self.item.root / "submissions" / "draft"
        self.assertEqual(WorkItem.latest_version(folder, "draft", "md"), 11)
        self.assertEqual(self.item.read_submission("draft", "markdown", 10), "version 10")

    def test_new_versions_never_touch_earlier_ones(self):
        first = self.item.put_submission("intake", "json", '{"n": 1}')
        self.item.put_submission("intake", "json", '{"n": 2}')
        self.assertEqual(first.path.read_text(encoding="utf-8"), '{"n": 1}')
        self.assertEqual(first.version, 1)

    def test_submission_is_stored_with_normalized_newlines_and_hash(self):
        ref = self.item.put_submission("draft", "markdown", "# T\r\n\r\nBody\r\n")
        self.assertEqual(ref.path.read_bytes(), b"# T\n\nBody\n")
        self.assertEqual(ref.sha256, sha256_text("# T\n\nBody\n"))

    def test_validation_records_are_write_once(self):
        self.item.record_validation("intake", 1, {"passed": True})
        with self.assertRaises(FileExistsError):
            self.item.record_validation("intake", 1, {"passed": False})

    def test_human_inputs_are_kept_in_order(self):
        self.item.put_human_input("first\n")
        self.item.put_human_input("second\n")
        self.assertEqual(self.item.human_inputs(), ["first\n", "second\n"])


class NetworkGuardTest(unittest.TestCase):
    def test_the_suite_cannot_open_network_connections(self):
        with self.assertRaises(NetworkAccessError):
            socket.create_connection(("example.com", 80))
        with socket.socket() as s, self.assertRaises(NetworkAccessError):
            s.connect(("example.com", 80))


if __name__ == "__main__":
    unittest.main()
