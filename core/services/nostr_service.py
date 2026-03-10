"""
core/services/nostr_service.py — DB interface for Nostr Intelligence (F4).

Second pass fixes (post-audit):
  - U4: Fixed rollback bug using begin_nested() savepoints per row
  - U5: Fixed 3 invalid seed pubkeys (63 chars → 64 chars verified)
  - M4: Fixed follower_tier sort order using CASE expression
  - G1: Elevated relay status file errors to WARNING
  - G3: Added event_id format validation (64-char hex)
  - GPT-P1: Added secondary sort by created_at in get_top_content()
"""
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

# Validate 64-char hex pubkey
_HEX64_RE = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)
_HEX64_EVENT_RE = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)


def _is_valid_pubkey(pubkey: str) -> bool:
    return bool(pubkey and _HEX64_RE.match(pubkey))


def _is_valid_event_id(event_id: str) -> bool:
    """G3: Validate Nostr event ID is exactly 64 hex chars."""
    return bool(event_id and _HEX64_EVENT_RE.match(event_id))


# ── High-signal Bitcoin Nostr pubkeys (seed list, LAW 3) ─────────────────────
# U5 FIX: All pubkeys verified to be exactly 64 hex chars.
# Sources: well-known Bitcoin community members confirmed via Nostr clients
SEED_PUBKEYS: List[Dict] = [
    {
        "pubkey": "82341f882b6eabcd2ba7f1ef90aad961cf074af15b9ef44a09f9d2a8fbfbe6a2",
        "display_name": "Jack Dorsey",
        "nip05": "jack@cash.app",
        "follower_tier": "vip",
    },
    {
        "pubkey": "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d",
        "display_name": "Fiatjaf (NIP inventor)",
        "nip05": "fiatjaf@fiatjaf.com",
        "follower_tier": "vip",
    },
    {
        "pubkey": "126103bfddc8df256b6e0abfd7f3797c80dcc4ea88f7c2f87dd4104220b4d650",
        "display_name": "Marty Bent",
        "nip05": "marty@tfp.com",
        "follower_tier": "vip",
    },
    {
        "pubkey": "04c915daefee38317fa734444acee390a8269fe5810b2241e5e6dd343dfbecc4",
        "display_name": "ODELL",
        "nip05": "odell@odell.xyz",
        "follower_tier": "vip",
    },
    {
        "pubkey": "e88a691e98d9987c964521dff60025f60700378a4879180dcbbb4a5027850411",
        "display_name": "NVK (CoinKite)",
        "nip05": "nvk@nvk.org",
        "follower_tier": "vip",
    },
    {
        "pubkey": "b9e76546ba06456ed301d9e52bc49fa48e70a6bf2282be7a1ae72947612023dc",
        "display_name": "Luke Dashjr",
        "nip05": None,
        "follower_tier": "vip",
    },
    {
        "pubkey": "dd664d5e4016433a8cd69f005ae1480804351789b59de5af06276de65633dcdc",
        "display_name": "Lyn Alden",
        "nip05": None,
        "follower_tier": "vip",
    },
    {
        "pubkey": "6ad3e2a34818b153c81f48c58f44e5199d7b4d925ba3f1d5b7dece969c99b340",
        "display_name": "Jeff Booth",
        "nip05": None,
        "follower_tier": "standard",
    },
    {
        "pubkey": "85080d3bad70ccdcd7f74c29a44f55bb85cbcd3dd0cbb957da1d215bdb931204",
        "display_name": "Will Cole (Iris.to)",
        "nip05": None,
        "follower_tier": "standard",
    },
    {
        "pubkey": "7fa56f5d6962ab1e3cd424e758c3002b8665f7b0d8dcee9fe9e288d7751ac194",
        "display_name": "Walker (Bitcoin Magazine)",
        "nip05": None,
        "follower_tier": "standard",
    },
]

# Assert all seed pubkeys are valid at module load time
for _entry in SEED_PUBKEYS:
    assert _is_valid_pubkey(_entry["pubkey"]), (
        f"SEED_PUBKEYS validation failed: {_entry['display_name']} pubkey is not 64 hex chars"
    )


def seed_tracked_pubkeys() -> int:
    """
    Insert high-signal pubkeys into nostr_tracked_pubkeys on first run.
    Returns number of new records inserted.

    U4 FIX: Uses begin_nested() savepoints per row so a per-row exception
    only rolls back that single row, not all previously staged inserts.
    """
    try:
        from app import app, db
        import models

        inserted = 0
        with app.app_context():
            for entry in SEED_PUBKEYS:
                if not _is_valid_pubkey(entry["pubkey"]):
                    logger.warning("Skipping invalid pubkey for %s", entry.get("display_name"))
                    continue
                try:
                    # Use savepoint per row (U4 fix)
                    with db.session.begin_nested():
                        existing = db.session.execute(
                            db.select(models.NostrTrackedPubkey).where(
                                models.NostrTrackedPubkey.pubkey == entry["pubkey"]
                            )
                        ).scalar_one_or_none()
                        if existing:
                            continue
                        record = models.NostrTrackedPubkey(
                            pubkey=entry["pubkey"],
                            display_name=entry.get("display_name"),
                            nip05=entry.get("nip05"),
                            follower_tier=entry.get("follower_tier", "standard"),
                        )
                        db.session.add(record)
                        inserted += 1
                except Exception as e:
                    logger.warning("Error seeding pubkey %s: %s", entry.get("display_name"), e)
                    # Savepoint automatically rolled back; outer session unaffected

            try:
                db.session.commit()
                logger.info("Seeded %d new tracked pubkeys", inserted)
            except Exception as e:
                logger.error("Seed commit failed: %s", e)
                db.session.rollback()
        return inserted
    except Exception as e:
        logger.error("seed_tracked_pubkeys failed: %s", e)
        return 0


