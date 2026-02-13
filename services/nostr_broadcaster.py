"""
Compatibility Nostr broadcaster wrapper used by admin routes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from services.distribution_manager import distribution_manager


class NostrBroadcaster:
    def __init__(self) -> None:
        self.queue_path = Path("/home/ultron/protocol_pulse/logs/nostr_retry_queue.json")

    def _load_queue(self):
        try:
            if self.queue_path.exists():
                data = json.loads(self.queue_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _save_queue(self, rows):
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue_path.write_text(json.dumps(rows, ensure_ascii=True, indent=2), encoding="utf-8")

    def get_relay_status(self):
        relays = distribution_manager._nostr_relays()  # compatibility helper
        queued = len(self._load_queue())
        return {
            "configured": bool(relays),
            "relays": relays,
            "relay_count": len(relays),
            "retry_queue_depth": queued,
        }

    def broadcast_note(self, content: str):
        result = distribution_manager._nostr_publish(content)
        err = str(result.get("error") or "").lower()
        should_queue = (not result.get("success")) and ("disabled" not in err) and ("missing" not in err)
        if should_queue:
            queue = self._load_queue()
            queue.append(
                {
                    "content": (content or "")[:4000],
                    "created_at": datetime.utcnow().isoformat(),
                    "attempts": int(result.get("attempts", 0)) + 1,
                    "next_retry_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
                    "last_error": str(result.get("error") or "relay_publish_failed"),
                }
            )
            self._save_queue(queue[-1000:])
        return result

    def test_connection(self):
        return self.broadcast_note("protocol pulse nostr test ping")

    def retry_pending(self):
        queue = self._load_queue()
        if not queue:
            return {"retried": 0, "successes": 0, "remaining": 0}
        now = datetime.utcnow()
        kept = []
        retried = 0
        successes = 0
        for row in queue:
            nra = str(row.get("next_retry_at") or "")
            should_retry = True
            if nra:
                try:
                    should_retry = datetime.fromisoformat(nra) <= now
                except Exception:
                    should_retry = True
            if not should_retry:
                kept.append(row)
                continue
            retried += 1
            result = distribution_manager._nostr_publish(str(row.get("content") or ""))
            if result.get("success"):
                successes += 1
                continue
            attempts = int(row.get("attempts") or 0) + 1
            row["attempts"] = attempts
            row["last_error"] = str(result.get("error") or "relay_publish_failed")
            row["next_retry_at"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            kept.append(row)
        self._save_queue(kept[-1000:])
        return {"retried": retried, "successes": successes, "remaining": len(kept)}


nostr_broadcaster = NostrBroadcaster()

