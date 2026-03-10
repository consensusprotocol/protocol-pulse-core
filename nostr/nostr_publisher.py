"""
nostr_publisher.py — Protocol Pulse content publisher to Nostr.

LAW 5: Every new article → NIP-23 long-form. Every video → NIP-1 short note.
LAW 5: Max 10 posts/day from PP account.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from pynostr.key import PrivateKey
    from pynostr.event import Event, EventKind
    _PYNOSTR_OK = True
except ImportError:
    _PYNOSTR_OK = False
    logger.error("pynostr not installed")

try:
    import websockets
    _WS_OK = True
except ImportError:
    _WS_OK = False

# LAW 5: Max 10 posts/day
MAX_DAILY_POSTS = 10

# Approved relay list (LAW 2)
NOSTR_RELAYS: List[str] = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://relay.primal.net",
]

# In-memory daily post counter (resets at midnight UTC)
_daily_count: dict = {"date": None, "count": 0}


def _check_daily_limit() -> bool:
    """Returns True if under daily post limit. False if at limit."""
    today = date.today().isoformat()
    if _daily_count["date"] != today:
        _daily_count["date"] = today
        _daily_count["count"] = 0
    return _daily_count["count"] < MAX_DAILY_POSTS


def _increment_daily_count():
    today = date.today().isoformat()
    if _daily_count["date"] != today:
        _daily_count["date"] = today
        _daily_count["count"] = 0
    _daily_count["count"] += 1


def _get_private_key() -> Optional[PrivateKey]:
    """Load PP private key from env."""
    if not _PYNOSTR_OK:
        return None
    priv_hex = os.environ.get("NOSTR_PRIVATE_KEY", "")
    if not priv_hex or len(priv_hex) != 64:
        logger.error("NOSTR_PRIVATE_KEY not set or invalid")
        return None
    try:
        return PrivateKey.from_hex(priv_hex)
    except Exception as e:
        logger.error("Failed to load private key: %s", e)
        return None


def _build_and_sign_event(content: str, kind: int, tags: List[List[str]]) -> Optional[dict]:
    """Build, sign, and return a Nostr event dict."""
    if not _PYNOSTR_OK:
        return None
    priv_key = _get_private_key()
    if not priv_key:
        return None

    try:
        event = Event(
            content=content,
            pubkey=priv_key.public_key.hex(),
            created_at=int(time.time()),
            kind=kind,
            tags=tags,
        )
        event.sign(priv_key.hex())
        return event.to_dict()
    except Exception as e:
        logger.error("Event build/sign failed: %s", e)
        return None


async def _publish_to_relay(relay_url: str, event_dict: dict, timeout: int = 10) -> bool:
    """Publish a signed event to a single relay. Returns True on success."""
    if not _WS_OK:
        return False
    try:
        async with websockets.connect(relay_url, open_timeout=timeout, close_timeout=5) as ws:
            msg = json.dumps(["EVENT", event_dict])
            await ws.send(msg)
            # Wait for OK response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                parsed = json.loads(response)
                if isinstance(parsed, list) and len(parsed) >= 3:
                    ok = parsed[0] == "OK" and parsed[2] is True
                    if ok:
                        logger.info("Published to %s: event_id=%s", relay_url, event_dict.get("id", "?")[:12])
                        return True
                    else:
                        logger.warning("Relay %s rejected event: %s", relay_url, parsed)
                        return False
                return True  # treat any response as OK
            except asyncio.TimeoutError:
                logger.warning("No OK response from %s (timeout) — assuming success", relay_url)
                return True
    except Exception as e:
        logger.warning("Failed to publish to %s: %s", relay_url, e)
        return False


async def _publish_to_all_relays(event_dict: dict) -> dict:
    """Publish event to all relays concurrently. Returns {relay: success}."""
    tasks = {relay: _publish_to_relay(relay, event_dict) for relay in NOSTR_RELAYS}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        relay: (r is True) for relay, r in zip(tasks.keys(), results)
    }


def sign_and_publish(content: str, kind: int = 1, tags: List[List[str]] = None) -> dict:
    """
    Sign content and publish to all relays.
    Respects daily post limit (LAW 5).
    Returns {"success": bool, "relays": {relay: bool}, "event_id": str}
    """
    if not _check_daily_limit():
        logger.warning("Daily post limit (%d) reached — skipping publish", MAX_DAILY_POSTS)
        return {"success": False, "error": "daily_limit_reached", "relays": {}}

    if tags is None:
        tags = []

    event_dict = _build_and_sign_event(content, kind, tags)
    if not event_dict:
        return {"success": False, "error": "event_build_failed", "relays": {}}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _publish_to_all_relays(event_dict))
                relay_results = future.result(timeout=30)
        else:
            relay_results = loop.run_until_complete(_publish_to_all_relays(event_dict))
    except Exception as e:
        logger.error("Publish error: %s", e)
        relay_results = {r: False for r in NOSTR_RELAYS}

    success_count = sum(1 for v in relay_results.values() if v)
    if success_count > 0:
        _increment_daily_count()

    return {
        "success": success_count > 0,
        "relays": relay_results,
        "event_id": event_dict.get("id", ""),
        "relays_ok": success_count,
        "relays_total": len(NOSTR_RELAYS),
    }


def publish_article(article_title: str, article_content: str, article_url: str = "") -> dict:
    """
    NIP-23 long-form article note (kind 30023).
    LAW 5: Auto-post every new article to Nostr.
    """
    tags = [
        ["title", article_title],
        ["t", "bitcoin"],
        ["t", "protocolpulse"],
        ["t", "news"],
    ]
    if article_url:
        tags.append(["r", article_url])

    # NIP-23: kind 30023 with d-tag (unique identifier)
    import hashlib
    d_tag = hashlib.sha256(article_title.encode()).hexdigest()[:16]
    tags.append(["d", d_tag])

    # Include URL in content for discoverability
    content = article_content
    if article_url:
        content = f"{article_content}\n\n{article_url}"

    logger.info("Publishing article to Nostr: %s", article_title[:60])
    return sign_and_publish(content=content, kind=30023, tags=tags)


def publish_video(video_title: str, video_url: str) -> dict:
    """
    NIP-1 short note linking to new video.
    LAW 5: Auto-post every daily video to Nostr.
    """
    content = f"New Pulse Check: {video_title}\n\n{video_url}"
    tags = [
        ["t", "bitcoin"],
        ["t", "video"],
        ["t", "protocolpulse"],
        ["r", video_url],
    ]
    logger.info("Publishing video to Nostr: %s", video_title[:60])
    return sign_and_publish(content=content, kind=1, tags=tags)


def get_daily_post_count() -> int:
    """Return current day's post count."""
    today = date.today().isoformat()
    if _daily_count["date"] != today:
        return 0
    return _daily_count["count"]


if __name__ == "__main__":
    # Quick test publish
    result = sign_and_publish(
        content="Protocol Pulse is now live on Nostr. Bitcoin intelligence, censorship-resistant. #bitcoin #nostr",
        kind=1,
        tags=[["t", "bitcoin"], ["t", "nostr"], ["t", "protocolpulse"]],
    )
    print("Publish result:", json.dumps(result, indent=2))
