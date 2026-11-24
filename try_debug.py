import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from eval.metrics import _issue_matches, match_requirements
from models import AnalysisResult

for gpath in sorted(glob.glob("data/eval/gold/*.json")):
    name = os.path.basename(gpath)[:-5]
    rpath = f"output/eval/results/{name}.json"
    if not os.path.exists(rpath):
        continue
    gold = json.load(open(gpath, encoding="utf-8"))
    result = AnalysisResult.model_validate_json(open(rpath, encoding="utf-8").read())
    g2p = match_requirements(result.document.raw_text, gold["requirements"], result.requirements)
    quote = {g["id"]: g["quote"] for g in gold["requirements"]}
    print(f"\n===== {name}")

    flagged = [s for s in result.suggestions if not s.grounded and s.kind.value != "clarification_question"]
    total = [s for s in result.suggestions if s.kind.value != "clarification_question"]
    print(f"-- flagged unsupported: {len(flagged)} of {len(total)}")
    for s in flagged[:6]:
        print(f"   {s.req_id} {s.kind.value} added={s.added_terms}\n      {s.content[:110]}")

    print("-- MISSED planted issues")
    for gi in gold["issues"]:
        if not any(_issue_matches(gi, f, g2p) for f in result.findings):
            print(f"   {gi['kind']}: " + " / ".join(quote[i][:50] for i in gi["req_ids"]))

    print("-- findings that matched nothing")
    for f in result.findings:
        if not any(_issue_matches(gi, f, g2p) for gi in gold["issues"]):
            print(f"   {f.kind.value} {f.req_ids}: {f.reason[:100]}")