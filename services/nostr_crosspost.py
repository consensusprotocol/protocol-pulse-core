"""
NOSTR CROSS-POSTER — Auto-post best tweets to Nostr.
=====================================================
The Bitcoin maximalist community is heavy on Nostr.
Cross-posting taps an audience that WANTS this content.

NIP-01 events, properly signed (BIP-340 schnorr via coincurve),
published over websocket with relay OK verification.

Reads our best recent post via services.x_reader (x_search) with the
legacy X API path as fallback. Dedupes via data/nostr_crossposted.json.
"""

import os
import sys
import json
import logging
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("nostr_crosspost")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PP_HANDLE = "ProtocolPulseHQ"
DEDUP_FILE = "data/nostr_crossposted.json"

# Public Nostr relays
DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://nos.lol",
    "wss://relay.primal.net",
]

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _decode_nsec(nsec: str) -> Optional[bytes]:
    """bech32 nsec1... -> 32-byte private key, or None."""
    if not nsec or not nsec.lower().startswith("nsec1"):
        # allow raw 64-char hex too
        try:
            b = bytes.fromhex(nsec)
            return b if len(b) == 32 else None
        except (ValueError, TypeError):
            return None
    body = nsec.lower()[5:]
    vals = [_BECH32_CHARSET.find(c) for c in body]
    if -1 in vals or len(vals) <= 6:
        return None
    vals = vals[:-6]  # strip checksum
    acc, bits, out = 0, 0, bytearray()
    for v in vals:
        acc = (acc << 5) | v
        bits += 5
        while bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return bytes(out) if len(out) == 32 else None


def _sign_event(seckey: bytes, kind: int, tags: List, content: str) -> Optional[Dict]:
    """Build and BIP-340-sign a NIP-01 event. Returns full event dict."""
    try:
        import coincurve
    except ImportError:
        logger.warning("coincurve not installed — cannot sign Nostr events")
        return None
    sk = coincurve.PrivateKey(seckey)
    pubkey = sk.public_key.format(compressed=True)[1:].hex()  # x-only
    created_at = int(time.time())
    ser = json.dumps([0, pubkey, created_at, kind, tags, content],
                     separators=(",", ":"), ensure_ascii=False)
    event_id = hashlib.sha256(ser.encode()).hexdigest()
    sig = sk.sign_schnorr(bytes.fromhex(event_id)).hex()
    return {
        "id": event_id,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig,
    }


class NostrCrossPoster:
    """Cross-post tweets to Nostr network."""

    def __init__(self):
        raw = os.environ.get("NOSTR_PRIVATE_KEY", "")
        self.seckey = _decode_nsec(raw)
        self.relays = DEFAULT_RELAYS
        self.configured = bool(self.seckey)
        if self.configured:
            logger.info("Nostr cross-poster initialized (key decoded)")
        elif raw:
            logger.warning("NOSTR_PRIVATE_KEY set but could not be decoded")
        else:
            logger.info("Nostr not configured (NOSTR_PRIVATE_KEY not set)")

    def crosspost(self, text: str) -> Dict:
        """Sign and publish a kind-1 note; verify relay OK responses."""
        if not self.configured:
            return {"success": False, "reason": "not_configured"}
        try:
            import websocket
        except ImportError:
            logger.warning("websocket-client not installed")
            return {"success": False, "reason": "websocket_not_installed"}

        event = _sign_event(self.seckey, 1, [["t", "bitcoin"]], text)
        if not event:
            return {"success": False, "reason": "signing_failed"}

        accepted, attempted = 0, 0
        for relay in self.relays[:3]:
            attempted += 1
            for attempt in range(2):
                try:
                    ws = websocket.create_connection(relay, timeout=10)
                    ws.send(json.dumps(["EVENT", event]))
                    ws.settimeout(6)
                    ok = False
                    try:
                        resp = json.loads(ws.recv())
                        # ["OK", <event_id>, <true|false>, <message>]
                        if (isinstance(resp, list) and len(resp) >= 3
                                and resp[0] == "OK"
                                and resp[1] == event["id"] and resp[2]):
                            ok = True
                        elif isinstance(resp, list) and resp[0] == "OK":
                            logger.warning("Relay %s rejected: %s", relay,
                                           resp[3] if len(resp) > 3 else "?")
                    except Exception:
                        pass  # no OK frame — treat as unconfirmed
                    ws.close()
                    if ok:
                        accepted += 1
                        logger.info("Nostr relay ACCEPTED event: %s", relay)
                    break
                except Exception as e:
                    if attempt == 1:
                        logger.warning("Nostr relay %s failed: %s", relay, e)
                    else:
                        time.sleep(2)
        return {"success": accepted > 0, "relays_accepted": accepted,
                "relays_attempted": attempted, "event_id": event["id"]}

    # ------------------------------------------------------------- dedup
    def _already_posted(self, post_id: str) -> bool:
        try:
            if os.path.exists(DEDUP_FILE):
                return post_id in json.load(open(DEDUP_FILE)).get("posted", [])
        except Exception:
            pass
        return False

    def _record_posted(self, post_id: str, event_id: str):
        os.makedirs("data", exist_ok=True)
        try:
            log = (json.load(open(DEDUP_FILE))
                   if os.path.exists(DEDUP_FILE) else {"posted": [], "history": []})
        except Exception:
            log = {"posted": [], "history": []}
        log["posted"] = (log.get("posted", []) + [post_id])[-300:]
        log.setdefault("history", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "post_id": post_id, "event_id": event_id})
        log["history"] = log["history"][-100:]
        json.dump(log, open(DEDUP_FILE, "w"), indent=2)

    # ------------------------------------------------------------ reads
    def _best_recent_post(self) -> Optional[Dict]:
        """Our best recent post: x_reader primary, legacy X API fallback."""
        try:
            try:
                from services import x_reader
            except ImportError:
                import x_reader
            posts = x_reader.get_top_posts([PP_HANDLE], hours=48, limit=5)
            fresh = [p for p in posts if not self._already_posted(p["post_id"])]
            if fresh:
                return {"id": fresh[0]["post_id"], "text": fresh[0]["text"]}
            if posts:
                logger.info("All recent posts already crossposted")
                return None
        except Exception as e:
            logger.warning("x_reader read failed: %s — trying legacy API", e)

        try:
            from services.comment_radar import CommentRadar
            radar = CommentRadar()
            data = radar.x_client.get_user_tweets(PP_HANDLE, max_results=5)
            if not data or "data" not in data:
                return None
            best, best_score = None, 0
            for t in data["data"]:
                m = t.get("public_metrics", {})
                score = m.get("like_count", 0) + m.get("retweet_count", 0) * 2
                if score > best_score and not self._already_posted(t["id"]):
                    best, best_score = t, score
            if best:
                return {"id": best["id"], "text": best.get("text", "")}
        except Exception as e:
            logger.error("Legacy read failed: %s", e)
        return None

    def crosspost_best_tweet(self) -> Dict:
        """Find our best recent tweet and cross-post to Nostr."""
        if not self.configured:
            return {"success": False, "reason": "not_configured"}
        post = self._best_recent_post()
        if not post or not post.get("text"):
            return {"success": False, "reason": "no_qualifying_tweet"}
        result = self.crosspost(post["text"])
        if result.get("success"):
            self._record_posted(post["id"], result.get("event_id", ""))
        return result


def run_nostr_crosspost():
    try:
        return NostrCrossPoster().crosspost_best_tweet()
    except Exception as e:
        logger.error(f"Nostr crosspost failed: {e}")
        return {"success": False, "error": str(e)}
