#!/usr/bin/env python3
"""Render individual segments for Protocol Pulse episodes.

Each segment is rendered to a standalone MP4. Zero business logic — if inputs
are bad, returns None. The orchestrator handles fallbacks.

Usage:
    from render_segment import render_segment, render_social_segment
"""

import logging
import os

log = logging.getLogger("render_segment")


def render_segment(segment_data: dict, audio_path: str, host_num: int,
                   segment_index: int, total_segments: int,
                   output_path: str, btc_price: str = "N/A",
                   thumbnail_path: str = "",
                   clip_path: str = "",
                   social_posts: list = None,
                   pip_video_path: str = "") -> str:
    """Render ONE segment to a standalone MP4.

    Delegates to assembler.make_broadcast_segment() which routes to the
    appropriate BV2 scene function based on segment type and position.

    Layout per segment type:
      - setup/react: Host narration with PiP clip preview
      - cold_open: Hook headline with waveform
      - data: 2x3 metrics cards + chart
      - social_segment: Tweet card stack
      - wrap: Final sign-off

    Args:
        segment_data: Dict with keys: type, text, speaker, headline, etc.
        audio_path: Path to TTS audio for this segment.
        host_num: Host number (1 or 2, both map to PBX).
        segment_index: Position in episode (0-based).
        total_segments: Total number of dialogue entries.
        output_path: Where to write the rendered segment.
        btc_price: BTC price for ticker overlay.
        thumbnail_path: Optional clip thumbnail for PiP.
        clip_path: Optional clip video path.
        social_posts: Optional list of tweet/social post dicts.
        pip_video_path: Optional PiP video for narration overlay.

    Returns:
        Path to rendered segment MP4, or None if failed.
    """
    # Validate inputs — zero business logic, just guard
    if not audio_path or not os.path.exists(audio_path):
        log.warning("render_segment: no audio at %s", audio_path)
        return None

    if not segment_data:
        log.warning("render_segment: no segment_data")
        return None

    from assembler import make_broadcast_segment

    try:
        result = make_broadcast_segment(
            segment_data, audio_path, host_num,
            segment_index, total_segments,
            output_path, btc_price=btc_price,
            thumbnail_path=thumbnail_path,
            clip_path=clip_path,
            social_posts=social_posts,
            pip_video_path=pip_video_path,
        )
        if result and os.path.exists(result):
            return result
    except Exception as e:
        log.error("render_segment failed: %s", e)

    return None


def render_clip_segment(clip_path: str, clip_info: dict,
                        output_path: str, btc_price: str = "N/A") -> str:
    """Render a YouTube clip segment with attribution overlay.

    Tries Remotion lower third first, falls back to FFmpeg-based overlay.
    Includes AV1/HEVC→H264 pre-conversion and CFR normalization.

    Args:
        clip_path: Path to the downloaded clip video.
        clip_info: Dict with channel, speaker, rank, etc.
        output_path: Where to write the rendered clip.
        btc_price: BTC price for ticker.

    Returns:
        Path to rendered clip MP4, or None if failed.
    """
    if not clip_path or not os.path.exists(clip_path):
        return None

    from assembler import (
        make_remotion_lower_third, make_clip_visual,
        mix_lower_slide_sfx, ffprobe_duration,
    )

    channel = clip_info.get("channel", "")
    handle = f"@{channel.replace(' ', '')}" if channel else "ProtocolPulse"

    result = ""
    try:
        result = make_remotion_lower_third(
            clip_path, handle, output_path,
            btc_price=btc_price,
            speaker_name=clip_info.get("speaker", ""),
        )
    except Exception as e:
        log.warning("Remotion lower third failed: %s", e)

    if not result:
        result = make_clip_visual(clip_path, handle, output_path,
                                  btc_price=btc_price)

    if result and os.path.exists(result):
        mix_lower_slide_sfx(result)
        return result

    return None


def render_social_segment(audio_path: str, posts: list,
                          output_path: str, btc_price: str = "N/A") -> str:
    """Render a social media card segment.

    Tries Remotion social card first, falls back to FFmpeg drawtext.

    Args:
        audio_path: Path to narration TTS.
        posts: List of tweet/social post dicts.
        output_path: Where to write the rendered segment.
        btc_price: BTC price for ticker.

    Returns:
        Path to rendered segment MP4, or None if failed.
    """
    if not audio_path or not os.path.exists(audio_path):
        return None
    if not posts:
        return None

    from assembler import (
        make_remotion_social_card, make_social_card_visual,
        make_host_visual, _mix_swoosh_into_segment,
    )

    result = ""
    try:
        result = make_remotion_social_card(
            audio_path, posts, output_path, btc_price=btc_price,
        )
    except Exception:
        pass

    if not result:
        result = make_social_card_visual(
            audio_path, posts, output_path, btc_price=btc_price,
        )
        if result:
            result = _mix_swoosh_into_segment(result)

    if not result:
        result = make_host_visual(
            audio_path, 2, posts[0].get("text", ""), output_path,
            btc_price=btc_price, label="social_fallback",
            segment_type="social_segment",
        )

    if result and os.path.exists(result):
        return result
    return None
