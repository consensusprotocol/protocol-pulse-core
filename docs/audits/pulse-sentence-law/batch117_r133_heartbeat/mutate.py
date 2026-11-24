#!/usr/bin/env python3
"""Batch 117 (ruling 133 R16) mutation run: each mutation applied to a scratch copy of the worktree, the heartbeat
tests run, the file restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

W = "/home/ultron/worktrees/r133-heartbeat"
M = sys.argv[1]                                     # a scratch directory for the copy
T = ["pipeline/test_heartbeat.py"]
MUTS = [
    ("M1 the pre-check marks no pass", "pipeline/lock_precheck.py",
     '        heartbeat.mark_pass("lock_precheck", served=n)       # ruling 133 R16 (the service is a once-loop)\n', ''),
    ("M2 the scorer starts no thread", "pipeline/stand_alone_scorer.py",
     '        heartbeat.start("scorer")                              # ruling 133 R16\n', '        pass\n'),
    ("M3 the word pass marks no cycle", "pipeline/word_pass_worker.py",
     '            heartbeat.mark_pass("word_pass", picked=rep.get("picked"), blocked=rep.get("blocked"))\n',
     '            pass\n'),
    ("M4 the judge launcher installs no wrapper", "pipeline/judge_serve.py",
     '    local_judge.serve_once = serve_once                     # main() looks serve_once up at call time\n', ''),
    ("M5 run_pass drops the heartbeat findings", "tools/session_watchdog.py",
     '        f, status["heartbeats"] = heartbeat_findings(state, now, paths)\n        findings += f\n',
     '        f, status["heartbeats"] = heartbeat_findings(state, now, paths)\n'),
    ("M6 HEARTBEAT is not a watchdog kind", "pipeline/telegram.py",
     '"SPEND", "HEARTBEAT")   # R16: 133', '"SPEND")'),
    ("M7 stale after 30 min", "pipeline/heartbeat.py",
     'STALE_S = 20 * 60', 'STALE_S = 30 * 60'),
    ("M8 a missing heartbeat has no grace", "tools/session_watchdog.py",
     '            if now - since > heartbeat.STALE_S:\n', '            if True:\n'),
    ("M9 a stuck pass is never found", "tools/session_watchdog.py",
     '        elif pass_at is not None and now - pass_at > heartbeat.PASS_STALE_S:\n', '        elif False:\n'),
    ("M10 a failed write raises", "pipeline/heartbeat.py",
     '    except OSError as e:\n        if service not in _warned:', '    except ValueError as e:\n        if service not in _warned:'),
    ("M11 the thread never refreshes", "pipeline/heartbeat.py",
     '        while not stop.wait(beat_s):\n            _write(service)\n', '        while not stop.wait(beat_s):\n            pass\n'),
    ("M12 the transcript run's age is ignored", "tools/session_watchdog.py",
     '    if last is None or now - last > TRANSCRIPT_STALE_S:\n', '    if last is None:\n'),
    ("M14 a NaN or out-of-range time ends the check (cycle 2 F1)", "tools/session_watchdog.py",
     '            if not all(0 < t < 1e11 for t in (at, pass_at) if t is not None):     # NaN, inf, out of range (cycle 2)\n',
     '            if False:\n'),
    ("M15 pass_at parsed outside the guarded read (cycle 1 F1)", "tools/session_watchdog.py",
     '            pass_at = None if rec.get("pass_at") is None else float(rec["pass_at"])\n',
     '            pass_at = rec.get("pass_at")\n'),
    ("M13 the scorer beats in once mode too", "pipeline/stand_alone_scorer.py",
     '        if a.cmd == "serve":\n            heartbeat.mark_pass("scorer", served=n)\n',
     '        heartbeat.mark_pass("scorer", served=n)\n'),
]


def run(tests):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=M, env=env,
                       capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


shutil.rmtree(M, ignore_errors=True)
shutil.copytree(W, M, ignore=shutil.ignore_patterns(".git", "runs", "__pycache__"))
rc, tail = run(T)
print(f"CONTROL (unmutated): exit {rc} | {tail}")
assert rc == 0, "the control must pass"
killed = 0
for name, fn, old, new in MUTS:
    p = os.path.join(M, fn)
    src = open(p).read()
    assert src.count(old) == 1, (name, src.count(old))
    open(p, "w").write(src.replace(old, new))
    try:
        rc, tail = run(T)
    finally:
        open(p, "w").write(src)
    killed += rc != 0
    print(f"{name}: {'KILLED' if rc else 'SURVIVED'} (exit {rc}) | {tail}")
print(f"mutations killed: {killed} of {len(MUTS)}")
