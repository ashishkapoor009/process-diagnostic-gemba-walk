"""Excel workbook report via pandas + XlsxWriter: one sheet per major
dataset (Overview, Diagnostics, Recommendations, Roadmap, Savings) with
light conditional formatting for quick scanning.
"""
from __future__ import annotations

import io

import pandas as pd

from app.reports.report_data import ReportContext

HEADER_FMT = {"bold": True, "bg_color": "#1D4ED8", "font_color": "white", "border": 1}


def generate_excel_report(ctx: ReportContext) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_format = workbook.add_format(HEADER_FMT)

        overview_df = pd.DataFrame(
            {
                "Field": [
                    "Process Name", "Team Name", "Current FTE", "Current Volume",
                    "AHT (min)", "LOB", "Pain Areas", "Current SLA", "Compliance Requirements",
                ],
                "Value": [
                    ctx.metadata.process_name, ctx.metadata.team_name,
                    ctx.metadata.current_fte, ctx.metadata.current_volume, ctx.metadata.aht_minutes,
                    ctx.metadata.lob, ctx.metadata.pain_areas or "",
                    ctx.metadata.current_sla or "", ctx.metadata.compliance_requirements or "",
                ],
            }
        )
        _write_sheet(writer, header_format, overview_df, "Overview")

        diag_df = pd.DataFrame(
            [
                {
                    "Step": d.step_number, "Step Name": d.step_name, "Owner": d.owner,
                    "Value Class": d.value_classification.value, "Cycle Time (m)": d.cycle_time_minutes,
                    "Touch Time (m)": d.touch_time_minutes, "Wait Time (m)": d.wait_time_minutes,
                    "Lean Wastes": ", ".join(w.value for w in d.lean_wastes),
                    "Root Cause": d.root_cause, "Business Risk": d.business_risk.value,
                    "Automation Score": d.automation_score, "AI Readiness": d.ai_readiness_score,
                    "Complexity": d.complexity_score, "Savings Potential %": d.savings_potential_pct,
                }
                for d in ctx.diagnostics
            ]
        )
        _write_sheet(writer, header_format, diag_df, "Process Diagnostics")

        rec_df = pd.DataFrame(
            [
                {
                    "Step": r.step_number or "Process-level", "Category": r.category.value,
                    "Sub-Category": r.sub_category.value if r.sub_category else "",
                    "Title": r.title, "Description": r.description, "Proposed By": r.proposed_by_agent,
                    "Horizon": r.roadmap_horizon.value, "Business Impact": r.prioritization.business_impact,
                    "Effort": r.prioritization.implementation_effort, "Cost": r.prioritization.cost,
                    "ROI": r.prioritization.roi, "Risk": r.prioritization.risk,
                    "Quadrant": r.prioritization.quadrant, "FTE Savings": r.savings.fte_savings,
                    "Annual Savings ($)": r.savings.annual_cost_savings,
                    "AHT Reduction %": r.savings.aht_reduction_pct,
                    "Confidence": r.confidence_score, "Source": r.source_type.value,
                }
                for r in ctx.recommendations
            ]
        )
        _write_sheet(writer, header_format, rec_df, "Recommendations")

        roadmap_rows = []
        for horizon, recs in ctx.roadmap_grouped().items():
            for r in recs:
                roadmap_rows.append({"Horizon": horizon, "Title": r.title, "Category": r.category.value})
        _write_sheet(writer, header_format, pd.DataFrame(roadmap_rows), "Roadmap")

        s = ctx.savings_summary
        savings_df = pd.DataFrame(
            {
                "Metric": [
                    "Total Recommendations", "Quick Wins", "Strategic Initiatives", "Estimated FTE Savings",
                    "Estimated Annual Cost Savings ($)", "Blended Efficiency Improvement %",
                    "Target Efficiency Range", "Assumption: Annual Cost / FTE ($)",
                ],
                "Value": [
                    s.get("total_recommendations"), s.get("quick_win_count"), s.get("strategic_count"),
                    s.get("total_fte_savings"), s.get("total_annual_cost_savings"),
                    s.get("blended_efficiency_improvement_pct"), s.get("target_efficiency_range_pct"),
                    s.get("annual_cost_per_fte_assumption"),
                ],
            }
        )
        _write_sheet(writer, header_format, savings_df, "Savings Summary")

    return buffer.getvalue()


def _write_sheet(writer, header_format, df: pd.DataFrame, sheet_name: str):
    df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
    worksheet = writer.sheets[sheet_name]
    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(0, col_idx, col_name, header_format)
        max_len = max([len(str(col_name))] + [len(str(v)) for v in df[col_name].astype(str).tolist()[:200]])
        worksheet.set_column(col_idx, col_idx, min(max_len + 2, 60))
