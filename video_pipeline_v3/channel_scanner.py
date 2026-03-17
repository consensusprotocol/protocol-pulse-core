#!/usr/bin/env python3
"""Channel Scanner — scan Bitcoin YouTube channels for recent videos, transcribe with Whisper.

Loads channels.yaml, uses yt-dlp to list recent videos, downloads audio,
transcribes with faster-whisper (GPU), returns video catalog with transcripts.
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

BASE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(BASE, "channels.yaml")
CACHE_DIR = os.path.join(BASE, "downloads", "audio_cache")
TRANSCRIPT_DIR = os.path.join(BASE, "transcripts")

logger = logging.getLogger("ChannelScanner")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[scanner] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── Editorial Tier Hierarchy ─────────────────────────────────────────────────
# Score multiplier applied per channel tier. Tier 1 = highest editorial trust.
EDITORIAL_TIERS = {
    # TIER 1 — Bitcoin thought leaders (1.4× multiplier)
    1: {
        "multiplier": 1.4,
        "channels": [
            "Preston Pysh", "Lyn Alden", "Robert Breedlove", "TFTC",
            "Stephan Livera", "Bitcoin Audible", "Saifedean Ammous",
        ],
    },
    # TIER 2 — Trusted Bitcoin media (1.2× multiplier)
    2: {
        "multiplier": 1.2,
        "channels": [
            "Simply Bitcoin", "Bitcoin Magazine", "Natalie Brunell",
            "Swan Bitcoin", "BTC Sessions",
        ],
    },
    # TIER 3 — Solid analysts (1.0× — baseline)
    3: {
        "multiplier": 1.0,
        "channels": [
            "The Bitcoin Layer", "Blockworks", "Nathaniel Whittemore",
        ],
    },
}

# Reverse lookup: channel_name -> multiplier
_CHANNEL_TIER_MULTIPLIER = {}
for _tier_data in EDITORIAL_TIERS.values():
    for _ch in _tier_data["channels"]:
        _CHANNEL_TIER_MULTIPLIER[_ch.lower()] = _tier_data["multiplier"]
_DEFAULT_TIER_MULTIPLIER = 0.8  # Untiered channels

# ── Banned Content Filter ────────────────────────────────────────────────────
# Reject clips whose title or transcript contains any of these terms.
BANNED_CONTENT_TERMS = [
    "altcoin", "ethereum", "solana", "defi", "nft", "xrp",
    "crypto portfolio", "price target", "buy signal", "sell signal",
]


def get_tier_multiplier(channel_name: str) -> float:
    """Return editorial tier multiplier for a channel (default 0.8 for untiered)."""
    return _CHANNEL_TIER_MULTIPLIER.get(channel_name.lower(), _DEFAULT_TIER_MULTIPLIER)


def is_banned_content(title: str, transcript: str = "") -> bool:
    """Return True if title or transcript contains banned content terms."""
    combined = (title + " " + transcript).lower()
    return any(term in combined for term in BANNED_CONTENT_TERMS)

# ── GPU Memory Guard ──────────────────────────────────────────────────────────
MIN_FREE_VRAM_MB = 3000  # Require 3GB free before loading Whisper on CUDA

def _check_gpu_memory_mb() -> float:
    """Return free VRAM on GPU 0 in MB. Returns 0 on failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        return float(lines[0].strip()) if lines else 0.0
    except Exception:
        return 0.0

# ── YT-DLP URL fallbacks for channels without /videos tab ─────────────────────
YT_URL_FALLBACKS = {
    "@WBDPodcast": "https://www.youtube.com/@WBDPodcast/podcasts",
    "@BitcoinAudible": "https://www.youtube.com/@BitcoinAudible/podcasts",
    "@BTCInc": "https://www.youtube.com/@BTCInc/videos",
    "@CasaBitcoin": "https://www.youtube.com/@CasaBitcoin/videos",
    "@AnselLindner": "https://www.youtube.com/@AnselLindner/videos",
}

