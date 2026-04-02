#!/usr/bin/env python3
"""Render intro sequences for Protocol Pulse episodes.

Handles cold open + brand sting rendering. Delegates complex rendering
to assembler.py scene functions while providing a clean module API.

Usage:
    from render_intro import render_intro
"""

import logging
import os

log = logging.getLogger("render_intro")


def render_intro(script: dict, audio_data: dict, work_dir: str,
                 btc_price: str = "N/A", **kwargs) -> str:
    """Render the episode intro sequence.

    Tries intro_tag + PBX cold open voice-over first, falls back to
    cyberpunk bg + date text.

    Args:
        script: Episode script dict with dialogue array.
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}.
        work_dir: Working directory for intermediate files.
        btc_price: BTC price string for ticker overlay.

    Returns:
        Path to rendered intro MP4, or empty string on failure.
    """
    os.makedirs(work_dir, exist_ok=True)

    # Import assembler functions (lazy to avoid circular imports)
    from assembler import (
        make_intro_coldopen, make_intro_tag_sequence,
        ffprobe_duration,
    )

    audio_lines = audio_data.get("lines", [])

    # Find first valid audio line for cold open
    cold_open_audio = None
    for al in audio_lines:
        if al.get("host") in ("CLIP",) or not al.get("path"):
            continue
        if al.get("path") and os.path.exists(al.get("path", "")):
            cold_open_audio = al
            break

    if cold_open_audio:
        co_path = cold_open_audio["path"]
        try:
            co_size = os.path.getsize(co_path)
        except OSError:
            co_size = -1

        # Handle empty/missing TTS with fallback
        if co_size <= 0:
            audio_dir = os.path.dirname(co_path) if co_path else ""
            if audio_dir and os.path.isdir(audio_dir):
                sorted_audio = sorted(
                    f for f in os.listdir(audio_dir)
                    if f.endswith((".m4a", ".mp3", ".wav"))
                )
                for af in sorted_audio:
                    af_path = os.path.join(audio_dir, af)
                    if os.path.getsize(af_path) > 1000:
                        cold_open_audio = dict(cold_open_audio)
                        cold_open_audio["path"] = af_path
                        log.warning("Cold open TTS empty, using fallback: %s", af_path)
                        break

        intro_out = os.path.join(work_dir, "part_000_intro_pbx_hook.mp4")
        result = make_intro_coldopen(
            cold_open_audio["path"], intro_out, btc_price=btc_price,
        )
        if result:
            dur = ffprobe_duration(result)
            log.info("Intro + PBX hook: %.1fs", dur)
            return result
        log.warning("Intro + PBX hook failed, trying tag-only fallback")

    # Fallback: intro tag without TTS
    from assembler import INTRO_TAG
    if os.path.exists(INTRO_TAG):
        tag_out = os.path.join(work_dir, "part_000_intro_tag.mp4")
        tag_result = make_intro_tag_sequence(tag_out)
        if tag_result:
            dur = ffprobe_duration(tag_result)
            log.info("Intro tag (no TTS): %.1fs", dur)
            return tag_result

    log.warning("No intro rendered — no tag or cold open available")
    return ""
