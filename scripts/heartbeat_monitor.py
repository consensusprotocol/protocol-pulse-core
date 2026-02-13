#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path("/home/ultron/protocol_pulse")
HEALING_PATH = PROJECT_ROOT / "data" / "healing_logs.json"
HEALTH_URL = "http://127.0.0.1:5000/health"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_rows():
    if HEALING_PATH.exists():
        try:
            data = json.loads(HEALING_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _write_rows(rows):
    HEALING_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALING_PATH.write_text(json.dumps(rows[-2000:], ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _service_active(name: str) -> bool:
    for cmd in (["systemctl", "is-active", name], ["systemctl", "--user", "is-active", name]):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if (p.stdout or "").strip() == "active":
                return True
        except Exception:
            continue
    return False


def _restart_pulse() -> tuple[bool, str]:
    cmds = [
        ["sudo", "systemctl", "restart", "pulse.service"],
        ["sudo", "systemctl", "restart", "pulse_web.service"],
        ["systemctl", "--user", "restart", "pulse_web.service"],
    ]
    errs = []
    for cmd in cmds:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if p.returncode == 0:
                return True, " ".join(cmd)
            errs.append(((p.stderr or "")[:120] or (p.stdout or "")[:120] or f"rc={p.returncode}").strip())
        except Exception as e:
            errs.append(str(e)[:120])
    return False, " | ".join(errs)


def main() -> int:
    now = _iso_now()
    event = {"ts": now, "status": "ok", "action": "none", "detail": ""}
    healthy = False
    try:
        r = requests.get(HEALTH_URL, timeout=8)
        healthy = r.status_code == 200
    except Exception as e:
        event["detail"] = f"health probe error: {e}"

    pulse_up = _service_active("pulse.service") or _service_active("pulse_web.service")
    if healthy and pulse_up:
        event["detail"] = "pulse healthy"
    else:
        ok, meta = _restart_pulse()
        event["status"] = "healed" if ok else "failed"
        event["action"] = "restart pulse"
        event["detail"] = meta

    rows = _read_rows()
    rows.append(event)
    _write_rows(rows)
    print(json.dumps(event, ensure_ascii=True))
    return 0 if event["status"] in ("ok", "healed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

