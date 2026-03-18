from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,safe_text
from ..constants import (
    VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
    AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
    AUDIO_LIMITER,AUDIO_TARGET_LUFS,AUDIO_MAX_TRUE_PEAK,AUDIO_LRA,
    BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,FONT_BOLD,FONT_MONO
)
logger=logging.getLogger(__name__)
PIP_X,PIP_Y,PIP_W,PIP_H=1240,140,640,360


class NarrationSegment(Segment):
    criticality='required'

    def render(self,spec,ctx,output_path,idx):
        try:
            pip=self._check_pip(spec)
            return self._render(spec,ctx,output_path,pip)
        except Exception as e:
            logger.error(f'[narration] exception: {e}')
            return self.filler_result(spec,ctx,output_path,str(e))

    def _check_pip(self,spec):
        """Check for pre-normalized PiP. Do NOT generate on demand (Law 7)."""
        pip=spec.pip()
        if pip and pip.exists() and pip.stat().st_size>10000:
            return pip
        logger.warning(f'[narration] pre-normalized pip missing rank={spec.clip_rank} — using no-PiP path')
        return None

    def _render(self,spec,ctx,output_path,pip):
        tts=spec.tts()
        if not tts or not tts.exists() or tts.stat().st_size<1000:
            return self.filler_result(spec,ctx,output_path,'TTS missing')
        dur=ffprobe_duration(tts)
        if dur<0.5:
            return self.filler_result(spec,ctx,output_path,'TTS silent')
        has_pip=pip and pip.exists() and pip.stat().st_size>1000
        has_bg=BG_LOOP.exists()
        if has_pip:
            ok=self._render_with_pip(tts,pip,output_path,dur,spec,has_bg)
        else:
            ok=self._render_no_pip(tts,output_path,dur,spec,has_bg)
        if not ok or not output_path.exists() or output_path.stat().st_size<1000:
            return self.filler_result(spec,ctx,output_path,'narration encode failed')
        # Contract already validated inside _encode() — verify final published file
        passed,summary=ffprobe_contract(output_path)
        actual=summary.get('duration',dur)
        logger.info(f'[narration] OK ({actual:.1f}s pip={has_pip})')
        return RenderedSegment(spec=spec,path=str(output_path),duration=actual,
                               contract_passed=passed,degraded=not passed,
                               ffprobe_summary=summary)

    def _build_fg_with_pip(self,pip,dur,headline,body):
        return (
            f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[bg];'
            f'[2:v]scale={PIP_W}:{PIP_H}:force_original_aspect_ratio=decrease,'
            f'pad={PIP_W}:{PIP_H}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},'
            f'format={VIDEO_PIX_FMT}[pip];'
            f'[bg][pip]overlay=x={PIP_X}:y={PIP_Y}:eof_action=repeat:shortest=0[wp];'
            f'[wp]drawbox=x={PIP_X-2}:y={PIP_Y-2}:w={PIP_W+4}:h={PIP_H+4}:'
            f'color={COLOR_RED}@0.8:t=2[pf];'
            f"[pf]drawtext=fontfile={FONT_BOLD}:text='{headline}':"
            f'fontcolor={COLOR_RED}:fontsize=28:x=48:y=48[wh];'
            f"[wh]drawtext=fontfile={FONT_MONO}:text='{body}':"
            f'fontcolor={COLOR_WHITE}:fontsize=22:x=48:y=100:line_spacing=8[v_out];'
            f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
            f'asetpts=PTS-STARTPTS,'
            f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
            f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
        )

    def _build_fg_no_pip(self,dur,headline,body):
        return (
            f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[bg];'
            f'[bg]drawbox=x={PIP_X}:y={PIP_Y}:w={PIP_W}:h={PIP_H}:'
            f'color={COLOR_BG}@1.0:t=fill[wp];'
            f"[wp]drawtext=fontfile={FONT_BOLD}:text='{headline}':"
            f'fontcolor={COLOR_RED}:fontsize=28:x=48:y=48[wh];'
            f"[wh]drawtext=fontfile={FONT_MONO}:text='{body}':"
            f'fontcolor={COLOR_WHITE}:fontsize=22:x=48:y=100:line_spacing=8[v_out];'
            f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
            f'asetpts=PTS-STARTPTS,'
            f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
            f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
        )

    def _encode(self,inputs_list,fg,output_path,dur,label):
        tmp=output_path.with_suffix('.tmp.mp4')
        flat=[str(x) for i in inputs_list for x in i]
        ok=run_ffmpeg(flat+['-filter_complex',fg,
            '-map','[v_out]','-map','[a_out]',
            '-c:v',VIDEO_CODEC,'-crf',str(VIDEO_CRF),'-preset','medium',
            '-r',str(VIDEO_FPS),'-pix_fmt',VIDEO_PIX_FMT,
            '-c:a',AUDIO_CODEC,'-ar',str(AUDIO_SAMPLE_RATE),
            '-b:a',AUDIO_BITRATE,'-ac',str(AUDIO_CHANNELS),
            '-t',str(round(dur,3)),'-movflags','+faststart',str(tmp)],label,180)
        if not ok or not tmp.exists() or tmp.stat().st_size<1000:
            tmp.unlink(missing_ok=True)
            return False
        # Validate BEFORE publishing (Law 2 — match partner_clip.py pattern)
        passed,summary=ffprobe_contract(tmp)
        if not passed:
            tmp.unlink(missing_ok=True)
            return False
        rename_ok=atomic_rename(tmp,output_path)
        if not rename_ok:
            tmp.unlink(missing_ok=True)
            return False
        return True

    def _render_with_pip(self,tts,pip,output_path,dur,spec,has_bg):
        hl=safe_text(spec.headline or spec.segment_type.upper(),55)
        bd=safe_text(spec.body or '',80)
        if has_bg:
            inputs=[['-stream_loop','-1','-i',str(BG_LOOP)],['-i',str(tts)],
                    ['-stream_loop','-1','-i',str(pip)]]
        else:
            inputs=[['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
                    ['-i',str(tts)],['-stream_loop','-1','-i',str(pip)]]
        return self._encode(inputs,self._build_fg_with_pip(pip,dur,hl,bd),
                            output_path,dur,f'narration+pip rank={spec.clip_rank}')

    def _render_no_pip(self,tts,output_path,dur,spec,has_bg):
        hl=safe_text(spec.headline or spec.segment_type.upper(),55)
        bd=safe_text(spec.body or '',80)
        if has_bg:
            inputs=[['-stream_loop','-1','-i',str(BG_LOOP)],['-i',str(tts)]]
        else:
            inputs=[['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
                    ['-i',str(tts)]]
        return self._encode(inputs,self._build_fg_no_pip(dur,hl,bd),
                            output_path,dur,f'narration no-pip rank={spec.clip_rank}')

