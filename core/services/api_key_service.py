"""
api_key_service.py — Terminal API authentication middleware, rate limiting, and usage tracking.

Features:
- X-API-Key header authentication
- Sliding window rate limiting (true hourly window)
- Burst protection (max 50 req/minute)
- Usage tracking per request
- Entitlements checking
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import request, jsonify

logger = logging.getLogger("ApiKeyService")

# ── Tier defaults ─────────────────────────────────────────────

TIER_LIMITS = {
    "demo": 20,
    "commander": 1000,
    "enterprise": -1,  # unlimited
}

TIER_BURST_LIMITS = {
    "demo": 5,       # max req/minute
    "commander": 50,
    "enterprise": 200,
}

TIER_ENTITLEMENTS = {
    "demo": {
        "stream": False,
        "webhook": False,
        "signal": True,
        "breaking": True,
        "topics": True,
        "entities": False,
        "sentiment": True,
    },
    "commander": {
        "stream": True,
        "webhook": True,
        "signal": True,
        "breaking": True,
        "topics": True,
        "entities": True,
        "sentiment": True,
    },
    "enterprise": {
        "stream": True,
        "webhook": True,
        "signal": True,
        "breaking": True,
        "topics": True,
        "entities": True,
        "sentiment": True,
    },
}

# Endpoint → entitlement required
ENDPOINT_ENTITLEMENTS = {
    "/api/v2/terminal/stream": "stream",
    "/api/v2/terminal/entities": "entities",
    "/api/v2/terminal/signal": "signal",
}


def generate_api_key(tier: str = "commander") -> str:
    """Generate a prefixed UUID4 API key. Format: pp_cmd_<32hex>"""
    prefix_map = {"commander": "pp_cmd_", "enterprise": "pp_ent_", "demo": "pp_demo_"}
    prefix = prefix_map.get(tier, "pp_cmd_")
    return prefix + str(uuid.uuid4()).replace("-", "")


def generate_webhook_secret() -> str:
    """Generate a random HMAC secret for webhook signing."""
    return "whs_" + str(uuid.uuid4()).replace("-", "")


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def check_rate_limit(subscriber, db, models) -> dict:
    """
    Sliding window rate limit check.
    Returns: {"allowed": bool, "remaining": int, "limit": int, "retry_after": int|None}
    """
    from models import ApiRequestLog

    tier = subscriber.tier
    limit = TIER_LIMITS.get(tier, 20)

    if limit == -1:  # unlimited
        return {"allowed": True, "remaining": 999999, "limit": -1, "retry_after": None}

    # Sliding window: count requests in last 60 minutes
    window_start = datetime.utcnow() - timedelta(hours=1)
    count_hour = db.session.query(db.func.count(ApiRequestLog.id)).filter(
        ApiRequestLog.api_key == subscriber.api_key,
        ApiRequestLog.created_at >= window_start
    ).scalar() or 0

    if count_hour >= limit:
        # Find oldest request in window to compute Retry-After
        oldest = db.session.query(ApiRequestLog.created_at).filter(
            ApiRequestLog.api_key == subscriber.api_key,
            ApiRequestLog.created_at >= window_start
        ).order_by(ApiRequestLog.created_at.asc()).first()
        retry_after = 3600
        if oldest:
            elapsed = (datetime.utcnow() - oldest[0]).total_seconds()
            retry_after = max(1, int(3600 - elapsed))
        return {"allowed": False, "remaining": 0, "limit": limit, "retry_after": retry_after}

    # Burst check: count requests in last 60 seconds
    burst_limit = TIER_BURST_LIMITS.get(tier, 5)
    burst_window = datetime.utcnow() - timedelta(seconds=60)
    count_minute = db.session.query(db.func.count(ApiRequestLog.id)).filter(
        ApiRequestLog.api_key == subscriber.api_key,
        ApiRequestLog.created_at >= burst_window
    ).scalar() or 0

    if count_minute >= burst_limit:
        return {"allowed": False, "remaining": limit - count_hour, "limit": limit, "retry_after": 60}

    return {
        "allowed": True,
        "remaining": limit - count_hour - 1,
        "limit": limit,
        "retry_after": None,
    }


def log_request(subscriber, endpoint: str, status_code: int, response_time_ms: int, db, models):
    """Log a request to api_request_log and update subscriber stats."""
    from models import ApiRequestLog

    try:
        ip = request.remote_addr or "unknown"
        log_entry = ApiRequestLog(
            api_key=subscriber.api_key,
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            status_code=status_code,
            ip_hash=_hash_ip(ip),
        )
        db.session.add(log_entry)

        # Update subscriber totals
        subscriber.requests_total = (subscriber.requests_total or 0) + 1
        subscriber.last_used_at = datetime.utcnow()

        db.session.commit()
    except Exception as e:
        logger.warning("Failed to log API request: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass


def require_api_key(f):
    """
    Decorator that validates X-API-Key header on Terminal API endpoints.
    Injects `_subscriber` kwarg into the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from app import db
        import models

        start_time = time.monotonic()
        api_key = request.headers.get("X-API-Key", "").strip()

        if not api_key:
            return jsonify({
                "error": "Missing X-API-Key header",
                "code": "NO_API_KEY",
                "docs": "/api/v2/terminal/docs"
            }), 401

        try:
            subscriber = models.ApiSubscriber.query.filter_by(api_key=api_key).first()
        except Exception as e:
            logger.error("DB error looking up API key: %s", e)
            return jsonify({"error": "Service temporarily unavailable", "code": "DB_ERROR"}), 503

        if not subscriber:
            # Also check if this is a rotated-away key still in grace period
            try:
                old_sub = models.ApiSubscriber.query.filter_by(
                    previous_api_key=api_key
                ).first()
                if old_sub and old_sub.previous_key_expires_at and \
                   datetime.utcnow() < old_sub.previous_key_expires_at and \
                   old_sub.is_active:
                    subscriber = old_sub
                else:
                    return jsonify({
                        "error": "Invalid or expired API key",
                        "code": "INVALID_KEY",
                        "docs": "/api/v2/terminal/docs"
                    }), 401
            except Exception:
                return jsonify({
                    "error": "Invalid or expired API key",
                    "code": "INVALID_KEY",
                    "docs": "/api/v2/terminal/docs"
                }), 401
        elif not subscriber.is_key_valid():
            return jsonify({
                "error": "Invalid or expired API key",
                "code": "INVALID_KEY",
                "docs": "/api/v2/terminal/docs"
            }), 401

        # Rate limit check
        rate_result = check_rate_limit(subscriber, db, models)
        if not rate_result["allowed"]:
            retry_after = rate_result.get("retry_after", 3600)
            resp = jsonify({
                "error": "Rate limit exceeded",
                "code": "RATE_LIMITED",
                "requests_limit": rate_result["limit"],
                "retry_after_seconds": retry_after,
            })
            resp.headers["Retry-After"] = str(retry_after)
            resp.headers["X-RateLimit-Limit"] = str(rate_result["limit"])
            resp.headers["X-RateLimit-Remaining"] = "0"
            return resp, 429

        # Check endpoint entitlement
        endpoint_path = request.path
        required_entitlement = ENDPOINT_ENTITLEMENTS.get(endpoint_path)
        if required_entitlement:
            ents = subscriber.get_entitlements()
            if not ents.get(required_entitlement, False):
                return jsonify({
                    "error": f"Your plan does not include '{required_entitlement}' access",
                    "code": "INSUFFICIENT_TIER",
                    "upgrade_url": "/premium"
                }), 403

        kwargs["_subscriber"] = subscriber
        result = f(*args, **kwargs)

        # Log after response
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        status_code = result[1] if isinstance(result, tuple) else 200
        log_request(subscriber, endpoint_path, status_code, elapsed_ms, db, models)

        # Add rate limit headers to response
        if isinstance(result, tuple):
            resp, code = result[0], result[1]
        else:
            resp, code = result, 200

        resp.headers["X-RateLimit-Limit"] = str(rate_result["limit"])
        resp.headers["X-RateLimit-Remaining"] = str(rate_result["remaining"])
        if subscriber.tier != "enterprise":
            resp.headers["X-Tier"] = subscriber.tier

        return resp, code

    return decorated


