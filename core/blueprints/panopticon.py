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

# ─── TTL cache helper (module-local; mirror of core.routes_api._ttl_cache) ───
import functools as _functools
import time as _time
def _ttl_cache(seconds):
    def decorator(fn):
        _store = {}
        @_functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = _time.monotonic()
            if key in _store:
                result, ts = _store[key]
                if now - ts < seconds:
                    return result
            result = fn(*args, **kwargs)
            _store[key] = (result, now)
            return result
        return wrapper
    return decorator



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
        {"headline": "US Strategic Bitcoin Reserve — Executive Order Establishes National BTC Stockpile", "category": "policy", "btc_signal": "bullish", "btc_rationale": "Nation-state accumulation confirms Bitcoin as strategic reserve asset alongside gold.", "source": "White House", "timestamp": "2025-03-06", "event_type": "geopolitical"},
        {"headline": "Japan Yen Under Pressure — BOJ Intervention Watch Activated", "category": "macro", "btc_signal": "bullish", "btc_rationale": "Currency debasement historically drives capital to hard assets. BTC +12% avg 30d post yen interventions.", "source": "Reuters", "timestamp": "2026-04-13", "event_type": "geopolitical"},
        {"headline": "EU MiCA Regulation — Full Crypto Asset Framework Active", "category": "regulation", "btc_signal": "neutral", "btc_rationale": "Regulatory clarity in EU; may push innovation to permissive jurisdictions.", "source": "European Commission", "timestamp": "2025-12-30", "event_type": "geopolitical"},
        {"headline": "Fed Holds Rates April 2026 — 98.2% Polymarket Probability", "category": "macro", "btc_signal": "bullish", "btc_rationale": "Stable rates remove macro tail risk — historically bullish for Bitcoin.", "source": "Federal Reserve", "timestamp": "2026-04-15", "event_type": "geopolitical"},
    ],
    "correlations": [],
    "watch_list": [],
    "polymarket": [
        {"question": "Will there be no change in Fed interest rates after the April 2026 meeting?", "yes_price": 98.2, "volume": 16185557, "volume_24h": 528612, "btc_signal": "bullish", "end_date": "2026-04-29", "source_url": "https://polymarket.com/event/fed-rate-april-2026", "event_type": "prediction"},
        {"question": "Will Trump acquire Greenland before 2027?", "yes_price": 9.0, "volume": 32493787, "volume_24h": 351955, "btc_signal": "neutral", "end_date": "2026-12-31", "source_url": "https://polymarket.com/event/trump-greenland", "event_type": "prediction"},
        {"question": "Will the Fed decrease rates by 50+ bps after April 2026?", "yes_price": 0.4, "volume": 26993351, "volume_24h": 1254576, "btc_signal": "bullish", "end_date": "2026-04-29", "source_url": "https://polymarket.com/event/fed-50bps-cut", "event_type": "prediction"},
        {"question": "Russia x Ukraine ceasefire by end of 2026?", "yes_price": 29.5, "volume": 14068338, "volume_24h": 163912, "btc_signal": "neutral", "end_date": "2026-12-31", "source_url": "https://polymarket.com/event/russia-ukraine-ceasefire-2026", "event_type": "prediction"},
        {"question": "Will Trump visit China by April 30?", "yes_price": 1.4, "volume": 10568303, "volume_24h": 300536, "btc_signal": "neutral", "end_date": "2026-04-30", "source_url": "https://polymarket.com/event/trump-china-april-2026", "event_type": "prediction"},
        {"question": "Iran x Israel/US conflict ends by April 15?", "yes_price": 53.4, "volume": 7822474, "volume_24h": 620212, "btc_signal": "neutral", "end_date": "2026-04-15", "source_url": "https://polymarket.com/event/iran-conflict-april-2026", "event_type": "prediction"},
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
        is_commander=(not demo_mode),
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


@_ttl_cache(300)
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


@_ttl_cache(300)
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
    """SEC EDGAR 13F institutional Bitcoin ETF holdings.
    Public: entity names + institution type. Commander: full detail with shares/values."""
    try:
        import importlib.util as _ilu
        _s = _ilu.spec_from_file_location('edgar_service',
            '/home/ultron/protocol_pulse/services/edgar_service.py')
        _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
        institutional = _m.fetch_institutional_btc_13f(20)
        coalition = [f for f in institutional if f.get("coalition_detected")]

        def _public_inst(r):
            return {
                "entity": r.get("entity", ""),
                "institution_type": r.get("institution_type", ""),
                "filing_date": r.get("filing_date", ""),
                "ticker": r.get("ticker", ""),
                "coalition_detected": r.get("coalition_detected", False),
                "coalition_score": r.get("coalition_score", 0),
            }

        is_cmd = _is_commander()
        return jsonify({
            "institutional_13f": institutional if is_cmd else [_public_inst(f) for f in institutional[:8]],
            "total_institutional_filers": len(institutional),
            "coalition_summary": {
                "detected": bool(coalition),
                "count": len(coalition),
                "active_months": {}
            },
            "commander_only": not is_cmd,
            "source": "SEC EDGAR (Free Public API)",
        })
    except Exception as e:
        logger.error("EDGAR institutional data failed: %s", e)
        return jsonify({"error": str(e), "institutional_13f": [], "total_institutional_filers": 0}), 500


@_ttl_cache(300)
@panopticon_bp.route("/api/panopticon/pe-datastream")
def api_pe_datastream():
    """Private equity datastream: Form D fundraising + coalition analysis.
    Public: counts + entity names only. Commander: full detail with amounts."""
    try:
        import importlib.util as _ilu
        _s = _ilu.spec_from_file_location('edgar_service',
            '/home/ultron/protocol_pulse/services/edgar_service.py')
        _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
        fetch_pe_fundraising_btc = _m.fetch_pe_fundraising_btc
        fetch_institutional_btc_13f = _m.fetch_institutional_btc_13f
        import datetime as _dt
        pe_rounds = fetch_pe_fundraising_btc(30)
        institutional = fetch_institutional_btc_13f(20)
        coalition = [f for f in institutional if f.get("coalition_detected")]
        # Strip amounts for public view, full detail for Commander
        def _public_round(r):
            return {"entity": r.get("entity",""), "form": r.get("form",""),
                    "filing_date": r.get("filing_date",""), "sector": r.get("sector","")}
        def _public_inst(r):
            return {"entity": r.get("entity",""), "institution_type": r.get("institution_type",""),
                    "filing_date": r.get("filing_date",""), "ticker": r.get("ticker","")}

        is_cmd = _is_commander()
        return jsonify({
            "pe_rounds": pe_rounds if is_cmd else [_public_round(r) for r in pe_rounds[:5]],
            "pe_count": len(pe_rounds),
            "institutional_13f": institutional if is_cmd else [_public_inst(r) for r in institutional[:5]],
            "coalition_signals": coalition if is_cmd else [],
            "coalition_count": len(coalition),
            "coalition_active": bool(coalition),
            "insight": (
                "COALITION SIGNAL: {} institutions accumulated BTC ETFs "
                "in coordinated windows.".format(len(coalition))
                if coalition else "No coalition pattern detected."
            ),
            "commander_only": not is_cmd,
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
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location('perception_layer',
            '/home/ultron/protocol_pulse/services/perception_layer.py')
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        data = _mod.fetch_all()
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




@_ttl_cache(300)
@panopticon_bp.route('/api/panopticon/bills')
def api_bills():
    # Bitcoin Bill Gap Tracker - public endpoint
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location('bill_tracker',
            '/home/ultron/protocol_pulse/services/bill_tracker.py')
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        data = _mod.fetch_all_bills()
        # Filter to Bitcoin-relevant bills only for public view
        btc_bills = [b for b in data.get('bills',[]) if
            any(c in b.get('categories',[]) for c in
                ['strategic_reserve','stablecoin','cbdc','market_structure','self_custody','mining','taxation'])]
        data['bills'] = btc_bills[:20]
        data['total_bills'] = len(btc_bills)
        return jsonify(data)
    except Exception as e:
        logger.error('Bill tracker API error: %s', e)
        return jsonify({'error': str(e), 'bills': []}), 500


@panopticon_bp.route('/api/panopticon/bills/vote', methods=['POST'])
def api_bills_vote():
    # Record a public vote on a bill
    d = request.get_json(silent=True) or {}
    bill_id = d.get('bill_id')
    bill_number = d.get('bill_number', '')
    vote = d.get('vote', '').lower()
    if not bill_id or vote not in ('yes', 'no'):
        return jsonify({'error': 'bill_id and vote (yes/no) required'}), 400
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location('bill_tracker',
            '/home/ultron/protocol_pulse/services/bill_tracker.py')
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        result = _mod.cast_public_vote(int(bill_id), bill_number, vote)
        return jsonify({'success': True, 'votes': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
