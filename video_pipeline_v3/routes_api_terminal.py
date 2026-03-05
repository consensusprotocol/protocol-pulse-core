"""Pulse Terminal API — Premium Bitcoin Intelligence endpoints.

Endpoints:
  GET /api/v2/terminal/topics     — Topic velocity data
  GET /api/v2/terminal/entities   — Entity mention tracking
  GET /api/v2/terminal/sentiment  — Overall market sentiment
  GET /api/v2/terminal/breaking   — Breaking news alerts
  GET /api/v2/terminal/network    — Bitcoin network health (nodes, hashrate, halving)
  GET /api/v2/terminal/docs       — OpenAPI documentation

Authentication: X-API-Key header required on all data endpoints.
Rate limits enforced per tier (free/operator/commander/sovereign).
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

terminal_bp = Blueprint("terminal", __name__)

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "intelligence"
ARCHIVE_DIR = BASE_DIR / "data" / "channel_archive"
USAGE_DIR = BASE_DIR / "data" / "terminal" / "usage"
NODE_SNAPSHOTS_DIR = BASE_DIR / "data" / "node_snapshots"

# Tier rate limits (requests per day)
TIER_LIMITS = {
    "free": 10,
    "operator": 100,
    "commander": 1000,
    "sovereign": -1,  # unlimited
}

# Endpoints restricted by tier
TIER_ENDPOINTS = {
    "free": {"/api/v2/terminal/topics"},
    "operator": {"/api/v2/terminal/topics", "/api/v2/terminal/entities",
                 "/api/v2/terminal/sentiment", "/api/v2/terminal/breaking",
                 "/api/v2/terminal/network"},
    "commander": "all",
    "sovereign": "all",
}

# Bitcoin halving constants
HALVING_INTERVAL = 210000
LAST_HALVING_BLOCK = 840000  # April 2024 halving
NEXT_HALVING_BLOCK = LAST_HALVING_BLOCK + HALVING_INTERVAL  # 1,050,000


# ─── Data Loading ─────────────────────────────────────────────

def _load_json(path):
    """Load a JSON file, return None if missing or invalid."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_api_keys():
    return _load_json(CONFIG_DIR / "api_keys.json") or {"keys": []}


# ─── Rate Limiting ────────────────────────────────────────────

def _get_usage_path(api_key: str) -> Path:
    """Get usage file path for an API key (hashed for security)."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return USAGE_DIR / f"{key_hash}.json"


def _get_usage(api_key: str) -> dict:
    """Get current day's usage for an API key."""
    path = _get_usage_path(api_key)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = _load_json(path)
    if data and data.get("date") == today:
        return data
    return {"date": today, "requests": 0, "endpoints": {}}


