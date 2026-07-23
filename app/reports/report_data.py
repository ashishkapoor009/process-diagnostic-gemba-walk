"""Common report data structure consumed by every generator (PDF/Word/
Excel/PPT) so all four output formats stay consistent with one assembly step.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation


@dataclass
class ReportContext:
    metadata: ProcessMetadata
    diagnostics: list[ProcessStepDiagnostic]
    recommendations: list[Recommendation]
    savings_summary: dict
    executive_summary: str
    flow_mermaid_current: str = ""
    flow_mermaid_future: str = ""
    future_diagnostics: list[ProcessStepDiagnostic] = field(default_factory=list)
    generated_at: dt.datetime = field(default_factory=dt.datetime.utcnow)

    @property
    def quick_wins(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.prioritization.quadrant == "Quick Win"]

    @property
    def strategic(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.prioritization.quadrant in ("Strategic Project", "Transformation Initiative")]

    @property
    def lean_recommendations(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.proposed_by_agent == "Kaizen Agent"]

    @property
    def automation_recommendations(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.proposed_by_agent == "Automation Agent"]

    @property
    def ai_recommendations(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.proposed_by_agent == "AI Agentic Agent"]

    def roadmap_grouped(self) -> dict[str, list[Recommendation]]:
        groups: dict[str, list[Recommendation]] = {}
        for r in self.recommendations:
            groups.setdefault(r.roadmap_horizon.value, []).append(r)
        return groups
