# Protocol Pulse - Complete Codebase Export
## Generated: January 2026

This document contains the complete source code for the Protocol Pulse project.

---

## Core Application Files

### app.py
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
app.secret_key = os.environ.get("SESSION_SECRET", "protocol-pulse-secret-key-2025")

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

# Import routes after app creation
import routes
```

### main.py
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

### models.py
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
```

### routes.py
```python
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from models import Article, Podcast, ContentPrompt, User, Advertisement, AutomationRun
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
    
    return render_template('index.html', 
                         featured_articles=featured_articles,
                         recent_articles=recent_articles,
                         featured_podcasts=featured_podcasts,
                         prices=prices,
                         price_service=price_service)

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
        
        # Our Book Series - books featured on the podcast
        our_books = [
            {
                'title': 'Genesis Book',
                'author': 'Knut Svanholm',
                'description': 'The first book in the series exploring the genesis of Bitcoin and its philosophical foundations.',
                'cover_url': 'https://m.media-amazon.com/images/I/41qJQJSHn9L._SY445_SX342_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B09MYXHP1Z?tag={affiliate_tag}'
            },
            {
                'title': 'Daylight Robbery',
                'author': 'Dominic Frisby',
                'description': 'A fascinating history of taxation from ancient times to the present day, and what it means for our future.',
                'cover_url': 'https://m.media-amazon.com/images/I/71z1YjQ7URL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/0241360544?tag={affiliate_tag}'
            },
            {
                'title': 'The Big Print',
                'author': 'Saifedean Ammous',
                'description': 'An exploration of fiat money, central banking, and the consequences of monetary inflation.',
                'cover_url': 'https://m.media-amazon.com/images/I/71RYSNi3w7L._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1544526474?tag={affiliate_tag}'
            },
            {
                'title': 'Everything Divided By 21 Million',
                'author': 'Knut Svanholm',
                'description': 'A philosophical exploration of Bitcoin through the lens of scarcity and absolute mathematical certainty.',
                'cover_url': 'https://m.media-amazon.com/images/I/41UWy8T+6GL._SY445_SX342_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B0BTRPZTY4?tag={affiliate_tag}'
            }
        ]
        
        # Recommended Bitcoin Books - bestsellers and essentials
        recommended_books = [
            {
                'title': 'The Bitcoin Standard',
                'author': 'Saifedean Ammous',
                'description': 'The essential guide to understanding Bitcoin as sound money and the history of monetary systems.',
                'cover_url': 'https://m.media-amazon.com/images/I/71gWPJMkCAL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1119473861?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'The Fiat Standard',
                'author': 'Saifedean Ammous',
                'description': 'A companion to The Bitcoin Standard examining our current fiat monetary system.',
                'cover_url': 'https://m.media-amazon.com/images/I/71ePXw1aYhL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1544526474?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'Broken Money',
                'author': 'Lyn Alden',
                'description': 'A comprehensive analysis of the global monetary system and why Bitcoin matters.',
                'cover_url': 'https://m.media-amazon.com/images/I/71aFQ6wdPOL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/B0CG83MBN9?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'The Price of Tomorrow',
                'author': 'Jeff Booth',
                'description': 'Why deflation is the key to an abundant future in a technologically advancing world.',
                'cover_url': 'https://m.media-amazon.com/images/I/71oYv6hF1cL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1999257405?tag={affiliate_tag}',
                'bestseller': False
            },
            {
                'title': '21 Lessons',
                'author': 'Gigi',
                'description': 'What falling down the Bitcoin rabbit hole taught one developer about philosophy, economics, and technology.',
                'cover_url': 'https://m.media-amazon.com/images/I/71vR+59OxuL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1697526349?tag={affiliate_tag}',
                'bestseller': False
            },
            {
                'title': 'Mastering Bitcoin',
                'author': 'Andreas Antonopoulos',
                'description': 'The technical guide to understanding and programming Bitcoin at a deep level.',
                'cover_url': 'https://m.media-amazon.com/images/I/81P+cmiXNkL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1098150090?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'The Sovereign Individual',
                'author': 'James Dale Davidson',
                'description': 'A prescient 1997 book predicting the rise of digital money and the transformation of society.',
                'cover_url': 'https://m.media-amazon.com/images/I/718T+2u9GaL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/0684832720?tag={affiliate_tag}',
                'bestseller': True
            },
            {
                'title': 'Layered Money',
                'author': 'Nik Bhatia',
                'description': 'An accessible introduction to how money works in layers, from gold to Bitcoin.',
                'cover_url': 'https://m.media-amazon.com/images/I/71vDhWDNPNL._SY522_.jpg',
                'amazon_url': f'https://www.amazon.com/dp/1736110519?tag={affiliate_tag}',
                'bestseller': False
            }
        ]
        
        # Get YouTube series data for Terminal Player
        youtube_series = YouTubeService.get_all_series()
        
        return render_template('media_hub.html', 
                               shows=shows, 
                               products=products,
                               our_books=our_books,
                               recommended_books=recommended_books,
                               youtube_series=youtube_series,
                               get_thumbnail=YouTubeService.get_thumbnail)
    except Exception as e:
        logging.error(f"Error loading media hub: {e}")
        return render_template('media_hub.html', shows=[], products=[], our_books=[], recommended_books=[], youtube_series={}, get_thumbnail=YouTubeService.get_thumbnail)

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

@app.route('/merch')
def merch():
    """Merchandise store page"""
    return render_template('merch.html')

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
        
        # Save to database with auto-approval (hands-off publishing)
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
            published=True  # Auto-approved for hands-off publishing
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
            'message': 'Article auto-approved and published' + (f' to Substack: {substack_url}' if substack_url else '')
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
    
    # Get ConvertKit credentials from environment variables (set in Replit Secrets)
    api_key = os.environ.get('CONVERTKIT_API_KEY')
    form_id = os.environ.get('CONVERTKIT_FORM_ID')
    
    if not api_key or not form_id:
        return jsonify({'error': 'ConvertKit API key and Form ID required'}), 500
    
    url = f"https://api.convertkit.com/v3/forms/{form_id}/subscribe"
    data = {'api_key': api_key, 'email': email, 'first_name': first_name}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return jsonify({'success': True})
    return jsonify({'error': 'Signup failed'}), 500

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
```

### routes_social.py
```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from services.reddit_service import RedditService
from services.x_service import XService
from services.youtube_service import YouTubeService
from services.ai_service import AIService
from app import db
from models import Article
import os
import uuid
import requests
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
import pytesseract
from PIL import Image
import yt_dlp
import assemblyai

social = Blueprint('social', __name__)

@social.route('/admin/social-monitor', methods=['GET', 'POST'])
@login_required
def social_monitor():
    if request.method == 'POST':
        handles = request.form.get('x_handles', 'CaitlinLong_,lopp,adam3us,woonomic,bitschmidty,LawrenceLepard,maxkeiser,jackmallers,TheBTCTherapist').split(',')
        subreddits = request.form.get('subreddits', 'cryptocurrency,bitcoin,ethtrader,satoshistreetbets,cryptomarkets,cryptotechnology,defi,altcoin').split(',')
        websites = request.form.get('websites', 'https://www.coindesk.com').split(',')
        youtube_handles = request.form.get('youtube_handles', 'BitcoinMagazine,nataliebrunell,bytefederal,BTCSessions,SimplyBitcoin,CoinBureau,thejackmallersshow,RobertBreedlove22').split(',')
        return jsonify({'success': True, 'handles': handles, 'subreddits': subreddits, 'websites': websites, 'youtube_handles': youtube_handles})
    return render_template('admin/social_monitor.html')

@social.route('/api/monitor-content')
@login_required
def monitor_content():
    return monitor_content_impl()

@social.route('/api/test-monitor-content')
def test_monitor_content():
    """Test endpoint without authentication"""
    return simple_spaces_test()

@social.route('/api/test-spaces-only')
def test_spaces_only():
    """Test only X Spaces functionality"""
    return simple_spaces_test()

def simple_spaces_test():
    """Simple test focusing only on X Spaces functionality"""
    trends = []
    
    # X Spaces (Testing with mock data)
    try:
        # For testing purposes, create a mock X Space
        mock_space_url = "https://twitter.com/i/spaces/1example" 
        mock_transcript = "Bitcoin is revolutionizing the global financial system through blockchain technology. We're seeing incredible adoption across institutions and retail investors. The future of decentralized finance looks very bullish with continued Web3 innovation and cryptocurrency growth."
        
        # Mock the download and transcription process
        logging.info(f"Testing X Spaces functionality with mock URL: {mock_space_url}")
        
        # Simulate audio download (would use real yt-dlp in production)
        mock_audio_path = "static/audio/mock_space_test.mp3"
        logging.info(f"Mock audio download successful: {mock_audio_path}")
        
        # Simulate transcription (would use real AssemblyAI in production)
        logging.info(f"Mock transcript generated: {mock_transcript[:100]}...")
        
        # Test our analysis functions
        topic_analysis = analyze_topic(mock_transcript)
        nuance_analysis = analyze_nuance(mock_transcript)
        
        # Take screenshot of the mock Space URL
        screenshot = take_screenshot(mock_space_url)
        screenshot_text = extract_screenshot_text(screenshot)
        
        # Add mock Space to trends
        trends.append({
            'type': 'spaces', 
            'title': 'Mock Bitcoin Discussion Space', 
            'content': mock_transcript, 
            'screenshot': screenshot,
            'screenshot_text': screenshot_text,
            'transcript_text': mock_transcript, 
            'topic': topic_analysis, 
            'nuance': nuance_analysis,
            'url': mock_space_url,
            'audio_url': mock_audio_path
        })
        
        logging.info(f"Successfully added mock X Space: Topic={topic_analysis}, Sentiment={nuance_analysis}")
        logging.info(f"Mock X Space processing completed - transcript saved and article ready for generation")
        
    except Exception as e:
        logging.error(f"Error in X Spaces testing: {e}")
    
    logging.info(f"X Spaces test completed: {len(trends)} spaces processed")
    
    return jsonify({'trends': trends, 'count': len(trends), 'status': 'success'})

def monitor_content_impl():
    reddit = RedditService()
    x_service = XService()
    youtube = YouTubeService()
    ai = AIService()
    trends = []
    
    # Reddit
    for sub in ['cryptocurrency', 'bitcoin', 'ethtrader', 'satoshistreetbets', 'cryptomarkets', 'cryptotechnology', 'defi', 'altcoin']:
        posts = reddit.get_trending_topics([sub], limit=2)
        for post in posts:
            screenshot = take_screenshot(post['permalink'])
            screenshot_text = extract_screenshot_text(screenshot)
            trends.append({'type': 'reddit', 'title': post['title'], 'content': post['selftext'], 'screenshot': screenshot, 'screenshot_text': screenshot_text})
    
    # X
    for handle in ['CaitlinLong_', 'lopp', 'adam3us', 'woonomic', 'bitschmidty', 'LawrenceLepard', 'maxkeiser', 'jackmallers', 'TheBTCTherapist']:
        tweets = x_service.get_feedback(handle)
        for tweet in tweets:
            screenshot = take_screenshot(f"https://x.com/{handle}/status/{tweet['id']}")
            screenshot_text = extract_screenshot_text(screenshot)
            trends.append({'type': 'x', 'title': tweet['text'], 'content': tweet['text'], 'screenshot': screenshot, 'screenshot_text': screenshot_text, 'topic': tweet['topic'], 'nuance': tweet['nuance']})
    
    # Websites
    for url in ['https://www.coindesk.com']:
        content = requests.get(url).text
        if 'sponsored' not in content.lower():
            screenshot = take_screenshot(url)
            screenshot_text = extract_screenshot_text(screenshot)
            trends.append({'type': 'website', 'title': url, 'content': content[:500], 'screenshot': screenshot, 'screenshot_text': screenshot_text})
    
    # YouTube
    videos = youtube.get_recent_videos()
    for video in videos:
        screenshot = take_screenshot(f"https://www.youtube.com/watch?v={video['id']}")
        screenshot_text = extract_screenshot_text(screenshot)
        trends.append({'type': 'youtube', 'title': video['title'], 'content': video['transcript'], 'screenshot': screenshot, 'screenshot_text': screenshot_text, 'video_url': f"https://www.youtube.com/embed/{video['id']}", 'topic': video['topic'], 'nuance': video['nuance']})

    # X Spaces (Testing with mock data)
    try:
        # For testing purposes, create a mock X Space
        mock_space_url = "https://twitter.com/i/spaces/1example" 
        mock_transcript = "Bitcoin is revolutionizing the global financial system through blockchain technology. We're seeing incredible adoption across institutions and retail investors. The future of decentralized finance looks very bullish with continued Web3 innovation and cryptocurrency growth."
        
        # Mock the download and transcription process
        logging.info(f"Testing X Spaces functionality with mock URL: {mock_space_url}")
        
        # Simulate audio download (would use real yt-dlp in production)
        mock_audio_path = "static/audio/mock_space_test.mp3"
        logging.info(f"Mock audio download successful: {mock_audio_path}")
        
        # Simulate transcription (would use real AssemblyAI in production)
        logging.info(f"Mock transcript generated: {mock_transcript[:100]}...")
        
        # Test our analysis functions
        topic_analysis = analyze_topic(mock_transcript)
        nuance_analysis = analyze_nuance(mock_transcript)
        
        # Take screenshot of the mock Space URL
        screenshot = take_screenshot(mock_space_url)
        screenshot_text = extract_screenshot_text(screenshot)
        
        # Add mock Space to trends
        trends.append({
            'type': 'spaces', 
            'title': 'Mock Bitcoin Discussion Space', 
            'content': mock_transcript, 
            'screenshot': screenshot,
            'screenshot_text': screenshot_text,
            'transcript_text': mock_transcript, 
            'topic': topic_analysis, 
            'nuance': nuance_analysis,
            'url': mock_space_url,
            'audio_url': mock_audio_path
        })
        
        logging.info(f"Successfully added mock X Space: Topic={topic_analysis}, Sentiment={nuance_analysis}")
        logging.info(f"Mock X Space processing completed - transcript saved and article ready for generation")
        
    except Exception as e:
        logging.error(f"Error in X Spaces testing: {e}")
    
    # Real X Spaces monitoring (commented out for testing)
    # for handle in ['CaitlinLong_', 'lopp', 'adam3us', 'woonomic', 'bitschmidty', 'LawrenceLepard', 'maxkeiser', 'jackmallers', 'TheBTCTherapist']:
    #     try:
    #         handle_id = handle
    #         spaces = x_service.client.search_spaces(user_ids=[handle_id], state='all').data or [] if hasattr(x_service, 'client') else []
    #         for space in spaces:
    #             if space.state == 'ended' and space.is_ticketed == False:
    #                 playback_url = space.playback_url
    #                 audio_path = download_audio(playback_url)
    #                 transcript = get_transcript(audio_path)
    #                 if transcript:
    #                     space_url = f"https://twitter.com/i/spaces/{space.id}"
    #                     screenshot = take_screenshot(space_url)
    #                     screenshot_text = extract_screenshot_text(screenshot)
    #                     trends.append({
    #                         'type': 'spaces', 
    #                         'title': space.title, 
    #                         'content': transcript, 
    #                         'screenshot': screenshot,
    #                         'screenshot_text': screenshot_text,
    #                         'transcript_text': transcript, 
    #                         'topic': analyze_topic(transcript), 
    #                         'nuance': analyze_nuance(transcript),
    #                         'url': space_url
    #                     })
    #     except Exception as e:
    #         logging.error(f"Error monitoring X Spaces for {handle}: {e}")
    
    # Generate articles with auto-approval (hands-off publishing)
    published_count = 0
    for trend in trends:
        if trend['type'] == 'spaces':
            prompt = f"Draft value-added recap of X Space '{trend['title']}': Overview, key points, implications for Web3/Bitcoin, speculative analysis. Embed: {trend['url']}."
        else:
            prompt = f"Write a speculative article on '{trend['title']}': Discuss implications with a sharp, provocative, investigative tone, acknowledging potential inaccuracy but exploring Web3/Bitcoin impact. Incorporate screenshot context: {trend['screenshot_text']}."
        article_data = ai.generate_content(prompt, system_prompt="You are an investigative journalist for Protocol Pulse, crafting bold, nuanced Web3 pieces.")
        article = Article(
            title=trend['title'],
            content=article_data,
            screenshot_url=trend['screenshot'],
            video_url=trend.get('video_url'),
            source_type=trend['type'],
            published=True,  # Auto-approved for hands-off publishing
            category='Web3',
            author="Al Ingle"
        )
        db.session.add(article)
        db.session.commit()  # Commit each article separately for Substack publishing
        
        # Immediately publish to Substack (hands-off workflow)
        try:
            from services.substack_service import SubstackService
            substack_service = SubstackService()
            
            # Format content for newsletter
            newsletter_content = substack_service.format_content_for_newsletter(
                article.content, 'article'
            )
            
            # Publish to Substack
            substack_url = substack_service.publish_to_substack(
                article.title,
                newsletter_content,
                article.screenshot_url  # Use screenshot as header image
            )
            
            if substack_url:
                # Update article with Substack URL
                article.substack_url = substack_url
                db.session.commit()
                published_count += 1
                logging.info(f"Auto-published social trend '{article.title}' to Substack: {substack_url}")
            else:
                logging.warning(f"Failed to auto-publish social trend '{article.title}' to Substack")
                
        except Exception as e:
            logging.error(f"Auto-publish to Substack failed for social trend '{article.title}': {e}")
    
    logging.info(f"Social monitoring completed: {len(trends)} articles generated, {published_count} published to Substack")
    
    return jsonify({'trends': trends})

def take_screenshot(url):
    try:
        chromedriver_autoinstaller.install()
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-data-dir=/tmp/chrome-profile-{uuid.uuid4().hex}')
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        screenshot_path = f'static/screenshots/{uuid.uuid4().hex}.png'
        driver.save_screenshot(screenshot_path)
        driver.quit()
        return screenshot_path
    except Exception as e:
        logging.error(f"Screenshot failed for {url}: {e}")
        # Return a mock screenshot path for testing
        mock_screenshot_path = f'static/screenshots/mock_{uuid.uuid4().hex}.png'
        logging.info(f"Using mock screenshot path: {mock_screenshot_path}")
        return mock_screenshot_path

def extract_screenshot_text(screenshot_path):
    try:
        image = Image.open(screenshot_path)
        text = pytesseract.image_to_string(image)
        return text if text.strip() else "No text detected"
    except Exception as e:
        logging.error(f"OCR error: {e}")
        return "OCR failed"

def download_audio(url):
    try:
        ydl_opts = {'outtmpl': 'static/audio/%(id)s.mp3'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        audio_path = ydl_opts['outtmpl'].replace('%(id)s', 'downloaded')  # Simplified path
        logging.info(f"Downloaded audio to: {audio_path}")
        return audio_path
    except Exception as e:
        logging.error(f"Audio download error: {e}")
        return None

def get_transcript(audio_path):
    try:
        if not audio_path:
            return "Transcript failed"
        
        assembly = assemblyai.Client(os.environ.get('ASSEMBLYAI_API_KEY'))
        transcript = assembly.transcribe(audio_path)
        
        if transcript.status == 'completed':
            logging.info(f"Transcript completed: {transcript.text[:100]}...")
            return transcript.text
        else:
            logging.error(f"Transcript failed with status: {transcript.status}")
            return "Transcript failed"
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return "Transcript failed"

def analyze_topic(transcript_text):
    try:
        # Simple keyword analysis for Web3/Bitcoin relevance
        web3_keywords = ['bitcoin', 'crypto', 'blockchain', 'defi', 'nft', 'ethereum', 'web3', 'dao', 'satoshi']
        word_count = sum(1 for word in web3_keywords if word.lower() in transcript_text.lower())
        return f"Web3 relevance score: {word_count}/10"
    except:
        return "Topic analysis failed"

def analyze_nuance(transcript_text):
    try:
        # Simple sentiment analysis based on keywords
        positive_words = ['bullish', 'optimistic', 'growth', 'adoption', 'innovation']
        negative_words = ['bearish', 'crash', 'regulation', 'scam', 'risk']
        
        positive_count = sum(1 for word in positive_words if word.lower() in transcript_text.lower())
        negative_count = sum(1 for word in negative_words if word.lower() in transcript_text.lower())
        
        if positive_count > negative_count:
            return "Positive sentiment"
        elif negative_count > positive_count:
            return "Negative sentiment"
        else:
            return "Neutral sentiment"
    except:
        return "Nuance analysis failed"

```

## Services

### services/ad_processor.py
```python
import os
import logging
from PIL import Image, ImageEnhance, ImageOps, ImageDraw

def spice_ad_image(input_path, output_path):
    """
    Transforms a standard sponsor logo into a Red/Black Cyberpunk terminal asset.
    
    This processor performs a multi-stage transformation:
    1. Desaturation - Remove original branding colors
    2. Channel Manipulation - Apply cyberpunk red tint
    3. Contrast Enhancement - Make blacks deeper and reds pop
    4. Scanline Injection - Add terminal/intel aesthetic
    5. Vignette Application - Focus on logo center
    """
    try:
        # 1. Load Image and convert to RGBA to handle transparency
        with Image.open(input_path) as img:
            # Handle different modes
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            
            width, height = img.size
            
            # 2. Create the "Cyberpunk Red" Tint
            # Convert to grayscale first to remove original colors
            grayscale = ImageOps.grayscale(img)
            
            # Apply red colorization - black stays black, white becomes red
            spiced_img = ImageOps.colorize(
                grayscale, 
                black="black", 
                white="#dc2626"  # --accent-red
            )
            spiced_img = spiced_img.convert("RGB")

            # 3. Enhance Contrast - Makes blacks deeper and reds pop
            enhancer = ImageEnhance.Contrast(spiced_img)
            spiced_img = enhancer.enhance(1.5)
            
            # Also boost brightness slightly
            brightness = ImageEnhance.Brightness(spiced_img)
            spiced_img = brightness.enhance(1.1)

            # 4. Overlay Digital Scanlines - Creates 'Intel Terminal' look
            draw = ImageDraw.Draw(spiced_img)
            for y in range(0, height, 4):  # Every 4th pixel row
                draw.line([(0, y), (width, y)], fill=(0, 0, 0, 100), width=1)

            # 5. Apply a Subtle Vignette - Darkens edges to focus on center
            # Create a radial gradient mask
            vignette = Image.new("L", spiced_img.size, 0)
            draw_v = ImageDraw.Draw(vignette)
            
            # Draw an ellipse that's larger than the image
            padding = min(width, height) // 4
            draw_v.ellipse(
                [-padding, -padding, width + padding, height + padding], 
                fill=255
            )
            
            # Apply the vignette as a blend
            # For simplicity, we'll skip the complex vignette and just save
            
            # 6. Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 7. Save the finalized asset
            spiced_img.save(output_path, "JPEG", quality=95, optimize=True)
            
            logging.info(f"Successfully spiced ad image: {output_path}")
            return True
            
    except Exception as e:
        logging.error(f"Error spicing image: {e}")
        return False


def process_sponsor_logo(original_path, sponsor_name):
    """
    Convenience function to process a sponsor logo and return the output path.
    
    Args:
        original_path: Path to the original logo file
        sponsor_name: Name of the sponsor (used for filename)
    
    Returns:
        Path to the processed image, or None if processing failed
    """
    import uuid
    
    # Generate unique filename
    safe_name = sponsor_name.lower().replace(' ', '_').replace("'", '')
    filename = f"spiced_{safe_name}_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join('static', 'ads', filename)
    
    if spice_ad_image(original_path, output_path):
        return f"/static/ads/{filename}"
    return None
```

### services/ai_service.py
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

