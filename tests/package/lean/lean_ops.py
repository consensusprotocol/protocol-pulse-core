#!/usr/bin/env python3
"""tests/package/lean/lean_ops.py: BUILD 172's OPERATIONS (the owner's 15:25 ET Nov 24 order: R1 one ceiling, R2
reversible routing, R3 one deadline; the owner's 08:38 ET Nov 25 blockers: B1 the ledger first and production's spend
at every reservation, B2 one paid call in flight, B3 reference assets, no delivery past the deadline, automatic
restore, ONE command). Run only by hand; nothing here is started by cron, a timer, a loop or a watcher.
Every subcommand takes --dry-run: it prints every command and checks every precondition, and executes nothing (no
process, no file, no tmux; only reads: git, ps, /proc, tmux list, crontab -l, the ledger).

  python3 -B tests/package/lean/lean_ops.py run --build-no 172 --deadline-s 6000 [--dry-run]
        THE ONE COMMAND: ledger-init, start, preflight, build, render, delivery and restore, in that order; detached
        from the terminal (stdin /dev/null, its own session, no tty), logging to a file whose path it prints; restore
        runs on every exit (success, refusal, deadline, error, SIGTERM, SIGINT, SIGHUP) and a detached guard restores
        if the launcher is killed (SIGKILL)
  python3 -B tests/package/lean/lean_ops.py snapshot                      production's state (read only)
  python3 -B tests/package/lean/lean_ops.py start   [--dry-run]           ledger-init, then the two instances (R2)
  python3 -B tests/package/lean/lean_ops.py launch  [--dry-run] [--build-no 172] [--deadline-s 2700]
  python3 -B tests/package/lean/lean_ops.py restore [--dry-run]           R2: stops them, proves production as before

R2. Production's services, files and processes are never re-pointed, restarted, signalled or written; Book Terminal and
the golds_ sessions are never named in a command. The experimental instances (tmux pipeline_lean_lockcheck: the lock
pre-check service; pipeline_lean_scorer: the clip scorer) run the PUSHED lean-release head, as a shared clone in RUN/release
mounted AT /home/ultron/protocol_pulse inside a private mount namespace of their own (unshare --user --map-root-user
--mount: the host's /tmp, pids, network and GPU0 lease, so the normal lease is taken per pass like any tenant): every live
tree read-only; every other top-level folder an overlay whose writes land in RUN/ns/<name>; the key file read-only by
name; pp-lean's pipeline/ at the production builder's path (the render's readiness check imports package_pin.py from
there). Their state is in RUN, outside every worktree: lock_precheck/ (pp-lean's requests read through EXTRA; results
seeded with a copy of production's, which the builder reads through PP_LOCK_PRECHECK_RESULTS), stand_alone_scorer/
(verdicts seeded with a copy of production's; the builder reads PP_SCORER_VERDICTS), heartbeats/ (never production's
/tmp/pulse_heartbeats), spend/, work/ (a copy of the builder's audio cache), logs/. Their command lines hold none of the
production watchdog's markers (scripts/lean/serve.py), so it never takes them for production services.
R1. Every program of the launch (the builder, the lock service, the scorer, the render, the delivery) runs with
PP_SPEND_CEILING=1: the spend day's ONE ledger (/home/ultron/pp_spend, spend_ceiling), the guard installed at start-up.
R3. ONE deadline from the launch's start to the Telegram delivery (default 2700 s): the build is handed --deadline-at
(its share), the render only the time left before the delivery's share, the delivery the rest; each stopped at its
limit by `timeout` and recorded on the build's one outcome line (outcomes.amend_stage: DEADLINE_STOPPED)."""
import argparse
import glob
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(REPO, "pipeline"), os.path.join(REPO, "tests", "package"), HERE]
import spend_ceiling as SC  # noqa: E402

LIVE_MAIN = "/home/ultron/protocol_pulse"
LIVE_BUILDER = "/home/ultron/worktrees/pp-selectid"
RELEASE_WT = "/home/ultron/worktrees/pp-lean-release"
RELEASE_BRANCH, BUILDER_BRANCH = "lean-release", "pp-lean"
RUN = os.environ.get("PP_LEAN_RUN") or "/home/ultron/pp_lean_run"       # PP_LEAN_RUN: tests only
RO_TREES = (LIVE_MAIN, "/home/ultron/worktrees", "/home/ultron/pulse_intel", "/home/ultron/.claude",
            "/home/ultron/bifrost")
PURE, LIVE_FIRST, KEYFILE = ("pipeline", "scripts", ".git"), ("data", "logs", "runs"), "." + "env"
SESSIONS = {"lockcheck": "pipeline_lean_lockcheck", "scorer": "pipeline_lean_scorer"}
WORKTREES = "/home/ultron/worktrees"
MARKERS = ("lock_precheck.py once", "lock_precheck.py serve", "stand_alone_scorer.py serve", "judge_serve.py",
           "local_judge.py serve", "word_pass_worker.py")       # tools/session_watchdog.py LAUNCH: never in ours
OURS = ("scripts/lean/serve.py", "lean-ns")                     # every experimental process's command line
SERVICES = {"session_watchdog": "tools/session_watchdog.py", "ingest_watch": "tools/ingest_watch.py",
            "judge": "judge_serve.py", "word_pass": "word_pass_worker.py", "scorer": "stand_alone_scorer.py serve",
            "lock_precheck": "lock_precheck.py", "waitress": "waitress --port=5000"}
NEVER_STARTS = ("proof_ledger.py", "build_and_record.sh", "pulse_check_run.sh", "lean_ops.py", "watch_ledger.py")
DEADLINE_S, BUILD_SHARE_S, DELIVERY_SHARE_S, GRACE_S = 2700, 1500, 120, 30   # 2700: the product's target (default)
RENDER_MEASURED_MAX_S = 3951       # the slowest measured render, preflight to verdict (Nov 13-24)
DELIVERY_MIN_S = 30                # B3 (b): a delivery starts only with this much left (the one measured took 18 s)
GUARD_POLL_S, GUARD_SLACK_S = 2.0, 300.0   # B3 (c): the guard's poll; past deadline + slack it stops the launcher
MEASURED = ("build 171, start to its stop: about 1237 s (its stage seconds); its 48 paid calls 970 s of calls over 744 s "
            "of wall time, at most 5 at once (one paid call in flight, B2: at least +226 s); the render, preflight to "
            "verdict: 3488 to 3951 s (its 3 full runs Nov 13-24: 3523, 3951, 3488); its two renders 1260-1705 s and QA "
            "gates 999-1415 s; the delivery: 18 s (Nov 13, the one delivered run)")
TEST_ONLY_ENV = ("PP_SPEND_LEDGER_DIR", "PP_SPEND_PROD_BUILDER", "PP_SPEND_PROD_OUTSIDE", "PP_SPEND_PROD_RUNS",
                 "PP_SPEND_ONE_WAIT_S", "PP_SPEND_LOCK_WAIT_S", "PP_VOICE_CHAR_CAP", "PP_LEAN_RUN")   # never in a live run
ASSETS = os.path.join(REPO, "docs", "audits", "lean", "ops172", "ASSETS.json")   # B3 (a): the render's untracked files
INGEST_DB = os.path.join(WORKTREES, "pp-ingest", "data", "editorial", "ingest", "queue.sqlite")   # B1 (c): read only
DRIVER = "tests/package/proof_ledger.py"
SINCE = "2026-11-13T03:01:09Z"
DELIVERED = tuple("tests/package/proof/" + x for x in (
    "fresh_20261112_050611/MOMENTS_PIN.json", "fresh_20261112_050611/MOMENTS_PIN_LY.json",
    "fresh_20261111_213954/MOMENTS_PIN_BATCH_B1.json", "ledger_20261113_073738/MOMENTS_PIN_LEDGER.json",
    "ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json", "ledger_20261113_215708/MOMENTS_PIN_LEDGER.json"))
CANDIDATES = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_SCORER_CANDIDATES.json")
REQUESTS = os.path.join(REPO, "tests", "package", "proof", "lock_requests")
def _lv2():
    """The builder's default work folder (proof_ly.SCRATCH/lv2: its audio cache), copied into RUN/work by `start`."""
    import proof_ly as PL
    return os.path.join(PL.SCRATCH, "lv2")
DELIVER = ("import sys, telegram as T\n"
           "run_dir, first = sys.argv[1], sys.argv[2]\n"
           "def send(kind, path, fields, data=None):\n"
           "    f = dict(fields)\n"
           "    for k, lim in (('caption', T.CAPTION_MAX), ('text', T.TEXT_MAX)):\n"
           "        if k in f:\n"
           "            f[k] = T._fit(first + '\\n' + str(f[k]), lim)\n"
           "    return T._send_bot_api(kind, path, f, data=data)\n"
           "r = T.deliver_run(run_dir, send=send)\n"
           "print('delivered:', [m.get('message_id') for m in r['messages']])\n")


def paths(run=None):
    r = run or RUN
    return {"run": r, "release": f"{r}/release", "ns": f"{r}/ns", "hide": f"{r}/ns/live_main",
            "lock": f"{r}/lock_precheck", "scorer": f"{r}/stand_alone_scorer", "beats": f"{r}/heartbeats",
            "spend": f"{r}/spend", "work": f"{r}/work", "logs": f"{r}/logs", "before": f"{r}/PRODUCTION_BEFORE.json"}


def _sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else str(b).encode()).hexdigest()[:16]


