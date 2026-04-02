#!/usr/bin/env python3
"""Render outro sequences for Protocol Pulse episodes.

Handles signoff + CTA + end screen rendering. Delegates complex rendering
to assembler.py scene functions while providing a clean module API.

Usage:
    from render_outro import render_outro
"""

import logging
import os

log = logging.getLogger("render_outro")


def render_outro(script: dict, audio_data: dict, work_dir: str,
                 parts: list = None, **kwargs) -> tuple:
    """Render the episode outro sequence.

    Tries outro_branded_new.mp4 first (has own embedded music, hard cut).
    Falls back to branded outro with wrap narration, then tag video.

    Args:
        script: Episode script dict.
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}.
        work_dir: Working directory for intermediate files.
        parts: Current list of episode parts (for timing calculation).

    Returns:
        Tuple of (outro_path, skip_outro_fade) where skip_outro_fade=True
        means the outro has its own music and should not be faded by concat.
    """
    os.makedirs(work_dir, exist_ok=True)

    from assembler import (
        make_outro_branded_new, make_branded_outro, make_tag_video,
        ffprobe_duration,
        OUTRO_BRANDED_NEW,
    )

    part_idx = len(parts) if parts else 0
    audio_lines = audio_data.get("lines", [])

    # Option 1: New branded outro (has own music, hard cut)
    if os.path.exists(OUTRO_BRANDED_NEW):
        outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded_new.mp4")
        result = make_outro_branded_new(outro_out)
        if result:
            dur = ffprobe_duration(result)
            log.info("Outro (branded new): %.1fs — hard cut, own music", dur)
            return result, True

    # Option 2: Branded outro with wrap narration
    wrap_audio = ""
    for al in reversed(audio_lines):
        if (al.get("host") not in ("CLIP",) and al.get("path")
                and os.path.exists(al.get("path", ""))):
            wrap_audio = al["path"]
            break

    outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded.mp4")
    result = make_branded_outro(outro_out, narration_audio=wrap_audio)
    if result:
        dur = ffprobe_duration(result)
        log.info("Outro (branded): %.1fs%s", dur,
                 " (with narration)" if wrap_audio else "")
        return result, False

    # Option 3: Tag video fallback
    tag_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_tag.mp4")
    result = make_tag_video(tag_out)
    if result:
        dur = ffprobe_duration(result)
        log.info("Outro (tag fallback): %.1fs", dur)
        return result, False

    log.warning("No outro available")
    return "", False
