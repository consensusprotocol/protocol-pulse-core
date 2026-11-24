#!/usr/bin/env python3
"""LEAN: build 171's pool replayed OFFLINE through the lean driver (pp-lean's tests/package/proof_ledger.py), the
verifier's method (pp-tests acceptance/acceptance_2026_11_24.py, READ, never edited: its HARNESS text, its sandbox
recipe): recorded answers only (Router replay; a missing recording is a ProviderError, logged with its request), the
clock frozen at build 171's start + 1 s, no network (an empty network namespace), the live trees read-only, every write
inside this folder. The pool is build 171's own 68 moments (--only); the candidate registry as it stood before build 171;
build 171's own record hidden (it did not exist at its start). $0: no model, no vendor, no Scribe.
Usage: python3 -B run_replay_171.py SCRATCH_DIR [--rerun]"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None   # a SCRATCH folder of its own
#   (it holds the clones B and R, the audio copy and the run: never inside a repository)
LEAN = "/home/ultron/worktrees/pp-lean"
LIVE_MAIN = "/home/ultron/protocol_pulse"
LV2_SRC = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad/lv2"
ACC = "/home/ultron/worktrees/pp-tests/acceptance/acceptance_2026_11_24.py"
AT = "2026-11-24T17:56:02+00:00"                 # build 171's start + 1 s (its own folder name stays free)
RUN171 = "tests/package/proof/ledger_20261124_175601"
BEFORE171 = "a800baa0e"                          # the commit before build 171's (its registry)
PINS = ["tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json",
        "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json",
        "tests/package/proof/fresh_20261111_213954/MOMENTS_PIN_BATCH_B1.json",
        "tests/package/proof/ledger_20261113_073738/MOMENTS_PIN_LEDGER.json",
        "tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json",
        "tests/package/proof/ledger_20261113_215708/MOMENTS_PIN_LEDGER.json"]
RO_TREES = ["/home/ultron/protocol_pulse", "/home/ultron/worktrees", "/home/ultron/pulse_intel", "/home/ultron/.claude",
            "/home/ultron/bifrost"]


def sh(cmd, **k):
    return subprocess.run(cmd, capture_output=True, text=True, **k)


def git(*a, cwd):
    r = sh(["git", *a], cwd=cwd)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)} in {cwd}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def harness():
    text = open(ACC).read()
    i = text.index("HARNESS = r'''") + len("HARNESS = r'''")
    j = text.index("\n'''", i)
    d = os.path.join(OUT, "harness")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "sitecustomize.py"), "w") as f:
        f.write(text[i:j] + "\n")
    return d


def prepare():
    lean_head = git("rev-parse", "HEAD", cwd=LEAN)
    rel_head = git("rev-parse", "origin/combo-letterbox-quoteonly-v2", cwd=LIVE_MAIN)
    B, R = os.path.join(OUT, "B"), os.path.join(OUT, "R")
    if not os.path.isdir(B):
        git("clone", "--quiet", "--shared", "--no-checkout", LEAN, B, cwd=OUT)
        git("remote", "set-url", "--push", "origin", "disabled://the-replay-never-pushes", cwd=B)
        git("checkout", "--quiet", "-B", "pp-lean", lean_head, cwd=B)
        reg = git("show", f"{BEFORE171}:tests/package/proof/CANDIDATES.json", cwd=B)
        with open(os.path.join(B, "tests/package/proof/CANDIDATES.json"), "w") as f:
            f.write(reg + "\n")                         # the registry as build 171 found it
        shutil.rmtree(os.path.join(B, RUN171))           # its own record did not exist at its start
    if not os.path.isdir(R):
        git("clone", "--quiet", "--shared", "--no-checkout", LIVE_MAIN, R, cwd=OUT)
        git("checkout", "--quiet", "--detach", rel_head, cwd=R)
    os.makedirs(os.path.join(R, "data"), exist_ok=True)
    lv2 = os.path.join(OUT, "lv2")
    if not os.path.isdir(lv2):
        shutil.copytree(LV2_SRC, lv2)
    inp = json.load(open(os.path.join(LEAN, RUN171, "inputs.json")))
    only = os.path.join(OUT, "ONLY_171.json")
    with open(only, "w") as f:
        json.dump({"ids": [m["moment_id"] for m in inp["moments"]],
                   "why": "the lean replay of build 171's pool (offline, recorded answers only)"}, f)
    run = os.path.join(OUT, "run")
    for d in ("hb", "lp", "lpx", "ledger", "misses"):
        os.makedirs(os.path.join(run, d), exist_ok=True)
    return {"B": B, "R": R, "lv2": lv2, "only": only, "run": run, "lean_head": lean_head, "rel_head": rel_head}


def main(argv):
    if OUT is None or OUT.startswith(("/home/ultron/worktrees", "/home/ultron/protocol_pulse")):
        raise SystemExit("usage: run_replay_171.py SCRATCH_DIR [--rerun] (a scratch folder, outside every repository)")
    os.makedirs(OUT, exist_ok=True)
    c = prepare()
    h = harness()
    hold = f"/var/tmp/lean_hold_{os.getpid()}"
    os.makedirs(hold, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
    env.update({"PYTHONPATH": h, "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "",
                "PP_GPU0_LEASE": os.path.join(c["run"], "gpu0.lease"), "PP_GPU1_LEASE": os.path.join(c["run"], "gpu1.lease"),
                "PP_HEARTBEAT_DIR": os.path.join(c["run"], "hb"),
                "PP_OUTSIDE_LEDGER": os.path.join(c["run"], "ledger", "outside.jsonl"),
                "PP_LOCK_PRECHECK_DIR": os.path.join(c["run"], "lp"), "PP_LOCK_PRECHECK_EXTRA": os.path.join(c["run"], "lpx"),
                "ACC_DENY": json.dumps(RO_TREES + ["/tmp/pulse_"]), "ACC_GUARD_LOG": os.path.join(c["run"], "guard.log"),
                "ACC_CALL_LOG": os.path.join(c["run"], "calls.log"), "ACC_REPLAY": "1", "ACC_AT": AT, "ACC_DOWN": "",
                "ACC_MISS_DIR": os.path.join(c["run"], "misses"), "PP_MAIN_TREE": c["R"]})
    q = shlex.quote
    ro = "; ".join(f"if [ -e {q(d)} ]; then mount --bind {q(d)} {q(d)} && mount -o remount,bind,ro {q(d)}; fi"
                   for d in RO_TREES)
    binds = [(os.path.join(c["R"], d), os.path.join(LIVE_MAIN, d), True) for d in ("pipeline", "scripts",
                                                                                   "video_pipeline_v3")]
    binds.append((os.path.join(LIVE_MAIN, "data"), os.path.join(c["R"], "data"), True))
    bs = "".join(f"[ -e {q(dst)} ] || mkdir -p {q(dst)}; mount --bind {q(src)} {q(dst)}; " +
                 (f"mount -o remount,bind,ro {q(dst)}; " if ro_ else "") for src, dst, ro_ in binds)
    setup = (f"set -e; mount --bind {q(OUT)} {q(hold)}; mount -t tmpfs -o mode=1777 tmpfs /tmp; mkdir -p {q(OUT)}; "
             f"mount --bind {q(hold)} {q(OUT)}; {ro}; {bs}cd {q(c['B'])}; exec \"$@\"")
    n = "9172" if "--rerun" in argv else "9171"
    cmd = ["python3", "-B", "tests/package/proof_ledger.py", "--build-no", n, "--build-id", f"lean-replay-171-{n}",
           "--out-dir-file", os.path.join(c["run"], f"outdir_{n}.txt"), "--lock-precheck", "on",
           "--routing", "heimdall_first", "--since", "2026-11-13T03:01:09Z", "--delivered", *PINS,
           "--only", c["only"], "--work-dir", c["lv2"], "--stop-usd", "1.50"]
    if "--rerun" in argv:
        env["ACC_AT"] = "2026-11-24T17:56:03+00:00"
    full = ["unshare", "--user", "--map-root-user", "--net", "--mount", "--pid", "--fork", "--mount-proc",
            "bash", "-c", setup, "lean-replay", *cmd]
    t0 = time.time()
    p = subprocess.run(full, env=env, capture_output=True, text=True, timeout=5400)
    log = os.path.join(c["run"], f"replay_{n}.log")
    with open(log, "w") as f:
        f.write(f"$ (sandbox: no network, live trees read-only, recorded answers only, clock {env['ACC_AT']}; "
                f"builder {c['lean_head'][:12]}, release {c['rel_head'][:12]})\n$ {' '.join(q(x) for x in cmd)}\n\n"
                + p.stdout + p.stderr)
    print(f"exit {p.returncode} in {time.time() - t0:.0f} s; log {log}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