def sh(cmd, timeout=120, cwd=None):
    """A READ: -> (rc, stdout). Never used for anything that changes state."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError) as e:
        return -1, f"{type(e).__name__}"


# ── the environments (R1, R2) ──

def env_instance(p, name, run_name, offline=False):
    e = {"PP_SPEND_CEILING": "1", "PP_SPEND_RUN": run_name, "PYTHONPATH": f"{LIVE_MAIN}/scripts/lean",
         "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1", "PP_HEARTBEAT_DIR": p["beats"],
         "PP_OUTSIDE_LEDGER": f"{p['spend']}/integrator_outside.jsonl", "PP_LOCK_PRECHECK_DIR": p["lock"],
         "PP_SCORER_DIR": p["scorer"], "CUDA_VISIBLE_DEVICES": "0", "CUDA_DEVICE_ORDER": "PCI_BUS_ID"}
    if name == "lockcheck":
        e["PP_LOCK_PRECHECK_EXTRA"] = REQUESTS
    if offline:          # the startup proof only (startup_proof.py): nothing can be asked of it (an empty requests
        e.update({"PP_SPEND_LEDGER_DIR": os.path.join(p["run"], "pp_spend"),   # folder), its one ledger and its GPU0
                  "PP_GPU0_WANT_DIR": os.path.join(p["run"], "offline", "gpu0_want")})   # want flags the scratch run's
        if name == "lockcheck":
            e["PP_LOCK_PRECHECK_EXTRA"] = os.path.join(p["run"], "offline", "lock_requests")
    return e


def env_builder(p, run_name):
    return {"PP_SPEND_CEILING": "1", "PP_SPEND_RUN": run_name, "PYTHONPATH": os.path.join(HERE, "ceiling_site"),
            "PP_LOCK_PRECHECK_RESULTS": f"{p['lock']}/results",
            "PP_SCORER_VERDICTS": f"{p['scorer']}/verdicts/latest.json"}


def instance_args(name, candidates=None):
    return {"lockcheck": ["python3", "scripts/lean/serve.py", "lockcheck", "--sleep", "5"],
            "scorer": ["python3", "scripts/lean/serve.py", "scorer", "--candidates", candidates or CANDIDATES]}[name]


# ── the private mount namespace (R2) ──

def tops():
    return sorted(n for n in os.listdir(LIVE_MAIN) if n not in PURE and os.path.isdir(os.path.join(LIVE_MAIN, n))
                  and not os.path.islink(os.path.join(LIVE_MAIN, n)))


def ns_script(p, name, top_dirs, offline=False):
    """The shell that builds the namespace and execs "$@" in it (pure: it makes nothing). offline (the startup proof
    only): the key file and config/api_keys.json bound from /dev/null, so no key can be read."""
    q, u = shlex.quote, os.path.join(p["ns"], name)
    s = ["set -e"]
    s += [f"if [ -e {q(d)} ]; then mount --bind {q(d)} {q(d)}; mount -o remount,bind,ro {q(d)}; fi" for d in RO_TREES]
    s += [f"mount --rbind {q(LIVE_MAIN)} {q(p['hide'])}", f"mount -o remount,bind,ro {q(p['hide'])}",
          f"mount --bind {q(p['release'])} {q(LIVE_MAIN)}"]
    for top in top_dirs:
        lowers = [f"{p['hide']}/{top}", f"{p['release']}/{top}"]
        if top not in LIVE_FIRST:
            lowers.reverse()                       # the pushed files on top; runtime folders: the live files on top
        opts = f"lowerdir={':'.join(lowers)},upperdir={u}/upper/{top},workdir={u}/work/{top}"
        s.append(f"mount -t overlay overlay -o {q(opts)} {q(LIVE_MAIN + '/' + top)}")
    kf = f"{LIVE_MAIN}/{KEYFILE}"
    s += [f"mount --bind {q('/dev/null' if offline else p['hide'] + '/' + KEYFILE)} {q(kf)}",
          f"mount -o remount,bind,ro {q(kf)}"]
    if offline:
        ak = f"{LIVE_MAIN}/config/api_keys.json"
        s.append(f"if [ -e {q(ak)} ]; then mount --bind /dev/null {q(ak)}; fi")
    for rel in ("pipeline", "tests/package/fixtures"):
        dst = f"{LIVE_BUILDER}/{rel}"
        s += [f"mount --bind {q(REPO + '/' + rel)} {q(dst)}", f"mount -o remount,bind,ro {q(dst)}"]
    s.append(owner_bridge(p, name))
    s.append(f'cd {q(LIVE_MAIN)}; exec "$@"')
    return "; ".join(s)


def in_ns(p, name, args, top_dirs, offline=False):
    return ["unshare", "--user", "--map-root-user", "--mount"] + (["--net"] if offline else []) + \
        ["bash", "-c", ns_script(p, name, top_dirs, offline), "lean-ns", *args]


def prepare_ns(p, name, top_dirs):
    """The namespace's mount points and overlay folders (all in RUN)."""
    u = os.path.join(p["ns"], name)
    os.makedirs(p["hide"], exist_ok=True)
    for top in top_dirs:
        for d in (f"{u}/upper/{top}", f"{u}/work/{top}", f"{p['release']}/{top}"):
            os.makedirs(d, exist_ok=True)
    kf = f"{p['release']}/{KEYFILE}"
    if not os.path.exists(kf):
        open(kf, "w").close()                      # an empty mount point: the live key file is bound over it


# ── the GPU0 Ollama's owner, across the user namespace (12:08 ET Nov 25) ──

OLLAMA_PORT = 11434        # the GPU0 Ollama: gpu0.OLLAMA_HOSTS[0], story_semantics.LLM_HOST
OWNER_ENV = ("CUDA_VISIBLE_DEVICES", "OLLAMA_HOST")   # all its check reads (LocalLLM.start: serve_env); nothing else


def owner_dir(p, name):
    return os.path.join(p["ns"], name, "ollama")


def _readlink(path):
    try:
        return os.readlink(path)
    except OSError:
        return None


