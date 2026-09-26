import datetime as dt
import unittest

from craftyprose.eis.workspace import EISError, list_brands, load_brand
from tests.helpers import AS_OF, BrandTestCase

SAMPLE_HEADER = """+++
title = "A sample"
author = "Someone"
source = "Somewhere"
human_written = {human}
how_known = "{how}"
rights = "{rights}"
license = "{license}"
added_by = "Tester"
added_on = 2026-09-26
+++
{body}
"""


def sample(body="Text.", human="false", how="", rights="synthetic", license=""):
    return SAMPLE_HEADER.format(body=body, human=human, how=how, rights=rights, license=license)


class ExampleBrandTest(BrandTestCase):
    def test_the_example_brand_loads(self):
        ws = self.load()
        self.assertEqual(ws.brand.name, "Fernhill")
        self.assertEqual([p.id for p in ws.personas], ["dispatcher", "owner"])
        self.assertEqual(ws.voice.speaker.pronoun, "we")
        self.assertEqual({s.name for s in ws.samples}, {"first-hour", "call-ins"})
        self.assertEqual(ws.pairs[0].title, "Reassigning a run")
        self.assertIn("In today's fast-paced", ws.pairs[0].before)
        self.assertEqual(len(ws.rules), 5)
        self.assertEqual([q.id for q in ws.open()], ["tms-integrations"])
        self.assertEqual(ws.content_log[0].date, dt.date(2026, 8, 14))
        self.assertEqual(list_brands(self.workspace), ["fernhill"])

    def test_example_samples_are_marked_synthetic_not_human(self):
        ws = self.load()
        self.assertFalse(ws.has_human_samples)
        self.assertTrue(all(s.provenance.rights == "synthetic" for s in ws.samples))

    def test_expired_claims_are_not_usable(self):
        ws = self.load()
        usable = [c.id for c in ws.usable_claims(AS_OF)]
        self.assertNotIn("spring-migration-offer", usable)  # expired 2026-06-30
        self.assertIn("go-live-time", usable)
        self.assertNotIn("go-live-time", [c.id for c in ws.usable_claims(dt.date(2027, 3, 2))])
        self.assertEqual([c.id for c in ws.usable_claims(dt.date(2026, 5, 1))], ["spring-migration-offer"])


class MissingPiecesTest(BrandTestCase):
    def test_missing_brand_names_the_path(self):
        with self.assertRaises(EISError) as ctx:
            load_brand(self.workspace, "nobody")
        self.assertIn("brands", str(ctx.exception))
        self.assertIn("nobody", str(ctx.exception))

    def test_missing_required_files_are_listed(self):
        (self.brand_root / "voice.toml").unlink()
        (self.brand_root / "audiences.toml").unlink()
        with self.assertRaises(EISError) as ctx:
            self.load()
        message = str(ctx.exception)
        self.assertIn("voice.toml", message)
        self.assertIn("audiences.toml", message)

    def test_optional_files_can_be_absent(self):
        for name in ("claims.toml", "guardrails.toml", "open_questions.toml", "content_log.jsonl"):
            (self.brand_root / name).unlink()
        ws = self.load()
        self.assertEqual((ws.approved_claims, ws.rules, ws.open_questions, ws.content_log), ((), (), (), ()))

    def test_bad_brand_ids(self):
        for bad in ("Fernhill", "../x", ""):
            with self.subTest(bad=bad), self.assertRaises(EISError):
                load_brand(self.workspace, bad)


