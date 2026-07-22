"""Settings page: view runtime configuration (LLM provider, RAGAS
threshold, target efficiency range, storage paths), toggle dark mode, and
inspect the audit log.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.config.settings import get_settings
from app.database.crud import session_scope
from app.database.models import AuditLog
from app.ui.styling import apply_branding, page_header

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
apply_branding()
page_header("Settings", "Runtime configuration, appearance, and audit trail.")

settings = get_settings()

st.subheader("Appearance")
st.toggle("🌙 Dark Mode", key="dark_mode")

st.divider()
st.subheader("LLM Configuration")
c1, c2 = st.columns(2)
c1.metric("Provider", settings.llm_provider)
c2.metric("Configured", "✅ Yes" if settings.llm_configured else "❌ No - set API key in .env")
if settings.llm_provider == "openai":
    st.code(f"OPENAI_CHAT_MODEL={settings.openai_chat_model}\nOPENAI_EMBEDDING_MODEL={settings.openai_embedding_model}")
else:
    st.code(
        f"AZURE_OPENAI_CHAT_DEPLOYMENT={settings.azure_openai_chat_deployment}\n"
        f"AZURE_OPENAI_EMBEDDING_DEPLOYMENT={settings.azure_openai_embedding_deployment}\n"
        f"AZURE_OPENAI_API_VERSION={settings.azure_openai_api_version}"
    )
st.caption("Change credentials in your `.env` file (see `.env.example`), then restart the app.")

st.divider()
st.subheader("Quality Gates & Targets")
q1, q2, q3 = st.columns(3)
q1.metric("RAGAS Minimum Score", f"{settings.ragas_min_score:.0%}")
q2.metric("Max Review Rounds", settings.ragas_max_review_rounds)
q3.metric("Target Efficiency", f"{settings.target_efficiency_low:.0%} - {settings.target_efficiency_high:.0%}")

st.divider()
st.subheader("Storage")
st.code(
    f"SQLite DB: {settings.sqlite_url}\nChromaDB: {settings.chroma_dir_abs}\nUploads: {settings.upload_dir_abs}"
)

st.divider()
st.subheader("Audit Log (most recent 100 events)")
try:
    with session_scope() as db:
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
        df = pd.DataFrame(
            [{"Time": l.created_at, "Process ID": l.process_id, "Actor": l.actor, "Action": l.action} for l in logs]
        )
    st.dataframe(df, use_container_width=True, hide_index=True)
except Exception as exc:
    st.info(f"No audit log yet ({exc}).")
