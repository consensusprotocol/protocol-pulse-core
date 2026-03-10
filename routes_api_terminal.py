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
    "commander": 1000,
    "sovereign": -1,   # unlimited (V31)
    "watcher":   100,  # V31
}

COMMANDER_DAILY_LIMIT = 1000
BREAKING_LOOKBACK_HOURS = 2
HALVING_INTERVAL = 210_000
LAST_HALVING_BLOCK = 840_000
NEXT_HALVING_BLOCK = LAST_HALVING_BLOCK + HALVING_INTERVAL  # 1,050,000
EXTERNAL_TIMEOUT = 6

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
    """Top categories from published articles in last 24hr."""
    from models import Article
    cutoff = _utcnow() - timedelta(hours=24)
    try:
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff)
            .with_entities(Article.category, func.count(Article.id).label("cnt"))
            .group_by(Article.category)
            .order_by(func.count(Article.id).desc())
            .limit(20)
            .all()
        )
        return [
            {"topic": r.category or "Uncategorized", "count": r.cnt}
            for r in rows if r.category
        ]
    except Exception as e:
        log.error("topics query failed: %s", e)
        return []


def _get_entities():
    """Keyword/tag frequency from published articles in last 24hr."""
    from models import Article
    cutoff = _utcnow() - timedelta(hours=24)
    try:
        rows = (
            Article.query
            .filter(
                Article.published == True,
                Article.created_at > cutoff,
                Article.tags != None,
                Article.tags != "",
            )
            .with_entities(Article.tags)
            .limit(200)
            .all()
        )
        counts: dict = {}
        for (tags,) in rows:
            if not tags:
                continue
            for tag in tags.split(","):
                tag = tag.strip()
                if not tag or len(tag) < 2:
                    continue
                if tag not in counts:
                    counts[tag] = {"name": tag, "mentions_24h": 0, "type": "keyword"}
                counts[tag]["mentions_24h"] += 1

        return sorted(counts.values(), key=lambda x: x["mentions_24h"], reverse=True)[:30]
    except Exception as e:
        log.error("entities query failed: %s", e)
        return []


def _get_sentiment():
    """Return (score 0-100, as_of datetime). 0=bearish, 50=neutral, 100=bullish."""
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
            return score, latest.timestamp
    except Exception:
        pass

    # Fallback: keyword heuristic on article titles/summaries
    try:
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff)
            .with_entities(Article.title, Article.summary)
            .limit(100)
            .all()
        )
        bull_kw = {"bullish", "surge", "rally", "ath", "gain", "rise", "pump", "moon", "buy", "adoption", "institutional"}
        bear_kw = {"bearish", "crash", "dump", "drop", "fall", "bear", "sell", "fear", "ban", "hack"}
        bull, bear = 0, 0
        for r in rows:
            blob = f"{r.title or ''} {r.summary or ''}".lower()
            bull += sum(1 for kw in bull_kw if kw in blob)
            bear += sum(1 for kw in bear_kw if kw in blob)
        total = bull + bear
        if total == 0:
            return 50, None
        return int(bull / total * 100), None
    except Exception as e:
        log.error("sentiment fallback failed: %s", e)
        return 50, None


def _get_breaking():
    """Articles published in last 2hr."""
    from models import Article
    cutoff = _utcnow() - timedelta(hours=BREAKING_LOOKBACK_HOURS)
    try:
        rows = (
            Article.query
            .filter(Article.published == True, Article.created_at > cutoff)
            .order_by(Article.created_at.desc())
            .limit(10)
            .all()
        )
        return [
            {
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "summary": (a.summary or "")[:200],
                "published_at": _iso(a.created_at),
                "url": f"https://protocolpulse.io/articles/{a.id}",
            }
            for a in rows
        ]
    except Exception as e:
        log.error("breaking query failed: %s", e)
        return []


def _get_network_stats() -> dict:
    """Fetch Bitcoin network stats from public APIs with timeout + graceful degradation."""
    stats = {
        "hashrate_eh": None,
        "difficulty": None,
        "block_height": None,
        "nodes_reachable": None,
        "halving": {
            "next_halving_block": NEXT_HALVING_BLOCK,
            "blocks_remaining": None,
            "estimated_date": None,
        },
    }

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
        remaining = max(0, NEXT_HALVING_BLOCK - height)
        stats["halving"]["blocks_remaining"] = remaining
        if remaining > 0:
            est_dt = _utcnow() + timedelta(minutes=remaining * 10)
            stats["halving"]["estimated_date"] = _iso(est_dt)
        else:
            stats["halving"]["estimated_date"] = "OCCURRED"

    return stats


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

    score, as_of = _get_sentiment()
    label = "bullish" if score > 60 else ("bearish" if score < 40 else "neutral")

    return jsonify(_terminal_response(
        endpoint="sentiment",
        data={
            "score": score,
            "label": label,
            "scale": "0 (max bearish) — 100 (max bullish)",
            "as_of": _iso(as_of) if as_of else _iso(_utcnow()),
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

        price_id = os.environ.get("STRIPE_PRICE_COMMANDER", "").strip()
        if not price_id:
            return jsonify({"error": "Stripe price not configured for commander tier"}), 503

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
                "subject": "Your Pulse Terminal API Key — Commander Access",
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