def get_top_content(limit: int = 10) -> List[Dict]:
    """
    Return top N Nostr events by engagement score from the last 24h.
    Falls back to all-time if no recent events exist.

    GPT-P1 FIX: Secondary sort by created_at.desc() for deterministic ordering on ties.
    """
    try:
        from app import app, db
        import models

        with app.app_context():
            cutoff = int(time.time()) - 86400  # 24h ago

            # Try recent first
            events = db.session.execute(
                db.select(models.NostrMonitorEvent)
                .where(models.NostrMonitorEvent.created_at >= cutoff)
                .order_by(
                    models.NostrMonitorEvent.engagement_score.desc(),
                    models.NostrMonitorEvent.created_at.desc(),  # tiebreaker
                )
                .limit(limit)
            ).scalars().all()

            # Fallback: all-time top if no recent events
            if not events:
                events = db.session.execute(
                    db.select(models.NostrMonitorEvent)
                    .order_by(
                        models.NostrMonitorEvent.engagement_score.desc(),
                        models.NostrMonitorEvent.created_at.desc(),
                    )
                    .limit(limit)
                ).scalars().all()

            result = []
            for ev in events:
                content_preview = (ev.content or "")[:280]
                result.append({
                    "event_id": ev.event_id,
                    "pubkey": ev.pubkey,
                    "pubkey_short": ev.pubkey[:8] + "..." if ev.pubkey else "",
                    "kind": ev.kind,
                    "content": content_preview,
                    "content_full": ev.content or "",
                    "engagement_score": round(ev.engagement_score or 0, 1),
                    "zaps": ev.zaps or 0,
                    "quotes": ev.quotes or 0,
                    "reposts": ev.reposts or 0,
                    "replies": ev.replies or 0,
                    "reactions": ev.reactions or 0,
                    "bitcoin_relevance": round(ev.bitcoin_relevance or 0, 2),
                    "relay_source": ev.relay_source or "",
                    "created_at": ev.created_at,
                    "created_at_iso": datetime.fromtimestamp(
                        ev.created_at, tz=timezone.utc
                    ).isoformat() if ev.created_at else None,
                    "fetched_at": ev.fetched_at.isoformat() if ev.fetched_at else None,
                    "nostr_link": f"https://njump.me/{ev.event_id}" if ev.event_id else "",
                })
            return result
    except Exception as e:
        logger.error("get_top_content error: %s", e)
        return []


def get_relay_status() -> List[Dict]:
    """
    Return relay connection status.
    Reads from state/nostr_relay_status.json written by the monitor process (atomic write).
    Falls back to static disconnected list if monitor not running.

    G1 FIX: File read errors now logged at WARNING level.
    """
    import json as _json
    from pathlib import Path as _Path

    status_file = _Path(__file__).resolve().parent.parent.parent / "state" / "nostr_relay_status.json"
    try:
        if status_file.exists():
            data = _json.loads(status_file.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
    except Exception as e:
        logger.warning("Could not read relay status file %s: %s", status_file, e)

    # Fallback: static disconnected
    relays = [
        "wss://relay.damus.io",
        "wss://nos.lol",
        "wss://relay.nostr.band",
        "wss://relay.primal.net",
    ]
    return [
        {
            "relay": r,
            "connected": False,
            "last_event_at": None,
            "events_today": 0,
        }
        for r in relays
    ]


def get_tracked_pubkeys() -> List[Dict]:
    """
    Return all tracked pubkeys from DB.
    M4 FIX: Uses CASE expression for deterministic tier ordering (vip > standard).
    """
    try:
        from app import app, db
        import models
        from sqlalchemy import case

        with app.app_context():
            tier_order = case(
                (models.NostrTrackedPubkey.follower_tier == "vip", 4),
                (models.NostrTrackedPubkey.follower_tier == "high", 3),
                (models.NostrTrackedPubkey.follower_tier == "medium", 2),
                else_=1,
            )
            rows = db.session.execute(
                db.select(models.NostrTrackedPubkey)
                .order_by(tier_order.desc(), models.NostrTrackedPubkey.display_name)
            ).scalars().all()
            return [
                {
                    "pubkey": r.pubkey,
                    "display_name": r.display_name,
                    "nip05": r.nip05,
                    "follower_tier": r.follower_tier,
                    "added_at": r.added_at.isoformat() if r.added_at else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error("get_tracked_pubkeys error: %s", e)
        return []


def get_stats() -> Dict:
    """Return aggregate stats for the admin dashboard."""
    try:
        from app import app, db
        import models

        with app.app_context():
            total = db.session.execute(
                db.select(db.func.count(models.NostrMonitorEvent.id))
            ).scalar() or 0

            cutoff = int(time.time()) - 86400
            today = db.session.execute(
                db.select(db.func.count(models.NostrMonitorEvent.id))
                .where(models.NostrMonitorEvent.created_at >= cutoff)
            ).scalar() or 0

            tracked = db.session.execute(
                db.select(db.func.count(models.NostrTrackedPubkey.id))
            ).scalar() or 0

            return {
                "total_events": total,
                "events_today": today,
                "tracked_pubkeys": tracked,
            }
    except Exception as e:
        logger.error("get_stats error: %s", e)
        return {"total_events": 0, "events_today": 0, "tracked_pubkeys": 0}
