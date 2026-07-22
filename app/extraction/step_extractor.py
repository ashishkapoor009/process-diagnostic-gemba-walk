"""Converts raw extracted text (from OCR/document parsing, or free-typed
user input) into a structured list of ProcessStepInput using the LLM with
a Pydantic structured-output schema. This is the "OCR + LLM" extraction
pipeline referenced in the spec.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config.llm_factory import get_chat_model
from app.schemas.process import ProcessStepInput
from app.utils.logging import get_logger
from app.utils.retry import llm_retry

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a Lean Six Sigma Master Black Belt performing a Gemba walk.
You are given raw text extracted from a process document (which may be messy,
OCR'd, or a table dump from a Visio/BPMN/PPT/PDF export). Your job is to
reconstruct the ORDERED list of discrete process steps it describes.

Rules:
- Merge fragments that clearly belong to the same step; split run-on text
  that clearly describes multiple sequential actions.
- Preserve the original process order as best you can infer it.
- If a step is a decision/gateway (Yes/No, Approved/Rejected, routing), set is_decision=true.
- Fill owner/system_used/input_data/output_data/cycle_time_minutes ONLY if
  stated or strongly implied by the text; otherwise leave them null/empty
  rather than inventing specifics.
- Produce at least 3 steps when the source text supports it. Never fabricate
  a process that isn't grounded in the given text.
"""


class _StepList(BaseModel):
    steps: list[ProcessStepInput] = Field(default_factory=list)


@llm_retry
def extract_steps_from_text(raw_text: str, process_name: str = "") -> list[ProcessStepInput]:
    if not raw_text or not raw_text.strip():
        return []

    llm = get_chat_model(temperature=0.0)
    structured_llm = llm.with_structured_output(_StepList)

    user_prompt = (
        f"Process name (if known): {process_name or 'Unknown'}\n\n"
        f"Raw extracted content:\n---\n{raw_text[:12000]}\n---\n\n"
        "Return the ordered list of process steps as structured data. "
        "Number step_number starting at 1, incrementing by 1 with no gaps."
    )

    result: _StepList = structured_llm.invoke(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    # Guarantee monotonic step numbering regardless of what the model returned.
    for i, step in enumerate(result.steps, start=1):
        step.step_number = i

    logger.info(f"LLM extracted {len(result.steps)} process steps from raw text ({len(raw_text)} chars)")
    return result.steps


def parse_manual_steps(text: str) -> list[ProcessStepInput]:
    """Fast-path, non-LLM parser for the manual-entry text box: one step per
    non-empty line, optionally 'Step name :: owner :: system :: minutes'.
    Used as an instant preview before the LLM enrichment pass runs.
    """
    steps: list[ProcessStepInput] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip().lstrip("-*0123456789.) ").strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("::")]
        name = parts[0]
        owner = parts[1] if len(parts) > 1 else None
        system_used = parts[2] if len(parts) > 2 else None
        cycle_time = None
        if len(parts) > 3:
            try:
                cycle_time = float(parts[3])
            except ValueError:
                cycle_time = None
        steps.append(
            ProcessStepInput(
                step_number=len(steps) + 1,
                step_name=name,
                owner=owner,
                system_used=system_used,
                cycle_time_minutes=cycle_time,
            )
        )
    return steps
