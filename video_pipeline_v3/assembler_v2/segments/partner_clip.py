from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_streams,ffprobe_contract,atomic_rename
from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
    AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
    AUDIO_LIMITER,COLOR_RED,COLOR_WHITE,FONT_BOLD,FONT_MONO)
logger=logging.getLogger(__name__)
LT_HEIGHT,LT_Y_OFFSET=80,60
LT_BG_ALPHA="0.82"


def _is_hdr(clip):
    """Detect if clip uses HDR color space (BT.2020 / PQ / HLG)."""
    try:
        import subprocess,json as j
        res=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
            "-show_entries","stream=color_space,color_transfer,color_primaries",
            "-of","json",str(clip)],capture_output=True,text=True,timeout=10)
        s=j.loads(res.stdout).get("streams",[{}])[0]
        hdr_markers={"bt2020","smpte2084","arib-std-b67","bt2020nc","bt2020c"}
        vals={s.get("color_space",""),s.get("color_transfer",""),s.get("color_primaries","")}
        return bool(vals & hdr_markers)
    except Exception:
        return False


def _tonemap_filter():
    """HDR-to-SDR tone mapping chain. Applied when HDR source detected."""
    return ("zscale=t=linear:npl=100,format=gbrpf32le,"
            "zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def _safe_label(text,max_chars=40):
    t=text.strip()[:max_chars]
    for o,n in [(chr(92),chr(92)*2),(chr(39),""),(chr(58),chr(92)+chr(58)),
                (chr(37),chr(92)+chr(37)),(chr(91),chr(92)+chr(91)),
                (chr(93),chr(92)+chr(93)),(chr(44),chr(92)+chr(44)),
                (chr(59),chr(92)+chr(59))]:
        t=t.replace(o,n)
    return t.replace(chr(10)," ")


class PartnerClipSegment(Segment):
    criticality="required"

    def render(self,spec,ctx,output_path,idx):
        try:
            return self._render(spec,ctx,output_path)
        except Exception as e:
            logger.error("[partner_clip] exception: "+str(e))
            return self.filler_result(spec,ctx,output_path,str(e))

    def _render(self,spec,ctx,output_path):
        clip=spec.clip()
        if not clip or not clip.exists() or clip.stat().st_size<50000:
            return self.filler_result(spec,ctx,output_path,"clip missing")
        dur=ffprobe_duration(clip)
        if dur<2.0:
            return self.filler_result(spec,ctx,output_path,"clip too short")
        info=ffprobe_streams(clip)
        streams=info.get("streams",[])
        has_v=any(s.get("codec_type")=="video" for s in streams)
        has_a=any(s.get("codec_type")=="audio" for s in streams)
        if not has_v:
            return self.filler_result(spec,ctx,output_path,"clip no video")
        hdr=_is_hdr(clip)
        ch=_safe_label(spec.headline or "PARTNER SIGNAL")
        sl="PROTOCOL PULSE  PARTNER CLIP"
        lty=VIDEO_H-LT_HEIGHT-LT_Y_OFFSET
        tmp=output_path.with_suffix(".tmp.mp4")
        W,H,pf=str(VIDEO_W),str(VIDEO_H),VIDEO_PIX_FMT
        fb,fm=str(FONT_BOLD),str(FONT_MONO)
        cw,cr=COLOR_WHITE,COLOR_RED
        sr,lim=str(AUDIO_SAMPLE_RATE),str(AUDIO_LIMITER)
        vfg=";".join([
            "[0:v]scale="+W+":"+H+":force_original_aspect_ratio=increase,"
            "crop="+W+":"+H+","
            +(_tonemap_filter()+"," if hdr else "")
            +"setsar=1,format="+pf+",setpts=PTS-STARTPTS[vn]",
            "[vn]drawbox=x=0:y="+str(lty)+":w="+W+":h="+str(LT_HEIGHT)+
                ":color=black@"+LT_BG_ALPHA+":t=fill[lb]",
            "[lb]drawtext=fontfile="+fb+":text="+ch+
                ":fontcolor="+cw+":fontsize=28:x=32:y="+str(lty+12)+"[lc]",
            "[lc]drawtext=fontfile="+fm+":text="+sl+
                ":fontcolor="+cr+":fontsize=18:x=32:y="+str(lty+46)+"[v_out]",
        ])
        afg=("[{i}:a]aformat=channel_layouts=stereo:sample_rates="+sr+","
             "asetpts=PTS-STARTPTS,alimiter=limit="+lim+":attack=5:release=50[a_out]")
        if has_a:
            fg=vfg+";"+afg.format(i=0)
            inputs=[["--i",str(clip)]]
            inputs[0][0]="-i"
        else:
            logger.warning("[partner_clip] no audio: "+clip.name)
            fg=vfg+";"+afg.format(i=1)
            inputs=[["--i",str(clip)],["--f","lavfi","--i","anullsrc=r="+sr+":cl=stereo"]]
            inputs[0][0]="-i";inputs[1][0]="-f";inputs[1][2]="-i"
        flat=[str(x) for i in inputs for x in i]
        ok=run_ffmpeg(flat+["-filter_complex",fg,
            "-map","[v_out]","-map","[a_out]",
            "-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset","medium",
            "-r",str(VIDEO_FPS),"-pix_fmt",pf,
            "-c:a",AUDIO_CODEC,"-ar",sr,"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),
            "-t",str(round(dur,3)),"-movflags","+faststart",str(tmp)],
            "partner_clip rank="+str(spec.clip_rank),300)
        if not ok or not tmp.exists() or tmp.stat().st_size<1000:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec,ctx,output_path,"encode failed")
        passed,summary=ffprobe_contract(tmp)
        atomic_rename(tmp,output_path)
        actual=summary.get("duration",dur)
        logger.info("[partner_clip] OK rank="+str(spec.clip_rank))
        return RenderedSegment(spec=spec,path=str(output_path),duration=actual,
                               contract_passed=passed,degraded=not passed,ffprobe_summary=summary)
