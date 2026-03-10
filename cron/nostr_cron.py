"""
cron/nostr_cron.py — Hourly Nostr top-content refresh.

Scheduled to run every hour via system cron or the PP scheduler.
Refreshes the nostr_monitor_events cache and prunes old low-score events.

M6 FIX: Explicit path setup to ensure imports resolve regardless of cwd.
Usage:
    python3 /home/ultron/protocol_pulse/cron/nostr_cron.py
  OR via crontab:
    0 * * * * cd /home/ultron/protocol_pulse/core && python3 ../cron/nostr_cron.py
"""
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# M6 FIX: Resolve project root and core path from this file's location (absolute)
_CRON_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CRON_DIR.parent
_CORE_DIR = _PROJECT_ROOT / "core"

# Insert at front so our modules take precedence
for _p in [str(_CORE_DIR), str(_PROJECT_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Switch cwd to core/ so Flask's relative paths (DB, .env) resolve correctly
os.chdir(str(_CORE_DIR))

logger = logging.getLogger("nostr_cron")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [nostr_cron] %(levelname)s %(message)s",
)


def prune_old_events(max_age_days: int = 7, min_score: float = 5.0) -> int:
    """
    Remove events older than max_age_days with score below min_score.
    Keeps top content and VIP pubkey content indefinitely.
    Returns number of rows deleted.
    """
    try:
        from app import app, db
        import models

        cutoff = int(time.time()) - (max_age_days * 86400)

        with app.app_context():
            # Get VIP pubkeys to protect their content
            vip_pubkeys = [
                row.pubkey
                for row in db.session.execute(
                    db.select(models.NostrTrackedPubkey).where(
                        models.NostrTrackedPubkey.follower_tier == "vip"
                    )
                ).scalars().all()
            ]

            # Delete old low-score events not from VIP pubkeys
            query = (
                db.delete(models.NostrMonitorEvent)
                .where(models.NostrMonitorEvent.created_at < cutoff)
                .where(models.NostrMonitorEvent.engagement_score < min_score)
            )
            if vip_pubkeys:
                query = query.where(
                    ~models.NostrMonitorEvent.pubkey.in_(vip_pubkeys)
                )

            result = db.session.execute(query)
            deleted = result.rowcount
            db.session.commit()
            logger.info("Pruned %d old low-score events", deleted)
            return deleted
    except Exception as e:
        logger.error("Prune error: %s", e)
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return 0


def seed_pubkeys_if_needed() -> int:
    """Ensure tracked pubkeys are seeded."""
    try:
        from services.nostr_service import seed_tracked_pubkeys
        return seed_tracked_pubkeys()
    except Exception as e:
        logger.error("Seed pubkeys error: %s", e)
        return 0


def log_stats():
    """Log current collection stats."""
    try:
        from services.nostr_service import get_stats
        stats = get_stats()
        logger.info(
            "Stats: %d total events, %d today, %d tracked pubkeys",
            stats.get("total_events", 0),
            stats.get("events_today", 0),
            stats.get("tracked_pubkeys", 0),
        )
    except Exception as e:
        logger.error("Stats error: %s", e)


def run():
    """Main cron job: seed → prune → log."""
    logger.info("=== Nostr cron job starting === %s", datetime.now(timezone.utc).isoformat())

    seeded = seed_pubkeys_if_needed()
    if seeded:
        logger.info("Seeded %d new pubkeys", seeded)

    pruned = prune_old_events(max_age_days=7, min_score=5.0)
    log_stats()

    logger.info("=== Nostr cron job complete (pruned %d) ===", pruned)


if __name__ == "__main__":
    run()
