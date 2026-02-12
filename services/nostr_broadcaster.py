"""
Compatibility Nostr broadcaster wrapper used by admin routes.
"""

from __future__ import annotations

from services.distribution_manager import distribution_manager


class NostrBroadcaster:
    def get_relay_status(self):
        relays = distribution_manager._nostr_relays()  # compatibility helper
        return {
            "configured": bool(relays),
            "relays": relays,
            "relay_count": len(relays),
        }

    def broadcast_note(self, content: str):
        return distribution_manager._nostr_publish(content)

    def test_connection(self):
        return self.broadcast_note("protocol pulse nostr test ping")


nostr_broadcaster = NostrBroadcaster()

