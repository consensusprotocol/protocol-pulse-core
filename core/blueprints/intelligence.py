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
import time
from pathlib import Path

from flask import Blueprint, Response, jsonify, render_template, request, stream_with_context
from flask_login import current_user

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

@intelligence_bp.route("/intelligence")
def intelligence_terminal():
    """Full Intelligence Terminal — Commander+ only."""
    if not _is_commander():
        return render_template("intelligence_terminal.html", demo_mode=True)
    return render_template("intelligence_terminal.html", demo_mode=False)


@intelligence_bp.route("/intelligence/demo")
def intelligence_demo():
    """Demo view — always watermarked."""
    return render_template("intelligence_terminal.html", demo_mode=True)


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
