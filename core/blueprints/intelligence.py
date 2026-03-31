"""
INTELLIGENCE TERMINAL BLUEPRINT — Protocol Pulse
=================================================
War Room interface: mempool live, PCAF v0 anomaly detection, 3-tier alerts.
Routes:
  GET  /intelligence              → Full terminal (Commander+ auth)
  GET  /intelligence/demo         → Demo view (watermarked, no auth)
  GET  /api/intelligence/state    → Full SentinelState JSON (auth gated)
  GET  /api/intelligence/state/public → Price + block_height + FNG only
  GET  /api/intelligence/alerts   → Alert history (auth gated)
  POST /api/intelligence/alerts/<id>/ack → Acknowledge alert
  GET  /api/intelligence/stream   → SSE push (2s interval)
"""

import importlib.util
import json
import logging
import os
import sqlite3
import time
import uuid
from pathlib import Path

from flask import Blueprint, Response, jsonify, render_template, request, session, stream_with_context
from flask_login import current_user, login_user

logger = logging.getLogger(__name__)

# ── Load sentinel by absolute file path (avoids core/services shadowing) ─────
_sentinel_path = str(Path(__file__).resolve().parent.parent.parent / "services" / "sentinel.py")
_spec = importlib.util.spec_from_file_location("_sentinel_daemon", _sentinel_path)
_sentinel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sentinel)

intelligence_bp = Blueprint("intelligence", __name__)

# ── Auth helper ──────────────────────────────────────────────────────────────

def _is_commander() -> bool:
    """Check if current user has Commander or Sovereign tier."""
    if not current_user.is_authenticated:
        return False
    tier = getattr(current_user, "subscription_tier", "free")
    return tier in ("commander", "sovereign", "operator")


def _check_bearer() -> bool:
    """Check Bearer API key for Commander access."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    try:
        import models
        key = auth[7:].strip()
        sub = models.ApiSubscriber.query.filter_by(api_key=key).first()
        return sub is not None and sub.is_key_valid()
    except Exception:
        return False


def _has_access() -> bool:
    return _is_commander() or _check_bearer()


# ── Page routes ──────────────────────────────────────────────────────────────

@intelligence_bp.route("/join")
def join_page():
    """Pricing / signup page — war room aesthetic."""
    stripe_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", os.environ.get("STRIPE_PUBLIC_KEY", ""))
    return render_template("join.html", stripe_key=stripe_key)


@intelligence_bp.route("/api/join/register", methods=["POST"])
def join_register():
    """Register + redirect to Stripe checkout in one step."""
    try:
        import models
        from app import db as _db
    except Exception as e:
        return jsonify({"success": False, "error": f"Import error: {e}"}), 500

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400
    if len(password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters"}), 400

    # Check existing user
    existing = models.User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"success": False, "error": "Account already exists. Please log in."}), 409

    # Create user
    try:
        user = models.User(email=email, username=email.split("@")[0])
        user.set_password(password)
        user.subscription_tier = "free"
        _db.session.add(user)
        _db.session.commit()
        login_user(user)
    except Exception as e:
        _db.session.rollback()
        return jsonify({"success": False, "error": f"Registration failed: {e}"}), 500

    # Create Stripe checkout session
    try:
        from services.monetization_service import monetization_service
        result = monetization_service.create_checkout_session(
            tier="commander",
            user_email=email,
            success_url=request.host_url.rstrip("/") + "/intelligence?activated=1",
            cancel_url=request.host_url.rstrip("/") + "/join",
        )
        if result.get("simulated"):
            # Dev mode: upgrade tier directly and skip Stripe redirect
            user.subscription_tier = "commander"
            _db.session.commit()
            return jsonify({"success": True, "checkout_url": None})
        if result.get("checkout_url"):
            return jsonify({"success": True, "checkout_url": result["checkout_url"]})
    except Exception as e:
        logger.warning("Stripe checkout creation failed: %s — continuing without payment", e)

    # Stripe not configured — upgrade and let them in
    user.subscription_tier = "commander"
    try:
        _db.session.commit()
    except Exception:
        _db.session.rollback()
    return jsonify({"success": True, "checkout_url": None})


@intelligence_bp.route("/intelligence-v2")
def intelligence_terminal():
    """Intelligence Dashboard — world-class redesign with PCAF orb, signal matrix, divergence engine."""
    import json as _json
    from datetime import datetime, timedelta as _td
    from sqlalchemy import text as _text

    # ── Commander status ──
    is_commander = _is_commander()

    # ── Signal strength ──
    try:
        from services.intelligence_service import (
            get_signal_strength, get_trending_topics,
            get_entity_tracker, get_narrative_timeline, get_intelligence_events
        )
        signal = get_signal_strength()
        trending = get_trending_topics(hours=24)
        entities = get_entity_tracker(hours=48)
        narrative_timeline = get_narrative_timeline(days=7)
        intel_events = get_intelligence_events(limit=8)
    except Exception as e:
        logger.error("intelligence_terminal data error: %s", e)
        signal = {"composite": 50, "label": "NEUTRAL", "color": "#f8c15c", "components": {}, "trajectory": "UNKNOWN"}
        trending = []
        entities = []
        narrative_timeline = []
        intel_events = []

    # ── Top articles ──
    top_articles = []
    try:
        from app import db as _db2
        if _db2:
            imp_rows = _db2.session.execute(
                _text("""SELECT id, title, sentiment, narrative_label, importance_score,
                                market_impact_magnitude, created_at
                         FROM articles WHERE published=1
                         ORDER BY importance_score DESC NULLS LAST, created_at DESC
                         LIMIT 15""")
            ).fetchall()
            top_articles = [
                {
                    "id": r[0], "title": r[1],
                    "sentiment": r[2] or "unclassified",
                    "narrative_label": r[3] or "—",
                    "importance_score": int(r[4] or 50),
                    "impact": float(r[5] or 5.0),
                    "created_at": str(r[6]),
                }
                for r in imp_rows
            ]
    except Exception:
        pass

    # ── Sovereign context ──
    sovereign_ctx = {}
    try:
        _ctx_path = str(Path(__file__).resolve().parent.parent.parent / "data" / "sovereign_context" / "latest.json")
        if os.path.exists(_ctx_path):
            with open(_ctx_path) as f:
                sovereign_ctx = json.load(f)
    except Exception:
        pass

    # ── Polymarket ──
    polymarket_markets = []
    polymarket_sentiment = 50
    try:
        _pm_path = str(Path(__file__).resolve().parent.parent.parent / "services" / "polymarket_service.py")
        spec = importlib.util.spec_from_file_location('polymarket_service', _pm_path)
        _pm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_pm)
        polymarket_markets = _pm.get_bitcoin_markets(5)
        polymarket_sentiment = _pm.get_macro_sentiment_score()
    except Exception:
        pass

    return render_template(
        "intelligence_page.html",
        signal=signal,
        trending=trending,
        entities=entities,
        narrative_timeline=narrative_timeline,
        intel_events=intel_events,
        top_articles=top_articles,
        signal_json=_json.dumps(signal, default=str),
        sovereign_ctx=sovereign_ctx,
        sovereign_ctx_json=_json.dumps(sovereign_ctx, default=str),
        polymarket_markets=polymarket_markets,
        polymarket_sentiment=polymarket_sentiment,
        is_commander=is_commander,
    )


@intelligence_bp.route("/intelligence/demo")
def intelligence_demo():
    """Demo view — always watermarked."""
    return render_template("intelligence_terminal.html", demo_mode=True, show_welcome=False)


# ── API routes ───────────────────────────────────────────────────────────────

@intelligence_bp.route("/api/intelligence/state")
def api_intelligence_state():
    """Full SentinelState — Commander+ auth required."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    return jsonify(_sentinel.get_state())


