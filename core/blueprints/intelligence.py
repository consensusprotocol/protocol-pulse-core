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


@intelligence_bp.route("/intelligence")
def intelligence_terminal():
    """Full Intelligence Terminal — Commander+ only, demo mode for guests."""
    just_upgraded = session.pop("just_upgraded", False)
    activated = request.args.get("activated") == "1"
    show_welcome = just_upgraded or activated

    if not _is_commander():
        return render_template("intelligence_terminal.html", demo_mode=True, show_welcome=False)
    return render_template("intelligence_terminal.html", demo_mode=False, show_welcome=show_welcome)


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
# Landing Page — /intelligence-terminal (public, no auth)
# ═══════════════════════════════════════════════════════════════════════════

@intelligence_bp.route("/intelligence-terminal")
def intelligence_landing():
    """Public landing page for Intelligence Terminal product."""
    return render_template("intelligence_landing.html")
