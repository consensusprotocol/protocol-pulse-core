#!/usr/bin/env python3
"""Batch 97 mutations: each must make the suites fail; the unmutated control must pass first.
Usage: python3 gt_mutate.py WORKTREE NETGUARD_DIR"""
import os
import subprocess
import sys

W, NG = sys.argv[1], sys.argv[2]
TI, SS, LP, GW = ("pipeline/transcript_ingest.py", "pipeline/stand_alone_scorer.py", "pipeline/lock_precheck.py",
                  "pipeline/gpu0_want.py")
TESTS = ["pipeline/test_gpu0_want.py", "pipeline/test_transcript_ingest.py", "pipeline/test_stand_alone_scorer.py",
         "pipeline/test_lock_precheck.py"]
MUT = [
    ("T1 the ingest never waits (defers at the first busy)", TI, "        if waited >= LEASE_WAIT_S:", "        if True:"),
    ("T2 a build's want ignored while waiting", TI, "        builds = gpu0_want.wanted()", "        builds = []"),
    ("T3 no yield to a build at the file boundary", TI,
     "            if hold is not None and (LJ.render_wants_gpu0() or gpu0_want.wanted()):",
     "            if hold is not None and LJ.render_wants_gpu0():"),
    ("T4 a render ignored while waiting", TI,
     '        if LJ.render_wants_gpu0():\n            return "deferred_render_wants_gpu0", waited',
     '        if False:\n            return "deferred_render_wants_gpu0", waited'),
    ("T5 Whisper not given back at the boundary", TI,
     "                hold.close()                             # this file boundary: Whisper unloaded, then the lease goes",
     "                pass"),
    ("T6 Whisper's unload not registered with the lease", TI,
     "                hold.callback(ts.release_whisper)        # LIFO: runs first on leaving, while the lease is still held",
     "                pass"),
    ("T7 a lease attempt that blocks", TI, "hold.enter_context(gpu0.lease(OWNER, wait_s=0))",
     "hold.enter_context(gpu0.lease(OWNER, wait_s=30))"),
    ("S1 the scorer raises no want while work waits", SS, "    gpu0_want.want(WANT)\n    if LJ.render_wants_gpu0():",
     "    if LJ.render_wants_gpu0():"),
    ("S2 the scorer not done when a batch empties its queue", SS,
     "    if not pending():\n        gpu0_want.done(WANT)", "    if False:\n        gpu0_want.done(WANT)"),
    ("S3 the scorer not done on an empty queue", SS, "    if not todo:\n        gpu0_want.done(WANT)\n        return 0",
     "    if not todo:\n        return 0"),
    ("P1 the pre-check raises no want while a decode waits", LP,
     "        gpu0_want.want(WANT)                     # a decode waits for GPU0", "        pass"),
    ("P2 the pre-check not done after its decodes", LP,
     "    if not ready or len(decoded) == len(ready):\n        gpu0_want.done(WANT)",
     "    if False:\n        gpu0_want.done(WANT)"),
    ("P3 the pre-check not done on an empty queue", LP, "    if not todo:\n        gpu0_want.done(WANT)\n        return 0",
     "    if not todo:\n        return 0"),
    ("G1 a stale want still counts", GW, "            if now - os.path.getmtime(os.path.join(DIR, name)) <= FRESH_S:",
     "            if True:"),
    ("G2 done() leaves the want", GW, "        os.remove(_path(service))", "        _path(service)"),
    ("G3 any name accepted", GW, '    if not NAME.match(service or ""):', "    if False:"),
    ("G4 strays counted as wants", GW, '        if not name.endswith(".json") or not NAME.match(name[:-5]):',
     '        if not name.endswith(".json"):'),
]


def run():
    env = dict(os.environ, PYTHONPATH=NG, CUDA_VISIBLE_DEVICES="")
    try:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "netguard", "-q", "-p", "no:cacheprovider",
                            "-x", *TESTS], cwd=W, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 124, "timed out (300 s)"
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
