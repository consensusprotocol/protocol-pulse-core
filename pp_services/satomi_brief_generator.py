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
    """Fetch BTC price: cached signals.json → CoinGecko → mempool.space."""
    # 1. Try cached signals.json (updated every 5min by signal_data_fetcher)
    try:
        signals_path = BASE / "data" / "signals.json"
        if signals_path.exists():
            import time
            age = time.time() - signals_path.stat().st_mtime
            if age < 900:  # fresh within 15 minutes
                data = json.loads(signals_path.read_text())
                bp = data.get("btc_price", {})
                if bp.get("value") and bp["value"] > 0:
                    logger.info("BTC price from signals.json cache (%.0fs old): $%s", age, bp["value"])
                    return {
                        "price": bp["value"],
                        "change_24h_pct": round(bp.get("change_24h", 0) or 0, 2),
                    }
    except Exception as e:
        logger.warning("signals.json cache read failed: %s", e)

    # 2. Try CoinGecko API
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers={"User-Agent": "ProtocolPulse/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        btc = data.get("bitcoin", {})
        if btc.get("usd") and btc["usd"] > 0:
            logger.info("BTC price from CoinGecko: $%s", btc["usd"])
            return {
                "price": btc["usd"],
                "change_24h_pct": round(btc.get("usd_24h_change", 0), 2),
            }
    except Exception as e:
        logger.warning("CoinGecko price fetch failed: %s", e)

    # 3. Fallback: mempool.space
    try:
        req = urllib.request.Request("https://mempool.space/api/v1/prices",
                                     headers={"User-Agent": "ProtocolPulse/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        usd = data.get("USD", 0)
        if usd and usd > 0:
            logger.info("BTC price from mempool.space: $%s", usd)
            return {"price": usd, "change_24h_pct": 0}
    except Exception as e:
        logger.warning("mempool.space price fetch failed: %s", e)

    return {"price": 0, "change_24h_pct": 0}


def _get_full_intelligence() -> dict:
    """Pull ALL intelligence from sovereign_context + convergence API."""
    intel = {
        "signals": [],
        "options": {},
        "futures": {},
        "macro": {},
        "onchain": {},
        "convergence": {},
        "whale_alerts": [],
        "lightning": {},
        "polymarket": {},
    }
    try:
        ctx_path = BASE / "data" / "sovereign_context" / "latest.json"
        if not ctx_path.exists():
            return intel
        data = json.loads(ctx_path.read_text())

        # Fear & Greed
        fg = data.get("fear_greed", {})
        if fg.get("value"):
            intel["signals"].append(f"Fear & Greed: {fg['value']}/100 ({fg.get('label', '')})")

        # Network
        net = data.get("network", {})
        if net.get("hashrate_eh"):
            adj = net.get("next_adj_pct", 0)
            intel["signals"].append(f"Hashrate: {net['hashrate_eh']} EH/s, next difficulty adjustment {adj:+.1f}%")

        # Options
        opts = data.get("options", {})
        if opts.get("put_call_ratio"):
            intel["options"] = {
                "put_call": opts.get("put_call_ratio"),
                "dvol": opts.get("dvol"),
                "max_pain": opts.get("max_pain"),
                "total_oi_btc": opts.get("total_oi_btc"),
                "avg_iv": opts.get("avg_mark_iv"),
            }

        # Futures
        fut = data.get("futures", {})
        if fut.get("funding_rate") is not None:
            intel["futures"] = {
                "funding_rate": fut.get("funding_rate"),
                "annualized_basis": fut.get("annualized_basis"),
                "open_interest_btc": fut.get("open_interest"),
                "open_interest_usd": fut.get("open_interest_usd"),
                "basis_pct": fut.get("basis_pct"),
            }

        # Macro
        macro = data.get("macro", {})
        if macro:
            intel["macro"] = {
                "gold": macro.get("gold_price"),
                "sp500": macro.get("sp500"),
                "ten_yr_yield": macro.get("ten_year_yield"),
                "btc_gold_corr": macro.get("btc_vs_gold_30d_corr"),
                "btc_dxy_corr": macro.get("btc_vs_dxy_30d_corr"),
            }

        # On-chain
        oc = data.get("on_chain", {})
        if oc:
            intel["onchain"] = {
                "active_addresses_7d": oc.get("active_addresses_7d"),
                "coin_days_destroyed": oc.get("coin_days_destroyed_7d"),
                "nvt_ratio": oc.get("nvt_ratio"),
                "accumulation_score": oc.get("accumulation_score"),
                "tx_volume_usd_7d": oc.get("tx_volume_usd_7d"),
            }

        # Whale alerts
        alerts = data.get("whale_alerts", [])
        if alerts:
            intel["whale_alerts"] = [a.get("message", "")[:100] for a in alerts[:3]]

        # Lightning
        ln = data.get("lightning", {})
        if ln.get("capacity_btc"):
            intel["lightning"] = {
                "capacity_btc": ln.get("capacity_btc"),
                "channels": ln.get("channels"),
                "nodes": ln.get("nodes"),
            }

        # Polymarket
        pm = data.get("polymarket", {})
        if pm.get("top_market"):
            intel["polymarket"] = {
                "top_market": pm.get("top_market"),
                "probability": pm.get("top_probability"),
            }

        # Convergence (from API)
        try:
            req = urllib.request.Request("http://localhost:5000/api/v1/intelligence/convergence/latest",
                                         headers={"User-Agent": "ProtocolPulse/Brief"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                conv = json.loads(resp.read())
            intel["convergence"] = {
                "score": conv.get("convergence_score"),
                "thesis": conv.get("dominant_thesis", {}).get("label"),
                "direction": conv.get("dominant_thesis", {}).get("direction"),
                "aligned": conv.get("aligned_signals", []),
                "conflicting": conv.get("conflicting_signals", []),
            }
        except Exception:
            pass

    except Exception as e:
        logger.warning("Intelligence fetch failed: %s", e)
    return intel


def _get_top_signals(limit: int = 3) -> list:
    """Legacy wrapper — still called by template fallback."""
    intel = _get_full_intelligence()
    return [{"title": s, "summary": ""} for s in intel.get("signals", [])[:limit]]


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
    # Log what data we have for debugging
    intel = _get_full_intelligence()
    logger.info("Brief data: %d signals, options=%s, futures=%s, macro=%s, convergence=%s",
                len(intel.get("signals", [])),
                bool(intel.get("options")),
                bool(intel.get("futures")),
                bool(intel.get("macro")),
                bool(intel.get("convergence")))
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
    """Use Claude to generate a polished 90-second voice script with ALL data."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    intel = _get_full_intelligence()

    data_lines = [
        f"Date: {today}",
        f"BTC Price: {price_str}, {direction} {pct:.1f}% in 24h",
    ]
    for s in intel.get("signals", []):
        data_lines.append(f"Signal: {s}")

    opts = intel.get("options", {})
    if opts.get("put_call"):
        data_lines.append(f"Options: Put/Call {opts['put_call']:.2f}, DVOL {opts.get('dvol', '?')}, Max Pain ${opts.get('max_pain', 0):,.0f}, OI {opts.get('total_oi_btc', 0):,.0f} BTC")

    fut = intel.get("futures", {})
    if fut.get("funding_rate") is not None:
        data_lines.append(f"Futures: Funding {fut['funding_rate']:.6f}, Basis {fut.get('annualized_basis', 0):.1f}% annualized, OI {fut.get('open_interest_btc', 0):,.0f} BTC")

    macro = intel.get("macro", {})
    if macro.get("gold"):
        data_lines.append(f"Macro: Gold ${macro['gold']:,.0f}, S&P {macro.get('sp500', '?'):,}, 10yr {macro.get('ten_yr_yield', '?')}%, BTC-DXY corr {macro.get('btc_dxy_corr', '?')}")

    oc = intel.get("onchain", {})
    if oc.get("active_addresses_7d"):
        data_lines.append(f"On-chain: {oc['active_addresses_7d']:,.0f} active addr 7d, NVT {oc.get('nvt_ratio', '?')}, Accum {oc.get('accumulation_score', '?')}/100")

    conv = intel.get("convergence", {})
    if conv.get("score"):
        data_lines.append(f"Convergence: {conv['score']:.1f}/100, Thesis: {conv.get('thesis', '?')}, Aligned: {conv.get('aligned', [])}, Conflicting: {conv.get('conflicting', [])}")

    alerts = intel.get("whale_alerts", [])
    if alerts:
        data_lines.append(f"Whales: {'; '.join(alerts[:2])}")

    if spaces:
        data_lines.append(f"X Spaces: {spaces.get('speaker', '?')} on '{spaces.get('title', '?')}'")

    data_block = "\n".join(f"- {l}" for l in data_lines)

    prompt = f"""You are the voice of Protocol Pulse, a sovereign Bitcoin intelligence briefing.
Write a 90-second spoken script. Authoritative, direct, cypherpunk edge.

ALL AVAILABLE DATA:
{data_block}

STRUCTURE:
1. "Good morning. Protocol Pulse intelligence brief for {today}."
2. Price + direction (one sentence, spell out numbers for speech)
3. The MOST interesting convergence or divergence in the data (2-3 sentences). If miners are bullish but fear is extreme, SAY that. If options diverge from spot, CALL IT OUT.
4. One macro insight — gold, yields, correlations — what it means for Bitcoin
5. One on-chain insight — accumulation, whale moves, NVT
6. Convergence Engine thesis in one punchy sentence
7. Close with exactly: "That's your brief. Stay sovereign."

RULES:
- ALWAYS lead with the BTC price and 24h change — this is the first thing the listener wants to hear
- If convergence score is above 70 or below 30, call it out explicitly — these are decision-relevant levels
- Name specific KOLs if their takes are in the data — "Saylor bought again" or "Lyn Alden flagged yield curve inversion" makes it personal
- No emojis, no markdown, no URLs, no hashtags
- Plain spoken English for phone delivery
- Spell out all numbers (sixty-seven thousand, not 67,000)
- Between 200-280 words — never shorter than 200
- Be opinionated. Take a stance.
- Say "stay sovereign" EXACTLY ONCE at the very end
- Sound like a cypherpunk intelligence officer, not a news anchor"""

    # 1. Try Claude Haiku
    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 700,
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
            logger.info("Brief generated by Claude Haiku (%d chars)", len(text))
            return text.strip()
    except Exception as e:
        logger.warning("Claude brief generation failed: %s", e)

    # 2. Try Gemini 2.5 Flash
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            payload = json.dumps({
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7},
            }).encode()
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if text and len(text) > 50:
                logger.info("Brief generated by Gemini Flash (%d chars)", len(text))
                return text.strip()
        except Exception as e:
            logger.warning("Gemini brief generation failed: %s", e)

    # 3. Try Grok 3 Mini Fast
    xai_key = os.environ.get("XAI_API_KEY", "")
    if xai_key:
        try:
            payload = json.dumps({
                "model": "grok-3-mini-fast",
                "messages": [{"role": "user", "content": prompt}],
            }).encode()
            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {xai_key}"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if text and len(text) > 50:
                logger.info("Brief generated by Grok Mini (%d chars)", len(text))
                return text.strip()
        except Exception as e:
            logger.warning("Grok brief generation failed: %s", e)

    return ""


def generate_and_deliver_brief():
    """Main entry: generate brief, deliver via voice call + SMS summary."""
    from pp_services.twilio_service import send_morning_brief_call, send_sms

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

    # SMS summary to PBX
    sms_text = f"[PROTOCOL PULSE BRIEF]\n{script[:280]}..."
    sms_ok = send_sms(pbx_number, sms_text)
    logger.info("SMS to PBX: %s", "OK" if sms_ok else "FAILED")

    # Deliver SMS to ALL subscribers
    sub_count = 0
    try:
        import sys as _sys2
        _sys2.path.insert(0, str(BASE / "core"))
        from app import app as _app, db as _db
        from models import SmsSubscriber
        with _app.app_context():
            subs = SmsSubscriber.query.filter_by(subscribed=True).all()
            for sub in subs:
                if sub.phone != pbx_number:
                    try:
                        send_sms(sub.phone, sms_text)
                        sub_count += 1
                    except Exception as _e:
                        logger.warning("SMS to %s failed: %s", sub.phone, _e)
        logger.info("SMS delivered to %d additional subscribers", sub_count)
    except Exception as _e:
        logger.warning("Subscriber delivery failed: %s", _e)

    result = {
        "success": call_ok or sms_ok,
        "call_delivered": call_ok,
        "sms_delivered": sms_ok,
        "subscriber_sms_count": sub_count,
        "script_length": len(script),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Brief delivery complete: %s", result)
    return result


if __name__ == "__main__":
    generate_and_deliver_brief()
