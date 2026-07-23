"""Deterministic savings/efficiency aggregation. LLM agents estimate
per-recommendation savings with stated assumptions; this module performs
the actual arithmetic roll-up so the headline efficiency number is
reproducible and auditable rather than LLM-generated.

Savings are reported two ways, both driven by the user-provided
`annual_fte_cost` (no more hardcoded per-FTE cost assumption):

- In-Year Savings: monthly FTE cost x months remaining in the current
  calendar year x FTEs released. Reflects what actually lands in this
  fiscal year's numbers if implementation starts now.
- 12-Month Savings: annual FTE cost x FTEs released. The full annualized
  run-rate savings once the recommendations are fully implemented.
"""
from __future__ import annotations

import datetime as dt

from app.config.settings import get_settings
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation

PRODUCTIVE_MINUTES_PER_FTE_PER_MONTH = 9_000  # ~150 productive hours/month after shrinkage


def compute_current_state_baseline(metadata: ProcessMetadata, steps: list[ProcessStepDiagnostic]) -> dict:
    total_cycle_time = sum(s.cycle_time_minutes for s in steps) or metadata.aht_minutes
    va_time = sum(s.touch_time_minutes for s in steps if s.is_value_added)
    nva_time = sum(s.non_value_add_minutes for s in steps if not s.is_value_added)
    pce = round((va_time / total_cycle_time) * 100, 1) if total_cycle_time else 0.0
    return {
        "total_cycle_time_minutes": round(total_cycle_time, 1),
        "va_time_minutes": round(va_time, 1),
        "nva_time_minutes": round(nva_time, 1),
        "process_cycle_efficiency_pct": pce,
        "current_fte": metadata.current_fte,
        "current_volume": metadata.current_volume,
        "current_aht_minutes": metadata.aht_minutes,
    }


def months_remaining_in_calendar_year(as_of: dt.date | None = None) -> int:
    """Months remaining in the current calendar year, counting the current
    month as remaining (e.g. in July, that's Jul-Dec = 6 months)."""
    today = as_of or dt.date.today()
    return 13 - today.month


def aggregate_savings(metadata: ProcessMetadata, recommendations: list[Recommendation]) -> dict:
    settings = get_settings()

    approved = [r for r in recommendations if r.reviewer_approved and not r.is_duplicate]

    total_fte_savings = sum(r.savings.fte_savings for r in approved)

    annual_fte_cost = metadata.annual_fte_cost
    monthly_fte_cost = annual_fte_cost / 12
    months_remaining = months_remaining_in_calendar_year()

    in_year_savings = monthly_fte_cost * months_remaining * total_fte_savings
    twelve_month_savings = annual_fte_cost * total_fte_savings

    # Blended % reduction: weight each recommendation's AHT reduction by its
    # own confidence score, then cap the aggregate to stay within a
    # defensible range (avoids naive summation double-counting overlapping steps).
    if approved:
        weighted_aht_reduction = sum(r.savings.aht_reduction_pct * r.confidence_score for r in approved) / max(
            sum(r.confidence_score for r in approved), 1e-6
        )
    else:
        weighted_aht_reduction = 0.0

    capacity_efficiency_pct = min(
        weighted_aht_reduction,
        (total_fte_savings / metadata.current_fte * 100) if metadata.current_fte else 0.0,
    )

    target_low = settings.target_efficiency_low * 100
    target_high = settings.target_efficiency_high * 100
    calibrated_efficiency_pct = max(capacity_efficiency_pct, 0.0)

    quick_wins = [r for r in approved if r.prioritization.quadrant == "Quick Win"]
    strategic = [r for r in approved if r.prioritization.quadrant in ("Strategic Project", "Transformation Initiative")]

    by_category: dict[str, int] = {}
    for r in approved:
        by_category[r.category.value] = by_category.get(r.category.value, 0) + 1

    return {
        "total_recommendations": len(approved),
        "quick_win_count": len(quick_wins),
        "strategic_count": len(strategic),
        "total_fte_savings": round(total_fte_savings, 2),
        "in_year_savings": round(in_year_savings, 2),
        "twelve_month_savings": round(twelve_month_savings, 2),
        "months_remaining_in_year": months_remaining,
        "annual_fte_cost": annual_fte_cost,
        "monthly_fte_cost": round(monthly_fte_cost, 2),
        "blended_efficiency_improvement_pct": round(calibrated_efficiency_pct, 1),
        "target_efficiency_range_pct": f"{target_low:.0f}-{target_high:.0f}%",
        "meets_target": target_low <= calibrated_efficiency_pct <= (target_high + 15),
        "recommendations_by_category": by_category,
        "productive_minutes_per_fte_per_month_assumption": PRODUCTIVE_MINUTES_PER_FTE_PER_MONTH,
    }
