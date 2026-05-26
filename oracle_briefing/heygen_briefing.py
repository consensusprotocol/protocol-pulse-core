#!/usr/bin/env python3
"""Oracle Briefing — 3x daily avatar stage briefings using HeyGen Sarah avatar.

Schedule:
  Morning  (8 AM EST)  — Market open recap + overnight moves
  Midday   (1 PM EST)  — Breaking developments + institutional moves
  Evening  (6 PM EST)  — Day summary + what to watch tomorrow

Each briefing: 45-90 seconds. Cost: ~$1 each = $3/day = ~$90/month.
"""
import argparse
import json
import os
import sys
from datetime import datetime

import requests

# Add parent for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load env from oracle_briefing/.env and root .env
for env_path in [
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
]:
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import anthropic
from pp_services.heygen_client import generate_and_download, SARAH_AVATAR_ID


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

def get_market_data() -> dict:
    """Fetch current BTC market data."""
    data = {"btc_price": "$97,000", "change_24h": "N/A", "fear_greed": "N/A"}
    try:
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            data["btc_price"] = f"${r.json().get('USD', 97000):,.0f}"
    except Exception:
        pass
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=5,
        )
        if r.status_code == 200:
            btc = r.json().get("bitcoin", {})
            change = btc.get("usd_24h_change")
            if change is not None:
                data["change_24h"] = f"{change:+.1f}%"
    except Exception:
        pass
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        if r.status_code == 200:
            fng = r.json().get("data", [{}])[0]
            data["fear_greed"] = f"{fng.get('value', '?')} — {fng.get('value_classification', '?')}"
    except Exception:
        pass
    return data


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------

PROMPTS = {
    "morning": """Write a 60-second Oracle Briefing for Protocol Pulse's morning update.

VOICE: Sarah, the Oracle — confident, data-driven, slightly edgy. Think Coin Bureau's Guy but female and more cypherpunk.
TONE: Professional but not corporate. Sharp. Decisive. Occasionally drops a hot take.
AUDIENCE: Bitcoin-focused investors and cypherpunks. They know the basics.

Market data: {market_json}

Structure:
1. Cold open hook (1 sentence, dramatic)
2. Overnight price action + key level to watch
3. One major development (institutional move, regulatory, on-chain)
4. "Stay sovereign."

RULES:
- Under 150 words (= ~60 seconds spoken)
- No "hey guys", "what's up", "let's dive in"
- Use exact numbers, not vague language
- One contrarian take per briefing
- End with "Stay sovereign."
- Output ONLY the spoken script, no stage directions or brackets""",

    "midday": """Write a 60-second Oracle Briefing for Protocol Pulse's midday update.

VOICE: Sarah, the Oracle — sharp, breaking-news energy. Like she just got off a call with a source.
Market data: {market_json}

Structure:
1. "Breaking from the Oracle desk..." (only if actual breaking news, otherwise skip)
2. Biggest development since morning
3. On-chain signal or whale movement
4. What it means for the next 24 hours
5. "Stay sovereign."

RULES:
- Under 150 words
- Output ONLY the spoken script, no stage directions or brackets""",

    "evening": """Write a 60-second Oracle Briefing for Protocol Pulse's evening wrap.

VOICE: Sarah — reflective, connecting dots. The "big picture" briefing.
Market data: {market_json}

Structure:
1. Day summary in one sentence
2. Winner and loser of the day
3. Most important chart or data point
4. What to watch overnight / tomorrow
5. "Stay sovereign. See you at dawn."

RULES:
- Under 150 words
- Close with forward-looking intelligence
- Output ONLY the spoken script, no stage directions or brackets""",
}


def write_briefing_script(briefing_type: str, market_data: dict) -> str:
    """Generate a briefing script using Claude."""
    client = anthropic.Anthropic()
    prompt = PROMPTS.get(briefing_type, PROMPTS["morning"]).format(
        market_json=json.dumps(market_data)
    )
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_briefing(briefing_type: str = "morning", test: bool = False,
                 dry_run: bool = False) -> dict | None:
    """Generate and save a complete Oracle Briefing."""
    ts = datetime.now()
    date_str = ts.strftime("%Y-%m-%d")
    time_str = ts.strftime("%H%M")

    out_dir = os.path.join(os.path.dirname(__file__), "output", date_str)
    os.makedirs(out_dir, exist_ok=True)

    # Step 1: Market data
    market = get_market_data()
    print(f"\n{'='*60}")
    print(f"  ORACLE BRIEFING — {briefing_type.upper()}{' [DRY RUN]' if dry_run else ''}")
    print(f"  {date_str} {time_str} | BTC: {market['btc_price']}")
    print(f"{'='*60}\n")

    # Step 2: Write script
    print("  [script] Generating briefing script...")
    script = write_briefing_script(briefing_type, market)
    word_count = len(script.split())
    est_seconds = int(word_count / 2.5)
    print(f"  [script] {len(script)} chars, {word_count} words, ~{est_seconds}s")

    script_path = os.path.join(out_dir, f"briefing_{briefing_type}_{time_str}.txt")
    with open(script_path, "w") as f:
        f.write(script)

    if dry_run:
        print(f"\n  [dry-run] Script saved: {script_path}")
        print(f"  [dry-run] Avatar: {SARAH_AVATAR_ID}")
        print(f"  [dry-run] Would generate HeyGen video ({est_seconds}s est)")
        print(f"\n  Script preview:\n  {script[:300]}...")
        return {"script": script_path, "type": briefing_type, "dry_run": True}

    # Step 3: Generate HeyGen video
    video_path = os.path.join(out_dir, f"briefing_{briefing_type}_{time_str}.mp4")
    result = generate_and_download(
        text=script,
        output_path=video_path,
        avatar_id=SARAH_AVATAR_ID,
        title=f"Oracle Briefing — {briefing_type.title()}",
        test=test,
    )

    if result:
        print(f"\n  OK Briefing saved: {result}")
        return {"video": result, "script": script_path, "type": briefing_type}
    else:
        print(f"\n  FAIL Briefing generation failed")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Briefing — HeyGen Sarah avatar")
    parser.add_argument(
        "--type",
        choices=["morning", "midday", "evening"],
        default="morning",
        help="Briefing type",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use HeyGen test mode (free, watermarked)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate script only, skip HeyGen video generation",
    )
    args = parser.parse_args()
    run_briefing(args.type, args.test, args.dry_run)
