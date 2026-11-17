#!/usr/bin/env python3
"""Batch 100 (ruling 131) mutation run: each mutation applied to a scratch copy of the worktree's pipeline/, its tests
run with the network blocked (-p netguard), the file restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r136-switch"
M = os.path.join(S, "b105", "mut")
LOCK = ["pipeline/test_ruling17_lock.py", "pipeline/test_lock_precheck.py"]
PRE = ["pipeline/test_lock_precheck.py"]
TG = ["pipeline/test_telegram_delivery.py"]
G18 = ["pipeline/test_word_diff.py", "pipeline/test_canon.py"]

RA = ["pipeline/test_release_auth.py"]
TG = ["pipeline/test_telegram_delivery.py"]
SF = ["pipeline/test_stand_alone_floor.py", "pipeline/test_ruling91_takeaway.py"]
MUTS = [
    ("F1 soft rows block", "pipeline/release_auth.py", 'elif v != "PASS" and k not in soft:', 'elif v != "PASS":', RA),
    ("F2 never measured passes", "pipeline/release_auth.py", '            out[k] = f"{FLAG_TEXT.get(k, k)} (not measured)"', '            pass', RA),
    ("F3 flags not bound at authorise", "pipeline/release_auth.py", "    elif note != (att.get(\"review_flags\") or []):", "    elif False:", RA),
    ("F4 pin flags unbound", "pipeline/release_auth.py", "            if not (isinstance(sha, str) and sha and sha == edl.get(\"moments_package_sha256\")):\n                return None", "            pass", RA),
    ("F5 no flag line", "pipeline/telegram.py", "    if flagged:\n        head = \"REVIEW FLAGS: \"", "    if False:\n        head = \"REVIEW FLAGS: \"", TG),
    ("F6 soft rules hold", "pipeline/run_fresh.py", 'hard = [r for r in results if not r["pass"] and r["rule"] not in EDL_SOFT]', 'hard = [r for r in results if not r["pass"]]', SF),
    ("F7 unknown rules flag", "pipeline/run_fresh.py", 'hard = [r for r in results if not r["pass"] and r["rule"] not in EDL_SOFT]', 'hard = [r for r in results if not r["pass"] and r["rule"] in ("rule_r2", "rule_r5", "rule_r6", "rule_r7")]', SF),
    ("F8 editorial laws hold", "pipeline/run_fresh.py", '        flag(run, "editorial law(s) not affirmed: "', '        raise Hold("editorial law(s) not affirmed: "', SF),
    ("F9 topic soft", "pipeline/run_fresh.py", "    if not sa[\"ok\"] and not topic_bad and not medley_bad:", "    if not sa[\"ok\"]:", SF),
    ("F10 flags not in the verdict", "pipeline/release_auth.py", 'verdict = ("PASS_WITH_FLAGS" if note else "ALL_PASS") if ok else "HOLD"', 'verdict = "ALL_PASS" if ok else "HOLD"', RA + TG),
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
    shutil.copytree(os.path.join(W, "references", "pulse_fresh_2026-11-13"),                  # the floor tests' tracked
                    os.path.join(M, "references", "pulse_fresh_2026-11-13"))                  # reference run
    os.makedirs(os.path.join(M, "video_pipeline_v3"), exist_ok=True)     # signoff / vo import relay from here
    shutil.copy2(os.path.join(W, "video_pipeline_v3", "relay.py"), os.path.join(M, "video_pipeline_v3", "relay.py"))
    deselect = ["--deselect", "pipeline/test_word_diff.py::TestYesterdaysFinal"]   # GPU0 lease tests (error on CPU)
    code, tail = run(RA + TG + SF)
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
