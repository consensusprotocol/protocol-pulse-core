from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from core.event_bus import read_events


class NarrativeMemory:
    def __init__(self, window_hours: int = 24) -> None:
        self.window_hours = window_hours

    def _in_window(self, ts: str) -> bool:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt >= (datetime.utcnow().astimezone(dt.tzinfo) - timedelta(hours=self.window_hours))
        except Exception:
            return True

    def get_recent_by_type(self, event_type: str, limit: int = 20) -> List[Dict]:
        rows = [r for r in read_events(limit=500) if str(r.get("type") or "") == event_type and self._in_window(str(r.get("ts") or ""))]
        return rows[-limit:]

    def search_events(self, keyword: str, limit: int = 20) -> List[Dict]:
        q = (keyword or "").strip().lower()
        if not q:
            return []
        rows = []
        for r in read_events(limit=800):
            text = " ".join(
                [
                    str(r.get("title") or ""),
                    str(r.get("detail") or ""),
                    str(r.get("type") or ""),
                    str(r.get("source") or ""),
                ]
            ).lower()
            if q in text and self._in_window(str(r.get("ts") or "")):
                rows.append(r)
        return rows[-limit:]


narrative_memory = NarrativeMemory()

