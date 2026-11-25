#!/usr/bin/env python3
"""The owner's ONE diagnostic of 12:14 ET Nov 25 (the 12:08 ET retry's scorer: "no Ollama listening on 127.0.0.1:11434").
Everything runs in a SCRATCH run folder, in the namespace the live services run in: lean_ops's own ns_script for the
service, HOST network (the scorer must reach the local Ollama; `unshare` without --net, as the live start), and for this
diagnostic the key files bound from /dev/null (ns_script offline=True's masks). Nothing is asked of any vendor.
  setup      the release copy at the pushed lean-release head and the namespaces' mount points, as `start` makes them
  ss         `ss -ltnp 'sport = :11434'`, `ss -ltn 'sport = :11434'` and the code's own checks
             (story_semantics.LocalLLM._listener_pid / .start, gpu0._ollama_pids), on the host and inside the scorer's
             namespace, without and with the owner bridge (lean_ops.ollama_owner + owner_bridge)
  score      the scorer, in its namespace, serving exactly ONE real candidate request (copied from the 12:08 run's queue,
             read only) once: the GPU0 lease, gemma3:27b on the shared Ollama, the verdict written, the GPU released
  python3 -B tests/package/lean/scorer_diag.py --run-dir /var/tmp/pp_leantest_run setup|ss|score --out FILE"""
import argparse
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(REPO, "pipeline"), os.path.join(REPO, "tests", "package"), HERE]
import lean_ops as LO  # noqa: E402

QUEUE = "/home/ultron/pp_lean_run/stand_alone_scorer/requests"      # the 12:08 run's 47 (read only)
LEASE = "/tmp/pulse_gpu0.lease"
WANT = "/tmp/pulse_gpu0.want"
CHECKS = r'''
import json, sys
sys.path.insert(0, "pipeline")
import story_semantics as sm, gpu0
out = {}
try:
    out["story_semantics.LocalLLM()._listener_pid()"] = sm.LocalLLM()._listener_pid()
except BaseException as e:
    out["story_semantics.LocalLLM()._listener_pid()"] = f"{type(e).__name__}: {e}"
try:
    llm = sm.LocalLLM().start()
    out["story_semantics.LocalLLM().start()"] = {"serve_pid": llm.serve_pid, "serve_env": llm.serve_env,
                                                  "digest": llm.digest}
except BaseException as e:
    out["story_semantics.LocalLLM().start()"] = f"{type(e).__name__}: {e}"
try:
    out["gpu0._ollama_pids()"] = sorted(gpu0._ollama_pids())
except BaseException as e:
    out["gpu0._ollama_pids()"] = f"{type(e).__name__}: {e}"
print(json.dumps(out, indent=1))
'''
ONCE = ("import runpy, sys; sys.argv = ['stand_alone_scorer.py', 'once']; sys.path.insert(0, 'pipeline'); "
        "runpy.run_path('pipeline/stand_alone_scorer.py', run_name='__main__')")


def scratch(run):
    run = os.path.realpath(run)
    if not run.startswith(("/tmp/", "/var/tmp/")) or run.startswith(os.path.realpath(LO.RUN)):
        raise SystemExit(f"refused: {run} must be a scratch folder under /tmp or /var/tmp (never {LO.RUN})")
    return run


def ns_cmd(p, name, td, args):
    """lean_ops.in_ns for `name` with HOST network (no --net: the live start's), the keys bound from /dev/null."""
    return ["unshare", "--user", "--map-root-user", "--mount", "bash", "-c", LO.ns_script(p, name, td, offline=True),
            "lean-ns", *args]


def env_for(p, name, store=None):
    e = dict(LO.env_instance(p, name, "diag", offline=True))   # scratch ledger, heartbeats, GPU0 want flags
    if store:
        e["PP_EDITORIAL_STORE"] = store
    return dict({k: v for k, v in os.environ.items() if k not in LO.TEST_ONLY_ENV}, **e)


def run_shown(say, argv, env=None, shown=None, timeout=900):
    say(f"$ {shown or ' '.join(shlex.quote(a) for a in argv)}")
    r = subprocess.run(argv, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=timeout,
                       cwd=REPO)
    for x in (r.stdout + r.stderr).rstrip("\n").split("\n"):
        say(f"  {x}")
    say(f"  (exit {r.returncode})")
    return r


