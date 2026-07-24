"""Schemas for the Reviewer Agent and RAGAS evaluation results."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RagasScore(BaseModel):
    faithfulness: float = Field(..., ge=0, le=1)
    answer_relevancy: float = Field(..., ge=0, le=1)
    context_precision: float = Field(..., ge=0, le=1)
    context_recall: float = Field(..., ge=0, le=1)
    context_relevancy: float = Field(..., ge=0, le=1)

    @property
    def overall(self) -> float:
        return round(
            (
                self.faithfulness
                + self.answer_relevancy
                + self.context_precision
                + self.context_recall
                + self.context_relevancy
            )
            / 5,
            4,
        )

    def passes(self, threshold: float) -> bool:
        return self.overall >= threshold


class DeepEvalFinding(BaseModel):
    """One deterministic grounding/numeric-sanity finding from the deep
    evaluation layer (app/evaluation/deep_eval.py) - RAGAS's complement,
    catching errors a narrative-answer judge can't (e.g. FTE savings that
    exceed the process's total headcount).
    """

    severity: str = "warning"  # "error" (auto-corrected) | "warning" (flagged only)
    recommendation_title: str
    issue: str
    round_number: int = 1


class AgentReviewNote(BaseModel):
    agent_output_id: str
    reviewer_agent: str = "Reviewer Agent"
    hallucination_flag: bool = False
    missing_opportunities: list[str] = Field(default_factory=list)
    weak_recommendations: list[str] = Field(default_factory=list)
    duplicate_recommendations: list[str] = Field(default_factory=list)
    prioritization_feedback: Optional[str] = None
    business_value_feedback: Optional[str] = None
    implementation_risk_feedback: Optional[str] = None
    expected_roi_feedback: Optional[str] = None
    confidence_score: float = Field(0.75, ge=0, le=1)
    ragas: Optional[RagasScore] = None
    verdict: str = "approved"  # approved | needs_revision
    round_number: int = 1
