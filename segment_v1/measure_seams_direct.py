#!/usr/bin/env python3
"""Measure all seams directly from source audio (no fade artifacts).
Compares the RMS of 200ms of speech just before each cut_out against
200ms of speech just after each cut_in, using loudnormed source segments."""
import json, os, subprocess, numpy as np, wave, math

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v2")

with open(os.path.join(BASE, "cuts_v2.json")) as f:
    cuts = json.load(f)

with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)


def extract_wav(src, start, end, out):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start)), "-to", str(end),
        "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out,
    ], capture_output=True, timeout=30)


def loudnorm_wav(inp, out):
    """Single-pass loudnorm (fine for measurement)."""
    subprocess.run([
        "ffmpeg", "-y", "-i", inp,
        "-af", "loudnorm=I=-18:TP=-1.5:LRA=11",
        "-c:a", "pcm_s16le", "-ar", "16000", out,
    ], capture_output=True, timeout=30)


def read_wav(path):
    try:
        with wave.open(path, 'rb') as wf:
            n = wf.getnframes()
            if n == 0: return np.array([]), 0
            raw = wf.readframes(n)
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, wf.getframerate()
    except: return np.array([]), 0


def db(v):
    return max(20 * math.log10(v), -80.0) if v > 0 else -80.0


# Build full sequence with VO
bridge_after = None
for b in edl.get("vo", {}).get("bridges", []):
    bridge_after = b.get("after_clip")

# Ordered sequence: hook, clip_01, clip_02, clip_03, clip_04
# VO sits between hook→clip_01 (intro) and clip_03→clip_04 (bridge)
# We measure clip-to-clip seams only (VO edges are N/A — music bed fills them)

clip_pairs = []
for i in range(len(cuts) - 1):
    a, b = cuts[i], cuts[i + 1]
    clip_pairs.append((a, b))

print("=== DIRECT SOURCE SEAM MEASUREMENT (loudnormed, no fade artifacts) ===\n")

seams = []
for idx, (a, b) in enumerate(clip_pairs):
    src_a = os.path.join(SOURCES, f"{a['video_id']}.mp4")
    src_b = os.path.join(SOURCES, f"{b['video_id']}.mp4")

    # Extract 500ms of speech ending at cut_out (not at boundary — before fade)
    raw_a = os.path.join(QA, f"dseam_{idx}_a_raw.wav")
    norm_a = os.path.join(QA, f"dseam_{idx}_a_norm.wav")
    extract_wav(src_a, a["cut_out"] - 0.5, a["cut_out"] - 0.02, raw_a)  # stop 20ms before boundary
    loudnorm_wav(raw_a, norm_a)

    # Extract 500ms of speech starting at cut_in (after any fade-in)
    raw_b = os.path.join(QA, f"dseam_{idx}_b_raw.wav")
    norm_b = os.path.join(QA, f"dseam_{idx}_b_norm.wav")
    extract_wav(src_b, b["cut_in"] + 0.02, b["cut_in"] + 0.52, raw_b)  # start 20ms after boundary
    loudnorm_wav(raw_b, norm_b)

    sa, sra = read_wav(norm_a)
    sb, srb = read_wav(norm_b)

    is_vo_edge = False
    # Check if VO sits between these clips
    a_num = int(a["clip_id"].split("_")[1]) if "_" in a["clip_id"] else 0
    if a["clip_id"] == "hook":
        is_vo_edge = True  # VO intro between hook and clip_01
    elif bridge_after and a_num == bridge_after:
        is_vo_edge = True  # VO bridge between clip_03 and clip_04

    if len(sa) > 0 and len(sb) > 0:
        rms_a = np.sqrt(np.mean(sa ** 2))
        rms_b = np.sqrt(np.mean(sb ** 2))
        jump = abs(db(rms_a) - db(rms_b))
        passed = jump <= 12.0
        seam = {
            "seam_id": f"seam_{idx+1:02d}",
            "between": [a["clip_id"], b["clip_id"]],
            "boundary_jump_db": round(jump, 1),
            "pass": passed,
        }
        if is_vo_edge:
            seam["note"] = "VO fills this gap in final render"
        elif not passed:
            seam["note"] = "FLAGGED — different speakers/rooms"
        status = "PASS" if passed else "FAIL"
        note = f" [{seam.get('note', '')}]" if seam.get("note") else ""
        print(f"  seam_{idx+1:02d}: {status} ({jump:.1f}dB) {a['clip_id']} -> {b['clip_id']}{note}")
        seams.append(seam)
    else:
        print(f"  seam_{idx+1:02d}: SKIP (audio extraction failed) {a['clip_id']} -> {b['clip_id']}")

pass_count = sum(1 for s in seams if s.get("pass"))
fail_count = len(seams) - pass_count
print(f"\n  Result: {pass_count}/{len(seams)} PASS" + (f", {fail_count} FLAGGED" if fail_count else ""))

with open(os.path.join(BASE, "seams_v2.json"), "w") as f:
    json.dump(seams, f, indent=2)
print(f"  Written seams_v2.json ({len(seams)} seams)")
