import pandas as pd
import streamlit as st

from models import ReqType, ReviewStatus

UNCLASSIFIED = "unclassified"
TYPES = [UNCLASSIFIED] + [t.value for t in ReqType]


def _type_name(req) -> str:
    return req.type.value if req.type else UNCLASSIFIED


def _apply_edits(edited: pd.DataFrame, reqs) -> bool:
    """Write analyst edits back to the requirements. Returns True if anything changed."""
    by_id = {r.req_id: r for r in reqs}
    changed = False
    for _, row in edited.iterrows():
        req = by_id[row["ID"]]
        new_text = str(row["Requirement"]).strip()
        new_type = None if row["Type"] == UNCLASSIFIED else ReqType(row["Type"])
        if not new_text:
            continue
        if new_text != req.text or new_type != req.type:
            req.text = new_text
            req.type = new_type
            req.review_status = ReviewStatus.EDITED
            changed = True
    return changed


def render_inventory() -> None:
    result = st.session_state.get("result")
    if result is None:
        st.info("Run an analysis on the Input tab first.")
        return

    reqs = result.requirements
    c1, c2, c3 = st.columns(3)
    c1.metric("Requirements", len(reqs))
    c2.metric("Findings", len(result.findings))
    c3.metric("Suggestions", len(result.suggestions))

    if result.summary:
        st.markdown(f"**Summary.** {result.summary}")

    chosen = st.multiselect("Filter by type", TYPES)
    shown = [r for r in reqs if not chosen or _type_name(r) in chosen]

    df = pd.DataFrame(
        [
            {
                "ID": r.req_id,
                "Type": _type_name(r),
                "Requirement": r.text,
                "Source": f"{r.source_span.start}-{r.source_span.end}" if r.source_span else "",
                "Status": r.review_status.value,
            }
            for r in shown
        ]
    )
    if df.empty:
        st.info("No requirements match this filter.")
        return

    st.caption("Edit the Type or Requirement cells directly. Edited rows are marked 'edited'.")
    edited = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        disabled=["ID", "Source", "Status"],
        column_config={
            "Type": st.column_config.SelectboxColumn("Type", options=TYPES, required=True),
            "Requirement": st.column_config.TextColumn("Requirement", width="large"),
        },
        key="inventory_editor_" + "_".join(sorted(chosen)),
    )

    if _apply_edits(edited, reqs):
        st.rerun()