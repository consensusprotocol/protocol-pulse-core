#!/usr/bin/env python3
"""Batch 100 (ruling 131) mutation run: each mutation applied to a scratch copy of the worktree's pipeline/, its tests
run with the network blocked (-p netguard), the file restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r101-spend"
M = os.path.join(S, "b101", "mut")
LOCK = ["pipeline/test_ruling17_lock.py", "pipeline/test_lock_precheck.py"]
PRE = ["pipeline/test_lock_precheck.py"]
TG = ["pipeline/test_telegram_delivery.py"]
G18 = ["pipeline/test_word_diff.py", "pipeline/test_canon.py"]

SP = ["pipeline/test_outside_spend.py"]
RU = ["pipeline/test_lock_precheck.py"]
MUTS = [
    ("B1 no Scribe line", "pipeline/second_recogniser.py", '    outside_spend.record("elevenlabs:scribe_v1"', '    (lambda *a, **k: None)("elevenlabs:scribe_v1"', SP),
    ("B2 ticks scale", "pipeline/signoff.py", "usd = ticks / 1e10 if", "usd = ticks / 1e9 if", SP),
    ("B3 sign-off call unrecorded", "pipeline/signoff.py", "        _spent(body, segment_id)", "        pass", SP),
    ("B4 no TTS line", "pipeline/vo.py", '        outside_spend.record(f"elevenlabs:tts:{model_id}"', '        (lambda *a, **k: None)(f"elevenlabs:tts:{model_id}"', SP),
    ("B5 window start open", "pipeline/outside_spend.py", "if a <= _when(d[\"at\"]) < b:", "if a < _when(d[\"at\"]) < b:", SP),
    ("B6 unpriced hidden", "pipeline/outside_spend.py", "return round(usd, 6), inside, [d for d in inside if not isinstance(d.get(\"usd\"), (int, float))]", "return round(usd, 6), inside, []", SP),
    ("B7 service not named", "pipeline/outside_spend.py", '"service": SERVICE,', '"service": "unknown",', SP),
    ("B8 ratio 0", "pipeline/lock_precheck.py", "REUSE_RATIO = 0.8 ", "REUSE_RATIO = 0.0 ", RU),
    ("B9 offset unchecked", "pipeline/lock_precheck.py", 'if c.get("offset") is not None and float(c["offset"]) != float(a["offset"]):', "if False:", RU),
    ("B10 any window", "pipeline/lock_precheck.py", 'os.path.join(ROOT, "work", base + ".*", "second_recogniser.json")', 'os.path.join(ROOT, "work", base.split(".")[0] + ".*", "second_recogniser.json")', RU),
    ("B11 never reused", "pipeline/lock_precheck.py", "    prev = _earlier(a, wd)\n", "    prev = None\n", RU),
    ("B12 pre-check unnamed", "pipeline/lock_precheck.py", '    outside_spend.SERVICE = "lock_precheck"', '    outside_spend.SERVICE = outside_spend.SERVICE', RU),
    ("B13 failed write raises", "pipeline/outside_spend.py", '        print(f"  OUTSIDE SPEND NOT RECORDED', '        raise\n        print(f"  OUTSIDE SPEND NOT RECORDED', SP),
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
    code, tail = run(SP + RU)
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
