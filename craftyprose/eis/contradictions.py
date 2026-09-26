"""Brand rules that contradict each other (architecture §16).

These are checked deterministically for the known cases. A brand with a
contradiction can't be written for until someone resolves it; intake (M4) turns
each one into a ``needs_input`` question instead of guessing which rule wins.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .text import find_term
from .workspace import BrandWorkspace

_DASHES = re.compile("[—–]")


@dataclass(frozen=True)
class Contradiction:
    id: str
    detail: str
    files: tuple[str, ...]


def find_contradictions(ws: BrandWorkspace) -> list[Contradiction]:
    out: list[Contradiction] = []
    voice = ws.voice
    avoided = {e.term.lower(): e for e in voice.avoid}
    forbidden_terms = [(r, t) for r in ws.rules if r.type == "forbidden_term" for t in r.terms]

    for e in voice.prefer:
        if e.term.lower() in avoided:
            out.append(Contradiction("C-LEXICON-BOTH", f"'{e.term}' is both preferred and avoided", ("voice.toml",)))
        for rule, term in forbidden_terms:
            if find_term(e.term, term):
                out.append(Contradiction("C-PREFERRED-FORBIDDEN",
                                         f"preferred term '{e.term}' is forbidden by guardrail '{rule.id}'",
                                         ("voice.toml", "guardrails.toml")))

    for claim in ws.approved_claims:
        texts = (claim.statement,) + claim.allowed_phrasings
        for rule, term in forbidden_terms:
            if any(find_term(t, term) for t in texts):
                out.append(Contradiction("C-CLAIM-FORBIDDEN-TERM",
                                         f"approved claim '{claim.id}' uses '{term}', forbidden by guardrail '{rule.id}'",
                                         ("claims.toml", "guardrails.toml")))
        for fc in ws.forbidden_claims:
            hit = any((re.search(fc.pattern, t, re.IGNORECASE) if fc.match == "regex" else find_term(t, fc.pattern))
                      for t in texts)
            if hit:
                out.append(Contradiction("C-CLAIM-FORBIDDEN-CLAIM",
                                         f"approved claim '{claim.id}' matches forbidden claim '{fc.id}'", ("claims.toml",)))
        if claim.kind != "testimonial":  # testimonials are quoted verbatim
            for term, entry in avoided.items():
                if any(find_term(t, entry.term) for t in texts):
                    out.append(Contradiction("C-CLAIM-AVOIDED-TERM",
                                             f"approved claim '{claim.id}' uses '{entry.term}', which the voice avoids",
                                             ("claims.toml", "voice.toml")))

    if voice.speaker.pronoun == "I" and any(r.policy == "no_first_person_singular" for r in ws.rules):
        out.append(Contradiction("C-SPEAKER-PRONOUN",
                                 "the voice speaks as 'I' but a guardrail forbids first-person singular",
                                 ("voice.toml", "guardrails.toml")))

    if voice.em_dash == "avoid":
        dashed = [s.name for s in ws.samples if _DASHES.search(s.text)]
        if dashed:
            out.append(Contradiction("C-EM-DASH-SAMPLES",
                                     f"punctuation says avoid em dashes but voice samples use them: {dashed}; "
                                     "set em_dash = \"match_samples\" or edit the samples",
                                     ("voice.toml", "voice/samples")))
    return out
