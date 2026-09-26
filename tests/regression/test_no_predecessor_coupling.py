"""ER §14 D17 and §15: the predecessor hard-coded its agency, clients, regions and
vertical into the engine (clicksavvy.com, Phoenix, Dubai, HVAC terms). Nothing of
the kind may appear in the engine, its specs, its standards or the example brand.
The docs and the evidence probes discuss the predecessor and are not scanned."""
import re
import unittest

from tests.helpers import REPO_ROOT

FORBIDDEN = [
    r"click\s*savvy", r"clicksavvy", r"harmony\s*homes", r"harmonyhomes", r"metanous", r"hermes", r"aionui",
    r"\bdubai\b", r"\bdewa\b", r"\bejari\b", r"\bjvc\b", r"\bphoenix\b", r"\barcadia\b", r"\bacme\b",
    r"\brinnai\b", r"\btankless\b",
]
SCANNED = ["craftyprose", "examples"]
SUFFIXES = {".py", ".toml", ".md", ".jsonl", ".json"}


class NoPredecessorCouplingTest(unittest.TestCase):
    def test_engine_and_examples_carry_no_predecessor_identity(self):
        pattern = re.compile("|".join(FORBIDDEN), re.IGNORECASE)
        hits = []
        for folder in SCANNED:
            for path in (REPO_ROOT / folder).rglob("*"):
                if path.suffix in SUFFIXES and "__pycache__" not in path.parts:
                    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                        if pattern.search(line):
                            hits.append(f"{path.relative_to(REPO_ROOT)}:{n}: {line.strip()[:80]}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