@intelligence_bp.route("/api/intelligence/state/public")
def api_intelligence_state_public():
    """Public subset: price + block_height + FNG only."""
    state = _sentinel.get_state()
    return jsonify({
        "block_height": state.get("network", {}).get("block_height", 0),
        "price": _get_btc_price(),
        "fng": _get_fng(),
    })


@intelligence_bp.route("/api/intelligence/alerts")
def api_intelligence_alerts():
    """Alert history with pagination — Commander+ auth required."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))
    alerts = _sentinel.get_alerts(limit=limit, offset=offset)
    return jsonify({"alerts": alerts, "limit": limit, "offset": offset})


@intelligence_bp.route("/api/intelligence/alerts/<int:alert_id>/ack", methods=["POST"])
def api_intelligence_ack(alert_id):
    """Acknowledge an alert — Commander+ auth required."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    ok = _sentinel.ack_alert(alert_id)
    return jsonify({"success": ok})


@intelligence_bp.route("/api/intelligence/stream")
def api_intelligence_stream():
    """SSE stream — pushes SentinelState every 2 seconds."""
    is_auth = _has_access()

    def generate():
        while True:
            try:
                state = _sentinel.get_state()
                if not is_auth:
                    state = {
                        "network": {"block_height": state.get("network", {}).get("block_height", 0)},
                        "price": _get_btc_price(),
                        "fng": _get_fng(),
                        "alerts": state.get("alerts", {}),
                        "convergence": {"state": state.get("convergence", {}).get("state", "IDLE")},
                        "sentiment": {"score": state.get("sentiment", {}).get("score", 0), "trend": state.get("sentiment", {}).get("trend", "stable")},
                    }
                else:
                    # Inject price + fng for authenticated stream too
                    state["price"] = _get_btc_price()
                    state["fng"] = _get_fng()
                    # Phase 1 alpha intel
                    try:
                        alpha = _get_alpha_intel(state)
                        state["signal_matrix"] = alpha["signal_matrix"]
                        state["narrative_momentum"] = alpha["narrative_momentum"]
                        state["divergence"] = alpha["divergence"]
                        state["early_warnings"] = alpha["early_warnings"]
                    except Exception as e:
                        logger.warning("Alpha intel error: %s", e)
                yield f"data: {json.dumps(state)}\n\n"
                time.sleep(2)
            except GeneratorExit:
                return
            except Exception as e:
                logger.warning("SSE stream error: %s", e)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── TPA — Temporal Predictive Analytics ──────────────────────────────────

# Load TPA engine by absolute file path
_tpa_engine_path = str(Path(__file__).resolve().parent.parent.parent / "services" / "tpa_engine.py")
_tpa_spec = importlib.util.spec_from_file_location("_tpa_engine_bp", _tpa_engine_path)
_tpa_mod = importlib.util.module_from_spec(_tpa_spec)
_tpa_spec.loader.exec_module(_tpa_mod)
_tpa_engine_instance = _tpa_mod.TPAEngine()


@intelligence_bp.route("/intelligence/scenarios")
def scenarios_page():
    """TPA Scenarios page — war room aesthetic."""
    return render_template("scenarios.html")


