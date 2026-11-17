#!/usr/bin/env python3
"""Batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r141-sign"
M = os.path.join(S, "b110", "mut")
RA = ["pipeline/test_release_auth.py"]
TG = ["pipeline/test_telegram_delivery.py"]
SF = ["pipeline/test_stand_alone_floor.py", "pipeline/test_ruling91_takeaway.py"]
ADV = ["tests/adversarial/test_f3_release_auth.py", "tests/adversarial/test_f4_vacuity.py"]
FB = ["pipeline/test_failure_blocks.py"]
CT = ["pipeline/test_canon.py", "pipeline/test_ruling17_lock.py"]
MUTS = [
    ("S1 no number-hyphen pass", "pipeline/canon.py",
     "    t = _NUM_HYPHEN.sub(r\"\\1\", t)", "    t = t", CT),
    ("S2 every spaced hyphen loses its sign", "pipeline/canon.py",
     '_NUM_HYPHEN = re.compile(r"(\\d\\s+)-(?=\\d)")', '_NUM_HYPHEN = re.compile(r"(\\s+)-(?=\\d)")', CT),
    ("S3 a number may be a word form", "pipeline/canon.py",
     '    if len(diff) != 1 or re.search(r"\\d", diff[0][0] + diff[0][1]):', "    if len(diff) != 1:", CT),
    ("S4 any two words are a word form", "pipeline/canon.py", "    return bool(a) and a == b", "    return bool(a)", CT),
    ("S5 no word-form exemption", "pipeline/pinned.py",
     "    crit = sorted({t for _, a, b, c, d in ops if not canon.word_form(r[a:b], p[c:d])",
     "    crit = sorted({t for _, a, b, c, d in ops if True", CT),
    ("S6 every pair exempt", "pipeline/pinned.py",
     "    crit = sorted({t for _, a, b, c, d in ops if not canon.word_form(r[a:b], p[c:d])",
     "    crit = sorted({t for _, a, b, c, d in ops if False", CT),
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
    code, tail = run(CT)
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
