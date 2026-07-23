"""Reports page: generates and downloads the consulting deliverables -
PDF, Word, Excel, and PowerPoint - for either the just-completed diagnostic
or any previously saved process reopened from the Dashboard.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.database.rehydrate import load_report_context
from app.reports.excel import generate_excel_report
from app.reports.pdf import generate_pdf_report
from app.reports.ppt import generate_ppt_report
from app.reports.report_data import ReportContext
from app.reports.word import generate_word_report
from app.schemas.enums import efficiency_plan_for_category, main_category_for_category, sub_category_label
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
            future_diagnostics=final_state.get("future_diagnostics", []),
            recommendations=final_state.get("recommendations", []),
            savings_summary=final_state.get("savings_summary", {}),
            executive_summary=final_state.get("executive_summary", ""),
            flow_mermaid_current=final_state.get("flow_mermaid_current", ""),
            flow_mermaid_future=final_state.get("flow_mermaid_future", ""),
        )

if ctx is None:
    st.warning("No diagnostic available. Run the Process Analysis first, or open a saved process from the Dashboard.")
    if st.button("⬅️ Go to Process Intake & Analysis"):
        st.switch_page("pages/1_📋_Process_Intake_&_Analysis.py")
    st.stop()

st.subheader(f"Report Package: {ctx.metadata.process_name}")
s = ctx.savings_summary
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Recommendations", s.get("total_recommendations", len(ctx.recommendations)))
m2.metric("Est. FTE Savings", s.get("total_fte_savings", "-"))
m3.metric("In-Year Savings", f"${s.get('in_year_savings', 0):,.0f}")
m4.metric("12-Month Savings", f"${s.get('twelve_month_savings', 0):,.0f}")
m5.metric("Efficiency Improvement", f"{s.get('blended_efficiency_improvement_pct', '-')}%")
st.caption(
    f"In-Year Savings = monthly FTE cost (${s.get('annual_fte_cost', 0):,.0f}/yr / 12) x "
    f"{s.get('months_remaining_in_year', '-')} months remaining in {dt.date.today().year} x "
    f"{s.get('total_fte_savings', 0)} FTEs released. 12-Month Savings = annual FTE cost x FTEs released "
    "(full run-rate once fully implemented)."
)

with st.expander("Executive Summary", expanded=True):
    st.markdown(ctx.executive_summary or "_Not yet generated._")

st.divider()
st.subheader("All Recommendations")
st.caption(
    "Every recommendation, categorized People / Process / Technology (main category) with a "
    "specific sub-category, plus how the efficiency gain is actually generated."
)

if not ctx.recommendations:
    st.info("No recommendations to show.")
else:
    rec_rows = []
    for r in ctx.recommendations:
        rec_rows.append(
            {
                "Step": r.step_number if r.step_number else "Process-level",
                "Title": r.title,
                "Main Category": main_category_for_category(r.category),
                "Sub-Category": sub_category_label(r.category),
                "Horizon": r.roadmap_horizon.value,
                "Description": r.description,
                "Efficiency Plan": efficiency_plan_for_category(r.category),
                "Business Impact": r.prioritization.business_impact,
                "Effort": r.prioritization.implementation_effort,
                "FTE Savings": r.savings.fte_savings,
                "Annual Savings ($)": r.savings.annual_cost_savings,
                "Confidence": r.confidence_score,
            }
        )
    rec_df = pd.DataFrame(rec_rows)

    f1, f2 = st.columns(2)
    main_cats = f1.multiselect("Filter by Main Category", ["People", "Process", "Technology"], default=["People", "Process", "Technology"])
    sub_cats = f2.multiselect("Filter by Sub-Category", sorted(rec_df["Sub-Category"].unique()), default=sorted(rec_df["Sub-Category"].unique()))
    filtered_df = rec_df[rec_df["Main Category"].isin(main_cats) & rec_df["Sub-Category"].isin(sub_cats)]

    st.caption(f"Showing {len(filtered_df)} of {len(rec_df)} recommendations.")
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Business Impact": st.column_config.ProgressColumn("Business Impact", min_value=0, max_value=10, format="%.0f"),
            "Effort": st.column_config.ProgressColumn("Effort", min_value=0, max_value=10, format="%.0f"),
            "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.0%%"),
            "Annual Savings ($)": st.column_config.NumberColumn("Annual Savings ($)", format="$%.0f"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Efficiency Plan": st.column_config.TextColumn("Efficiency Plan", width="large"),
        },
    )

    cat_summary = rec_df.groupby("Main Category").agg(
        Count=("Title", "count"), FTE_Savings=("FTE Savings", "sum"), Annual_Savings=("Annual Savings ($)", "sum")
    ).reset_index()
    sc1, sc2, sc3 = st.columns(3)
    for col, main_cat in zip((sc1, sc2, sc3), ["People", "Process", "Technology"]):
        row = cat_summary[cat_summary["Main Category"] == main_cat]
        count = int(row["Count"].iloc[0]) if not row.empty else 0
        annual = float(row["Annual_Savings"].iloc[0]) if not row.empty else 0.0
        col.metric(main_cat, f"{count} recommendation(s)", f"${annual:,.0f}/yr")

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
