#!/usr/bin/env python3
"""
sync_media_feeds.py — Standalone robust media feed sync.
Runs independently of Flask. Safe to call from cron or manually.
Usage: python3 ~/protocol_pulse/scripts/sync_media_feeds.py
Cron:  */30 * * * * cd /home/ultron/protocol_pulse/core && /usr/bin/python3 ../scripts/sync_media_feeds.py >> /home/ultron/protocol_pulse/logs/media_sync.log 2>&1
"""
import sys, os, logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [FeedSync] %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

CORE_DIR = Path(__file__).resolve().parent.parent / 'core'
sys.path.insert(0, str(CORE_DIR))

def main():
    log.info('Starting feed sync...')
    try:
        from app import app, db
        from pp_services.media_feed_service import sync_all_feeds
        import models

        with app.app_context():
            # Sync all feeds
            total = sync_all_feeds(app)
            log.info(f'Sync complete. Total new: {total}')

            # Prune old episodes — keep only 30 most recent per feed
            feeds = models.MediaFeed.query.filter_by(active=True).all()
            pruned = 0
            for feed in feeds:
                eps = (models.MediaEpisode.query
                       .filter_by(feed_id=feed.id)
                       .order_by(models.MediaEpisode.published_at.desc())
                       .all())
                if len(eps) > 30:
                    for old_ep in eps[30:]:
                        db.session.delete(old_ep)
                        pruned += 1
            if pruned:
                db.session.commit()
                log.info(f'Pruned {pruned} old episodes (keeping 30/feed)')

            # Report feed health
            for feed in feeds:
                ep_count = models.MediaEpisode.query.filter_by(feed_id=feed.id).count()
                log.info(f'  {feed.name[:35]:38} {feed.feed_type:8} eps:{ep_count:3} last:{str(feed.last_synced)[:16]}')

    except Exception as e:
        log.error(f'Sync failed: {e}', exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
