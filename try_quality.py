import sys
from ingest.extract import extract_text
from ingest.split import split_requirements
from analysis.classify import classify_requirements
from analysis.quality import analyze_quality

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())

reqs, w1 = split_requirements(doc)
w2 = classify_requirements(reqs)
findings, w3 = analyze_quality(doc, reqs)

text_by_id = {r.req_id: r.text for r in reqs}
for fd in findings:
    ev = fd.evidence[0].quote if fd.evidence else "NO EVIDENCE"
    flag = "ok" if fd.grounded else "UNSUPPORTED"
    print(f"[{fd.severity.value:<6}] {fd.kind.value:<12} {fd.req_ids[0]} ({flag})")
    print(f"    req:      {text_by_id[fd.req_ids[0]]}")
    print(f"    evidence: {ev!r}")
    print(f"    reason:   {fd.reason}")
print(len(findings), "findings. warnings:", w1 + w2 + w3)