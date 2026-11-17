#!/usr/bin/env python3
"""pipeline/transcript_ingest.py — background transcript ingestion (editorial infrastructure).

Scans every enabled registry channel with a channel_id (editorial universe; layout approval is
irrelevant here), registers recent uploads, and acquires a transcript once per video via the
transcript_store policy (captions first, Whisper on 429/unavailable). Steady state: cron every
30 min, so production runs query an already-understood recent universe.

Safety:
  - single instance (flock on data/editorial/state/ingest.lock)
  - GPU0 only (CUDA_VISIBLE_DEVICES=0, CUDA_DEVICE_ORDER=PCI_BUS_ID set by main()); Whisper is skipped
    (captions-only pass) while a production render/orchestrator is running, unless --allow-during-run
  - law L-r (no lease, no load): Whisper loads only while this process holds the GPU0 lease, and is unloaded
    before it is left. Before this (Nov 12-15) every run that needed Whisper died on gpu0.LeaseMissing.
  - who comes first (orchestrator order '13:05' ET Nov 16, pp-ingest's request R13; "builds and renders keep
    priority over Whisper; Whisper runs between calls"):
      * A render comes first. While its yield flag is up (local_judge.YIELD_FLAG) the pass stops, and the
        remaining videos wait for the next run. The flag is checked before every video, so the pass stops
        after the one in hand.
      * A build's GPU0 service that wants the card (gpu0_want.wanted(): the scorer, the pre-check) comes
        first too, and so does another owner of the lease. The pass WAITS, polling every LEASE_POLL_S and
        holding nothing, at most LEASE_WAIT_S in all per run. Each attempt is non-blocking.
      * A build that wants GPU0 mid-pass gets it at the next file boundary: Whisper is unloaded, the lease
        goes, and the pass ENDS (batch 102): the rest wait for the next run. Once Whisper has loaded, this
        process holds a CUDA context until it exits, and every other GPU0 user (the scorer, a render) sees that
        context as foreign (L-r) and stops after a 600 s wait. Batch 97's wait-and-go-on killed the stand-alone
        scorer at 15:26 ET Nov 16 that way. Waiting BEFORE the first load (no context yet) is unchanged.
    Before the order the lease was tried once at no wait, so one scorer burst at the cron's start deferred
    every video for 30 minutes.
  - bounded: --hours window and --max-whisper-hours audio budget per invocation

Usage:
  CUDA_VISIBLE_DEVICES=0 python3 pipeline/transcript_ingest.py --hours 72 --max-whisper-hours 80
"""
import argparse
import contextlib
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
OWNER = "transcript_ingest Whisper pass (cron, GPU0)"
LEASE_WAIT_S = 1500.0       # order '13:05': the most one run waits for GPU0 in all (cron */30, one instance at a time)
LEASE_POLL_S = 5.0


def editorial_channels():
    with open(CHANNELS_PATH) as f:
        return [c for c in json.load(f) if c.get("enabled", True) and c.get("channel_id")]


def universe(hours, channels=None):
    """Recent non-Short uploads from every editorial channel: list of dicts with rss + channel. An entry older than
    the window by its RSS time stays in when the store holds it as a stream that aired inside the window
    (transcript_store.stream_start; pp-ingest R14, INGEST-FAIL-03); its age_h is then the stream's."""
    channels = channels or editorial_channels()
    now = datetime.now(timezone.utc)

    def one(c):
        out = []
        for v in fetch_rss(c["channel_id"]):
            p = parse_iso_datetime(v["published"])
            if p is None or "/shorts/" in v.get("url", ""):
                continue
            age = (now - p).total_seconds() / 3600
            if age > hours:                              # pp-ingest R14: a stream is dated by when it aired; its RSS
                start = ts.stream_start(v["video_id"])   # time is when it was scheduled, days before
                if start is not None:
                    age = (now - start).total_seconds() / 3600
            if 0 <= age <= hours:
                out.append({"video_id": v["video_id"], "rss": {"title": v["title"],
                            "published": v["published"]}, "channel": c, "age_h": round(age, 1)})
        return out
    with ThreadPoolExecutor(8) as ex:
        return [v for lst in ex.map(one, channels) for v in lst]


