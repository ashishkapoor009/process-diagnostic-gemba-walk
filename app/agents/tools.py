"""LangChain tools shared by every ReAct agent: retrieving grounded
knowledge-base context (RAG) and looking up specific process facts. Giving
agents tools (rather than dumping everything into the prompt) is what makes
them genuine ReAct agents - they decide when to call a tool, observe the
result, and reason over it before producing a final answer.
"""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.agents.context_capture import record_retrieved_chunks
from app.rag.retriever import format_context_for_prompt, retrieve_context


def build_process_lookup_tool(metadata: dict, steps: list[dict]):
    """Factory: bakes the current process's data into a closured tool so the
    agent can look up specific facts on demand instead of re-reading a huge
    prompt block for every reasoning turn.
    """

    @tool("get_process_details")
    def get_process_details(field: str = "all") -> str:
        """Look up details about the process under analysis. Pass 'metadata'
        for process-level facts (FTE, volume, AHT, department, pain areas,
        systems used, compliance requirements, etc.), 'steps' for the list
        of raw process steps, or 'all' for both.
        """
        payload = {}
        if field in ("metadata", "all"):
            payload["metadata"] = metadata
        if field in ("steps", "all"):
            payload["steps"] = steps
        return json.dumps(payload, default=str)[:6000]

    return get_process_details


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Search the Process Excellence knowledge base (Lean Six Sigma, Toyota
    Production System, Kaizen, BPM CBOK, Process Mining, VSM, RPA best
    practices, GenAI/Agentic AI patterns, ISO/COPC/ITIL/COBIT/PMBOK, SOP
    templates) for guidance relevant to the given query. Always call this
    before recommending a specific methodology or tool so the recommendation
    is grounded in established best practice rather than invented.
    """
    chunks = retrieve_context(query, k=4, log_to_db=True)
    record_retrieved_chunks([c.content for c in chunks])
    return format_context_for_prompt(chunks)


def default_tools(metadata: dict, steps: list[dict]) -> list:
    return [search_knowledge_base, build_process_lookup_tool(metadata, steps)]
