"""Loads the enterprise knowledge base (Lean Six Sigma, TPS, BPM CBOK,
RPA, GenAI/Agentic patterns, ISO/COPC/ITIL/COBIT/PMBOK, SOP templates) and
chunks it for embedding into ChromaDB.
"""
from __future__ import annotations

from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.utils.logging import get_logger

logger = get_logger(__name__)

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=900,
    chunk_overlap=150,
    separators=["\n## ", "\n### ", "\n\n", "\n", " "],
)


def load_knowledge_base_documents() -> list[Document]:
    """Read every markdown file in the knowledge base directory, split into
    overlapping chunks, and tag each chunk with its source file and section
    heading for citation/traceability in recommendations.
    """
    documents: list[Document] = []
    for path in sorted(KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks = _SPLITTER.split_text(text)
        for i, chunk in enumerate(chunks):
            heading = chunk.strip().splitlines()[0].lstrip("#").strip() if chunk.strip() else path.stem
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": path.stem,
                        "section": heading[:120],
                        "chunk_index": i,
                    },
                )
            )
    logger.info(f"Loaded {len(documents)} knowledge-base chunks from {KB_DIR}")
    return documents


def load_supplementary_documents(extra_texts: list[tuple[str, str]]) -> list[Document]:
    """Chunk ad-hoc supplementary text (e.g. an uploaded internal SOP or a
    prior similar process's diagnostic) so it can be added to the same
    vector store for process benchmarking.
    extra_texts: list of (source_name, text) tuples.
    """
    documents: list[Document] = []
    for source_name, text in extra_texts:
        for i, chunk in enumerate(_SPLITTER.split_text(text)):
            documents.append(
                Document(page_content=chunk, metadata={"source": source_name, "section": f"chunk_{i}", "chunk_index": i})
            )
    return documents
