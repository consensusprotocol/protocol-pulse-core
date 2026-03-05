#!/usr/bin/env python3
"""Channel Intelligence Daemon — background monitoring of partner channels.

Runs every 15 minutes via cron. Scans all channels for new uploads,
transcribes with Whisper (GPU), archives transcripts persistently,
and updates intelligence signals.

Per PIPELINE_LAWS Sections 21-22.

Cron entry:
  */15 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/channel_daemon.py >> logs/channel_daemon.log 2>&1
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

# Ensure project root is on path
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import yaml

logger = logging.getLogger("ChannelDaemon")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [daemon] %(message)s",
                                            datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

CHANNELS_FILE = os.path.join(BASE, "channels.yaml")
ARCHIVE_DIR = os.path.join(BASE, "data", "channel_archive")
KNOWN_VIDEOS_PATH = os.path.join(ARCHIVE_DIR, "known_videos.json")
INTELLIGENCE_DIR = os.path.join(BASE, "data", "intelligence")
AUDIO_CACHE_DIR = os.path.join(BASE, "downloads", "audio_cache")

# Topic keywords for simple classification
TOPIC_KEYWORDS = {
    "etf": ["etf", "ishares", "ibit", "blackrock etf", "grayscale", "gbtc", "spot etf"],
    "mining": ["mining", "hash rate", "hashrate", "difficulty", "miner", "asic", "antminer"],
    "price": ["price", "ath", "all-time high", "rally", "dump", "crash", "correction", "bull", "bear"],
    "regulation": ["sec", "regulation", "regulatory", "congress", "bill", "legislation", "ban"],
    "lightning": ["lightning", "layer 2", "l2", "channel", "liquidity", "payments"],
    "self-custody": ["self-custody", "self custody", "cold storage", "hardware wallet", "seed phrase", "not your keys"],
    "macro": ["fed", "federal reserve", "inflation", "interest rate", "cpi", "gdp", "dollar", "fiat"],
    "institutional": ["institutional", "corporate", "treasury", "microstrategy", "saylor", "wall street"],
    "privacy": ["privacy", "coinjoin", "tor", "vpn", "surveillance", "kyc"],
}


def load_channels() -> list:
    """Load all channels from channels.yaml (both core and mainstream)."""
    with open(CHANNELS_FILE) as f:
        config = yaml.safe_load(f)
    channels = list(config.get("channels", []))
    mainstream = config.get("mainstream", [])
    channels.extend(mainstream)
    return channels


def load_known_videos() -> dict:
    """Load the known videos index."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    if not os.path.exists(KNOWN_VIDEOS_PATH):
        return {"videos": {}, "last_scan": "", "total_archived": 0}
    with open(KNOWN_VIDEOS_PATH) as f:
        return json.load(f)


