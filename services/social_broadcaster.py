#!/usr/bin/env python3
"""
Social Broadcaster — Unified multi-platform posting.
One call broadcasts to X, Nostr, and YouTube Community simultaneously.

Usage:
    from services.social_broadcaster import broadcast
    result = broadcast("Bitcoin just hit $100K. The denominator is zero.")
    # Returns: {"x": {"success": True, "id": "..."}, "nostr": {"success": True, ...}, "youtube": {"success": False, "error": "not_implemented"}}

Platforms:
    X       — via tweepy (OAuth 1.0a), same path as tweet_machine.post_to_x()
    Nostr   — via NIP-01 kind-1 text note (coincurve + bech32 + websocket)
    YouTube — NOT AVAILABLE. Google deprecated activities.insert (bulletin) in 2020.
              No programmatic API exists for YouTube Community posts as of 2026-04.
              Documented as TODO pending Google re-enabling the API or Puppeteer automation.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("social_broadcaster")

BASE = Path("/home/ultron/protocol_pulse")

# ── Env Loading ──────────────────────────────────────────────────────────────

def _load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── X (Twitter) ──────────────────────────────────────────────────────────────

def post_to_x(text: str) -> dict:
    """Post to X via tweepy OAuth 1.0a. Same credentials as tweet_machine."""
    api_key = os.environ.get("X_API_KEY", os.environ.get("X_CONSUMER_KEY", ""))
    api_secret = os.environ.get("X_API_SECRET", os.environ.get("X_CONSUMER_SECRET", ""))
    access_token = os.environ.get("X_ACCESS_TOKEN", "")
    access_secret = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        return {"success": False, "error": "x_credentials_missing"}

    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        logger.info(f"[X] Posted tweet {tweet_id}: {text[:60]}...")
        return {"success": True, "tweet_id": str(tweet_id)}
    except ImportError:
        return {"success": False, "error": "tweepy_not_installed"}
    except Exception as e:
        logger.error(f"[X] Post failed: {e}")
        return {"success": False, "error": str(e)}


# ── Nostr ────────────────────────────────────────────────────────────────────

DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.primal.net",
    "wss://nos.lol",
    "wss://relay.nostr.band",
]


def _decode_nostr_key(raw_key: str) -> bytes:
    """Decode nsec1... bech32 or raw hex private key to 32 bytes."""
    raw_key = (raw_key or "").strip()
    if not raw_key:
        raise ValueError("NOSTR_PRIVATE_KEY not set")
    if raw_key.startswith("nsec1"):
        from bech32 import bech32_decode, convertbits
        hrp, data = bech32_decode(raw_key)
        if hrp != "nsec" or not data:
            raise ValueError("Invalid nsec key")
        decoded = convertbits(data, 5, 8, False)
        if not decoded:
            raise ValueError("Failed nsec convertbits")
        return bytes(decoded)
    return bytes.fromhex(raw_key.lower().replace("0x", ""))


def _build_nostr_event(content: str) -> dict:
    """Build a signed NIP-01 kind-1 text note event."""
    from coincurve import PrivateKey

    key_bytes = _decode_nostr_key(os.environ.get("NOSTR_PRIVATE_KEY", ""))
    pk = PrivateKey(key_bytes)
    pubkey = pk.public_key.format(compressed=False)[1:].hex()
    created_at = int(time.time())

    event = {
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": 1,
        "tags": [],
        "content": content.strip(),
    }

    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    sig = pk.sign_schnorr(bytes.fromhex(event_id), aux_randomness=os.urandom(32)).hex()
    event["id"] = event_id
    event["sig"] = sig
    return event


def _get_relays() -> List[str]:
    """Get relay list from env or defaults."""
    raw = (os.environ.get("NOSTR_RELAYS") or "").strip()
    if raw:
        relays = [r.strip() for r in raw.split(",") if r.strip()]
        if relays:
            return relays
    return DEFAULT_RELAYS


def post_to_nostr(text: str) -> dict:
    """Post a kind-1 text note to Nostr relays."""
    import websocket

    try:
        event = _build_nostr_event(text)
    except Exception as e:
        logger.error(f"[Nostr] Event build failed: {e}")
        return {"success": False, "error": str(e), "relays_success": [], "relays_failed": []}

    relays_success: List[str] = []
    relays_failed: List[str] = []

    for relay in _get_relays():
        ws = None
        try:
            ws = websocket.create_connection(relay, timeout=8)
            ws.send(json.dumps(["EVENT", event], separators=(",", ":"), ensure_ascii=False))
            ws.settimeout(2)
            try:
                _ = ws.recv()
            except Exception:
                pass
            relays_success.append(relay)
        except Exception as e:
            relays_failed.append(f"{relay}::{e}")
        finally:
            try:
                if ws:
                    ws.close()
            except Exception:
                pass

    ok = len(relays_success) > 0
    if ok:
        logger.info(f"[Nostr] Published to {len(relays_success)} relays: {text[:60]}...")
    else:
        logger.warning(f"[Nostr] All relays failed: {relays_failed}")

    return {
        "success": ok,
        "event_id": event.get("id"),
        "relays_success": relays_success,
        "relays_failed": relays_failed,
    }


# ── YouTube Community ────────────────────────────────────────────────────────

def post_to_youtube(text: str) -> dict:
    """Post to YouTube Community tab.

    NOT IMPLEMENTED: Google deprecated the activities.insert (bulletin) API in 2020.
    No programmatic API for YouTube Community posts exists as of 2026-04.
    This is a placeholder that returns a clear status.
    """
    return {
        "success": False,
        "error": "not_implemented",
        "reason": "YouTube Community Posts API deprecated by Google (2020). No replacement exists.",
    }


# ── Unified Broadcast ────────────────────────────────────────────────────────

def broadcast(text: str, platforms: Optional[List[str]] = None) -> dict:
    """Broadcast text to all platforms (X + Nostr + YouTube).

    Args:
        text: The post content.
        platforms: Optional list of platforms to target. Defaults to all.
                   Valid values: "x", "nostr", "youtube"

    Returns:
        Dict with per-platform results:
        {"x": {...}, "nostr": {...}, "youtube": {...}}
    """
    if not text or not text.strip():
        return {
            "x": {"success": False, "error": "empty_text"},
            "nostr": {"success": False, "error": "empty_text"},
            "youtube": {"success": False, "error": "empty_text"},
        }

    text = text.strip()
    targets = set(platforms) if platforms else {"x", "nostr", "youtube"}
    results = {}

    # X
    if "x" in targets:
        try:
            results["x"] = post_to_x(text)
        except Exception as e:
            logger.error(f"[broadcast] X exception: {e}")
            results["x"] = {"success": False, "error": str(e)}
    else:
        results["x"] = {"success": False, "error": "skipped"}

    # Nostr
    if "nostr" in targets:
        try:
            results["nostr"] = post_to_nostr(text)
        except Exception as e:
            logger.error(f"[broadcast] Nostr exception: {e}")
            results["nostr"] = {"success": False, "error": str(e)}
    else:
        results["nostr"] = {"success": False, "error": "skipped"}

    # YouTube
    if "youtube" in targets:
        try:
            results["youtube"] = post_to_youtube(text)
        except Exception as e:
            logger.error(f"[broadcast] YouTube exception: {e}")
            results["youtube"] = {"success": False, "error": str(e)}
    else:
        results["youtube"] = {"success": False, "error": "skipped"}

    # Summary
    any_success = any(r.get("success") for r in results.values())
    logger.info(
        f"[broadcast] {'OK' if any_success else 'FAIL'} — "
        f"X:{results['x'].get('success')}, "
        f"Nostr:{results['nostr'].get('success')}, "
        f"YouTube:{results['youtube'].get('success')}"
    )

    return results


def broadcast_nostr(text: str) -> dict:
    """Convenience: broadcast to Nostr only."""
    return broadcast(text, platforms=["nostr"])


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Social Broadcaster — unified multi-platform posting")
    parser.add_argument("text", nargs="?", help="Text to broadcast (omit for dry-run import test)")
    parser.add_argument("--platforms", nargs="+", choices=["x", "nostr", "youtube"], help="Target platforms")
    parser.add_argument("--dry-run", action="store_true", help="Test import and config without posting")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[social_broadcaster] %(asctime)s %(levelname)s %(message)s")

    if args.dry_run or not args.text:
        print("=== Social Broadcaster Dry Run ===")
        print(f"post_to_x:     callable={callable(post_to_x)}")
        print(f"post_to_nostr: callable={callable(post_to_nostr)}")
        print(f"post_to_youtube: callable={callable(post_to_youtube)}")
        print(f"broadcast:     callable={callable(broadcast)}")

        # Check X credentials
        x_ok = all([
            os.environ.get("X_API_KEY") or os.environ.get("X_CONSUMER_KEY"),
            os.environ.get("X_API_SECRET") or os.environ.get("X_CONSUMER_SECRET"),
            os.environ.get("X_ACCESS_TOKEN"),
            os.environ.get("X_ACCESS_TOKEN_SECRET"),
        ])
        print(f"X credentials:  {'OK' if x_ok else 'MISSING'}")

        # Check Nostr key
        nostr_ok = bool(os.environ.get("NOSTR_PRIVATE_KEY"))
        print(f"Nostr key:      {'OK' if nostr_ok else 'MISSING'}")

        # YouTube
        print(f"YouTube:        NOT_AVAILABLE (API deprecated)")
        print("=== Done ===")
    else:
        result = broadcast(args.text, platforms=args.platforms)
        for platform, r in result.items():
            status = "OK" if r.get("success") else "FAIL"
            print(f"[{platform}] {status}: {r}")
