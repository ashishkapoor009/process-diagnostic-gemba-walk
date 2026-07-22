"""Plotly visualization library for the dashboard: pie/bar/heatmap/radar/
bubble/priority-matrix/timeline charts consumed by the Streamlit UI and
embedded into PDF/PPT reports (via kaleido static image export).
"""
from __future__ import annotations

import datetime as dt
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.schemas.enums import LeanWaste
from app.schemas.process import ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation

BRAND_BLUE = "#1D4ED8"
BRAND_BLUE_LIGHT = "#93C5FD"
PALETTE = ["#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"]


def va_nva_pie(steps: list[ProcessStepDiagnostic]) -> go.Figure:
    counts = Counter(s.value_classification.value for s in steps)
    fig = px.pie(
        names=list(counts.keys()), values=list(counts.values()), hole=0.45,
        color_discrete_sequence=["#16A34A", "#DC2626", "#D97706"],
        title="Value-Added vs Non-Value-Added Step Distribution",
    )
    fig.update_traces(textinfo="percent+label")
    return fig


def cycle_time_bar(steps: list[ProcessStepDiagnostic]) -> go.Figure:
    df = pd.DataFrame(
        {
            "Step": [f"{s.step_number}. {s.step_name[:28]}" for s in steps],
            "Touch Time": [s.touch_time_minutes for s in steps],
            "Wait Time": [s.wait_time_minutes for s in steps],
        }
    )
    fig = px.bar(
        df, x="Step", y=["Touch Time", "Wait Time"], barmode="stack",
        color_discrete_sequence=[BRAND_BLUE, "#FCA5A5"],
        title="Cycle Time Breakdown by Step (minutes)",
    )
    fig.update_layout(xaxis_tickangle=-35, legend_title_text="")
    return fig


def lean_waste_heatmap(steps: list[ProcessStepDiagnostic]) -> go.Figure:
    wastes = [w for w in LeanWaste if w != LeanWaste.NONE]
    z = [[1 if w in s.lean_wastes else 0 for s in steps] for w in wastes]
    fig = px.imshow(
        z, x=[f"S{s.step_number}" for s in steps], y=[w.value for w in wastes],
        color_continuous_scale=["#F8FAFC", "#DC2626"], aspect="auto",
        title="Lean Waste Heatmap (TIMWOODS + Process Wastes)",
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig


def automation_ai_heatmap(steps: list[ProcessStepDiagnostic]) -> go.Figure:
    df = pd.DataFrame(
        {
            "Step": [f"S{s.step_number}" for s in steps],
            "Automation Score": [s.automation_score for s in steps],
            "AI Readiness": [s.ai_readiness_score for s in steps],
            "Complexity": [s.complexity_score for s in steps],
        }
    ).set_index("Step").T
    fig = px.imshow(
        df, color_continuous_scale="Blues", aspect="auto", text_auto=True,
        title="Automation & AI Opportunity Heatmap (0-100 scale)",
    )
    return fig


def process_maturity_radar(scores: dict[str, float], title: str = "Process Maturity Assessment (1-5)") -> go.Figure:
    """scores keys: Governance, Documentation, Automation, Analytics (each 1-5)."""
    categories = list(scores.keys())
    values = list(scores.values())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values + values[:1], theta=categories + categories[:1], fill="toself",
                                    line_color=BRAND_BLUE, name="Current Maturity"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), title=title, showlegend=False)
    return fig


def ai_readiness_radar(steps: list[ProcessStepDiagnostic]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=[s.ai_readiness_score for s in steps] + [steps[0].ai_readiness_score] if steps else [],
            theta=[f"S{s.step_number}" for s in steps] + ([f"S{steps[0].step_number}"] if steps else []),
            fill="toself", line_color="#7C3AED", name="AI Readiness",
        )
    )
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="AI Readiness by Step")
    return fig


