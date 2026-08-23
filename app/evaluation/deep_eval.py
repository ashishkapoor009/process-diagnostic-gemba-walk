"""Deep evaluation: deterministic grounding checks that complement RAGAS.
RAGAS judges whether the Reviewer Agent's narrative answer is faithful to
retrieved knowledge - it has no way to know that a recommendation
references a process step that doesn't exist, or is asserted with high
confidence but no retrieved grounding at all. This module catches exactly
that class of error.

Purely observational - it reports findings, it does not correct data.
Like RAGAS (see app/agents/orchestrator.py's module docstring), it runs
independently of the agent graph: app/services/pipeline_runner.py calls it
on already-persisted diagnostics/recommendations, after the pipeline has
returned to its caller, so it never influences agent behavior or the
revision loop. It used to also flag/auto-correct FTE-savings numbers that
exceeded the process total, but by the time this runs independently the
recommendations are already pulled from SQLite post-persistence - the
savings calculator guarantees that arithmetic is sane before anything is
ever persisted (see app/agents/savings_calculator.py's
_clamp_fte_savings), so a check here could never find anything to flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.evaluation import DeepEvalFinding
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic
from app.schemas.recommendation import Recommendation
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeepEvalResult:
    findings: list[DeepEvalFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


def deep_evaluate_recommendations(
    metadata: ProcessMetadata, diagnostics: list[ProcessStepDiagnostic], recommendations: list[Recommendation],
    round_number: int = 1,
) -> DeepEvalResult:
    result = DeepEvalResult()
    valid_step_numbers = {d.step_number for d in diagnostics}
    active_recs = [r for r in recommendations if not r.is_duplicate]

    # A recommendation referencing a step_number that doesn't exist in this
    # process's diagnosed steps is a grounding failure.
    for r in active_recs:
        if r.step_number is not None and r.step_number not in valid_step_numbers:
            result.findings.append(
                DeepEvalFinding(
                    severity="warning", recommendation_title=r.title, round_number=round_number,
                    issue=f"References step {r.step_number}, which doesn't exist in this process's diagnosed steps.",
                )
            )

    # Overconfident with no retrieved grounding: pure LLM reasoning claiming
    # very high confidence is a soft red flag worth a human look.
    for r in active_recs:
        if r.source_type.value == "LLM Reasoning" and r.confidence_score > 0.9:
            result.findings.append(
                DeepEvalFinding(
                    severity="warning", recommendation_title=r.title, round_number=round_number,
                    issue=f"Confidence {r.confidence_score:.0%} with no retrieved-knowledge grounding (LLM reasoning only).",
                )
            )

    if result.findings:
        logger.info(f"Deep evaluation: {len(result.findings)} finding(s).")

    return result
