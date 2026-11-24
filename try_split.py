import sys
from ingest.extract import extract_text
from ingest.split import split_requirements

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

reqs, warnings = split_requirements(doc)
for r in reqs:
    print(r.req_id, (r.source_span.start, r.source_span.end), r.text)
print("warnings:", warnings)