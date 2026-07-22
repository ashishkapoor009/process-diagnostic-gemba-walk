"""AI Recommendations page: for every process step, show all applicable
improvement opportunities across the five lenses (Lean, Process
Simplification, Process Standardization, Automation/RPA, AI Agentic Solution)
side by side - plus a flat filterable list and the automation/AI heatmap.
"""
from __future__ import annotations

import streamlit as st

from app.graphs.visualizations import (
    automation_ai_heatmap,
    confidence_distribution,
    recommendation_bubble_chart,
)
from app.schemas.enums import IMPROVEMENT_BUCKETS, bucket_for_category
from app.ui.styling import apply_branding, badge, page_header

st.set_page_config(page_title="AI Recommendations", page_icon="🤖", layout="wide")
apply_branding()
page_header(
    "AI Recommendations",
    "For every process step: Lean, Process Simplification, Process Standardization, "
    "Automation/RPA, and AI Agentic opportunities, side by side.",
)

final_state = st.session_state.get("final_state")
diagnostics = final_state.get("diagnostics", []) if final_state else []
recommendations = final_state.get("recommendations", []) if final_state else []

if not recommendations:
    st.warning("No recommendations yet. Run the diagnostic on the Process Analysis page first.")
    if st.button("⬅️ Go to Process Intake & Analysis"):
        st.switch_page("pages/1_📋_Process_Intake_&_Analysis.py")
    st.stop()

CATEGORY_COLOR = {
    "Automation Agent": "blue", "AI Agentic Agent": "purple", "Kaizen Agent": "green",
}
BUCKET_COLOR = {
    "Lean": "green", "Process Simplification": "blue", "Process Standardization": "blue",
    "Automation / RPA": "amber", "AI Agentic Solution": "purple", "Governance & Enablement": "red",
}

recs_by_step: dict[int | None, list] = {}
for r in recommendations:
    recs_by_step.setdefault(r.step_number, []).append(r)


def render_recommendation_card(r) -> None:
    with st.container(border=True):
        header_cols = st.columns([5, 1])
        header_cols[0].markdown(f"**{r.title}**")
        header_cols[1].markdown(
            badge(r.proposed_by_agent, CATEGORY_COLOR.get(r.proposed_by_agent, "blue")), unsafe_allow_html=True
        )
        st.markdown(
            badge(r.category.value, "blue") + badge(r.roadmap_horizon.value, "amber") +
            badge(r.prioritization.quadrant, "green") +
            (badge("⚠ Possible Duplicate", "red") if r.is_duplicate else ""),
            unsafe_allow_html=True,
        )
        st.write(r.description)
        if r.rationale:
            st.caption(f"Rationale: {r.rationale}")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Business Impact", f"{r.prioritization.business_impact}/10")
        m2.metric("Effort", f"{r.prioritization.implementation_effort}/10")
        m3.metric("ROI", f"{r.prioritization.roi}/10")
        m4.metric("Confidence", f"{r.confidence_score:.0%}")
        m5.metric("Annual Savings", f"${r.savings.annual_cost_savings:,.0f}")

        st.caption(f"Complexity: {r.complexity.value} | Risk: {r.risk_level.value} | Source: {r.source_type.value}")
        if r.savings.assumptions:
            with st.expander("Savings assumptions"):
                for a in r.savings.assumptions:
                    st.markdown(f"- {a}")
        if r.reviewer_notes:
            st.info(f"Reviewer note: {r.reviewer_notes}")


tab_by_step, tab_all, tab_visual = st.tabs(["📋 By Process Step", "📃 All Recommendations", "📊 Visual Analysis"])

with tab_by_step:
    st.caption(
        "Every diagnosed step, screened against all five improvement lenses. "
        "A lens with no card means no opportunity was identified there for this step."
    )
    for d in diagnostics:
        step_recs = recs_by_step.get(d.step_number, [])
        bucket_hits = {b: [] for b in IMPROVEMENT_BUCKETS}
        for r in step_recs:
            bucket_hits[bucket_for_category(r.category)].append(r)

        applicable_lenses = [b for b, items in bucket_hits.items() if items and b != "Governance & Enablement"]
        lens_summary = "".join(badge(b, BUCKET_COLOR[b]) for b in applicable_lenses) or badge("No opportunity identified", "green")

        with st.expander(f"Step {d.step_number}: {d.step_name}  —  {len(step_recs)} opportunity(ies)", expanded=False):
            st.markdown(
                badge(d.value_classification.value, "blue" if d.is_value_added else "red") +
                (badge(", ".join(w.value for w in d.lean_wastes), "amber") if d.lean_wastes else "") +
                lens_summary,
                unsafe_allow_html=True,
            )
            st.caption(f"Owner: {d.owner} | System: {d.system_used or 'n/a'} | Cycle time: {d.cycle_time_minutes} min")
            if d.root_cause:
                st.caption(f"Root cause: {d.root_cause}")

            lens_order = ["Lean", "Process Simplification", "Process Standardization", "Automation / RPA", "AI Agentic Solution", "Governance & Enablement"]
            cols = st.columns(len(lens_order))
            for col, lens in zip(cols, lens_order):
                with col:
                    st.markdown(f"**{lens}**")
                    items = bucket_hits[lens]
                    if not items:
                        st.caption("—")
                    for r in items:
                        st.markdown(f"- {r.title}")

            if step_recs:
                st.markdown("---")
                for r in step_recs:
                    render_recommendation_card(r)

    process_level = recs_by_step.get(None, [])
    if process_level:
        st.markdown("### Process-Level Recommendations")
        for r in process_level:
            render_recommendation_card(r)

with tab_all:
    f1, f2, f3 = st.columns(3)
    agents = sorted({r.proposed_by_agent for r in recommendations})
    categories = sorted({r.category.value for r in recommendations})
    horizons = sorted({r.roadmap_horizon.value for r in recommendations})

    sel_agents = f1.multiselect("Filter by Agent", agents, default=agents)
    sel_categories = f2.multiselect("Filter by Category", categories, default=categories)
    sel_horizons = f3.multiselect("Filter by Roadmap Horizon", horizons, default=horizons)

    filtered = [
        r for r in recommendations
        if r.proposed_by_agent in sel_agents and r.category.value in sel_categories and r.roadmap_horizon.value in sel_horizons
    ]
    st.caption(f"Showing {len(filtered)} of {len(recommendations)} recommendations.")
    for r in filtered:
        st.caption(f"Step: {r.step_number or 'Process-level'}")
        render_recommendation_card(r)

with tab_visual:
    v1, v2 = st.columns(2)
    v1.plotly_chart(recommendation_bubble_chart(recommendations), use_container_width=True)
    v2.plotly_chart(confidence_distribution(recommendations), use_container_width=True)
    st.plotly_chart(automation_ai_heatmap(diagnostics), use_container_width=True)

if st.button("➡️ View Process Flow", type="primary"):
    st.switch_page("pages/3_🔀_Process_Flow.py")
