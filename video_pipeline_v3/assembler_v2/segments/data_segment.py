from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,get_chart_path,safe_text
from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
    AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
    AUDIO_LIMITER,BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,COLOR_CYAN,FONT_BOLD,FONT_MONO)
logger=logging.getLogger(__name__)

KEYWORD_MAP={
    "price":"price","$":"price","dollar":"price","usd":"price",
    "hashrate":"hashrate","eh/s":"hashrate","mining":"hashrate",
    "miner":"hashrate","difficulty":"hashrate","exahash":"hashrate",
    "mempool":"mempool","fee":"mempool","sat/vb":"mempool",
    "transaction":"mempool","congestion":"mempool","backlog":"mempool",
}

def _detect_keyword(text):
    t=text.lower()
    for kw,cat in KEYWORD_MAP.items():
        if kw in t: return cat
    return ""

METRICS_CACHE_TTL=120  # seconds — cache valid for 2 minutes
_METRICS_MIN_REFRESH_INTERVAL = 60  # minimum seconds between refresh attempts


def _refresh_metrics_cache(cache_path, ctx):
    """Fetch all metrics and write to cache. Called in background thread under ctx.metrics_lock."""
    import json,urllib.request,time,os
    data={}
    try:
        with urllib.request.urlopen("https://mempool.space/api/v1/prices",timeout=4) as resp:
            d=json.loads(resp.read())
            data["price"]="$"+"{:,}".format(d.get("USD",0))
    except Exception as e:
        logger.error(f"[data] metrics fetch failed (price): {e}")
    try:
        with urllib.request.urlopen("https://mempool.space/api/v1/mining/hashrate/3d",timeout=4) as resp:
            d=json.loads(resp.read())
            data["hashrate"]=str(round(d.get("currentHashrate",0)/1e18,1))+" EH/s"
    except Exception as e:
        logger.error(f"[data] metrics fetch failed (hashrate): {e}")
    try:
        with urllib.request.urlopen("https://mempool.space/api/mempool",timeout=4) as resp:
            d=json.loads(resp.read())
            data["mempool"]=str(round(d.get("mempool_byte_per_vbyte",0),1))+" sat/vB"
    except Exception as e:
        logger.error(f"[data] metrics fetch failed (mempool): {e}")
    if data:
        data["_ts"]=time.time()
        try:
            tmp=str(cache_path)+".tmp"
            with open(tmp,"w") as f:
                json.dump(data,f)
            os.replace(tmp,str(cache_path))
        except Exception as e:
            logger.error(f"[data] metrics cache write failed: {e}")
    ctx.last_metrics_refresh_ts=time.time()


def _get_metric(key,fallback,cache_path,ctx):
    """
    Cache-first metric fetch. Scoped to episode workdir — no /tmp races.
    Refreshes cache under ctx.metrics_lock — only one thread refreshes at a time.
    On any failure: returns fallback immediately, never raises.
    """
    import json,time,threading
    from pathlib import Path
    cp=Path(cache_path)
    try:
        cache=json.loads(cp.read_text())
        age=time.time()-cache.get("_ts",0)
        if age<METRICS_CACHE_TTL and key in cache:
            return cache[key]
        # Stale — refresh under lock, prevent thundering herd
        if time.time()-ctx.last_metrics_refresh_ts>=_METRICS_MIN_REFRESH_INTERVAL:
            if ctx.metrics_lock.acquire(blocking=False):
                try:
                    threading.Thread(target=_locked_refresh,args=(cp,ctx),daemon=True).start()
                finally:
                    pass  # lock released inside _locked_refresh
        if key in cache:
            return cache[key]
    except Exception as e:
        logger.error(f"[data] metrics cache read failed for '{key}': {e}")
        if time.time()-ctx.last_metrics_refresh_ts>=_METRICS_MIN_REFRESH_INTERVAL:
            if ctx.metrics_lock.acquire(blocking=False):
                threading.Thread(target=_locked_refresh,args=(cp,ctx),daemon=True).start()
    # One-shot fallback with short timeout — won't block long
    try:
        import urllib.request
        if key=="price":
            with urllib.request.urlopen("https://mempool.space/api/v1/prices",timeout=2) as resp:
                return "$"+"{:,}".format(json.loads(resp.read()).get("USD",0))
        if key=="hashrate":
            with urllib.request.urlopen("https://mempool.space/api/v1/mining/hashrate/3d",timeout=2) as resp:
                return str(round(json.loads(resp.read()).get("currentHashrate",0)/1e18,1))+" EH/s"
        if key=="mempool":
            with urllib.request.urlopen("https://mempool.space/api/mempool",timeout=2) as resp:
                return str(round(json.loads(resp.read()).get("mempool_byte_per_vbyte",0),1))+" sat/vB"
    except Exception as e:
        logger.error(f"[data] metrics one-shot fallback failed for '{key}': {e}")
    return fallback


def _locked_refresh(cache_path, ctx):
    """Run refresh under lock, then release."""
    try:
        _refresh_metrics_cache(cache_path, ctx)
    finally:
        try:
            ctx.metrics_lock.release()
        except RuntimeError:
            pass

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
        VALID_CHART_KEYWORDS={"price","hashrate","mempool","dominance",""}
        if keyword and keyword.lower() not in VALID_CHART_KEYWORDS:
            logger.warning(f"[data] invalid chart_keyword '{keyword}' — falling back to no chart")
        chart=get_chart_path(keyword)
        cache_path=ctx.workdir/"metrics_cache.json"
        btc=safe_text(_get_metric("price",spec.btc_price or "$N/A",cache_path,ctx),20)
        hr=safe_text(_get_metric("hashrate","N/A EH/s",cache_path,ctx),20)
        mp=safe_text(_get_metric("mempool","N/A sat/vB",cache_path,ctx),20)
        hl=safe_text(spec.headline or "BITCOIN SIGNAL",45)
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
                +"[mp]drawtext=fontfile="+fb+":text='"+hl+"':fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
                +"[h1]drawtext=fontfile="+fm+":text='"+btc+"':fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
                +"[m1]drawtext=fontfile="+fm+":text='"+hr+"':fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
                +"[m2]drawtext=fontfile="+fm+":text='"+mp+"':fontcolor="+cw+":fontsize=22:x=20:y=152[v_m];"
                +"["+ci+":v]scale=1340:754:force_original_aspect_ratio=decrease,"
                +"pad=1340:754:(ow-iw)/2:(oh-ih)/2:"+COLOR_BG+",format="+pf+"[chart];"
                +"[v_m][chart]overlay=x=490:y=163:eof_action=repeat[v_out]")
            fg=bg_fg+";"+chart_fg
        else:
            no_chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
                +"[mp]drawtext=fontfile="+fb+":text='"+hl+"':fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
                +"[h1]drawtext=fontfile="+fm+":text='"+btc+"':fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
                +"[m1]drawtext=fontfile="+fm+":text='"+hr+"':fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
                +"[m2]drawtext=fontfile="+fm+":text='"+mp+"':fontcolor="+cw+":fontsize=22:x=20:y=152[v_out]")
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
        if not passed:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec,ctx,output_path,"contract_failed")
        rename_ok=atomic_rename(tmp,output_path)
        if not rename_ok:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec,ctx,output_path,'atomic_rename failed')
        logger.info("[data] OK ("+str(round(dur,1))+"s chart="+keyword+")")
        return RenderedSegment(spec=spec,path=str(output_path),duration=summary.get("duration",dur),
                               contract_passed=True,degraded=False,ffprobe_summary=summary)
