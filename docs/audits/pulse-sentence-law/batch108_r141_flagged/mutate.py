#!/usr/bin/env python3
"""Batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r141-flagged"
M = os.path.join(S, "b108", "mut")
RA = ["pipeline/test_release_auth.py"]
TG = ["pipeline/test_telegram_delivery.py"]
SF = ["pipeline/test_stand_alone_floor.py", "pipeline/test_ruling91_takeaway.py"]
ADV = ["tests/adversarial/test_f3_release_auth.py", "tests/adversarial/test_f4_vacuity.py"]
FB = ["pipeline/test_failure_blocks.py"]
EG = ["pipeline/test_edl_rules.py", "pipeline/test_editorial_gate.py"]
MUTS = [
    ("Q1 FLAGGED needs no flags", "pipeline/edl_rules.py",
     '    return row.get("status") == "FLAGGED" and isinstance(f, list) and bool(f) \\',
     '    return row.get("status") == "FLAGGED" or isinstance(f, list) and bool(f) \\', EG),
    ("Q2 replayed ignored", "pipeline/edl_rules.py",
     '    if not isinstance(row, dict) or row.get("replayed") is not False:', '    if not isinstance(row, dict):', EG),
    ("Q3 the hook's own join ignored", "pipeline/edl_rules.py", '    if QUESTION_HOOK_JOIN in med["flagged"]:',
     '    if False:', EG),
    ("Q4 the takeaway wants PASS only", "pipeline/edl_rules.py",
     '    if not sealed_ok(row):                          # ruling 141: a FLAGGED verdict with its flags counts (the pin says it)',
     '    if not (isinstance(row, dict) and row.get("status") == "PASS" and row.get("replayed") is False):', EG),
    ("Q5 the editorial gate wants PASS only", "pipeline/editorial_gate.py",
     '    return [r for r in rows if not (isinstance(g, dict) and sealed_ok(g.get(r)))]',
     '    return [r for r in rows if not (isinstance(g, dict) and isinstance(g.get(r), dict) and g[r].get("status") == "PASS" and g[r].get("replayed") is False)]', EG),
    ("Q6 R1 wants a PASS medley only", "pipeline/edl_rules.py",
     '    if not sealed_ok(med) or not isinstance(med.get("flagged"), list):       # ruling 141: FLAGGED with its flags',
     '    if not (isinstance(med, dict) and med.get("status") == "PASS" and med.get("replayed") is False) or not isinstance(med.get("flagged"), list):', EG),
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
    for d in ("pipeline", "segment_v1", "scripts", "config", "tests/fixtures", "tests/adversarial"):
        if os.path.isdir(os.path.join(W, d)):
            shutil.copytree(os.path.join(W, d), os.path.join(M, d), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(W, "references"), os.path.join(M, "references"),       # the protected references
                    ignore=shutil.ignore_patterns("*.mp4", "*.wav", "*.mov"))       # (their EDLs; not the media)
    os.makedirs(os.path.join(M, "video_pipeline_v3"), exist_ok=True)
    shutil.copy2(os.path.join(W, "video_pipeline_v3", "relay.py"), os.path.join(M, "video_pipeline_v3", "relay.py"))
    code, tail = run(EG)
    print(f"CONTROL (unmutated): exit {code} | {tail}", flush=True)
    if code != 0:
        sys.exit("control failed: no mutation result would mean anything")
    killed = 0
    for name, rel, old, new, tests in MUTS:
        path = os.path.join(M, rel)
        src = open(path).read()
        if src.count(old) != 1:
            print(f"{name}: NOT APPLIED (found {src.count(old)} times)", flush=True)
            continue
        open(path, "w").write(src.replace(old, new))
        try:
            code, tail = run(tests)
        finally:
            open(path, "w").write(src)
        ok = code != 0
        killed += ok
        print(f"{name}: {'KILLED' if ok else 'SURVIVED'} | {tail}", flush=True)
    print(f"{killed} of {len(MUTS)} killed")


if __name__ == "__main__":
    main()
