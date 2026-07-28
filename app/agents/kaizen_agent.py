"""Agent 3: Kaizen Agent.

Tactical, shop-floor continuous improvement (5S, visual management, Kaizen
events, poka-yoke defect-proofing at a single step) plus the governance/
enablement categories that support adoption of every OTHER agent's
recommendations (dashboards, training, change management, knowledge
management). Deliberately does NOT cover whole-process redesign
(simplification, standardization, step elimination, load balancing) -
that's the Lean Agent's territory (see app/agents/lean_agent.py), so the
two agents propose non-overlapping recommendations on the same steps. Also
exports assign_roadmap_horizons(), a postprocessing safety net applied to
every recommendation gathered from all agents, not just this one's own.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.schemas.enums import RoadmapHorizon
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation, RecommendationDraft, promote_draft
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Kaizen Agent - a Continuous Improvement Lead steeped in Toyota
Production System practice: 5S, Kanban, Poka-Yoke, SMED, A3 problem solving,
and RACI. You run alongside a separate Lean Agent that owns whole-process
redesign (simplification, standardization, step elimination, load
balancing) - do NOT propose those; stay in your lane below or you'll
duplicate its work on the same steps.

Your job has two parts:

1. PROPOSE new recommendations in ONLY these categories: Lean (5S, Kanban,
   Poka-Yoke, SMED, A3 - tactical fixes scoped to ONE step, not the whole
   process) / Governance & Control / Dashboard & Visualization / Training /
   Change Management / Knowledge Management. Apply named Lean techniques
   where they concretely fit the waste identified at that specific step
   (e.g. Poka-Yoke for a step with high defect/rework rates, visual
   management for a step with unclear status/handoff) - not generically,
   and not as a substitute for standardizing or redesigning the process
   itself. Governance/enablement recommendations should focus on making the
   OTHER agents' recommendations stick (adoption dashboards, training plans,
   change-management/communication plans, a knowledge base for the new
   process) rather than proposing your own structural changes.

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
    "Produce one Recommendation per distinct Kaizen/governance/enablement opportunity "
    "identified (NOT process simplification/standardization/elimination/load-balancing - "
    "that's the Lean Agent's job), tagged with the correct step_number (or null for "
    "process-level). problem_statement must state the SPECIFIC problem/pain point at "
    "that step this recommendation resolves (e.g. 'Manual hand-off between Step 3 and "
    "Step 4 causes a 2-day queue wait'), distinct from the description of the fix itself."
)


class _RecList(BaseModel):
    recommendations: list[RecommendationDraft] = Field(default_factory=list)


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
        "Propose Kaizen/governance/enablement recommendations (not process redesign - "
        "that's the Lean Agent) and roadmap horizons."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _RecList, STRUCTURING_INSTRUCTION, temperature=0.3
    )
    recommendations = [promote_draft(d, "Kaizen Agent") for d in result.recommendations]
    logger.info(f"Kaizen Agent produced {len(recommendations)} recommendations")
    return recommendations, raw_answer


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
