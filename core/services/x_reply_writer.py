"""
Sovereign Sentry reply writer.

Uses the Sovereign Sentry V4 persona prompt to generate JSON replies
for monitored tweets using the shared AIService abstraction.
"""

import json
import logging
from typing import Dict, Any

from .ai_service import AIService
from models import SentimentSnapshot
from ..config.response_prompt import SOVEREIGN_SENTRY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _get_latest_sentiment() -> Dict[str, Any]:
    """Return latest SentimentSnapshot as a simple dict; safe if table empty."""
    try:
        snap = (
            SentimentSnapshot.query.order_by(SentimentSnapshot.computed_at.desc()).first()
        )
        if not snap:
            return {}
        return {
            "score": snap.score,
            "state": snap.state,
            "label": snap.state_label,
            "velocity": snap.velocity,
        }
    except Exception as e:  # pragma: no cover
        logger.debug("x_reply_writer: sentiment lookup failed: %s", e)
        return {}


def generate_reply(
    tweet_text: str,
    author_handle: str,
    author_name: str | None = None,
    style_hint: str | None = None,
) -> Dict[str, Any]:
    """
    Generate a Sovereign Sentry reply JSON for a tweet.

    Returns a dict with keys:
    - response (str)
    - confidence (float)
    - reasoning (str)
    - style_used (str)
    - skip (bool)
    - reason (optional, when skip is true)
    """
    ai = AIService()
    sentiment = _get_latest_sentiment()

    # Build user prompt; system prompt already encodes rules + JSON schema.
    payload = {
        "tweet": tweet_text,
        "author_handle": author_handle,
        "author_name": author_name,
        "style_hint": style_hint,
        "sentiment_snapshot": sentiment,
    }

    prompt = (
        "You are generating a single reply to the following X post.\n"
        "Input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
        "Follow the system instructions exactly and return ONLY valid JSON."
    )

    try:
        # Prefer OpenAI structured JSON; fall back to Anthropic/plain text if needed.
        result = ai.generate_structured_content(
            prompt=prompt,
            system_prompt=SOVEREIGN_SENTRY_SYSTEM_PROMPT,
            provider="openai",
        )

        # generate_structured_content may return dict or string; normalize.
        if isinstance(result, dict):
            data = result
        else:
            # Try to parse as JSON; if that fails, skip.
            try:
                data = json.loads(str(result))
            except Exception:
                logger.warning("x_reply_writer: non-JSON response, skipping.")
                return {"skip": True, "reason": "non_json_response"}

        # Ensure core keys
        if data.get("skip") is True:
            return {
                "skip": True,
                "reason": data.get("reason", "model_chose_skip"),
            }

        response_text = (data.get("response") or "").strip()
        if not response_text:
            return {"skip": True, "reason": "empty_response"}

        # Sovereign Sentry constraints: lowercase, no emojis, short.
        response_text = response_text.lower()
        if len(response_text) > 280:
            response_text = response_text[:277] + "..."

        return {
            "response": response_text,
            "confidence": float(data.get("confidence", 0.5)),
            "reasoning": data.get("reasoning", ""),
            "style_used": data.get("style_used", style_hint or ""),
            "skip": False,
        }

    except Exception as e:  # pragma: no cover
        logger.warning("x_reply_writer: generation error, skipping. %s", e)
        return {"skip": True, "reason": "generation_error"}

"""
Sovereign Sentry reply writer.

Uses the Sovereign Sentry V4 persona prompt to generate JSON replies
for monitored tweets using the shared AIService abstraction.
"""

import json
import logging
from typing import Dict, Any

from .ai_service import AIService
from models import SentimentSnapshot
from config.response_prompt import SOVEREIGN_SENTRY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _get_latest_sentiment() -> Dict[str, Any]:
    """Return latest SentimentSnapshot as a simple dict; safe if table empty."""
    try:
        snap = (
            SentimentSnapshot.query.order_by(SentimentSnapshot.computed_at.desc()).first()
        )
        if not snap:
            return {}
        return {
            "score": snap.score,
            "state": snap.state,
            "label": snap.state_label,
            "velocity": snap.velocity,
        }
    except Exception as e:  # pragma: no cover
        logger.debug("x_reply_writer: sentiment lookup failed: %s", e)
        return {}


def generate_reply(
    tweet_text: str,
    author_handle: str,
    author_name: str | None = None,
    style_hint: str | None = None,
) -> Dict[str, Any]:
    """
    Generate a Sovereign Sentry reply JSON for a tweet.

    Returns a dict with keys:
    - response (str)
    - confidence (float)
    - reasoning (str)
    - style_used (str)
    - skip (bool)
    - reason (optional, when skip is true)
    """
    ai = AIService()
    sentiment = _get_latest_sentiment()

    # Build user prompt; system prompt already encodes rules + JSON schema.
    payload = {
        "tweet": tweet_text,
        "author_handle": author_handle,
        "author_name": author_name,
        "style_hint": style_hint,
        "sentiment_snapshot": sentiment,
    }

    prompt = (
        "You are generating a single reply to the following X post.\n"
        "Input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
        "Follow the system instructions exactly and return ONLY valid JSON."
    )

    try:
        # Prefer OpenAI structured JSON; fall back to Anthropic/plain text if needed.
        result = ai.generate_structured_content(
            prompt=prompt,
            system_prompt=SOVEREIGN_SENTRY_SYSTEM_PROMPT,
            provider="openai",
        )

        # generate_structured_content may return dict or string; normalize.
        if isinstance(result, dict):
            data = result
        else:
            # Try to parse as JSON; if that fails, skip.
            try:
                data = json.loads(str(result))
            except Exception:
                logger.warning("x_reply_writer: non-JSON response, skipping.")
                return {"skip": True, "reason": "non_json_response"}

        # Ensure core keys
        if data.get("skip") is True:
            return {
                "skip": True,
                "reason": data.get("reason", "model_chose_skip"),
            }

        response_text = (data.get("response") or "").strip()
        if not response_text:
            return {"skip": True, "reason": "empty_response"}

        # Sovereign Sentry constraints: lowercase, no emojis, short.
        response_text = response_text.lower()
        if len(response_text) > 280:
            response_text = response_text[:277] + "..."

        return {
            "response": response_text,
            "confidence": float(data.get("confidence", 0.5)),
            "reasoning": data.get("reasoning", ""),
            "style_used": data.get("style_used", style_hint or ""),
            "skip": False,
        }

    except Exception as e:  # pragma: no cover
        logger.warning("x_reply_writer: generation error, skipping. %s", e)
        return {"skip": True, "reason": "generation_error"}

