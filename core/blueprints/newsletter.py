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
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, render_template_string, abort

logger = logging.getLogger(__name__)

newsletter_bp = Blueprint("newsletter_main", __name__)

SITE_URL = os.environ.get("SITE_URL", "https://protocolpulse.io")
FROM_EMAIL = "pulse@protocolpulse.io"


def _verify_turnstile(token: str) -> bool:
    """Verify a Cloudflare Turnstile token. Returns True if valid."""
    secret = os.environ.get('TURNSTILE_SECRET_KEY', '')
    if not secret:
        logging.warning("TURNSTILE_SECRET_KEY not set — skipping captcha check")
        return True
    try:
        resp = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': secret, 'response': token},
            timeout=5,
        )
        return resp.json().get('success', False)
    except Exception as e:
        logging.error(f"Turnstile verification error: {e}")
        return False
RESEND_BASE = "https://api.resend.com"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _resend_key() -> str:
    return os.environ.get("RESEND_API_KEY", "")


def _get_subscriber_count() -> int:
    try:
        from models import NewsletterSubscriber
        return NewsletterSubscriber.query.filter_by(confirmed=True, subscribed=True).count()
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
  <title>Your Signal Is Now Active</title>
</head>
<body style="margin:0;padding:0;background:#000000;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#000000;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:#0a0a0a;
                      border:1px solid #1a1a1a;overflow:hidden;">

          <!-- RED TOP BAR -->
          <tr>
            <td style="background:#dc2626;height:3px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- HEADER -->
          <tr>
            <td style="padding:40px 40px 24px;text-align:center;">
              <p style="margin:0 0 6px;font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,Courier,monospace;
                         font-size:13px;font-weight:700;letter-spacing:4px;color:#dc2626;text-transform:uppercase;">
                PROTOCOL PULSE
              </p>
              <p style="margin:0;font-family:'SFMono-Regular',Consolas,monospace;
                         font-size:9px;letter-spacing:3px;color:rgba(255,255,255,0.3);text-transform:uppercase;">
                SOVEREIGN BITCOIN INTELLIGENCE
              </p>
            </td>
          </tr>

          <!-- RED SEPARATOR -->
          <tr>
            <td style="padding:0 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="border-bottom:1px solid #dc2626;height:1px;font-size:0;">&nbsp;</td></tr>
              </table>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <p style="margin:0 0 24px;font-family:'SFMono-Regular',Consolas,monospace;
                         font-size:28px;font-weight:700;color:#ffffff;line-height:1.2;letter-spacing:-0.5px;">
                Your signal is now active.
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#999;line-height:1.8;">
                Every morning at 8am ET, you'll receive what the network saw while you were sleeping.
                No spam. No shilling. Just signal.
              </p>

              <!-- WHAT YOU GET — CLASSIFIED BRIEFING STYLE -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#111;border-left:3px solid #dc2626;margin-bottom:28px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 14px;font-family:'SFMono-Regular',Consolas,monospace;
                               font-size:9px;letter-spacing:3px;color:#dc2626;text-transform:uppercase;font-weight:700;">
                      DAILY BRIEFING CONTENTS
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;font-family:'SFMono-Regular',Consolas,monospace;">
                      &gt; Lead intelligence + 4 supporting signals
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;font-family:'SFMono-Regular',Consolas,monospace;">
                      &gt; Network stat: hashrate, difficulty, mempool
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;font-family:'SFMono-Regular',Consolas,monospace;">
                      &gt; Oracle signal: convergence engine score
                    </p>
                    <p style="margin:0;font-size:14px;color:#d0d0d0;font-family:'SFMono-Regular',Consolas,monospace;">
                      &gt; Satomi's watch: what she sees in the data
                    </p>
                  </td>
                </tr>
              </table>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <a href="{SITE_URL}/intelligence"
                       style="display:inline-block;padding:14px 36px;
                              background:#dc2626;color:#fff;font-size:14px;
                              font-weight:700;text-decoration:none;
                              border-radius:6px;letter-spacing:1px;
                              font-family:'SFMono-Regular',Consolas,monospace;">
                      ENTER THE TERMINAL &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0;font-size:13px;color:#555;text-align:center;
                         font-family:'SFMono-Regular',Consolas,monospace;">
                Stay sovereign. — Satomi
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 40px;border-top:1px solid #1a1a1a;
                       background:#050505;text-align:center;">
              <p style="margin:0 0 8px;font-size:11px;color:#333;">
                You subscribed to Protocol Pulse on {today_str}.
              </p>
              <p style="margin:0;font-size:11px;color:#333;">
                <a href="{unsub_url}" style="color:#dc2626;text-decoration:none;">Unsubscribe</a>
                &nbsp;&bull;&nbsp;
                <a href="{SITE_URL}" style="color:#444;text-decoration:none;">protocolpulse.io</a>
              </p>
              <p style="margin:8px 0 0;font-family:'SFMono-Regular',Consolas,monospace;
                         font-size:10px;letter-spacing:2px;color:#dc2626;">
                Verify. Don't trust.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    payload = {
        "from": FROM_EMAIL,
        "to": [email],
        "subject": "Your signal is now active — Protocol Pulse",
        "html": html,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{RESEND_BASE}/emails",
                headers=headers,
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info("Welcome email sent to %s", email)
                return True
            if attempt == 0:
                logger.warning("Welcome email attempt 1 failed for %s: HTTP %s, retrying...", email, resp.status_code)
                import time
                time.sleep(5)
                continue
            logger.warning("Welcome email failed for %s: HTTP %s", email, resp.status_code)
            return False
        except Exception as e:
            if attempt == 0:
                logger.warning("Welcome email attempt 1 exception for %s: %s, retrying...", email, e)
                import time
                time.sleep(5)
                continue
            logger.error("Welcome email exception for %s: %s", email, e)
            return False
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

    status = request.args.get("status", "")

    return render_template(
        "newsletter.html",
        subscriber_count=subscriber_count,
        articles=articles,
        signal=signal,
        btc=btc,
        total_articles=total_articles,
        today_str=today_str,
        status=status,
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
            cf_token = payload.get("cf-turnstile-response", "")
            is_ajax = True
        else:
            email = str(request.form.get("email", "")).strip().lower()
            cf_token = request.form.get("cf-turnstile-response", "")
            is_ajax = False

        # Cloudflare Turnstile bot check
        if not _verify_turnstile(cf_token):
            if is_ajax:
                return jsonify({"success": False, "message": "CAPTCHA verification failed"}), 403
            return redirect(url_for("newsletter_main.newsletter_page") + "?error=captcha")

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            if is_ajax:
                return jsonify({"success": False, "message": "Valid email address required"}), 400
            return redirect(url_for("newsletter_main.newsletter_page"))

        from services.newsletter_service import subscribe
        success, msg = subscribe(email, source="newsletter_page")

        if success:
            if is_ajax:
                if msg == "already_subscribed":
                    message = "You're already subscribed!"
                else:
                    message = "Check your inbox to confirm your subscription."
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


# ── Double opt-in confirmation ─────────────────────────────────────────────

@newsletter_bp.route("/newsletter/confirm")
def newsletter_confirm():
    """GET /newsletter/confirm?token=xxx — Confirm double opt-in."""
    token = request.args.get("token", "").strip()
    if not token:
        return redirect(url_for("newsletter_main.newsletter_page"))

    try:
        from services.newsletter_service import confirm_subscriber
        success, status = confirm_subscriber(token)

        if success:
            return redirect(url_for("newsletter_main.newsletter_page") + f"?status={status}")

        if status == "not_found":
            return render_template_string(
                _UNSUB_PAGE,
                icon="⚠",
                title="Invalid Link",
                message=(
                    "This confirmation link is invalid or expired. "
                    "Please subscribe again at "
                    "<a href='/newsletter'>protocolpulse.io/newsletter</a>."
                ),
            ), 404

        return render_template_string(
            _UNSUB_PAGE, icon="⚠", title="Error",
            message="Something went wrong. Please try again.",
        ), 500

    except Exception as e:
        logger.error("/newsletter/confirm error: %s", e)
        return render_template_string(
            _UNSUB_PAGE, icon="⚠", title="Error",
            message="Something went wrong. Please try again.",
        ), 500


# ── Admin: send digest ────────────────────────────────────────────────────

_ADMIN_TOKEN = os.environ.get(
    "ADMIN_TOKEN",
    os.environ.get("NEWSLETTER_ADMIN_TOKEN", ""),
)


def _is_admin_authorized(req) -> bool:
    if not _ADMIN_TOKEN:
        return req.remote_addr in ("127.0.0.1", "::1")
    auth = req.headers.get("Authorization", "")
    return f"Bearer {_ADMIN_TOKEN}" == auth or req.remote_addr in ("127.0.0.1", "::1")


@newsletter_bp.route("/api/newsletter/send", methods=["POST"])
def api_newsletter_send():
    """
    POST /api/newsletter/send (Bearer ADMIN_TOKEN)
    Generate digest from last 24h articles, batch send to confirmed subscribers.
    """
    if not _is_admin_authorized(request):
        return jsonify({"error": "unauthorized"}), 401

    try:
        from app import db
        from models import Article, NewsletterSubscriber, NewsletterCampaign
        from services.email_templates import digest_email
        import time

        cutoff = datetime.utcnow() - timedelta(hours=24)
        articles = (
            Article.query
            .filter(Article.published == True, Article.created_at >= cutoff)
            .order_by(Article.created_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            articles = (
                Article.query.filter_by(published=True)
                .order_by(Article.created_at.desc())
                .limit(5)
                .all()
            )

        if not articles:
            return jsonify({"error": "No articles available"}), 400

        art_list = [
            {
                "title": a.title or "Untitled",
                "summary": (a.summary or (a.content[:300] if a.content else ""))[:250],
                "cover_image_url": getattr(a, "cover_image_url", "") or "",
                "url": f"{SITE_URL}/article/{a.id}",
            }
            for a in articles
        ]

        subscribers = NewsletterSubscriber.query.filter_by(
            confirmed=True, subscribed=True
        ).all()

        if not subscribers:
            return jsonify({"error": "No confirmed subscribers"}), 400

        sent = 0
        failed = 0
        key = os.environ.get("RESEND_API_KEY", "")
        batch_size = 100

        for i in range(0, len(subscribers), batch_size):
            chunk = subscribers[i:i + batch_size]
            batch_emails = []
            for sub in chunk:
                unsub_url = f"{SITE_URL}/newsletter/unsubscribe?token={sub.unsubscribe_token}"
                tmpl = digest_email(art_list, unsub_url, SITE_URL)
                batch_emails.append({
                    "from": FROM_EMAIL,
                    "to": [sub.email],
                    "subject": tmpl["subject"],
                    "html": tmpl["html"],
                })

            if key and batch_emails:
                try:
                    resp = requests.post(
                        f"{RESEND_BASE}/emails/batch",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json=batch_emails,
                        timeout=60,
                    )
                    if resp.status_code in (200, 201):
                        sent += len(chunk)
                    else:
                        failed += len(chunk)
                        logger.error("Digest batch failed: HTTP %s", resp.status_code)
                except Exception as be:
                    failed += len(chunk)
                    logger.error("Digest batch exception: %s", be)
            else:
                failed += len(chunk)

            if i + batch_size < len(subscribers):
                time.sleep(1)

        top_headline = art_list[0]["title"]
        status = "sent" if failed == 0 else ("partial" if sent > 0 else "failed")
        campaign = NewsletterCampaign(
            recipient_count=sent,
            failed_count=failed,
            top_headline=top_headline,
            status=status,
        )
        db.session.add(campaign)
        db.session.commit()

        return jsonify({"sent": sent, "failed": failed, "status": status})

    except Exception as e:
        logger.error("/api/newsletter/send error: %s", e)
        return jsonify({"error": str(e)}), 500


@newsletter_bp.route("/api/newsletter/latest-digest")
def api_newsletter_latest_digest():
    """GET /api/newsletter/latest-digest — public preview of last 5 articles as newsletter."""
    try:
        articles = _get_preview_articles(5)
        result = [
            {
                "title": a["title"],
                "summary": a["summary"][:200],
                "category": a["category"],
            }
            for a in articles
        ]
        return jsonify({"articles": result, "count": len(result)})
    except Exception as e:
        logger.error("/api/newsletter/latest-digest error: %s", e)
        return jsonify({"articles": [], "count": 0})
