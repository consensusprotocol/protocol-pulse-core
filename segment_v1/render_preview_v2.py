#!/usr/bin/env python3
"""Render preview_v2.mp4: 640x360 30fps CFR, loudnorm, 20ms audio fades, straight cuts.
Then measure all seams from the rendered file."""
import json, os, subprocess, numpy as np, wave, math

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v2")
os.makedirs(QA, exist_ok=True)

with open(os.path.join(BASE, "cuts_v2.json")) as f:
    cuts = json.load(f)

with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)

# VO audio paths
VO_INTRO = os.path.join(BASE, "vo_audio", "vo_intro.wav")
VO_BRIDGE = os.path.join(BASE, "vo_audio", "vo_bridge_01.wav")

# Build order: hook -> VO intro -> clip_01 -> clip_02 -> clip_03 -> VO bridge -> clip_04
bridge_after = None
for b in edl.get("vo", {}).get("bridges", []):
    bridge_after = b.get("after_clip")


def render_clip_segment(cut, out_path):
    """Render a single clip segment at 640x360 30fps with loudnorm and 20ms fades."""
    src = os.path.join(SOURCES, f"{cut['video_id']}.mp4")
    dur = cut["cut_duration"]
    fade_out_start = max(dur - 0.02, 0)
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(cut["cut_in"]), "-to", str(cut["cut_out"]),
        "-i", src,
        "-vf", "scale=640:360", "-r", "30", "-vsync", "cfr",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
        "-af", f"loudnorm=I=-18:TP=-1.5:LRA=11,afade=t=in:d=0.02,afade=t=out:st={fade_out_start:.3f}:d=0.02",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
        out_path,
    ], capture_output=True, timeout=120)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 1000


def render_vo_segment(wav_path, out_path):
    """Render VO WAV as a black-background 640x360 video with 20ms fades."""
    dur_s = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav_path],
        capture_output=True, text=True, timeout=10
    ).stdout.strip()
    dur = float(dur_s)
    fade_out_start = max(dur - 0.02, 0)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=640x360:r=30:d={dur:.3f}",
        "-i", wav_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
        "-af", f"afade=t=in:d=0.02,afade=t=out:st={fade_out_start:.3f}:d=0.02",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
        "-shortest", out_path,
    ], capture_output=True, timeout=60)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 500


print("=== RENDERING PREVIEW v2 ===\n")

# Build segments in order
segments = []

# 1. Hook
hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
if hook_cut:
    p = os.path.join(QA, "pv2f_hook.mp4")
    if render_clip_segment(hook_cut, p):
        segments.append(("hook", p))
        print(f"  hook: OK")

# 2. VO intro
if os.path.exists(VO_INTRO):
    p = os.path.join(QA, "pv2f_vo_intro.mp4")
    if render_vo_segment(VO_INTRO, p):
        segments.append(("vo_intro", p))
        print(f"  vo_intro: OK")

# 3. Clips with VO bridge after specified clip
for cut in cuts:
    if cut["clip_id"] == "hook":
        continue
    p = os.path.join(QA, f"pv2f_{cut['clip_id']}.mp4")
    if render_clip_segment(cut, p):
        segments.append((cut["clip_id"], p))
        print(f"  {cut['clip_id']}: OK")

    # Insert VO bridge after the specified clip
    clip_num = int(cut["clip_id"].split("_")[1]) if "_" in cut["clip_id"] else 0
    if bridge_after and clip_num == bridge_after and os.path.exists(VO_BRIDGE):
        bp = os.path.join(QA, "pv2f_vo_bridge.mp4")
        if render_vo_segment(VO_BRIDGE, bp):
            segments.append(("vo_bridge", bp))
            print(f"  vo_bridge (after clip_{bridge_after:02d}): OK")

# Concat
filelist = os.path.join(QA, "pv2f_filelist.txt")
with open(filelist, "w") as f:
    for label, path in segments:
        f.write(f"file '{path}'\n")

print(f"\n  Segment order: {' -> '.join(s[0] for s in segments)}")

preview_path = os.path.join(BASE, "preview_v2.mp4")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
    "-vf", "setpts=PTS-STARTPTS",
    "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
    "-movflags", "+faststart", preview_path,
], capture_output=True, timeout=180)

# Verify
dur_str = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", preview_path],
    capture_output=True, text=True, timeout=10
).stdout.strip()
nb_frames = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
     "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", preview_path],
    capture_output=True, text=True, timeout=60
).stdout.strip()
file_size = os.path.getsize(preview_path)

