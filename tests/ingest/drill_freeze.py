#!/usr/bin/env python3
"""Outage drill under the spend freeze (orchestrator 05:30 ET 2026-11-12), real components, scratch store.

The real Service, Router, providers.json (Heimdall then local; OpenAI / Anthropic / xAI / Google frozen), yt-dlp and
transcript_store, on ONE real channel in a scratch store (never the live watcher's). Heimdall's base URL is pointed at
a dead port through the runtime override file; the videos must WAIT (mine_waiting, reason OUTAGE, no try used, never
mined_partial) for as many passes as the outage lasts, with no call to any frozen vendor; when the override is removed
the breaker's half-open probe finds Heimdall again and every video is mined. The STATE notice the meter would write
(its /credits read goes to the dead URL too) is written to a scratch copy, never to the real STATE file.

  PP_INGEST_STORE=<scratch> PP_INGEST_CHANNELS=<slug> python3 tests/ingest/drill_freeze.py --out <report.json>
"""
import argparse
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from pipeline.ingest import config, providers, service  # noqa: E402
from pipeline.ingest import queue as Q  # noqa: E402

DEAD = {"heimdall_qwen27b": {"base_url": "http://127.0.0.1:9/api/v1"}}


def snapshot(s):
    vids = s.q.rows("SELECT video_id, state, mine_tries, windows, windows_failed, moments, reason FROM videos "
                    "WHERE state NOT IN (?,?)", (Q.SEEN_OLD, Q.SHORT))
    calls = s.q.rows("SELECT backend, kind, COUNT(*) AS n, ROUND(SUM(COALESCE(cost_usd,0)),5) AS usd FROM calls "
                     "GROUP BY backend, kind")
    return {"at": config.iso(), "videos": [dict(v, reason=(v["reason"] or "")[:160]) for v in vids],
            "calls": [dict(c) for c in calls], "router": {b: {k: v for k, v in snap.items() if k in (
                "open", "why", "frozen", "vendor", "enabled")} for b, snap in s.router.snapshot().items()}}


def passes(s, n, log):
    for i in range(n):
        s.q.x("UPDATE videos SET next_at=0 WHERE state IN (?,?)", (Q.MINE_WAIT, Q.MINED_PARTIAL))
        while s.mine_once(wait=True):
            pass
        log.append(dict(snapshot(s), step=f"outage pass {i + 1}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--outage-passes", type=int, default=10)
    a = ap.parse_args()
    p = config.paths()
    if os.path.realpath(p["root"]).startswith(os.path.realpath(os.path.join(REPO, "data"))):
        raise SystemExit("refused: give a scratch PP_INGEST_STORE (never the live watcher's store)")
    os.makedirs(p["ingest"], exist_ok=True)
    state_copy = os.path.join(p["ingest"], "STATE_drill_copy.md")
    open(state_copy, "w").write("# drill copy of the STATE file\n")
    real_notice, real_outage = service.spend.write_state_notice, service.spend.write_outage_notice
    service.spend.write_state_notice = lambda st, snap, **k: real_notice(st, snap, **dict(k, doc=state_copy))
    service.spend.write_outage_notice = lambda n, since, **k: real_outage(n, since, **dict(k, doc=state_copy))
    with open(p["overrides"], "w") as f:
        json.dump(DEAD, f)
    log = []
    s = service.Service(log=lambda m: log.append({"log": m}))
    try:
        s.meter.measure()
        s.last_measure = s.clock()
        log.append({"step": "start", "chain": s.router.chain("mine"), "callable": s.router.effective("mine"),
                    "frozen": sorted(providers.frozen_vendors(s.cfg)), "meter": s.meter.state()})
        s.watch_once()
        for _ in range(10):
            if not s.fetch_once(limit=10):
                break
        log.append(dict(snapshot(s), step="fetched"))
        passes(s, a.outage_passes, log)
        os.unlink(p["overrides"])                         # the outage ends
        t_restore = time.time()
        log.append({"step": "override removed", "at": config.iso()})
        deadline = time.time() + 900
        while time.time() < deadline:
            s.q.x("UPDATE videos SET next_at=0 WHERE state IN (?,?)", (Q.MINE_WAIT, Q.MINED_PARTIAL))
            while s.mine_once(wait=True):
                pass
            if not s.q.rows("SELECT 1 FROM videos WHERE state IN (?,?,?)", (Q.MINE_WAIT, Q.TRANSCRIBED, Q.MINING)):
                break
            time.sleep(20)
        log.append(dict(snapshot(s), step="after restore", restore_to_done_s=round(time.time() - t_restore)))
        s.meter.measure()
        log.append({"step": "meter", "state": s.meter.state(), "snap": s.meter.snapshot()})
    finally:
        s.close()
        if os.path.exists(p["overrides"]):
            os.unlink(p["overrides"])
    frozen_calls = [c for c in log[-3]["calls"] if c["backend"] not in ("heimdall_qwen27b", "local_gemma")] \
        if "calls" in log[-3] else None
    with open(a.out, "w") as f:
        json.dump({"log": log, "frozen_vendor_calls": frozen_calls}, f, indent=1, default=str)
    print(json.dumps({"final": log[-2], "frozen_vendor_calls": frozen_calls}, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
