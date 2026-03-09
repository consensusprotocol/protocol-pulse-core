"""
routes_commander.py — Pulse Terminal Commander API tier
Blueprint registered in app.py with url_prefix=/api/v1
Import pattern matches routes.py: top-level imports after app is initialized.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from functools import wraps

import jwt as _jwt
from flask import Blueprint, jsonify, request, session

# Top-level imports — safe because app.py imports us AFTER db.init_app()
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

commander_bp = Blueprint("commander", __name__, url_prefix="/api/v1")

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SESSION_SECRET", "pulse-terminal-dev-secret")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24


def _jwt_required(f):
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


def _rl(user_id, tier):
    result = check_and_increment_rate_limit(user_id, tier)
    meta = {
        "tier": tier,
        "rate_limit_remaining": result["remaining"],
        "rate_limit_daily": result["limit"],
        "freshness": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return result["allowed"], meta


# ── /api/v1/auth/token ────────────────────────────────────────────────────────

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


# ── /api/v1/signals/live ─────────────────────────────────────────────────────

@commander_bp.route("/signals/live", methods=["GET"])
@_jwt_required
def v1_signals_live(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    limit = min(int(request.args.get("limit", 10)), 50)
    result = get_live_signals(limit=limit)
    resp = {"data": result["data"], "meta": {**meta, "stale": result.get("stale", False)}}
    if result.get("stale"):
        resp["warning"] = "Data may be stale"
    return jsonify(resp)


# ── /api/v1/spaces/live ───────────────────────────────────────────────────────

@commander_bp.route("/spaces/live", methods=["GET"])
@_jwt_required
def v1_spaces_live(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    result = get_spaces_live()
    return jsonify({"data": result["data"], "meta": {**meta, "stale": result.get("stale", False)}})


# ── /api/v1/tradfi/signals ───────────────────────────────────────────────────

@commander_bp.route("/tradfi/signals", methods=["GET"])
@_jwt_required
def v1_tradfi_signals(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"))
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


# ── /api/v1/sentiment/composite ──────────────────────────────────────────────

@commander_bp.route("/sentiment/composite", methods=["GET"])
@_jwt_required
def v1_sentiment_composite(**kwargs):
    allowed, meta = _rl(kwargs.get("_jwt_user_id"), kwargs.get("_jwt_tier"))
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429
    result = get_sentiment_composite()
    return jsonify({"data": result["data"], "scan_time": result["scan_time"],
                    "meta": {**meta, "stale": result.get("stale", False)}})


# ── /api/v1/alerts/webhook ───────────────────────────────────────────────────

@commander_bp.route("/alerts/webhook", methods=["GET", "POST"])
@_jwt_required
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


# ── /api/v1/stripe/webhook ───────────────────────────────────────────────────

@commander_bp.route("/stripe/webhook", methods=["POST"])
def v1_stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret:
        event = validate_webhook_signature(payload, sig_header, webhook_secret)
        if event is None:
            return jsonify({"error": "Invalid signature"}), 400
    else:
        try:
            event = json.loads(payload)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400
    event_type = event.get("type", "")
    event_data = (event.get("data") or {}).get("object") or {}
    if event_type == "checkout.session.completed":
        result = handle_checkout_completed(event_data, db, models)
        logging.info("Commander checkout: %s", result)
        return jsonify({"received": True, "result": result})
    elif event_type in ("customer.subscription.deleted",
                        "customer.subscription.paused",
                        "customer.subscription.updated"):
        result = handle_subscription_deleted(event_data, db, models)
        logging.info("Commander sub event %s: %s", event_type, result)
        return jsonify({"received": True, "result": result})
    return jsonify({"received": True, "event_type": event_type, "handled": False})
