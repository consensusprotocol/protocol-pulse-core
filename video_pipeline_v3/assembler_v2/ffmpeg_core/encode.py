from __future__ import annotations
import time,logging
from pathlib import Path
from ..constants import VIDEO_CODEC,VIDEO_CRF,VIDEO_PRESET,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_BITRATE,VIDEO_MAXRATE,VIDEO_BUFSIZE,AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS
from ..helpers import run_ffmpeg,ffprobe_contract,make_filler,atomic_rename
logger=logging.getLogger(__name__)
def encode_segment(inputs,filter_complex,video_map,audio_map,output_path,duration,label="segment",timeout=300,tts_path=None):
    tmp=output_path.with_suffix(".tmp.mp4")
    t0=time.time()
    flat=[]
    for i in inputs:
        flat.extend([str(x) for x in i] if isinstance(i,(list,tuple)) else [str(i)])
    args=flat+["-filter_complex",filter_complex,"-map",video_map,"-map",audio_map,"-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset",VIDEO_PRESET,"-r",str(VIDEO_FPS),"-pix_fmt",VIDEO_PIX_FMT,"-b:v",VIDEO_BITRATE,"-maxrate",VIDEO_MAXRATE,"-bufsize",VIDEO_BUFSIZE,"-c:a",AUDIO_CODEC,"-ar",str(AUDIO_SAMPLE_RATE),"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),"-t",str(round(duration,3)),"-movflags","+faststart",str(tmp)]
    ok=run_ffmpeg(args,label,timeout)
    ms=int((time.time()-t0)*1000)
    def filler(reason):
        logger.error(f"[encode] {reason} {label}")
        fp=output_path.with_suffix(".filler.mp4")
        make_filler(fp,duration,tts_path)
        if fp.exists(): atomic_rename(fp,output_path)
    if not ok or not tmp.exists() or tmp.stat().st_size<10000:
        filler("ENCODE FAILED")
        return False,False,{"error":"encode failed"},ms
    passed,summary=ffprobe_contract(tmp)
    if not passed:
        tmp.unlink(missing_ok=True)
        filler("CONTRACT FAIL")
        return True,False,summary,ms
    atomic_rename(tmp,output_path)
    logger.info(f"[encode] OK {label} ({summary.get(chr(100)+chr(117)+chr(114)+chr(97)+chr(116)+chr(105)+chr(111)+chr(110),0):.1f}s,{ms}ms)")
    return True,True,summary,ms
