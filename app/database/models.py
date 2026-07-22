"""SQLAlchemy ORM models backing the SQLite persistence layer.

Tables: users, projects, processes, process_steps, recommendations,
agent_responses, evaluation_scores, rag_history, uploads, feedback,
audit_logs - as specified in the architecture doc.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.config.settings import get_settings


class Base(DeclarativeBase):
    pass


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(80), default="Consultant")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="In Progress")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    owner: Mapped["User"] = relationship(back_populates="projects")
    processes: Mapped[list["Process"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)

    process_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(150))
    business_function: Mapped[str] = mapped_column(String(150))
    current_fte: Mapped[float] = mapped_column(Float)
    current_volume: Mapped[float] = mapped_column(Float)
    aht_minutes: Mapped[float] = mapped_column(Float)
    country: Mapped[str] = mapped_column(String(100))
    lob: Mapped[str] = mapped_column(String(150))

    pain_areas: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_complaints: Mapped[str | None] = mapped_column(Text, nullable=True)
    dependencies: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_sla: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    applications_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    systems_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_activities: Mapped[str | None] = mapped_column(Text, nullable=True)
    automation_already_implemented: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    savings_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    flow_mermaid_current: Mapped[str | None] = mapped_column(Text, nullable=True)
    flow_mermaid_future: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    project: Mapped["Project"] = relationship(back_populates="processes")
    steps: Mapped[list["ProcessStep"]] = relationship(back_populates="process", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="process", cascade="all, delete-orphan")
    agent_responses: Mapped[list["AgentResponse"]] = relationship(back_populates="process", cascade="all, delete-orphan")
    evaluation_scores: Mapped[list["EvaluationScore"]] = relationship(back_populates="process", cascade="all, delete-orphan")
    uploads: Mapped[list["Upload"]] = relationship(back_populates="process", cascade="all, delete-orphan")


class ProcessStep(Base):
    __tablename__ = "process_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))

    step_number: Mapped[int] = mapped_column(Integer)
    step_name: Mapped[str] = mapped_column(String(300))
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(150), nullable=True)
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_used: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_decision: Mapped[bool] = mapped_column(Boolean, default=False)

    cycle_time_minutes: Mapped[float] = mapped_column(Float, default=0)
    touch_time_minutes: Mapped[float] = mapped_column(Float, default=0)
    wait_time_minutes: Mapped[float] = mapped_column(Float, default=0)

    value_classification: Mapped[str] = mapped_column(String(40), default="Non-Value Added")
    business_risk: Mapped[str] = mapped_column(String(20), default="Low")
    customer_impact: Mapped[str] = mapped_column(String(20), default="Low")
    compliance_risk: Mapped[str] = mapped_column(String(20), default="Low")

    lean_wastes_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)

    automation_score: Mapped[float] = mapped_column(Float, default=0)
    ai_readiness_score: Mapped[float] = mapped_column(Float, default=0)
    complexity_score: Mapped[float] = mapped_column(Float, default=0)
    implementation_effort_days: Mapped[float] = mapped_column(Float, default=0)
    savings_potential_pct: Mapped[float] = mapped_column(Float, default=0)

    process: Mapped["Process"] = relationship(back_populates="steps")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category: Mapped[str] = mapped_column(String(80))
    sub_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_by_agent: Mapped[str] = mapped_column(String(80))

    roadmap_horizon: Mapped[str] = mapped_column(String(60), default="60-Day")
    complexity: Mapped[str] = mapped_column(String(20), default="Medium")
    risk_level: Mapped[str] = mapped_column(String(20), default="Low")

    business_impact: Mapped[float] = mapped_column(Float, default=5)
    implementation_effort: Mapped[float] = mapped_column(Float, default=5)
    cost: Mapped[float] = mapped_column(Float, default=5)
    roi: Mapped[float] = mapped_column(Float, default=5)
    risk: Mapped[float] = mapped_column(Float, default=3)
    time_to_value_weeks: Mapped[float] = mapped_column(Float, default=4)

    fte_savings: Mapped[float] = mapped_column(Float, default=0)
    annual_cost_savings: Mapped[float] = mapped_column(Float, default=0)
    cycle_time_reduction_pct: Mapped[float] = mapped_column(Float, default=0)
    aht_reduction_pct: Mapped[float] = mapped_column(Float, default=0)
    assumptions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, default=0.75)
    source_type: Mapped[str] = mapped_column(String(60), default="LLM Reasoning")
    retrieved_context_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewer_approved: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    process: Mapped["Process"] = relationship(back_populates="recommendations")


class AgentResponse(Base):
    __tablename__ = "agent_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    agent_name: Mapped[str] = mapped_column(String(80))
    node_name: Mapped[str] = mapped_column(String(80))
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_text: Mapped[str] = mapped_column(Text)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    process: Mapped["Process"] = relationship(back_populates="agent_responses")


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    agent_response_id: Mapped[int | None] = mapped_column(ForeignKey("agent_responses.id"), nullable=True)

    faithfulness: Mapped[float] = mapped_column(Float)
    answer_relevancy: Mapped[float] = mapped_column(Float)
    context_precision: Mapped[float] = mapped_column(Float)
    context_recall: Mapped[float] = mapped_column(Float)
    context_relevancy: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float)
    passed_threshold: Mapped[bool] = mapped_column(Boolean, default=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    process: Mapped["Process"] = relationship(back_populates="evaluation_scores")


class RagHistory(Base):
    __tablename__ = "rag_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"), nullable=True)
    query: Mapped[str] = mapped_column(Text)
    retrieved_doc_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(300))
    file_type: Mapped[str] = mapped_column(String(40))
    storage_path: Mapped[str] = mapped_column(String(500))
    extracted_steps_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    process: Mapped["Process"] = relationship(back_populates="uploads")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"), nullable=True)
    recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("recommendations.id"), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(150), default="system")
    action: Mapped[str] = mapped_column(String(200))
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.sqlite_url, connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def init_db() -> None:
    Base.metadata.create_all(get_engine())
