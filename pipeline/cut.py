#!/usr/bin/env python3
"""pipeline/cut.py — K3 stage: compute acoustic cut points via M19a valley rule.

For every clip in edl.json:
  1. Load word-level transcript from transcripts/<video_id>.json
  2. Call acoustic.compute_acoustic_cut_out() for the valley-rule cut point
  3. Compute cut_in (first_word start - 0.05s, M19 20ms fade-in)
  4. Write cuts_final.json with verified=true

Renderers refuse cuts without verified=true.
"""
import json
import os
import sys
import time

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)


def compute_all_cuts(run_dir):
    """Compute acoustic cut points for all clips in edl.json.

    Writes cuts_final.json. Returns True on success.
    """
    t0 = time.time()
    print(f"\n=== CUT: M19a valley rule ===")

    from acoustic import compute_acoustic_cut_out

    edl_path = os.path.join(run_dir, "edl.json")
    with open(edl_path) as f:
        edl = json.load(f)

    sources_dir = os.path.join(run_dir, "sources")
    cuts = []

    # Process hook + clips
    segments = []
    hook = edl.get("hook")
    if hook:
        segments.append(("hook", hook))
    for clip in edl.get("clips", []):
        segments.append((f"clip_{clip['index']:02d}", clip))

    for label, seg in segments:
        video_id = seg["video_id"]
        source_path = os.path.join(sources_dir, f"{video_id}.mp4")
        if not os.path.exists(source_path):
            print(f"  {label}: source not found — SKIP")
            cuts.append({
                "clip_id": label,
                "video_id": video_id,
                "verified": False,
                "error": "source not found",
            })
            continue

        word_end = seg.get("word_end", seg.get("end", 0))
        word_start = seg.get("word_start", seg.get("start", 0))

        # M19a: acoustic cut-out via valley rule
        try:
            result = compute_acoustic_cut_out(source_path, word_end)
            cut_out = result["cut_out"]
            safe = result["safe"]
            valley = result.get("valley")
        except Exception as e:
            print(f"  {label}: acoustic analysis failed: {e}")
            cut_out = word_end + 0.15  # Fallback: 150ms after last word
            safe = False
            valley = None

        # M19: cut_in = first word start - 0.05s (20ms fade-in)
        cut_in = max(0, word_start - 0.05)
        cut_duration = round(cut_out - cut_in, 3)

        # M19: 30ms fade-out
        fade_out_ms = 30

        cut_entry = {
            "clip_id": label,
            "video_id": video_id,
            "channel": seg.get("channel", ""),
            "cut_in": round(cut_in, 3),
            "cut_out": round(cut_out, 3),
            "cut_duration": cut_duration,
            "fade_out_ms": fade_out_ms,
            "fade_in_ms": 20,
            "last_word_expected": seg.get("last_word", ""),
            "first_word_expected": seg.get("first_word", ""),
            "verified": safe,
        }

        if valley:
            cut_entry["acoustic_valley_centre"] = valley.get("centre")
            cut_entry["acoustic_valley_end"] = valley.get("end")
            cut_entry["acoustic_valley_depth_db"] = valley.get("depth_db")
            cut_entry["acoustic_valley_width_ms"] = valley.get("width_ms")

        if result.get("onset"):
            cut_entry["acoustic_onset"] = result["onset"]
        if result.get("speech_median_db"):
            cut_entry["speech_median_db"] = result["speech_median_db"]

        tag = "SAFE" if safe else "UNSAFE"
        print(f"  {label}: in={cut_in:.3f} out={cut_out:.3f} dur={cut_duration:.2f}s [{tag}]")
        cuts.append(cut_entry)

    # Update edl.json with cut_out values
    if hook and cuts:
        hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
        if hook_cut:
            hook["cut_out"] = hook_cut["cut_out"]
            hook["fade_out_ms"] = hook_cut["fade_out_ms"]
    for clip in edl.get("clips", []):
        clip_cut = next((c for c in cuts if c["clip_id"] == f"clip_{clip['index']:02d}"), None)
        if clip_cut:
            clip["cut_out"] = clip_cut["cut_out"]
            clip["fade_out_ms"] = clip_cut["fade_out_ms"]
            if clip_cut.get("acoustic_valley_centre"):
                clip["acoustic_valley_centre"] = clip_cut["acoustic_valley_centre"]
                clip["acoustic_valley_end"] = clip_cut["acoustic_valley_end"]
                clip["acoustic_valley_depth_db"] = clip_cut["acoustic_valley_depth_db"]
                clip["acoustic_valley_width_ms"] = clip_cut["acoustic_valley_width_ms"]
            if clip_cut.get("acoustic_onset"):
                clip["acoustic_onset"] = clip_cut["acoustic_onset"]

    # Write updated EDL
    with open(edl_path, "w") as f:
        json.dump(edl, f, indent=2)

    # Write cuts_final.json
    cuts_path = os.path.join(run_dir, "cuts_final.json")
    with open(cuts_path, "w") as f:
        json.dump(cuts, f, indent=2)

    # Check all verified
    all_verified = all(c.get("verified", False) for c in cuts)
    if not all_verified:
        unverified = [c["clip_id"] for c in cuts if not c.get("verified", False)]
        print(f"  WARNING: {len(unverified)} unverified cuts: {unverified}")

    elapsed = time.time() - t0
    print(f"  Cut time: {elapsed:.1f}s")
    return True
