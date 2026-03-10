"""
signal_engine.py — PP Signal Intelligence Score Engine

Computes a weighted composite signal score from 5 live data sources.
Weights: article sentiment 30%, price momentum 25%, onchain health 20%,
         social volume 15%, fear/greed 10%.
Caches result for 2 minutes to avoid quota burn.
"""

import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("SignalEngine")

# Weight table (must sum to 1.0)
WEIGHTS = {
    "article_sentiment":  0.30,
    "price_momentum":     0.25,
    "onchain_health":     0.20,
    "social_volume":      0.15,
    "fear_greed_contrib": 0.10,
}

# In-process cache — avoids re-computing on every request
_cache: dict = {"data": None, "ts": 0.0, "ttl": 120}  # 2-minute TTL


# ── Component functions ───────────────────────────────────────────────────────

def _article_sentiment_score(db, models) -> int:
    """Average sentiment_score from SentimentReport (last 30 records) → 0-100."""
    try:
        reports = (models.SentimentReport.query
                   .filter(models.SentimentReport.sentiment_score.isnot(None))
                   .order_by(models.SentimentReport.created_at.desc())
                   .limit(30)
                   .all())
        if not reports:
            return 52  # slight bullish lean fallback
        values = []
        for r in reports:
            v = float(r.sentiment_score)
            # Normalise: stored as -1..1 → 0-100
            if -1.0 <= v <= 1.0:
                v = (v + 1.0) * 50.0
            values.append(min(100.0, max(0.0, v)))
        return round(sum(values) / len(values))
    except Exception as exc:
        logger.warning("article_sentiment fallback: %s", exc)
        return 52


def _price_momentum_score() -> int:
    """BTC 24h price change mapped to 0-100 (centre at 0% = 50)."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true"},
            timeout=6,
            headers={"Accept": "application/json"},
        )
        change = float(r.json().get("bitcoin", {}).get("usd_24h_change", 0) or 0)
        # ±10% range maps to 0-100
        score = 50.0 + change * 5.0
        return round(min(100, max(0, score)))
    except Exception as exc:
        logger.warning("price_momentum fallback: %s", exc)
        return 50


def _onchain_health_score() -> int:
    """Hashrate 3-day trend from mempool.space → 0-100."""
    try:
        r = requests.get(
            "https://mempool.space/api/v1/mining/hashrate/3d",
            timeout=6,
            headers={"Accept": "application/json"},
        )
        rates = r.json().get("hashrates", [])
        if len(rates) >= 2:
            latest = float(rates[-1].get("avgHashrate", 0) or 0)
            prev = float(rates[-2].get("avgHashrate", 1) or 1)
            if prev > 0:
                pct = (latest - prev) / prev * 100.0
                # ±5% maps to 0-100
                score = 50.0 + pct * 10.0
                return round(min(100, max(0, score)))
        return 60
    except Exception as exc:
        logger.warning("onchain_health fallback: %s", exc)
        return 60


def _social_volume_score(db, models) -> int:
    """Article count in the last 4 hours as proxy for social/media volume → 0-100."""
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=4)
        count = (models.Article.query
                 .filter(models.Article.created_at >= cutoff,
                         models.Article.published == True)
                 .count())
        # 0 articles → 20, 20+ articles → 90 (cap)
        score = min(90, 20 + count * 3)
        return round(score)
    except Exception as exc:
        logger.warning("social_volume fallback: %s", exc)
        return 50


def _fear_greed_score() -> int:
    """Fear & Greed index from alternative.me → 0-100 (already on that scale)."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=6)
        value = int(r.json()["data"][0]["value"])
        return max(0, min(100, value))
    except Exception as exc:
        logger.warning("fear_greed fallback: %s", exc)
        return 50


# ── Classification ────────────────────────────────────────────────────────────

def classify_signal(score: int) -> str:
    if score >= 80:
        return "EXTREME BULLISH"
    elif score >= 65:
        return "BULLISH"
    elif score >= 45:
        return "NEUTRAL"
    elif score >= 30:
        return "BEARISH"
    else:
        return "EXTREME FEAR"


# ── Public API ────────────────────────────────────────────────────────────────

def compute_signal_score(db=None, models=None) -> dict:
    """
    Compute the PP Signal Intelligence score. Cached for 2 minutes.

    Returns:
        {
          "score":          int,        # 0-100 composite
          "classification": str,        # EXTREME FEAR / BEARISH / NEUTRAL / BULLISH / EXTREME BULLISH
          "components":     dict,       # per-component 0-100 scores
          "delta":          int,        # change from previous cached value (+/-)
          "ts":             str,        # ISO-8601 UTC timestamp
        }
    """
    now = time.monotonic()
    if _cache["data"] is not None and (now - _cache["ts"]) < _cache["ttl"]:
        return _cache["data"]

    components = {
        "article_sentiment":  _article_sentiment_score(db, models) if db else 52,
        "price_momentum":     _price_momentum_score(),
        "onchain_health":     _onchain_health_score(),
        "social_volume":      _social_volume_score(db, models) if db else 50,
        "fear_greed_contrib": _fear_greed_score(),
    }

    score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    score_int = round(score)
    classification = classify_signal(score_int)

    prev = _cache["data"]
    delta = (score_int - prev["score"]) if prev else 0

    result = {
        "score": score_int,
        "classification": classification,
        "components": components,
        "delta": delta,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _cache["data"] = result
    _cache["ts"] = now
    return result
