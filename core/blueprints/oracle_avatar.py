"""
SESSION 7 — ORACLE AVATAR
Blueprint: oracle_avatar_bp

Routes:
  GET  /oracle-live                — page (hero video, schedule, archive, status sidebar)
  GET  /api/oracle/briefings       — today + last 7 days briefings list
  GET  /api/oracle/status          — system health, next scheduled, last generated
  POST /api/oracle/generate        — manual trigger (admin only, IP-gated)
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, date
from pathlib import Path

import pytz
import requests
from flask import Blueprint, jsonify, render_template, request, abort

logger = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")

BRIEFING_SLOTS = {
    "pre_market": {
        "label":       "Pre-Market Briefing",
        "time_et":     "7:45 AM ET",
        "time_utc":    "12:45 UTC",
        "description": "Overnight BTC moves, Asian session wrap, key levels for the day",
        "publish_hour_et": 8,   # 08:00 ET publish time
    },
    "open": {
        "label":       "Market Open Briefing",
        "time_et":     "12:00 PM ET",
        "time_utc":    "17:00 UTC",
        "description": "Mid-session update — mempool status, fee market, notable developments",
        "publish_hour_et": 12,
    },
    "close": {
        "label":       "Daily Close Briefing",
        "time_et":     "5:00 PM ET",
        "time_utc":    "22:00 UTC",
        "description": "Day summary, Signal score, tomorrow's outlook",
        "publish_hour_et": 17,
    },
}

# Ultron LAN / cloudflare tunnel IPs allowed for admin trigger
ADMIN_ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}
ADMIN_TOKEN = os.environ.get("ORACLE_ADMIN_TOKEN", "")

oracle_avatar_bp = Blueprint("oracle_avatar", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_et_now() -> datetime:
    return datetime.now(ET)


def _et_date_str(dt: datetime | None = None) -> str:
    d = dt or _get_et_now()
    return d.strftime("%Y-%m-%d")


def _load_env_keys():
    """Load root .env keys not present in core/.env."""
    root_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if root_env.exists() and not os.environ.get("HEYGEN_API_KEY"):
        for line in root_env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _live_btc_price() -> float | None:
    try:
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            price = r.json().get("USD")
            if price:
                return float(price)
    except Exception:
        pass
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=5,
        )
        if r.status_code == 200:
            return float(r.json().get("bitcoin", {}).get("usd", 0)) or None
    except Exception:
        pass
    return None


def _live_fear_greed() -> dict:
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        if r.status_code == 200:
            fng = r.json().get("data", [{}])[0]
            return {"value": fng.get("value"), "label": fng.get("value_classification")}
    except Exception:
        pass
    return {"value": None, "label": "Unavailable"}


def _heygen_api_ok() -> bool:
    key = os.environ.get("HEYGEN_API_KEY", "")
    return bool(key and len(key) > 10)


def _elevenlabs_api_ok() -> bool:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    return bool(key and len(key) > 10)


def _anthropic_api_ok() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(key and len(key) > 10)


def _next_scheduled_briefing() -> dict:
    """Return info about the next upcoming briefing slot."""
    now_et = _get_et_now()
    for slot_type, slot in BRIEFING_SLOTS.items():
        slot_time = now_et.replace(
            hour=slot["publish_hour_et"],
            minute=0,
            second=0,
            microsecond=0,
        )
        if slot_time > now_et:
            diff = slot_time - now_et
            hours, rem = divmod(int(diff.total_seconds()), 3600)
            minutes = rem // 60
            return {
                "type": slot_type,
                "label": slot["label"],
                "time_et": slot["time_et"],
                "seconds_until": int(diff.total_seconds()),
                "eta_str": f"{hours}h {minutes}m" if hours else f"{minutes}m",
            }
    # All today's slots passed — next is tomorrow's pre_market
    tomorrow_et = (now_et + timedelta(days=1)).replace(
        hour=7, minute=45, second=0, microsecond=0
    )
    diff = tomorrow_et - now_et
    hours, rem = divmod(int(diff.total_seconds()), 3600)
    minutes = rem // 60
    return {
        "type": "pre_market",
        "label": "Pre-Market Briefing",
        "time_et": "7:45 AM ET (tomorrow)",
        "seconds_until": int(diff.total_seconds()),
        "eta_str": f"{hours}h {minutes}m",
    }


def _get_briefings_list(days_back: int = 7) -> list[dict]:
    """Return briefings from today + last N days, newest first."""
    try:
        import models
        from app import app
        with app.app_context():
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            briefings = (
                models.MarketBriefing.query
                .filter(models.MarketBriefing.generated_at >= cutoff)
                .order_by(models.MarketBriefing.generated_at.desc())
                .limit(30)
                .all()
            )
            return [b.to_dict() for b in briefings]
    except Exception as exc:
        logger.warning("Briefings list fetch failed: %s", exc)
        return []


def _get_today_briefings() -> dict:
    """Return {pre_market, open, close} slots with their DB status for today."""
    et_date = _et_date_str()
    slots: dict = {k: {"slot": v, "briefing": None} for k, v in BRIEFING_SLOTS.items()}
    try:
        import models
        from app import app
        with app.app_context():
            today_briefings = (
                models.MarketBriefing.query
                .filter_by(scheduled_date=et_date)
                .all()
            )
            for b in today_briefings:
                if b.briefing_type in slots:
                    slots[b.briefing_type]["briefing"] = b.to_dict()
    except Exception as exc:
        logger.warning("Today briefings fetch failed: %s", exc)
    return slots


def _is_admin_request() -> bool:
    """IP gate + optional token check for manual trigger."""
    ip = request.remote_addr or ""
    if ip in ADMIN_ALLOWED_IPS:
        return True
    token = request.headers.get("X-Admin-Token", "") or request.args.get("token", "")
    if ADMIN_TOKEN and token == ADMIN_TOKEN:
        return True
    return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@oracle_avatar_bp.route("/oracle-live")
def oracle_live():
    """Oracle Live — cinematic briefing viewer."""
    _load_env_keys()

    today_slots = _get_today_briefings()
    recent_briefings = _get_briefings_list(days_back=7)
    btc_price = _live_btc_price()
    fear_greed = _live_fear_greed()
    next_slot = _next_scheduled_briefing()

    # Latest published video for hero player
    hero_briefing = next(
        (b for b in recent_briefings if b.get("status") == "completed" and b.get("video_url")),
        None,
    )

    system_status = {
        "heygen":     {"ok": _heygen_api_ok(),     "label": "HeyGen API"},
        "elevenlabs": {"ok": _elevenlabs_api_ok(), "label": "ElevenLabs"},
        "anthropic":  {"ok": _anthropic_api_ok(),  "label": "Script Gen"},
    }

    # Count today's completed briefings
    today_completed = sum(
        1 for s in today_slots.values()
        if s.get("briefing") and s["briefing"].get("status") == "completed"
    )

    return render_template(
        "oracle_live.html",
        hero_briefing=hero_briefing,
        today_slots=today_slots,
        today_completed=today_completed,
        recent_briefings=recent_briefings,
        system_status=system_status,
        next_slot=next_slot,
        btc_price=btc_price,
        fear_greed=fear_greed,
        et_date=_et_date_str(),
        now_et=_get_et_now().strftime("%H:%M ET"),
    )


@oracle_avatar_bp.route("/api/oracle/briefings")
def api_oracle_briefings():
    """List briefings: today's slots + last 7 days archive."""
    _load_env_keys()
    days_back = min(int(request.args.get("days", 7)), 30)

    today_slots = _get_today_briefings()
    archive = _get_briefings_list(days_back=days_back)

    # Serialize today slots
    today_out = {}
    for slot_type, slot_data in today_slots.items():
        today_out[slot_type] = {
            "slot_label": slot_data["slot"]["label"],
            "time_et": slot_data["slot"]["time_et"],
            "description": slot_data["slot"]["description"],
            "briefing": slot_data["briefing"],
        }

    return jsonify({
        "today": today_out,
        "archive": archive,
        "et_date": _et_date_str(),
        "total": len(archive),
    })