def ollama_owner(p, name, port=OLLAMA_PORT, write=True):
    """The GPU0 Ollama listener's owner, read HERE, outside any user namespace, exactly as the services' own checks read
    it (story_semantics.LocalLLM.start and gpu0._ollama_pids: `ss -ltnpH`, then /proc/<pid>/environ), for the namespace
    to present (owner_bridge). Inside a user namespace the kernel hides another namespace's process's fd links and
    environment, so `ss -p` names no owner and its environment cannot be read: the scorer's "no Ollama listening on
    127.0.0.1:11434" of 12:08 ET Nov 25 (release code unchanged: story_semantics.py is in SCORER_SHA, gpu0.py in the
    lock pre-check's decoder_sha). Kept: the pid, its start time, the listening socket's inode(s) and fd(s), and the
    two environment variables the check reads (OWNER_ENV); nothing else of its environment is copied. No single owner
    (nothing listens, or several pids): nothing is presented, so the services' checks refuse as they always did.
    -> the record."""
    rec = {"port": port, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": None}
    rc, out = sh(["ss", "-ltnpH", f"sport = :{port}"])
    rc2, out2 = sh(["ss", "-ltneH", f"sport = :{port}"])
    import re
    pids = sorted({int(x) for x in re.findall(r"pid=(\d+)", out)}) if rc == 0 else []
    inodes = sorted(set(re.findall(r"\bino:(\d+)", out2))) if rc2 == 0 else []
    rec["listening"] = bool(out.strip()) if rc == 0 else None
    links = {}
    if len(pids) == 1 and inodes:
        pid = pids[0]
        want = {f"socket:[{i}]" for i in inodes}
        try:
            links = {fd: _readlink(f"/proc/{pid}/fd/{fd}") for fd in os.listdir(f"/proc/{pid}/fd")}
            links = {fd: t for fd, t in links.items() if t in want}
            with open(f"/proc/{pid}/environ", "rb") as f:
                env = dict(x.split("=", 1) for x in f.read().decode(errors="ignore").split("\0") if "=" in x)
            start = proc_start(pid)
            if links and start:
                rec.update(pid=pid, start=start, inodes=inodes, fds=sorted(links, key=int),
                           env={k: env.get(k) for k in OWNER_ENV})
            else:
                rec["why"] = f"pid {pid}: no fd of the listening socket {inodes}, or gone"
        except OSError as e:
            rec["why"] = f"pid {pid}: {type(e).__name__}"
    else:
        rec["why"] = "nothing listens" if rec["listening"] is False else f"owner pids {pids}, socket inodes {inodes}"
    if write:
        d = owner_dir(p, name)
        tmp = d + ".tmp"
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(os.path.join(tmp, "fd"))
        if rec["pid"]:
            for fd in rec["fds"]:
                os.symlink(links[fd], os.path.join(tmp, "fd", fd))     # the listening socket's link, as the kernel names it
            with open(os.path.join(tmp, "environ"), "wb") as f:
                f.write(b"".join(f"{k}={v}\0".encode() for k, v in rec["env"].items() if v is not None))
            with open(os.path.join(tmp, "start"), "w") as f:
                f.write(rec["start"])
            with open(os.path.join(tmp, "pid"), "w") as f:
                f.write(str(rec["pid"]))
        with open(os.path.join(tmp, "record.json"), "w") as f:
            json.dump(rec, f, indent=1)
        shutil.rmtree(d, ignore_errors=True)
        os.replace(tmp, d)
    return rec


def say_owner(o, name):
    rec = ollama_owner(o.p, name, write=not o.dry)
    o.say(f"  {'WOULD RECORD' if o.dry else 'RECORDED'} the GPU0 Ollama's owner for the {name} namespace "
          f"({owner_dir(o.p, name)}): " + (f"pid {rec['pid']} (start {rec['start']}), socket {rec['inodes']} on fd "
                                           f"{rec['fds']}, {rec['env']}" if rec["pid"] else
                                           f"none ({rec.get('why')}): its checks will refuse"))
    return rec


def owner_bridge(p, name):
    """The namespace's lines (inside it, after its other mounts): the recorded owner presented to this namespace only,
    by bind mounts over /proc/<pid>/environ and /proc/<pid>/fd (the host's /proc is untouched), and only while that pid
    is still the process recorded (its start time): a restarted Ollama, or none, gets nothing, so the services' own
    checks refuse. A pid that exits takes the mounts with its /proc entries."""
    o = shlex.quote(owner_dir(p, name))
    return (f'if [ -s {o}/pid ]; then P="$(cat {o}/pid)"; S="$(cat {o}/start)"; '
            f'N="$(awk \'{{sub(/^.*\\) /, ""); print $20}}\' "/proc/$P/stat" 2>/dev/null || true)"; '
            f'if [ -n "$S" ] && [ "$N" = "$S" ]; then mount --bind {o}/environ "/proc/$P/environ"; '
            f'mount --bind {o}/fd "/proc/$P/fd"; fi; fi')


TMUX_MAX = 16300      # tmux 3.2a sends a command in one message of at most 16384 bytes: a longer one is refused ("command
#                       too long": the 11:08 ET start's 22,156 bytes). So the start line goes in a file; tmux gets `bash
#                       <the file>` (tests/package/test_lean_ops.py TheStartupCommand keeps it under this).


def service_log(p, name):
    return os.path.join(p["logs"], f"{name}.log")


def service_file(p, name):
    return os.path.join(p["ns"], f"{name}.start.sh")


def service_script(p, name, env, top_dirs, offline=False):
    """The service's start file (RUN/ns/<name>.start.sh, written by `start`): the namespace, then the service, every
    line of their stdout and stderr (the mount script's included) through tee into RUN/logs/<name>.log and the pane;
    the service's exit status ends the log and is the pane's (pipefail). tee also keeps the pane's terminal open: a pane
    whose every descriptor leaves its terminal is hung up by tmux at once (SIGHUP; found Nov 25 in the tests). The tmux
    server's own environment never carries a test override into a service (B1: the launcher's own is checked by
    preconditions)."""
    cand = os.path.join(p["run"], "offline", "no_candidates.json") if offline else None   # the proof: none to score
    inner = ["env"] + [f"--unset={k}" for k in TEST_ONLY_ENV] + [f"{k}={v}" for k, v in sorted(env.items())] + \
        in_ns(p, name, instance_args(name, cand), top_dirs, offline)
    stamp = '"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'
    return "\n".join(["set -o pipefail", "{", f'echo {stamp} "{name}: START (bash $$): the namespace, then the service"',
                      " ".join(shlex.quote(x) for x in inner), "rc=$?", f'echo {stamp} "{name}: ENDED, exit $rc"',
                      "exit $rc", f"}} 2>&1 | tee -a {shlex.quote(service_log(p, name))}"]) + "\n"


def tmux_cmd(p, name):
    """The service's session, handed only `bash <its start file>` (short: the start line itself is ~22 KB), stdin
    /dev/null, and bash's own errors (before its first line runs) appended to RUN/logs/<name>.log; the pane stays after
    its process ends (remain-on-exit, set in the same tmux command, before the server can see the process end) until
    `restore` kills the session."""
    s = SESSIONS[name]
    line = f"exec bash {shlex.quote(service_file(p, name))} </dev/null 2>>{shlex.quote(service_log(p, name))}"
    return ["tmux", "new-session", "-d", "-s", s, "-c", p["run"], line, ";",
            "set-option", "-w", "-t", f"={s}:", "remain-on-exit", "on"]


def log_tail(path, n=40):
    """The last n lines of a log (a failed start's own error), never the whole file into memory."""
    import collections
    try:
        with open(path, errors="replace") as f:
            return [x.rstrip("\n") for x in collections.deque(f, maxlen=n)]
    except OSError as e:
        return [f"(no log {path}: {type(e).__name__})"]


def say_tail(o, name, n=40):
    path = service_log(o.p, name)
    o.say(f"  {name}'s own log {path}, its last {n} lines:")
    for x in log_tail(path, n):
        o.say(f"    | {x[:2000]}")


def pane_state(s):
    """-> None (no such session), or (alive, exit status or None) of its pane, which stays after its process ends
    (remain-on-exit) until `restore`."""
    rc, out = sh(["tmux", "list-panes", "-s", "-t", f"={s}", "-F", "#{pane_dead} #{pane_dead_status}"])
    first = out.strip().split("\n")[0].split() if rc == 0 else []
    if not first:
        return None
    return first[0] != "1", (first[1] if first[0] == "1" and len(first) > 1 else None)


def release_copy_cmds(p, sha):
    common = os.path.realpath(os.path.join(RELEASE_WT, sh(["git", "-C", RELEASE_WT, "rev-parse", "--git-common-dir"])[1]
                                           .strip() or ".git"))
    top = os.path.dirname(common)
    r = p["release"]
    return [["git", "clone", "--quiet", "--shared", "--no-checkout", top, r],
            ["git", "-C", r, "checkout", "-q", "-B", RELEASE_BRANCH, sha],
            ["git", "-C", r, "update-ref", f"refs/remotes/origin/{RELEASE_BRANCH}", sha],
            ["git", "-C", r, "branch", "-q", f"--set-upstream-to=origin/{RELEASE_BRANCH}"],
            ["git", "-C", r, "remote", "set-url", "--push", "origin", "disabled://lean-ns"]], \
        (os.path.join(r, ".git", "objects", "info", "alternates"),
         os.path.join(p["hide"], os.path.relpath(common, LIVE_MAIN), "objects"))


# ── production's state (R2's proof) ──

def tmux_sessions():
    rc, out = sh(["tmux", "list-sessions", "-F", "#{session_name}"])
    return sorted(x for x in out.split() if x) if rc == 0 else []


def book():
    """Book Terminal's names, DISCOVERED at every use, never hard-coded (its session was book_terminal_r2 on Nov 24 and
    is book_terminal_r3 on Nov 25): every tmux session whose name holds "book", every worktree folder under
    /home/ultron/worktrees and every git worktree whose folder or branch holds "book". No command here names them."""
    sessions = [s for s in tmux_sessions() if "book" in s.lower()]
    wts, branches = set(), set()
    for d in glob.glob(os.path.join(WORKTREES, "*")):
        if "book" in os.path.basename(d).lower() and os.path.isdir(d):
            wts.add(d)
    rc, out = sh(["git", "-C", REPO, "worktree", "list", "--porcelain"])
    cur = None
    for line in out.splitlines() if rc == 0 else []:
        if line.startswith("worktree "):
            cur = line[len("worktree "):]
        elif line.startswith("branch ") and cur:
            br = line[len("branch "):].replace("refs/heads/", "")
            if "book" in os.path.basename(cur).lower() or "book" in br.lower():
                wts.add(cur)
                branches.add(br)
    for w in sorted(wts):
        b = sh(["git", "-C", w, "rev-parse", "--abbrev-ref", "HEAD"])[1].strip()
        if b:
            branches.add(b)
    return {"worktrees": sorted(wts), "branches": sorted(branches), "sessions": sorted(sessions)}


def ours_argv(argv):
    """An EXPERIMENTAL process, matched on whole arguments (never a substring of a command line, so a shell or a grep
    that merely mentions them is not one): our namespace wrapper (bash -c <script> lean-ns ...; env ... unshare ...
    lean-ns ...) or a service (python3 scripts/lean/serve.py ...). The launcher itself (lean_ops.py) never."""
    if not argv or any(os.path.basename(a) == "lean_ops.py" for a in argv):
        return False
    exe = os.path.basename(argv[0])
    if exe in ("bash", "sh", "env", "unshare", "lean-ns"):          # the wrapper: "lean-ns" as a whole argument
        return exe == "lean-ns" or "lean-ns" in argv
    if exe.startswith("python"):                                   # a service: the script is its first argument
        rest = [a for a in argv[1:] if not a.startswith("-")]
        return bool(rest) and rest[0].endswith("scripts/lean/serve.py")
    return False


def leftovers():
    """restore: the experimental processes still running (ours_argv) -> [(pid, command)]. Tests replace it: a test never
    signals a real process."""
    left = []
    for d in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            with open(d, "rb") as f:
                argv = [a.decode(errors="replace") for a in f.read().split(b"\0") if a]
        except OSError:
            continue
        if ours_argv(argv):
            left.append((int(d.split("/")[2]), " ".join(argv)[:120]))
    return left


def snapshot():
    """Production's state, read only: its service processes (pid, start, command sha), its tmux sessions and their pane
    pids, its trees (HEAD, tracked changes), the crontab, the key file's stat (never opened), its spend ledgers."""
    procs = {}
    for d in glob.glob("/proc/[0-9]*"):
        try:
            with open(d + "/cmdline", "rb") as f:
                raw = f.read()
            cmd = raw.replace(b"\0", b" ").decode(errors="replace").strip()
            with open(d + "/stat") as f:
                start = f.read().rsplit(")", 1)[1].split()[19]
        except (OSError, IndexError):
            continue
        if not cmd or ours_argv([a.decode(errors="replace") for a in raw.split(b"\0") if a]):
            continue
        for svc, mark in SERVICES.items():
            if mark in cmd:
                procs.setdefault(svc, []).append([int(d.rsplit("/", 1)[1]), start, _sha(cmd)])
    sessions = [s for s in tmux_sessions() if not s.startswith("pipeline_lean_")]
    panes = {}
    for s in sessions:
        rc, out = sh(["tmux", "list-panes", "-s", "-t", f"={s}", "-F", "#{pane_pid}"])
        panes[s] = sorted(out.split()) if rc == 0 else None
    trees = {}
    for t in (LIVE_MAIN, LIVE_BUILDER, *book()["worktrees"], os.path.join(WORKTREES, "pp-ingest")):
        trees[t] = {"head": sh(["git", "-C", t, "rev-parse", "HEAD"])[1].strip(),
                    "tracked_changes": _sha(sh(["git", "-C", t, "status", "--porcelain=v1", "--untracked-files=no"],
                                               timeout=300)[1])}
    kst = os.stat(os.path.join(LIVE_MAIN, KEYFILE))
    spend = {}
    for f in sorted(glob.glob(f"{LIVE_BUILDER}/tests/package/proof/SPEND_D*.json"))[-2:] + \
            [f"{LIVE_MAIN}/data/spend/integrator_outside.jsonl"]:
        try:
            spend[f] = _sha(open(f, "rb").read())
        except OSError:
            spend[f] = None
    return {"at": datetime.now(timezone.utc).isoformat(), "processes": {k: sorted(v) for k, v in procs.items()},
            "sessions": sessions, "panes": panes, "trees": trees, "crontab": _sha(sh(["crontab", "-l"])[1]),
            "keyfile_stat": [kst.st_size, int(kst.st_mtime)], "spend": spend}


def compare(before, after):
    """-> (differences that would be ours, notes): a production process gone or restarted, a session or pane gone or
    changed, a tree, the crontab or the key file changed. A production ledger that grew is a NOTE (production's own
    spend), never ours."""
    bad, notes = [], []
    for svc, rows in before["processes"].items():
        now = {(p, s) for p, s, _ in after["processes"].get(svc, [])}
        for p, s, _ in rows:
            if (p, s) not in now:
                bad.append(f"production process {svc} pid {p} (started {s}) is gone or restarted")
    if before["sessions"] != after["sessions"]:
        bad.append(f"production tmux sessions changed: {sorted(set(before['sessions']) ^ set(after['sessions']))}")
    for s, pp in before["panes"].items():
        if after["panes"].get(s) != pp:
            bad.append(f"production session {s}: its panes changed")
    for t, st in before["trees"].items():               # the live tree and the production builder's: strict; other
        if after["trees"].get(t) != st:                  # sessions' working trees (Book Terminal, pp-ingest) commit on
            (bad if t in (LIVE_MAIN, LIVE_BUILDER) else notes).append(   # their own: a note (no command here writes a tree)
                f"{t}: HEAD or tracked changes moved ({st.get('head', '')[:9]} -> "
                f"{(after['trees'].get(t) or {}).get('head', '')[:9]})")
    for k in ("crontab", "keyfile_stat"):
        if before[k] != after[k]:
            bad.append(f"production {k} changed")
    for f, h in before["spend"].items():
        if after["spend"].get(f) != h:
            notes.append(f"production's own ledger {f} changed (its own spend in the window: not this launch's)")
    return bad, notes


# ── the steps ──

def proc_start(pid):
    """A process's start time (/proc stat field 22), or None when it is gone: (pid, start) names ONE process."""
    try:
        with open(f"/proc/{int(pid)}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError, ValueError):
        return None


def session_members(sid):
    """Every live process of session `sid` (a stage runs in a session of its own: start_new_session)."""
    out = []
    for d in glob.glob("/proc/[0-9]*/stat"):
        try:
            with open(d) as f:
                fields = f.read().rsplit(")", 1)[1].split()
            if int(fields[3]) == int(sid) and fields[0] != "Z":
                out.append(int(d.split("/")[2]))
        except (OSError, IndexError, ValueError):
            continue
    return out


def kill_session(sid, grace=GRACE_S):
    """B3 (c): a stage's whole session stopped: SIGTERM, up to `grace` seconds, then SIGKILL. -> the pids signalled."""
    hit = []
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 5.0)):
        pids = session_members(sid)
        if not pids:
            break
        for pid in pids:
            try:
                os.kill(pid, sig)
                hit.append(pid)
            except ProcessLookupError:
                pass
        end = time.time() + wait
        while time.time() < end and session_members(sid):
            time.sleep(0.2)
    return sorted(set(hit))


