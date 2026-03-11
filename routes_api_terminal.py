"""Pulse Terminal API — V30 Premium Bitcoin Intelligence.

Endpoints (Commander tier, $49/mo):
  POST /api/v2/terminal/subscribe       — Create Stripe checkout session
  POST /api/v2/terminal/webhook         — Stripe payment webhook
  GET  /api/v2/terminal/topics          — Top topics last 24hr (from articles DB)
  GET  /api/v2/terminal/entities        — Named entities + sentiment
  GET  /api/v2/terminal/sentiment       — BTC sentiment score 0-100
  GET  /api/v2/terminal/breaking        — Breaking articles (last 2hr)
  GET  /api/v2/terminal/network         — Live network stats (hashrate, difficulty, nodes)
  GET  /api/v2/terminal/docs            — Redirect to docs section
  GET  /terminal/success                — Post-payment confirmation page

Authentication: X-PP-API-Key header required on all data endpoints.
Rate limit: 1000 req/day for Commander tier. Resets daily at 00:00 UTC.
Key format: pp_cmd_{32 hex chars}
Security: Keys stored as SHA256 hash only — plaintext never persisted.
"""

import hashlib
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import requests
from flask import Blueprint, jsonify, request, render_template, redirect
from sqlalchemy import func, update

log = logging.getLogger(__name__)

terminal_bp = Blueprint("terminal", __name__)

# ── Constants ─────────────────────────────────────────────────────────────────

TIER_LIMITS = {
    "demo":      20,
    "commander": 1000,
    "sovereign": -1,   # unlimited (V31)
    "watcher":   100,  # V31
}

COMMANDER_DAILY_LIMIT = 1000
DEMO_KEY = "pp_demo_readonly"
DEMO_KEY_HASH = hashlib.sha256(DEMO_KEY.encode()).hexdigest()
BREAKING_LOOKBACK_HOURS = 2
HALVING_INTERVAL = 210_000
LAST_HALVING_BLOCK = 840_000
NEXT_HALVING_BLOCK = LAST_HALVING_BLOCK + HALVING_INTERVAL  # 1,050,000
EXTERNAL_TIMEOUT = 6

# Known Bitcoin entities for entity tracking (Phase 3 spec)
KNOWN_ENTITIES = [
    "MicroStrategy", "BlackRock", "Saylor", "Fed", "ETF",
    "Halving", "Lightning", "Ordinals", "Runes", "Taproot",
]

