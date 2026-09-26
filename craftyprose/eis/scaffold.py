"""``brand init``: scaffold a brand workspace to fill in (architecture §3.2).

Required values are left empty on purpose, so ``brand check`` fails and names
each field until a person fills it in. Nothing is guessed on the brand's behalf.
"""
from __future__ import annotations

from pathlib import Path

from ..core.files import write_text_atomic
from .workspace import BRAND_ID_RE, EISError, brand_dir

TEMPLATES = {
    "brand.toml": '''# Who the brand is. Fill in every value; "brand check" lists what's missing.
id = "{brand_id}"
name = ""
description = ""        # one or two plain sentences: what the brand does, for whom
positioning = ""        # why a reader would choose it
locale = "en-US"
markets = []            # e.g. ["US courier firms with 5 to 200 drivers"]

# [[offerings]]
# id = "product-slug"
# name = "Product name"
# summary = "What it does, in one sentence."
# url = "https://..."

# Pages content may link to. Internal links must be listed here.
# [[linkable_pages]]
# url = "https://..."
# title = "Page title"
# topics = ["topic"]
''',
    "audiences.toml": '''# Who the content is for. Add one [[personas]] block per reader type.
[[personas]]
id = ""
who = ""                  # who they are, in their own terms
sophistication = "practitioner"   # novice | practitioner | expert
problems = []             # what they're trying to fix
questions = []            # what they ask, in their words
objections = []           # why they hesitate
vocabulary = []           # words they use
''',
    "voice.toml": '''# How the brand sounds. Voice samples in voice/samples/ outrank these rules.
register = ""             # e.g. "plain, direct and practical"
personality = []          # three or four words
rules = []                # short writing rules the brand actually follows

[speaker]
mode = "company"          # company | author
name = ""                 # required for an author voice
pronoun = "we"            # we | I  (a company voice speaks as "we")

# [[lexicon.prefer]]
# term = "word we use"
# instead_of = ["word we don't"]
# reason = "why"

# [[lexicon.avoid]]
# term = "word we avoid"
# reason = "why"
# alternative = "what to say instead"

[punctuation]
em_dash = "allow"         # avoid | allow | match_samples

[style]
spelling = "en-US"        # en-US | en-GB | en-AU | en-CA
headings = "sentence"     # sentence | title
''',
    "claims.toml": '''# First-party claims the brand has approved for use, and claims it forbids.
# A statement about the brand's results, customers or capabilities can only be
# released if it matches an approved, unexpired claim here.

# [[approved]]
# id = "claim-slug"
# kind = "first_party_fact"     # first_party_fact | marketing_claim | testimonial
# statement = "The exact wording that was approved."
# source = "Where it comes from (policy, records, interview)"
# approved_by = "Name"
# approved_on = 2026-01-01
# expires_on = 2026-12-31       # optional
# attribution = ""              # required for testimonials
# allowed_phrasings = []

# [[forbidden]]
# id = "forbidden-slug"
# match = "phrase"              # phrase | regex
# pattern = "claim we never make"
# reason = "why"
''',
    "guardrails.toml": '''# Hard rules, checked on every draft.
# types: forbidden_term (terms), forbidden_pattern (pattern), banned_topic (terms),
#        required_disclosure (triggers, disclosure), speaker_policy (policy)

# [[rules]]
# id = "rule-slug"
# type = "banned_topic"
# terms = ["pricing"]
# message = "Why the rule exists and what to do instead."
# applies_to = []               # content type ids; empty means all
''',
    "open_questions.toml": '''# Facts nobody has confirmed yet. Topics listed in blocks_topics are blocked
# until the question is answered and its status set to "resolved".

# [[questions]]
# id = "question-slug"
# question = "What isn't known yet?"
# blocks_topics = ["topic"]
# status = "open"               # open | resolved
''',
}


def init_brand(workspace: Path, brand_id: str) -> Path:
    if not BRAND_ID_RE.match(brand_id or ""):
        raise EISError(f"brand id must be a lowercase slug, got {brand_id!r}")
    root = brand_dir(workspace, brand_id)
    if root.exists():
        raise EISError(f"{root} already exists")
    for name, text in TEMPLATES.items():
        write_text_atomic(root / name, text.replace("{brand_id}", brand_id))
    for sub in ("voice/samples", "voice/pairs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root
