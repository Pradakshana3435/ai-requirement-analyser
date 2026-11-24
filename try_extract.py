import sys
from ingest.extract import extract_text

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())
print(len(doc.raw_text), "characters")
print(doc.raw_text[:500])