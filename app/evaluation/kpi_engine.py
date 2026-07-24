"""KPI engine: compares a diagnosed process against a golden/reference
benchmark dataset of Lean Six Sigma & shared-services "best-in-class"
rules of thumb, and projects where the process should land once its
recommendations are implemented.

The golden dataset (GOLDEN_BENCHMARKS below) is a transparent, editable
reference table - not a claim about any specific real-world organization's
actuals. It exists so every diagnostic has a consistent yardstick to be
measured against, and is downloadable as-is (see app/reports/excel.py /
ppt.py) so a reviewer can see and adjust exactly what was compared to.
"""
from __future__ import annotations

from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation

PRODUCTIVE_MINUTES_PER_FTE_PER_PERIOD = 9_000  # ~150 productive hours/period after shrinkage

# Reference benchmarks: Lean Six Sigma / shared-services industry rules of
# thumb, not a specific real dataset. process_cycle_efficiency_pct >= 25%
# is the classical Lean threshold for a "lean" process; the rest are
# directional targets commonly cited for mature transactional operations.
# Adjust these to your organization's actuals as better data becomes available.
GOLDEN_BENCHMARKS: list[dict] = [
    {
        "category": "Claims / Insurance Operations",
        "keywords": ["claim", "insurance", "underwrit", "policy"],
        "process_cycle_efficiency_pct": 22.0,
        "automation_coverage_pct": 65.0,
        "ai_readiness_pct": 55.0,
        "touch_time_ratio_pct": 70.0,
        "first_pass_yield_pct": 92.0,
        "rework_rate_pct": 8.0,
    },
    {
        "category": "Wealth Management Operations",
        "keywords": ["wealth", "asset", "invest", "custody", "portfolio"],
        "process_cycle_efficiency_pct": 20.0,
        "automation_coverage_pct": 60.0,
        "ai_readiness_pct": 50.0,
        "touch_time_ratio_pct": 68.0,
        "first_pass_yield_pct": 94.0,
        "rework_rate_pct": 6.0,
    },
    {
        "category": "Finance & Accounting",
        "keywords": ["finance", "accounting", "accounts payable", "accounts receivable",
                     "record to report", "gl ", "general ledger", "procure to pay"],
        "process_cycle_efficiency_pct": 25.0,
        "automation_coverage_pct": 75.0,
        "ai_readiness_pct": 55.0,
        "touch_time_ratio_pct": 78.0,
        "first_pass_yield_pct": 96.0,
        "rework_rate_pct": 4.0,
    },
    {
        "category": "Customer Service / Contact Center",
        "keywords": ["customer service", "contact center", "support", "helpdesk", "call center"],
        "process_cycle_efficiency_pct": 18.0,
        "automation_coverage_pct": 55.0,
        "ai_readiness_pct": 60.0,
        "touch_time_ratio_pct": 65.0,
        "first_pass_yield_pct": 90.0,
        "rework_rate_pct": 10.0,
    },
    {
        "category": "HR / People Operations",
        "keywords": ["hr", "human resources", "people ops", "payroll", "recruit", "onboarding"],
        "process_cycle_efficiency_pct": 20.0,
        "automation_coverage_pct": 55.0,
        "ai_readiness_pct": 50.0,
        "touch_time_ratio_pct": 70.0,
        "first_pass_yield_pct": 93.0,
        "rework_rate_pct": 7.0,
    },
    {
        "category": "IT / Technology Operations",
        "keywords": ["it ", "technology", "infrastructure", "devops", "service desk"],
        "process_cycle_efficiency_pct": 30.0,
        "automation_coverage_pct": 80.0,
        "ai_readiness_pct": 60.0,
        "touch_time_ratio_pct": 75.0,
        "first_pass_yield_pct": 95.0,
        "rework_rate_pct": 5.0,
    },
    {
        "category": "Procurement / Supply Chain",
        "keywords": ["procurement", "supply chain", "sourcing", "vendor", "logistics"],
        "process_cycle_efficiency_pct": 22.0,
        "automation_coverage_pct": 65.0,
        "ai_readiness_pct": 50.0,
        "touch_time_ratio_pct": 72.0,
        "first_pass_yield_pct": 94.0,
        "rework_rate_pct": 6.0,
    },
    {
        "category": "Healthcare Operations",
        "keywords": ["healthcare", "clinical", "patient", "medical", "provider"],
        "process_cycle_efficiency_pct": 18.0,
        "automation_coverage_pct": 50.0,
        "ai_readiness_pct": 45.0,
        "touch_time_ratio_pct": 65.0,
        "first_pass_yield_pct": 92.0,
        "rework_rate_pct": 8.0,
    },
    {
        "category": "General Shared Services / BPO",
        "keywords": [],  # fallback - always matches
        "process_cycle_efficiency_pct": 25.0,
        "automation_coverage_pct": 65.0,
        "ai_readiness_pct": 55.0,
        "touch_time_ratio_pct": 70.0,
        "first_pass_yield_pct": 93.0,
        "rework_rate_pct": 7.0,
    },
]


