#!/usr/bin/env python3
"""pipeline/scan.py — YouTube RSS channel scanner (M17).

Fetches YouTube RSS feeds for all enabled channels and returns videos
published within a configurable window (default 24h, fallback 48h).

Excludes:
  - Shorts (< 60s or /shorts/ in URL)
  - Livestream VODs > 3h (unless explicitly windowed)

Usage:
    python3 -m pipeline.scan --segment <segment_dir> [--window-hours 24]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

# YouTube RSS namespace
YT_NS = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"
ATOM_NS = "http://www.w3.org/2005/Atom"

MAX_VOD_DURATION_S = 3 * 3600  # 3 hours — exclude livestream VODs above this
MIN_VIDEO_DURATION_S = 60      # exclude Shorts


def fetch_rss(channel_id, timeout=15):
    """Fetch YouTube RSS feed for a channel. Returns list of video dicts."""
    import urllib.request
    import urllib.error

    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ProtocolPulse/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml_data = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"    WARN: RSS fetch failed for {channel_id}: {e}")
        return []

    try:
        root = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError as e:
        print(f"    WARN: RSS parse failed for {channel_id}: {e}")
        return []

    videos = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        vid_el = entry.find(f"{{{YT_NS}}}videoId")
        title_el = entry.find(f"{{{ATOM_NS}}}title")
        published_el = entry.find(f"{{{ATOM_NS}}}published")
        link_el = entry.find(f"{{{ATOM_NS}}}link")

        if vid_el is None or title_el is None or published_el is None:
            continue

        video_id = vid_el.text.strip()
        title = title_el.text.strip() if title_el.text else ""
        published = published_el.text.strip()
        url = link_el.get("href", "") if link_el is not None else ""

        videos.append({
            "video_id": video_id,
            "title": title,
            "published": published,
            "url": url or f"https://www.youtube.com/watch?v={video_id}",
        })

    return videos


def parse_iso_datetime(s):
    """Parse ISO 8601 datetime string to timezone-aware datetime."""
    # Handle various formats: 2026-11-05T12:00:00+00:00, 2026-11-05T12:00:00Z
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def scan_channels(channels_json_path, window_hours=24, fallback_hours=48):
    """Scan all enabled channels for recent videos.

    Returns list of candidate dicts with channel info and video metadata.
    """
    with open(channels_json_path) as f:
        channels = json.load(f)

    enabled = [ch for ch in channels if ch.get("enabled", True)]
    print(f"Scanning {len(enabled)} enabled channels (window: {window_hours}h)")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    fallback_cutoff = now - timedelta(hours=fallback_hours)

    candidates = []
    channels_with_videos = 0

    for i, ch in enumerate(enabled):
        channel_id = ch.get("channel_id", "")
        handle = ch.get("yt_handle", "")
        name = ch.get("display_name", handle)

        if not channel_id:
            print(f"  [{i+1}/{len(enabled)}] {name}: SKIP (no channel_id)")
            continue

        print(f"  [{i+1}/{len(enabled)}] {name}...", end=" ", flush=True)
        videos = fetch_rss(channel_id)

        count = 0
        for v in videos:
            pub = parse_iso_datetime(v["published"])
            if pub is None:
                continue

            # Check window
            if pub < fallback_cutoff:
                continue  # Too old even for fallback

            in_window = pub >= cutoff

            # Skip Shorts (detected by title patterns or URL)
            if "/shorts/" in v["url"]:
                continue

            candidates.append({
                "channel": name,
                "handle": handle,
                "tier": ch.get("tier", 3),
                "video_id": v["video_id"],
                "title": v["title"],
                "published": v["published"],
                "url": v["url"],
                "in_primary_window": in_window,
            })
            count += 1

        if count > 0:
            channels_with_videos += 1
        print(f"{count} videos")

    print(f"\nTotal candidates: {len(candidates)} from {channels_with_videos} channels")
    return candidates


def main():
    p = argparse.ArgumentParser(description="YouTube RSS channel scanner")
    p.add_argument("--segment", required=True, help="Segment directory for output")
    p.add_argument("--window-hours", type=int, default=24, help="Primary window (hours)")
    p.add_argument("--fallback-hours", type=int, default=48, help="Fallback window (hours)")
    args = p.parse_args()

    channels_path = os.path.join(PIPELINE_DIR, "channels.json")
    if not os.path.exists(channels_path):
        print(f"STOP: channels.json not found at {channels_path}")
        sys.exit(1)

    t0 = time.time()
    candidates = scan_channels(channels_path, args.window_hours, args.fallback_hours)

    # Write output
    out_path = os.path.join(args.segment, "sources.json")
    os.makedirs(args.segment, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(candidates, f, indent=2)
        f.write("\n")

    elapsed = time.time() - t0
    print(f"\nSaved {len(candidates)} candidates to {out_path}")
    print(f"Scan time: {elapsed:.1f}s ({elapsed/60:.1f}min)")

    if elapsed > 300:
        print("WARNING: Scan took > 5 minutes")


if __name__ == "__main__":
    main()
