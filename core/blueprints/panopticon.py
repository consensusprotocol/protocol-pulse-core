"""
PANOPTICON Blueprint — Congressional Disclosure & Whale Intelligence Dashboard
"They watch us. Now we watch them."

Routes:
  /panopticon                          — Main dashboard (Commander-gated)
  /api/panopticon/disclosures          — STOCK Act filings (crypto-filtered)
  /api/panopticon/congress             — Alias for disclosures
  /api/panopticon/whale-alerts         — Whale wallet movements
  /api/panopticon/whales               — Alias for whale-alerts
  /api/panopticon/correlations         — Cross-reference timeline
  /api/panopticon/geopolitical         — Nation-state & macro signals
  /api/panopticon/polymarket           — Prediction market odds
  /api/panopticon/make-bitcoin-case    — AI-generated Bitcoin case (POST)
  /api/panopticon/bitcoin-case         — Alias for make-bitcoin-case
"""

import logging
import re
from flask import Blueprint, render_template, jsonify, request
from flask_login import current_user

logger = logging.getLogger(__name__)

panopticon_bp = Blueprint("panopticon", __name__)

# ── Rate limiter (P0 fix for U2 — IP-based throttling on all API routes) ────
# Applied via before_request to avoid circular import issues with app.limiter
_rate_limit_store = {}  # IP -> {count, window_start}
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 30  # requests per window for general API routes
_RATE_LIMIT_WHALE = 10  # tighter limit for expensive whale-alerts endpoint (P2 UI-2)
import time as _time


@panopticon_bp.before_request
def _enforce_rate_limit():
    """IP-based rate limiting for all /api/panopticon/* routes."""
    if not request.path.startswith("/api/panopticon/"):
        return None

    ip = request.remote_addr or "unknown"
    now = _time.time()
    key = f"{ip}:{request.path}"

    # Tighter limit for whale-alerts (most expensive upstream call)
    max_requests = _RATE_LIMIT_WHALE if "whale" in request.path else _RATE_LIMIT_MAX

    entry = _rate_limit_store.get(key)
    if entry is None or now - entry["start"] > _RATE_LIMIT_WINDOW:
        _rate_limit_store[key] = {"count": 1, "start": now}
        return None

    entry["count"] += 1
    if entry["count"] > max_requests:
        logger.warning("Rate limit exceeded: %s on %s (%d/%d)", ip, request.path,
                        entry["count"], max_requests)
        return jsonify({
            "error": "Rate limit exceeded",
            "retry_after": int(_RATE_LIMIT_WINDOW - (now - entry["start"])),
        }), 429

    return None

_EMPTY_DATA = {
    "btc_price": None,
    "events_today": 0,
    "disclosures": [],
    "flagged": [],
    "whales": [],
    "forex": [],
    "geopolitical": [],
    "correlations": [],
    "watch_list": [],
    "polymarket": [],
    "generated_at": None,
}

