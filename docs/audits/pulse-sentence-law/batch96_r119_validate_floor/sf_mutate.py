#!/usr/bin/env python3
"""Batch 96 mutations: each must make the three suites fail; the unmutated control must pass first.
Usage: python3 sf_mutate.py WORKTREE NETGUARD_DIR"""
import os
import subprocess
import sys

W, NG = sys.argv[1], sys.argv[2]
F = "pipeline/stand_alone_floor.py"
TESTS = ["pipeline/test_stand_alone_floor.py", "pipeline/test_telegram_delivery.py", "pipeline/test_stand_alone_scorer.py"]
MUT = [
    ("M1 the floor dropped (any score under the bar)", F,
     "not FLOOR <= score < SA.CLIP_MIN_SCORE", "not score < SA.CLIP_MIN_SCORE"),
    ("M2 the scorer-code check dropped", F,
     "if code != MEASURED_SCORER_SHA or weights != MEASURED_DIGEST:", "if weights != MEASURED_DIGEST:"),
    ("M3 the weights check dropped", F,
     "if code != MEASURED_SCORER_SHA or weights != MEASURED_DIGEST:", "if code != MEASURED_SCORER_SHA:"),
    ("M4 the seal check dropped", F,
     'if not (isinstance(sha, str) and sha and sha == edl.get("moments_package_sha256")):', "if False:"),
    ("M5 the marked segments ignored", F,
     'if r["segment"] not in rec["segments"] or r["opener"]["pass"] or not isinstance(v, dict):',
     'if r["opener"]["pass"] or not isinstance(v, dict):'),
    ("M6 the opener asked again at the bar skipped", F,
     "        if not ok:                                               # it fails for another reason than its score",
     "        if False:"),
    ("M7 the topic test ignored", F, 'r["pass"] = r["topic"]["pass"]', 'r["pass"] = True'),
    ("M8 the medley rule ignored", F,
     'sa["ok"] = all(r["pass"] for r in sa["rows"]) and sa.get("medley_names_bitcoin", {"pass": True})["pass"]',
     'sa["ok"] = all(r["pass"] for r in sa["rows"])'),
    ("M9 the mark's floor not checked", F, "floor != FLOOR or ", ""),
    ("M10 the mark's scorer code not checked", F, ' or m["scorer_sha"] != MEASURED_SCORER_SHA:', ":"),
    ("M11 the mark's places not bounded", F, "0 <= p < n_segments", "0 <= p"),
    ("M12 the mark's exact fields not checked", F,
     "if not isinstance(m, dict) or sorted(m) != sorted(FIELDS):", "if not isinstance(m, dict):"),
    ("M13 validate does not apply the floor", "pipeline/run_fresh.py",
     "        sa = stand_alone_floor.apply(sa, edl, run.dir)", "        pass"),
    ("M14 a malformed mark at validate is not a HOLD", "pipeline/run_fresh.py",
     '        raise Hold(f"stand-alone calibrated floor (ruling 119 (1)): {e}")', "        pass"),
    ("M15 check_pin_only does not check the mark", "scripts/integrator/check_pin_only.py",
     '        stand_alone_floor.mark(mp, len(pin.get("segments") or []))', "        pass"),
    ("M16 the drop has no line for the mark", "pipeline/telegram.py",
     ',\n             ("stand_alone_bar", STAND_ALONE_BAR_NOTE, "ruling 119"))', ")"),
    ("M17 a verdict's digest not its own entry's", "pipeline/stand_alone_scorer.py",
     '"digest": e.get("digest"), ', '"digest": "dg", '),
    ("M18 the block names a digest for mixed weights", "pipeline/stand_alone_scorer.py",
     "weights.pop() if len(weights) == 1 else None", "next(iter(weights), None)"),
]


def run():
    env = dict(os.environ, PYTHONPATH=NG, CUDA_VISIBLE_DEVICES="")
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "netguard", "-q", "-p", "no:cacheprovider", "-x",
                        *TESTS], cwd=W, env=env, capture_output=True, text=True, timeout=900)
    tail = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l or "error" in l.lower()]
    return r.returncode, (tail[-1] if tail else r.stdout[-200:]).strip()


code, tail = run()
print(f"CONTROL (unmutated): exit {code} | {tail}", flush=True)
if code != 0:
    sys.exit("control failed: no mutation run")
killed = 0
for name, rel, old, new in MUT:
    p = os.path.join(W, rel)
    with open(p) as f:
        orig = f.read()
    n = orig.count(old)
    if n != 1:
        print(f"{name}: NOT APPLIED (the text occurs {n} times)", flush=True)
        continue
    try:
        with open(p, "w") as f:
            f.write(orig.replace(old, new))
        code, tail = run()
    finally:
        with open(p, "w") as f:
            f.write(orig)
    ok = code != 0
    killed += ok
    print(f"{name}: {'KILLED' if ok else 'SURVIVED'} | {tail}", flush=True)
print(f"{killed} of {len(MUT)} killed", flush=True)
code, tail = run()
print(f"AFTER (restored): exit {code} | {tail}", flush=True)
