"""Shared helper for running a genuine ReAct (Reason + Act + Observe) agent
loop via LangGraph's prebuilt create_react_agent, then coercing the agent's
final free-text answer into a strict Pydantic schema with a follow-up
structured-output call. This gives every agent real tool-use reasoning
while still guaranteeing type-safe, database-ready output.
"""
from __future__ import annotations

from typing import TypeVar

from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, ValidationError

from app.agents.context_capture import capture_context
from app.config.llm_factory import get_chat_model
from app.utils.logging import get_logger
from app.utils.retry import llm_retry

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@llm_retry
def run_react_agent(system_prompt: str, user_message: str, tools: list, temperature: float = 0.2) -> str:
    """Runs a full ReAct loop (the agent may call tools 0-N times, observing
    results between calls) and returns the final natural-language answer.
    """
    llm = get_chat_model(temperature=temperature)
    # This pinned langgraph version (0.2.x) takes the system prompt via
    # `state_modifier`, not the `prompt` kwarg used by newer langgraph releases.
    agent = create_react_agent(llm, tools=tools, state_modifier=system_prompt)
    result = agent.invoke({"messages": [{"role": "user", "content": user_message}]})
    final_message = result["messages"][-1]
    return final_message.content if hasattr(final_message, "content") else str(final_message)


def _invoke_structured(llm, schema: type[T], prompt: str, **kwargs) -> T:
    return llm.with_structured_output(schema, **kwargs).invoke(prompt)


@llm_retry
def structure_output(raw_answer: str, schema: type[T], instruction: str = "") -> T:
    """Coerces a free-text ReAct answer into the given Pydantic schema using
    a dedicated structured-output call, so downstream code always receives
    clean, validated data regardless of how the agent phrased its reasoning.

    Three layers of defense against a hallucinated enum value (e.g. a
    recommendation's `category` set to a free-text string like "Error
    Proofing" instead of one of the allowed ImprovementCategory members),
    which previously surfaced as a raw Pydantic ValidationError that crashed
    the entire diagnostic job:

    1. OpenAI strict JSON-schema structured outputs (`method="json_schema"`,
       `strict=True`) constrain enum fields server-side, so the model
       literally cannot emit a value outside the schema on supported models.
    2. If that mode isn't supported by the configured provider/deployment,
       fall back to the default structured-output method.
    3. If validation still fails, re-prompt once with the exact Pydantic
       error and ask the model to fix only the offending field(s).
    """
    llm = get_chat_model(temperature=0.0)
    prompt = (
        f"{instruction}\n\nConvert the following analysis into the required "
        f"structured format. Preserve every concrete fact and recommendation; "
        f"do not drop content, only reshape it.\n\n---\n{raw_answer}\n---"
    )

    try:
        return _invoke_structured(llm, schema, prompt, method="json_schema", strict=True)
    except ValidationError as exc:
        logger.warning(f"Strict structured output failed validation, falling back: {exc}")
    except Exception as exc:
        logger.warning(f"Strict JSON-schema structured output unsupported ({exc}); falling back.")

    try:
        return _invoke_structured(llm, schema, prompt)
    except ValidationError as exc:
        logger.warning(f"Structured output validation failed, retrying with correction: {exc}")
        correction_prompt = (
            f"{prompt}\n\nYour previous attempt failed validation with this error:\n{exc}\n\n"
            "Fix ONLY the offending field(s) - use exactly one of the allowed enum values named "
            "in the error above. Do not change anything else."
        )
        return _invoke_structured(llm, schema, correction_prompt)


def react_and_structure(system_prompt: str, user_message: str, tools: list, schema: type[T],
                          structuring_instruction: str = "", temperature: float = 0.2) -> tuple[T, str]:
    """Convenience wrapper: run the ReAct loop, then structure its answer.
    Returns (structured_result, raw_agent_answer) - the raw answer is kept
    for AgentResponse audit logging.
    """
    raw_answer = run_react_agent(system_prompt, user_message, tools, temperature=temperature)
    structured = structure_output(raw_answer, schema, structuring_instruction)
    return structured, raw_answer


def react_and_structure_with_context(system_prompt: str, user_message: str, tools: list, schema: type[T],
                                       structuring_instruction: str = "", temperature: float = 0.2
                                       ) -> tuple[T, str, list[str]]:
    """Same as react_and_structure, but also returns every knowledge-base
    chunk the agent actually retrieved via search_knowledge_base during its
    ReAct loop - used as the RAGAS evaluation contexts for this agent's output.
    """
    with capture_context() as retrieved_chunks:
        raw_answer = run_react_agent(system_prompt, user_message, tools, temperature=temperature)
    structured = structure_output(raw_answer, schema, structuring_instruction)
    return structured, raw_answer, list(retrieved_chunks)
