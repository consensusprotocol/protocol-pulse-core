"""
B1 NEWSLETTER SERVICE — Protocol Pulse
=======================================
Gospel: GOSPEL.md (b1-newsletter)
Laws:
  1. Resend API only (RESEND_API_KEY in .env)
  2. One newsletter per day — never two in the same day
  3. Newsletter format: subject with BTC price, top story 2-sentence,
     4 others 1-sentence, network stat, oracle signal, CTA, footer
  4. Unsubscribe must work (CAN-SPAM) — UUID token per subscriber
"""

import os
import uuid
import secrets
import logging
import requests
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

FROM_EMAIL = "pulse@protocolpulse.io"
SITE_URL = os.environ.get("SITE_URL", "https://protocolpulse.io")
NOSTR_NPUB = os.environ.get("NOSTR_NPUB", "npub1a38uwcec9u4pqd4dutezcfg3ujfapfm90vzzjtkq9cs2u5tws50stujyhm")
RESEND_BASE = "https://api.resend.com"
RESEND_TIMEOUT = 30  # seconds


def _resend_api_key() -> str:
    """Read RESEND_API_KEY at call time (supports late .env loading)."""
    return os.environ.get("RESEND_API_KEY", "")


# ── Subscriber management ────────────────────────────────────────────────────

def subscribe(email: str, source: str = "api") -> Tuple[bool, str]:
    """
    Double opt-in subscribe. Returns (success, status).
    Status values: 'already_subscribed', 'check_email', 'check_email_resent'.
    Sends confirmation email via Resend. Subscriber is NOT confirmed until
    they click the link (GET /newsletter/confirm?token=xxx).
    """
    from app import db
    from models import NewsletterSubscriber

    email = email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return False, "Invalid email address"

    try:
        existing = NewsletterSubscriber.query.filter_by(email=email).first()
        if existing:
            if existing.confirmed and existing.subscribed:
                return True, "already_subscribed"
            if not existing.confirmed:
                # Resend confirmation email
                _send_confirmation_email(email, existing.confirmation_token)
                return True, "check_email"
            # Was unsubscribed — re-subscribe but require re-confirm
            existing.confirmed = False
            existing.confirmation_token = secrets.token_urlsafe(32)
            existing.subscribed = True
            existing.unsubscribed_at = None
            existing.subscribed_at = datetime.utcnow()
            db.session.commit()
            _send_confirmation_email(email, existing.confirmation_token)
            return True, "check_email"

        unsub_token = str(uuid.uuid4())
        confirm_token = secrets.token_urlsafe(32)
        sub = NewsletterSubscriber(
            email=email,
            unsubscribe_token=unsub_token,
            confirmation_token=confirm_token,
            confirmed=False,
            subscribed=True,
            source=source,
        )
        db.session.add(sub)
        db.session.commit()
        logger.info(f"New subscriber (pending confirm): {email} (source={source})")
        _send_confirmation_email(email, confirm_token)
        return True, "check_email"

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"subscribe error for {email}: {e}")
        return False, "database_error"


def confirm_subscriber(token: str) -> Tuple[bool, str]:
    """
    Confirm a subscriber by their confirmation token.
    Returns (success, status): 'confirmed', 'already_confirmed', 'not_found'.
    Sends welcome email on first confirmation.
    """
    from app import db
    from models import NewsletterSubscriber

    if not token:
        return False, "not_found"

    try:
        sub = NewsletterSubscriber.query.filter_by(confirmation_token=token).first()
        if not sub:
            return False, "not_found"
        if sub.confirmed:
            return True, "already_confirmed"

        sub.confirmed = True
        sub.confirmed_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"Subscriber confirmed: {sub.email}")

        # Send welcome email
        _send_welcome_email(sub.email, sub.unsubscribe_token)
        return True, "confirmed"

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"confirm_subscriber error: {e}")
        return False, "database_error"


def _send_confirmation_email(email: str, confirmation_token: str) -> bool:
    """Send double opt-in confirmation email via Resend."""
    key = _resend_api_key()
    if not key:
        logger.warning("RESEND_API_KEY not set — confirmation email skipped")
        return False

    confirm_url = f"{SITE_URL}/newsletter/confirm?token={confirmation_token}"

    from services.email_templates import confirmation_email
    tmpl = confirmation_email(confirm_url, email, SITE_URL)

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
                "subject": tmpl["subject"],
                "html": tmpl["html"],
            },
            timeout=RESEND_TIMEOUT,
        )
        if resp.status_code in (200, 201):
            logger.info("Confirmation email sent to %s", email)
            return True
        logger.warning("Confirmation email failed for %s: HTTP %s", email, resp.status_code)
        return False
    except Exception as e:
        logger.error("Confirmation email exception for %s: %s", email, e)
        return False


