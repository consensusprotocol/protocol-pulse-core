#!/usr/bin/env python3
"""pipeline/gates.py — Parameterised QA gate runner.

FROZEN from segment_v1/qa_gates.py. Delegates to the original gate functions.
Only difference: paths resolved from --segment dir, VO_DIR set dynamically.
M23: G15 (credits continuous + ring aspect ratio) added here.

Usage:
    python3 -m pipeline.gates --segment <segment_dir> --final <mp4> --manifest <json> [--qa-version N]
"""
import argparse
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths

# Patch BASE and VO_DIR before importing qa_gates
import importlib


def _get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


# ── G14: AUDIO-VISUAL ALIGNMENT (Amendment 1 rewrite) ──
#
# For each sampled output time t (joins + inside every clip <= 2s):
#   1. Cross-correlate output audio window against the clip's source audio
#      to find the matching source time independently of the render schedule.
#   2. Compare the output frame at t with the source frame at matched source time.
#   3. 40ms tolerance. Inconclusive = HOLD, never PASS.

def _extract_audio_mono(mp4, start_s, dur_s, sr=16000):
    """Extract a mono audio segment as int16 numpy array.
    Uses fast keyframe seek to get close, then precise decode with -ss after -i
    for the residual offset. This avoids both full-file decode and keyframe bias."""
    # Fast-seek to 5s before target, then precise-seek the remainder
    fast_seek = max(0, start_s - 5.0)
    precise_offset = start_s - fast_seek
    r = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(fast_seek),       # fast keyframe seek
        "-i", mp4,
        "-ss", str(precise_offset),   # precise decode offset
        "-t", str(dur_s),
        "-ar", str(sr), "-ac", "1", "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1",
    ], capture_output=True, timeout=30)
    if r.returncode != 0 or len(r.stdout) < 2:
        return None
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32)


