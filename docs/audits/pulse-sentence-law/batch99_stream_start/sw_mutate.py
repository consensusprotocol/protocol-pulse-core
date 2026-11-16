#!/usr/bin/env python3
"""Batch 99 mutations: each must make the suites fail; the unmutated control must pass first.
Usage: python3 gt_mutate.py WORKTREE NETGUARD_DIR"""
import os
import subprocess
import sys

W, NG = sys.argv[1], sys.argv[2]
TS, TI = "pipeline/transcript_store.py", "pipeline/transcript_ingest.py"
TESTS = ["pipeline/test_stream_window.py", "pipeline/test_transcript_store_live.py", "pipeline/test_transcript_ingest.py"]
MUT = [
    ("W1 the universe ignores the stream start", TI,
     "            if age > hours:", "            if age > hours and False:"),
    ("W2 the release_timestamp not read", TS,
     '    for field in ("release_timestamp",) + (("metadata_fetched_at",) if m.get("live_status") in LIVE_STATES else ()):',
     '    for field in (("metadata_fetched_at",) if m.get("live_status") in LIVE_STATES else ()):'),
    ("W3 the read time used for a finished stream too", TS,
     '    for field in ("release_timestamp",) + (("metadata_fetched_at",) if m.get("live_status") in LIVE_STATES else ()):',
     '    for field in ("release_timestamp", "metadata_fetched_at"):'),
    ("W4 any record taken as a stream", TS,
     '    if not isinstance(m, dict) or m.get("live_status") not in LIVE_STATES + ("was_live",):',
     "    if not isinstance(m, dict):"),
    ("W5 meta.json, not the newest snapshot", TS, "        m = _newest_meta(video_id)\n    except (OSError, ValueError, TypeError):",
     '        m = json.load(open(os.path.join(_vdir(video_id), "meta.json")))\n    except (OSError, ValueError, TypeError):'),
    ("W6 the release_timestamp not stored", TS,
     '        "release_timestamp": _release_iso(j.get("release_timestamp")),', '        "release_timestamp": None,'),
    ("W7 any release_timestamp value accepted", TS,
     "    if isinstance(x, bool) or not isinstance(x, (int, float)):", "    if x is None:"),
    ("W8 a future start counted", TI, "            if 0 <= age <= hours:", "            if age <= hours:"),
    ("W9 an unreadable record breaks the universe", TS,
     "        m = _newest_meta(video_id)\n    except (OSError, ValueError, TypeError):",
     "        m = _newest_meta(video_id)\n    except KeyError:"),
]


def run():
    env = dict(os.environ, PYTHONPATH=NG, CUDA_VISIBLE_DEVICES="")
    try:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "netguard", "-q", "-p", "no:cacheprovider",
                            "-x", *TESTS], cwd=W, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 124, "timed out (300 s)"
    tail = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l or "error" in l.lower()]
    return r.returncode, (tail[-1] if tail else r.stdout[-200:]).strip()


code, tail = run()
print(f"CONTROL (unmutated): exit {code} | {tail}", flush=True)
if code != 0:
    sys.exit("control failed: no mutation run")
killed = 0
for name, rel, old, new in MUT:
    p = os.path.join(W, rel)
    with open(p) as f:
        orig = f.read()
    n = orig.count(old)
    if n != 1:
        print(f"{name}: NOT APPLIED (the text occurs {n} times)", flush=True)
        continue
    try:
        with open(p, "w") as f:
            f.write(orig.replace(old, new))
        code, tail = run()
    finally:
        with open(p, "w") as f:
            f.write(orig)
    ok = code != 0
    killed += ok
    print(f"{name}: {'KILLED' if ok else 'SURVIVED'} | {tail}", flush=True)
print(f"{killed} of {len(MUT)} killed", flush=True)
code, tail = run()
print(f"AFTER (restored): exit {code} | {tail}", flush=True)