# Sentiment keywords (Phase 3 spec)
POSITIVE_KEYWORDS = ["bull", "surge", "rally", "ath", "adoption", "record", "inflow"]
NEGATIVE_KEYWORDS = ["bear", "crash", "dump", "ban", "fear", "panic", "outflow"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _ip_hash() -> str:
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip = ip.split(",")[0].strip()
    return _sha256(ip)


def _utcnow() -> datetime:
    """Naive UTC datetime (matches SQLite column storage)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt) -> str:
    if dt is None:
        return None
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt)


def _midnight_tomorrow() -> datetime:
    now = datetime.now(timezone.utc)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _terminal_response(endpoint: str, data, tier: str,
                       requests_today: int, limit: int, cache_age: int = 0) -> dict:
    """Build GOSPEL-compliant response envelope."""
    reset_at = _midnight_tomorrow()
    return {
        "tier": tier,
        "endpoint": endpoint,
        "timestamp": _iso(_utcnow()),
        "cache_age_seconds": cache_age,
        "data": data,
        "rate_limit": {
            "requests_today": requests_today,
            "limit": limit,
            "resets_at": reset_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }


# ── Demo Key Provisioning ─────────────────────────────────────────────────────

def provision_demo_key():
    """Insert the demo API key on first run. Called at app startup."""
    from app import db
    from models import ApiKey

    try:
        existing = ApiKey.query.filter_by(key_hash=DEMO_KEY_HASH).first()
        if existing:
            return
        demo = ApiKey(
            key_hash=DEMO_KEY_HASH,
            key_prefix=DEMO_KEY[:8],
            tier="demo",
            subscriber_email="demo@protocolpulse.io",
            requests_today=0,
            requests_total=0,
            active=True,
        )
        db.session.add(demo)
        db.session.commit()
        log.info("Demo API key provisioned: %s", DEMO_KEY)
    except Exception as e:
        log.warning("Demo key provisioning failed (non-fatal): %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass


# ── Auth + Rate-Limit Decorator ───────────────────────────────────────────────

def require_terminal_auth(required_tier: str = "commander"):
    """Decorator: authenticate X-PP-API-Key and enforce per-day rate limit."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from app import db
            from models import ApiKey, ApiUsageLog

            api_key_raw = request.headers.get("X-PP-API-Key", "").strip()
            if not api_key_raw:
                return jsonify({
                    "error": "Missing X-PP-API-Key header.",
                    "docs": "https://protocolpulse.io/terminal",
                }), 401

            key_hash = _sha256(api_key_raw)
            t_start = time.monotonic()

            try:
                key_entry = ApiKey.query.filter_by(key_hash=key_hash, active=True).first()
            except Exception as e:
                log.error("DB auth error: %s", e)
                return jsonify({"error": "Internal auth error"}), 500

            if not key_entry:
                return jsonify({"error": "Invalid or inactive API key."}), 401

            # Daily reset check (idempotent)
            try:
                key_entry.reset_if_new_day()
                db.session.flush()
            except Exception as e:
                log.warning("Daily reset flush failed: %s", e)

            tier = key_entry.tier

            # Tier gate
            tier_order = {"watcher": 1, "commander": 2, "sovereign": 3}
            if tier_order.get(tier, 0) < tier_order.get(required_tier, 2):
                return jsonify({
                    "error": f"Endpoint requires {required_tier} tier.",
                    "your_tier": tier,
                    "upgrade": "https://protocolpulse.io/terminal#pricing",
                }), 403

            # Rate limit check (pre-increment snapshot)
            limit = TIER_LIMITS.get(tier, 1000)
            if limit != -1 and key_entry.requests_today >= limit:
                reset_at = _midnight_tomorrow()
                resp = jsonify({
                    "error": f"Daily rate limit reached. {limit} requests/day for {tier} tier.",
                    "resets_at": reset_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "tier": tier,
                })
                resp.headers["Retry-After"] = str(
                    int((reset_at - datetime.now(timezone.utc)).total_seconds())
                )
                return resp, 429

            # Atomic increment — prevents race condition under concurrent requests.
            # Uses UPDATE ... SET col = col + 1 which is serialized at DB level.
            try:
                today_str = _utcnow().strftime("%Y-%m-%d")
                db.session.execute(
                    update(ApiKey)
                    .where(ApiKey.key_hash == key_hash)
                    .values(
                        requests_today=ApiKey.requests_today + 1,
                        requests_total=ApiKey.requests_total + 1,
                        last_used_at=_utcnow(),
                    )
                )
                db.session.commit()
                # Refresh to get updated count for the response envelope
                db.session.refresh(key_entry)
            except Exception as e:
                log.error("Failed to update usage counters: %s", e)
                try:
                    db.session.rollback()
                except Exception:
                    pass
                return jsonify({"error": "Usage tracking error"}), 500

            # Attach context to request
            request.api_tier = tier
            request.api_key_entry = key_entry
            request.api_key_prefix = key_entry.key_prefix
            request.api_limit = limit

            # Execute the view
            response = f(*args, **kwargs)

            # Log usage (best-effort — never fail the response)
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            try:
                status_code = response[1] if isinstance(response, tuple) else 200
                log_entry = ApiUsageLog(
                    key_prefix=key_entry.key_prefix,
                    endpoint=request.path,
                    response_ms=elapsed_ms,
                    status_code=status_code,
                    ip_hash=_ip_hash(),
                )
                db.session.add(log_entry)
                db.session.commit()
            except Exception as e:
                log.warning("Usage log write failed (non-fatal): %s", e)
                try:
                    db.session.rollback()
                except Exception:
                    pass

            return response
        return decorated
    return decorator


# ── Data Helpers ──────────────────────────────────────────────────────────────

def _get_topics():
    """Top 10 topics from published articles in last 24hr with trend direction."""
    from models import Article
    cutoff_24h = _utcnow() - timedelta(hours=24)
    cutoff_4d = _utcnow() - timedelta(days=4)
    try:
        # Current 24hr counts
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff_24h)
            .with_entities(Article.category, func.count(Article.id).label("cnt"))
            .group_by(Article.category)
            .order_by(func.count(Article.id).desc())
            .limit(10)
            .all()
        )

        # Prior 3 days average (for trend direction)
        prior_rows = (
            Article.query
            .filter(
                Article.published == True,
                Article.created_at > cutoff_4d,
                Article.created_at <= cutoff_24h,
            )
            .with_entities(Article.category, func.count(Article.id).label("cnt"))
            .group_by(Article.category)
            .all()
        )
        # Average per day over 3 days
        prior_avg = {r.category: r.cnt / 3.0 for r in prior_rows if r.category}

        results = []
        for r in rows:
            if not r.category:
                continue
            avg = prior_avg.get(r.category, 0)
            trend = "rising" if r.cnt > avg else "stable"
            results.append({
                "topic": r.category,
                "count": r.cnt,
                "trend_direction": trend,
            })
        return results
    except Exception as e:
        log.error("topics query failed: %s", e)
        return []


