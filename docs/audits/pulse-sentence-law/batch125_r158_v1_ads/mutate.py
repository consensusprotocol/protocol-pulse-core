#!/usr/bin/env python3
"""Batch 125 (ruling 158 (2), V1's advertising line) mutation run on a scratch copy; an unmutated control first."""
import os
import shutil
import subprocess
import sys

W = "/home/ultron/worktrees/r158-v1ad"
M = sys.argv[1]
F = "pipeline/visual_check.py"
MUTS = [
    ("V1 the line removed", F, '    ("no_on_screen_advertising", "RULING 158: no still', '    ("not_asked_any_more", "RULING 158: no still'),
    ("V2 n/a allowed for it", F,
     '        allowed_na = k in ("vertical_speaker_centred", "no_letterbox_on_talking_heads") and fmt == "16x9"\n',
     '        allowed_na = k in ("vertical_speaker_centred", "no_letterbox_on_talking_heads", "no_on_screen_advertising")\n'),
    ("V3 'cannot tell' no longer an ad", F,
     "if there is none; when you cannot tell an ad from the show's own graphic, answer \"\n",
     "if there is none; \"\n"),
]


def run():
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "pipeline/test_visual_check.py"],
                       cwd=M, env=env, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


shutil.rmtree(M, ignore_errors=True)
shutil.copytree(W, M, ignore=shutil.ignore_patterns(".git", "runs", "__pycache__"))
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
