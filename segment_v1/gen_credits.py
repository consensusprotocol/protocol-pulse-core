#!/usr/bin/env python3
"""Generate credits.md and youtube_description.txt from edl.json.
Run after Stage 2 (EDL exists) or Stage 3 (cuts.json exists for timecodes)."""
import json, os

BASE = "/home/ultron/protocol_pulse/segment_v1"

with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)

# Optional: load cuts for timecodes
cuts = []
cuts_path = os.path.join(BASE, "cuts_v2.json")
if os.path.exists(cuts_path):
    with open(cuts_path) as f:
        cuts = json.load(f)

# Collect all used channels in cut order
used = []
seen = set()

# Hook
hook = edl.get("hook")
if hook and hook.get("video_id"):
    key = (hook["video_id"], hook.get("channel", ""))
    if key not in seen:
        used.append({
            "channel": hook.get("channel", ""),
            "handle": hook.get("handle", ""),
            "title": hook.get("video_title", ""),
            "url": f"https://www.youtube.com/watch?v={hook['video_id']}",
            "word_start": hook.get("word_start", 0),
            "word_end": hook.get("word_end", 0),
            "role": "hook",
        })
        seen.add(key)

# Clips
for clip in edl.get("clips", []):
    entry = {
        "channel": clip.get("channel", ""),
        "handle": clip.get("handle", ""),
        "title": clip.get("video_title", ""),
        "url": clip.get("url", f"https://www.youtube.com/watch?v={clip['video_id']}"),
        "word_start": clip.get("word_start", 0),
        "word_end": clip.get("word_end", 0),
        "role": clip.get("role", "clip"),
    }
    used.append(entry)

# Unique channels for description
unique_channels = []
unique_seen = set()
for u in used:
    if u["handle"] not in unique_seen:
        unique_channels.append(u)
        unique_seen.add(u["handle"])

# --- credits.md ---
lines = ["# Credits — Segment V1 Medley", ""]
lines.append(f"**Topic:** {edl.get('topic', 'N/A')}")
lines.append(f"**Angle:** {edl.get('angle', 'N/A')}")
lines.append("")
lines.append("## Clips (cut order)")
lines.append("")
lines.append("| # | Channel | Handle | Video Title | URL | Timecode |")
lines.append("|---|---------|--------|-------------|-----|----------|")

for i, u in enumerate(used):
    tc = f"{u['word_start']:.1f}s – {u['word_end']:.1f}s"
    lines.append(f"| {i+1} | {u['channel']} | {u['handle']} | {u['title']} | {u['url']} | {tc} |")

lines.append("")
lines.append("## Standing Law")
lines.append("")
lines.append("Every source channel used in the final cut MUST be credited in:")
lines.append("1. **credits.md** — cut order: channel, @handle, title, URL, timecode range")
lines.append("2. **youtube_description.txt** — summary + Sources block")
lines.append("3. **Lower-thirds** — channel name burned into video overlay")
lines.append("4. **REPORT.md** — full credit listing")
lines.append("")

credits_md = "\n".join(lines)
with open(os.path.join(BASE, "credits.md"), "w") as f:
    f.write(credits_md)
print(f"Written credits.md ({len(used)} entries)")

# --- youtube_description.txt ---
desc = []
desc.append(edl.get("topic", "Protocol Pulse Medley"))
desc.append("")
desc.append(edl.get("angle", ""))
desc.append("")
desc.append("---")
desc.append("")
desc.append("Sources:")
for u in unique_channels:
    desc.append(f"• {u['channel']} ({u['handle']}): {u['title']}")
    desc.append(f"  {u['url']}")
    desc.append("")

desc.append("---")
desc.append("")
desc.append("Protocol Pulse — Bitcoin intelligence, distilled daily.")
desc.append("Subscribe for more: https://protocolpulse.io")

yt_desc = "\n".join(desc)
with open(os.path.join(BASE, "youtube_description.txt"), "w") as f:
    f.write(yt_desc)
print(f"Written youtube_description.txt ({len(unique_channels)} unique channels)")
