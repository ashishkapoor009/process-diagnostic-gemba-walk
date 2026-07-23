"""Retrieval helpers used by every agent before it reasons/answers -
implements the "retrieve context before answering" RAG requirement, and
logs every query to RagHistory for auditability.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.rag.vector_store import get_vector_store
from app.utils.caching import disk_cache
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    source: str
    section: str
    score: float


@disk_cache("rag_similarity_search")
def _cached_similarity_search(query: str, k: int) -> list[tuple[str, str, str, float]]:
    """The embedding call + vector search is the expensive part of every
    retrieval - this is the "working memory" cache layer: repeated queries
    (common across agents/rounds - e.g. multiple agents searching "Lean
    waste") are served from disk instead of re-embedding and re-querying
    ChromaDB. Returns plain tuples (not LangChain Document objects) so the
    cache stays picklable/stable across code changes to the Document class.
    """
    store = get_vector_store()
    results = store.similarity_search_with_relevance_scores(query, k=k)
    return [(doc.page_content, doc.metadata.get("source", "unknown"), doc.metadata.get("section", ""), float(score))
            for doc, score in results]


def retrieve_context(query: str, k: int = 5, process_id: int | None = None,
                      log_to_db: bool = True) -> list[RetrievedChunk]:
    results = _cached_similarity_search(query, k)

    chunks = [
        RetrievedChunk(content=content, source=source, section=section, score=score)
        for content, source, section, score in results
    ]

    if log_to_db:
        try:
            from app.database.crud import log_rag_query

            log_rag_query(process_id, query, [f"{c.source}::{c.section}" for c in chunks], k)
        except Exception as exc:  # pragma: no cover - DB may not be initialized in some contexts
            logger.debug(f"RAG history logging skipped: {exc}")

    return chunks


def format_context_for_prompt(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant knowledge-base context retrieved."
    lines = []
    for i, c in enumerate(chunks, start=1):
        lines.append(f"[{i}] (source: {c.source} | {c.section} | relevance={c.score:.2f})\n{c.content}")
    return "\n\n".join(lines)


def context_sources(chunks: list[RetrievedChunk]) -> list[str]:
    return [f"{c.source}::{c.section}" for c in chunks]
