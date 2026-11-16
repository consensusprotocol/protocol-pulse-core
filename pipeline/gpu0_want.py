#!/usr/bin/env python3
"""pipeline/gpu0_want.py: a build's GPU0 service says it wants the card, so the transcript ingest's Whisper gives it
back at its next file boundary.

Orchestrator order '13:05' ET Nov 16 (pp-ingest's request R13). The scorer server leases GPU0 only for its scoring
work, and Whisper runs between those calls. Builds and renders keep priority over Whisper: a transcription yields at
the next file boundary when a render asks (local_judge.YIELD_FLAG, unchanged) or when a build's service wants GPU0
(this module).

Each service keeps its own file, DIR/<service>.json, while it has GPU work waiting:
- want() touches the file on every pass;
- done() removes it when the service's queue is empty;
- the file of a service that died goes stale after FRESH_S, so it never holds Whisper back for long.

Nothing here touches the GPU or the lease. This is no lease of its own: gpu0.py's lease stays the one owner rule
(law L-r), and the want only orders who asks next."""
import json
import os
import re
import time

DIR = os.environ.get("PP_GPU0_WANT_DIR", "/tmp/pulse_gpu0.want")
FRESH_S = 90.0                     # a want counts while touched within this many seconds (the services poll every 5-10 s)
NAME = re.compile(r"^[a-z0-9_]{1,40}$")


def _path(service):
    if not NAME.match(service or ""):
        raise ValueError(f"not a service name: {service!r}")
    return os.path.join(DIR, f"{service}.json")


def want(service, now=None):
    """`service` has GPU0 work waiting (touch its file, atomically)."""
    p = _path(service)
    os.makedirs(DIR, exist_ok=True)
    tmp = f"{p}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump({"service": service, "pid": os.getpid(), "at": time.time() if now is None else now}, f)
    os.replace(tmp, p)


def done(service):
    """`service` has no GPU0 work waiting."""
    try:
        os.remove(_path(service))
    except FileNotFoundError:
        pass


def wanted(now=None):
    """The services whose want is fresh (touched within FRESH_S), sorted; [] when none."""
    now = time.time() if now is None else now
    out = []
    try:
        names = sorted(os.listdir(DIR))
    except FileNotFoundError:
        return out
    for name in names:
        if not name.endswith(".json") or not NAME.match(name[:-5]):
            continue
        try:
            if now - os.path.getmtime(os.path.join(DIR, name)) <= FRESH_S:
                out.append(name[:-5])
        except OSError:                                  # removed while listed
            continue
    return out
