#!/usr/bin/env python3
"""Stage 1a v2: Scan partner channels for uploads in the last 48h.
Uses --playlist-end 15 + --match-filter to get recent uploads only."""
import json
import subprocess
import sys
from datetime import datetime, timedelta

PARTNER_FILE = "/home/ultron/protocol_pulse/config/partner_channels.json"
OUTPUT_FILE = "/home/ultron/protocol_pulse/segment_v1/sources.json"

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
    # Use the /videos tab URL
    url = f"https://www.youtube.com/{handle}/videos"
    print(f"  Scanning {name} ({handle})...", end=" ", flush=True)
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--no-warnings",
                "--playlist-end", "15",
                "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date>%Y%m%d)s",
                url,
            ],
            capture_output=True, text=True, timeout=120,
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        count = 0
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 4:
                vid_id, title, dur, upload_date = parts[0], parts[1], parts[2], parts[3]
                try:
                    dur_int = int(float(dur)) if dur and dur != "NA" else 0
                except (ValueError, TypeError):
                    dur_int = 0
                # Skip shorts (<120s) and old videos
                if dur_int < 120:
                    continue
                if upload_date < date_after and upload_date != "NA":
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
        if result.stderr:
            err_lines = [l for l in result.stderr.strip().split("\n") if "ERROR" in l]
            for e in err_lines[:2]:
                print(f"    ERR: {e[:100]}")
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\nTotal: {len(all_videos)} videos from {len(channels)} channels")
with open(OUTPUT_FILE, "w") as f:
    json.dump({"scan_date": datetime.utcnow().isoformat(), "date_after": date_after, "videos": all_videos}, f, indent=2)
print(f"Written to {OUTPUT_FILE}")

# Print summary table
print("\n--- UPLOAD SUMMARY ---")
for v in all_videos:
    print(f"  {v['upload_date']} | {v['channel_name'][:20]:20s} | {v['title'][:60]} | {v['duration_s']}s")