def match_benchmark(lob: str) -> dict:
    lob_lower = (lob or "").lower()
    for row in GOLDEN_BENCHMARKS[:-1]:  # last row is the fallback
        if any(kw in lob_lower for kw in row["keywords"]):
            return row
    return GOLDEN_BENCHMARKS[-1]


def golden_benchmark_rows() -> list[dict]:
    """Flat rows (no internal 'keywords' field) suitable for a downloadable
    dataset - the exact reference table diagnostics are compared against.
    """
    return [{k: v for k, v in row.items() if k != "keywords"} for row in GOLDEN_BENCHMARKS]


def _status(current: float, benchmark: float, higher_is_better: bool = True) -> str:
    if benchmark == 0:
        return "N/A"
    ratio = current / benchmark
    if not higher_is_better:
        ratio = benchmark / current if current else 0
    if ratio >= 1.0:
        return "Above Benchmark"
    if ratio >= 0.85:
        return "Near Benchmark"
    return "Below Benchmark"


def compute_kpis(
    metadata: ProcessMetadata,
    diagnostics: list[ProcessStepDiagnostic],
    recommendations: list[Recommendation],
    savings_summary: dict,
) -> dict:
    benchmark = match_benchmark(metadata.lob)
    total_steps = len(diagnostics) or 1

    total_cycle = sum(d.cycle_time_minutes for d in diagnostics) or metadata.aht_minutes
    total_touch = sum(d.touch_time_minutes for d in diagnostics)
    avg_automation = sum(d.automation_score for d in diagnostics) / total_steps
    avg_ai_readiness = sum(d.ai_readiness_score for d in diagnostics) / total_steps
    touch_time_ratio = round((total_touch / total_cycle) * 100, 1) if total_cycle else 0.0
    pce = savings_summary.get("baseline", {}).get("process_cycle_efficiency_pct", 0.0)

    active_recs = [r for r in recommendations if not r.is_duplicate]
    automation_steps = {r.step_number for r in active_recs if "Automation" in r.category.value or r.category.value == "Workflow Automation" or r.category.value in ("API Integration", "Low Code / No Code")}
    ai_steps = {r.step_number for r in active_recs if r.category.value.startswith("AI -")}
    automation_rec_coverage_pct = len(automation_steps) / total_steps * 100
    ai_rec_coverage_pct = len(ai_steps) / total_steps * 100

    projected_automation = min(avg_automation + automation_rec_coverage_pct * 0.5, 100)
    projected_ai_readiness = min(avg_ai_readiness + ai_rec_coverage_pct * 0.5, 100)
    blended_improvement = savings_summary.get("blended_efficiency_improvement_pct", 0.0)
    projected_pce = min(pce + blended_improvement, 95.0)

    expected_capacity_per_fte = PRODUCTIVE_MINUTES_PER_FTE_PER_PERIOD / metadata.aht_minutes if metadata.aht_minutes else 0
    actual_volume_per_fte = metadata.current_volume / metadata.current_fte if metadata.current_fte else 0
    capacity_utilization_pct = round((actual_volume_per_fte / expected_capacity_per_fte) * 100, 1) if expected_capacity_per_fte else 0.0

    kpis = [
        {
            "kpi": "Process Cycle Efficiency", "unit": "%",
            "current": round(pce, 1), "benchmark": benchmark["process_cycle_efficiency_pct"],
            "projected": round(projected_pce, 1),
            "status": _status(pce, benchmark["process_cycle_efficiency_pct"]),
        },
        {
            "kpi": "Automation Coverage", "unit": "score/100",
            "current": round(avg_automation, 1), "benchmark": benchmark["automation_coverage_pct"],
            "projected": round(projected_automation, 1),
            "status": _status(avg_automation, benchmark["automation_coverage_pct"]),
        },
        {
            "kpi": "AI Readiness", "unit": "score/100",
            "current": round(avg_ai_readiness, 1), "benchmark": benchmark["ai_readiness_pct"],
            "projected": round(projected_ai_readiness, 1),
            "status": _status(avg_ai_readiness, benchmark["ai_readiness_pct"]),
        },
        {
            "kpi": "Touch-Time Ratio", "unit": "%",
            "current": touch_time_ratio, "benchmark": benchmark["touch_time_ratio_pct"],
            "projected": None,
            "status": _status(touch_time_ratio, benchmark["touch_time_ratio_pct"]),
        },
        {
            "kpi": "Capacity Utilization", "unit": "%",
            "current": capacity_utilization_pct, "benchmark": 100.0,
            "projected": None,
            "status": _status(capacity_utilization_pct, 100.0),
            "note": "Assumes current_volume is measured per month; re-check if the process's reporting period differs.",
        },
    ]

    scored = [k for k in kpis if k["benchmark"]]
    maturity_score = round(
        sum(min(k["current"] / k["benchmark"], 1.2) for k in scored) / len(scored) * 100, 1
    ) if scored else 0.0

    return {
        "benchmark_category": benchmark["category"],
        "kpis": kpis,
        "maturity_score": maturity_score,
        "benchmark_source_note": (
            "Reference benchmarks are Lean Six Sigma / shared-services industry rules of "
            "thumb (editable), not a specific real-world dataset - see the downloadable "
            "golden dataset for the exact values used."
        ),
    }
