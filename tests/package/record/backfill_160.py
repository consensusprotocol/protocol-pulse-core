#!/usr/bin/env python3
"""RULING 160 (2b) (orchestrator 07:33 ET Nov 24): "Backfill last night's builds 152 to 168 from their records."
Each build's number and record folder come from its own commit ("pp-selectid build N (ledger_...)"); its line is
outcomes.outcome_of() on the committed record, marked backfilled. ONE record holds no reason of its own: build 156 was
stopped by the builder at its start (exit 143, before step A, no paid call); its reason is the builder's STATE line of
20:29 ET Nov 23, quoted below, and it is given here (OVERRIDE), never invented. Writes with outcomes.write_once (a run
already in the file is never written twice). Usage: python3 tests/package/record/backfill_160.py [--dry-run]"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "tests", "package"))
import outcomes as OC  # noqa: E402

BUILDS = range(152, 169)
OVERRIDE = {156: {"outcome": "NO_ELIGIBLE_STORY", "stage": "start", "clip": "f47662e48ecb4dc31582",
                  "gate": "a clip of the set (Scott Melker f47662e4) passed 12 h before a sealed pin could reach the "
                          "render (ruling 76): stopped by the builder at its start",
                  "note": "the record holds no package.json (terminated, exit 143, before step A: no paid call); "
                          "STATE 20:29 ET Nov 23: 'BUILD 156 STOPPED BY ME AT ITS START (no paid call made: it was "
                          "before step A): its set held Scott Melker f47662e4, which passes 12 h at about 21:00 ET, "
                          "before a sealed pin could reach the render.' Build 157 retried without it."}}


def runs():
    """{build number: record folder} from the build commits' subjects."""
    log = subprocess.run(["git", "-C", REPO, "log", "--format=%s", "--grep=^pp-selectid build 1[56][0-9] "],
                         capture_output=True, text=True, check=True).stdout
    out = {}
    for s in log.splitlines():
        m = re.match(r"pp-selectid build (\d+) \((ledger_\d{8}_\d{6})", s)
        if m and int(m.group(1)) in BUILDS:
            out.setdefault(int(m.group(1)), m.group(2))
    return out


def main(argv):
    rs = runs()
    missing = [n for n in BUILDS if n not in rs]
    if missing:
        sys.exit(f"no build commit names a record for {missing}")
    proof = os.path.join(REPO, "tests", "package", "proof")
    titles = {}
    for n in BUILDS:
        t, sid = OC.story_of(os.path.join(proof, rs[n]))
        if t and sid:
            titles.setdefault(sid, t)
    for n in BUILDS:
        line = OC.outcome_of(os.path.join(proof, rs[n]), build_no=n, backfilled=True, titles=titles)
        line.update(OVERRIDE.get(n, {}))
        wrote = "dry" if "--dry-run" in argv else OC.write_once(line)
        print(f"{n} {line['run']} {line['outcome']} at {line['stage']}: {line['gate'][:110]}"
              + (f" (clip {line['clip']})" if line.get("clip") else "") + f" [{wrote}]")


if __name__ == "__main__":
    main(sys.argv[1:])
