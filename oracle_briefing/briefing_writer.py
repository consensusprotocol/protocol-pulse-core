#!/usr/bin/env python3
"""Oracle Briefing Script Generator — writes daily 60-90s intelligence briefings.

Uses Claude to generate punchy, authoritative scripts from live Bitcoin data.
Format: HOOK → THE NUMBER → THE SIGNAL → THE TAKE → SIGN-OFF
"""
import json, os, sys, time
from datetime import datetime, timezone

import requests

from relay import get_key

# ---------------------------------------------------------------------------
# Live data fetchers
# ---------------------------------------------------------------------------

def fetch_btc_price() -> dict:
    """Fetch current BTC price + 24h change from CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true"},
            timeout=10,
        )
        if r.status_code == 200:
            d = r.json()["bitcoin"]
            return {
                "price": d["usd"],
                "change_24h": round(d.get("usd_24h_change", 0), 2),
                "market_cap": d.get("usd_market_cap", 0),
            }
    except Exception as e:
        print(f"[data] BTC price error: {e}")
    return {"price": 0, "change_24h": 0, "market_cap": 0}


def fetch_btc_7d() -> list:
    """Fetch 7-day BTC price history for overlay chart."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": "7"},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("prices", [])
    except Exception as e:
        print(f"[data] BTC 7d error: {e}")
    return []


def fetch_mempool() -> dict:
    """Fetch mempool stats from mempool.space API."""
    try:
        r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
        if r.status_code == 200:
            fees = r.json()
            r2 = requests.get("https://mempool.space/api/mempool", timeout=10)
            pool = r2.json() if r2.status_code == 200 else {}
            return {
                "fastest_fee": fees.get("fastestFee", 0),
                "half_hour_fee": fees.get("halfHourFee", 0),
                "hour_fee": fees.get("hourFee", 0),
                "economy_fee": fees.get("economyFee", 0),
                "tx_count": pool.get("count", 0),
                "vsize": pool.get("vsize", 0),
            }
    except Exception as e:
        print(f"[data] Mempool error: {e}")
    return {"fastest_fee": 0, "half_hour_fee": 0, "hour_fee": 0,
            "economy_fee": 0, "tx_count": 0, "vsize": 0}


def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed Index from alternative.me."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        if r.status_code == 200:
            d = r.json()["data"][0]
            return {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception as e:
        print(f"[data] FNG error: {e}")
    return {"value": 50, "label": "Neutral"}


def fetch_hashrate() -> dict:
    """Fetch hashrate / difficulty from mempool.space."""
    try:
        r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=10)
        if r.status_code == 200:
            data = r.json()
            hr = data.get("hashrates", [])
            diff = data.get("difficulty", [])
            current_hr = hr[-1]["avgHashrate"] if hr else 0
            return {
                "hashrate_eh": round(current_hr / 1e18, 1),
                "difficulty_epochs": diff[-5:] if len(diff) >= 5 else diff,
            }
    except Exception as e:
        print(f"[data] Hashrate error: {e}")
    return {"hashrate_eh": 0, "difficulty_epochs": []}


def fetch_latest_articles() -> list:
    """Fetch latest Protocol Pulse articles from Replit."""
    from relay import query_db
    try:
        raw = query_db(
            "SELECT title, slug, summary FROM articles ORDER BY published_at DESC LIMIT 5"
        )
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"[data] Articles error: {e}")
    return []


