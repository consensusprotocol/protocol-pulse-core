"""
SESSION 3 — MEDIA UNIFIED BLUEPRINT
=====================================
Routes:
  GET  /media                         — Media Intelligence page
  GET  /media-unified                 — Alias redirect → /media
  GET  /api/signal/composite          — Weighted signal score (cached 2min)
  GET  /api/sentiment/heatmap         — Category sentiment grid (last 2h)
  GET  /api/media/sources/health      — Source scraper health
  GET  /api/media/feed/intelligence   — Latest 20 PP articles with sentiment
  GET  /api/media/feed/stream         — SSE stream for real-time feed
"""

import json
import logging
import time
from datetime import datetime, timedelta

import requests
from flask import Blueprint, Response, jsonify, redirect, render_template, request, stream_with_context

log = logging.getLogger(__name__)

media_bp = Blueprint("media", __name__)

# ── In-process cache ───────────────────────────────────────────────────────
_cache: dict = {}


def _cached(key: str, ttl: int, fn):
    """Simple TTL cache. Runs fn() to refresh if stale."""
    entry = _cache.get(key)
    now = time.time()
    if entry and now - entry["ts"] < ttl:
        return entry["data"]
    try:
        data = fn()
        _cache[key] = {"ts": now, "data": data}
        return data
    except Exception as exc:
        log.warning("cache refresh failed for %s: %s", key, exc)
        return entry["data"] if entry else None


# ── Helpers ────────────────────────────────────────────────────────────────

def _utcnow():
    return datetime.utcnow()


def _sentiment_label(score: float) -> str:
    if score is None:
        return "NEUTRAL"
    if score >= 65:
        return "BULLISH"
    if score <= 35:
        return "BEARISH"
    return "NEUTRAL"


def _sentiment_color(score: float) -> str:
    if score is None:
        return "#9ca3af"
    if score >= 65:
        return "#22c55e"
    if score <= 35:
        return "#ef4444"
    return "#f59e0b"


def _signal_color(score: float) -> str:
    if score >= 60:
        return "#22c55e"
    if score >= 30:
        return "#f59e0b"
    return "#ef4444"


def _signal_label(score: float) -> str:
    if score >= 75:
        return "STRONG"
    if score >= 60:
        return "ELEVATED"
    if score >= 40:
        return "MODERATE"
    if score >= 20:
        return "WEAK"
    return "MINIMAL"


# ── Signal Composite Logic ─────────────────────────────────────────────────

