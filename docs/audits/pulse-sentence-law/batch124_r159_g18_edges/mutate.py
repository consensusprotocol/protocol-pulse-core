#!/usr/bin/env python3
"""Batch 124 (ruling 159 (b) at G18's edges) mutation run on a scratch copy; an unmutated control first."""
import os
import shutil
import subprocess
import sys

W = "/home/ultron/worktrees/r143-tests"
M = sys.argv[1]
T = ["pipeline/test_word_diff.py", "pipeline/test_ruling17_lock.py"]
F = "pipeline/word_diff.py"
MUTS = [
    ("E1 every edge difference counts as a substitution", F,
     "    if not edge:\n        return False\n    for tag, i1, i2, j1, j2 in edge:\n",
     "    return True\n    for tag, i1, i2, j1, j2 in edge:\n"),
    ("E2 a material edge word allowed", F,
     '        if _material([("replace", " ".join(e[i1:i2]), " ".join(h[j1:j2]))], (expected, heard)):\n            return False\n',
     ""),
    ("E3 an inserted or omitted edge word allowed", F,
     '        if tag != "replace" or i2 - i1 != j2 - j1:\n            return False\n', ""),
    ("E4 the edge cleared without the audio", F,
     '            if row["omission_adjudication"].get("same_audio"):\n                row["edges_small_words"], row["edges"] = row["edges"], []\n',
     '            row["edges_small_words"], row["edges"] = row["edges"], []\n'),
]


def run():
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *T, "-k",
                        "Ruling143 or Nov12 or SettledLock or Ruling135 or Canonical"], cwd=M, env=env,
                       capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


shutil.rmtree(M, ignore_errors=True)
shutil.copytree(W, M, ignore=shutil.ignore_patterns(".git", "runs", "__pycache__"), symlinks=True)
if not os.path.exists(os.path.join(M, "runs")):
    os.symlink("/home/ultron/protocol_pulse/runs", os.path.join(M, "runs"))
rc, tail = run()
print(f"CONTROL: exit {rc} | {tail}")
assert rc == 0
killed = 0
for name, fn, old, new in MUTS:
    p = os.path.join(M, fn)
    src = open(p).read()
    assert src.count(old) == 1, (name, src.count(old))
    open(p, "w").write(src.replace(old, new))
    try:
        rc, tail = run()
    finally:
        open(p, "w").write(src)
    killed += rc != 0
    print(f"{name}: {'KILLED' if rc else 'SURVIVED'} (exit {rc}) | {tail}")
print(f"mutations killed: {killed} of {len(MUTS)}")
