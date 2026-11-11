#!/usr/bin/env python3
"""pipeline/transition_options.py — the labelled transition options on one finished cut (Phase 3, DEC-4).

The production run renders the DEC-4 default (6-frame cross-dissolve + matching audio crossfade). For PBX's
choice, the SAME cut (same cuts, same prepared clips, same layout plan) is rendered again per option in a
copy of the run dir, and every option is gated and packed like a production render:
  A  clean cut; 6-frame audio dip-crossfade across the cut
  B  6-frame cross-dissolve + matching audio crossfade + a soft synthesized pulse thump
  C  brand ECG line sweep, 8 frames on black, double thump (no logo, no text, nothing at the open)
Usage: CUDA_VISIBLE_DEVICES=0 python3 transition_options.py RUN_DIR [A B C]
Delivery is separate: telegram.deliver_run(<copy>, option="A") (labelled, never a release candidate).
"""
import json
import os
import shutil
import sys

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)


def render_option(run_dir, style):
    import run_fresh as rf
    import verify_pack
    dst = f"{run_dir.rstrip('/')}_option{style}"
    if os.path.exists(dst):
        raise SystemExit(f"STOP: {dst} exists")
    shutil.copytree(run_dir, dst, ignore=shutil.ignore_patterns("TELEGRAM_DELIVERY*.json", "VERIFY"))
    for p in ("out/segment.mp4", "out/segment_vertical.mp4", "GATE_REPORT.json"):
        if os.path.exists(os.path.join(dst, p)):
            os.remove(os.path.join(dst, p))
    run = rf.Run(dst)
    with open(os.path.join(dst, "status.json")) as f:
        run.mode = json.load(f).get("mode", "auto")
    pin = os.path.join(dst, "PINNED_DECISION.json")
    if run.mode == "pinned" and os.path.exists(pin):        # same limiter as the original render
        with open(pin) as f:
            run.machine_cuts = bool(json.load(f).get("pin", {}).get("machine_cuts", False))
    with open(os.path.join(dst, "cuts_final.json")) as f:
        cuts = json.load(f)
    rf.TRANSITION_STYLE = style                     # the option, on the same cut
    final16, man16, final9, man9 = rf.stage_render(run)
    rows, flags, limits = rf.stage_gates(run, final16, man16, final9, man9)
    verify_pack.build(dst)
    run.save()
    print(f"option {style}: {dst} | " + ", ".join(f"{fmt}: {rf.verdict_for(rows[fmt])[0]}" for fmt in rows))
    return dst, cuts


if __name__ == "__main__":
    rd = os.path.abspath(sys.argv[1])
    for st in (sys.argv[2:] or ["A", "B", "C"]):
        render_option(rd, st)