def _get_entities():
    """Scan last 50 article titles for known Bitcoin entities with sentiment."""
    from models import Article
    cutoff = _utcnow() - timedelta(hours=24)
    try:
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff)
            .with_entities(Article.title, Article.summary)
            .order_by(Article.created_at.desc())
            .limit(50)
            .all()
        )

        positive_words = {"bull", "surge", "rally", "ath", "adoption", "record", "inflow",
                          "growth", "gain", "buy", "rise", "pump", "approved", "success"}
        negative_words = {"bear", "crash", "dump", "ban", "fear", "panic", "outflow",
                          "sell", "drop", "hack", "reject", "fail", "loss", "decline"}

        results = []
        for entity in KNOWN_ENTITIES:
            mentions = 0
            pos_count = 0
            neg_count = 0
            entity_lower = entity.lower()

            for r in rows:
                blob = f"{r.title or ''} {r.summary or ''}".lower()
                if entity_lower in blob:
                    mentions += 1
                    # Sentiment from surrounding words
                    pos_count += sum(1 for w in positive_words if w in blob)
                    neg_count += sum(1 for w in negative_words if w in blob)

            if mentions > 0:
                total = pos_count + neg_count
                if total == 0:
                    sentiment = "neutral"
                    score = 0.0
                elif pos_count > neg_count:
                    sentiment = "positive"
                    score = round(pos_count / total, 2)
                elif neg_count > pos_count:
                    sentiment = "negative"
                    score = round(-neg_count / total, 2)
                else:
                    sentiment = "neutral"
                    score = 0.0
            else:
                sentiment = "neutral"
                score = 0.0

            results.append({
                "entity": entity,
                "mentions": mentions,
                "sentiment": sentiment,
                "sentiment_score": score,
            })

        return sorted(results, key=lambda x: x["mentions"], reverse=True)
    except Exception as e:
        log.error("entities query failed: %s", e)
        return []