print(f"\n  Preview: {preview_path}")
print(f"  Duration: {dur_str}s")
print(f"  Frames: {nb_frames}")
print(f"  Size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")

dur_f = float(dur_str)
nb_f = int(nb_frames) if nb_frames.isdigit() else 0
ok_dur = 60 <= dur_f <= 120
ok_frames = nb_f > 1500
ok_size = file_size > 3 * 1024 * 1024

print(f"  Duration check (60-120s): {'PASS' if ok_dur else 'FAIL'}")
print(f"  Frame count check (>1500): {'PASS' if ok_frames else 'FAIL'}")
print(f"  Size check (>3MB): {'PASS' if ok_size else 'FAIL'}")

# Extract frame at 30s
frame_path = os.path.join(QA, "preview_v2_frame30s.png")
subprocess.run([
    "ffmpeg", "-y", "-ss", "30", "-i", preview_path, "-vframes", "1", "-q:v", "2", frame_path,
], capture_output=True, timeout=30)
print(f"  Frame at 30s: {frame_path} ({os.path.getsize(frame_path):,} bytes)")

# === POST-PREVIEW SEAM MEASUREMENT ===
print("\n=== POST-PREVIEW SEAM MEASUREMENT ===\n")

# Extract full preview audio
pv_wav = os.path.join(QA, "pv2f_full.wav")
subprocess.run([
    "ffmpeg", "-y", "-i", preview_path, "-vn", "-ac", "1", "-ar", "16000",
    "-c:a", "pcm_s16le", pv_wav,
], capture_output=True, timeout=60)


def read_wav(path):
    try:
        with wave.open(path, 'rb') as wf:
            n = wf.getnframes()
            if n == 0:
                return np.array([], dtype=np.float32), 0
            raw = wf.readframes(n)
            sr = wf.getframerate()
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr
    except Exception:
        return np.array([], dtype=np.float32), 0


def db(val):
    if val <= 0:
        return -80.0
    return max(20 * math.log10(val), -80.0)


pv_samples, pv_sr = read_wav(pv_wav)
if len(pv_samples) == 0:
    print("  ERROR: Could not read preview audio")
else:
    # Build boundary times from segment durations
    boundary_times = []
    boundary_labels = []
    offset = 0.0
    for i, (label, path) in enumerate(segments):
        seg_dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10
        ).stdout.strip())
        offset += seg_dur
        if i < len(segments) - 1:
            boundary_times.append(offset)
            boundary_labels.append((label, segments[i + 1][0]))

    all_seams = []
    for i, (t, (a_label, b_label)) in enumerate(zip(boundary_times, boundary_labels)):
        # Measure 200ms each side
        a_idx = int(max(0, t - 0.2) * pv_sr)
        b_idx = int(t * pv_sr)
        c_idx = int(min(len(pv_samples) / pv_sr, t + 0.2) * pv_sr)
        seg_a = pv_samples[a_idx:b_idx]
        seg_b = pv_samples[b_idx:c_idx]

        if len(seg_a) > 0 and len(seg_b) > 0:
            rms_a = np.sqrt(np.mean(seg_a ** 2))
            rms_b = np.sqrt(np.mean(seg_b ** 2))
            jump = abs(db(rms_a) - db(rms_b))
            passed = jump <= 12.0
            seam = {
                "seam_id": f"pv_seam_{i+1:02d}",
                "between": [a_label, b_label],
                "boundary_time_s": round(t, 3),
                "boundary_jump_db": round(jump, 1),
                "pass": passed,
            }
            # Flag VO bridge seam
            if "vo_bridge" in (a_label, b_label):
                seam["note"] = "VO bridge edge"
            all_seams.append(seam)
            status = "PASS" if passed else "FAIL"
            note = f" [{seam.get('note', '')}]" if seam.get("note") else ""
            print(f"  pv_seam_{i+1:02d}: {status} ({jump:.1f}dB) {a_label} -> {b_label}{note}")

    pass_count = sum(1 for s in all_seams if s.get("pass"))
    fail_count = len(all_seams) - pass_count
    print(f"\n  Result: {pass_count}/{len(all_seams)} PASS" + (f", {fail_count} FLAGGED" if fail_count else ""))

    # Write seams
    with open(os.path.join(BASE, "seams_v2.json"), "w") as f:
        json.dump(all_seams, f, indent=2)
    print(f"  Written seams_v2.json ({len(all_seams)} entries)")
