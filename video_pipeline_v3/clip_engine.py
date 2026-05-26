#!/usr/bin/env python3
"""Clip Engine — automated best-moment extraction + YouTube publishing.

Scans partner channels, finds the best 30-60s moments using Whisper + LLM,
brands them with Protocol Pulse overlay + creator credit, publishes to YouTube.

Usage:
    python3 clip_engine.py                    # Process all channels, publish best clips
    python3 clip_engine.py --dry-run          # Extract + brand but don't upload
    python3 clip_engine.py --channel "Simply Bitcoin"  # Single channel
    python3 clip_engine.py --top 5            # Top N clips only

Cron (run daily at 6 AM ET):
    0 6 * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 clip_engine.py >> logs/clip_engine.log 2>&1
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("ClipEngine")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[clip_engine] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE, "output", "clips_daily")
PUBLISHED_LOG = os.path.join(BASE, "data", "published_clips.json")
BRAND_LOGO = os.path.join(BASE, "assets", "logo_protocol_pulse.png")

SPONSOR_ASSETS_DIR = os.path.join(BASE, "assets", "sponsors")

SPONSORS = [
    {"name": "Curated Mining", "tag": "Brought to you by Curated Mining"},
    {"name": "Meanwhile", "tag": "Brought to you by Meanwhile"},
    {"name": "River", "tag": "Brought to you by River"},
]

SPAM_CHANNELS = [
    "BitBoy", "Crypto Banter", "altcoin buzz", "moon carl",
    "crypto jebb", "sheldon evans", "datadash",
]

def _get_sponsor():
    """Rotate sponsors daily."""
    day = datetime.now().timetuple().tm_yday
    return SPONSORS[day % len(SPONSORS)]["tag"]

def _is_spam_channel(channel_name):
    """Filter out shilling/spam channels."""
    lower = channel_name.lower()
    return any(spam.lower() in lower for spam in SPAM_CHANNELS)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def load_published():
    """Load list of already-published video_ids to avoid duplicates."""
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG) as f:
            return json.load(f)
    return {"published": []}


def save_published(data):
    os.makedirs(os.path.dirname(PUBLISHED_LOG), exist_ok=True)
    with open(PUBLISHED_LOG, "w") as f:
        json.dump(data, f, indent=2)


def scan_recent_videos(channels_yaml, max_age_hours=48):
    """Get recent videos from all channels via yt-dlp flat-playlist."""
    import yaml
    with open(channels_yaml) as f:
        channels = yaml.safe_load(f)

    videos = []
    for ch in channels.get("channels", []):
        name = ch.get("name", "Unknown")
        url = ch.get("url", "")
        if not url:
            continue
        try:
            r = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--dump-json", "--playlist-end", "5", url],
                capture_output=True, text=True, timeout=30
            )
            for line in r.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    v = json.loads(line)
                    v["channel_name"] = name
                    v["channel_handle"] = ch.get("handle", "")
                    dur = v.get("duration", 0)
                    if dur and 60 < dur < 1800:  # 1-30 min only
                        if not _is_spam_channel(name):
                            videos.append(v)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.warning(f"  {name}: scan failed ({e})")

    logger.info(f"Scanned {len(videos)} videos from {len(channels.get('channels', []))} channels")
    return videos


def score_clip_with_llm(video_meta, transcript_text):
    """Use local Qwen to score clip for standalone publishing potential.
    
    Returns: dict with score (0-100), best_segment (start_s, end_s), 
             title, description, tags
    """
    try:
        import requests
        prompt = f"""You are a viral clip selector for a Bitcoin YouTube channel called Protocol Pulse.

VIDEO: "{video_meta.get('title', 'Unknown')}" by {video_meta.get('channel_name', 'Unknown')}
DURATION: {video_meta.get('duration', 0)}s

TRANSCRIPT (first 2000 chars):
{transcript_text[:2000]}

