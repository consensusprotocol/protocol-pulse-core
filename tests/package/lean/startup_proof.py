#!/usr/bin/env python3
"""The startup proof (the owner's order of 11:18 ET Nov 25, step 4): both experimental services started by
lean_ops.start ITSELF (the function THE ONE COMMAND runs, not a copy), waited for by lean_ops.services_ready, stopped by
lean_ops.restore, in a SCRATCH run folder and OFFLINE:
  - the services' namespace with no network (unshare --net: a loopback that is down, nothing else) and the key files
    bound from /dev/null (Ops(offline=True): ns_script, in_ns);
  - nothing can be asked of them: the lock service's two request folders and the scorer's empty, no candidates file;
  - nothing they write is production's: the one ledger, the outside ledger, the heartbeats and the GPU0 want flags are
    the scratch run's; the sessions are pipeline_leantest_*.
The only other changes are three module values this process sets: lean_ops.RUN, lean_ops.SESSIONS, and
spend_ceiling.LEDGER_DIR (the launcher's ledger-init writes the scratch ledger). This process itself has its sockets
and name lookups blocked. It reads what the services' network namespace counted, then restores.
  python3 -B tests/package/lean/startup_proof.py --run-dir /var/tmp/pp_leantest_run --out FILE"""
import argparse
import hashlib
import json
import os
import socket
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(REPO, "pipeline"), os.path.join(REPO, "tests", "package"), HERE]
import lean_ops as LO  # noqa: E402
import spend_ceiling as SC  # noqa: E402

LEANTEST = {"lockcheck": "pipeline_leantest_lockcheck", "scorer": "pipeline_leantest_scorer"}
LIVE_LEDGER = "/home/ultron/pp_spend"
WANT = "/tmp/pulse_gpu0.want"


def _blocked(*a, **k):
    raise OSError("startup_proof: this process makes no network call")


for _n in ("connect", "connect_ex", "sendto", "sendmsg"):
    setattr(socket.socket, _n, _blocked)
for _n in ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo"):
    setattr(socket, _n, _blocked)


def fingerprint(d):
    """Names, sizes, mtimes and content hashes of a folder's files (read only)."""
    out = {}
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        f = os.path.join(d, n)
        with open(f, "rb") as fo:
            out[n] = [os.path.getsize(f), int(os.path.getmtime(f)), hashlib.sha256(fo.read()).hexdigest()[:16]]
    return out


def children(pid):
    try:
        with open(f"/proc/{pid}/task/{pid}/children") as f:
            return [int(x) for x in f.read().split()]
    except OSError:
        return []


