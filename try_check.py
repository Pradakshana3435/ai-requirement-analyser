import sys

from ingest.extract import extract_text
from ingest.split import split_requirements
from analysis.classify import classify_requirements
from analysis.quality import analyze_quality
from analysis.pairs import find_duplicates_conflicts
from analysis.suggest import generate_suggestions
from validate.new_facts import check_new_facts

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

reqs, w1 = split_requirements(doc)
w2 = classify_requirements(reqs)
f1, w3 = analyze_quality(doc, reqs)
f2, w4 = find_duplicates_conflicts(doc, reqs)
suggestions, w5 = generate_suggestions(reqs, f1 + f2)
w6 = check_new_facts(reqs, suggestions)

text_by_id = {r.req_id: r.text for r in reqs}
flagged = [s for s in suggestions if not s.grounded]
for s in flagged:
    print(f"\n{s.req_id}: {text_by_id[s.req_id]}")
    print(f"   {s.kind.value}: {s.content}")
    print(f"   added terms: {s.added_terms or 'none (not verified)'}")

print(f"\n{len(suggestions)} suggestions, {len(flagged)} flagged as unsupported")
print("warnings:", w1 + w2 + w3 + w4 + w5 + w6)