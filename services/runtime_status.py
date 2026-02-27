"""
Lightweight runtime status store for health reporting and self-check gates.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

STATUS_PATH = Path("/home/ultron/protocol_pulse/logs/runtime_status.json")


def _load() -> Dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def update_status(section: str, payload: Dict[str, Any]) -> None:
    current = _load()
    current[section] = payload
    current["updated_at"] = datetime.utcnow().isoformat()
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(current, ensure_ascii=True, indent=2), encoding="utf-8")


def get_status() -> Dict[str, Any]:
    return _load()

