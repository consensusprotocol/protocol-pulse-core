"""
routes_commander.py — Pulse Terminal Commander API + Stripe checkout + pages.
Blueprint registered in app.py with url_prefix=/api/v1 (commander_bp).
Commander pages blueprint registered with no prefix (commander_pages_bp).
"""

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

import jwt as _jwt
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for

from app import app as _flask_app, db
import models

from core.services.pulse_terminal_service import (
    get_live_signals,
    get_spaces_live,
    get_tradfi_signals,
    get_sentiment_composite,
    get_breaking_alerts,
    check_and_increment_rate_limit,
)
from core.services.stripe_service import (
    validate_webhook_signature,
    handle_checkout_completed,
    handle_subscription_deleted,
)

logger = logging.getLogger(__name__)

commander_bp = Blueprint("commander", __name__, url_prefix="/api/v1")
commander_pages_bp = Blueprint("commander_pages", __name__)

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SESSION_SECRET", "pulse-terminal-dev-secret")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24
_COMMANDER_DAILY_LIMIT = 1000
_RESEND_TIMEOUT = 10  # seconds

# Idempotency: track processed Stripe event IDs (in-memory, TTL-based)
_processed_events = {}  # event_id -> timestamp
_IDEMPOTENCY_TTL = 86400  # 24 hours

# Short-lived cache for displaying plaintext API key on success page (5 min TTL)
_pending_keys = {}  # stripe_session_id -> (api_key, expiry_timestamp)


def _is_event_processed(event_id):
    """Check if a Stripe event ID has already been processed."""
    if event_id in _processed_events:
        if (datetime.utcnow() - _processed_events[event_id]).total_seconds() < _IDEMPOTENCY_TTL:
            return True
        del _processed_events[event_id]
    return False


def _mark_event_processed(event_id):
    """Mark a Stripe event ID as processed. Prune old entries."""
    _processed_events[event_id] = datetime.utcnow()
    # Prune entries older than TTL (every 100 events to avoid overhead)
    if len(_processed_events) > 100:
        cutoff = datetime.utcnow() - timedelta(seconds=_IDEMPOTENCY_TTL)
        stale = [k for k, v in _processed_events.items() if v < cutoff]
        for k in stale:
            del _processed_events[k]


# ══════════════════════════════════════════════════════════════════════════════
# AUTH DECORATORS
# ══════════════════════════════════════════════════════════════════════════════

def _hash_key(raw_key):
    return hashlib.sha256(raw_key.encode()).hexdigest()


def require_commander_key(f):
    """Authenticate via X-Commander-Key header against CommanderSubscriber."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-Commander-Key", "").strip()
        if not api_key:
            return jsonify({
                "error": "Missing X-Commander-Key header",
                "code": "NO_API_KEY",
                "docs": "https://protocolpulse.io/commander",
            }), 401

        key_hash = _hash_key(api_key)
        try:
            sub = models.CommanderSubscriber.query.filter_by(
                api_key_hash=key_hash, active=True
            ).first()
        except Exception as e:
            logger.error("DB error looking up Commander key: %s", e)
            return jsonify({"error": "Service temporarily unavailable"}), 503

        if not sub:
            return jsonify({
                "error": "Invalid or inactive API key",
                "code": "INVALID_KEY",
                "docs": "https://protocolpulse.io/commander",
            }), 401

        # Rate limit: 1000/day
        sub.reset_if_needed()
        if sub.calls_today >= _COMMANDER_DAILY_LIMIT:
            return jsonify({
                "error": "Daily rate limit exceeded (1000 req/day)",
                "code": "RATE_LIMITED",
                "calls_today": sub.calls_today,
            }), 429

        sub.increment_calls()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        kwargs["_commander_sub"] = sub
        return f(*args, **kwargs)
    return decorated


def _jwt_required(f):
    """Authenticate via Bearer JWT token (legacy, still supported)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header", "code": "NO_AUTH"}), 401
        token = auth_header[7:]
        try:
            payload = _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        except _jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired", "code": "TOKEN_EXPIRED"}), 401
        except _jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token", "code": "TOKEN_INVALID"}), 401
        tier = payload.get("tier", "free")
        if tier not in ("commander", "sovereign"):
            return jsonify({"error": "Commander tier required", "code": "TIER_REQUIRED"}), 403
        kwargs["_jwt_user_id"] = payload.get("user_id")
        kwargs["_jwt_tier"] = tier
        return f(*args, **kwargs)
    return decorated


