#!/usr/bin/env python3
"""tools/ingest_watch.py: the pp-ingest service and its reports (docs/audits/INGEST_DESIGN.md).

  run                     the long-running watcher (tmux pipeline_pp_ingest_watch); no GPU, no cron
  once [--no-watch]       one watch + fetch + mine pass, then exit (tests and the outage drill)
  status                  the live numbers (also written to <store>/ingest/live.json every minute)
  coverage [--hours 24]   the coverage check now (also daily at 06:00 ET inside `run`)
  moments --since ISO     the packager's read: best unused moments since T (ledger adapter), as JSON lines
  handoff --main DIR      list (default) or --apply the staging transcript files absent from the main store
  ab ...                  the blind A/B of back-ends on saved universes (pipeline/ingest/ab.py)
  flagcheck ...           a second model's check of the miner's hard flags (ruling 40; measurement only:
                          pipeline/ingest/flagcheck.py)
  hooks [--hours 12]      ruling 80: the hook pass per video (rows, cost, state), newest first (read only)
  purge [--apply]         ruling 77: one pass of the rolling purge of expired media (default: a dry run that
                          deletes nothing); --measure also sizes the media it never deletes. The watcher
                          runs the same pass every 10 min in its own loop (pipeline/ingest/purge.py)

Store: PP_INGEST_STORE (default <repo>/data/editorial; refused inside the main tree unless PP_INGEST_ALLOW_MAIN_STORE=1).
One service per store: `run` and `once` refuse a store another service holds (<store>/ingest/service.lock).
Gateway base URL for a drill: the runtime override file <store>/ingest/overrides.json ({"<back-end id>": {"base_url":
"http://127.0.0.1:9/api/v1"}}; only this machine or the configured host is honoured), or the back-end's base_url_env.
Spend freeze: providers.json spend_freeze (vendors never called by any role; lift = remove, restart).
"""
import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from pipeline.ingest import config  # noqa: E402


