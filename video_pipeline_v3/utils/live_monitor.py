#!/usr/bin/env python3
"""Live Stream Monitor — detect YouTube Live + X Spaces from partner channels.

Runs every 5 minutes via cron. Detects active live streams from Tier 1+2 channels,
captures audio in real-time, transcribes with Whisper in 30-second chunks,
classifies topics/sentiment, and updates live_signals.json.

Per LIVE_INTELLIGENCE_LAWS.md.

Cron entry:
  */5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/live_monitor.py >> logs/live_monitor.log 2>&1
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

# Ensure project root is on path
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import yaml

logger = logging.getLogger("LiveMonitor")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [live] %(message)s",
                                            datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

CHANNELS_FILE = os.path.join(BASE, "channels.yaml")
LIVE_SIGNALS = os.path.join(BASE, "data", "intelligence", "live_signals.json")
LIVE_CACHE_DIR = os.path.join(BASE, "cache", "live")

# ──────────────────────────────────────────────────────────────
# Topic + Sentiment Classification (keyword-based, $0 cost)
# ──────────────────────────────────────────────────────────────

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
# Live Stream Detection
# ──────────────────────────────────────────────────────────────

def load_channels(max_priority=2):
    """Load Tier 1+2 channels from channels.yaml."""
    if not os.path.exists(CHANNELS_FILE):
        logger.error(f"channels.yaml not found at {CHANNELS_FILE}")
        return []

    with open(CHANNELS_FILE) as f:
        config = yaml.safe_load(f)

    channels = config.get("channels", [])
    # Also check mainstream if present
    channels += config.get("mainstream", [])

    # Filter to Tier 1+2 only
    filtered = [ch for ch in channels if ch.get("priority", ch.get("tier", 99)) <= max_priority]
    return filtered


def detect_live_streams(channels):
    """Check all Tier 1+2 channels for active live streams via yt-dlp."""
    live_streams = []

    for ch in channels:
        url = ch.get("url", "")
        name = ch.get("name", ch.get("handle", "unknown"))
        if not url:
            continue

        try:
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--match-filter", "is_live",
                 "--print", "%(id)s|%(title)s|%(uploader)s",
                 url + "/streams", "--max-downloads", "1",
                 "--no-warnings", "--quiet"],
                capture_output=True, text=True, timeout=20
            )
            stdout = result.stdout.strip()
            if stdout:
                for line in stdout.split("\n"):
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        live_streams.append({
                            "video_id": parts[0],
                            "title": parts[1],
                            "channel": name,
                            "source": "youtube_live",
                            "url": f"https://www.youtube.com/watch?v={parts[0]}",
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                        })
                        logger.info(f"LIVE DETECTED: {name} -- {parts[1]}")
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking {name} for live streams")
        except Exception as e:
            logger.warning(f"Live check failed for {name}: {e}")

    return live_streams


# ──────────────────────────────────────────────────────────────
# Audio Capture (background process)
# ──────────────────────────────────────────────────────────────

def capture_live_audio(video_url, video_id):
    """Start background audio capture of a live stream. Returns (process, output_path)."""
    output_dir = os.path.join(LIVE_CACHE_DIR, video_id)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "live_audio.m4a")

    proc = subprocess.Popen(
        ["yt-dlp", "-f", "bestaudio", "--live-from-start",
         "-o", output_path, video_url,
         "--no-warnings", "--quiet"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    logger.info(f"Started audio capture PID {proc.pid} -> {output_path}")
    return proc, output_path


# ──────────────────────────────────────────────────────────────
# Chunked Transcription (Whisper on GPU)
# ──────────────────────────────────────────────────────────────

def transcribe_chunk(audio_path, start_time, duration=30):
    """Transcribe a 30-second chunk using Whisper. Returns text or empty string."""
    chunk_path = audio_path + f".chunk_{start_time}.wav"

    # Extract chunk with ffmpeg
    result = subprocess.run(
        ["ffmpeg", "-ss", str(start_time), "-t", str(duration),
         "-i", audio_path, "-ar", "16000", "-ac", "1", chunk_path,
         "-y", "-loglevel", "quiet"],
        capture_output=True, timeout=15
    )

    if not os.path.exists(chunk_path) or os.path.getsize(chunk_path) < 1000:
        # Chunk too small or missing — stream may not have enough data yet
        if os.path.exists(chunk_path):
            os.remove(chunk_path)
        return ""

    try:
        import whisper
        model = whisper.load_model("base", device="cuda")
        result = model.transcribe(chunk_path)
        text = result.get("text", "").strip()
        return text
    except Exception as e:
        logger.warning(f"Whisper transcription failed for chunk at {start_time}s: {e}")
        return ""
    finally:
        if os.path.exists(chunk_path):
            os.remove(chunk_path)


# ──────────────────────────────────────────────────────────────
# Live Signals JSON Management
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


def update_live_signals(stream_info, topics, sentiment, transcript_chunk=""):
    """Update live_signals.json with new data from a detected/processed stream."""
    signals = load_live_signals()

    # Find existing stream entry or create new one
    stream_entry = None
    for s in signals.get("live_streams", []):
        if s.get("video_id") == stream_info.get("video_id"):
            stream_entry = s
            break

    if stream_entry is None:
        stream_entry = {
            "video_id": stream_info["video_id"],
            "title": stream_info["title"],
            "channel": stream_info["channel"],
            "source": stream_info.get("source", "youtube_live"),
            "url": stream_info.get("url", ""),
            "started_at": stream_info.get("detected_at", datetime.now(timezone.utc).isoformat()),
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
        # Keep last 100 sentiment points
        stream_entry["sentiment_history"] = stream_entry["sentiment_history"][-100:]

    # Current sentiment = average of last 5 readings
    recent = stream_entry["sentiment_history"][-5:]
    stream_entry["current_sentiment"] = round(sum(r["score"] for r in recent) / len(recent))

    # Transcript chunks (first 200 chars each, keep last 50)
    if transcript_chunk:
        stream_entry["transcript_chunks"].append(transcript_chunk[:200])
        stream_entry["transcript_chunks"] = stream_entry["transcript_chunks"][-50:]

    stream_entry["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Count channels watched
    signals["channels_watched"] = len(load_channels(max_priority=2))

    save_live_signals(signals)
    return stream_entry


def expire_stale_streams():
    """Mark streams as ended if not updated in 6 hours. Remove after 24 hours."""
    signals = load_live_signals()
    now = datetime.now(timezone.utc)
    changed = False

    active = []
    for s in signals.get("live_streams", []):
        last = s.get("last_updated") or s.get("started_at", "")
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            active.append(s)
            continue

        age_hours = (now - last_dt).total_seconds() / 3600

        if age_hours > 24:
            logger.info(f"EXPIRED: Removing {s.get('channel')} stream (>24h old)")
            changed = True
            continue  # drop it

        if age_hours > 6 and s.get("status") == "live":
            s["status"] = "ended"
            logger.info(f"ENDED: Marking {s.get('channel')} stream as ended (>6h stale)")
            changed = True

        active.append(s)

    if changed:
        signals["live_streams"] = active
        save_live_signals(signals)


# ──────────────────────────────────────────────────────────────
# Main Daemon
# ──────────────────────────────────────────────────────────────

def run_daemon():
    """Main daemon loop. Designed to run via cron every 5 minutes.

    Flow:
    1. Load Tier 1+2 channels
    2. Check each for active live streams (yt-dlp)
    3. For newly detected streams: log + update live_signals.json
    4. Expire stale streams (>6h ended, >24h removed)

    Note: Full chunked capture + transcription is Phase 2.
    This V1 detects and records live streams only.
    """
    channels = load_channels(max_priority=2)
    if not channels:
        logger.error("No channels loaded from channels.yaml")
        return

    logger.info(f"Scanning {len(channels)} Tier 1+2 channels for live streams...")

    live = detect_live_streams(channels)

    if not live:
        logger.info("No live streams detected")
    else:
        for stream in live:
            logger.info(f"LIVE: {stream['channel']} -- {stream['title']}")
            # Classify the title as initial signal
            topics, sentiment = classify_text(stream["title"])
            update_live_signals(stream, topics, sentiment, f"Live stream detected: {stream['title']}")

    # Clean up stale entries
    expire_stale_streams()

    # Summary
    signals = load_live_signals()
    active_count = sum(1 for s in signals.get("live_streams", []) if s.get("status") == "live")
    logger.info(f"Summary: {active_count} active live streams, "
                f"{len(signals.get('live_streams', []))} total tracked")


if __name__ == "__main__":
    run_daemon()