### services/automation.py
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
```

### services/content_analyzer.py
```python
"""
Content Analysis Service for Social Media Monitoring
Analyzes monitored content and generates article drafts
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from services.ai_service import AIService
from services.gemini_service import gemini_service

class ContentAnalyzer:
    def __init__(self):
        """Initialize content analyzer with AI service"""
        self.ai_service = AIService()
        self.gemini_service = gemini_service
        
    def analyze_tweet_for_article(self, tweet_data: Dict) -> Optional[Dict]:
        """Analyze tweet content and determine if it's worthy of an article"""
        try:
            # Content relevance scoring
            relevance_prompt = f"""
            Analyze this tweet for crypto/Web3 news relevance:
            
            Tweet: {tweet_data['content']}
            Handle: {tweet_data['handle']}
            Engagement: {tweet_data['engagement']['likes']} likes, {tweet_data['engagement']['retweets']} retweets
            
            Score from 1-10 how newsworthy this is for a crypto media site.
            Consider: market impact, breaking news value, industry relevance, engagement level.
            
            Respond with just a number (1-10) and brief explanation.
            """
            
            relevance_text = self.gemini_service.generate_bitcoin_article(relevance_prompt, "analysis")
            
            # Extract score (look for number in response)
            import re
            score_match = re.search(r'(\d+)', relevance_text)
            if not score_match:
                return None
                
            relevance_score = int(score_match.group(1))
            
            # Only proceed if score is 6 or higher
            if relevance_score < 6:
                logging.info(f"Tweet scored {relevance_score}/10 - not creating article")
                return None
            
            # Generate article draft
            article_prompt = f"""
            Create a professional crypto news article based on this tweet:
            
            Tweet: {tweet_data['content']}
            Handle: {tweet_data['handle']}
            URL: {tweet_data['url']}
            
            Write a complete article with:
            1. Compelling headline
            2. TL;DR section (HTML format with tldr-section class)
            3. Full article body (HTML with proper header/paragraph classes)
            4. Market implications
            5. Source attribution
            
            Use professional journalist tone. Format as HTML with these classes:
            - tldr-section for summary
            - article-header for main headers
            - article-subheader for subheaders  
            - article-paragraph for paragraphs
            
            No raw markdown (**, ###). Only clean HTML.
            """
            
            article_response = self.gemini_service.generate_content(article_prompt)
            article_content = article_response.text.strip()
            
            # Extract title from content
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_content)
            if not title_match:
                title_match = re.search(r'headline[:\-]\s*(.+)', article_content, re.IGNORECASE)
            
            title = title_match.group(1) if title_match else f"Breaking: {tweet_data['handle']} Tweet Analysis"
            title = title.strip('"').strip("'")
            
            return {
                'title': title,
                'content': article_content,
                'source_type': 'twitter',
                'source_url': tweet_data['url'],
                'source_handle': tweet_data['handle'],
                'relevance_score': relevance_score,
                'screenshot_path': tweet_data.get('screenshot'),
                'category': 'social-media',
                'author': 'AI Social Monitor'
            }
            
        except Exception as e:
            logging.error(f"Error analyzing tweet for article: {e}")
            return None
    
    def analyze_reddit_post_for_article(self, reddit_data: Dict) -> Optional[Dict]:
        """Analyze Reddit post and generate article if newsworthy"""
        try:
            # Content relevance scoring
            relevance_prompt = f"""
            Analyze this Reddit post for crypto/Web3 news relevance:
            
            Title: {reddit_data['title']}
            Content: {reddit_data['content'][:500]}...
            Subreddit: r/{reddit_data['subreddit']}
            Score: {reddit_data['engagement']['score']} upvotes
            Comments: {reddit_data['engagement']['comments']}
            
            Score from 1-10 how newsworthy this is for a crypto media site.
            Consider: market impact, breaking news value, community discussion level.
            
            Respond with just a number (1-10) and brief explanation.
            """
            
            relevance_text = self.gemini_service.generate_bitcoin_article(relevance_prompt, "analysis")
            
            # Extract score
            import re
            score_match = re.search(r'(\d+)', relevance_text)
            if not score_match:
                return None
                
            relevance_score = int(score_match.group(1))
            
            # Only proceed if score is 7 or higher (Reddit requires higher threshold)
            if relevance_score < 7:
                logging.info(f"Reddit post scored {relevance_score}/10 - not creating article")
                return None
            
            # Generate article draft
            article_prompt = f"""
            Create a professional crypto news article based on this Reddit discussion:
            
            Title: {reddit_data['title']}
            Content: {reddit_data['content']}
            Subreddit: r/{reddit_data['subreddit']}
            Community Engagement: {reddit_data['engagement']['score']} upvotes, {reddit_data['engagement']['comments']} comments
            
            Write a complete article with:
            1. Compelling headline
            2. TL;DR section (HTML format with tldr-section class)
            3. Full article body discussing the community perspective
            4. Market implications if relevant
            5. Source attribution to Reddit community
            
            Use professional journalist tone. Format as HTML with these classes:
            - tldr-section for summary
            - article-header for main headers
            - article-subheader for subheaders  
            - article-paragraph for paragraphs
            
            No raw markdown (**, ###). Only clean HTML.
            """
            
            article_response = self.gemini_service.generate_content(article_prompt)
            article_content = article_response.text.strip()
            
            # Extract title
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_content)
            if not title_match:
                title_match = re.search(r'headline[:\-]\s*(.+)', article_content, re.IGNORECASE)
            
            title = title_match.group(1) if title_match else reddit_data['title']
            title = title.strip('"').strip("'")
            
            return {
                'title': title,
                'content': article_content,
                'source_type': 'reddit',
                'source_url': reddit_data['url'],
                'source_subreddit': reddit_data['subreddit'],
                'relevance_score': relevance_score,
                'category': 'community',
                'author': 'AI Social Monitor'
            }
            
        except Exception as e:
            logging.error(f"Error analyzing Reddit post for article: {e}")
            return None
    
    def analyze_website_content_for_article(self, website_data: Dict) -> Optional[Dict]:
        """Analyze website content and generate article if newsworthy"""
        try:
            # Extract key information from website content
            content_snippet = website_data['content'][:1000]  # First 1000 chars
            
            relevance_prompt = f"""
            Analyze this website content for crypto/Web3 news relevance:
            
            Source: {website_data['url']}
            Content Preview: {content_snippet}...
            
            Score from 1-10 how newsworthy this is for a crypto media site.
            Consider: breaking news, market impact, industry developments.
            
            Respond with just a number (1-10) and brief explanation.
            """
            
            relevance_text = self.gemini_service.generate_bitcoin_article(relevance_prompt, "analysis")
            
            # Extract score
            import re
            score_match = re.search(r'(\d+)', relevance_text)
            if not score_match:
                return None
                
            relevance_score = int(score_match.group(1))
            
            # Only proceed if score is 8 or higher (website content requires highest threshold)
            if relevance_score < 8:
                logging.info(f"Website content scored {relevance_score}/10 - not creating article")
                return None
            
            # Generate article draft
            article_prompt = f"""
            Create a professional crypto news article based on this website content:
            
            Source: {website_data['url']}
            Content: {website_data['content'][:2000]}
            
            Write a complete original article that:
            1. Has a compelling headline
            2. Includes TL;DR section (HTML format with tldr-section class)
            3. Provides original analysis and perspective
            4. Discusses market implications
            5. Properly attributes the source
            
            IMPORTANT: Do not copy content directly. Create original analysis and reporting.
            
            Use professional journalist tone. Format as HTML with these classes:
            - tldr-section for summary
            - article-header for main headers
            - article-subheader for subheaders  
            - article-paragraph for paragraphs
            
            No raw markdown (**, ###). Only clean HTML.
            """
            
            article_response = self.gemini_service.generate_content(article_prompt)
            article_content = article_response.text.strip()
            
            # Extract title
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_content)
            if not title_match:
                title_match = re.search(r'headline[:\-]\s*(.+)', article_content, re.IGNORECASE)
            
            title = title_match.group(1) if title_match else "Breaking Web3 News Update"
            title = title.strip('"').strip("'")
            
            return {
                'title': title,
                'content': article_content,
                'source_type': 'website',
                'source_url': website_data['url'],
                'relevance_score': relevance_score,
                'category': 'breaking-news',
                'author': 'AI News Monitor'
            }
            
        except Exception as e:
            logging.error(f"Error analyzing website content for article: {e}")
            return None
    
    def process_monitoring_results(self, monitoring_results: Dict) -> List[Dict]:
        """Process all monitoring results and generate article drafts"""
        article_drafts = []
        
        # Process Twitter content
        for tweet_data in monitoring_results.get('twitter', []):
            article = self.analyze_tweet_for_article(tweet_data)
            if article:
                article_drafts.append(article)
        
        # Process Reddit content
        for reddit_data in monitoring_results.get('reddit', []):
            article = self.analyze_reddit_post_for_article(reddit_data)
            if article:
                article_drafts.append(article)
        
        # Process website content
        for website_data in monitoring_results.get('websites', []):
            article = self.analyze_website_content_for_article(website_data)
            if article:
                article_drafts.append(article)
        
        logging.info(f"Generated {len(article_drafts)} article drafts from monitoring")
        return article_drafts

# Global instance
content_analyzer = ContentAnalyzer()```

### services/content_engine.py
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

### services/content_generator.py
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
        
        # Default prompts for different content types
        self.default_prompts = {
            'news_article': """
            Write a high-value article blog post about {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
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
            Write a high-value article blog post about {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            - Never include "Tags:" or similar metadata
            
            Focus on expert-level analysis with unique perspectives supporting decentralized finance and Bitcoin adoption.
            Target length: 1000-1500 words
            """,
            
            'breaking_news': """
            Write a high-value article blog post about {topic} using the following content. The article must be written in the style of Walter Cronkite without mentioning him or using first-person language, maintaining an authoritative, thoughtful, and journalistic tone. Content should be uniquely rephrased with expanded commentary and added perspectives, weaving in subtle pro-decentralization and pro-Bitcoin philosophy. The article should conclude with a strong, principled statement about financial freedom and decentralization, but it must not be labeled as a closing statement nor reference cypherpunk by name.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            - Never include "Tags:" or similar metadata
            
            Maintain urgency and accuracy while promoting decentralized financial freedom.
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
            
            # Add system prompt for consistency - New Editorial Guidelines
            system_prompt = """
            You are a world-class journalist writing for Protocol Pulse with the trust and authority 
            of Walter Cronkite but in a natural, human style that feels engaging and real. 
            
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
            
            STRUCTURE REQUIREMENT: Always format the article in two distinct sections:
            - 'The Report' (factual news reporting)
            - 'The Bitcoin Lens' (philosophical commentary and Bitcoin-focused analysis)
            
            This reinforces the separation between unbiased news and philosophical commentary. Vary 
            the narrative style to keep the writing fresh, sometimes closing with firm conviction, 
            sometimes with a reflective question, but always leaving readers more orange-pilled, 
            more educated, and more convinced of Bitcoin's unique importance to humanity.
            
            CRITICAL: OUTPUT ONLY CLEAN HTML - NO MARKDOWN SYNTAX ALLOWED.
            Use <div class="tldr-section"><em><strong>TL;DR: content</strong></em></div> for summaries.
            Use <h2 class="article-header"> for 'The Report' and 'The Bitcoin Lens' sections.
            Use <h3 class="article-subheader"> for sub-sections within each main section.
            Use <p class="article-paragraph"> for all paragraphs.
            Never use **, ***, ##, ### or any markdown syntax - only HTML tags.
            """
            
            # Generate the main content using Gemini (primary) with fallbacks
            content = None
            
            # Try Gemini first (we have API key)
            try:
                content = self.gemini_service.generate_content(formatted_prompt, system_prompt)
            except Exception as e:
                logging.warning(f"Gemini generation failed: {e}")
            
            # Fallback to OpenAI if available
            if not content:
                try:
                    content = self.ai_service.generate_content_openai(formatted_prompt, system_prompt)
                except Exception as e:
                    logging.warning(f"OpenAI generation failed: {e}")
            
            # Fallback to Anthropic if available
            if not content:
                try:
                    content = self.ai_service.generate_content_anthropic(formatted_prompt, system_prompt)
                except Exception as e:
                    logging.warning(f"Anthropic generation failed: {e}")
            
            if not content:
                raise Exception("Failed to generate content with any AI service")
            
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
            
            return {
                'title': title,
                'content': content,
                'summary': "",  # No summary - TL;DR is embedded in content
                'category': category,
                'tags': tags,
                'seo_title': seo_data.get('seo_title', title),
                'seo_description': seo_data.get('seo_description', title[:150]),
                'header_image_url': header_image_url
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
    
    def _extract_or_generate_title(self, content, topic):
        """Extract title from content or generate one"""
        try:
            # Try to extract title from the first line if it looks like a headline
            first_line = content.split('\n')[0].strip()
            if len(first_line) < 100 and len(first_line) > 10:
                # Remove common article prefixes and any "Protocol Pulse" branding
                title = first_line.replace('# ', '').replace('## ', '').strip()
                title = title.replace('Protocol Pulse News:', '').replace('Protocol Pulse:', '').strip()
                if title and not title.endswith('.'):
                    return title
            
            # Generate title using AI - explicitly forbid "Protocol Pulse" in title
            title_prompt = f"""Create a compelling, SEO-friendly headline for an article about: {topic}. 
            CRITICAL: Do NOT include 'Protocol Pulse' or any publication name in the title.
            The title should focus ONLY on the news topic itself.
            Make it under 60 characters and newsworthy."""
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

### services/elevenlabs_service.py
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

### services/gemini_service.py
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

### services/grok_service.py
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

### services/heygen_service.py
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

### services/image_service.py
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

### services/newsletter.py
```python
# SendGrid Newsletter Service - Protocol Pulse
# Using blueprint:python_sendgrid integration

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

    def send_newsletter(self, subject: str, content: str, recipients: list = None) -> bool:
        """Send newsletter to all subscribers or specific recipients"""
        if not self.enabled:
            return False
            
        try:
            if recipients is None:
                # Get all subscribed users
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

### services/node_service.py
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

### services/price_service.py
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

### services/printful_service.py
```python
import requests
import logging
from typing import List, Dict, Optional
import os

class PrintfulService:
    """Service for integrating with Printful API for merch store"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.environ.get('PRINTFUL_API_KEY')
        self.base_url = 'https://api.printful.com'
        # Printful now uses OAuth 2.0 bearer tokens (as of March 2023)
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        if not self.api_key:
            self.logger.warning("PRINTFUL_API_KEY not configured - merch functionality disabled")
    
    def get_store_products(self) -> List[Dict]:
        """Get all products from Printful store"""
        if not self.api_key:
            return []
        
        try:
            response = requests.get(
                f'{self.base_url}/store/products',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                return data.get('result', [])
            else:
                self.logger.error(f"Printful API error: {data}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching Printful products: {e}")
            return []
    
    def get_product_details(self, product_id: int) -> Optional[Dict]:
        """Get detailed information for a specific product"""
        if not self.api_key:
            return None
        
        try:
            response = requests.get(
                f'{self.base_url}/store/products/{product_id}',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                return data.get('result')
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
        
        return {
            'id': sync_product.get('id'),
            'name': sync_product.get('name', 'Product'),
            'thumbnail': sync_product.get('thumbnail_url'),
            'main_image': main_image,
            'variants': variants,
            'description': sync_product.get('description', ''),
            'tags': sync_product.get('tags', []),
            'is_ignored': sync_product.get('is_ignored', False)
        }```

### services/reddit_service.py
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

### services/rss_service.py
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

### services/scheduler.py
```python
import schedule
import time
import random
from datetime import datetime, timedelta
from app import app, db
from models import Article
from services.content_generator import ContentGenerator
import logging

generator = ContentGenerator()

# Diverse breaking news topics for automated generation
BREAKING_TOPICS = [
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
    "Bitcoin reaches new adoption milestone in emerging markets",
    "DeFi lending protocols revolutionize traditional banking models"
]

def generate_scheduled_article():
    """Generate fresh breaking news articles automatically"""
    with app.app_context():
        try:
            # Select random topic for variety
            topic = random.choice(BREAKING_TOPICS)
            
            # Generate the article with breaking news focus
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='ai_generated'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.summary = ""  # TL;DR embedded in content
                article.category = article_data.get('category', 'Bitcoin')
                article.tags = article_data.get('tags', 'bitcoin,breaking,news')
                article.author = "Al Ingle"
                article.seo_title = article_data.get('seo_title', article_data['title'])
                article.seo_description = article_data.get('seo_description', article_data['title'][:150])
                article.header_image_url = article_data.get('header_image_url')
                article.published = True  # Auto-publish breaking news
                article.featured = True   # Mark as featured for homepage visibility
                db.session.add(article)
                db.session.commit()
                
                logging.info(f"✅ Auto-generated breaking news: {article.title}")
                
                # Immediately publish to Substack (hands-off workflow)
                try:
                    from services.substack_service import SubstackService
                    substack_service = SubstackService()
                    
                    # Format content for newsletter
                    newsletter_content = substack_service.format_content_for_newsletter(
                        article.content, 'bitcoin'
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
                        logging.info(f"🚀 Auto-published to Substack: {substack_url}")
                    else:
                        logging.warning(f"⚠️ Failed to auto-publish '{article.title}' to Substack")
                        
                except Exception as e:
                    logging.error(f"❌ Auto-publish to Substack failed: {e}")
                
                # Archive older articles to keep homepage fresh
                archive_old_articles()
                
            else:
                logging.error("❌ Failed to generate scheduled article content")
                
        except Exception as e:
            logging.error(f"❌ Error in scheduled article generation: {str(e)}")

def archive_old_articles():
    """Archive articles older than 7 days to keep homepage fresh"""
    with app.app_context():
        try:
            # Find articles older than 7 days that are still featured
            archive_date = datetime.utcnow() - timedelta(days=7)
            old_featured = Article.query.filter(
                Article.featured == True,
                Article.created_at < archive_date
            ).all()
            
            archived_count = 0
            for article in old_featured:
                article.featured = False  # Remove from featured to archive
                archived_count += 1
            
            if archived_count > 0:
                db.session.commit()
                logging.info(f"📁 Archived {archived_count} older featured articles")
                
        except Exception as e:
            logging.error(f"❌ Error archiving articles: {str(e)}")

def maintain_featured_count():
    """Ensure we always have 3-6 featured articles on homepage"""
    with app.app_context():
        try:
            featured_count = Article.query.filter_by(published=True, featured=True).count()
            
            # If we have too few featured articles, promote recent ones
            if featured_count < 3:
                recent_articles = Article.query.filter_by(
                    published=True, 
                    featured=False
                ).order_by(Article.created_at.desc()).limit(3 - featured_count).all()
                
                for article in recent_articles:
                    article.featured = True
                
                if recent_articles:
                    db.session.commit()
                    logging.info(f"📈 Promoted {len(recent_articles)} articles to featured")
                    
        except Exception as e:
            logging.error(f"❌ Error maintaining featured count: {str(e)}")

def run_social_monitoring():
    """Run automated social media monitoring"""
    with app.app_context():
        try:
            from services.reddit_service import RedditService
            from services.x_service import XService
            from services.youtube_service import YouTubeService
            from services.ai_service import AIService
            
            reddit = RedditService()
            x_service = XService()
            youtube = YouTubeService()
            ai = AIService()
            trends = []
            
            # Monitor X handles for new posts
            x_handles = ['CaitlinLong_', 'lopp', 'adam3us', 'woonomic', 'bitschmidty', 'LawrenceLepard', 'maxkeiser', 'jackmallers', 'TheBTCTherapist']
            for handle in x_handles:
                tweets = x_service.get_feedback(handle)
                for tweet in tweets:
                    from routes_social import take_screenshot, extract_screenshot_text
                    screenshot = take_screenshot(f"https://x.com/{handle}/status/{tweet['id']}")
                    screenshot_text = extract_screenshot_text(screenshot)
                    trends.append({
                        'type': 'x', 
                        'title': tweet['text'], 
                        'content': tweet['text'], 
                        'screenshot': screenshot, 
                        'screenshot_text': screenshot_text, 
                        'topic': tweet['topic'], 
                        'nuance': tweet['nuance'],
                        'source_url': f"https://x.com/{handle}/status/{tweet['id']}"
                    })
            
            # Monitor YouTube channels for new videos
            videos = youtube.get_recent_videos()
            for video in videos:
                from routes_social import take_screenshot, extract_screenshot_text
                screenshot = take_screenshot(f"https://www.youtube.com/watch?v={video['id']}")
                screenshot_text = extract_screenshot_text(screenshot)
                trends.append({
                    'type': 'youtube', 
                    'title': video['title'], 
                    'content': video['transcript'], 
                    'screenshot': screenshot, 
                    'screenshot_text': screenshot_text, 
                    'video_url': f"https://www.youtube.com/embed/{video['id']}", 
                    'topic': video['topic'], 
                    'nuance': video['nuance'],
                    'source_url': f"https://www.youtube.com/watch?v={video['id']}"
                })
            
            # Generate articles with auto-approval and immediate Substack publishing
            published_count = 0
            for trend in trends:
                prompt = f"Write a speculative article on '{trend['title']}': Discuss implications with a sharp, provocative, investigative tone, acknowledging potential inaccuracy but exploring Web3/Bitcoin impact. Incorporate screenshot context: {trend['screenshot_text']}."
                article_data = ai.generate_content_openai(prompt, system_prompt="You are an investigative journalist for Protocol Pulse, crafting bold, nuanced Web3 pieces.")
                
                # Create hyperlinked content that opens in new window
                content_with_link = f'<p><a href="{trend["source_url"]}" target="_blank" rel="noopener">🔗 View Original Post</a></p>\n{article_data}'
                
                article = Article()
                article.title = trend['title']
                article.content = content_with_link
                article.screenshot_url = trend['screenshot']
                article.video_url = trend.get('video_url')
                article.source_type = trend['type']
                article.source_url = trend['source_url']
                article.published = True  # Auto-approved
                article.category = 'Web3'
                article.author = "Al Ingle"
                article.featured = False  # Social content not auto-featured
                db.session.add(article)
                db.session.commit()
                
                # Auto-publish to Substack
                try:
                    from services.substack_service import SubstackService
                    substack_service = SubstackService()
                    newsletter_content = substack_service.format_content_for_newsletter(article.content, 'article')
                    substack_url = substack_service.publish_to_substack(article.title, newsletter_content, article.screenshot_url)
                    
                    if substack_url:
                        article.substack_url = substack_url
                        db.session.commit()
                        published_count += 1
                        logging.info(f"🚀 Auto-published social trend '{article.title}' to Substack: {substack_url}")
                except Exception as e:
                    logging.error(f"❌ Substack publishing failed for '{article.title}': {e}")
            
            logging.info(f"📱 Social monitoring completed: {len(trends)} trends found, {published_count} published to Substack")
            
        except Exception as e:
            logging.error(f"❌ Social monitoring error: {str(e)}")

# Schedule automated content generation
schedule.every(15).minutes.do(generate_scheduled_article)  # Generate breaking news every 15 minutes for testing
schedule.every(2).hours.do(run_social_monitoring)        # Monitor X/YouTube every 2 hours
schedule.every(6).hours.do(maintain_featured_count)     # Maintain homepage freshness
schedule.every(1).days.do(archive_old_articles)        # Daily archiving

def run_scheduler():
    """Main scheduler loop for automated content generation"""
    logging.info("🚀 Protocol Pulse Content Scheduler Started")
    logging.info("📰 Breaking news generation: Every 15 minutes")
    logging.info("📱 Social monitoring (X/YouTube): Every 2 hours")
    logging.info("📁 Article archiving: Daily")
    logging.info("🔄 Homepage maintenance: Every 6 hours")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("⏹️  Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Scheduler error: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == '__main__':
    run_scheduler()```

### services/simple_content_analyzer.py
```python
"""
Simplified Content Analysis Service for Social Media Monitoring
Uses existing AI services correctly for content analysis
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from services.ai_service import AIService

class SimpleContentAnalyzer:
    def __init__(self):
        """Initialize content analyzer with working AI service"""
        self.ai_service = AIService()
        
    def analyze_social_content(self, content_data: Dict, content_type: str) -> Optional[Dict]:
        """Analyze social media content and create article if newsworthy"""
        try:
            # Use OpenAI/Anthropic for analysis since they work reliably
            if content_type == 'twitter':
                return self._analyze_twitter_content(content_data)
            elif content_type == 'reddit':
                return self._analyze_reddit_content(content_data)
            elif content_type == 'website':
                return self._analyze_website_content(content_data)
            else:
                return None
                
        except Exception as e:
            logging.error(f"Error analyzing {content_type} content: {e}")
            return None
    
    def _analyze_twitter_content(self, tweet_data: Dict) -> Optional[Dict]:
        """Analyze Twitter content"""
        try:
            # Simple relevance check
            content = tweet_data.get('content', '')
            handle = tweet_data.get('handle', '')
            engagement = tweet_data.get('engagement', {})
            
            # Basic filtering - high engagement or crypto keywords
            crypto_keywords = ['bitcoin', 'btc', 'ethereum', 'eth', 'defi', 'crypto', 'blockchain', 'web3']
            has_crypto_keywords = any(keyword in content.lower() for keyword in crypto_keywords)
            high_engagement = engagement.get('likes', 0) > 100 or engagement.get('retweets', 0) > 50
            
            if not (has_crypto_keywords or high_engagement):
                return None
            
            # Create article content
            title = f"Twitter Update: {handle} Shares Crypto Insights"
            article_content = f"""
            <div class="tldr-section">
                <strong>TL;DR:</strong> {handle} shared important crypto insights on Twitter with {engagement.get('likes', 0)} likes and {engagement.get('retweets', 0)} retweets.
            </div>
            
            <div class="article-paragraph">
                <strong>Tweet Content:</strong><br>
                {content}
            </div>
            
            <div class="article-paragraph">
                <strong>Community Engagement:</strong><br>
                This tweet received {engagement.get('likes', 0)} likes, {engagement.get('retweets', 0)} retweets, and {engagement.get('replies', 0)} replies, indicating strong community interest.
            </div>
            
            <div class="article-paragraph">
                <strong>Source:</strong> <a href="{tweet_data.get('url', '#')}" target="_blank">View Original Tweet</a>
            </div>
            """
            
            return {
                'title': title,
                'content': article_content,
                'source_type': 'twitter',
                'source_url': tweet_data.get('url'),
                'source_handle': handle,
                'category': 'social-media',
                'author': 'AI Social Monitor',
                'screenshot_path': tweet_data.get('screenshot')
            }
            
        except Exception as e:
            logging.error(f"Error analyzing Twitter content: {e}")
            return None
    
    def _analyze_reddit_content(self, reddit_data: Dict) -> Optional[Dict]:
        """Analyze Reddit content"""
        try:
            title = reddit_data.get('title', '')
            content = reddit_data.get('content', '')
            subreddit = reddit_data.get('subreddit', '')
            engagement = reddit_data.get('engagement', {})
            
            # Basic filtering - good engagement score
            score = engagement.get('score', 0)
            comments = engagement.get('comments', 0)
            
            if score < 50 and comments < 10:
                return None
            
            # Create article content
            article_title = f"Reddit Discussion: {title[:60]}{'...' if len(title) > 60 else ''}"
            article_content = f"""
            <div class="tldr-section">
                <strong>TL;DR:</strong> Active discussion on r/{subreddit} gaining significant community attention with {score} upvotes and {comments} comments.
            </div>
            
            <div class="article-paragraph">
                <strong>Discussion Title:</strong><br>
                {title}
            </div>
            
            <div class="article-paragraph">
                <strong>Community Post:</strong><br>
                {content[:500]}{'...' if len(content) > 500 else ''}
            </div>
            
            <div class="article-paragraph">
                <strong>Community Response:</strong><br>
                This discussion has received {score} upvotes and sparked {comments} comments, showing strong community engagement.
            </div>
            
            <div class="article-paragraph">
                <strong>Source:</strong> <a href="{reddit_data.get('url', '#')}" target="_blank">View Original Discussion</a>
            </div>
            """
            
            return {
                'title': article_title,
                'content': article_content,
                'source_type': 'reddit',
                'source_url': reddit_data.get('url'),
                'source_subreddit': subreddit,
                'category': 'community',
                'author': 'AI Social Monitor'
            }
            
        except Exception as e:
            logging.error(f"Error analyzing Reddit content: {e}")
            return None
    
    def _analyze_website_content(self, website_data: Dict) -> Optional[Dict]:
        """Analyze website content"""
        try:
            url = website_data.get('url', '')
            content = website_data.get('content', '')
            
            # Basic filtering - has substantial content
            if len(content) < 200:
                return None
            
            # Extract potential title from content
            content_lines = content.split('\n')
            potential_title = content_lines[0] if content_lines else "Breaking News Update"
            
            # Create article content
            article_title = f"Industry Update: {potential_title[:60]}{'...' if len(potential_title) > 60 else ''}"
            article_content = f"""
            <div class="tldr-section">
                <strong>TL;DR:</strong> Important update detected from industry news source with potential market implications.
            </div>
            
            <div class="article-paragraph">
                <strong>Source:</strong> <a href="{url}" target="_blank">{url}</a>
            </div>
            
            <div class="article-paragraph">
                <strong>Content Summary:</strong><br>
                {content[:1000]}{'...' if len(content) > 1000 else ''}
            </div>
            
            <div class="article-paragraph">
                <strong>Analysis:</strong><br>
                This content was automatically detected as potentially newsworthy based on source credibility and content analysis.
            </div>
            """
            
            return {
                'title': article_title,
                'content': article_content,
                'source_type': 'website',
                'source_url': url,
                'category': 'breaking-news',
                'author': 'AI News Monitor'
            }
            
        except Exception as e:
            logging.error(f"Error analyzing website content: {e}")
            return None

# Global instance
simple_content_analyzer = SimpleContentAnalyzer()```

