"""
SESSION 10 — ARTICLE REBUILD: helpers + new API blueprint
Helper functions are imported by routes.py to enrich the existing page handlers.
New API endpoint /api/v2/articles is registered here as a Blueprint.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# ─── Article helper functions (imported by routes.py) ─────────────────────────

CATEGORY_COLORS: dict[str, str] = {
    "mining": "#f7931a",
    "regulation": "#dc2626",
    "etfs": "#3b82f6",
    "lightning": "#eab308",
    "macro": "#a855f7",
    "technical": "#06b6d4",
    "bitcoin": "#f97316",
    "editorial": "#10b981",
    "defi": "#6366f1",
    "web3": "#8b5cf6",
    "security": "#ef4444",
    "institutional": "#0ea5e9",
    "markets": "#14b8a6",
    "adoption": "#22c55e",
    "default": "#9ca3af",
}

CATEGORY_GRADIENTS: dict[str, str] = {
    "mining": "linear-gradient(135deg,#1a1200,#2d1e00)",
    "regulation": "linear-gradient(135deg,#1a0a0a,#2d1515)",
    "etfs": "linear-gradient(135deg,#0a1628,#0f2545)",
    "lightning": "linear-gradient(135deg,#1a1500,#2d2400)",
    "macro": "linear-gradient(135deg,#120a1a,#1f1030)",
    "technical": "linear-gradient(135deg,#0a1a1a,#0f2d2d)",
    "bitcoin": "linear-gradient(135deg,#1a0e00,#2d1800)",
    "editorial": "linear-gradient(135deg,#0a1a12,#0f2d1e)",
    "default": "linear-gradient(135deg,#0d0d1a,#1a1a2e)",
}

SENTIMENT_MAP: dict[str, dict] = {
    "bullish": {"label": "BULLISH", "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
    "bearish": {"label": "BEARISH", "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
    "neutral": {"label": "NEUTRAL", "color": "#6b7280", "bg": "rgba(107,114,128,0.12)"},
    "positive": {"label": "BULLISH", "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
    "negative": {"label": "BEARISH", "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
}

_BULLISH_SIGNALS = {
    "ath", "all-time high", "rally", "surge", "breakout", "adoption", "etf approved",
    "approval", "institutional", "accumulate", "bullish", "hodl", "all time high",
    "record", "positive", "growth", "expand", "partnership", "launch", "inflows",
}
_BEARISH_SIGNALS = {
    "ban", "crackdown", "hack", "exploit", "fraud", "scam", "crash", "dump",
    "lawsuit", "sec charges", "warning", "concern", "liquidation", "fud",
    "decline", "bearish", "sell-off", "capitulation", "regulation ban",
}


def article_get_image(article) -> str:
    """Return best available image URL. Returns empty string if none found (template handles fallback)."""
    for attr in ("cover_image_url", "header_image_url"):
        url = (getattr(article, attr, None) or "").strip()
        if url and url.startswith("http"):
            return url
        if url and url.startswith("/static/") and "default-header" not in url:
            return url
    return ""


def article_get_sentiment(article) -> dict:
    """Return sentiment dict: label, color, bg. Never crashes."""
    try:
        reports = getattr(article, "sentiment_report", None)
        if reports:
            if isinstance(reports, list) and reports:
                report = sorted(reports, key=lambda r: r.id, reverse=True)[0]
            else:
                report = reports
            if report:
                if report.overall_sentiment:
                    key = report.overall_sentiment.lower().strip()
                    if key in SENTIMENT_MAP:
                        return SENTIMENT_MAP[key]
                if report.sentiment_score is not None:
                    if report.sentiment_score > 55:
                        return SENTIMENT_MAP["bullish"]
                    if report.sentiment_score < 40:
                        return SENTIMENT_MAP["bearish"]
                    return SENTIMENT_MAP["neutral"]
    except Exception:
        pass

    # Keyword inference from title + summary + tags
    text = " ".join([
        (getattr(article, "title", None) or ""),
        (getattr(article, "summary", None) or "")[:200],
        (getattr(article, "tags", None) or ""),
    ]).lower()
    bull = sum(1 for w in _BULLISH_SIGNALS if w in text)
    bear = sum(1 for w in _BEARISH_SIGNALS if w in text)
    if bull > bear and bull >= 2:
        return SENTIMENT_MAP["bullish"]
    if bear > bull and bear >= 2:
        return SENTIMENT_MAP["bearish"]
    return SENTIMENT_MAP["neutral"]


def article_get_read_time(article) -> int:
    """Estimate read time in minutes at 200 wpm."""
    content = getattr(article, "content", None) or ""
    word_count = len(re.sub(r"<[^>]+>", "", content).split())
    return max(1, round(word_count / 200))


def article_get_related(article, db, Article, limit: int = 3) -> list:
    """Always returns `limit` articles. Same category first, then any recent."""
    related = []
    try:
        if article.category:
            related = (
                Article.query
                .filter(
                    Article.id != article.id,
                    Article.published.is_(True),
                    Article.category == article.category,
                )
                .order_by(Article.created_at.desc())
                .limit(limit)
                .all()
            )
        if len(related) < limit:
            exc_ids = [article.id] + [r.id for r in related]
            pad = (
                Article.query
                .filter(
                    ~Article.id.in_(exc_ids),
                    Article.published.is_(True),
                )
                .order_by(Article.created_at.desc())
                .limit(limit - len(related))
                .all()
            )
            related.extend(pad)
    except Exception as exc:
        logger.warning("article_get_related failed: %s", exc)
    return related[:limit]


def article_cat_color(category: str | None) -> str:
    key = (category or "default").lower()
    return CATEGORY_COLORS.get(key, CATEGORY_COLORS["default"])


def article_cat_gradient(category: str | None) -> str:
    key = (category or "default").lower()
    return CATEGORY_GRADIENTS.get(key, CATEGORY_GRADIENTS["default"])


def build_article_data(articles, sentiment_fn=None, img_fn=None) -> list[dict]:
    """Build article_data list for template rendering."""
    result = []
    for a in articles:
        result.append({
            "article": a,
            "image_url": article_get_image(a),
            "sentiment": article_get_sentiment(a),
            "read_time": article_get_read_time(a),
            "cat_color": article_cat_color(a.category),
            "cat_gradient": article_cat_gradient(a.category),
        })
    return result


# ─── Blueprint: new JSON API endpoint ─────────────────────────────────────────

articles_api_bp = Blueprint("articles_api_bp", __name__)


@articles_api_bp.route("/api/v2/articles")
def api_v2_articles():
    """
    Articles JSON API — paginated, filterable, searchable.
    Supports: ?page=N&per_page=24&category=Mining&q=searchterm
    Used by the Load More button and client-side search on /articles.
    """
    from app import db
    from models import Article

    try:
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(48, request.args.get("per_page", 24, type=int))
        category = request.args.get("category", "").strip()
        search = request.args.get("q", "").strip()

        q = Article.query.filter(Article.published.is_(True))
        total = q.count()
        if total == 0:  # dev fallback
            q = Article.query
            total = q.count()

        if category and category.lower() != "all":
            q = q.filter(Article.category.ilike(f"%{category}%"))

        if search:
            like = f"%{search}%"
            q = q.filter(
                db.or_(
                    Article.title.ilike(like),
                    Article.summary.ilike(like),
                    Article.tags.ilike(like),
                )
            )

        q = q.order_by(Article.created_at.desc())
        paged = q.paginate(page=page, per_page=per_page, error_out=False)

        def to_dict(a):
            img = article_get_image(a)
            sent = article_get_sentiment(a)
            return {
                "id": a.id,
                "title": a.title or "",
                "summary": (a.summary or re.sub(r"<[^>]+>", "", a.content or "")[:280]),
                "category": a.category or "Bitcoin",
                "category_color": article_cat_color(a.category),
                "category_gradient": article_cat_gradient(a.category),
                "image_url": img,
                "sentiment_label": sent["label"],
                "sentiment_color": sent["color"],
                "sentiment_bg": sent["bg"],
                "source": a.author or a.source_type or "Protocol Pulse",
                "read_time": article_get_read_time(a),
                "created_at": a.created_at.isoformat() if a.created_at else "",
                "url": f"/articles/{a.id}",
                "is_featured": bool(a.featured),
            }

        return jsonify({
            "articles": [to_dict(a) for a in paged.items],
            "page": page,
            "per_page": per_page,
            "total": paged.total,
            "total_pages": paged.pages,
            "has_more": paged.has_next,
        })
    except Exception as err:
        logger.error("api_v2_articles error: %s", err)
        return jsonify({"articles": [], "error": str(err), "has_more": False}), 500
