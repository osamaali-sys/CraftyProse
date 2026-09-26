import unittest

from craftyprose.core.validation import GateResult, ValidationResult


class ValidationResultTest(unittest.TestCase):
    def test_blocking_failure_fails_advisory_failure_does_not(self):
        r = ValidationResult("v").add("ok", True).add("advice", False, "consider X", blocking=False)
        self.assertTrue(r.passed)
        self.assertEqual([c.name for c in r.advisories], ["advice"])
        r.add("hard", False, "broken")
        self.assertFalse(r.passed)
        self.assertEqual([c.name for c in r.failures], ["hard"])

    def test_add_returns_self_so_checks_chain(self):
        # The predecessor's add() returned None, which broke a failure path.
        r = ValidationResult("v")
        self.assertIs(r.add("a", True), r)

    def test_empty_result_passes(self):
        self.assertTrue(ValidationResult("v").passed)

    def test_checks_carry_pattern_and_location(self):
        r = ValidationResult("v").add("uncited", False, "no marker", pattern_id="EV-UNCITED-CLAIM", location="Intro")
        c = r.failures[0]
        self.assertEqual((c.pattern_id, c.location), ("EV-UNCITED-CLAIM", "Intro"))


class GateResultTest(unittest.TestCase):
    def test_aggregates_and_round_trips(self):
        a = ValidationResult("a").add("x", True).add("y", False, blocking=False)
        b = ValidationResult("b").add("z", False, "bad")
        gate = GateResult("draft", 2, [a, b])
        self.assertFalse(gate.passed)
        self.assertEqual([c.name for c in gate.failures], ["z"])
        self.assertEqual([c.name for c in gate.advisories], ["y"])
        again = GateResult.from_dict(gate.to_dict())
        self.assertEqual(again.to_dict(), gate.to_dict())


if __name__ == "__main__":
    unittest.main()
