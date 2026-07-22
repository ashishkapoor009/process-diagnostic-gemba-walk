"""Single place that builds LangChain chat + embedding clients, switching
transparently between OpenAI and Azure OpenAI based on Settings.llm_provider.
Every agent and the RAG layer import from here instead of instantiating
langchain_openai clients directly, so provider swaps stay a one-line config
change.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config.settings import get_settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when an LLM call is attempted without API credentials set."""


@lru_cache
def get_chat_model(temperature: float = 0.2) -> BaseChatModel:
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMNotConfiguredError(
            "No LLM credentials configured. Set OPENAI_API_KEY (or the "
            "AZURE_OPENAI_* variables) in your .env file."
        )

    if settings.llm_provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_chat_deployment,
            temperature=temperature,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        temperature=temperature,
    )


@lru_cache
def get_embeddings() -> Embeddings:
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMNotConfiguredError(
            "No LLM credentials configured. Set OPENAI_API_KEY (or the "
            "AZURE_OPENAI_* variables) in your .env file."
        )

    if settings.llm_provider == "azure_openai":
        from langchain_openai import AzureOpenAIEmbeddings

        return AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_embedding_deployment,
        )

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
    )
