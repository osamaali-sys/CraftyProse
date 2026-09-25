"""Probe: how well does the Metanous human-writing validator separate AI-shaped prose
from human prose, and do the draft-stage evidence gates catch uncited or fabricated material?

Run from C:\\Users\\mohdo\\Documents\\Metanous\\content-engine :
    python <this file>
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\mohdo\Documents\Metanous\content-engine")
sys.path.insert(0, r"C:\Users\mohdo\Documents\Metanous\content-engine\tests")
from engine.validators import human_writing as hw, run_validator  # noqa: E402
import fixtures  # noqa: E402


def hwrun(text):
    ctx = {"draft": text}
    r = hw.validate(ctx)
    return (r.passed, [c["name"] for c in r.failed_checks],
            [(f["id"], f["severity"]) for f in ctx.get("human_writing_semantic_findings", [])])


# 1. The calibration case: externally judged "strongly AI-generated".
d2 = Path(r"C:\Users\mohdo\Documents\Metanous\content\W-20260916-001\drafts\draft-v2.md").read_text(encoding="utf-8")
print("1. Known-AI draft-v2 -> (gate passed, failed checks, semantic findings):", hwrun(d2))
contrast = re.findall(
    r"\b(?:is|are|was)\s+not\s+[^.;]{3,80}[.;]\s*(?:It|it|They|they|That|that)\s+(?:is|are)\b"
    r"|\bnot\s+[^.;,]{3,60},\s*(?:it is|but)|,\s*not\s+an?\s+\w+", d2)
print("   'X is not Y. It is Z' contrasts in draft-v2:", len(contrast),
      "| hits from the validator's NOT_BUT regex:", len(hw.NOT_BUT_PATTERN.findall(d2)))

# 2. The fixture the test suite treats as clean.
fx = fixtures.DRAFT_BODY.format(work_id="W-1")
print("2. 'Clean' test fixture ->", hwrun(fx))
print("   contrast constructions in fixture:",
      len(re.findall(r"\bnot\s+(?:a|an|the|better|one)\b[^.;—]{0,60}[;—.]\s*(?:it|It|they)\s+(?:is|are)", fx)))

# 3. Short human-style prose.
human = """My grandfather kept the shop open until he was eighty-one. Nobody asked him to. The margins were thin, the roof leaked over the back counter, and every February he swore he'd sell.

He never did. What he did instead was learn every regular's order and write it on an index card, in pencil, so he could change it when their kids started school or their doctor told them to cut salt. When the supermarket opened two blocks away in 1994 he lost a third of his Saturday trade within a month. He got most of it back by delivering, which he hated, because the van was older than I was.

I asked him once why he bothered. He looked at me like I'd asked why he breathed."""
print("3. Human-style prose ->", hwrun(human))

# 4. Evidence gates: 15 uncited statistics appended to a valid draft.
d = fixtures.DRAFT_BODY.format(work_id="W-1") + "\n\n## Numbers\n\n" + " ".join(
    f"Adoption rose {40 + i}% in {2010 + i} across {i + 3} industries." for i in range(15))
ctx = {"draft": d, "research": fixtures.research(), "work_id": "W-1", "outline": None, "brief": fixtures.brief()}
print("4. Draft + 15 uncited statistics -> citations gate:", run_validator("validate_citations", ctx).result,
      "| claims gate:", run_validator("validate_claims", ctx).result)

# 5. A fabricated source URL.
res = fixtures.research()
res["sources"][0]["url"] = "https://totally-made-up-source.example/fake-study-2026"
print("5. Fabricated URL -> sources gate:", run_validator("validate_sources", {"research": res}).result)
