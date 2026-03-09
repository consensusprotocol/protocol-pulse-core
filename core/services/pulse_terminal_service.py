"""
pulse_terminal_service.py — Data reading logic for Pulse Terminal Commander API
Reads from intelligence data files, returns structured JSON for each endpoint.
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone, date
from pathlib import Path

logger = logging.getLogger("PulseTerminalService")

# ── Data path resolution ──────────────────────────────────────────────────────
# TERMINAL_DATA_DIR env overrides; defaults to pipeline intelligence dir on Ultron.
# On Replit, data is synced to this path from Ultron every 5 min.
_DEFAULT_DATA_DIR = os.path.expanduser(
    "~/protocol_pulse/video_pipeline_v3/data/intelligence"
)
_DATA_DIR = Path(os.environ.get("TERMINAL_DATA_DIR", _DEFAULT_DATA_DIR))

# ── Rate limiting (SQLite, per-day per user_id) ───────────────────────────────
_RL_DB_PATH = os.environ.get("RATE_LIMIT_DB", "/tmp/pp_terminal_rate_limits.db")
_rl_lock = threading.Lock()

COMMANDER_DAILY_LIMIT = 1000
OPERATOR_DAILY_LIMIT = 100


def _rl_db():
    conn = sqlite3.connect(_RL_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS rate_limits "
        "(user_id INTEGER, date TEXT, count INTEGER, PRIMARY KEY (user_id, date))"
    )
    conn.commit()
    return conn


def check_and_increment_rate_limit(user_id: int, tier: str) -> dict:
    """
    Returns {"allowed": bool, "remaining": int, "limit": int}.
    Increments counter if allowed.
    """
    limit = COMMANDER_DAILY_LIMIT if tier in ("commander", "sovereign") else OPERATOR_DAILY_LIMIT
    today = date.today().isoformat()

    with _rl_lock:
        conn = _rl_db()
        try:
            row = conn.execute(
                "SELECT count FROM rate_limits WHERE user_id=? AND date=?",
                (user_id, today),
            ).fetchone()
            current = row[0] if row else 0

            if current >= limit:
                return {"allowed": False, "remaining": 0, "limit": limit}

            if row:
                conn.execute(
                    "UPDATE rate_limits SET count=count+1 WHERE user_id=? AND date=?",
                    (user_id, today),
                )
            else:
                conn.execute(
                    "INSERT INTO rate_limits (user_id, date, count) VALUES (?,?,1)",
                    (user_id, today),
                )
            conn.commit()
            return {"allowed": True, "remaining": limit - current - 1, "limit": limit}
        finally:
            conn.close()


def get_rate_limit_status(user_id: int, tier: str) -> dict:
    """Returns current usage without incrementing."""
    limit = COMMANDER_DAILY_LIMIT if tier in ("commander", "sovereign") else OPERATOR_DAILY_LIMIT
    today = date.today().isoformat()
    conn = _rl_db()
    try:
        row = conn.execute(
            "SELECT count FROM rate_limits WHERE user_id=? AND date=?",
            (user_id, today),
        ).fetchone()
        used = row[0] if row else 0
        return {"used": used, "remaining": max(0, limit - used), "limit": limit}
    finally:
        conn.close()


# ── File loading helper ───────────────────────────────────────────────────────

def _load_json(filename: str) -> dict:
    """Load a JSON file from DATA_DIR; return {} on any error."""
    path = _DATA_DIR / filename
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Data file not found: %s", path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", path, e)
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Signal helpers ────────────────────────────────────────────────────────────

_BTC_TOPICS = {
    "price", "mining", "etf", "halving", "regulation", "lightning", "self-custody",
    "self custody", "layer2", "layer 2", "institutional", "reserve", "treasury",
    "btc", "bitcoin", "hash", "difficulty", "mempool", "fees", "block",
    "saylor", "blackrock", "etf flows", "spot etf",
}


def _btc_lens_score(stream: dict) -> int:
    """Estimate BTC relevance (0-100) from topics + title."""
    topics = [t.lower() for t in stream.get("topics", [])]
    title = (stream.get("title", "") or "").lower()
    hits = sum(1 for kw in _BTC_TOPICS if kw in title or any(kw in t for t in topics))
    return min(100, hits * 20 + stream.get("current_sentiment", 50) // 5)


# ── Live signals endpoint data ────────────────────────────────────────────────

def get_live_signals(limit: int = 10) -> dict:
    """
    Returns last N BTC-relevant live signals (YouTube + X Spaces).
    Adds btc_lens_sentiment derived score.
    """
    raw = _load_json("live_signals.json")
    streams = raw.get("live_streams", [])

    # Enrich each stream with btc_lens_sentiment
    enriched = []
    for s in streams:
        enriched.append({
            "video_id": s.get("video_id"),
            "title": s.get("title"),
            "channel": s.get("channel"),
            "source": s.get("source", "unknown"),
            "url": s.get("url"),
            "status": s.get("status", "unknown"),
            "started_at": s.get("started_at"),
            "last_updated": s.get("last_updated"),
            "topics": s.get("topics", []),
            "current_sentiment": s.get("current_sentiment", 50),
            "btc_lens_sentiment": _btc_lens_score(s),
            "participant_count": s.get("participant_count", 0),
        })

    # Sort by btc_lens_sentiment desc, return top N
    enriched.sort(key=lambda x: x["btc_lens_sentiment"], reverse=True)

    return {
        "data": {
            "signals": enriched[:limit],
            "total_monitored": len(streams),
            "channels_watched": raw.get("channels_watched", 0),
            "monitoring": raw.get("monitoring", False),
            "updated_at": raw.get("updated_at", _now_iso()),
        },
        "stale": _is_stale(raw.get("updated_at")),
    }


# ── Spaces live endpoint data ─────────────────────────────────────────────────

def get_spaces_live() -> dict:
    """Returns active X Spaces from live_signals.json."""
    raw = _load_json("live_signals.json")
    streams = raw.get("live_streams", [])

    spaces = [
        {
            "space_id": s.get("video_id"),
            "title": s.get("title"),
            "host": s.get("channel"),
            "url": s.get("url"),
            "status": s.get("status", "unknown"),
            "started_at": s.get("started_at"),
            "last_updated": s.get("last_updated"),
            "topics": s.get("topics", []),
            "current_sentiment": s.get("current_sentiment", 50),
            "btc_lens_sentiment": _btc_lens_score(s),
            "participant_count": s.get("participant_count", 0),
            "detected_via": s.get("detected_via", "monitor"),
        }
        for s in streams
        if s.get("source") == "x_spaces"
    ]

    active = [sp for sp in spaces if sp["status"] == "live"]

    return {
        "data": {
            "spaces": spaces,
            "active_count": len(active),
            "total_detected": len(spaces),
            "updated_at": raw.get("updated_at", _now_iso()),
        },
        "stale": _is_stale(raw.get("updated_at")),
    }


# ── TradFi signals endpoint data ─────────────────────────────────────────────

_TRADFI_FALLBACK = [
    {"handle": "ZeroHedge", "category": "macro", "btc_relevant": True,
     "signal": "Fed policy uncertainty driving hard-asset demand", "sentiment_score": 62,
     "timestamp": "2026-03-08T12:00:00Z", "source": "tradfi_monitor"},
    {"handle": "peterschiff", "category": "hard_assets", "btc_relevant": False,
     "signal": "Gold outperforming as inflation expectations rise", "sentiment_score": 55,
     "timestamp": "2026-03-08T11:30:00Z", "source": "tradfi_monitor"},
    {"handle": "elerianm", "category": "macro", "btc_relevant": True,
     "signal": "Institutional allocation to digital assets accelerating", "sentiment_score": 72,
     "timestamp": "2026-03-08T10:45:00Z", "source": "tradfi_monitor"},
    {"handle": "LizAnnSonders", "category": "equities", "btc_relevant": False,
     "signal": "Risk-on sentiment recovering after recent correction", "sentiment_score": 58,
     "timestamp": "2026-03-08T09:15:00Z", "source": "tradfi_monitor"},
    {"handle": "AswathDamodaran", "category": "valuation", "btc_relevant": True,
     "signal": "Bitcoin narrative shifting from speculation to store of value", "sentiment_score": 68,
     "timestamp": "2026-03-08T08:30:00Z", "source": "tradfi_monitor"},
]


def get_tradfi_signals(limit: int = 20) -> dict:
    """Returns top N TradFi signals. Reads tradfi_signals.json if available."""
    raw = _load_json("tradfi_signals.json")

    if raw:
        signals_raw = raw.get("signals", raw.get("items", []))
        # Ensure btc_relevant flag and sentiment_score exist
        signals = []
        for s in signals_raw[:limit]:
            signals.append({
                "handle": s.get("handle", s.get("author", "unknown")),
                "category": s.get("category", "macro"),
                "btc_relevant": s.get("btc_relevant", False),
                "signal": s.get("signal", s.get("text", s.get("content", ""))),
                "sentiment_score": s.get("sentiment_score", s.get("sentiment", 50)),
                "timestamp": s.get("timestamp", s.get("created_at", _now_iso())),
                "source": "tradfi_monitor",
                "url": s.get("url", s.get("tweet_url", "")),
            })
        updated_at = raw.get("updated_at", _now_iso())
        stale = _is_stale(updated_at)
    else:
        # Graceful fallback — use static stub data
        signals = _TRADFI_FALLBACK[:limit]
        updated_at = _now_iso()
        stale = True

    btc_relevant = [s for s in signals if s.get("btc_relevant")]

    return {
        "data": {
            "signals": signals,
            "btc_relevant_count": len(btc_relevant),
            "total_returned": len(signals),
            "updated_at": updated_at,
        },
        "stale": stale,
    }


# ── Composite sentiment endpoint data ────────────────────────────────────────

def get_sentiment_composite() -> dict:
    """Returns full composite sentiment from sentiment.json."""
    raw = _load_json("sentiment.json")

    if raw and "data" in raw:
        data = raw["data"]
        scan_time = raw.get("scan_time", _now_iso())
    else:
        # Fallback structure
        data = {
            "overall": {
                "score": 50,
                "label": "neutral",
                "change_24h": "N/A",
                "components": {
                    "youtube_sentiment": 50,
                    "topic_velocity_bullish_pct": 0,
                    "x_spaces_sentiment": 50,
                },
            },
            "breakdown": {
                "institutional": {"score": 50, "label": "neutral", "driver": "insufficient data"},
                "retail": {"score": 50, "label": "neutral", "driver": "insufficient data"},
                "mining": {"score": 50, "label": "neutral", "driver": "insufficient data"},
            },
            "historical": [],
        }
        scan_time = _now_iso()

    return {
        "data": data,
        "scan_time": scan_time,
        "stale": _is_stale(scan_time),
    }


# ── Alerts data ───────────────────────────────────────────────────────────────

def get_breaking_alerts() -> dict:
    """Returns current breaking alert status from daily_signals.json."""
    raw = _load_json("daily_signals.json")

    breaking = raw.get("breaking", False)
    topics = raw.get("topics", [])

    # Find any high-velocity topics that could be breaking
    breaking_topic = None
    for t in topics:
        if t.get("velocity_score", 0) >= 80:
            breaking_topic = t
            break

    alert = None
    if breaking or breaking_topic:
        topic_data = breaking_topic or topics[0] if topics else {}
        alert = {
            "topic": topic_data.get("topic", "unknown"),
            "velocity_score": topic_data.get("velocity_score", 0),
            "channels": topic_data.get("channels_covering", 0),
            "sentiment": topic_data.get("sentiment", "neutral"),
            "detected_at": _now_iso(),
            "severity": "high" if (topic_data.get("velocity_score", 0) or 0) >= 80 else "medium",
        }

    return {
        "data": {
            "breaking": bool(breaking or breaking_topic),
            "alert": alert,
            "monitoring": True,
            "threshold": {"channels": 4, "window_hours": 3, "velocity_score": 80},
            "checked_at": _now_iso(),
        }
    }


# ── Staleness helper ──────────────────────────────────────────────────────────

def _is_stale(ts_str: str | None, max_minutes: int = 30) -> bool:
    """Returns True if timestamp is more than max_minutes old or unparseable."""
    if not ts_str:
        return True
    try:
        # Handle both Z and +00:00 suffixes
        ts_str = ts_str.replace("Z", "+00:00")
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds() / 60
        return age > max_minutes
    except Exception:
        return True