### services/social_monitor.py
```python
"""
Social Media & Website Monitoring Service
Monitors Twitter handles, Reddit threads, and websites like CoinDesk
"""
import os
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import tweepy
import praw
import trafilatura
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
from io import BytesIO
from PIL import Image

class SocialMonitor:
    def __init__(self):
        """Initialize social media monitoring service"""
        self.setup_twitter()
        self.setup_reddit()
        self.setup_selenium()
        self.monitored_handles = []
        self.monitored_threads = []
        self.monitored_websites = []
        
    def setup_twitter(self):
        """Initialize Twitter API connection"""
        try:
            # Using existing Twitter/X API credentials from environment
            auth = tweepy.OAuthHandler(
                os.getenv('TWITTER_API_KEY'),
                os.getenv('TWITTER_API_SECRET')
            )
            auth.set_access_token(
                os.getenv('TWITTER_ACCESS_TOKEN'),
                os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            self.twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
            logging.info("Twitter API initialized successfully")
        except Exception as e:
            logging.warning(f"Twitter API setup failed: {e}")
            self.twitter_api = None
    
    def setup_reddit(self):
        """Initialize Reddit API connection"""
        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT')
            )
            logging.info("Reddit API initialized successfully")
        except Exception as e:
            logging.warning(f"Reddit API setup failed: {e}")
            self.reddit = None
    
    def setup_selenium(self):
        """Initialize Selenium for screenshot capabilities"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1200,800')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logging.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logging.warning(f"Selenium setup failed: {e}")
            self.driver = None
    
    def add_twitter_handle(self, handle: str, keywords: Optional[List[str]] = None):
        """Add Twitter handle to monitoring list"""
        if not handle.startswith('@'):
            handle = f'@{handle}'
        
        monitor_config = {
            'handle': handle,
            'keywords': keywords or [],
            'last_checked': datetime.utcnow(),
            'active': True
        }
        self.monitored_handles.append(monitor_config)
        logging.info(f"Added Twitter handle {handle} to monitoring")
        return monitor_config
    
    def add_reddit_thread(self, subreddit: str, thread_keywords: Optional[List[str]] = None):
        """Add Reddit subreddit/thread to monitoring list"""
        monitor_config = {
            'subreddit': subreddit,
            'keywords': thread_keywords or [],
            'last_checked': datetime.utcnow(),
            'active': True
        }
        self.monitored_threads.append(monitor_config)
        logging.info(f"Added Reddit subreddit r/{subreddit} to monitoring")
        return monitor_config
    
    def add_website(self, url: str, keywords: Optional[List[str]] = None):
        """Add website to monitoring list"""
        monitor_config = {
            'url': url,
            'keywords': keywords or [],
            'last_checked': datetime.utcnow(),
            'active': True,
            'last_content_hash': None
        }
        self.monitored_websites.append(monitor_config)
        logging.info(f"Added website {url} to monitoring")
        return monitor_config
    
    def take_tweet_screenshot(self, tweet_url: str) -> Optional[str]:
        """Take screenshot of a tweet and return base64 encoded image"""
        if not self.driver:
            logging.error("Selenium driver not available for screenshots")
            return None
        
        try:
            # Navigate to tweet
            self.driver.get(tweet_url)
            time.sleep(3)  # Wait for content to load
            
            # Find the tweet container
            tweet_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
            )
            
            # Take screenshot of the tweet element
            screenshot = tweet_element.screenshot_as_png
            
            # Convert to base64 for storage
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            
            # Save screenshot to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_filename = f"tweet_screenshot_{timestamp}.png"
            screenshot_path = f"/tmp/{screenshot_filename}"
            
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot)
            
            logging.info(f"Tweet screenshot saved: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logging.error(f"Failed to take tweet screenshot: {e}")
            return None
    
    def monitor_twitter_handles(self) -> List[Dict]:
        """Monitor configured Twitter handles for new tweets"""
        if not self.twitter_api:
            return []
        
        new_content = []
        
        for handle_config in self.monitored_handles:
            if not handle_config['active']:
                continue
                
            try:
                handle = handle_config['handle'].replace('@', '')
                tweets = self.twitter_api.user_timeline(
                    screen_name=handle,
                    count=10,
                    tweet_mode='extended',
                    since_id=None
                )
                
                for tweet in tweets:
                    # Check if tweet is recent (within last hour)
                    tweet_time = tweet.created_at
                    if tweet_time > handle_config['last_checked']:
                        
                        # Take screenshot
                        tweet_url = f"https://twitter.com/{handle}/status/{tweet.id}"
                        screenshot_path = self.take_tweet_screenshot(tweet_url)
                        
                        new_content.append({
                            'type': 'twitter',
                            'handle': handle_config['handle'],
                            'content': tweet.full_text,
                            'url': tweet_url,
                            'timestamp': tweet_time,
                            'screenshot': screenshot_path,
                            'engagement': {
                                'likes': tweet.favorite_count,
                                'retweets': tweet.retweet_count,
                                'replies': tweet.reply_count
                            }
                        })
                
                # Update last checked time
                handle_config['last_checked'] = datetime.utcnow()
                
            except Exception as e:
                logging.error(f"Error monitoring Twitter handle {handle_config['handle']}: {e}")
        
        return new_content
    
    def monitor_reddit_threads(self) -> List[Dict]:
        """Monitor configured Reddit subreddits for new content"""
        if not self.reddit:
            return []
        
        new_content = []
        
        for thread_config in self.monitored_threads:
            if not thread_config['active']:
                continue
                
            try:
                subreddit = self.reddit.subreddit(thread_config['subreddit'])
                
                # Get hot posts from last 24 hours
                for submission in subreddit.hot(limit=20):
                    post_time = datetime.fromtimestamp(submission.created_utc)
                    
                    if post_time > thread_config['last_checked']:
                        # Check if post contains relevant keywords
                        content_text = f"{submission.title} {submission.selftext}".lower()
                        keywords = thread_config['keywords']
                        
                        if not keywords or any(keyword.lower() in content_text for keyword in keywords):
                            new_content.append({
                                'type': 'reddit',
                                'subreddit': thread_config['subreddit'],
                                'title': submission.title,
                                'content': submission.selftext,
                                'url': f"https://reddit.com{submission.permalink}",
                                'timestamp': post_time,
                                'engagement': {
                                    'score': submission.score,
                                    'comments': submission.num_comments,
                                    'upvote_ratio': submission.upvote_ratio
                                }
                            })
                
                # Update last checked time
                thread_config['last_checked'] = datetime.utcnow()
                
            except Exception as e:
                logging.error(f"Error monitoring Reddit subreddit {thread_config['subreddit']}: {e}")
        
        return new_content
    
    def monitor_websites(self) -> List[Dict]:
        """Monitor configured websites for new content"""
        new_content = []
        
        for website_config in self.monitored_websites:
            if not website_config['active']:
                continue
                
            try:
                # Extract content using trafilatura
                downloaded = trafilatura.fetch_url(website_config['url'])
                if not downloaded:
                    continue
                    
                text_content = trafilatura.extract(downloaded)
                if not text_content:
                    continue
                
                # Create content hash to detect changes
                import hashlib
                content_hash = hashlib.md5(text_content.encode()).hexdigest()
                
                # Check if content has changed
                if website_config['last_content_hash'] != content_hash:
                    new_content.append({
                        'type': 'website',
                        'url': website_config['url'],
                        'content': text_content,
                        'timestamp': datetime.utcnow(),
                        'content_hash': content_hash
                    })
                    
                    # Update last content hash
                    website_config['last_content_hash'] = content_hash
                
                # Update last checked time
                website_config['last_checked'] = datetime.utcnow()
                
            except Exception as e:
                logging.error(f"Error monitoring website {website_config['url']}: {e}")
        
        return new_content
    
    def run_monitoring_cycle(self) -> Dict:
        """Run complete monitoring cycle and return all new content"""
        logging.info("Starting social media monitoring cycle")
        
        results = {
            'twitter': self.monitor_twitter_handles(),
            'reddit': self.monitor_reddit_threads(),
            'websites': self.monitor_websites(),
            'timestamp': datetime.utcnow()
        }
        
        total_items = len(results['twitter']) + len(results['reddit']) + len(results['websites'])
        logging.info(f"Monitoring cycle complete. Found {total_items} new items")
        
        return results
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring configuration and status"""
        return {
            'twitter_handles': len(self.monitored_handles),
            'reddit_threads': len(self.monitored_threads),
            'websites': len(self.monitored_websites),
            'handles': [h['handle'] for h in self.monitored_handles if h['active']],
            'subreddits': [t['subreddit'] for t in self.monitored_threads if t['active']],
            'website_urls': [w['url'] for w in self.monitored_websites if w['active']]
        }
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

# Global instance
social_monitor = SocialMonitor()```

### services/spaces_service.py
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

### services/substack_service.py
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

### services/x_service.py
```python
import tweepy
import os
import logging
import json
from openai import OpenAI

class XService:
    def __init__(self):
        # Use OAuth instead of Bearer Token
        try:
            if all([os.environ.get('TWITTER_API_KEY'), 
                    os.environ.get('TWITTER_API_SECRET'),
                    os.environ.get('TWITTER_ACCESS_TOKEN'),
                    os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')]):
                auth = tweepy.OAuthHandler(
                    os.environ.get('TWITTER_API_KEY'),
                    os.environ.get('TWITTER_API_SECRET')
                )
                auth.set_access_token(
                    os.environ.get('TWITTER_ACCESS_TOKEN'),
                    os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
                )
                self.client = tweepy.API(auth, wait_on_rate_limit=True)
                logging.info("Twitter API initialized successfully")
            else:
                self.client = None
                logging.warning("Twitter API credentials incomplete")
        except Exception as e:
            logging.error(f"Twitter API setup failed: {e}")
            self.client = None
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY')) if os.environ.get('OPENAI_API_KEY') else None
        
    def get_feedback(self, handle):
        if not self.client:
            return [{'id': 'mock_id', 'text': f'Mock tweet from @{handle}', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
        try:
            tweets = self.client.search_recent_tweets(query=f'from:{handle} -is:retweet', max_results=10, expansions='referenced_tweets.id').data or []
            filtered = []
            for tweet in tweets:
                if not hasattr(tweet, 'referenced_tweets') or not tweet.referenced_tweets:  # Native only
                    relevance = self._is_relevant(tweet.text)
                    if relevance['is_relevant']:
                        filtered.append({'id': tweet.id, 'text': tweet.text, 'is_relevant': True, 'topic': relevance['topic'], 'nuance': relevance['nuance']})
            return filtered
        except Exception as e:
            logging.error(f"X API error: {e}")
            return [{'id': 'mock_id', 'text': f'Mock tweet from @{handle}', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
    
    def _is_relevant(self, text):
        if not self.openai_client:
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
        if len(text.split()) < 10 or any(m in text.lower() for m in ['lol', '😂', 'meme']):
            return {'is_relevant': False}
        try:
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': f"Analyze tweet: '{text}'. Is it relevant to Web3/Bitcoin/DeFi? If yes, extract topic (e.g., 'Bitcoin ETF') and nuance (e.g., 'bullish'). Return JSON: {{'is_relevant': bool, 'topic': str, 'nuance': str}}"}],
                max_tokens=100
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Relevance analysis error: {e}")
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}

    def post_article_tweet(self, article, base_url=''):
        """Post a tweet about a published article"""
        if not self.client:
            logging.warning("Twitter API not configured - skipping tweet")
            return None
        
        try:
            # Generate 280-char snippet + link
            title = article.title[:100] if len(article.title) > 100 else article.title
            article_url = f"{base_url}/articles/{article.id}" if base_url else f"/articles/{article.id}"
            
            # Create tweet text (max 280 chars)
            hashtags = "#Bitcoin #BTC"
            if hasattr(article, 'category'):
                if 'DeFi' in article.category:
                    hashtags = "#Bitcoin #DeFi"
                elif 'Lightning' in str(article.tags or ''):
                    hashtags = "#Bitcoin #Lightning"
            
            tweet_text = f"{title}\n\n{article_url}\n\n{hashtags}"
            
            # Truncate if too long
            if len(tweet_text) > 280:
                max_title_len = 280 - len(article_url) - len(hashtags) - 10
                title = title[:max_title_len] + "..."
                tweet_text = f"{title}\n\n{article_url}\n\n{hashtags}"
            
            # Post the tweet
            response = self.client.update_status(tweet_text)
            logging.info(f"Tweet posted: {response.id}")
            return response.id
            
        except Exception as e:
            logging.error(f"Failed to post tweet: {e}")
            return None

# Backward compatibility functions
def get_social_feedback(topic):
    """Get social feedback for backward compatibility"""
    return {
        'sentiment': 'neutral',
        'sentiment_score': 0.5,
        'key_insights': [f"Mock insight about {topic}", "Community discussion ongoing", "Market watching closely"],
        'source': 'stubbed_data'
    }```

### services/youtube_service.py
```python
import os
import re
import json
import logging
import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

class YouTubeService:
    # Podcast Series YouTube Configuration
    # Map show IDs to their YouTube playlist/video data
    # TO UPDATE: Replace video IDs below with actual YouTube video IDs from your channel
    # Format: Go to any YouTube video URL like youtube.com/watch?v=XXXXXXXXXXX
    # The 11-character code after "v=" is the video ID
    SERIES_CONFIG = {
        'cypherpunkd': {
            'title': "Cypherpunk'd // Intel Briefing",
            'channel': 'Protocol Pulse',
            'host': 'Matty Ice',
            'description': 'Deep dives into privacy, cryptography, and financial sovereignty. Raw interviews with thought leaders, Bitcoiners, and digital freedom fighters.',
            'playlist': [
                {'id': 'QX3M8Ka9vUA', 'title': 'Adam Back: From Cypherpunk to Bitcoin Treasury'},
                {'id': 'k0BWlvnBmIE', 'title': 'The Big Print: Decentralization Episode'},
                {'id': 'ERJ3NCqTTqg', 'title': 'Why Hyperinflation Makes Bitcoin Inevitable'}
            ],
            'latest_id': 'QX3M8Ka9vUA'
        },
        'protocol_pulse': {
            'title': 'Protocol Pulse // Analysis',
            'channel': 'Protocol Pulse Network',
            'host': 'Protocol Pulse Team',
            'description': 'Where Bitcoin leaders speak truth. Unfiltered conversations from major conferences and exclusive interviews with pioneers.',
            'playlist': [
                {'id': 'F9D7yL8C_W8', 'title': 'Bitcoin 2025 Conference Highlights'},
                {'id': 'GtDMBqLVrpE', 'title': 'The Case for Sound Money'}
            ],
            'latest_id': 'F9D7yL8C_W8'
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
    
    @classmethod
    def get_series_data(cls, show_id: str) -> dict:
        """Get YouTube series data for a podcast show"""
        return cls.SERIES_CONFIG.get(show_id, {})
    
    @classmethod
    def get_all_series(cls) -> dict:
        """Get all configured series data"""
        return cls.SERIES_CONFIG

    def __init__(self):
        self.youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=os.environ.get('YOUTUBE_API_KEY')) if os.environ.get('YOUTUBE_API_KEY') else None
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY')) if os.environ.get('OPENAI_API_KEY') else None
        self.handles = ['BitcoinMagazine', 'nataliebrunell', 'bytefederal', 'BTCSessions', 'SimplyBitcoin', 'CoinBureau', 'thejackmallersshow', 'RobertBreedlove22']

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
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}```

## Templates

### templates/404.html
```html
<h1>404 Not Found</h1>```

### templates/500.html
```html
<h1>500 Error</h1>```

### templates/about.html
```html
{% extends "base.html" %}

{% block title %}About Us - Protocol Pulse{% endblock %}

{% block content %}
<section class="py-5">
    <div class="container">
        <!-- Hero Section -->
        <div class="row mb-5">
            <div class="col-12 text-center">
                <h1 class="display-4 fw-bold mb-4">
                    About <span class="text-primary">Protocol Pulse</span>
                </h1>
                <p class="lead text-muted">Your trusted source for Bitcoin and DeFi news, delivering timely insights and expert analysis</p>
            </div>
        </div>

        <!-- Mission Section -->
        <div class="row mb-5">
            <div class="col-lg-6 mb-4">
                <div class="card bg-secondary border-0 h-100">
                    <div class="card-body p-4">
                        <div class="text-center mb-4">
                            <i class="fas fa-target text-primary fa-3x"></i>
                        </div>
                        <h3 class="text-center mb-3">Our Mission</h3>
                        <p class="text-muted text-center">
                            To democratize access to high-quality Bitcoin journalism, delivering timely, 
                            accurate, and insightful coverage of the Bitcoin and DeFi ecosystem.
                        </p>
                    </div>
                </div>
            </div>
            <div class="col-lg-6 mb-4">
                <div class="card bg-secondary border-0 h-100">
                    <div class="card-body p-4">
                        <div class="text-center mb-4">
                            <i class="fas fa-eye text-primary fa-3x"></i>
                        </div>
                        <h3 class="text-center mb-3">Our Vision</h3>
                        <p class="text-muted text-center">
                            To become the leading media network in the Bitcoin space, combining cutting-edge 
                            insights with expert analysis to help our readers navigate the future of finance.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Our Approach -->
        <div class="row mb-5">
            <div class="col-12">
                <h2 class="text-center mb-5">Our Approach</h2>
                <div class="row g-4">
                    <div class="col-md-3 col-sm-6">
                        <div class="card bg-secondary border-0 text-center p-3">
                            <i class="fab fa-bitcoin text-primary fa-2x mb-3"></i>
                            <h6>Bitcoin-First Focus</h6>
                            <small class="text-muted">Dedicated coverage</small>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="card bg-secondary border-0 text-center p-3">
                            <i class="fas fa-search text-primary fa-2x mb-3"></i>
                            <h6>Deep Research</h6>
                            <small class="text-muted">Thorough analysis</small>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="card bg-secondary border-0 text-center p-3">
                            <i class="fas fa-bolt text-primary fa-2x mb-3"></i>
                            <h6>Breaking News</h6>
                            <small class="text-muted">Real-time updates</small>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="card bg-secondary border-0 text-center p-3">
                            <i class="fas fa-clock text-primary fa-2x mb-3"></i>
                            <h6>24/7 Coverage</h6>
                            <small class="text-muted">Always on</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Contact CTA -->
        <div class="row">
            <div class="col-12 text-center">
                <div class="card bg-primary text-white">
                    <div class="card-body p-5">
                        <h2 class="mb-3">Stay Connected</h2>
                        <p class="mb-4">Join our community for the latest Bitcoin and DeFi insights.</p>
                        <a href="{{ url_for('contact') }}" class="btn btn-light btn-lg">
                            <i class="fas fa-envelope me-2"></i>Contact Us
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}```

### templates/article_detail.html
```html
{% extends "base.html" %}

{% block title %}{{ article.title }} - Protocol Pulse{% endblock %}

{% block meta_description %}{{ article.summary if article.summary else article.content[:150] }}{% endblock %}

{% block head %}
<!-- Open Graph meta tags for social media sharing -->
<meta property="og:title" content="{{ article.title }}">
<meta property="og:description" content="{{ article.content[:200] }}...">
<meta property="og:image" content="{{ article.header_image_url or url_for('static', filename='images/protocol-pulse-og.png') }}">
<meta property="og:url" content="{{ request.url }}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Protocol Pulse">

<!-- Twitter Card meta tags -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@protocolpulse">
<meta name="twitter:title" content="{{ article.title }}">
<meta name="twitter:description" content="{{ article.content[:200] }}...">
<meta name="twitter:image" content="{{ article.header_image_url or url_for('static', filename='images/protocol-pulse-og.png') }}">

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
</script>
{% endblock %}```

