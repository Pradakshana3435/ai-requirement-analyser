import streamlit as st

import config
from ingest.extract import ExtractionError, extract_text, from_pasted_text
from llm.client import LLMError
from pipeline import run_analysis


def _analyse(pasted: str, uploaded) -> None:
    try:
        if uploaded is not None:
            doc = extract_text(uploaded.name, uploaded.getvalue())
        elif pasted.strip():
            doc = from_pasted_text(pasted)
        else:
            st.error("Paste some text or upload a file first.")
            return
    except ExtractionError as exc:
        st.error(str(exc))
        return

    bar = st.progress(0.0, text="Starting...")

    def progress(name: str, fraction: float) -> None:
        bar.progress(min(fraction, 1.0), text=name)

    try:
        result = run_analysis(doc, progress=progress)
    except (LLMError, RuntimeError) as exc:
        bar.empty()
        st.error(f"Analysis failed: {exc}")
        return

    bar.empty()
    st.session_state["result"] = result


def render_input() -> None:
    st.subheader("Submit requirements")

    pasted = st.text_area(
        "Paste requirements",
        height=220,
        placeholder="Paste emails, meeting notes or requirement text here...",
    )
    uploaded = st.file_uploader("...or upload a file (PDF, DOCX or TXT)", type=["pdf", "docx", "txt"])
    st.caption(
        f"Maximum file size: {config.MAX_UPLOAD_MB} MB. If you provide both, the uploaded file is used. "
        "Text is sent to the AI model for analysis, so use synthetic or sanitised documents only."
    )

    if st.button("Analyse", type="primary"):
        _analyse(pasted, uploaded)

    result = st.session_state.get("result")
    if result is not None:
        st.success(
            f"Analysed '{result.document.filename}': {len(result.requirements)} requirements, "
            f"{len(result.findings)} findings, {len(result.suggestions)} suggestions. "
            "Open the Inventory tab."
        )
        for warning in result.warnings:
            st.warning(warning)
        with st.expander("Extracted text"):
            st.text(result.document.raw_text)