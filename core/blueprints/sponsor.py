"""
SPONSOR AGENT BLUEPRINT — Protocol Pulse
==========================================
Routes:
  GET  /sponsor-agent               — Admin dashboard (Kanban view)
  POST /api/sponsor-agent/scan      — Trigger prospect scan
  POST /api/sponsor-agent/draft     — Draft emails for prospects
  POST /api/sponsor-agent/send      — Send approved outreach email
  POST /api/sponsor-agent/status    — Update outreach status
  GET  /api/sponsor-agent/stats     — Pipeline stats
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

sponsor_bp = Blueprint("sponsor", __name__)

VALID_STATUSES = {"prospect", "draft", "approved", "sent", "replied", "negotiating", "closed", "rejected"}


def _check_admin():
    """Verify admin token. Returns error response or None if OK."""
    token = os.environ.get("ADMIN_TOKEN", "")
    if not token:
        return jsonify({"error": "ADMIN_TOKEN not configured"}), 500

    provided = request.headers.get("X-Admin-Token") or request.args.get("token", "")
    if provided != token:
        return jsonify({"error": "Unauthorized"}), 401

    return None


@sponsor_bp.route("/sponsor-agent")
def dashboard():
    """Admin Kanban dashboard for sponsor outreach pipeline."""
    token = os.environ.get("ADMIN_TOKEN", "")
    provided = request.args.get("token", "")
    if not token or provided != token:
        return "Unauthorized", 401

    from app import db
    from models import SponsorOutreach

    outreach_items = SponsorOutreach.query.order_by(SponsorOutreach.created_at.desc()).all()

    # Group by status
    columns = {}
    for status in ["prospect", "draft", "approved", "sent", "replied", "negotiating", "closed", "rejected"]:
        columns[status] = [o for o in outreach_items if o.status == status]

    # Stats
    total = len(outreach_items)
    sent_count = sum(1 for o in outreach_items if o.status in ("sent", "replied", "negotiating", "closed"))
    replied_count = sum(1 for o in outreach_items if o.status in ("replied", "negotiating", "closed"))
    closed_count = sum(1 for o in outreach_items if o.status == "closed")
    revenue = sum(o.deal_value or 0 for o in outreach_items if o.status == "closed")

    return render_template(
        "sponsor_agent.html",
        columns=columns,
        total=total,
        sent_count=sent_count,
        replied_count=replied_count,
        closed_count=closed_count,
        revenue=revenue,
        token=provided,
    )


@sponsor_bp.route("/api/sponsor-agent/scan", methods=["POST"])
def api_scan():
    """Trigger a prospect scan."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True) or {}
    count = min(int(data.get("count", 5)), 20)
    category = data.get("category")

    from sponsor_agent.prospect_finder import find_new_prospects
    from app import app

    prospects = find_new_prospects(count=count, category=category)
    return jsonify({"found": len(prospects), "prospects": prospects})


@sponsor_bp.route("/api/sponsor-agent/draft", methods=["POST"])
def api_draft():
    """Draft emails for all prospect-status outreach items."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    from sponsor_agent.email_writer import draft_emails_for_prospects

    drafted = draft_emails_for_prospects()
    return jsonify({"drafted": drafted})


@sponsor_bp.route("/api/sponsor-agent/send", methods=["POST"])
def api_send():
    """Send an approved outreach email via Resend."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    from app import db
    from models import SponsorOutreach

    data = request.get_json(silent=True) or {}
    outreach_id = data.get("id")
    if not outreach_id:
        return jsonify({"error": "Missing id"}), 400

    outreach = SponsorOutreach.query.get(outreach_id)
    if not outreach:
        return jsonify({"error": "Not found"}), 404

    if outreach.status != "approved":
        return jsonify({"error": f"Cannot send — status is '{outreach.status}', must be 'approved'"}), 400

    if not outreach.email:
        return jsonify({"error": "No email address for this prospect"}), 400

    # Send via Resend
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        return jsonify({"error": "RESEND_API_KEY not configured"}), 500

    import requests as http_requests

    try:
        resp = http_requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json={
                "from": "Protocol Pulse <partnerships@protocolpulse.io>",
                "to": [outreach.email],
                "subject": outreach.subject,
                "text": outreach.body,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except http_requests.RequestException as exc:
        logger.error("Resend send failed for %s: %s", outreach.company, exc)
        return jsonify({"error": f"Send failed: {exc}"}), 502

    outreach.status = "sent"
    outreach.sent_at = datetime.utcnow()
    db.session.commit()

    logger.info("Sent outreach email to %s (%s)", outreach.company, outreach.email)
    return jsonify({"ok": True, "company": outreach.company})


@sponsor_bp.route("/api/sponsor-agent/status", methods=["POST"])
def api_update_status():
    """Update outreach status and/or notes."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    from app import db
    from models import SponsorOutreach

    data = request.get_json(silent=True) or {}
    outreach_id = data.get("id")
    new_status = data.get("status")
    notes = data.get("notes")
    deal_value = data.get("deal_value")

    if not outreach_id:
        return jsonify({"error": "Missing id"}), 400

    outreach = SponsorOutreach.query.get(outreach_id)
    if not outreach:
        return jsonify({"error": "Not found"}), 404

    if new_status:
        if new_status not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status: {new_status}"}), 400
        outreach.status = new_status
        if new_status == "replied":
            outreach.replied_at = datetime.utcnow()

    if notes is not None:
        outreach.notes = notes

    if deal_value is not None:
        outreach.deal_value = float(deal_value)

    db.session.commit()
    return jsonify({"ok": True, "status": outreach.status})


@sponsor_bp.route("/api/sponsor-agent/stats")
def api_stats():
    """Pipeline stats."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    from models import SponsorOutreach

    items = SponsorOutreach.query.all()
    stats = {s: 0 for s in VALID_STATUSES}
    revenue = 0.0
    for item in items:
        if item.status in stats:
            stats[item.status] += 1
        if item.status == "closed" and item.deal_value:
            revenue += item.deal_value

    return jsonify({
        "total": len(items),
        "by_status": stats,
        "revenue": revenue,
    })
