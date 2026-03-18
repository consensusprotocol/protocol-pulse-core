"""
Protocol Pulse V2 — helpers.py
Core utilities. Every ffmpeg call goes through run_ffmpeg(). No exceptions.
"""
from __future__ import annotations
import subprocess, json, os, time, shutil, logging
from pathlib import Path
from typing import Optional
from .constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    COLOR_BG, CHARTS_DIR,
    FFMPEG_TIMEOUT_ENCODE, FFMPEG_TIMEOUT_FILTER, FFMPEG_TIMEOUT_PROBE
)

logger = logging.getLogger(__name__)


# ── Core FFmpeg runner ────────────────────────────────────────────────────────

def run_ffmpeg(args: list, label: str = "", timeout: int = FFMPEG_TIMEOUT_ENCODE) -> bool:
    """
    Single authoritative ffmpeg runner. All segments use this. Never bypass.
    Logs full command, duration, and stderr on failure.
    """
    cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
    full_cmd = ' '.join(cmd)
    logger.debug(f"[ffmpeg] {label} | full cmd: {full_cmd}")
    logger.info(f"[ffmpeg] {label} | cmd: {' '.join(cmd[:10])}...")
    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = round(time.time() - t0, 2)
        if result.returncode != 0:
            logger.error(f"[ffmpeg] FAIL {label} ({elapsed}s) rc={result.returncode}")
            logger.error(f"[ffmpeg] STDERR: {result.stderr[-1200:]}")
            return False
        logger.info(f"[ffmpeg] OK {label} ({elapsed}s)")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"[ffmpeg] TIMEOUT {label} after {timeout}s")
        return False
    except Exception as e:
        logger.error(f"[ffmpeg] EXCEPTION {label}: {e}")
        return False


# ── FFprobe utilities ─────────────────────────────────────────────────────────

def ffprobe_duration(path: Path) -> float:
    """Return audio/video duration in seconds. Returns 0.0 on any error."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_PROBE
        )
        val = r.stdout.strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0


def ffprobe_streams(path: Path) -> dict:
    """Return full ffprobe JSON. Returns {} on error."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_PROBE
        )
        return json.loads(r.stdout)
    except Exception:
        return {}


def ffprobe_contract(path: Path) -> tuple:
    """
    Verify segment meets the V2 output contract.
    Returns (passed: bool, summary: dict).
    Every segment is checked after render. Filler used if failed.
    """
    if not path.exists() or path.stat().st_size < 1000:
        return False, {"error": "file missing or too small", "passed": False}

    info = ffprobe_streams(path)
    if not info:
        return False, {"error": "ffprobe returned no data", "passed": False}

    streams = info.get("streams", [])
    fmt = info.get("format", {})
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration", 0))
    issues = []

    if not video:
        issues.append("no video stream")
    else:
        if video.get("width") != VIDEO_W:
            issues.append(f"width={video.get('width')} (need {VIDEO_W})")
        if video.get("height") != VIDEO_H:
            issues.append(f"height={video.get('height')} (need {VIDEO_H})")
        if video.get("pix_fmt") != VIDEO_PIX_FMT:
            issues.append(f"pix_fmt={video.get('pix_fmt')} (need {VIDEO_PIX_FMT})")
        fps_str = video.get("r_frame_rate", "0/1")
        try:
            n, d = fps_str.split("/")
            fps = float(n) / float(d)
            if abs(fps - VIDEO_FPS) > 0.5:
                issues.append(f"fps={fps:.2f} (need {VIDEO_FPS})")
        except Exception:
            issues.append(f"unparseable fps: {fps_str}")

    if not audio:
        issues.append("no audio stream")
    else:
        sr = int(audio.get("sample_rate", 0))
        if sr != AUDIO_SAMPLE_RATE:
            issues.append(f"sample_rate={sr} (need {AUDIO_SAMPLE_RATE})")
        ch = audio.get("channels", 0)
        if ch != AUDIO_CHANNELS:
            issues.append(f"channels={ch} (need {AUDIO_CHANNELS})")
        # Codec checks — critical for concat compatibility
        if video and video.get("codec_name") != "h264":
            issues.append(f"video_codec={video.get('codec_name')} (need h264)")
        if audio.get("codec_name") != AUDIO_CODEC:
            issues.append(f"audio_codec={audio.get('codec_name')} (need {AUDIO_CODEC})")
        # Audio bitrate check — ±10% tolerance for VBR rounding (192k = 192000 bps)
        # AAC VBR compresses silence very efficiently, so short or silent segments
        # will average far below nominal. Upper bound always checked (catches wrong
        # -b:a setting). Lower bound only reliable on segments >= 30s with real audio.
        raw_br = audio.get("bit_rate", 0)
        try:
            audio_br = int(raw_br)
        except (ValueError, TypeError):
            audio_br = 0
        if audio_br > 211200:
            issues.append(f"audio_bitrate={audio_br} too high (max 211200)")
        elif audio_br > 0 and duration >= 30.0 and audio_br < 172800:
            issues.append(f"audio_bitrate={audio_br} too low (min 172800)")

    passed = len(issues) == 0

    summary = {
        "passed": passed,
        "issues": issues,
        "duration": round(duration, 3),
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "fps": fps_str if video else None,
        "pix_fmt": video.get("pix_fmt") if video else None,
        "sample_rate": audio.get("sample_rate") if audio else None,
        "channels": audio.get("channels") if audio else None,
    }

    if issues:
        logger.warning(f"[contract] FAIL {path.name}: {', '.join(issues)}")
    else:
        logger.info(f"[contract] PASS {path.name} ({duration:.1f}s)")

    return passed, summary


