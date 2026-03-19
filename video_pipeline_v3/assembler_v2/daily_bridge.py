"""
daily_bridge.py — Translates daily_run.py pipeline outputs into assembler_v2 EpisodeManifest.

Script format (actual):
  script["dialogue"] = list of dicts with keys: host, text, type, clip_rank, headline
  script["cold_open"] = str (standalone cold open text — same as first dialogue entry)
  host == 2 → narration (PBX)
  host == "CLIP" → partner_clip (no audio, clip_rank key)

Audio format: audio_dir/line_{NNN:03d}_pbx.m4a — indexed by dialogue position
  CLIP entries (host=="CLIP") have no audio file — they're skipped in numbering.

extracted_clips: dict keyed by int rank → {"path": str}
"""
import os, json, logging
from pathlib import Path
from .manifest import EpisodeManifest, SegmentSpec

logger = logging.getLogger(__name__)

TYPE_MAP = {
    "cold_open":      "cold_open",
    "setup":          "narration",
    "react":          "narration",
    "narration":      "narration",
    "data_segment":   "data",
    "data":           "data",
    "social_segment": "social",
    "social":         "social",
    "signal_active":  "signal_active",
    "wrap":           "wrap",
    "outro":          "wrap",
}


def build_manifest_from_pipeline(
    script: dict,
    audio_paths: dict,
    extracted_clips: dict,
    btc_price: str,
    date_str: str,
    audio_dir: str = None,
) -> EpisodeManifest:
    """Build EpisodeManifest from daily_run.py pipeline outputs."""

    dialogue = script.get("dialogue", script.get("segments", []))
    if not dialogue:
        logger.error("[bridge] No dialogue in script")
        return EpisodeManifest(date_str=date_str, title="Empty", segments=[], btc_price=btc_price)

    specs = []
    speech_idx = 0  # tracks narration-only audio file index

    for entry in dialogue:
        host = entry.get("host")
        seg_type_raw = entry.get("type", "narration")
        headline = entry.get("headline", "")
        text = entry.get("text", "")
        clip_rank = entry.get("clip_rank", entry.get("rank", 0))

        # CLIP entries → partner_clip segment
        if host == "CLIP":
            clip_info = extracted_clips.get(clip_rank, {})
            if isinstance(clip_info, list):
                clip_info = clip_info[0] if clip_info else {}
            clip_path = clip_info.get("path") if isinstance(clip_info, dict) else None

            if clip_path and Path(clip_path).exists():
                specs.append(SegmentSpec(
                    segment_type="partner_clip",
                    clip_rank=clip_rank,
                    clip_path=clip_path,
                    headline=headline,
                    btc_price=btc_price,
                ))
                # Add transition after partner_clip
                specs.append(SegmentSpec(segment_type="transition", btc_price=btc_price))
            else:
                logger.warning(f"[bridge] Clip rank {clip_rank} missing — skipping")
            continue

        # Narration entries — find audio file
        seg_type = TYPE_MAP.get(seg_type_raw, "narration")

        # Audio file: line_{speech_idx:03d}_pbx.m4a
        tts_path = None
        if audio_dir:
            candidate = Path(audio_dir) / f"line_{speech_idx:03d}_pbx.m4a"
            if candidate.exists() and candidate.stat().st_size > 500:
                tts_path = str(candidate)
        speech_idx += 1

        # Duration hint
        duration_hint = 0.0
        if tts_path:
            try:
                from .helpers import ffprobe_duration
                duration_hint = ffprobe_duration(Path(tts_path))
            except Exception:
                pass

        # Social posts for social segments
        social_posts = []
        if seg_type == "social":
            try:
                cache = Path(__file__).parent.parent / "cache" / "active_signal.json"
                if cache.exists():
                    data = json.loads(cache.read_text())
                    posts = data.get("nostr_posts", [])[:3]
                    social_posts = [{
                        "account": p.get("display_name", "unknown"),
                        "text": p.get("text", "")[:280],
                        "timestamp": "", "likes": 0, "retweets": 0,
                    } for p in posts]
            except Exception:
                pass

        specs.append(SegmentSpec(
            segment_type=seg_type,
            clip_rank=clip_rank or 0,
            tts_path=tts_path,
            headline=headline[:80] if headline else text[:80],
            body=text[:500],
            social_posts=social_posts,
            duration_hint=duration_hint,
            btc_price=btc_price,
            is_required=(seg_type in ("cold_open", "wrap")),
        ))

    # Ensure wrap at end
    if specs and specs[-1].segment_type != "wrap":
        specs.append(SegmentSpec(
            segment_type="wrap",
            btc_price=btc_price,
            is_required=True,
        ))

    title = script.get("episode_title", f"Pulse Check {date_str}")
    logger.info(f"[bridge] Built manifest: {len(specs)} segments for '{title}'")
    return EpisodeManifest(date_str=date_str, title=title, segments=specs, btc_price=btc_price)
