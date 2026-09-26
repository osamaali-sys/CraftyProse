import unittest

from craftyprose.core.findings import ENGINE_OWNED_KEYS, Finding, FindingError, Location, verdict_of


def data(**overrides):
    base = {
        "pattern_id": "EV-UNCITED-CLAIM",
        "severity": "major",
        "problem": "The statistic has no evidence.",
        "required_correction": "Cite the claim or remove it.",
        "location": {"section": "Why it matters", "quote": "41% of buyers"},
    }
    base.update(overrides)
    return base


class FindingParseTest(unittest.TestCase):
    def test_valid_finding_parses_with_engine_source(self):
        f = Finding.from_dict(data(), source="judge:evidence")
        self.assertEqual(f.source, "judge:evidence")
        self.assertTrue(f.blocking)
        self.assertEqual(f.to_dict()["fingerprint"], f.fingerprint)

    def test_engine_owned_fields_are_rejected(self):
        for key in sorted(ENGINE_OWNED_KEYS):
            with self.subTest(key=key), self.assertRaises(FindingError) as ctx:
                Finding.from_dict(data(**{key: True}), source="judge:evidence")
            self.assertIn("engine-owned", str(ctx.exception))

    def test_unknown_fields_are_rejected(self):
        with self.assertRaises(FindingError):
            Finding.from_dict(data(confidence=0.9), source="judge:evidence")
        with self.assertRaises(FindingError):
            Finding.from_dict(data(location={"section": "x", "line": 3}), source="judge:evidence")

    def test_malformed_values_are_rejected(self):
        cases = {
            "bad severity": data(severity="blocker"),
            "bad pattern prefix": data(pattern_id="XX-THING"),
            "lowercase pattern": data(pattern_id="ev-uncited"),
            "empty problem": data(problem="  "),
            "empty correction": data(required_correction=""),
            "non-boolean flag": data(requires_new_evidence="yes"),
            "location not an object": data(location="Intro"),
        }
        for label, value in cases.items():
            with self.subTest(label), self.assertRaises(FindingError):
                Finding.from_dict(value, source="judge:evidence")
        with self.assertRaises(FindingError):
            Finding.from_dict(["not", "an", "object"], source="judge:evidence")

    def test_source_is_required(self):
        with self.assertRaises(FindingError):
            Finding.from_dict(data(), source="")


class FingerprintTest(unittest.TestCase):
    def test_fingerprint_ignores_whitespace_case_and_quote_style(self):
        a = Finding.from_dict(data(location={"section": "Intro", "quote": "It’s  the\nbest"}), source="judge:e")
        b = Finding.from_dict(data(location={"section": " intro ", "quote": "it's the best"}), source="judge:writing")
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_fingerprint_changes_with_pattern_or_quote(self):
        base = Finding.from_dict(data(), source="judge:e")
        self.assertNotEqual(base.fingerprint, Finding.from_dict(data(pattern_id="EV-OVERSTATEMENT"), source="judge:e").fingerprint)
        self.assertNotEqual(base.fingerprint,
                            Finding.from_dict(data(location={"section": "Why it matters", "quote": "42%"}), source="judge:e").fingerprint)


class VerdictTest(unittest.TestCase):
    def make(self, severity):
        return Finding("ED-THIN", severity, "judge:editorial", "thin", "add substance", Location())

    def test_verdict_is_computed_from_severities(self):
        self.assertEqual(verdict_of([]), "pass")
        self.assertEqual(verdict_of([self.make("minor"), self.make("minor")]), "pass")
        self.assertEqual(verdict_of([self.make("minor"), self.make("major")]), "fail")
        self.assertEqual(verdict_of([self.make("critical")]), "fail")


if __name__ == "__main__":
    unittest.main()
