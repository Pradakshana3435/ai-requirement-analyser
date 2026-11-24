import sys
from ingest.extract import extract_text
from ingest.split import split_requirements
from analysis.classify import classify_requirements
from analysis.pairs import find_duplicates_conflicts, shortlist_pairs

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

reqs, w1 = split_requirements(doc)
w2 = classify_requirements(reqs)
print("candidate pairs sent to the model:", len(shortlist_pairs(reqs)))

findings, w3 = find_duplicates_conflicts(doc, reqs)
text_by_id = {r.req_id: r.text for r in reqs}
for fd in findings:
    print(f"\n[{fd.severity.value}] {fd.kind.value.upper()}  {fd.req_ids}  grounded={fd.grounded}")
    for rid in fd.req_ids:
        print(f"   {rid}: {text_by_id[rid]}")
    print(f"   reason: {fd.reason}")
print("\nwarnings:", w1 + w2 + w3)