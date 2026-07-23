"""The shared LangGraph state object threaded through every node in the
Gemba Walk multi-agent workflow.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from app.schemas.evaluation import AgentReviewNote, RagasScore
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic, ProcessStepInput
from app.schemas.recommendation import Recommendation


def _last_write(_left: Any, right: Any) -> Any:
    return right


def _extend_list(left: list, right: list) -> list:
    """Additive reducer for state keys written by multiple nodes in the same
    superstep (e.g. Automation Agent and AI Agentic Agent running in
    parallel). Each node returns only ITS OWN new items; LangGraph calls
    this reducer to concatenate them onto whatever's already in the channel,
    rather than one parallel branch's write clobbering the other's.
    """
    return (left or []) + (right or [])


class GembaWalkState(TypedDict, total=False):
    # Inputs
    metadata: ProcessMetadata
    raw_steps: list[ProcessStepInput]

    # RAG
    retrieved_context: Annotated[list[dict], _last_write]

    # Agent outputs. recommendations/trace use the additive reducer because
    # the Automation Agent and AI Agentic Agent run concurrently (parallel
    # fan-out from PE Agent) and both write to these keys in the same step.
    diagnostics: Annotated[list[ProcessStepDiagnostic], _last_write]
    future_diagnostics: Annotated[list[ProcessStepDiagnostic], _last_write]
    recommendations: Annotated[list[Recommendation], _extend_list]
    flow_mermaid_current: Annotated[str, _last_write]
    flow_mermaid_future: Annotated[str, _last_write]

    # Review / evaluation loop
    review_notes: Annotated[list[AgentReviewNote], _last_write]
    ragas_scores: Annotated[list[RagasScore], _last_write]
    review_round: int
    needs_revision: bool

    # Aggregated results
    executive_summary: Annotated[str, _last_write]
    savings_summary: Annotated[dict, _last_write]
    trace: Annotated[list[str], _extend_list]