def setup(p, say):
    _, sha = LO.head_pushed(LO.RELEASE_WT, LO.RELEASE_BRANCH)
    cmds, (alt, line) = LO.release_copy_cmds(p, sha)
    if os.path.isdir(os.path.join(p["release"], ".git")):
        cmds = cmds[1:]
    for c in cmds:
        subprocess.run(c, check=True, stdin=subprocess.DEVNULL)
    with open(alt, "a+") as f:
        f.seek(0)
        if line not in f.read().split():
            f.write(line + "\n")
    td = LO.tops()
    for n in ("scorer", "lockcheck"):
        LO.prepare_ns(p, n, td)
    for d in ("logs", "beats", "spend", "lock", "scorer"):
        os.makedirs(p[d], exist_ok=True)
    say(f"SETUP {p['run']}: the release copy at lean-release {sha[:12]} "
        f"({subprocess.run(['git', '-C', p['release'], 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()[:12]})"
        f", the scorer's and the lockcheck's mount points ({len(td)} top folders)")


def ss_phase(p, say):
    td = LO.tops()
    env = env_for(p, "scorer")
    plain = [["ss", "-ltnp", "sport = :11434"], ["ss", "-ltn", "sport = :11434"]]
    say("== ON THE HOST (this shell, uid ultron, the init user namespace) ==")
    for a in plain:
        run_shown(say, a, env=env)
    r = subprocess.run(["python3", "-c", CHECKS], capture_output=True, text=True, env=env, cwd=p["release"],
                       stdin=subprocess.DEVNULL, timeout=120)
    say("$ (cd <the release copy> && python3 -c '<CHECKS: LocalLLM()._listener_pid(), LocalLLM().start(), "
        "gpu0._ollama_pids()>')")
    for x in (r.stdout + r.stderr).rstrip("\n").split("\n"):
        say(f"  {x}")
    say(f"  (exit {r.returncode})")
    shutil.rmtree(LO.owner_dir(p, "scorer"), ignore_errors=True)
    for label in ("WITHOUT the owner bridge (as at 12:08 ET: no record)", "WITH the owner bridge"):
        if label.startswith("WITH "):
            rec = LO.ollama_owner(p, "scorer")
            say(f"-- recorded outside the namespace: {json.dumps(rec)}")
        say(f"== INSIDE the scorer's namespace (lean_ops.ns_script('scorer'), host network, keys /dev/null), {label} ==")
        for a in plain:
            run_shown(say, ns_cmd(p, "scorer", td, a), env=env, shown=f"<scorer namespace> {shlex.join(a)}")
        run_shown(say, ns_cmd(p, "scorer", td, ["python3", "-c", CHECKS]), env=env,
                  shown="<scorer namespace> python3 -c '<CHECKS: LocalLLM()._listener_pid(), LocalLLM().start(), "
                        "gpu0._ollama_pids()>'")


def gpu_state(say, when):
    smi = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip().replace("\n", " | ")
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip().replace("\n", " | ")
    holder = None
    try:
        ino = os.stat(LEASE).st_ino
        for line in open("/proc/locks"):
            f = line.split()
            if len(f) >= 6 and f[1] == "FLOCK" and f[5].rsplit(":", 1)[-1] == str(ino):
                holder = int(f[4])
    except OSError:
        pass
    ps = subprocess.run(["curl", "-s", "--max-time", "5", "http://127.0.0.1:11434/api/ps"], capture_output=True,
                        text=True).stdout.strip()
    say(f"  GPU {when}: {smi}; compute apps: {apps or 'none'}; the GPU0 lease's holder: {holder}; production's GPU0 "
        f"wants: {sorted(os.listdir(WANT))}; Ollama /api/ps: {ps}")
    return holder, ps


