from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,
                         AUDIO_TARGET_LUFS,AUDIO_MAX_TRUE_PEAK,AUDIO_LRA,AUDIO_LIMITER,
                         AUDIO_SAMPLE_RATE,OUTRO_BRANDED,COLOR_BG)
from ..helpers import ffprobe_duration
from ..ffmpeg_core.encode import encode_segment
logger=logging.getLogger(__name__)

class WrapSegment(Segment):
    criticality='optional'

    def render(self,spec:SegmentSpec,ctx:EpisodeContext,output_path:Path,idx:int)->RenderedSegment:
        try:
            return self._render(spec,ctx,output_path)
        except Exception as e:
            logger.error(f'[wrap] exception: {e}')
            return self.filler_result(spec,ctx,output_path,str(e))

    def _render(self,spec,ctx,output_path):
        tts=Path(spec.tts_path) if spec.tts_path else None
        tts_dur=ffprobe_duration(tts) if tts and tts.exists() else 0.0
        outro_dur=ffprobe_duration(OUTRO_BRANDED) if OUTRO_BRANDED.exists() else 0.0
        total_dur=max(tts_dur,outro_dur,10.0)

        if not OUTRO_BRANDED.exists() or outro_dur<1.0:
            logger.warning('[wrap] outro asset missing — filler')
            return self.filler_result(spec,ctx,output_path,'outro asset missing')

        if tts and tts.exists() and tts_dur>0.5:
            inputs=[
                ['-stream_loop','-1','-i',str(OUTRO_BRANDED)],
                ['-i',str(tts)],
            ]
            fade_st=max(0,total_dur-0.5)
            fg=(
                f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
                f'setpts=PTS-STARTPTS,'
                f'fade=t=out:st={fade_st:.3f}:d=0.5[v_out];'
                f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
                f'asetpts=PTS-STARTPTS,'
                f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
                f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
            )
        else:
            inputs=[['-stream_loop','-1','-i',str(OUTRO_BRANDED)]]
            fade_st=max(0,total_dur-0.5)
            fg=(
                f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
                f'setpts=PTS-STARTPTS,'
                f'fade=t=out:st={fade_st:.3f}:d=0.5[v_out];'
                f'[0:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
                f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
            )

        ok,passed,summary,ms=encode_segment(
            inputs,fg,'[v_out]','[a_out]',output_path,total_dur,'wrap outro',120,tts)

        if not ok or not output_path.exists():
            return self.filler_result(spec,ctx,output_path,'wrap encode failed')

        logger.info(f'[wrap] OK ({total_dur:.1f}s)')
        return RenderedSegment(spec=spec,path=str(output_path),
                               duration=summary.get('duration',total_dur),
                               contract_passed=passed,degraded=not passed,
                               ffprobe_summary=summary,render_ms=ms)
