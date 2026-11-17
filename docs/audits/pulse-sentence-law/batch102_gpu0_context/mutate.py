#!/usr/bin/env python3
"""Batch 100 (ruling 131) mutation run: each mutation applied to a scratch copy of the worktree's pipeline/, its tests
run with the network blocked (-p netguard), the file restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r102-gpu0"
M = os.path.join(S, "b102", "mut")
LOCK = ["pipeline/test_ruling17_lock.py", "pipeline/test_lock_precheck.py"]
PRE = ["pipeline/test_lock_precheck.py"]
TG = ["pipeline/test_telegram_delivery.py"]
G18 = ["pipeline/test_word_diff.py", "pipeline/test_canon.py"]

TI = ["pipeline/test_transcript_ingest.py"]
SC = ["pipeline/test_stand_alone_scorer.py"]
MUTS = [
    ("C1 the pass waits and goes on (batch 97)", "pipeline/transcript_ingest.py", "outlive its turn: L-r)\")\n                break", "outlive its turn: L-r)\")\n                pass", TI),
    ("C2 one status for both causes", "pipeline/transcript_ingest.py", 'why = "deferred_render_wants_gpu0" if LJ.render_wants_gpu0() else "deferred_gpu0_yielded"', 'why = "deferred_gpu0_yielded"', TI),
    ("C3 the scorer dies on a Gpu0Stop", "pipeline/stand_alone_scorer.py", "    except gpu0.Gpu0Stop as e:", "    except gpu0.Gpu0Unreadable as e:", SC),
]

def run(tests):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH=S)
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "netguard", "-q", "-p", "no:cacheprovider", "-x",
                        *tests], cwd=M, env=env, capture_output=True, text=True, timeout=900)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return r.returncode, tail


def main():
    if os.path.exists(M):
        shutil.rmtree(M)
    os.makedirs(M)
    for d in ("pipeline", "segment_v1", "scripts", "config", "tests/fixtures"):
        if os.path.isdir(os.path.join(W, d)):
            shutil.copytree(os.path.join(W, d), os.path.join(M, d), ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(M, "video_pipeline_v3"), exist_ok=True)     # signoff / vo import relay from here
    shutil.copy2(os.path.join(W, "video_pipeline_v3", "relay.py"), os.path.join(M, "video_pipeline_v3", "relay.py"))
    deselect = ["--deselect", "pipeline/test_word_diff.py::TestYesterdaysFinal"]   # GPU0 lease tests (error on CPU)
    code, tail = run(TI + SC)
    print(f"CONTROL (unmutated): exit {code} | {tail}")
    if code != 0:
        sys.exit("control failed: no mutation result would mean anything")
    killed = 0
    for name, rel, old, new, tests in MUTS:
        path = os.path.join(M, rel)
        src = open(path).read()
        if src.count(old) != 1:
            print(f"{name}: NOT APPLIED (pattern found {src.count(old)} times)")
            continue
        open(path, "w").write(src.replace(old, new))
        try:
            code, tail = run(tests + (deselect if "pipeline/test_word_diff.py" in tests else []))
        finally:
            open(path, "w").write(src)
        verdict = "KILLED" if code != 0 else "SURVIVED"
        killed += code != 0
        print(f"{name}: {verdict} | {tail}")
    print(f"{killed} of {len(MUTS)} killed")


main()
