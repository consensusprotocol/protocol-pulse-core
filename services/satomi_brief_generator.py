"""
Satomi Morning Brief Generator
Generates a 90-second voice script from live intelligence data,
then delivers via Twilio voice call + SMS summary.

Cron: 45 6 * * * (06:45 UTC daily)
"""
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[satomi_brief] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "morning_brief.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("satomi_brief")


def _load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


_load_env()


# ── Data Collectors ──────────────────────────────────────────────────────────

def _get_btc_price() -> dict:
    """Fetch BTC price from CoinGecko. Returns {price, change_24h_pct}."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers={"User-Agent": "ProtocolPulse/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        btc = data.get("bitcoin", {})
        return {
            "price": btc.get("usd", 0),
            "change_24h_pct": round(btc.get("usd_24h_change", 0), 2),
        }
    except Exception as e:
        logger.warning("BTC price fetch failed: %s", e)
        return {"price": 0, "change_24h_pct": 0}


def _get_top_signals(limit: int = 3) -> list:
    """Pull top signals from sovereign_context/latest.json."""
    try:
        ctx_path = BASE / "data" / "sovereign_context" / "latest.json"
        if not ctx_path.exists():
            return []
        data = json.loads(ctx_path.read_text())

        # Try explicit signals list first
        signals = data.get("signals", data.get("top_signals", []))
        if signals:
            result = []
            for s in signals[:limit]:
                if isinstance(s, dict):
                    title = s.get("title") or s.get("headline") or s.get("name", "Signal")
                    summary = s.get("summary") or s.get("description") or s.get("content", "")
                    result.append({"title": title, "summary": summary[:200]})
                elif isinstance(s, str):
                    result.append({"title": s[:100], "summary": ""})
            return result

        # Build signals from structured context fields
        result = []
        fg = data.get("fear_greed", {})
        if fg and fg.get("value"):
            result.append({
                "title": f"Fear and Greed Index at {fg['value']}",
                "summary": fg.get("classification", ""),
            })
        mempool = data.get("mempool", {})
        if mempool and mempool.get("pending_tx"):
            fee = mempool.get("median_fee", "unknown")
            result.append({
                "title": f"Mempool: {mempool['pending_tx']:,} pending transactions",
                "summary": f"Median fee {fee} sat/vB",
            })
        net = data.get("network", {})
        if net and net.get("hashrate"):
            result.append({
                "title": f"Network hashrate at {net['hashrate']}",
                "summary": net.get("difficulty_change", ""),
            })
        narrative = data.get("narrative", {})
        if narrative and narrative.get("dominant_theme"):
            result.append({
                "title": f"Dominant narrative: {narrative['dominant_theme']}",
                "summary": f"Sentiment: {narrative.get('sentiment', 'neutral')}",
            })
        return result[:limit]
    except Exception as e:
        logger.warning("Signal fetch failed: %s", e)
        return []


def _get_spaces_highlight() -> dict:
    """Get latest X Spaces highlight from sentiment data."""
    try:
        sentiment_path = BASE / "video_pipeline_v3" / "data" / "intelligence" / "sentiment.json"
        if sentiment_path.exists():
            data = json.loads(sentiment_path.read_text())
            xs = data.get("data", {}).get("breakdown", {}).get("x_spaces", {})
            if xs and xs.get("top_host"):
                return {
                    "speaker": xs.get("top_host", "Unknown"),
                    "title": xs.get("top_topic", "Bitcoin discussion"),
                    "score": xs.get("score", 50),
                }
        # Fallback: check spaces scraper data
        scraper_path = BASE / "spaces_scraper" / "data"
        if scraper_path.exists():
            files = sorted(scraper_path.glob("*.json"), reverse=True)
            for f in files[:3]:
                d = json.loads(f.read_text())
                if d.get("title"):
                    return {
                        "speaker": d.get("host", "a prominent voice"),
                        "title": d.get("title", "Bitcoin discussion"),
                        "score": d.get("sentiment_score", 50),
                    }
    except Exception as e:
        logger.warning("Spaces data fetch failed: %s", e)
    return {}


def _get_social_sentiment() -> str:
    """Get overall social sentiment label."""
    try:
        sentiment_path = BASE / "video_pipeline_v3" / "data" / "intelligence" / "sentiment.json"
        if sentiment_path.exists():
            data = json.loads(sentiment_path.read_text())
            score = data.get("data", {}).get("overall_score", 50)
            if score >= 65:
                return "BULLISH"
            elif score <= 35:
                return "BEARISH"
        return "NEUTRAL"
    except Exception:
        return "NEUTRAL"


# ── Script Generator ─────────────────────────────────────────────────────────

def generate_brief_script() -> str:
    """Generate the 90-second morning brief voice script."""
    btc = _get_btc_price()
    signals = _get_top_signals(3)
    spaces = _get_spaces_highlight()
    sentiment = _get_social_sentiment()
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    price_str = f"${btc['price']:,.0f}" if btc["price"] else "price unavailable"
    direction = "up" if btc["change_24h_pct"] > 0 else "down"
    pct = abs(btc["change_24h_pct"])

    # Try Claude for polished script
    script = _generate_with_claude(today, price_str, direction, pct, signals, spaces, sentiment)
    if script:
        return script

    # Fallback: template-based
    lines = [
        f"Good morning. Protocol Pulse sovereign intelligence brief for {today}.",
        f"Bitcoin is trading at {price_str}, {direction} {pct:.1f} percent in the last 24 hours.",
    ]
    for s in signals[:2]:
        lines.append(f"{s['title']}. {s['summary'][:80]}." if s["summary"] else f"{s['title']}.")
    if spaces:
        lines.append(f"In X Spaces, {spaces['speaker']} discussed: {spaces['title']}.")
    lines.append(f"Social sentiment is {sentiment}.")
    lines.append("That's your brief. Stay sovereign.")
    return " ".join(lines)


def _generate_with_claude(today, price_str, direction, pct, signals, spaces, sentiment) -> str:
    """Use Claude to generate a polished 90-second voice script."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    signal_text = ""
    for i, s in enumerate(signals[:3], 1):
        signal_text += f"  Signal {i}: {s['title']}"
        if s["summary"]:
            signal_text += f" - {s['summary'][:150]}"
        signal_text += "\n"

    spaces_text = ""
    if spaces:
        spaces_text = f"X Spaces highlight: {spaces['speaker']} on '{spaces['title']}' (score: {spaces.get('score', 'N/A')})"

    prompt = f"""Write a 90-second spoken intelligence briefing script. Read it aloud naturally.

DATA:
- Date: {today}
- BTC: {price_str}, {direction} {pct:.1f}% in 24h
- Top signals:
{signal_text}- {spaces_text or 'No X Spaces highlight today.'}
- Social sentiment: {sentiment}

FORMAT (strict):
"Good morning. Protocol Pulse sovereign intelligence brief for {today}.
Bitcoin is trading at {price_str}, {direction} {pct:.1f} percent in the last 24 hours.
[Signal 1]: [1 sentence].
[Signal 2]: [1 sentence].
[Optional spaces line].
Social sentiment is {sentiment}.
That's your brief. Stay sovereign."

RULES:
- No emojis, no markdown, no URLs
- Plain spoken English, concise, authoritative
- Under 250 words total
- Every number spelled for speech (e.g. "eighty-seven thousand")"""

    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        text = result.get("content", [{}])[0].get("text", "")
        if text and len(text) > 50:
            return text.strip()
    except Exception as e:
        logger.warning("Claude brief generation failed: %s", e)
    return ""


