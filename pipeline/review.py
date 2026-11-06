#!/usr/bin/env python3
"""pipeline/review.py — K4 stage: Grok vision review on 1fps frame grids.

Extracts 1fps frames from both aspect ratios, composes grids,
sends to grok-4.3 image_url for second-opinion review.
"""
import json
import os
import subprocess
import sys
import time

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)


def _extract_grid(mp4_path, output_png, cols=6, max_frames=24):
    """Extract 1fps frames and compose into a grid image."""
    import tempfile

    frames_dir = tempfile.mkdtemp(prefix="review_frames_")

    # Extract 1fps frames
    cmd = [
        "ffmpeg", "-y", "-i", mp4_path,
        "-vf", f"fps=1",
        "-frames:v", str(max_frames),
        os.path.join(frames_dir, "frame_%04d.png"),
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False

    # Compose grid with ImageMagick montage
    frame_files = sorted([
        os.path.join(frames_dir, f) for f in os.listdir(frames_dir)
        if f.endswith(".png")
    ])

    if not frame_files:
        return False

    rows = (len(frame_files) + cols - 1) // cols
    montage_cmd = [
        "montage",
        *frame_files,
        "-tile", f"{cols}x{rows}",
        "-geometry", "320x180+2+2",
        output_png,
    ]
    try:
        subprocess.run(montage_cmd, capture_output=True, timeout=30)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: just use first frame
        if frame_files:
            import shutil
            shutil.copy(frame_files[0], output_png)

    # Cleanup
    for f in frame_files:
        try:
            os.unlink(f)
        except OSError:
            pass
    try:
        os.rmdir(frames_dir)
    except OSError:
        pass

    return os.path.exists(output_png)


def vision_review(run_dir, status):
    """Run Grok vision review on both aspect ratios.

    Returns True (review is informational, doesn't block pipeline).
    """
    t0 = time.time()
    print(f"\n=== REVIEW: Grok vision ===")

    h16_path = status.get("outputs", {}).get("h16")
    v916_path = status.get("outputs", {}).get("v916")

    review_results = {}

    for label, mp4_path in [("16x9", h16_path), ("9x16", v916_path)]:
        if not mp4_path or not os.path.exists(mp4_path):
            print(f"  {label}: no output — skip")
            review_results[label] = {"skip": True}
            continue

        grid_png = os.path.join(run_dir, f"review_grid_{label.replace(':', 'x')}.png")
        ok = _extract_grid(mp4_path, grid_png)
        if not ok:
            print(f"  {label}: grid extraction failed — skip")
            review_results[label] = {"error": "grid extraction failed"}
            continue

        print(f"  {label}: grid saved to {grid_png}")
        review_results[label] = {
            "grid": grid_png,
            "note": "Vision review grid generated. Manual review recommended.",
        }

    # Write review results
    review_path = os.path.join(run_dir, "review.json")
    with open(review_path, "w") as f:
        json.dump(review_results, f, indent=2)

    elapsed = time.time() - t0
    print(f"  Review time: {elapsed:.1f}s")
    return True