Find the single most compelling 30-60 second moment that would work as a standalone clip.
Criteria: controversial take, surprising data, emotional moment, quotable one-liner, breaking news.

Respond ONLY in JSON:
{{
  "score": 0-100,
  "start_seconds": N,
  "end_seconds": N,
  "why": "one sentence reason",
  "clip_title": "catchy title for YouTube",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen3-coder:30b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 300}
            },
            timeout=60
        )
        if r.ok:
            text = r.json().get("message", {}).get("content", "")
            # Extract JSON from response
            import re
            m = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
    except Exception as e:
        logger.warning(f"  LLM scoring failed: {e}")
    return None


def extract_clip(video_url, start_s, end_s, output_path):
    """Extract a clip segment using yt-dlp + ffmpeg."""
    duration = end_s - start_s
    try:
        # Download with yt-dlp using time range
        tmp_raw = output_path + ".raw.mp4"
        r = subprocess.run([
            "yt-dlp",
            "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=1080]",
            "--download-sections", f"*{start_s}-{end_s}",
            "--force-keyframes-at-cuts",
            "-o", tmp_raw,
            video_url,
        ], capture_output=True, text=True, timeout=120)

        if not os.path.exists(tmp_raw):
            logger.error(f"  Download failed: {r.stderr[:200]}")
            return False

        # Normalize to 1080p 30fps CFR
        ok = subprocess.run([
            "ffmpeg", "-y", "-i", tmp_raw,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            "-t", str(duration),
            output_path,
        ], capture_output=True, text=True, timeout=300)

        os.remove(tmp_raw) if os.path.exists(tmp_raw) else None
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100000

    except Exception as e:
        logger.error(f"  Extract failed: {e}")
        return False


def brand_clip(input_path, output_path, channel_name, channel_handle, clip_title):
    """Add Protocol Pulse branding + creator credit overlay."""
    # Lower third with creator credit + PP logo
    filter_parts = [
        # Darken bottom bar for text
        "drawbox=x=0:y=ih-100:w=iw:h=100:color=black@0.7:t=fill",
        # Channel name
        f"drawtext=text='{channel_name}':fontfile={FONT_BOLD}:fontsize=28:fontcolor=white:x=20:y=h-80",
        # Handle
        f"drawtext=text='{channel_handle}':fontfile={FONT_BOLD}:fontsize=20:fontcolor=#CC0000:x=20:y=h-45",
        # Protocol Pulse watermark top-right
        f"drawtext=text='PROTOCOL PULSE':fontfile={FONT_BOLD}:fontsize=16:fontcolor=white@0.6:x=w-220:y=15",
    ]

    vf = ",".join(filter_parts)

    try:
        ok = subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            output_path,
        ], capture_output=True, text=True, timeout=300)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100000
    except Exception as e:
        logger.error(f"  Branding failed: {e}")
        return False


def upload_to_youtube(video_path, title, description, tags, category_id="28"):
    """Upload clip to YouTube via the existing upload module."""
    try:
        from utils.youtube_upload import upload_video
        result = upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,  # 28 = Science & Technology
            privacy_status="public",
        )
        return result
    except Exception as e:
        logger.error(f"  Upload failed: {e}")
        return None


