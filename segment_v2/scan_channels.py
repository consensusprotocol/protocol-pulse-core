#!/usr/bin/env python3
"""Stage S1: Scan approved partner channels for uploads.
8h window first; fallback 48h if <3 qualifying videos with >=3 distinct channels.
EXCLUDE altcoin-centric channels (Coin Bureau, etc.) per PBX directive.
Uses non-flat yt-dlp to get actual upload_date."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

BASE = "/home/ultron/protocol_pulse/segment_v2"
PARTNER_FILE = "/home/ultron/protocol_pulse/config/partner_channels.json"
OUTPUT_FILE = f"{BASE}/sources.json"

APPROVED_CHANNELS = {
    "Simply Bitcoin", "BTC Sessions", "CoinDesk", "Bitcoin Magazine",
    "Natalie Brunell",
    "What Bitcoin Did", "The Bitcoin Layer", "Anthony Pompliano",
    "Preston Pysh", "Stephan Livera", "TFTC", "Robert Breedlove",
    "Swan Bitcoin",
}
EXCLUDED_CHANNELS = {"Coin Bureau", "Bitcoin Fundamentals"}
MIN_DURATION_S = 120
VIDS_PER_CHANNEL = 10  # fetch last N per channel


def scan(hours_back):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours_back)
    cutoff_str = cutoff.strftime("%Y%m%d")

    with open(PARTNER_FILE) as f:
        cfg = json.load(f)

    channels = [
        c for c in cfg["channels"]
        if c.get("enabled") and c["name"] in APPROVED_CHANNELS and c["name"] not in EXCLUDED_CHANNELS
    ]
    print(f"Scanning {len(channels)} channels, cutoff={cutoff_str} ({hours_back}h)")

    all_videos = []
    for ch in channels:
        handle, name, cid = ch["handle"], ch["name"], ch["channel_id"]
        url = f"https://www.youtube.com/{handle}/videos"
        print(f"  {name}...", end=" ", flush=True)
        try:
            r = subprocess.run(
                [
                    "yt-dlp", "--no-flat-playlist", "--playlist-end", str(VIDS_PER_CHANNEL),
                    "--skip-download",
                    "--print", "%(id)s\t%(upload_date)s\t%(duration)s\t%(title)s",
                    "--no-warnings", url,
                ],
                capture_output=True, text=True, timeout=120,
            )
            count = 0
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t", 3)
                if len(parts) < 4:
                    continue
                vid_id, upload_date, dur_raw, title = parts
                if upload_date == "NA" or not upload_date:
                    continue
                if upload_date < cutoff_str:
                    continue
                try:
                    dur_int = int(float(dur_raw)) if dur_raw and dur_raw != "NA" else 0
                except (ValueError, TypeError):
                    dur_int = 0
                if dur_int < MIN_DURATION_S:
                    continue
                all_videos.append({
                    "channel_name": name, "channel_handle": handle, "channel_id": cid,
                    "video_id": vid_id, "title": title, "duration_s": dur_int,
                    "upload_date": upload_date,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                })
                count += 1
            print(f"{count}")
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
        except Exception as e:
            print(f"ERROR: {e}")

    return all_videos


videos_8h = scan(8)
distinct_8h = len(set(v["channel_name"] for v in videos_8h))
print(f"\n8h: {len(videos_8h)} videos, {distinct_8h} channels")

if distinct_8h >= 3 and len(videos_8h) >= 3:
    videos = videos_8h
    window = 8
else:
    print("Insufficient — falling back to 48h")
    videos = scan(48)
    window = 48

seen = set()
unique = []
for v in videos:
    if v["video_id"] not in seen:
        seen.add(v["video_id"])
        unique.append(v)

distinct = len(set(v["channel_name"] for v in unique))
print(f"\nFinal: {len(unique)} videos from {distinct} channels ({window}h)")

result = {
    "scan_date": datetime.now(timezone.utc).isoformat(),
    "window_hours": window,
    "distinct_channels": distinct,
    "videos": unique,
}
with open(OUTPUT_FILE, "w") as f:
    json.dump(result, f, indent=2)
print(f"Written to {OUTPUT_FILE}")
