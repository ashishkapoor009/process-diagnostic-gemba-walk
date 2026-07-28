"""Agent 3: Lean Agent.

Structural/systemic process redesign: process simplification, standardization,
non-value-added step elimination, and load balancing across owners/steps.
Runs concurrently with Kaizen, Automation, AI Agentic and Process Flow (see
app/agents/orchestrator.py) - none of the five reads another's output, so
scope is deliberately kept distinct from Kaizen Agent's tactical, shop-floor
continuous-improvement territory (5S/visual management/Kaizen events) to
avoid both agents proposing near-duplicate recommendations on the same step.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation, RecommendationDraft, promote_draft
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Lean Agent - a Lean Six Sigma Black Belt focused on structural
process redesign, distinct from the Kaizen Agent (which handles tactical,
shop-floor quick wins like 5S/visual management/poka-yoke). Your mandate is
the WHOLE-PROCESS shape, not one step in isolation. Propose recommendations
in exactly these four areas, using ONLY the Lean / Process Simplification /
Process Standardization / SOP Improvement / Business Rules / Decision
Simplification categories:

1. PROCESS SIMPLIFICATION - collapse redundant sub-steps, remove unnecessary
   decision branches/approvals, reorder steps to cut hand-offs and touchpoints.
2. STANDARDIZATION - replace variable, tribal-knowledge execution with one
   documented best way (SOPs, business rules, decision criteria) wherever
   steps show inconsistent execution or no documented standard.
3. PROCESS STEP ELIMINATION - identify steps that are pure waste with no
   remaining business purpose (duplicate checks, obsolete approvals,
   legacy hand-offs) and recommend removing them outright, not automating
   them - only propose elimination where the step's value_classification and
   root_cause genuinely support "this step should not exist," not just
   "this step is slow."
4. LOAD BALANCING - using each step's owner, cycle_time_minutes and
   wait_time_minutes, identify uneven work distribution (one owner
   bottlenecking multiple steps while others are underutilized, or volume
   concentrated at a single step/time causing queueing) and recommend
   concrete rebalancing: redistributing steps across owners, cross-training,
   batching/leveling volume, or splitting a single-owner bottleneck step
   across a pooled team. This is a distinct lens from Automation/AI
   recommendations - it changes WHO does the work and WHEN, not what tool
   performs it.

ALWAYS call search_knowledge_base (e.g. "process simplification techniques",
"workload balancing lean", "SOP design standard work") before finalizing, so
technique choices are grounded in established Lean practice. Use
get_process_details for full step diagnostics including owner assignments.

For each recommendation give: category, title, description, rationale,
complexity, risk_level, roadmap_horizon, and a prioritization score
(business_impact, implementation_effort, cost, roi, risk 0-10;
time_to_value_weeks). Estimate savings using the process's actual
FTE/volume/AHT with explicit assumptions. Load-balancing recommendations
should be process-level (step_number null) unless the fix is scoped to one
specific step.
"""

STRUCTURING_INSTRUCTION = (
    "Produce one Recommendation per distinct simplification/standardization/"
    "elimination/load-balancing opportunity identified, tagged with the "
    "correct step_number (or null for process-level, e.g. most load-balancing "
    "recommendations). problem_statement must state the SPECIFIC problem this "
    "recommendation resolves (e.g. 'Step 4 owner also handles Steps 6 and 7, "
    "creating a single-person bottleneck that stalls 40% of volume'), distinct "
    "from the description of the fix itself."
)


class _RecList(BaseModel):
    recommendations: list[RecommendationDraft] = Field(default_factory=list)


def run_lean_agent(metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic]) -> tuple[list[Recommendation], str]:
    tools = default_tools(metadata.model_dump(), [d.model_dump() for d in diagnostics])

    steps_text = "\n".join(
        f"Step {d.step_number}: {d.step_name} | owner: {d.owner or 'Unknown'} | "
        f"value_class: {d.value_classification.value} | cycle_time: {d.cycle_time_minutes}min | "
        f"wait_time: {d.wait_time_minutes}min | wastes: {[w.value for w in d.lean_wastes]} | "
        f"root_cause: {d.root_cause or 'n/a'}"
        for d in diagnostics
    )

    user_message = (
        f"Process: {metadata.process_name} | Team: {metadata.team_name} | "
        f"FTE: {metadata.current_fte} | Volume: {metadata.current_volume}/period | "
        f"AHT: {metadata.aht_minutes} min\n"
        f"Pain areas: {metadata.pain_areas or 'not stated'}\n"
        f"Known risks: {metadata.known_risks or 'not stated'}\n\n"
        f"Diagnosed steps:\n{steps_text}\n\n"
        "Propose process simplification, standardization, step elimination and "
        "load-balancing recommendations across the WHOLE process, not just individual steps."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _RecList, STRUCTURING_INSTRUCTION, temperature=0.3
    )
    recommendations = [promote_draft(d, "Lean Agent") for d in result.recommendations]
    logger.info(f"Lean Agent produced {len(recommendations)} recommendations")
    return recommendations, raw_answer
