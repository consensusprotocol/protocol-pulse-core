#!/usr/bin/env python3
"""pipeline/run_isolated.py — Isolated v2f render orchestration (PINNED-CUT mode).

Creates a fresh run dir, sha256-checks all inputs, writes pinned cuts (no cutter),
measures clip_01 onset gap, pre-renders clip segments, then renderers + gates.
No edits to renderers, cutter, G14, G15, or any gate.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

from config import FPS, WIDTH, HEIGHT, VERT_W, VERT_H, NVENC_QP_INTERMEDIATE
from acoustic import apply_fades

SEGMENT_V2 = "/home/ultron/protocol_pulse/segment_v2"
RUNS_DIR = "/home/ultron/protocol_pulse/runs"

# Known-good sha256 hashes (from PRE_RENDER_CHECKPOINT.md section 7)
SOURCE_HASHES = {
    "RBFN4CB60To.mp4": "cfb2c57aebbfd9d41fb98694fa8adbfa5011bf880c9364ababd9dd49b2125460",
    "Pxrak-iMT0g.mp4": "57ba9c51544bbbe0449c3914c95b83448886db6d35cf400bf55ecce7d0f1354a",
    "QCgW8RlTu5Q.mp4": "a1f760077bf02cf1725f9bf68ef1ee7f23dfa192868a71b1cd73fdedb5b65bd4",
}

VO_HASHES = {
    "vo_intro_pp2_v1.wav": "ce576ec2373bbea0efaf0c96e0916cca3feec3153a0f1411a4808de3c6a95290",
    "vo_bridge_01_pp2_v1.wav": "6721610b1b69f20425e59df79bac3f96dfa167b8e08b5805935e9bbcec7d29a3",
    "vo_signoff_pp2_v1.wav": "8796e840c666c0e74e8d31a9d3d61c540ba3c8d183f8832cc94b3209a9462b78",
}

# Pinned cut table (PBX 2026-11-06 ~05:00 ET)
# CLIP1_OUT is supplied via --clip1-out CLI arg.
PINNED_CUTS_TEMPLATE = {
    "hook":    {"video_id": "RBFN4CB60To", "cut_in": 0.000, "cut_out": 9.520},
    "clip_01": {"video_id": "Pxrak-iMT0g", "cut_in": 238.550, "cut_out": None},  # set by CLI
    "clip_02": {"video_id": "RBFN4CB60To", "cut_in": 624.630, "cut_out": 636.720},
    "clip_03": {"video_id": "QCgW8RlTu5Q", "cut_in": 998.000, "cut_out": 1011.800},
}

CUTS_PINNED_MD = """\
# CUTS_PINNED.md

## Pinned cut table

| segment  | video_id      | cut_in   | cut_out  |
|----------|---------------|----------|----------|
| hook     | RBFN4CB60To   | 0.000    | 9.520    |
| clip_01  | Pxrak-iMT0g   | 238.550  | {clip1_out:.3f}    |
| clip_02  | RBFN4CB60To   | 624.630  | 636.720  |
| clip_03  | QCgW8RlTu5Q   | 998.000  | 1011.800 |

## Rationale

Pinned by PBX 2026-11-06 ~05:00 ET because the acoustic cutter cut inside
"thinks" (hook 9.13) and "themselves" (clip_03 997.25) and moved
clip_02/clip_03 out-points too close to the next word.

## Source evidence (whisper words + RMS)

- **hook**: whisper word_end=9.02 ("thinks."). Cutter valley at 9.13 clips the
  trailing sibilant. Pinned out=9.52 preserves the full word + 500ms tail.
- **clip_01**: whisper word_end=249.30 ("magnitude."). Pinned out={clip1_out:.3f}
  (supplied via --clip1-out). Gap to next-word onset measured at runtime.
- **clip_02**: whisper word_end=636.22 ("dollars."). Cutter out=636.78 extends
  60ms past pinned 636.72. Pinned value preserves 500ms silence after last word.
- **clip_03**: whisper word_start=997.30 ("pris-"). Cutter cut_in=997.25 starts
  50ms before the word, inside the preceding speaker's sentence ("themselves").
  Pinned cut_in=998.00 starts at the sentence boundary. Cutter cut_out=1012.13
  extends 330ms past pinned 1011.80. Pinned value preserves clean tail.

