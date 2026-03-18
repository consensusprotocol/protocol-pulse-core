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
)
from .constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    COLOR_BG, FFMPEG_TIMEOUT_FILTER, FFMPEG_TIMEOUT_ENCODE,
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
            logger.error(f"[episode] fatal exception: {e}")
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
        import os as _os
        concat_list = ctx.workdir / "concat_list.txt"
        concat_tmp = concat_list.with_suffix('.tmp')
        concat_tmp.write_text(
            "\n".join(f"file '{p}'" for p in concat_paths) + "\n"
        )
        _os.replace(str(concat_tmp), str(concat_list))

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

        # 6. Contract check on final
        contract_passed, final_summary = ffprobe_contract(final_path)

        # 7. Verdict
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
        return run_ffmpeg([
            "-f", "lavfi", "-i",
            f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-f", "lavfi", "-i",
            f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
            "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
            "-ac", str(AUDIO_CHANNELS),
            "-t", "15",
            str(output_path),
        ], "unknown_filler 15s", FFMPEG_TIMEOUT_FILTER)
