import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ingest.extract import extract_text

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

rows = [line for line in doc.raw_text.split("\n") if line.startswith("FR-")]
print(len(rows), "lines starting with FR-")
for line in rows[:12]:
    print(line[:170])