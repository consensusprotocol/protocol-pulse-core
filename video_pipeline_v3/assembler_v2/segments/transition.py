from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..constants import VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,COLOR_BG,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,SFX_WHOOSH,FFMPEG_TIMEOUT_SHORT
from ..ffmpeg_core.encode import encode_segment
logger=logging.getLogger(__name__)
TRANSITION_DURATION=0.25

class TransitionSegment(Segment):
    criticality='optional'

    def render(self,spec:SegmentSpec,ctx:EpisodeContext,output_path:Path,idx:int)->RenderedSegment:
        try:
            return self._render(spec,ctx,output_path)
        except Exception as e:
            logger.error(f'[transition] exception: {e}')
            return self.filler_result(spec,ctx,output_path,str(e))

    def _render(self,spec,ctx,output_path):
        dur=TRANSITION_DURATION
        apply_whoosh=SFX_WHOOSH.exists() and not ctx.has_whoosh(output_path)

        if apply_whoosh:
            inputs=[
                ['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
                ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
                ['-i',str(SFX_WHOOSH)],
            ]
            fg=(
                f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
                f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[sil];'
                f'[2:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
                f'afade=t=in:st=0:d=0.05,volume=0.6[whoosh];'
                f'[sil][whoosh]amix=inputs=2:duration=first:weights=1 1[a_out]'
            )
        else:
            inputs=[
                ['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
                ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
            ]
            fg=(
                f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
                f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[a_out]'
            )

        ok,passed,summary,ms=encode_segment(
            inputs,fg,'[v_out]','[a_out]',output_path,dur,'transition',FFMPEG_TIMEOUT_SHORT)

        if not ok or not output_path.exists():
            return self.filler_result(spec,ctx,output_path,'transition encode failed')

        if apply_whoosh:
            ctx.mark_whoosh(output_path)
            logger.info('[transition] OK with whoosh')
        else:
            logger.info('[transition] OK (no whoosh)')

        return RenderedSegment(spec=spec,path=str(output_path),
                               duration=dur,contract_passed=passed,
                               degraded=not passed,ffprobe_summary=summary,
                               render_ms=ms)
