"""
nostr_monitor.py — Asyncio relay monitor for Protocol Pulse.

Connects to 4 Nostr relays concurrently, subscribes to Bitcoin topics,
scores events by engagement, deduplicates by event ID, and flushes to DB.

LAW 4: Runs as asyncio — NOT threads.
LAW 2: 4 relays, exponential backoff (1s→2s→4s→max 60s) on disconnect.
LAW 3: Subscribes to kinds [1, 30023] with bitcoin hashtag filters.
"""
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

# Allow running standalone or as module
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    print("ERROR: websockets not installed — run: pip install websockets")
    sys.exit(1)

logger = logging.getLogger("nostr_monitor")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [nostr_monitor] %(levelname)s %(message)s",
)

# ── LAW 2: Approved relay list ──────────────────────────────────────────────
NOSTR_RELAYS: List[str] = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://relay.primal.net",
]

# ── LAW 3: Subscription filter ──────────────────────────────────────────────
SUBSCRIPTION_FILTER: Dict = {
    "kinds": [1, 30023],
    "#t": ["bitcoin", "btc", "lightning", "nostr", "sovereignty"],
    "limit": 50,
}

# ── LAW 1: Scoring formula ───────────────────────────────────────────────────
def score_event(zaps: int = 0, quotes: int = 0, reposts: int = 0,
                replies: int = 0, reactions: int = 0) -> float:
    return (zaps * 10 + quotes * 5 + reposts * 3 + replies * 2 + reactions * 1)


# ── Bitcoin relevance scoring ────────────────────────────────────────────────
BITCOIN_KEYWORDS = {
    "bitcoin": 0.4, "btc": 0.3, "satoshi": 0.3, "lightning": 0.25,
    "sovereignty": 0.2, "hodl": 0.15, "sats": 0.2, "blockchain": 0.1,
    "nostr": 0.1, "zap": 0.15, "self-custody": 0.2, "multisig": 0.2,
    "halving": 0.25, "mempool": 0.2, "taproot": 0.2, "ordinals": 0.15,
}

def compute_bitcoin_relevance(content: str) -> float:
    """Score 0-1 for how bitcoin-relevant the content is."""
    content_lower = content.lower()
    score = 0.0
    for kw, weight in BITCOIN_KEYWORDS.items():
        if kw in content_lower:
            score += weight
    return min(score, 1.0)


# ── Content moderation ────────────────────────────────────────────────────────
BLOCK_PATTERNS = [
    "porn", "xxx", "nude", "onlyfans", "casino", "gambling",
    "free money", "guaranteed profit", "100x",
]

def is_content_acceptable(content: str) -> bool:
    """Basic content moderation — block obvious spam/adult content."""
    lower = content.lower()
    return not any(p in lower for p in BLOCK_PATTERNS)


def extract_entities(event: Dict) -> Dict:
    """Extract bitcoin keywords and mentioned npubs from event."""
    content = event.get("content", "")
    tags = event.get("tags", [])
    npubs_mentioned = [t[1] for t in tags if len(t) >= 2 and t[0] == "p"]
    bitcoin_kws = [kw for kw in BITCOIN_KEYWORDS if kw in content.lower()]
    return {"bitcoin_keywords": bitcoin_kws, "npubs_mentioned": npubs_mentioned}


def validate_event(event: Dict) -> bool:
    """NIP-01 structural validation."""
    required = ("id", "pubkey", "kind", "content", "created_at")
    return all(k in event for k in required)


# ── Global state ─────────────────────────────────────────────────────────────
_seen_ids: Set[str] = set()
_event_queue: List[Dict] = []
_relay_status: Dict[str, Dict] = {
    relay: {"connected": False, "last_event_at": None, "events_today": 0}
    for relay in NOSTR_RELAYS
}
_MAX_QUEUE = 1000
_FLUSH_INTERVAL = 60  # seconds
_STATUS_FILE = Path(__file__).resolve().parent.parent / "state" / "nostr_relay_status.json"