def _compute_composite_signal():
    """
    Weighted composite signal from 4 sub-components:
      Article Velocity   30%
      Sentiment Trend    25%
      Network Activity   20%
      Social Volume      15%
      Fear & Greed       10%
    Returns dict with overall score + sub-components.
    """
    from app import db
    from models import Article, FeedItem, SentimentSnapshot

    now = _utcnow()
    cutoff_1h = now - timedelta(hours=1)
    cutoff_2h = now - timedelta(hours=2)
    cutoff_24h = now - timedelta(hours=24)

    # ── Article Velocity (30%) ──
    try:
        articles_1h = Article.query.filter(
            Article.published == True,
            Article.created_at >= cutoff_1h,
        ).count()
        articles_24h = Article.query.filter(
            Article.published == True,
            Article.created_at >= cutoff_24h,
        ).count()
        hourly_avg = max(articles_24h / 24.0, 0.5)
        velocity_ratio = min(articles_1h / hourly_avg, 3.0)
        # Map 0-3x ratio → 0-100
        velocity_score = min(round(velocity_ratio / 3.0 * 100), 100)
        velocity_delta = round((velocity_ratio - 1.0) * 100)  # % vs baseline
    except Exception as exc:
        log.warning("velocity calc failed: %s", exc)
        articles_1h, articles_24h, velocity_score, velocity_delta = 0, 0, 50, 0

    # ── Sentiment Trend (25%) ──
    try:
        snapshot = (
            SentimentSnapshot.query
            .order_by(SentimentSnapshot.created_at.desc())
            .first()
        )
        sentiment_score = round(snapshot.score or 50) if snapshot else 50
        # 24h ago snapshot for delta
        snap_24h = (
            SentimentSnapshot.query
            .filter(SentimentSnapshot.created_at <= cutoff_24h)
            .order_by(SentimentSnapshot.created_at.desc())
            .first()
        )
        sentiment_delta = round(sentiment_score - (snap_24h.score or 50)) if snap_24h else 0
    except Exception as exc:
        log.warning("sentiment calc failed: %s", exc)
        sentiment_score, sentiment_delta = 50, 0

    # ── Network Activity (20%) — mempool.space ──
    def _fetch_mempool():
        r = requests.get(
            "https://mempool.space/api/mempool",
            timeout=5,
            headers={"User-Agent": "ProtocolPulse/3.0"},
        )
        r.raise_for_status()
        return r.json()

    try:
        mempool_data = _cached("mempool_stats", 120, _fetch_mempool)
        pending_txs = (mempool_data or {}).get("count", 0)
        # 0 pending → score 20, 200k+ → score 80 (high activity)
        network_score = min(max(int(20 + (pending_txs / 200000) * 60), 20), 85)
        network_delta = 0  # directional delta not available from single snapshot
    except Exception as exc:
        log.warning("mempool calc failed: %s", exc)
        pending_txs, network_score, network_delta = 0, 50, 0

    # ── Social Volume (15%) — FeedItem count last 1h ──
    try:
        social_1h = FeedItem.query.filter(
            FeedItem.created_at >= cutoff_1h,
        ).count()
        social_24h = FeedItem.query.filter(
            FeedItem.created_at >= cutoff_24h,
        ).count()
        social_avg = max(social_24h / 24.0, 0.5)
        social_ratio = min(social_1h / social_avg, 3.0)
        social_score = min(round(social_ratio / 3.0 * 100), 100)
        social_delta = round((social_ratio - 1.0) * 100)
    except Exception as exc:
        log.warning("social volume calc failed: %s", exc)
        social_1h, social_score, social_delta = 0, 50, 0

    # ── Fear & Greed (10%) ──
    def _fetch_fng():
        r = requests.get(
            "https://api.alternative.me/fng/?limit=2",
            timeout=5,
            headers={"User-Agent": "ProtocolPulse/3.0"},
        )
        r.raise_for_status()
        return r.json()

    try:
        fng_data = _cached("fng_latest", 3600, _fetch_fng)
        fng_items = (fng_data or {}).get("data", [])
        fng_score = int(fng_items[0]["value"]) if fng_items else 50
        fng_delta = (
            int(fng_items[0]["value"]) - int(fng_items[1]["value"])
            if len(fng_items) >= 2
            else 0
        )
        fng_label = (fng_items[0].get("value_classification") or "Neutral").upper() if fng_items else "NEUTRAL"
    except Exception as exc:
        log.warning("fng calc failed: %s", exc)
        fng_score, fng_delta, fng_label = 50, 0, "NEUTRAL"

    # ── Weighted Composite ──
    composite = round(
        velocity_score * 0.30
        + sentiment_score * 0.25
        + network_score * 0.20
        + social_score * 0.15
        + fng_score * 0.10
    )

    return {
        "score": composite,
        "label": _signal_label(composite),
        "color": _signal_color(composite),
        "components": {
            "article_velocity": {
                "label": "Article Velocity",
                "score": velocity_score,
                "delta": velocity_delta,
                "detail": f"{articles_1h} articles/hr",
                "weight": 30,
            },
            "sentiment_trend": {
                "label": "Sentiment Trend",
                "score": sentiment_score,
                "delta": sentiment_delta,
                "detail": _sentiment_label(sentiment_score),
                "weight": 25,
            },
            "network_activity": {
                "label": "Network Activity",
                "score": network_score,
                "delta": network_delta,
                "detail": f"{pending_txs:,} mempool txs",
                "weight": 20,
            },
            "social_volume": {
                "label": "Social Volume",
                "score": social_score,
                "delta": social_delta,
                "detail": f"{social_1h} signals/hr",
                "weight": 15,
            },
            "fear_greed": {
                "label": "Fear & Greed",
                "score": fng_score,
                "delta": fng_delta,
                "detail": fng_label,
                "weight": 10,
            },
        },
        "computed_at": now.isoformat() + "Z",
    }


