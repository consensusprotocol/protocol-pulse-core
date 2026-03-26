"""
PANOPTICON Blueprint — Congressional Disclosure & Whale Intelligence Dashboard
"They watch us. Now we watch them."

Routes:
  /panopticon                     — Main dashboard (Commander-gated)
  /api/panopticon/disclosures     — STOCK Act filings (crypto-filtered)
  /api/panopticon/whale-alerts    — Whale wallet movements
  /api/panopticon/correlations    — Cross-reference timeline
  /api/panopticon/geopolitical    — Nation-state & macro signals
"""

import logging
from flask import Blueprint, render_template, jsonify, request
from flask_login import current_user

logger = logging.getLogger(__name__)

panopticon_bp = Blueprint("panopticon", __name__)


def _is_commander() -> bool:
    """Check if current user has Commander+ tier access."""
    if not current_user.is_authenticated:
        return False
    tier = getattr(current_user, "subscription_tier", "free")
    return tier in ("commander", "sovereign")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE ROUTE
# ═══════════════════════════════════════════════════════════════════════════

@panopticon_bp.route("/panopticon")
def panopticon_page():
    """PANOPTICON dashboard — Commander tier sees full data, free tier sees CLASSIFIED overlays."""
    demo_mode = not _is_commander()

    # Always fetch data — free tier sees structure with overlays
    try:
        from services.panopticon_service import get_dashboard_data
        data = get_dashboard_data()
    except Exception as e:
        logger.error("Panopticon data fetch failed: %s", e)
        data = {
            "btc_price": None,
            "events_today": 0,
            "disclosures": [],
            "flagged": [],
            "whales": [],
            "forex": [],
            "geopolitical": [],
            "correlations": [],
            "watch_list": [],
            "generated_at": None,
        }

    return render_template(
        "panopticon.html",
        demo_mode=demo_mode,
        data=data,
    )


# ═══════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@panopticon_bp.route("/api/panopticon/disclosures")
def api_disclosures():
    """Recent STOCK Act filings filtered for crypto/fintech."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        from services.panopticon_service import fetch_disclosures
        limit = min(int(request.args.get("limit", 50)), 100)
        disclosures = fetch_disclosures(limit=limit)
        return jsonify({
            "disclosures": disclosures,
            "count": len(disclosures),
            "tier": "confirmed",
        })
    except Exception as e:
        logger.error("Disclosures API error: %s", e)
        return jsonify({"error": "Failed to fetch disclosures"}), 500


@panopticon_bp.route("/api/panopticon/whale-alerts")
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
    """Cross-reference timeline: disclosures × whale movements × geopolitical events."""
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


@panopticon_bp.route("/api/panopticon/make-bitcoin-case", methods=["POST"])
def api_make_bitcoin_case():
    """Generate a cypherpunk Bitcoin self-custody argument for a specific event via Claude."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403

    try:
        body = request.get_json(silent=True) or {}
        event_summary = body.get("event_summary", "").strip()
        if not event_summary:
            return jsonify({"error": "event_summary is required"}), 400
        if len(event_summary) > 500:
            event_summary = event_summary[:500]

        from services.panopticon_service import get_make_bitcoin_case
        result = get_make_bitcoin_case(event_summary)
        return jsonify(result)
    except Exception as e:
        logger.error("Make Bitcoin Case API error: %s", e)
        return jsonify({"error": "Failed to generate Bitcoin case"}), 500