def score_phase(p, say):
    td = LO.tops()
    store = os.path.join(p["run"], "editorial_store")
    os.makedirs(os.path.join(p["scorer"], "requests"), exist_ok=True)
    reqs = sorted(glob.glob(os.path.join(QUEUE, "cand.*.json")))
    pick = reqs[0]
    for f in glob.glob(os.path.join(p["scorer"], "requests", "*.json")):
        os.remove(f)
    shutil.copy(pick, os.path.join(p["scorer"], "requests", os.path.basename(pick)))
    say(f"ONE real candidate: {os.path.basename(pick)} (first of the 12:08 run's {len(reqs)} queued for "
        f"2026-11-24T17:56:57, copied, read only) into {p['scorer']}/requests; the reply cache: an empty scratch store "
        f"{store} (production answered all 47 already: their cached replies would answer without loading the model)")
    with open(pick) as f:
        say(f"  the request: {f.read().strip()[:1500]}")
    holder, ps = gpu_state(say, "BEFORE")
    if holder is not None or sorted(os.listdir(WANT)):
        say("  STOP: the GPU0 lease is held or a production tenant is waiting: not taken")
        return 3
    rec = LO.ollama_owner(p, "scorer")
    say(f"  the owner, recorded outside the namespace: {json.dumps(rec)}")
    env = env_for(p, "scorer", store)
    t0 = time.time()
    r = run_shown(say, ns_cmd(p, "scorer", td, ["python3", "-c", ONCE]), env=env,
                  shown="<scorer namespace> python3 -c \"<runpy pipeline/stand_alone_scorer.py once>\"", timeout=1800)
    say(f"  the scorer: exit {r.returncode} after {time.time() - t0:.0f} s")
    gpu_state(say, "AFTER")
    for f in sorted(glob.glob(os.path.join(p["scorer"], "results", "*.json"))):
        say(f"THE VERDICT {f}:")
        with open(f) as fo:
            for x in fo.read().rstrip("\n").split("\n"):
                say(f"  {x}")
    say(f"  requests left: {sorted(os.listdir(os.path.join(p['scorer'], 'requests')))}; done: "
        f"{sorted(os.listdir(os.path.join(p['scorer'], 'requests', 'done'))) if os.path.isdir(os.path.join(p['scorer'], 'requests', 'done')) else []}")
    prod = os.path.join("/home/ultron/protocol_pulse/data/stand_alone_scorer/results",
                        os.path.basename(glob.glob(os.path.join(p["scorer"], "results", "*.json"))[0])) \
        if glob.glob(os.path.join(p["scorer"], "results", "*.json")) else None
    if prod and os.path.exists(prod):
        with open(prod) as fo:
            pv = json.load(fo)
        say(f"  production's verdict for the same moment and text (read only, {prod}): "
            f"{[{k: v.get(k) for k in ('score', 'affirmed', 'prompt_sha256', 'digest', 'at')} for v in pv]}")
    return r.returncode


LOCK_ONCE = ("import runpy, sys; sys.argv = ['lock_precheck.py', 'once']; sys.path.insert(0, 'pipeline'); "
             "runpy.run_path('pipeline/lock_precheck.py', run_name='__main__')")
CACHE = "/home/ultron/worktrees/r159-g18/data/lock_precheck/work"    # the lock pre-check's own downloads (read only)
LOCK_REQUEST = "/home/ultron/worktrees/pp-lean/tests/package/proof/lock_requests/pp-selectid.ledger_20261114_011253.1.json"
DECODER = "9326604699a7"


