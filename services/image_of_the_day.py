#!/usr/bin/env python3
"""
image_of_the_day.py — Protocol Pulse daily Bitcoin education image generator.
Generates one image per day using Grok Aurora API in Protocol Pulse visual style.
Saves to data/social_queue/image_of_the_day.png for tweet_machine.py to attach.
"""
import json, os, sys, random, base64, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
OUT_PATH = BASE / "data/social_queue/image_of_the_day.png"
LOG_PATH = BASE / "logs/image_of_the_day.log"
BRIEF_PATH = BASE / "data/intelligence/morning_intelligence_brief.json"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_env():
    env = {}
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f: f.write(line + "\n")

FORMATS = ["TYPE_BOMB", "ICON_PUNCH", "PROPAGANDA_POSTER", "CHARACTER_DROP", "PHOTO_PUNCH"]

STATEMENTS = [
    "FIAT IS LEGALIZED TIME THEFT.",
    "21 MILLION. THAT IS THE DEAL.",
    "NOT YOUR KEYS. NOT YOUR COINS.",
    "PRINTING MONEY IS A MORAL VIOLATION.",
    "QUESTIONING MONEY MEANS QUESTIONING REALITY.",
    "BITCOIN FIXES THIS.",
    "GO WHERE YOU ARE TREATED BEST.",
    "THE MACHINES NEVER LIE.",
    "SOUND MONEY OR SERFDOM.",
    "OPT OUT.",
    "STACK SATS. STAY SOVEREIGN.",
    "MATHEMATICS DOES NOT LIE.",
    "YOUR SAVINGS ARE BEING STOLEN.",
    "BUILD THE ALTERNATIVE.",
    "PROPERTY RIGHTS BASED ON MATHEMATICAL CONSENT.",
    "THE HALVING IS NOT NEGOTIABLE.",
    "ENERGY IS MONEY. BITCOIN IS ENERGY.",
    "DECENTRALIZED. UNCENSORABLE. UNSTOPPABLE.",
]

FORMAT_DETAILS = {
    "TYPE_BOMB": "Pure black background #000000. Stack 2-3 lines of massive all-caps bold white and red text filling 80% of the frame. No illustration. Pure confrontational typography.",
    "ICON_PUNCH": "Pure black background. One large flat vector icon centered (use red #CC2222 and cream #F5E6C8 and black). Bold all-caps text above or below. Bitcoin symbol integrated naturally.",
    "PROPAGANDA_POSTER": "Full solid red #CC2222 background with subtle paper texture. Black silhouette illustration (choose: hands, tanks, hourglasses, crowds, surveillance cameras, or printing presses). Cream #F5E6C8 text in black banner strip at bottom. Soviet-era WPA poster aesthetic.",
    "CHARACTER_DROP": "Pure black background. Bold red-tinted flat vector illustrated figure (tuxedo, cypherpunk, or working person). Graphic novel style, high contrast. Bold white and red statement below figure.",
    "PHOTO_PUNCH": "Dramatic photorealistic scene relevant to financial sovereignty or Bitcoin. Dark edges vignette. Simple white all-caps bold text overlay at bottom third. Cinematic lighting.",
}

def pick_format_and_statement():
    day_of_year = datetime.now().timetuple().tm_yday
    fmt = FORMATS[day_of_year % len(FORMATS)]
    # Try to use today narrative from morning brief
    statement = None
    if BRIEF_PATH.exists():
        try:
            brief = json.loads(BRIEF_PATH.read_text())
            narratives = brief.get("dominant_narratives", [])
            if narratives:
                # Convert narrative to punchy statement via selection
                statement = None  # Let Grok pick based on context
        except Exception:
            pass
    if not statement:
        statement = STATEMENTS[day_of_year % len(STATEMENTS)]
    return fmt, statement

def build_prompt(fmt, statement):
    fmt_detail = FORMAT_DETAILS[fmt]
    return f"""Create a 1:1 square social media image in Protocol Pulse Bitcoin education visual style.

STATEMENT TO CONVEY: {statement}
FORMAT: {fmt} — {fmt_detail}

STRICT COLOR SYSTEM (no exceptions):
- Pure black #000000 or solid red #CC2222 for background only
- Pure white #FFFFFF for primary text
- Bitcoin red #CC2222 for accent text or illustrations  
- Warm cream/ivory #F5E6C8 for secondary elements
- Zero other colors

TYPOGRAPHY: All caps only. Heavy condensed bold Impact-weight sans-serif. 
2-4 words per line maximum. Confrontational placement. Never centered decoratively.

BRANDING: Bottom-right corner — tiny red ECG/waveform line icon with "PROTOCOL PULSE" 
text in small caps. No more than 6% of frame.

NEVER: gradients, drop shadows, more than 3 colors, lowercase text, altcoins, 
moon rockets, lambos, complex patterned backgrounds, serif fonts.

STYLE REFERENCE: Soviet constructivist meets Bitcoin maximalist. Looks like 
a protest sign or revolutionary poster. Uncomfortable to scroll past. Sharp 
flat design. High contrast. Instantly readable at thumbnail size."""

def generate_image(prompt, env):
    api_key = env.get("XAI_API_KEY", "")
    if not api_key:
        log("ERROR: XAI_API_KEY not found")
        return False
    
    payload = json.dumps({
        "model": "aurora",
        "prompt": prompt,
        "n": 1,
        "response_format": "b64_json",
    }).encode()
    
    req = urllib.request.Request(
        "https://api.x.ai/v1/images/generations",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            b64 = data["data"][0]["b64_json"]
            img_bytes = base64.b64decode(b64)
            OUT_PATH.write_bytes(img_bytes)
            log(f"Image saved: {OUT_PATH} ({len(img_bytes)//1024}KB)")
            return True
    except urllib.error.HTTPError as e:
        log(f"API error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        log(f"Error: {e}")
        return False

def main():
    log("=== IMAGE OF THE DAY ===")
    env = load_env()
    fmt, statement = pick_format_and_statement()
    log(f"Format: {fmt} | Statement: {statement}")
    prompt = build_prompt(fmt, statement)
    log("Generating via Grok Aurora...")
    success = generate_image(prompt, env)
    if success:
        log("Done. Tweet machine will attach on next run.")
    else:
        log("Failed. Tweet will go text-only today.")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
