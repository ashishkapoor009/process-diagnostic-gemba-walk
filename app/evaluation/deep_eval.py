"""Deep evaluation: deterministic grounding and numeric sanity checks that
complement RAGAS. RAGAS judges whether the Reviewer Agent's narrative
answer is faithful to retrieved knowledge - it has no way to know that a
recommendation claims more FTE savings than the process actually has, or
references a process step that doesn't exist. This module catches exactly
that class of error and auto-corrects the ones that are safe to auto-correct
(capping implausible numbers), flagging everything else for human review.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeepEvalFinding:
    severity: str  # "error" (auto-corrected) | "warning" (flagged only)
    recommendation_title: str
    issue: str


@dataclass
class DeepEvalResult:
    findings: list[DeepEvalFinding] = field(default_factory=list)
    corrections_applied: int = 0

    @property
    def passed(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


def deep_evaluate_recommendations(
    metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic], recommendations: list[Recommendation]
) -> DeepEvalResult:
    result = DeepEvalResult()
    valid_step_numbers = {d.step_number for d in diagnostics}
    active_recs = [r for r in recommendations if not r.is_duplicate]

    # 1. Per-recommendation FTE savings can never exceed the process's total
    # current FTE - a single recommendation "releasing" more FTEs than the
    # process employs is a clear hallucination/arithmetic error.
    for r in active_recs:
        if r.savings.fte_savings > metadata.current_fte:
            original = r.savings.fte_savings
            r.savings.fte_savings = round(metadata.current_fte * 0.5, 2)
            result.corrections_applied += 1
            result.findings.append(
                DeepEvalFinding(
                    severity="error", recommendation_title=r.title,
                    issue=(
                        f"FTE savings ({original}) exceeded total process FTE ({metadata.current_fte}); "
                        f"capped to {r.savings.fte_savings}."
                    ),
                )
            )

    # 2. Aggregate FTE savings across all recommendations shouldn't exceed
    # current FTE either (a process can't release more capacity than it has,
    # even split across many recommendations touching different steps).
    total_fte_savings = sum(r.savings.fte_savings for r in active_recs)
    if total_fte_savings > metadata.current_fte and total_fte_savings > 0:
        scale = (metadata.current_fte * 0.9) / total_fte_savings  # leave 10% headroom
        for r in active_recs:
            r.savings.fte_savings = round(r.savings.fte_savings * scale, 3)
        result.corrections_applied += 1
        result.findings.append(
            DeepEvalFinding(
                severity="error", recommendation_title="(aggregate)",
                issue=(
                    f"Sum of FTE savings across {len(active_recs)} recommendations ({total_fte_savings:.2f}) "
                    f"exceeded total process FTE ({metadata.current_fte}); scaled down by {scale:.2f}x."
                ),
            )
        )

    # 3. A recommendation referencing a step_number that doesn't exist in
    # this process's diagnosed steps is a grounding failure - flagged, not
    # auto-corrected (safer to surface than to guess which real step it meant).
    for r in active_recs:
        if r.step_number is not None and r.step_number not in valid_step_numbers:
            result.findings.append(
                DeepEvalFinding(
                    severity="warning", recommendation_title=r.title,
                    issue=f"References step {r.step_number}, which doesn't exist in this process's diagnosed steps.",
                )
            )

    # 4. Overconfident with no retrieved grounding: pure LLM reasoning
    # claiming very high confidence is a soft red flag worth a human look.
    for r in active_recs:
        if r.source_type.value == "LLM Reasoning" and r.confidence_score > 0.9:
            result.findings.append(
                DeepEvalFinding(
                    severity="warning", recommendation_title=r.title,
                    issue=f"Confidence {r.confidence_score:.0%} with no retrieved-knowledge grounding (LLM reasoning only).",
                )
            )

    if result.findings:
        logger.info(
            f"Deep evaluation: {len(result.findings)} finding(s), {result.corrections_applied} auto-corrected."
        )

    return result
