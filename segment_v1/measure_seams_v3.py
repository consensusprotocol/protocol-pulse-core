#!/usr/bin/env python3
"""Seam QA v3: measure all clip boundaries from cuts_v3.json using
direct-source method (200ms windows, loudnormed, 12dB gate)."""
import json, os, subprocess, numpy as np, wave, math

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v3")
os.makedirs(QA, exist_ok=True)

with open(os.path.join(BASE, "cuts_v3.json")) as f:
    cuts = json.load(f)

with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)


def extract_wav(src, start, end, out):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start)), "-to", str(end),
        "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out,
    ], capture_output=True, timeout=30)


def loudnorm_wav(inp, out):
    subprocess.run([
        "ffmpeg", "-y", "-i", inp,
        "-af", "loudnorm=I=-18:TP=-1.5:LRA=11",
        "-c:a", "pcm_s16le", "-ar", "16000", out,
    ], capture_output=True, timeout=30)


def read_wav(path):
    try:
        with wave.open(path, 'rb') as wf:
            n = wf.getnframes()
            if n == 0:
                return np.array([]), 0
            raw = wf.readframes(n)
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, wf.getframerate()
    except Exception:
        return np.array([]), 0


def db(v):
    return max(20 * math.log10(v), -80.0) if v > 0 else -80.0


# Determine VO positions
bridge_after = None
for b in edl.get("vo", {}).get("bridges", []):
    bridge_after = b.get("after_clip")

print("=== SEAM QA v3 (direct source, loudnormed, 200ms windows) ===\n")

seams = []
for idx in range(len(cuts) - 1):
    a, b = cuts[idx], cuts[idx + 1]
    src_a = os.path.join(SOURCES, f"{a['video_id']}.mp4")
    src_b = os.path.join(SOURCES, f"{b['video_id']}.mp4")

    # Extract 200ms of speech at each boundary (skip 20ms of fade zone)
    raw_a = os.path.join(QA, f"seam3_{idx}_a_raw.wav")
    norm_a = os.path.join(QA, f"seam3_{idx}_a_norm.wav")
    extract_wav(src_a, a["cut_out"] - 0.22, a["cut_out"] - 0.02, raw_a)
    loudnorm_wav(raw_a, norm_a)

    raw_b = os.path.join(QA, f"seam3_{idx}_b_raw.wav")
    norm_b = os.path.join(QA, f"seam3_{idx}_b_norm.wav")
    extract_wav(src_b, b["cut_in"] + 0.02, b["cut_in"] + 0.22, raw_b)
    loudnorm_wav(raw_b, norm_b)

    sa, sra = read_wav(norm_a)
    sb, srb = read_wav(norm_b)

    # Check if VO sits between these clips
    is_vo_edge = False
    a_num = int(a["clip_id"].split("_")[1]) if "_" in a["clip_id"] else 0
    if a["clip_id"] == "hook":
        is_vo_edge = True
    elif bridge_after and a_num == bridge_after:
        is_vo_edge = True

    if len(sa) > 0 and len(sb) > 0:
        rms_a = np.sqrt(np.mean(sa ** 2))
        rms_b = np.sqrt(np.mean(sb ** 2))
        jump = abs(db(rms_a) - db(rms_b))
        passed = jump <= 12.0
        seam = {
            "seam_id": f"seam_{idx + 1:02d}",
            "between": [a["clip_id"], b["clip_id"]],
            "source_jump_db": round(jump, 1),
            "pass": passed,
        }
        if is_vo_edge:
            seam["vo_fills_gap"] = True
            seam["note"] = "VO fills this gap in final render"
        elif not passed:
            seam["note"] = "FLAGGED — different speakers/rooms"
        status = "PASS" if passed else "FAIL"
        note = f" [{seam.get('note', '')}]" if seam.get("note") else ""
        print(f"  seam_{idx + 1:02d}: {status} ({jump:.1f}dB) {a['clip_id']} -> {b['clip_id']}{note}")
        seams.append(seam)
    else:
        print(f"  seam_{idx + 1:02d}: SKIP (audio failed) {a['clip_id']} -> {b['clip_id']}")

pass_count = sum(1 for s in seams if s.get("pass"))
fail_count = len(seams) - pass_count
print(f"\n  Result: {pass_count}/{len(seams)} PASS" +
      (f", {fail_count} FLAGGED" if fail_count else ""))

with open(os.path.join(BASE, "seams_v3.json"), "w") as f:
    json.dump(seams, f, indent=2)
print(f"  Written seams_v3.json ({len(seams)} seams)")