def _increment_usage(api_key: str, endpoint: str):
    """Increment usage counter for an API key."""
    usage = _get_usage(api_key)
    usage["requests"] += 1
    usage["endpoints"][endpoint] = usage["endpoints"].get(endpoint, 0) + 1
    usage["last_request"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    path = _get_usage_path(api_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(usage, f)
    return usage


def _check_rate_limit(api_key: str, tier: str) -> tuple:
    """Check if API key has exceeded rate limit.

    Returns (allowed: bool, usage: dict).
    """
    limit = TIER_LIMITS.get(tier, 10)
    if limit == -1:  # unlimited
        return True, _get_usage(api_key)
    usage = _get_usage(api_key)
    return usage["requests"] < limit, usage


# ─── Response Metadata ────────────────────────────────────────

def _build_meta(tier: str, api_key: str, freshness: str = None) -> dict:
    """Build standard response metadata."""
    limit = TIER_LIMITS.get(tier, 10)
    usage = _get_usage(api_key)
    remaining = max(0, limit - usage["requests"]) if limit != -1 else "unlimited"
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return {
        "tier": tier,
        "freshness": freshness or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rate_limit_remaining": remaining,
        "rate_limit_reset": tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ─── Auth + Rate Limit Decorator ─────────────────────────────

def require_api_key(f):
    """Decorator: authenticate via X-API-Key header and enforce rate limits."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key", "")
        if not api_key:
            return jsonify({"error": "Missing X-API-Key header. Get your key at protocolpulse.io/terminal"}), 401

        keys_data = _load_api_keys()
        matched = None
        for entry in keys_data.get("keys", []):
            if entry.get("key") == api_key and entry.get("active", True):
                matched = entry
                break

        if not matched:
            return jsonify({"error": "Invalid or inactive API key"}), 401

        tier = matched.get("tier", "free")
        endpoint = request.path

        # Check endpoint access
        allowed_endpoints = TIER_ENDPOINTS.get(tier, set())
        if allowed_endpoints != "all" and endpoint not in allowed_endpoints:
            return jsonify({
                "error": f"Endpoint {endpoint} not available on {tier} tier. Upgrade at protocolpulse.io/terminal",
                "tier": tier,
            }), 403

        # Check rate limit
        allowed, usage = _check_rate_limit(api_key, tier)
        if not allowed:
            limit = TIER_LIMITS.get(tier, 10)
            tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            resp = jsonify({
                "error": f"Rate limit exceeded. {tier} tier allows {limit} requests/day.",
                "tier": tier,
                "retry_after": tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            resp.headers["Retry-After"] = str(int((tomorrow - datetime.now(timezone.utc)).total_seconds()))
            return resp, 429

        # Track usage
        _increment_usage(api_key, endpoint)

        # Attach to request context
        request.api_tier = tier
        request.api_key = api_key
        request.api_subscriber = matched.get("subscriber", "unknown")
        return f(*args, **kwargs)
    return decorated


# ─── Free tier data delay ─────────────────────────────────────

def _apply_free_delay(data: dict, tier: str) -> dict:
    """For free tier, shift freshness timestamps back 24 hours."""
    if tier != "free":
        return data
    # Don't mutate original
    import copy
    delayed = copy.deepcopy(data)
    if "scan_time" in delayed:
        try:
            ts = datetime.fromisoformat(delayed["scan_time"].replace("Z", "+00:00"))
            delayed["scan_time"] = (ts - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            delayed["delayed"] = True
            delayed["delay_hours"] = 24
        except (ValueError, AttributeError):
            pass
    return delayed


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@terminal_bp.route("/api/v2/terminal/topics", methods=["GET"])
@require_api_key
def get_topics():
    """Topic velocity — what Bitcoin YouTube is talking about right now."""
    tier = getattr(request, "api_tier", "free")
    api_key = getattr(request, "api_key", "")

    data = _load_json(DATA_DIR / "daily_signals.json")
    if data is None:
        return jsonify({
            "data": None,
            "error": "Intelligence data not yet available. Daemon populating.",
            "meta": _build_meta(tier, api_key, freshness=None),
        })

    topics = data.get("topic_velocity", [])
    freshness = data.get("scan_time")

    # Query param filters
    min_velocity = request.args.get("min_velocity", type=int)
    topic_filter = request.args.get("topic", "").lower()

    if min_velocity:
        topics = [t for t in topics if t.get("velocity_score", 0) >= min_velocity]
    if topic_filter:
        topics = [t for t in topics if topic_filter in t.get("topic", "").lower()]

    # Free tier: top 3 only
    if tier == "free":
        topics = topics[:3]

    result = {
        "data": {
            "topics": topics,
            "scan_time": freshness,
            "total_channels_monitored": 80,
            "total_videos_analyzed_24h": data.get("total_videos_48h", 0),
        },
        "meta": _build_meta(tier, api_key, freshness),
    }

    return jsonify(_apply_free_delay(result, tier))


@terminal_bp.route("/api/v2/terminal/entities", methods=["GET"])
@require_api_key
def get_entities():
    """Entity tracking — who's being talked about and how sentiment is shifting."""
    tier = getattr(request, "api_tier", "free")
    api_key = getattr(request, "api_key", "")

    data = _load_json(DATA_DIR / "entity_mentions.json")

    # If file doesn't exist, generate it
    if data is None:
        try:
            from utils.entity_tracker import build_entity_mentions
            data = build_entity_mentions()
        except Exception as e:
            return jsonify({
                "data": None,
                "error": f"Entity data not yet available: {e}",
                "meta": _build_meta(tier, api_key),
            })

    entities = data.get("entities", [])
    freshness = data.get("scan_time")

    # Query params
    entity_type = request.args.get("type", "").lower()
    min_mentions = request.args.get("min_mentions", type=int)
    sort_by = request.args.get("sort", "mentions")

    if entity_type:
        entities = [e for e in entities if e.get("type", "").lower() == entity_type]
    if min_mentions:
        entities = [e for e in entities if e.get("mentions_24h", 0) >= min_mentions]
    if sort_by == "channels":
        entities.sort(key=lambda e: e.get("channels_covering", 0), reverse=True)

    result = {
        "data": {"entities": entities},
        "meta": _build_meta(tier, api_key, freshness),
    }

    return jsonify(_apply_free_delay(result, tier))


@terminal_bp.route("/api/v2/terminal/sentiment", methods=["GET"])
@require_api_key
def get_sentiment():
    """Market sentiment composite — the Protocol Pulse sentiment index."""
    tier = getattr(request, "api_tier", "free")
    api_key = getattr(request, "api_key", "")

    data = _load_json(DATA_DIR / "sentiment.json")

    # If file doesn't exist, compute it
    if data is None:
        try:
            from utils.sentiment_calculator import compute_sentiment
            data = compute_sentiment()
        except Exception as e:
            return jsonify({
                "data": None,
                "error": f"Sentiment data not yet available: {e}",
                "meta": _build_meta(tier, api_key),
            })

    freshness = data.get("scan_time")
    result = {
        "data": data.get("data", data),
        "meta": _build_meta(tier, api_key, freshness),
    }

    return jsonify(_apply_free_delay(result, tier))


@terminal_bp.route("/api/v2/terminal/breaking", methods=["GET"])
@require_api_key
def get_breaking():
    """Breaking news detection — real-time alerts when narrative convergence detected."""
    tier = getattr(request, "api_tier", "free")
    api_key = getattr(request, "api_key", "")

    data = _load_json(DATA_DIR / "daily_signals.json")
    if data is None:
        return jsonify({
            "data": {"breaking": False, "monitoring": True, "alert": None},
            "meta": _build_meta(tier, api_key),
        })

    topics = data.get("topic_velocity", [])
    breaking = data.get("breaking_threshold", False)

    # Find the highest velocity topic as the alert
    alert = None
    if breaking and topics:
        top = max(topics, key=lambda t: t.get("velocity_score", 0))
        if top.get("channels", 0) >= 4:
            alert = {
                "topic": top.get("topic", ""),
                "velocity_score": top.get("velocity_score", 0),
                "channels": top.get("channels", 0),
                "detected_at": data.get("scan_time", ""),
                "severity": "high" if top.get("channels", 0) >= 6 else "medium",
                "summary": f"{top.get('channels', 0)} channels covering {top.get('topic', '')} "
                           f"within scan window",
            }

    # Threshold config
    threshold = {"channels": 4, "window_hours": 3}

    result = {
        "data": {
            "breaking": breaking,
            "alert": alert,
            "recent_alerts": [],
            "monitoring": True,
            "threshold": threshold,
        },
        "meta": _build_meta(tier, api_key, data.get("scan_time")),
    }

    return jsonify(result)


@terminal_bp.route("/api/v2/terminal/network", methods=["GET"])
@require_api_key
def get_network():
    """Bitcoin network health — node count, hashrate, difficulty, halving countdown."""
    tier = getattr(request, "api_tier", "free")
    api_key = getattr(request, "api_key", "")

    # Node data from cache
    node_data = _load_json(NODE_SNAPSHOTS_DIR / "latest.json")
    nodes_response = {"total_reachable": None, "net_change_24h": 0}

    if node_data:
        nodes_response = {
            "total_reachable": node_data.get("total_nodes", 0),
            "net_change_24h": node_data.get("comparison", {}).get("net_change", 0),
        }
    else:
        # Try fetching live
        try:
            from utils.node_monitor import get_node_snapshot
            snapshot = get_node_snapshot()
            nodes_response["total_reachable"] = snapshot.get("total_nodes", 0)
        except Exception:
            pass

    # Block height and halving calc
    latest_height = 0
    if node_data:
        latest_height = node_data.get("latest_height", 0)

    halving_blocks_remaining = max(0, NEXT_HALVING_BLOCK - latest_height) if latest_height else None
    # ~10 min per block
    if halving_blocks_remaining:
        halving_minutes = halving_blocks_remaining * 10
        estimated_date = (datetime.now(timezone.utc) + timedelta(minutes=halving_minutes)).strftime("%Y-%m-%d")
    else:
        estimated_date = None

    result = {
        "data": {
            "nodes": nodes_response,
            "halving": {
                "blocks_remaining": halving_blocks_remaining,
                "estimated_date": estimated_date,
                "next_halving_block": NEXT_HALVING_BLOCK,
            },
            "latest_block_height": latest_height or None,
        },
        "meta": _build_meta(tier, api_key, node_data.get("fetched_at") if node_data else None),
    }

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════
# DOCS ENDPOINT
# ═══════════════════════════════════════════════════════════════

@terminal_bp.route("/api/v2/terminal/docs")
def terminal_docs():
    """Serve OpenAPI documentation page."""
    docs_path = BASE_DIR / "static" / "terminal_api_docs.html"
    if docs_path.exists():
        return send_from_directory(str(BASE_DIR / "static"), "terminal_api_docs.html")
    # Fallback: redirect to YAML
    yaml_path = BASE_DIR / "openapi_terminal.yaml"
    if yaml_path.exists():
        return send_from_directory(str(BASE_DIR), "openapi_terminal.yaml",
                                   mimetype="text/yaml")
    return jsonify({"error": "Documentation not yet generated"}), 404


# ═══════════════════════════════════════════════════════════════
# STRIPE SUBSCRIPTION ENDPOINTS (stubs — wire when keys available)
# ═══════════════════════════════════════════════════════════════

@terminal_bp.route("/api/v2/terminal/subscribe", methods=["POST"])
def terminal_subscribe():
    """Create a Stripe checkout session for Terminal subscription.

    Body: {"tier": "commander", "email": "user@example.com"}
    Returns: {"checkout_url": "https://checkout.stripe.com/..."}

    TODO: Wire when STRIPE_SECRET_KEY is configured.
    Requires: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET in env.
    Products to create:
      - Pulse Terminal Operator ($19/mo)
      - Pulse Terminal Commander ($49/mo)
      - Pulse Terminal Sovereign ($99/mo)
    """
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({
            "error": "Stripe not yet configured. Contact team@protocolpulse.io for access.",
            "pricing": {
                "operator": {"price": "$19/month", "requests": "100/day"},
                "commander": {"price": "$49/month", "requests": "1,000/day"},
                "sovereign": {"price": "$99/month", "requests": "unlimited"},
            },
        }), 503

    body = request.get_json(silent=True) or {}
    tier = body.get("tier", "").lower()
    email = body.get("email", "")

    if tier not in ("operator", "commander", "sovereign"):
        return jsonify({"error": "Invalid tier. Choose: operator, commander, sovereign"}), 400
    if not email:
        return jsonify({"error": "Email required"}), 400

    # Stripe checkout session creation
    try:
        import stripe
        stripe.api_key = stripe_key

        price_ids = {
            "operator": os.environ.get("STRIPE_PRICE_OPERATOR"),
            "commander": os.environ.get("STRIPE_PRICE_COMMANDER"),
            "sovereign": os.environ.get("STRIPE_PRICE_SOVEREIGN"),
        }

        price_id = price_ids.get(tier)
        if not price_id:
            return jsonify({"error": f"Stripe price not configured for {tier} tier"}), 503

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"https://protocolpulse.io/terminal/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://protocolpulse.io/terminal/pricing",
            metadata={"tier": tier},
        )
        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": f"Stripe error: {e}"}), 500


@terminal_bp.route("/api/v2/terminal/webhook", methods=["POST"])
def terminal_webhook():
    """Stripe webhook handler.

    Handles:
      - checkout.session.completed -> generate API key, store in api_keys.json
      - customer.subscription.deleted -> deactivate API key

    TODO: Wire when STRIPE_WEBHOOK_SECRET is configured.
    """
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not stripe_key or not webhook_secret:
        return jsonify({"error": "Stripe webhooks not configured"}), 503

    try:
        import stripe
        stripe.api_key = stripe_key

        payload = request.get_data(as_text=True)
        sig_header = request.headers.get("Stripe-Signature", "")
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        return jsonify({"error": f"Webhook verification failed: {e}"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tier = session.get("metadata", {}).get("tier", "operator")
        email = session.get("customer_email", "")

        # Generate API key
        import secrets
        new_key = f"pp-{tier}-{secrets.token_hex(16)}"

        # Add to api_keys.json
        keys_data = _load_api_keys()
        keys_data["keys"].append({
            "key": new_key,
            "tier": tier,
            "subscriber": email,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "active": True,
            "stripe_session": session.get("id"),
        })
        with open(CONFIG_DIR / "api_keys.json", "w") as f:
            json.dump(keys_data, f, indent=2)

        # TODO: Email API key via Resend
        return jsonify({"status": "key_generated", "tier": tier})

    elif event["type"] == "customer.subscription.deleted":
        # Deactivate associated key
        subscription = event["data"]["object"]
        keys_data = _load_api_keys()
        for key_entry in keys_data["keys"]:
            if key_entry.get("stripe_subscription") == subscription.get("id"):
                key_entry["active"] = False
        with open(CONFIG_DIR / "api_keys.json", "w") as f:
            json.dump(keys_data, f, indent=2)

        return jsonify({"status": "key_deactivated"})

    return jsonify({"status": "ignored"})
