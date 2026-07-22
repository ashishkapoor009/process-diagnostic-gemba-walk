"""Knowledge Base page: search the RAG-grounding corpus (Lean Six Sigma,
TPS, BPM CBOK, RPA, GenAI/Agentic patterns, ISO/COPC/ITIL/COBIT/PMBOK, SOP
templates) directly, view recent RAG retrieval history, and rebuild the
ChromaDB collection.
"""
from __future__ import annotations

import streamlit as st

from app.config.settings import get_settings
from app.rag.loader import KB_DIR
from app.rag.retriever import retrieve_context
from app.rag.vector_store import get_vector_store, reset_and_reingest
from app.ui.styling import apply_branding, page_header

st.set_page_config(page_title="Knowledge Base", page_icon="📚", layout="wide")
apply_branding()
page_header("Knowledge Base", "The enterprise RAG corpus every agent retrieves from before answering.")

settings = get_settings()

st.subheader("Source Documents")
md_files = sorted(KB_DIR.glob("*.md"))
cols = st.columns(3)
for i, f in enumerate(md_files):
    with cols[i % 3]:
        with st.expander(f.stem.replace("_", " ").title()):
            st.markdown(f.read_text(encoding="utf-8")[:2500] + "...")

st.divider()
st.subheader("Search the Knowledge Base")
query = st.text_input("Query", placeholder="e.g. RPA tool selection criteria")
top_k = st.slider("Results", 1, 10, 5)
if query and settings.llm_configured:
    try:
        chunks = retrieve_context(query, k=top_k, log_to_db=False)
        for c in chunks:
            with st.container(border=True):
                st.caption(f"Source: {c.source} | Section: {c.section} | Relevance: {c.score:.2f}")
                st.write(c.content)
    except Exception as exc:
        st.error(f"Search failed: {exc}")
elif query:
    st.warning("Configure LLM credentials (OPENAI_API_KEY) to enable semantic search.")

st.divider()
st.subheader("Vector Store Administration")
c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 Rebuild Knowledge Base Index", disabled=not settings.llm_configured):
        with st.spinner("Re-ingesting knowledge base into ChromaDB..."):
            try:
                count = reset_and_reingest()
                st.success(f"Rebuilt index with {count} chunks.")
            except Exception as exc:
                st.error(f"Rebuild failed: {exc}")
with c2:
    if settings.llm_configured:
        try:
            store = get_vector_store()
            st.metric("Indexed Chunks", store._collection.count())
        except Exception:
            st.metric("Indexed Chunks", "N/A")
    st.caption(f"Persisted at: {settings.chroma_dir_abs}")
