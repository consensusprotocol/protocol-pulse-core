#!/usr/bin/env python3
"""QC Pipeline — preflight checks + post-render quality validation.

Two entry points:
  preflight_check(manifest_path) — runs BEFORE render
  post_render_qc(video_path, manifest_path) — runs AFTER render

V1 Rule: QC failures LOG only. Do NOT block publish.
"""
import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger("QCPipeline")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[qc] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")


def _ffprobe_duration(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip()) if r.stdout.strip() else 0.0
    except Exception:
        return 0.0


def _ffprobe_bitrate(path: str) -> int:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=bit_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return int(r.stdout.strip()) if r.stdout.strip() else 0
    except Exception:
        return 0


def preflight_check(manifest_path: str) -> tuple:
    """Verify all assets exist and are valid BEFORE rendering.

    Returns:
        (passed: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    if not os.path.exists(manifest_path):
        return False, ["Manifest file not found"], []

    with open(manifest_path) as f:
        manifest = json.load(f)

    segments = manifest.get("segments", [])
    logger.info(f"Preflight check: {len(segments)} segments")

    # Check music bed
    music_bed = manifest.get("music_bed_path", "")
    if music_bed and not os.path.exists(music_bed):
        warnings.append(f"Music bed not found: {music_bed}")

    # Check background assets
    bg_files = [
        os.path.join(ASSETS, "backgrounds", "cyberspace.mp4"),
        os.path.join(ASSETS, "backgrounds", "cyberpunk_loop.mp4"),
    ]
    if not any(os.path.exists(bg) for bg in bg_files):
        warnings.append("No background video assets found")

    for seg in segments:
        seg_id = seg.get("id", "?")
        seg_type = seg.get("type", "unknown")

        # Check audio paths
        audio_path = seg.get("audio_path", "")
        if audio_path and not os.path.exists(audio_path):
            if seg_type in ("partner_clip", "cold_open", "narration_setup",
                            "narration_react", "social_card", "wrap"):
                errors.append(f"MISSING AUDIO: segment {seg_id} ({seg_type}): {audio_path}")
            else:
                warnings.append(f"Missing audio: segment {seg_id} ({seg_type}): {audio_path}")
        elif audio_path and os.path.exists(audio_path):
            dur = _ffprobe_duration(audio_path)
            if dur <= 0:
                errors.append(f"ZERO DURATION audio: segment {seg_id} ({seg_type}): {audio_path}")

        # Check clip paths and quality
        video_path = seg.get("video_path", "")
        if seg_type == "partner_clip" and video_path:
            if not os.path.exists(video_path):
                errors.append(f"MISSING CLIP: segment {seg_id}: {video_path}")
            else:
                bitrate = _ffprobe_bitrate(video_path)
                if bitrate > 0 and bitrate < 1_500_000:
                    warnings.append(
                        f"LOW QUALITY clip: segment {seg_id} at {bitrate/1e6:.1f}Mbps: {video_path}")

        # Check social card data
        if seg_type == "social_card":
            card = seg.get("social_card_data", {})
            if not card.get("handle") or not card.get("text"):
                warnings.append(f"Social card segment {seg_id} missing handle/text")
            ss = card.get("screenshot_path", "")
            if ss and not os.path.exists(ss):
                warnings.append(f"Missing screenshot: segment {seg_id}: {ss}")

    passed = len(errors) == 0
    logger.info(f"Preflight: {'PASS' if passed else 'FAIL'} — {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        logger.error(f"  ERROR: {e}")
    for w in warnings:
        logger.warning(f"  WARN: {w}")

    return passed, errors, warnings


def post_render_qc(video_path: str, manifest_path: str = "") -> dict:
    """Run automated quality checks AFTER rendering.

    Returns:
        QC report dict with pass/fail for each check.
    """
    report = {
        "video_path": video_path,
        "checks": {},
        "passed": False,
        "details": {},
    }

    if not os.path.exists(video_path):
        report["checks"]["file_exists"] = False
        report["details"]["file_exists"] = "Video file not found"
        return report
    report["checks"]["file_exists"] = True

    # Load manifest expectations if available
    qc_exp = {}
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        qc_exp = manifest.get("qc_expectations", {})

    # 1. Duration check
    duration = _ffprobe_duration(video_path)
    dur_range = qc_exp.get("total_duration_range", [360, 900])
    dur_ok = dur_range[0] <= duration <= dur_range[1]
    report["checks"]["duration"] = dur_ok
    report["details"]["duration"] = {
        "measured": round(duration, 1),
        "expected_range": dur_range,
    }
    logger.info(f"  Duration: {duration:.1f}s (range {dur_range}) {'PASS' if dur_ok else 'FAIL'}")

    # 2. Loudness check (integrated LUFS)
    lufs = None
    true_peak = None
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-filter:a", "loudnorm=print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        # Parse loudnorm JSON from stderr
        stderr = r.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            ln_data = json.loads(stderr[json_start:json_end])
            lufs = float(ln_data.get("input_i", -99))
            true_peak = float(ln_data.get("input_tp", 0))
    except Exception as e:
        logger.warning(f"  Loudness measurement failed: {e}")

    target_lufs = qc_exp.get("loudness_lufs", -14)
    if lufs is not None:
        lufs_ok = abs(lufs - target_lufs) <= 2
        report["checks"]["loudness"] = lufs_ok
        report["details"]["loudness"] = {
            "measured_lufs": round(lufs, 1),
            "target_lufs": target_lufs,
            "deviation": round(abs(lufs - target_lufs), 1),
        }
        logger.info(f"  Loudness: {lufs:.1f} LUFS (target {target_lufs}) {'PASS' if lufs_ok else 'FAIL'}")
    else:
        report["checks"]["loudness"] = None
        report["details"]["loudness"] = "measurement_failed"

    # 3. True peak check
    target_tp = qc_exp.get("true_peak_dbtp", -1.5)
    if true_peak is not None:
        tp_ok = true_peak <= target_tp
        report["checks"]["true_peak"] = tp_ok
        report["details"]["true_peak"] = {
            "measured_dbtp": round(true_peak, 1),
            "max_dbtp": target_tp,
        }
        logger.info(f"  True peak: {true_peak:.1f} dBTP (max {target_tp}) {'PASS' if tp_ok else 'FAIL'}")
    else:
        report["checks"]["true_peak"] = None

    # 4. Silent gap detection (>2s)
    silences = []
    try:
        max_gap = qc_exp.get("max_silent_gap_sec", 2.0)
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af",
             f"silencedetect=noise=-40dB:d={max_gap}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        import re
        for match in re.finditer(r"silence_start: ([\d.]+).*?silence_end: ([\d.]+)", r.stderr, re.DOTALL):
            start, end = float(match.group(1)), float(match.group(2))
            silences.append({"start": round(start, 1), "end": round(end, 1),
                             "duration": round(end - start, 1)})
    except Exception as e:
        logger.warning(f"  Silence detection failed: {e}")

    silence_ok = len(silences) == 0
    report["checks"]["no_dead_air"] = silence_ok
    report["details"]["silences"] = silences
    logger.info(f"  Silent gaps (>{qc_exp.get('max_silent_gap_sec', 2.0)}s): {len(silences)} {'PASS' if silence_ok else 'FAIL'}")

    # 5. Black frame detection (>0.5s)
    black_frames = []
    try:
        max_black = qc_exp.get("max_black_frames_sec", 0.5)
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf",
             f"blackdetect=d={max_black}:pix_th=0.10",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300,
        )
        import re
        for match in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", r.stderr):
            black_frames.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            })
    except Exception as e:
        logger.warning(f"  Black frame detection failed: {e}")

    black_ok = len(black_frames) == 0
    report["checks"]["no_black_frames"] = black_ok
    report["details"]["black_frames"] = black_frames
    logger.info(f"  Black frames (>{qc_exp.get('max_black_frames_sec', 0.5)}s): {len(black_frames)} {'PASS' if black_ok else 'FAIL'}")

    # 6. Clip count check
    exp_clips = qc_exp.get("clip_count", 0)
    if exp_clips > 0:
        report["details"]["expected_clips"] = exp_clips

    # Overall pass
    check_vals = [v for v in report["checks"].values() if v is not None]
    report["passed"] = all(check_vals) if check_vals else False

    logger.info(f"  QC Overall: {'PASS' if report['passed'] else 'FAIL'}")
    return report


def save_qc_report(report: dict, output_dir: str) -> str:
    """Save QC report to disk."""
    report_path = os.path.join(output_dir, "qc_report.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"  QC report saved: {report_path}")
    return report_path


def main():
    """CLI: python3 qc_pipeline.py <output_dir>"""
    if len(sys.argv) < 2:
        print("Usage: python3 qc_pipeline.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]

    # Find video and manifest
    import glob
    videos = glob.glob(os.path.join(output_dir, "pulse_check_*.mp4"))
    manifest_path = os.path.join(output_dir, "episode_manifest.json")

    if not videos:
        print(f"No pulse_check_*.mp4 found in {output_dir}")
        sys.exit(1)

    video_path = videos[0]
    print(f"QC Pipeline — {video_path}")

    # Preflight (if manifest exists)
    if os.path.exists(manifest_path):
        passed, errors, warnings = preflight_check(manifest_path)
        print(f"\nPreflight: {'PASS' if passed else 'FAIL'}")

    # Post-render QC
    report = post_render_qc(video_path, manifest_path)
    save_qc_report(report, output_dir)

    print(f"\nPost-render QC: {'PASS' if report['passed'] else 'FAIL'}")
    for check, val in report["checks"].items():
        status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
        print(f"  [{status}] {check}")

    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
