"""The brand workspace: EIS context and permission (architecture §3.2).

    <workspace>/brands/<brand_id>/
      brand.toml            required: identity, positioning, locale, offerings, linkable pages
      audiences.toml        required: personas
      voice.toml            required: speaker, register, rules, lexicon, punctuation, style
      voice/samples/*.md    approved writing samples with provenance (they outrank style rules)
      voice/pairs/*.md      before/after rewrites that show the voice
      claims.toml           approved first-party claims and forbidden claims
      guardrails.toml       hard rules, compiled to deterministic checks
      open_questions.toml   unresolved facts; topics that depend on them are blocked
      content_log.jsonl     what has been released, to avoid repetition

A missing required file is an error naming its path: the engine stops and says
so rather than writing from memory (lineage C, ER §13 P9).
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..core.files import normalize_newlines
from ..core.schema import SchemaError, Table, load_toml, unique_ids
from .provenance import Provenance, TextSample, read_sample

BRAND_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
REQUIRED_FILES = ("brand.toml", "audiences.toml", "voice.toml")
CLAIM_KINDS = ("first_party_fact", "marketing_claim", "testimonial")
RULE_TYPES = ("forbidden_term", "forbidden_pattern", "banned_topic", "required_disclosure", "speaker_policy")
SPEAKER_POLICIES = ("no_first_person_singular",)
RULE_SEVERITIES = ("critical", "major")


class EISError(SchemaError):
    """The brand workspace is missing, incomplete or invalid."""


# --------------------------------------------------------------------- model
@dataclass(frozen=True)
class Offering:
    id: str
    name: str
    summary: str
    url: str


@dataclass(frozen=True)
class LinkablePage:
    url: str
    title: str
    topics: tuple[str, ...]


@dataclass(frozen=True)
class Brand:
    id: str
    name: str
    description: str
    positioning: str
    locale: str
    markets: tuple[str, ...]
    offerings: tuple[Offering, ...]
    linkable_pages: tuple[LinkablePage, ...]


@dataclass(frozen=True)
class Persona:
    id: str
    who: str
    sophistication: str
    problems: tuple[str, ...]
    questions: tuple[str, ...]
    objections: tuple[str, ...]
    vocabulary: tuple[str, ...]


@dataclass(frozen=True)
class LexiconEntry:
    term: str
    reason: str
    instead_of: tuple[str, ...] = ()
    alternative: str = ""


@dataclass(frozen=True)
class Speaker:
    mode: str  # company | author
    name: str
    pronoun: str  # we | I


@dataclass(frozen=True)
class Voice:
    register: str
    personality: tuple[str, ...]
    rules: tuple[str, ...]
    speaker: Speaker
    prefer: tuple[LexiconEntry, ...]
    avoid: tuple[LexiconEntry, ...]
    em_dash: str  # avoid | allow | match_samples
    spelling: str
    headings: str  # sentence | title


@dataclass(frozen=True)
class VoicePair:
    name: str
    title: str
    before: str
    after: str
    provenance: Provenance


@dataclass(frozen=True)
class ApprovedClaim:
    id: str
    kind: str
    statement: str
    source: str
    approved_by: str
    approved_on: dt.date
    expires_on: dt.date | None
    attribution: str
    allowed_phrasings: tuple[str, ...]

    def usable_on(self, day: dt.date) -> bool:
        return self.approved_on <= day and (self.expires_on is None or day <= self.expires_on)


@dataclass(frozen=True)
class ForbiddenClaim:
    id: str
    match: str  # phrase | regex
    pattern: str
    reason: str


@dataclass(frozen=True)
class GuardrailRule:
    id: str
    type: str
    message: str
    severity: str
    applies_to: tuple[str, ...]
    terms: tuple[str, ...] = ()
    pattern: str = ""
    triggers: tuple[str, ...] = ()
    disclosure: str = ""
    policy: str = ""

    def applies(self, content_type: str) -> bool:
        return not self.applies_to or content_type in self.applies_to


@dataclass(frozen=True)
class OpenQuestion:
    id: str
    question: str
    blocks_topics: tuple[str, ...]
    status: str  # open | resolved


@dataclass(frozen=True)
class PublishedItem:
    date: dt.date
    work_id: str
    content_type: str
    title: str
    primary_question: str
    topics: tuple[str, ...]
    url: str


@dataclass(frozen=True)
class BrandWorkspace:
    root: Path
    brand: Brand
    personas: tuple[Persona, ...]
    voice: Voice
    samples: tuple[TextSample, ...]
    pairs: tuple[VoicePair, ...]
    approved_claims: tuple[ApprovedClaim, ...]
    forbidden_claims: tuple[ForbiddenClaim, ...]
    rules: tuple[GuardrailRule, ...]
    open_questions: tuple[OpenQuestion, ...]
    content_log: tuple[PublishedItem, ...]

    def usable_claims(self, day: dt.date) -> tuple[ApprovedClaim, ...]:
        return tuple(c for c in self.approved_claims if c.usable_on(day))

    def open(self) -> tuple[OpenQuestion, ...]:
        return tuple(q for q in self.open_questions if q.status == "open")

    @property
    def has_human_samples(self) -> bool:
        return any(s.provenance.human_written for s in self.samples)


# ------------------------------------------------------------------- loading
def brand_dir(workspace: Path, brand_id: str) -> Path:
    return Path(workspace) / "brands" / brand_id


def list_brands(workspace: Path) -> list[str]:
    root = Path(workspace) / "brands"
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and BRAND_ID_RE.match(p.name))


def load_brand(workspace: Path, brand_id: str, *, content_types: Iterable[str] | None = None) -> BrandWorkspace:
    """Load and validate a brand workspace. Raises ``EISError`` with the exact path on any problem."""
    if not BRAND_ID_RE.match(brand_id or ""):
        raise EISError(f"brand id must be a lowercase slug, got {brand_id!r}")
    root = brand_dir(workspace, brand_id)
    if not root.is_dir():
        raise EISError(f"no brand workspace at {root}")
    missing = [str(root / f) for f in REQUIRED_FILES if not (root / f).is_file()]
    if missing:
        raise EISError(f"brand workspace is missing required file(s): {', '.join(missing)}")
    try:
        brand = _brand(load_toml(root / "brand.toml"), brand_id)
        personas = _personas(load_toml(root / "audiences.toml"))
        voice = _voice(load_toml(root / "voice.toml"))
        samples = tuple(read_sample(p) for p in sorted((root / "voice" / "samples").glob("*.md")))
        pairs = tuple(_pair(p) for p in sorted((root / "voice" / "pairs").glob("*.md")))
        approved, forbidden = _claims(root / "claims.toml")
        rules = _rules(root / "guardrails.toml")
        questions = _questions(root / "open_questions.toml")
        log = _content_log(root / "content_log.jsonl")
    except EISError:
        raise
    except SchemaError as exc:
        raise EISError(str(exc)) from exc
    if content_types is not None:
        known = set(content_types)
        for rule in rules:
            unknown = sorted(set(rule.applies_to) - known)
            if unknown:
                raise EISError(f"{root / 'guardrails.toml'}: rule {rule.id!r} applies_to unknown content type(s) {unknown}")
    return BrandWorkspace(root, brand, personas, voice, samples, pairs, approved, forbidden, rules, questions, log)


def _brand(t: Table, brand_id: str) -> Brand:
    declared = t.str("id")
    if declared != brand_id:
        raise EISError(f"{t.where}: id {declared!r} doesn't match the directory name {brand_id!r}")
    offerings = []
    for o in t.tables("offerings"):
        offerings.append(Offering(o.str("id"), o.str("name"), o.str("summary"), o.url("url", required=False)))
        o.finish()
    pages = []
    for p in t.tables("linkable_pages"):
        pages.append(LinkablePage(p.url("url"), p.str("title"), p.str_list("topics")))
        p.finish()
    brand = Brand(declared, t.str("name"), t.str("description"), t.str("positioning"), t.str("locale"),
                  t.str_list("markets", required=True, nonempty=True), tuple(offerings), tuple(pages))
    t.finish()
    unique_ids(brand.offerings, f"{t.where} offerings")
    unique_ids(brand.linkable_pages, f"{t.where} linkable_pages", attr="url")
    return brand


def _personas(t: Table) -> tuple[Persona, ...]:
    personas = []
    for p in t.tables("personas"):
        personas.append(Persona(
            id=p.str("id"), who=p.str("who"),
            sophistication=p.str("sophistication", choices=("novice", "practitioner", "expert")),
            problems=p.str_list("problems", required=True, nonempty=True),
            questions=p.str_list("questions"), objections=p.str_list("objections"),
            vocabulary=p.str_list("vocabulary"),
        ))
        p.finish()
    t.finish()
    if not personas:
        raise EISError(f"{t.where}: define at least one [[personas]] entry")
    unique_ids(personas, f"{t.where} personas")
    return tuple(personas)


def _voice(t: Table) -> Voice:
    s = t.table("speaker", required=True)
    speaker = Speaker(s.str("mode", choices=("company", "author")), s.str("name", required=False, nonempty=False),
                      s.str("pronoun", choices=("we", "I")))
    s.finish()
    if speaker.mode == "author" and not speaker.name:
        raise EISError(f"{s.where}: an author voice needs the author's name")
    if speaker.mode == "company" and speaker.pronoun != "we":
        raise EISError(f"{s.where}: a company voice speaks as 'we'")
    lex = t.table("lexicon")
    prefer = []
    for e in lex.tables("prefer"):
        prefer.append(LexiconEntry(e.str("term"), e.str("reason"), instead_of=e.str_list("instead_of")))
        e.finish()
    avoid = []
    for e in lex.tables("avoid"):
        avoid.append(LexiconEntry(e.str("term"), e.str("reason"),
                                  alternative=e.str("alternative", required=False, nonempty=False)))
        e.finish()
    lex.finish()
    punct = t.table("punctuation")
    em_dash = punct.str("em_dash", required=False, default="allow", choices=("avoid", "allow", "match_samples"))
    punct.finish()
    style = t.table("style", required=True)
    spelling = style.str("spelling", choices=("en-US", "en-GB", "en-AU", "en-CA"))
    headings = style.str("headings", required=False, default="sentence", choices=("sentence", "title"))
    style.finish()
    voice = Voice(t.str("register"), t.str_list("personality", required=True, nonempty=True), t.str_list("rules"),
                  speaker, tuple(prefer), tuple(avoid), em_dash, spelling, headings)
    t.finish()
    unique_ids(voice.prefer, f"{t.where} lexicon.prefer", attr="term")
    unique_ids(voice.avoid, f"{t.where} lexicon.avoid", attr="term")
    return voice


def _pair(path: Path) -> VoicePair:
    sample = read_sample(path)
    body = normalize_newlines(sample.text)
    m = re.match(r"^##\s+Before\s*\n(.*?)\n##\s+After\s*\n(.*)$", body.strip() + "\n", re.S | re.I)
    if not m or not m.group(1).strip() or not m.group(2).strip():
        raise EISError(f"{path}: a voice pair needs '## Before' and '## After' sections, both non-empty")
    return VoicePair(sample.name, sample.title, m.group(1).strip() + "\n", m.group(2).strip() + "\n", sample.provenance)


def _claims(path: Path) -> tuple[tuple[ApprovedClaim, ...], tuple[ForbiddenClaim, ...]]:
    if not path.exists():
        return (), ()
    t = load_toml(path)
    approved = []
    for c in t.tables("approved"):
        claim = ApprovedClaim(
            id=c.str("id"), kind=c.str("kind", choices=CLAIM_KINDS), statement=c.str("statement"),
            source=c.str("source"), approved_by=c.str("approved_by"), approved_on=c.date("approved_on"),
            expires_on=c.date("expires_on", required=False),
            attribution=c.str("attribution", required=False, nonempty=False),
            allowed_phrasings=c.str_list("allowed_phrasings"),
        )
        c.finish()
        if claim.kind == "testimonial" and not claim.attribution:
            raise EISError(f"{c.where}: a testimonial needs an attribution")
        if claim.expires_on and claim.expires_on < claim.approved_on:
            raise EISError(f"{c.where}: expires_on is before approved_on")
        approved.append(claim)
    forbidden = []
    for f in t.tables("forbidden"):
        claim = ForbiddenClaim(f.str("id"), f.str("match", choices=("phrase", "regex")), f.str("pattern"), f.str("reason"))
        f.finish()
        if claim.match == "regex":
            _compile(claim.pattern, f.where)
        forbidden.append(claim)
    t.finish()
    unique_ids(approved + forbidden, str(path))
    return tuple(approved), tuple(forbidden)


_RULE_FIELDS = {
    "forbidden_term": {"terms"},
    "forbidden_pattern": {"pattern"},
    "banned_topic": {"terms"},
    "required_disclosure": {"triggers", "disclosure"},
    "speaker_policy": {"policy"},
}


def _rules(path: Path) -> tuple[GuardrailRule, ...]:
    if not path.exists():
        return ()
    t = load_toml(path)
    rules = []
    for r in t.tables("rules"):
        rtype = r.str("type", choices=RULE_TYPES)
        fields = _RULE_FIELDS[rtype]
        extra = sorted(set(r.data) & (set().union(*_RULE_FIELDS.values()) - fields))
        if extra:
            raise EISError(f"{r.where}: {extra} don't apply to a {rtype} rule")
        rule = GuardrailRule(
            id=r.str("id"), type=rtype, message=r.str("message"),
            severity=r.str("severity", required=False, default="major", choices=RULE_SEVERITIES),
            applies_to=r.str_list("applies_to"),
            terms=r.str_list("terms", required=True, nonempty=True) if "terms" in fields else (),
            pattern=r.str("pattern") if "pattern" in fields else "",
            triggers=r.str_list("triggers", required=True, nonempty=True) if "triggers" in fields else (),
            disclosure=r.str("disclosure") if "disclosure" in fields else "",
            policy=r.str("policy", choices=SPEAKER_POLICIES) if "policy" in fields else "",
        )
        r.finish()
        if rule.pattern:
            _compile(rule.pattern, r.where)
        rules.append(rule)
    t.finish()
    unique_ids(rules, str(path))
    return tuple(rules)


def _questions(path: Path) -> tuple[OpenQuestion, ...]:
    if not path.exists():
        return ()
    t = load_toml(path)
    questions = []
    for q in t.tables("questions"):
        questions.append(OpenQuestion(q.str("id"), q.str("question"), q.str_list("blocks_topics", required=True, nonempty=True),
                                      q.str("status", required=False, default="open", choices=("open", "resolved"))))
        q.finish()
    t.finish()
    unique_ids(questions, str(path))
    return tuple(questions)


def _content_log(path: Path) -> tuple[PublishedItem, ...]:
    if not path.exists():
        return ()
    items = []
    for n, line in enumerate(normalize_newlines(path.read_text(encoding="utf-8")).split("\n"), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EISError(f"{path}:{n}: invalid JSON: {exc}") from exc
        t = Table(data, f"{path}:{n}")
        items.append(PublishedItem(t.date("date"), t.str("work_id"), t.str("content_type"), t.str("title"),
                                   t.str("primary_question", required=False, nonempty=False), t.str_list("topics"),
                                   t.url("url", required=False)))
        t.finish()
    return tuple(items)


def _compile(pattern: str, where: str) -> re.Pattern:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise EISError(f"{where}: invalid regular expression {pattern!r}: {exc}") from exc
