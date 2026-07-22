"""Bridges the Streamlit UI to the LangGraph orchestrator + persistence
layer: runs the full six-agent diagnostic and writes every artifact
(diagnostics, recommendations, RAGAS scores, flow diagrams, executive
summary) to SQLite so it survives page navigation and future sessions.
"""
from __future__ import annotations

from app.agents.orchestrator import run_full_diagnostic
from app.database import crud
from app.schemas.process import ProcessMetadata, ProcessStepInput
from app.utils.logging import get_logger

logger = get_logger(__name__)


def run_and_persist_pipeline(metadata: ProcessMetadata, raw_steps: list[ProcessStepInput],
                               project_id: int | None = None) -> tuple[int, dict]:
    crud.ensure_db_ready()
    process_id = crud.create_process(project_id, metadata)
    crud.log_audit(process_id, "system", "diagnostic_started", {"steps": len(raw_steps)})

    final_state = run_full_diagnostic(metadata, raw_steps)

    diagnostics = final_state.get("diagnostics", [])
    recommendations = final_state.get("recommendations", [])

    crud.save_diagnostics(process_id, diagnostics)
    crud.save_recommendations(process_id, recommendations)
    crud.save_flow_diagrams(
        process_id, final_state.get("flow_mermaid_current", ""), final_state.get("flow_mermaid_future", "")
    )
    crud.save_executive_summary(
        process_id, final_state.get("executive_summary", ""), final_state.get("savings_summary", {})
    )

    for i, note in enumerate(final_state.get("review_notes", [])):
        response_id = crud.save_agent_response(
            process_id, "Reviewer Agent", "review_agent",
            output_text=note.model_dump_json(), round_number=note.round_number,
        )
        if i < len(final_state.get("ragas_scores", [])):
            crud.save_evaluation_score(
                process_id, final_state["ragas_scores"][i], threshold=0.70,
                agent_response_id=response_id, round_number=note.round_number,
            )

    crud.log_audit(process_id, "system", "diagnostic_completed", {
        "diagnostics": len(diagnostics), "recommendations": len(recommendations),
    })

    logger.info(f"Persisted diagnostic run for process_id={process_id}")
    return process_id, final_state