def save_known_videos(data: dict):
    """Save the known videos index."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(KNOWN_VIDEOS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_recent_videos(channel_url: str, channel_name: str,
                      max_age_hours: int = 48, max_videos: int = 5,
                      filter_keywords: list = None) -> list:
    """Get recent video IDs from a channel via yt-dlp --flat-playlist."""
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_str = cutoff.strftime("%Y%m%d")

    cmd = [
        "yt-dlp", "--flat-playlist",
        "--dateafter", cutoff_str,
        "--playlist-end", str(max_videos * 3),
        "--print", "%(id)s|%(title)s|%(duration)s|%(upload_date)s",
        "--no-warnings", "--quiet",
        channel_url + "/videos",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return []
    except subprocess.TimeoutExpired:
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split("|")
        if len(parts) < 4:
            continue

        video_id = parts[0]
        title = parts[1]
        try:
            duration = int(float(parts[2])) if parts[2] and parts[2] != "NA" else 0
        except (ValueError, TypeError):
            duration = 0
        upload_date = parts[3] if parts[3] != "NA" else ""

        # Skip shorts (<2min) and super long (>4hr)
        if duration < 120 or duration > 14400:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "channel": channel_name,
            "duration": duration,
            "upload_date": upload_date,
        })

    # Keyword filter for mainstream channels
    if filter_keywords and videos:
        videos = [v for v in videos
                  if any(kw.lower() in v["title"].lower() for kw in filter_keywords)]

    return videos[:max_videos]


def download_and_transcribe(video_id: str) -> dict | None:
    """Download audio and transcribe with Whisper. Returns transcript dict or None."""
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    wav_path = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.wav")

    # Download audio if not cached
    if not (os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000):
        url = f"https://www.youtube.com/watch?v={video_id}"
        output_template = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.%(ext)s")
        cmd = [
            "yt-dlp", "-x", "--audio-format", "wav",
            "--audio-quality", "5", "--no-playlist", "--quiet",
            "-o", output_template, url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            logger.warning(f"  Audio download timed out: {video_id}")
            return None

        # Convert if needed
        if not os.path.exists(wav_path):
            for ext in ["m4a", "mp3", "opus", "webm", "ogg"]:
                alt = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.{ext}")
                if os.path.exists(alt):
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", alt, "-ar", "16000", "-ac", "1", wav_path],
                        capture_output=True, timeout=120,
                    )
                    if os.path.exists(wav_path):
                        try:
                            os.remove(alt)
                        except OSError:
                            pass
                        break

    if not os.path.exists(wav_path):
        return None

    # Transcribe with Whisper
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cuda", compute_type="float16")
        t0 = time.time()
        segments_iter, info = model.transcribe(
            wav_path, language="en", word_timestamps=False,
            vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500),
        )
        text_parts = []
        timestamped = []
        for seg in segments_iter:
            seg_text = seg.text.strip()
            text_parts.append(seg_text)
            mm = int(seg.start // 60)
            ss = int(seg.start % 60)
            timestamped.append({"start": round(seg.start, 2),
                                "end": round(seg.end, 2),
                                "text": seg_text})
        elapsed = time.time() - t0
        duration = info.duration if hasattr(info, "duration") else 0
        speed = duration / elapsed if elapsed > 0 else 0
        logger.info(f"  Transcribed in {elapsed:.1f}s ({speed:.0f}x realtime)")
        return {
            "transcript_text": " ".join(text_parts),
            "timestamped_text": timestamped,
            "duration": round(duration, 2),
        }
    except Exception as e:
        logger.error(f"  Transcription failed: {e}")
        return None


def classify_topics(text: str) -> list:
    """Simple keyword-based topic classification."""
    text_lower = text.lower()
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(topic)
    return topics


def classify_sentiment(text: str) -> str:
    """Simple sentiment classification based on keyword balance."""
    text_lower = text.lower()
    bullish = sum(1 for w in ["bullish", "rally", "surge", "pump", "ath", "record",
                               "growth", "accumulation", "adoption", "inflows"]
                  if w in text_lower)
    bearish = sum(1 for w in ["bearish", "crash", "dump", "decline", "sell",
                               "outflows", "fear", "risk", "ban", "collapse"]
                  if w in text_lower)
    if bullish > bearish + 1:
        return "bullish"
    elif bearish > bullish + 1:
        return "bearish"
    return "neutral"


def update_daily_signals(archive_data: dict):
    """Rebuild daily_signals.json from the archive."""
    os.makedirs(INTELLIGENCE_DIR, exist_ok=True)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    topic_counts = {}  # topic -> set of channels
    topic_sentiments = {}

    for vid_id, entry in archive_data.get("videos", {}).items():
        archived_at = entry.get("archived_at", "")
        if not archived_at:
            continue
        try:
            ts = datetime.fromisoformat(archived_at.replace("Z", "+00:00"))
            if ts < cutoff:
                continue
        except (ValueError, TypeError):
            continue

        for topic in entry.get("topics", []):
            if topic not in topic_counts:
                topic_counts[topic] = set()
                topic_sentiments[topic] = []
            topic_counts[topic].add(entry.get("channel", ""))
            topic_sentiments[topic].append(entry.get("sentiment", "neutral"))

    # Build topic velocity list
    topic_velocity = []
    for topic, channels in topic_counts.items():
        sentiments = topic_sentiments[topic]
        bullish_count = sentiments.count("bullish")
        bearish_count = sentiments.count("bearish")
        dominant = "bullish" if bullish_count > bearish_count else (
            "bearish" if bearish_count > bullish_count else "neutral")
        score = min(100, len(channels) * 15 + bullish_count * 5)
        topic_velocity.append({
            "topic": topic,
            "channels": len(channels),
            "sentiment": dominant,
            "velocity_score": score,
        })

    topic_velocity.sort(key=lambda t: t["velocity_score"], reverse=True)

    # Breaking threshold: velocity >= 4 channels in recent window
    breaking = any(t["channels"] >= 4 for t in topic_velocity)

    signals = {
        "topic_velocity": topic_velocity,
        "breaking_threshold": breaking,
        "recommended_topics": [t["topic"] for t in topic_velocity[:3]],
        "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_videos_48h": sum(1 for v in archive_data.get("videos", {}).values()
                                if v.get("archived_at", "") > cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")),
    }

    signals_path = os.path.join(INTELLIGENCE_DIR, "daily_signals.json")
    with open(signals_path, "w") as f:
        json.dump(signals, f, indent=2)
    logger.info(f"Updated daily_signals.json: {len(topic_velocity)} topics, breaking={breaking}")


def scan_all_channels():
    """Main daemon entry: scan all channels, archive new videos."""
    logger.info("=" * 60)
    logger.info("CHANNEL DAEMON: Starting scan")

    channels = load_channels()
    known = load_known_videos()

    total_scanned = 0
    new_videos = 0
    errors = 0

    for ch in channels:
        channel_name = ch["name"]
        channel_url = ch["url"]
        filter_keywords = ch.get("filter_keywords")

        # Check if channel is stale (no uploads in 48h) — scan hourly instead
        last_upload_key = f"_last_upload_{channel_name}"
        last_upload = known.get(last_upload_key, "")
        if last_upload:
            try:
                last_ts = datetime.fromisoformat(last_upload.replace("Z", "+00:00"))
                hours_since = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600
                if hours_since > 48:
                    # Only check stale channels at the top of the hour
                    if datetime.now().minute > 14:
                        continue
            except (ValueError, TypeError):
                pass

        videos = get_recent_videos(channel_url, channel_name,
                                   filter_keywords=filter_keywords)
        total_scanned += 1

        for video in videos:
            vid_id = video["video_id"]
            if vid_id in known.get("videos", {}):
                continue

            # NEW video detected
            logger.info(f"NEW: {channel_name} — {video['title']} ({video['duration']}s)")

            # Check transcript cache first
            transcript_cache = os.path.join(BASE, "transcripts", f"{vid_id}.json")
            transcript_data = None
            if os.path.exists(transcript_cache):
                with open(transcript_cache) as f:
                    cached = json.load(f)
                transcript_data = {
                    "transcript_text": cached.get("text", ""),
                    "timestamped_text": cached.get("timestamped_text", ""),
                    "duration": cached.get("duration", video["duration"]),
                }
                logger.info(f"  Transcript cached ({len(transcript_data['transcript_text'])} chars)")
            else:
                transcript_data = download_and_transcribe(vid_id)

            if not transcript_data:
                logger.warning(f"  Failed to get transcript for {vid_id}")
                errors += 1
                continue

            # Classify
            topics = classify_topics(transcript_data["transcript_text"])
            sentiment = classify_sentiment(transcript_data["transcript_text"])

            # Archive entry
            entry = {
                "video_id": vid_id,
                "title": video["title"],
                "channel": channel_name,
                "upload_date": video.get("upload_date", ""),
                "duration": video["duration"],
                "transcript_text": transcript_data["transcript_text"],
                "timestamped_text": transcript_data["timestamped_text"],
                "topics": topics,
                "sentiment": sentiment,
                "archived_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            # Save to channel-specific archive
            safe_name = re.sub(r'[^\w\-]', '_', channel_name)
            channel_dir = os.path.join(ARCHIVE_DIR, safe_name)
            os.makedirs(channel_dir, exist_ok=True)
            with open(os.path.join(channel_dir, f"{vid_id}.json"), "w") as f:
                json.dump(entry, f, indent=2)

            # Update known videos index
            known["videos"][vid_id] = {
                "title": video["title"],
                "channel": channel_name,
                "upload_date": video.get("upload_date", ""),
                "duration": video["duration"],
                "topics": topics,
                "sentiment": sentiment,
                "archived_at": entry["archived_at"],
            }
            known[f"_last_upload_{channel_name}"] = entry["archived_at"]

            new_videos += 1
            logger.info(f"  ARCHIVED: topics={topics}, sentiment={sentiment}")

    # Update index
    known["last_scan"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    known["total_archived"] = len(known.get("videos", {}))
    save_known_videos(known)

    # Update intelligence signals
    update_daily_signals(known)

    if new_videos == 0:
        logger.info(f"SCAN: No new uploads across {total_scanned} channels")
    else:
        logger.info(f"SCAN COMPLETE: {total_scanned} channels scanned, "
                     f"{new_videos} new videos archived, {errors} errors")
    logger.info("=" * 60)

    return {"scanned": total_scanned, "new": new_videos, "errors": errors}


if __name__ == "__main__":
    scan_all_channels()
