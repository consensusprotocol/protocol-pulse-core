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

# Lazy-loaded Whisper model
_whisper_model = None


def _get_whisper(model_size: str = "base"):
    """Load faster-whisper model (lazy, cached)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    from faster_whisper import WhisperModel
    logger.info(f"Loading Whisper '{model_size}' on CUDA...")
    t0 = time.time()
    _whisper_model = WhisperModel(model_size, device="cuda", compute_type="float16")
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
        channel_url + "/videos",
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

        # Skip shorts (under 2 minutes) and super-long videos (over 4 hours)
        if duration < 120 or duration > 14400:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "channel": channel_name,
            "duration": duration,
            "upload_date": upload_date,
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
    """Transcribe audio with faster-whisper. Returns {text, timestamped_text, duration}."""
    model = _get_whisper(model_size)
    t0 = time.time()

    segments_iter, info = model.transcribe(
        audio_path,
        language="en",
        word_timestamps=False,  # faster without word-level
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

            # Cache transcript
            with open(transcript_cache, "w") as f:
                json.dump({
                    "text": result["text"],
                    "timestamped_text": result["timestamped_text"],
                    "duration": result["duration"],
                    "video_id": vid,
                    "title": video["title"],
                    "channel": video["channel"],
                }, f, indent=2)

            transcribed.append(video)
            speed = result["duration"] / result["transcription_time"] if result["transcription_time"] > 0 else 0
            logger.info(f"  Transcribed in {result['transcription_time']:.1f}s "
                        f"({speed:.0f}x realtime, {len(result['text'])} chars)")
        except Exception as e:
            logger.error(f"  Transcription failed for {vid}: {e}")
            continue

    logger.info(f"Transcribed {len(transcribed)}/{len(all_videos)} videos")
    return transcribed


if __name__ == "__main__":
    videos = scan_all_channels()
    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE: {len(videos)} videos with transcripts")
    for v in videos:
        print(f"  [{v['channel']}] {v['title'][:50]} ({v['duration']}s)")
        print(f"    Transcript: {len(v.get('transcript_text', ''))} chars")
    print(f"{'='*60}")
