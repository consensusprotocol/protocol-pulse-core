from __future__ import annotations
import time,logging
from pathlib import Path
from typing import Optional
from ..constants import VIDEO_CODEC,VIDEO_CRF,VIDEO_PRESET,VIDEO_FPS,VIDEO_PIX_FMT,AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,FFMPEG_TIMEOUT_ENCODE
from ..helpers import run_ffmpeg,ffprobe_contract,make_filler,atomic_rename
logger=logging.getLogger(__name__)

def encode_segment(inputs,filter_complex,video_map,audio_map,output_path,duration,label="segment",timeout=FFMPEG_TIMEOUT_ENCODE,tts_path=None):
    """Single authoritative encode function. Every segment calls this. Never bypass."""
    tmp=output_path.with_suffix(".tmp.mp4")
    t0=time.time()
    flat=[]
    for i in inputs:
        flat.extend([str(x) for x in i] if isinstance(i,(list,tuple)) else [str(i)])
    args=(
        ["-hide_banner"]  # suppress version banner in logs
        +flat
        +["-filter_complex",filter_complex]
        +["-map",video_map,"-map",audio_map]
        +["-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset",VIDEO_PRESET]
        +["-r",str(VIDEO_FPS),"-pix_fmt",VIDEO_PIX_FMT]
        +["-c:a",AUDIO_CODEC,"-ar",str(AUDIO_SAMPLE_RATE),"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS)]
        +["-t",str(round(duration,3))]
        +["-movflags","+faststart"]
        +[str(tmp)]
    )
    # NOTE: run_ffmpeg already prepends ["ffmpeg","-y"] — overwrites tmp safely
    ok=run_ffmpeg(args,label,timeout)
    ms=int((time.time()-t0)*1000)
    def use_filler(reason):
        """Write filler to output_path. Raises RuntimeError if filler itself fails."""
        logger.error(f"[encode] {reason} for {label} — writing filler")
        fp=output_path.with_suffix(".filler.mp4")
        filler_ok=make_filler(fp,duration,tts_path)
        if not filler_ok or not fp.exists():
            raise RuntimeError(f"[encode] filler creation ALSO failed for {label}")
        rename_ok=atomic_rename(fp,output_path)
        if not rename_ok:
            raise RuntimeError(f"[encode] filler rename ALSO failed for {label}")
    if not ok or not tmp.exists() or tmp.stat().st_size<1000:
        use_filler("ENCODE FAILED")
        # Filler written to output_path — signal ok=True so callers don't double-filler
        return True,False,{"error":"encode failed","filler_used":True},ms
    passed,summary=ffprobe_contract(tmp)
    if not passed:
        tmp.unlink(missing_ok=True)
        use_filler("CONTRACT FAILED")
        summary["filler_used"]=True
        return True,False,summary,ms
    atomic_rename(tmp,output_path)
    dur=summary.get("duration",0)
    logger.info(f"[encode] OK {label} ({dur:.1f}s, {ms}ms)")
    return True,True,summary,ms
