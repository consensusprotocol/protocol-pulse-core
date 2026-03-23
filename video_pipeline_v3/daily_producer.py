#!/usr/bin/env python3
"""Daily Pulse Check Producer V5 — clip-first pipeline.

Real YouTube clips from partner channels, host dialogue around them,
music integration, cold open, avatar shorts.

Usage:
  python3 daily_producer.py               # Full daily episode
  python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  python3 daily_producer.py --skip-scan   # Use cached transcripts only
  python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
"""
import sys; sys.dont_write_bytecode=True
import argparse
import fcntl
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
from clip_selector import select_clips
from clip_extractor import extract_all, extract_montage_all, check_av_sync
from script_writer import generate_from_clips
from tts_engine import generate_dialogue_audio
from assembler import assemble_episode, verify_video
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
# Per-Render Context File (consumed by watchdog for CC repair specs)
# ---------------------------------------------------------------------------

CHECKPOINT_FILE = "/tmp/render_checkpoint.json"


def write_render_context(step, status, error=None, **extra):
    """Write/update /tmp/render_context_YYYYMMDD.json for watchdog consumption.

    Called after every pipeline step completes or fails. The watchdog reads this
    file to give Claude Code full context about what was being built when a crash
    occurred. See QWEN_CONTEXT_BIBLE.md Section 7.

    P0 Fix 3: Also writes step-level checkpoint for resume-on-crash.
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
        # P0 Fix 3: checkpoint for resume
        _write_checkpoint(step)
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


def _write_checkpoint(step):
    """Write last completed step number to checkpoint file."""
    try:
        data = {
            "last_completed_step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _read_checkpoint():
    """Read checkpoint. Returns last_completed_step (int) or 0 if none/stale."""
    try:
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
        # Only resume if checkpoint is from today
        if data.get("date") != datetime.now(timezone.utc).strftime("%Y-%m-%d"):
            return 0
        return int(data.get("last_completed_step", 0))
    except Exception:
        return 0


def _clear_checkpoint():
    """Clear checkpoint after successful render."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except OSError:
        pass


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
    if lufs is not None and (lufs < -17 or lufs > -12):
        issues.append(f"lufs={lufs:.1f} (target -17 to -12)")
    if true_peak is not None and true_peak > -1.0:
        issues.append(f"true_peak={true_peak:.1f}dBTP (max -1.0)")

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
    # Content-level freezes (static social cards / signal scenes) need
    # imperceptible temporal noise to break pixel-identical frames.
    # Plain CFR re-encode does NOT fix content-level freezes.
    if "freeze_frames" in issues_str:
        logger.info("[PREFLIGHT FIX] Re-encoding with temporal noise to break content-level freezes")
        tmp = video_path + ".freeze_fix.mp4"
        try:
            r = subprocess.run(
                ["ffmpeg", "-y",
                 "-fflags", "+genpts+igndts+discardcorrupt",
                 "-i", video_path,
                 "-c:v", "libx264", "-preset", "medium",
                 "-b:v", "8M", "-minrate", "3.5M", "-maxrate", "10M", "-bufsize", "15M",
                 "-r", "30", "-vsync", "cfr",
                 "-vf", "noise=c0s=3:c0f=t,setpts=PTS-STARTPTS,format=yuv420p",
                 "-c:a", "copy",
                 "-movflags", "+faststart",
                 tmp],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode == 0 and os.path.exists(tmp):
                os.replace(tmp, video_path)
                logger.info("[PREFLIGHT FIX] Freeze frame noise fix complete")
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
                 "-af", "loudnorm=I=-14:TP=-2.0:LRA=7:linear=true",
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


def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
                 fast_test: bool = False) -> bool:
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
    resume_step = _read_checkpoint()
    if resume_step >= 4:
        logger.info(f"CHECKPOINT RESUME: last completed step={resume_step}, checking for resumable state")
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
    tts_cache = os.path.join(BASE, "tts_cache")
    shutil.rmtree(tts_cache, ignore_errors=True)
    os.makedirs(tts_cache, exist_ok=True)
    logger.info("TTS cache wiped")

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

    # Ensure music directory exists
    ensure_music_dir()

    # Log feature flags at startup
    flags = load_flags()
    logger.info(f"Feature flags: {json.dumps(flags)}")

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

    # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
    print("\n[STEP 1/12] FETCHING BTC PRICE...")
    t0 = time.time()
    btc_price = get_btc_price()
    print(f"  BTC: {btc_price}")
    timing["1_price"] = round(time.time() - t0, 2)
    write_render_context(1, "ok", btc_price=btc_price)

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
        print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
        t0 = time.time()
        selections = select_clips(videos)
        clips = selections.get("clips", [])
        print(f"  Selected: {len(clips)} clips")
        for c in clips:
            print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
        timing["3_select"] = round(time.time() - t0, 2)

    if not clips:
        print("\n  [FAIL] No clips selected — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "select", "No clips selected")
        return False

    # In test mode, use only top 2 clips
    if not fast_test and test_mode and len(clips) > 2:
        selections["clips"] = clips[:2]
        clips = selections["clips"]
        print(f"  [test] Truncated to {len(clips)} clips")

    # Save selections
    sel_path = os.path.join(run_dir, "selections.json")
    with open(sel_path, "w") as f:
        json.dump(selections, f, indent=2)

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
    extracted_clips = extract_all(selections, clip_dir)
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
            for si, sp in enumerate(sorted_social):
                logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
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
    speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
    clip_markers = [d for d in dialogue if d.get("host") in ("CLIP", "SPACE_CLIP")]
    social_seg_count = sum(1 for d in dialogue if d.get("type") == "social_segment")
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
                         space_tap_available=bool(selections.get("space_tap_clips")))

    # ── Step 6: TTS ───────────────────────────────────────────────────────
    print("\n[STEP 6/12] GENERATING PBX NARRATION AUDIO (ElevenLabs)...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_data = generate_dialogue_audio(dialogue, audio_dir)
    successful = sum(1 for l in audio_data.get("lines", [])
                     if l.get("path") and os.path.exists(l.get("path", "")))
    print(f"  Audio: {successful}/{len(speech_lines)} lines")
    print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
    timing["6_tts"] = round(time.time() - t0, 2)
    write_render_context(6, "ok", tts_provider="elevenlabs")

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

    # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
    print("\n[STEP 7/12] ASSEMBLING VIDEO...")
    t0 = time.time()
    result = assemble_episode(script, audio_data, extracted_clips, final_video,
                              btc_price=btc_price, music_bed=music_bed,
                              intro_music=intro_music)
    timing["7_assemble"] = round(time.time() - t0, 2)

    if not result or not os.path.exists(final_video):
        print("\n  [FAIL] Assembly failed")
        write_render_context(7, "fail", error="Video assembly failed or no output file")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
        return False
    write_render_context(7, "ok")

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
    if clips:
        top_quote = clips[0].get("quote", "")
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
            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
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
    args = parser.parse_args()

    # P0 Fix 1: flock process lock — prevent duplicate producers
    lock_file = open("/tmp/daily_producer.lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.error("Another daily_producer is already running. Exiting.")
        sys.exit(1)

    success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
                           fast_test=args.fast_test)

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
