"""Optional FastAPI backend service layer.

Exposes the same multi-agent diagnostic pipeline as a REST API so a
separately hosted frontend (e.g. a Next.js app on Vercel) can drive this
tool without embedding Streamlit. Run with:
    uvicorn app.main:api --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

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
from app.reports.word import generate_word_report
from app.schemas.process import ProcessMetadata, ProcessStepInput
from app.ui.pipeline_runner import run_and_persist_pipeline
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
        "recommendations": [r.model_dump() for r in ctx.recommendations],
        "savings_summary": ctx.savings_summary,
        "executive_summary": ctx.executive_summary,
        "flow_mermaid_current": ctx.flow_mermaid_current,
        "flow_mermaid_future": ctx.flow_mermaid_future,
    }


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
