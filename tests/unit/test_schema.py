import datetime as dt
import unittest

from craftyprose.core.schema import SchemaError, Table


class TableTest(unittest.TestCase):
    def test_reads_typed_values(self):
        t = Table({"s": " x ", "b": True, "i": 3, "f": 0.5, "l": ["a", "b"], "r": [1, 4], "d": "2026-09-26",
                   "u": "https://a.example/x"}, "f.toml")
        self.assertEqual(t.str("s"), "x")
        self.assertTrue(t.bool("b"))
        self.assertEqual(t.int("i", minimum=1), 3)
        self.assertEqual(t.float("f", minimum=0, maximum=1), 0.5)
        self.assertEqual(t.str_list("l"), ("a", "b"))
        self.assertEqual(t.range("r"), (1, 4))
        self.assertEqual(t.date("d"), dt.date(2026, 9, 26))
        self.assertEqual(t.url("u"), "https://a.example/x")
        t.finish()

    def test_unknown_keys_are_errors_naming_the_file(self):
        t = Table({"name": "x", "nmae": "y"}, "brand.toml")
        t.str("name")
        with self.assertRaises(SchemaError) as ctx:
            t.finish()
        self.assertIn("brand.toml", str(ctx.exception))
        self.assertIn("nmae", str(ctx.exception))

    def test_errors_name_the_key(self):
        cases = [
            (lambda t: t.str("missing"), "is required"),
            (lambda t: t.str("empty"), "must not be empty"),
            (lambda t: t.str("s", choices=("a", "b")), "must be one of"),
            (lambda t: t.bool("s"), "true or false"),
            (lambda t: t.int("s"), "integer"),
            (lambda t: t.str_list("dupes"), "duplicate"),
            (lambda t: t.str_list("l", choices=("a",)), "unknown value"),
            (lambda t: t.range("bad_range"), "min <= max"),
            (lambda t: t.range("l"), "[min, max]"),
            (lambda t: t.date("s"), "date"),
            (lambda t: t.url("s"), "http(s) URL"),
            (lambda t: t.tables("s"), "array of tables"),
        ]
        for read, message in cases:
            t = Table({"empty": " ", "s": "c", "dupes": ["a", "a"], "l": ["a", "b"], "bad_range": [5, 2]}, "x.toml")
            with self.subTest(message), self.assertRaises(SchemaError) as ctx:
                read(t)
            self.assertIn(message, str(ctx.exception))

    def test_nested_tables_report_their_path(self):
        t = Table({"items": [{"id": "a"}, {"id": ""}]}, "claims.toml")
        rows = t.tables("items")
        rows[0].str("id")
        with self.assertRaises(SchemaError) as ctx:
            rows[1].str("id")
        self.assertIn("claims.toml.items[1]", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
