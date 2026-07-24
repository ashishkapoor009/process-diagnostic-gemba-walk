"""Agent 2: Process Flow Agent.

Generates the Current State flow (directly from the PE Agent's
diagnostics) and reasons about a Future State flow (which steps merge,
eliminate, or get automated away), then renders both as Mermaid
flowcharts/swimlanes via app.graphs.mermaid.

Runs in parallel with the Automation/AI/Kaizen agents (all four only depend
on PE Agent's diagnostics), so it reasons directly from each step's
automation_score/ai_readiness_score/lean_wastes rather than waiting on the
other agents' specific recommendation titles - a deliberate precision/speed
trade-off. When recommendation summaries ARE available (e.g. a future caller
passes them), they're used as additional grounding.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.graphs.mermaid import render_flowchart, render_swimlane
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Process Flow Agent - a business process architect who designs
BPMN-style future-state flows.

Given the current-state diagnosed steps (each with a value classification,
Lean wastes, automation_score, and ai_readiness_score), determine the
FUTURE STATE step sequence: which steps are eliminated (pure waste with no
remaining purpose), which are merged (sequential steps a single
automation/AI solution would collapse into one), which are automated (same
purpose, but performed by a bot/AI instead of a human - keep as a step but
note it's automated), and which are unchanged. Use each step's
automation_score/ai_readiness_score as your primary signal for how far to
push automation, and its Lean wastes to decide what's eliminated vs. merged.
If recommendation summaries are provided, use them as additional grounding
for exactly which technique applies where - but reason from the diagnostic
scores even when they are not. Preserve overall process intent and any
required compliance/approval steps (BNVA should be simplified, not silently
deleted).

ALWAYS call search_knowledge_base for BPMN/swimlane design guidance before
finalizing. Use get_process_details for the full current-state step data.

Return the future-state step list in the same ProcessStepDiagnostic shape,
renumbered sequentially, with cycle/touch/wait time reflecting the
post-improvement estimate and value_classification updated where a step's
NVA content was removed.
"""

STRUCTURING_INSTRUCTION = (
    "Produce the future-state step list as future_steps, one ProcessStepDiagnostic "
    "per surviving step, renumbered sequentially starting at 1."
)


class _FutureStateResult(BaseModel):
    future_steps: list[ProcessStepDiagnostic] = Field(default_factory=list)
    transformation_notes: str = ""


def run_flow_agent(metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic],
                     recommendation_summaries: list[str] | None = None) -> tuple[list[ProcessStepDiagnostic], str, str, str]:
    """Returns (future_steps, transformation_notes, current_state_mermaid, future_state_mermaid).

    `recommendation_summaries` is optional: this agent runs in parallel with
    the recommendation-generating agents, so it typically reasons from the
    diagnostic automation/AI-readiness scores alone (see SYSTEM_PROMPT).
    """
    tools = default_tools(metadata.model_dump(), [d.model_dump() for d in diagnostics])

    steps_text = "\n".join(
        f"Step {d.step_number}: {d.step_name} | value_class: {d.value_classification.value} | "
        f"wastes: {[w.value for w in d.lean_wastes]} | automation_score: {d.automation_score} | "
        f"ai_readiness_score: {d.ai_readiness_score} | owner: {d.owner} | system: {d.system_used or 'n/a'}"
        for d in diagnostics
    )
    recs_text = "\n".join(f"- {s}" for s in (recommendation_summaries or [])[:60]) or (
        "Not available yet - infer automation/AI opportunities directly from each "
        "step's automation_score and ai_readiness_score above."
    )

    user_message = (
        f"Process: {metadata.process_name}\n\nCurrent-state steps:\n{steps_text}\n\n"
        f"Recommendations gathered so far:\n{recs_text}\n\n"
        "Design the future-state process flow."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _FutureStateResult, STRUCTURING_INSTRUCTION, temperature=0.3
    )

    current_mermaid = render_swimlane(diagnostics, title=f"{metadata.process_name} - Current State")
    future_mermaid = render_flowchart(result.future_steps, title=f"{metadata.process_name} - Future State")

    logger.info(
        f"Flow Agent: current state {len(diagnostics)} steps -> future state {len(result.future_steps)} steps"
    )
    return result.future_steps, result.transformation_notes, current_mermaid, future_mermaid