def provision_demo_key(db, models):
    """
    Ensure a demo subscriber exists in the DB.
    Called at app startup. Returns the demo api_key.
    """
    DEMO_EMAIL = "demo@protocolpulse.io"
    DEMO_KEY = "pp_demo_00000000000000000000000000000001"

    try:
        existing = models.ApiSubscriber.query.filter_by(email=DEMO_EMAIL).first()
        if existing:
            return existing.api_key

        entitlements = json.dumps(TIER_ENTITLEMENTS.get("demo", {}))
        demo = models.ApiSubscriber(
            email=DEMO_EMAIL,
            api_key=DEMO_KEY,
            tier="demo",
            rate_limit_per_hour=20,
            entitlements=entitlements,
            key_scopes=json.dumps(["read"]),
            is_active=True,
            subscription_status="active",
        )
        db.session.add(demo)
        db.session.commit()
        logger.info("Demo API key provisioned: %s", DEMO_KEY)
        return DEMO_KEY
    except Exception as e:
        logger.warning("Could not provision demo key: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return DEMO_KEY


def get_hourly_usage_sparkline(api_key: str, db, models) -> list:
    """
    Returns 24 hourly buckets (last 24h) of request counts for the sparkline.
    Single GROUP BY query — no N+1.
    """
    from models import ApiRequestLog
    from sqlalchemy import func, text

    now = datetime.utcnow()
    window_start = now - timedelta(hours=24)

    # Initialize 24 zero-count slots
    buckets = {}
    for i in range(23, -1, -1):
        slot_time = now - timedelta(hours=i)
        key = slot_time.strftime("%H:00")
        buckets[key] = 0

    try:
        # Single query: count requests per hour in last 24h
        results = db.session.query(
            func.strftime("%H", ApiRequestLog.created_at).label("hour"),
            func.count(ApiRequestLog.id).label("cnt"),
        ).filter(
            ApiRequestLog.api_key == api_key,
            ApiRequestLog.created_at >= window_start,
        ).group_by(
            func.strftime("%H", ApiRequestLog.created_at)
        ).all()

        for row in results:
            slot_key = f"{row.hour}:00"
            if slot_key in buckets:
                buckets[slot_key] = row.cnt

    except Exception as e:
        logger.warning("sparkline query failed: %s", e)

    return [{"hour": k, "count": v} for k, v in buckets.items()]
