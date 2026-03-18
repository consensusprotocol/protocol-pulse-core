"""Protocol Pulse V2 - preflight.py"""
from __future__ import annotations
import os,shutil,logging
from pathlib import Path
from .constants import INTRO_TAG,INTRO_MUSIC,BG_LOOP,OUTRO_BRANDED,SFX_WHOOSH,SFX_SWOOSH,FONT_BOLD,FONT_MONO,CHARTS_DIR
from .helpers import ffprobe_duration,ffprobe_streams
logger=logging.getLogger(__name__)
CRITICAL=[(INTRO_TAG,"intro_tag.mp4",1000000),(INTRO_MUSIC,"intro_music.mp3",100000),(BG_LOOP,"bg_loop.mp4",1000000),(OUTRO_BRANDED,"outro_branded_new.mp4",1000000),(SFX_WHOOSH,"custom_whoosh.wav",10000),(SFX_SWOOSH,"card_swoosh.wav",10000),(FONT_BOLD,"JetBrainsMono-Bold.ttf",50000),(FONT_MONO,"JetBrainsMono-Regular.ttf",50000)]
def run_preflight(tts_files:list,clip_files:list,work_dir:Path)->dict:
    rpt={"passed":True,"critical_failures":[],"warnings":[],"checks":{}}
    def fail(m):
        rpt["critical_failures"].append(m);rpt["passed"]=False;logger.error(f"[preflight] CRITICAL: {m}")
    def warn(m):
        rpt["warnings"].append(m);logger.warning(f"[preflight] WARNING: {m}")
    for t in("ffmpeg","ffprobe"):
        if shutil.which(t):rpt["checks"][t]="OK"
        else:fail(f"{t} not in PATH")
    for path,name,mn in CRITICAL:
        if not path.exists():fail(f"Missing: {name}")
        elif path.stat().st_size<mn:fail(f"Too small: {name}")
        else:rpt["checks"][name]=f"OK {path.stat().st_size//1024}KB"
    try:
        s=os.statvfs(str(work_dir));fg=(s.f_bavail*s.f_frsize)/(1024**3)
        if fg<5.0:fail(f"Disk critical {fg:.1f}GB")
        elif fg<10.0:warn(f"Disk low {fg:.1f}GB")
        else:rpt["checks"]["disk"]=f"OK {fg:.1f}GB"
    except Exception as e:warn(f"Disk check: {e}")
    for p in[Path(x) for x in tts_files]:
        if not p.exists():fail(f"TTS missing: {p.name}")
        elif p.stat().st_size<1000:fail(f"TTS empty: {p.name}")
        else:
            d=ffprobe_duration(p)
            if d<0.5:fail(f"TTS silent: {p.name}")
            else:rpt["checks"][f"tts:{p.name}"]=f"OK {d:.1f}s"
    for p in[Path(x) for x in clip_files]:
        if not p.exists():warn(f"Clip missing (filler): {p.name}");continue
        info=ffprobe_streams(p);streams=info.get("streams",[])
        hv=any(s.get("codec_type")=="video" for s in streams)
        ha=any(s.get("codec_type")=="audio" for s in streams)
        d=ffprobe_duration(p)
        if not hv:fail(f"Clip no video: {p.name}")
        if not ha:warn(f"Clip no audio: {p.name}")
        rpt["checks"][f"clip:{p.name}"]=f"OK {d:.1f}s v={hv} a={ha}"
    for c in("price_chart.png","hashrate_chart.png","dominance_chart.png"):
        cp=CHARTS_DIR/c
        if cp.exists() and cp.stat().st_size>1000:rpt["checks"][c]="OK"
        else:warn(f"Chart missing: {c}")
    if rpt["critical_failures"]:
        raise RuntimeError("Preflight FAILED: "+("; ".join(rpt["critical_failures"])))
    logger.info(f"[preflight] PASSED {len(rpt['checks'])} checks, {len(rpt['warnings'])} warnings")
    return rpt