## clip_01 onset gap measurement

{gap_section}
"""


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def create_run_dir():
    """Create runs/v2f_<UTC timestamp>. Refuses if it exists."""
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    run_dir = os.path.join(RUNS_DIR, f"v2f_{ts}")
    if os.path.exists(run_dir):
        raise FileExistsError(f"ABORT: run dir already exists: {run_dir}")
    os.makedirs(run_dir)
    os.makedirs(os.path.join(run_dir, "sources"))
    os.makedirs(os.path.join(run_dir, "vo_audio"))
    os.makedirs(os.path.join(run_dir, "transcripts"))
    os.makedirs(os.path.join(run_dir, "out"))
    os.makedirs(os.path.join(run_dir, "qa"))
    return run_dir


def verify_and_link(run_dir):
    """sha256-check sources + VO stems, symlink into run dir. Refuses on mismatch."""
    src_dir = os.path.join(SEGMENT_V2, "sources")
    for name, expected in SOURCE_HASHES.items():
        path = os.path.join(src_dir, name)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"ABORT: hash mismatch {name}: {actual[:16]}... != {expected[:16]}...")
        os.symlink(path, os.path.join(run_dir, "sources", name))
        print(f"  source OK: {name}")

    vo_src = os.path.join(SEGMENT_V2, "vo_audio")
    for name, expected in VO_HASHES.items():
        path = os.path.join(vo_src, name)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"ABORT: VO hash mismatch {name}: {actual[:16]}... != {expected[:16]}...")
        os.symlink(path, os.path.join(run_dir, "vo_audio", name))
        print(f"  VO stem OK: {name}")

    # Copy VO_MANIFEST.json and edl.json and topic.json
    shutil.copy2(os.path.join(vo_src, "VO_MANIFEST.json"),
                 os.path.join(run_dir, "vo_audio", "VO_MANIFEST.json"))
    shutil.copy2(os.path.join(SEGMENT_V2, "edl.json"),
                 os.path.join(run_dir, "edl.json"))
    shutil.copy2(os.path.join(SEGMENT_V2, "topic.json"),
                 os.path.join(run_dir, "topic.json"))

    # Copy transcripts
    tx_src = os.path.join(SEGMENT_V2, "transcripts")
    for f in os.listdir(tx_src):
        shutil.copy2(os.path.join(tx_src, f), os.path.join(run_dir, "transcripts", f))

    print("  All inputs verified and linked.")


def write_pinned_cuts(run_dir, clip1_out):
    """Write cuts_final.json and update edl.json with pinned values."""
    cuts_table = []
    for clip_id in ["hook", "clip_01", "clip_02", "clip_03"]:
        tmpl = PINNED_CUTS_TEMPLATE[clip_id]
        cut_out = clip1_out if clip_id == "clip_01" else tmpl["cut_out"]
        cut_in = tmpl["cut_in"]
        cuts_table.append({
            "clip_id": clip_id,
            "video_id": tmpl["video_id"],
            "cut_in": round(cut_in, 3),
            "cut_out": round(cut_out, 3),
            "cut_duration": round(cut_out - cut_in, 3),
            "fade_out_ms": 30,
            "fade_in_ms": 20,
            "verified": True,
            "pinned": True,
        })

    cuts_path = os.path.join(run_dir, "cuts_final.json")
    with open(cuts_path, "w") as f:
        json.dump(cuts_table, f, indent=2)

    # Update edl.json with pinned cut_out values (as cut.py would)
    edl_path = os.path.join(run_dir, "edl.json")
    with open(edl_path) as f:
        edl = json.load(f)

    hook = edl.get("hook")
    if hook:
        hook["cut_out"] = 9.520
        hook["fade_out_ms"] = 30

    for clip in edl.get("clips", []):
        cid = f"clip_{clip['index']:02d}"
        entry = next((c for c in cuts_table if c["clip_id"] == cid), None)
        if entry:
            clip["cut_out"] = entry["cut_out"]
            clip["fade_out_ms"] = 30

    with open(edl_path, "w") as f:
        json.dump(edl, f, indent=2)

    print("\n  PINNED CUT TABLE:")
    print(f"  {'clip':<10} {'cut_in':>10} {'cut_out':>10} {'duration':>10}")
    for c in cuts_table:
        print(f"  {c['clip_id']:<10} {c['cut_in']:10.3f} {c['cut_out']:10.3f} "
              f"{c['cut_duration']:10.3f}")
    return cuts_table


def measure_onset_gap(source_path, cut_out, window_ms=10, run_length_ms=30,
                      threshold_db=12):
    """Measure gap from cut_out to next-word onset in source audio.

    onset = first run_length_ms consecutive windows within threshold_db of speech median.
    Returns (gap_ms, onset_time, speech_median_db, details_str).
    """
    # Extract audio: 2s of speech BEFORE cut_out (for median) + 2s after (for scan)
    pre_speech = 2.0
    analysis_dur = 2.0
    extract_start = max(0, cut_out - pre_speech)
    extract_dur = pre_speech + analysis_dur
    r = subprocess.run([
        "ffmpeg", "-y", "-ss", str(extract_start), "-i", source_path,
        "-t", str(extract_dur),
        "-ac", "1", "-ar", "48000", "-f", "f32le", "-",
    ], capture_output=True, timeout=30)
    samples = np.frombuffer(r.stdout, dtype=np.float32)

    sr = 48000
    hop = int(sr * window_ms / 1000)  # samples per window

    # Measure speech median from 2s BEFORE cut_out (clear speech, not the tail)
    speech_samples = int(pre_speech * sr)
    speech_rms_vals = []
    for i in range(0, speech_samples - hop, hop):
        chunk = samples[i:i + hop]
        rms = np.sqrt(np.mean(chunk ** 2)) if len(chunk) == hop else 0
        if rms > 0:
            speech_rms_vals.append(rms)

    if not speech_rms_vals:
        return (0, cut_out, -99, "ERROR: no speech samples found")

    speech_median_rms = np.median(speech_rms_vals)
    speech_median_db = 20 * np.log10(speech_median_rms + 1e-12)
    onset_threshold_rms = speech_median_rms * (10 ** (-threshold_db / 20))

    # Scan from cut_out forward (offset pre_speech into our extract)
    scan_start = int(pre_speech * sr)
    windows_needed = int(run_length_ms / window_ms)

    # Phase 1: skip any residual energy from the current word's tail
    # (wait for signal to drop below threshold — the silence gap)
    in_silence = False
    silence_start = scan_start
    for i in range(scan_start, len(samples) - hop, hop):
        chunk = samples[i:i + hop]
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms < onset_threshold_rms:
            in_silence = True
            silence_start = i
            break

    # Phase 2: find the next-word onset (first run_length_ms run above threshold)
    consecutive = 0
    onset_sample = None
    search_from = silence_start if in_silence else scan_start
    for i in range(search_from, len(samples) - hop, hop):
        chunk = samples[i:i + hop]
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms >= onset_threshold_rms:
            if consecutive == 0:
                onset_sample = i
            consecutive += 1
            if consecutive >= windows_needed:
                break
        else:
            consecutive = 0
            onset_sample = None

    if onset_sample is None:
        gap_val = analysis_dur * 1000
        return (gap_val, cut_out + analysis_dur, speech_median_db,
                f"No onset found in {analysis_dur}s after cut_out (clean silence)")

    # onset_sample is relative to our extract start (cut_out - pre_speech)
    onset_offset_s = (onset_sample - scan_start) / sr
    onset_time = cut_out + onset_offset_s
    gap_ms = onset_offset_s * 1000

    details = (f"speech_median={speech_median_db:.1f}dB, "
               f"threshold={20 * np.log10(onset_threshold_rms + 1e-12):.1f}dB "
               f"(-{threshold_db}dB), onset_at={onset_time:.3f}s, "
               f"gap={gap_ms:.1f}ms")
    return (gap_ms, onset_time, speech_median_db, details)


def _get_duration(path):
    """Return duration in seconds via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10, check=True)
    return float(r.stdout.strip())


