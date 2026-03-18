#!/usr/bin/env python3
"""x_spaces_pipeline/monitor.py"""
import os, subprocess, sys, time, logging
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, "/home/ultron/protocol_pulse")
from x_spaces_scraper.spaces_state import SpaceStateDB
logger = logging.getLogger("spaces.monitor")
LOCK_DIR = Path("/tmp/pp_spaces_locks")
RAW_DIR  = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
COOKIE   = "/home/ultron/protocol_pulse/video_pipeline_v3/data/yt_cookies.txt"
PIPELINE = Path("/home/ultron/protocol_pulse/x_spaces_pipeline")
STALE_LOCK_AGE = 18000
MONITORED_HANDLES = [
    "saylor","LynAldenContact","PrestonPysh","Breedlove22","ODELL",
    "MartyBent","natbrunell","PeterMcCormack","lopp","saifedean",
    "JeffBooth","CaitlinLong_","coryklippsten","Dennis_Porter_",
    "americanhodl8","woonomic","jack","adam3us","nvk","giacomozucco",
    "dergigi","pierre_rochard","jimmysong","Excellion","nic__carter",
    "100trillionUSD","aantonop","APompliano","knutsvanholm","TheGuySwann",
]
def acquire_lock(handle):
    LOCK_DIR.mkdir(exist_ok=True)
    lp = LOCK_DIR / f"{handle}.lock"
    if lp.exists():
        if time.time() - lp.stat().st_mtime > STALE_LOCK_AGE:
            lp.unlink(missing_ok=True)
        else:
            return None
    try:
        fd = os.open(str(lp), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        return fd
    except FileExistsError:
        return None
def release_lock(handle, fd):
    try: os.close(fd)
    except OSError: pass
    (LOCK_DIR / f"{handle}.lock").unlink(missing_ok=True)
def is_space_live(handle):
    try:
        res = subprocess.run(["twspace_dl","-i",f"https://twitter.com/{handle}","--cookies",COOKIE,"--metadata"],capture_output=True,text=True,timeout=30)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "m3u8" in line:
                    return {"handle":handle,"url":line.strip(),"space_id":f"live_{handle}_{int(time.time())}","detected_at":time.time()}
    except subprocess.TimeoutExpired: logger.warning(f"twspace_dl timeout @{handle}")
    except Exception as e: logger.debug(f"@{handle}: {e}")
    try:
        res = subprocess.run(["yt-dlp","--cookies",COOKIE,"--get-url","--no-playlist",f"https://twitter.com/{handle}"],capture_output=True,text=True,timeout=30)
        if res.returncode==0 and "m3u8" in res.stdout:
            return {"handle":handle,"url":res.stdout.strip().splitlines()[0],"space_id":f"replay_{handle}_{int(time.time())}","detected_at":time.time()}
    except Exception: pass
    return None
def run_monitor():
    db = SpaceStateDB()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for handle in MONITORED_HANDLES:
        fd = acquire_lock(handle)
        if fd is None: continue
        space = is_space_live(handle)
        if space:
            if db.get(space["space_id"]):
                release_lock(handle, fd); continue
            db.upsert(space["space_id"],title=f"Space @{handle}",host=handle,url=space["url"],discovered_at=datetime.now(timezone.utc).isoformat())
            subprocess.Popen(["python3",str(PIPELINE/"recorder.py"),"--handle",handle,"--url",space["url"],"--space-id",space["space_id"],"--lock-fd",str(fd)],start_new_session=True,close_fds=False,pass_fds=(fd,))
            logger.info(f"Spawned recorder @{handle}")
        else:
            release_lock(handle, fd)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_monitor()