def _send_welcome_email(email: str, unsubscribe_token: str) -> bool:
    """Send welcome email after confirmation via Resend."""
    key = _resend_api_key()
    if not key:
        logger.warning("RESEND_API_KEY not set — welcome email skipped")
        return False

    unsub_url = f"{SITE_URL}/newsletter/unsubscribe?token={unsubscribe_token}"

    from services.email_templates import welcome_email
    tmpl = welcome_email(unsub_url, SITE_URL)

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
                "subject": tmpl["subject"],
                "html": tmpl["html"],
            },
            timeout=RESEND_TIMEOUT,
        )
        if resp.status_code in (200, 201):
            logger.info("Welcome email sent to %s", email)
            return True
        logger.warning("Welcome email failed for %s: HTTP %s", email, resp.status_code)
        return False
    except Exception as e:
        logger.error("Welcome email exception for %s: %s", email, e)
        return False


def unsubscribe_by_token(token: str) -> Tuple[bool, str]:
    """
    Unsubscribe a user by their token. Returns (success, message).
    """
    from app import db
    from models import NewsletterSubscriber

    if not token:
        return False, "missing_token"

    try:
        sub = NewsletterSubscriber.query.filter_by(
            unsubscribe_token=token
        ).first()
        if not sub:
            return False, "not_found"
        if not sub.subscribed:
            return True, "already_unsubscribed"

        sub.subscribed = False
        sub.unsubscribed_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"Unsubscribed: {sub.email}")
        return True, "unsubscribed"

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"unsubscribe_by_token error: {e}")
        return False, "database_error"


def already_sent_today() -> bool:
    """
    LAW 2: One newsletter per day. Returns True if we already sent today.
    """
    from models import NewsletterSend

    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = NewsletterSend.query.filter(
            NewsletterSend.sent_at >= today_start
        ).count()
        return count > 0
    except Exception as e:
        logger.error(f"already_sent_today check failed: {e}")
        # Be conservative — don't block if we can't check
        return False


# ── Content assembly ─────────────────────────────────────────────────────────

def _get_btc_price() -> Tuple[str, str]:
    """Returns (price_str, change_str) — e.g. ('$95,420', '+2.3%')."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json().get("bitcoin", {})
            price = data.get("usd", 0)
            change = data.get("usd_24h_change", 0.0)
            price_str = f"${price:,.0f}"
            sign = "+" if change >= 0 else ""
            change_str = f"{sign}{change:.1f}%"
            return price_str, change_str
    except Exception as e:
        logger.warning(f"BTC price fetch failed: {e}")
    return "$—", "—"


def _get_network_stat() -> str:
    """Return network stat of the day (hashrate or difficulty) as a string."""
    try:
        r = requests.get(
            "https://blockchain.info/q/getdifficulty",
            timeout=8,
        )
        if r.status_code == 200:
            difficulty = float(r.text.strip())
            if difficulty > 1e12:
                stat = f"{difficulty / 1e12:.2f}T"
            elif difficulty > 1e9:
                stat = f"{difficulty / 1e9:.2f}B"
            else:
                stat = f"{difficulty:,.0f}"
            return f"Difficulty: {stat}"
    except Exception as e:
        logger.warning(f"Network stat fetch failed: {e}")

    # Fallback: try hashrate
    try:
        r = requests.get(
            "https://blockchain.info/q/hashrate",
            timeout=8,
        )
        if r.status_code == 200:
            hr = float(r.text.strip())
            hr_eh = hr / 1e6  # convert GH/s → EH/s
            return f"Hashrate: {hr_eh:.1f} EH/s"
    except Exception as e:
        logger.warning(f"Hashrate fetch failed: {e}")

    return "Network: Online"


def _get_oracle_signal() -> str:
    """Return today's Oracle signal text from daily_signals.json."""
    try:
        signals_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "intelligence", "daily_signals.json"
        )
        signals_path = os.path.normpath(signals_path)
        if os.path.exists(signals_path):
            import json

            with open(signals_path) as f:
                data = json.load(f)
            topics = data.get("topics", [])
            if topics:
                t = topics[0]
                sentiment = t.get("sentiment", "neutral").upper()
                topic = t.get("topic", "Bitcoin")
                score = t.get("velocity_score", 0)
                return f"{topic.title()} — {sentiment} (velocity {score}/100)"
    except Exception as e:
        logger.warning(f"Oracle signal read failed: {e}")
    return "Signal: Accumulation zone active"


