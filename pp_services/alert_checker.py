"""
Price Alert Checker — runs every 5 minutes via cron.
Checks active alerts against current BTC price and sends Resend emails on trigger.
"""
import logging
import os
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESEND_BASE = "https://api.resend.com"
RESEND_TIMEOUT = 30
FROM_EMAIL = "pulse@protocolpulse.io"
BASE_URL = os.environ.get("BASE_URL", "https://protocolpulse.replit.app")


def _resend_api_key() -> str:
    return os.environ.get("RESEND_API_KEY", "")


def _send_email(to: str, subject: str, html: str) -> dict:
    """Send one email via Resend."""
    key = _resend_api_key()
    if not key:
        return {"success": False, "error": "RESEND_API_KEY not set"}
    try:
        r = requests.post(
            f"{RESEND_BASE}/emails",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            timeout=RESEND_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return {"success": True, "id": r.json().get("id")}
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _trigger_email_html(price: float, target: float, direction: str, token: str) -> str:
    d = "above" if direction == "above" else "below"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Courier New',monospace;color:#e5e5e5">
<div style="max-width:600px;margin:0 auto;padding:40px 24px">
  <div style="text-align:center;margin-bottom:32px">
    <span style="font-size:28px;font-weight:700;letter-spacing:4px;color:#dc2626">PROTOCOL PULSE</span>
  </div>
  <div style="border:1px solid rgba(220,38,38,.4);border-radius:4px;padding:32px;background:#111">
    <h2 style="color:#dc2626;font-size:14px;letter-spacing:3px;margin:0 0 16px">⚡ ALERT TRIGGERED</h2>
    <p style="font-size:24px;font-weight:700;color:#F8C15C;margin:0 0 8px">BTC ${price:,.0f}</p>
    <p style="font-size:13px;color:#999;margin:0 0 24px">
      Your target: <strong style="color:#e5e5e5">${target:,.0f}</strong> ({d})
    </p>
    <div style="border-top:1px solid rgba(255,255,255,.08);padding-top:20px;margin-top:8px">
      <a href="{BASE_URL}/alerts" style="display:inline-block;background:#dc2626;color:#fff;padding:10px 24px;text-decoration:none;border-radius:3px;font-size:12px;letter-spacing:2px;font-weight:700">SET NEW ALERT</a>
      <span style="margin:0 12px;color:#333">|</span>
      <a href="{BASE_URL}/alerts/manage?token={token}" style="color:#666;font-size:11px;text-decoration:underline">Manage alerts</a>
    </div>
  </div>
  <p style="text-align:center;font-size:10px;color:#444;margin-top:24px;letter-spacing:1px">PROTOCOL PULSE · SOVEREIGN BITCOIN INTELLIGENCE</p>
</div>
</body></html>"""


def _get_btc_price() -> float | None:
    """Fetch BTC spot price from Coinbase."""
    try:
        r = requests.get(
            "https://api.coinbase.com/v2/prices/BTC-USD/spot",
            timeout=10,
        )
        if r.status_code == 200:
            return float(r.json()["data"]["amount"])
    except Exception as e:
        logger.error("Price fetch failed: %s", e)
    return None


def check_all_alerts():
    """Main entry — check all active alerts against current price."""
    # Bootstrap Flask app context
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import app, db
    from models import PriceAlert

    price = _get_btc_price()
    if price is None:
        logger.error("Could not fetch BTC price — skipping alert check")
        return

    logger.info("BTC price: $%.0f — checking alerts", price)

    with app.app_context():
        alerts = PriceAlert.query.filter_by(active=True, notified=False).all()
        triggered = 0
        for alert in alerts:
            hit = (
                (alert.direction == "above" and price >= alert.price_target)
                or (alert.direction == "below" and price <= alert.price_target)
            )
            if not hit:
                continue

            html = _trigger_email_html(price, alert.price_target, alert.direction, alert.email_token)
            result = _send_email(
                alert.email,
                f"⚡ BTC Alert: ${price:,.0f} ({alert.direction} ${alert.price_target:,.0f})",
                html,
            )
            if result["success"]:
                alert.notified = True
                alert.triggered_at = datetime.utcnow()
                alert.triggered_price = price
                triggered += 1
                logger.info("Triggered alert #%d for %s", alert.id, alert.email)
            else:
                logger.error("Email failed for alert #%d: %s", alert.id, result.get("error"))

        if triggered:
            try:
                db.session.commit()
                logger.info("Triggered %d alerts", triggered)
            except Exception as e:
                db.session.rollback()
                logger.error("DB commit failed after triggering %d alerts: %s", triggered, e)
        else:
            logger.info("No alerts triggered (%d active)", len(alerts))


if __name__ == "__main__":
    check_all_alerts()
