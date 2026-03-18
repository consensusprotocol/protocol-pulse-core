"""
Protocol Pulse V2 — daily_bridge.py
Bridge between the existing daily_run.py pipeline outputs and assembler_v2's
EpisodeManifest format. One function: build_manifest_from_pipeline().
"""
import os
import json
from pathlib import Path

from .manifest import EpisodeManifest, SegmentSpec


def build_manifest_from_pipeline(
    script: dict,
    audio_paths: dict,
    extracted_clips: dict,
    btc_price: str,
    date_str: str,
) -> EpisodeManifest:
    """Convert daily_run.py pipeline outputs into an EpisodeManifest.

    Args:
        script: Script dict with "segments" list (each has type, host, text, headline, rank)
        audio_paths: Dict with "segments" list of absolute .m4a paths
        extracted_clips: Dict keyed by rank int, value has "path" key
        btc_price: Price string like "$84,000"
        date_str: Date string like "2026-03-18"

    Returns:
        EpisodeManifest ready for EpisodeRunner.run()
    """
    segments_list = script.get("segments", [])
    audio_list = audio_paths.get("segments", [])
    spec_list = []

    TYPE_MAP = {
        "cold_open": "cold_open",
        "narration": "narration",
        "setup": "narration",
        "react": "narration",
        "partner_clip": "partner_clip",
        "data": "data",
        "social": "social",
        "signal_active": "signal_active",
        "wrap": "wrap",
        "outro": "wrap",
    }

    for i, seg in enumerate(segments_list):
        seg_type = seg.get("type", "narration")
        mapped_type = TYPE_MAP.get(seg_type, "narration")

        # If host is "CLIP", it's a partner_clip segment
        if seg.get("host") == "CLIP" or seg_type == "partner_clip":
            mapped_type = "partner_clip"

        tts_path = audio_list[i] if i < len(audio_list) else None
        clip_rank = seg.get("rank", i + 1)

        # Get clip path for partner_clip segments
        clip_path = None
        pip_path = None
        if mapped_type == "partner_clip":
            clip_info = extracted_clips.get(clip_rank, {})
            if isinstance(clip_info, list):
                clip_info = clip_info[0] if clip_info else {}
            clip_path = clip_info.get("path") if clip_info else None

        # Get duration hint from TTS file if available
        duration_hint = 0.0
        if tts_path and os.path.exists(tts_path):
            try:
                from .helpers import ffprobe_duration
                duration_hint = ffprobe_duration(Path(tts_path))
            except Exception:
                pass

        # Get social posts from active_signal cache if social segment
        social_posts = []
        if mapped_type == "social":
            try:
                cache = Path(__file__).parent.parent / "cache" / "active_signal.json"
                if cache.exists():
                    data = json.loads(cache.read_text())
                    posts = data.get("nostr_posts", [])[:3]
                    social_posts = [
                        {
                            "account": p.get("display_name", "unknown"),
                            "text": p.get("text", "")[:280],
                            "timestamp": "",
                            "likes": 0,
                            "retweets": 0,
                        }
                        for p in posts
                    ]
            except Exception:
                pass

        spec = SegmentSpec(
            segment_type=mapped_type,
            clip_rank=clip_rank,
            tts_path=tts_path if tts_path and os.path.exists(str(tts_path)) else None,
            clip_path=clip_path,
            pip_path=pip_path,
            headline=seg.get("headline", seg.get("text", "")[:80]),
            body=seg.get("text", "")[:500],
            social_posts=social_posts,
            duration_hint=duration_hint,
            btc_price=btc_price,
            is_required=(mapped_type in ("cold_open", "wrap")),
        )
        spec_list.append(spec)

    # Always ensure wrap segment at end if missing
    if spec_list and spec_list[-1].segment_type != "wrap":
        spec_list.append(SegmentSpec(segment_type="wrap", btc_price=btc_price))

    # Add transition between partner_clip and following narration segments
    final_specs = []
    for j, spec in enumerate(spec_list):
        final_specs.append(spec)
        if spec.segment_type == "partner_clip" and j + 1 < len(spec_list):
            next_type = spec_list[j + 1].segment_type
            if next_type == "narration":
                final_specs.append(SegmentSpec(segment_type="transition"))

    return EpisodeManifest(
        date_str=date_str,
        title=script.get("episode_title", f"Pulse Check {date_str}"),
        segments=final_specs,
        btc_price=btc_price,
    )