# Redacted teaser data for free-tier users (no real Commander data leaked)
_DEMO_DATA = {
    "btc_price": None,
    "events_today": 12,
    "disclosures": [
        {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
        {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
        {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
    ],
    "flagged": [
        {"entity": "██████████", "asset": "CLASSIFIED", "tier": "flagged", "correlation_score": 0.0, "flag_reason": "CLASSIFIED — Upgrade to Commander"},
    ],
    "whales": [
        {"entity": "██████████", "wallet_label": "CLASSIFIED", "address": "████...████", "txid": "████...████", "amount_btc": 0, "tx_type": "classified", "confirmed": True, "timestamp": "████-██-██", "event_type": "whale"},
    ],
    "forex": [],
    "geopolitical": [
        {"headline": "CLASSIFIED — Upgrade to Commander for geopolitical intelligence", "category": "classified", "btc_signal": "neutral", "btc_rationale": "CLASSIFIED", "source": "CLASSIFIED", "timestamp": "████-██-██", "event_type": "geopolitical"},
    ],
    "correlations": [],
    "watch_list": [],
    "polymarket": [
        {"question": "CLASSIFIED — Upgrade to Commander for prediction market data", "yes_price": None, "volume": 0, "event_type": "prediction", "btc_signal": "neutral"},
    ],
    "generated_at": None,
}


def _is_commander() -> bool:
    """Check if current user has Commander+ tier access."""
    if not current_user.is_authenticated:
        return False
    tier = getattr(current_user, "subscription_tier", "free")
    return tier in ("commander", "sovereign")


def _sanitize_event_summary(text: str) -> str:
    """Sanitize user input for the Make Bitcoin Case prompt to prevent injection."""
    # Strip control characters and excessive whitespace
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Remove common prompt injection patterns
    text = re.sub(r'(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)', '', text)
    # Limit to alphanumeric, basic punctuation, and spaces
    text = re.sub(r'[^\w\s.,;:!?\'"\-()/$%@#&+=]', '', text)
    return text.strip()[:500]


# ═══════════════════════════════════════════════════════════════════════════
# PAGE ROUTE
# ═══════════════════════════════════════════════════════════════════════════

@panopticon_bp.route("/panopticon")
def panopticon_page():
    """PANOPTICON dashboard — Commander tier sees full data, free tier sees redacted CLASSIFIED data.
    SECURITY: Free-tier users receive only redacted placeholder data. Real Commander data is NEVER
    embedded in the HTML payload for unauthenticated or free-tier users."""
    demo_mode = not _is_commander()

    if demo_mode:
        # Free tier: send only redacted demo data — no real data touches the template
        data = _DEMO_DATA
    else:
        # Commander tier: fetch real intelligence data
        try:
            from services.panopticon_service import get_dashboard_data
            data = get_dashboard_data()
        except Exception as e:
            logger.error("Panopticon data fetch failed: %s", e)
            data = _EMPTY_DATA

    return render_template(
        "panopticon.html",
        demo_mode=demo_mode,
        data=data,
    )


# ═══════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@panopticon_bp.route("/api/panopticon/disclosures")
@panopticon_bp.route("/api/panopticon/congress")
def api_disclosures():
    """Recent STOCK Act filings filtered for crypto/fintech."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        from services.panopticon_service import fetch_disclosures
        limit = min(int(request.args.get("limit", 50)), 100)
        disclosures, is_live = fetch_disclosures(limit=limit)
        return jsonify({
            "disclosures": disclosures,
            "count": len(disclosures),
            "is_live": is_live,
            "tier": "confirmed",
        })
    except Exception as e:
        logger.error("Disclosures API error: %s", e)
        return jsonify({"error": "Failed to fetch disclosures"}), 500


@panopticon_bp.route("/api/panopticon/whale-alerts")
@panopticon_bp.route("/api/panopticon/whales")
def api_whale_alerts():
    """Recent large BTC wallet movements from known entities."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        from services.panopticon_service import fetch_whale_alerts, get_btc_price
        limit = min(int(request.args.get("limit", 20)), 50)
        alerts = fetch_whale_alerts(limit=limit)
        btc_price = get_btc_price()

        # Enrich with USD
        if btc_price:
            for a in alerts:
                if a.get("amount_btc"):
                    a["amount_usd"] = round(a["amount_btc"] * btc_price, 2)

        return jsonify({
            "alerts": alerts,
            "count": len(alerts),
            "btc_price": btc_price,
        })
    except Exception as e:
        logger.error("Whale alerts API error: %s", e)
        return jsonify({"error": "Failed to fetch whale alerts"}), 500


@panopticon_bp.route("/api/panopticon/correlations")
def api_correlations():
    """Cross-reference timeline: disclosures x whale movements x geopolitical events."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        from services.panopticon_service import build_correlations
        limit = min(int(request.args.get("limit", 10)), 25)
        correlations = build_correlations(limit=limit)
        return jsonify({
            "correlations": correlations,
            "count": len(correlations),
        })
    except Exception as e:
        logger.error("Correlations API error: %s", e)
        return jsonify({"error": "Failed to build correlations"}), 500


@panopticon_bp.route("/api/panopticon/geopolitical")
def api_geopolitical():
    """Nation-state signals, forex interventions, sovereign BTC activity."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        from services.panopticon_service import fetch_geopolitical, fetch_forex_signals
        geo = fetch_geopolitical()
        forex = fetch_forex_signals()
        return jsonify({
            "geopolitical": geo,
            "forex": forex,
            "count": len(geo) + len(forex),
        })
    except Exception as e:
        logger.error("Geopolitical API error: %s", e)
        return jsonify({"error": "Failed to fetch geopolitical signals"}), 500


@panopticon_bp.route("/api/panopticon/polymarket")
def api_polymarket():
    """Live Polymarket prediction market odds for crypto/macro events."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        from services.panopticon_service import fetch_polymarket_markets
        limit = min(int(request.args.get("limit", 15)), 30)
        markets = fetch_polymarket_markets(limit=limit)
        return jsonify({
            "markets": markets,
            "count": len(markets),
        })
    except Exception as e:
        logger.error("Polymarket API error: %s", e)
        return jsonify({"error": "Failed to fetch Polymarket data"}), 500


@panopticon_bp.route("/api/panopticon/make-bitcoin-case", methods=["POST"])
@panopticon_bp.route("/api/panopticon/bitcoin-case", methods=["POST"])
def api_make_bitcoin_case():
    """Generate a cypherpunk Bitcoin self-custody argument for a specific event via Claude."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        body = request.get_json(silent=True) or {}
        raw_summary = body.get("event_summary", "").strip()
        if not raw_summary:
            return jsonify({"error": "event_summary is required"}), 400
        event_summary = _sanitize_event_summary(raw_summary)
        if not event_summary:
            return jsonify({"error": "event_summary contains no valid content"}), 400

        from services.panopticon_service import get_make_bitcoin_case
        result = get_make_bitcoin_case(event_summary)
        return jsonify(result)
    except Exception as e:
        logger.error("Make Bitcoin Case API error: %s", e)
        return jsonify({"error": "Failed to generate Bitcoin case"}), 500
