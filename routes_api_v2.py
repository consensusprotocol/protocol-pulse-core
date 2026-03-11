"""
routes_api_v2.py - Protocol Pulse Article API v2
Clean JSON-only endpoints for the Next.js frontend.
See ARTICLE_PAGE_LAWS.md for the schema contract.
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


def _strip_html(html):
    if not html:
        return ""
    return re.sub(r'<[^>]+>', '', html).strip()


def _article_to_dict(article, include_content=False):
    """Convert Article model to API dict. Law 2 schema. Delegates to model.to_api_dict()."""
    if hasattr(article, 'to_api_dict'):
        return article.to_api_dict(include_content=include_content)
    # Fallback for older model without to_api_dict
    plain = _strip_html(article.content or "")
    word_count = len(plain.split()) if plain else 0
    tags = []
    if article.tags:
        try:
            tags = json.loads(article.tags) if article.tags.startswith('[') else [t.strip() for t in article.tags.split(',') if t.strip()]
        except Exception:
            tags = []
    result = {
        "id": article.id,
        "title": article.title or "",
        "slug": getattr(article, 'slug', None) or f"article-{article.id}",
        "summary": (article.summary or plain[:200] + ("..." if len(plain) > 200 else "")).strip(),
        "category": article.category or "Bitcoin",
        "tags": tags,
        "author": article.author or "Protocol Pulse AI",
        "cover_image_url": article.resolve_cover_image() if hasattr(article, 'resolve_cover_image') else (article.cover_image_url or "/static/images/default-header.png"),
        "source_url": article.source_url or "",
        "source_type": article.source_type or "",
        "published_at": article.published_at.isoformat() + "Z" if article.published_at else None,
        "created_at": article.created_at.isoformat() + "Z" if article.created_at else None,
        "read_time_minutes": max(1, word_count // 200),
    }
    if include_content:
        result["content"] = article.content or ""
    return result


@api_v2.route('/articles')
def list_articles():
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 20, type=int)), 50)
        category = request.args.get('category', '').strip()
        sort = request.args.get('sort', 'newest').strip()
        since = request.args.get('since', '').strip()

        query = Article.query.filter(Article.published.is_(True))

        if category:
            query = query.filter(Article.category == category)

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(Article.created_at >= since_dt)
            except (ValueError, TypeError):
                pass

        if sort == 'oldest':
            query = query.order_by(Article.published_at.asc())
        else:
            query = query.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())

        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        articles = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "articles": [_article_to_dict(a) for a in articles],
            "pagination": {
                "page": page, "per_page": per_page, "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages, "has_prev": page > 1,
            },
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"}
        })
    except Exception as e:
        logger.error(f"API v2 list_articles error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/articles/<path:slug>')
def get_article(slug):
    try:
        article = None
        if hasattr(Article, 'slug'):
            article = Article.query.filter(Article.slug == slug, Article.published.is_(True)).first()
        if not article and slug.isdigit():
            article = Article.query.filter(Article.id == int(slug), Article.published.is_(True)).first()
        if not article:
            return jsonify({"error": "Article not found"}), 404

        return jsonify({
            "article": _article_to_dict(article, include_content=True),
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"}
        })
    except Exception as e:
        logger.error(f"API v2 get_article error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/categories')
def list_categories():
    try:
        results = db.session.query(
            Article.category, db.func.count(Article.id)
        ).filter(
            Article.published.is_(True),
            Article.category.isnot(None), Article.category != ''
        ).group_by(Article.category).all()

        categories = [
            {"name": cat, "count": count}
            for cat, count in sorted(results, key=lambda x: x[1], reverse=True)
            if cat and cat != 'DeFi'
        ]
        return jsonify({"categories": categories, "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"}})
    except Exception as e:
        logger.error(f"API v2 categories error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/search')
def search_articles():
    try:
        q = request.args.get('q', '').strip()
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 20, type=int)), 50)

        if not q or len(q) < 2:
            return jsonify({"error": "Query must be at least 2 characters"}), 400

        search_term = f"%{q}%"
        query = Article.query.filter(
            Article.published.is_(True),
            db.or_(Article.title.ilike(search_term), Article.content.ilike(search_term))
        ).order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())

        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        articles = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "articles": [_article_to_dict(a) for a in articles],
            "query": q,
            "pagination": {
                "page": page, "per_page": per_page, "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages, "has_prev": page > 1,
            },
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"}
        })
    except Exception as e:
        logger.error(f"API v2 search error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/prices')
def get_prices():
    try:
        from services.price_service import price_service
        prices = price_service.get_prices()
        return jsonify({"prices": prices, "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"}})
    except Exception as e:
        logger.error(f"API v2 prices error: {e}")
        return jsonify({"error": "Price service unavailable"}), 503


@api_v2.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '')
    allowed = ['https://protocolpulse.io', 'https://www.protocolpulse.io', 'http://localhost:3000', 'http://localhost:3001']
    if origin in allowed or origin.endswith('.vercel.app'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