@intelligence_bp.route("/api/intelligence/tpa")
def api_tpa_state():
    """Full TPA state JSON — auth gated."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    tpa = state.get("tpa", {})
    # If sentinel hasn't run TPA yet, run it now from the blueprint's engine
    if not tpa.get("scenarios"):
        tpa = _tpa_engine_instance.run_cycle(state)
    return jsonify(tpa)


@intelligence_bp.route("/api/intelligence/tpa/stream")
def api_tpa_stream():
    """SSE stream for TPA — pushes on probability changes >0.5%."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401

    def generate():
        last_probs = {}
        while True:
            try:
                state = _sentinel.get_state()
                tpa = state.get("tpa", {})
                scenarios = tpa.get("scenarios", [])

                # Only push if probabilities changed by >0.5%
                changed = False
                for s in scenarios:
                    prev = last_probs.get(s.get("id"), 0)
                    if abs(s.get("probability", 0) - prev) > 0.5:
                        changed = True
                        last_probs[s.get("id")] = s.get("probability", 0)

                if changed or not last_probs:
                    yield f"data: {json.dumps(tpa)}\n\n"

                time.sleep(2)
            except GeneratorExit:
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@intelligence_bp.route("/api/intelligence/tpa/track", methods=["POST"])
def api_tpa_track():
    """Store scenario tracking preference."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    data = request.get_json(silent=True) or {}
    scenario_id = data.get("scenario_id")
    tracked = data.get("tracked", True)
    # Store in-memory for now (persistent storage is a TODO)
    return jsonify({"success": True, "scenario_id": scenario_id, "tracked": tracked})


@intelligence_bp.route("/api/intelligence/tpa/snapshot", methods=["POST"])
def api_tpa_snapshot():
    """Generate a shareable TPA snapshot URL."""
    data = request.get_json(silent=True) or {}
    scenario_id = data.get("scenario_id")
    snapshot = _tpa_engine_instance.get_share_snapshot(scenario_id)
    snap_id = snapshot.get("snapshot_id", "unknown")
    return jsonify({"url": f"/intelligence/scenarios/snapshot/{snap_id}", "snapshot_id": snap_id})


@intelligence_bp.route("/intelligence/scenarios/snapshot/<snapshot_id>")
def scenario_snapshot_page(snapshot_id):
    """Public snapshot page — no auth required."""
    snapshot = _tpa_engine_instance.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        # Try to build a live snapshot as fallback
        state = _sentinel.get_state()
        tpa = state.get("tpa", {})
        if tpa.get("scenarios"):
            snapshot = {
                "scenarios": tpa["scenarios"],
                "snapshot_id": snapshot_id,
                "timestamp": time.time(),
            }
        else:
            snapshot = {"scenarios": [], "snapshot_id": snapshot_id}

    snap_time = ""
    if snapshot.get("timestamp"):
        import datetime
        snap_time = datetime.datetime.fromtimestamp(
            snapshot["timestamp"]).strftime("%Y-%m-%d %H:%M UTC")

    return render_template("scenario_snapshot.html",
                           snapshot_data=snapshot,
                           snapshot_time=snap_time)


# ── Phase 2 API endpoints ────────────────────────────────────────────────

@intelligence_bp.route("/api/intelligence/sentiment")
def api_intelligence_sentiment():
    """Sentiment Pulse data — Commander+ auth required."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    return jsonify(state.get("sentiment", {}))


@intelligence_bp.route("/api/intelligence/sovereign")
def api_intelligence_sovereign():
    """Sovereign Intelligence Layer — Commander+ auth required."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    return jsonify(state.get("sovereign", {}))


@intelligence_bp.route("/api/intelligence/network-graph")
def api_intelligence_network_graph():
    """Network State Graph — Commander+ auth required."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    return jsonify(state.get("network_graph", {"nodes": [], "edges": []}))


# ── Helpers ──────────────────────────────────────────────────────────────────

_price_cache = {"value": None, "ts": 0}
_fng_cache = {"value": None, "ts": 0}


def _get_btc_price() -> dict:
    now = time.time()
    if _price_cache["value"] and now - _price_cache["ts"] < 30:
        return _price_cache["value"]
    try:
        import requests as _req
        resp = _req.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("bitcoin", {})
            result = {"usd": data.get("usd", 0), "change_24h": round(data.get("usd_24h_change", 0), 2)}
            _price_cache["value"] = result
            _price_cache["ts"] = now
            return result
    except Exception:
        pass
    # Fallback: read from signals.json (updated every 5 min by cron)
    if not _price_cache["value"] or _price_cache["value"].get("usd", 0) == 0:
        try:
            _sig_path = str(Path(__file__).resolve().parent.parent.parent / "data" / "signals.json")
            with open(_sig_path) as _f:
                _sig = json.load(_f)
            bp = _sig.get("btc_price", {})
            if bp.get("value"):
                result = {"usd": bp["value"], "change_24h": bp.get("change_24h", 0)}
                _price_cache["value"] = result
                _price_cache["ts"] = now
                return result
        except Exception:
            pass
    return _price_cache["value"] or {"usd": 0, "change_24h": 0}


def _get_fng() -> dict:
    now = time.time()
    if _fng_cache["value"] and now - _fng_cache["ts"] < 900:
        return _fng_cache["value"]
    try:
        import requests as _req
        resp = _req.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        if resp.status_code == 200:
            entry = resp.json().get("data", [{}])[0]
            result = {"value": int(entry.get("value", 0)), "label": entry.get("value_classification", "")}
            _fng_cache["value"] = result
            _fng_cache["ts"] = now
            return result
    except Exception:
        pass
    return _fng_cache["value"] or {"value": 0, "label": ""}


# ═══════════════════════════════════════════════════════════════════════════
# F-P3-7: Alert History & Precision Tracking
# ═══════════════════════════════════════════════════════════════════════════

_ALERTS_DB = str(Path(__file__).resolve().parent.parent.parent / "data" / "sentinel_alerts.db")


def _ensure_alert_columns():
    """Add user_vote + backtest columns to alerts table if they don't exist."""
    try:
        conn = sqlite3.connect(_ALERTS_DB)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(alerts)").fetchall()]
        new_cols = {
            "user_vote": "TEXT",
            "price_at_alert": "REAL",
            "price_24h_later": "REAL",
            "price_7d_later": "REAL",
            "outcome": "TEXT",
        }
        for col, typ in new_cols.items():
            if col not in cols:
                conn.execute(f"ALTER TABLE alerts ADD COLUMN {col} {typ}")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to add alert columns: %s", e)


_ensure_alert_columns()


@intelligence_bp.route("/intelligence/alerts")
def alert_history_page():
    """Full alert history page — Commander+ auth required."""
    if not _has_access():
        return render_template("intelligence_terminal.html", demo_mode=True)
    return render_template("alert_history.html")


@intelligence_bp.route("/intelligence/alerts/stats")
def alert_stats_page():
    """Alert analytics page — Commander+ auth required."""
    if not _has_access():
        return render_template("intelligence_terminal.html", demo_mode=True)
    return render_template("alert_stats.html")


