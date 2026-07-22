"""Agent 3: Kaizen Agent.

Synthesizes Lean, standardization, governance, and change-management
recommendations, and organizes ALL recommendations (its own plus the
Automation and AI agents' output already gathered) into a roadmap: Quick
Wins, 30/60/90-Day, Strategic, and a Digital Transformation Roadmap.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.schemas.enums import RoadmapHorizon
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Kaizen Agent - a Continuous Improvement Lead steeped in Toyota
Production System practice: 5S, Kanban, Poka-Yoke, SMED, Value Stream
Mapping, A3 problem solving, RACI, Standard Work, and SOP design.

Your job has two parts:

1. PROPOSE new recommendations in the Lean / Process Simplification / Process
   Standardization / SOP Improvement / Business Rules / Decision
   Simplification / Governance & Control / Dashboard & Visualization /
   Training / Change Management / Knowledge Management categories for
   process steps that need them - especially steps with hand-offs,
   approvals, rework, waiting, or missing standard work. Apply specific
   named techniques (5S, Kanban, Poka-Yoke, SMED, VSM, A3, RACI) where they
   concretely fit the waste identified, not generically.

2. ASSIGN a roadmap_horizon to every recommendation you produce, using this
   ladder: Quick Win (< 30 Days) for no/low-cost changes needing no new
   system; 30-Day for SOP rewrites/small config changes/training; 60-Day for
   RPA bots/dashboards/first AI pilots; 90-Day for broader rollouts/process
   redesign; Strategic (6-12 Months) for system replacement/large AI
   programs; Transformational (12+ Months) for operating-model change.

ALWAYS call search_knowledge_base (e.g. "Kaizen quick wins", "5S visual
management", "digital transformation roadmap horizons") before finalizing,
so your technique choices and horizon assignments are grounded in
established practice. Use get_process_details for the full step diagnostics.

For each recommendation give: category, title, description, rationale,
complexity, risk_level, roadmap_horizon, and a prioritization score
(business_impact, implementation_effort, cost, roi, risk 0-10;
time_to_value_weeks). Estimate savings using the process's actual
FTE/volume/AHT with explicit assumptions.
"""

STRUCTURING_INSTRUCTION = (
    "Produce one Recommendation per distinct Lean/Kaizen/governance opportunity "
    "identified, tagged with the correct step_number (or null for process-level). "
    "proposed_by_agent must be 'Kaizen Agent'."
)


class _RecList(BaseModel):
    recommendations: list[Recommendation] = Field(default_factory=list)


def run_kaizen_agent(metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic]) -> tuple[list[Recommendation], str]:
    tools = default_tools(metadata.model_dump(), [d.model_dump() for d in diagnostics])

    steps_text = "\n".join(
        f"Step {d.step_number}: {d.step_name} | value_class: {d.value_classification.value} | "
        f"wastes: {[w.value for w in d.lean_wastes]} | root_cause: {d.root_cause or 'n/a'} | "
        f"wait_time: {d.wait_time_minutes}min | business_risk: {d.business_risk.value}"
        for d in diagnostics
    )

    user_message = (
        f"Process: {metadata.process_name} | Team: {metadata.team_name} | "
        f"FTE: {metadata.current_fte} | Volume: {metadata.current_volume}/period | "
        f"AHT: {metadata.aht_minutes} min\n"
        f"Pain areas: {metadata.pain_areas or 'not stated'}\n"
        f"Current SLA: {metadata.current_sla or 'not stated'}\n\n"
        f"Diagnosed steps:\n{steps_text}\n\n"
        "Propose Lean/Kaizen/standardization/governance recommendations and roadmap horizons."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _RecList, STRUCTURING_INSTRUCTION, temperature=0.3
    )
    for r in result.recommendations:
        r.proposed_by_agent = "Kaizen Agent"
    logger.info(f"Kaizen Agent produced {len(result.recommendations)} recommendations")
    return result.recommendations, raw_answer


def assign_roadmap_horizons(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Safety net: guarantee every recommendation (including ones from the
    Automation/AI agents) has a sensible horizon even if the source agent
    left the default, using the quadrant computed from its own prioritization score.
    """
    for r in recommendations:
        if r.prioritization.quadrant == "Quick Win" and r.roadmap_horizon not in (
            RoadmapHorizon.QUICK_WIN, RoadmapHorizon.DAYS_30
        ):
            r.roadmap_horizon = RoadmapHorizon.QUICK_WIN
    return recommendations