def _extract_frame(mp4, time_s, tmp_path):
    """Extract a single frame at time_s, return as numpy BGR array or None."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(time_s), "-i", mp4,
        "-vframes", "1", "-q:v", "2", tmp_path,
    ], capture_output=True, timeout=15)
    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
        img = cv2.imread(tmp_path)
        os.unlink(tmp_path)
        return img
    return None


def _xcorr_offset(output_audio, source_audio, sr=16000):
    """Cross-correlate to find the offset (in seconds) of output within source.
    Returns (offset_s, peak_correlation). offset_s is the source time corresponding
    to the start of output_audio."""
    if output_audio is None or source_audio is None:
        return None, 0.0
    if len(output_audio) < 100 or len(source_audio) < 100:
        return None, 0.0

    # Normalize
    oa = output_audio - output_audio.mean()
    sa = source_audio - source_audio.mean()
    oa_std = oa.std()
    sa_std = sa.std()
    if oa_std < 1.0 or sa_std < 1.0:
        return None, 0.0  # silence — inconclusive

    oa = oa / oa_std
    sa = sa / sa_std

    # Use scipy if available, else numpy correlate
    try:
        from scipy.signal import fftconvolve
        corr = fftconvolve(sa, oa[::-1], mode='valid')
    except ImportError:
        corr = np.correlate(sa, oa, mode='valid')

    peak_idx = int(np.argmax(corr))
    peak_val = float(corr[peak_idx]) / len(oa)
    offset_s = peak_idx / sr
    return offset_s, peak_val


def _frame_similarity(frame_a, frame_b):
    """Structural similarity between two frames (0-1). Handles size mismatch."""
    if frame_a is None or frame_b is None:
        return None
    h, w = 320, 480  # compare at reduced resolution
    a = cv2.resize(frame_a, (w, h))
    b = cv2.resize(frame_b, (w, h))
    a_gray = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    b_gray = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # Normalized cross-correlation
    a_n = a_gray - a_gray.mean()
    b_n = b_gray - b_gray.mean()
    a_std = a_n.std()
    b_std = b_n.std()
    if a_std < 1.0 or b_std < 1.0:
        return None
    ncc = float(np.sum(a_n * b_n) / (a_std * b_std * a_n.size))
    return max(0.0, min(1.0, ncc))


def gate_g14(final_mp4, manifest_path, source_clips=None, tolerance_ms=40,
             qa_dir=None):
    """G14: audio-visual alignment (Amendment 1).

    For each talking_head segment, samples at joins and every <= 2s inside.
    Cross-correlates output audio against source to find matching source time.
    Compares frames. 40ms tolerance. Inconclusive = HOLD.

    source_clips: dict mapping clip label -> {"path": str, "cut_in": float}
                  or label -> str (path only, cut_in defaults to 0)
    Returns (pass: bool, details: list[dict]).
    """
    print("\n=== G14: AUDIO-VISUAL ALIGNMENT ===")

    with open(manifest_path) as f:
        manifest = json.load(f)

    segments = manifest["segments"]
    tol_s = tolerance_ms / 1000.0
    sr = 16000
    window_s = 0.5  # audio window for cross-correlation

    if qa_dir is None:
        qa_dir = os.path.dirname(manifest_path)

    # Normalize source_clips to {"path": ..., "cut_in": ...}
    if source_clips:
        norm = {}
        for k, v in source_clips.items():
            if isinstance(v, str):
                norm[k] = {"path": v, "cut_in": 0}
            elif isinstance(v, dict):
                norm[k] = v
            else:
                norm[k] = {"path": str(v), "cut_in": 0}
        source_clips = norm

    details = []
    all_pass = True
    has_hold = False

    for seg in segments:
        seg_type = seg.get("type", "")
        label = seg.get("label", "")
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start

        # Only check talking_head segments (clips with source audio)
        if seg_type != "talking_head":
            continue

        source_info = None
        if source_clips and label in source_clips:
            source_info = source_clips[label]
        elif source_clips:
            for k, v in source_clips.items():
                if k in label or label in k:
                    source_info = v
                    break

        source_path = source_info["path"] if source_info else None
        source_cut_in = source_info.get("cut_in", 0) if source_info else 0

        if source_path is None or not os.path.exists(str(source_path)):
            print(f"  HOLD: {label} — no source clip available for cross-correlation")
            details.append({
                "label": label, "status": "HOLD",
                "reason": "no source clip for cross-correlation",
            })
            has_hold = True
            continue

        # Determine sample points: start + every <= 2s + near end.
        # Avoid the last window_s at the end (may cross into next segment).
        sample_offsets = [0.2]  # inside the clip, past any transition
        step = min(2.0, seg_dur / 2)
        t = step
        while t < seg_dur - window_s - 0.1:
            sample_offsets.append(t)
            t += step
        if seg_dur > window_s + 0.5:
            sample_offsets.append(seg_dur - window_s - 0.1)  # near end but not crossing

        print(f"  {label}: {len(sample_offsets)} samples in {seg_dur:.2f}s")

        # Load source audio starting from cut_in with margin.
        # We load from cut_in - 1s to cut_in + seg_dur + 1s.
        src_margin = 1.0
        src_audio_start = max(0, source_cut_in - src_margin)
        src_audio_dur = seg_dur + 2 * src_margin
        src_audio = _extract_audio_mono(source_path, src_audio_start, src_audio_dur, sr)

        # Establish reference: use source_cut_in as the expected source
        # position for the segment start, then VALIDATE with xcorr.
        # This avoids false matches when xcorr peak is low (v12 clip_04 bug).
        ref_extract_start = seg_start + 0.05
        ref_out_audio = _extract_audio_mono(final_mp4, ref_extract_start, window_s, sr)
        ref_offset, ref_peak = _xcorr_offset(ref_out_audio, src_audio, sr)

        # The expected source time for ref_extract_start:
        # seg_start maps to source_cut_in, so seg_start+0.05 maps to source_cut_in+0.05
        expected_ref_src = source_cut_in + 0.05

        if ref_offset is not None and ref_peak >= 0.5:
            # High-confidence xcorr — use discovered offset but sanity-check
            discovered_ref_src = src_audio_start + ref_offset
            ref_discrepancy = abs(discovered_ref_src - expected_ref_src)
            if ref_discrepancy < 0.5:
                # xcorr agrees with cut_in — use xcorr result for precision
                ref_src_time = discovered_ref_src
                print(f"    Reference: output {ref_extract_start:.3f}s = source {ref_src_time:.3f}s "
                      f"(xcorr={ref_peak:.3f}, agrees with cut_in)")
            else:
                # xcorr diverges from cut_in despite high peak — trust cut_in, flag
                ref_src_time = expected_ref_src
                print(f"    Reference: output {ref_extract_start:.3f}s = source {ref_src_time:.3f}s "
                      f"(using cut_in; xcorr={ref_peak:.3f} found {discovered_ref_src:.3f}s, "
                      f"discrepancy={ref_discrepancy:.3f}s)")
        elif ref_offset is not None and ref_peak >= 0.3:
            # Low-confidence xcorr — trust cut_in instead of discovered offset
            ref_src_time = expected_ref_src
            print(f"    Reference: output {ref_extract_start:.3f}s = source {ref_src_time:.3f}s "
                  f"(using cut_in; xcorr low confidence peak={ref_peak:.3f})")
        else:
            # Very low or no xcorr — still use cut_in but flag as lower confidence
            if ref_peak < 0.1:
                print(f"    HOLD: {label} — cannot validate reference (peak={ref_peak:.3f}, silence?)")
                details.append({
                    "label": label, "status": "HOLD",
                    "reason": f"cannot validate reference (peak={ref_peak:.3f})",
                })
                has_hold = True
                continue
            ref_src_time = expected_ref_src
            print(f"    Reference: output {ref_extract_start:.3f}s = source {ref_src_time:.3f}s "
                  f"(using cut_in; xcorr marginal peak={ref_peak:.3f})")

        for offset in sample_offsets:
            out_time = seg_start + offset
            # Extract from the same position style (start of window, not centered)
            # to maintain consistent offset measurement with the reference.
            extract_start = out_time
            out_audio = _extract_audio_mono(final_mp4, extract_start, window_s, sr)

            xcorr_off, xcorr_peak = _xcorr_offset(out_audio, src_audio, sr)

            entry = {
                "label": label,
                "output_time": round(out_time, 3),
                "status": "HOLD",
            }

            if xcorr_off is None or xcorr_peak < 0.3:
                entry["reason"] = f"inconclusive xcorr (peak={xcorr_peak:.3f})"
                has_hold = True
                print(f"    HOLD: t={out_time:.3f}s — inconclusive (peak={xcorr_peak:.3f})")
            else:
                matched_src_time = src_audio_start + xcorr_off
                # Expected: ref_src_time shifted by the difference in extraction starts
                expected_src_time = ref_src_time + (extract_start - ref_extract_start)
                delta_s = abs(matched_src_time - expected_src_time)
                delta_ms_val = delta_s * 1000

                entry["matched_src_s"] = round(matched_src_time, 3)
                entry["expected_src_s"] = round(expected_src_time, 3)
                entry["delta_ms"] = round(delta_ms_val, 1)
                entry["xcorr_peak"] = round(xcorr_peak, 4)

                if delta_ms_val <= tolerance_ms:
                    # Audio aligned — now verify frame matches.
                    # Extract output frame at out_time and source frame at matched_src_time.
                    out_frame_path = os.path.join(qa_dir, "g14_out_frame.png")
                    src_frame_path = os.path.join(qa_dir, "g14_src_frame.png")
                    out_frame = _extract_frame(final_mp4, out_time, out_frame_path)
                    src_frame = _extract_frame(source_path, matched_src_time, src_frame_path)
                    sim = _frame_similarity(out_frame, src_frame)
                    entry["frame_sim"] = round(sim, 3) if sim is not None else None

                    # Frame similarity > 0.3 means the pictures match
                    # (threshold accounts for layout transforms, overlays, blurs)
                    if sim is not None and sim >= 0.3:
                        entry["status"] = "PASS"
                        print(f"    PASS: t={out_time:.3f}s -> src={matched_src_time:.3f}s "
                              f"(audio_delta={delta_ms_val:.1f}ms, frame_sim={sim:.3f})")
                    elif sim is not None and sim < 0.3:
                        entry["status"] = "FAIL"
                        entry["reason"] = f"audio aligned but frame mismatch (sim={sim:.3f})"
                        all_pass = False
                        print(f"    FAIL: t={out_time:.3f}s frame mismatch "
                              f"(audio ok, frame_sim={sim:.3f} < 0.3)")
                    else:
                        entry["status"] = "HOLD"
                        entry["reason"] = "frame comparison inconclusive"
                        has_hold = True
                        print(f"    HOLD: t={out_time:.3f}s — frame comparison inconclusive")
                else:
                    entry["status"] = "FAIL"
                    all_pass = False
                    print(f"    FAIL: t={out_time:.3f}s -> src={matched_src_time:.3f}s "
                          f"(expected={expected_src_time:.3f}s, delta={delta_ms_val:.1f}ms, "
                          f"xcorr={xcorr_peak:.3f})")

            details.append(entry)

    # VO segments get declared pre-roll — just verify they exist at the right time
    for seg in segments:
        if seg.get("type") == "vo":
            print(f"  {seg['label']}: VO pre-roll declared (no source cross-correlation)")
            details.append({
                "label": seg["label"], "status": "PASS",
                "reason": "VO pre-roll declared",
            })

    status = "FAIL" if not all_pass else ("HOLD" if has_hold else "PASS")
    print(f"\n  G14 {status}")
    return all_pass and not has_hold, details


def gate_g14c(mp4_16, mp4_9, tolerance_ms=42):
    """G14c: duration parity — |dur_16 - dur_9| <= tolerance_ms."""
    print("\n=== G14c: DURATION PARITY ===")
    dur_16 = _get_duration(mp4_16)
    dur_9 = _get_duration(mp4_9)
    delta_ms = abs(dur_16 - dur_9) * 1000
    ok = delta_ms <= tolerance_ms
    print(f"  16:9 = {dur_16:.3f}s, 9:16 = {dur_9:.3f}s, delta = {delta_ms:.1f}ms (limit: {tolerance_ms}ms)")
    print(f"  G14c {'PASS' if ok else 'FAIL'}")
    return ok, {"dur_16": dur_16, "dur_9": dur_9, "delta_ms": round(delta_ms, 1)}


# ── G15: CREDITS CONTINUOUS + RING ASPECT ──

def gate_g15(final_mp4, segments, qa_dir, channels=None):
    """G15: the shoutout card must play once (no mid-card scene change)
    and visible avatar rings must have aspect ratio 0.95-1.05 (catches squished cards).
    DEC-11: rings measured on the brand-red ring mask; `channels` (the credited channels in card order)
    also checks that each disc is that channel's registered avatar.

    Returns (pass: bool, details: dict).
    """
    print("\n=== G15: CREDITS CONTINUOUS + RING ASPECT ===")

    # Find shoutout segment boundaries
    shoutout_seg = None
    for seg in segments:
        if seg.get("type") == "shoutout" or seg.get("label") == "shoutout":
            shoutout_seg = seg
            break

    if not shoutout_seg:
        print("  SKIP: no shoutout segment in manifest")
        return True, {"skip": True}

    start = shoutout_seg["start"]
    end = shoutout_seg["end"]
    dur = end - start
    print(f"  Shoutout: {start:.3f}s - {end:.3f}s ({dur:.2f}s)")

    # Part 1: Check for mid-card scene changes.
    # Skip the first 0.3s (node entry animation) and the last 0.5s (fade to black).
    # Use lower threshold (0.15) to catch cross-aspect card insertion.
    check_start = start + 0.3
    check_dur = dur - 0.8
    if check_dur < 0.5:
        check_dur = dur * 0.6  # at least check 60% of the card

    r = subprocess.run([
        "ffmpeg", "-ss", str(check_start), "-t", str(check_dur),
        "-i", final_mp4,
        "-vf", "select='gt(scene,0.15)',showinfo",
        "-vsync", "vfr", "-f", "null", "-",
    ], capture_output=True, text=True, timeout=60)

    mid_scene_changes = []
    for line in r.stderr.split("\n"):
        if "pts_time:" in line:
            for token in line.split():
                if token.startswith("pts_time:"):
                    mid_scene_changes.append(float(token.split(":")[1]))

    card_continuous = len(mid_scene_changes) == 0
    if not card_continuous:
        print(f"  FAIL: {len(mid_scene_changes)} mid-card scene change(s) "
              f"(threshold=0.15, window={check_start:.1f}-{check_start+check_dur:.1f}s)")
    else:
        print(f"  Card continuous: OK (no mid-card scene changes)")

    # Part 2 (DEC-11, 2026-11-11): the rings the renderer draws, not a circle search over avatar artwork.
    # Each ring = the brand-red mask's external contour of ring size (pipeline/credit_rings.py); the ellipse
    # is fitted to that mask, aspect tolerance unchanged (>= 0.95). With the credited channels known, each
    # disc inside a ring must be that channel's registered avatar (D4: yesterday's rings were round, the
    # squashed thumbnails inside them were the defect). No ring found = FAIL (fail closed).
    import credit_rings as CR
    ring_aspect_ok = True
    avatar_ok = True
    ring_details, avatar_details = [], []

    for pct in [0.25, 0.50, 0.75, 0.90]:
        ts = start + dur * pct
        frame_path = os.path.join(qa_dir, f"g15_frame_{pct:.0f}.png")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", final_mp4,
            "-vframes", "1", "-q:v", "2", frame_path,
        ], capture_output=True, timeout=15)

        if not os.path.exists(frame_path):
            ring_aspect_ok = False
            print(f"  FAIL: no frame at {ts:.2f}s")
            continue
        img = cv2.imread(frame_path)
        os.unlink(frame_path)
        if img is None:
            ring_aspect_ok = False
            continue

        count, aspect_ok, _, rings = CR.check_card(img)
        for r in rings:
            ring_details.append({"pct": pct, **r})
        if not aspect_ok:
            ring_aspect_ok = False
            bad = [r for r in rings if r["aspect"] < CR.ASPECT_MIN]
            print(f"  FAIL at {pct:.0%}: " + ("no brand-red ring found" if not rings else
                  "; ".join(f"ring at ({r['cx']:.0f},{r['cy']:.0f}) aspect={r['aspect']:.3f} axes {r['axes']}"
                            for r in bad)))
        discs = CR.disc_matches(img, channels or [])
        if not channels or len(discs) != len(channels):    # fail closed: credited channels unknown or unmeasured
            avatar_ok = False
            print(f"  FAIL at {pct:.0%}: credited channels {'unknown' if not channels else 'not all measured'}")
        for d in discs:
            avatar_details.append({"pct": pct, **d})
            if d["r"] is None or d["r"] < CR.AVATAR_R_MIN:
                avatar_ok = False
                print(f"  FAIL at {pct:.0%}: the disc for {d['channel']} is not its registered avatar "
                      f"(r={d['r']}, min {CR.AVATAR_R_MIN})")

    if ring_aspect_ok:
        print(f"  Ring aspects: OK ({len(ring_details)} rings checked)")

    all_pass = card_continuous and ring_aspect_ok and avatar_ok
    print(f"\n  G15 {'PASS' if all_pass else 'FAIL'}")
    return all_pass, {
        "card_continuous": card_continuous,
        "mid_scene_changes": mid_scene_changes,
        "ring_aspect_ok": ring_aspect_ok,
        "rings": ring_details,
        "avatar_ok": avatar_ok,
        "avatars": avatar_details,
        "method": "DEC-11 ring mask + registered-avatar disc",
    }


def run_gates(segment_dir, final_mp4, manifest_path, qa_version=None,
              source_clips=None, vo_assembled_tracks=None):
    """Run all QA gates. Returns (all_pass, results_dict)."""
    paths = resolve_paths(segment_dir, qa_version)

    # Dynamically patch the frozen qa_gates module's BASE and VO_DIR
    sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
    import qa_gates
    qa_gates.BASE = segment_dir
    qa_gates.VO_DIR = paths["vo_dir"]

    qa_dir = paths["qa_dir"]

    # Load assembled VO tracks if path provided
    if vo_assembled_tracks is None:
        vo_tracks_path = os.path.join(qa_dir, "vo_assembled_tracks.json")
        if os.path.exists(vo_tracks_path):
            with open(vo_tracks_path) as f:
                vo_assembled_tracks = json.load(f)

    # Resolve EDL and channels registry for G10 chyron gate
    edl_path = os.path.join(segment_dir, "edl.json")
    channels_json_path = os.path.join(os.path.dirname(__file__), "channels.json")
    if not os.path.exists(edl_path):
        edl_path = None
    if not os.path.exists(channels_json_path):
        channels_json_path = None

    return qa_gates.run_all_gates(
        final_mp4, manifest_path, qa_dir,
        source_clips=source_clips,
        vo_assembled_tracks=vo_assembled_tracks,
        edl_path=edl_path,
        channels_json_path=channels_json_path,
    )


def main():
    p = argparse.ArgumentParser(description="Parameterised QA gate runner")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--final", required=True, help="Final mp4 to test")
    p.add_argument("--manifest", required=True, help="Concat manifest JSON")
    p.add_argument("--qa-version", type=int, default=None)
    p.add_argument("--source-clip", action="append", default=[],
                   help="label:path pairs for G4 source layout classification")
    p.add_argument("--vo-track", action="append", default=[],
                   help="label:path pairs for assembled VO tracks")
    args = p.parse_args()

    source_clips = {}
    for sc in args.source_clip:
        parts = sc.split(":", 1)
        if len(parts) == 2:
            source_clips[parts[0]] = parts[1]

    vo_tracks = {}
    for vt in args.vo_track:
        parts = vt.split(":", 1)
        if len(parts) == 2:
            vo_tracks[parts[0]] = parts[1]

    ok, results = run_gates(
        args.segment, args.final, args.manifest, args.qa_version,
        source_clips=source_clips or None,
        vo_assembled_tracks=vo_tracks or None,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
