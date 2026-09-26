"""Context slices: the declared part of EIS each role receives (architecture §3.4).

Least context is what makes judges independent. The writing judge never sees
the claims or evidence; the evidence judge never sees voice samples. Slices are
rendered deterministically and hashed, so a run is reproducible, and the stable
EIS prefix can be cached. Work-item artifacts (brief, ledger, draft) are added
by the stages after this prefix.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass

from ..content_types.loader import ELEMENTS, ContentType
from ..core.files import canonical_json, sha256_text
from ..runtime.llm import Block
from .standards import library, principles
from .workspace import BrandWorkspace

ROLES = ("planner", "researcher", "strategist", "writer", "judge_evidence", "judge_editorial", "judge_writing")

SLICES: dict[str, tuple[str, ...]] = {
    "planner": ("principles", "brand", "offerings", "audiences", "guardrails", "open_questions", "content_log",
                "content_type"),
    "researcher": ("brand", "offerings", "approved_claims", "content_type"),
    "strategist": ("principles", "brand", "offerings", "audiences", "voice_summary", "approved_claims", "guardrails",
                   "content_log", "content_type"),
    "writer": ("principles", "brand", "offerings", "audiences", "voice", "voice_samples", "voice_pairs",
               "approved_claims", "guardrails", "content_type"),
    "judge_evidence": ("principles", "approved_claims", "guardrails", "content_type", "patterns:evidence"),
    "judge_editorial": ("principles", "brand", "offerings", "audiences", "content_log", "content_type",
                        "patterns:editorial"),
    "judge_writing": ("voice", "voice_samples", "voice_pairs", "content_type", "patterns:writing"),
}

CONTENT_LOG_LIMIT = 50


@dataclass(frozen=True)
class ContextSlice:
    role: str
    parts: tuple[str, ...]
    blocks: tuple[Block, ...]
    sha256: str


def build_slice(ws: BrandWorkspace, role: str, content_type: ContentType, *, as_of: dt.date) -> ContextSlice:
    if role not in SLICES:
        raise ValueError(f"unknown role {role!r}; roles: {list(SLICES)}")
    parts = SLICES[role]
    blocks = tuple(Block(f"eis/{part}", _render(part, ws, content_type, as_of), cacheable=True) for part in parts)
    digest = sha256_text(canonical_json([asdict(b) for b in blocks]))
    return ContextSlice(role, parts, blocks, digest)


def _render(part: str, ws: BrandWorkspace, ct: ContentType, as_of: dt.date) -> str:
    if part.startswith("patterns:"):
        return _patterns(part.split(":", 1)[1])
    return {
        "principles": lambda: principles(),
        "brand": lambda: _brand(ws),
        "offerings": lambda: _offerings(ws),
        "audiences": lambda: _audiences(ws),
        "voice": lambda: _voice(ws, full=True),
        "voice_summary": lambda: _voice(ws, full=False),
        "voice_samples": lambda: _samples(ws),
        "voice_pairs": lambda: _pairs(ws),
        "approved_claims": lambda: _claims(ws, as_of),
        "guardrails": lambda: _guardrails(ws),
        "open_questions": lambda: _questions(ws),
        "content_log": lambda: _log(ws),
        "content_type": lambda: _content_type(ct),
    }[part]()


def _lines(*lines: str) -> str:
    return "\n".join(line for line in lines if line is not None) + "\n"


def _bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items) if items else "- (none)"


def _brand(ws: BrandWorkspace) -> str:
    b = ws.brand
    return _lines(f"# Brand: {b.name}", b.description, "", f"Positioning: {b.positioning}",
                  f"Locale: {b.locale}", f"Markets: {'; '.join(b.markets)}")


def _offerings(ws: BrandWorkspace) -> str:
    b = ws.brand
    offerings = [f"{o.name} ({o.id}): {o.summary}" + (f" <{o.url}>" if o.url else "") for o in b.offerings]
    pages = [f"{p.title} <{p.url}>" + (f" topics: {', '.join(p.topics)}" if p.topics else "") for p in b.linkable_pages]
    return _lines("# Offerings", _bullets(offerings), "", "# Linkable pages (the only internal links allowed)",
                  _bullets(pages))


def _audiences(ws: BrandWorkspace) -> str:
    out = ["# Audiences"]
    for p in ws.personas:
        out += ["", f"## {p.id} ({p.sophistication})", p.who,
                "Problems:", _bullets(p.problems), "Questions:", _bullets(p.questions),
                "Objections:", _bullets(p.objections), f"Their words: {', '.join(p.vocabulary) or '(none)'}"]
    return _lines(*out)


def _voice(ws: BrandWorkspace, *, full: bool) -> str:
    v = ws.voice
    speaker = (f"the company, speaking as '{v.speaker.pronoun}'" if v.speaker.mode == "company"
               else f"{v.speaker.name}, speaking as '{v.speaker.pronoun}'")
    out = ["# Voice", f"Speaker: {speaker}", f"Register: {v.register}", f"Personality: {', '.join(v.personality)}"]
    if not full:
        return _lines(*out)
    prefer = [f"'{e.term}'" + (f" instead of {', '.join(repr(x) for x in e.instead_of)}" if e.instead_of else "")
              + f": {e.reason}" for e in v.prefer]
    avoid = [f"'{e.term}': {e.reason}" + (f" Use: {e.alternative}" if e.alternative else "") for e in v.avoid]
    out += ["Rules:", _bullets(v.rules), "Preferred terms:", _bullets(prefer), "Avoided terms:", _bullets(avoid),
            f"Em dashes: {v.em_dash}", f"Spelling: {v.spelling}", f"Headings: {v.headings} case"]
    return _lines(*out)


def _provenance_note(p) -> str:
    written = "human-written" if p.human_written else "not human-written"
    return f"({written}; {p.rights}; {p.author}; {p.source})"


def _samples(ws: BrandWorkspace) -> str:
    if not ws.samples:
        return _lines("# Voice samples", "(none: judge the voice against the rules only)")
    out = ["# Voice samples (these outrank the style rules)"]
    for s in ws.samples:
        out += ["", f"## {s.title} {_provenance_note(s.provenance)}", s.text.rstrip()]
    return _lines(*out)


def _pairs(ws: BrandWorkspace) -> str:
    if not ws.pairs:
        return _lines("# Before and after", "(none)")
    out = ["# Before and after"]
    for p in ws.pairs:
        out += ["", f"## {p.title}", "Before:", p.before.rstrip(), "After:", p.after.rstrip()]
    return _lines(*out)


def _claims(ws: BrandWorkspace, as_of: dt.date) -> str:
    usable = ws.usable_claims(as_of)
    out = [f"# Approved brand claims (usable on {as_of.isoformat()})"]
    for c in usable:
        extra = [f"attribution: {c.attribution}" if c.attribution else "",
                 f"expires {c.expires_on.isoformat()}" if c.expires_on else "",
                 f"allowed wording: {' | '.join(c.allowed_phrasings)}" if c.allowed_phrasings else ""]
        out.append(f"- [{c.id}] ({c.kind}) {c.statement} Source: {c.source}. "
                   + " ".join(e + "." for e in extra if e))
    if not usable:
        out.append("- (none)")
    skipped = len(ws.approved_claims) - len(usable)
    if skipped:
        out.append(f"({skipped} approved claim(s) are expired or not yet valid and must not be used.)")
    out += ["", "# Forbidden claims", _bullets([f"[{f.id}] {f.pattern} ({f.match}): {f.reason}" for f in ws.forbidden_claims])]
    return _lines(*out)


def _guardrails(ws: BrandWorkspace) -> str:
    items = []
    for r in ws.rules:
        scope = f" (only for: {', '.join(r.applies_to)})" if r.applies_to else ""
        detail = {
            "forbidden_term": f"never use: {', '.join(r.terms)}",
            "banned_topic": f"don't cover: {', '.join(r.terms)}",
            "forbidden_pattern": f"never match: {r.pattern}",
            "required_disclosure": f"when mentioning {', '.join(r.triggers)}, include: \"{r.disclosure}\"",
            "speaker_policy": f"policy: {r.policy}",
        }[r.type]
        items.append(f"[{r.id}] {detail}. {r.message}{scope}")
    return _lines("# Guardrails (hard rules)", _bullets(items))


def _questions(ws: BrandWorkspace) -> str:
    items = [f"[{q.id}] {q.question} Blocks: {', '.join(q.blocks_topics)}" for q in ws.open()]
    return _lines("# Open questions (topics that depend on these are blocked)", _bullets(items))


def _log(ws: BrandWorkspace) -> str:
    recent = sorted(ws.content_log, key=lambda i: (i.date, i.work_id), reverse=True)[:CONTENT_LOG_LIMIT]
    items = [f"{i.date.isoformat()} {i.content_type}: {i.title}"
             + (f" (question: {i.primary_question})" if i.primary_question else "") for i in recent]
    return _lines("# Already released (don't repeat)", _bullets(items))


def _content_type(ct: ContentType) -> str:
    a = ct.anatomy
    elements = [f"{e} ({'required' if e in a.required else 'optional'}): {ELEMENTS[e]}"
                + (f"; count {a.counts[e][0]} to {a.counts[e][1]}" if e in a.counts else "")
                + (f"; {a.fields[e][0]} to {a.fields[e][1]} characters" if e in a.fields else "")
                for e in a.elements]
    limits = []
    if a.intro_max_sentences:
        limits.append(f"intro at most {a.intro_max_sentences} sentences")
    if a.hook_max_chars:
        limits.append(f"hook at most {a.hook_max_chars} characters")
    ev = ct.evidence
    ages = ", ".join(f"{k} {v} years" for k, v in sorted(ev.max_source_age_years.items()))
    d = ct.discoverability
    disc = "off" if not d.enabled else (
        f"on; primary question {'required' if d.primary_question_required else 'optional'}; "
        f"title {d.title_chars[0]} to {d.title_chars[1]} characters; meta description "
        f"{d.meta_description_chars[0]} to {d.meta_description_chars[1]} characters; keyword density at most "
        f"{d.keyword_density_max:.1%}; internal links {d.internal_links[0]} to {d.internal_links[1]}")
    return _lines(
        f"# Content type: {ct.name} ({ct.id})", ct.description, f"Goal: {ct.goal}",
        f"Length: {ct.length[0]} to {ct.length[1]} {ct.length_unit}",
        f"Headings: {'yes' if a.headings else 'no'}", "Elements:", _bullets(elements),
        f"Limits: {'; '.join(limits) or 'none'}",
        f"Evidence: third-party evidence {'required' if ev.third_party_required else 'not required'}; "
        f"at least {ev.min_supported_claims} supported claim(s); source age limits: {ages or 'none'}",
        f"Discoverability: {disc}", f"Writing mode: {ct.writing_mode}",
        f"Output: {ct.release_format}; citations: {ct.citation_style}",
    )


def _patterns(judge: str) -> str:
    items = [f"{p.id} ({p.severity}) {p.name}: {p.definition}" + (f" Example: {p.example}" if p.example else "")
             for p in library().for_judge(judge)]
    return _lines(f"# Failure patterns you may report ({judge} judge)", _bullets(items))
