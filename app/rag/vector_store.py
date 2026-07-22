"""ChromaDB-backed vector store wrapper. Builds (or loads a persisted)
collection from the knowledge base on first use, and exposes a cached
singleton so every agent shares one Chroma client/collection.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config.llm_factory import get_embeddings
from app.config.settings import get_settings
from app.rag.loader import load_knowledge_base_documents
from app.utils.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "pe_gemba_knowledge_base"


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir_abs,
    )
    if store._collection.count() == 0:
        logger.info("Vector store empty - ingesting knowledge base for the first time.")
        documents = load_knowledge_base_documents()
        ids = [f"{d.metadata['source']}_{d.metadata['chunk_index']}" for d in documents]
        store.add_documents(documents, ids=ids)
        logger.info(f"Ingested {len(documents)} chunks into '{COLLECTION_NAME}'.")
    return store


def add_documents(documents: list[Document], id_prefix: str) -> None:
    store = get_vector_store()
    ids = [f"{id_prefix}_{i}" for i in range(len(documents))]
    store.add_documents(documents, ids=ids)


def reset_and_reingest() -> int:
    """Wipes and rebuilds the collection from the knowledge base folder.
    Used by the Settings page's "Rebuild Knowledge Base" action.
    """
    settings = get_settings()
    get_vector_store.cache_clear()
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir_abs,
    )
    existing = store._collection.get()
    if existing and existing.get("ids"):
        store._collection.delete(ids=existing["ids"])
    documents = load_knowledge_base_documents()
    ids = [f"{d.metadata['source']}_{d.metadata['chunk_index']}" for d in documents]
    store.add_documents(documents, ids=ids)
    get_vector_store.cache_clear()
    return len(documents)
