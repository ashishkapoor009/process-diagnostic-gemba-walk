"""Runs the full six-agent diagnostic via the LangGraph orchestrator and
persists every artifact (diagnostics, recommendations, deep eval findings,
flow diagrams, executive summary) to SQLite so it survives process restarts
and can be re-fetched by the API.

RAGAS evaluation lives entirely in this module, not the agent graph (see
app/agents/orchestrator.py's module docstring for why). run_and_persist_pipeline
persists the Reviewer Agent's raw (question, answer, contexts) per round and
returns to its caller WITHOUT waiting for RAGAS; a background thread scores
them afterward. rerun_ragas_evaluation lets a caller (see the
/api/processes/{id}/evaluate-ragas endpoint) re-trigger scoring on demand
against those same stored artifacts, independent of any pipeline run.
"""
from __future__ import annotations

import json
import threading

from app.agents.orchestrator import run_full_diagnostic
from app.agents.savings_calculator import compute_current_state_baseline
from app.config.settings import get_settings
from app.database import crud
from app.database.rehydrate import rehydrate_process_metadata, rehydrate_recommendations
from app.evaluation.kpi_engine import compute_kpis
from app.evaluation.ragas import evaluate_response
from app.graphs.mermaid import render_swimlane
from app.schemas.evaluation import RagasScore
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic, ProcessStepInput
from app.utils.logging import get_logger

logger = get_logger(__name__)

_RAGAS_INPUT_NODE = "review_agent_ragas_input"


def run_and_persist_pipeline(metadata: ProcessMetadata, raw_steps: list[ProcessStepInput],
                               project_id: int | None = None) -> tuple[int, dict]:
    crud.ensure_db_ready()
    process_id = crud.create_process(project_id, metadata)
    crud.log_audit(process_id, "system", "diagnostic_started", {"steps": len(raw_steps)})

    final_state = run_full_diagnostic(metadata, raw_steps)

    diagnostics = final_state.get("diagnostics", [])
    future_diagnostics = final_state.get("future_diagnostics", [])
    recommendations = final_state.get("recommendations", [])

    # Persist both slices of the structured process map (current + future
    # state), then recommendations - in that order, so recommendations can
    # resolve their process_step_id FK against the just-saved current steps.
    crud.save_diagnostics(process_id, diagnostics, state="current")
    crud.save_diagnostics(process_id, future_diagnostics, state="future")
    crud.save_recommendations(process_id, recommendations)
    crud.save_flow_diagrams(
        process_id, final_state.get("flow_mermaid_current", ""), final_state.get("flow_mermaid_future", "")
    )
    crud.save_executive_summary(
        process_id, final_state.get("executive_summary", ""), final_state.get("savings_summary", {}),
        kpi_summary=final_state.get("kpi_summary", {}),
    )

    for note in final_state.get("review_notes", []):
        crud.save_agent_response(
            process_id, "Reviewer Agent", "review_agent",
            output_text=note.model_dump_json(), round_number=note.round_number,
        )

    # Persist the raw materials RAGAS needs (question/answer/contexts per
    # round) as their own AgentResponse rows - this is what makes RAGAS
    # scoring re-runnable independently later (see rerun_ragas_evaluation),
    # not just a one-shot side effect of this pipeline run.
    review_artifacts = final_state.get("review_artifacts", [])
    for artifact in review_artifacts:
        crud.save_agent_response(
            process_id, "Reviewer Agent", _RAGAS_INPUT_NODE,
            output_text=json.dumps(artifact), round_number=artifact["round_number"],
        )

    if final_state.get("deep_eval_findings"):
        crud.save_deep_eval_findings(process_id, final_state["deep_eval_findings"])

    crud.log_audit(process_id, "system", "diagnostic_completed", {
        "diagnostics": len(diagnostics), "recommendations": len(recommendations),
    })

    logger.info(f"Persisted diagnostic run for process_id={process_id}")

    # Fire-and-forget: RAGAS never blocks the caller or influences the
    # pipeline above. If this thread fails or the process restarts before
    # it finishes, the process simply has no RAGAS scores yet - the
    # frontend already handles that (empty evaluation_scores) and
    # rerun_ragas_evaluation can compute them later on demand.
    if review_artifacts:
        threading.Thread(
            target=run_independent_ragas_evaluation, args=(process_id, review_artifacts), daemon=True
        ).start()

    return process_id, final_state