def _get_articles() -> List[Dict]:
    """
    Return top 5 articles from the last 24h — first is the lead story,
    next 4 are supporting.
    """
    from app import db
    from models import Article
    from datetime import timedelta

    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        articles = (
            Article.query.filter(
                Article.published == True,
                Article.created_at >= cutoff,
            )
            .order_by(Article.created_at.desc())
            .limit(10)
            .all()
        )

        if not articles:
            # Fallback: last 5 published articles regardless of date
            articles = (
                Article.query.filter_by(published=True)
                .order_by(Article.created_at.desc())
                .limit(5)
                .all()
            )

        result = []
        for a in articles[:5]:
            summary = a.summary or (a.content[:300] if a.content else "") or ""
            result.append(
                {
                    "id": a.id,
                    "title": a.title or "Untitled",
                    "summary": summary,
                    "url": f"{SITE_URL}/article/{a.id}",
                    "category": getattr(a, "category", "news"),
                }
            )
        return result

    except Exception as e:
        logger.error(f"_get_articles failed: {e}")
        return []


def _truncate_to_sentences(text: str, n: int) -> str:
    """Return first n sentences from text."""
    if not text:
        return ""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n]).strip()


# ── HTML builder ─────────────────────────────────────────────────────────────

def build_newsletter_html(
    articles: List[Dict],
    btc_price: str,
    btc_change: str,
    network_stat: str,
    oracle_signal: str,
    unsubscribe_url: str,
    date_str: str,
) -> str:
    """Build the full newsletter HTML per LAW 3 format."""

    # Lead story
    lead = articles[0] if articles else None
    others = articles[1:5]

    lead_html = ""
    if lead:
        lead_summary_2 = _truncate_to_sentences(lead["summary"], 2)
        lead_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
          <tr>
            <td style="border-left:3px solid #dc2626; padding:0 0 0 16px;">
              <p style="margin:0 0 6px; font-size:11px; text-transform:uppercase;
                         letter-spacing:1.5px; color:#dc2626; font-weight:700;">
                TOP STORY
              </p>
              <a href="{lead['url']}"
                 style="color:#ffffff; font-size:19px; font-weight:700;
                        text-decoration:none; line-height:1.35; display:block;
                        margin-bottom:10px;">
                {lead['title']}
              </a>
              <p style="margin:0; color:#b0b0b0; font-size:14px; line-height:1.65;">
                {lead_summary_2}
              </p>
            </td>
          </tr>
        </table>"""

    others_html = ""
    for art in others:
        one_sentence = _truncate_to_sentences(art["summary"], 1)
        others_html += f"""
        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin-bottom:16px; border-bottom:1px solid #1e1e1e; padding-bottom:16px;">
          <tr>
            <td>
              <a href="{art['url']}"
                 style="color:#e0e0e0; font-size:15px; font-weight:600;
                        text-decoration:none; display:block; margin-bottom:6px;
                        line-height:1.4;">
                {art['title']}
              </a>
              <p style="margin:0; color:#888; font-size:13px; line-height:1.55;">
                {one_sentence}
              </p>
            </td>
          </tr>
        </table>"""

    change_color = "#22c55e" if "+" in btc_change else "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Protocol Pulse — {date_str}</title>
  <!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#080808;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background-color:#080808;">
    <tr>
      <td align="center" style="padding:32px 16px;">

        <!-- WRAPPER -->
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px; width:100%;
                      background-color:#0d0d0d;
                      border:1px solid #1e1e1e;
                      border-radius:8px;
                      overflow:hidden;">

          <!-- HEADER -->
          <tr>
            <td style="padding:28px 32px 20px;
                       background:linear-gradient(135deg,#0d0d0d 0%,#130000 100%);
                       border-bottom:2px solid #dc2626;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0 0 4px; font-size:22px; font-weight:800;
                               letter-spacing:3px; color:#dc2626;">
                      PROTOCOL PULSE
                    </p>
                    <p style="margin:0; font-size:12px; color:#555;
                               text-transform:uppercase; letter-spacing:1px;">
                      Bitcoin Intelligence Brief &mdash; {date_str}
                    </p>
                  </td>
                  <td align="right" style="white-space:nowrap;">
                    <p style="margin:0; font-size:20px; font-weight:800; color:#fff;">
                      {btc_price}
                    </p>
                    <p style="margin:0; font-size:13px; font-weight:700;
                               color:{change_color};">
                      {btc_change}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ARTICLES -->
          <tr>
            <td style="padding:28px 32px 8px;">
              {lead_html}
              {others_html}
            </td>
          </tr>

          <!-- NETWORK STAT -->
          <tr>
            <td style="padding:0 32px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#111; border:1px solid #1e1e1e;
                            border-radius:6px; margin-bottom:16px;">
                <tr>
                  <td style="padding:14px 18px;">
                    <p style="margin:0 0 3px; font-size:10px; text-transform:uppercase;
                               letter-spacing:1.5px; color:#555; font-weight:700;">
                      Network Stat of the Day
                    </p>
                    <p style="margin:0; font-size:15px; font-weight:700;
                               color:#e0e0e0; font-family:monospace;">
                      {network_stat}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ORACLE SIGNAL -->
          <tr>
            <td style="padding:0 32px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:linear-gradient(135deg,#130000,#0d0d0d);
                            border:1px solid #3b0000; border-radius:6px;
                            margin-bottom:20px;">
                <tr>
                  <td style="padding:14px 18px;">
                    <p style="margin:0 0 3px; font-size:10px; text-transform:uppercase;
                               letter-spacing:1.5px; color:#dc2626; font-weight:700;">
                      &#9650; Oracle Signal
                    </p>
                    <p style="margin:0; font-size:14px; color:#d0d0d0; line-height:1.5;">
                      {oracle_signal}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td style="padding:4px 32px 28px; text-align:center;">
              <a href="{SITE_URL}"
                 style="display:inline-block; padding:13px 32px;
                        background:#dc2626; color:#fff; font-size:14px;
                        font-weight:700; text-decoration:none;
                        border-radius:6px; letter-spacing:0.5px;">
                Read Full Briefing at protocolpulse.io &rarr;
              </a>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 32px; border-top:1px solid #1a1a1a;
                       background:#0a0a0a; text-align:center;">
              <p style="margin:0 0 8px; font-size:12px; color:#444;">
                You received this because you subscribed to Protocol Pulse.
              </p>
              <p style="margin:0 0 8px; font-size:12px; color:#444;">
                <a href="{unsubscribe_url}"
                   style="color:#dc2626; text-decoration:none;">
                  Unsubscribe
                </a>
                &nbsp;&bull;&nbsp;
                <a href="{SITE_URL}"
                   style="color:#555; text-decoration:none;">
                  protocolpulse.io
                </a>
              </p>
              <p style="margin:0; font-size:11px; color:#333;
                         font-family:monospace; word-break:break-all;">
                {NOSTR_NPUB}
              </p>
            </td>
          </tr>

        </table>
        <!-- /WRAPPER -->

      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Resend sender ─────────────────────────────────────────────────────────────

def _send_via_resend(to: str, subject: str, html: str, idempotency_key: str = "") -> Dict:
    """Send one email via Resend. Returns {success, id, error}."""
    key = _resend_api_key()
    if not key:
        return {"success": False, "error": "RESEND_API_KEY not set"}
    try:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        r = requests.post(
            f"{RESEND_BASE}/emails",
            headers=headers,
            json={
                "from": FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=RESEND_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return {"success": True, "id": r.json().get("id")}
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _send_batch_via_resend(batch: List[Dict], idempotency_key: str = "") -> Dict:
    """
    Send up to 100 emails in one Resend batch call.
    batch: [{"from","to","subject","html"}, ...]
    """
    key = _resend_api_key()
    if not key:
        return {"success": False, "error": "RESEND_API_KEY not set"}
    try:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        r = requests.post(
            f"{RESEND_BASE}/emails/batch",
            headers=headers,
            json=batch,
            timeout=60,
        )
        if r.status_code in (200, 201):
            data = r.json()
            ids = [item.get("id") for item in data.get("data", [])]
            return {"success": True, "count": len(ids), "ids": ids}
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Main orchestration ────────────────────────────────────────────────────────

def send_daily_newsletter(force: bool = False) -> Dict:
    """
    Assemble and send the daily newsletter.
    LAW 2: Refuses if already sent today (unless force=True).
    Returns result dict with success, recipient_count, subject, error.
    """
    from app import db
    from models import NewsletterSubscriber, NewsletterSend

    # LAW 2 guard
    if not force and already_sent_today():
        msg = "Newsletter already sent today — skipping (LAW 2)"
        logger.info(msg)
        return {"success": False, "error": msg, "skipped": True}

    # Assemble content
    try:
        btc_price, btc_change = _get_btc_price()
        network_stat = _get_network_stat()
        oracle_signal = _get_oracle_signal()
        articles = _get_articles()
    except Exception as e:
        logger.error(f"Content assembly failed: {e}")
        return {"success": False, "error": f"Content assembly error: {e}"}

    if not articles:
        return {"success": False, "error": "No articles available to send"}

    # Build subject per LAW 3
    today = datetime.utcnow()
    date_str = today.strftime("%B %d, %Y")
    date_key = today.strftime("%Y-%m-%d")  # used as idempotency key base
    subject = f"Protocol Pulse — {date_str} | BTC: {btc_price} {btc_change}"

    # Load active confirmed subscribers only (double opt-in)
    try:
        subscribers = NewsletterSubscriber.query.filter_by(subscribed=True, confirmed=True).all()
    except Exception as e:
        logger.error(f"Subscriber query failed: {e}")
        return {"success": False, "error": f"Subscriber query error: {e}"}

    if not subscribers:
        return {"success": False, "error": "No active subscribers"}

    # Send per-subscriber (personalised unsubscribe token)
    total_sent = 0
    errors = []
    batch_size = 100

    # Build all emails
    all_emails = []
    for sub in subscribers:
        unsub_url = f"{SITE_URL}/unsubscribe?token={sub.unsubscribe_token}"
        html = build_newsletter_html(
            articles=articles,
            btc_price=btc_price,
            btc_change=btc_change,
            network_stat=network_stat,
            oracle_signal=oracle_signal,
            unsubscribe_url=unsub_url,
            date_str=date_str,
        )
        all_emails.append(
            {
                "from": FROM_EMAIL,
                "to": [sub.email],
                "subject": subject,
                "html": html,
            }
        )

    # Send in batches of 100 with per-batch idempotency keys
    for i in range(0, len(all_emails), batch_size):
        chunk = all_emails[i : i + batch_size]
        batch_num = i // batch_size
        idempotency_key = f"pp-newsletter-{date_key}-batch{batch_num}"
        result = _send_batch_via_resend(chunk, idempotency_key=idempotency_key)
        if result.get("success"):
            total_sent += result.get("count", len(chunk))
        else:
            err = result.get("error", "unknown")
            logger.error(
                "newsletter batch %d failed (idempotency_key=%s): %s",
                batch_num, idempotency_key, err
            )
            errors.append(err)

    # Record send in DB
    try:
        send_record = NewsletterSend(
            subject=subject,
            resend_batch_id=",".join(
                str(e) for e in (errors if errors else ["ok"])
            ),
            recipient_count=total_sent,
        )
        db.session.add(send_record)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"Failed to record send: {e}")

    success = total_sent > 0
    result = {
        "success": success,
        "recipient_count": total_sent,
        "total_subscribers": len(subscribers),
        "subject": subject,
    }
    if errors:
        result["errors"] = errors
    logger.info(f"Newsletter sent: {result}")
    return result


def send_test_newsletter(to_email: str) -> Dict:
    """
    Send a test newsletter to a single address (admin use).
    Does NOT write to newsletter_sends or enforce LAW 2.
    """
    try:
        btc_price, btc_change = _get_btc_price()
        network_stat = _get_network_stat()
        oracle_signal = _get_oracle_signal()
        articles = _get_articles()
    except Exception as e:
        return {"success": False, "error": f"Content assembly error: {e}"}

    today = datetime.utcnow()
    date_str = today.strftime("%B %d, %Y")
    subject = f"[TEST] Protocol Pulse — {date_str} | BTC: {btc_price} {btc_change}"
    unsub_url = f"{SITE_URL}/unsubscribe?token=test-token"

    html = build_newsletter_html(
        articles=articles or [
            {
                "id": 0,
                "title": "Test Article — No articles in DB",
                "summary": "This is a test send. No real articles are available.",
                "url": SITE_URL,
                "category": "test",
            }
        ],
        btc_price=btc_price,
        btc_change=btc_change,
        network_stat=network_stat,
        oracle_signal=oracle_signal,
        unsubscribe_url=unsub_url,
        date_str=date_str,
    )

    return _send_via_resend(to_email, subject, html)
