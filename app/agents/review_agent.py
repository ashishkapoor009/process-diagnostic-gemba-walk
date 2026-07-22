"""Agent 6: Reviewer Agent - Senior Director, Process Excellence.

Critically reviews all diagnostics and recommendations for hallucinations,
missing opportunities, weak/duplicate recommendations, prioritization
quality, business value, implementation risk, and expected ROI, producing a
confidence score and verdict. This is also the node that regenerates
recommendations when the RAGAS score falls below threshold.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure_with_context
from app.agents.tools import default_tools
from app.schemas.evaluation import AgentReviewNote
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Reviewer Agent - a Senior Director of Process Excellence with
final sign-off authority over every deliverable this consulting engagement
produces. You are deliberately skeptical: your job is to catch what the
other agents got wrong before it reaches the client.

Review the full set of step diagnostics and recommendations for:
- Hallucinations: any recommendation referencing systems, numbers, or facts
  not supported by the process data provided.
- Missing opportunities: steps with clear waste/automation/AI potential that
  received NO recommendation.
- Weak recommendations: vague, generic, or not actionable ("improve the
  process") rather than specific.
- Duplicate recommendations: near-identical recommendations on the same step
  from different agents - flag by title so they can be merged.
- Prioritization quality: does the business_impact/effort/cost/roi/risk
  scoring look internally consistent and defensible?
- Business value, implementation risk, and expected ROI: sanity-check the
  savings estimates against the stated FTE/volume/AHT - flag anything that
  looks inflated or unsupported.

ALWAYS call search_knowledge_base to validate that recommended methodologies/
tools are being applied correctly per best practice before approving.

Assign an overall confidence_score (0-1) and a verdict: 'approved' if the
package is client-ready, or 'needs_revision' if material issues were found.
"""

STRUCTURING_INSTRUCTION = (
    "Produce a single AgentReviewNote summarizing the review. Set "
    "agent_output_id to 'batch_review' and round_number as instructed."
)


def run_review_agent(metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic],
                       recommendations: list[Recommendation], round_number: int = 1
                       ) -> tuple[AgentReviewNote, str, str, list[str]]:
    tools = default_tools(metadata.model_dump(), [d.model_dump() for d in diagnostics])

    diag_summary = "\n".join(
        f"Step {d.step_number}: {d.step_name} | {d.value_classification.value} | "
        f"wastes: {[w.value for w in d.lean_wastes]} | automation_score: {d.automation_score} | "
        f"ai_readiness: {d.ai_readiness_score}"
        for d in diagnostics
    )
    rec_summary = "\n".join(
        f"[{r.proposed_by_agent}] Step {r.step_number or 'process-level'}: {r.title} "
        f"({r.category.value}) | impact={r.prioritization.business_impact} "
        f"effort={r.prioritization.implementation_effort} roi={r.prioritization.roi} | "
        f"fte_savings={r.savings.fte_savings} confidence={r.confidence_score}"
        for r in recommendations
    )

    user_message = (
        f"Process: {metadata.process_name} | FTE: {metadata.current_fte} | "
        f"Volume: {metadata.current_volume} | AHT: {metadata.aht_minutes} min (review round {round_number})\n\n"
        f"Step diagnostics:\n{diag_summary}\n\n"
        f"Recommendations ({len(recommendations)} total):\n{rec_summary}\n\n"
        "Perform the full critical review described in your instructions."
    )

    result, raw_answer, contexts = react_and_structure_with_context(
        SYSTEM_PROMPT, user_message, tools, AgentReviewNote,
        STRUCTURING_INSTRUCTION + f" round_number={round_number}.", temperature=0.1,
    )
    result.round_number = round_number
    logger.info(f"Reviewer Agent verdict: {result.verdict} (confidence={result.confidence_score})")
    return result, raw_answer, user_message, contexts