### templates/articles.html
```html
{% extends "base.html" %}

{% block title %}Latest Intelligence - Protocol Pulse{% endblock %}

{% block head %}
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700;800&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    :root {
        --btc-gold: #f7931a;
        --btc-gold-glow: rgba(247, 147, 26, 0.25);
        --dark-bg: #050505;
        --card-bg: #0a0a0a;
        --card-hover: #0f0f0f;
        --text-main: #f5f5f5;
        --text-muted: #707070;
        --border-dim: rgba(220, 38, 38, 0.1);
        --accent-red: #dc2626;
        --accent-red-glow: rgba(220, 38, 38, 0.25);
    }

    body { 
        background-color: var(--dark-bg); 
        color: var(--text-main);
    }

    #news-pulse-container {
        background: 
            linear-gradient(180deg, rgba(10, 10, 10, 0.98) 0%, rgba(5, 5, 5, 1) 100%),
            url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIj48cGF0aCBkPSJNMCAwaDYwdjYwSDBWeiIvPjxwYXRoIGQ9Ik0wIDYwaDYwIiBzdHJva2U9InJnYmEoMjIwLDM4LDM4LDAuMDMpIiBzdHJva2Utd2lkdGg9IjEiLz48cGF0aCBkPSJNNjAgMHY2MCIgc3Ryb2tlPSJyZ2JhKDIyMCwzOCwzOCwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9nPjwvc3ZnPg==');
        background-attachment: fixed;
        position: relative;
        min-height: 100vh;
        padding-bottom: 4rem;
    }

    #news-pulse-container::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 0, 0, 0.03) 2px,
            rgba(0, 0, 0, 0.03) 4px
        );
        pointer-events: none;
        z-index: 1;
    }

    #news-pulse-container::after {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--accent-red), transparent);
        box-shadow: 0 0 30px var(--accent-red);
        animation: scanline 12s linear infinite;
        pointer-events: none;
        z-index: 10;
    }

    @keyframes scanline {
        0% { top: 0; opacity: 0.6; }
        50% { opacity: 1; }
        100% { top: 100%; opacity: 0.6; }
    }

    .content-layer {
        position: relative;
        z-index: 2;
    }

    .zone-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.3em;
        color: var(--accent-red);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .zone-label::before {
        content: '';
        width: 6px;
        height: 6px;
        background: var(--accent-red);
        border-radius: 50%;
        animation: pulse-dot 2s infinite;
        box-shadow: 0 0 12px var(--accent-red);
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    .timestamp {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: var(--accent-red);
        font-weight: 500;
        letter-spacing: 0.05em;
    }

    .page-title {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 3rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        line-height: 1;
    }

    .section-header {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 1.25rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border-dim);
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .section-header i {
        color: var(--accent-red);
        font-size: 0.9rem;
    }

    .bento-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }

    @media (max-width: 992px) {
        .bento-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .bento-hero-card {
            grid-column: span 2 !important;
            grid-row: span 1 !important;
        }
    }

    @media (max-width: 576px) {
        .bento-grid {
            grid-template-columns: 1fr;
        }
        .bento-hero-card {
            grid-column: span 1 !important;
        }
    }

    .bento-card {
        background: var(--card-bg);
        border: 1px solid var(--border-dim);
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .bento-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--accent-red), transparent);
        opacity: 0;
        transition: opacity 0.35s ease;
    }

    .bento-card:hover {
        border-color: var(--accent-red);
        box-shadow: 0 0 40px var(--accent-red-glow), inset 0 0 60px rgba(220, 38, 38, 0.03);
        transform: translateY(-3px);
    }

    .bento-card:hover::before {
        opacity: 1;
    }

    .bento-hero-card {
        grid-column: span 2;
        grid-row: span 2;
        padding: 2.5rem;
        background: linear-gradient(145deg, #0c0c0c 0%, #080808 100%);
    }

    .bento-hero-card::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-red), var(--btc-gold));
    }

    .headline-hero {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 2.5rem;
        font-weight: 800;
        line-height: 1.1;
        color: #ffffff !important;
        letter-spacing: -0.02em;
        transition: color 0.3s ease;
    }

    .headline-hero:hover {
        color: var(--accent-red) !important;
    }

    .headline-secondary {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 1.2rem;
        font-weight: 700;
        line-height: 1.3;
        color: #ffffff !important;
        transition: color 0.3s ease;
    }

    .headline-secondary:hover {
        color: var(--accent-red) !important;
    }

    .body-text {
        font-family: 'DM Sans', -apple-system, sans-serif;
        font-size: 1rem;
        line-height: 1.75;
        color: #999999;
    }

    .meta-mono {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-muted);
        letter-spacing: 0.02em;
    }

    .badge-breaking {
        background: var(--accent-red);
        color: white;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        font-weight: 600;
        padding: 4px 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-radius: 3px;
        box-shadow: 0 0 20px rgba(220, 38, 38, 0.5);
        animation: pulse-badge 2s infinite;
    }

    @keyframes pulse-badge {
        0%, 100% { box-shadow: 0 0 20px rgba(220, 38, 38, 0.5); }
        50% { box-shadow: 0 0 30px rgba(220, 38, 38, 0.7); }
    }

    .badge-category {
        background: rgba(255, 255, 255, 0.06);
        color: #aaaaaa;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        font-weight: 500;
        padding: 4px 10px;
        border-radius: 3px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .terminal-list {
        background: rgba(5, 5, 5, 0.6);
        border: 1px solid var(--border-dim);
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
    }

    .terminal-item {
        display: flex;
        align-items: flex-start;
        gap: 1.25rem;
        padding: 1.25rem 0;
        border-bottom: 1px solid var(--accent-red);
        border-bottom-style: solid;
        border-bottom-width: 1px;
        border-image: linear-gradient(90deg, var(--accent-red), transparent) 1;
        transition: all 0.2s ease;
    }

    .terminal-item:last-child {
        border-bottom: none;
    }

    .terminal-item:hover {
        background: rgba(220, 38, 38, 0.02);
        margin: 0 -1.5rem;
        padding: 1.25rem 1.5rem;
    }

    .terminal-thumb {
        width: 100px;
        height: 75px;
        background: linear-gradient(135deg, #111 0%, #080808 100%);
        border: 1px solid var(--accent-red);
        border-radius: 6px;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--accent-red);
        font-size: 1.25rem;
        opacity: 0.8;
    }

    .terminal-headline {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 1.05rem;
        font-weight: 600;
        line-height: 1.4;
        color: #ffffff !important;
        transition: color 0.2s ease;
        margin-bottom: 0.5rem;
    }

    .terminal-headline:hover {
        color: var(--accent-red) !important;
    }

    .terminal-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: var(--text-muted);
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .archive-btn {
        background: transparent;
        border: 1px solid var(--border-dim);
        color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace;
        padding: 1rem 2rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        transition: all 0.3s ease;
        width: 100%;
    }

    .archive-btn:hover {
        border-color: var(--accent-red);
        color: var(--accent-red);
        background: rgba(220, 38, 38, 0.05);
        box-shadow: 0 0 20px var(--accent-red-glow);
    }

    .archive-zone {
        display: none;
        margin-top: 1.5rem;
    }

    .archive-zone.show {
        display: block;
        animation: fadeIn 0.4s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .sidebar-sticky { 
        position: sticky; 
        top: 1.5rem; 
    }
    
    .sidebar-module {
        background: var(--card-bg);
        border: 1px solid var(--border-dim);
        padding: 1.25rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }

    .sidebar-module-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: #ffffff;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border-dim);
    }

    .ticker-row {
        padding: 10px 0;
        border-bottom: 1px solid var(--border-dim);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .ticker-row:last-child {
        border-bottom: none;
    }
    
    .ticker-symbol { 
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600; 
        color: var(--text-muted); 
        font-size: 0.75rem;
        letter-spacing: 0.02em;
    }
    
    .ticker-price { 
        font-family: 'JetBrains Mono', monospace; 
        font-weight: 600;
        font-size: 0.85rem;
    }

    .nav-link-item {
        display: block;
        padding: 0.6rem 0;
        color: var(--text-muted);
        text-decoration: none;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        border-bottom: 1px solid var(--border-dim);
        transition: all 0.2s ease;
    }

    .nav-link-item:hover {
        color: var(--btc-gold);
        padding-left: 8px;
    }

    .nav-link-item:last-child {
        border-bottom: none;
    }

    .subscribe-field {
        background: #000 !important;
        border: 1px solid var(--border-dim) !important;
        color: white !important;
        font-family: 'DM Sans', sans-serif;
        border-radius: 5px;
        padding: 10px 12px;
        font-size: 0.85rem;
    }

    .subscribe-field:focus {
        border-color: var(--btc-gold) !important;
        box-shadow: 0 0 0 2px rgba(247, 147, 26, 0.15);
    }

    .subscribe-btn {
        background: var(--btc-gold);
        color: #000;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        border: none;
        width: 100%;
        padding: 10px;
        border-radius: 5px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.7rem;
        transition: all 0.3s ease;
    }

    .subscribe-btn:hover {
        background: #ffffff;
        box-shadow: 0 0 25px var(--btc-gold-glow);
    }

    .read-link {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 500;
        color: var(--accent-red);
        text-decoration: none;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        transition: all 0.2s ease;
    }

    .read-link:hover {
        color: #ffffff;
    }

    .read-link i {
        transition: transform 0.2s ease;
    }

    .read-link:hover i {
        transform: translateX(4px);
    }

    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: var(--text-muted);
        border: 1px dashed var(--border-dim);
        border-radius: 12px;
        font-family: 'DM Sans', sans-serif;
    }
</style>
{% endblock %}

{% block content %}
<div id="news-pulse-container">
    <div class="content-layer">
        <div class="container py-4">
            <div class="row g-4">
                <div class="col-lg-8">
                    <header class="mb-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="zone-label">Live Feed</span>
                            <span class="timestamp">{{ last_updated.strftime('%H:%M:%S') }} UTC</span>
                        </div>
                        <h1 class="page-title">The Report</h1>
                    </header>

                    {% if today_articles %}
                    <section class="mb-5">
                        <h2 class="section-header">
                            <i class="fas fa-bolt"></i>The 24-Hour Pulse
                        </h2>

                        <div class="bento-grid">
                            {% if today_articles|length > 0 %}
                            <a href="{{ url_for('article_detail', article_id=today_articles[0].id) }}" class="text-decoration-none bento-hero-card bento-card">
                                <div class="d-flex align-items-center gap-2 mb-3">
                                    {% if today_articles[0].is_pressing %}
                                    <span class="badge-breaking">Breaking</span>
                                    {% endif %}
                                    <span class="badge-category">{{ today_articles[0].category }}</span>
                                    <span class="meta-mono ms-2">{{ today_articles[0].created_at.strftime('%H:%M') }} UTC</span>
                                </div>
                                <h2 class="headline-hero mb-4">{{ today_articles[0].title }}</h2>
                                <p class="body-text mb-4">{{ today_articles[0].content | clean_preview(300) }}</p>
                                <div class="d-flex align-items-center justify-content-between">
                                    <span class="read-link">Read Full Report <i class="fas fa-arrow-right ms-2"></i></span>
                                    <span class="meta-mono">{{ today_articles[0].author or 'Protocol Pulse' }}</span>
                                </div>
                            </a>
                            {% endif %}

                            {% for article in today_articles[1:5] %}
                            <a href="{{ url_for('article_detail', article_id=article.id) }}" class="text-decoration-none bento-card">
                                <div class="d-flex align-items-center gap-2 mb-2">
                                    {% if article.is_pressing %}
                                    <span class="badge-breaking" style="font-size: 0.5rem; padding: 3px 7px;">Breaking</span>
                                    {% endif %}
                                    <span class="badge-category">{{ article.category }}</span>
                                </div>
                                <h3 class="headline-secondary mb-3">{{ article.title }}</h3>
                                <p class="body-text mb-3" style="font-size: 0.9rem; line-height: 1.6;">{{ article.content | clean_preview(100) }}</p>
                                <div class="d-flex align-items-center justify-content-between">
                                    <span class="meta-mono">{{ article.created_at.strftime('%H:%M') }} UTC</span>
                                    <span class="read-link" style="font-size: 0.6rem;">Read <i class="fas fa-chevron-right ms-1"></i></span>
                                </div>
                            </a>
                            {% endfor %}
                        </div>

                        {% if today_articles|length > 5 %}
                        <div class="bento-grid" style="grid-template-columns: repeat(2, 1fr);">
                            {% for article in today_articles[5:] %}
                            <a href="{{ url_for('article_detail', article_id=article.id) }}" class="text-decoration-none bento-card">
                                <div class="d-flex align-items-center gap-2 mb-2">
                                    <span class="badge-category">{{ article.category }}</span>
                                </div>
                                <h3 class="headline-secondary mb-2">{{ article.title }}</h3>
                                <span class="meta-mono">{{ article.created_at.strftime('%H:%M') }} UTC</span>
                            </a>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </section>
                    {% else %}
                    <div class="empty-state mb-5">
                        <i class="fas fa-satellite-dish mb-3" style="font-size: 2.5rem; color: var(--accent-red);"></i>
                        <p class="mb-0">Scanning networks for intelligence...</p>
                    </div>
                    {% endif %}

                    {% if yesterday_articles %}
                    <section class="mb-5">
                        <h2 class="section-header">
                            <i class="fas fa-history"></i>The Morning After
                        </h2>
                        <div class="terminal-list">
                            {% for article in yesterday_articles %}
                            <a href="{{ url_for('article_detail', article_id=article.id) }}" class="text-decoration-none">
                                <div class="terminal-item">
                                    <div class="terminal-thumb">
                                        <i class="fas fa-file-alt"></i>
                                    </div>
                                    <div class="flex-grow-1">
                                        <h4 class="terminal-headline">{{ article.title }}</h4>
                                        <div class="terminal-meta">
                                            <span class="badge-category">{{ article.category }}</span>
                                            <span>{{ article.created_at.strftime('%H:%M:%S') }}</span>
                                            <span>{{ article.created_at.strftime('%Y-%m-%d') }}</span>
                                        </div>
                                    </div>
                                </div>
                            </a>
                            {% endfor %}
                        </div>
                    </section>
                    {% endif %}

                    {% if archive_articles %}
                    <section class="mb-5">
                        <button class="archive-btn" onclick="toggleArchive()">
                            <i class="fas fa-archive me-2"></i>Load Archive // {{ archive_articles|length }}+ Reports
                        </button>
                        
                        <div id="archive-content" class="archive-zone">
                            <h2 class="section-header">
                                <i class="fas fa-database"></i>The Vault
                            </h2>
                            <div class="terminal-list">
                                {% for article in archive_articles %}
                                <a href="{{ url_for('article_detail', article_id=article.id) }}" class="text-decoration-none">
                                    <div class="terminal-item">
                                        <div class="terminal-thumb">
                                            <i class="fas fa-file-alt"></i>
                                        </div>
                                        <div class="flex-grow-1">
                                            <h4 class="terminal-headline">{{ article.title }}</h4>
                                            <div class="terminal-meta">
                                                <span>{{ article.created_at.strftime('%Y-%m-%d') }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </a>
                                {% endfor %}
                            </div>
                        </div>
                    </section>
                    {% endif %}
                </div>

                <div class="col-lg-4">
                    <div class="sidebar-sticky">
                        
                        <div class="sidebar-module" style="border-top: 2px solid var(--btc-gold);">
                            <h5 class="sidebar-module-title">Market Pulse</h5>
                            <div id="price-ticker">
                                {% if prices %}
                                <div class="ticker-row">
                                    <span class="ticker-symbol">BTC/USD</span>
                                    <span class="ticker-price {{ 'text-success' if prices.get('bitcoin', {}).get('usd_24h_change', 0) >= 0 else 'text-danger' }}">
                                        {{ price_service.format_price(prices.get('bitcoin', {}).get('usd', 0)) }}
                                    </span>
                                </div>
                                <div class="ticker-row">
                                    <span class="ticker-symbol">ETH/USD</span>
                                    <span class="ticker-price {{ 'text-success' if prices.get('ethereum', {}).get('usd_24h_change', 0) >= 0 else 'text-danger' }}">
                                        {{ price_service.format_price(prices.get('ethereum', {}).get('usd', 0)) }}
                                    </span>
                                </div>
                                <div class="ticker-row">
                                    <span class="ticker-symbol">SOL/USD</span>
                                    <span class="ticker-price {{ 'text-success' if prices.get('solana', {}).get('usd_24h_change', 0) >= 0 else 'text-danger' }}">
                                        {{ price_service.format_price(prices.get('solana', {}).get('usd', 0)) }}
                                    </span>
                                </div>
                                {% else %}
                                <div class="ticker-row">
                                    <span class="meta-mono">Loading...</span>
                                </div>
                                {% endif %}
                            </div>
                        </div>

                        <div class="sidebar-module">
                            <h5 class="sidebar-module-title">Deep Dive</h5>
                            {% for category in categories %}
                            <a href="/{{ category|lower }}" class="nav-link-item">
                                <i class="fas fa-chevron-right me-2" style="font-size: 0.6rem; color: var(--accent-red);"></i>{{ category }}
                            </a>
                            {% endfor %}
                        </div>

                        <div class="sidebar-module" style="border-top: 2px solid var(--accent-red);">
                            <h5 class="sidebar-module-title">Protocol Dispatch</h5>
                            <p class="meta-mono mb-3" style="font-size: 0.75rem; color: #888;">Daily Bitcoin intelligence.</p>
                            <form action="{{ url_for('subscribe') }}" method="POST">
                                <input type="email" name="email" class="form-control subscribe-field mb-2" placeholder="your@email.com" required>
                                <button type="submit" class="subscribe-btn">Subscribe</button>
                            </form>
                        </div>

                        {% if active_ads %}
                        <div class="sidebar-module bg-transparent border-0 p-0">
                            <span class="meta-mono d-block mb-2" style="font-size: 0.6rem; letter-spacing: 0.15em;">Partner</span>
                            {% for ad in active_ads %}
                            <div class="mt-2">
                                <a href="{{ ad.target_url }}" target="_blank">
                                    <img src="{{ ad.image_url }}" alt="Partner" class="img-fluid rounded" style="border: 1px solid var(--accent-red); opacity: 0.9;">
                                </a>
                            </div>
                            {% endfor %}
                        </div>
                        {% endif %}

                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function toggleArchive() {
    const archive = document.getElementById('archive-content');
    archive.classList.toggle('show');
    const btn = event.target.closest('button');
    if (archive.classList.contains('show')) {
        btn.innerHTML = '<i class="fas fa-times me-2"></i>Close Archive';
    } else {
        btn.innerHTML = '<i class="fas fa-archive me-2"></i>Load Archive // {{ archive_articles|length }}+ Reports';
    }
}
</script>
{% endblock %}
```

### templates/base.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Protocol Pulse{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}?v=1.1">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/coindesk-style.css') }}?v=1.1">
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
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/articles"><i class="fas fa-newspaper me-1"></i>Latest News</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/media"><i class="fas fa-broadcast-tower me-1"></i>The Network</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/merch"><i class="fas fa-tshirt me-1"></i>Merch</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                            <i class="fas fa-tags me-1"></i>Categories
                        </a>
                        <ul class="dropdown-menu bg-dark">
                            <li><a class="dropdown-item text-light" href="/bitcoin">Bitcoin</a></li>
                            <li><a class="dropdown-item text-light" href="/defi">DeFi</a></li>
                            <li><a class="dropdown-item text-light" href="/regulation">Regulation</a></li>
                            <li><a class="dropdown-item text-light" href="/privacy">Privacy</a></li>
                            <li><a class="dropdown-item text-light" href="/innovation">Innovation</a></li>
                        </ul>
                    </li>
                </ul>
                <form class="d-flex me-3">
                    <input class="form-control me-2 bg-secondary border-0 text-light" type="search" placeholder="Search articles...">
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
                <div class="col-md-4">
                    <h5>Protocol Pulse</h5>
                    <p>Bitcoin news and insights.</p>
                </div>
                <div class="col-md-4">
                    <h5>Categories</h5>
                    <ul class="list-unstyled">
                        <li><a href="/bitcoin">Bitcoin</a></li>
                        <li><a href="/defi">DeFi</a></li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <h5>Follow Us</h5>
                    <a href="#">Twitter</a> | <a href="#">LinkedIn</a>
                </div>
            </div>
            <hr>
            <p class="text-center">&copy; 2025 Protocol Pulse</p>
        </div>
    </footer>
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
    {% block scripts %}{% endblock %}
</body>
</html>```

### templates/category.html
```html
{% extends "base.html" %}
{% block title %}{{ category }} - Protocol Pulse{% endblock %}
{% block content %}
<div class="container mt-5">
    <div class="row">
        <div class="col-12">
            <h1 class="display-4 mb-4">
                <i class="fas fa-tags text-primary me-3"></i>{{ category }}
            </h1>
            <p class="lead text-muted mb-5">Latest news and insights in {{ category }}</p>
        </div>
    </div>
    
    {% if articles %}
        <div class="row">
            {% for article in articles %}
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card h-100 bg-dark border-secondary">
                        {% if article.header_image_url %}
                            <img src="{{ article.header_image_url }}" class="card-img-top" alt="{{ article.title }}" style="height: 200px; object-fit: cover;">
                        {% endif %}
                        <div class="card-body">
                            <span class="badge bg-primary mb-2">{{ article.category }}</span>
                            <h5 class="card-title">
                                <a href="/articles/{{ article.id }}" class="text-decoration-none text-light">{{ article.title }}</a>
                            </h5>
                            <p class="card-text text-muted">{{ article.content | clean_preview(120) }}...</p>
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">{{ article.created_at.strftime('%B %d, %Y') }}</small>
                                {% if article.featured %}
                                    <span class="badge bg-warning text-dark">Featured</span>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="row">
            <div class="col-12 text-center">
                <div class="py-5">
                    <i class="fas fa-newspaper text-muted mb-4" style="font-size: 4rem;"></i>
                    <h3 class="text-muted">No articles in {{ category }} yet</h3>
                    <p class="text-muted">Check back soon for new content in this category.</p>
                    <a href="/articles" class="btn btn-primary">
                        <i class="fas fa-arrow-left me-2"></i>Browse All Articles
                    </a>
                </div>
            </div>
        </div>
    {% endif %}
</div>
{% endblock %}```

### templates/contact.html
```html
{% extends "base.html" %}

{% block title %}Contact Us - Protocol Pulse{% endblock %}

{% block content %}
<section class="py-5">
    <div class="container">
        <div class="row mb-5">
            <div class="col-12 text-center">
                <h1 class="display-5 fw-bold mb-4">
                    <i class="fas fa-envelope text-primary me-3"></i>Get in Touch
                </h1>
                <p class="lead text-muted">Have questions, feedback, or want to collaborate? We'd love to hear from you.</p>
            </div>
        </div>

        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card bg-secondary border-0 shadow-lg">
                    <div class="card-body p-5">
                        <form class="needs-validation" novalidate>
                            <div class="row g-4">
                                <div class="col-md-6">
                                    <label for="name" class="form-label text-white">
                                        <i class="fas fa-user me-2"></i>Full Name
                                    </label>
                                    <input type="text" class="form-control form-control-lg" id="name" name="name" placeholder="Enter your full name" required>
                                    <div class="invalid-feedback">Please provide your name.</div>
                                </div>
                                
                                <div class="col-md-6">
                                    <label for="email" class="form-label text-white">
                                        <i class="fas fa-envelope me-2"></i>Email Address
                                    </label>
                                    <input type="email" class="form-control form-control-lg" id="email" name="email" placeholder="Enter your email" required>
                                    <div class="invalid-feedback">Please provide a valid email.</div>
                                </div>
                                
                                <div class="col-12">
                                    <label for="subject" class="form-label text-white">
                                        <i class="fas fa-tag me-2"></i>Subject
                                    </label>
                                    <select class="form-select form-select-lg" id="subject" name="subject" required>
                                        <option value="">Choose a subject...</option>
                                        <option value="general">General Inquiry</option>
                                        <option value="feedback">Feedback</option>
                                        <option value="partnership">Partnership Opportunity</option>
                                        <option value="press">Press Inquiry</option>
                                        <option value="technical">Technical Support</option>
                                        <option value="other">Other</option>
                                    </select>
                                    <div class="invalid-feedback">Please select a subject.</div>
                                </div>
                                
                                <div class="col-12">
                                    <label for="message" class="form-label text-white">
                                        <i class="fas fa-comment me-2"></i>Message
                                    </label>
                                    <textarea class="form-control" id="message" name="message" rows="6" placeholder="Tell us about your inquiry..." required></textarea>
                                    <div class="invalid-feedback">Please provide a message.</div>
                                </div>
                                
                                <div class="col-12 text-center">
                                    <button type="submit" class="btn btn-primary btn-lg px-5">
                                        <i class="fas fa-paper-plane me-2"></i>Send Message
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- Contact Info -->
        <div class="row mt-5">
            <div class="col-12">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="text-center">
                            <div class="mb-3">
                                <i class="fas fa-robot text-primary fa-3x"></i>
                            </div>
                            <h5>AI-Powered Support</h5>
                            <p class="text-muted">Our advanced AI systems are available 24/7 to help with your inquiries.</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <div class="mb-3">
                                <i class="fas fa-clock text-primary fa-3x"></i>
                            </div>
                            <h5>Response Time</h5>
                            <p class="text-muted">We typically respond within 24 hours during business days.</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <div class="mb-3">
                                <i class="fas fa-shield-alt text-primary fa-3x"></i>
                            </div>
                            <h5>Privacy Protected</h5>
                            <p class="text-muted">Your information is secure and never shared with third parties.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Social Links -->
        <div class="row mt-5">
            <div class="col-12 text-center">
                <h4 class="mb-4">Follow Us</h4>
                <div class="social-links justify-content-center">
                    <a href="https://x.com/ProtocolPulseHQ" target="_blank" class="social-icon" title="Follow us on X (Twitter)">
                        <i class="fab fa-twitter"></i>
                    </a>
                    <a href="https://www.linkedin.com/company/protocol-pulse/" target="_blank" class="social-icon" title="Connect on LinkedIn">
                        <i class="fab fa-linkedin"></i>
                    </a>
                    <a href="https://youtube.com/@protocolpulse?si=GNX-oERzlxJKZ32D" target="_blank" class="social-icon" title="Subscribe to our YouTube">
                        <i class="fab fa-youtube"></i>
                    </a>
                    <a href="https://t.me/+OTksIaXp3e42ZDEx" target="_blank" class="social-icon" title="Join our Telegram">
                        <i class="fab fa-telegram"></i>
                    </a>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}

{% block extra_scripts %}
<script>
// Form validation
(function() {
    'use strict';
    window.addEventListener('load', function() {
        var forms = document.getElementsByClassName('needs-validation');
        var validation = Array.prototype.filter.call(forms, function(form) {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                if (form.checkValidity() === false) {
                    event.stopPropagation();
                } else {
                    // Show success message
                    alert('Thank you for your message! We\'ll get back to you soon.');
                }
                form.classList.add('was-validated');
            }, false);
        });
    }, false);
})();
</script>
{% endblock %}```

### templates/index.html
```html
{% extends "base.html" %}
{% block title %}Home - Protocol Pulse{% endblock %}
{% block content %}
    <!-- Awesome Animated Hero Section with Red Flare Background -->
    <section class="hero-section">
        <canvas id="particles-canvas" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none;"></canvas>
        <div class="hero-particles"></div>
        <div class="container" style="position: relative; z-index: 5;">
            <div class="row align-items-center min-vh-100">
                <div class="col-lg-8">
                    <h1 class="hero-title display-1 fw-bold mb-4">
                        Protocol Pulse
                    </h1>
                    <p class="lead mb-4 text-light">
                        Where Bitcoin Innovation Meets Expert Analysis
                    </p>
                    <p class="mb-5 text-muted fs-5">
                        Deep insights, breaking news, and expert coverage of Bitcoin, 
                        DeFi, blockchain technology, and the decentralized future.
                    </p>
                    <div class="hero-actions">
                        <a href="/articles" class="btn btn-primary btn-lg me-3">
                            <i class="fas fa-newspaper me-2"></i>Latest News
                        </a>
                        <a href="/podcasts" class="btn btn-outline-light btn-lg me-3">
                            <i class="fas fa-podcast me-2"></i>Podcasts
                        </a>
                        <a href="/merch" class="btn btn-outline-danger btn-lg">
                            <i class="fas fa-tshirt me-2"></i>Merch
                        </a>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="hero-graphic text-center">
                        <img src="/static/images/bitcoin-symbol.png" alt="Bitcoin Symbol" style="width: 10rem; height: 10rem; opacity: 0.9;">
                        <div class="mt-4">
                            <div class="d-flex justify-content-center gap-4">
                                <i class="fas fa-chart-line" style="font-size: 2.5rem; color: var(--primary-color); opacity: 0.7;"></i>
                                <i class="fas fa-cube" style="font-size: 2.5rem; color: var(--primary-color); opacity: 0.7;"></i>
                                <i class="fas fa-network-wired" style="font-size: 2.5rem; color: var(--primary-color); opacity: 0.7;"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Featured Stories, Latest News, and Featured Podcasts Sections -->
    <div class="container my-5">
        
        <!-- Featured Stories Section -->
        <section class="featured-stories-section mb-5">
            <h2 class="section-title mb-4">
                <i class="fas fa-star text-warning me-2"></i>Featured Stories
            </h2>
            <div id="high-priority-featured-display" class="row">
                {% for article in featured_articles %}
                    <div class="col-md-4 mb-4">
                        <div class="card article-card h-100">
                            <div class="card-body">
                                <span class="badge bg-warning text-dark mb-2">Featured</span>
                                <h5 class="card-title article-title">
                                    <a href="/articles/{{ article.id }}" class="text-decoration-none">{{ article.title }}</a>
                                </h5>
                                <p class="card-text article-summary">{{ article.content | clean_preview(120) }}...</p>
                                <div class="d-flex justify-content-between align-items-center">
                                    <small class="article-date">{{ article.created_at.strftime('%B %d, %Y') }}</small>
                                    <span class="badge bg-secondary">{{ article.category }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </section>

        <!-- Latest News Section -->
        <section class="latest-news-section mb-5">
            <div class="row">
                <div class="col-lg-8">
                    <h2 class="section-title mb-4">
                        <i class="fas fa-newspaper text-primary me-2"></i>Latest News
                    </h2>
                    <div class="row">
                        {% for article in recent_articles[3:] %}
                            <div class="col-md-6 mb-4">
                                <div class="card article-card h-100">
                                    <div class="card-body">
                                        <h5 class="card-title">
                                            <a href="/articles/{{ article.id }}" class="text-decoration-none">{{ article.title }}</a>
                                        </h5>
                                        <p class="card-text text-muted">{{ article.content | clean_preview(100) }}...</p>
                                        <div class="d-flex justify-content-between align-items-center">
                                            <small class="text-muted">{{ article.created_at.strftime('%B %d, %Y') }}</small>
                                            <span class="badge bg-primary">{{ article.category }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                
                <!-- Sidebar with Markets -->
                <div class="col-lg-4">
                    <div class="sidebar">
                        <h3 class="sidebar-title mb-4">
                            <i class="fas fa-chart-line text-success me-2"></i>Markets
                        </h3>
                        <div class="market-widget">
                            <div class="crypto-price">
                                <span class="crypto-name">
                                    <span class="crypto-icon" style="background: #F7931A; color: white; width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; margin-right: 8px;">₿</span>
                                    Bitcoin
                                </span>
                                <span class="crypto-price-value">{{ price_service.format_price(prices.bitcoin.price) if prices and prices.bitcoin else '$--' }}</span>
                                <span class="crypto-change {{ 'positive' if prices and prices.bitcoin and prices.bitcoin.change_24h >= 0 else 'negative' }}">
                                    {{ price_service.format_change(prices.bitcoin.change_24h) if prices and prices.bitcoin else '--' }}
                                </span>
                            </div>
                            <div class="crypto-price">
                                <span class="crypto-name">
                                    <span class="crypto-icon" style="background: #627EEA; color: white; width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; margin-right: 8px;">Ξ</span>
                                    Ethereum
                                </span>
                                <span class="crypto-price-value">{{ price_service.format_price(prices.ethereum.price) if prices and prices.ethereum else '$--' }}</span>
                                <span class="crypto-change {{ 'positive' if prices and prices.ethereum and prices.ethereum.change_24h >= 0 else 'negative' }}">
                                    {{ price_service.format_change(prices.ethereum.change_24h) if prices and prices.ethereum else '--' }}
                                </span>
                            </div>
                            <div class="crypto-price">
                                <span class="crypto-name">
                                    <span class="crypto-icon" style="background: linear-gradient(135deg, #9945FF, #14F195); color: white; width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; margin-right: 8px;">S</span>
                                    Solana
                                </span>
                                <span class="crypto-price-value">{{ price_service.format_price(prices.solana.price) if prices and prices.solana else '$--' }}</span>
                                <span class="crypto-change {{ 'positive' if prices and prices.solana and prices.solana.change_24h >= 0 else 'negative' }}">
                                    {{ price_service.format_change(prices.solana.change_24h) if prices and prices.solana else '--' }}
                                </span>
                            </div>
                            <div class="text-muted small mt-2 text-center">
                                <i class="fas fa-sync-alt me-1"></i>Live prices via CoinGecko
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- View All News Button - Centered across full width -->
            <div class="text-center mt-4">
                <a href="/articles" class="btn btn-primary btn-lg">
                    <i class="fas fa-newspaper me-2"></i>View All News
                </a>
            </div>
        </section>

        <!-- Featured Podcasts Section -->
        <section class="featured-podcasts-section mb-5">
            <h2 class="section-title mb-4">
                <i class="fas fa-podcast text-info me-2"></i>Featured Podcasts
            </h2>
            <div class="row">
                {% for podcast in featured_podcasts %}
                    <div class="col-md-4 mb-4">
                        <div class="card podcast-card h-100">
                            <div class="card-body">
                                <span class="badge bg-info text-dark mb-2">Podcast</span>
                                <h5 class="card-title">{{ podcast.title }}</h5>
                                <p class="card-text text-muted">{{ podcast.description[:100] }}...</p>
                                <div class="d-flex justify-content-between align-items-center">
                                    <small class="text-muted">Episode {{ podcast.episode_number }}</small>
                                    <span class="badge bg-secondary">{{ podcast.duration }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            </div>
            <div class="text-center">
                <a href="/podcasts" class="btn btn-info btn-lg">
                    <i class="fas fa-podcast me-2"></i>View All Podcasts
                </a>
            </div>
        </section>
        
        <!-- Newsletter Signup Section -->
        <section class="newsletter-section py-5 bg-secondary">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-lg-8 text-center">
                        <h2 class="section-title mb-3">
                            <i class="fas fa-envelope text-primary me-2"></i>Stay Updated
                        </h2>
                        <p class="text-muted mb-4">Get the latest Bitcoin and blockchain insights delivered directly to your inbox.</p>
                        <form id="newsletter-form" class="newsletter-form">
                            <div class="row g-3">
                                <div class="col-md-5">
                                    <input type="text" class="form-control" id="first-name" name="first_name" placeholder="First Name">
                                </div>
                                <div class="col-md-5">
                                    <input type="email" class="form-control" id="email" name="email" placeholder="Email Address" required>
                                </div>
                                <div class="col-md-2">
                                    <button type="submit" class="btn btn-primary w-100" id="subscribe-btn">
                                        <i class="fas fa-paper-plane me-1"></i>Subscribe
                                    </button>
                                </div>
                            </div>
                        </form>
                        <div id="newsletter-message" class="mt-3" style="display: none;"></div>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <!-- Enhanced particles and animations -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Create floating particles in hero section
            const heroParticles = document.querySelector('.hero-particles');
            if (heroParticles) {
                for (let i = 0; i < 80; i++) {
                    const particle = document.createElement('div');
                    particle.className = 'particle';
                    particle.style.left = Math.random() * 100 + '%';
                    particle.style.animationDelay = Math.random() * 8 + 's';
                    particle.style.animationDuration = (Math.random() * 4 + 5) + 's';
                    
                    // Random particle sizes for more variety
                    const size = Math.random() * 6 + 2;
                    particle.style.width = size + 'px';
                    particle.style.height = size + 'px';
                    
                    heroParticles.appendChild(particle);
                }
            }

            // Add extra animation to the hero icons - slower on mobile
            const heroIcons = document.querySelectorAll('.hero-graphic i');
            const isMobile = window.innerWidth <= 768;
            const baseSpeed = isMobile ? 8 : 3;  // Much slower on mobile
            heroIcons.forEach((icon, index) => {
                icon.style.animation = `float ${baseSpeed + index * 0.5}s ease-in-out infinite`;
                icon.style.animationDelay = `${index * 0.2}s`;
            });
            
            // Newsletter form submission
            const newsletterForm = document.getElementById('newsletter-form');
            if (newsletterForm) {
                newsletterForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const email = document.getElementById('email').value;
                    const firstName = document.getElementById('first-name').value;
                    const subscribeBtn = document.getElementById('subscribe-btn');
                    const messageDiv = document.getElementById('newsletter-message');
                    
                    // Show loading state
                    subscribeBtn.disabled = true;
                    subscribeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Subscribing...';
                    
                    fetch('/api/subscribe', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            email: email,
                            first_name: firstName
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            messageDiv.innerHTML = '<div class="alert alert-success">Successfully subscribed! Check your email for confirmation.</div>';
                            newsletterForm.reset();
                        } else {
                            messageDiv.innerHTML = '<div class="alert alert-danger">Subscription failed: ' + (data.error || 'Unknown error') + '</div>';
                        }
                        messageDiv.style.display = 'block';
                    })
                    .catch(error => {
                        messageDiv.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
                        messageDiv.style.display = 'block';
                    })
                    .finally(() => {
                        // Reset button state
                        subscribeBtn.disabled = false;
                        subscribeBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>Subscribe';
                    });
                });
            }
        });
    </script>
{% endblock %}```

### templates/login.html
```html
{% extends "base.html" %}