def _get_sentiment():
    """Return (score 0-100, label, article_count, as_of).

    Algorithm: average of (article score field if exists, else title keyword scoring).
    Positive keywords: +10 each. Negative keywords: -10 each. Normalize to 0-100.
    """
    from models import Article
    cutoff = _utcnow() - timedelta(hours=24)

    # Try SentimentBuffer first
    try:
        from models import SentimentBuffer
        latest = (
            SentimentBuffer.query
            .filter(SentimentBuffer.timestamp > cutoff)
            .order_by(SentimentBuffer.timestamp.desc())
            .first()
        )
        if latest and latest.sentiment_score is not None:
            raw = latest.sentiment_score
            if -1.0 <= raw <= 1.0:
                score = int((raw + 1) / 2 * 100)
            elif 0 <= raw <= 100:
                score = int(raw)
            else:
                score = 50
            label = "Bullish" if score > 60 else ("Bearish" if score < 40 else "Neutral")
            return score, label, 0, latest.timestamp
    except Exception:
        pass

    # Keyword heuristic on article titles
    try:
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff)
            .with_entities(Article.title, Article.summary)
            .limit(100)
            .all()
        )
        article_count = len(rows)
        raw_score = 50  # start neutral
        for r in rows:
            blob = f"{r.title or ''} {r.summary or ''}".lower()
            for kw in POSITIVE_KEYWORDS:
                if kw in blob:
                    raw_score += 10
            for kw in NEGATIVE_KEYWORDS:
                if kw in blob:
                    raw_score -= 10

        # Normalize to 0-100
        score = max(0, min(100, raw_score))
        label = "Bullish" if score > 60 else ("Bearish" if score < 40 else "Neutral")
        return score, label, article_count, _utcnow()
    except Exception as e:
        log.error("sentiment fallback failed: %s", e)
        return 50, "Neutral", 0, None


def _get_breaking():
    """Articles published in last 2hr with score > 80 (or all if score not set)."""
    from models import Article
    cutoff = _utcnow() - timedelta(hours=BREAKING_LOOKBACK_HOURS)
    try:
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff)
            .order_by(Article.created_at.desc())
            .limit(20)
            .all()
        )
        # Filter by score > 80 if score field exists, else include all (limit 10)
        filtered = []
        for a in rows:
            score = getattr(a, "score", None) or getattr(a, "relevance_score", None)
            if score is not None and score <= 80:
                continue
            filtered.append({
                "id": a.id,
                "title": a.title,
                "url": f"https://protocolpulse.io/article/{a.id}",
                "published_at": _iso(a.created_at),
                "score": score,
                "category": a.category,
            })
            if len(filtered) >= 10:
                break
        return filtered
    except Exception as e:
        log.error("breaking query failed: %s", e)
        return []


