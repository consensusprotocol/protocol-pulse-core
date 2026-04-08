"""
routes_helpers.py — Shared state, imports, decorators, and service instances
used across all route blueprints.
"""
from flask import render_template, request, jsonify, redirect, url_for, flash, make_response, session, Response, abort, send_file
from flask_login import login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db, limiter, cache

import models

import hashlib
import json
import logging
import requests
import os
import re
import stripe
import uuid
from functools import wraps
from datetime import datetime, timedelta
import threading


# ── Cloudflare Turnstile CAPTCHA verification ────────────────────────────────

def verify_turnstile(token):
    """Verify a Cloudflare Turnstile token. Returns True if valid.
    Fails open if secret key is not configured or is a test/placeholder key."""
    secret = os.environ.get('TURNSTILE_SECRET_KEY', '')
    if not secret or secret.startswith('1x0000000000') or secret == 'your_secret_key_here':
        logging.warning("TURNSTILE_SECRET_KEY not configured — skipping captcha check")
        return True
    if not token:
        logging.warning("Turnstile token empty — skipping captcha check")
        return True
    try:
        resp = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': secret, 'response': token},
            timeout=5,
        )
        result = resp.json()
        if result.get('success', False):
            return True
        logging.warning(f"Turnstile verification failed: {result.get('error-codes', [])}")
        return False
    except Exception as e:
        logging.error(f"Turnstile verification error: {e}")
        return True


# ── Service imports ──────────────────────────────────────────────────────────
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.content_generator import ContentGenerator
from services.content_engine import ContentEngine
try:
    from services.substack_service import SubstackService
except ModuleNotFoundError:
    SubstackService = None
from services.newsletter import newsletter_service
try:
    from services.rss_service import RSSService
except ModuleNotFoundError:
    RSSService = None
try:
    from services.media_feed_service import MediaFeedService as _MFS
    media_feed_service = _MFS()
except Exception as _e:
    logging.warning('media_feed_service: %s', _e)
    media_feed_service = None
from services.printful_service import PrintfulService
from services.price_service import price_service
from services.youtube_service import YouTubeService
from services.node_service import NodeService
from services.ghl_service import ghl_service
from services.transcript_service import get_space_transcript, summarize_for_tweet

ADMIN_SECRET = os.environ.get('ADMIN_SECRET', '')


# ── Sentiment classification trigger ────────────────────────────────────────

def _trigger_sentiment_classification(article_id: int):
    """Spin up a background thread to classify the article."""
    def _classify_worker(aid):
        import time as _time
        _time.sleep(2)
        try:
            from services.sentiment_analyzer import classify_article
            result = classify_article(aid)
            if result:
                logging.info("Sentiment classification complete: article %s → %s", aid, result.get("sentiment"))
        except Exception as e:
            logging.error("Background sentiment classification failed for article %s: %s", aid, e)
    t = threading.Thread(target=_classify_worker, args=(article_id,), daemon=True)
    t.start()


def _startup_batch_classify():
    """Run on app startup: classify any unclassified articles from last 24h."""
    def _batch_worker():
        import time as _time
        _time.sleep(10)
        try:
            from services.sentiment_analyzer import batch_classify
            result = batch_classify(hours=24)
            logging.info("Startup batch classify: %s", result)
        except Exception as e:
            logging.error("Startup batch classify failed: %s", e)
    t = threading.Thread(target=_batch_worker, daemon=True)
    t.start()

_startup_batch_classify()


# ── Service instances ────────────────────────────────────────────────────────
ai_service = AIService()
reddit_service = RedditService()
content_generator = ContentGenerator()
content_engine = ContentEngine()
if SubstackService is not None:
    try:
        substack_service = SubstackService()
    except Exception as e:
        logging.warning("Substack service initialization failed: %s", e)
        substack_service = None
else:
    substack_service = None
    logging.warning("Substack service not available (module not found)")

rss_service = RSSService() if RSSService is not None else None
printful_service = PrintfulService()


# ── Decorators ───────────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator to enforce admin role-based access control"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def premium_required(f):
    """Require Commander ($29/mo) or higher for premium hub access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('auth.login') + '?next=' + request.path)
        if not getattr(current_user, 'has_commander_tier', lambda: False)():
            flash('Premium Hub requires a Commander ($29/mo) subscription.')
            return redirect(url_for('pages.premium_page'))
        return f(*args, **kwargs)
    return decorated_function


def premium_hub_required(f):
    """Require any paid tier (Operator / Commander / Sovereign) for hub access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('auth.login') + '?next=' + request.path)
        if not getattr(current_user, 'has_premium', lambda: False)():
            flash('Premium Hub requires a paid subscription (Operator $21/mo or higher).')
            return redirect(url_for('pages.premium_page'))
        return f(*args, **kwargs)
    return decorated_function


def _require_csrf():
    """Abort 400 if POST CSRF token is missing or does not match session."""
    if request.method != "POST":
        return
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token or not session.get("csrf_token") or token != session.get("csrf_token"):
        abort(400, "Invalid or missing CSRF token")


def _index_cache_key():
    """Cache key for homepage — separate for authenticated vs anonymous."""
    from flask_login import current_user
    return "index_" + (str(current_user.id) if current_user.is_authenticated else "anon")


# ── JWT auth for /v1/* API endpoints ─────────────────────────────────────────
import jwt as _jwt

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "pulse-terminal-dev-secret-change-in-prod")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24


def _jwt_required(f):
    """Decorator: validates Bearer JWT; injects _jwt_user_id, _jwt_tier into kwargs."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header[7:]
        try:
            payload = _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        except _jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except _jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        tier = payload.get("tier", "free")
        if tier not in ("commander", "sovereign"):
            return jsonify({"error": "Commander tier required"}), 403

        kwargs["_jwt_user_id"] = payload.get("user_id")
        kwargs["_jwt_tier"] = tier
        return f(*args, **kwargs)
    return decorated


def _apply_rate_limit(user_id, tier):
    """Check rate limit; returns (allowed, meta_dict)."""
    from services.pulse_terminal_service import check_and_increment_rate_limit
    result = check_and_increment_rate_limit(user_id, tier)
    meta = {
        "tier": tier,
        "rate_limit_remaining": result["remaining"],
        "rate_limit_daily": result["limit"],
        "freshness": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return result["allowed"], meta