def recommendation_bubble_chart(recommendations: list[Recommendation]) -> go.Figure:
    if not recommendations:
        return go.Figure()
    df = pd.DataFrame(
        [
            {
                "Title": r.title[:40],
                "Business Impact": r.prioritization.business_impact,
                "Implementation Effort": r.prioritization.implementation_effort,
                "ROI": r.prioritization.roi,
                "Annual Savings": max(r.savings.annual_cost_savings, 1000),
                "Category": r.category.value,
                "Agent": r.proposed_by_agent,
            }
            for r in recommendations
        ]
    )
    fig = px.scatter(
        df, x="Implementation Effort", y="Business Impact", size="Annual Savings", color="Agent",
        hover_name="Title", hover_data=["Category", "ROI"], size_max=45,
        color_discrete_sequence=PALETTE, title="Automation Complexity vs. Business Value Matrix",
    )
    fig.update_layout(xaxis=dict(range=[0, 10]), yaxis=dict(range=[0, 10]))
    return fig


def priority_matrix(recommendations: list[Recommendation]) -> go.Figure:
    if not recommendations:
        return go.Figure()
    df = pd.DataFrame(
        [
            {
                "Title": r.title[:40],
                "Business Impact": r.prioritization.business_impact,
                "Implementation Effort": r.prioritization.implementation_effort,
                "Quadrant": r.prioritization.quadrant,
                "Category": r.category.value,
            }
            for r in recommendations
        ]
    )
    color_map = {
        "Quick Win": "#16A34A", "Strategic Project": "#2563EB",
        "Fill-In": "#D97706", "Transformation Initiative": "#7C3AED",
    }
    fig = px.scatter(
        df, x="Implementation Effort", y="Business Impact", color="Quadrant",
        hover_name="Title", hover_data=["Category"], color_discrete_map=color_map,
        title="Prioritization Matrix: Impact vs. Effort",
    )
    fig.add_vline(x=5, line_dash="dash", line_color="gray")
    fig.add_hline(y=6, line_dash="dash", line_color="gray")
    fig.update_layout(xaxis=dict(range=[0, 10]), yaxis=dict(range=[0, 10]))
    return fig


def roadmap_timeline(recommendations: list[Recommendation]) -> go.Figure:
    if not recommendations:
        return go.Figure()
    horizon_days = {
        "Quick Win (< 30 Days)": (0, 30), "30-Day": (0, 30), "60-Day": (30, 60),
        "90-Day": (60, 90), "Strategic (6-12 Months)": (90, 365), "Transformational (12+ Months)": (365, 730),
    }
    today = dt.date.today()
    rows = []
    for r in recommendations:
        start_d, end_d = horizon_days.get(r.roadmap_horizon.value, (0, 90))
        rows.append(
            {
                "Task": r.title[:45],
                "Start": today + dt.timedelta(days=start_d),
                "Finish": today + dt.timedelta(days=max(end_d, start_d + 5)),
                "Horizon": r.roadmap_horizon.value,
                "Category": r.category.value,
            }
        )
    df = pd.DataFrame(rows)
    fig = px.timeline(
        df, x_start="Start", x_end="Finish", y="Task", color="Horizon",
        color_discrete_sequence=PALETTE, title="Implementation Roadmap (30/60/90-Day & Strategic)",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def savings_by_category_bar(recommendations: list[Recommendation]) -> go.Figure:
    if not recommendations:
        return go.Figure()
    df = pd.DataFrame(
        [{"Category": r.category.value, "Annual Savings": r.savings.annual_cost_savings} for r in recommendations]
    )
    grouped = df.groupby("Category", as_index=False)["Annual Savings"].sum().sort_values("Annual Savings", ascending=True)
    fig = px.bar(
        grouped, x="Annual Savings", y="Category", orientation="h",
        color_discrete_sequence=[BRAND_BLUE], title="Estimated Annual Cost Savings by Improvement Category",
    )
    return fig


def confidence_distribution(recommendations: list[Recommendation]) -> go.Figure:
    if not recommendations:
        return go.Figure()
    df = pd.DataFrame([{"Confidence": r.confidence_score, "Source": r.source_type.value} for r in recommendations])
    fig = px.histogram(
        df, x="Confidence", color="Source", nbins=10, color_discrete_sequence=PALETTE,
        title="Recommendation Confidence Score Distribution",
    )
    return fig
