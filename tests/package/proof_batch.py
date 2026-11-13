#!/usr/bin/env python3
"""ORCHESTRATOR 00:05 ET Nov 13 (PBX on the L-y medley: "new batch!"): up to THREE novel L-y medleys, ranked, sealed.

Why rebuilds: the four L-y packages of the 20:30 re-run (fresh_20261112_001448, fresh_20261111_213954,
fresh_20261111_192645, fresh_20261111_190259) were built with delivered=() and every one reuses delivered moments.
Each opens on the hook wdk5JZ9hPzs 3218.1-3221.6 (in 37c5b5f5 and 41f29b1f) and carries c1JGheQBPH4 2403.2-2422.1 (in
41f29b1f); 001448 is 41f29b1f clip for clip. The order's item 2 ("no moment reused") therefore rebuilds every one from
the remaining moments.

build RUN: one universe's medley, built by the packager as it stands (house style in the writer's prompt and in the
STYLE lint, recency facts per segment, ruling 5's budget and deadlines):
- "now" is the RENDER clock (ruling 1): step A, L-v 3 and currency are judged against tonight.
- Novelty: every clip span of --delivered (the delivered pins) and of --exclude (the batch's kept packages) goes to
  package.usable as delivered, which drops any moment that overlaps one in the same video (L-p).
- --avoid-videos drops every moment of those source videos first ("no source video used twice across the batch if
  avoidable"). When such a build finds no package, a second build without the avoidance is the order's "if
  avoidable"; it is a separate run with its own tag.
- The legs and meters are proof_ly's. Spend goes to the batch's own ledger, SPEND_BATCH.json (estimate ceiling
  BATCH_LIMIT_USD). The order's budget is $6 vendor-reported for the batch.
Writes tests/package/proof/<RUN>/package_batch_<tag>.json (the package, or why none) and package_batch_<tag>.log.

seal RUN --tag T: the kept package's speakers (speakers.attribute_package: the source's own lines and the transcript
around each clip; "unknown" unless the text shows it), then the pin through package_pin.to_pin (every gate, recency
and speaker check) -> tests/package/proof/<RUN>/MOMENTS_PIN_BATCH_<T>.json; the speakers are written back into
package_batch_<T>.json.

Usage: python3 tests/package/proof_batch.py build RUN --tag T --delivered PIN ... [--exclude PKG_JSON ...]
                                                   [--avoid-videos VID ...]
       python3 tests/package/proof_batch.py seal RUN --tag T
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import eligibility as E  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import proof_ledger as PLG  # noqa: E402
import proof_ly as PL  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402

OUT = PL.OUT
SPEND = os.path.join(OUT, "SPEND_BATCH.json")
BATCH_LIMIT_USD = 30.0     # the price-table estimate ceiling for the batch's own ledger (an upper bound; the
                           # reported cost ran about 1/8 of it tonight); ruling 5's per-package $1.50 reported and
                           # $5 estimate still stop each build; the order's batch budget is $6 vendor-reported


def package_spans(paths):
    """Every clip span of the batch's kept packages (package_batch_*.json) -> [{video_id, start, end, pin}]."""
    out = []
    for p in paths:
        with open(p) as f:
            res = json.load(f)
        pk = res.get("package")
        if not pk:
            raise ValueError(f"{p}: holds no package")
        out += [{"video_id": s["video_id"], "start": float(s["start"]), "end": float(s["end"]),
                 "pin": f"batch:{os.path.basename(os.path.dirname(p))}"} for s in pk["segments"]]
    return out


