"""
Local Ollama runtime helpers.

Provides resilient model selection and non-streaming generation against localhost:11434.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://127.0.0.1:11434"


@lru_cache(maxsize=1)
def list_models() -> List[str]:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=8)
        r.raise_for_status()
        models = r.json().get("models") or []
        return [str((m or {}).get("name") or "").strip() for m in models if (m or {}).get("name")]
    except Exception as e:
        logger.warning("ollama model discovery failed: %s", e)
        return []


def resolve_model(preferred: Optional[str] = None, fallbacks: Optional[List[str]] = None) -> Optional[str]:
    available_list = list_models()
    available = set(available_list)
    candidates: List[str] = []
    if preferred:
        candidates.append(preferred.strip())
    candidates.extend(fallbacks or [])
    for name in candidates:
        n = (name or "").strip()
        if n and n in available:
            return n
    preferred_default_order = [
        "llama3.2:3b",
        "llama3.1",
        "llama3.3",
        "deepseek-coder-v2:16b",
        "qwen2.5:72b",
    ]
    for name in preferred_default_order:
        if name in available:
            return name
    return available_list[0] if available_list else None


def generate(prompt: str, preferred_model: Optional[str] = None, options: Optional[Dict[str, Any]] = None, timeout: int = 25) -> str:
    model = resolve_model(
        preferred=preferred_model,
        fallbacks=["llama3.2:3b", "llama3.1", "llama3.3", "deepseek-coder-v2:16b", "qwen2.5:72b"],
    )
    if not model:
        return ""
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options or {"temperature": 0.5, "num_predict": 90},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return (r.json().get("response") or "").strip()
    except Exception as e:
        logger.warning("ollama generate failed (model=%s): %s", model, e)
        return ""

