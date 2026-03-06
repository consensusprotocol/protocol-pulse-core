#!/usr/bin/env python3
"""Manifest Builder — generates episode_manifest.json BEFORE assembly.

Reads: script JSON, audio_data dict, extracted_clips dict, social_posts list.
Produces: episode_manifest.json with explicit segment timeline.

Phase 1: Runs in PARALLEL with existing assembler. Logs manifest vs actual.
"""
import json
import logging
import os
from datetime import datetime, timezone

from music import ffprobe_duration

logger = logging.getLogger("ManifestBuilder")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[manifest] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def build_manifest(script: dict, audio_data: dict, extracted_clips: dict,
                   output_dir: str, music_bed: str = "",
                   btc_price: str = "N/A") -> dict:
    """Build episode manifest from script + audio + clips.

    Args:
        script: Script dict with dialogue array and social_posts
        audio_data: From generate_dialogue_audio() — {lines, total_duration}
        extracted_clips: {rank: {path, channel, duration, video_id, ...}}
        output_dir: Where to save episode_manifest.json
        music_bed: Path to selected music bed track
        btc_price: BTC price string

    Returns:
        Complete manifest dict (also saved to disk)
    """
    dialogue = script.get("dialogue", [])
    audio_lines = audio_data.get("lines", [])
    social_posts = script.get("social_posts", [])
    episode_title = script.get("episode_title", "Pulse Check")
    date_str = datetime.now().strftime("%Y-%m-%d")

    segments = []
    seg_id = 0
    cumulative_sec = 0.0
    audio_idx = 0
    clip_count = 0
    unique_channels = set()

    def _next_audio():
        nonlocal audio_idx
        while audio_idx < len(audio_lines):
            al = audio_lines[audio_idx]
            if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al.get("path", "")):
                audio_idx += 1
                return al
            audio_idx += 1
        return None

    def _add_segment(seg_type, duration, audio_path="", video_path="",
                     visual_mode="cyberpunk_bg", primary_visual="waveform_only",
                     transition_in="none", transition_out="none",
                     music_state="bed_ducked", clip_fade_in=0.0, clip_fade_out=0.0,
                     logo_allowed=False, face_expected=False, clip_rank=0,
                     lower_third=None, social_card_data=None, pip_source=None):
        nonlocal seg_id, cumulative_sec
        seg = {
            "id": seg_id,
            "type": seg_type,
            "screen_mode": seg_type,
            "start_sec": round(cumulative_sec, 2),
            "duration_sec": round(duration, 2),
            "audio_path": audio_path,
            "video_path": video_path,
            "visual_mode": visual_mode,
            "primary_visual_type": primary_visual,
            "transition_in": transition_in,
            "transition_out": transition_out,
            "music_state": music_state,
            "clip_fade_in_sec": clip_fade_in,
            "clip_fade_out_sec": clip_fade_out,
            "logo_allowed": logo_allowed,
            "face_expected": face_expected,
            "clip_rank": clip_rank,
            "lower_third": lower_third,
            "social_card_data": social_card_data,
            "pip_source": pip_source,
        }
        segments.append(seg)
        cumulative_sec += duration
        seg_id += 1
        return seg

    # Process dialogue entries
    social_card_idx = 0
    cold_open_done = False

    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host_field = entry.get("host", "")

        if host_field == "CLIP":
            rank = entry.get("rank", 0)
            clip_info = extracted_clips.get(rank, {})
            clip_path = clip_info.get("path", "")
            channel = clip_info.get("channel", "")

            if clip_path and os.path.exists(clip_path):
                clip_dur = ffprobe_duration(clip_path)
                clip_count += 1
                if channel:
                    unique_channels.add(channel)

                # Transition before clip
                _add_segment("transition", 0.7,
                             transition_in="custom_whoosh",
                             music_state="transition_swell",
                             visual_mode="transition")

                # The clip itself
                _add_segment("partner_clip", clip_dur,
                             audio_path=clip_path,
                             video_path=clip_path,
                             visual_mode="fullscreen_clip",
                             primary_visual="fullscreen_clip",
                             transition_in="custom_whoosh",
                             transition_out="xfade_1s",
                             music_state="none",
                             clip_fade_in=0.3,
                             clip_fade_out=0.5,
                             logo_allowed=True,
                             face_expected=True,
                             clip_rank=rank,
                             lower_third={
                                 "channel": channel,
                                 "speaker": clip_info.get("speaker", ""),
                                 "topic": clip_info.get("topic", ""),
                             })
            continue

        # Host dialogue
        al = _next_audio()
        if not al:
            continue

        audio_path = al["path"]
        audio_dur = ffprobe_duration(audio_path)
        if audio_dur <= 0:
            audio_dur = 5.0

        # Map entry type to segment type
        if entry_type == "cold_open" and not cold_open_done:
            cold_open_done = True
            pip_src = None
            if 1 in extracted_clips:
                pip_src = extracted_clips[1].get("path", "")
            _add_segment("cold_open", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="pip_upcoming",
                         music_state="none",
                         face_expected=True,
                         pip_source=pip_src)
            # Title sequence after cold open
            _add_segment("title_sequence", 4.0,
                         music_state="title_hit",
                         visual_mode="title_card",
                         logo_allowed=True)

        elif entry_type == "setup":
            clip_rank = entry.get("clip_rank", 0)
            pip_src = None
            if clip_rank and clip_rank in extracted_clips:
                pip_src = extracted_clips[clip_rank].get("path", "")
            _add_segment("narration_setup", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="pip_upcoming",
                         pip_source=pip_src,
                         face_expected=bool(pip_src))

        elif entry_type == "react":
            _add_segment("narration_react", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="clip_callback_thumb")

        elif entry_type == "social_segment":
            # Each tweet as its own segment
            cards = social_posts[social_card_idx:social_card_idx + 3]
            for ci, card in enumerate(cards):
                card_dur = audio_dur + 0.3 if ci == 0 else 8.0
                _add_segment("social_card", card_dur,
                             audio_path=audio_path if ci == 0 else "",
                             visual_mode="remotion_social_card",
                             primary_visual="social_card",
                             transition_in="card_swoosh" if ci > 0 else "none",
                             transition_out="card_swoosh",
                             social_card_data={
                                 "handle": card.get("handle", ""),
                                 "text": card.get("text", ""),
                                 "likes": card.get("likes", 0),
                                 "screenshot_path": card.get("screenshot_path", ""),
                             })
            social_card_idx += len(cards)

        elif entry_type == "data_segment":
            _add_segment("data_segment", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="data_card")

        elif entry_type == "wrap":
            _add_segment("wrap", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="waveform_only",
                         music_state="outro_rise")

        else:
            # Generic narration
            _add_segment(entry_type or "narration", audio_dur + 0.3,
                         audio_path=audio_path,
                         visual_mode="cyberpunk_bg",
                         primary_visual="waveform_only")

    # Outro
    _add_segment("outro", 8.0,
                 visual_mode="branded_outro",
                 primary_visual="branded_outro",
                 music_state="outro_rise",
                 logo_allowed=True)

    # Build episode manifest
    manifest = {
        "episode_id": date_str,
        "episode_title": episode_title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_loudness_lufs": -14,
        "true_peak_dbtp": -1.5,
        "music_bed_path": music_bed,
        "logo_policy": "restraint",
        "btc_price": btc_price,
        "total_segments": len(segments),
        "total_duration_estimate": round(cumulative_sec, 2),
        "segments": segments,
        "qc_expectations": {
            "total_duration_range": [360, 900],
            "clip_count": clip_count,
            "unique_channels": len(unique_channels),
            "loudness_lufs": -14,
            "true_peak_dbtp": -1.5,
            "max_silent_gap_sec": 2.0,
            "max_black_frames_sec": 0.5,
        },
    }

    # Save to disk
    manifest_path = os.path.join(output_dir, "episode_manifest.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest built: {len(segments)} segments, ~{cumulative_sec:.0f}s estimated")
    logger.info(f"  Clips: {clip_count} from {len(unique_channels)} channels")
    logger.info(f"  Saved: {manifest_path}")

    return manifest