def stages_file(p):
    return os.path.join(p["run"], "STAGES.json")


def _stages(p, update=None):
    """RUN/STAGES.json: the stage sessions the launcher has running ({sid: {what, start, at}}); update(d) edits it."""
    f = stages_file(p)
    try:
        with open(f) as fo:
            d = json.load(fo)
    except (OSError, ValueError):
        d = {}
    if update is not None:
        update(d)
        os.makedirs(p["run"], exist_ok=True)
        with open(f + ".tmp", "w") as fo:
            json.dump(d, fo, indent=1)
        os.replace(f + ".tmp", f)
    return d


class Ops:
    def __init__(self, dry, clock=time.time, run=None, out=print, p=None, offline=False):
        self.dry, self.clock, self.out, self.p = dry, clock, out, p or paths()
        self.offline = offline                 # the startup proof only (startup_proof.py): no network, no key, nothing
        #   to serve (main never sets it)
        self._run = run or self._exec
        self.guard_argv = None                 # B3 (c): the detached guard's command (run sets it; tests replace it)
        self.window = None                     # B1 (c): (t0, t1) of the launch, for ingestion's separate report

    def say(self, *a):
        self.out(" ".join(str(x) for x in a))

    def do(self, cmd, env=None, timeout=None, log=None, what=""):
        """A command that changes state: printed always, run only without --dry-run. -> exit code (0 in a dry run)."""
        shown = " ".join(shlex.quote(str(x)) for x in cmd)
        envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in sorted((env or {}).items()))
        self.say(f"  {'WOULD RUN' if self.dry else 'RUN'} {what}: {envs + ' ' if envs else ''}{shown}"[:4000])
        if self.dry:
            return 0
        return self._run(cmd, env, timeout, log)

    def _exec(self, cmd, env, timeout, log):
        """A stage, live: its own session (start_new_session), stdin from /dev/null (no terminal read can freeze it:
        build 170), recorded in RUN/STAGES.json while it runs; anything that interrupts the wait (a signal, an error)
        stops the stage's whole session before it propagates (B3 (c))."""
        full = dict(os.environ, **(env or {}))
        fo = open(log, "a") if log else subprocess.DEVNULL
        p = None
        try:
            p = subprocess.Popen(cmd, env=full, stdin=subprocess.DEVNULL, stdout=fo, stderr=subprocess.STDOUT, cwd=REPO,
                                 start_new_session=True)
            st = proc_start(p.pid)
            _stages(self.p, lambda d: d.__setitem__(str(p.pid), {"what": " ".join(map(str, cmd))[:300], "start": st,
                                                                 "at": datetime.now(timezone.utc).isoformat()}))
            try:
                return p.wait(timeout=None if timeout is None else timeout + 2 * GRACE_S)
            except subprocess.TimeoutExpired:          # the `timeout` inside the command did not end it: the session
                kill_session(p.pid, grace=0.0)
                p.wait()
                return 124
            except BaseException:                      # a signal or an error in the launcher: the stage goes first
                kill_session(p.pid)
                try:
                    p.wait(timeout=GRACE_S + 10)
                except BaseException:                  # noqa: BLE001 (the restore that follows stops what is left)
                    pass
                raise
        finally:
            if p is not None:
                _stages(self.p, lambda d: d.pop(str(p.pid), None))
            if log:
                fo.close()


