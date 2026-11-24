"""Pure scoring functions for the evaluation. They only read attributes of the
analysis result, so they work on real AnalysisResult objects and on test stubs."""
import csv
import difflib
import io
import re
from collections import Counter, defaultdict

ISSUE_KINDS = ["ambiguous", "incomplete", "duplicate", "conflict", "non_testable"]
TYPES = ["functional", "non_functional", "business_rule", "constraint",
         "assumption", "dependency", "open_question"]


def _v(x):
    return getattr(x, "value", x)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _iou(a, b):
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def match_requirements(raw_text, gold_reqs, pred_reqs, min_iou=0.5, min_text=0.8):
    """Greedy one-to-one match. Returns {gold_id: predicted Requirement}."""
    cands = []
    for g in gold_reqs:
        start = raw_text.find(g["quote"])
        gspan = (start, start + len(g["quote"])) if start >= 0 else None
        for p in pred_reqs:
            score = 0.0
            span = getattr(p, "source_span", None)
            if gspan and span is not None:
                score = _iou(gspan, (span.start, span.end))
                if score < min_iou:
                    score = 0.0
            if score == 0.0:
                ratio = difflib.SequenceMatcher(None, _norm(g["quote"]), _norm(p.text)).ratio()
                score = ratio if ratio >= min_text else 0.0
            if score > 0:
                cands.append((score, g["id"], p.req_id, p))
    cands.sort(key=lambda c: -c[0])
    used_g, used_p, out = set(), set(), {}
    for _, gid, pid, p in cands:
        if gid in used_g or pid in used_p:
            continue
        used_g.add(gid)
        used_p.add(pid)
        out[gid] = p
    return out


def _issue_matches(gold_issue, pred_finding, g2p):
    if _v(pred_finding.kind) != gold_issue["kind"]:
        return False
    wanted = {g2p[g].req_id for g in gold_issue["req_ids"] if g in g2p}
    if len(wanted) < len(gold_issue["req_ids"]):
        return False  # a requirement of this issue was never found
    have = set(pred_finding.req_ids)
    return len(wanted & have) >= (2 if len(wanted) >= 2 else 1)


def score_document(raw_text, gold, result):
    """Returns a dict of raw counts for one document (summed later)."""
    c = Counter()
    g2p = match_requirements(raw_text, gold["requirements"], result.requirements)
    c["req_gold"] = len(gold["requirements"])
    c["req_pred"] = len(result.requirements)
    c["req_matched"] = len(g2p)
    for g in gold["requirements"]:
        p = g2p.get(g["id"])
        if p is not None:
            c["type_total"] += 1
            if _v(p.type) == g["type"]:
                c["type_correct"] += 1
            c[f"confusion|{g['type']}|{_v(p.type)}"] += 1

    for kind in ISSUE_KINDS:
        gold_k = [i for i in gold["issues"] if i["kind"] == kind]
        pred_k = [f for f in result.findings if _v(f.kind) == kind]
        c[f"{kind}|gold"] = len(gold_k)
        c[f"{kind}|pred"] = len(pred_k)
        c[f"{kind}|gold_hit"] = sum(
            1 for gi in gold_k if any(_issue_matches(gi, pf, g2p) for pf in pred_k))
        c[f"{kind}|pred_hit"] = sum(
            1 for pf in pred_k if any(_issue_matches(gi, pf, g2p) for gi in gold_k))

    reqs = result.requirements
    c["span_total"] = len(reqs)
    doc = getattr(result, "document", None)
    for r in reqs:
        span = getattr(r, "source_span", None)
        if span is not None and (doc is None or not hasattr(doc, "span_is_valid")
                                 or doc.span_is_valid(span)):
            c["span_valid"] += 1
    c["finding_total"] = len(result.findings)
    c["finding_grounded"] = sum(1 for f in result.findings if getattr(f, "grounded", True))
    checked = [s for s in result.suggestions if _v(s.kind) != "clarification_question"]
    c["sugg_total"] = len(checked)
    c["sugg_unsupported"] = sum(1 for s in checked if not getattr(s, "grounded", True))
    c["warnings"] = len(getattr(result, "warnings", []) or [])
    return c


def _prf(tp_p, n_p, tp_g, n_g):
    precision = tp_p / n_p if n_p else None
    recall = tp_g / n_g if n_g else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else (0.0 if precision is not None and recall is not None else None))
    return precision, recall, f1


