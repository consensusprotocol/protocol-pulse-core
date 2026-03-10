"""
routes_api_v2.py - Protocol Pulse Article API v2
Clean JSON-only endpoints. See ARTICLE_PAGE_LAWS.md for schema contract.

SESSION 10 fix: added display fields (sentiment, category colour/gradient,
read_time, has_more) so articles.html Load More JS can render cards correctly
without extra requests. Also added published=True fallback so the endpoint
never returns 0 articles when articles exist but lack the published flag.
"""

import re
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import Article
from app import db

logger = logging.getLogger(__name__)

api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# ── Display helpers (import from articles blueprint; graceful fallback) ────────
try:
    from core.blueprints.articles import (
        article_get_sentiment,
        article_cat_color,
        article_cat_gradient,
        article_make_slug,
        article_get_read_time,
        article_get_image,
    )
    _HELPERS_LOADED = True
except Exception as _he:
    logger.warning("articles helpers not loaded in routes_api_v2: %s", _he)
    _HELPERS_LOADED = False


def _strip_html(html):
    if not html:
        return ""
    return re.sub(r'<[^>]+>', '', html).strip()


def _article_to_dict(article, include_content=False):
    """
    Convert Article model to API dict.

    Base fields: Law 2 schema (ARTICLE_PAGE_LAWS.md).
    Display fields: sentiment_label/color/bg, category_color, category_gradient,
    read_time — used by articles.html Load More JS to render cards client-side.
    """
    plain = _strip_html(article.content or "")
    word_count = len(plain.split()) if plain else 0

    tags = []
    if article.tags:
        try:
            tags = json.loads(article.tags) if article.tags.startswith('[') else [
                t.strip() for t in article.tags.split(',') if t.strip()
            ]
        except Exception:
            tags = []

    # Slug: use id-prefixed slug for O(1) DB lookup
    if _HELPERS_LOADED:
        slug = article_make_slug(article)
        cover = article_get_image(article) or "/static/images/default-header.png"
        sent = article_get_sentiment(article)
        cat_color = article_cat_color(article.category)
        cat_gradient = article_cat_gradient(article.category)
        read_time = article_get_read_time(article)
    else:
        slug = getattr(article, 'slug', None) or f"article-{article.id}"
        cover = (article.cover_image_url or "").strip() or "/static/images/default-header.png"
        sent = {"label": "NEUTRAL", "color": "#6b7280", "bg": "rgba(107,114,128,0.12)"}
        cat_color = "#9ca3af"
        cat_gradient = "linear-gradient(135deg,#0d0d1a,#1a1a2e)"
        read_time = max(1, word_count // 200)

    result = {
        # Law 2 base fields
        "id":               article.id,
        "title":            article.title or "",
        "slug":             slug,
        "summary":          (article.summary or plain[:200] + ("..." if len(plain) > 200 else "")).strip(),
        "category":         article.category or "Bitcoin",
        "tags":             tags,
        "author":           article.author or "Protocol Pulse AI",
        "cover_image_url":  cover,
        "source_url":       article.source_url or "",
        "source_type":      article.source_type or "",
        "published_at":     article.published_at.isoformat() + "Z" if article.published_at else None,
        "created_at":       article.created_at.isoformat() + "Z" if article.created_at else None,
        "read_time_minutes": read_time,
        # Display fields for articles.html Load More JS
        "sentiment_label":  sent["label"],
        "sentiment_color":  sent["color"],
        "sentiment_bg":     sent["bg"],
        "category_color":   cat_color,
        "category_gradient": cat_gradient,
        "read_time":        read_time,   # alias (JS uses this)
        "source":           article.author or article.source_type or "Protocol Pulse",
    }

    if include_content:
        result["content"] = article.content or ""

    return result


def _base_query():
    """
    Return the base Article query.

    Law: published=True preferred; if 0 published articles exist, fall back to
    ALL articles so the feed never shows empty when data is present.
    """
    q = Article.query.filter(Article.published.is_(True))
    if q.count() == 0:
        logger.info("api_v2: 0 published articles — falling back to all articles")
        q = Article.query
    return q


@api_v2.route('/articles')
def list_articles():
    try:
        page     = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 20, type=int)), 50)
        category = request.args.get('category', '').strip()
        sort     = request.args.get('sort', 'newest').strip()
        since    = request.args.get('since', '').strip()
        search   = request.args.get('q', request.args.get('search', '')).strip()

        query = _base_query()

        if category and category.lower() != 'all':
            query = query.filter(Article.category.ilike(f"%{category}%"))

        if search:
            like = f"%{search}%"
            query = query.filter(db.or_(
                Article.title.ilike(like),
                Article.summary.ilike(like),
                Article.tags.ilike(like),
            ))

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(Article.created_at >= since_dt)
            except (ValueError, TypeError):
                pass

        if sort == 'oldest':
            query = query.order_by(Article.created_at.asc())
        else:
            query = query.order_by(Article.created_at.desc())

        total       = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        articles    = query.offset((page - 1) * per_page).limit(per_page).all()
        has_more    = page < total_pages

        return jsonify({
            "articles":    [_article_to_dict(a) for a in articles],
            "has_more":    has_more,          # top-level for articles.html JS
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": total_pages,
            "pagination": {
                "page":        page,
                "per_page":    per_page,
                "total":       total,
                "total_pages": total_pages,
                "has_next":    has_more,
                "has_prev":    page > 1,
            },
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"},
        })
    except Exception as e:
        logger.error("api_v2 list_articles error: %s", e)
        return jsonify({"articles": [], "error": str(e), "has_more": False}), 500