def _aware(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise SystemExit(f"{s}: give a timezone (e.g. 2026-11-12T00:00:00+00:00)")
    return d


def cmd_run(a):
    from pipeline.ingest.service import Service
    Service().run()


def cmd_once(a):
    from pipeline.ingest.service import Service
    s = Service()
    s.meter.measure()
    s.last_measure = s.clock()
    if not a.no_watch:
        s.watch_once()
    for _ in range(a.fetch_rounds):
        if not s.fetch_once(limit=a.fetch_limit):
            break
    while s.mine_once(wait=True):
        pass
    print(json.dumps(s.health_once(force_coverage=a.coverage), indent=1, default=str))
    s.close()


def cmd_status(a):
    from pipeline.ingest import queue as Q, stats
    p = config.paths()
    q = Q.Queue(p["queue"])
    out = stats.live(q, hours=a.hours)
    try:                                          # ruling 87: the watcher's own view of the shared signal (live.json,
        with open(p["live"]) as f:                # written by its health loop every 60 s), with that file's age
            sig = json.load(f).get("down_signal")
        if sig is not None:
            out["down_signal"] = dict(sig, from_live_json_age_s=round(time.time() - os.path.getmtime(p["live"])))
            out["paid_route"] = sig.get("paid_route")             # ruling 98: is the miner on the paid route?
    except (OSError, ValueError):
        out["down_signal"] = None
    print(json.dumps(out, indent=1, default=str))


def cmd_coverage(a):
    from pipeline.ingest import coverage, queue as Q, watch
    p = config.paths()
    config.ts()
    rep = coverage.check(Q.Queue(p["queue"]), watch.YouTubeGate(), hours=a.hours)
    path = coverage.write(rep, p["coverage"])
    print(json.dumps({k: rep[k] for k in ("published", "shorts", "eligible", "mined", "coverage", "measured")}, indent=1))
    print(path)


def cmd_moments(a):
    from pipeline.ingest import ledger, watch
    p = config.paths()
    reg, _ = watch.registry()
    optout, oerr = watch.optouts()
    if oerr:
        raise SystemExit(f"refused: {oerr}")
    delivered = []
    if a.delivered:
        with open(a.delivered) as f:
            delivered = [l.strip() for l in f if l.strip()]
    out, rep = ledger.best_unused_moments(p["ledger"], _aware(a.since), datetime.now(timezone.utc), delivered,
                                          registry=reg, optout=optout, store_root=p["root"], limit=a.limit)
    for l in out:
        print(json.dumps(l, ensure_ascii=False, sort_keys=True))
    print(json.dumps({"report": rep}), file=sys.stderr)


def cmd_handoff(a):
    """Copy (with --apply) staging transcript files that the main store lacks. Never overwrites; verifies every
    record's transcript_sha256 before listing it."""
    p = config.paths()
    ts = config.ts()
    main = os.path.realpath(a.main)
    plan, refused = [], []
    import re
    for vid in sorted(os.listdir(p["transcripts"])):
        sdir = os.path.join(p["transcripts"], vid)
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) or not os.path.isdir(sdir):
            refused.append((sdir, "not a video id directory"))
            continue
        for name in sorted(os.listdir(sdir)):
            if not (name == "meta.json" or re.fullmatch(r"transcript\.[A-Za-z0-9_.-]+\.json", name)):
                continue
            src, dst = os.path.join(sdir, name), os.path.join(main, "transcripts", vid, name)
            if os.path.exists(dst):
                continue
            if name.startswith("transcript."):
                with open(src) as f:
                    rec = json.load(f)
                if ts.segments_sha256(rec["segments"]) != rec["transcript_sha256"]:
                    refused.append((src, "transcript_sha256 mismatch"))
                    continue
            plan.append((src, dst))
    for src, dst in plan:
        print(("COPY " if a.apply else "would copy ") + f"{src} -> {dst}")
        if a.apply:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tmp = dst + ".handoff.tmp"
            shutil.copyfile(src, tmp)
            try:
                os.link(tmp, dst)             # fails if dst appeared meanwhile: write-once like the store
            finally:
                os.unlink(tmp)                # never left behind, whether the link was made or refused
    for src, why in refused:
        print(f"REFUSED {src}: {why}")
    print(f"{len(plan)} files {'copied' if a.apply else 'to copy'}, {len(refused)} refused")


def cmd_ab(a):
    from pipeline.ingest import ab
    ab.main(a)


def cmd_flagcheck(a):
    from pipeline.ingest import flagcheck
    flagcheck.main(a)


def cmd_hooks(a):
    from pipeline.ingest import mine
    from pipeline.ingest import queue as Q
    q = Q.Queue(config.paths()["queue"])
    since = q.clock() - a.hours * 3600
    if a.rerun:                                       # the watcher's hook loop asks the CURRENT hook question again
        n = q.x("UPDATE videos SET hook_ts=NULL, hook_tries=0, hook_next_ts=NULL, hook_note=? WHERE state IN (?, ?) "
                "AND published_ts >= ? AND hook_ts IS NOT NULL AND (hook_version IS NULL OR hook_version <> ?)",
                (f"re-run: {mine.HOOK_PROMPT_VERSION}", Q.MINED, Q.MINED_PARTIAL, max(since, q.clock() - 12 * 3600),
                 mine.HOOK_PROMPT_VERSION)).rowcount
        q.event("hooks_rerun", None, None, version=mine.HOOK_PROMPT_VERSION, videos=n)
        print(f"{n} videos of the last 12 h queued for the hook pass again ({mine.HOOK_PROMPT_VERSION}), newest first")
    rows = q.rows("SELECT video_id, channel_id, title, published_at, state, moments, hook_ts, hook_rows, hook_cost_usd, "
                  "hook_note, hook_tries FROM videos WHERE published_ts >= ? AND state IN (?, ?) "
                  "ORDER BY published_ts DESC", (since, Q.MINED, Q.MINED_PARTIAL))
    done = [r for r in rows if r["hook_ts"]]
    print(f"{len(rows)} mined videos published in the last {a.hours:g} h; hook pass done on {len(done)}; "
          f"{sum(r['hook_rows'] or 0 for r in done)} hook rows; ${sum(r['hook_cost_usd'] or 0 for r in rows):.4f}")
    for r in rows:
        state = (f"{r['hook_rows']} hook rows, ${(r['hook_cost_usd'] or 0):.4f}" if r["hook_ts"] else
                 f"waiting ({r['hook_note'] or 'not yet run'})")
        print(f"  {r['published_at']}  {r['video_id']}  {(r['title'] or '')[:60]!r}: {state}")


