import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, r"C:\Users\mohdo\Documents\Metanous\content-engine")
sys.path.insert(0, r"C:\Users\mohdo\Documents\Metanous\content-engine\tests")
from engine import orchestrator
import fixtures as fx

# 4. Deterministic HW failure during human_writing stage: revision or escalation?
root = Path(tempfile.mkdtemp()); wid = fx.new_work(root)
for st, d, md in [("brief",fx.brief(),0),("research",fx.research(),0),("strategy",fx.strategy(),0),("outline",fx.outline(),1)]:
    fx.submit(root, wid, st, d, md)
bad = fx.draft(wid).replace("## What Agents Are\n\n", "## What Agents Are\n\nIn today's rapidly evolving landscape, agents matter. ", 1)
print("4a. draft w/ generic AI intro at DRAFT gate:", fx.submit(root, wid, "draft", bad, 1)["message"])
print("   ", fx.submit(root, wid, "factcheck", fx.review("pass"))["message"])
print("   ", fx.submit(root, wid, "editorial", fx.review("pass"))["message"])
for i in range(3):
    r = fx.submit(root, wid, "human_writing", fx.review("pass", stage="human_writing"))
    print(f"4b. HW review attempt {i+1}: {r['message']} | status={r['status']}")

# 5. Revision ignores human_writing blocking findings
root2 = Path(tempfile.mkdtemp()); w2 = fx.run_to_draft(root2)
fx.submit(root2, w2, "factcheck", fx.review("pass")); fx.submit(root2, w2, "editorial", fx.review("pass"))
r = fx.submit(root2, w2, "human_writing", fx.review("fail", [{"id":"HW-PARA-1","severity":"major","problem":"formulaic paragraphs"}], stage="human_writing"))
print("5a. HW fail ->", r["message"])
rev = {"work_id":w2,"revision":1,"draft":fx.draft(w2).replace("draft-v1","draft-v2"),"resolutions":[]}
print("5b. revision w/ ZERO resolutions + UNCHANGED text ->", fx.submit(root2, w2, "revision", rev)["message"])

# 8. review says pass while carrying a major finding marked resolved:true by the reviewer itself
root3 = Path(tempfile.mkdtemp()); w3 = fx.run_to_draft(root3)
fx.submit(root3, w3, "factcheck", fx.review("pass", [{"id":"FC-9","severity":"critical","problem":"fabricated statistic","resolved":True}]))
fx.submit(root3, w3, "editorial", fx.review("pass")); fx.submit(root3, w3, "human_writing", fx.review("pass", stage="human_writing"))
fx.submit(root3, w3, "final_review", fx.final_review())
a = orchestrator.approve(w3, root3)
print("8. critical 'fabricated statistic' self-marked resolved, never revised -> approve ok =", a["ok"], "|", a["message"])
# 9. rubber stamp: all reviews pass with zero findings on the known-AI calibration draft
root4 = Path(tempfile.mkdtemp()); w4 = fx.run_to_draft(root4)
for st in ("factcheck","editorial"): fx.submit(root4, w4, st, fx.review("pass", stage=st))
fx.submit(root4, w4, "human_writing", fx.review("pass", stage="human_writing")); fx.submit(root4, w4, "final_review", fx.final_review())
print("9. zero-finding rubber-stamp reviews -> approve ok =", orchestrator.approve(w4, root4)["ok"])
