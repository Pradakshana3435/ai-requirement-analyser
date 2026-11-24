import csv
import glob
import os
import sys
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from eval.metrics import _issue_matches, match_requirements
from models import AnalysisResult

rows = []
for gpath in sorted(glob.glob("data/eval/gold/*.json")):
    name = os.path.basename(gpath)[:-5]
    rpath = f"output/eval/results/{name}.json"
    if not os.path.exists(rpath):
        continue
    gold = json.load(open(gpath, encoding="utf-8"))
    result = AnalysisResult.model_validate_json(open(rpath, encoding="utf-8").read())
    g2p = match_requirements(result.document.raw_text, gold["requirements"], result.requirements)
    quote = {g["id"]: g["quote"] for g in gold["requirements"]}
    text = {r.req_id: r.text for r in result.requirements}

    for w in result.warnings:
        print(f"{name} WARNING: {w[:150]}")
    for gi in gold["issues"]:
        if not any(_issue_matches(gi, f, g2p) for f in result.findings):
            print(f"{name} MISSED {gi['kind']}: " + " / ".join(quote[i][:60] for i in gi["req_ids"]))
    for f in result.findings:
        if not any(_issue_matches(gi, f, g2p) for gi in gold["issues"]):
            rows.append([name, f.kind.value, ", ".join(f.req_ids),
                         " / ".join(text.get(i, "")[:90] for i in f.req_ids), f.reason, ""])

os.makedirs("output/eval", exist_ok=True)
with open("output/eval/unmatched_findings.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["document", "kind", "requirements", "requirement_text", "reason", "valid_yes_no"])
    w.writerows(rows)
print(f"\n{len(rows)} unmatched findings written to output\\eval\\unmatched_findings.csv")