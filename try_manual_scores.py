import csv
import glob
import json
import os


def rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def yes(value):
    return value.strip().lower().startswith("y")


predicted = 0
for p in glob.glob("output/eval/results/*.json"):
    if not p.endswith(".meta.json"):
        predicted += len(json.load(open(p, encoding="utf-8"))["findings"])

path = "output/eval/unmatched_rated.csv"
if os.path.exists(path):
    unmatched = rows(path)
    marked = [r for r in unmatched if r["valid_yes_no"].strip()]
    if marked:
        share = sum(yes(r["valid_yes_no"]) for r in marked) / len(marked)
        matched = predicted - len(unmatched)
        adjusted = (matched + share * len(unmatched)) / predicted
        print(f"Unmatched findings marked: {len(marked)} of {len(unmatched)}")
        print(f"Share of unmatched that are valid: {share:.0%}")
        print(f"Adjusted issue precision: {adjusted:.1%}  (was {matched / predicted:.1%})")

path = "output/eval/review_sheet_rated.csv"
if os.path.exists(path):
    rated = [r for r in rows(path) if r["usefulness_1_to_5"].strip()]
    if rated:
        scores = [float(r["usefulness_1_to_5"]) for r in rated]
        print(f"\nSuggestions rated: {len(rated)}")
        print(f"Average usefulness: {sum(scores) / len(scores):.2f} / 5")
        print(f"Marked accurate: {sum(yes(r['accurate_yes_no']) for r in rated) / len(rated):.0%}")
        for kind in sorted({r["kind"] for r in rated}):
            ks = [float(r["usefulness_1_to_5"]) for r in rated if r["kind"] == kind]
            print(f"  {kind}: {sum(ks) / len(ks):.2f} ({len(ks)} rated)")