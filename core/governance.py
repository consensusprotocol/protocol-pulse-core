from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

USAGE_PATH = Path("/home/ultron/protocol_pulse/logs/governance_usage.json")
DEFAULT_CAPS = {
    "sentry_generation": 800,
    "onboarding_ai": 600,
    "medley_render": 6,
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> Dict:
    if USAGE_PATH.exists():
        try:
            return json.loads(USAGE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"day": _today(), "usage": {}}


def _save(data: Dict) -> None:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    USAGE_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def check_and_consume(lane: str, units: int = 1) -> Dict:
    data = _load()
    if data.get("day") != _today():
        data = {"day": _today(), "usage": {}}
    usage = data.setdefault("usage", {})
    current = int(usage.get(lane, 0))
    cap = int(DEFAULT_CAPS.get(lane, 1000))
    if current + units > cap:
        return {"ok": False, "lane": lane, "used": current, "cap": cap, "remaining": max(0, cap - current)}
    usage[lane] = current + units
    _save(data)
    return {"ok": True, "lane": lane, "used": usage[lane], "cap": cap, "remaining": max(0, cap - usage[lane])}


def get_metrics() -> Dict:
    data = _load()
    usage = data.get("usage") or {}
    return {
        "day": data.get("day"),
        "lanes": {k: {"used": int(usage.get(k, 0)), "cap": int(DEFAULT_CAPS.get(k, 1000))} for k in DEFAULT_CAPS.keys()},
    }

