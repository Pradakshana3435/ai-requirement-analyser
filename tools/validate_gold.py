r"""Checks the gold files: quotes exist in the documents, labels are valid.
Run from the project root:
    python tools\validate_gold.py                 (data\eval)
    python tools\validate_gold.py data/heldout    (the held-out set)"""
import glob
import json
import os
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "data/eval"
TYPES = {"functional", "non_functional", "business_rule", "constraint",
         "assumption", "dependency", "open_question"}
KINDS = {"ambiguous", "incomplete", "duplicate", "conflict", "non_testable"}

errors, n_req, n_issue = [], 0, 0
paths = sorted(glob.glob(f"{BASE}/gold/*.json"))
for path in paths:
    name = os.path.basename(path)
    gold = json.load(open(path, encoding="utf-8"))
    text = open(f"{BASE}/docs/{gold['doc']}", encoding="utf-8").read()
    ids = set()
    for r in gold["requirements"]:
        n_req += 1
        ids.add(r["id"])
        if r["quote"] not in text:
            errors.append(f"{name}: quote not in document: {r['quote'][:50]}")
        if r["type"] not in TYPES:
            errors.append(f"{name}: bad type {r['type']}")
    for i in gold["issues"]:
        n_issue += 1
        if i["kind"] not in KINDS:
            errors.append(f"{name}: bad kind {i['kind']}")
        if not set(i["req_ids"]) <= ids:
            errors.append(f"{name}: unknown id in {i}")
        if i["kind"] in ("duplicate", "conflict") and len(i["req_ids"]) != 2:
            errors.append(f"{name}: {i['kind']} needs two requirements")
print(f"{len(paths)} gold files, {n_req} requirements, {n_issue} issues")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("OK")
