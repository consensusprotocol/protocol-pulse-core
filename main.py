from app import app
import os
import sys
import logging
import atexit
import multiprocessing
import fcntl
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

application = app

_scheduler = None
_scheduler_started = False
_lock_fd = None

def start_scheduler():
    """Start the background scheduler for automatic article generation"""
    global _scheduler, _scheduler_started

    if _scheduler_started:
        logger.info("Scheduler already started, skipping")
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler()

    def run_automation():
        """Run the article generation automation"""
        try:
            with app.app_context():
                # Verify database is accessible before proceeding
                from models import Article
                Article.query.first()

                from pp_services.automation import generate_article_with_tracking
                logger.info("=== SCHEDULED AUTOMATION TRIGGERED ===")
                result = generate_article_with_tracking()
                if result.get('success'):
                    logger.info(f"Automation SUCCESS: Article #{result.get('article_id')} - {result.get('title', '')[:50]}...")
                elif result.get('skipped'):
                    logger.info("Automation skipped: Another process is running")
                else:
                    logger.warning(f"Automation completed with issues: {result.get('error', 'Unknown')}")


        except Exception as e:
            logger.error(f"Automation error: {e}", exc_info=True)

    scheduler.add_job(
        func=run_automation,
        trigger=IntervalTrigger(minutes=15),
        id='article_automation',
        name='Generate article every 15 minutes',
        replace_existing=True,
        max_instances=1
    )

    # Affiliate editorial articles - 3 per day, rotated partners
    try:
        from pp_services.article_automation import run_scheduled_affiliate_article
        scheduler.add_job(
            run_scheduled_affiliate_article,
            'cron',
            hour='14,19,1',
            minute=30,
            id='affiliate_articles',
            name='Generate affiliate editorial article 3x/day',
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info("Affiliate article scheduler: 3x/day at 9:30am, 2:30pm, 8:30pm ET")
    except Exception as e:
        logger.error(f"Failed to schedule affiliate articles: {e}")

    # Comment Radar — every 3 hours, reply to viral Bitcoin tweets
    try:
        from pp_services.radar_automation import run_radar_cycle_safe
        scheduler.add_job(
            run_radar_cycle_safe,
            'interval',
            hours=3,
            id='comment_radar',
            name='Comment Radar - reply to viral Bitcoin tweets',
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info("Comment Radar scheduler: every 3 hours")
    except Exception as e:
        logger.error(f"Failed to schedule Comment Radar: {e}")
    # Sentiment Pulse — daily editorial digest at 6 PM ET (23:00 UTC)
    try:
        from pp_services.sentiment_pulse import generate_daily_sentiment_pulse
        scheduler.add_job(
            generate_daily_sentiment_pulse,
            'cron',
            hour=23,
            minute=0,
            id='sentiment_pulse',
            name='Daily Sentiment Pulse article',
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info("Sentiment Pulse scheduler: daily at 6 PM ET")
    except Exception as e:
        logger.error(f"Failed to schedule Sentiment Pulse: {e}")

    # Viral Tweet Engine — original tweets + quote tweets every 4 hours (offset from Comment Radar)
    try:
        from pp_services.x_engagement_engine import run_full_engagement_strategy
        scheduler.add_job(
            run_full_engagement_strategy,
            'interval',
            hours=4,
            id='viral_tweet_engine',
            name='Viral Tweet Engine - original posts + quote tweets',
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info("Viral Tweet Engine scheduler: every 4 hours")
    except Exception as e:
        logger.error(f"Failed to schedule Viral Tweet Engine: {e}")

    # Reply-Back Engine — respond to replies on our tweets every 2 hours
    try:
        from pp_services.reply_back_engine import run_reply_back
        scheduler.add_job(
            run_reply_back, 'interval', hours=2,
            id='reply_back', name='Reply-Back Engine',
            replace_existing=True, misfire_grace_time=3600
        )
        logger.info("Reply-Back Engine scheduler: every 2 hours")
    except Exception as e:
        logger.error(f"Failed to schedule Reply-Back: {e}")


    # Intel Briefing — opinion columns 3x daily (8AM, 1PM, 7PM ET)
    try:
        from pp_services.intel_briefing import generate_intel_briefing
        for hour_utc, label in [(13, 'morning'), (18, 'afternoon'), (0, 'evening')]:
            scheduler.add_job(
                generate_intel_briefing,
                'cron',
                hour=hour_utc,
                minute=15,
                id=f'intel_briefing_{label}',
                name=f'Intel Briefing - {label} edition',
                replace_existing=True,
                misfire_grace_time=3600
            )
        logger.info("Intel Briefing scheduler: 3x daily (8AM, 1PM, 7PM ET)")
    except Exception as e:
        logger.error(f"Failed to schedule Intel Briefing: {e}")





    def refresh_podcast_feeds():
        """Background task to refresh podcast RSS feeds"""
        try:
            with app.app_context():
                from pp_services.rss_service import rss_service
                rss_service.clear_cache()
                episodes = rss_service.get_latest_episodes(limit=20)
                logger.info(f"RSS refresh: {len(episodes)} episodes loaded")
        except Exception as e:
            logger.error(f"RSS refresh failed: {e}")

    scheduler.add_job(
        func=refresh_podcast_feeds,
        trigger=IntervalTrigger(minutes=15),
        id='rss_feed_refresh',
        name='Refresh podcast RSS feeds every 15 minutes',
        replace_existing=True,
        max_instances=1
    )

    def run_podcast_generation():
        """Background task to generate audio intelligence podcasts from partner channels"""
        try:
            with app.app_context():
                from pp_services.automation import generate_podcasts_from_partners
                generate_podcasts_from_partners()
                logger.info("Podcast generation completed")
        except Exception as e:
            logger.error(f"Podcast generation failed: {e}")

    def run_multimodal_auto_processing():
        """Background task to auto-process new partner videos with full social packages"""
        try:
            with app.app_context():
                from pp_services.youtube_service import YouTubeService
                yt_service = YouTubeService()
                results = yt_service.auto_process_new_partner_videos()
                logger.info(f"Multimodal auto-processing completed: {results.get('videos_found', 0)} videos processed")
        except Exception as e:
            logger.error(f"Multimodal auto-processing failed: {e}")

    scheduler.add_job(
        func=run_podcast_generation,
        trigger=IntervalTrigger(hours=12),
        id='podcast_generation',
        name='Generate podcasts from partner channels every 12 hours',
        replace_existing=True,
        max_instances=1
    )

    scheduler.add_job(
        func=run_multimodal_auto_processing,
        trigger=IntervalTrigger(hours=6),
        id='multimodal_auto_processing',
        name='Auto-process new partner videos every 6 hours',
        replace_existing=True,
        max_instances=1
    )

    def run_cypherpunkd_autonomy():
        """
        PERMANENT AUTONOMY: Cypherpunk'd Playlist Auto-Processing

        Pipeline:
        1. Polls Cypherpunk'd playlist (PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd) every 6 hours
        2. Detects new episodes and transcribes them
        3. Generates Bitcoin Lens article with Sovereign Intelligence voice
        4. Cuts 60-second clips with branding outro
        5. Creates X thread + Nostr note with Walter Cronkite persona
        6. Auto-approves sequence for 8:30 AM EST "Sovereign Window"
        7. Sends Telegram confirmation: "SIGNAL SECURED"
        """
        try:
            with app.app_context():
                from pp_services.youtube_service import YouTubeService
                yt_service = YouTubeService()
                results = yt_service.auto_process_cypherpunkd_with_launch()

                if results.get('sequences_queued'):
                    logger.info(f"[CYPHERPUNK'D AUTONOMY] {len(results['sequences_queued'])} sequences auto-approved for dispatch")
                else:
                    logger.info("[CYPHERPUNK'D AUTONOMY] No new episodes to process")

        except Exception as e:
            logger.error(f"Cypherpunk'd autonomy pipeline failed: {e}")

    scheduler.add_job(
        func=run_cypherpunkd_autonomy,
        trigger=IntervalTrigger(hours=6),
        id='cypherpunkd_autonomy',
        name='Cypherpunk\'d Autonomous Pipeline - Poll every 6 hours',
        replace_existing=True,
        max_instances=1
    )

    def run_ghl_network_sync():
        """Sync Bitcoin network metrics to GHL Custom Values"""
        try:
            with app.app_context():
                from pp_services.ghl_service import ghl_service
                result = ghl_service.sync_network_metrics()
                if result.get('success'):
                    logger.info(f"GHL SYNC SUCCESS: Network metrics pushed - Difficulty={result.get('difficulty')}, Hashrate={result.get('hashrate')}")
                else:
                    logger.warning(f"GHL sync failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"GHL sync error: {e}")

    scheduler.add_job(
        func=run_ghl_network_sync,
        trigger=IntervalTrigger(hours=24),
        id='ghl_network_sync',
        name='Sync Bitcoin network metrics to GHL every 24 hours',
        replace_existing=True,
        max_instances=1
    )

    def run_social_listener_scan():
        """Scan social targets for new engagement opportunities"""
        try:
            with app.app_context():
                from pp_services.social_listener import social_listener
                if social_listener.initialized:
                    results = social_listener.scan_all_targets()
                    if results.get('new_tweets'):
                        logger.info(f"Social Listener found {len(results['new_tweets'])} new tweets from targets")
                    else:
                        logger.debug("Social Listener scan complete - no new signal tweets")
                else:
                    logger.debug("Social Listener not initialized - skipping scan")
        except Exception as e:
            logger.error(f"Social Listener scan error: {e}")

    scheduler.add_job(
        func=run_social_listener_scan,
        trigger=IntervalTrigger(minutes=10),
        id='social_listener_scan',
        name='Scan social targets every 10 minutes',
        replace_existing=True,
        max_instances=1
    )

    def run_feed_ingestion():
        """Ingest feeds from RSS, YouTube, and other sources"""
        try:
            with app.app_context():
                from pp_services.feed_ingest import run_full_ingestion
                count = run_full_ingestion()
                logger.info(f"Feed ingestion complete: {count} items")
        except Exception as e:
            logger.error(f"Feed ingestion error: {e}")

    scheduler.add_job(
        func=run_feed_ingestion,
        trigger=IntervalTrigger(minutes=5),
        id='feed_ingestion',
        name='Ingest media feeds every 5 minutes',
        replace_existing=True,
        max_instances=1
    )

    def run_sentiment_analysis():
        """Compute network sentiment using weighted scoring and state detection"""
        try:
            with app.app_context():
                from pp_services.sentiment_engine import compute_network_sentiment
                result = compute_network_sentiment(hours=24)
                if result.get('state_changed'):
                    logger.info(f"Network state changed: {result.get('previous_state')} -> {result.get('state', {}).get('key')}")
                else:
                    logger.debug(f"Sentiment computed: {result.get('score', 50):.1f} ({result.get('state', {}).get('label', 'EQUILIBRIUM')})")
        except Exception as e:
            logger.error(f"Sentiment engine error: {e}")

    scheduler.add_job(
        func=run_sentiment_analysis,
        trigger=IntervalTrigger(minutes=2),
        id='sentiment_analysis',
        name='Compute sentiment every 2 minutes',
        replace_existing=True,
        max_instances=1
    )

    def run_supervisor_auto_publish():
        """Auto-generate and publish content via Multi-Agent Supervisor"""
        try:
            with app.app_context():
                from pp_services.launch_sequence import launch_sequence_service
                from models import Article

                latest_article = Article.query.order_by(Article.created_at.desc()).first()
                if latest_article:
                    result = launch_sequence_service.auto_publish_supervisor_content(
                        article_id=latest_article.id
                    )
                    if result.get('success'):
                        logger.info(f"Supervisor auto-publish SUCCESS: Nostr={result.get('nostr_result', {}).get('success')}, X={result.get('x_result', {}).get('success')}")
                    else:
                        logger.warning(f"Supervisor auto-publish completed with issues: {result.get('error', 'Unknown')}")
        except Exception as e:
            logger.error(f"Supervisor auto-publish error: {e}")

    scheduler.add_job(
        func=run_supervisor_auto_publish,
        trigger=IntervalTrigger(hours=2),
        id='supervisor_auto_publish',
        name='Auto-publish via Multi-Agent Supervisor every 2 hours',
        replace_existing=True,
        max_instances=1
    )

    def run_intelligence_stream():
        """Generate and publish Alex/Sarah intel tweets from partner content every 3 hours"""
        try:
            with app.app_context():
                from pp_services.intelligence_stream_service import intelligence_stream
                result = intelligence_stream.run_intelligence_stream()
                if result.get('success'):
                    logger.info(f"[INTEL STREAM] Published: {result.get('partner', 'unknown')}")
                else:
                    logger.debug(f"[INTEL STREAM] No content published this cycle")
        except Exception as e:
            logger.error(f"Intelligence stream error: {e}")

    scheduler.add_job(
        func=run_intelligence_stream,
        trigger=IntervalTrigger(hours=3),
        id='intelligence_stream',
        name='Alex/Sarah Intelligence Stream every 3 hours',
        replace_existing=True,
        max_instances=1
    )

    def run_whale_heartbeat():
        """Monitor for whale transactions and send Telegram alerts"""
        try:
            import requests
            resp = requests.get('https://mempool.space/api/mempool/recent', timeout=10)
            if resp.status_code == 200:
                whales = [tx for tx in resp.json() if tx.get('value', 0) / 100000000 >= 100]
                if whales:
                    logger.info(f"[WHALE] Detected {len(whales)} whale transactions (>=100 BTC)")
                    from pp_services.telegram_service import send_whale_alert
                    for whale in whales[:2]:
                        btc = whale.get('value', 0) / 100000000
                        is_mega = btc >= 500
                        send_whale_alert(btc, whale['txid'], is_mega)
        except Exception as e:
            logger.debug(f"Whale heartbeat check: {e}")

    scheduler.add_job(
        func=run_whale_heartbeat,
        trigger=IntervalTrigger(minutes=5),
        id='whale_heartbeat',
        name='Whale Watcher heartbeat every 5 minutes',
        replace_existing=True,
        max_instances=1
    )

    def run_content_distribution():
        """Check for articles ready for distribution and push to channels"""
        try:
            with app.app_context():
                from models import Article
                from pp_services.telegram_service import send_article_notification

                if not hasattr(Article, 'status'):
                    logger.debug("[DISTRIBUTION] Article model does not have status field - skipping")
                    return

                pending = Article.query.filter(
                    Article.status == 'ready_for_distribution'
                ).limit(3).all()

                if not pending:
                    logger.debug("[DISTRIBUTION] No articles pending distribution")
                    return

                for article in pending:
                    slug = getattr(article, 'slug', None) or f"article-{article.id}"
                    category = getattr(article, 'category', None) or "Intel Brief"

                    result = send_article_notification(
                        title=article.title,
                        url=f"/article/{slug}",
                        category=category
                    )

                    if result:
                        article.status = 'distributed'
                        logger.info(f"[DISTRIBUTION] Published: {article.title[:50]}...")
                    else:
                        logger.warning(f"[DISTRIBUTION] Failed to distribute: {article.title[:50]}...")

                from app import db
                db.session.commit()
        except Exception as e:
            logger.debug(f"Content distribution check: {e}")

    scheduler.add_job(
        func=run_content_distribution,
        trigger=IntervalTrigger(hours=1),
        id='content_distribution',
        name='Content distribution check every hour',
        replace_existing=True,
        max_instances=1
    )

    def run_daily_sentiment_report():
        """Generate daily Bitcoin sentiment report from X and Nostr"""
        try:
            from pp_services.sentiment_tracker_service import sentiment_tracker
            article_id = sentiment_tracker.run_daily_report()
            if article_id:
                logger.info(f"[SENTIMENT] Daily report generated: Article #{article_id}")
            else:
                logger.debug("[SENTIMENT] No report generated this cycle")
        except Exception as e:
            logger.error(f"Sentiment report error: {e}")

    scheduler.add_job(
        func=run_daily_sentiment_report,
        trigger=IntervalTrigger(hours=24),
        id='daily_sentiment_report',
        name='Daily Bitcoin Sentiment Report from X/Nostr',
        replace_existing=True,
        max_instances=1
    )


    scheduler.start()

    scheduler.add_job(
        func=run_daily_sentiment_report,
        id='initial_sentiment_report',
        name='Initial Sentiment Report',
        trigger='date',
        run_date=datetime.now() + timedelta(seconds=45),
        replace_existing=True
    )
    logger.info("=== INITIAL SENTIMENT REPORT SCHEDULED (45 sec delay) ===")

    # Trigger first auto-publish immediately (30 second delay to let app fully initialize)
    scheduler.add_job(
        func=run_supervisor_auto_publish,
        id='initial_auto_publish',
        name='Initial supervisor auto-publish',
        trigger='date',
        run_date=datetime.now() + timedelta(seconds=30),
        replace_existing=True
    )
    logger.info("=== INITIAL AUTO-PUBLISH SCHEDULED (30 sec delay) ===")
    _scheduler = scheduler
    _scheduler_started = True
    logger.info("=== SCHEDULER STARTED: Articles will generate every 15 minutes ===")

    # Trigger first run immediately (runs in background thread)
    scheduler.add_job(
        func=run_automation,
        id='initial_run',
        name='Initial article generation',
        replace_existing=True
    )
    logger.info("=== INITIAL ARTICLE GENERATION TRIGGERED ===")

    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler

    # Thread Engine — weekly deep-dive threads (Mon & Thu 10AM ET)
    try:
        from pp_services.thread_engine import run_weekly_thread
        scheduler.add_job(
            run_weekly_thread, 'cron', day_of_week='mon,thu', hour=14, minute=30,
            id='thread_engine', name='Thread Engine - weekly deep-dive',
            replace_existing=True, misfire_grace_time=7200
        )
        logger.info("Thread Engine scheduler: Mon & Thu 10AM ET")
    except Exception as e:
        logger.error(f"Failed to schedule Thread Engine: {e}")

    # Performance Tracker — update strategy weights daily
    try:
        from pp_services.performance_tracker import update_performance_weights
        scheduler.add_job(
            update_performance_weights, 'cron', hour=4, minute=0,
            id='performance_tracker', name='Performance Tracker',
            replace_existing=True, misfire_grace_time=3600
        )
        logger.info("Performance Tracker scheduler: daily midnight ET")
    except Exception as e:
        logger.error(f"Failed to schedule Performance Tracker: {e}")

    # Bookmark Bait — save-worthy tweets daily at 2PM ET
    try:
        from pp_services.bookmark_bait import run_bookmark_bait
        scheduler.add_job(
            run_bookmark_bait, 'cron', hour=19, minute=0,
            id='bookmark_bait', name='Bookmark Bait tweet',
            replace_existing=True, misfire_grace_time=3600
        )
        logger.info("Bookmark Bait scheduler: daily 2PM ET")
    except Exception as e:
        logger.error(f"Failed to schedule Bookmark Bait: {e}")

    # Nostr Cross-poster — daily best tweet to Nostr at 3PM ET
    try:
        from pp_services.nostr_crosspost import run_nostr_crosspost
        scheduler.add_job(
            run_nostr_crosspost, 'cron', hour=20, minute=0,
            id='nostr_crosspost', name='Nostr cross-post best tweet',
            replace_existing=True, misfire_grace_time=3600
        )
        logger.info("Nostr cross-poster scheduler: daily 3PM ET")
    except Exception as e:
        logger.error(f"Failed to schedule Nostr: {e}")

    # Daily Newsletter — morning intelligence brief at 9AM ET (14:00 UTC)
    try:
        from pp_services.newsletter_engine import NewsletterEngine
        def run_daily_newsletter():
            with app.app_context():
                engine = NewsletterEngine()
                result = engine.run_daily_newsletter()
                logger.info(f"Daily newsletter result: {result}")
                return result
        scheduler.add_job(
            run_daily_newsletter, 'cron', hour=14, minute=0,
            id='daily_newsletter', name='Daily Newsletter - morning brief',
            replace_existing=True, misfire_grace_time=3600
        )
        logger.info("Daily Newsletter scheduler: 9AM ET daily")
    except Exception as e:
        logger.error(f"Failed to schedule Daily Newsletter: {e}")

    # Weekly Premium Digest — "The Sovereign Signal" every Monday 8AM ET (13:00 UTC)
    try:
        from pp_services.newsletter_digest import NewsletterDigestService
        def run_weekly_premium():
            with app.app_context():
                digest = NewsletterDigestService()
                result = digest.generate_and_publish()
                logger.info(f"Weekly premium digest result: {result}")

                # Send to subscribers
                from pp_services.newsletter_engine import NewsletterEngine
                engine = NewsletterEngine()
                subscribers = engine.get_subscribers()
                if subscribers and result.get("success"):
                    html = result.get("html", "")
                    if html:
                        send_result = engine.send_newsletter(
                            subscribers,
                            subject=f"The Sovereign Signal • Week of {__import__('datetime').datetime.utcnow().strftime('%B %d')}",
                            html=html
                        )
                        logger.info(f"Weekly digest sent: {send_result}")
                return result
        scheduler.add_job(
            run_weekly_premium, 'cron', day_of_week='mon', hour=13, minute=0,
            id='weekly_premium', name='Weekly Premium Digest - The Sovereign Signal',
            replace_existing=True, misfire_grace_time=7200
        )
        logger.info("Weekly Premium Digest scheduler: Monday 8AM ET")
    except Exception as e:
        logger.error(f"Failed to schedule Weekly Digest: {e}")








def try_start_scheduler_once():
    """
    Use file-based locking to ensure only ONE process starts the scheduler.
    This works reliably with Gunicorn multi-worker mode.
    """
    global _lock_fd

    # Skip in development Flask reloader subprocess
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        logger.info("Skipping scheduler in Flask reloader subprocess")
        return

    lock_file = '/tmp/protocol_pulse_scheduler.lock'

    try:
        # Try to acquire exclusive non-blocking lock
        _lock_fd = open(lock_file, 'w')
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Write PID to lock file for debugging
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()

        logger.info(f"Acquired scheduler lock (PID {os.getpid()}) - starting scheduler")
        start_scheduler()

    except (IOError, OSError) as e:
        # Another process holds the lock
        logger.info(f"Another process owns scheduler lock - skipping (PID {os.getpid()})")
        if _lock_fd:
            _lock_fd.close()
            _lock_fd = None


# SCHEDULER PAUSED - All automated jobs disabled to stop API spending
# Scheduler enabled
try:
    try_start_scheduler_once()
    logger.info("=== SCHEDULER STARTED - All automation active ===")
except Exception as e:
    logger.error(f"Failed to start scheduler: {e}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
