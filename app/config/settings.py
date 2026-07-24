"""Centralized application configuration.

All runtime configuration is sourced from environment variables (via a .env
file in development) and exposed as a single, cached, typed Settings object.
Nothing else in the codebase should call os.environ directly - import
`get_settings()` instead so behaviour stays consistent and testable.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider selection ---
    llm_provider: Literal["openai", "azure_openai"] = "openai"

    openai_api_key: str = Field(default="")
    openai_chat_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"

    azure_openai_api_key: str = Field(default="")
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_chat_deployment: str = Field(default="")
    azure_openai_embedding_deployment: str = Field(default="")

    # --- App behaviour ---
    app_env: str = "development"
    log_level: str = "INFO"
    ragas_min_score: float = 0.70
    # RAGAS's 4-metric evaluation alone takes ~90s (each metric is a
    # sequential LLM-judge call); a full revision round (Kaizen + Postprocess
    # + Reviewer + RAGAS again) adds ~2.5-3 minutes on top of the ~3 minutes
    # the rest of the pipeline takes. Capped at 1 round so a run reliably
    # finishes under 5 minutes - deep evaluation's numeric auto-correction
    # (the harder safety net for concrete errors like inflated FTE savings)
    # still runs regardless of this setting; only the narrative-quality
    # revision loop is capped.
    ragas_max_review_rounds: int = 1
    target_efficiency_low: float = 0.25
    target_efficiency_high: float = 0.30

    # --- Storage ---
    sqlite_db_path: str = "./data/pe_agent.db"
    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"

    # --- OCR ---
    tesseract_cmd: str = "tesseract"

    # --- Backend ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    @property
    def sqlite_url(self) -> str:
        path = (BASE_DIR / self.sqlite_db_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"

    @property
    def chroma_dir_abs(self) -> str:
        path = (BASE_DIR / self.chroma_persist_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def upload_dir_abs(self) -> str:
        path = (BASE_DIR / self.upload_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        return bool(self.azure_openai_api_key and self.azure_openai_endpoint)


@lru_cache
def get_settings() -> Settings:
    return Settings()