def _get_network_stats() -> dict:
    """Fetch Bitcoin network stats from public APIs with timeout + graceful degradation."""
    stats = {
        "price": None,
        "price_change_24h": None,
        "hashrate_eh": None,
        "difficulty": None,
        "block_height": None,
        "next_halving_blocks": None,
    }

    # BTC price from internal API or CoinGecko fallback
    try:
        # Try internal /api/btc-price first
        from flask import current_app
        with current_app.test_client() as client:
            resp = client.get("/api/btc-price")
            if resp.status_code == 200:
                d = resp.get_json()
                stats["price"] = d.get("price") or d.get("usd")
                stats["price_change_24h"] = d.get("change_24h") or d.get("price_change_24h")
    except Exception:
        pass

    # Fallback: CoinGecko for price if not available
    if stats["price"] is None:
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
                timeout=EXTERNAL_TIMEOUT,
            )
            if resp.ok:
                d = resp.json().get("bitcoin", {})
                stats["price"] = d.get("usd")
                stats["price_change_24h"] = round(d.get("usd_24h_change", 0), 2)
        except Exception as e:
            log.warning("price fetch failed: %s", e)

    # Block height via mempool.space
    try:
        resp = requests.get(
            "https://mempool.space/api/blocks/tip/height",
            timeout=EXTERNAL_TIMEOUT,
        )
        if resp.ok:
            stats["block_height"] = int(resp.text.strip())
    except Exception as e:
        log.warning("block height fetch failed: %s", e)

    # Difficulty via mempool.space
    try:
        resp = requests.get(
            "https://mempool.space/api/v1/difficulty-adjustment",
            timeout=EXTERNAL_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        if resp.ok:
            d = resp.json()
            stats["difficulty"] = d.get("difficulty")
    except Exception as e:
        log.warning("difficulty fetch failed: %s", e)

    # Hashrate via blockchain.info
    try:
        resp = requests.get(
            "https://api.blockchain.info/stats",
            timeout=EXTERNAL_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        if resp.ok:
            d = resp.json()
            hash_rate_gh = d.get("hash_rate", 0)  # GH/s
            stats["hashrate_eh"] = round(hash_rate_gh / 1_000_000_000, 2)
    except Exception as e:
        log.warning("hashrate fetch failed: %s", e)

    # Halving countdown
    height = stats.get("block_height")
    if height:
        stats["next_halving_blocks"] = max(0, NEXT_HALVING_BLOCK - height)

    return stats


# ── Status Endpoint (no auth) ─────────────────────────────────────────────────

@terminal_bp.route("/api/v2/terminal/status", methods=["GET"])
def terminal_status():
    """Public status endpoint — no auth required."""
    return jsonify({
        "status": "operational",
        "version": "1.0",
        "tiers": ["commander"],
        "docs": "https://protocolpulse.io/terminal",
    })


# ── API Endpoints ─────────────────────────────────────────────────────────────

@terminal_bp.route("/api/v2/terminal/topics", methods=["GET"])
@require_terminal_auth("commander")
def terminal_topics():
    """Top topics from the last 24hr of published articles."""
    tier = getattr(request, "api_tier", "commander")
    entry = getattr(request, "api_key_entry", None)
    requests_today = entry.requests_today if entry else 0
    limit = getattr(request, "api_limit", COMMANDER_DAILY_LIMIT)

    topics = _get_topics()
    return jsonify(_terminal_response(
        endpoint="topics",
        data={"topics": topics, "count": len(topics), "window_hours": 24},
        tier=tier,
        requests_today=requests_today,
        limit=limit,
    ))


@terminal_bp.route("/api/v2/terminal/entities", methods=["GET"])
@require_terminal_auth("commander")
def terminal_entities():
    """Named entities and keyword frequency from the last 24hr."""
    tier = getattr(request, "api_tier", "commander")
    entry = getattr(request, "api_key_entry", None)
    requests_today = entry.requests_today if entry else 0
    limit = getattr(request, "api_limit", COMMANDER_DAILY_LIMIT)

    entities = _get_entities()
    return jsonify(_terminal_response(
        endpoint="entities",
        data={"entities": entities, "count": len(entities), "window_hours": 24},
        tier=tier,
        requests_today=requests_today,
        limit=limit,
    ))


@terminal_bp.route("/api/v2/terminal/sentiment", methods=["GET"])
@require_terminal_auth("commander")
def terminal_sentiment():
    """BTC sentiment score 0-100 (0=bearish, 50=neutral, 100=bullish)."""
    tier = getattr(request, "api_tier", "commander")
    entry = getattr(request, "api_key_entry", None)
    requests_today = entry.requests_today if entry else 0
    limit = getattr(request, "api_limit", COMMANDER_DAILY_LIMIT)

    score, label, article_count, computed_at = _get_sentiment()

    return jsonify(_terminal_response(
        endpoint="sentiment",
        data={
            "score": score,
            "label": label,
            "article_count": article_count,
            "computed_at": _iso(computed_at) if computed_at else _iso(_utcnow()),
        },
        tier=tier,
        requests_today=requests_today,
        limit=limit,
    ))


@terminal_bp.route("/api/v2/terminal/breaking", methods=["GET"])
@require_terminal_auth("commander")
def terminal_breaking():
    """Breaking articles from the last 2 hours."""
    tier = getattr(request, "api_tier", "commander")
    entry = getattr(request, "api_key_entry", None)
    requests_today = entry.requests_today if entry else 0
    limit = getattr(request, "api_limit", COMMANDER_DAILY_LIMIT)

    articles = _get_breaking()
    return jsonify(_terminal_response(
        endpoint="breaking",
        data={
            "articles": articles,
            "count": len(articles),
            "window_hours": BREAKING_LOOKBACK_HOURS,
            "has_breaking": len(articles) > 0,
        },
        tier=tier,
        requests_today=requests_today,
        limit=limit,
    ))


@terminal_bp.route("/api/v2/terminal/network", methods=["GET"])
@require_terminal_auth("commander")
def terminal_network():
    """Live Bitcoin network: hashrate, difficulty, block height, halving countdown."""
    tier = getattr(request, "api_tier", "commander")
    entry = getattr(request, "api_key_entry", None)
    requests_today = entry.requests_today if entry else 0
    limit = getattr(request, "api_limit", COMMANDER_DAILY_LIMIT)

    stats = _get_network_stats()
    return jsonify(_terminal_response(
        endpoint="network",
        data=stats,
        tier=tier,
        requests_today=requests_today,
        limit=limit,
    ))


# ── Stripe Subscribe ──────────────────────────────────────────────────────────

@terminal_bp.route("/api/v2/terminal/subscribe", methods=["POST"])
def terminal_subscribe():
    """Create a Stripe Checkout session for Commander ($49/mo) subscription.

    Body (JSON): {"email": "user@example.com", "tier": "commander"}
    Returns:     {"checkout_url": "https://checkout.stripe.com/...", "session_id": "..."}
    """
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not stripe_key:
        return jsonify({
            "error": "Payments not yet enabled. Email team@protocolpulse.io for early access.",
            "pricing": {"commander": {"price": "$49/month", "requests": "1,000/day"}},
        }), 503

    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    tier = (body.get("tier") or "commander").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400
    if tier != "commander":
        return jsonify({"error": "Only 'commander' tier is available at launch."}), 400

    try:
        import stripe as stripe_lib
        stripe_lib.api_key = stripe_key

        price_id = os.environ.get("STRIPE_COMMANDER_PRICE_ID", "").strip()
        if not price_id:
            return jsonify({"error": "Stripe price not configured", "setup": "See /terminal#setup"}), 503

        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://protocolpulse.io/terminal/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://protocolpulse.io/terminal#pricing",
            metadata={"tier": tier},
        )
        return jsonify({"checkout_url": session.url, "session_id": session.id})
    except Exception as e:
        log.error("Stripe checkout error: %s", e)
        return jsonify({"error": f"Payment processing error: {e}"}), 500


# ── Stripe Webhook ────────────────────────────────────────────────────────────

@terminal_bp.route("/api/v2/terminal/webhook", methods=["POST"])
def terminal_webhook():
    """Stripe webhook: checkout.session.completed → generate API key → email subscriber.

    Env required: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
    """
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

    if not stripe_key or not webhook_secret:
        return jsonify({"error": "Stripe not configured"}), 503

    payload = request.get_data(as_text=False)
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        import stripe as stripe_lib
        stripe_lib.api_key = stripe_key
        event = stripe_lib.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        log.warning("Stripe webhook verification failed: %s", e)
        return jsonify({"error": f"Webhook verification failed: {e}"}), 400

    from app import db
    from models import ApiKey

    event_type = event.get("type", "")

    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        tier = (session_obj.get("metadata") or {}).get("tier", "commander")
        email = (
            session_obj.get("customer_email")
            or (session_obj.get("customer_details") or {}).get("email", "")
        )
        stripe_customer_id = session_obj.get("customer", "")
        stripe_subscription_id = session_obj.get("subscription", "")
        stripe_session_id = session_obj.get("id", "")

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            log.error("Webhook: invalid or missing email in session %s (got: %r)", stripe_session_id, email)
            return jsonify({"error": "Invalid or missing subscriber email in session"}), 400

        # Generate key: pp_cmd_{32 hex chars}
        raw_key = f"pp_cmd_{secrets.token_hex(16)}"
        key_hash = _sha256(raw_key)
        key_prefix = raw_key[:8]   # "pp_cmd_x" (first 8 chars)

        try:
            new_key = ApiKey(
                key_hash=key_hash,
                key_prefix=key_prefix,
                tier=tier,
                subscriber_email=email,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                stripe_session_id=stripe_session_id,
            )
            db.session.add(new_key)
            db.session.commit()
        except Exception as e:
            log.error("Failed to persist API key for %s: %s", email, e)
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({"error": "Key storage failed"}), 500

        # Email the raw key (best-effort)
        _send_api_key_email(email, raw_key, tier)
        log.info("API key provisioned for %s (%s) — prefix: %s", email, tier, key_prefix)
        return jsonify({"status": "key_generated", "tier": tier, "prefix": key_prefix})

    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub = event["data"]["object"]
        stripe_sub_id = sub.get("id", "")
        if stripe_sub_id:
            try:
                key_entry = ApiKey.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
                if key_entry:
                    key_entry.active = False
                    db.session.commit()
                    log.info("API key deactivated for subscription %s", stripe_sub_id)
            except Exception as e:
                log.error("Failed to deactivate key: %s", e)
                try:
                    db.session.rollback()
                except Exception:
                    pass
        return jsonify({"status": "key_deactivated"})

    return jsonify({"status": "ignored", "event_type": event_type})


@terminal_bp.route("/webhook/stripe/terminal", methods=["POST"])
def terminal_webhook_alias():
    """Alias for the Terminal Stripe webhook (spec-required path)."""
    return terminal_webhook()


def _send_api_key_email(email: str, raw_key: str, tier: str):
    """Send API key via Resend. Best-effort — log on failure, never raise."""
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not resend_key:
        log.warning("RESEND_API_KEY not set — skipping key email to %s", email)
        return

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            timeout=10,
            headers={
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "Pulse Terminal <terminal@protocolpulse.io>",
                "to": [email],
                "subject": f"Your Protocol Pulse Commander API Key — {raw_key[:12]}...",
                "html": f"""
<div style="font-family:monospace;background:#000;color:#fff;padding:32px;max-width:520px;">
  <h2 style="color:#dc2626;font-size:1.4rem;margin-bottom:16px;">PULSE TERMINAL — COMMANDER</h2>
  <p style="color:#aaa;margin-bottom:24px;">Your API key is active. Store it securely — it will not be shown again.</p>
  <div style="background:#0a0a0a;border:1px solid #dc2626;padding:16px;border-radius:4px;margin-bottom:24px;">
    <code style="color:#dc2626;font-size:1.1rem;word-break:break-all;">{raw_key}</code>
  </div>
  <p style="color:#aaa;margin-bottom:8px;"><strong style="color:#fff;">Quick start:</strong></p>
  <pre style="background:#111;padding:12px;border-radius:4px;font-size:0.85rem;overflow-x:auto;">curl https://protocolpulse.io/api/v2/terminal/topics \\
  -H "X-PP-API-Key: {raw_key}"</pre>
  <p style="color:#555;margin-top:24px;font-size:0.8rem;">
    Rate limit: 1,000 requests/day, resets at 00:00 UTC.<br>
    Docs: <a href="https://protocolpulse.io/terminal" style="color:#dc2626;">protocolpulse.io/terminal</a>
  </p>
</div>
""",
            },
        )
        if not resp.ok:
            log.error("Resend API error (%s): %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.error("Email delivery exception for %s: %s", email, e)


# ── Success + Docs ────────────────────────────────────────────────────────────

@terminal_bp.route("/terminal/success")
def terminal_success():
    """Post-Stripe-checkout confirmation page."""
    return render_template("pulse_terminal_success.html")


@terminal_bp.route("/api/v2/terminal/docs")
def terminal_docs():
    """Redirect to the docs section of the Terminal landing page."""
    return redirect("/terminal#docs")
