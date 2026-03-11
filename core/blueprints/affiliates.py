"""
core/blueprints/affiliates.py
Protocol Pulse SESSION 13 — Affiliate Revenue Engine Blueprint

Routes:
  GET  /bitcoin-insurance          — Meanwhile landing page
  GET  /digital-residency          — RNS.ID landing page (alias)
  GET  /go/meanwhile               — Click redirect → Meanwhile
  GET  /go/rns                     — Click redirect → RNS.ID
  GET  /api/affiliate/click        — Click tracking + redirect
  GET  /admin/affiliates           — Admin dashboard
"""

import hashlib
import logging
import os
from datetime import datetime

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    jsonify,
    url_for,
)
from flask_login import login_required

logger = logging.getLogger(__name__)

affiliates_bp = Blueprint(
    "affiliates",
    __name__,
    url_prefix="",
)

# Affiliate destination URLs
AFFILIATE_URLS = {
    "meanwhile": "https://meanwhile.app?ref=KKM73K",
    "rns": "https://rns.id?ref=protocol-pulse",
}


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────
def _get_user_hash(ip: str) -> str:
    """SHA256(ip + date.today() + TRACKING_SALT)[:16] — daily rotating."""
    from services.affiliate_injector import hash_user
    return hash_user(ip)


def _get_client_ip() -> str:
    return (
        request.headers.get("X-Forwarded-For", request.remote_addr or "")
        .split(",")[0]
        .strip()
    )


def _get_ab_variant(user_hash: str) -> str:
    """50/50 A/B split based on last nibble of user_hash."""
    return "A" if int(user_hash[-1], 16) < 8 else "B"


def _record_click_db(partner: str, article_id: str, user_hash: str, variant: str):
    """Write click to affiliate_clicks table (lazy import to avoid circular deps)."""
    try:
        from app import db
        from services.affiliate_injector import record_click
        record_click(db, partner, article_id, user_hash, variant)
    except Exception as exc:
        logger.warning("_record_click_db failed: %s", exc)


# ────────────────────────────────────────────────────────────
# Landing Pages
# ────────────────────────────────────────────────────────────
@affiliates_bp.route("/bitcoin-insurance")
def bitcoin_insurance():
    """Meanwhile Bitcoin Life Insurance landing page — SESSION 13."""
    return render_template("bitcoin_insurance.html")


# ────────────────────────────────────────────────────────────
# GET /api/affiliate/click  — Click tracking + redirect
# ────────────────────────────────────────────────────────────
@affiliates_bp.route("/api/affiliate/click")
def affiliate_click():
    """
    Track affiliate click and redirect to partner URL.

    Query params:
      partner    — 'meanwhile' | 'rns'
      article_id — source article (optional, defaults to 'direct')

    LAW: TRACKING_SALT MUST be set — raises RuntimeError if missing.
    LAW: Never store raw IP — always SHA256 hash.
    LAW: 50/50 A/B via user_hash last nibble.
    """
    partner = request.args.get("partner", "").strip().lower()
    article_id = request.args.get("article_id", "direct")

    if partner not in AFFILIATE_URLS:
        return redirect("/", code=302)

    ip = _get_client_ip()

    # TRACKING_SALT hard-fail — raises RuntimeError if not set (per LAW)
    user_hash = _get_user_hash(ip)

    # A/B variant: 50/50 deterministic from user_hash
    variant = _get_ab_variant(user_hash)

    # Record click asynchronously (fire-and-forget; don't block redirect)
    _record_click_db(partner, str(article_id), user_hash, variant)

    # Redirect to affiliate URL
    dest = AFFILIATE_URLS[partner]
    resp = redirect(dest, code=302)
    resp.headers["Cache-Control"] = "no-store, no-cache"
    return resp


# ────────────────────────────────────────────────────────────
# Short redirect aliases (/go/*)
# ────────────────────────────────────────────────────────────
@affiliates_bp.route("/go/meanwhile-s13")
def go_meanwhile_s13():
    """Session 13 short link for Meanwhile."""
    ip = _get_client_ip()
    user_hash = _get_user_hash(ip)
    variant = _get_ab_variant(user_hash)
    referrer = request.args.get("ref", request.referrer or "direct")
    _record_click_db("meanwhile", referrer[:200], user_hash, variant)
    resp = redirect(AFFILIATE_URLS["meanwhile"], code=302)
    resp.headers["Cache-Control"] = "no-store, no-cache"
    return resp


@affiliates_bp.route("/go/rns-s13")
def go_rns_s13():
    """Session 13 short link for RNS.ID."""
    ip = _get_client_ip()
    user_hash = _get_user_hash(ip)
    variant = _get_ab_variant(user_hash)
    referrer = request.args.get("ref", request.referrer or "direct")
    _record_click_db("rns", referrer[:200], user_hash, variant)
    resp = redirect(AFFILIATE_URLS["rns"], code=302)
    resp.headers["Cache-Control"] = "no-store, no-cache"
    return resp


# ────────────────────────────────────────────────────────────
# Admin Dashboard
# ────────────────────────────────────────────────────────────
@affiliates_bp.route("/admin/affiliates-s13")
@login_required
def admin_affiliates_s13():
    """
    Admin affiliate analytics dashboard (SESSION 13).
    Shows click counts per partner, A/B performance, recent clicks.
    """
    try:
        from app import db
        from sqlalchemy import text
        from services.affiliate_injector import (
            _init_affiliate_clicks_table,
            compute_ab_stats,
            PARTNER_CONFIG,
        )

        _init_affiliate_clicks_table(db)

        # Totals per partner
        totals = db.session.execute(text(
            "SELECT partner, COUNT(*) as total "
            "FROM affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner"
        )).fetchall()
        totals_map = {r[0]: r[1] for r in totals}

        # Daily clicks last 30 days
        daily = db.session.execute(text(
            "SELECT partner, date(clicked_at) as day, COUNT(*) as cnt "
            "FROM affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner, day ORDER BY day DESC"
        )).fetchall()
        daily_by_partner = {}
        for r in daily:
            daily_by_partner.setdefault(r[0], []).append({"date": r[1], "clicks": r[2]})

        # Recent clicks (last 20, k-anon: show truncated hash only)
        recent = db.session.execute(text(
            "SELECT partner, article_id, substr(user_hash,1,8) as hash_prefix, "
            "variant, clicked_at "
            "FROM affiliate_clicks "
            "ORDER BY clicked_at DESC LIMIT 20"
        )).fetchall()

        # A/B stats
        ab_stats = {
            "meanwhile": compute_ab_stats("meanwhile", db),
            "rns": compute_ab_stats("rns", db),
        }

        # Estimated earnings (conservative 2% conversion)
        earnings = {}
        for partner_key, cfg in PARTNER_CONFIG.items():
            t = totals_map.get(partner_key, 0)
            earnings[partner_key] = round(t * 0.02 * cfg["estimated_commission"], 2)

        return render_template(
            "admin/affiliates_s13.html",
            totals_map=totals_map,
            daily_by_partner=daily_by_partner,
            recent=recent,
            ab_stats=ab_stats,
            earnings=earnings,
            partner_cfg=PARTNER_CONFIG,
        )

    except Exception as exc:
        logger.error("admin_affiliates_s13 error: %s", exc)
        return render_template(
            "admin/affiliates_s13.html",
            totals_map={},
            daily_by_partner={},
            recent=[],
            ab_stats={},
            earnings={},
            partner_cfg={},
            error=str(exc),
        )
