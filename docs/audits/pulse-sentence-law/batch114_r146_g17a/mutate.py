#!/usr/bin/env python3
"""Batch 114 (ruling 146 (2)); adapted from batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r146-g17a"
M = os.path.join(S, "b146", "mut")
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
R146 = ["pipeline/test_ruling146_g17a.py"]
SNAP = ["pipeline/test_shot_snap.py"]
LP = ["pipeline/test_lock_precheck.py"]
MUTS = [
    ("M1 the soft hook keeps 'refused'", "pipeline/sentence_law.py",
     '            hook = {**{k: v for k, v in hook.items() if k != "refused"}, "short": hook["refused"],',
     '            hook = {**hook, "short": hook["refused"],', R146),
    ("M2 the soft hook takes a tried cut", "pipeline/sentence_law.py",
     '                    "cut_in": pick["cut_in"], "fade_in_ms": pick["fade_in_ms"], "pad_s": plan["in"]["lead_in_pad_s"],',
     '                    "cut_in": hook["tried"][0]["cut_in"], "fade_in_ms": pick["fade_in_ms"], "pad_s": plan["in"]["lead_in_pad_s"],', R146),
    ("M3 the soft hook is padded", "pipeline/sentence_law.py",
     '                    "cut_in": pick["cut_in"], "fade_in_ms": pick["fade_in_ms"], "pad_s": plan["in"]["lead_in_pad_s"],',
     '                    "cut_in": pick["cut_in"], "fade_in_ms": pick["fade_in_ms"], "pad_s": LEAD_PAD_S,', R146),
    ("M4 the snap marks every clip", "pipeline/shot_snap.py",
     '    if cut.get("clip_id") == "hook" and head and on - head / fps < SL.HEAD_LEAD_MIN_S:     # ruling 146 (2): SOFT',
     '    if head and on - head / fps < SL.HEAD_LEAD_MIN_S:', SNAP),
    ("M5 the snap still refuses the hook", "pipeline/shot_snap.py",
     "    lead_min = SL.LEAD_MIN_S                   # ruling 146 (2): the hook's HEAD_LEAD_MIN_S is soft (marked below)",
     '    lead_min = SL.HEAD_LEAD_MIN_S if cut.get("clip_id") == "hook" else SL.LEAD_MIN_S', SNAP),
    ("M6 G17a passes every row", "pipeline/run_fresh.py",
     '    return all(r["pass"] for r in table if r["segment"] != "hook")',
     '    return True', R146),
    ("M7 G17a soft on the hook's tail too", "pipeline/run_fresh.py",
     '    soft = [r for r in table if r["segment"] == "hook" and not r["lead_ok"] and r["tail_ok"]]',
     '    soft = [r for r in table if r["segment"] == "hook" and not r["lead_ok"]]', R146),
    ("M8 any cut with a hook record flags", "pipeline/run_fresh.py",
     """            flag(run, HOOK_ABRUPT, f"G17a at the cut (ruling 146 (2)): {c['hook_lead']['short']}")""",
     """            flag(run, HOOK_ABRUPT, f"G17a at the cut (ruling 146 (2)): {c['hook_lead']['short']}")
        elif isinstance(c.get("hook_lead"), dict):
            flag(run, HOOK_ABRUPT, "G17a at the cut")""", R146),
    ("M9 a refused snap passes", "pipeline/run_fresh.py",
     """        raise Hold(f"{clip_id}: shot snap refused (ruling 71): {snap['refused']}")""",
     "        pass", R146),
    ("M10 the pre-check drops the short lead", "pipeline/lock_precheck.py",
     '                             "hook_lead_short": (cut.get("hook_lead") or {}).get("short")}   # ruling 146 (2): a flag',
     '                             "hook_lead_short": None}', LP),
    ("M11 the snap's short hook is not flagged", "pipeline/run_fresh.py",
     """        flag(run, HOOK_ABRUPT, f"shot snap (ruling 146 (2)): {snap['hook_lead_short']}")""",
     "        pass", R146),
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
    code, tail = run(R146 + SNAP + LP)
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
