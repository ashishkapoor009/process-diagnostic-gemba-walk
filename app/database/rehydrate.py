"""Reconstructs typed Pydantic schema objects (ProcessMetadata,
ProcessStepDiagnostic, Recommendation) from persisted SQLAlchemy rows, so
any saved process can be reopened on the Reports/Process Flow/AI
Recommendations pages after a browser refresh or in a new session, not just
immediately after a live pipeline run.
"""
from __future__ import annotations

from app.database.crud import get_process_full
from app.schemas.enums import (
    AutomationTool,
    ComplexityLevel,
    ImprovementCategory,
    LeanWaste,
    RiskLevel,
    RoadmapHorizon,
    SourceType,
    ValueClassification,
)
from app.schemas.evaluation import DeepEvalFinding
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import PrioritizationScore, Recommendation, SavingsEstimate
from app.reports.report_data import ReportContext


def _enum_or(enum_cls, value, default):
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        return default


def rehydrate_process_metadata(process) -> ProcessMetadata:
    return ProcessMetadata(
        process_name=process.process_name, team_name=process.team_name,
        current_fte=process.current_fte,
        current_volume=process.current_volume, aht_minutes=process.aht_minutes,
        lob=process.lob, annual_fte_cost=process.annual_fte_cost, pain_areas=process.pain_areas,
        customer_complaints=process.customer_complaints, dependencies=process.dependencies,
        current_sla=process.current_sla, known_risks=process.known_risks,
        applications_used=process.applications_used, systems_used=process.systems_used,
        manual_activities=process.manual_activities,
        automation_already_implemented=process.automation_already_implemented,
        compliance_requirements=process.compliance_requirements,
    )


def rehydrate_diagnostics(steps) -> list[ProcessStepDiagnostic]:
    result = []
    for s in steps:
        result.append(
            ProcessStepDiagnostic(
                step_number=s.step_number, step_name=s.step_name, purpose=s.purpose or "",
                owner=s.owner or "Unassigned", input_data=s.input_data or "", output_data=s.output_data or "",
                cycle_time_minutes=s.cycle_time_minutes, touch_time_minutes=s.touch_time_minutes,
                wait_time_minutes=s.wait_time_minutes,
                value_classification=_enum_or(ValueClassification, s.value_classification, ValueClassification.NVA),
                business_risk=_enum_or(RiskLevel, s.business_risk, RiskLevel.LOW),
                customer_impact=_enum_or(RiskLevel, s.customer_impact, RiskLevel.LOW),
                compliance_risk=_enum_or(RiskLevel, s.compliance_risk, RiskLevel.LOW),
                lean_wastes=[_enum_or(LeanWaste, w, LeanWaste.NONE) for w in (s.lean_wastes_json or [])],
                root_cause=s.root_cause or "", automation_score=s.automation_score,
                ai_readiness_score=s.ai_readiness_score, complexity_score=s.complexity_score,
                implementation_effort_days=s.implementation_effort_days,
                savings_potential_pct=s.savings_potential_pct, system_used=s.system_used, is_decision=s.is_decision,
            )
        )
    return result


def rehydrate_recommendations(recs) -> list[Recommendation]:
    result = []
    for r in recs:
        result.append(
            Recommendation(
                id=r.id, step_number=r.step_number,
                category=_enum_or(ImprovementCategory, r.category, ImprovementCategory.PROCESS_SIMPLIFICATION),
                sub_category=_enum_or(AutomationTool, r.sub_category, None) if r.sub_category else None,
                title=r.title, description=r.description, problem_statement=r.problem_statement or "",
                rationale=r.rationale or "",
                proposed_by_agent=r.proposed_by_agent,
                roadmap_horizon=_enum_or(RoadmapHorizon, r.roadmap_horizon, RoadmapHorizon.DAYS_60),
                complexity=_enum_or(ComplexityLevel, r.complexity, ComplexityLevel.MEDIUM),
                risk_level=_enum_or(RiskLevel, r.risk_level, RiskLevel.LOW),
                prioritization=PrioritizationScore(
                    business_impact=r.business_impact, implementation_effort=r.implementation_effort,
                    cost=r.cost, roi=r.roi, risk=r.risk, time_to_value_weeks=r.time_to_value_weeks,
                ),
                savings=SavingsEstimate(
                    fte_savings=r.fte_savings, annual_cost_savings=r.annual_cost_savings,
                    cycle_time_reduction_pct=r.cycle_time_reduction_pct, aht_reduction_pct=r.aht_reduction_pct,
                    assumptions=r.assumptions_json or [],
                ),
                confidence_score=r.confidence_score,
                source_type=_enum_or(SourceType, r.source_type, SourceType.LLM_REASONING),
                retrieved_context_refs=r.retrieved_context_refs_json or [],
                reviewer_notes=r.reviewer_notes, is_duplicate=r.is_duplicate, reviewer_approved=r.reviewer_approved,
            )
        )
    return result


def rehydrate_evaluation_scores(scores) -> list[dict]:
    return [
        {
            "round_number": s.round_number,
            "faithfulness": s.faithfulness,
            "answer_relevancy": s.answer_relevancy,
            "context_precision": s.context_precision,
            "context_recall": s.context_recall,
            "context_relevancy": s.context_relevancy,
            "overall_score": s.overall_score,
            "passed_threshold": s.passed_threshold,
        }
        for s in scores
    ]


def rehydrate_deep_eval_findings(findings) -> list[DeepEvalFinding]:
    return [
        DeepEvalFinding(
            severity=f.severity, recommendation_title=f.recommendation_title,
            issue=f.issue, round_number=f.round_number,
        )
        for f in findings
    ]


def load_report_context(process_id: int) -> ReportContext | None:
    data = get_process_full(process_id)
    process = data.get("process")
    if not process:
        return None
    return ReportContext(
        metadata=rehydrate_process_metadata(process),
        diagnostics=rehydrate_diagnostics(data["steps"]),
        future_diagnostics=rehydrate_diagnostics(data.get("future_steps", [])),
        recommendations=rehydrate_recommendations(data["recommendations"]),
        savings_summary=process.savings_summary_json or {},
        kpi_summary=process.kpi_summary_json or {},
        executive_summary=process.executive_summary or "",
        flow_mermaid_current=process.flow_mermaid_current or "",
        flow_mermaid_future=process.flow_mermaid_future or "",
        evaluation_scores=rehydrate_evaluation_scores(data.get("evaluation_scores", [])),
        deep_eval_findings=rehydrate_deep_eval_findings(data.get("deep_eval_findings", [])),
        generated_at=process.updated_at,
    )