# ── Sentiment Heatmap Logic ────────────────────────────────────────────────

_HEATMAP_CATEGORIES = {
    "Mining": ["mining", "hashrate", "miner", "asic", "difficulty", "pool"],
    "Regulation": ["regulation", "regulatory", "sec", "etf", "law", "policy", "government", "ban", "legal"],
    "ETFs": ["etf", "blackrock", "fidelity", "spot", "fund", "institutional"],
    "Lightning": ["lightning", "ln", "channel", "payment", "l2", "layer 2"],
    "DeFi": ["defi", "defi", "wrapped", "taproot", "ordinals", "runes"],
    "Macro": ["macro", "inflation", "fed", "interest rate", "economy", "dollar", "usd", "gold", "gdp"],
}


def _compute_heatmap():
    """Return category sentiment grid from articles in last 2h."""
    from app import db
    from models import Article

    cutoff_2h = _utcnow() - timedelta(hours=2)
    cutoff_24h = _utcnow() - timedelta(hours=24)

    try:
        recent = (
            Article.query
            .filter(Article.published == True, Article.created_at >= cutoff_24h)
            .with_entities(
                Article.category,
                Article.tags,
                Article.created_at,
            )
            .order_by(Article.created_at.desc())
            .limit(500)
            .all()
        )
    except Exception as exc:
        log.warning("heatmap query failed: %s", exc)
        recent = []

    # Bucket articles into categories
    buckets = {cat: {"count_2h": 0, "count_24h": 0} for cat in _HEATMAP_CATEGORIES}

    for row in recent:
        text = " ".join([
            (row.category or "").lower(),
            (row.tags or "").lower(),
        ])
        is_2h = row.created_at >= cutoff_2h if row.created_at else False
        for cat, keywords in _HEATMAP_CATEGORIES.items():
            if any(kw in text for kw in keywords):
                buckets[cat]["count_24h"] += 1
                if is_2h:
                    buckets[cat]["count_2h"] += 1

    # Build response cells
    cells = []
    for cat, data in buckets.items():
        count = data["count_2h"]
        count_24h = data["count_24h"]
        # Simple sentiment proxy: more articles = more coverage = higher buzz
        # Score from 0-100 based on coverage vs average
        avg_24h = max(sum(v["count_24h"] for v in buckets.values()) / len(buckets), 1)
        raw_score = min((count_24h / avg_24h) * 50, 100)
        score = round(raw_score)
        cells.append({
            "category": cat,
            "count_2h": count,
            "count_24h": count_24h,
            "score": score,
            "label": _sentiment_label(score),
            "color": _sentiment_color(score),
        })

    return {"cells": cells, "computed_at": _utcnow().isoformat() + "Z"}


# ── Source Health Logic ────────────────────────────────────────────────────

_KEY_SOURCES = [
    "Bitcoin Magazine", "CoinDesk", "Cointelegraph", "Decrypt",
    "The Block", "Blockworks", "Bitcoin.com", "Newsbtc",
    "Ambcrypto", "Bitcoinist", "CryptoSlate", "99Bitcoins",
]


