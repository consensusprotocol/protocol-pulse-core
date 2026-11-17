#!/usr/bin/env python3
"""Batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r142-postlive"
M = os.path.join(S, "b111", "mut")
RA = ["pipeline/test_release_auth.py"]
TG = ["pipeline/test_telegram_delivery.py"]
SF = ["pipeline/test_stand_alone_floor.py", "pipeline/test_ruling91_takeaway.py"]
ADV = ["tests/adversarial/test_f3_release_auth.py", "tests/adversarial/test_f4_vacuity.py"]
FB = ["pipeline/test_failure_blocks.py"]
PL = ["pipeline/test_post_live.py"]
MUTS = [
    ("L1 no whole-stream fallback", "pipeline/select_passages.py",
     "        if _post_live_window(video_id, dl_start, dl_end, out_path, cookies if os.path.exists(cookies) else None):",
     "        if False:", PL),
    ("L2 picture without audio counts as media", "pipeline/select_passages.py",
     "    return fmt >= POST_LIVE_MIN_S and bool(aud) and max(aud) >= POST_LIVE_MIN_S", "    return fmt >= POST_LIVE_MIN_S", PL),
    ("L3 any shift passes", "pipeline/pinned.py", "    if abs(med) > POST_LIVE_MAX_OFFSET_S:", "    if False:", PL),
    ("L4 a handful of words suffices", "pipeline/pinned.py", "    if len(deltas) < POST_LIVE_MIN_ALIGNED:",
     "    if not deltas:", PL),
    ("L5 acquire skips the guard", "pipeline/pinned.py",
     '            if os.path.exists(path + ".post_live.json"):          # ruling 142 (3): cut from the whole stream',
     "            if False:", PL),
    ("L6 the cut starts at 0", "pipeline/select_passages.py",
     '    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{dl_start:.3f}", "-i", got["video"], "-ss", f"{dl_start:.3f}",',
     '    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", "0.000", "-i", got["video"], "-ss", f"{dl_start:.3f}",', PL),
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
    code, tail = run(PL)
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