# ── Delivery ─────────────────────────────────────────────────────────────────

def generate_and_deliver_brief():
    """Main entry: generate brief, deliver via voice call + SMS summary."""
    from services.twilio_service import send_morning_brief_call, send_sms

    pbx_number = os.getenv("PBX_PHONE_NUMBER")
    if not pbx_number:
        logger.error("PBX_PHONE_NUMBER not set — cannot deliver brief")
        return {"success": False, "error": "PBX_PHONE_NUMBER not set"}

    logger.info("Generating morning brief...")
    script = generate_brief_script()
    logger.info("Brief script generated (%d chars)", len(script))

    # Voice call
    call_ok = send_morning_brief_call(pbx_number, script)
    logger.info("Voice call result: %s", "OK" if call_ok else "FAILED")

    # SMS summary (first 300 chars)
    sms_text = f"[PROTOCOL PULSE BRIEF]\n{script[:280]}..."
    sms_ok = send_sms(pbx_number, sms_text)
    logger.info("SMS summary result: %s", "OK" if sms_ok else "FAILED")

    result = {
        "success": call_ok or sms_ok,
        "call_delivered": call_ok,
        "sms_delivered": sms_ok,
        "script_length": len(script),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Brief delivery complete: %s", result)
    return result


if __name__ == "__main__":
    generate_and_deliver_brief()
