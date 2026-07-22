"""Thin, typed CRUD helpers over the SQLAlchemy models. Every function opens
and closes its own session so callers (Streamlit pages, FastAPI routes,
LangGraph nodes) never have to manage session lifecycle themselves.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from app.database.models import (
    AgentResponse,
    AuditLog,
    EvaluationScore,
    Feedback,
    Process,
    ProcessStep,
    Project,
    RagHistory,
    Recommendation,
    Upload,
    User,
    get_session_factory,
    init_db,
)
from app.schemas.evaluation import RagasScore
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation as RecommendationSchema
from app.utils.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def session_scope() -> Iterator:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_db_ready() -> None:
    init_db()


def get_or_create_user(email: str, name: str = "Guest Consultant", role: str = "Consultant") -> int:
    with session_scope() as db:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user:
            return user.id
        user = User(email=email, name=name, role=role)
        db.add(user)
        db.flush()
        return user.id


def create_project(name: str, owner_id: Optional[int] = None) -> int:
    with session_scope() as db:
        project = Project(name=name, owner_id=owner_id)
        db.add(project)
        db.flush()
        return project.id


def create_process(project_id: Optional[int], metadata: ProcessMetadata) -> int:
    with session_scope() as db:
        process = Process(project_id=project_id, **metadata.model_dump())
        db.add(process)
        db.flush()
        return process.id


def save_diagnostics(process_id: int, diagnostics: list[ProcessStepDiagnostic]) -> None:
    with session_scope() as db:
        db.query(ProcessStep).filter(ProcessStep.process_id == process_id).delete()
        for d in diagnostics:
            db.add(
                ProcessStep(
                    process_id=process_id,
                    step_number=d.step_number,
                    step_name=d.step_name,
                    purpose=d.purpose,
                    owner=d.owner,
                    input_data=d.input_data,
                    output_data=d.output_data,
                    system_used=d.system_used,
                    is_decision=d.is_decision,
                    cycle_time_minutes=d.cycle_time_minutes,
                    touch_time_minutes=d.touch_time_minutes,
                    wait_time_minutes=d.wait_time_minutes,
                    value_classification=d.value_classification.value,
                    business_risk=d.business_risk.value,
                    customer_impact=d.customer_impact.value,
                    compliance_risk=d.compliance_risk.value,
                    lean_wastes_json=[w.value for w in d.lean_wastes],
                    root_cause=d.root_cause,
                    automation_score=d.automation_score,
                    ai_readiness_score=d.ai_readiness_score,
                    complexity_score=d.complexity_score,
                    implementation_effort_days=d.implementation_effort_days,
                    savings_potential_pct=d.savings_potential_pct,
                )
            )


def save_recommendations(process_id: int, recommendations: list[RecommendationSchema]) -> None:
    with session_scope() as db:
        db.query(Recommendation).filter(Recommendation.process_id == process_id).delete()
        for r in recommendations:
            db.add(
                Recommendation(
                    process_id=process_id,
                    step_number=r.step_number,
                    category=r.category.value,
                    sub_category=r.sub_category.value if r.sub_category else None,
                    title=r.title,
                    description=r.description,
                    rationale=r.rationale,
                    proposed_by_agent=r.proposed_by_agent,
                    roadmap_horizon=r.roadmap_horizon.value,
                    complexity=r.complexity.value,
                    risk_level=r.risk_level.value,
                    business_impact=r.prioritization.business_impact,
                    implementation_effort=r.prioritization.implementation_effort,
                    cost=r.prioritization.cost,
                    roi=r.prioritization.roi,
                    risk=r.prioritization.risk,
                    time_to_value_weeks=r.prioritization.time_to_value_weeks,
                    fte_savings=r.savings.fte_savings,
                    annual_cost_savings=r.savings.annual_cost_savings,
                    cycle_time_reduction_pct=r.savings.cycle_time_reduction_pct,
                    aht_reduction_pct=r.savings.aht_reduction_pct,
                    assumptions_json=r.savings.assumptions,
                    confidence_score=r.confidence_score,
                    source_type=r.source_type.value,
                    retrieved_context_refs_json=r.retrieved_context_refs,
                    reviewer_notes=r.reviewer_notes,
                    is_duplicate=r.is_duplicate,
                    reviewer_approved=r.reviewer_approved,
                )
            )


def save_agent_response(process_id: int, agent_name: str, node_name: str, output_text: str,
                         input_summary: str = "", round_number: int = 1) -> int:
    with session_scope() as db:
        resp = AgentResponse(
            process_id=process_id,
            agent_name=agent_name,
            node_name=node_name,
            output_text=output_text,
            input_summary=input_summary,
            round_number=round_number,
        )
        db.add(resp)
        db.flush()
        return resp.id


def save_evaluation_score(process_id: int, ragas: RagasScore, threshold: float,
                           agent_response_id: Optional[int] = None, round_number: int = 1) -> None:
    with session_scope() as db:
        db.add(
            EvaluationScore(
                process_id=process_id,
                agent_response_id=agent_response_id,
                faithfulness=ragas.faithfulness,
                answer_relevancy=ragas.answer_relevancy,
                context_precision=ragas.context_precision,
                context_recall=ragas.context_recall,
                context_relevancy=ragas.context_relevancy,
                overall_score=ragas.overall,
                passed_threshold=ragas.passes(threshold),
                round_number=round_number,
            )
        )


def save_flow_diagrams(process_id: int, current_mermaid: str, future_mermaid: str) -> None:
    with session_scope() as db:
        process = db.get(Process, process_id)
        if process:
            process.flow_mermaid_current = current_mermaid
            process.flow_mermaid_future = future_mermaid


def save_executive_summary(process_id: int, summary: str, savings_summary: dict) -> None:
    with session_scope() as db:
        process = db.get(Process, process_id)
        if process:
            process.executive_summary = summary
            process.savings_summary_json = savings_summary


def log_rag_query(process_id: Optional[int], query: str, doc_ids: list[str], top_k: int) -> None:
    with session_scope() as db:
        db.add(RagHistory(process_id=process_id, query=query, retrieved_doc_ids_json=doc_ids, top_k=top_k))


def log_upload(process_id: Optional[int], filename: str, file_type: str, storage_path: str,
                extracted_steps_count: int) -> int:
    with session_scope() as db:
        upload = Upload(
            process_id=process_id,
            filename=filename,
            file_type=file_type,
            storage_path=storage_path,
            extracted_steps_count=extracted_steps_count,
        )
        db.add(upload)
        db.flush()
        return upload.id


def save_feedback(process_id: Optional[int], recommendation_id: Optional[int], user_name: str,
                   rating: int, comments: str) -> None:
    with session_scope() as db:
        db.add(
            Feedback(
                process_id=process_id,
                recommendation_id=recommendation_id,
                user_name=user_name,
                rating=rating,
                comments=comments,
            )
        )


def log_audit(process_id: Optional[int], actor: str, action: str, details: Optional[dict] = None) -> None:
    with session_scope() as db:
        db.add(AuditLog(process_id=process_id, actor=actor, action=action, details_json=details or {}))


def list_projects() -> list[dict]:
    with session_scope() as db:
        return [
            {"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at}
            for p in db.query(Project).order_by(Project.created_at.desc()).all()
        ]


def list_processes(project_id: Optional[int] = None) -> list[dict]:
    with session_scope() as db:
        q = db.query(Process)
        if project_id:
            q = q.filter(Process.project_id == project_id)
        return [
            {
                "id": p.id,
                "process_name": p.process_name,
                "department": p.department,
                "lob": p.lob,
                "current_fte": p.current_fte,
                "current_volume": p.current_volume,
                "aht_minutes": p.aht_minutes,
                "created_at": p.created_at,
            }
            for p in q.order_by(Process.created_at.desc()).all()
        ]


def get_process_full(process_id: int) -> dict:
    with session_scope() as db:
        process = db.get(Process, process_id)
        if not process:
            return {}
        steps = db.query(ProcessStep).filter(ProcessStep.process_id == process_id).order_by(ProcessStep.step_number).all()
        recs = db.query(Recommendation).filter(Recommendation.process_id == process_id).all()
        scores = db.query(EvaluationScore).filter(EvaluationScore.process_id == process_id).all()
        return {
            "process": process,
            "steps": steps,
            "recommendations": recs,
            "evaluation_scores": scores,
        }
