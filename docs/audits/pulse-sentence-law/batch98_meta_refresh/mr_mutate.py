#!/usr/bin/env python3
"""Batch 98 mutations: each must make the suites fail; the unmutated control must pass first.
Usage: python3 gt_mutate.py WORKTREE NETGUARD_DIR"""
import os
import subprocess
import sys

W, NG = sys.argv[1], sys.argv[2]
TS = "pipeline/transcript_store.py"
TESTS = ["pipeline/test_transcript_store_live.py", "pipeline/test_transcript_ingest.py"]
MUT = [
    ("R1 no re-read of a stored live record", TS, '    if meta.get("live_status") in LIVE_STATES:', '    if False:'),
    ("R2 the re-read interval ignored", TS,
     "    if last is not None and (time.time() if now is None else now) - last < META_RECHECK_S:", "    if False:"),
    ("R3 ensure_meta returns meta.json, not the newest snapshot", TS, "        return _newest_meta(video_id)",
     "        return json.load(open(path))"),
    ("R4 the snapshot not appended to the history", TS,
     '        f.write(json.dumps(fresh, ensure_ascii=False) + "\\n")', "        pass"),
    ("R5 a torn history line breaks the read", TS, "                except ValueError:\n                    continue",
     "                except KeyError:\n                    continue"),
    ("R6 another video's snapshot accepted", TS,
     '                if not (isinstance(snap, dict) and snap.get("video_id") == video_id):',
     "                if not isinstance(snap, dict):"),
    ("R7 a failed re-read crashes the acquisition", TS, "        except AcquisitionError:\n            pass",
     "        except KeyError:\n            pass"),
    ("R8 post_live now skipped", TS, 'SKIP_LIVE = ("is_live", "is_upcoming")', "SKIP_LIVE = LIVE_STATES"),
    ("R9 only is_live read again", TS, 'LIVE_STATES = ("is_live", "is_upcoming", "post_live")',
     'LIVE_STATES = ("is_live",)'),
    ("R10 a hung yt-dlp not turned into an AcquisitionError", TS,
     "    except (subprocess.TimeoutExpired, OSError) as e:", "    except KeyError as e:"),
    ("R11 the last line wins, not the latest read", TS,
     "                if at is not None and (best is None or at >= best):", "                if True:"),
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
