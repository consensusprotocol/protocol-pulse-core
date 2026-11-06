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


# ── G14: SCENE-CHANGE ALIGNMENT ──

def gate_g14(final_mp4, manifest_path, tolerance_ms=42):
    """G14: verify scene changes in the output align with the concat manifest.

    For each talking_head→vo or vo→talking_head transition, a visual scene
    change must occur within *tolerance_ms* of the manifest boundary.
    Also checks parity: |dur_16 - dur_9| <= tolerance_ms when both manifests
    are available.

    Returns (pass: bool, details: list[dict]).
    """
    print("\n=== G14: SCENE-CHANGE ALIGNMENT ===")

    with open(manifest_path) as f:
        manifest = json.load(f)

    segments = manifest["segments"]
    fmt = manifest.get("format", "16x9")
    tol_s = tolerance_ms / 1000.0

    # Detect scene changes in the final output
    r = subprocess.run([
        "ffmpeg", "-i", final_mp4,
        "-vf", "select='gt(scene,0.25)',showinfo",
        "-vsync", "vfr", "-f", "null", "-",
    ], capture_output=True, text=True, timeout=120)

    scene_times = []
    for line in r.stderr.split("\n"):
        if "pts_time:" in line:
            for token in line.split():
                if token.startswith("pts_time:"):
                    scene_times.append(float(token.split(":")[1]))

    print(f"  Detected {len(scene_times)} scene changes: {[f'{t:.3f}' for t in scene_times]}")

    # Expected transition boundaries: where a VISUAL scene change should occur.
    # VO segments use a blurred freeze of the preceding clip, so:
    #   talking_head -> vo: NO scene change (blur of same frame)
    #   vo -> talking_head: YES (new clip appears)
    #   talking_head -> talking_head: YES (different source)
    #   anything -> shoutout: YES
    #   shoutout -> outro: YES (but outro fade may be gradual)
    expected_boundaries = []
    for i in range(1, len(segments)):
        prev_type = segments[i - 1]["type"]
        curr_type = segments[i]["type"]
        # Skip talking_head -> vo (visually continuous due to blur)
        if prev_type == "talking_head" and curr_type == "vo":
            continue
        boundary = segments[i]["start"]
        expected_boundaries.append({
            "time": boundary,
            "from": segments[i - 1]["label"],
            "to": segments[i]["label"],
        })

    print(f"  Expected {len(expected_boundaries)} boundaries")

    details = []
    all_pass = True

    for eb in expected_boundaries:
        t = eb["time"]
        # Find closest scene change
        closest = None
        closest_delta = float("inf")
        for sc in scene_times:
            delta = abs(sc - t)
            if delta < closest_delta:
                closest = sc
                closest_delta = delta

        # Shoutout -> outro has a fade (0.4s black), so scene detection is unreliable there.
        # Mark as advisory, not blocking.
        is_fade = "shoutout" in eb["from"] and "outro" in eb["to"]
        ok = closest_delta <= tol_s if closest is not None else False
        entry = {
            "boundary": f"{eb['from']}->{eb['to']}",
            "expected_s": round(t, 3),
            "detected_s": round(closest, 3) if closest is not None else None,
            "delta_ms": round(closest_delta * 1000, 1) if closest is not None else None,
            "pass": ok,
            "advisory": is_fade,
        }
        details.append(entry)
        status = "PASS" if ok else ("ADVISORY" if is_fade else "FAIL")
        det_str = f"{closest:.3f}" if closest is not None else "none"
        delta_str = f"{closest_delta * 1000:.1f}ms" if closest is not None else "N/A"
        print(f"  {status}: {eb['from']}->{eb['to']}  expect={t:.3f}  detect={det_str}  delta={delta_str}")

        if not ok and not is_fade:
            all_pass = False

    print(f"\n  G14 {'PASS' if all_pass else 'FAIL'}")
    return all_pass, details


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

def gate_g15(final_mp4, segments, qa_dir):
    """G15: the shoutout card must play once (no mid-card scene change)
    and visible avatar rings must have aspect ratio 0.95-1.05 (catches squished cards).

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

    # Part 2: Check avatar ring aspect ratios
    # Sample 3 frames from the shoutout at 25%, 50%, 75%
    ring_aspect_ok = True
    ring_details = []

    for pct in [0.25, 0.50, 0.75, 0.90]:
        ts = start + dur * pct
        frame_path = os.path.join(qa_dir, f"g15_frame_{pct:.0f}.png")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", final_mp4,
            "-vframes", "1", "-q:v", "2", frame_path,
        ], capture_output=True, timeout=15)

        if not os.path.exists(frame_path):
            continue

        # Detect circles using HoughCircles on grayscale
        img = cv2.imread(frame_path)
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape

        # Edge detect for ellipse finding
        edges = cv2.Canny(gray, 50, 150)

        # Find contours that could be avatar rings
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            if len(cnt) < 30:
                continue
            # Fit ellipse
            ellipse = cv2.fitEllipse(cnt)
            (cx, cy), (axis_a, axis_b), angle = ellipse

            # Filter: must be reasonably large (avatar-sized) and roughly circular
            min_axis = min(axis_a, axis_b)
            max_axis = max(axis_a, axis_b)
            if min_axis < 40 or max_axis > h_img * 0.6:
                continue

            aspect = min_axis / max_axis if max_axis > 0 else 0
            # Only check ellipses that are roughly avatar-ring-sized
            if max_axis > 80 and min_axis > 60:
                ring_details.append({
                    "pct": pct, "cx": round(cx), "cy": round(cy),
                    "axes": (round(axis_a, 1), round(axis_b, 1)),
                    "aspect": round(aspect, 3),
                })
                if aspect < 0.95:
                    ring_aspect_ok = False
                    print(f"  FAIL: ring at ({cx:.0f},{cy:.0f}) aspect={aspect:.3f} "
                          f"(axes {axis_a:.0f}x{axis_b:.0f}) — squished")

        # Clean up frame
        os.unlink(frame_path)

    if ring_aspect_ok:
        print(f"  Ring aspects: OK ({len(ring_details)} rings checked)")

    all_pass = card_continuous and ring_aspect_ok
    print(f"\n  G15 {'PASS' if all_pass else 'FAIL'}")
    return all_pass, {
        "card_continuous": card_continuous,
        "mid_scene_changes": mid_scene_changes,
        "ring_aspect_ok": ring_aspect_ok,
        "rings": ring_details,
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
