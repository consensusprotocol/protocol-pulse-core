#!/usr/bin/env python3
"""Batch 118 (ruling 145, the word pass's half) mutation run: each mutation applied to a scratch copy of the worktree,
its tests run, the file restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

W = "/home/ultron/worktrees/r145-wordpass"
M = sys.argv[1]
T = ["pipeline/test_word_pass_worker.py", "-k", "TestForeignGpu1User or TestLeaseBusy"]
F = "pipeline/word_pass_worker.py"
MUTS = [
    ("M1 the except clause removed", F,
     '        except (gpu0.Gpu0Foreign, gpu0.GpuOOM, gpu0.Gpu0NotFree) as e:   # ruling 145: another program on GPU1 ends the\n'
     '            log(f"cycle stopped, GPU1 not ours to use now: {type(e).__name__}: {e}")   # cycle, never the worker;\n'
     '            rep = {"picked": 0, "blocked": f"{type(e).__name__}"}               # the moments are picked again\n', ''),
    ("M2 every GPU stop caught (LeaseMissing too)", F,
     'except (gpu0.Gpu0Foreign, gpu0.GpuOOM, gpu0.Gpu0NotFree) as e:', 'except gpu0.Gpu0Stop as e:'),
    ("M3 no sleep after a caught stop", F,
     '            rep = {"picked": 0, "blocked": f"{type(e).__name__}"}               # the moments are picked again\n',
     '            rep = {"picked": 1}\n'),
    ("M4 only Gpu0Foreign caught", F,
     'except (gpu0.Gpu0Foreign, gpu0.GpuOOM, gpu0.Gpu0NotFree) as e:', 'except gpu0.Gpu0Foreign as e:'),
    ("M5 the stop not logged", F,
     '            log(f"cycle stopped, GPU1 not ours to use now: {type(e).__name__}: {e}")   # cycle, never the worker;\n',
     '            pass\n'),
]


def run(tests):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=M, env=env,
                           capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:                 # a mutant that loops forever (no sleep) never ends its test
        return 124, "TIMEOUT: the test never ended (the worker looped without sleeping)"
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


shutil.rmtree(M, ignore_errors=True)
shutil.copytree(W, M, ignore=shutil.ignore_patterns(".git", "runs", "__pycache__"))
rc, tail = run(T)
print(f"CONTROL (unmutated): exit {rc} | {tail}")
assert rc == 0, "the control must pass"
killed = 0
for name, fn, old, new in MUTS:
    p = os.path.join(M, fn)
    src = open(p).read()
    assert src.count(old) == 1, (name, src.count(old))
    open(p, "w").write(src.replace(old, new))
    try:
        rc, tail = run(T)
    finally:
        open(p, "w").write(src)
    killed += rc != 0
    print(f"{name}: {'KILLED' if rc else 'SURVIVED'} (exit {rc}) | {tail}")
print(f"mutations killed: {killed} of {len(MUTS)}")