{% block title %}Login - Protocol Pulse{% endblock %}

{% block content %}
<section class="py-5">
    <div class="container">
        <div class="row justify-content-center align-items-center min-vh-75">
            <div class="col-md-6 col-lg-4">
                <div class="card bg-secondary border-0 shadow-lg">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <i class="fas fa-broadcast-tower text-primary fa-3x mb-3"></i>
                            <h2 class="h3 fw-bold text-white">Welcome Back</h2>
                            <p class="text-muted">Sign in to access your Protocol Pulse dashboard</p>
                        </div>

                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ 'danger' if category == 'error' else 'warning' }} alert-dismissible fade show" role="alert">
                                        <i class="fas fa-exclamation-circle me-2"></i>{{ message }}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}

                        <form method="post" class="needs-validation" novalidate>
                            <div class="mb-4">
                                <label for="username" class="form-label text-white">
                                    <i class="fas fa-user me-2"></i>Username
                                </label>
                                <input type="text" 
                                       class="form-control form-control-lg" 
                                       id="username" 
                                       name="username" 
                                       placeholder="Enter your username"
                                       required>
                                <div class="invalid-feedback">
                                    Please enter your username.
                                </div>
                            </div>
                            
                            <div class="mb-4">
                                <label for="password" class="form-label text-white">
                                    <i class="fas fa-lock me-2"></i>Password
                                </label>
                                <div class="input-group">
                                    <input type="password" 
                                           class="form-control form-control-lg" 
                                           id="password" 
                                           name="password" 
                                           placeholder="Enter your password"
                                           required>
                                    <button class="btn btn-outline-secondary" type="button" onclick="togglePassword()">
                                        <i id="passwordToggleIcon" class="fas fa-eye"></i>
                                    </button>
                                </div>
                                <div class="invalid-feedback">
                                    Please enter your password.
                                </div>
                            </div>

                            <div class="mb-4">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="rememberMe" name="remember">
                                    <label class="form-check-label text-muted" for="rememberMe">
                                        Remember me for 30 days
                                    </label>
                                </div>
                            </div>

                            <button type="submit" class="btn btn-primary btn-lg w-100 mb-3">
                                <i class="fas fa-sign-in-alt me-2"></i>Sign In
                            </button>

                            <div class="text-center">
                                <a href="#" class="text-primary text-decoration-none me-3">
                                    <i class="fas fa-key me-1"></i>Forgot Password?
                                </a>
                                <a href="{{ url_for('signup') }}" class="text-primary text-decoration-none">
                                    <i class="fas fa-user-plus me-1"></i>Create Account
                                </a>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="text-center mt-4">
                    <p class="text-muted">
                        <i class="fas fa-shield-alt me-2"></i>
                        Your data is protected with enterprise-grade security
                    </p>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}

{% block extra_scripts %}
<script>
// Form validation
(function() {
    'use strict';
    window.addEventListener('load', function() {
        var forms = document.getElementsByClassName('needs-validation');
        var validation = Array.prototype.filter.call(forms, function(form) {
            form.addEventListener('submit', function(event) {
                if (form.checkValidity() === false) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }, false);
})();

// Password toggle
function togglePassword() {
    const passwordField = document.getElementById('password');
    const passwordToggleIcon = document.getElementById('passwordToggleIcon');
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        passwordToggleIcon.className = 'fas fa-eye-slash';
    } else {
        passwordField.type = 'password';
        passwordToggleIcon.className = 'fas fa-eye';
    }
}

// Auto-focus username field
document.getElementById('username').focus();
</script>
{% endblock %}```

### templates/media_hub.html
```html
{% extends "base.html" %}

{% block title %}The Network - Protocol Pulse Media{% endblock %}

{% block head %}
<link href="https://fonts.googleapis.com/css2?family=Uncut+Sans:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "PodcastSeries",
  "name": "Protocol Pulse",
  "description": "Where Bitcoin leaders speak truth. Unfiltered conversations with pioneers in the Bitcoin and Web3 space.",
  "url": "{{ url_for('media_hub', _external=True) }}",
  "genre": ["Bitcoin", "Cryptocurrency", "Technology", "Finance"],
  "inLanguage": "en",
  "publisher": {
    "@type": "Organization",
    "name": "Protocol Pulse",
    "url": "{{ url_for('index', _external=True) }}"
  }
}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "Bitcoin Essential Reading",
  "description": "Curated collection of essential Bitcoin and sound money literature",
  "itemListElement": [
    {% for book in recommended_books[:5] %}
    {
      "@type": "ListItem",
      "position": {{ loop.index }},
      "item": {
        "@type": "Book",
        "name": "{{ book.title }}",
        "author": {"@type": "Person", "name": "{{ book.author }}"},
        "description": "{{ book.description }}",
        "image": "{{ book.cover_url }}"
      }
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
</script>

<style>
    :root {
        --glass: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        --accent-red: #dc2626;
        --pure-white: #ffffff;
        --deep-black: #050505;
    }

    .media-hub {
        font-family: 'Uncut Sans', sans-serif;
        background-color: var(--deep-black);
        color: var(--pure-white);
    }

    /* Cinematic Hero */
    .hero-media {
        padding: 8rem 0 4rem;
        background: radial-gradient(circle at 0% 0%, #1a0505 0%, var(--deep-black) 50%);
        text-align: left;
        position: relative;
        overflow: hidden;
    }

    .hero-media::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 40%;
        height: 100%;
        background: radial-gradient(ellipse at 100% 0%, rgba(220, 38, 38, 0.15) 0%, transparent 60%);
        pointer-events: none;
    }

    .hero-media h1 {
        font-size: clamp(3rem, 8vw, 6rem);
        font-weight: 700;
        letter-spacing: -3px;
        line-height: 0.9;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    .hero-media .accent-text {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 4px;
        display: block;
        margin-bottom: 1rem;
    }

    .hero-subtitle {
        font-size: 1.25rem;
        font-weight: 300;
        color: rgba(255, 255, 255, 0.6);
        max-width: 500px;
    }

    /* The Bento Grid Architecture */
    .bento-section {
        padding: 4rem 0;
        background: var(--deep-black);
    }

    .section-label {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin-bottom: 2rem;
        display: block;
    }

    .bento-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        grid-auto-rows: 240px;
        gap: 1.5rem;
        margin-bottom: 4rem;
    }

    .bento-item {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 32px;
        padding: 2rem;
        position: relative;
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        display: flex;
        flex-direction: column;
    }

    .bento-item:hover {
        border-color: var(--accent-red);
        background: rgba(220, 38, 38, 0.05);
        transform: scale(1.02);
    }

    /* Spanning logic for spectacular look */
    .item-large { grid-column: span 2; grid-row: span 2; }
    .item-tall { grid-row: span 2; }
    .item-wide { grid-column: span 2; }

    /* Cinematic Card Backgrounds - YouTube Thumbnails */
    .bento-item.has-bg {
        background-size: cover;
        background-position: center;
        border: none;
    }

    .bento-item.has-bg::after {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(to top, rgba(0,0,0,0.95) 15%, rgba(0,0,0,0.4) 60%, rgba(0,0,0,0.2) 100%);
        z-index: 1;
        border-radius: 32px;
    }

    .bento-content {
        position: relative;
        z-index: 2;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }

    .bento-content .show-title {
        text-shadow: 0 4px 20px rgba(0,0,0,0.8);
    }

    /* Terminal Player Overlay */
    .player-terminal {
        position: fixed;
        inset: 0;
        background: rgba(5,5,5,0.98);
        z-index: 9999;
        display: none;
        padding: 2rem 4rem;
        backdrop-filter: blur(20px);
        overflow-y: auto;
    }

    .player-terminal.active {
        display: block;
        animation: terminalOpen 0.4s ease-out;
    }

    @keyframes terminalOpen {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }

    .terminal-header {
        border-bottom: 1px solid var(--accent-red);
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
    }

    .terminal-title {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.7);
        letter-spacing: 3px;
    }

    .btn-close-terminal {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        width: 40px;
        height: 40px;
        border-radius: 50%;
        font-size: 1.25rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-close-terminal:hover {
        background: var(--accent-red);
        border-color: var(--accent-red);
    }

    .video-wrapper {
        border: 1px solid var(--accent-red);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 40px 80px rgba(220,38,38,0.2);
    }

    .playlist-scroll {
        max-height: 60vh;
        overflow-y: auto;
        padding-right: 1rem;
    }

    .playlist-scroll::-webkit-scrollbar {
        width: 4px;
    }

    .playlist-scroll::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05);
    }

    .playlist-scroll::-webkit-scrollbar-thumb {
        background: var(--accent-red);
        border-radius: 2px;
    }

    .playlist-item {
        padding: 1.25rem;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    .playlist-item:hover {
        background: rgba(220,38,38,0.15);
        padding-left: 1.75rem;
    }

    .playlist-item.active {
        background: rgba(220,38,38,0.2);
        border-left: 3px solid var(--accent-red);
    }

    .playlist-item i {
        color: var(--accent-red);
        font-size: 1.1rem;
    }

    .playlist-item span {
        font-size: 0.95rem;
        font-weight: 500;
    }

    .series-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--pure-white);
        margin-bottom: 1.5rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
    }

    /* Button variants for Terminal */
    .btn-series {
        background: var(--accent-red);
        color: var(--pure-white);
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }

    .btn-series:hover {
        background: var(--pure-white);
        color: var(--deep-black);
        transform: translateY(-2px);
    }

    .btn-audio-only {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        width: 48px;
        height: 48px;
        border-radius: 50%;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .btn-audio-only:hover {
        border-color: var(--accent-red);
        color: var(--accent-red);
    }

    .now-broadcasting {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 3px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .now-broadcasting::before {
        content: '';
        width: 8px;
        height: 8px;
        background: var(--accent-red);
        border-radius: 50%;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* Protocol Heartbeat Node Tracker */
    .node-tracker-card {
        background: linear-gradient(135deg, rgba(0,0,0,1) 0%, rgba(20,20,20,1) 100%);
        position: relative;
        border-left: 3px solid var(--accent-red) !important;
    }

    .block-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--pure-white);
        letter-spacing: -1px;
    }

    .status-indicator {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        letter-spacing: 1px;
        padding: 2px 6px;
        border: 1px solid currentColor;
        border-radius: 3px;
    }

    .node-bg-effect {
        position: absolute;
        bottom: -20%;
        right: -10%;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(220, 38, 38, 0.15) 0%, transparent 70%);
        pointer-events: none;
        z-index: 0;
    }

    @keyframes blockFlash {
        0% { color: var(--accent-red); transform: scale(1.1); text-shadow: 0 0 20px var(--accent-red); }
        100% { color: var(--pure-white); transform: scale(1); text-shadow: none; }
    }

    .block-flash {
        animation: blockFlash 1s ease-out;
    }

    .x-small {
        font-size: 0.6rem;
    }

    /* Terminal Intel Briefing Sidebar */
    .terminal-sidebar {
        background: rgba(10, 10, 10, 0.5);
        border-left: 1px solid rgba(220, 38, 38, 0.2);
        height: 70vh;
        display: flex;
        flex-direction: column;
        padding: 1.5rem;
        border-radius: 16px;
    }

    .status-pill {
        background: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 4px;
    }

    .terminal-text {
        font-family: 'JetBrains Mono', monospace;
        color: var(--accent-red);
        opacity: 0.8;
    }

    #guideBody {
        font-size: 0.95rem;
        line-height: 1.6;
        color: rgba(255, 255, 255, 0.8);
    }

    /* Terminal Ad Unit */
    .terminal-ad-unit {
        padding-top: 1.5rem;
        margin-top: auto;
        position: relative;
        transition: opacity 0.3s ease;
    }

    .ad-perimeter {
        border: 1px solid rgba(220, 38, 38, 0.3);
        padding: 1rem;
        background: linear-gradient(180deg, rgba(220, 38, 38, 0.05) 0%, transparent 100%);
        border-radius: 12px;
    }

    .ad-content-wrapper {
        position: relative;
        overflow: hidden;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    #terminalAdImage {
        max-height: 80px;
        transition: transform 0.5s ease;
        filter: grayscale(100%) contrast(120%) brightness(80%);
    }

    .ad-perimeter:hover #terminalAdImage {
        filter: grayscale(0%) contrast(100%) brightness(100%);
        transform: scale(1.05);
    }

    .pulse-dot {
        width: 6px;
        height: 6px;
        background: #22c55e;
        border-radius: 50%;
        box-shadow: 0 0 10px #22c55e;
        animation: pulse 2s infinite;
    }

    .glitch-active #terminalAdImage {
        animation: glitch 0.4s steps(2) infinite;
        opacity: 0.5;
    }

    @keyframes glitch {
        0% { transform: translate(0); }
        20% { transform: translate(-5px, 5px); }
        40% { transform: translate(5px, -5px); }
        100% { transform: translate(0); }
    }

    /* Luxurious Book Cards */
    .book-card-luxury {
        background: linear-gradient(145deg, rgba(15,15,15,1) 0%, rgba(25,25,25,1) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 24px;
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        position: relative;
    }

    .book-card-luxury:hover {
        border-color: var(--accent-red);
        transform: translateY(-8px);
        box-shadow: 0 30px 60px rgba(220, 38, 38, 0.15);
    }

    .book-cover-luxury {
        height: 320px;
        background: linear-gradient(180deg, #0a0a0a 0%, #151515 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        padding: 2rem;
        overflow: hidden;
        perspective: 1200px;
        transform-style: preserve-3d;
    }

    .book-cover-luxury::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at 50% 0%, rgba(220, 38, 38, 0.1) 0%, transparent 60%);
        pointer-events: none;
    }

    .book-cover-luxury img {
        max-height: 280px;
        max-width: 180px;
        object-fit: contain;
        filter: drop-shadow(0 30px 50px rgba(0, 0, 0, 0.8));
        transition: transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94), filter 0.4s ease;
    }

    .book-card-luxury:hover .book-cover-luxury img {
        transform: scale(1.12) rotateY(-8deg) rotateX(3deg) translateZ(30px);
        filter: drop-shadow(0 40px 70px rgba(0, 0, 0, 0.9)) drop-shadow(0 0 25px rgba(220, 38, 38, 0.2));
    }

    .book-body-luxury {
        padding: 1.75rem;
    }

    .book-title-luxury {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
        line-height: 1.3;
        letter-spacing: -0.5px;
    }

    .book-author-luxury {
        font-size: 0.85rem;
        color: var(--accent-red);
        margin-bottom: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .book-description-luxury {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.5);
        line-height: 1.5;
        margin-bottom: 1.25rem;
    }

    .btn-amazon-luxury {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        padding: 0.85rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        transition: all 0.3s ease;
        width: 100%;
    }

    .btn-amazon-luxury:hover {
        background: #ff9900;
        color: var(--deep-black);
        border-color: #ff9900;
    }

    .badge-luxury {
        position: absolute;
        top: 1.25rem;
        left: 1.25rem;
        background: var(--accent-red);
        color: var(--pure-white);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        font-weight: 700;
        padding: 0.4rem 0.85rem;
        border-radius: 50px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        z-index: 2;
    }

    .badge-bestseller {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }

    /* Live Visualizer */
    .live-visualizer {
        display: flex;
        align-items: flex-end;
        gap: 3px;
        height: 24px;
        margin-bottom: 1rem;
    }

    .bar {
        width: 4px;
        background: var(--accent-red);
        border-radius: 2px;
        animation: equalize 0.8s infinite ease-in-out alternate;
    }

    .bar:nth-child(1) { animation-delay: 0.0s; }
    .bar:nth-child(2) { animation-delay: 0.15s; }
    .bar:nth-child(3) { animation-delay: 0.3s; }
    .bar:nth-child(4) { animation-delay: 0.45s; }
    .bar:nth-child(5) { animation-delay: 0.6s; }

    @keyframes equalize {
        from { height: 6px; }
        to { height: 24px; }
    }

    .show-title {
        font-size: 2.5rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 1rem;
        letter-spacing: -1px;
    }

    .show-meta {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: auto;
    }

    .btn-play-bento {
        background: var(--pure-white);
        color: var(--deep-black);
        border-radius: 50%;
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        text-decoration: none;
        position: absolute;
        bottom: 2rem;
        right: 2rem;
        transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
        border: none;
        cursor: pointer;
    }

    .btn-play-bento:hover {
        background: var(--accent-red);
        color: var(--pure-white);
        transform: rotate(15deg) scale(1.1);
    }

    .btn-play-bento.small {
        width: 48px;
        height: 48px;
        font-size: 1rem;
    }

    /* Episode Cards in Bento */
    .episode-bento {
        padding: 1.5rem;
    }

    .episode-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--accent-red);
        margin-bottom: 0.75rem;
    }

    .episode-title-bento {
        font-size: 1.3rem;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .episode-desc {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.6);
        line-height: 1.5;
    }

    /* Stats Card */
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: var(--pure-white);
        margin-bottom: 0.5rem;
    }

    .stat-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: rgba(255, 255, 255, 0.5);
    }

    /* CTA Card */
    .cta-card h3 {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .cta-card p {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 1.5rem;
    }

    .btn-cta {
        background: var(--accent-red);
        color: var(--pure-white);
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.9rem;
        text-decoration: none;
        display: inline-block;
        transition: all 0.3s ease;
    }

    .btn-cta:hover {
        background: #ef4444;
        transform: translateY(-2px);
        color: var(--pure-white);
    }

    /* Books Section - Bento Style */
    .books-section {
        padding: 6rem 0;
        background: linear-gradient(180deg, var(--deep-black) 0%, #0a0a0a 100%);
    }

    .books-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
    }

    .book-card-bento {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    }

    .book-card-bento:hover {
        border-color: var(--accent-red);
        transform: translateY(-8px);
    }

    .book-cover-bento {
        height: 280px;
        background: linear-gradient(135deg, #111 0%, #1a1a1a 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        padding: 2rem;
    }

    .book-cover-bento img {
        max-height: 240px;
        max-width: 160px;
        object-fit: contain;
        filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.5));
        transition: transform 0.4s ease;
    }

    .book-card-bento:hover .book-cover-bento img {
        transform: scale(1.05) rotate(-2deg);
    }

    .book-badge {
        position: absolute;
        top: 1rem;
        left: 1rem;
        background: var(--accent-red);
        color: var(--pure-white);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: 50px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .book-body-bento {
        padding: 1.5rem;
    }

    .book-title-bento {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        line-height: 1.3;
    }

    .book-author-bento {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 1rem;
    }

    .btn-amazon {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        padding: 0.75rem 1.25rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        transition: all 0.3s ease;
        width: 100%;
    }

    .btn-amazon:hover {
        background: var(--pure-white);
        color: var(--deep-black);
        border-color: var(--pure-white);
    }

    /* Tactile Merch Section - High Contrast */
    .merch-section {
        background: var(--pure-white);
        color: var(--deep-black);
        padding: 8rem 0;
        border-radius: 60px 60px 0 0;
        margin-top: 4rem;
    }

    .merch-title {
        font-size: clamp(2.5rem, 6vw, 4rem);
        font-weight: 700;
        letter-spacing: -2px;
        margin-bottom: 4rem;
        color: var(--deep-black);
        line-height: 1;
    }

    .merch-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
    }

    .merch-card-bento {
        background: #f5f5f5;
        border-radius: 24px;
        padding: 1.5rem;
        border: none;
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    }

    .merch-card-bento:hover {
        background: #eeeeee;
        transform: translateY(-10px);
    }

    .merch-img-wrapper {
        background: #fff;
        border-radius: 20px;
        height: 280px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1.5rem;
        overflow: hidden;
    }

    .merch-img-wrapper img {
        max-width: 80%;
        max-height: 80%;
        object-fit: contain;
        transition: transform 0.4s ease;
    }

    .merch-card-bento:hover .merch-img-wrapper img {
        transform: scale(1.1);
    }

    .merch-name {
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        color: var(--deep-black);
    }

    .merch-price {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        color: var(--accent-red);
        font-size: 1.25rem;
    }

    .btn-buy {
        background: var(--deep-black);
        color: var(--pure-white);
        border: none;
        padding: 0.6rem 1.25rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        transition: all 0.3s ease;
    }

    .btn-buy:hover {
        background: var(--accent-red);
        color: var(--pure-white);
    }

    /* Audio Player - Cyberpunk Style */
    .audio-player-bento {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(5, 5, 5, 0.95);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-top: 1px solid var(--glass-border);
        padding: 1rem 0;
        z-index: 1000;
        display: none;
    }

    .player-content {
        display: flex;
        align-items: center;
        gap: 2rem;
    }

    .player-controls {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .btn-player {
        background: var(--accent-red);
        border: none;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--pure-white);
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-player:hover {
        transform: scale(1.1);
    }

    .player-info {
        flex: 1;
    }

    .player-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.25rem;
    }

    .player-show {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.5);
    }

    .player-progress {
        flex: 2;
    }

    .progress-bar-container {
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
        cursor: pointer;
    }

    .progress-bar-fill {
        height: 100%;
        background: var(--accent-red);
        border-radius: 2px;
        width: 0%;
        transition: width 0.1s linear;
    }

    .time-display {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .player-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .btn-speed {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        padding: 0.4rem 0.75rem;
        border-radius: 50px;
        font-size: 0.8rem;
        font-family: 'JetBrains Mono', monospace;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-speed:hover {
        border-color: var(--accent-red);
    }

    .btn-close-player {
        background: transparent;
        border: none;
        color: rgba(255, 255, 255, 0.5);
        font-size: 1.25rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-close-player:hover {
        color: var(--pure-white);
    }

    /* Responsive */
    @media (max-width: 1200px) {
        .bento-grid, .books-grid, .merch-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .item-large { grid-column: span 2; }
    }

    @media (max-width: 768px) {
        .hero-media {
            padding: 6rem 0 3rem;
        }

        .hero-media h1 {
            font-size: 2.5rem;
            letter-spacing: -1px;
        }

        .bento-grid, .books-grid, .merch-grid {
            grid-template-columns: 1fr;
        }

        .item-large, .item-wide, .item-tall {
            grid-column: span 1;
            grid-row: span 1;
        }

        .item-large {
            grid-row: span 2;
        }

        .bento-grid {
            grid-auto-rows: auto;
        }

        .bento-item {
            min-height: 200px;
        }

        .merch-section {
            border-radius: 40px 40px 0 0;
            padding: 4rem 0;
        }

        .player-content {
            flex-wrap: wrap;
            gap: 1rem;
        }

        .player-progress {
            order: 3;
            flex-basis: 100%;
        }
    }

    /* Loading State */
    .loading-bento {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 200px;
    }

    .loader-ring {
        width: 40px;
        height: 40px;
        border: 3px solid var(--glass-border);
        border-top-color: var(--accent-red);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>
{% endblock %}

{% block content %}
<div class="media-hub">
    <!-- Cinematic Hero -->
    <section class="hero-media">
        <div class="container">
            <span class="accent-text">Network Operations // 2026</span>
            <h1>The Audio<br>Powerhouse.</h1>
            <p class="hero-subtitle">Dive deep into Bitcoin, privacy, and the future of decentralized finance with our premium podcast network.</p>
        </div>
    </section>

    <!-- Podcast Bento Grid -->
    <section class="bento-section">
        <div class="container">
            <span class="section-label">Live Broadcasts</span>
            
            <div class="bento-grid" id="podcast-bento">
                {% for show in shows %}
                {% if 'orange is the new' not in show.name|lower %}
                {% set series_slug = show.name|lower|replace(' ', '_')|replace("'", '') %}
                {% set series_key_map = {'cypherpunkd': 'cypherpunkd', "cypherpunk'd": 'cypherpunkd', 'protocol_pulse': 'protocol_pulse', 'protocol pulse': 'protocol_pulse'} %}
                {% set series_key = series_key_map.get(series_slug, series_slug) %}
                {% set series_data = youtube_series.get(series_key, {}) if youtube_series else {} %}
                {% set has_youtube = series_data and series_data.get('latest_id') %}
                {% set latest_id = series_data.get('latest_id', '') if has_youtube else '' %}
                {% if loop.index == 1 %}
                <!-- Primary Show - Large Cinematic Card -->
                <div class="bento-item item-large{% if has_youtube %} has-bg{% endif %}"{% if has_youtube %} style="background-image: url('https://img.youtube.com/vi/{{ latest_id }}/maxresdefault.jpg');"{% endif %}>
                    <div class="bento-content">
                        <div class="now-broadcasting">Now Broadcasting</div>
                        <h2 class="show-title">{{ show.name }}</h2>
                        <p class="episode-desc">{{ show.description[:100] }}...</p>
                        <div class="d-flex gap-2 mt-3">
                            {% if has_youtube %}
                            <button class="btn-series" onclick="openTerminal('{{ series_key }}')">
                                <i class="fas fa-tv me-2"></i>Series Guide
                            </button>
                            {% endif %}
                            <button class="btn-audio-only" onclick="loadShowEpisodes('{{ show.id }}')" title="Audio Only">
                                <i class="fas fa-headphones"></i>
                            </button>
                        </div>
                    </div>
                </div>
                {% elif loop.index == 2 %}
                <!-- Secondary Show - Wide Cinematic Card -->
                <div class="bento-item item-wide{% if has_youtube %} has-bg{% endif %}"{% if has_youtube %} style="background-image: url('https://img.youtube.com/vi/{{ latest_id }}/maxresdefault.jpg');"{% endif %}>
                    <div class="bento-content">
                        <span class="episode-tag">Featured Show</span>
                        <h2 class="show-title" style="font-size: 1.8rem;">{{ show.name }}</h2>
                        <div class="d-flex gap-2 mt-2">
                            {% if has_youtube %}
                            <button class="btn-series" onclick="openTerminal('{{ series_key }}')">
                                <i class="fas fa-play me-1"></i>Open Playlist
                            </button>
                            {% else %}
                            <button class="btn-series" onclick="loadShowEpisodes('{{ show.id }}')">
                                <i class="fas fa-headphones me-1"></i>Listen Now
                            </button>
                            {% endif %}
                        </div>
                    </div>
                </div>
                {% else %}
                <!-- Additional Shows - Standard Card -->
                <div class="bento-item">
                    <span class="episode-tag">{{ show.category }}</span>
                    <h3 class="show-title" style="font-size: 1.3rem;">{{ show.name }}</h3>
                    <p class="show-meta"><i class="fas fa-headphones me-2"></i>{{ show.episode_count }} episodes</p>
                    <button class="btn-play-bento small" onclick="loadShowEpisodes('{{ show.id }}')">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
                {% endif %}
                {% endif %}
                {% endfor %}

                <!-- Protocol Heartbeat - Live Node Tracker -->
                <div class="bento-item node-tracker-card" id="nodeTracker">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <span class="episode-tag">Protocol_Telemetry</span>
                        <span id="nodeStatus" class="status-indicator text-success">LOADING</span>
                    </div>
                    
                    <div class="tracker-main">
                        <label class="x-small opacity-50 font-monospace">BLOCK_HEIGHT</label>
                        <div id="liveHeight" class="block-number">#---,---</div>
                    </div>

                    <div class="tracker-footer mt-3 pt-2 border-top border-secondary">
                        <div class="row g-0">
                            <div class="col-12">
                                <label class="x-small opacity-50 font-monospace d-block">GLOBAL_HASHRATE</label>
                                <span id="liveHashrate" class="fw-bold" style="color: var(--accent-red);">---.-- EH/s</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="node-bg-effect"></div>
                </div>

                <!-- Stats Card -->
                <div class="bento-item">
                    <span class="episode-tag">Network Status</span>
                    <div class="stat-value" id="episode-count">{{ shows|sum(attribute='episode_count') }}</div>
                    <div class="stat-label">Total Episodes</div>
                </div>

                <!-- CTA Card -->
                <div class="bento-item cta-card">
                    <h3>Get the Alpha.</h3>
                    <p>Join the network of informed Bitcoiners.</p>
                    <a href="/newsletter" class="btn-cta">Subscribe</a>
                </div>
            </div>

            <!-- Latest Episodes -->
            <span class="section-label">Latest Episodes</span>
            <div class="bento-grid" id="episodes-container" style="grid-auto-rows: auto;">
                <div class="bento-item loading-bento" style="grid-column: span 4;">
                    <div class="loader-ring"></div>
                </div>
            </div>
        </div>
    </section>

    <!-- Books Section -->
    <section class="books-section">
        <div class="container">
            <span class="section-label">Essential Reading</span>
            <h2 style="font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; letter-spacing: -1px; margin-bottom: 3rem;">Our Book Series</h2>
            
            <div class="books-grid">
                {% for book in our_books %}
                <div class="book-card-luxury">
                    <div class="book-cover-luxury">
                        <span class="badge-luxury">Featured</span>
                        {% if book.cover_url %}
                        <img src="{{ book.cover_url }}" alt="{{ book.title }}">
                        {% else %}
                        <i class="fas fa-book" style="font-size: 4rem; color: #333;"></i>
                        {% endif %}
                    </div>
                    <div class="book-body-luxury">
                        <h5 class="book-title-luxury">{{ book.title }}</h5>
                        <p class="book-author-luxury">{{ book.author }}</p>
                        <p class="book-description-luxury">{{ book.description[:100] }}...</p>
                        <a href="{{ book.amazon_url }}" target="_blank" rel="noopener" class="btn-amazon-luxury">
                            <i class="fab fa-amazon"></i>Get on Amazon
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>

            <h2 style="font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; letter-spacing: -1px; margin: 4rem 0 3rem;">Recommended Reading</h2>
            
            <div class="books-grid">
                {% for book in recommended_books %}
                <div class="book-card-luxury">
                    <div class="book-cover-luxury">
                        {% if book.bestseller %}
                        <span class="badge-luxury badge-bestseller">Bestseller</span>
                        {% endif %}
                        {% if book.cover_url %}
                        <img src="{{ book.cover_url }}" alt="{{ book.title }}">
                        {% else %}
                        <i class="fas fa-book" style="font-size: 4rem; color: #333;"></i>
                        {% endif %}
                    </div>
                    <div class="book-body-luxury">
                        <h5 class="book-title-luxury">{{ book.title }}</h5>
                        <p class="book-author-luxury">{{ book.author }}</p>
                        <p class="book-description-luxury">{{ book.description[:100] }}...</p>
                        <a href="{{ book.amazon_url }}" target="_blank" rel="noopener" class="btn-amazon-luxury">
                            <i class="fab fa-amazon"></i>Get on Amazon
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>

    <!-- Tactile Merch Section -->
    <section class="merch-section">
        <div class="container">
            <h2 class="merch-title">Equip the<br>Movement.</h2>
            
            <div class="merch-grid">
                {% if products %}
                {% for product in products[:4] %}
                <div class="merch-card-bento">
                    <div class="merch-img-wrapper">
                        {% if product.thumbnail_url %}
                        <img src="{{ product.thumbnail_url }}" alt="{{ product.name }}">
                        {% else %}
                        <i class="fas fa-tshirt" style="font-size: 4rem; color: #ccc;"></i>
                        {% endif %}
                    </div>
                    <h5 class="merch-name">{{ product.name }}</h5>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="merch-price">${{ "%.2f"|format(product.retail_price|float) }}</span>
                        <a href="/merch" class="btn-buy">Buy</a>
                    </div>
                </div>
                {% endfor %}
                {% else %}
                <div class="merch-card-bento" style="grid-column: span 4; text-align: center; padding: 4rem;">
                    <p style="color: #666; margin-bottom: 1.5rem;">Merch coming soon!</p>
                    <a href="/merch" class="btn-buy">View Store</a>
                </div>
                {% endif %}
            </div>
            
            {% if products and products|length > 4 %}
            <div class="text-center mt-5">
                <a href="/merch" class="btn-buy" style="padding: 1rem 2rem; font-size: 1rem;">View All Merch</a>
            </div>
            {% endif %}
        </div>
    </section>
</div>

<!-- Cyberpunk Audio Player -->
<div id="audioPlayer" class="audio-player-bento">
    <div class="container">
        <div class="player-content">
            <div class="player-controls">
                <button class="btn-player" onclick="togglePlayPause()">
                    <i id="playPauseIcon" class="fas fa-play"></i>
                </button>
            </div>
            <div class="player-info">
                <div id="currentTitle" class="player-title">Now Playing</div>
                <div id="currentShow" class="player-show">Podcast Show</div>
            </div>
            <div class="player-progress">
                <div class="progress-bar-container" onclick="seekAudio(event)">
                    <div id="progressBar" class="progress-bar-fill"></div>
                </div>
                <div class="time-display">
                    <span id="currentTime">0:00</span>
                    <span id="totalTime">0:00</span>
                </div>
            </div>
            <div class="player-actions">
                <button class="btn-speed" onclick="adjustSpeed()">
                    <span id="speedLabel">1x</span>
                </button>
                <button class="btn-close-player" onclick="closePlayer()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    </div>
    <audio id="audioElement" style="display: none;"></audio>
</div>

<!-- YouTube Terminal Player Overlay -->
<div id="mediaTerminal" class="player-terminal">
    <div class="container-fluid">
        <div class="terminal-header">
            <span class="terminal-title">PROTOCOL PULSE // MEDIA_TERMINAL_v1.0</span>
            <button onclick="closeTerminal()" class="btn-close-terminal">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="row">
            <div class="col-lg-8 mb-4">
                <div class="video-wrapper">
                    <div class="ratio ratio-16x9">
                        <iframe id="terminalIframe" src="" allowfullscreen allow="autoplay"></iframe>
                    </div>
                </div>
            </div>
            <div class="col-lg-4 terminal-sidebar">
                <div class="briefing-header mb-4">
                    <span class="status-pill"><i class="fas fa-circle me-1"></i> SYSTEM_ONLINE</span>
                    <h3 class="accent-text mt-2" id="seriesTitle">INTEL_BRIEFING</h3>
                </div>

                <div id="seriesDescription" class="mb-4">
                    <p class="terminal-text small">
                        // AUTHORIZATION: PROTOCOL_LEVEL_4<br>
                        // SUBJECT: DECENTRALIZED_INTEL
                    </p>
                    <p id="guideBody">
                        Loading mission parameters...
                    </p>
                </div>

                <h5 class="text-uppercase small tracking-widest opacity-50 mb-3" style="letter-spacing: 2px;">Transmission Archive</h5>
                <div class="playlist-scroll" id="playlistContent">
                </div>

                <div class="mt-4 pt-3 border-top border-secondary">
                    <div class="row g-0 text-center">
                        <div class="col-6 border-end border-secondary">
                            <span class="d-block x-small opacity-50">EPISODES</span>
                            <span class="fw-bold" id="epCount">--</span>
                        </div>
                        <div class="col-6">
                            <span class="d-block x-small opacity-50">NETWORK_LOAD</span>
                            <span class="fw-bold text-success">OPTIMAL</span>
                        </div>
                    </div>
                </div>

                <!-- Sponsor Node -->
                <div class="terminal-ad-unit" id="terminalAdContainer" style="display: none;">
                    <div class="ad-perimeter">
                        <div class="ad-header d-flex justify-content-between align-items-center">
                            <span class="x-small font-monospace text-uppercase" style="letter-spacing: 2px; color: var(--accent-red);">Protocol_Partner</span>
                            <div class="pulse-dot"></div>
                        </div>
                        <a id="terminalAdLink" href="#" target="_blank" rel="noopener">
                            <div class="ad-content-wrapper mt-2">
                                <img id="terminalAdImage" src="" alt="Sponsor" class="img-fluid rounded">
                            </div>
                        </a>
                        <div class="ad-footer mt-2 d-flex justify-content-between">
                            <span id="terminalAdName" class="x-small font-monospace opacity-50">SCANNING...</span>
                            <span class="x-small font-monospace opacity-50">NODE_ID: 0x<span id="adNodeId">000</span></span>
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
let currentEpisode = null;
let playbackSpeeds = [0.75, 1, 1.25, 1.5, 2];
let currentSpeedIndex = 1;
let loadedEpisodes = 0;
const EPISODES_PER_LOAD = 6;

// YouTube Series Data with Intel Briefings
// TO UPDATE: Replace video IDs with your actual YouTube video IDs
// Go to youtube.com/watch?v=XXXXXXXXXXX - the 11-char code after v= is the ID
const seriesData = {
    'cypherpunkd': {
        title: "CYPHERPUNK'D // INTEL BRIEFING",
        epCount: '142',
        host: 'Matty Ice',
        description: 'Deep dives into privacy, cryptography, and financial sovereignty. Raw interviews with thought leaders, Bitcoiners, and digital freedom fighters. From zero-knowledge proofs to the physics of Proof of Work.',
        playlist: [
            { id: 'QX3M8Ka9vUA', title: 'Adam Back: From Cypherpunk to Bitcoin Treasury' },
            { id: 'k0BWlvnBmIE', title: 'The Big Print: Decentralization Episode' },
            { id: 'ERJ3NCqTTqg', title: 'Why Hyperinflation Makes Bitcoin Inevitable' }
        ]
    },
    'protocol_pulse': {
        title: 'PROTOCOL_PULSE // ANALYSIS',
        epCount: '84',
        host: 'Protocol Pulse Team',
        description: 'Where Bitcoin leaders speak truth. Unfiltered conversations from major conferences and exclusive interviews with pioneers shaping the future of sound money.',
        playlist: [
            { id: 'F9D7yL8C_W8', title: 'Bitcoin 2025 Conference Highlights' },
            { id: 'GtDMBqLVrpE', title: 'The Case for Sound Money' }
        ]
    }
};

// Sponsor Ads Data - Loaded from API
let terminalAds = [];
let currentAdIndex = 0;

// Load sponsors for terminal
async function loadTerminalAds() {
    try {
        const response = await fetch('/api/active-ads');
        const data = await response.json();
        if (data.success && data.ads.length > 0) {
            terminalAds = data.ads;
            displayTerminalAd();
            document.getElementById('terminalAdContainer').style.display = 'block';
        }
    } catch (error) {
        console.log('No sponsors available');
    }
}

function displayTerminalAd() {
    if (terminalAds.length === 0) return;
    
    const ad = terminalAds[currentAdIndex];
    document.getElementById('terminalAdImage').src = ad.image_url;
    document.getElementById('terminalAdLink').href = ad.target_url;
    document.getElementById('terminalAdName').textContent = ad.name.toUpperCase().replace(/ /g, '_');
    document.getElementById('adNodeId').textContent = ad.id.toString(16).toUpperCase().padStart(3, '0');
}

function rotateTerminalAds() {
    if (terminalAds.length <= 1) return;
    
    const adUnit = document.querySelector('.terminal-ad-unit');
    adUnit.classList.add('glitch-active');
    
    setTimeout(() => {
        currentAdIndex = (currentAdIndex + 1) % terminalAds.length;
        displayTerminalAd();
        adUnit.classList.remove('glitch-active');
    }, 400);
}

// Rotate ads every 20 seconds when terminal is open
setInterval(() => {
    if (document.getElementById('mediaTerminal').classList.contains('active')) {
        rotateTerminalAds();
    }
}, 20000);

// Terminal Player Functions
function openTerminal(seriesKey) {
    const data = seriesData[seriesKey];
    if (!data || !data.playlist || data.playlist.length === 0) {
        console.error('No series data found for:', seriesKey);
        return;
    }
    
    const iframe = document.getElementById('terminalIframe');
    const list = document.getElementById('playlistContent');
    const title = document.getElementById('seriesTitle');
    const guideBody = document.getElementById('guideBody');
    const epCount = document.getElementById('epCount');
    
    // Update Intel Briefing content
    title.textContent = data.title;
    guideBody.textContent = data.description;
    epCount.textContent = data.epCount || data.playlist.length;
    
    // Set first video
    iframe.src = `https://www.youtube.com/embed/${data.playlist[0].id}?autoplay=1&modestbranding=1&rel=0`;
    
    // Build Playlist with episode numbers
    list.innerHTML = data.playlist.map((video, index) => `
        <div class="playlist-item d-flex align-items-center ${index === 0 ? 'active' : ''}" onclick="changeVideo('${video.id}', this)">
            <span class="me-3 opacity-30 font-monospace" style="font-size: 0.75rem;">${(index + 1).toString().padStart(2, '0')}</span>
            <div class="flex-grow-1">
                <span>${video.title}</span>
            </div>
            <i class="fas fa-play-circle ms-2" style="color: var(--accent-red);"></i>
        </div>
    `).join('');

    document.getElementById('mediaTerminal').classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Load sponsors when terminal opens
    loadTerminalAds();
}

function changeVideo(id, element) {
    document.getElementById('terminalIframe').src = `https://www.youtube.com/embed/${id}?autoplay=1&modestbranding=1&rel=0`;
    
    // Update active state
    document.querySelectorAll('.playlist-item').forEach(item => item.classList.remove('active'));
    if (element) {
        element.classList.add('active');
    }
}

function closeTerminal() {
    document.getElementById('terminalIframe').src = '';
    document.getElementById('mediaTerminal').classList.remove('active');
    document.body.style.overflow = '';
}

// Close terminal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeTerminal();
    }
});

// Protocol Heartbeat - Live Network Stats
async function updateNodeTracker() {
    try {
        const response = await fetch('/api/network-stats');
        const data = await response.json();
        
        const heightEl = document.getElementById('liveHeight');
        const hashrateEl = document.getElementById('liveHashrate');
        const statusEl = document.getElementById('nodeStatus');

        // Check if block changed to trigger animation
        if (heightEl.textContent !== `#${data.height}`) {
            heightEl.classList.add('block-flash');
            setTimeout(() => heightEl.classList.remove('block-flash'), 1000);
        }

        heightEl.textContent = `#${data.height}`;
        hashrateEl.textContent = data.hashrate;
        statusEl.textContent = data.status;
        
        // Update status color
        if (data.status === 'OPERATIONAL') {
            statusEl.classList.remove('text-warning', 'text-danger');
            statusEl.classList.add('text-success');
        } else if (data.status === 'RECONNECTING' || data.status === 'TIMEOUT') {
            statusEl.classList.remove('text-success', 'text-danger');
            statusEl.classList.add('text-warning');
        } else {
            statusEl.classList.remove('text-success', 'text-warning');
            statusEl.classList.add('text-danger');
        }
        
    } catch (error) {
        console.error("Telemetry Link Error:", error);
        document.getElementById('nodeStatus').textContent = 'OFFLINE';
        document.getElementById('nodeStatus').classList.remove('text-success');
        document.getElementById('nodeStatus').classList.add('text-danger');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadEpisodes();
    
    // Initialize Protocol Heartbeat
    updateNodeTracker();
    setInterval(updateNodeTracker, 60000); // Update every 60 seconds
});

function loadEpisodes() {
    const container = document.getElementById('episodes-container');
    
    fetch(`/api/latest-episodes?limit=${EPISODES_PER_LOAD}&offset=${loadedEpisodes}`)
        .then(response => response.json())
        .then(data => {
            if (loadedEpisodes === 0) {
                container.innerHTML = '';
            }
            
            if (data.episodes && data.episodes.length > 0) {
                data.episodes.forEach((episode, index) => {
                    const card = createEpisodeCard(episode, index);
                    container.insertAdjacentHTML('beforeend', card);
                });
                loadedEpisodes += data.episodes.length;
                
                // Add load more button if there are more episodes
                if (data.has_more) {
                    const existingBtn = document.getElementById('load-more-btn');
                    if (!existingBtn) {
                        container.insertAdjacentHTML('afterend', `
                            <div class="text-center mt-4" id="load-more-container">
                                <button id="load-more-btn" class="btn-cta" onclick="loadMoreEpisodes()" style="background: transparent; border: 1px solid var(--glass-border); color: var(--pure-white);">
                                    <i class="fas fa-plus me-2"></i>Load More
                                </button>
                            </div>
                        `);
                    }
                }
            } else if (loadedEpisodes === 0) {
                container.innerHTML = '<div class="bento-item" style="grid-column: span 4; text-align: center;"><p style="color: rgba(255,255,255,0.5);">No episodes available yet.</p></div>';
            }
        })
        .catch(error => {
            console.error('Error loading episodes:', error);
            if (loadedEpisodes === 0) {
                container.innerHTML = '<div class="bento-item" style="grid-column: span 4; text-align: center;"><p style="color: rgba(255,255,255,0.5);">Unable to load episodes.</p></div>';
            }
        });
}

function loadMoreEpisodes() {
    loadEpisodes();
}

function createEpisodeCard(episode, index) {
    const date = new Date(episode.published_date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric'
    });
    
    // Vary card sizes for visual interest
    let sizeClass = '';
    if (index === 0) sizeClass = 'item-wide';
    
    return `
        <div class="bento-item ${sizeClass}" style="min-height: 180px;">
            <span class="episode-tag">${episode.show_name}</span>
            <h4 class="episode-title-bento">${episode.title}</h4>
            <div class="d-flex align-items-center justify-content-between mt-auto">
                <span style="font-size: 0.8rem; color: rgba(255,255,255,0.5);">
                    <i class="fas fa-clock me-1"></i>${episode.duration || 'N/A'}
                    <span class="ms-3"><i class="fas fa-calendar me-1"></i>${date}</span>
                </span>
                <button class="btn-play-bento small" onclick='playEpisode(${JSON.stringify(episode).replace(/'/g, "\\'")})'>
                    <i class="fas fa-play"></i>
                </button>
            </div>
        </div>
    `;
}

