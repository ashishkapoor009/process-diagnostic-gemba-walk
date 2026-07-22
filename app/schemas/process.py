"""Schemas describing the process being diagnosed: user-supplied metadata,
raw step input (from text or extracted from an upload), and the fully
enriched per-step diagnostic produced by the PE Agent.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.enums import LeanWaste, RiskLevel, ValueClassification


class ProcessMetadata(BaseModel):
    """Mandatory + optional intake fields collected in the Streamlit form."""

    # Mandatory
    process_name: str = Field(..., min_length=2, max_length=200)
    department: str = Field(..., min_length=2, max_length=120)
    business_function: str = Field(..., min_length=2, max_length=120)
    current_fte: float = Field(..., gt=0)
    current_volume: float = Field(..., gt=0, description="Transactions handled per period (e.g. per month)")
    aht_minutes: float = Field(..., gt=0, description="Average Handle Time in minutes")
    country: str = Field(..., min_length=2, max_length=80)
    lob: str = Field(..., min_length=2, max_length=120, description="Line of Business")

    # Optional
    pain_areas: Optional[str] = None
    customer_complaints: Optional[str] = None
    dependencies: Optional[str] = None
    current_sla: Optional[str] = None
    known_risks: Optional[str] = None
    applications_used: Optional[str] = None
    systems_used: Optional[str] = None
    manual_activities: Optional[str] = None
    automation_already_implemented: Optional[str] = None
    compliance_requirements: Optional[str] = None

    @field_validator("process_name", "department", "business_function", "country", "lob")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ProcessStepInput(BaseModel):
    """A single raw process step, either typed by the user or produced by
    the extraction pipeline (OCR / document parsing) before enrichment."""

    step_number: int = Field(..., ge=1)
    step_name: str
    description: str = ""
    owner: Optional[str] = None
    system_used: Optional[str] = None
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    is_decision: bool = False
    cycle_time_minutes: Optional[float] = Field(default=None, ge=0)


class ProcessStepDiagnostic(BaseModel):
    """Full Gemba-walk diagnostic for one process step, as produced by the
    PE Agent and consumed by every downstream agent, the flow generator,
    and the reports.
    """

    step_number: int
    step_name: str
    purpose: str
    owner: str = "Unassigned"
    input_data: str = ""
    output_data: str = ""

    cycle_time_minutes: float = Field(0, ge=0)
    touch_time_minutes: float = Field(0, ge=0)
    wait_time_minutes: float = Field(0, ge=0)

    value_classification: ValueClassification = ValueClassification.NVA
    business_risk: RiskLevel = RiskLevel.LOW
    customer_impact: RiskLevel = RiskLevel.LOW
    compliance_risk: RiskLevel = RiskLevel.LOW

    lean_wastes: list[LeanWaste] = Field(default_factory=list)
    root_cause: str = ""

    automation_score: float = Field(0, ge=0, le=100, description="0-100 automation potential")
    ai_readiness_score: float = Field(0, ge=0, le=100, description="0-100 AI readiness")
    complexity_score: float = Field(0, ge=0, le=100, description="0-100 implementation complexity")
    implementation_effort_days: float = Field(0, ge=0)
    savings_potential_pct: float = Field(0, ge=0, le=100)

    system_used: Optional[str] = None
    is_decision: bool = False

    @property
    def is_value_added(self) -> bool:
        return self.value_classification == ValueClassification.VA

    @property
    def non_value_add_minutes(self) -> float:
        if self.value_classification == ValueClassification.VA:
            return 0.0
        return self.cycle_time_minutes
