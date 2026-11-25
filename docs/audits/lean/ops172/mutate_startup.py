"""Must-fail credit for the startup fix's tests (Nov 25): each MUTATION breaks one guarded behaviour in a SCRATCH COPY
of pp-lean (never the worktree) and must make its test fail; an unmutated control run of the same selection first must
pass. Network blocked (a dead proxy; the real-tmux tests run the namespace with --net and fail before any service).
Usage: python3 -I mutate_startup.py OUT_FILE"""
import os
import shutil
import subprocess
import sys

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mut")
LEAN = "/home/ultron/worktrees/pp-lean"
CL = os.path.join(M, "pp-lean")
ENV = dict(os.environ, http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9",
           HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9")
LOP, TL = "tests/package/lean/lean_ops.py", "tests/package/test_lean_ops.py"
CMD, KEPT = "TheStartupCommand", "TheStartupErrorsAreKept"
MOUNT = KEPT + "::test_a_service_failing_at_a_mount_leaves_its_error_in_the_run_log"
TOOLONG = KEPT + "::test_tmux_s_own_refusal_is_in_the_run_log"
MUTATIONS = [  # (label, file, old, new, test selector)
    ("the whole start line handed to tmux again (the 11:08 ET failure)", LOP,
     '    line = f"exec bash {shlex.quote(service_file(p, name))} </dev/null 2>>{shlex.quote(service_log(p, name))}"',
     '    line = " ".join(shlex.quote(x) for x in in_ns(p, name, instance_args(name), tops(), True))', CMD),
    ("the same, judged by the real-tmux test", LOP,
     '    line = f"exec bash {shlex.quote(service_file(p, name))} </dev/null 2>>{shlex.quote(service_log(p, name))}"',
     '    line = " ".join(shlex.quote(x) for x in in_ns(p, name, instance_args(name), tops(), True))', MOUNT),
    ("tmux's own output discarded again (log None)", LOP,
     'rc = o.do(tmux_cmd(p, name), what=f"the experimental {name}", log=None if o.dry else service_log(p, name))',
     'rc = o.do(tmux_cmd(p, name), what=f"the experimental {name}", log=None)', TOOLONG),
    ("a failed start prints no log tail", LOP,
     '            o.say(f"FAILED to start {name}: tmux exit {rc}; run `restore`")\n            say_tail(o, name)',
     '            o.say(f"FAILED to start {name}: tmux exit {rc}; run `restore`")', TOOLONG),
    ("the service's output not in its log (no tee)", LOP,
     '"exit $rc", f"}} 2>&1 | tee -a {shlex.quote(service_log(p, name))}"]) + "\\n"',
     '"exit $rc", "} 2>&1"]) + "\\n"', MOUNT),
    ("the pane not kept (no remain-on-exit)", LOP,
     '    return ["tmux", "new-session", "-d", "-s", s, "-c", p["run"], line, ";",\n            "set-option", "-w", "-t", f"={s}:", "remain-on-exit", "on"]',
     '    return ["tmux", "new-session", "-d", "-s", s, "-c", p["run"], line]', MOUNT),
    ("services_ready takes a kept dead pane for a service up (has-session)", LOP,
     "        state = {n: (pane_state(s), beat_fresh(o.p, n)) for n, s in SESSIONS.items()}",
     '        state = {n: ((True, None) if sh(["tmux", "has-session", "-t", f"={s}"])[0] == 0 else None, '
     'beat_fresh(o.p, n)) for n, s in SESSIONS.items()}', MOUNT),
    ("the launch's preflight takes a dead pane for a service up", LOP,
     "            up = ps is not None and ps[0]", "            up = ps is not None",
     "ThePreflight::test_a_service_whose_process_ended_is_not_up"),
    ("offline without --net", LOP, '(["--net"] if offline else [])', "[]", CMD),
    ("offline reads the live key", LOP, "{q('/dev/null' if offline else p['hide'] + '/' + KEYFILE)}",
     "{q(p['hide'] + '/' + KEYFILE)}", CMD),
]


def copy():
    if os.path.isdir(M):
        shutil.rmtree(M)
    for d in ("pipeline", "tests", "docs/audits/parallel", "docs/audits/lean"):
        if os.path.isdir(os.path.join(LEAN, d)):
            shutil.copytree(os.path.join(LEAN, d), os.path.join(CL, d), symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__"))


def run(sel):
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", f"{TL}::{sel}"],
                       cwd=CL, env=ENV, capture_output=True, text=True, timeout=900)
    tail = [x for x in r.stdout.splitlines() if " passed" in x or " failed" in x or " error" in x][-1:]
    return r.returncode, (tail[0] if tail else r.stdout[-200:].replace("\n", " "))


def main(out):
    copy()
    lines = []
    for label, f, old, new, sel in MUTATIONS:
        rc, said = run(sel)
        lines.append(f"CONTROL (unmutated) {sel}: rc {rc}: {said}")
        path = os.path.join(CL, f)
        src = open(path).read()
        if src.count(old) != 1:
            lines.append(f"NOT APPLIED ({src.count(old)} matches): {label}")
            print(lines[-1], flush=True)
            continue
        open(path, "w").write(src.replace(old, new, 1))
        rc2, said2 = run(sel)
        open(path, "w").write(src)
        lines.append(f"{'KILLED' if rc2 != 0 and rc == 0 else 'SURVIVED' if rc == 0 else 'NO CONTROL'}: {label} -> "
                     f"{sel}: rc {rc2}: {said2}")
        print(lines[-1], flush=True)
    with open(out, "w") as fo:
        fo.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
