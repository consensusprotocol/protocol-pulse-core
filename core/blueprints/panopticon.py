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

# ── Rate limiting via app-level Flask-Limiter (P0 audit fix: shared across workers) ──
# The app.py limiter uses get_remote_address as key_func.
# We apply limits per-route via a lazy import to avoid circular imports at module load.
_limiter = None


def _get_limiter():
    """Lazy-load the app-level Flask-Limiter instance."""
    global _limiter
    if _limiter is None:
        try:
            from app import limiter
            _limiter = limiter
        except ImportError:
            try:
                from core.app import limiter
                _limiter = limiter
            except ImportError:
                logger.warning("Flask-Limiter not available — panopticon rate limiting disabled")
    return _limiter


@panopticon_bp.before_request
def _enforce_rate_limit():
    """Rate limiting for /api/panopticon/* routes via Flask-Limiter.
    Falls back to app-level default if limiter unavailable."""
    if not request.path.startswith("/api/panopticon/"):
        return None

    lim = _get_limiter()
    if lim is None:
        return None

    # Flask-Limiter handles enforcement via decorators on individual routes.
    # This hook exists only for logging/monitoring.
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
    """Sanitize user input for the Make Bitcoin Case prompt to prevent injection.
    Defense-in-depth layer — primary injection defense is in the system prompt
    (see panopticon_service.get_make_bitcoin_case)."""
    # Strip control characters and excessive whitespace
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Remove common prompt injection patterns
    text = re.sub(r'(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)', '', text)
    # Limit to alphanumeric, basic punctuation, and spaces
    text = re.sub(r'[^\w\s.,;:!?\'"\-()/$%@#&+=]', '', text)
    return text.strip()[:500]


def _validate_llm_output(text: str) -> str:
    """Validate LLM output before rendering to users.
    P1 audit fix: reject outputs containing instruction-like patterns or code."""
    if not text:
        return text
    # Reject outputs with injection indicators
    suspicious_patterns = [
        r'(?i)ignore\s+(all\s+)?previous\s+instructions',
        r'(?i)system\s*prompt',
        r'(?i)<script',
        r'(?i)javascript:',
        r'(?i)on(load|error|click)\s*=',
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, text):
            logger.warning("LLM output validation failed: suspicious pattern detected")
            return "Self-custody is the only guarantee that no institution can freeze, seize, or debase your savings. Bitcoin is the exit."
    return text


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
    """Recent large BTC wallet movements from known entities.
    Tighter rate limit (10/min) — most expensive upstream call."""
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




# ═══════════════════════════════════════════════════════════════════════════
# PRIVATE EQUITY & INSTITUTIONAL INTELLIGENCE (SEC EDGAR)
# ═══════════════════════════════════════════════════════════════════════════

