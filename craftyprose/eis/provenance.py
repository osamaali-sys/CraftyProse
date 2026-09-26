"""Provenance and rights for text samples (decision D3).

Voice samples now, and the human-writing calibration corpus later, use the same
record. A sample is only treated as human-written when someone states how that
is known; scraped text of unknown authorship never qualifies, and synthetic
text (written by a model or for tests) is always marked as such.

Samples are Markdown files with a TOML front-matter block between ``+++`` lines::

    +++
    title = "Why we start every onboarding with the dispatch board"
    author = "Jordan Lee, head of customer success"
    source = "Customer newsletter, March 2021"
    human_written = true
    how_known = "Written and sent by the author in 2021; archived copy on file"
    rights = "owned"          # owned | licensed | public_domain | synthetic
    license = ""              # required when rights = "licensed"
    added_by = "Osama"
    added_on = 2026-09-26
    +++
    The sample text...
"""
from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..core.files import normalize_newlines
from ..core.schema import SchemaError, Table

RIGHTS = ("owned", "licensed", "public_domain", "synthetic")


@dataclass(frozen=True)
class Provenance:
    author: str
    source: str
    human_written: bool
    how_known: str
    rights: str
    license: str
    added_by: str
    added_on: dt.date

    @classmethod
    def read(cls, t: Table) -> "Provenance":
        p = cls(
            author=t.str("author"),
            source=t.str("source"),
            human_written=t.bool("human_written"),
            how_known=t.str("how_known", required=False, nonempty=False),
            rights=t.str("rights", choices=RIGHTS),
            license=t.str("license", required=False, nonempty=False),
            added_by=t.str("added_by"),
            added_on=t.date("added_on"),
        )
        if p.rights == "synthetic" and p.human_written:
            raise SchemaError(f"{t.where}: synthetic text can't be marked human_written")
        if p.human_written and not p.how_known:
            raise SchemaError(f"{t.where}: human_written samples must say how that is known ('how_known')")
        if p.rights == "licensed" and not p.license:
            raise SchemaError(f"{t.where}: licensed samples must name the license")
        return p


@dataclass(frozen=True)
class TextSample:
    name: str  # file stem
    title: str
    text: str
    provenance: Provenance


def read_sample(path: Path) -> TextSample:
    """Parse a Markdown file with a +++ TOML front-matter block into a sample."""
    raw = normalize_newlines(path.read_text(encoding="utf-8"))
    if not raw.startswith("+++\n"):
        raise SchemaError(f"{path}: must start with a +++ TOML front-matter block")
    end = raw.find("\n+++\n", 4)
    if end < 0:
        raise SchemaError(f"{path}: front-matter block is not closed with +++")
    try:
        meta = tomllib.loads(raw[4:end])
    except tomllib.TOMLDecodeError as exc:
        raise SchemaError(f"{path}: invalid front matter: {exc}") from exc
    t = Table(meta, f"{path} front matter")
    title = t.str("title")
    provenance = Provenance.read(t)
    t.finish()
    text = raw[end + 5:].strip()
    if not text:
        raise SchemaError(f"{path}: the sample has no text after the front matter")
    return TextSample(path.stem, title, text + "\n", provenance)
