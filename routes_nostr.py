"""
SESSION 8 — NOSTR FEED BLUEPRINT
==================================
Routes:
  GET  /nostr                  — main page (SSR with cached events)
  GET  /api/nostr/relays       — relay list with metadata
  GET  /api/nostr/cache        — last 50 cached Bitcoin events
  POST /api/nostr/relay/add    — validate and register a custom relay
  GET  /api/nostr/stats        — aggregate stats (pubkeys, tags, events)

Architecture:
  Browser connects DIRECTLY to Nostr relays via WebSocket (client-side).
  Server provides relay config + initial event cache for fast first paint.
  Background worker (nostr_feed_worker) pre-fetches events at startup.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Blueprint, jsonify, render_template, request

logger = logging.getLogger(__name__)

nostr_bp = Blueprint("nostr", __name__)

# ── Lazy-start the background worker (once per process) ───────────────────
_worker_launched = False


def _ensure_worker() -> None:
    global _worker_launched
    if _worker_launched:
        return
    _worker_launched = True
    try:
        from services.nostr_feed_worker import start_worker
        start_worker()
        logger.info("Nostr feed worker launched")
    except Exception as exc:
        logger.warning("Nostr feed worker failed to start: %s", exc)


# ── Helpers ────────────────────────────────────────────────────────────────

def _serialise_event(event: Dict) -> Dict:
    """Strip internal fields and format for JSON output."""
    pubkey = event.get("pubkey", "")
    pub_short = pubkey[:8] + "…" + pubkey[-4:] if len(pubkey) > 12 else pubkey

    created_at = event.get("created_at", 0)
    try:
        dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
        time_str = dt.strftime("%H:%M UTC")
        date_str = dt.strftime("%Y-%m-%d")
        iso_str = dt.isoformat()
    except Exception:
        time_str = date_str = iso_str = ""

    content = event.get("content", "")

    # Extract referenced tags
    tags = event.get("tags", [])
    hashtags = [
        t[1].lower()
        for t in tags
        if isinstance(t, list) and t and t[0] == "t" and len(t) > 1
    ]

    # Build Nostr client links
    event_id = event.get("id", "")
    nostr_uri = f"nostr:{event_id}" if event_id else ""
    primal_link = f"https://primal.net/e/{event_id}" if event_id else ""
    snort_link = f"https://snort.social/e/{event_id}" if event_id else ""
    njump_link = f"https://njump.me/{event_id}" if event_id else ""

    return {
        "id": event_id,
        "pubkey": pubkey,
        "pubkey_short": pub_short,
        "pubkey_initials": (pubkey[:2].upper() if pubkey else "??"),
        "content": content,
        "content_preview": content[:280] if len(content) > 280 else content,
        "content_truncated": len(content) > 280,
        "created_at": created_at,
        "created_at_iso": iso_str,
        "time_str": time_str,
        "date_str": date_str,
        "kind": event.get("kind", 1),
        "hashtags": hashtags[:8],
        "relay": (event.get("_relay", "")).replace("wss://", ""),
        "nostr_uri": nostr_uri,
        "primal_link": primal_link,
        "snort_link": snort_link,
        "njump_link": njump_link,
    }


def _get_cached_events_serialised(limit: int = 50) -> List[Dict]:
    try:
        from services.nostr_feed_worker import get_cached_events
        events = get_cached_events(limit=limit)
        return [_serialise_event(e) for e in events]
    except Exception as exc:
        logger.warning("Failed to get cached Nostr events: %s", exc)
        return []


def _get_relay_status() -> List[Dict]:
    try:
        from services.nostr_feed_worker import get_relay_status, DEFAULT_RELAYS
        return get_relay_status()
    except Exception as exc:
        logger.warning("Failed to get relay status: %s", exc)
        try:
            from services.nostr_feed_worker import DEFAULT_RELAYS
            return [
                {
                    "url": r["url"],
                    "name": r["name"],
                    "description": r["description"],
                    "nips": r["nips"],
                    "connected": False,
                    "latency_ms": None,
                    "events_session": 0,
                    "events_per_min": 0.0,
                    "last_event_at": None,
                    "error": str(exc)[:60],
                }
                for r in DEFAULT_RELAYS
            ]
        except Exception:
            return []


# ── Page route ─────────────────────────────────────────────────────────────

@nostr_bp.route("/nostr")
def nostr_page():
    """Main Nostr feed page — SSR with cached events, client WS takes over."""
    _ensure_worker()

    cached_events = _get_cached_events_serialised(limit=50)
    relay_status = _get_relay_status()

    connected_count = sum(1 for r in relay_status if r.get("connected"))

    # PP npub (from env or well-known default)
    import os
    pp_npub = os.environ.get(
        "PP_NOSTR_NPUB",
        "npub1a38uwcec9u4pqd4dutezcfg3ujfapfm90vzzjtkq9cs2u5tws50stujyhm"
    )

    return render_template(
        "nostr_feed.html",
        cached_events=cached_events,
        relay_status=relay_status,
        connected_count=connected_count,
        relay_count=len(relay_status),
        pp_npub=pp_npub,
        initial_event_count=len(cached_events),
    )


# ── API: relay list ────────────────────────────────────────────────────────

@nostr_bp.route("/api/nostr/relays")
def api_nostr_relays():
    """GET /api/nostr/relays — default relay list with live status."""
    _ensure_worker()
    relay_status = _get_relay_status()
    return jsonify({
        "relays": relay_status,
        "connected_count": sum(1 for r in relay_status if r.get("connected")),
        "total_count": len(relay_status),
        "ts": int(time.time()),
    })


# ── API: cached events ─────────────────────────────────────────────────────

@nostr_bp.route("/api/nostr/cache")
def api_nostr_cache():
    """GET /api/nostr/cache — last 50 server-cached Bitcoin events."""
    _ensure_worker()
    limit = min(int(request.args.get("limit", 50)), 100)
    events = _get_cached_events_serialised(limit=limit)
    return jsonify({
        "events": events,
        "count": len(events),
        "ts": int(time.time()),
    })


# ── API: stats ─────────────────────────────────────────────────────────────

@nostr_bp.route("/api/nostr/stats")
def api_nostr_stats():
    """GET /api/nostr/stats — aggregate stats across all cached events."""
    _ensure_worker()
    try:
        from services.nostr_feed_worker import get_stats
        stats = get_stats()
    except Exception as exc:
        logger.warning("Nostr stats failed: %s", exc)
        stats = {
            "events_cached": 0,
            "relays_connected": 0,
            "relays_total": 4,
            "unique_pubkeys": 0,
            "top_hashtags": [],
            "worker_started": False,
        }
    return jsonify(stats)


# ── API: add custom relay ──────────────────────────────────────────────────

@nostr_bp.route("/api/nostr/relay/add", methods=["POST"])
def api_nostr_relay_add():
    """
    POST /api/nostr/relay/add
    Body (JSON): {"url": "wss://..."}
    Validates the relay URL format — actual client-side connection is
    handled by the browser, this just validates the URL structure.
    """
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip()

    if not url:
        return jsonify({"ok": False, "error": "url required"}), 400

    # Validate: must be wss:// or ws:// URL
    if not re.match(r"^wss?://[a-zA-Z0-9._\-]+(:\d+)?(/.*)?$", url):
        return jsonify({"ok": False, "error": "Invalid relay URL — must be wss:// or ws://"}), 400

    # Length guard
    if len(url) > 200:
        return jsonify({"ok": False, "error": "URL too long"}), 400

    logger.info("Nostr relay add requested: %s", url)
    return jsonify({
        "ok": True,
        "url": url,
        "message": "Relay URL validated — connect client-side",
    })
