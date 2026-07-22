"""PDF report generation via ReportLab: Executive Summary, Process
Overview, Current State, Pain Areas, Root Cause Analysis, Lean/Automation/
AI Findings, Quick Wins, Roadmap, Savings, and Appendix.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reports.report_data import ReportContext

BLUE = colors.HexColor("#1D4ED8")
LIGHT_BLUE = colors.HexColor("#DBEAFE")
DARK = colors.HexColor("#0F172A")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("H1Brand", parent=styles["Heading1"], textColor=BLUE, spaceAfter=12))
    styles.add(ParagraphStyle("H2Brand", parent=styles["Heading2"], textColor=BLUE, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle("BodyBrand", parent=styles["BodyText"], textColor=DARK, leading=14))
    return styles


def _table(data: list[list[str]], col_widths=None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def generate_pdf_report(ctx: ReportContext) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                              leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = _styles()
    story = []

    story.append(Paragraph("Process Diagnostic / Gemba Walk Report", styles["Title"]))
    story.append(Paragraph(ctx.metadata.process_name, styles["H2Brand"]))
    story.append(Paragraph(
        f"{ctx.metadata.department} | {ctx.metadata.business_function} | {ctx.metadata.lob} | "
        f"{ctx.metadata.country} | Generated {ctx.generated_at:%Y-%m-%d %H:%M} UTC", styles["BodyBrand"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Executive Summary", styles["H1Brand"]))
    for para in ctx.executive_summary.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip().replace("\n", "<br/>"), styles["BodyBrand"]))
            story.append(Spacer(1, 6))

    story.append(PageBreak())
    story.append(Paragraph("Process Overview", styles["H1Brand"]))
    overview_data = [
        ["Metric", "Value"],
        ["Current FTE", str(ctx.metadata.current_fte)],
        ["Current Volume / Period", str(ctx.metadata.current_volume)],
        ["Average Handle Time (min)", str(ctx.metadata.aht_minutes)],
        ["Pain Areas", ctx.metadata.pain_areas or "Not stated"],
        ["Current SLA", ctx.metadata.current_sla or "Not stated"],
        ["Compliance Requirements", ctx.metadata.compliance_requirements or "Not stated"],
    ]
    story.append(_table(overview_data, col_widths=[5 * cm, 11 * cm]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Current State - Process Diagnostics", styles["H1Brand"]))
    diag_header = ["#", "Step", "VA/NVA", "Cycle(m)", "Wastes", "Risk", "Automation", "AI Ready"]
    diag_rows = [diag_header]
    for d in ctx.diagnostics:
        diag_rows.append([
            str(d.step_number), d.step_name[:30], d.value_classification.value.split(" ")[0],
            str(d.cycle_time_minutes), ", ".join(w.value for w in d.lean_wastes)[:40] or "None",
            d.business_risk.value, str(d.automation_score), str(d.ai_readiness_score),
        ])
    story.append(_table(diag_rows))

    story.append(PageBreak())
    story.append(Paragraph("Root Cause Analysis", styles["H1Brand"]))
    for d in ctx.diagnostics:
        if d.root_cause:
            story.append(Paragraph(f"<b>Step {d.step_number} - {d.step_name}:</b> {d.root_cause}", styles["BodyBrand"]))
            story.append(Spacer(1, 4))

    for title, recs in [
        ("Lean & Standardization Findings", ctx.lean_recommendations),
        ("Automation Findings", ctx.automation_recommendations),
        ("AI / GenAI Findings", ctx.ai_recommendations),
    ]:
        story.append(PageBreak())
        story.append(Paragraph(title, styles["H1Brand"]))
        if not recs:
            story.append(Paragraph("No recommendations in this category.", styles["BodyBrand"]))
        for r in recs:
            story.append(Paragraph(f"<b>{r.title}</b> ({r.category.value}) - {r.roadmap_horizon.value}", styles["BodyBrand"]))
            story.append(Paragraph(r.description, styles["BodyBrand"]))
            story.append(Paragraph(
                f"<i>Impact: {r.prioritization.business_impact}/10 | Effort: {r.prioritization.implementation_effort}/10 | "
                f"ROI: {r.prioritization.roi}/10 | Confidence: {r.confidence_score:.0%} | "
                f"FTE Savings: {r.savings.fte_savings} | Annual Savings: ${r.savings.annual_cost_savings:,.0f}</i>",
                styles["BodyBrand"],
            ))
            story.append(Spacer(1, 8))

    story.append(PageBreak())
    story.append(Paragraph("Quick Wins (Immediate Action)", styles["H1Brand"]))
    qw_rows = [["Title", "Category", "Impact", "Effort", "Timeline"]]
    for r in ctx.quick_wins:
        qw_rows.append([r.title[:40], r.category.value, str(r.prioritization.business_impact),
                          str(r.prioritization.implementation_effort), r.roadmap_horizon.value])
    story.append(_table(qw_rows) if len(qw_rows) > 1 else Paragraph("No quick wins identified.", styles["BodyBrand"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Implementation Roadmap", styles["H1Brand"]))
    for horizon, recs in ctx.roadmap_grouped().items():
        story.append(Paragraph(f"<b>{horizon}</b>", styles["BodyBrand"]))
        for r in recs:
            story.append(Paragraph(f"&bull; {r.title} ({r.category.value})", styles["BodyBrand"]))
        story.append(Spacer(1, 6))

    story.append(PageBreak())
    story.append(Paragraph("Savings & Efficiency Summary", styles["H1Brand"]))
    s = ctx.savings_summary
    savings_rows = [
        ["Metric", "Value"],
        ["Total Recommendations", str(s.get("total_recommendations", "-"))],
        ["Quick Wins", str(s.get("quick_win_count", "-"))],
        ["Strategic Initiatives", str(s.get("strategic_count", "-"))],
        ["Estimated FTE Savings", str(s.get("total_fte_savings", "-"))],
        ["Estimated Annual Cost Savings", f"${s.get('total_annual_cost_savings', 0):,.0f}"],
        ["Blended Efficiency Improvement", f"{s.get('blended_efficiency_improvement_pct', '-')}%"],
        ["Target Efficiency Range", str(s.get("target_efficiency_range_pct", "25-30%"))],
        ["Assumption: Annual Cost / FTE", f"${s.get('annual_cost_per_fte_assumption', 0):,.0f}"],
    ]
    story.append(_table(savings_rows, col_widths=[8 * cm, 8 * cm]))

    story.append(PageBreak())
    story.append(Paragraph("Appendix: All Recommendations", styles["H1Brand"]))
    appendix_rows = [["Step", "Category", "Agent", "Title", "Confidence"]]
    for r in ctx.recommendations:
        appendix_rows.append([
            str(r.step_number or "Process"), r.category.value, r.proposed_by_agent, r.title[:35], f"{r.confidence_score:.0%}",
        ])
    story.append(_table(appendix_rows))

    doc.build(story)
    return buffer.getvalue()
