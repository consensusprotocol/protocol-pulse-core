#!/usr/bin/env python3
"""Daily Pulse Check Producer V5 — clip-first pipeline.

Real YouTube clips from partner channels, host dialogue around them,
music integration, cold open, avatar shorts.

Usage:
  python3 daily_producer.py               # Full daily episode
  python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  python3 daily_producer.py --skip-scan   # Use cached transcripts only
  python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
  python3 daily_producer.py --no-resume   # Force fresh render, skip checkpoint
"""
import sys; sys.dont_write_bytecode=True
import argparse
import fcntl
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from channel_scanner import scan_all_channels
from clip_selector import select_clips, select_clips_with_fallback
from clip_extractor import extract_all, extract_montage_all, check_av_sync
from script_writer import generate_from_clips
from tts_engine import generate_dialogue_audio
from validators import retry_stage
from assembler import assemble_episode, concatenate_parts, verify_video
from shorts_cutter import generate_shorts
from thumbnail_gen import generate_thumbnail
from chapters import generate_chapters
from podcast_feed import extract_podcast_audio, generate_rss_item
from newsletter_embed import generate_email_html, save_newsletter_html
from music import ensure_music_dir, has_music, has_intro, has_outro
from utils.feature_flags import is_enabled, load_all as load_flags
from utils.quality_gate import compute_quality_score, should_upload, format_score_report
from utils.telegram_alerts import (
    alert_pipeline_start, alert_pipeline_success,
    alert_pipeline_failure, alert_quality_hold, alert_upload_success,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("Producer")


# ---------------------------------------------------------------------------
# Retry-wrapped stage functions (most fragile pipeline stages)
# ---------------------------------------------------------------------------

@retry_stage(max_retries=3, backoff_seconds=5, stage_name="clip_selection")
def _retry_select_clips(videos):
    """Clip selection with retry — wraps select_clips_with_fallback."""
    return select_clips_with_fallback(videos)


@retry_stage(max_retries=3, backoff_seconds=10, stage_name="tts_generation")
def _retry_tts(dialogue, audio_dir):
    """TTS generation with retry — ElevenLabs can timeout."""
    return generate_dialogue_audio(dialogue, audio_dir)


@retry_stage(max_retries=2, backoff_seconds=5, stage_name="clip_extraction")
def _retry_extract_clips(selections, clip_dir):
    """Clip extraction with retry — yt-dlp can fail on specific videos."""
    return extract_all(selections, clip_dir)


# ---------------------------------------------------------------------------
# Per-Render Context File (consumed by watchdog for CC repair specs)
# ---------------------------------------------------------------------------

CHECKPOINT_FILE = "/tmp/render_checkpoint.json"


def write_render_context(step, status, error=None, stage_data=None, **extra):
    """Write/update /tmp/render_context_YYYYMMDD.json for watchdog consumption.

    Called after every pipeline step completes or fails. The watchdog reads this
    file to give Claude Code full context about what was being built when a crash
    occurred. See QWEN_CONTEXT_BIBLE.md Section 7.

    P0 Fix 3: Also writes step-level checkpoint for resume-on-crash.
    stage_data: dict of artifacts to persist for resume (clip paths, script, etc.)
    """
    ctx_path = f"/tmp/render_context_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    try:
        with open(ctx_path) as f:
            ctx = json.load(f)
    except Exception:
        ctx = {
            "episode_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "steps_completed": [],
            "steps_failed": [],
            "render_start_time": datetime.now(timezone.utc).isoformat(),
        }

    if status == "ok":
        if step not in ctx["steps_completed"]:
            ctx["steps_completed"].append(step)
        # P0 Fix 3: checkpoint for resume (with stage artifacts)
        _write_checkpoint(step, stage_data=stage_data)
    else:
        ctx["steps_failed"].append({
            "step": step,
            "error": str(error)[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Merge any extra context (episode_title, btc_price, clips, mood, etc.)
    for k, v in extra.items():
        ctx[k] = v

    try:
        with open(ctx_path, "w") as f:
            json.dump(ctx, f, indent=2)
    except Exception as e:
        logger.warning(f"write_render_context failed: {e}")


def _write_checkpoint(step, stage_data=None):
    """Write last completed step + stage data to checkpoint file.

    stage_data persists artifacts from completed stages (clip paths, script path,
    TTS paths, selections path) so the pipeline can resume from any point.
    """
    try:
        # Merge new stage_data into existing checkpoint data
        existing = {}
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE) as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing_stage_data = existing.get("stage_data", {})
        if stage_data:
            existing_stage_data.update(stage_data)
        data = {
            "last_completed_step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "code_hash": _code_hash(),
            "stage_data": existing_stage_data,
        }
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _read_checkpoint():
    """Read checkpoint. Returns (last_completed_step, stage_data) or (0, {}) if none/stale."""
    try:
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
        # Only resume if checkpoint is from today
        if data.get("date") != datetime.now(timezone.utc).strftime("%Y-%m-%d"):
            return 0, {}
        return int(data.get("last_completed_step", 0)), data.get("stage_data", {})
    except Exception:
        return 0, {}


def _clear_checkpoint():
    """Clear checkpoint after successful render."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except OSError:
        pass


def _code_hash():
    """Hash key pipeline files to detect code changes since last checkpoint."""
    h = hashlib.md5()
    for f in ['assembler.py', 'script_writer.py', 'tts_engine.py', 'clip_extractor.py']:
        path = os.path.join(BASE, f)
        if os.path.exists(path):
            h.update(open(path, 'rb').read())
    return h.hexdigest()[:12]


def get_btc_price() -> str:
    """Fetch current BTC price (CoinGecko primary + mempool.space fallback)."""
    try:
        import requests
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
        if r.status_code == 200:
            usd = r.json().get("bitcoin", {}).get("usd")
            if usd is not None:
                return f"${usd:,.0f}"
    except Exception:
        pass
    try:
        import requests
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            usd = r.json().get("USD", 0)
            return f"${usd:,.0f}"
    except Exception:
        pass
    return "$N/A"  # Fallback - no hardcoded stale price


def _build_fast_test_script(clips_info: dict, btc_price: str) -> dict:
    """Build a minimal hardcoded script for fast-test mode (no Claude API call)."""
    dialogue = []
    # Cold open — PBX-only (host 2) per SOLO HOST law
    dialogue.append({
        "host": 2, "type": "cold_open",
        "text": f"[COLD_OPEN] Bitcoin at {btc_price}. Let's get into today's pulse check.",
    })
    # For each clip, add a setup + clip marker + react
    for rank, info in sorted(clips_info.items()):
        channel = info.get("channel", "Unknown")
        dialogue.append({
            "host": 2, "type": "setup",
            "text": f"[NARRATION] Here's what {channel} had to say.",
        })
        dialogue.append({
            "host": "CLIP", "type": "clip",
            "rank": rank, "source_id": info.get("video_id", ""),
        })
        dialogue.append({
            "host": 2, "type": "react",
            "text": "[NARRATION] Interesting take. Let's keep moving.",
        })
    # Wrap
    dialogue.append({
        "host": 2, "type": "wrap",
        "text": "[WARM] That's the pulse check for today. Stay sovereign.",
    })
    return {
        "episode_title": f"Fast Test — {btc_price}",
        "dialogue": dialogue,
        "thumbnail": {"headline": "FAST TEST", "subtext": btc_price},
    }


def _send_resend_alert(subject: str, body: str):
    """Send a non-blocking email alert via Resend."""
    try:
        import resend
        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        if not resend.api_key:
            logger.warning("RESEND_API_KEY not set — skipping email alert")
            return
        resend.Emails.send({
            "from": "pulse@protocolpulse.io",
            "to": ["contact@consensusprotocol.org"],
            "subject": subject,
            "html": f"<pre>{body}</pre>",
        })
    except Exception as e:
        logger.warning(f"Resend alert failed: {e}")


def _post_render_health_check(video_path: str) -> tuple[bool, list[str]]:
    """Verify rendered video meets quality thresholds.

    Returns (passed, errors).
    """
    errors = []
    if not os.path.exists(video_path):
        return False, ["Video file does not exist"]

    # File size > 50MB
    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if size_mb < 50:
        errors.append(f"File size {size_mb:.1f}MB < 50MB minimum")

    # ffprobe checks
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", video_path],
            capture_output=True, text=True, timeout=30,
        )
        info = json.loads(probe.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])

        # Duration 480-900s (PIPELINE_LAWS: 8-15 min)
        duration = float(fmt.get("duration", 0))
        if duration < 480 or duration > 900:
            errors.append(f"Duration {duration:.0f}s outside 480-900s range (8-15 min law)")
        if duration <= 0:
            errors.append("ffprobe reports zero or negative duration — file likely corrupt")

        # Audio stream present
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        if not audio_streams:
            errors.append("No audio stream found")

        # Video stream present and decodable (audit P2-X3)
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        if not video_streams:
            errors.append("No video stream found")
    except Exception as e:
        errors.append(f"ffprobe failed: {e}")

    passed = len(errors) == 0
    if not passed:
        logger.critical(f"POST-RENDER HEALTH CHECK FAILED: {errors}")
        _send_resend_alert(
            "CRITICAL: Pulse Check render failed health check",
            f"Video: {video_path}\nErrors:\n" + "\n".join(f"  - {e}" for e in errors),
        )
    return passed, errors


import re as _re

# ---------------------------------------------------------------------------
# Pre-Flight QC — Grade A Guarantee
# ---------------------------------------------------------------------------
MAX_PREFLIGHT_ATTEMPTS = 3
MAX_EPISODE_DURATION_S = 900  # 15 minutes HARD CAP — grade F if exceeded

_PREFLIGHT_LOG_DIR = os.path.join(BASE, "logs")


def _preflight_log(msg: str):
    """Append one line to preflight_YYYYMMDD.log."""
    os.makedirs(_PREFLIGHT_LOG_DIR, exist_ok=True)
    log_file = os.path.join(
        _PREFLIGHT_LOG_DIR,
        f"preflight_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log",
    )
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def run_preflight_qc(video_path: str) -> dict:
    """Run pre-flight QC checks on assembled video before grading.

    Returns {passed: bool, issues: list[str], metrics: dict}.

    Checks (all via ffprobe/ffmpeg, no LLM needed):
      1. FREEZE FRAMES — ffmpeg freezedetect n=0.003:d=1.5
      2. SILENCE GAPS  — ffmpeg silencedetect n=-50dB:d=0.8 (middle 80%)
      3. LOUDNESS      — ffmpeg ebur128 (integrated LUFS -17 to -12, TP <= -1.0)
      4. DURATION      — ffprobe (7-15 minutes)
      5. RESOLUTION    — ffprobe (1920x1080)
    """
    issues: list[str] = []
    metrics: dict = {}

    if not os.path.exists(video_path):
        return {"passed": False, "issues": ["Video file not found"], "metrics": {}}

    # ── 1. Freeze frames ──────────────────────────────────────────────────
    freeze_count = 0
    freeze_timestamps: list[float] = []
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf", "freezedetect=n=0.003:d=1.5",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        for m in _re.finditer(r"freeze_start:\s*([\d.]+)", r.stderr):
            freeze_timestamps.append(float(m.group(1)))
        freeze_count = len(freeze_timestamps)
    except Exception as e:
        logger.warning(f"[PREFLIGHT] freezedetect failed: {e}")
    metrics["freeze_frames"] = freeze_count
    metrics["freeze_timestamps"] = freeze_timestamps
    if freeze_count > 0:
        issues.append(f"freeze_frames={freeze_count} (max 0)")

    # ── 2. Silence gaps (middle 80% of video) ─────────────────────────────
    silence_gaps: list[dict] = []
    try:
        # Get duration first
        dur_r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        total_dur = float(dur_r.stdout.strip()) if dur_r.stdout.strip() else 0
        margin = total_dur * 0.10  # ignore first/last 10%

        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af", "silencedetect=noise=-50dB:d=0.8",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        for m in _re.finditer(
            r"silence_start:\s*([\d.]+).*?silence_end:\s*([\d.]+)",
            r.stderr, _re.DOTALL,
        ):
            start, end = float(m.group(1)), float(m.group(2))
            # Only count gaps in the middle 80%
            if start >= margin and end <= (total_dur - margin):
                silence_gaps.append({"start": round(start, 2), "end": round(end, 2),
                                     "duration": round(end - start, 2)})
    except Exception as e:
        logger.warning(f"[PREFLIGHT] silencedetect failed: {e}")
    metrics["silence_gaps"] = len(silence_gaps)
    metrics["silence_details"] = silence_gaps
    if len(silence_gaps) > 0:
        issues.append(f"silence_gaps={len(silence_gaps)} (max 0 in middle 80%)")

    # ── 3. Loudness (ebur128) ─────────────────────────────────────────────
    lufs = None
    true_peak = None
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-filter:a", "loudnorm=print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        json_start = r.stderr.rfind("{")
        json_end = r.stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            ln = json.loads(r.stderr[json_start:json_end])
            lufs = float(ln.get("input_i", -99))
            true_peak = float(ln.get("input_tp", 0))
    except Exception as e:
        logger.warning(f"[PREFLIGHT] loudness measurement failed: {e}")
    metrics["lufs"] = round(lufs, 1) if lufs is not None else None
    metrics["true_peak"] = round(true_peak, 1) if true_peak is not None else None
    if lufs is not None and (lufs < -15.5 or lufs > -12.5):
        issues.append(f"lufs={lufs:.1f} (target -15.5 to -12.5, broadcast -14)")
    if true_peak is not None and true_peak > -0.5:
        issues.append(f"true_peak={true_peak:.1f}dBTP (max -0.5)")

    # ── 4. Duration ───────────────────────────────────────────────────────
    try:
        dur_r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        duration_s = float(dur_r.stdout.strip()) if dur_r.stdout.strip() else 0
    except Exception:
        duration_s = 0
    metrics["duration_s"] = round(duration_s, 1)
    dur_min = duration_s / 60
    metrics["duration_fmt"] = f"{int(dur_min)}m{int(duration_s % 60):02d}s"
    if duration_s < 420 or duration_s > 900:  # 7-15 min
        issues.append(f"duration={dur_min:.1f}min (target 7-15)")

    # ── 5. Resolution ─────────────────────────────────────────────────────
    width, height = 0, 0
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "default=noprint_wrappers=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        for line in r.stdout.strip().splitlines():
            if line.startswith("width="):
                width = int(line.split("=")[1])
            elif line.startswith("height="):
                height = int(line.split("=")[1])
    except Exception:
        pass
    metrics["resolution"] = f"{width}x{height}"
    if width != 1920 or height != 1080:
        issues.append(f"resolution={width}x{height} (expected 1920x1080)")

    passed = len(issues) == 0
    _preflight_log(
        f"freeze_frames={freeze_count} silence_gaps={len(silence_gaps)} "
        f"lufs={metrics.get('lufs')} duration={metrics.get('duration_fmt')} "
        f"resolution={metrics.get('resolution')}"
    )
    _preflight_log(f"{'PASS' if passed else 'FAIL'}" + (f" — {issues}" if issues else " — proceeding to grading"))

    return {"passed": passed, "issues": issues, "metrics": metrics}


def _apply_preflight_fixes(video_path: str, qc: dict):
    """Apply targeted fixes for each preflight issue type.

    Modifies video_path IN-PLACE (via atomic rename).
    """
    issues_str = " ".join(qc.get("issues", []))

    # ── Freeze frame fix ──────────────────────────────────────────────────
    # Root cause: data panels / social cards / signal scenes are visually static.
    # Ken Burns motion in assembler.py is the proper fix (per PIPELINE_LAWS).
    # Preflight applies a post-hoc Ken Burns crop as safety net.
    # noise=c0s=3 is BANNED per PIPELINE_LAWS (Gemini penalizes it).
    if "freeze_frames" in issues_str:
        freeze_count = qc.get("metrics", {}).get("freeze_frames", 0)
        logger.info(f"[PREFLIGHT FIX] Ken Burns re-encode to fix {freeze_count} freeze regions")
        tmp = video_path + ".freeze_fix.mp4"
        try:
            # Scale up 3% then crop back with 6s sin oscillation (30px H, 16px V)
            # Guarantees >=1px integer displacement per frame at 30fps
            r = subprocess.run(
                ["ffmpeg", "-y",
                 "-i", video_path,
                 "-vf", "mpdecimate=max=0:hi=64:lo=32:frac=0.33,setpts=N/FRAME_RATE/TB",
                 "-r", "30",
                 "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                 "-c:a", "copy",
                 tmp],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode == 0 and os.path.exists(tmp):
                # Verify the fix reduced freeze frames
                verify = subprocess.run(
                    ["ffmpeg", "-i", tmp, "-vf", "freezedetect=n=0.003:d=1.5",
                     "-f", "null", "-"],
                    capture_output=True, text=True, timeout=300,
                )
                remaining = len(_re.findall(r"freeze_start", verify.stderr))
                logger.info(f"[PREFLIGHT FIX] Freeze frames: {freeze_count} → {remaining}")
                if remaining < freeze_count:
                    os.replace(tmp, video_path)
                    logger.info("[PREFLIGHT FIX] Ken Burns freeze fix applied")
                else:
                    logger.warning("[PREFLIGHT FIX] Ken Burns did not reduce freezes — keeping original")
                    os.remove(tmp)
            elif os.path.exists(tmp):
                os.remove(tmp)
        except Exception as e:
            logger.warning(f"[PREFLIGHT FIX] Freeze frame fix failed: {e}")
            if os.path.exists(tmp):
                os.remove(tmp)

    # ── Silence gap fix ───────────────────────────────────────────────────
    if "silence_gaps" in issues_str:
        logger.info("[PREFLIGHT FIX] Filling silence gaps with fade bridge")
        tmp = video_path + ".silence_fix.mp4"
        try:
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", video_path,
                 "-c:v", "copy",
                 "-af", "silenceremove=stop_periods=-1:stop_duration=0.8:stop_threshold=-50dB,"
                        "apad=pad_dur=0.05",
                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                 "-movflags", "+faststart",
                 tmp],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0 and os.path.exists(tmp):
                os.replace(tmp, video_path)
                logger.info("[PREFLIGHT FIX] Silence gap fix complete")
            elif os.path.exists(tmp):
                os.remove(tmp)
        except Exception as e:
            logger.warning(f"[PREFLIGHT FIX] Silence fix failed: {e}")
            if os.path.exists(tmp):
                os.remove(tmp)

    # ── Loudness fix ──────────────────────────────────────────────────────
    if "lufs=" in issues_str or "true_peak=" in issues_str:
        logger.info("[PREFLIGHT FIX] Applying loudnorm to fix loudness")
        tmp = video_path + ".loudnorm_fix.mp4"
        try:
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", video_path,
                 "-c:v", "copy",
                 "-af", "alimiter=limit=0.891:level=false,loudnorm=I=-14:TP=-1.0:LRA=11:linear=true",
                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                 "-movflags", "+faststart",
                 tmp],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0 and os.path.exists(tmp):
                os.replace(tmp, video_path)
                logger.info("[PREFLIGHT FIX] Loudnorm fix complete")
            elif os.path.exists(tmp):
                os.remove(tmp)
        except Exception as e:
            logger.warning(f"[PREFLIGHT FIX] Loudnorm fix failed: {e}")
            if os.path.exists(tmp):
                os.remove(tmp)


def preflight_health_check():
    """Verify system health before render. Fail fast on critical issues."""
    issues = []

    # RAM check
    try:
        import psutil
        ram_free_gb = psutil.virtual_memory().available / (1024 ** 3)
        if ram_free_gb < 30:
            issues.append(f"RAM: only {ram_free_gb:.1f}GB free (need 30GB+)")
        else:
            logger.info(f"PREFLIGHT: RAM {ram_free_gb:.1f}GB free")
    except ImportError:
        pass  # psutil not available, skip

    # Kill zombie avatar_server
    try:
        result = subprocess.run(["pgrep", "-f", "avatar_server"], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split()
            subprocess.run(["kill", "-9"] + pids, capture_output=True)
            issues.append(f"KILLED: avatar_server zombie (PIDs: {pids})")
    except Exception:
        pass

    # Validate critical JSON files
    from validators import validate_json_file
    for path, expected, keys in [
        (os.path.join(BASE, "data", "used_clips.json"), dict, ["episodes"]),
    ]:
        _, errs = validate_json_file(path, expected, keys)
        issues.extend(errs)

    # Check GPU VRAM
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            free_mb = float(result.stdout.strip().split('\n')[0])
            if free_mb < 3000:
                issues.append(f"GPU: only {free_mb:.0f}MB VRAM free (need 3000MB+)")
            else:
                logger.info(f"PREFLIGHT: GPU {free_mb:.0f}MB VRAM free")
    except Exception:
        pass

    # Check API keys
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_elevenlabs = bool(os.environ.get("ELEVENLABS_API_KEY"))
    if not has_anthropic and not has_elevenlabs:
        issues.append("No API keys (ANTHROPIC_API_KEY, ELEVENLABS_API_KEY) in environment")

    # Report
    for issue in issues:
        logger.warning(f"PREFLIGHT: {issue}")
    if not issues:
        logger.info("PREFLIGHT: All checks passed")

    # Only fail on truly critical issues
    critical = [i for i in issues if "RAM:" in i or "No API keys" in i]
    if critical:
        raise RuntimeError(f"PREFLIGHT FAILED: {'; '.join(critical)}")

    return issues


def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
                 fast_test: bool = False, reuse_content: bool = False,
                 no_resume: bool = False) -> bool:
    # Fast test implies test + skip-scan
    if fast_test:
        test_mode = True
        skip_scan = True

    # P1 Fix 8: VRAM cleanup between renders
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.info("VRAM cleared")
    except Exception:
        pass

    # P0 Fix 3: Check checkpoint for resume
    if test_mode or fast_test or no_resume:
        # Never resume in test mode or when --no-resume is set — always fresh render
        resume_step = 0
        if no_resume:
            logger.info("CHECKPOINT RESUME SKIPPED: --no-resume flag set")
        else:
            logger.info("CHECKPOINT RESUME SKIPPED: test mode — always fresh render")
        _clear_checkpoint()
    else:
        resume_step, resume_data = _read_checkpoint()
        if resume_step >= 4:
            logger.info(f"CHECKPOINT RESUME: last completed step={resume_step}, checking for resumable state")
            # Verify code hasn't changed since checkpoint
            try:
                with open(CHECKPOINT_FILE) as _cf:
                    _cp_data = json.load(_cf)
                saved_code_hash = _cp_data.get("code_hash", "")
            except Exception:
                saved_code_hash = ""
            current_code_hash = _code_hash()
            if saved_code_hash and saved_code_hash != current_code_hash:
                logger.info(f"  Code changed since checkpoint (saved={saved_code_hash} current={current_code_hash}) — starting fresh")
                resume_step = 0
                _clear_checkpoint()
            else:
                # Verify clips still exist before resuming
                today_dir = os.path.join(BASE, "output", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                clips_dir = os.path.join(today_dir, "clips")
                if os.path.exists(clips_dir) and os.listdir(clips_dir):
                    skip_scan = True
                    logger.info(f"  Clips exist at {clips_dir} — will resume from step {resume_step + 1}")
                else:
                    logger.info("  No clips found — starting fresh")
                    resume_step = 0
        else:
            resume_step = 0

    # Wipe TTS cache before each run to prevent stale audio
    # CONTENT LOCK LAW: skip wipe when reusing locked content
    tts_cache = os.path.join(BASE, "tts_cache")
    if not reuse_content:
        shutil.rmtree(tts_cache, ignore_errors=True)
        os.makedirs(tts_cache, exist_ok=True)
        logger.info("TTS cache wiped")
    else:
        os.makedirs(tts_cache, exist_ok=True)
        logger.info("TTS cache preserved (reuse-content mode)")

    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y%m%d")
    time_str = ts.strftime("%Y%m%d_%H%M%S")

    if test_mode:
        run_dir = os.path.join(BASE, "output", f"test_{time_str}")
    else:
        run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))

    os.makedirs(run_dir, exist_ok=True)
    final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
    timing = {}
    t_pipeline_start = time.time()
    clips = []  # initialized early; set properly in content fetch path
    sel_path = os.path.join(run_dir, "selections.json")
    script_path = os.path.join(run_dir, "script.json")

    # Ensure music directory exists
    ensure_music_dir()

    # Log feature flags at startup
    flags = load_flags()
    logger.info(f"Feature flags: {json.dumps(flags)}")

    # ── PREFLIGHT HEALTH CHECK ─────────────────────────────────────────
    try:
        _preflight_issues = preflight_health_check()
    except RuntimeError as e:
        logger.critical(f"PREFLIGHT ABORTED: {e}")
        return False

    # Telegram alert at pipeline start
    if is_enabled("telegram_alerts"):
        alert_pipeline_start(date_str, test_mode)

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
    mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
    print(f"  {mode_label}Run {time_str}")
    print(f"  Output: {run_dir}")
    print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
    print("=" * 70)


    # ── CONTENT LOCK: reuse locked content from previous iteration ────────
    if reuse_content:
        locked_dir = os.path.join(run_dir, "locked_content")
        locked_script = os.path.join(locked_dir, "script.json")
        locked_clips = os.path.join(locked_dir, "clips")
        locked_tts = os.path.join(locked_dir, "tts")
        locked_audio = os.path.join(locked_dir, "audio_data.json")
        locked_meta = os.path.join(locked_dir, "meta.json")

        if not os.path.exists(locked_script):
            logger.error(f"REUSE MODE FAILED: no locked content at {locked_dir}")
            print(f"  [FAIL] No locked content found at {locked_dir}")
            return False

        logger.info(f"REUSE MODE: skipping content fetch, using locked content from {locked_dir}")
        print(f"\n  *** CONTENT LOCK ACTIVE — reusing locked content from {locked_dir} ***")
        print("  Skipping Steps 1-6 (fetch/script/TTS)")

        from validators import validate_json_file
        script, script_errs = validate_json_file(locked_script, dict, ["dialogue"])
        for e in script_errs:
            logger.warning(f"REUSE SCRIPT: {e}")
        audio_data, audio_errs = validate_json_file(locked_audio, dict, ["lines"])
        for e in audio_errs:
            logger.warning(f"REUSE AUDIO: {e}")

        # Load metadata (btc_price, music paths)
        meta = {}
        if os.path.exists(locked_meta):
            with open(locked_meta) as f:
                meta = json.load(f)
        btc_price = meta.get("btc_price", "$0")
        music_bed = meta.get("music_bed", "")
        intro_music = meta.get("intro_music", "")

        # Build extracted_clips dict from locked clips directory
        extracted_clips = {}
        if os.path.exists(locked_clips):
            import glob as _lc_glob
            for clip_file in sorted(_lc_glob.glob(os.path.join(locked_clips, "*.mp4"))):
                fname = os.path.basename(clip_file)
                try:
                    rank = int(fname.split("_")[1])
                except (IndexError, ValueError):
                    rank = len(extracted_clips) + 1
                extracted_clips[rank] = {
                    "path": clip_file,
                    "video_id": fname,
                    "channel": "",
                    "duration": 0,
                }

        # Restore TTS cache from locked copy
        if os.path.exists(locked_tts):
            for tts_file in os.listdir(locked_tts):
                src = os.path.join(locked_tts, tts_file)
                dst = os.path.join(tts_cache, tts_file)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)

        # ── PARTS CACHE: restore rendered parts from locked_content ──────
        if is_enabled("cache_rendered_parts"):
            cached_parts = os.path.join(locked_dir, "parts")
            cached_hash_file = os.path.join(locked_dir, "parts_hash.txt")
            live_parts = os.path.join(run_dir, "work")
            # Verify script hash matches before restoring
            current_hash = hashlib.md5(json.dumps(script, sort_keys=True).encode()).hexdigest()
            hash_ok = False
            if os.path.exists(cached_hash_file):
                with open(cached_hash_file) as hf:
                    saved_hash = hf.read().strip()
                hash_ok = (saved_hash == current_hash)
                if not hash_ok:
                    logger.warning(f"PARTS CACHE HASH MISMATCH: saved={saved_hash[:12]} current={current_hash[:12]} — skipping cache")

            # Verify clip file count matches
            clips_ok = True
            if hash_ok and os.path.exists(cached_parts):
                locked_clip_names = set()
                if os.path.exists(locked_clips):
                    locked_clip_names = set(os.listdir(locked_clips))
                current_clip_names = set()
                clip_dir_check = os.path.join(run_dir, "clips")
                if os.path.exists(clip_dir_check):
                    current_clip_names = set(os.listdir(clip_dir_check))
                if locked_clip_names != current_clip_names:
                    clips_ok = False
                    logger.warning(f"PARTS CACHE CLIP MISMATCH: locked={len(locked_clip_names)} current={len(current_clip_names)} — skipping cache")

            if hash_ok and clips_ok and os.path.exists(cached_parts) and os.listdir(cached_parts):
                # ffprobe integrity check on each cached part
                all_parts_valid = True
                for pf in os.listdir(cached_parts):
                    pf_path = os.path.join(cached_parts, pf)
                    if os.path.getsize(pf_path) == 0:
                        logger.warning(f"PARTS CACHE CORRUPT: {pf} is 0 bytes — skipping cache")
                        all_parts_valid = False
                        break
                    try:
                        probe = subprocess.run(
                            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "csv=p=0", pf_path],
                            capture_output=True, text=True, timeout=10)
                        dur = float(probe.stdout.strip() or "0")
                        if dur < 0.1:
                            logger.warning(f"PARTS CACHE CORRUPT: {pf} duration={dur:.3f}s — skipping cache")
                            all_parts_valid = False
                            break
                    except Exception as e:
                        logger.warning(f"PARTS CACHE PROBE FAILED: {pf} — {e} — skipping cache")
                        all_parts_valid = False
                        break

                if all_parts_valid:
                    os.makedirs(live_parts, exist_ok=True)
                    shutil.copytree(cached_parts, live_parts, dirs_exist_ok=True)
                    part_count = len([f for f in os.listdir(live_parts) if f.startswith("part_")])
                    logger.info(f"PARTS RESTORED: {part_count} cached parts → skipping assembly")
                    os.makedirs(os.path.join(run_dir, ".cache_flags"), exist_ok=True)
                    open(os.path.join(run_dir, ".cache_flags", "parts_cached"), "w").close()
                else:
                    logger.info("PARTS CACHE INVALID — running full assembly")
            else:
                logger.info("No valid cached parts found — running full assembly")

        dialogue = script.get("dialogue", [])
        print(f"  Loaded: script ({len(dialogue)} dialogue entries), "
              f"{len(extracted_clips)} clips, BTC={btc_price}")

    # ── Steps 1-6: Content generation (skipped in reuse mode) ─────────────
    if not reuse_content:
        # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
        print("\n[STEP 1/12] FETCHING BTC PRICE...")
        t0 = time.time()
        btc_price = get_btc_price()
        print(f"  BTC: {btc_price}")
        timing["1_price"] = round(time.time() - t0, 2)
        write_render_context(1, "ok", btc_price=btc_price,
                             stage_data={"btc_price": btc_price, "run_dir": run_dir})

        # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
        print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
        t0 = time.time()
        if skip_scan:
            # Load cached transcripts from transcript dir
            import glob
            transcript_dir = os.path.join(BASE, "transcripts")
            videos = []
            for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:60]:
                with open(tf) as f:
                    data = json.load(f)
                    videos.append({
                        "video_id": data.get("video_id", ""),
                        "title": data.get("title", ""),
                        "channel": data.get("channel", ""),
                        "duration": data.get("duration", 0),
                        "upload_date": "",
                        "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
                        "transcript_text": data.get("text", ""),
                        "timestamped_text": data.get("timestamped_text", ""),
                    })
            print(f"  Loaded {len(videos)} cached transcripts")
        else:
            whisper_model = "tiny" if test_mode else "base"
            videos = scan_all_channels(model_size=whisper_model)
            print(f"  Scanned: {len(videos)} videos with transcripts")
        timing["2_scan"] = round(time.time() - t0, 2)
        write_render_context(2, "ok")

        if not videos:
            print("\n  [FAIL] No videos found — cannot produce episode")
            _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
            if is_enabled("telegram_alerts"):
                alert_pipeline_failure(date_str, "scan", "No videos found")
            return False

        # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
        if fast_test:
            print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
            t0 = time.time()
            # Build minimal selections from cached videos without calling Claude
            fast_clips = []
            for i, v in enumerate(videos[:2], 1):
                text = v.get("transcript_text", "")
                fast_clips.append({
                    "rank": i,
                    "video_id": v["video_id"],
                    "channel": v.get("channel", ""),
                    "title": v.get("title", ""),
                    "quote": text[:100] if text else "No transcript",
                    "why": "fast-test auto-select",
                    "start_seconds": 60,
                    "end_seconds": 90,
                })
            selections = {"clips": fast_clips}
            clips = fast_clips
            print(f"  Auto-selected: {len(clips)} clips (no API call)")
            timing["3_select"] = round(time.time() - t0, 2)
        else:
            print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude → Qwen → fallback)...")
            t0 = time.time()
            selections = _retry_select_clips(videos)
            clips = selections.get("clips", [])
            print(f"  Selected: {len(clips)} clips")
            for c in clips:
                print(f"    #{c.get('rank', 0)}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
            timing["3_select"] = round(time.time() - t0, 2)

        if not clips:
            print("\n  [FAIL] No clips selected — cannot produce episode")
            _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
            if is_enabled("telegram_alerts"):
                alert_pipeline_failure(date_str, "select", "No clips selected")
            return False

        # V4.3 FIX 3: Test mode minimum 3 clips (was 2) for adequate duration
        if not fast_test and test_mode and len(clips) > 3:
            selections["clips"] = clips[:3]
            clips = selections["clips"]
            print(f"  [test] Truncated to {len(clips)} clips")

        # Save selections
        sel_path = os.path.join(run_dir, "selections.json")
        with open(sel_path, "w") as f:
            json.dump(selections, f, indent=2)
        write_render_context(3, "ok",
                             stage_data={"selections_path": sel_path,
                                         "clip_count": len(clips)})

        # ── Step 3b: Select independent montage clips (Qwen, free) ──────────
        print("\n[STEP 3b] SELECTING MONTAGE CLIPS (local Qwen)...")
        try:
            from clip_selector import select_montage_clips
            montage_selections = select_montage_clips(videos)
            montage_clips_sel = montage_selections.get("clips", [])
            montage_sel_path = os.path.join(run_dir, "montage_selections.json")
            with open(montage_sel_path, "w") as f:
                json.dump(montage_selections, f, indent=2)
            print(f"  Montage: {len(montage_clips_sel)} independent clips selected")
        except Exception as e:
            print(f"  Montage selection failed ({e}) — montage will reuse Pulse Check clips")
            montage_selections = None

        # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
        print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
        t0 = time.time()
        # FIX 2: Wipe clips/ dir completely to prevent stale files from prior renders
        clip_dir = os.path.join(run_dir, "clips")
        if os.path.exists(clip_dir):
            shutil.rmtree(clip_dir)
            logger.info(f"  Wiped stale clips dir: {clip_dir}")
        os.makedirs(clip_dir, exist_ok=True)
        # Also wipe stale pip_preview files from work dir
        work_dir = os.path.join(run_dir, "work")
        if os.path.exists(work_dir):
            import glob as _pip_glob
            for stale_pip in _pip_glob.glob(os.path.join(work_dir, "pip_preview_*.mp4")):
                try:
                    os.remove(stale_pip)
                except OSError:
                    pass
            logger.info("  Wiped stale pip_preview files from work/")
        extracted_clips = _retry_extract_clips(selections, clip_dir)
        print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")

        # ── Quality-aware fallback: retry with ranked alternates ──────────
        if not test_mode and not fast_test and len(extracted_clips) < 5:
            used_video_ids = {info["video_id"] for info in extracted_clips.values()}
            used_channels = {info["channel"] for info in extracted_clips.values()}
            tried_video_ids = {c["video_id"] for c in clips} | used_video_ids

            remaining = [v for v in videos
                         if v["video_id"] not in tried_video_ids
                         and v.get("channel", "") not in used_channels]

            if remaining:
                need = 5 - len(extracted_clips)
                logger.info(
                    f"[extractor] Only {len(extracted_clips)}/5 clips passed quality "
                    f"— selecting fallbacks from {len(remaining)} candidates (need {need})"
                )
                fallback_sel = select_clips(remaining)
                fallback_clips = fallback_sel.get("clips", [])

                max_rank = max(extracted_clips.keys()) if extracted_clips else 0
                for fc in fallback_clips:
                    if len(extracted_clips) >= 5:
                        break
                    fc_ch = fc.get("channel", "")
                    fc_vid = fc.get("video_id", "")
                    if fc_ch in used_channels or fc_vid in tried_video_ids:
                        continue
                    max_rank += 1
                    fc["rank"] = max_rank
                    logger.info(
                        f"[extractor] Clip failed quality — trying fallback candidate "
                        f"#{max_rank} [{fc_ch}] from selections"
                    )
                    fb_result = extract_all({"clips": [fc]}, clip_dir)
                    if fb_result:
                        for r, info in fb_result.items():
                            extracted_clips[r] = info
                            used_video_ids.add(info["video_id"])
                            used_channels.add(info["channel"])
                            tried_video_ids.add(fc_vid)
                            selections["clips"].append(fc)
                            logger.info(
                                f"[extractor] Fallback clip #{r} passed quality — "
                                f"{info['channel']} ({info['duration']:.1f}s)"
                            )
                    else:
                        tried_video_ids.add(fc_vid)
                        logger.warning(
                            f"[extractor] Fallback [{fc_ch}] also failed quality — trying next"
                        )

                # Update clips list and re-save selections
                clips = selections.get("clips", [])
                with open(sel_path, "w") as f:
                    json.dump(selections, f, indent=2)
                logger.info(f"[extractor] After fallback: {len(extracted_clips)}/5 clips")
            else:
                logger.warning("[extractor] No fallback candidates — all channels/videos exhausted")

        if not test_mode:
            _unique_ch = len({info.get("channel", f"unk_{i}") for i, info in enumerate(extracted_clips.values())})
            if len(extracted_clips) < 3 or _unique_ch < 2:
                logger.critical(
                    f"[PIPELINE] HARD FAIL: Need 5 clips from 5 unique channels, "
                    f"got {len(extracted_clips)} clips from {_unique_ch} channels."
                )
                return False
        for rank, info in sorted(extracted_clips.items()):
            print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
        timing["4_extract"] = round(time.time() - t0, 2)
        write_render_context(4, "ok",
                             stage_data={"extracted_clip_ranks": list(extracted_clips.keys()),
                                         "clip_dir": clip_dir})

        # ── Step 4m: Extract montage clips ───────────────────────────────────
        if montage_selections and montage_selections.get("clips"):
            print("\n[STEP 4m] EXTRACTING MONTAGE CLIPS...")
            try:
                extract_montage_all(montage_selections, clip_dir)
                print(f"  Montage clips extracted to {clip_dir}")
            except Exception as e:
                print(f"  Montage extraction failed ({e}) — skipping")

        if not extracted_clips:
            print("\n  [FAIL] No clips extracted — cannot produce episode")
            _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
            if is_enabled("telegram_alerts"):
                alert_pipeline_failure(date_str, "extract", "No clips extracted")
            return False

        # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
        import glob as _glob
        import random as _random

        def classify_episode_mood(script_text: str) -> str:
            """Classify episode mood from clip quotes."""
            moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
            lower = script_text.lower()
            if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
                moods["tense"] += 3
            if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
                moods["confident"] += 3
            if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
                moods["contemplative"] += 2
            if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
                moods["upbeat"] += 2
            if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
                moods["edge"] += 2
            best = max(moods, key=moods.get)
            return best if moods[best] > 0 else "confident"

        def select_music_bed(mood: str, music_dir: str) -> str:
            # Sprint 1.10: Randomize music, avoid repeating last track
            last_track_file = os.path.join(music_dir, ".last_track.txt")
            last_track = ""
            if os.path.exists(last_track_file):
                try:
                    last_track = open(last_track_file).read().strip()
                except Exception:
                    pass

            tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
            if not tracks:
                tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
            if not tracks:
                # Get all tracks except reserved ones
                all_tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
                tracks = [t for t in all_tracks
                          if os.path.basename(t) not in ("pp_outro.mp3", "pp_background.mp3",
                                                           "pp_intro.mp3", "pp_transition.mp3")]
            if not tracks:
                return ""

            # Avoid repeating last track
            if last_track and len(tracks) > 1:
                tracks = [t for t in tracks if os.path.basename(t) != last_track] or tracks

            # LOCKED: confident_02.mp3 is the signature Protocol Pulse soundtrack
            locked_track = os.path.join(music_dir, 'confident_02.mp3')
            if os.path.exists(locked_track):
                chosen = locked_track
            else:
                chosen = _random.choice(tracks)
            try:
                with open(last_track_file, "w") as f:
                    f.write(os.path.basename(chosen))
            except Exception:
                pass
            return chosen

        def select_intro_music(music_dir: str) -> str:
            tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
            return _random.choice(tracks) if tracks else ""

        # Classify mood from clip quotes
        clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
        episode_mood = classify_episode_mood(clip_quotes)
        music_dir = os.path.join(BASE, "assets", "music")
        music_bed = select_music_bed(episode_mood, music_dir)
        intro_music = select_intro_music(music_dir)
        print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")

        # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
        live_context = ""
        live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
        try:
            if os.path.exists(live_signals_path):
                with open(live_signals_path) as f:
                    live_data = json.load(f)
                from datetime import timezone as _tz
                now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
                active_streams = []
                for s in live_data.get("live_streams", []):
                    # Only include streams from last 6 hours
                    started = s.get("started_at", "")
                    try:
                        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                        age_hours = (now - started_dt).total_seconds() / 3600
                        if age_hours > 6:
                            continue
                    except (ValueError, AttributeError):
                        continue
                    source = s.get("source", "youtube_live")
                    channel = s.get("channel", "unknown")
                    title = s.get("title", "")
                    topics = ", ".join(s.get("topics", []))
                    sentiment = s.get("current_sentiment", 50)
                    sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
                    active_streams.append(
                        f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
                    )
                if active_streams:
                    live_context = "\n".join(active_streams)
                    print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
                    for line in active_streams:
                        print(f"    {line}")
                else:
                    print("  Live signals: no active streams in last 6 hours")
        except Exception as e:
            logger.warning(f"Live signals read failed: {e}")

        # ── Step 5a: Fetch social posts + Space Tap BEFORE script generation ──
        # Social posts: fetch once, sort by likes desc, pass to script_writer
        sorted_social = []
        try:
            from utils.social_fetcher import get_todays_social_posts
            sorted_social = get_todays_social_posts(max_posts=5)
            if sorted_social:
                sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
                # Assign deterministic seg_id for tweet↔narration binding
                import hashlib as _seg_hashlib
                for si, sp in enumerate(sorted_social):
                    raw = sp.get("tweet_url") or sp.get("url") or sp.get("text", "")
                    sp["seg_id"] = f"tweet_{_seg_hashlib.md5(raw.encode()).hexdigest()[:8]}_{si}"
                    sp["display_order"] = si
                    logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} [seg_id={sp['seg_id']}] — {sp.get('text', '')[:40]}")
        except Exception as e:
            logger.warning(f"Social posts fetch failed: {e}")

        # Space Tap: fetch X Spaces clips BEFORE script generation so LLM can write dialogue
        print("[STEP 5a] SPACE TAP -- LIVE X SPACES INTERCEPT...")
        try:
            import importlib.util
            _spaces_scraper_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "x_spaces_scraper", "scraper.py"
            )
            if os.path.exists(_spaces_scraper_path):
                _spec = importlib.util.spec_from_file_location("x_spaces_scraper", _spaces_scraper_path)
                _mod = importlib.util.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                # Hard 120s timeout — Whisper can hang forever without this
                import threading as _st_thread
                _st_result = [None]
                def _fetch_spaces(): _st_result[0] = _mod.get_best_space_clips(max_clips=3)
                _st_t = _st_thread.Thread(target=_fetch_spaces, daemon=True)
                _st_t.start(); _st_t.join(timeout=120)
                if _st_t.is_alive():
                    logger.warning("[SpaceTap] get_best_space_clips timed out (120s) — skipping")
                    _st = None
                else:
                    _st = _st_result[0]
                if _st and _st.get("clips"):
                    selections["space_tap_clips"] = _st["clips"]
                    print(f"  Space Tap: {len(_st['clips'])} clips from {_st.get('spaces_count', 0)} spaces")
                else:
                    print("  Space Tap: no live spaces — segment skipped")
            else:
                print("  Space Tap: scraper not installed — segment skipped")
        except Exception as _ste:
            logger.error(f"Space Tap fetch error: {type(_ste).__name__}: {_ste}")
            print(f"  Space Tap: skipped ({_ste})")

        # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
        if fast_test:
            print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
            t0 = time.time()
            script = _build_fast_test_script(extracted_clips, btc_price)
            timing["5_script"] = round(time.time() - t0, 2)
        else:
            print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
            t0 = time.time()
            script = generate_from_clips(selections, btc_price=btc_price,
                                         live_context=live_context,
                                         social_posts_sorted=sorted_social)
            timing["5_script"] = round(time.time() - t0, 2)

        # Attach social posts to script for assembler (single source of truth)
        if sorted_social:
            script["social_posts"] = sorted_social

        # Re-read dialogue AFTER all mutations (Space Tap entries may be in script)
        dialogue = script.get("dialogue", [])
        # V4.3 FIX 1: Accept both old (host:2) and new (type-only) format
        # script_writer._extract_segment_tags defaults missing host to 2, so this catches both
        speech_lines = [d for d in dialogue if d.get("host") not in ("CLIP", "SPACE_CLIP", None)]
        clip_markers = [d for d in dialogue if d.get("host") in ("CLIP", "SPACE_CLIP")]
        social_seg_count = sum(1 for d in dialogue if d.get("type") == "social_segment")

        # V4.2 FIX 7: Enforce "What Bitcoin Internet Is Saying" — inject if social data exists but segment missing
        if sorted_social and social_seg_count == 0:
            logger.warning(f"[producer] V4.2 FIX 7: {len(sorted_social)} social posts but 0 social_segment entries — injecting")
            # Insert social segments before the final wrap
            wrap_idx = None
            for _wi in range(len(dialogue) - 1, -1, -1):
                if dialogue[_wi].get("type") == "wrap":
                    wrap_idx = _wi
                    break
            inject_entries = []
            for si, sp in enumerate(sorted_social[:3]):
                handle = sp.get("handle", "unknown")
                text_preview = sp.get("text", "")[:200]
                inject_entries.append({
                    "host": 2,
                    "text": f"{handle} posted — {text_preview}. The signal is clear.",
                    "type": "social_segment",
                    "headline": "SIGNAL FROM THE FIELD",
                })
            if wrap_idx is not None:
                for ji, je in enumerate(inject_entries):
                    dialogue.insert(wrap_idx + ji, je)
            else:
                dialogue.extend(inject_entries)
            social_seg_count = len(inject_entries)
            logger.info(f"[producer] V4.2 FIX 7: Injected {social_seg_count} social_segment entries")
        space_tap_count = sum(1 for d in dialogue if d.get("host") == "SPACE_CLIP"
                             or (d.get("type") or "").startswith("space_tap"))
        print(f"  Title: {script.get('episode_title', 'Untitled')}")
        print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
        print(f"  SOCIAL segments: {social_seg_count} (input tweets: {len(sorted_social)})")
        print(f"  SPACE TAP entries: {space_tap_count} (input clips: {len(selections.get('space_tap_clips', []))})")
        if sorted_social and social_seg_count == 0:
            logger.error("SOCIAL SEGMENT ABSENT despite having tweet data — check script_writer enforcement")
        if selections.get("space_tap_clips") and space_tap_count == 0:
            logger.error("SPACE TAP ABSENT despite having clip data — check script_writer enforcement")

        # Save script
        script_path = os.path.join(run_dir, "script.json")
        with open(script_path, "w") as f:
            json.dump(script, f, indent=2)

        write_render_context(5, "ok",
                             episode_title=script.get("episode_title", ""),
                             social_posts_count=len(sorted_social),
                             space_tap_available=bool(selections.get("space_tap_clips")),
                             stage_data={"script_path": script_path,
                                         "dialogue_count": len(dialogue)})

        # ── Step 5b: SCRIPT QUALITY GATE (V4 audit consensus) ────────────────
        print("\n[STEP 5b] SCRIPT QUALITY GATE...")
        script_issues = []

        # Check: has cold open?
        if not any(d.get("type") == "cold_open" for d in dialogue):
            script_issues.append("Missing cold open")

        # Check: has signoff?
        if not any("stay sovereign" in d.get("text", "").lower() for d in dialogue):
            script_issues.append("Missing 'Stay sovereign' signoff")

        # Check: no banned phrases
        banned = ["let's dive in", "great point", "it's worth noting", "interestingly",
                  "without further ado", "in today's episode", "let's break this down"]
        for d in dialogue:
            text_lower = d.get("text", "").lower()
            for phrase in banned:
                if phrase in text_lower:
                    script_issues.append(f"Banned phrase: '{phrase}'")

        # V4.3 FIX 2: Tightened from 4→3 sentences max, auto-split if >3
        _split_inserts = []  # (index, new_entry) pairs for deferred insert
        for di, d in enumerate(dialogue):
            if d.get("type") in ("setup", "react", "cold_open"):
                text = d.get("text", "")
                sentences = text.count('.') + text.count('!') + text.count('?')
                if sentences > 3:
                    # Split: keep first 2 sentences in original, rest in new segment
                    import re as _split_re
                    parts = _split_re.split(r'(?<=[.!?])\s+', text, maxsplit=2)
                    if len(parts) >= 3:
                        d["text"] = parts[0] + " " + parts[1]
                        overflow = " ".join(parts[2:])
                        _split_inserts.append((di + 1, {
                            "host": d.get("host", 2),
                            "text": overflow,
                            "type": d.get("type"),
                            "clip_rank": d.get("clip_rank", 0),
                            "headline": d.get("headline", ""),
                        }))
                        script_issues.append(f"Segment split: {sentences} sentences → 2 + remainder")
                    else:
                        script_issues.append(f"Segment too long: {sentences} sentences (max 3)")

        # V4.3 FIX 2: Apply deferred segment splits
        for offset, (idx, new_entry) in enumerate(_split_inserts):
            dialogue.insert(idx + offset, new_entry)

        if script_issues:
            print(f"  SCRIPT GATE FAILED: {script_issues}")
            if not test_mode and not fast_test:
                print("  Regenerating script with stricter prompt...")
                script = generate_from_clips(selections, btc_price=btc_price,
                                             live_context=live_context,
                                             social_posts_sorted=sorted_social)
                dialogue = script.get("dialogue", [])
                speech_lines = [d for d in dialogue if d.get("host") not in ("CLIP", "SPACE_CLIP", None)]
                # Re-save script
                with open(script_path, "w") as f:
                    json.dump(script, f, indent=2)
        else:
            print("  SCRIPT GATE PASSED")

        # V4.3 FIX 8: HARDCODED "Stay sovereign" signoff — always ensure it's the LAST segment
        if not any("stay sovereign" in d.get("text", "").lower() for d in dialogue):
            logger.warning("[producer] SIGNOFF MISSING — force-appending hardcoded signoff")
            dialogue.append({
                "host": 2,
                "type": "signoff",
                "text": "Stay sovereign. This has been Protocol Pulse.",
                "headline": "STAY SOVEREIGN",
            })
        else:
            # Ensure signoff is LAST — move it if not already at the end
            for si in range(len(dialogue) - 1, -1, -1):
                if "stay sovereign" in dialogue[si].get("text", "").lower():
                    if si != len(dialogue) - 1:
                        signoff = dialogue.pop(si)
                        dialogue.append(signoff)
                        logger.info("[producer] Moved signoff to last position")
                    break
        script["dialogue"] = dialogue
        with open(script_path, "w") as f:
            json.dump(script, f, indent=2)

        # Strip seg_id prefix from social_segment narration before TTS (binding tag, not spoken)
        # Keep originals in dialogue for assembler ID-binding — only strip the TTS copy
        import re as _strip_re
        _seg_id_originals = {}
        for _di, _entry in enumerate(dialogue):
            if _entry.get("type") == "social_segment" and _strip_re.search(r'^\[ID:tweet_[a-f0-9]+_\d+\]', _entry.get("text", "")):
                _seg_id_originals[_di] = _entry["text"]
                _entry["text"] = _strip_re.sub(r'^\[ID:tweet_[a-f0-9]+_\d+\]\s*', '', _entry["text"])

        # ── Step 6: TTS ───────────────────────────────────────────────────────
        print("\n[STEP 6/12] GENERATING PBX NARRATION AUDIO (ElevenLabs)...")
        t0 = time.time()
        audio_dir = os.path.join(run_dir, "audio")
        audio_data = _retry_tts(dialogue, audio_dir)

        # Restore seg_id prefixes after TTS so assembler can read them for card binding
        for _di, _orig_text in _seg_id_originals.items():
            dialogue[_di]["text"] = _orig_text
        successful = sum(1 for l in audio_data.get("lines", [])
                         if l.get("path") and os.path.exists(l.get("path", "")))
        print(f"  Audio: {successful}/{len(speech_lines)} lines")
        print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
        timing["6_tts"] = round(time.time() - t0, 2)
        write_render_context(6, "ok", tts_provider="elevenlabs",
                             stage_data={"audio_dir": audio_dir,
                                         "tts_lines": successful})

        # ── Step 6b: BUILD MANIFEST ─────────────────────────────────────────
        print("\n[STEP 6b/12] BUILDING EPISODE MANIFEST...")
        t0 = time.time()
        try:
            from manifest_builder import build_manifest
            episode_manifest = build_manifest(
                script, audio_data, extracted_clips, run_dir,
                music_bed=music_bed, btc_price=btc_price,
            )
            print(f"  Manifest: {episode_manifest.get('total_segments', 0)} segments, "
                  f"~{episode_manifest.get('total_duration_estimate', 0):.0f}s estimated")
        except Exception as e:
            logger.warning(f"Manifest build failed (non-blocking): {e}")
            episode_manifest = {}
        timing["6b_manifest"] = round(time.time() - t0, 2)

        # ── Step 6c: PREFLIGHT CHECK ─────────────────────────────────────────
        manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
        if os.path.exists(manifest_json_path):
            print("\n[STEP 6c/12] PREFLIGHT QC CHECK...")
            t0 = time.time()
            try:
                from qc_pipeline import preflight_check
                pf_passed, pf_errors, pf_warnings = preflight_check(manifest_json_path)
                print(f"  Preflight: {'PASS' if pf_passed else 'FAIL'} — "
                      f"{len(pf_errors)} errors, {len(pf_warnings)} warnings")
            except Exception as e:
                logger.warning(f"Preflight check failed (non-blocking): {e}")
            timing["6c_preflight"] = round(time.time() - t0, 2)


        # ── CONTENT LOCK: save content for future iterations ──────────────
        locked_dir = os.path.join(run_dir, "locked_content")
        os.makedirs(locked_dir, exist_ok=True)
        script_lock_src = os.path.join(run_dir, "script.json")
        if os.path.exists(script_lock_src):
            shutil.copy2(script_lock_src, os.path.join(locked_dir, "script.json"))
        clip_dir = os.path.join(run_dir, "clips")
        if os.path.exists(clip_dir):
            shutil.copytree(clip_dir, os.path.join(locked_dir, "clips"), dirs_exist_ok=True)
        if os.path.exists(tts_cache) and os.listdir(tts_cache):
            shutil.copytree(tts_cache, os.path.join(locked_dir, "tts"), dirs_exist_ok=True)
        # Save audio_data for reuse
        with open(os.path.join(locked_dir, "audio_data.json"), "w") as f:
            json.dump(audio_data, f, indent=2)
        # Save metadata
        with open(os.path.join(locked_dir, "meta.json"), "w") as f:
            json.dump({"btc_price": btc_price, "music_bed": music_bed,
                        "intro_music": intro_music}, f, indent=2)
        logger.info(f"CONTENT LOCKED to {locked_dir} — subsequent iterations will reuse this")

    # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
    parts_cached_flag = os.path.join(run_dir, ".cache_flags", "parts_cached")
    if is_enabled("cache_rendered_parts") and os.path.exists(parts_cached_flag):
        # PARTS CACHE HIT — skip full assembly, go straight to final concat
        print("\n[STEP 7/12] PARTS CACHE HIT — skipping assembly, concatenating cached parts...")
        t0 = time.time()
        work_dir = os.path.join(run_dir, "work")
        cached_part_files = sorted([
            os.path.join(work_dir, f)
            for f in os.listdir(work_dir)
            if f.startswith("part_") and f.endswith(".mp4")
        ])
        logger.info(f"PARTS CACHE HIT: {len(cached_part_files)} parts → concatenating directly")
        os.makedirs(os.path.dirname(os.path.abspath(final_video)), exist_ok=True)
        result = concatenate_parts(cached_part_files, final_video)
        timing["7_assemble"] = round(time.time() - t0, 2)
        logger.info(f"PARTS CACHE CONCAT: {timing['7_assemble']:.1f}s (vs ~90min full assembly)")
    else:
        print("\n[STEP 7/12] ASSEMBLING VIDEO...")
        t0 = time.time()
        result = assemble_episode(script, audio_data, extracted_clips, final_video,
                                  btc_price=btc_price, music_bed=music_bed,
                                  intro_music=intro_music)
        timing["7_assemble"] = round(time.time() - t0, 2)

        # ── PARTS CACHE: save rendered parts after successful assembly ────
        if is_enabled("cache_rendered_parts") and result and os.path.exists(final_video):
            locked_dir = os.path.join(run_dir, "locked_content")
            work_dir = os.path.join(run_dir, "work")
            if os.path.exists(work_dir):
                part_files = [f for f in os.listdir(work_dir) if f.startswith("part_") and f.endswith(".mp4")]
                if part_files:
                    parts_dst = os.path.join(locked_dir, "parts")
                    os.makedirs(parts_dst, exist_ok=True)
                    for pf in part_files:
                        shutil.copy2(os.path.join(work_dir, pf), os.path.join(parts_dst, pf))
                    # Save script hash for verification on restore
                    script_hash = hashlib.md5(json.dumps(script, sort_keys=True).encode()).hexdigest()
                    with open(os.path.join(locked_dir, "parts_hash.txt"), "w") as hf:
                        hf.write(script_hash)
                    logger.info(f"PARTS CACHED: {len(part_files)} parts → {parts_dst} (hash={script_hash[:12]})")

    if not result or not os.path.exists(final_video):
        print("\n  [FAIL] Assembly failed")
        write_render_context(7, "fail", error="Video assembly failed or no output file")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
        return False
    write_render_context(7, "ok")

    # ── Step 7a: DURATION HARD CAP (15 min = 900s) ──────────────────────
    try:
        _dur_r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", final_video],
            capture_output=True, text=True, timeout=30,
        )
        _raw_dur = float(_dur_r.stdout.strip()) if _dur_r.stdout.strip() else 0
        if _raw_dur > MAX_EPISODE_DURATION_S:
            logger.warning(f"[DURATION CAP] {_raw_dur:.0f}s > {MAX_EPISODE_DURATION_S}s — trimming")
            print(f"\n  [DURATION CAP] {_raw_dur:.0f}s exceeds {MAX_EPISODE_DURATION_S}s — trimming...")
            _trim_tmp = final_video + ".trimmed.mp4"
            _trim_r = subprocess.run(
                ["ffmpeg", "-y", "-i", final_video,
                 "-t", str(MAX_EPISODE_DURATION_S),
                 "-c:v", "libx264", "-preset", "medium",
                 "-b:v", "8M", "-maxrate", "10M", "-bufsize", "15M",
                 "-r", "30", "-vsync", "cfr",
                 "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
                 "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                 "-af", "asetpts=PTS-STARTPTS",
                 "-movflags", "+faststart",
                 _trim_tmp],
                capture_output=True, text=True, timeout=600,
            )
            if _trim_r.returncode == 0 and os.path.exists(_trim_tmp):
                os.replace(_trim_tmp, final_video)
                print(f"  [DURATION CAP] Trimmed to {MAX_EPISODE_DURATION_S}s")
            elif os.path.exists(_trim_tmp):
                os.remove(_trim_tmp)
    except Exception as e:
        logger.warning(f"[DURATION CAP] Check failed: {e}")

    # ── Step 7b: PRE-FLIGHT QC (Grade A Guarantee) ───────────────────────
    print("\n[STEP 7b] PRE-FLIGHT QC...")
    t0 = time.time()
    for pf_attempt in range(1, MAX_PREFLIGHT_ATTEMPTS + 1):
        logger.info(f"[PREFLIGHT] Attempt {pf_attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
        print(f"  Preflight attempt {pf_attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
        qc = run_preflight_qc(final_video)

        if qc["passed"]:
            print("  [PREFLIGHT] PASSED — proceeding to grading")
            logger.info("[PREFLIGHT] PASSED — sending to grading")
            break

        logger.warning(f"[PREFLIGHT] FAILED: {qc['issues']}")
        print(f"  [PREFLIGHT] FAILED: {qc['issues']}")
        write_render_context("7b", "fail", error=str(qc["issues"]))

        if pf_attempt == MAX_PREFLIGHT_ATTEMPTS:
            logger.error("[PREFLIGHT] Max attempts reached — sending anyway")
            print("  [PREFLIGHT] Max attempts — sending to grading anyway")
            if is_enabled("telegram_alerts"):
                from utils.telegram_alerts import send_alert
                send_alert(
                    f"PREFLIGHT: {qc['issues']} — sending to grading anyway",
                    level="warning",
                )
            break

        # Apply targeted fixes
        _apply_preflight_fixes(final_video, qc)

    timing["7b_preflight_qc"] = round(time.time() - t0, 2)
    write_render_context("7b", "ok" if qc["passed"] else "warn")

    # ── Step 8: SHORTS ────────────────────────────────────────────────────
    print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
    t0 = time.time()
    shorts_dir = os.path.join(run_dir, "shorts")
    shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
                             max_shorts=3 if not test_mode else 1)
    print(f"  Shorts: {len(shorts)}")
    timing["8_shorts"] = round(time.time() - t0, 2)

    # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
    print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
    t0 = time.time()
    thumb_data = script.get("thumbnail", {})
    top_quote = ""
    try:
        if clips:
            top_quote = clips[0].get("quote", "")
    except (NameError, UnboundLocalError):
        pass
    thumb_path = os.path.join(run_dir, "thumbnail.png")
    generate_thumbnail(
        thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
        thumb_data.get("subtext", ""),
        thumb_path,
        btc_price=btc_price,
        top_quote=top_quote,
    )
    timing["9_thumbnail"] = round(time.time() - t0, 2)

    # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
    print("\n[STEP 10/12] GENERATING CHAPTERS...")
    t0 = time.time()
    chapters_path = os.path.join(run_dir, "chapters.txt")
    generate_chapters(script, audio_data, chapters_path)
    timing["10_chapters"] = round(time.time() - t0, 2)

    # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
    print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
    t0 = time.time()
    podcast_path = os.path.join(run_dir, "podcast.mp3")
    extract_podcast_audio(final_video, podcast_path)

    email_html = generate_email_html(
        script.get("episode_title", "Pulse Check"),
        segments_summary=script.get("segments_summary", []),
        btc_price=btc_price,
    )
    newsletter_path = os.path.join(run_dir, "newsletter.html")
    save_newsletter_html(email_html, newsletter_path)
    timing["11_podcast_newsletter"] = round(time.time() - t0, 2)

    # ── Step 12: VERIFY ───────────────────────────────────────────────────
    print("\n[STEP 12/12] VERIFYING OUTPUT...")
    t0 = time.time()
    passed = verify_video(final_video)

    # Final AV sync validation
    final_offset = check_av_sync(final_video)
    print(f"  Final AV sync offset: {final_offset:+.3f}s")
    if abs(final_offset) > 0.05:
        logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
        nuclear_tmp = final_video + ".nuclear.mp4"
        nuclear_cmd = subprocess.run([
            "ffmpeg", "-y",
            "-fflags", "+genpts+igndts",
            "-i", final_video,
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-vsync", "cfr",
            "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-af", "asetpts=PTS-STARTPTS,aresample=48000,alimiter=limit=0.891:level=false",
            "-movflags", "+faststart",
            nuclear_tmp,
        ], capture_output=True, text=True, timeout=600)
        if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
            os.replace(nuclear_tmp, final_video)
            recheck = check_av_sync(final_video)
            print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
        elif os.path.exists(nuclear_tmp):
            os.remove(nuclear_tmp)

    # Final bitrate validation
    br_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
        capture_output=True, text=True,
    )
    try:
        br_info = json.loads(br_result.stdout)
        bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
        print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
        if bitrate < 3_000_000:
            logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
    except Exception:
        pass

    timing["12_verify"] = round(time.time() - t0, 2)
    write_render_context(12, "ok" if passed else "fail",
                         error="verify failed" if not passed else None)

    # ── Step 12b: POST-RENDER QC (blocking — P1 Fix 6) ─────────────────
    print("\n[STEP 12b] POST-RENDER QC...")
    t0 = time.time()
    qc_passed = True
    try:
        from qc_pipeline import post_render_qc, save_qc_report
        manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
        qc_report = post_render_qc(final_video, manifest_json_path)
        save_qc_report(qc_report, run_dir)
        qc_passed = qc_report.get("passed", False)
        print(f"  QC: {'PASS' if qc_passed else 'FAIL'}")
        for check, val in qc_report.get("checks", {}).items():
            status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
            print(f"    [{status}] {check}")
        if not qc_passed:
            logger.error("Post-render QC FAILED — render is not broadcast-ready")
            write_render_context("12b", "fail", error="Post-render QC failed")
    except Exception as e:
        logger.warning(f"Post-render QC exception: {e}")
        qc_passed = False
    timing["12b_qc"] = round(time.time() - t0, 2)

    # ── Summary ──────────────────────────────────────────────────────────
    timing["total"] = round(time.time() - t_pipeline_start, 2)

    # Video stats
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", final_video],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])
        vid = next((s for s in streams if s.get("codec_type") == "video"), {})
        aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
        dur = float(fmt.get("duration", 0))
        sz = int(fmt.get("size", 0)) / 1024 / 1024
        timing["video_duration"] = round(dur, 1)
        timing["video_size_mb"] = round(sz, 1)
    except Exception:
        vid, aud, dur, sz = {}, {}, 0, 0

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
    print(f"  Title:    {script.get('episode_title', 'Untitled')}")
    print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
    print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
    print(f"  Size:     {sz:.1f}MB")
    print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
    print(f"  Shorts:   {len(shorts)}")
    print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")

    outputs = {
        "video": final_video,
        "shorts": [s for s in shorts],
        "thumbnail": thumb_path,
        "chapters": chapters_path,
        "podcast": podcast_path,
        "newsletter": newsletter_path,
        "script": script_path,
        "selections": sel_path,
    }

    print(f"\n  OUTPUT FILES:")
    for name, path in outputs.items():
        if isinstance(path, list):
            for p in path:
                exists = "Y" if os.path.exists(p) else "N"
                print(f"    [{exists}] {os.path.basename(p)}")
        else:
            exists = "Y" if os.path.exists(path) else "N"
            print(f"    [{exists}] {os.path.basename(path)}")

    print(f"\n  TIMING:")
    for step, secs in timing.items():
        if step not in ("video_duration", "video_size_mb"):
            print(f"    {step:25s}: {secs:.1f}s")
    print(f"\n  Output: {run_dir}")
    print("=" * 70)

    _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)

    # Save manifest
    manifest = {
        "version": "v5",
        "episode_title": script.get("episode_title", ""),
        "btc_price": btc_price,
        "test_mode": test_mode,
        "timestamp": time_str,
        "clips_used": [
            {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
            for r, info in sorted(extracted_clips.items())
        ],
        "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
        "timing": timing,
        "success": passed,
    }
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
    print("\n[STEP 13] QUALITY GATE...")
    t0 = time.time()
    quality_score = compute_quality_score(manifest_path, video_path=final_video)
    print(f"  {format_score_report(quality_score)}")
    manifest["quality_score"] = quality_score

    if is_enabled("youtube_auto_upload") and should_upload(quality_score):
        from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
        # Build YouTube metadata
        ep_title = script.get("episode_title", "Pulse Check")
        yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
        chapters_text = ""
        if os.path.exists(chapters_path):
            with open(chapters_path) as f:
                chapters_text = f.read()
        yt_description = build_description(
            summary=f"{ep_title}\n\nBTC Price: {btc_price}",
            chapters_text=chapters_text,
            clips=clips,
        )
        topics = [c.get("channel", "") for c in clips]
        yt_tags = build_tags(topics)

        print(f"  Uploading to YouTube (unlisted)...")
        upload_result = yt_upload(
            final_video, yt_title, yt_description,
            tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
        )
        print(f"  Upload result: {upload_result.get('status')}")
        if upload_result.get("url"):
            print(f"  URL: {upload_result['url']}")
        manifest["upload_result"] = upload_result
        if is_enabled("telegram_alerts") and upload_result.get("url"):
            alert_upload_success(date_str, upload_result["url"])

        # Auto-publish to Nostr + X after successful YouTube upload
        if upload_result.get("url"):
            try:
                import sys
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from core.social_publisher import SocialPublisher
                yt_id = upload_result.get("video_id", "")
                social_result = SocialPublisher().publish_episode(yt_title, yt_id, yt_description)
                print(f"  Social publish: nostr={social_result.get('nostr', {}).get('success')}, x={social_result.get('twitter', {}).get('success')}")
                manifest["social_publish"] = social_result
            except Exception as e:
                logger.error("Social auto-publish episode failed (non-blocking): %s", e)
                print(f"  Social publish failed (non-blocking): {e}")
    elif quality_score < 85:
        logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
        hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
        with open(hold_path, "w") as f:
            f.write(f"Quality score: {quality_score}/100\n")
            f.write(f"Threshold: 85\n")
            f.write(f"Reason: Below quality threshold\n")
            f.write(f"Episode: {script.get('episode_title', '')}\n")
            f.write(f"Video: {final_video}\n")
        manifest["held_for_review"] = True
        if is_enabled("telegram_alerts"):
            alert_quality_hold(date_str, quality_score)
    else:
        logger.info("YouTube auto-upload disabled in feature flags")

    # Write final manifest with quality score
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    timing["13_quality_gate"] = round(time.time() - t0, 2)

    # ── Step 13b: GEMINI GRADING ──────────────────────────────────────────
    print("\n[STEP 13b] GEMINI GRADING...")
    t0_grade = time.time()
    try:
        grade_script = os.path.join(BASE, "gemini_grade.py")
        grade_result = subprocess.run(
            [sys.executable, grade_script, final_video],
            capture_output=True, text=True, timeout=600,
        )
        grade_stdout = grade_result.stdout.strip()
        grade_line = [l for l in grade_stdout.splitlines() if l.startswith("GRADE_")]
        if grade_line:
            parts = grade_line[-1].split("|")
            gemini_grade = parts[0].replace("GRADE_", "").replace("_PASS", "").replace("_FAIL", "")
            gemini_score = int(parts[1]) if len(parts) > 1 else 0
            gemini_verdict = parts[3] if len(parts) > 3 else ""
            logger.info(f"Gemini grade: {gemini_grade} ({gemini_score}/100) — {gemini_verdict}")
            print(f"  Gemini Grade: {gemini_grade} | Score: {gemini_score}/100")
            print(f"  Verdict: {gemini_verdict}")
            manifest["gemini_grade"] = gemini_grade
            manifest["gemini_score"] = gemini_score
            manifest["gemini_verdict"] = gemini_verdict
        else:
            logger.warning(f"Gemini grading returned no grade line. stderr: {grade_result.stderr[-300:]}")
            print(f"  Gemini grading: no grade line returned (exit {grade_result.returncode})")

        # Copy grade JSON to grades/ directory
        grades_dir = os.path.join(BASE, "grades")
        os.makedirs(grades_dir, exist_ok=True)
        logs_grades_dir = os.path.join(BASE, "logs", "grades")
        if os.path.isdir(logs_grades_dir):
            import glob as _grade_glob
            _grade_files = sorted(_grade_glob.glob(os.path.join(logs_grades_dir, "grade_*.json")),
                                  key=os.path.getmtime)
            if _grade_files:
                latest_grade_json = _grade_files[-1]
                dest = os.path.join(grades_dir, os.path.basename(latest_grade_json))
                shutil.copy2(latest_grade_json, dest)
                logger.info(f"Grade JSON copied to {dest}")
    except subprocess.TimeoutExpired:
        logger.warning("Gemini grading timed out after 600s")
        print("  Gemini grading: TIMED OUT (600s)")
    except Exception as e:
        logger.warning(f"Gemini grading failed (non-fatal): {e}")
        print(f"  Gemini grading failed: {e}")
    timing["13b_gemini_grade"] = round(time.time() - t0_grade, 2)

    # Write manifest again with gemini grade
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # ── Step 14: STAGE BRIEF (post Grade-A render) ─────────────────────────
    if quality_score >= 85:
        try:
            from generate_stage_brief import generate_brief
            print("\n[STEP 14] GENERATING STAGE BRIEF...")
            t0 = time.time()
            brief_path = generate_brief(run_dir)
            if brief_path:
                logger.info(f"Stage brief generated: {brief_path}")
                print(f"  Stage brief: {brief_path}")
                manifest["stage_brief"] = brief_path
            else:
                logger.warning("Stage brief returned None")
                print("  Stage brief: skipped (returned None)")
            timing["14_stage_brief"] = round(time.time() - t0, 2)
        except Exception as e:
            logger.warning(f"Stage brief generation failed (non-fatal): {e}")
            print(f"  Stage brief failed (non-fatal): {e}")
            timing["14_stage_brief"] = 0
    else:
        logger.info(f"Skipping stage brief — quality score {quality_score} < 85")

    # Save episode performance data (V17)
    try:
        from utils.analytics_store import save_episode_performance
        perf_data = {
            "date": ts.strftime("%Y-%m-%d"),
            "episode_title": script.get("episode_title", ""),
            "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
            "quality_score": manifest.get("quality_score", 0),
            "clips_count": len(manifest.get("clips_used", [])),
            "duration_seconds": round(timing.get("video_duration", 0), 1),
            "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
            "av_sync_offset": round(final_offset, 3),
            "music_mood": episode_mood,
            "test_mode": test_mode,
        }
        save_episode_performance(date_str, perf_data)
    except Exception as e:
        logger.warning(f"Performance data save failed: {e}")

    # Telegram success alert
    if is_enabled("telegram_alerts") and passed:
        alert_pipeline_success(date_str, quality_score,
                               timing.get("video_duration", 0), final_video)

    # ── Step 14: FORMAT MULTIPLIER (V22) ───────────────────────────────────
    # LAW 1: Only runs AFTER episode is fully rendered and QC-passed.
    # LAW 2: Runs as a detached subprocess — never blocks or delays the main render.
    if is_enabled("multi_format_output") and passed:
        print("\n[STEP 14] FORMAT MULTIPLIER — launching secondary formats...")
        try:
            fmt_script = os.path.join(BASE, "format_multiplier.py")
            fmt_args = [
                sys.executable, fmt_script,
                "--manifest", manifest_path,
                "--video", final_video,
            ]
            if test_mode:
                fmt_args.append("--test")
            # Detached subprocess: does not block main pipeline return
            fmt_proc = subprocess.Popen(
                fmt_args,
                stdout=open(os.path.join(run_dir, "format_multiplier.log"), "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True,  # detach from parent process group
            )
            print(f"  Format multiplier launched (PID {fmt_proc.pid}) — 5 formats running in background")
            print(f"  Log: {run_dir}/format_multiplier.log")
            manifest["format_multiplier_pid"] = fmt_proc.pid
        except Exception as e:
            logger.warning(f"Format multiplier launch failed (non-blocking): {e}")
    elif not is_enabled("multi_format_output"):
        logger.info("multi_format_output feature flag is disabled — skipping format multiplier")

    # ── Post-render health check + Resend notification ─────────────────────
    hc_passed = True  # default for test mode; overridden below for production
    if not test_mode:
        hc_passed, hc_errors = _post_render_health_check(final_video)
        dur_s = timing.get("video_duration", 0)
        size_mb = timing.get("video_size_mb", 0)
        dur_min = int(dur_s // 60)
        dur_sec = int(dur_s % 60)
        if passed and hc_passed:
            _send_resend_alert(
                f"Pulse Check rendered: {dur_min}m {dur_sec}s, {size_mb:.0f}MB",
                f"Episode: {script.get('episode_title', 'Untitled')}\n"
                f"Duration: {dur_min}m {dur_sec}s\n"
                f"Size: {size_mb:.1f}MB\n"
                f"Quality: {quality_score}/100\n"
                f"Video: {final_video}",
            )
        else:
            _send_resend_alert(
                "ALERT: Pulse Check render issues detected",
                f"Episode: {script.get('episode_title', 'Untitled')}\n"
                f"Pipeline passed: {passed}\n"
                f"Health check passed: {hc_passed}\n"
                f"Errors: {hc_errors}\n"
                f"Video: {final_video}",
            )

    success = passed and hc_passed and qc_passed
    if success:
        _clear_checkpoint()  # P0 Fix 3: clear checkpoint on success
    return success


def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
    report_path = os.path.join(run_dir, "timing_report.txt")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "PULSE CHECK V5 — Timing Report",
        f"Generated: {ts}",
        f"Status: {'SUCCESS' if success else 'FAILED'}",
        "",
        "STEP TIMINGS:",
    ]
    for step, val in timing.items():
        if step in ("video_duration", "video_size_mb"):
            continue
        lines.append(f"  {step:<25}: {val:.1f}s")
    lines += [
        "",
        "OUTPUT STATS:",
        f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
        f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
        f"  total_wall_time_s    : {time.time() - t_start:.1f}",
    ]
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Pulse Check V5 — Clip-First Video Producer")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: fewer clips, truncated, test output dir")
    parser.add_argument("--skip-scan", action="store_true",
                        help="Skip channel scanning, use cached transcripts")
    parser.add_argument("--fast-test", action="store_true",
                        help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
    parser.add_argument("--reuse-content", action="store_true",
                        help="Skip Steps 1-6 (fetch/script/TTS), reuse locked content from previous run")
    parser.add_argument("--no-resume", action="store_true",
                        help="Skip checkpoint resume, force fresh render")
    args = parser.parse_args()

    # P0 Fix 1: flock process lock — prevent duplicate producers
    # GPU-specific lock allows parallel instances on separate GPUs
    import os as _os
    _gpu_id = _os.environ.get('CUDA_VISIBLE_DEVICES', '0').replace(',','_')
    lock_file = open(f"/tmp/daily_producer_gpu{_gpu_id}.lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.error("Another daily_producer is already running. Exiting.")
        sys.exit(1)

    success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
                           fast_test=args.fast_test,
                           reuse_content=args.reuse_content,
                           no_resume=args.no_resume)

    fcntl.flock(lock_file, fcntl.LOCK_UN)
    # ── Post-render: fire tweet machine from morning brief ──────────────
    try:
        import subprocess as _sp
        _sp.Popen(["python3", "/home/ultron/protocol_pulse/services/tweet_machine.py"],
                  stdout=open("/home/ultron/protocol_pulse/logs/tweet_machine.log", "a"),
                  stderr=subprocess.STDOUT)
        print("  Tweet machine: fired (async)")
    except Exception as _te:
        print(f"  Tweet machine: skipped ({_te})")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
