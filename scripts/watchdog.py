#!/usr/bin/env python3
"""
Protocol Pulse watchdog:
- runs self_check
- emits RED/GREEN heartbeat line to pulse_events.jsonl
- auto-restarts mapped services when failed
- prevents restart loops with cooldown + max retries
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELF_CHECK = PROJECT_ROOT / "scripts" / "self_check.py"
EVENTS_PATH = PROJECT_ROOT / "data" / "pulse_events.jsonl"
STATE_PATH = PROJECT_ROOT / "logs" / "watchdog_state.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_event(severity: str, title: str, detail: str, meta: dict | None = None) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": _iso_now(),
        "lane": "system",
        "severity": severity,
        "title": title,
        "detail": detail,
        "meta": meta or {},
        "tag": "watchdog",
    }
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"services": {}, "last_run": None}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _run_self_check(timeout_sec: int = 420) -> tuple[int, str]:
    cmd = [str(PROJECT_ROOT / "venv" / "bin" / "python"), str(SELF_CHECK)]
    env = os.environ.copy()
    env.setdefault("SELF_CHECK_BASE_URL", "http://127.0.0.1:5000")
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True, timeout=timeout_sec)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output


def _choose_service(failure_output: str) -> str:
    text = (failure_output or "").lower()
    if "gate d (whale watcher)" in text or "gate e (x-sentry dry)" in text or "gate c (streaming)" in text:
        return "pulse_intel.service"
    if "gate g (medley smoke)" in text:
        return "pulse_medley.service"
    return "pulse_web.service"


def _restart_service(service: str) -> tuple[bool, str]:
    # Try user unit first, then system-level.
    user_cmd = ["systemctl", "--user", "restart", service]
    proc = subprocess.run(user_cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, "user"
    sys_cmd = ["systemctl", "restart", service]
    proc2 = subprocess.run(sys_cmd, capture_output=True, text=True)
    if proc2.returncode == 0:
        return True, "system"
    msg = f"user_err={(proc.stderr or '').strip()[:160]} system_err={(proc2.stderr or '').strip()[:160]}"
    return False, msg


def run_once(cooldown_sec: int, max_retries: int) -> int:
    state = _load_state()
    state["last_run"] = _iso_now()
    now = int(time.time())

    rc, out = _run_self_check()
    if rc == 0:
        _append_event("info", "WATCHDOG GREEN", "self_check passed; no restart required")
        print("WATCHDOG: GREEN")
        _save_state(state)
        return 0

    service = _choose_service(out)
    svc_state = state.setdefault("services", {}).setdefault(service, {"retries": 0, "last_restart_epoch": 0})
    since_last = now - int(svc_state.get("last_restart_epoch", 0) or 0)

    if svc_state.get("retries", 0) >= max_retries and since_last < cooldown_sec:
        detail = f"self_check failed; restart blocked by cooldown/max_retries service={service}"
        _append_event("crit", "WATCHDOG RED (blocked)", detail, {"service": service, "retries": svc_state.get("retries", 0)})
        print("WATCHDOG: RED (restart blocked)")
        _save_state(state)
        return 1

    if since_last < cooldown_sec:
        detail = f"self_check failed; cooldown active ({cooldown_sec - since_last}s) service={service}"
        _append_event("warn", "WATCHDOG RED (cooldown)", detail, {"service": service})
        print("WATCHDOG: RED (cooldown active)")
        _save_state(state)
        return 1

    ok, mode = _restart_service(service)
    if ok:
        svc_state["retries"] = int(svc_state.get("retries", 0)) + 1
        svc_state["last_restart_epoch"] = now
        _append_event("warn", "WATCHDOG RED -> RESTART", f"self_check failed; restarted {service}", {"service": service, "mode": mode})
        print(f"WATCHDOG: RED -> restarted {service} ({mode})")
    else:
        _append_event("crit", "WATCHDOG RED (restart failed)", f"failed restarting {service}: {mode}", {"service": service})
        print(f"WATCHDOG: RED (restart failed for {service})")
    _save_state(state)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cooldown-sec", type=int, default=900)
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()
    return run_once(cooldown_sec=args.cooldown_sec, max_retries=args.max_retries)


if __name__ == "__main__":
    raise SystemExit(main())

