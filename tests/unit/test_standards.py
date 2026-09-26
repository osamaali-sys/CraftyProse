import re
import shutil
import tempfile
import unittest
from pathlib import Path

from craftyprose.core.findings import PATTERN_CATEGORIES, PATTERN_ID_RE
from craftyprose.eis.guardrails import FORBIDDEN_CLAIM_PATTERN, OPEN_QUESTION_PATTERN, PATTERN_FOR_RULE
from craftyprose.eis.standards import JUDGE_FOR_PREFIX, StandardsError, library, load_library, principles
from tests.helpers import REPO_ROOT

ID_LITERAL = re.compile(r"[\"'](%s)-[A-Z0-9]+(?:-[A-Z0-9]+)*[\"']" % "|".join(PATTERN_CATEGORIES))


class LibraryTest(unittest.TestCase):
    def test_library_loads_with_valid_ids(self):
        lib = library()
        self.assertGreater(len(lib.patterns), 50)
        for p in lib.patterns.values():
            with self.subTest(p.id):
                self.assertRegex(p.id, PATTERN_ID_RE)
                self.assertTrue(p.definition and p.remediation)

    def test_every_judge_has_a_jurisdiction(self):
        lib = library()
        for judge in set(JUDGE_FOR_PREFIX.values()):
            with self.subTest(judge):
                patterns = lib.for_judge(judge)
                self.assertTrue(patterns)
                self.assertTrue(all(JUDGE_FOR_PREFIX[p.prefix] == judge for p in patterns))

    def test_structure_patterns_are_deterministic_only(self):
        for p in library().patterns.values():
            if p.prefix == "ST":
                self.assertEqual(p.detectors, ("deterministic",))

    def test_every_pattern_id_the_code_uses_exists(self):
        lib = library()
        used = set(PATTERN_FOR_RULE.values()) | {FORBIDDEN_CLAIM_PATTERN, OPEN_QUESTION_PATTERN}
        for path in (REPO_ROOT / "craftyprose").rglob("*.py"):
            used |= {m.group(0).strip("\"'") for m in ID_LITERAL.finditer(path.read_text(encoding="utf-8"))}
        missing = sorted(i for i in used if i not in lib.patterns)
        self.assertEqual(missing, [])

    def test_principles_rank_truth_first(self):
        text = principles()
        self.assertLess(text.index("**Truth.**"), text.index("**Discoverability.**"))


class LibraryValidationTest(unittest.TestCase):
    """Lineage A's library reused IDs (FP-0503, FP-0703 and FP-1003 each appeared twice)."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="craftyprose-std-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def lib(self, body: str):
        path = self.tmp / "patterns.toml"
        path.write_text('version = "t"\n' + body, encoding="utf-8")
        return load_library(path)

    ENTRY = ('[[patterns]]\nid = "{id}"\nname = "n"\nseverity = "major"\ndetectors = [{det}]\n'
             'definition = "d"\nremediation = "r"\n')

    def test_duplicate_ids_are_rejected(self):
        entry = self.ENTRY.format(id="ED-THIN", det='"judge"')
        with self.assertRaises(StandardsError):
            self.lib(entry + entry)

    def test_bad_prefix_and_judge_on_structure(self):
        with self.assertRaises(StandardsError):
            self.lib(self.ENTRY.format(id="FP-0101", det='"judge"'))
        with self.assertRaises(StandardsError):
            self.lib(self.ENTRY.format(id="ST-THING", det='"judge"'))


if __name__ == "__main__":
    unittest.main()
