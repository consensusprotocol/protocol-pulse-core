#!/usr/bin/env python3
"""Protocol Pulse branded lower thirds.

Renders lower third overlays as standalone video files or FFmpeg filter strings.
Style: Red accent bar (4px) on left, dark glass background, white text.

Brand colors match PIPELINE_LAWS:
  - Red accent: #CC2222
  - Dark bg: #0A0A0F
  - Gold (eyebrow): #F5A623
  - White text: #F4F5F8

Usage:
    from lower_thirds import render_lower_third, lower_third_filter
"""

import logging
import os
import subprocess

log = logging.getLogger("lower_thirds")

# Brand colors (PIPELINE_LAWS gospel)
PP_RED = "0xCC2222"
PP_DARK = "0x0A0A0F"
PP_GOLD = "0xF5A623"
PP_WHITE = "0xF4F5F8"
PP_MUTED = "0x888888"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _sanitize(text: str) -> str:
    """Remove special characters that break FFmpeg drawtext."""
    return (text
            .replace("'", "\u2019")
            .replace(":", "\\:")
            .replace("%", "%%")
            .replace("\\", "/")
            .replace("\n", " ")
            .strip())


def lower_third_filter(text: str, subtitle: str = "",
                       y_offset: int = 880,
                       show_start: float = 0.5,
                       show_end: float = 0.0,
                       width: int = 800) -> str:
    """Generate FFmpeg drawtext filter string for a lower third overlay.

    Returns a filter string (no brackets/labels) that can be inserted into
    a larger filter_complex chain. Caller must add [input]/[output] labels.

    Args:
        text: Main text line (channel name, topic, etc).
        subtitle: Secondary text in gold (optional).
        y_offset: Top edge Y position of the lower third box. Default 880.
        show_start: Time to start showing the lower third.
        show_end: Time to stop showing (0 = show until end).
        width: Box width in pixels. Default 800.

    Returns:
        FFmpeg filter string (drawbox + drawtext chain).
    """
    safe_text = _sanitize(text)[:80]
    safe_sub = _sanitize(subtitle)[:60]

    enable = f"enable='gte(t,{show_start})'" if show_end <= 0 else (
        f"enable='between(t,{show_start},{show_end})'")

    parts = [
        # Dark glass background
        f"drawbox=x=40:y={y_offset}:w={width}:h=100:"
        f"color={PP_DARK}@0.85:t=fill:{enable}",
        # Red accent bar (left edge)
        f"drawbox=x=40:y={y_offset}:w=4:h=100:"
        f"color={PP_RED}@1.0:t=fill:{enable}",
        # Main text
        f"drawtext=fontfile={FONT_BOLD}:"
        f"text='{safe_text}':fontsize=26:fontcolor={PP_WHITE}:"
        f"x=60:y={y_offset + 20}:{enable}",
    ]

    if safe_sub:
        parts.append(
            f"drawtext=fontfile={FONT_MONO}:"
            f"text='{safe_sub}':fontsize=16:fontcolor={PP_GOLD}:"
            f"x=60:y={y_offset + 58}:{enable}"
        )

    return ",".join(parts)


def render_lower_third(text: str, subtitle: str = "",
                       output_path: str = "",
                       duration: float = 4.0,
                       width: int = 1920, height: int = 200) -> bool:
    """Render a branded lower third as a standalone transparent video.

    Output is a short video with alpha channel (PNG codec) that can be
    overlaid on other video segments.

    Args:
        text: Main text line.
        subtitle: Secondary text in gold.
        output_path: Where to write the rendered overlay.
        duration: Duration of the overlay video.
        width: Output width.
        height: Output height.

    Returns:
        True if rendering succeeded.
    """
    if not output_path:
        log.error("render_lower_third: no output_path")
        return False

    safe_text = _sanitize(text)[:80]
    safe_sub = _sanitize(subtitle)[:60]

    vf_parts = [
        # Dark glass background
        f"drawbox=x=40:y=40:w=800:h=120:color={PP_DARK}@0.85:t=fill",
        # Red accent bar
        f"drawbox=x=40:y=40:w=4:h=120:color={PP_RED}@1.0:t=fill",
        # Main text
        f"drawtext=fontfile={FONT_BOLD}:text='{safe_text}':"
        f"fontsize=28:fontcolor={PP_WHITE}:x=60:y=65",
    ]

    if safe_sub:
        vf_parts.append(
            f"drawtext=fontfile={FONT_MONO}:text='{safe_sub}':"
            f"fontsize=18:fontcolor={PP_GOLD}:x=60:y=105"
        )

    vf = ",".join(vf_parts)

    try:
        r = subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=0x000000@0.0:s={width}x{height}:d={duration}:r=30",
            "-vf", vf,
            "-c:v", "png", "-pix_fmt", "argb",
            output_path,
        ], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        log.warning("render_lower_third: timeout")
        return False

    return r.returncode == 0 and os.path.exists(output_path)


def apply_lower_third(video_path: str, text: str, subtitle: str = "",
                      output_path: str = "",
                      show_start: float = 0.5,
                      show_duration: float = 4.0) -> str:
    """Apply a branded lower third overlay directly onto a video.

    Video stream is re-encoded with the lower third burned in.
    Audio is copied.

    Args:
        video_path: Source video to overlay on.
        text: Main text line.
        subtitle: Secondary text.
        output_path: Where to write result. Default: video_path + ".lt.mp4".
        show_start: When to show the lower third (seconds).
        show_duration: How long to show it (seconds).

    Returns:
        output_path on success, empty string on failure.
    """
    if not os.path.exists(video_path):
        return ""

    if not output_path:
        output_path = video_path + ".lt.mp4"

    show_end = show_start + show_duration
    lt_filter = lower_third_filter(text, subtitle,
                                   show_start=show_start,
                                   show_end=show_end)

    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", lt_filter,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M",
            "-c:a", "copy",
            output_path,
        ], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        log.warning("apply_lower_third: timeout")
        return ""

    if r.returncode == 0 and os.path.exists(output_path):
        return output_path
    return ""
