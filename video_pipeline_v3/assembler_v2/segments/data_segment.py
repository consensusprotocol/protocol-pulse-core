from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,get_chart_path
from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
    AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
    AUDIO_LIMITER,BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,COLOR_CYAN,FONT_BOLD,FONT_MONO)
logger=logging.getLogger(__name__)

KEYWORD_MAP={"price":"price","$":"price","hashrate":"hashrate","eh/s":"hashrate",
             "mining":"hashrate","mempool":"mempool","fee":"mempool","sat/vb":"mempool"}

def _detect_keyword(text):
    t=text.lower()
    for kw,cat in KEYWORD_MAP.items():
        if kw in t: return cat
    return ""

def _get_metric(key,fallback):
    try:
        import json,urllib.request
        if key=="price":
            with urllib.request.urlopen("https://mempool.space/api/v1/prices",timeout=5) as r:
                return "$"+"{:,}".format(json.loads(r.read()).get("USD",0))
        if key=="hashrate":
            with urllib.request.urlopen("https://mempool.space/api/v1/mining/hashrate/3d",timeout=5) as r:
                return str(round(json.loads(r.read()).get("currentHashrate",0)/1e18,1))+" EH/s"
        if key=="mempool":
            with urllib.request.urlopen("https://mempool.space/api/mempool",timeout=5) as r:
                return str(round(json.loads(r.read()).get("mempool_byte_per_vbyte",0),1))+" sat/vB"
    except Exception:
        pass
    return fallback

def _safe(text,n=30):
    t=text.strip()[:n]
    for o,s in [(chr(92),chr(92)*2),(chr(39),""),(chr(58),chr(92)+chr(58)),
                (chr(37),chr(92)+chr(37)),(chr(91),chr(92)+chr(91)),(chr(93),chr(92)+chr(93)),
                (chr(44),chr(92)+chr(44)),(chr(59),chr(92)+chr(59))]:
        t=t.replace(o,s)
    return t.replace(chr(10)," ")

class DataSegment(Segment):
    """Bitcoin data overlay: live metrics + keyword-matched chart. Optional segment."""
    criticality="optional"

    def render(self,spec,ctx,output_path,idx):
        try:
            return self._render(spec,ctx,output_path)
        except Exception as e:
            logger.error("[data] exception: "+str(e))
            return self.filler_result(spec,ctx,output_path,str(e))

    def _render(self,spec,ctx,output_path):
        tts=spec.tts()
        if not tts or not tts.exists() or tts.stat().st_size<1000:
            return self.filler_result(spec,ctx,output_path,"TTS missing")
        dur=ffprobe_duration(tts)
        if dur<0.5:
            return self.filler_result(spec,ctx,output_path,"TTS silent")
        keyword=spec.chart_keyword or _detect_keyword(spec.body+" "+spec.headline)
        chart=get_chart_path(keyword)
        btc=_safe(_get_metric("price",spec.btc_price or "$N/A"),20)
        hr=_safe(_get_metric("hashrate","N/A EH/s"),20)
        mp=_safe(_get_metric("mempool","N/A sat/vB"),20)
        hl=_safe(spec.headline or "BITCOIN SIGNAL",45)
        tmp=output_path.with_suffix(".tmp.mp4")
        W,H,pf=str(VIDEO_W),str(VIDEO_H),VIDEO_PIX_FMT
        fb,fm=str(FONT_BOLD),str(FONT_MONO)
        cw,cr,cc=COLOR_WHITE,COLOR_RED,COLOR_CYAN
        sr,lim=str(AUDIO_SAMPLE_RATE),str(AUDIO_LIMITER)

        if BG_LOOP.exists():
            inputs=[["-stream_loop","-1","-i",str(BG_LOOP)],["-i",str(tts)]]
            bg_fg="[0:v]scale="+W+":"+H+",setsar=1,format="+pf+",setpts=PTS-STARTPTS[bg]"
        else:
            inputs=[["-f","lavfi","-i","color=c="+COLOR_BG+":s="+W+"x"+H+":r="+str(VIDEO_FPS)],["-i",str(tts)]]
            bg_fg="[0:v]format="+pf+",setpts=PTS-STARTPTS[bg]"

        if chart and chart.exists():
            inputs.append(["-loop","1","-framerate",str(VIDEO_FPS),"-i",str(chart)])
            ci=str(len(inputs)-1)
            chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
                +"[mp]drawtext=fontfile="+fb+":text="+hl+":fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
                +"[h1]drawtext=fontfile="+fm+":text="+btc+":fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
                +"[m1]drawtext=fontfile="+fm+":text="+hr+":fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
                +"[m2]drawtext=fontfile="+fm+":text="+mp+":fontcolor="+cw+":fontsize=22:x=20:y=152[v_m];"
                +"["+ci+":v]scale=1340:754:force_original_aspect_ratio=decrease,"
                +"pad=1340:754:(ow-iw)/2:(oh-ih)/2:"+COLOR_BG+",format="+pf+"[chart];"
                +"[v_m][chart]overlay=x=490:y=163:eof_action=repeat[v_out]")
            fg=bg_fg+";"+chart_fg
        else:
            no_chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
                +"[mp]drawtext=fontfile="+fb+":text="+hl+":fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
                +"[h1]drawtext=fontfile="+fm+":text="+btc+":fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
                +"[m1]drawtext=fontfile="+fm+":text="+hr+":fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
                +"[m2]drawtext=fontfile="+fm+":text="+mp+":fontcolor="+cw+":fontsize=22:x=20:y=152[v_out]")
            fg=bg_fg+";"+no_chart_fg

        audio_fg=("[1:a]aformat=channel_layouts=stereo:sample_rates="+sr+","
                  "asetpts=PTS-STARTPTS,"
                  "loudnorm=I=-14:TP=-2:LRA=7:linear=true,"
                  "alimiter=limit="+lim+":attack=5:release=50[a_out]")
        fg=fg+";"+audio_fg
        flat=[str(x) for i in inputs for x in i]
        ok=run_ffmpeg(flat+["-filter_complex",fg,
            "-map","[v_out]","-map","[a_out]",
            "-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset","medium",
            "-r",str(VIDEO_FPS),"-pix_fmt",pf,
            "-c:a",AUDIO_CODEC,"-ar",sr,"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),
            "-t",str(round(dur,3)),"-movflags","+faststart",str(tmp)],
            "data_segment keyword="+keyword,180)
        if not ok or not tmp.exists() or tmp.stat().st_size<1000:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec,ctx,output_path,"data encode failed")
        passed,summary=ffprobe_contract(tmp)
        atomic_rename(tmp,output_path)
        logger.info("[data] OK ("+str(round(dur,1))+"s chart="+keyword+")")
        return RenderedSegment(spec=spec,path=str(output_path),duration=summary.get("duration",dur),
                               contract_passed=passed,degraded=not passed,ffprobe_summary=summary)
