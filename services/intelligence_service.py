"""
Intelligence Service — p3-sentiment-intel
Computes signal strength composite, trending topics, entity tracker,
narrative timeline, and anomaly detection.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)

# ─── In-memory cache ────────────────────────────────────────────────────────
_cache: Dict[str, tuple] = {}  # key → (value, expires_at)

def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.monotonic() < entry[1]:
        return entry[0]
    return None

def _cache_set(key: str, value, ttl_seconds: int):
    _cache[key] = (value, time.monotonic() + ttl_seconds)


# ─── External data helpers ───────────────────────────────────────────────────

def _fetch_btc_price() -> Optional[float]:
    """Fetch BTC/USD price from CoinGecko. Returns None on failure."""
    cached = _cache_get("btc_price")
    if cached is not None:
        return cached
    try:
        import requests
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=8,
        )
        r.raise_for_status()
        price = float(r.json()["bitcoin"]["usd"])
        _cache_set("btc_price", price, 300)
        return price
    except Exception as e:
        logger.warning("_fetch_btc_price failed: %s", e)
        return None


def _fetch_btc_24h_change() -> Optional[float]:
    """Fetch 24h BTC price change % from CoinGecko."""
    cached = _cache_get("btc_24h_change")
    if cached is not None:
        return cached
    try:
        import requests
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={"localization": "false", "tickers": "false", "community_data": "false",
                    "developer_data": "false", "sparkline": "false"},
            timeout=8,
        )
        r.raise_for_status()
        change = float(r.json()["market_data"]["price_change_percentage_24h"])
        _cache_set("btc_24h_change", change, 300)
        return change
    except Exception as e:
        logger.warning("_fetch_btc_24h_change failed: %s", e)
        return None


def _fetch_fear_greed() -> Optional[Dict]:
    """Fetch Fear & Greed index from Alternative.me."""
    cached = _cache_get("fear_greed")
    if cached is not None:
        return cached
    try:
        import requests
        r = requests.get(
            "https://api.alternative.me/fng/",
            params={"limit": 8},
            timeout=8,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        result = {
            "value": int(data[0]["value"]),
            "classification": data[0]["value_classification"],
            "history": [{"value": int(d["value"]), "label": d["value_classification"]} for d in data],
        }
        _cache_set("fear_greed", result, 3600)
        return result
    except Exception as e:
        logger.warning("_fetch_fear_greed failed: %s", e)
        return None


def _fetch_hashrate() -> Optional[float]:
    """Fetch current hashrate in EH/s from mempool.space."""
    cached = _cache_get("hashrate")
    if cached is not None:
        return cached
    try:
        import requests
        r = requests.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=8)
        r.raise_for_status()
        data = r.json()
        # currentHashrate is in H/s, convert to EH/s
        current = data.get("currentHashrate", 0)
        ehs = current / 1e18
        _cache_set("hashrate", ehs, 600)
        return ehs
    except Exception as e:
        logger.warning("_fetch_hashrate failed: %s", e)
        return None


# ─── Signal strength composite ───────────────────────────────────────────────

def get_signal_strength() -> Dict:
    """
    Compute composite signal strength (0-100) from 5 weighted components:
      - sentiment_score:   40% weight (from latest sentiment_report)
      - fear_greed:        10% weight (Alternative.me)
      - price_momentum:    20% weight (24h BTC change)
      - article_volume:    15% weight (24h count vs 7-day avg)
      - hashrate_trend:    15% weight (vs 30-day avg)

    Returns dict with overall score, label, components, and trajectory.
    """
    cached = _cache_get("signal_strength")
    if cached is not None:
        return cached

    from app import db
    from sqlalchemy import text

    components = {}

    # ── Sentiment component (40%) ──
    try:
        row = db.session.execute(
            text("""SELECT score FROM sentiment_reports
                    ORDER BY report_date DESC LIMIT 1""")
        ).fetchone()
        sent_score = float(row[0]) if row else 50.0
    except Exception:
        sent_score = 50.0
    components["sentiment"] = {
        "score": sent_score,
        "weight": 0.40,
        "label": "Narrative Sentiment",
        "description": f"{sent_score:.0f}/100 based on article analysis",
    }

    # ── Fear & Greed component (10%) ──
    fg_data = _fetch_fear_greed()
    if fg_data:
        fg_score = float(fg_data["value"])
        fg_label = fg_data["classification"]
    else:
        fg_score = 50.0
        fg_label = "Unknown"
    components["fear_greed"] = {
        "score": fg_score,
        "weight": 0.10,
        "label": "Fear & Greed",
        "description": fg_label,
        "raw_data": fg_data,
    }

    # ── Price momentum component (20%) ──
    price_change = _fetch_btc_24h_change()
    if price_change is not None:
        # Map -20%..+20% → 0..100 (center at 50)
        price_score = max(0.0, min(100.0, 50.0 + price_change * 2.5))
        price_desc = f"{price_change:+.2f}% 24h"
    else:
        price_score = 50.0
        price_desc = "Data unavailable"
    components["price_momentum"] = {
        "score": price_score,
        "weight": 0.20,
        "label": "Price Momentum",
        "description": price_desc,
    }

    # ── Article volume component (15%) ──
    try:
        cutoff_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        cutoff_7d = (datetime.utcnow() - timedelta(days=7)).isoformat()

        count_24h = db.session.execute(
            text("SELECT COUNT(*) FROM articles WHERE published=1 AND created_at >= :c"),
            {"c": cutoff_24h}
        ).fetchone()[0]

        count_7d = db.session.execute(
            text("SELECT COUNT(*) FROM articles WHERE published=1 AND created_at >= :c"),
            {"c": cutoff_7d}
        ).fetchone()[0]

        daily_avg = (count_7d / 7.0) if count_7d else 1.0
        if daily_avg > 0:
            # Ratio: 1x avg = 50 pts, 2x avg = 100 pts, 0x = 0 pts
            vol_score = max(0.0, min(100.0, (count_24h / daily_avg) * 50.0))
        else:
            vol_score = 50.0
        vol_desc = f"{count_24h} articles (7d avg: {daily_avg:.1f}/day)"
    except Exception as e:
        logger.warning("get_signal_strength: article volume failed: %s", e)
        vol_score = 50.0
        vol_desc = "Data unavailable"
        count_24h = 0

    components["article_volume"] = {
        "score": vol_score,
        "weight": 0.15,
        "label": "Article Volume",
        "description": vol_desc,
        "count_24h": count_24h,
    }

    # ── Hashrate trend component (15%) ──
    hashrate = _fetch_hashrate()
    if hashrate is not None:
        # >1000 EH/s is strong (100), 500 EH/s is neutral (50), <100 EH/s is weak (0)
        hash_score = max(0.0, min(100.0, (hashrate / 10.0)))
        hash_desc = f"{hashrate:.0f} EH/s"
    else:
        hash_score = 65.0  # reasonable default
        hash_desc = "Data unavailable"
    components["hashrate"] = {
        "score": hash_score,
        "weight": 0.15,
        "label": "Hash Rate",
        "description": hash_desc,
        "value_ehs": hashrate,
    }

    # ── Composite ──
    composite = sum(c["score"] * c["weight"] for c in components.values())
    composite = max(0.0, min(100.0, composite))

    if composite >= 75:
        label = "EUPHORIA"
        color = "#5de4ff"
    elif composite >= 60:
        label = "CONFIDENCE"
        color = "#89ffb8"
    elif composite >= 45:
        label = "NEUTRAL"
        color = "#f8c15c"
    elif composite >= 30:
        label = "CAUTION"
        color = "#ff8ba0"
    else:
        label = "FEAR"
        color = "#ff3b5f"

    # ── Trajectory (7-day slope) ──
    try:
        rows_7d = db.session.execute(
            text("""SELECT score FROM sentiment_reports
                    ORDER BY report_date DESC LIMIT 7""")
        ).fetchall()
        scores_7d = [float(r[0]) for r in rows_7d if r[0] is not None]
        if len(scores_7d) >= 3:
            # Simple slope: last - first over N days
            slope = (scores_7d[0] - scores_7d[-1]) / len(scores_7d)
            if slope > 3:
                trajectory = "ACCELERATING_BULLISH"
            elif slope > 1:
                trajectory = "RECOVERING"
            elif slope < -3:
                trajectory = "ACCELERATING_BEARISH"
            elif slope < -1:
                trajectory = "DETERIORATING"
            else:
                trajectory = "STABLE"
        else:
            trajectory = "INSUFFICIENT_DATA"
            scores_7d = []
    except Exception:
        trajectory = "INSUFFICIENT_DATA"
        scores_7d = []

    result = {
        "composite": round(composite, 1),
        "label": label,
        "color": color,
        "components": components,
        "trajectory": trajectory,
        "score_history_7d": scores_7d,
        "btc_price": _fetch_btc_price(),
        "computed_at": datetime.utcnow().isoformat(),
    }

    _cache_set("signal_strength", result, 300)  # 5-minute cache
    return result


# ─── Trending topics ─────────────────────────────────────────────────────────

def get_trending_topics(hours: int = 24) -> List[Dict]:
    """
    Extract top topics from recent article titles/narratives.
    Returns list of {topic, count, sentiment, size} dicts.
    Cached 30 minutes.
    """
    cache_key = f"trending_topics_{hours}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    from app import db
    from sqlalchemy import text

    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        rows = db.session.execute(
            text("""SELECT title, sentiment, narrative_label, importance_score
                    FROM articles
                    WHERE published = 1 AND created_at >= :cutoff
                    ORDER BY importance_score DESC NULLS LAST
                    LIMIT 100"""),
            {"cutoff": cutoff}
        ).fetchall()
    except Exception as e:
        logger.error("get_trending_topics: query failed: %s", e)
        return []

    if not rows:
        return []

    # Use Claude Haiku to extract topics from narrative_labels if available
    # Otherwise fall back to simple narrative counting
    narrative_data: Dict[str, Dict] = {}
    for row in rows:
        narr = row[2] or "other"
        sent = row[1] or "neutral"
        if narr not in narrative_data:
            narrative_data[narr] = {"count": 0, "bullish": 0, "bearish": 0, "neutral": 0}
        narrative_data[narr]["count"] += 1
        if sent in ("bullish", "bearish", "neutral"):
            narrative_data[narr][sent] += 1

    # Sort by count descending
    sorted_topics = sorted(narrative_data.items(), key=lambda x: x[1]["count"], reverse=True)

    # Compute font size (12-36px proportional)
    max_count = sorted_topics[0][1]["count"] if sorted_topics else 1
    result = []
    for topic, data in sorted_topics[:15]:
        count = data["count"]
        bull = data["bullish"]
        bear = data["bearish"]

        if bull > bear:
            dominant_sentiment = "bullish"
        elif bear > bull:
            dominant_sentiment = "bearish"
        else:
            dominant_sentiment = "neutral"

        size = 12 + int((count / max_count) * 24)

        result.append({
            "topic": topic,
            "count": count,
            "sentiment": dominant_sentiment,
            "size": size,
            "bullish": bull,
            "bearish": bear,
            "neutral": data["neutral"],
        })

    _cache_set(cache_key, result, 1800)
    return result


# ─── Entity tracker ──────────────────────────────────────────────────────────

def get_entity_tracker(hours: int = 48) -> List[Dict]:
    """
    Extract named entities from recent article titles.
    Returns list of {entity, type, mention_count, sentiment, trend}.
    Cached 30 minutes.
    """
    cache_key = f"entity_tracker_{hours}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    from app import db
    from sqlalchemy import text

    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cutoff_prev = (datetime.utcnow() - timedelta(hours=hours * 2)).isoformat()

    try:
        rows = db.session.execute(
            text("""SELECT title, summary, sentiment, created_at
                    FROM articles
                    WHERE published = 1 AND created_at >= :cutoff
                    ORDER BY created_at DESC LIMIT 100"""),
            {"cutoff": cutoff}
        ).fetchall()
    except Exception as e:
        logger.error("get_entity_tracker: query failed: %s", e)
        return []

    if not rows:
        return []

    # Use Claude Haiku for entity extraction if >5 articles, else simple scan
    # Simple entity scanner based on known Bitcoin entities
    KNOWN_ENTITIES = {
        # People
        "Michael Saylor": "person", "Satoshi Nakamoto": "person",
        "Elon Musk": "person", "Jack Dorsey": "person", "Lyn Alden": "person",
        "Warren Buffett": "person", "Jerome Powell": "person", "Gary Gensler": "person",
        "Paul Tudor Jones": "person", "Cathie Wood": "person",
        # Orgs
        "MicroStrategy": "organization", "BlackRock": "organization",
        "Grayscale": "organization", "Coinbase": "organization", "Binance": "organization",
        "SEC": "organization", "Federal Reserve": "organization", "IMF": "organization",
        "Fidelity": "organization", "ARK Invest": "organization",
        # Coins/protocols
        "Bitcoin": "protocol", "Lightning Network": "protocol", "Taproot": "protocol",
        "Ordinals": "protocol", "Runes": "protocol", "Liquid": "protocol",
        # Events
        "ETF": "event", "halving": "event", "FOMC": "event",
    }

    entity_data: Dict[str, Dict] = {}
    all_text = " ".join([f"{r[0]} {r[1] or ''}" for r in rows])
    all_text_lower = all_text.lower()

    for entity, etype in KNOWN_ENTITIES.items():
        count = all_text_lower.count(entity.lower())
        if count == 0:
            continue

        # Sentiment for articles mentioning this entity
        entity_lower = entity.lower()
        bull = sum(1 for r in rows if entity_lower in (r[0] or "").lower() and r[2] == "bullish")
        bear = sum(1 for r in rows if entity_lower in (r[0] or "").lower() and r[2] == "bearish")

        if bull > bear:
            sent = "bullish"
        elif bear > bull:
            sent = "bearish"
        else:
            sent = "neutral"

        entity_data[entity] = {
            "entity": entity,
            "type": etype,
            "mention_count": count,
            "sentiment": sent,
            "bullish": bull,
            "bearish": bear,
        }

    # Sort by mention count
    sorted_entities = sorted(entity_data.values(), key=lambda x: x["mention_count"], reverse=True)

    # Add trend: compare vs previous period (simple stub — needs historical data)
    for e in sorted_entities:
        e["trend"] = "stable"  # TODO: compare vs prev period when enough data

    result = sorted_entities[:20]
    _cache_set(cache_key, result, 1800)
    return result


# ─── Narrative timeline ──────────────────────────────────────────────────────

def get_narrative_timeline(days: int = 7) -> List[Dict]:
    """
    Return dominant narrative per day for the last N days.
    Returns list of {date, dominant_narrative, score, sentiment}.
    """
    from app import db
    from sqlalchemy import text

    result = []
    for i in range(days - 1, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        try:
            row = db.session.execute(
                text("""SELECT dominant_narrative, score, overall_sentiment
                        FROM sentiment_reports WHERE report_date = :d"""),
                {"d": day.isoformat()}
            ).fetchone()

            if row:
                result.append({
                    "date": day.strftime("%b %d"),
                    "dominant_narrative": row[0] or "unknown",
                    "score": float(row[1]) if row[1] else 50.0,
                    "sentiment": row[2] or "neutral",
                })
            else:
                # Compute on-the-fly from articles
                cutoff_start = datetime.combine(day, datetime.min.time()).isoformat()
                cutoff_end = datetime.combine(day, datetime.max.time()).isoformat()
                narr_row = db.session.execute(
                    text("""SELECT narrative_label, COUNT(*) as cnt
                            FROM articles
                            WHERE published=1
                            AND created_at BETWEEN :s AND :e
                            AND narrative_label IS NOT NULL
                            GROUP BY narrative_label
                            ORDER BY cnt DESC LIMIT 1"""),
                    {"s": cutoff_start, "e": cutoff_end}
                ).fetchone()
                result.append({
                    "date": day.strftime("%b %d"),
                    "dominant_narrative": narr_row[0] if narr_row else "no data",
                    "score": 50.0,
                    "sentiment": "neutral",
                })
        except Exception as e:
            logger.warning("get_narrative_timeline: day %s failed: %s", day, e)
            result.append({
                "date": day.strftime("%b %d"),
                "dominant_narrative": "error",
                "score": 50.0,
                "sentiment": "neutral",
            })

    return result


# ─── Anomaly detection ───────────────────────────────────────────────────────

def detect_anomalies() -> Optional[Dict]:
    """
    Compare last 2hr sentiment vs 24hr baseline.
    Checks 3 vectors: score delta, volume spike, narrative shift.
    Returns anomaly dict if detected, else None.
    """
    from app import db
    from sqlalchemy import text

    try:
        now = datetime.utcnow()
        cutoff_2h = (now - timedelta(hours=2)).isoformat()
        cutoff_24h = (now - timedelta(hours=24)).isoformat()

        # Recent (2h) articles
        recent = db.session.execute(
            text("""SELECT sentiment, narrative_label, importance_score
                    FROM articles WHERE published=1 AND created_at >= :c
                    AND sentiment IS NOT NULL"""),
            {"c": cutoff_2h}
        ).fetchall()

        # Baseline (24h) articles
        baseline = db.session.execute(
            text("""SELECT sentiment, narrative_label, importance_score
                    FROM articles WHERE published=1 AND created_at >= :c
                    AND sentiment IS NOT NULL"""),
            {"c": cutoff_24h}
        ).fetchall()

        if len(baseline) < 5:
            return None

        def _score_list(rows):
            if not rows:
                return 50.0
            bull = sum(1 for r in rows if r[0] == "bullish")
            bear = sum(1 for r in rows if r[0] == "bearish")
            total = len(rows)
            return (bull / total) * 100 if total > 0 else 50.0

        recent_score = _score_list(recent)
        baseline_score = _score_list(baseline)
        delta = abs(recent_score - baseline_score)

        anomalies = []

        # Vector 1: Score delta > 20
        if delta > 20:
            direction = "bullish" if recent_score > baseline_score else "bearish"
            anomalies.append({
                "vector": "sentiment_score",
                "description": f"Score shifted {direction} by {delta:.0f} points in 2h",
                "severity": "critical" if delta > 30 else "warning",
            })

        # Vector 2: Volume spike (2h rate vs 24h rate)
        rate_24h = len(baseline) / 24.0
        rate_2h = len(recent) / 2.0
        if rate_24h > 0 and rate_2h > rate_24h * 2:
            anomalies.append({
                "vector": "volume_spike",
                "description": f"Article rate 2x normal: {rate_2h:.1f}/hr vs avg {rate_24h:.1f}/hr",
                "severity": "warning",
            })

        # Vector 3: Narrative shift
        if recent and baseline:
            recent_narratives = Counter(r[1] for r in recent if r[1])
            baseline_narratives = Counter(r[1] for r in baseline if r[1])
            if recent_narratives and baseline_narratives:
                recent_dominant = recent_narratives.most_common(1)[0][0]
                baseline_dominant = baseline_narratives.most_common(1)[0][0]
                if recent_dominant != baseline_dominant:
                    anomalies.append({
                        "vector": "narrative_shift",
                        "description": f"Narrative shifted: '{baseline_dominant}' → '{recent_dominant}'",
                        "severity": "info",
                    })

        if not anomalies:
            return None

        result = {
            "anomalies": anomalies,
            "recent_score": recent_score,
            "baseline_score": baseline_score,
            "delta": delta,
            "detected_at": now.isoformat(),
        }

        # Log to intelligence_events
        try:
            db.session.execute(
                text("""INSERT INTO intelligence_events
                        (event_type, severity, description, data_snapshot, created_at)
                        VALUES (:type, :sev, :desc, :data, :now)"""),
                {
                    "type": "multivariate_anomaly",
                    "sev": max(a["severity"] for a in anomalies),
                    "desc": "; ".join(a["description"] for a in anomalies),
                    "data": json.dumps(result),
                    "now": now.isoformat(),
                }
            )
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            logger.warning("detect_anomalies: failed to log event: %s", db_err)

        return result

    except Exception as e:
        logger.error("detect_anomalies failed: %s", e)
        return None


# ─── Intelligence events feed ────────────────────────────────────────────────

def get_intelligence_events(limit: int = 10) -> List[Dict]:
    """Return recent intelligence events from the DB."""
    from app import db
    from sqlalchemy import text

    try:
        rows = db.session.execute(
            text("""SELECT id, event_type, severity, description, created_at
                    FROM intelligence_events
                    ORDER BY created_at DESC LIMIT :lim"""),
            {"lim": limit}
        ).fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "event_type": r[1],
                "severity": r[2],
                "description": r[3],
                "created_at": r[4],
            })
        return result
    except Exception as e:
        logger.error("get_intelligence_events failed: %s", e)
        return []


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    args = sys.argv[1:]
    if not args:
        print("Usage: python -m services.intelligence_service signal")
        sys.exit(1)

    command = args[0]
    if command == "signal":
        from app import create_app
        app = create_app()
        with app.app_context():
            result = get_signal_strength()
            print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
