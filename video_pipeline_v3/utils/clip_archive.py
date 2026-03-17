#!/usr/bin/env python3
"""Clip Archive — persistent clip storage for fallback on yt-dlp failures.

Saves every successfully extracted clip to data/clip_archive/CHANNEL/VIDEO_ID.mp4
so that if yt-dlp fails (rate limit, geo-block, etc.), a recent archived clip
from the same channel can be used as a fallback.
"""
import json
import logging
import os
import shutil
import time

logger = logging.getLogger("ClipArchive")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_DIR = os.path.join(BASE, "data", "clip_archive")


def save_clip(channel: str, video_id: str, mp4_path: str, metadata: dict) -> bool:
    """Archive a successfully extracted clip.

    Args:
        channel: Channel name (sanitized for filesystem)
        video_id: YouTube video ID
        mp4_path: Path to the extracted MP4 file
        metadata: Dict with start, end, duration, quote, etc.

    Returns:
        True if archived successfully
    """
    safe_channel = channel.replace(" ", "_").replace("/", "_")
    channel_dir = os.path.join(ARCHIVE_DIR, safe_channel)
    os.makedirs(channel_dir, exist_ok=True)

    dest_mp4 = os.path.join(channel_dir, f"{video_id}.mp4")
    dest_meta = os.path.join(channel_dir, f"{video_id}.json")

    try:
        shutil.copy2(mp4_path, dest_mp4)
        meta = {**metadata, "archived_at": time.time(), "channel": channel, "video_id": video_id}
        with open(dest_meta, "w") as f:
            json.dump(meta, f, indent=2)
        logger.info(f"[archive] Saved clip {video_id} for {channel}")
        return True
    except Exception as e:
        logger.warning(f"[archive] Failed to save clip {video_id}: {e}")
        return False


def get_fallback_clip(channel: str, max_age_days: int = 7) -> str | None:
    """Find the most recent archived clip for a channel within max_age_days.

    Args:
        channel: Channel name
        max_age_days: Maximum age of clip in days

    Returns:
        Path to archived MP4, or None if nothing suitable found
    """
    safe_channel = channel.replace(" ", "_").replace("/", "_")
    channel_dir = os.path.join(ARCHIVE_DIR, safe_channel)

    if not os.path.isdir(channel_dir):
        return None

    cutoff = time.time() - (max_age_days * 86400)
    best_path = None
    best_time = 0

    for fname in os.listdir(channel_dir):
        if not fname.endswith(".mp4"):
            continue
        fpath = os.path.join(channel_dir, fname)
        mtime = os.path.getmtime(fpath)
        if mtime >= cutoff and mtime > best_time and os.path.getsize(fpath) > 10_000:
            best_time = mtime
            best_path = fpath

    return best_path


def list_archive() -> dict:
    """List all archived clips by channel.

    Returns:
        Dict mapping channel name -> list of {video_id, path, age_days, size_mb}
    """
    result = {}
    if not os.path.isdir(ARCHIVE_DIR):
        return result

    now = time.time()
    for channel_name in sorted(os.listdir(ARCHIVE_DIR)):
        channel_dir = os.path.join(ARCHIVE_DIR, channel_name)
        if not os.path.isdir(channel_dir):
            continue
        clips = []
        for fname in sorted(os.listdir(channel_dir)):
            if not fname.endswith(".mp4"):
                continue
            fpath = os.path.join(channel_dir, fname)
            video_id = fname.replace(".mp4", "")
            clips.append({
                "video_id": video_id,
                "path": fpath,
                "age_days": round((now - os.path.getmtime(fpath)) / 86400, 1),
                "size_mb": round(os.path.getsize(fpath) / (1024 * 1024), 1),
            })
        if clips:
            result[channel_name] = clips

    return result