def check(name, ok, detail, out):
    out(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return bool(ok)


def head_pushed(root, branch):
    head = sh(["git", "-C", root, "rev-parse", "HEAD"])[1].strip()
    rc, remote = sh(["git", "-C", root, "ls-remote", "origin", f"refs/heads/{branch}"], timeout=60)
    rsha = remote.split()[0] if rc == 0 and remote.split() else None
    return head, rsha


def tree_clean(root, dirs=None):
    rc, out = sh(["git", "-C", root, "status", "--porcelain=v1", "-uall", "--", *(dirs or ["."])], timeout=300)
    bad = [x[3:] for x in out.splitlines() if x[3:].strip('"').endswith((".py", ".sh"))] if rc == 0 else ["(git)"]
    return not bad, bad


def nothing_starts_by_itself():
    """No cron line, user timer, loop or watcher that could start a build or a render: -> (ok, evidence lines)."""
    ev = []
    rc, cron = sh(["crontab", "-l"])
    hits = [x for x in cron.splitlines() if not x.lstrip().startswith("#") and any(n in x for n in NEVER_STARTS)]
    ev.append(f"crontab: {len([x for x in cron.splitlines() if x.strip() and not x.lstrip().startswith('#')])} lines, "
              f"{len(hits)} naming {', '.join(NEVER_STARTS)}" + (f": {hits}" if hits else ""))
    rc, timers = sh(["systemctl", "--user", "list-timers", "--all", "--no-legend", "--no-pager"])
    th = [x for x in timers.splitlines() if x.strip()]
    ev.append(f"user timers: {len(th)}" + (f": {th}" if th else ""))
    running = []
    for d in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            cmd = open(d, "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if any(n in cmd for n in NEVER_STARTS) and "lean_ops.py" not in cmd:
            running.append(cmd[:160])
    ev.append(f"processes running {', '.join(NEVER_STARTS[:-2])} or watch_ledger.py: {len(running)}" +
              (f": {running}" if running else ""))
    return not hits and not th and not running, ev


def ledger_state():
    """The one ledger, read without the lock and without creating anything -> (state dict or None, why)."""
    try:
        st = SC.peek()
    except SC.CeilingRefused as e:
        return None, str(e)
    if not st["exists"]:
        return st, f"{st['ledger']} does not exist (not initialized)"
    if not st.get("init"):
        return st, f"{st['ledger']} is not initialized (no init record)"
    if st["stop"]:
        return st, f"{st['ledger']} is STOPPED: {st['stop']}"
    return st, ""


def assets_check(out):
    """B3 (a): every untracked file the render reads at run time (ASSETS.json: its inventory, in git), checked by path
    and size, and shown to resolve inside the render's namespace (under an overlaid top-level folder or outside the
    live tree, never under a folder the namespace takes from git only). -> (ok, lines)."""
    try:
        with open(ASSETS) as f:
            inv = json.load(f)
    except (OSError, ValueError) as e:
        return False, [f"the asset inventory {ASSETS} cannot be read ({type(e).__name__})"]
    bad, lines, opt = [], [], []
    for a in inv.get("files") or []:
        path, size = a["path"], a.get("size")
        try:
            have = os.stat(path).st_size if os.path.isfile(path) else None
        except OSError:
            have = None
        if a.get("optional"):                          # the code falls back without it: reported, never refused
            opt.append(f"{os.path.basename(path)} {'present' if have is not None else 'absent'}")
            continue
        rel = os.path.relpath(path, LIVE_MAIN)
        top = rel.split(os.sep)[0] if not rel.startswith("..") else None
        problem = None
        if have is None:
            problem = "MISSING"
        elif size is not None and have != size:
            problem = f"size {have}, inventory {size}"
        elif top in PURE and not a.get("tracked"):
            problem = f"under {top}/, which the namespace takes from git only"
        elif a.get("sha256"):                          # the render pins it (outro_locked, the face model): checked too
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != a["sha256"]:
                problem = f"sha256 {h.hexdigest()[:12]}, pinned {a['sha256'][:12]}"
        if problem:
            bad.append(f"{path}: {problem}")
    n = len(inv.get("files") or []) - len(opt)
    lines.append(f"{n} files checked by path and size, the pinned ones by sha256 too ({os.path.relpath(ASSETS, REPO)}, "
                 f"inventory of {inv.get('taken_at', '?')})" + (f"; {len(bad)} FAIL: {bad[:6]}" if bad else
                                                                ": all present") + f"; optional: {opt}")
    return not bad, lines


def preconditions(o, run_name, launch=True, t0=None, deadline_s=None):
    """Every check printed; -> True when all pass."""
    p, out, ok = o.p, o.out, True
    set_ = [k for k in TEST_ONLY_ENV if os.environ.get(k)]
    ok &= check("no test-only override in the environment", not set_, f"set: {set_}" if set_ else
                f"none of {', '.join(TEST_ONLY_ENV)}", out)
    found = SC.production_running()
    ok &= check("no production build or render running (B1)", not found, f"running: {found[:3]}" if found else
                f"none of {', '.join(SC.PRODUCTION_RUNS)} outside this launcher", out)
    h, r = head_pushed(REPO, BUILDER_BRANCH)
    clean, bad = tree_clean(REPO, ["pipeline", "tests"])
    ok &= check("pp-lean clean and pushed", clean and h and h == r, f"HEAD {h[:12]} origin {str(r)[:12]}"
                + (f"; not clean: {bad[:5]}" if not clean else ""), out)
    h2, r2 = head_pushed(RELEASE_WT, RELEASE_BRANCH)
    clean2, bad2 = tree_clean(RELEASE_WT, ["pipeline", "scripts"])
    ok &= check("lean-release clean and pushed", clean2 and h2 and h2 == r2, f"HEAD {h2[:12]} origin {str(r2)[:12]}"
                + (f"; not clean: {bad2[:5]}" if not clean2 else ""), out)
    if launch:
        rh = sh(["git", "-C", p["release"], "rev-parse", "HEAD"])[1].strip()
        ok &= check("the experimental release copy is the pushed lean-release head", rh and rh == r2,
                    f"{p['release']} at {rh[:12] or 'missing'}", out)
        clean3, bad3 = tree_clean(LIVE_MAIN, ["pipeline", "video_pipeline_v3"])
        ok &= check("the live tree (the build reads it) has no uncommitted code", clean3,
                    "clean" if clean3 else f"{bad3[:5]}", out)
    st, why = ledger_state()
    if launch:                                         # B1 (a): the launch needs the ledger initialized (by start)
        ok &= check("the one ledger initialized, readable, not stopped", st is not None and not why and
                    st["room"] > 0, why or f"{st['ledger']} (spend day from {st['day_starts']}): spent "
                    f"${st['spent']:.4f}, held ${st['held']:.4f}, ROOM ${st['room']:.4f} of ${SC.CAP_USD:.2f}", out)
    else:                                              # start: initialized next, unless it is unreadable or stopped
        ok &= check("the one ledger readable and not stopped (ledger-init comes next)",
                    st is not None and not (st["exists"] and st["stop"]),
                    why or f"{st['ledger']}: spent ${st['spent']:.4f}, held ${st['held']:.4f}", out)
    import ceiling_seed as CS
    start = SC.day_start()
    from datetime import timedelta
    try:
        parts, voice, notes, unknown = CS.parts_for(start, start + timedelta(days=1))
        ok &= check("the day's other spend accounted (carried in at init, re-read at every reservation)", not unknown,
                    f"{parts} (${sum(parts.values()):.4f}); voice {voice} characters" +
                    (f"; UNKNOWN sources: {unknown}" if unknown else ""), out)
    except SC.CeilingRefused as e:
        ok &= check("the day's other spend accounted", False, str(e), out)
    if launch and t0 is not None and deadline_s is not None:   # one spend day: the whole run inside it
        end = SC.day_start(datetime.fromtimestamp(t0, timezone.utc)) + timedelta(days=1)
        last = t0 + deadline_s + 2 * GRACE_S + GUARD_SLACK_S
        ok &= check("the deadline ends inside the spend day (no new day's $1.50 mid-run)", last <= end.timestamp(),
                    f"the run ends by {datetime.fromtimestamp(last, SC.DAY_ET):%H:%M} ET at the latest; the spend day "
                    f"ends {end:%H:%M} ET", out)
    if launch:
        a_ok, lines = assets_check(out)
        ok &= check("the render's reference assets (B3)", a_ok, " | ".join(lines), out)
    if launch:
        for name, sess in SESSIONS.items():
            ps = pane_state(sess)                      # a pane kept after its process ended is not up
            up = ps is not None and ps[0]
            fresh = beat_fresh(p, name)
            ok &= check(f"experimental {name} up ({sess})", up and fresh, f"session "
                        f"{'up' if up else (f'ENDED (exit {ps[1]})' if ps else 'MISSING')}; its "
                        f"own heartbeat {os.path.join(p['beats'], BEAT_FILES[name])} "
                        f"{'fresh' if fresh else 'MISSING or older than 900 s'}", out)
        try:
            with open(p["before"]) as f:
                before = json.load(f)
            bad, notes2 = compare(before, snapshot())
            ok &= check("production undisturbed since start", not bad, "; ".join(bad + notes2) or "as at start", out)
        except OSError:
            ok &= check("production undisturbed since start", False, f"no {p['before']}: run `start` first", out)
    quiet, ev = nothing_starts_by_itself()
    ok &= check("nothing starts by itself (cron, timers, loops)", quiet, " | ".join(ev), out)
    bk = book()
    check("Book Terminal untouched (discovered now, so commands avoid it)", True,
          f"worktrees {bk['worktrees']}, branches {bk['branches']}, tmux {bk['sessions']}: no command here names "
          f"them", out)
    return ok


BEAT_FILES = {"lockcheck": "lock_precheck.json", "scorer": "scorer.json"}   # heartbeat.path(<service>): each its own
SERVICE_WAIT_S = 180.0             # run: how long the launch waits for both services' first heartbeats after `start`


def beat_fresh(p, name, max_age=900.0):
    """A service's OWN heartbeat file (pipeline/heartbeat.py: written as the service starts, then every beat)."""
    try:
        return time.time() - os.path.getmtime(os.path.join(p["beats"], BEAT_FILES[name])) < max_age
    except OSError:
        return False


def services_ready(o, wait_s=SERVICE_WAIT_S):
    """run, between `start` and the launch: both experimental sessions up with their own first heartbeat (each service
    writes it as it starts, after its imports), waited for up to wait_s; else the run is refused."""
    if o.dry:
        o.say(f"  WOULD WAIT up to {wait_s:.0f} s for both services' own first heartbeats")
        return True
    end = time.time() + wait_s
    while True:
        state = {n: (pane_state(s), beat_fresh(o.p, n)) for n, s in SESSIONS.items()}
        ended = [n for n, (ps, _) in sorted(state.items()) if ps is not None and not ps[0]]
        if ended:                  # a service whose process ended: refused at once, with its own log's last lines
            for n in ended:
                o.say(f"REFUSED: the experimental {n} ENDED (exit {state[n][0][1]}) before the launch; its pane is "
                      f"kept until restore")
                say_tail(o, n)
            return False
        if all(ps is not None and fresh for ps, fresh in state.values()):
            o.say(f"  both services up with their own heartbeats: {sorted(state)}")
            return True
        if time.time() >= end:
            o.say(f"REFUSED: the services did not come up within {wait_s:.0f} s "
                  f"({ {n: (ps is not None, fresh) for n, (ps, fresh) in state.items()} }: up, heartbeat)")
            for n, (ps, fresh) in sorted(state.items()):
                if ps is None or not fresh:
                    say_tail(o, n)
            return False
        time.sleep(2.0)


def ledger_init(o):
    """B1 (a): the spend day's one ledger CREATED and seeded with the day's carried-in spend (ceiling_seed --write:
    SC.init_day) BEFORE any service that can charge is started. -> True when it is initialized (a dry run: printed)."""
    import ceiling_seed as CS
    o.say("  LEDGER-INIT (B1, step 1 of start): the spend day's one ledger created and seeded with the day's "
          "carried-in spend, before any service that can charge")
    if o.dry:
        o.say("  WOULD RUN the ledger-init: python3 -B tests/package/lean/ceiling_seed.py --write; its reading now:")
        CS.main([])
        return True
    if CS.main(["--write"]) != 0:
        o.say("REFUSED: the ledger-init refused (a spend source it cannot account for); no service started")
        return False
    st, why = ledger_state()
    if why:
        o.say(f"REFUSED: after the ledger-init: {why}; no service started")
        return False
    return True


def ledger_ready(o, what):
    """B1 (a): checked immediately before a service that can charge starts: the one ledger exists, is initialized,
    readable and not stopped; otherwise the service is NOT started (a dry run: its absence is only reported)."""
    st, why = ledger_state()
    if why and not o.dry:
        o.say(f"REFUSED: {what} not started: {why}")
        return False
    o.say(f"  the one ledger checked before {what}: " + (f"[dry run: {why}; the live start initializes it first]"
                                                          if why else f"{st['ledger']} initialized "
                                                          f"{(st.get('init') or {}).get('at')}, room ${st['room']:.4f}"))
    return True


def start(o, run_name="build172", strict=False):
    p = o.p
    o.say(f"START the experimental instances ({'DRY RUN: nothing is executed' if o.dry else 'live'}). ORDER: 1 the "
          f"ledger-init, 2 production BEFORE, 3 the release copy and the seeds, 4 each service, after the ledger is "
          f"checked again")
    ok = preconditions(o, run_name, launch=False)
    up = [s for s in SESSIONS.values() if sh(["tmux", "has-session", "-t", f"={s}"])[0] == 0]
    if up:
        o.say(f"  already up: {up} (start does nothing twice; `restore` first)")
        return 2 if strict else 0
    if not ok and not o.dry:
        o.say("REFUSED: a precondition failed; nothing was started")
        return 2
    if not ok:
        o.say("DRY RUN: a precondition FAILS, so a live start would be REFUSED here; the commands it would run:")
    if not ledger_init(o):                         # B1 (a): FIRST, before anything that can charge
        return 2
    _, sha = head_pushed(RELEASE_WT, RELEASE_BRANCH)
    td = tops()
    if not o.dry:
        for d in ("lock", "scorer", "beats", "spend", "work", "logs", "ns"):
            os.makedirs(p[d], exist_ok=True)
        with open(p["before"], "w") as f:
            json.dump(snapshot(), f, indent=1)
    o.say(f"  production BEFORE: {p['before']} ({'would be written' if o.dry else 'written'})")
    cmds, (alt, line) = release_copy_cmds(p, sha)
    if os.path.isdir(os.path.join(p["release"], ".git")):
        cmds = cmds[1:]                                # the copy exists: moved to the pushed head (shared objects)
    for c in cmds:
        if o.do(c, what="the release copy") != 0:
            o.say("REFUSED: the release copy failed")
            return 2
    o.say(f"  {'WOULD APPEND' if o.dry else 'APPEND'} {line} to {alt}")
    if not o.dry:
        with open(alt, "a+") as f:
            f.seek(0)
            if line not in f.read().split():
                f.write(line + "\n")
    for src, dst in ((f"{LIVE_MAIN}/data/lock_precheck/results/.", f"{p['lock']}/results"),
                     (f"{LIVE_MAIN}/data/stand_alone_scorer/verdicts/.", f"{p['scorer']}/verdicts"),
                     (f"{_lv2()}/.", p["work"])):
        o.do(["mkdir", "-p", dst], what="a seed folder")
        o.do(["cp", "-a", "--no-clobber", src, dst], what="a seed (read from production, written to RUN)")
    for name in SESSIONS:
        if not ledger_ready(o, f"the experimental {name}"):   # B1 (a): no service that can charge before the ledger
            return 2
        env = env_instance(p, name, run_name, o.offline)
        script = service_script(p, name, env, td, o.offline)
        if not o.dry:
            prepare_ns(p, name, td)
            if o.offline:
                for d in ("lock_requests", "gpu0_want"):
                    os.makedirs(os.path.join(p["run"], "offline", d), exist_ok=True)
            with open(service_file(p, name), "w") as f:
                f.write(script)
        say_owner(o, name)                             # read here, outside the namespace; presented inside it
        o.say(f"  {name}: env " + " ".join(f"{k}={v}" for k, v in sorted(env.items())))
        o.say(f"  {'WOULD WRITE' if o.dry else 'WROTE'} its start file {service_file(p, name)} ({len(script)} bytes; "
              f"tmux is handed only `bash` of it): " + next(x for x in script.split("\n") if x.startswith("env "))[:3000])
        rc = o.do(tmux_cmd(p, name), what=f"the experimental {name}", log=None if o.dry else service_log(p, name))
        if rc != 0:                                    # tmux's own error is in the service's log: shown here
            o.say(f"FAILED to start {name}: tmux exit {rc}; run `restore`")
            say_tail(o, name)
            return 1
    o.say("STARTED" if not o.dry else "DRY RUN: nothing was started")
    return 0


def restore(o):
    """Stops the experimental instances (exact session names; leftover processes by OUR command-line markers only),
    then proves production as it was at `start`. Safe to run twice."""
    p = o.p
    o.say(f"RESTORE ({'DRY RUN: nothing is executed' if o.dry else 'live'})")
    for sid, st in sorted(_stages(p).items()):         # B3 (c): a stage the launcher left running (it was killed)
        alive = session_members(int(sid))
        if not alive:
            continue
        o.say(f"  {'WOULD STOP' if o.dry else 'STOP'} the launch's stage session {sid} ({st.get('what', '')[:100]}): "
              f"{len(alive)} process(es)")
        if not o.dry:
            kill_session(int(sid))
    if not o.dry and os.path.exists(stages_file(p)):
        _stages(p, lambda d: [d.pop(k) for k in list(d) if not session_members(int(k))])
    for s in SESSIONS.values():
        if sh(["tmux", "has-session", "-t", f"={s}"])[0] == 0:
            o.do(["tmux", "kill-session", "-t", f"={s}"], what="stop")
        else:
            o.say(f"  {s}: not running (nothing to stop)")
    left = leftovers()
    for pid, cmd in left:
        o.say(f"  {'WOULD STOP' if o.dry else 'STOP'} leftover experimental process {pid}: {cmd}")
        if not o.dry:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    if left and not o.dry:
        time.sleep(5)
        for pid, _ in left:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    after = snapshot()
    try:
        with open(p["before"]) as f:
            before = json.load(f)
    except OSError:
        before = None
        o.say(f"  no {p['before']}: restore already ran, or start never did; production now: "
              f"{len(after['sessions'])} sessions, services {sorted(after['processes'])}")
    bad, notes = compare(before, after) if before is not None else ([], [])
    if before is None:
        o.say("  " + ingest_line(o))
        return 0
    o.say("  PRODUCTION AS BEFORE" if not bad else "  PRODUCTION DIFFERS: " + "; ".join(bad))
    for n in notes:
        o.say("  note: " + n)
    if not o.dry:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        with open(os.path.join(p["run"], f"PRODUCTION_AFTER_{stamp}.json"), "w") as f:
            json.dump(after, f, indent=1)
        os.replace(p["before"], os.path.join(p["run"], f"PRODUCTION_BEFORE_{stamp}.json"))
    try:
        st = SC.peek()                                  # read only, creates nothing
        o.say(f"  the one ledger: spent ${st['spent']:.4f}, held ${st['held']:.4f}, room ${st['room']:.4f}, "
              f"stop {st['stop']}")
    except SC.CeilingRefused as e:
        o.say(f"  the one ledger: {e}")
    o.say("  " + ingest_line(o))
    return 0 if not bad else 1


def ingest_spend(t0, t1, db=None, scratch=None):
    """B1 (c): the ingest miner's OWN spend between t0 and t1 (epoch seconds), from its own ledger (pp-ingest's queue,
    table `calls`, column cost_usd), read only: the database and its write-ahead log are COPIED (the live files are
    never opened by sqlite, which would create sidecar files) and the copy is read. -> {backend: [calls, usd]}."""
    import shutil
    import sqlite3
    import tempfile
    db = db or INGEST_DB
    tmp = tempfile.mkdtemp(prefix="ingest_copy_", dir=scratch)
    try:
        for suffix in ("", "-wal"):
            if os.path.exists(db + suffix):
                shutil.copyfile(db + suffix, os.path.join(tmp, "q.sqlite" + suffix))
        con = sqlite3.connect(os.path.join(tmp, "q.sqlite"))
        try:
            rows = con.execute("SELECT COALESCE(backend, '?'), COUNT(*), SUM(COALESCE(cost_usd, 0)) FROM calls "
                               "WHERE ts >= ? AND ts < ? GROUP BY 1 ORDER BY 1", (float(t0), float(t1))).fetchall()
        finally:
            con.close()
        return {b: [int(n), round(float(u or 0.0), 6)] for b, n, u in rows}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _launch_window(o):
    if o.window:
        return o.window[0], (o.window[1] if o.window[1] is not None else o.clock())
    recs = sorted(glob.glob(os.path.join(o.p["logs"], "*.launch.json")), key=os.path.getmtime)
    try:
        with open(recs[-1]) as f:
            r = json.load(f)
        return float(r["t0"]), o.clock()
    except (IndexError, OSError, ValueError, KeyError):
        return None


def ingest_line(o):
    """B1 (c): ONE separate line, never added to the $1.50 (ingestion keeps running, untouched, outside the ceiling)."""
    w = _launch_window(o)
    if o.dry or w is None:
        return (f"INGESTION (separate, NEVER in the $1.50): read at restore from {INGEST_DB} (table calls, cost_usd), "
                f"for the launch's window" + (" (no launch yet)" if w is None else ""))
    try:
        by = ingest_spend(w[0], w[1], scratch=o.p["run"] if os.path.isdir(o.p["run"]) else None)
    except Exception as e:                              # noqa: BLE001 (a report line; never stops the restore)
        return f"INGESTION (separate, NEVER in the $1.50): {INGEST_DB} could not be read ({type(e).__name__}: {e})"
    tot = round(sum(u for _, u in by.values()), 6)
    outside = {b: v for b, v in by.items() if not str(b).startswith("heimdall")}
    return (f"INGESTION (separate, NEVER in the $1.50): ${tot:.4f} in {sum(n for n, _ in by.values())} calls between "
            f"{datetime.fromtimestamp(w[0], SC.DAY_ET):%H:%M:%S} and {datetime.fromtimestamp(w[1], SC.DAY_ET):%H:%M:%S}"
            f" ET, from {INGEST_DB} (table calls); by back-end {by}; outside vendors (ruling 98's paid route) "
            f"{outside or 'none'}")


def shares(t0, deadline_s):
    """R3: ONE deadline; -> {"deadline_at", "build_at", "render_at"} (epoch seconds). The build's share ends at
    BUILD_SHARE_S (build 171 stopped at about 1237 s), or later when the deadline leaves more than the slowest measured
    render (RENDER_MEASURED_MAX_S) and the delivery's share need (build 172's 6000 s: 1929 s; the default 2700 s: 1500
    s, as before); the render's ends DELIVERY_SHARE_S before the deadline (the one measured delivery: 18 s), the
    delivery's at the deadline."""
    deadline_at = t0 + deadline_s
    build_s = max(BUILD_SHARE_S, deadline_s - DELIVERY_SHARE_S - RENDER_MEASURED_MAX_S)
    return {"deadline_at": deadline_at, "build_at": min(t0 + build_s, deadline_at - DELIVERY_SHARE_S),
            "render_at": deadline_at - DELIVERY_SHARE_S}


def launch(o, build_no=172, deadline_s=DEADLINE_S, why="the owner's build 172 (lean)", t0=None):
    import outcomes as OC
    p, t0 = o.p, (o.clock() if t0 is None else t0)
    sh_ = shares(t0, deadline_s)
    run_name = f"build{build_no}"
    stamp = datetime.fromtimestamp(t0, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    build_id = f"b{build_no}-{stamp}-lean"
    o.say(f"LAUNCH build {build_no} ({'DRY RUN: nothing is executed' if o.dry else 'live'}): {why}")
    o.say(f"  R3 the one deadline: {deadline_s} s from {datetime.fromtimestamp(t0, timezone.utc).isoformat()}; the "
          f"build's share to +{sh_['build_at'] - t0:.0f} s, the render's to +{sh_['render_at'] - t0:.0f} s, the "
          f"delivery's to +{deadline_s} s. Measured: {MEASURED}")
    if deadline_s != DEADLINE_S:
        o.say(f"  R3 NOTE: {deadline_s} s is THIS build's deadline, an exception for this one build; the product's "
              f"target, and this script's default, stays {DEADLINE_S} s")
    if deadline_s < RENDER_MEASURED_MAX_S + BUILD_SHARE_S // 2:
        o.say(f"  R3 NOTE: the measured render alone (3488-3951 s) does not fit in {deadline_s} s: unless it is "
              f"faster than every measured run, it is stopped at its share (DEADLINE_STOPPED at render)")
    if not preconditions(o, run_name, launch=True, t0=t0, deadline_s=deadline_s):
        if not o.dry:
            o.say("REFUSED: a precondition failed; nothing was started")
            return 2
        o.say("DRY RUN: a precondition FAILS, so a live launch would be REFUSED here; the commands it would run:")
    record = {"build_no": build_no, "build_id": build_id, "t0": t0, "deadline_s": deadline_s, **sh_, "stages": {}}
    o.window = (t0, None)
    if not o.dry:
        os.makedirs(p["logs"], exist_ok=True)
        with open(os.path.join(p["logs"], f"{build_id}.launch.json"), "w") as f:
            json.dump(record, f, indent=1)                 # its t0 from the start (B1 (c): ingestion's window)
    benv = env_builder(p, run_name)
    outf = os.path.join(p["logs"], f"{build_id}.outdir")
    left = sh_["build_at"] - o.clock()
    cmd = ["timeout", "--signal=TERM", f"--kill-after={GRACE_S}", f"{max(1, int(left)) + GRACE_S}", "python3", "-B",
           DRIVER, "--build-no", str(build_no), "--build-id", build_id, "--out-dir-file", outf, "--lock-precheck", "on",
           "--routing", "heimdall_first", "--since", SINCE, "--work-dir", p["work"], "--deadline-at",
           f"{sh_['build_at']:.0f}", "--delivered", *DELIVERED]
    tb = o.clock()
    rc = o.do(cmd, env=benv, timeout=left + GRACE_S, log=os.path.join(p["logs"], f"{build_id}.build.log"),
              what=f"the build (its share: {left:.0f} s)")
    record["stages"]["build"] = {"exit": rc, "seconds": round(o.clock() - tb, 1)}
    d = None
    if not o.dry:
        try:
            d = open(outf).read().strip()
        except OSError:
            d = None
    pin = next((x for x in (f"{d}/MOMENTS_PIN_LEDGER.json", f"{d}/SPOTLIGHT_PIN.json") if d and os.path.exists(x)),
               None) if not o.dry else "<the build's pin>"
    run = os.path.basename(d) if d else "<the build's record>"
    if pin is None:
        o.say(f"  no pin (build exit {rc}): its one outcome line stands; no render, no delivery")
        return finish(o, record, d)
    td = tops()
    renv = dict(env_instance(p, "render", run_name))
    left = sh_["render_at"] - o.clock()
    if left <= 0:
        o.say("  the render's share is already used up: not started")
        if not o.dry:
            OC.amend_stage(run, "render", OC.DEADLINE_EXIT, 0.0, pin, "not started: no time left")
        return finish(o, record, d)
    if not o.dry:
        prepare_ns(p, "render", td)
    say_owner(o, "render")                             # the render's checks read the GPU0 Ollama's owner too
    said = os.path.join(p["logs"], f"{build_id}.render.log")
    tr = o.clock()
    rc = o.do(["timeout", "--signal=TERM", f"--kill-after={GRACE_S}", f"{max(1, int(left))}",
               *in_ns(p, "render", ["bash", "scripts/pulse_check_run.sh", "--pinned", pin, "--foreground",
                                    "--no-telegram"], td)],
              env=renv, timeout=left, log=said, what=f"the render (the time left: {left:.0f} s)")
    secs = round(o.clock() - tr, 1)
    record["stages"]["render"] = {"exit": rc, "seconds": secs}
    tail = "" if o.dry else open(said, errors="replace").read()[-4000:]
    if not o.dry:
        line = OC.amend_stage(run, "render", rc, secs, pin, tail)
        o.say(f"  the render: exit {rc}, {secs} s; the outcome line: {(line or {}).get('outcome')}")
    run_dir = None
    if not o.dry:
        import re
        m = re.search(r"=== FRESH-TOPIC RUN (\S+) ===", tail) or re.search(r"run dir (\S+)", tail)
        run_dir = m.group(1) if m else None
    if rc != 0 or (not o.dry and not run_dir):
        o.say("  not delivered (the render did not release it)")
        return finish(o, record, d)
    left = sh_["deadline_at"] - o.clock()               # B3 (b): THE check, immediately before the delivery, on the
    if left < DELIVERY_MIN_S and not o.dry:            # launch's one clock: an expired deadline starts nothing
        o.say(f"  the deadline: {max(0.0, left):.0f} s left, under the delivery's {DELIVERY_MIN_S} s: NOT delivered "
              f"(nothing is sent)")
        record["stages"]["delivery"] = {"exit": OC.DEADLINE_EXIT, "seconds": 0.0, "not_started": True}
        OC.amend_stage(run, "delivery", OC.DEADLINE_EXIT, 0.0, pin,
                       f"not started: {max(0.0, left):.0f} s left at the deadline check (B3)")
        return finish(o, record, d)
    td_ = o.clock()
    rc = o.do(["timeout", "--signal=TERM", "--kill-after=10", f"{max(1, int(left))}",
               *in_ns(p, "render", ["bash", "-c", 'cd pipeline && exec python3 -c "$0" "$@"', DELIVER,
                                     run_dir or "<the render's run dir>",
                                     f"LEAN BUILD {build_no}: EXPERIMENTAL (pp-lean / lean-release)"], td)],
              env=renv, timeout=left, log=os.path.join(p["logs"], f"{build_id}.delivery.log"),
              what=f"the delivery (the time left: {left:.0f} s)")
    record["stages"]["delivery"] = {"exit": rc, "seconds": round(o.clock() - td_, 1)}
    if not o.dry:
        OC.amend_stage(run, "delivery", rc, record["stages"]["delivery"]["seconds"], pin)
    return finish(o, record, d)


def finish(o, record, d):
    record["seconds_total"] = round(o.clock() - record["t0"], 1)
    record["inside_deadline"] = o.clock() <= record["deadline_at"] + 2 * GRACE_S
    try:
        record["ledger"] = SC.peek() if o.dry else SC.status()     # a dry run creates nothing
    except SC.CeilingRefused as e:
        record["ledger"] = str(e)
    o.say(f"  LAUNCH RECORD: {json.dumps({k: v for k, v in record.items() if k != 'ledger'})}")
    if not o.dry:
        for path in (os.path.join(o.p["logs"], f"{record['build_id']}.launch.json"),
                     *( [os.path.join(d, "LEAN_LAUNCH.json")] if d and os.path.isdir(d) else [])):
            with open(path, "w") as f:
                json.dump(record, f, indent=1, default=str)
    return 0


class RunStopped(BaseException):
    """B3 (c): SIGTERM, SIGINT or SIGHUP reached the launcher: its stage is stopped and it restores (a BaseException,
    so no `except Exception` on the way swallows it)."""

    def __init__(self, signum):
        super().__init__(f"signal {signal.Signals(signum).name}")
        self.signum = signum


def restored_marker(p, pid):
    return os.path.join(p["run"], f"RESTORED.{pid}")


def _mark(path, why):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {why}\n")


def guard_cmd(pid, start, deadline_at):
    return [sys.executable, "-B", os.path.abspath(__file__), "guard", "--pid", str(pid), "--start", str(start),
            "--deadline-at", f"{deadline_at:.0f}"]


def spawn_guard(o, deadline_at, log=None):
    """B3 (c): a DETACHED restorer (its own session, stdin /dev/null) watching this launcher by (pid, start time): if
    the launcher disappears without having restored (SIGKILL), it restores; if the launcher is still running
    GUARD_SLACK_S past the deadline, it stops it (SIGTERM, then SIGKILL a minute later) and restores."""
    me = os.getpid()
    argv = (o.guard_argv or guard_cmd)(me, proc_start(me), deadline_at)
    if o.dry:
        o.say("  WOULD START the guard (detached): " + " ".join(shlex.quote(str(x)) for x in argv))
        return None
    fo = open(log, "a") if log else subprocess.DEVNULL
    try:
        g = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=fo, stderr=subprocess.STDOUT, cwd=REPO,
                             start_new_session=True, close_fds=True)
    finally:
        if log:
            fo.close()
    o.say(f"  the guard: pid {g.pid}, watching launcher {me} (it restores if the launcher is killed)")
    return g


def guard(o, pid, start, deadline_at=None, poll=GUARD_POLL_S):
    """B3 (c): the guard's loop (`lean_ops.py guard`). -> restore's exit code, or 0 when the launcher restored."""
    marker, termed = restored_marker(o.p, pid), None
    o.say(f"GUARD: watching launcher {pid} (start {start}); deadline {deadline_at}")
    while True:
        if proc_start(pid) != str(start):
            if os.path.exists(marker):
                o.say(f"GUARD: launcher {pid} ended and restored itself: nothing to do")
                return 0
            held = run_lock(o.p)                        # a newer run already live restores its own: never ours to stop
            if held is None:
                o.say(f"GUARD: launcher {pid} is gone, but another run holds RUN.lock: it restores; nothing done here")
                return 0
            o.say(f"GUARD: launcher {pid} is gone WITHOUT restoring (killed): RESTORE")
            try:
                return restore(o)
            finally:
                _mark(marker, "restored by the guard")
                held.close()
        now = time.time()
        if deadline_at and now > float(deadline_at) + GUARD_SLACK_S:
            sig = signal.SIGTERM if termed is None else signal.SIGKILL if now > termed + 60 else None
            if sig is not None:
                o.say(f"GUARD: launcher {pid} still running past the deadline (+{GUARD_SLACK_S:.0f} s): {sig.name}")
                try:
                    os.kill(int(pid), sig)
                except ProcessLookupError:
                    pass
                termed = termed or now
        time.sleep(poll)


def run_lock(p):
    """ONE run at a time: an exclusive lock on RUN/RUN.lock, held for the launcher's life (the kernel drops it when the
    process ends, SIGKILL included). -> the open file holding it, or None when another run holds it."""
    import fcntl
    os.makedirs(p["run"], exist_ok=True)
    f = open(os.path.join(p["run"], "RUN.lock"), "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    f.seek(0)
    f.truncate()
    f.write(f"{os.getpid()}\n")
    f.flush()
    return f


def run(o, build_no=172, deadline_s=DEADLINE_S, log=None):
    """THE ONE COMMAND's body: ledger-init and start, then the launch (preflight, build, render, delivery), then
    RESTORE on every exit path: success, refusal, deadline, an error, SIGTERM, SIGINT, SIGHUP (B3 (c)); a detached
    guard covers SIGKILL. The one deadline counts from this command's start. A second run while one is live is refused
    BEFORE anything else, and restores nothing (its restore would stop the live run's services). -> the exit code."""
    t0 = o.clock()
    sh_ = shares(t0, deadline_s)
    o.say(f"RUN build {build_no} ({'DRY RUN: nothing is executed' if o.dry else 'live'}): pid {os.getpid()}; log "
          f"{log or '(this terminal)'}; ORDER: ledger-init, start, preflight, build, render, delivery, restore")
    held = None
    if not o.dry:
        held = run_lock(o.p)
        if held is None:
            o.say(f"REFUSED: another run holds {os.path.join(o.p['run'], 'RUN.lock')}: nothing started, nothing "
                  f"restored (that run restores its own)")
            return 2
    o.run_lock = held
    prev, rc, why = {}, 1, "an error"

    def on_signal(signum, frame):
        raise RunStopped(signum)
    if not o.dry:
        for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            prev[s] = signal.signal(s, on_signal)
    try:
        spawn_guard(o, sh_["deadline_at"], log)
        rc = start(o, f"build{build_no}", strict=True)
        if rc != 0 and not o.dry:
            why = "refused at start"
            return rc
        if not services_ready(o):
            rc, why = 2, "the services did not come up"
            return rc
        rc = launch(o, build_no, deadline_s, t0=t0)
        why = {0: "the launch ended", 2: "refused at the launch's preflight"}.get(rc, f"exit {rc}")
        return rc
    except RunStopped as e:
        rc, why = 128 + e.signum, f"stopped by {e}"
        o.say(f"STOPPED by {e}: the running stage was stopped first")
        return rc
    except BaseException as e:                          # noqa: BLE001 (any error: restore, then a non-zero exit)
        import traceback
        rc, why = 1, f"{type(e).__name__}: {e}"
        o.say("ERROR: " + "".join(traceback.format_exception(type(e), e, e.__traceback__))[-1500:])
        return rc
    finally:
        for s in prev:                                   # nothing interrupts the restore
            signal.signal(s, signal.SIG_IGN)
        o.window = (t0, o.clock())
        o.say(f"RUN ENDING ({why}, exit {rc}): RESTORE")
        try:
            restore(o)
        finally:
            if not o.dry:
                _mark(restored_marker(o.p, os.getpid()), why)
            if held is not None:                         # after the restore and its marker: the next run may start
                held.close()


def detach(argv, p, entry=None):
    """THE ONE COMMAND, live: the run re-started detached from any terminal (its own session, stdin /dev/null, no
    tty: build 170 was frozen by a terminal read), logging to a file whose path is printed."""
    os.makedirs(p["logs"], exist_ok=True)
    log = os.path.join(p["logs"], f"run_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.log")
    with open(log, "a") as fo:
        child = subprocess.Popen([sys.executable, "-B", entry or os.path.abspath(__file__), *argv, "--foreground",
                                  "--log", log],
                                 stdin=subprocess.DEVNULL, stdout=fo, stderr=subprocess.STDOUT, cwd=REPO,
                                 start_new_session=True, close_fds=True)
    print(f"RUN DETACHED: pid {child.pid} (its own session, stdin /dev/null, no terminal)")
    print(f"LOG: {log}")
    print(f"  follow: tail -f {log}    stop it early: kill -TERM {child.pid} (it stops its stage and restores)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=("run", "snapshot", "start", "launch", "restore", "guard"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--build-no", type=int, default=172)
    ap.add_argument("--deadline-s", type=int, default=DEADLINE_S, help="R3: the one wall-clock budget (default 2700)")
    ap.add_argument("--foreground", action="store_true", help="run: in this process (the detached child; tests)")
    ap.add_argument("--log", help="run: the log file (set by the detaching parent)")
    ap.add_argument("--pid", type=int, help="guard: the launcher's pid")
    ap.add_argument("--start", help="guard: the launcher's /proc start time")
    ap.add_argument("--deadline-at", type=float, help="guard: the launch's deadline (epoch seconds)")
    raw = list(sys.argv[1:] if argv is None else argv)
    a = ap.parse_args(raw)
    o = Ops(a.dry_run)
    if a.what == "snapshot":
        print(json.dumps(snapshot(), indent=1))
        return 0
    if a.what == "start":
        return start(o, f"build{a.build_no}")
    if a.what == "restore":
        return restore(o)
    if a.what == "guard":
        return guard(o, a.pid, a.start, a.deadline_at)
    if a.what == "run":
        if not a.dry_run and not a.foreground:
            return detach([x for x in raw if x not in ("--foreground",)], o.p)
        return run(o, a.build_no, a.deadline_s, a.log)
    return launch(o, a.build_no, a.deadline_s)


if __name__ == "__main__":
    sys.exit(main())
