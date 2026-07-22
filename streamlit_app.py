"""Process Diagnostic / Gemba Walk Multi-Agent Solution - Dashboard (Home).

Entry point for the Streamlit application. Run with:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import streamlit as st

from app.database import crud
from app.ui.styling import APP_SUBTITLE, APP_TITLE, apply_branding, badge, metric_card, page_header
from app.utils.logging import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
apply_branding()

with st.sidebar:
    st.markdown("### 🧭 Gemba Walk Platform")
    st.toggle("🌙 Dark Mode", key="dark_mode")
    st.caption("Process Excellence | Lean Six Sigma | Business Transformation")
    st.divider()
    st.caption("Six specialist ReAct agents, RAG-grounded, RAGAS-evaluated.")

crud.ensure_db_ready()

page_header(APP_TITLE, APP_SUBTITLE)

st.markdown(
    """This platform runs a **multi-agent ReAct diagnostic** - modeled on a
    Lean Six Sigma Gemba walk - across your process, retrieving grounded
    best-practice knowledge (RAG) and generating Lean, Automation, and AI
    improvement opportunities for every step, evaluated automatically with
    **RAGAS** and reviewed by a Senior-Director-level Reviewer Agent."""
)

try:
    projects = crud.list_projects()
    processes = crud.list_processes()
except Exception as exc:
    logger.error(f"Dashboard DB read failed: {exc}")
    projects, processes = [], []

col1, col2, col3, col4 = st.columns(4)
metric_card("Processes Diagnosed", str(len(processes)), col1)
metric_card("Projects", str(len(projects)), col2)
total_recs = 0
avg_efficiency = 0.0
if processes:
    with_summary = 0
    for p in processes:
        full = crud.get_process_full(p["id"])
        proc = full.get("process")
        if proc and proc.savings_summary_json:
            avg_efficiency += proc.savings_summary_json.get("blended_efficiency_improvement_pct", 0)
            with_summary += 1
        total_recs += len(full.get("recommendations", []))
    avg_efficiency = round(avg_efficiency / with_summary, 1) if with_summary else 0.0
metric_card("Total Recommendations Generated", str(total_recs), col3)
metric_card("Avg. Efficiency Improvement", f"{avg_efficiency}%", col4)

st.divider()

left, right = st.columns([2, 1])
with left:
    st.subheader("Recent Process Diagnostics")
    if not processes:
        st.info("No processes analyzed yet. Start your first Gemba walk diagnostic below.")
    else:
        for p in processes[:10]:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(f"**{p['process_name']}**  \n{p['department']} | {p['lob']}")
                c2.markdown(
                    f"FTE: {p['current_fte']} | Volume: {p['current_volume']} | AHT: {p['aht_minutes']}m  \n"
                    f"{p['created_at']:%Y-%m-%d %H:%M}"
                )
                if c3.button("Open ➜", key=f"open_{p['id']}"):
                    st.session_state.current_process_id = p["id"]
                    st.switch_page("pages/4_📄_Reports.py")

with right:
    st.subheader("Get Started")
    st.markdown(
        f"""
        {badge("1. Intake & Analysis", "blue")}<br>Enter process details, add steps (typed or uploaded), and run the six-agent diagnostic - all on one page.<br><br>
        {badge("2. AI Recommendations", "blue")}<br>Review Lean, Automation & AI opportunities.<br><br>
        {badge("3. Process Flow", "blue")}<br>Current vs. future-state flow, bottleneck & priority maps.<br><br>
        {badge("4. Reports", "blue")}<br>Download PDF / Word / Excel / PowerPoint.
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚀 Start New Diagnostic", type="primary", use_container_width=True):
        st.switch_page("pages/1_📋_Process_Intake_&_Analysis.py")

st.divider()
st.caption(
    "Architecture: Streamlit UI · LangGraph ReAct multi-agent workflow · ChromaDB RAG · "
    "RAGAS evaluation · SQLite persistence · OpenAI / Azure OpenAI compatible models."
)