@oracle_avatar_bp.route("/api/oracle/status")
def api_oracle_status():
    """System health + scheduling metadata."""
    _load_env_keys()

    next_slot = _next_scheduled_briefing()
    today_slots = _get_today_briefings()
    today_completed = sum(
        1 for s in today_slots.values()
        if s.get("briefing") and s["briefing"].get("status") == "completed"
    )

    # Most recent completed briefing
    recent = _get_briefings_list(days_back=1)
    last_completed = next(
        (b for b in recent if b.get("status") == "completed"), None
    )

    last_generated_ago = None
    if last_completed and last_completed.get("generated_at"):
        try:
            ts = datetime.fromisoformat(last_completed["generated_at"])
            diff = datetime.utcnow() - ts.replace(tzinfo=None)
            h, rem = divmod(int(diff.total_seconds()), 3600)
            m = rem // 60
            last_generated_ago = f"{h}h {m}m ago" if h else f"{m}m ago"
        except Exception:
            pass

    system_status = {
        "heygen":     {"ok": _heygen_api_ok(),     "label": "HeyGen API"},
        "elevenlabs": {"ok": _elevenlabs_api_ok(), "label": "ElevenLabs TTS"},
        "anthropic":  {"ok": _anthropic_api_ok(),  "label": "Script Generation"},
    }
    all_ok = all(v["ok"] for v in system_status.values())

    return jsonify({
        "system": system_status,
        "all_systems_go": all_ok,
        "next_scheduled": next_slot,
        "today_completed": today_completed,
        "today_total_slots": len(BRIEFING_SLOTS),
        "last_generated": last_completed,
        "last_generated_ago": last_generated_ago,
        "et_now": _get_et_now().strftime("%Y-%m-%d %H:%M ET"),
    })


@oracle_avatar_bp.route("/api/oracle/generate", methods=["POST"])
def api_oracle_generate():
    """Manual briefing generation — admin only (IP-gated + token)."""
    _load_env_keys()

    if not _is_admin_request():
        logger.warning(
            "Unauthorized oracle generate attempt from %s", request.remote_addr
        )
        abort(403)

    body = request.get_json(silent=True) or {}
    briefing_type = body.get("briefing_type", "open")
    if briefing_type not in BRIEFING_SLOTS:
        return jsonify({
            "success": False,
            "error": f"Invalid briefing_type: {briefing_type}. Valid: {list(BRIEFING_SLOTS)}",
        }), 400

    try:
        from core.services.briefing_service import generate_briefing
        result = generate_briefing(briefing_type)
    except ImportError:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from services.briefing_service import generate_briefing
            result = generate_briefing(briefing_type)
        except Exception as exc:
            logger.error("Oracle generate import failed: %s", exc)
            return jsonify({"success": False, "error": str(exc)}), 500
    except Exception as exc:
        logger.error("Oracle generate failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500

    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code
