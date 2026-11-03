#!/usr/bin/env python3
"""Render preview_v3.mp4: 640x360 24fps with fixed tails (Law 14c),
corrected VO intro (6.4B), and Ken Burns + waveform VO visuals."""
import json, os, subprocess, sys

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v3")
os.makedirs(QA, exist_ok=True)

with open(os.path.join(BASE, "cuts_v3.json")) as f:
    cuts = json.load(f)

with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)

# VO visual segments (already rendered by render_vo_visual.py)
VO_INTRO_VIS = os.path.join(QA, "vo_intro_visual.mp4")
VO_BRIDGE_VIS = os.path.join(QA, "vo_bridge_visual.mp4")

FPS = 24
bridge_after = None
for b in edl.get("vo", {}).get("bridges", []):
    bridge_after = b.get("after_clip")


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def render_clip_segment(cut, out_path):
    """Render clip at 640x360 24fps with loudnorm and 20ms fades."""
    src = os.path.join(SOURCES, f"{cut['video_id']}.mp4")
    dur = cut["cut_out"] - cut["cut_in"]
    fade_out_start = max(dur - 0.02, 0)
    r = subprocess.run([
        "ffmpeg", "-y", "-ss", str(cut["cut_in"]), "-to", str(cut["cut_out"]),
        "-i", src,
        "-vf", f"scale=640:360", "-r", str(FPS), "-vsync", "cfr",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
        "-af", f"loudnorm=I=-18:TP=-1.5:LRA=11,afade=t=in:d=0.02,afade=t=out:st={fade_out_start:.3f}:d=0.02",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
        out_path,
    ], capture_output=True, timeout=120)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 1000


def scale_vo_visual(src, out_path):
    """Scale VO visual from 640x360 (already preview size) to ensure format match."""
    r = subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-vf", "scale=640:360", "-r", str(FPS), "-vsync", "cfr",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
        out_path,
    ], capture_output=True, timeout=60)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 500


print("=== RENDERING PREVIEW v3 ===\n")

segments = []

# 1. Hook
hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
if hook_cut:
    p = os.path.join(QA, "pv3_hook.mp4")
    if render_clip_segment(hook_cut, p):
        segments.append(("hook", p))
        print(f"  hook: OK ({get_duration(p):.2f}s)")

# 2. VO intro visual
if os.path.exists(VO_INTRO_VIS):
    p = os.path.join(QA, "pv3_vo_intro.mp4")
    if scale_vo_visual(VO_INTRO_VIS, p):
        segments.append(("vo_intro", p))
        print(f"  vo_intro: OK ({get_duration(p):.2f}s)")

# 3. Clips with VO bridge after specified clip
for cut in cuts:
    if cut["clip_id"] == "hook":
        continue
    p = os.path.join(QA, f"pv3_{cut['clip_id']}.mp4")
    if render_clip_segment(cut, p):
        segments.append((cut["clip_id"], p))
        print(f"  {cut['clip_id']}: OK ({get_duration(p):.2f}s)")

    # Insert VO bridge after the specified clip
    clip_num = int(cut["clip_id"].split("_")[1]) if "_" in cut["clip_id"] else 0
    if bridge_after and clip_num == bridge_after and os.path.exists(VO_BRIDGE_VIS):
        bp = os.path.join(QA, "pv3_vo_bridge.mp4")
        if scale_vo_visual(VO_BRIDGE_VIS, bp):
            segments.append(("vo_bridge", bp))
            print(f"  vo_bridge: OK ({get_duration(bp):.2f}s)")

if not segments:
    print("ERROR: No segments rendered")
    sys.exit(1)

# Concat
filelist = os.path.join(QA, "pv3_filelist.txt")
with open(filelist, "w") as f:
    for label, path in segments:
        f.write(f"file '{path}'\n")

order = " -> ".join(s[0] for s in segments)
print(f"\n  Order: {order}")

preview_path = os.path.join(BASE, "preview_v3.mp4")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
    "-vf", "setpts=PTS-STARTPTS",
    "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
    "-movflags", "+faststart", preview_path,
], capture_output=True, timeout=180)

# Verify
if os.path.exists(preview_path):
    dur = get_duration(preview_path)
    sz = os.path.getsize(preview_path)
    # Count frames
    nb = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", preview_path],
        capture_output=True, text=True, timeout=60).stdout.strip()
    # Get FPS
    fps_str = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", preview_path],
        capture_output=True, text=True, timeout=10).stdout.strip()

    print(f"\n  Preview: {preview_path}")
    print(f"  Duration: {dur:.2f}s")
    print(f"  Frames: {nb}")
    print(f"  FPS: {fps_str}")
    print(f"  Size: {sz:,} bytes ({sz/1024/1024:.1f} MB)")
    print(f"  Duration check (60-120s): {'PASS' if 60 <= dur <= 120 else 'WARN'}")
else:
    print("ERROR: Preview failed")
    sys.exit(1)
