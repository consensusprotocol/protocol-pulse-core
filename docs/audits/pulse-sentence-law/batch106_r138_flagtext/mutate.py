#!/usr/bin/env python3
"""Batch 106 (ruling 138 (3); ruling 137 (2): V1's credits row and malformed SOFT evidence HARD) mutation run: each
mutation applied to a scratch copy of the worktree, its tests run with the network blocked (-p netguard), the file
restored. An unmutated control runs first and must pass."""
import os
import shutil
import subprocess
import sys

S = "/tmp/claude-1000/-home-ultron-protocol-pulse/f10c552c-cf11-4d53-ab62-ba6be4b5be5a/scratchpad"
W = "/home/ultron/worktrees/r138-flagtext"
M = os.path.join(S, "b106", "mut")
RA = ["pipeline/test_release_auth.py"]
TG = ["pipeline/test_telegram_delivery.py"]
SF = ["pipeline/test_stand_alone_floor.py", "pipeline/test_ruling91_takeaway.py"]
ADV = ["tests/adversarial/test_f3_release_auth.py", "tests/adversarial/test_f4_vacuity.py"]
FB = ["pipeline/test_failure_blocks.py"]
MUTS = [
    ("N1 clips never named", "pipeline/release_auth.py",
     '    m = re.fullmatch(r"clip[_ ]0*(\\d+)", str(seg))', '    m = None', RA),
    ("N2 no 'both versions'", "pipeline/release_auth.py",
     '''        where = "both versions" if len(fmts) > 1 else f"the {fmts[0].replace('x', ':')} version"''',
     '''        where = f"the {fmts[0].replace('x', ':')} version"''', RA),
    ("N3 V1 credits 'no' soft", "pipeline/release_auth.py",
     '    return "the vision check doubted the credits card (speaker credit is HARD)" if CREDITS_ROW in d else None',
     '    return None', RA),
    ("N4 V1 credits unanswered soft", "pipeline/release_auth.py",
     '    if any(CREDITS_ROW not in (d.get("rows") or {}) for d in per):', '    if False:', RA),
    ("N5 malformed SOFT evidence flags", "pipeline/release_auth.py",
     '            if e is not None and not (isinstance(e, dict) and type(e.get("executed")) is bool',
     '            if False and not (isinstance(e, dict) and type(e.get("executed")) is bool', RA + ADV),
    ("N6 SKIPPED said as a doubt", "pipeline/release_auth.py",
     '        if v == "SKIPPED" or v == "PASS" and evidence is not NO_EVIDENCE_CHECK and not measured:',
     '        if v == "PASS" and evidence is not NO_EVIDENCE_CHECK and not measured:', RA),
    ("N7 'non-hook' names the opener", "pipeline/run_fresh.py",
     '_LABEL = re.compile(r"(?<![-\\w])(hook|clip[_ ]\\d+)\\b")', '_LABEL = re.compile(r"(hook|clip[_ ]\\d+)\\b")', SF),
    ("N8 flags on one line", "pipeline/telegram.py",
     '        head = "\\n".join(["REVIEW FLAGS:"] + [f"- {f}" for f in flagged]) + "\\n" + head',
     '        head = "REVIEW FLAGS: " + "; ".join(flagged) + "\\n" + head', TG),
    ("N9 authorise skips the credits row", "pipeline/release_auth.py",
     '        cb = v1_credit_block(fmt, rows.get(fmt), rep)   # ruling 137 (2): V1\'s credits row is HARD',
     '        cb = None', RA),
    ("N10 authorise names no clip", "pipeline/release_auth.py",
     '    note = review_flags({fmt: flags(fmt, rows.get(fmt), evidence, rep, edl) for fmt in formats},',
     '    note = review_flags({fmt: flags(fmt, rows.get(fmt), evidence) for fmt in formats},', RA),
    ("N11 V1 says no row", "pipeline/release_auth.py",
     '        what = " and that ".join(words) or "the video looks right"', '        what = "the video looks right"', RA),
    ("N12 G9 says neither", "pipeline/release_auth.py",
     '        what = " and ".join(bad) or "might look or sound wrong"', '        what = "might look or sound wrong"', RA),
    ("N13 0 samples counts as measured", "pipeline/release_auth.py",
     '            and e["samples"] >= 1\n        if v == "SKIPPED"', '            and e["samples"] >= 0\n        if v == "SKIPPED"',
     RA + ADV),
    ("N14 stand-alone names no clip", "pipeline/run_fresh.py",
     '                                   edl, r["segment"]), r["opener"]["why"])',
     '                                   edl, ""), r["opener"]["why"])', SF),
]


def run(tests):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH=S)
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "netguard", "-q", "-p", "no:cacheprovider", "-x",
                        *tests], cwd=M, env=env, capture_output=True, text=True, timeout=900)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return r.returncode, tail


def main():
    if os.path.exists(M):
        shutil.rmtree(M)
    os.makedirs(M)
    for d in ("pipeline", "segment_v1", "scripts", "config", "tests/fixtures", "tests/adversarial"):
        if os.path.isdir(os.path.join(W, d)):
            shutil.copytree(os.path.join(W, d), os.path.join(M, d), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(W, "references", "pulse_fresh_2026-11-13"),
                    os.path.join(M, "references", "pulse_fresh_2026-11-13"))
    os.makedirs(os.path.join(M, "video_pipeline_v3"), exist_ok=True)
    shutil.copy2(os.path.join(W, "video_pipeline_v3", "relay.py"), os.path.join(M, "video_pipeline_v3", "relay.py"))
    code, tail = run(RA + TG + SF + ADV + FB)
    print(f"CONTROL (unmutated): exit {code} | {tail}", flush=True)
    if code != 0:
        sys.exit("control failed: no mutation result would mean anything")
    killed = 0
    for name, rel, old, new, tests in MUTS:
        path = os.path.join(M, rel)
        src = open(path).read()
        if src.count(old) != 1:
            print(f"{name}: NOT APPLIED (found {src.count(old)} times)", flush=True)
            continue
        open(path, "w").write(src.replace(old, new))
        try:
            code, tail = run(tests)
        finally:
            open(path, "w").write(src)
        ok = code != 0
        killed += ok
        print(f"{name}: {'KILLED' if ok else 'SURVIVED'} | {tail}", flush=True)
    print(f"{killed} of {len(MUTS)} killed")


if __name__ == "__main__":
    main()
