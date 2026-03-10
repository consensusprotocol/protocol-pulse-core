"""
routes_premium_api.py — Protocol Pulse Terminal API Blueprint
Handles: Terminal API endpoints, Stripe checkout for API subscriptions,
         subscriber dashboard, API playground, webhook delivery.

Blueprint prefix: (none — registered at root)
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps

import requests as http_requests
from flask import (
    Blueprint, Response, jsonify, redirect, render_template,
    request, session, stream_with_context, url_for
)

from app import db
import models
from services.api_key_service import (
    require_api_key,
    generate_api_key,
    generate_webhook_secret,
    provision_demo_key,
    get_hourly_usage_sparkline,
    TIER_ENTITLEMENTS,
    TIER_LIMITS,
)
from services.stripe_service import (
    validate_webhook_signature,
    provision_terminal_subscriber,
    cancel_terminal_subscriber,
)

logger = logging.getLogger("PremiumAPI")

premium_api = Blueprint("premium_api", __name__)

DEMO_KEY = "pp_demo_00000000000000000000000000000001"

# ─── Helpers ──────────────────────────────────────────────────


def _send_welcome_email(email: str, api_key: str) -> bool:
    """Send welcome email with API key via Resend. Returns True on success."""
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        logger.warning("RESEND_API_KEY not set — skipping welcome email for %s", email)
        return False
    try:
        resp = http_requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json={
                "from": "Protocol Pulse <noreply@protocolpulse.io>",
                "to": [email],
                "subject": "Your Protocol Pulse Commander API Key",
                "html": f"""
<div style="background:#0a0a0f;color:#eef2ff;font-family:JetBrains Mono,monospace;padding:40px;max-width:600px;margin:0 auto;">
  <div style="border-bottom:2px solid #f8c15c;padding-bottom:20px;margin-bottom:30px;">
    <h1 style="color:#f8c15c;font-size:18px;letter-spacing:0.1em;margin:0;">PROTOCOL PULSE</h1>
    <p style="color:#95a0ba;font-size:12px;margin:4px 0 0;">COMMANDER TERMINAL API</p>
  </div>
  <h2 style="color:#eef2ff;font-size:20px;">Your API Key Is Ready</h2>
  <p style="color:#95a0ba;">Welcome to the Protocol Pulse Commander Tier. Your API key grants access to real-time Bitcoin intelligence data.</p>
  <div style="background:#1a1a2e;border:1px solid rgba(248,193,92,0.3);border-radius:8px;padding:20px;margin:24px 0;">
    <p style="color:#95a0ba;font-size:11px;margin:0 0 8px;letter-spacing:0.15em;">YOUR API KEY</p>
    <code style="color:#f8c15c;font-size:13px;word-break:break-all;">{api_key}</code>
  </div>
  <p style="color:#95a0ba;font-size:13px;">Usage: <code style="color:#eef2ff;">X-API-Key: {api_key}</code></p>
  <p style="color:#95a0ba;font-size:13px;">Rate limit: 1,000 requests/hour | <a href="https://protocolpulse.io/api/dashboard" style="color:#f8c15c;">Manage your key →</a></p>
  <div style="margin-top:30px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.1);">
    <p style="color:#95a0ba;font-size:11px;">Quick start:</p>
    <pre style="background:#0d1118;border:1px solid rgba(255,255,255,0.08);border-radius:6px;padding:12px;font-size:12px;color:#5de4ff;overflow-x:auto;">curl https://protocolpulse.io/api/v2/terminal/topics \\
  -H "X-API-Key: {api_key}"</pre>
  </div>
  <p style="color:#95a0ba;font-size:11px;margin-top:30px;">
    <a href="https://protocolpulse.io/api/playground" style="color:#f8c15c;">Try the Playground</a> ·
    <a href="https://protocolpulse.io/api/dashboard" style="color:#f8c15c;">Dashboard</a>
  </p>