function loadShowEpisodes(showId) {
    fetch(`/api/episodes/${showId}?limit=10`)
        .then(response => response.json())
        .then(data => {
            if (data.episodes && data.episodes.length > 0) {
                playEpisode(data.episodes[0]);
            }
        })
        .catch(error => console.error('Error loading show episodes:', error));
}

function playEpisode(episode) {
    if (!episode.audio_url) {
        alert('Audio not available for this episode.');
        return;
    }
    
    currentEpisode = episode;
    document.getElementById('currentTitle').textContent = episode.title;
    document.getElementById('currentShow').textContent = episode.show_name;
    document.getElementById('audioPlayer').style.display = 'block';
    
    const audioElement = document.getElementById('audioElement');
    audioElement.src = episode.audio_url;
    audioElement.play();
    
    updatePlayPauseIcon(true);
}

function togglePlayPause() {
    const audioElement = document.getElementById('audioElement');
    if (audioElement.paused) {
        audioElement.play();
        updatePlayPauseIcon(true);
    } else {
        audioElement.pause();
        updatePlayPauseIcon(false);
    }
}

function updatePlayPauseIcon(isPlaying) {
    const icon = document.getElementById('playPauseIcon');
    icon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
}

function adjustSpeed() {
    const audioElement = document.getElementById('audioElement');
    currentSpeedIndex = (currentSpeedIndex + 1) % playbackSpeeds.length;
    const newSpeed = playbackSpeeds[currentSpeedIndex];
    audioElement.playbackRate = newSpeed;
    document.getElementById('speedLabel').textContent = newSpeed + 'x';
}

function closePlayer() {
    const audioElement = document.getElementById('audioElement');
    audioElement.pause();
    audioElement.currentTime = 0;
    document.getElementById('audioPlayer').style.display = 'none';
}

function seekAudio(event) {
    const audioElement = document.getElementById('audioElement');
    const progressBar = event.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audioElement.currentTime = percent * audioElement.duration;
}

document.getElementById('audioElement').addEventListener('timeupdate', function() {
    const audio = this;
    const progressBar = document.getElementById('progressBar');
    const currentTime = document.getElementById('currentTime');
    const totalTime = document.getElementById('totalTime');
    
    if (audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        progressBar.style.width = progress + '%';
        
        currentTime.textContent = formatTime(audio.currentTime);
        totalTime.textContent = formatTime(audio.duration);
    }
});

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
}
</script>
{% endblock %}
```

### templates/merch.html
```html
{% extends "base.html" %}

{% block title %}Merchandise - Protocol Pulse{% endblock %}

{% block content %}
<section class="py-5">
    <div class="container">
        <div class="row mb-5">
            <div class="col-12 text-center">
                <h1 class="display-5 fw-bold mb-4">
                    <i class="fas fa-tshirt text-primary me-3"></i>Protocol Pulse Merch
                </h1>
                <p class="lead text-muted">Show your support for the future of decentralized finance</p>
            </div>
        </div>

        <!-- Coming Soon Section -->
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card bg-secondary border-0 text-center">
                    <div class="card-body p-5">
                        <div class="mb-4">
                            <i class="fas fa-rocket text-primary" style="font-size: 4rem;"></i>
                        </div>
                        <h2 class="mb-4">Coming Soon!</h2>
                        <p class="text-muted mb-4">
                            We're working on bringing you awesome Protocol Pulse merchandise including 
                            t-shirts, hoodies, stickers, and exclusive Bitcoin & DeFi themed items.
                        </p>
                        
                        <!-- Newsletter Signup -->
                        <div class="card bg-primary text-white mb-4">
                            <div class="card-body p-4">
                                <h4 class="mb-3">Get Notified First</h4>
                                <p class="mb-3">Be the first to know when our merch store launches!</p>
                                <form class="row g-3 justify-content-center">
                                    <div class="col-md-6">
                                        <input type="email" class="form-control form-control-lg" placeholder="Enter your email">
                                    </div>
                                    <div class="col-auto">
                                        <button type="submit" class="btn btn-light btn-lg">
                                            <i class="fas fa-bell me-2"></i>Notify Me
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                        
                        <!-- Preview Items -->
                        <h4 class="mb-4">What to Expect</h4>
                        <div class="row g-4">
                            <div class="col-md-4">
                                <div class="card bg-dark border-primary">
                                    <div class="card-body p-3">
                                        <i class="fas fa-tshirt text-primary fa-2x mb-3"></i>
                                        <h6>Premium T-Shirts</h6>
                                        <p class="text-muted small mb-0">High-quality shirts with Bitcoin & DeFi designs</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-dark border-primary">
                                    <div class="card-body p-3">
                                        <i class="fas fa-coffee text-primary fa-2x mb-3"></i>
                                        <h6>Coffee Mugs</h6>
                                        <p class="text-muted small mb-0">Perfect for your morning Bitcoin news reading</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-dark border-primary">
                                    <div class="card-body p-3">
                                        <i class="fas fa-sticky-note text-primary fa-2x mb-3"></i>
                                        <h6>Sticker Packs</h6>
                                        <p class="text-muted small mb-0">Show your Bitcoin pride everywhere</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <a href="{{ url_for('index') }}" class="btn btn-outline-primary me-3">
                                <i class="fas fa-home me-2"></i>Back to Home
                            </a>
                            <a href="{{ url_for('articles') }}" class="btn btn-primary">
                                <i class="fas fa-newspaper me-2"></i>Read Articles
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Features Section -->
        <div class="row mt-5">
            <div class="col-12">
                <h3 class="text-center mb-4">Why Protocol Pulse Merch?</h3>
                <div class="row g-4">
                    <div class="col-md-3 col-sm-6">
                        <div class="text-center">
                            <i class="fas fa-leaf text-primary fa-2x mb-3"></i>
                            <h6>Eco-Friendly</h6>
                            <p class="text-muted small">Sustainable materials and carbon-neutral shipping</p>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="text-center">
                            <i class="fas fa-award text-primary fa-2x mb-3"></i>
                            <h6>Premium Quality</h6>
                            <p class="text-muted small">Only the finest materials and printing techniques</p>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="text-center">
                            <i class="fab fa-bitcoin text-primary fa-2x mb-3"></i>
                            <h6>Bitcoin Payments</h6>
                            <p class="text-muted small">Pay with Bitcoin for seamless transactions</p>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="text-center">
                            <i class="fas fa-shipping-fast text-primary fa-2x mb-3"></i>
                            <h6>Fast Shipping</h6>
                            <p class="text-muted small">Worldwide shipping with tracking included</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}```

### templates/podcasts.html
```html
{% extends "base.html" %}

{% block title %}Podcasts - Protocol Pulse{% endblock %}

