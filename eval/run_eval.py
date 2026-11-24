"""Runs the analyser over the evaluation set and writes a report.

From the project root:
    python -m eval.run_eval                 (all documents, resumes if interrupted)
    python -m eval.run_eval --limit 5       (first 5 documents)
    python -m eval.run_eval --only eval_03  (one document)
    python -m eval.run_eval --force         (ignore saved results)
    python -m eval.run_eval --score-only    (rebuild the report from saved results)
"""
import argparse
import glob
import json
import os
import sys
import time

from eval.metrics import aggregate, render_report, review_sheet, score_document

DOCS = "data/eval/docs"
GOLD = "data/eval/gold"
OUT = "output/eval"


def main():
    global DOCS, GOLD, OUT
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--score-only", action="store_true")
    ap.add_argument("--data", default="data/eval")
    args = ap.parse_args()
    DOCS, GOLD = f"{args.data}/docs", f"{args.data}/gold"
    set_name = os.path.basename(os.path.normpath(args.data))
    OUT = "output/eval" if set_name == "eval" else f"output/{set_name}"

    from ingest.extract import extract_text
    from models import AnalysisResult
    from pipeline import run_analysis

    os.makedirs(f"{OUT}/results", exist_ok=True)
    names = sorted(os.path.basename(p)[:-5] for p in glob.glob(f"{GOLD}/*.json"))
    if args.only:
        names = [n for n in names if n == args.only]
    if args.limit:
        names = names[: args.limit]

    start = time.time()
    counts, per_doc, failed, results = [], [], [], []
    for name in names:
        res_path = f"{OUT}/results/{name}.json"
        meta_path = f"{OUT}/results/{name}.meta.json"
        with open(f"{GOLD}/{name}.json", encoding="utf-8") as f:
            gold = json.load(f)
        txt_path = f"{DOCS}/{gold['doc']}"
        if not (os.path.exists(res_path) and not args.force):
            if args.score_only:
                continue
            with open(txt_path, "rb") as f:
                doc = extract_text(txt_path, f.read())
            t0 = time.time()
            try:
                result = run_analysis(doc, progress=lambda step, p: None)
            except Exception as exc:  # keep going; record the failure
                failed.append((name, str(exc)[:200]))
                print(f"{name}: FAILED {str(exc)[:120]}")
                continue
            seconds = time.time() - t0
            with open(res_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({"seconds": seconds}, f)
            print(f"{name}: {len(result.requirements)} requirements, {seconds:.1f}s")
        with open(res_path, encoding="utf-8") as f:
            result = AnalysisResult.model_validate_json(f.read())
        seconds = 0.0
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                seconds = json.load(f).get("seconds", 0.0)
        raw = result.document.raw_text
        counts.append(score_document(raw, gold, result))
        per_doc.append((name, len(result.requirements), len(result.findings),
                        len(result.suggestions), seconds))
        results.append((name, result))

    if not counts:
        print("No results to score.")
        return
    report = render_report(aggregate(counts), per_doc, sum(d[4] for d in per_doc), failed)
    with open(f"{OUT}/report.md", "w", encoding="utf-8") as f:
        f.write(report)
    with open(f"{OUT}/review_sheet.csv", "w", encoding="utf-8-sig", newline="") as f:
        f.write(review_sheet(results))
    print(f"\nWrote {OUT}/report.md and {OUT}/review_sheet.csv")


if __name__ == "__main__":
    main()
