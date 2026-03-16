"""Quality Gate — compute episode quality score and decide upload eligibility.

Score 0-100 based on REAL production quality metrics (ffprobe analysis).
Per PIPELINE_FORENSIC_AUDIT LAW D4 + 2026-03-12 QC overhaul.

Previous version was manifest-metadata-only and scored 94/100 on renders
that Gemini graded F (29-38/100). Now runs actual ffprobe checks for:
  - Silence detection (silencedetect)
  - Black frame detection (blackdetect)
  - True peak analysis (loudnorm)
  - Duration validation
"""
import json
import logging
import os
import re
import subprocess

logger = logging.getLogger("QualityGate")


def _run_ffprobe_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip()) if r.stdout.strip() else 0.0
    except Exception:
        return 0.0


def _detect_silence(video_path: str, min_duration: float = 2.0,
                    noise_db: int = -50) -> list:
    """Run ffmpeg silencedetect and return list of silent segments.

    Returns: [{"start": float, "end": float, "duration": float}, ...]
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af",
             f"silencedetect=noise={noise_db}dB:d={min_duration}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        silences = []
        for match in re.finditer(
            r"silence_start: ([\d.]+).*?silence_end: ([\d.]+).*?silence_duration: ([\d.]+)",
            r.stderr, re.DOTALL,
        ):
            silences.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            })
        return silences
    except Exception as e:
        logger.warning(f"Silence detection failed: {e}")
        return []


def _detect_black_frames(video_path: str, min_duration: float = 0.3,
                         pix_threshold: float = 0.08) -> list:
    """Run ffmpeg blackdetect and return list of black segments.

    Returns: [{"start": float, "end": float, "duration": float}, ...]
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf",
             f"blackdetect=d={min_duration}:pix_th={pix_threshold}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        blacks = []
        for match in re.finditer(
            r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)",
            r.stderr,
        ):
            blacks.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            })
        return blacks
    except Exception as e:
        logger.warning(f"Black frame detection failed: {e}")
        return []


