#!/usr/bin/env python3
"""Clean transitions between segments. No star wipes. No cheap effects.

Provides crossfade (dissolve) transitions for broadcast-standard video.
Default: 0.5s crossfade. All transitions produce valid 1920x1080 30fps MP4.

Usage:
    from transitions import apply_crossfade, apply_transitions
"""

import logging
import os
import subprocess

log = logging.getLogger("transitions")

BASE = os.path.dirname(os.path.abspath(__file__))


def _ffprobe_duration(path: str) -> float:
    """Get duration of a media file via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip()) if r.stdout.strip() else 0.0
    except (subprocess.TimeoutExpired, ValueError):
        return 0.0


def apply_crossfade(clip1: str, clip2: str, output_path: str,
                    duration: float = 0.5,
                    transition: str = "fade") -> str:
    """Apply crossfade between two video segments.

    Both inputs are normalized to 1920x1080 30fps before the xfade filter.
    Audio uses acrossfade with triangular curve for smooth blending.

    Args:
        clip1: Path to first video segment.
        clip2: Path to second video segment.
        output_path: Where to write the crossfaded result.
        duration: Crossfade duration in seconds. Default 0.5s.
        transition: xfade transition type (fade, slideleft, etc).

    Returns:
        output_path on success, empty string on failure.
    """
    if not (os.path.exists(clip1) and os.path.exists(clip2)):
        return ""

    dur1 = _ffprobe_duration(clip1)
    if dur1 <= duration:
        log.warning("apply_crossfade: clip1 too short (%.1fs <= %.1fs)", dur1, duration)
        return ""

    offset = max(0, dur1 - duration)

    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-i", clip1, "-i", clip2,
            "-filter_complex",
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,fps=30[v0];"
            f"[1:v]scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,fps=30[v1];"
            f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a0];"
            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a1];"
            f"[v0][v1]xfade=transition={transition}:duration={duration}:"
            f"offset={offset},format=yuv420p[outv];"
            f"[a0][a1]acrossfade=d={duration}:c1=tri:c2=tri[outa]",
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        log.warning("apply_crossfade: timeout")
        return ""

    if r.returncode == 0 and os.path.exists(output_path):
        return output_path
    return ""


def apply_transitions(segment_paths: list, work_dir: str,
                      transition_type: str = "fade",
                      duration: float = 0.5) -> list:
    """Apply crossfade transitions between a list of pre-rendered segments.

    Merges consecutive pairs with short crossfades. On failure for any pair,
    falls back to hard cut (keeps both segments separate).

    Args:
        segment_paths: List of paths to segment MP4 files.
        work_dir: Directory for intermediate files.
        transition_type: xfade transition name. Default "fade" (dissolve).
        duration: Crossfade duration in seconds. Default 0.5s.

    Returns:
        List of output segment paths (may be fewer than input if merges succeed).
    """
    if len(segment_paths) < 2:
        return list(segment_paths)

    os.makedirs(work_dir, exist_ok=True)
    output_parts = [segment_paths[0]]

    for i in range(1, len(segment_paths)):
        prev = output_parts[-1]
        seg = segment_paths[i]

        if not (prev and os.path.exists(prev) and seg and os.path.exists(seg)):
            output_parts.append(seg)
            continue

        merged = os.path.join(work_dir, f"xfade_{i}.mp4")
        result = apply_crossfade(prev, seg, merged,
                                 duration=duration,
                                 transition=transition_type)
        if result:
            output_parts[-1] = result
            log.info("transition: crossfade %d→%d (%.1fs %s)",
                     i - 1, i, duration, transition_type)
        else:
            # Fallback: hard cut (no transition)
            output_parts.append(seg)
            log.info("transition: hard cut %d→%d (crossfade failed)", i - 1, i)

    return output_parts