def run_clip_engine(dry_run=False, top_n=5, channel_filter=None):
    """Main clip engine loop."""
    logger.info("=" * 60)
    logger.info(f"CLIP ENGINE — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")
    logger.info("=" * 60)

    # Load published history
    published = load_published()
    published_ids = set(published.get("published", []))

    # Scan channels
    channels_yaml = os.path.join(BASE, "channels.yaml")
    videos = scan_recent_videos(channels_yaml)

    # Filter already published
    fresh = [v for v in videos if v.get("id") not in published_ids]
    logger.info(f"Fresh videos: {len(fresh)} (filtered {len(videos) - len(fresh)} already published)")

    if channel_filter:
        fresh = [v for v in fresh if channel_filter.lower() in v.get("channel_name", "").lower()]
        logger.info(f"Channel filter '{channel_filter}': {len(fresh)} videos")

    # Score each video with LLM
    scored = []
    for v in fresh[:30]:  # Cap at 30 to limit LLM calls
        logger.info(f"  Scoring: {v.get('title', '?')[:60]} ({v.get('channel_name')})")
        # TODO: get transcript from scanner cache or quick whisper
        # For now, use title + description as proxy
        proxy_text = f"{v.get('title', '')}. {v.get('description', '')[:500]}"
        result = score_clip_with_llm(v, proxy_text)
        if result and result.get("score", 0) >= 60:
            v["clip_score"] = result
            scored.append(v)

    # Sort by score, take top N
    scored.sort(key=lambda x: x.get("clip_score", {}).get("score", 0), reverse=True)
    top_clips = scored[:top_n]

    logger.info(f"Top {len(top_clips)} clips selected for extraction")

    # Process each clip
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []

    for i, v in enumerate(top_clips, 1):
        cs = v["clip_score"]
        vid_id = v.get("id", "unknown")
        channel = v.get("channel_name", "Unknown")
        handle = v.get("channel_handle", "")
        
        logger.info(f"\n--- CLIP {i}/{len(top_clips)} ---")
        logger.info(f"  {channel}: {v.get('title', '?')[:60]}")
        logger.info(f"  Score: {cs.get('score')}/100 | {cs.get('start_seconds')}s-{cs.get('end_seconds')}s")
        logger.info(f"  Why: {cs.get('why', '?')}")

        raw_path = os.path.join(OUTPUT_DIR, f"clip_{vid_id}_raw.mp4")
        branded_path = os.path.join(OUTPUT_DIR, f"clip_{vid_id}_branded.mp4")

        # Extract
        video_url = f"https://www.youtube.com/watch?v={vid_id}"
        ok = extract_clip(video_url, cs.get("start_seconds", 0), cs.get("end_seconds", 60), raw_path)
        if not ok:
            logger.error(f"  SKIP: extraction failed")
            continue

        # Brand
        ok = brand_clip(raw_path, branded_path, channel, handle, cs.get("clip_title", ""))
        if not ok:
            logger.error(f"  SKIP: branding failed")
            continue

        # Upload
        if not dry_run:
            clip_title = f"{cs.get('clip_title', channel + ' clip')} | Protocol Pulse"
            description = (
                f"Best moment from {channel} ({handle})\n\n"
                f"Original video: {video_url}\n\n"
                f"Subscribe to {channel}: {v.get('channel_url', '')}\n"
                f"Subscribe to Protocol Pulse: https://www.youtube.com/@ProtocolPulse?sub_confirmation=1\n\n"
                f"#Bitcoin #ProtocolPulse #BTC"
            )
            tags = cs.get("tags", []) + ["Bitcoin", "Protocol Pulse", channel]

            yt_result = upload_to_youtube(branded_path, clip_title, description, tags)
            if yt_result:
                logger.info(f"  UPLOADED: {yt_result}")
                published["published"].append(vid_id)
                save_published(published)
            else:
                logger.error(f"  Upload failed")
        else:
            logger.info(f"  DRY RUN: would upload {branded_path}")

        results.append({"video_id": vid_id, "channel": channel, "score": cs.get("score")})

    logger.info(f"\n{'=' * 60}")
    logger.info(f"CLIP ENGINE COMPLETE: {len(results)} clips processed")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Protocol Pulse Clip Engine")
    parser.add_argument("--dry-run", action="store_true", help="Extract + brand without uploading")
    parser.add_argument("--top", type=int, default=5, help="Number of top clips to process")
    parser.add_argument("--channel", type=str, help="Filter to specific channel")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(BASE), ".env"))

    run_clip_engine(dry_run=args.dry_run, top_n=args.top, channel_filter=args.channel)
