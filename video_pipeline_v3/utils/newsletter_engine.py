#!/usr/bin/env python3
"""Protocol Pulse Daily Newsletter Engine.

Reads intelligence data (daily_signals.json, sentiment) and latest articles,
compiles an HTML digest email, and sends via Resend API.

Designed to run daily at 13:00 UTC (8 AM EST) via cron on Ultron,
triggering the Replit newsletter endpoint or sending directly.
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add parent dir to path for relay import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import relay

logger = logging.getLogger("newsletter_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INTELLIGENCE_DIR = DATA_DIR / "intelligence"
SITE_URL = "https://protocolpulse.io"


def load_daily_signals() -> dict:
    """Load topic velocity and recommended topics from daily_signals.json."""
    path = INTELLIGENCE_DIR / "daily_signals.json"
    if not path.exists():
        logger.warning("daily_signals.json not found")
        return {}
    with open(path) as f:
        return json.load(f)


def load_sentiment() -> dict:
    """Load sentiment data. Falls back to daily_signals if no separate file."""
    path = INTELLIGENCE_DIR / "sentiment.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    # Derive from daily_signals
    signals = load_daily_signals()
    if not signals.get("topic_velocity"):
        return {"score": 50, "label": "neutral"}
    sentiments = [t.get("sentiment", "neutral") for t in signals["topic_velocity"]]
    bullish = sentiments.count("bullish")
    bearish = sentiments.count("bearish")
    total = len(sentiments)
    if bullish > bearish:
        label = "bullish"
        score = 50 + int((bullish / total) * 50)
    elif bearish > bullish:
        label = "bearish"
        score = 50 - int((bearish / total) * 50)
    else:
        label = "neutral"
        score = 50
    return {"score": score, "label": label}


def fetch_latest_articles(count: int = 5) -> list:
    """Fetch latest articles from the Replit API."""
    try:
        import requests
        r = requests.get(
            f"{SITE_URL}/api/v2/articles?per_page={count}",
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("articles", data.get("data", []))[:count]
    except Exception as e:
        logger.warning(f"API fetch failed: {e}")
    # Fallback: query via relay
    raw = relay.query_db(
        f"SELECT id, title, slug, summary, created_at FROM articles "
        f"WHERE published=1 ORDER BY created_at DESC LIMIT {count}"
    )
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return []


def load_node_data() -> dict:
    """Load node monitor data if available."""
    path = DATA_DIR / "node_snapshots" / "latest.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def sentiment_emoji(label: str) -> str:
    """Return a text indicator for sentiment (no actual emojis)."""
    mapping = {
        "bullish": "UP",
        "very_bullish": "STRONG UP",
        "bearish": "DOWN",
        "very_bearish": "STRONG DOWN",
        "neutral": "FLAT",
    }
    return mapping.get(label, "FLAT")


def sentiment_color(label: str) -> str:
    if "bullish" in label:
        return "#00CC66"
    elif "bearish" in label:
        return "#CC0000"
    return "#888888"


def build_newsletter_html(
    signals: dict,
    sentiment: dict,
    articles: list,
    node_data: dict,
    date_str: str,
) -> tuple:
    """Build the newsletter HTML and subject line.

    Returns (subject, html_body).
    """
    label = sentiment.get("label", "neutral").upper()
    score = sentiment.get("score", 50)
    subject = f"Protocol Pulse Daily Brief -- {date_str} | BTC {label}"

    # Top 3 topics
    topics = signals.get("topic_velocity", [])[:3]
    topics_html = ""
    for t in topics:
        name = t.get("topic", "Unknown").title()
        vel = t.get("velocity_score", 0)
        chans = t.get("channels", 0)
        sent = t.get("sentiment", "neutral")
        bar_width = min(vel, 100)
        topics_html += f"""
        <tr>
          <td style="color:#EDEDED;padding:8px 12px;font-family:'JetBrains Mono',monospace;font-size:14px;border-bottom:1px solid #1F1F1F;">
            {name}
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #1F1F1F;">
            <div style="background:#1F1F1F;border-radius:4px;height:16px;width:120px;display:inline-block;vertical-align:middle;">
              <div style="background:#CC0000;border-radius:4px;height:16px;width:{bar_width}%;"></div>
            </div>
            <span style="color:#888;font-size:12px;margin-left:6px;">{vel}</span>
          </td>
          <td style="color:{sentiment_color(sent)};padding:8px 12px;font-size:13px;border-bottom:1px solid #1F1F1F;text-transform:uppercase;">
            {sent} ({chans} ch)
          </td>
        </tr>"""

    # Sentiment gauge
    gauge_color = sentiment_color(sentiment.get("label", "neutral"))
    gauge_html = f"""
    <div style="text-align:center;padding:20px;">
      <div style="font-size:48px;font-family:'JetBrains Mono',monospace;color:{gauge_color};font-weight:bold;">
        {score}
      </div>
      <div style="color:{gauge_color};font-size:16px;text-transform:uppercase;letter-spacing:3px;margin-top:4px;">
        {label}
      </div>
      <div style="color:#555;font-size:12px;margin-top:4px;">PROTOCOL PULSE SENTIMENT INDEX</div>
    </div>"""

    # Articles
    articles_html = ""
    for a in articles:
        title = a.get("title", "Untitled")
        summary = a.get("summary", a.get("description", ""))[:180]
        slug = a.get("slug", "")
        link = f"{SITE_URL}/article/{slug}" if slug else SITE_URL
        articles_html += f"""
        <div style="border-bottom:1px solid #1F1F1F;padding:14px 0;">
          <a href="{link}" style="color:#EDEDED;text-decoration:none;font-size:15px;font-weight:bold;display:block;">
            {title}
          </a>
          <p style="color:#888;font-size:13px;margin:6px 0 0;line-height:1.5;">{summary}</p>
        </div>"""

    # Node data
    node_html = ""
    if node_data:
        total = node_data.get("total_reachable", "N/A")
        change = node_data.get("net_change_24h", 0)
        sign = "+" if change >= 0 else ""
        change_color = "#00CC66" if change >= 0 else "#CC0000"
        node_html = f"""
        <div style="background:#111;border:1px solid #1F1F1F;border-radius:8px;padding:16px;margin:16px 0;">
          <div style="color:#555;font-size:11px;letter-spacing:2px;margin-bottom:8px;">NODE PULSE</div>
          <span style="color:#EDEDED;font-size:28px;font-family:'JetBrains Mono',monospace;font-weight:bold;">{total:,}</span>
          <span style="color:{change_color};font-size:16px;margin-left:8px;">{sign}{change}</span>
          <div style="color:#555;font-size:11px;margin-top:4px;">Total reachable nodes | 24h change</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#000;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:640px;margin:0 auto;background:#0A0A0A;">

  <!-- HEADER -->
  <div style="background:#0A0A0A;padding:24px;border-bottom:2px solid #CC0000;">
    <div style="color:#CC0000;font-size:11px;letter-spacing:4px;font-weight:bold;">PROTOCOL PULSE</div>
    <div style="color:#EDEDED;font-size:22px;font-weight:bold;margin-top:6px;">Daily Intelligence Brief</div>
    <div style="color:#555;font-size:13px;margin-top:4px;">{date_str}</div>
  </div>

  <!-- SENTIMENT GAUGE -->
  <div style="padding:0 24px;">
    {gauge_html}
  </div>

  <!-- TOP TOPICS -->
  <div style="padding:0 24px;">
    <div style="color:#555;font-size:11px;letter-spacing:2px;margin-bottom:12px;">TOP TOPICS BY VELOCITY</div>
    <table style="width:100%;border-collapse:collapse;">
      {topics_html}
    </table>
  </div>

  <!-- ARTICLES -->
  <div style="padding:20px 24px;">
    <div style="color:#555;font-size:11px;letter-spacing:2px;margin-bottom:8px;">TODAY'S INTELLIGENCE</div>
    {articles_html}
  </div>

  <!-- NODE PULSE -->
  <div style="padding:0 24px;">
    {node_html}
  </div>

  <!-- CTA: Watch Today's Pulse Check -->
  <div style="padding:20px 24px;text-align:center;">
    <a href="https://www.youtube.com/@ProtocolPulse"
       style="display:inline-block;background:#CC0000;color:white;
              padding:14px 36px;border-radius:6px;text-decoration:none;
              font-weight:bold;font-size:15px;letter-spacing:1px;">
      WATCH TODAY'S PULSE CHECK
    </a>
  </div>

  <!-- FOOTER -->
  <div style="background:#080808;padding:20px 24px;border-top:1px solid #1F1F1F;text-align:center;">
    <div style="margin-bottom:12px;">
      <a href="{SITE_URL}" style="color:#888;text-decoration:none;font-size:12px;margin:0 8px;">Website</a>
      <a href="https://twitter.com/ProtocolPulse" style="color:#888;text-decoration:none;font-size:12px;margin:0 8px;">X</a>
      <a href="https://www.youtube.com/@ProtocolPulse" style="color:#888;text-decoration:none;font-size:12px;margin:0 8px;">YouTube</a>
    </div>
    <div style="color:#444;font-size:11px;line-height:1.6;">
      Protocol Pulse -- Bitcoin Intelligence Daily -- Stay Sovereign<br>
      <a href="{SITE_URL}/unsubscribe" style="color:#555;text-decoration:underline;">Unsubscribe</a>
    </div>
  </div>