# ── Filler segment ────────────────────────────────────────────────────────────

def make_filler(output_path: Path, duration: float,
                tts_path: Optional[Path] = None) -> bool:
    """
    Generate a contract-compliant filler segment.
    Uses TTS audio if available so PBX voice continues even if video failed.
    Dark background — clearly not final content but episode continues.
    """
    dur = max(float(duration), 5.0)
    if float(duration) < 5.0:
        logger.info(f"[filler] 5s floor applied (requested {duration:.1f}s)")

    if tts_path and tts_path.exists() and tts_path.stat().st_size > 1000:
        ok = run_ffmpeg([
            "-f", "lavfi", "-i",
            f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-i", str(tts_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
            "-ac", str(AUDIO_CHANNELS),
            "-t", str(dur), "-shortest",
            str(output_path)
        ], f"filler+audio {output_path.name}", FFMPEG_TIMEOUT_FILTER)
    else:
        ok = run_ffmpeg([
            "-f", "lavfi", "-i",
            f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-f", "lavfi", "-i",
            f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
            "-ac", str(AUDIO_CHANNELS),
            "-t", str(dur),
            str(output_path)
        ], f"filler+silence {output_path.name}", FFMPEG_TIMEOUT_FILTER)

    return ok and output_path.exists() and output_path.stat().st_size > 1000


# ── Atomic file operations ────────────────────────────────────────────────────

def atomic_rename(src: Path, dst: Path) -> bool:
    """
    Atomically move src to dst. Never leaves partial files at dst.
    Uses os.replace() for POSIX atomicity. Falls back to copy+replace
    for cross-device moves.
    """
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(str(src), str(dst))
        except OSError:
            # Cross-device: copy then atomic swap
            tmp_copy = dst.with_suffix(dst.suffix + ".atomic_tmp")
            shutil.copy2(str(src), str(tmp_copy))
            os.replace(str(tmp_copy), str(dst))
            src.unlink(missing_ok=True)
        logger.info(f"[atomic] {src.name} -> {dst}")
        return True
    except Exception as e:
        logger.error(f"[atomic] FAIL {src} -> {dst}: {e}")
        return False


# ── PiP pre-normalization ─────────────────────────────────────────────────────

