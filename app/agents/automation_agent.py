"""Agent 4: Automation Agent.

Analyzes every process step for simple-automation and RPA opportunities:
Excel macros, Power Query, Power Automate (Cloud/Desktop), UiPath,
Automation Anywhere, Blue Prism, Python scripts, API integration, chatbots,
email automation, workflow automation, OCR/computer vision/document AI.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Automation Agent - a Robotic Process Automation and Intelligent
Automation architect with deep hands-on experience across Excel/VBA, Power
Query, Power Automate (Cloud & Desktop), UiPath, Automation Anywhere, Blue
Prism, Python scripting, API integration, chatbots, email automation,
workflow automation platforms, OCR, computer vision and Document AI.

For EVERY process step provided, evaluate its automation potential and, if
justified, propose ONE OR MORE concrete automation recommendations choosing
the RIGHT TOOL for the job (prefer the lowest-cost/lowest-effort tool that
fully solves the problem; only recommend full RPA/API integration when
Excel/Power Automate/Power Query genuinely can't do it). Skip steps that are
already automated or are pure human judgment calls with no automatable
sub-component.

ALWAYS call search_knowledge_base (e.g. "RPA automation tool selection",
"OCR document extraction") before finalizing your tool choice, so the
recommendation reflects established automation best practice, not guesswork.
Use get_process_details to check current systems/applications used and
whether automation is already implemented before recommending.

For each recommendation give: category (one of the Automation-* / Workflow
Automation / API Integration / Low Code categories), sub_category (the
specific tool), a concrete title and description, rationale referencing the
step's waste/bottleneck, complexity, risk_level, roadmap_horizon, and a
prioritization score (business_impact, implementation_effort, cost, roi,
risk 0-10 scales; time_to_value_weeks). Estimate savings (fte_savings,
annual_cost_savings, cycle_time_reduction_pct, aht_reduction_pct) using the
process's actual FTE/volume/AHT, and STATE YOUR ASSUMPTIONS explicitly in
the savings.assumptions list (e.g. assumed automation rate, assumed cost per FTE).
Set source_type to reflect whether you grounded this in retrieved knowledge,
your own reasoning, or both, and set confidence_score accordingly.
"""

STRUCTURING_INSTRUCTION = (
    "Produce one Recommendation per distinct automation opportunity identified, "
    "each tagged with the correct step_number. proposed_by_agent must be 'Automation Agent'."
)


class _RecList(BaseModel):
    recommendations: list[Recommendation] = Field(default_factory=list)


def run_automation_agent(metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic]) -> tuple[list[Recommendation], str]:
    tools = default_tools(metadata.model_dump(), [d.model_dump() for d in diagnostics])

    steps_text = "\n".join(
        f"Step {d.step_number}: {d.step_name} | system: {d.system_used or 'unknown'} | "
        f"cycle_time: {d.cycle_time_minutes}min | automation_score: {d.automation_score} | "
        f"value_class: {d.value_classification.value} | wastes: {[w.value for w in d.lean_wastes]} | "
        f"root_cause: {d.root_cause or 'n/a'}"
        for d in diagnostics
    )

    user_message = (
        f"Process: {metadata.process_name} | FTE: {metadata.current_fte} | "
        f"Volume: {metadata.current_volume}/period | AHT: {metadata.aht_minutes} min\n"
        f"Systems used: {metadata.systems_used or 'not stated'}\n"
        f"Applications used: {metadata.applications_used or 'not stated'}\n"
        f"Automation already implemented: {metadata.automation_already_implemented or 'none stated'}\n\n"
        f"Diagnosed steps:\n{steps_text}\n\n"
        "Identify automation opportunities for every applicable step."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _RecList, STRUCTURING_INSTRUCTION, temperature=0.3
    )
    for r in result.recommendations:
        r.proposed_by_agent = "Automation Agent"
    logger.info(f"Automation Agent produced {len(result.recommendations)} recommendations")
    return result.recommendations, raw_answer
