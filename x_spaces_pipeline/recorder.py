"""
TOMBSTONED 2026-03-18
This file is part of the deprecated x_spaces_pipeline/ live-capture system.
It has been superseded by x_spaces_scraper/run_scraper.py which is the
single authoritative pipeline. SpaceStateDB is the authoritative state store.
DO NOT USE — DO NOT IMPORT — DO NOT EXECUTE
Live capture capability will be reintegrated as a clean stage in run_scraper.py.
"""
#!/usr/bin/env python3
"""x_spaces_pipeline/recorder.py"""
import argparse, json, logging, os, signal, subprocess, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, "/home/ultron/protocol_pulse")
from x_spaces_scraper.spaces_state import SpaceStateDB
logger = logging.getLogger("spaces.recorder")
RAW_DIR  = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
LOCK_DIR = Path("/tmp/pp_spaces_locks")
TIMEOUT  = 14400
def release_lock(handle, lock_fd):
    try: os.close(lock_fd)
    except OSError: pass
    (LOCK_DIR / f"{handle}.lock").unlink(missing_ok=True)
def record(handle, url, space_id, lock_fd):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = RAW_DIR / f"{date_str}_{space_id}.m4a"
    meta_path = RAW_DIR / f"{date_str}_{space_id}.meta.json"
    meta_path.write_text(json.dumps({"handle":handle,"space_id":space_id,"url":url,"date_str":date_str},indent=2))
    db = SpaceStateDB()
    cmd = ["ffmpeg","-y","-allowed_extensions","ALL","-protocol_whitelist","file,crypto,data,tls,tcp,http,https,m3u8,hls","-i",url,"-c","copy","-t",str(TIMEOUT),str(output)]
    proc = None
    try:
        proc = subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,preexec_fn=os.setsid)
        logger.info(f"Recording @{handle} pid={proc.pid}")
        proc.wait(timeout=TIMEOUT+60)
        if output.exists() and output.stat().st_size > 102400:
            db.upsert(space_id, downloaded_at=datetime.now().isoformat(), transcript_source="audio_replay")
            return str(output)
        db.upsert(space_id, error="output_too_small_or_missing")
        return None
    except subprocess.TimeoutExpired:
        db.upsert(space_id, error="timeout")
        if proc:
            try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError: pass
        return None
    except Exception as e:
        db.upsert(space_id, error=str(e)[:200])
        if proc:
            try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError: pass
        return None
    finally:
        release_lock(handle, lock_fd)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--space-id", required=True)
    ap.add_argument("--lock-fd", type=int, required=True)
    args = ap.parse_args()
    record(args.handle, args.url, args.space_id, args.lock_fd)
