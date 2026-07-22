"""Lightweight disk+memory cache for expensive, deterministic operations
(embedding lookups, RAG retrieval, parsed-document caching) keyed by a
content hash so re-runs on the same input are instant.
"""
from __future__ import annotations

import functools
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Callable

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _hash_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def disk_cache(prefix: str) -> Callable:
    """Decorator that memoizes a function's return value to disk."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _hash_key(prefix, *args, **kwargs)
            cache_file = _CACHE_DIR / f"{key}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, "rb") as fh:
                        return pickle.load(fh)
                except Exception:
                    pass
            result = func(*args, **kwargs)
            try:
                with open(cache_file, "wb") as fh:
                    pickle.dump(result, fh)
            except Exception:
                pass
            return result

        return wrapper

    return decorator
