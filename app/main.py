"""FastAPI backend service layer.

Exposes the multi-agent diagnostic pipeline as a REST API consumed by the
Next.js frontend. Run with:
    uvicorn app.main:api --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.config.settings import get_settings
from app.database import crud
from app.database.rehydrate import load_report_context
from app.extraction.document_parser import parse_document
from app.extraction.step_extractor import extract_steps_from_text
from app.reports.excel import generate_excel_report
from app.reports.pdf import generate_pdf_report
from app.reports.ppt import generate_ppt_report
from app.reports.standalone_exports import (
    generate_golden_dataset_excel,
    generate_golden_dataset_ppt,
    generate_recommendations_excel,
    generate_recommendations_ppt,
)
from app.reports.word import generate_word_report
from app.schemas.process import ProcessMetadata, ProcessStepDiagnostic, ProcessStepInput
from app.services.pipeline_runner import run_and_persist_pipeline, update_current_state_diagnostics
from app.utils.logging import get_logger

logger = get_logger(__name__)

api = FastAPI(
    title="Process Diagnostic / Gemba Walk Multi-Agent API",
    description="REST API for the multi-agent Process Excellence diagnostic platform.",
    version="1.0.0",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your deployed frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.on_event("startup")
def on_startup() -> None:
    crud.ensure_db_ready()
    logger.info("FastAPI backend started; SQLite database ready.")


class DiagnosticRequest(BaseModel):
    metadata: ProcessMetadata
    steps: list[ProcessStepInput]
    project_id: int | None = None


class ExtractStepsRequest(BaseModel):
    raw_text: str
    process_name: str = ""


@api.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "llm_configured": settings.llm_configured, "llm_provider": settings.llm_provider}


@api.post("/api/extract/text")
def extract_from_text(payload: ExtractStepsRequest) -> list[ProcessStepInput]:
    return extract_steps_from_text(payload.raw_text, payload.process_name)


@api.post("/api/extract/upload")
async def extract_from_upload(file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    upload_path = Path(settings.upload_dir_abs) / file.filename
    content = await file.read()
    upload_path.write_bytes(content)

    extracted = parse_document(upload_path)
    steps = extract_steps_from_text(extracted.combined_text, "")
    crud.log_upload(None, file.filename, extracted.file_type, str(upload_path), len(steps))
    return {"filename": file.filename, "used_ocr": extracted.used_ocr, "steps": [s.model_dump() for s in steps]}


@api.post("/api/processes")
def create_and_run_diagnostic(payload: DiagnosticRequest) -> dict:
    """Synchronous variant - blocks for the full 3-8 minute pipeline run.
    Only suitable for direct backend-to-backend calls with a generous
    timeout; browser/Vercel clients should use the async job endpoints
    below instead (POST /api/jobs + poll GET /api/jobs/{job_id}).
    """
    settings = get_settings()
    if not settings.llm_configured:
        raise HTTPException(status_code=503, detail="LLM credentials not configured on the server.")
    try:
        process_id, final_state = run_and_persist_pipeline(payload.metadata, payload.steps, payload.project_id)
    except Exception as exc:
        logger.exception("Diagnostic pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "process_id": process_id,
        "diagnostics_count": len(final_state.get("diagnostics", [])),
        "recommendations_count": len(final_state.get("recommendations", [])),
        "executive_summary": final_state.get("executive_summary", ""),
        "savings_summary": final_state.get("savings_summary", {}),
    }


# ---------------------------------------------------------------------------
# Async job pattern: the six-agent pipeline (RAGAS-gated, up to 2 review
# rounds) routinely takes 3-8 minutes - far longer than any serverless
# function timeout (Vercel caps at 60s) or typical browser fetch. The
# frontend starts a job, gets a job_id immediately, and polls for status.
#
# In-memory + a small thread pool is enough for a single-instance backend
# deployment (Render/Railway); swap for Redis/Celery if you ever run
# multiple backend replicas.
# ---------------------------------------------------------------------------
_job_executor = ThreadPoolExecutor(max_workers=2)
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_diagnostic_job(job_id: str, metadata: ProcessMetadata, steps: list[ProcessStepInput],
                          project_id: int | None) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["started_at"] = _now()
    try:
        process_id, final_state = run_and_persist_pipeline(metadata, steps, project_id)
        with _jobs_lock:
            _jobs[job_id].update(
                status="completed",
                completed_at=_now(),
                process_id=process_id,
                result={
                    "diagnostics_count": len(final_state.get("diagnostics", [])),
                    "recommendations_count": len(final_state.get("recommendations", [])),
                    "executive_summary": final_state.get("executive_summary", ""),
                    "savings_summary": final_state.get("savings_summary", {}),
                },
            )
    except Exception as exc:
        logger.exception(f"Diagnostic job {job_id} failed")
        with _jobs_lock:
            _jobs[job_id].update(status="failed", completed_at=_now(), error=str(exc))


@api.post("/api/jobs")
def start_diagnostic_job(payload: DiagnosticRequest) -> dict:
    settings = get_settings()
    if not settings.llm_configured:
        raise HTTPException(status_code=503, detail="LLM credentials not configured on the server.")

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "queued", "created_at": _now()}
    _job_executor.submit(_run_diagnostic_job, job_id, payload.metadata, payload.steps, payload.project_id)
    return {"job_id": job_id, "status": "queued"}


@api.get("/api/jobs/{job_id}")
def get_job_status(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"job_id": job_id, **job}


@api.get("/api/processes")
def list_processes() -> list[dict]:
    return crud.list_processes()


@api.get("/api/processes/{process_id}")
def get_process(process_id: int) -> dict:
    ctx = load_report_context(process_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Process not found.")
    return {
        "metadata": ctx.metadata.model_dump(),
        "diagnostics": [d.model_dump() for d in ctx.diagnostics],
        "future_diagnostics": [d.model_dump() for d in ctx.future_diagnostics],
        "recommendations": [r.model_dump() for r in ctx.recommendations],
        "savings_summary": ctx.savings_summary,
        "kpi_summary": ctx.kpi_summary,
        "executive_summary": ctx.executive_summary,
        "flow_mermaid_current": ctx.flow_mermaid_current,
        "flow_mermaid_future": ctx.flow_mermaid_future,
        "evaluation_scores": ctx.evaluation_scores,
        "deep_eval_findings": [f.model_dump() for f in ctx.deep_eval_findings],
    }


class UpdateStepsRequest(BaseModel):
    diagnostics: list[ProcessStepDiagnostic]


@api.patch("/api/processes/{process_id}/steps")
def update_process_steps(process_id: int, payload: UpdateStepsRequest) -> dict:
    """User-editable correction to the current-state diagnostics table -
    optional, does not re-run the LLM pipeline. See
    update_current_state_diagnostics for exactly what does and doesn't
    recompute.
    """
    try:
        return update_current_state_diagnostics(process_id, payload.diagnostics)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


_REPORT_GENERATORS = {
    "pdf": (generate_pdf_report, "application/pdf", "pdf"),
    "word": (generate_word_report, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "excel": (generate_excel_report, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "ppt": (generate_ppt_report, "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
}


@api.get("/api/processes/{process_id}/report/{fmt}")
def download_report(process_id: int, fmt: Literal["pdf", "word", "excel", "ppt"]) -> Response:
    ctx = load_report_context(process_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Process not found.")
    generator, mime, ext = _REPORT_GENERATORS[fmt]
    content = generator(ctx)
    filename = f"{ctx.metadata.process_name}_GembaWalk.{ext}"
    return Response(content=content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

_RECOMMENDATIONS_GENERATORS = {
    "excel": (generate_recommendations_excel, _XLSX_MIME, "xlsx"),
    "ppt": (generate_recommendations_ppt, _PPTX_MIME, "pptx"),
}


@api.get("/api/processes/{process_id}/recommendations/{fmt}")
def download_recommendations(process_id: int, fmt: Literal["excel", "ppt"]) -> Response:
    """Standalone recommendations table (mapped to process steps, with
    problem statements) - independent of the full report bundle above.
    """
    ctx = load_report_context(process_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Process not found.")
    generator, mime, ext = _RECOMMENDATIONS_GENERATORS[fmt]
    content = generator(ctx)
    filename = f"{ctx.metadata.process_name}_Recommendations.{ext}"
    return Response(content=content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


_GOLDEN_DATASET_GENERATORS = {
    "excel": (generate_golden_dataset_excel, _XLSX_MIME, "xlsx"),
    "ppt": (generate_golden_dataset_ppt, _PPTX_MIME, "pptx"),
}


@api.get("/api/golden-dataset/{fmt}")
def download_golden_dataset(fmt: Literal["excel", "ppt"]) -> Response:
    """The reference benchmark dataset the KPI engine compares every
    diagnostic against - downloadable standalone, independent of any process.
    """
    generator, mime, ext = _GOLDEN_DATASET_GENERATORS[fmt]
    content = generator()
    return Response(content=content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="Golden_Benchmark_Dataset.{ext}"'})
