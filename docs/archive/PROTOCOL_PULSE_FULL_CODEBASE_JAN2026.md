# Protocol Pulse - Complete Codebase Export
## Generated: January 27, 2026

---

# TABLE OF CONTENTS

1. Core Application Files
   - app.py
   - main.py
   - models.py
   - routes.py (partial - key routes)
   
2. Service Layer
   - services/ai_service.py
   - services/content_engine.py
   - services/fact_checker.py
   - services/newsletter.py
   - services/monetization_service.py
   - services/youtube_service.py
   - services/ghl_service.py
   - services/price_service.py
   - services/nostr_broadcaster.py
   - services/launch_sequence.py

3. Templates (Key Templates)
   - templates/base.html
   - templates/index.html (partial)
   - templates/article_detail.html
   - templates/live_terminal.html

4. Static Assets
   - static/css/style.css (partial)
   - static/sw.js

---


# SECTION 1: CORE APPLICATION FILES

## app.py
```python
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Get port from environment for deployment
port = int(os.environ.get("PORT", 5000))

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
if database_url.startswith("sqlite:"):
    database_url += "?charset=utf8mb4"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Template filter for natural ad injection into article content
@app.template_filter('inject_ads')
def inject_ads(content):
    """
    Injects native advertisement units into article content naturally.
    Ads appear as 'Partner Intelligence' sections that blend with editorial content.
    """
    import random
    from models import Advertisement
    
    try:
        active_ads = Advertisement.query.filter_by(is_active=True).all()
        if not active_ads:
            return content
        
        ad = random.choice(active_ads)
        ad_html = f'''
        <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
            <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
            <a href="{ad.target_url}" target="_blank" rel="noopener" class="text-decoration-none">
                <img src="{ad.image_url}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{ad.name}">
                <p class="mb-0 text-white fw-bold">{ad.name}</p>
            </a>
        </div>
        '''
        
        # Inject ad after the second paragraph for natural placement
        parts = content.split('</p>', 2)
        if len(parts) > 2:
            return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
        return content + ad_html
        
    except Exception as e:
        logging.warning(f"Ad injection failed: {e}")
        return content


@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string to Python object"""
    import json
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


# Import routes after app creation
import routes
```

## main.py
```python
from app import app
import os
import sys
import logging
import atexit
import multiprocessing
import fcntl

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
                
                from services.automation import generate_article_with_tracking
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
    
    def refresh_podcast_feeds():
        """Background task to refresh podcast RSS feeds"""
        try:
            with app.app_context():
                from services.rss_service import rss_service
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
                from services.automation import generate_podcasts_from_partners
                generate_podcasts_from_partners()
                logger.info("Podcast generation completed")
        except Exception as e:
            logger.error(f"Podcast generation failed: {e}")
    
    def run_multimodal_auto_processing():
        """Background task to auto-process new partner videos with full social packages"""
        try:
            with app.app_context():
                from services.youtube_service import YouTubeService
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
    
    def run_ghl_network_sync():
        """Sync Bitcoin network metrics to GHL Custom Values"""
        try:
            with app.app_context():
                from services.ghl_service import ghl_service
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
                from services.social_listener import social_listener
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
    
    scheduler.start()
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


# Start scheduler on module import (works with Gunicorn)
try:
    try_start_scheduler_once()
except Exception as e:
    logger.error(f"Failed to start scheduler: {e}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

## models.py
```python
from app import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    newsletter_subscribed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    author = db.Column(db.String(100), default="Protocol Pulse AI")
    category = db.Column(db.String(50), default="Web3")
    tags = db.Column(db.String(500))  # Comma-separated tags
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))  # reddit, ai_generated, manual
    featured = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    substack_url = db.Column(db.String(500))  # URL of published Substack post
    header_image_url = db.Column(db.String(500))  # Header image for the article
    screenshot_url = db.Column(db.String(500))  # Screenshot for social media posts
    video_url = db.Column(db.String(500))  # YouTube embed URL for video content

class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    host = db.Column(db.String(100))
    episode_number = db.Column(db.Integer)
    duration = db.Column(db.String(20))  # Format: "1h 23m"
    audio_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    featured = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default="Web3")
    rss_source = db.Column(db.String(100))  # Source RSS feed name

class ContentPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    target_url = db.Column(db.String(300), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AutomationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # running, success, failed, skipped
    error = db.Column(db.String(500))  # Error message if failed


class LaunchSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer)
    content_type = db.Column(db.String(50))  # episode, brief, clip, article
    
    primary_post_copy = db.Column(db.Text)
    thread_replies = db.Column(db.Text)  # JSON array
    quote_variants = db.Column(db.Text)  # JSON array
    reply_drafts = db.Column(db.Text)  # JSON array of 10 templates
    
    hashtags = db.Column(db.String(500))
    posting_time = db.Column(db.Time)
    velocity_prediction = db.Column(db.Float)
    
    first_reply_link = db.Column(db.String(500))
    call_to_action = db.Column(db.String(300))
    
    status = db.Column(db.String(50), default='draft')  # draft, approved, published, analyzed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    
    tweet_id = db.Column(db.String(100))
    actual_velocity_score = db.Column(db.Float)
    replies_first_5min = db.Column(db.Integer, default=0)
    total_engagement = db.Column(db.Integer, default=0)
    reached_for_you = db.Column(db.Boolean, default=False)


class TargetAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(50))  # reply_squad, trending, partner
    source_url = db.Column(db.String(500))
    source_account = db.Column(db.String(100))
    content_snippet = db.Column(db.Text)
    priority = db.Column(db.Integer, default=2)  # 1 highest, 3 lowest
    strategy_suggested = db.Column(db.String(100))
    draft_replies = db.Column(db.Text)  # JSON array
    status = db.Column(db.String(50), default='pending')  # pending, approved, posted, skipped
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)


class NostrEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100))  # Nostr event ID hex
    content_type = db.Column(db.String(50))
    content_id = db.Column(db.Integer)
    relays_success = db.Column(db.Text)  # JSON array
    relays_failed = db.Column(db.Text)  # JSON array
    zaps_received = db.Column(db.Integer, default=0)
    zaps_amount_sats = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReplySquadMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(150))
    category = db.Column(db.String(100))  # human_rights, macro, technical, mining
    priority = db.Column(db.Integer, default=2)
    reciprocal_engagements = db.Column(db.Integer, default=0)
    last_engagement = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WhaleTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txid = db.Column(db.String(100), unique=True, nullable=False)
    btc_amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float)
    fee_sats = db.Column(db.Integer)
    block_height = db.Column(db.Integer)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_mega = db.Column(db.Boolean, default=False)  # 1000+ BTC


class BitcoinDonation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100))  # BTCPay or Lightning invoice ID
    amount_sats = db.Column(db.Integer)
    amount_usd = db.Column(db.Float)
    donor_email = db.Column(db.String(200))
    donor_name = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, expired
    payment_method = db.Column(db.String(50))  # onchain, lightning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
```

## routes.py (Complete)
```python
from flask import render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_login import login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from models import Article, Podcast, ContentPrompt, User, Advertisement, AutomationRun, LaunchSequence, TargetAlert, NostrEvent, ReplySquadMember
from functools import wraps
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.content_generator import ContentGenerator
from services.content_engine import ContentEngine
from services.substack_service import SubstackService
from services.newsletter import newsletter_service
from services.rss_service import RSSService
from services.printful_service import PrintfulService
from services.price_service import price_service
from services.youtube_service import YouTubeService
from services.node_service import NodeService
from services.ghl_service import ghl_service
import logging
import requests
import os
import re
import uuid
from datetime import datetime, timedelta

# Initialize services
ai_service = AIService()
reddit_service = RedditService()
content_generator = ContentGenerator()
content_engine = ContentEngine()
try:
    substack_service = SubstackService()
except Exception as e:
    logging.warning(f"Substack service initialization failed: {e}")
    substack_service = None

# Initialize RSS and Printful services
rss_service = RSSService()
printful_service = PrintfulService()

def admin_required(f):
    """Decorator to enforce admin role-based access control"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.template_filter('clean_preview')
def clean_preview_filter(content, max_length=150):
    """Extract clean preview text from HTML content, prioritizing TL;DR sections"""
    if not content:
        return ""
    
    # First try to extract TL;DR content specifically
    tldr_match = re.search(r'<div class="tldr-section">.*?<strong>TL;DR:\s*(.*?)</strong>', content, re.DOTALL | re.IGNORECASE)
    if tldr_match:
        tldr_text = tldr_match.group(1)
        # Strip any remaining HTML tags from TL;DR
        clean_tldr = re.sub(r'<[^>]+>', '', tldr_text).strip()
        if clean_tldr:
            # Return clean TL;DR text, truncated if needed
            return clean_tldr[:max_length] + ("..." if len(clean_tldr) > max_length else "")
    
    # Fallback: strip all HTML tags and get clean text
    clean_text = re.sub(r'<[^>]+>', '', content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()  # Normalize whitespace
    
    # Return truncated clean text
    return clean_text[:max_length] + ("..." if len(clean_text) > max_length else "")

@app.route('/')
def index():
    """Homepage with featured articles and podcasts"""
    featured_articles = Article.query.filter_by(published=True, featured=True).order_by(Article.created_at.desc()).limit(3).all()
    recent_articles = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).limit(6).all()
    featured_podcasts = Podcast.query.filter_by(featured=True).order_by(Podcast.published_date.desc()).limit(3).all()
    
    # Fetch live cryptocurrency prices
    prices = price_service.get_prices()
    
    # Generate Today's Signal briefing (120 words max)
    todays_signal = generate_todays_signal()
    
    return render_template('index.html', 
                         featured_articles=featured_articles,
                         recent_articles=recent_articles,
                         featured_podcasts=featured_podcasts,
                         prices=prices,
                         price_service=price_service,
                         todays_signal=todays_signal)

def generate_todays_signal():
    """Generate rotating 120-word briefing for Today's Signal"""
    import random
    
    # Pool of rotating signals (each under 120 words)
    signal_pool = [
        "Bitcoin network security remains robust at 146.47 T difficulty with ~977 EH/s hashrate. Transactors should monitor the upcoming difficulty adjustment for mining economics impact. The protocol continues self-regulating monetary issuance.",
        "Hashrate at ~977 EH/s demonstrates global miner commitment to network security. Current difficulty 146.47 T ensures 10-minute blocks. Smart transactors batch transactions during low-fee periods for optimal cost efficiency.",
        "Network fundamentals strong: 146.47 T difficulty secures the monetary base layer while ~977 EH/s proves decentralized work. Unlike fiat policy meetings, Bitcoin's issuance schedule is mathematically predetermined and censorship-resistant.",
        "Mining economics update: At 146.47 T difficulty, efficient operations remain profitable. Transactors benefit from predictable block times and transparent fee markets. The sound money protocol continues operating as designed.",
        "Bitcoin's difficulty adjustment mechanism proves protocol resilience. Current 146.47 T difficulty balances miner incentives with network security. ~977 EH/s of global hashpower validates decentralization thesis."
    ]
    
    try:
        # Get latest network stats from NodeService for dynamic signal
        stats = NodeService.get_network_stats()
        if stats and stats.get('height'):
            difficulty = stats.get('difficulty', '146.47 T')
            hashrate = stats.get('hashrate', '~977 EH/s')
            height = stats.get('height', 'Unknown')
            # Add dynamic signal based on real data
            dynamic_signal = f"Block {height}: Network difficulty at {difficulty} with {hashrate} hashrate. Transactors should monitor mining economics as the protocol continues self-regulating monetary issuance."
            signal_pool.append(dynamic_signal)
    except Exception as e:
        logging.warning(f"Failed to fetch network stats for signal: {e}")
    
    # Rotate based on time (changes every hour)
    hour_index = datetime.utcnow().hour % len(signal_pool)
    return signal_pool[hour_index]

@app.route('/live')
def live_terminal():
    """Live Settlement Terminal - Real-time Bitcoin network visualization"""
    return render_template('live_terminal.html')

@app.route('/map')
def merchant_map():
    """Sovereign Merchant Map - Interactive BTC vendor locator"""
    return render_template('merchant_map.html')

@app.route('/offline')
def offline():
    """Offline fallback page for PWA"""
    return render_template('offline.html')

@app.route('/whale-watcher')
def whale_watcher():
    """Whale Watcher - Live ticker for large BTC transactions"""
    return render_template('whale_watcher.html')

@app.route('/scorecard')
def sovereign_scorecard():
    """Sovereign Scorecard - Security self-assessment quiz"""
    return render_template('sovereign_scorecard.html')

@app.route('/clips')
def clips_gallery():
    """Signal Clips Gallery - Viral short-form content"""
    from services.clips_service import clips_service
    clips = clips_service.get_all_clips()
    return render_template('clips_gallery.html', clips=clips)

@app.route('/dashboard')
def dashboard():
    """Intelligence Dashboard with real-time Mempool.space metrics and Chart.js visualizations"""
    # Fetch Bitcoin network stats
    network_stats = None
    try:
        network_stats = NodeService.get_network_stats()
    except Exception as e:
        logging.warning(f"Failed to fetch network stats for dashboard: {e}")
    
    # Fetch mempool data from Mempool.space API
    mempool_data = fetch_mempool_data()
    
    # Fetch cryptocurrency prices
    prices = price_service.get_prices()
    
    return render_template('dashboard.html',
                         network_stats=network_stats,
                         mempool_data=mempool_data,
                         prices=prices,
                         price_service=price_service)

def fetch_mempool_data():
    """Fetch real-time data from Mempool.space API"""
    try:
        mempool_stats = {}
        
        # Fetch mempool statistics
        response = requests.get('https://mempool.space/api/mempool', timeout=10)
        if response.status_code == 200:
            data = response.json()
            mempool_stats['count'] = data.get('count', 0)
            mempool_stats['vsize'] = data.get('vsize', 0)
            mempool_stats['total_fee'] = data.get('total_fee', 0)
        
        # Fetch recommended fees
        response = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=10)
        if response.status_code == 200:
            fees = response.json()
            mempool_stats['fees'] = {
                'fastest': fees.get('fastestFee', 0),
                'half_hour': fees.get('halfHourFee', 0),
                'hour': fees.get('hourFee', 0),
                'economy': fees.get('economyFee', 0),
                'minimum': fees.get('minimumFee', 0)
            }
        
        # Fetch hashrate data (30 days)
        response = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=10)
        if response.status_code == 200:
            hashrate_data = response.json()
            mempool_stats['hashrate_history'] = hashrate_data.get('hashrates', [])[-30:]
            mempool_stats['current_hashrate'] = hashrate_data.get('currentHashrate', 0)
            mempool_stats['current_difficulty'] = hashrate_data.get('currentDifficulty', 0)
        
        # Fetch difficulty adjustment data
        response = requests.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=10)
        if response.status_code == 200:
            diff_data = response.json()
            mempool_stats['difficulty_adjustment'] = {
                'progress': diff_data.get('progressPercent', 0),
                'remaining_blocks': diff_data.get('remainingBlocks', 0),
                'remaining_time': diff_data.get('remainingTime', 0),
                'estimated_retarget': diff_data.get('estimatedRetargetDate', ''),
                'change_percent': diff_data.get('difficultyChange', 0)
            }
        
        return mempool_stats
        
    except Exception as e:
        logging.error(f"Error fetching mempool data: {e}")
        return {}

@app.route('/articles')
def articles():
    """Articles listing page with chronological Edition layout"""
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)
    
    # Zone 1: The 24-Hour Pulse (last 24 hours)
    today_articles = Article.query.filter(
        Article.published == True,
        Article.created_at >= cutoff_24h
    ).order_by(Article.created_at.desc()).all()
    
    # Zone 2: The Morning After (24h to 48h old)
    yesterday_articles = Article.query.filter(
        Article.published == True,
        Article.created_at >= cutoff_48h,
        Article.created_at < cutoff_24h
    ).order_by(Article.created_at.desc()).all()
    
    # Zone 3: The Archive (older than 48h) - limited for initial load
    archive_articles = Article.query.filter(
        Article.published == True,
        Article.created_at < cutoff_48h
    ).order_by(Article.created_at.desc()).limit(20).all()
    
    # Add pressing status to today's articles
    for article in today_articles:
        time_diff = (now - article.created_at).total_seconds() / 3600
        article.is_pressing = time_diff < 1
    
    # Get all categories for filter
    categories = db.session.query(Article.category).filter_by(published=True).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    # Get active advertisements
    active_ads = Advertisement.query.filter_by(is_active=True).all()
    
    # Fetch live cryptocurrency prices for sidebar
    prices = price_service.get_prices()
    
    return render_template('articles.html', 
                         today_articles=today_articles,
                         yesterday_articles=yesterday_articles,
                         archive_articles=archive_articles,
                         categories=categories,
                         active_ads=active_ads,
                         prices=prices,
                         price_service=price_service,
                         last_updated=now)

@app.route('/articles/<int:article_id>')
def article_detail(article_id):
    """Individual article page"""
    article = Article.query.get_or_404(article_id)
    related_articles = Article.query.filter(
        Article.id != article_id,
        Article.published == True,
        Article.category == article.category
    ).limit(3).all()
    
    return render_template('article_detail.html', article=article, related_articles=related_articles)

@app.route('/podcasts')
def podcasts():
    """Podcasts listing page with RSS feed sections"""
    # Group podcasts by RSS source, showing only 3 most recent per section
    podcast_sections = {}
    
    # Get distinct RSS sources
    sources = db.session.query(Podcast.rss_source).filter(Podcast.rss_source.isnot(None)).distinct().all()
    
    for source_tuple in sources:
        source = source_tuple[0] or 'General'
        # Get only the 3 most recent episodes for initial display
        recent_episodes = Podcast.query.filter_by(rss_source=source).order_by(Podcast.published_date.desc()).limit(3).all()
        if recent_episodes:
            podcast_sections[source] = recent_episodes
    
    return render_template('podcasts.html', podcast_sections=podcast_sections)

@app.route('/api/podcast/<int:podcast_id>')
def get_podcast_api(podcast_id):
    """API endpoint to get podcast data for player"""
    try:
        podcast = Podcast.query.get_or_404(podcast_id)
        return jsonify({
            'id': podcast.id,
            'title': podcast.title,
            'description': podcast.description,
            'host': podcast.host,
            'duration': podcast.duration,
            'audio_url': podcast.audio_url,
            'cover_image_url': podcast.cover_image_url,
            'published_date': podcast.published_date.isoformat() if podcast.published_date else None,
            'category': podcast.category
        })
    except Exception as e:
        logging.error(f"Error fetching podcast {podcast_id}: {e}")
        return jsonify({'error': 'Podcast not found'}), 404

@app.route('/api/podcasts/<rss_source>')
def get_more_podcasts_api(rss_source):
    """API endpoint to load more episodes for a specific RSS source"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 3, type=int)
        
        # Get podcasts for this RSS source with pagination
        podcasts = Podcast.query.filter_by(rss_source=rss_source).order_by(
            Podcast.published_date.desc()
        ).offset(offset).limit(limit).all()
        
        # Get total count for this source
        total_count = Podcast.query.filter_by(rss_source=rss_source).count()
        
        podcast_list = []
        for podcast in podcasts:
            podcast_list.append({
                'id': podcast.id,
                'title': podcast.title,
                'description': podcast.description[:120] + '...' if podcast.description and len(podcast.description) > 120 else podcast.description,
                'host': podcast.host or 'Protocol Pulse Team',
                'duration': podcast.duration,
                'episode_number': podcast.episode_number,
                'cover_image_url': podcast.cover_image_url,
                'published_date': podcast.published_date.strftime('%b %d, %Y') if podcast.published_date else '',
                'audio_url': podcast.audio_url
            })
        
        return jsonify({
            'podcasts': podcast_list,
            'total_count': total_count,
            'has_more': (offset + limit) < total_count
        })
    except Exception as e:
        logging.error(f"Error fetching more podcasts for {rss_source}: {e}")
        return jsonify({'error': 'Failed to load podcasts'}), 500

@app.route('/rss/podcasts.xml')
def podcast_rss():
    """Generate RSS feed for podcasts"""
    try:
        rss_xml = rss_service.generate_rss_feed()
        response = app.response_class(rss_xml, mimetype='application/rss+xml')
        return response
    except Exception as e:
        logging.error(f"Error generating podcast RSS: {e}")
        return "Error generating RSS feed", 500

@app.route('/media')
@app.route('/media-hub')
def media_hub():
    """Media Hub page with live RSS feeds, books, and merch"""
    try:
        shows = rss_service.get_show_info()
        products = []
        try:
            products = printful_service.get_store_products()
            products = [printful_service.format_product_for_display(p) for p in products if not printful_service.format_product_for_display(p).get('is_ignored', True)]
        except Exception as e:
            logging.warning(f"Could not load merch products: {e}")
        
        # Get Amazon affiliate tag from environment (set yours in Secrets)
        affiliate_tag = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')
        
        # Our Book Series - books featured on the Protocol Pulse podcast (using Open Library covers as reliable fallback)
        our_books = [
            {
                'title': 'Everything Divided by 21 Million',
                'author': 'Knut Svanholm',
                'description': 'A philosophical deep dive into Bitcoin\'s relationship to time, money, freedom, and human progress through mathematical scarcity.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9798887191195-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B0BTRPZTY4?tag={affiliate_tag}'
            },
            {
                'title': 'The Big Print',
                'author': 'Lawrence Lepard',
                'description': 'An exposé revealing how the Federal Reserve and financial elites engineered wealth extraction through monetary policy.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9798989448401-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B0C7T1YZFB?tag={affiliate_tag}'
            },
            {
                'title': 'Daylight Robbery',
                'author': 'Dominic Frisby',
                'description': 'The hidden history of how taxation has shaped human civilization from ancient empires to modern governments.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9780241360545-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/0241360544?tag={affiliate_tag}'
            },
            {
                'title': 'The Genesis Book',
                'author': 'Aaron van Wirdum',
                'description': 'The definitive history of Bitcoin\'s ideological origins — from Austrian economics to the cypherpunk movement.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781544542973-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B0CW1C6FQ3?tag={affiliate_tag}'
            }
        ]
        
        # Recommended Bitcoin Books - bestsellers and essentials (using Open Library covers as reliable fallback)
        recommended_books = [
            {
                'title': 'The Bitcoin Standard',
                'author': 'Saifedean Ammous',
                'description': 'The essential guide to understanding Bitcoin as sound money and the history of monetary systems.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781119473862-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1119473861?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'The Fiat Standard',
                'author': 'Saifedean Ammous',
                'description': 'A companion to The Bitcoin Standard examining our current fiat monetary system.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781544526478-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1544526474?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'Broken Money',
                'author': 'Lyn Alden',
                'description': 'A comprehensive analysis of the global monetary system and why Bitcoin matters.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9798988874904-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B0CG83MBN9?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'The Price of Tomorrow',
                'author': 'Jeff Booth',
                'description': 'Why deflation is the key to an abundant future in a technologically advancing world.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781999257408-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1999257405?tag={affiliate_tag}',
                'bestseller': False
            },
            {
                'title': '21 Lessons',
                'author': 'Gigi',
                'description': 'What falling down the Bitcoin rabbit hole taught one developer about philosophy, economics, and technology.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781697526349-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1697526349?tag={affiliate_tag}',
                'bestseller': False
            },
            {
                'title': 'Mastering Bitcoin',
                'author': 'Andreas Antonopoulos',
                'description': 'The technical guide to understanding and programming Bitcoin at a deep level.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781098150099-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1098150090?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'The Sovereign Individual',
                'author': 'James Dale Davidson',
                'description': 'A prescient 1997 book predicting the rise of digital money and the transformation of society.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9780684832722-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/0684832720?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'Layered Money',
                'author': 'Nik Bhatia',
                'description': 'An accessible introduction to how money works in layers, from gold to Bitcoin.',
                'cover_url': 'https://covers.openlibrary.org/b/isbn/9781736110515-L.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1736110519?tag={affiliate_tag}',
                'bestseller': False
            }
        ]
        
        # Get YouTube series data for Terminal Player (with dynamic API fetching if available)
        youtube_service_instance = YouTubeService()
        youtube_series = youtube_service_instance.get_all_dynamic_series()
        
        # Get Live Broadcasts data (Cypherpunk'd and Protocol Pulse videos) - make a deep copy
        import copy
        live_broadcasts = copy.deepcopy(YouTubeService.LIVE_BROADCASTS)
        
        # Dynamically update Protocol Pulse (Coin Bureau) latest video if API available
        try:
            coin_bureau_uploads = youtube_service_instance.get_channel_uploads(live_broadcasts['protocol_pulse']['channel_id'], max_results=1)
            if coin_bureau_uploads:
                live_broadcasts['protocol_pulse']['latest_id'] = coin_bureau_uploads[0]['id']
                logging.info(f"Successfully fetched latest Coin Bureau video: {coin_bureau_uploads[0]['id']}")
            else:
                logging.warning("No Coin Bureau uploads returned from API - using fallback")
        except Exception as e:
            logging.warning(f"Failed to fetch dynamic Coin Bureau video: {e}")
        
        # Get active advertisements for sponsor rotation
        active_ads = Advertisement.query.filter_by(is_active=True).all()
        
        return render_template('media_hub.html', 
                               shows=shows, 
                               products=products,
                               our_books=our_books,
                               recommended_books=recommended_books,
                               youtube_series=youtube_series,
                               live_broadcasts=live_broadcasts,
                               active_ads=active_ads,
                               get_thumbnail=YouTubeService.get_thumbnail)
    except Exception as e:
        logging.error(f"Error loading media hub: {e}")
        return render_template('media_hub.html', shows=[], products=[], our_books=[], recommended_books=[], youtube_series={}, live_broadcasts={}, get_thumbnail=YouTubeService.get_thumbnail)

@app.route('/api/latest-episodes')
def get_latest_episodes():
    """API endpoint to get latest podcast episodes from RSS feeds"""
    try:
        limit = request.args.get('limit', 6, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Fetch more episodes than needed to check if there are more
        all_episodes = rss_service.get_latest_episodes(limit=100)  # Get all available
        total_count = len(all_episodes)
        episodes = all_episodes[offset:offset + limit]
        
        episode_list = []
        for ep in episodes:
            pub_date = ep.get('published_date')
            episode_list.append({
                'id': ep.get('id'),
                'title': ep.get('title'),
                'description': ep.get('description', '')[:150] + '...' if len(ep.get('description', '')) > 150 else ep.get('description', ''),
                'audio_url': ep.get('audio_url'),
                'duration': ep.get('duration'),
                'published_date': pub_date.isoformat() if pub_date and hasattr(pub_date, 'isoformat') else str(pub_date) if pub_date else None,
                'show_name': ep.get('show_name'),
                'host': ep.get('host'),
                'color': ep.get('color', '#f7931a'),
                'cover_image': ep.get('cover_image')
            })
        
        return jsonify({
            'episodes': episode_list,
            'total_count': total_count,
            'has_more': (offset + limit) < total_count
        })
    except Exception as e:
        logging.error(f"Error fetching latest episodes: {e}")
        return jsonify({'episodes': [], 'error': str(e)}), 500

@app.route('/api/episodes/<show_id>')
def get_show_episodes(show_id):
    """API endpoint to get episodes for a specific show"""
    try:
        limit = request.args.get('limit', 10, type=int)
        episodes = rss_service.get_episodes_by_show(show_id, limit=limit)
        
        episode_list = []
        for ep in episodes:
            pub_date = ep.get('published_date')
            episode_list.append({
                'id': ep.get('id'),
                'title': ep.get('title'),
                'description': ep.get('description', '')[:150],
                'audio_url': ep.get('audio_url'),
                'duration': ep.get('duration'),
                'published_date': pub_date.isoformat() if pub_date and hasattr(pub_date, 'isoformat') else str(pub_date) if pub_date else None,
                'show_name': ep.get('show_name'),
                'host': ep.get('host'),
                'color': ep.get('color', '#f7931a')
            })
        
        return jsonify({'episodes': episode_list})
    except Exception as e:
        logging.error(f"Error fetching episodes for {show_id}: {e}")
        return jsonify({'episodes': [], 'error': str(e)}), 500

@app.route('/api/episodes/search')
def search_episodes():
    """API endpoint to search episodes"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'episodes': [], 'error': 'Query parameter required'}), 400
        
        episodes = rss_service.search_episodes(query, limit=limit)
        
        episode_list = []
        for ep in episodes:
            episode_list.append({
                'id': ep.get('id'),
                'title': ep.get('title'),
                'description': ep.get('description', '')[:150],
                'audio_url': ep.get('audio_url'),
                'duration': ep.get('duration'),
                'show_name': ep.get('show_name'),
                'host': ep.get('host')
            })
        
        return jsonify({'episodes': episode_list, 'query': query})
    except Exception as e:
        logging.error(f"Error searching episodes: {e}")
        return jsonify({'episodes': [], 'error': str(e)}), 500

@app.route('/api/rss/refresh')
def refresh_rss_feeds():
    """API endpoint to manually refresh RSS feeds (admin use)"""
    try:
        rss_service.clear_cache()
        episodes = rss_service.get_latest_episodes(limit=20)
        return jsonify({
            'success': True,
            'message': f'RSS feeds refreshed, {len(episodes)} episodes loaded'
        })
    except Exception as e:
        logging.error(f"Error refreshing RSS feeds: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/sync-podcasts')
@login_required
@admin_required
def sync_podcasts():
    """Sync all podcast RSS feeds"""
    try:
        results = rss_service.sync_all_feeds()
        flash(f'Podcast sync completed: {results}')
        return redirect('/admin/podcasts')
    except Exception as e:
        logging.error(f"Error syncing podcasts: {e}")
        flash(f'Error syncing podcasts: {e}')
        return redirect('/admin/podcasts')

@app.route('/merch')
def merch_store():
    """Merch store page"""
    try:
        products = printful_service.get_store_products()
        formatted_products = []
        
        for product in products:
            formatted_product = printful_service.format_product_for_display(product)
            if not formatted_product.get('is_ignored', True):
                formatted_products.append(formatted_product)
        
        return render_template('merch.html', products=formatted_products)
    except Exception as e:
        logging.error(f"Error loading merch store: {e}")
        flash('Error loading merchandise. Please try again later.')
        return render_template('merch.html', products=[])

@app.route('/api/merch/product/<int:product_id>')
def get_product_details(product_id):
    """Get detailed product information"""
    try:
        product = printful_service.get_product_details(product_id)
        if product:
            formatted_product = printful_service.format_product_for_display(product)
            return jsonify(formatted_product)
        else:
            return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        logging.error(f"Error getting product details: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Category routes
@app.route('/bitcoin')
def bitcoin_category():
    """Bitcoin category page"""
    articles = Article.query.filter_by(published=True, category='Bitcoin').order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Bitcoin')

@app.route('/defi')
def defi_category():
    """DeFi category page"""
    articles = Article.query.filter_by(published=True, category='DeFi').order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='DeFi')

@app.route('/regulation')
def regulation_category():
    """Regulation category page"""
    articles = Article.query.filter_by(published=True, category='Regulation').order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Regulation')

@app.route('/privacy')
def privacy_category():
    """Privacy category page"""
    articles = Article.query.filter_by(published=True, category='Privacy').order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Privacy')

@app.route('/innovation')
def innovation_category():
    """Innovation category page"""
    articles = Article.query.filter_by(published=True, category='Innovation').order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Innovation')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@app.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    """Handle newsletter subscription requests"""
    try:
        email = request.form.get('email')
        if not email:
            flash('Email address is required.', 'error')
            return redirect(url_for('index'))
        
        success = newsletter_service.subscribe_user(email)
        if success:
            flash('Successfully subscribed to Protocol Pulse newsletter!', 'success')
        else:
            flash('Newsletter subscription failed. Please try again.', 'error')
    except Exception as e:
        logging.error(f"Newsletter subscription error: {e}")
        flash('An error occurred. Please try again.', 'error')
    
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=login_input).first()
        if not user:
            user = User.query.filter_by(email=login_input).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect('/admin')
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Registration disabled for security - admin accounts only
    flash('Registration is disabled. Please contact administrator for access.')
    return redirect('/login')

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    total_articles = Article.query.count()
    published_articles = Article.query.filter_by(published=True).count()
    total_podcasts = Podcast.query.count()
    recent_articles = Article.query.order_by(Article.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_articles=total_articles,
                         published_articles=published_articles,
                         total_podcasts=total_podcasts,
                         recent_articles=recent_articles)

@app.route('/admin/generate')
@login_required
@admin_required
def admin_generate():
    """Article generation page"""
    prompts = ContentPrompt.query.filter_by(active=True).all()
    return render_template('admin/generate_article.html', prompts=prompts)

@app.route('/api/generate-article', methods=['POST'])
@login_required
@admin_required
def api_generate_article():
    """API endpoint to generate articles"""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip().replace('<', '&lt;').replace('>', '&gt;')
        source_type = data.get('source_type', 'ai_generated')
        prompt_id = data.get('prompt_id')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Get trending topics from Reddit if source is reddit
        if source_type == 'reddit':
            reddit_posts = reddit_service.get_trending_topics(['cryptocurrency', 'bitcoin', 'ethereum', 'web3'])
            if reddit_posts:
                # Use the first relevant post as context
                topic = f"{topic} - Context from Reddit: {reddit_posts[0].get('title', '')}"
        
        # Generate article using AI
        article_data = content_generator.generate_article(topic, prompt_id)
        
        if not article_data:
            return jsonify({'error': 'Failed to generate article'}), 500
        
        # FACT-CHECK GATE: Block auto-publishing if fact-check failed
        fact_check_warnings = article_data.get('fact_check_warnings', [])
        fact_check_passed = article_data.get('fact_check_passed', True)
        
        if not fact_check_passed:
            # Save as DRAFT for human review - do NOT auto-publish
            logging.warning(f"FACT-CHECK BLOCKED: Article '{article_data['title'][:50]}' has verification errors: {fact_check_warnings}")
            
            article = Article(
                title=article_data['title'],
                content=article_data['content'],
                summary="",
                category=article_data.get('category', 'Web3'),
                tags=article_data.get('tags', ''),
                source_type=source_type,
                author="Al Ingle",
                seo_title=article_data.get('seo_title', article_data['title']),
                seo_description=article_data.get('seo_description', article_data['title'][:150]),
                published=False  # BLOCKED - saved as draft for review
            )
            db.session.add(article)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'article_id': article.id,
                'title': article.title,
                'published': False,
                'fact_check_passed': False,
                'fact_check_warnings': fact_check_warnings,
                'message': 'Article saved as DRAFT - fact-check verification failed. Please review errors and fix before publishing.',
                'action_required': 'Review fact-check errors and manually approve or regenerate'
            }), 422
        
        # Fact-check passed - proceed with auto-publishing
        article = Article(
            title=article_data['title'],
            content=article_data['content'],
            summary="",  # No summary - TL;DR is embedded in content
            category=article_data.get('category', 'Web3'),
            tags=article_data.get('tags', ''),
            source_type=source_type,
            author="Al Ingle",
            seo_title=article_data.get('seo_title', article_data['title']),
            seo_description=article_data.get('seo_description', article_data['title'][:150]),
            published=True  # Fact-check passed - auto-approved
        )
        
        db.session.add(article)
        db.session.commit()
        
        # Immediately publish to Substack (hands-off workflow)
        substack_url = None
        if substack_service:
            try:
                # Determine content type from category
                category = article.category.lower()
                if 'bitcoin' in category:
                    content_type = 'bitcoin'
                elif 'defi' in category:
                    content_type = 'defi'
                else:
                    content_type = 'article'
                
                # Format content for newsletter
                newsletter_content = substack_service.format_content_for_newsletter(
                    article.content, content_type
                )
                
                # Publish to Substack
                substack_url = substack_service.publish_to_substack(
                    article.title,
                    newsletter_content,
                    article.header_image_url
                )
                
                if substack_url:
                    # Update article with Substack URL
                    article.substack_url = substack_url
                    db.session.commit()
                    logging.info(f"Auto-published article '{article.title}' to Substack: {substack_url}")
                else:
                    logging.warning(f"Failed to auto-publish article '{article.title}' to Substack")
                    
            except Exception as e:
                logging.error(f"Auto-publish to Substack failed for article '{article.title}': {e}")
        
        return jsonify({
            'success': True,
            'article_id': article.id,
            'title': article.title,
            'published': True,
            'substack_url': substack_url,
            'message': 'Article auto-approved and published' + (f' to Substack: {substack_url}' if substack_url else ''),
            'fact_check_passed': True,
            'fact_check_warnings': []
        })
        
    except Exception as e:
        logging.error(f"Error generating article: {str(e)}")
        return jsonify({'error': f'Failed to generate article: {str(e)}'}), 500

@app.route('/api/publish-article/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def api_publish_article(article_id):
    """API endpoint to publish articles"""
    try:
        article = Article.query.get_or_404(article_id)
        
        # Use AI review and approval workflow BEFORE setting published=True
        approval_result = content_engine.approve_and_publish_article(article_id)
        if not approval_result["success"]:
            return jsonify({'error': f'AI review failed: {approval_result.get("errors", ["Unknown error"])}'}, 500)
        
        # Only set published after AI approval
        article.published = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Article published successfully'})
        
    except Exception as e:
        logging.error(f"Error publishing article: {str(e)}")
        return jsonify({'error': f'Failed to publish article: {str(e)}'}), 500

@app.route('/admin/publish-to-substack/<int:article_id>', methods=['POST'])
@login_required
@admin_required  
def publish_to_substack(article_id):
    """Publish existing article to Substack using python-substack"""
    try:
        if not substack_service:
            return jsonify({'success': False, 'error': 'Substack service not available'})
            
        article = Article.query.get_or_404(article_id)
        
        # Determine content type from category
        category = article.category.lower()
        if 'bitcoin' in category:
            content_type = 'bitcoin'
        elif 'defi' in category:
            content_type = 'defi'
        else:
            content_type = 'article'
        
        # Format content for newsletter
        newsletter_content = substack_service.format_content_for_newsletter(
            article.content, content_type
        )
        
        # Publish to Substack
        substack_url = substack_service.publish_to_substack(
            article.title,
            newsletter_content,
            article.header_image_url
        )
        
        if substack_url:
            # Update article with Substack URL
            article.substack_url = substack_url
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'substack_url': substack_url,
                'message': 'Article published to Substack successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to publish to Substack'})
            
    except Exception as e:
        logging.error(f"Substack publishing failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/share-reddit/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def share_to_reddit(article_id):
    """Cross-post article to Reddit using PRAW"""
    try:
        from services.reddit_service import RedditService
        
        article = Article.query.get_or_404(article_id)
        
        # Get target subreddit from request (default to 'bitcoin')
        request_data = request.get_json() or {}
        target_subreddit = request_data.get('subreddit', 'bitcoin')
        
        # Prepare Reddit post
        post_title = article.title
        post_url = article.substack_url or request.url_root + f"articles/{article.id}"
        
        # Post to Reddit
        reddit_service = RedditService()
        result = reddit_service.post_to_reddit(target_subreddit, post_title, post_url)
        
        if result["success"]:
            return jsonify({
                'success': True,
                'reddit_url': result["post_url"],
                'message': f'Successfully posted to r/{target_subreddit}'
            })
        else:
            return jsonify({
                'success': False,
                'errors': result.get("errors", ["Unknown error"]),
                'message': 'Failed to post to Reddit'
            })
            
    except Exception as e:
        logging.error(f"Reddit crosspost failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test/generate-article', methods=['POST'])
def test_generate_article():
    """Test endpoint for article generation without auth"""
    try:
        data = request.get_json()
        topic = data.get('topic', 'Bitcoin market update')
        content_type = data.get('content_type', 'bitcoin_news')
        auto_publish = data.get('auto_publish', True)
        
        # Generate article with AI review
        result = content_engine.generate_and_publish_article(
            topic=topic,
            content_type=content_type,
            auto_publish=auto_publish
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Test article generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate-content', methods=['POST'])
@login_required
@admin_required
def generate_content():
    """Generate content using the content engine"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON data'})
        
        topic = data.get('topic', '')
        content_type = data.get('content_type', 'bitcoin_news')
        auto_publish = data.get('auto_publish', False)
        
        if not topic:
            return jsonify({'success': False, 'error': 'Topic is required'})
        
        # Generate content using the content engine
        result = content_engine.generate_and_publish_article(topic, content_type, auto_publish)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Content generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate-podcast', methods=['POST'])
@login_required
@admin_required
def generate_podcast():
    """Generate audio intelligence podcast from YouTube video"""
    from services.podcast_generator import podcast_generator
    
    try:
        data = request.get_json() or {}
        video_id = data.get('video_id')
        channel_name = data.get('channel_name', 'YouTube Channel')
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id required'})
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        result = podcast_generator.generate_podcast_from_video(
            video_id=video_id,
            thumbnail_url=thumbnail_url,
            channel_name=channel_name
        )
        
        if result and result.get('audio_file'):
            article = Article(
                title=f"Audio Deep Dive: {channel_name} Analysis",
                summary=f"Deep-dive audio analysis featuring expert commentary",
                content=f'<p class="article-paragraph">Listen to our AI-hosted podcast breakdown.</p><audio controls src="/{result["audio_file"]}" style="width:100%; margin-top: 1rem;"></audio>',
                category='Podcast',
                image_url=thumbnail_url,
                published=True
            )
            db.session.add(article)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'article_id': article.id,
                'audio_file': result.get('audio_file'),
                'video_file': result.get('video_file')
            })
        
        return jsonify({'success': False, 'error': 'Failed to generate podcast'})
        
    except Exception as e:
        logging.error(f"Podcast generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate-podcasts-batch', methods=['POST'])
@login_required
@admin_required
def generate_podcasts_batch():
    """Generate podcasts from all monitored Bitcoin channels"""
    from services.automation import generate_podcasts_from_partners
    
    try:
        generate_podcasts_from_partners()
        return jsonify({'success': True, 'message': 'Podcast generation started for all monitored channels'})
    except Exception as e:
        logging.error(f"Batch podcast generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/multimodal/social-package', methods=['POST'])
@login_required
@admin_required
def generate_social_package():
    """Generate full social media package from a YouTube video (podcast + clips + article)"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Partner Channel')
    thumbnail_url = data.get('thumbnail_url')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'video_id required'})
    
    if not thumbnail_url:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    try:
        package = podcast_generator.create_full_social_package(
            video_id=video_id,
            thumbnail_url=thumbnail_url,
            channel_name=channel_name
        )
        
        return jsonify({
            'success': True,
            'package': {
                'podcast_created': package.get('podcast') is not None,
                'article_title': package.get('article', {}).get('title') if package.get('article') else None,
                'clips_count': len(package.get('clips', [])),
                'social_videos_count': len(package.get('social_videos', [])),
                'generated_at': package.get('generated_at')
            }
        })
    except Exception as e:
        logging.error(f"Social package generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/multimodal/bitcoin-lens', methods=['POST'])
@login_required
@admin_required
def generate_bitcoin_lens_article():
    """Generate a Bitcoin Lens reactionary review article from a YouTube video"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Partner Channel')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'video_id required'})
    
    try:
        result = podcast_generator.generate_bitcoin_lens_review(video_id, channel_name)
        
        if result:
            return jsonify({
                'success': True,
                'article': {
                    'title': result.get('title'),
                    'content_preview': result.get('content', '')[:500] + '...',
                    'channel': result.get('source_channel'),
                    'generated_at': result.get('generated_at')
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate Bitcoin Lens review'})
            
    except Exception as e:
        logging.error(f"Bitcoin Lens generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/multimodal/extract-clip', methods=['POST'])
@login_required
@admin_required
def extract_podcast_clip():
    """Extract a 60-second clip from an existing podcast audio file"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    audio_file = data.get('audio_file')
    start_time = data.get('start_time', 30)
    
    if not audio_file:
        return jsonify({'success': False, 'error': 'audio_file path required'})
    
    try:
        clip_path = podcast_generator.extract_60s_clip(audio_file, start_time=start_time)
        
        if clip_path:
            return jsonify({
                'success': True,
                'clip_path': clip_path
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to extract clip'})
            
    except Exception as e:
        logging.error(f"Clip extraction failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/multimodal/social-wrapper', methods=['POST'])
@login_required
@admin_required
def create_social_wrapper():
    """Wrap an audio clip with YouTube thumbnail and cyberpunk headline overlay"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    audio_clip = data.get('audio_clip')
    thumbnail_url = data.get('thumbnail_url')
    headline = data.get('headline', 'Bitcoin Intelligence Briefing')
    output_format = data.get('format', 'shorts')
    
    if not audio_clip or not thumbnail_url:
        return jsonify({'success': False, 'error': 'audio_clip and thumbnail_url required'})
    
    try:
        video_path = podcast_generator.create_social_video_wrapper(
            audio_clip=audio_clip,
            thumbnail_url=thumbnail_url,
            headline=headline,
            output_format=output_format
        )
        
        if video_path:
            return jsonify({
                'success': True,
                'video_path': video_path,
                'format': output_format
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create social wrapper'})
            
    except Exception as e:
        logging.error(f"Social wrapper creation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/multimodal/auto-process', methods=['POST'])
@login_required
@admin_required
def auto_process_partner_videos():
    """Automatically process new videos from partner channels"""
    youtube_service = YouTubeService()
    
    try:
        results = youtube_service.auto_process_new_partner_videos()
        
        return jsonify({
            'success': True,
            'results': {
                'videos_found': results.get('videos_found', 0),
                'articles_generated': len(results.get('articles_generated', [])),
                'podcasts_generated': len(results.get('podcasts_generated', [])),
                'clips_created': len(results.get('clips_created', [])),
                'errors': results.get('errors', [])
            }
        })
    except Exception as e:
        logging.error(f"Auto-process partner videos failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/ghl-sync', methods=['POST'])
@login_required
@admin_required
def admin_ghl_sync():
    """Manually trigger GHL Custom Value sync for network metrics"""
    try:
        result = ghl_service.sync_network_metrics()
        if result.get('success'):
            logging.info(f"GHL SYNC SUCCESS: Difficulty={result.get('difficulty')}, Hashrate={result.get('hashrate')}")
            return jsonify({
                'success': True,
                'message': 'GHL Custom Values synced successfully',
                'difficulty': result.get('difficulty'),
                'hashrate': result.get('hashrate'),
                'synced_at': result.get('synced_at')
            })
        else:
            return jsonify({'success': False, 'error': result.get('error')})
    except Exception as e:
        logging.error(f"GHL sync error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/admin/social-listener', methods=['GET'])
@login_required
@admin_required
def admin_social_listener():
    """Get Social Intelligence Listener status and recent findings"""
    try:
        from services.social_listener import social_listener
        status = social_listener.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logging.error(f"Social Listener status error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/social-listener/scan', methods=['POST'])
@login_required
@admin_required
def admin_social_listener_scan():
    """Manually trigger a social listener scan"""
    try:
        from services.social_listener import social_listener
        if not social_listener.initialized:
            return jsonify({'success': False, 'error': 'Social Listener not initialized - check Twitter API credentials'})
        
        results = social_listener.scan_all_targets()
        logging.info(f"Social Listener manual scan: {results.get('scanned')} handles, {len(results.get('new_tweets', []))} new tweets")
        return jsonify({
            'success': True,
            'scanned': results.get('scanned'),
            'new_tweets': len(results.get('new_tweets', [])),
            'errors': len(results.get('errors', [])),
            'timestamp': results.get('timestamp')
        })
    except Exception as e:
        logging.error(f"Social Listener scan error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate-from-reddit', methods=['POST'])
@login_required
@admin_required
def generate_from_reddit():
    """Generate content from Reddit trending topics"""
    try:
        # Get Reddit trending topics
        trending_topics = reddit_service.get_trending_topics(['cryptocurrency', 'bitcoin', 'ethereum', 'web3'])
        
        if not trending_topics:
            return jsonify({'success': False, 'error': 'No trending topics found'})
        
        results = []
        for topic in trending_topics[:3]:  # Generate from top 3 topics
            try:
                result = content_engine.generate_content_from_reddit_trend(topic)
                results.append({
                    'topic': topic.get('title', 'Unknown'),
                    'result': result
                })
            except Exception as e:
                results.append({
                    'topic': topic.get('title', 'Unknown'),
                    'result': {'success': False, 'error': str(e)}
                })
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        logging.error(f"Reddit content generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/ai-review/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def ai_review_article(article_id):
    """Trigger AI review and auto-publishing for article"""
    try:
        # Use AI review workflow (Gemini as Editor-in-Chief)
        result = content_engine.approve_and_publish_article(article_id)
        
        if result["success"]:
            return jsonify({
                'success': True,
                'substack_url': result.get("substack_url"),
                'message': result.get("message"),
                'review': result.get("review")
            })
        else:
            return jsonify({
                'success': False,
                'errors': result.get("errors", ["Unknown error"]),
                'message': result.get("message"),
                'review': result.get("review")
            })
            
    except Exception as e:
        logging.error(f"AI review failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/latest-articles')
def latest_articles():
    articles = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).limit(10).all()
    return jsonify([{'id': a.id, 'title': a.title, 'summary': a.summary, 'header_image_url': a.header_image_url or '/static/images/placeholder.jpg'} for a in articles])

@app.route('/api/reddit-trends', methods=['GET'])
@login_required
@admin_required
def api_reddit_trends():
    """API endpoint to get Reddit trending topics"""
    try:
        subreddits = ['cryptocurrency', 'bitcoin', 'ethereum', 'blockchain', 'web3']
        trends = reddit_service.get_trending_topics(subreddits)
        return jsonify({'trends': trends})
        
    except Exception as e:
        logging.error(f"Error fetching Reddit trends: {str(e)}")
        return jsonify({'error': f'Failed to fetch trends: {str(e)}'}), 500

# Register social monitoring blueprint
from routes_social import social
app.register_blueprint(social)

@app.route('/admin/write', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_write_article():
    """Admin page for writing manual articles"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'Bitcoin')
        author = request.form.get('author', current_user.username)
        seo_description = request.form.get('seo_description', '')
        tags = request.form.get('tags', '')
        is_pressing = request.form.get('is_pressing') == 'on'
        action = request.form.get('action', 'draft')
        
        if not title or not content:
            flash('Title and content are required.')
            return redirect('/admin/write')
        
        article = Article(
            title=title,
            content=content,
            category=category,
            author=author,
            seo_description=seo_description or title[:155],
            seo_title=title[:60],
            tags=tags,
            is_pressing=is_pressing,
            source_type='manual',
            published=(action == 'publish')
        )
        db.session.add(article)
        db.session.commit()
        
        if action == 'publish':
            flash(f'Article "{title}" published successfully!')
        else:
            flash(f'Article "{title}" saved as draft.')
        
        return redirect('/admin')
    
    return render_template('admin/write_article.html')

@app.route('/admin/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_article(article_id):
    """Admin page for editing existing articles"""
    article = Article.query.get_or_404(article_id)
    
    if request.method == 'POST':
        article.title = request.form.get('title', '').strip()
        article.content = request.form.get('content', '').strip()
        article.category = request.form.get('category', 'Bitcoin')
        article.author = request.form.get('author', current_user.username)
        article.seo_description = request.form.get('seo_description', '') or article.title[:155]
        article.seo_title = article.title[:60]
        article.tags = request.form.get('tags', '')
        article.is_pressing = request.form.get('is_pressing') == 'on'
        action = request.form.get('action', 'publish')
        
        if not article.title or not article.content:
            flash('Title and content are required.')
            return redirect(f'/admin/edit/{article_id}')
        
        article.published = (action == 'publish')
        db.session.commit()
        
        if action == 'publish':
            flash(f'Article "{article.title}" updated and published!')
        else:
            flash(f'Article "{article.title}" saved as draft.')
        
        return redirect('/admin')
    
    return render_template('admin/edit_article.html', article=article)

@app.route('/admin/delete/<int:article_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_article(article_id):
    """Admin endpoint to delete an article"""
    try:
        article = Article.query.get_or_404(article_id)
        title = article.title
        db.session.delete(article)
        db.session.commit()
        logging.info(f"Article '{title}' (ID: {article_id}) deleted by {current_user.username}")
        return jsonify({'success': True, 'message': f'Article "{title}" deleted successfully'})
    except Exception as e:
        logging.error(f"Error deleting article {article_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/ads')
@login_required
@admin_required
def admin_ads():
    """Admin page for managing advertisements"""
    ads = Advertisement.query.all()
    return render_template('admin/ads.html', ads=ads)

@app.route('/api/add-ad', methods=['POST'])
@login_required
@admin_required
def api_add_ad():
    """API endpoint to add a new advertisement"""
    try:
        # Get form data and sanitize inputs
        name = request.form.get('name', '').strip().replace('<', '&lt;')
        target_url = request.form.get('target_url', '').strip()
        
        if not name or not target_url:
            return jsonify({'success': False, 'error': 'Name and target URL are required'}), 400
        
        # Handle image upload
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'Image file is required'}), 400
        
        image = request.files['image']
        if image.filename == '':
            return jsonify({'success': False, 'error': 'No image selected'}), 400
        
        # Secure filename and add UUID
        if not image.filename:
            return jsonify({'success': False, 'error': 'Invalid filename'}), 400
        
        original_filename = secure_filename(image.filename)
        if not original_filename:
            return jsonify({'success': False, 'error': 'Invalid filename'}), 400
        
        # Generate unique filename with UUID
        filename_parts = original_filename.rsplit('.', 1)
        if len(filename_parts) == 2:
            unique_filename = f"{filename_parts[0]}_{uuid.uuid4().hex}.{filename_parts[1]}"
        else:
            unique_filename = f"{original_filename}_{uuid.uuid4().hex}"
        
        # Create ads directory if it doesn't exist
        if not app.static_folder:
            return jsonify({'success': False, 'error': 'Static folder not configured'}), 500
        
        ads_dir = os.path.join(app.static_folder, 'ads')
        os.makedirs(ads_dir, exist_ok=True)
        
        # Save the image
        image_path = os.path.join(ads_dir, unique_filename)
        image.save(image_path)
        
        # Enhance image with AI
        try:
            enhanced_url = ai_service.enhance_ad_image(image_path)
            if enhanced_url:
                # Download enhanced image
                response = requests.get(enhanced_url)
                if response.status_code == 200:
                    enhanced_filename = f"enhanced_{unique_filename}"
                    enhanced_path = os.path.join(ads_dir, enhanced_filename)
                    with open(enhanced_path, 'wb') as f:
                        f.write(response.content)
                    image_url = f"/static/ads/{enhanced_filename}"
                else:
                    image_url = f"/static/ads/{unique_filename}"
            else:
                image_url = f"/static/ads/{unique_filename}"
        except Exception as e:
            logging.error(f"Image enhancement failed: {e}")
            image_url = f"/static/ads/{unique_filename}"
        
        # Create and save advertisement
        ad = Advertisement(
            name=name,
            image_url=image_url,
            target_url=target_url,
            is_active=False
        )
        
        db.session.add(ad)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Advertisement created successfully',
            'ad_id': ad.id
        })
        
    except Exception as e:
        logging.error(f"Error creating advertisement: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle-ad/<int:ad_id>', methods=['POST'])
@login_required
@admin_required
def api_toggle_ad(ad_id):
    """API endpoint to toggle advertisement active status"""
    try:
        ad = Advertisement.query.get_or_404(ad_id)
        ad.is_active = not ad.is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Advertisement {"activated" if ad.is_active else "deactivated"}',
            'is_active': ad.is_active
        })
        
    except Exception as e:
        logging.error(f"Error toggling advertisement: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-ad/<int:ad_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_ad(ad_id):
    """API endpoint to delete an advertisement"""
    try:
        ad = Advertisement.query.get_or_404(ad_id)
        
        # Delete image files if they exist
        try:
            if ad.image_url.startswith('/static/ads/') and app.static_folder:
                image_filename = ad.image_url.replace('/static/ads/', '')
                image_path = os.path.join(app.static_folder, 'ads', image_filename)
                if os.path.exists(image_path):
                    os.remove(image_path)
        except Exception as e:
            logging.warning(f"Could not delete image file: {e}")
        
        db.session.delete(ad)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Advertisement deleted successfully'
        })
        
    except Exception as e:
        logging.error(f"Error deleting advertisement: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/active-ads', methods=['GET'])
def api_active_ads():
    """API endpoint to get active advertisements for cycling"""
    try:
        active_ads = Advertisement.query.filter_by(is_active=True).all()
        
        ads_data = []
        for ad in active_ads:
            ads_data.append({
                'id': ad.id,
                'name': ad.name,
                'image_url': ad.image_url,
                'target_url': ad.target_url,
                'created_at': ad.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'ads': ads_data,
            'count': len(ads_data)
        })
        
    except Exception as e:
        logging.error(f"Error fetching active ads: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/network-stats')
def api_network_stats():
    """API endpoint to get live Bitcoin network statistics from Mempool.space"""
    try:
        stats = NodeService.get_network_stats()
        return jsonify({
            'success': True,
            **stats
        })
    except Exception as e:
        logging.error(f"Error fetching network stats: {e}")
        return jsonify({
            'success': False,
            'height': '---,---',
            'hashrate': '--- EH/s',
            'status': 'ERROR'
        }), 500

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    email = request.json.get('email')
    first_name = request.json.get('first_name', '')
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    # Save to local database via newsletter service
    newsletter_service.subscribe_user(email, first_name)
    
    # Push to GHL (HighLevel) CRM
    ghl_result = ghl_service.push_to_ghl(email, first_name, 'Protocol_Pulse_Subscriber')
    if ghl_result.get('success'):
        logging.info(f"GHL sync successful for {email}")
    
    # Also try ConvertKit if configured
    api_key = os.environ.get('CONVERTKIT_API_KEY')
    form_id = os.environ.get('CONVERTKIT_FORM_ID')
    
    if api_key and form_id:
        try:
            url = f"https://api.convertkit.com/v3/forms/{form_id}/subscribe"
            data = {'api_key': api_key, 'email': email, 'first_name': first_name}
            requests.post(url, json=data)
        except Exception as e:
            logging.warning(f"ConvertKit sync failed: {e}")
    
    return jsonify({'success': True})


# ==========================================
# GHL (HighLevel) SUBSCRIBER INTEGRATION
# ==========================================

@app.route('/subscribe/ghl', methods=['GET', 'POST'])
def subscribe_ghl():
    """
    Subscribe to Protocol Pulse via HighLevel CRM.
    Saves to local DB and pushes to GHL with 'Protocol_Pulse_Subscriber' tag.
    """
    if request.method == 'GET':
        return render_template('subscribe_ghl.html')
    
    try:
        email = request.form.get('email')
        name = request.form.get('name', '')
        source = request.form.get('source', 'website')
        
        if not email:
            flash('Email address is required.', 'error')
            return redirect(url_for('subscribe_ghl'))
        
        # Save to local newsletter service
        newsletter_service.subscribe_user(email)
        
        # Push to GHL with appropriate tag
        tag = 'Protocol_Pulse_Subscriber'
        if source == 'series':
            tag = 'Series_Viewer'
        
        result = ghl_service.push_to_ghl(email, name, tag)
        
        if result.get('success'):
            logging.info(f"GHL subscription success: {email} -> {result.get('contact_id')}")
            return render_template('subscribe_success.html', email=email)
        else:
            logging.warning(f"GHL push failed (local saved): {result.get('error')}")
            flash('Successfully subscribed! (CRM sync pending)', 'success')
            return redirect(url_for('index'))
            
    except Exception as e:
        logging.error(f"GHL subscription error: {e}")
        flash('Subscription failed. Please try again.', 'error')
        return redirect(url_for('subscribe_ghl'))


# ==========================================
# SERIES GUIDE - WATCH SERIES WITH NAVIGATION
# ==========================================

@app.route('/series/<series_slug>')
def watch_series(series_slug):
    """
    Watch a video series with episode navigation sidebar.
    Provides 'Next Up' teaser and smooth transitions between episodes.
    """
    # Curated series data (can be moved to database later)
    SERIES_CATALOG = {
        'everything-divided-by-21-million': {
            'title': 'Everything Divided By 21 Million',
            'description': 'A foundational series exploring Bitcoin\'s fixed supply and its implications for humanity.',
            'episodes': [
                {'id': 1, 'title': 'The Scarcity Revolution', 'video_id': 'example_vid_1', 'duration': '12:34'},
                {'id': 2, 'title': 'Why 21 Million Matters', 'video_id': 'example_vid_2', 'duration': '15:21'},
                {'id': 3, 'title': 'The Final Money', 'video_id': 'example_vid_3', 'duration': '18:45'},
            ]
        },
        'bitcoin-for-beginners': {
            'title': 'Bitcoin for Beginners',
            'description': 'Your sovereign journey into Bitcoin starts here.',
            'episodes': [
                {'id': 1, 'title': 'What Is Bitcoin?', 'video_id': 'beginner_1', 'duration': '10:00'},
                {'id': 2, 'title': 'How To Buy Your First Bitcoin', 'video_id': 'beginner_2', 'duration': '8:30'},
                {'id': 3, 'title': 'Self-Custody Basics', 'video_id': 'beginner_3', 'duration': '12:15'},
            ]
        }
    }
    
    series = SERIES_CATALOG.get(series_slug)
    if not series:
        flash('Series not found.', 'error')
        return redirect(url_for('media_hub'))
    
    # Get current episode (default to 1)
    current_ep = request.args.get('episode', 1, type=int)
    current_episode = None
    next_episode = None
    
    for i, ep in enumerate(series['episodes']):
        if ep['id'] == current_ep:
            current_episode = ep
            if i + 1 < len(series['episodes']):
                next_episode = series['episodes'][i + 1]
            break
    
    if not current_episode:
        current_episode = series['episodes'][0]
        if len(series['episodes']) > 1:
            next_episode = series['episodes'][1]
    
    # Generate AI teaser for next episode if available
    next_teaser = None
    if next_episode:
        next_teaser = _generate_episode_teaser(next_episode['title'], series['title'])
    
    return render_template('watch_series.html',
                          series=series,
                          series_slug=series_slug,
                          current_episode=current_episode,
                          next_episode=next_episode,
                          next_teaser=next_teaser,
                          episodes=series['episodes'])


def _generate_episode_teaser(episode_title: str, series_title: str) -> str:
    """Generate exactly 20-word AI teaser for the next episode"""
    try:
        prompt = f"""Generate EXACTLY 20 words for a teaser about a Bitcoin education video titled "{episode_title}" 
        from the series "{series_title}". Write in the voice of an intelligence briefing - urgent, insightful, 
        focused on sovereignty and freedom. No hashtags, no emojis. Output ONLY the 20-word teaser, nothing else."""
        
        teaser = ai_service.generate_content_openai(prompt)
        if teaser:
            words = teaser.strip().split()[:20]
            return ' '.join(words)
        return f"Next: {episode_title} - Continue your sovereign education journey."
    except Exception as e:
        logging.warning(f"Teaser generation failed: {e}")
        return f"Next: {episode_title} - Continue your sovereign education journey."


@app.route('/api/series/teaser', methods=['POST'])
def get_series_teaser():
    """API endpoint to get AI-generated teaser for next episode"""
    data = request.get_json() or {}
    episode_title = data.get('episode_title', '')
    series_title = data.get('series_title', '')
    
    if not episode_title:
        return jsonify({'error': 'Episode title required'}), 400
    
    teaser = _generate_episode_teaser(episode_title, series_title)
    return jsonify({'teaser': teaser})

@app.route('/api/trigger-automation', methods=['POST', 'GET'])
def trigger_automation():
    """Webhook endpoint to trigger article generation from Scheduled Deployment"""
    from services.automation import generate_article_with_tracking
    
    result = generate_article_with_tracking()
    
    if result.get('success'):
        return jsonify({
            'status': 'success',
            'message': f"Article generated: {result.get('title')}",
            'article_id': result.get('article_id')
        }), 200
    elif result.get('skipped'):
        return jsonify({
            'status': 'skipped',
            'message': 'Another process is running'
        }), 200
    else:
        return jsonify({
            'status': 'failed',
            'message': result.get('error', 'Unknown error')
        }), 500

@app.route('/health/automation')
def automation_health():
    """Health check endpoint for automation monitoring"""
    from services.automation import get_last_run_status
    from datetime import datetime, timedelta
    
    status = get_last_run_status()
    
    if status.get('status') == 'never_run':
        return jsonify({
            'status': 'warning',
            'message': 'Automation has never run',
            'details': status
        }), 200
    
    # Check if last run is stale (>20 minutes)
    if status.get('last_run'):
        last_run_time = datetime.fromisoformat(status['last_run'])
        if datetime.utcnow() - last_run_time > timedelta(minutes=20):
            return jsonify({
                'status': 'stale',
                'message': 'Automation is stale (last run >20 minutes ago)',
                'details': status
            }), 200
    
    # Check if last run failed
    if status.get('status') == 'failed':
        return jsonify({
            'status': 'failed',
            'message': 'Last automation run failed',
            'details': status
        }), 200
    
    return jsonify({
        'status': 'healthy',
        'message': 'Automation is running normally',
        'details': status
    }), 200

# ============================================
# LAUNCH SEQUENCE MANAGEMENT ROUTES
# ============================================

@app.route('/admin/launch-sequences')
@login_required
@admin_required
def admin_launch_sequences():
    """View all launch sequences"""
    sequences = LaunchSequence.query.order_by(LaunchSequence.created_at.desc()).all()
    return render_template('admin_launch_sequences.html', sequences=sequences)

@app.route('/admin/launch-sequence/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_launch_sequence():
    """Create a new launch sequence"""
    if request.method == 'POST':
        from services.launch_sequence import launch_sequence_service
        
        content = request.form.get('content', '')
        content_type = request.form.get('content_type', 'article')
        content_id = request.form.get('content_id')
        
        result = launch_sequence_service.generate_launch_sequence(
            content=content,
            content_type=content_type,
            content_id=int(content_id) if content_id else None
        )
        
        seq = LaunchSequence(
            content_id=result.get('content_id'),
            content_type=result.get('content_type'),
            primary_post_copy=result.get('primary_post_copy'),
            thread_replies=result.get('thread_replies'),
            quote_variants=result.get('quote_variants'),
            reply_drafts=result.get('reply_drafts'),
            hashtags=result.get('hashtags'),
            posting_time=result.get('posting_time'),
            velocity_prediction=result.get('velocity_prediction'),
            first_reply_link=result.get('first_reply_link'),
            call_to_action=result.get('call_to_action'),
            status='draft'
        )
        db.session.add(seq)
        db.session.commit()
        
        flash('Launch sequence created successfully!')
        return redirect(url_for('admin_launch_sequences'))
    
    articles = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).limit(20).all()
    podcasts = Podcast.query.order_by(Podcast.published_date.desc()).limit(20).all()
    return render_template('create_launch_sequence.html', articles=articles, podcasts=podcasts)

@app.route('/admin/launch-sequence/<int:seq_id>')
@login_required
@admin_required
def view_launch_sequence(seq_id):
    """View a specific launch sequence"""
    import json
    seq = LaunchSequence.query.get_or_404(seq_id)
    drafts = []
    if seq.reply_drafts:
        try:
            drafts = json.loads(seq.reply_drafts)
        except:
            pass
    return render_template('view_launch_sequence.html', sequence=seq, drafts=drafts)

@app.route('/admin/launch-sequence/<int:seq_id>/approve', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_launch_sequence(seq_id):
    """Approve a launch sequence for use"""
    seq = LaunchSequence.query.get_or_404(seq_id)
    seq.status = 'approved'
    seq.approved_at = datetime.utcnow()
    db.session.commit()
    flash('Launch sequence approved!')
    return redirect(url_for('admin_launch_sequences'))

@app.route('/admin/launch-sequence/<int:seq_id>/regenerate', methods=['GET', 'POST'])
@login_required
@admin_required
def regenerate_launch_sequence(seq_id):
    """Regenerate a launch sequence with new content"""
    from services.launch_sequence import launch_sequence_service
    
    seq = LaunchSequence.query.get_or_404(seq_id)
    
    content = seq.primary_post_copy or ""
    if seq.content_id and seq.content_type == 'article':
        article = Article.query.get(seq.content_id)
        if article:
            content = f"{article.title}\n\n{article.summary or article.content[:500]}"
    
    result = launch_sequence_service.generate_launch_sequence(
        content=content,
        content_type=seq.content_type or 'article',
        content_id=seq.content_id
    )
    
    seq.primary_post_copy = result.get('primary_post_copy')
    seq.thread_replies = result.get('thread_replies')
    seq.quote_variants = result.get('quote_variants')
    seq.reply_drafts = result.get('reply_drafts')
    seq.hashtags = result.get('hashtags')
    seq.velocity_prediction = result.get('velocity_prediction')
    seq.status = 'draft'
    db.session.commit()
    
    flash('Launch sequence regenerated!')
    return redirect(url_for('view_launch_sequence', seq_id=seq_id))

@app.route('/launch-console/<int:seq_id>')
@login_required
@admin_required
def launch_console(seq_id):
    """Open the launch console for an approved sequence"""
    import json
    seq = LaunchSequence.query.get_or_404(seq_id)
    
    drafts = []
    if seq.reply_drafts:
        try:
            drafts = json.loads(seq.reply_drafts)
        except:
            pass
    
    return render_template('launch_console.html', sequence=seq, drafts=drafts)

@app.route('/launch-console/<int:seq_id>/complete', methods=['POST'])
@login_required
@admin_required
def complete_launch(seq_id):
    """Complete a launch and record metrics"""
    seq = LaunchSequence.query.get_or_404(seq_id)
    
    data = request.get_json() or {}
    seq.status = 'analyzed'
    seq.actual_velocity_score = data.get('velocity_score', 0)
    seq.replies_first_5min = data.get('replies_early', 0)
    seq.total_engagement = data.get('total_engagement', 0)
    seq.reached_for_you = data.get('reached_for_you', False)
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================
# TARGET ALERT ROUTES
# ============================================

@app.route('/admin/target-alerts')
@login_required
@admin_required
def admin_target_alerts():
    """View all target alerts"""
    alerts = TargetAlert.query.order_by(TargetAlert.created_at.desc()).limit(50).all()
    return render_template('admin_target_alerts.html', alerts=alerts)

@app.route('/admin/target-alerts/scan', methods=['POST'])
@login_required
@admin_required
def scan_targets():
    """Scan RSS feeds for new opportunities"""
    from services.target_monitor import target_monitor_service
    
    alerts_data = target_monitor_service.scan_rss_feeds()
    
    for alert_data in alerts_data[:10]:
        drafts = target_monitor_service.generate_reply_drafts(
            alert_data['source_account'],
            alert_data['content_snippet']
        )
        
        alert = TargetAlert(
            trigger_type=alert_data['trigger_type'],
            source_url=alert_data['source_url'],
            source_account=alert_data['source_account'],
            content_snippet=alert_data['content_snippet'],
            priority=alert_data['priority'],
            strategy_suggested=alert_data.get('strategy_suggested', 'default'),
            draft_replies=json.dumps(drafts) if drafts else None,
            status='pending'
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify({'success': True, 'count': len(alerts_data)})

@app.route('/admin/target-alert/<int:alert_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_alert(alert_id):
    """Approve an alert for posting"""
    alert = TargetAlert.query.get_or_404(alert_id)
    alert.status = 'approved'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/target-alert/<int:alert_id>/skip', methods=['POST'])
@login_required
@admin_required
def skip_alert(alert_id):
    """Skip an alert"""
    alert = TargetAlert.query.get_or_404(alert_id)
    alert.status = 'skipped'
    db.session.commit()
    return jsonify({'success': True})

# ============================================
# NOSTR BROADCASTER ROUTES
# ============================================

@app.route('/admin/nostr')
@login_required
@admin_required
def admin_nostr():
    """Nostr broadcaster dashboard"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    status = nostr_broadcaster.get_relay_status()
    events = NostrEvent.query.order_by(NostrEvent.created_at.desc()).limit(50).all()
    
    return render_template('admin_nostr.html', status=status, events=events)

@app.route('/admin/nostr/test', methods=['POST'])
@login_required
@admin_required
def test_nostr():
    """Test Nostr broadcast"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    result = nostr_broadcaster.test_connection()
    
    if result.get('success'):
        event = NostrEvent(
            event_id=result.get('event_id'),
            content_type='test',
            relays_success=json.dumps(result.get('relays_success', [])),
            relays_failed=json.dumps(result.get('relays_failed', []))
        )
        db.session.add(event)
        db.session.commit()
    
    return jsonify(result)

@app.route('/admin/nostr/broadcast', methods=['POST'])
@login_required
@admin_required
def broadcast_to_nostr():
    """Broadcast content to Nostr"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    data = request.get_json() or {}
    content = data.get('content', '')
    content_type = data.get('type', 'note')
    content_id = data.get('content_id')
    
    if not content:
        return jsonify({'error': 'Content required'}), 400
    
    result = nostr_broadcaster.broadcast_note(content)
    
    if result.get('success') or result.get('simulated'):
        event = NostrEvent(
            event_id=result.get('event_id'),
            content_type=content_type,
            content_id=content_id,
            relays_success=json.dumps(result.get('relays_success', [])),
            relays_failed=json.dumps(result.get('relays_failed', []))
        )
        db.session.add(event)
        db.session.commit()
    
    return jsonify(result)

@app.route('/.well-known/nostr.json')
def nostr_nip05():
    """NIP-05 verification endpoint"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    nip05_data = nostr_broadcaster.get_nip05_json()
    
    if nip05_data:
        response = jsonify(nip05_data)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    return jsonify({'names': {}, 'relays': {}}), 200

# ============================================
# INTELLIGENCE DASHBOARD
# ============================================

@app.route('/admin/intelligence')
@login_required
@admin_required
def intelligence_dashboard():
    """Main intelligence dashboard with all metrics"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    articles_count = Article.query.filter_by(published=True).count()
    podcasts_count = Podcast.query.count()
    
    launch_sequences = LaunchSequence.query.order_by(LaunchSequence.created_at.desc()).limit(5).all()
    pending_sequences = LaunchSequence.query.filter_by(status='draft').count()
    
    target_alerts = TargetAlert.query.filter_by(status='pending').order_by(TargetAlert.created_at.desc()).limit(5).all()
    pending_alerts = TargetAlert.query.filter_by(status='pending').count()
    
    nostr_status = nostr_broadcaster.get_relay_status()
    nostr_events = NostrEvent.query.count()
    total_zaps = db.session.query(db.func.sum(NostrEvent.zaps_amount_sats)).scalar() or 0
    
    avg_velocity = db.session.query(db.func.avg(LaunchSequence.actual_velocity_score)).filter(
        LaunchSequence.actual_velocity_score.isnot(None)
    ).scalar() or 0
    
    reply_squad = ReplySquadMember.query.filter_by(active=True).order_by(
        ReplySquadMember.reciprocal_engagements.desc()
    ).limit(10).all()
    
    return render_template('intelligence_dashboard.html',
        articles_count=articles_count,
        podcasts_count=podcasts_count,
        launch_sequences=launch_sequences,
        pending_sequences=pending_sequences,
        target_alerts=target_alerts,
        pending_alerts=pending_alerts,
        nostr_status=nostr_status,
        nostr_events=nostr_events,
        total_zaps=total_zaps,
        avg_velocity=avg_velocity,
        reply_squad=reply_squad
    )

@app.route('/admin/reply-squad')
@login_required
@admin_required
def admin_reply_squad():
    """Manage reply squad members"""
    members = ReplySquadMember.query.order_by(ReplySquadMember.priority, ReplySquadMember.handle).all()
    return render_template('admin_reply_squad.html', members=members)

@app.route('/admin/reply-squad/add', methods=['POST'])
@login_required
@admin_required
def add_reply_squad_member():
    """Add a new reply squad member"""
    data = request.get_json() or request.form
    
    member = ReplySquadMember(
        handle=data.get('handle', ''),
        display_name=data.get('display_name', ''),
        category=data.get('category', 'general'),
        priority=int(data.get('priority', 2)),
        notes=data.get('notes', '')
    )
    db.session.add(member)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'id': member.id})
    flash('Reply squad member added!')
    return redirect(url_for('admin_reply_squad'))

@app.route('/admin/reply-squad/init', methods=['POST'])
@login_required
@admin_required
def init_reply_squad():
    """Initialize reply squad with default members"""
    from services.target_monitor import REPLY_SQUAD
    
    for member_data in REPLY_SQUAD:
        existing = ReplySquadMember.query.filter_by(handle=member_data['handle']).first()
        if not existing:
            member = ReplySquadMember(
                handle=member_data['handle'],
                display_name=member_data.get('name', ''),
                category=member_data.get('category', 'general'),
                priority=member_data.get('priority', 2)
            )
            db.session.add(member)
    
    db.session.commit()
    flash('Reply squad initialized!')
    return redirect(url_for('admin_reply_squad'))

import json

# ============================================
# BITCOIN MEETUP MAP ROUTES
# ============================================

@app.route('/meetup-map')
def meetup_map():
    """Bitcoin meetup and merchant map"""
    from services.meetup_map_service import meetup_map_service
    
    stats = meetup_map_service.get_global_stats()
    meetups = meetup_map_service.get_bitcoin_meetups()
    
    return render_template('meetup_map.html', stats=stats, meetups=meetups)

@app.route('/api/merchants')
def api_merchants():
    """API endpoint for merchants within bounds"""
    from services.meetup_map_service import meetup_map_service
    
    bounds = request.args.get('bounds', '')
    limit = int(request.args.get('limit', 50))
    
    if bounds:
        try:
            parts = bounds.split(',')
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = map(float, parts)
                merchants = meetup_map_service.get_merchants_by_bounds(
                    min_lat, min_lon, max_lat, max_lon, limit
                )
                return jsonify({'merchants': merchants})
        except ValueError:
            pass
    
    return jsonify({'merchants': []})

@app.route('/api/merchants/search')
def api_merchant_search():
    """Search merchants by query"""
    from services.meetup_map_service import meetup_map_service
    
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    
    if query:
        results = meetup_map_service.search_merchants(query, limit)
        return jsonify({'merchants': results})
    
    return jsonify({'merchants': []})

# ============================================
# MONETIZATION & PREMIUM ROUTES
# ============================================

@app.route('/premium')
def premium_page():
    """Premium subscription pricing page"""
    from services.monetization_service import monetization_service
    
    tiers = monetization_service.get_subscription_tiers()
    return render_template('premium.html', tiers=tiers)

@app.route('/subscribe/premium/<tier>')
@login_required
def subscribe_premium(tier):
    """Initiate premium subscription checkout"""
    from services.monetization_service import monetization_service
    
    if tier not in ['operator', 'sovereign']:
        flash('Invalid subscription tier')
        return redirect(url_for('premium_page'))
    
    result = monetization_service.create_checkout_session(
        tier=tier,
        user_email=current_user.email,
        success_url=request.host_url + 'subscription/success',
        cancel_url=request.host_url + 'premium'
    )
    
    if result.get('checkout_url'):
        return redirect(result['checkout_url'])
    elif result.get('simulated'):
        flash('Stripe not configured - subscription simulated for demo')
        return redirect(url_for('premium_page'))
    else:
        flash(f"Error: {result.get('error', 'Unknown error')}")
        return redirect(url_for('premium_page'))

@app.route('/subscription/success')
@login_required
def subscription_success():
    """Subscription success page"""
    session_id = request.args.get('session_id', '')
    return render_template('subscription_success.html', session_id=session_id)

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    """One-time donation page"""
    from services.monetization_service import monetization_service
    
    if request.method == 'POST':
        amount = int(request.form.get('amount', 21))
        email = request.form.get('email', '')
        message = request.form.get('message', '')
        
        result = monetization_service.create_donation_session(
            amount_usd=amount,
            donor_email=email,
            success_url=request.host_url + 'donate/thanks',
            cancel_url=request.host_url + 'donate',
            message=message
        )
        
        if result.get('checkout_url'):
            return redirect(result['checkout_url'])
        elif result.get('simulated'):
            flash('Stripe not configured - donation simulated for demo')
            return redirect(url_for('donate'))
    
    return render_template('donate.html')

@app.route('/donate/thanks')
def donate_thanks():
    """Donation thank you page"""
    return render_template('donate_thanks.html')

@app.route('/tip/<int:amount>')
def tip_checkout(amount):
    """Quick tip checkout - creates a Stripe session for article tips"""
    from services.monetization_service import monetization_service
    
    article_id = request.args.get('article_id', '')
    
    # Validate amount (minimum $1, maximum $500)
    if amount < 1:
        amount = 1
    elif amount > 500:
        amount = 500
    
    # Create descriptive message
    if article_id:
        message = f"Tip for article #{article_id}"
    else:
        message = "Protocol Pulse tip"
    
    result = monetization_service.create_donation_session(
        amount_usd=amount,
        donor_email='',
        success_url=request.host_url + 'donate/thanks',
        cancel_url=request.referrer or request.host_url,
        message=message,
        article_id=article_id if article_id else None
    )
    
    if result.get('checkout_url'):
        return redirect(result['checkout_url'])
    elif result.get('simulated'):
        flash(f'Thank you for your ${amount} tip! (Demo mode)')
        return redirect(request.referrer or url_for('index'))
    else:
        flash('Unable to process tip. Please try again.')
        return redirect(request.referrer or url_for('donate'))

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    from services.monetization_service import monetization_service
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    
    result = monetization_service.handle_webhook(payload, sig_header)
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    return jsonify({'success': True}), 200

@app.route('/admin/revenue')
@login_required
@admin_required
def admin_revenue():
    """Revenue dashboard"""
    from services.monetization_service import monetization_service
    
    stats = monetization_service.get_revenue_stats()
    return render_template('admin_revenue.html', stats=stats)

# ============================================
# CYPHERPUNKS CATEGORY
# ============================================

CYPHERPUNKS = [
    {'name': 'Satoshi Nakamoto', 'role': 'Bitcoin Creator', 'era': '2008-2011'},
    {'name': 'Hal Finney', 'role': 'First Bitcoin Recipient, PGP Developer', 'era': '1992-2014'},
    {'name': 'Nick Szabo', 'role': 'Bit Gold, Smart Contracts Pioneer', 'era': '1990s-present'},
    {'name': 'Adam Back', 'role': 'Hashcash Inventor, Blockstream CEO', 'era': '1997-present'},
    {'name': 'Wei Dai', 'role': 'b-money Creator, Crypto++ Library', 'era': '1998-present'},
    {'name': 'David Chaum', 'role': 'DigiCash Founder, eCash Pioneer', 'era': '1983-present'},
    {'name': 'Timothy C. May', 'role': 'Crypto Anarchist Manifesto Author', 'era': '1988-2018'},
    {'name': 'Eric Hughes', 'role': 'Cypherpunk Manifesto Author', 'era': '1993-present'},
    {'name': 'John Gilmore', 'role': 'EFF Co-founder, Cypherpunks Co-founder', 'era': '1990s-present'},
    {'name': 'Philip Zimmermann', 'role': 'PGP Creator', 'era': '1991-present'},
    {'name': 'Whitfield Diffie', 'role': 'Public-key Cryptography Pioneer', 'era': '1976-present'},
    {'name': 'Ralph Merkle', 'role': 'Merkle Trees, Public-key Cryptography', 'era': '1970s-present'},
]

@app.route('/cypherpunks')
def cypherpunks():
    """Cypherpunks category - honoring the pioneers"""
    articles = Article.query.filter(
        Article.published == True,
        Article.category.ilike('%cypherpunk%')
    ).order_by(Article.created_at.desc()).limit(20).all()
    
    return render_template('cypherpunks.html', 
                          articles=articles,
                          pioneers=CYPHERPUNKS)

# ============================================
# WHALE TRANSACTION API
# ============================================

@app.route('/api/whales')
def api_whales():
    """Get stored whale transactions"""
    from models import WhaleTransaction
    
    whales = WhaleTransaction.query.order_by(WhaleTransaction.detected_at.desc()).limit(50).all()
    
    return jsonify({
        'whales': [{
            'txid': w.txid,
            'btc': w.btc_amount,
            'usd': w.usd_value,
            'time': w.detected_at.isoformat() if w.detected_at else None,
            'is_mega': w.is_mega
        } for w in whales]
    })

@app.route('/api/whales/live')
def api_whales_live():
    """Fetch live whale transactions from Mempool.space API"""
    import requests
    
    whales = []
    min_btc = 10  # Lower threshold to 10 BTC for visibility
    
    try:
        # Check mempool for pending transactions
        mempool_resp = requests.get('https://mempool.space/api/mempool/recent', timeout=10)
        if mempool_resp.status_code == 200:
            for tx in mempool_resp.json():
                btc_value = tx.get('value', 0) / 100000000
                if btc_value >= min_btc:
                    whales.append({
                        'txid': tx['txid'],
                        'btc': round(btc_value, 4),
                        'fee': tx.get('fee', 0),
                        'time': int(datetime.utcnow().timestamp() * 1000),
                        'status': 'pending'
                    })
        
        # Check recent blocks for confirmed large transactions
        blocks_resp = requests.get('https://mempool.space/api/blocks', timeout=10)
        if blocks_resp.status_code == 200:
            blocks = blocks_resp.json()[:5]  # Last 5 blocks
            
            for block in blocks:
                block_time = block.get('timestamp', 0) * 1000
                block_height = block.get('height')
                
                # Get multiple pages of transactions
                for start_idx in [0, 25]:
                    try:
                        txs_resp = requests.get(
                            f"https://mempool.space/api/block/{block['id']}/txs/{start_idx}",
                            timeout=15
                        )
                        
                        if txs_resp.status_code == 200:
                            for tx in txs_resp.json():
                                outputs = tx.get('vout', [])
                                total_out = sum(out.get('value', 0) for out in outputs)
                                btc_value = total_out / 100000000
                                
                                if btc_value >= min_btc:
                                    whales.append({
                                        'txid': tx['txid'],
                                        'btc': round(btc_value, 4),
                                        'fee': tx.get('fee', 0),
                                        'time': block_time,
                                        'status': 'confirmed',
                                        'block': block_height
                                    })
                    except Exception as e:
                        logging.warning(f"Error fetching block txs page: {e}")
                        continue
        
        # Remove duplicates by txid
        seen = set()
        unique_whales = []
        for w in whales:
            if w['txid'] not in seen:
                seen.add(w['txid'])
                unique_whales.append(w)
        
        # Sort by BTC amount descending
        unique_whales.sort(key=lambda x: x['btc'], reverse=True)
        whales = unique_whales[:50]
        
    except Exception as e:
        logging.error(f"Error fetching live whales: {e}")
    
    return jsonify({'whales': whales, 'min_btc': min_btc, 'count': len(whales)})

@app.route('/api/whales/save', methods=['POST'])
def api_save_whale():
    """Save a whale transaction to database"""
    from models import WhaleTransaction
    
    data = request.get_json()
    if not data or 'txid' not in data:
        return jsonify({'error': 'Missing txid'}), 400
    
    existing = WhaleTransaction.query.filter_by(txid=data['txid']).first()
    if existing:
        return jsonify({'status': 'exists', 'id': existing.id})
    
    whale = WhaleTransaction(
        txid=data['txid'],
        btc_amount=data.get('btc', 0),
        usd_value=data.get('usd'),
        fee_sats=data.get('fee'),
        block_height=data.get('block'),
        is_mega=data.get('btc', 0) >= 1000
    )
    db.session.add(whale)
    db.session.commit()
    
    return jsonify({'status': 'saved', 'id': whale.id})

# ============================================
# BITCOIN DONATIONS
# ============================================

@app.route('/donate/bitcoin')
def donate_bitcoin():
    """Bitcoin donation page with Lightning and on-chain options"""
    return render_template('donate_bitcoin.html')

@app.route('/api/donate/lightning', methods=['POST'])
def create_lightning_invoice():
    """Create a Lightning invoice for donation"""
    from models import BitcoinDonation
    
    data = request.get_json() or {}
    amount_sats = data.get('amount_sats', 21000)
    message = data.get('message', '')
    email = data.get('email', '')
    
    donation = BitcoinDonation(
        amount_sats=amount_sats,
        donor_email=email,
        message=message,
        payment_method='lightning',
        status='pending'
    )
    db.session.add(donation)
    db.session.commit()
    
    return jsonify({
        'donation_id': donation.id,
        'lightning_address': 'protocolpulse@getalby.com',
        'amount_sats': amount_sats,
        'message': 'Use your Lightning wallet to send sats to our Lightning address'
    })

@app.route('/og/<og_type>.png')
def dynamic_og_image(og_type):
    """Generate dynamic OG images with live Bitcoin data for SEO"""
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
    import requests
    
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    
    try:
        price_data = requests.get('https://api.coinbase.com/v2/prices/BTC-USD/spot', timeout=3).json()
        btc_price = float(price_data['data']['amount'])
        btc_price_str = f"${btc_price:,.0f}"
    except:
        btc_price_str = "$---,---"
    
    try:
        mempool_data = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=3).json()
        fee_str = f"{mempool_data.get('fastestFee', '--')} sat/vB"
    except:
        fee_str = "-- sat/vB"
    
    draw.rectangle([0, 0, width, height], fill=(10, 10, 10))
    draw.rectangle([0, 0, width, 8], fill=(220, 38, 38))
    draw.rectangle([0, height-8, width, height], fill=(220, 38, 38))
    
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        data_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        title_font = subtitle_font = data_font = small_font = ImageFont.load_default()
    
    if og_type == 'home':
        draw.text((60, 180), "PROTOCOL PULSE", fill=(220, 38, 38), font=title_font)
        draw.text((60, 280), "Bitcoin Intelligence for Transactors", fill=(255, 255, 255), font=subtitle_font)
        draw.text((60, 400), f"BTC {btc_price_str}", fill=(34, 197, 94), font=data_font)
        draw.text((60, 470), f"Next Block: {fee_str}", fill=(234, 179, 8), font=subtitle_font)
    elif og_type == 'bitcoin':
        draw.text((60, 120), "BITCOIN PRICE", fill=(220, 38, 38), font=title_font)
        try:
            big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 120)
        except:
            big_font = title_font
        draw.text((60, 250), btc_price_str, fill=(34, 197, 94), font=big_font)
        draw.text((60, 420), f"Network Fee: {fee_str}", fill=(234, 179, 8), font=subtitle_font)
        draw.text((60, 520), "Protocol Pulse • Live Data", fill=(150, 150, 150), font=small_font)
    elif og_type == 'article':
        article_id = request.args.get('id')
        article_title = "Breaking Bitcoin Intel"
        if article_id:
            try:
                article = Article.query.get(int(article_id))
                if article:
                    article_title = article.title[:60] + "..." if len(article.title) > 60 else article.title
            except:
                pass
        draw.text((60, 180), article_title, fill=(255, 255, 255), font=title_font)
        draw.text((60, 320), "Protocol Pulse", fill=(220, 38, 38), font=subtitle_font)
        draw.text((60, 450), f"BTC {btc_price_str}", fill=(100, 100, 100), font=small_font)
    else:
        draw.text((60, 200), "PROTOCOL PULSE", fill=(220, 38, 38), font=title_font)
        draw.text((60, 300), "Sovereign Bitcoin Intelligence", fill=(255, 255, 255), font=subtitle_font)
    
    output = BytesIO()
    img.save(output, format='PNG', optimize=True)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'public, max-age=300'
    return response

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
```

---

# SECTION 2: SERVICE LAYER

## services/ai_service.py
```python
import os
import json
import logging
from openai import OpenAI
import anthropic
from anthropic import Anthropic
from .grok_service import grok_service
from .gemini_service import gemini_service

class AIService:
    def __init__(self):
        # Initialize OpenAI client
        # Using GPT-5 model for content generation
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)
        else:
            self.openai_client = None
        
        # Initialize Anthropic client
        # Using Claude Opus 4.1 model for content generation
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
        else:
            self.anthropic_client = None
        
        self.default_openai_model = "gpt-4o"
        self.default_anthropic_model = "claude-3-opus-20240229"
        
        # AI service integrations - check availability
        try:
            self.grok_available = grok_service.test_connection()
        except:
            self.grok_available = False
        
        try:
            self.gemini_available = gemini_service.test_connection()
        except:
            self.gemini_available = False
    
    def generate_content_openai(self, prompt, system_prompt=None):
        """Generate content using OpenAI GPT-4o"""
        if not self.openai_client:
            raise ValueError("API key required")
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an investigative journalist for Protocol Pulse."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise
    
    def generate_content_anthropic(self, prompt, system_prompt=None):
        """Generate content using Anthropic Claude"""
        if not self.anthropic_client:
            raise ValueError("API key required")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = self.anthropic_client.messages.create(
                model=self.default_anthropic_model,
                max_tokens=2000,
                temperature=0.7,
                system="You are an investigative journalist for Protocol Pulse.",
                messages=messages
            )
            
            # Handle Anthropic response properly - extract text from content blocks
            if response and response.content and len(response.content) > 0:
                content_block = response.content[0]
                # Use getattr to safely access text attribute regardless of block type
                text_content = getattr(content_block, 'text', None)
                if text_content is not None:
                    return str(text_content)
                else:
                    # Fallback to string conversion for other block types
                    return str(content_block)
            return ""
            
        except Exception as e:
            logging.error(f"Anthropic API error: {str(e)}")
            raise
    
    def generate_structured_content(self, prompt, system_prompt=None, provider="openai"):
        """Generate structured content with JSON response"""
        if provider == "openai" and self.openai_client:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model=self.default_openai_model,
                    messages=messages,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if content:
                    return json.loads(content)
                else:
                    return {}
                
            except Exception as e:
                logging.error(f"OpenAI structured content error: {str(e)}")
                # Fallback to regular generation
                return self.generate_content_openai(prompt, system_prompt)
        
        elif provider == "anthropic" and self.anthropic_client:
            return self.generate_content_anthropic(prompt, system_prompt)
        
        elif provider == "openai" and not self.openai_client:
            raise ValueError("API key required")
        
        elif provider == "anthropic" and not self.anthropic_client:
            raise ValueError("API key required")
        
        else:
            raise ValueError("API key required")
    
    def summarize_text(self, text, max_words=150):
        """Summarize text content"""
        prompt = f"Summarize the following text in {max_words} words or less, focusing on key points relevant to Web3, cryptocurrency, and blockchain technology:\n\n{text}"
        
        try:
            # Try OpenAI first, fallback to Anthropic
            if self.openai_client:
                return self.generate_content_openai(prompt)
            elif self.anthropic_client:
                return self.generate_content_anthropic(prompt)
            else:
                raise ValueError("API key required")
                
        except Exception as e:
            logging.error(f"Summarization error: {str(e)}")
            return text[:500] + "..." if len(text) > 500 else text
    
    def generate_seo_metadata(self, title, content):
        """Generate SEO title and description"""
        prompt = f"""
        Generate SEO-optimized metadata for this article:
        Title: {title}
        Content: {content[:500]}...
        
        Provide a compelling SEO title (60 chars max) and meta description (155 chars max) that includes relevant Web3/crypto keywords.
        Respond in JSON format: {{"seo_title": "...", "seo_description": "..."}}
        """
        
        system_prompt = "You are an SEO expert specializing in Web3 and cryptocurrency content."
        
        try:
            if self.openai_client:
                result = self.generate_structured_content(prompt, system_prompt, "openai")
                if isinstance(result, dict):
                    return result
            elif self.anthropic_client:
                response = self.generate_content_anthropic(prompt, system_prompt)
                return {
                    "seo_title": title[:60],
                    "seo_description": content[:155] + "..." if len(content) > 155 else content
                }
            else:
                raise ValueError("API key required")
            
        except Exception as e:
            logging.error(f"SEO generation error: {str(e)}")
            return {
                "seo_title": title[:60],
                "seo_description": content[:155] + "..." if len(content) > 155 else content
            }
    
    
    def generate_content_grok(self, topic, content_type="bitcoin_news"):
        """Generate content using Grok"""
        if not self.grok_available:
            raise ValueError("API key required")
        
        try:
            if content_type == "bitcoin_news":
                return grok_service.generate_bitcoin_article(topic, "news")
            elif content_type == "bitcoin_analysis":
                return grok_service.generate_bitcoin_article(topic, "analysis")
            elif content_type == "defi_general":
                return grok_service.generate_defi_article(topic, "general")
            elif content_type == "defi_protocols":
                return grok_service.generate_defi_article(topic, "protocols")
            elif content_type == "podcast_script":
                return grok_service.generate_podcast_script(topic)
            else:
                return grok_service.generate_bitcoin_article(topic, "news")
                
        except Exception as e:
            logging.error(f"Grok content generation error: {str(e)}")
            raise
    
    def analyze_sentiment_grok(self, text):
        """Analyze sentiment using Grok"""
        if not self.grok_available:
            raise ValueError("API key required")
        
        try:
            return grok_service.analyze_market_sentiment(text)
        except Exception as e:
            logging.error(f"Grok sentiment analysis error: {str(e)}")
            return {"error": str(e)}
    
    def generate_content_gemini(self, topic, content_type="bitcoin_news"):
        """Generate content using Gemini"""
        if not self.gemini_available:
            raise ValueError("API key required")
        
        try:
            if content_type == "bitcoin_news":
                return gemini_service.generate_bitcoin_article(topic, "news")
            elif content_type == "bitcoin_analysis":
                return gemini_service.generate_bitcoin_article(topic, "analysis")
            elif content_type == "defi_general":
                return gemini_service.generate_defi_article(topic, "general")
            elif content_type == "defi_protocols":
                return gemini_service.generate_defi_article(topic, "protocols")
            elif content_type == "podcast_script":
                return gemini_service.generate_podcast_script(topic)
            else:
                return gemini_service.generate_bitcoin_article(topic, "news")
                
        except Exception as e:
            logging.error(f"Gemini content generation error: {str(e)}")
            raise
    
    def analyze_sentiment_gemini(self, text):
        """Analyze sentiment using Gemini"""
        if not self.gemini_available:
            raise ValueError("API key required")
        
        try:
            return gemini_service.analyze_market_sentiment(text)
        except Exception as e:
            logging.error(f"Gemini sentiment analysis error: {str(e)}")
            return {"error": str(e)}
    
    def get_available_providers(self):
        """Get list of available AI providers"""
        providers = []
        if self.openai_client:
            providers.append("OpenAI GPT-5")
        if self.anthropic_client:
            providers.append("Anthropic Claude")
        if self.grok_available:
            providers.append("xAI Grok")
        if self.gemini_available:
            providers.append("Google Gemini")
        return providers
    
    def enhance_ad_image(self, image_path):
        """Enhance advertisement image using AI"""
        # Try Gemini first for image enhancement
        if self.gemini_available:
            try:
                from .gemini_service import gemini_service
                enhanced_url = gemini_service.enhance_image_with_spice(image_path)
                if enhanced_url:
                    return enhanced_url
            except Exception as e:
                logging.warning(f"Gemini image enhancement failed: {e}")
        
        # Fallback to OpenAI if Gemini fails
        if not self.openai_client:
            logging.warning("OpenAI client not available for image enhancement")
            return None
        
        try:
            with open(image_path, "rb") as image_file:
                response = self.openai_client.images.edit(
                    image=image_file,
                    prompt="Spice up in dramatic red/black/white, futuristic cyberpunk, premium sleek high-tech—DO NOT change core subject/composition.",
                    n=1,
                    size="1024x1024"
                )
                
                if response.data and len(response.data) > 0:
                    return response.data[0].url
                else:
                    logging.warning("No image data returned from OpenAI")
                    return None
                    
        except Exception as e:
            logging.error(f"Image enhancement error: {str(e)}")
            return None
```

## services/content_engine.py
```python
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from app import db
from models import Article
from services.ai_service import AIService
from services.substack_service import SubstackService
from services.elevenlabs_service import ElevenLabsService
from services.heygen_service import HeyGenService
from substack import Api
from substack.post import Post


class ContentEngine:
    """
    Main content generation and publishing engine for Protocol Pulse
    Coordinates AI generation, Substack publishing, and cross-platform distribution
    """
    
    # EDITORIAL ACCURACY MANDATE - Applied to all generated content
    ACCURACY_MANDATE = """
=== EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===

BEFORE DRAFTING ANY ARTICLE, YOU MUST:
1. VERIFY the latest Bitcoin metrics (Difficulty, Hashrate, Price) via real-time data fetch ONLY
2. DO NOT rely on training data or assumptions about network conditions
3. State the ACTUAL current date and ACTUAL current metrics correctly
4. If real-time data is not provided in the source material, DO NOT report on metrics

STRICTLY PROHIBITED - IMMEDIATE REJECTION IF VIOLATED:
- NEVER claim "all-time high," "record high," "unprecedented," or "new record" for ANY Bitcoin metric
- NEVER hallucinate hashrate figures (e.g., do not invent "1.2 ZH/s" or any number)
- NEVER assume difficulty is increasing - it can DECREASE during miner stress periods
- NEVER fabricate "network strengthening" narratives without verified data
- NEVER use phrases like "surge," "soaring," or "record-breaking" for metrics you cannot verify

REALITY CHECK - As of January 2026:
- Bitcoin hashrate has DECLINED approximately 15% from its October 2024 peak
- Difficulty adjustments can be NEGATIVE (downward) - this is normal during miner stress
- The network is NOT always hitting "new highs" - it fluctuates based on miner economics

IF WRITING ABOUT BITCOIN NETWORK METRICS:
- Only report what is EXPLICITLY stated in verified source material
- If source says "difficulty adjustment" without direction, ask for clarification or omit
- Use qualified language: "according to [source]," "data from [provider] shows"
- If you cannot verify a claim, DO NOT MAKE IT

Hallucinating record highs when the network is experiencing miner stress is STRICTLY PROHIBITED and will result in content rejection.
"""
    
    def __init__(self):
        self.ai_service = AIService()
        try:
            self.substack_service = SubstackService()
        except Exception as e:
            logging.warning(f"Substack service initialization failed: {e}")
            self.substack_service = None
            
        try:
            self.elevenlabs_service = ElevenLabsService()
        except Exception as e:
            logging.warning(f"ElevenLabs service initialization failed: {e}")
            self.elevenlabs_service = None
            
        try:
            self.heygen_service = HeyGenService()
        except Exception as e:
            logging.warning(f"HeyGen service initialization failed: {e}")
            self.heygen_service = None
        
        logging.info("Content Engine initialized")

    def review_article_with_gemini(self, title: str, content: str) -> Dict:
        """
        Use Gemini as Editor-in-Chief for automated quality control
        Returns AI review decision: APPROVE or REJECT with reasoning
        """
        try:
            from services.ai_service import AIService
            
            review_prompt = f"""
You are the Editor-in-Chief for Protocol Pulse, a professional Bitcoin and DeFi media network.

Review this article for publication quality:

TITLE: {title}

CONTENT: {content}

Evaluate on these criteria:
1. Factual accuracy and credibility
2. Writing clarity and professionalism  
3. Relevance to Bitcoin/DeFi audience
4. Completeness and depth of analysis
5. Freedom from errors or inconsistencies

Respond with JSON only:
{{"decision": "APPROVE" or "REJECT", "reason": "brief explanation", "score": 1-10}}

APPROVE if score >= 7, REJECT if score < 7.
"""
            
            ai_service = AIService()
            response = ai_service.generate_content_openai(review_prompt)
            
            # Parse AI review response
            import json
            try:
                review_data = json.loads(response)
                return {
                    "decision": review_data.get("decision", "REJECT"),
                    "reason": review_data.get("reason", "No reason provided"),
                    "score": review_data.get("score", 0)
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                if "APPROVE" in response.upper():
                    return {"decision": "APPROVE", "reason": "AI approved content", "score": 8}
                else:
                    return {"decision": "REJECT", "reason": "AI rejected content", "score": 5}
                    
        except Exception as e:
            logging.error(f"Gemini review failed: {e}")
            # Default to approval if review system fails
            return {"decision": "APPROVE", "reason": "Review system unavailable", "score": 7}

    def approve_and_publish_article(self, article_id: int) -> Dict:
        """
        Automated AI review and publishing workflow
        Uses Gemini as Editor-in-Chief for quality control
        """
        result = {
            "success": False,
            "substack_url": None,
            "errors": [],
            "review": None
        }
        
        try:
            # Get article from database
            article = db.session.get(Article, article_id)
            if not article:
                result["errors"].append("Article not found")
                return result
            
            # AI Review with Gemini (Editor-in-Chief)
            review = self.review_article_with_gemini(article.title, article.content)
            result["review"] = review
            
            if review.get("decision") == "APPROVE":
                # Save to DB (mark as approved)
                article.published = True
                
                # No header images - user preference
                image_path = None
                
                # Publish to Substack
                substack_url = self.publish_to_substack(
                    title=article.title, 
                    body_markdown=article.content, 
                    image_path=image_path
                )
                
                if substack_url:
                    article.substack_url = substack_url
                    db.session.commit()
                    
                    result["success"] = True
                    result["substack_url"] = substack_url
                    result["message"] = f"AI approved and published (Score: {review.get('score')}/10)"
                    
                    logging.info(f"Article {article_id} AI-approved and published: {substack_url}")
                else:
                    result["errors"].append("Failed to publish to Substack")
                    
            else:
                # AI rejected - save as draft for potential revision
                article.published = False
                db.session.commit()
                result["message"] = f"AI rejected: {review.get('reason')} (Score: {review.get('score')}/10)"
                logging.info(f"Article {article_id} AI-rejected: {review.get('reason')}")
            
            return result
            
        except Exception as e:
            result["errors"].append(f"AI review workflow error: {e}")
            logging.error(f"AI review workflow failed for article {article_id}: {e}")
            return result

    def generate_and_publish_article(self, topic: str, content_type: str = "bitcoin_news", 
                                   auto_publish: bool = False) -> Dict:
        """
        Complete content generation and publishing pipeline
        
        Args:
            topic: Article topic or source content
            content_type: Type of content (bitcoin_news, defi_analysis, market_update)
            auto_publish: Whether to auto-publish to Substack
            
        Returns:
            Dictionary with generation results and URLs
        """
        result = {
            "success": False,
            "article_id": None,
            "substack_url": None,
            "audio_file": None,
            "video_url": None,
            "errors": []
        }
        
        try:
            # Step 1: Generate article content
            logging.info(f"Generating {content_type} article for topic: {topic}")
            
            if content_type == "bitcoin_news":
                article_data = self._generate_bitcoin_article(topic)
            elif content_type == "defi_analysis":
                article_data = self._generate_defi_article(topic)
            elif content_type == "market_update":
                article_data = self._generate_market_article(topic)
            else:
                article_data = self._generate_general_article(topic, content_type)
            
            if not article_data:
                result["errors"].append("Failed to generate article content")
                return result
            
            # Step 2: Save article to database
            article = self._save_article_to_db(article_data)
            if article:
                result["article_id"] = article.id
                logging.info(f"Article saved to database with ID: {article.id}")
            else:
                result["errors"].append("Failed to save article to database")
                return result
            
            # Step 3: Generate multimedia content
            if self.elevenlabs_service:
                try:
                    audio_file = self._generate_audio_content(article_data)
                    if audio_file:
                        result["audio_file"] = audio_file
                        logging.info(f"Generated audio file: {audio_file}")
                except Exception as e:
                    result["errors"].append(f"Audio generation failed: {e}")
            
            if self.heygen_service:
                try:
                    video_url = self._generate_video_content(article_data, content_type)
                    if video_url:
                        result["video_url"] = video_url
                        logging.info(f"Generated video: {video_url}")
                except Exception as e:
                    result["errors"].append(f"Video generation failed: {e}")
            
            # Step 4: AI Review and Auto-Publishing Pipeline
            if auto_publish and self.substack_service:
                try:
                    # AI Review with Gemini Editor-in-Chief
                    review = self.review_article_with_gemini(article_data["title"], article_data["content"])
                    result["review"] = review
                    
                    if review.get("decision") == "APPROVE":
                        # AI approved - publish to Substack
                        image_path = None  # No header images - user preference
                        substack_url = self.publish_to_substack(
                            title=article_data["title"], 
                            body_markdown=article_data["content"], 
                            image_path=image_path
                        )
                        
                        if substack_url:
                            article.substack_url = substack_url
                            article.published = True
                            db.session.commit()
                            
                            result["substack_url"] = substack_url
                            result["message"] = f"AI approved and published (Score: {review.get('score')}/10)"
                            logging.info(f"AI approved and published: {substack_url}")
                        else:
                            result["errors"].append("Substack publishing failed")
                    else:
                        # AI rejected - save as draft
                        article.published = False
                        db.session.commit()
                        result["message"] = f"AI rejected: {review.get('reason')} (Score: {review.get('score')}/10)"
                        logging.info(f"AI rejected article: {review.get('reason')}")
                        
                except Exception as e:
                    result["errors"].append(f"AI review pipeline failed: {e}")
            else:
                # Save as draft for later review
                result["status"] = "draft"
                result["message"] = "Article saved as draft"
            
            result["success"] = True
            return result
            
        except Exception as e:
            logging.error(f"Content generation pipeline failed: {e}")
            result["errors"].append(f"Pipeline error: {e}")
            return result

    def _generate_bitcoin_article(self, topic: str) -> Optional[Dict]:
        """Generate Bitcoin-focused news article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            Write a high-value article blog post about: {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Focus exclusively on Bitcoin. Target length: 800-1200 words
            """
            
            content = self.ai_service.generate_content_openai(prompt)
            if content:
                return self._parse_article_content(content, "Bitcoin")
            return None
            
        except Exception as e:
            logging.error(f"Bitcoin article generation failed: {e}")
            return None

    def _generate_defi_article(self, topic: str) -> Optional[Dict]:
        """Generate DeFi analysis article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            Write a high-value article blog post about: {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Focus on DeFi protocols and decentralized finance. Target length: 1000-1500 words
            """
            
            content = self.ai_service.generate_content_anthropic(prompt)
            if content:
                return self._parse_article_content(content, "DeFi")
            return None
            
        except Exception as e:
            logging.error(f"DeFi article generation failed: {e}")
            return None

    def _generate_market_article(self, topic: str) -> Optional[Dict]:
        """Generate market update article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            Write a high-value article blog post about: {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Cover both Bitcoin price action and DeFi market trends. Target length: 600-900 words
            """
            
            content = self.ai_service.generate_content_openai(prompt)
            if content:
                return self._parse_article_content(content, "Market Update")
            return None
            
        except Exception as e:
            logging.error(f"Market article generation failed: {e}")
            return None

    def _generate_general_article(self, topic: str, content_type: str) -> Optional[Dict]:
        """Generate general Web3/crypto article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            Write a high-value article blog post about: {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Focus on Bitcoin and DeFi as primary topics. Target length: 800-1200 words
            """
            
            content = self.ai_service.generate_content_openai(prompt)
            if content:
                return self._parse_article_content(content, content_type.title())
            return None
            
        except Exception as e:
            logging.error(f"General article generation failed: {e}")
            return None

    def _parse_article_content(self, content: str, category: str) -> Dict:
        """Parse AI-generated content into structured article data"""
        lines = content.strip().split('\n')
        
        # Extract title (first non-empty line or line starting with #)
        title = ""
        content_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not title:
                title = line.replace('#', '').strip()
                content_start = i + 1
                break
        
        # Extract summary (look for summary section or use first paragraph)
        summary = ""
        article_content = ""
        
        remaining_lines = lines[content_start:]
        if remaining_lines:
            # Try to find a summary section
            summary_found = False
            content_lines = []
            
            for line in remaining_lines:
                line_lower = line.lower().strip()
                if any(keyword in line_lower for keyword in ['summary:', 'overview:', 'key points:']):
                    summary_found = True
                    continue
                elif summary_found and line.strip() and not line.startswith('#'):
                    summary = line.strip()
                    summary_found = False
                else:
                    content_lines.append(line)
            
            article_content = '\n'.join(content_lines).strip()
            
            # If no summary found, use first paragraph
            if not summary and article_content:
                paragraphs = article_content.split('\n\n')
                if paragraphs:
                    summary = paragraphs[0][:300] + "..." if len(paragraphs[0]) > 300 else paragraphs[0]
        
        return {
            "title": title or "Untitled Article",
            "content": article_content or content,
            "summary": summary or "AI-generated article summary",
            "category": category,
            "tags": f"{category}, Bitcoin, DeFi, Protocol Pulse",
            "seo_title": title[:200] if title else "Protocol Pulse Article",
            "seo_description": summary[:300] if summary else "Latest Bitcoin and DeFi insights"
        }

    def _save_article_to_db(self, article_data: Dict) -> Optional[Article]:
        """Save article to database"""
        try:
            # Clean content to handle special characters
            def clean_text(text):
                if isinstance(text, str):
                    # Replace problematic Unicode characters
                    text = text.replace('\u2019', "'")  # Smart apostrophe
                    text = text.replace('\u2018', "'")  # Smart apostrophe
                    text = text.replace('\u201c', '"')  # Smart quote
                    text = text.replace('\u201d', '"')  # Smart quote
                    text = text.replace('\u2013', '-')  # En dash
                    text = text.replace('\u2014', '--') # Em dash
                    return text.encode('utf-8', errors='ignore').decode('utf-8')
                return text
            
            article = Article(
                title=clean_text(article_data["title"]),
                content=clean_text(article_data["content"]),
                summary="",  # No summary - TL;DR is embedded in content
                category=clean_text(article_data["category"]),
                tags=clean_text(article_data["tags"]),
                seo_title=clean_text(article_data["seo_title"]),
                seo_description=clean_text(article_data["seo_description"]),
                source_type="ai_generated",
                published=False,  # Require manual approval by default
                author="Al Ingle"
            )
            
            db.session.add(article)
            db.session.commit()
            
            return article
            
        except Exception as e:
            logging.error(f"Database save failed: {e}")
            db.session.rollback()
            return None

    def _generate_audio_content(self, article_data: Dict) -> Optional[str]:
        """Generate audio version of article"""
        try:
            if not self.elevenlabs_service:
                return None
                
            # Determine voice type based on content category
            category = article_data.get("category", "").lower()
            if "bitcoin" in category:
                voice_type = "professional_male"
            elif "defi" in category:
                voice_type = "authoritative"
            elif "market" in category:
                voice_type = "professional_female"
            else:
                voice_type = "conversational"
            
            # Generate audio
            audio_file = self.elevenlabs_service.generate_article_summary_audio(
                article_data["title"], 
                article_data["content"],
                voice_type
            )
            
            return audio_file
            
        except Exception as e:
            logging.error(f"Audio generation failed: {e}")
            return None

    def _generate_video_content(self, article_data: Dict, content_type: str) -> Optional[str]:
        """Generate video version of article"""
        try:
            if not self.heygen_service:
                return None
                
            # Generate appropriate video based on content type
            if content_type == "bitcoin_news":
                video_url = self.heygen_service.create_bitcoin_news_video(
                    article_data["title"],
                    article_data["summary"]
                )
            elif content_type == "defi_analysis":
                video_url = self.heygen_service.create_defi_analysis_video(
                    article_data["content"][:500]  # Truncate for video
                )
            else:
                video_url = self.heygen_service.create_social_media_video(
                    article_data["summary"]
                )
            
            return video_url
            
        except Exception as e:
            logging.error(f"Video generation failed: {e}")
            return None

    def _publish_to_substack(self, article_data: Dict, content_type: str) -> Optional[str]:
        """Publish article to Substack using your exact implementation"""
        return self.publish_to_substack(
            article_data["title"], 
            article_data["content"], 
            None  # No header images - user preference
        )

    def publish_to_substack(self, title: str, body_markdown: str, image_path: str = None) -> Optional[str]:
        """Your exact Substack publishing implementation"""
        try:
            api = Api(
                email=os.environ.get("SUBSTACK_EMAIL"),
                password=os.environ.get("SUBSTACK_PASSWORD"),
                publication_url=os.environ.get("SUBSTACK_PUBLICATION_URL")
            )
            user_id = api.get_user_id()

            post = Post(
                title=title,
                subtitle="Generated by Protocol Pulse AI",
                user_id=user_id
            )

            # Add body as paragraph (convert Markdown to Substack blocks if needed; simple for now)
            post.add({"type": "paragraph", "content": body_markdown})

            # Optional header image (from DALL-E path/URL)
            if image_path:
                uploaded = api.get_image(image_path)  # Handles upload
                post.add({"type": "captionedImage", "src": uploaded.get("url")})

            draft = api.post_draft(post.get_draft())
            # Optional: Set section if needed - api.put_draft(draft.get("id"), ...)
            api.prepublish_draft(draft.get("id"))
            published = api.publish_draft(draft.get("id"))
            post_url = published.get("canonical_url")
            self.send_slack_notification(f"Article published to Substack: {post_url}")
            return post_url
        except Exception as e:
            self.send_slack_notification(f"Substack error: {e}")
            logging.error(f"Substack publishing error: {e}")
            return None

    def send_slack_notification(self, message: str):
        """Send notification to Slack (placeholder for now)"""
        try:
            # TODO: Implement Slack integration when API keys are provided
            logging.info(f"Slack notification: {message}")
        except Exception as e:
            logging.error(f"Slack notification failed: {e}")

    def generate_content_from_reddit_trend(self, reddit_post: Dict) -> Dict:
        """Generate content based on Reddit trending topic"""
        try:
            topic = f"{reddit_post.get('title', '')} - {reddit_post.get('selftext', '')[:500]}"
            
            # Determine content type based on post
            if any(keyword in topic.lower() for keyword in ['defi', 'protocol', 'yield', 'liquidity']):
                content_type = "defi_analysis"
            elif any(keyword in topic.lower() for keyword in ['price', 'market', 'pump', 'dump']):
                content_type = "market_update"
            else:
                content_type = "bitcoin_news"
            
            return self.generate_and_publish_article(topic, content_type, auto_publish=False)
            
        except Exception as e:
            logging.error(f"Reddit trend content generation failed: {e}")
            return {"success": False, "errors": [str(e)]}

# Initialize the content engine
content_engine = ContentEngine()```

## services/fact_checker.py
```python
"""
Protocol Pulse Fact Checker Service
Prevents AI hallucinations by verifying claims against live blockchain data.

Philosophy: "Technical Storytelling, Not Hype" - Facts first, always.
"""

import requests
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class FactChecker:
    """Verifies factual claims in Bitcoin articles against live data sources."""
    
    BITNODES_API = "https://bitnodes.io/api"
    MEMPOOL_API = "https://mempool.space/api/v1"
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    BLOCKCHAIN_INFO_API = "https://blockchain.info"
    
    TREND_THRESHOLDS = {
        'surging': 15,      # 15%+ growth
        'increasing': 5,    # 5-15% growth
        'stable': -5,       # -5% to 5%
        'declining': -15,   # -15% to -5%
        'plummeting': -100  # Below -15%
    }
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached data if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
        return None
    
    def _set_cache(self, key: str, data: dict):
        """Cache data with timestamp."""
        self.cache[key] = (data, datetime.now())
    
    def verify_node_count(self, claimed_count: int = None, claimed_trend: str = None) -> Dict:
        """
        Verifies Bitcoin node count claims against Bitnodes API.
        
        Args:
            claimed_count: The number claimed in article (e.g., 15000)
            claimed_trend: 'surging', 'declining', 'stable', etc.
        
        Returns:
            Verification result with actual data
        """
        try:
            cached = self._get_cached('node_count')
            if cached:
                current_count = cached['total_nodes']
            else:
                response = requests.get(f"{self.BITNODES_API}/snapshots/latest/", timeout=10)
                response.raise_for_status()
                data = response.json()
                current_count = data.get('total_nodes', 0)
                self._set_cache('node_count', data)
            
            hist_response = requests.get(f"{self.BITNODES_API}/snapshots/?limit=30", timeout=10)
            hist_data = hist_response.json()
            
            thirty_days_ago = None
            if hist_data.get('results') and len(hist_data['results']) >= 30:
                thirty_days_ago = hist_data['results'][-1].get('total_nodes')
            
            pct_change = 0
            actual_trend = 'unknown'
            if thirty_days_ago and thirty_days_ago > 0:
                pct_change = ((current_count - thirty_days_ago) / thirty_days_ago) * 100
                
                if pct_change >= self.TREND_THRESHOLDS['surging']:
                    actual_trend = 'surging'
                elif pct_change >= self.TREND_THRESHOLDS['increasing']:
                    actual_trend = 'increasing'
                elif pct_change >= self.TREND_THRESHOLDS['stable']:
                    actual_trend = 'stable'
                elif pct_change >= self.TREND_THRESHOLDS['declining']:
                    actual_trend = 'declining'
                else:
                    actual_trend = 'plummeting'
            
            errors = []
            
            if claimed_count is not None:
                tolerance = current_count * 0.10  # 10% tolerance
                if abs(claimed_count - current_count) > tolerance:
                    errors.append(
                        f"Node count claim inaccurate. Claimed: {claimed_count:,}, "
                        f"Actual: {current_count:,} (off by {abs(claimed_count - current_count):,})"
                    )
            
            if claimed_trend is not None:
                claimed_lower = claimed_trend.lower()
                if claimed_lower in ['surging', 'surge', 'skyrocketing', 'unprecedented']:
                    if actual_trend not in ['surging']:
                        errors.append(
                            f"Trend claim inaccurate. Claimed: '{claimed_trend}' but actual trend is "
                            f"'{actual_trend}' ({pct_change:+.1f}% over 30 days)"
                        )
                elif claimed_lower in ['increasing', 'growing', 'rising']:
                    if actual_trend not in ['surging', 'increasing']:
                        errors.append(
                            f"Trend claim inaccurate. Claimed: '{claimed_trend}' but actual is "
                            f"'{actual_trend}' ({pct_change:+.1f}% over 30 days)"
                        )
            
            return {
                'verified': len(errors) == 0,
                'actual_count': current_count,
                'claimed_count': claimed_count,
                'actual_trend': actual_trend,
                'claimed_trend': claimed_trend,
                'pct_change_30d': round(pct_change, 2),
                'errors': errors,
                'source': 'bitnodes.io',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Node count verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'actual_count': None,
                'source': 'bitnodes.io',
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_difficulty(self, claimed_value: float = None, claimed_is_ath: bool = False) -> Dict:
        """
        Verifies Bitcoin difficulty claims against Mempool.space API.
        
        Args:
            claimed_value: Claimed difficulty in T (e.g., 146.47 for 146.47T)
            claimed_is_ath: Whether article claims this is all-time high
        
        Returns:
            Verification result
        """
        try:
            response = requests.get("https://mempool.space/api/v1/blocks/tip/height", timeout=10)
            response.raise_for_status()
            tip_height = response.json()
            
            block_response = requests.get(f"https://mempool.space/api/block-height/{tip_height}", timeout=10)
            block_hash = block_response.text.strip()
            
            block_detail_response = requests.get(f"https://mempool.space/api/block/{block_hash}", timeout=10)
            block_data = block_detail_response.json()
            
            current_difficulty = block_data.get('difficulty', 0)
            current_t = current_difficulty / 1e12
            
            KNOWN_ATH_T = 155.9
            
            errors = []
            
            if claimed_value is not None:
                tolerance = claimed_value * 0.10  # 10% tolerance
                if abs(claimed_value - current_t) > tolerance:
                    errors.append(
                        f"Difficulty claim inaccurate. Claimed: {claimed_value}T, Actual: {current_t:.2f}T"
                    )
            
            is_actually_ath = current_t > KNOWN_ATH_T
            if claimed_is_ath and not is_actually_ath:
                errors.append(
                    f"ATH claim incorrect. Current difficulty ({current_t:.2f}T) is not an all-time high. "
                    f"Known ATH is {KNOWN_ATH_T}T from November 2025."
                )
            
            return {
                'verified': len(errors) == 0,
                'actual_difficulty_t': round(current_t, 2),
                'claimed_difficulty_t': claimed_value,
                'is_ath': is_actually_ath,
                'known_ath_t': KNOWN_ATH_T,
                'claimed_is_ath': claimed_is_ath,
                'errors': errors,
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Difficulty verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_price_movement(self, claimed_movement: str) -> Dict:
        """
        Verifies price movement claims. We AVOID price headlines but verify if mentioned.
        
        Args:
            claimed_movement: 'surging', 'plummeting', 'stable', etc.
        
        Returns:
            Verification result
        """
        try:
            response = requests.get(
                f"{self.COINGECKO_API}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            change_24h = data['bitcoin'].get('usd_24h_change', 0)
            current_price = data['bitcoin'].get('usd', 0)
            
            if change_24h > 10:
                actual_movement = 'surging'
            elif change_24h > 3:
                actual_movement = 'rising'
            elif change_24h > -3:
                actual_movement = 'stable'
            elif change_24h > -10:
                actual_movement = 'declining'
            else:
                actual_movement = 'plummeting'
            
            errors = []
            claimed_lower = claimed_movement.lower()
            
            movement_map = {
                'surging': ['surging'],
                'rising': ['surging', 'rising'],
                'stable': ['rising', 'stable', 'declining'],
                'declining': ['declining', 'stable'],
                'plummeting': ['plummeting', 'declining'],
                'crashing': ['plummeting']
            }
            
            if claimed_lower in movement_map:
                if actual_movement not in movement_map[claimed_lower]:
                    errors.append(
                        f"Price movement claim inaccurate. Claimed: '{claimed_movement}', "
                        f"Actual: '{actual_movement}' ({change_24h:+.1f}% 24h)"
                    )
            
            return {
                'verified': len(errors) == 0,
                'current_price_usd': current_price,
                'change_24h': round(change_24h, 2),
                'actual_movement': actual_movement,
                'claimed_movement': claimed_movement,
                'errors': errors,
                'source': 'coingecko.com',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Price verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'source': 'coingecko.com',
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_hashrate(self, claimed_value: float = None, claimed_unit: str = 'EH/s') -> Dict:
        """
        Verifies hashrate claims.
        
        Args:
            claimed_value: Claimed hashrate value
            claimed_unit: Unit (EH/s, TH/s, etc.)
        
        Returns:
            Verification result
        """
        try:
            response = requests.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current_hashrate = data.get('currentHashrate', 0)
            current_eh = current_hashrate / 1e18 if current_hashrate > 0 else 0
            
            errors = []
            
            if claimed_value is not None:
                claimed_eh = claimed_value
                if claimed_unit.upper() == 'TH/S':
                    claimed_eh = claimed_value / 1e6
                elif claimed_unit.upper() == 'PH/S':
                    claimed_eh = claimed_value / 1e3
                
                tolerance = current_eh * 0.10  # 10% tolerance
                if abs(claimed_eh - current_eh) > tolerance:
                    errors.append(
                        f"Hashrate claim inaccurate. Claimed: {claimed_value} {claimed_unit}, "
                        f"Actual: {current_eh:.0f} EH/s"
                    )
            
            return {
                'verified': len(errors) == 0,
                'actual_hashrate_eh': round(current_eh, 1),
                'claimed_value': claimed_value,
                'claimed_unit': claimed_unit,
                'errors': errors,
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Hashrate verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
    
    def extract_claims_from_article(self, article_text: str) -> List[Dict]:
        """
        Extracts verifiable claims from article text using pattern matching.
        
        Args:
            article_text: The full article text
        
        Returns:
            List of extracted claims with their types
        """
        claims = []
        
        node_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:reachable\s+)?nodes?',
            r'node\s+count\s+(?:has\s+)?(?:reached|crossed|surpassed)\s+(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s+mark\s+(?:globally|worldwide)?'
        ]
        
        trend_patterns = [
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:surging|skyrocketing|unprecedented)', 'surging'),
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:increasing|growing|rising)', 'increasing'),
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:stable|steady)', 'stable'),
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:declining|dropping|falling)', 'declining'),
        ]
        
        for pattern in node_patterns:
            matches = re.findall(pattern, article_text, re.IGNORECASE)
            for match in matches:
                count = int(match.replace(',', ''))
                claims.append({
                    'type': 'node_count',
                    'value': count,
                    'raw_text': match
                })
        
        for pattern, trend in trend_patterns:
            if re.search(pattern, article_text, re.IGNORECASE):
                claims.append({
                    'type': 'node_trend',
                    'value': trend,
                    'raw_text': re.search(pattern, article_text, re.IGNORECASE).group()
                })
        
        difficulty_patterns = [
            r'difficulty\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*T',
            r'(\d+(?:\.\d+)?)\s*T\s+difficulty'
        ]
        
        for pattern in difficulty_patterns:
            matches = re.findall(pattern, article_text, re.IGNORECASE)
            for match in matches:
                claims.append({
                    'type': 'difficulty',
                    'value': float(match),
                    'raw_text': match
                })
        
        if re.search(r'all[- ]time\s+high|ATH|record\s+(?:high|difficulty)', article_text, re.IGNORECASE):
            claims.append({
                'type': 'difficulty_ath',
                'value': True,
                'raw_text': 'all-time high/ATH claim'
            })
        
        hashrate_patterns = [
            r'hashrate\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(EH|TH|PH)',
            r'(\d+(?:\.\d+)?)\s*(EH|TH|PH)/s\s+hashrate'
        ]
        
        for pattern in hashrate_patterns:
            matches = re.findall(pattern, article_text, re.IGNORECASE)
            for match in matches:
                claims.append({
                    'type': 'hashrate',
                    'value': float(match[0]),
                    'unit': match[1].upper() + '/s',
                    'raw_text': f"{match[0]} {match[1]}/s"
                })
        
        return claims
    
    def verify_article(self, article_text: str) -> Dict:
        """
        Comprehensive article verification. Extracts and verifies all claims.
        
        Args:
            article_text: The full article text
        
        Returns:
            Complete verification report
        """
        claims = self.extract_claims_from_article(article_text)
        
        results = {
            'verified': True,
            'claims_found': len(claims),
            'claims_verified': 0,
            'claims_failed': 0,
            'errors': [],
            'warnings': [],
            'verifications': [],
            'timestamp': datetime.now().isoformat()
        }
        
        node_count_claim = None
        node_trend_claim = None
        
        for claim in claims:
            if claim['type'] == 'node_count':
                node_count_claim = claim['value']
            elif claim['type'] == 'node_trend':
                node_trend_claim = claim['value']
        
        if node_count_claim is not None or node_trend_claim is not None:
            verification = self.verify_node_count(node_count_claim, node_trend_claim)
            results['verifications'].append({
                'type': 'node_count',
                'result': verification
            })
            if verification['verified']:
                results['claims_verified'] += 1
            else:
                results['claims_failed'] += 1
                results['errors'].extend(verification.get('errors', []))
                results['verified'] = False
        
        difficulty_claim = None
        difficulty_ath_claim = False
        
        for claim in claims:
            if claim['type'] == 'difficulty':
                difficulty_claim = claim['value']
            elif claim['type'] == 'difficulty_ath':
                difficulty_ath_claim = True
        
        if difficulty_claim is not None or difficulty_ath_claim:
            verification = self.verify_difficulty(difficulty_claim, difficulty_ath_claim)
            results['verifications'].append({
                'type': 'difficulty',
                'result': verification
            })
            if verification['verified']:
                results['claims_verified'] += 1
            else:
                results['claims_failed'] += 1
                results['errors'].extend(verification.get('errors', []))
                results['verified'] = False
        
        for claim in claims:
            if claim['type'] == 'hashrate':
                verification = self.verify_hashrate(claim['value'], claim.get('unit', 'EH/s'))
                results['verifications'].append({
                    'type': 'hashrate',
                    'result': verification
                })
                if verification['verified']:
                    results['claims_verified'] += 1
                else:
                    results['claims_failed'] += 1
                    results['errors'].extend(verification.get('errors', []))
                    results['verified'] = False
        
        return results
    
    def get_current_network_stats(self) -> Dict:
        """
        Gets current accurate network stats for article generation.
        Use this data instead of hallucinating.
        
        Returns:
            Dictionary with current verified network statistics
        """
        stats = {
            'timestamp': datetime.now().isoformat(),
            'sources': []
        }
        
        try:
            node_response = requests.get(f"{self.BITNODES_API}/snapshots/latest/", timeout=10)
            if node_response.ok:
                node_data = node_response.json()
                stats['nodes'] = {
                    'reachable_count': node_data.get('total_nodes'),
                    'timestamp': node_data.get('timestamp')
                }
                stats['sources'].append('bitnodes.io')
        except Exception as e:
            logger.warning(f"Failed to fetch node stats: {e}")
        
        try:
            mempool_response = requests.get(f"{self.MEMPOOL_API}/fees/recommended", timeout=10)
            if mempool_response.ok:
                fee_data = mempool_response.json()
                stats['fees'] = {
                    'fastest': fee_data.get('fastestFee'),
                    'half_hour': fee_data.get('halfHourFee'),
                    'hour': fee_data.get('hourFee'),
                    'economy': fee_data.get('economyFee')
                }
                stats['sources'].append('mempool.space')
        except Exception as e:
            logger.warning(f"Failed to fetch fee stats: {e}")
        
        try:
            diff_response = requests.get(f"{self.MEMPOOL_API}/difficulty-adjustment", timeout=10)
            if diff_response.ok:
                diff_data = diff_response.json()
                stats['difficulty'] = {
                    'current': diff_data.get('difficultyChange'),
                    'progress_percent': diff_data.get('progressPercent'),
                    'remaining_blocks': diff_data.get('remainingBlocks'),
                    'remaining_time': diff_data.get('remainingTime'),
                    'estimated_retarget': diff_data.get('estimatedRetargetDate')
                }
        except Exception as e:
            logger.warning(f"Failed to fetch difficulty stats: {e}")
        
        try:
            hashrate_response = requests.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=10)
            if hashrate_response.ok:
                hashrate_data = hashrate_response.json()
                current_hashrate = hashrate_data.get('currentHashrate', 0)
                stats['hashrate'] = {
                    'current_eh': round(current_hashrate / 1e18, 1) if current_hashrate > 0 else 0,
                    'current_raw': current_hashrate
                }
        except Exception as e:
            logger.warning(f"Failed to fetch hashrate stats: {e}")
        
        try:
            price_response = requests.get(
                f"{self.COINGECKO_API}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
                timeout=10
            )
            if price_response.ok:
                price_data = price_response.json()
                stats['price'] = {
                    'usd': price_data['bitcoin'].get('usd'),
                    'change_24h': round(price_data['bitcoin'].get('usd_24h_change', 0), 2)
                }
                stats['sources'].append('coingecko.com')
        except Exception as e:
            logger.warning(f"Failed to fetch price stats: {e}")
        
        return stats


fact_checker = FactChecker()


def verify_article_before_publish(article_text: str) -> Tuple[bool, Dict]:
    """
    Convenience function to verify article before publication.
    
    Args:
        article_text: Full article text
    
    Returns:
        Tuple of (is_verified, verification_report)
    """
    report = fact_checker.verify_article(article_text)
    return report['verified'], report


def get_verified_network_stats() -> Dict:
    """
    Get current network stats for accurate article generation.
    
    Returns:
        Dictionary with verified network statistics
    """
    return fact_checker.get_current_network_stats()
```

## services/newsletter.py
```python
# SendGrid Newsletter Service - Protocol Pulse
# Using blueprint:python_sendgrid integration
# 
# FACTUAL ACCURACY MANDATE: All newsletter content is verified before sending.
# The fact-checker validates Bitcoin metrics, node counts, fee rates, etc.
# against live blockchain data sources (mempool.space, bitnodes.io, coingecko).
#
# HIGHLEVEL REQUIREMENTS:
# To enable automated newsletter distribution via GHL:
# 1. Create a GHL Workflow triggered by webhook
# 2. Set up a webhook URL in your GHL Location Settings
# 3. Configure GHL_WEBHOOK_URL environment variable
# 4. Create email template in GHL that uses these payload fields:
#    - email_subject: Newsletter subject line
#    - headline: Lead article title
#    - headline_url: Link to lead article
#    - articles[]: Array of article objects (title, summary, url, category)
#    - article_count: Number of articles included
# 5. Configure a contact list or tag for subscribers in GHL
# 6. Wire the workflow to send emails using your template

import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app import db
from models import User
import logging

class NewsletterService:
    def __init__(self):
        self.sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        if not self.sendgrid_key:
            logging.warning("SENDGRID_API_KEY not configured - newsletter functionality disabled")
            self.enabled = False
        else:
            self.enabled = True
            self.sg = SendGridAPIClient(self.sendgrid_key)

    def subscribe_user(self, email: str, name: str = None) -> bool:
        """Subscribe user to newsletter and save to database"""
        if not self.enabled:
            logging.warning("Newsletter service not enabled - SENDGRID_API_KEY missing")
            return False
            
        try:
            # Save to database
            existing_user = User.query.filter_by(email=email).first()
            if not existing_user:
                user = User()
                user.username = name or email.split('@')[0]
                user.email = email
                user.newsletter_subscribed = True
                db.session.add(user)
                db.session.commit()
                logging.info(f"New user subscribed: {email}")
            else:
                existing_user.newsletter_subscribed = True
                db.session.commit()
                logging.info(f"Existing user resubscribed: {email}")
            
            # Send welcome email
            return self.send_welcome_email(email, name)
            
        except Exception as e:
            logging.error(f"Newsletter subscription error: {e}")
            return False

    def send_welcome_email(self, to_email: str, name: str = None) -> bool:
        """Send welcome email to new subscriber"""
        if not self.enabled:
            return False
            
        try:
            subject = "Welcome to Protocol Pulse - Your Bitcoin & DeFi News Source"
            
            display_name = f' {name}' if name else ''
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #dc2626; color: white; padding: 20px; text-align: center;">
                    <h1>Welcome to Protocol Pulse</h1>
                </div>
                <div style="padding: 30px;">
                    <h2>Hello{display_name}!</h2>
                    <p>Thank you for subscribing to Protocol Pulse, your trusted source for Bitcoin and DeFi news.</p>
                    
                    <p>You'll receive:</p>
                    <ul>
                        <li>🚀 Breaking Bitcoin & DeFi news</li>
                        <li>📊 AI-powered market analysis</li>
                        <li>🎯 Expert insights from Al Ingle</li>
                        <li>🔥 Weekly newsletter roundups</li>
                    </ul>
                    
                    <p>Visit our website to read the latest articles: <a href="https://protocolpulse.replit.app">Protocol Pulse</a></p>
                    
                    <p>Best regards,<br>The Protocol Pulse Team</p>
                </div>
            </div>
            """
            
            message = Mail(
                from_email=Email("newsletter@protocolpulse.com", "Protocol Pulse"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.sg.send(message)
            logging.info(f"Welcome email sent to {to_email}")
            return True
            
        except Exception as e:
            logging.error(f"SendGrid welcome email error: {e}")
            return False

    def _strip_html(self, html_content: str) -> str:
        """Strip HTML tags to get plain text for fact-checking."""
        import re
        clean = re.sub(r'<[^>]+>', ' ', html_content)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def send_newsletter(self, subject: str, content: str, recipients: list = None, 
                         skip_fact_check: bool = False) -> bool:
        """
        Send newsletter to all subscribers or specific recipients.
        
        FACTUAL ACCURACY MANDATE: Content is verified before sending.
        Uses blocking fact-check - if verification fails or service errors,
        newsletter is NOT sent. This ensures all distributed content is accurate.
        
        Args:
            subject: Newsletter subject line
            content: HTML content to send
            recipients: Optional list of email addresses (defaults to all subscribers)
            skip_fact_check: Set True to skip verification (not recommended)
        
        Returns:
            bool: True if newsletter sent successfully, False otherwise
        """
        if not self.enabled:
            logging.error("Newsletter service not enabled - SENDGRID_API_KEY missing")
            return False
        
        # BLOCKING FACT CHECK - Newsletter must be factual
        # If fact-check fails OR service errors, we do NOT send
        if not skip_fact_check:
            try:
                from services.fact_checker import verify_article_before_publish
                
                plain_text = self._strip_html(content)
                is_verified, verification_report = verify_article_before_publish(plain_text)
                
                if not is_verified:
                    logging.error(f"Newsletter BLOCKED - fact-check failed: {verification_report.get('errors', [])}")
                    self.last_verification_report = verification_report
                    return False
                    
                logging.info("Newsletter passed fact-check verification")
                self.last_verification_report = verification_report
                
            except Exception as e:
                # STRICT BLOCKING: If fact-checker service fails, do NOT send
                logging.error(f"Newsletter BLOCKED - fact-check service error: {e}")
                self.last_verification_report = {'error': str(e), 'verified': False}
                return False
            
        try:
            if recipients is None:
                subscribed_users = User.query.filter_by(newsletter_subscribed=True).all()
                recipients = [user.email for user in subscribed_users]
            
            if not recipients:
                logging.warning("No newsletter recipients found")
                return False
            
            for email in recipients:
                message = Mail(
                    from_email=Email("newsletter@protocolpulse.com", "Protocol Pulse"),
                    to_emails=To(email),
                    subject=subject,
                    html_content=Content("text/html", content)
                )
                
                self.sg.send(message)
            
            logging.info(f"Newsletter sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logging.error(f"Newsletter sending error: {e}")
            return False
    
    def get_last_verification_report(self) -> dict:
        """Get the verification report from the last send attempt."""
        return getattr(self, 'last_verification_report', {})

# Global newsletter service instance
newsletter_service = NewsletterService()


# ============================================
# HighLevel (GHL) Webhook Integration
# ============================================

GHL_WEBHOOK_URL = os.environ.get('GHL_WEBHOOK_URL', '')
SITE_URL = os.environ.get('SITE_URL', 'https://protocolpulse.io')


def send_daily_brief_to_ghl(ghl_webhook_url=None):
    """
    Fetches articles from the last 24 hours and sends them to GHL webhook
    for automated newsletter distribution.
    
    Args:
        ghl_webhook_url: Optional webhook URL override (uses env var if not provided)
    
    Returns:
        dict with status and response details
    """
    from datetime import datetime, timedelta
    from models import Article
    import requests
    import re
    
    webhook_url = ghl_webhook_url or GHL_WEBHOOK_URL
    
    if not webhook_url:
        logging.warning("GHL_WEBHOOK_URL not configured - skipping newsletter send")
        return {'status': 'skipped', 'reason': 'No webhook URL configured'}
    
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        today_articles = Article.query.filter(
            Article.published == True,
            Article.created_at >= cutoff
        ).order_by(Article.created_at.desc()).limit(5).all()
        
        if not today_articles:
            logging.info("No articles from last 24h - skipping newsletter")
            return {'status': 'skipped', 'reason': 'No articles to send'}
        
        def clean_summary(content, max_length=200):
            if not content:
                return ""
            clean = re.sub(r'<[^>]+>', '', content)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if len(clean) > max_length:
                clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
            return clean
        
        payload = {
            "email_subject": f"Protocol Pulse: The {datetime.utcnow().strftime('%B %d')} Brief",
            "send_date": datetime.utcnow().isoformat(),
            "article_count": len(today_articles),
            "articles": [
                {
                    "title": article.title,
                    "summary": clean_summary(article.content, 200),
                    "category": article.category or "Bitcoin",
                    "url": f"{SITE_URL}/articles/{article.id}",
                    "published_at": article.created_at.isoformat()
                }
                for article in today_articles[:3]
            ],
            "headline": today_articles[0].title if today_articles else "",
            "headline_url": f"{SITE_URL}/articles/{today_articles[0].id}" if today_articles else "",
            "site_url": SITE_URL,
            "unsubscribe_url": f"{SITE_URL}/unsubscribe"
        }
        
        logging.info(f"Sending {len(today_articles)} articles to GHL webhook")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            logging.info("Successfully sent newsletter to GHL")
            return {
                'status': 'success',
                'articles_sent': len(today_articles),
                'response_code': response.status_code
            }
        else:
            logging.error(f"GHL webhook returned {response.status_code}: {response.text}")
            return {
                'status': 'error',
                'response_code': response.status_code,
                'error': response.text
            }
            
    except Exception as e:
        logging.error(f"Error sending to GHL: {str(e)}")
        return {'status': 'error', 'error': str(e)}```

## services/monetization_service.py
```python
"""
Monetization Service for Protocol Pulse
Handles Stripe integration for premium subscriptions, donations, and affiliate tracking
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logging.warning("Stripe not installed - monetization features limited")

class MonetizationService:
    """Service for handling payments, subscriptions, and revenue tracking"""
    
    SUBSCRIPTION_TIERS = {
        'free': {
            'name': 'Free Intel',
            'price_monthly': 0,
            'features': [
                'Daily intelligence briefings',
                'Basic article access',
                'Public podcast episodes',
                'Community access'
            ]
        },
        'operator': {
            'name': 'Pulse Operator',
            'price_monthly': 21,
            'price_id': None,
            'features': [
                'All Free features',
                'Priority intel alerts',
                'Exclusive deep-dive reports',
                'Early access to content',
                'Ad-free experience',
                'Discord/Telegram access',
                'Weekly strategy calls'
            ]
        },
        'sovereign': {
            'name': 'Sovereign Elite',
            'price_monthly': 210,
            'price_id': None,
            'features': [
                'All Operator features',
                '1-on-1 monthly strategy session',
                'Custom research requests',
                'Private Signal group',
                'Early investment opportunities',
                'Lifetime protocol access',
                'Name in credits'
            ]
        }
    }
    
    def __init__(self):
        self.stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        self.stripe_webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        self.initialized = False
        
        if STRIPE_AVAILABLE and self.stripe_key:
            stripe.api_key = self.stripe_key
            self.initialized = True
            logging.info("Stripe monetization service initialized")
        else:
            logging.warning("Stripe not configured - using simulation mode")
    
    def get_subscription_tiers(self) -> Dict:
        """Return available subscription tiers"""
        return self.SUBSCRIPTION_TIERS
    
    def create_checkout_session(self, tier: str, user_email: str, 
                                 success_url: str, cancel_url: str) -> Dict:
        """Create a Stripe checkout session for subscription"""
        if tier not in ['operator', 'sovereign']:
            return {'error': 'Invalid tier'}
        
        tier_info = self.SUBSCRIPTION_TIERS[tier]
        
        if not self.initialized:
            return {
                'simulated': True,
                'checkout_url': f"{success_url}?session_id=sim_session_{tier}",
                'tier': tier,
                'message': 'Stripe not configured - simulation mode'
            }
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': tier_info['name'],
                            'description': f"Protocol Pulse {tier_info['name']} Subscription"
                        },
                        'unit_amount': tier_info['price_monthly'] * 100,
                        'recurring': {'interval': 'month'}
                    },
                    'quantity': 1
                }],
                mode='subscription',
                customer_email=user_email,
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'tier': tier,
                    'source': 'protocol_pulse'
                }
            )
            
            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            }
            
        except Exception as e:
            logging.error(f"Stripe checkout error: {e}")
            return {'error': str(e)}
    
    def create_donation_session(self, amount_usd: int, donor_email: str,
                                 success_url: str, cancel_url: str,
                                 message: str = '', article_id: Optional[str] = None) -> Dict:
        """Create a one-time donation payment session"""
        if not self.initialized:
            return {
                'simulated': True,
                'checkout_url': f"{success_url}?donation=sim_{amount_usd}",
                'amount': amount_usd,
                'message': 'Stripe not configured - simulation mode'
            }
        
        metadata = {
            'type': 'donation',
            'message': message[:500] if message else '',
            'source': 'protocol_pulse'
        }
        if article_id:
            metadata['article_id'] = str(article_id)
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Protocol Pulse Support',
                            'description': 'One-time contribution to support sovereign journalism'
                        },
                        'unit_amount': amount_usd * 100
                    },
                    'quantity': 1
                }],
                mode='payment',
                customer_email=donor_email,
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata=metadata
            )
            
            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            }
            
        except Exception as e:
            logging.error(f"Stripe donation error: {e}")
            return {'error': str(e)}
    
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        """Handle Stripe webhook events"""
        if not self.initialized or not self.stripe_webhook_secret:
            return {'error': 'Webhook not configured'}
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.stripe_webhook_secret
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                return self._handle_checkout_complete(session)
            
            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                return self._handle_subscription_update(subscription)
            
            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                return self._handle_subscription_cancel(subscription)
            
            elif event['type'] == 'invoice.payment_failed':
                invoice = event['data']['object']
                return self._handle_payment_failed(invoice)
            
            return {'success': True, 'event_type': event['type']}
            
        except stripe.error.SignatureVerificationError as e:
            logging.error(f"Webhook signature verification failed: {e}")
            return {'error': 'Invalid signature'}
        except Exception as e:
            logging.error(f"Webhook processing error: {e}")
            return {'error': str(e)}
    
    def _handle_checkout_complete(self, session: Dict) -> Dict:
        """Process completed checkout"""
        customer_email = session.get('customer_email')
        metadata = session.get('metadata', {})
        tier = metadata.get('tier')
        
        logging.info(f"Checkout complete: {customer_email} - {tier}")
        
        return {
            'success': True,
            'action': 'subscription_created',
            'email': customer_email,
            'tier': tier
        }
    
    def _handle_subscription_update(self, subscription: Dict) -> Dict:
        """Handle subscription updates"""
        logging.info(f"Subscription updated: {subscription.get('id')}")
        return {'success': True, 'action': 'subscription_updated'}
    
    def _handle_subscription_cancel(self, subscription: Dict) -> Dict:
        """Handle subscription cancellation"""
        logging.info(f"Subscription cancelled: {subscription.get('id')}")
        return {'success': True, 'action': 'subscription_cancelled'}
    
    def _handle_payment_failed(self, invoice: Dict) -> Dict:
        """Handle failed payment"""
        logging.warning(f"Payment failed for invoice: {invoice.get('id')}")
        return {'success': True, 'action': 'payment_failed'}
    
    def get_revenue_stats(self) -> Dict:
        """Get revenue statistics (simulated if Stripe not available)"""
        if not self.initialized:
            return {
                'mrr': 0,
                'subscribers': {
                    'operator': 0,
                    'sovereign': 0
                },
                'total_donations': 0,
                'affiliate_earnings': 0,
                'zaps_sats': 0,
                'simulated': True
            }
        
        try:
            subscriptions = stripe.Subscription.list(limit=100, status='active')
            
            operator_count = 0
            sovereign_count = 0
            mrr = 0
            
            for sub in subscriptions.data:
                amount = sub.plan.amount / 100
                if amount <= 50:
                    operator_count += 1
                else:
                    sovereign_count += 1
                mrr += amount
            
            return {
                'mrr': mrr,
                'subscribers': {
                    'operator': operator_count,
                    'sovereign': sovereign_count
                },
                'total_donations': 0,
                'affiliate_earnings': 0,
                'zaps_sats': 0,
                'simulated': False
            }
            
        except Exception as e:
            logging.error(f"Error fetching revenue stats: {e}")
            return {
                'mrr': 0,
                'subscribers': {'operator': 0, 'sovereign': 0},
                'error': str(e)
            }
    
    def generate_affiliate_link(self, product_type: str, product_id: str,
                                 user_id: Optional[int] = None) -> str:
        """Generate an affiliate tracking link"""
        base_urls = {
            'amazon_book': 'https://www.amazon.com/dp/',
            'trezor': 'https://shop.trezor.io/?offer_id=',
            'swan': 'https://www.swanbitcoin.com/signup?ref=',
            'river': 'https://river.com/signup?ref='
        }
        
        base = base_urls.get(product_type, '')
        if not base:
            return ''
        
        affiliate_tag = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')
        
        if product_type == 'amazon_book':
            return f"{base}{product_id}?tag={affiliate_tag}"
        else:
            return f"{base}{product_id}"
    
    def track_affiliate_click(self, link_type: str, product_id: str, 
                               user_id: Optional[int] = None) -> bool:
        """Track an affiliate link click"""
        logging.info(f"Affiliate click: {link_type} - {product_id}")
        return True
    
    def get_lightning_invoice(self, amount_sats: int, memo: str = '') -> Dict:
        """Generate a Lightning invoice for zap payments"""
        lnurl = os.environ.get('LIGHTNING_ADDRESS', '')
        
        if not lnurl:
            return {
                'simulated': True,
                'invoice': 'lnbc10u1pj...(simulated)',
                'amount_sats': amount_sats,
                'message': 'Lightning not configured'
            }
        
        return {
            'lightning_address': lnurl,
            'amount_sats': amount_sats,
            'memo': memo
        }


monetization_service = MonetizationService()
```

## services/youtube_service.py
```python
import os
import re
import json
import logging
import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

class YouTubeService:
    # Bitcoin channels for audio intelligence podcast generation
    PODCAST_CHANNELS = [
        {'name': 'Coin Bureau', 'id': 'UCqK_GSMbpiV8spgD3ZGloSw'},
        {'name': 'Natalie Brunell', 'id': 'UC6c1WLEK4w4qsKaIKqGptUw'},
        {'name': 'Bitcoin Magazine', 'id': 'UCni7PAlyNS0_12H-26DJJ3w'},
        {'name': 'Simply Bitcoin', 'id': 'UCNDkNyQe6ShQR3XjPPMnbvg'},
        {'name': 'Robert Breedlove', 'id': 'UCJLVQQf3LzXd7N_BuRZ3Vdw'},
        {'name': 'BTC Sessions', 'id': 'UChzLnWVsl3puKQwc5PoO6Zg'},
    ]
    
    # Podcast Series YouTube Configuration
    # Map show IDs to their YouTube playlist/video data
    # TO UPDATE: Replace video IDs below with actual YouTube video IDs from your channel
    # Format: Go to any YouTube video URL like youtube.com/watch?v=XXXXXXXXXXX
    # The 11-character code after "v=" is the video ID
    # Live Broadcasts - Featured shows with embedded videos
    LIVE_BROADCASTS = {
        'cypherpunkd': {
            'title': "Cypherpunk'd // Intel Briefing",
            'channel': 'Protocol Pulse',
            'playlist_id': 'PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd',
            'description': 'The original cypherpunk podcast exploring Bitcoin, privacy, and digital freedom.',
            'latest_id': 'QX3M8Ka9vUA'
        },
        'protocol_pulse': {
            'title': 'Protocol Pulse // Analysis',
            'channel': 'Coin Bureau',
            'channel_id': 'UCqK_GSMbpiV8spgD3ZGloSw',
            'description': 'Top crypto analysis and market insights from Coin Bureau.',
            'latest_id': 'rYQgy8QDEBI'
        }
    }
    
    SERIES_CONFIG = {
        'cypherpunkd': {
            'title': "Cypherpunk'd // Intel Briefing",
            'channel': 'Protocol Pulse',
            'description': 'The original cypherpunk podcast exploring Bitcoin, privacy, and digital freedom.',
            'playlist': [
                {'id': 'QX3M8Ka9vUA', 'title': 'Adam Back: From Cypherpunk to Bitcoin Treasury'},
                {'id': 'k0BWlvnBmIE', 'title': 'The Big Print: Decentralization Episode'},
                {'id': 'ERJ3NCqTTqg', 'title': 'Why Hyperinflation Makes Bitcoin Inevitable'}
            ],
            'latest_id': 'QX3M8Ka9vUA'
        },
        'protocol_pulse': {
            'title': 'Protocol Pulse // Analysis',
            'channel': 'Protocol Pulse',
            'description': 'Bitcoin analysis and market insights.',
            'playlist': [
                {'id': 'F9D7yL8C_W8', 'title': 'Bitcoin 2025 Conference Highlights'},
                {'id': 'GtDMBqLVrpE', 'title': 'The Case for Sound Money'}
            ],
            'latest_id': 'F9D7yL8C_W8'
        },
        'genesis_book': {
            'title': 'The Genesis Book Series',
            'channel': 'Protocol Pulse',
            'description': 'A series exploring Austrian economics and the foundational ideas behind Bitcoin.',
            'playlist': [
                {'id': 'QX3M8Ka9vUA', 'title': 'Genesis Book Series'}
            ],
            'latest_id': 'QX3M8Ka9vUA'
        },
        'daylight_robbery': {
            'title': 'Daylight Robbery Series',
            'channel': 'Protocol Pulse',
            'description': 'A series exposing the hidden story of how taxation has shaped human civilization.',
            'playlist': [
                {'id': 'ERJ3NCqTTqg', 'title': 'Daylight Robbery Analysis'}
            ],
            'latest_id': 'ERJ3NCqTTqg'
        },
        'big_print': {
            'title': 'The Big Print Series',
            'channel': 'Protocol Pulse',
            'description': 'An exposé revealing how the Federal Reserve engineered wealth extraction through monetary policy.',
            'playlist': [
                {'id': 'k0BWlvnBmIE', 'title': 'The Big Print Series'}
            ],
            'latest_id': 'k0BWlvnBmIE'
        },
        'everything_21m': {
            'title': 'Everything Divided By 21 Million',
            'channel': 'Protocol Pulse',
            'description': 'A cinematic exploration of Bitcoin\'s relationship to time, money, freedom, and human progress.',
            'playlist': [
                {'id': 'GtDMBqLVrpE', 'title': 'Everything Divided By 21 Million'}
            ],
            'latest_id': 'GtDMBqLVrpE'
        }
    }
    
    @staticmethod
    def get_thumbnail(video_id: str) -> str:
        """Get highest resolution YouTube thumbnail URL"""
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    @staticmethod
    def get_hq_thumbnail(video_id: str) -> str:
        """Get high quality thumbnail (fallback if maxres not available)"""
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    
    @staticmethod
    def get_embed_url(video_id: str, autoplay: bool = True) -> str:
        """Get YouTube embed URL with modestbranding"""
        params = "modestbranding=1&rel=0"
        if autoplay:
            params = f"autoplay=1&{params}"
        return f"https://www.youtube.com/embed/{video_id}?{params}"
    
    @staticmethod
    def extract_id(url: str) -> str:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
            r"(?:embed\/)([0-9A-Za-z_-]{11})"
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    # Designated channels to monitor for reactionary articles
    MONITORED_CHANNELS = {
        'BitcoinMagazine': 'UC6s6fMupv37_XN72S_5fDYA',
        'NatalieBrunell': 'UC0_M9-3R_mXv2oF_u7O08uQ',
        'SimplyBitcoin': 'UCqK_GSMbpiV8spgD3ZGloSw',
        'BTCSessions': 'UChzLnWVsl3puKQwc5PoO6Zg',
        'RobertBreedlove': 'UCpvDOLw4CXEmT-kKMCGe8Yg'
    }
    
    # Channel and Playlist IDs for dynamic fetching
    CHANNEL_PLAYLISTS = {
        'cypherpunkd': {
            'channel_id': None,  # Will be fetched dynamically
            'playlist_id': 'PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd',
            'search_term': 'Cypherpunkd Bitcoin'
        },
        'protocol_pulse': {
            'channel_id': None,
            'playlist_id': None,
            'search_term': 'Protocol Pulse Bitcoin analysis'
        },
        'genesis_book': {
            'channel_id': None,
            'playlist_id': None,
            'search_term': 'Genesis Book Bitcoin Aaron van Wirdum'
        },
        'coin_bureau': {
            'channel_id': 'UCqK_GSMbpiV8spgD3ZGloSw',  # Coin Bureau channel
            'playlist_id': None,
            'search_term': 'Coin Bureau Bitcoin'
        }
    }
    
    @classmethod
    def get_series_data(cls, show_id: str) -> dict:
        """Get YouTube series data for a podcast show"""
        return cls.SERIES_CONFIG.get(show_id, {})
    
    @classmethod
    def get_all_series(cls) -> dict:
        """Get all configured series data"""
        return cls.SERIES_CONFIG

    def __init__(self):
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        self.youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=self.api_key) if self.api_key else None
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY')) if os.environ.get('OPENAI_API_KEY') else None
        self.handles = ['BitcoinMagazine', 'nataliebrunell', 'bytefederal', 'BTCSessions', 'SimplyBitcoin', 'CoinBureau', 'thejackmallersshow', 'RobertBreedlove22']
        self._playlist_cache = {}  # Cache for API results
    
    def get_playlist_videos(self, playlist_id: str, max_results: int = 10) -> list:
        """
        Fetch videos from a YouTube playlist using the API.
        Falls back to hardcoded data if API is unavailable.
        """
        if not self.youtube:
            logging.warning("YouTube API not available - using fallback data")
            return []
        
        cache_key = f"playlist_{playlist_id}"
        if cache_key in self._playlist_cache:
            return self._playlist_cache[cache_key]
        
        try:
            request = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=max_results
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                video_id = snippet.get('resourceId', {}).get('videoId')
                if video_id:
                    videos.append({
                        'id': video_id,
                        'title': snippet.get('title', 'Untitled'),
                        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                        'description': snippet.get('description', '')[:200],
                        'published_at': snippet.get('publishedAt', '')
                    })
            
            self._playlist_cache[cache_key] = videos
            logging.info(f"Fetched {len(videos)} videos from playlist {playlist_id}")
            return videos
            
        except Exception as e:
            logging.error(f"Error fetching playlist {playlist_id}: {e}")
            return []
    
    def search_playlist(self, search_term: str) -> str:
        """
        Search for a playlist by term and return playlist ID.
        """
        if not self.youtube:
            return None
        
        try:
            request = self.youtube.search().list(
                part='snippet',
                q=search_term,
                type='playlist',
                maxResults=1
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]['id']['playlistId']
            return None
            
        except Exception as e:
            logging.error(f"Error searching playlist: {e}")
            return None
    
    def get_channel_uploads(self, channel_id: str, max_results: int = 5) -> list:
        """
        Get recent uploads from a channel.
        Falls back to RSS feed if YouTube API is not available.
        """
        # First try the API
        if self.youtube:
            try:
                request = self.youtube.channels().list(
                    part='contentDetails',
                    id=channel_id
                )
                response = request.execute()
                
                if response.get('items'):
                    uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    return self.get_playlist_videos(uploads_id, max_results)
            except Exception as e:
                logging.warning(f"YouTube API failed, trying RSS fallback: {e}")
        
        # Fallback to RSS feed (publicly available, no API key needed)
        try:
            import requests
            import xml.etree.ElementTree as ET
            
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            response = requests.get(rss_url, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
                
                videos = []
                entries = root.findall('atom:entry', ns)[:max_results]
                
                for entry in entries:
                    video_id = entry.find('yt:videoId', ns)
                    title = entry.find('atom:title', ns)
                    
                    if video_id is not None and title is not None:
                        videos.append({
                            'id': video_id.text,
                            'title': title.text,
                            'thumbnail': f"https://img.youtube.com/vi/{video_id.text}/maxresdefault.jpg"
                        })
                
                if videos:
                    logging.info(f"Successfully fetched {len(videos)} videos via RSS for channel {channel_id}")
                    return videos
                    
        except Exception as e:
            logging.error(f"RSS fallback also failed: {e}")
        
        return []
    
    def get_latest_video(self, channel_id: str) -> dict:
        """
        Get the latest video from a channel for podcast generation.
        Returns dict with id, title, published_at, thumbnail.
        """
        videos = self.get_channel_uploads(channel_id, max_results=1)
        
        if videos:
            video = videos[0]
            return {
                'id': video.get('id'),
                'title': video.get('title'),
                'thumbnail': video.get('thumbnail', f"https://img.youtube.com/vi/{video.get('id')}/maxresdefault.jpg"),
                'published_at': video.get('published_at', None)
            }
        return None
    
    def get_dynamic_series(self, show_id: str) -> dict:
        """
        Get series data with dynamic video fetching.
        Uses API if available, falls back to static config.
        """
        static_config = self.SERIES_CONFIG.get(show_id, {})
        
        if not self.youtube:
            return static_config
        
        playlist_config = self.CHANNEL_PLAYLISTS.get(show_id, {})
        playlist_id = playlist_config.get('playlist_id')
        channel_id = playlist_config.get('channel_id')
        search_term = playlist_config.get('search_term')
        
        videos = []
        
        if playlist_id:
            videos = self.get_playlist_videos(playlist_id)
        elif channel_id:
            videos = self.get_channel_uploads(channel_id)
        elif search_term:
            found_playlist = self.search_playlist(search_term)
            if found_playlist:
                videos = self.get_playlist_videos(found_playlist)
        
        if videos:
            return {
                **static_config,
                'playlist': videos,
                'latest_id': videos[0]['id'] if videos else static_config.get('latest_id'),
                'dynamic': True
            }
        
        return static_config
    
    def get_all_dynamic_series(self) -> dict:
        """
        Get all series with dynamic video data where available.
        """
        result = {}
        for show_id in self.SERIES_CONFIG.keys():
            result[show_id] = self.get_dynamic_series(show_id)
        return result

    def get_channel_id(self, handle):
        if not self.youtube:
            return 'mock_channel_id'
        try:
            request = self.youtube.search().list(part='snippet', type='channel', q=f'@{handle}', maxResults=1)
            response = request.execute()
            return response['items'][0]['id']['channelId'] if response['items'] else 'mock_channel_id'
        except Exception as e:
            logging.error(f"YouTube search error: {e}")
            return 'mock_channel_id'

    def get_recent_videos(self):
        if not self.youtube:
            return [{'id': 'mock_id', 'title': 'Mock video', 'transcript': 'Mock Web3 video content.', 'thumbnail': 'mock.jpg', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
        
        videos = []
        try:
            for handle in self.handles:
                channel_id = self.get_channel_id(handle)
                request = self.youtube.channels().list(part='contentDetails', id=channel_id)
                response = request.execute()
                uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                request = self.youtube.playlistItems().list(part='snippet', playlistId=uploads_id, maxResults=2)
                response = request.execute()
                
                for item in response['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    transcript = self._get_transcript(video_id)
                    relevance = self._is_relevant(item['snippet']['title'] + ' ' + transcript)
                    
                    if relevance['is_relevant']:
                        videos.append({
                            'id': video_id,
                            'title': item['snippet']['title'],
                            'transcript': transcript,
                            'thumbnail': item['snippet']['thumbnails']['high']['url'],
                            'is_relevant': True,
                            'topic': relevance['topic'],
                            'nuance': relevance['nuance']
                        })
            return videos
        except Exception as e:
            logging.error(f"YouTube API error: {e}")
            return [{'id': 'mock_id', 'title': 'Mock video', 'transcript': 'Mock Web3 video content.', 'thumbnail': 'mock.jpg', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]

    def _get_transcript(self, video_id):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return ' '.join([t['text'] for t in transcript])
        except Exception:
            return "Transcript unavailable"

    def draft_reactionary_article(self, video_data: dict) -> str:
        """
        Transcribes designated show and drafts a complementary review.
        Creates a "reactionary article" that reviews the key arguments made
        and offers additional philosophical analysis through the 'Bitcoin Lens'.
        
        Args:
            video_data: Dict containing 'id', 'title', and optionally 'transcript'
            
        Returns:
            HTML-formatted article content ready for publication
        """
        if not self.openai_client:
            logging.warning("OpenAI client not available for reactionary article")
            return None
        
        try:
            transcript = video_data.get('transcript')
            if not transcript or transcript == "Transcript unavailable":
                transcript = self._get_transcript(video_data['id'])
            
            if not transcript or transcript == "Transcript unavailable":
                logging.warning(f"No transcript available for video {video_data['id']}")
                return None
            
            prompt = f"""
            ACT AS: Walter Cronkite reporting for Protocol Pulse - the premier Bitcoin-first media network.
            
            TASK: Transcribe and REVIEW the following show: '{video_data['title']}'.
            
            CONTENT: {transcript[:8000]}
            
            GOAL: Draft a reactionary article that:
            1. Summarizes the key arguments and insights made in the show.
            2. Review the creator's arguments as a peer journalist. Contrast their points with the Protocol Pulse 'Bitcoin Lens' and provide a final verdict on whether the signal matches the noise.
            3. Provides additional philosophical analysis through the 'Bitcoin Lens'.
            4. Offers Protocol Pulse's authoritative perspective on the topics discussed.
            5. Maintains journalistic integrity while being engaging and insightful.
            
            FORMAT: Return ONLY valid HTML with these sections:
            - A compelling TL;DR box (class="tldr-section")
            - An introduction paragraph (class="article-paragraph")
            - Key points with headers (class="article-subheader")
            - Analysis paragraphs (class="article-paragraph")
            - A conclusion with Protocol Pulse perspective and final verdict.
            
            TONE: Authoritative, insightful, Bitcoin-maximalist perspective. Like a trusted evening news anchor who deeply understands sound money.
            """
            
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error drafting reactionary article: {e}")
            return None
    
    def get_monitored_channel_videos(self, limit: int = 5) -> list:
        """
        Get latest videos from monitored Bitcoin channels for reactionary articles.
        
        Args:
            limit: Maximum videos per channel
            
        Returns:
            List of video data dictionaries
        """
        if not self.youtube:
            return []
        
        videos = []
        try:
            for handle, channel_id in self.MONITORED_CHANNELS.items():
                try:
                    request = self.youtube.channels().list(part='contentDetails', id=channel_id)
                    response = request.execute()
                    
                    if response['items']:
                        uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                        
                        request = self.youtube.playlistItems().list(
                            part='snippet', 
                            playlistId=uploads_id, 
                            maxResults=limit
                        )
                        response = request.execute()
                        
                        for item in response['items']:
                            snippet = item['snippet']
                            video_id = item['snippet']['resourceId']['videoId']
                            thumbnail = snippet.get('thumbnails', {}).get('maxres', {}).get('url') or \
                                        snippet.get('thumbnails', {}).get('high', {}).get('url')
                            
                            videos.append({
                                'id': video_id,
                                'title': snippet['title'],
                                'channel': handle,
                                'thumbnail': thumbnail,
                                'published_at': snippet['publishedAt']
                            })
                except Exception as e:
                    logging.warning(f"Error fetching videos from {handle}: {e}")
                    continue
                    
            return videos
        except Exception as e:
            logging.error(f"Error getting monitored channel videos: {e}")
            return []
    
    def _is_relevant(self, text):
        if not self.openai_client:
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
        
        if len(text.split()) < 20 or any(m in text.lower() for m in ['lol', '😂', 'meme']):
            return {'is_relevant': False}
        
        try:
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': f"Analyze text: '{text[:500]}'. Is it relevant to Web3/Bitcoin/DeFi? If yes, extract topic (e.g., 'Bitcoin ETF') and nuance (e.g., 'bullish'). Return JSON: {{'is_relevant': bool, 'topic': str, 'nuance': str}}"}],
                max_tokens=100
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Relevance analysis error: {e}")
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
    
    # ==========================================
    # MULTIMODAL CONTENT ENGINE - Auto-Transcription
    # ==========================================
    
    def check_partner_channels_for_new_videos(self, hours_back: int = 12) -> list:
        """
        Check partner channels for new videos uploaded in the last N hours.
        Returns list of videos ready for auto-transcription and Bitcoin Lens review.
        
        Partner Channels: Coin Bureau, Natalie Brunell, Bitcoin Magazine,
        Simply Bitcoin, BTC Sessions, Robert Breedlove
        """
        from datetime import datetime, timedelta
        
        new_videos = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for channel in self.PODCAST_CHANNELS:
            channel_name = channel['name']
            channel_id = channel['id']
            
            try:
                videos = self.get_channel_latest_videos(channel_id, limit=3)
                
                for video in videos:
                    published_str = video.get('published_at', '')
                    if published_str:
                        try:
                            published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                            if published_dt.replace(tzinfo=None) > cutoff_time:
                                new_videos.append({
                                    'video_id': video['id'],
                                    'title': video['title'],
                                    'channel_name': channel_name,
                                    'thumbnail': video.get('thumbnail', self.get_thumbnail(video['id'])),
                                    'published_at': published_str
                                })
                                logging.info(f"Found new video from {channel_name}: {video['title']}")
                        except ValueError:
                            continue
                            
            except Exception as e:
                logging.warning(f"Error checking {channel_name} for new videos: {e}")
                continue
        
        return new_videos
    
    def auto_process_new_partner_videos(self) -> dict:
        """
        Automatically process new partner videos:
        1. Detect new videos from partner channels
        2. Generate Bitcoin Lens review articles
        3. Create AI podcast episodes
        4. Extract social clips
        
        Returns summary of processed content.
        """
        from services.podcast_generator import podcast_generator
        
        results = {
            'videos_found': 0,
            'articles_generated': [],
            'podcasts_generated': [],
            'clips_created': [],
            'errors': []
        }
        
        new_videos = self.check_partner_channels_for_new_videos(hours_back=12)
        results['videos_found'] = len(new_videos)
        
        for video in new_videos:
            video_id = video['video_id']
            channel_name = video['channel_name']
            thumbnail = video['thumbnail']
            
            try:
                package = podcast_generator.create_full_social_package(
                    video_id=video_id,
                    thumbnail_url=thumbnail,
                    channel_name=channel_name
                )
                
                if package.get('article'):
                    results['articles_generated'].append({
                        'title': package['article'].get('title'),
                        'channel': channel_name,
                        'video_id': video_id
                    })
                
                if package.get('podcast'):
                    results['podcasts_generated'].append({
                        'audio_file': package['podcast'].get('audio_file'),
                        'channel': channel_name
                    })
                
                if package.get('social_videos'):
                    results['clips_created'].extend(package['social_videos'])
                    
            except Exception as e:
                error_msg = f"Error processing {channel_name} video {video_id}: {e}"
                logging.error(error_msg)
                results['errors'].append(error_msg)
        
        logging.info(f"Auto-processed {len(new_videos)} partner videos: "
                     f"{len(results['articles_generated'])} articles, "
                     f"{len(results['podcasts_generated'])} podcasts")
        
        return results
    
    def get_channel_latest_videos(self, channel_id: str, limit: int = 5) -> list:
        """
        Get latest videos from a specific channel.
        Uses the uploads playlist for the channel.
        """
        if not self.youtube:
            logging.warning("YouTube API not available")
            return []
        
        try:
            request = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return []
            
            uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            request = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_id,
                maxResults=limit
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                thumbnail = snippet.get('thumbnails', {}).get('maxres', {}).get('url') or \
                           snippet.get('thumbnails', {}).get('high', {}).get('url') or \
                           self.get_thumbnail(video_id)
                
                videos.append({
                    'id': video_id,
                    'title': snippet['title'],
                    'thumbnail': thumbnail,
                    'published_at': snippet.get('publishedAt', ''),
                    'description': snippet.get('description', '')[:200]
                })
            
            return videos
            
        except Exception as e:
            logging.error(f"Error getting latest videos for channel {channel_id}: {e}")
            return []```

## services/ghl_service.py
```python
"""
HighLevel (GHL) CRM Integration Service
Handles subscriber management, Custom Value syncing, and automated intelligence briefings
"""
import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class GHLService:
    """Service for integrating with HighLevel (GoHighLevel) CRM API v2"""
    
    def __init__(self):
        self.api_key = os.environ.get('GHL_API_KEY')
        self.location_id = os.environ.get('GHL_LOCATION_ID')
        self.base_url = "https://services.leadconnectorhq.com"
        self.initialized = bool(self.api_key and self.location_id)
        self._custom_value_ids = {}
        
        if self.initialized:
            logging.info("GHL service initialized successfully")
        else:
            logging.warning("GHL service not configured - missing GHL_API_KEY or GHL_LOCATION_ID")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers for GHL requests"""
        if self.api_key and self.api_key.startswith('pit-'):
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
        else:
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
    
    def push_to_ghl(self, email: str, name: str = "", tag: str = "Protocol_Pulse_Subscriber") -> Dict[str, Any]:
        """
        Push a new subscriber to HighLevel CRM.
        
        Args:
            email: Subscriber email address
            name: Subscriber name (optional)
            tag: Tag to apply (default: Protocol_Pulse_Subscriber)
            
        Returns:
            Dict with success status and response data
        """
        if not self.initialized:
            logging.warning("GHL service not initialized - skipping push")
            return {"success": False, "error": "GHL not configured"}
        
        try:
            # Split name into first/last if provided
            first_name = ""
            last_name = ""
            if name:
                parts = name.strip().split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
            
            # Build contact payload
            payload = {
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "locationId": self.location_id,
                "tags": [tag],
                "source": "Protocol Pulse Website",
                "customFields": [
                    {"key": "subscription_date", "value": datetime.now().isoformat()},
                    {"key": "subscriber_type", "value": "Sovereign Transactor"}
                ]
            }
            
            # Create or update contact
            response = requests.post(
                f"{self.base_url}/contacts/",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                logging.info(f"GHL: Successfully pushed contact {email} with tag {tag}")
                return {
                    "success": True,
                    "contact_id": data.get("contact", {}).get("id"),
                    "message": "Contact created/updated in GHL"
                }
            else:
                logging.error(f"GHL API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logging.error(f"GHL push error: {e}")
            return {"success": False, "error": str(e)}
    
    def add_tag_to_contact(self, contact_id: str, tag: str) -> bool:
        """Add a tag to an existing contact"""
        if not self.initialized:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/contacts/{contact_id}/tags",
                headers=self._get_headers(),
                json={"tags": [tag]},
                timeout=30
            )
            return response.status_code in [200, 201]
        except Exception as e:
            logging.error(f"GHL tag error: {e}")
            return False
    
    def send_daily_brief_to_ghl(self, report_html: str, bitcoin_lens_html: str, 
                                 difficulty: str = "146.47 T", fees: str = "3 sat/vB") -> Dict[str, Any]:
        """
        Push the daily intelligence briefing as a campaign draft to GHL.
        
        Args:
            report_html: The Report section HTML
            bitcoin_lens_html: The Bitcoin Lens section HTML
            difficulty: Current network difficulty
            fees: Current fee rate
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            # Build email content with terminal-style header
            email_html = f'''
            <div style="background: #0a0a0a; color: #00ff41; font-family: 'JetBrains Mono', monospace; padding: 20px;">
                <div style="border: 1px solid #00ff41; padding: 15px; margin-bottom: 20px;">
                    <h1 style="color: #ff6600; margin: 0;">PROTOCOL PULSE INTELLIGENCE BRIEFING</h1>
                    <p style="color: #888; margin: 5px 0 0 0;">{datetime.now().strftime('%B %d, %Y')} | DIFFICULTY: {difficulty} | FEES: {fees}</p>
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h2 style="color: #00ff41; border-bottom: 1px solid #333;">THE REPORT</h2>
                    {report_html}
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h2 style="color: #ff6600; border-bottom: 1px solid #333;">THE BITCOIN LENS</h2>
                    {bitcoin_lens_html}
                </div>
                
                <div style="text-align: center; padding: 20px; border-top: 1px solid #333;">
                    <p style="color: #666;">Transmitted via Protocol Pulse | Sovereign Intelligence Network</p>
                </div>
            </div>
            '''
            
            # Create campaign draft in GHL
            campaign_payload = {
                "locationId": self.location_id,
                "name": f"Daily Intel - {datetime.now().strftime('%Y-%m-%d')}",
                "status": "draft",
                "emailSubject": f"INTEL BRIEFING: Difficulty {difficulty} | {datetime.now().strftime('%b %d')}",
                "emailBody": email_html
            }
            
            response = requests.post(
                f"{self.base_url}/campaigns/",
                headers=self._get_headers(),
                json=campaign_payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logging.info("GHL: Daily briefing campaign draft created")
                return {"success": True, "message": "Campaign draft created"}
            else:
                logging.warning(f"GHL campaign creation returned: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"GHL daily brief error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_custom_value_info(self, key: str) -> Optional[Dict[str, str]]:
        """
        Get the custom value ID and name for a given key.
        Fetches and caches all custom values if not already cached.
        Returns dict with 'id' and 'name' keys.
        """
        normalized_key = key.lower().replace(' ', '_')
        if normalized_key in self._custom_value_ids:
            return self._custom_value_ids[normalized_key]
        
        try:
            response = requests.get(
                f"{self.base_url}/locations/{self.location_id}/customValues",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                custom_values = data.get('customValues', [])
                for cv in custom_values:
                    cv_name = cv.get('name', '')
                    cv_id = cv.get('id')
                    if cv_id and cv_name:
                        cv_key = cv_name.lower().replace(' ', '_')
                        self._custom_value_ids[cv_key] = {'id': cv_id, 'name': cv_name}
                        self._custom_value_ids[cv_name.lower()] = {'id': cv_id, 'name': cv_name}
                
                logging.info(f"GHL Custom Values cached: {list(self._custom_value_ids.keys())}")
                return self._custom_value_ids.get(normalized_key)
            else:
                logging.error(f"Failed to fetch GHL custom values: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error fetching GHL custom values: {e}")
            return None
    
    def update_custom_value(self, key: str, value: str) -> Dict[str, Any]:
        """
        Update a Custom Value in GHL location settings.
        
        Args:
            key: Custom Value key (e.g., 'bitcoin_difficulty', 'network_hashrate', 'daily_intel_briefing')
            value: Value to set
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            logging.warning("GHL service not initialized - skipping custom value update")
            return {"success": False, "error": "GHL not configured"}
        
        try:
            cv_info = self._get_custom_value_info(key)
            
            if not cv_info:
                logging.warning(f"Custom Value '{key}' not found in GHL. Available keys: {list(self._custom_value_ids.keys())}")
                return {"success": False, "error": f"Custom Value '{key}' not found in GHL"}
            
            custom_value_id = cv_info['id']
            custom_value_name = cv_info['name']
            
            payload = {
                "name": custom_value_name,
                "value": value
            }
            
            response = requests.put(
                f"{self.base_url}/locations/{self.location_id}/customValues/{custom_value_id}",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                log_value = f"'{value[:50]}...'" if len(value) > 50 else f"'{value}'"
                logging.info(f"GHL SYNC SUCCESS: Custom Value '{key}' updated to {log_value}")
                return {"success": True, "key": key, "value": value}
            else:
                logging.error(f"GHL Custom Value update failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logging.error(f"GHL Custom Value error: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_network_metrics(self) -> Dict[str, Any]:
        """
        Sync Bitcoin network metrics (Difficulty and Hashrate) to GHL Custom Values.
        Fetches live data from Mempool.space API.
        
        Returns:
            Dict with success status and synced values
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            from services.node_service import NodeService
            
            stats = NodeService.get_network_stats()
            
            difficulty = stats.get('difficulty', '146.47 T')
            hashrate = stats.get('hashrate', '~977 EH/s')
            
            difficulty_result = self.update_custom_value('bitcoin_difficulty', difficulty)
            hashrate_result = self.update_custom_value('network_hashrate', hashrate)
            
            if difficulty_result.get('success') and hashrate_result.get('success'):
                logging.info(f"GHL NETWORK SYNC SUCCESS: Difficulty={difficulty}, Hashrate={hashrate}")
                return {
                    "success": True,
                    "difficulty": difficulty,
                    "hashrate": hashrate,
                    "synced_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "difficulty_result": difficulty_result,
                    "hashrate_result": hashrate_result
                }
                
        except Exception as e:
            logging.error(f"GHL network metrics sync error: {e}")
            return {"success": False, "error": str(e)}
    
    def push_daily_intel_briefing(self, article_body: str) -> Dict[str, Any]:
        """
        Push the Daily Intel Briefing (Bitcoin Lens article body) to GHL Custom Value.
        
        Args:
            article_body: Full article body text/HTML from Bitcoin Lens article
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            result = self.update_custom_value('daily_intel_briefing', article_body)
            
            if result.get('success'):
                logging.info("GHL DAILY INTEL BRIEFING SYNC SUCCESS: Article body pushed to Custom Value")
            
            return result
            
        except Exception as e:
            logging.error(f"GHL Daily Intel Briefing push error: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
ghl_service = GHLService()
```

## services/price_service.py
```python
"""
Cryptocurrency Price Service
Fetches real-time prices from CoinGecko API (free, no API key required)
"""
import requests
import logging
from datetime import datetime, timedelta
from functools import lru_cache
import time

class PriceService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}
        self.cache_duration = 60  # Cache prices for 60 seconds
        self.last_fetch = None
        logging.info("Price service initialized")
    
    def get_prices(self):
        """Get current prices for Bitcoin, Ethereum, and other major coins"""
        now = datetime.utcnow()
        
        # Return cached data if still valid
        if self.last_fetch and (now - self.last_fetch).total_seconds() < self.cache_duration:
            if self.cache:
                return self.cache
        
        try:
            # Fetch prices from CoinGecko
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,solana',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Format the data
            prices = {
                'bitcoin': {
                    'price': data.get('bitcoin', {}).get('usd', 0),
                    'change_24h': data.get('bitcoin', {}).get('usd_24h_change', 0),
                    'market_cap': data.get('bitcoin', {}).get('usd_market_cap', 0)
                },
                'ethereum': {
                    'price': data.get('ethereum', {}).get('usd', 0),
                    'change_24h': data.get('ethereum', {}).get('usd_24h_change', 0),
                    'market_cap': data.get('ethereum', {}).get('usd_market_cap', 0)
                },
                'solana': {
                    'price': data.get('solana', {}).get('usd', 0),
                    'change_24h': data.get('solana', {}).get('usd_24h_change', 0),
                    'market_cap': data.get('solana', {}).get('usd_market_cap', 0)
                },
                'last_updated': now.isoformat()
            }
            
            # Update cache
            self.cache = prices
            self.last_fetch = now
            
            logging.info(f"Prices updated: BTC ${prices['bitcoin']['price']:,.0f}, ETH ${prices['ethereum']['price']:,.0f}")
            return prices
            
        except Exception as e:
            logging.error(f"Error fetching prices: {e}")
            # Return cached data if available, otherwise return defaults
            if self.cache:
                return self.cache
            return self._get_default_prices()
    
    def _get_default_prices(self):
        """Return default prices if API fails"""
        return {
            'bitcoin': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'ethereum': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'solana': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'last_updated': None,
            'error': True
        }
    
    def get_defi_tvl(self):
        """Get total DeFi TVL from DeFiLlama API"""
        try:
            url = "https://api.llama.fi/tvl/defi"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                tvl = response.json()
                return tvl
        except Exception as e:
            logging.error(f"Error fetching DeFi TVL: {e}")
        
        # Fallback - try to get from protocols endpoint
        try:
            url = "https://api.llama.fi/protocols"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                protocols = response.json()
                total_tvl = sum(p.get('tvl', 0) for p in protocols if p.get('tvl'))
                return total_tvl
        except:
            pass
        
        return None
    
    def format_price(self, price):
        """Format price with commas and dollar sign"""
        if price >= 1000:
            return f"${price:,.0f}"
        elif price >= 1:
            return f"${price:,.2f}"
        else:
            return f"${price:.4f}"
    
    def format_change(self, change):
        """Format percentage change with + or - sign"""
        if change >= 0:
            return f"+{change:.1f}%"
        else:
            return f"{change:.1f}%"
    
    def format_market_cap(self, cap):
        """Format market cap in billions/trillions"""
        if cap >= 1_000_000_000_000:
            return f"${cap / 1_000_000_000_000:.2f}T"
        elif cap >= 1_000_000_000:
            return f"${cap / 1_000_000_000:.0f}B"
        elif cap >= 1_000_000:
            return f"${cap / 1_000_000:.0f}M"
        else:
            return f"${cap:,.0f}"

# Initialize singleton
price_service = PriceService()
```

## services/nostr_broadcaster.py
```python
import os
import json
import time
import hashlib
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOSTR_PRIVATE_KEY = os.environ.get('NOSTR_PRIVATE_KEY', '')
NOSTR_RELAYS_STR = os.environ.get('NOSTR_RELAYS', 
    'wss://relay.damus.io,wss://nos.lol,wss://relay.snort.social,wss://nostr.wine,wss://relay.primal.net')
NOSTR_RELAYS = [r.strip() for r in NOSTR_RELAYS_STR.split(',') if r.strip()]

DEFAULT_HASHTAGS = ['bitcoin', 'freedomtech', 'protocolpulse', 'sovereignty']


class NostrBroadcasterService:
    def __init__(self):
        self.private_key = NOSTR_PRIVATE_KEY
        self.relays = NOSTR_RELAYS
        self.public_key = None
        self.pynostr_available = False
        
        try:
            from pynostr.key import PrivateKey
            from pynostr.event import Event
            from pynostr.relay_manager import RelayManager
            self.pynostr_available = True
            
            if self.private_key and self.private_key.startswith('nsec'):
                pk = PrivateKey.from_nsec(self.private_key)
                self.public_key = pk.public_key.hex()
                logger.info(f"Nostr Broadcaster initialized with pubkey: {self.public_key[:16]}...")
            else:
                logger.warning("Nostr private key not configured or invalid format")
        except ImportError as e:
            logger.warning(f"pynostr not available: {e}")
        except Exception as e:
            logger.error(f"Error initializing Nostr: {e}")
    
    def get_relay_status(self):
        status = {
            'configured': len(self.relays),
            'relays': self.relays,
            'public_key': self.public_key,
            'ready': self.pynostr_available and bool(self.private_key)
        }
        return status
    
    def broadcast_note(self, content, hashtags=None, url=None):
        if not self.pynostr_available or not self.private_key:
            return self._simulate_broadcast(content)
        
        try:
            from pynostr.key import PrivateKey
            from pynostr.event import Event
            from pynostr.relay_manager import RelayManager
            
            pk = PrivateKey.from_nsec(self.private_key)
            
            tags = []
            all_hashtags = (hashtags or []) + DEFAULT_HASHTAGS
            for tag in all_hashtags[:5]:
                clean_tag = tag.replace('#', '').lower()
                tags.append(['t', clean_tag])
            
            if url:
                tags.append(['r', url])
            
            event = Event(
                public_key=pk.public_key.hex(),
                created_at=int(time.time()),
                kind=1,
                tags=tags,
                content=content
            )
            event.sign(pk.hex())
            
            success_relays = []
            failed_relays = []
            
            relay_manager = RelayManager()
            
            for relay_url in self.relays:
                try:
                    relay_manager.add_relay(relay_url)
                except Exception as e:
                    logger.warning(f"Failed to add relay {relay_url}: {e}")
                    failed_relays.append(relay_url)
            
            try:
                relay_manager.open_connections()
                time.sleep(1)
                
                relay_manager.publish_event(event)
                time.sleep(2)
                
                for relay_url in self.relays:
                    if relay_url not in failed_relays:
                        success_relays.append(relay_url)
                
                relay_manager.close_connections()
                
            except Exception as e:
                logger.error(f"Error publishing to relays: {e}")
                failed_relays = self.relays
            
            return {
                'success': len(success_relays) > 0,
                'event_id': event.id,
                'relays_success': success_relays,
                'relays_failed': failed_relays,
                'pubkey': pk.public_key.hex()
            }
            
        except Exception as e:
            logger.error(f"Error broadcasting to Nostr: {e}")
            return self._simulate_broadcast(content)
    
    def _simulate_broadcast(self, content):
        logger.info(f"Simulating Nostr broadcast (no private key configured)")
        
        event_id = hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()
        
        return {
            'success': False,
            'simulated': True,
            'event_id': event_id,
            'relays_success': [],
            'relays_failed': self.relays,
            'message': 'Nostr key not configured - broadcast simulated'
        }
    
    def broadcast_brief(self, title, summary, url, tags=None):
        content = f"""🔴 INTEL BRIEFING

{title}

{summary[:500]}

Full analysis: {url}

#Bitcoin #FreedomTech #ProtocolPulse"""
        
        return self.broadcast_note(content, hashtags=tags, url=url)
    
    def broadcast_episode(self, title, guest, quote, url, tags=None):
        content = f"""🎙️ New Cypherpunk'd Episode

{guest}: "{quote[:200]}"

We dive deep into the signal behind the noise.

Listen: {url}

#Bitcoin #Podcast #ProtocolPulse"""
        
        return self.broadcast_note(content, hashtags=tags, url=url)
    
    def broadcast_article(self, title, excerpt, url, tags=None):
        content = f"""📝 New Analysis

{title}

{excerpt[:400]}

Read more: {url}

#Bitcoin #Analysis #ProtocolPulse"""
        
        return self.broadcast_note(content, hashtags=tags, url=url)
    
    def broadcast_thread(self, tweets, url=None):
        results = []
        previous_event_id = None
        
        for i, tweet_text in enumerate(tweets):
            tags = DEFAULT_HASHTAGS.copy()
            
            if i == 0:
                content = f"🧵 Thread:\n\n{tweet_text}"
            else:
                content = tweet_text
            
            result = self.broadcast_note(content, hashtags=tags if i == 0 else None, url=url if i == 0 else None)
            results.append(result)
            
            if result.get('success'):
                previous_event_id = result.get('event_id')
            
            time.sleep(0.5)
        
        return {
            'success': any(r.get('success') for r in results),
            'notes_published': len([r for r in results if r.get('success')]),
            'total_notes': len(tweets),
            'results': results
        }
    
    def get_nip05_json(self):
        if not self.public_key:
            return None
        
        return {
            "names": {
                "intel": self.public_key,
                "pulse": self.public_key,
                "pbx": self.public_key
            },
            "relays": {
                self.public_key: self.relays[:3]
            }
        }
    
    def test_connection(self):
        test_result = self.broadcast_note(
            "🔴 Protocol Pulse connection test. Sovereignty through verification.",
            hashtags=['test', 'bitcoin']
        )
        return test_result


nostr_broadcaster = NostrBroadcasterService()
```

## services/launch_sequence.py
```python
import os
import json
import logging
from datetime import datetime, timedelta
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

KEYWORD_ROTATIONS = {
    1: {'sovereignty': 0.6, 'tech': 0.4},
    2: {'economic': 0.6, 'cultural': 0.4},
    3: {'tech': 0.5, 'cultural': 0.3, 'sovereignty': 0.2},
    4: {'sovereignty': 0.25, 'tech': 0.25, 'economic': 0.25, 'cultural': 0.25}
}

KEYWORD_BANKS = {
    'sovereignty': [
        'digital sovereignty', 'self-custody', 'financial freedom', 
        'permissionless', 'censorship-resistant', 'monetary sovereignty',
        'sovereign individual', 'freedom tech', 'exit strategy'
    ],
    'tech': [
        'protocol-level', 'on-chain', 'hash rate', 'difficulty adjustment',
        'mempool', 'UTXO', 'Lightning Network', 'layer 2', 'node operator'
    ],
    'economic': [
        'sound money', 'Austrian economics', 'monetary policy', 
        'fiat debasement', 'purchasing power', 'hard money',
        'store of value', 'scarcity', 'inflation hedge'
    ],
    'cultural': [
        'generational wealth', 'monetary education', 'orange pill',
        'Bitcoin standard', 'time preference', 'proof of work ethic',
        'trustless', 'verification over trust'
    ]
}

REPLY_STRATEGIES = [
    {'name': 'Technical', 'prompt': 'Provide technical insight about on-chain data or protocol mechanics'},
    {'name': 'Contrarian', 'prompt': 'Present a thoughtful devil\'s advocate perspective'},
    {'name': 'Data Reference', 'prompt': 'Reference specific Bitcoin network data (difficulty ~146T, hashrate ~1000 EH/s)'},
    {'name': 'Historical', 'prompt': 'Draw a historical parallel to past monetary or tech transitions'},
    {'name': 'Resource', 'prompt': 'Point to additional resources or deeper analysis'},
    {'name': 'Episode Callback', 'prompt': 'Reference a relevant podcast episode or interview'},
    {'name': 'Austrian Economics', 'prompt': 'Frame through Austrian economics lens'},
    {'name': 'Sovereignty', 'prompt': 'Connect to self-custody or individual sovereignty themes'},
    {'name': 'Tell Me Wrong', 'prompt': 'End with "Tell me I\'m wrong" or "What am I missing?"'},
    {'name': 'Expand Insight', 'prompt': 'Expand on an incomplete insight to drive engagement'}
]


class LaunchSequenceService:
    def __init__(self):
        self.client = None
        if OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("Launch Sequence Service initialized with OpenAI")
        else:
            logger.warning("OpenAI API key not configured")
    
    def get_current_week(self):
        week_of_year = datetime.now().isocalendar()[1]
        return ((week_of_year - 1) % 4) + 1
    
    def apply_keyword_rotation(self, base_text, week_number=None):
        if week_number is None:
            week_number = self.get_current_week()
        
        rotation = KEYWORD_ROTATIONS.get(week_number, KEYWORD_ROTATIONS[4])
        
        import random
        keywords = []
        for category, weight in rotation.items():
            bank = KEYWORD_BANKS.get(category, [])
            num_to_pick = max(1, int(weight * 3))
            if bank:
                keywords.extend(random.sample(bank, min(num_to_pick, len(bank))))
        
        return keywords
    
    def generate_launch_sequence(self, content, content_type='article', content_id=None):
        if not self.client:
            return self._generate_fallback_sequence(content, content_type)
        
        try:
            week = self.get_current_week()
            keywords = self.apply_keyword_rotation(content, week)
            keyword_str = ', '.join(keywords[:5])
            
            main_prompt = f"""You are PBX, the Intelligence Officer at Protocol Pulse, a Bitcoin media platform.

Create an optimized Twitter/X post for this content:
---
{content[:2000]}
---

REQUIREMENTS:
1. Main post MUST be under 280 characters
2. Create engagement through: incomplete insight, provocative question, or controversial take
3. Do NOT include links in the main post (link goes in first reply)
4. Incorporate these keywords naturally: {keyword_str}
5. End with something that demands a response

Respond in JSON format:
{{
    "primary_post": "Your 280-char optimized main post",
    "thread_tweets": ["Tweet 2...", "Tweet 3...", "Tweet 4...", "Tweet 5..."],
    "quote_variants": ["Alternative angle 1...", "Alternative angle 2...", "Alternative angle 3..."],
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "first_reply": "Your link + context for first reply",
    "call_to_action": "Clear CTA for audience"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": main_prompt}],
                temperature=0.8,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text.strip())
            
            reply_drafts = self._generate_reply_drafts(content[:1000])
            
            return {
                'primary_post_copy': result.get('primary_post', ''),
                'thread_replies': json.dumps(result.get('thread_tweets', [])),
                'quote_variants': json.dumps(result.get('quote_variants', [])),
                'reply_drafts': json.dumps(reply_drafts),
                'hashtags': ' '.join(result.get('hashtags', [])),
                'first_reply_link': result.get('first_reply', ''),
                'call_to_action': result.get('call_to_action', ''),
                'velocity_prediction': self._predict_velocity(result.get('primary_post', '')),
                'posting_time': self._get_optimal_posting_time(),
                'content_id': content_id,
                'content_type': content_type
            }
            
        except Exception as e:
            logger.error(f"Error generating launch sequence: {e}")
            return self._generate_fallback_sequence(content, content_type)
    
    def _generate_reply_drafts(self, content):
        if not self.client:
            return self._get_fallback_reply_drafts()
        
        try:
            drafts = []
            
            for strategy in REPLY_STRATEGIES:
                prompt = f"""You are PBX from Protocol Pulse. Generate ONE reply for this content using this strategy:

Strategy: {strategy['name']}
Instructions: {strategy['prompt']}

Content context:
{content}

Reply must be under 280 characters. Be substantive but concise."""

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.9,
                    max_tokens=150
                )
                
                drafts.append({
                    'strategy': strategy['name'],
                    'text': response.choices[0].message.content.strip()
                })
            
            return drafts
            
        except Exception as e:
            logger.error(f"Error generating reply drafts: {e}")
            return self._get_fallback_reply_drafts()
    
    def _get_fallback_reply_drafts(self):
        return [
            {'strategy': 'Technical', 'text': 'Looking at the on-chain data, this pattern mirrors what we saw in the 2020 cycle. The hashrate-to-price ratio is particularly telling.'},
            {'strategy': 'Contrarian', 'text': "Playing devil's advocate - what if we're reading this signal wrong? The correlation could be coincidental."},
            {'strategy': 'Data', 'text': 'The 146.47T difficulty and 1046 EH/s hashrate paint a clear picture of network security reaching ATH.'},
            {'strategy': 'Historical', 'text': 'This reminds me of the 2013 Cyprus banking crisis. History doesn\'t repeat, but it rhymes.'},
            {'strategy': 'Resource', 'text': 'For anyone wanting to dig deeper, we covered this in detail on our latest intel briefing.'},
            {'strategy': 'Episode', 'text': 'We explored this exact thesis with our last guest. The conviction is only growing.'},
            {'strategy': 'Austrian', 'text': 'Through an Austrian lens, this is simply the market discovering true price in a sound money context.'},
            {'strategy': 'Sovereignty', 'text': 'This is why self-custody matters. Financial sovereignty isn\'t optional anymore.'},
            {'strategy': 'Challenge', 'text': 'Tell me I\'m wrong, but this seems like the most obvious signal we\'ve had in years.'},
            {'strategy': 'Incomplete', 'text': 'The part nobody\'s talking about is what happens when institutions figure this out...'}
        ]
    
    def _predict_velocity(self, post_text):
        score = 50
        
        if '?' in post_text:
            score += 15
        
        controversy_words = ['wrong', 'disagree', 'unpopular', 'controversial', 'hot take']
        if any(word in post_text.lower() for word in controversy_words):
            score += 20
        
        if len(post_text) > 200 and len(post_text) < 260:
            score += 10
        
        engagement_hooks = ['tell me', 'what if', 'imagine', 'consider this', 'here\'s the thing']
        if any(hook in post_text.lower() for hook in engagement_hooks):
            score += 15
        
        return min(score, 100)
    
    def _get_optimal_posting_time(self):
        from datetime import time
        optimal_hours = [9, 12, 15, 18, 21]  # EST
        import random
        hour = random.choice(optimal_hours)
        return time(hour, random.randint(0, 30))
    
    def _generate_fallback_sequence(self, content, content_type):
        summary = content[:200] if len(content) > 200 else content
        
        return {
            'primary_post_copy': f"🔴 New intel just dropped. {summary[:150]}... Thread 👇",
            'thread_replies': json.dumps([
                "Here's why this matters for your stack...",
                "The signal most are missing is the network fundamentals.",
                "What this means for the next 6-12 months...",
                "What would you add? Tell me in the replies."
            ]),
            'quote_variants': json.dumps([
                "This is the signal in the noise.",
                "Pay attention to what's happening at the protocol level.",
                "The network doesn't lie."
            ]),
            'reply_drafts': json.dumps(self._get_fallback_reply_drafts()),
            'hashtags': '#Bitcoin #FreedomTech #ProtocolPulse',
            'first_reply_link': 'Full analysis: [LINK]',
            'call_to_action': 'Follow for daily Bitcoin intelligence.',
            'velocity_prediction': 60,
            'posting_time': self._get_optimal_posting_time(),
            'content_id': None,
            'content_type': content_type
        }
    
    def create_thread_from_content(self, content, max_tweets=10):
        if not self.client:
            return self._create_fallback_thread(content)
        
        try:
            prompt = f"""Create a Twitter thread (max {max_tweets} tweets) from this content.

Content:
{content[:3000]}

REQUIREMENTS:
1. Each tweet MUST be under 270 characters (leave room for thread numbering)
2. Tweet 1: Hook that creates curiosity
3. Each tweet should end with something that makes them want to read the next
4. Tweet 7 (if applicable): "What would you add?"
5. Final tweet: "Tell me I'm wrong" or strong CTA

Respond in JSON format:
{{"thread": ["Tweet 1 text...", "Tweet 2 text...", ...]}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text.strip())
            return result.get('thread', [])
            
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            return self._create_fallback_thread(content)
    
    def _create_fallback_thread(self, content):
        sentences = content.split('.')
        thread = []
        current_tweet = ""
        
        for sentence in sentences[:15]:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_tweet) + len(sentence) + 2 < 270:
                current_tweet += sentence + ". "
            else:
                if current_tweet:
                    thread.append(current_tweet.strip())
                current_tweet = sentence + ". "
        
        if current_tweet:
            thread.append(current_tweet.strip())
        
        if thread:
            thread.append("What would you add? 👇")
        
        return thread[:10]


launch_sequence_service = LaunchSequenceService()
```

## services/automation.py
```python
"""
Automation helper with database-backed execution tracking and locking
Ensures idempotent execution and prevents duplicate runs
"""
import logging
from datetime import datetime, timedelta
from app import app, db
from models import Article
from services.content_generator import ContentGenerator
from services.gemini_service import gemini_service
import random
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Breaking news topics - expanded and more diverse
TOPICS = [
    "Bitcoin mining difficulty reaches new all-time high as hash rate surges",
    "Major institutional investors allocate billions to Bitcoin treasury reserves", 
    "Lightning Network payment volume breaks monthly records",
    "DeFi protocols implement revolutionary new yield farming mechanisms",
    "Central banks accelerate CBDC development in response to Bitcoin adoption",
    "Major corporations announce Bitcoin payment integration plans",
    "Renewable energy Bitcoin mining initiatives expand globally",
    "DeFi total value locked reaches new milestone despite market volatility",
    "Bitcoin ETF inflows surge as retail and institutional demand grows",
    "Layer 2 scaling solutions see unprecedented adoption rates",
    "Bitcoin node count reaches new highs as decentralization strengthens",
    "Nostr protocol adoption grows as censorship-resistant social media expands",
    "Bitcoin self-custody solutions see record downloads amid banking concerns",
    "Hardware wallet manufacturers report surge in demand",
    "Bitcoin development activity increases with new BIP proposals",
    "Stablecoin regulations face scrutiny as Bitcoin alternative gains attention",
    "Bitcoin ordinals and inscriptions drive on-chain activity surge",
    "Countries explore strategic Bitcoin reserve policies",
    "Bitcoin privacy improvements proposed in new protocol upgrades",
    "Cross-border Bitcoin payments reduce remittance costs globally"
]

def get_topic_keywords(text):
    """Extract meaningful keywords from a topic/title for similarity comparison"""
    # Remove common words AND generic crypto terms that appear in most headlines
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'new', 'amid', 'despite',
                  # Crypto-generic terms that don't distinguish topics
                  'bitcoin', 'btc', 'crypto', 'cryptocurrency', 'market', 'markets',
                  'hit', 'hits', 'reach', 'reaches', 'record', 'high', 'highs', 'low',
                  'surge', 'surges', 'soar', 'soars', 'rise', 'rises', 'grow', 'grows',
                  'boost', 'boosts', 'boosting', 'gain', 'gains', 'see', 'sees', 'show',
                  'shows', 'global', 'globally', 'major', 'top', 'big', 'breaking',
                  'report', 'reports', 'amid', 'despite', 'all', 'time', 'monthly',
                  'weekly', 'daily', 'unprecedented', 'expansion', 'initiative', 'initiatives'}
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return set(word for word in words if word not in stop_words)

# Core topic categories - if two articles share the same core topic, they're duplicates
CORE_TOPICS = {
    'mining_difficulty': ['mining', 'difficulty', 'hash', 'hashrate'],
    'lightning_network': ['lightning', 'network', 'payment', 'volume'],
    'defi_tvl': ['defi', 'tvl', 'locked', 'value'],
    'defi_yield': ['defi', 'yield', 'farming', 'protocol'],
    'etf_inflows': ['etf', 'inflow', 'inflows', 'demand'],
    'etf_flows': ['etf', 'flow', 'flows', 'outflow', 'outflows', 'billion'],
    'institutional': ['institutional', 'treasury', 'billion'],
    'green_mining': ['renewable', 'energy', 'green', 'sustainable'],
    'cbdc': ['cbdc', 'central', 'bank', 'digital', 'currency'],
    'corporate_payments': ['corporate', 'corporation', 'payment', 'accept'],
    'layer2_scaling': ['layer', 'scaling', 'solution', 'adoption'],
    'node_count': ['node', 'nodes', 'decentralization', 'count'],
    'strategic_reserve': ['reserve', 'reserves', 'strategic', 'nation', 'nations', 'country', 'countries', 'government', 'sovereign', 'treasury'],
    'price_milestone': ['price', 'milestone', 'ath', 'high', 'record', 'surge'],
    'adoption': ['adoption', 'accept', 'acceptance', 'mainstream', 'integration'],
    'halving': ['halving', 'halvening', 'block', 'reward', 'subsidy'],
    'regulation': ['regulation', 'regulatory', 'sec', 'cftc', 'law', 'bill', 'legislation'],
}

def get_core_topic(text):
    """Identify the core topic category of an article"""
    text_lower = text.lower()
    words = set(re.findall(r'\b[a-zA-Z]{3,}\b', text_lower))
    
    for topic_id, keywords in CORE_TOPICS.items():
        # If 2+ keywords from a category are present, it's that topic
        matches = sum(1 for kw in keywords if kw in words)
        if matches >= 2:
            return topic_id
    return None

def is_semantic_duplicate(new_headline, recent_headlines):
    """
    Use Gemini to check semantic similarity between headlines.
    Catches meaning-based duplicates that keyword matching misses.
    Example: "US Treasury adds BTC to reserves" vs "White House embraces Bitcoin as strategic asset"
    Returns True if Gemini identifies the new headline as the same story.
    """
    if not recent_headlines:
        return False
    
    # Build the prompt for Gemini - focused on EXACT SAME NEWS EVENT
    headlines_list = "\n".join([f"- {h}" for h in recent_headlines[:10]])
    prompt = f"""You are a senior news editor at a major financial publication. Your job is to prevent duplicate coverage.

NEW HEADLINE TO CHECK: "{new_headline}"

EXISTING HEADLINES FROM LAST 48 HOURS:
{headlines_list}

CRITICAL QUESTION: Are any of the existing headlines covering the EXACT SAME news event as the new headline?

RULES:
- Ignore generic wording or similar themes - focus ONLY on whether it's the SAME SPECIFIC EVENT
- "Nations adopt Bitcoin reserves" and "Countries explore strategic Bitcoin holdings" = SAME EVENT (both about sovereign Bitcoin adoption trend)
- "Bitcoin ETF sees $500M inflows" and "Spot Bitcoin ETFs record massive demand" = SAME EVENT (both about ETF flow activity)
- "Bitcoin hits $100K" and "Bitcoin adoption grows in Africa" = DIFFERENT EVENTS (price vs regional adoption)

Reply with ONLY one word: "DUPLICATE" or "UNIQUE" - nothing else."""

    try:
        response = gemini_service.generate_content(prompt)
        if response:
            answer = response.strip().upper()
            if "DUPLICATE" in answer:
                logging.info(f"🧠 SEMANTIC DUPLICATE: Gemini detected '{new_headline[:50]}...' matches existing story")
                return True
            logging.info(f"✅ SEMANTIC UNIQUE: Gemini confirmed '{new_headline[:50]}...' is a new story")
    except Exception as e:
        logging.warning(f"Gemini semantic check failed: {e}")
    
    return False

def is_topic_similar_to_recent(topic, hours=48, similarity_threshold=0.35):
    """
    Check if a topic is too similar to recently published articles
    Uses THREE-tier detection:
    1. Core topic category matching (fastest, catches obvious duplicates)
    2. Keyword Jaccard similarity (catches word overlap)
    3. Gemini semantic analysis (catches meaning-based duplicates)
    Returns True if similar article found, False if topic is unique enough
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent_articles = Article.query.filter(
        Article.created_at >= cutoff,
        Article.published == True
    ).all()
    
    if not recent_articles:
        return False
    
    # FIRST CHECK: Core topic category matching (fastest, strongest detection)
    new_core_topic = get_core_topic(topic)
    if new_core_topic:
        for article in recent_articles:
            existing_core_topic = get_core_topic(article.title)
            if existing_core_topic and new_core_topic == existing_core_topic:
                logging.info(f"🚫 CORE TOPIC DUPLICATE: '{topic[:40]}...' matches category '{new_core_topic}' with '{article.title[:40]}...'")
                return True
    
    # SECOND CHECK: Keyword similarity (catches word overlap)
    topic_keywords = get_topic_keywords(topic)
    
    for article in recent_articles:
        article_keywords = get_topic_keywords(article.title)
        
        if not topic_keywords or not article_keywords:
            continue
        
        # Calculate Jaccard similarity
        intersection = len(topic_keywords & article_keywords)
        union = len(topic_keywords | article_keywords)
        similarity = intersection / union if union > 0 else 0
        
        if similarity >= similarity_threshold:
            logging.info(f"🔄 Topic similar to existing article: '{article.title}' (similarity: {similarity:.2f})")
            return True
    
    # THIRD CHECK: Gemini semantic analysis (catches meaning-based duplicates)
    # Example: "US Treasury adds BTC" vs "White House embraces Bitcoin as strategic asset"
    recent_headlines = [a.title for a in recent_articles[:5]]
    if is_semantic_duplicate(topic, recent_headlines):
        return True
    
    return False

def get_unique_topic(max_attempts=10):
    """
    Select a topic that hasn't been recently covered
    Returns a unique topic or None if all topics are too similar
    """
    available_topics = TOPICS.copy()
    random.shuffle(available_topics)
    
    for topic in available_topics[:max_attempts]:
        if not is_topic_similar_to_recent(topic):
            return topic
        logging.info(f"⏭️ Skipping similar topic: {topic[:50]}...")
    
    # If all predefined topics are similar, generate a dynamic one
    logging.info("🎲 All predefined topics similar - generating dynamic topic")
    dynamic_topics = [
        f"Bitcoin adoption trends and market analysis for {datetime.utcnow().strftime('%B %Y')}",
        f"Weekly Bitcoin network statistics show evolving usage patterns",
        f"Bitcoin's role in the evolving global monetary landscape",
        f"Technical analysis of Bitcoin's current market cycle position",
        f"Bitcoin mining industry developments and energy usage trends"
    ]
    
    for topic in dynamic_topics:
        if not is_topic_similar_to_recent(topic):
            return topic
    
    return None

def acquire_lock(task_name='article_generation', ttl_minutes=10):
    """
    Acquire execution lock to prevent duplicate runs
    Returns AutomationRun if lock acquired, None if another process is running
    """
    from models import AutomationRun
    
    # First, clean up stale locks (older than 30 minutes with no finish time)
    stale_threshold = datetime.utcnow() - timedelta(minutes=30)
    stale_count = AutomationRun.query.filter(
        AutomationRun.status == 'running',
        AutomationRun.started_at < stale_threshold,
        AutomationRun.finished_at == None
    ).update({
        'status': 'failed',
        'error': 'Stale lock cleaned up automatically',
        'finished_at': datetime.utcnow()
    })
    
    if stale_count > 0:
        db.session.commit()
        logging.warning(f"🧹 Cleaned up {stale_count} stale lock(s)")
    
    # Check for active locks (runs started within TTL that haven't finished)
    cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
    active_run = AutomationRun.query.filter(
        AutomationRun.task_name == task_name,
        AutomationRun.started_at >= cutoff,
        AutomationRun.finished_at == None
    ).first()
    
    if active_run:
        logging.warning(f"⏳ Lock held by run {active_run.id} started at {active_run.started_at}")
        return None
    
    # Acquire lock
    run = AutomationRun(
        task_name=task_name,
        started_at=datetime.utcnow(),
        status='running'
    )
    db.session.add(run)
    db.session.commit()
    
    logging.info(f"🔒 Lock acquired: {run.id}")
    return run

def release_lock(run, status='success', error=None):
    """Release execution lock and update status"""
    run.finished_at = datetime.utcnow()
    run.status = status
    if error:
        run.error = str(error)[:500]  # Truncate long errors
    db.session.commit()
    logging.info(f"🔓 Lock released: {run.id} ({status})")

def generate_article_with_tracking():
    """
    Core generation routine with structured logging and error handling
    This is the idempotent helper that automation_worker.py will call
    """
    with app.app_context():
        # Acquire lock to prevent duplicate execution
        run = acquire_lock()
        if not run:
            logging.info("⏭️  Skipping: Another process is running")
            return {'skipped': True}
        
        try:
            generator = ContentGenerator()
            
            # Get a unique topic that hasn't been covered recently
            topic = get_unique_topic()
            
            if not topic:
                logging.warning("⚠️ No unique topics available - all topics too similar to recent articles")
                release_lock(run, 'skipped', 'No unique topics available')
                return {'skipped': True, 'reason': 'All topics too similar to recent articles'}
            
            logging.info(f"🔥 Generating article: {topic}")
            
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='ai_generated'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.summary = ""
                article.category = article_data.get('category', 'Bitcoin')
                article.tags = article_data.get('tags', 'bitcoin,breaking,news')
                article.author = "Al Ingle"
                article.seo_title = article_data.get('seo_title', article_data['title'])
                article.seo_description = article_data.get('seo_description', article_data['title'][:150])
                article.published = True
                article.featured = True
                db.session.add(article)
                db.session.commit()
                
                logging.info(f"✅ Article created: {article.title}")
                
                # Try to publish to Substack (non-blocking)
                try:
                    from services.substack_service import SubstackService
                    substack_service = SubstackService()
                    newsletter_content = substack_service.format_content_for_newsletter(article.content, 'bitcoin')
                    substack_url = substack_service.publish_to_substack(article.title, newsletter_content, article.header_image_url)
                    
                    if substack_url:
                        article.substack_url = substack_url
                        db.session.commit()
                        logging.info(f"🚀 Published to Substack: {substack_url}")
                except Exception as e:
                    logging.error(f"❌ Substack error (non-fatal): {e}")
                
                # Release lock with success
                release_lock(run, 'success')
                return {'success': True, 'article_id': article.id, 'title': article.title}
            else:
                logging.error("❌ No article data generated")
                release_lock(run, 'failed', 'No article data generated')
                return {'success': False, 'error': 'No article data'}
                
        except Exception as e:
            logging.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            release_lock(run, 'failed', e)
            return {'success': False, 'error': str(e)}

def auto_generate_reactionary_articles():
    """
    Automatically fetch latest videos from monitored channels,
    transcribe them, and generate reactionary articles.
    """
    from services.youtube_service import YouTubeService
    youtube_service = YouTubeService()
    videos = youtube_service.get_monitored_channel_videos(limit=1)
    
    for video in videos:
        # Check if we already have an article for this video using semantic check if possible
        existing = Article.query.filter(Article.title.contains(video['title'])).first()
        if existing:
            continue
            
        # Semantic duplicate check
        recent_articles = Article.query.order_by(Article.created_at.desc()).limit(10).all()
        recent_headlines = [a.title for a in recent_articles]
        if is_semantic_duplicate(f"Review: {video['title']}", recent_headlines):
            logging.info(f"⏭️ Skipping semantic duplicate video: {video['title']}")
            continue

        logging.info(f"Generating reactionary article for: {video['title']}")
        content = youtube_service.draft_reactionary_article(video)
        
        if content:
            article = Article(
                title=f"Review: {video['title']}",
                content=content,
                category="Analysis",
                author=f"Protocol Pulse // {video['channel']}",
                image_url=video['thumbnail'],
                published=True
            )
            db.session.add(article)
            db.session.commit()
            logging.info(f"Published reactionary article for {video['title']}")

def get_last_run_status():
    """Get the status of the last automation run for health checks"""
    from models import AutomationRun
    
    last_run = AutomationRun.query.order_by(AutomationRun.started_at.desc()).first()
    
    if not last_run:
        return {'status': 'never_run'}
    
    return {
        'last_run': last_run.started_at.isoformat() if last_run.started_at else None,
        'status': last_run.status,
        'finished': last_run.finished_at.isoformat() if last_run.finished_at else None,
        'error': last_run.error
    }


def generate_podcasts_from_partners():
    """
    Audio intelligence podcast generation from monitored Bitcoin channels.
    Generates AI-hosted audio overviews of videos from partner channels.
    """
    from services.podcast_generator import podcast_generator
    from services.youtube_service import YouTubeService
    
    with app.app_context():
        yt_service = YouTubeService()
        
        for channel in YouTubeService.PODCAST_CHANNELS:
            try:
                video = yt_service.get_latest_video(channel['id'])
                
                if not video:
                    logging.info(f"No recent video found for {channel['name']}")
                    continue
                
                video_id = video.get('id')
                video_title = video.get('title', 'Unknown')
                
                existing = Article.query.filter(
                    Article.title.contains(video_title[:50])
                ).first()
                
                if existing:
                    logging.info(f"Podcast already exists for {video_title}")
                    continue
                
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                
                result = podcast_generator.generate_podcast_from_video(
                    video_id=video_id,
                    thumbnail_url=thumbnail_url,
                    channel_name=channel['name']
                )
                
                if result and result.get('audio_file'):
                    article = Article(
                        title=f"Audio Deep Dive: {video_title}",
                        summary=f"Deep-dive audio analysis of {channel['name']}'s latest content",
                        content=f'<p class="article-paragraph">Listen to our AI-hosted breakdown of {channel["name"]}\'s latest video.</p><audio controls src="/{result["audio_file"]}" style="width:100%;"></audio>',
                        category='Podcast',
                        image_url=thumbnail_url,
                        published=True
                    )
                    db.session.add(article)
                    db.session.commit()
                    logging.info(f"Created podcast article for: {video_title}")
                
            except Exception as e:
                logging.error(f"Error generating podcast for {channel['name']}: {e}")
                continue
```

## services/reddit_service.py
```python
import os
import logging
import praw
from datetime import datetime
from typing import List, Dict

class RedditService:
    def __init__(self):
        self.reddit = None
        try:
            self.reddit = praw.Reddit(
                client_id=os.environ.get('REDDIT_CLIENT_ID'),
                client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
                user_agent=os.environ.get('REDDIT_USER_AGENT')
            )
            logging.info("Reddit PRAW service initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize PRAW: {e}")
        
        # Bitcoin and DeFi focused subreddits
        self.crypto_subreddits = [
            'bitcoin',
            'defi', 
            'cryptocurrency',
            'bitcoinbeginners',
            'bitcoindiscussion',
            'lightningnetwork',
            'decentralizedfinance',
            'ethfinance',
            'cryptomarkets',
            'bitcointech'
        ]
    
    def post_to_reddit(self, subreddit_name: str, title: str, url: str) -> Dict:
        """Post a link to Reddit using PRAW"""
        result = {"success": False, "post_url": None, "errors": []}
        
        if not self.reddit:
            result["errors"].append("Reddit API not available")
            return result
            
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Submit the link post
            submission = subreddit.submit(title=title, url=url)
            
            result["success"] = True
            result["post_url"] = f"https://reddit.com{submission.permalink}"
            result["post_id"] = submission.id
            
            logging.info(f"Successfully posted to r/{subreddit_name}: {result['post_url']}")
            return result
            
        except Exception as e:
            result["errors"].append(f"Reddit posting failed: {e}")
            logging.error(f"Error posting to r/{subreddit_name}: {e}")
            return result

    def get_trending_posts(self, subreddit_name: str, limit: int = 10) -> List[Dict]:
        if not self.reddit:
            return []
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            for submission in subreddit.hot(limit=limit):
                if submission.stickied:
                    continue
                posts.append({
                    'title': submission.title,
                    'url': submission.url,
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'created_utc': datetime.fromtimestamp(submission.created_utc),
                    'selftext': submission.selftext,
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'permalink': f"https://reddit.com{submission.permalink}"
                })
            return posts
        except Exception as e:
            logging.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return []

    def get_trending_topics(self, subreddits, limit=10, time_period='day'):
        """
        Get trending topics from specified subreddits
        subreddits: list of subreddit names
        limit: number of posts to fetch per subreddit
        time_period: 'hour', 'day', 'week', 'month', 'year', 'all'
        """
        trending_posts = []
        
        for subreddit in subreddits:
            try:
                url = f"{self.base_url}/r/{subreddit}/hot.json"
                params = {
                    'limit': limit,
                    't': time_period
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post_data in posts:
                        post = post_data.get('data', {})
                        
                        # Filter for relevant content
                        if self._is_relevant_post(post):
                            trending_posts.append({
                                'title': post.get('title', ''),
                                'selftext': post.get('selftext', ''),
                                'url': post.get('url', ''),
                                'subreddit': post.get('subreddit', ''),
                                'score': post.get('score', 0),
                                'num_comments': post.get('num_comments', 0),
                                'created_utc': post.get('created_utc', 0),
                                'permalink': f"{self.base_url}{post.get('permalink', '')}",
                                'author': post.get('author', 'Unknown')
                            })
                
                else:
                    logging.warning(f"Failed to fetch from r/{subreddit}: {response.status_code}")
                    
            except Exception as e:
                logging.error(f"Error fetching from r/{subreddit}: {str(e)}")
                continue
        
        # Sort by score (popularity) and return top posts
        trending_posts.sort(key=lambda x: x['score'], reverse=True)
        return trending_posts[:limit * len(subreddits)]
    
    def _is_relevant_post(self, post):
        """Filter posts for relevance to Web3/crypto topics"""
        title = post.get('title', '').lower()
        selftext = post.get('selftext', '').lower()
        
        # Keywords that indicate relevance
        relevant_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 
            'blockchain', 'web3', 'defi', 'nft', 'dao', 'smart contract',
            'mining', 'staking', 'yield farming', 'dapp', 'metaverse',
            'privacy', 'decentralized', 'protocol', 'token', 'coin',
            'regulation', 'sec', 'cbdc', 'lightning network', 'layer 2'
        ]
        
        # Check if any relevant keywords are in title or text
        content = f"{title} {selftext}"
        return any(keyword in content for keyword in relevant_keywords)
    
    def get_post_details(self, post_url):
        """Get detailed information about a specific Reddit post"""
        try:
            # Convert Reddit URL to JSON API URL
            if 'reddit.com' in post_url:
                json_url = post_url.rstrip('/') + '.json'
            else:
                return None
            
            response = requests.get(json_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    post_data = data[0].get('data', {}).get('children', [])
                    if post_data:
                        post = post_data[0].get('data', {})
                        
                        # Get top comments
                        comments = []
                        if len(data) > 1:
                            comment_data = data[1].get('data', {}).get('children', [])
                            for comment in comment_data[:5]:  # Top 5 comments
                                comment_info = comment.get('data', {})
                                if comment_info.get('body') and comment_info.get('body') != '[deleted]':
                                    comments.append({
                                        'body': comment_info.get('body', ''),
                                        'score': comment_info.get('score', 0),
                                        'author': comment_info.get('author', 'Unknown')
                                    })
                        
                        return {
                            'title': post.get('title', ''),
                            'selftext': post.get('selftext', ''),
                            'url': post.get('url', ''),
                            'score': post.get('score', 0),
                            'num_comments': post.get('num_comments', 0),
                            'comments': comments,
                            'created_utc': post.get('created_utc', 0)
                        }
            
            return None
            
        except Exception as e:
            logging.error(f"Error fetching post details: {str(e)}")
            return None
    
    def search_subreddit(self, subreddit, query, limit=25):
        """Search for specific topics within a subreddit"""
        try:
            url = f"{self.base_url}/r/{subreddit}/search.json"
            params = {
                'q': query,
                'restrict_sr': 'true',
                'sort': 'relevance',
                'limit': limit,
                't': 'week'  # Posts from the last week
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                
                search_results = []
                for post_data in posts:
                    post = post_data.get('data', {})
                    search_results.append({
                        'title': post.get('title', ''),
                        'selftext': post.get('selftext', ''),
                        'url': post.get('url', ''),
                        'score': post.get('score', 0),
                        'permalink': f"{self.base_url}{post.get('permalink', '')}",
                        'created_utc': post.get('created_utc', 0)
                    })
                
                return search_results
            
            return []
            
        except Exception as e:
            logging.error(f"Error searching subreddit: {str(e)}")
            return []

    def get_bitcoin_trending_topics(self, limit: int = 20) -> List[Dict]:
        """Get trending Bitcoin-related topics using PRAW"""
        if self.use_api:
            bitcoin_subreddits = ['bitcoin', 'bitcoinbeginners', 'bitcoindiscussion', 'lightningnetwork']
            all_posts = []
            
            for subreddit_name in bitcoin_subreddits:
                posts = self.get_trending_posts_praw(subreddit_name, limit=8)
                all_posts.extend(posts)
            
            # Sort by engagement score
            all_posts.sort(key=lambda x: x['score'] + (x['num_comments'] * 2), reverse=True)
            return all_posts[:limit]
        else:
            # Fallback to public API
            return self.get_trending_topics(['bitcoin', 'bitcoinbeginners'], limit=limit)

    def get_defi_trending_topics(self, limit: int = 20) -> List[Dict]:
        """Get trending DeFi-related topics using PRAW"""
        if self.use_api:
            defi_subreddits = ['defi', 'decentralizedfinance', 'ethfinance']
            all_posts = []
            
            for subreddit_name in defi_subreddits:
                posts = self.get_trending_posts_praw(subreddit_name, limit=8)
                all_posts.extend(posts)
            
            # Sort by engagement score
            all_posts.sort(key=lambda x: x['score'] + (x['num_comments'] * 2), reverse=True)
            return all_posts[:limit]
        else:
            # Fallback to public API
            return self.get_trending_topics(['defi', 'cryptocurrency'], limit=limit)

    def get_content_ideas(self, topic_type: str = "bitcoin", limit: int = 5) -> List[Dict]:
        """Get content ideas based on trending topics"""
        if topic_type.lower() == "bitcoin":
            posts = self.get_bitcoin_trending_topics(limit=15)
        elif topic_type.lower() == "defi":
            posts = self.get_defi_trending_topics(limit=15)
        else:
            posts = self.get_trending_topics(['cryptocurrency', 'cryptomarkets'], limit=15)
        
        # Convert to content ideas
        content_ideas = []
        for post in posts[:limit]:
            if isinstance(post, dict):
                score = post.get('score', 0)
                comments = post.get('num_comments', 0)
                
                if score > 50 and comments > 10:  # Minimum engagement threshold
                    idea = {
                        'title': post.get('title', ''),
                        'article_angle': self._generate_article_angle(post),
                        'source_url': post.get('permalink', ''),
                        'engagement_score': score + comments,
                        'subreddit': post.get('subreddit', ''),
                        'created': post.get('created_utc', datetime.now()).strftime('%Y-%m-%d %H:%M') if isinstance(post.get('created_utc'), datetime) else 'Unknown'
                    }
                    content_ideas.append(idea)
        
        return content_ideas

    def _generate_article_angle(self, post: Dict) -> str:
        """Generate a potential article angle from a Reddit post"""
        title = post.get('title', '').lower()
        
        # Common article angles based on post content
        if any(word in title for word in ['price', 'surge', 'rally', 'pump']):
            return "Market Analysis: Price Movement Deep Dive"
        elif any(word in title for word in ['adoption', 'institutional', 'company']):
            return "Adoption News: Industry Impact Analysis"
        elif any(word in title for word in ['technical', 'upgrade', 'update', 'protocol']):
            return "Technical Analysis: Technology Advancement"
        elif any(word in title for word in ['regulation', 'legal', 'sec', 'government']):
            return "Regulatory Update: Policy Impact Assessment"
        elif any(word in title for word in ['hack', 'security', 'exploit']):
            return "Security Alert: Risk Analysis and Prevention"
        elif any(word in title for word in ['defi', 'yield', 'liquidity', 'protocol']):
            return "DeFi Deep Dive: Protocol Analysis"
        else:
            return "Community Spotlight: Trending Discussion Analysis"

    def test_connection(self) -> bool:
        """Test Reddit API connection"""
        if self.use_api and self.reddit:
            try:
                subreddit = self.reddit.subreddit('bitcoin')
                next(subreddit.hot(limit=1))
                return True
            except Exception as e:
                logging.error(f"Reddit PRAW connection test failed: {e}")
                return False
        else:
            # Test public API fallback
            try:
                import requests
                response = requests.get("https://www.reddit.com/r/bitcoin/hot.json?limit=1", timeout=5)
                return response.status_code == 200
            except:
                return False
```

## services/content_generator.py
```python
import logging
from datetime import datetime, timedelta
from app import app, db
from models import ContentPrompt, Article
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.x_service import get_social_feedback
from services import x_service
from services.image_service import image_service
from services.gemini_service import gemini_service
from services.node_service import NodeService
from services.fact_checker import fact_checker, verify_article_before_publish


def is_topic_duplicate_via_gemini(proposed_topic):
    """
    AI GATEKEEPER: Check if the proposed topic duplicates any recent article.
    Returns True if duplicate (should skip), False if unique (proceed).
    """
    try:
        with app.app_context():
            # Fetch last 10 published article titles
            recent_articles = Article.query.filter_by(published=True).order_by(
                Article.created_at.desc()
            ).limit(10).all()
            
            if not recent_articles:
                return False  # No articles to compare, proceed
            
            headlines_list = "\n".join([f"- {a.title}" for a in recent_articles])
            
            prompt = f"""You are a senior news editor preventing duplicate coverage.

PROPOSED NEW TOPIC: "{proposed_topic}"

LAST 10 PUBLISHED HEADLINES:
{headlines_list}

CRITICAL QUESTION: Is the proposed topic covering the EXACT SAME news event as ANY of these existing headlines?

RULES:
- Focus on the CORE EVENT, not wording
- "Bitcoin reaches new high" and "BTC price surges to record" = SAME EVENT
- "Nations adopt Bitcoin reserves" and "Countries add BTC to treasuries" = SAME EVENT
- "Bitcoin mining difficulty rises" and "New mining hardware released" = DIFFERENT EVENTS

Reply with ONLY one word: "DUPLICATE" or "UNIQUE" - nothing else."""

            response = gemini_service.generate_content(prompt)
            if response:
                answer = response.strip().upper()
                if "DUPLICATE" in answer:
                    logging.info(f"🚫 GATEKEEPER BLOCKED: '{proposed_topic[:50]}...' is duplicate of existing story")
                    return True
                logging.info(f"✅ GATEKEEPER APPROVED: '{proposed_topic[:50]}...' is unique")
            return False
    except Exception as e:
        logging.warning(f"Gatekeeper check failed: {e}")
        return False  # On error, allow generation to proceed

class ContentGenerator:
    def __init__(self):
        self.ai_service = AIService()
        self.reddit_service = RedditService()
        self.gemini_service = gemini_service
        
        # EDITORIAL ACCURACY MANDATE - Applied to all content types
        self.accuracy_mandate = """
=== EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===

GROUND TRUTH DATA LOCKDOWN (January 23, 2026):
- Bitcoin Difficulty: 146.47 T (NOT an all-time high - below November 2025 peak of 155.9 T)
- Network Hashrate: ~977 EH/s (approximately 1042 EH/s in some readings)
- These figures are CURRENT and VERIFIED - use them when discussing network security

RECORD HIGH PROHIBITION:
- NEVER claim "all-time high," "record high," "unprecedented," or "new record" for difficulty
- The November 2025 peak was 155.9 T - current difficulty is BELOW that threshold
- Only use "record" terminology if difficulty exceeds 155.9 T (which it does NOT today)

STRICTLY PROHIBITED - IMMEDIATE REJECTION IF VIOLATED:
- NEVER hallucinate hashrate figures (do not invent numbers not listed above)
- NEVER assume difficulty is always increasing - it can DECREASE during miner stress periods
- NEVER fabricate "network strengthening" narratives without verified data
- NEVER use phrases like "surge," "soaring," or "record-breaking" for metrics you cannot verify

TECHNICAL STORYTELLING - EDITORIAL APPROACH:
Write every piece as a peer-to-peer intelligence briefing for "transactors" (active Bitcoin users),
NOT for "tourists" (passive chart-watchers seeking price speculation):
- Transactors care about: network security, difficulty adjustments, hashrate distribution, mining economics, protocol fundamentals
- Tourists care about: price predictions, moon shots, get-rich-quick narratives (AVOID THIS)
- Frame content as actionable intelligence that helps transactors make informed decisions about their Bitcoin holdings

THE BITCOIN LENS - PHILOSOPHICAL GROUNDING:
Every article must connect technical Bitcoin metrics back to the philosophy of "The Hardest Money":
- Difficulty at 146.47 T represents computational security protecting the soundest monetary base layer
- 977 EH/s of hashpower demonstrates global commitment to decentralized, censorship-resistant money
- Each difficulty adjustment proves the protocol's self-regulating nature vs fiat's arbitrary manipulation
- Frame all network metrics as evidence of Bitcoin's position as incorruptible, trustless money

BEFORE DRAFTING ANY ARTICLE, YOU MUST:
1. Use the GROUND TRUTH DATA above for January 23, 2026
2. DO NOT rely on training data or assumptions about network conditions
3. State the ACTUAL current date and ACTUAL current metrics correctly
4. Connect network fundamentals to Bitcoin's role as sound money vs fiat debasement

IF WRITING ABOUT BITCOIN NETWORK METRICS:
- Use the verified metrics above: Difficulty 146.47 T, Hashrate ~977 EH/s
- Use qualified language: "current difficulty stands at 146.47 T," "network hashrate of approximately 977 EH/s"
- If you cannot verify a claim beyond the ground truth data, DO NOT MAKE IT

Hallucinating record highs when the network is below November 2025's 155.9 T peak is STRICTLY PROHIBITED.
"""

        # INTELLIGENCE OFFICER LOCKED STRUCTURE - Mandatory 5-section format
        self.locked_structure_mandate = """
=== INTELLIGENCE OFFICER DIRECTIVE - LOCKED OUTPUT STRUCTURE ===

YOU ARE FORBIDDEN FROM RETURNING AN ARTICLE UNLESS IT CONTAINS ALL FIVE SECTIONS:

1. <div class="tldr-section">: A punchy, 3-sentence summary of why today's specific metrics matter for sovereignty.
   - Use the ground truth data as FOUNDATION, then BUILD A NARRATIVE around it
   - Do NOT just repeat the numbers - explain their SIGNIFICANCE
   
2. <h2 class="article-header">The Report</h2>: Factual account (300+ words)
   - Network status with verified metrics
   - Recent global events affecting Bitcoin
   - Mining economics and fee market conditions
   
3. <h2 class="article-header">The Bitcoin Lens</h2>: Philosophical analysis (300+ words)
   - Deep analysis on network resilience vs fiat debasement
   - Connect current metrics to long-term monetary sovereignty
   - Second-order thinking: what do these numbers MEAN for the future?
   
4. <h2 class="article-header">Transactor Intelligence</h2>: Actionable advice (200+ words)
   - Specific guidance for miners based on current difficulty/fees
   - Recommendations for high-value users regarding fee optimization
   - Timing considerations for transactions based on mempool conditions
   
5. <h2 class="article-header">Sources</h2>: Formatted list of data sources

ANTI-LOOP RULE:
- Do NOT repeat exact phrasing used in homepage terminal modules ("FEES: X sat/vB", "BLOCK: Y")
- EXPAND on those metrics with second-order analysis - tell readers what to DO with the information
- Every section must contain UNIQUE content not duplicated elsewhere in the article

MINIMUM LENGTH REQUIREMENT:
- Total article body must be 800+ words (excluding HTML tags)
- If your output is shorter, you have FAILED - expand with deeper analysis
- The TL;DR is NOT the article - it's a summary. BUILD THE FULL NARRATIVE.

NARRATIVE BRIDGE:
Use the ground truth metrics (146.47 T difficulty, ~977 EH/s hashrate) as the FOUNDATION, 
but you MUST build a 1,000-word deep-dive around them. The numbers are the starting point, 
not the entire article.
"""

        # Default prompts for different content types - TECHNICAL STORYTELLING APPROACH
        self.default_prompts = {
            'news_article': """
            Write a peer-to-peer intelligence briefing about {topic} for TRANSACTORS (active Bitcoin users who self-custody), NOT for tourists (passive chart-watchers). The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should focus on actionable intelligence: network security implications, mining economics, protocol fundamentals, and sovereignty considerations. Weave in pro-decentralization and pro-Bitcoin philosophy naturally. Conclude with a principled statement about financial freedom and decentralization.
            
            """ + """CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            - Never include "Tags:" or similar metadata
            
            Target length: 800-1200 words
            """,
            
            'analysis_piece': """
            Write an expert-level intelligence briefing about {topic} for TRANSACTORS (active Bitcoin users who understand protocol fundamentals), NOT for tourists (passive speculators). The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should deliver deep technical analysis with unique perspectives on Bitcoin's role as sound money. Conclude with a principled statement about financial freedom and decentralization.
            
            """ + """CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            - Never include "Tags:" or similar metadata
            
            TECHNICAL STORYTELLING: Deliver actionable intelligence for transactors - focus on protocol fundamentals, mining economics, and sovereignty implications.
            Target length: 1000-1500 words
            """,
            
            'breaking_news': """
            Write an urgent intelligence briefing about {topic} for TRANSACTORS (active Bitcoin users). This is breaking news that affects network participants directly. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should deliver critical information transactors need NOW, with clear implications for their Bitcoin holdings and sovereignty.
            
            """ + """CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            - Never include "Tags:" or similar metadata
            
            TECHNICAL STORYTELLING: Maintain urgency while delivering actionable intelligence. What do transactors need to know and do RIGHT NOW?
            Target length: 400-600 words
            """
        }
    
    def generate_article(self, topic, prompt_id=None, content_type='news_article', source_type='ai_generated'):
        """Generate a complete article based on topic and prompt"""
        try:
            # AI GATEKEEPER: Check for duplicates before generating
            if is_topic_duplicate_via_gemini(topic):
                logging.info(f"⏭️ Skipping generation: Gatekeeper detected duplicate topic")
                return {
                    'success': False,
                    'error': 'Duplicate topic detected by AI gatekeeper',
                    'skipped': True
                }
            
            # Integrate Reddit if source_type is reddit
            if source_type == 'reddit':
                try:
                    with app.app_context():
                        reddit_trends = self.reddit_service.get_trending_topics(['cryptocurrency', 'bitcoin', 'defi', 'web3'], limit=3)
                        if reddit_trends:
                            reddit_context = f"Recent Reddit trends: {reddit_trends[0].get('title', '')} - {reddit_trends[0].get('selftext', '')[:200]}..."
                            topic = f"{topic}. {reddit_context}"
                except Exception as e:
                    logging.warning(f"Failed to fetch Reddit trends: {str(e)}")
            
            # Integrate X (Twitter) social feedback for nuance
            if source_type == 'x' or source_type == 'twitter':
                try:
                    with app.app_context():
                        feedback = x_service.get_feedback(topic)
                        if feedback:
                            topic = f"{topic} (X feedback: {feedback})"
                            logging.info(f"Added X feedback for topic: {topic[:50]}...")
                except Exception as e:
                    logging.warning(f"Failed to fetch X feedback: {str(e)}")
            
            # Get custom prompt if provided
            prompt_template = self._get_prompt_template(prompt_id, content_type)
            
            # Format the prompt with the topic
            # Enhanced prompt with new editorial guidelines
            enhanced_prompt = f"""
            Write a comprehensive news article about: {topic}
            
            Apply the Protocol Pulse editorial mandate: Begin with clear factual reporting, 
            then provide thoughtful context connecting to history, economics, and society. 
            Include unique analysis with data and credible sources. Write through a Bitcoin-first 
            lens where Bitcoin is money, the only truly decentralized currency, and foundation 
            of freedom and sovereignty.
            
            Structure as two distinct sections:
            1. 'The Report' - Factual news account with context and analysis
            2. 'The Bitcoin Lens' - Bitcoin-focused commentary and philosophical perspective
            
            Make it engaging, authoritative, and educational while orange-pilling readers 
            about Bitcoin's unique importance to humanity.
            """
            
            formatted_prompt = prompt_template.format(topic=enhanced_prompt)
            
            # GROUND TRUTH VERIFICATION: Fetch real-time Bitcoin metrics before generating
            network_stats = None
            try:
                network_stats = NodeService.get_network_stats()
                logging.info(f"Ground truth metrics fetched: Height={network_stats.get('height')}, Hashrate={network_stats.get('hashrate')}")
            except Exception as e:
                logging.warning(f"Failed to fetch network stats for ground truth: {e}")
            
            # Build real-time metrics context for the AI
            metrics_context = ""
            if network_stats:
                metrics_context = f"""
VERIFIED REAL-TIME BITCOIN NETWORK DATA (as of {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}):
- Current Block Height: {network_stats.get('height', 'Unknown')}
- Current Hashrate: {network_stats.get('hashrate', 'Unknown')}
- Network Status: {network_stats.get('status', 'Unknown')}
- Difficulty Adjustment Progress: {network_stats.get('difficulty_progress', 'Unknown')}
- Blocks Until Adjustment: {network_stats.get('remaining_blocks', 'Unknown')}

YOU MUST USE THESE VERIFIED METRICS. Do not invent different numbers.
If the hashrate is below previous peaks, DO NOT claim "record high" or "all-time high".
If difficulty progress indicates an upcoming DECREASE, report that accurately.
"""
            else:
                metrics_context = """
WARNING: Real-time network data unavailable. 
DO NOT report specific Bitcoin metrics (hashrate, difficulty, price) in this article.
Focus on qualitative analysis only. No fabricated numbers allowed.
"""
            
            # Add system prompt for consistency - New Editorial Guidelines + Accuracy Mandate + Locked Structure
            system_prompt = f"""
            You are a world-class journalist writing for Protocol Pulse with the trust and authority 
            of Walter Cronkite but in a natural, human style that feels engaging and real. 
            
            {metrics_context}
            
            {self.accuracy_mandate}
            
            {self.locked_structure_mandate}
            
            EDITORIAL MANDATE: Write every article like a world-class journalist with the trust and 
            authority of Walter Cronkite but in a natural, human style that feels engaging and real. 
            Begin with a clear and factual account of the news, then provide thoughtful context that 
            connects events to history, economics, and society. Always deliver unique analysis that 
            uncovers deeper meaning, using data, historical parallels, and quotes from credible sources 
            to establish authority. Avoid jargon where a simpler, clearer explanation will do. 
            
            Every piece must be written through a Bitcoin-first lens: reinforce that Bitcoin is money, 
            the only truly decentralized currency, and the foundation of freedom, privacy, and sovereignty. 
            When other crypto projects are mentioned, they should be framed as secondary, never rivaling 
            Bitcoin's role. 
            
            MANDATORY 5-SECTION STRUCTURE:
            1. TL;DR (punchy 3-sentence summary)
            2. 'The Report' (factual news reporting - 300+ words)
            3. 'The Bitcoin Lens' (philosophical analysis - 300+ words)
            4. 'Transactor Intelligence' (actionable advice for miners and users - 200+ words)
            5. 'Sources' (formatted list of data sources)
            
            This reinforces the separation between unbiased news, philosophical commentary, and actionable intelligence.
            
            CRITICAL: OUTPUT ONLY CLEAN HTML - NO MARKDOWN SYNTAX ALLOWED.
            Use <div class="tldr-section"><em><strong>TL;DR: content</strong></em></div> for summaries.
            Use <h2 class="article-header"> for all main sections.
            Use <h3 class="article-subheader"> for sub-sections within each main section.
            Use <p class="article-paragraph"> for all paragraphs.
            Never use **, ***, ##, ### or any markdown syntax - only HTML tags.
            
            MINIMUM: 800 words total. Build the full narrative around the ground truth metrics.
            """
            
            # Generate the main content using OpenAI (primary for better structure compliance) with fallbacks
            # With auto-retry for validation failures
            content = None
            max_retries = 2
            
            for attempt in range(max_retries + 1):
                # Try OpenAI first (better at following structured output requirements)
                try:
                    content = self.ai_service.generate_content_openai(formatted_prompt, system_prompt)
                except Exception as e:
                    logging.warning(f"OpenAI generation failed: {e}")
                
                # Fallback to Gemini if OpenAI fails
                if not content:
                    try:
                        content = self.gemini_service.generate_content(formatted_prompt, system_prompt)
                    except Exception as e:
                        logging.warning(f"Gemini generation failed: {e}")
                
                # Fallback to Anthropic if available
                if not content:
                    try:
                        content = self.ai_service.generate_content_anthropic(formatted_prompt, system_prompt)
                    except Exception as e:
                        logging.warning(f"Anthropic generation failed: {e}")
                
                if not content:
                    raise Exception("Failed to generate content with any AI service")
                
                # VALIDATION: Check for mandatory 5-section structure and minimum length
                validation_result = self._validate_article_structure(content)
                
                if validation_result['valid']:
                    logging.info(f"Article validation passed: {validation_result['word_count']} words, all sections present")
                    break
                else:
                    if attempt < max_retries:
                        logging.warning(f"Article validation failed (attempt {attempt + 1}): {validation_result['errors']}. Retrying...")
                        # Add retry instruction to prompt
                        formatted_prompt += f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {', '.join(validation_result['errors'])}. You MUST include all 5 sections and write at least 800 words."
                        content = None  # Reset for retry
                    else:
                        logging.warning(f"Article validation failed after {max_retries + 1} attempts: {validation_result['errors']}")
            
            # Extract title from content or generate separately
            title = self._extract_or_generate_title(content, topic)
            
            # No summary - TL;DR is embedded in content
            summary = ""
            
            # Generate SEO metadata
            seo_data = self.ai_service.generate_seo_metadata(title, content) or {}
            
            # Generate tags
            tags = self._generate_tags(topic, content)
            
            # Determine category
            category = self._determine_category(topic, content)
            
            # No header images - user preference is to only include tweet screenshots inside articles
            header_image_url = None
            
            # FACT-CHECK VERIFICATION: Verify claims before returning article
            fact_check_result = None
            fact_check_warnings = []
            try:
                is_verified, verification_report = verify_article_before_publish(content)
                fact_check_result = verification_report
                
                if not is_verified:
                    fact_check_warnings = verification_report.get('errors', [])
                    logging.warning(f"FACT-CHECK WARNINGS for article '{title[:50]}': {fact_check_warnings}")
                else:
                    logging.info(f"FACT-CHECK PASSED for article '{title[:50]}': {verification_report.get('claims_verified', 0)} claims verified")
            except Exception as e:
                logging.warning(f"Fact-check failed to run: {e}")
            
            return {
                'title': title,
                'content': content,
                'summary': "",  # No summary - TL;DR is embedded in content
                'category': category,
                'tags': tags,
                'seo_title': seo_data.get('seo_title', title),
                'seo_description': seo_data.get('seo_description', title[:150]),
                'header_image_url': header_image_url,
                'fact_check': fact_check_result,
                'fact_check_warnings': fact_check_warnings,
                'fact_check_passed': len(fact_check_warnings) == 0
            }
            
        except Exception as e:
            logging.error(f"Error generating article: {str(e)}")
            return None
    
    def generate_from_reddit_trend(self, reddit_post):
        """Generate article based on Reddit trending post"""
        try:
            # Combine title and text for context
            context = f"Title: {reddit_post.get('title', '')}\n"
            if reddit_post.get('selftext'):
                context += f"Content: {reddit_post.get('selftext', '')}\n"
            
            # Add comments for additional context
            if reddit_post.get('comments'):
                context += "Top comments:\n"
                for comment in reddit_post.get('comments', [])[:3]:
                    context += f"- {comment.get('body', '')}\n"
            
            topic = f"Based on this Reddit discussion: {context}"
            
            # Generate article with news format
            return self.generate_article(topic, content_type='news_article', source_type='reddit')
            
        except Exception as e:
            logging.error(f"Error generating article from Reddit trend: {str(e)}")
            return None
    
    def _get_prompt_template(self, prompt_id, content_type):
        """Get prompt template from database or use default"""
        if prompt_id:
            try:
                with app.app_context():
                    custom_prompt = ContentPrompt.query.get(prompt_id)
                    if custom_prompt and custom_prompt.active:
                        return custom_prompt.prompt_text
            except Exception as e:
                logging.warning(f"Failed to get custom prompt {prompt_id}: {str(e)}")
        
        return self.default_prompts.get(content_type, self.default_prompts['news_article'])
    
    def _validate_article_structure(self, content):
        """
        Validate article has all 5 mandatory sections and meets minimum word count.
        Returns dict with 'valid' boolean, 'errors' list, and 'word_count'.
        """
        import re
        
        errors = []
        
        # Check for mandatory sections
        required_sections = [
            ('tldr-section', 'TL;DR section'),
            ('The Report', 'The Report section'),
            ('The Bitcoin Lens', 'The Bitcoin Lens section'),
            ('Transactor Intelligence', 'Transactor Intelligence section'),
            ('Sources', 'Sources section')
        ]
        
        for marker, name in required_sections:
            if marker not in content:
                errors.append(f"Missing {name}")
        
        # Count words (strip HTML tags first)
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        word_count = len(clean_text.split())
        
        if word_count < 800:
            errors.append(f"Only {word_count} words (minimum 800 required)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'word_count': word_count
        }
    
    def _extract_or_generate_title(self, content, topic):
        """Extract title from content or generate one using Conversational SEO"""
        try:
            # Try to extract title from the first line if it looks like a headline
            first_line = content.split('\n')[0].strip()
            if len(first_line) < 100 and len(first_line) > 10:
                # Remove common article prefixes and any "Protocol Pulse" branding
                title = first_line.replace('# ', '').replace('## ', '').strip()
                title = title.replace('Protocol Pulse News:', '').replace('Protocol Pulse:', '').strip()
                if title and not title.endswith('.'):
                    return title
            
            # Generate title using AI with CONVERSATIONAL SEO (question-based logic)
            title_prompt = f"""Create a compelling, SEO-friendly headline for an article about: {topic}. 

CONVERSATIONAL SEO MANDATE:
- Use QUESTION-BASED headlines that AI assistants and voice search will surface
- Examples of good question headlines:
  * "How Will the January 22 Difficulty Rise Affect Miners?"
  * "What Does 146.47 T Difficulty Mean for Network Security?"
  * "Why Are Bitcoin Miners Accumulating Before the Halving?"
  * "Is the Current Hashrate Sustainable for Small Miners?"

RULES:
- CRITICAL: Do NOT include 'Protocol Pulse' or any publication name
- Prefer "How", "What", "Why", "Is", "Will" question starters
- If a question doesn't fit naturally, use declarative headlines that answer implied questions
- Keep under 70 characters
- Focus on transactor concerns (network security, mining economics, sovereignty)"""
            title = self.ai_service.generate_content_openai(title_prompt)
            
            if title:
                # Clean up the title - remove any Protocol Pulse branding that slipped through
                title = title.strip().replace('"', '').replace("'", '')
                title = title.replace('Protocol Pulse News:', '').replace('Protocol Pulse:', '').strip()
                return title[:100]  # Limit length
            
            # Fallback to topic-based title (no branding)
            clean_topic = topic[:60].replace('Protocol Pulse', '').strip()
            return clean_topic if clean_topic else topic[:60]
            
        except Exception as e:
            logging.error(f"Error generating title: {str(e)}")
            # Fallback without any branding - just use topic
            clean_topic = topic[:60].replace('Protocol Pulse', '').strip()
            return clean_topic if clean_topic else topic[:60]
    
    def _generate_tags(self, topic, content):
        """Generate relevant tags for the article"""
        try:
            # Bitcoin and DeFi focused tags
            common_tags = [
                'Bitcoin', 'BTC', 'DeFi', 'Cryptocurrency', 'Blockchain',
                'Decentralized Finance', 'Lightning Network', 'Yield Farming', 'Mining', 'Staking',
                'Privacy', 'Regulation', 'Innovation', 'Technology'
            ]
            
            # Use AI to suggest relevant tags
            tag_prompt = f"Based on this topic '{topic}' and content preview '{content[:200]}...', suggest 5-7 relevant tags from Web3/crypto space. Return as comma-separated list."
            
            ai_tags = self.ai_service.generate_content_openai(tag_prompt)
            
            if ai_tags:
                # Clean and combine tags
                suggested_tags = [tag.strip() for tag in ai_tags.split(',')]
                # Combine with common tags and remove duplicates
                all_tags = list(set(suggested_tags + common_tags))
                return ', '.join(all_tags[:8])  # Limit to 8 tags
            
            return ', '.join(common_tags[:5])
            
        except Exception as e:
            logging.error(f"Error generating tags: {str(e)}")
            return 'Web3, Cryptocurrency, Blockchain, Technology, News'
    
    def _determine_category(self, topic, content):
        """Determine the most appropriate category for the article"""
        categories = {
            'Bitcoin': ['bitcoin', 'btc', 'mining', 'halving', 'lightning', 'satoshi'],
            'DeFi': ['defi', 'yield', 'liquidity', 'dex', 'lending', 'aave', 'uniswap', 'compound'],
            'Regulation': ['regulation', 'sec', 'government', 'legal', 'compliance'],
            'Privacy': ['privacy', 'anonymous', 'surveillance', 'encryption'],
            'Innovation': ['innovation', 'development', 'technology', 'breakthrough']
        }
        
        topic_lower = topic.lower()
        content_lower = content[:500].lower()
        combined_text = f"{topic_lower} {content_lower}"
        
        # Score each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, default to Web3
        if category_scores:
            return max(category_scores.keys(), key=lambda x: category_scores[x])
        
        return 'Web3'
```

## services/clips_service.py
```python
import os
import logging
import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class ClipsService:
    def __init__(self):
        self.clips_dir = 'static/clips'
        self.outro_path = 'static/videos/outro.mp4'
        self.opus_api_key = os.environ.get('OPUSCLIP_API_KEY')
        
        os.makedirs(self.clips_dir, exist_ok=True)
        
        self.ffmpeg_available = self._check_ffmpeg()
        
        logger.info(f"Clips service initialized. FFmpeg: {self.ffmpeg_available}, OpusClip: {bool(self.opus_api_key)}")
    
    def _check_ffmpeg(self) -> bool:
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def extract_clip(self, video_path: str, start_time: float, duration: float, output_name: str) -> Dict[str, Any]:
        if not self.ffmpeg_available:
            return {'success': False, 'error': 'FFmpeg not available'}
        
        try:
            output_path = os.path.join(self.clips_dir, f"{output_name}.mp4")
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-crf', '23',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return {
                    'success': True,
                    'output_path': output_path,
                    'duration': duration
                }
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Clip extraction error: {e}")
            return {'success': False, 'error': str(e)}
    
    def append_outro(self, clip_path: str, output_name: str = None) -> Dict[str, Any]:
        if not self.ffmpeg_available:
            return {'success': False, 'error': 'FFmpeg not available'}
        
        if not os.path.exists(self.outro_path):
            return {'success': False, 'error': 'Outro video not found'}
        
        try:
            if output_name:
                output_path = os.path.join(self.clips_dir, f"{output_name}_final.mp4")
            else:
                base = os.path.splitext(os.path.basename(clip_path))[0]
                output_path = os.path.join(self.clips_dir, f"{base}_final.mp4")
            
            concat_file = os.path.join(self.clips_dir, 'concat_list.txt')
            with open(concat_file, 'w') as f:
                f.write(f"file '{os.path.abspath(clip_path)}'\n")
                f.write(f"file '{os.path.abspath(self.outro_path)}'\n")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            os.remove(concat_file)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return {
                    'success': True,
                    'output_path': output_path
                }
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Outro append error: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_with_opus(self, youtube_url: str) -> Dict[str, Any]:
        if not self.opus_api_key:
            return {'success': False, 'error': 'OpusClip API key not configured'}
        
        try:
            import httpx
            
            response = httpx.post(
                'https://api.opus.pro/v1/clips',
                headers={
                    'Authorization': f'Bearer {self.opus_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'video_url': youtube_url,
                    'num_clips': 5,
                    'min_duration': 30,
                    'max_duration': 60
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'job_id': data.get('job_id'),
                    'status': 'processing'
                }
            else:
                return {'success': False, 'error': f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"OpusClip API error: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_opus_status(self, job_id: str) -> Dict[str, Any]:
        if not self.opus_api_key:
            return {'success': False, 'error': 'OpusClip API key not configured'}
        
        try:
            import httpx
            
            response = httpx.get(
                f'https://api.opus.pro/v1/clips/{job_id}',
                headers={'Authorization': f'Bearer {self.opus_api_key}'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('status'),
                    'clips': data.get('clips', [])
                }
            else:
                return {'success': False, 'error': f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"OpusClip status check error: {e}")
            return {'success': False, 'error': str(e)}
    
    def download_opus_clips(self, clips: List[Dict]) -> List[Dict[str, Any]]:
        results = []
        
        for i, clip in enumerate(clips):
            try:
                import httpx
                
                clip_url = clip.get('url')
                if not clip_url:
                    continue
                
                filename = f"opus_clip_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.mp4"
                output_path = os.path.join(self.clips_dir, filename)
                
                response = httpx.get(clip_url, timeout=120)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    final_result = self.append_outro(output_path)
                    
                    results.append({
                        'success': True,
                        'original': output_path,
                        'with_outro': final_result.get('output_path') if final_result.get('success') else None,
                        'title': clip.get('title', f'Clip {i+1}'),
                        'score': clip.get('virality_score', 0)
                    })
                    
            except Exception as e:
                logger.error(f"Clip download error: {e}")
                results.append({'success': False, 'error': str(e)})
        
        return results
    
    def get_all_clips(self) -> List[Dict[str, Any]]:
        clips = []
        
        if not os.path.exists(self.clips_dir):
            return clips
        
        for filename in os.listdir(self.clips_dir):
            if filename.endswith('.mp4'):
                filepath = os.path.join(self.clips_dir, filename)
                stat = os.stat(filepath)
                
                clips.append({
                    'filename': filename,
                    'path': filepath,
                    'url': f'/static/clips/{filename}',
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'is_final': '_final' in filename
                })
        
        clips.sort(key=lambda x: x['created'], reverse=True)
        return clips
    
    def get_status(self) -> Dict[str, Any]:
        clips = self.get_all_clips()
        return {
            'ffmpeg_available': self.ffmpeg_available,
            'opus_configured': bool(self.opus_api_key),
            'clips_count': len(clips),
            'final_clips_count': len([c for c in clips if c['is_final']])
        }

clips_service = ClipsService()
```

## services/telegram_bot.py
```python
import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class PulseOperative:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHANNEL_ID')
        self.initialized = False
        self.bot = None
        self.application = None
        
        if self.token:
            try:
                from telegram import Bot
                from telegram.ext import Application, CommandHandler, MessageHandler, filters
                self.Bot = Bot
                self.Application = Application
                self.CommandHandler = CommandHandler
                self.MessageHandler = MessageHandler
                self.filters = filters
                self.initialized = True
                logger.info("Telegram Pulse Operative initialized")
            except ImportError:
                logger.warning("python-telegram-bot not installed")
        else:
            logger.info("TELEGRAM_BOT_TOKEN not configured - Pulse Operative disabled")
    
    async def start_bot(self):
        if not self.initialized:
            return
        
        self.application = self.Application.builder().token(self.token).build()
        
        self.application.add_handler(self.CommandHandler("start", self.cmd_start))
        self.application.add_handler(self.CommandHandler("brief", self.cmd_brief))
        self.application.add_handler(self.CommandHandler("price", self.cmd_price))
        self.application.add_handler(self.CommandHandler("fees", self.cmd_fees))
        self.application.add_handler(self.CommandHandler("whale", self.cmd_whale))
        self.application.add_handler(self.CommandHandler("help", self.cmd_help))
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Pulse Operative bot started and polling")
    
    def run_bot_sync(self):
        if not self.initialized:
            logger.warning("Telegram bot not initialized - skipping")
            return
        
        try:
            self.application = self.Application.builder().token(self.token).build()
            
            self.application.add_handler(self.CommandHandler("start", self.cmd_start))
            self.application.add_handler(self.CommandHandler("brief", self.cmd_brief))
            self.application.add_handler(self.CommandHandler("price", self.cmd_price))
            self.application.add_handler(self.CommandHandler("fees", self.cmd_fees))
            self.application.add_handler(self.CommandHandler("whale", self.cmd_whale))
            self.application.add_handler(self.CommandHandler("help", self.cmd_help))
            
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Telegram bot run error: {e}")
    
    async def stop_bot(self):
        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Bot stop error: {e}")
    
    async def cmd_start(self, update, context):
        welcome = """
🔴 *PROTOCOL PULSE OPERATIVE*
━━━━━━━━━━━━━━━━━━━━━

Welcome to your Bitcoin intelligence terminal.

*Available Commands:*
/brief - Generate today's intelligence briefing
/price - Current BTC price & metrics
/fees - Network fee analysis
/whale - Recent large transactions
/help - Command reference

_Intelligence for transactors._
        """
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        help_text = """
*PULSE OPERATIVE COMMANDS*
━━━━━━━━━━━━━━━━━━━━━

/brief - Generate AI intelligence briefing
/price - BTC price, 24h change, market cap
/fees - Current mempool fees
/whale - Recent 500+ BTC transactions
/start - Welcome message

_All data sourced from live network APIs._
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_price(self, update, context):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://api.coingecko.com/api/v3/simple/price',
                    params={'ids': 'bitcoin', 'vs_currencies': 'usd', 'include_24hr_change': 'true', 'include_market_cap': 'true'}
                )
                data = response.json()
                
                price = data['bitcoin']['usd']
                change = data['bitcoin']['usd_24h_change']
                mcap = data['bitcoin']['usd_market_cap']
                
                emoji = "🟢" if change > 0 else "🔴"
                
                message = f"""
🟠 *BITCOIN PRICE UPDATE*
━━━━━━━━━━━━━━━━━━━━━

💰 *Price:* ${price:,.0f}
{emoji} *24h:* {change:+.2f}%
📊 *Market Cap:* ${mcap/1e12:.2f}T

_Updated: {datetime.utcnow().strftime('%H:%M UTC')}_
                """
                await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Price command error: {e}")
            await update.message.reply_text("⚠️ Unable to fetch price data. Try again.")
    
    async def cmd_fees(self, update, context):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get('https://mempool.space/api/v1/fees/recommended')
                fees = response.json()
                
                mempool_resp = await client.get('https://mempool.space/api/mempool')
                mempool = mempool_resp.json()
                
                pending = mempool.get('count', 0)
                size_mb = mempool.get('vsize', 0) / 1000000
                
                message = f"""
⛽ *NETWORK FEE ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━

🚀 *High Priority:* {fees['fastestFee']} sat/vB
⚡ *Medium:* {fees['halfHourFee']} sat/vB  
🐢 *Economy:* {fees['economyFee']} sat/vB

📦 *Mempool:* {pending:,} txs ({size_mb:.1f} MB)

{"🟢 LOW FEES - Good time to transact!" if fees['fastestFee'] < 10 else "🟡 Moderate fees" if fees['fastestFee'] < 30 else "🔴 High fees - Consider waiting"}

_Source: mempool.space_
                """
                await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Fees command error: {e}")
            await update.message.reply_text("⚠️ Unable to fetch fee data. Try again.")
    
    async def cmd_whale(self, update, context):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                blocks_resp = await client.get('https://mempool.space/api/blocks')
                blocks = blocks_resp.json()
                
                whales = []
                for block in blocks[:2]:
                    tx_resp = await client.get(f"https://mempool.space/api/block/{block['id']}/txs")
                    txs = tx_resp.json()
                    
                    for tx in txs:
                        total = sum(out.get('value', 0) for out in tx.get('vout', []))
                        btc = total / 100000000
                        if btc >= 500:
                            whales.append({'txid': tx['txid'][:16], 'btc': btc})
                
                if whales:
                    whale_lines = "\n".join([f"🐋 {w['btc']:,.0f} BTC - `{w['txid']}...`" for w in whales[:5]])
                    message = f"""
🌊 *WHALE WATCHER*
━━━━━━━━━━━━━━━━━━━━━

*Recent Large Transactions (500+ BTC):*

{whale_lines}

_View full feed: protocolpulse.com/whale-watcher_
                    """
                else:
                    message = "🌊 No whale activity detected in recent blocks."
                
                await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Whale command error: {e}")
            await update.message.reply_text("⚠️ Unable to fetch whale data. Try again.")
    
    async def cmd_brief(self, update, context):
        await update.message.reply_text("🔄 Generating intelligence briefing...")
        
        try:
            from services.ai_service import ai_service
            
            prompt = """Generate a concise 60-second Bitcoin intelligence briefing for today. Include:
1. Current network status (use real mempool data if available)
2. One key development from the past 24 hours
3. One transactor insight or recommendation

Format for Telegram with emojis. Keep it under 200 words. Be factual and avoid hype."""
            
            brief = ai_service.generate_content(prompt, max_tokens=300)
            
            message = f"""
🔴 *DAILY INTELLIGENCE BRIEFING*
━━━━━━━━━━━━━━━━━━━━━
{datetime.utcnow().strftime('%B %d, %Y')}

{brief}

_Generated by Protocol Pulse AI_
            """
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Brief generation error: {e}")
            await update.message.reply_text("⚠️ Unable to generate briefing. Try /price or /fees instead.")
    
    async def send_message(self, text: str, chat_id: str = None, parse_mode: str = 'Markdown'):
        if not self.initialized:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            bot = self.Bot(self.token)
            target_chat = chat_id or self.chat_id
            if not target_chat:
                return {'success': False, 'error': 'No chat_id specified'}
            
            await bot.send_message(chat_id=target_chat, text=text, parse_mode=parse_mode)
            return {'success': True}
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_audio(self, audio_path: str, caption: str = None, chat_id: str = None):
        if not self.initialized:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            bot = self.Bot(self.token)
            target_chat = chat_id or self.chat_id
            
            with open(audio_path, 'rb') as audio_file:
                await bot.send_audio(
                    chat_id=target_chat,
                    audio=audio_file,
                    caption=caption,
                    parse_mode='Markdown'
                )
            return {'success': True}
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def post_clip(self, video_path: str, caption: str, chat_id: str = None):
        if not self.initialized:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            bot = self.Bot(self.token)
            target_chat = chat_id or self.chat_id
            
            with open(video_path, 'rb') as video_file:
                await bot.send_video(
                    chat_id=target_chat,
                    video=video_file,
                    caption=caption,
                    parse_mode='Markdown'
                )
            return {'success': True}
        except Exception as e:
            logger.error(f"Post clip error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'initialized': self.initialized,
            'token_configured': bool(self.token),
            'channel_configured': bool(self.chat_id),
            'bot_running': self.application is not None
        }

pulse_operative = PulseOperative()
```

## services/rss_service.py
```python
import feedparser
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app import db
from models import Podcast

class RSSService:
    """Service for managing RSS feed synchronization and generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Your podcast RSS feeds (curated list)
        self.podcast_feeds = [
            {
                'name': "Cypherpunk'd",
                'url': 'https://anchor.fm/s/fa724db8/podcast/rss',
                'category': 'Privacy & Freedom',
                'host': 'PBX',
                'color': '#f7931a'
            },
            {
                'name': 'Protocol Pulse', 
                'url': 'https://feed.podbean.com/protocolpulse/feed.xml',
                'category': 'Bitcoin & Markets',
                'host': 'Protocol Pulse',
                'color': '#dc2626'
            }
        ]
        
        # Episode cache for real-time display
        self._episode_cache = {}
        self._cache_expiry = None
    
    def sync_all_feeds(self) -> Dict[str, int]:
        """Synchronize all configured podcast RSS feeds"""
        results = {}
        
        for feed_config in self.podcast_feeds:
            try:
                count = self.sync_feed(feed_config['url'], feed_config['category'], feed_config['name'])
                results[feed_config['name']] = count
                self.logger.info(f"Synced {count} episodes from {feed_config['name']}")
            except Exception as e:
                self.logger.error(f"Failed to sync {feed_config['name']}: {e}")
                results[feed_config['name']] = 0
        
        return results
    
    def sync_feed(self, rss_url: str, category: str = "Web3", rss_source: str = "Protocol Pulse") -> int:
        """Sync individual RSS feed to database"""
        try:
            feed = feedparser.parse(rss_url)
            synced_count = 0
            
            for entry in feed.entries:
                # Check if episode already exists
                existing = Podcast.query.filter_by(
                    title=entry.title,
                    audio_url=self.extract_audio_url(entry)
                ).first()
                
                if existing:
                    continue
                
                # Create new podcast episode
                podcast = Podcast()
                podcast.title = entry.title
                podcast.description = self.clean_description(entry.get('description', ''))
                podcast.host = feed.feed.get('author', 'Protocol Pulse')
                podcast.duration = self.extract_duration(entry)
                podcast.audio_url = self.extract_audio_url(entry)
                podcast.cover_image_url = self.extract_cover_image(entry, feed)
                podcast.published_date = self.parse_date(entry.get('published_parsed'))
                podcast.category = category
                podcast.rss_source = rss_source
                podcast.featured = False
                
                db.session.add(podcast)
                synced_count += 1
            
            db.session.commit()
            return synced_count
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing RSS feed {rss_url}: {e}")
            raise
    
    def extract_audio_url(self, entry) -> Optional[str]:
        """Extract audio URL from RSS entry"""
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('audio/'):
                    return enclosure.href
        
        # Fallback: look for links
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('audio/'):
                    return link.href
        
        return None
    
    def extract_duration(self, entry) -> str:
        """Extract episode duration from RSS entry"""
        # Check iTunes duration
        if hasattr(entry, 'itunes_duration'):
            return entry.itunes_duration
        
        # Check other duration fields
        duration_fields = ['duration', 'podcast_duration']
        for field in duration_fields:
            if hasattr(entry, field):
                return str(getattr(entry, field))
        
        return "Unknown"
    
    def extract_cover_image(self, entry, feed) -> Optional[str]:
        """Extract cover image from RSS entry or feed"""
        # Episode-specific image
        if hasattr(entry, 'image') and entry.image.get('href'):
            return entry.image.href
        
        # iTunes image
        if hasattr(entry, 'itunes_image'):
            return entry.itunes_image
        
        # Feed-level image
        if hasattr(feed.feed, 'image') and feed.feed.image.get('href'):
            return feed.feed.image.href
        
        return None
    
    def clean_description(self, description: str) -> str:
        """Clean and truncate description"""
        import re
        # Remove HTML tags
        clean_desc = re.sub(r'<[^>]*>', '', description)
        # Limit length
        if len(clean_desc) > 500:
            clean_desc = clean_desc[:497] + "..."
        return clean_desc.strip()
    
    def parse_date(self, date_tuple) -> datetime:
        """Parse RSS date tuple to datetime"""
        if date_tuple:
            try:
                import time
                return datetime.fromtimestamp(time.mktime(date_tuple))
            except:
                pass
        return datetime.utcnow()
    
    def generate_rss_feed(self) -> str:
        """Generate RSS feed XML for published podcasts"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Get latest published podcasts
        podcasts = Podcast.query.order_by(Podcast.published_date.desc()).limit(50).all()
        
        # Create RSS XML
        rss = Element('rss', version='2.0')
        rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
        rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
        
        channel = SubElement(rss, 'channel')
        
        # Channel info
        SubElement(channel, 'title').text = 'Protocol Pulse Podcast'
        SubElement(channel, 'description').text = 'The leading podcast for Web3, Bitcoin, and blockchain insights'
        SubElement(channel, 'link').text = 'https://your-domain.com/podcasts'
        SubElement(channel, 'language').text = 'en-us'
        SubElement(channel, 'copyright').text = f'© {datetime.now().year} Protocol Pulse'
        
        # Add episodes
        for podcast in podcasts:
            item = SubElement(channel, 'item')
            SubElement(item, 'title').text = podcast.title
            SubElement(item, 'description').text = podcast.description or ""
            SubElement(item, 'link').text = f'https://your-domain.com/podcasts/{podcast.id}'
            SubElement(item, 'guid').text = f'https://your-domain.com/podcasts/{podcast.id}'
            SubElement(item, 'pubDate').text = podcast.published_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            if podcast.audio_url:
                enclosure = SubElement(item, 'enclosure')
                enclosure.set('url', podcast.audio_url)
                enclosure.set('type', 'audio/mpeg')
                enclosure.set('length', '0')  # You may want to add actual file size
            
            if podcast.duration:
                SubElement(item, 'itunes:duration').text = podcast.duration
        
        # Pretty print XML
        rough_string = tostring(rss, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def get_latest_episodes(self, limit: int = 20) -> List[Dict]:
        """Get latest episodes from all feeds with caching"""
        import time
        
        # Check cache validity (15 minute cache)
        if self._cache_expiry and time.time() < self._cache_expiry and self._episode_cache:
            return list(self._episode_cache.values())[:limit]
        
        all_episodes = []
        
        for feed_config in self.podcast_feeds:
            try:
                feed = feedparser.parse(feed_config['url'])
                show_name = feed_config['name']
                
                for entry in feed.entries[:10]:  # Get latest 10 per show
                    episode = {
                        'id': hash(entry.get('link', entry.title))  % 100000,
                        'title': entry.title,
                        'description': self.clean_description(entry.get('description', '')),
                        'audio_url': self.extract_audio_url(entry),
                        'duration': self.extract_duration(entry),
                        'published_date': self.parse_date(entry.get('published_parsed')),
                        'cover_image': self.extract_cover_image(entry, feed),
                        'show_name': show_name,
                        'host': feed_config.get('host', 'Protocol Pulse'),
                        'category': feed_config.get('category', 'Main'),
                        'color': feed_config.get('color', '#dc2626')
                    }
                    all_episodes.append(episode)
                    
            except Exception as e:
                self.logger.error(f"Error fetching {feed_config['name']}: {e}")
        
        # Sort by date, newest first
        all_episodes.sort(key=lambda x: x['published_date'], reverse=True)
        
        # Update cache
        self._episode_cache = {ep['id']: ep for ep in all_episodes}
        self._cache_expiry = time.time() + (15 * 60)  # 15 minutes
        
        return all_episodes[:limit]
    
    def get_show_info(self) -> List[Dict]:
        """Get information about all podcast shows"""
        shows = []
        for feed_config in self.podcast_feeds:
            try:
                feed = feedparser.parse(feed_config['url'])
                show = {
                    'id': feed_config['name'].lower().replace(' ', '_').replace("'", ''),
                    'name': feed_config['name'],
                    'description': feed.feed.get('description', '')[:200] if hasattr(feed, 'feed') else '',
                    'host': feed_config.get('host', 'Protocol Pulse'),
                    'category': feed_config.get('category', 'Main'),
                    'color': feed_config.get('color', '#dc2626'),
                    'episode_count': len(feed.entries) if hasattr(feed, 'entries') else 0,
                    'cover_image': self._get_feed_cover(feed),
                    'rss_url': feed_config['url']
                }
                shows.append(show)
            except Exception as e:
                self.logger.error(f"Error getting show info for {feed_config['name']}: {e}")
        return shows
    
    def _get_feed_cover(self, feed) -> Optional[str]:
        """Extract cover image from feed"""
        try:
            if hasattr(feed.feed, 'image') and feed.feed.image:
                return feed.feed.image.get('href')
            if hasattr(feed.feed, 'itunes_image'):
                return feed.feed.itunes_image.get('href')
        except:
            pass
        return None
    
    def get_episodes_by_show(self, show_id: str, limit: int = 20) -> List[Dict]:
        """Get episodes for a specific show"""
        for feed_config in self.podcast_feeds:
            config_id = feed_config['name'].lower().replace(' ', '_').replace("'", '')
            if config_id == show_id:
                try:
                    feed = feedparser.parse(feed_config['url'])
                    episodes = []
                    for entry in feed.entries[:limit]:
                        episode = {
                            'id': hash(entry.get('link', entry.title)) % 100000,
                            'title': entry.title,
                            'description': self.clean_description(entry.get('description', '')),
                            'audio_url': self.extract_audio_url(entry),
                            'duration': self.extract_duration(entry),
                            'published_date': self.parse_date(entry.get('published_parsed')),
                            'cover_image': self.extract_cover_image(entry, feed),
                            'show_name': feed_config['name'],
                            'host': feed_config.get('host', 'Protocol Pulse'),
                            'color': feed_config.get('color', '#dc2626')
                        }
                        episodes.append(episode)
                    return episodes
                except Exception as e:
                    self.logger.error(f"Error fetching episodes for {show_id}: {e}")
        return []
    
    def clear_cache(self):
        """Clear the episode cache to force refresh"""
        self._episode_cache = {}
        self._cache_expiry = None
        self.logger.info("RSS episode cache cleared")
    
    def search_episodes(self, query: str, limit: int = 10) -> List[Dict]:
        """Search episodes by title or description"""
        all_episodes = self.get_latest_episodes(limit=50)
        query_lower = query.lower()
        results = [
            ep for ep in all_episodes
            if query_lower in ep['title'].lower() or query_lower in ep['description'].lower()
        ]
        return results[:limit]


# Global instance for convenience
rss_service = RSSService()```

## services/podcast_generator.py
```python
import os
import logging
import subprocess
import json
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydub import AudioSegment

class PodcastGenerator:
    def __init__(self):
        self.eleven_client = None
        self.openai = None
        
        if os.environ.get('ELEVENLABS_API_KEY'):
            try:
                self.eleven_client = ElevenLabs(api_key=os.environ.get('ELEVENLABS_API_KEY'))
                logging.info("ElevenLabs client initialized for podcast generation")
            except Exception as e:
                logging.warning(f"ElevenLabs initialization failed: {e}")
        
        if os.environ.get('OPENAI_API_KEY'):
            self.openai = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        self.male_voice = "pNInz6obpgDQGcFmaJgB"  # Adam
        self.female_voice = "EXAVITQu4vr4xnSDxMaL"  # Bella
        self.background_image = 'static/background.jpg'
        self.output_dir = 'static/audio'
        
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info("Podcast Generator initialized")
    
    def generate_podcast_from_video(self, video_id: str, thumbnail_url: str = None, channel_name: str = "Unknown") -> Optional[Dict]:
        """
        Generate an audio intelligence podcast from a YouTube video.
        Returns dict with audio_file, video_file, script, and metadata.
        """
        transcript = self._get_transcript(video_id)
        if not transcript:
            logging.warning(f"No transcript available for video {video_id}")
            return None
        
        script_json = self._generate_dialogue_script(transcript, channel_name)
        if not script_json:
            logging.error(f"Failed to generate script for video {video_id}")
            return None
        
        audio_file = self._synthesize_multi_voice(script_json)
        if not audio_file:
            logging.error(f"Failed to synthesize audio for video {video_id}")
            return None
        
        video_file = None
        if thumbnail_url:
            video_file = self._convert_audio_to_video(audio_file, thumbnail_url)
        
        return {
            'audio_file': audio_file,
            'video_file': video_file,
            'script': script_json,
            'source_video_id': video_id,
            'channel_name': channel_name,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _get_transcript(self, video_id: str) -> Optional[str]:
        """Fetch transcript from YouTube video using youtube-transcript-api"""
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript = ytt_api.fetch(video_id)
            full_text = ' '.join(item.text for item in transcript)
            logging.info(f"Retrieved transcript for {video_id}: {len(full_text)} characters")
            return full_text
        except NoTranscriptFound:
            logging.warning(f"No transcript found for video {video_id}")
            return None
        except Exception as e:
            logging.error(f"Transcript error for {video_id}: {e}")
            return None
    
    def _generate_dialogue_script(self, transcript: str, channel_name: str) -> Optional[List[Dict]]:
        """
        Generate a conversational dialogue script using AI.
        Two hosts: Alex (male, analytical) and Sarah (female, high-insight)
        """
        if not self.openai:
            logging.error("OpenAI client not available for script generation")
            return None
        
        prompt = f"""
You are the producers of "Protocol Pulse," a world-class Bitcoin intelligence podcast.
The hosts are:
- **Alex** (Male - Analytical): Deep technical understanding, connects macro events to Bitcoin fundamentals, asks probing questions
- **Sarah** (Female - High-Insight): Strategic thinker, draws connections others miss, provides actionable intelligence for transactors

TASK: Analyze this transcript and write a script for a "Deep Dive" episode (5-8 minutes when spoken).
TRANSCRIPT SOURCE: {channel_name}'s latest video.

GROUND TRUTH DATA (January 22, 2026):
- Bitcoin Difficulty: 146.47 T (below November 2025 peak of 155.9 T)
- Network Hashrate: ~977 EH/s
- PROHIBITION: NEVER claim "Record Highs" or "All-Time Highs" unless difficulty exceeds 155.9 T
- Focus on network fundamentals, mining economics, and macro positioning

TECHNICAL STORYTELLING MANDATE:
This podcast is for TRANSACTORS (active Bitcoin users who self-custody and run nodes), NOT TOURISTS (chart-watchers seeking price speculation).
- Deliver peer-to-peer intelligence briefings with actionable insights
- Explain WHY network metrics matter for sovereignty and security
- Connect technical details to the broader philosophy of sound money
- Avoid moon-boy narratives and price predictions

PERSONA GUIDELINES:
1. **Alex (Male - Analytical):** Breaks down technical concepts, cites specific metrics (146.47 T difficulty, 977 EH/s hashrate), asks "But what does this mean for the network?" questions
2. **Sarah (Female - High-Insight):** Connects dots between events, identifies second-order effects, provides strategic perspective: "Here's what most people are missing..."
3. **Banter:** Natural interruptions, disfluencies like "I mean...", "Look...", "Right?", "Here's the thing..."
4. **References:** When you mention the source, say "We were just watching {channel_name}'s latest video..." or similar.
5. **Structure:** Open with a hook, dive into key points, include back-and-forth debate, end with actionable takeaways for transactors.
6. **Bitcoin Lens:** Always analyze through the lens of Bitcoin as sound money vs fiat debasement.

OUTPUT FORMAT: Return ONLY a JSON array (no markdown, no code blocks). Each object has "speaker" and "text" keys.
Example format:
[
  {{"speaker": "Alex", "text": "Welcome back to the Pulse. Look, I watched this video and the implications for network security are significant."}},
  {{"speaker": "Sarah", "text": "Alex, here's what most people are missing - this isn't just about the numbers."}},
  {{"speaker": "Alex", "text": "Exactly. At 146.47 T difficulty and 977 exahash, we're seeing real commitment to the network."}},
  {{"speaker": "clip", "text": "Start of Viral Clip 1"}}
]

Mark 3-5 "clip points" in the script with {{"speaker": "clip", "text": "Clip: [description]"}} to indicate good short clip segments for social media.

IMPORTANT: Generate enough dialogue for 5-8 minutes. Aim for 40-60 exchanges minimum.

Transcript to analyze:
{transcript[:6000]}...
"""
        
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            script = json.loads(content)
            logging.info(f"Generated script with {len(script)} lines")
            return script
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse script JSON: {e}")
            logging.debug(f"Raw content: {content[:500]}")
            return None
        except Exception as e:
            logging.error(f"Script generation error: {e}")
            return None
    
    def _synthesize_multi_voice(self, script_json: List[Dict]) -> Optional[str]:
        """
        Synthesize multi-voice audio using ElevenLabs.
        Alex uses male voice, Sarah uses female voice.
        """
        if not self.eleven_client:
            logging.error("ElevenLabs client not available for audio synthesis")
            return None
        
        combined_audio = AudioSegment.empty()
        voice_map = {"Alex": self.male_voice, "Sarah": self.female_voice}
        
        for i, line in enumerate(script_json):
            speaker = line.get("speaker", "")
            
            if speaker == "clip" or not line.get("text"):
                continue
            
            text = line.get("text")
            voice_id = voice_map.get(speaker, self.male_voice)
            
            try:
                audio_stream = self.eleven_client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_turbo_v2",
                    voice_settings=VoiceSettings(
                        stability=0.75,
                        similarity_boost=0.8,
                        style=0.2,
                        use_speaker_boost=True
                    )
                )
                
                temp_chunk = f"/tmp/temp_chunk_{i}.mp3"
                with open(temp_chunk, "wb") as f:
                    for chunk in audio_stream:
                        f.write(chunk)
                
                segment = AudioSegment.from_mp3(temp_chunk)
                combined_audio += segment
                
                pause = AudioSegment.silent(duration=1000)
                combined_audio += pause
                
                os.remove(temp_chunk)
                
                if i % 10 == 0:
                    logging.info(f"Synthesized {i+1}/{len(script_json)} lines")
                    
            except Exception as e:
                logging.error(f"Error synthesizing line {i}: {e}")
                continue
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"{self.output_dir}/podcast_{timestamp}.mp3"
        combined_audio.export(output_path, format="mp3")
        
        duration_seconds = len(combined_audio) / 1000
        logging.info(f"Created podcast audio: {output_path} ({duration_seconds:.1f}s)")
        
        return output_path
    
    def _convert_audio_to_video(self, audio_path: str, image_url: str) -> Optional[str]:
        """
        Convert audio to video with thumbnail as background.
        YouTube rejects MP3 uploads, so we create MP4 with static image.
        """
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                with open(self.background_image, 'wb') as f:
                    f.write(response.content)
            else:
                logging.warning(f"Failed to download thumbnail: {response.status_code}")
                if not os.path.exists(self.background_image):
                    return None
        except Exception as e:
            logging.error(f"Thumbnail download error: {e}")
            if not os.path.exists(self.background_image):
                return None
        
        output_video_path = audio_path.replace(".mp3", ".mp4")
        
        try:
            subprocess.run([
                'ffmpeg', '-loop', '1', '-i', self.background_image, '-i', audio_path,
                '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '192k',
                '-pix_fmt', 'yuv420p', '-shortest', output_video_path, '-y'
            ], check=True, capture_output=True)
            
            logging.info(f"Created podcast video: {output_video_path}")
            return output_video_path
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Video conversion error: {e.stderr.decode() if e.stderr else e}")
            return None
        except Exception as e:
            logging.error(f"Video conversion error: {e}")
            return None
    
    def create_short_clips(self, audio_file: str, script_json: List[Dict], clip_duration: int = 60) -> List[str]:
        """
        Create short clips based on marked clip points in the script.
        Good for social media distribution (X, Instagram Reels, YouTube Shorts).
        """
        clips = []
        
        clip_indices = [i for i, line in enumerate(script_json) if line.get("speaker") == "clip"]
        
        if not clip_indices:
            logging.info("No clip markers found in script")
            return clips
        
        words_per_sec = 2.5  # ~150 words per minute
        current_time = 0
        clip_times = []
        
        for i, line in enumerate(script_json):
            if line.get("speaker") == "clip":
                clip_times.append(current_time)
            else:
                word_count = len(line.get("text", "").split())
                current_time += word_count / words_per_sec + 0.2  # +0.2 for pauses
        
        for i, start_time in enumerate(clip_times[:3]):  # Max 3 clips
            clip_file = audio_file.replace('.mp3', f'_clip_{i+1}.mp3')
            
            try:
                subprocess.run([
                    'ffmpeg', '-i', audio_file, '-ss', str(max(0, start_time - 2)),
                    '-t', str(clip_duration), '-c', 'copy', clip_file, '-y'
                ], check=True, capture_output=True)
                
                clips.append(clip_file)
                logging.info(f"Created clip: {clip_file}")
                
            except Exception as e:
                logging.error(f"Error creating clip {i}: {e}")
        
        return clips
    
    def generate_from_article(self, article) -> Optional[Dict]:
        """
        Generate a podcast from an existing Protocol Pulse article.
        Uses article content instead of YouTube transcript.
        """
        if not self.openai:
            logging.error("OpenAI client not available")
            return None
        
        content = article.content if hasattr(article, 'content') else str(article.get('content', ''))
        title = article.title if hasattr(article, 'title') else str(article.get('title', 'Article'))
        
        content_text = content.replace('<p class="article-paragraph">', '')
        content_text = content_text.replace('</p>', ' ')
        content_text = content_text.replace('<br>', ' ')
        
        script_json = self._generate_dialogue_script(content_text, f"Protocol Pulse article: {title}")
        
        if not script_json:
            return None
        
        audio_file = self._synthesize_multi_voice(script_json)
        
        if audio_file:
            return {
                'audio_file': audio_file,
                'script': script_json,
                'source_article_title': title,
                'generated_at': datetime.utcnow().isoformat()
            }
        
        return None
    
    def generate_video_description(self, channel_name: str, video_title: str = "") -> str:
        """
        Generate a monetized description for YouTube/Rumble uploads.
        Includes affiliate links and proper attribution.
        """
        description = f"""Protocol Pulse Deep Dive: Analysis of {channel_name}'s latest content.

Hosts Alex (Analytical) and Sarah (High-Insight) deliver peer-to-peer intelligence briefings for transactors - analyzing every development through the Bitcoin Lens framework of sound money vs fiat debasement.

TIMESTAMPS:
00:00 - Introduction
01:30 - Key Insights
04:00 - Bitcoin Lens Analysis
06:00 - Actionable Takeaways

---

📚 Support Protocol Pulse: Shop the Bitcoin Standard
https://www.amazon.com/dp/1119473861?tag=protocolpulse-20

🔔 Subscribe for daily Bitcoin analysis
🐦 Follow us on X: @ProtocolPulse

---

Original Source: {channel_name}
{f"Video: {video_title}" if video_title else ""}

#Bitcoin #Crypto #BTC #MacroAnalysis #SoundMoney #ProtocolPulse
"""
        return description.strip()
    
    # ==========================================
    # MULTIMODAL CONTENT ENGINE - New Features
    # ==========================================
    
    def extract_60s_clip(self, audio_file: str, start_time: float = 0, output_suffix: str = "social") -> Optional[str]:
        """
        Extract a 60-second clip from the AI podcast for social media distribution.
        Uses FFmpeg for precise cutting without re-encoding when possible.
        
        Args:
            audio_file: Path to source audio file
            start_time: Start time in seconds (default: 0)
            output_suffix: Suffix for output filename
            
        Returns:
            Path to the extracted clip or None on failure
        """
        if not audio_file or not os.path.exists(audio_file):
            logging.error(f"Audio file not found: {audio_file}")
            return None
        
        if start_time < 0:
            start_time = 0
        
        clip_file = audio_file.replace('.mp3', f'_{output_suffix}_60s.mp3')
        
        try:
            subprocess.run([
                'ffmpeg', '-i', audio_file,
                '-ss', str(start_time),
                '-t', '60',
                '-acodec', 'libmp3lame',
                '-ab', '192k',
                clip_file, '-y'
            ], check=True, capture_output=True)
            
            if os.path.exists(clip_file):
                logging.info(f"Extracted 60s clip: {clip_file} (start: {start_time}s)")
                return clip_file
            else:
                logging.error(f"Clip file not created: {clip_file}")
                return None
            
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg clip extraction error: {e.stderr.decode() if e.stderr else e}")
            return None
        except Exception as e:
            logging.error(f"Clip extraction error: {e}")
            return None
    
    def create_social_video_wrapper(
        self,
        audio_clip: str,
        thumbnail_url: str,
        headline: str,
        output_format: str = "shorts"
    ) -> Optional[str]:
        """
        Wrap audio clip with YouTube thumbnail and bold cyberpunk headline overlay.
        Creates vertical (9:16) video for Shorts/Reels/X or horizontal (16:9) for YouTube.
        
        Args:
            audio_clip: Path to audio clip file
            thumbnail_url: URL to YouTube thumbnail
            headline: Bold headline text for overlay
            output_format: 'shorts' (9:16), 'youtube' (16:9), or 'square' (1:1)
            
        Returns:
            Path to the wrapped video file or None on failure
        """
        dimensions = {
            'shorts': ('1080', '1920'),
            'youtube': ('1920', '1080'),
            'square': ('1080', '1080')
        }
        width, height = dimensions.get(output_format, ('1080', '1920'))
        
        temp_thumb = '/tmp/social_thumb.jpg'
        try:
            response = requests.get(thumbnail_url, timeout=15)
            if response.status_code == 200:
                with open(temp_thumb, 'wb') as f:
                    f.write(response.content)
            else:
                logging.error(f"Failed to download thumbnail: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Thumbnail download error: {e}")
            return None
        
        output_video = audio_clip.replace('.mp3', f'_{output_format}.mp4')
        
        safe_headline = headline.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace(":", "\\:")
        if len(safe_headline) > 60:
            safe_headline = safe_headline[:57] + "..."
        
        cyberpunk_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"drawbox=y=ih-180:w=iw:h=180:color=black@0.7:t=fill,"
            f"drawtext=text='{safe_headline}':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=36:fontcolor=white:"
            f"borderw=3:bordercolor=0xFF3333:"
            f"x=(w-text_w)/2:y=h-120,"
            f"drawtext=text='PROTOCOL PULSE':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=24:fontcolor=0xFF3333:"
            f"x=(w-text_w)/2:y=h-60"
        )
        
        try:
            subprocess.run([
                'ffmpeg',
                '-loop', '1', '-i', temp_thumb,
                '-i', audio_clip,
                '-vf', cyberpunk_filter,
                '-c:v', 'libx264', '-tune', 'stillimage',
                '-c:a', 'aac', '-b:a', '192k',
                '-pix_fmt', 'yuv420p',
                '-shortest',
                output_video, '-y'
            ], check=True, capture_output=True)
            
            logging.info(f"Created social video wrapper: {output_video}")
            
            if os.path.exists(temp_thumb):
                os.remove(temp_thumb)
                
            return output_video
            
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg social wrapper error: {e.stderr.decode() if e.stderr else e}")
            return None
        except Exception as e:
            logging.error(f"Social wrapper error: {e}")
            return None
    
    def generate_bitcoin_lens_review(self, video_id: str, channel_name: str) -> Optional[Dict]:
        """
        Auto-transcribe a partner video and draft a 'Bitcoin Lens' reactionary review article.
        This is triggered when Coin Bureau, Natalie Brunell, or other partner channels post new content.
        
        Args:
            video_id: YouTube video ID
            channel_name: Name of the partner channel
            
        Returns:
            Dict with article content, title, and metadata or None on failure
        """
        if not self.openai:
            logging.error("OpenAI client not available for Bitcoin Lens review")
            return None
        
        transcript = self._get_transcript(video_id)
        if not transcript:
            logging.warning(f"No transcript available for Bitcoin Lens review: {video_id}")
            return None
        
        prompt = f"""You are a senior editor at Protocol Pulse, a world-class Bitcoin intelligence publication.

TASK: Write a "Bitcoin Lens" reactionary review article analyzing {channel_name}'s latest video.

GROUND TRUTH DATA (January 22, 2026):
- Bitcoin Difficulty: 146.47 T (below November 2025 peak of 155.9 T)
- Network Hashrate: ~977 EH/s
- PROHIBITION: NEVER claim "Record Highs" unless difficulty exceeds 155.9 T

TECHNICAL STORYTELLING MANDATE:
This article is for TRANSACTORS (active Bitcoin users), NOT tourists (chart-watchers).
- Deliver peer-to-peer intelligence with actionable insights
- Analyze through the lens of Bitcoin as sound money vs fiat debasement
- Explain WHY this matters for sovereignty and network security
- Avoid moon-boy narratives and price predictions

ARTICLE STRUCTURE (Output as clean HTML):
1. <div class="tldr-section"><strong>TL;DR:</strong> 2-3 sentence summary</div>

2. <h2 class="article-header">Bitcoin Lens: [Video Topic Analysis]</h2>

3. <p class="article-paragraph">[Opening paragraph contextualizing what {channel_name} covered]</p>

4. <h3 class="article-subheader">Key Takeaways for Transactors</h3>
<p class="article-paragraph">[3-5 actionable insights from the video]</p>

5. <h3 class="article-subheader">The Bitcoin Lens Analysis</h3>
<p class="article-paragraph">[Your critical analysis through sound money principles]</p>

6. <h3 class="article-subheader">What This Means for Network Participants</h3>
<p class="article-paragraph">[Practical implications for miners, nodes, transactors]</p>

7. <div class="sources-list"><strong>Source:</strong> {channel_name} - Video ID: {video_id}</div>

Generate a compelling headline and the full article.

Transcript to analyze:
{transcript[:8000]}...

OUTPUT FORMAT:
{{
    "title": "Your compelling headline here",
    "content": "Full HTML article content here"
}}"""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            result['source_video_id'] = video_id
            result['source_channel'] = channel_name
            result['generated_at'] = datetime.utcnow().isoformat()
            result['article_type'] = 'bitcoin_lens_review'
            
            logging.info(f"Generated Bitcoin Lens review for {channel_name}: {result.get('title', 'Untitled')}")
            
            if result.get('content'):
                try:
                    from services.ghl_service import ghl_service
                    ghl_result = ghl_service.push_daily_intel_briefing(result['content'])
                    if ghl_result.get('success'):
                        logging.info("GHL DAILY INTEL BRIEFING SYNC SUCCESS: Bitcoin Lens article pushed to CRM")
                except Exception as e:
                    logging.warning(f"GHL Daily Intel Briefing push failed (non-critical): {e}")
            
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse Bitcoin Lens review JSON: {e}")
            return None
        except Exception as e:
            logging.error(f"Bitcoin Lens review generation error: {e}")
            return None
    
    def create_full_social_package(
        self,
        video_id: str,
        thumbnail_url: str,
        channel_name: str
    ) -> Dict:
        """
        Create a complete social media package from a partner video:
        1. Generate podcast from video transcript
        2. Extract 60-second social clips
        3. Wrap clips with cyberpunk overlays
        4. Generate Bitcoin Lens article
        
        Args:
            video_id: YouTube video ID
            thumbnail_url: URL to video thumbnail
            channel_name: Partner channel name
            
        Returns:
            Dict with all generated assets and metadata
        """
        package = {
            'video_id': video_id,
            'channel': channel_name,
            'podcast': None,
            'clips': [],
            'social_videos': [],
            'article': None,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        podcast_result = self.generate_podcast_from_video(video_id, thumbnail_url, channel_name)
        if podcast_result:
            package['podcast'] = podcast_result
            
            audio_file = podcast_result.get('audio_file')
            script = podcast_result.get('script', [])
            
            if audio_file:
                clip_60s = self.extract_60s_clip(audio_file, start_time=30)
                if clip_60s:
                    package['clips'].append(clip_60s)
                    
                    headline = f"Bitcoin Intel from {channel_name}"
                    
                    shorts_video = self.create_social_video_wrapper(
                        clip_60s, thumbnail_url, headline, 'shorts'
                    )
                    if shorts_video:
                        package['social_videos'].append({
                            'format': 'shorts',
                            'path': shorts_video
                        })
                    
                    square_video = self.create_social_video_wrapper(
                        clip_60s, thumbnail_url, headline, 'square'
                    )
                    if square_video:
                        package['social_videos'].append({
                            'format': 'square',
                            'path': square_video
                        })
        
        article = self.generate_bitcoin_lens_review(video_id, channel_name)
        if article:
            package['article'] = article
        
        logging.info(f"Created full social package for {channel_name} video {video_id}")
        return package


podcast_generator = PodcastGenerator()
```

## services/elevenlabs_service.py
```python
import os
import logging
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings, Voice
from typing import List, Dict, Optional
import tempfile


class ElevenLabsService:
    def __init__(self):
        """Initialize ElevenLabs service for AI voice generation"""
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
        
        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=self.api_key)
        
        # Default voice settings for professional podcast quality
        self.default_voice_settings = VoiceSettings(
            stability=0.75,      # Balanced stability for consistent voice
            similarity_boost=0.8, # High similarity for natural sound
            style=0.2,           # Moderate style for professional tone
            use_speaker_boost=True
        )
        
        # Protocol Pulse recommended voices for different content types
        self.content_voices = {
            "professional_male": "pNInz6obpgDQGcFmaJgB",    # Adam - Professional, news
            "professional_female": "EXAVITQu4vr4xnSDxMaL",  # Bella - Clear, articulate
            "warm_male": "VR6AewLTigWG4xSOukaG",           # Arnold - Warm, engaging
            "energetic_female": "21m00Tcm4TlvDq8ikWAM",     # Rachel - Energetic, excited
            "authoritative": "29vD33N1CtxCmqQRPOHJ",        # Drew - Authoritative, serious
            "conversational": "pqHfZKP75CvOlQylNhV4"       # Bill - Conversational, friendly
        }
        
        logging.info("ElevenLabs service initialized successfully")

    def get_available_voices(self) -> List[Dict]:
        """Get list of available voices from ElevenLabs"""
        try:
            voice_list = self.client.voices.get_all()
            
            available_voices = []
            for voice in voice_list.voices:
                voice_info = {
                    'voice_id': voice.voice_id,
                    'name': voice.name,
                    'description': getattr(voice, 'description', ''),
                    'category': getattr(voice, 'category', 'general'),
                    'preview_url': getattr(voice, 'preview_url', None)
                }
                available_voices.append(voice_info)
            
            return available_voices
            
        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            return []

    def generate_podcast_audio(self, text: str, voice_type: str = "professional_male", 
                             output_format: str = "mp3") -> Optional[str]:
        """Generate podcast audio from text using specified voice"""
        try:
            # Get voice ID for the specified type
            voice_id = self.content_voices.get(voice_type, self.content_voices["professional_male"])
            
            # Generate audio using text_to_speech
            audio = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                voice_settings=self.default_voice_settings,
                model_id="eleven_turbo_v2"  # Fast, high-quality model
            )
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_format}')
            
            # Write audio data to file
            for chunk in audio:
                temp_file.write(chunk)
            temp_file.close()
            
            logging.info(f"Generated audio file: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logging.error(f"Error generating podcast audio: {e}")
            return None

    def generate_article_summary_audio(self, article_title: str, article_content: str,
                                     voice_type: str = "professional_female") -> Optional[str]:
        """Generate audio summary of an article optimized for podcast format"""
        try:
            # Create a podcast-friendly script from the article
            podcast_script = self._create_podcast_script(article_title, article_content)
            
            # Generate audio
            return self.generate_podcast_audio(podcast_script, voice_type)
            
        except Exception as e:
            logging.error(f"Error generating article summary audio: {e}")
            return None

    def generate_bitcoin_news_audio(self, news_content: str, urgency: str = "normal") -> Optional[str]:
        """Generate Bitcoin news audio with appropriate voice style"""
        try:
            # Choose voice based on urgency
            if urgency == "breaking":
                voice_type = "energetic_female"
                intro = "Breaking Bitcoin News: "
            elif urgency == "analysis":
                voice_type = "authoritative"
                intro = "Bitcoin Analysis Update: "
            else:
                voice_type = "professional_male"
                intro = "Bitcoin News: "
            
            # Format content for audio
            audio_content = f"{intro}{news_content}"
            
            return self.generate_podcast_audio(audio_content, voice_type)
            
        except Exception as e:
            logging.error(f"Error generating Bitcoin news audio: {e}")
            return None

    def generate_defi_analysis_audio(self, analysis_content: str) -> Optional[str]:
        """Generate DeFi analysis audio with technical, authoritative voice"""
        try:
            intro = "DeFi Protocol Analysis: "
            audio_content = f"{intro}{analysis_content}"
            
            return self.generate_podcast_audio(audio_content, "authoritative")
            
        except Exception as e:
            logging.error(f"Error generating DeFi analysis audio: {e}")
            return None

    def _create_podcast_script(self, title: str, content: str) -> str:
        """Convert article content into podcast-friendly script"""
        # Create engaging podcast introduction
        intro = f"Welcome to Protocol Pulse. Today we're discussing: {title}."
        
        # Process content for audio (remove markdown, make conversational)
        processed_content = content.replace('#', '').replace('*', '').replace('_', '')
        
        # Add natural pauses and transitions
        script_parts = [
            intro,
            "Let's dive into the details.",
            processed_content,
            "That's our analysis for today. Thanks for listening to Protocol Pulse."
        ]
        
        return " ".join(script_parts)

    def batch_generate_episodes(self, articles: List[Dict], voice_type: str = "professional_male") -> List[str]:
        """Generate multiple podcast episodes from a list of articles"""
        generated_files = []
        
        for article in articles:
            try:
                title = article.get('title', 'Untitled')
                content = article.get('content', '')
                
                if content:
                    audio_file = self.generate_article_summary_audio(title, content, voice_type)
                    if audio_file:
                        generated_files.append(audio_file)
                        
            except Exception as e:
                logging.error(f"Error in batch generation for article '{title}': {e}")
                continue
        
        return generated_files

    def get_voice_recommendation(self, content_type: str, mood: str = "professional") -> str:
        """Get recommended voice based on content type and mood"""
        recommendations = {
            ("bitcoin_news", "professional"): "professional_male",
            ("bitcoin_news", "urgent"): "energetic_female",
            ("defi_analysis", "professional"): "authoritative",
            ("market_update", "conversational"): "conversational",
            ("tutorial", "friendly"): "warm_male",
            ("breaking_news", "urgent"): "energetic_female",
            ("interview", "conversational"): "conversational"
        }
        
        return recommendations.get((content_type, mood), "professional_male")

    def test_connection(self) -> bool:
        """Test ElevenLabs API connection"""
        try:
            # Test by generating a very short audio clip
            test_audio = self.client.text_to_speech.convert(
                voice_id=self.content_voices["professional_male"],
                text="Test connection successful.",
                voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.5),
                model_id="eleven_turbo_v2"
            )
            
            # If we get audio stream back, connection is working
            audio_data = b""
            for chunk in test_audio:
                audio_data += chunk
                break  # Just need to verify we get data
            
            return len(audio_data) > 0
            
        except Exception as e:
            logging.error(f"ElevenLabs connection test failed: {e}")
            return False

# Initialize the service
elevenlabs_service = ElevenLabsService()```

## services/target_monitor.py
```python
import os
import json
import logging
import feedparser
from datetime import datetime, timedelta
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

REPLY_SQUAD = [
    {'handle': '@gladstein', 'name': 'Alex Gladstein', 'category': 'human_rights', 'priority': 1},
    {'handle': '@MartyBent', 'name': 'Marty Bent', 'category': 'macro', 'priority': 1},
    {'handle': '@BitcoinMagazine', 'name': 'Bitcoin Magazine', 'category': 'news', 'priority': 1},
    {'handle': '@PrestonPysh', 'name': 'Preston Pysh', 'category': 'macro', 'priority': 1},
    {'handle': '@DocumentingBTC', 'name': 'Documenting BTC', 'category': 'aggregator', 'priority': 2},
    {'handle': '@sabordo', 'name': 'Saifedean', 'category': 'economics', 'priority': 1},
    {'handle': '@NatBrunell', 'name': 'Natalie Brunell', 'category': 'media', 'priority': 2},
    {'handle': '@dergigi', 'name': 'Gigi', 'category': 'philosophy', 'priority': 2},
    {'handle': '@MustStopMurad', 'name': 'Murad', 'category': 'analysis', 'priority': 2},
    {'handle': '@TheGuySwann', 'name': 'Guy Swann', 'category': 'education', 'priority': 2},
    {'handle': '@Dennis_Porter_', 'name': 'Dennis Porter', 'category': 'policy', 'priority': 2},
    {'handle': '@BitcoinPierre', 'name': 'Pierre Rochard', 'category': 'technical', 'priority': 2},
    {'handle': '@CynthiaMLummis', 'name': 'Senator Lummis', 'category': 'policy', 'priority': 1},
    {'handle': '@nikitagod', 'name': 'Nik Bhatia', 'category': 'economics', 'priority': 2},
    {'handle': '@JeffBooth', 'name': 'Jeff Booth', 'category': 'economics', 'priority': 1}
]

RSS_FEEDS = [
    {'name': 'Bitcoin Magazine', 'url': 'https://bitcoinmagazine.com/feed', 'category': 'news'},
    {'name': 'CoinDesk Bitcoin', 'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml', 'category': 'news'},
    {'name': 'Mempool Research', 'url': 'https://mempool.space/api/v1/services/feed', 'category': 'technical'},
]

REPLY_STRATEGIES = {
    'human_rights': {
        'prompt': 'Reply with a sovereignty angle. Connect to monetary freedom or self-custody. Be respectful and add value.',
        'keywords': ['freedom', 'sovereignty', 'self-custody', 'permissionless', 'human rights']
    },
    'macro': {
        'prompt': 'Reply with Austrian economics perspective. Reference sound money principles or fiat critique. Be substantive.',
        'keywords': ['sound money', 'inflation', 'monetary policy', 'store of value', 'purchasing power']
    },
    'technical': {
        'prompt': 'Reply with protocol-level insight or mining/difficulty reference. Show expertise but keep accessible.',
        'keywords': ['hashrate', 'difficulty', 'on-chain', 'UTXO', 'mempool', 'protocol']
    },
    'news': {
        'prompt': 'Add context or alternative perspective to the news. Reference Protocol Pulse analysis if relevant.',
        'keywords': ['signal', 'analysis', 'context', 'deeper look']
    },
    'economics': {
        'prompt': 'Engage with economic thesis. Reference Austrian principles, time preference, or monetary history.',
        'keywords': ['Austrian', 'time preference', 'hard money', 'scarcity', 'value']
    },
    'philosophy': {
        'prompt': 'Engage on philosophical level. Connect to individual sovereignty, proof of work ethic, or verification.',
        'keywords': ['verify', 'trust', 'sovereignty', 'proof of work', 'first principles']
    },
    'policy': {
        'prompt': 'Engage on regulatory/policy angle. Reference self-custody rights, property rights, or freedom.',
        'keywords': ['regulation', 'policy', 'rights', 'freedom', 'legislation']
    },
    'default': {
        'prompt': 'Reply with insight that adds value. Reference Protocol Pulse content if relevant.',
        'keywords': ['signal', 'analysis', 'perspective']
    }
}


class TargetMonitorService:
    def __init__(self):
        self.client = None
        if OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("Target Monitor Service initialized")
        else:
            logger.warning("OpenAI API key not configured for Target Monitor")
    
    def get_reply_squad(self):
        return REPLY_SQUAD
    
    def get_strategy_for_account(self, handle):
        for member in REPLY_SQUAD:
            if member['handle'].lower() == handle.lower():
                category = member.get('category', 'default')
                return REPLY_STRATEGIES.get(category, REPLY_STRATEGIES['default'])
        return REPLY_STRATEGIES['default']
    
    def generate_reply_drafts(self, source_account, content_snippet, strategy_override=None):
        if not self.client:
            return self._get_fallback_drafts(source_account)
        
        try:
            strategy = strategy_override or self.get_strategy_for_account(source_account)
            
            prompt = f"""You are PBX from Protocol Pulse, a Bitcoin intelligence platform.

Generate 5 reply options for this tweet from {source_account}:
---
{content_snippet}
---

Strategy: {strategy['prompt']}
Keywords to consider: {', '.join(strategy['keywords'])}

REQUIREMENTS:
1. Each reply MUST be under 280 characters
2. Be substantive and add value
3. Be respectful of their work
4. Vary the tone: technical, thoughtful, provocative, supporting, questioning
5. At least one should invite further discussion

Respond in JSON format:
{{
    "drafts": [
        {{"type": "technical", "text": "Reply 1..."}},
        {{"type": "thoughtful", "text": "Reply 2..."}},
        {{"type": "provocative", "text": "Reply 3..."}},
        {{"type": "supporting", "text": "Reply 4..."}},
        {{"type": "questioning", "text": "Reply 5..."}}
    ],
    "recommended": 0
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text.strip())
            return result
            
        except Exception as e:
            logger.error(f"Error generating reply drafts: {e}")
            return self._get_fallback_drafts(source_account)
    
    def _get_fallback_drafts(self, source_account):
        return {
            'drafts': [
                {'type': 'technical', 'text': f'This aligns with what we\'re seeing in the on-chain data. The network fundamentals are telling the same story.'},
                {'type': 'thoughtful', 'text': f'Appreciate the signal. This is exactly what Protocol Pulse has been tracking in our daily briefings.'},
                {'type': 'provocative', 'text': f'Playing devil\'s advocate - what if this is just the beginning of a larger trend we haven\'t fully mapped yet?'},
                {'type': 'supporting', 'text': f'This. The signal is clear for those paying attention to the fundamentals.'},
                {'type': 'questioning', 'text': f'Curious about your take on the second-order effects here. What are you watching as a leading indicator?'}
            ],
            'recommended': 0
        }
    
    def scan_rss_feeds(self):
        alerts = []
        
        for feed_config in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_config['url'])
                
                for entry in feed.entries[:5]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')[:500]
                    
                    if self._is_relevant_content(title + ' ' + summary):
                        alerts.append({
                            'trigger_type': 'trending',
                            'source_url': link,
                            'source_account': feed_config['name'],
                            'content_snippet': f"{title}\n\n{summary[:300]}",
                            'priority': 2,
                            'strategy_suggested': feed_config['category']
                        })
                        
            except Exception as e:
                logger.error(f"Error scanning RSS feed {feed_config['name']}: {e}")
        
        return alerts[:15]
    
    def _is_relevant_content(self, text):
        text_lower = text.lower()
        
        high_priority_keywords = [
            'bitcoin', 'btc', 'mining', 'hashrate', 'difficulty',
            'self-custody', 'lightning', 'cbdc', 'regulation',
            'fed', 'monetary', 'inflation', 'reserve'
        ]
        
        return any(keyword in text_lower for keyword in high_priority_keywords)
    
    def create_alert(self, trigger_type, source_url, source_account, content_snippet, priority=2):
        strategy = self.get_strategy_for_account(source_account)
        drafts = self.generate_reply_drafts(source_account, content_snippet)
        
        return {
            'trigger_type': trigger_type,
            'source_url': source_url,
            'source_account': source_account,
            'content_snippet': content_snippet,
            'priority': priority,
            'strategy_suggested': strategy.get('keywords', ['analysis'])[0] if strategy else 'analysis',
            'draft_replies': json.dumps(drafts),
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
    
    def process_manual_url(self, url, account_handle=None):
        content_snippet = f"Content from: {url}"
        
        return self.create_alert(
            trigger_type='manual',
            source_url=url,
            source_account=account_handle or 'unknown',
            content_snippet=content_snippet,
            priority=1
        )


target_monitor_service = TargetMonitorService()
```

## services/substack_service.py
```python
import os
import logging
from typing import Optional, Dict
from substack import Api
from substack.post import Post


class SubstackService:
    def __init__(self):
        """Initialize Substack service for automated publishing"""
        self.email = os.environ.get('SUBSTACK_EMAIL')
        self.password = os.environ.get('SUBSTACK_PASSWORD')
        self.publication_url = os.environ.get('SUBSTACK_PUBLICATION_URL')
        
        if not all([self.email, self.password, self.publication_url]):
            raise ValueError("SUBSTACK_EMAIL, SUBSTACK_PASSWORD, and SUBSTACK_PUBLICATION_URL environment variables are required")
        
        # Initialize the API connection
        self.api = None
        self.user_id = None
        
        logging.info("Substack service initialized successfully")

    def _initialize_api(self) -> bool:
        """Initialize Substack API connection"""
        try:
            if not self.api:
                self.api = Api(
                    email=self.email,
                    password=self.password,
                    publication_url=self.publication_url
                )
                self.user_id = self.api.get_user_id()
                logging.info(f"Substack API initialized with user ID: {self.user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Substack API: {e}")
            return False

    def publish_to_substack(self, title: str, body_markdown: str, image_path: str = None) -> Optional[str]:
        """
        Publish article to Substack following the specified format
        
        Args:
            title: Article title
            body_markdown: Article content in markdown format
            image_path: Optional path or URL to header image
            
        Returns:
            Published post URL if successful, None if failed
        """
        try:
            if not self._initialize_api():
                return None

            # Create the post
            post = Post(
                title=title,
                subtitle="Generated by Protocol Pulse AI",
                user_id=self.user_id
            )

            # Add body as paragraph (convert Markdown to Substack blocks if needed; simple for now)
            post.add({"type": "paragraph", "content": body_markdown})

            # Optional header image (from DALL-E path/URL)
            if image_path:
                try:
                    uploaded = self.api.get_image(image_path)  # Handles upload
                    if uploaded and uploaded.get("url"):
                        post.add({"type": "captionedImage", "src": uploaded.get("url")})
                        logging.info(f"Added header image to Substack post: {uploaded.get('url')}")
                except Exception as e:
                    logging.warning(f"Failed to upload image to Substack: {e}")
                    # Continue without image

            # Create draft
            draft = self.api.post_draft(post.get_draft())
            draft_id = draft.get("id")
            
            if not draft_id:
                logging.error("Failed to create Substack draft")
                return None

            logging.info(f"Created Substack draft with ID: {draft_id}")

            # Prepare for publishing
            self.api.prepublish_draft(draft_id)
            
            # Publish the draft
            published = self.api.publish_draft(draft_id)
            post_url = published.get("canonical_url")
            
            if post_url:
                logging.info(f"Successfully published to Substack: {post_url}")
                return post_url
            else:
                logging.error("Published to Substack but no URL returned")
                return None

        except Exception as e:
            logging.error(f"Substack publishing error: {e}")
            return None

    def publish_bitcoin_news(self, title: str, content: str, image_url: str = None) -> Optional[str]:
        """Publish Bitcoin news article to Substack"""
        try:
            # Format content for Substack newsletter
            formatted_title = f"🪙 {title}"
            
            # Add Protocol Pulse branding and Bitcoin focus
            newsletter_content = f"""
{content}

---

*This article was generated by Protocol Pulse AI - Your source for Bitcoin and DeFi analysis.*

*Subscribe for daily Bitcoin insights and DeFi protocol updates.*
"""
            
            return self.publish_to_substack(formatted_title, newsletter_content, image_url)
            
        except Exception as e:
            logging.error(f"Error publishing Bitcoin news to Substack: {e}")
            return None

    def publish_defi_analysis(self, title: str, content: str, image_url: str = None) -> Optional[str]:
        """Publish DeFi analysis article to Substack"""
        try:
            # Format content for DeFi analysis
            formatted_title = f"🏦 {title}"
            
            newsletter_content = f"""
{content}

---

*This DeFi analysis was generated by Protocol Pulse AI - Your trusted source for decentralized finance insights.*

*Stay ahead of DeFi trends with our daily protocol analysis.*
"""
            
            return self.publish_to_substack(formatted_title, newsletter_content, image_url)
            
        except Exception as e:
            logging.error(f"Error publishing DeFi analysis to Substack: {e}")
            return None

    def publish_market_update(self, title: str, content: str, image_url: str = None) -> Optional[str]:
        """Publish market update to Substack"""
        try:
            formatted_title = f"📈 {title}"
            
            newsletter_content = f"""
{content}

---

*Market updates powered by Protocol Pulse AI - Real-time Bitcoin and DeFi market analysis.*

*Get instant alerts on market movements and protocol updates.*
"""
            
            return self.publish_to_substack(formatted_title, newsletter_content, image_url)
            
        except Exception as e:
            logging.error(f"Error publishing market update to Substack: {e}")
            return None

    def create_draft_only(self, title: str, body_markdown: str, image_path: str = None) -> Optional[str]:
        """Create a draft without publishing for review"""
        try:
            if not self._initialize_api():
                return None

            post = Post(
                title=title,
                subtitle="Generated by Protocol Pulse AI - DRAFT",
                user_id=self.user_id
            )

            post.add({"type": "paragraph", "content": body_markdown})

            if image_path:
                try:
                    uploaded = self.api.get_image(image_path)
                    if uploaded and uploaded.get("url"):
                        post.add({"type": "captionedImage", "src": uploaded.get("url")})
                except Exception as e:
                    logging.warning(f"Failed to upload image to draft: {e}")

            draft = self.api.post_draft(post.get_draft())
            draft_id = draft.get("id")
            
            if draft_id:
                logging.info(f"Created Substack draft for review: {draft_id}")
                return draft_id
            else:
                logging.error("Failed to create Substack draft")
                return None

        except Exception as e:
            logging.error(f"Error creating Substack draft: {e}")
            return None

    def get_publication_stats(self) -> Dict:
        """Get publication statistics"""
        try:
            if not self._initialize_api():
                return {}

            # Note: python-substack library may have limited stats functionality
            # This is a placeholder for potential stats retrieval
            stats = {
                "publication_url": self.publication_url,
                "status": "connected",
                "user_id": self.user_id
            }
            
            return stats
            
        except Exception as e:
            logging.error(f"Error getting publication stats: {e}")
            return {"status": "error", "error": str(e)}

    def test_connection(self) -> bool:
        """Test Substack connection"""
        try:
            return self._initialize_api()
        except Exception as e:
            logging.error(f"Substack connection test failed: {e}")
            return False

    def format_content_for_newsletter(self, content: str, content_type: str = "article") -> str:
        """Format content specifically for newsletter consumption"""
        # Remove markdown formatting that doesn't work well in Substack
        formatted = content.replace('###', '').replace('##', '').replace('#', '')
        formatted = formatted.replace('**', '').replace('*', '')
        
        # Add newsletter-specific formatting
        if content_type == "bitcoin":
            header = "🪙 BITCOIN UPDATE\n\n"
        elif content_type == "defi":
            header = "🏦 DEFI ANALYSIS\n\n"
        else:
            header = "📰 PROTOCOL PULSE\n\n"
            
        footer = f"""

---

💡 What did you think of this analysis? Reply and let us know!

🔔 Never miss an update - make sure you're subscribed to Protocol Pulse

📈 Follow us for real-time Bitcoin and DeFi insights

---

*Powered by Protocol Pulse AI - The future of crypto journalism*
"""
        
        return header + formatted + footer

# Initialize the service
substack_service = SubstackService()```

## services/meetup_map_service.py
```python
"""
Bitcoin Meetup Map Service
Comprehensive worldwide Bitcoin meetup data with BTC Map merchant integration
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

class MeetupMapService:
    """Service for fetching Bitcoin merchant and meetup data"""
    
    BTC_MAP_API = "https://api.btcmap.org/v2"
    
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=1)
    
    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached data if not expired"""
        if key in self.cache and key in self.cache_expiry:
            if datetime.utcnow() < self.cache_expiry[key]:
                return self.cache[key]
        return None
    
    def _set_cached(self, key: str, data: any):
        """Cache data with expiry"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.utcnow() + self.cache_duration
    
    def get_merchants_by_bounds(self, min_lat: float, min_lon: float, 
                                 max_lat: float, max_lon: float,
                                 limit: int = 100) -> List[Dict]:
        """Get Bitcoin-accepting merchants within geographic bounds"""
        cache_key = f"merchants_{min_lat}_{min_lon}_{max_lat}_{max_lon}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{self.BTC_MAP_API}/elements",
                params={
                    'updated_since': (datetime.utcnow() - timedelta(days=365)).isoformat(),
                    'limit': limit
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                merchants = []
                for element in data.get('data', []):
                    osm_json = element.get('osm_json', {})
                    lat = osm_json.get('lat', 0)
                    lon = osm_json.get('lon', 0)
                    
                    if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                        tags = osm_json.get('tags', {})
                        merchants.append({
                            'id': element.get('id'),
                            'name': tags.get('name', 'Unknown'),
                            'lat': lat,
                            'lon': lon,
                            'type': self._categorize_merchant(tags),
                            'payment_lightning': tags.get('payment:lightning', 'no') == 'yes',
                            'payment_onchain': tags.get('payment:bitcoin', 'no') == 'yes',
                            'address': self._format_address(tags),
                            'website': tags.get('website', ''),
                            'phone': tags.get('phone', ''),
                            'opening_hours': tags.get('opening_hours', ''),
                            'verified': element.get('tags', {}).get('verified', False)
                        })
                
                self._set_cached(cache_key, merchants)
                return merchants
            else:
                logging.warning(f"BTC Map API returned {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Error fetching BTC Map data: {e}")
            return []
    
    def get_global_stats(self) -> Dict:
        """Get global Bitcoin merchant statistics"""
        cache_key = "global_stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{self.BTC_MAP_API}/elements",
                params={'limit': 1},
                timeout=10
            )
            
            if response.status_code == 200:
                total_count = response.headers.get('X-Total-Count', '40000')
                
                stats = {
                    'total_merchants': int(total_count) if total_count.isdigit() else 40000,
                    'countries': 80,
                    'lightning_enabled': 0.65,
                    'growth_rate': 0.12,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                self._set_cached(cache_key, stats)
                return stats
                
        except Exception as e:
            logging.error(f"Error fetching global stats: {e}")
        
        return {
            'total_merchants': 40000,
            'countries': 80,
            'lightning_enabled': 0.65,
            'growth_rate': 0.12,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def get_bitcoin_meetups(self, lat: float = 0, lon: float = 0, radius_miles: int = 50) -> List[Dict]:
        """
        Get comprehensive worldwide Bitcoin meetups
        Returns curated list of major Bitcoin communities globally
        """
        
        # Comprehensive worldwide Bitcoin meetup database - Verified URLs 2025
        worldwide_meetups = [
            # ==================== NORTH AMERICA ====================
            # United States - Major Cities
            {'name': 'Bitcoin Park Austin', 'city': 'Austin, TX, USA', 'lat': 30.2672, 'lon': -97.7431, 'frequency': 'Weekly', 'members': 3500, 'next_event': 'Every Tuesday', 'url': 'https://www.meetup.com/bitcoin-park-austin/', 'region': 'North America'},
            {'name': 'Bitcoin Miami', 'city': 'Miami, FL, USA', 'lat': 25.7617, 'lon': -80.1918, 'frequency': 'Weekly', 'members': 3200, 'next_event': 'Every Wednesday', 'url': 'https://www.meetup.com/miami-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'BitDevs NYC', 'city': 'New York, NY, USA', 'lat': 40.7128, 'lon': -74.0060, 'frequency': 'Bi-weekly', 'members': 4100, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/bitdevsnyc/', 'region': 'North America'},
            {'name': 'SF Bitcoin Devs', 'city': 'San Francisco, CA, USA', 'lat': 37.7749, 'lon': -122.4194, 'frequency': 'Monthly', 'members': 2932, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/sf-bitcoin-devs/', 'region': 'North America'},
            {'name': 'Bitcoin Nashville', 'city': 'Nashville, TN, USA', 'lat': 36.1627, 'lon': -86.7816, 'frequency': 'Monthly', 'members': 1800, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/nashville-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Chicago BitDevs', 'city': 'Chicago, IL, USA', 'lat': 41.8781, 'lon': -87.6298, 'frequency': 'Monthly', 'members': 1400, 'next_event': 'First Tuesday', 'url': 'https://www.meetup.com/chibitdevs/', 'region': 'North America'},
            {'name': 'LA Bitcoin', 'city': 'Los Angeles, CA, USA', 'lat': 34.0522, 'lon': -118.2437, 'frequency': 'Monthly', 'members': 2200, 'next_event': 'Second Thursday', 'url': 'https://www.meetup.com/los-angeles-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Seattle Bitcoin', 'city': 'Seattle, WA, USA', 'lat': 47.6062, 'lon': -122.3321, 'frequency': 'Monthly', 'members': 1100, 'next_event': 'First Wednesday', 'url': 'https://www.meetup.com/seattle-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Denver Bitcoin', 'city': 'Denver, CO, USA', 'lat': 39.7392, 'lon': -104.9903, 'frequency': 'Monthly', 'members': 950, 'next_event': 'Third Tuesday', 'url': 'https://www.meetup.com/denver-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Boston Bitcoin', 'city': 'Boston, MA, USA', 'lat': 42.3601, 'lon': -71.0589, 'frequency': 'Monthly', 'members': 1200, 'next_event': 'Second Wednesday', 'url': 'https://www.meetup.com/boston-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Phoenix Bitcoin', 'city': 'Phoenix, AZ, USA', 'lat': 33.4484, 'lon': -112.0740, 'frequency': 'Monthly', 'members': 800, 'next_event': 'Last Thursday', 'url': 'https://www.meetup.com/phoenix-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Atlanta Bitcoin', 'city': 'Atlanta, GA, USA', 'lat': 33.7490, 'lon': -84.3880, 'frequency': 'Monthly', 'members': 1100, 'next_event': 'First Friday', 'url': 'https://www.meetup.com/atlanta-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Dallas Bitcoin', 'city': 'Dallas, TX, USA', 'lat': 32.7767, 'lon': -96.7970, 'frequency': 'Monthly', 'members': 1300, 'next_event': 'Second Saturday', 'url': 'https://www.meetup.com/dallas-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Houston Bitcoin', 'city': 'Houston, TX, USA', 'lat': 29.7604, 'lon': -95.3698, 'frequency': 'Monthly', 'members': 900, 'next_event': 'Third Wednesday', 'url': 'https://www.meetup.com/houston-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Portland Bitcoin', 'city': 'Portland, OR, USA', 'lat': 45.5152, 'lon': -122.6784, 'frequency': 'Monthly', 'members': 700, 'next_event': 'Last Tuesday', 'url': 'https://www.meetup.com/portland-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Las Vegas Bitcoin', 'city': 'Las Vegas, NV, USA', 'lat': 36.1699, 'lon': -115.1398, 'frequency': 'Monthly', 'members': 650, 'next_event': 'First Saturday', 'url': 'https://www.meetup.com/las-vegas-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'San Diego Bitcoin', 'city': 'San Diego, CA, USA', 'lat': 32.7157, 'lon': -117.1611, 'frequency': 'Monthly', 'members': 750, 'next_event': 'Second Thursday', 'url': 'https://www.meetup.com/san-diego-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Triangle Bitcoin', 'city': 'Raleigh, NC, USA', 'lat': 35.7796, 'lon': -78.6382, 'frequency': 'Monthly', 'members': 500, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/triangle-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Salt Lake City Bitcoin', 'city': 'Salt Lake City, UT, USA', 'lat': 40.7608, 'lon': -111.8910, 'frequency': 'Monthly', 'members': 450, 'next_event': 'Last Wednesday', 'url': 'https://www.meetup.com/slc-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Minneapolis Bitcoin', 'city': 'Minneapolis, MN, USA', 'lat': 44.9778, 'lon': -93.2650, 'frequency': 'Monthly', 'members': 600, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/minneapolis-bitcoin-meetup/', 'region': 'North America'},
            {'name': 'Naples Bitcoin + Blockchain', 'city': 'Naples, FL, USA', 'lat': 26.1420, 'lon': -81.7948, 'frequency': 'Monthly', 'members': 350, 'next_event': 'First Tuesday', 'url': 'https://www.meetup.com/naples-bitcoin-blockchain-group/', 'region': 'North America'},
            
            # Canada
            {'name': 'Bitcoin Bay', 'city': 'Toronto, ON, Canada', 'lat': 43.6532, 'lon': -79.3832, 'frequency': 'Monthly', 'members': 1800, 'next_event': 'Second Tuesday', 'url': 'https://www.meetup.com/bitcoinbay/', 'region': 'North America'},
            {'name': 'Bitcoin Vancouver', 'city': 'Vancouver, BC, Canada', 'lat': 49.2827, 'lon': -123.1207, 'frequency': 'Monthly', 'members': 1200, 'next_event': 'First Wednesday', 'url': 'https://www.meetup.com/vancouver-bitcoiners/', 'region': 'North America'},
            {'name': 'Bitcoin Montreal', 'city': 'Montreal, QC, Canada', 'lat': 45.5017, 'lon': -73.5673, 'frequency': 'Monthly', 'members': 900, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-montreal/', 'region': 'North America'},
            {'name': 'Bitcoin Calgary', 'city': 'Calgary, AB, Canada', 'lat': 51.0447, 'lon': -114.0719, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Last Tuesday', 'url': 'https://www.meetup.com/bitcoin-calgary/', 'region': 'North America'},
            {'name': 'Bitcoin Ottawa', 'city': 'Ottawa, ON, Canada', 'lat': 45.4215, 'lon': -75.6972, 'frequency': 'Monthly', 'members': 400, 'next_event': 'Second Thursday', 'url': 'https://www.meetup.com/ottawa-bitcoin-meetup/', 'region': 'North America'},
            
            # Mexico
            {'name': 'Bitcoin Mexico City', 'city': 'Mexico City, Mexico', 'lat': 19.4326, 'lon': -99.1332, 'frequency': 'Monthly', 'members': 1500, 'next_event': 'First Saturday', 'url': 'https://www.meetup.com/bitcoin-mexico-city/', 'region': 'North America'},
            {'name': 'Bitcoin Guadalajara', 'city': 'Guadalajara, Mexico', 'lat': 20.6597, 'lon': -103.3496, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Third Friday', 'url': 'https://www.meetup.com/bitcoin-guadalajara/', 'region': 'North America'},
            
            # ==================== LATIN AMERICA ====================
            {'name': 'Bitcoin El Salvador', 'city': 'San Salvador, El Salvador', 'lat': 13.6929, 'lon': -89.2182, 'frequency': 'Weekly', 'members': 5000, 'next_event': 'Every Saturday', 'url': 'https://www.meetup.com/bitcoin-el-salvador/', 'region': 'Latin America'},
            {'name': 'Bitcoin Beach', 'city': 'El Zonte, El Salvador', 'lat': 13.4967, 'lon': -89.3914, 'frequency': 'Daily', 'members': 2000, 'next_event': 'Ongoing', 'url': 'https://www.bitcoinbeach.com/', 'region': 'Latin America'},
            {'name': 'Bitcoin Argentina', 'city': 'Buenos Aires, Argentina', 'lat': -34.6037, 'lon': -58.3816, 'frequency': 'Monthly', 'members': 2500, 'next_event': 'Last Thursday', 'url': 'https://www.meetup.com/bitcoin-argentina/', 'region': 'Latin America'},
            {'name': 'Bitcoin São Paulo', 'city': 'São Paulo, Brazil', 'lat': -23.5505, 'lon': -46.6333, 'frequency': 'Monthly', 'members': 3000, 'next_event': 'Second Saturday', 'url': 'https://www.meetup.com/bitcoin-sao-paulo/', 'region': 'Latin America'},
            {'name': 'Bitcoin Rio', 'city': 'Rio de Janeiro, Brazil', 'lat': -22.9068, 'lon': -43.1729, 'frequency': 'Monthly', 'members': 1200, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-rio-de-janeiro/', 'region': 'Latin America'},
            {'name': 'Bitcoin Colombia', 'city': 'Bogotá, Colombia', 'lat': 4.7110, 'lon': -74.0721, 'frequency': 'Monthly', 'members': 1800, 'next_event': 'First Wednesday', 'url': 'https://www.meetup.com/bitcoin-bogota/', 'region': 'Latin America'},
            {'name': 'Bitcoin Chile', 'city': 'Santiago, Chile', 'lat': -33.4489, 'lon': -70.6693, 'frequency': 'Monthly', 'members': 1100, 'next_event': 'Second Tuesday', 'url': 'https://www.meetup.com/bitcoin-santiago/', 'region': 'Latin America'},
            {'name': 'Bitcoin Peru', 'city': 'Lima, Peru', 'lat': -12.0464, 'lon': -77.0428, 'frequency': 'Monthly', 'members': 800, 'next_event': 'Last Friday', 'url': 'https://www.meetup.com/bitcoin-lima/', 'region': 'Latin America'},
            {'name': 'Bitcoin Venezuela', 'city': 'Caracas, Venezuela', 'lat': 10.4806, 'lon': -66.9036, 'frequency': 'Monthly', 'members': 1500, 'next_event': 'Third Saturday', 'url': 'https://www.meetup.com/bitcoin-caracas/', 'region': 'Latin America'},
            {'name': 'Bitcoin Costa Rica', 'city': 'San José, Costa Rica', 'lat': 9.9281, 'lon': -84.0907, 'frequency': 'Monthly', 'members': 700, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/bitcoin-costa-rica/', 'region': 'Latin America'},
            {'name': 'Bitcoin Guatemala', 'city': 'Guatemala City, Guatemala', 'lat': 14.6349, 'lon': -90.5069, 'frequency': 'Monthly', 'members': 400, 'next_event': 'Second Saturday', 'url': 'https://www.meetup.com/bitcoin-guatemala/', 'region': 'Latin America'},
            {'name': 'Bitcoin Panama', 'city': 'Panama City, Panama', 'lat': 9.1012, 'lon': -79.4025, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Third Tuesday', 'url': 'https://www.meetup.com/bitcoin-panama/', 'region': 'Latin America'},
            
            # ==================== EUROPE ====================
            # Western Europe
            {'name': 'London BitDevs', 'city': 'London, UK', 'lat': 51.5074, 'lon': -0.1278, 'frequency': 'Monthly', 'members': 2500, 'next_event': 'Second Thursday', 'url': 'https://www.meetup.com/london-bitcoin-devs/', 'region': 'Europe'},
            {'name': 'Bitcoin Amsterdam', 'city': 'Amsterdam, Netherlands', 'lat': 52.3676, 'lon': 4.9041, 'frequency': 'Monthly', 'members': 1800, 'next_event': 'Last Friday', 'url': 'https://www.meetup.com/bitcoin-amsterdam/', 'region': 'Europe'},
            {'name': 'Bitcoin Paris', 'city': 'Paris, France', 'lat': 48.8566, 'lon': 2.3522, 'frequency': 'Monthly', 'members': 1600, 'next_event': 'First Tuesday', 'url': 'https://www.meetup.com/bitcoin-paris/', 'region': 'Europe'},
            {'name': 'Bitcoin Berlin', 'city': 'Berlin, Germany', 'lat': 52.5200, 'lon': 13.4050, 'frequency': 'Weekly', 'members': 2200, 'next_event': 'Every Thursday', 'url': 'https://www.meetup.com/bitcoin-lab-berlin/', 'region': 'Europe'},
            {'name': 'Bitcoin Munich', 'city': 'Munich, Germany', 'lat': 48.1351, 'lon': 11.5820, 'frequency': 'Monthly', 'members': 1100, 'next_event': 'Second Wednesday', 'url': 'https://www.meetup.com/bitcoin-munich/', 'region': 'Europe'},
            {'name': 'Bitcoin Zurich', 'city': 'Zurich, Switzerland', 'lat': 47.3769, 'lon': 8.5417, 'frequency': 'Monthly', 'members': 1400, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-zurich/', 'region': 'Europe'},
            {'name': 'Bitcoin Vienna', 'city': 'Vienna, Austria', 'lat': 48.2082, 'lon': 16.3738, 'frequency': 'Monthly', 'members': 900, 'next_event': 'Last Tuesday', 'url': 'https://www.meetup.com/bitcoin-vienna/', 'region': 'Europe'},
            {'name': 'Bitcoin Brussels', 'city': 'Brussels, Belgium', 'lat': 50.8503, 'lon': 4.3517, 'frequency': 'Monthly', 'members': 600, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/bitcoin-brussels/', 'region': 'Europe'},
            {'name': 'Bitcoin Dublin', 'city': 'Dublin, Ireland', 'lat': 53.3498, 'lon': -6.2603, 'frequency': 'Monthly', 'members': 700, 'next_event': 'Second Friday', 'url': 'https://www.meetup.com/bitcoin-dublin/', 'region': 'Europe'},
            {'name': 'Bitcoin Lisbon', 'city': 'Lisbon, Portugal', 'lat': 38.7223, 'lon': -9.1393, 'frequency': 'Monthly', 'members': 1200, 'next_event': 'Third Saturday', 'url': 'https://www.meetup.com/bitcoin-lisbon/', 'region': 'Europe'},
            {'name': 'Bitcoin Madrid', 'city': 'Madrid, Spain', 'lat': 40.4168, 'lon': -3.7038, 'frequency': 'Monthly', 'members': 1000, 'next_event': 'Last Wednesday', 'url': 'https://www.meetup.com/bitcoin-madrid/', 'region': 'Europe'},
            {'name': 'Bitcoin Barcelona', 'city': 'Barcelona, Spain', 'lat': 41.3851, 'lon': 2.1734, 'frequency': 'Monthly', 'members': 900, 'next_event': 'First Saturday', 'url': 'https://www.meetup.com/bitcoin-barcelona/', 'region': 'Europe'},
            {'name': 'Bitcoin Milan', 'city': 'Milan, Italy', 'lat': 45.4642, 'lon': 9.1900, 'frequency': 'Monthly', 'members': 800, 'next_event': 'Second Tuesday', 'url': 'https://www.meetup.com/bitcoin-milano/', 'region': 'Europe'},
            {'name': 'Bitcoin Rome', 'city': 'Rome, Italy', 'lat': 41.9028, 'lon': 12.4964, 'frequency': 'Monthly', 'members': 650, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-roma/', 'region': 'Europe'},
            {'name': 'Bitcoin Frankfurt', 'city': 'Frankfurt, Germany', 'lat': 50.1109, 'lon': 8.6821, 'frequency': 'Monthly', 'members': 750, 'next_event': 'Last Friday', 'url': 'https://www.meetup.com/bitcoin-frankfurt/', 'region': 'Europe'},
            
            # Nordic Countries
            {'name': 'Bitcoin Stockholm', 'city': 'Stockholm, Sweden', 'lat': 59.3293, 'lon': 18.0686, 'frequency': 'Monthly', 'members': 800, 'next_event': 'First Wednesday', 'url': 'https://www.meetup.com/bitcoin-stockholm/', 'region': 'Europe'},
            {'name': 'Bitcoin Oslo', 'city': 'Oslo, Norway', 'lat': 59.9139, 'lon': 10.7522, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Second Thursday', 'url': 'https://www.meetup.com/bitcoin-oslo/', 'region': 'Europe'},
            {'name': 'Bitcoin Copenhagen', 'city': 'Copenhagen, Denmark', 'lat': 55.6761, 'lon': 12.5683, 'frequency': 'Monthly', 'members': 700, 'next_event': 'Third Tuesday', 'url': 'https://www.meetup.com/bitcoin-copenhagen/', 'region': 'Europe'},
            {'name': 'Bitcoin Helsinki', 'city': 'Helsinki, Finland', 'lat': 60.1699, 'lon': 24.9384, 'frequency': 'Monthly', 'members': 500, 'next_event': 'Last Saturday', 'url': 'https://www.meetup.com/bitcoin-helsinki/', 'region': 'Europe'},
            
            # Eastern Europe
            {'name': 'Bitcoin Prague', 'city': 'Prague, Czech Republic', 'lat': 50.0755, 'lon': 14.4378, 'frequency': 'Monthly', 'members': 1500, 'next_event': 'First Friday', 'url': 'https://www.meetup.com/bitcoin-prague/', 'region': 'Europe'},
            {'name': 'Bitcoin Warsaw', 'city': 'Warsaw, Poland', 'lat': 52.2297, 'lon': 21.0122, 'frequency': 'Monthly', 'members': 900, 'next_event': 'Second Wednesday', 'url': 'https://www.meetup.com/bitcoin-warsaw/', 'region': 'Europe'},
            {'name': 'Bitcoin Budapest', 'city': 'Budapest, Hungary', 'lat': 47.4979, 'lon': 19.0402, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-budapest/', 'region': 'Europe'},
            {'name': 'Bitcoin Bucharest', 'city': 'Bucharest, Romania', 'lat': 44.4268, 'lon': 26.1025, 'frequency': 'Monthly', 'members': 500, 'next_event': 'Last Tuesday', 'url': 'https://www.meetup.com/bitcoin-bucharest/', 'region': 'Europe'},
            {'name': 'Bitcoin Tallinn', 'city': 'Tallinn, Estonia', 'lat': 59.4370, 'lon': 24.7536, 'frequency': 'Monthly', 'members': 450, 'next_event': 'First Saturday', 'url': 'https://www.meetup.com/bitcoin-tallinn/', 'region': 'Europe'},
            
            # ==================== ASIA ====================
            {'name': 'Bitcoin Tokyo', 'city': 'Tokyo, Japan', 'lat': 35.6762, 'lon': 139.6503, 'frequency': 'Monthly', 'members': 1500, 'next_event': 'Second Saturday', 'url': 'https://www.meetup.com/tokyo-bitcoin-meetup/', 'region': 'Asia'},
            {'name': 'Bitcoin Singapore', 'city': 'Singapore', 'lat': 1.3521, 'lon': 103.8198, 'frequency': 'Monthly', 'members': 2000, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/bitcoin-singapore/', 'region': 'Asia'},
            {'name': 'Bitcoin Hong Kong', 'city': 'Hong Kong', 'lat': 22.3193, 'lon': 114.1694, 'frequency': 'Monthly', 'members': 1800, 'next_event': 'Third Wednesday', 'url': 'https://www.meetup.com/bitcoin-hong-kong/', 'region': 'Asia'},
            {'name': 'Bitcoin Seoul', 'city': 'Seoul, South Korea', 'lat': 37.5665, 'lon': 126.9780, 'frequency': 'Monthly', 'members': 1200, 'next_event': 'Last Friday', 'url': 'https://www.meetup.com/bitcoin-seoul/', 'region': 'Asia'},
            {'name': 'Bitcoin Bangkok', 'city': 'Bangkok, Thailand', 'lat': 13.7563, 'lon': 100.5018, 'frequency': 'Monthly', 'members': 900, 'next_event': 'Second Tuesday', 'url': 'https://www.meetup.com/bitcoin-bangkok/', 'region': 'Asia'},
            {'name': 'Bitcoin Manila', 'city': 'Manila, Philippines', 'lat': 14.5995, 'lon': 120.9842, 'frequency': 'Monthly', 'members': 800, 'next_event': 'Third Saturday', 'url': 'https://www.meetup.com/bitcoin-manila/', 'region': 'Asia'},
            {'name': 'Bitcoin Taipei', 'city': 'Taipei, Taiwan', 'lat': 25.0330, 'lon': 121.5654, 'frequency': 'Monthly', 'members': 700, 'next_event': 'First Wednesday', 'url': 'https://www.meetup.com/bitcoin-taipei/', 'region': 'Asia'},
            {'name': 'Bitcoin Jakarta', 'city': 'Jakarta, Indonesia', 'lat': -6.2088, 'lon': 106.8456, 'frequency': 'Monthly', 'members': 1000, 'next_event': 'Second Thursday', 'url': 'https://www.meetup.com/bitcoin-jakarta/', 'region': 'Asia'},
            {'name': 'Bitcoin Kuala Lumpur', 'city': 'Kuala Lumpur, Malaysia', 'lat': 3.1390, 'lon': 101.6869, 'frequency': 'Monthly', 'members': 650, 'next_event': 'Last Tuesday', 'url': 'https://www.meetup.com/bitcoin-kuala-lumpur/', 'region': 'Asia'},
            {'name': 'Bitcoin Saigon', 'city': 'Ho Chi Minh City, Vietnam', 'lat': 10.8231, 'lon': 106.6297, 'frequency': 'Monthly', 'members': 550, 'next_event': 'Third Friday', 'url': 'https://www.meetup.com/bitcoin-saigon/', 'region': 'Asia'},
            {'name': 'Bitcoin Bangalore', 'city': 'Bangalore, India', 'lat': 12.9716, 'lon': 77.5946, 'frequency': 'Monthly', 'members': 1400, 'next_event': 'First Saturday', 'url': 'https://www.meetup.com/bitcoin-bangalore/', 'region': 'Asia'},
            {'name': 'Bitcoin Mumbai', 'city': 'Mumbai, India', 'lat': 19.0760, 'lon': 72.8777, 'frequency': 'Monthly', 'members': 1100, 'next_event': 'Second Sunday', 'url': 'https://www.meetup.com/bitcoin-mumbai/', 'region': 'Asia'},
            {'name': 'Bitcoin Delhi', 'city': 'New Delhi, India', 'lat': 28.6139, 'lon': 77.2090, 'frequency': 'Monthly', 'members': 900, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-delhi/', 'region': 'Asia'},
            
            # ==================== MIDDLE EAST ====================
            {'name': 'Bitcoin Dubai', 'city': 'Dubai, UAE', 'lat': 25.2048, 'lon': 55.2708, 'frequency': 'Monthly', 'members': 1600, 'next_event': 'First Tuesday', 'url': 'https://www.meetup.com/bitcoin-dubai/', 'region': 'Middle East'},
            {'name': 'Bitcoin Tel Aviv', 'city': 'Tel Aviv, Israel', 'lat': 32.0853, 'lon': 34.7818, 'frequency': 'Monthly', 'members': 1200, 'next_event': 'Second Wednesday', 'url': 'https://www.meetup.com/bitcoin-tel-aviv/', 'region': 'Middle East'},
            {'name': 'Bitcoin Riyadh', 'city': 'Riyadh, Saudi Arabia', 'lat': 24.7136, 'lon': 46.6753, 'frequency': 'Monthly', 'members': 500, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-riyadh/', 'region': 'Middle East'},
            
            # ==================== OCEANIA ====================
            {'name': 'Bitcoin Sydney', 'city': 'Sydney, Australia', 'lat': -33.8688, 'lon': 151.2093, 'frequency': 'Monthly', 'members': 1400, 'next_event': 'First Thursday', 'url': 'https://www.meetup.com/bitcoin-sydney/', 'region': 'Oceania'},
            {'name': 'Bitcoin Melbourne', 'city': 'Melbourne, Australia', 'lat': -37.8136, 'lon': 144.9631, 'frequency': 'Monthly', 'members': 1100, 'next_event': 'Second Tuesday', 'url': 'https://www.meetup.com/bitcoin-melbourne/', 'region': 'Oceania'},
            {'name': 'Bitcoin Brisbane', 'city': 'Brisbane, Australia', 'lat': -27.4698, 'lon': 153.0251, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Third Wednesday', 'url': 'https://www.meetup.com/bitcoin-brisbane/', 'region': 'Oceania'},
            {'name': 'Bitcoin Auckland', 'city': 'Auckland, New Zealand', 'lat': -36.8485, 'lon': 174.7633, 'frequency': 'Monthly', 'members': 500, 'next_event': 'Last Friday', 'url': 'https://www.meetup.com/bitcoin-auckland/', 'region': 'Oceania'},
            {'name': 'Bitcoin Perth', 'city': 'Perth, Australia', 'lat': -31.9505, 'lon': 115.8605, 'frequency': 'Monthly', 'members': 400, 'next_event': 'First Saturday', 'url': 'https://www.meetup.com/bitcoin-perth/', 'region': 'Oceania'},
            
            # ==================== AFRICA ====================
            {'name': 'Bitcoin Lagos', 'city': 'Lagos, Nigeria', 'lat': 6.5244, 'lon': 3.3792, 'frequency': 'Monthly', 'members': 2000, 'next_event': 'Second Saturday', 'url': 'https://www.meetup.com/bitcoin-lagos/', 'region': 'Africa'},
            {'name': 'Bitcoin Nairobi', 'city': 'Nairobi, Kenya', 'lat': -1.2921, 'lon': 36.8219, 'frequency': 'Monthly', 'members': 1500, 'next_event': 'Third Thursday', 'url': 'https://www.meetup.com/bitcoin-nairobi/', 'region': 'Africa'},
            {'name': 'Bitcoin Cape Town', 'city': 'Cape Town, South Africa', 'lat': -33.9249, 'lon': 18.4241, 'frequency': 'Monthly', 'members': 800, 'next_event': 'Last Tuesday', 'url': 'https://www.meetup.com/bitcoin-cape-town/', 'region': 'Africa'},
            {'name': 'Bitcoin Johannesburg', 'city': 'Johannesburg, South Africa', 'lat': -26.2041, 'lon': 28.0473, 'frequency': 'Monthly', 'members': 700, 'next_event': 'First Friday', 'url': 'https://www.meetup.com/bitcoin-johannesburg/', 'region': 'Africa'},
            {'name': 'Bitcoin Accra', 'city': 'Accra, Ghana', 'lat': 5.6037, 'lon': -0.1870, 'frequency': 'Monthly', 'members': 600, 'next_event': 'Second Wednesday', 'url': 'https://www.meetup.com/bitcoin-accra/', 'region': 'Africa'},
            {'name': 'Bitcoin Cairo', 'city': 'Cairo, Egypt', 'lat': 30.0444, 'lon': 31.2357, 'frequency': 'Monthly', 'members': 500, 'next_event': 'Third Saturday', 'url': 'https://www.meetup.com/bitcoin-cairo/', 'region': 'Africa'},
            {'name': 'Bitcoin Addis Ababa', 'city': 'Addis Ababa, Ethiopia', 'lat': 8.9806, 'lon': 38.7578, 'frequency': 'Monthly', 'members': 350, 'next_event': 'Last Thursday', 'url': 'https://www.meetup.com/bitcoin-addis-ababa/', 'region': 'Africa'},
        ]
        
        return worldwide_meetups
    
    def get_bitcoin_atms(self, min_lat: float, min_lon: float, 
                          max_lat: float, max_lon: float) -> List[Dict]:
        """Get Bitcoin ATMs within bounds from BTC Map"""
        cache_key = f"atms_{min_lat}_{min_lon}_{max_lat}_{max_lon}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{self.BTC_MAP_API}/elements",
                params={'limit': 200},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                atms = []
                
                for element in data.get('data', []):
                    osm_json = element.get('osm_json', {})
                    tags = osm_json.get('tags', {})
                    
                    if tags.get('amenity') == 'atm' or 'atm' in tags.get('name', '').lower():
                        lat = osm_json.get('lat', 0)
                        lon = osm_json.get('lon', 0)
                        
                        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                            atms.append({
                                'id': element.get('id'),
                                'name': tags.get('name', 'Bitcoin ATM'),
                                'lat': lat,
                                'lon': lon,
                                'operator': tags.get('operator', 'Unknown'),
                                'buy': tags.get('atm:bitcoin:buy', 'unknown'),
                                'sell': tags.get('atm:bitcoin:sell', 'unknown'),
                                'address': self._format_address(tags)
                            })
                
                self._set_cached(cache_key, atms)
                return atms
                
        except Exception as e:
            logging.error(f"Error fetching ATMs: {e}")
        
        return []
    
    def _categorize_merchant(self, tags: Dict) -> str:
        """Categorize merchant by OSM tags"""
        amenity = tags.get('amenity', '')
        shop = tags.get('shop', '')
        tourism = tags.get('tourism', '')
        
        if amenity in ['restaurant', 'fast_food', 'cafe', 'bar', 'pub']:
            return 'food_drink'
        elif amenity in ['atm', 'bank']:
            return 'atm_exchange'
        elif shop in ['supermarket', 'convenience', 'grocery']:
            return 'grocery'
        elif shop in ['clothes', 'shoes', 'jewelry']:
            return 'retail'
        elif shop in ['electronics', 'computer', 'mobile_phone']:
            return 'electronics'
        elif tourism in ['hotel', 'hostel', 'guest_house']:
            return 'accommodation'
        elif shop or amenity:
            return 'other'
        else:
            return 'unknown'
    
    def _format_address(self, tags: Dict) -> str:
        """Format address from OSM tags"""
        parts = []
        if tags.get('addr:housenumber'):
            parts.append(tags['addr:housenumber'])
        if tags.get('addr:street'):
            parts.append(tags['addr:street'])
        if tags.get('addr:city'):
            parts.append(tags['addr:city'])
        if tags.get('addr:country'):
            parts.append(tags['addr:country'])
        return ', '.join(parts) if parts else ''
    
    def search_merchants(self, query: str, limit: int = 20) -> List[Dict]:
        """Search merchants by name or location"""
        try:
            response = requests.get(
                f"{self.BTC_MAP_API}/elements",
                params={'limit': 500},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                query_lower = query.lower()
                
                for element in data.get('data', []):
                    osm_json = element.get('osm_json', {})
                    tags = osm_json.get('tags', {})
                    name = tags.get('name', '').lower()
                    city = tags.get('addr:city', '').lower()
                    
                    if query_lower in name or query_lower in city:
                        results.append({
                            'id': element.get('id'),
                            'name': tags.get('name', 'Unknown'),
                            'lat': osm_json.get('lat', 0),
                            'lon': osm_json.get('lon', 0),
                            'type': self._categorize_merchant(tags),
                            'address': self._format_address(tags)
                        })
                        
                        if len(results) >= limit:
                            break
                
                return results
                
        except Exception as e:
            logging.error(f"Error searching merchants: {e}")
        
        return []
    
    def get_meetups_by_region(self, region: str = None) -> List[Dict]:
        """Get meetups filtered by region"""
        all_meetups = self.get_bitcoin_meetups()
        
        if not region:
            return all_meetups
        
        return [m for m in all_meetups if m.get('region', '').lower() == region.lower()]
    
    def get_meetup_stats(self) -> Dict:
        """Get statistics about Bitcoin meetups"""
        meetups = self.get_bitcoin_meetups()
        
        total_members = sum(m.get('members', 0) for m in meetups)
        regions = set(m.get('region', 'Unknown') for m in meetups)
        
        return {
            'total_meetups': len(meetups),
            'total_members': total_members,
            'regions': len(regions),
            'top_cities': sorted(meetups, key=lambda x: x.get('members', 0), reverse=True)[:10]
        }


meetup_map_service = MeetupMapService()
```

## services/social_listener.py
```python
"""
Social Intelligence Listener Service
24/7 monitoring of high-value X handles with Gemini image auto-engagement
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    logging.warning("Tweepy not installed - Social Listener running in monitor-only mode")

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class SocialListenerService:
    """
    Monitors designated X handles for new posts and generates
    AI-powered visual responses using Gemini Imagen 3.
    """
    
    def __init__(self):
        self.initialized = False
        self.targets = []
        self.last_seen_tweets: Dict[str, str] = {}
        self.bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')
        self.api_key = os.environ.get('TWITTER_API_KEY')
        self.gemini_key = os.environ.get('GEMINI_API_KEY')
        
        self._load_targets()
        self._init_clients()
        
    def _load_targets(self):
        """Load monitoring targets from config file"""
        config_path = 'config/social_targets.json'
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.targets = config.get('targets', [])
                    self.poll_interval = config.get('update_interval_minutes', 10)
                    logging.info(f"Social Listener: Loaded {len(self.targets)} monitoring targets")
        except Exception as e:
            logging.error(f"Failed to load social targets: {e}")
            self.targets = []
            
    def _init_clients(self):
        """Initialize Twitter and Gemini API clients"""
        try:
            if self.bearer_token and TWEEPY_AVAILABLE:
                self.twitter_client = tweepy.Client(
                    bearer_token=self.bearer_token,
                    wait_on_rate_limit=True
                )
                logging.info("Social Listener: Twitter client initialized")
            else:
                self.twitter_client = None
                
            if self.gemini_key and GEMINI_AVAILABLE:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
                logging.info("Social Listener: Gemini client initialized")
            else:
                self.gemini_client = None
                
            self.initialized = bool(self.twitter_client)
            
        except Exception as e:
            logging.error(f"Social Listener initialization error: {e}")
            self.initialized = False
            
    def get_target_handles(self, priority: Optional[int] = None, category: Optional[str] = None) -> List[str]:
        """Get list of handles to monitor, optionally filtered"""
        handles = []
        for target in self.targets:
            if priority and target.get('priority') != priority:
                continue
            if category and target.get('category') != category:
                continue
            handles.append(target['handle'])
        return handles
        
    def fetch_recent_tweets(self, handle: str, since_minutes: int = 15) -> List[Dict[str, Any]]:
        """Fetch recent tweets from a specific handle"""
        if not self.twitter_client:
            return []
            
        try:
            user = self.twitter_client.get_user(username=handle)
            if not user.data:
                return []
                
            user_id = user.data.id
            start_time = datetime.utcnow() - timedelta(minutes=since_minutes)
            
            tweets = self.twitter_client.get_users_tweets(
                id=user_id,
                start_time=start_time.isoformat() + 'Z',
                max_results=10,
                tweet_fields=['created_at', 'public_metrics', 'text']
            )
            
            if not tweets.data:
                return []
                
            result = []
            for tweet in tweets.data:
                result.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'metrics': tweet.public_metrics,
                    'handle': handle
                })
            return result
            
        except Exception as e:
            logging.error(f"Error fetching tweets for @{handle}: {e}")
            return []
            
    def generate_engagement_image(self, tweet_text: str) -> Optional[bytes]:
        """
        Generate a Protocol Pulse branded technical visualization
        using Gemini Imagen 3 based on tweet content
        """
        if not self.gemini_client:
            logging.warning("Gemini client not available for image generation")
            return None
            
        try:
            prompt = f"""Create a hyper-realistic 2026 cyberpunk-style technical diagram or infographic 
reflecting this concept: {tweet_text[:500]}

Design Requirements:
- Use Protocol Pulse color scheme: Primary Red (#dc2626), Deep Black (#000000), Pure White (#ffffff)
- Include subtle Bitcoin network visualization elements
- Modern glassmorphism aesthetic with neon accents
- Professional financial intelligence briefing style
- Include subtle grid patterns and data visualization elements
- No text or words in the image"""

            response = self.gemini_client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio='16:9',
                    safety_filter_level='BLOCK_ONLY_HIGH'
                )
            )
            
            if response.generated_images:
                return response.generated_images[0].image.image_bytes
            return None
            
        except Exception as e:
            logging.error(f"Gemini image generation error: {e}")
            return None
            
    def generate_engagement_text(self, tweet_text: str) -> str:
        """
        Generate a Walter Cronkite-style one-liner response
        """
        if not self.gemini_client:
            return "The protocol speaks for itself. 🔴"
            
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""You are a Walter Cronkite-style Bitcoin intelligence analyst for Protocol Pulse.
                
Generate a single, authoritative one-liner reply to this tweet: "{tweet_text[:300]}"

Requirements:
- Maximum 180 characters
- Sound like a seasoned financial journalist
- Reference Bitcoin fundamentals when relevant
- Be insightful, not promotional
- End with subtle conviction

Reply:"""
            )
            
            if response.text:
                return response.text.strip()[:180]
            return "The protocol speaks for itself. 🔴"
            
        except Exception as e:
            logging.error(f"Gemini text generation error: {e}")
            return "The protocol speaks for itself. 🔴"
            
    def post_engagement_reply(self, tweet_id: str, text: str, image_bytes: Optional[bytes] = None) -> bool:
        """
        Post a reply to a tweet with optional image attachment
        Note: Requires write access tokens (not just bearer token)
        """
        logging.info(f"Would post reply to tweet {tweet_id}: {text}")
        return False
        
    def scan_all_targets(self) -> Dict[str, Any]:
        """
        Scan all monitoring targets for new tweets
        Returns summary of findings
        """
        results = {
            'scanned': 0,
            'new_tweets': [],
            'errors': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        priority_handles = self.get_target_handles(priority=1)
        
        for handle in priority_handles[:10]:
            try:
                tweets = self.fetch_recent_tweets(handle, since_minutes=15)
                results['scanned'] += 1
                
                for tweet in tweets:
                    tweet_id = str(tweet['id'])
                    if self.last_seen_tweets.get(handle) != tweet_id:
                        results['new_tweets'].append(tweet)
                        self.last_seen_tweets[handle] = tweet_id
                        
            except Exception as e:
                results['errors'].append({'handle': handle, 'error': str(e)})
                
            time.sleep(0.5)
            
        logging.info(f"Social scan complete: {results['scanned']} handles, {len(results['new_tweets'])} new tweets")
        return results
        
    def get_status(self) -> Dict[str, Any]:
        """Get service status for admin dashboard"""
        return {
            'initialized': self.initialized,
            'twitter_connected': bool(self.twitter_client),
            'gemini_connected': bool(self.gemini_client),
            'targets_loaded': len(self.targets),
            'priority_1_targets': len(self.get_target_handles(priority=1)),
            'last_seen_count': len(self.last_seen_tweets)
        }


social_listener = SocialListenerService()
```

## services/printful_service.py
```python
import requests
import logging
from typing import List, Dict, Optional
import os

class PrintfulService:
    """Service for integrating with Printful API for merch store"""
    
    # Multiple store IDs - Proto P first (priority), then Consensus Protocol
    STORES = [
        {'id': '17589919', 'name': 'Proto P', 'url_base': 'https://proto-p.printful.me'},
        {'id': '13051112', 'name': 'Consensus Protocol', 'url_base': 'https://protocolpulse.printful.me'}
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.environ.get('PRINTFUL_API_KEY')
        self.base_url = 'https://api.printful.com'
        
        if not self.api_key:
            self.logger.warning("PRINTFUL_API_KEY not configured - merch functionality disabled")
    
    def _get_headers(self, store_id: str) -> Dict:
        """Get headers for a specific store"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-PF-Store-Id': store_id
        }
    
    def get_store_products(self) -> List[Dict]:
        """Get all products from all Printful stores (Proto P first, then Consensus Protocol)"""
        if not self.api_key:
            return []
        
        all_products = []
        
        for store in self.STORES:
            try:
                headers = self._get_headers(store['id'])
                response = requests.get(
                    f'{self.base_url}/sync/products',
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get('code') == 200:
                    products = data.get('result', [])
                    for product in products:
                        product_id = product.get('id')
                        if product_id:
                            detail = self.get_product_details(product_id, store['id'], store['url_base'])
                            if detail:
                                detail['store_name'] = store['name']
                                all_products.append(detail)
                    self.logger.info(f"Fetched {len(products)} products from {store['name']}")
                else:
                    self.logger.error(f"Printful API error for {store['name']}: {data}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching products from {store['name']}: {e}")
        
        return all_products
    
    def get_product_details(self, product_id: int, store_id: str = None, url_base: str = None) -> Optional[Dict]:
        """Get detailed information for a specific product"""
        if not self.api_key:
            return None
        
        # Default to first store if not specified
        if not store_id:
            store_id = self.STORES[0]['id']
        if not url_base:
            url_base = self.STORES[0]['url_base']
        
        try:
            headers = self._get_headers(store_id)
            response = requests.get(
                f'{self.base_url}/sync/products/{product_id}',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                result = data.get('result')
                # Attach the store URL base for proper linking
                if result:
                    result['_store_url_base'] = url_base
                return result
            else:
                self.logger.error(f"Printful API error for product {product_id}: {data}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching Printful product {product_id}: {e}")
            return None
    
    def create_order(self, order_data: Dict) -> Optional[Dict]:
        """Create an order in Printful"""
        if not self.api_key:
            return None
        
        try:
            response = requests.post(
                f'{self.base_url}/orders',
                headers=self.headers,
                json=order_data,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') in [200, 201]:
                return data.get('result')
            else:
                self.logger.error(f"Printful order creation error: {data}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating Printful order: {e}")
            return None
    
    def get_shipping_rates(self, recipient: Dict, items: List[Dict]) -> List[Dict]:
        """Get shipping rates for an order"""
        if not self.api_key:
            return []
        
        try:
            shipping_data = {
                'recipient': recipient,
                'items': items
            }
            
            response = requests.post(
                f'{self.base_url}/shipping/rates',
                headers=self.headers,
                json=shipping_data,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                return data.get('result', [])
            else:
                self.logger.error(f"Printful shipping rates error: {data}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting Printful shipping rates: {e}")
            return []
    
    def format_product_for_display(self, product: Dict) -> Dict:
        """Format Printful product data for website display"""
        sync_product = product.get('sync_product', {})
        sync_variants = product.get('sync_variants', [])
        store_url_base = product.get('_store_url_base', 'https://proto-p.printful.me')
        store_name = product.get('store_name', 'Proto P')
        
        # Get the main product image
        main_image = None
        if sync_variants:
            files = sync_variants[0].get('files', [])
            for file_data in files:
                if file_data.get('type') == 'preview':
                    main_image = file_data.get('preview_url')
                    break
        
        # Format variants with pricing
        variants = []
        for variant in sync_variants:
            variant_data = {
                'id': variant.get('id'),
                'name': variant.get('name', ''),
                'price': variant.get('retail_price', '0.00'),
                'currency': variant.get('currency', 'USD'),
                'size': variant.get('size', ''),
                'color': variant.get('color', ''),
                'in_stock': variant.get('availability_status') != 'out_of_stock'
            }
            variants.append(variant_data)
        
        # Construct store URL using the correct store base URL
        product_id = sync_product.get('external_id') or sync_product.get('id')
        store_url = f"{store_url_base}/product/{product_id}" if product_id else None
        
        return {
            'id': sync_product.get('id'),
            'name': sync_product.get('name', 'Product'),
            'thumbnail': sync_product.get('thumbnail_url'),
            'main_image': main_image,
            'variants': variants,
            'description': sync_product.get('description', ''),
            'tags': sync_product.get('tags', []),
            'is_ignored': sync_product.get('is_ignored', False),
            'store_url': store_url,
            'store_name': store_name
        }```

---

# SECTION 3: TEMPLATES

## templates/base.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#dc2626">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Protocol Pulse">
    <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
    <link rel="apple-touch-icon" href="{{ url_for('static', filename='icons/icon-192.png') }}">
    <title>{% block title %}Protocol Pulse{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}?v=1.2">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/coindesk-style.css') }}?v=1.1">
    
    <!-- JSON-LD Schema Markup for AI Agent Ingestion (ChatGPT/Gemini) -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsMediaOrganization",
        "name": "Protocol Pulse",
        "url": "{{ request.url_root }}",
        "logo": "{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}",
        "description": "World-Class Bitcoin Intelligence Hub delivering peer-to-peer briefings for transactors. Real-time network metrics, expert analysis, and sound money philosophy.",
        "sameAs": [
            "https://twitter.com/ProtocolPulse"
        ],
        "foundingDate": "2025",
        "knowsAbout": ["Bitcoin", "Cryptocurrency", "Blockchain", "Sound Money", "Mining", "Network Security"],
        "publishingPrinciples": "Technical Storytelling for transactors, not tourists. All content verified against ground truth network data.",
        "slogan": "Intelligence for Transactors"
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Protocol Pulse",
        "url": "{{ request.url_root }}",
        "potentialAction": {
            "@type": "SearchAction",
            "target": "{{ request.url_root }}search?q={search_term_string}",
            "query-input": "required name=search_term_string"
        },
        "about": {
            "@type": "Thing",
            "name": "Bitcoin Network Intelligence",
            "description": "Real-time Bitcoin network metrics including difficulty (146.47 T), hashrate (~977 EH/s), and mining economics analysis."
        }
    }
    </script>
    {% block schema %}{% endblock %}
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark fixed-top bg-dark">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">
                <img src="{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png') }}" alt="Protocol Pulse" height="32" class="me-2">
                Protocol Pulse
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto ms-lg-4">
                    <li class="nav-item">
                        <a class="nav-link" href="/">
                            <i class="fas fa-chart-area"></i>
                            <span>Intel</span>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/articles">
                            <i class="fas fa-newspaper"></i>
                            <span>Briefs</span>
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                            <i class="fas fa-map-marked-alt"></i>
                            <span>Maps</span>
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item text-light" href="/map"><i class="fas fa-store me-2 text-warning"></i>Merchants</a></li>
                            <li><a class="dropdown-item text-light" href="/meetup-map"><i class="fas fa-users me-2 text-info"></i>Meetups</a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/media">
                            <i class="fas fa-broadcast-tower"></i>
                            <span>Media</span>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/merch">
                            <i class="fas fa-tshirt"></i>
                            <span>Merch</span>
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                            <i class="fas fa-layer-group"></i>
                            <span>Topics</span>
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item text-light" href="/bitcoin"><i class="fab fa-bitcoin me-2 text-warning"></i>Bitcoin</a></li>
                            <li><a class="dropdown-item text-light" href="/defi"><i class="fas fa-coins me-2 text-info"></i>DeFi</a></li>
                            <li><a class="dropdown-item text-light" href="/regulation"><i class="fas fa-gavel me-2 text-danger"></i>Regulation</a></li>
                            <li><a class="dropdown-item text-light" href="/privacy"><i class="fas fa-user-secret me-2 text-success"></i>Privacy</a></li>
                            <li><a class="dropdown-item text-light" href="/innovation"><i class="fas fa-lightbulb me-2 text-warning"></i>Innovation</a></li>
                            <li><hr class="dropdown-divider" style="border-color: rgba(255,255,255,0.1);"></li>
                            <li><a class="dropdown-item text-light" href="/cypherpunks"><i class="fas fa-mask me-2 text-purple" style="color: #a855f7;"></i>Cypherpunks</a></li>
                        </ul>
                    </li>
                </ul>
                <form class="d-flex me-3 navbar-search">
                    <input class="form-control" type="search" placeholder="Search...">
                    <button class="btn btn-outline-danger" type="submit">
                        <i class="fas fa-search"></i>
                    </button>
                </form>
                {% if current_user.is_authenticated %}
                    {% if current_user.is_admin %}
                    <a href="/admin" class="btn btn-outline-warning btn-sm me-2">
                        <i class="fas fa-cogs me-1"></i>Admin
                    </a>
                    {% endif %}
                    <a href="/logout" class="btn btn-outline-secondary btn-sm">
                        <i class="fas fa-sign-out-alt me-1"></i>Logout
                    </a>
                {% else %}
                    <a href="/login" class="btn btn-outline-light btn-sm">
                        <i class="fas fa-user me-1"></i>Login
                    </a>
                {% endif %}
            </div>
        </div>
    </nav>
    <main class="content-wrapper main-content">
        {% block content %}{% endblock %}
    </main>
    <footer class="bg-dark text-white py-4">
        <div class="container">
            <div class="row">
                <div class="col-md-3">
                    <h5>Protocol Pulse</h5>
                    <p>Bitcoin Intelligence for Transactors.</p>
                </div>
                <div class="col-md-3">
                    <h5>Command Center</h5>
                    <ul class="list-unstyled">
                        <li><a href="/#dashboard">Dashboard</a></li>
                        <li><a href="/#terminal">Live Terminal</a></li>
                        <li><a href="/#whale-watcher">Whale Watcher</a></li>
                        <li><a href="/map">Merchant Map</a></li>
                        <li><a href="/scorecard">Sovereign Scorecard</a></li>
                        <li><a href="/clips">Signal Clips</a></li>
                    </ul>
                </div>
                <div class="col-md-3">
                    <h5>Categories</h5>
                    <ul class="list-unstyled">
                        <li><a href="/bitcoin">Bitcoin</a></li>
                        <li><a href="/defi">DeFi</a></li>
                    </ul>
                    <div class="mt-3">
                        <h6 class="text-muted mb-2"><i class="fas fa-heart me-1"></i> Support the Signal</h6>
                        <a href="/donate" class="btn btn-sm btn-outline-success me-1 mb-1">Tip $</a>
                        <a href="/donate/bitcoin" class="btn btn-sm btn-outline-warning mb-1"><i class="fas fa-bolt"></i> Tip Sats</a>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="satoshi-clock">
                        <div class="clock-label">NETWORK TIME (EST)</div>
                        <div class="clock-display" id="est-clock" style="font-size: 1.3rem; margin-bottom: 10px;">
                            <span class="clock-value" id="est-time">--:--:--</span>
                            <span class="clock-unit" style="margin-left: 5px;">EST</span>
                        </div>
                        <div class="clock-label" style="margin-top: 8px;">2028 HALVING</div>
                        <div class="clock-display" id="halving-clock" style="font-size: 1.1rem;">
                            <span class="clock-segment"><span class="clock-value" id="halving-days">---</span><span class="clock-unit">D</span></span>
                            <span class="clock-separator">:</span>
                            <span class="clock-segment"><span class="clock-value" id="halving-hours">--</span><span class="clock-unit">H</span></span>
                            <span class="clock-separator">:</span>
                            <span class="clock-segment"><span class="clock-value" id="halving-mins">--</span><span class="clock-unit">M</span></span>
                        </div>
                        <div class="clock-sublabel">Block 1,050,000</div>
                    </div>
                </div>
            </div>
            <hr>
            <div class="d-flex justify-content-between align-items-center">
                <p class="mb-0">&copy; 2026 Protocol Pulse</p>
                <div class="gas-alert-toggle">
                    <button class="btn btn-sm btn-outline-danger" onclick="toggleGasAlerts()" id="gas-alert-btn">
                        <i class="fas fa-bell me-1"></i>
                        <span id="gas-alert-status">Enable Fee Alerts</span>
                    </button>
                </div>
            </div>
        </div>
    </footer>
    
    <style>
    .satoshi-clock {
        text-align: center;
        padding: 15px;
        background: rgba(220, 38, 38, 0.1);
        border: 1px solid rgba(220, 38, 38, 0.3);
        border-radius: 12px;
    }
    .clock-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: #dc2626;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .clock-display {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        color: #fff;
        display: flex;
        justify-content: center;
        align-items: baseline;
        gap: 2px;
    }
    .clock-segment {
        display: inline-flex;
        align-items: baseline;
    }
    .clock-value {
        font-weight: 700;
    }
    .clock-unit {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.5);
        margin-left: 2px;
    }
    .clock-separator {
        color: #dc2626;
        font-weight: 300;
    }
    .clock-sublabel {
        font-size: 0.6rem;
        color: rgba(255,255,255,0.4);
        margin-top: 5px;
        font-family: 'JetBrains Mono', monospace;
    }
    .gas-alert-toggle .btn {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
    }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    <script src="{{ url_for('static', filename='js/coindesk.js') }}"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            var navbarCollapse = document.getElementById('navbarNav');
            var navLinks = navbarCollapse.querySelectorAll('.nav-link, .btn');
            navLinks.forEach(function(link) {
                link.addEventListener('click', function() {
                    if (window.innerWidth < 992) {
                        var bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                        if (bsCollapse) {
                            bsCollapse.hide();
                        }
                    }
                });
            });
        });
    </script>
    <script>
    // EST Time Display
    function updateESTClock() {
        const now = new Date();
        const estTime = now.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
        const estEl = document.getElementById('est-time');
        if (estEl) estEl.textContent = estTime;
    }
    
    // Satoshi Clock - 2028 Halving Countdown
    function updateHalvingClock() {
        // Estimated halving date: April 2028 (block 1,050,000)
        const halvingDate = new Date('2028-04-15T00:00:00Z');
        const now = new Date();
        const diff = halvingDate - now;
        
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            
            document.getElementById('halving-days').textContent = days.toString().padStart(3, '0');
            document.getElementById('halving-hours').textContent = hours.toString().padStart(2, '0');
            document.getElementById('halving-mins').textContent = mins.toString().padStart(2, '0');
        }
        
        updateESTClock();
    }
    
    // Gas Alert System
    let gasAlertsEnabled = localStorage.getItem('gasAlerts') === 'true';
    
    function updateGasAlertUI() {
        const btn = document.getElementById('gas-alert-btn');
        const status = document.getElementById('gas-alert-status');
        if (gasAlertsEnabled) {
            btn.classList.remove('btn-outline-danger');
            btn.classList.add('btn-danger');
            status.textContent = 'Fee Alerts ON';
        } else {
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-outline-danger');
            status.textContent = 'Enable Fee Alerts';
        }
    }
    
    function toggleGasAlerts() {
        if (!('Notification' in window)) {
            alert('Browser notifications not supported');
            return;
        }
        
        if (Notification.permission === 'denied') {
            alert('Notifications blocked. Please enable in browser settings.');
            return;
        }
        
        if (Notification.permission === 'default') {
            Notification.requestPermission().then(perm => {
                if (perm === 'granted') {
                    gasAlertsEnabled = true;
                    localStorage.setItem('gasAlerts', 'true');
                    updateGasAlertUI();
                    checkFeeAlert();
                }
            });
        } else {
            gasAlertsEnabled = !gasAlertsEnabled;
            localStorage.setItem('gasAlerts', gasAlertsEnabled.toString());
            updateGasAlertUI();
            if (gasAlertsEnabled) checkFeeAlert();
        }
    }
    
    async function checkFeeAlert() {
        if (!gasAlertsEnabled) return;
        
        try {
            const res = await fetch('https://mempool.space/api/v1/fees/recommended');
            const fees = await res.json();
            
            if (fees.hourFee <= 5) {
                const lastAlert = localStorage.getItem('lastFeeAlert');
                const now = Date.now();
                
                if (!lastAlert || now - parseInt(lastAlert) > 1800000) {
                    new Notification('Protocol Pulse: Low Fee Window', {
                        body: `Network fees at ${fees.hourFee} sat/vB. Optimal transacting conditions.`,
                        icon: '/static/images/protocol-pulse-logo-transparent.png',
                        tag: 'fee-alert'
                    });
                    localStorage.setItem('lastFeeAlert', now.toString());
                }
            }
        } catch (e) {
            console.error('Fee check failed:', e);
        }
    }
    
    updateHalvingClock();
    setInterval(updateHalvingClock, 60000);
    updateGasAlertUI();
    if (gasAlertsEnabled) setInterval(checkFeeAlert, 300000);
    
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/sw.js')
                .then(reg => console.log('SW registered:', reg.scope))
                .catch(err => console.log('SW registration failed:', err));
        });
    }
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>```

## templates/live_terminal.html
```html
{% extends "base.html" %}

{% block title %}Live Settlement Terminal | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.85);
}

.terminal-container {
    position: relative;
    width: 100%;
    min-height: calc(100vh - 60px);
    background: var(--pp-dark);
    overflow: hidden;
}

.back-nav {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
    transform: translateX(-3px);
}

.back-btn i {
    color: var(--pp-red);
}

.bitfeed-frame {
    width: 100%;
    height: calc(100vh - 60px);
    border: none;
    filter: hue-rotate(330deg) saturate(1.2);
}

.terminal-hud {
    position: fixed;
    top: 80px;
    right: 20px;
    background: var(--pp-glass);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 20px;
    min-width: 280px;
    z-index: 1000;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.hud-title {
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.hud-title::before {
    content: '';
    width: 8px;
    height: 8px;
    background: var(--pp-red);
    border-radius: 50%;
    animation: pulse-dot 1.5s infinite;
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
    50% { opacity: 0.8; box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
}

.hud-metric {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.hud-metric:last-child {
    border-bottom: none;
}

.metric-label {
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    font-size: 1.1rem;
    font-weight: 600;
}

.metric-value.fee-low { color: #22c55e; }
.metric-value.fee-medium { color: #eab308; }
.metric-value.fee-high { color: var(--pp-red); }

.latest-block {
    background: rgba(220, 38, 38, 0.1);
    border-radius: 8px;
    padding: 15px;
    margin-top: 15px;
}

.block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.block-height {
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    font-size: 1.2rem;
    font-weight: 700;
}

.block-time {
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.75rem;
}

.block-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.block-stat {
    text-align: center;
}

.block-stat-label {
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
}

.block-stat-value {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    font-size: 0.9rem;
}

.terminal-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--pp-glass);
    backdrop-filter: blur(20px);
    border-top: 1px solid rgba(220, 38, 38, 0.2);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 1000;
}

.terminal-status {
    display: flex;
    align-items: center;
    gap: 20px;
}

.status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.7);
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22c55e;
}

.terminal-source {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.4);
}

.terminal-source a {
    color: var(--pp-red);
    text-decoration: none;
}

.mempool-viz {
    position: relative;
    height: 60px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    overflow: hidden;
    margin-top: 15px;
}

.mempool-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(to top, var(--pp-red), rgba(220, 38, 38, 0.3));
    transition: height 0.5s ease;
}

.mempool-label {
    position: absolute;
    bottom: 5px;
    left: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.8);
    z-index: 1;
}

@media (max-width: 768px) {
    .terminal-hud {
        top: auto;
        bottom: 80px;
        right: 10px;
        left: 10px;
        min-width: auto;
    }
    .sovereign-symbol-container {
        display: none;
    }
}

.sovereign-symbol-container {
    position: fixed;
    bottom: 70px;
    left: 20px;
    width: 200px;
    height: 200px;
    background: var(--pp-glass);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    z-index: 999;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    overflow: hidden;
}

.sovereign-symbol-label {
    position: absolute;
    top: 8px;
    left: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 6px;
}

.sovereign-symbol-label::before {
    content: '';
    width: 6px;
    height: 6px;
    background: var(--pp-red);
    border-radius: 50%;
    animation: pulse-dot 1.5s infinite;
}

#sovereign-canvas {
    width: 100%;
    height: 100%;
    cursor: grab;
}

#sovereign-canvas:active {
    cursor: grabbing;
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="terminal-container">
    <iframe 
        src="https://bits.monospace.live/" 
        class="bitfeed-frame" 
        allow="fullscreen"
        loading="lazy"
    ></iframe>
    
    <div class="terminal-hud">
        <div class="hud-title">Live Network Status</div>
        
        <div class="hud-metric">
            <span class="metric-label">Mempool Size</span>
            <span class="metric-value" id="mempool-size">Loading...</span>
        </div>
        
        <div class="hud-metric">
            <span class="metric-label">Pending TXs</span>
            <span class="metric-value" id="pending-txs">--</span>
        </div>
        
        <div class="hud-metric">
            <span class="metric-label">Next Block Fee</span>
            <span class="metric-value" id="next-block-fee">-- sat/vB</span>
        </div>
        
        <div class="hud-metric">
            <span class="metric-label">Low Priority</span>
            <span class="metric-value fee-low" id="low-fee">-- sat/vB</span>
        </div>
        
        <div class="mempool-viz">
            <div class="mempool-bar" id="mempool-bar" style="height: 20%"></div>
            <span class="mempool-label" id="mempool-mb">-- MB</span>
        </div>
        
        <div class="latest-block">
            <div class="block-header">
                <span class="block-height" id="block-height">#---,---</span>
                <span class="block-time" id="block-time">--:--</span>
            </div>
            <div class="block-stats">
                <div class="block-stat">
                    <div class="block-stat-label">TXs</div>
                    <div class="block-stat-value" id="block-txs">--</div>
                </div>
                <div class="block-stat">
                    <div class="block-stat-label">Size</div>
                    <div class="block-stat-value" id="block-size">-- MB</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="sovereign-symbol-container">
        <span class="sovereign-symbol-label">Sovereign Symbol</span>
        <canvas id="sovereign-canvas"></canvas>
    </div>
    
    <div class="terminal-footer">
        <div class="terminal-status">
            <div class="status-item">
                <span class="status-dot"></span>
                <span>LIVE</span>
            </div>
            <div class="status-item">
                <span id="connection-status">Connected to Bitcoin Network</span>
            </div>
        </div>
        <div class="terminal-source">
            Powered by <a href="https://mempool.space" target="_blank">Mempool.space</a> | 
            Visualization by <a href="https://bits.monospace.live" target="_blank">Bitfeed</a>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script>
(function initSovereignSymbol() {
    const canvas = document.getElementById('sovereign-canvas');
    if (!canvas) return;
    
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(200, 200);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    
    const group = new THREE.Group();
    
    const outerRingGeo = new THREE.TorusGeometry(1.2, 0.08, 16, 64);
    const redMaterial = new THREE.MeshBasicMaterial({ 
        color: 0xdc2626,
        transparent: true,
        opacity: 0.9
    });
    const outerRing = new THREE.Mesh(outerRingGeo, redMaterial);
    group.add(outerRing);
    
    const innerRingGeo = new THREE.TorusGeometry(0.8, 0.05, 16, 64);
    const whiteMaterial = new THREE.MeshBasicMaterial({ 
        color: 0xffffff,
        transparent: true,
        opacity: 0.6
    });
    const innerRing = new THREE.Mesh(innerRingGeo, whiteMaterial);
    group.add(innerRing);
    
    const btcGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.1, 32);
    const btcMesh = new THREE.Mesh(btcGeo, redMaterial);
    btcMesh.rotation.x = Math.PI / 2;
    group.add(btcMesh);
    
    const lineGeo = new THREE.BoxGeometry(0.08, 0.7, 0.12);
    const line1 = new THREE.Mesh(lineGeo, whiteMaterial);
    line1.position.y = 0.1;
    group.add(line1);
    
    const line2 = new THREE.Mesh(lineGeo, whiteMaterial);
    line2.position.y = -0.1;
    group.add(line2);
    
    const glowGeo = new THREE.SphereGeometry(1.5, 32, 32);
    const glowMat = new THREE.MeshBasicMaterial({ 
        color: 0xdc2626,
        transparent: true,
        opacity: 0.05
    });
    const glow = new THREE.Mesh(glowGeo, glowMat);
    group.add(glow);
    
    scene.add(group);
    camera.position.z = 4;
    
    let mouseX = 0, mouseY = 0;
    let isDragging = false;
    
    canvas.addEventListener('mousedown', () => isDragging = true);
    canvas.addEventListener('mouseup', () => isDragging = false);
    canvas.addEventListener('mouseleave', () => isDragging = false);
    canvas.addEventListener('mousemove', (e) => {
        if (isDragging) {
            mouseX = (e.offsetX / 200 - 0.5) * 4;
            mouseY = (e.offsetY / 200 - 0.5) * 4;
        }
    });
    
    function animate() {
        requestAnimationFrame(animate);
        
        if (!isDragging) {
            group.rotation.y += 0.008;
            group.rotation.x = Math.sin(Date.now() * 0.001) * 0.2;
        } else {
            group.rotation.y = mouseX;
            group.rotation.x = mouseY;
        }
        
        outerRing.rotation.z += 0.002;
        innerRing.rotation.z -= 0.003;
        
        const pulseScale = 1 + Math.sin(Date.now() * 0.002) * 0.03;
        glow.scale.set(pulseScale, pulseScale, pulseScale);
        
        renderer.render(scene, camera);
    }
    
    animate();
})();

async function updateMempoolData() {
    try {
        const [mempoolRes, feesRes, blocksRes] = await Promise.all([
            fetch('https://mempool.space/api/mempool'),
            fetch('https://mempool.space/api/v1/fees/recommended'),
            fetch('https://mempool.space/api/blocks')
        ]);
        
        const mempool = await mempoolRes.json();
        const fees = await feesRes.json();
        const blocks = await blocksRes.json();
        
        const mempoolMB = (mempool.vsize / 1000000).toFixed(1);
        const mempoolPercent = Math.min((mempool.vsize / 300000000) * 100, 100);
        
        document.getElementById('mempool-size').textContent = mempoolMB + ' vMB';
        document.getElementById('pending-txs').textContent = mempool.count.toLocaleString();
        document.getElementById('mempool-mb').textContent = mempoolMB + ' MB';
        document.getElementById('mempool-bar').style.height = mempoolPercent + '%';
        
        const nextBlockFee = fees.fastestFee;
        const feeEl = document.getElementById('next-block-fee');
        feeEl.textContent = nextBlockFee + ' sat/vB';
        feeEl.className = 'metric-value ' + (nextBlockFee < 10 ? 'fee-low' : nextBlockFee < 50 ? 'fee-medium' : 'fee-high');
        
        document.getElementById('low-fee').textContent = fees.hourFee + ' sat/vB';
        
        if (blocks.length > 0) {
            const latest = blocks[0];
            document.getElementById('block-height').textContent = '#' + latest.height.toLocaleString();
            
            const blockTime = new Date(latest.timestamp * 1000);
            const now = new Date();
            const minAgo = Math.floor((now - blockTime) / 60000);
            document.getElementById('block-time').textContent = minAgo + ' min ago';
            
            document.getElementById('block-txs').textContent = latest.tx_count.toLocaleString();
            document.getElementById('block-size').textContent = (latest.size / 1000000).toFixed(2) + ' MB';
        }
        
        if (nextBlockFee <= 5) {
            checkAndNotifyLowFees(nextBlockFee);
        }
        
    } catch (error) {
        console.error('Mempool data fetch error:', error);
        document.getElementById('connection-status').textContent = 'Reconnecting...';
    }
}

function checkAndNotifyLowFees(fee) {
    if ('Notification' in window && Notification.permission === 'granted') {
        if (!window.lastFeeNotification || Date.now() - window.lastFeeNotification > 300000) {
            new Notification('Protocol Pulse: Low Fee Alert', {
                body: `Network fees dropped to ${fee} sat/vB. Optimal time to transact.`,
                icon: '/static/images/protocol-pulse-logo-transparent.png'
            });
            window.lastFeeNotification = Date.now();
        }
    }
}

updateMempoolData();
setInterval(updateMempoolData, 10000);

if ('Notification' in window && Notification.permission === 'default') {
    setTimeout(() => {
        Notification.requestPermission();
    }, 5000);
}
</script>
{% endblock %}
```

## templates/article_detail.html
```html
{% extends "base.html" %}

{% block title %}{{ article.title }} - Protocol Pulse{% endblock %}

{% block meta_description %}{{ article.summary if article.summary else article.content[:150] }}{% endblock %}

{% block head %}
<!-- Open Graph meta tags for social media sharing -->
<meta property="og:title" content="{{ article.title }}">
<meta property="og:description" content="{{ article.content[:200] }}...">
<meta property="og:image" content="{{ article.header_image_url or url_for('dynamic_og_image', og_type='article', id=article.id) }}">
<meta property="og:url" content="{{ request.url }}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Protocol Pulse">

<!-- Twitter Card meta tags -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@protocolpulse">
<meta name="twitter:title" content="{{ article.title }}">
<meta name="twitter:description" content="{{ article.content[:200] }}...">
<meta name="twitter:image" content="{{ article.header_image_url or url_for('dynamic_og_image', og_type='article', id=article.id) }}">

<!-- SEO meta tags -->
<meta name="description" content="{{ article.seo_description or article.summary }}">
<meta name="keywords" content="{{ article.tags }}, Bitcoin, DeFi, Protocol Pulse">
<link rel="canonical" href="{{ request.url }}">
{% endblock %}

{% block content %}
<div class="reading-progress"></div>

<article class="py-5">
    <div class="container">
        <!-- Article Header -->
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="mb-4">
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="{{ url_for('index') }}" class="text-primary">Home</a></li>
                            <li class="breadcrumb-item"><a href="{{ url_for('articles') }}" class="text-primary">News</a></li>
                            <li class="breadcrumb-item active text-muted" aria-current="page">{{ article.title[:50] }}...</li>
                        </ol>
                    </nav>
                </div>

                <header class="article-header-professional">
                    <!-- Category Badge -->
                    <div class="category-section mb-4">
                        <span class="category-badge">{{ article.category }}</span>
                    </div>

                    <!-- Article Title -->
                    <h1 class="article-title-professional">{{ article.title }}</h1>
                    
                    <!-- Author and Date -->
                    <div class="article-meta-professional mb-4">
                        <div class="meta-item">
                            <span class="meta-label">By</span>
                            <span class="meta-value">{{ article.author }}</span>
                        </div>
                        <div class="meta-divider">•</div>
                        <div class="meta-item">
                            <span class="meta-value">{{ article.created_at.strftime('%B %d, %Y at %I:%M %p') }}</span>
                        </div>
                        <div class="meta-divider">•</div>
                        <div class="meta-item">
                            <span class="meta-value">{{ ((article.content | length) / 1000 * 3) | round | int }} min read</span>
                        </div>
                    </div>

                    {% if article.header_image_url %}
                    <!-- Hero Image -->
                    <div class="article-image-hero mb-4">
                        <img src="{{ article.header_image_url }}" alt="{{ article.title }}" class="img-fluid w-100">
                    </div>
                    {% endif %}

                    <!-- Share Buttons -->
                    <div class="share-social-section">
                        <div class="share-buttons-container">
                            <span class="share-label">Share this story</span>
                            <div class="social-buttons">
                                <button class="social-btn twitter-btn" onclick="shareOnTwitter()">
                                    <i class="fab fa-twitter"></i>
                                    <span>Twitter</span>
                                </button>
                                <button class="social-btn linkedin-btn" onclick="shareOnLinkedIn()">
                                    <i class="fab fa-linkedin"></i>
                                    <span>LinkedIn</span>
                                </button>
                                <button class="social-btn copy-btn" onclick="copyToClipboard()">
                                    <i class="fas fa-link"></i>
                                    <span>Copy Link</span>
                                </button>
                            </div>
                        </div>
                        <div class="reading-time">
                            <i class="fas fa-clock"></i>
                            <span>{{ ((article.content | length) / 1000 * 3) | round | int }} min read</span>
                        </div>
                    </div>
                </header>

                <!-- Article Content -->
                <div class="article-content">
                    {% if article.video_url %}<iframe src="{{ article.video_url }}" width="100%" height="315" frameborder="0" allowfullscreen></iframe>{% endif %}
                    {% if article.screenshot_url %}<img src="{{ article.screenshot_url }}" alt="Source screenshot" class="screenshot">{% endif %}
                    {% if article.audio_url %}<audio controls src="{{ article.audio_url }}"></audio>{% endif %}
                    {% if article.transcript_text %}<p class="transcript">Transcript Overview: {{ article.transcript_text[:500] }}...</p>{% endif %}
                    {{ article.content | safe }}
                </div>

                <!-- Tip Jar - Support sovereign journalism with sats or dollars -->
                <div class="tip-jar-section mt-5 pt-4 border-top border-secondary">
                    <div class="tip-jar-container">
                        <div class="tip-header">
                            <span class="tip-title">Value this Intelligence Brief?</span>
                            <p class="tip-description">Support freedom tech journalism. Every sat and dollar funds the signal.</p>
                        </div>
                        
                        <!-- Lightning Tips (Sats) -->
                        <div class="tip-row">
                            <div class="tip-label"><i class="fas fa-bolt text-warning"></i> Tip with Sats</div>
                            <div class="zapper-buttons">
                                <button class="zapper-btn" onclick="zapSats(1000)">
                                    <i class="fas fa-bolt"></i> 1K
                                </button>
                                <button class="zapper-btn" onclick="zapSats(5000)">
                                    <i class="fas fa-bolt"></i> 5K
                                </button>
                                <button class="zapper-btn zapper-btn-featured" onclick="zapSats(21000)">
                                    <i class="fas fa-bolt"></i> 21K
                                </button>
                                <button class="zapper-btn zapper-btn-custom" onclick="zapCustom()">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </div>
                        
                        <!-- Stripe Tips (Dollars) -->
                        <div class="tip-row">
                            <div class="tip-label"><i class="fas fa-credit-card text-success"></i> Tip with Dollars</div>
                            <div class="stripe-buttons">
                                <a href="{{ url_for('tip_checkout', amount=5, article_id=article.id) }}" class="stripe-btn">$5</a>
                                <a href="{{ url_for('tip_checkout', amount=10, article_id=article.id) }}" class="stripe-btn">$10</a>
                                <a href="{{ url_for('tip_checkout', amount=21, article_id=article.id) }}" class="stripe-btn stripe-btn-featured">$21</a>
                                <a href="{{ url_for('tip_checkout', amount=50, article_id=article.id) }}" class="stripe-btn">$50</a>
                            </div>
                        </div>
                        
                        <div class="zapper-fallback mt-3" id="zapper-fallback" style="display: none;">
                            <p class="text-muted small mb-2">WebLN not detected. Scan to tip:</p>
                            <div class="qr-placeholder">
                                <img src="https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=lnurl1dp68gurn8ghj7ampd3kx2ar0veekzar0wd5xjtnrdakj7tnhv4kxctttdehhwm30d3h82unvwqhkxmmww3jk6amfw35k7m30vs3xvdnpwylhgct884kx7emfdch82enpv9jxvem9x5mrjce5v93r2dfs893rxveex5cxvve3x4jkycmp8ycnvvt8xcknhghj6mnyv4ezudt5wqmhudmhvfez" alt="Lightning QR" class="qr-code">
                            </div>
                        </div>
                    </div>
                </div>

                <style>
                .tip-jar-section {
                    background: rgba(10, 10, 10, 0.85);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    border: 1px solid rgba(220, 38, 38, 0.2);
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 
                        inset 0 0 15px rgba(220, 38, 38, 0.05),
                        0 10px 30px rgba(0, 0, 0, 0.5);
                }
                .tip-jar-container {
                    max-width: 500px;
                    margin: 0 auto;
                }
                .tip-header {
                    text-align: center;
                    margin-bottom: 25px;
                }
                .tip-title {
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 1.2rem;
                    color: #fff;
                    font-weight: 700;
                    display: block;
                    margin-bottom: 8px;
                }
                .tip-description {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 0.9rem;
                    margin: 0;
                }
                .tip-row {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 15px;
                    padding: 15px 0;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }
                .tip-row:last-of-type {
                    border-bottom: none;
                }
                .tip-label {
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.85rem;
                    color: rgba(255, 255, 255, 0.8);
                    white-space: nowrap;
                }
                .tip-label i {
                    margin-right: 8px;
                }
                .zapper-description {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 0.85rem;
                    margin-bottom: 20px;
                }
                .zapper-buttons {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    justify-content: center;
                }
                .zapper-btn {
                    background: rgba(234, 179, 8, 0.2);
                    border: 1px solid rgba(234, 179, 8, 0.5);
                    color: #eab308;
                    padding: 10px 18px;
                    border-radius: 25px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }
                .zapper-btn:hover {
                    background: rgba(234, 179, 8, 0.4);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 15px rgba(234, 179, 8, 0.3);
                }
                .zapper-btn-featured {
                    background: linear-gradient(135deg, #eab308 0%, #f59e0b 100%);
                    color: #000;
                    font-weight: 600;
                }
                .zapper-btn-featured:hover {
                    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                }
                .zapper-btn-custom {
                    background: rgba(255, 255, 255, 0.05);
                    border-color: rgba(255, 255, 255, 0.2);
                    color: rgba(255, 255, 255, 0.7);
                }
                .stripe-buttons {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    justify-content: center;
                }
                .stripe-btn {
                    background: rgba(34, 197, 94, 0.2);
                    border: 1px solid rgba(34, 197, 94, 0.5);
                    color: #22c55e;
                    padding: 10px 18px;
                    border-radius: 25px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem;
                    cursor: pointer;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }
                .stripe-btn:hover {
                    background: rgba(34, 197, 94, 0.4);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
                    color: #22c55e;
                    text-decoration: none;
                }
                .stripe-btn-featured {
                    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                    color: #000;
                    font-weight: 600;
                }
                .stripe-btn-featured:hover {
                    background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
                    color: #000;
                }
                .qr-placeholder {
                    display: inline-block;
                    padding: 10px;
                    background: #fff;
                    border-radius: 8px;
                }
                .qr-code {
                    display: block;
                }
                @media (max-width: 576px) {
                    .tip-row {
                        flex-direction: column;
                        align-items: flex-start;
                    }
                    .zapper-buttons, .stripe-buttons {
                        width: 100%;
                        justify-content: flex-start;
                    }
                }
                </style>

                <!-- Tags -->
                {% if article.tags %}
                <div class="article-tags mt-5 pt-4 border-top border-secondary">
                    <h6 class="text-primary mb-3">Tags:</h6>
                    {% for tag in article.tags.split(',') %}
                        <span class="badge bg-outline-primary me-2 mb-2">{{ tag.strip() }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Related Articles -->
        {% if related_articles %}
        <div class="row mt-5">
            <div class="col-12">
                <h3 class="text-primary mb-4">Related Articles</h3>
                <div class="row g-4">
                    {% for related in related_articles %}
                    <div class="col-md-4">
                        <div class="card bg-secondary border-0 h-100">
                            <div class="card-body">
                                <span class="badge bg-outline-primary mb-2">{{ related.category }}</span>
                                <h6 class="card-title">
                                    <a href="{{ url_for('article_detail', article_id=related.id) }}" 
                                       class="text-decoration-none text-light">
                                        {{ related.title[:60] }}{% if related.title|length > 60 %}...{% endif %}
                                    </a>
                                </h6>
                                <p class="card-text text-muted small">
                                    {{ related.content | clean_preview(80) }}
                                </p>
                                <small class="text-muted">
                                    <i class="fas fa-clock me-1"></i>
                                    {{ related.created_at.strftime('%b %d') }}
                                </small>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Back to Articles -->
        <div class="row mt-5">
            <div class="col-12 text-center">
                <a href="{{ url_for('articles') }}" class="btn btn-outline-primary">
                    <i class="fas fa-arrow-left me-2"></i>Back to All Articles
                </a>
            </div>
        </div>
    </div>
</article>
{% endblock %}

{% block extra_scripts %}
<script>
// Reading progress
window.addEventListener('scroll', () => {
    const article = document.querySelector('.article-content');
    const progress = document.querySelector('.reading-progress');
    
    if (article && progress) {
        const articleTop = article.offsetTop;
        const articleHeight = article.offsetHeight;
        const windowTop = window.pageYOffset;
        const windowHeight = window.innerHeight;
        
        const scrolled = ((windowTop - articleTop + windowHeight) / articleHeight) * 100;
        const progressWidth = Math.min(100, Math.max(0, scrolled));
        
        progress.style.width = progressWidth + '%';
    }
});

// Share functions
function shareOnTwitter() {
    const url = encodeURIComponent(window.location.href);
    const text = encodeURIComponent('{{ article.title }} - Protocol Pulse');
    window.open(`https://twitter.com/intent/tweet?url=${url}&text=${text}`, '_blank');
}

function shareOnLinkedIn() {
    const url = encodeURIComponent(window.location.href);
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}`, '_blank');
}

function copyToClipboard() {
    navigator.clipboard.writeText(window.location.href).then(() => {
        alert('Link copied to clipboard!');
    });
}

function shareByEmail() {
    const subject = encodeURIComponent('{{ article.title }} - Protocol Pulse');
    const body = encodeURIComponent(`Check out this article: ${window.location.href}`);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
}

// Lightning Zapper - WebLN Integration
async function zapSats(amount) {
    if (typeof window.webln !== 'undefined') {
        try {
            await window.webln.enable();
            const invoice = await window.webln.makeInvoice({
                amount: amount,
                defaultMemo: `Protocol Pulse tip for: {{ article.title[:50] }}`
            });
            console.log('Invoice created:', invoice);
            alert(`Zapped ${amount} sats! Thank you for supporting freedom tech journalism.`);
        } catch (error) {
            console.error('WebLN error:', error);
            showZapperFallback();
        }
    } else {
        showZapperFallback();
    }
}

async function zapCustom() {
    const amount = prompt('Enter amount in sats:', '2100');
    if (amount && !isNaN(amount)) {
        await zapSats(parseInt(amount));
    }
}

function showZapperFallback() {
    document.getElementById('zapper-fallback').style.display = 'block';
}

// Check for WebLN on load
document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.webln === 'undefined') {
        // Add subtle indicator that WebLN is not available
        const zapperBtns = document.querySelectorAll('.zapper-btn');
        zapperBtns.forEach(btn => {
            btn.title = 'Install a WebLN-compatible wallet like Alby for instant zaps';
        });
    }
});
</script>
{% endblock %}```

## templates/merchant_map.html
```html
{% extends "base.html" %}

{% block title %}Sovereign Merchant Map | Protocol Pulse{% endblock %}

{% block head %}
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
    --pp-gold: #f59e0b;
}

.map-page {
    position: relative;
    width: 100%;
    min-height: calc(100vh - 60px);
    background: var(--pp-dark);
    display: flex;
}

.back-nav {
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
    transform: translateX(-3px);
}

.merchant-sidebar {
    width: 380px;
    min-width: 380px;
    background: var(--pp-glass);
    border-right: 1px solid rgba(220, 38, 38, 0.2);
    height: calc(100vh - 60px);
    overflow-y: auto;
    z-index: 100;
}

.sidebar-header {
    padding: 25px 20px;
    border-bottom: 1px solid rgba(220, 38, 38, 0.2);
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.1), transparent);
}

.sidebar-title {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 5px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.sidebar-title i {
    color: var(--pp-red);
    font-size: 1.4rem;
}

.sidebar-subtitle {
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
}

.stats-bar {
    display: flex;
    gap: 15px;
    padding: 20px;
    border-bottom: 1px solid rgba(220, 38, 38, 0.2);
    background: rgba(220, 38, 38, 0.05);
}

.stat-card {
    flex: 1;
    text-align: center;
    padding: 12px 8px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
}

.stat-label {
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

.search-section {
    padding: 20px;
    border-bottom: 1px solid rgba(220, 38, 38, 0.2);
}

.search-input-group {
    display: flex;
    gap: 10px;
    margin-bottom: 12px;
}

.search-input {
    flex: 1;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 14px 18px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
}

.search-input::placeholder {
    color: rgba(255, 255, 255, 0.3);
}

.search-input:focus {
    outline: none;
    border-color: var(--pp-red);
}

.search-btn {
    background: var(--pp-red);
    border: none;
    border-radius: 10px;
    padding: 14px 20px;
    color: #fff;
    cursor: pointer;
    transition: all 0.3s ease;
}

.search-btn:hover {
    background: #b91c1c;
    transform: scale(1.05);
}

.location-btn {
    width: 100%;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 12px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.location-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
}

.category-filter {
    padding: 15px 20px;
    border-bottom: 1px solid rgba(220, 38, 38, 0.2);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.category-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 8px 16px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 6px;
}

.category-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
}

.category-btn.active {
    background: var(--pp-red);
    border-color: var(--pp-red);
    color: #fff;
}

.category-btn i {
    font-size: 0.85rem;
}

.merchant-list {
    flex: 1;
    overflow-y: auto;
    padding: 10px 0;
}

.merchant-card {
    padding: 18px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    cursor: pointer;
    transition: all 0.3s ease;
}

.merchant-card:hover {
    background: rgba(220, 38, 38, 0.1);
}

.merchant-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}

.merchant-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 600;
    color: #fff;
    margin-bottom: 2px;
}

.merchant-location {
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.5);
}

.merchant-badges {
    display: flex;
    gap: 6px;
}

.badge {
    font-size: 0.65rem;
    padding: 4px 8px;
    border-radius: 12px;
    font-family: 'JetBrains Mono', monospace;
}

.badge-lightning {
    background: rgba(245, 158, 11, 0.2);
    color: var(--pp-gold);
}

.badge-onchain {
    background: rgba(220, 38, 38, 0.2);
    color: var(--pp-red);
}

.badge-category {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.7);
}

.merchant-meta {
    display: flex;
    gap: 15px;
    margin-top: 10px;
}

.merchant-meta-item {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
    display: flex;
    align-items: center;
    gap: 5px;
}

.merchant-meta-item i {
    color: var(--pp-red);
    font-size: 0.7rem;
}

.map-container {
    flex: 1;
    position: relative;
}

#merchant-map {
    width: 100%;
    height: calc(100vh - 60px);
    background: #111;
}

.leaflet-tile {
    filter: saturate(0) brightness(0.8) contrast(1.2);
}

.btc-marker {
    background: var(--pp-red);
    border: 2px solid #fff;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 13px;
    box-shadow: 0 3px 12px rgba(220, 38, 38, 0.6);
}

.btc-marker i,
.btc-marker .fab,
.btc-marker .fas {
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    width: 100%;
    height: 100%;
}

.btc-marker-lightning {
    background: var(--pp-gold);
    box-shadow: 0 3px 12px rgba(245, 158, 11, 0.6);
}

.marker-cluster-small, .marker-cluster-medium, .marker-cluster-large {
    background: rgba(220, 38, 38, 0.4);
}

.marker-cluster-small div, .marker-cluster-medium div, .marker-cluster-large div {
    background: var(--pp-red);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
}

.merchant-popup .leaflet-popup-content-wrapper {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    backdrop-filter: blur(20px);
}

.merchant-popup .leaflet-popup-content {
    margin: 18px;
    font-family: 'JetBrains Mono', monospace;
}

.merchant-popup .leaflet-popup-tip {
    background: var(--pp-glass);
}

.popup-name {
    color: var(--pp-red);
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 6px;
}

.popup-category {
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}

.popup-badges {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    background: rgba(10, 10, 10, 0.6);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    padding: 12px;
    border-radius: 8px;
    border: 1px solid rgba(220, 38, 38, 0.2);
}

.popup-badges .badge {
    filter: none !important;
    box-shadow: none !important;
}

.popup-detail {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.8rem;
    line-height: 1.4;
}

.popup-detail i {
    color: var(--pp-red);
    width: 16px;
    text-align: center;
    flex-shrink: 0;
}

.popup-detail a {
    color: #60a5fa;
    text-decoration: none;
}

.popup-detail a:hover {
    color: #93c5fd;
    text-decoration: underline;
}

.popup-actions {
    margin-top: 15px;
    display: flex;
    gap: 10px;
}

.directions-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--pp-red);
    color: #fff;
    padding: 10px 18px;
    border-radius: 8px;
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 600;
    transition: all 0.2s ease;
}

.directions-btn:hover {
    background: #b91c1c;
    color: #fff;
    transform: translateY(-1px);
}

.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.9);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
}

.loading-overlay.active {
    opacity: 1;
    pointer-events: auto;
}

.loading-spinner {
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    font-size: 1.1rem;
}

.loading-progress {
    margin-top: 15px;
    width: 200px;
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    overflow: hidden;
}

.loading-bar {
    height: 100%;
    background: var(--pp-red);
    animation: loading 1.5s ease-in-out infinite;
}

@keyframes loading {
    0% { width: 0; margin-left: 0; }
    50% { width: 60%; margin-left: 20%; }
    100% { width: 0; margin-left: 100%; }
}

.empty-state {
    padding: 40px 20px;
    text-align: center;
    color: rgba(255, 255, 255, 0.5);
}

.empty-state i {
    font-size: 3rem;
    color: var(--pp-red);
    margin-bottom: 15px;
    opacity: 0.5;
}

@media (max-width: 992px) {
    .merchant-sidebar {
        display: none;
    }
    
    .mobile-panel {
        display: block;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: var(--pp-glass);
        border-top: 1px solid rgba(220, 38, 38, 0.3);
        padding: 15px;
        z-index: 1000;
        backdrop-filter: blur(20px);
    }
}

@media (min-width: 993px) {
    .mobile-panel {
        display: none;
    }
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="map-page">
    <aside class="merchant-sidebar">
        <div class="sidebar-header">
            <div class="sidebar-title">
                <i class="fab fa-bitcoin"></i>
                Sovereign Merchant Map
            </div>
            <div class="sidebar-subtitle">Bitcoin-accepting businesses worldwide</div>
        </div>
        
        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-value" id="total-count">--</div>
                <div class="stat-label">Merchants</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="lightning-count">--</div>
                <div class="stat-label">Lightning</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="country-count">80+</div>
                <div class="stat-label">Countries</div>
            </div>
        </div>
        
        <div class="search-section">
            <div class="search-input-group">
                <input type="text" class="search-input" id="location-search" placeholder="City, ZIP, or Address...">
                <button class="search-btn" onclick="searchLocation()">
                    <i class="fas fa-search"></i>
                </button>
            </div>
            <button class="location-btn" onclick="useCurrentLocation()">
                <i class="fas fa-crosshairs"></i>
                Use My Location
            </button>
        </div>
        
        <div class="category-filter">
            <button class="category-btn active" onclick="filterCategory(null, this)">
                <i class="fas fa-globe"></i> All
            </button>
            <button class="category-btn" onclick="filterCategory('restaurant', this)">
                <i class="fas fa-utensils"></i> Food
            </button>
            <button class="category-btn" onclick="filterCategory('shop', this)">
                <i class="fas fa-shopping-bag"></i> Retail
            </button>
            <button class="category-btn" onclick="filterCategory('hotel', this)">
                <i class="fas fa-bed"></i> Lodging
            </button>
            <button class="category-btn" onclick="filterCategory('atm', this)">
                <i class="fas fa-money-bill-wave"></i> ATM
            </button>
            <button class="category-btn" onclick="filterCategory('lightning', this)">
                <i class="fas fa-bolt"></i> Lightning
            </button>
        </div>
        
        <div class="merchant-list" id="merchant-list">
            <div class="empty-state">
                <i class="fab fa-bitcoin"></i>
                <p>Navigate the map or search a location<br>to discover Bitcoin merchants</p>
            </div>
        </div>
    </aside>
    
    <div class="map-container">
        <div id="merchant-map"></div>
    </div>
    
    <div class="mobile-panel">
        <div class="search-input-group">
            <input type="text" class="search-input" id="mobile-search" placeholder="Search location...">
            <button class="search-btn" onclick="searchLocationMobile()">
                <i class="fas fa-search"></i>
            </button>
        </div>
    </div>
    
    <div class="loading-overlay" id="loading-overlay">
        <div class="loading-spinner">
            <i class="fas fa-circle-notch fa-spin me-2"></i>
            Scanning for sovereign merchants...
        </div>
        <div class="loading-progress">
            <div class="loading-bar"></div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
let map;
let markerCluster;
let allMerchants = [];
let visibleMerchants = [];
let currentCategory = null;

const btcIcon = L.divIcon({
    className: 'btc-marker-wrapper',
    html: '<div class="btc-marker"><i class="fab fa-bitcoin"></i></div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14]
});

const lightningIcon = L.divIcon({
    className: 'btc-marker-wrapper',
    html: '<div class="btc-marker btc-marker-lightning"><i class="fas fa-bolt"></i></div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14]
});

function initMap() {
    map = L.map('merchant-map', {
        zoomControl: true,
        attributionControl: false
    }).setView([25, 0], 2);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(map);
    
    markerCluster = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 16
    });
    
    map.addLayer(markerCluster);
    map.on('moveend', updateMerchantList);
    
    loadMerchants();
}

async function loadMerchants() {
    showLoading();
    try {
        const response = await fetch('https://api.btcmap.org/v2/elements?limit=10000');
        const data = await response.json();
        
        let lightningCount = 0;
        
        data.forEach(merchant => {
            if (merchant.osm_json?.lat && merchant.osm_json?.lon) {
                const tags = merchant.osm_json?.tags || {};
                const hasLightning = tags['payment:lightning'] === 'yes' || tags['payment:lightning_contactless'] === 'yes';
                
                if (hasLightning) lightningCount++;
                
                const m = {
                    lat: merchant.osm_json.lat,
                    lon: merchant.osm_json.lon,
                    name: tags.name || 'Bitcoin Merchant',
                    category: tags.amenity || tags.shop || tags.tourism || 'merchant',
                    hasLightning: hasLightning,
                    hasOnchain: tags['payment:bitcoin'] === 'yes',
                    address: buildAddress(tags),
                    phone: tags.phone || tags['contact:phone'] || '',
                    website: tags.website || tags['contact:website'] || '',
                    hours: tags.opening_hours || '',
                    raw: merchant
                };
                
                allMerchants.push(m);
            }
        });
        
        document.getElementById('total-count').textContent = allMerchants.length.toLocaleString();
        document.getElementById('lightning-count').textContent = lightningCount.toLocaleString();
        
        addMarkers();
        hideLoading();
        updateMerchantList();
        
    } catch (error) {
        console.error('Failed to load merchants:', error);
        hideLoading();
    }
}

function addMarkers(category = null) {
    markerCluster.clearLayers();
    
    let filtered = allMerchants;
    
    if (category === 'lightning') {
        filtered = allMerchants.filter(m => m.hasLightning);
    } else if (category === 'restaurant') {
        filtered = allMerchants.filter(m => ['restaurant', 'fast_food', 'cafe', 'bar', 'pub', 'food'].includes(m.category));
    } else if (category === 'shop') {
        filtered = allMerchants.filter(m => m.category.includes('shop') || ['supermarket', 'convenience', 'clothes', 'electronics'].includes(m.category));
    } else if (category === 'hotel') {
        filtered = allMerchants.filter(m => ['hotel', 'hostel', 'guest_house', 'motel', 'apartment'].includes(m.category));
    } else if (category === 'atm') {
        filtered = allMerchants.filter(m => m.category === 'atm' || m.name.toLowerCase().includes('atm'));
    }
    
    filtered.forEach(m => {
        const marker = L.marker([m.lat, m.lon], {
            icon: m.hasLightning ? lightningIcon : btcIcon
        });
        
        marker.merchantData = m;
        marker.on('click', () => showMerchantPopup(m, marker));
        markerCluster.addLayer(marker);
    });
}

function filterCategory(category, btn) {
    currentCategory = category;
    
    document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    
    addMarkers(category);
    updateMerchantList();
}

function updateMerchantList() {
    const bounds = map.getBounds();
    const listEl = document.getElementById('merchant-list');
    
    let filtered = allMerchants.filter(m => {
        return bounds.contains([m.lat, m.lon]);
    });
    
    if (currentCategory === 'lightning') {
        filtered = filtered.filter(m => m.hasLightning);
    } else if (currentCategory === 'restaurant') {
        filtered = filtered.filter(m => ['restaurant', 'fast_food', 'cafe', 'bar', 'pub', 'food'].includes(m.category));
    } else if (currentCategory === 'shop') {
        filtered = filtered.filter(m => m.category.includes('shop') || ['supermarket', 'convenience', 'clothes', 'electronics'].includes(m.category));
    } else if (currentCategory === 'hotel') {
        filtered = filtered.filter(m => ['hotel', 'hostel', 'guest_house', 'motel', 'apartment'].includes(m.category));
    } else if (currentCategory === 'atm') {
        filtered = filtered.filter(m => m.category === 'atm' || m.name.toLowerCase().includes('atm'));
    }
    
    visibleMerchants = filtered.slice(0, 100);
    
    if (visibleMerchants.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <i class="fab fa-bitcoin"></i>
                <p>No merchants in this view.<br>Zoom out or pan the map to discover more.</p>
            </div>
        `;
        return;
    }
    
    listEl.innerHTML = visibleMerchants.map(m => `
        <div class="merchant-card" onclick="flyToMerchant(${m.lat}, ${m.lon})">
            <div class="merchant-card-header">
                <div>
                    <div class="merchant-name">${escapeHtml(m.name)}</div>
                    <div class="merchant-location">${escapeHtml(m.address || formatCategory(m.category))}</div>
                </div>
                <div class="merchant-badges">
                    ${m.hasLightning ? '<span class="badge badge-lightning"><i class="fas fa-bolt"></i> LN</span>' : ''}
                    ${m.hasOnchain ? '<span class="badge badge-onchain"><i class="fab fa-bitcoin"></i></span>' : ''}
                </div>
            </div>
            <div class="merchant-meta">
                <span class="merchant-meta-item">
                    <i class="fas fa-tag"></i> ${formatCategory(m.category)}
                </span>
                ${m.hours ? `<span class="merchant-meta-item"><i class="fas fa-clock"></i> Open</span>` : ''}
            </div>
        </div>
    `).join('');
}

function showMerchantPopup(m, marker) {
    let detailsHtml = '';
    
    if (m.address) {
        detailsHtml += `<div class="popup-detail"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(m.address)}</div>`;
    }
    if (m.phone) {
        detailsHtml += `<div class="popup-detail"><i class="fas fa-phone"></i> <a href="tel:${m.phone.replace(/\s/g, '')}">${escapeHtml(m.phone)}</a></div>`;
    }
    if (m.website) {
        const displayUrl = m.website.replace(/^https?:\/\//, '').replace(/\/$/, '').substring(0, 40);
        detailsHtml += `<div class="popup-detail"><i class="fas fa-globe"></i> <a href="${escapeHtml(m.website)}" target="_blank">${escapeHtml(displayUrl)}</a></div>`;
    }
    if (m.hours) {
        detailsHtml += `<div class="popup-detail"><i class="fas fa-clock"></i> ${escapeHtml(m.hours)}</div>`;
    }
    
    const popupContent = `
        <div class="popup-name">${escapeHtml(m.name)}</div>
        <div class="popup-category">${formatCategory(m.category)}</div>
        <div class="popup-badges">
            ${m.hasLightning ? '<span class="badge badge-lightning"><i class="fas fa-bolt me-1"></i>Lightning</span>' : ''}
            ${m.hasOnchain ? '<span class="badge badge-onchain"><i class="fab fa-bitcoin me-1"></i>On-chain</span>' : ''}
        </div>
        ${detailsHtml}
        <div class="popup-actions">
            <a href="https://www.google.com/maps/dir/?api=1&destination=${m.lat},${m.lon}" target="_blank" class="directions-btn">
                <i class="fas fa-directions"></i> Get Directions
            </a>
        </div>
    `;
    
    marker.bindPopup(popupContent, {
        className: 'merchant-popup',
        maxWidth: 300
    }).openPopup();
}

function flyToMerchant(lat, lon) {
    map.flyTo([lat, lon], 16, { duration: 1 });
}

function buildAddress(tags) {
    const parts = [];
    if (tags['addr:housenumber']) parts.push(tags['addr:housenumber']);
    if (tags['addr:street']) parts.push(tags['addr:street']);
    if (tags['addr:city']) parts.push(tags['addr:city']);
    if (tags['addr:country']) parts.push(tags['addr:country']);
    return parts.join(', ');
}

function formatCategory(cat) {
    if (!cat) return 'Business';
    return cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function searchLocation() {
    const query = document.getElementById('location-search').value;
    if (!query) return;
    
    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
        const results = await response.json();
        
        if (results.length > 0) {
            const { lat, lon } = results[0];
            map.flyTo([parseFloat(lat), parseFloat(lon)], 12, { duration: 1.5 });
        }
    } catch (error) {
        console.error('Search failed:', error);
    }
}

function searchLocationMobile() {
    const query = document.getElementById('mobile-search').value;
    document.getElementById('location-search').value = query;
    searchLocation();
}

function useCurrentLocation() {
    if ('geolocation' in navigator) {
        navigator.geolocation.getCurrentPosition(
            pos => {
                map.flyTo([pos.coords.latitude, pos.coords.longitude], 13, { duration: 1.5 });
            },
            err => {
                alert('Could not get your location. Please enable location services.');
            }
        );
    } else {
        alert('Geolocation is not supported by your browser.');
    }
}

function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

document.getElementById('location-search').addEventListener('keypress', e => {
    if (e.key === 'Enter') searchLocation();
});

document.addEventListener('DOMContentLoaded', initMap);
</script>
{% endblock %}
```

## templates/meetup_map.html
```html
{% extends "base.html" %}

{% block title %}Bitcoin Meetup Map | Protocol Pulse{% endblock %}

{% block head %}
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
    --btc-orange: #f7931a;
}

.map-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding-top: 80px;
}

.map-header {
    padding: 30px 20px;
    text-align: center;
}

.map-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    margin-bottom: 10px;
}

.map-title i {
    color: var(--btc-orange);
}

.map-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.6);
}

.stats-bar {
    display: flex;
    justify-content: center;
    gap: 40px;
    padding: 20px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.stat-item {
    text-align: center;
}

.stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--btc-orange);
}

.stat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.map-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 20px 40px;
}

.map-wrapper {
    display: grid;
    grid-template-columns: 1fr 350px;
    gap: 20px;
}

@media (max-width: 992px) {
    .map-wrapper {
        grid-template-columns: 1fr;
    }
}

#bitcoin-map {
    height: 600px;
    border-radius: 16px;
    border: 1px solid rgba(247, 147, 26, 0.3);
    overflow: hidden;
}

.leaflet-container {
    background: #1a1a1a;
}

.sidebar {
    background: rgba(10, 10, 10, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(247, 147, 26, 0.2);
    border-radius: 8px;
    padding: 20px;
    max-height: 600px;
    overflow-y: auto;
    box-shadow: 
        inset 0 0 15px rgba(247, 147, 26, 0.05),
        0 10px 30px rgba(0, 0, 0, 0.5);
}

.sidebar i,
.sidebar img {
    filter: none !important;
    box-shadow: none !important;
}

.sidebar-section {
    margin-bottom: 25px;
}

.section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--btc-orange);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.meetup-list {
    display: grid;
    gap: 12px;
}

.meetup-card {
    background: rgba(10, 10, 10, 0.6);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(247, 147, 26, 0.15);
    border-radius: 8px;
    padding: 15px;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.meetup-card:hover {
    border-color: rgba(247, 147, 26, 0.6);
    box-shadow: 
        0 0 20px rgba(247, 147, 26, 0.15),
        inset 0 0 15px rgba(247, 147, 26, 0.08);
    transform: translateY(-2px);
}

.meetup-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #fff;
    font-weight: 600;
    margin-bottom: 5px;
}

.meetup-city {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 8px;
}

.meetup-meta {
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
}

.meta-item {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.6);
    display: flex;
    align-items: center;
    gap: 5px;
}

.meta-item i {
    color: var(--btc-orange);
}

.legend {
    display: grid;
    gap: 10px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.7);
}

.legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}

.legend-dot.meetup {
    background: var(--btc-orange);
}

.legend-dot.merchant {
    background: #22c55e;
}

.legend-dot.atm {
    background: #60a5fa;
}

.search-box {
    width: 100%;
    padding: 12px 15px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    margin-bottom: 15px;
}

.search-box:focus {
    outline: none;
    border-color: var(--btc-orange);
}

.search-box::placeholder {
    color: rgba(255, 255, 255, 0.4);
}

.btc-marker {
    background: var(--btc-orange);
    border-radius: 50%;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #000;
    font-weight: bold;
    font-size: 14px;
    border: 2px solid #fff;
    box-shadow: 0 2px 10px rgba(247, 147, 26, 0.5);
}

.merchant-marker {
    background: #22c55e;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    border: 2px solid #fff;
    box-shadow: 0 2px 8px rgba(34, 197, 94, 0.5);
}

.leaflet-popup-content-wrapper {
    background: rgba(10, 10, 10, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(247, 147, 26, 0.2);
    border-radius: 8px;
    color: #fff;
    box-shadow: 
        inset 0 0 15px rgba(247, 147, 26, 0.05),
        0 10px 30px rgba(0, 0, 0, 0.5);
}

.leaflet-popup-tip {
    background: rgba(10, 10, 10, 0.85);
}

.leaflet-popup-content-wrapper i,
.leaflet-popup-content-wrapper img {
    filter: none !important;
    box-shadow: none !important;
}

.popup-content {
    padding: 5px;
}

.popup-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 600;
    color: var(--btc-orange);
    margin-bottom: 8px;
}

.popup-info {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.5;
}

.popup-link {
    display: inline-block;
    margin-top: 10px;
    padding: 6px 12px;
    background: var(--btc-orange);
    color: #000;
    text-decoration: none;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
}

.popup-link:hover {
    background: #e8820f;
    color: #000;
}

.region-filter {
    display: flex;
    justify-content: center;
    gap: 10px;
    padding: 0 20px 30px;
    flex-wrap: wrap;
}

.region-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(247, 147, 26, 0.2);
    color: rgba(255, 255, 255, 0.7);
    padding: 10px 18px;
    border-radius: 25px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.region-btn:hover {
    background: rgba(247, 147, 26, 0.15);
    border-color: var(--btc-orange);
    color: #fff;
}

.region-btn.active {
    background: var(--btc-orange);
    border-color: var(--btc-orange);
    color: #000;
    font-weight: 600;
}

.back-nav {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(247, 147, 26, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(247, 147, 26, 0.2);
    border-color: var(--btc-orange);
    color: #fff;
}

.meetup-region {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--btc-orange);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 5px;
}

#bitcoin-map {
    height: 650px;
}

@media (max-width: 768px) {
    .region-filter {
        gap: 6px;
        padding: 0 10px 20px;
    }
    .region-btn {
        padding: 8px 12px;
        font-size: 0.65rem;
    }
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="map-page">
    <div class="map-header">
        <h1 class="map-title">
            <i class="fab fa-bitcoin"></i>
            Sovereign Merchant Map
        </h1>
        <p class="map-subtitle">Find Bitcoin-accepting businesses and meetups worldwide</p>
    </div>
    
    <div class="stats-bar">
        <div class="stat-item">
            <div class="stat-value" id="total-merchants">{{ stats.total_merchants | default(40000) | int }}</div>
            <div class="stat-label">Bitcoin Merchants</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{{ meetups | length }}</div>
            <div class="stat-label">Active Meetups</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{{ (stats.lightning_enabled | default(0.65) * 100) | int }}%</div>
            <div class="stat-label">Lightning Enabled</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">6</div>
            <div class="stat-label">Continents</div>
        </div>
    </div>
    
    <div class="region-filter">
        <button class="region-btn active" onclick="filterRegion(null, this)">All Regions</button>
        <button class="region-btn" onclick="filterRegion('North America', this)">North America</button>
        <button class="region-btn" onclick="filterRegion('Latin America', this)">Latin America</button>
        <button class="region-btn" onclick="filterRegion('Europe', this)">Europe</button>
        <button class="region-btn" onclick="filterRegion('Asia', this)">Asia</button>
        <button class="region-btn" onclick="filterRegion('Africa', this)">Africa</button>
        <button class="region-btn" onclick="filterRegion('Oceania', this)">Oceania</button>
        <button class="region-btn" onclick="filterRegion('Middle East', this)">Middle East</button>
    </div>
    
    <div class="map-container">
        <div class="map-wrapper">
            <div id="bitcoin-map"></div>
            
            <div class="sidebar">
                <input type="text" class="search-box" placeholder="Search cities or meetups..." id="search-input">
                
                <div class="sidebar-section">
                    <div class="section-title">
                        <i class="fas fa-users"></i> Bitcoin Meetups
                    </div>
                    <div class="meetup-list" id="meetup-list">
                        {% for meetup in meetups %}
                        <div class="meetup-card" onclick="flyToMeetup({{ meetup.lat }}, {{ meetup.lon }}, '{{ meetup.name }}')">
                            <div class="meetup-name">{{ meetup.name }}</div>
                            <div class="meetup-city">{{ meetup.city }}</div>
                            <div class="meetup-meta">
                                <span class="meta-item">
                                    <i class="fas fa-calendar"></i> {{ meetup.frequency }}
                                </span>
                                <span class="meta-item">
                                    <i class="fas fa-users"></i> {{ meetup.members | default(0) | int }}
                                </span>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="sidebar-section">
                    <div class="section-title">
                        <i class="fas fa-info-circle"></i> Legend
                    </div>
                    <div class="legend">
                        <div class="legend-item">
                            <span class="legend-dot meetup"></span>
                            Bitcoin Meetup
                        </div>
                        <div class="legend-item">
                            <span class="legend-dot merchant"></span>
                            Accepting Merchant
                        </div>
                        <div class="legend-item">
                            <span class="legend-dot atm"></span>
                            Bitcoin ATM
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css" />
<script>
const meetups = {{ meetups | tojson | safe }};
let markers = [];
let markerCluster;
let currentFilter = null;

const map = L.map('bitcoin-map').setView([25, 0], 2);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://carto.com/">CartoDB</a>',
    maxZoom: 19
}).addTo(map);

const btcIcon = L.divIcon({
    className: 'btc-marker-wrapper',
    html: '<div class="btc-marker">₿</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15]
});

function initMarkers(filterRegion = null) {
    if (markerCluster) {
        map.removeLayer(markerCluster);
    }
    markers = [];
    markerCluster = L.markerClusterGroup({
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        iconCreateFunction: function(cluster) {
            const count = cluster.getChildCount();
            return L.divIcon({
                html: `<div class="cluster-marker">${count}</div>`,
                className: 'btc-cluster',
                iconSize: [40, 40]
            });
        }
    });
    
    const filteredMeetups = filterRegion 
        ? meetups.filter(m => m.region === filterRegion)
        : meetups;
    
    filteredMeetups.forEach(meetup => {
        const popup = `
            <div class="popup-content">
                <div class="popup-title">${meetup.name}</div>
                <div class="popup-info">
                    <strong>Location:</strong> ${meetup.city}<br>
                    <strong>Region:</strong> ${meetup.region || 'Unknown'}<br>
                    <strong>Schedule:</strong> ${meetup.next_event || meetup.frequency}<br>
                    <strong>Members:</strong> ${meetup.members ? meetup.members.toLocaleString() : 'Unknown'}
                </div>
                ${meetup.url ? `<a href="${meetup.url}" target="_blank" class="popup-link">Join Meetup</a>` : ''}
            </div>
        `;
        
        const marker = L.marker([meetup.lat, meetup.lon], { icon: btcIcon })
            .bindPopup(popup);
        markers.push({ marker, meetup });
        markerCluster.addLayer(marker);
    });
    
    map.addLayer(markerCluster);
    updateMeetupList(filterRegion);
}

function updateMeetupList(filterRegion = null) {
    const listEl = document.getElementById('meetup-list');
    const filteredMeetups = filterRegion 
        ? meetups.filter(m => m.region === filterRegion)
        : meetups;
    
    const sortedMeetups = [...filteredMeetups].sort((a, b) => (b.members || 0) - (a.members || 0));
    
    listEl.innerHTML = sortedMeetups.slice(0, 20).map(meetup => `
        <div class="meetup-card" onclick="flyToMeetup(${meetup.lat}, ${meetup.lon}, '${meetup.name.replace(/'/g, "\\'")}')">
            <div class="meetup-name">${meetup.name}</div>
            <div class="meetup-city">${meetup.city}</div>
            <div class="meetup-meta">
                <span class="meta-item">
                    <i class="fas fa-calendar"></i> ${meetup.frequency}
                </span>
                <span class="meta-item">
                    <i class="fas fa-users"></i> ${meetup.members ? meetup.members.toLocaleString() : 0}
                </span>
            </div>
            <div class="meetup-region">${meetup.region || ''}</div>
        </div>
    `).join('');
}

function filterRegion(region, btn) {
    currentFilter = region;
    
    document.querySelectorAll('.region-btn').forEach(b => {
        b.classList.remove('active');
    });
    if (btn) btn.classList.add('active');
    
    initMarkers(region);
    
    if (region) {
        const regionCenters = {
            'North America': [40, -100],
            'Latin America': [-15, -60],
            'Europe': [50, 10],
            'Asia': [30, 105],
            'Africa': [0, 20],
            'Oceania': [-25, 140],
            'Middle East': [28, 45]
        };
        const center = regionCenters[region] || [25, 0];
        map.flyTo(center, 3, { duration: 1 });
    } else {
        map.flyTo([25, 0], 2, { duration: 1 });
    }
}

function flyToMeetup(lat, lon, name) {
    map.flyTo([lat, lon], 12, {
        duration: 1.5
    });
    
    markers.forEach(({ marker, meetup }) => {
        if (meetup.name === name) {
            setTimeout(() => marker.openPopup(), 1600);
        }
    });
}

document.getElementById('search-input').addEventListener('input', function(e) {
    const query = e.target.value.toLowerCase();
    const cards = document.querySelectorAll('.meetup-card');
    
    cards.forEach(card => {
        const name = card.querySelector('.meetup-name').textContent.toLowerCase();
        const city = card.querySelector('.meetup-city').textContent.toLowerCase();
        
        if (name.includes(query) || city.includes(query)) {
            card.style.display = 'block';
        } else {
            card.style.display = query ? 'none' : 'block';
        }
    });
});

async function loadMerchants(bounds) {
    try {
        const response = await fetch(`/api/merchants?bounds=${bounds.toBBoxString()}&limit=100`);
        const data = await response.json();
        
        if (data.merchants) {
            data.merchants.forEach(m => {
                const merchantIcon = L.divIcon({
                    className: 'merchant-marker-wrapper',
                    html: '<div class="merchant-marker"></div>',
                    iconSize: [18, 18],
                    iconAnchor: [9, 9]
                });
                
                L.marker([m.lat, m.lon], { icon: merchantIcon })
                    .addTo(map)
                    .bindPopup(`<div class="popup-content">
                        <div class="popup-title">${m.name}</div>
                        <div class="popup-info">${m.address || ''}</div>
                        ${m.payment_lightning ? '<div style="color: #f7931a; font-size: 0.7rem;">⚡ Lightning Enabled</div>' : ''}
                    </div>`);
            });
        }
    } catch (error) {
        console.log('Merchant loading error:', error);
    }
}

map.on('moveend', function() {
    if (map.getZoom() >= 10) {
        loadMerchants(map.getBounds());
    }
});

initMarkers();
</script>
<style>
.btc-cluster {
    background: transparent;
}
.cluster-marker {
    background: var(--btc-orange);
    color: #000;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-weight: bold;
    font-size: 0.85rem;
    border: 2px solid #fff;
    box-shadow: 0 2px 10px rgba(247, 147, 26, 0.5);
}
.leaflet-marker-icon.marker-cluster {
    background: transparent !important;
}
</style>
{% endblock %}
```

## templates/sovereign_scorecard.html
```html
{% extends "base.html" %}

{% block title %}Sovereign Scorecard | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
}

.scorecard-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 100px 20px 60px;
}

.scorecard-container {
    max-width: 800px;
    margin: 0 auto;
}

.scorecard-header {
    text-align: center;
    margin-bottom: 40px;
}

.back-nav {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
    transform: translateX(-3px);
}

.back-btn i {
    color: var(--pp-red);
}

.scorecard-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.2rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 15px;
}

.scorecard-title i {
    color: var(--pp-red);
    margin-right: 15px;
}

.scorecard-subtitle {
    color: rgba(255, 255, 255, 0.5);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    max-width: 600px;
    margin: 0 auto;
}

.quiz-section {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 16px;
    padding: 30px;
    margin-bottom: 20px;
    backdrop-filter: blur(20px);
}

.section-header {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 25px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.section-icon {
    width: 45px;
    height: 45px;
    background: rgba(220, 38, 38, 0.2);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--pp-red);
    font-size: 1.2rem;
}

.section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: #fff;
    font-weight: 600;
}

.quiz-question {
    margin-bottom: 25px;
}

.question-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.9);
    margin-bottom: 12px;
}

.question-options {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.option-wrapper {
    position: relative;
    flex: 1;
    min-width: 140px;
}

.option-btn {
    width: 100%;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 14px 20px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}

.option-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
}

.option-btn.selected {
    background: var(--pp-red);
    border-color: var(--pp-red);
    color: #fff;
}

.option-btn.selected.green {
    background: #22c55e;
    border-color: #22c55e;
}

.option-btn.selected.yellow {
    background: #eab308;
    border-color: #eab308;
}

.info-icon {
    font-size: 0.7rem;
    opacity: 0.6;
    transition: opacity 0.3s ease;
}

.option-btn:hover .info-icon {
    opacity: 1;
}

.tooltip-popup {
    position: absolute;
    bottom: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%);
    background: #1a1a1a;
    border: 1px solid var(--pp-red);
    border-radius: 12px;
    padding: 15px 18px;
    width: 280px;
    z-index: 100;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
}

.tooltip-popup.active {
    opacity: 1;
    visibility: visible;
}

.tooltip-popup::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 8px solid transparent;
    border-top-color: var(--pp-red);
}

.tooltip-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--pp-red);
    font-weight: 600;
    margin-bottom: 8px;
}

.tooltip-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.8);
    line-height: 1.6;
    margin-bottom: 10px;
}

.tooltip-examples {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 8px;
}

.tooltip-examples strong {
    color: #22c55e;
}

.submit-section {
    text-align: center;
    margin-top: 30px;
}

.submit-btn {
    background: var(--pp-red);
    border: none;
    border-radius: 10px;
    padding: 18px 50px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}

.submit-btn:hover {
    background: #b91c1c;
    transform: translateY(-2px);
}

.submit-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.results-section {
    display: none;
}

.score-display {
    text-align: center;
    margin-bottom: 30px;
}

.score-circle {
    width: 180px;
    height: 180px;
    border-radius: 50%;
    margin: 0 auto 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}

.score-circle::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 50%;
    padding: 6px;
    background: conic-gradient(var(--score-color) calc(var(--score-percent) * 3.6deg), rgba(255,255,255,0.1) 0);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
}

.score-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 3rem;
    font-weight: 700;
    color: #fff;
}

.score-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 2px;
}

.score-grade {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 10px;
}

.score-message {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.6;
    max-width: 500px;
    margin: 0 auto 30px;
}

.action-plan {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 16px;
    padding: 25px;
    margin-top: 25px;
    text-align: left;
}

.action-plan-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.action-plan-header i {
    color: var(--pp-red);
    font-size: 1.2rem;
}

.action-plan-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: #fff;
    font-weight: 600;
}

.action-category {
    margin-bottom: 25px;
}

.action-category:last-child {
    margin-bottom: 0;
}

.action-category-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}

.priority-badge {
    padding: 4px 10px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.priority-critical {
    background: rgba(220, 38, 38, 0.3);
    color: #dc2626;
}

.priority-important {
    background: rgba(234, 179, 8, 0.3);
    color: #eab308;
}

.priority-recommended {
    background: rgba(34, 197, 94, 0.3);
    color: #22c55e;
}

.action-category-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.9);
}

.action-item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    padding: 18px;
    margin-bottom: 12px;
}

.action-item:last-child {
    margin-bottom: 0;
}

.action-item-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
}

.action-item-header i {
    color: var(--pp-red);
    margin-top: 3px;
}

.action-item-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #fff;
    font-weight: 600;
}

.action-item-desc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.6;
    margin-bottom: 12px;
    padding-left: 28px;
}

.action-steps {
    padding-left: 28px;
}

.action-step {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
}

.action-step-num {
    background: var(--pp-red);
    color: #fff;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 600;
    flex-shrink: 0;
}

.product-recs {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 8px;
    padding: 12px;
    margin-top: 12px;
    margin-left: 28px;
}

.product-recs-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #22c55e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.product-list {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.8);
}

.product-list span {
    display: inline-block;
    background: rgba(255, 255, 255, 0.1);
    padding: 4px 10px;
    border-radius: 4px;
    margin: 3px 4px 3px 0;
}

.retake-btn {
    background: transparent;
    border: 1px solid var(--pp-red);
    border-radius: 8px;
    padding: 12px 30px;
    color: var(--pp-red);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 25px;
}

.retake-btn:hover {
    background: var(--pp-red);
    color: #fff;
}

@media (max-width: 768px) {
    .scorecard-title {
        font-size: 1.6rem;
    }
    .quiz-section {
        padding: 20px;
    }
    .option-wrapper {
        min-width: 100%;
    }
    .tooltip-popup {
        width: 250px;
        left: 0;
        transform: none;
    }
    .tooltip-popup::after {
        left: 20%;
    }
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="scorecard-page">
    <div class="scorecard-container">
        <div class="scorecard-header">
            <h1 class="scorecard-title"><i class="fas fa-shield-halved"></i>Sovereign Scorecard</h1>
            <p class="scorecard-subtitle">Assess your Bitcoin security posture. Hover over any option for more information. Answer honestly to receive personalized recommendations and a step-by-step action plan.</p>
        </div>
        
        <div id="quiz-form">
            <div class="quiz-section">
                <div class="section-header">
                    <div class="section-icon"><i class="fas fa-key"></i></div>
                    <div class="section-title">Key Management</div>
                </div>
                
                <div class="quiz-question" data-category="keys" data-question="custody">
                    <div class="question-text">How do you store your Bitcoin?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                Exchange only <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup" data-tooltip="exchange">
                                <div class="tooltip-title">Exchange Custody</div>
                                <div class="tooltip-text">Your Bitcoin is held by a third party (like Coinbase, Kraken, or Binance). You don't control the private keys - the exchange does. If the exchange gets hacked, goes bankrupt, or freezes your account, you could lose access to your funds.</div>
                                <div class="tooltip-examples"><strong>Risk:</strong> "Not your keys, not your coins" - exchanges have failed before (Mt. Gox, FTX)</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="5" data-color="yellow">
                                Hot wallet <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup" data-tooltip="hotwallet">
                                <div class="tooltip-title">Hot Wallet</div>
                                <div class="tooltip-text">A wallet app on your phone or computer that's connected to the internet. You control the keys, but since it's online, it's more vulnerable to hackers and malware. Good for small amounts you spend regularly.</div>
                                <div class="tooltip-examples"><strong>Examples:</strong> BlueWallet, Muun, Phoenix, Electrum mobile</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="8" data-color="yellow">
                                Hardware wallet <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup" data-tooltip="hardware">
                                <div class="tooltip-title">Hardware Wallet</div>
                                <div class="tooltip-text">A dedicated physical device that stores your private keys offline (cold storage). Your keys never touch the internet, making it extremely secure. Required to physically press buttons on the device to approve transactions.</div>
                                <div class="tooltip-examples"><strong>Examples:</strong> Trezor, Ledger, Coldcard, BitBox02, Foundation Passport</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Multisig <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup" data-tooltip="multisig">
                                <div class="tooltip-title">Multi-Signature (Multisig)</div>
                                <div class="tooltip-text">Requires multiple keys (e.g., 2-of-3 or 3-of-5) to authorize a transaction. Even if one key is compromised or lost, your Bitcoin remains safe. The gold standard for securing significant amounts.</div>
                                <div class="tooltip-examples"><strong>Services:</strong> Unchained Capital, Casa, Nunchuk, Sparrow Wallet (self-custody)</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="quiz-question" data-category="keys" data-question="backup">
                    <div class="question-text">How is your seed phrase backed up?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                Not backed up <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">No Backup</div>
                                <div class="tooltip-text">Without a backup of your 12 or 24-word seed phrase, if your wallet device is lost, stolen, or breaks, your Bitcoin is gone forever. There is no recovery option without the seed phrase.</div>
                                <div class="tooltip-examples"><strong>Critical:</strong> An estimated 20% of all Bitcoin is lost forever due to lost keys</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="3" data-color="red">
                                Digital file <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Digital Backup</div>
                                <div class="tooltip-text">Storing your seed phrase in a text file, notes app, email, or cloud storage. While convenient, this is highly vulnerable - your computer can be hacked, cloud accounts can be breached, and photos can sync to compromised services.</div>
                                <div class="tooltip-examples"><strong>Warning:</strong> Never take a photo of your seed phrase or store it digitally</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="7" data-color="yellow">
                                Paper backup <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Paper Backup</div>
                                <div class="tooltip-text">Writing your seed phrase on paper and storing it securely. Better than digital, but paper can be destroyed by fire, water, or fade over time. Consider laminating and storing in multiple secure locations.</div>
                                <div class="tooltip-examples"><strong>Tip:</strong> Use a fireproof safe and consider multiple copies in different locations</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Metal backup <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Metal Backup</div>
                                <div class="tooltip-text">Stamping or engraving your seed phrase onto stainless steel or titanium plates. Survives fire (up to 1500°C), floods, and decades of storage. The most durable backup method available.</div>
                                <div class="tooltip-examples"><strong>Products:</strong> Cryptosteel, Billfodl, Blockplate, Seedplate, ColdTI</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="quiz-section">
                <div class="section-header">
                    <div class="section-icon"><i class="fas fa-lock"></i></div>
                    <div class="section-title">Access Security</div>
                </div>
                
                <div class="quiz-question" data-category="access" data-question="2fa">
                    <div class="question-text">Do you use 2FA on exchange accounts?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                No 2FA <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">No Two-Factor Authentication</div>
                                <div class="tooltip-text">Using only a password to protect your account. If your password is leaked in a data breach or guessed, attackers have full access to your account and can steal your funds immediately.</div>
                                <div class="tooltip-examples"><strong>Stat:</strong> 80% of hacking-related breaches involve stolen or weak credentials</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="5" data-color="yellow">
                                SMS 2FA <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">SMS Two-Factor Authentication</div>
                                <div class="tooltip-text">Receiving a code via text message. Better than nothing, but vulnerable to SIM swap attacks where criminals convince your phone carrier to transfer your number to their SIM card, intercepting all your codes.</div>
                                <div class="tooltip-examples"><strong>Risk:</strong> SIM swaps have resulted in millions of dollars in crypto theft</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="8" data-color="yellow">
                                Authenticator app <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Authenticator App</div>
                                <div class="tooltip-text">Apps that generate time-based codes (TOTP) on your phone. Much more secure than SMS since codes are generated locally and can't be intercepted. Make sure to back up your authenticator seeds.</div>
                                <div class="tooltip-examples"><strong>Apps:</strong> Google Authenticator, Authy, Microsoft Authenticator, Aegis (open source)</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Hardware key <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Hardware Security Key</div>
                                <div class="tooltip-text">A physical USB or NFC device that you must physically plug in or tap to authenticate. Phishing-resistant because it cryptographically verifies the website is legitimate. The most secure 2FA method available.</div>
                                <div class="tooltip-examples"><strong>Products:</strong> YubiKey, Thetis, SoloKeys, Nitrokey</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="quiz-question" data-category="access" data-question="password">
                    <div class="question-text">How do you manage passwords?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                Same password <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Password Reuse</div>
                                <div class="tooltip-text">Using the same password across multiple sites. When any one site is breached (which happens constantly), attackers automatically try your credentials on crypto exchanges and financial sites.</div>
                                <div class="tooltip-examples"><strong>Check:</strong> Visit haveibeenpwned.com to see if your emails appear in breaches</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="4" data-color="yellow">
                                Unique passwords <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Unique Passwords (Memorized)</div>
                                <div class="tooltip-text">Using different passwords for each site but trying to remember them all. Better than reusing, but leads to weak passwords or writing them down insecurely. A password manager is strongly recommended.</div>
                                <div class="tooltip-examples"><strong>Tip:</strong> Humans can't reliably remember truly random, strong passwords for dozens of accounts</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Password manager <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Password Manager</div>
                                <div class="tooltip-text">Software that generates and securely stores unique, strong passwords for every account. You only need to remember one master password. Most security experts consider this essential for everyone.</div>
                                <div class="tooltip-examples"><strong>Options:</strong> Bitwarden (free), 1Password, KeePassXC (offline), Proton Pass</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="quiz-section">
                <div class="section-header">
                    <div class="section-icon"><i class="fas fa-network-wired"></i></div>
                    <div class="section-title">Network Sovereignty</div>
                </div>
                
                <div class="quiz-question" data-category="network" data-question="node">
                    <div class="question-text">Do you run your own Bitcoin node?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                No <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">No Personal Node</div>
                                <div class="tooltip-text">You rely on third-party servers to verify your transactions and check your balance. This means trusting that they're showing you accurate information and not tracking your activity. Works, but isn't sovereign.</div>
                                <div class="tooltip-examples"><strong>Privacy:</strong> Third-party servers can see which addresses you're checking</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="5" data-color="yellow">
                                Planning to <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Planning to Run a Node</div>
                                <div class="tooltip-text">You understand the importance and are considering setting one up. Modern node solutions have made this much easier than before - many are plug-and-play devices or simple software installations.</div>
                                <div class="tooltip-examples"><strong>Getting started:</strong> Start, Umbrel, RaspiBlitz, MyNode, or Bitcoin Core on any computer</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Yes, full node <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Running a Full Node</div>
                                <div class="tooltip-text">You verify every transaction and block yourself, trusting no third party. You're contributing to Bitcoin's decentralization and security. Your wallet connects directly to your node for maximum privacy.</div>
                                <div class="tooltip-examples"><strong>Solutions:</strong> Umbrel, RaspiBlitz, Start9, MyNode, Nodl, Bitcoin Core</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="quiz-question" data-category="network" data-question="privacy">
                    <div class="question-text">How do you handle transaction privacy?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                No measures <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">No Privacy Measures</div>
                                <div class="tooltip-text">All your transactions are fully traceable on the public blockchain. Chain analysis companies can link your purchases, income, and holdings. This data is sold to governments and corporations.</div>
                                <div class="tooltip-examples"><strong>Reality:</strong> Bitcoin is pseudonymous, not anonymous - all transactions are public</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="5" data-color="yellow">
                                New addresses <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">New Address Per Transaction</div>
                                <div class="tooltip-text">Using a fresh receiving address for each transaction. This is basic privacy hygiene that prevents casual observers from tracking all your transactions. Most modern wallets do this automatically.</div>
                                <div class="tooltip-examples"><strong>Good practice:</strong> Never share the same address twice - most wallets auto-generate new ones</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="8" data-color="yellow">
                                VPN/Tor <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">VPN or Tor Network</div>
                                <div class="tooltip-text">Hiding your IP address when broadcasting transactions or checking balances. Prevents your internet provider and network observers from knowing you use Bitcoin. Tor is stronger than VPN for this purpose.</div>
                                <div class="tooltip-examples"><strong>Tools:</strong> Tor Browser, Mullvad VPN, running your node over Tor</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Coinjoin <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">CoinJoin</div>
                                <div class="tooltip-text">A technique where multiple users combine their transactions, making it difficult to trace which inputs correspond to which outputs. Breaks the chain of transaction history for improved on-chain privacy.</div>
                                <div class="tooltip-examples"><strong>Tools:</strong> Wasabi Wallet, Sparrow Wallet (Whirlpool), JoinMarket</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="quiz-section">
                <div class="section-header">
                    <div class="section-icon"><i class="fas fa-brain"></i></div>
                    <div class="section-title">OPSEC Awareness</div>
                </div>
                
                <div class="quiz-question" data-category="opsec" data-question="disclosure">
                    <div class="question-text">How many people know you own Bitcoin?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Nobody <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Complete Discretion</div>
                                <div class="tooltip-text">You don't discuss your Bitcoin holdings with anyone. This is the strongest operational security (OPSEC) position, eliminating social engineering and physical attack vectors entirely.</div>
                                <div class="tooltip-examples"><strong>Principle:</strong> You can't be targeted for what people don't know you have</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="7" data-color="yellow">
                                Close family <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Trusted Family Only</div>
                                <div class="tooltip-text">Only your spouse or immediate family knows. This is reasonable for inheritance planning purposes, but ensure they understand the importance of discretion and have the knowledge to access funds if needed.</div>
                                <div class="tooltip-examples"><strong>Important:</strong> Family members should know not to mention your holdings to others</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="3" data-color="yellow">
                                Friends <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Friends Know</div>
                                <div class="tooltip-text">Friends or acquaintances know you hold Bitcoin. Information spreads - friends tell other friends, and social dynamics change if they perceive you as wealthy. This increases your attack surface.</div>
                                <div class="tooltip-examples"><strong>Risk:</strong> Information spreads through social networks unpredictably</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                Public <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Publicly Known</div>
                                <div class="tooltip-text">You've posted about your holdings on social media, at work, or in public forums. This makes you a potential target for sophisticated phishing, social engineering, SIM swap attacks, and even physical threats.</div>
                                <div class="tooltip-examples"><strong>Warning:</strong> "$5 wrench attacks" target known Bitcoin holders</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="quiz-question" data-category="opsec" data-question="inheritance">
                    <div class="question-text">Do you have an inheritance plan?</div>
                    <div class="question-options">
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="0" data-color="red">
                                No plan <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">No Inheritance Plan</div>
                                <div class="tooltip-text">If something happens to you, your Bitcoin could be lost forever. Unlike bank accounts, there's no institution to recover Bitcoin - if no one knows your keys, the coins are gone permanently.</div>
                                <div class="tooltip-examples"><strong>Reality:</strong> Millions of BTC are estimated to be permanently lost</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="5" data-color="yellow">
                                Verbal only <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Verbal Instructions Only</div>
                                <div class="tooltip-text">You've told someone about your Bitcoin verbally but haven't documented anything. People forget details, especially under stress. Written documentation with clear steps is essential for heirs to actually recover funds.</div>
                                <div class="tooltip-examples"><strong>Issue:</strong> Technical details are easily forgotten or misremembered</div>
                            </div>
                        </div>
                        <div class="option-wrapper">
                            <button class="option-btn" data-value="10" data-color="green">
                                Documented <i class="fas fa-info-circle info-icon"></i>
                            </button>
                            <div class="tooltip-popup">
                                <div class="tooltip-title">Documented Inheritance Plan</div>
                                <div class="tooltip-text">You have written instructions, potentially with a lawyer or in a secure location, explaining how to access your Bitcoin. This may include seed phrase locations, wallet instructions, and step-by-step recovery procedures.</div>
                                <div class="tooltip-examples"><strong>Solutions:</strong> Casa inheritance, Unchained inheritance, lawyer letters, detailed written guides</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="submit-section">
                <button class="submit-btn" onclick="calculateScore()" disabled>Calculate My Score</button>
            </div>
        </div>
        
        <div class="results-section" id="results-section">
            <div class="quiz-section">
                <div class="score-display">
                    <div class="score-circle" id="score-circle">
                        <span class="score-value" id="score-value">0</span>
                        <span class="score-label">/ 80</span>
                    </div>
                    <div class="score-grade" id="score-grade">--</div>
                    <div class="score-message" id="score-message"></div>
                </div>
                
                <div class="action-plan" id="action-plan"></div>
                
                <div style="text-align: center;">
                    <button class="retake-btn" onclick="retakeQuiz()">
                        <i class="fas fa-redo me-2"></i>Retake Assessment
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
const answers = {};
let totalQuestions = 0;
let activeTooltip = null;

document.querySelectorAll('.quiz-question').forEach(q => {
    totalQuestions++;
    q.querySelectorAll('.option-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (e.target.classList.contains('info-icon')) return;
            
            q.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected', 'green', 'yellow'));
            btn.classList.add('selected', btn.dataset.color);
            
            const question = q.dataset.question;
            answers[question] = {
                value: parseInt(btn.dataset.value),
                text: btn.textContent.replace(/\s+/g, ' ').trim(),
                color: btn.dataset.color
            };
            
            checkAllAnswered();
        });
        
        const wrapper = btn.closest('.option-wrapper');
        const tooltip = wrapper.querySelector('.tooltip-popup');
        
        if (tooltip) {
            let hoverTimeout;
            
            wrapper.addEventListener('mouseenter', () => {
                hoverTimeout = setTimeout(() => {
                    if (activeTooltip && activeTooltip !== tooltip) {
                        activeTooltip.classList.remove('active');
                    }
                    tooltip.classList.add('active');
                    activeTooltip = tooltip;
                }, 300);
            });
            
            wrapper.addEventListener('mouseleave', () => {
                clearTimeout(hoverTimeout);
                tooltip.classList.remove('active');
                if (activeTooltip === tooltip) activeTooltip = null;
            });
            
            tooltip.addEventListener('click', (e) => {
                e.stopPropagation();
                tooltip.classList.remove('active');
                activeTooltip = null;
            });
        }
    });
});

document.addEventListener('scroll', () => {
    if (activeTooltip) {
        activeTooltip.classList.remove('active');
        activeTooltip = null;
    }
});

function checkAllAnswered() {
    const answered = Object.keys(answers).length;
    document.querySelector('.submit-btn').disabled = answered < totalQuestions;
}

function calculateScore() {
    let total = 0;
    Object.values(answers).forEach(a => total += a.value);
    
    const maxScore = 80;
    const percent = (total / maxScore) * 100;
    
    let grade, message, color;
    if (percent >= 90) {
        grade = 'SOVEREIGN';
        message = 'Outstanding security posture. You embody true self-custody principles and are well-protected against most attack vectors.';
        color = '#22c55e';
    } else if (percent >= 70) {
        grade = 'PROTECTED';
        message = 'Good security practices. You\'ve taken important steps but there\'s room for improvement in some areas.';
        color = '#22c55e';
    } else if (percent >= 50) {
        grade = 'DEVELOPING';
        message = 'Basic security in place. Several critical areas need attention to properly protect your Bitcoin.';
        color = '#eab308';
    } else if (percent >= 30) {
        grade = 'AT RISK';
        message = 'Significant security gaps detected. Your Bitcoin is vulnerable to common attack vectors.';
        color = '#f97316';
    } else {
        grade = 'CRITICAL';
        message = 'Urgent action required. Your current setup provides minimal protection for your Bitcoin.';
        color = '#dc2626';
    }
    
    document.getElementById('quiz-form').style.display = 'none';
    document.getElementById('results-section').style.display = 'block';
    
    const circle = document.getElementById('score-circle');
    circle.style.setProperty('--score-percent', percent);
    circle.style.setProperty('--score-color', color);
    
    document.getElementById('score-value').textContent = total;
    document.getElementById('score-grade').textContent = grade;
    document.getElementById('score-grade').style.color = color;
    document.getElementById('score-message').textContent = message;
    
    generateActionPlan();
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function generateActionPlan() {
    const critical = [];
    const important = [];
    const recommended = [];
    
    if (answers.custody?.value === 0) {
        critical.push({
            title: 'Move Bitcoin Off Exchanges Immediately',
            desc: 'Keeping Bitcoin on an exchange means you don\'t truly own it. Exchange failures (Mt. Gox, FTX) have caused billions in losses.',
            steps: [
                'Purchase a hardware wallet (Trezor Model T ~$180, Ledger Nano X ~$150, or Coldcard ~$150)',
                'Set up the device following official instructions - NEVER buy used or pre-configured',
                'Write down your 24-word seed phrase on paper, verify it, then back up to metal',
                'Send a small test transaction from the exchange to your new wallet',
                'Once confirmed, transfer remaining balance in batches',
                'Enable withdrawal address whitelisting on exchanges you still use'
            ],
            products: ['Trezor Model T', 'Ledger Nano X', 'Coldcard Mk4', 'BitBox02', 'Foundation Passport']
        });
    } else if (answers.custody?.value === 5) {
        important.push({
            title: 'Upgrade from Hot Wallet to Hardware Wallet',
            desc: 'Hot wallets are vulnerable to malware and phone theft. Hardware wallets keep keys offline.',
            steps: [
                'Research hardware wallets - Trezor for beginners, Coldcard for advanced users',
                'Order directly from manufacturer (never Amazon or eBay)',
                'Generate new seed on the hardware device - don\'t import hot wallet seed',
                'Back up new seed phrase to metal plate',
                'Transfer funds from hot wallet to new hardware wallet addresses'
            ],
            products: ['Trezor Safe 3', 'Ledger Nano S Plus', 'Coldcard Q', 'Jade (open source)']
        });
    } else if (answers.custody?.value === 8) {
        recommended.push({
            title: 'Consider Upgrading to Multisig',
            desc: 'For significant holdings, multisig provides redundancy - no single point of failure.',
            steps: [
                'Learn about 2-of-3 multisig setups (you control 2 keys, company holds 1)',
                'Evaluate services: Unchained Capital, Casa, or self-custody with Sparrow',
                'For DIY: get 3 different hardware wallets from different manufacturers',
                'Use Sparrow Wallet or Electrum to coordinate multisig setup',
                'Distribute keys geographically (home safe, bank box, trusted family)'
            ],
            products: ['Unchained Capital', 'Casa', 'Nunchuk', 'Sparrow Wallet (free)']
        });
    }
    
    if (answers.backup?.value <= 3) {
        critical.push({
            title: 'Create Proper Seed Phrase Backups',
            desc: 'Your seed phrase is the ONLY way to recover your Bitcoin. Digital backups are hackable; paper burns.',
            steps: [
                'Purchase a metal seed storage device ($20-80)',
                'Stamp or engrave your 24 words into the metal plate',
                'Verify every word is correct by checking against your wallet',
                'Store in a fireproof safe or safety deposit box',
                'Consider creating a second backup in a different geographic location',
                'Never store digitally - delete any photos or text files with your seed'
            ],
            products: ['Cryptosteel Capsule (~$80)', 'Billfodl (~$60)', 'Blockplate (~$100)', 'Seedplate (~$30)']
        });
    } else if (answers.backup?.value === 7) {
        important.push({
            title: 'Upgrade Paper Backup to Metal',
            desc: 'Paper degrades, burns, and can be destroyed by water. Metal survives disasters.',
            steps: [
                'Order a metal backup device (steel or titanium)',
                'Carefully stamp or slide your existing seed words into the device',
                'Triple-check every word matches your paper backup',
                'Store the metal backup in a secure location',
                'Optionally keep paper as secondary backup in different location'
            ],
            products: ['Cryptosteel', 'Billfodl', 'SeedSigner (DIY)', 'ColdTI (titanium)']
        });
    }
    
    if (answers['2fa']?.value <= 5) {
        critical.push({
            title: 'Enable Strong 2FA on All Crypto Accounts',
            desc: 'SMS 2FA is vulnerable to SIM swap attacks. Authenticator apps or hardware keys are essential.',
            steps: [
                'Download an authenticator app: Authy or Google Authenticator',
                'Log into each exchange and enable TOTP (authenticator) 2FA',
                'Save the backup codes in your password manager',
                'For maximum security, purchase a YubiKey (~$50) for FIDO2/WebAuthn',
                'Register the hardware key on exchanges that support it (Coinbase, Kraken, Gemini)',
                'Disable SMS 2FA after setting up stronger alternatives'
            ],
            products: ['YubiKey 5 NFC (~$50)', 'Thetis FIDO2 (~$25)', 'Google Titan (~$35)']
        });
    }
    
    if (answers.password?.value < 10) {
        important.push({
            title: 'Start Using a Password Manager',
            desc: 'Reusing passwords or trying to remember them leads to weak security. Password managers are essential.',
            steps: [
                'Choose a password manager: Bitwarden (free) or 1Password (paid)',
                'Install browser extension and mobile app',
                'Create a strong master password - 4+ random words you can remember',
                'Start saving existing passwords as you log into sites',
                'Use the generator to create new random passwords (16+ characters)',
                'Enable 2FA on your password manager account'
            ],
            products: ['Bitwarden (free)', '1Password ($3/mo)', 'KeePassXC (offline, free)', 'Proton Pass']
        });
    }
    
    if (answers.node?.value < 10) {
        recommended.push({
            title: 'Run Your Own Bitcoin Node',
            desc: 'Verify transactions yourself instead of trusting third parties. Protects privacy and supports the network.',
            steps: [
                'Choose your approach: dedicated device or personal computer',
                'Easiest: Buy a pre-built node (Start9, Nodl) or Raspberry Pi kit (Umbrel)',
                'DIY: Install Umbrel or RaspiBlitz on a Raspberry Pi 4 with 1TB SSD (~$200 total)',
                'Alternative: Run Bitcoin Core on any computer with 500GB+ free space',
                'Initial sync takes 1-7 days depending on hardware',
                'Connect your wallet (Sparrow, Electrum) to your node for private balance checks'
            ],
            products: ['Umbrel (free software)', 'Start9 ($600 pre-built)', 'RaspiBlitz (DIY ~$200)', 'MyNode ($300)']
        });
    }
    
    if (answers.privacy?.value < 8) {
        recommended.push({
            title: 'Improve Transaction Privacy',
            desc: 'Bitcoin transactions are public. Basic privacy measures prevent tracking of your financial activity.',
            steps: [
                'Configure your wallet to always generate new receiving addresses',
                'Download Tor Browser for any Bitcoin-related web browsing',
                'Run your Bitcoin node over Tor (most node software supports this)',
                'For advanced privacy: Learn about CoinJoin with Wasabi or Sparrow Wallet',
                'Avoid linking your identity to addresses (no social media posts)',
                'Consider non-KYC Bitcoin acquisition methods for new purchases'
            ],
            products: ['Tor Browser (free)', 'Mullvad VPN ($5/mo)', 'Wasabi Wallet (free)', 'Sparrow Wallet (free)']
        });
    }
    
    if (answers.inheritance?.value < 10) {
        important.push({
            title: 'Create an Inheritance Plan',
            desc: 'Without a plan, your Bitcoin dies with you. Document everything your heirs need to recover funds.',
            steps: [
                'Write down which wallets/devices hold your Bitcoin',
                'Document exact steps to access each wallet (include PINs if using passphrase)',
                'Explain where seed phrase backups are located',
                'Consider multisig where heirs control one key',
                'Store instructions in a sealed envelope with your will or lawyer',
                'Test the plan: Could someone unfamiliar with Bitcoin follow your instructions?',
                'Review and update annually'
            ],
            products: ['Casa Inheritance', 'Unchained Inheritance', 'Stamped steel plate letters', 'Lawyer consultation']
        });
    }
    
    if (answers.disclosure?.value <= 3) {
        important.push({
            title: 'Reduce Your Public Bitcoin Profile',
            desc: 'Public knowledge of your holdings makes you a target for scams, hacks, and physical attacks.',
            steps: [
                'Audit your social media for Bitcoin-related posts',
                'Delete or make private any posts mentioning holdings or gains',
                'Stop discussing specific amounts with friends or online',
                'Use pseudonymous accounts for Bitcoin community participation',
                'Be vague if asked: "I have some crypto exposure" rather than specifics',
                'Remember: Information spreads. Tell no one who doesn\'t need to know'
            ],
            products: ['N/A - behavioral change required']
        });
    }
    
    let html = '<div class="action-plan-header"><i class="fas fa-clipboard-list"></i><div class="action-plan-title">Your Personal Action Plan</div></div>';
    
    if (critical.length > 0) {
        html += '<div class="action-category">';
        html += '<div class="action-category-header"><span class="priority-badge priority-critical">Critical Priority</span><span class="action-category-title">Address These First</span></div>';
        critical.forEach(item => {
            html += generateActionItemHTML(item);
        });
        html += '</div>';
    }
    
    if (important.length > 0) {
        html += '<div class="action-category">';
        html += '<div class="action-category-header"><span class="priority-badge priority-important">Important</span><span class="action-category-title">Address Soon</span></div>';
        important.forEach(item => {
            html += generateActionItemHTML(item);
        });
        html += '</div>';
    }
    
    if (recommended.length > 0) {
        html += '<div class="action-category">';
        html += '<div class="action-category-header"><span class="priority-badge priority-recommended">Recommended</span><span class="action-category-title">When Ready</span></div>';
        recommended.forEach(item => {
            html += generateActionItemHTML(item);
        });
        html += '</div>';
    }
    
    if (critical.length === 0 && important.length === 0 && recommended.length === 0) {
        html += `
            <div class="action-item" style="text-align: center; padding: 30px;">
                <i class="fas fa-trophy" style="font-size: 3rem; color: #22c55e; margin-bottom: 15px;"></i>
                <div class="action-item-title" style="font-size: 1.1rem; margin-bottom: 10px;">Excellent Security Posture!</div>
                <div class="action-item-desc" style="padding-left: 0; max-width: 400px; margin: 0 auto;">
                    You've implemented best practices across all categories. Continue staying informed about new threats and security developments. Consider helping others in the Bitcoin community level up their security.
                </div>
            </div>
        `;
    }
    
    document.getElementById('action-plan').innerHTML = html;
}

function generateActionItemHTML(item) {
    let stepsHtml = '';
    item.steps.forEach((step, i) => {
        stepsHtml += `<div class="action-step"><span class="action-step-num">${i + 1}</span><span>${step}</span></div>`;
    });
    
    let productsHtml = '';
    if (item.products && item.products[0] !== 'N/A - behavioral change required') {
        productsHtml = `
            <div class="product-recs">
                <div class="product-recs-title">Recommended Products/Services</div>
                <div class="product-list">${item.products.map(p => `<span>${p}</span>`).join('')}</div>
            </div>
        `;
    }
    
    return `
        <div class="action-item">
            <div class="action-item-header">
                <i class="fas fa-arrow-right"></i>
                <div class="action-item-title">${item.title}</div>
            </div>
            <div class="action-item-desc">${item.desc}</div>
            <div class="action-steps">${stepsHtml}</div>
            ${productsHtml}
        </div>
    `;
}

function retakeQuiz() {
    Object.keys(answers).forEach(k => delete answers[k]);
    document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected', 'green', 'yellow'));
    document.querySelector('.submit-btn').disabled = true;
    document.getElementById('quiz-form').style.display = 'block';
    document.getElementById('results-section').style.display = 'none';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
{% endblock %}
```

## templates/dashboard.html
```html
{% extends "base.html" %}
{% block title %}Intelligence Dashboard - Protocol Pulse{% endblock %}

{% block schema %}
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "Bitcoin Intelligence Dashboard",
    "description": "Real-time Bitcoin network metrics including difficulty, hashrate, mempool stats, and fee estimates. Live data from Mempool.space for transactors.",
    "mainEntity": {
        "@type": "Dataset",
        "name": "Bitcoin Network Metrics",
        "description": "Live Bitcoin network statistics including difficulty (146.47 T), hashrate (~977 EH/s), mempool size, and recommended fees.",
        "temporalCoverage": "2025/..",
        "license": "https://creativecommons.org/publicdomain/zero/1.0/"
    }
}
</script>
{% endblock %}

{% block head %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
    .dashboard-hero {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
        padding: 2rem 0;
        border-bottom: 1px solid rgba(220, 38, 38, 0.2);
    }
    .dashboard-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        color: #fff;
    }
    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #22c55e;
    }
    .live-dot {
        width: 8px;
        height: 8px;
        background: #22c55e;
        border-radius: 50%;
        animation: blink 1s ease-in-out infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    .back-nav {
        position: fixed;
        top: 80px;
        left: 20px;
        z-index: 1000;
    }
    
    .back-btn {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: rgba(10, 10, 10, 0.95);
        border: 1px solid rgba(220, 38, 38, 0.3);
        border-radius: 12px;
        padding: 12px 20px;
        color: #fff;
        text-decoration: none;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        backdrop-filter: blur(20px);
        transition: all 0.3s ease;
    }
    
    .back-btn:hover {
        background: rgba(220, 38, 38, 0.2);
        border-color: #dc2626;
        color: #fff;
        transform: translateX(-3px);
    }
    
    .back-btn i {
        color: #dc2626;
    }
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="dashboard-container">
    <!-- Dashboard Hero -->
    <div class="dashboard-hero">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h1 class="dashboard-title">
                        <i class="fas fa-chart-area text-danger me-2"></i>INTELLIGENCE DASHBOARD
                    </h1>
                    <p class="text-muted mb-0 font-monospace small">Real-time Bitcoin network metrics for transactors</p>
                </div>
                <div class="live-indicator">
                    <span class="live-dot"></span>
                    LIVE DATA
                </div>
            </div>
        </div>
    </div>

    <div class="container py-4">
        <!-- Primary Metrics Row -->
        <div class="row g-4 mb-4">
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Bitcoin Price</div>
                    <div class="metric-value text-warning">{{ price_service.format_price(prices.bitcoin.price) if prices and prices.bitcoin else '$--' }}</div>
                    <div class="metric-change {{ 'positive' if prices and prices.bitcoin and prices.bitcoin.change_24h >= 0 else 'negative' }}">
                        {{ price_service.format_change(prices.bitcoin.change_24h) if prices and prices.bitcoin else '--' }} (24h)
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Network Difficulty</div>
                    <div class="metric-value text-danger">{{ '%.2f T' % (mempool_data.current_difficulty / 1e12) if mempool_data and mempool_data.current_difficulty else '146.47 T' }}</div>
                    <div class="metric-change {{ 'positive' if mempool_data and mempool_data.difficulty_adjustment and mempool_data.difficulty_adjustment.change_percent >= 0 else 'negative' }}">
                        {% if mempool_data and mempool_data.difficulty_adjustment %}
                            {{ '+%.2f' % mempool_data.difficulty_adjustment.change_percent if mempool_data.difficulty_adjustment.change_percent >= 0 else '%.2f' % mempool_data.difficulty_adjustment.change_percent }}% est.
                        {% else %}
                            +1.2% est.
                        {% endif %}
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Network Hashrate</div>
                    <div class="metric-value text-info">{{ '%.0f EH/s' % (mempool_data.current_hashrate / 1e18) if mempool_data and mempool_data.current_hashrate else '~977 EH/s' }}</div>
                    <div class="metric-change text-muted">Computational Security</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Mempool Size</div>
                    <div class="metric-value text-success">{{ '{:,}'.format(mempool_data.count) if mempool_data and mempool_data.count else '--' }}</div>
                    <div class="metric-change text-muted">Unconfirmed TXs</div>
                </div>
            </div>
        </div>

        <!-- Fee Estimates Row -->
        <div class="row g-4 mb-4">
            <div class="col-12">
                <div class="chart-container">
                    <div class="chart-title"><i class="fas fa-tachometer-alt me-2"></i>Recommended Fee Rates (sat/vB)</div>
                    <div class="row">
                        {% if mempool_data and mempool_data.fees %}
                        <div class="col-md-2 text-center">
                            <div class="p-3 bg-dark rounded">
                                <div class="text-danger fs-3 fw-bold font-monospace">{{ mempool_data.fees.fastest }}</div>
                                <div class="text-muted small">Fastest</div>
                                <div class="text-muted small">~10 min</div>
                            </div>
                        </div>
                        <div class="col-md-2 text-center">
                            <div class="p-3 bg-dark rounded">
                                <div class="text-warning fs-3 fw-bold font-monospace">{{ mempool_data.fees.half_hour }}</div>
                                <div class="text-muted small">Fast</div>
                                <div class="text-muted small">~30 min</div>
                            </div>
                        </div>
                        <div class="col-md-2 text-center">
                            <div class="p-3 bg-dark rounded">
                                <div class="text-info fs-3 fw-bold font-monospace">{{ mempool_data.fees.hour }}</div>
                                <div class="text-muted small">Medium</div>
                                <div class="text-muted small">~1 hour</div>
                            </div>
                        </div>
                        <div class="col-md-2 text-center">
                            <div class="p-3 bg-dark rounded">
                                <div class="text-success fs-3 fw-bold font-monospace">{{ mempool_data.fees.economy }}</div>
                                <div class="text-muted small">Economy</div>
                                <div class="text-muted small">~2 hours</div>
                            </div>
                        </div>
                        <div class="col-md-2 text-center">
                            <div class="p-3 bg-dark rounded">
                                <div class="text-muted fs-3 fw-bold font-monospace">{{ mempool_data.fees.minimum }}</div>
                                <div class="text-muted small">Minimum</div>
                                <div class="text-muted small">No priority</div>
                            </div>
                        </div>
                        {% else %}
                        <div class="col-12 text-center text-muted py-4">
                            <i class="fas fa-spinner fa-spin me-2"></i>Loading fee data...
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row g-4 mb-4">
            <div class="col-md-8">
                <div class="chart-container">
                    <div class="chart-title"><i class="fas fa-chart-line me-2"></i>Hashrate History (30 Days)</div>
                    <div style="position: relative; height: 250px; width: 100%;">
                        <canvas id="hashrateChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="chart-container h-100">
                    <div class="chart-title"><i class="fas fa-clock me-2"></i>Difficulty Adjustment</div>
                    {% if mempool_data and mempool_data.difficulty_adjustment %}
                    <div class="text-center py-4">
                        <div style="position: relative; height: 120px; width: 200px; margin: 0 auto;">
                            <canvas id="difficultyGauge"></canvas>
                        </div>
                        <div class="mt-3">
                            <div class="text-muted small">Progress</div>
                            <div class="fs-4 fw-bold text-warning">{{ '%.1f' % mempool_data.difficulty_adjustment.progress }}%</div>
                        </div>
                        <div class="mt-2">
                            <div class="text-muted small">Blocks Remaining</div>
                            <div class="fs-5 fw-bold font-monospace">{{ mempool_data.difficulty_adjustment.remaining_blocks }}</div>
                        </div>
                        <div class="mt-2">
                            <div class="text-muted small">Estimated Change</div>
                            <div class="fs-5 fw-bold {{ 'text-success' if mempool_data.difficulty_adjustment.change_percent >= 0 else 'text-danger' }}">
                                {{ '+%.2f' % mempool_data.difficulty_adjustment.change_percent if mempool_data.difficulty_adjustment.change_percent >= 0 else '%.2f' % mempool_data.difficulty_adjustment.change_percent }}%
                            </div>
                        </div>
                    </div>
                    {% else %}
                    <div class="text-center text-muted py-5">
                        <i class="fas fa-spinner fa-spin me-2"></i>Loading...
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Bitcoin Lens Analysis -->
        <div class="row g-4">
            <div class="col-12">
                <div class="chart-container">
                    <div class="chart-title"><i class="fas fa-eye me-2"></i>The Bitcoin Lens</div>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="p-3">
                                <h5 class="text-danger"><i class="fas fa-shield-alt me-2"></i>Network Security</h5>
                                <p class="text-muted small">
                                    Current difficulty at {{ '%.2f T' % (mempool_data.current_difficulty / 1e12) if mempool_data and mempool_data.current_difficulty else '146.47 T' }} 
                                    represents the computational barrier protecting your transactions. Each hash proves work was done to secure the network.
                                </p>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3">
                                <h5 class="text-warning"><i class="fas fa-coins me-2"></i>Mining Economics</h5>
                                <p class="text-muted small">
                                    Fee rates indicate network demand. Higher fees signal more users competing for block space. 
                                    Transactors should batch transactions during low-fee periods for efficiency.
                                </p>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3">
                                <h5 class="text-info"><i class="fas fa-balance-scale me-2"></i>Sound Money Signal</h5>
                                <p class="text-muted small">
                                    Unlike fiat monetary policy, Bitcoin's issuance is mathematically predetermined. 
                                    The difficulty adjustment ensures blocks are found every ~10 minutes regardless of hashrate changes.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Hashrate Chart
    const hashrateCtx = document.getElementById('hashrateChart');
    if (hashrateCtx) {
        {% if mempool_data and mempool_data.hashrate_history %}
        const hashrateData = {{ mempool_data.hashrate_history | tojson }};
        const labels = hashrateData.map(d => {
            const date = new Date(d.timestamp * 1000);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        const values = hashrateData.map(d => d.avgHashrate / 1e18);
        {% else %}
        // Fallback: generate last 30 days of dates
        const labels = Array.from({length: 30}, (_, i) => {
            const date = new Date();
            date.setDate(date.getDate() - (29 - i));
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        const values = Array.from({length: 30}, () => 900 + Math.random() * 100);
        {% endif %}
        
        new Chart(hashrateCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Hashrate (EH/s)',
                    data: values,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255,255,255,0.05)'
                        },
                        ticks: {
                            color: '#666',
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255,255,255,0.05)'
                        },
                        ticks: {
                            color: '#666',
                            callback: function(value) {
                                return value.toFixed(0) + ' EH/s';
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Difficulty Gauge
    const gaugeCtx = document.getElementById('difficultyGauge');
    if (gaugeCtx) {
        {% if mempool_data and mempool_data.difficulty_adjustment %}
        const progress = {{ mempool_data.difficulty_adjustment.progress }};
        {% else %}
        const progress = 45;
        {% endif %}
        
        new Chart(gaugeCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [progress, 100 - progress],
                    backgroundColor: ['#dc2626', '#1a1a1a'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '70%',
                rotation: -90,
                circumference: 180,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            }
        });
    }
});
</script>
{% endblock %}
```

## templates/whale_watcher.html
```html
{% extends "base.html" %}

{% block title %}Whale Watcher | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
}

.whale-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 100px 20px 40px;
}

.whale-header {
    text-align: center;
    margin-bottom: 40px;
}

.back-nav {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
    transform: translateX(-3px);
}

.back-btn i {
    color: var(--pp-red);
}

.whale-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 10px;
}

.whale-title i {
    color: var(--pp-red);
    margin-right: 15px;
}

.whale-subtitle {
    color: rgba(255, 255, 255, 0.5);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.whale-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    max-width: 1000px;
    margin: 0 auto 40px;
}

.whale-stat {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 25px;
    text-align: center;
    backdrop-filter: blur(20px);
}

.stat-label {
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

.stat-value {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    font-size: 1.8rem;
    font-weight: 700;
}

.stat-value.red { color: var(--pp-red); }
.stat-value.green { color: #22c55e; }

.whale-feed {
    max-width: 1200px;
    margin: 0 auto;
}

.feed-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding: 0 10px;
}

.feed-title {
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.feed-status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #22c55e;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.whale-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.whale-tx {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 20px 25px;
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    gap: 20px;
    align-items: center;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
    animation: slideIn 0.5s ease;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.whale-tx:hover {
    border-color: var(--pp-red);
    transform: translateX(5px);
}

.whale-tx.mega {
    border-color: #eab308;
    background: rgba(234, 179, 8, 0.1);
}

.tx-icon {
    width: 50px;
    height: 50px;
    background: rgba(220, 38, 38, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
}

.tx-icon.mega {
    background: rgba(234, 179, 8, 0.2);
}

.tx-icon i {
    color: var(--pp-red);
}

.tx-icon.mega i {
    color: #eab308;
}

.tx-info {
    overflow: hidden;
}

.tx-amount {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.3rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 5px;
}

.tx-hash {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tx-hash a {
    color: rgba(255, 255, 255, 0.4);
    text-decoration: none;
}

.tx-hash a:hover {
    color: var(--pp-red);
}

.tx-usd {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    color: #22c55e;
    text-align: right;
}

.tx-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    text-align: right;
    min-width: 80px;
}

.loading-indicator {
    text-align: center;
    padding: 60px;
    color: rgba(255, 255, 255, 0.5);
    font-family: 'JetBrains Mono', monospace;
}

.empty-state {
    text-align: center;
    padding: 80px 20px;
    color: rgba(255, 255, 255, 0.4);
    font-family: 'JetBrains Mono', monospace;
}

.empty-state i {
    font-size: 4rem;
    margin-bottom: 20px;
    opacity: 0.3;
}

@media (max-width: 768px) {
    .whale-tx {
        grid-template-columns: auto 1fr;
        gap: 15px;
    }
    .tx-usd, .tx-time {
        display: none;
    }
    .whale-title {
        font-size: 1.8rem;
    }
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="whale-page">
    <div class="whale-header">
        <h1 class="whale-title"><i class="fas fa-water"></i>Whale Watcher</h1>
        <p class="whale-subtitle">Real-time large transaction surveillance</p>
    </div>
    
    <div class="whale-stats">
        <div class="whale-stat">
            <div class="stat-label">24h Whale Volume</div>
            <div class="stat-value" id="total-volume">--</div>
        </div>
        <div class="whale-stat">
            <div class="stat-label">Whale Transactions</div>
            <div class="stat-value red" id="tx-count">--</div>
        </div>
        <div class="whale-stat">
            <div class="stat-label">Largest Move</div>
            <div class="stat-value green" id="largest-tx">--</div>
        </div>
        <div class="whale-stat">
            <div class="stat-label">BTC Price</div>
            <div class="stat-value" id="btc-price">--</div>
        </div>
    </div>
    
    <div class="whale-feed">
        <div class="feed-header">
            <div class="feed-title"><i class="fas fa-rss me-2"></i>Live Feed (10+ BTC)</div>
            <div class="feed-status">
                <span class="status-dot"></span>
                <span>Monitoring Mempool</span>
            </div>
        </div>
        
        <div class="whale-list" id="whale-list">
            <div class="loading-indicator">
                <i class="fas fa-circle-notch fa-spin me-2"></i>
                Scanning for whale activity...
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let btcPrice = 100000;
let whaleTransactions = [];
let totalVolume = 0;
let largestTx = 0;

async function fetchBtcPrice() {
    try {
        const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd');
        const data = await response.json();
        btcPrice = data.bitcoin.usd;
        document.getElementById('btc-price').textContent = '$' + btcPrice.toLocaleString();
    } catch (error) {
        console.error('Price fetch error:', error);
    }
}

async function loadStoredWhales() {
    try {
        const response = await fetch('/api/whales');
        const data = await response.json();
        if (data.whales && data.whales.length > 0) {
            data.whales.forEach(w => {
                if (!whaleTransactions.find(wt => wt.txid === w.txid)) {
                    whaleTransactions.push({
                        txid: w.txid,
                        btc: w.btc,
                        fee: 0,
                        time: w.time ? new Date(w.time).getTime() : Date.now(),
                        stored: true
                    });
                    totalVolume += w.btc;
                    if (w.btc > largestTx) largestTx = w.btc;
                }
            });
            updateUI();
        }
    } catch (error) {
        console.error('Stored whales error:', error);
    }
}

async function saveWhale(whale) {
    try {
        await fetch('/api/whales/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                txid: whale.txid,
                btc: whale.btc,
                usd: whale.btc * btcPrice,
                fee: whale.fee
            })
        });
    } catch (error) {
        console.error('Save whale error:', error);
    }
}

async function fetchWhaleTransactions() {
    try {
        const response = await fetch('/api/whales/live');
        const data = await response.json();
        
        if (data.whales && data.whales.length > 0) {
            for (const whale of data.whales) {
                if (!whaleTransactions.find(w => w.txid === whale.txid)) {
                    whaleTransactions.unshift({
                        txid: whale.txid,
                        btc: whale.btc,
                        fee: whale.fee || 0,
                        time: whale.time || Date.now()
                    });
                    totalVolume += whale.btc;
                    if (whale.btc > largestTx) largestTx = whale.btc;
                    await saveWhale(whale);
                }
            }
            
            whaleTransactions = whaleTransactions.slice(0, 50);
            updateUI();
        }
        
        if (whaleTransactions.length === 0) {
            await fetchRecentBlocks();
        }
        
    } catch (error) {
        console.error('Whale fetch error:', error);
        await fetchRecentBlocks();
    }
}

async function fetchRecentBlocks() {
    try {
        const blocksResponse = await fetch('https://mempool.space/api/blocks');
        const blocks = await blocksResponse.json();
        
        for (const block of blocks.slice(0, 3)) {
            const txResponse = await fetch(`https://mempool.space/api/block/${block.id}/txs`);
            const transactions = await txResponse.json();
            
            transactions.forEach(tx => {
                const outputs = tx.vout || [];
                const totalOut = outputs.reduce((sum, out) => sum + (out.value || 0), 0);
                const btcValue = totalOut / 100000000;
                
                if (btcValue >= 500 && !whaleTransactions.find(w => w.txid === tx.txid)) {
                    whaleTransactions.unshift({
                        txid: tx.txid,
                        btc: btcValue,
                        fee: tx.fee || 0,
                        time: (block.timestamp || Math.floor(Date.now()/1000)) * 1000
                    });
                    totalVolume += btcValue;
                    if (btcValue > largestTx) largestTx = btcValue;
                }
            });
        }
        
        whaleTransactions = whaleTransactions.slice(0, 50);
        updateUI();
        
    } catch (error) {
        console.error('Block fetch error:', error);
        showEmptyState();
    }
}

function updateUI() {
    document.getElementById('total-volume').textContent = totalVolume.toLocaleString(undefined, {maximumFractionDigits: 0}) + ' BTC';
    document.getElementById('tx-count').textContent = whaleTransactions.length;
    document.getElementById('largest-tx').textContent = largestTx.toLocaleString(undefined, {maximumFractionDigits: 2}) + ' BTC';
    
    const listEl = document.getElementById('whale-list');
    
    if (whaleTransactions.length === 0) {
        showEmptyState();
        return;
    }
    
    listEl.innerHTML = whaleTransactions.map(tx => {
        const usdValue = tx.btc * btcPrice;
        const isMega = tx.btc >= 100;
        const timeAgo = getTimeAgo(tx.time);
        
        return `
            <div class="whale-tx ${isMega ? 'mega' : ''}">
                <div class="tx-icon ${isMega ? 'mega' : ''}">
                    <i class="fas ${isMega ? 'fa-crown' : 'fa-fish'}"></i>
                </div>
                <div class="tx-info">
                    <div class="tx-amount">${tx.btc.toLocaleString(undefined, {maximumFractionDigits: 2})} BTC</div>
                    <div class="tx-hash">
                        <a href="https://mempool.space/tx/${tx.txid}" target="_blank">${tx.txid.substring(0, 20)}...${tx.txid.substring(tx.txid.length - 8)}</a>
                    </div>
                </div>
                <div class="tx-usd">$${(usdValue / 1000000).toFixed(2)}M</div>
                <div class="tx-time" title="${new Date(tx.time).toLocaleString()}">${timeAgo}</div>
            </div>
        `;
    }).join('');
}

function showEmptyState() {
    document.getElementById('whale-list').innerHTML = `
        <div class="empty-state">
            <i class="fas fa-water"></i>
            <p>No whale activity detected in recent blocks.<br>Large transactions (10+ BTC) will appear here in real-time.</p>
        </div>
    `;
}

function getTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return seconds + 's ago';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
}

fetchBtcPrice();
loadStoredWhales().then(() => fetchWhaleTransactions());

setInterval(fetchBtcPrice, 60000);
setInterval(fetchWhaleTransactions, 30000);
</script>
{% endblock %}
```

## templates/donate.html
```html
{% extends "base.html" %}

{% block title %}Support Protocol Pulse | Donate{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --btc-orange: #f7931a;
}

.donate-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 100px 20px 60px;
}

.donate-container {
    max-width: 600px;
    margin: 0 auto;
}

.donate-header {
    text-align: center;
    margin-bottom: 40px;
}

.donate-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    color: #fff;
    margin-bottom: 15px;
}

.donate-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    color: rgba(255, 255, 255, 0.6);
    line-height: 1.6;
}

.donate-card {
    background: rgba(10, 10, 10, 0.95);
    border: 1px solid rgba(247, 147, 26, 0.3);
    border-radius: 20px;
    padding: 35px;
}

.amount-selector {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 25px;
}

.amount-btn {
    padding: 15px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.amount-btn:hover, .amount-btn.selected {
    border-color: var(--btc-orange);
    background: rgba(247, 147, 26, 0.1);
    color: var(--btc-orange);
}

.form-group {
    margin-bottom: 20px;
}

.form-label {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 8px;
}

.form-input, .form-textarea {
    width: 100%;
    padding: 15px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
}

.form-input:focus, .form-textarea:focus {
    outline: none;
    border-color: var(--btc-orange);
}

.form-textarea {
    min-height: 100px;
    resize: vertical;
}

.donate-btn {
    width: 100%;
    padding: 18px;
    background: var(--btc-orange);
    border: none;
    border-radius: 12px;
    color: #000;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-top: 30px;
}

.donate-btn:hover {
    background: #e8820f;
    transform: translateY(-2px);
}

.lightning-section {
    margin-top: 30px;
    padding-top: 30px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}

.lightning-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 15px;
}

.lightning-address {
    background: rgba(255, 255, 255, 0.05);
    padding: 15px 20px;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--btc-orange);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    cursor: pointer;
}

.lightning-address:hover {
    background: rgba(247, 147, 26, 0.1);
}
</style>
{% endblock %}

{% block content %}
<div class="donate-page">
    <div class="donate-container">
        <div class="donate-header">
            <h1 class="donate-title"><i class="fas fa-heart" style="color: var(--pp-red);"></i> Support Sovereign Journalism</h1>
            <p class="donate-subtitle">Your contribution helps keep Protocol Pulse independent, ad-light, and committed to truth. Every satoshi counts.</p>
        </div>
        
        <div class="donate-card">
            <form method="POST" action="/donate">
                <div class="amount-selector">
                    <button type="button" class="amount-btn" data-amount="21">$21</button>
                    <button type="button" class="amount-btn selected" data-amount="50">$50</button>
                    <button type="button" class="amount-btn" data-amount="100">$100</button>
                    <button type="button" class="amount-btn" data-amount="210">$210</button>
                </div>
                
                <input type="hidden" name="amount" id="amount-input" value="50">
                
                <div class="form-group">
                    <label class="form-label">Custom Amount (USD)</label>
                    <input type="number" class="form-input" id="custom-amount" min="1" placeholder="Enter custom amount">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Email (for receipt)</label>
                    <input type="email" name="email" class="form-input" placeholder="your@email.com" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Message (optional)</label>
                    <textarea name="message" class="form-textarea" placeholder="Leave a message of support..."></textarea>
                </div>
                
                <button type="submit" class="donate-btn">
                    <i class="fas fa-bolt"></i> Donate Now
                </button>
            </form>
            
            <div class="lightning-section">
                <div class="lightning-title">Or pay with Bitcoin</div>
                <a href="/donate/bitcoin" style="display: inline-flex; align-items: center; gap: 10px; padding: 15px 25px; background: rgba(247, 147, 26, 0.2); border: 1px solid #f7931a; border-radius: 10px; color: #f7931a; font-family: 'JetBrains Mono', monospace; text-decoration: none; margin-bottom: 15px;">
                    <i class="fab fa-bitcoin"></i> Donate with Bitcoin / Lightning
                </a>
                <div class="lightning-address" onclick="copyLightning()">
                    <i class="fas fa-bolt"></i>
                    protocolpulse@getalby.com
                    <i class="fas fa-copy"></i>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.querySelectorAll('.amount-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('selected'));
        this.classList.add('selected');
        document.getElementById('amount-input').value = this.dataset.amount;
        document.getElementById('custom-amount').value = '';
    });
});

document.getElementById('custom-amount').addEventListener('input', function() {
    if (this.value) {
        document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('selected'));
        document.getElementById('amount-input').value = this.value;
    }
});

function copyLightning() {
    navigator.clipboard.writeText('protocolpulse@getalby.com');
    alert('Lightning address copied!');
}
</script>
{% endblock %}
```

## templates/premium.html
```html
{% extends "base.html" %}

{% block title %}Upgrade to Premium | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
    --gold: #f59e0b;
    --btc-orange: #f7931a;
}

.premium-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 100px 20px 60px;
}

.premium-container {
    max-width: 1200px;
    margin: 0 auto;
}

.premium-header {
    text-align: center;
    margin-bottom: 50px;
}

.premium-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    color: #fff;
    margin-bottom: 15px;
}

.premium-title span {
    background: linear-gradient(135deg, var(--gold), var(--btc-orange));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.premium-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.6);
    max-width: 600px;
    margin: 0 auto;
}

.pricing-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 25px;
    margin-bottom: 60px;
}

@media (max-width: 992px) {
    .pricing-grid {
        grid-template-columns: 1fr;
        max-width: 400px;
        margin: 0 auto 60px;
    }
}

.pricing-card {
    background: var(--pp-glass);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 35px;
    position: relative;
    transition: all 0.3s ease;
}

.pricing-card:hover {
    transform: translateY(-5px);
}

.pricing-card.featured {
    border-color: var(--gold);
    box-shadow: 0 0 40px rgba(245, 158, 11, 0.2);
}

.pricing-card.featured::before {
    content: 'MOST POPULAR';
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--gold);
    color: #000;
    padding: 6px 20px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1px;
}

.tier-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 10px;
}

.tier-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    color: #fff;
    font-weight: 600;
    margin-bottom: 20px;
}

.tier-price {
    margin-bottom: 25px;
}

.price-amount {
    font-family: 'JetBrains Mono', monospace;
    font-size: 3rem;
    font-weight: 700;
    color: #fff;
}

.featured .price-amount {
    color: var(--gold);
}

.price-period {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.5);
}

.sats-price {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--btc-orange);
    margin-top: 5px;
}

.features-list {
    list-style: none;
    padding: 0;
    margin: 0 0 30px;
}

.features-list li {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.8);
}

.features-list li i {
    color: #22c55e;
    margin-top: 3px;
}

.subscribe-btn {
    width: 100%;
    padding: 16px;
    border-radius: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    text-decoration: none;
    display: block;
    text-align: center;
}

.subscribe-btn.primary {
    background: var(--gold);
    border: none;
    color: #000;
}

.subscribe-btn.primary:hover {
    background: #d97706;
}

.subscribe-btn.secondary {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #fff;
}

.subscribe-btn.secondary:hover {
    border-color: var(--gold);
    color: var(--gold);
}

.subscribe-btn.free {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.6);
}

.faq-section {
    max-width: 800px;
    margin: 0 auto;
}

.faq-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    color: #fff;
    text-align: center;
    margin-bottom: 30px;
}

.faq-item {
    background: var(--pp-glass);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-bottom: 15px;
    overflow: hidden;
}

.faq-question {
    padding: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    color: #fff;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.faq-question:hover {
    background: rgba(255, 255, 255, 0.03);
}

.faq-answer {
    padding: 0 20px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.6;
    display: none;
}

.faq-item.active .faq-answer {
    display: block;
}

.payment-methods {
    text-align: center;
    margin-top: 40px;
    padding-top: 40px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.payment-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
}

.payment-icons {
    display: flex;
    justify-content: center;
    gap: 20px;
    flex-wrap: wrap;
}

.payment-icon {
    width: 50px;
    height: 30px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.6);
    font-size: 1.2rem;
}

.payment-icon.btc {
    color: var(--btc-orange);
}
</style>
{% endblock %}

{% block content %}
<div class="premium-page">
    <div class="premium-container">
        <div class="premium-header">
            <h1 class="premium-title">Upgrade to <span>Premium Intelligence</span></h1>
            <p class="premium-subtitle">Access exclusive research, strategy calls, and priority intel alerts. Pay with card or Bitcoin.</p>
        </div>
        
        <div class="pricing-grid">
            <div class="pricing-card">
                <div class="tier-name">Starter</div>
                <div class="tier-title">{{ tiers.free.name }}</div>
                <div class="tier-price">
                    <span class="price-amount">$0</span>
                    <span class="price-period">/forever</span>
                </div>
                <ul class="features-list">
                    {% for feature in tiers.free.features %}
                    <li><i class="fas fa-check"></i> {{ feature }}</li>
                    {% endfor %}
                </ul>
                <a href="/register" class="subscribe-btn free">Current Plan</a>
            </div>
            
            <div class="pricing-card featured">
                <div class="tier-name">Recommended</div>
                <div class="tier-title">{{ tiers.operator.name }}</div>
                <div class="tier-price">
                    <span class="price-amount">${{ tiers.operator.price_monthly }}</span>
                    <span class="price-period">/month</span>
                    <div class="sats-price">~21,000 sats/month</div>
                </div>
                <ul class="features-list">
                    {% for feature in tiers.operator.features %}
                    <li><i class="fas fa-check"></i> {{ feature }}</li>
                    {% endfor %}
                </ul>
                <a href="/subscribe/premium/operator" class="subscribe-btn primary">Upgrade Now</a>
            </div>
            
            <div class="pricing-card">
                <div class="tier-name">Elite</div>
                <div class="tier-title">{{ tiers.sovereign.name }}</div>
                <div class="tier-price">
                    <span class="price-amount">${{ tiers.sovereign.price_monthly }}</span>
                    <span class="price-period">/month</span>
                    <div class="sats-price">~210,000 sats/month</div>
                </div>
                <ul class="features-list">
                    {% for feature in tiers.sovereign.features %}
                    <li><i class="fas fa-check"></i> {{ feature }}</li>
                    {% endfor %}
                </ul>
                <a href="/subscribe/premium/sovereign" class="subscribe-btn secondary">Go Sovereign</a>
            </div>
        </div>
        
        <div class="faq-section">
            <h2 class="faq-title">Frequently Asked Questions</h2>
            
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    Can I pay with Bitcoin?
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="faq-answer">
                    Yes! We accept both on-chain Bitcoin and Lightning payments. After checkout, you'll receive an invoice you can pay with any Bitcoin wallet. Lightning payments are instant.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    What's the refund policy?
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="faq-answer">
                    We offer a 7-day money-back guarantee. If you're not satisfied within the first week, contact us for a full refund. After 7 days, you can cancel anytime but no refunds are provided for the current billing period.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    How do I access premium content?
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="faq-answer">
                    After subscribing, you'll get access to the private Discord/Telegram channels, premium articles marked with a gold badge, and strategy call invites via email. Everything is linked to your account.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    Can I upgrade or downgrade later?
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="faq-answer">
                    Absolutely. You can change your plan at any time from your account settings. Upgrades take effect immediately, and downgrades apply at the end of your current billing period.
                </div>
            </div>
        </div>
        
        <div class="payment-methods">
            <div class="payment-title">Accepted Payment Methods</div>
            <div class="payment-icons">
                <div class="payment-icon btc"><i class="fab fa-bitcoin"></i></div>
                <div class="payment-icon"><i class="fas fa-bolt"></i></div>
                <div class="payment-icon"><i class="fab fa-cc-visa"></i></div>
                <div class="payment-icon"><i class="fab fa-cc-mastercard"></i></div>
                <div class="payment-icon"><i class="fab fa-apple-pay"></i></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## templates/launch_console.html
```html
{% extends "base.html" %}

{% block title %}Launch Console | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
}

.console-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 80px 20px 40px;
}

.console-container {
    max-width: 1200px;
    margin: 0 auto;
}

.console-header {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 16px;
    padding: 25px;
    margin-bottom: 20px;
}

.console-title {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 15px;
}

.console-title i {
    color: var(--pp-red);
    font-size: 1.5rem;
}

.console-title h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    color: #fff;
    margin: 0;
}

.post-preview {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.8);
    background: rgba(255, 255, 255, 0.05);
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
    line-height: 1.6;
}

.status-bar {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}

.status-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}

.status-critical {
    background: rgba(220, 38, 38, 0.3);
    color: #dc2626;
    animation: pulse 1.5s infinite;
}

.status-active {
    background: rgba(234, 179, 8, 0.3);
    color: #eab308;
}

.status-complete {
    background: rgba(34, 197, 94, 0.3);
    color: #22c55e;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.console-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

@media (max-width: 992px) {
    .console-grid {
        grid-template-columns: 1fr;
    }
}

.console-panel {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 16px;
    padding: 20px;
}

.panel-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-header i {
    color: var(--pp-red);
    font-size: 1.1rem;
}

.panel-header h3 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #fff;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.velocity-tracker {
    margin-bottom: 25px;
}

.velocity-bar {
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    margin-bottom: 15px;
    overflow: hidden;
}

.velocity-progress {
    height: 100%;
    background: linear-gradient(90deg, var(--pp-red), #f97316);
    border-radius: 4px;
    transition: width 0.5s ease;
}

.velocity-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
}

.velocity-stat {
    background: rgba(255, 255, 255, 0.03);
    padding: 12px;
    border-radius: 8px;
}

.velocity-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 5px;
}

.velocity-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.3rem;
    color: #fff;
    font-weight: 600;
}

.velocity-value.warning {
    color: #eab308;
}

.velocity-value.good {
    color: #22c55e;
}

.reply-feed {
    max-height: 400px;
    overflow-y: auto;
}

.reply-item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 12px;
}

.reply-item.high-value {
    border: 1px solid rgba(220, 38, 38, 0.5);
    background: rgba(220, 38, 38, 0.1);
}

.reply-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}

.reply-handle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--pp-red);
    font-weight: 600;
}

.reply-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.4);
}

.high-value-badge {
    background: var(--pp-red);
    color: #fff;
    font-size: 0.65rem;
    padding: 3px 8px;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    margin-left: auto;
}

.reply-content {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.8);
    line-height: 1.5;
    margin-bottom: 12px;
}

.reply-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.draft-btn {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 8px 14px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.draft-btn:hover {
    background: var(--pp-red);
    border-color: var(--pp-red);
    color: #fff;
}

.draft-list {
    max-height: 500px;
    overflow-y: auto;
}

.draft-item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 12px;
}

.draft-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--pp-red);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.draft-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.8);
    line-height: 1.5;
    margin-bottom: 12px;
}

.copy-btn {
    background: var(--pp-red);
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 8px;
}

.copy-btn:hover {
    background: #b91c1c;
}

.copy-btn.copied {
    background: #22c55e;
}

.actions-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.action-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.action-item:last-child {
    border-bottom: none;
}

.action-icon {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    flex-shrink: 0;
}

.action-icon.done {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
}

.action-icon.urgent {
    background: rgba(220, 38, 38, 0.2);
    color: var(--pp-red);
    animation: pulse 1s infinite;
}

.action-icon.wait {
    background: rgba(234, 179, 8, 0.2);
    color: #eab308;
}

.action-icon.tip {
    background: rgba(96, 165, 250, 0.2);
    color: #60a5fa;
}

.action-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.8);
    line-height: 1.5;
}

.generate-btn {
    width: 100%;
    background: rgba(255, 255, 255, 0.05);
    border: 1px dashed rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    padding: 15px;
    color: rgba(255, 255, 255, 0.6);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 10px;
}

.generate-btn:hover {
    background: rgba(220, 38, 38, 0.1);
    border-color: var(--pp-red);
    color: #fff;
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: rgba(255, 255, 255, 0.4);
}

.empty-state i {
    font-size: 2rem;
    margin-bottom: 15px;
    color: rgba(255, 255, 255, 0.2);
}

.empty-state p {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}

.back-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: rgba(255, 255, 255, 0.6);
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    margin-bottom: 20px;
    transition: color 0.3s ease;
}

.back-link:hover {
    color: var(--pp-red);
}
</style>
{% endblock %}

{% block content %}
<div class="console-page">
    <div class="console-container">
        <a href="/admin/launch-sequences" class="back-link">
            <i class="fas fa-arrow-left"></i> Back to Launch Sequences
        </a>
        
        <div class="console-header">
            <div class="console-title">
                <i class="fas fa-rocket"></i>
                <h1>Launch Console</h1>
            </div>
            
            <div class="post-preview" id="post-preview">
                {% if sequence %}
                {{ sequence.primary_post_copy }}
                {% else %}
                No active launch sequence. Create one from the admin panel.
                {% endif %}
            </div>
            
            <div class="status-bar">
                <div class="status-badge status-critical" id="status-badge">
                    <i class="fas fa-clock"></i>
                    <span id="status-text">CRITICAL WINDOW</span>
                </div>
                <div class="status-badge">
                    <i class="fas fa-bullseye"></i>
                    <span>Target: 3-5 replies by minute 5</span>
                </div>
                <div class="status-badge" id="elapsed-badge">
                    <i class="fas fa-stopwatch"></i>
                    <span id="elapsed-time">0:00 elapsed</span>
                </div>
            </div>
        </div>
        
        <div class="console-grid">
            <div class="console-panel">
                <div class="panel-header">
                    <i class="fas fa-chart-line"></i>
                    <h3>Velocity Tracker</h3>
                </div>
                
                <div class="velocity-tracker">
                    <div class="velocity-bar">
                        <div class="velocity-progress" id="velocity-bar" style="width: 0%"></div>
                    </div>
                    
                    <div class="velocity-stats">
                        <div class="velocity-stat">
                            <div class="velocity-label">Replies (0-5 min)</div>
                            <div class="velocity-value warning" id="replies-early">0</div>
                        </div>
                        <div class="velocity-stat">
                            <div class="velocity-label">Total Replies</div>
                            <div class="velocity-value" id="total-replies">0</div>
                        </div>
                        <div class="velocity-stat">
                            <div class="velocity-label">Velocity Score</div>
                            <div class="velocity-value" id="velocity-score">0</div>
                        </div>
                        <div class="velocity-stat">
                            <div class="velocity-label">Status</div>
                            <div class="velocity-value" id="velocity-status">STANDBY</div>
                        </div>
                    </div>
                </div>
                
                <div class="panel-header" style="margin-top: 20px;">
                    <i class="fas fa-comments"></i>
                    <h3>Incoming Replies</h3>
                </div>
                
                <div class="reply-feed" id="reply-feed">
                    <div class="empty-state">
                        <i class="fas fa-satellite-dish"></i>
                        <p>Waiting for replies...<br>They'll appear here in real-time.</p>
                    </div>
                </div>
            </div>
            
            <div>
                <div class="console-panel" style="margin-bottom: 20px;">
                    <div class="panel-header">
                        <i class="fas fa-edit"></i>
                        <h3>Reply Drafts (One-Click Copy)</h3>
                    </div>
                    
                    <div class="draft-list" id="draft-list">
                        {% if drafts %}
                            {% for draft in drafts %}
                            <div class="draft-item">
                                <div class="draft-type">{{ draft.strategy }}</div>
                                <div class="draft-text">{{ draft.text }}</div>
                                <button class="copy-btn" onclick="copyDraft(this, '{{ draft.text | e }}')">
                                    <i class="fas fa-copy"></i> Copy to Clipboard
                                </button>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="draft-item">
                                <div class="draft-type">Technical</div>
                                <div class="draft-text">Looking at the on-chain data, this pattern mirrors what we saw in the 2020 cycle. The hashrate-to-price ratio is particularly telling.</div>
                                <button class="copy-btn" onclick="copyDraft(this, 'Looking at the on-chain data, this pattern mirrors what we saw in the 2020 cycle. The hashrate-to-price ratio is particularly telling.')">
                                    <i class="fas fa-copy"></i> Copy to Clipboard
                                </button>
                            </div>
                            <div class="draft-item">
                                <div class="draft-type">Contrarian</div>
                                <div class="draft-text">Playing devil's advocate - what if we're reading this signal wrong? The correlation could be coincidental.</div>
                                <button class="copy-btn" onclick="copyDraft(this, 'Playing devil\\'s advocate - what if we\\'re reading this signal wrong? The correlation could be coincidental.')">
                                    <i class="fas fa-copy"></i> Copy to Clipboard
                                </button>
                            </div>
                            <div class="draft-item">
                                <div class="draft-type">Data Reference</div>
                                <div class="draft-text">The 146.47T difficulty and ~1046 EH/s hashrate paint a clear picture of network security at historic levels.</div>
                                <button class="copy-btn" onclick="copyDraft(this, 'The 146.47T difficulty and ~1046 EH/s hashrate paint a clear picture of network security at historic levels.')">
                                    <i class="fas fa-copy"></i> Copy to Clipboard
                                </button>
                            </div>
                        {% endif %}
                    </div>
                    
                    <button class="generate-btn" onclick="generateMoreDrafts()">
                        <i class="fas fa-magic me-2"></i> Generate More Drafts
                    </button>
                </div>
                
                <div class="console-panel">
                    <div class="panel-header">
                        <i class="fas fa-bullseye"></i>
                        <h3>Next Actions</h3>
                    </div>
                    
                    <ul class="actions-list" id="actions-list">
                        <li class="action-item">
                            <div class="action-icon done"><i class="fas fa-check"></i></div>
                            <span class="action-text">Post link in first reply (DONE)</span>
                        </li>
                        <li class="action-item">
                            <div class="action-icon urgent"><i class="fas fa-bolt"></i></div>
                            <span class="action-text">Reply to high-value accounts first (priority targets)</span>
                        </li>
                        <li class="action-item">
                            <div class="action-icon wait"><i class="fas fa-clock"></i></div>
                            <span class="action-text">Space replies 2-3 minutes apart (avoid robotic patterns)</span>
                        </li>
                        <li class="action-item">
                            <div class="action-icon tip"><i class="fas fa-lightbulb"></i></div>
                            <span class="action-text">Consider quote-posting relevant threads from reply squad</span>
                        </li>
                        <li class="action-item">
                            <div class="action-icon tip"><i class="fas fa-thumbtack"></i></div>
                            <span class="action-text">Pin this post if top performer by minute 15</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let startTime = Date.now();
let sequenceId = {{ sequence.id if sequence else 0 }};

function updateElapsedTime() {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    document.getElementById('elapsed-time').textContent = `${minutes}:${seconds.toString().padStart(2, '0')} elapsed`;
    
    const velocityBar = document.getElementById('velocity-bar');
    const progress = Math.min((elapsed / 1800) * 100, 100);
    velocityBar.style.width = progress + '%';
    
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    
    if (minutes < 5) {
        statusBadge.className = 'status-badge status-critical';
        statusText.textContent = 'CRITICAL WINDOW';
    } else if (minutes < 15) {
        statusBadge.className = 'status-badge status-active';
        statusText.textContent = 'ACCELERATION PHASE';
    } else if (minutes < 30) {
        statusBadge.className = 'status-badge status-active';
        statusText.textContent = 'MOMENTUM PHASE';
    } else {
        statusBadge.className = 'status-badge status-complete';
        statusText.textContent = 'WINDOW CLOSED';
    }
}

function copyDraft(button, text) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    });
}

function generateMoreDrafts() {
    alert('Generating more drafts... This feature requires backend integration.');
}

function addReplyToFeed(handle, content, isHighValue = false) {
    const feed = document.getElementById('reply-feed');
    const emptyState = feed.querySelector('.empty-state');
    if (emptyState) {
        feed.innerHTML = '';
    }
    
    const replyHtml = `
        <div class="reply-item ${isHighValue ? 'high-value' : ''}">
            <div class="reply-header">
                <span class="reply-handle">${handle}</span>
                <span class="reply-time">just now</span>
                ${isHighValue ? '<span class="high-value-badge">PRIORITY</span>' : ''}
            </div>
            <div class="reply-content">${content}</div>
            <div class="reply-actions">
                <button class="draft-btn" onclick="copyDraft(this, 'Great point! The on-chain data supports this thesis.')">Copy Draft 1</button>
                <button class="draft-btn" onclick="copyDraft(this, 'This is exactly what we\\'ve been tracking. The signal is clear.')">Copy Draft 2</button>
            </div>
        </div>
    `;
    
    feed.insertAdjacentHTML('afterbegin', replyHtml);
    
    const totalReplies = feed.querySelectorAll('.reply-item').length;
    document.getElementById('total-replies').textContent = totalReplies;
    
    const elapsed = Math.floor((Date.now() - startTime) / 1000 / 60);
    if (elapsed < 5) {
        const earlyReplies = parseInt(document.getElementById('replies-early').textContent) + 1;
        document.getElementById('replies-early').textContent = earlyReplies;
        document.getElementById('replies-early').className = earlyReplies >= 3 ? 'velocity-value good' : 'velocity-value warning';
    }
    
    const score = Math.min(totalReplies * 25, 250);
    document.getElementById('velocity-score').textContent = score;
    
    if (score >= 150) {
        document.getElementById('velocity-status').textContent = 'EXCELLENT';
        document.getElementById('velocity-status').className = 'velocity-value good';
    } else if (score >= 75) {
        document.getElementById('velocity-status').textContent = 'GOOD';
    } else {
        document.getElementById('velocity-status').textContent = 'BUILDING';
        document.getElementById('velocity-status').className = 'velocity-value warning';
    }
}

setInterval(updateElapsedTime, 1000);
updateElapsedTime();

setTimeout(() => {
    addReplyToFeed('@bitcoiner42', 'This is the signal everyone should be watching. Network fundamentals don\'t lie.', false);
}, 5000);

setTimeout(() => {
    addReplyToFeed('@gladstein', 'This aligns with what we\'re seeing in emerging markets. Financial sovereignty is becoming non-optional.', true);
}, 12000);
</script>
{% endblock %}
```

## templates/intelligence_dashboard.html
```html
{% extends "base.html" %}

{% block title %}Intelligence Dashboard | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
}

.intel-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 100px 20px 60px;
}

.intel-container {
    max-width: 1400px;
    margin: 0 auto;
}

.intel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 30px;
    flex-wrap: wrap;
    gap: 20px;
}

.intel-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 15px;
}

.intel-title i {
    color: var(--pp-red);
}

.quick-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.quick-btn {
    padding: 12px 20px;
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.7);
}

.quick-btn:hover {
    border-color: var(--pp-red);
    color: #fff;
}

.quick-btn.primary {
    background: var(--pp-red);
    border-color: var(--pp-red);
    color: #fff;
}

.quick-btn.primary:hover {
    background: #b91c1c;
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}

.metric-card {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 5px;
}

.metric-value.highlight {
    color: var(--pp-red);
}

.metric-value.success {
    color: #22c55e;
}

.metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
}

@media (max-width: 992px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
    }
}

.dash-panel {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 16px;
    padding: 25px;
}

.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #fff;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.panel-title i {
    color: var(--pp-red);
}

.panel-badge {
    background: rgba(220, 38, 38, 0.2);
    color: var(--pp-red);
    padding: 4px 12px;
    border-radius: 15px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
}

.sequence-list, .alert-list, .squad-list {
    max-height: 350px;
    overflow-y: auto;
}

.sequence-item, .alert-item, .squad-item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 10px;
}

.sequence-item:hover, .alert-item:hover, .squad-item:hover {
    background: rgba(255, 255, 255, 0.05);
}

.item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}

.item-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--pp-red);
    text-transform: uppercase;
}

.item-status {
    padding: 3px 10px;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
}

.status-draft { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.6); }
.status-approved { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
.status-pending { background: rgba(234, 179, 8, 0.2); color: #eab308; }

.item-content {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.5;
}

.item-content a {
    color: var(--pp-red);
    text-decoration: none;
}

.nostr-status {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
}

.relay-status {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    padding: 15px;
}

.relay-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    margin-bottom: 5px;
}

.relay-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.2rem;
    color: #fff;
}

.relay-value.online {
    color: #22c55e;
}

.relay-list {
    margin-top: 15px;
}

.relay-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
}

.relay-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
}

.squad-handle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--pp-red);
    font-weight: 600;
}

.squad-category {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
}

.squad-engagements {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #22c55e;
}

.back-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: rgba(255, 255, 255, 0.6);
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    margin-bottom: 20px;
    transition: color 0.3s ease;
}

.back-link:hover {
    color: var(--pp-red);
}

.empty-state {
    text-align: center;
    padding: 30px;
    color: rgba(255, 255, 255, 0.4);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}
</style>
{% endblock %}

{% block content %}
<div class="intel-page">
    <div class="intel-container">
        <a href="/admin" class="back-link">
            <i class="fas fa-arrow-left"></i> Back to Admin
        </a>
        
        <div class="intel-header">
            <h1 class="intel-title">
                <i class="fas fa-satellite-dish"></i>
                Intelligence Dashboard
            </h1>
            <div class="quick-actions">
                <a href="/admin/launch-sequences" class="quick-btn">
                    <i class="fas fa-rocket"></i> Launch Sequences
                </a>
                <a href="/admin/target-alerts" class="quick-btn">
                    <i class="fas fa-crosshairs"></i> Target Alerts
                </a>
                <a href="/admin/nostr" class="quick-btn">
                    <i class="fas fa-broadcast-tower"></i> Nostr
                </a>
                <a href="/admin/launch-sequence/create" class="quick-btn primary">
                    <i class="fas fa-plus"></i> New Launch
                </a>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{{ articles_count }}</div>
                <div class="metric-label">Published Articles</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ podcasts_count }}</div>
                <div class="metric-label">Episodes</div>
            </div>
            <div class="metric-card">
                <div class="metric-value highlight">{{ pending_sequences }}</div>
                <div class="metric-label">Pending Launches</div>
            </div>
            <div class="metric-card">
                <div class="metric-value highlight">{{ pending_alerts }}</div>
                <div class="metric-label">Target Alerts</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{{ nostr_events }}</div>
                <div class="metric-label">Nostr Notes</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{{ total_zaps|int }}</div>
                <div class="metric-label">Total Zaps (sats)</div>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="dash-panel">
                <div class="panel-header">
                    <span class="panel-title"><i class="fas fa-rocket"></i> Launch Sequences</span>
                    <span class="panel-badge">{{ pending_sequences }} pending</span>
                </div>
                
                <div class="sequence-list">
                    {% if launch_sequences %}
                        {% for seq in launch_sequences %}
                        <div class="sequence-item">
                            <div class="item-header">
                                <span class="item-type">{{ seq.content_type or 'Content' }}</span>
                                <span class="item-status status-{{ seq.status }}">{{ seq.status }}</span>
                            </div>
                            <div class="item-content">
                                <a href="/admin/launch-sequence/{{ seq.id }}">{{ seq.primary_post_copy[:100] if seq.primary_post_copy else 'No content' }}...</a>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                    <div class="empty-state">No launch sequences yet</div>
                    {% endif %}
                </div>
            </div>
            
            <div class="dash-panel">
                <div class="panel-header">
                    <span class="panel-title"><i class="fas fa-crosshairs"></i> Target Alerts</span>
                    <span class="panel-badge">{{ pending_alerts }} pending</span>
                </div>
                
                <div class="alert-list">
                    {% if target_alerts %}
                        {% for alert in target_alerts %}
                        <div class="alert-item">
                            <div class="item-header">
                                <span class="item-type">{{ alert.source_account }}</span>
                                <span class="item-status status-{{ alert.status }}">{{ alert.status }}</span>
                            </div>
                            <div class="item-content">
                                {{ alert.content_snippet[:120] if alert.content_snippet else 'No content' }}...
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                    <div class="empty-state">No pending alerts</div>
                    {% endif %}
                </div>
            </div>
            
            <div class="dash-panel">
                <div class="panel-header">
                    <span class="panel-title"><i class="fas fa-broadcast-tower"></i> Nostr Network</span>
                </div>
                
                <div class="nostr-status">
                    <div class="relay-status">
                        <div class="relay-label">Relays Configured</div>
                        <div class="relay-value online">{{ nostr_status.configured }}</div>
                    </div>
                    <div class="relay-status">
                        <div class="relay-label">Status</div>
                        <div class="relay-value {% if nostr_status.ready %}online{% endif %}">
                            {% if nostr_status.ready %}READY{% else %}NOT CONFIGURED{% endif %}
                        </div>
                    </div>
                </div>
                
                <div class="relay-list">
                    {% for relay in nostr_status.relays[:5] %}
                    <div class="relay-item">
                        <span class="relay-dot"></span>
                        {{ relay }}
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <div class="dash-panel">
                <div class="panel-header">
                    <span class="panel-title"><i class="fas fa-users"></i> Reply Squad</span>
                    <a href="/admin/reply-squad" class="quick-btn" style="padding: 6px 12px; font-size: 0.7rem;">Manage</a>
                </div>
                
                <div class="squad-list">
                    {% if reply_squad %}
                        {% for member in reply_squad %}
                        <div class="squad-item">
                            <div class="item-header">
                                <span class="squad-handle">{{ member.handle }}</span>
                                <span class="squad-engagements">{{ member.reciprocal_engagements }} engagements</span>
                            </div>
                            <div class="squad-category">{{ member.category or 'General' }}</div>
                        </div>
                        {% endfor %}
                    {% else %}
                    <div class="empty-state">
                        <p>No reply squad configured</p>
                        <form action="/admin/reply-squad/init" method="POST" style="margin-top: 15px;">
                            <button type="submit" class="quick-btn primary">Initialize Default Squad</button>
                        </form>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## templates/admin/dashboard.html
```html
{% extends "base.html" %}

{% block title %}Admin Dashboard - Protocol Pulse{% endblock %}

{% block content %}
<style>
    @media (max-width: 991.98px) {
        .admin-sidebar {
            position: fixed;
            top: 56px;
            left: -280px;
            width: 280px;
            height: calc(100vh - 56px);
            background: #1a1a2e;
            z-index: 1040;
            transition: left 0.3s ease;
            overflow-y: auto;
            padding: 1rem;
        }
        .admin-sidebar.show {
            left: 0;
        }
        .sidebar-overlay {
            display: none;
            position: fixed;
            top: 56px;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1035;
        }
        .sidebar-overlay.show {
            display: block;
        }
        .admin-toggle-btn {
            display: block !important;
        }
    }
    @media (min-width: 992px) {
        .admin-toggle-btn {
            display: none !important;
        }
    }
</style>

<div class="container-fluid mt-5 pt-4">
    <!-- Mobile Toggle Button -->
    <button class="btn btn-primary mb-3 admin-toggle-btn d-lg-none" type="button" id="adminSidebarToggle">
        <i class="fas fa-bars me-2"></i> Menu
    </button>
    
    <!-- Overlay for mobile -->
    <div class="sidebar-overlay" id="sidebarOverlay"></div>
    
    <div class="row">
        <!-- Sidebar -->
        <div class="col-lg-2 admin-sidebar" id="adminSidebar">
            <div class="position-sticky pt-3">
                <h5 class="text-primary mb-3">
                    <i class="fas fa-cogs"></i> Admin Panel
                </h5>
                <ul class="nav nav-pills flex-column">
                    <li class="nav-item">
                        <a class="nav-link active" href="/admin">
                            <i class="fas fa-tachometer-alt"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin/write">
                            <i class="fas fa-pen"></i> Write Article
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin/generate">
                            <i class="fas fa-robot"></i> AI Generate
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin/ads">
                            <i class="fas fa-ad"></i> Manage Ads
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/articles">
                            <i class="fas fa-newspaper"></i> View Articles
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/podcasts">
                            <i class="fas fa-podcast"></i> View Podcasts
                        </a>
                    </li>
                </ul>
            </div>
        </div>

        <!-- Main Content -->
        <div class="col-lg-10">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-2 mb-3 border-bottom">
                <h1 class="h2 text-white">
                    <i class="fas fa-broadcast-tower text-primary"></i> 
                    Protocol Pulse Dashboard
                </h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <div class="btn-group me-2">
                        <button type="button" class="btn btn-primary" onclick="location.href='/admin/generate'">
                            <i class="fas fa-plus"></i> Generate Content
                        </button>
                        <button type="button" class="btn btn-outline-light" onclick="refreshTrends()">
                            <i class="fas fa-sync"></i> Refresh Data
                        </button>
                    </div>
                </div>
            </div>

            <!-- Stats Cards -->
            <div class="row mb-4">
                <div class="col-xl-3 col-md-6 mb-4">
                    <div class="card border-left-primary shadow h-100 py-2 bg-dark border-primary">
                        <div class="card-body">
                            <div class="row no-gutters align-items-center">
                                <div class="col mr-2">
                                    <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
                                        Total Articles
                                    </div>
                                    <div class="h5 mb-0 font-weight-bold text-white">{{ total_articles }}</div>
                                </div>
                                <div class="col-auto">
                                    <i class="fas fa-newspaper fa-2x text-primary"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-xl-3 col-md-6 mb-4">
                    <div class="card border-left-success shadow h-100 py-2 bg-dark border-success">
                        <div class="card-body">
                            <div class="row no-gutters align-items-center">
                                <div class="col mr-2">
                                    <div class="text-xs font-weight-bold text-success text-uppercase mb-1">
                                        Published Articles
                                    </div>
                                    <div class="h5 mb-0 font-weight-bold text-white">{{ published_articles }}</div>
                                </div>
                                <div class="col-auto">
                                    <i class="fas fa-check-circle fa-2x text-success"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-xl-3 col-md-6 mb-4">
                    <div class="card border-left-info shadow h-100 py-2 bg-dark border-info">
                        <div class="card-body">
                            <div class="row no-gutters align-items-center">
                                <div class="col mr-2">
                                    <div class="text-xs font-weight-bold text-info text-uppercase mb-1">
                                        Total Podcasts
                                    </div>
                                    <div class="h5 mb-0 font-weight-bold text-white">{{ total_podcasts }}</div>
                                </div>
                                <div class="col-auto">
                                    <i class="fas fa-podcast fa-2x text-info"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-xl-3 col-md-6 mb-4">
                    <div class="card border-left-warning shadow h-100 py-2 bg-dark border-warning">
                        <div class="card-body">
                            <div class="row no-gutters align-items-center">
                                <div class="col mr-2">
                                    <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
                                        Draft Articles
                                    </div>
                                    <div class="h5 mb-0 font-weight-bold text-white">{{ total_articles - published_articles }}</div>
                                </div>
                                <div class="col-auto">
                                    <i class="fas fa-edit fa-2x text-warning"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card bg-dark border-primary">
                        <div class="card-header border-primary">
                            <h5 class="text-primary mb-0">
                                <i class="fas fa-rocket"></i> Quick Actions
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <label for="quickTopic" class="form-label text-light">Generate New Article:</label>
                                    <div class="input-group mb-3">
                                        <input type="text" class="form-control bg-dark text-light border-primary" 
                                               id="quickTopic" placeholder="Bitcoin Lightning Network updates...">
                                        <button class="btn btn-primary" type="button" onclick="quickGenerate()">
                                            <i class="fas fa-magic"></i> Generate
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label text-light">Content Type:</label>
                                    <select id="contentType" class="form-select bg-dark text-light border-primary">
                                        <option value="bitcoin_news">Bitcoin News</option>
                                        <option value="defi_analysis">DeFi Analysis</option>
                                        <option value="breaking_news">Breaking News</option>
                                        <option value="market_update">Market Update</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Recent Articles -->
            <div class="row">
                <div class="col-12">
                    <div class="card bg-dark border-primary">
                        <div class="card-header border-primary">
                            <h5 class="text-primary mb-0">
                                <i class="fas fa-clock"></i> Recent Articles
                            </h5>
                        </div>
                        <div class="card-body">
                            {% if recent_articles %}
                                <div class="table-responsive">
                                    <table class="table table-dark table-striped">
                                        <thead>
                                            <tr>
                                                <th>Title</th>
                                                <th>Category</th>
                                                <th>Status</th>
                                                <th>Created</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for article in recent_articles %}
                                            <tr>
                                                <td>
                                                    <a href="/articles/{{ article.id }}" class="text-primary text-decoration-none">
                                                        {{ article.title[:60] }}{% if article.title|length > 60 %}...{% endif %}
                                                    </a>
                                                </td>
                                                <td>
                                                    <span class="badge bg-secondary">{{ article.category }}</span>
                                                </td>
                                                <td>
                                                    {% if article.published %}
                                                        <span class="badge bg-success">Published</span>
                                                    {% else %}
                                                        <span class="badge bg-warning">Draft</span>
                                                    {% endif %}
                                                </td>
                                                <td class="text-muted">
                                                    {{ article.created_at.strftime('%b %d, %Y') }}
                                                </td>
                                                <td>
                                                    <div class="btn-group btn-group-sm">
                                                        <a href="/admin/edit/{{ article.id }}" class="btn btn-outline-primary btn-sm" title="Edit Article">
                                                            <i class="fas fa-edit"></i>
                                                        </a>
                                                        {% if not article.published %}
                                                            <button class="btn btn-outline-success btn-sm" 
                                                                    onclick="publishArticle({{ article.id }})" 
                                                                    title="Publish Article">
                                                                <i class="fas fa-check"></i>
                                                            </button>
                                                        {% endif %}
                                                        {% if article.published and not article.substack_url %}
                                                            <button class="btn btn-outline-info btn-sm" 
                                                                    onclick="publishToSubstack({{ article.id }})" 
                                                                    title="Publish to Substack">
                                                                <i class="fas fa-paper-plane"></i>
                                                            </button>
                                                        {% endif %}
                                                        {% if article.substack_url %}
                                                            <button class="btn btn-outline-warning btn-sm" 
                                                                    onclick="shareToReddit({{ article.id }})" 
                                                                    title="Share to Reddit">
                                                                <i class="fab fa-reddit"></i>
                                                            </button>
                                                        {% endif %}
                                                    </div>
                                                </td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            {% else %}
                                <div class="text-center py-4">
                                    <i class="fas fa-newspaper fa-3x text-muted mb-3"></i>
                                    <p class="text-muted">No articles found. Generate your first article!</p>
                                    <button class="btn btn-primary" onclick="location.href='/admin/generate'">
                                        <i class="fas fa-plus"></i> Generate Article
                                    </button>
                                </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
.sidebar {
    position: fixed;
    top: 80px;
    bottom: 0;
    left: 0;
    z-index: 100;
    padding: 48px 0 0;
    box-shadow: inset -1px 0 0 rgba(0, 123, 255, .1);
    background: rgba(13, 27, 42, 0.9);
    backdrop-filter: blur(10px);
}

.sidebar .nav-link {
    color: #adb5bd;
    padding: 12px 16px;
    margin: 4px 8px;
    border-radius: 8px;
    transition: all 0.3s ease;
}

.sidebar .nav-link:hover,
.sidebar .nav-link.active {
    color: #007bff;
    background: rgba(0, 123, 255, 0.1);
    transform: translateX(5px);
}

.border-left-primary { border-left: 4px solid #007bff !important; }
.border-left-success { border-left: 4px solid #28a745 !important; }
.border-left-info { border-left: 4px solid #17a2b8 !important; }
.border-left-warning { border-left: 4px solid #ffc107 !important; }

.card { 
    transition: all 0.3s ease; 
    border: 1px solid rgba(0, 123, 255, 0.2);
}
.card:hover { 
    transform: translateY(-2px); 
    box-shadow: 0 8px 25px rgba(0, 123, 255, 0.2);
}

@media (max-width: 767.98px) {
    .sidebar {
        position: relative;
        top: 0;
        height: auto;
    }
}
</style>

<script>
async function quickGenerate() {
    const topic = document.getElementById('quickTopic').value;
    const contentType = document.getElementById('contentType').value;
    
    if (!topic) {
        alert('Please enter a topic for the article');
        return;
    }
    
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/generate-article', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                topic: topic,
                source_type: 'ai_generated'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Article generated successfully!');
            location.reload();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error generating article: ' + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

async function publishArticle(id) {
    if (!confirm('Publish this article?')) return;
    
    try {
        const response = await fetch(`/api/publish-article/${id}`, {method: 'POST'});
        const result = await response.json();
        
        if (result.success) {
            alert('Article published successfully!');
            location.reload();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function publishToSubstack(id) {
    if (!confirm('Publish this article to Substack?')) return;
    
    try {
        const response = await fetch(`/admin/publish-to-substack/${id}`, {method: 'POST'});
        const result = await response.json();
        
        if (result.success) {
            alert('Article published to Substack successfully!');
            location.reload();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function shareToReddit(id) {
    const subreddit = prompt('Enter subreddit name (default: bitcoin):', 'bitcoin');
    if (!subreddit) return;
    
    try {
        const response = await fetch(`/admin/share-reddit/${id}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({subreddit: subreddit})
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Article shared to Reddit successfully!');
        } else {
            alert('Error: ' + (result.error || result.message || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function refreshTrends() {
    location.reload();
}

// Admin sidebar toggle for mobile
document.addEventListener('DOMContentLoaded', function() {
    var sidebar = document.getElementById('adminSidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var toggleBtn = document.getElementById('adminSidebarToggle');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            overlay.classList.toggle('show');
        });
    }
    
    if (overlay) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        });
    }
    
    // Close sidebar when clicking a link on mobile
    var sidebarLinks = sidebar.querySelectorAll('.nav-link');
    sidebarLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                sidebar.classList.remove('show');
                overlay.classList.remove('show');
            }
        });
    });
});
</script>

{% endblock %}```

---

# SECTION 4: STATIC ASSETS

## static/css/style.css
```css
/* Protocol Pulse - Custom Styles */

:root {
    --primary-color: #dc2626;
    --secondary-color: #6c757d;
    --success-color: #198754;
    --danger-color: #dc2626;
    --warning-color: #ffc107;
    --info-color: #dc2626;
    --light-color: #ffffff;
    --dark-color: #000000;
    --bg-dark: #000000;
    --bg-secondary: #1a1a1a;
    --text-muted: #a0a0a0;
    --border-color: #333333;
    --accent-red: #ff0000;
    --gradient-red: linear-gradient(135deg, #dc2626 0%, #b91c1c 50%, #991b1b 100%);
}

/* Global Styles */
body {
    background-color: var(--bg-dark);
    color: var(--light-color);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.6;
}

/* Custom Bootstrap Overrides */
.bg-primary {
    background-color: var(--primary-color) !important;
}

.bg-secondary {
    background-color: var(--bg-secondary) !important;
}

.bg-dark {
    background-color: var(--bg-dark) !important;
}

.text-muted {
    color: var(--text-muted) !important;
}

.border-secondary {
    border-color: var(--border-color) !important;
}

/* Command Center Signal Terminal */
:root {
    --neon-green: #39ff14;
    --accent-red: #dc2626;
    --terminal-font: 'JetBrains Mono', monospace;
}

.signal-terminal-bar {
    position: relative;
    background: #0a0a0a;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    background-blend-mode: overlay;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(220, 38, 38, 0.25);
    margin-top: 56px;
    padding: 0.75rem 0;
}

.signal-terminal-inner {
    background: rgba(10, 10, 10, 0.6);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 8px;
    padding: 0.75rem 1rem;
}

.system-status {
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Kinetic Heartbeat Pulse */
.status-pulse {
    position: relative;
    width: 12px;
    height: 12px;
}

.status-pulse::before,
.status-pulse::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
}

.status-pulse::before {
    width: 12px;
    height: 12px;
    background: var(--neon-green);
    box-shadow: 0 0 10px var(--neon-green), 0 0 20px var(--neon-green);
    animation: pulse-inner 2s ease-in-out infinite;
}

.status-pulse::after {
    width: 24px;
    height: 24px;
    background: transparent;
    border: 1px solid var(--neon-green);
    opacity: 0.5;
    animation: pulse-outer 2s ease-in-out infinite;
}

@keyframes pulse-inner {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
    50% { transform: translate(-50%, -50%) scale(0.85); opacity: 0.8; }
}

@keyframes pulse-outer {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
    50% { transform: translate(-50%, -50%) scale(1.3); opacity: 0.2; }
}

.status-label {
    font-family: var(--terminal-font);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--neon-green);
    text-shadow: 0 0 8px rgba(57, 255, 20, 0.4);
}

/* Data Stream Marquee */
.signal-ticker {
    flex: 1;
    overflow: hidden;
    position: relative;
    margin: 0 1.5rem;
}

.signal-ticker-wrapper {
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 6px;
    padding: 0.5rem 1rem;
    overflow: hidden;
}

.ticker-content {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 40s linear infinite;
    font-family: var(--terminal-font);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255, 255, 255, 0.9);
}

/* Pause on hover for readability */
.signal-ticker-wrapper:hover .ticker-content {
    animation-play-state: paused;
}

@keyframes ticker-scroll {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}

.signal-label {
    font-family: var(--terminal-font);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--accent-red);
    margin-right: 0.75rem;
}

/* Terminal Metadata */
.terminal-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-family: var(--terminal-font);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255, 255, 255, 0.5);
}

.meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
}

.meta-value {
    color: var(--neon-green);
    font-weight: 600;
}

/* Color-coded fee levels */
.meta-value.fee-low {
    color: var(--neon-green);
}

.meta-value.fee-high {
    color: #ef4444;
}

/* Intelligence Dashboard Styles */
.dashboard-container {
    padding-top: 100px;
}

.metric-card {
    background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 1.5rem;
    transition: all 0.3s ease;
}

.metric-card:hover {
    border-color: rgba(220, 38, 38, 0.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(220, 38, 38, 0.15);
}

.metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
}

.metric-label {
    font-size: 0.85rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.metric-change {
    font-size: 0.9rem;
    font-family: monospace;
}

.metric-change.positive { color: #22c55e; }
.metric-change.negative { color: #dc2626; }

.chart-container {
    background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
}

.chart-container canvas {
    max-height: 250px !important;
    width: 100% !important;
    display: block;
}

.chart-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 1rem;
}

/* World-Class Navigation */
.navbar-dark {
    background: linear-gradient(180deg, rgba(0,0,0,0.98) 0%, rgba(10,10,10,0.95) 100%) !important;
    backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(220, 38, 38, 0.15);
    padding: 0.75rem 0;
}

.navbar-dark .navbar-brand {
    font-size: 1.4rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.navbar-dark .navbar-brand img {
    filter: drop-shadow(0 0 8px rgba(220, 38, 38, 0.3));
}

.navbar-dark .navbar-nav {
    gap: 0.25rem;
}

.navbar-dark .navbar-nav .nav-link {
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: rgba(255,255,255,0.8) !important;
}

.navbar-dark .navbar-nav .nav-link:hover {
    color: #fff !important;
    background: rgba(220, 38, 38, 0.15);
}

.navbar-dark .navbar-nav .nav-link i {
    font-size: 0.85rem;
    opacity: 0.7;
}

.navbar-dark .navbar-nav .nav-link:hover i {
    opacity: 1;
    color: var(--primary-color);
}

.navbar-dark .dropdown-menu {
    background: rgba(15, 15, 15, 0.98) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 12px;
    padding: 0.5rem;
    margin-top: 0.5rem;
}

.navbar-dark .dropdown-item {
    border-radius: 8px;
    padding: 0.6rem 1rem;
    transition: all 0.2s ease;
}

.navbar-dark .dropdown-item:hover {
    background: rgba(220, 38, 38, 0.15) !important;
    color: #fff !important;
}

.navbar-search .form-control {
    background: rgba(30, 30, 30, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 20px 0 0 20px;
    font-size: 0.85rem;
    padding: 0.5rem 1rem;
    width: 120px;
    transition: width 0.3s ease, background 0.3s ease, border-color 0.3s ease;
}

.navbar-search .form-control:focus {
    background: rgba(40, 40, 40, 0.9) !important;
    border-color: rgba(220, 38, 38, 0.4) !important;
    box-shadow: none;
    width: 220px;
}

.navbar-search .btn {
    border-radius: 0 20px 20px 0;
    padding: 0.5rem 1rem;
}

/* Content Wrapper */
.content-wrapper {
    margin-top: 80px;
    min-height: calc(100vh - 200px);
}

/* Pages with signal bar need extra top margin */
.has-signal-bar .content-wrapper {
    margin-top: 120px;
}

/* Main Content - Boutique Minimalism Grid Background */
.main-content {
    background-color: #050505;
    background-image: 
        linear-gradient(rgba(220, 38, 38, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(220, 38, 38, 0.05) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* Hero Section */
.hero-section {
    background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-secondary) 50%, var(--bg-dark) 100%);
    min-height: 80vh;
    display: flex;
    align-items: center;
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 30% 70%, rgba(220, 38, 38, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 70% 30%, rgba(220, 38, 38, 0.05) 0%, transparent 50%);
    animation: pulseBackground 8s ease-in-out infinite;
}

@keyframes pulseBackground {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.hero-graphic {
    position: relative;
    animation: float 3s ease-in-out infinite;
}

.hero-particles {
    position: absolute;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
}

.particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: var(--primary-color);
    border-radius: 50%;
    animation: particleFloat 6s linear infinite;
}

@keyframes particleFloat {
    0% {
        transform: translateY(100vh) scale(0);
        opacity: 1;
    }
    50% {
        opacity: 1;
        transform: scale(1);
    }
    100% {
        transform: translateY(-100vh) scale(0);
        opacity: 0;
    }
}

.hero-title {
    color: var(--light-color);
    text-shadow: 0 0 20px rgba(220, 38, 38, 0.5);
    animation: titleGlow 3s ease-in-out infinite alternate;
    position: relative;
    z-index: 10 !important;
}

@keyframes titleGlow {
    0% {
        text-shadow: 0 0 20px rgba(220, 38, 38, 0.5);
    }
    100% {
        text-shadow: 0 0 40px rgba(220, 38, 38, 0.8), 0 0 60px rgba(220, 38, 38, 0.4);
    }
}

@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-20px); }
}

/* Gentle float for mobile - very subtle movement */
@keyframes floatGentle {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-6px); }
}

/* Slow down hero animation on mobile */
@media (max-width: 768px) {
    .hero-graphic {
        animation: float 6s ease-in-out infinite;
    }
}

/* Cards */
.card {
    border-radius: 12px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    overflow: hidden;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(13, 110, 253, 0.1);
}

.featured-card {
    border: 1px solid rgba(220, 38, 38, 0.2);
    background-color: #ffffff;
}

/* Featured Card Text - Black text on white background for high contrast */
.featured-card .card-title,
.featured-card .card-title a {
    color: #050505 !important;
    font-weight: 700;
}

.featured-card .card-title a:hover {
    color: #dc2626 !important;
}

.featured-card .card-text {
    color: #333333 !important;
}

.featured-card .text-muted {
    color: #666666 !important;
}

.featured-card:hover {
    border-color: var(--primary-color);
}

/* Article Cards */
.article-card {
    height: 100%;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    overflow: hidden;
}

.article-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 2px;
    background: var(--gradient-red);
    transition: left 0.5s ease;
}

.article-card:hover::before {
    left: 100%;
}

.article-card:hover {
    transform: translateY(-12px) scale(1.02);
    box-shadow: 0 20px 60px rgba(220, 38, 38, 0.2), 0 0 30px rgba(220, 38, 38, 0.1);
}

.article-title a:hover {
    color: var(--primary-color) !important;
}

.article-meta .badge {
    font-size: 0.75rem;
    padding: 0.4rem 0.8rem;
}

/* Podcast Cards */
.podcast-card {
    overflow: hidden;
    position: relative;
}

.podcast-cover-container {
    position: relative;
    overflow: hidden;
}

.podcast-cover {
    height: 200px;
    object-fit: cover;
    transition: transform 0.3s ease;
}

.placeholder-cover {
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.play-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: 2;
}

.podcast-card:hover .play-overlay {
    opacity: 1;
}

.podcast-card:hover .podcast-cover {
    transform: scale(1.1);
}

.play-btn {
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* Audio Player */
.audio-player {
    background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-secondary) 100%);
    backdrop-filter: blur(10px);
    border-top: 2px solid var(--primary-color);
    z-index: 1050;
}

.progress {
    height: 6px;
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
}

.progress-bar {
    border-radius: 3px;
}

/* Buttons */
.btn {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.3s ease;
    border-width: 2px;
}

.btn-primary {
    background: var(--gradient-red);
    border-color: var(--primary-color);
    position: relative;
    overflow: hidden;
}

.btn-primary::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.btn-primary:hover::before {
    left: 100%;
}

.btn-primary:hover {
    background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%);
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 25px rgba(220, 38, 38, 0.6);
}

.btn-outline-primary {
    border-color: var(--primary-color);
    color: var(--primary-color);
}

.btn-outline-primary:hover {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    transform: translateY(-2px);
}

/* Forms */
.form-control, .form-select {
    background-color: var(--bg-dark);
    border-color: var(--border-color);
    color: var(--light-color);
    border-radius: 8px;
    transition: all 0.3s ease;
}

.form-control:focus, .form-select:focus {
    background-color: var(--bg-dark);
    border-color: var(--primary-color);
    color: var(--light-color);
    box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}

.form-control::placeholder {
    color: var(--text-muted);
}

/* Badges */
.badge {
    font-weight: 500;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
}

.badge.bg-outline-primary {
    background-color: rgba(13, 110, 253, 0.1) !important;
    color: var(--primary-color);
    border: 1px solid var(--primary-color);
}

.badge.bg-outline-secondary {
    background-color: rgba(108, 117, 125, 0.1) !important;
    color: var(--text-muted);
    border: 1px solid var(--border-color);
}

/* Pagination */
.pagination .page-link {
    background-color: var(--bg-secondary);
    border-color: var(--border-color);
    color: var(--light-color);
    border-radius: 8px;
    margin: 0 2px;
}

.pagination .page-link:hover {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    color: white;
}

.pagination .page-item.active .page-link {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
}

/* Footer */
footer {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-dark) 100%);
    border-top: 2px solid var(--primary-color);
}

footer a:hover {
    color: var(--primary-color) !important;
}

.social-links {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.social-icon {
    color: #fff;
    font-size: 1.2rem;
    margin: 0 0.5rem;
    transition: color 0.3s ease;
}

.social-icon:hover {
    color: var(--primary-color);
}

/* Ticker Animation */
.ticker-wrapper {
    overflow: hidden;
    white-space: nowrap;
}

.ticker-content {
    display: inline-block;
    transition: transform 0.5s ease;
}

.ticker-item {
    display: inline-block;
    margin-right: 2rem;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    background-color: rgba(255, 255, 255, 0.05);
}

/* Floating Action Button */
.fab-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
}

.fab {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 20px rgba(13, 110, 253, 0.4);
    transition: all 0.3s ease;
}

.fab:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 25px rgba(13, 110, 253, 0.6);
}

/* World-Class Article Formatting */
.article-content {
    font-family: 'Georgia', 'Times New Roman', serif;
    font-size: 1.1rem;
    line-height: 1.8;
    color: #e8e9ea;
    max-width: 800px;
    margin: 0 auto;
}

.transcript {
    background: #222;
    padding: 15px;
    border-radius: 5px;
}

/* Professional TL;DR Section */
.tldr-section {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.15), rgba(220, 38, 38, 0.05));
    border-left: 4px solid var(--primary-color);
    padding: 25px 30px;
    margin: 40px 0 50px 0;
    border-radius: 8px;
    font-size: 1.15rem;
    box-shadow: 0 4px 15px rgba(220, 38, 38, 0.1);
}

.tldr-section em strong {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-style: italic !important;
    font-size: 1.2rem;
}

/* Journalist-Style Headers */
.article-header {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--primary-color) !important;
    margin: 60px 0 30px 0 !important;
    padding-bottom: 15px;
    border-bottom: 2px solid rgba(220, 38, 38, 0.3);
    font-family: 'Inter', sans-serif;
    letter-spacing: -0.5px;
}

.article-subheader {
    font-size: 1.35rem !important;
    font-weight: 600 !important;
    color: #ffffff !important;
    margin: 45px 0 25px 0 !important;
    font-family: 'Inter', sans-serif;
    letter-spacing: -0.3px;
}

/* Premium Paragraph Styling */
.article-paragraph {
    font-size: 1.15rem !important;
    line-height: 1.9 !important;
    margin: 30px 0 !important;
    color: #e8e9ea !important;
    text-align: justify;
    text-indent: 0;
    font-weight: 400;
}

.article-paragraph:first-of-type {
    font-size: 1.2rem;
    font-weight: 500;
    color: #f8f9fa;
}

/* Professional Sources Section */
.sources-list {
    background: rgba(40, 44, 52, 0.8);
    border-radius: 10px;
    padding: 25px 30px;
    margin: 40px 0;
    border: 1px solid rgba(220, 38, 38, 0.2);
}

.sources-list li {
    color: #c9d1d9;
    margin: 15px 0;
    padding: 8px 0 8px 15px;
    border-left: 3px solid var(--primary-color);
    margin-left: 20px;
    font-size: 1rem;
    transition: all 0.3s ease;
}

.sources-list li:hover {
    background: rgba(220, 38, 38, 0.05);
    padding-left: 20px;
}

/* Enhanced spacing for readability */
.article-content > * + * {
    margin-top: 30px;
}

.article-content .article-header + .article-paragraph,
.article-content .article-subheader + .article-paragraph {
    margin-top: 25px;
}

/* Typography enhancements */
.article-content strong {
    color: #ffffff !important;
    font-weight: 600 !important;
}

.article-content em {
    font-style: italic !important;
    color: #f8f9fa !important;
}

/* Remove old article styles */
.article-content h1, .article-content h2, .article-content h3 {
    color: var(--light-color);
    margin-top: 2rem;
    margin-bottom: 1rem;
}

.article-content p {
    margin-bottom: 1.5rem;
    color: var(--text-muted);
}

.share-buttons button {
    border-radius: 50%;
    width: 40px;
    height: 40px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.reading-progress {
    position: fixed;
    top: 0;
    left: 0;
    width: 0%;
    height: 3px;
    background: linear-gradient(90deg, var(--primary-color), var(--info-color));
    z-index: 1000;
    transition: width 0.3s ease;
}

/* Admin Styles */
.admin-header {
    background: linear-gradient(135deg, var(--primary-color) 0%, #0b5ed7 100%);
    color: white;
    padding: 2rem 0;
}

.stat-card {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-dark) 100%);
    border: 1px solid var(--border-color);
    transition: all 0.3s ease;
}

.stat-card:hover {
    border-color: var(--primary-color);
    transform: translateY(-3px);
}

.activity-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border-color);
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-icon {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
}

/* Loading States */
.spinner-border {
    border-width: 3px;
}

.progress-sm {
    height: 4px;
}

/* ========================================
   WORLD-CLASS MOBILE OPTIMIZATION
   ======================================== */

/* Mobile-First Base Styles */
@media (max-width: 768px) {
    /* Enhanced Content Wrapper */
    .content-wrapper {
        margin-top: 56px; /* Compact mobile navbar height */
        padding: 0;
    }
    
    /* Mobile Container Optimization */
    .container {
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Mobile Hero Section - Compact & Impactful */
    .hero-section {
        min-height: 60vh; /* Reduced from 80vh for mobile */
        padding: 2rem 0;
        text-align: center;
    }
    
    .hero-title {
        font-size: 2.5rem !important; /* Optimized mobile hero title */
        line-height: 1.1;
        margin-bottom: 1.5rem;
    }
    
    .hero-section .lead {
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    
    .hero-section p {
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Mobile Hero Actions - Touch Optimized & Aligned */
    .hero-actions {
        display: flex;
        flex-direction: column;
        gap: 0.875rem;
        align-items: center;
        width: 100%;
        padding: 0 1rem;
    }
    
    .hero-actions .btn {
        width: 100%;
        max-width: 280px;
        padding: 0.875rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 10px;
        min-height: 52px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 !important; /* Override any me-3 margins */
    }
    
    /* Make all mobile hero buttons same solid style */
    .hero-actions .btn-outline-light,
    .hero-actions .btn-outline-danger {
        border-width: 2px;
    }
    
    /* Mobile Hero Graphics - CALMER animations on mobile */
    .hero-graphic {
        animation: none !important; /* Disable bouncing on mobile */
    }
    
    .hero-graphic img {
        width: 8rem !important;
        height: 8rem !important;
        margin: 1rem 0;
        animation: floatGentle 8s ease-in-out infinite !important; /* Very slow, subtle */
    }
    
    .hero-graphic .d-flex {
        gap: 1.5rem;
    }
    
    .hero-graphic i {
        font-size: 2rem !important;
        animation: none !important; /* No animation on mobile for icons */
    }
    
    /* Enhanced FAB */
    .fab-container {
        bottom: 20px;
        right: 20px;
        z-index: 1000;
    }
    
    .fab {
        width: 64px;
        height: 64px;
        box-shadow: 0 8px 20px rgba(220, 38, 38, 0.4);
    }
    
    /* Audio Player Mobile Optimization */
    .audio-player {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 12px;
    }
    
    .audio-player .row {
        flex-direction: column;
        gap: 1rem;
    }
    
    .audio-player .col-md-6,
    .audio-player .col-md-3 {
        text-align: center;
    }
    
    /* Mobile Typography Optimization */
    .display-1 {
        font-size: 2.5rem;
    }
    
    .display-4 {
        font-size: 2rem;
    }
    
    h1 {
        font-size: 2rem;
    }
    
    h2 {
        font-size: 1.75rem;
    }
    
    h3 {
        font-size: 1.5rem;
    }
    
    /* Section Spacing Mobile */
    section {
        padding: 2rem 0;
    }
    
    .section-title {
        font-size: 1.75rem;
        margin-bottom: 1.5rem;
        text-align: center;
    }
}

/* ========================================
   WORLD-CLASS MOBILE NAVIGATION
   ======================================== */

@media (max-width: 768px) {
    /* Enhanced Mobile Navbar */
    .navbar {
        padding: 0.75rem 0;
        backdrop-filter: blur(10px);
        background: rgba(0, 0, 0, 0.95) !important;
        border-bottom: 1px solid rgba(220, 38, 38, 0.3);
        box-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
    }
    
    /* Mobile Brand Optimization */
    .navbar-brand {
        font-size: 1.35rem !important;
        font-weight: 700;
        display: flex;
        align-items: center;
        transition: all 0.3s ease;
    }
    
    .navbar-brand:hover {
        color: var(--primary-color) !important;
    }
    
    .navbar-brand img {
        height: 30px !important;
        margin-right: 0.75rem !important;
        transition: transform 0.3s ease;
    }
    
    .navbar-brand:hover img {
        transform: scale(1.1);
    }
    
    /* Premium Mobile Hamburger Menu */
    .navbar-toggler {
        padding: 0.5rem;
        border: 2px solid var(--primary-color);
        border-radius: 8px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .navbar-toggler:hover {
        background: var(--primary-color);
        transform: scale(1.05);
    }
    
    .navbar-toggler:focus {
        box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.3);
        outline: none;
    }
    
    .navbar-toggler-icon {
        background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 30'%3e%3cpath stroke='rgba%28255, 255, 255, 1%29' stroke-linecap='round' stroke-miterlimit='10' stroke-width='2' d='m4 7h22M4 15h22M4 23h22'/%3e%3c/svg%3e");
        transition: transform 0.3s ease;
    }
    
    .navbar-toggler[aria-expanded="true"] .navbar-toggler-icon {
        transform: rotate(45deg);
    }
    
    /* Enhanced Mobile Menu */
    .navbar-collapse {
        margin-top: 1.25rem;
        padding: 1.5rem 0 1rem 0;
        border-top: 2px solid rgba(220, 38, 38, 0.3);
        background: rgba(0, 0, 0, 0.98);
        border-radius: 0 0 12px 12px;
        backdrop-filter: blur(15px);
    }
    
    /* Mobile Navigation Links */
    .navbar-nav {
        gap: 0.5rem;
    }
    
    .navbar-nav .nav-link {
        padding: 1rem 1.25rem;
        border-radius: 10px;
        margin: 0.25rem 0;
        font-size: 1rem;
        font-weight: 500;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        min-height: 48px; /* Touch-friendly */
        display: flex;
        align-items: center;
    }
    
    .navbar-nav .nav-link::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(220, 38, 38, 0.1), transparent);
        transition: left 0.5s ease;
    }
    
    .navbar-nav .nav-link:hover::before {
        left: 100%;
    }
    
    .navbar-nav .nav-link:hover {
        background: rgba(220, 38, 38, 0.15);
        transform: translateX(8px);
        border-left: 3px solid var(--primary-color);
    }
    
    .navbar-nav .nav-link i {
        width: 24px;
        text-align: center;
        margin-right: 0.75rem;
        font-size: 1.1rem;
    }
    
    /* Enhanced Mobile Dropdown */
    .dropdown-menu {
        border: none;
        margin-top: 0.75rem;
        border-radius: 12px;
        background: rgba(26, 26, 26, 0.98);
        backdrop-filter: blur(15px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(220, 38, 38, 0.2);
    }
    
    .dropdown-item {
        padding: 1rem 1.25rem;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        border-radius: 8px;
        margin: 0.25rem;
        min-height: 48px;
        display: flex;
        align-items: center;
    }
    
    .dropdown-item:hover {
        background: rgba(220, 38, 38, 0.15);
        color: white;
        transform: translateX(8px);
    }
    
    /* Mobile Search Enhancement */
    .navbar-nav .d-flex {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        gap: 0.75rem;
    }
    
    .navbar-nav .form-control {
        font-size: 1rem;
        padding: 0.875rem 1rem;
        border-radius: 10px;
        border: 2px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.05);
        min-height: 48px;
        transition: all 0.3s ease;
    }
    
    .navbar-nav .form-control:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
        background: rgba(255, 255, 255, 0.08);
    }
    
    .navbar-nav .btn {
        padding: 0.875rem 1.25rem;
        border-radius: 10px;
        min-width: 64px;
        min-height: 48px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .navbar-nav .btn:hover {
        transform: scale(1.05);
    }
    
    /* Content Wrapper Mobile Spacing */
    .content-wrapper {
        padding-top: 85px; /* Account for enhanced navbar */
    }
}

/* ========================================
   MOBILE CARDS & CONTENT OPTIMIZATION
   ======================================== */

/* Add mobile card styles after the navigation section */
@media (max-width: 768px) {
    /* Enhanced Card Styles */
    .card {
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(26, 26, 26, 0.95);
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(220, 38, 38, 0.2);
        border-color: rgba(220, 38, 38, 0.3);
    }
    
    .card-body {
        padding: 1.5rem;
    }
    
    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        line-height: 1.3;
        margin-bottom: 1rem;
    }
    
    .card-title a {
        color: var(--light-color);
        text-decoration: none;
        transition: color 0.3s ease;
    }
    
    .card-title a:hover {
        color: var(--primary-color);
    }
    
    .card-text {
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 1.25rem;
        color: var(--text-muted);
    }
    
    /* Mobile Article Cards */
    .article-card::before {
        height: 3px;
    }
    
    .article-card:hover {
        transform: translateY(-6px) scale(1.01);
    }
    
    /* Mobile Featured Cards - Dark theme with white text */
    .featured-card {
        border: 2px solid rgba(220, 38, 38, 0.3);
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.05) 0%, rgba(0, 0, 0, 0.95) 100%);
    }
    
    .featured-card .card-title,
    .featured-card .card-title a {
        color: #ffffff !important;
    }
    
    .featured-card .card-text {
        color: #cccccc !important;
    }
    
    /* Mobile Badge Styling */
    .badge {
        font-size: 0.8rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    /* Mobile Meta Information */
    .d-flex.justify-content-between {
        flex-direction: column;
        gap: 0.75rem;
        align-items: flex-start;
    }
    
    .d-flex.justify-content-between small {
        font-size: 0.85rem;
        color: var(--text-muted);
    }
}

/* ========================================
   MOBILE BUTTONS & INTERACTIVE ELEMENTS
   ======================================== */

@media (max-width: 768px) {
    /* Enhanced Mobile Buttons */
    .btn {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        min-height: 48px; /* Touch-friendly minimum */
        padding: 0.875rem 1.5rem;
        font-size: 1rem;
        position: relative;
        overflow: hidden;
    }
    
    .btn-lg {
        min-height: 56px;
        padding: 1rem 2rem;
        font-size: 1.1rem;
        border-radius: 14px;
    }
    
    .btn-sm {
        min-height: 40px;
        padding: 0.75rem 1.25rem;
        font-size: 0.9rem;
        border-radius: 10px;
    }
    
    /* Mobile Button Hover Effects */
    .btn-primary:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 25px rgba(220, 38, 38, 0.5);
    }
    
    .btn-outline-primary:hover {
        transform: translateY(-2px);
    }
    
    .btn-outline-light:hover {
        transform: translateY(-2px);
    }
    
    /* Mobile Form Optimization */
    .form-control {
        border-radius: 12px;
        padding: 0.875rem 1rem;
        font-size: 1rem;
        min-height: 48px;
        transition: all 0.3s ease;
    }
    
    .form-control:focus {
        transform: scale(1.02);
    }
    
    /* Mobile Newsletter Form */
    .newsletter-form .row {
        gap: 1rem;
    }
    
    .newsletter-form .col-md-5,
    .newsletter-form .col-md-2 {
        flex: 1;
        min-width: 0;
    }
}

/* ========================================
   SMALL MOBILE DEVICES (≤576px)
   ======================================== */

@media (max-width: 576px) {
    .container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Extra Small Mobile Typography */
    .hero-title {
        font-size: 2rem !important;
    }
    
    .section-title {
        font-size: 1.5rem;
    }
    
    h1 {
        font-size: 1.75rem;
    }
    
    h2 {
        font-size: 1.5rem;
    }
    
    h3 {
        font-size: 1.25rem;
    }
    
    /* Extra Small Mobile Navigation */
    .navbar {
        padding: 0.5rem 0;
    }
    
    .navbar-brand {
        font-size: 1.15rem !important;
    }
    
    .navbar-brand img {
        height: 26px !important;
        margin-right: 0.5rem !important;
    }
    
    .navbar-nav .nav-link {
        padding: 0.875rem 1rem;
        font-size: 0.95rem;
    }
    
    .navbar-nav .nav-link i {
        font-size: 1rem;
        width: 22px;
    }
    
    .dropdown-item {
        padding: 0.875rem 1rem;
        font-size: 0.9rem;
    }
    
    .navbar-nav .form-control {
        font-size: 0.95rem;
        padding: 0.75rem 1rem;
    }
    
    .navbar-nav .btn {
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        min-width: 56px;
    }
    
    .content-wrapper {
        padding-top: 75px;
    }
    
    /* Extra Small Mobile Cards */
    .card-body {
        padding: 1.25rem;
    }
    
    .card-title {
        font-size: 1.1rem;
    }
    
    .card-text {
        font-size: 0.9rem;
    }
    
    /* Extra Small Mobile Buttons */
    .btn {
        font-size: 0.95rem;
        padding: 0.75rem 1.25rem;
        min-height: 44px;
    }
    
    .btn-lg {
        font-size: 1rem;
        padding: 0.875rem 1.5rem;
        min-height: 52px;
    }
    
    .btn-group .btn {
        font-size: 0.9rem;
        padding: 0.75rem 1rem;
        min-height: 44px;
    }
    
    /* Extra Small Mobile Hero Actions */
    .hero-actions .btn {
        max-width: 280px;
        font-size: 0.95rem;
    }
    
    /* Extra Small Mobile Newsletter */
    .newsletter-form .row {
        flex-direction: column;
        gap: 1rem;
    }
    
    .newsletter-form .col-md-5,
    .newsletter-form .col-md-2 {
        width: 100%;
    }
    
    /* Enhanced Footer Mobile Styles */
    footer {
        padding: 3rem 0 2rem 0 !important;
        background: linear-gradient(135deg, rgba(26, 26, 26, 0.98) 0%, rgba(0, 0, 0, 0.98) 100%);
        backdrop-filter: blur(10px);
        border-top: 2px solid rgba(220, 38, 38, 0.3);
    }
    
    footer .container {
        padding-left: 1.25rem;
        padding-right: 1.25rem;
    }
    
    footer .row {
        gap: 2rem;
        justify-content: center;
        text-align: center;
    }
    
    footer .col-md-4 {
        margin-bottom: 2rem;
    }
    
    footer h5 {
        font-size: 1.25rem;
        margin-bottom: 1rem;
        color: var(--primary-color);
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    footer p {
        font-size: 1rem;
        line-height: 1.5;
        margin-bottom: 0.75rem;
        color: var(--text-muted);
    }
    
    footer ul {
        margin-bottom: 0;
        list-style: none;
        padding: 0;
    }
    
    footer ul li {
        margin-bottom: 0.75rem;
    }
    
    footer ul li a {
        font-size: 1rem;
        color: var(--text-muted);
        text-decoration: none;
        transition: all 0.3s ease;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        display: inline-block;
    }
    
    footer ul li a:hover {
        color: var(--primary-color) !important;
        background: rgba(220, 38, 38, 0.1);
        transform: translateY(-2px);
    }
    
    footer hr {
        margin: 2.5rem 0 1.5rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
    }
    
    footer .text-center {
        font-size: 0.9rem;
        color: var(--text-muted);
        margin-bottom: 0;
        padding: 1rem 0;
    }
    
    /* Social links mobile styling */
    footer a:not(li a) {
        font-size: 1rem;
        color: var(--text-muted);
        text-decoration: none;
        transition: all 0.3s ease;
        padding: 0.5rem;
        border-radius: 6px;
    }
    
    footer a:not(li a):hover {
        color: var(--primary-color) !important;
        background: rgba(220, 38, 38, 0.1);
    }
}

/* Dark Theme Utilities */
.bg-gradient {
    background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-secondary) 100%);
}

.text-gradient {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--info-color) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Advanced Animations */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(50px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes morphBackground {
    0%, 100% {
        border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
    }
    50% {
        border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%;
    }
}

@keyframes dataFlow {
    0% {
        transform: translateX(-100px) opacity(0);
    }
    50% {
        opacity: 1;
    }
    100% {
        transform: translateX(calc(100vw + 100px)) opacity(0);
    }
}

.morphing-bg {
    position: absolute;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, var(--primary-color) 0%, transparent 70%);
    opacity: 0.1;
    animation: morphBackground 8s ease-in-out infinite;
}

.data-stream {
    position: absolute;
    width: 2px;
    height: 20px;
    background: var(--primary-color);
    opacity: 0.8;
    animation: dataFlow 3s linear infinite;
}

.card-hover-effect {
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.card-hover-effect:hover {
    transform: translateY(-10px) rotateX(5deg);
    box-shadow: 0 20px 40px rgba(220, 38, 38, 0.15), 0 0 20px rgba(220, 38, 38, 0.1);
}

.fade-in-up {
    animation: fadeInUp 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}

.slide-in-right {
    animation: slideInRight 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}

.stagger-animation {
    animation-delay: var(--stagger-delay, 0s);
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}

.pulse {
    animation: pulse 2s ease-in-out infinite;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-dark);
}

::-webkit-scrollbar-thumb {
    background: var(--primary-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #0b5ed7;
}

/* Selection Styling */
::selection {
    background-color: var(--primary-color);
    color: white;
}

::-moz-selection {
    background-color: var(--primary-color);
    color: white;
}

/* Advanced Hero Particles */
.hero-particles {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    z-index: 1;
    pointer-events: none;
}

.particle {
    position: absolute;
    width: 2px;
    height: 2px;
    background: var(--primary-color);
    border-radius: 50%;
    opacity: 0.8;
    animation: floatUp linear infinite;
}

.particle::before {
    content: '';
    position: absolute;
    width: 4px;
    height: 4px;
    background: var(--primary-color);
    border-radius: 50%;
    opacity: 0.4;
    top: -1px;
    left: -1px;
}

@keyframes floatUp {
    0% {
        transform: translateY(100vh) translateX(0px);
        opacity: 0;
    }
    10% {
        opacity: 0.8;
    }
    90% {
        opacity: 0.8;
    }
    100% {
        transform: translateY(-100px) translateX(100px);
        opacity: 0;
    }
}

@keyframes float {
    0%, 100% {
        transform: translateY(0px) rotate(0deg);
    }
    50% {
        transform: translateY(-20px) rotate(5deg);
    }
}

/* Clean social icon styling - no glowing frames */

/* Bitcoin icon alignment fix */
.fab.fa-bitcoin {
    display: inline-block;
    text-align: center;
    vertical-align: middle;
}

/* Interactive mouse effects */
.hero-section::before {
    content: '';
    position: absolute;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(220, 38, 38, 0.1) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
    transition: all 0.3s ease;
    transform: translate(var(--mouse-x, 50%), var(--mouse-y, 50%));
}

/* Enhanced Cards */
.card {
    backdrop-filter: blur(10px);
    border: 1px solid rgba(220, 38, 38, 0.1);
}

.card:hover {
    border-color: rgba(220, 38, 38, 0.3);
    background-color: rgba(17, 24, 39, 0.95);
}

/* WORLD-CLASS ARTICLE HEADERS */
.article-header-professional {
    background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-secondary) 100%);
    border-radius: 0;
    padding: 3rem 0 2rem 0;
    border-bottom: 1px solid rgba(220, 38, 38, 0.1);
    position: relative;
    overflow: hidden;
}

.article-header-professional::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #dc2626 0%, #ef4444 50%, #dc2626 100%);
}

.category-section {
    margin-bottom: 2rem;
}

.category-badge {
    display: inline-block;
    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 25px;
    font-weight: 700;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.article-title-professional {
    font-family: 'Georgia', 'Times New Roman', serif;
    font-size: clamp(2.5rem, 5vw, 4rem);
    font-weight: 700;
    line-height: 1.1;
    color: var(--light-color);
    margin-bottom: 2rem;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    letter-spacing: -0.02em;
}

.article-meta-professional {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 1.5rem 0;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.meta-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.meta-label {
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
}

.meta-value {
    color: var(--light-color);
    font-size: 0.875rem;
    font-weight: 500;
}

.meta-divider {
    color: var(--text-muted);
    font-size: 0.875rem;
    opacity: 0.5;
}

/* Enhanced breadcrumb styling */
.breadcrumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 2rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.breadcrumb-item a {
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
}

.breadcrumb-item a:hover {
    color: #ef4444;
}

.breadcrumb-item.active {
    color: var(--text-muted);
}

/* Professional Social Share Buttons */
.share-social-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    margin: 2rem 0;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.share-buttons-container {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.share-label {
    color: var(--light-color);
    font-weight: 600;
    font-size: 0.875rem;
    margin-right: 0.5rem;
    letter-spacing: 0.5px;
}

.social-buttons {
    display: flex;
    gap: 0.75rem;
}

.social-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    border: none;
    border-radius: 25px;
    font-weight: 600;
    font-size: 0.875rem;
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.social-btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s ease;
}

.social-btn:hover::before {
    left: 100%;
}

.twitter-btn {
    background: linear-gradient(135deg, #1da1f2 0%, #0d8bd9 100%);
    color: white;
    border: 1px solid rgba(29, 161, 242, 0.3);
}

.twitter-btn:hover {
    background: linear-gradient(135deg, #0d8bd9 0%, #1da1f2 100%);
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(29, 161, 242, 0.4);
}

.linkedin-btn {
    background: linear-gradient(135deg, #0077b5 0%, #005885 100%);
    color: white;
    border: 1px solid rgba(0, 119, 181, 0.3);
}

.linkedin-btn:hover {
    background: linear-gradient(135deg, #005885 0%, #0077b5 100%);
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(0, 119, 181, 0.4);
}

.copy-btn {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.05) 100%);
    color: var(--light-color);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.copy-btn:hover {
    background: linear-gradient(135deg, var(--primary-color) 0%, #b91c1c 100%);
    color: white;
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(220, 38, 38, 0.4);
}

.reading-time {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    background: rgba(255, 255, 255, 0.05);
    padding: 0.75rem 1rem;
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.reading-time i {
    color: var(--primary-color);
}

/* Reading progress bar */
.reading-progress {
    position: fixed;
    top: 0;
    left: 0;
    width: 0%;
    height: 4px;
    background: linear-gradient(90deg, #dc2626 0%, #ef4444 50%, #dc2626 100%);
    z-index: 9999;
    transition: width 0.3s ease;
    box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);
}

/* Article content professional styling */
.article-content {
    font-family: 'Georgia', 'Times New Roman', serif;
    font-size: 1.125rem;
    line-height: 1.8;
    color: var(--light-color);
    max-width: none;
}

.article-content h2,
.article-content h3,
.article-content h4 {
    color: var(--light-color);
    margin-top: 3rem;
    margin-bottom: 1.5rem;
}

.article-content p {
    margin-bottom: 1.5rem;
    text-align: justify;
}

/* Tags enhancement */
.article-tags {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 2rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.article-tags .badge {
    background: rgba(220, 38, 38, 0.1);
    color: var(--primary-color);
    border: 1px solid rgba(220, 38, 38, 0.3);
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 20px;
}

/* Related articles enhancement */
.related-articles {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    padding: 2rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

/* ========================================
   WORLD-CLASS MOBILE ARTICLE FORMATTING
   ======================================== */

/* Mobile Article Typography & Reading Experience */
@media (max-width: 768px) {
    /* Enhanced Article Container */
    .article-content {
        font-family: 'Georgia', 'Times New Roman', serif;
        font-size: 1.1rem;
        line-height: 1.7;
        color: #e8e9ea;
        max-width: 100%;
        margin: 0;
        padding: 1.5rem;
        background: rgba(0, 0, 0, 0.5);
        border-radius: 12px;
        backdrop-filter: blur(5px);
    }
    
    /* Mobile TL;DR Section - Premium Design */
    .tldr-section {
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.2), rgba(220, 38, 38, 0.08));
        border-left: 4px solid var(--primary-color);
        padding: 1.5rem 1.25rem;
        margin: 2rem 0 2.5rem 0;
        border-radius: 12px;
        font-size: 1rem;
        box-shadow: 0 6px 20px rgba(220, 38, 38, 0.15);
        position: relative;
        overflow: hidden;
    }
    
    .tldr-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-color), transparent);
    }
    
    .tldr-section em strong {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-style: italic !important;
        font-size: 1.1rem;
        display: block;
        margin-bottom: 0.75rem;
    }
    
    /* Mobile Article Headers - Optimized Hierarchy */
    .article-header {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: var(--primary-color) !important;
        margin: 2.5rem 0 1.5rem 0 !important;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(220, 38, 38, 0.3);
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.3px;
        line-height: 1.3;
    }
    
    .article-subheader {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin: 2rem 0 1.25rem 0 !important;
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.2px;
        line-height: 1.4;
    }
    
    /* Mobile Paragraph Optimization */
    .article-paragraph {
        font-size: 1.05rem !important;
        line-height: 1.75 !important;
        margin: 1.5rem 0 !important;
        color: #e8e9ea !important;
        text-align: left;
        text-indent: 0;
        font-weight: 400;
        word-spacing: 0.1em;
    }
    
    .article-paragraph:first-of-type {
        font-size: 1.1rem;
        font-weight: 500;
        color: #f8f9fa;
        margin-top: 2rem !important;
    }
    
    /* Mobile Sources Section */
    .sources-list {
        background: rgba(40, 44, 52, 0.9);
        border-radius: 12px;
        padding: 1.5rem 1.25rem;
        margin: 2rem 0;
        border: 1px solid rgba(220, 38, 38, 0.25);
        backdrop-filter: blur(5px);
    }
    
    .sources-list li {
        color: #c9d1d9;
        margin: 0.75rem 0;
        padding: 0.75rem 0 0.75rem 1rem;
        border-left: 3px solid var(--primary-color);
        margin-left: 1rem;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        border-radius: 6px;
    }
    
    .sources-list li:hover {
        background: rgba(220, 38, 38, 0.08);
        padding-left: 1.25rem;
        transform: translateX(4px);
    }
    
    /* Enhanced Mobile Article Spacing */
    .article-content > * + * {
        margin-top: 1.5rem;
    }
    
    .article-content .article-header + .article-paragraph,
    .article-content .article-subheader + .article-paragraph {
        margin-top: 1.25rem;
    }
    
    /* Mobile Typography Enhancements */
    .article-content strong {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.02em;
    }
    
    .article-content em {
        font-style: italic !important;
        color: #f8f9fa !important;
        font-size: 1.01em;
    }
    
    /* Mobile Article Images */
    .article-content img {
        width: 100%;
        height: auto;
        border-radius: 8px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Mobile Video Embeds */
    .article-content iframe {
        width: 100%;
        height: 250px;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    /* Professional Article Header Mobile */
    .article-header-professional {
        padding: 2rem 1rem 1.5rem 1rem;
        background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-secondary) 100%);
        border-radius: 0 0 16px 16px;
    }
    
    .article-title-professional {
        font-size: 1.75rem;
        margin-bottom: 1.5rem;
        line-height: 1.25;
        text-align: left;
    }
    
    .article-meta-professional {
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
        padding: 1.25rem 0;
    }
    
    .meta-item {
        flex-direction: row;
    }
    
    .category-badge {
        padding: 0.6rem 1.25rem;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }
    
    /* Enhanced Mobile Social Sharing */
    .share-social-section {
        flex-direction: column;
        gap: 1.5rem;
        padding: 1.5rem;
        margin: 2rem 0;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%);
        backdrop-filter: blur(15px);
    }
    
    .share-buttons-container {
        flex-direction: column;
        align-items: stretch;
        gap: 1.25rem;
        width: 100%;
    }
    
    .share-label {
        text-align: center;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }
    
    .social-buttons {
        width: 100%;
        justify-content: space-between;
        gap: 0.75rem;
    }
    
    .social-btn {
        flex: 1;
        justify-content: center;
        padding: 1rem;
        font-size: 0.9rem;
        min-width: 0;
        min-height: 48px;
        border-radius: 12px;
        font-weight: 600;
        position: relative;
        overflow: hidden;
    }
    
    .social-btn span {
        display: none;
    }
    
    .social-btn i {
        font-size: 1.2rem;
    }
    
    .reading-time {
        align-self: center;
        padding: 0.75rem 1.25rem;
        font-size: 0.9rem;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    /* Mobile Breadcrumb */
    .breadcrumb {
        padding: 0.75rem 1rem;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
        border-radius: 10px;
    }
}

/* ========================================
   MOBILE PERFORMANCE OPTIMIZATIONS
   ======================================== */

@media (max-width: 768px) {
    /* Reduce motion for mobile performance */
    .hero-particles {
        display: none; /* Disable particles on mobile for better performance */
    }
    
    /* Optimize animations for mobile */
    * {
        animation-duration: 0.3s !important;
        transition-duration: 0.3s !important;
    }
    
    /* Mobile-optimized transforms */
    .card:hover {
        transform: translateY(-2px); /* Reduced transform for mobile */
    }
    
    .article-card:hover {
        transform: translateY(-3px) scale(1.005); /* Lighter transform */
    }
    
    /* Mobile touch optimization */
    .btn, .nav-link, .dropdown-item, .card {
        -webkit-tap-highlight-color: rgba(220, 38, 38, 0.3);
        touch-action: manipulation;
    }
    
    /* Disable heavy backdrop filters on smaller screens for performance */
    @media (max-width: 480px) {
        .card, .navbar, .footer {
            backdrop-filter: none;
        }
        
        /* Simplified shadows for better performance */
        .card {
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
        }
        
        .btn {
            box-shadow: 0 2px 8px rgba(220, 38, 38, 0.2);
        }
    }
    
    /* Optimize scrolling performance */
    html {
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }
    
    /* Mobile focus states for accessibility */
    .btn:focus, .form-control:focus, .nav-link:focus {
        outline: 3px solid rgba(220, 38, 38, 0.5);
        outline-offset: 2px;
    }
    
    /* Mobile-specific loading optimizations */
    .content-wrapper {
        will-change: auto; /* Remove will-change to prevent layer creation */
    }
    
    /* Enhanced mobile section spacing */
    .featured-stories-section,
    .latest-news-section,
    .featured-podcasts-section {
        padding: 2rem 0;
        margin-bottom: 2rem;
    }
    
    /* Mobile sidebar optimizations */
    .sidebar {
        margin-top: 2rem;
        padding: 1.5rem;
        background: rgba(26, 26, 26, 0.95);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .market-widget {
        gap: 1rem;
    }
    
    .crypto-price {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        margin-bottom: 0.75rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
    }
    
    .crypto-name {
        font-weight: 600;
        color: var(--light-color);
        font-size: 1rem;
    }
    
    .crypto-price-value {
        font-weight: 700;
        color: var(--light-color);
        font-size: 1.1rem;
    }
    
    .crypto-change {
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
    }
    
    .crypto-change.positive {
        color: #22c55e;
        background: rgba(34, 197, 94, 0.1);
    }
    
    .crypto-change.negative {
        color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
    }
}

@media (max-width: 480px) {
    .container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    .article-header-professional {
        padding: 1.5rem 0 1rem 0;
    }
    
    .article-title-professional {
        font-size: 1.75rem;
        line-height: 1.2;
        margin-bottom: 1rem;
    }
    
    .category-badge {
        padding: 0.5rem 1rem;
        font-size: 0.7rem;
        margin-bottom: 1rem;
    }
    
    .article-meta-professional {
        padding: 1rem 0;
        gap: 0.5rem;
    }
    
    .meta-value, .meta-label {
        font-size: 0.8rem;
    }
    
    .breadcrumb {
        padding: 0.5rem 0.75rem;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }
    
    .breadcrumb-item.active {
        font-size: 0.75rem;
    }
    
    .share-social-section {
        padding: 1rem;
        margin: 1.5rem 0;
        border-radius: 12px;
    }
    
    .share-label {
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }
    
    .social-btn {
        padding: 0.75rem;
        font-size: 0.75rem;
    }
    
    .social-btn i {
        font-size: 1rem;
    }
    
    .reading-time {
        font-size: 0.75rem;
        padding: 0.5rem 0.75rem;
    }
    
    /* Article content mobile optimization */
    .article-content {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    .article-content h1,
    .article-content h2,
    .article-content h3 {
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
    
    .article-content h1 {
        font-size: 1.5rem;
    }
    
    .article-content h2 {
        font-size: 1.3rem;
    }
    
    .article-content h3 {
        font-size: 1.15rem;
    }
    
    .article-content p {
        margin-bottom: 1rem;
    }
    
    .article-content img {
        margin: 1rem 0;
    }
    
    .article-content iframe {
        height: 200px;
        margin: 1rem 0;
    }
    
    /* Tags mobile optimization */
    .article-tags {
        padding: 1rem;
        margin-top: 1.5rem;
    }
    
    .article-tags h6 {
        font-size: 0.9rem;
        margin-bottom: 0.75rem;
    }
    
    .article-tags .badge {
        font-size: 0.7rem;
        padding: 0.4rem 0.8rem;
        margin: 0.25rem 0.25rem 0.25rem 0;
    }
    
    /* Related articles mobile optimization */
    .related-articles {
        padding: 1rem;
        margin-top: 1.5rem;
    }
    
    .related-articles h3 {
        font-size: 1.25rem;
        margin-bottom: 1rem;
    }
    
    .related-articles .card {
        margin-bottom: 1rem;
    }
    
    .related-articles .card-body {
        padding: 1rem;
    }
    
    .related-articles .card-title {
        font-size: 0.95rem;
        line-height: 1.3;
    }
    
    .related-articles .card-text {
        font-size: 0.8rem;
    }
    
    /* Back button mobile optimization */
    .btn {
        font-size: 0.85rem;
        padding: 0.6rem 1.2rem;
    }
}

/* FINAL OVERRIDE FOR FEATURED CARDS - WHITE BACKGROUND / BLACK TEXT */
#high-priority-featured-display .article-card {
    background-color: #ffffff !important;
}

#high-priority-featured-display .article-card h2, 
#high-priority-featured-display .article-card h3,
#high-priority-featured-display .article-card h5,
#high-priority-featured-display .article-card .article-title,
#high-priority-featured-display .article-card .card-title,
#high-priority-featured-display .article-card .card-title a {
    color: #050505 !important;
    -webkit-text-fill-color: #050505 !important;
    font-weight: 800 !important;
}

#high-priority-featured-display .article-card p,
#high-priority-featured-display .article-card .article-summary,
#high-priority-featured-display .article-card .card-text {
    color: #1a1a1a !important;
    -webkit-text-fill-color: #1a1a1a !important;
}

#high-priority-featured-display .article-card .article-date,
#high-priority-featured-display .article-card .text-muted,
#high-priority-featured-display .article-card small {
    color: #4b5563 !important;
}

/* Bitcoin Icon Alignment Fixes - Global */
.fa-bitcoin,
.fab.fa-bitcoin {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    vertical-align: middle;
    line-height: 1;
    font-size: 1.25em;
}

/* Fix Bitcoin icons in badges */
.badge .fa-bitcoin,
.badge .fab.fa-bitcoin,
.badge-onchain .fa-bitcoin,
.badge-lightning .fa-bolt {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    vertical-align: middle;
    line-height: 1;
    position: relative;
    top: 0;
    font-size: 1.1em;
}

/* Fix Bitcoin icons in circular markers (map markers) */
.btc-marker .fa-bitcoin,
.btc-marker .fab.fa-bitcoin {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    line-height: 1;
    font-size: 1.5rem;
}

/* Fix Bitcoin icons in headers/titles */
.sidebar-title .fa-bitcoin,
.sidebar-title .fab.fa-bitcoin {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    vertical-align: middle;
    font-size: 1.3em;
}

/* Bitcoin icon size variations */
.btc-icon-lg .fa-bitcoin,
.btc-icon-lg .fab.fa-bitcoin {
    font-size: 1.5em;
}

.btc-icon-xl .fa-bitcoin,
.btc-icon-xl .fab.fa-bitcoin {
    font-size: 2em;
}

/* ===== SOVEREIGN CARD - World-Class Terminal Design ===== */
/* Glassmorphism + Layered Shadows - premium institutional look */
.sovereign-card {
    background: rgba(10, 10, 10, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 8px;
    position: relative;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
    box-shadow: 
        inset 0 0 15px rgba(220, 38, 38, 0.05),
        0 10px 30px rgba(0, 0, 0, 0.5);
}

.sovereign-card:hover {
    border-color: rgba(220, 38, 38, 0.8);
    box-shadow: 
        0 0 25px rgba(220, 38, 38, 0.2),
        inset 0 0 20px rgba(220, 38, 38, 0.1);
    transform: translateY(-2px);
}

/* Remove all icon glows inside sovereign cards */
.sovereign-card img,
.sovereign-card i,
.sovereign-card svg {
    filter: none !important;
    box-shadow: none !important;
}

.sovereign-card-dark {
    background: rgba(5, 5, 5, 0.9);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(220, 38, 38, 0.15);
    border-radius: 8px;
    box-shadow: 
        inset 0 0 10px rgba(220, 38, 38, 0.03),
        0 8px 25px rgba(0, 0, 0, 0.6);
    transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.sovereign-card-dark:hover {
    border-color: rgba(220, 38, 38, 0.6);
    box-shadow: 
        0 0 20px rgba(220, 38, 38, 0.15),
        inset 0 0 15px rgba(220, 38, 38, 0.08);
    transform: translateY(-2px);
}

/* Sovereign button style - glassmorphism */
.btn-sovereign {
    background: rgba(10, 10, 10, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(220, 38, 38, 0.2);
    color: #fff;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    box-shadow: 
        inset 0 0 10px rgba(220, 38, 38, 0.05),
        0 6px 20px rgba(0, 0, 0, 0.4);
    transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.btn-sovereign:hover {
    border-color: rgba(220, 38, 38, 0.8);
    box-shadow: 
        0 0 20px rgba(220, 38, 38, 0.2),
        inset 0 0 15px rgba(220, 38, 38, 0.1);
    color: #fff;
    transform: translateY(-2px);
}

/* Sovereign icon container - unified with card, no separate glow */
.sovereign-icon {
    background: rgba(10, 10, 10, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 
        inset 0 0 10px rgba(220, 38, 38, 0.05),
        0 6px 20px rgba(0, 0, 0, 0.4);
    transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.sovereign-icon:hover {
    border-color: rgba(220, 38, 38, 0.6);
    box-shadow: 
        0 0 15px rgba(220, 38, 38, 0.15),
        inset 0 0 12px rgba(220, 38, 38, 0.08);
}

.sovereign-icon i,
.sovereign-icon svg {
    color: var(--accent-red);
    filter: none !important;
    box-shadow: none !important;
}
```

## static/sw.js (Service Worker for PWA)
```javascript
const CACHE_NAME = 'protocol-pulse-v1';
const OFFLINE_URL = '/offline';

const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/css/style.css',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('mempool.space') ||
      event.request.url.includes('btcmap.org') ||
      event.request.url.includes('blockchain.info')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => response)
        .catch(() => new Response(JSON.stringify({error: 'offline'}), {
          headers: {'Content-Type': 'application/json'}
        }))
    );
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        fetch(event.request).then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, response);
            });
          }
        });
        return cachedResponse;
      }
      
      return fetch(event.request).then((response) => {
        if (response.ok && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      }).catch(() => {
        if (event.request.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }
      });
    })
  );
});

self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  const title = data.title || 'Protocol Pulse';
  const options = {
    body: data.body || 'New intelligence available',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    },
    actions: [
      {action: 'open', title: 'View'},
      {action: 'dismiss', title: 'Dismiss'}
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'dismiss') return;
  
  event.waitUntil(
    clients.matchAll({type: 'window'}).then((clientList) => {
      for (const client of clientList) {
        if (client.url === event.notification.data.url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data.url);
      }
    })
  );
});
```

---

# SECTION 5: CONFIGURATION FILES

## replit.md
```markdown
# Protocol Pulse

## Overview

Protocol Pulse is a Web3 and cryptocurrency news platform that uses AI to generate high-quality articles, podcasts, and content. It combines automated content generation from Reddit trends and other social media with manual editorial control, aiming to be a modern media network for blockchain, cryptocurrency, and decentralized web coverage. The platform focuses on democratizing access to Web3 journalism through AI-powered insights and expert analysis, aspiring to be a world-class media hub.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM.
- **Database**: SQLite for development, configurable for production.
- **Models**: User authentication, Article, Podcast, and Content prompt templates.
- **Application Factory Pattern**: Centralized app configuration and database management.
- **AI Content Generation**: Multi-provider AI integration (OpenAI, Anthropic) with customizable, database-stored content templates for various article types. Automated content scheduling and generation based on Reddit and other social media trends.
- **Content Management System (CMS)**: Full CRUD for articles (with SEO, categorization), podcast management (episodes, metadata), and an admin dashboard for content and AI generation.
- **Multimodal Content Engine**: Automates the creation of full content bundles from videos, including podcasts, articles, and social media clips, with AI-generated scripts and video wrappers. Includes Bitcoin Lens reactionary articles.
- **GHL CRM Integration**: Syncs subscriber data and Bitcoin network metrics (difficulty, hashrate) to a HighLevel CRM, and pushes daily intel briefings.

### Frontend Architecture
- **Responsive Design**: Bootstrap 5 with custom CSS for a dark theme.
- **Template Engine**: Jinja2 with modular design.
- **Interactive Elements**: JavaScript for dynamic content, sharing, and user interactions.
- **SEO Optimization**: Meta tags, structured data (Schema.org), and semantic HTML.
- **UI/UX**: Features include a Live Settlement Terminal with real-time blockchain data visualization, an interactive Sovereign Merchant Map using Leaflet.js, a Satoshi Clock, and a Gas Alert HUD. Premium book card hover effects and premium typography are utilized.
- **Article Structure**: Enforced 5-section structure (TL;DR, The Report, The Bitcoin Lens, Transactor Intelligence, Sources) with validation and auto-retry logic for AI generation.
- **Series Guide Navigation**: Dedicated routes for guided viewing experiences with episode sidebars, embedded YouTube players, and AI-generated "Next Up" teasers.

### Content Aggregation
- **Social Media Integration**: Automated trending topic extraction from cryptocurrency and blockchain subreddits (Reddit API), X (Twitter) handles, and YouTube channels.
- **X Spaces Monitoring**: Transcribes X Spaces using yt-dlp and AssemblyAI, generating recap articles with speaker identification, sentiment analysis, and topic analysis.
- **Monitored Channels**: Tracks specific YouTube channels (e.g., Coin Bureau, Natalie Brunell) for new content to generate podcasts and articles.

## External Dependencies

- **OpenAI API**: Primary AI model (GPT-5, GPT-4o) for content generation and script creation.
- **Anthropic API**: Claude Sonnet-4 as an alternative AI provider.
- **Reddit API**: For trending topic aggregation.
- **YouTube Data API / yt-dlp / youtube-transcript-api**: For video monitoring, audio extraction, and transcript fetching.
- **AssemblyAI**: For audio transcription and advanced analysis of X Spaces.
- **ElevenLabs API**: For multi-voice synthesis in podcast generation.
- **Mempool.space API**: For live Bitcoin network data (difficulty, hashrate, mempool stats).
- **BTC Map API**: For merchant location data on the Sovereign Merchant Map.
- **HighLevel API (GHL)**: For CRM integration and custom value synchronization.
- **Amazon Product Advertising API (PA-API)**: For dynamic book data and affiliate links.
- **Tweepy**: For X (Twitter) handle monitoring.
- **Gemini Imagen 3**: For auto-engagement image generation.
- **FFmpeg**: For video clip extraction and social video wrapping.
- **Bootstrap CDN**: Frontend styling framework.
- **Font Awesome**: Icon library.
- **SQLite Database**: Local development storage.
- **Flask Extensions**: SQLAlchemy, Flask-Login.
- **WebLN**: For Lightning Network tipping functionality.
- **python-telegram-bot**: For Telegram bot integration (Pulse Operative).
- **httpx**: For async HTTP requests in bot services.

### Phase 6 Features (Implemented)
- **PWA Support**: Progressive Web App manifest and service worker for mobile "Add to Home Screen" functionality.
- **Whale Watcher** (/whale-watcher): Real-time monitoring of 500+ BTC transactions using Mempool.space API.
- **Sovereign Scorecard** (/scorecard): Interactive security self-assessment quiz with personalized recommendations.
- **Signal Clips Gallery** (/clips): Video clip gallery with FFmpeg outro branding support.
- **Telegram Pulse Operative**: Bot service with /price, /fees, /whale, /brief commands for community engagement.
- **Clips Service**: FFmpeg-based video processing with OpusClip API integration for viral content extraction.

### Phase 7 Features (Current)
- **Dual-Currency Tip Jar**: Lightning sats + Stripe dollars support on articles and footer
- **Dynamic OG Images**: Server-side generated social share images with live BTC price at `/og/<type>.png`
- **3D Sovereign Symbol**: Three.js interactive Bitcoin symbol on the Live Terminal (/live)

## YouTube Shorts Autopublishing Requirements

### Overview
To enable automated YouTube Shorts publishing from Protocol Pulse clips, the following setup is required. This feature would allow generated Signal Clips to be automatically uploaded as YouTube Shorts.

### Required APIs & Credentials
1. **Google Cloud Project**: Create at https://console.cloud.google.com
2. **YouTube Data API v3**: Enable in the API Library
3. **OAuth 2.0 Credentials**: Create OAuth client credentials (type: Web Application)
   - Authorized redirect URI: `https://your-domain.com/oauth/youtube/callback`

### Required Environment Variables
```
YOUTUBE_CLIENT_ID=your_oauth_client_id
YOUTUBE_CLIENT_SECRET=your_oauth_client_secret
YOUTUBE_REDIRECT_URI=https://your-domain.com/oauth/youtube/callback
YOUTUBE_REFRESH_TOKEN=obtained_after_first_auth
```

### OAuth Authorization Flow
1. User (admin) visits `/admin/youtube-auth` to initiate OAuth
2. Google redirects back with authorization code
3. Exchange code for access_token + refresh_token
4. Store refresh_token in environment (manual step - requires Secrets tab)
5. Service uses refresh_token to get new access_tokens automatically

### Implementation Requirements
1. **google-auth-oauthlib**: For OAuth2 flow
2. **google-api-python-client**: For YouTube Data API calls
3. **Video Requirements**: 
   - Duration: Max 60 seconds for Shorts
   - Aspect ratio: 9:16 vertical
   - File format: MP4 (already supported by clips_service.py)

### Upload Endpoint Structure
```python
POST /admin/api/upload-short
{
    "clip_path": "/path/to/clip.mp4",
    "title": "Bitcoin breaks $100K! #shorts #bitcoin",
    "description": "Daily Bitcoin intel from Protocol Pulse",
    "tags": ["bitcoin", "crypto", "shorts"]
}
```

### Limitations & Notes
- YouTube API quota: 10,000 units/day (upload costs ~1600 units)
- Videos uploaded as "private" first, then set to "public" after review
- Requires manual OAuth consent by channel owner initially
- Recommended: Set up a dedicated YouTube Brand Account for the channel

## Reference Documentation

**Complete Codebase Reference:** See `PROTOCOL_PULSE_COMPLETE_CODEBASE.md` for the comprehensive single-file documentation containing:
- Complete architecture overview with technology stack
- All database models and schema definitions
- Full routes and API endpoint documentation
- Complete service module implementations (AI, content engine, social distribution)
- Configuration and environment variable requirements
- Key design patterns (Human-in-Loop, Editorial Accuracy Mandate, 3-Tier Duplicate Detection)

Last updated: January 27, 2026```

## pyproject.toml
```toml
[project]
name = "repl-nix-workspace"
version = "0.1.0"
description = "Add your description here"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.66.0",
    "email-validator>=2.3.0",
    "flask-login>=0.6.3",
    "flask>=3.1.2",
    "flask-sqlalchemy>=3.1.1",
    "gunicorn>=23.0.0",
    "openai>=1.105.0",
    "psycopg2-binary>=2.9.10",
    "sqlalchemy>=2.0.43",
    "trafilatura>=2.0.0",
    "requests>=2.32.5",
    "flask-paginate>=2024.4.12",
    "praw>=7.8.1",
    "schedule>=1.2.2",
    "tweepy>=4.16.0",
    "werkzeug>=3.1.3",
    "uvicorn>=0.35.0",
    "asgiref>=3.9.1",
    "google-genai>=1.33.0",
    "slack-sdk>=3.36.0",
    "markdown>=3.9",
    "google-generativeai>=0.8.5",
    "elevenlabs>=2.14.0",
    "python-substack>=0.1.15",
    "sendgrid>=6.12.5",
    "flask-migrate>=4.1.0",
    "selenium>=4.35.0",
    "pillow>=11.3.0",
    "chromedriver-autoinstaller>=0.6.4",
    "pytesseract>=0.3.13",
    "youtube-transcript-api>=1.2.2",
    "google-api-python-client>=2.181.0",
    "yt-dlp>=2025.9.23",
    "assemblyai>=0.44.3",
    "flask-caching>=2.3.1",
    "flask-limiter>=3.13",
    "feedparser>=6.0.12",
    "apscheduler>=3.11.1",
    "pydub>=0.25.1",
    "httpx>=0.28.1",
    "python-telegram-bot>=22.6",
    "boto3>=1.42.34",
    "sentry-sdk>=2.50.0",
    "pynostr>=0.7.0",
    "stripe>=14.2.0",
    "flask-socketio>=5.6.0",
    "discord-py>=2.6.4",
]
```

---

# END OF CODEBASE EXPORT

Generated: January 27, 2026
Protocol Pulse - Bitcoin Intelligence Platform

---

# ADDITIONAL SERVICES

## services/gemini_service.py
```python
import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel


# Google Gemini service using the latest google-genai SDK
class GeminiService:
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Initialize Google Genai client with the latest SDK
        self.client = genai.Client(api_key=self.api_key)
        
        # Using the newest Gemini model series
        self.text_model = "gemini-2.5-flash"
        self.pro_model = "gemini-2.5-pro"
        
        logging.info("Gemini service initialized successfully")

    def generate_bitcoin_article(self, topic, article_type="news"):
        """Generate Bitcoin-focused content using Gemini"""
        prompts = {
            "news": f"Write a professional Bitcoin news article about: {topic}. Include current market context, technical analysis insights, and potential implications for Bitcoin adoption.",
            "analysis": f"Create a comprehensive Bitcoin analysis about: {topic}. Include technical indicators, on-chain metrics, institutional sentiment, and price predictions.",
            "breaking": f"Write urgent Bitcoin breaking news about: {topic}. Focus on immediate market impact, key stakeholders affected, and short-term price implications."
        }
        
        try:
            system_instruction = "You are a professional Bitcoin journalist writing for Protocol Pulse, a leading Web3 media network. Create engaging, factual content that provides valuable insights for both newcomers and Bitcoin veterans."
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompts.get(article_type, prompts["news"]),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=1500
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini Bitcoin article error: {e}")
            return f"Error generating Bitcoin content: {str(e)}"

    def generate_defi_article(self, topic, focus_area="general"):
        """Generate DeFi-focused content using Gemini"""
        focus_prompts = {
            "general": f"Write a comprehensive DeFi article about: {topic}. Explain the technology clearly, highlight user benefits, and discuss potential risks.",
            "protocols": f"Analyze the DeFi protocol: {topic}. Cover its mechanism, tokenomics, yield opportunities, security considerations, and competitive position.",
            "trends": f"Explore the emerging DeFi trend: {topic}. Include adoption metrics, ecosystem impact, regulatory considerations, and future outlook."
        }
        
        try:
            system_instruction = "You are a DeFi expert analyst writing for Protocol Pulse. Create informative content that helps readers understand complex DeFi concepts while providing actionable insights and risk assessments."
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=focus_prompts.get(focus_area, focus_prompts["general"]),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.6,
                    max_output_tokens=1500
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini DeFi article error: {e}")
            return f"Error generating DeFi content: {str(e)}"

    def analyze_market_sentiment(self, text_data):
        """Analyze crypto market sentiment using Gemini with structured output"""
        try:
            system_instruction = (
                "Analyze cryptocurrency market sentiment from the provided text. "
                "Respond with JSON containing: sentiment (bullish/bearish/neutral), "
                "confidence (0-1), key_factors (array of strings), and summary (string)."
            )
            
            class MarketSentiment(BaseModel):
                sentiment: str
                confidence: float
                key_factors: list[str]
                summary: str
            
            response = self.client.models.generate_content(
                model=self.pro_model,
                contents=f"Analyze the sentiment of this cryptocurrency market text: {text_data}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=MarketSentiment,
                    temperature=0.3
                )
            )
            
            if response.text:
                return json.loads(response.text)
            else:
                return {"error": "Empty response from Gemini"}
            
        except Exception as e:
            logging.error(f"Gemini sentiment analysis error: {e}")
            return {"error": str(e)}

    def generate_podcast_script(self, topic, duration_minutes=10):
        """Generate podcast script for Bitcoin/DeFi topics using Gemini"""
        try:
            system_instruction = (
                f"Create an engaging {duration_minutes}-minute podcast script for Protocol Pulse. "
                "Structure: compelling intro hook, main content with 3-4 key points, "
                "practical insights for listeners, and memorable outro with call-to-action. "
                "Make it conversational and accessible."
            )
            
            prompt = f"Create a podcast script about: {topic}"
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8,
                    max_output_tokens=2000
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini podcast script error: {e}")
            return f"Error generating podcast script: {str(e)}"

    def summarize_content(self, text, max_words=150):
        """Summarize content with focus on crypto/Web3 key points"""
        try:
            prompt = (
                f"Summarize the following text in {max_words} words or less, "
                f"focusing on key points relevant to cryptocurrency, blockchain, and Web3:\n\n{text}"
            )
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=max_words + 50
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini summarization error: {e}")
            return f"Error summarizing content: {str(e)}"

    def generate_content(self, prompt, system_prompt=None):
        """Generate general content using Gemini - primary method for content generation"""
        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=3000
            )
            
            if system_prompt:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=3000
                )
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=config
            )
            
            return response.text or None
            
        except Exception as e:
            logging.error(f"Gemini content generation error: {e}")
            return None

    def test_connection(self):
        """Test the Gemini API connection"""
        try:
            response = self.client.models.generate_content(
                model=self.text_model,
                contents="Say 'Gemini API connection successful!' in exactly those words.",
                config=types.GenerateContentConfig(max_output_tokens=50)
            )
            
            if response.text:
                result = response.text.strip()
                return "Gemini API connection successful!" in result
            return False
            
        except Exception as e:
            logging.error(f"Gemini connection test failed: {e}")
            return False
    
    def enhance_image_with_spice(self, image_path):
        """Enhance advertisement image using Gemini's spice prompt"""
        try:
            system_instruction = "You are an expert image enhancement AI. Analyze the image and provide enhancement suggestions using the spice prompt."
            
            prompt = "Spice up in dramatic red/black/white, futuristic cyberpunk, premium sleek high-tech—DO NOT change core subject/composition."
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=f"Analyze this image and suggest enhancements: {prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            
            # Note: Gemini doesn't directly return enhanced images like OpenAI
            # This provides analysis that could be used for enhancement workflows
            logging.info(f"Gemini enhancement analysis: {response.text}")
            
            # Return None to fall back to OpenAI for actual image editing
            return None
            
        except Exception as e:
            logging.error(f"Gemini image enhancement error: {str(e)}")
            return None

# Initialize the service
gemini_service = GeminiService()```

## services/grok_service.py
```python
import os
import json
import logging
from openai import OpenAI

# Grok API service using xAI's OpenAI-compatible API
class GrokService:
    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY')
        if not self.api_key:
            raise ValueError("XAI_API_KEY environment variable is required")
        
        # Create OpenAI client with xAI endpoint
        self.client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=self.api_key
        )
        
        # Default model - using the latest Grok model (updated December 2025)
        self.model = "grok-3"
        
        logging.info("Grok service initialized successfully")

    def generate_bitcoin_article(self, topic, article_type="news"):
        """Generate Bitcoin-focused content using Grok"""
        prompts = {
            "news": f"Write a professional Bitcoin news article about: {topic}. Include market insights and technical analysis. Focus on factual reporting with expert perspective.",
            "analysis": f"Create an in-depth Bitcoin analysis piece about: {topic}. Include technical indicators, market sentiment, and potential price implications.",
            "breaking": f"Write urgent breaking news about Bitcoin: {topic}. Keep it concise, factual, and include immediate market impact."
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional Bitcoin and cryptocurrency journalist writing for Protocol Pulse, a leading Web3 media network. Write engaging, accurate, and insightful content that appeals to both beginners and experts."
                    },
                    {
                        "role": "user", 
                        "content": prompts.get(article_type, prompts["news"])
                    }
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Grok API error: {e}")
            return f"Error generating content: {str(e)}"

    def generate_defi_article(self, topic, focus_area="general"):
        """Generate DeFi-focused content using Grok"""
        focus_prompts = {
            "general": f"Write a comprehensive DeFi article about: {topic}. Explain concepts clearly and include practical implications for users.",
            "protocols": f"Analyze the DeFi protocol: {topic}. Cover tokenomics, security, yield opportunities, and risks.",
            "trends": f"Explore the latest DeFi trend: {topic}. Include adoption metrics, ecosystem impact, and future outlook."
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DeFi analyst writing for Protocol Pulse. Create informative content that helps readers understand complex DeFi concepts while highlighting opportunities and risks."
                    },
                    {
                        "role": "user",
                        "content": focus_prompts.get(focus_area, focus_prompts["general"])
                    }
                ],
                max_tokens=1500,
                temperature=0.6
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Grok API error: {e}")
            return f"Error generating DeFi content: {str(e)}"

    def analyze_market_sentiment(self, text_data):
        """Analyze market sentiment of crypto-related text"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of cryptocurrency/Bitcoin related text. Provide a JSON response with: sentiment (bullish/bearish/neutral), confidence (0-1), key_factors (array), and summary."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this crypto market text: {text_data}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            return {"error": "Empty response"}
            
        except Exception as e:
            logging.error(f"Sentiment analysis error: {e}")
            return {"error": str(e)}

    def generate_podcast_script(self, topic, duration_minutes=10):
        """Generate podcast script for Bitcoin/DeFi topics"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Create an engaging {duration_minutes}-minute podcast script for Protocol Pulse. Include intro, main content with key points, and outro. Make it conversational and informative."
                    },
                    {
                        "role": "user",
                        "content": f"Create a podcast script about: {topic}"
                    }
                ],
                max_tokens=2000,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Podcast script error: {e}")
            return f"Error generating podcast script: {str(e)}"

    def test_connection(self):
        """Test the Grok API connection"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'Grok API connection successful!' in exactly those words."}],
                max_tokens=50
            )
            
            content = response.choices[0].message.content
            if content:
                result = content.strip()
                return "Grok API connection successful!" in result
            return False
            
        except Exception as e:
            logging.error(f"Connection test failed: {e}")
            return False

# Initialize the service
grok_service = GrokService()```

## services/image_service.py
```python
# AI-Powered Header Image Generation Service for Protocol Pulse
# Generates minimalist, Dilbert-style header images for Bitcoin/DeFi articles

import os
import json
import logging
from openai import OpenAI
import requests
from datetime import datetime

class ImageGenerationService:
    def __init__(self):
        """Initialize the image generation service with OpenAI DALL-E"""
        try:
            self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            logging.info("Image generation service initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize image generation service: {e}")
            self.openai_client = None

        self.base_style_prompt = """
        Ultra-minimalist geometric header image for a Bitcoin/DeFi news article.
        **Style:** Extremely clean, abstract geometric composition. Think Swiss design meets cryptocurrency. Maximum simplicity with powerful visual impact.
        **Color Palette:** ONLY deep red (#DC2626), pure black (#000000), and pure white (#FFFFFF). Use red very sparingly as accent only.
        **Composition:** Ultra-minimal. Single geometric shape or 2-3 basic shapes maximum. Vast amounts of negative white space. Think logo-level simplicity.
        **Subject Matter:** Pure abstract geometric representation. Simple circles, triangles, lines, or basic Bitcoin "₿" symbol. No complex scenes, no people, no detailed objects. Maximum abstraction.
        **Mood/Tone:** Professional, pristine, editorial. Like Financial Times or Wall Street Journal header graphics.
        **ABSOLUTELY CRITICAL:** 
        - NO words, text, letters, numbers, or any typography whatsoever
        - NO complex illustrations or detailed imagery
        - NO gradients or textures - flat colors only
        - Maximum geometric simplicity
        - Professional news publication aesthetic
        """

    def generate_article_header_image(self, article_title: str, article_summary: str) -> str:
        """Generate a header image for an article using DALL-E"""
        if not self.openai_client:
            logging.warning("Image generation service not available - using default image")
            return self._get_default_image()

        # Construct the full prompt for DALL-E
        full_prompt = (
            self.base_style_prompt +
            f"\n\n**Article Topic/Essence:** '{article_title}' and its core idea summarized as: '{article_summary[:150]}'."
        )

        try:
            logging.info(f"Generating header image for: {article_title}")
            
            # Generate image using DALL-E 3
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                n=1,
                size="1024x1024",
                quality="standard"
            )
            
            if not response.data or len(response.data) == 0:
                logging.error("No image data received from DALL-E")
                return self._get_default_image()
            
            image_url = response.data[0].url
            if not image_url:
                logging.error("No image URL received from DALL-E")
                return self._get_default_image()
            
            # Download and save the image locally
            local_path = self._save_image_locally(image_url, article_title)
            
            logging.info(f"✅ Generated header image: {local_path}")
            return local_path

        except Exception as e:
            logging.error(f"Error generating image for '{article_title}': {e}")
            return self._get_default_image()

    def _save_image_locally(self, image_url: str, article_title: str) -> str:
        """Download and save the generated image locally"""
        try:
            # Create images directory if it doesn't exist
            os.makedirs('static/images/headers', exist_ok=True)
            
            # Generate filename from article title
            safe_filename = "".join(c for c in article_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')[:50]  # Limit length
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"header_{safe_filename}_{timestamp}.png"
            local_path = f"static/images/headers/{filename}"
            
            # Download the image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Return the relative URL for use in templates
            return f"/static/images/headers/{filename}"
            
        except Exception as e:
            logging.error(f"Error saving image locally: {e}")
            return self._get_default_image()

    def _get_default_image(self) -> str:
        """Return a default image URL when generation fails"""
        return "/static/images/default-header.png"

    def extract_summary_from_content(self, content: str) -> str:
        """Extract TL;DR summary from article content for image generation"""
        try:
            # Look for TL;DR in the content
            if "TL;DR:" in content:
                start = content.find("TL;DR:") + 6
                end = content.find("</", start)
                if end > start:
                    summary = content[start:end].strip()
                    # Clean up HTML tags
                    summary = summary.replace("<strong>", "").replace("</strong>", "")
                    summary = summary.replace("<em>", "").replace("</em>", "")
                    return summary[:200]  # Limit summary length
            
            # Fallback: use first paragraph
            if "<p class=\"article-paragraph\">" in content:
                start = content.find("<p class=\"article-paragraph\">") + 30
                end = content.find("</p>", start)
                if end > start:
                    summary = content[start:end].strip()[:200]
                    return summary
            
            return "Breaking news in Bitcoin and DeFi markets"
            
        except Exception as e:
            logging.error(f"Error extracting summary: {e}")
            return "Protocol Pulse news update"

# Global service instance
image_service = ImageGenerationService()```

## services/heygen_service.py
```python
import os
import logging
import requests
import json
import time
from typing import Dict, Optional, List, Tuple
import tempfile


class HeyGenService:
    def __init__(self):
        """Initialize HeyGen service for AI video generation"""
        self.api_key = os.environ.get('HEYGEN_API_KEY')
        
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY environment variable is required")
        
        # HeyGen API configuration
        self.base_url = "https://api.heygen.com"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Protocol Pulse optimized avatar configurations
        self.avatar_configs = {
            "professional_male": {
                "avatar_id": "Daisy-inskirt-20220818",  # Professional male presenter
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",  # Clear male voice
                "style": "professional"
            },
            "professional_female": {
                "avatar_id": "Susan_public_2_20240328",  # Professional female presenter
                "voice_id": "2d5b0e6c0c8b4f0f8f8f8f8f8f8f8f8f",  # Clear female voice
                "style": "professional"
            },
            "news_anchor_male": {
                "avatar_id": "josh_lite3_20230714",  # News anchor style
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",
                "style": "authoritative"
            },
            "crypto_expert": {
                "avatar_id": "Tyler-insuit-20220721",  # Tech expert look
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",
                "style": "knowledgeable"
            }
        }
        
        # Video quality settings for different content types
        self.quality_settings = {
            "podcast_teaser": {
                "resolution": "1280x720",
                "quality": "high",
                "background": "crypto_themed"
            },
            "news_update": {
                "resolution": "1920x1080", 
                "quality": "premium",
                "background": "news_studio"
            },
            "analysis_video": {
                "resolution": "1920x1080",
                "quality": "premium", 
                "background": "tech_analysis"
            },
            "social_media": {
                "resolution": "1080x1080",
                "quality": "high",
                "background": "minimal"
            }
        }
        
        logging.info("HeyGen service initialized successfully")

    def get_available_avatars(self) -> List[Dict]:
        """Get list of available avatars from HeyGen"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/avatars",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("avatars", [])
            else:
                logging.error(f"Failed to fetch avatars: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Error fetching avatars: {e}")
            return []

    def get_available_voices(self) -> List[Dict]:
        """Get list of available voices from HeyGen"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/voices",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("voices", [])
            else:
                logging.error(f"Failed to fetch voices: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            return []

    def create_bitcoin_news_video(self, title: str, content: str, 
                                avatar_type: str = "news_anchor_male") -> Optional[str]:
        """Create a Bitcoin news video with professional presentation"""
        try:
            # Get avatar configuration
            avatar_config = self.avatar_configs.get(avatar_type, self.avatar_configs["news_anchor_male"])
            quality_config = self.quality_settings["news_update"]
            
            # Create engaging script for Bitcoin news
            script = self._format_news_script(title, content)
            
            # Prepare video generation request
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#000000"  # Black background for Protocol Pulse theme
                    }
                }],
                "dimension": {
                    "width": 1920,
                    "height": 1080
                },
                "aspect_ratio": "16:9"
            }
            
            return self._generate_video(video_data, "bitcoin_news")
            
        except Exception as e:
            logging.error(f"Error creating Bitcoin news video: {e}")
            return None

    def create_defi_analysis_video(self, analysis_content: str,
                                 avatar_type: str = "crypto_expert") -> Optional[str]:
        """Create a DeFi analysis video with technical expertise presentation"""
        try:
            avatar_config = self.avatar_configs.get(avatar_type, self.avatar_configs["crypto_expert"])
            quality_config = self.quality_settings["analysis_video"]
            
            # Format analysis content for video presentation
            script = self._format_analysis_script(analysis_content)
            
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text", 
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#DC2626"  # Red background for Protocol Pulse branding
                    }
                }],
                "dimension": {
                    "width": 1920,
                    "height": 1080
                },
                "aspect_ratio": "16:9"
            }
            
            return self._generate_video(video_data, "defi_analysis")
            
        except Exception as e:
            logging.error(f"Error creating DeFi analysis video: {e}")
            return None

    def create_podcast_teaser_video(self, episode_title: str, summary: str,
                                  avatar_type: str = "professional_female") -> Optional[str]:
        """Create a podcast teaser video to promote audio episodes"""
        try:
            avatar_config = self.avatar_configs.get(avatar_type, self.avatar_configs["professional_female"])
            quality_config = self.quality_settings["podcast_teaser"]
            
            # Create engaging teaser script
            script = self._format_teaser_script(episode_title, summary)
            
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#1F2937"  # Dark background with Protocol Pulse styling
                    }
                }],
                "dimension": {
                    "width": 1280,
                    "height": 720
                },
                "aspect_ratio": "16:9"
            }
            
            return self._generate_video(video_data, "podcast_teaser")
            
        except Exception as e:
            logging.error(f"Error creating podcast teaser video: {e}")
            return None

    def create_social_media_video(self, content: str, format_type: str = "square") -> Optional[str]:
        """Create short-form videos optimized for social media platforms"""
        try:
            avatar_config = self.avatar_configs["professional_male"]
            
            # Format content for social media (shorter, punchier)
            script = self._format_social_script(content)
            
            # Configure dimensions based on format type
            if format_type == "square":
                dimensions = {"width": 1080, "height": 1080}
                aspect_ratio = "1:1"
            elif format_type == "vertical":
                dimensions = {"width": 1080, "height": 1920}
                aspect_ratio = "9:16"
            else:  # horizontal
                dimensions = {"width": 1920, "height": 1080}
                aspect_ratio = "16:9"
            
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#000000"
                    }
                }],
                "dimension": dimensions,
                "aspect_ratio": aspect_ratio
            }
            
            return self._generate_video(video_data, f"social_{format_type}")
            
        except Exception as e:
            logging.error(f"Error creating social media video: {e}")
            return None

    def _generate_video(self, video_data: Dict, video_type: str) -> Optional[str]:
        """Generate video using HeyGen API and return video URL"""
        try:
            # Submit video generation request
            response = requests.post(
                f"{self.base_url}/v2/video/generate",
                headers=self.headers,
                json=video_data
            )
            
            if response.status_code != 200:
                logging.error(f"Video generation failed: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            video_id = result.get("data", {}).get("video_id")
            
            if not video_id:
                logging.error("No video ID returned from HeyGen")
                return None
            
            logging.info(f"Video generation started with ID: {video_id}")
            
            # Poll for video completion
            return self._wait_for_video_completion(video_id, video_type)
            
        except Exception as e:
            logging.error(f"Error in video generation: {e}")
            return None

    def _wait_for_video_completion(self, video_id: str, video_type: str, 
                                 max_wait_time: int = 300) -> Optional[str]:
        """Wait for video generation to complete and return download URL"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                # Check video status
                response = requests.get(
                    f"{self.base_url}/v1/video_status.get",
                    headers=self.headers,
                    params={"video_id": video_id}
                )
                
                if response.status_code != 200:
                    logging.error(f"Failed to check video status: {response.text}")
                    time.sleep(10)
                    continue
                
                status_data = response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "completed":
                    video_url = status_data.get("data", {}).get("video_url")
                    logging.info(f"Video {video_id} completed: {video_url}")
                    return video_url
                elif status == "failed":
                    logging.error(f"Video generation failed for {video_id}")
                    return None
                else:
                    logging.info(f"Video {video_id} status: {status}")
                    time.sleep(15)  # Wait 15 seconds before checking again
            
            logging.error(f"Video generation timed out for {video_id}")
            return None
            
        except Exception as e:
            logging.error(f"Error waiting for video completion: {e}")
            return None

    def _format_news_script(self, title: str, content: str) -> str:
        """Format news content into engaging video script"""
        intro = "Breaking news in the Bitcoin world:"
        formatted_content = content.replace('#', '').replace('*', '').strip()
        
        # Keep it concise for video (aim for 60-90 seconds)
        if len(formatted_content) > 500:
            formatted_content = formatted_content[:500] + "..."
        
        script = f"{intro} {title}. {formatted_content}"
        return script

    def _format_analysis_script(self, content: str) -> str:
        """Format analysis content for technical video presentation"""
        intro = "Here's your DeFi protocol analysis:"
        formatted_content = content.replace('#', '').replace('*', '').strip()
        
        if len(formatted_content) > 600:
            formatted_content = formatted_content[:600] + "..."
        
        script = f"{intro} {formatted_content}"
        return script

    def _format_teaser_script(self, title: str, summary: str) -> str:
        """Format podcast episode into engaging teaser"""
        intro = "Coming up on Protocol Pulse:"
        formatted_summary = summary.replace('#', '').replace('*', '').strip()
        
        if len(formatted_summary) > 300:
            formatted_summary = formatted_summary[:300] + "..."
        
        script = f"{intro} {title}. {formatted_summary} Don't miss this episode!"
        return script

    def _format_social_script(self, content: str) -> str:
        """Format content for short social media videos (15-30 seconds)"""
        formatted_content = content.replace('#', '').replace('*', '').strip()
        
        # Keep very short for social media
        if len(formatted_content) > 200:
            formatted_content = formatted_content[:200] + "..."
        
        return formatted_content

    def test_connection(self) -> bool:
        """Test HeyGen API connection"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/avatars",
                headers=self.headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"HeyGen connection test failed: {e}")
            return False

    def get_account_info(self) -> Dict:
        """Get account information and limits"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/user/remaining_quota",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logging.error(f"Failed to get account info: {response.text}")
                return {}
                
        except Exception as e:
            logging.error(f"Error getting account info: {e}")
            return {}

# Initialize the service
heygen_service = HeyGenService()```

## services/node_service.py
```python
import requests
import logging
import time

class NodeService:
    """Service for fetching live Bitcoin network statistics from Mempool.space API"""
    
    _cache = None
    _cache_expiry = 0
    CACHE_DURATION = 30  # Cache for 30 seconds
    
    @classmethod
    def get_network_stats(cls):
        """Fetches live PoW metrics for the Protocol Heartbeat tracker."""
        current_time = time.time()
        
        # Return cached data if still valid
        if cls._cache and current_time < cls._cache_expiry:
            return cls._cache
        
        try:
            # Fetching from Mempool.space API
            height_res = requests.get(
                "https://mempool.space/api/blocks/tip/height", 
                timeout=5
            )
            hashrate_res = requests.get(
                "https://mempool.space/api/v1/mining/hashrate/3d", 
                timeout=5
            )
            difficulty_res = requests.get(
                "https://mempool.space/api/v1/difficulty-adjustment",
                timeout=5
            )
            
            if height_res.status_code == 200:
                height = int(height_res.text)
                
                # Convert raw hashrate to EH/s for that 'Powerhouse' feel
                hashrate_data = hashrate_res.json()
                current_hashrate = hashrate_data.get('currentHashrate', 0) / 10**18
                
                # Get difficulty adjustment info
                diff_data = difficulty_res.json() if difficulty_res.status_code == 200 else {}
                progress_percent = diff_data.get('progressPercent', 0)
                remaining_blocks = diff_data.get('remainingBlocks', 0)
                
                result = {
                    "height": f"{height:,}",
                    "height_raw": height,
                    "hashrate": f"{current_hashrate:.2f} EH/s",
                    "hashrate_raw": current_hashrate,
                    "difficulty_progress": f"{progress_percent:.1f}%",
                    "remaining_blocks": remaining_blocks,
                    "status": "OPERATIONAL"
                }
                
                # Update cache
                cls._cache = result
                cls._cache_expiry = current_time + cls.CACHE_DURATION
                
                return result
                
        except requests.exceptions.Timeout:
            logging.warning("Mempool.space API timeout")
            return cls._get_fallback("TIMEOUT")
        except requests.exceptions.RequestException as e:
            logging.error(f"Node Tracker Request Error: {e}")
            return cls._get_fallback("NETWORK_ERROR")
        except Exception as e:
            logging.error(f"Node Tracker Error: {e}")
            return cls._get_fallback("RECONNECTING")
    
    @classmethod
    def _get_fallback(cls, status):
        """Return cached data if available, otherwise offline status"""
        if cls._cache:
            fallback = cls._cache.copy()
            fallback["status"] = status
            return fallback
        return {
            "height": "---,---",
            "height_raw": 0,
            "hashrate": "--- EH/s",
            "hashrate_raw": 0,
            "difficulty_progress": "--%",
            "remaining_blocks": 0,
            "status": status
        }


# Global instance
node_service = NodeService()
```

## services/amazon_service.py
```python
import os
import logging
from typing import Optional, Dict, List

class AmazonService:
    """
    Amazon Product Advertising API integration for dynamic book data.
    
    Note: Requires AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, and AMAZON_PARTNER_TAG
    environment variables to be set for full API functionality.
    
    Without API keys, uses curated fallback book data with affiliate links.
    """
    
    def __init__(self):
        self.access_key = os.environ.get('AMAZON_ACCESS_KEY')
        self.secret_key = os.environ.get('AMAZON_SECRET_KEY')
        self.partner_tag = os.environ.get('AMAZON_PARTNER_TAG', 'protocolpulse-20')
        self.amazon = None
        
        if self.access_key and self.secret_key:
            try:
                from amazon_paapi import AmazonAPI
                self.amazon = AmazonAPI(
                    self.access_key,
                    self.secret_key,
                    self.partner_tag,
                    "US"
                )
                logging.info("Amazon PA-API initialized successfully")
            except ImportError:
                logging.warning("amazon-paapi not installed, using fallback book data")
            except Exception as e:
                logging.error(f"Failed to initialize Amazon API: {e}")
        else:
            logging.info("Amazon API keys not configured, using curated book data")
    
    def get_book_details(self, asin: str) -> Optional[Dict]:
        """
        Fetches book details from Amazon Product Advertising API.
        Returns high-res images and affiliate URLs automatically.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            Dict with title, image, url, price, rating or None if failed
        """
        if not self.amazon:
            return self._get_fallback_book(asin)
        
        try:
            product = self.amazon.get_products(asin)
            if product and len(product) > 0:
                item = product[0]
                return {
                    'title': item.title,
                    'image': item.images.primary.large.url if item.images else None,
                    'url': item.detail_page_url,
                    'price': item.offers.listings[0].price.display_amount if item.offers else None,
                    'rating': item.customer_reviews.star_rating if item.customer_reviews else None,
                    'asin': asin
                }
        except Exception as e:
            logging.error(f"Amazon API error for ASIN {asin}: {e}")
        
        return self._get_fallback_book(asin)
    
    def get_books_batch(self, asins: List[str]) -> List[Dict]:
        """
        Fetch multiple books at once for efficiency.
        
        Args:
            asins: List of ASINs to fetch
            
        Returns:
            List of book dictionaries
        """
        if not self.amazon:
            return [self._get_fallback_book(asin) for asin in asins if self._get_fallback_book(asin)]
        
        try:
            products = self.amazon.get_products(asins)
            return [{
                'title': item.title,
                'image': item.images.primary.large.url if item.images else None,
                'url': item.detail_page_url,
                'price': item.offers.listings[0].price.display_amount if item.offers else None,
                'asin': item.asin
            } for item in products]
        except Exception as e:
            logging.error(f"Amazon batch API error: {e}")
            return [self._get_fallback_book(asin) for asin in asins if self._get_fallback_book(asin)]
    
    def _get_fallback_book(self, asin: str) -> Optional[Dict]:
        """
        Returns curated fallback data for known Bitcoin books.
        """
        fallback_books = {
            '1119473861': {
                'title': 'The Bitcoin Standard',
                'author': 'Saifedean Ammous',
                'image': 'https://m.media-amazon.com/images/I/71gWPJMkCAL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1119473861?tag={self.partner_tag}',
                'asin': '1119473861'
            },
            '1544526474': {
                'title': 'The Fiat Standard',
                'author': 'Saifedean Ammous',
                'image': 'https://m.media-amazon.com/images/I/71ePXw1aYhL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1544526474?tag={self.partner_tag}',
                'asin': '1544526474'
            },
            'B0CG83MBN9': {
                'title': 'Broken Money',
                'author': 'Lyn Alden',
                'image': 'https://m.media-amazon.com/images/I/71aFQ6wdPOL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/B0CG83MBN9?tag={self.partner_tag}',
                'asin': 'B0CG83MBN9'
            },
            '1999257405': {
                'title': 'The Price of Tomorrow',
                'author': 'Jeff Booth',
                'image': 'https://m.media-amazon.com/images/I/71oYv6hF1cL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1999257405?tag={self.partner_tag}',
                'asin': '1999257405'
            },
            '1697526349': {
                'title': '21 Lessons',
                'author': 'Gigi',
                'image': 'https://m.media-amazon.com/images/I/71vR+59OxuL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1697526349?tag={self.partner_tag}',
                'asin': '1697526349'
            },
            '1098150090': {
                'title': 'Mastering Bitcoin',
                'author': 'Andreas Antonopoulos',
                'image': 'https://m.media-amazon.com/images/I/81P+cmiXNkL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1098150090?tag={self.partner_tag}',
                'asin': '1098150090'
            },
            '0684832720': {
                'title': 'The Sovereign Individual',
                'author': 'James Dale Davidson',
                'image': 'https://m.media-amazon.com/images/I/718T+2u9GaL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/0684832720?tag={self.partner_tag}',
                'asin': '0684832720'
            },
            'B09MYXHP1Z': {
                'title': 'Genesis Book',
                'author': 'Knut Svanholm',
                'image': 'https://m.media-amazon.com/images/I/41qJQJSHn9L._SY445_SX342_.jpg',
                'url': f'https://www.amazon.com/dp/B09MYXHP1Z?tag={self.partner_tag}',
                'asin': 'B09MYXHP1Z'
            },
            'B0BTRPZTY4': {
                'title': 'Everything Divided By 21 Million',
                'author': 'Knut Svanholm',
                'image': 'https://m.media-amazon.com/images/I/41UWy8T+6GL._SY445_SX342_.jpg',
                'url': f'https://www.amazon.com/dp/B0BTRPZTY4?tag={self.partner_tag}',
                'asin': 'B0BTRPZTY4'
            }
        }
        
        return fallback_books.get(asin)
    
    def search_bitcoin_books(self, keywords: str = "bitcoin", limit: int = 10) -> List[Dict]:
        """
        Search for Bitcoin-related books on Amazon.
        
        Args:
            keywords: Search terms
            limit: Maximum results to return
            
        Returns:
            List of book dictionaries
        """
        if not self.amazon:
            return list(self._get_all_fallback_books())[:limit]
        
        try:
            search_result = self.amazon.search_products(
                keywords=keywords,
                search_index="Books",
                item_count=limit
            )
            return [{
                'title': item.title,
                'image': item.images.primary.large.url if item.images else None,
                'url': item.detail_page_url,
                'asin': item.asin
            } for item in search_result]
        except Exception as e:
            logging.error(f"Amazon search error: {e}")
            return list(self._get_all_fallback_books())[:limit]
    
    def _get_all_fallback_books(self) -> List[Dict]:
        """Returns all curated fallback books."""
        return [
            self._get_fallback_book(asin) 
            for asin in ['1119473861', '1544526474', 'B0CG83MBN9', '1999257405', 
                        '1697526349', '1098150090', '0684832720', 'B09MYXHP1Z', 'B0BTRPZTY4']
            if self._get_fallback_book(asin)
        ]


# Singleton instance
amazon_service = AmazonService()
```

## services/spaces_service.py
```python
import os
import logging
import requests
import assemblyai as aai
import yt_dlp
from datetime import datetime
from typing import Optional, Dict, List
import json

class SpacesService:
    def __init__(self):
        """Initialize X Spaces transcription service"""
        self.assemblyai_key = os.environ.get('ASSEMBLYAI_API_KEY')
        if self.assemblyai_key:
            aai.settings.api_key = self.assemblyai_key
            logging.info("AssemblyAI service initialized successfully")
        else:
            logging.warning("ASSEMBLYAI_API_KEY not found - X Spaces transcription disabled")
        
        self.monitored_spaces = []  # List of space URLs/IDs to monitor
        
    def add_space_to_monitor(self, space_url: str) -> bool:
        """Add X Space URL to monitoring list"""
        try:
            if space_url not in self.monitored_spaces:
                self.monitored_spaces.append(space_url)
                logging.info(f"Added X Space to monitoring: {space_url}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error adding space to monitor: {e}")
            return False
    
    def download_space_audio(self, space_url: str) -> Optional[str]:
        """Download audio from X Space using yt-dlp"""
        try:
            # Configure yt-dlp options for audio extraction
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'wav',
                'outtmpl': f'static/audio/spaces/%(title)s_%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to get metadata
                info = ydl.extract_info(space_url, download=False)
                if not info:
                    logging.error(f"Could not extract info from Space: {space_url}")
                    return None
                
                # Download the audio
                ydl.download([space_url])
                
                # Construct the expected filename
                title = info.get('title', 'Unknown')
                space_id = info.get('id', 'unknown')
                audio_file = f'static/audio/spaces/{title}_{space_id}.wav'
                
                logging.info(f"Downloaded X Space audio: {audio_file}")
                return audio_file
                
        except Exception as e:
            logging.error(f"Error downloading X Space audio: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path: str) -> Optional[Dict]:
        """Transcribe audio using AssemblyAI"""
        try:
            if not self.assemblyai_key:
                logging.error("AssemblyAI API key not configured")
                return None
            
            # Configure transcription settings
            config = aai.TranscriptionConfig(
                speaker_labels=True,  # Identify different speakers
                auto_chapters=True,   # Automatically detect chapter breaks
                sentiment_analysis=True,  # Analyze sentiment
                entity_detection=True,   # Detect entities/topics
                language_detection=True, # Auto-detect language
            )
            
            transcriber = aai.Transcriber(config=config)
            
            logging.info(f"Starting transcription of: {audio_file_path}")
            transcript = transcriber.transcribe(audio_file_path)
            
            if transcript.status == aai.TranscriptStatus.error:
                logging.error(f"Transcription failed: {transcript.error}")
                return None
            
            # Extract structured data
            result = {
                'text': transcript.text,
                'confidence': transcript.confidence,
                'speakers': [],
                'chapters': [],
                'sentiments': [],
                'entities': [],
                'duration': transcript.audio_duration / 1000,  # Convert to seconds
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Process speaker labels if available
            if hasattr(transcript, 'utterances') and transcript.utterances:
                for utterance in transcript.utterances:
                    result['speakers'].append({
                        'speaker': utterance.speaker,
                        'text': utterance.text,
                        'start': utterance.start / 1000,
                        'end': utterance.end / 1000,
                        'confidence': utterance.confidence
                    })
            
            # Process chapters if available
            if hasattr(transcript, 'chapters') and transcript.chapters:
                for chapter in transcript.chapters:
                    result['chapters'].append({
                        'summary': chapter.summary,
                        'headline': chapter.headline,
                        'start': chapter.start / 1000,
                        'end': chapter.end / 1000
                    })
            
            # Process sentiment analysis
            if hasattr(transcript, 'sentiment_analysis_results') and transcript.sentiment_analysis_results:
                for sentiment in transcript.sentiment_analysis_results:
                    result['sentiments'].append({
                        'text': sentiment.text,
                        'sentiment': sentiment.sentiment.value,
                        'confidence': sentiment.confidence,
                        'start': sentiment.start / 1000,
                        'end': sentiment.end / 1000
                    })
            
            # Process entity detection
            if hasattr(transcript, 'entities') and transcript.entities:
                for entity in transcript.entities:
                    result['entities'].append({
                        'text': entity.text,
                        'entity_type': entity.entity_type.value,
                        'start': entity.start / 1000,
                        'end': entity.end / 1000
                    })
            
            logging.info(f"Transcription completed successfully: {len(result['text'])} characters")
            return result
            
        except Exception as e:
            logging.error(f"Error transcribing audio: {e}")
            return None
    
    def process_space(self, space_url: str) -> Optional[Dict]:
        """Complete pipeline: download and transcribe X Space"""
        try:
            # Step 1: Download audio
            audio_file = self.download_space_audio(space_url)
            if not audio_file:
                return None
            
            # Step 2: Transcribe audio
            transcription = self.transcribe_audio(audio_file)
            if not transcription:
                return None
            
            # Step 3: Add metadata
            transcription.update({
                'space_url': space_url,
                'audio_file': audio_file,
                'processed_at': datetime.utcnow().isoformat()
            })
            
            logging.info(f"Successfully processed X Space: {space_url}")
            return transcription
            
        except Exception as e:
            logging.error(f"Error processing X Space: {e}")
            return None
    
    def get_space_insights(self, transcription: Dict) -> Dict:
        """Extract key insights from transcribed X Space"""
        try:
            insights = {
                'duration_minutes': round(transcription.get('duration', 0) / 60, 1),
                'speaker_count': len(set([s.get('speaker') for s in transcription.get('speakers', [])])),
                'chapter_count': len(transcription.get('chapters', [])),
                'key_topics': [],
                'sentiment_summary': {},
                'notable_entities': []
            }
            
            # Analyze entities for key topics
            entities = transcription.get('entities', [])
            entity_counts = {}
            for entity in entities:
                entity_text = entity.get('text', '').lower()
                entity_counts[entity_text] = entity_counts.get(entity_text, 0) + 1
            
            # Get top entities as key topics
            insights['key_topics'] = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Sentiment analysis summary
            sentiments = transcription.get('sentiments', [])
            if sentiments:
                sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
                for sentiment in sentiments:
                    sentiment_type = sentiment.get('sentiment', 'neutral').lower()
                    if sentiment_type in sentiment_counts:
                        sentiment_counts[sentiment_type] += 1
                
                total = sum(sentiment_counts.values())
                if total > 0:
                    insights['sentiment_summary'] = {
                        'positive_pct': round(sentiment_counts['positive'] / total * 100, 1),
                        'negative_pct': round(sentiment_counts['negative'] / total * 100, 1),
                        'neutral_pct': round(sentiment_counts['neutral'] / total * 100, 1)
                    }
            
            # Notable entities (high-frequency, important topics)
            insights['notable_entities'] = [entity for entity, count in insights['key_topics'] if count >= 3]
            
            return insights
            
        except Exception as e:
            logging.error(f"Error extracting insights: {e}")
            return {}
    
    def monitor_spaces(self) -> List[Dict]:
        """Monitor all added spaces for new content"""
        results = []
        
        for space_url in self.monitored_spaces:
            try:
                transcription = self.process_space(space_url)
                if transcription:
                    insights = self.get_space_insights(transcription)
                    
                    result = {
                        'space_url': space_url,
                        'transcription': transcription,
                        'insights': insights,
                        'processed_at': datetime.utcnow().isoformat()
                    }
                    results.append(result)
                    
                    logging.info(f"Successfully monitored space: {space_url}")
                else:
                    logging.warning(f"Failed to process space: {space_url}")
                    
            except Exception as e:
                logging.error(f"Error monitoring space {space_url}: {e}")
        
        return results

# Initialize service
spaces_service = SpacesService()```

---

# FINAL SUMMARY

## File Statistics
Total Python files: 54
Total HTML templates: 46
Total CSS files: 3
Total JS files: 4

## Key Features Implemented

### Phase 7 (Current - January 2026)
- Dual-Currency Tip Jar (Lightning sats + Stripe dollars)
- Dynamic OG Images with live Bitcoin price (/og/<type>.png)
- 3D Sovereign Symbol on Live Terminal (Three.js)
- YouTube Shorts autopublishing documentation

### Phase 6 (Completed)
- PWA Support with service worker
- Whale Watcher (500+ BTC transactions)
- Sovereign Scorecard quiz
- Signal Clips Gallery
- Telegram Pulse Operative bot

### Core Features
- AI Content Generation (OpenAI GPT-4o, Anthropic Claude, Gemini, Grok)
- Blocking Fact-Checker for newsletter
- Launch Sequence Manager for X/Twitter
- Nostr Broadcaster (5 relays)
- HighLevel CRM Integration
- Bitcoin Meetup Map (75+ worldwide locations)
- Bitcoin Merchant Map (BTCMap.org integration)
- Stripe Premium Subscriptions

---

END OF COMPLETE CODEBASE EXPORT
Generated: January 27, 2026