</div>
""",
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info("Welcome email sent to %s", email)
            return True
        logger.warning("Resend returned %d for %s: %s", resp.status_code, email, resp.text[:200])
        return False
    except Exception as e:
        logger.error("Welcome email failed for %s: %s", email, e)
        return False


def _json_meta(subscriber) -> dict:
    """Build the standard meta block for API responses."""
    from services.api_key_service import TIER_LIMITS
    limit = TIER_LIMITS.get(subscriber.tier, 1000)
    # Count requests in last hour from log
    try:
        window = datetime.utcnow() - timedelta(hours=1)
        used = db.session.query(db.func.count(models.ApiRequestLog.id)).filter(
            models.ApiRequestLog.api_key == subscriber.api_key,
            models.ApiRequestLog.created_at >= window,
        ).scalar() or 0
    except Exception:
        used = 0
    return {
        "tier": subscriber.tier,
        "requests_this_hour": used,
        "requests_remaining": max(0, limit - used) if limit != -1 else 999999,
        "rate_limit": limit,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def _get_topics_data() -> list:
    """Extract top 20 topics from recent articles."""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        articles = models.Article.query.filter(
            models.Article.published.is_(True),
            models.Article.created_at >= cutoff,
        ).order_by(models.Article.created_at.desc()).limit(100).all()

        topic_counts: dict = {}
        for art in articles:
            tags_raw = art.tags or ""
            if tags_raw.startswith("["):
                try:
                    tags = json.loads(tags_raw)
                except Exception:
                    tags = []
            else:
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            for tag in tags:
                tag_clean = tag.strip().lower()
                if tag_clean:
                    topic_counts[tag_clean] = topic_counts.get(tag_clean, 0) + 1

        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        return [{"topic": t, "mentions": c, "trend": "rising" if c > 3 else "stable"}
                for t, c in sorted_topics]
    except Exception as e:
        logger.warning("topics data error: %s", e)
        return [{"topic": "bitcoin", "mentions": 10, "trend": "rising"},
                {"topic": "halving", "mentions": 7, "trend": "stable"}]


def _get_entities_data() -> dict:
    """Extract named entities from recent article tags/content."""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        articles = models.Article.query.filter(
            models.Article.published.is_(True),
            models.Article.created_at >= cutoff,
        ).limit(50).all()

        people, orgs, coins = {}, {}, {}
        coin_keywords = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "lightning"]
        people_keywords = ["saylor", "musk", "gensler", "warren", "yellen", "powell"]
        org_keywords = ["fed", "sec", "coinbase", "grayscale", "blackrock", "microstrategy", "galaxy"]

        for art in articles:
            text = (art.title + " " + (art.summary or "")).lower()
            for kw in coin_keywords:
                if kw in text:
                    coins[kw] = coins.get(kw, 0) + 1
            for kw in people_keywords:
                if kw in text:
                    people[kw] = people.get(kw, 0) + 1
            for kw in org_keywords:
                if kw in text:
                    orgs[kw] = orgs.get(kw, 0) + 1

        return {
            "people": [{"name": k, "mentions": v} for k, v in sorted(people.items(), key=lambda x: -x[1])[:10]],
            "organizations": [{"name": k, "mentions": v} for k, v in sorted(orgs.items(), key=lambda x: -x[1])[:10]],
            "coins": [{"symbol": k.upper(), "mentions": v} for k, v in sorted(coins.items(), key=lambda x: -x[1])[:5]],
        }
    except Exception as e:
        logger.warning("entities data error: %s", e)
        return {"people": [], "organizations": [], "coins": [{"symbol": "BTC", "mentions": 20}]}


def _get_sentiment_data() -> dict:
    """Return latest sentiment from SentimentSnapshot or fallback."""
    try:
        snap = models.SentimentSnapshot.query.order_by(
            models.SentimentSnapshot.computed_at.desc()
        ).first()
        if snap:
            top_kw = []
            if snap.top_keywords:
                try:
                    top_kw = json.loads(snap.top_keywords)
                except Exception:
                    top_kw = snap.top_keywords.split(",")[:5] if snap.top_keywords else []
            return {
                "score": round(snap.score, 1),
                "state": snap.state or "NEUTRAL",
                "label": snap.state_label or "Neutral",
                "velocity": round(snap.velocity or 0, 2),
                "top_keywords": top_kw[:5],
                "sample_size": snap.sample_size or 0,
                "computed_at": snap.computed_at.isoformat() + "Z" if snap.computed_at else None,
            }
    except Exception as e:
        logger.warning("sentiment data error: %s", e)
    return {"score": 52.0, "state": "NEUTRAL", "label": "Neutral", "velocity": 0.0,
            "top_keywords": ["bitcoin", "network"], "sample_size": 0, "computed_at": None}


def _get_breaking_data() -> list:
    """Articles published in last 2 hours."""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=2)
        articles = models.Article.query.filter(
            models.Article.published.is_(True),
            models.Article.created_at >= cutoff,
        ).order_by(models.Article.created_at.desc()).limit(10).all()
        return [{
            "id": a.id,
            "title": a.title,
            "summary": (a.summary or "")[:300],
            "category": a.category or "bitcoin",
            "url": f"/articles/{a.id}",
            "published_at": a.created_at.isoformat() + "Z" if a.created_at else None,
        } for a in articles]
    except Exception as e:
        logger.warning("breaking data error: %s", e)
        return []


def _get_signal_data() -> dict:
    """Compute composite Signal Strength 0-100."""
    try:
        sentiment = _get_sentiment_data()
        breaking = _get_breaking_data()
        topics = _get_topics_data()

        sentiment_score = float(sentiment.get("score", 50))
        breaking_score = min(100, len(breaking) * 12)  # up to ~8 articles = 100
        topic_score = min(100, len(topics) * 5)
        velocity_bonus = min(20, abs(float(sentiment.get("velocity", 0))) * 10)

        composite = (sentiment_score * 0.4 + breaking_score * 0.3 + topic_score * 0.2 + velocity_bonus * 0.1)
        composite = round(min(100, max(0, composite)), 1)

        state = "EXTREME FEAR" if composite < 20 else \
                "FEAR" if composite < 40 else \
                "NEUTRAL" if composite < 60 else \
                "GREED" if composite < 80 else "EXTREME GREED"

        return {
            "composite_score": composite,
            "state": state,
            "components": {
                "sentiment": round(sentiment_score, 1),
                "breaking_activity": round(breaking_score, 1),
                "topic_velocity": round(topic_score, 1),
                "momentum_bonus": round(velocity_bonus, 1),
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.warning("signal data error: %s", e)
        return {"composite_score": 50.0, "state": "NEUTRAL", "components": {},
                "timestamp": datetime.utcnow().isoformat() + "Z"}


# ─── Terminal API Endpoints ────────────────────────────────────


@premium_api.route("/api/v2/terminal/topics", methods=["GET"])
@require_api_key
def terminal_topics(_subscriber=None):
    data = _get_topics_data()
    return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200


@premium_api.route("/api/v2/terminal/entities", methods=["GET"])
@require_api_key
def terminal_entities(_subscriber=None):
    data = _get_entities_data()
    return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200


@premium_api.route("/api/v2/terminal/sentiment", methods=["GET"])
@require_api_key
def terminal_sentiment(_subscriber=None):
    data = _get_sentiment_data()
    return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200


@premium_api.route("/api/v2/terminal/breaking", methods=["GET"])
@require_api_key
def terminal_breaking(_subscriber=None):
    data = _get_breaking_data()
    return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200


@premium_api.route("/api/v2/terminal/signal", methods=["GET"])
@require_api_key
def terminal_signal(_subscriber=None):
    data = _get_signal_data()
    return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200


@premium_api.route("/api/v2/terminal/status", methods=["GET"])
@require_api_key
def terminal_status(_subscriber=None):
    """Subscriber usage stats and quota."""
    sparkline = get_hourly_usage_sparkline(_subscriber.api_key, db, models)
    data = {
        "email": _subscriber.email,
        "tier": _subscriber.tier,
        "api_key_prefix": _subscriber.api_key[:12] + "...",
        "requests_total": _subscriber.requests_total or 0,
        "rate_limit_per_hour": _subscriber.rate_limit_per_hour,
        "subscription_status": _subscriber.subscription_status,
        "current_period_end": _subscriber.current_period_end.isoformat() + "Z"
            if _subscriber.current_period_end else None,
        "created_at": _subscriber.created_at.isoformat() + "Z" if _subscriber.created_at else None,
        "last_used_at": _subscriber.last_used_at.isoformat() + "Z" if _subscriber.last_used_at else None,
        "entitlements": _subscriber.get_entitlements(),
        "hourly_sparkline": sparkline,
    }
    return jsonify({"data": data, "meta": _json_meta(_subscriber)}), 200


@premium_api.route("/api/v2/terminal/stream", methods=["GET"])
@require_api_key
def terminal_stream(_subscriber=None):
    """SSE stream of breaking news. Commander only (entitlement: stream)."""
    channel = request.args.get("channel", "all")  # breaking|sentiment|all

    def generate():
        """SSE generator — polls for new articles every 15s."""
        last_article_id = None
        try:
            latest = models.Article.query.filter_by(published=True).order_by(
                models.Article.created_at.desc()
            ).first()
            if latest:
                last_article_id = latest.id
        except Exception:
            pass

        yield f"data: {json.dumps({'type': 'connected', 'channel': channel, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        heartbeat_counter = 0
        while True:
            time.sleep(15)
            heartbeat_counter += 1

            try:
                # Check for new breaking articles
                if channel in ("breaking", "all"):
                    query = models.Article.query.filter(
                        models.Article.published.is_(True),
                    ).order_by(models.Article.created_at.desc()).limit(5)

                    new_articles = []
                    for art in query.all():
                        if last_article_id is None or art.id > last_article_id:
                            new_articles.append(art)
                            if last_article_id is None or art.id > last_article_id:
                                last_article_id = art.id

                    for art in new_articles:
                        payload = {
                            "type": "breaking_article",
                            "data": {
                                "id": art.id,
                                "title": art.title,
                                "summary": (art.summary or "")[:200],
                                "category": art.category or "bitcoin",
                                "url": f"/articles/{art.id}",
                                "published_at": art.created_at.isoformat() + "Z" if art.created_at else None,
                            },
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        yield f"data: {json.dumps(payload)}\n\n"

                # Check for sentiment updates
                if channel in ("sentiment", "all") and heartbeat_counter % 4 == 0:  # every ~60s
                    sentiment = _get_sentiment_data()
                    payload = {
                        "type": "sentiment_update",
                        "data": sentiment,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                # Heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            except GeneratorExit:
                return
            except Exception as e:
                logger.warning("SSE stream error: %s", e)
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error — reconnecting'})}\n\n"
                time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@premium_api.route("/api/v2/terminal/docs", methods=["GET"])
def terminal_docs():
    """OpenAPI-style documentation (public)."""
    docs = {
        "title": "Protocol Pulse Terminal API",
        "version": "2.0",
        "base_url": "https://protocolpulse.io",
        "auth": {
            "type": "API Key",
            "header": "X-API-Key",
            "example": "X-API-Key: pp_cmd_your_key_here",
        },
        "endpoints": [
            {"method": "GET", "path": "/api/v2/terminal/topics", "description": "Top 20 trending topics (last 24h)", "tier": "all"},
            {"method": "GET", "path": "/api/v2/terminal/entities", "description": "Named entities: people, orgs, coins", "tier": "commander+"},
            {"method": "GET", "path": "/api/v2/terminal/sentiment", "description": "Aggregate sentiment score + components", "tier": "all"},
            {"method": "GET", "path": "/api/v2/terminal/breaking", "description": "Articles published in last 2 hours", "tier": "all"},
            {"method": "GET", "path": "/api/v2/terminal/signal", "description": "Composite Signal Strength 0-100", "tier": "commander+"},
            {"method": "GET", "path": "/api/v2/terminal/status", "description": "Your usage stats and quota", "tier": "all"},
            {"method": "GET", "path": "/api/v2/terminal/stream", "description": "SSE breaking news stream", "tier": "commander"},
        ],
        "rate_limits": {
            "demo": "20 requests/hour",
            "commander": "1,000 requests/hour",
            "enterprise": "Unlimited",
        },
        "get_key": "https://protocolpulse.io/premium",
    }
    return jsonify(docs), 200


# ─── Stripe Checkout ──────────────────────────────────────────


@premium_api.route("/api/v2/terminal/subscribe", methods=["POST"])
def terminal_subscribe():
    """Create Stripe Checkout session for Terminal API subscription."""
    try:
        import stripe
    except ImportError:
        return jsonify({"error": "Stripe not installed. Run: pip install stripe"}), 500

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400

    # CSRF protection: validate request origin
    allowed_origins = {
        os.environ.get("SERVER_NAME", "protocolpulse.io"),
        "protocolpulse.io",
        "www.protocolpulse.io",
        "127.0.0.1",
        "localhost",
    }
    origin = request.headers.get("Origin", "") or request.headers.get("Referer", "")
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        if parsed.hostname and parsed.hostname not in allowed_origins:
            logger.warning("CSRF: blocked subscribe from origin %s", origin)
            return jsonify({"error": "Invalid request origin", "code": "INVALID_ORIGIN"}), 403

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({
            "error": "Stripe not configured. Contact support@protocolpulse.io",
            "code": "STRIPE_NOT_CONFIGURED"
        }), 503

    price_id = os.environ.get("STRIPE_COMMANDER_PRICE_ID")
    if not price_id:
        return jsonify({
            "error": "Product not configured. Contact support@protocolpulse.io",
            "code": "PRICE_NOT_CONFIGURED"
        }), 503

    try:
        stripe.api_key = stripe_key
        # Set SDK-level timeout so a Stripe outage never hangs a Flask worker
        stripe.default_http_client = stripe.RequestsClient(timeout=10)
        # Idempotency key: prevents duplicate checkout sessions from retries/double-clicks
        # 5-minute window so legitimate retries after failures can succeed
        idempotency_key = hashlib.sha256(
            f"checkout-{email}-{int(time.time() // 300)}".encode()
        ).hexdigest()
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=request.url_root.rstrip("/") + "/subscribe/terminal/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.url_root.rstrip("/") + "/premium",
            metadata={
                "subscription_type": "terminal_api",
                "tier": "commander",
                "email": email,
            },
            idempotency_key=idempotency_key,
        )
        return jsonify({"checkout_url": session.url, "session_id": session.id}), 200
    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        return jsonify({"error": "Checkout failed. Please try again.", "detail": str(e)[:200]}), 500


@premium_api.route("/subscribe/terminal/success", methods=["GET"])
def terminal_subscribe_success():
    """Post-Stripe success page — shows API key."""
    session_id = request.args.get("session_id", "")
    api_key = None
    email = None
    error = None

    if session_id:
        try:
            import stripe
            stripe_key = os.environ.get("STRIPE_SECRET_KEY")
            if stripe_key:
                stripe.api_key = stripe_key
                checkout_session = stripe.checkout.Session.retrieve(
                    session_id,
                    expand=["customer"],
                )
                customer_email = (checkout_session.get("customer_details") or {}).get("email")
                if customer_email:
                    email = customer_email
                    # Look up subscriber
                    sub = models.ApiSubscriber.query.filter_by(email=customer_email).first()
                    if sub:
                        api_key = sub.api_key
                    else:
                        # Trigger provisioning (webhook may not have fired yet)
                        result = provision_terminal_subscriber(dict(checkout_session), db, models)
                        if result["success"]:
                            api_key = result["api_key"]
                            # Welcome email sent by webhook handler (authoritative) — not here
        except Exception as e:
            logger.error("Success page error for session %s: %s", session_id, e)
            error = "Could not retrieve your subscription details. Check your email for your API key."

    return render_template(
        "subscribe_terminal_success.html",
        api_key=api_key,
        email=email,
        error=error,
        session_id=session_id,
    )


@premium_api.route("/webhook/stripe/terminal", methods=["POST"])
def terminal_stripe_webhook():
    """Stripe webhook handler for Terminal API subscriptions only."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.critical("STRIPE_WEBHOOK_SECRET not configured — rejecting all webhook requests. "
                        "Set STRIPE_WEBHOOK_SECRET in .env to enable Terminal API subscriptions.")
        from flask import abort
        abort(500)
    event = validate_webhook_signature(payload, sig_header, webhook_secret)
    if not event:
        logger.warning("Invalid Stripe webhook signature from %s", request.remote_addr)
        return jsonify({"error": "Invalid signature"}), 400

    event_type = event.get("type", "")
    event_obj = (event.get("data") or {}).get("object", {})

    logger.info("Terminal webhook: %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            result = provision_terminal_subscriber(event_obj, db, models)
            if result["success"] and result.get("api_key") and result.get("email"):
                # Send welcome email only once (check flag to prevent double-send)
                try:
                    sub = models.ApiSubscriber.query.filter_by(
                        api_key=result["api_key"]
                    ).first()
                    if sub and not sub.welcome_email_sent:
                        sub.welcome_email_sent = True
                        db.session.commit()
                        email = result["email"]
                        key = result["api_key"]
                        t = threading.Thread(
                            target=_send_welcome_email, args=(email, key), daemon=True
                        )
                        t.start()
                except Exception as e:
                    logger.error("Error sending welcome email: %s", e)
                    db.session.rollback()

        elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
            if event_type == "customer.subscription.deleted":
                cancel_terminal_subscriber(event_obj, db, models)
            elif event_type == "customer.subscription.updated":
                status = event_obj.get("status")
                sub_id = event_obj.get("id")
                if status and sub_id:
                    try:
                        sub = models.ApiSubscriber.query.filter_by(
                            stripe_subscription_id=sub_id
                        ).first()
                        if sub:
                            sub.subscription_status = status
                            if status == "active":
                                sub.is_active = True
                                sub.past_due_since = None
                            elif status == "past_due":
                                if not sub.past_due_since:
                                    sub.past_due_since = datetime.utcnow()
                            elif status in ("canceled", "unpaid"):
                                sub.is_active = False
                            # Sync renewal date, price, and rate limit on every plan event
                            period_end_ts = event_obj.get("current_period_end")
                            if period_end_ts:
                                sub.current_period_end = datetime.utcfromtimestamp(period_end_ts)
                            price_id = (event_obj.get("items") or {}).get("data", [{}])[0].get("price", {}).get("id")
                            if price_id:
                                sub.stripe_price_id = price_id
                            # Keep rate_limit_per_hour in sync with the subscriber's tier
                            tier_limit = TIER_LIMITS.get(sub.tier, 1000)
                            if tier_limit != -1:
                                sub.rate_limit_per_hour = tier_limit
                            db.session.commit()
                    except Exception as e:
                        logger.error("Error updating subscription status: %s", e)
                        db.session.rollback()

        elif event_type == "invoice.payment_failed":
            customer_id = event_obj.get("customer")
            if customer_id:
                try:
                    sub = models.ApiSubscriber.query.filter_by(
                        stripe_customer_id=customer_id
                    ).first()
                    if sub:
                        sub.subscription_status = "past_due"
                        db.session.commit()
                except Exception as e:
                    logger.error("Error marking past_due: %s", e)
                    db.session.rollback()

    except Exception as e:
        logger.error("Webhook handler error for %s: %s", event_type, e)

    return jsonify({"received": True}), 200


# ─── Dashboard ────────────────────────────────────────────────


@premium_api.route("/api/dashboard/auth", methods=["POST"])
def dashboard_auth():
    """Exchange a raw API key for a signed session cookie.

    The key is stored in Flask's HMAC-signed, HttpOnly session cookie so it
    never appears in URLs, server logs, or browser history.
    """
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return jsonify({"error": "api_key required"}), 400
    try:
        sub = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
    except Exception as e:
        logger.error("dashboard_auth DB error: %s", e)
        return jsonify({"error": "Server error"}), 500
    if not sub or api_key == DEMO_KEY:
        return jsonify({"error": "Invalid API key"}), 401
    session["dashboard_api_key"] = api_key
    session.permanent = True
    return jsonify({"ok": True, "redirect": "/api/dashboard"}), 200


@premium_api.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    """Subscriber self-service dashboard. Auth via X-API-Key header or signed session cookie.
    The ?key= query parameter is NOT supported — use POST /api/dashboard/auth to set the
    session cookie, which keeps the key out of URLs, logs, and browser history.
    """
    api_key = (
        request.headers.get("X-API-Key", "")
        or session.get("dashboard_api_key", "")
        or ""
    ).strip()

    subscriber = None
    if api_key:
        try:
            subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
        except Exception as e:
            logger.error("Dashboard DB error: %s", e)

    if not subscriber or api_key == DEMO_KEY:
        subscriber = None  # Show unauthenticated state

    sparkline = []
    requests_today = 0
    if subscriber:
        sparkline = get_hourly_usage_sparkline(subscriber.api_key, db, models)
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            requests_today = db.session.query(db.func.count(models.ApiRequestLog.id)).filter(
                models.ApiRequestLog.api_key == subscriber.api_key,
                models.ApiRequestLog.created_at >= today_start,
            ).scalar() or 0
        except Exception as e:
            logger.warning("requests_today query failed: %s", e)

    return render_template(
        "api_dashboard.html",
        subscriber=subscriber,
        sparkline_json=json.dumps(sparkline),
        api_key=api_key if subscriber else "",
        requests_today=requests_today,
    )


@premium_api.route("/api/dashboard/rotate-key", methods=["POST"])
def rotate_api_key():
    """Generate a new API key, deactivate the old one (1hr grace period)."""
    api_key = request.headers.get("X-API-Key", "").strip()
    if not api_key:
        return jsonify({"error": "X-API-Key header required"}), 401

    try:
        subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
        if not subscriber or not subscriber.is_key_valid():
            return jsonify({"error": "Invalid or expired API key"}), 401

        if subscriber.tier == "demo":
            return jsonify({"error": "Cannot rotate demo key"}), 403

        new_key = generate_api_key(subscriber.tier)
        # Move current key to previous with 1-hour grace period
        subscriber.previous_api_key = subscriber.api_key
        subscriber.previous_key_expires_at = datetime.utcnow() + timedelta(hours=1)
        subscriber.api_key = new_key
        db.session.commit()

        logger.info("API key rotated for %s", subscriber.email)
        return jsonify({
            "success": True,
            "new_api_key": new_key,
            "message": "Old key valid for 1 hour grace period. Update your applications.",
        }), 200
    except Exception as e:
        logger.error("Key rotation error: %s", e)
        db.session.rollback()
        return jsonify({"error": "Key rotation failed. Try again."}), 500


@premium_api.route("/api/dashboard/billing-portal", methods=["POST"])
def billing_portal():
    """Create Stripe Customer Portal session."""
    api_key = request.headers.get("X-API-Key", "").strip()
    if not api_key:
        return jsonify({"error": "X-API-Key header required"}), 401

    try:
        subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
        if not subscriber:
            return jsonify({"error": "Invalid API key"}), 401
    except Exception as e:
        return jsonify({"error": "Service error"}), 503

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key or not subscriber.stripe_customer_id:
        return jsonify({
            "error": "Billing portal not available. Email: support@protocolpulse.io",
            "code": "NOT_CONFIGURED"
        }), 503

    try:
        import stripe
        stripe.api_key = stripe_key
        portal = stripe.billing_portal.Session.create(
            customer=subscriber.stripe_customer_id,
            return_url=request.url_root.rstrip("/") + "/api/dashboard",
        )
        return jsonify({"portal_url": portal.url}), 200
    except Exception as e:
        logger.error("Billing portal error: %s", e)
        return jsonify({"error": "Could not open billing portal. Try again."}), 500


@premium_api.route("/api/dashboard/webhook", methods=["POST"])
def configure_webhook():
    """Configure subscriber webhook URL."""
    api_key = request.headers.get("X-API-Key", "").strip()
    if not api_key:
        return jsonify({"error": "X-API-Key header required"}), 401

    data = request.get_json(silent=True) or {}
    webhook_url = (data.get("webhook_url") or "").strip()

    try:
        subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
        if not subscriber or not subscriber.is_key_valid():
            return jsonify({"error": "Invalid or expired API key"}), 401

        if not subscriber.has_entitlement("webhook"):
            return jsonify({"error": "Webhook delivery requires Commander tier", "upgrade_url": "/premium"}), 403

        if webhook_url and not webhook_url.startswith("https://"):
            return jsonify({"error": "Webhook URL must use HTTPS"}), 400

        subscriber.webhook_url = webhook_url or None
        if webhook_url and not subscriber.webhook_secret:
            subscriber.webhook_secret = generate_webhook_secret()
        db.session.commit()

        return jsonify({
            "success": True,
            "webhook_url": subscriber.webhook_url,
            "webhook_secret": subscriber.webhook_secret,
            "message": "Webhook configured. Sign each payload with HMAC-SHA256.",
        }), 200
    except Exception as e:
        logger.error("Webhook config error: %s", e)
        db.session.rollback()
        return jsonify({"error": "Failed to configure webhook"}), 500


# ─── API Playground ───────────────────────────────────────────


@premium_api.route("/api/playground", methods=["GET"])
def api_playground():
    """Interactive API playground with demo key."""
    demo_key = DEMO_KEY
    return render_template("api_playground.html", demo_key=demo_key)


# ─── Webhook Delivery (background) ───────────────────────────


def _deliver_webhook(subscriber: models.ApiSubscriber, payload: dict):
    """Deliver a webhook payload to a subscriber. Retries 3x with exponential backoff."""
    if not subscriber.webhook_url or not subscriber.webhook_secret:
        return

    body = json.dumps(payload)
    sig = hmac.new(
        subscriber.webhook_secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    for attempt in range(3):
        try:
            resp = http_requests.post(
                subscriber.webhook_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PP-Signature": f"sha256={sig}",
                    "X-PP-Event": payload.get("event", "unknown"),
                },
                timeout=10,
            )
            if resp.status_code < 300:
                logger.info("Webhook delivered to %s (attempt %d)", subscriber.webhook_url, attempt + 1)
                return
            logger.warning("Webhook %s returned %d (attempt %d)", subscriber.webhook_url, resp.status_code, attempt + 1)
        except Exception as e:
            logger.warning("Webhook delivery error (attempt %d): %s", attempt + 1, e)
        time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s


def deliver_breaking_article_webhooks(article_id: int, title: str, summary: str, url: str, published_at: str):
    """
    Deliver breaking article webhook to all subscribers with webhook_url set.
    Called from article publish routes.
    """
    payload = {
        "event": "breaking_article",
        "data": {
            "id": article_id,
            "title": title,
            "summary": summary[:300] if summary else "",
            "url": url,
            "published_at": published_at,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    def background():
        try:
            from app import app
            with app.app_context():
                subscribers = models.ApiSubscriber.query.filter(
                    models.ApiSubscriber.webhook_url.isnot(None),
                    models.ApiSubscriber.is_active.is_(True),
                ).all()
                for sub in subscribers:
                    if sub.has_entitlement("webhook"):
                        _deliver_webhook(sub, payload)
        except Exception as e:
            logger.error("Webhook delivery background error: %s", e)

    t = threading.Thread(target=background, daemon=True)
    t.start()
