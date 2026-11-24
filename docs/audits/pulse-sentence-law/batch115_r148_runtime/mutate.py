#!/usr/bin/env python3
"""Batch 115 (ruling 148 (1)); adapted from batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r148-runtime"
M = os.path.join(S, "b148", "mut")
RA = ["pipeline/test_release_auth.py"]
TG = ["pipeline/test_telegram_delivery.py"]
SF = ["pipeline/test_stand_alone_floor.py", "pipeline/test_ruling91_takeaway.py"]
ADV = ["tests/adversarial/test_f3_release_auth.py", "tests/adversarial/test_f4_vacuity.py"]
FB = ["pipeline/test_failure_blocks.py"]
CT = ["pipeline/test_canon.py", "pipeline/test_ruling17_lock.py"]
LK = ["pipeline/test_ruling17_lock.py", "pipeline/test_lock_precheck.py"]
G18 = ["pipeline/test_word_diff.py"]
TGN = ["pipeline/test_telegram_delivery.py"]
FLG = ["pipeline/test_stand_alone_floor.py"]
R = ["pipeline/test_ruling148_runtime.py"]
RV = ["pipeline/test_ruling148_runtime.py", "pipeline/test_stand_alone_floor.py"]
MUTS = [
    ("M1 a PASS runtime row relaxes G5", "pipeline/edl_rules.py",
     '    return row if sealed_ok(row) and row.get("status") == "FLAGGED" else None',
     '    return row if sealed_ok(row) else None', R),
    ("M2 a replayed row counts", "pipeline/edl_rules.py",
     '    return row if sealed_ok(row) and row.get("status") == "FLAGGED" else None',
     '    return row if isinstance(row, dict) and row.get("status") == "FLAGGED" and row.get("flags") else None', R),
    ("M3 the floor forgets the format's tail", "segment_v1/qa_gates.py",
     '            return ((edl_rules.RUNTIME_FLAG_FLOOR_S + edl_rules.FINAL_TAIL_S, G5_RUNTIME_FLAGGED_MAX_S),',
     '            return ((edl_rules.RUNTIME_FLAG_FLOOR_S, G5_RUNTIME_FLAGGED_MAX_S),', R),
    ("M4 any EDL takes the exception", "segment_v1/qa_gates.py",
     '    if isinstance(edl, dict) and edl.get("package_type") == "moments":      # ruling 148 (1): a sealed, FLAGGED runtime',
     '    if isinstance(edl, dict):', R),
    ("M5 the ceiling drops to 70 s", "segment_v1/qa_gates.py",
     'G5_RUNTIME_FLAGGED_MAX_S = 72.0',
     'G5_RUNTIME_FLAGGED_MAX_S = 70.0', R),
    ("M6 R4 always says the voiceover", "pipeline/run_fresh.py",
     '    out = [EDL_SOFT["rule_r4"]] if rest or not runtime else []',
     '    out = [EDL_SOFT["rule_r4"]]', R),
    ("M7 R4 ignores the sealed row", "pipeline/run_fresh.py",
     '    if runtime and edl_rules.flagged_runtime_row(run_dir) is None:',
     '    if runtime:', R),
    ("M8 validate does not route R4", "pipeline/run_fresh.py",
     '            for s in (r4_sentences(run.dir, r.get("reason", "")) if r["rule"] == "rule_r4"\n                      else [sentence(EDL_SOFT[r["rule"]], edl, r.get("reason", ""))]):',
     '            for s in [sentence(EDL_SOFT[r["rule"]], edl, r.get("reason", ""))]:', R),
    ("M9 validate flags no soft rule", "pipeline/run_fresh.py",
     '    flag_soft_rules(run, edl, results)\n',
     '    pass\n', RV),
]


def run(tests):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH=S)
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "netguard", "-q", "-p", "no:cacheprovider", "-x",
                        "--deselect", "pipeline/test_word_diff.py::TestYesterdaysFinal", *tests], cwd=M, env=env, capture_output=True, text=True, timeout=900)
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
    code, tail = run(RV)
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
