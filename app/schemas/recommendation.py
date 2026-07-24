"""Schemas for improvement recommendations, prioritization scoring and the
estimated savings that back the 25-30% efficiency target.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import (
    AutomationTool,
    ComplexityLevel,
    ImprovementCategory,
    RiskLevel,
    RoadmapHorizon,
    SourceType,
)


class PrioritizationScore(BaseModel):
    business_impact: float = Field(..., ge=0, le=10)
    implementation_effort: float = Field(..., ge=0, le=10, description="Higher = more effort")
    cost: float = Field(..., ge=0, le=10, description="Higher = more costly")
    roi: float = Field(..., ge=0, le=10)
    risk: float = Field(..., ge=0, le=10, description="Higher = riskier")
    time_to_value_weeks: float = Field(..., ge=0)

    @property
    def priority_index(self) -> float:
        """Simple weighted index: reward impact + ROI, penalize effort/cost/risk.
        Scaled 0-10, used to sort the prioritization matrix and quadrant chart.
        """
        score = (
            (self.business_impact * 0.35)
            + (self.roi * 0.30)
            - (self.implementation_effort * 0.15)
            - (self.cost * 0.10)
            - (self.risk * 0.10)
        )
        # Recenter around a 0-10 scale (raw score naturally clusters near 0).
        return round(max(0.0, min(10.0, score + 5.0)), 2)

    @property
    def quadrant(self) -> str:
        high_impact = self.business_impact >= 6
        low_effort = self.implementation_effort <= 5
        if high_impact and low_effort:
            return "Quick Win"
        if high_impact and not low_effort:
            return "Strategic Project"
        if not high_impact and low_effort:
            return "Fill-In"
        return "Transformation Initiative"


class SavingsEstimate(BaseModel):
    time_savings_minutes_per_txn: float = Field(0, ge=0)
    fte_savings: float = Field(0, ge=0)
    annual_cost_savings: float = Field(0, ge=0)
    cycle_time_reduction_pct: float = Field(0, ge=0, le=100)
    aht_reduction_pct: float = Field(0, ge=0, le=100)
    quality_improvement_pct: float = Field(0, ge=0, le=100)
    sla_improvement_pct: float = Field(0, ge=0, le=100)
    productivity_increase_pct: float = Field(0, ge=0, le=100)
    assumptions: list[str] = Field(default_factory=list)


class RecommendationDraft(BaseModel):
    """What a generating agent (Kaizen/Automation/AI) is actually qualified
    to produce. Deliberately excludes fields that belong to LATER pipeline
    stages - `id` (DB-assigned), `proposed_by_agent` (overwritten by the
    calling agent regardless), `retrieved_context_refs` (populated from the
    ReAct loop's tool calls, not authored), `reviewer_notes`/`is_duplicate`/
    `reviewer_approved` (set by the Reviewer Agent / postprocess step, never
    by the agent proposing the recommendation).

    This split matters: under OpenAI's strict JSON-schema structured-output
    mode, every field on a schema becomes mandatory for the model to fill in
    (Pydantic defaults are NOT respected server-side). Asking the model to
    also decide `reviewer_approved` for its own not-yet-reviewed
    recommendation produced near-random True/False answers, silently
    dropping most recommendations from the savings totals. Keeping this
    schema narrow to what the agent can legitimately judge avoids that
    entire class of bug.
    """

    step_number: Optional[int] = Field(None, description="Null = process-level recommendation")
    category: ImprovementCategory
    sub_category: Optional[AutomationTool] = None
    title: str
    description: str
    problem_statement: str = Field(
        "", description="The specific problem/pain point at this process step that this recommendation resolves."
    )
    rationale: str = ""

    roadmap_horizon: RoadmapHorizon = RoadmapHorizon.DAYS_60
    complexity: ComplexityLevel = ComplexityLevel.MEDIUM
    risk_level: RiskLevel = RiskLevel.LOW

    prioritization: PrioritizationScore
    savings: SavingsEstimate = Field(default_factory=SavingsEstimate)

    confidence_score: float = Field(0.75, ge=0, le=1)
    source_type: SourceType = SourceType.LLM_REASONING


class Recommendation(BaseModel):
    id: Optional[int] = None
    step_number: Optional[int] = Field(None, description="Null = process-level recommendation")
    category: ImprovementCategory
    sub_category: Optional[AutomationTool] = None
    title: str
    description: str
    problem_statement: str = Field(
        "", description="The specific problem/pain point at this process step that this recommendation resolves."
    )
    rationale: str = ""

    proposed_by_agent: str = Field(..., description="Which agent authored this: PE / Automation / AI / Kaizen")
    roadmap_horizon: RoadmapHorizon = RoadmapHorizon.DAYS_60
    complexity: ComplexityLevel = ComplexityLevel.MEDIUM
    risk_level: RiskLevel = RiskLevel.LOW

    prioritization: PrioritizationScore
    savings: SavingsEstimate = Field(default_factory=SavingsEstimate)

    confidence_score: float = Field(0.75, ge=0, le=1)
    source_type: SourceType = SourceType.LLM_REASONING
    retrieved_context_refs: list[str] = Field(default_factory=list)

    reviewer_notes: Optional[str] = None
    is_duplicate: bool = False
    reviewer_approved: bool = True


def promote_draft(draft: RecommendationDraft, proposed_by_agent: str) -> Recommendation:
    """Fills in the pipeline-owned fields RecommendationDraft deliberately
    omits, with their correct not-yet-reviewed defaults."""
    return Recommendation(proposed_by_agent=proposed_by_agent, **draft.model_dump())
