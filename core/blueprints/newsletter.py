"""
NEWSLETTER BLUEPRINT — Protocol Pulse
======================================
Routes:
  GET  /newsletter              — Landing page (hero + preview + stats)
  POST /newsletter/subscribe    — Subscribe with Resend welcome email
  GET  /newsletter/unsubscribe  — One-click unsubscribe by token
"""

import os
import logging
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, render_template_string

logger = logging.getLogger(__name__)

newsletter_bp = Blueprint("newsletter_main", __name__)

SITE_URL = os.environ.get("SITE_URL", "https://protocolpulse.io")
FROM_EMAIL = "pulse@protocolpulse.io"
RESEND_BASE = "https://api.resend.com"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _resend_key() -> str:
    return os.environ.get("RESEND_API_KEY", "")


def _get_subscriber_count() -> int:
    try:
        from models import NewsletterSubscriber
        return NewsletterSubscriber.query.filter_by(subscribed=True).count()
    except Exception as e:
        logger.warning("subscriber_count error: %s", e)
        return 0


def _get_preview_articles(limit: int = 5):
    try:
        from models import Article
        arts = (
            Article.query
            .filter_by(published=True)
            .order_by(Article.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": a.id,
                "title": a.title or "Untitled",
                "summary": (a.summary or a.content or "")[:200],
                "category": getattr(a, "category", "news") or "news",
                "created_at": a.created_at,
            }
            for a in arts
        ]
    except Exception as e:
        logger.warning("preview_articles error: %s", e)
        return []


def _get_signal_score() -> dict:
    """Return latest sentiment signal or safe defaults."""
    try:
        from app import db
        from sqlalchemy import text as _text
        row = db.session.execute(_text(
            "SELECT score, narrative FROM sentiment_reports ORDER BY created_at DESC LIMIT 1"
        )).fetchone()
        if row:
            score = int(row[0] or 50)
            label = "BULLISH" if score >= 60 else ("BEARISH" if score <= 40 else "NEUTRAL")
            return {"score": score, "label": label, "narrative": row[1] or ""}
    except Exception:
        pass
    return {"score": 50, "label": "NEUTRAL", "narrative": ""}


def _get_btc_price() -> dict:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json().get("bitcoin", {})
            price = data.get("usd", 0)
            change = data.get("usd_24h_change", 0.0)
            sign = "+" if change >= 0 else ""
            return {
                "price": f"${price:,.0f}",
                "change": f"{sign}{change:.1f}%",
                "positive": change >= 0,
            }
    except Exception:
        pass
    return {"price": "$—", "change": "—", "positive": True}


def _get_total_article_count() -> int:
    try:
        from models import Article
        return Article.query.filter_by(published=True).count()
    except Exception:
        return 1300


def _send_welcome_email(email: str, unsubscribe_token: str) -> bool:
    """Send Resend welcome email to new subscriber."""
    key = _resend_key()
    if not key:
        logger.warning("RESEND_API_KEY not set — welcome email skipped")
        return False

    unsub_url = f"{SITE_URL}/unsubscribe?token={unsubscribe_token}"
    today_str = datetime.utcnow().strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Welcome to Protocol Pulse</title>
