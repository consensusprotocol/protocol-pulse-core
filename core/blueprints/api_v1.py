"""Protocol Pulse API v1 — inline auth, no decorator at module load time."""
import hashlib, json as _j, logging, os, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify, request, Response, stream_with_context

logger = logging.getLogger(__name__)
api_v1_bp = Blueprint("api_v1", __name__)
_DB = "/home/ultron/protocol_pulse/instance/protocol_pulse.db"

TIER_CFG = {
    "demo":      {"day":20,    "hour":5,     "signals":True,  "orb":False, "congress":False,"whale":False,"pe":False,"stream":False},
    "commander": {"day":100,   "hour":20,    "signals":True,  "orb":True,  "congress":True, "whale":True, "pe":False,"stream":False},
    "intel":     {"day":500,   "hour":100,   "signals":True,  "orb":True,  "congress":True, "whale":True, "pe":True, "stream":True},
    "sovereign": {"day":999999,"hour":999999,"signals":True,  "orb":True,  "congress":True, "whale":True, "pe":True, "stream":True},
}

def _hash(k): return hashlib.sha256(k.encode()).hexdigest()
def _token():
    a = request.headers.get("Authorization","")
    if a.startswith("Bearer "): return a[7:].strip()
    return request.args.get("api_key","").strip() or None

def _auth(ent=None):
    raw = _token()
    if not raw:
        return None, (jsonify({"error":"API key required","signup":"https://protocolpulse.io/api/keys"}), 401)
    try:
        conn = sqlite3.connect(_DB)
        row = conn.execute(
            "SELECT key_prefix,tier,subscriber_email,requests_today,requests_total,last_used_at,last_reset_at FROM api_keys WHERE key_hash=? AND active=1",
            (_hash(raw),)).fetchone()
        conn.close()
    except Exception as e:
        return None, (jsonify({"error":"DB error"}), 500)
    if not row:
        return None, (jsonify({"error":"Invalid or expired API key"}), 401)
    prefix,tier,email,rday,rtotal,lused,lreset = row
    cfg = TIER_CFG.get(tier, TIER_CFG["commander"])
    if ent and not cfg.get(ent,False):
        min_t = next((t for t in ["commander","intel","sovereign"] if TIER_CFG[t].get(ent)),None) or "sovereign"
        return None, (jsonify({"error":f"{ent} requires {min_t} tier or higher","upgrade":"https://protocolpulse.io/api/keys"}), 403)
    dlimit = cfg["day"]
    if dlimit < 999999:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        rday = 0 if (lreset or "")[:10] != today else rday
        if rday >= dlimit:
            return None, (jsonify({"error":"Rate limit exceeded","tier":tier,"limit":dlimit,"upgrade":"https://protocolpulse.io/api/keys"}), 429)
        try:
            conn = sqlite3.connect(_DB)
            if (lreset or "")[:10] != today:
                conn.execute("UPDATE api_keys SET requests_today=1,requests_total=requests_total+1,last_used_at=?,last_reset_at=? WHERE key_hash=?",(now.isoformat(),now.isoformat(),_hash(raw)))
            else:
                conn.execute("UPDATE api_keys SET requests_today=requests_today+1,requests_total=requests_total+1,last_used_at=? WHERE key_hash=?",(now.isoformat(),_hash(raw)))
            conn.commit(); conn.close()
        except Exception: pass
    return {"prefix":prefix,"tier":tier,"email":email,"rday":rday,"rtotal":rtotal,"cfg":cfg}, None

def _sig(): return _j.loads(Path("/home/ultron/protocol_pulse/data/signals.json").read_text())
def _sent():
    p = Path("/tmp/sentinel_state.json")
    return _j.loads(p.read_text()) if p.exists() else {}

# ── PUBLIC ────────────────────────────────────────────────────────────────────
@api_v1_bp.route("/api/v1/docs")
@api_v1_bp.route("/api/docs")
def api_docs():
    return jsonify({"name":"Protocol Pulse Intelligence API","version":"v1",
        "base_url":"https://protocolpulse.io/api/v1","auth":"Authorization: Bearer pp_live_xxx",
        "tiers":{"commander":{"price":"$49/mo","limits":"100 req/day"},"intel":{"price":"$149/mo","limits":"500 req/day"},"sovereign":{"price":"$499/mo","limits":"unlimited"}},
        "endpoints":[
            {"path":"/api/v1/orb/latest","tier":"commander","desc":"Matrix Orb + convergence state"},
            {"path":"/api/v1/signals/latest","tier":"commander","desc":"Full intelligence signals"},
            {"path":"/api/v1/congress/trades","tier":"commander","desc":"STOCK Act + IHX score"},
            {"path":"/api/v1/whale/alerts","tier":"commander","desc":"Live whale transactions"},
            {"path":"/api/v1/pe/datastream","tier":"intel","desc":"SEC EDGAR 13F + PE coalition"},
            {"path":"/api/v1/stream","tier":"intel","desc":"SSE real-time stream"},
            {"path":"/api/v1/keys/usage","tier":"any","desc":"Usage stats"},
            {"path":"/api/v1/keys/rotate","tier":"any","desc":"Rotate key"},
            {"path":"/api/v1/checkout","tier":"public","desc":"Start Stripe checkout"},
        ],"signup":"https://protocolpulse.io/api/keys"})

