"""RULING 142 (3), the route's missing half (Nov 23). A post_live stream's DASH section can TIME OUT instead of coming
back without media: Bitcoin Magazine U7X6kReXets (BMTV Nov 23, 7134 s, post_live) ran past --download-sections' 120 s
twice (19:03 and 19:48 ET). select_passages._download_window then returns None before its whole-stream route
(_post_live_window) is ever tried, and the window is lost to the lock pre-check and to the render alike.

prefetch() runs before pinned.acquire, in the render's stage_pinned and in the lock pre-check's prefetch. When the
normal download leaves no window and the video's live_status is post_live, it cuts the window through
_post_live_window itself, at the same path and with the same start, and writes its .post_live.json record. pinned.acquire
then finds the file (its cache hit) and runs ruling 142 (3)'s HARD clock guard on it, as on the route's other entry.
select_passages.py and pinned.py (decoder files) are unchanged.
"""
import json
import os
import subprocess

PIPELINE = os.path.dirname(os.path.abspath(__file__))
COOKIES = os.path.join(os.path.dirname(PIPELINE), "data", "yt_cookies.txt")
PAD_S = 15.0                    # select_passages._download_window's default pad: the same window, the same start


def live_status(video_id):
    """yt-dlp's live_status for the video (post_live, was_live, not_live ...), or None when it cannot be read."""
    cmd = ["yt-dlp", "-J", "--skip-download", "--no-warnings", f"https://www.youtube.com/watch?v={video_id}"]
    if os.path.exists(COOKIES):
        cmd += ["--cookies", COOKIES]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)    # batch 119 cycle 1 (qwen F1)
        d = json.loads(r.stdout or "{}")
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None
    return d.get("live_status") if isinstance(d, dict) else None


def prefetch(video_id, start_s, end_s, run_dir, log=print):
    """The window pinned.acquire will ask for: -> (path, dl_start) as _download_window returns it, or None."""
    from select_passages import _download_window, _post_live_window
    res = _download_window(video_id, start_s, end_s, run_dir)
    if res and res[0]:
        return res
    status = live_status(video_id)
    if status != "post_live":
        log(f"  {video_id}: the window did not download (live_status {status}): no whole-stream route")
        return None
    out = os.path.join(run_dir, "sources", f"{video_id}.mp4")
    dl_start = float(round(max(0, start_s - PAD_S)))
    log(f"  {video_id}: post_live, the window did not download: cutting it from the whole stream (ruling 142 (3))")
    if _post_live_window(video_id, dl_start, end_s + PAD_S, out, COOKIES if os.path.exists(COOKIES) else None):
        return out, dl_start
    log(f"  {video_id}: the whole-stream route gave no media")
    return None
