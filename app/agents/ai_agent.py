"""Agent 5: AI Agentic Agent.

Identifies opportunities for LLM/GenAI, agentic AI, AI copilots, knowledge
assistants, document extraction, intelligent routing, semantic search,
email classification, recommendation engines, predictive models, planning
agents, decision agents, autonomous AI and multi-agent systems.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.react_utils import react_and_structure
from app.agents.tools import default_tools
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation, RecommendationDraft, promote_draft
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the AI Agentic Agent - an applied AI/GenAI solutions architect who
designs LLM, agentic AI, and predictive AI solutions for enterprise
operations teams.

For EVERY process step provided, evaluate whether the bottleneck is
JUDGMENT ON UNSTRUCTURED INPUT (reading, interpreting, classifying,
summarizing, deciding) rather than purely rule-based data movement (that
belongs to the Automation Agent, not you - do not duplicate simple RPA
recommendations). Where AI readiness is genuine, propose ONE OR MORE
concrete AI recommendations: Document AI/extraction, Knowledge Assistant /
semantic search (RAG), Intelligent routing/classification, Email
classification, Summarization/drafting co-pilot, Predictive model,
Recommendation engine, Planning Agent, Decision Agent, or a
multi-agent/Agentic AI system for complex multi-stage steps. Only propose
Autonomous AI (no human in the loop) for low-risk, high-confidence,
non-compliance-sensitive steps; otherwise require a human-in-the-loop
threshold and say so explicitly in the description.

ALWAYS call search_knowledge_base (e.g. "GenAI use case patterns",
"agentic AI readiness signals") before finalizing, so recommendations are
grounded in the established AI-readiness criteria and governance
requirements (especially for compliance-flagged steps). Use
get_process_details to check compliance_requirements and customer impact
before proposing autonomous/low-oversight AI.

For each recommendation give: category (one of the AI-* categories), a
concrete title and description, rationale, complexity, risk_level,
roadmap_horizon, and a prioritization score (business_impact,
implementation_effort, cost, roi, risk 0-10; time_to_value_weeks). Estimate
savings using the process's actual FTE/volume/AHT and STATE ASSUMPTIONS
explicitly. Set source_type and confidence_score honestly based on how much
of this is retrieved best practice vs. your own reasoning about this
specific process.
"""

STRUCTURING_INSTRUCTION = (
    "Produce one Recommendation per distinct AI/GenAI/Agentic opportunity identified, "
    "each tagged with the correct step_number. "
    "problem_statement must state the SPECIFIC problem/pain point at that step this "
    "recommendation resolves (e.g. 'Reviewer must read unstructured attachments to "
    "judge member eligibility, a 5 min/case judgment bottleneck with no assist'), "
    "distinct from the description of the fix itself."
)


class _RecList(BaseModel):
    recommendations: list[RecommendationDraft] = Field(default_factory=list)


def run_ai_agent(metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic]) -> tuple[list[Recommendation], str]:
    tools = default_tools(metadata.model_dump(), [d.model_dump() for d in diagnostics])

    steps_text = "\n".join(
        f"Step {d.step_number}: {d.step_name} | purpose: {d.purpose} | "
        f"ai_readiness_score: {d.ai_readiness_score} | is_decision: {d.is_decision} | "
        f"customer_impact: {d.customer_impact.value} | compliance_risk: {d.compliance_risk.value}"
        for d in diagnostics
    )

    user_message = (
        f"Process: {metadata.process_name} | FTE: {metadata.current_fte} | "
        f"Volume: {metadata.current_volume}/period | AHT: {metadata.aht_minutes} min\n"
        f"Compliance requirements: {metadata.compliance_requirements or 'not stated'}\n"
        f"Customer complaints: {metadata.customer_complaints or 'not stated'}\n\n"
        f"Diagnosed steps:\n{steps_text}\n\n"
        "Identify AI/GenAI/Agentic AI opportunities for every applicable step."
    )

    result, raw_answer = react_and_structure(
        SYSTEM_PROMPT, user_message, tools, _RecList, STRUCTURING_INSTRUCTION, temperature=0.3
    )
    recommendations = [promote_draft(d, "AI Agentic Agent") for d in result.recommendations]
    logger.info(f"AI Agentic Agent produced {len(recommendations)} recommendations")
    return recommendations, raw_answer