@api_v2.route('/articles/<path:slug>')
def get_article(slug):
    try:
        article = None
        # Try id-prefixed slug (O(1) lookup by PK)
        if _HELPERS_LOADED:
            from core.blueprints.articles import article_find_by_slug
            article = article_find_by_slug(slug)
        if not article and hasattr(Article, 'slug'):
            article = Article.query.filter(Article.slug == slug).first()
        if not article and slug.split('-')[0].isdigit():
            article = Article.query.filter(Article.id == int(slug.split('-')[0])).first()
        if not article and slug.isdigit():
            article = Article.query.filter(Article.id == int(slug)).first()
        if not article:
            return jsonify({"error": "Article not found"}), 404

        return jsonify({
            "article": _article_to_dict(article, include_content=True),
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"},
        })
    except Exception as e:
        logger.error("api_v2 get_article error: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/categories')
def list_categories():
    try:
        base = _base_query()
        results = db.session.query(
            Article.category, db.func.count(Article.id)
        ).filter(
            Article.category.isnot(None), Article.category != ''
        ).group_by(Article.category).all()

        categories = [
            {"name": cat, "count": count}
            for cat, count in sorted(results, key=lambda x: x[1], reverse=True)
            if cat and cat != 'DeFi'
        ]
        return jsonify({
            "categories": categories,
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"},
        })
    except Exception as e:
        logger.error("api_v2 categories error: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/search')
def search_articles():
    try:
        q        = request.args.get('q', '').strip()
        page     = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 20, type=int)), 50)

        if not q or len(q) < 2:
            return jsonify({"error": "Query must be at least 2 characters"}), 400

        search_term = f"%{q}%"
        query = _base_query().filter(
            db.or_(Article.title.ilike(search_term), Article.content.ilike(search_term))
        ).order_by(Article.created_at.desc())

        total       = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        articles    = query.offset((page - 1) * per_page).limit(per_page).all()
        has_more    = page < total_pages

        return jsonify({
            "articles":  [_article_to_dict(a) for a in articles],
            "query":     q,
            "has_more":  has_more,
            "pagination": {
                "page": page, "per_page": per_page, "total": total,
                "total_pages": total_pages,
                "has_next": has_more, "has_prev": page > 1,
            },
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"},
        })
    except Exception as e:
        logger.error("api_v2 search error: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/prices')
def get_prices():
    try:
        from services.price_service import price_service
        prices = price_service.get_prices()
        return jsonify({
            "prices": prices,
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"},
        })
    except Exception as e:
        logger.error("api_v2 prices error: %s", e)
        return jsonify({"error": "Price service unavailable"}), 503


@api_v2.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '')
    allowed = [
        'https://protocolpulse.io', 'https://www.protocolpulse.io',
        'http://localhost:3000', 'http://localhost:3001',
    ]
    if origin in allowed or origin.endswith('.vercel.app'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
