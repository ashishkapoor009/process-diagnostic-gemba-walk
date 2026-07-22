"""Reports page: generates and downloads the consulting deliverables -
PDF, Word, Excel, and PowerPoint - for either the just-completed diagnostic
or any previously saved process reopened from the Dashboard.
"""
from __future__ import annotations

import streamlit as st

from app.database.rehydrate import load_report_context
from app.reports.excel import generate_excel_report
from app.reports.pdf import generate_pdf_report
from app.reports.ppt import generate_ppt_report
from app.reports.report_data import ReportContext
from app.reports.word import generate_word_report
from app.ui.styling import apply_branding, page_header

st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")
apply_branding()
page_header("Reports", "Download the client-ready deliverables generated from your diagnostic.")

ctx: ReportContext | None = None
process_id = st.session_state.get("current_process_id")

if process_id:
    try:
        ctx = load_report_context(process_id)
    except Exception as exc:
        st.error(f"Could not load saved process #{process_id}: {exc}")

if ctx is None:
    final_state = st.session_state.get("final_state")
    metadata = st.session_state.get("process_metadata")
    if final_state and metadata:
        ctx = ReportContext(
            metadata=metadata, diagnostics=final_state.get("diagnostics", []),
            recommendations=final_state.get("recommendations", []),
            savings_summary=final_state.get("savings_summary", {}),
            executive_summary=final_state.get("executive_summary", ""),
            flow_mermaid_current=final_state.get("flow_mermaid_current", ""),
            flow_mermaid_future=final_state.get("flow_mermaid_future", ""),
        )

if ctx is None:
    st.warning("No diagnostic available. Run the Process Analysis first, or open a saved process from the Dashboard.")
    if st.button("⬅️ Go to Process Analysis"):
        st.switch_page("pages/2_🔍_Process_Analysis.py")
    st.stop()

st.subheader(f"Report Package: {ctx.metadata.process_name}")
s = ctx.savings_summary
m1, m2, m3, m4 = st.columns(4)
m1.metric("Recommendations", s.get("total_recommendations", len(ctx.recommendations)))
m2.metric("Est. FTE Savings", s.get("total_fte_savings", "-"))
m3.metric("Est. Annual Savings", f"${s.get('total_annual_cost_savings', 0):,.0f}")
m4.metric("Efficiency Improvement", f"{s.get('blended_efficiency_improvement_pct', '-')}%")

with st.expander("Executive Summary", expanded=True):
    st.markdown(ctx.executive_summary or "_Not yet generated._")

st.divider()
st.subheader("Download Deliverables")

d1, d2, d3, d4 = st.columns(4)
with d1:
    if st.button("📄 Generate PDF"):
        st.session_state["_pdf_bytes"] = generate_pdf_report(ctx)
    if st.session_state.get("_pdf_bytes"):
        st.download_button("⬇️ Download PDF", st.session_state["_pdf_bytes"],
                             file_name=f"{ctx.metadata.process_name}_GembaWalk_Report.pdf", mime="application/pdf")

with d2:
    if st.button("📝 Generate Word"):
        st.session_state["_word_bytes"] = generate_word_report(ctx)
    if st.session_state.get("_word_bytes"):
        st.download_button("⬇️ Download Word", st.session_state["_word_bytes"],
                             file_name=f"{ctx.metadata.process_name}_GembaWalk_Report.docx",
                             mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with d3:
    if st.button("📊 Generate Excel"):
        st.session_state["_excel_bytes"] = generate_excel_report(ctx)
    if st.session_state.get("_excel_bytes"):
        st.download_button("⬇️ Download Excel", st.session_state["_excel_bytes"],
                             file_name=f"{ctx.metadata.process_name}_GembaWalk_Data.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with d4:
    if st.button("📽️ Generate PowerPoint"):
        st.session_state["_ppt_bytes"] = generate_ppt_report(ctx)
    if st.session_state.get("_ppt_bytes"):
        st.download_button("⬇️ Download PPTX", st.session_state["_ppt_bytes"],
                             file_name=f"{ctx.metadata.process_name}_GembaWalk_Deck.pptx",
                             mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

st.divider()
st.subheader("Provide Feedback")
with st.form("feedback_form"):
    rating = st.slider("Rate this diagnostic (1-5)", 1, 5, 4)
    comments = st.text_area("Comments")
    if st.form_submit_button("Submit Feedback"):
        from app.database import crud

        crud.save_feedback(process_id, None, "Guest Consultant", rating, comments)
        st.success("Thank you - feedback recorded.")