{% block content %}
<section class="py-5">
    <div class="container">
        <div class="row mb-5">
            <div class="col-12">
                <h1 class="display-5 fw-bold text-center mb-3">
                    <i class="fas fa-podcast text-primary me-3"></i>Protocol Pulse Podcasts
                </h1>
                <p class="lead text-center text-muted">Deep dives into Bitcoin, DeFi, and the future of decentralized finance</p>
            </div>
        </div>

        {% if podcast_sections %}
        {% for section_name, podcasts in podcast_sections.items() %}
        <div class="mb-5">
            <div class="row mb-4">
                <div class="col-12">
                    <h2 class="fw-bold text-primary border-bottom border-primary pb-2">
                        <i class="fas fa-rss me-2"></i>{{ section_name }}
                    </h2>
                </div>
            </div>
            <div class="row g-4">
                {% for podcast in podcasts %}
            <div class="col-lg-4 col-md-6">
                <div class="card bg-secondary border-0 h-100 podcast-card">
                    <div class="podcast-cover-container">
                        {% if podcast.cover_image_url %}
                            <img src="{{ podcast.cover_image_url }}" 
                                 alt="{{ podcast.title }}" 
                                 class="podcast-cover w-100">
                        {% else %}
                            <div class="placeholder-cover bg-primary d-flex align-items-center justify-content-center">
                                <i class="fas fa-microphone fa-3x text-white"></i>
                            </div>
                        {% endif %}
                        
                        <div class="play-overlay">
                            <button class="btn btn-primary rounded-circle play-btn" onclick="playPodcast('{{ podcast.id }}')">
                                <i class="fas fa-play"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="card-body d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-primary">Episode {{ podcast.episode_number or 'N/A' }}</span>
                            {% if podcast.duration %}
                            <small class="text-muted">
                                <i class="fas fa-clock me-1"></i>{{ podcast.duration }}
                            </small>
                            {% endif %}
                        </div>
                        
                        <h5 class="card-title mb-3">{{ podcast.title }}</h5>
                        
                        <p class="card-text text-muted mb-3 flex-grow-1">
                            {{ podcast.description[:120] if podcast.description else 'An exciting discussion about the latest developments in Bitcoin and decentralized finance.' }}...
                        </p>
                        
                        <div class="podcast-meta">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <small class="text-muted">
                                    <i class="fas fa-user me-1"></i>{{ podcast.host or 'Protocol Pulse Team' }}
                                </small>
                                <small class="text-muted">
                                    {{ podcast.published_date.strftime('%b %d, %Y') }}
                                </small>
                            </div>
                            
                            <div class="d-flex gap-2">
                                <button class="btn btn-primary btn-sm flex-fill" onclick="playPodcast('{{ podcast.id }}')">
                                    <i class="fas fa-play me-1"></i>Play
                                </button>
                                <button class="btn btn-outline-primary btn-sm flex-fill" onclick="downloadPodcast('{{ podcast.id }}')">
                                    <i class="fas fa-download me-1"></i>Download
                                </button>
                                <button class="btn btn-outline-primary btn-sm" onclick="sharePodcast('{{ podcast.id }}')">
                                    <i class="fas fa-share me-1"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
                {% endfor %}
            </div>
            
            <!-- Additional episodes container (hidden initially) -->
            <div id="more-episodes-{{ section_name | replace(' ', '-') | replace("'", '') }}" class="row g-4 mt-2" style="display: none;"></div>
            
            <!-- See More button -->
            <div class="row mt-4">
                <div class="col-12 text-center">
                    <button class="btn btn-outline-primary" 
                            id="see-more-btn-{{ section_name | replace(' ', '-') | replace("'", '') }}"
                            onclick="loadMoreEpisodes('{{ section_name }}', '{{ section_name | replace(' ', '-') | replace("'", '') }}')">
                        <i class="fas fa-chevron-down me-2"></i>See More Episodes
                    </button>
                </div>
            </div>
        </div>
        {% endfor %}

        {% else %}
        <div class="text-center py-5">
            <i class="fas fa-microphone text-muted mb-4" style="font-size: 4rem;"></i>
            <h3 class="text-muted mb-3">Podcasts Coming Soon</h3>
            <p class="text-muted mb-4">We're working on bringing you exciting discussions about Bitcoin, DeFi, and the future of decentralized finance.</p>
            <a href="{{ url_for('index') }}" class="btn btn-primary me-3">
                <i class="fas fa-home me-2"></i>Back to Home
            </a>
            <a href="{{ url_for('articles') }}" class="btn btn-outline-primary">
                <i class="fas fa-newspaper me-2"></i>Read Articles
            </a>
        </div>
        {% endif %}
    </div>
</section>

<!-- Audio Player (Hidden by default) -->
<div id="audioPlayer" class="audio-player position-fixed bottom-0 start-0 end-0 p-3" style="display: none;">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-md-6">
                <div class="d-flex align-items-center">
                    <button class="btn btn-primary btn-sm me-3" onclick="togglePlayPause()">
                        <i id="playPauseIcon" class="fas fa-play"></i>
                    </button>
                    <div>
                        <h6 id="currentTitle" class="mb-0 text-white">Podcast Title</h6>
                        <small id="currentHost" class="text-muted">Host Name</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="progress progress-sm">
                    <div id="progressBar" class="progress-bar bg-primary" role="progressbar" style="width: 0%"></div>
                </div>
                <small class="text-muted">
                    <span id="currentTime">0:00</span> / <span id="totalTime">0:00</span>
                </small>
            </div>
            <div class="col-md-3 text-end">
                <button class="btn btn-outline-light btn-sm me-2" onclick="adjustSpeed()">
                    <span id="speedLabel">1x</span>
                </button>
                <button class="btn btn-outline-light btn-sm" onclick="closePlayer()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    </div>
    <audio id="audioElement" style="display: none;"></audio>
</div>
{% endblock %}

{% block scripts %}
<script>
let currentPodcast = null;
let playbackSpeeds = [0.75, 1, 1.25, 1.5, 2];
let currentSpeedIndex = 1;

function playPodcast(podcastId) {
    // Fetch real podcast data from backend
    fetch(`/api/podcast/${podcastId}`)
        .then(response => response.json())
        .then(podcast => {
            if (!podcast.audio_url) {
                alert('Audio not available for this episode yet.');
                return;
            }
            
            currentPodcast = podcast;
            document.getElementById('currentTitle').textContent = podcast.title;
            document.getElementById('currentHost').textContent = podcast.host || 'Protocol Pulse';
            document.getElementById('audioPlayer').style.display = 'block';
            
            const audioElement = document.getElementById('audioElement');
            audioElement.src = podcast.audio_url;
            audioElement.play();
            
            updatePlayPauseIcon(true);
        })
        .catch(error => {
            console.error('Error loading podcast:', error);
            alert('Unable to load podcast. Please try again.');
        });
}

function togglePlayPause() {
    const audioElement = document.getElementById('audioElement');
    if (audioElement.paused) {
        audioElement.play();
        updatePlayPauseIcon(true);
    } else {
        audioElement.pause();
        updatePlayPauseIcon(false);
    }
}

function updatePlayPauseIcon(isPlaying) {
    const icon = document.getElementById('playPauseIcon');
    icon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
}

function adjustSpeed() {
    const audioElement = document.getElementById('audioElement');
    currentSpeedIndex = (currentSpeedIndex + 1) % playbackSpeeds.length;
    const newSpeed = playbackSpeeds[currentSpeedIndex];
    audioElement.playbackRate = newSpeed;
    document.getElementById('speedLabel').textContent = newSpeed + 'x';
}

function closePlayer() {
    const audioElement = document.getElementById('audioElement');
    audioElement.pause();
    audioElement.currentTime = 0;
    document.getElementById('audioPlayer').style.display = 'none';
}

function downloadPodcast(podcastId) {
    alert('Download feature coming soon! Subscribe to get notified.');
}

function sharePodcast(podcastId) {
    if (navigator.share) {
        navigator.share({
            title: 'Protocol Pulse Podcast',
            text: 'Check out this podcast episode!',
            url: window.location.href
        });
    } else {
        navigator.clipboard.writeText(window.location.href);
        alert('Link copied to clipboard!');
    }
}

// Update progress bar
document.getElementById('audioElement').addEventListener('timeupdate', function() {
    const audio = this;
    const progressBar = document.getElementById('progressBar');
    const currentTime = document.getElementById('currentTime');
    const totalTime = document.getElementById('totalTime');
    
    if (audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        progressBar.style.width = progress + '%';
        
        currentTime.textContent = formatTime(audio.currentTime);
        totalTime.textContent = formatTime(audio.duration);
    }
});

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
}

// Podcast progressive loading functionality
let loadingStates = {}; // Track loading state for each section

function loadMoreEpisodes(sectionName, sectionId) {
    if (loadingStates[sectionId]) return; // Prevent multiple simultaneous requests
    
    loadingStates[sectionId] = true;
    const button = document.getElementById(`see-more-btn-${sectionId}`);
    const container = document.getElementById(`more-episodes-${sectionId}`);
    
    // Change button to loading state
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    button.disabled = true;
    
    // Calculate offset based on existing episodes
    const existingEpisodes = container.children.length + 3; // 3 initial + loaded ones
    const loadLimit = button.dataset.showingAll === 'true' ? 999 : 3; // Load 3 more or all remaining
    
    fetch(`/api/podcasts/${encodeURIComponent(sectionName)}?offset=${existingEpisodes}&limit=${loadLimit}`)
        .then(response => response.json())
        .then(data => {
            if (data.podcasts && data.podcasts.length > 0) {
                // Show container if hidden
                container.style.display = 'flex';
                
                // Add new episodes
                data.podcasts.forEach(podcast => {
                    const podcastCard = createPodcastCard(podcast);
                    container.appendChild(podcastCard);
                });
                
                // Update button based on remaining episodes
                if (button.dataset.showingAll === 'true' || !data.has_more) {
                    // No more episodes to load
                    button.style.display = 'none';
                } else {
                    // Update button for "See All" functionality
                    button.innerHTML = '<i class="fas fa-expand-alt me-2"></i>See All Episodes';
                    button.dataset.showingAll = 'true';
                }
            } else {
                // No more episodes
                button.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error loading more episodes:', error);
            button.innerHTML = originalHTML;
            alert('Failed to load more episodes. Please try again.');
        })
        .finally(() => {
            loadingStates[sectionId] = false;
            button.disabled = false;
        });
}

function createPodcastCard(podcast) {
    const col = document.createElement('div');
    col.className = 'col-lg-4 col-md-6';
    
    col.innerHTML = `
        <div class="card bg-secondary border-0 h-100 podcast-card">
            <div class="podcast-cover-container">
                ${podcast.cover_image_url ? 
                    `<img src="${podcast.cover_image_url}" alt="${podcast.title}" class="podcast-cover w-100">` :
                    `<div class="placeholder-cover bg-primary d-flex align-items-center justify-content-center">
                        <i class="fas fa-microphone fa-3x text-white"></i>
                    </div>`
                }
                <div class="play-overlay">
                    <button class="btn btn-primary rounded-circle play-btn" onclick="playPodcast('${podcast.id}')">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
            </div>
            
            <div class="card-body d-flex flex-column">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <span class="badge bg-primary">Episode ${podcast.episode_number || 'N/A'}</span>
                    ${podcast.duration ? 
                        `<small class="text-muted"><i class="fas fa-clock me-1"></i>${podcast.duration}</small>` : 
                        ''
                    }
                </div>
                
                <h5 class="card-title mb-3">${podcast.title}</h5>
                
                <p class="card-text text-muted mb-3 flex-grow-1">
                    ${podcast.description || 'An exciting discussion about the latest developments in Bitcoin and decentralized finance.'}
                </p>
                
                <div class="podcast-meta">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <small class="text-muted">
                            <i class="fas fa-user me-1"></i>${podcast.host}
                        </small>
                        <small class="text-muted">
                            ${podcast.published_date}
                        </small>
                    </div>
                    
                    <div class="d-flex gap-2">
                        <button class="btn btn-primary btn-sm flex-fill" onclick="playPodcast('${podcast.id}')">
                            <i class="fas fa-play me-1"></i>Play
                        </button>
                        <button class="btn btn-outline-primary btn-sm flex-fill" onclick="downloadPodcast('${podcast.id}')">
                            <i class="fas fa-download me-1"></i>Download
                        </button>
                        <button class="btn btn-outline-primary btn-sm" onclick="sharePodcast('${podcast.id}')">
                            <i class="fas fa-share me-1"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    return col;
}
</script>
{% endblock %}```

### templates/signup.html
```html
{% extends "base.html" %}

{% block title %}Sign Up - Protocol Pulse{% endblock %}

{% block content %}
<section class="py-5">
    <div class="container">
        <div class="row justify-content-center align-items-center min-vh-75">
            <div class="col-md-6 col-lg-5">
                <div class="card bg-secondary border-0 shadow-lg">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <i class="fas fa-user-plus text-primary fa-3x mb-3"></i>
                            <h2 class="h3 fw-bold text-white">Join Protocol Pulse</h2>
                            <p class="text-muted">Create your account to access exclusive Bitcoin content</p>
                        </div>

                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ 'danger' if category == 'error' else 'warning' }} alert-dismissible fade show" role="alert">
                                        <i class="fas fa-exclamation-circle me-2"></i>{{ message }}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}

                        <form method="post" class="needs-validation" novalidate>
                            <div class="mb-4">
                                <label for="username" class="form-label text-white">
                                    <i class="fas fa-user me-2"></i>Username
                                </label>
                                <input type="text" 
                                       class="form-control form-control-lg" 
                                       id="username" 
                                       name="username" 
                                       placeholder="Choose a unique username"
                                       pattern="[a-zA-Z0-9_]{3,20}"
                                       title="Username must be 3-20 characters long and contain only letters, numbers, and underscores"
                                       required>
                                <div class="invalid-feedback">
                                    Please choose a valid username (3-20 characters).
                                </div>
                            </div>
                            
                            <div class="mb-4">
                                <label for="email" class="form-label text-white">
                                    <i class="fas fa-envelope me-2"></i>Email Address
                                </label>
                                <input type="email" 
                                       class="form-control form-control-lg" 
                                       id="email" 
                                       name="email" 
                                       placeholder="Enter your email address"
                                       required>
                                <div class="invalid-feedback">
                                    Please provide a valid email address.
                                </div>
                                <div class="form-text text-muted">
                                    We'll never share your email with anyone else.
                                </div>
                            </div>
                            
                            <div class="mb-4">
                                <label for="password" class="form-label text-white">
                                    <i class="fas fa-lock me-2"></i>Password
                                </label>
                                <div class="input-group">
                                    <input type="password" 
                                           class="form-control form-control-lg" 
                                           id="password" 
                                           name="password" 
                                           placeholder="Create a strong password"
                                           pattern=".{8,}"
                                           title="Password must be at least 8 characters long"
                                           required>
                                    <button class="btn btn-outline-secondary" type="button" onclick="togglePassword()">
                                        <i id="passwordToggleIcon" class="fas fa-eye"></i>
                                    </button>
                                </div>
                                <div class="invalid-feedback">
                                    Password must be at least 8 characters long.
                                </div>
                                <div class="form-text text-muted">
                                    Use at least 8 characters with a mix of letters, numbers, and symbols.
                                </div>
                            </div>

                            <div class="mb-4">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="agreeTerms" required>
                                    <label class="form-check-label text-muted" for="agreeTerms">
                                        I agree to the <a href="#" class="text-primary">Terms of Service</a> 
                                        and <a href="#" class="text-primary">Privacy Policy</a>
                                    </label>
                                    <div class="invalid-feedback">
                                        You must agree to the terms before signing up.
                                    </div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="newsletter" name="newsletter">
                                    <label class="form-check-label text-muted" for="newsletter">
                                        Subscribe to our newsletter for Bitcoin & DeFi updates
                                    </label>
                                </div>
                            </div>

                            <button type="submit" class="btn btn-primary btn-lg w-100 mb-3">
                                <i class="fas fa-user-plus me-2"></i>Create Account
                            </button>

                            <div class="text-center">
                                <span class="text-muted">Already have an account?</span>
                                <a href="{{ url_for('login') }}" class="text-primary text-decoration-none ms-1">
                                    <i class="fas fa-sign-in-alt me-1"></i>Sign In
                                </a>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="text-center mt-4">
                    <p class="text-muted">
                        <i class="fas fa-shield-alt me-2"></i>
                        Join thousands of Bitcoiners getting the latest Bitcoin and DeFi insights
                    </p>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}

{% block extra_scripts %}
<script>
// Form validation
(function() {
    'use strict';
    window.addEventListener('load', function() {
        var forms = document.getElementsByClassName('needs-validation');
        var validation = Array.prototype.filter.call(forms, function(form) {
            form.addEventListener('submit', function(event) {
                if (form.checkValidity() === false) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }, false);
})();

// Password toggle
function togglePassword() {
    const passwordField = document.getElementById('password');
    const passwordToggleIcon = document.getElementById('passwordToggleIcon');
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        passwordToggleIcon.className = 'fas fa-eye-slash';
    } else {
        passwordField.type = 'password';
        passwordToggleIcon.className = 'fas fa-eye';
    }
}

// Auto-focus username field
document.getElementById('username').focus();
</script>
{% endblock %}```

### templates/admin/ads.html
```html
{% extends "base.html" %}

{% block title %}Advertisement Management - Protocol Pulse Admin{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1 class="h3 text-primary">Advertisement Management</h1>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addAdModal">
                    <i class="fas fa-plus me-2"></i>Add New Advertisement
                </button>
            </div>

            <!-- Advertisements Grid -->
            <div class="row g-4">
                {% if ads %}
                    {% for ad in ads %}
                    <div class="col-lg-4 col-md-6">
                        <div class="card h-100 ad-card" data-ad-id="{{ ad.id }}">
                            <div class="position-relative">
                                <img src="{{ ad.image_url }}" alt="{{ ad.name }}" class="card-img-top" style="height: 200px; object-fit: cover;">
                                <div class="position-absolute top-0 end-0 p-2">
                                    <span class="badge bg-{{ 'success' if ad.is_active else 'secondary' }}">
                                        {{ 'Active' if ad.is_active else 'Inactive' }}
                                    </span>
                                </div>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title">{{ ad.name }}</h5>
                                <p class="card-text">
                                    <strong>Target URL:</strong><br>
                                    <a href="{{ ad.target_url }}" target="_blank" class="text-break">{{ ad.target_url }}</a>
                                </p>
                                <small class="text-muted">Created: {{ ad.created_at.strftime('%B %d, %Y at %I:%M %p') }}</small>
                            </div>
                            <div class="card-footer bg-transparent">
                                <div class="btn-group w-100" role="group">
                                    <button class="btn btn-outline-{{ 'warning' if ad.is_active else 'success' }} toggle-ad-btn" 
                                            data-ad-id="{{ ad.id }}" 
                                            data-current-status="{{ ad.is_active }}">
                                        <i class="fas fa-{{ 'pause' if ad.is_active else 'play' }} me-1"></i>
                                        {{ 'Deactivate' if ad.is_active else 'Activate' }}
                                    </button>
                                    <button class="btn btn-outline-danger delete-ad-btn" 
                                            data-ad-id="{{ ad.id }}" 
                                            data-ad-name="{{ ad.name }}">
                                        <i class="fas fa-trash me-1"></i>Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                <div class="col-12">
                    <div class="text-center py-5">
                        <i class="fas fa-ad text-muted" style="font-size: 4rem;"></i>
                        <h3 class="mt-3 text-muted">No advertisements yet</h3>
                        <p class="text-muted">Create your first advertisement to get started.</p>
                        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addAdModal">
                            <i class="fas fa-plus me-2"></i>Add First Advertisement
                        </button>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- Add Advertisement Modal -->
<div class="modal fade" id="addAdModal" tabindex="-1" aria-labelledby="addAdModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="addAdModalLabel">Add New Advertisement</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form id="addAdForm" enctype="multipart/form-data">
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="adName" class="form-label">Advertisement Name</label>
                        <input type="text" class="form-control" id="adName" name="name" required>
                        <div class="form-text">Internal name for identification</div>
                    </div>
                    <div class="mb-3">
                        <label for="adTargetUrl" class="form-label">Target URL</label>
                        <input type="url" class="form-control" id="adTargetUrl" name="target_url" required>
                        <div class="form-text">Where users will be redirected when clicking the ad</div>
                    </div>
                    <div class="mb-3">
                        <label for="adImage" class="form-label">Advertisement Image</label>
                        <input type="file" class="form-control" id="adImage" name="image" accept="image/*" required>
                        <div class="form-text">Image will be enhanced using AI for optimal visual impact</div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-magic me-2"></i>Create & Enhance
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>

<style>
.ad-card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.ad-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.card-img-top {
    border-bottom: 1px solid #dee2e6;
}

.btn-group .btn {
    flex: 1;
}

.loading {
    opacity: 0.6;
    pointer-events: none;
}
</style>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const addAdForm = document.getElementById('addAdForm');
    const addAdModal = new bootstrap.Modal(document.getElementById('addAdModal'));

    // Handle form submission
    addAdForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating...';
        submitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/add-ad', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                addAdModal.hide();
                location.reload(); // Refresh to show new ad
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('Error creating advertisement: ' + error.message);
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    });

    // Handle toggle buttons
    document.querySelectorAll('.toggle-ad-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const adId = this.dataset.adId;
            const currentStatus = this.dataset.currentStatus === 'True';
            
            try {
                const response = await fetch(`/api/toggle-ad/${adId}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    location.reload(); // Refresh to show updated status
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Error toggling advertisement: ' + error.message);
            }
        });
    });

    // Handle delete buttons
    document.querySelectorAll('.delete-ad-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const adId = this.dataset.adId;
            const adName = this.dataset.adName;
            
            if (confirm(`Are you sure you want to delete "${adName}"? This action cannot be undone.`)) {
                try {
                    const response = await fetch(`/api/delete-ad/${adId}`, {
                        method: 'DELETE'
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        location.reload(); // Refresh to show updated list
                    } else {
                        alert('Error: ' + result.error);
                    }
                } catch (error) {
                    alert('Error deleting advertisement: ' + error.message);
                }
            }
        });
    });
});
</script>
{% endblock %}```

### templates/admin/dashboard.html
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

### templates/admin/edit_article.html
```html
{% extends "base.html" %}

{% block title %}Edit Article - Admin{% endblock %}

{% block extra_head %}
<style>
    .write-form {
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 2rem;
    }
    .form-label {
        color: #f7931a;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .form-control, .form-select {
        background: #0a0a0a;
        border: 1px solid #333;
        color: #fff;
        padding: 0.75rem 1rem;
    }
    .form-control:focus, .form-select:focus {
        background: #0a0a0a;
        border-color: #f7931a;
        color: #fff;
        box-shadow: 0 0 0 0.2rem rgba(247, 147, 26, 0.25);
    }
    .form-control::placeholder {
        color: #666;
    }
    #content-editor {
        min-height: 400px;
        font-family: 'DM Sans', sans-serif;
        line-height: 1.7;
    }
    .btn-publish {
        background: #f7931a;
        color: #000;
        font-weight: 700;
        padding: 0.75rem 2rem;
        border: none;
    }
    .btn-publish:hover {
        background: #ffa726;
        color: #000;
    }
    .btn-draft {
        background: transparent;
        color: #f7931a;
        border: 2px solid #f7931a;
        font-weight: 600;
        padding: 0.75rem 2rem;
    }
    .btn-draft:hover {
        background: rgba(247, 147, 26, 0.1);
        color: #f7931a;
    }
    .article-status {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.875rem;
    }
    .status-published {
        background: rgba(40, 167, 69, 0.2);
        color: #28a745;
        border: 1px solid #28a745;
    }
    .status-draft {
        background: rgba(255, 193, 7, 0.2);
        color: #ffc107;
        border: 1px solid #ffc107;
    }
</style>
{% endblock %}

{% block content %}
<div class="container mt-5 pt-4">
    <div class="row">
        <div class="col-lg-3">
            <div class="position-sticky" style="top: 100px;">
                <h5 class="text-primary mb-3">
                    <i class="fas fa-cogs"></i> Admin Panel
                </h5>
                <ul class="nav nav-pills flex-column">
                    <li class="nav-item">
                        <a class="nav-link" href="/admin">
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
                </ul>
            </div>
        </div>
        
        <div class="col-lg-9">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1 class="h2 text-white">
                    <i class="fas fa-edit text-primary"></i> Edit Article
                </h1>
                <span class="article-status {{ 'status-published' if article.published else 'status-draft' }}">
                    {% if article.published %}
                    <i class="fas fa-check-circle me-1"></i> Published
                    {% else %}
                    <i class="fas fa-pencil-alt me-1"></i> Draft
                    {% endif %}
                </span>
            </div>
            
            <form action="/admin/edit/{{ article.id }}" method="POST" class="write-form">
                <div class="mb-4">
                    <label for="title" class="form-label">Article Title</label>
                    <input type="text" class="form-control" id="title" name="title" 
                           value="{{ article.title }}" required>
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-6">
                        <label for="category" class="form-label">Category</label>
                        <select class="form-select" id="category" name="category" required>
                            <option value="Bitcoin" {{ 'selected' if article.category == 'Bitcoin' }}>Bitcoin</option>
                            <option value="DeFi" {{ 'selected' if article.category == 'DeFi' }}>DeFi</option>
                            <option value="Web3" {{ 'selected' if article.category == 'Web3' }}>Web3</option>
                            <option value="Mining" {{ 'selected' if article.category == 'Mining' }}>Mining</option>
                            <option value="Regulation" {{ 'selected' if article.category == 'Regulation' }}>Regulation</option>
                            <option value="Markets" {{ 'selected' if article.category == 'Markets' }}>Markets</option>
                            <option value="Technology" {{ 'selected' if article.category == 'Technology' }}>Technology</option>
                            <option value="Opinion" {{ 'selected' if article.category == 'Opinion' }}>Opinion</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="author" class="form-label">Author Name</label>
                        <input type="text" class="form-control" id="author" name="author" 
                               value="{{ article.author or '' }}">
                    </div>
                </div>
                
                <div class="mb-4">
                    <label for="content" class="form-label">Article Content</label>
                    <p class="text-muted small mb-2">You can use HTML for formatting. Use &lt;h2&gt; for headers, &lt;p&gt; for paragraphs, &lt;strong&gt; for bold.</p>
                    <textarea class="form-control" id="content-editor" name="content" required>{{ article.content }}</textarea>
                </div>
                
                <div class="mb-4">
                    <label for="seo_description" class="form-label">SEO Description (optional)</label>
                    <input type="text" class="form-control" id="seo_description" name="seo_description" 
                           value="{{ article.seo_description or '' }}" maxlength="155">
                </div>
                
                <div class="mb-4">
                    <label for="tags" class="form-label">Tags (optional)</label>
                    <input type="text" class="form-control" id="tags" name="tags" 
                           value="{{ article.tags or '' }}">
                </div>
                
                <div class="form-check mb-4">
                    <input class="form-check-input" type="checkbox" id="is_pressing" name="is_pressing" {{ 'checked' if article.is_pressing }}>
                    <label class="form-check-label text-white" for="is_pressing">
                        <i class="fas fa-bolt text-danger"></i> Mark as Breaking News
                    </label>
                </div>
                
                <div class="d-flex gap-3">
                    <button type="submit" name="action" value="publish" class="btn btn-publish">
                        <i class="fas fa-paper-plane me-2"></i> Update & Publish
                    </button>
                    <button type="submit" name="action" value="draft" class="btn btn-draft">
                        <i class="fas fa-save me-2"></i> Save as Draft
                    </button>
                    <a href="/admin" class="btn btn-outline-secondary">
                        <i class="fas fa-times me-2"></i> Cancel
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### templates/admin/generate_article.html
```html
{% extends "base.html" %} {% block title %}Generate{% endblock %} {% block content %} <h2>Generate Article</h2> <form action="/api/generate-article" method="post"><input name="topic"><button>Submit</button></form> {% endblock %}```

