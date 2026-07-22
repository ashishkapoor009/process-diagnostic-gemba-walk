"""Renders process step diagnostics as Mermaid diagrams: a flowchart (for
the future-state / simple views) and a swimlane-style flow keyed by owner
(for the current-state BPMN-style view), plus a Value Stream Map lane
showing VA vs NVA/wait time. Mermaid text is rendered natively by
Streamlit (via st.markdown with mermaid support / streamlit-mermaid) and
is portable into Visio/Lucidchart/draw.io.
"""
from __future__ import annotations

import re

from app.schemas.enums import ValueClassification
from app.schemas.process import ProcessStepDiagnostic


def _safe_id(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def _sanitize_label(text: str, max_len: int = 60) -> str:
    text = re.sub(r'[\[\]{}"|]', "", text or "")
    text = text.replace("\n", " ").strip()
    return (text[: max_len - 1] + "…") if len(text) > max_len else text or "Step"


def render_flowchart(steps: list[ProcessStepDiagnostic], title: str = "Process Flow") -> str:
    """Simple top-down flowchart: decision steps render as diamonds, VA
    steps as green, NVA as red, BNVA as amber - giving an instant visual
    read of where waste concentrates.
    """
    if not steps:
        return f"flowchart TD\n    empty[\"No steps to display\"]"

    lines = ["%% " + title, "flowchart TD"]
    for s in steps:
        node = _safe_id("S", s.step_number)
        label = _sanitize_label(f"{s.step_number}. {s.step_name}")
        if s.is_decision:
            lines.append("    " + node + '{"' + label + '"}')
        else:
            lines.append(f'    {node}["{label}"]')

    for i in range(len(steps) - 1):
        lines.append(f"    {_safe_id('S', steps[i].step_number)} --> {_safe_id('S', steps[i + 1].step_number)}")

    style_map = {
        ValueClassification.VA: "fill:#DCFCE7,stroke:#16A34A,color:#14532D",
        ValueClassification.NVA: "fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D",
        ValueClassification.BNVA: "fill:#FEF3C7,stroke:#D97706,color:#78350F",
    }
    for s in steps:
        style = style_map.get(s.value_classification, "fill:#EFF6FF,stroke:#2563EB,color:#1E3A8A")
        lines.append(f"    style {_safe_id('S', s.step_number)} {style}")

    return "\n".join(lines)


def render_swimlane(steps: list[ProcessStepDiagnostic], title: str = "Process Flow") -> str:
    """Swimlane-style Mermaid flowchart using subgraphs per owner, which is
    the closest portable equivalent to a BPMN swimlane diagram Mermaid
    supports natively.
    """
    if not steps:
        return f"flowchart TD\n    empty[\"No steps to display\"]"

    owners: dict[str, list[ProcessStepDiagnostic]] = {}
    for s in steps:
        owners.setdefault(s.owner or "Unassigned", []).append(s)

    lines = ["%% " + title, "flowchart TD"]
    for lane_idx, (owner, lane_steps) in enumerate(owners.items()):
        lane_id = f"lane{lane_idx}"
        safe_owner = _sanitize_label(owner, 40)
        lines.append(f'    subgraph {lane_id} ["{safe_owner}"]')
        for s in lane_steps:
            node = _safe_id("S", s.step_number)
            label = _sanitize_label(f"{s.step_number}. {s.step_name}")
            waste_tag = " ⚠" if s.value_classification == ValueClassification.NVA else ""
            if s.is_decision:
                lines.append("        " + node + '{"' + label + waste_tag + '"}')
            else:
                lines.append(f'        {node}["{label}{waste_tag}"]')
        lines.append("    end")

    for i in range(len(steps) - 1):
        lines.append(f"    {_safe_id('S', steps[i].step_number)} --> {_safe_id('S', steps[i + 1].step_number)}")

    return "\n".join(lines)


def render_vsm(steps: list[ProcessStepDiagnostic], title: str = "Value Stream Map") -> str:
    """Value Stream Map style Mermaid: alternates process boxes with wait-time
    triangles, and a footer computing Process Cycle Efficiency (PCE).
    """
    if not steps:
        return "flowchart LR\n    empty[\"No steps to display\"]"

    lines = ["%% " + title, "flowchart LR"]
    total_va = 0.0
    total_lead = 0.0
    prev_node = None
    for s in steps:
        node = _safe_id("P", s.step_number)
        va = s.touch_time_minutes if s.value_classification == ValueClassification.VA else 0.0
        total_va += va
        total_lead += s.cycle_time_minutes
        label = _sanitize_label(f"{s.step_name}\\nVA:{s.touch_time_minutes}m / Wait:{s.wait_time_minutes}m")
        lines.append(f'    {node}["{label}"]')
        if prev_node:
            lines.append(f"    {prev_node} --> {node}")
        prev_node = node

    pce = round((total_va / total_lead) * 100, 1) if total_lead > 0 else 0.0
    lines.append(f'    PCE["Process Cycle Efficiency: {pce}% (VA time / total lead time)"]')
    lines.append("    style PCE fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A")
    return "\n".join(lines)
