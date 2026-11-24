"""Ruling 133 R16: a heartbeat for every kept-alive service, read by tools/session_watchdog.py.

Each service writes <DIR>/<service>.json: {service, pid, at, pass_at, passes, info}.
- `at` is the process's last sign of life. start() refreshes it every BEAT_S from a daemon thread, so a long lease wait
  or a render's 50 minutes never reads as death. A process that exits or is frozen stops beating.
- `pass_at` is the end of the service's last loop pass (mark_pass). A process that beats but finishes no pass for
  PASS_STALE_S is stuck in a pass.
A heartbeat never stops its service: a failed write is printed once and the service goes on.
"""
import json
import os
import threading
import time

DIR = os.environ.get("PP_HEARTBEAT_DIR", "/tmp/pulse_heartbeats")
BEAT_S = 60
STALE_S = 20 * 60          # R16: a heartbeat older than 20 minutes is a Telegram line
PASS_STALE_S = 90 * 60     # alive, but no finished pass: longer than a render (about 50 min) plus a lease wait

_state = {}                # service -> {"pass_at", "passes", "info"} of this process
_lock = threading.Lock()
_warned = set()


def path(service):
    return os.path.join(DIR, f"{service}.json")


def _write(service, now=None):
    with _lock:
        s = _state.setdefault(service, {"pass_at": None, "passes": 0, "info": {}})
        rec = {"service": service, "pid": os.getpid(), "at": time.time() if now is None else now, **s}
    try:
        os.makedirs(DIR, exist_ok=True)
        tmp = f"{path(service)}.tmp{os.getpid()}.{threading.get_ident()}"
        with open(tmp, "w") as f:
            json.dump(rec, f, default=str)
        os.replace(tmp, path(service))
    except OSError as e:
        if service not in _warned:
            _warned.add(service)
            print(f"heartbeat {service}: cannot write {path(service)}: {e} (the service goes on)", flush=True)
    return rec


def mark_pass(service, now=None, **info):
    """The end of one loop pass: pass_at, the pass count and this pass's info, written at once."""
    t = time.time() if now is None else now
    with _lock:
        s = _state.setdefault(service, {"pass_at": None, "passes": 0, "info": {}})
        s.update(pass_at=t, passes=s["passes"] + 1, info=info)
    return _write(service, now=t)


def start(service, beat_s=BEAT_S, stop=None):
    """Write now, then every beat_s from a daemon thread while the process lives (or until `stop`, an Event, is set)."""
    _write(service)
    stop = stop or threading.Event()

    def loop():
        while not stop.wait(beat_s):
            _write(service)
    t = threading.Thread(target=loop, name=f"heartbeat-{service}", daemon=True)
    t.start()
    return t


def read(service):
    """The service's last record, or None (missing or unreadable)."""
    try:
        with open(path(service)) as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) else None
    except (OSError, ValueError):
        return None
