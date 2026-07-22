def test_compute_current_state_baseline(sample_metadata, sample_diagnostics):
    from app.agents.savings_calculator import compute_current_state_baseline

    baseline = compute_current_state_baseline(sample_metadata, sample_diagnostics)
    assert baseline["total_cycle_time_minutes"] == sum(d.cycle_time_minutes for d in sample_diagnostics)
    assert 0 <= baseline["process_cycle_efficiency_pct"] <= 100


def test_aggregate_savings_with_recommendations(sample_metadata, sample_recommendation):
    from app.agents.savings_calculator import aggregate_savings

    result = aggregate_savings(sample_metadata, [sample_recommendation])
    assert result["total_recommendations"] == 1
    assert result["total_fte_savings"] == 0.8
    assert result["total_annual_cost_savings"] == 28000
    assert "blended_efficiency_improvement_pct" in result


def test_aggregate_savings_excludes_duplicates(sample_metadata, sample_recommendation):
    from app.agents.savings_calculator import aggregate_savings

    dup = sample_recommendation.model_copy(deep=True)
    dup.is_duplicate = True
    result = aggregate_savings(sample_metadata, [sample_recommendation, dup])
    assert result["total_recommendations"] == 1