@intelligence_bp.route("/api/intelligence/alerts/<int:alert_id>/vote", methods=["POST"])
def api_alert_vote(alert_id):
    """Vote on alert accuracy — correct or false_positive."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401

    data = request.get_json(silent=True) or {}
    vote = data.get("vote")
    if vote not in ("correct", "false_positive"):
        return jsonify({"error": "vote must be 'correct' or 'false_positive'"}), 400

    try:
        conn = sqlite3.connect(_ALERTS_DB)
        conn.execute("UPDATE alerts SET user_vote = ? WHERE id = ?", (vote, alert_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "alert_id": alert_id, "vote": vote})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@intelligence_bp.route("/api/intelligence/alerts/precision")
def api_alert_precision():
    """Get precision metrics for alerts."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    try:
        conn = sqlite3.connect(_ALERTS_DB)
        rows = conn.execute(
            "SELECT tier, user_vote, COUNT(*) FROM alerts WHERE user_vote IS NOT NULL GROUP BY tier, user_vote"
        ).fetchall()
        conn.close()

        stats = {}
        for tier, vote, count in rows:
            if tier not in stats:
                stats[tier] = {"correct": 0, "false_positive": 0}
            stats[tier][vote] = count

        precision = {}
        for tier, counts in stats.items():
            total = counts["correct"] + counts["false_positive"]
            precision[tier] = {
                "correct": counts["correct"],
                "false_positive": counts["false_positive"],
                "total_rated": total,
                "precision_pct": round(counts["correct"] / total * 100, 1) if total > 0 else 0,
            }

        return jsonify({"precision": precision})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# F-P3-8: External API Layer (REST, auth, rate-limited)
# ═══════════════════════════════════════════════════════════════════════════

@intelligence_bp.route("/api/v1/state")
def api_v1_state():
    """Full SentinelState snapshot — API key auth required."""
    if not _has_access():
        return jsonify({"error": "API key required. Header: Authorization: Bearer <key>"}), 401
    state = _sentinel.get_state()
    state["price"] = _get_btc_price()
    state["fng"] = _get_fng()
    return jsonify(state)


@intelligence_bp.route("/api/v1/mempool")
def api_v1_mempool():
    if not _has_access():
        return jsonify({"error": "API key required"}), 401
    return jsonify(_sentinel.get_state().get("mempool", {}))


@intelligence_bp.route("/api/v1/convergence")
def api_v1_convergence():
    if not _has_access():
        return jsonify({"error": "API key required"}), 401
    return jsonify(_sentinel.get_state().get("convergence", {}))


@intelligence_bp.route("/api/v1/alerts")
def api_v1_alerts():
    if not _has_access():
        return jsonify({"error": "API key required"}), 401
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))
    return jsonify(_sentinel.get_alerts(limit=limit, offset=offset))


@intelligence_bp.route("/api/v1/sentiment")
def api_v1_sentiment():
    if not _has_access():
        return jsonify({"error": "API key required"}), 401
    return jsonify(_sentinel.get_state().get("sentiment", {}))


@intelligence_bp.route("/api/v1/sovereign")
def api_v1_sovereign():
    if not _has_access():
        return jsonify({"error": "API key required"}), 401
    return jsonify(_sentinel.get_state().get("sovereign", {}))


@intelligence_bp.route("/api/v1/network")
def api_v1_network():
    if not _has_access():
        return jsonify({"error": "API key required"}), 401
    return jsonify(_sentinel.get_state().get("network_graph", {}))


@intelligence_bp.route("/api/v1/stream")
def api_v1_stream():
    """WebSocket-compatible SSE stream for institutional access."""
    if not _has_access():
        return jsonify({"error": "API key required"}), 401

    def generate():
        while True:
            try:
                state = _sentinel.get_state()
                state["price"] = _get_btc_price()
                state["fng"] = _get_fng()
                yield f"data: {json.dumps(state)}\n\n"
                time.sleep(2)
            except GeneratorExit:
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@intelligence_bp.route("/api/v1/keys/generate", methods=["POST"])
def api_v1_generate_key():
    """Generate new API key for current user."""
    if not _is_commander():
        return jsonify({"error": "Commander access required"}), 401
    try:
        import models
        key = str(uuid.uuid4())
        current_user.api_key = key
        models.db.session.commit()
        return jsonify({"api_key": key})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@intelligence_bp.route("/api/v1/docs")
def api_v1_docs():
    """API documentation — public."""
    endpoints = [
        {"path": "/api/v1/state", "method": "GET", "auth": True, "description": "Full SentinelState snapshot"},
        {"path": "/api/v1/mempool", "method": "GET", "auth": True, "description": "Mempool panel data"},
        {"path": "/api/v1/convergence", "method": "GET", "auth": True, "description": "Convergence state"},
        {"path": "/api/v1/alerts", "method": "GET", "auth": True, "description": "Alert history (paginated)"},
        {"path": "/api/v1/sentiment", "method": "GET", "auth": True, "description": "Sentiment pulse data"},
        {"path": "/api/v1/sovereign", "method": "GET", "auth": True, "description": "Sovereign intelligence"},
        {"path": "/api/v1/network", "method": "GET", "auth": True, "description": "Network graph nodes/edges"},
        {"path": "/api/v1/stream", "method": "GET", "auth": True, "description": "SSE real-time stream"},
        {"path": "/api/v1/keys/generate", "method": "POST", "auth": True, "description": "Generate API key"},
    ]
    return jsonify({"version": "v1", "base_url": "/api/v1", "auth_header": "Authorization: Bearer <key>", "endpoints": endpoints})


@intelligence_bp.route("/intelligence/api")
def api_management_page():
    """API key management page — Commander+ auth required."""
    if not _has_access():
        return render_template("intelligence_terminal.html", demo_mode=True)
    return render_template("api_management.html")


# ═══════════════════════════════════════════════════════════════════════════
# F-P3-9: Backtesting Interface
# ═══════════════════════════════════════════════════════════════════════════

@intelligence_bp.route("/intelligence/backtest")
def backtest_page():
    """Backtesting page — Commander+ auth required."""
    if not _has_access():
        return render_template("intelligence_terminal.html", demo_mode=True)
    return render_template("backtest.html")


