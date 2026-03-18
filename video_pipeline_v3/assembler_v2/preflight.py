"""Validate everything before touching ffmpeg. Fail fast."""

import os, shutil, logging, json
from pathlib import Path
from typing import Optional
from .constants import *
from .helpers import ffprobe_duration, ffprobe_streams

logger = logging.getLogger(__name__)

CRITICAL_ASSETS = [
    (INTRO_TAG, "intro_tag.mp4"),
    (INTRO_MUSIC, "intro_music.mp3"),
    (BG_LOOP, "bg_loop.mp4"),
    (OUTRO_BRANDED, "outro_branded_new.mp4"),
    (SFX_WHOOSH, "custom_whoosh.wav"),
    (SFX_SWOOSH, "card_swoosh.wav"),
    (FONT_BOLD, "JetBrainsMono-Bold.ttf"),
    (FONT_MONO, "JetBrainsMono-Regular.ttf"),
]


def run_preflight(tts_files: list[Path], clip_files: list[Path],
                  work_dir: Path) -> dict:
    """Run all preflight checks. Returns report dict.
    Raises RuntimeError if any CRITICAL check fails."""
    report = {"passed": True, "critical_failures": [], "warnings": [], "checks": {}}

    def fail(msg: str):
        report["critical_failures"].append(msg)
        report["passed"] = False
        logger.error(f"[preflight] CRITICAL: {msg}")

    def warn(msg: str):
        report["warnings"].append(msg)
        logger.warning(f"[preflight] WARNING: {msg}")

    # 1. ffmpeg / ffprobe available
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            fail(f"{tool} not found in PATH")
        else:
            report["checks"][tool] = "OK"

    # 2. Critical asset files
    for path, name in CRITICAL_ASSETS:
        if not path.exists():
            fail(f"Missing critical asset: {name} at {path}")
        elif path.stat().st_size < 1000:
            fail(f"Zero/tiny asset: {name} ({path.stat().st_size} bytes)")
        else:
            report["checks"][name] = f"OK ({path.stat().st_size // 1024}KB)"

    # 3. Disk space (need at least 10GB free)
    try:
        stat = os.statvfs(str(work_dir))
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if free_gb < 5.0:
            fail(f"Insufficient disk space: {free_gb:.1f}GB free (need 5GB+)")
        elif free_gb < 10.0:
            warn(f"Low disk space: {free_gb:.1f}GB free")
        report["checks"]["disk_space"] = f"{free_gb:.1f}GB free"
    except Exception as e:
        warn(f"Could not check disk space: {e}")

    # 4. TTS files validation
    for p in tts_files:
        if not p.exists():
            fail(f"TTS file missing: {p.name}")
        elif p.stat().st_size < 1000:
            fail(f"TTS file empty/tiny: {p.name} ({p.stat().st_size} bytes)")
        else:
            dur = ffprobe_duration(p)
            if dur < 0.5:
                fail(f"TTS file has no audio: {p.name}")
            else:
                report["checks"][f"tts_{p.name}"] = f"OK ({dur:.1f}s)"

    # 5. Partner clip validation
    for p in clip_files:
        if not p.exists():
            warn(f"Clip missing (will use filler): {p.name}")
            continue
        if p.stat().st_size < 50000:
            warn(f"Clip suspiciously small: {p.name} ({p.stat().st_size} bytes)")
            continue
        info = ffprobe_streams(p)
        streams = info.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        dur = ffprobe_duration(p)
        if not has_video:
            warn(f"Clip has no video stream: {p.name}")
        if not has_audio:
            warn(f"Clip has no audio stream: {p.name}")
        if dur < 5:
            warn(f"Clip very short ({dur:.1f}s): {p.name}")
        if dur > 600:
            warn(f"Clip very long ({dur:.1f}s): {p.name}")
        report["checks"][f"clip_{p.name}"] = f"OK ({dur:.1f}s, video={has_video}, audio={has_audio})"

    # 6. Chart PNGs (warnings only — data segment handles missing gracefully)
    for chart in ("price_chart.png", "hashrate_chart.png", "dominance_chart.png"):
        chart_path = CHARTS_DIR / chart
        if not chart_path.exists():
            warn(f"Chart PNG missing: {chart} — data segment will use fallback")
        else:
            report["checks"][chart] = f"OK ({chart_path.stat().st_size // 1024}KB)"

    if report["critical_failures"]:
        raise RuntimeError(
            f"Preflight FAILED — {len(report['critical_failures'])} critical issues:\n"
            + "\n".join(f"  - {x}" for x in report["critical_failures"])
        )

    logger.info(f"[preflight] PASSED — {len(report['warnings'])} warnings")
    return report
