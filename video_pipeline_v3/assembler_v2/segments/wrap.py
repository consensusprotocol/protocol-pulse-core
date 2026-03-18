from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..constants import (VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
                         AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
                         AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA, AUDIO_LIMITER,
                         OUTRO_BRANDED, COLOR_BG, COLOR_RED, COLOR_WHITE, FONT_BOLD, FONT_MONO)
from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename
logger = logging.getLogger(__name__)

class WrapSegment(Segment):
    criticality = 'optional'

    def render(self, spec: SegmentSpec, ctx: EpisodeContext, output_path: Path, idx: int) -> RenderedSegment:
        try:
            return self._render(spec, ctx, output_path)
        except Exception as e:
            logger.error(f'[wrap] exception: {e}')
            return self.filler_result(spec, ctx, output_path, str(e))

    def _render(self, spec, ctx, output_path):
        tts = Path(spec.tts_path) if spec.tts_path else None
        tts_dur = ffprobe_duration(tts) if tts and tts.exists() else 0.0
        outro_dur = ffprobe_duration(OUTRO_BRANDED) if OUTRO_BRANDED.exists() else 0.0
        total_dur = max(tts_dur, outro_dur, 10.0)
        tmp = output_path.with_suffix('.tmp.mp4')

        if not OUTRO_BRANDED.exists() or outro_dur < 1.0:
            logger.warning('[wrap] outro_branded_new.mp4 missing — using dark fallback')
            return self._render_dark_fallback(spec, ctx, output_path, tts, tts_dur)

        if tts and tts.exists() and tts_dur > 0.5:
            inputs = [
                ['-stream_loop', '-1', '-i', str(OUTRO_BRANDED)],
                ['-i', str(tts)],
            ]
            fg = (
                f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
                f'setpts=PTS-STARTPTS,'
                f'fade=t=out:st={max(0,total_dur-0.5):.3f}:d=0.5[v_out];'
                f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
                f'asetpts=PTS-STARTPTS,'
                f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
                f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
            )
        else:
            inputs = [['-stream_loop', '-1', '-i', str(OUTRO_BRANDED)]]
            fg = (
                f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
                f'setpts=PTS-STARTPTS,'
                f'fade=t=out:st={max(0,total_dur-0.5):.3f}:d=0.5[v_out];'
                f'[0:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
                f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
            )

        flat = []
        for i in inputs: flat.extend([str(x) for x in i])
        args = (flat + ['-filter_complex', fg]
                + ['-map', '[v_out]', '-map', '[a_out]']
                + ['-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium']
                + ['-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT]
                + ['-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
                   '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS)]
                + ['-t', str(round(total_dur, 3)), '-movflags', '+faststart', str(tmp)])

        ok = run_ffmpeg(args, 'wrap outro', 120)
        if not ok or not tmp.exists() or tmp.stat().st_size < 10000:
            return self.filler_result(spec, ctx, output_path, 'wrap encode failed')

        passed, summary = ffprobe_contract(tmp)
        atomic_rename(tmp, output_path)
        logger.info(f'[wrap] OK ({total_dur:.1f}s)')
        return RenderedSegment(spec=spec, path=str(output_path),
                               duration=summary.get('duration', total_dur),
                               contract_passed=passed, degraded=False,
                               ffprobe_summary=summary)

    def _render_dark_fallback(self, spec, ctx, output_path, tts, dur):
        from ..helpers import make_filler
        dur = max(dur, 10.0)
        make_filler(output_path, dur, tts)
        return RenderedSegment(spec=spec, path=str(output_path),
                               duration=dur, contract_passed=True, degraded=True,
                               error='outro asset missing')
