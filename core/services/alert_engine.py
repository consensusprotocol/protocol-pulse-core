"""
SESSION 20 — Alert Engine
Checks BTC price vs active confirmed alerts every 5 minutes.

Run via cron:
  */5 * * * * cd /home/ultron/protocol_pulse && source .env && python3 -m core.services.alert_engine >> logs/alert_engine.log 2>&1

Or call check_alerts() from any app context.
"""
import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
BASE_URL = os.environ.get("BASE_URL", "https://protocolpulse.io")
FROM_EMAIL = "Protocol Pulse <alerts@protocolpulse.io>"

_COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
)
_COINBASE_URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
_HEADERS = {"User-Agent": "ProtocolPulse/2026 AlertEngine"}


# ── Price Fetching ─────────────────────────────────────────────────────────────

def get_current_btc_price():
    """Return (price_usd: float, change_24h: float) or (None, None) on error."""
    # Primary: Coinbase (fast, reliable)
    try:
        r = requests.get(_COINBASE_URL, timeout=6, headers=_HEADERS)
        r.raise_for_status()
        price = float(r.json()["data"]["amount"])
        # Coinbase spot doesn't give 24h change; try CoinGecko for that
        try:
            cg = requests.get(_COINGECKO_URL, timeout=5, headers=_HEADERS)
            cg.raise_for_status()
            change = float(cg.json()["bitcoin"].get("usd_24h_change", 0))
        except Exception:
            change = 0.0
        return price, change
    except Exception as e:
        logger.warning("Coinbase price fetch failed: %s", e)

    # Fallback: CoinGecko
    try:
        r = requests.get(_COINGECKO_URL, timeout=7, headers=_HEADERS)
        r.raise_for_status()
        data = r.json()["bitcoin"]
        return float(data["usd"]), float(data.get("usd_24h_change", 0))
    except Exception as e:
        logger.error("CoinGecko price fetch failed: %s", e)
        return None, None


# ── Email Helpers ──────────────────────────────────────────────────────────────