def _get_channel_url(channel: dict) -> str:
    """Get the best yt-dlp URL for a channel, with fallbacks for broken tabs."""
    handle = channel.get("handle", "")
    if handle in YT_URL_FALLBACKS:
        return YT_URL_FALLBACKS[handle]
    url = channel.get("url", "")
    # Extract handle from URL if present
    for fb_handle, fb_url in YT_URL_FALLBACKS.items():
        if fb_handle in url:
            return fb_url
    return url

# Lazy-loaded Whisper model
_whisper_model = None
_whisper_device = None  # Track which device the current model uses


def _get_whisper(model_size: str = "base", force_cpu: bool = False):
    """Load faster-whisper model with GPU memory guard and CPU fallback."""
    global _whisper_model, _whisper_device

    if force_cpu:
        target_device = "cpu"
    else:
        free_mb = _check_gpu_memory_mb()
        if free_mb >= MIN_FREE_VRAM_MB:
            target_device = "cuda"
            logger.info(f"Whisper: CUDA mode ({free_mb:.0f}MB free)")
        else:
            target_device = "cpu"
            logger.warning(f"Whisper: CPU fallback (only {free_mb:.0f}MB free on GPU)")

    # Reuse cached model if device matches
    if _whisper_model is not None and _whisper_device == target_device:
        return _whisper_model

    from faster_whisper import WhisperModel
    compute = "float16" if target_device == "cuda" else "int8"
    logger.info(f"Loading Whisper '{model_size}' on {target_device} ({compute})...")
    t0 = time.time()
    _whisper_model = WhisperModel(model_size, device=target_device, compute_type=compute)
    _whisper_device = target_device
    logger.info(f"Whisper loaded in {time.time() - t0:.1f}s")
    return _whisper_model


def load_channels() -> dict:
    """Load channels.yaml config."""
    with open(CHANNELS_FILE) as f:
        return yaml.safe_load(f)


def scan_channel(channel_url: str, channel_name: str,
                 max_age_hours: int = 48, max_videos: int = 3,
                 filter_keywords: list = None) -> list:
    """Get recent videos from a YouTube channel using yt-dlp.

    Args:
        filter_keywords: If set, only include videos whose title contains
                         at least one keyword (case-insensitive). Used for
                         mainstream channels to filter non-Bitcoin content.

    Returns list of dicts: {video_id, title, channel, duration, upload_date, url}
    """
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_str = cutoff.strftime("%Y%m%d")

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dateafter", cutoff_str,
        "--playlist-end", str(max_videos * 3),  # fetch extra, filter later
        "--print", "%(id)s|%(title)s|%(duration)s|%(upload_date)s",
        "--no-warnings",
        "--quiet",
        channel_url if "/videos" in channel_url or "/podcasts" in channel_url
                        or "/streams" in channel_url or "/releases" in channel_url
        else channel_url + "/videos",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.warning(f"yt-dlp failed for {channel_name}: {result.stderr[:200]}")
            return []
    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp timed out for {channel_name}")
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

        # ── Strict upload_date freshness enforcement ──
        if not upload_date:
            logger.warning(f"  WARNING no upload_date for {video_id} - allowing through")
        try:
            upload_dt = datetime.strptime(upload_date, "%Y%m%d")
            hours_old = (datetime.now() - upload_dt).total_seconds() / 3600
            if upload_dt < cutoff:
                logger.info(f"  SKIPPED old video: {title[:60]} (uploaded {upload_date}) — exceeds {max_age_hours}h window")
                continue
        except ValueError:
            logger.warning(f"  WARNING unparseable upload_date {video_id} - allowing")

        # Skip shorts (under 2 minutes) and super-long videos (over 4 hours)
        if duration < 120 or duration > 14400:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "channel": channel_name,
            "duration": duration,
            "upload_date": upload_date,
            "upload_date_iso": f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}",
            "hours_old": round(hours_old, 1),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    # Keyword filter for mainstream channels (BUG-005 fix)
    if filter_keywords and videos:
        total = len(videos)
        filtered = []
        for v in videos:
            title_lower = v["title"].lower()
            if any(kw.lower() in title_lower for kw in filter_keywords):
                filtered.append(v)
        dropped = total - len(filtered)
        if dropped > 0:
            logger.info(f"  KEYWORD FILTER: {channel_name} — {total} videos, "
                        f"{len(filtered)} matched keywords, {dropped} filtered out")
        videos = filtered

    # Limit to max_videos
    videos = videos[:max_videos]
    if videos:
        logger.info(f"  {channel_name}: {len(videos)} videos found")
    return videos