def production_running():
    out = subprocess.run(["ps", "-eo", "cmd"], capture_output=True, text=True).stdout
    return any(p in out for p in PRODUCTION_PATTERNS)


def gpu0_turn(hold, waited, log=print):
    """-> (None, waited) when this process now holds GPU0 for Whisper. The lease is entered into `hold`, an ExitStack,
    and Whisper's unload is registered to run first when `hold` closes, while the lease is still held (GPU0 left as
    found). Otherwise -> (why not, waited), the deferred videos' status.

    Order '13:05' (R13):
    - A render being launched (its yield flag) comes first: the pass stops at once. pulse_check_run exits 75 on a
      held lease, so a render must never find this pass starting; the flag is read right before every attempt.
    - A build's GPU0 service that wants the card comes first too (gpu0_want.wanted()), and so does any other owner of
      the lease: wait, polling every LEASE_POLL_S and holding nothing, until neither is true. Each attempt is
      non-blocking (wait_s=0).
    - `waited` is this run's waiting so far; past LEASE_WAIT_S the remaining videos wait for the next run."""
    import gpu0
    import gpu0_want
    import local_judge as LJ
    while True:
        if LJ.render_wants_gpu0():
            return "deferred_render_wants_gpu0", waited
        builds = gpu0_want.wanted()
        if builds:
            busy = f"wanted by {', '.join(builds)}"
        else:
            try:
                hold.enter_context(gpu0.lease(OWNER, wait_s=0))
                hold.callback(ts.release_whisper)        # LIFO: runs first on leaving, while the lease is still held
                return None, waited
            except gpu0.LeaseBusy as e:
                busy = str(e)
        if waited >= LEASE_WAIT_S:
            log(f"  GPU0 not free for Whisper after {waited:.0f} s of waiting ({busy}): the rest wait for the next run")
            return "deferred_gpu0_busy", waited
        time.sleep(LEASE_POLL_S)
        waited += LEASE_POLL_S


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
    import gpu0_want
    import local_judge as LJ
    hold, waited = None, 0.0                             # law L-r: the GPU0 lease for Whisper, while held
    try:
        for i, v in enumerate(pending):
            meta = ts.ensure_meta(v["video_id"], rss=v["rss"], channel=v["channel"])
            dur = meta.get("duration") or 0
            if not whisper_ok:
                summary["status"][v["video_id"]] = "deferred_production_running"
                continue
            if used + dur > budget:
                summary["status"][v["video_id"]] = "deferred_budget"
                continue
            if hold is not None and (LJ.render_wants_gpu0() or gpu0_want.wanted()):
                hold.close()                             # this file boundary: Whisper unloaded, then the lease goes
                hold = None                              # batch 102: and the pass ENDS, so that this process (its
                why = "deferred_render_wants_gpu0" if LJ.render_wants_gpu0() else "deferred_gpu0_yielded"
                for w in pending[i:]:                    # CUDA context) is gone before anyone else loads on GPU0
                    summary["status"][w["video_id"]] = why
                log(f"  Whisper gives GPU0 back at this file boundary (a render or a build asked) and the pass ends: "
                    f"{len(pending) - i} video(s) wait for the next run (this process's CUDA context must not "
                    f"outlive its turn: L-r)")
                break
            if hold is None:
                hold = contextlib.ExitStack()
                why, waited = gpu0_turn(hold, waited, log)
                if why:                                  # this video and every one after it: the next run
                    hold.close()
                    hold = None
                    for w in pending[i:]:
                        summary["status"][w["video_id"]] = why
                    log(f"  Whisper pass stops: {why} ({len(pending) - i} video(s) deferred)")
                    break
            t1 = time.time()
            rec, st = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"],
                                 allow_whisper=True, try_captions=False)
            used += dur
            summary["status"][v["video_id"]] = st
            log(f"  whisper {v['video_id']} {v['channel']['display_name']}: {st} "
                f"({dur / 60:.0f} min audio in {time.time() - t1:.0f}s)")
    finally:
        if hold is not None:
            hold.close()                                 # Whisper unloaded, then the lease goes (also on an error)
    summary.update(waited_for_gpu0_s=round(waited))
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
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"   # law L-r: CUDA device 0 is nvidia-smi GPU 0 (gpu0.require checks
    #                                                  it; the cron line sets only CUDA_VISIBLE_DEVICES), before any load
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
