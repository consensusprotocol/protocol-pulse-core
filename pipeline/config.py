#!/usr/bin/env python3
"""pipeline/config.py — Path resolution and constants for parameterised Pulse Check pipeline.

FROZEN from segment_v1/ constants. All paths resolved from segment_dir arg.
"""
import os

# ── Video constants (Law 2, Law 3) ──
FPS = 24
WIDTH = 1920
HEIGHT = 1080
VERT_W = 1080
VERT_H = 1920
PRE_ROLL = 1.0
ACCENT_COLOR = (247, 147, 26)

# ── Encoding presets ──
NVENC_QP_FINAL = 18
NVENC_QP_INTERMEDIATE = 20

# ── QA thresholds (Law 20 — do not change) ──
VOICE_SIM_THRESHOLD = 0.75
TRANSCRIPT_OVERLAP_THRESHOLD = 0.80
SHARPNESS_FLOOR = 60
LUMA_FLOOR = 20
AUDIO_FLOOR_DB = -50
EDGE_DENSITY_MAX = 0.08
WHITE_FRACTION_MAX = 0.25
DURATION_TOL = 0.25
PRE_ROLL_FLOOR = 0.95

# ── VO word caps (M18 — single source of truth) ──
INTRO_WORD_CAP = 30
BRIDGE_WORD_CAP = 20
SIGNOFF_WORD_CAP = 24


def resolve_paths(segment_dir, qa_version=None):
    """Resolve all standard paths from a segment directory.

    Returns a dict with all paths needed by render/VO/gates scripts.
    """
    segment_dir = os.path.abspath(segment_dir)

    # QA dir: qa_v<N> if version given, else qa/
    if qa_version is not None:
        # Accept both "qa_v1" and "1" as inputs
        v = qa_version.replace("qa_v", "") if isinstance(qa_version, str) else qa_version
        qa_dir = os.path.join(segment_dir, f"qa_v{v}")
    else:
        qa_dir = os.path.join(segment_dir, "qa")

    paths = {
        "segment_dir": segment_dir,
        "out_dir": os.path.join(segment_dir, "out"),
        "qa_dir": qa_dir,
        "vo_dir": os.path.join(segment_dir, "vo_audio"),
        "sources_dir": os.path.join(segment_dir, "sources"),
        "brand_dir": os.path.join(segment_dir, "brand"),
        "edl_json": os.path.join(segment_dir, "edl.json"),
        "cuts_json": os.path.join(segment_dir, "cuts_final.json"),
        "vo_manifest": os.path.join(segment_dir, "vo_audio", "VO_MANIFEST.json"),
        "publish_dir": os.path.join(segment_dir, "publish"),
    }

    # Ensure output dirs exist
    os.makedirs(paths["out_dir"], exist_ok=True)
    os.makedirs(paths["qa_dir"], exist_ok=True)

    return paths


def resolve_brand(segment_dir):
    """Resolve brand assets. Falls back to segment_v1 brand if not local."""
    local_mark = os.path.join(segment_dir, "brand", "pp_mark_wave_alpha.png")
    if os.path.exists(local_mark):
        return local_mark
    # Fallback to segment_v1 brand (the canonical mark)
    v1_mark = "/home/ultron/protocol_pulse/segment_v1/brand/2026-11/pp_mark_wave_alpha.png"
    if os.path.exists(v1_mark):
        return v1_mark
    # Fallback to brand/ top-level
    top_mark = "/home/ultron/protocol_pulse/brand/2026-11/pp_mark_wave_400.png"
    return top_mark


def resolve_bgm(segment_dir):
    """Resolve background music track. Uses default confident_02 if none specified."""
    local_bgm = os.path.join(segment_dir, "bgm.mp3")
    if os.path.exists(local_bgm):
        return local_bgm
    return "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"
