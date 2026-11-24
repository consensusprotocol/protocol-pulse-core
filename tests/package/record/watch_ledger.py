"""BATCH 3's ledger watcher (orchestrator 08:56 ET Nov 15, item 3: build on every ledger change, with a 30-minute
fallback poll). Read-only on the ledger, the word pass and the store; no model call; no GPU.

It polls every POLL_S seconds and ENDS (so the builder is re-invoked) with:
- CHANGED: a new moment in the 12-h ledger, a moment newly word-ready (a ready window record in word_pass.jsonl, or a
  full-video word record in the store), or a word-pass row (any status) for a ledger moment that had none or another;
- FALLBACK: FALLBACK_S after it started, whatever happened, so a missed event cannot idle the builder.
An expiry alone does not end it (nothing new to judge); it is printed. An adapter failure is printed and polled again.
The baseline is BASE (WATCH_BASE.json beside this file): what the builder last acted on, written only by --mark.

Usage: python3 -B watch_ledger.py --mark           (after each build or check: the current state becomes the baseline)
       python3 -B watch_ledger.py --watch [POLL_S FALLBACK_S]   (default 300 1800)
       python3 -B watch_ledger.py --show           (the current state against the baseline; writes nothing)"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WT = REPO
for _p in ("pipeline", "tests/package", "tests/select_by_id", "tests/moments"):
    sys.path.insert(0, os.path.join(WT, _p))
import ledger_build as LB  # noqa: E402

BASE = os.path.join(WT, "tests", "package", "proof", "WATCH_BASE.json")   # state, never committed
SINCE = datetime.fromisoformat("2026-11-13T03:01:09+00:00")     # the build's own --since
ET = ZoneInfo("America/New_York")


def et(t=None):
    return (t or datetime.now(timezone.utc)).astimezone(ET).strftime("%H:%M:%S")


def wp_status(ids, path=LB.WORD_PASS):
    """The LAST word-pass row of each ledger moment, classified as word_pass_index classifies it."""
    last = {}
    try:
        f = open(path)
    except FileNotFoundError:
        return {}
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("moment_id") in ids:
                last[r["moment_id"]] = r
    out = {}
    for mid, r in last.items():
        if r.get("error") or r.get("window_record") is None:
            out[mid] = "failed"
        elif r.get("sentence_ready") is not True:
            out[mid] = "not_ready"
        elif isinstance(r.get("window_record"), str) and isinstance(r.get("record_sha256"), str):
            out[mid] = "ready"
        else:
            out[mid] = "unreadable"
    return out


def state():
    now = datetime.now(timezone.utc)
    rows, rep = LB.rows(SINCE, now, horizon_h=12.0)
    ids = {r["moment_id"] for r in rows}
    st = wp_status(ids)
    full = {r["video_id"] for r in rows
            if any(os.path.exists(os.path.join(LB.STORE, "transcripts", r["video_id"], n)) for n in LB.WORD_RECORDS)}
    ready = {r["moment_id"] for r in rows if st.get(r["moment_id"]) == "ready" or r["video_id"] in full}
    return {"at": now.isoformat(timespec="seconds"), "ids": sorted(ids),
            "videos": sorted({r["video_id"] for r in rows}), "channels": sorted({r["channel_id"] for r in rows}),
            "word_pass": st, "full_video": sorted(full), "word_ready": sorted(ready),
            "excluded": rep.get("excluded")}


def diff(base, cur):
    new = sorted(set(cur["ids"]) - set(base["ids"]))
    ready = sorted(set(cur["word_ready"]) - set(base["word_ready"]))
    rows = sorted(mid for mid in cur["ids"] if mid in base["ids"] and cur["word_pass"].get(mid) != base["word_pass"].get(mid))
    gone = sorted(set(base["ids"]) - set(cur["ids"]))
    return new, ready, rows, gone


def brief(s):
    return (f"{len(s['ids'])} moments in 12 h ({len(s['videos'])} videos, {len(s['channels'])} channels), "
            f"{len(s['word_ready'])} word-ready, {len(s['word_pass'])} with a word-pass row, "
            f"{len(s['full_video'])} videos with a full-video word record")


def main(argv):
    mode = argv[0] if argv else "--show"
    if mode == "--mark":
        s = state()
        with open(BASE + ".tmp", "w") as f:
            json.dump(s, f, indent=1)
        os.replace(BASE + ".tmp", BASE)
        print(f"MARKED at {et()} ET: {brief(s)}")
        return 0
    if not os.path.exists(BASE):
        print("no baseline: run --mark first")
        return 2
    base = json.load(open(BASE))
    if mode == "--show":
        cur = state()
        print(f"baseline {et(datetime.fromisoformat(base['at']))} ET: {brief(base)}")
        print(f"now {et()} ET: {brief(cur)}; new/ready/rows/gone: {diff(base, cur)}")
        return 0
    poll_s, fallback_s = (float(argv[1]), float(argv[2])) if len(argv) >= 3 else (300.0, 1800.0)
    t_end = time.time() + fallback_s
    print(f"watching from the baseline of {et(datetime.fromisoformat(base['at']))} ET ({brief(base)}) at {et()} ET; "
          f"poll {poll_s:g} s, fallback {fallback_s:g} s", flush=True)
    seen_gone = set()
    while True:
        try:
            cur = state()
        except Exception as e:                           # noqa: BLE001  a failed read is printed, never a change
            print(f"{et()} adapter or read failed ({type(e).__name__}: {str(e)[:200]})", flush=True)
            cur = None
        if cur is not None:
            new, ready, rows, gone = diff(base, cur)
            if set(gone) - seen_gone:
                print(f"{et()} expired since the baseline (no build: nothing new): {len(gone)}", flush=True)
                seen_gone |= set(gone)
            if new or ready or rows:
                print(f"CHANGED at {et()} ET: new {len(new)} {new[:20]}; newly word-ready {len(ready)} {ready[:20]}; "
                      f"word-pass rows changed {len(rows)} {[(m, cur['word_pass'].get(m)) for m in rows[:20]]}; "
                      f"now {brief(cur)}", flush=True)
                return 0
        if time.time() >= t_end:
            print(f"FALLBACK at {et()} ET: no change since the baseline; now " +
                  (brief(cur) if cur is not None else "unread (the last poll failed)"), flush=True)
            return 0
        time.sleep(max(1.0, min(poll_s, t_end - time.time())))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
