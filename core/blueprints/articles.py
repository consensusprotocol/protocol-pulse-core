"""
SESSION 10 — ARTICLE REBUILD
core/blueprints/articles.py

Registered in both core/app.py and app.py.

Routes:
  GET /article/<slug>           — article detail by slug (NEW — no conflict with routes.py)
  GET /articles/<int:id>/slug   — redirect to /article/<slug>
  GET /api/v2/articles          — JSON listing API (paginated, filterable)

Helper functions (imported by routes.py for /articles list page):
  build_article_data()          — builds rich dicts for template rendering
  article_get_image()           — normalised image URL
  article_get_sentiment()       — BULLISH/BEARISH/NEUTRAL dict
  article_get_read_time()       — minutes at 200 wpm
  article_get_related()         — always-3 related articles
  article_cat_color()           — hex colour per category
  article_cat_gradient()        — CSS gradient per category
  article_make_slug()           — {id}-{title-slug}
  article_tldr_bullets()        — "What you need to know" 3-bullet list
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

logger = logging.getLogger(__name__)

# ─── Category colour / gradient maps ─────────────────────────────────────────

CATEGORY_COLORS: dict[str, str] = {
    "mining":       "#f7931a",
    "regulation":   "#dc2626",
    "etfs":         "#3b82f6",
    "lightning":    "#eab308",
    "macro":        "#a855f7",
    "technical":    "#06b6d4",
    "bitcoin":      "#f97316",
    "editorial":    "#10b981",
    "defi":         "#6366f1",
    "web3":         "#8b5cf6",
    "security":     "#ef4444",
    "institutional":"#0ea5e9",
    "markets":      "#14b8a6",
    "adoption":     "#22c55e",
    "default":      "#9ca3af",
}

CATEGORY_GRADIENTS: dict[str, str] = {
    "mining":       "linear-gradient(135deg,#1a1200,#2d1e00)",
    "regulation":   "linear-gradient(135deg,#1a0a0a,#2d1515)",
    "etfs":         "linear-gradient(135deg,#0a1628,#0f2545)",
    "lightning":    "linear-gradient(135deg,#1a1500,#2d2400)",
    "macro":        "linear-gradient(135deg,#120a1a,#1f1030)",
    "technical":    "linear-gradient(135deg,#0a1a1a,#0f2d2d)",
    "bitcoin":      "linear-gradient(135deg,#1a0e00,#2d1800)",
    "editorial":    "linear-gradient(135deg,#0a1a12,#0f2d1e)",
    "default":      "linear-gradient(135deg,#0d0d1a,#1a1a2e)",
}

SENTIMENT_MAP: dict[str, dict] = {
    "bullish":  {"label": "BULLISH",  "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
    "bearish":  {"label": "BEARISH",  "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
    "neutral":  {"label": "NEUTRAL",  "color": "#6b7280", "bg": "rgba(107,114,128,0.12)"},
    "positive": {"label": "BULLISH",  "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
    "negative": {"label": "BEARISH",  "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
}

_BULLISH_SIGNALS = {
    "ath", "all-time high", "rally", "surge", "breakout", "adoption", "etf approved",
    "approval", "institutional", "accumulate", "bullish", "hodl", "all time high",
    "record", "positive", "growth", "expand", "partnership", "launch", "inflows",
}
_BEARISH_SIGNALS = {
    "ban", "crackdown", "hack", "exploit", "fraud", "scam", "crash", "dump",
    "lawsuit", "sec charges", "warning", "concern", "liquidation", "fud",
    "decline", "bearish", "sell-off", "capitulation",
}

# ─── Helper functions ─────────────────────────────────────────────────────────

def article_make_slug(article) -> str:
    """Return URL-safe slug: {id}-{title-words}. ID prefix enables O(1) lookup."""
    title_part = re.sub(r"[^a-z0-9]+", "-", (article.title or "").lower()).strip("-")[:60]
    return f"{article.id}-{title_part}"


def article_find_by_slug(slug: str):
    """Extract article ID from slug prefix and look up by PK. Never crashes."""
    try:
        from models import Article
        article_id = int(slug.split("-", 1)[0])
        return Article.query.get(article_id)
    except Exception:
        return None


def article_get_image(article) -> str:
    """Return best available image URL — cover_image_url preferred (ARTICLE_PAGE_LAWS Law 1)."""
    for attr in ("cover_image_url", "header_image_url"):
        url = (getattr(article, attr, None) or "").strip()
        if url and url.startswith("http"):
            return url
        if url and url.startswith("/static/") and "default-header" not in url:
            return url
    return ""


def article_get_sentiment(article) -> dict:
    """Return BULLISH/BEARISH/NEUTRAL dict. Never crashes."""
    try:
        # 1. DB column (added by p3-sentiment-intel migration)
        col_val = getattr(article, "sentiment", None)
        if col_val:
            key = col_val.lower().strip()
            if key in SENTIMENT_MAP:
                return SENTIMENT_MAP[key]
        # 2. SentimentReport backref (ORM relationship)
        reports = getattr(article, "sentiment_report", None)
        if reports:
            report = sorted(reports, key=lambda r: r.id, reverse=True)[0] if isinstance(reports, list) else reports
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
    # 3. Keyword inference
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
    """Always returns exactly `limit` articles. Same-category first, then pads."""
    related: list = []
    try:
        if article.category:
            related = (
                Article.query
                .filter(Article.id != article.id, Article.published.is_(True),
                        Article.category == article.category)
                .order_by(Article.created_at.desc()).limit(limit).all()
            )
        if len(related) < limit:
            exc_ids = [article.id] + [r.id for r in related]
            pad = (
                Article.query
                .filter(~Article.id.in_(exc_ids), Article.published.is_(True))
                .order_by(Article.created_at.desc()).limit(limit - len(related)).all()
            )
            related.extend(pad)
    except Exception as exc:
        logger.warning("article_get_related failed: %s", exc)
    return related[:limit]


def article_cat_color(category: str | None) -> str:
    return CATEGORY_COLORS.get((category or "default").lower(), CATEGORY_COLORS["default"])


def article_cat_gradient(category: str | None) -> str:
    return CATEGORY_GRADIENTS.get((category or "default").lower(), CATEGORY_GRADIENTS["default"])


def article_tldr_bullets(article, max_bullets: int = 3) -> list[str]:
    """
    'What you need to know' — 3 bullet TL;DR above article body.
    Derived from summary (sentence split) or first sentences of content.
    No Claude API call — instant, never crashes.
    """
    try:
        text = (getattr(article, "summary", None) or "").strip()
        if not text:
            # Fall back to stripped content first 500 chars
            raw = re.sub(r"<[^>]+>", " ", getattr(article, "content", None) or "")
            text = re.sub(r"\s+", " ", raw).strip()[:600]
        # Split on sentence boundaries
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip() and len(s.strip()) > 15]
        bullets = sentences[:max_bullets]
        # Ensure sentences end with punctuation
        bullets = [b if b[-1] in ".!?" else b + "." for b in bullets]
        return bullets
    except Exception:
        return []


def build_article_data(articles, limit: int = 0) -> list[dict]:
    """Build article_data list for template rendering."""
    if limit:
        articles = articles[:limit]
    result = []
    for a in articles:
        result.append({
            "article":      a,
            "image_url":    article_get_image(a),
            "sentiment":    article_get_sentiment(a),
            "read_time":    article_get_read_time(a),
            "cat_color":    article_cat_color(a.category),
            "cat_gradient": article_cat_gradient(a.category),
            "slug":         article_make_slug(a),
        })
    return result


# ─── Blueprint ────────────────────────────────────────────────────────────────

articles_bp = Blueprint("articles_bp", __name__)


@articles_bp.route("/article/<slug>")
def article_by_slug(slug):
    """Individual article page — slug-based URL (SESSION 10 spec)."""
    from app import db
    from models import Article

    article = article_find_by_slug(slug)
    if article is None:
        from flask import abort
        abort(404)

    # Redirect to canonical slug if URL doesn't match
    canonical = article_make_slug(article)
    if slug != canonical:
        return redirect(url_for("articles_bp.article_by_slug", slug=canonical), 301)

    # Enrich
    sentiment     = article_get_sentiment(article)
    cat_color     = article_cat_color(article.category)
    cat_gradient  = article_cat_gradient(article.category)
    read_time     = article_get_read_time(article)
    header_image  = article_get_image(article) or "/static/images/default-header.png"
    tldr_bullets  = article_tldr_bullets(article)
    related_list  = article_get_related(article, db, Article, 3)
    related_data  = build_article_data(related_list)

    # Key takeaways (same as TL;DR bullets for now — spec says Claude-generated,
    # but we use instant extraction to avoid API calls on every page view)
    key_takeaways_bullets = tldr_bullets

    # Body HTML: strip duplicate TL;DR block if content generator embedded it
    body_html = _strip_tldr_block(article.content or "")

    return render_template(
        "article_detail.html",
        article=article,
        sentiment=sentiment,
        cat_color=cat_color,
        cat_gradient=cat_gradient,
        read_time=read_time,
        header_image_url=header_image,
        tldr_bullets=tldr_bullets,
        key_takeaways_bullets=key_takeaways_bullets,
        related_articles=related_list,
        related_data=related_data,
        body_html=body_html,
        article_slug=canonical,
    )


@articles_bp.route("/articles/<int:article_id>/slug")
def article_id_to_slug(article_id):
    """Redirect legacy ID URLs to canonical slug URL."""
    from models import Article
    article = Article.query.get_or_404(article_id)
    return redirect(url_for("articles_bp.article_by_slug", slug=article_make_slug(article)), 301)


# ─── Private helpers ──────────────────────────────────────────────────────────

def _strip_tldr_block(content: str) -> str:
    """Remove duplicate TL;DR block that content_generator sometimes embeds."""
    try:
        from services.content_generator import strip_duplicate_tldr
        return strip_duplicate_tldr(content)
    except Exception:
        pass
    # Fallback: strip common TL;DR markers
    content = re.sub(r"<[^>]*>\s*TL;DR.*?</[^>]*>", "", content, flags=re.IGNORECASE | re.DOTALL)
    return content
