import pytest
from pydantic import ValidationError


def test_process_metadata_requires_mandatory_fields():
    from app.schemas.process import ProcessMetadata

    with pytest.raises(ValidationError):
        ProcessMetadata(process_name="X")  # missing mandatory fields


def test_process_metadata_valid(sample_metadata):
    assert sample_metadata.process_name == "Vendor Invoice Processing"
    assert sample_metadata.current_fte == 6


def test_prioritization_quadrant_quick_win():
    from app.schemas.recommendation import PrioritizationScore

    score = PrioritizationScore(business_impact=8, implementation_effort=3, cost=2, roi=8, risk=2, time_to_value_weeks=2)
    assert score.quadrant == "Quick Win"


def test_prioritization_quadrant_strategic():
    from app.schemas.recommendation import PrioritizationScore

    score = PrioritizationScore(business_impact=9, implementation_effort=9, cost=8, roi=7, risk=6, time_to_value_weeks=20)
    assert score.quadrant == "Strategic Project"


def test_ragas_score_overall_and_pass():
    from app.schemas.evaluation import RagasScore

    score = RagasScore(faithfulness=0.9, answer_relevancy=0.8, context_precision=0.7, context_recall=0.75, context_relevancy=0.85)
    assert 0 <= score.overall <= 1
    assert score.passes(0.7) is True
    assert score.passes(0.99) is False