def lock_phase(p, say):
    """The lockcheck serving ONE real request (the one the live lockcheck took up at 12:08:30) in its namespace, once:
    the windows from the lock pre-check's own cache (their source files only: the decode runs), the decode on GPU0
    under the normal lease, the locks, and the second recogniser (Scribe) refused by the one ledger at room $0."""
    import spend_ceiling as SC
    td = LO.tops()
    root = p["lock"]
    for d in ("requests", "results", "work", "answered"):
        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
        os.makedirs(os.path.join(root, d))
    extra = os.path.join(p["run"], "offline", "lock_requests")
    shutil.rmtree(extra, ignore_errors=True)
    os.makedirs(extra)
    shutil.copy(LOCK_REQUEST, extra)
    with open(LOCK_REQUEST) as f:
        req = json.load(f)
    say(f"ONE real request: {os.path.basename(LOCK_REQUEST)} (the lockcheck's first at 12:08:30 ET; copied, read only) "
        f"into {extra}: {[(s['video_id'], s['start'], s['end'], s['role']) for s in req['segments']]}")
    for s in req["segments"]:
        name = f"{s['video_id']}.{s['start']:.3f}-{s['end']:.3f}.{DECODER}"
        src = os.path.join(CACHE, name, "sources", f"{s['video_id']}.mp4")
        dst = os.path.join(root, "work", name, "sources")
        os.makedirs(dst)
        shutil.copy(src, dst)
        say(f"  the window from the cache: {src} ({os.path.getsize(src)} bytes), its source file only (no transcript, "
            f"no second reading: the decode and the Scribe leg run)")
    SC.LEDGER_DIR = os.path.join(p["run"], "pp_spend")                    # = the service's PP_SPEND_LEDGER_DIR
    shutil.rmtree(SC.LEDGER_DIR, ignore_errors=True)
    SC.init_day({"diagnostic: room held at $0 (the owner's order of 12:14 ET)": SC.CAP_USD}, 0,
                by="scorer_diag.py lock phase")
    st = SC.status()
    say(f"  THE SCRATCH LEDGER {SC.ledger_path()}: spent ${st['spent']:.4f}, held ${st['held']:.4f}, ROOM "
        f"${st['room']:.4f}")
    if st["room"] > 0:
        say("  STOP: the room is not $0")
        return 3
    bin_ = os.path.join(p["run"], "offline", "bin")
    os.makedirs(bin_, exist_ok=True)
    with open(os.path.join(bin_, "yt-dlp"), "w") as f:
        f.write("#!/bin/sh\necho 'yt-dlp BLOCKED by the diagnostic (no download)' >&2\nexit 1\n")
    os.chmod(os.path.join(bin_, "yt-dlp"), 0o755)
    env = env_for(p, "lockcheck")
    env.update({"ELEVENLABS_API_KEY": "dummy-not-a-key-scorer-diag", "https_proxy": "http://127.0.0.1:9",
                "HTTPS_PROXY": "http://127.0.0.1:9", "no_proxy": "127.0.0.1,localhost", "NO_PROXY": "127.0.0.1,localhost",
                "PATH": bin_ + ":" + env.get("PATH", "")})
    say("  the env beyond the service's: ELEVENLABS_API_KEY=<a dummy, so the code reaches the ceiling: it reads the key "
        "first>, https_proxy/HTTPS_PROXY=http://127.0.0.1:9 (dead: no https request can leave), no_proxy=127.0.0.1,"
        "localhost (the local Ollama), PATH starting with a yt-dlp that refuses (no download)")
    holder, ps = gpu_state(say, "BEFORE")
    if holder is not None or sorted(os.listdir(WANT)):
        say("  STOP: the GPU0 lease is held or a production tenant is waiting: not taken")
        return 3
    rec = LO.ollama_owner(p, "lockcheck")
    say(f"  the owner, recorded outside the namespace: {json.dumps(rec)}")
    t0 = time.time()
    r = run_shown(say, ns_cmd(p, "lockcheck", td, ["python3", "-c", LOCK_ONCE]), env=env,
                  shown="<lockcheck namespace> python3 -c \"<runpy pipeline/lock_precheck.py once>\"", timeout=1800)
    say(f"  the lockcheck: exit {r.returncode} after {time.time() - t0:.0f} s")
    gpu_state(say, "AFTER")
    for f in sorted(glob.glob(os.path.join(root, "results", "*.json"))):
        say(f"RESULT {f}:")
        for e in json.load(open(f)):
            say("  " + json.dumps({k: e.get(k) for k in ("request_id", "video_id", "start", "end", "role", "outcome",
                                                        "reason", "source_file_sha256", "transcript_sha256",
                                                        "decoder_sha", "faster_whisper", "scribe_usd", "timing")})[:3000])
            say("    lock: " + json.dumps({k: (e.get("lock") or {}).get(k) for k in ("text", "first_word", "last_word")}))
    st = SC.status()
    say(f"  THE SCRATCH LEDGER after: spent ${st['spent']:.4f}, held ${st['held']:.4f}, room ${st['room']:.4f}; "
        f"its records: {json.dumps(SC.read(SC.ledger_path()))[:1500]}")
    out_ledger = os.path.join(p["spend"], "integrator_outside.jsonl")
    say(f"  the outside ledger {out_ledger}: "
        f"{open(out_ledger).read().strip() if os.path.exists(out_ledger) else 'absent (no vendor call recorded)'}")
    say(f"  answered markers: {sorted(os.listdir(os.path.join(root, 'answered')))}; done: "
        f"{sorted(os.listdir(os.path.join(root, 'requests', 'done'))) if os.path.isdir(os.path.join(root, 'requests', 'done')) else []}")
    for w in sorted(glob.glob(os.path.join(root, "work", "*"))):
        say(f"  {os.path.basename(w)}: {sorted(os.listdir(w))} | sources {sorted(os.listdir(os.path.join(w, 'sources')))}"
            f" | transcripts {sorted(os.listdir(os.path.join(w, 'transcripts'))) if os.path.isdir(os.path.join(w, 'transcripts')) else []}")
    return r.returncode


