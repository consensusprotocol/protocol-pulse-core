#!/usr/bin/env python3
"""pipeline/transcript_ingest.py — background transcript ingestion (editorial infrastructure).

Scans every enabled registry channel with a channel_id (editorial universe; layout approval is
irrelevant here), registers recent uploads, and acquires a transcript once per video via the
transcript_store policy (captions first, Whisper on 429/unavailable). Steady state: cron every
30 min, so production runs query an already-understood recent universe.

Safety:
  - single instance (flock on data/editorial/state/ingest.lock)
  - GPU0 only (CUDA_VISIBLE_DEVICES=0); Whisper is skipped (captions-only pass) while a production
    render/orchestrator is running, unless --allow-during-run
  - bounded: --hours window and --max-whisper-hours audio budget per invocation

Usage:
  CUDA_VISIBLE_DEVICES=0 python3 pipeline/transcript_ingest.py --hours 72 --max-whisper-hours 80
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

import transcript_store as ts  # noqa: E402
from scan import fetch_rss, parse_iso_datetime  # noqa: E402

CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")
PRODUCTION_PATTERNS = ("run_isolated.py", "run_fresh.py", "render16", "render_vertical")


def editorial_channels():
    with open(CHANNELS_PATH) as f:
        return [c for c in json.load(f) if c.get("enabled", True) and c.get("channel_id")]


def universe(hours, channels=None):
    """Recent non-Short uploads from every editorial channel: list of dicts with rss + channel."""
    channels = channels or editorial_channels()
    now = datetime.now(timezone.utc)

    def one(c):
        out = []
        for v in fetch_rss(c["channel_id"]):
            p = parse_iso_datetime(v["published"])
            if p is None or "/shorts/" in v.get("url", ""):
                continue
            age = (now - p).total_seconds() / 3600
            if 0 <= age <= hours:
                out.append({"video_id": v["video_id"], "rss": {"title": v["title"],
                            "published": v["published"]}, "channel": c, "age_h": round(age, 1)})
        return out
    with ThreadPoolExecutor(8) as ex:
        return [v for lst in ex.map(one, channels) for v in lst]


def production_running():
    out = subprocess.run(["ps", "-eo", "cmd"], capture_output=True, text=True).stdout
    return any(p in out for p in PRODUCTION_PATTERNS)


def priority(v):
    c = v["channel"]
    return (0 if c.get("layout_status") == "approved" else 1, c.get("tier", 9), v["age_h"])


def ingest(hours=72, max_whisper_hours=10.0, allow_during_run=False, log=print):
    os.makedirs(ts.STATE_DIR, exist_ok=True)
    t0 = time.time()
    vids = universe(hours)
    summary = {"started": ts.now_iso(), "hours": hours, "universe": len(vids),
               "channels": len({v["channel"]["channel_id"] for v in vids}), "status": {}}
    pending = []
    for v in sorted(vids, key=priority):
        try:
            rec, st = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"],
                                 allow_whisper=False)
        except Exception as e:
            st = f"error:{type(e).__name__}"
            log(f"  {v['video_id']} meta/captions error: {e}")
        summary["status"][v["video_id"]] = st
        if st == "pending_whisper":
            pending.append(v)
    log(f"caption pass: {len(vids)} videos, {len(pending)} need Whisper "
        f"(circuit open: {ts.caption_circuit_open()})")
    whisper_ok = allow_during_run or not production_running()
    budget = max_whisper_hours * 3600
    used = 0.0
    for v in pending:
        meta = ts.ensure_meta(v["video_id"], rss=v["rss"], channel=v["channel"])
        dur = meta.get("duration") or 0
        if not whisper_ok:
            summary["status"][v["video_id"]] = "deferred_production_running"
            continue
        if used + dur > budget:
            summary["status"][v["video_id"]] = "deferred_budget"
            continue
        t1 = time.time()
        rec, st = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"],
                             allow_whisper=True, try_captions=False)
        used += dur
        summary["status"][v["video_id"]] = st
        log(f"  whisper {v['video_id']} {v['channel']['display_name']}: {st} "
            f"({dur / 60:.0f} min audio in {time.time() - t1:.0f}s)")
    summary.update(ended=ts.now_iso(), seconds=round(time.time() - t0),
                   whisper_audio_hours=round(used / 3600, 2))
    counts = {}
    for st in summary["status"].values():
        counts[st] = counts.get(st, 0) + 1
    summary["counts"] = counts
    with open(os.path.join(ts.STATE_DIR, "ingest_runs.jsonl"), "a") as f:
        f.write(json.dumps({k: v for k, v in summary.items() if k != "status"}) + "\n")
    log(f"ingest done: {counts} in {summary['seconds']}s")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=72)
    ap.add_argument("--max-whisper-hours", type=float, default=10.0)
    ap.add_argument("--allow-during-run", action="store_true")
    a = ap.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        sys.exit("CUDA_VISIBLE_DEVICES must be 0")
    os.makedirs(ts.STATE_DIR, exist_ok=True)
    lock = open(os.path.join(ts.STATE_DIR, "ingest.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another ingest is running; exit")
        return
    print(f"=== TRANSCRIPT INGEST {ts.now_iso()} ===", flush=True)
    ingest(a.hours, a.max_whisper_hours, a.allow_during_run,
           log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    main()