def _commander_or_jwt(f):
    """Accept EITHER X-Commander-Key OR Bearer JWT — unified auth for all /api/v1 endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        commander_key = request.headers.get("X-Commander-Key", "").strip()
        auth_header = request.headers.get("Authorization", "")

        # Try Commander key first
        if commander_key:
            key_hash = _hash_key(commander_key)
            try:
                sub = models.CommanderSubscriber.query.filter_by(
                    api_key_hash=key_hash, active=True
                ).first()
            except Exception as e:
                logger.error("DB error looking up Commander key: %s", e)
                return jsonify({"error": "Service temporarily unavailable"}), 503

            if not sub:
                return jsonify({
                    "error": "Invalid or inactive API key",
                    "code": "INVALID_KEY",
                }), 401

            sub.reset_if_needed()
            if sub.calls_today >= _COMMANDER_DAILY_LIMIT:
                return jsonify({
                    "error": "Daily rate limit exceeded (1000 req/day)",
                    "code": "RATE_LIMITED",
                }), 429

            sub.increment_calls()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

            kwargs["_commander_sub"] = sub
            kwargs["_jwt_user_id"] = f"cmd_{sub.id}"
            kwargs["_jwt_tier"] = "commander"
            return f(*args, **kwargs)

        # Fall back to JWT
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
            except _jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired", "code": "TOKEN_EXPIRED"}), 401
            except _jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token", "code": "TOKEN_INVALID"}), 401
            tier = payload.get("tier", "free")
            if tier not in ("commander", "sovereign"):
                return jsonify({"error": "Commander tier required", "code": "TIER_REQUIRED"}), 403
            kwargs["_jwt_user_id"] = payload.get("user_id")
            kwargs["_jwt_tier"] = tier
            return f(*args, **kwargs)

        return jsonify({
            "error": "Missing authentication. Provide X-Commander-Key header or Bearer JWT.",
            "code": "NO_AUTH",
            "docs": "https://protocolpulse.io/commander",
        }), 401
    return decorated


def _rl(user_id, tier, commander_sub=None):
    """Rate limit check. Commander key users skip the service-level limiter
    since they're already rate-limited in the auth decorator."""
    if commander_sub:
        # Already rate-limited in _commander_or_jwt — just build meta
        meta = {
            "tier": "commander",
            "rate_limit_remaining": max(0, _COMMANDER_DAILY_LIMIT - (commander_sub.calls_today or 0)),
            "rate_limit_daily": _COMMANDER_DAILY_LIMIT,
            "freshness": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return True, meta
    result = check_and_increment_rate_limit(user_id, tier)
    meta = {
        "tier": tier,
        "rate_limit_remaining": result["remaining"],
        "rate_limit_daily": result["limit"],
        "freshness": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return result["allowed"], meta


# ══════════════════════════════════════════════════════════════════════════════
# STRIPE CHECKOUT + WEBHOOK
# ══════════════════════════════════════════════════════════════════════════════

@commander_bp.route("/checkout/create-session", methods=["POST"])
def v1_checkout_create_session():
    """Create a Stripe Checkout Session for Commander subscription."""
    try:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not stripe.api_key:
            return jsonify({"error": "Stripe not configured"}), 503

        price_id = os.environ.get("STRIPE_COMMANDER_PRICE_ID", "")
        if not price_id:
            return jsonify({"error": "Commander price not configured"}), 503

        data = request.get_json(silent=True) or {}
        customer_email = (data.get("email") or "").strip().lower() or None

        checkout_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": "https://protocolpulse.io/commander/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://protocolpulse.io/commander",
            "metadata": {"subscription_type": "commander_api", "tier": "commander"},
        }
        if customer_email:
            checkout_params["customer_email"] = customer_email

        checkout_session = stripe.checkout.Session.create(**checkout_params)
        return jsonify({"url": checkout_session.url, "session_id": checkout_session.id})

    except Exception as e:
        logger.error("Stripe checkout creation failed: %s", e)
        return jsonify({"error": "Failed to create checkout session"}), 500


@commander_bp.route("/stripe/webhook", methods=["POST"])
def v1_stripe_webhook():
    """Handle Stripe webhook events for Commander subscriptions."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured — rejecting webhook")
        return jsonify({"error": "Webhook verification not configured"}), 503

    event = validate_webhook_signature(payload, sig_header, webhook_secret)
    if event is None:
        return jsonify({"error": "Invalid signature"}), 400

    # Idempotency: skip already-processed events
    event_id = event.get("id", "")
    if event_id and _is_event_processed(event_id):
        return jsonify({"received": True, "duplicate": True})
    if event_id:
        _mark_event_processed(event_id)

    event_type = event.get("type", "")
    event_data = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        result = _handle_commander_checkout(event_data)
        # Also update User model if applicable
        user_result = handle_checkout_completed(event_data, db, models)
        logger.info("Commander checkout: commander=%s user=%s", result, user_result)
        return jsonify({"received": True, "result": result})

    elif event_type == "customer.subscription.deleted":
        result = _handle_commander_cancellation(event_data)
        user_result = handle_subscription_deleted(event_data, db, models)
        logger.info("Commander cancellation: commander=%s user=%s", result, user_result)
        return jsonify({"received": True, "result": result})

    elif event_type == "invoice.payment_failed":
        result = _handle_payment_failed(event_data)
        logger.info("Commander payment failed: %s", result)
        return jsonify({"received": True, "result": result})

    elif event_type in ("customer.subscription.paused",
                        "customer.subscription.updated"):
        result = handle_subscription_deleted(event_data, db, models)
        logger.info("Commander sub event %s: %s", event_type, result)
        return jsonify({"received": True, "result": result})

    return jsonify({"received": True, "event_type": event_type, "handled": False})


def _handle_commander_checkout(session_obj):
    """Create CommanderSubscriber + generate API key on checkout.session.completed."""
    customer_email = (session_obj.get("customer_details") or {}).get("email")
    if not customer_email:
        customer_email = session_obj.get("customer_email")
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")
    session_id = session_obj.get("id")

    if not customer_email:
        return {"success": False, "error": "no email in checkout session"}

    try:
        existing = models.CommanderSubscriber.query.filter_by(email=customer_email).first()
        if existing:
            # Reactivation: generate a fresh key
            new_key = "pp_cmd_" + secrets.token_hex(32)
            existing.active = True
            existing.stripe_customer_id = customer_id
            existing.stripe_subscription_id = subscription_id
            existing.stripe_session_id = session_id
            existing.api_key_hash = _hash_key(new_key)
            existing.api_key_prefix = new_key[:12]
            db.session.commit()
            if session_id:
                _pending_keys[session_id] = (new_key, datetime.utcnow() + timedelta(minutes=5))
            _send_welcome_email(customer_email, new_key)
            return {"success": True, "email": customer_email, "reactivated": True}

        api_key = "pp_cmd_" + secrets.token_hex(32)
        sub = models.CommanderSubscriber(
            email=customer_email,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            stripe_session_id=session_id,
            api_key_hash=_hash_key(api_key),
            api_key_prefix=api_key[:12],
            active=True,
        )
        db.session.add(sub)
        db.session.commit()
        # Cache plaintext key briefly for success page display
        if session_id:
            _pending_keys[session_id] = (api_key, datetime.utcnow() + timedelta(minutes=5))
        _send_welcome_email(customer_email, api_key)
        logger.info("Commander subscriber created: %s", customer_email)
        return {"success": True, "email": customer_email, "reactivated": False}

    except Exception as e:
        logger.error("Error creating Commander subscriber: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def _handle_commander_cancellation(subscription_obj):
    """Deactivate CommanderSubscriber on subscription deletion."""
    subscription_id = subscription_obj.get("id")
    customer_id = subscription_obj.get("customer")

    try:
        sub = None
        if subscription_id:
            sub = models.CommanderSubscriber.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
        if not sub and customer_id:
            sub = models.CommanderSubscriber.query.filter_by(
                stripe_customer_id=customer_id
            ).first()
        if not sub:
            return {"success": False, "error": "subscriber not found"}

        sub.active = False
        db.session.commit()
        logger.info("Commander subscriber deactivated: %s", sub.email)
        return {"success": True, "email": sub.email}
    except Exception as e:
        logger.error("Error deactivating Commander subscriber: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def _handle_payment_failed(invoice_obj):
    """Deactivate subscriber and send alert on invoice.payment_failed."""
    subscription_id = invoice_obj.get("subscription")
    customer_id = invoice_obj.get("customer")
    customer_email = (invoice_obj.get("customer_email") or "")

    try:
        sub = None
        if subscription_id:
            sub = models.CommanderSubscriber.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
        if not sub and customer_id:
            sub = models.CommanderSubscriber.query.filter_by(
                stripe_customer_id=customer_id
            ).first()
        if not sub:
            return {"success": False, "error": "subscriber not found"}

        sub.active = False
        db.session.commit()

        email = customer_email or sub.email
        _send_payment_failed_email(email)
        logger.info("Commander payment failed, deactivated: %s", email)
        return {"success": True, "email": email}
    except Exception as e:
        logger.error("Error handling payment failure: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def _send_welcome_email(email, api_key):
    """Send welcome email with API key via Resend."""
    try:
        import requests as _requests
        resend_key = os.environ.get("RESEND_API_KEY", "")
        if not resend_key:
            logger.warning("RESEND_API_KEY not set, skipping welcome email for %s", email)
            return
        resp = _requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            timeout=_RESEND_TIMEOUT,
            json={
                "from": "Protocol Pulse <noreply@protocolpulse.io>",
                "to": [email],
                "subject": "Your Commander API Key is Ready",
                "html": f"""<div style="font-family:monospace;background:#000;color:#fff;padding:40px;max-width:600px;">
<h1 style="color:#F7931A;">COMMANDER ACTIVATED</h1>
<p>Your Protocol Pulse Commander subscription is live.</p>
<div style="background:#111;border:1px solid #F7931A;padding:16px;border-radius:4px;margin:20px 0;">
<p style="color:#888;margin:0 0 8px;">Your API Key:</p>
<code style="color:#F7931A;font-size:14px;word-break:break-all;">{api_key}</code>
</div>
<p style="color:#888;">Quick start:</p>
<pre style="background:#111;padding:12px;border-radius:4px;overflow-x:auto;font-size:12px;">curl -s https://protocolpulse.io/api/v1/signals/live \\
  -H "X-Commander-Key: {api_key}"</pre>
<p>Rate limit: 1,000 requests/day. Resets at 00:00 UTC.</p>
<p style="color:#888;font-size:0.8rem;margin-top:24px;">
Dashboard: <a href="https://protocolpulse.io/commander/dashboard?key={api_key}" style="color:#dc2626;">protocolpulse.io/commander/dashboard</a>
</p>
</div>""",
            },
        )
        if not resp.ok:
            logger.error("Resend welcome email error (%s): %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Welcome email exception for %s: %s", email, e)


def _send_payment_failed_email(email):
    """Send payment failure alert via Resend."""
    try:
        import requests as _requests
        resend_key = os.environ.get("RESEND_API_KEY", "")
        if not resend_key:
            return
        _requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            timeout=_RESEND_TIMEOUT,
            json={
                "from": "Protocol Pulse <noreply@protocolpulse.io>",
                "to": [email],
                "subject": "Payment Failed — Commander Access Paused",
                "html": """<div style="font-family:monospace;background:#000;color:#fff;padding:40px;max-width:600px;">
<h1 style="color:#dc2626;">PAYMENT FAILED</h1>
<p>Your Commander subscription payment could not be processed. Your API access has been paused.</p>
<p>Please update your payment method to restore access:</p>
<p><a href="https://protocolpulse.io/commander" style="color:#F7931A;">Update Payment &rarr;</a></p>
</div>""",
            },
        )
    except Exception as e:
        logger.error("Payment failed email exception for %s: %s", email, e)


# ══════════════════════════════════════════════════════════════════════════════
# JWT AUTH TOKEN (legacy)
# ══════════════════════════════════════════════════════════════════════════════

@commander_bp.route("/auth/token", methods=["POST"])
def v1_auth_token():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    user = models.User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    tier = getattr(user, "subscription_tier", "free")
    if tier not in ("operator", "commander", "sovereign"):
        return jsonify({"error": "Commander or higher tier required", "upgrade_url": "/premium"}), 403
    expiry = datetime.utcnow() + timedelta(hours=_JWT_EXPIRY_HOURS)
    payload = {"user_id": user.id, "email": user.email, "tier": tier,
               "exp": expiry, "iat": datetime.utcnow()}
    token = _jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    return jsonify({"token": token, "tier": tier,
                    "expires_in": _JWT_EXPIRY_HOURS * 3600,
                    "expires_at": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "rate_limit": "1000 req/day",
                    "docs": "https://protocolpulse.io/developers"})


# ══════════════════════════════════════════════════════════════════════════════
# COMMANDER DATA ENDPOINTS (X-Commander-Key OR Bearer JWT)
# ══════════════════════════════════════════════════════════════════════════════

@commander_bp.route("/signals/live", methods=["GET"])
@_commander_or_jwt
def v1_signals_live(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"), kwargs.get("_commander_sub"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    limit = min(int(request.args.get("limit", 10)), 50)
    result = get_live_signals(limit=limit)
    resp = {"data": result["data"], "meta": {**meta, "stale": result.get("stale", False)}}
    if result.get("stale"):
        resp["warning"] = "Data may be stale"
    return jsonify(resp)


@commander_bp.route("/spaces/live", methods=["GET"])
@_commander_or_jwt
def v1_spaces_live(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"), kwargs.get("_commander_sub"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    result = get_spaces_live()
    return jsonify({"data": result["data"], "meta": {**meta, "stale": result.get("stale", False)}})


@commander_bp.route("/tradfi/signals", methods=["GET"])
@_commander_or_jwt
def v1_tradfi_signals(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"), kwargs.get("_commander_sub"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    limit = min(int(request.args.get("limit", 20)), 50)
    btc_only = request.args.get("btc_only", "false").lower() == "true"
    result = get_tradfi_signals(limit=limit)
    signals = result["data"]["signals"]
    if btc_only:
        signals = [s for s in signals if s.get("btc_relevant")]
    return jsonify({"data": {**result["data"], "signals": signals, "total_returned": len(signals)},
                    "meta": {**meta, "stale": result.get("stale", False), "btc_only": btc_only}})


@commander_bp.route("/sentiment/composite", methods=["GET"])
@_commander_or_jwt
def v1_sentiment_composite(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"), kwargs.get("_commander_sub"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    result = get_sentiment_composite()
    return jsonify({"data": result["data"], "scan_time": result["scan_time"],
                    "meta": {**meta, "stale": result.get("stale", False)}})


@commander_bp.route("/alerts/webhook", methods=["GET", "POST"])
@_commander_or_jwt
def v1_alerts_webhook(**kwargs):
    user_id = kwargs.get("_jwt_user_id")
    tier = kwargs.get("_jwt_tier")
    allowed, meta = _rl(user_id, tier)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        webhook_url = body.get("webhook_url", "")
        threshold = int(body.get("threshold_velocity", 80))
        if webhook_url and not webhook_url.startswith(("https://", "http://")):
            return jsonify({"error": "webhook_url must be http/https"}), 400
        session[f"alert_webhook_{user_id}"] = {
            "url": webhook_url, "threshold_velocity": threshold,
            "registered_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return jsonify({"registered": True, "webhook_url": webhook_url,
                        "threshold_velocity": threshold, "meta": meta})
    alerts = get_breaking_alerts()
    webhook_config = session.get(f"alert_webhook_{user_id}", {})
    return jsonify({"data": {**alerts["data"], "webhook_config": webhook_config or None}, "meta": meta})


# ══════════════════════════════════════════════════════════════════════════════
# COMMANDER PAGE ROUTES (no prefix)
# ══════════════════════════════════════════════════════════════════════════════

@commander_pages_bp.route("/commander")
def commander_landing():
    """Commander sales/activation page."""
    return render_template("commander.html")


@commander_pages_bp.route("/commander/success")
def commander_success():
    """Post-checkout success page — display API key from short-lived cache."""
    session_id = request.args.get("session_id", "")
    api_key = ""
    email = ""

    # Retrieve plaintext key from short-lived cache
    if session_id and session_id in _pending_keys:
        cached_key, expiry = _pending_keys[session_id]
        if datetime.utcnow() < expiry:
            api_key = cached_key
            del _pending_keys[session_id]  # one-time display
        else:
            del _pending_keys[session_id]

    # Look up subscriber for email display
    if session_id:
        sub = models.CommanderSubscriber.query.filter_by(
            stripe_session_id=session_id
        ).first()
        if sub:
            email = sub.email

    return render_template("commander_success.html", api_key=api_key, email=email)


@commander_pages_bp.route("/commander/dashboard")
def commander_dashboard():
    """Commander dashboard — auth via X-Commander-Key header OR ?key= param."""
    api_key = request.headers.get("X-Commander-Key", "").strip()
    if not api_key:
        api_key = request.args.get("key", "").strip()
    if not api_key:
        return render_template("commander_dashboard.html", authed=False, sub=None, error="No API key provided. Add ?key=YOUR_KEY to the URL.")

    key_hash = _hash_key(api_key)
    sub = models.CommanderSubscriber.query.filter_by(api_key_hash=key_hash, active=True).first()
    if not sub:
        return render_template("commander_dashboard.html", authed=False, sub=None, error="Invalid or inactive API key.")

    sub.reset_if_needed()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    masked_key = sub.api_key_prefix + "..." + api_key[-4:]

    return render_template(
        "commander_dashboard.html",
        authed=True,
        sub=sub,
        masked_key=masked_key,
        calls_today=sub.calls_today,
        calls_month=sub.calls_month,
        daily_limit=_COMMANDER_DAILY_LIMIT,
        error=None,
    )
