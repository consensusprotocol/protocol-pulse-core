"""
Content Analytics & Insights Engine - Protocol Pulse

Lightweight, file-based analytics for website content engagement.
Tracks pageviews, scroll depth, time-on-page, and derives insights
without requiring database migrations.

Storage: data/content_analytics.jsonl (append-only JSON-lines)
Cache:   In-memory dict with 5-minute TTL
"""

import json
import logging
import os
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE_DIR / "data"
_JSONL_PATH = _DATA_DIR / "content_analytics.jsonl"

_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 300  # 5 minutes
_WRITE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    """Create the data directory if it does not already exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _parse_device(user_agent: Optional[str]) -> str:
    """Classify a User-Agent string into mobile / tablet / desktop.

    Uses simple substring matching so we avoid pulling in an external
    library.  Covers the vast majority of real-world traffic.
    """
    if not user_agent:
        return "unknown"
    ua = user_agent.lower()
    # Tablets first (some tablet UAs also contain "mobile")
    if "ipad" in ua or "tablet" in ua or "kindle" in ua or "silk" in ua:
        return "tablet"
    if ("mobile" in ua or "android" in ua or "iphone" in ua
            or "ipod" in ua or "opera mini" in ua or "opera mobi" in ua):
        return "mobile"
    return "desktop"


def _clean_referrer(referrer: Optional[str]) -> str:
    """Normalise a referrer to its domain or a short label."""
    if not referrer:
        return "direct"
    referrer = referrer.strip()
    if not referrer or referrer == "-":
        return "direct"
    # Strip protocol
    for prefix in ("https://", "http://"):
        if referrer.startswith(prefix):
            referrer = referrer[len(prefix):]
            break
    # Strip www.
    if referrer.startswith("www."):
        referrer = referrer[4:]
    # Keep only the domain (drop path)
    domain = referrer.split("/")[0].split("?")[0]
    return domain or "direct"


def _cache_get(key: str) -> Optional[Any]:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.time() > expires_at:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any):
    _CACHE[key] = (value, time.time() + _CACHE_TTL)


def _read_events(since: Optional[datetime] = None) -> List[Dict]:
    """Read events from the JSONL file, optionally filtering by timestamp."""
    events: List[Dict] = []
    if not _JSONL_PATH.exists():
        return events
    cutoff_iso = since.isoformat() if since else None
    try:
        with open(_JSONL_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if cutoff_iso and evt.get("timestamp", "") < cutoff_iso:
                    continue
                events.append(evt)
    except Exception as exc:
        logger.error(f"Failed to read analytics JSONL: {exc}")
    return events


# ---------------------------------------------------------------------------
# 1. track_event
# ---------------------------------------------------------------------------

def track_event(data: Dict) -> Dict[str, Any]:
    """Record a content analytics event.

    Parameters (in *data*):
        path          - URL path viewed
        visitor_hash  - anonymised visitor identifier
        user_agent    - raw User-Agent header
        referrer      - HTTP Referer header
        event_type    - one of: pageview, scroll, time
        scroll_depth  - 0-100 percentage (for scroll events)
        time_on_page  - seconds spent (for time events)
        article_id    - associated Article PK (optional)

    The event is appended to ``data/content_analytics.jsonl`` and, for
    pageview events, the Article.views counter is incremented when the
    column exists on the model.
    """
    _ensure_data_dir()

    event_type = (data.get("event_type") or "pageview").lower()
    now = datetime.utcnow()

    record = {
        "timestamp": now.isoformat(),
        "path": data.get("path", "/"),
        "visitor_hash": data.get("visitor_hash", ""),
        "user_agent": data.get("user_agent", ""),
        "referrer": data.get("referrer", ""),
        "event_type": event_type,
        "scroll_depth": _clamp(data.get("scroll_depth"), 0, 100),
        "time_on_page": max(0, int(data.get("time_on_page") or 0)),
        "article_id": data.get("article_id"),
        "device": _parse_device(data.get("user_agent")),
    }

    # ---- Append to JSONL (thread-safe) ----
    try:
        with _WRITE_LOCK:
            with open(_JSONL_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        logger.error(f"content_analytics: failed to write event: {exc}")
        return {"ok": False, "error": str(exc)}

    # ---- Bump Article.views for pageview events ----
    if event_type == "pageview" and data.get("article_id"):
        _bump_article_views(data["article_id"])

    # Invalidate cached insights so the next call picks up fresh data
    _CACHE.clear()

    return {"ok": True, "event_type": event_type, "timestamp": record["timestamp"]}


def _clamp(value, lo, hi):
    """Clamp a numeric value (or None) between lo and hi."""
    if value is None:
        return 0
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 0
    return max(lo, min(hi, v))


def _bump_article_views(article_id):
    """Increment Article.views if the column exists; silently skip otherwise."""
    try:
        from app import db
        from models import Article

        article = db.session.get(Article, int(article_id))
        if article is None:
            return
        # The Article model may or may not have a 'views' column.
        if hasattr(article, "views") and article.views is not None:
            article.views = (article.views or 0) + 1
        elif hasattr(article, "views"):
            article.views = 1
        else:
            # No views column on this schema version -- skip gracefully.
            return
        db.session.commit()
    except Exception as exc:
        logger.warning(f"content_analytics: could not bump article views: {exc}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 2. get_insights
# ---------------------------------------------------------------------------

def get_insights(days: int = 30) -> Dict[str, Any]:
    """Aggregate content analytics insights over the last *days* days.

    Returns a dictionary suitable for an admin dashboard, including:
        - total_views, unique_visitors, avg_time_on_page, avg_scroll_depth
        - top_articles   (by pageview count)
        - top_referrers
        - device_breakdown  (mobile / desktop / tablet / unknown)
        - views_by_day      (for time-series charts)
        - trending_topics   (article categories read most)
        - content_gaps      (categories with few articles but high views)
    """
    cache_key = f"insights_{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(days=days)
    events = _read_events(since=since)

    # --- Base counters ---
    pageviews = [e for e in events if e.get("event_type") == "pageview"]
    time_events = [e for e in events if e.get("event_type") == "time"]
    scroll_events = [e for e in events if e.get("event_type") == "scroll"]

    total_views = len(pageviews)
    unique_visitors = len({e.get("visitor_hash") for e in pageviews if e.get("visitor_hash")})

    avg_time = 0.0
    if time_events:
        avg_time = round(
            sum(e.get("time_on_page", 0) for e in time_events) / len(time_events), 1
        )

    avg_scroll = 0.0
    if scroll_events:
        avg_scroll = round(
            sum(e.get("scroll_depth", 0) for e in scroll_events) / len(scroll_events), 1
        )

    # --- Top articles ---
    article_counter: Counter = Counter()
    article_titles: Dict[int, str] = {}
    for e in pageviews:
        aid = e.get("article_id")
        if aid is not None:
            aid = int(aid)
            article_counter[aid] += 1

    # Attempt to resolve titles from the database
    try:
        from models import Article
        for aid in list(article_counter.keys()):
            art = Article.query.get(aid)
            if art:
                article_titles[aid] = art.title
    except Exception:
        pass

    top_articles = [
        {
            "article_id": aid,
            "title": article_titles.get(aid, f"Article #{aid}"),
            "views": count,
        }
        for aid, count in article_counter.most_common(15)
    ]

    # --- Top referrers ---
    ref_counter: Counter = Counter()
    for e in pageviews:
        ref_counter[_clean_referrer(e.get("referrer"))] += 1
    top_referrers = [
        {"referrer": ref, "views": cnt}
        for ref, cnt in ref_counter.most_common(15)
    ]

    # --- Device breakdown ---
    device_counter: Counter = Counter()
    for e in pageviews:
        device_counter[e.get("device", _parse_device(e.get("user_agent")))] += 1
    device_breakdown = {dev: cnt for dev, cnt in device_counter.most_common()}

    # --- Views by day ---
    day_counter: Counter = Counter()
    for e in pageviews:
        ts = e.get("timestamp", "")
        day_str = ts[:10]  # YYYY-MM-DD
        if day_str:
            day_counter[day_str] += 1
    views_by_day = [
        {"date": d, "views": c}
        for d, c in sorted(day_counter.items())
    ]

    # --- Trending topics (categories being read most) ---
    category_views: Counter = Counter()
    try:
        from models import Article
        for aid, count in article_counter.items():
            art = Article.query.get(aid)
            if art and art.category:
                category_views[art.category] += count
    except Exception:
        pass
    trending_topics = [
        {"category": cat, "views": cnt}
        for cat, cnt in category_views.most_common(10)
    ]

    # --- Content gap suggestions ---
    content_gaps = _compute_content_gaps(category_views)

    result = {
        "period_days": days,
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "avg_time_on_page": avg_time,
        "avg_scroll_depth": avg_scroll,
        "top_articles": top_articles,
        "top_referrers": top_referrers,
        "device_breakdown": device_breakdown,
        "views_by_day": views_by_day,
        "trending_topics": trending_topics,
        "content_gaps": content_gaps,
        "generated_at": datetime.utcnow().isoformat(),
    }

    _cache_set(cache_key, result)
    return result


def _compute_content_gaps(category_views: Counter) -> List[Dict]:
    """Find categories with high reader demand but low article supply.

    A "gap" is a category whose views-per-article ratio is notably higher
    than the overall average, suggesting readers want more content there.
    """
    gaps: List[Dict] = []
    try:
        from models import Article
        from sqlalchemy import func as sa_func
        from app import db

        rows = (
            db.session.query(Article.category, sa_func.count(Article.id))
            .filter(Article.published == True)
            .group_by(Article.category)
            .all()
        )
        article_counts = {cat: cnt for cat, cnt in rows if cat}
    except Exception:
        article_counts = {}

    if not article_counts or not category_views:
        return gaps

    # Compute views-per-article for each category
    ratios: Dict[str, float] = {}
    for cat, views in category_views.items():
        count = article_counts.get(cat, 0)
        if count > 0:
            ratios[cat] = views / count

    if not ratios:
        return gaps

    avg_ratio = sum(ratios.values()) / len(ratios)

    for cat, ratio in sorted(ratios.items(), key=lambda x: -x[1]):
        if ratio > avg_ratio * 1.3:
            gaps.append({
                "category": cat,
                "article_count": article_counts.get(cat, 0),
                "views": category_views.get(cat, 0),
                "views_per_article": round(ratio, 1),
                "suggestion": f"Readers want more '{cat}' content -- high demand vs supply.",
            })
    return gaps[:10]


# ---------------------------------------------------------------------------
# 3. get_article_analytics
# ---------------------------------------------------------------------------

def get_article_analytics(article_id: int) -> Dict[str, Any]:
    """Return detailed analytics for a single article.

    Includes:
        - views_over_time    (daily view counts)
        - avg_scroll_depth
        - avg_time_on_page
        - referrer_breakdown
        - device_breakdown
        - total_views
    """
    cache_key = f"article_{article_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    article_id = int(article_id)
    all_events = _read_events()
    events = [e for e in all_events if _safe_int(e.get("article_id")) == article_id]

    if not events:
        result = _empty_article_analytics(article_id)
        _cache_set(cache_key, result)
        return result

    pageviews = [e for e in events if e.get("event_type") == "pageview"]
    time_events = [e for e in events if e.get("event_type") == "time"]
    scroll_events = [e for e in events if e.get("event_type") == "scroll"]

    total_views = len(pageviews)

    # --- Views over time ---
    day_counter: Counter = Counter()
    for e in pageviews:
        day_str = e.get("timestamp", "")[:10]
        if day_str:
            day_counter[day_str] += 1
    views_over_time = [
        {"date": d, "views": c}
        for d, c in sorted(day_counter.items())
    ]

    # --- Avg scroll depth ---
    avg_scroll = 0.0
    if scroll_events:
        avg_scroll = round(
            sum(e.get("scroll_depth", 0) for e in scroll_events) / len(scroll_events), 1
        )

    # --- Avg time on page ---
    avg_time = 0.0
    if time_events:
        avg_time = round(
            sum(e.get("time_on_page", 0) for e in time_events) / len(time_events), 1
        )

    # --- Referrer breakdown ---
    ref_counter: Counter = Counter()
    for e in pageviews:
        ref_counter[_clean_referrer(e.get("referrer"))] += 1
    referrer_breakdown = [
        {"referrer": ref, "views": cnt}
        for ref, cnt in ref_counter.most_common(15)
    ]

    # --- Device breakdown ---
    device_counter: Counter = Counter()
    for e in pageviews:
        device_counter[e.get("device", _parse_device(e.get("user_agent")))] += 1
    device_breakdown = {dev: cnt for dev, cnt in device_counter.most_common()}

    # --- Resolve title ---
    title = f"Article #{article_id}"
    try:
        from models import Article
        art = Article.query.get(article_id)
        if art:
            title = art.title
    except Exception:
        pass

    result = {
        "article_id": article_id,
        "title": title,
        "total_views": total_views,
        "views_over_time": views_over_time,
        "avg_scroll_depth": avg_scroll,
        "avg_time_on_page": avg_time,
        "referrer_breakdown": referrer_breakdown,
        "device_breakdown": device_breakdown,
        "generated_at": datetime.utcnow().isoformat(),
    }

    _cache_set(cache_key, result)
    return result


def _empty_article_analytics(article_id: int) -> Dict[str, Any]:
    """Return a zeroed-out analytics payload when no events exist."""
    title = f"Article #{article_id}"
    try:
        from models import Article
        art = Article.query.get(article_id)
        if art:
            title = art.title
    except Exception:
        pass
    return {
        "article_id": article_id,
        "title": title,
        "total_views": 0,
        "views_over_time": [],
        "avg_scroll_depth": 0.0,
        "avg_time_on_page": 0.0,
        "referrer_breakdown": [],
        "device_breakdown": {},
        "generated_at": datetime.utcnow().isoformat(),
    }


def _safe_int(value) -> Optional[int]:
    """Attempt to cast a value to int; return None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
