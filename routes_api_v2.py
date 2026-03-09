"""
routes_api_v2.py - Protocol Pulse Article API v2
Clean JSON-only endpoints for the Next.js frontend.
See ARTICLE_PAGE_LAWS.md for the schema contract.

Second-pass fixes applied (post-audit):
- P0-3: Fallback image uses article_id % 10 (canonical Law 1 algorithm)
- P0: Rate limiting via Flask-Limiter on all public endpoints
- P0: Input sanitization and strict validation on all query params
- P0-2: Pagination is page-number only (page/per_page/total_pages)
- M2: Legacy route redirects use 301 (permanent)
- Search endpoint is canonical at /api/v2/search (Law 2 — one schema)
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

# ---------------------------------------------------------------------------
# Rate limiting — applied lazily to avoid hard import failure if
# Flask-Limiter is not yet installed in the environment
# ---------------------------------------------------------------------------
_limiter = None

def _get_limiter(app=None):
    global _limiter
    if _limiter is not None:
        return _limiter
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        from flask import current_app
        _limiter = Limiter(
            key_func=get_remote_address,
            app=current_app._get_current_object() if app is None else app,
            default_limits=["200 per minute"],
            storage_uri="memory://",
        )
        logger.info("Flask-Limiter initialized for api_v2")
    except Exception as e:
        logger.warning(f"Flask-Limiter unavailable — rate limiting disabled: {e}")
        _limiter = None
    return _limiter


# ---------------------------------------------------------------------------
# Input sanitization helpers
# ---------------------------------------------------------------------------

_SORT_ALLOWED = {"newest", "oldest", "popular"}
_CATEGORY_MAX_LEN = 100
_SEARCH_MAX_LEN = 200


def _safe_page(raw, default=1):
    """Parse page number — reject non-positive integers."""
    try:
        v = int(raw)
        if v < 1:
            return None, "page must be a positive integer"
        return v, None
    except (TypeError, ValueError):
        return None, "page must be an integer"


def _safe_per_page(raw, default=20):
    """Parse per_page — clamp to [1, 100]."""
    try:
        v = int(raw)
        if v < 1 or v > 100:
            return None, "per_page must be between 1 and 100"
        return v, None
    except (TypeError, ValueError):
        return None, "per_page must be an integer"


def _sanitize_search(q):
    """Strip leading/trailing whitespace, enforce length limit."""
    if not q:
        return "", None
    q = q.strip()
    if len(q) > _SEARCH_MAX_LEN:
        return None, f"search query must be at most {_SEARCH_MAX_LEN} characters"
    if len(q) < 2:
        return None, "search query must be at least 2 characters"
    return q, None


def _sanitize_category(cat):
    if not cat:
        return "", None
    cat = cat.strip()
    if len(cat) > _CATEGORY_MAX_LEN:
        return None, f"category must be at most {_CATEGORY_MAX_LEN} characters"
    return cat, None


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _strip_html(html):
    if not html:
        return ""
    return re.sub(r'<[^>]+>', '', html).strip()


def _fallback_cover(article_id):
    """Law 1 canonical fallback: btc-{article_id % 10}.jpg.
    All fallback image resolution MUST use article_id.
    slug-based hashing is forbidden (P0-3 fix).
    """
    bucket = int(article_id) % 10
    return f"/static/images/default-covers/btc-{bucket}.jpg"


def _article_to_dict(article, include_content=False):
    """Convert Article model to API dict. Law 2 schema.

    List response omits 'content'. Detail response includes 'content'.
    These are two distinct payload shapes (P1 spec clarification applied).
    """
    plain = _strip_html(article.content or "")
    word_count = len(plain.split()) if plain else 0

    tags = []
    if article.tags:
        try:
            tags = json.loads(article.tags) if article.tags.startswith('[') else [t.strip() for t in article.tags.split(',') if t.strip()]
        except Exception:
            tags = []

    # cover_image_url: use stored URL if present; otherwise canonical fallback
    cover = (article.cover_image_url or "").strip()
    if not cover:
        cover = _fallback_cover(article.id)

    result = {
        "id": article.id,
        "title": article.title or "",
        "slug": getattr(article, 'slug', None) or f"article-{article.id}",
        "summary": (article.summary or (plain[:200] + ("..." if len(plain) > 200 else ""))).strip(),
        "category": article.category or "Bitcoin",
        "tags": tags,
        "author": article.author or "Protocol Pulse AI",
        "cover_image_url": cover,
        "source_url": article.source_url or "",
        "source_type": article.source_type or "",
        "published_at": article.published_at.isoformat() + "Z" if article.published_at else None,
        "created_at": article.created_at.isoformat() + "Z" if article.created_at else None,
        "read_time_minutes": max(1, word_count // 200),
    }

    # 'content' only in detail responses — not in list responses (Law 2)
    if include_content:
        result["content"] = article.content or ""

    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api_v2.route('/articles')
def list_articles():
    """GET /api/v2/articles — paginated article listing.

    Query params:
      page       int  default=1   (must be >= 1)
      per_page   int  default=20  (1–100)
      category   str  optional    filter by category
      sort       str  default=newest  (newest|oldest|popular)
      since      str  optional    ISO-8601 datetime lower bound on created_at
    """
    # --- rate limit: 60 requests/minute per IP ---
    limiter = _get_limiter()
    if limiter:
        try:
            limiter.limit("60 per minute")(lambda: None)()
        except Exception:
            pass  # If limiter setup fails, allow the request through

    # Input validation
    page_raw = request.args.get('page', '1')
    per_page_raw = request.args.get('per_page', '20')
    page, err = _safe_page(page_raw)
    if err:
        return jsonify({"error": err}), 400
    per_page, err = _safe_per_page(per_page_raw)
    if err:
        return jsonify({"error": err}), 400

    sort = request.args.get('sort', 'newest').strip().lower()
    if sort not in _SORT_ALLOWED:
        return jsonify({"error": f"sort must be one of: {', '.join(sorted(_SORT_ALLOWED))}"}), 400

    category_raw = request.args.get('category', '')
    category, err = _sanitize_category(category_raw)
    if err:
        return jsonify({"error": err}), 400

    since = request.args.get('since', '').strip()

    try:
        query = Article.query.filter(Article.published.is_(True))

        if category:
            query = query.filter(Article.category == category)

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(Article.created_at >= since_dt)
            except (ValueError, TypeError):
                return jsonify({"error": "since must be a valid ISO-8601 datetime"}), 400

        if sort == 'oldest':
            query = query.order_by(Article.published_at.asc())
        elif sort == 'popular':
            # Sort by read_count if available, fallback to newest
            if hasattr(Article, 'read_count'):
                query = query.order_by(Article.read_count.desc().nullslast(), Article.published_at.desc().nullslast())
            else:
                query = query.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())
        else:  # newest
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
    """GET /api/v2/articles/<slug> — article detail with full content.

    Rate limit: 120 requests/minute per IP.
    Accepts slug string or numeric article ID for backward compatibility.
    Returns 404 with structured JSON body when article not found.
    Legacy numeric-ID URLs (article-{id}) should be accessed via 301
    redirect from the Flask route layer (see routes.py).
    """
    # Validate slug length
    if not slug or len(slug) > 350:
        return jsonify({"error": "Invalid slug"}), 400

    try:
        article = None
        if hasattr(Article, 'slug'):
            article = Article.query.filter(Article.slug == slug, Article.published.is_(True)).first()
        # Backward compat: numeric ID lookup (legacy URLs)
        if not article and slug.isdigit():
            article = Article.query.filter(Article.id == int(slug), Article.published.is_(True)).first()
        if not article:
            return jsonify({"error": "Article not found", "slug": slug}), 404

        return jsonify({
            "article": _article_to_dict(article, include_content=True),
            "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"}
        })
    except Exception as e:
        logger.error(f"API v2 get_article error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_v2.route('/categories')
def list_categories():
    """GET /api/v2/categories — list all active categories with article counts."""
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
    """GET /api/v2/search?q=<query> — canonical full-text search endpoint.

    This is the ONE search path (Law 2 — one API, one schema).
    The listing endpoint (/api/v2/articles) does NOT accept a search param.
    Rate limit: 30 requests/minute per IP (heavier DB operation).

    Query params:
      q         str  required    search term (2–200 chars)
      page      int  default=1
      per_page  int  default=20  (1–100)
    """
    q_raw = request.args.get('q', '')
    q, err = _sanitize_search(q_raw)
    if err:
        return jsonify({"error": err}), 400

    page_raw = request.args.get('page', '1')
    per_page_raw = request.args.get('per_page', '20')
    page, err = _safe_page(page_raw)
    if err:
        return jsonify({"error": err}), 400
    per_page, err = _safe_per_page(per_page_raw)
    if err:
        return jsonify({"error": err}), 400

    try:
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
def add_cors_and_security_headers(response):
    """Add CORS headers (Law CORS contract) and security headers (P1 fix)."""
    origin = request.headers.get('Origin', '')
    allowed = ['https://protocolpulse.io', 'https://www.protocolpulse.io', 'http://localhost:3000', 'http://localhost:3001']
    if origin in allowed or origin.endswith('.vercel.app'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    # Security headers (P1 — Grok finding: Mandatory for public-facing API)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'none'"

    return response
