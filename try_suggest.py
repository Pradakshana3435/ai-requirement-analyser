import sys
from collections import defaultdict

from ingest.extract import extract_text
from ingest.split import split_requirements
from analysis.classify import classify_requirements
from analysis.quality import analyze_quality
from analysis.pairs import find_duplicates_conflicts
from analysis.suggest import generate_suggestions

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

reqs, w1 = split_requirements(doc)
w2 = classify_requirements(reqs)
f1, w3 = analyze_quality(doc, reqs)
f2, w4 = find_duplicates_conflicts(doc, reqs)
suggestions, w5 = generate_suggestions(reqs, f1 + f2)

by_req = defaultdict(list)
for s in suggestions:
    by_req[s.req_id].append(s)

for r in reqs:
    if r.req_id not in by_req:
        continue
    print(f"\n{r.req_id} [{r.type.value if r.type else '?'}] {r.text}")
    for s in by_req[r.req_id]:
        print(f"   {s.kind.value:<24} {s.content}")

print("\ntotal suggestions:", len(suggestions))
print("warnings:", w1 + w2 + w3 + w4 + w5)