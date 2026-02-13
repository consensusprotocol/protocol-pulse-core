from __future__ import annotations

import json
import os
from typing import Dict, List

import requests

from services.nostr_broadcaster import nostr_broadcaster


class GlobalRelayService:
    """Broadcast finalized Pulse Drop summaries to Nostr + Discord."""

    def __init__(self) -> None:
        self.discord_webhook = (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()

    def _build_summary(self, reel_link: str, segments: List[dict]) -> str:
        top = segments[:3]
        bullets = []
        for s in top:
            label = str(s.get("label") or "alpha segment")[:100]
            start = int(s.get("start_sec") or 0)
            bullets.append(f"- t+{start}s {label}")
        bullets_txt = "\n".join(bullets) if bullets else "- no segment metadata"
        return (
            "pulse drop finalized.\n"
            f"live link: {reel_link}\n"
            "narrative brief:\n"
            f"{bullets_txt}\n"
            "operator action: review mission log and execute on confirmed edge."
        )

    def _post_discord(self, text: str) -> Dict:
        if not self.discord_webhook:
            return {"ok": False, "error": "discord_webhook_missing"}
        try:
            r = requests.post(self.discord_webhook, json={"content": text[:1900]}, timeout=20)
            return {"ok": r.status_code < 300, "status": r.status_code, "body": (r.text or "")[:300]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def broadcast_pulse_drop(self, reel_link: str, segments: List[dict]) -> Dict:
        text = self._build_summary(reel_link=reel_link, segments=segments)
        nostr = nostr_broadcaster.broadcast_note(text)
        discord = self._post_discord(text)
        return {
            "ok": bool((nostr or {}).get("success")) or bool((discord or {}).get("ok")),
            "nostr": nostr,
            "discord": discord,
            "message_preview": text[:240],
        }


global_relay_service = GlobalRelayService()

