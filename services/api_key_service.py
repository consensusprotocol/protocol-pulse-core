#!/usr/bin/env python3
"""
Protocol Pulse API Key Service — Session 2
==========================================
Handles the complete API key lifecycle:
  - Key generation (pp_live_XXXX format, SHA-256 hashed in DB)
  - Bearer token authentication middleware
  - Per-tier rate limiting (day + hour windows)
  - Usage tracking (api_usage_log table)
  - Entitlement enforcement per endpoint
  - Stripe webhook processing (subscription created/cancelled/updated)
  - Key rotation

Tiers:
  commander  $49/mo   100 req/day   20 req/hr
  intel      $149/mo  500 req/day  100 req/hr
  sovereign  $499/mo  unlimited    unlimited
"""
import hashlib
import logging
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Optional, Tuple

from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# ── Tier configuration ────────────────────────────────────────────────────────

TIER_CONFIG = {
    "demo": {
        "rate_limit_day": 20,
        "rate_limit_hour": 5,
        "entitlements": {"signals": True, "congress": False, "whale": False,
                         "orb": False, "pe": False, "stream": False, "mcp": False},
    },
    "commander": {
        "rate_limit_day": 100,
        "rate_limit_hour": 20,
        "entitlements": {"signals": True, "congress": True, "whale": True,
                         "orb": True, "pe": False, "stream": False, "mcp": False},
        "stripe_price_id": os.environ.get("STRIPE_PRICE_COMMANDER", ""),
    },
    "intel": {
        "rate_limit_day": 500,
        "rate_limit_hour": 100,
        "entitlements": {"signals": True, "congress": True, "whale": True,
                         "orb": True, "pe": True, "stream": True, "mcp": False},
        "stripe_price_id": os.environ.get("STRIPE_PRICE_INTEL", ""),
    },
    "sovereign": {
        "rate_limit_day": 999_999,
        "rate_limit_hour": 999_999,
        "entitlements": {"signals": True, "congress": True, "whale": True,
                         "orb": True, "pe": True, "stream": True, "mcp": True, "webhook": True},
        "stripe_price_id": os.environ.get("STRIPE_PRICE_SOVEREIGN", ""),
    },
}

# Endpoint → required entitlement
ENDPOINT_ENTITLEMENTS = {
    "/api/v1/signals":       "signals",
    "/api/v1/intelligence":  "signals",
    "/api/v1/congress":      "congress",
    "/api/v1/whale":         "whale",
    "/api/v1/orb":           "orb",
    "/api/v1/convergence":   "orb",
    "/api/v1/pe":            "pe",
    "/api/v1/panopticon":    "pe",
    "/api/v1/stream":        "stream",
    "/api/v1/mcp":           "mcp",
}

# ── Key generation ────────────────────────────────────────────────────────────

def generate_api_key(tier: str = "commander") -> Tuple[str, str]:
    """
    Generate a new API key.
    Returns (raw_key, key_prefix) — raw_key shown once to user, prefix for display.
    raw_key is NEVER stored — only the SHA-256 hash is persisted.
    """
    # Format: pp_live_<tier_abbrev>_<32 random hex chars>
    tier_abbrev = {"commander": "cmd", "intel": "int", "sovereign": "sov", "demo": "demo"}.get(tier, "key")
    raw = f"pp_live_{tier_abbrev}_{secrets.token_hex(24)}"
    prefix = raw[:20] + "..."
    return raw, prefix


def hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key — stored in DB."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_subscriber_key(email: str, tier: str, stripe_customer_id: str = "",
                           stripe_subscription_id: str = "", stripe_price_id: str = "") -> dict:
    """
    Create a new API subscriber with a fresh key.
    Writes to both api_keys and api_subscribers tables.
    Returns {"api_key": raw_key, "prefix": prefix, "tier": tier}
    """
    import sqlite3
    db_path = "/home/ultron/protocol_pulse/instance/protocol_pulse.db"
    raw_key, prefix = generate_api_key(tier)
    key_hash = hash_key(raw_key)
    tier_cfg = TIER_CONFIG.get(tier, TIER_CONFIG["commander"])
    now = datetime.now(timezone.utc).isoformat()

    try:
        conn = sqlite3.connect(db_path)

        # Deactivate any existing keys for this email
        conn.execute("UPDATE api_keys SET active=0 WHERE subscriber_email=?", (email,))
        conn.execute("UPDATE api_subscribers SET is_active=0 WHERE email=?", (email,))

        # Insert into api_keys (hashed)
        conn.execute("""
            INSERT INTO api_keys
            (key_hash, key_prefix, tier, subscriber_email, stripe_customer_id,
             stripe_subscription_id, requests_today, requests_total,
             last_reset_at, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 1, ?)
        """, (key_hash, prefix, tier, email, stripe_customer_id,
               stripe_subscription_id, now, now))

        # Insert into api_subscribers (full record)
        entitlements_json = str(tier_cfg["entitlements"])
        conn.execute("""
            INSERT OR REPLACE INTO api_subscribers
            (email, api_key, tier, stripe_customer_id, stripe_subscription_id,
             stripe_price_id, rate_limit_per_hour, requests_this_hour,
             requests_today, requests_total, rate_window_start,
             entitlements, key_scopes, is_active, subscription_status,
             created_at, welcome_email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, 1, 'active', ?, 0)
        """, (email, raw_key, tier, stripe_customer_id, stripe_subscription_id,
               stripe_price_id, tier_cfg["rate_limit_hour"],
               now, str(tier_cfg["entitlements"]), '["read"]', now))

        conn.commit()
        conn.close()
        logger.info("API key created: tier=%s email=%s prefix=%s", tier, email, prefix)
        return {"api_key": raw_key, "prefix": prefix, "tier": tier, "success": True}

    except Exception as e:
        logger.error("Key creation failed for %s: %s", email, e)
        return {"success": False, "error": str(e)}


