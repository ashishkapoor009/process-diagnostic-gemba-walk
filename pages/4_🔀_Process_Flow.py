"""Process Flow page: current-state (swimlane) and future-state (flowchart)
Mermaid diagrams, Value Stream Map, Process Bottleneck Map, Prioritization
Matrix, and the implementation roadmap timeline.
"""
from __future__ import annotations

import streamlit as st

from app.graphs.mermaid import render_vsm
from app.graphs.networkx_graphs import find_bottlenecks, render_bottleneck_map
from app.graphs.visualizations import priority_matrix, roadmap_timeline, savings_by_category_bar
from app.ui.mermaid_render import render_mermaid
from app.ui.styling import apply_branding, page_header

st.set_page_config(page_title="Process Flow", page_icon="🔀", layout="wide")
apply_branding()
page_header("Process Flow", "Current vs. future-state flow, value stream map, bottleneck map, and roadmap.")

final_state = st.session_state.get("final_state")
if not final_state or not final_state.get("diagnostics"):
    st.warning("No process flow yet. Run the diagnostic on the Process Analysis page first.")
    if st.button("⬅️ Go to Process Analysis"):
        st.switch_page("pages/2_🔍_Process_Analysis.py")
    st.stop()

diagnostics = final_state["diagnostics"]
recommendations = final_state.get("recommendations", [])

tab_current, tab_future, tab_vsm, tab_bottleneck, tab_priority = st.tabs(
    ["📍 Current State", "🚀 Future State", "📊 Value Stream Map", "🧯 Bottleneck Map", "🎯 Priority Matrix & Roadmap"]
)

with tab_current:
    st.caption("Swimlane view grouped by process owner. ⚠ marks Non-Value-Added steps.")
    render_mermaid(final_state.get("flow_mermaid_current", ""), key="current")

with tab_future:
    st.caption("Recommended future-state flow after applying Lean, Automation, and AI improvements.")
    render_mermaid(final_state.get("flow_mermaid_future", ""), key="future")

with tab_vsm:
    st.caption("Value Stream Map: VA touch time vs. wait time per step, with Process Cycle Efficiency (PCE).")
    render_mermaid(render_vsm(diagnostics), height=400, key="vsm")

with tab_bottleneck:
    st.caption("Steps in red are the top time-constrained bottlenecks (Theory of Constraints).")
    st.plotly_chart(render_bottleneck_map(diagnostics), use_container_width=True)
    st.markdown("**Top bottleneck steps:**")
    for b in find_bottlenecks(diagnostics):
        st.markdown(f"- Step {b.step_number} ({b.step_name}): {b.cycle_time_minutes + b.wait_time_minutes:.1f} min total")

with tab_priority:
    st.plotly_chart(priority_matrix(recommendations), use_container_width=True)
    st.plotly_chart(savings_by_category_bar(recommendations), use_container_width=True)
    st.plotly_chart(roadmap_timeline(recommendations), use_container_width=True)

if st.button("➡️ Generate Reports", type="primary"):
    st.switch_page("pages/5_📄_Reports.py")
