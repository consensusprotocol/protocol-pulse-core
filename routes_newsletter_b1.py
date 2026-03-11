"""
B1 NEWSLETTER ROUTES — Protocol Pulse
======================================
Routes:
  POST /api/newsletter/subscribe   — {email} → subscribe
  GET  /unsubscribe                — ?token=xxx → unsubscribe (CAN-SPAM LAW 4)
  POST /api/newsletter/send        — Admin trigger (auth required)
"""

import os
import logging
from flask import Blueprint, jsonify, request, render_template_string, abort

logger = logging.getLogger(__name__)

newsletter_b1_bp = Blueprint("newsletter_b1", __name__)

# ── Admin auth ─────────────────────────────────────────────────────────────
_ADMIN_TOKEN = os.environ.get(
    "NEWSLETTER_ADMIN_TOKEN",
    "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552",
)

def _is_authorized(req) -> bool:
    auth = req.headers.get("Authorization", "")
    payload = (req.get_json(silent=True) or {}) if req.is_json else {}
    token = payload.get("token", "") or req.form.get("token", "")
    return (
        _ADMIN_TOKEN in auth
        or token == _ADMIN_TOKEN
        or req.remote_addr in ("127.0.0.1", "::1")
    )


# ── Subscribe ──────────────────────────────────────────────────────────────

@newsletter_b1_bp.route("/api/newsletter/subscribe", methods=["POST"])
def api_newsletter_subscribe():
    """
    POST /api/newsletter/subscribe
    Body (JSON or form): {email}
    Returns: {success, message}
    """
    try:
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            email = str(payload.get("email", "")).strip()
        else:
            email = str(request.form.get("email", "")).strip()

        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400

        from services.newsletter_service import subscribe

        success, msg = subscribe(email, source="api")

        if success:
            if msg == "already_subscribed":
                message = "You're already subscribed!"
            else:
                message = "Check your inbox to confirm your subscription."
            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "status": msg,
                }
            ), 200

        return (
            jsonify({"success": False, "message": "Could not subscribe — please try again"}),
            400,
        )

    except Exception as e:
        logger.error(f"/api/newsletter/subscribe error: {e}")
        return jsonify({"success": False, "message": "Internal error"}), 500


# ── Unsubscribe ───────────────────────────────────────────────────────────

_UNSUB_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Unsubscribe — Protocol Pulse</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#080808;color:#e0e0e0;
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;
         display:flex;align-items:center;justify-content:center;
         min-height:100vh;padding:20px}
    .card{background:#0d0d0d;border:1px solid #1e1e1e;border-radius:8px;
          max-width:480px;width:100%;padding:48px 40px;text-align:center}
    .logo{font-size:20px;font-weight:800;letter-spacing:3px;color:#dc2626;
          margin-bottom:32px}
    .icon{font-size:40px;margin-bottom:20px}
    h1{font-size:22px;font-weight:700;margin-bottom:12px}
    p{font-size:14px;color:#888;line-height:1.6;margin-bottom:24px}
    a{color:#dc2626;text-decoration:none}
    a:hover{text-decoration:underline}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">PROTOCOL PULSE</div>
    <div class="icon">{{ icon }}</div>
    <h1>{{ title }}</h1>
    <p>{{ message }}</p>
    <p><a href="/">Return to Protocol Pulse &rarr;</a></p>
  </div>
</body>
</html>"""


@newsletter_b1_bp.route("/unsubscribe", methods=["GET"])
def unsubscribe():
    """
    GET /unsubscribe?token=xxx
    CAN-SPAM compliant one-click unsubscribe.
    """
    token = request.args.get("token", "").strip()

    try:
        from services.newsletter_service import unsubscribe_by_token

        success, msg = unsubscribe_by_token(token)

        if success:
            if msg == "already_unsubscribed":
                return render_template_string(
                    _UNSUB_TEMPLATE,
                    icon="✓",
                    title="Already Unsubscribed",
                    message="You're not receiving Protocol Pulse emails.",
                )
            return render_template_string(
                _UNSUB_TEMPLATE,
                icon="✓",
                title="Unsubscribed",
                message=(
                    "You've been removed from Protocol Pulse. "
                    "No further emails will be sent."
                ),
            )

        if msg == "not_found":
            return render_template_string(
                _UNSUB_TEMPLATE,
                icon="⚠",
                title="Link Not Found",
                message=(
                    "This unsubscribe link is invalid or has already been used. "
                    "If you're still receiving emails, contact us at "
                    "<a href='mailto:pulse@protocolpulse.io'>pulse@protocolpulse.io</a>."
                ),
            ), 404

        return render_template_string(
            _UNSUB_TEMPLATE,
            icon="⚠",
            title="Error",
            message="Something went wrong. Please try again or contact us.",
        ), 500

    except Exception as e:
        logger.error(f"/unsubscribe error: {e}")
        return render_template_string(
            _UNSUB_TEMPLATE,
            icon="⚠",
            title="Error",
            message="Something went wrong. Please try again.",
        ), 500


# ── Admin send trigger ─────────────────────────────────────────────────────

@newsletter_b1_bp.route("/api/newsletter/send", methods=["POST"])
def api_newsletter_send():
    """
    POST /api/newsletter/send
    Admin-only. Triggers daily newsletter send.
    Optional body: {token, force: bool, test_to: email}
    """
    try:
        if not _is_authorized(request):
            return jsonify({"error": "unauthorized"}), 401

        payload = {}
        if request.is_json:
            payload = request.get_json(silent=True) or {}

        force = bool(payload.get("force", False))
        test_to = str(payload.get("test_to", "")).strip()

        from services.newsletter_service import send_daily_newsletter, send_test_newsletter

        if test_to:
            result = send_test_newsletter(test_to)
            result["mode"] = "test"
            return jsonify(result), 200 if result.get("success") else 500

        result = send_daily_newsletter(force=force)
        status = 200 if result.get("success") or result.get("skipped") else 500
        return jsonify(result), status

    except Exception as e:
        logger.error(f"/api/newsletter/send error: {e}")
        return jsonify({"error": str(e)}), 500
