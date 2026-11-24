#!/usr/bin/env python3
"""Ruling 159 (b) rows, batches 121 (G18 under ruling 143) and 123 (the watchdog restarts a dead service): each mutation
applied to a scratch copy of the worktree, its tests run, the file restored. An unmutated control runs first."""
import os
import shutil
import subprocess
import sys

W = "/home/ultron/worktrees/r159-g18"
M = sys.argv[1]
G18 = ["pipeline/test_word_diff.py", "-k", "Ruling143"]
HB = ["pipeline/test_heartbeat.py"]
WD = "tools/session_watchdog.py"
MUTS = [
    ("G1 the adjudicated precondition back", "pipeline/word_diff.py",
     '        small_only = bool(row["identity"]) and \\\n',
     '        small_only = bool(row["identity"]) and bool(c.get("adjudicated")) and \\\n', G18),
    ("G2 materiality ignored", "pipeline/word_diff.py",
     '            not _material(row["identity"], (c["lock_text"], heard))      # ruling 143 (2): a small word never holds,\n',
     '            True\n', G18),
    ("R1 a running service is restarted", WD,
     '        if is_running(LAUNCH[name][0]):\n', '        if False:\n', HB),
    ("R2 no gap between restarts", WD,
     '        if now - float(last.get(name, 0)) < RESTART_GAP_S:\n', '        if False:\n', HB),
    ("R3 a stuck pass is restarted too", WD,
     '''        if f.get("kind") != "HEARTBEAT" or name not in LAUNCH or not f.get("dead"):\n''',
     '''        if f.get("kind") != "HEARTBEAT" or name not in LAUNCH:\n''', HB),
    ("R4 a dry run restarts", WD,
     '        if not dry_run:\n            status["restarts"] = restart_dead(f, state, now, paths, sessions)    # ruling 159 (b): any hour\n',
     '        status["restarts"] = restart_dead(f, state, now, paths, sessions)    # ruling 159 (b): any hour\n', HB),
    ("R5 the restart sends keys", WD,
     '''    argv = (["tmux", "new-window", "-t", f"={session}:", "-n", f"{name}-restarted", cmd] if present\n''',
     '''    argv = (["tmux", "send-keys", "-t", f"={session}:", "-n", f"{name}-restarted", cmd] if present\n''', HB),
    ("R6 the missing-heartbeat restart is not marked dead", WD,
     '''                out.append(finding(session, "HEARTBEAT", f"{name}: no heartbeat written", since, service=name,\n                                   dead=True))''',
     '''                out.append(finding(session, "HEARTBEAT", f"{name}: no heartbeat written", since, service=name))''', HB),
]


def run(tests):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=M, env=env,
                           capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


shutil.rmtree(M, ignore_errors=True)
shutil.copytree(W, M, ignore=shutil.ignore_patterns(".git", "runs", "__pycache__"))
for t in (G18, HB):
    rc, tail = run(t)
    print(f"CONTROL {t[0]}: exit {rc} | {tail}")
    assert rc == 0
killed = 0
for name, fn, old, new, tests in MUTS:
    p = os.path.join(M, fn)
    src = open(p).read()
    assert src.count(old) == 1, (name, src.count(old))
    open(p, "w").write(src.replace(old, new))
    try:
        rc, tail = run(tests)
    finally:
        open(p, "w").write(src)
    killed += rc != 0
    print(f"{name}: {'KILLED' if rc else 'SURVIVED'} (exit {rc}) | {tail}")
print(f"mutations killed: {killed} of {len(MUTS)}")
