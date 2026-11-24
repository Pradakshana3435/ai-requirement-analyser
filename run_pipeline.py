import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import os
import sys

from ingest.extract import extract_text
from pipeline import run_analysis

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

result = run_analysis(doc, progress=lambda name, p: print(f"[{p:>4.0%}] {name}"))

os.makedirs("output", exist_ok=True)
with open("output/analysis.json", "w", encoding="utf-8") as f:
    f.write(result.model_dump_json(indent=2))

print("\nSummary:", result.summary)
print(f"{len(result.requirements)} requirements, {len(result.findings)} findings, "
      f"{len(result.suggestions)} suggestions")
print("warnings:", result.warnings)