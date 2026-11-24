import sys
from ingest.extract import extract_text
from ingest.split import split_requirements
from analysis.classify import classify_requirements

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

reqs, split_warnings = split_requirements(doc)
class_warnings = classify_requirements(reqs)

for r in reqs:
    t = r.type.value if r.type else "?"
    print(f"{r.req_id}  {t:<15} {r.text}")
print("warnings:", split_warnings + class_warnings)