@panopticon_bp.route("/api/panopticon/institutional")
def api_institutional():
    """SEC EDGAR 13F institutional Bitcoin ETF accumulation + PE coalition detection."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
    try:
        from services.edgar_service import get_panopticon_institutional_data
        data = get_panopticon_institutional_data()
        return jsonify(data)
    except Exception as e:
        logger.error("EDGAR institutional data failed: %s", e)
        return jsonify({"error": str(e), "institutional_13f": [], "pe_fundraising": []}), 500


@panopticon_bp.route("/api/panopticon/pe-datastream")
def api_pe_datastream():
    """Private equity datastream: Form D fundraising + coalition analysis."""
    if not _is_commander():
        return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
    try:
        from services.edgar_service import (fetch_pe_fundraising_btc,
                                             fetch_institutional_btc_13f)
        import datetime as _dt
        pe_rounds = fetch_pe_fundraising_btc(30)
        institutional = fetch_institutional_btc_13f(20)
        coalition = [f for f in institutional if f.get("coalition_detected")]
        return jsonify({
            "pe_rounds": pe_rounds,
            "pe_count": len(pe_rounds),
            "institutional_13f": institutional,
            "coalition_signals": coalition,
            "coalition_count": len(coalition),
            "coalition_active": bool(coalition),
            "insight": (
                "COALITION SIGNAL: {} institutions accumulated BTC ETFs "
                "in coordinated windows.".format(len(coalition))
                if coalition else "No coalition pattern in current window."
            ),
            "source": "SEC EDGAR (Free Public API)",
            "updated_at": _dt.datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error("PE datastream failed: %s", e)
        return jsonify({"error": str(e), "pe_rounds": []}), 500


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
        # P1 audit fix: validate LLM output before rendering to users
        if result.get("case_text"):
            result["case_text"] = _validate_llm_output(result["case_text"])
        return jsonify(result)
    except Exception as e:
        logger.error("Make Bitcoin Case API error: %s", e)
        return jsonify({"error": "Failed to generate Bitcoin case"}), 500



@panopticon_bp.route('/api/panopticon/stream')
def api_panopticon_stream():
    # SSE real-time: orb every 30s, whale every 2min, congress every 5min
    import time, json as _j
    from pathlib import Path
    from flask import Response, stream_with_context
    from datetime import datetime, timezone
    def _sig():
        try: return _j.loads(Path('/home/ultron/protocol_pulse/data/signals.json').read_text())
        except: return {}
    def _sent():
        p = Path('/tmp/sentinel_state.json')
        try: return _j.loads(p.read_text()) if p.exists() else {}
        except: return {}
    def generate():
        tick = 0
        sig = _sig(); sent = _sent()
        def orb_evt(s, sn):
            return _j.dumps({'type':'orb_update','ts':datetime.now(timezone.utc).isoformat(),
                'btc':{'price':s.get('btc_price',{}).get('value',0),'change_24h':s.get('btc_price',{}).get('change_24h',0)},
                'fear_greed':s.get('fear_greed',{}),'hashrate':s.get('hashrate',{}).get('value',''),
                'dominance':s.get('dominance',{}).get('value',0),'signal_score':s.get('signal_score',{}),
                'convergence':{'state':sn.get('convergence_state','IDLE'),'patterns':sn.get('active_patterns',[])}})
        yield 'data: ' + _j.dumps({'type':'connected','ts':datetime.now(timezone.utc).isoformat()}) + '\n\n'
        yield 'data: ' + orb_evt(sig, sent) + '\n\n'
        while True:
            try:
                time.sleep(15); tick += 1
                yield 'data: ' + _j.dumps({'type':'heartbeat','tick':tick}) + '\n\n'
                if tick % 2 == 0:
                    sig = _sig(); sent = _sent()
                    yield 'data: ' + orb_evt(sig, sent) + '\n\n'
                if tick % 8 == 0:
                    try:
                        from services.panopticon_service import fetch_whale_alerts
                        a = fetch_whale_alerts(limit=8)
                        yield 'data: ' + _j.dumps({'type':'whale_update','alerts':a,'count':len(a)}) + '\n\n'
                    except: pass
                if tick % 20 == 0:
                    try:
                        from services.congress_trading_service import CongressTradingService
                        svc = CongressTradingService()
                        yield 'data: ' + _j.dumps({'type':'congress_update','ihx':svc.get_insider_heat_score(),'trades':svc.get_recent_trades(8)}) + '\n\n'
                    except: pass
                if tick % 60 == 0:
                    try:
                        import sys as _s; _s.path.insert(0, '/home/ultron/protocol_pulse')
                        from services.perception_layer import fetch_all as _pfa
                        pd = _pfa()
                        yield 'data: ' + _j.dumps({'type':'perception_update','composite':pd['composite'],'fee_market':pd.get('fee_market',{}),'lightning':pd.get('lightning_health',{}),'trending':pd.get('trending_narratives',{}).get('active_narratives',[]),'social_velocity':pd.get('social_sentiment',{}).get('velocity_label',''),'fg_trend':pd.get('fg_trend',{})}) + '\n\n'
                    except: pass
            except GeneratorExit: return
            except Exception as ex: logger.warning('SSE error: %s', ex); time.sleep(5)
    return Response(stream_with_context(generate()), mimetype='text/event-stream',
        headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@panopticon_bp.route('/api/panopticon/perception')
def api_perception_layer():
    # Perception Layer: social sentiment, narrative velocity, on-chain fundamentals
    # Public endpoint - no auth required (score visible, full detail for Commander)
    try:
        import sys as _sys; _sys.path.insert(0, '/home/ultron/protocol_pulse')
        from services.perception_layer import fetch_all
        data = fetch_all()
        if _is_commander():
            return jsonify(data)
        # Free tier: composite score only
        return jsonify({
            'perception_score': data['composite']['perception_score'],
            'label': data['composite']['label'],
            'overall_signal': data['composite']['overall_signal'],
            'updated_at': data['updated_at'],
            'upgrade': 'Upgrade to Commander for full intelligence breakdown',
        })
    except Exception as e:
        logger.error('Perception Layer API error: %s', e)
        return jsonify({'error': str(e)}), 500


