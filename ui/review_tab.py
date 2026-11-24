"""Review tab: source text with highlighted evidence (left), finding and suggestion cards (right)."""
import html
import re

import streamlit as st

from models import ReviewStatus

STATUSES = ["pending", "accepted", "edited", "rejected"]
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_COLOR = {"high": "red", "medium": "orange", "low": "blue"}
PAGE_SIZE = 10
"""Review tab: source text with highlighted evidence (left), finding and suggestion cards (right)."""
import html
import re

import streamlit as st

from models import ReviewStatus

STATUSES = ["pending", "accepted", "edited", "rejected"]
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_COLOR = {"high": "red", "medium": "orange", "low": "blue"}


# ---------- small helpers ----------

def _val(x):
    return str(getattr(x, "value", x))


def _status(item):
    return _val(item.review_status).lower()


def _unsupported(item):
    return not getattr(item, "grounded", True)


def _as_list(x):
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _set_status(obj, name):
    if name == "accepted" and getattr(obj, "edited_content", None):
        name = "edited"  # an analyst-edited item stays "edited"
    try:
        obj.review_status = ReviewStatus(name)
    except ValueError:
        obj.review_status = ReviewStatus[name.upper()]


def _save_edit(obj, text_key):
    text = str(st.session_state.get(text_key, "")).strip()
    if not text or text == str(obj.content).strip():
        return
    obj.edited_content = text
    _set_status(obj, "edited")


def _focus(key):
    st.session_state["review_focus"] = key

def _go_page(delta, last):
    st.session_state["rv_page"] = max(0, min(last, st.session_state.get("rv_page", 0) + delta))

# ---------- evidence location and highlighting ----------

def _flex_find(text, quote, within):
    quote = quote.strip()
    if not quote:
        return None
    pattern = re.compile(r"\s+".join(re.escape(w) for w in quote.split()), re.IGNORECASE)
    for a, b in within:
        m = pattern.search(text, a, b)
        if m:
            return m.span()
    m = pattern.search(text)
    return m.span() if m else None


def _evidence_texts(evidence):
    out = []
    for e in _as_list(evidence):
        q = getattr(e, "quote", e)
        if isinstance(q, str) and q.strip():
            out.append(q.strip())
    return out


def _evidence_ranges(doc, evidence, within):
    ranges = []
    for e in _as_list(evidence):
        if hasattr(e, "start") and hasattr(e, "end"):
            ranges.append((e.start, e.end))
            continue
        q = getattr(e, "quote", e)
        if isinstance(q, str):
            r = _flex_find(doc.raw_text, q, within)
            if r:
                ranges.append(r)
    return ranges


def _req_ids(kind, obj):
    return list(obj.req_ids) if kind == "finding" else [obj.req_id]


def _highlight_html(text, light, strong, start, end):
    levels = [0] * (end - start)
    for ranges, level in ((light, 1), (strong, 2)):
        for a, b in ranges:
            for i in range(max(a, start), min(b, end)):
                levels[i - start] = level
    out, i = [], 0
    while i < len(levels):
        j = i
        while j < len(levels) and levels[j] == levels[i]:
            j += 1
        chunk = html.escape(text[start + i:start + j]).replace("\n", "<br>")
        if levels[i] == 2:
            out.append(f'<mark style="background:#ffb347;color:#000">{chunk}</mark>')
        elif levels[i] == 1:
            out.append(f'<span style="background:#fff3b0;color:#000">{chunk}</span>')
        else:
            out.append(chunk)
        i = j
    return '<div style="line-height:1.7">' + "".join(out) + "</div>"


# ---------- panes ----------

def _render_source(doc, reqs, focus):
    st.subheader("Source text")
    text = doc.raw_text
    light, strong = [], []
    if focus:
        kind, key, obj = focus
        within = []
        for rid in _req_ids(kind, obj):
            r = reqs.get(rid)
            if r is not None:
                within.append((r.source_span.start, r.source_span.end))
        light = within
        strong = _evidence_ranges(doc, obj.evidence, within)
    full = st.checkbox("Show full document", key="rv_full")
    if full or not focus:
        start, end = 0, len(text) if full else min(len(text), 1500)
    else:
        spans = strong or light
        if spans:
            start = max(0, min(a for a, _ in spans) - 400)
            end = min(len(text), max(b for _, b in spans) + 400)
        else:
            start, end = 0, min(len(text), 1500)
    if not focus:
        st.caption("Click 'Show in source' on a card to highlight its evidence here.")
    else:
        st.caption("Orange = evidence quote, yellow = the linked requirement.")
    if start > 0:
        st.caption("...")
    st.markdown(_highlight_html(text, light, strong, start, end), unsafe_allow_html=True)
    if end < len(text):
        st.caption("...")


