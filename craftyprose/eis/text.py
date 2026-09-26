"""Text matching shared by EIS checks: whole-term, case-insensitive, quote-aware."""
from __future__ import annotations

import re

_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
_BLOCKQUOTE = re.compile(r"(?m)^\s*>.*$")


def term_regex(term: str) -> re.Pattern:
    """Match ``term`` as a whole word or phrase; internal whitespace matches any whitespace."""
    parts = [re.escape(p) for p in term.split()]
    return re.compile(r"(?<![\w-])" + r"\s+".join(parts) + r"(?![\w-])", re.IGNORECASE)


def find_term(text: str, term: str) -> str | None:
    m = term_regex(term).search(text)
    return m.group(0) if m else None


def without_quotations(text: str) -> str:
    """Drop quoted passages and blockquotes (testimonials, cited words) before voice checks."""
    return _QUOTED.sub(" ", _BLOCKQUOTE.sub(" ", text))


def snippet(text: str, needle: str, width: int = 60) -> str:
    i = text.lower().find(needle.lower())
    if i < 0:
        return needle
    start, end = max(0, i - width // 2), min(len(text), i + len(needle) + width // 2)
    return " ".join(text[start:end].split())
