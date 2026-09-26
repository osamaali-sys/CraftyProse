"""Load and validate content-type specifications (``specs/<id>.toml``).

A spec parameterizes the generic stages and validators; the core never branches
on a type. Adding a type means adding a spec file (and, only when parameters
can't express a rule, a small rule plugin in a later milestone).

Spec sections:

    id, name, goal, description
    [length]           unit = "words" | "characters"; range = [min, max]
    [anatomy]          required / optional elements (vocabulary below); headings
    [anatomy.counts]   element = [min, max] for countable elements
    [anatomy.fields]   element = [min_chars, max_chars] for short text fields
    [anatomy.limits]   intro_max_sentences, hook_max_chars
    [evidence]         third_party_required, min_supported_claims, max_source_age_years.{kind}
    [discoverability]  enabled, primary_question_required, title_chars, meta_description_chars,
                       keyword_density_max, internal_links, jsonld
    [human_writing]    mode = "reference" | "marketing" | "shortform"
    [review]           judges (subset of evidence, editorial, writing)
    [release]          format, citation_style
    [approval]         required = true (decision D5: always true in v1)

Writing modes (architecture §10): *reference* applies every writing pattern at
full strength with no promotional allowances; *marketing* expects concrete
benefit claims and calls to action, and treats generic superlatives as "make it
concrete" rather than "delete"; *shortform* is for pieces under about 300 words,
where length-based statistics such as rhythm variation are skipped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..core.schema import SchemaError, Table, load_toml

SPECS_DIR = Path(__file__).with_name("specs")

GOALS = ("educate", "persuade", "position", "convert", "nurture", "engage", "announce")
MODES = ("reference", "marketing", "shortform")
JUDGES = ("evidence", "editorial", "writing")
FORMATS = ("markdown", "plain_text")
CITATION_STYLES = ("inline_links", "footnotes", "sources_note", "none")
JSONLD_TYPES = ("Article", "BlogPosting", "FAQPage", "WebPage")

# Anatomy vocabulary: the contract between specs and the structure validators.
ELEMENTS = {
    "title": "the piece's title (H1 for markdown formats)",
    "answer_first_intro": "an opening that answers the primary question in its first sentences",
    "body_sections": "headed sections carrying the argument",
    "thesis": "a stated position the piece argues for",
    "counter_position": "the strongest objection to the thesis, taken seriously",
    "faq": "questions phrased as questions, each answered directly",
    "how_we_work": "a short passage on the brand's method, using approved claims only",
    "hook": "the opening lines shown before a feed truncates the post",
    "body": "the main text of a short-form piece",
    "closing_prompt": "a closing question or invitation to respond",
    "headline": "a landing page's main headline",
    "subhead": "the line under the headline",
    "value_points": "distinct benefits, each concrete",
    "proof": "evidence of results, from approved claims and testimonials only",
    "objections": "answers to the reader's likely objections",
    "subject": "an email subject line",
    "preheader": "an email preview line",
    "sign_off": "an email closing",
    "cta": "one call to action",
    "primary_cta": "the single main call to action",
}
COUNTABLE = ("body_sections", "value_points", "faq")
FIELD_ELEMENTS = ("subject", "preheader")


@dataclass(frozen=True)
class Anatomy:
    required: tuple[str, ...]
    optional: tuple[str, ...]
    headings: bool
    counts: dict[str, tuple[int, int]] = field(default_factory=dict)
    fields: dict[str, tuple[int, int]] = field(default_factory=dict)
    intro_max_sentences: int | None = None
    hook_max_chars: int | None = None

    @property
    def elements(self) -> tuple[str, ...]:
        return self.required + self.optional


@dataclass(frozen=True)
class EvidenceRules:
    third_party_required: bool
    min_supported_claims: int
    max_source_age_years: dict[str, int]

    def max_age(self, claim_kind: str) -> int | None:
        return self.max_source_age_years.get(claim_kind, self.max_source_age_years.get("default"))


@dataclass(frozen=True)
class Discoverability:
    enabled: bool
    primary_question_required: bool = False
    title_chars: tuple[int, int] | None = None
    meta_description_chars: tuple[int, int] | None = None
    keyword_density_max: float | None = None
    internal_links: tuple[int, int] | None = None
    jsonld: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContentType:
    id: str
    name: str
    goal: str
    description: str
    length_unit: str
    length: tuple[int, int]
    anatomy: Anatomy
    evidence: EvidenceRules
    discoverability: Discoverability
    writing_mode: str
    judges: tuple[str, ...]
    release_format: str
    citation_style: str
    approval_required: bool
    path: Path


class ContentTypeError(SchemaError):
    pass


def load_spec(path: Path) -> ContentType:
    try:
        return _read(load_toml(path), path)
    except ContentTypeError:
        raise
    except SchemaError as exc:
        raise ContentTypeError(str(exc)) from exc


def _read(t: Table, path: Path) -> ContentType:
    type_id = t.str("id")
    if type_id != path.stem:
        raise ContentTypeError(f"{path}: id {type_id!r} must match the file name {path.stem!r}")

    length = t.table("length", required=True)
    unit = length.str("unit", choices=("words", "characters"))
    length_range = length.range("range", minimum=1)
    length.finish()

    a = t.table("anatomy", required=True)
    required = a.str_list("required", required=True, nonempty=True, choices=ELEMENTS)
    optional = a.str_list("optional", choices=ELEMENTS)
    overlap = sorted(set(required) & set(optional))
    if overlap:
        raise ContentTypeError(f"{a.where}: {overlap} can't be both required and optional")
    elements = set(required) | set(optional)
    headings = a.bool("headings")
    counts_t = a.table("counts")
    counts = {k: counts_t.range(k, minimum=0) for k in list(counts_t.data)}
    counts_t.finish()
    fields_t = a.table("fields")
    fields = {k: fields_t.range(k, minimum=1) for k in list(fields_t.data)}
    fields_t.finish()
    limits = a.table("limits")
    intro_max = limits.int("intro_max_sentences", default=0, minimum=0) or None
    hook_max = limits.int("hook_max_chars", default=0, minimum=0) or None
    limits.finish()
    a.finish()
    for name, table, allowed in (("counts", counts, COUNTABLE), ("fields", fields, FIELD_ELEMENTS)):
        for k in table:
            if k not in allowed:
                raise ContentTypeError(f"{a.where}.{name}: '{k}' isn't a {name[:-1]} element; allowed: {list(allowed)}")
            if k not in elements:
                raise ContentTypeError(f"{a.where}.{name}: '{k}' isn't in this type's anatomy")
    if intro_max and "answer_first_intro" not in elements:
        raise ContentTypeError(f"{a.where}.limits: intro_max_sentences needs an answer_first_intro element")
    if hook_max and "hook" not in elements:
        raise ContentTypeError(f"{a.where}.limits: hook_max_chars needs a hook element")
    anatomy = Anatomy(required, optional, headings, counts, fields, intro_max, hook_max)

    e = t.table("evidence", required=True)
    ages_t = e.table("max_source_age_years")
    ages = {k: ages_t.int(k, minimum=1) for k in list(ages_t.data)}
    ages_t.finish()
    evidence = EvidenceRules(e.bool("third_party_required"), e.int("min_supported_claims", minimum=0), ages)
    e.finish()
    if evidence.third_party_required and "default" not in ages:
        raise ContentTypeError(f"{e.where}: third-party evidence needs max_source_age_years.default")

    d = t.table("discoverability", required=True)
    enabled = d.bool("enabled")
    if enabled:
        disc = Discoverability(
            enabled=True,
            primary_question_required=d.bool("primary_question_required"),
            title_chars=d.range("title_chars", minimum=1),
            meta_description_chars=d.range("meta_description_chars", minimum=1),
            keyword_density_max=d.float("keyword_density_max", minimum=0.001, maximum=0.2),
            internal_links=d.range("internal_links", minimum=0),
            jsonld=d.str_list("jsonld", choices=JSONLD_TYPES),
        )
    else:
        disc = Discoverability(enabled=False)
    d.finish()

    hw = t.table("human_writing", required=True)
    mode = hw.str("mode", choices=MODES)
    hw.finish()
    review = t.table("review", required=True)
    judges = review.str_list("judges", required=True, nonempty=True, choices=JUDGES)
    review.finish()
    release = t.table("release", required=True)
    fmt = release.str("format", choices=FORMATS)
    citation = release.str("citation_style", choices=CITATION_STYLES)
    release.finish()
    if headings and fmt == "plain_text":
        raise ContentTypeError(f"{path}: plain-text output can't use headings")
    approval = t.table("approval", required=True)
    approval_required = approval.bool("required")
    approval.finish()
    if not approval_required:
        raise ContentTypeError(f"{approval.where}: every content type requires human approval in v1 (decision D5)")

    spec = ContentType(type_id, t.str("name"), t.str("goal", choices=GOALS), t.str("description"), unit,
                       length_range, anatomy, evidence, disc, mode, judges, fmt, citation, approval_required, path)
    t.finish()
    return spec


class Catalog:
    """All content types in a specs directory, loaded once and validated together."""

    def __init__(self, specs_dir: Path = SPECS_DIR) -> None:
        self.types: dict[str, ContentType] = {}
        for path in sorted(Path(specs_dir).glob("*.toml")):
            spec = load_spec(path)
            self.types[spec.id] = spec
        if not self.types:
            raise ContentTypeError(f"no content-type specs in {specs_dir}")

    def ids(self) -> tuple[str, ...]:
        return tuple(self.types)

    def get(self, type_id: str) -> ContentType:
        if type_id not in self.types:
            raise ContentTypeError(f"unknown content type {type_id!r}; known: {list(self.types)}")
        return self.types[type_id]
