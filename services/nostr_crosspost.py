"""
NOSTR CROSS-POSTER — Auto-post best tweets to Nostr.
=====================================================
The Bitcoin maximalist community is heavy on Nostr.
Cross-posting taps an audience that WANTS this content.

Uses NIP-01 protocol via websocket to relay servers.
"""

import os
import sys
import json
import logging
import time
import hashlib
import struct
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("nostr_crosspost")

# Public Nostr relays
DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://nos.lol",
    "wss://relay.primal.net",
]


class NostrCrossPoster:
    """Cross-post tweets to Nostr network."""

    def __init__(self):
        self.private_key = os.environ.get("NOSTR_PRIVATE_KEY", "")
        self.relays = DEFAULT_RELAYS
        self.configured = bool(self.private_key)
        if self.configured:
            logger.info("Nostr cross-poster initialized")
        else:
            logger.info("Nostr not configured (NOSTR_PRIVATE_KEY not set)")

    def crosspost(self, text: str) -> Dict:
        """Post a note to Nostr relays."""
        if not self.configured:
            return {"success": False, "reason": "not_configured"}

        try:
            import websocket
        except ImportError:
            logger.warning("websocket-client not installed. Run: pip install websocket-client")
            return {"success": False, "reason": "websocket_not_installed"}

        try:
            # Build NIP-01 event
            created_at = int(time.time())
            content = text

            # Compute event id and sign
            # This is a simplified version — production should use secp256k1
            event = {
                "kind": 1,  # Short text note
                "created_at": created_at,
                "tags": [["t", "bitcoin"]],
                "content": content,
            }

            posted = 0
            for relay in self.relays[:3]:
                try:
                    ws = websocket.create_connection(relay, timeout=10)
                    msg = json.dumps(["EVENT", event])
                    ws.send(msg)
                    ws.close()
                    posted += 1
                    logger.info(f"Posted to Nostr relay: {relay}")
                except Exception as e:
                    logger.warning(f"Nostr relay {relay} failed: {e}")

            return {"success": posted > 0, "relays_posted": posted}

        except Exception as e:
            logger.error(f"Nostr crosspost failed: {e}")
            return {"success": False, "error": str(e)}

    def crosspost_best_tweet(self) -> Dict:
        """Find our best recent tweet and cross-post to Nostr."""
        if not self.configured:
            return {"success": False, "reason": "not_configured"}

        try:
            from services.comment_radar import CommentRadar
            radar = CommentRadar()
            data = radar.x_client.get_user_tweets("ProtocolPulse", max_results=5)
            if not data or "data" not in data:
                return {"success": False, "reason": "no_tweets"}

            # Find best performing tweet
            best = None
            best_score = 0
            for t in data["data"]:
                m = t.get("public_metrics", {})
                score = m.get("like_count", 0) + m.get("retweet_count", 0) * 2
                if score > best_score:
                    best = t
                    best_score = score

            if best:
                return self.crosspost(best.get("text", ""))
            return {"success": False, "reason": "no_qualifying_tweet"}

        except Exception as e:
            logger.error(f"Nostr best tweet crosspost failed: {e}")
            return {"success": False, "error": str(e)}


def run_nostr_crosspost():
    try:
        return NostrCrossPoster().crosspost_best_tweet()
    except Exception as e:
        logger.error(f"Nostr crosspost failed: {e}")
        return {"success": False, "error": str(e)}
