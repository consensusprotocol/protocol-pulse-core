#!/usr/bin/env python3
"""Broadcast-standard audio mastering for Protocol Pulse episodes.

Handles LUFS measurement, per-segment normalization, music ducking via
sidechain compression, and final limiting. Target: EBU R128 broadcast
standard (-14 LUFS integrated, -1.0 dBTP).

Usage:
    from audio_master import master_audio, normalize_segment, get_lufs
"""

import json
import logging
import os
import subprocess

log = logging.getLogger("audio_master")


def get_lufs(audio_path: str) -> float:
    """Measure integrated loudness (LUFS) of an audio/video file.

    Uses ffmpeg loudnorm filter in measurement-only mode (two-pass approach).

    Args:
        audio_path: Path to audio or video file.

    Returns:
        Integrated loudness in LUFS (negative float). Returns -24.0 on error.
    """
    if not os.path.exists(audio_path):
        log.warning("get_lufs: file not found: %s", audio_path)
        return -24.0

    cmd = [
        "ffmpeg", "-i", audio_path, "-af",
        "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        log.warning("get_lufs: timeout on %s", audio_path)
        return -24.0

    # Parse the JSON output block from loudnorm's stderr
    lines = result.stderr.split("\n")
    json_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_start = i
            break

    if json_start is not None:
        json_block = "\n".join(lines[json_start:])
        # Find the closing brace
        brace_depth = 0
        end_idx = 0
        for ci, ch in enumerate(json_block):
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    end_idx = ci + 1
                    break
        if end_idx > 0:
            try:
                data = json.loads(json_block[:end_idx])
                return float(data.get("input_i", -24))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

    return -24.0


def normalize_segment(segment_path: str, target_lufs: float = -16) -> None:
    """Normalize a single segment to target LUFS (in-place).

    Skips normalization if current loudness is within 0.5 LUFS of target.
    Video stream is copied (not re-encoded).

    Args:
        segment_path: Path to video/audio segment (modified in-place).
        target_lufs: Target integrated loudness. Default -16 LUFS.
    """
    if not os.path.exists(segment_path):
        return

    current = get_lufs(segment_path)
    if abs(current - target_lufs) < 0.5:
        log.info("normalize_segment: %s already at %.1f LUFS (target %.1f)",
                 os.path.basename(segment_path), current, target_lufs)
        return

    output = segment_path + ".norm.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", segment_path,
            "-af", f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11",
            "-c:v", "copy",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            output,
        ], capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        log.warning("normalize_segment: timeout on %s", segment_path)
        if os.path.exists(output):
            os.remove(output)
        return

    if os.path.exists(output) and os.path.getsize(output) > 1000:
        os.replace(output, segment_path)
        log.info("normalize_segment: %s → %.1f LUFS (was %.1f)",
                 os.path.basename(segment_path), target_lufs, current)
    else:
        if os.path.exists(output):
            os.remove(output)


def master_audio(video_path: str, music_bed: str = None, **kwargs) -> bool:
    """Final audio mastering pass on assembled video.

    Pipeline:
      1. If music_bed provided: mix with sidechain ducking (voice priority)
      2. Normalize to -14 LUFS (EBU R128 broadcast standard)
      3. True peak limiting at -1.0 dBTP

    Args:
        video_path: Path to video file (modified in-place on success).
        music_bed: Optional path to background music file.

    Returns:
        True if mastering succeeded.
    """
    if not os.path.exists(video_path):
        log.error("master_audio: file not found: %s", video_path)
        return False

    if music_bed and os.path.exists(music_bed):
        output = video_path + ".mastered.mp4"
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", video_path,
                "-stream_loop", "-1", "-i", music_bed,
                "-filter_complex",
                # Music at low volume, sidechain compress against voice
                "[1:a]volume=0.08,aloop=loop=-1:size=2e9[music];"
                "[0:a][music]sidechaincompress="
                "threshold=0.08:ratio=16:attack=5:release=200[mixed];"
                # Final loudnorm to broadcast standard
                "[mixed]loudnorm=I=-14:TP=-1.0:LRA=11[final]",
                "-map", "0:v", "-map", "[final]",
                "-c:v", "copy",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                "-shortest",
                output,
            ], capture_output=True, timeout=300)
        except subprocess.TimeoutExpired:
            log.warning("master_audio: timeout during music mix")
            if os.path.exists(output):
                os.remove(output)
            return False

        if os.path.exists(output) and os.path.getsize(output) > 1000:
            os.replace(output, video_path)
            log.info("master_audio: mastered with music bed + sidechain ducking")
            return True
        else:
            if os.path.exists(output):
                os.remove(output)
            log.warning("master_audio: music mix failed, falling back to normalize-only")

    # No music or music mix failed — just normalize
    output = video_path + ".norm.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-af", "loudnorm=I=-14:TP=-1.0:LRA=11",
            "-c:v", "copy",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            output,
        ], capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        log.warning("master_audio: timeout during normalize")
        if os.path.exists(output):
            os.remove(output)
        return False

    if os.path.exists(output) and os.path.getsize(output) > 1000:
        os.replace(output, video_path)
        log.info("master_audio: normalized to -14 LUFS")
        return True

    if os.path.exists(output):
        os.remove(output)
    return False
