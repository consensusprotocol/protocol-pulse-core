"""
Webhook Manager - Integration Layer for Protocol Pulse
=======================================================
Manages outbound webhook delivery to Discord, Telegram, Slack,
and generic (Zapier-compatible) endpoints.

FEATURES:
- Fire events to all registered webhook endpoints
- Platform-specific formatting (Discord embeds, Telegram HTML, Slack blocks)
- Exponential-backoff retry (up to 3 attempts)
- Delivery logging to data/webhook_deliveries.jsonl
- Thread-safe registration and delivery

SUPPORTED EVENTS:
- article.published
- article.updated
- breaking_news
- price_alert
- whale_alert
- daily_summary
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DATA_DIR = BASE_DIR / "data"
WEBHOOKS_FILE = DATA_DIR / "webhooks.json"
DELIVERIES_FILE = DATA_DIR / "webhook_deliveries.jsonl"

VALID_EVENTS = {
    "article.published",
    "article.updated",
    "breaking_news",
    "price_alert",
    "whale_alert",
    "daily_summary",
}

VALID_PLATFORMS = {"discord", "telegram", "slack", "generic"}

REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
BACKOFF_BASE = 2  # exponential backoff base in seconds

# Thread lock for file I/O safety
_file_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_webhooks() -> List[Dict[str, Any]]:
    """Load registered webhooks from data/webhooks.json (thread-safe)."""
    with _file_lock:
        if not WEBHOOKS_FILE.exists():
            return []
        try:
            raw = WEBHOOKS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            return []
        except Exception as exc:
            logger.error("Failed to load webhooks file: %s", exc)
            return []


def _save_webhooks(webhooks: List[Dict[str, Any]]) -> None:
    """Persist webhooks list to data/webhooks.json (thread-safe)."""
    with _file_lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        WEBHOOKS_FILE.write_text(
            json.dumps(webhooks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _append_delivery_log(entry: Dict[str, Any]) -> None:
    """Append a delivery record to data/webhook_deliveries.jsonl."""
    with _file_lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DELIVERIES_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def _send_with_retries(
    url: str,
    json_body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    POST *json_body* to *url* with up to MAX_RETRIES attempts.

    Returns dict with keys: success, status_code, response_time_ms, error, attempts.
    """
    if headers is None:
        headers = {"Content-Type": "application/json"}

    last_error: Optional[str] = None
    for attempt in range(1, MAX_RETRIES + 1):
        start = time.monotonic()
        try:
            resp = requests.post(
                url,
                json=json_body,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)

            if resp.status_code < 300:
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "response_time_ms": elapsed_ms,
                    "error": None,
                    "attempts": attempt,
                }

            # Rate-limited -- honour Retry-After if present
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", BACKOFF_BASE ** attempt))
                last_error = f"Rate limited (429). Retry-After {retry_after}s"
                logger.warning("Webhook %s rate-limited, waiting %.1fs", url, retry_after)
                time.sleep(retry_after)
                continue

            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"

        except requests.exceptions.Timeout:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            last_error = f"Timeout after {REQUEST_TIMEOUT}s"
        except requests.exceptions.ConnectionError as exc:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            last_error = f"Connection error: {exc}"
        except requests.exceptions.RequestException as exc:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            last_error = f"Request error: {exc}"

        if attempt < MAX_RETRIES:
            backoff = BACKOFF_BASE ** attempt
            logger.info(
                "Webhook delivery attempt %d/%d failed for %s, retrying in %ds: %s",
                attempt, MAX_RETRIES, url, backoff, last_error,
            )
            time.sleep(backoff)

    return {
        "success": False,
        "status_code": 0,
        "response_time_ms": 0,
        "error": last_error,
        "attempts": MAX_RETRIES,
    }


# ---------------------------------------------------------------------------
# Platform formatters
# ---------------------------------------------------------------------------

# Colour constants for Discord embeds
_COLOR_GREEN = 0x00C853   # positive / informational
_COLOR_RED = 0xFF1744     # alerts / breaking
_COLOR_ORANGE = 0xFF9100  # warnings
_COLOR_BLUE = 0x2979FF    # neutral updates