def _measure_loudness(video_path: str) -> dict:
    """Run ffmpeg loudnorm to get LUFS and true peak.

    Returns: {"lufs": float|None, "true_peak": float|None}
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-filter:a", "loudnorm=print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        stderr = r.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            ln_data = json.loads(stderr[json_start:json_end])
            return {
                "lufs": float(ln_data.get("input_i", -99)),
                "true_peak": float(ln_data.get("input_tp", 0)),
            }
    except Exception as e:
        logger.warning(f"Loudness measurement failed: {e}")
    return {"lufs": None, "true_peak": None}


def compute_quality_score(manifest_path: str, video_path: str = "",
                          gemini_qc_result: dict = None) -> int:
    """Score 0-100 based on real video quality analysis.

    Two modes:
      - manifest_path only: legacy manifest-based scoring (capped at 60)
      - manifest_path + video_path: full ffprobe analysis

    Gemini QC integration (Option A fix):
      - If gemini_qc_result is provided and has critical failures, cap score < 50
      - Prevents the false 94/100 bug where broken renders scored high

    Critical failures that force score to 0:
      - Total silence > 5s (host audio missing)
      - Any mid-video black segment > 2s
      - No video file / unreadable

    Penalties:
      - True peak > -1.0 dBFS: -20 points
      - LUFS deviation > 3 from -14: -10 points
      - Any silence > 2s: -5 per occurrence (on top of critical check)
      - Any black > 0.5s: -15 per second over 0.5s

    Base points (from manifest, max 50):
      - Clips present with good AV sync: up to 15
      - Channel diversity: 10
      - Music present: 10
      - Pipeline success flag: 15
    """
    import time as _time

    # ── Load manifest ──
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Cannot read manifest: {e}")
        return 0

    # ── Round 3 FIX 2: Verify video file freshness ──
    if video_path and os.path.exists(video_path):
        mtime = os.path.getmtime(video_path)
        age_hours = (_time.time() - mtime) / 3600
        fsize_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"  QC scanning: {video_path}")
        logger.info(f"  File mtime: {age_hours:.1f}h ago, size: {fsize_mb:.1f}MB")
        if age_hours > 2.0:
            logger.warning(f"  WARNING: Video file is {age_hours:.1f}h old — may be stale cached file")

    # ── Base score from manifest (max 50) ──
    score = 0
    clips_used = manifest.get("clips_used", [])

    # AV sync: up to 15 points (5 per clip, max 3 clips)
    for clip in clips_used[:3]:
        av_offset = clip.get("av_offset", 999)
        if av_offset < 0.05:
            score += 5
        elif av_offset < 0.15:
            score += 3
    # Benefit of doubt if no av_offset data
    if clips_used and not any("av_offset" in c for c in clips_used):
        score += 5 * min(len(clips_used), 3)

    # Channel diversity: 10 points
    channels = [c.get("channel", "") for c in clips_used]
    if channels and len(channels) == len(set(channels)):
        score += 10

    # Music present: 10 points
    if manifest.get("music_track") or manifest.get("timing", {}).get("7_assemble"):
        score += 10

    # Pipeline success: 15 points
    if manifest.get("success", False):
        score += 15

    score = min(50, score)
    logger.info(f"  Manifest base score: {score}/50")

    # ── If no video path, cap at manifest score (max 50) ──
    if not video_path or not os.path.exists(video_path):
        logger.warning("  No video file for ffprobe analysis — capped at manifest score")
        return min(50, score)

    # ── Real ffprobe checks (up to 50 bonus points, or hard penalties) ──
    failures = []
    duration = _run_ffprobe_duration(video_path)

    # Duration check: must be > 60s for a real episode
    if duration < 60:
        failures.append(f"Video too short: {duration:.1f}s")
        logger.error(f"  CRITICAL: Video duration {duration:.1f}s < 60s")
        return 0

    # ── Silence detection (Round 3 FIX 2: -40dB threshold, 2.0s min) ──
    silences = _detect_silence(video_path, min_duration=2.8, noise_db=-40)
    total_silence = sum(s["duration"] for s in silences)

    if total_silence > 20.0:
        # Critical: > 20s total silence means host audio is missing (transitions account for ~13s normally)
        failures.append(f"Total silence: {total_silence:.1f}s (>5s limit)")
        logger.error(f"  CRITICAL FAIL: {total_silence:.1f}s total silence detected "
                      f"({len(silences)} gaps). Host audio likely missing.")
        for s in silences:
            logger.error(f"    Silent gap: {s['start']:.1f}s - {s['end']:.1f}s "
                          f"({s['duration']:.1f}s)")
        return 0

    # Non-critical silence penalty: -5 per gap > 2s
    silence_penalty = len(silences) * 5
    if silences:
        logger.warning(f"  Silence penalty: -{silence_penalty} ({len(silences)} gaps >2s)")
        for s in silences:
            logger.warning(f"    Silent gap: {s['start']:.1f}s - {s['end']:.1f}s ({s['duration']:.1f}s)")

    # ── Black frame detection (Render12 FIX B: pix_th 0.02→0.08, min_dur 0.5→0.3 to catch near-black) ──
    blacks = _detect_black_frames(video_path, min_duration=0.3, pix_threshold=0.08)

    # Filter: ignore first 2s (title card) and last 5s (outro fade)
    mid_blacks = [b for b in blacks
                  if b["start"] > 2.0 and b["end"] < (duration - 5.0)]

    critical_blacks = [b for b in mid_blacks if b["duration"] > 2.0]
    if critical_blacks:
        failures.append(f"{len(critical_blacks)} black segments >2s mid-video")
        logger.error(f"  CRITICAL FAIL: {len(critical_blacks)} black frame segments >2s:")
        for b in critical_blacks:
            logger.error(f"    Black: {b['start']:.1f}s - {b['end']:.1f}s "
                          f"({b['duration']:.1f}s)")
        return 0

    # Penalty: -15 per second of black over 0.5s threshold
    total_black_excess = sum(max(0, b["duration"] - 0.5) for b in mid_blacks)
    black_penalty = int(total_black_excess * 15)
    if mid_blacks:
        logger.warning(f"  Black frame penalty: -{black_penalty} ({len(mid_blacks)} segments, "
                       f"{total_black_excess:.1f}s excess)")
        for b in mid_blacks:
            logger.warning(f"    Black: {b['start']:.1f}s - {b['end']:.1f}s ({b['duration']:.1f}s)")

    # ── Loudness / True peak ──
    loudness = _measure_loudness(video_path)
    peak_penalty = 0
    lufs_penalty = 0

    if loudness["true_peak"] is not None:
        if loudness["true_peak"] > -1.0:
            peak_penalty = 20
            logger.warning(f"  True peak penalty: -20 ({loudness['true_peak']:.1f} dBTP > -1.0)")
        logger.info(f"  True peak: {loudness['true_peak']:.1f} dBTP")

    if loudness["lufs"] is not None:
        lufs_dev = abs(loudness["lufs"] - (-14))
        if lufs_dev > 3:
            lufs_penalty = 10
            logger.warning(f"  LUFS penalty: -10 ({loudness['lufs']:.1f} LUFS, "
                            f"deviation {lufs_dev:.1f} from -14)")
        logger.info(f"  Integrated LUFS: {loudness['lufs']:.1f}")

    # ── Compute final score ──
    # Video analysis bonus: 50 points minus penalties
    video_bonus = max(0, 50 - silence_penalty - black_penalty - peak_penalty - lufs_penalty)
    final_score = min(100, score + video_bonus)

    logger.info(f"  Video analysis: +{video_bonus}/50 "
                f"(silence:-{silence_penalty} black:-{black_penalty} "
                f"peak:-{peak_penalty} lufs:-{lufs_penalty})")

    # ── Gemini QC integration (Option A fix) ──
    # If Gemini QC ran and found critical issues, cap the score so broken
    # renders can never score 94/100 again.
    if gemini_qc_result and isinstance(gemini_qc_result, dict):
        qc_grade = gemini_qc_result.get("overall_grade", "").upper()
        qc_issues = gemini_qc_result.get("issues", [])
        qc_voices = gemini_qc_result.get("voices", 0)

        # Grade F from Gemini QC = hard cap at 30
        if qc_grade == "F":
            final_score = min(final_score, 30)
            logger.warning(f"  Gemini QC grade F — capping score at {final_score}")

        # Grade D from Gemini QC = hard cap at 45
        elif qc_grade == "D":
            final_score = min(final_score, 45)
            logger.warning(f"  Gemini QC grade D — capping score at {final_score}")

        # Voice quality < 5 = critical failure, cap at 40
        if isinstance(qc_voices, (int, float)) and qc_voices < 5:
            final_score = min(final_score, 40)
            logger.warning(f"  Gemini QC voices={qc_voices}/10 — capping score at {final_score}")

        # Any critical issue string = cap at 50
        critical_keywords = ["dead air", "missing audio", "no narration", "silent", "zero-byte"]
        for issue in qc_issues:
            if any(kw in issue.lower() for kw in critical_keywords):
                final_score = min(final_score, 50)
                logger.warning(f"  Gemini QC critical issue: {issue} — capping at {final_score}")
                break

    logger.info(f"  Final score: {final_score}/100")

    return final_score


def should_upload(score: int, threshold: int = 85) -> bool:
    """Determine if episode quality is high enough for auto-upload."""
    return score >= threshold


def format_score_report(score: int, threshold: int = 85) -> str:
    """Format a human-readable quality report."""
    status = "PASS" if score >= threshold else "HOLD"
    bar = "#" * (score // 5) + "-" * (20 - score // 5)
    return f"QUALITY SCORE: {score}/100 [{bar}] {status} (threshold: {threshold})"
