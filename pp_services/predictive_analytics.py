"""
Predictive Analytics Engine - Protocol Pulse

Lightweight forecasting module for Bitcoin intelligence trends.
Analyzes sentiment trajectories, topic acceleration, whale activity,
and content velocity to produce actionable market signals.

No ML libraries required -- uses basic statistics (mean, std dev,
simple linear regression) computed from SQLAlchemy query results.
Results are cached for 10 minutes to keep computations cheap.
"""

import logging
import math
import time
from datetime import datetime, timedelta, date
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy import func, desc, cast, Date

from app import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy model imports -- avoids circular-import issues at module level.
# ---------------------------------------------------------------------------

def _get_models():
    """Import models lazily to avoid circular imports during app bootstrap."""
    from models import Article, SentimentSnapshot, WhaleTransaction
    # PageView may or may not exist; handle gracefully
    try:
        from models import PageView
    except ImportError:
        PageView = None
    return Article, SentimentSnapshot, WhaleTransaction, PageView


# ---------------------------------------------------------------------------
# In-process TTL cache (no external dependencies)
# ---------------------------------------------------------------------------

_cache_store: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10 minutes in seconds


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache_store.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > _CACHE_TTL:
        _cache_store.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _cache_store[key] = (time.time(), value)


def _cache_clear() -> None:
    _cache_store.clear()