def run_independent_ragas_evaluation(process_id: int, review_artifacts: list[dict]) -> list[RagasScore]:
    """The only place RAGAS actually runs. Takes each round's raw
    (question, answer, contexts) - produced by the Reviewer Agent but never
    scored by it - and evaluates them completely outside the agent graph.
    Safe to call from a background thread (fire-and-forget after a fresh
    run) or synchronously (a manual re-run via the API).
    """
    settings = get_settings()
    scores = []
    for artifact in review_artifacts:
        try:
            # `contexts` alone is only the knowledge-base chunks the
            # Reviewer Agent retrieved; its critique is mostly about this
            # process's own facts (FTE, savings figures, step names), which
            # live in `question`. Scoring against KB chunks alone measures
            # the wrong ground truth and drives scores toward zero
            # regardless of answer quality - `question` is legitimate
            # grounding the reviewer is supposed to draw claims from.
            score = evaluate_response(
                question=artifact["question"], answer=artifact["raw_answer"],
                contexts=artifact["contexts"] + [artifact["question"]],
            )
            crud.save_evaluation_score(
                process_id, score, threshold=settings.ragas_min_score, round_number=artifact["round_number"],
            )
            scores.append(score)
        except Exception:
            logger.exception(f"Independent RAGAS evaluation failed for process_id={process_id} "
                              f"round={artifact.get('round_number')}")
    logger.info(f"Independent RAGAS evaluation complete for process_id={process_id}: {len(scores)} round(s) scored")
    return scores


def rerun_ragas_evaluation(process_id: int) -> list[RagasScore]:
    """Manual on-demand re-score, using the same review_artifacts a prior
    pipeline run persisted - no agent re-runs, nothing in the graph is
    touched, purely an independent evaluation pass.
    """
    stored = crud.get_agent_responses(process_id, node_name=_RAGAS_INPUT_NODE)
    if not stored:
        raise ValueError(f"No stored Reviewer Agent output found for process {process_id} to evaluate.")
    review_artifacts = [json.loads(row.output_text) for row in stored]
    crud.delete_evaluation_scores(process_id)
    return run_independent_ragas_evaluation(process_id, review_artifacts)


def update_current_state_diagnostics(process_id: int, diagnostics: list[ProcessStepDiagnostic]) -> dict:
    """User-initiated correction to the current-state process map (e.g. a
    real owner name instead of "Unknown", a corrected cycle time). Only
    touches deterministic, non-LLM outputs: the persisted step rows, the
    current-state Mermaid diagram, the baseline PCE calc, and the KPI
    benchmark comparison. Recommendations, the executive summary, and the
    future-state flow were generated by LLM calls against the ORIGINAL
    diagnostics and are deliberately left untouched - regenerating them
    would mean re-running the full pipeline, not a lightweight correction.
    """
    data = crud.get_process_full(process_id)
    process = data.get("process")
    if not process:
        raise ValueError(f"Process {process_id} not found")

    metadata = rehydrate_process_metadata(process)
    recommendations = rehydrate_recommendations(data.get("recommendations", []))
    active_recommendations = [r for r in recommendations if not r.is_duplicate]

    crud.save_diagnostics(process_id, diagnostics, state="current")

    current_mermaid = render_swimlane(diagnostics, title=f"{metadata.process_name} - Current State")
    crud.save_flow_diagrams(process_id, current_mermaid, process.flow_mermaid_future or "")

    savings_summary = dict(process.savings_summary_json or {})
    savings_summary["baseline"] = compute_current_state_baseline(metadata, diagnostics)
    kpi_summary = compute_kpis(metadata, diagnostics, active_recommendations, savings_summary)
    crud.save_executive_summary(
        process_id, process.executive_summary or "", savings_summary, kpi_summary=kpi_summary
    )

    crud.log_audit(process_id, "user", "current_state_diagnostics_edited", {"steps": len(diagnostics)})
    logger.info(f"Updated current-state diagnostics for process_id={process_id}")

    return {
        "diagnostics": [d.model_dump() for d in diagnostics],
        "savings_summary": savings_summary,
        "kpi_summary": kpi_summary,
        "flow_mermaid_current": current_mermaid,
    }
