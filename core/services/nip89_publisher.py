"""
nip89_publisher.py — NIP-89 (kind:31990) service discovery for Protocol Pulse.

Publishes machine-readable cards describing PP's paid APIs to Nostr so any
agent crawling the network can discover, price-compare and pay for access.
Events are signed with Schnorr (coincurve) per BIP-340 / NIP-01.

CLI:
    python3 nip89_publisher.py --generate-key      # emit a fresh Nostr keypair
    python3 nip89_publisher.py --publish           # publish all services

The privkey is read from $NOSTR_PRIVKEY_HEX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import ssl
import sys
import time
from typing import Dict, List, Tuple

import coincurve

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────

NOSTR_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.snort.social",
]

NOSTR_PRIVKEY_HEX = os.environ.get("NOSTR_PRIVKEY_HEX", "")

LIGHTNING_ADDRESS = os.environ.get("LIGHTNING_ADDRESS", "protocolpulse@getalby.com")
BASE_URL = os.environ.get("PP_BASE_URL", "https://protocolpulse.io")


PP_SERVICES: List[Dict] = [
    {
        "name": "Protocol Pulse · Live Signals",
        "description": (
            "Stream of the 10 latest BTC-relevant signals with Bitcoin-lens "
            "sentiment, narrative tags, and freshness metadata. Refreshed in "
            "real time from the Protocol Pulse intelligence engine."
        ),
        "endpoint": f"{BASE_URL}/v1/signals/live",
        "price_msats": 1000,
        "lightning_address": LIGHTNING_ADDRESS,
        "tags": ["bitcoin", "signals", "intelligence", "lsat"],
        "returns": "application/json",
    },
    {
        "name": "Protocol Pulse · Sovereign Orb",
        "description": (
            "Composite sovereign index (MCX miner conviction, EPX exchange "
            "pressure, IHX insider heat) plus live network streams — hashrate, "
            "fear/greed, mempool fees, exchange flow, KOL score."
        ),
        "endpoint": f"{BASE_URL}/api/orb",
        "price_msats": 100,
        "lightning_address": LIGHTNING_ADDRESS,
        "tags": ["bitcoin", "sovereign", "index", "lsat"],
        "returns": "application/json",
    },
    {
        "name": "Protocol Pulse · Signal Strength",
        "description": (
            "Composite Bitcoin signal score 0-100 combining narrative momentum, "
            "market posture, on-chain health, and sentiment. Includes dominant "
            "theme and BTC price snapshot."
        ),
        "endpoint": f"{BASE_URL}/api/intelligence/signal",
        "price_msats": 500,
        "lightning_address": LIGHTNING_ADDRESS,
        "tags": ["bitcoin", "signal", "sentiment", "lsat"],
        "returns": "application/json",
    },
]


# ── Keys ────────────────────────────────────────────────────────────────────

def generate_keypair() -> Tuple[str, str]:
    """Generate a fresh Nostr keypair. Returns (privkey_hex, x-only pubkey_hex)."""
    priv = coincurve.PrivateKey()
    privkey_hex = priv.secret.hex()
    # X-only pubkey: drop the leading byte (0x02/0x03) from the compressed form.
    pubkey_hex = priv.public_key.format(compressed=True)[1:].hex()
    return privkey_hex, pubkey_hex


def _xonly_pubkey(privkey_hex: str) -> str:
    priv = coincurve.PrivateKey(bytes.fromhex(privkey_hex))
    return priv.public_key.format(compressed=True)[1:].hex()


# ── Signing ─────────────────────────────────────────────────────────────────

def _schnorr_sign_event(event: dict, privkey_hex: str) -> dict:
    """
    Compute NIP-01 event id + Schnorr signature in place.

    Canonical form (array): [0, pubkey, created_at, kind, tags, content]
    The id is the sha256 hex of the JSON-serialised canonical form with no
    whitespace and UTF-8 escaping identical across implementations.
    """
    priv = coincurve.PrivateKey(bytes.fromhex(privkey_hex))
    pubkey_hex = priv.public_key.format(compressed=True)[1:].hex()

    canonical = json.dumps(
        [0, pubkey_hex, event["created_at"], event["kind"], event["tags"], event["content"]],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    sig = priv.sign_schnorr(bytes.fromhex(event_id)).hex()

    event["pubkey"] = pubkey_hex
    event["id"] = event_id
    event["sig"] = sig
    return event


# ── Event construction ─────────────────────────────────────────────────────

def build_nip89_event(service: dict, privkey_hex: str) -> dict:
    """Build a signed NIP-89 kind:31990 service handler event."""
    identifier = service["endpoint"]
    content = {
        "name": service["name"],
        "about": service["description"],
        "picture": f"{BASE_URL}/static/og-logo.png",
        "website": BASE_URL,
        "nip05": "protocolpulse@protocolpulse.io",
        "lud16": service["lightning_address"],
        "endpoint": service["endpoint"],
        "returns": service.get("returns", "application/json"),
        "pricing": {
            "amount_msats": service["price_msats"],
            "currency": "sats",
            "model": "per_call_lsat",
            "auth": "LSAT (RFC 9186) — Lightning Service Authentication Token",
        },
    }
    tags = [
        ["d", identifier],
        ["k", "lsat-api"],
        ["name", service["name"]],
        ["about", service["description"]],
        ["endpoint", service["endpoint"]],
        ["price", str(service["price_msats"]), "msat"],
        ["lud16", service["lightning_address"]],
    ]
    for t in service.get("tags", []):
        tags.append(["t", t])

    event = {
        "kind": 31990,
        "created_at": int(time.time()),
        "tags": tags,
        "content": json.dumps(content, separators=(",", ":"), ensure_ascii=False),
    }
    return _schnorr_sign_event(event, privkey_hex)


# ── Relay publishing ────────────────────────────────────────────────────────

def publish_to_relay(event: dict, relay_url: str, timeout: float = 8.0) -> Tuple[bool, str]:
    """
    Publish a signed event to a Nostr relay over WebSocket.

    Uses the `websocket-client` library if available (already a common dep of
    other PP services). Falls back to returning a clear error if not.
    """
    try:
        import websocket  # type: ignore
    except ImportError as exc:
        return False, f"websocket-client missing: {exc}"

    msg = json.dumps(["EVENT", event], separators=(",", ":"), ensure_ascii=False)
    ws = None
    try:
        ws = websocket.create_connection(
            relay_url,
            timeout=timeout,
            sslopt={"cert_reqs": ssl.CERT_NONE} if relay_url.startswith("wss://") else None,
        )
        ws.send(msg)
        try:
            reply = ws.recv()
        except Exception:
            reply = ""
        # Accept both OK and the no-reply case (some relays close silently).
        if reply:
            try:
                parsed = json.loads(reply)
                if isinstance(parsed, list) and parsed and parsed[0] == "OK":
                    return (bool(parsed[2]) if len(parsed) >= 3 else True), str(reply)
            except Exception:
                pass
            return True, str(reply)
        return True, "sent (no reply)"
    except Exception as exc:
        return False, str(exc)
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass


def publish_all_services(privkey_hex: str = "") -> dict:
    """
    Sign kind:31990 events for every PP service and broadcast to every relay.
    Returns aggregate stats + the signed events.
    """
    privkey_hex = privkey_hex or NOSTR_PRIVKEY_HEX
    if not privkey_hex:
        return {
            "published": 0,
            "failed": len(PP_SERVICES) * len(NOSTR_RELAYS),
            "events": [],
            "error": "NOSTR_PRIVKEY_HEX not set — run `python3 nip89_publisher.py --generate-key`",
        }

    events = [build_nip89_event(svc, privkey_hex) for svc in PP_SERVICES]
    published = 0
    failed = 0
    per_relay: Dict[str, Dict[str, int]] = {}
    event_summaries = []

    for event in events:
        summary = {"id": event["id"], "kind": event["kind"], "endpoint": None, "relays": {}}
        for tag in event["tags"]:
            if tag and tag[0] == "endpoint":
                summary["endpoint"] = tag[1] if len(tag) > 1 else None
                break
        for relay in NOSTR_RELAYS:
            ok, msg = publish_to_relay(event, relay)
            summary["relays"][relay] = {"ok": ok, "msg": msg[:140]}
            per_relay.setdefault(relay, {"ok": 0, "fail": 0})
            if ok:
                published += 1
                per_relay[relay]["ok"] += 1
            else:
                failed += 1
                per_relay[relay]["fail"] += 1
        event_summaries.append(summary)

    return {
        "published": published,
        "failed": failed,
        "relays": per_relay,
        "events": event_summaries,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def _cli() -> int:
    parser = argparse.ArgumentParser(description="NIP-89 Nostr publisher for Protocol Pulse")
    parser.add_argument("--generate-key", action="store_true", help="Print a fresh Nostr keypair and exit")
    parser.add_argument("--publish", action="store_true", help="Publish all PP services to configured relays")
    args = parser.parse_args()

    if args.generate_key:
        priv, pub = generate_keypair()
        print("Generated Nostr keypair — save the PRIVATE key securely.")
        print(f"NOSTR_PRIVKEY_HEX={priv}")
        print(f"NOSTR_PUBKEY_HEX={pub}")
        return 0

    if args.publish:
        priv = NOSTR_PRIVKEY_HEX
        if not priv:
            print("ERROR: NOSTR_PRIVKEY_HEX is not set.", file=sys.stderr)
            return 2
        result = publish_all_services(priv)
        print(json.dumps(result, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
