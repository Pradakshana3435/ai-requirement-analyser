import streamlit as st
from ui.report_tab import render_report_tab
import config
from ui.input_tab import render_input
from ui.inventory_tab import render_inventory
from ui.review_tab import render_review_tab

st.set_page_config(page_title="AI Requirement Analyser", layout="wide")
st.title("AI Requirement Analyser")
st.caption("AI output is a suggestion, not an approved requirement. A Business Analyst reviews everything.")

with st.sidebar:
    st.markdown("**Model**")
    st.write(f"{config.LLM_PROVIDER}: {config.GROQ_MODEL}")
    if st.button("Start over"):
        st.session_state.clear()
        st.rerun()

VIEWS = ["1. Input", "2. Inventory", "3. Review", "4. Report"]
view = st.radio("View", VIEWS, horizontal=True, label_visibility="collapsed", key="view")

if view == VIEWS[0]:
    render_input()
elif view == VIEWS[1]:
    render_inventory()
elif view == VIEWS[2]:
    render_review_tab()
else:
    render_report_tab()