def build(run, tag, delivered, avoid, router, own, used, say, work_dir):
    rec_m = json.load(open(os.path.join(PL.PM.OUT, run, "moments.json")))
    words, captions, ctx_u, saved = PL.PM.universe_sources(run)
    sources = {s.video_id: s for s in words}
    now = datetime.now(timezone.utc)
    ctx = E.Context(now, PL.PM.PS.REG, ledger=PL.PM.PS.ledger_entries())
    moments = [m for m in rec_m["moments"] if m["video_id"] not in avoid]
    say(f"  {len(rec_m['moments'])} moments, {len(rec_m['moments']) - len(moments)} on avoided videos out; "
        f"{len(delivered)} delivered or kept spans out; now (render clock) {now.isoformat(timespec='seconds')}")
    e0, b0 = own["est"], own["best"]
    u0 = dict(used)
    t0 = time.time()
    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a_now.json"),
                   spend=lambda: (own["est"], own["best"]))
    res.update(run=run, tag=tag, seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"] - e0, 4),
               usd_best_known=round(own["best"] - b0, 4), code=PL.code_sha(), chains=router.chains,
               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"), as_of=now.isoformat(), avoid_videos=sorted(avoid),
               delivered_spans=delivered,
               full={k: round(used[k] - u0[k], 4) for k in ("est", "best", "model_s", "calls")})
    if res["package"]:
        res["package"]["usd_best_known"] = res["usd_best_known"]
        say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known): "
            + "; ".join(f"{s['video_id']} {float(s['start']):.1f}-{float(s['end']):.1f}"
                        for s in res["package"]["segments"]))
    else:
        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
    with open(os.path.join(OUT, run, f"package_batch_{tag}.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    return res


def seal(run, tag, router, say):
    path = os.path.join(OUT, run, f"package_batch_{tag}.json")
    with open(path) as f:
        res = json.load(f)
    pk = res.get("package")
    if not pk:
        raise ValueError(f"{path}: holds no package")
    words, captions, ctx_u, saved = PL.PM.universe_sources(run)
    SP.attribute_package(router, pk, {s.video_id: s for s in words}, log=say)
    with open(path, "w") as f:
        json.dump(res, f, indent=1, default=str)
    out, pin = package_pin.write_pin(pk, f"batch_{tag}_{run}", os.path.join(OUT, run),
                                     name=f"MOMENTS_PIN_BATCH_{tag.upper()}.json")
    say(f"PIN {os.path.relpath(out, REPO)} {pin['moments_package']['package_sha256']}")
    return out, pin


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("run")
    b.add_argument("--tag", required=True)
    b.add_argument("--delivered", nargs="+", required=True, metavar="PIN")
    b.add_argument("--exclude", nargs="*", default=[], metavar="PKG_JSON", help="the batch's kept packages")
    b.add_argument("--avoid-videos", nargs="*", default=[], metavar="VID")
    b.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
    sl = sub.add_parser("seal")
    sl.add_argument("run")
    sl.add_argument("--tag", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "seal":
        router = P.Router(env_path=PL.PM.PS.ENV, record_dir=PL.REPLIES, spend_path=SPEND,
                          limit_usd=BATCH_LIMIT_USD, chains=PL.chains())
        own = PL.meter(router)
        with open(os.path.join(OUT, a.run, f"package_batch_{a.tag}.log"), "a") as logf:
            def say(s):
                print(f"[{a.run}:{a.tag}] {s}", flush=True)
                logf.write(s + "\n")
                logf.flush()
            say(f"=== {time.strftime('%H:%M:%S %Z')} SEAL {a.tag}: speakers, then the pin")
            try:
                seal(a.run, a.tag, router, say)
            except (package_pin.PinRefused, ValueError, OSError, KeyError, TypeError) as e:   # glm C1 P1-5
                say(f"PIN REFUSED: {type(e).__name__}: {e}")
                return 4
            finally:
                say(f"  speakers: ${own['est']:.4f} estimate, ${own['best']:.4f} best known")
        return 0
    try:                                                # read before anything is written (fail closed)
        delivered, _, pins = PLG.delivered_pins(a.delivered)
        delivered = delivered + package_spans(a.exclude)
        if not os.path.exists(os.path.join(PL.PM.OUT, a.run, "moments.json")):
            raise ValueError(f"{a.run}: no saved universe")
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"REFUSED: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    os.makedirs(a.work_dir, exist_ok=True)
    router = P.Router(env_path=PL.PM.PS.ENV, record_dir=PL.REPLIES, spend_path=SPEND, limit_usd=BATCH_LIMIT_USD,
                      chains=PL.chains())
    own, used = PL.meter(router), PL.reply_meter(router)
    with open(os.path.join(OUT, a.run, f"package_batch_{a.tag}.log"), "a") as logf:
        def say(s):
            print(f"[{a.run}:{a.tag}] {s}", flush=True)
            logf.write(s + "\n")
            logf.flush()
        say(f"=== {time.strftime('%H:%M:%S %Z')} BATCH medley build {a.tag}, code {PL.code_sha()}, delivered "
            f"{[p['story_id'] for p in pins]}, kept {a.exclude}, avoid {sorted(a.avoid_videos)}")
        try:
            build(a.run, a.tag, delivered, set(a.avoid_videos), router, own, used, say, a.work_dir)
        except P.SpendLimit as e:
            say(f"STOPPED: {e}")
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