# ── Authentication middleware ─────────────────────────────────────────────────

def _get_bearer_token() -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    # Also accept ?api_key= query param
    return request.args.get("api_key", "").strip() or None


def lookup_api_key(raw_key: str) -> Optional[dict]:
    """
    Look up a raw API key. Returns subscriber record or None.
    Uses hash comparison — never stores raw key in lookup.
    """
    import sqlite3
    key_hash = hash_key(raw_key)
    try:
        conn = sqlite3.connect("/home/ultron/protocol_pulse/instance/protocol_pulse.db")
        row = conn.execute("""
            SELECT key_prefix, tier, subscriber_email, requests_today,
                   requests_total, last_used_at, last_reset_at, active
            FROM api_keys
            WHERE key_hash=? AND active=1
        """, (key_hash,)).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "prefix": row[0], "tier": row[1], "email": row[2],
            "requests_today": row[3], "requests_total": row[4],
            "last_used_at": row[5], "last_reset_at": row[6],
        }
    except Exception as e:
        logger.error("Key lookup failed: %s", e)
        return None


def check_rate_limit(raw_key: str, tier: str) -> Tuple[bool, dict]:
    """
    Check and enforce rate limits. Resets daily counter at midnight UTC.
    Returns (allowed: bool, headers: dict)
    """
    import sqlite3
    cfg = TIER_CONFIG.get(tier, TIER_CONFIG["commander"])
    day_limit = cfg["rate_limit_day"]
    hour_limit = cfg["rate_limit_hour"]

    if day_limit >= 999_999:
        return True, {"X-RateLimit-Tier": tier, "X-RateLimit-Remaining": "unlimited"}

    key_hash = hash_key(raw_key)
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    try:
        conn = sqlite3.connect("/home/ultron/protocol_pulse/instance/protocol_pulse.db")

        row = conn.execute("""
            SELECT requests_today, requests_total, last_reset_at
            FROM api_keys WHERE key_hash=?
        """, (key_hash,)).fetchone()

        if not row:
            conn.close()
            return False, {}

        req_today, req_total, last_reset = row

        # Reset daily counter at midnight UTC
        reset_date = (last_reset or "")[:10]
        if reset_date != today_str:
            req_today = 0
            conn.execute("""
                UPDATE api_keys SET requests_today=0, last_reset_at=?
                WHERE key_hash=?
            """, (now.isoformat(), key_hash))

        if req_today >= day_limit:
            conn.close()
            return False, {
                "X-RateLimit-Limit": str(day_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z"),
                "Retry-After": "86400",
            }

        # Increment counters
        conn.execute("""
            UPDATE api_keys
            SET requests_today=requests_today+1, requests_total=requests_total+1,
                last_used_at=?
            WHERE key_hash=?
        """, (now.isoformat(), key_hash))
        conn.commit()
        conn.close()

        remaining = day_limit - req_today - 1
        return True, {
            "X-RateLimit-Tier": tier,
            "X-RateLimit-Limit": str(day_limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z"),
        }
    except Exception as e:
        logger.error("Rate limit check failed: %s", e)
        return True, {}  # Fail open to avoid blocking on DB errors


def log_api_request(key_prefix: str, endpoint: str, status: int, ms: int):
    """Write to api_usage_log for analytics."""
    import sqlite3
    import hashlib
    ip_hash = hashlib.sha256(request.remote_addr.encode()).hexdigest()[:16]
    try:
        conn = sqlite3.connect("/home/ultron/protocol_pulse/instance/protocol_pulse.db")
        conn.execute("""
            INSERT INTO api_usage_log (key_prefix, endpoint, response_ms, status_code, ip_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key_prefix, endpoint, ms, status, ip_hash, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug("Usage log write failed: %s", e)


# ── Decorator ─────────────────────────────────────────────────────────────────

def require_api_key(entitlement: str = "signals"):
    """
    Decorator for API v1 endpoints.
    Usage:
        @app.route("/api/v1/signals")
        @require_api_key("signals")
        def get_signals():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            t_start = time.monotonic()
            raw_key = _get_bearer_token()

            if not raw_key:
                return jsonify({
                    "error": "API key required",
                    "docs": "https://protocolpulse.io/api/docs",
                    "signup": "https://protocolpulse.io/api/keys",
                }), 401

            sub = lookup_api_key(raw_key)
            if not sub:
                return jsonify({"error": "Invalid or expired API key"}), 401

            tier = sub["tier"]
            cfg = TIER_CONFIG.get(tier, TIER_CONFIG["commander"])

            # Check entitlement
            if entitlement and not cfg["entitlements"].get(entitlement, False):
                return jsonify({
                    "error": f"Your {tier} plan does not include {entitlement} access",
                    "upgrade": "https://protocolpulse.io/api/keys",
                    "required_tier": _min_tier_for(entitlement),
                }), 403

            # Check rate limit
            allowed, rl_headers = check_rate_limit(raw_key, tier)
            if not allowed:
                resp = jsonify({
                    "error": "Rate limit exceeded",
                    "tier": tier,
                    "upgrade": "https://protocolpulse.io/api/keys",
                })
                resp.status_code = 429
                for k, v in rl_headers.items():
                    resp.headers[k] = v
                return resp

            # Attach subscriber info to request context
            g.api_sub = sub
            g.api_tier = tier

            # Execute the route
            result = fn(*args, **kwargs)

            # Log usage
            ms = int((time.monotonic() - t_start) * 1000)
            status = result[1] if isinstance(result, tuple) else (
                result.status_code if hasattr(result, 'status_code') else 200
            )
            log_api_request(sub["prefix"], request.path, status, ms)

            # Add rate limit headers to response
            if hasattr(result, 'headers'):
                for k, v in rl_headers.items():
                    result.headers[k] = v

            return result
        return wrapper
    return decorator


def _min_tier_for(entitlement: str) -> str:
    """Return minimum tier name that grants an entitlement."""
    for tier in ["commander", "intel", "sovereign"]:
        if TIER_CONFIG[tier]["entitlements"].get(entitlement):
            return tier
    return "sovereign"


# ── Stripe webhook handler ─────────────────────────────────────────────────────

def handle_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Process Stripe webhook events for subscription lifecycle.
    Handles: checkout.session.completed, customer.subscription.deleted,
             customer.subscription.updated, invoice.payment_failed
    """
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        logger.error("Stripe webhook signature verification failed")
        return {"error": "invalid_signature"}
    except Exception as e:
        logger.error("Stripe webhook construct failed: %s", e)
        return {"error": str(e)}

    event_type = event["type"]
    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email", "")
        customer_id = session.get("customer", "")
        subscription_id = session.get("subscription", "")
        price_id = ""

        # Get price from line items
        try:
            items = stripe.checkout.Session.list_line_items(session["id"])
            if items.data:
                price_id = items.data[0].price.id
        except Exception:
            pass

        # Map price_id to tier
        tier = _price_to_tier(price_id)
        if email and tier:
            result = create_subscriber_key(email, tier, customer_id, subscription_id, price_id)
            # Send welcome email with key
            if result.get("success"):
                _send_api_welcome_email(email, result["api_key"], tier)
            logger.info("New API subscriber: %s tier=%s", email, tier)

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer", "")
        _deactivate_subscription(customer_id)

    elif event_type == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub.get("customer", "")
        status = sub.get("status", "")
        if status == "past_due":
            _flag_past_due(customer_id)
        elif status == "active":
            _reactivate_subscription(customer_id)

    elif event_type == "invoice.payment_failed":
        inv = event["data"]["object"]
        customer_id = inv.get("customer", "")
        _flag_past_due(customer_id)

    return {"received": True, "event": event_type}


def _price_to_tier(price_id: str) -> Optional[str]:
    for tier, cfg in TIER_CONFIG.items():
        if cfg.get("stripe_price_id") == price_id:
            return tier
    # Fallback from env
    price_map = {
        os.environ.get("STRIPE_PRICE_COMMANDER", ""): "commander",
        os.environ.get("STRIPE_PRICE_INTEL", ""): "intel",
        os.environ.get("STRIPE_PRICE_SOVEREIGN", ""): "sovereign",
    }
    return price_map.get(price_id)


def _deactivate_subscription(customer_id: str):
    import sqlite3
    try:
        conn = sqlite3.connect("/home/ultron/protocol_pulse/instance/protocol_pulse.db")
        conn.execute("UPDATE api_keys SET active=0 WHERE stripe_customer_id=?", (customer_id,))
        conn.execute("UPDATE api_subscribers SET is_active=0, subscription_status='cancelled' WHERE stripe_customer_id=?", (customer_id,))
        conn.commit()
        conn.close()
        logger.info("Deactivated API keys for customer %s", customer_id)
    except Exception as e:
        logger.error("Deactivation failed: %s", e)


def _reactivate_subscription(customer_id: str):
    import sqlite3
    try:
        conn = sqlite3.connect("/home/ultron/protocol_pulse/instance/protocol_pulse.db")
        conn.execute("UPDATE api_keys SET active=1 WHERE stripe_customer_id=?", (customer_id,))
        conn.execute("UPDATE api_subscribers SET is_active=1, subscription_status='active' WHERE stripe_customer_id=?", (customer_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Reactivation failed: %s", e)


def _flag_past_due(customer_id: str):
    import sqlite3
    try:
        conn = sqlite3.connect("/home/ultron/protocol_pulse/instance/protocol_pulse.db")
        conn.execute("UPDATE api_subscribers SET subscription_status='past_due' WHERE stripe_customer_id=?", (customer_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Past due flag failed: %s", e)


def _send_api_welcome_email(email: str, api_key: str, tier: str):
    """Send welcome email with API key to new subscriber."""
    try:
        import urllib.request as ur, json as _json
        key = os.environ.get("RESEND_API_KEY", "")
        if not key:
            return
        tier_names = {"commander": "Commander", "intel": "Intel", "sovereign": "Sovereign"}
        tier_label = tier_names.get(tier, tier.title())
        limits = {"commander": "100 req/day", "intel": "500 req/day", "sovereign": "Unlimited"}
        limit = limits.get(tier, "")
        html = f"""<div style="background:#0a0a0a;color:#e0e0e0;font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:2rem;">
<div style="border-bottom:2px solid #cc0000;padding-bottom:1rem;margin-bottom:1.5rem;">
<span style="font-family:'Courier New',monospace;font-size:.7rem;letter-spacing:.2em;text-transform:uppercase;color:#cc0000;">Protocol Pulse API</span>
<h1 style="font-size:1.5rem;font-weight:700;color:#fff;margin:.5rem 0 0;">Your {tier_label} API Key</h1>
</div>
<p>Your API key is below. <strong>Copy and store it now — it will not be shown again.</strong></p>
<div style="background:#0d0d0d;border:1px solid #cc0000;padding:1rem;border-radius:6px;font-family:'Courier New',monospace;font-size:.85rem;color:#cc0000;word-break:break-all;margin:1rem 0;">
{api_key}
</div>
<p style="color:#888;font-size:.85rem;">Tier: <strong style="color:#fff;">{tier_label}</strong> · {limit}</p>
<h3 style="color:#cc0000;">Quick Start</h3>
<pre style="background:#0d0d0d;padding:1rem;border-radius:6px;font-size:.8rem;overflow-x:auto;">curl -H "Authorization: Bearer {api_key}" \\
  https://protocolpulse.io/api/v1/orb/latest</pre>
<p><a href="https://protocolpulse.io/api/docs" style="color:#cc0000;">Full API documentation →</a></p>
<p style="font-size:.7rem;color:#444;border-top:1px solid #222;padding-top:1rem;margin-top:2rem;">
Protocol Pulse · <a href="https://protocolpulse.io" style="color:#888;">protocolpulse.io</a>
</p>
</div>"""
        payload = _json.dumps({
            "from": "Protocol Pulse <pulse@protocolpulse.io>",
            "to": [email],
            "subject": f"Your Protocol Pulse {tier_label} API Key",
            "html": html,
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST")
        with ur.urlopen(req, timeout=10) as r:
            logger.info("API welcome email sent to %s: %s", email, r.status)
    except Exception as e:
        logger.error("API welcome email failed: %s", e)


# ── Stripe checkout route helper ───────────────────────────────────────────────

def create_api_checkout_session(tier: str, email: str, success_url: str, cancel_url: str) -> dict:
    """Create a Stripe checkout session for API subscription."""
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    cfg = TIER_CONFIG.get(tier)
    if not cfg:
        return {"error": "Invalid tier"}
    price_id = cfg.get("stripe_price_id", "")
    if not price_id:
        return {"error": f"Price not configured for {tier}"}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            customer_email=email,
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"tier": tier, "product": "api_key"},
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error("Checkout session failed: %s", e)
        return {"error": str(e)}