_EVENT_COLORS = {
    "article.published": _COLOR_BLUE,
    "article.updated": _COLOR_BLUE,
    "breaking_news": _COLOR_RED,
    "price_alert": _COLOR_ORANGE,
    "whale_alert": _COLOR_RED,
    "daily_summary": _COLOR_GREEN,
}

_EVENT_LABELS = {
    "article.published": "New Article Published",
    "article.updated": "Article Updated",
    "breaking_news": "BREAKING NEWS",
    "price_alert": "Price Alert",
    "whale_alert": "Whale Alert",
    "daily_summary": "Daily Intelligence Summary",
}


def format_discord_embed(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Discord webhook payload with a rich embed.

    Returns a dict suitable for POSTing to a Discord webhook URL:
    ``{"embeds": [<embed>]}``.
    """
    title = payload.get("title") or _EVENT_LABELS.get(event_name, event_name)
    description = payload.get("description") or payload.get("summary", "")
    url = payload.get("url", "")
    color = _EVENT_COLORS.get(event_name, _COLOR_BLUE)

    # If the payload hints at a negative / alert sentiment, use red
    if payload.get("alert") or payload.get("severity") == "high":
        color = _COLOR_RED
    elif payload.get("positive"):
        color = _COLOR_GREEN

    embed: Dict[str, Any] = {
        "title": title[:256],
        "description": description[:4096],
        "color": color,
        "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "footer": {
            "text": "Protocol Pulse -- Bitcoin Intelligence",
        },
    }

    if url:
        embed["url"] = url

    # Build fields from common payload keys
    fields: List[Dict[str, Any]] = []

    if payload.get("author"):
        fields.append({"name": "Author", "value": str(payload["author"]), "inline": True})

    if payload.get("category"):
        fields.append({"name": "Category", "value": str(payload["category"]), "inline": True})

    if payload.get("price"):
        fields.append({"name": "Price", "value": str(payload["price"]), "inline": True})

    if payload.get("change"):
        fields.append({"name": "Change", "value": str(payload["change"]), "inline": True})

    if payload.get("btc_amount"):
        fields.append({"name": "BTC Amount", "value": str(payload["btc_amount"]), "inline": True})

    if payload.get("from_wallet"):
        fields.append({"name": "From", "value": str(payload["from_wallet"])[:100], "inline": True})

    if payload.get("to_wallet"):
        fields.append({"name": "To", "value": str(payload["to_wallet"])[:100], "inline": True})

    if payload.get("txid"):
        fields.append({"name": "TX ID", "value": str(payload["txid"])[:64], "inline": False})

    # Extra arbitrary fields supplied by caller
    for extra in payload.get("fields", []):
        if isinstance(extra, dict) and "name" in extra and "value" in extra:
            fields.append({
                "name": str(extra["name"])[:256],
                "value": str(extra["value"])[:1024],
                "inline": extra.get("inline", True),
            })

    if fields:
        embed["fields"] = fields[:25]  # Discord limit

    if payload.get("image_url"):
        embed["image"] = {"url": payload["image_url"]}

    if payload.get("thumbnail_url"):
        embed["thumbnail"] = {"url": payload["thumbnail_url"]}

    return {"embeds": [embed]}


def format_telegram_message(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Telegram Bot API ``sendMessage`` compatible payload.

    Returns dict with ``chat_id``, ``text`` (HTML), and ``parse_mode``.
    The caller must inject the correct ``chat_id`` before sending if it
    is not already present in the payload.
    """
    label = _EVENT_LABELS.get(event_name, event_name)
    title = payload.get("title") or label
    description = payload.get("description") or payload.get("summary", "")
    url = payload.get("url", "")

    lines: List[str] = [
        f"<b>{_html_escape(label)}</b>",
        "",
    ]

    if title and title != label:
        if url:
            lines.append(f'<a href="{_html_escape(url)}">{_html_escape(title)}</a>')
        else:
            lines.append(f"<b>{_html_escape(title)}</b>")
        lines.append("")

    if description:
        lines.append(_html_escape(description))
        lines.append("")

    # Key-value details
    detail_keys = [
        ("author", "Author"),
        ("category", "Category"),
        ("price", "Price"),
        ("change", "Change"),
        ("btc_amount", "BTC Amount"),
        ("from_wallet", "From"),
        ("to_wallet", "To"),
        ("txid", "TX ID"),
    ]
    for key, display in detail_keys:
        if payload.get(key):
            lines.append(f"<b>{display}:</b> <code>{_html_escape(str(payload[key]))}</code>")

    lines.append("")
    lines.append("<i>Protocol Pulse -- Bitcoin Intelligence</i>")

    text = "\n".join(lines).strip()

    message: Dict[str, Any] = {
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": not bool(url),
    }

    if payload.get("chat_id"):
        message["chat_id"] = payload["chat_id"]

    return message


def format_slack_blocks(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Slack Block Kit payload.

    Returns dict with ``blocks`` list ready for Slack incoming webhooks.
    """
    label = _EVENT_LABELS.get(event_name, event_name)
    title = payload.get("title") or label
    description = payload.get("description") or payload.get("summary", "")
    url = payload.get("url", "")

    blocks: List[Dict[str, Any]] = []

    # Header section
    header_text = f"*{label}*"
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": label[:150]},
    })

    # Title + description section
    body_parts: List[str] = []
    if title and title != label:
        if url:
            body_parts.append(f"<{url}|*{title}*>")
        else:
            body_parts.append(f"*{title}*")
    if description:
        body_parts.append(description[:3000])

    if body_parts:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(body_parts)},
        })

    # Fields section for metadata
    field_entries: List[Dict[str, Any]] = []
    slack_field_keys = [
        ("author", "Author"),
        ("category", "Category"),
        ("price", "Price"),
        ("change", "Change"),
        ("btc_amount", "BTC Amount"),
        ("from_wallet", "From"),
        ("to_wallet", "To"),
    ]
    for key, display in slack_field_keys:
        if payload.get(key):
            field_entries.append({
                "type": "mrkdwn",
                "text": f"*{display}:*\n{payload[key]}",
            })

    if field_entries:
        # Slack allows max 10 fields per section
        blocks.append({
            "type": "section",
            "fields": field_entries[:10],
        })

    if payload.get("txid"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*TX ID:*\n`{payload['txid']}`"},
        })

    # Divider
    blocks.append({"type": "divider"})

    # Context / footer
    timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Protocol Pulse -- Bitcoin Intelligence | {timestamp}"},
        ],
    })

    return {"blocks": blocks}


def _format_generic(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Zapier-compatible generic JSON payload.

    Wraps the original payload with event metadata so downstream
    automation tools can route on ``event`` and ``timestamp``.
    """
    return {
        "event": event_name,
        "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }


def _html_escape(text: str) -> str:
    """Minimal HTML escape for Telegram messages."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fire_event(
    event_name: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Fire a webhook event to all registered endpoints subscribed to *event_name*.

    Parameters
    ----------
    event_name : str
        One of the VALID_EVENTS constants.
    payload : dict
        Arbitrary event data. Common keys: title, description, url,
        price, change, btc_amount, txid, etc.

    Returns
    -------
    dict
        ``{delivered: int, failed: int, errors: []}``
    """
    if event_name not in VALID_EVENTS:
        logger.warning("Unknown event name '%s'; proceeding anyway.", event_name)

    webhooks = _load_webhooks()
    targets = [
        wh for wh in webhooks
        if event_name in wh.get("events", []) and wh.get("active", True)
    ]

    if not targets:
        logger.debug("No webhooks registered for event '%s'.", event_name)
        return {"delivered": 0, "failed": 0, "errors": []}

    delivered = 0
    failed = 0
    errors: List[str] = []

    for wh in targets:
        url = wh.get("url", "")
        platform = wh.get("platform", "generic")
        wh_id = wh.get("id", "unknown")

        if not _is_valid_url(url):
            error_msg = f"Webhook {wh_id}: invalid URL '{url}'"
            logger.error(error_msg)
            errors.append(error_msg)
            failed += 1
            continue

        # Format payload for the target platform
        if platform == "discord":
            body = format_discord_embed(event_name, payload)
        elif platform == "telegram":
            body = format_telegram_message(event_name, payload)
        elif platform == "slack":
            body = format_slack_blocks(event_name, payload)
        else:
            body = _format_generic(event_name, payload)

        result = _send_with_retries(url, body)

        # Log delivery
        log_entry = {
            "id": str(uuid.uuid4()),
            "webhook_id": wh_id,
            "webhook_name": wh.get("name", ""),
            "event": event_name,
            "platform": platform,
            "url": url,
            "success": result["success"],
            "status_code": result["status_code"],
            "response_time_ms": result["response_time_ms"],
            "attempts": result["attempts"],
            "error": result["error"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_delivery_log(log_entry)

        if result["success"]:
            delivered += 1
            logger.info(
                "Webhook %s (%s) delivered for '%s' in %.0fms",
                wh_id, platform, event_name, result["response_time_ms"],
            )
        else:
            failed += 1
            error_msg = f"Webhook {wh_id} ({platform}): {result['error']}"
            errors.append(error_msg)
            logger.error("Webhook delivery failed: %s", error_msg)

    return {"delivered": delivered, "failed": failed, "errors": errors}


def test_webhook(
    url: str,
    platform: str = "generic",
) -> Dict[str, Any]:
    """
    Send a test payload to *url* to verify connectivity.

    Returns
    -------
    dict
        ``{success: bool, status_code: int, response_time_ms: float, error: str|None}``
    """
    if not _is_valid_url(url):
        return {
            "success": False,
            "status_code": 0,
            "response_time_ms": 0,
            "error": f"Invalid URL: {url}",
        }

    test_payload: Dict[str, Any] = {
        "title": "Protocol Pulse Webhook Test",
        "description": "This is a test event to verify your webhook integration is working.",
        "url": "https://protocolpulse.ai",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    event_name = "article.published"

    if platform == "discord":
        body = format_discord_embed(event_name, test_payload)
    elif platform == "telegram":
        body = format_telegram_message(event_name, test_payload)
    elif platform == "slack":
        body = format_slack_blocks(event_name, test_payload)
    else:
        body = _format_generic(event_name, test_payload)

    start = time.monotonic()
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        success = resp.status_code < 300
        return {
            "success": success,
            "status_code": resp.status_code,
            "response_time_ms": elapsed_ms,
            "error": None if success else f"HTTP {resp.status_code}: {resp.text[:200]}",
        }
    except requests.exceptions.Timeout:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "success": False,
            "status_code": 0,
            "response_time_ms": elapsed_ms,
            "error": f"Timeout after {REQUEST_TIMEOUT}s",
        }
    except requests.exceptions.ConnectionError as exc:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "success": False,
            "status_code": 0,
            "response_time_ms": elapsed_ms,
            "error": f"Connection error: {exc}",
        }
    except requests.exceptions.RequestException as exc:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "success": False,
            "status_code": 0,
            "response_time_ms": elapsed_ms,
            "error": f"Request error: {exc}",
        }


def register_webhook(
    url: str,
    platform: str,
    events: List[str],
    name: str = "",
) -> Dict[str, Any]:
    """
    Register a new webhook endpoint.

    Parameters
    ----------
    url : str
        The endpoint URL to receive POST payloads.
    platform : str
        One of: discord, telegram, slack, generic.
    events : list[str]
        Event names this webhook should receive.
    name : str, optional
        Human-friendly label for the webhook.

    Returns
    -------
    dict
        The saved webhook configuration.
    """
    if not _is_valid_url(url):
        raise ValueError(f"Invalid URL: {url}")

    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"Invalid platform '{platform}'. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}"
        )

    invalid_events = [e for e in events if e not in VALID_EVENTS]
    if invalid_events:
        raise ValueError(
            f"Invalid event(s): {', '.join(invalid_events)}. "
            f"Valid events: {', '.join(sorted(VALID_EVENTS))}"
        )

    webhooks = _load_webhooks()

    # Prevent duplicate URL + platform registrations
    for wh in webhooks:
        if wh.get("url") == url and wh.get("platform") == platform:
            # Update existing registration
            wh["events"] = list(set(events))
            wh["name"] = name or wh.get("name", "")
            wh["updated_at"] = datetime.now(timezone.utc).isoformat()
            wh["active"] = True
            _save_webhooks(webhooks)
            logger.info("Updated existing webhook %s for %s", wh["id"], platform)
            return wh

    webhook_config: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "url": url,
        "platform": platform,
        "events": list(set(events)),
        "name": name,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    webhooks.append(webhook_config)
    _save_webhooks(webhooks)
    logger.info("Registered new webhook %s (%s) for events: %s", webhook_config["id"], platform, events)
    return webhook_config
