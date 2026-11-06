#!/usr/bin/env python3
"""pipeline/config.py — Path resolution and constants for parameterised Pulse Check pipeline.

FROZEN from segment_v1/ constants. All paths resolved from segment_dir arg.
"""
import hashlib
import os
import subprocess

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

def verify_vo_voice(vo_manifest):
    """Voice consistency over whichever VO entries actually exist.

    Returns (voice_id, model_id). Raises RuntimeError if there are no VO
    entries or if entries disagree on voice_id/model_id. An intro-less
    manifest (Law 27/M20) is legitimate.
    """
    entries = {k: v for k, v in vo_manifest.items()
               if isinstance(v, dict) and v.get("stem_wav")}
    if not entries:
        raise RuntimeError("STOP: VO manifest has no VO entries")
    pairs = {(v.get("voice_id"), v.get("model_id")) for v in entries.values()}
    if len(pairs) != 1 or None in next(iter(pairs)):
        raise RuntimeError(f"STOP: VO voice/model mismatch across entries: "
                           f"{ {k: (v.get('voice_id'), v.get('model_id')) for k, v in entries.items()} }")
    return next(iter(pairs))


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


# ── PBX Outro Masters (Amendment 1 section 2) ──
OUTRO_MASTER_16x9 = "/home/ultron/protocol_pulse/brand/2026-11/pp_outro_2026-11_16x9_master.mp4"
OUTRO_MASTER_9x16 = "/home/ultron/protocol_pulse/brand/2026-11/pp_outro_2026-11_9x16_master.mp4"
OUTRO_CACHE_DIR = "/home/ultron/protocol_pulse/brand/2026-11/conformed"


def _measure_lufs(path):
    """Measure integrated loudness (LUFS) of an audio/video file."""
    r = subprocess.run([
        "ffmpeg", "-i", path,
        "-af", "loudnorm=print_format=json", "-f", "null", "-",
    ], capture_output=True, text=True, timeout=30)
    import json as _json
    for line in r.stderr.split("\n"):
        if '"input_i"' in line:
            # Find the JSON block
            start = r.stderr.find("{", r.stderr.find('"input_i"') - 50)
            end = r.stderr.find("}", start) + 1
            data = _json.loads(r.stderr[start:end])
            return float(data["input_i"])
    return None


def conform_outro(aspect="16x9"):
    """Conform PBX outro master to pipeline specs (Amendment 1 §2, Amendment 2 §6a).

    Lanczos scale to 1920x1080 / 1080x1920, 24fps, 48kHz stereo.
    Amendment 2 6a: attenuate 9:16 outro to match 16:9 outro level.
    Content-keyed cache: only re-conforms if master hash changes.
    Returns path to conformed file, or raises FileNotFoundError.
    """
    if aspect == "16x9":
        master = OUTRO_MASTER_16x9
        w, h = WIDTH, HEIGHT
    else:
        master = OUTRO_MASTER_9x16
        w, h = VERT_W, VERT_H

    if not os.path.exists(master):
        raise FileNotFoundError(f"PBX outro master missing: {master}")

    os.makedirs(OUTRO_CACHE_DIR, exist_ok=True)

    # Content-keyed: sha256 of master determines cache filename
    sha = hashlib.sha256(open(master, "rb").read()).hexdigest()[:16]
    conformed = os.path.join(OUTRO_CACHE_DIR, f"outro_{aspect}_{sha}.mp4")

    if os.path.exists(conformed):
        return conformed

    # Amendment 2 6a: attenuate 9:16 to match 16:9 level (attenuate only, never boost)
    af_parts = []
    if aspect == "9x16" and os.path.exists(OUTRO_MASTER_16x9):
        lufs_16 = _measure_lufs(OUTRO_MASTER_16x9)
        lufs_9 = _measure_lufs(OUTRO_MASTER_9x16)
        if lufs_16 is not None and lufs_9 is not None and lufs_9 > lufs_16:
            atten_db = lufs_16 - lufs_9  # negative = attenuation
            af_parts.append(f"volume={atten_db:.1f}dB")
            print(f"  6a: attenuating 9:16 outro by {atten_db:.1f}dB "
                  f"({lufs_9:.1f} -> {lufs_16:.1f} LUFS)")

    af_filter = ",".join(af_parts) if af_parts else None

    partial = conformed + ".partial.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", master,
        "-vf", f"scale={w}:{h}:flags=lanczos,setsar=1:1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp",
        "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
    ]
    if af_filter:
        cmd.extend(["-af", af_filter])
    cmd.extend([
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", partial,
    ])
    subprocess.run(cmd, capture_output=True, timeout=60, check=True)
    os.replace(partial, conformed)
    print(f"  Conformed outro ({aspect}): {conformed}")
    return conformed


def resolve_bgm(segment_dir):
    """Resolve background music track. Uses default confident_02 if none specified."""
    local_bgm = os.path.join(segment_dir, "bgm.mp3")
    if os.path.exists(local_bgm):
        return local_bgm
    return "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"
