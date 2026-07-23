"""Process Intake & Analysis - a single, simplified page: tell us about the
process (mandatory fields up front, optional details tucked away), give us
the steps (typed or uploaded), and run the six-agent Gemba-walk diagnostic -
all without leaving this page.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.config.settings import get_settings
from app.extraction.document_parser import parse_document
from app.extraction.step_extractor import extract_steps_from_text, parse_manual_steps
from app.graphs.visualizations import cycle_time_bar, lean_waste_heatmap, va_nva_pie
from app.schemas.process import ProcessMetadata, ProcessStepInput
from app.ui.pipeline_runner import run_and_persist_pipeline
from app.ui.styling import apply_branding, badge, page_header
from app.utils.logging import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Process Intake & Analysis", page_icon="📋", layout="wide")
apply_branding()
page_header(
    "Process Intake & Analysis",
    "Tell us about the process, give us the steps, and run the multi-agent Gemba-walk diagnostic.",
)

settings = get_settings()
if not settings.llm_configured:
    st.warning("No LLM credentials configured yet. Set OPENAI_API_KEY (or the AZURE_OPENAI_* variables) in your .env file.")

# ---------------------------------------------------------------------------
# Step 1: Process metadata (mandatory fields up front, optional in an expander)
# ---------------------------------------------------------------------------
st.subheader("1. Process Details")
with st.form("process_metadata_form"):
    c1, c2, c3 = st.columns(3)
    process_name = c1.text_input("Process Name*", value=st.session_state.get("meta_process_name", ""))
    team_name = c2.text_input("Team Name*", value=st.session_state.get("meta_team_name", ""))
    lob = c3.text_input("LOB (Line of Business)*", value=st.session_state.get("meta_lob", ""))

    c4, c5, c6, c7 = st.columns(4)
    current_fte = c4.number_input("Current FTE*", min_value=0.1, value=st.session_state.get("meta_fte", 5.0), step=0.5)
    current_volume = c5.number_input("Current Volume (per period)*", min_value=1.0, value=st.session_state.get("meta_volume", 1000.0), step=10.0)
    aht_minutes = c6.number_input("Average Handle Time - AHT (minutes)*", min_value=0.1, value=st.session_state.get("meta_aht", 15.0), step=0.5)
    annual_fte_cost = c7.number_input(
        "Annual FTE Cost ($)*", min_value=1.0, value=st.session_state.get("meta_fte_cost", 35000.0), step=1000.0,
        help="Fully-loaded annual cost per FTE - used to calculate In-Year and 12-Month savings.",
    )

    with st.expander("➕ Optional details (pain areas, dependencies, risks, systems...)"):
        o1, o2 = st.columns(2)
        pain_areas = o1.text_area("Pain Areas", value=st.session_state.get("meta_pain_areas", ""))
        dependencies = o2.text_area("Dependencies", value=st.session_state.get("meta_dependencies", ""))
        o3, o4 = st.columns(2)
        customer_complaints = o3.text_area("Customer Complaints", value=st.session_state.get("meta_complaints", ""))
        known_risks = o4.text_area("Known Risks", value=st.session_state.get("meta_risks", ""))
        o5, o6 = st.columns(2)
        current_sla = o5.text_input("Current SLA", value=st.session_state.get("meta_sla", ""))
        compliance_requirements = o6.text_area("Compliance Requirements", value=st.session_state.get("meta_compliance", ""))
        o7, o8 = st.columns(2)
        applications_used = o7.text_input("Applications Used", value=st.session_state.get("meta_apps", ""))
        systems_used = o8.text_input("Systems Used", value=st.session_state.get("meta_systems", ""))
        o9, o10 = st.columns(2)
        manual_activities = o9.text_area("Manual Activities", value=st.session_state.get("meta_manual", ""))
        automation_already_implemented = o10.text_area("Automation Already Implemented", value=st.session_state.get("meta_auto_done", ""))

    submitted = st.form_submit_button("💾 Save Process Details", type="primary")

    if submitted:
        try:
            metadata = ProcessMetadata(
                process_name=process_name, team_name=team_name,
                current_fte=current_fte, current_volume=current_volume, aht_minutes=aht_minutes,
                lob=lob, annual_fte_cost=annual_fte_cost, pain_areas=pain_areas or None, customer_complaints=customer_complaints or None,
                dependencies=dependencies or None, current_sla=current_sla or None, known_risks=known_risks or None,
                applications_used=applications_used or None, systems_used=systems_used or None,
                manual_activities=manual_activities or None,
                automation_already_implemented=automation_already_implemented or None,
                compliance_requirements=compliance_requirements or None,
            )
            st.session_state.process_metadata = metadata
            for k, v in {
                "meta_process_name": process_name, "meta_team_name": team_name, "meta_fte": current_fte,
                "meta_volume": current_volume, "meta_aht": aht_minutes, "meta_lob": lob, "meta_fte_cost": annual_fte_cost,
                "meta_pain_areas": pain_areas, "meta_complaints": customer_complaints,
                "meta_dependencies": dependencies, "meta_sla": current_sla, "meta_risks": known_risks,
                "meta_compliance": compliance_requirements, "meta_apps": applications_used,
                "meta_systems": systems_used, "meta_manual": manual_activities, "meta_auto_done": automation_already_implemented,
            }.items():
                st.session_state[k] = v
            st.success("Saved.")
        except Exception as exc:
            st.error(f"Please check the mandatory fields: {exc}")

# ---------------------------------------------------------------------------
# Step 2: Process steps - type or upload
# ---------------------------------------------------------------------------
st.subheader("2. Process Steps")
tab_manual, tab_upload = st.tabs(["✍️ Type Steps", "📎 Upload Process Map"])

with tab_manual:
    st.caption("One step per line. Optional format: `Step name :: Owner :: System :: Cycle time (min)`")
    manual_text = st.text_area("Process steps", height=180, label_visibility="collapsed", placeholder=(
        "Receive customer request via email\n"
        "Manually log request in tracking spreadsheet :: Ops Analyst :: Excel :: 5\n"
        "Route to approver for sign-off :: Team Lead :: Email :: 45"
    ))
    if st.button("🤖 Extract Steps with AI", type="primary", disabled=not settings.llm_configured, key="extract_manual"):
        with st.spinner("Structuring your process steps..."):
            try:
                st.session_state.raw_steps = extract_steps_from_text(manual_text, st.session_state.get("meta_process_name", ""))
                st.success(f"Extracted {len(st.session_state.raw_steps)} steps.")
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                logger.exception("Manual text LLM extraction failed")

with tab_upload:
    st.caption("Supported: PDF, DOCX, PPT/PPTX, PNG, JPG/JPEG, BPMN, VISIO (XML export), CSV, Excel")
    uploaded = st.file_uploader("Upload a process document", type=["pdf", "docx", "pptx", "png", "jpg", "jpeg", "bpmn", "xml", "csv", "xlsx", "xls"], label_visibility="collapsed")
    if uploaded and st.button("🤖 Extract Steps from Upload", type="primary", disabled=not settings.llm_configured):
        with st.spinner(f"Parsing {uploaded.name} (OCR where needed) and extracting steps..."):
            try:
                upload_path = Path(settings.upload_dir_abs) / uploaded.name
                upload_path.write_bytes(uploaded.getvalue())
                extracted = parse_document(upload_path)
                st.session_state.raw_steps = extract_steps_from_text(extracted.combined_text, st.session_state.get("meta_process_name", ""))
                st.success(f"Parsed '{uploaded.name}' and extracted {len(st.session_state.raw_steps)} steps.")
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                logger.exception("Document extraction failed")

raw_steps: list[ProcessStepInput] = st.session_state.get("raw_steps", [])
if raw_steps:
    with st.expander(f"✅ Review & edit {len(raw_steps)} extracted steps", expanded=True):
        df = pd.DataFrame([s.model_dump() for s in raw_steps])
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="steps_editor")

# ---------------------------------------------------------------------------
# Step 3: Run the multi-agent diagnostic
# ---------------------------------------------------------------------------
st.subheader("3. Run Multi-Agent Diagnostic")
metadata = st.session_state.get("process_metadata")
ready = bool(metadata) and bool(raw_steps)

if not ready:
    st.info("Save your process details and add at least one process step above to continue.")
else:
    st.markdown(
        f"**Process:** {metadata.process_name} &nbsp;|&nbsp; **Steps:** {len(raw_steps)} &nbsp;|&nbsp; "
        f"**FTE:** {metadata.current_fte} &nbsp;|&nbsp; **Volume:** {metadata.current_volume} &nbsp;|&nbsp; "
        f"**AHT:** {metadata.aht_minutes} min &nbsp;|&nbsp; **Annual FTE Cost:** ${metadata.annual_fte_cost:,.0f}"
    )
    is_running = st.session_state.get("diagnostic_running", False)
    st.caption(
        "⏱️ Typically takes **3-8 minutes** - six agents run sequentially, and the Reviewer Agent's "
        "RAGAS evaluation (4 real LLM-judged metrics, up to 2 rounds) alone can take 1-3 minutes. "
        "Please don't click again while it's running - a second click starts a duplicate run instead of speeding it up."
    )
    if is_running:
        st.info("⏳ A diagnostic is already running for this session. Please wait for it to finish.")

    if st.button("▶️ Run Multi-Agent Diagnostic", type="primary", disabled=not settings.llm_configured or is_running):
        st.session_state.diagnostic_running = True
        try:
            confirmed_steps = []
            edited = st.session_state.get("steps_editor", {}).get("edited_rows", {}) if "steps_editor" in st.session_state else {}
            base_df = pd.DataFrame([s.model_dump() for s in raw_steps])
            for i, row in base_df.iterrows():
                row_data = {**row.to_dict(), **edited.get(i, {})}
                confirmed_steps.append(
                    ProcessStepInput(
                        step_number=i + 1, step_name=str(row_data.get("step_name", f"Step {i + 1}")),
                        description=str(row_data.get("description", "") or ""), owner=row_data.get("owner") or None,
                        system_used=row_data.get("system_used") or None, is_decision=bool(row_data.get("is_decision", False)),
                        cycle_time_minutes=row_data.get("cycle_time_minutes") or None,
                    )
                )

            with st.status("Running the six-agent Gemba Walk diagnostic (this can take several minutes)...", expanded=True) as status:
                st.write("🕵️ **PE Agent** conducting Gemba-walk diagnostic (VA/NVA, Lean waste, root cause)...")
                st.write("⚙️ **Automation Agent** evaluating RPA / Power Automate / API opportunities...")
                st.write("🤖 **AI Agentic Agent** evaluating GenAI / Agentic AI opportunities...")
                st.write("📈 **Kaizen Agent** synthesizing Lean, standardization & roadmap horizons...")
                st.write("🔀 **Process Flow Agent** generating current & future-state flow...")
                st.write("🧐 **Reviewer Agent** critically reviewing output, gated by **RAGAS** evaluation (slowest step)...")
                try:
                    process_id, final_state = run_and_persist_pipeline(metadata, confirmed_steps, project_id=None)
                    st.session_state.current_process_id = process_id
                    st.session_state.final_state = final_state
                    status.update(label="Diagnostic complete.", state="complete")
                except Exception as exc:
                    status.update(label="Diagnostic failed.", state="error")
                    st.error(f"Pipeline error: {exc}")
                    logger.exception("Pipeline run failed")
                    st.stop()
        finally:
            st.session_state.diagnostic_running = False

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
final_state = st.session_state.get("final_state")
if final_state:
    st.divider()
    st.subheader("Results")

    diagnostics = final_state.get("diagnostics", [])
    review_notes = final_state.get("review_notes", [])
    ragas_scores = final_state.get("ragas_scores", [])

    with st.expander("Quality Gate: Reviewer Agent + RAGAS Evaluation", expanded=False):
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

    st.markdown("#### Current-State Process Diagnostics")
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

    with st.expander("Root-cause analysis per step"):
        for d in diagnostics:
            if d.root_cause:
                st.markdown(f"**Step {d.step_number} - {d.step_name}:** {d.root_cause}")

    viz1, viz2 = st.columns(2)
    viz1.plotly_chart(va_nva_pie(diagnostics), use_container_width=True)
    viz2.plotly_chart(lean_waste_heatmap(diagnostics), use_container_width=True)
    st.plotly_chart(cycle_time_bar(diagnostics), use_container_width=True)

    if st.button("➡️ View AI Recommendations", type="primary"):
        st.switch_page("pages/2_🤖_AI_Recommendations.py")