</head>
<body style="margin:0;padding:0;background:#080808;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#080808;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:#0d0d0d;
                      border:1px solid #1e1e1e;border-radius:8px;overflow:hidden;">

          <!-- HEADER -->
          <tr>
            <td style="padding:32px;background:linear-gradient(135deg,#0d0d0d 0%,#130000 100%);
                       border-bottom:2px solid #dc2626;text-align:center;">
              <p style="margin:0 0 6px;font-size:24px;font-weight:800;
                         letter-spacing:4px;color:#dc2626;font-family:monospace;">
                PROTOCOL PULSE
              </p>
              <p style="margin:0;font-size:12px;color:#555;
                         text-transform:uppercase;letter-spacing:2px;">
                Bitcoin Intelligence
              </p>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:40px 32px;">
              <h1 style="margin:0 0 16px;font-size:26px;font-weight:700;color:#fff;line-height:1.3;">
                You're in the signal.
              </h1>
              <p style="margin:0 0 20px;font-size:15px;color:#b0b0b0;line-height:1.7;">
                Welcome to the <strong style="color:#fff;">Protocol Pulse</strong> daily briefing.
                Every morning you'll receive 5 minutes of distilled Bitcoin intelligence —
                top stories, network stats, and our Signal score — curated from 80+ sources.
              </p>

              <!-- What to expect -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#111;border:1px solid #1e1e1e;
                            border-radius:6px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 12px;font-size:11px;text-transform:uppercase;
                               letter-spacing:2px;color:#dc2626;font-weight:700;">
                      WHAT YOU'LL RECEIVE
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; <strong>1 Lead Story</strong> — deep analysis, 2-sentence brief
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; <strong>4 Supporting Stories</strong> — what you need to know
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; <strong>Network Stat of the Day</strong> — hashrate, difficulty, mempool
                    </p>
                    <p style="margin:0;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; <strong>Oracle Signal</strong> — market intelligence score
                    </p>
                  </td>
                </tr>
              </table>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <a href="{SITE_URL}"
                       style="display:inline-block;padding:14px 36px;
                              background:#dc2626;color:#fff;font-size:15px;
                              font-weight:700;text-decoration:none;
                              border-radius:6px;letter-spacing:0.5px;">
                      Read Today's Briefing &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0;font-size:13px;color:#666;text-align:center;">
                First issue arrives tomorrow morning (UTC). Stay sovereign.
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #1a1a1a;
                       background:#0a0a0a;text-align:center;">
              <p style="margin:0 0 8px;font-size:12px;color:#444;">
                You subscribed to Protocol Pulse on {today_str}.
              </p>
              <p style="margin:0;font-size:12px;color:#444;">
                <a href="{unsub_url}"
                   style="color:#dc2626;text-decoration:none;">Unsubscribe</a>
                &nbsp;&bull;&nbsp;
                <a href="{SITE_URL}" style="color:#555;text-decoration:none;">
                  protocolpulse.io
                </a>
              </p>
              <p style="margin:8px 0 0;font-size:11px;color:#333;">
                Protocol Pulse by Consensus Protocol LLC, Naples FL
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    try:
        resp = requests.post(
            f"{RESEND_BASE}/emails",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [email],
                "subject": "Welcome to Protocol Pulse — You're in the signal ⚡",
                "html": html,
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info("Welcome email sent to %s", email)
            return True
        logger.warning("Welcome email failed for %s: HTTP %s", email, resp.status_code)
        return False
    except Exception as e:
        logger.error("Welcome email exception for %s: %s", email, e)
        return False


# ── Routes ────────────────────────────────────────────────────────────────────

@newsletter_bp.route("/newsletter")
def newsletter_page():
    """Newsletter landing page — hero + preview + stats."""
    subscriber_count = _get_subscriber_count()
    articles = _get_preview_articles(5)
    signal = _get_signal_score()
    btc = _get_btc_price()
    total_articles = _get_total_article_count()
    today_str = datetime.utcnow().strftime("%B %d, %Y")

    return render_template(
        "newsletter.html",
        subscriber_count=subscriber_count,
        articles=articles,
        signal=signal,
        btc=btc,
        total_articles=total_articles,
        today_str=today_str,
    )


@newsletter_bp.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    """
    POST /newsletter/subscribe
    Accepts JSON {email} or form email=...
    Saves subscriber + sends Resend welcome email.
    Returns JSON for AJAX or redirects for plain form.
    """
    try:
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            email = str(payload.get("email", "")).strip().lower()
            is_ajax = True
        else:
            email = str(request.form.get("email", "")).strip().lower()
            is_ajax = False

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            if is_ajax:
                return jsonify({"success": False, "message": "Valid email address required"}), 400
            return redirect(url_for("newsletter_main.newsletter_page"))

        from services.newsletter_service import subscribe
        success, msg = subscribe(email, source="newsletter_page")

        if success:
            # Send welcome email for new subscribers only
            if msg == "subscribed":
                try:
                    from models import NewsletterSubscriber
                    sub = NewsletterSubscriber.query.filter_by(email=email).first()
                    if sub and sub.unsubscribe_token:
                        _send_welcome_email(email, sub.unsubscribe_token)
                except Exception as we:
                    logger.warning("Welcome email lookup failed: %s", we)

            if is_ajax:
                message = (
                    "You're already subscribed!"
                    if msg == "already_subscribed"
                    else "Check your inbox to confirm. Welcome to the signal."
                )
                return jsonify({"success": True, "message": message, "status": msg})

            return redirect(url_for("newsletter_main.newsletter_page") + "?subscribed=1")

        if is_ajax:
            return jsonify({"success": False, "message": "Could not subscribe — please try again"}), 400

        return redirect(url_for("newsletter_main.newsletter_page") + "?error=1")

    except Exception as e:
        logger.error("/newsletter/subscribe error: %s", e)
        if request.is_json:
            return jsonify({"success": False, "message": "Internal error"}), 500
        return redirect(url_for("newsletter_main.newsletter_page"))


_UNSUB_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ title }} — Protocol Pulse</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#080808;color:#e0e0e0;
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;
         display:flex;align-items:center;justify-content:center;
         min-height:100vh;padding:20px}
    .card{background:#0d0d0d;border:1px solid #1e1e1e;border-radius:8px;
          max-width:480px;width:100%;padding:48px 40px;text-align:center}
    .logo{font-size:20px;font-weight:800;letter-spacing:3px;color:#dc2626;
          margin-bottom:32px;font-family:monospace}
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


@newsletter_bp.route("/newsletter/unsubscribe")
def newsletter_unsubscribe():
    """GET /newsletter/unsubscribe?token=xxx — CAN-SPAM one-click unsubscribe."""
    token = request.args.get("token", "").strip()
    try:
        from services.newsletter_service import unsubscribe_by_token
        success, msg = unsubscribe_by_token(token)

        if success:
            if msg == "already_unsubscribed":
                return render_template_string(
                    _UNSUB_PAGE,
                    icon="✓",
                    title="Already Unsubscribed",
                    message="You're not receiving Protocol Pulse emails.",
                )
            return render_template_string(
                _UNSUB_PAGE,
                icon="✓",
                title="Unsubscribed",
                message="You've been removed from Protocol Pulse. No further emails will be sent.",
            )

        if msg == "not_found":
            return render_template_string(
                _UNSUB_PAGE,
                icon="⚠",
                title="Link Not Found",
                message=(
                    "This unsubscribe link is invalid or has already been used. "
                    "If you're still receiving emails, contact us at "
                    "<a href='mailto:pulse@protocolpulse.io'>pulse@protocolpulse.io</a>."
                ),
            ), 404

        return render_template_string(
            _UNSUB_PAGE, icon="⚠", title="Error",
            message="Something went wrong. Please try again.",
        ), 500

    except Exception as e:
        logger.error("/newsletter/unsubscribe error: %s", e)
        return render_template_string(
            _UNSUB_PAGE, icon="⚠", title="Error",
            message="Something went wrong. Please try again.",
        ), 500
