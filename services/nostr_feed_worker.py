"""
Nostr Feed Worker — Session 8
==============================
Background thread that subscribes to Nostr relays and caches
the last 50 Bitcoin-tagged events for fast initial page loads.

Client-side WebSocket takes over after page load — this is just
for the initial cache burst.

Architecture:
- One thread per relay using websocket-client (synchronous, thread-safe)
- In-memory circular buffer of last 50 events (thread-lock protected)
- Relay health tracking: connected, latency, events/min, last event time
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Default relay list ─────────────────────────────────────────────────────
DEFAULT_RELAYS: List[Dict[str, Any]] = [
    {
        "url": "wss://relay.damus.io",
        "name": "Damus",
        "description": "Largest public relay — most coverage",
        "nips": ["NIP-01", "NIP-02", "NIP-04", "NIP-09", "NIP-11"],
    },
    {
        "url": "wss://nos.lol",
        "name": "nos.lol",
        "description": "Fast, well-maintained public relay",
        "nips": ["NIP-01", "NIP-02", "NIP-09", "NIP-11"],
    },
    {
        "url": "wss://relay.nostr.band",
        "name": "Nostr Band",
        "description": "Aggregation + search relay",
        "nips": ["NIP-01", "NIP-02", "NIP-09", "NIP-11", "NIP-50"],
    },
    {
        "url": "wss://relay.primal.net",
        "name": "Primal",
        "description": "High-performance Nostr relay by Primal",
        "nips": ["NIP-01", "NIP-02", "NIP-09", "NIP-11"],
    },
]

# ── In-memory state (thread-safe) ─────────────────────────────────────────
_lock = threading.Lock()
_events_cache: deque = deque(maxlen=50)   # last 50 events
_relay_status: Dict[str, Dict] = {}       # per-relay health

# Track events per minute per relay
_relay_event_times: Dict[str, deque] = {}  # relay_url → deque of timestamps

# Startup flag
_worker_started = False


def _now_ts() -> float:
    return time.time()


def _init_relay_status(url: str) -> None:
    with _lock:
        if url not in _relay_status:
            _relay_status[url] = {
                "url": url,
                "connected": False,
                "events_session": 0,
                "latency_ms": None,
                "last_event_at": None,
                "events_per_min": 0.0,
                "error": None,
            }
        if url not in _relay_event_times:
            _relay_event_times[url] = deque(maxlen=120)  # 2-minute window


def _record_event(relay_url: str, event: Dict) -> None:
    """Add event to cache and update relay stats."""
    now = _now_ts()
    with _lock:
        # Deduplicate by event id
        event_id = event.get("id", "")
        existing_ids = {e.get("id") for e in _events_cache}
        if event_id and event_id in existing_ids:
            return

        # Enrich event
        event["_relay"] = relay_url
        event["_cached_at"] = now
        _events_cache.appendleft(event)

        # Update relay stats
        if relay_url in _relay_status:
            _relay_status[relay_url]["events_session"] += 1
            _relay_status[relay_url]["last_event_at"] = datetime.utcnow().isoformat()

        # Track event timestamps for events/min calculation
        if relay_url in _relay_event_times:
            _relay_event_times[relay_url].append(now)


def _calc_events_per_min(relay_url: str) -> float:
    """Sliding window events/minute for a relay."""
    cutoff = _now_ts() - 60.0
    with _lock:
        times = _relay_event_times.get(relay_url, deque())
        recent = sum(1 for t in times if t >= cutoff)
    return float(recent)


def _connect_relay(relay_url: str) -> None:
    """Maintain a persistent WebSocket connection to a single relay."""
    try:
        import websocket  # websocket-client
    except ImportError:
        logger.warning("websocket-client not installed — relay worker disabled")
        return

    _init_relay_status(relay_url)
    SUB_ID = "pp_bitcoin_feed"

    while True:
        connect_start = _now_ts()
        ws: Optional[websocket.WebSocket] = None
        try:
            ws = websocket.create_connection(
                relay_url,
                timeout=15,
                enable_multithread=True,
            )
            latency = round((_now_ts() - connect_start) * 1000, 1)

            with _lock:
                _relay_status[relay_url]["connected"] = True
                _relay_status[relay_url]["latency_ms"] = latency
                _relay_status[relay_url]["error"] = None

            logger.info("Nostr relay connected: %s (%.0fms)", relay_url, latency)

            # Subscribe: kind 1 notes with #bitcoin or #btc tag, last 2 hours
            since_ts = int(time.time()) - 7200  # 2 hours back
            req = json.dumps([
                "REQ", SUB_ID,
                {
                    "kinds": [1],
                    "#t": ["bitcoin"],
                    "since": since_ts,
                    "limit": 50,
                }
            ])
            ws.send(req)

            # Also subscribe to #btc tag
            req2 = json.dumps([
                "REQ", SUB_ID + "_btc",
                {
                    "kinds": [1],
                    "#t": ["btc"],
                    "since": since_ts,
                    "limit": 20,
                }
            ])
            ws.send(req2)

            # Read loop
            ws.sock.settimeout(30)
            while True:
                try:
                    raw = ws.recv()
                    if not raw:
                        break
                    msg = json.loads(raw)
                    if not isinstance(msg, list) or len(msg) < 3:
                        continue
                    msg_type = msg[0]
                    if msg_type == "EVENT":
                        event = msg[2]
                        if isinstance(event, dict) and event.get("kind") == 1:
                            _record_event(relay_url, event)
                            _relay_event_times.setdefault(relay_url, deque(maxlen=120)).append(_now_ts())
                    elif msg_type == "EOSE":
                        logger.debug("Nostr EOSE from %s — caught up to now", relay_url)
                    elif msg_type == "NOTICE":
                        logger.debug("Nostr NOTICE from %s: %s", relay_url, msg[1] if len(msg) > 1 else "")

                except Exception as recv_err:
                    logger.debug("Nostr recv error from %s: %s", relay_url, recv_err)
                    break

        except Exception as conn_err:
            logger.warning("Nostr relay %s connection failed: %s", relay_url, conn_err)
            with _lock:
                _relay_status[relay_url]["connected"] = False
                _relay_status[relay_url]["error"] = str(conn_err)[:120]
        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass
            with _lock:
                if relay_url in _relay_status:
                    _relay_status[relay_url]["connected"] = False

        # Reconnect backoff: 30s
        time.sleep(30)


def start_worker() -> None:
    """Launch one daemon thread per relay. Call once on startup."""
    global _worker_started
    if _worker_started:
        return
    _worker_started = True

    for relay in DEFAULT_RELAYS:
        url = relay["url"]
        t = threading.Thread(
            target=_connect_relay,
            args=(url,),
            daemon=True,
            name=f"nostr-relay-{url.split('//')[1].split('/')[0]}",
        )
        t.start()
        logger.info("Nostr relay worker started: %s", url)


def get_cached_events(limit: int = 50) -> List[Dict]:
    """Return cached events sorted by created_at descending."""
    with _lock:
        events = list(_events_cache)

    # Sort by created_at desc (most recent first)
    events.sort(key=lambda e: e.get("created_at", 0), reverse=True)
    return events[:limit]


def get_relay_status() -> List[Dict]:
    """Return current relay health for all tracked relays."""
    result = []
    with _lock:
        statuses = dict(_relay_status)

    for relay in DEFAULT_RELAYS:
        url = relay["url"]
        status = statuses.get(url, {})
        epm = _calc_events_per_min(url)

        result.append({
            "url": url,
            "name": relay["name"],
            "description": relay["description"],
            "nips": relay["nips"],
            "connected": status.get("connected", False),
            "latency_ms": status.get("latency_ms"),
            "events_session": status.get("events_session", 0),
            "events_per_min": round(epm, 1),
            "last_event_at": status.get("last_event_at"),
            "error": status.get("error"),
        })

    return result


def get_stats() -> Dict:
    """Return aggregate stats across all relays."""
    with _lock:
        total_events = len(_events_cache)
        all_events = list(_events_cache)

    connected_count = sum(
        1 for s in _relay_status.values() if s.get("connected")
    )

    # Count unique pubkeys seen
    pubkeys = {e.get("pubkey", "") for e in all_events if e.get("pubkey")}

    # Count hashtags
    tag_counts: Dict[str, int] = {}
    for event in all_events:
        for tag in event.get("tags", []):
            if tag and tag[0] == "t" and len(tag) > 1:
                t_val = tag[1].lower()
                if t_val not in ("bitcoin", "btc"):  # exclude primary filter tags
                    tag_counts[t_val] = tag_counts.get(t_val, 0) + 1

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "events_cached": total_events,
        "relays_connected": connected_count,
        "relays_total": len(DEFAULT_RELAYS),
        "unique_pubkeys": len(pubkeys),
        "top_hashtags": [{"tag": t, "count": c} for t, c in top_tags],
        "worker_started": _worker_started,
    }
