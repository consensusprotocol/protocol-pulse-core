#!/usr/bin/env python3
"""Batch 100 (ruling 131) mutation run: each mutation applied to a scratch copy of the worktree's pipeline/, its tests
run with the network blocked (-p netguard), the file restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r131-lock"
M = os.path.join(S, "b100", "mut")
LOCK = ["pipeline/test_ruling17_lock.py", "pipeline/test_lock_precheck.py"]
PRE = ["pipeline/test_lock_precheck.py"]
TG = ["pipeline/test_telegram_delivery.py"]
G18 = ["pipeline/test_word_diff.py", "pipeline/test_canon.py"]

MUTS = [
    ("M1 edge 3->2", "pipeline/pinned.py", "MAJORITY_EDGE = 3 ", "MAJORITY_EDGE = 2 ", LOCK),
    ("M2 >= -> >", "pipeline/pinned.py", "run_ok and dist >= MAJORITY_EDGE", "run_ok and dist > MAJORITY_EDGE", LOCK),
    ("M3 no left slide", "pipeline/pinned.py", "while n <= left and seq[x - n] == seq[y - n]:",
     "while False and n <= left:", LOCK),
    ("M4 no right slide", "pipeline/pinned.py", "while n <= right and seq[x + n - 1] == seq[y + n - 1]:",
     "while False and n <= right:", LOCK),
    ("M5 slide max->min", "pipeline/pinned.py", "return max(min(a + n, len(r) - (b + n)) for n in shifts)",
     "return min(min(a + n, len(r) - (b + n)) for n in shifts)", LOCK),
    ("M6 no currency filter", "pipeline/pinned.py", "    if cur:\n        ops = [o for o in ops if o not in cur]",
     "    if cur and False:\n        ops = [o for o in ops if o not in cur]", LOCK),
    ("M7 run wins without the second", "pipeline/pinned.py",
     'took = "approved" if pin_ok else "run" if run_ok and dist', 'took = "approved" if pin_ok else "run" if dist', LOCK),
    ("M8 held pairs ignored", "pipeline/pinned.py", "            if took is None:\n                held.append(pair)",
     "            if took is None:\n                pass", LOCK),
    ("M9 merged keeps approved", "pipeline/pinned.py",
     'want += r[a:b] if (x is not None and x["took"] == "run") else p[c:d]', "want += p[c:d]", LOCK),
    ("M10 dollars at k=0", "pipeline/canon.py", 'return tokens[k] == "dollars" and k > 0 and',
     'return tokens[k] == "dollars" and', G18),
    ("M11 no dollars drop", "pipeline/canon.py",
     "return [w for k, w in enumerate(tokens) if not dollars_after_number(tokens, k)]", "return list(tokens)", G18),
    ("M12 no (A) seal", "pipeline/lock_precheck.py", 'if verdict == "same" and majority:', "if False:", PRE),
    ("M13 sealed = second's text", "pipeline/lock_precheck.py", 'outcome, sealed = "adopt_spoken", first["text"]',
     'outcome, sealed = "adopt_spoken", text', PRE),
    ("M14 no re-lock", "pipeline/lock_precheck.py",
     '                            lock = pinned.segment_lock(s2, a, pinned.validate_range(s2, a), recognise=recognise, log=log)\n                            outcome, sealed = "adopt_spoken", first["text"]',
     '                            lock = first\n                            outcome, sealed = "adopt_spoken", first["text"]', PRE),
    ("M15 entry adjudication = re-lock's", "pipeline/lock_precheck.py",
     '"adjudication": (_majority(first) or lock.get("adjudication")', '"adjudication": (lock.get("adjudication")', PRE),
    ("M16 as_spoken no currency", "pipeline/lock_precheck.py",
     "and not (all(canon.dollars_after_number(L, i)", "and not (False and all(canon.dollars_after_number(L, i)", PRE),
    ("M17 no currency_format in entry", "pipeline/lock_precheck.py",
     '"currency_format": (first or {}).get("currency_format")', '"currency_format": None', PRE),
    ("M18 caption: render lock ignored", "pipeline/telegram.py",
     'str(x["adjudication"].get("rule", "")).startswith("ruling 131 (A)") for x in locks)',
     'str(x["adjudication"].get("rule", "")).startswith("never") for x in locks)', TG),
    ("M19 caption: pin ignored", "pipeline/telegram.py", "majority = majority or sealed", "majority = majority", TG),
    ("M20 caption: no digest binding", "pipeline/telegram.py",
     'if sealed and not (isinstance(sha, str) and sha and sha == edl.get("moments_package_sha256")):',
     "if False:", TG),
    ("M21 caption: no currency line", "pipeline/telegram.py", "currency = any(x.get(\"currency_format\") for x in locks)",
     "currency = False", TG),
    ("M22 caption: lines dropped", "pipeline/telegram.py",
     "lines[2:2] = bar_lines(run_dir, edl) + lock_lines(run_dir, edl)", "lines[2:2] = bar_lines(run_dir, edl)", TG),
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
    deselect = ["--deselect", "pipeline/test_word_diff.py::TestYesterdaysFinal"]   # GPU0 lease tests (error on CPU)
    code, tail = run(LOCK + PRE + TG + G18 + deselect)
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
