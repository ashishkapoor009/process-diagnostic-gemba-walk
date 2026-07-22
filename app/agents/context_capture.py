"""Captures which knowledge-base chunks each ReAct agent actually retrieved
during its tool calls, so the Reviewer Agent's RAGAS evaluation can score
faithfulness/context metrics against the SAME context the agent reasoned
over (not a re-run retrieval, which could differ).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

_current_capture: ContextVar[list | None] = ContextVar("_current_capture", default=None)


def record_retrieved_chunks(chunks: list[str]) -> None:
    bucket = _current_capture.get()
    if bucket is not None:
        bucket.extend(chunks)


@contextmanager
def capture_context():
    bucket: list[str] = []
    token = _current_capture.set(bucket)
    try:
        yield bucket
    finally:
        _current_capture.reset(token)
