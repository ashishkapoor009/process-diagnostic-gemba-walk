"""Shared pytest fixtures: isolates every test run behind a temporary
SQLite database and ChromaDB directory so tests never touch developer data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    from app.config.settings import get_settings
    from app.database import models

    get_settings.cache_clear()
    models._engine = None
    models._SessionLocal = None

    yield

    get_settings.cache_clear()
    models._engine = None
    models._SessionLocal = None


@pytest.fixture
def sample_metadata():
    from app.schemas.process import ProcessMetadata

    return ProcessMetadata(
        process_name="Vendor Invoice Processing", team_name="Finance Operations",
        current_fte=6, current_volume=3200,
        aht_minutes=22, lob="Shared Services Finance", annual_fte_cost=35000,
        pain_areas="High rework, manual 3-way match", compliance_requirements="SOX segregation of duties",
    )


@pytest.fixture
def sample_diagnostics():
    from app.schemas.enums import LeanWaste, RiskLevel, ValueClassification
    from app.schemas.process import ProcessStepDiagnostic

    return [
        ProcessStepDiagnostic(
            step_number=1, step_name="Receive invoice via email", purpose="Intake",
            owner="AP Clerk", cycle_time_minutes=1, touch_time_minutes=1,
            value_classification=ValueClassification.VA, automation_score=80, ai_readiness_score=40,
        ),
        ProcessStepDiagnostic(
            step_number=2, step_name="Manually log invoice in Excel", purpose="Tracking",
            owner="AP Clerk", cycle_time_minutes=8, touch_time_minutes=8,
            value_classification=ValueClassification.NVA, lean_wastes=[LeanWaste.OVERPROCESSING, LeanWaste.DEFECTS],
            business_risk=RiskLevel.MEDIUM, automation_score=90, ai_readiness_score=30,
            root_cause="Duplicate data entry because SAP and Excel are not integrated.",
        ),
        ProcessStepDiagnostic(
            step_number=3, step_name="Resolve PO mismatch with vendor", purpose="Exception handling",
            owner="AP Clerk", cycle_time_minutes=180, wait_time_minutes=170,
            value_classification=ValueClassification.NVA, lean_wastes=[LeanWaste.WAITING, LeanWaste.REWORK],
            business_risk=RiskLevel.HIGH, automation_score=35, ai_readiness_score=70, is_decision=True,
        ),
    ]


@pytest.fixture
def sample_recommendation():
    from app.schemas.enums import ImprovementCategory, RoadmapHorizon, SourceType
    from app.schemas.recommendation import PrioritizationScore, Recommendation, SavingsEstimate

    return Recommendation(
        step_number=2, category=ImprovementCategory.AUTOMATION_RPA, title="Automate invoice data capture with OCR",
        description="Use OCR + API integration to SAP instead of manual re-keying.",
        rationale="Eliminates duplicate data entry waste.", proposed_by_agent="Automation Agent",
        roadmap_horizon=RoadmapHorizon.DAYS_60,
        prioritization=PrioritizationScore(business_impact=8, implementation_effort=4, cost=4, roi=8, risk=2, time_to_value_weeks=6),
        savings=SavingsEstimate(fte_savings=0.8, annual_cost_savings=28000, aht_reduction_pct=30, assumptions=["Assumed 85% automation rate"]),
        confidence_score=0.85, source_type=SourceType.BOTH,
    )