@api_v1_bp.route("/api/v1/checkout", methods=["POST"])
def api_checkout():
    d = request.get_json(silent=True) or {}
    tier,email = d.get("tier","").lower(), d.get("email","").strip()
    if not email or "@" not in email: return jsonify({"error":"Valid email required"}), 400
    if tier not in ("commander","intel","sovereign"): return jsonify({"error":"tier must be: commander | intel | sovereign"}), 400
    from services.api_key_service import create_api_checkout_session
    base = os.environ.get("PUBLIC_BASE_URL","https://protocolpulse.io")
    r = create_api_checkout_session(tier, email, f"{base}/api/keys/success", f"{base}/api/keys")
    return (jsonify(r),500) if "error" in r else jsonify(r)

@api_v1_bp.route("/api/v1/webhook/stripe", methods=["POST"])
def api_stripe_webhook():
    from services.api_key_service import handle_stripe_webhook
    r = handle_stripe_webhook(request.get_data(), request.headers.get("Stripe-Signature",""))
    return (jsonify(r),400) if "error" in r else jsonify(r)

# ── COMMANDER ─────────────────────────────────────────────────────────────────
@api_v1_bp.route("/api/v1/orb/latest")
def api_orb_latest():
    sub,err = _auth("orb")
    if err: return err
    try:
        s,sent = _sig(),_sent()
        return jsonify({"as_of":s.get("updated_at",""),
            "btc":{"price":s.get("btc_price",{}).get("value",0),"change_24h":s.get("btc_price",{}).get("change_24h",0)},
            "fear_greed":s.get("fear_greed",{}),"hashrate":s.get("hashrate",{}).get("value",""),
            "dominance":s.get("dominance",{}).get("value",0),"funding_rate":s.get("funding_rate",{}).get("annualized",0),
            "signal_score":s.get("signal_score",{}),
            "convergence":{"state":sent.get("convergence_state",sent.get("state","IDLE")),"patterns":sent.get("active_patterns",[]),"pcaf_score":sent.get("pcaf_score")},
            "source":"Protocol Pulse Matrix Orb"})
    except Exception as e: return jsonify({"error":str(e)}),500

@api_v1_bp.route("/api/v1/signals/latest")
def api_signals_latest():
    sub,err = _auth("signals")
    if err: return err
    try:
        s = _sig()
        return jsonify({"as_of":s.get("updated_at",""),"btc_price":s.get("btc_price",{}),"fear_greed":s.get("fear_greed",{}),
            "hashrate":s.get("hashrate",{}),"dominance":s.get("dominance",{}),"funding_rate":s.get("funding_rate",{}),
            "open_interest":s.get("open_interest",{}),"difficulty_adjustment":s.get("difficulty_adjustment",{}),
            "sp500":s.get("sp500",{}),"gold":s.get("gold",{}),"dxy":s.get("dxy",{}),"signal_score":s.get("signal_score",{}),
            "source":"Protocol Pulse Intelligence"})
    except Exception as e: return jsonify({"error":str(e)}),500

@api_v1_bp.route("/api/v1/congress/trades")
def api_congress_trades():
    sub,err = _auth("congress")
    if err: return err
    try:
        from services.congress_trading_service import CongressTradingService
        svc = CongressTradingService()
        limit = min(int(request.args.get("limit",20)),100)
        return jsonify({"trades":svc.get_recent_trades(limit),"ihx":svc.get_insider_heat_score(),
            "source":"STOCK Act / Public Financial Disclosures","as_of":datetime.now(timezone.utc).isoformat()})
    except Exception as e: return jsonify({"error":str(e)}),500

@api_v1_bp.route("/api/v1/whale/alerts")
def api_whale_alerts():
    sub,err = _auth("whale")
    if err: return err
    try:
        from services.panopticon_service import fetch_whale_alerts
        a = fetch_whale_alerts(limit=min(int(request.args.get("limit",20)),100))
        return jsonify({"alerts":a,"count":len(a),"source":"mempool.space","as_of":datetime.now(timezone.utc).isoformat()})
    except Exception as e: return jsonify({"error":str(e)}),500

