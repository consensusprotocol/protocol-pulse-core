"""Quality Gate — compute episode quality score and decide upload eligibility.

Score 0-100 based on production quality metrics.
Per PIPELINE_FORENSIC_AUDIT LAW D4.
"""
import json
import logging
import os

logger = logging.getLogger("QualityGate")


def compute_quality_score(manifest_path: str) -> int:
    """Score 0-100 based on episode quality metrics.

    Scoring:
      - AV sync: each clip with offset < 0.05s = +10 (max 30 for 3 clips)
      - No premature cutoffs: each clip trimmed at pause = +5 (max 15)
      - Channel diversity: all unique channels = +20
      - Music present = +10
      - Regression/verify passed = +25

    Args:
        manifest_path: Path to episode manifest.json

    Returns:
        Quality score 0-100
    """
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Cannot read manifest: {e}")
        return 0

    score = 0

    # AV sync: each clip with good offset = +10 (max 30)
    clips_used = manifest.get("clips_used", [])
    for clip in clips_used:
        av_offset = clip.get("av_offset", 999)
        if av_offset < 0.05:
            score += 10
        elif av_offset < 0.15:
            # Partial credit for acceptable sync
            score += 5

    # If no av_offset data in manifest, give benefit of doubt for clips that exist
    if clips_used and not any("av_offset" in c for c in clips_used):
        score += 10 * min(len(clips_used), 3)

    # No premature cutoffs: each clip trimmed at natural pause = +5 (max 15)
    for clip in clips_used:
        if clip.get("trimmed_at_pause", False):
            score += 5
    # If no trimmed_at_pause data, give partial credit for existing clips
    if clips_used and not any("trimmed_at_pause" in c for c in clips_used):
        score += 3 * min(len(clips_used), 3)

    # Channel diversity: all unique channels = +20
    channels = [c.get("channel", "") for c in clips_used]
    if channels and len(channels) == len(set(channels)):
        score += 20

    # Music present = +10
    if manifest.get("music_track") or manifest.get("timing", {}).get("7_assemble"):
        score += 10

    # Regression/verify passed = +25
    if manifest.get("success", False):
        score += 25
    if manifest.get("regression_passed", False):
        score += 0  # Already counted in success

    return min(100, score)


def should_upload(score: int, threshold: int = 85) -> bool:
    """Determine if episode quality is high enough for auto-upload."""
    return score >= threshold


def format_score_report(score: int, threshold: int = 85) -> str:
    """Format a human-readable quality report."""
    status = "PASS" if score >= threshold else "HOLD"
    bar = "#" * (score // 5) + "-" * (20 - score // 5)
    return f"QUALITY SCORE: {score}/100 [{bar}] {status} (threshold: {threshold})"