def argv_of(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return [x.decode(errors="replace") for x in f.read().split(b"\0") if x]
    except OSError:
        return []


def service_pid(session):
    """The service's python3 (scripts/lean/serve.py) under the session's pane."""
    rc, out = LO.sh(["tmux", "list-panes", "-s", "-t", f"={session}", "-F", "#{pane_pid}"])
    todo = [int(out.split()[0])] if rc == 0 and out.split() else []
    while todo:
        pid = todo.pop()
        a = argv_of(pid)
        if a and a[0].startswith("python") and "scripts/lean/serve.py" in a:
            return pid
        todo += children(pid)
    return None


def snmp(pid):
    """The service's network namespace's own counters (they start at 0 when the namespace is made)."""
    rows = {}
    with open(f"/proc/{pid}/net/snmp") as f:
        lines = f.read().split("\n")
    for head, vals in zip(lines[::2], lines[1::2]):
        if head and vals:
            k = head.split(":")[0]
            rows[k] = dict(zip(head.split()[1:], vals.split()[1:]))
    return {"Ip.OutRequests": rows["Ip"]["OutRequests"], "Ip.OutNoRoutes": rows["Ip"]["OutNoRoutes"],
            "Tcp.ActiveOpens": rows["Tcp"]["ActiveOpens"], "Tcp.AttemptFails": rows["Tcp"]["AttemptFails"],
            "Udp.OutDatagrams": rows["Udp"]["OutDatagrams"]}


def net_view(pid):
    with open(f"/proc/{pid}/net/dev") as f:
        devs = [x.split(":")[0].strip() + " (" + " ".join(x.split(":")[1].split()[:2]) + " rx bytes/packets)"
                for x in f.read().split("\n")[2:] if x.strip()]
    socks = {}
    for t in ("tcp", "tcp6", "udp", "udp6"):
        with open(f"/proc/{pid}/net/{t}") as f:
            socks[t] = len([x for x in f.read().split("\n")[1:] if x.strip()])
    fds = 0
    for fd in os.listdir(f"/proc/{pid}/fd"):
        try:
            fds += os.readlink(f"/proc/{pid}/fd/{fd}").startswith("socket:")
        except OSError:
            pass
    return {"netns": os.readlink(f"/proc/{pid}/ns/net"), "launcher_netns": os.readlink("/proc/self/ns/net"),
            "interfaces": devs, "inet_sockets_in_its_namespace": socks, "socket_fds_of_the_service": fds}


def key_view(pid):
    """stat only (never opened): the key paths as the service sees them."""
    null = os.stat("/dev/null").st_rdev
    out = {}
    for rel in (LO.KEYFILE, "config/api_keys.json"):
        try:
            st = os.stat(f"/proc/{pid}/root{LO.LIVE_MAIN}/{rel}")
            out[rel] = "/dev/null (character device, 0 bytes readable)" if stat.S_ISCHR(st.st_mode) and \
                st.st_rdev == null else f"NOT MASKED: mode {oct(st.st_mode)} size {st.st_size}"
        except OSError as e:
            out[rel] = f"absent ({type(e).__name__})"
    return out


def gpu_apps():
    rc, out = LO.sh(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"])
    return sorted(x.strip() for x in out.split("\n") if x.strip()) if rc == 0 else [f"nvidia-smi rc {rc}"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--idle-s", type=float, default=25.0, help="after both heartbeats: idle passes watched")
    a = ap.parse_args(argv)
    run = os.path.realpath(a.run_dir)
    if not run.startswith(("/tmp/", "/var/tmp/")) or run.startswith(os.path.realpath(LO.RUN)):
        raise SystemExit(f"refused: {run} must be a scratch folder under /tmp or /var/tmp (never {LO.RUN})")
    lines = []

    def say(x):
        lines.append(x)
        print(x, flush=True)
    LO.RUN, LO.SESSIONS, SC.LEDGER_DIR = run, dict(LEANTEST), os.path.join(run, "pp_spend")
    p = LO.paths(run)
    say(f"STARTUP PROOF {time.strftime('%Y-%m-%d %H:%M:%S %Z')}: pp-lean {LO.sh(['git', '-C', REPO, 'rev-parse', 'HEAD'])[1][:12]}"
        f", the scratch run {run}, sessions {sorted(LEANTEST.values())}, the one ledger {SC.ledger_path()}")
    live0, want0, gpu0 = fingerprint(LIVE_LEDGER), sorted(os.listdir(WANT)), gpu_apps()
    say(f"  BEFORE: the live ledger folder {LIVE_LEDGER}: {live0}; {WANT}: {want0}; GPU compute apps: {gpu0}")
    o = LO.Ops(False, out=say, p=p, offline=True)
    rc = LO.start(o, "startup_proof", strict=True)
    ready, seen = False, {}
    try:
        if rc == 0:
            ready = LO.services_ready(o, wait_s=180)
        say(f"START exit {rc}; both services up with their own first heartbeats: {ready}")
        for n, s in LEANTEST.items():
            pid = service_pid(s)
            seen[n] = pid
            say(f"  {n}: pane {LO.pane_state(s)}, service pid {pid}: {' '.join(argv_of(pid))[:200] if pid else '-'}")
            if pid:
                say(f"    keys as it sees them: {key_view(pid)}")
                say(f"    its network: {net_view(pid)}")
                say(f"    its namespace's counters at its first heartbeat: {snmp(pid)}")
        if ready:
            time.sleep(a.idle_s)                        # idle passes: the lock service every 5 s, the scorer every 10 s
            for n, pid in seen.items():
                if pid:
                    say(f"  {n}: after {a.idle_s:.0f} s more of idle passes: {snmp(pid)}; alive "
                        f"{os.path.exists(f'/proc/{pid}')}")
        say(f"  GPU compute apps while up: {gpu_apps()}")
        for f in sorted(os.listdir(p["beats"])) if os.path.isdir(p["beats"]) else []:
            with open(os.path.join(p["beats"], f)) as fo:
                say(f"  HEARTBEAT {os.path.join(p['beats'], f)}: {fo.read().strip()[:300]}")
        for n in LEANTEST:
            say(f"  SERVICE LOG {LO.service_log(p, n)}:")
            for x in LO.log_tail(LO.service_log(p, n), 40):
                say(f"    | {x[:400]}")
        st = SC.peek()
        say(f"  THE SCRATCH LEDGER {SC.ledger_path()}: spent ${st['spent']:.4f}, held ${st['held']:.4f}, room "
            f"${st['room']:.4f}, stop {st['stop']}")
        for d in (os.path.join(run, "offline", "lock_requests"), os.path.join(p["lock"], "requests"),
                  os.path.join(p["scorer"], "requests"), os.path.join(run, "offline", "gpu0_want")):
            say(f"  {d}: {sorted(os.listdir(d)) if os.path.isdir(d) else 'absent'}")
        say(f"  {os.path.join(run, 'offline', 'no_candidates.json')} exists: "
            f"{os.path.exists(os.path.join(run, 'offline', 'no_candidates.json'))}")
    finally:
        LO.restore(o)
    left = LO.tmux_sessions()
    procs = [pid for pid in seen.values() if pid and os.path.exists(f"/proc/{pid}")]
    live1, want1, gpu1 = fingerprint(LIVE_LEDGER), sorted(os.listdir(WANT)), gpu_apps()
    say(f"AFTER: pipeline_leantest_ sessions {[x for x in left if x.startswith('pipeline_leantest_')]}; the service "
        f"processes still alive {procs}; experimental processes left {LO.leftovers()}")
    say(f"  the live ledger folder unchanged: {live1 == live0} ({live1}); {WANT} unchanged: {want1 == want0} "
        f"({want1}); GPU compute apps {gpu1}")
    ok = (rc == 0 and ready and all(seen.values()) and live1 == live0 and want1 == want0 and not procs and
          not [x for x in left if x.startswith("pipeline_leantest_")])
    say(f"STARTUP PROOF: {'PASS' if ok else 'FAIL'}")
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
