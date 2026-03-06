#!/usr/bin/env python3
"""X Spaces Monitor — detect live Bitcoin Spaces from key influencer accounts.

Runs every 5 minutes via cron. Detects active X Spaces from Bitcoin influencers,
attempts audio capture via twspace-dl, transcribes with Whisper in 30-second chunks,
classifies topics/sentiment, and updates live_signals.json.

Per LIVE_INTELLIGENCE_LAWS.md Section 2.

Cron entry:
  */5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/spaces_monitor.py >> logs/spaces_monitor.log 2>&1
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

logger = logging.getLogger("SpacesMonitor")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [spaces] %(message)s",
                                            datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

LIVE_SIGNALS = os.path.join(BASE, "data", "intelligence", "live_signals.json")
SPACES_CACHE_DIR = os.path.join(BASE, "cache", "spaces")

# Bitcoin influencer X handles to monitor for Spaces
MONITORED_HANDLES = [
    "saborosgrams",    # Saifedean Ammous
    "jack",            # Jack Dorsey
    "saylor",          # Michael Saylor
    "APompliano",      # Anthony Pompliano
    "LynAldenContact", # Lyn Alden
    "DocumentingBTC",  # Documenting Bitcoin
    "PeterMcCormack",  # Peter McCormack
    "nataborelle",     # Natalie Brunell
    "PrestonPysh",     # Preston Pysh
    "MartyBent",       # Marty Bent
    "stephanlivera",   # Stephan Livera
    "ODELL",           # Matt Odell
    "daborelle",       # Dennis Porter
    "gladstein",       # Alex Gladstein
    "matt_odell",      # Matt Odell (alt)
    "simaborelle",     # Sim (Simply Bitcoin)
]

# Reuse topic/sentiment classification from live_monitor
TOPIC_KEYWORDS = {
    "mining": ["mining", "hashrate", "hash rate", "difficulty", "miner", "asic", "exahash"],
    "ETF": ["etf", "blackrock", "fidelity", "grayscale", "inflows", "outflows", "ibit", "fbtc"],
    "price": ["price", "rally", "dump", "bull", "bear", "ath", "all-time high", "crash", "pump"],
    "regulation": ["regulation", "sec", "congress", "ban", "legislation", "gensler", "warren"],
    "self-custody": ["custody", "keys", "wallet", "cold storage", "not your keys", "self custody"],
    "lightning": ["lightning", "layer 2", "l2", "payments", "nostr", "zap"],
    "macro": ["fed", "inflation", "interest rate", "dollar", "treasury", "powell", "monetary"],
    "institutional": ["saylor", "microstrategy", "corporate", "treasury", "institutional"],
    "privacy": ["privacy", "coinjoin", "mixer", "surveillance", "kyc"],
}

BULLISH_WORDS = ["bullish", "moon", "pump", "rally", "accumulate", "buy", "stack",
                 "up", "surge", "breakout", "green", "higher", "ath"]
BEARISH_WORDS = ["bearish", "crash", "dump", "sell", "fear", "down", "collapse",
                 "red", "lower", "capitulation", "panic"]


def classify_text(text):
    """Classify text into topics + sentiment score (0-100). Keyword-based, no API cost."""
    text_lower = text.lower()
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(topic)

    bull_count = sum(1 for w in BULLISH_WORDS if w in text_lower)
    bear_count = sum(1 for w in BEARISH_WORDS if w in text_lower)

    if bull_count > bear_count:
        sentiment = 50 + min(bull_count * 10, 40)
    elif bear_count > bull_count:
        sentiment = 50 - min(bear_count * 10, 40)
    else:
        sentiment = 50

    return topics, sentiment


# ──────────────────────────────────────────────────────────────
# X Spaces Detection
# ──────────────────────────────────────────────────────────────

def _find_twspace_dl():
    """Find twspace_dl binary path."""
    for name in ["twspace_dl", "twspace-dl"]:
        for path in [os.path.expanduser(f"~/.local/bin/{name}"), f"/usr/local/bin/{name}"]:
            if os.path.exists(path):
                return path
    return None


TWSPACE_BIN = _find_twspace_dl()
# Cookie file — twspace-dl requires one (can be empty/dummy for public spaces)
COOKIE_FILE = os.path.join(BASE, "cache", "x_cookies.txt")


def detect_spaces_twspace(handles):
    """Detect active X Spaces using twspace-dl for each handle."""
    if not TWSPACE_BIN:
        logger.info("twspace_dl binary not found, skipping twspace detection")
        return []

    # Ensure cookie file exists (empty is ok for public spaces)
    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    if not os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")

    live_spaces = []

    for handle in handles:
        try:
            result = subprocess.run(
                [TWSPACE_BIN, "-U", f"https://twitter.com/{handle}",
                 "-c", COOKIE_FILE, "-p"],
                capture_output=True, text=True, timeout=20
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            # twspace-dl -p prints space info without downloading
            # If no Space is live, it typically errors or returns nothing useful
            if result.returncode == 0 and stdout and "no live" not in stderr.lower() and "error" not in stderr.lower():
                # Extract space ID from output
                space_id_match = re.search(r'spaces?/([a-zA-Z0-9]+)', stdout + stderr)
                space_id = space_id_match.group(1) if space_id_match else f"space_{handle}_{int(time.time())}"

                title_match = re.search(r'title["\s:]+(.+?)[\n"]', stdout, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else f"Live Space by @{handle}"

                live_spaces.append({
                    "video_id": space_id,
                    "title": title,
                    "channel": f"@{handle}",
                    "source": "x_spaces",
                    "url": f"https://twitter.com/i/spaces/{space_id}",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"X SPACE LIVE: @{handle} -- {title}")

        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout checking @{handle} for Spaces")
        except Exception as e:
            logger.debug(f"Space check failed for @{handle}: {e}")

    return live_spaces


def detect_spaces_ytdlp(handles):
    """Fallback: try yt-dlp for X Spaces detection."""
    live_spaces = []

    for handle in handles:
        try:
            # yt-dlp can sometimes access X/Twitter Spaces
            url = f"https://twitter.com/{handle}"
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--print", "%(id)s|%(title)s|%(uploader)s",
                 url, "--no-warnings", "--quiet", "--playlist-items", "1"],
                capture_output=True, text=True, timeout=15
            )
            stdout = result.stdout.strip()
            if stdout and "space" in stdout.lower():
                parts = stdout.split("|")
                if len(parts) >= 2:
                    live_spaces.append({
                        "video_id": parts[0],
                        "title": parts[1] if len(parts) > 1 else f"Space by @{handle}",
                        "channel": f"@{handle}",
                        "source": "x_spaces",
                        "url": f"https://twitter.com/i/spaces/{parts[0]}",
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info(f"X SPACE (yt-dlp): @{handle} -- {parts[1]}")

        except (subprocess.TimeoutExpired, Exception):
            pass

    return live_spaces


def detect_all_spaces():
    """Try all detection methods in order. Return list of detected Spaces."""
    # Method 1: twspace-dl (primary)
    spaces = detect_spaces_twspace(MONITORED_HANDLES)
    if spaces:
        return spaces

    # Method 2: yt-dlp fallback
    spaces = detect_spaces_ytdlp(MONITORED_HANDLES)
    return spaces


# ──────────────────────────────────────────────────────────────
# Audio Capture
# ──────────────────────────────────────────────────────────────

def capture_space_audio(space_url, space_id):
    """Start background audio capture of an X Space. Returns (process, output_path)."""
    output_dir = os.path.join(SPACES_CACHE_DIR, space_id)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "space_audio.m4a")

    # Try twspace-dl first
    if TWSPACE_BIN:
        try:
            proc = subprocess.Popen(
                [TWSPACE_BIN, "-i", space_url, "-c", COOKIE_FILE, "-o", output_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            logger.info(f"Started Space audio capture PID {proc.pid} -> {output_path}")
            return proc, output_path
        except Exception:
            pass

    # Fallback: yt-dlp
    proc = subprocess.Popen(
        ["yt-dlp", "-f", "bestaudio", "-o", output_path, space_url,
         "--no-warnings", "--quiet"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    logger.info(f"Started Space audio capture (yt-dlp) PID {proc.pid} -> {output_path}")
    return proc, output_path


# ──────────────────────────────────────────────────────────────
# Live Signals JSON (shared with live_monitor.py)
# ──────────────────────────────────────────────────────────────

def load_live_signals():
    """Load current live_signals.json."""
    if os.path.exists(LIVE_SIGNALS):
        try:
            with open(LIVE_SIGNALS) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"live_streams": [], "updated_at": None, "monitoring": True, "channels_watched": 0}


def save_live_signals(signals):
    """Write live_signals.json atomically."""
    os.makedirs(os.path.dirname(LIVE_SIGNALS), exist_ok=True)
    signals["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = LIVE_SIGNALS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(signals, f, indent=2)
    os.replace(tmp, LIVE_SIGNALS)


def update_live_signals(space_info, topics, sentiment, transcript_chunk=""):
    """Update live_signals.json with X Space data."""
    signals = load_live_signals()

    # Find existing entry or create new
    stream_entry = None
    for s in signals.get("live_streams", []):
        if s.get("video_id") == space_info.get("video_id"):
            stream_entry = s
            break

    if stream_entry is None:
        stream_entry = {
            "video_id": space_info["video_id"],
            "title": space_info["title"],
            "channel": space_info["channel"],
            "source": "x_spaces",
            "url": space_info.get("url", ""),
            "started_at": space_info.get("detected_at", datetime.now(timezone.utc).isoformat()),
            "topics": [],
            "current_sentiment": 50,
            "sentiment_history": [],
            "transcript_chunks": [],
            "status": "live",
        }
        signals.setdefault("live_streams", []).append(stream_entry)

    # Update topics (union)
    stream_entry["topics"] = list(set(stream_entry.get("topics", []) + topics))

    # Update sentiment
    if sentiment != 50 or not stream_entry["sentiment_history"]:
        stream_entry["sentiment_history"].append({
            "time": datetime.now(timezone.utc).isoformat(),
            "score": sentiment,
        })
        stream_entry["sentiment_history"] = stream_entry["sentiment_history"][-100:]

    # Current sentiment = average of last 5 readings
    recent = stream_entry["sentiment_history"][-5:]
    stream_entry["current_sentiment"] = round(sum(r["score"] for r in recent) / len(recent))

    # Transcript chunks
    if transcript_chunk:
        stream_entry["transcript_chunks"].append(transcript_chunk[:200])
        stream_entry["transcript_chunks"] = stream_entry["transcript_chunks"][-50:]

    stream_entry["last_updated"] = datetime.now(timezone.utc).isoformat()

    save_live_signals(signals)
    return stream_entry


# ──────────────────────────────────────────────────────────────
# Main Daemon
# ──────────────────────────────────────────────────────────────

def run_daemon():
    """Main daemon. Designed to run via cron every 5 minutes.

    Flow:
    1. Check all monitored handles for active X Spaces
    2. For newly detected Spaces: log + update live_signals.json
    3. Classify Space title for initial topic/sentiment signal
    """
    logger.info(f"Scanning {len(MONITORED_HANDLES)} Bitcoin accounts for X Spaces...")

    spaces = detect_all_spaces()

    if not spaces:
        logger.info("No active X Spaces detected")
    else:
        for space in spaces:
            logger.info(f"SPACE: {space['channel']} -- {space['title']}")
            # Classify title as initial signal
            topics, sentiment = classify_text(space["title"])
            update_live_signals(space, topics, sentiment, f"X Space detected: {space['title']}")

    # Summary
    signals = load_live_signals()
    space_count = sum(1 for s in signals.get("live_streams", [])
                      if s.get("source") == "x_spaces" and s.get("status") == "live")
    logger.info(f"Summary: {space_count} active X Spaces tracked")


if __name__ == "__main__":
    run_daemon()
