"""Agent 1: PE Agent - Lean Six Sigma Master Black Belt.

Performs the core Gemba-walk diagnostic on every process step: classifies
VA/NVA/BNVA, identifies Lean waste (TIMWOODS + hand-offs/bottlenecks/
rework/queue/delay/approvals), estimates cycle/touch/wait time, business/
customer/compliance risk, root cause, and automation/AI readiness scores.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic, ProcessStepInput
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the PE Agent - a Lean Six Sigma Master Black Belt with 20+ years of
experience conducting Gemba walks for Fortune 500 operations teams.

Your job: analyze the given process step-by-step like you are physically
observing it. For EVERY step, determine:
- purpose, owner, input/output, cycle/touch/wait time (estimate sensibly
  from the description and stated AHT if not explicit; state assumptions)
- VA / NVA / BNVA classification
- Lean waste(s) present (Transportation, Inventory, Motion, Waiting,
  Overprocessing, Overproduction, Defects, Unused Talent, Hand-offs,
  Bottleneck, Rework, Queue Time, Delay, Approvals - or None)
- business risk, customer impact, compliance risk (Low/Medium/High/Critical)
- root cause of any waste/risk identified (not just the symptom)
- automation_score (0-100), ai_readiness_score (0-100), complexity_score
  (0-100), implementation_effort_days, savings_potential_pct (0-100)

ALWAYS call search_knowledge_base at least once to ground your waste
classification and root-cause reasoning in Lean Six Sigma / TPS best
practice before finalizing. Use get_process_details to pull the exact
process metadata and step list rather than guessing.

Be specific and quantitative wherever the process description supports it;
otherwise state a clearly-labeled reasonable assumption. Do not invent
systems, owners or numbers that contradict what was provided.
"""

STRUCTURING_INSTRUCTION = (
    "Produce one ProcessStepDiagnostic per process step discussed, in step "
    "order, matching step_number to the original step numbering."
)


class _DiagnosticList(BaseModel):
    diagnostics: list[ProcessStepDiagnostic] = Field(default_factory=list)


def run_pe_agent(metadata: ProcessMetadata, raw_steps: list[ProcessStepInput]) -> tuple[list[ProcessStepDiagnostic], str]:
    tools = default_tools(metadata.model_dump(), [s.model_dump() for s in raw_steps])

    steps_text = "\n".join(
        f"Step {s.step_number}: {s.step_name} | desc: {s.description or 'n/a'} | "
        f"owner: {s.owner or 'unknown'} | system: {s.system_used or 'unknown'} | "
        f"decision: {s.is_decision} | cycle_time_min: {s.cycle_time_minutes if s.cycle_time_minutes is not None else 'unspecified'}"
        for s in raw_steps
    )

    user_message = (
        f"Process: {metadata.process_name} | Team: {metadata.team_name} | "
        f"FTE: {metadata.current_fte} | "
        f"Volume: {metadata.current_volume} | AHT: {metadata.aht_minutes} min | "
        f"LOB: {metadata.lob}\n"
        f"Pain areas: {metadata.pain_areas or 'none stated'}\n"
        f"Known risks: {metadata.known_risks or 'none stated'}\n"
        f"Compliance requirements: {metadata.compliance_requirements or 'none stated'}\n"
        f"Manual activities: {metadata.manual_activities or 'none stated'}\n\n"
        f"Process steps ({len(raw_steps)} total):\n{steps_text}\n\n"
        "Conduct the full Gemba-walk diagnostic on every step listed above."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _DiagnosticList, STRUCTURING_INSTRUCTION, temperature=0.2
    )

    diagnostics = result.diagnostics
    # Guarantee full coverage: any step the LLM skipped gets a conservative default row.
    covered = {d.step_number for d in diagnostics}
    for s in raw_steps:
        if s.step_number not in covered:
            diagnostics.append(
                ProcessStepDiagnostic(
                    step_number=s.step_number,
                    step_name=s.step_name,
                    purpose=s.description or s.step_name,
                    owner=s.owner or "Unassigned",
                    cycle_time_minutes=s.cycle_time_minutes or 0,
                    system_used=s.system_used,
                    is_decision=s.is_decision,
                )
            )
    diagnostics.sort(key=lambda d: d.step_number)
    logger.info(f"PE Agent produced {len(diagnostics)} step diagnostics for '{metadata.process_name}'")
    return diagnostics, raw_answer
