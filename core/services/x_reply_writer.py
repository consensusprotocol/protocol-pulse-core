"""
X Reply Writer (V5 Overhaul).

Generates replies using the unified Protocol Pulse reply prompt.
Handles NO_REPLY filtering, banned phrase detection, and plain-text output.
"""

import json
import logging
import os
from typing import Dict, Any

from .ai_service import AIService
from models import SentimentSnapshot

try:
    from core.config.response_prompt import (
        REPLY_SYSTEM_PROMPT,
        build_user_prompt,
        contains_banned_phrase,
    )
except Exception:
    from config.response_prompt import (
        REPLY_SYSTEM_PROMPT,
        build_user_prompt,
        contains_banned_phrase,
    )

try:
    from services.ollama_runtime import generate as ollama_generate
except Exception:
    ollama_generate = None

logger = logging.getLogger(__name__)

_MAX_REGENERATE_ATTEMPTS = 2


def _get_latest_sentiment() -> Dict[str, Any]:
    """Return latest SentimentSnapshot as a simple dict; safe if table empty."""
    try:
        snap = (
            SentimentSnapshot.query.order_by(
                SentimentSnapshot.computed_at.desc()
            ).first()
        )
        if not snap:
            return {}
        return {
            "score": snap.score,
            "state": snap.state,
            "label": snap.state_label,
            "velocity": snap.velocity,
        }
    except Exception as e:
        logger.debug("x_reply_writer: sentiment lookup failed: %s", e)
        return {}


def _is_no_reply(text: str) -> bool:
    """Check if the model chose not to reply."""
    stripped = text.strip().upper()
    return stripped == "NO_REPLY" or stripped == "NO REPLY"


def _clean_reply(text: str) -> str:
    """Clean up model output to plain reply text."""
    text = text.strip()
    # Strip wrapping quotes
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1].strip()
    # Strip common AI prefixes
    for prefix in ["Reply:", "reply:", "Here's a reply:", "Response:"]:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    # Enforce lowercase (mostly)
    text = text[0].lower() + text[1:] if text else text
    # Cap length at 180 chars (overhaul spec)
    if len(text) > 180:
        text = text[:177] + "..."
    return text


def _call_llm(user_prompt: str) -> str | None:
    """Call local Ollama first, fall back to AIService (OpenAI)."""
    use_local = str(
        os.environ.get("USE_LOCAL_GPU", "true")
    ).strip().lower() in {"1", "true", "yes", "on"}

    if use_local and ollama_generate is not None:
        model = (
            os.environ.get("OLLAMA_MODEL")
            or os.environ.get("MATTY_ICE_MODEL")
            or "llama3.2:3b"
        )
        local_prompt = f"{REPLY_SYSTEM_PROMPT}\n\n{user_prompt}"
        result = ollama_generate(
            prompt=local_prompt,
            preferred_model=model,
            options={"temperature": 0.7, "num_predict": 120},
            timeout=90,
        )
        if result and result.strip():
            return result.strip().splitlines()[0].strip()

    # Cloud fallback
    ai = AIService()
    result = ai.generate_structured_content(
        prompt=user_prompt,
        system_prompt=REPLY_SYSTEM_PROMPT,
        provider="openai",
    )
    if isinstance(result, dict):
        return (result.get("response") or result.get("text") or "").strip()
    return str(result).strip() if result else None


def generate_reply(
    tweet_text: str,
    author_handle: str,
    author_name: str | None = None,
    style_hint: str | None = None,
) -> Dict[str, Any]:
    """
    Generate a reply for a tweet using the V5 overhaul prompt.

    Returns a dict with keys:
    - response (str)
    - confidence (float)
    - reasoning (str)
    - style_used (str)
    - skip (bool)
    - reason (optional, when skip is true)
    """
    user_prompt = build_user_prompt(
        tweet_text=tweet_text,
        author_handle=author_handle,
        author_name=author_name,
    )

    for attempt in range(_MAX_REGENERATE_ATTEMPTS):
        try:
            raw = _call_llm(user_prompt)
            if not raw:
                return {"skip": True, "reason": "empty_response"}

            # NO_REPLY filter
            if _is_no_reply(raw):
                logger.info(
                    "x_reply_writer: NO_REPLY for @%s tweet", author_handle
                )
                return {"skip": True, "reason": "no_reply"}

            reply_text = _clean_reply(raw)
            if not reply_text:
                return {"skip": True, "reason": "empty_after_clean"}

            # Banned phrases filter
            if contains_banned_phrase(reply_text):
                logger.info(
                    "x_reply_writer: banned phrase detected (attempt %d), %s",
                    attempt + 1,
                    "retrying" if attempt < _MAX_REGENERATE_ATTEMPTS - 1 else "skipping",
                )
                if attempt < _MAX_REGENERATE_ATTEMPTS - 1:
                    continue
                return {"skip": True, "reason": "banned_phrase"}

            return {
                "response": reply_text,
                "confidence": 0.80,
                "reasoning": "v5_overhaul_prompt",
                "style_used": style_hint or "unified",
                "skip": False,
            }

        except Exception as e:
            logger.warning("x_reply_writer: generation error, skipping. %s", e)
            return {"skip": True, "reason": "generation_error"}

    return {"skip": True, "reason": "all_attempts_failed"}
