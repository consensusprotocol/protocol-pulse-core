#!/usr/bin/env python3
"""PBX Weekly Report — Coin Bureau style deep analysis.

2x per week (Tuesday + Friday). 3-5 minutes each. Cost: ~$6-10 per video = ~$50/month.

Style: Guy from Coin Bureau but with CYPHERPUNK LIBERTARIAN TWIST.
- Direct to camera, authoritative
- Data-heavy with opinions
- Austrian economics lens
- Anti-surveillance, pro-sovereignty messaging
- Contrarian takes, not mainstream narratives
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
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
from services.heygen_client import generate_and_download, PBX_AVATAR_ID, SARAH_VOICE_ID

# Voice for PBX — Thanos Broadcaster
PBX_VOICE_ID = "054af44a167344d0af2722fdfef08d17"


# ---------------------------------------------------------------------------
# Script prompt
# ---------------------------------------------------------------------------

PBX_SCRIPT_PROMPT = """You are writing a script for PBX, the founder of Protocol Pulse.
This is his WEEKLY REPORT — a Coin Bureau-style deep-dive but with a strong cypherpunk and libertarian philosophy.

PBX's voice:
- Direct. No filler. Every sentence carries weight.
- Austrian economics perspective — sound money, free markets, individual sovereignty
- NOT conspiratorial — data-driven contrarianism
- Cites specific on-chain data, regulatory filings, historical parallels
- Ends with: "Stay free. Stay sovereign. This is PBX, Protocol Pulse."

FORMAT: 2-3 minute script (~300-450 words)

STRUCTURE:
1. Hook — "This week, something happened that changes everything for Bitcoin holders..." (dramatic but factual)
2. Main story — deep analysis of the #1 Bitcoin story this week
3. Second story — supporting trend or development
4. The Cypherpunk Take — what this means for sovereignty and freedom (THIS IS THE SIGNATURE SECTION)
5. Action item — one concrete thing the viewer should do this week
6. Sign-off: "Stay free. Stay sovereign. This is PBX, Protocol Pulse."

RULES:
- Output ONLY the spoken script, no stage directions or brackets
- 300-450 words
- Use specific numbers and data points
- One contrarian take

This week's top stories and data:
{stories}

BTC price: {btc_price}
"""


# ---------------------------------------------------------------------------
# Intelligence gathering
# ---------------------------------------------------------------------------

def gather_weekly_intel() -> list:
    """Gather the week's top Bitcoin stories from Protocol Pulse articles."""
    try:
        cmd_payload = json.dumps({
            "token": "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552",
            "cmd": (
                "cd /home/runner/workspace && python3 -c \""
                "import sqlite3, json; "
                "db=sqlite3.connect('instance/protocol_pulse.db'); "
                "rows=db.execute('SELECT title, summary FROM articles ORDER BY published_at DESC LIMIT 20').fetchall(); "
                "print(json.dumps([{'title':r[0],'summary':r[1]} for r in rows]))"
                "\""
            ),
        }).encode()
        req = urllib.request.Request(
            "https://protocolpulse.replit.app/api/admin/exec",
            data=cmd_payload,
            headers={"Content-Type": "application/json"},
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        stdout = resp.get("stdout", "")
        if stdout.strip():
            stories = json.loads(stdout.strip())
            if stories:
                return stories[:10]
    except Exception as e:
        print(f"  [intel] Failed to fetch from Replit: {e}")

    return [
        {
            "title": "Bitcoin weekly summary",
            "summary": "Market consolidation with institutional accumulation",
        }
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_pbx_report(test: bool = False) -> str | None:
    """Generate a PBX Weekly Report video."""
    ts = datetime.now()
    date_str = ts.strftime("%Y-%m-%d")

    out_dir = os.path.join(os.path.dirname(__file__), "output", date_str)
    os.makedirs(out_dir, exist_ok=True)

    # Gather intel
    print("  [intel] Gathering weekly intelligence...")
    stories = gather_weekly_intel()
    print(f"  [intel] Got {len(stories)} stories")

    # BTC price
    btc_price = "$97,000"
    try:
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            btc_price = f"${r.json().get('USD', 97000):,.0f}"
    except Exception:
        pass

    print(f"\n{'='*60}")
    print(f"  PBX WEEKLY REPORT")
    print(f"  {date_str} | BTC: {btc_price}")
    print(f"{'='*60}\n")

    # Write script
    print("  [script] Generating PBX script...")
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": PBX_SCRIPT_PROMPT.format(
                    stories=json.dumps(stories, indent=2), btc_price=btc_price
                ),
            }
        ],
    )
    script = response.content[0].text
    word_count = len(script.split())
    est_seconds = int(word_count / 2.5)
    print(f"  [script] {len(script)} chars, {word_count} words, ~{est_seconds}s")

    script_path = os.path.join(out_dir, f"pbx_report_{date_str}.txt")
    with open(script_path, "w") as f:
        f.write(script)

    # Generate HeyGen video
    video_path = os.path.join(out_dir, f"pbx_report_{date_str}.mp4")
    result = generate_and_download(
        text=script,
        output_path=video_path,
        avatar_id=PBX_AVATAR_ID,
        voice_id=PBX_VOICE_ID,
        title=f"PBX Report — {date_str}",
        test=test,
    )

    if result:
        print(f"\n  OK PBX Report saved: {result}")
    else:
        print(f"\n  FAIL PBX Report generation failed")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PBX Weekly Report — HeyGen avatar")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use HeyGen test mode (free, watermarked)",
    )
    args = parser.parse_args()
    run_pbx_report(args.test)
