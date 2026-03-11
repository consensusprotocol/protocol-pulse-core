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

ALLOWED_TRANSITIONS = {
    "prospect": {"draft", "rejected"},
    "draft": {"approved", "rejected"},
    "approved": {"sent", "rejected"},
    "sent": {"replied", "rejected"},
    "replied": {"negotiating", "rejected"},
    "negotiating": {"closed", "rejected"},
    "closed": set(),
    "rejected": set(),
}


def _check_admin():
    """Verify admin token via header only. Returns error response or None if OK."""
    token = os.environ.get("ADMIN_TOKEN", "")
    if not token:
        return jsonify({"error": "ADMIN_TOKEN not configured"}), 500

    provided = request.headers.get("X-Admin-Token", "")
    if provided != token:
        return jsonify({"error": "Unauthorized"}), 401

    return None


def _check_admin_page():
    """Verify admin for page loads (header or query param for initial load)."""
    token = os.environ.get("ADMIN_TOKEN", "")
    if not token:
        return False
    provided = request.headers.get("X-Admin-Token") or request.args.get("token", "")
    return provided == token


def _log_activity(db, outreach_id: int, action: str, details: str = None,
                  old_status: str = None, new_status: str = None):
    """Record a state change in the activity log."""
    from models import SponsorActivityLog
    log = SponsorActivityLog(
        outreach_id=outreach_id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        details=details,
    )
    db.session.add(log)


@sponsor_bp.route("/sponsor-agent")
def dashboard():
    """Admin Kanban dashboard for sponsor outreach pipeline."""
    if not _check_admin_page():
        return "Unauthorized", 401

    from models import SponsorOutreach

    outreach_items = (
        SponsorOutreach.query
        .filter_by(is_deleted=False)
        .order_by(SponsorOutreach.created_at.desc())
        .all()
    )

    columns = {}
    for status in ["prospect", "draft", "approved", "sent", "replied", "negotiating", "closed", "rejected"]:
        columns[status] = [o for o in outreach_items if o.status == status]

    total = len(outreach_items)
    sent_count = sum(1 for o in outreach_items if o.status in ("sent", "replied", "negotiating", "closed"))
    replied_count = sum(1 for o in outreach_items if o.status in ("replied", "negotiating", "closed"))
    closed_count = sum(1 for o in outreach_items if o.status == "closed")
    revenue = sum(o.deal_value or 0 for o in outreach_items if o.status == "closed")

    token = request.args.get("token", "")

    return render_template(
        "sponsor_agent.html",
        columns=columns,
        total=total,
        sent_count=sent_count,
        replied_count=replied_count,
        closed_count=closed_count,
        revenue=revenue,
        token=token,
    )


@sponsor_bp.route("/api/sponsor-agent/scan", methods=["POST"])
def api_scan():
    """Trigger a prospect scan."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True) or {}

    try:
        count = max(1, min(int(data.get("count", 5)), 20))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid count parameter"}), 400

    category = data.get("category")
    if category and category not in {"hardware", "exchanges", "mining", "financial", "education"}:
        return jsonify({"error": f"Invalid category: {category}"}), 400

    from sponsor_agent.prospect_finder import find_new_prospects

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

    try:
        outreach_id = int(data.get("id", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid id"}), 400

    if not outreach_id:
        return jsonify({"error": "Missing id"}), 400

    outreach = SponsorOutreach.query.get(outreach_id)
    if not outreach:
        return jsonify({"error": "Not found"}), 404

    if outreach.status != "approved":
        return jsonify({"error": f"Cannot send — status is '{outreach.status}', must be 'approved'"}), 400

    if not outreach.email:
        return jsonify({"error": "No email address for this prospect"}), 400

    if not outreach.subject or not outreach.body:
        return jsonify({"error": "Email subject and body must be set before sending"}), 400

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
        resend_data = resp.json()
    except http_requests.RequestException as exc:
        logger.error("Resend send failed for outreach_id=%d (%s): %s", outreach.id, outreach.company, exc)
        return jsonify({"error": f"Send failed: {exc}"}), 502

    old_status = outreach.status
    outreach.status = "sent"
    outreach.sent_at = datetime.utcnow()
    outreach.resend_message_id = resend_data.get("id")

    _log_activity(db, outreach.id, "email_sent",
                  f"Sent via Resend (msg_id={outreach.resend_message_id})",
                  old_status=old_status, new_status="sent")

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("DB commit failed after sending email for outreach_id=%d: %s", outreach.id, exc)
        return jsonify({"error": "Email sent but failed to update status — check logs"}), 500

    logger.info("Sent outreach to %s (%s), resend_id=%s", outreach.company, outreach.email, outreach.resend_message_id)
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

    try:
        outreach_id = int(data.get("id", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid id"}), 400

    if not outreach_id:
        return jsonify({"error": "Missing id"}), 400

    new_status = data.get("status")
    notes = data.get("notes")
    deal_value = data.get("deal_value")

    outreach = SponsorOutreach.query.get(outreach_id)
    if not outreach:
        return jsonify({"error": "Not found"}), 404

    if new_status:
        if new_status not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status: {new_status}"}), 400

        allowed = ALLOWED_TRANSITIONS.get(outreach.status, set())
        if new_status not in allowed:
            return jsonify({"error": f"Cannot transition from '{outreach.status}' to '{new_status}'"}), 400

        old_status = outreach.status
        outreach.status = new_status
        if new_status == "replied":
            outreach.replied_at = datetime.utcnow()

        _log_activity(db, outreach.id, "status_change",
                      f"{old_status} -> {new_status}",
                      old_status=old_status, new_status=new_status)

    if notes is not None:
        outreach.notes = notes

    if deal_value is not None:
        try:
            outreach.deal_value = float(deal_value)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid deal_value"}), 400

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to update outreach_id=%d: %s", outreach_id, exc)
        return jsonify({"error": "Update failed"}), 500

    return jsonify({"ok": True, "status": outreach.status})


@sponsor_bp.route("/api/sponsor-agent/stats")
def api_stats():
    """Pipeline stats."""
    auth_err = _check_admin()
    if auth_err:
        return auth_err

    from app import db
    from models import SponsorOutreach
    from sqlalchemy import func

    status_counts = (
        db.session.query(SponsorOutreach.status, func.count(SponsorOutreach.id))
        .filter_by(is_deleted=False)
        .group_by(SponsorOutreach.status)
        .all()
    )

    stats = {s: 0 for s in VALID_STATUSES}
    total = 0
    for status, cnt in status_counts:
        if status in stats:
            stats[status] = cnt
        total += cnt

    revenue_result = (
        db.session.query(func.coalesce(func.sum(SponsorOutreach.deal_value), 0))
        .filter_by(status="closed", is_deleted=False)
        .scalar()
    )

    return jsonify({
        "total": total,
        "by_status": stats,
        "revenue": float(revenue_result),
    })