def _write_relay_status():
    """Persist relay status to JSON file for Flask process to read."""
    try:
        _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "relay": relay,
                "connected": _relay_status[relay]["connected"],
                "last_event_at": _relay_status[relay]["last_event_at"],
                "events_today": _relay_status[relay]["events_today"],
            }
            for relay in NOSTR_RELAYS
        ]
        tmp = _STATUS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(_STATUS_FILE)  # atomic replace
    except Exception as e:
        logger.debug("Could not write relay status file: %s", e)


def get_relay_status() -> List[Dict]:
    """Return relay connection status for API endpoint (in-process use)."""
    return [
        {
            "relay": relay,
            "connected": _relay_status[relay]["connected"],
            "last_event_at": _relay_status[relay]["last_event_at"],
            "events_today": _relay_status[relay]["events_today"],
        }
        for relay in NOSTR_RELAYS
    ]


# ── DB flush ─────────────────────────────────────────────────────────────────
def _flush_to_db(events: List[Dict]) -> int:
    """Write queued events to database. Returns number written."""
    if not events:
        return 0
    try:
        # Dynamic import to work standalone and in Flask context
        from core.app import app, db
        import core.models as models

        saved = 0
        with app.app_context():
            for ev in events:
                try:
                    # Check for existing event
                    existing = db.session.execute(
                        db.select(models.NostrMonitorEvent).where(
                            models.NostrMonitorEvent.event_id == ev["event_id"]
                        )
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    record = models.NostrMonitorEvent(
                        event_id=ev["event_id"],
                        pubkey=ev["pubkey"],
                        kind=ev["kind"],
                        content=ev["content"][:4000],  # cap at 4KB
                        engagement_score=ev.get("engagement_score", 0.0),
                        zaps=ev.get("zaps", 0),
                        quotes=ev.get("quotes", 0),
                        reposts=ev.get("reposts", 0),
                        replies=ev.get("replies", 0),
                        reactions=ev.get("reactions", 0),
                        bitcoin_relevance=ev.get("bitcoin_relevance", 0.0),
                        relay_source=ev.get("relay_source", ""),
                        created_at=ev.get("created_at", int(time.time())),
                    )
                    db.session.add(record)
                    saved += 1
                except Exception as e:
                    logger.warning("Error inserting event %s: %s", ev.get("event_id", "?"), e)
                    db.session.rollback()
            try:
                db.session.commit()
            except Exception as e:
                logger.error("DB commit failed: %s", e)
                db.session.rollback()
        return saved
    except Exception as e:
        logger.error("DB flush error: %s", e)
        return 0


async def _flush_loop():
    """Background coroutine: flush event queue to DB every 60s."""
    global _event_queue
    while True:
        await asyncio.sleep(_FLUSH_INTERVAL)
        if _event_queue:
            batch = _event_queue[:_MAX_QUEUE]
            _event_queue = _event_queue[_MAX_QUEUE:]
            saved = await asyncio.get_event_loop().run_in_executor(None, _flush_to_db, batch)
            logger.info("Flushed %d events to DB (saved %d new)", len(batch), saved)


# ── Per-relay coroutine ───────────────────────────────────────────────────────
async def _connect_relay(relay_url: str):
    """
    Maintain a persistent WebSocket connection to one relay.
    Reconnects with exponential backoff on any error.
    LAW 2: Never crashes on disconnect.
    """
    backoff = 1
    sub_id = f"pp_{relay_url.split('/')[-1].replace('.', '_')}"

    while True:
        try:
            logger.info("Connecting to %s ...", relay_url)
            async with websockets.connect(
                relay_url,
                open_timeout=15,
                close_timeout=10,
                ping_interval=30,
                ping_timeout=20,
                max_size=2 ** 20,  # 1MB max message
            ) as ws:
                _relay_status[relay_url]["connected"] = True
                _write_relay_status()
                backoff = 1  # reset backoff on successful connect
                logger.info("Connected to %s", relay_url)

                # Send subscription request
                req = json.dumps(["REQ", sub_id, SUBSCRIPTION_FILTER])
                await ws.send(req)
                logger.info("Subscribed on %s (sub_id=%s)", relay_url, sub_id)

                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(msg, list) or len(msg) < 2:
                        continue

                    msg_type = msg[0]

                    if msg_type == "EVENT" and len(msg) >= 3:
                        event = msg[2]
                        _process_event(event, relay_url)
                    elif msg_type == "EOSE":
                        logger.debug("EOSE from %s — live subscription active", relay_url)
                    elif msg_type == "NOTICE":
                        logger.debug("NOTICE from %s: %s", relay_url, msg[1] if len(msg) > 1 else "")

        except (ConnectionClosed, WebSocketException) as e:
            logger.warning("WebSocket closed for %s: %s", relay_url, e)
        except asyncio.TimeoutError:
            logger.warning("Timeout connecting to %s", relay_url)
        except Exception as e:
            logger.error("Error on %s: %s", relay_url, e)
        finally:
            _relay_status[relay_url]["connected"] = False
            _write_relay_status()

        logger.info("Reconnecting %s in %ds ...", relay_url, backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)  # exponential backoff, max 60s


_EVENT_ID_RE = re.compile(r'^[0-9a-f]{64}$')

def _process_event(event: Dict, relay_url: str):
    """Validate, deduplicate, score, and enqueue an event."""
    global _event_queue, _seen_ids

    if not validate_event(event):
        return

    event_id = event.get("id", "")
    # G3: Validate event_id is exactly 64 hex chars before storage
    if not event_id or not _EVENT_ID_RE.match(event_id):
        logger.debug("Dropping event with invalid id format: %s", str(event_id)[:20])
        return
    if event_id in _seen_ids:
        return
    _seen_ids.add(event_id)

    # Bound dedup cache to prevent memory leak
    if len(_seen_ids) > 50000:
        # Remove oldest half (set has no ordering, just trim)
        to_remove = list(_seen_ids)[:25000]
        for eid in to_remove:
            _seen_ids.discard(eid)

    content = event.get("content", "")
    if not is_content_acceptable(content):
        return

    bitcoin_relevance = compute_bitcoin_relevance(content)
    # Drop low-relevance content (< 0.05) to keep DB clean
    if bitcoin_relevance < 0.05:
        return

    tags = event.get("tags", [])
    # Count engagement from tags (NIP-25 reactions, NIP-18 reposts)
    reactions = sum(1 for t in tags if t and t[0] == "e")
    zaps = int(event.get("zaps", 0))
    quotes = int(event.get("quotes", 0))
    reposts = int(event.get("reposts", 0))
    replies = int(event.get("replies", 0))

    eng_score = score_event(zaps, quotes, reposts, replies, reactions)

    _relay_status[relay_url]["last_event_at"] = datetime.now(timezone.utc).isoformat()
    _relay_status[relay_url]["events_today"] = _relay_status[relay_url].get("events_today", 0) + 1

    if len(_event_queue) < _MAX_QUEUE:
        _event_queue.append({
            "event_id": event_id,
            "pubkey": event.get("pubkey", ""),
            "kind": event.get("kind", 1),
            "content": content,
            "engagement_score": eng_score,
            "zaps": zaps,
            "quotes": quotes,
            "reposts": reposts,
            "replies": replies,
            "reactions": reactions,
            "bitcoin_relevance": bitcoin_relevance,
            "relay_source": relay_url,
            "created_at": event.get("created_at", int(time.time())),
        })


# ── Main entry point ──────────────────────────────────────────────────────────
async def run_monitor():
    """Start all relay connections + flush loop concurrently."""
    logger.info("Starting Nostr Monitor — Protocol Pulse")
    logger.info("Relays: %s", NOSTR_RELAYS)

    tasks = [asyncio.create_task(_connect_relay(r)) for r in NOSTR_RELAYS]
    tasks.append(asyncio.create_task(_flush_loop()))

    logger.info("Monitor running — %d relays + flush loop", len(NOSTR_RELAYS))
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(run_monitor())
    except KeyboardInterrupt:
        logger.info("Nostr Monitor stopped by user.")
