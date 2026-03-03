#!/usr/bin/env python3
"""Music Integration — handles background music, jingles, and transitions.

All music files are optional. If missing, the pipeline skips gracefully.
"""
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE, "assets", "music")

INTRO_JINGLE = os.path.join(MUSIC_DIR, "pp_intro.mp3")
BG_MUSIC = os.path.join(MUSIC_DIR, "pp_background.mp3")
TRANSITION = os.path.join(MUSIC_DIR, "pp_transition.mp3")
OUTRO_JINGLE = os.path.join(MUSIC_DIR, "pp_outro.mp3")


def has_music() -> bool:
    """Check if background music is available."""
    return os.path.exists(BG_MUSIC)


def has_intro() -> bool:
    return os.path.exists(INTRO_JINGLE)


def has_transition() -> bool:
    return os.path.exists(TRANSITION)


def has_outro() -> bool:
    return os.path.exists(OUTRO_JINGLE)


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def mix_tts_with_music(tts_path: str, output_path: str,
                       music_volume: float = 0.12) -> bool:
    """Mix TTS audio with background music underneath.

    Background music plays at -18dB (volume=0.12) with 1s fade in/out.

    Args:
        tts_path: Path to TTS audio file
        output_path: Where to save mixed audio
        music_volume: Volume level for background music (0.12 = ~-18dB)

    Returns:
        True if mixing succeeded
    """
    if not has_music():
        # No music available — just copy TTS as-is
        subprocess.run(["cp", tts_path, output_path], capture_output=True)
        return os.path.exists(output_path)

    tts_dur = ffprobe_duration(tts_path)
    if tts_dur <= 0:
        return False

    fade_out_start = max(0, tts_dur - 1.0)

    cmd = [
        "ffmpeg", "-y",
        "-i", tts_path,
        "-i", BG_MUSIC,
        "-filter_complex",
        f"[1:a]volume={music_volume},"
        f"afade=t=in:d=1,"
        f"afade=t=out:st={fade_out_start}:d=1,"
        f"atrim=0:{tts_dur}[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first[out]",
        "-map", "[out]",
        "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and os.path.exists(output_path)
    except subprocess.TimeoutExpired:
        return False


def ensure_music_dir():
    """Create music directory if it doesn't exist."""
    os.makedirs(MUSIC_DIR, exist_ok=True)