def normalize_pip_preview(clip_path: Path, output_path: Path,
                           duration: float = 8.0) -> bool:
    """
    Pre-normalize a partner clip to pip_preview_norm format.
    Run ONCE per clip in Stage 2, NOT inside narration renders.
    Output: 640x360, yuv420p, 30fps CFR, no audio, h264 crf=18, hue=s=0.25.
    This pre-processing means narration.py only does a simple overlay.
    No zoompan, no heavy real-time transforms.
    """
    if not clip_path.exists() or clip_path.stat().st_size < 50000:
        logger.warning(f"[pip_norm] clip missing or tiny: {clip_path}")
        return False

    clip_dur = ffprobe_duration(clip_path)
    if clip_dur < 2.0:
        logger.warning(f"[pip_norm] clip too short ({clip_dur:.1f}s): {clip_path.name}")
        return False

    # Extract from midpoint — better face/content shots
    start = max(0.0, (clip_dur / 2.0) - (duration / 2.0))
    actual_dur = min(duration, clip_dur - start)

    ok = run_ffmpeg([
        "-ss", str(round(start, 3)),
        "-i", str(clip_path),
        "-t", str(round(actual_dur, 3)),
        "-an",
        "-vf", (
            "scale=640:360:force_original_aspect_ratio=decrease,"
            "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={VIDEO_FPS},"
            f"format={VIDEO_PIX_FMT},"
            "hue=s=0.25"
        ),
        "-c:v", VIDEO_CODEC, "-crf", "18", "-preset", "veryfast",
        str(output_path)
    ], f"pip_norm {clip_path.name}", FFMPEG_TIMEOUT_FILTER)

    if ok and output_path.exists():
        logger.info(f"[pip_norm] OK {output_path.name} ({actual_dur:.1f}s)")
        return True
    return False


# ── Chart PNG helper ──────────────────────────────────────────────────────────

def get_chart_path(keyword: str) -> Optional[Path]:
    """
    Map narration keyword to chart PNG path.
    Returns None if chart missing — caller must handle gracefully.
    """
    mapping = {
        "price": CHARTS_DIR / "price_chart.png",
        "hashrate": CHARTS_DIR / "hashrate_chart.png",
        "mempool": CHARTS_DIR / "dominance_chart.png",
        "dominance": CHARTS_DIR / "dominance_chart.png",
    }
    path = mapping.get(keyword.lower())
    if path and path.exists() and path.stat().st_size > 1000:
        return path
    # Return None for unmapped keywords — segment handles missing chart gracefully
    # Never return a wrong chart (content integrity rule)
    if keyword and keyword.lower() not in mapping:
        logger.warning(f"[chart] unmapped chart keyword '{keyword}' — returning None")
        return None
    # For empty keyword (show all charts), return None — segment handles grid layout
    return None

def write_concat_list(paths: list, dest: Path) -> bool:
    """Write FFmpeg concat demuxer list file with proper path escaping.
    Single quotes in paths are escaped as '\\'' for the concat demuxer format.
    Writes atomically via temp file. Returns True on success."""
    try:
        import tempfile
        lines = []
        for p in paths:
            escaped = str(p).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        content = "\n".join(lines) + "\n"
        with tempfile.NamedTemporaryFile(
            mode='w', dir=str(dest.parent), suffix='.tmp', delete=False
        ) as f:
            f.write(content)
            tmp_path = Path(f.name)
        os.replace(str(tmp_path), str(dest))
        return True
    except Exception as e:
        logger.error(f"[helpers] write_concat_list failed: {e}")
        return False


def safe_text(text, max_chars=80):
    """
    Single authoritative text sanitizer for FFmpeg drawtext filter values.
    FFmpeg drawtext escape rules:
      - Backslash must be escaped first: \\ → \\\\
      - Single quotes are the text= delimiter, escape as: ' → '\\''
        (close quote, literal escaped quote, reopen quote)
      - Colons, percent signs, brackets, commas, semicolons need backslash escape
      - Newlines replaced with space (drawtext does not support literal newlines)
    Every drawtext text= value MUST go through this function. No exceptions.
    """
    t = str(text).strip()[:max_chars]
    # Backslash first (before any other escape introduces backslashes)
    t = t.replace("\\", "\\\\")
    # Single quote: FFmpeg drawtext escape sequence
    t = t.replace("'", "'\\''")
    # Special chars that need backslash escaping in drawtext
    for ch in (":", "%", "[", "]", ",", ";"):
        t = t.replace(ch, "\\" + ch)
    return t.replace("\n", " ")