def _get_stream_info(path):
    """Return (width, height, fps_num, fps_den, sample_rate, channels) via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10, check=True)
    parts = r.stdout.strip().split(",")
    w, h = int(parts[0]), int(parts[1])
    fps_parts = parts[2].split("/")
    fps = int(fps_parts[0]) / int(fps_parts[1]) if len(fps_parts) == 2 else float(fps_parts[0])

    r2 = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10, check=True)
    aparts = r2.stdout.strip().split(",")
    sr, ch = int(aparts[0]), int(aparts[1])
    return w, h, fps, sr, ch


def prerender_clips(run_dir, cuts_table):
    """Pre-render clip segments from source+cuts into qa_dir as final_<clip_id>.mp4.

    Matches segment_v2/qa_v1 finals: scale to 1920x1080 lanczos, setsar=1:1,
    24fps, 48kHz stereo, then acoustic.apply_fades with each cut's own fade lengths in milliseconds
    (cut["fade_in_ms"], cut["fade_out_ms"]; absent = 20 in / 30 out, the M19 defaults). DEC-10: a cut at an
    envelope minimum declares 83 ms (2 video frames); v2f's table declares 20 / 30, so its render is unchanged.
    """
    qa_dir = os.path.join(run_dir, "qa")
    sources_dir = os.path.join(run_dir, "sources")

    VF = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease:flags=lanczos,"
          f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1:1")

    for cut in cuts_table:
        clip_id = cut["clip_id"]
        src = os.path.join(sources_dir, f"{cut['video_id']}.mp4")
        raw_out = os.path.join(qa_dir, f"raw_{clip_id}.mp4")
        final_out = os.path.join(qa_dir, f"final_{clip_id}.mp4")

        cut_in = cut["cut_in"]
        dur = cut["cut_duration"]

        # Double-seek for accuracy: coarse seek then fine seek
        coarse = max(0, cut_in - 5)
        fine = cut_in - coarse

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(coarse), "-i", src, "-ss", str(fine), "-t", str(dur),
            "-vf", VF,
            "-r", str(FPS), "-vsync", "cfr",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp",
            "-qp", str(NVENC_QP_INTERMEDIATE),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", raw_out,
        ]
        print(f"  {clip_id}: ffmpeg {' '.join(cmd[1:])}")
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)

        # Apply M19 audio fades (20ms in, 30ms out) — matches acoustic.apply_fades defaults; a DEC-10 cut at an
        # envelope minimum declares its 2-frame fade in the cut table (v2f's table declares 20 / 30: unchanged)
        apply_fades(raw_out, final_out, cut_in_fade_ms=cut.get("fade_in_ms", 20), cut_out_fade_ms=cut.get("fade_out_ms", 30))
        os.unlink(raw_out)

        dur_actual = _get_duration(final_out)
        w, h, fps, sr, ch = _get_stream_info(final_out)
        print(f"  {clip_id}: {dur_actual:.2f}s {w}x{h} {fps}fps {sr}Hz ({final_out})")


def preflight_check(run_dir):
    """Assert pre-rendered clips + shoutout are 1920x1080, 24fps, 48kHz.

    Checks final_hook, final_clip_*, shoutout_16x9, shoutout_9x16.
    These are the inputs produced by run_isolated.py before render16/render9.
    (VO plates and reframed clips are produced by the renderers themselves.)
    Aborts (sys.exit(1)) on any mismatch.
    """
    qa_dir = os.path.join(run_dir, "qa")
    targets = [f for f in os.listdir(qa_dir)
               if f.endswith(".mp4") and (f.startswith("final_") or f.startswith("shoutout_"))]

    print(f"\n  Preflight: checking {len(targets)} pre-rendered inputs...")
    errors = []
    for fname in sorted(targets):
        path = os.path.join(qa_dir, fname)
        try:
            w, h, fps, sr, ch = _get_stream_info(path)
        except Exception as e:
            errors.append(f"  {fname}: probe failed ({e})")
            continue

        # Determine expected resolution by filename
        if "9x16" in fname:
            exp_w, exp_h = VERT_W, VERT_H
        else:
            exp_w, exp_h = WIDTH, HEIGHT

        if (w, h) != (exp_w, exp_h):
            errors.append(f"  {fname}: {w}x{h} != {exp_w}x{exp_h}")
        if round(fps) != FPS:
            errors.append(f"  {fname}: {fps}fps != {FPS}fps")
        if sr != 48000:
            errors.append(f"  {fname}: {sr}Hz != 48000Hz")

    if errors:
        print(f"\n** PREFLIGHT ABORT **")
        for e in errors:
            print(e)
        sys.exit(1)
    print(f"  Preflight: PASS — all {len(targets)} inputs verified")


def postflight_check(output_path, expected_dur, aspect, log_output=""):
    """Abort if output duration, resolution, or reframe-fallback is wrong.

    - Duration must be within 0.05s of expected.
    - Resolution must match aspect (1920x1080 or 1080x1920).
    - For 9:16: any 'reframe failed' + 'using original' in log is fatal.
    """
    errors = []

    if not os.path.exists(output_path):
        print(f"\n** POSTFLIGHT ABORT ({aspect}): output file missing: {output_path} **")
        sys.exit(1)

    dur = _get_duration(output_path)
    w, h, fps, sr, ch = _get_stream_info(output_path)

    if aspect == "16x9":
        exp_w, exp_h = WIDTH, HEIGHT
    else:
        exp_w, exp_h = VERT_W, VERT_H

    if abs(dur - expected_dur) > 0.05:
        errors.append(f"duration {dur:.3f}s vs expected {expected_dur:.3f}s "
                      f"(delta {abs(dur - expected_dur):.3f}s > 0.05s)")
    if (w, h) != (exp_w, exp_h):
        errors.append(f"resolution {w}x{h} != {exp_w}x{exp_h}")
    if aspect == "9x16" and "reframe failed" in log_output and "using original" in log_output:
        errors.append("9:16 reframe fallback detected — mixed resolution likely")

    if errors:
        print(f"\n** POSTFLIGHT ABORT ({aspect}) **")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    print(f"  Postflight ({aspect}): PASS — {dur:.2f}s, {w}x{h}")


def run_pipeline(run_dir):
    """Run renderers + gates. Never calls telegram.

    Order (F2): shoutout both → render16 → render9 → gates16 → gates9.
    Gate failure blocks DELIVERY, not the other render.
    Preflight before each render; postflight after each render.
    """
    from shoutout import build_shoutout
    from render16 import render_16x9
    from render_vertical import render_9x16
    from gates import run_gates
    from config import resolve_paths

    # Shoutout both
    print("\n=== SHOUTOUT ===")
    build_shoutout(run_dir, None, "16x9")
    build_shoutout(run_dir, None, "9x16")

    paths = resolve_paths(run_dir)

    # ── Preflight: verify all pre-rendered inputs ──
    print("\n=== PREFLIGHT ===")
    preflight_check(run_dir)

    print("\n=== RENDER 16:9 ===")
    render_16x9(run_dir, None, "segment.mp4")

    final_16 = os.path.join(paths["out_dir"], "segment.mp4")
    manifest_16 = os.path.join(paths["qa_dir"], "concat_manifest_16x9.json")
    # Read segment-list total from manifest for postflight
    with open(manifest_16) as f:
        mfst = json.load(f)
    segs = mfst.get("segments", [])
    total_16 = max(seg.get("end", 0) for seg in segs) if segs else 0
    postflight_check(final_16, total_16, "16x9")

    # ── 9:16 ──
    print("\n=== RENDER 9:16 ===")
    # Capture stdout to detect "reframe failed ... using original"
    import io
    old_stdout = sys.stdout
    tee_buf = io.StringIO()

    class Tee:
        """Write to both original stdout and capture buffer."""
        def __init__(self, orig, buf):
            self.orig = orig
            self.buf = buf
        def write(self, s):
            self.orig.write(s)
            self.buf.write(s)
        def flush(self):
            self.orig.flush()

    sys.stdout = Tee(old_stdout, tee_buf)
    try:
        render_9x16(run_dir, None, "segment_vertical.mp4")
    finally:
        sys.stdout = old_stdout
    render_log = tee_buf.getvalue()

    final_9 = os.path.join(paths["out_dir"], "segment_vertical.mp4")
    manifest_9_path = os.path.join(paths["qa_dir"], "concat_manifest_9x16.json")
    if os.path.exists(manifest_9_path):
        with open(manifest_9_path) as f:
            mfst9 = json.load(f)
        segs9 = mfst9.get("segments", [])
        total_9 = max(seg.get("end", 0) for seg in segs9) if segs9 else total_16
    else:
        total_9 = total_16  # fallback: same segment count
    postflight_check(final_9, total_9, "9x16", log_output=render_log)

    # Gates both (record results, don't short-circuit)
    print("\n=== GATES 16:9 ===")
    ok16, _ = run_gates(run_dir, final_16, manifest_16)

    print("\n=== GATES 9:16 ===")
    ok9, _ = run_gates(run_dir, final_9, manifest_9_path)

    if not ok16:
        print("\n** GATE FAILURE 16:9 **")
    if not ok9:
        print("\n** GATE FAILURE 9:16 **")

    print(f"\n=== PIPELINE COMPLETE — 16:9 {'PASS' if ok16 else 'FAIL'} / "
          f"9:16 {'PASS' if ok9 else 'FAIL'} (no telegram) ===")
    return ok16 and ok9


def main():
    parser = argparse.ArgumentParser(description="Isolated v2f render (PINNED-CUT)")
    parser.add_argument("--clip1-out", type=float, required=True,
                        help="clip_01 cut_out value (required, no default)")
    parser.add_argument("--allow-clip1-gap-ms", type=float, default=None,
                        help="Override minimum clip_01 onset gap (default: 60ms)")
    args = parser.parse_args()

    t0 = time.time()
    print("=== ISOLATED v2f RENDER (PINNED-CUT) ===\n")

    # 1. Create run dir
    run_dir = create_run_dir()
    print(f"Run dir: {run_dir}")

    # 2. Verify and link inputs
    print("\nVerifying inputs...")
    verify_and_link(run_dir)

    # 3. Write pinned cuts
    print("\nWriting pinned cuts...")
    cuts_table = write_pinned_cuts(run_dir, args.clip1_out)

    # 4. Measure clip_01 onset gap
    print("\nMeasuring clip_01 onset gap...")
    source_path = os.path.join(run_dir, "sources", "Pxrak-iMT0g.mp4")
    gap_ms, onset_time, speech_median_db, details = measure_onset_gap(
        source_path, args.clip1_out)
    print(f"  {details}")
    print(f"  GAP: {gap_ms:.1f}ms")

    min_gap = 60.0
    gap_exception = ""
    if args.allow_clip1_gap_ms is not None:
        min_gap = args.allow_clip1_gap_ms
        gap_exception = (f"\n--allow-clip1-gap-ms={args.allow_clip1_gap_ms} given; "
                         f"minimum overridden from 60ms to {min_gap}ms.")

    if gap_ms < min_gap:
        gap_section = (f"gap={gap_ms:.1f}ms < {min_gap}ms — **ABORT**\n{details}"
                       f"{gap_exception}")
        # Write CUTS_PINNED.md before aborting
        md_path = os.path.join(run_dir, "CUTS_PINNED.md")
        with open(md_path, "w") as f:
            f.write(CUTS_PINNED_MD.format(clip1_out=args.clip1_out,
                                           gap_section=gap_section))
        print(f"\n** ABORT: clip_01 onset gap {gap_ms:.1f}ms < {min_gap}ms **")
        print(f"  Run dir preserved: {run_dir}")
        sys.exit(2)

    gap_section = (f"gap={gap_ms:.1f}ms >= {min_gap}ms — **PASS**\n{details}"
                   f"{gap_exception}")

    # Write CUTS_PINNED.md
    md_path = os.path.join(run_dir, "CUTS_PINNED.md")
    with open(md_path, "w") as f:
        f.write(CUTS_PINNED_MD.format(clip1_out=args.clip1_out,
                                       gap_section=gap_section))
    print(f"  Wrote {md_path}")

    # 5. Pre-render clip segments from source
    print("\nPre-rendering clips from source...")
    prerender_clips(run_dir, cuts_table)

    # 6. Render + gates
    success = run_pipeline(run_dir)

    elapsed = time.time() - t0
    print(f"\nTotal: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    if not success:
        sys.exit(1)
    print(f"\nOutput: {run_dir}/out/")


if __name__ == "__main__":
    main()