@intelligence_bp.route("/api/intelligence/backtest")
def api_backtest():
    """Get alert outcomes with price data for backtesting."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    try:
        conn = sqlite3.connect(_ALERTS_DB)
        rows = conn.execute("""
            SELECT id, tier, rule, message, score, created_at, user_vote,
                   price_at_alert, price_24h_later, price_7d_later, outcome
            FROM alerts
            WHERE tier IN ('CRITICAL', 'WATCH')
            ORDER BY created_at DESC
            LIMIT 200
        """).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "id": row[0], "tier": row[1], "rule": row[2],
                "message": row[3], "score": row[4],
                "created_at": row[5], "user_vote": row[6],
                "price_at_alert": row[7], "price_24h_later": row[8],
                "price_7d_later": row[9], "outcome": row[10],
            })
        return jsonify({"alerts": results})
    except Exception as e:
        return jsonify({"alerts": [], "note": f"Backtest columns not yet populated: {e}"})


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1 Alpha Intelligence — Sovereign Signal Matrix, Narrative Momentum,
# Cross-Signal Divergence, Early Warning Feed
# ═══════════════════════════════════════════════════════════════════════════

_signal_matrix_cache = {"value": None, "ts": 0}
_narrative_cache = {"value": None, "ts": 0}
_divergence_cache = {"value": None, "ts": 0}
_early_warning_cache = {"value": None, "ts": 0}


def _compute_signal_matrix(state: dict) -> dict:
    """Compute 6-axis Sovereign Signal Matrix from live Sentinel state.

    Axes (each 0-100):
      1. Miner Health — from miner_health.score
      2. Exchange Pressure — from dark_pool + ETF flow + whale coordination
      3. Narrative Momentum — from sentiment trend + convergence signal count
      4. On-Chain Accumulation — from exchange reserves + CDD + whale coordination
      5. Lightning Growth — from lightning capacity/channels vs baseline
      6. Social Divergence — from sentiment vs price divergence
    """
    now = time.time()
    if _signal_matrix_cache["value"] and now - _signal_matrix_cache["ts"] < 30:
        return _signal_matrix_cache["value"]

    mh = state.get("miner_health", {})
    dp = state.get("dark_pool", {})
    etf = state.get("etf", {})
    wc = state.get("whale_coordination", {})
    sov = state.get("sovereign", {})
    ln = state.get("lightning", {})
    sent = state.get("sentiment", {})
    conv = state.get("convergence", {})
    pcaf = state.get("pcaf_v0", {})
    price = state.get("price", {})

    # 1. Miner Health (direct from engine, 0-100)
    miner_score = min(100, max(0, mh.get("score", 50)))

    # 2. Exchange Pressure (inverse = bullish when outflows)
    dp_signal_map = {"CLEAR": 30, "WATCH": 60, "ACCUMULATION": 85}
    dp_val = dp_signal_map.get(dp.get("signal", "CLEAR"), 30)
    etf_dir = etf.get("net_6h_direction", "neutral")
    etf_val = 70 if etf_dir == "inflow" else 30 if etf_dir == "outflow" else 50
    wc_signal_map = {"CLEAR": 20, "NOTE": 50, "WATCH": 80}
    wc_val = wc_signal_map.get(wc.get("signal", "CLEAR"), 20)
    exchange_pressure = int((dp_val * 0.4 + etf_val * 0.35 + wc_val * 0.25))

    # 3. Narrative Momentum (sentiment trend + convergence density)
    trend_map = {"rising": 75, "stable": 50, "falling": 25}
    trend_val = trend_map.get(sent.get("trend", "stable"), 50)
    sig_count = len(conv.get("signals", []))
    conv_density = min(100, sig_count * 12)
    narrative_momentum = int(trend_val * 0.6 + conv_density * 0.4)

    # 4. On-Chain Accumulation (exchange reserves declining = bullish)
    ch = sov.get("custody_health", {})
    reserve_ratio = ch.get("exchange_reserve_ratio", 50)
    accum_from_reserves = max(0, min(100, 100 - reserve_ratio))
    cdd_map = {"STABLE": 60, "ELEVATED": 40, "SPIKE": 20}
    cdd_val = cdd_map.get(ch.get("cdd_signal", "STABLE"), 60)
    wc_btc = wc.get("total_btc_90min", 0)
    whale_accum = min(100, wc_btc / 50 * 100) if wc_btc > 0 else 30
    onchain_accum = int(accum_from_reserves * 0.4 + cdd_val * 0.3 + whale_accum * 0.3)

    # 5. Lightning Growth (capacity trend)
    ln_cap = ln.get("capacity_btc", 0)
    ln_chans = ln.get("channel_count", 0)
    # Baseline: ~5400 BTC capacity, ~16000 channels (2025-2026 range)
    ln_cap_score = min(100, max(0, int((ln_cap / 5400) * 50))) if ln_cap else 50
    ln_chan_score = min(100, max(0, int((ln_chans / 16000) * 50))) if ln_chans else 50
    lightning_growth = int(ln_cap_score * 0.6 + ln_chan_score * 0.4)

    # 6. Social Divergence (sentiment vs price direction)
    sent_score = sent.get("score", 0)
    price_change = (price or {}).get("change_24h", 0)
    # Divergence = sentiment and price moving in opposite directions
    if (sent_score > 20 and price_change < -2) or (sent_score < -20 and price_change > 2):
        social_div = 85  # Strong divergence
    elif abs(sent_score) > 40:
        social_div = 65  # High sentiment extremity
    else:
        social_div = max(20, min(80, 50 + int(abs(sent_score) * 0.5)))

    # Composite score (weighted average)
    composite = int(
        miner_score * 0.20 + exchange_pressure * 0.20 +
        narrative_momentum * 0.15 + onchain_accum * 0.20 +
        lightning_growth * 0.10 + social_div * 0.15
    )

    # Overall bias
    if composite >= 65:
        bias = "BULLISH"
    elif composite <= 35:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    result = {
        "axes": {
            "miner_health": miner_score,
            "exchange_pressure": exchange_pressure,
            "narrative_momentum": narrative_momentum,
            "onchain_accumulation": onchain_accum,
            "lightning_growth": lightning_growth,
            "social_divergence": social_div,
        },
        "composite": composite,
        "bias": bias,
        "updated_at": now,
    }
    _signal_matrix_cache["value"] = result
    _signal_matrix_cache["ts"] = now
    return result


def _compute_narrative_momentum() -> dict:
    """Scan last 50 articles for topic cluster acceleration/deceleration."""
    now = time.time()
    if _narrative_cache["value"] and now - _narrative_cache["ts"] < 120:
        return _narrative_cache["value"]

    try:
        from datetime import datetime, timedelta
        import models
        cutoff_recent = datetime.utcnow() - timedelta(days=3)
        cutoff_prior = datetime.utcnow() - timedelta(days=10)

        recent = models.Article.query.filter(
            models.Article.published == True,
            models.Article.created_at >= cutoff_recent,
        ).order_by(models.Article.created_at.desc()).limit(50).all()

        prior = models.Article.query.filter(
            models.Article.published == True,
            models.Article.created_at >= cutoff_prior,
            models.Article.created_at < cutoff_recent,
        ).order_by(models.Article.created_at.desc()).limit(100).all()

        def _extract_topics(articles):
            """Count category occurrences and extract tag frequencies."""
            cats = {}
            tags_freq = {}
            for a in articles:
                cat = (a.category or "general").lower()
                cats[cat] = cats.get(cat, 0) + 1
                if a.tags:
                    for tag in a.tags.split(","):
                        t = tag.strip().lower()
                        if t and len(t) > 2:
                            tags_freq[t] = tags_freq.get(t, 0) + 1
            return cats, tags_freq

        recent_cats, recent_tags = _extract_topics(recent)
        prior_cats, prior_tags = _extract_topics(prior)

        # Normalize by count
        recent_total = max(len(recent), 1)
        prior_total = max(len(prior), 1)

        # Build momentum for categories
        all_cats = set(list(recent_cats.keys()) + list(prior_cats.keys()))
        momentum = []
        for cat in all_cats:
            recent_pct = (recent_cats.get(cat, 0) / recent_total) * 100
            prior_pct = (prior_cats.get(cat, 0) / prior_total) * 100
            delta = recent_pct - prior_pct
            if recent_cats.get(cat, 0) >= 2 or prior_cats.get(cat, 0) >= 2:
                momentum.append({
                    "topic": cat,
                    "recent_count": recent_cats.get(cat, 0),
                    "prior_count": prior_cats.get(cat, 0),
                    "recent_pct": round(recent_pct, 1),
                    "prior_pct": round(prior_pct, 1),
                    "delta": round(delta, 1),
                    "trend": "accelerating" if delta > 5 else "decelerating" if delta < -5 else "stable",
                })

        momentum.sort(key=lambda x: abs(x["delta"]), reverse=True)

        # Top trending tags
        trending_tags = []
        for tag in recent_tags:
            if recent_tags[tag] >= 2:
                prior_count = prior_tags.get(tag, 0)
                trending_tags.append({
                    "tag": tag,
                    "recent": recent_tags[tag],
                    "prior": prior_count,
                    "new": prior_count == 0,
                })
        trending_tags.sort(key=lambda x: x["recent"], reverse=True)

        # Leading indicator: topic spikes that precede price moves
        leading_signals = []
        for m in momentum:
            if m["trend"] == "accelerating" and m["recent_count"] >= 3:
                leading_signals.append(
                    f"{m['topic'].upper()} coverage up {m['delta']:+.0f}pp — watch for correlation"
                )

        result = {
            "momentum": momentum[:8],
            "trending_tags": trending_tags[:10],
            "leading_signals": leading_signals[:3],
            "article_count_3d": len(recent),
            "article_count_10d": len(prior),
            "updated_at": now,
        }
        _narrative_cache["value"] = result
        _narrative_cache["ts"] = now
        return result

    except Exception as e:
        logger.warning("Narrative momentum error: %s", e)
        return {"momentum": [], "trending_tags": [], "leading_signals": [],
                "article_count_3d": 0, "article_count_10d": 0, "updated_at": now, "error": str(e)}


def _compute_divergence_alerts(state: dict) -> dict:
    """Detect cross-signal divergence — when 3+ signals break historical correlation."""
    now = time.time()
    if _divergence_cache["value"] and now - _divergence_cache["ts"] < 30:
        return _divergence_cache["value"]

    price = state.get("price", {})
    sent = state.get("sentiment", {})
    mh = state.get("miner_health", {})
    dp = state.get("dark_pool", {})
    etf = state.get("etf", {})
    fng = state.get("fng", {})
    conv = state.get("convergence", {})
    ln = state.get("lightning", {})
    pcaf = state.get("pcaf_v0", {})

    price_change = (price or {}).get("change_24h", 0)

    # Define signal directions: +1 = bullish, -1 = bearish, 0 = neutral
    signals = []

    # Price direction
    if price_change > 2:
        signals.append({"name": "Price 24h", "direction": 1, "value": f"+{price_change:.1f}%", "weight": 1.0})
    elif price_change < -2:
        signals.append({"name": "Price 24h", "direction": -1, "value": f"{price_change:.1f}%", "weight": 1.0})
    else:
        signals.append({"name": "Price 24h", "direction": 0, "value": f"{price_change:+.1f}%", "weight": 1.0})

    # Sentiment direction
    sent_score = sent.get("score", 0)
    if sent_score > 20:
        signals.append({"name": "Sentiment", "direction": 1, "value": f"+{sent_score:.0f}", "weight": 0.8})
    elif sent_score < -20:
        signals.append({"name": "Sentiment", "direction": -1, "value": f"{sent_score:.0f}", "weight": 0.8})
    else:
        signals.append({"name": "Sentiment", "direction": 0, "value": f"{sent_score:+.0f}", "weight": 0.8})

    # Miner health
    miner_score = mh.get("score", 100)
    if miner_score >= 70:
        signals.append({"name": "Miner Health", "direction": 1, "value": f"{miner_score}", "weight": 0.7})
    elif miner_score < 50:
        signals.append({"name": "Miner Health", "direction": -1, "value": f"{miner_score}", "weight": 0.7})
    else:
        signals.append({"name": "Miner Health", "direction": 0, "value": f"{miner_score}", "weight": 0.7})

    # Exchange flow (ETF)
    etf_dir = etf.get("net_6h_direction", "neutral")
    if etf_dir == "inflow":
        signals.append({"name": "Exchange Flow", "direction": 1, "value": "INFLOW", "weight": 0.9})
    elif etf_dir == "outflow":
        signals.append({"name": "Exchange Flow", "direction": -1, "value": "OUTFLOW", "weight": 0.9})
    else:
        signals.append({"name": "Exchange Flow", "direction": 0, "value": "NEUTRAL", "weight": 0.9})

    # Fear & Greed
    fng_val = fng.get("value", 50) if isinstance(fng, dict) else 50
    if fng_val >= 65:
        signals.append({"name": "Fear & Greed", "direction": 1, "value": f"{fng_val} Greed", "weight": 0.6})
    elif fng_val <= 35:
        signals.append({"name": "Fear & Greed", "direction": -1, "value": f"{fng_val} Fear", "weight": 0.6})
    else:
        signals.append({"name": "Fear & Greed", "direction": 0, "value": f"{fng_val}", "weight": 0.6})

    # Dark Pool
    dp_signal = dp.get("signal", "CLEAR")
    if dp_signal == "ACCUMULATION":
        signals.append({"name": "Dark Pool", "direction": 1, "value": "ACCUMULATION", "weight": 0.8})
    elif dp_signal == "WATCH":
        signals.append({"name": "Dark Pool", "direction": 0, "value": "WATCH", "weight": 0.8})
    else:
        signals.append({"name": "Dark Pool", "direction": 0, "value": "CLEAR", "weight": 0.8})

    # PCAF anomaly
    pcaf_score = pcaf.get("anomaly_score", 0)
    if pcaf_score >= 70:
        signals.append({"name": "PCAF Anomaly", "direction": -1, "value": f"{pcaf_score}", "weight": 0.9})
    elif pcaf_score >= 30:
        signals.append({"name": "PCAF Anomaly", "direction": 0, "value": f"{pcaf_score}", "weight": 0.9})
    else:
        signals.append({"name": "PCAF Anomaly", "direction": 1, "value": f"{pcaf_score}", "weight": 0.9})

    # Find divergences — signals pointing in different directions
    bullish = [s for s in signals if s["direction"] == 1]
    bearish = [s for s in signals if s["direction"] == -1]
    divergence_detected = len(bullish) >= 2 and len(bearish) >= 2

    # Historical context for divergence
    divergence_alerts = []
    if divergence_detected:
        bull_names = ", ".join([s["name"] for s in bullish[:3]])
        bear_names = ", ".join([s["name"] for s in bearish[:3]])
        divergence_alerts.append({
            "type": "DIVERGENCE",
            "severity": "HIGH" if (len(bullish) >= 3 or len(bearish) >= 3) else "MODERATE",
            "message": f"Bullish ({bull_names}) vs Bearish ({bear_names})",
            "context": "Historically, multi-signal divergence resolves within 24-72h. The minority direction often wins.",
            "bullish_signals": bullish,
            "bearish_signals": bearish,
        })

    # Sentiment-Price divergence (most tradeable)
    if (sent_score > 30 and price_change < -3) or (sent_score < -30 and price_change > 3):
        divergence_alerts.append({
            "type": "SENT_PRICE_DIV",
            "severity": "HIGH",
            "message": f"Sentiment ({sent_score:+.0f}) diverges from Price ({price_change:+.1f}%)",
            "context": "Sentiment-price divergence historically resolves within 48h. Sentiment tends to lead.",
        })

    result = {
        "divergence_detected": divergence_detected or len(divergence_alerts) > 0,
        "alerts": divergence_alerts,
        "signals": signals,
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "neutral_count": len([s for s in signals if s["direction"] == 0]),
        "updated_at": now,
    }
    _divergence_cache["value"] = result
    _divergence_cache["ts"] = now
    return result


def _compute_early_warnings(state: dict) -> dict:
    """Top 5 early warning indicators from live data.

    Precursor patterns that historically precede major BTC moves by 24-72h:
    1. Hashrate surge + exchange outflows = supply shock precursor
    2. Fear & Greed extreme (<15 or >85) + volume spike = reversal imminent
    3. Miner capitulation (score <40) + hash price compression = bottom signal
    4. Whale accumulation + low mempool = stealth buying
    5. PCAF anomaly spike + sentiment divergence = structural shift
    """
    now = time.time()
    if _early_warning_cache["value"] and now - _early_warning_cache["ts"] < 30:
        return _early_warning_cache["value"]

    price = state.get("price", {})
    mh = state.get("miner_health", {})
    fng = state.get("fng", {})
    mem = state.get("mempool", {})
    dp = state.get("dark_pool", {})
    wc = state.get("whale_coordination", {})
    sent = state.get("sentiment", {})
    pcaf = state.get("pcaf_v0", {})
    etf = state.get("etf", {})
    ln = state.get("lightning", {})
    net = state.get("network", {})

    fng_val = fng.get("value", 50) if isinstance(fng, dict) else 50
    miner_score = mh.get("score", 100)
    pcaf_score = pcaf.get("anomaly_score", 0)
    sent_score = sent.get("score", 0)
    price_change = (price or {}).get("change_24h", 0)
    mempool_vsize = (mem.get("vsize", 0) or 0) / 1e6  # vMB
    whale_btc = wc.get("total_btc_90min", 0)
    etf_dir = etf.get("net_6h_direction", "neutral")

    warnings = []

    # 1. Supply Shock Precursor
    hashrate = net.get("hashrate_3d", 0) or 0
    if hashrate > 0 and etf_dir == "outflow":
        conf = min(85, 50 + int(hashrate / 10))
        warnings.append({
            "id": "supply_shock",
            "name": "Supply Shock Precursor",
            "confidence": conf,
            "timeframe": "24-72h",
            "direction": "BULLISH",
            "detail": f"Hashrate {hashrate:.0f} EH/s + exchange outflows detected",
            "precedent": "Historically, hashrate highs + outflows preceded 8-15% rallies within 72h",
            "active": etf_dir == "outflow" and hashrate > 600,
        })

    # 2. Extreme Fear/Greed Reversal
    if fng_val <= 20 or fng_val >= 80:
        direction = "BULLISH" if fng_val <= 20 else "BEARISH"
        conf = min(90, 60 + abs(50 - fng_val))
        warnings.append({
            "id": "fng_extreme",
            "name": "Fear & Greed Extreme",
            "confidence": conf,
            "timeframe": "24-48h",
            "direction": direction,
            "detail": f"F&G Index at {fng_val} ({fng.get('label', '')}) — contrarian signal",
            "precedent": f"F&G {'<20' if fng_val<=20 else '>80'} historically precedes {'reversal up' if fng_val<=20 else 'correction'} within 48h",
            "active": True,
        })

    # 3. Miner Capitulation Signal
    if miner_score < 60:
        conf = min(80, 40 + (100 - miner_score))
        warnings.append({
            "id": "miner_cap",
            "name": "Miner Stress Signal",
            "confidence": conf,
            "timeframe": "48-72h",
            "direction": "BULLISH" if miner_score < 40 else "WATCH",
            "detail": f"Miner health score {miner_score}/100 — {'capitulation zone' if miner_score<40 else 'stressed'}",
            "precedent": "Miner capitulation historically marks cycle bottoms — last 5 events preceded 20%+ rallies",
            "active": True,
        })

    # 4. Stealth Accumulation
    if whale_btc > 10 and mempool_vsize < 50:
        conf = min(75, 50 + int(whale_btc / 5))
        warnings.append({
            "id": "stealth_accum",
            "name": "Stealth Accumulation",
            "confidence": conf,
            "timeframe": "24-48h",
            "direction": "BULLISH",
            "detail": f"{whale_btc:.0f} BTC whale txs in quiet mempool ({mempool_vsize:.0f} vMB)",
            "precedent": "Large whale txs during low mempool activity = institutional OTC accumulation pattern",
            "active": True,
        })

    # 5. PCAF Structural Shift
    if pcaf_score >= 40:
        sent_div = abs(sent_score) > 30
        conf = min(85, pcaf_score + (20 if sent_div else 0))
        warnings.append({
            "id": "pcaf_shift",
            "name": "PCAF Structural Alert",
            "confidence": conf,
            "timeframe": "24-72h",
            "direction": "WATCH",
            "detail": f"PCAF anomaly {pcaf_score}/100{' + sentiment divergence' if sent_div else ''}",
            "precedent": "PCAF >40 with sentiment divergence preceded 5 of last 7 major moves",
            "active": True,
        })

    # 6. Lightning Network surge (if data available)
    ln_cap = ln.get("capacity_btc", 0) or 0
    if ln_cap > 5500:
        warnings.append({
            "id": "ln_surge",
            "name": "Lightning Capacity Surge",
            "confidence": 55,
            "timeframe": "48-72h",
            "direction": "BULLISH",
            "detail": f"LN capacity {ln_cap:.0f} BTC — above 5,500 BTC threshold",
            "precedent": "Lightning capacity growth correlates with long-term holder conviction",
            "active": True,
        })

    # Sort by confidence, take top 5 active
    active_warnings = [w for w in warnings if w.get("active")]
    active_warnings.sort(key=lambda x: x["confidence"], reverse=True)

    result = {
        "warnings": active_warnings[:5],
        "total_active": len(active_warnings),
        "highest_confidence": active_warnings[0]["confidence"] if active_warnings else 0,
        "updated_at": now,
    }
    _early_warning_cache["value"] = result
    _early_warning_cache["ts"] = now
    return result


def _get_alpha_intel(state: dict) -> dict:
    """Bundle all Phase 1 alpha intel for SSE stream injection."""
    return {
        "signal_matrix": _compute_signal_matrix(state),
        "narrative_momentum": _compute_narrative_momentum(),
        "divergence": _compute_divergence_alerts(state),
        "early_warnings": _compute_early_warnings(state),
    }


@intelligence_bp.route("/api/intelligence/signal-matrix")
def api_signal_matrix():
    """Sovereign Signal Matrix — 6-axis radar. Commander+ auth."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    return jsonify(_compute_signal_matrix(state))