def fetch_all_data() -> dict:
    """Fetch all live data sources."""
    print("[data] Fetching live data...")
    btc = fetch_btc_price()
    mempool = fetch_mempool()
    fng = fetch_fear_greed()
    hashrate = fetch_hashrate()
    articles = fetch_latest_articles()
    btc_7d = fetch_btc_7d()

    data = {
        "btc": btc,
        "btc_7d": btc_7d,
        "mempool": mempool,
        "fng": fng,
        "hashrate": hashrate,
        "articles": articles,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  BTC: ${btc['price']:,.0f} ({btc['change_24h']:+.1f}%)")
    print(f"  FNG: {fng['value']} ({fng['label']})")
    print(f"  Mempool: {mempool['tx_count']:,} txs, {mempool['fastest_fee']} sat/vB fastest")
    print(f"  Hashrate: {hashrate['hashrate_eh']} EH/s")
    return data


SAMPLE_DATA = {
    "btc": {"price": 87432, "change_24h": 2.4, "market_cap": 1720000000000},
    "btc_7d": [[1709251200000, 84200], [1709337600000, 85100],
               [1709424000000, 84800], [1709510400000, 86300],
               [1709596800000, 85900], [1709683200000, 86700],
               [1709769600000, 87432]],
    "mempool": {"fastest_fee": 12, "half_hour_fee": 8, "hour_fee": 5,
                "economy_fee": 3, "tx_count": 42000, "vsize": 180000000},
    "fng": {"value": 72, "label": "Greed"},
    "hashrate": {"hashrate_eh": 792.3, "difficulty_epochs": []},
    "articles": [
        {"title": "Bitcoin Crosses $87K As Institutional Demand Surges",
         "slug": "bitcoin-crosses-87k", "summary": "Bitcoin breaks above $87,000..."},
        {"title": "Mining Difficulty Hits All-Time High",
         "slug": "mining-difficulty-ath", "summary": "Network difficulty adjustment..."},
    ],
    "timestamp": datetime.now(timezone.utc).isoformat(),
}


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Protocol Pulse Oracle — the authoritative voice of Bitcoin intelligence.

You write daily Oracle Briefing scripts: 60-90 seconds of punchy, data-driven analysis.
Your tone is confident, direct, and slightly dramatic. No filler. No hedging. Every word earns its place.

Format (strict):
1. HOOK — 1 sentence, max 15 words. Grabs attention immediately.
2. THE NUMBER — Key metric of the day with context. 40-50 words max.
3. THE SIGNAL — Top development/trend with analysis. 40-50 words max.
4. THE TAKE — Your editorial opinion. Bold, clear stance. 40-50 words max.
5. SIGN-OFF — "This has been the Oracle Briefing from Protocol Pulse. Stay sovereign. Stay informed."

Rules:
- Total script: 150-200 words (60-90 seconds at speaking pace)
- Use exact numbers from the data provided
- Reference specific articles when relevant
- No questions — only statements
- No "let's" or "we" — speak as the Oracle
- Format BTC prices with commas: $87,432
- Each segment must stand alone as a compelling statement"""

USER_PROMPT_TEMPLATE = """Write today's Oracle Briefing script using this live data:

**Bitcoin:**
- Price: ${price:,.0f} ({change:+.1f}% 24h)
- Market Cap: ${mcap:,.0f}

**Network:**
- Mempool: {tx_count:,} unconfirmed txs
- Fees: {fastest_fee} sat/vB fastest, {hour_fee} sat/vB economy
- Hashrate: {hashrate} EH/s

**Sentiment:**
- Fear & Greed: {fng_value} ({fng_label})

**Latest Protocol Pulse Headlines:**
{headlines}

Date: {date}

Return ONLY valid JSON (no markdown fences):
{{
  "hook": "...",
  "the_number": "...",
  "the_signal": "...",
  "the_take": "...",
  "signoff": "This has been the Oracle Briefing from Protocol Pulse. Stay sovereign. Stay informed.",
  "full_script": "... (all segments concatenated with natural pauses)",
  "thumbnail_headline": "... (5-8 word punchy headline for thumbnail)",
  "overlay_suggestions": {{
    "the_number": "price_chart|mempool_viz|hashrate_chart",
    "the_signal": "price_chart|article_screenshot|hashrate_chart",
    "the_take": "price_chart|mempool_viz"
  }}
}}"""


def generate_script(data: dict = None, test: bool = False) -> dict:
    """Generate Oracle Briefing script using Claude."""
    if test:
        data = SAMPLE_DATA

    if data is None:
        data = fetch_all_data()

    btc = data["btc"]
    mem = data["mempool"]
    fng = data["fng"]
    hr = data["hashrate"]
    articles = data.get("articles", [])

    headlines = "\n".join(
        f"- {a['title']}" for a in articles[:5]
    ) or "- No recent articles available"

    user_prompt = USER_PROMPT_TEMPLATE.format(
        price=btc["price"],
        change=btc["change_24h"],
        mcap=btc["market_cap"],
        tx_count=mem["tx_count"],
        fastest_fee=mem["fastest_fee"],
        hour_fee=mem["hour_fee"],
        hashrate=hr["hashrate_eh"],
        fng_value=fng["value"],
        fng_label=fng["label"],
        headlines=headlines,
        date=datetime.now(timezone.utc).strftime("%B %d, %Y"),
    )

    key = get_key("ANTHROPIC_API_KEY")
    if not key:
        print("[writer] ERROR: No ANTHROPIC_API_KEY available")
        return _fallback_script(data)

    print("[writer] Generating script via Claude...")
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )

        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rfind("```")]
            script = json.loads(text)
            script["data"] = data
            script["generated_at"] = datetime.now(timezone.utc).isoformat()
            print("[writer] Script generated successfully")
            return script
        else:
            print(f"[writer] Claude API error {r.status_code}: {r.text[:200]}")
            return _fallback_script(data)

    except json.JSONDecodeError as e:
        print(f"[writer] JSON parse error: {e}")
        return _fallback_script(data)
    except Exception as e:
        print(f"[writer] Error: {e}")
        return _fallback_script(data)


def _fallback_script(data: dict) -> dict:
    """Generate a basic script without Claude API."""
    btc = data["btc"]
    fng = data["fng"]
    mem = data["mempool"]

    price_str = f"${btc['price']:,.0f}"
    direction = "up" if btc["change_24h"] > 0 else "down"

    return {
        "hook": f"Bitcoin is at {price_str}. Here's what you need to know.",
        "the_number": (
            f"Bitcoin trades at {price_str}, {direction} {abs(btc['change_24h']):.1f} percent "
            f"in the last twenty-four hours. The Fear and Greed Index sits at {fng['value']}, "
            f"reading {fng['label']}. The number to watch today: {price_str}."
        ),
        "the_signal": (
            f"The mempool holds {mem['tx_count']:,} unconfirmed transactions. "
            f"Priority fees are running at {mem['fastest_fee']} sats per vbyte. "
            f"Network activity tells the real story of adoption."
        ),
        "the_take": (
            "The fundamentals remain unchanged. Bitcoin continues to do what Bitcoin does. "
            "Price is a distraction. The network is the signal. "
            "Block by block, the protocol advances."
        ),
        "signoff": "This has been the Oracle Briefing from Protocol Pulse. Stay sovereign. Stay informed.",
        "full_script": None,  # Will be assembled by producer
        "thumbnail_headline": f"BTC {price_str} — {fng['label']}",
        "overlay_suggestions": {
            "the_number": "price_chart",
            "the_signal": "mempool_viz",
            "the_take": "price_chart",
        },
        "data": data,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fallback": True,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    if test_mode:
        print("=== Oracle Briefing Writer (TEST MODE) ===\n")
        script = generate_script(test=True)
    else:
        print("=== Oracle Briefing Writer ===\n")
        script = generate_script()

    # Build full_script if not set
    if not script.get("full_script"):
        script["full_script"] = " ".join([
            script["hook"],
            script["the_number"],
            script["the_signal"],
            script["the_take"],
            script["signoff"],
        ])

    print("\n--- SCRIPT ---")
    for seg in ["hook", "the_number", "the_signal", "the_take", "signoff"]:
        print(f"\n[{seg.upper()}]")
        print(script.get(seg, ""))

    print(f"\n--- FULL SCRIPT ({len(script['full_script'].split())} words) ---")
    print(script["full_script"])

    print(f"\n--- THUMBNAIL ---")
    print(script.get("thumbnail_headline", ""))

    # Dump JSON
    out = {k: v for k, v in script.items() if k != "data"}
    print(f"\n--- JSON ---")
    print(json.dumps(out, indent=2))
