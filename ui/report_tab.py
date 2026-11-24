import streamlit as st

from export.report import build_sections, to_csv, to_docx, to_markdown

RESULT_KEY = "result"  # change this to the key your review_tab.py uses


def render_report_tab():
    result = st.session_state.get(RESULT_KEY)
    if result is None:
        st.info("Run an analysis on the Input tab first.")
        return

    st.subheader("Report")
    st.caption(
        "Items you rejected are left out of the main report and listed in an appendix. "
        "Items not yet reviewed are labelled as such."
    )

    sections = {s.title: s for s in build_sections(result)}
    status = sections["Review Status"]
    st.markdown("**Review progress**")
    st.dataframe(
        [dict(zip(status.headers, row)) for row in status.rows],
        hide_index=True,
        width="stretch",
    )

    summary = sections["Requirement Summary"].text
    with st.expander("Summary", expanded=True):
        st.write(summary)

    base = (result.document.filename or "requirements").rsplit(".", 1)[0]
    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "Download Word (.docx)",
        data=to_docx(result),
        file_name=f"{base}_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        width="stretch",
    )
    col2.download_button(
        "Download Excel/CSV",
        data=to_csv(result).encode("utf-8-sig"),
        file_name=f"{base}_report.csv",
        mime="text/csv",
        width="stretch",
    )
    col3.download_button(
        "Download Markdown",
        data=to_markdown(result).encode("utf-8"),
        file_name=f"{base}_report.md",
        mime="text/markdown",
        width="stretch",
    )