# ── INTEL ─────────────────────────────────────────────────────────────────────
@api_v1_bp.route("/api/v1/pe/datastream")
def api_pe_datastream():
    sub,err = _auth("pe")
    if err: return err
    try:
        from services.edgar_service import get_panopticon_institutional_data
        return jsonify(get_panopticon_institutional_data())
    except Exception as e: return jsonify({"error":str(e)}),500

@api_v1_bp.route("/api/v1/stream")
def api_stream():
    sub,err = _auth("stream")
    if err: return err
    def gen():
        while True:
            try:
                s,sent = _sig(),_sent()
                yield f"data: {_j.dumps({'ts':datetime.now(timezone.utc).isoformat(),'btc_price':s.get('btc_price',{}).get('value',0),'convergence_state':sent.get('convergence_state','IDLE'),'fear_greed':s.get('fear_greed',{}).get('value',0),'signal_score':s.get('signal_score',{})})}\n\n"
                time.sleep(30)
            except GeneratorExit: return
            except Exception: time.sleep(10)
    return Response(stream_with_context(gen()),mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

# ── KEY MANAGEMENT ────────────────────────────────────────────────────────────
@api_v1_bp.route("/api/v1/keys/usage")
def api_key_usage():
    sub,err = _auth()
    if err: return err
    return jsonify({"prefix":sub["prefix"],"tier":sub["tier"],"requests_today":sub["rday"],
        "requests_total":sub["rtotal"],"rate_limit_day":sub["cfg"]["day"],"rate_limit_hour":sub["cfg"]["hour"]})

@api_v1_bp.route("/api/v1/keys/rotate", methods=["POST"])
def api_key_rotate():
    sub,err = _auth()
    if err: return err
    from services.api_key_service import create_subscriber_key
    r = create_subscriber_key(sub["email"],sub["tier"])
    if not r.get("success"): return jsonify({"error":r.get("error")}),500
    return jsonify({"api_key":r["api_key"],"prefix":r["prefix"],"tier":r["tier"],
        "note":"Previous key invalid. Store this key — shown once only."})


@api_v1_bp.route("/api/keys/success")
def api_key_success():
    from flask import render_template, session
    session_id = request.args.get("session_id","")
    # Look up the subscriber from the Stripe session
    api_key = session.get("new_api_key","")
    tier = session.get("new_api_tier","commander")
    if not api_key:
        # Try to pull from DB via session_id
        try:
            conn = sqlite3.connect(_DB)
            row = conn.execute(
                "SELECT api_key, tier FROM api_subscribers WHERE stripe_session_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1",
                (session_id,)).fetchone()
            conn.close()
            if row:
                api_key, tier = row
        except Exception:
            pass
    if not api_key:
        return render_template("api_key_success.html",
            api_key="Check your email for your API key.",
            tier=tier, limits="See email", features=["API key sent to your email"])
    TIER_FEATURES = {
        "commander": ["100 req/day","Signals endpoint","Congress trades","Whale alerts","Matrix Orb","IHX score"],
        "intel":     ["500 req/day","All Commander features","PE datastream","Institutional 13F","Coalition detection","Real-time stream"],
        "sovereign": ["Unlimited requests","All Intel features","Webhook delivery","Slack alerts","MCP access","Priority support"],
    }
    TIER_LIMITS = {"commander":"100 req/day", "intel":"500 req/day", "sovereign":"Unlimited"}
    return render_template("api_key_success.html",
        api_key=api_key,
        tier=tier,
        limits=TIER_LIMITS.get(tier,"100 req/day"),
        features=TIER_FEATURES.get(tier, TIER_FEATURES["commander"]))

@api_v1_bp.route("/api/keys")
def api_keys_page():
    from flask import render_template
    from services.api_key_service import TIER_CONFIG
    import os
    return render_template("api_keys_landing.html",
        tiers={"commander":{"price":"$49","limits":"100 req/day","price_id":os.environ.get("STRIPE_PRICE_COMMANDER","")},
               "intel":{"price":"$149","limits":"500 req/day","price_id":os.environ.get("STRIPE_PRICE_INTEL","")},
               "sovereign":{"price":"$499","limits":"Unlimited","price_id":os.environ.get("STRIPE_PRICE_SOVEREIGN","")}})


@api_v1_bp.route('/api/v1/perception')
def api_v1_perception():
    sub, err = _auth('pe')  # Intel tier required for full data
    if err: return err
    try:
        import sys as _sys; _sys.path.insert(0, '/home/ultron/protocol_pulse')
        from services.perception_layer import fetch_all
        return jsonify(fetch_all())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