def _send_via_resend(to_email: str, subject: str, html: str) -> bool:
    """POST to Resend API. Returns True on success."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — email to %s skipped", to_email)
        return False
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"from": FROM_EMAIL, "to": [to_email], "subject": subject, "html": html},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True
        logger.error("Resend API error %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception as e:
        logger.error("Resend request exception: %s", e)
        return False


def send_confirmation_email(alert) -> bool:
    """Send double-opt-in confirmation email for a pending alert."""
    confirm_url = f"{BASE_URL}/api/alerts/verify?token={alert.confirm_token}"
    direction_word = "rises above" if alert.direction == "above" else "drops below"

    html = f"""
    <div style="background:#000;color:#fff;font-family:'Courier New',monospace;padding:40px;max-width:580px;margin:0 auto;">
      <div style="border-left:4px solid #F8C15C;padding-left:20px;margin-bottom:32px;">
        <div style="color:#666;font-size:11px;letter-spacing:3px;text-transform:uppercase;">Protocol Pulse · Alert Confirmation</div>
        <h1 style="color:#F8C15C;font-size:22px;margin:8px 0 0;">Confirm Your BTC Alert</h1>
      </div>
      <p style="color:#ccc;font-size:15px;line-height:1.6;">
        You requested a notification when Bitcoin <strong style="color:#fff;">{direction_word}</strong>
        <span style="color:#F8C15C;font-size:20px;font-weight:bold;">${alert.target_price:,.0f}</span>.
      </p>
      <p style="margin:32px 0;">
        <a href="{confirm_url}"
           style="background:#dc2626;color:#fff;padding:14px 28px;text-decoration:none;display:inline-block;font-weight:bold;letter-spacing:1px;font-size:14px;text-transform:uppercase;">
          CONFIRM ALERT →
        </a>
      </p>
      <hr style="border:none;border-top:1px solid #222;margin:24px 0;">
      <p style="color:#555;font-size:11px;line-height:1.8;">
        This confirmation link expires in 24 hours.<br>
        If you didn't request this alert, you can safely ignore this email.<br>
        <a href="{BASE_URL}/api/alerts/cancel?token={alert.cancel_token}" style="color:#444;">Cancel this alert</a>
      </p>
    </div>
    """
    subject = f"Confirm your BTC alert: ${alert.target_price:,.0f}"
    return _send_via_resend(alert.email, subject, html)


def send_triggered_email(alert, current_price: float, change_24h: float) -> bool:
    """Send email when an alert fires."""
    direction_word = "surpassed" if alert.direction == "above" else "dropped below"
    change_color = "#22c55e" if change_24h >= 0 else "#dc2626"
    change_arrow = "▲" if change_24h >= 0 else "▼"
    cancel_url = f"{BASE_URL}/api/alerts/cancel?token={alert.cancel_token}"

    html = f"""
    <div style="background:#000;color:#fff;font-family:'Courier New',monospace;padding:40px;max-width:580px;margin:0 auto;">
      <div style="border-left:4px solid #dc2626;padding-left:20px;margin-bottom:24px;">
        <div style="color:#dc2626;font-size:11px;letter-spacing:3px;text-transform:uppercase;">⚡ Alert Triggered</div>
        <h1 style="color:#fff;font-size:20px;margin:8px 0 0;">BITCOIN PRICE ALERT</h1>
      </div>
      <p style="color:#ccc;font-size:15px;">
        BTC has <strong style="color:#fff;">{direction_word}</strong> your target of
        <span style="color:#F8C15C;font-size:18px;font-weight:bold;">${alert.target_price:,.0f}</span>
      </p>
      <div style="background:#0a0a0a;border:1px solid #222;padding:20px;margin:24px 0;border-radius:4px;">
        <div style="font-size:36px;font-weight:bold;color:#F8C15C;">${current_price:,.2f}</div>
        <div style="color:{change_color};font-size:16px;margin-top:8px;">
          {change_arrow} {abs(change_24h):.2f}% (24h)
        </div>
      </div>
      <div style="margin-top:24px;">
        <a href="{BASE_URL}/charts" style="color:#F8C15C;text-decoration:none;margin-right:20px;">View Charts →</a>
        <a href="{BASE_URL}/alerts" style="color:#888;text-decoration:none;margin-right:20px;">Set another alert</a>
        <a href="{cancel_url}" style="color:#555;text-decoration:none;">Cancel remaining alerts</a>
      </div>
      <hr style="border:none;border-top:1px solid #222;margin:32px 0 16px;">
      <p style="color:#444;font-size:11px;">
        Protocol Pulse · Bitcoin Intelligence · <a href="{BASE_URL}" style="color:#444;">protocolpulse.io</a>
      </p>
    </div>
    """
    direction_hit = "hit" if alert.direction == "above" else "broken"
    subject = (
        f"⚡ BTC Alert: ${current_price:,.0f} — "
        f"your target of ${alert.target_price:,.0f} was {direction_hit}"
    )
    return _send_via_resend(alert.email, subject, html)


# ── Core Check Loop ────────────────────────────────────────────────────────────

def check_alerts():
    """
    Main alert checking function.
    Must be called inside a Flask app context (or creates its own when run as __main__).
    """
    from core.models import PriceAlert
    from core.app import db

    current_price, change_24h = get_current_btc_price()
    if current_price is None:
        logger.error("Could not fetch BTC price — skipping alert check")
        return

    logger.info("BTC price: $%.2f (24h: %.2f%%) — checking alerts", current_price, change_24h or 0)

    # 1. Expire unconfirmed alerts older than 24 hours
    try:
        expired = PriceAlert.query.filter(
            PriceAlert.confirmed == False,  # noqa: E712
            PriceAlert.expires_at != None,  # noqa: E711
            PriceAlert.expires_at < datetime.utcnow(),
        ).all()
        for alert in expired:
            db.session.delete(alert)
        if expired:
            db.session.commit()
            logger.info("Deleted %d expired unconfirmed alerts", len(expired))
    except Exception as e:
        db.session.rollback()
        logger.error("Error expiring alerts: %s", e)

    # 2. Check active confirmed alerts that haven't fired
    try:
        active_alerts = PriceAlert.query.filter(
            PriceAlert.active == True,    # noqa: E712
            PriceAlert.confirmed == True, # noqa: E712
            PriceAlert.triggered_at == None,  # noqa: E711
        ).all()
        logger.info("Active confirmed alerts: %d", len(active_alerts))
    except Exception as e:
        logger.error("Error querying active alerts: %s", e)
        return

    triggered_count = 0
    for alert in active_alerts:
        should_fire = (
            (alert.direction == "above" and current_price >= alert.target_price) or
            (alert.direction == "below" and current_price <= alert.target_price)
        )
        if not should_fire:
            continue

        try:
            sent = send_triggered_email(alert, current_price, change_24h or 0)
            alert.triggered_at = datetime.utcnow()
            alert.active = False
            alert.triggered = True  # keep legacy field in sync
            db.session.commit()
            triggered_count += 1
            logger.info(
                "Alert %d fired: %s BTC %s $%.0f (price $%.2f) — email sent: %s",
                alert.id, alert.email, alert.direction, alert.target_price, current_price, sent,
            )
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to process alert %d: %s", alert.id, e)

    logger.info("Alert check complete — triggered: %d", triggered_count)


if __name__ == "__main__":
    import sys
    import os
    # Allow running as: python3 -m core.services.alert_engine
    # from the project root
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.app import app
    with app.app_context():
        check_alerts()