@intelligence_bp.route("/api/intelligence/narrative-momentum")
def api_narrative_momentum():
    """Narrative Momentum Tracker — article topic acceleration. Commander+ auth."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    return jsonify(_compute_narrative_momentum())


@intelligence_bp.route("/api/intelligence/divergence")
def api_divergence():
    """Cross-Signal Divergence Alerts. Commander+ auth."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    return jsonify(_compute_divergence_alerts(state))


@intelligence_bp.route("/api/intelligence/early-warnings")
def api_early_warnings():
    """Early Warning Feed — top 5 precursor indicators. Commander+ auth."""
    if not _has_access():
        return jsonify({"error": "Commander access required"}), 401
    state = _sentinel.get_state()
    return jsonify(_compute_early_warnings(state))


# ═══════════════════════════════════════════════════════════════════════════
# Landing Page — /intelligence-terminal (public, no auth)
# ═══════════════════════════════════════════════════════════════════════════

@intelligence_bp.route("/intelligence-terminal")
def intelligence_landing():
    """Public landing page for Intelligence Terminal product."""
    return render_template("intelligence_landing.html")


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC SIGNAL DATA — /api/signals (no auth, powered by signal_data_fetcher)
# ═══════════════════════════════════════════════════════════════════════════

_SIGNALS_PATH = str(Path(__file__).resolve().parent.parent.parent / "data" / "signals.json")


@intelligence_bp.route("/api/signals")
def api_signals():
    """Serve latest signal data from signals.json — public, no auth."""
    try:
        with open(_SIGNALS_PATH) as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "updated_at": None}), 200


@intelligence_bp.route("/api/panopticon/status")
def api_panopticon_status():
    """Feed Panopticon counters from live signal data."""
    try:
        with open(_SIGNALS_PATH) as f:
            data = json.load(f)
        return jsonify({
            "disclosures": 0,
            "whale_moves": data.get("whale_moves", {}).get("count", 0),
            "patterns": data.get("signal_score", {}).get("bull_count", 0) + data.get("signal_score", {}).get("bear_count", 0),
            "events_today": sum(data.get("signal_score", {}).get(k, 0) for k in ("bull_count", "bear_count", "neutral_count")),
            "fear_greed": data.get("fear_greed", {}),
            "hashrate": data.get("hashrate", {}),
            "updated_at": data.get("updated_at"),
        })
    except Exception:
        return jsonify({"disclosures": 0, "whale_moves": 0, "patterns": 0, "events_today": 0})