# ---------------------------------------------------------------------------
# Statistical helpers (no numpy/scipy needed)
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std_dev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _linear_regression_slope(values: List[float]) -> float:
    """Simple OLS slope for evenly-spaced data (x = 0..n-1).

    Returns the slope; positive means increasing trend.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _mean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _moving_average(values: List[float], window: int = 7) -> List[Optional[float]]:
    """Compute moving average. Returns None for positions before the window fills."""
    result: List[Optional[float]] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            window_slice = values[i - window + 1:i + 1]
            result.append(round(_mean(window_slice), 4))
    return result


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ---------------------------------------------------------------------------
# Emotional / engagement word lists for heuristic scoring
# ---------------------------------------------------------------------------

_EMOTIONAL_WORDS = frozenset([
    "crash", "surge", "plunge", "soar", "explode", "collapse", "moon",
    "panic", "fear", "greed", "euphoria", "catastrophe", "crisis",
    "breakthrough", "massive", "unprecedented", "shocking", "urgent",
    "critical", "breaking", "alert", "warning", "bull", "bear",
    "rally", "dump", "pump", "whale", "record", "historic",
    "secret", "revealed", "exclusive", "insider", "prediction",
    "bitcoin", "btc", "satoshi", "halving", "etf", "regulation",
])

_POWER_WORDS = frozenset([
    "why", "how", "what", "guide", "ultimate", "complete", "essential",
    "proven", "simple", "free", "new", "best", "top", "must",
])


# ===========================================================================
# 1. get_pulse_forecast()
# ===========================================================================

def get_pulse_forecast() -> Dict[str, Any]:
    """Build the main forecast payload with all sub-analyses.

    Returns a comprehensive dict covering sentiment trends, topic forecasts,
    content velocity, engagement predictions, whale activity, and a
    synthesised market-correlation signal.

    Results are cached for 10 minutes.
    """
    cached = _cache_get("pulse_forecast")
    if cached is not None:
        return cached

    Article, SentimentSnapshot, WhaleTransaction, PageView = _get_models()

    now = datetime.utcnow()

    result = {
        "sentiment_trend": _build_sentiment_trend(SentimentSnapshot, now),
        "topic_forecast": _build_topic_forecast(Article, now),
        "content_velocity": _build_content_velocity(Article, now),
        "engagement_prediction": _build_engagement_predictions(Article, PageView, now),
        "whale_activity_trend": _build_whale_activity_trend(WhaleTransaction, now),
        "market_correlation": None,  # filled below after sub-analyses
        "forecast_summary": "",
        "generated_at": now.isoformat() + "Z",
    }

    # Market correlation needs sentiment + article volume
    result["market_correlation"] = _build_market_correlation(
        SentimentSnapshot, Article, now
    )

    # Synthesise a human-readable forecast summary
    result["forecast_summary"] = _build_forecast_summary(result)

    _cache_set("pulse_forecast", result)
    return result


# ---------------------------------------------------------------------------
# Sub-builders
# ---------------------------------------------------------------------------

def _build_sentiment_trend(SentimentSnapshot, now: datetime) -> Dict[str, Any]:
    """Analyse sentiment over the last 30 days."""
    try:
        cutoff = now - timedelta(days=30)

        rows = (
            db.session.query(
                cast(SentimentSnapshot.created_at, Date).label("day"),
                func.avg(SentimentSnapshot.score).label("avg_score"),
            )
            .filter(SentimentSnapshot.created_at >= cutoff)
            .group_by(cast(SentimentSnapshot.created_at, Date))
            .order_by("day")
            .all()
        )

        if not rows:
            return {
                "trend": "NEUTRAL",
                "current_score": None,
                "slope": 0.0,
                "sparkline": [],
                "ma_7d": [],
                "data_points": 0,
            }

        daily_scores = [float(r.avg_score) for r in rows]
        dates = [r.day.isoformat() if hasattr(r.day, "isoformat") else str(r.day) for r in rows]
        ma_7d = _moving_average(daily_scores, window=7)
        slope = _linear_regression_slope(daily_scores)

        # Determine trend label from the slope relative to the score range.
        # SentimentSnapshot.score defaults to 50.0 (0-100 scale).
        if slope > 0.5:
            trend = "BULLISH"
        elif slope < -0.5:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        return {
            "trend": trend,
            "current_score": round(daily_scores[-1], 2) if daily_scores else None,
            "slope": round(slope, 4),
            "sparkline": [
                {"date": d, "score": round(s, 2)}
                for d, s in zip(dates, daily_scores)
            ],
            "ma_7d": [
                {"date": d, "value": round(v, 2) if v is not None else None}
                for d, v in zip(dates, ma_7d)
            ],
            "data_points": len(daily_scores),
        }
    except Exception as exc:
        logger.error("Sentiment trend analysis failed: %s", exc)
        return {
            "trend": "NEUTRAL",
            "current_score": None,
            "slope": 0.0,
            "sparkline": [],
            "ma_7d": [],
            "data_points": 0,
        }


def _build_topic_forecast(Article, now: datetime) -> List[Dict[str, Any]]:
    """Identify topics with accelerating coverage.

    Compares article counts per tag in the most recent 7 days versus the
    prior 7 days and returns the top 5 by growth rate.
    """
    try:
        recent_start = now - timedelta(days=7)
        prior_start = now - timedelta(days=14)

        recent_articles = (
            Article.query
            .filter(Article.created_at >= recent_start, Article.published == True)
            .all()
        )
        prior_articles = (
            Article.query
            .filter(
                Article.created_at >= prior_start,
                Article.created_at < recent_start,
                Article.published == True,
            )
            .all()
        )

        def _tag_counts(articles) -> Dict[str, int]:
            counts: Dict[str, int] = defaultdict(int)
            for art in articles:
                tags_raw = art.tags or ""
                for tag in tags_raw.split(","):
                    tag = tag.strip().lower()
                    if tag:
                        counts[tag] += 1
            return counts

        recent_counts = _tag_counts(recent_articles)
        prior_counts = _tag_counts(prior_articles)

        all_tags = set(recent_counts.keys()) | set(prior_counts.keys())
        growth_data = []
        for tag in all_tags:
            recent_n = recent_counts.get(tag, 0)
            prior_n = prior_counts.get(tag, 0)
            # Growth rate: avoid division by zero; treat 0 prior as baseline of 1
            baseline = max(prior_n, 1)
            growth_rate = (recent_n - prior_n) / baseline
            growth_data.append({
                "topic": tag,
                "recent_7d": recent_n,
                "prior_7d": prior_n,
                "growth_rate": round(growth_rate, 2),
            })

        # Sort by growth rate descending, break ties by recent count
        growth_data.sort(key=lambda x: (x["growth_rate"], x["recent_7d"]), reverse=True)
        return growth_data[:5]
    except Exception as exc:
        logger.error("Topic forecast failed: %s", exc)
        return []


def _build_content_velocity(Article, now: datetime) -> Dict[str, Any]:
    """Articles/day per category for last 7 and 30 days."""
    try:
        def _velocity_by_category(days: int) -> Dict[str, float]:
            cutoff = now - timedelta(days=days)
            rows = (
                db.session.query(
                    Article.category,
                    func.count(Article.id).label("cnt"),
                )
                .filter(Article.created_at >= cutoff, Article.published == True)
                .group_by(Article.category)
                .all()
            )
            return {
                (r.category or "Uncategorized"): round(r.cnt / max(days, 1), 2)
                for r in rows
            }

        vel_7d = _velocity_by_category(7)
        vel_30d = _velocity_by_category(30)

        all_cats = set(vel_7d.keys()) | set(vel_30d.keys())
        categories = []
        for cat in sorted(all_cats):
            v7 = vel_7d.get(cat, 0.0)
            v30 = vel_30d.get(cat, 0.0)
            acceleration = round(v7 - v30, 2)
            categories.append({
                "category": cat,
                "articles_per_day_7d": v7,
                "articles_per_day_30d": v30,
                "acceleration": acceleration,
            })

        # Sort by 7d velocity descending
        categories.sort(key=lambda x: x["articles_per_day_7d"], reverse=True)

        return {
            "categories": categories,
            "hottest_category": categories[0]["category"] if categories else None,
        }
    except Exception as exc:
        logger.error("Content velocity analysis failed: %s", exc)
        return {"categories": [], "hottest_category": None}


def _build_engagement_predictions(
    Article, PageView, now: datetime
) -> List[Dict[str, Any]]:
    """Score unpublished or recently-created articles on likely engagement.

    Uses heuristics: title length, numbers, questions, emotional words,
    topic recency, and (optionally) historical PageView data.
    """
    try:
        # Get unpublished articles OR articles published in the last 48h
        cutoff_recent = now - timedelta(hours=48)
        candidates = (
            Article.query
            .filter(
                db.or_(
                    Article.published == False,
                    db.and_(
                        Article.published == True,
                        Article.created_at >= cutoff_recent,
                    ),
                )
            )
            .order_by(desc(Article.created_at))
            .limit(20)
            .all()
        )

        # Compute category popularity from the last 30 days
        cat_cutoff = now - timedelta(days=30)
        cat_rows = (
            db.session.query(
                Article.category,
                func.count(Article.id).label("cnt"),
            )
            .filter(Article.created_at >= cat_cutoff, Article.published == True)
            .group_by(Article.category)
            .all()
        )
        max_cat_count = max((r.cnt for r in cat_rows), default=1) or 1
        cat_popularity = {
            (r.category or "Uncategorized"): r.cnt / max_cat_count
            for r in cat_rows
        }

        # Compute tag recency -- tags used in the last 7 days
        tag_cutoff = now - timedelta(days=7)
        recent_arts = (
            Article.query
            .filter(Article.created_at >= tag_cutoff, Article.published == True)
            .all()
        )
        recent_tags: Dict[str, int] = defaultdict(int)
        for art in recent_arts:
            for tag in (art.tags or "").split(","):
                tag = tag.strip().lower()
                if tag:
                    recent_tags[tag] += 1

        results = []
        for art in candidates:
            score, factors = _score_article_engagement(
                title=art.title or "",
                category=art.category or "",
                tags=art.tags or "",
                cat_popularity=cat_popularity,
                recent_tags=recent_tags,
            )
            results.append({
                "article_id": art.id,
                "title": art.title,
                "published": art.published,
                "score": score,
                "factors": factors,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    except Exception as exc:
        logger.error("Engagement prediction failed: %s", exc)
        return []


def _build_whale_activity_trend(WhaleTransaction, now: datetime) -> Dict[str, Any]:
    """Analyse whale transactions over 24h, 7d, 30d windows."""
    try:
        def _window_stats(hours: int) -> Dict[str, Any]:
            cutoff = now - timedelta(hours=hours)
            txns = (
                WhaleTransaction.query
                .filter(WhaleTransaction.detected_at >= cutoff)
                .all()
            )
            amounts = [t.btc_amount for t in txns if t.btc_amount]
            count = len(amounts)
            total = sum(amounts)
            avg = _mean(amounts) if amounts else 0.0
            mega_count = sum(1 for t in txns if getattr(t, "is_mega", False))
            return {
                "count": count,
                "total_btc": round(total, 4),
                "avg_btc": round(avg, 4),
                "mega_count": mega_count,
            }

        w_24h = _window_stats(24)
        w_7d = _window_stats(24 * 7)
        w_30d = _window_stats(24 * 30)

        # Trend detection: compare daily rate 7d vs 30d
        daily_7d = w_7d["count"] / 7.0 if w_7d["count"] else 0
        daily_30d = w_30d["count"] / 30.0 if w_30d["count"] else 0

        if daily_30d > 0:
            ratio = daily_7d / daily_30d
        else:
            ratio = 1.0

        if ratio > 1.25:
            activity_trend = "INCREASING"
        elif ratio < 0.75:
            activity_trend = "DECREASING"
        else:
            activity_trend = "STABLE"

        return {
            "windows": {
                "24h": w_24h,
                "7d": w_7d,
                "30d": w_30d,
            },
            "trend": activity_trend,
            "daily_rate_7d": round(daily_7d, 2),
            "daily_rate_30d": round(daily_30d, 2),
        }
    except Exception as exc:
        logger.error("Whale activity trend failed: %s", exc)
        return {
            "windows": {"24h": {}, "7d": {}, "30d": {}},
            "trend": "UNKNOWN",
            "daily_rate_7d": 0,
            "daily_rate_30d": 0,
        }


def _build_market_correlation(
    SentimentSnapshot, Article, now: datetime
) -> Dict[str, Any]:
    """Correlate sentiment with article volume to derive a market signal.

    Higher article volume + positive sentiment = BULLISH signal.
    """
    try:
        cutoff = now - timedelta(days=14)

        # Daily sentiment averages
        sent_rows = (
            db.session.query(
                cast(SentimentSnapshot.created_at, Date).label("day"),
                func.avg(SentimentSnapshot.score).label("avg_score"),
            )
            .filter(SentimentSnapshot.created_at >= cutoff)
            .group_by(cast(SentimentSnapshot.created_at, Date))
            .order_by("day")
            .all()
        )

        # Daily article counts
        art_rows = (
            db.session.query(
                cast(Article.created_at, Date).label("day"),
                func.count(Article.id).label("cnt"),
            )
            .filter(Article.created_at >= cutoff, Article.published == True)
            .group_by(cast(Article.created_at, Date))
            .order_by("day")
            .all()
        )

        sent_by_day = {
            (r.day.isoformat() if hasattr(r.day, "isoformat") else str(r.day)): float(r.avg_score)
            for r in sent_rows
        }
        art_by_day = {
            (r.day.isoformat() if hasattr(r.day, "isoformat") else str(r.day)): r.cnt
            for r in art_rows
        }

        all_days = sorted(set(sent_by_day.keys()) | set(art_by_day.keys()))

        sentiment_values = [sent_by_day.get(d, 50.0) for d in all_days]
        volume_values = [float(art_by_day.get(d, 0)) for d in all_days]

        # Pearson correlation (manual)
        correlation = _pearson_correlation(sentiment_values, volume_values)

        avg_sentiment = _mean(sentiment_values)
        avg_volume = _mean(volume_values)

        # Signal logic: sentiment above neutral (50) and volume above average
        recent_sentiment = _mean(sentiment_values[-7:]) if len(sentiment_values) >= 7 else avg_sentiment
        recent_volume = _mean(volume_values[-7:]) if len(volume_values) >= 7 else avg_volume

        if recent_sentiment > 60 and recent_volume > avg_volume:
            signal = "BULLISH"
        elif recent_sentiment < 40 and recent_volume > avg_volume:
            signal = "BEARISH"
        elif recent_sentiment > 55:
            signal = "SLIGHTLY_BULLISH"
        elif recent_sentiment < 45:
            signal = "SLIGHTLY_BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "signal": signal,
            "correlation": round(correlation, 4),
            "avg_sentiment_14d": round(avg_sentiment, 2),
            "avg_volume_14d": round(avg_volume, 2),
            "recent_sentiment_7d": round(recent_sentiment, 2),
            "recent_volume_7d": round(recent_volume, 2),
            "data_points": len(all_days),
        }
    except Exception as exc:
        logger.error("Market correlation analysis failed: %s", exc)
        return {
            "signal": "NEUTRAL",
            "correlation": 0.0,
            "avg_sentiment_14d": 50.0,
            "avg_volume_14d": 0,
            "recent_sentiment_7d": 50.0,
            "recent_volume_7d": 0,
            "data_points": 0,
        }


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient between two equal-length lists."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x = x[:n]
    y = y[:n]
    x_mean = _mean(x)
    y_mean = _mean(y)
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denom_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def _build_forecast_summary(result: Dict[str, Any]) -> str:
    """Generate a 3-5 sentence text summary of the overall forecast."""
    parts: List[str] = []

    # Sentiment
    sent = result.get("sentiment_trend", {})
    trend = sent.get("trend", "NEUTRAL")
    score = sent.get("current_score")
    if score is not None:
        parts.append(
            f"Market sentiment is currently {trend.lower()} with a latest score of {score:.1f}/100."
        )
    else:
        parts.append("Insufficient sentiment data is available for trend analysis.")

    # Topic forecast
    topics = result.get("topic_forecast", [])
    if topics:
        top_names = [t["topic"] for t in topics[:3]]
        parts.append(
            f"Trending topics gaining momentum include {', '.join(top_names)}."
        )

    # Whale activity
    whale = result.get("whale_activity_trend", {})
    whale_trend = whale.get("trend", "UNKNOWN")
    w24 = whale.get("windows", {}).get("24h", {})
    if w24.get("count", 0) > 0:
        parts.append(
            f"Whale activity is {whale_trend.lower()} with {w24['count']} large transactions "
            f"totalling {w24.get('total_btc', 0):.2f} BTC in the last 24 hours."
        )
    else:
        parts.append(f"Whale transaction activity is {whale_trend.lower()} over recent windows.")

    # Market correlation
    corr = result.get("market_correlation", {})
    signal = corr.get("signal", "NEUTRAL")
    parts.append(f"The combined market signal based on sentiment-volume correlation is {signal}.")

    # Content velocity
    velocity = result.get("content_velocity", {})
    hottest = velocity.get("hottest_category")
    if hottest:
        parts.append(f"The most active content category is \"{hottest}\".")

    return " ".join(parts)


# ===========================================================================
# 2. get_sentiment_timeline(days=30)
# ===========================================================================

def get_sentiment_timeline(days: int = 30) -> List[Dict[str, Any]]:
    """Return daily sentiment scores with labels and 7-day moving average.

    Format: [{date, score, label, ma_7d}, ...]
    Results are cached for 10 minutes.
    """
    cache_key = f"sentiment_timeline_{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    _, SentimentSnapshot, _, _ = _get_models()

    try:
        now = datetime.utcnow()
        cutoff = now - timedelta(days=days)

        rows = (
            db.session.query(
                cast(SentimentSnapshot.created_at, Date).label("day"),
                func.avg(SentimentSnapshot.score).label("avg_score"),
            )
            .filter(SentimentSnapshot.created_at >= cutoff)
            .group_by(cast(SentimentSnapshot.created_at, Date))
            .order_by("day")
            .all()
        )

        if not rows:
            return []

        scores = [float(r.avg_score) for r in rows]
        ma_7d = _moving_average(scores, window=7)

        timeline = []
        for i, row in enumerate(rows):
            score_val = round(scores[i], 2)
            # Derive a human label from the score (0-100 scale, 50 = neutral)
            if score_val >= 70:
                label = "VERY_BULLISH"
            elif score_val >= 55:
                label = "BULLISH"
            elif score_val >= 45:
                label = "NEUTRAL"
            elif score_val >= 30:
                label = "BEARISH"
            else:
                label = "VERY_BEARISH"

            day_str = row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day)

            timeline.append({
                "date": day_str,
                "score": score_val,
                "label": label,
                "ma_7d": round(ma_7d[i], 2) if ma_7d[i] is not None else None,
            })

        _cache_set(cache_key, timeline)
        return timeline
    except Exception as exc:
        logger.error("Sentiment timeline failed: %s", exc)
        return []


# ===========================================================================
# 3. predict_engagement(title, category, tags)
# ===========================================================================

def predict_engagement(
    title: str, category: str = "", tags: str = ""
) -> Dict[str, Any]:
    """Predict article engagement before publishing.

    Returns:
        {score: 0-100, factors: [{name, value, impact}], suggestions: [str]}
    Results are cached for 10 minutes keyed on input parameters.
    """
    cache_key = f"predict_engagement:{title}:{category}:{tags}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    Article, _, _, _ = _get_models()

    now = datetime.utcnow()

    # -- Category popularity ------------------------------------------------
    try:
        cat_cutoff = now - timedelta(days=30)
        cat_rows = (
            db.session.query(
                Article.category,
                func.count(Article.id).label("cnt"),
            )
            .filter(Article.created_at >= cat_cutoff, Article.published == True)
            .group_by(Article.category)
            .all()
        )
        max_cat = max((r.cnt for r in cat_rows), default=1) or 1
        cat_popularity = {
            (r.category or ""): r.cnt / max_cat for r in cat_rows
        }
    except Exception:
        cat_popularity = {}

    # -- Recent tag frequency -----------------------------------------------
    try:
        tag_cutoff = now - timedelta(days=7)
        recent_arts = (
            Article.query
            .filter(Article.created_at >= tag_cutoff, Article.published == True)
            .all()
        )
        recent_tags: Dict[str, int] = defaultdict(int)
        for art in recent_arts:
            for t in (art.tags or "").split(","):
                t = t.strip().lower()
                if t:
                    recent_tags[t] += 1
    except Exception:
        recent_tags = {}

    score, factors = _score_article_engagement(
        title=title,
        category=category,
        tags=tags,
        cat_popularity=cat_popularity,
        recent_tags=recent_tags,
    )

    # -- Suggestions --------------------------------------------------------
    suggestions = _generate_suggestions(title, category, tags, factors)

    result = {
        "score": score,
        "factors": factors,
        "suggestions": suggestions,
    }

    _cache_set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Shared engagement scoring logic
# ---------------------------------------------------------------------------

def _score_article_engagement(
    title: str,
    category: str,
    tags: str,
    cat_popularity: Dict[str, float],
    recent_tags: Dict[str, int],
) -> Tuple[int, List[Dict[str, Any]]]:
    """Score 0-100 with per-factor breakdown.

    Factors (each contributes to a weighted total):
      - title_length:    optimal 40-70 chars
      - has_numbers:     presence of digits in title
      - has_question:    title ends with ?
      - emotional_words: count of emotional/power words
      - category_pop:    popularity of the category (30d)
      - tag_recency:     how trending the tags are (7d)
      - title_words:     penalise very short or very long titles
    """
    factors: List[Dict[str, Any]] = []
    weighted_sum = 0.0
    total_weight = 0.0

    title_clean = title.strip()
    title_lower = title_clean.lower()
    title_len = len(title_clean)
    title_words = title_lower.split()

    # 1. Title length (weight 20) ------------------------------------------
    weight = 20
    if 40 <= title_len <= 70:
        value = 1.0
    elif 30 <= title_len < 40 or 70 < title_len <= 90:
        value = 0.7
    elif 20 <= title_len < 30 or 90 < title_len <= 120:
        value = 0.4
    else:
        value = 0.2
    impact = round(value * weight, 1)
    factors.append({"name": "title_length", "value": title_len, "impact": impact})
    weighted_sum += value * weight
    total_weight += weight

    # 2. Has numbers (weight 10) -------------------------------------------
    weight = 10
    has_num = any(ch.isdigit() for ch in title_clean)
    value = 1.0 if has_num else 0.3
    impact = round(value * weight, 1)
    factors.append({"name": "has_numbers", "value": has_num, "impact": impact})
    weighted_sum += value * weight
    total_weight += weight

    # 3. Has question mark (weight 10) -------------------------------------
    weight = 10
    has_q = title_clean.endswith("?")
    value = 1.0 if has_q else 0.4
    impact = round(value * weight, 1)
    factors.append({"name": "has_question", "value": has_q, "impact": impact})
    weighted_sum += value * weight
    total_weight += weight

    # 4. Emotional / power words (weight 20) -------------------------------
    weight = 20
    emotional_count = sum(
        1 for w in title_words if w.strip(".,!?:;\"'") in _EMOTIONAL_WORDS
    )
    power_count = sum(
        1 for w in title_words if w.strip(".,!?:;\"'") in _POWER_WORDS
    )
    word_score = min(emotional_count + power_count, 5) / 5.0
    value = max(word_score, 0.15)  # baseline even with no trigger words
    impact = round(value * weight, 1)
    factors.append({
        "name": "emotional_words",
        "value": emotional_count + power_count,
        "impact": impact,
    })
    weighted_sum += value * weight
    total_weight += weight

    # 5. Category popularity (weight 20) -----------------------------------
    weight = 20
    cat_score = cat_popularity.get(category, cat_popularity.get(category.strip(), 0.3))
    value = _clamp(cat_score, 0.1, 1.0)
    impact = round(value * weight, 1)
    factors.append({"name": "category_popularity", "value": round(cat_score, 2), "impact": impact})
    weighted_sum += value * weight
    total_weight += weight

    # 6. Tag recency (weight 20) -------------------------------------------
    weight = 20
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
    if tag_list and recent_tags:
        max_tag_freq = max(recent_tags.values(), default=1) or 1
        tag_scores = [recent_tags.get(t, 0) / max_tag_freq for t in tag_list]
        value = _clamp(_mean(tag_scores), 0.1, 1.0)
    elif tag_list:
        value = 0.3  # tags present but no recent data
    else:
        value = 0.15  # no tags at all
    impact = round(value * weight, 1)
    factors.append({"name": "tag_recency", "value": round(value, 2), "impact": impact})
    weighted_sum += value * weight
    total_weight += weight

    # Final score 0-100
    raw = (weighted_sum / total_weight) * 100 if total_weight > 0 else 50
    score = int(_clamp(round(raw), 0, 100))

    return score, factors


def _generate_suggestions(
    title: str,
    category: str,
    tags: str,
    factors: List[Dict[str, Any]],
) -> List[str]:
    """Generate actionable suggestions based on the factor scores."""
    suggestions: List[str] = []
    factor_map = {f["name"]: f for f in factors}

    # Title length
    tl = factor_map.get("title_length", {})
    tl_val = tl.get("value", 0)
    if isinstance(tl_val, (int, float)) and tl_val < 40:
        suggestions.append(
            "Consider a longer title (40-70 characters is optimal for engagement)."
        )
    elif isinstance(tl_val, (int, float)) and tl_val > 70:
        suggestions.append(
            "Your title may be too long. Aim for 40-70 characters for best click-through."
        )

    # Numbers
    if not factor_map.get("has_numbers", {}).get("value"):
        suggestions.append(
            "Including a number in your title (e.g., '5 Reasons...', '$100K...') can boost engagement."
        )

    # Question
    if not factor_map.get("has_question", {}).get("value"):
        suggestions.append(
            "Question-style titles ('Will Bitcoin...?') tend to drive higher click-through rates."
        )

    # Emotional words
    ew = factor_map.get("emotional_words", {})
    if ew.get("value", 0) == 0:
        suggestions.append(
            "Add impactful words (e.g., 'breaking', 'surge', 'critical') to make the title more compelling."
        )

    # Tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    if not tag_list:
        suggestions.append(
            "Add relevant tags to improve discoverability and topic matching."
        )

    # Category
    cp = factor_map.get("category_popularity", {})
    if cp.get("value", 0) < 0.3 and category:
        suggestions.append(
            f"The category \"{category}\" has lower recent activity. "
            "Consider a more popular category or cross-tagging with trending topics."
        )

    # Cap at 5 suggestions
    return suggestions[:5]