def cmd_purge(a):
    from pipeline.ingest import purge
    from pipeline.ingest import queue as Q
    spec = purge.load_spec()
    p = config.paths()
    rep = purge.run_pass(spec, q=Q.Queue(p["queue"]), dry_run=not a.apply, log_dir=p["purge"])
    print(purge.summary(rep))
    for r in rep["delivered_runs"]:
        print(f"  delivered (kept): {r['run']} ({', '.join(r['why'])})")
    for v, why in sorted(((rep.get("one_copy_per_delivery") or {}).get("unresolved") or {}).items()):
        print(f"  unresolved, every copy kept (A19): {v}: {why}")                  # audit a19 c2 (minimax N-5)
    for f in rep.get("would_delete") or []:
        print(f"  would delete: {f['path']} ({f['bytes'] / 1e6:.1f} MB; video {f['video_id']}, {f['age_h']} h old)")
    if a.measure:
        for r in purge.measure_reported(spec):
            print(f"  never deleted, reported: {r['name']}: {r['files']} media files, {r['bytes'] / 1e9:.2f} GB "
                  f"({r['what']})")
    if a.json:
        print(json.dumps(rep, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    o = sub.add_parser("once")
    o.add_argument("--no-watch", action="store_true")
    o.add_argument("--fetch-rounds", type=int, default=50)
    o.add_argument("--fetch-limit", type=int, default=10)
    o.add_argument("--coverage", action="store_true")
    o.set_defaults(fn=cmd_once)
    s = sub.add_parser("status")
    s.add_argument("--hours", type=float, default=24)
    s.set_defaults(fn=cmd_status)
    c = sub.add_parser("coverage")
    c.add_argument("--hours", type=float, default=24)
    c.set_defaults(fn=cmd_coverage)
    m = sub.add_parser("moments")
    m.add_argument("--since", required=True)
    m.add_argument("--delivered", help="file of moment ids delivered in the previous 24 h, one per line")
    m.add_argument("--limit", type=int)
    m.set_defaults(fn=cmd_moments)
    h = sub.add_parser("handoff")
    h.add_argument("--main", required=True)
    h.add_argument("--apply", action="store_true")
    h.set_defaults(fn=cmd_handoff)
    b = sub.add_parser("ab")
    from pipeline.ingest import ab as _ab
    _ab.add_args(b)
    b.set_defaults(fn=cmd_ab)
    hk = sub.add_parser("hooks")
    hk.add_argument("--hours", type=float, default=12.0)
    hk.add_argument("--rerun", action="store_true", help="queue the last 12 h's mined videos whose completed hook "
                    "pass asked an older hook question for the current one; the watcher's loop does the work, newest "
                    "first. Idempotent per version (a pass completed under the current question is never queued "
                    "again); a video still in a pass is left to it")
    hk.set_defaults(fn=cmd_hooks)
    pg = sub.add_parser("purge")
    pg.add_argument("--apply", action="store_true", help="delete (default: a dry run)")
    pg.add_argument("--measure", action="store_true", help="also size the media outside the targets")
    pg.add_argument("--json", action="store_true")
    pg.set_defaults(fn=cmd_purge)
    fc = sub.add_parser("flagcheck")
    from pipeline.ingest import flagcheck as _fc
    _fc.add_args(fc)
    fc.set_defaults(fn=cmd_flagcheck)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
