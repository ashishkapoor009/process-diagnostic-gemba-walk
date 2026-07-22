"""Process Analysis page: runs the six-agent LangGraph diagnostic (PE ->
Automation -> AI -> Kaizen -> Flow -> Reviewer, RAGAS-gated) and displays
the resulting per-step Gemba-walk diagnostics.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.config.settings import get_settings
from app.graphs.visualizations import cycle_time_bar, lean_waste_heatmap, va_nva_pie
from app.ui.pipeline_runner import run_and_persist_pipeline
from app.ui.styling import apply_branding, badge, page_header
from app.utils.logging import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Process Analysis", page_icon="🔍", layout="wide")
apply_branding()
page_header("Process Analysis", "Multi-agent Gemba-walk diagnostic: PE → Automation → AI → Kaizen → Flow → Reviewer (RAGAS-gated)")

settings = get_settings()
metadata = st.session_state.get("process_metadata")
raw_steps = st.session_state.get("raw_steps")

if not metadata or not raw_steps:
    st.warning("Please complete Upload & Intake first.")
    if st.button("⬅️ Go to Upload & Intake"):
        st.switch_page("pages/1_📤_Upload.py")
    st.stop()

if not settings.llm_configured:
    st.error("No LLM credentials configured. Set OPENAI_API_KEY (or AZURE_OPENAI_*) in .env, then reload.")
    st.stop()

st.markdown(
    f"**Process:** {metadata.process_name} &nbsp;|&nbsp; **Steps:** {len(raw_steps)} &nbsp;|&nbsp; "
    f"**FTE:** {metadata.current_fte} &nbsp;|&nbsp; **Volume:** {metadata.current_volume} &nbsp;|&nbsp; "
    f"**AHT:** {metadata.aht_minutes} min"
)

run_col, status_col = st.columns([1, 3])
run_clicked = run_col.button("▶️ Run Multi-Agent Diagnostic", type="primary")

if run_clicked:
    with st.status("Running the six-agent Gemba Walk diagnostic...", expanded=True) as status:
        st.write("🕵️ **PE Agent** conducting Gemba-walk diagnostic (VA/NVA, Lean waste, root cause)...")
        st.write("⚙️ **Automation Agent** evaluating RPA / Power Automate / API opportunities...")
        st.write("🤖 **AI Agentic Agent** evaluating GenAI / Agentic AI opportunities...")
        st.write("📈 **Kaizen Agent** synthesizing Lean, standardization & roadmap horizons...")
        st.write("🔀 **Process Flow Agent** generating current & future-state flow...")
        st.write("🧐 **Reviewer Agent** critically reviewing output, gated by **RAGAS** evaluation...")
        try:
            process_id, final_state = run_and_persist_pipeline(metadata, raw_steps, project_id=None)
            st.session_state.current_process_id = process_id
            st.session_state.final_state = final_state
            status.update(label="Diagnostic complete.", state="complete")
        except Exception as exc:
            status.update(label="Diagnostic failed.", state="error")
            st.error(f"Pipeline error: {exc}")
            logger.exception("Pipeline run failed")
            st.stop()

final_state = st.session_state.get("final_state")
if not final_state:
    st.info("Click 'Run Multi-Agent Diagnostic' to begin.")
    st.stop()

diagnostics = final_state.get("diagnostics", [])
review_notes = final_state.get("review_notes", [])
ragas_scores = final_state.get("ragas_scores", [])

st.divider()
st.subheader("Quality Gate: Reviewer Agent + RAGAS Evaluation")
qc1, qc2, qc3 = st.columns(3)
qc1.markdown(badge(f"Review rounds: {len(review_notes)}", "blue"), unsafe_allow_html=True)
if review_notes:
    last = review_notes[-1]
    verdict_color = "green" if last.verdict == "approved" else "amber"
    qc2.markdown(badge(f"Verdict: {last.verdict}", verdict_color), unsafe_allow_html=True)
    qc3.markdown(badge(f"Reviewer confidence: {last.confidence_score:.0%}", "purple"), unsafe_allow_html=True)

if ragas_scores:
    ragas_df = pd.DataFrame(
        [
            {
                "Round": i + 1, "Faithfulness": s.faithfulness, "Answer Relevancy": s.answer_relevancy,
                "Context Precision": s.context_precision, "Context Recall": s.context_recall,
                "Context Relevancy": s.context_relevancy, "Overall": s.overall,
            }
            for i, s in enumerate(ragas_scores)
        ]
    )
    st.dataframe(ragas_df, use_container_width=True, hide_index=True)
    st.caption(f"RAGAS quality threshold: {settings.ragas_min_score:.0%} overall score.")

st.divider()
st.subheader("Current-State Process Diagnostics")

diag_df = pd.DataFrame(
    [
        {
            "Step": d.step_number, "Name": d.step_name, "Owner": d.owner,
            "Value Class": d.value_classification.value, "Cycle(m)": d.cycle_time_minutes,
            "Wait(m)": d.wait_time_minutes, "Lean Wastes": ", ".join(w.value for w in d.lean_wastes) or "None",
            "Business Risk": d.business_risk.value, "Automation": d.automation_score,
            "AI Readiness": d.ai_readiness_score, "Effort(days)": d.implementation_effort_days,
        }
        for d in diagnostics
    ]
)
st.dataframe(diag_df, use_container_width=True, hide_index=True)

with st.expander("View root-cause analysis per step"):
    for d in diagnostics:
        if d.root_cause:
            st.markdown(f"**Step {d.step_number} - {d.step_name}:** {d.root_cause}")

viz1, viz2 = st.columns(2)
viz1.plotly_chart(va_nva_pie(diagnostics), use_container_width=True)
viz2.plotly_chart(lean_waste_heatmap(diagnostics), use_container_width=True)
st.plotly_chart(cycle_time_bar(diagnostics), use_container_width=True)

if st.button("➡️ View AI Recommendations", type="primary"):
    st.switch_page("pages/3_🤖_AI_Recommendations.py")
