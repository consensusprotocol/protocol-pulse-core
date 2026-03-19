"""
Protocol Pulse V2 — episode.py
Episode runner — single entry point that orchestrates a full episode render
from EpisodeManifest to final concatenated MP4.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging, time

from .manifest import EpisodeManifest, SegmentSpec, RenderedSegment
from .state import EpisodeContext
from .preflight import run_preflight
from .helpers import (
    run_ffmpeg, ffprobe_duration, ffprobe_contract, make_filler, atomic_rename,
    write_concat_list,
)
from .ffmpeg_core.probe import measure_lufs, detect_black_frames, detect_silence
from .constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    COLOR_BG, FFMPEG_TIMEOUT_FILTER, FFMPEG_TIMEOUT_ENCODE,
    QC_MIN_LUFS, QC_MAX_LUFS, QC_MAX_TRUE_PEAK, QC_MAX_BLACK_FRAME_S, QC_MAX_SILENCE_S,
    QC_EPISODE_SILENCE_HOLD_S, QC_MIN_DURATION, QC_MAX_DURATION,
)
from .segments.cold_open import ColdOpenSegment
from .segments.narration import NarrationSegment
from .segments.partner_clip import PartnerClipSegment
from .segments.transition import TransitionSegment
from .segments.data_segment import DataSegment
from .segments.social import SocialSegment
from .segments.signal_active import SignalActiveSegment
from .segments.wrap import WrapSegment
from .segments.x_spaces_segment import XSpacesSegment

logger = logging.getLogger(__name__)

SEGMENT_MAP = {
    "cold_open": ColdOpenSegment,
    "narration": NarrationSegment,
    "partner_clip": PartnerClipSegment,
    "transition": TransitionSegment,
    "data": DataSegment,
    "social": SocialSegment,
    "signal_active": SignalActiveSegment,
    "wrap": WrapSegment,
    "x_spaces": XSpacesSegment,
}


@dataclass
class EpisodeReport:
    episode_id: str = ""
    output_path: Optional[Path] = None
    verdict: str = "HOLD"
    duration: float = 0.0
    contract_passed: bool = False
    degraded_count: int = 0
    total_filler_seconds: float = 0.0
    segment_reports: list = field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: str = ""


class EpisodeRunner:
    """Orchestrates a full episode render. run() NEVER raises."""

    def run(self, manifest: EpisodeManifest, output_dir: Path) -> EpisodeReport:
        t0 = time.time()
        try:
            return self._run(manifest, output_dir, t0)
        except Exception as e:
            logger.exception(f"[episode] fatal exception: {e}")
            return EpisodeReport(
                episode_id=manifest.episode_id,
                verdict="HOLD",
                elapsed_seconds=round(time.time() - t0, 3),
                error=str(e),
            )

    def _run(self, manifest: EpisodeManifest, output_dir: Path, t0: float) -> EpisodeReport:
        # 0. Validate manifest
        try:
            manifest.validate()
        except ValueError as e:
            return EpisodeReport(
                episode_id=manifest.episode_id,
                verdict="HOLD",
                elapsed_seconds=round(time.time() - t0, 3),
                error=f"manifest validation failed: {e}",
            )

        # 1. Preflight
        tts_files = [s.tts_path for s in manifest.segments if s.tts_path]
        clip_files = [s.clip_path for s in manifest.segments if s.clip_path]
        try:
            run_preflight(tts_files, clip_files, output_dir)
        except RuntimeError as e:
            return EpisodeReport(
                episode_id=manifest.episode_id,
                verdict="HOLD",
                elapsed_seconds=round(time.time() - t0, 3),
                error=str(e),
            )

        # 2. Create EpisodeContext
        ctx = EpisodeContext.create(manifest.date_str, output_dir)

        # 3. Dispatch segments
        segment_reports: list[RenderedSegment] = []
        for idx, spec in enumerate(manifest.segments):
            seg_t0 = time.time()
            seg_class = SEGMENT_MAP.get(spec.segment_type)
            if seg_class is None:
                # Unknown segment type — filler
                logger.warning(f"[episode] unknown segment_type '{spec.segment_type}' — filler")
                ctx.mark_degraded(spec.segment_type, f"unknown segment_type: {spec.segment_type}", 15.0)
                filler_path = ctx.segment_dir() / f"seg_{idx:03d}_{spec.segment_type}_filler.mp4"
                self._make_unknown_filler(filler_path)
                result = RenderedSegment(
                    spec=spec,
                    path=str(filler_path) if filler_path.exists() else None,
                    duration=15.0,
                    contract_passed=filler_path.exists() and filler_path.stat().st_size > 1000,
                    degraded=True,
                    error=f"unknown segment_type: {spec.segment_type}",
                )
            else:
                out_path = ctx.segment_dir() / f"seg_{idx:03d}_{spec.segment_type}.mp4"
                result = seg_class().render(spec, ctx, out_path, idx)
            seg_elapsed = round((time.time() - seg_t0) * 1000)
            result.render_ms = seg_elapsed
            segment_reports.append(result)
            ctx.segments_rendered.append(result)
            logger.info(
                f"[episode] seg {idx} {spec.segment_type} "
                f"{'OK' if not result.degraded else 'DEGRADED'} "
                f"({seg_elapsed}ms)"
            )

        # 4. Build concat list
        concat_paths = [Path(r.path) for r in segment_reports if r.path and Path(r.path).exists()]
        if not concat_paths:
            return EpisodeReport(
                episode_id=ctx.episode_id,
                verdict="HOLD",
                degraded_count=ctx.degraded_count,
                total_filler_seconds=ctx.total_filler_seconds,
                segment_reports=segment_reports,
                elapsed_seconds=round(time.time() - t0, 3),
                error="no valid segments to concatenate",
            )

        # 5. Concatenate
        concat_list = ctx.workdir / "concat_list.txt"
        if not write_concat_list(concat_paths, concat_list):
            return EpisodeReport(
                episode_id=ctx.episode_id,
                verdict="HOLD",
                degraded_count=ctx.degraded_count,
                total_filler_seconds=ctx.total_filler_seconds,
                segment_reports=segment_reports,
                elapsed_seconds=round(time.time() - t0, 3),
                error="concat list write failed",
            )

        final_name = f"{manifest.date_str}_{ctx.episode_id}_episode.mp4"
        final_tmp = ctx.workdir / f"{final_name}.tmp.mp4"
        final_path = output_dir / final_name

        ok = run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(final_tmp),
        ], "episode concat", FFMPEG_TIMEOUT_ENCODE)

        if not ok or not final_tmp.exists() or final_tmp.stat().st_size == 0:
            final_tmp.unlink(missing_ok=True)
            return EpisodeReport(
                episode_id=ctx.episode_id,
                verdict="HOLD",
                degraded_count=ctx.degraded_count,
                total_filler_seconds=ctx.total_filler_seconds,
                segment_reports=segment_reports,
                elapsed_seconds=round(time.time() - t0, 3),
                error="concat produced empty output",
            )

        rename_ok = atomic_rename(final_tmp, final_path)
        if not rename_ok:
            final_tmp.unlink(missing_ok=True)
            return EpisodeReport(
                episode_id=ctx.episode_id,
                verdict="HOLD",
                error="final episode atomic_rename failed",
                elapsed_seconds=round(time.time() - t0, 3),
                segment_reports=segment_reports,
            )


        # Final audio limiter -- keeps true_peak under -1.0 dBTP
        limiter_tmp = final_path.with_suffix('.lim.mp4')
        lim_ok = run_ffmpeg([
            "-i", str(final_path), "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=7:linear=true,alimiter=limit=0.841:attack=5:release=50",
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
            "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
            "-movflags", "+faststart", str(limiter_tmp),
        ], "final audio limiter", FFMPEG_TIMEOUT_ENCODE)
        if lim_ok and limiter_tmp.exists() and limiter_tmp.stat().st_size > 1000:
            atomic_rename(limiter_tmp, final_path)
            logger.info("[episode] Final audio limiter applied")
        elif limiter_tmp.exists():
            limiter_tmp.unlink(missing_ok=True)
        # 6. Contract check on final
        contract_passed, final_summary = ffprobe_contract(final_path)

        # 7. Content QC — measure actual content quality
        qc_failures = []
        try:
            # Black frame check
            black_segs = detect_black_frames(final_path, min_dur=QC_MAX_BLACK_FRAME_S)
            total_black = sum(b[2] for b in black_segs)
            if total_black > QC_MAX_BLACK_FRAME_S:
                qc_failures.append(f"black_frames={total_black:.1f}s (max {QC_MAX_BLACK_FRAME_S}s)")

            # Silence check
            silence_segs = detect_silence(final_path, min_dur=QC_MAX_SILENCE_S)
            total_silence = sum(e - s for s, e in silence_segs)
            if total_silence > QC_EPISODE_SILENCE_HOLD_S:
                qc_failures.append(f"silence={total_silence:.1f}s")

            # Duration check — must be within spec
            duration = final_summary.get("duration", 0.0)
            if duration < QC_MIN_DURATION:
                qc_failures.append(f"too_short={duration:.0f}s (min {QC_MIN_DURATION}s)")
            elif duration > QC_MAX_DURATION:
                qc_failures.append(f"too_long={duration:.0f}s (max {QC_MAX_DURATION}s)")

            # LUFS check
            lufs, true_peak = measure_lufs(final_path)
            if lufs != -99.0:  # -99 means probe failed — skip check
                if lufs < QC_MIN_LUFS or lufs > QC_MAX_LUFS:
                    qc_failures.append(f"lufs={lufs:.1f} (range {QC_MIN_LUFS} to {QC_MAX_LUFS})")
                if true_peak > QC_MAX_TRUE_PEAK:
                    qc_failures.append(f"true_peak={true_peak:.1f} (max {QC_MAX_TRUE_PEAK})")
        except Exception as e:
            logger.warning(f"[episode] QC probe failed (non-fatal): {e}")

        if qc_failures:
            logger.warning(f"[episode] QC failures: {qc_failures}")
            verdict = "HOLD"

        # 8. Final verdict (QC failures override ctx verdict)
        if not qc_failures:
            verdict = ctx.verdict()
            if not contract_passed:
                verdict = "HOLD"

        duration = final_summary.get("duration", 0.0)

        return EpisodeReport(
            episode_id=ctx.episode_id,
            output_path=final_path,
            verdict=verdict,
            duration=duration,
            contract_passed=contract_passed,
            degraded_count=ctx.degraded_count,
            total_filler_seconds=ctx.total_filler_seconds,
            segment_reports=segment_reports,
            elapsed_seconds=round(time.time() - t0, 3),
            error="",
        )

    def _make_unknown_filler(self, output_path: Path) -> bool:
        """Generate 15s black silent mp4 for unknown segment types. CRF only."""
        tmp = output_path.with_suffix('.tmp.mp4')
        ok = run_ffmpeg([
            "-f", "lavfi", "-i",
            f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-f", "lavfi", "-i",
            f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
            "-ac", str(AUDIO_CHANNELS),
            "-t", "15",
            "-movflags", "+faststart",
            str(tmp),
        ], "unknown_filler 15s", FFMPEG_TIMEOUT_FILTER)
        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            tmp.unlink(missing_ok=True)
            return False
        return atomic_rename(tmp, output_path)