### templates/admin/social_monitor.html
```html
{% extends "base.html" %}
{% block title %}Social Monitor{% endblock %}
{% block content %}
<h2>Social Media Monitoring</h2>
<form method="post" action="/admin/social-monitor">
    <label>X Handles (comma-separated)</label>
    <input name="x_handles" value="CaitlinLong_,lopp,adam3us,woonomic,bitschmidty,LawrenceLepard,maxkeiser,jackmallers,TheBTCTherapist">
    <label>Subreddits</label>
    <input name="subreddits" value="cryptocurrency,bitcoin,ethtrader,satoshistreetbets,cryptomarkets,cryptotechnology,defi,altcoin">
    <label>Websites</label>
    <input name="websites" value="https://www.coindesk.com">
    <label>YouTube Handles (comma-separated)</label>
    <input name="youtube_handles" value="BitcoinMagazine,nataliebrunell,bytefederal,BTCSessions,SimplyBitcoin,CoinBureau,thejackmallersshow,RobertBreedlove22">
    <button>Update Sources</button>
</form>
<button onclick="fetch('/api/monitor-content').then(res => res.json()).then(data => { document.getElementById('trends').innerHTML = data.trends.map(t => `<p>${t.type}: ${t.title} <img src='${t.screenshot}'><br>OCR: ${t.screenshot_text}</p>`).join(''); })">Run Monitor</button>
<h3>Recent Trends</h3>
<div id="trends"></div>
{% endblock %}```

### templates/admin/write_article.html
```html
{% extends "base.html" %}

{% block title %}Write Article - Admin{% endblock %}

{% block extra_head %}
<style>
    .write-form {
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 2rem;
    }
    .form-label {
        color: #f7931a;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .form-control, .form-select {
        background: #0a0a0a;
        border: 1px solid #333;
        color: #fff;
        padding: 0.75rem 1rem;
    }
    .form-control:focus, .form-select:focus {
        background: #0a0a0a;
        border-color: #f7931a;
        color: #fff;
        box-shadow: 0 0 0 0.2rem rgba(247, 147, 26, 0.25);
    }
    .form-control::placeholder {
        color: #666;
    }
    #content-editor {
        min-height: 400px;
        font-family: 'DM Sans', sans-serif;
        line-height: 1.7;
    }
    .btn-publish {
        background: #f7931a;
        color: #000;
        font-weight: 700;
        padding: 0.75rem 2rem;
        border: none;
    }
    .btn-publish:hover {
        background: #ffa726;
        color: #000;
    }
    .btn-draft {
        background: transparent;
        color: #f7931a;
        border: 2px solid #f7931a;
        font-weight: 600;
        padding: 0.75rem 2rem;
    }
    .btn-draft:hover {
        background: rgba(247, 147, 26, 0.1);
        color: #f7931a;
    }
</style>
{% endblock %}

{% block content %}
<div class="container mt-5 pt-4">
    <div class="row">
        <div class="col-lg-3">
            <div class="position-sticky" style="top: 100px;">
                <h5 class="text-primary mb-3">
                    <i class="fas fa-cogs"></i> Admin Panel
                </h5>
                <ul class="nav nav-pills flex-column">
                    <li class="nav-item">
                        <a class="nav-link" href="/admin">
                            <i class="fas fa-tachometer-alt"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin/generate">
                            <i class="fas fa-robot"></i> AI Generate
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/admin/write">
                            <i class="fas fa-pen"></i> Write Article
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
                </ul>
            </div>
        </div>
        
        <div class="col-lg-9">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1 class="h2 text-white">
                    <i class="fas fa-pen text-primary"></i> Write Article
                </h1>
            </div>
            
            <form action="/admin/write" method="POST" class="write-form">
                <div class="mb-4">
                    <label for="title" class="form-label">Article Title</label>
                    <input type="text" class="form-control" id="title" name="title" 
                           placeholder="Enter a compelling headline..." required>
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-6">
                        <label for="category" class="form-label">Category</label>
                        <select class="form-select" id="category" name="category" required>
                            <option value="Bitcoin">Bitcoin</option>
                            <option value="DeFi">DeFi</option>
                            <option value="Web3">Web3</option>
                            <option value="Mining">Mining</option>
                            <option value="Regulation">Regulation</option>
                            <option value="Markets">Markets</option>
                            <option value="Technology">Technology</option>
                            <option value="Opinion">Opinion</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="author" class="form-label">Author Name</label>
                        <input type="text" class="form-control" id="author" name="author" 
                               placeholder="Your name or pen name" value="{{ current_user.username }}">
                    </div>
                </div>
                
                <div class="mb-4">
                    <label for="content" class="form-label">Article Content</label>
                    <p class="text-muted small mb-2">You can use HTML for formatting. Use &lt;h2&gt; for headers, &lt;p&gt; for paragraphs, &lt;strong&gt; for bold.</p>
                    <textarea class="form-control" id="content-editor" name="content" 
                              placeholder="Write your article content here..." required></textarea>
                </div>
                
                <div class="mb-4">
                    <label for="seo_description" class="form-label">SEO Description (optional)</label>
                    <input type="text" class="form-control" id="seo_description" name="seo_description" 
                           placeholder="Brief description for search engines (155 chars max)" maxlength="155">
                </div>
                
                <div class="mb-4">
                    <label for="tags" class="form-label">Tags (optional)</label>
                    <input type="text" class="form-control" id="tags" name="tags" 
                           placeholder="bitcoin, defi, lightning (comma separated)">
                </div>
                
                <div class="form-check mb-4">
                    <input class="form-check-input" type="checkbox" id="is_pressing" name="is_pressing">
                    <label class="form-check-label text-white" for="is_pressing">
                        <i class="fas fa-bolt text-danger"></i> Mark as Breaking News
                    </label>
                </div>
                
                <div class="d-flex gap-3">
                    <button type="submit" name="action" value="publish" class="btn btn-publish">
                        <i class="fas fa-paper-plane me-2"></i> Publish Now
                    </button>
                    <button type="submit" name="action" value="draft" class="btn btn-draft">
                        <i class="fas fa-save me-2"></i> Save as Draft
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

## Static Files (CSS/JS)

### static/css/coindesk-style.css
```css
/* CoinDesk-Style CSS for Protocol Pulse */

/* Global Styles */
body {
    background-color: #000;
    color: #fff;
    font-family: Arial, sans-serif;
    line-height: 1.6;
}

/* Header Styling */
header {
    background-color: #000;
    border-bottom: 1px solid #333;
}

/* Navigation Styling */
.navbar-brand {
    font-weight: bold;
    font-size: 1.5rem;
}

.navbar-nav .nav-link {
    color: #fff;
    font-weight: 500;
    margin: 0 0.5rem;
    transition: color 0.3s ease;
}

.navbar-nav .nav-link:hover {
    color: #00aaff;
}

/* Main Content */
.container {
    max-width: 1200px;
}

/* Card Styling */
.card {
    border: none;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.card-img-top {
    border-radius: 8px 8px 0 0;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    color: #333;
}

.lead {
    font-size: 1.1rem;
    color: #666;
}

/* Button Styling */
.btn {
    border-radius: 6px;
    font-weight: 500;
    padding: 0.5rem 1.5rem;
    transition: all 0.3s ease;
}

.btn-primary {
    background-color: #007bff;
    border-color: #007bff;
}

.btn-primary:hover {
    background-color: #0056b3;
    border-color: #0056b3;
    transform: translateY(-2px);
}

.btn-outline-light:hover {
    background-color: #f8f9fa;
    color: #333;
}

/* Search Form */
.form-control {
    border-radius: 6px;
    border: 1px solid #ddd;
}

.form-control:focus {
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
    border-color: #007bff;
}

/* Footer Styling */
footer {
    background-color: #000;
    border-top: 1px solid #333;
}

footer h5 {
    color: #f8f9fa;
    font-weight: 600;
}

footer p, footer li {
    color: #adb5bd;
}

footer a {
    color: #aaa;
    text-decoration: none;
    transition: color 0.3s ease;
}

footer a:hover {
    color: #fff;
}

/* Responsive Design */
@media (max-width: 768px) {
    .navbar-brand {
        font-size: 1.3rem;
    }
    
    .card {
        margin-bottom: 1rem;
    }
    
    .container {
        padding: 0 1rem;
    }
}

/* Animation Classes */
.fade-in {
    opacity: 0;
    animation: fadeIn 0.6s ease-in-out forwards;
}

@keyframes fadeIn {
    to {
        opacity: 1;
    }
}

/* Article-specific styles */
.article-content {
    font-size: 1.1rem;
    line-height: 1.8;
}

.article-meta {
    color: #666;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}

.article-title {
    color: #ffffff;
    font-weight: 700;
    margin-bottom: 1rem;
}

/* Card title styling for article cards */
.card-title {
    color: #ffffff !important;
}

.card-title a {
    color: #ffffff !important;
    text-decoration: none;
}

.card-title a:hover {
    color: #dc2626 !important;
}

/* Featured card titles - white text for dark theme */
.featured-card .card-title {
    color: #ffffff !important;
}

.featured-card .card-title a {
    color: #ffffff !important;
}

.featured-card .card-title a:hover {
    color: #dc2626 !important;
}

/* Featured card hover state - ensure text is readable on dark background */
.featured-card:hover .card-title,
.featured-card:hover .card-title a {
    color: #ffffff !important;
}

.featured-card:hover .card-title a:hover {
    color: #dc2626 !important;
}

.featured-card:hover .card-text,
.featured-card:hover .text-muted {
    color: #e0e0e0 !important;
}

/* Advertisement Styling - 2025 Standards */
.ad-container {
    position: relative;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    height: 100%;
}

.ad-container:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.ad-container a {
    text-decoration: none;
    color: inherit;
    display: block;
    height: 100%;
}

.ad-label {
    background: #6c757d;
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    position: relative;
}

.ad-label::before {
    content: "👑";
    margin-right: 0.25rem;
}

/* Sidebar Ad Styling */
.sidebar-ad {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease;
    margin-bottom: 1rem;
}

.sidebar-ad:hover {
    transform: translateY(-2px);
}

.sidebar-ad img {
    transition: transform 0.2s ease;
    border-radius: 6px;
}

.sidebar-ad:hover img {
    transform: scale(1.02);
}

.sidebar-ad a {
    text-decoration: none;
    color: inherit;
}

.sidebar-ad small {
    font-size: 0.75rem;
    color: #6c757d;
    font-weight: 500;
}

/* Responsive Advertisement Display */
@media (max-width: 991.98px) {
    .sidebar-ad {
        display: none;
    }
}

@media (max-width: 768px) {
    .ad-container {
        margin: 1rem 0;
    }
}

/* Hero Carousel Styling */
.hero-carousel {
    margin-bottom: 2rem;
}

.hero-carousel img {
    height: 400px;
    object-fit: cover;
}

.carousel-caption {
    background: rgba(0, 0, 0, 0.7);
    border-radius: 8px;
    padding: 1.5rem;
    left: 10%;
    right: 10%;
    bottom: 20px;
}

.carousel-caption h5 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.carousel-caption p {
    font-size: 1rem;
    margin-bottom: 1rem;
}

/* Article Grid Styling */
.article-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-top: 1rem;
}

.article-card {
    background: #222;
    padding: 10px;
    border-radius: 5px;
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.article-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.article-card img {
    width: 100%;
    height: 150px;
    object-fit: cover;
}

.article-card h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1rem;
    margin-bottom: 0.5rem;
}

.article-card h3 a {
    text-decoration: none;
    color: #333;
    transition: color 0.3s ease;
}

.article-card h3 a:hover {
    color: #007bff;
}

.article-card p {
    margin: 1rem;
    color: #666;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Sidebar Styling */
.sidebar {
    background: #111;
    padding: 15px;
    border-left: 1px solid #333;
}

.sidebar h3 {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: #333;
    border-bottom: 2px solid #007bff;
    padding-bottom: 0.5rem;
}

/* Market Widget */
.market-widget {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.crypto-price {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid #eee;
}

.crypto-price:last-child {
    border-bottom: none;
}

.crypto-name {
    font-weight: 600;
    color: #333;
}

.crypto-price-value {
    font-weight: 700;
    color: #333;
}

.crypto-change {
    font-size: 0.9rem;
    font-weight: 600;
}

.crypto-change.positive {
    color: #28a745;
}

.crypto-change.negative {
    color: #dc3545;
}

/* Featured Content */
.featured-content {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.featured-item {
    display: flex;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
}

.featured-item:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.featured-item img {
    width: 80px;
    height: 60px;
    object-fit: cover;
    border-radius: 4px;
    margin-right: 1rem;
}

.featured-item h4 {
    font-size: 0.9rem;
    font-weight: 600;
    margin: 0;
    line-height: 1.3;
}

.featured-item h4 a {
    text-decoration: none;
    color: #333;
    transition: color 0.3s ease;
}

.featured-item h4 a:hover {
    color: #007bff;
}

/* Responsive Design */
@media (max-width: 768px) {
    .sidebar {
        padding-left: 0;
        margin-top: 2rem;
    }
    
    .carousel-caption {
        left: 5%;
        right: 5%;
    }
    
    .carousel-caption h5 {
        font-size: 1.2rem;
    }
    
    .article-grid {
        grid-template-columns: 1fr;
    }
}

.screenshot { 
    max-width: 100%; 
    height: auto; 
    border: 1px solid #333; 
    margin-bottom: 20px; 
}```

### static/css/news-layout.css
```css
/* Professional News Site Layout Styles */

/* News Article Cards */
.news-article-card {
    background: white;
    transition: transform 0.2s ease;
    border-radius: 0 !important;
}

.news-article-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
}

.news-image-container {
    height: 250px;
    overflow: hidden;
    background: #f8f9fa;
}

.news-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
}

.news-image:hover {
    transform: scale(1.05);
}

.news-content {
    padding: 1.5rem !important;
}

.news-meta {
    border-bottom: 1px solid #eee;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem !important;
}

.news-category {
    font-size: 0.75rem;
    letter-spacing: 0.5px;
    font-weight: 600 !important;
}

.news-time {
    font-size: 0.75rem;
}

.news-headline {
    font-size: 1.25rem;
    line-height: 1.3;
    font-weight: 600;
    margin-bottom: 1rem !important;
}

.news-headline a:hover {
    color: #dc2626 !important;
}

.news-excerpt {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #6b7280 !important;
}

.read-more-link {
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-decoration: none !important;
}

.read-more-link:hover {
    text-decoration: underline !important;
}

/* Latest News Cards */
.latest-news-card {
    border-radius: 0 !important;
    transition: transform 0.2s ease;
    border: 1px solid #e5e7eb !important;
}

.latest-news-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.latest-image-container {
    height: 180px;
    overflow: hidden;
    background: #f8f9fa;
}

.latest-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
}

.latest-image:hover {
    transform: scale(1.05);
}

.latest-content {
    padding: 1rem !important;
}

.latest-meta {
    margin-bottom: 0.75rem !important;
}

.latest-category {
    font-size: 0.7rem;
    letter-spacing: 0.5px;
    font-weight: 600 !important;
}

.latest-time {
    font-size: 0.7rem;
}

.latest-headline {
    font-size: 1rem;
    line-height: 1.3;
    font-weight: 600;
    margin-bottom: 0.75rem !important;
}

.latest-headline a:hover {
    color: #dc2626 !important;
}

.latest-excerpt {
    font-size: 0.85rem;
    line-height: 1.5;
    color: #6b7280 !important;
}

/* Typography improvements */
.tracking-wide {
    letter-spacing: 0.025em;
}

/* Professional section styling */
.section-divider {
    border-bottom: 3px solid #dc2626;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #1f2937;
}

/* Article detail page improvements */
.article-header-professional {
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 2rem;
    margin-bottom: 2rem;
}

.article-image-hero {
    height: 400px;
    overflow: hidden;
    margin-bottom: 2rem;
    background: #f8f9fa;
}

.article-image-hero img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}```

### static/css/style.css
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

/* Navigation */
.navbar-dark .navbar-brand {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.5px;
}

.navbar-dark .navbar-nav .nav-link {
    font-weight: 500;
    transition: color 0.3s ease;
}

.navbar-dark .navbar-nav .nav-link:hover {
    color: var(--primary-color) !important;
}

/* Content Wrapper */
.content-wrapper {
    margin-top: 80px;
    min-height: calc(100vh - 200px);
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
        margin-top: 76px; /* Optimized for mobile navbar */
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
```

### static/js/articles.js
```javascript
// Auto-refresh functionality for articles page
let refreshInterval;
let isRefreshing = false;

// Initialize auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Articles auto-refresh initialized');
    startAutoRefresh();
});

function startAutoRefresh() {
    // Refresh every 60 seconds (60000 milliseconds)
    refreshInterval = setInterval(() => {
        if (!isRefreshing) {
            refreshArticles();
        }
    }, 60000);
    
    console.log('Auto-refresh started - will update every 60 seconds');
}

function refreshArticles() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    console.log('Fetching latest articles...');
    
    fetch('/api/latest-articles')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateGrid(data.articles);
                showRefreshIndicator();
                console.log(`Updated grid with ${data.count} articles`);
            } else {
                console.error('Failed to fetch articles:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching articles:', error);
        })
        .finally(() => {
            isRefreshing = false;
        });
}

function updateGrid(articles) {
    if (!articles || articles.length === 0) {
        console.log('No articles to display');
        return;
    }
    
    // Update hero article (first article)
    updateHeroArticle(articles[0]);
    
    // Update article grid (remaining articles)
    if (articles.length > 1) {
        updateArticleGrid(articles.slice(1));
    }
}

function updateHeroArticle(article) {
    const heroSection = document.querySelector('.hero-article');
    if (!heroSection) return;
    
    // Calculate if article is pressing
    const createdAt = new Date(article.created_at);
    const now = new Date();
    const hoursDiff = (now - createdAt) / (1000 * 60 * 60);
    const isPressing = hoursDiff < 1;
    
    const pressingBadge = isPressing ? 
        '<span class="pressing-badge"><i class="fas fa-bolt"></i> PRESSING</span>' : '';
    
    heroSection.innerHTML = `
        <div class="hero-meta">
            <span class="hero-category">${article.category}</span>
            ${pressingBadge}
            <span class="card-time">${article.created_at}</span>
        </div>
        
        <h1><a href="${article.url}" class="text-decoration-none text-dark">${article.title}</a></h1>
        
        ${article.header_image_url ? `<img src="${article.header_image_url}" alt="${article.title}">` : ''}
        
        <p>${article.summary}</p>
        
        <a href="${article.url}" class="btn btn-danger">
            Read Full Story <i class="fas fa-arrow-right ms-1"></i>
        </a>
    `;
}

function updateArticleGrid(articles) {
    const gridContainer = document.getElementById('articleGrid');
    if (!gridContainer) return;
    
    gridContainer.innerHTML = '';
    
    articles.forEach((article, index) => {
        const cardClass = index < 2 ? 'medium' : 'small';
        
        // Calculate if article is pressing
        const createdAt = new Date(article.created_at);
        const now = new Date();
        const hoursDiff = (now - createdAt) / (1000 * 60 * 60);
        const isPressing = hoursDiff < 1;
        
        const pressingBadge = isPressing ? 
            '<span class="pressing-badge"><i class="fas fa-bolt"></i> PRESSING</span>' : '';
        
        const cardHTML = `
            <article class="article-card ${cardClass}">
                ${article.header_image_url ? 
                    `<img src="${article.header_image_url}" alt="${article.title}" class="card-image">` : 
                    ''
                }
                
                <div class="card-content">
                    <div class="card-meta">
                        <span class="card-category">${article.category}</span>
                        ${pressingBadge}
                        <span class="card-time">${formatDate(article.created_at)}</span>
                    </div>
                    
                    <h3 class="card-title">
                        <a href="${article.url}">
                            ${article.title}
                        </a>
                    </h3>
                    
                    <p class="card-excerpt">
                        ${article.summary}
                    </p>
                </div>
            </article>
        `;
        
        gridContainer.innerHTML += cardHTML;
    });
}

function showRefreshIndicator() {
    const indicator = document.getElementById('refreshIndicator');
    if (indicator) {
        indicator.classList.add('show');
        
        // Hide after 2 seconds
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 2000);
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

// Manual refresh function (can be called from UI if needed)
function manualRefresh() {
    console.log('Manual refresh triggered');
    refreshArticles();
}

// Stop auto-refresh (useful for debugging or when leaving page)
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
        console.log('Auto-refresh stopped');
    }
}

// Restart auto-refresh
function restartAutoRefresh() {
    stopAutoRefresh();
    startAutoRefresh();
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});```

### static/js/coindesk.js
```javascript
// CoinDesk-Style JavaScript for Protocol Pulse

document.addEventListener('DOMContentLoaded', function() {
    // Initialize smooth scrolling
    initSmoothScrolling();
    
    // Initialize search functionality
    initSearch();
    
    // Initialize article animations
    initAnimations();
    
    // Carousel rotation (already in Bootstrap, but add auto if needed)
    const heroSlider = document.getElementById('heroSlider');
    if (heroSlider) {
        new bootstrap.Carousel(heroSlider, { interval: 5000 });
    }

    // Grid refresh (every 60s fetch new articles)
    function refreshGrid() {
        fetch('/api/latest-articles')
            .then(res => res.json())
            .then(data => {
                // Update DOM with new articles (simplified)
                const grid = document.querySelector('.article-grid');
                if (grid) {
                    grid.innerHTML = '';  // Clear and repopulate
                    data.forEach(article => {
                        grid.innerHTML += `<div class="article-card"><img src="${article.header_image_url || '/static/images/placeholder.jpg'}" alt="${article.title}"><h3><a href="/articles/${article.id}">${article.title}</a></h3><p>${article.summary ? article.summary.substring(0, 150) : 'Web3 news update'}...</p></div>`;
                    });
                }
            })
            .catch(error => {
                console.log('Grid refresh failed:', error);
            });
    }
    setInterval(refreshGrid, 60000);  // 60s
    
    // Initialize ad cycling (only on article pages)
    if (document.querySelector('.ad-container, .sidebar-ad')) {
        setInterval(cycleAds, 10000);
    }
});

function initSmoothScrolling() {
    // Add smooth scrolling to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            // Check if href is valid (not just '#')
            if (href && href !== '#') {
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
}

function initSearch() {
    const searchForm = document.querySelector('form.d-flex');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchInput = this.querySelector('input[type="search"]');
            const searchTerm = searchInput.value.trim();
            
            if (searchTerm) {
                // Redirect to articles page with search query
                window.location.href = `/articles?search=${encodeURIComponent(searchTerm)}`;
            }
        });
    }
}

function initAnimations() {
    // Add fade-in animation to cards on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    // Observe all cards
    document.querySelectorAll('.card').forEach(card => {
        observer.observe(card);
    });
}

// Advertisement cycling functionality (only for article pages)
function cycleAds() {
    // Only run if we're on a page with ads
    if (!document.querySelector('.ad-container, .sidebar-ad')) {
        return;
    }
    
    fetch('/api/active-ads')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.ads && data.ads.length > 0) {
                const adContainers = document.querySelectorAll('.ad-container, .sidebar-ad');
                
                adContainers.forEach(container => {
                    const link = container.querySelector('a');
                    const img = container.querySelector('img');
                    const label = container.querySelector('.ad-label, small');
                    
                    if (link && img && data.ads.length > 1) {
                        // Fade out current ad
                        container.style.transition = 'opacity 0.5s ease';
                        container.style.opacity = '0.3';
                        
                        setTimeout(() => {
                            // Get random ad
                            const randomAd = data.ads[Math.floor(Math.random() * data.ads.length)];
                            
                            // Update ad content
                            link.href = randomAd.target_url;
                            img.src = randomAd.image_url;
                            img.alt = randomAd.name;
                            
                            // Fade in new ad
                            container.style.opacity = '1';
                        }, 250);
                    }
                });
            }
        })
        .catch(error => {
            console.log('Ad cycling error:', error);
        });
}

// Utility function for responsive navigation
function toggleMobileMenu() {
    const navbarCollapse = document.querySelector('.navbar-collapse');
    if (navbarCollapse) {
        navbarCollapse.classList.toggle('show');
    }
}

// Add click handler for mobile menu toggle
document.addEventListener('click', function(e) {
    if (e.target.closest('.navbar-toggler')) {
        toggleMobileMenu();
    }
});

// Close mobile menu when clicking outside
document.addEventListener('click', function(e) {
    const navbar = document.querySelector('.navbar');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbar && navbarCollapse && !navbar.contains(e.target)) {
        navbarCollapse.classList.remove('show');
    }
});

// Enhanced button hover effects
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
    });
    
    btn.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Form validation enhancement
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = this.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        if (!isValid) {
            e.preventDefault();
        }
    });
});```

### static/js/main.js
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    let particles = [];

    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 5 + 1;
            this.speedX = Math.random() * 3 - 1.5;
            this.speedY = Math.random() * 3 - 1.5;
            this.color = 'rgba(220, 38, 38, 0.5)';
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            if (this.size > 0.2) this.size -= 0.1;
        }
        draw() {
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (particles.length < 100) particles.push(new Particle());
        particles.forEach((p, i) => {
            p.update();
            p.draw();
            if (p.size <= 0.2) particles.splice(i, 1);
        });
        requestAnimationFrame(animate);
    }

    function wave() {
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        for (let i = 0; i < canvas.width; i++) {
            ctx.lineTo(i, canvas.height / 2 + Math.sin(i * 0.01 + Date.now() * 0.001) * 20);
        }
        ctx.strokeStyle = 'rgba(220, 38, 38, 0.3)';
        ctx.stroke();
    }

    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });

    animate();
    setInterval(wave, 100);
    
    // Advertisement cycling functionality
    setInterval(cycleAds, 10000);
});

// Cycle advertisements with fade effect
function cycleAds() {
    fetch('/api/active-ads')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.ads && data.ads.length > 0) {
                const adContainers = document.querySelectorAll('.ad-container, .sidebar-ad');
                
                adContainers.forEach(container => {
                    const link = container.querySelector('a');
                    const img = container.querySelector('img');
                    const label = container.querySelector('.ad-label, small');
                    
                    if (link && img && data.ads.length > 1) {
                        // Fade out current ad
                        container.style.transition = 'opacity 0.5s ease';
                        container.style.opacity = '0.3';
                        
                        setTimeout(() => {
                            // Get random ad
                            const randomAd = data.ads[Math.floor(Math.random() * data.ads.length)];
                            
                            // Update ad content
                            link.href = randomAd.target_url;
                            img.src = randomAd.image_url;
                            img.alt = randomAd.name;
                            
                            // Fade in new ad
                            container.style.opacity = '1';
                        }, 250);
                    }
                });
            }
        })
        .catch(error => {
            console.log('Ad cycling error:', error);
        });
}```

