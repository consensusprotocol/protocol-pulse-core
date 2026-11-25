"""Must-fail credit for the owner bridge (12:08 ET scorer failure); adapted from the startup fix's tests (Nov 25): each MUTATION breaks one guarded behaviour in a SCRATCH COPY
of pp-lean (never the worktree) and must make its test fail; an unmutated control run of the same selection first must
pass. Network blocked (a dead proxy; the real-tmux tests run the namespace with --net and fail before any service).
Usage: python3 -I mutate_startup.py OUT_FILE"""
import os
import shutil
import subprocess
import sys

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mut_owner")
LEAN = "/home/ultron/worktrees/pp-lean"
CL = os.path.join(M, "pp-lean")
ENV = dict(os.environ, http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9",
           HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9")
LOP, TL = "tests/package/lean/lean_ops.py", "tests/package/test_lean_ops.py"
CMD, KEPT = "TheStartupCommand", "TheStartupErrorsAreKept"
MOUNT = KEPT + "::test_a_service_failing_at_a_mount_leaves_its_error_in_the_run_log"
TOOLONG = KEPT + "::test_tmux_s_own_refusal_is_in_the_run_log"
MUTATIONS_ALL = [  # (label, file, old, new, test selector)
    ("the bridge presents a record whatever process holds that pid now (no start-time check)", LOP,
     """if [ -n "$S" ] && [ "$N" = "$S" ]; then mount""", """if [ -n "$S" ]; then mount""",
     "TheOllamaOwner::test_an_owner_that_cannot_be_identified_is_not_accepted"),
    ("the record says GPU0-only whatever the owner's environment says", LOP,
     "env={k: env.get(k) for k in OWNER_ENV})", 'env={"CUDA_VISIBLE_DEVICES": "0", "OLLAMA_HOST": env.get("OLLAMA_HOST")})',
     "TheOllamaOwner::test_an_owner_not_gpu0_only_is_still_refused"),
    ("the bridge presents the environment only (no fd link: ss names no owner)", LOP,
     """f'mount --bind {o}/fd "/proc/$P/fd"; fi; fi')""", """f'fi; fi')""",
     "TheOllamaOwner::test_the_owner_read_outside_is_seen_inside_and_accepted"),
    ("the record copies the owner's whole environment", LOP,
     "env={k: env.get(k) for k in OWNER_ENV})", "env=dict(env))",
     "TheOllamaOwner::test_only_the_two_variables_the_check_reads_are_copied"),
    ("a namespace without the bridge", LOP, "    s.append(owner_bridge(p, name))\n", "",
     "TheOllamaOwner::test_every_namespace_carries_the_bridge"),
    ("start does not record the owner before a service", LOP,
     "        say_owner(o, name)                             # read here, outside the namespace; presented inside it\n", "",
     "TheOwnerIsRecordedFirst"),
    ("launch does not record the owner before the render", LOP,
     "    say_owner(o, \"render\")                             # the render's checks read the GPU0 Ollama's owner too\n", "",
     "TheOneDeadline::test_the_render_s_namespace_gets_the_owner_recorded_first"),
]
MUTATIONS = [m for m in MUTATIONS_ALL if m[0].startswith('the bridge presents the environment only')]


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
