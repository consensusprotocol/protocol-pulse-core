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
        """Write filler to output_path. Never raises — emergency black on any failure."""
        logger.error(f"[encode] {reason} for {label} — writing filler")
        try:
            fp=output_path.with_suffix(".filler.mp4")
            filler_ok=make_filler(fp,duration,tts_path)
            if filler_ok and fp.exists() and fp.stat().st_size>1000:
                rename_ok=atomic_rename(fp,output_path)
                if rename_ok:
                    return True  # filler written successfully
            # Filler creation failed — write emergency static black frame
            logger.error(f"[encode] filler also failed for {label} — writing emergency black")
            emergency_ok=run_ffmpeg([
                "-f","lavfi","-i",
                f"color=c=black:s=1920x1080:r=30,format=yuv420p",
                "-f","lavfi","-i",
                f"anullsrc=r=48000:cl=stereo",
                "-c:v","libx264","-crf","17","-preset","ultrafast",
                "-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
                "-t",str(max(float(duration),1.0)),
                "-movflags","+faststart",str(output_path)
            ],f"emergency filler {label}",30)
            return emergency_ok
        except Exception as ex:
            logger.error(f"[encode] emergency filler ALSO failed: {ex}")
            return False
    if not ok or not tmp.exists() or tmp.stat().st_size<1000:
        use_filler("ENCODE FAILED")
        return False,False,{"error":"encode failed","filler_used":True},ms
    passed,summary=ffprobe_contract(tmp)
    if not passed:
        tmp.unlink(missing_ok=True)
        use_filler("CONTRACT FAILED")
        summary["filler_used"]=True
        return False,False,summary,ms
    rename_ok=atomic_rename(tmp,output_path)
    if not rename_ok:
        tmp.unlink(missing_ok=True)
        use_filler("RENAME FAILED")
        return False,False,{"error":"rename failed","filler_used":True},ms
    dur=summary.get("duration",0)
    logger.info(f"[encode] OK {label} ({dur:.1f}s, {ms}ms)")
    return True,True,summary,ms
