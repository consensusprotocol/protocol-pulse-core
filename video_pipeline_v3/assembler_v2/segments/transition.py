from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..constants import VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, COLOR_BG, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, VIDEO_CODEC, VIDEO_CRF, AUDIO_CODEC, AUDIO_BITRATE, SFX_WHOOSH
from ..helpers import run_ffmpeg, ffprobe_contract, atomic_rename
logger = logging.getLogger(__name__)

TRANSITION_DURATION = 0.25  # seconds — black flash

class TransitionSegment(Segment):
    criticality = 'optional'

    def render(self, spec: SegmentSpec, ctx: EpisodeContext, output_path: Path, idx: int) -> RenderedSegment:
        try:
            return self._render(spec, ctx, output_path)
        except Exception as e:
            logger.error(f'[transition] exception: {e}')
            return self.filler_result(spec, ctx, output_path, str(e))

    def _render(self, spec, ctx, output_path):
        dur = TRANSITION_DURATION
        tmp = output_path.with_suffix('.tmp.mp4')

        # Check whoosh dedup BEFORE building
        apply_whoosh = SFX_WHOOSH.exists() and not ctx.has_whoosh(output_path)

        if apply_whoosh:
            inputs = [
                ['-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
                ['-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
                ['-i', str(SFX_WHOOSH)],
            ]
            fg = (
                f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
                f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[sil];'
                f'[2:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
                f'afade=t=in:st=0:d=0.05,volume=0.6[whoosh];'
                f'[sil][whoosh]amix=inputs=2:duration=first:weights=1 1[a_out]'
            )
        else:
            inputs = [
                ['-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
                ['-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
            ]
            fg = (
                f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
                f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[a_out]'
            )

        flat = []
        for i in inputs: flat.extend([str(x) for x in i])
        args = (flat + ['-filter_complex', fg]
                + ['-map', '[v_out]', '-map', '[a_out]']
                + ['-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'veryfast']
                + ['-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT]
                + ['-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
                   '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS)]
                + ['-t', str(dur), '-movflags', '+faststart', str(tmp)])

        ok = run_ffmpeg(args, 'transition', 30)
        if not ok or not tmp.exists():
            return self.filler_result(spec, ctx, output_path, 'transition encode failed')

        passed, summary = ffprobe_contract(tmp)
        atomic_rename(tmp, output_path)

        if apply_whoosh:
            ctx.mark_whoosh(output_path)
            logger.info('[transition] OK with whoosh')
        else:
            logger.info('[transition] OK (whoosh deduped or missing)')

        return RenderedSegment(spec=spec, path=str(output_path),
                               duration=dur, contract_passed=passed,
                               degraded=False, ffprobe_summary=summary)
