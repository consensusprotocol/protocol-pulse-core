#!/usr/bin/env python3
"""pipeline/replay.py — re-run the tail of an existing run on a COPY of its directory with the current code.

Orchestrator note 2026-11-11 08:30 ET (direction 4): "re-runs gates+verify on an existing run dir and
re-renders from prepared clips without re-downloading or re-transcribing, so each fix is checked in a minute
or two, not a full pipeline pass." The copy keeps sources/ (hard links: never written), transcripts/, the EDL,
the selection locks, the cut table and the VO; run_fresh.run_tail then runs the SAME functions main runs,
from the chosen stage. Nothing is delivered: a replay is diagnostic (deliver a run only from a full pass).
  CUDA_VISIBLE_DEVICES=0 python3 replay.py RUN_DIR [--from prepare|layout|render|gates] [--no-vision]
Exit: 0 = every gate passed, 3 = HOLD. The copy is RUN_DIR_replay_<UTC stamp>."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

DROP = ("TELEGRAM_DELIVERY*.json", "VERIFY", "*_replay_*")


def make_copy(run_dir, start, stamp=None):
    """The replay directory: a copy whose sources are hard links (read-only inputs); the outputs the
    replayed stages rebuild are removed so nothing stale can be measured."""
    import run_fresh as rf
    src = os.path.abspath(run_dir.rstrip("/"))
    dst = f"{src}_replay_{stamp or time.strftime('%Y%m%d_%H%M%S', time.gmtime())}"
    if os.path.exists(dst):
        raise SystemExit(f"STOP: {dst} exists")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*DROP, "sources"))
    os.makedirs(os.path.join(dst, "sources"))
    for name in os.listdir(os.path.join(src, "sources")):
        a, b = os.path.join(src, "sources", name), os.path.join(dst, "sources", name)
        if os.path.isfile(a):
            try:
                os.link(a, b)                           # read-only input
            except OSError:                             # e.g. another device: a copy is equally safe
                shutil.copy2(a, b)
        else:
            shutil.copytree(a, b)
    k = rf.TAIL_STAGES.index(start)
    stale = ["GATE_REPORT.json", "VERDICT.txt"]
    if k <= 2:
        stale += ["out/segment.mp4", "out/segment_vertical.mp4"]
    for p in stale:
        if os.path.exists(os.path.join(dst, p)):
            os.remove(os.path.join(dst, p))
    return dst


def replay(run_dir, start="prepare", vision=True, stamp=None):
    import run_fresh as rf
    dst = make_copy(run_dir, start, stamp)
    run = rf.Run(dst)
    with open(os.path.join(dst, "status.json")) as f:
        old = json.load(f)
    with open(os.path.join(dst, "PROVENANCE.json")) as f:
        run.prov = {**json.load(f), "run_dir": dst}
    run.mode = old.get("mode", "auto")
    pin = os.path.join(dst, "PINNED_DECISION.json")
    if run.mode == "pinned" and os.path.exists(pin):             # same rules (limiter, retries) as the original
        with open(pin) as f:
            run.machine_cuts = bool(json.load(f).get("pin", {}).get("machine_cuts", False))
    run.status.update(mode=run.mode, replay_of=os.path.abspath(run_dir), replay_from=start, vision=vision,
                      release_state=rf.RELEASE_STATE)
    head = subprocess.run(["git", "-C", PIPELINE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", PIPELINE, "status", "--porcelain", "--", "."], capture_output=True,
                           text=True).stdout.strip()
    run.prov["replay"] = {"of": os.path.abspath(run_dir), "from": start, "vision": vision, "head": head,
                          "pipeline_tree_dirty": bool(dirty)}
    with open(os.path.join(dst, "cuts_final.json")) as f:
        cuts = json.load(f)
    t0 = time.time()
    try:
        rf.run_tail(run, cuts, start=start, vision=vision)
    except rf.Hold:
        run.status["verdict"] = rf.VERDICT_HOLD
    except Exception as e:                              # as run_fresh.main: anything unexpected is a HOLD
        import traceback
        run.status["verdict"] = rf.VERDICT_HOLD
        run.status["holds"].append(f"replay: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        run.status["elapsed_s"] = round(time.time() - t0, 1)
        run.status["ended"] = rf.now_iso()
        run.save()
        rf.write_report(run)
        with open(os.path.join(dst, "VERDICT.txt"), "w") as f:
            f.write(str(run.status["verdict"]) + "\n")
    print(f"\n=== REPLAY {dst} (from {start}, vision {'on' if vision else 'OFF'}): {run.status['verdict']} ===")
    for h in run.status["holds"]:
        print(f"  HOLD: {h}")
    return dst, run.status["verdict"]


def main():
    import run_fresh as rf
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir")
    ap.add_argument("--from", dest="start", default="prepare", choices=rf.TAIL_STAGES)
    ap.add_argument("--no-vision", action="store_true", help="skip the Heimdall vision checklist (V1 not scored)")
    a = ap.parse_args()
    dst, verdict = replay(a.run_dir, a.start, vision=not a.no_vision)
    sys.exit(0 if verdict == rf.VERDICT_CANDIDATE else 3)


if __name__ == "__main__":
    main()
