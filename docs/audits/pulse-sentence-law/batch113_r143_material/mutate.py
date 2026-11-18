#!/usr/bin/env python3
"""Batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r143-material"
M = os.path.join(S, "b113", "mut")
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
MUTS = [
    ("T1 a material word never holds", "pipeline/pinned.py",
     "            took = \"run\" if run_ok else None           # transcript was wrong); they disagree -> HOLD",
     "            took = \"run\"", LK),
    ("T2 a small word holds when all differ", "pipeline/pinned.py",
     "            took = \"approved\" if pin_ok else \"run\"     # the render cuts)",
     "            took = \"approved\" if pin_ok else \"run\" if run_ok else None", LK),
    ("T3 no wrong-audio gate", "pipeline/pinned.py",
     "    if wrong_audio(r, s) is not None:                  # ruling 143 (4): the wrong audio, not small words: HARD",
     "    if False:", LK),
    ("T4 the second reader's extra words count", "pipeline/pinned.py",
     "    return sum(m.size for m in SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks()) / len(x)",
     "    return sum(m.size for m in SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks()) / max(len(x), len(y))", LK),
    ("T5 a ticker is not material", "pipeline/pinned.py",
     "                if (before and before[-1] not in \".!?\") or (len(w) >= 2 and w.isupper()):",
     "                if (before and before[-1] not in \".!?\"):", LK),
    ("T6 ruling 72 holds on small words", "pipeline/lock_precheck.py",
     "    return (\"hold\" if \"material\" in cls else \"same\"), diffs, cls, spoken",
     "    return (\"hold\" if cls else \"same\"), diffs, cls, spoken", LK),
    ("T7 G18 decides no small word by the audio", "pipeline/word_diff.py",
     "        if row[\"identity\"] and (omitted or small_only) and c.get(\"prepared\"):",
     "        if row[\"identity\"] and omitted and c.get(\"prepared\"):", G18),
    ("T8 the note says no correction", "pipeline/telegram.py", "        + corrected", "        + []", TGN),
    ("T9 the flag waits for 5", "pipeline/run_fresh.py",
     "        if isinstance(n, int) and not isinstance(n, bool) and n > 3:",
     "        if isinstance(n, int) and not isinstance(n, bool) and n > 4:", FLG),
    ("T10 fillers stay in the second reading", "pipeline/pinned.py",
     "    s = [x for x in canon.canon_tokens(sec_t) if not canon.nonlexical(x)]      # ruling 135 (d): fillers are not words",
     "    s = canon.canon_tokens(sec_t)", LK),
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
    code, tail = run(LK + G18 + TGN + FLG)
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