def _compute_source_health():
    """Return health status for key article sources."""
    from app import db
    from models import Article
    from sqlalchemy import func

    try:
        now = _utcnow()
        rows = (
            Article.query
            .filter(Article.published == True)
            .with_entities(
                Article.author,
                func.count(Article.id).label("total"),
                func.max(Article.created_at).label("last_at"),
                func.sum(
                    db.case(
                        (Article.created_at >= now - timedelta(hours=24), 1),
                        else_=0,
                    )
                ).label("today"),
            )
            .group_by(Article.author)
            .order_by(func.count(Article.id).desc())
            .limit(30)
            .all()
        )
    except Exception as exc:
        log.warning("source health query failed: %s", exc)
        rows = []

    now = _utcnow()
    sources = []
    for row in rows:
        if not row.author or row.author in ("Protocol Pulse AI", ""):
            continue
        last_at = row.last_at
        if last_at is None:
            continue
        age_hours = (now - last_at).total_seconds() / 3600
        if age_hours < 1:
            status = "green"
            status_label = "LIVE"
        elif age_hours < 6:
            status = "amber"
            status_label = "RECENT"
        elif age_hours < 24:
            status = "red"
            status_label = "STALE"
        else:
            status = "red"
            status_label = "OFFLINE"

        sources.append({
            "name": row.author[:30],
            "last_scraped": last_at.isoformat() + "Z",
            "articles_today": int(row.today or 0),
            "total": int(row.total or 0),
            "status": status,
            "status_label": status_label,
            "age_hours": round(age_hours, 1),
        })
        if len(sources) >= 12:
            break

    return {"sources": sources, "computed_at": _utcnow().isoformat() + "Z"}


# ── Intelligence Feed Logic ────────────────────────────────────────────────