class ValidationTest(BrandTestCase):
    def assert_load_fails(self, *fragments):
        with self.assertRaises(EISError) as ctx:
            self.load()
        for fragment in fragments:
            self.assertIn(fragment, str(ctx.exception))

    def test_id_must_match_the_directory(self):
        self.edit("brand.toml", 'id = "fernhill"', 'id = "fernhill-co"')
        self.assert_load_fails("doesn't match the directory")

    def test_unknown_keys_name_file_and_key(self):
        self.append("brand.toml", '\ntagline = "x"\n')
        self.assert_load_fails("brand.toml", "tagline")

    def test_bad_url(self):
        self.edit("brand.toml", 'url = "https://fernhill.example/driver-app"', 'url = "fernhill.example/driver-app"')
        self.assert_load_fails("http(s) URL")

    def test_voice_rules(self):
        self.edit("voice.toml", 'pronoun = "we"', 'pronoun = "I"')
        self.assert_load_fails("company voice speaks as 'we'")

    def test_author_voice_needs_a_name(self):
        self.edit("voice.toml", 'mode = "company"', 'mode = "author"')
        self.assert_load_fails("author's name")

    def test_testimonial_needs_attribution(self):
        self.edit("claims.toml", 'attribution = "Dana R., dispatcher at a regional courier (fictional)"', 'attribution = ""')
        self.assert_load_fails("attribution")

    def test_claim_dates(self):
        self.edit("claims.toml", "expires_on = 2027-03-01", "expires_on = 2026-01-01")
        self.assert_load_fails("before approved_on")

    def test_duplicate_ids(self):
        self.edit("claims.toml", 'id = "fleet-size"', 'id = "support-hours"')
        self.assert_load_fails("duplicate id 'support-hours'")

    def test_guardrail_fields_must_fit_the_type(self):
        self.append("guardrails.toml", '\n[[rules]]\nid = "x"\ntype = "forbidden_term"\nterms = ["a"]\n'
                                       'pattern = "b"\nmessage = "m"\n')
        self.assert_load_fails("don't apply to a forbidden_term rule")

    def test_guardrail_regex_must_compile(self):
        self.edit("guardrails.toml", "pattern = '", "pattern = '(unclosed")
        self.assert_load_fails("invalid regular expression")

    def test_guardrail_scope_must_name_real_content_types(self):
        self.append("guardrails.toml", '\n[[rules]]\nid = "x"\ntype = "banned_topic"\nterms = ["a"]\n'
                                       'message = "m"\napplies_to = ["podcast"]\n')
        self.assert_load_fails("unknown content type", "podcast")

    def test_content_log_lines_are_validated(self):
        self.append("content_log.jsonl", "{not json}\n")
        self.assert_load_fails("content_log.jsonl:2", "invalid JSON")

    def test_voice_pair_needs_both_sections(self):
        self.write("voice/pairs/broken.md", sample(body="## Before\n\nOnly before."))
        self.assert_load_fails("'## Before' and '## After'")


class ProvenanceTest(BrandTestCase):
    def test_synthetic_text_cannot_claim_to_be_human(self):
        self.write("voice/samples/x.md", sample(human="true", how="I say so", rights="synthetic"))
        with self.assertRaises(EISError) as ctx:
            self.load()
        self.assertIn("synthetic text can't be marked human_written", str(ctx.exception))

    def test_human_samples_must_say_how_that_is_known(self):
        self.write("voice/samples/x.md", sample(human="true", how="", rights="owned"))
        with self.assertRaises(EISError) as ctx:
            self.load()
        self.assertIn("how_known", str(ctx.exception))

    def test_licensed_samples_name_the_license(self):
        self.write("voice/samples/x.md", sample(human="true", how="Published by the author in 2019", rights="licensed"))
        with self.assertRaises(EISError) as ctx:
            self.load()
        self.assertIn("name the license", str(ctx.exception))

    def test_a_verified_human_sample_is_recognized(self):
        self.write("voice/samples/x.md", sample(human="true", how="Written by the founder in 2020; original on file",
                                                rights="owned"))
        self.assertTrue(self.load().has_human_samples)

    def test_front_matter_is_required(self):
        self.write("voice/samples/x.md", "Just text, no provenance.\n")
        with self.assertRaises(EISError) as ctx:
            self.load()
        self.assertIn("front-matter", str(ctx.exception))

    def test_unknown_rights_value(self):
        self.write("voice/samples/x.md", sample(rights="scraped"))
        with self.assertRaises(EISError) as ctx:
            self.load()
        self.assertIn("rights", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
