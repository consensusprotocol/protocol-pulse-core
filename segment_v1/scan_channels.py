#!/usr/bin/env python3
"""Stage 1a: Scan partner channels for uploads in the last 48h."""
import json
import subprocess
import sys
from datetime import datetime, timedelta

PARTNER_FILE = "/home/ultron/protocol_pulse/config/partner_channels.json"
OUTPUT_FILE = "/home/ultron/protocol_pulse/segment_v1/sources.json"

# 48h ago in YYYYMMDD
date_after = (datetime.utcnow() - timedelta(hours=48)).strftime("%Y%m%d")

with open(PARTNER_FILE) as f:
    cfg = json.load(f)

channels = [c for c in cfg["channels"] if c.get("enabled", False)]
print(f"Scanning {len(channels)} enabled channels, dateafter={date_after}")

all_videos = []
for ch in channels:
    handle = ch["handle"]
    name = ch["name"]
    channel_id = ch["channel_id"]
    url = f"https://www.youtube.com/{handle}/videos"
    print(f"  Scanning {name} ({handle})...", end=" ", flush=True)
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--dateafter", date_after,
                "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date)s",
                "--no-warnings",
                "--extractor-args", "youtube:approximate_date",
                url,
            ],
            capture_output=True, text=True, timeout=60,
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        count = 0
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 4:
                vid_id, title, dur, upload_date = parts[0], parts[1], parts[2], parts[3]
                # Filter: only videos (not shorts, typically >60s)
                try:
                    dur_int = int(float(dur)) if dur and dur != "NA" else 0
                except (ValueError, TypeError):
                    dur_int = 0
                if dur_int < 120:
                    continue
                all_videos.append({
                    "channel_name": name,
                    "channel_handle": handle,
                    "channel_id": channel_id,
                    "video_id": vid_id,
                    "title": title,
                    "duration_s": dur_int,
                    "upload_date": upload_date,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                })
                count += 1
        print(f"{count} videos")
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\nTotal: {len(all_videos)} videos from {len(channels)} channels")
with open(OUTPUT_FILE, "w") as f:
    json.dump({"scan_date": datetime.utcnow().isoformat(), "date_after": date_after, "videos": all_videos}, f, indent=2)
print(f"Written to {OUTPUT_FILE}")