def _get_intelligence_feed(limit=20):
    """Latest articles with sentiment badges."""
    from app import db
    from models import Article

    try:
        articles = (
            Article.query
            .filter(Article.published == True)
            .order_by(Article.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as exc:
        log.warning("intelligence feed query failed: %s", exc)
        return {"items": [], "computed_at": _utcnow().isoformat() + "Z"}

    items = []
    for a in articles:
        # Derive sentiment from category/tags heuristic if no SentimentReport
        text = " ".join([
            (a.category or "").lower(),
            (a.tags or "").lower(),
            (a.title or "").lower(),
        ])
        bullish_words = ["bull", "surge", "rally", "growth", "adoption", "all-time", "record", "approved", "launch"]
        bearish_words = ["bear", "crash", "drop", "ban", "hack", "attack", "decline", "loss", "fail"]
        bull_score = sum(1 for w in bullish_words if w in text)
        bear_score = sum(1 for w in bearish_words if w in text)
        if bull_score > bear_score:
            sentiment = "BULLISH"
            sentiment_color = "#22c55e"
        elif bear_score > bull_score:
            sentiment = "BEARISH"
            sentiment_color = "#ef4444"
        else:
            sentiment = "NEUTRAL"
            sentiment_color = "#f59e0b"

        items.append({
            "id": a.id,
            "title": a.title,
            "summary": (a.summary or "")[:200],
            "source": a.author or "Protocol Pulse",
            "category": a.category or "News",
            "url": f"/article/{a.id}",
            "timestamp": a.created_at.isoformat() + "Z" if a.created_at else None,
            "sentiment": sentiment,
            "sentiment_color": sentiment_color,
            "cover_image": a.cover_image_url or a.header_image_url or "",
        })

    return {"items": items, "computed_at": _utcnow().isoformat() + "Z"}


# ── Live BTC Price (for health strip) ─────────────────────────────────────

def _fetch_btc_price():
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
        timeout=5,
        headers={"User-Agent": "ProtocolPulse/3.0"},
    )
    r.raise_for_status()
    data = r.json()
    return {
        "price": data["bitcoin"]["usd"],
        "change_24h": round(data["bitcoin"].get("usd_24h_change", 0), 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@media_bp.route("/media")
@media_bp.route("/media-unified")
def media_page():
    """Media Unified Intelligence page."""
    try:
        # SSR initial data so the page is meaningful before JS kicks in
        signal = _cached("signal_composite", 120, _compute_composite_signal)
        feed = _get_intelligence_feed(limit=10)
        return render_template(
            "media_unified.html",
            initial_signal=signal,
            initial_feed=feed,
        )
    except Exception as exc:
        log.error("media_page error: %s", exc, exc_info=True)
        return render_template(
            "media_unified.html",
            initial_signal=None,
            initial_feed=None,
        )


@media_bp.route("/api/signal/composite")
def api_signal_composite():
    """Weighted composite signal score. Cached 2min."""
    data = _cached("signal_composite", 120, _compute_composite_signal)
    if data is None:
        data = {
            "score": 50,
            "label": "MODERATE",
            "color": "#f59e0b",
            "components": {},
            "computed_at": _utcnow().isoformat() + "Z",
        }
    return jsonify(data)


@media_bp.route("/api/sentiment/heatmap")
def api_sentiment_heatmap():
    """Category sentiment heatmap from last 2h of articles."""
    data = _cached("sentiment_heatmap", 300, _compute_heatmap)
    if data is None:
        data = {"cells": [], "computed_at": _utcnow().isoformat() + "Z"}
    return jsonify(data)


@media_bp.route("/api/media/sources/health")
def api_media_sources_health():
    """Source health status grid."""
    data = _cached("sources_health", 300, _compute_source_health)
    if data is None:
        data = {"sources": [], "computed_at": _utcnow().isoformat() + "Z"}
    return jsonify(data)


@media_bp.route("/api/media/feed/intelligence")
def api_media_feed_intelligence():
    """Latest 20 PP articles with sentiment badges."""
    limit = min(int(request.args.get("limit", 20)), 50)
    data = _get_intelligence_feed(limit=limit)
    return jsonify(data)


@media_bp.route("/api/media/feed/stream")
def api_media_feed_stream():
    """
    Server-sent events for real-time intelligence feed.
    Polls DB every 30s for new articles and pushes them to the client.
    """
    def generate():
        from models import Article
        last_id = 0
        try:
            latest = Article.query.filter(Article.published == True).order_by(Article.id.desc()).first()
            if latest:
                last_id = latest.id
        except Exception:
            pass

        # Send initial heartbeat
        yield "event: heartbeat\ndata: {}\n\n"

        while True:
            try:
                new_articles = (
                    Article.query
                    .filter(Article.published == True, Article.id > last_id)
                    .order_by(Article.id.asc())
                    .limit(5)
                    .all()
                )
                for a in new_articles:
                    last_id = a.id
                    text = " ".join([
                        (a.category or "").lower(),
                        (a.tags or "").lower(),
                        (a.title or "").lower(),
                    ])
                    bullish_words = ["bull", "surge", "rally", "growth", "adoption", "record", "approved"]
                    bearish_words = ["bear", "crash", "drop", "ban", "hack", "decline", "loss"]
                    bull_score = sum(1 for w in bullish_words if w in text)
                    bear_score = sum(1 for w in bearish_words if w in text)
                    sentiment = "BULLISH" if bull_score > bear_score else ("BEARISH" if bear_score > bull_score else "NEUTRAL")
                    item = {
                        "id": a.id,
                        "title": a.title,
                        "source": a.author or "Protocol Pulse",
                        "category": a.category or "News",
                        "url": f"/article/{a.id}",
                        "timestamp": a.created_at.isoformat() + "Z" if a.created_at else None,
                        "sentiment": sentiment,
                    }
                    yield f"event: article\ndata: {json.dumps(item)}\n\n"
            except Exception as exc:
                log.warning("SSE stream error: %s", exc)
                yield f"event: error\ndata: {json.dumps({'msg': 'stream error'})}\n\n"

            # Heartbeat every 30s
            time.sleep(30)
            yield "event: heartbeat\ndata: {}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
