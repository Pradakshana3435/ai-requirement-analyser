import sys

from export.report import to_csv, to_docx, to_markdown
from models import AnalysisResult

with open("output/analysis.json", encoding="utf-8") as f:
    result = AnalysisResult.model_validate_json(f.read())

with open("output/report.docx", "wb") as f:
    f.write(to_docx(result))
with open("output/report.md", "w", encoding="utf-8") as f:
    f.write(to_markdown(result))
with open("output/report.csv", "w", encoding="utf-8-sig", newline="") as f:
    f.write(to_csv(result))
print("saved output\\report.docx, report.md, report.csv")