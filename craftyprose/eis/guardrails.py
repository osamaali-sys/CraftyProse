"""Brand rules compiled into deterministic checks (ADR-002, principle "guardrails are rules").

``Guardrails.check_text`` checks content (drafts, revisions, rendered release
text). ``Guardrails.check_topic`` checks a request or brief before any research
is done: banned topics and topics blocked by unresolved open questions. Every
check is named after its rule, carries a failure-pattern ID and blocks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..core.findings import normalize_text
from ..core.validation import ValidationResult
from .text import find_term, snippet, without_quotations
from .workspace import BrandWorkspace, ForbiddenClaim, GuardrailRule, OpenQuestion

FIRST_PERSON_SINGULAR = re.compile(r"\b(?:I|I'm|I've|I'd|I'll|me|my|mine|myself)\b")

PATTERN_FOR_RULE = {
    "forbidden_term": "RK-FORBIDDEN-TERM",
    "forbidden_pattern": "RK-FORBIDDEN-PATTERN",
    "banned_topic": "RK-BANNED-TOPIC",
    "required_disclosure": "RK-MISSING-DISCLOSURE",
    "speaker_policy": "RK-SPEAKER-POLICY",
}
FORBIDDEN_CLAIM_PATTERN = "RK-FORBIDDEN-CLAIM"
OPEN_QUESTION_PATTERN = "RK-BLOCKED-BY-OPEN-QUESTION"


@dataclass(frozen=True)
class Guardrails:
    rules: tuple[GuardrailRule, ...]
    forbidden_claims: tuple[ForbiddenClaim, ...]
    open_questions: tuple[OpenQuestion, ...]

    @classmethod
    def from_workspace(cls, ws: BrandWorkspace) -> "Guardrails":
        return cls(ws.rules, ws.forbidden_claims, ws.open())

    # ------------------------------------------------------------- content
    def check_text(self, text: str, content_type: str) -> ValidationResult:
        result = ValidationResult("guardrails")
        for rule in self.rules:
            if rule.applies(content_type):
                passed, detail = _check_rule(rule, text)
                result.add(f"guardrail:{rule.id}", passed, detail, pattern_id=PATTERN_FOR_RULE[rule.type])
        for claim in self.forbidden_claims:
            hit = _match_forbidden_claim(claim, text)
            result.add(f"forbidden_claim:{claim.id}", hit is None,
                       f"'{snippet(text, hit)}' matches a forbidden claim: {claim.reason}" if hit else "",
                       pattern_id=FORBIDDEN_CLAIM_PATTERN)
        return result

    # --------------------------------------------------------------- topic
    def check_topic(self, text: str, content_type: str) -> ValidationResult:
        result = ValidationResult("topic")
        for rule in self.rules:
            if rule.type == "banned_topic" and rule.applies(content_type):
                passed, detail = _check_rule(rule, text)
                result.add(f"guardrail:{rule.id}", passed, detail, pattern_id=PATTERN_FOR_RULE[rule.type])
        for q in self.open_questions:
            hit = next((t for t in q.blocks_topics if find_term(text, t)), None)
            result.add(f"open_question:{q.id}", hit is None,
                       f"'{hit}' depends on an unresolved question: {q.question}" if hit else "",
                       pattern_id=OPEN_QUESTION_PATTERN)
        return result


def _check_rule(rule: GuardrailRule, text: str) -> tuple[bool, str]:
    if rule.type in ("forbidden_term", "banned_topic"):
        for term in rule.terms:
            hit = find_term(text, term)
            if hit:
                return False, f"'{snippet(text, hit)}': {rule.message}"
        return True, ""
    if rule.type == "forbidden_pattern":
        m = re.search(rule.pattern, text, re.IGNORECASE)
        return (False, f"'{snippet(text, m.group(0))}': {rule.message}") if m else (True, "")
    if rule.type == "required_disclosure":
        trigger = next((t for t in rule.triggers if find_term(text, t)), None)
        if trigger is None:
            return True, ""
        if normalize_text(rule.disclosure) in normalize_text(text):
            return True, ""
        return False, f"mentions '{trigger}' without the required disclosure: \"{rule.disclosure}\""
    if rule.type == "speaker_policy" and rule.policy == "no_first_person_singular":
        m = FIRST_PERSON_SINGULAR.search(without_quotations(text))
        return (False, f"first-person singular '{m.group(0)}' outside quotations: {rule.message}") if m else (True, "")
    raise ValueError(f"unhandled guardrail {rule.type}/{rule.policy}")  # pragma: no cover - load validates


def _match_forbidden_claim(claim: ForbiddenClaim, text: str) -> str | None:
    if claim.match == "regex":
        m = re.search(claim.pattern, text, re.IGNORECASE)
        return m.group(0) if m else None
    return find_term(text, claim.pattern)
