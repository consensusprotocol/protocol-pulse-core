import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://nos.lol",
    "wss://relay.snort.social"
]

_nostr_cache = {}
_cache_timestamp = 0
CACHE_DURATION = 120


def load_nostr_allowlist():
    try:
        with open('data/supported_sources.json', 'r') as f:
            data = json.load(f)
            return data.get('nostr_allowlist', [])
    except Exception as e:
        logger.error(f"Failed to load nostr allowlist: {e}")
        return []


def verify_nip05(nip05: str, pubkey: str) -> bool:
    if not nip05 or '@' not in nip05 or not pubkey:
        return False
    
    try:
        name, domain = nip05.split('@', 1)
        url = f"https://{domain}/.well-known/nostr.json?name={name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            names = data.get('names', {})
            if name in names:
                resolved_pubkey = names[name]
                if resolved_pubkey and pubkey:
                    npub_hex = pubkey.replace('npub1', '') if pubkey.startswith('npub1') else pubkey
                    resolved_hex = resolved_pubkey.replace('npub1', '') if resolved_pubkey.startswith('npub1') else resolved_pubkey
                    if npub_hex.lower() == resolved_hex.lower():
                        return True
                    if len(npub_hex) > 10 and len(resolved_hex) > 10:
                        if npub_hex[:10].lower() == resolved_hex[:10].lower():
                            logger.debug(f"NIP-05 partial match for {nip05}")
                            return True
    except Exception as e:
        logger.debug(f"NIP-05 verification failed for {nip05}: {e}")
    
    return False


def fetch_notes_from_relay(relay_url: str, pubkeys: List[str], limit: int = 20) -> List[Dict]:
    logger.info(f"Note: Nostr relay fetch is stubbed - would connect to {relay_url}")
    return []


def get_allowlist_notes(limit: int = 50) -> List[Dict]:
    global _nostr_cache, _cache_timestamp
    
    if _nostr_cache and (time.time() - _cache_timestamp) < CACHE_DURATION:
        return _nostr_cache.get('notes', [])[:limit]
    
    allowlist = load_nostr_allowlist()
    if not allowlist:
        return []
    
    notes = []
    for entry in allowlist:
        is_verified = verify_nip05(entry.get('nip05'), entry.get('pubkey'))
        
        notes.append({
            'source': entry['name'],
            'pubkey': entry.get('pubkey', ''),
            'nip05': entry.get('nip05'),
            'tier': entry.get('tier', 'macro'),
            'verified': is_verified,
            'platform_icon': 'fa-bolt',
            'note': f"[Nostr feed from {entry['name']} - real-time ingestion requires relay connection]",
            'created_at': datetime.utcnow().isoformat()
        })
    
    _nostr_cache = {'notes': notes}
    _cache_timestamp = time.time()
    
    return notes[:limit]


def ingest_nostr_notes():
    from app import app, db
    from models import FeedItem
    
    allowlist = load_nostr_allowlist()
    if not allowlist:
        logger.info("No Nostr allowlist configured")
        return 0
    
    logger.info(f"Nostr ingestion: {len(allowlist)} allowlisted accounts configured")
    logger.info("Note: Full Nostr relay integration requires websocket client (nostr-sdk)")
    
    return 0


def get_verified_sources() -> List[Dict]:
    allowlist = load_nostr_allowlist()
    verified = []
    
    for entry in allowlist:
        is_verified = verify_nip05(entry.get('nip05'), entry.get('pubkey'))
        verified.append({
            'name': entry['name'],
            'nip05': entry.get('nip05'),
            'tier': entry.get('tier'),
            'verified': is_verified
        })
    
    return verified


def post_to_nostr(content: str, tags: list = None) -> dict:
    """Post a note to Nostr relays"""
    import os
    import json
    import time
    import hashlib
    import secp256k1
    import websocket
    
    private_key_raw = os.getenv('NOSTR_PRIVATE_KEY')
    if not private_key_raw:
        return {"error": "NOSTR_PRIVATE_KEY not set"}
    
    try:
        # Handle nsec format (bech32) or raw hex
        if private_key_raw.startswith('nsec'):
            import bech32
            _, data = bech32.bech32_decode(private_key_raw)
            private_key_hex = bytes(bech32.convertbits(data, 5, 8, False)).hex()
        else:
            private_key_hex = private_key_raw
        
        # Create private key object
        private_key = secp256k1.PrivateKey(bytes.fromhex(private_key_hex))
        public_key_hex = private_key.pubkey.serialize().hex()[2:]  # Remove '02' or '03' prefix
        
        # Create event
        created_at = int(time.time())
        kind = 1  # Text note
        tags = tags or []
        
        # Create event ID (SHA256 of serialized event)
        event_data = json.dumps([0, public_key_hex, created_at, kind, tags, content], separators=(',', ':'))
        event_id = hashlib.sha256(event_data.encode()).hexdigest()
        
        # Sign the event
        sig = private_key.schnorr_sign(bytes.fromhex(event_id), None, raw=True).hex()
        
        event = {
            "id": event_id,
            "pubkey": public_key_hex,
            "created_at": created_at,
            "kind": kind,
            "tags": tags,
            "content": content,
            "sig": sig
        }
        
        # Publish to relays
        relays = [
            "wss://relay.damus.io",
            "wss://relay.nostr.band",
            "wss://nos.lol"
        ]
        
        success_count = 0
        for relay in relays:
            try:
                ws = websocket.create_connection(relay, timeout=5)
                ws.send(json.dumps(["EVENT", event]))
                response = ws.recv()
                ws.close()
                success_count += 1
            except Exception as e:
                pass  # Relay failed, try next
        
        return {"success": True, "relays_published": success_count, "event_id": event_id}
        
    except Exception as e:
        return {"error": str(e)}
