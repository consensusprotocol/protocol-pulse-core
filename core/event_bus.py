from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

EVENTS_PATH = Path("/home/ultron/protocol_pulse/data/pulse_events.jsonl")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit_event(
    event_type: str,
    source: str,
    payload: Dict | None = None,
    *,
    lane: str = "system",
    severity: str = "info",
    title: str | None = None,
    detail: str | None = None,
) -> Dict:
    """Append a normalized event line to pulse_events.jsonl."""
    row = {
        "ts": _iso_now(),
        "type": str(event_type or "event"),
        "source": str(source or "unknown"),
        "lane": str(lane or "system"),
        "severity": str(severity or "info"),
        "title": str(title or event_type or "event"),
        "detail": str(detail or ""),
        "payload": payload or {},
    }
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")
    return row


def read_events(limit: int = 100, lane: str | None = None) -> List[Dict]:
    if not EVENTS_PATH.exists():
        return []
    lines = EVENTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: List[Dict] = []
    for raw in reversed(lines):
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if lane and str(row.get("lane") or "") != lane:
            continue
        out.append(row)
        if len(out) >= max(1, int(limit)):
            break
    return list(reversed(out))


def iter_events_since(offset: int = 0) -> tuple[int, Iterable[Dict]]:
    """Return new events after byte offset with the new tail offset."""
    if not EVENTS_PATH.exists():
        return 0, []
    with EVENTS_PATH.open("r", encoding="utf-8", errors="ignore") as f:
        f.seek(offset)
        chunk = f.read()
        new_offset = f.tell()
    rows: List[Dict] = []
    for line in (chunk or "").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return new_offset, rows