def download_audio(video_id: str) -> str:
    """Download audio from a YouTube video, return path to wav file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    wav_path = os.path.join(CACHE_DIR, f"{video_id}.wav")

    # Check cache
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
        logger.info(f"  Audio cached: {video_id}")
        return wav_path

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = os.path.join(CACHE_DIR, f"{video_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--audio-quality", "5",  # lower quality = smaller/faster
        "--no-playlist",
        "--quiet",
        "-o", output_template,
        url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.warning(f"  Audio download timed out: {video_id}")
        return ""

    if os.path.exists(wav_path):
        return wav_path

    # Check for other formats and convert
    for ext in ["m4a", "mp3", "opus", "webm", "ogg"]:
        alt = os.path.join(CACHE_DIR, f"{video_id}.{ext}")
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
                return wav_path

    logger.warning(f"  No audio file for {video_id}")
    return ""


def transcribe_audio(audio_path: str, model_size: str = "base") -> dict:
    """Transcribe audio with faster-whisper. CUDA OOM guard + CPU fallback."""
    global _whisper_model, _whisper_device

    def _run_transcription(mdl):
        t0 = time.time()
        segments_iter, info = mdl.transcribe(
            audio_path,
            language="en",
            word_timestamps=False,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text_parts = []
        timestamped_lines = []
        for seg in segments_iter:
            seg_text = seg.text.strip()
            text_parts.append(seg_text)
            mm = int(seg.start // 60)
            ss = int(seg.start % 60)
            timestamped_lines.append(f"[{mm:02d}:{ss:02d}] {seg_text}")
        elapsed = time.time() - t0
        duration = info.duration if hasattr(info, "duration") else 0
        return {
            "text": " ".join(text_parts),
            "timestamped_text": "\n".join(timestamped_lines),
            "duration": round(duration, 2),
            "transcription_time": round(elapsed, 2),
        }

    model = _get_whisper(model_size)
    try:
        return _run_transcription(model)
    except Exception as e:
        err_str = str(e).lower()
        if "out of memory" in err_str or "cuda" in err_str:
            logger.warning(f"CUDA OOM on {audio_path} — clearing cache + retrying on CPU")
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
            _whisper_model = None
            _whisper_device = None
            try:
                cpu_model = _get_whisper(model_size, force_cpu=True)
                return _run_transcription(cpu_model)
            except Exception as e2:
                logger.error(f"CPU retry also failed: {e2}")
                return {"text": "", "timestamped_text": "", "duration": 0, "transcription_time": 0}
        raise


def scan_all_channels(model_size: str = "base") -> list:
    """Main entry: scan all channels, download audio, transcribe.

    Returns list of video dicts with transcript data added:
    {video_id, title, channel, duration, upload_date, url, transcript_text, timestamped_text}
    """
    config = load_channels()
    channels = list(config.get("channels", []))
    # Merge mainstream channels (with keyword filtering)
    mainstream = config.get("mainstream", [])
    channels.extend(mainstream)

    scan_cfg = config.get("scan", {})
    max_age = scan_cfg.get("max_age_hours", 48)
    fallback_age = scan_cfg.get("fallback_age_hours", 168)
    max_videos = scan_cfg.get("max_videos_per_channel", 3)

    # Sort by priority (1 first)
    channels.sort(key=lambda c: c.get("priority", 99))

    logger.info(f"Scanning {len(channels)} channels (max age: {max_age}h)...")
    all_videos = []

    for ch in channels:
        keywords = ch.get("filter_keywords")
        videos = scan_channel(ch["url"], ch["name"], max_age, max_videos,
                              filter_keywords=keywords)
        if not videos:
            logger.info(f"  DEAD CHANNEL: {ch['name']} — 0 fresh videos in last {max_age}h")
        all_videos.extend(videos)

    # Fallback: if too few videos, expand time window
    if len(all_videos) < 3:
        logger.info(f"Only {len(all_videos)} videos found, expanding to {fallback_age}h...")
        all_videos = []
        for ch in channels:
            keywords = ch.get("filter_keywords")
            videos = scan_channel(ch["url"], ch["name"], fallback_age, max_videos,
                                  filter_keywords=keywords)
            all_videos.extend(videos)

    logger.info(f"Total videos found: {len(all_videos)}")
    if not all_videos:
        return []

    # Download audio + transcribe each video
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    transcribed = []

    for i, video in enumerate(all_videos):
        vid = video["video_id"]
        logger.info(f"[{i+1}/{len(all_videos)}] {video['channel']}: {video['title'][:60]}")

        # Check transcript cache
        transcript_cache = os.path.join(TRANSCRIPT_DIR, f"{vid}.json")
        if os.path.exists(transcript_cache):
            with open(transcript_cache) as f:
                cached = json.load(f)
            video["transcript_text"] = cached.get("text", "")
            video["timestamped_text"] = cached.get("timestamped_text", "")
            transcribed.append(video)
            logger.info(f"  Transcript cached ({len(video['transcript_text'])} chars)")
            continue

        # Download audio
        audio_path = download_audio(vid)
        if not audio_path:
            logger.warning(f"  Skipping {vid}: audio download failed")
            continue

        # Transcribe
        try:
            result = transcribe_audio(audio_path, model_size)
            video["transcript_text"] = result["text"]
            video["timestamped_text"] = result["timestamped_text"]

            # Cache transcript (with upload_date for downstream freshness checks)
            with open(transcript_cache, "w") as f:
                json.dump({
                    "text": result["text"],
                    "timestamped_text": result["timestamped_text"],
                    "duration": result["duration"],
                    "video_id": vid,
                    "title": video["title"],
                    "channel": video["channel"],
                    "upload_date": video.get("upload_date", ""),
                    "upload_date_iso": video.get("upload_date_iso", ""),
                    "hours_old": video.get("hours_old", -1),
                }, f, indent=2)

            transcribed.append(video)
            speed = result["duration"] / result["transcription_time"] if result["transcription_time"] > 0 else 0
            logger.info(f"  Transcribed in {result['transcription_time']:.1f}s "
                        f"({speed:.0f}x realtime, {len(result['text'])} chars)")
        except Exception as e:
            logger.error(f"  Transcription failed for {vid}: {e}")
            continue

    logger.info(f"Transcribed {len(transcribed)}/{len(all_videos)} videos")

    # ── Apply editorial tier multipliers + banned content filter ──
    scored = []
    banned_count = 0
    for video in transcribed:
        title = video.get("title", "")
        transcript = video.get("transcript_text", "")
        if is_banned_content(title, transcript):
            banned_count += 1
            logger.info(f"  BANNED: [{video['channel']}] {title[:60]}")
            continue
        video["tier_multiplier"] = get_tier_multiplier(video.get("channel", ""))
        scored.append(video)

    if banned_count:
        logger.info(f"Filtered {banned_count} banned-content clips")
    logger.info(f"Returning {len(scored)} clips (tier-scored, content-filtered)")
    return scored


if __name__ == "__main__":
    videos = scan_all_channels()
    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE: {len(videos)} videos with transcripts")
    for v in videos:
        print(f"  [{v['channel']}] {v['title'][:50]} ({v['duration']}s)")
        print(f"    Transcript: {len(v.get('transcript_text', ''))} chars")
    print(f"{'='*60}")