</div>
</body>
</html>"""

    return subject, html


def send_via_resend(subject: str, html: str, audience_id: str = "") -> dict:
    """Send the newsletter via Resend API.

    Uses Resend's broadcast/audience feature if audience_id is set,
    otherwise falls back to a test recipient.
    """
    import requests as req

    api_key = relay.get_key("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY not available (checked env + Replit relay)")
        return {"ok": False, "error": "no_api_key"}

    from_email = "Protocol Pulse <newsletter@protocolpulse.io>"

    if audience_id:
        # Broadcast to full audience
        payload = {
            "from": from_email,
            "to": audience_id,
            "subject": subject,
            "html": html,
        }
    else:
        # Fetch subscriber list from Replit DB
        raw = relay.query_db(
            "SELECT email FROM users WHERE newsletter_opt_in=1 AND email IS NOT NULL"
        )
        recipients = []
        if raw:
            try:
                rows = json.loads(raw)
                recipients = [r["email"] for r in rows if r.get("email")]
            except (json.JSONDecodeError, KeyError):
                pass

        if not recipients:
            logger.warning("No subscribers found. Sending test to relay only.")
            return {"ok": False, "error": "no_subscribers", "html_saved": True}

        # Resend supports batch sending up to 100
        results = []
        for batch_start in range(0, len(recipients), 50):
            batch = recipients[batch_start:batch_start + 50]
            payload = {
                "from": from_email,
                "to": batch,
                "subject": subject,
                "html": html,
            }
            try:
                r = req.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30,
                )
                results.append({"status": r.status_code, "batch": len(batch)})
                if r.status_code not in (200, 201):
                    logger.error(f"Resend error {r.status_code}: {r.text[:200]}")
            except Exception as e:
                logger.error(f"Resend request failed: {e}")
                results.append({"status": "error", "error": str(e)})

        sent = sum(1 for r in results if r.get("status") in (200, 201))
        return {"ok": sent > 0, "batches": results, "total_recipients": len(recipients)}

    # Single send (audience mode)
    try:
        r = req.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        return {"ok": r.status_code in (200, 201), "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_daily_newsletter() -> dict:
    """Main entry point. Compile and send the daily newsletter."""
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    logger.info(f"Building newsletter for {date_str}")

    signals = load_daily_signals()
    sentiment = load_sentiment()
    articles = fetch_latest_articles(5)
    node_data = load_node_data()

    subject, html = build_newsletter_html(signals, sentiment, articles, node_data, date_str)

    # Save HTML locally for inspection
    output_dir = BASE_DIR / "output" / "newsletters"
    output_dir.mkdir(parents=True, exist_ok=True)
    date_file = datetime.utcnow().strftime("%Y-%m-%d")
    html_path = output_dir / f"newsletter_{date_file}.html"
    with open(html_path, "w") as f:
        f.write(html)
    logger.info(f"Newsletter HTML saved: {html_path}")

    # Send
    result = send_via_resend(subject, html)
    logger.info(f"Send result: {result}")

    return {
        "date": date_str,
        "subject": subject,
        "articles": len(articles),
        "topics": len(signals.get("topic_velocity", [])[:3]),
        "sentiment": sentiment.get("label", "unknown"),
        "html_path": str(html_path),
        "send_result": result,
    }


def trigger_replit_newsletter() -> dict:
    """Alternative: trigger the newsletter endpoint on Replit."""
    result = relay.run(
        "curl -s http://localhost:5000/api/newsletter/send "
        '-H "Content-Type: application/json" '
        '-d \'{"source": "ultron_cron"}\''
    )
    return {"replit_response": result}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Protocol Pulse Daily Newsletter")
    parser.add_argument("--test", action="store_true", help="Generate HTML only, don't send")
    parser.add_argument("--trigger-replit", action="store_true", help="Trigger Replit endpoint instead")
    args = parser.parse_args()

    if args.trigger_replit:
        result = trigger_replit_newsletter()
    elif args.test:
        signals = load_daily_signals()
        sentiment = load_sentiment()
        articles = fetch_latest_articles(5)
        node_data = load_node_data()
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        subject, html = build_newsletter_html(signals, sentiment, articles, node_data, date_str)
        output_dir = BASE_DIR / "output" / "newsletters"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"newsletter_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        with open(path, "w") as f:
            f.write(html)
        result = {"test": True, "subject": subject, "html_path": str(path)}
    else:
        result = run_daily_newsletter()

    print(json.dumps(result, indent=2, default=str))