def _card(kind, key, obj, reqs):
    status = _status(obj)
    unsupported = _unsupported(obj)
    with st.container(border=True):
        head = f"**{_val(obj.kind).replace('_', ' ').title()}**"
        if kind == "finding":
            sev = _val(obj.severity).lower()
            head += f" · :{SEVERITY_COLOR.get(sev, 'gray')}[{sev.upper()}]"
        else:
            head += " · suggestion"
        head += f" · status: **{status}**"
        if unsupported:
            head += " · :red[Unsupported]"
        st.markdown(head)

        for rid in _req_ids(kind, obj):
            r = reqs.get(rid)
            if r is not None:
                st.caption(f"{rid}: {r.text[:200]}")

        if kind == "finding":
            st.write(obj.reason)
        else:
            edited = getattr(obj, "edited_content", None)
            if edited:
                st.markdown("**Analyst version**")
                st.write(edited)
                with st.expander("AI original"):
                    st.write(obj.content)
            else:
                st.write(obj.content)
            terms = getattr(obj, "added_terms", None)
            if terms:
                st.markdown("Added terms not found in source: " + ", ".join(f"`{t}`" for t in terms))

        for q in _evidence_texts(obj.evidence):
            st.markdown("> " + q)

        confirmed = True
        if unsupported:
            confirmed = st.checkbox(
                "I checked the source and confirm this is supported",
                key=f"{key}-confirm",
            )

        c1, c2, c3, c4 = st.columns(4)
        c1.button("Show in source", key=f"{key}-focus", on_click=_focus, args=(key,))
        c2.button(
            "Accept",
            key=f"{key}-accept",
            on_click=_set_status,
            args=(obj, "accepted"),
            disabled=(not confirmed) or status in ("accepted", "edited"),
        )
        c3.button("Reject", key=f"{key}-reject", on_click=_set_status, args=(obj, "rejected"))
        c4.button("Reset", key=f"{key}-reset", on_click=_set_status, args=(obj, "pending"))

        if kind == "suggestion":
            with st.expander("Edit"):
                tk = f"{key}-edit"
                st.text_area(
                    "Your version",
                    value=getattr(obj, "edited_content", None) or obj.content,
                    key=tk,
                    height=110,
                )
                st.button("Save edit", key=f"{key}-save", on_click=_save_edit, args=(obj, tk))


# ---------- main entry ----------

def render_review_tab():
    result = st.session_state.get("result")
    if result is None:
        st.info("Run an analysis on the Input tab first.")
        return

    doc = result.document
    reqs = {r.req_id: r for r in result.requirements}

    items = []
    for f in sorted(result.findings, key=lambda f: SEVERITY_ORDER.get(_val(f.severity).lower(), 3)):
        items.append(("finding", f"finding:{f.finding_id}", f))
    for s in result.suggestions:
        items.append(("suggestion", f"suggestion:{s.sugg_id}", s))
    lookup = {key: (kind, key, obj) for kind, key, obj in items}

    # counters
    counts = {s: 0 for s in STATUSES}
    for _, _, obj in items:
        counts[_status(obj)] = counts.get(_status(obj), 0) + 1
    total = len(items)
    reviewed = total - counts["pending"]
    cols = st.columns(5)
    cols[0].metric("Pending", counts["pending"])
    cols[1].metric("Accepted", counts["accepted"])
    cols[2].metric("Edited", counts["edited"])
    cols[3].metric("Rejected", counts["rejected"])
    cols[4].metric("Unsupported", sum(1 for _, _, o in items if _unsupported(o)))
    st.progress(reviewed / total if total else 0.0, text=f"{reviewed} of {total} reviewed")

    # filters
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    status_sel = f1.multiselect("Status", STATUSES, default=STATUSES, key="rv_status")
    type_sel = f2.multiselect(
        "Show", ["finding", "suggestion"], default=["finding", "suggestion"], key="rv_type"
    )
    kinds = sorted({_val(o.kind) for _, _, o in items})
    kind_sel = f3.multiselect("Kind", kinds, default=kinds)
    only_unsup = f4.checkbox("Unsupported only", key="rv_unsup")

    shown = [
        (k, key, o)
        for k, key, o in items
        if k in type_sel
        and _status(o) in status_sel
        and _val(o.kind) in kind_sel
        and (not only_unsup or _unsupported(o))
    ]

    # paging: reset to page 1 whenever a filter changes
    signature = (tuple(status_sel), tuple(type_sel), tuple(kind_sel), only_unsup)
    if st.session_state.get("rv_sig") != signature:
        st.session_state["rv_sig"] = signature
        st.session_state["rv_page"] = 0
    last = max(0, (len(shown) - 1) // PAGE_SIZE)
    page = max(0, min(last, st.session_state.get("rv_page", 0)))
    st.session_state["rv_page"] = page
    visible = shown[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    left, right = st.columns(2)
    with left:
        _render_source(doc, reqs, lookup.get(st.session_state.get("review_focus")))
    with right:
        st.subheader(f"Findings and suggestions ({len(shown)})")
        n1, n2, n3 = st.columns([1, 2, 1])
        n1.button("Previous", key="rv_prev", on_click=_go_page, args=(-1, last), disabled=page == 0)
        n2.markdown(f"Page {page + 1} of {last + 1}")
        n3.button("Next", key="rv_next", on_click=_go_page, args=(1, last), disabled=page >= last)
        with st.container(height=700):
            if not visible:
                st.info("No items match the filters.")
            for kind, key, obj in visible:
                _card(kind, key, obj, reqs)