"""Probe: does the Click Savvy EIS infrastructure (infrastructure/*.py) run, and do its gates hold?

Read-only against the predecessor repo; all writes go to a temp directory.
    python <this file>
"""
import json
import os
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")
REPO = r"C:\Users\mohdo\Downloads\ClickSavvy-SEO-main\ClickSavvy-SEO-main\infrastructure"
for sub in ("validation", "evidence", "knowledge", "execution", "writing"):
    sys.path.insert(0, os.path.join(REPO, sub))
tmp = tempfile.mkdtemp()
os.chdir(tmp)  # gcv.py writes to a relative "vault/" path

print("1. GCVEngine() construction")
try:
    import gcv
    gcv.GCVEngine(tmp)
    print("   constructed")
except Exception as e:
    print("   FAIL:", type(e).__name__, e)
try:
    import gcv_validators  # noqa: F401
    print("   gcv_validators imported")
except Exception as e:
    print("   gcv_validators import FAIL:", type(e).__name__, e)

from bs4 import BeautifulSoup  # noqa: E402

print("2. GCV-001 trade-offs validator on a real Pros/Cons table")
html = "<table><tr><th>Option</th><th>Pros</th><th>Cons</th></tr><tr><td>A</td><td>cheap</td><td>slow</td></tr></table>"
r = gcv.TradeoffsValidator().run({"soup": BeautifulSoup(html, "html.parser"), "text": ""})
print("   passed =", r.passed, "(a correct validator would pass this)")

print("3. GCV-009 'factual claim' extractor on non-factual sentences")
html2 = "<h1>x</h1><p>This guide walks through the thinking behind our process. We love helping teams like yours. Thanks for reading this far today.</p>"
print("  ", gcv.EvidenceReferencesValidator()._extract_factual_claims(BeautifulSoup(html2, "html.parser")))

import service as ev  # noqa: E402

s = ev.EvidenceService(tmp)
print("4. EvidenceService.ingest_evidence on a clean government statistic")
src = {"type": "government standards_body", "name": "Gov stat", "url": "https://www.bls.gov/x",
       "content": "The unemployment rate was 4.1 percent in June according to the survey data released."}
try:
    print("   ingested", s.ingest_evidence(src, "The unemployment rate was 4.1 percent in June",
                                          {"criticality": "background", "namespace": "u", "topic": "t"}))
except Exception as e:
    print("   FAIL:", type(e).__name__, e)

print("5. Excerpt extraction when the source does not support the claim")
src2 = {"type": "government", "url": "https://x.gov",
        "content": "Completely unrelated text about weather patterns in the northern hemisphere during winter."}
print("   excerpt returned as 'evidence':", repr(s._extract_excerpt(src2, "Tankless heaters save 40 percent on energy")[:70]))

import kp_service as kps  # noqa: E402

print("6. KPService: save, then modify again (JSON round-trip)")
k = kps.KPService(tmp)
kid = k.create_kp("c", "topic", "r")
comp = {"claims": [{"text": "x", "evidence_ids": ["EVD-1"], "criticality": "core",
                    "evidence_confidence": 99, "coverage_status": "covered"}]}
try:
    k.assemble_component(kid, kps.KPComponent.BUSINESS_INTELLIGENCE, comp, "r")
    k.assemble_component(kid, kps.KPComponent.INDUSTRY_INTELLIGENCE, comp, "r")
    print("   both assembles OK")
except Exception as e:
    print("   FAIL on second write:", type(e).__name__, e)

print("7. Confidence gate fed self-reported confidence and a nonexistent evidence id")
k2 = kps.KPService(tempfile.mkdtemp())
kid2 = k2.create_kp("c", "t", "r")
kp = k2._load_kp(kid2)
for c in kps.KPService.REQUIRED_COMPONENTS:
    setattr(kp, c.value, comp)
k2._load_kp = lambda _id: kp  # bypass the broken reload from probe 6
rep = k2.calculate_confidence(kid2)
print("   score:", rep["score"], "status:", rep["status"],
      "| component weights sum to", round(sum(kps.KPService.COMPONENT_WEIGHTS.values()), 2))

import engine as ex  # noqa: E402

print("8. ExecutionEngine self-test sequence (gate 0 -> gate 1)")
e = ex.ExecutionEngine(tmp)
e.create_article("a1", ex.ContentPath.STANDARD)
for a in ("strategy_brief", "kp_seeds", "editorial_objectives", "client_profile", "voice_profile",
          "business_intelligence", "industry_intelligence", "regional_intelligence",
          "customer_intelligence", "competitor_intelligence"):
    e.set_artifact("a1", a, "ref")
print("   transition to 0:", e.transition("a1", 0, "strategist"))
print("   transition to 1:", e.transition("a1", 1, "discovery_team"))

import declaration as dc  # noqa: E402

print("9. WriterDeclaration: all compliance booleans are self-set by the writer")
svc = dc.WriterDeclarationService(tmp)
d = svc.create_declaration("ART-1", "writer-1", "KP-1", "VPR-1")
for f in ("kp_compliance", "voice_compliance", "evidence_compliance", "e_e_a_t_compliance",
          "research_budget_compliance", "failure_pattern_compliance", "no_fabrication"):
    setattr(d, f, True)
svc._save_declaration(d)
print("   submit:", svc.submit_declaration(d.declaration_id, svc._get_writer_secret("writer-1")),
      "| validate:", svc.validate_declaration(d.declaration_id, "engine"))
print("   reload of a saved declaration:", svc.get_declaration(d.declaration_id),
      "(status is saved as 'DeclarationStatus.DRAFT' and cannot be parsed back)")
print("   even when it works, the gate checks only booleans the writer set; the draft is never examined")