def aggregate(counts_list):
    """Sums per-document counters and derives the report metrics."""
    t = Counter()
    for c in counts_list:
        t.update(c)
    m = {}
    p, r, f = _prf(t["req_matched"], t["req_pred"], t["req_matched"], t["req_gold"])
    m["split"] = {"precision": p, "recall": r, "f1": f}
    m["type_accuracy"] = t["type_correct"] / t["type_total"] if t["type_total"] else None
    m["issues"] = {}
    tot = Counter()
    for kind in ISSUE_KINDS:
        p, r, f = _prf(t[f"{kind}|pred_hit"], t[f"{kind}|pred"], t[f"{kind}|gold_hit"], t[f"{kind}|gold"])
        m["issues"][kind] = {"precision": p, "recall": r, "f1": f, "gold": t[f"{kind}|gold"],
                             "predicted": t[f"{kind}|pred"]}
        for k in ("pred_hit", "pred", "gold_hit", "gold"):
            tot[k] += t[f"{kind}|{k}"]
    p, r, f = _prf(tot["pred_hit"], tot["pred"], tot["gold_hit"], tot["gold"])
    m["issues"]["overall"] = {"precision": p, "recall": r, "f1": f, "gold": tot["gold"],
                              "predicted": tot["pred"]}
    m["span_valid_rate"] = t["span_valid"] / t["span_total"] if t["span_total"] else None
    m["finding_grounded_rate"] = t["finding_grounded"] / t["finding_total"] if t["finding_total"] else None
    m["unsupported_rate"] = t["sugg_unsupported"] / t["sugg_total"] if t["sugg_total"] else None
    m["confusion"] = {k: v for k, v in t.items() if k.startswith("confusion|")}
    m["warnings"] = t["warnings"]
    return m


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render_report(metrics, per_doc, seconds, failed):
    """per_doc: list of (name, requirements, findings, suggestions, seconds)."""
    lines = ["# Evaluation Report", ""]
    n = len(per_doc)
    lines += [f"Documents evaluated: {n}" + (f" ({len(failed)} failed)" if failed else ""), ""]
    s = metrics["split"]
    lines += ["## Requirement splitting", "",
              "| Metric | Value |", "| --- | --- |",
              f"| Precision | {_pct(s['precision'])} |", f"| Recall | {_pct(s['recall'])} |",
              f"| F1 | {_pct(s['f1'])} |", ""]
    lines += ["## Classification", "", f"Type accuracy on matched requirements: {_pct(metrics['type_accuracy'])}", ""]
    conf = defaultdict(dict)
    for k, v in metrics["confusion"].items():
        _, g, p = k.split("|")
        conf[g][p] = v
    cols = TYPES + ["None"]
    lines += ["| Gold \\ Predicted | " + " | ".join(cols) + " |", "| --- |" + " --- |" * len(cols)]
    for g in TYPES:
        lines.append(f"| {g} | " + " | ".join(str(conf[g].get(c, 0)) for c in cols) + " |")
    lines += ["", "## Issue detection", "",
              "| Issue | Gold | Predicted | Precision | Recall | F1 |", "| --- | --- | --- | --- | --- | --- |"]
    for kind in ISSUE_KINDS + ["overall"]:
        i = metrics["issues"][kind]
        lines.append(f"| {kind} | {i['gold']} | {i['predicted']} | {_pct(i['precision'])} | "
                     f"{_pct(i['recall'])} | {_pct(i['f1'])} |")
    lines += ["", "## Grounding and unsupported facts", "",
              f"- Requirements with a valid source span: {_pct(metrics['span_valid_rate'])}",
              f"- Findings grounded in the text: {_pct(metrics['finding_grounded_rate'])}",
              f"- Suggestions flagged as unsupported by the new-fact check: {_pct(metrics['unsupported_rate'])}",
              f"- Pipeline warnings: {metrics['warnings']}", ""]
    avg = sum(d[4] for d in per_doc) / n if n else 0
    lines += ["## Speed", "", f"- Average time per document: {avg:.1f} s", f"- Total: {seconds:.0f} s", ""]
    lines += ["## Per document", "",
              "| Document | Requirements | Findings | Suggestions | Seconds |", "| --- | --- | --- | --- | --- |"]
    for name, rq, fd, sg, sec in per_doc:
        lines.append(f"| {name} | {rq} | {fd} | {sg} | {sec:.1f} |")
    if failed:
        lines += ["", "## Failed documents", ""] + [f"- {name}: {err}" for name, err in failed]
    lines += ["", "## Notes", "",
              "- Gold labels were written by the project author; a second reviewer would strengthen them.",
              "- Precision on issues counts a finding as correct only if it matches a planted issue; "
              "real issues the author did not plant count against precision.",
              "- BA usefulness is scored by hand with output/eval/review_sheet.csv.", ""]
    return "\n".join(lines)


def review_sheet(results, per_kind=1, max_rows=40):
    """CSV of suggestions for a Business Analyst to rate by hand, sampled across all documents."""
    rows = []
    for name, result in results:
        seen = Counter()
        for s in result.suggestions:
            k = _v(s.kind)
            if seen[k] >= per_kind:
                continue
            seen[k] += 1
            rows.append([name, s.req_id, k, getattr(s, "content", ""), "", "", ""])
    if len(rows) > max_rows:
        step = len(rows) / max_rows
        rows = [rows[int(i * step)] for i in range(max_rows)]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["document", "requirement", "kind", "suggestion",
                "usefulness_1_to_5", "accurate_yes_no", "notes"])
    w.writerows(rows)
    return buf.getvalue()
