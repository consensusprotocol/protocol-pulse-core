"""Core utilities. Every ffmpeg call goes through run_ffmpeg(). No exceptions."""

import subprocess, json, os, time, logging, shutil
from pathlib import Path
from typing import Optional
from .constants import *

logger = logging.getLogger(__name__)


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    """Single authoritative ffmpeg runner. All segments use this. Never call subprocess directly."""
    cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
    logger.info(f"[ffmpeg] {label}: {' '.join(cmd[:8])}...")
    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - t0
        if result.returncode != 0:
            logger.error(f"[ffmpeg] FAILED {label} ({elapsed:.1f}s): {result.stderr[-500:]}")
            return False
        logger.info(f"[ffmpeg] OK {label} ({elapsed:.1f}s)")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"[ffmpeg] TIMEOUT {label} after {timeout}s")
        return False
    except Exception as e:
        logger.error(f"[ffmpeg] EXCEPTION {label}: {e}")
        return False


def ffprobe_duration(path: Path) -> float:
    """Return duration in seconds. Returns 0.0 on any error."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=15
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def ffprobe_streams(path: Path) -> dict:
    """Return full stream info dict. Returns {} on error."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=15
        )
        return json.loads(result.stdout)
    except Exception:
        return {}


def ffprobe_contract(path: Path) -> tuple[bool, dict]:
    """Verify segment meets the output contract. Returns (passed, summary_dict)."""
    info = ffprobe_streams(path)
    if not info:
        return False, {"error": "ffprobe failed"}

    streams = info.get("streams", [])
    fmt = info.get("format", {})

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    issues = []

    if not video:
        issues.append("no video stream")
    else:
        if video.get("width") != VIDEO_W: issues.append(f"width={video.get('width')} not {VIDEO_W}")
        if video.get("height") != VIDEO_H: issues.append(f"height={video.get('height')} not {VIDEO_H}")
        if video.get("pix_fmt") != VIDEO_PIX_FMT: issues.append(f"pix_fmt={video.get('pix_fmt')}")
        fps_str = video.get("r_frame_rate", "0/1")
        try:
            n, d = fps_str.split("/")
            fps = float(n) / float(d)
            if abs(fps - VIDEO_FPS) > 0.5: issues.append(f"fps={fps:.2f} not {VIDEO_FPS}")
        except Exception:
            issues.append(f"bad fps: {fps_str}")

    if not audio:
        issues.append("no audio stream")
    else:
        if int(audio.get("sample_rate", 0)) != AUDIO_SAMPLE_RATE:
            issues.append(f"sample_rate={audio.get('sample_rate')}")
        if audio.get("channels") != AUDIO_CHANNELS:
            issues.append(f"channels={audio.get('channels')}")

    duration = float(fmt.get("duration", 0))

    passed = len(issues) == 0
    summary = {
        "duration": duration,
        "issues": issues,
        "passed": passed,
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "fps": fps_str if video else None,
        "sample_rate": audio.get("sample_rate") if audio else None,
    }

    if issues:
        logger.warning(f"[contract] FAIL {path.name}: {', '.join(issues)}")
    else:
        logger.info(f"[contract] PASS {path.name} ({duration:.1f}s)")

    return passed, summary


def make_filler(output_path: Path, duration: float, tts_path: Optional[Path] = None) -> bool:
    """Generate a filler segment. Uses TTS audio if available, else silence.
    Always produces a contract-compliant segment."""
    dur = max(duration, 5.0)

    if tts_path and tts_path.exists() and tts_path.stat().st_size > 1000:
        # Dark video with TTS audio still playing
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-i", str(tts_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
            "-ac", str(AUDIO_CHANNELS),
            "-t", str(dur),
            "-shortest",
            str(output_path)
        ], "filler with TTS audio", 60)
    else:
        # Pure dark silence filler
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
            "-ac", str(AUDIO_CHANNELS),
            "-t", str(dur),
            str(output_path)
        ], "filler silence", 60)

    return ok and output_path.exists()


def atomic_rename(src: Path, dst: Path) -> bool:
    """Atomically move src to dst. Never leaves partial files at dst."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return True
    except Exception as e:
        logger.error(f"[atomic] rename failed {src} -> {dst}: {e}")
        return False


def normalize_pip_preview(clip_path: Path, output_path: Path, duration: float = 8.0) -> bool:
    """Pre-normalize a partner clip to pip_preview_norm format.
    Run ONCE per clip, not inside narration renders.
    Output: 640x360, yuv420p, 30fps, no audio, h264 crf=18"""
    if not clip_path.exists() or clip_path.stat().st_size < 50000:
        return False
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur < 2:
        return False
    start = max(0, (clip_dur / 2) - (duration / 2))
    actual_dur = min(duration, clip_dur - start)
    return run_ffmpeg([
        "-ss", str(start), "-i", str(clip_path),
        "-t", str(actual_dur), "-an",
        "-vf", (
            "scale=640:360:force_original_aspect_ratio=decrease,"
            "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={VIDEO_FPS},format={VIDEO_PIX_FMT},"
            "hue=s=0.25"   # desaturate slightly — full desat done in narration overlay
        ),
        "-c:v", VIDEO_CODEC, "-crf", "18", "-preset", "veryfast",
        str(output_path)
    ], f"pip normalize {clip_path.name}", 120)
