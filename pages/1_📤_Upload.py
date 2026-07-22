"""Upload & Intake page: collects mandatory/optional process metadata and
either manual process-step text or an uploaded document (PDF/DOCX/PPT/
image/BPMN/Visio/CSV/Excel), then runs the OCR + LLM extraction pipeline to
produce an editable list of process steps ready for the multi-agent analysis.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.config.settings import get_settings
from app.extraction.document_parser import parse_document
from app.extraction.step_extractor import extract_steps_from_text, parse_manual_steps
from app.schemas.process import ProcessMetadata, ProcessStepInput
from app.ui.styling import apply_branding, page_header
from app.utils.logging import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Upload & Intake", page_icon="📤", layout="wide")
apply_branding()
page_header("Upload & Intake", "Tell us about the process, then give us the steps - typed or uploaded.")

settings = get_settings()
if not settings.llm_configured:
    st.warning(
        "No LLM credentials configured yet. Set OPENAI_API_KEY (or the AZURE_OPENAI_* "
        "variables) in your .env file before running extraction or the multi-agent analysis. "
        "You can still fill in this form."
    )

st.subheader("1. Process Metadata")
with st.form("process_metadata_form", clear_on_submit=False):
    st.markdown("**Mandatory**")
    c1, c2, c3, c4 = st.columns(4)
    process_name = c1.text_input("Process Name*", value=st.session_state.get("meta_process_name", ""))
    department = c2.text_input("Department*", value=st.session_state.get("meta_department", ""))
    business_function = c3.text_input("Business Function*", value=st.session_state.get("meta_business_function", ""))
    country = c4.text_input("Country*", value=st.session_state.get("meta_country", ""))

    c5, c6, c7, c8 = st.columns(4)
    current_fte = c5.number_input("Current FTE*", min_value=0.1, value=st.session_state.get("meta_fte", 5.0), step=0.5)
    current_volume = c6.number_input("Current Volume (per period)*", min_value=1.0, value=st.session_state.get("meta_volume", 1000.0), step=10.0)
    aht_minutes = c7.number_input("Average Handle Time - AHT (minutes)*", min_value=0.1, value=st.session_state.get("meta_aht", 15.0), step=0.5)
    lob = c8.text_input("LOB (Line of Business)*", value=st.session_state.get("meta_lob", ""))

    st.markdown("**Optional**")
    o1, o2 = st.columns(2)
    pain_areas = o1.text_area("Pain Areas", value=st.session_state.get("meta_pain_areas", ""))
    customer_complaints = o2.text_area("Customer Complaints", value=st.session_state.get("meta_complaints", ""))
    o3, o4 = st.columns(2)
    dependencies = o3.text_area("Dependencies", value=st.session_state.get("meta_dependencies", ""))
    current_sla = o4.text_input("Current SLA", value=st.session_state.get("meta_sla", ""))
    o5, o6 = st.columns(2)
    known_risks = o5.text_area("Known Risks", value=st.session_state.get("meta_risks", ""))
    compliance_requirements = o6.text_area("Compliance Requirements", value=st.session_state.get("meta_compliance", ""))
    o7, o8 = st.columns(2)
    applications_used = o7.text_input("Applications Used", value=st.session_state.get("meta_apps", ""))
    systems_used = o8.text_input("Systems Used", value=st.session_state.get("meta_systems", ""))
    o9, o10 = st.columns(2)
    manual_activities = o9.text_area("Manual Activities", value=st.session_state.get("meta_manual", ""))
    automation_already_implemented = o10.text_area("Automation Already Implemented", value=st.session_state.get("meta_auto_done", ""))

    submitted = st.form_submit_button("💾 Save Process Metadata", type="primary")

    if submitted:
        try:
            metadata = ProcessMetadata(
                process_name=process_name, department=department, business_function=business_function,
                current_fte=current_fte, current_volume=current_volume, aht_minutes=aht_minutes,
                country=country, lob=lob, pain_areas=pain_areas or None, customer_complaints=customer_complaints or None,
                dependencies=dependencies or None, current_sla=current_sla or None, known_risks=known_risks or None,
                applications_used=applications_used or None, systems_used=systems_used or None,
                manual_activities=manual_activities or None,
                automation_already_implemented=automation_already_implemented or None,
                compliance_requirements=compliance_requirements or None,
            )
            st.session_state.process_metadata = metadata
            for k, v in {
                "meta_process_name": process_name, "meta_department": department,
                "meta_business_function": business_function, "meta_country": country, "meta_fte": current_fte,
                "meta_volume": current_volume, "meta_aht": aht_minutes, "meta_lob": lob,
                "meta_pain_areas": pain_areas, "meta_complaints": customer_complaints,
                "meta_dependencies": dependencies, "meta_sla": current_sla, "meta_risks": known_risks,
                "meta_compliance": compliance_requirements, "meta_apps": applications_used,
                "meta_systems": systems_used, "meta_manual": manual_activities, "meta_auto_done": automation_already_implemented,
            }.items():
                st.session_state[k] = v
            st.success("Process metadata saved. Continue to Step 2 below.")
        except Exception as exc:
            st.error(f"Please check the mandatory fields: {exc}")

st.divider()
st.subheader("2. Process Steps - Type or Upload")

tab_manual, tab_upload = st.tabs(["✍️ Type Process Steps", "📎 Upload Process Document"])

with tab_manual:
    st.caption("One step per line. Optional format: `Step name :: Owner :: System :: Cycle time (min)`")
    manual_text = st.text_area("Process steps", height=220, placeholder=(
        "Receive customer request via email\n"
        "Manually log request in tracking spreadsheet :: Ops Analyst :: Excel :: 5\n"
        "Route to approver for sign-off :: Team Lead :: Email :: 45\n"
        "Update case in CRM :: Ops Analyst :: Salesforce :: 4\n"
        "Send confirmation email to customer :: Ops Analyst :: Outlook :: 3"
    ))
    col_a, col_b = st.columns(2)
    if col_a.button("⚡ Quick Preview (no LLM)"):
        st.session_state.raw_steps = parse_manual_steps(manual_text)
    if col_b.button("🤖 Extract & Enrich with AI", type="primary", disabled=not settings.llm_configured):
        with st.spinner("PE Agent's extraction pipeline is structuring your steps..."):
            try:
                st.session_state.raw_steps = extract_steps_from_text(
                    manual_text, st.session_state.get("meta_process_name", "")
                )
                st.success(f"Extracted {len(st.session_state.raw_steps)} steps.")
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                logger.exception("Manual text LLM extraction failed")

with tab_upload:
    st.caption("Supported: PDF, DOCX, PPT/PPTX, PNG, JPG/JPEG, BPMN, VISIO (XML export), CSV, Excel")
    uploaded = st.file_uploader(
        "Upload a process document", type=["pdf", "docx", "pptx", "png", "jpg", "jpeg", "bpmn", "xml", "csv", "xlsx", "xls"]
    )
    if uploaded and st.button("🤖 Extract Steps from Upload", type="primary", disabled=not settings.llm_configured):
        with st.spinner(f"Parsing {uploaded.name} (OCR where needed) and extracting steps with AI..."):
            try:
                upload_path = Path(settings.upload_dir_abs) / uploaded.name
                upload_path.write_bytes(uploaded.getvalue())
                extracted = parse_document(upload_path)
                st.session_state.last_extracted_text = extracted.combined_text
                st.session_state.raw_steps = extract_steps_from_text(
                    extracted.combined_text, st.session_state.get("meta_process_name", "")
                )
                st.success(
                    f"Parsed '{uploaded.name}' ({'OCR used' if extracted.used_ocr else 'native text'}) "
                    f"and extracted {len(st.session_state.raw_steps)} steps."
                )
                with st.expander("View raw extracted text"):
                    st.text(extracted.combined_text[:5000])
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                logger.exception("Document extraction failed")

st.divider()
st.subheader("3. Review & Edit Extracted Steps")

raw_steps: list[ProcessStepInput] = st.session_state.get("raw_steps", [])
if raw_steps:
    df = pd.DataFrame([s.model_dump() for s in raw_steps])
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="steps_editor")
    if st.button("✅ Confirm Steps"):
        confirmed = []
        for i, row in edited_df.iterrows():
            confirmed.append(
                ProcessStepInput(
                    step_number=i + 1, step_name=str(row.get("step_name", f"Step {i + 1}")),
                    description=str(row.get("description", "") or ""), owner=row.get("owner") or None,
                    system_used=row.get("system_used") or None,
                    is_decision=bool(row.get("is_decision", False)),
                    cycle_time_minutes=row.get("cycle_time_minutes") or None,
                )
            )
        st.session_state.raw_steps = confirmed
        st.success(f"{len(confirmed)} steps confirmed and ready for analysis.")

    if st.session_state.get("process_metadata") and st.session_state.get("raw_steps"):
        if st.button("➡️ Proceed to Process Analysis", type="primary"):
            st.switch_page("pages/2_🔍_Process_Analysis.py")
else:
    st.info("No steps yet - type them or upload a document above.")
