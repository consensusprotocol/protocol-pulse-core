#!/usr/bin/env python3
"""Phase-2 proof driver, step 2 (PACKAGE) on saved universes: reads tests/moments/proof/<run>/moments.json, builds the
package through both gates (pipeline/package.py), records every reply (tests/package/fixtures/replies), spends into the
phase-2 ledger (tests/moments/proof/SPEND.json, $40 guard), writes tests/package/proof/<run>/package.json and prints the
package in full. CPU only; read-only inputs.

Usage: python3 tests/package/proof_packages.py --runs fresh_20261112_050611 [--replay]
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import proof_moments as PM  # noqa: E402
import providers as P  # noqa: E402

REPLIES = os.path.join(HERE, "fixtures", "replies")
OUT = os.path.join(HERE, "proof")


def show(pk):
    coh = (pk.get("checks") or {}).get("coherence") or {}
    gates = "; ".join(f"{k} {v['status']}" for k, v in (pk.get("gates") or {}).items())
    lines = [f"ANGLE: {pk['angle']}", f"VO {pk['vo_kind']} | runtime estimate {pk['runtime_s_estimate']} s "
             f"({pk['runtime_note']})",
             f"COHERENCE (blind, {coh.get('backend')}): through-line \"{coh.get('through_line')}\" | clips "
             f"{coh.get('clips')} | VO point {coh.get('vo_point')}",
             f"TITLE: {pk['title']}", f"CAPTION: {pk['caption']}", f"VO intro: {pk['vo']['intro']}"]
    after = dict(zip(pk["vo"].get("bridges_after_clip") or [], pk["vo"]["bridges"]))
    for i, s in enumerate(pk["segments"]):
        lines.append(f"  [{s['label']}] {s['channel']} {s['video_id']} {s['start']:.2f}-{s['end']:.2f} "
                     f"({s['duration_s']} s): \"{s['text']}\"")
        if after.get(i):
            lines.append(f"VO bridge: {after[i]}")
    lines.append(f"VO sign-off: {pk['vo']['signoff']}")
    lines.append(f"models: {pk.get('models')}")
    lines.append(f"gates: {gates}")
    return "\n".join(lines)


def run_one(run, router, log=print, work_dir=None, max_angles=PK.MAX_ANGLES, writes=PK.WRITES):
    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
    words, captions, ctx, saved = PM.universe_sources(run)
    sources = {s.video_id: s for s in words}
    t0 = time.time()
    spend = lambda: json.load(open(PM.SPEND))["usd_estimate"]
    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
                   max_angles=max_angles, writes=writes, work_dir=work_dir,
                   store=os.path.join(OUT, run, "step_a.json"), spend=spend)
    res["seconds"] = round(time.time() - t0, 1)
    res["run"] = run
    os.makedirs(os.path.join(OUT, run), exist_ok=True)
    json.dump(res, open(os.path.join(OUT, run, "package.json"), "w"), indent=1, default=str)
    if res["package"]:
        import package_pin
        for i, pk in enumerate(res["packages"]):
            name = "MOMENTS_PIN.json" if i == 0 else f"MOMENTS_PIN_alt{i}.json"    # never overwrites the top pin
            path, _ = package_pin.write_pin(pk, run, os.path.join(OUT, run), name=name)
            log(f"{run}: {'PACKAGE' if i == 0 else f'ALTERNATIVE {i}'} ({res['seconds']} s, ${res.get('usd')}) pin "
                f"{path}\n" + show(pk))
    else:
        log(f"{run}: no package ({res.get('why_none')}); usable moments {res['usable']}; tried "
            f"{json.dumps(res['tried'], default=str)[:1500]}")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--work-dir", required=True, help="law L-v 2's audio windows (required: no second pass, no package)")
    ap.add_argument("--max-angles", type=int, default=PK.MAX_ANGLES)
    ap.add_argument("--writes", type=int, default=PK.WRITES)
    a = ap.parse_args(argv)
    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, replay=a.replay, spend_path=PM.SPEND,
                      limit_usd=PM.LIMIT_USD)
    for run in a.runs:
        run_one(run, router, work_dir=a.work_dir, max_angles=a.max_angles, writes=a.writes)
    if router.notices:
        print("NOTICES:", router.notices)


if __name__ == "__main__":
    main()