REPLAY = r"""
import json, socket, sys, traceback
def _no_net(*a, **k):
    raise OSError("the replay makes no network call")
socket.socket.connect = _no_net
socket.getaddrinfo = _no_net
sys.path.insert(0, "pipeline")
import pinned, lock_precheck as LP
req = json.load(open(sys.argv[1]))
sha = LP.decoder_sha()
class Reached(Exception):
    pass
def recognise(src):
    where = [f.name for f in traceback.extract_stack()][-4:-1]
    raise Reached(f"the second recogniser (Scribe) asked from {where}")
for s in req["segments"]:
    vid = s["video_id"]
    lo, hi = LP.window(req["segments"], vid)
    wd = LP.work_dir(vid, lo, hi, sha)
    mine = [dict(x, source={"kind": "youtube"}) for x in req["segments"] if x["video_id"] == vid]
    a = pinned.acquire({"segments": mine}, wd, log=lambda m: None)[vid]
    out = {"video_id": vid, "role": s["role"], "approved_text": s.get("approved_text"),
           "decode": {"source_file_sha256": a["provenance"].get("source_file_sha256"), "words": len(a["transcript"]["words"])}}
    try:
        v = pinned.validate_range(s, a)
        lock = pinned.segment_lock(s, a, v, recognise=recognise, log=lambda m: None)
        out["ruling 17 (segment_lock)"] = "the lock stands without the second recogniser"
        out["lock text"] = lock["text"]
        try:
            LP.as_spoken(lock, a["transcript"]["words"], recognise(a["path"])[0])
        except Reached as e:
            out["ruling 72 (as_spoken)"] = str(e)
    except Reached as e:
        out["ruling 17 (segment_lock)"] = str(e)
    except pinned.PinError as e:
        out["PinError"] = str(e)
    print(json.dumps(out))
"""


def replay_phase(p, say):
    """The lock code (pinned.acquire, validate_range, segment_lock, lock_precheck.as_spoken) replayed on the lock walk's
    own cached acquisition (its source and its GPU0 decode: no GPU, no download), in the lockcheck's namespace, with a
    second recogniser that only records where it is asked: how far the transcript comparison runs before the Scribe
    leg, which the walk's result entries (lock null on any error) do not show."""
    td = LO.tops()
    req = os.path.join(p["run"], "offline", "lock_requests", os.path.basename(LOCK_REQUEST))
    env = env_for(p, "lockcheck")
    env.update({"CUDA_VISIBLE_DEVICES": "", "https_proxy": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9"})
    r = run_shown(say, ns_cmd(p, "lockcheck", td, ["python3", "-c", REPLAY, req]), env=env,
                  shown="<lockcheck namespace> CUDA_VISIBLE_DEVICES='' python3 -c '<REPLAY: the lock code on the walk's "
                        "cached acquisition; a recogniser that records where it is asked>' <the request>")
    return r.returncode


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("what", choices=("setup", "ss", "score", "lockcheck", "lockreplay"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    p = LO.paths(scratch(a.run_dir))
    lines = []

    def say(x):
        lines.append(x)
        print(x, flush=True)
    say(f"SCORER DIAGNOSTIC {a.what} {time.strftime('%Y-%m-%d %H:%M:%S %Z')}: pp-lean "
        f"{subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout[:12]}, "
        f"scratch run {p['run']}")
    try:
        rc = {"setup": lambda: setup(p, say) or 0, "ss": lambda: ss_phase(p, say) or 0,
              "score": lambda: score_phase(p, say), "lockcheck": lambda: lock_phase(p, say),
              "lockreplay": lambda: replay_phase(p, say)}[a.what]()
    finally:
        with open(a.out, "w") as f:
            f.write("\n".join(lines) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
