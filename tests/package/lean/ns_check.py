#!/usr/bin/env python3
"""B3 (a) (the owner, 08:38 ET Nov 25): OFFLINE evidence that the experimental renderer sees every reference asset it
reads at run time. It builds THE SAME private mount namespace the render gets (lean_ops.ns_script: the pushed
lean-release copy mounted AT /home/ultron/protocol_pulse, every live tree read-only, the live tree's untracked files
under the overlaid top-level folders), in a SCRATCH run folder (never /home/ultron/pp_lean_run), with two additions of
its own: NO NETWORK at all (unshare --net: no interface but a down loopback) and the key file(s) masked by /dev/null (no
key can be read). Nothing in the live trees is written (they are read-only in the namespace; every write lands in the
scratch folder's overlay uppers). No GPU (CUDA_VISIBLE_DEVICES='' and private lease files, as the release's conftest).

  python3 -B tests/package/lean/ns_check.py --run-dir SCRATCH --sha <lean-release head> stat
        every file of docs/audits/lean/ops172/ASSETS.json stat'ed INSIDE the namespace: path, size, and which layer
        it comes from (the pushed copy or the live tree)
  python3 -B tests/package/lean/ns_check.py --run-dir SCRATCH --sha <lean-release head> pytest pipeline/test_x.py ...
        the release's test files run inside the namespace (cwd /home/ultron/protocol_pulse), each judged by its exit code"""
import argparse
import json
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lean_ops as LO  # noqa: E402

MASK = (LO.KEYFILE, "config/api_keys.json")            # bound to /dev/null inside: never readable here


def build(run_dir, sha):
    """The scratch run folder: a shared clone of the repo at `sha` (the pushed lean-release head) and the namespace's
    mount points (lean_ops.prepare_ns), exactly as `start` makes them in RUN."""
    if os.path.realpath(run_dir).startswith(os.path.realpath(LO.RUN)) or not run_dir.startswith(("/tmp/", "/var/tmp/")):
        raise SystemExit(f"refused: {run_dir} must be a scratch folder under /tmp or /var/tmp (never {LO.RUN})")
    p = LO.paths(run_dir)
    if not os.path.isdir(os.path.join(p["release"], ".git")):
        cmds, (alt, line) = LO.release_copy_cmds(p, sha)
        for c in cmds:
            subprocess.run(c, check=True, stdin=subprocess.DEVNULL)
        with open(alt, "a") as f:
            f.write(line + "\n")
    subprocess.run(["git", "-C", p["release"], "checkout", "-q", "--detach", sha], check=True)
    LO.prepare_ns(p, "check", LO.tops())
    return p


def in_ns(p, argv):
    """unshare --user --map-root-user --mount --net: the render's namespace script, the masks, then argv."""
    script = LO.ns_script(p, "check", LO.tops())
    head, tail = script.rsplit("; cd ", 1)
    masks = "; ".join(f"if [ -e {shlex.quote(LO.LIVE_MAIN + '/' + m)} ]; then mount --bind /dev/null "
                      f"{shlex.quote(LO.LIVE_MAIN + '/' + m)}; fi" for m in MASK)
    return ["unshare", "--user", "--map-root-user", "--mount", "--net", "bash", "-c",
            f"{head}; {masks}; cd {tail}", "nscheck", *argv]


ENV = {"CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1", "http_proxy": "http://127.0.0.1:9",
       "https_proxy": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9"}

STAT = r'''
import json, os, sys
inv = json.load(open(sys.argv[1]))
rows = []
for a in inv["files"]:
    p = a["path"]
    try:
        st = os.stat(p)
        rows.append({"path": p, "size": st.st_size, "want": a.get("size"), "ok": a.get("size") in (None, st.st_size)})
    except OSError as e:
        rows.append({"path": p, "size": None, "want": a.get("size"), "ok": False, "error": type(e).__name__})
for k in ("/home/ultron/protocol_pulse/.env",):
    rows.append({"path": k, "masked_size": os.stat(k).st_size if os.path.exists(k) else None})
print(json.dumps(rows))
'''


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("what", choices=("stat", "pytest"))
    ap.add_argument("files", nargs="*")
    a = ap.parse_args(argv)
    p = build(a.run_dir, a.sha)
    env = dict(os.environ, **ENV)
    if a.what == "stat":
        inv = os.path.join(a.run_dir, "ASSETS.json")
        with open(LO.ASSETS) as fi, open(inv, "w") as fo:
            fo.write(fi.read())
        r = subprocess.run(in_ns(p, ["python3", "-I", "-c", STAT, inv]), capture_output=True, text=True, env=env,
                           stdin=subprocess.DEVNULL, timeout=600)
        if r.returncode != 0:
            print(r.stderr[-2000:])
            return r.returncode
        rows = json.loads(r.stdout.strip().splitlines()[-1])
        bad = [x for x in rows if x.get("ok") is False]
        for x in rows:
            print(json.dumps(x))
        print(f"INSIDE THE NAMESPACE: {len(rows) - 1} asset files, {len(bad)} missing or of another size")
        return 1 if bad else 0
    rc_all = 0
    for t in a.files:
        r = subprocess.run(in_ns(p, ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", t]),
                           capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=3600)
        last = [x for x in r.stdout.splitlines() if " passed" in x or " failed" in x or " error" in x][-1:]
        print(f"{t}\trc={r.returncode}\t{last[0] if last else r.stdout[-300:]}")
        if r.returncode != 0:
            rc_all = 1
            fails = [x for x in r.stdout.splitlines() if x.startswith(("FAILED", "ERROR"))]
            for f in fails[:20]:
                print("    " + f[:300])
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
