from flask import render_template, request, jsonify, redirect, url_for, flash, make_response, session, Response, abort, send_file
from flask_login import login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db, limiter, cache

# --- CIRCULAR IMPORT FIX ---
# Instead of 'from models import ...', we import the module itself.
import models 

import hashlib
import json
import logging
import requests
import os
import re
import uuid
from functools import wraps
from datetime import datetime, timedelta
import threading

# Import services
# Note: Ensure these services are also using relative imports if they cause loops
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.content_generator import ContentGenerator
from services.content_engine import ContentEngine
try:
    from services.substack_service import SubstackService
except ModuleNotFoundError:
    SubstackService = None
from services.newsletter import newsletter_service
try:
    from services.rss_service import RSSService
except ModuleNotFoundError:
    RSSService = None
from services.printful_service import PrintfulService
from services.price_service import price_service
from services.youtube_service import YouTubeService
from services.node_service import NodeService
from services.ghl_service import ghl_service

ADMIN_SECRET = os.environ.get('ADMIN_SECRET', '')

# ─── Sentiment classification trigger (LAW 1: classify within 60s of publish) ───

def _trigger_sentiment_classification(article_id: int):
    """
    Spin up a background thread to classify the article.
    Uses Flask app context so DB writes work correctly.
    Non-blocking — returns immediately.
    """
    def _classify_worker(aid):
        import time as _time
        _time.sleep(2)  # brief delay to let the DB commit settle
        try:
            from services.sentiment_analyzer import classify_article
            result = classify_article(aid)
            if result:
                logging.info("Sentiment classification complete: article %s → %s", aid, result.get("sentiment"))
        except Exception as e:
            logging.error("Background sentiment classification failed for article %s: %s", aid, e)

    t = threading.Thread(target=_classify_worker, args=(article_id,), daemon=True)
    t.start()


def _startup_batch_classify():
    """Run on app startup: classify any unclassified articles from last 24h."""
    def _batch_worker():
        import time as _time
        _time.sleep(10)  # wait for app to finish starting up
        try:
            from services.sentiment_analyzer import batch_classify
            result = batch_classify(hours=24)
            logging.info("Startup batch classify: %s", result)
        except Exception as e:
            logging.error("Startup batch classify failed: %s", e)

    t = threading.Thread(target=_batch_worker, daemon=True)
    t.start()


# Fire startup batch classify once (non-blocking)
_startup_batch_classify()


# Initialize services
ai_service = AIService()
reddit_service = RedditService()
content_generator = ContentGenerator()
content_engine = ContentEngine()
if SubstackService is not None:
    try:
        substack_service = SubstackService()
    except Exception as e:
        logging.warning("Substack service initialization failed: %s", e)
        substack_service = None
else:
    substack_service = None
    logging.warning("Substack service not available (module not found)")

rss_service = RSSService() if RSSService is not None else None
printful_service = PrintfulService()

from services.transcript_service import get_space_transcript, summarize_for_tweet

def admin_required(f):
    """Decorator to enforce admin role-based access control"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def premium_required(f):
    """Require Commander ($99/mo) or higher for premium hub access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('login') + '?next=' + request.path)
        if not getattr(current_user, 'has_commander_tier', lambda: False)():
            flash('Premium Hub requires a Commander ($99/mo) subscription.')
            return redirect(url_for('premium_page'))
        return f(*args, **kwargs)
    return decorated_function


def premium_hub_required(f):
    """Require any paid tier (Operator / Commander / Sovereign) for hub access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('login') + '?next=' + request.path)
        if not getattr(current_user, 'has_premium', lambda: False)():
            flash('Premium Hub requires a paid subscription (Operator $21/mo or higher).')
            return redirect(url_for('premium_page'))
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


def _require_csrf():
    """Abort 400 if POST CSRF token is missing or does not match session."""
    if request.method != "POST":
        return
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token or not session.get("csrf_token") or token != session.get("csrf_token"):
        abort(400, "Invalid or missing CSRF token")


@app.route('/debug-routes')
def debug_routes():
    """List all registered URL rules (for 404 debugging: confirm / is in the app that is actually running)."""
    rules = [{"rule": r.rule, "endpoint": r.endpoint, "methods": list(r.methods - {"HEAD", "OPTIONS"})}
             for r in app.url_map.iter_rules()]
    return jsonify({"app": "Protocol Pulse", "rules": sorted(rules, key=lambda x: x["rule"])})


@app.route('/health')
def health():
    """Liveness: app is up. Used by load balancers and Render."""
    return jsonify({"status": "ok", "service": "protocol-pulse"}), 200


@app.route('/ready')
def ready():
    """Readiness: app and DB are responsive. Used by orchestrators before sending traffic."""
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ready", "db": "ok"}), 200
    except Exception as e:
        logging.warning("Ready check failed: %s", e)
        return jsonify({"status": "not_ready", "db": "error"}), 503


@app.route('/robots.txt', endpoint='robots_txt_core')
def robots_txt():
    """Search engine crawler instructions."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /api/",
        "Disallow: /hub",
        "Disallow: /login",
        "Disallow: /signup",
        "",
        "Sitemap: " + (request.url_root.rstrip("/") + "/sitemap.xml"),
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route('/sitemap.xml')
def sitemap_xml():
    """Simple sitemap for SEO: home, articles, key public pages."""
    base = request.url_root.rstrip("/")
    pages = [
        ("/", "daily", "1.0"),
        ("/articles", "daily", "0.9"),
        ("/dossier", "weekly", "0.9"),
        ("/live", "daily", "0.8"),
        ("/whale-watcher", "daily", "0.8"),
        ("/map", "weekly", "0.7"),
        ("/about", "monthly", "0.5"),
        ("/contact", "monthly", "0.5"),
        ("/donate", "monthly", "0.5"),
        ("/donate/bitcoin", "monthly", "0.5"),
        ("/premium", "monthly", "0.6"),
        ("/privacy-policy", "monthly", "0.3"),
    ]
    try:
        articles = models.Article.query.filter_by(published=True).order_by(models.Article.updated_at.desc()).limit(500).all()
    except Exception:
        articles = []
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for path, changefreq, priority in pages:
        out.append(f"  <url><loc>{base}{path}</loc><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>")
    for a in articles:
        lastmod = getattr(a, "updated_at", None) or getattr(a, "created_at", None)
        lastmod_str = lastmod.strftime("%Y-%m-%d") if lastmod else ""
        out.append(f"  <url><loc>{base}/articles/{a.id}</loc><changefreq>weekly</changefreq><priority>0.7</priority><lastmod>{lastmod_str}</lastmod></url>")
    out.append("</urlset>")
    return Response("\n".join(out), mimetype="application/xml")

def _index_cache_key():
    from flask_login import current_user
    return "index_" + (str(current_user.id) if current_user.is_authenticated else "anon")


@app.route('/')
@cache.cached(timeout=60, key_prefix=_index_cache_key)
def index():
    """Homepage with featured articles, segment-based Bento-box ranking"""
    featured_articles = models.Article.query.filter_by(published=True, featured=True).order_by(models.Article.created_at.desc()).limit(3).all()
    recent_articles = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(6).all()
    featured_podcasts = models.Podcast.query.filter_by(featured=True).order_by(models.Podcast.published_date.desc()).limit(3).all()
    
    # Fetch live cryptocurrency prices
    prices = price_service.get_prices()
    
    # Generate Today's Signal briefing (120 words max)
    todays_signal = generate_todays_signal()
    
    # Segment-based Bento-box ranking
    user_segment = 'general'
    bento_categories = []
    if current_user.is_authenticated:
        segment = models.UserSegment.query.filter_by(user_id=current_user.id).first()
        if segment:
            user_segment = segment.segment_type
            # Miners prioritize hashrate/mining content
            if segment.segment_type == 'miner':
                bento_categories = ['mining', 'hashrate', 'bitcoin', 'difficulty']
            # Institutions prioritize macro/regulatory content
            elif segment.segment_type == 'institution':
                bento_categories = ['regulation', 'macro', 'bitcoin', 'etf']
            # Traders prioritize price/trading content
            elif segment.segment_type == 'trader':
                bento_categories = ['trading', 'price', 'defi', 'bitcoin']
            # Developers prioritize technical content
            elif segment.segment_type == 'developer':
                bento_categories = ['innovation', 'lightning', 'privacy', 'bitcoin']
    
    # Get segment-specific content for Bento-box
    bento_articles = []
    if bento_categories:
        for category in bento_categories[:2]:
            cat_articles = models.Article.query.filter(
                models.Article.published == True,
                models.Article.category.ilike(f'%{category}%')
            ).order_by(models.Article.created_at.desc()).limit(2).all()
            bento_articles.extend(cat_articles)
    
    # Build article_image_urls for carousel/cards
    import os as _os
    default_header_url = "/static/images/default-header.png"
    article_image_urls = {}
    for a in list(featured_articles) + list(recent_articles):
        if a.id in article_image_urls:
            continue
        ciu = (getattr(a, "cover_image_url", None) or "").strip()
        if ciu and (ciu.startswith("http") or (ciu.startswith("/static/") and "default-header" not in ciu)):
            article_image_urls[a.id] = ciu
            continue
        url = (getattr(a, "header_image_url", None) or "").strip()
        if url and url.startswith("http"):
            article_image_urls[a.id] = url
        elif url and url != default_header_url:
            filepath = url.lstrip("/")
            if _os.path.exists(filepath):
                article_image_urls[a.id] = url
            else:
                article_image_urls[a.id] = default_header_url
        else:
            article_image_urls[a.id] = default_header_url

    return render_template('index.html',
                         featured_articles=featured_articles,
                         recent_articles=recent_articles,
                         featured_podcasts=featured_podcasts,
                         prices=prices,
                         price_service=price_service,
                         todays_signal=todays_signal,
                         user_segment=user_segment,
                         bento_articles=bento_articles[:4],
                         article_image_urls=article_image_urls,
                         default_header_url=default_header_url)

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

@app.route('/bitfeed-live')
@app.route('/kinetic')
@app.route('/gravity-well')
def kinetic_terminal():
    """Redirect to Live Terminal - Sovereign Uplift Terminal with Three.js"""
    from flask import redirect
    return redirect('/live')

@app.route('/hud')
def predictive_hud():
    """Predictive HUD - AI-powered network predictions for miners and traders"""
    return render_template('predictive_hud.html')

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
    import requests
    
    # Fetch last 5 high-value transactions (>10 BTC) from database
    initial_whales = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.btc_amount >= 10
    ).order_by(models.WhaleTransaction.detected_at.desc()).limit(5).all()
    
    whale_data = [{
        'txid': w.txid,
        'btc_amount': w.btc_amount,
        'usd_value': w.usd_value,
        'fee_sats': w.fee_sats,
        'block_height': w.block_height,
        'detected_at': w.detected_at.isoformat() if w.detected_at else None,
        'is_mega': w.is_mega
    } for w in initial_whales]
    
    # If we have fewer than 5 transactions, fetch real ones from mempool.space
    if len(whale_data) < 5:
        try:
            # Get recent blocks to find real whale transactions
            blocks_resp = requests.get('https://mempool.space/api/blocks', timeout=10)
            if blocks_resp.status_code == 200:
                blocks = blocks_resp.json()[:3]
                existing_txids = {w['txid'] for w in whale_data}
                
                for block in blocks:
                    if len(whale_data) >= 5:
                        break
                    block_time = block.get('timestamp', 0) * 1000
                    block_height = block.get('height')
                    
                    try:
                        txs_resp = requests.get(
                            f"https://mempool.space/api/block/{block['id']}/txs/0",
                            timeout=10
                        )
                        if txs_resp.status_code == 200:
                            for tx in txs_resp.json():
                                if len(whale_data) >= 5:
                                    break
                                outputs = tx.get('vout', [])
                                total_out = sum(out.get('value', 0) for out in outputs)
                                btc_value = total_out / 100000000
                                
                                if btc_value >= 10 and tx['txid'] not in existing_txids:
                                    whale_data.append({
                                        'txid': tx['txid'],
                                        'btc_amount': round(btc_value, 4),
                                        'usd_value': round(btc_value * 100000, 2),
                                        'fee_sats': tx.get('fee', 0),
                                        'block_height': block_height,
                                        'detected_at': datetime.utcnow().isoformat(),
                                        'is_mega': btc_value >= 500
                                    })
                                    existing_txids.add(tx['txid'])
                    except Exception as e:
                        logging.warning(f"Error fetching block txs: {e}")
                        continue
        except Exception as e:
            logging.error(f"Error fetching fallback whales: {e}")
    
    # Verified historical whale transactions for fallback (real Bitcoin txids)
    # These are actual large Bitcoin transactions that can be verified on mempool.space
    historical_whales = [
        {'txid': '8f907925d2ebe48765103e6845c06f1f2bb77c6adc1cc002865865eb5cfd5c1c', 'btc_amount': 44000.0, 'usd_value': 4400000000, 'fee_sats': 36000, 'block_height': 792678, 'detected_at': '2023-07-17T12:00:00', 'is_mega': True},
        {'txid': 'a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d', 'btc_amount': 10000.0, 'usd_value': 1000000000, 'fee_sats': 5000, 'block_height': 57043, 'detected_at': '2010-05-22T00:00:00', 'is_mega': True},
        {'txid': 'e9a66845e05d5abc0ad04ec80f774a7e585c6e8db975962d069a522137b80c1d', 'btc_amount': 11501.0, 'usd_value': 1150100000, 'fee_sats': 18900, 'block_height': 634150, 'detected_at': '2020-06-15T08:30:00', 'is_mega': True},
        {'txid': '4410c8d14ff9f87ceeed1d65cb58e7c7b2422b2d7529a9c4c95c0e4d1b8e0eca', 'btc_amount': 2500.0, 'usd_value': 250000000, 'fee_sats': 12500, 'block_height': 710000, 'detected_at': '2021-12-01T14:00:00', 'is_mega': True},
        {'txid': 'f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16', 'btc_amount': 50.0, 'usd_value': 5000000, 'fee_sats': 0, 'block_height': 170, 'detected_at': '2009-01-12T00:00:00', 'is_mega': False}
    ]
    
    # Top up to exactly 5 transactions using historical fallback
    existing_txids = {w['txid'] for w in whale_data}
    for hw in historical_whales:
        if len(whale_data) >= 5:
            break
        if hw['txid'] not in existing_txids:
            whale_data.append(hw)
    
    return render_template('whale_watcher.html', initial_whales=whale_data)

@app.route('/bitfeed-live')
@app.route('/bitfeed-ultimate')
def bitfeed_ultimate():
    """Ultimate Bitfeed Visualizer - Blocks assemble into B, explode on new block"""
    return render_template('bitfeed_ultimate.html')

# =====================================
# VALUE STREAM - Decentralized Social Aggregator
# =====================================

@app.route('/value-stream')
def value_stream():
    """Value Stream - Sovereign Intelligence Market"""
    default_pulse = {'value': 0, 'label': 'Neutral', 'zap_volume_24h': 0, 'posts_with_zaps_24h': 0, 'ratio': 0}
    try:
        from services.value_stream_service import value_stream_service

        platform = request.args.get('platform')
        posts = value_stream_service.get_value_stream(limit=50, platform=platform)
        curators = value_stream_service.get_top_curators(limit=10)

        post_objects = []
        for p in posts:
            post = models.CuratedPost.query.get(p['id'])
            if post:
                post_objects.append(post)

        curator_objects = []
        for c in curators:
            curator = models.ValueCreator.query.get(c['id'])
            if curator:
                curator_objects.append(curator)

        total_sats = db.session.query(db.func.coalesce(db.func.sum(models.CuratedPost.total_sats), 0)).scalar() or 0
        sats_per_hour = db.session.query(db.func.coalesce(db.func.sum(models.ZapEvent.amount_sats), 0)).filter(
            models.ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).scalar() or 0

        try:
            from services.pulse_nexus_service import compute_market_pulse
            market_pulse = compute_market_pulse()
        except Exception:
            market_pulse = default_pulse

        return render_template('value_stream.html',
                              posts=post_objects,
                              curators=curator_objects,
                              selected_platform=platform,
                              total_sats=int(total_sats),
                              sats_per_hour=int(sats_per_hour),
                              market_pulse=market_pulse)
    except Exception as e:
        logging.exception("value_stream route failed: %s", e)
        return render_template('value_stream.html',
                              posts=[],
                              curators=[],
                              selected_platform=request.args.get('platform'),
                              total_sats=0,
                              sats_per_hour=0,
                              market_pulse=default_pulse)

@app.route('/signal-terminal')
def signal_terminal():
    """Signal Terminal — redirects to /terminal (Bloomberg-grade rebuild)."""
    return redirect(url_for('pulse_terminal'))

@app.route('/api/value-stream/post/<int:post_id>')
def api_get_post_details(post_id):
    """Get detailed post info for Signal Terminal inspector"""
    from datetime import datetime, timedelta
    
    post = models.CuratedPost.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'error': 'Post not found'})
    
    hours_ago = (datetime.utcnow() - post.submitted_at).total_seconds() / 3600
    if hours_ago < 1:
        age_display = f"{int(hours_ago * 60)}m ago"
    elif hours_ago < 24:
        age_display = f"{int(hours_ago)}h ago"
    else:
        age_display = f"{int(hours_ago / 24)}d ago"
    
    velocity = 0
    recent_zaps = models.ZapEvent.query.filter(
        models.ZapEvent.post_id == post_id,
        models.ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).count()
    velocity = recent_zaps
    
    boost_sats = 0
    if hasattr(post, 'boosts'):
        boost_sats = sum(b.amount for b in post.boosts if b.active)
    
    return jsonify({
        'success': True,
        'post': {
            'id': post.id,
            'title': post.title or 'Untitled Signal',
            'platform': post.platform,
            'original_url': post.original_url,
            'original_id': post.original_id,
            'total_sats': post.total_sats or 0,
            'zap_count': post.zap_count or 0,
            'boost_sats': boost_sats,
            'signal_score': round(post.signal_score or 0, 2),
            'curator_name': post.curator.display_name if post.curator else 'Anonymous',
            'creator_name': post.creator.display_name if post.creator else None,
            'age_display': age_display,
            'velocity': velocity,
            'thumbnail_url': post.thumbnail_url
        }
    })

@app.route('/api/signal-terminal/stream')
def signal_terminal_stream():
    """SSE endpoint for real-time Signal Terminal updates with heartbeat"""
    from datetime import datetime, timedelta
    import time
    import json
    
    def generate():
        last_check = datetime.utcnow()
        heartbeat_count = 0
        max_runtime = 300
        start_time = time.time()
        
        while time.time() - start_time < max_runtime:
            try:
                with app.app_context():
                    new_posts = models.CuratedPost.query.filter(
                        models.CuratedPost.submitted_at > last_check
                    ).order_by(models.CuratedPost.signal_score.desc()).limit(10).all()
                    
                    new_zaps = models.ZapEvent.query.filter(
                        models.ZapEvent.created_at > last_check
                    ).order_by(models.ZapEvent.created_at.desc()).limit(20).all()
                    
                    if new_posts:
                        for post in new_posts:
                            velocity = models.ZapEvent.query.filter(
                                models.ZapEvent.post_id == post.id,
                                models.ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
                            ).count()
                            
                            post_data = {
                                'type': 'new_post',
                                'id': post.id,
                                'title': post.title or 'Untitled Signal',
                                'platform': post.platform,
                                'total_sats': post.total_sats or 0,
                                'zap_count': post.zap_count or 0,
                                'signal_score': round(post.signal_score or 0, 2),
                                'velocity': velocity
                            }
                            yield f"data: {json.dumps(post_data)}\n\n"
                    
                    if new_zaps:
                        for zap in new_zaps:
                            zap_data = {
                                'type': 'new_zap',
                                'post_id': zap.post_id,
                                'amount': zap.amount_sats
                            }
                            yield f"data: {json.dumps(zap_data)}\n\n"
                    
                    last_check = datetime.utcnow()
                
                heartbeat_count += 1
                if heartbeat_count % 3 == 0:
                    yield f": heartbeat {heartbeat_count}\n\n"
                
                time.sleep(5)
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
        
        yield f"data: {json.dumps({'type': 'reconnect', 'reason': 'timeout'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})

@app.route('/api/value-stream/submit', methods=['POST'])
def api_submit_content():
    """API endpoint for submitting curated content"""
    from services.value_stream_service import value_stream_service
    import re
    
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    title = data.get('title', '')[:500]
    
    if not url:
        return jsonify({'success': False, 'error': 'URL required'})
    
    if not re.match(r'^https?://', url):
        return jsonify({'success': False, 'error': 'Invalid URL format'})
    
    if len(url) > 2000:
        return jsonify({'success': False, 'error': 'URL too long'})
    
    curator_id = None
    if current_user.is_authenticated:
        creator = models.ValueCreator.query.filter_by(
            twitter_handle=current_user.username
        ).first()
        if creator:
            curator_id = creator.id
        else:
            new_creator = models.ValueCreator(
                display_name=current_user.username,
                twitter_handle=current_user.username
            )
            db.session.add(new_creator)
            db.session.commit()
            curator_id = new_creator.id
    
    result = value_stream_service.submit_content(url, curator_id, title)
    return jsonify(result)

@app.route('/api/value-stream/zap/<int:post_id>', methods=['POST'])
def api_zap_content(post_id):
    """API endpoint for zapping content"""
    from services.value_stream_service import value_stream_service
    
    data = request.get_json() or {}
    amount = data.get('amount_sats', 1000)
    payment_hash = data.get('payment_hash')
    sender_id = data.get('sender_id')
    
    result = value_stream_service.process_zap(post_id, sender_id, amount, payment_hash)
    return jsonify(result)

@app.route('/api/value-stream/invoice/<int:post_id>', methods=['POST'])
def api_create_zap_invoice(post_id):
    """Create Lightning invoice for zapping content via LNURL"""
    import requests as req
    
    data = request.get_json() or {}
    amount_sats = data.get('amount_sats', 1000)
    amount_msats = amount_sats * 1000
    
    post = models.CuratedPost.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'error': 'Post not found'})
    
    lightning_address = 'protocolpulse@getalby.com'
    if post.creator and post.creator.lightning_address:
        lightning_address = post.creator.lightning_address
    
    invoice = None
    try:
        if '@' in lightning_address:
            username, domain = lightning_address.split('@')
            lnurl_url = f"https://{domain}/.well-known/lnurlp/{username}"
            
            lnurl_resp = req.get(lnurl_url, timeout=5)
            if lnurl_resp.status_code == 200:
                lnurl_data = lnurl_resp.json()
                callback = lnurl_data.get('callback')
                min_amt = lnurl_data.get('minSendable', 1000)
                max_amt = lnurl_data.get('maxSendable', 100000000000)
                
                if callback and min_amt <= amount_msats <= max_amt:
                    invoice_resp = req.get(f"{callback}?amount={amount_msats}", timeout=5)
                    if invoice_resp.status_code == 200:
                        invoice_data = invoice_resp.json()
                        invoice = invoice_data.get('pr')
    except Exception as e:
        logging.warning(f"LNURL invoice generation failed: {e}")
    
    return jsonify({
        'success': True,
        'post_id': post_id,
        'amount_sats': amount_sats,
        'lightning_address': lightning_address,
        'invoice': invoice
    })

@app.route('/api/value-stream/curators')
def api_get_curators():
    """Get top curators for the leaderboard"""
    from services.value_stream_service import value_stream_service
    
    curators = value_stream_service.get_top_curators(limit=20)
    return jsonify({'success': True, 'curators': curators})

@app.route('/api/value-stream/register', methods=['POST'])
def api_register_creator():
    """Register as a creator/curator"""
    from services.value_stream_service import value_stream_service
    
    data = request.get_json() or {}
    display_name = data.get('display_name')
    nostr_pubkey = data.get('nostr_pubkey')
    lightning_address = data.get('lightning_address')
    nip05 = data.get('nip05')
    
    if not display_name:
        return jsonify({'success': False, 'error': 'Display name required'})
    
    result = value_stream_service.register_creator(
        display_name=display_name,
        nostr_pubkey=nostr_pubkey,
        lightning_address=lightning_address,
        nip05=nip05
    )
    return jsonify(result)

def _is_nostr_spam(content: str) -> bool:
    """Filter explicit content, altcoin spam, and hashtag farms from Nostr posts."""
    if not content:
        return False
    c = content.lower()
    spam_terms = ['incest', 'onlyfans', 'nude', 'xxx', 'porn', 'naked', 'sex tape',
                  '#solana', '#memecoin', 'ethbtc', 'paxgbtc']
    if any(t in c for t in spam_terms):
        return True
    words = content.split()
    if len(words) > 0:
        hashtag_ratio = sum(1 for w in words if w.startswith('#')) / len(words)
        if hashtag_ratio > 0.6:
            return True
    return False


@app.route('/api/nostr/latest/<pubkey>')
def api_nostr_latest(pubkey):
    """Get latest Nostr post for a given pubkey"""
    try:
        events = models.NostrEvent.query.filter_by(pubkey=pubkey).order_by(models.NostrEvent.created_at.desc()).limit(10).all()
        for event in events:
            if not _is_nostr_spam(event.content):
                return jsonify({
                    'success': True,
                    'content': event.content,
                    'created_at': event.created_at.timestamp() if event.created_at else None,
                    'kind': event.kind
                })
        return jsonify({'success': False, 'error': 'No events found'})
    except Exception as e:
        logging.warning(f"Nostr latest fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/extension')
def extension_page():
    """Browser extension download and info page"""
    return render_template('extension.html')

@app.route('/extension/download')
def download_extension():
    """Download the browser extension as a ZIP file"""
    import zipfile
    import io
    import os
    
    extension_dir = 'static/extension'
    
    if not os.path.exists(extension_dir):
        return "Extension files not found", 404
    
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(extension_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extension_dir)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)
    
    from flask import send_file
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='pulse-zapper-extension.zip'
    )

@app.route('/scorecard')
def sovereign_scorecard():
    """Sovereign Scorecard - Security self-assessment quiz"""
    return render_template('sovereign_scorecard.html')


@app.route('/drill')
def recovery_drill():
    """Recovery Drill - Seed phrase practice without real keys"""
    return render_template('recovery_drill.html')


@app.route('/operator-costs')
def operator_costs():
    """Operator Costs - Fee leakage calculator"""
    return render_template('operator_costs.html')

@app.route('/solo-slayers')
def solo_slayers():
    """Solo Miner Tracker - Celebrates independent miners who find blocks"""
    import importlib.util
    # solo_tracker lives in project root services/, not core/services/ — load by path
    _tracker_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services', 'solo_tracker.py')
    spec = importlib.util.spec_from_file_location('solo_tracker', os.path.abspath(_tracker_path))
    _mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mod)
    tracker = _mod.solo_tracker

    stats = tracker.get_stats()
    leaderboard = tracker.get_leaderboard()
    solo_blocks = tracker.solo_blocks[:50]

    return render_template('solo_slayers.html',
                         stats=stats,
                         leaderboard=leaderboard,
                         solo_blocks=solo_blocks)


def _dossier_manifest_path():
    """Resolve dossier manifest path from the core package dir (works with any cwd or gunicorn core.app:app)."""
    core_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(core_dir, 'static', 'data', 'dossier_manifest.json')


def _sovereign7_manifest_path():
    """Sovereign 7 condensed dossier manifest (7 chapters)."""
    core_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(core_dir, 'static', 'data', 'sovereign7_manifest.json')


# Built-in Sovereign 7 chapters so /dossier always works even if JSON is missing (e.g. wrong cwd or deploy).
SOVEREIGN7_CHAPTERS_FALLBACK = [
    {"id": 1, "title": "The Infinite Printing Press", "subtitle": "The Problem",
     "narrative": "Modern money isn't earned; it's printed. When they add a zero to the supply, they subtract a year of your life.",
     "image_path": "/static/images/dossier/sovereign7/01_infinite_printing.png",
     "deep_dive": {"key_metric": "M2 Money Supply Expansion vs. Purchasing Power",
                  "math": "Since 1913, the USD has lost over 96% of its value. Since 2020, over 40% of all USD in existence was printed.",
                  "technical_insight": "The Cantillon Effect: newly printed money benefits banks and government first, while dilution (inflation) hits the average citizen last."}},
    {"id": 2, "title": "The Nixon Shock", "subtitle": "The Point of No Return",
     "narrative": "In 1971, the world lost its anchor. We moved from \"Money backed by Gold\" to \"Money backed by Promises.\"",
     "image_path": "/static/images/dossier/sovereign7/02_nixon_shock.png",
     "deep_dive": {"key_metric": "Real Wages vs. Productivity Gap",
                  "math": "Post-1971, productivity continued to rise, but real wages decoupled and stayed flat.",
                  "technical_insight": "Transition from Commodity-Backed Money to Debt-Based Fiat. \"Fiat\" is Latin for \"by decree\"—value only because the government says so, backed by nothing but tax collection and military force."}},
    {"id": 3, "title": "The Scarcity Wall", "subtitle": "The Solution",
     "narrative": "For the first time in human history, we have an asset where the supply is mathematically fixed. There will only ever be 21 million.",
     "image_path": "/static/images/dossier/sovereign7/03_scarcity_wall.png",
     "deep_dive": {"key_metric": "Absolute Scarcity vs. Stock-to-Flow",
                  "math": "Total Supply = Σ (n=0 to 32) of 210,000 × (50 / 2^n)",
                  "technical_insight": "Bitcoin is the first un-inflatable asset. Unlike gold (higher price → more mining), Bitcoin's supply is inelastic. No matter how high the price, the issuance schedule stays identical."}},
    {"id": 4, "title": "The Difficulty Adjustment", "subtitle": "The Heartbeat",
     "narrative": "Bitcoin breathes. Every two weeks, the network adjusts to ensure it can never be killed, cheated, or rushed. It is the only machine that manages itself.",
     "image_path": "/static/images/dossier/sovereign7/04_difficulty_adjustment.png",
     "deep_dive": {"key_metric": "The 2016 Block Target (Approx. 2 weeks)",
                  "math": "If blocks are found too fast (<10 min), difficulty increases. If too slow (>10 min), it decreases.",
                  "technical_insight": "The most important Satoshi discovery. Ensures Bitcoin's issuance cannot be rushed by more powerful hardware. The network is a living, self-correcting biological machine."}},
    {"id": 5, "title": "The Energy Shield", "subtitle": "The Security",
     "narrative": "Bitcoin isn't backed by nothing. It's backed by the laws of physics. Every block is a wall of pure energy that makes the network unhackable.",
     "image_path": "/static/images/dossier/sovereign7/05_energy_shield.png",
     "deep_dive": {"key_metric": "Terahashes per Second (TH/s) & Exahashes",
                  "math": "To rewrite a block, an attacker must control >51% of total network hashrate—costing billions in hardware and electricity.",
                  "technical_insight": "Thermodynamic Security. Bitcoin converts raw energy into a digital wall that protects wealth. The only digital asset that is expensive to create, preventing the Infinite Printing problem of fiat."}},
    {"id": 6, "title": "The S-Curve", "subtitle": "The Inevitability",
     "narrative": "Adoption isn't a straight line; it's a tidal wave. We are currently at the \"Early Majority\" stage. The shift to a Bitcoin Standard is a mathematical certainty.",
     "image_path": "/static/images/dossier/sovereign7/06_scurve.png",
     "deep_dive": {"key_metric": "Metcalfe's Law (V ∝ n²)",
                  "math": "The value of a network is proportional to the square of its users.",
                  "technical_insight": "Bitcoin's adoption curve parallels the Internet, the Smartphone, and the Automobile. We are in the Early Majority phase. As the network grows, utility and liquidity increase exponentially—making it harder for any other coin to catch up."}},
    {"id": 7, "title": "Sovereign Custody", "subtitle": "The Freedom",
     "narrative": "If you don't hold the keys, you don't hold the coins. Sovereignty starts with your own private vault.",
     "image_path": "/static/images/dossier/sovereign7/07_sovereign_custody.png",
     "deep_dive": {"key_metric": "256-bit ECDSA Encryption",
                  "math": "There are 2^256 possible private keys—more than the number of atoms in the observable universe.",
                  "technical_insight": "Holding your own keys means you are your own central bank. No customer service to freeze your account. You move from Permissioned Finance (asking to use your money) to Permissionless Sovereignty."}},
]


def _load_json_manifest(path):
    """Load JSON manifest; return [] on any error."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Manifest not found at %s", path)
        return []
    except json.JSONDecodeError as e:
        logging.warning("Manifest invalid JSON: %s", e)
        return []
    except Exception as e:
        logging.warning("Manifest error: %s", e)
        return []


def _get_sovereign7_chapters():
    """Return Sovereign 7 chapters from JSON file, or built-in fallback so /dossier always has content."""
    path = _sovereign7_manifest_path()
    chapters = _load_json_manifest(path)
    if chapters and len(chapters) >= 7:
        return chapters
    logging.warning("Using built-in Sovereign 7 chapters (file missing or invalid at %s)", path)
    return SOVEREIGN7_CHAPTERS_FALLBACK


@app.route('/dossier')
def dossier():
    """The Protocol Pulse Dossier — Sovereign 7 (7 chapters). Main dossier template is dossier.html."""
    chapters = _get_sovereign7_chapters()
    resp = make_response(render_template('dossier.html', chapters=chapters))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route('/dossier/classic')
def dossier_classic():
    """The Protocol Pulse Dossier — full 32-slide version."""
    manifest_path = _dossier_manifest_path()
    manifest = _load_json_manifest(manifest_path)
    return render_template('dossier_classic.html', manifest=manifest)


@app.route('/mining-risk')
def mining_risk():
    """Mining Risk by Geography — risk factor by deployment location with real-time metrics"""
    return render_template('mining_risk.html')


@app.route('/api/mining-risk')
def api_mining_risk():
    """API: regions with risk scores + live network metrics for Mining Risk page"""
    try:
        from services.mining_risk_service import get_regions_with_risk, get_live_network_metrics
        regions = get_regions_with_risk()
        network = get_live_network_metrics()
        return jsonify({
            'regions': regions,
            'network': network,
            'updated_at': network.get('updated_at'),
        })
    except Exception as e:
        logging.error(f"Mining risk API error: {e}")
        return jsonify({'regions': [], 'network': {}, 'error': str(e)}), 500


@app.route('/api/solo-blocks')
def api_solo_blocks():
    """API endpoint for solo block data"""
    from services.solo_tracker import solo_tracker
    
    stats = solo_tracker.get_stats()
    leaderboard = solo_tracker.get_leaderboard()
    blocks = solo_tracker.solo_blocks[:100]
    
    return jsonify({
        'success': True,
        'stats': stats,
        'leaderboard': leaderboard,
        'blocks': blocks
    })

@app.route('/.well-known/nostr.json')
def nostr_nip05():
    """NIP-05 Identity Verification for @user@protocolpulse.io"""
    name = request.args.get('name', '').lower()
    
    known_pubkeys = {
        '_': '36a56b0d52d34afd5f26cbdd8fede3ab89e4a6d8b6e23b7d9d8b6f8f8f8f8f8f',
        'pulse': '36a56b0d52d34afd5f26cbdd8fede3ab89e4a6d8b6e23b7d9d8b6f8f8f8f8f8f',
        'alex': 'alex0000000000000000000000000000000000000000000000000000000000',
        'sarah': 'sarah000000000000000000000000000000000000000000000000000000000'
    }
    
    if name and name in known_pubkeys:
        response_data = {
            'names': {name: known_pubkeys[name]},
            'relays': {
                known_pubkeys[name]: ['wss://relay.damus.io', 'wss://nos.lol', 'wss://relay.primal.net']
            }
        }
    else:
        response_data = {
            'names': {k: v for k, v in known_pubkeys.items()},
            'relays': {}
        }
    
    response = make_response(jsonify(response_data))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/chat')
def ask_alex_chat():
    """Ask Alex Chat - LangGraph conversational agent for Bitcoin intelligence"""
    return render_template('ask_alex_chat.html')

@app.route('/api/chat/ask', methods=['POST'])
def chat_ask_alex():
    """API endpoint for Ask Alex chat interactions"""
    try:
        from services.multi_agent_supervisor import supervisor
        from services.node_service import NodeService
        
        data = request.get_json() or {}
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        network_stats = NodeService.get_network_stats()
        context = f"""LIVE NETWORK DATA:
- Block Height: {network_stats.get('height', 'N/A')}
- Hashrate: {network_stats.get('hashrate', 'N/A')}
- Difficulty: {network_stats.get('difficulty', 'N/A')}
- Mempool: {network_stats.get('mempool_count', 'N/A')} transactions

USER QUESTION: {question}"""
        
        from services.multi_agent_supervisor import TaskType
        result = supervisor.run_task(
            topic=context,
            task_type=TaskType.GROUND_TRUTH
        )
        
        alex_response = result.get('alex_analysis', 'Unable to process your question at this time.')
        
        return jsonify({
            'success': True,
            'response': alex_response,
            'network_data': network_stats,
            'generated_by': 'Alex The Quant'
        })
        
    except Exception as e:
        logging.error(f"Ask Alex error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clips')
def clips_gallery():
    """Signal Clips Gallery - Viral short-form content"""
    try:
        from services.ai_clips_service import ai_clips_service
        clips = ai_clips_service.get_all_clips()
        status = ai_clips_service.get_status()
    except Exception as e:
        logging.error(f"AI Clips service error: {e}")
        from services.clips_service import clips_service
        clips = clips_service.get_all_clips()
        status = clips_service.get_status()
    return render_template('clips_gallery.html', clips=clips, status=status)

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

@app.route('/api/network-data')
def api_network_data():
    """Server-side API for network data - avoids CORS issues"""
    try:
        mempool_data = fetch_mempool_data()
        prices = price_service.get_prices()
        
        fees_data = mempool_data.get('fees', {})
        hashrate_raw = mempool_data.get('current_hashrate', 0)
        difficulty_raw = mempool_data.get('current_difficulty', 0)
        
        response_data = {
            'success': True,
            'bitcoin': {
                'price': prices.get('bitcoin', {}).get('price', 0),
                'change_24h': prices.get('bitcoin', {}).get('change_24h', 0),
            },
            'mempool': {
                'count': mempool_data.get('count', 0),
                'vsize': mempool_data.get('vsize', 0),
            },
            'fees': {
                'fastest': fees_data.get('fastest', 0),
                'halfHourFee': fees_data.get('half_hour', 0),
                'hourFee': fees_data.get('hour', 0),
                'economyFee': fees_data.get('economy', 0),
                'minimumFee': fees_data.get('minimum', 0),
            },
            'network': {
                'hashrate': hashrate_raw / 1e18 if hashrate_raw else 0,
                'difficulty': difficulty_raw / 1e12 if difficulty_raw else 0,
            },
            'difficulty_adjustment': mempool_data.get('difficulty_adjustment', {}),
            'last_updated': datetime.now().isoformat()
        }
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error in network-data API: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/articles')
def articles():
    """Intelligence Terminal: Bento layout with hero, grid, Network Health sidebar. Paginated so all articles load."""
    now = datetime.utcnow()
    per_page = 40
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    base_q = models.Article.query.filter(models.Article.published.is_(True)).order_by(
        models.Article.created_at.desc()
    )
    total_count = base_q.count()
    if total_count == 0:
        logging.info("No published articles; falling back to all articles.")
        base_q = models.Article.query.order_by(models.Article.created_at.desc())
        total_count = base_q.count()

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page
    recent = base_q.offset(offset).limit(per_page).all()

    ticker_q = models.Article.query.filter(models.Article.published.is_(True)).order_by(
        models.Article.created_at.desc()
    ).limit(5)
    if total_count == 0:
        ticker_q = models.Article.query.order_by(models.Article.created_at.desc()).limit(5)
    ticker_titles = [a.title for a in ticker_q.all()]

    latest_article = recent[0] if (page == 1 and recent) else None
    grid_articles = recent[1:] if (page == 1 and len(recent) > 1) else recent
    categories = [cat[0] for cat in db.session.query(models.Article.category).distinct().all() if cat[0]]
    categories = [c for c in categories if c != 'DeFi']
    spotlight_articles = recent[1:4] if (page == 1 and len(recent) > 1) else []
    rest_for_sections = recent[4:24] if (page == 1 and len(recent) > 4) else []
    sectioned = {}
    for c in categories:
        sectioned[c] = [a for a in rest_for_sections if a.category == c][:4]
    shown_in_sections = set()
    for arts in sectioned.values():
        for a in arts:
            shown_in_sections.add(a.id)
    latest_grid = [a for a in rest_for_sections if a.id not in shown_in_sections]
    more_articles = recent[24:40] if (page == 1 and len(recent) > 24) else []

    today_articles = recent[:10]
    yesterday_articles = recent[10:20] if len(recent) > 10 else []
    archive_articles = recent[20:40] if len(recent) > 20 else []
    for article in today_articles:
        time_diff = (now - article.created_at).total_seconds() / 3600
        article.is_pressing = time_diff < 1

    use_published = total_count > 0
    category_counts = {}
    for c in categories:
        q = models.Article.query.filter(models.Article.category == c)
        if use_published:
            q = q.filter(models.Article.published.is_(True))
        category_counts[c] = q.count()
    active_ads = models.Advertisement.query.filter_by(is_active=True).all()
    prices = price_service.get_prices()
    network_stats = None
    mempool_data = {}
    try:
        network_stats = NodeService.get_network_stats()
    except Exception:
        pass
    try:
        mempool_data = fetch_mempool_data()
    except Exception:
        pass
    default_header_url = "/static/images/default-header.png"
    import os as _os
    article_image_urls = {}
    for a in recent:
        # Law 1: prefer cover_image_url, fall back to header_image_url
        ciu = (getattr(a, "cover_image_url", None) or "").strip()
        if ciu and (ciu.startswith("http") or (ciu.startswith("/static/") and "default-header" not in ciu)):
            article_image_urls[a.id] = ciu
            continue
        url = (getattr(a, "header_image_url", None) or "").strip()
        if url and url.startswith("http"):
            article_image_urls[a.id] = url
        elif url and url != default_header_url:
            filepath = url.lstrip("/")
            if _os.path.exists(filepath):
                article_image_urls[a.id] = url
            else:
                article_image_urls[a.id] = default_header_url
        else:
            article_image_urls[a.id] = default_header_url

    return render_template('articles.html',
                         today_articles=today_articles,
                         yesterday_articles=yesterday_articles,
                         archive_articles=archive_articles,
                         latest_article=latest_article,
                         grid_articles=grid_articles,
                         spotlight_articles=spotlight_articles,
                         sectioned=sectioned,
                         latest_grid=latest_grid,
                         more_articles=more_articles,
                         ticker_titles=ticker_titles,
                         categories=categories,
                         category_counts=category_counts,
                         active_ads=active_ads,
                         prices=prices,
                         price_service=price_service,
                         network_stats=network_stats,
                         mempool_data=mempool_data,
                         last_updated=now,
                         page=page,
                         total_pages=total_pages,
                         total_count=total_count,
                         per_page=per_page,
                         default_header_url=default_header_url,
                         article_image_urls=article_image_urls)


def _article_body_without_tldr(content):
    """Delete ALL text before the first <h2> tag to prevent double-summaries (TL;DR/summary only in Key Takeaways)."""
    if not content:
        return ""
    first_h2 = re.search(r'<h2[\s>]', content, re.IGNORECASE)
    if first_h2:
        return content[first_h2.start():].strip()
    return content.strip()


def _article_key_takeaways(article):
    """Extract key takeaways: summary, or TL;DR from content, or first 400 chars."""
    summary = (article.summary or "").strip()
    content = (article.content or "")
    if summary:
        return summary
    tldr_match = re.search(
        r'<div\s+class="tldr-section"[^>]*>\s*(?:<[^>]+>)*\s*TL;DR:\s*([^<]+)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if tldr_match:
        text = re.sub(r"<[^>]+>", "", tldr_match.group(1)).strip()
        return text[:500] + ("…" if len(text) > 500 else "")
    plain = re.sub(r"<[^>]+>", "", content).strip()
    return plain[:400] + ("…" if len(plain) > 400 else "") if plain else ""


@app.route('/articles/<int:article_id>')
def article_detail(article_id):
    """Individual article page. Key Takeaways and body never duplicated."""
    article = models.Article.query.get_or_404(article_id)
    try:
        related_articles = models.Article.query.filter(
            models.Article.id != article_id,
            models.Article.published == True,
            models.Article.category == article.category
        ).limit(3).all()
    except Exception:
        related_articles = []
    key_takeaways_text = _article_key_takeaways(article)
    key_takeaways_bullets = []
    if key_takeaways_text:
        for part in re.split(r"\.\s+", key_takeaways_text):
            part = part.strip().strip(".")
            if part and len(part) > 10:
                key_takeaways_bullets.append(part + ("." if not part.endswith(".") else ""))
    if not key_takeaways_bullets and key_takeaways_text:
        key_takeaways_bullets = [key_takeaways_text]
    body_html = _article_body_without_tldr(article.content or "")
    header_image_url = article.resolve_cover_image() if hasattr(article, 'resolve_cover_image') else (article.cover_image_url or article.header_image_url or "/static/images/default-header.png")

    # P3 Affiliate CTA injection — contextual, AI-classified, privacy-first
    affiliate_cta = None
    try:
        from services.affiliate_injector import inject_affiliate_cta
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        client_ip = raw_ip.split(',')[0].strip()
        tags_str = getattr(article, 'tags', '') or ''
        affiliate_cta = inject_affiliate_cta(
            article_id=article.id,
            article_content=article.content or '',
            article_category=article.category or '',
            article_tags=tags_str,
            client_ip=client_ip,
        )
    except Exception as _aff_exc:
        logging.debug("affiliate_inject skipped: %s", _aff_exc)

    return render_template(
        "article_detail.html",
        article=article,
        related_articles=related_articles,
        key_takeaways_text=key_takeaways_text,
        key_takeaways_bullets=key_takeaways_bullets,
        body_html=body_html,
        cover_image_url=header_image_url,
        affiliate_cta=affiliate_cta,
    )

@app.route('/category/<category>')
def category_articles(category):
    """Category-filtered article listing with premium design"""
    articles = models.Article.query.filter(
        models.Article.published == True,
        models.Article.category == category
    ).order_by(models.Article.created_at.desc()).limit(50).all()
    
    return render_template('category.html', category=category, articles=articles)

def _slugify_section(name):
    """Safe HTML id from section name (alphanumeric and dashes only)."""
    if not name:
        return "general"
    import re
    s = re.sub(r'[^\w\s-]', '', str(name)).strip().lower()
    return re.sub(r'[-\s]+', '-', s) or "general"


def _get_podcast_sections(per_section=6):
    """Build podcast sections list (Protocol Pulse, Cypherpunk'd, etc.) for Media Hub."""
    sections_list = []
    seen_slugs = set()
    sources = db.session.query(models.Podcast.rss_source).distinct().all()
    for (source,) in sources:
        source_name = source if source else "General"
        slug = _slugify_section(source_name)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        recent = models.Podcast.query.filter_by(rss_source=source).order_by(
            models.Podcast.published_date.desc()
        ).limit(per_section).all()
        if recent:
            sections_list.append({
                "name": source_name,
                "slug": slug,
                "podcasts": recent,
            })
    return sections_list


@app.route('/podcasts')
def podcasts():
    """Redirect to Media Hub Podcasts section."""
    return redirect(url_for('media_hub') + '#section-podcasts')

@app.route('/api/podcast/<int:podcast_id>')
def get_podcast_api(podcast_id):
    """API endpoint to get podcast data for player"""
    try:
        podcast = models.Podcast.query.get_or_404(podcast_id)
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

@app.route('/api/podcasts/<path:rss_source>')
def get_more_podcasts_api(rss_source):
    """API endpoint to load more episodes for a specific RSS source (use 'General' for null source)."""
    try:
        from urllib.parse import unquote
        rss_source = unquote(rss_source)
        source_filter = None if rss_source == "General" else rss_source
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 3, type=int)

        base = models.Podcast.query
        if source_filter is None:
            base = base.filter(models.Podcast.rss_source.is_(None))
        else:
            base = base.filter(models.Podcast.rss_source == source_filter)
        total_count = base.count()
        podcasts = base.order_by(models.Podcast.published_date.desc()).offset(offset).limit(limit).all()
        
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
    if not rss_service:
        return "RSS service not available", 503
    try:
        rss_xml = rss_service.generate_rss_feed()
        response = app.response_class(rss_xml, mimetype='application/rss+xml')
        return response
    except Exception as e:
        logging.error(f"Error generating podcast RSS: {e}")
        return "Error generating RSS feed", 500

@app.route('/media-terminal')
def media_terminal():
    """Redirect media-terminal to the unified media hub"""
    return redirect(url_for('media_hub'))

def _get_media_hub_books():
    """Build our_books and recommended_books for Media Hub. Always available (no RSS/API dependency)."""
    affiliate_tag = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')
    our_books = [
        {
            'title': 'Everything Divided by 21 Million',
            'author': 'Knut Svanholm',
            'description': 'A philosophical deep dive into Bitcoin\'s relationship to time, money, freedom, and human progress through mathematical scarcity.',
            'cover_url': '/static/images/books/everything_21m.jpg',
            'amazon_url': f'https://www.amazon.com/dp/9916697191?tag={affiliate_tag}'
        },
        {
            'title': 'The Big Print',
            'author': 'Lawrence Lepard',
            'description': 'An exposé revealing how the Federal Reserve and financial elites engineered wealth extraction through monetary policy.',
            'cover_url': '/static/images/books/big_print.jpg',
            'amazon_url': f'https://www.amazon.com/dp/B0DVTCVX8J?tag={affiliate_tag}'
        },
        {
            'title': 'Daylight Robbery',
            'author': 'Dominic Frisby',
            'description': 'The hidden history of how taxation has shaped human civilization from ancient empires to modern governments.',
            'cover_url': '/static/images/books/daylight_robbery.jpg',
            'amazon_url': f'https://www.amazon.com/dp/0241360846?tag={affiliate_tag}'
        },
        {
            'title': 'The Genesis Book',
            'author': 'Aaron van Wirdum',
            'description': 'The definitive history of Bitcoin\'s ideological origins — from Austrian economics to the cypherpunk movement.',
            'cover_url': '/static/images/books/genesis_book.jpg',
            'amazon_url': f'https://www.amazon.com/dp/B0CQLMQRH7?tag={affiliate_tag}'
        }
    ]
    recommended_books = [
        {
            'title': 'The Bitcoin Standard',
            'author': 'Saifedean Ammous',
            'description': 'The essential guide to understanding Bitcoin as sound money and the history of monetary systems.',
            'cover_url': '/static/images/books/bitcoin_standard.jpg',
            'amazon_url': f'https://www.amazon.com/dp/1119473861?tag={affiliate_tag}',
            'bestseller': True
        },
        {
            'title': 'Broken Money',
            'author': 'Lyn Alden',
            'description': 'A comprehensive analysis of the global monetary system and why Bitcoin matters.',
            'cover_url': '/static/images/books/broken_money.jpg',
            'amazon_url': f'https://www.amazon.com/dp/B0CG8985FR?tag={affiliate_tag}',
            'bestseller': True
        },
        {
            'title': 'Mastering Bitcoin',
            'author': 'Andreas Antonopoulos & David Harding',
            'description': 'The technical guide to understanding and programming Bitcoin at a deep level. Third Edition.',
            'cover_url': '/static/images/books/mastering_bitcoin.jpg',
            'amazon_url': f'https://www.amazon.com/dp/1098150090?tag={affiliate_tag}',
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
            'title': 'The Sovereign Individual',
            'author': 'James Dale Davidson & Lord William Rees-Mogg',
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
        },
        {
            'title': 'Inventing Bitcoin',
            'author': 'Yan Pritzker',
            'description': 'A concise technical and economic introduction to how Bitcoin works and why it matters.',
            'cover_url': 'https://covers.openlibrary.org/b/isbn/9781097476922-L.jpg',
            'amazon_url': f'https://www.amazon.com/dp/1097476922?tag={affiliate_tag}',
            'bestseller': True
        },
        {
            'title': 'Thank God for Bitcoin',
            'author': 'Jimmy Song et al.',
            'description': 'A faith-oriented perspective on Bitcoin as a tool for freedom and stewardship.',
            'cover_url': 'https://covers.openlibrary.org/b/isbn/9781642790622-L.jpg',
            'amazon_url': f'https://www.amazon.com/dp/1642790622?tag={affiliate_tag}',
            'bestseller': False
        },
        {
            'title': 'The Blocksize War',
            'author': 'Jonathan Bier',
            'description': 'The inside story of the battle over Bitcoin\'s block size and the future of the protocol.',
            'cover_url': 'https://covers.openlibrary.org/b/isbn/9781916294212-L.jpg',
            'amazon_url': f'https://www.amazon.com/dp/1916294216?tag={affiliate_tag}',
            'bestseller': False
        },
        {
            'title': 'Softwar',
            'author': 'Larry Ellison',
            'description': 'Oracle and the rise of cloud computing — context on tech and power that resonates with Bitcoin\'s story.',
            'cover_url': 'https://covers.openlibrary.org/b/isbn/9781416532190-L.jpg',
            'amazon_url': f'https://www.amazon.com/dp/1416532194?tag={affiliate_tag}',
            'bestseller': False
        },
        {
            'title': 'The Truth About Money',
            'author': 'Richard Duncan',
            'description': 'How fiat money creation drives inequality and instability — essential macro context for Bitcoin.',
            'cover_url': 'https://covers.openlibrary.org/b/isbn/9780470181553-L.jpg',
            'amazon_url': f'https://www.amazon.com/dp/0470181552?tag={affiliate_tag}',
            'bestseller': False
        },
    ]
    return our_books, recommended_books


@app.route('/media')
@app.route('/media-hub')
def media_hub():
    """Media Hub page with live RSS feeds, books, podcasts, and merch"""
    our_books, recommended_books = _get_media_hub_books()
    podcast_sections_list = _get_podcast_sections(per_section=6)
    if not rss_service:
        return render_template('media_hub_new.html', shows=[], products=[], our_books=our_books, recommended_books=recommended_books, youtube_series={}, live_broadcasts={}, intel_posts=[], new_this_week=[], latest_feed=[], podcast_sections_list=podcast_sections_list, get_thumbnail=YouTubeService.get_thumbnail)
    try:
        shows = rss_service.get_show_info()
        products = []
        try:
            products = printful_service.get_store_products()
            products = [printful_service.format_product_for_display(p) for p in products if not printful_service.format_product_for_display(p).get('is_ignored', True)]
        except Exception as e:
            logging.warning(f"Could not load merch products: {e}")
        
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
        active_ads = models.Advertisement.query.filter_by(is_active=True).all()
        
        # Get intel posts for the Intelligence Stream section
        intel_posts = []
        try:
            recent_intel = models.IntelligencePost.query.order_by(
                models.IntelligencePost.published_at.desc()
            ).limit(5).all()
            for post in recent_intel:
                hours_ago = 1
                try:
                    if post.published_at:
                        hours_ago = int((datetime.utcnow() - post.published_at).total_seconds() / 3600)
                except:
                    pass
                intel_posts.append({
                    'id': post.id,
                    'persona': post.persona or 'Alex',
                    'partner_handle': post.partner_handle or '',
                    'primary_tweet': post.primary_tweet,
                    'key_insight': post.key_insight,
                    'time_ago': f"{hours_ago}h ago" if hours_ago < 24 else f"{hours_ago // 24}d ago",
                    'x_url': f"https://x.com/ProtocolPulse/status/{post.x_tweet_id}" if post.x_tweet_id else None
                })
        except Exception as e:
            logging.warning(f"Could not load intel posts for media hub: {e}")
        
        # New this week: 2 intel, 1 latest episode, 1 featured book
        new_this_week = []
        for post in intel_posts[:2]:
            new_this_week.append({
                'type': 'intel',
                'title': (post.get('key_insight') or post.get('primary_tweet') or 'Intel brief')[:80],
                'url': post.get('x_url') or '#',
                'meta': post.get('time_ago', '') + ' · ' + (post.get('persona') or ''),
                'description': post.get('key_insight') or '',
            })
        lb = live_broadcasts.get('cypherpunkd') or {}
        if lb:
            new_this_week.append({
                'type': 'episode',
                'title': lb.get('title', "Cypherpunk'd // Intel Briefing"),
                'url': '#section-series',
                'meta': 'Latest episode',
                'video_id': lb.get('latest_id'),
                'series_id': 'everything_21m',
                'description': lb.get('description', '')[:120],
            })
        if our_books:
            b = our_books[0]
            new_this_week.append({
                'type': 'book',
                'title': b.get('title', ''),
                'url': b.get('amazon_url', '#'),
                'meta': 'Featured',
                'description': (b.get('description') or '')[:100],
                'cover_url': b.get('cover_url'),
            })
        
        # Unified latest feed (intel + one episode + one book) for "Latest" section
        latest_feed = []
        for post in intel_posts:
            latest_feed.append({
                'type': 'intel',
                'title': (post.get('key_insight') or post.get('primary_tweet') or 'Intel brief')[:80],
                'url': post.get('x_url') or '#',
                'meta': post.get('time_ago', '') + ' · ' + (post.get('persona') or ''),
                'description': post.get('key_insight') or '',
            })
        if lb and not any(x.get('type') == 'episode' for x in latest_feed):
            latest_feed.append({
                'type': 'episode',
                'title': lb.get('title', "Cypherpunk'd"),
                'url': '#section-series',
                'meta': 'Latest',
                'video_id': lb.get('latest_id'),
                'series_id': 'everything_21m',
                'description': lb.get('description', '')[:120],
            })
        if our_books:
            b = our_books[0]
            latest_feed.append({
                'type': 'book',
                'title': b.get('title', ''),
                'url': b.get('amazon_url', '#'),
                'meta': 'Sovereign Library',
                'description': (b.get('description') or '')[:100],
                'cover_url': b.get('cover_url'),
            })
        
        return render_template('media_hub_new.html',
                               shows=shows,
                               products=products,
                               our_books=our_books,
                               recommended_books=recommended_books,
                               youtube_series=youtube_series,
                               live_broadcasts=live_broadcasts,
                               active_ads=active_ads,
                               intel_posts=intel_posts,
                               new_this_week=new_this_week,
                               latest_feed=latest_feed,
                               podcast_sections_list=podcast_sections_list,
                               series_data={},
                               get_thumbnail=YouTubeService.get_thumbnail)
    except Exception as e:
        logging.error(f"Error loading media hub: {e}")
        return render_template('media_hub_new.html', shows=[], products=[], our_books=locals().get('our_books', []), recommended_books=locals().get('recommended_books', []), youtube_series={}, live_broadcasts={}, intel_posts=[], new_this_week=[], latest_feed=[], podcast_sections_list=locals().get('podcast_sections_list') or [], series_data={}, get_thumbnail=YouTubeService.get_thumbnail)

@app.route('/api/latest-episodes')
def get_latest_episodes():
    """API endpoint to get latest podcast episodes from RSS feeds"""
    if not rss_service:
        return jsonify({'episodes': [], 'error': 'RSS service not available'}), 503
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
    if not rss_service:
        return jsonify({'episodes': [], 'error': 'RSS service not available'}), 503
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
    if not rss_service:
        return jsonify({'episodes': [], 'error': 'RSS service not available'}), 503
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
    if not rss_service:
        return jsonify({'success': False, 'error': 'RSS service not available'}), 503
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
    if not rss_service:
        flash('RSS service not available (install feedparser)')
        return redirect('/admin/podcasts')
    try:
        results = rss_service.sync_all_feeds()
        flash(f'Podcast sync completed: {results}')
        return redirect('/admin/podcasts')
    except Exception as e:
        logging.error(f"Error syncing podcasts: {e}")
        flash(f'Error syncing podcasts: {e}')
        return redirect('/admin/podcasts')


@app.route('/admin/x-replies')
@login_required
@admin_required
def admin_x_replies():
    """Admin dashboard for Sovereign Sentry reply queue."""
    from models import XInboxTweet

    pending = (
        XInboxTweet.query.filter_by(status='drafted')
        .order_by(XInboxTweet.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('admin/x_replies.html', pending=pending)


@app.route('/admin/x-replies/<int:inbox_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_approve(inbox_id):
    """Approve a draft and post reply to X."""
    from models import XInboxTweet, XReplyDraft, XReplyPost
    from services.x_client import XClient

    inbox = XInboxTweet.query.get_or_404(inbox_id)
    draft = inbox.drafts.order_by(XReplyDraft.created_at.desc()).first()
    if not draft:
        flash('No draft available for this tweet.')
        return redirect('/admin/x-replies')

    # Allow inline edit of draft text
    new_text = request.form.get('draft_text', '').strip()
    if new_text:
        draft.draft_text = new_text

    client = XClient()
    result = client.post_reply(in_reply_to_tweet_id=inbox.tweet_id, text=draft.draft_text)

    post = XReplyPost(
        inbox_id=inbox.id,
        draft_id=draft.id,
        reply_tweet_id=result.get('tweet_id'),
        response_payload=json.dumps(result.get('raw', {})),
    )
    inbox.status = 'posted' if result.get('success') else 'error'

    db.session.add(post)
    db.session.add(inbox)
    db.session.commit()

    if result.get('success'):
        flash('Reply posted to X.')
    else:
        flash('Reply failed to post; see logs.')
    return redirect('/admin/x-replies')


@app.route('/admin/x-replies/<int:inbox_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_reject(inbox_id):
    """Reject a draft; tweet will not be replied to."""
    from models import XInboxTweet

    inbox = XInboxTweet.query.get_or_404(inbox_id)
    inbox.status = 'rejected'
    db.session.add(inbox)
    db.session.commit()
    flash('Draft rejected.')
    return redirect('/admin/x-replies')

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
        
        rtsa_hot = []
        rtsa_approved = []
        rtsa_foundational = []
        try:
            from services.rtsa_service import rtsa_service
            rtsa_hot = rtsa_service.get_hot_products()
            rtsa_approved = rtsa_service.get_approved_products(limit=6)
            rtsa_foundational = rtsa_service.get_foundational_statements()
        except Exception as rtsa_error:
            logging.warning(f"RTSA products unavailable: {rtsa_error}")
        
        return render_template('merch.html', 
                             products=formatted_products,
                             rtsa_hot=rtsa_hot,
                             rtsa_approved=rtsa_approved,
                             rtsa_foundational=rtsa_foundational)
    except Exception as e:
        logging.error(f"Error loading merch store: {e}")
        flash('Error loading merchandise. Please try again later.')
        return render_template('merch.html', products=[], rtsa_hot=[], rtsa_approved=[], rtsa_foundational=[])

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

# Sovereign Checkout - Cart and Checkout Routes
@app.route('/api/merch/checkout', methods=['POST'])
def merch_checkout():
    """Create Stripe checkout session for merch purchase, fulfills via Printful"""
    try:
        import stripe
        
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({'error': 'No items provided'}), 400
        
        items = data.get('items', [])
        customer_email = data.get('email', '')
        
        if not items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe_key:
            return jsonify({'error': 'Payment system not configured'}), 500
        
        stripe.api_key = stripe_key
        
        # Build line items for Stripe
        line_items = []
        printful_items = []
        
        for item in items:
            variant_id = item.get('variant_id')
            quantity = item.get('quantity', 1)
            name = item.get('name', 'Product')
            price = float(item.get('price', 0))
            size = item.get('size', '')
            
            # Format for Stripe
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{name} - {size}" if size else name,
                        'description': f'Protocol Pulse Merchandise'
                    },
                    'unit_amount': int(price * 100)
                },
                'quantity': quantity
            })
            
            # Store for Printful fulfillment
            printful_items.append({
                'sync_variant_id': variant_id,
                'quantity': quantity
            })
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=customer_email if customer_email else None,
            success_url=request.url_root + 'merch/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.url_root + 'merch',
            shipping_address_collection={
                'allowed_countries': ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'NL', 'ES', 'IT', 'JP']
            },
            metadata={
                'type': 'merch_order',
                'printful_items': json.dumps(printful_items)
            }
        )
        
        return jsonify({
            'success': True,
            'checkout_url': session.url,
            'session_id': session.id
        })
        
    except Exception as e:
        logging.error(f"Merch checkout error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/merch/success')
def merch_success():
    """Merch purchase success page"""
    session_id = request.args.get('session_id', '')
    return render_template('merch_success.html', session_id=session_id)

@app.route('/webhook/printful', methods=['POST'])
def printful_webhook():
    """Handle Printful webhook for order status updates"""
    try:
        data = request.get_json()
        event_type = data.get('type')
        order_data = data.get('data', {}).get('order', {})
        
        logging.info(f"Printful webhook: {event_type} - Order {order_data.get('id')}")
        
        # Could integrate with notifications here
        return jsonify({'received': True}), 200
    except Exception as e:
        logging.error(f"Printful webhook error: {e}")
        return jsonify({'error': str(e)}), 500

# Category routes
@app.route('/bitcoin')
def bitcoin_category():
    """Bitcoin category page"""
    articles = models.Article.query.filter_by(published=True, category='Bitcoin').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Bitcoin')

@app.route('/defi')
def defi_category():
    """DeFi category page"""
    articles = models.Article.query.filter_by(published=True, category='DeFi').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='DeFi')

@app.route('/regulation')
def regulation_category():
    """Regulation category page"""
    articles = models.Article.query.filter_by(published=True, category='Regulation').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Regulation')

@app.route('/privacy')
def privacy_category():
    """Privacy category page"""
    articles = models.Article.query.filter_by(published=True, category='Privacy').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Privacy')

@app.route('/innovation')
def innovation_category():
    """Innovation category page"""
    articles = models.Article.query.filter_by(published=True, category='Innovation').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Innovation')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy policy (legal)."""
    return render_template('privacy_policy.html')

def _send_contact_notification_email(submission):
    """Send a notification email to CONTACT_EMAIL when SENDGRID_API_KEY is set."""
    to_email = os.environ.get("CONTACT_EMAIL") or os.environ.get("SENDGRID_FROM_EMAIL")
    if not to_email:
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
    except ImportError:
        return False
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        return False
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@protocolpulse.io")
    subject = f"[Protocol Pulse Contact] {submission.subject} — {submission.name}"
    body = f"Name: {submission.name}\nEmail: {submission.email}\nSubject: {submission.subject}\n\n{submission.message}"
    message = Mail(
        from_email=Email(from_email, "Protocol Pulse"),
        to_emails=To(to_email),
        subject=subject,
        plain_text_content=Content("text/plain", body),
    )
    try:
        SendGridAPIClient(api_key).send(message)
        return True
    except Exception as e:
        logging.warning("Contact notification email failed: %s", e)
        return False


@app.route('/contact', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def contact():
    """Contact page: GET shows form; POST saves submission and optionally emails."""
    if request.method == 'POST':
        _require_csrf()
        name = (request.form.get("name") or "").strip()[:200]
        email = (request.form.get("email") or "").strip()[:200]
        subject = (request.form.get("subject") or "general").strip()[:100]
        message = (request.form.get("message") or "").strip()[:10000]
        if not name or not email or not message:
            flash("Please fill in name, email, and message.", "error")
            return render_template("contact.html")
        submission = models.ContactSubmission(
            name=name,
            email=email,
            subject=subject or "general",
            message=message,
            ip_address=request.remote_addr,
        )
        try:
            db.session.add(submission)
            db.session.commit()
            _send_contact_notification_email(submission)
            flash("Signal received. We'll respond within 24–48 hours.", "success")
        except Exception as e:
            logging.exception("Contact form save failed: %s", e)
            db.session.rollback()
            flash("Something went wrong. Please try again or email us directly.", "error")
            return render_template("contact.html")
        return redirect(url_for("contact"))
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

# ── B1 Newsletter Engine Routes ──────────────────────────────────────────────

@app.route('/api/newsletter/subscribe', methods=['POST'])
@limiter.limit("5 per minute")
def api_newsletter_subscribe():
    """Subscribe to newsletter — JSON API."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or request.form.get('email', '')).strip().lower()
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Valid email required'}), 400
    source = request.referrer or 'api'
    # Check existing
    existing = models.NewsletterSubscriber.query.filter_by(email=email).first()
    if existing and existing.subscribed:
        return jsonify({'success': False, 'message': 'Already subscribed'}), 409
    if existing and not existing.subscribed:
        existing.subscribed = True
        existing.unsubscribed_at = None
        db.session.commit()
        return jsonify({'success': True, 'message': 'Re-subscribed successfully'})
    sub = models.NewsletterSubscriber(
        email=email,
        unsubscribe_token=str(uuid.uuid4()),
        subscribed=True,
        source=source[:50] if isinstance(source, str) else 'api',
    )
    db.session.add(sub)
    # Also set User flag
    user = models.User.query.filter_by(email=email).first()
    if user:
        user.newsletter_subscribed = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Subscribed to Protocol Pulse'})


@app.route('/unsubscribe')
def newsletter_unsubscribe():
    """CAN-SPAM compliant unsubscribe (LAW 4)."""
    token = request.args.get('token', '').strip()
    if not token:
        return '<html><body style="background:#0a0a0a;color:#f4f5f8;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div style="text-align:center"><h1 style="color:#FF0000">Invalid Link</h1><p>Missing unsubscribe token.</p></div></body></html>', 400
    sub = models.NewsletterSubscriber.query.filter_by(unsubscribe_token=token).first()
    if not sub:
        return '<html><body style="background:#0a0a0a;color:#f4f5f8;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div style="text-align:center"><h1 style="color:#FF0000">Not Found</h1><p>Token not recognized.</p></div></body></html>', 404
    sub.subscribed = False
    sub.unsubscribed_at = datetime.utcnow()
    # Also update User table
    user = models.User.query.filter_by(email=sub.email).first()
    if user:
        user.newsletter_subscribed = False
    db.session.commit()
    return '''<html><body style="background:#0a0a0a;color:#f4f5f8;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
<div style="text-align:center">
<h1 style="color:#FF0000;letter-spacing:0.1em;">PROTOCOL PULSE</h1>
<p style="font-size:18px;margin-top:20px;">You've been unsubscribed from Protocol Pulse.</p>
<p style="color:#888;font-size:14px;margin-top:10px;">You will no longer receive daily briefings.</p>
<a href="/" style="display:inline-block;margin-top:24px;color:#FF0000;text-decoration:none;border:1px solid #FF0000;padding:10px 24px;border-radius:4px;">Return to Protocol Pulse</a>
</div></body></html>''', 200


@app.route('/api/newsletter/send', methods=['POST'])
def api_newsletter_send():
    """Admin-only: trigger newsletter send."""
    # Check admin session or ADMIN_SECRET header
    admin_ok = False
    if hasattr(current_user, 'is_admin') and current_user.is_authenticated and current_user.is_admin:
        admin_ok = True
    secret = request.headers.get('X-Admin-Secret', '')
    if secret and ADMIN_SECRET and secret == ADMIN_SECRET:
        admin_ok = True
    if not admin_ok:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    from services.newsletter import NewsletterEngine
    engine = NewsletterEngine()
    result = engine.send()
    return jsonify(result)


@app.route('/admin/newsletter')
@login_required
def admin_newsletter():
    """Newsletter admin dashboard."""
    if not current_user.is_admin:
        return redirect(url_for('index'))
    sub_count = models.NewsletterSubscriber.query.filter_by(subscribed=True).count()
    total_subs = models.NewsletterSubscriber.query.count()
    recent_sends = models.NewsletterSend.query.order_by(models.NewsletterSend.sent_at.desc()).limit(10).all()
    last_send = recent_sends[0] if recent_sends else None
    return render_template('admin_newsletter.html',
                           sub_count=sub_count, total_subs=total_subs,
                           recent_sends=recent_sends, last_send=last_send)


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    # Always generate a fresh CSRF token for the login page
    import secrets as _secrets
    if 'csrf_token' not in session or request.method == 'GET':
        session['csrf_token'] = _secrets.token_hex(32)
        session.modified = True

    if request.method == 'POST':
        # CSRF check for login — lenient: if token missing from session, allow but warn
        form_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
        session_token = session.get('csrf_token', '')
        if form_token and session_token and form_token != session_token:
            # Tokens present but don't match — genuine CSRF attempt, block it
            abort(400, 'Invalid CSRF token')
        # If either token is missing entirely (Cloudflare session issue), allow through
        # since login itself doesn't carry sensitive session state to steal

        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = models.User.query.filter_by(username=login_input).first()
        if not user:
            user = models.User.query.filter_by(email=login_input).first()
        if user and user.password_hash and user.check_password(password):
            login_user(user)
            session.pop('csrf_token', None)  # Clear token after successful login
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
    total_articles = models.Article.query.count()
    published_articles = models.Article.query.filter_by(published=True).count()
    total_podcasts = models.Podcast.query.count()
    recent_articles = models.Article.query.order_by(models.Article.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_articles=total_articles,
                         published_articles=published_articles,
                         total_podcasts=total_podcasts,
                         recent_articles=recent_articles)

# ============================================================
# ADMIN INTELLIGENCE DASHBOARD API ROUTES
# ============================================================

@app.route('/api/admin/pipeline-stats')
@login_required
@admin_required
def api_admin_pipeline_stats():
    """Pipeline health: article counts, video render status."""
    now = datetime.utcnow()
    h24 = now - timedelta(hours=24)
    d7 = now - timedelta(days=7)
    h1 = now - timedelta(hours=1)

    articles_24h = models.Article.query.filter(models.Article.created_at >= h24).count()
    articles_7d = models.Article.query.filter(models.Article.created_at >= d7).count()
    articles_total = models.Article.query.count()
    articles_published = models.Article.query.filter_by(published=True).count()
    articles_draft = models.Article.query.filter_by(published=False).count()
    articles_1h = models.Article.query.filter(models.Article.created_at >= h1).count()

    # Daily sparkline: count per day for last 7 days
    sparkline = []
    for i in range(6, -1, -1):
        day_start = now - timedelta(days=i + 1)
        day_end = now - timedelta(days=i)
        cnt = models.Article.query.filter(
            models.Article.created_at >= day_start,
            models.Article.created_at < day_end
        ).count()
        sparkline.append(cnt)

    # Last video render — check logs
    last_video = None
    try:
        report_paths = [
            os.path.expanduser('~/protocol_pulse/logs/daily_pulse.report.json'),
            os.path.expanduser('~/protocol_pulse/logs/medley_pipeline_report.json'),
            os.path.expanduser('~/protocol_pulse/logs/medley_daily_beat.report.json'),
        ]
        for rpath in report_paths:
            if os.path.exists(rpath):
                mtime = os.path.getmtime(rpath)
                ts = datetime.utcfromtimestamp(mtime).isoformat() + 'Z'
                last_video = {'path': os.path.basename(rpath), 'timestamp': ts}
                break
    except Exception:
        pass

    # Next briefing (13:00 UTC daily)
    next_briefing = now.replace(hour=13, minute=0, second=0, microsecond=0)
    if next_briefing <= now:
        next_briefing += timedelta(days=1)

    return jsonify({
        'articles_24h': articles_24h,
        'articles_7d': articles_7d,
        'articles_total': articles_total,
        'articles_published': articles_published,
        'articles_draft': articles_draft,
        'articles_1h': articles_1h,
        'sparkline': sparkline,
        'last_video': last_video,
        'next_briefing': next_briefing.isoformat() + 'Z',
        'timestamp': now.isoformat() + 'Z',
    })


@app.route('/api/admin/audience-stats')
@login_required
@admin_required
def api_admin_audience_stats():
    """Newsletter subscribers, email stats."""
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        total_subs = models.NewsletterSubscriber.query.filter_by(subscribed=True).count()
        total_unsub = models.NewsletterSubscriber.query.filter_by(subscribed=False).count()
        new_today = models.NewsletterSubscriber.query.filter(
            models.NewsletterSubscriber.subscribed_at >= today_start,
            models.NewsletterSubscriber.subscribed == True
        ).count()
        new_week = models.NewsletterSubscriber.query.filter(
            models.NewsletterSubscriber.subscribed_at >= week_start,
            models.NewsletterSubscriber.subscribed == True
        ).count()
        unsub_week = models.NewsletterSubscriber.query.filter(
            models.NewsletterSubscriber.unsubscribed_at >= week_start
        ).count()

        last_send = models.NewsletterSend.query.order_by(models.NewsletterSend.sent_at.desc()).first()
        last_send_data = None
        if last_send:
            last_send_data = {
                'subject': last_send.subject,
                'sent_at': last_send.sent_at.isoformat() + 'Z' if last_send.sent_at else None,
                'recipient_count': last_send.recipient_count,
                'open_count': getattr(last_send, 'open_count', 0),
                'click_count': getattr(last_send, 'click_count', 0),
            }

        next_email = now.replace(hour=13, minute=0, second=0, microsecond=0)
        if next_email <= now:
            next_email += timedelta(days=1)

        return jsonify({
            'total_subscribers': total_subs,
            'total_unsubscribed': total_unsub,
            'new_today': new_today,
            'new_week': new_week,
            'unsub_week': unsub_week,
            'last_send': last_send_data,
            'next_email': next_email.isoformat() + 'Z',
            'timestamp': now.isoformat() + 'Z',
        })
    except Exception as e:
        return jsonify({'error': str(e), 'total_subscribers': 0})


@app.route('/api/admin/content-stats')
@login_required
@admin_required
def api_admin_content_stats():
    """Top articles, sentiment distribution, affiliate clicks."""
    now = datetime.utcnow()
    d7 = now - timedelta(days=7)

    top_articles_q = models.Article.query.filter_by(published=True)\
        .order_by(models.Article.created_at.desc()).limit(10).all()
    top_articles = [{
        'id': a.id,
        'title': a.title[:70],
        'category': a.category,
        'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
    } for a in top_articles_q]

    # Sentiment distribution from SentimentReport
    sentiment_dist = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    try:
        reports = models.SentimentReport.query.order_by(models.SentimentReport.report_date.desc()).limit(30).all()
        for r in reports:
            s = (r.overall_sentiment or '').lower()
            if 'bull' in s:
                sentiment_dist['bullish'] += 1
            elif 'bear' in s:
                sentiment_dist['bearish'] += 1
            else:
                sentiment_dist['neutral'] += 1
    except Exception:
        pass

    # Affiliate click counts per partner
    affiliate_data = []
    try:
        partners = models.AffiliatePartner.query.filter_by(is_active=True).all()
        for p in partners:
            clicks_7d = models.AffiliateClick.query.filter(
                models.AffiliateClick.partner_id == p.id,
                models.AffiliateClick.clicked_at >= d7
            ).count()
            clicks_total = models.AffiliateClick.query.filter_by(partner_id=p.id).count()
            affiliate_data.append({
                'name': p.name,
                'slug': p.slug,
                'clicks_7d': clicks_7d,
                'clicks_total': clicks_total,
            })
    except Exception:
        pass

    # Draft queue
    draft_queue = models.Article.query.filter_by(published=False)\
        .order_by(models.Article.created_at.desc()).limit(5).all()
    draft_list = [{
        'id': a.id,
        'title': a.title[:60],
        'category': a.category,
        'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
    } for a in draft_queue]

    return jsonify({
        'top_articles': top_articles,
        'sentiment_dist': sentiment_dist,
        'affiliate_data': affiliate_data,
        'draft_queue': draft_list,
        'timestamp': now.isoformat() + 'Z',
    })


@app.route('/api/admin/system-health')
@login_required
@admin_required
def api_admin_system_health():
    """CPU, RAM, disk, GPU, recent errors."""
    import psutil
    import subprocess

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # GPU via nvidia-smi
    gpu = None
    try:
        gpu_out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total',
             '--format=csv,noheader,nounits'],
            timeout=3
        ).decode().strip().split(',')
        gpu = {
            'utilization': float(gpu_out[0].strip()),
            'temp': float(gpu_out[1].strip()),
            'memory_used': float(gpu_out[2].strip()),
            'memory_total': float(gpu_out[3].strip()),
        }
    except Exception:
        pass

    # Recent errors from gunicorn error log
    errors = []
    log_paths = [
        os.path.expanduser('~/protocol_pulse/logs/gunicorn_error.log'),
        os.path.expanduser('~/logs/gunicorn_error.log'),
    ]
    for lp in log_paths:
        try:
            with open(lp, 'r') as f:
                lines = f.readlines()[-200:]
            for line in lines:
                if 'ERROR' in line or 'CRITICAL' in line or 'Traceback' in line:
                    errors.append(line.strip()[:200])
            errors = errors[-10:]
            break
        except Exception:
            pass

    # Uptime
    uptime_seconds = None
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = int(datetime.utcnow().timestamp() - boot_time)
    except Exception:
        pass

    return jsonify({
        'cpu_pct': cpu,
        'ram_used_gb': round(ram.used / (1024**3), 1),
        'ram_total_gb': round(ram.total / (1024**3), 1),
        'ram_pct': round(ram.percent, 1),
        'disk_used_gb': round(disk.used / (1024**3), 1),
        'disk_total_gb': round(disk.total / (1024**3), 1),
        'disk_pct': round(disk.percent, 1),
        'gpu': gpu,
        'recent_errors': errors,
        'uptime_seconds': uptime_seconds,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    })


@app.route('/api/admin/revenue-stats')
@login_required
@admin_required
def api_admin_revenue_stats():
    """Stripe MRR, active Commander subscribers."""
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe_key:
        return jsonify({'available': False})

    try:
        import stripe as _stripe
        _stripe.api_key = stripe_key

        commander_count = models.User.query.filter(
            models.User.subscription_tier.in_(['commander', 'sovereign'])
        ).count()

        mrr_cents = 0
        recent_charges = []
        try:
            subs = _stripe.Subscription.list(status='active', limit=100)
            for sub in subs.data:
                for item in sub['items']['data']:
                    plan = item.get('plan') or item.get('price', {})
                    amount = plan.get('amount', 0) or 0
                    interval = plan.get('interval', 'month')
                    if interval == 'year':
                        mrr_cents += amount // 12
                    else:
                        mrr_cents += amount
        except Exception:
            pass

        try:
            charges = _stripe.Charge.list(limit=5, created={'gte': int((datetime.utcnow() - timedelta(days=30)).timestamp())})
            for ch in charges.data:
                if ch.paid:
                    recent_charges.append({
                        'amount': ch.amount / 100,
                        'currency': ch.currency.upper(),
                        'created': datetime.utcfromtimestamp(ch.created).isoformat() + 'Z',
                        'description': ch.description or '',
                    })
        except Exception:
            pass

        return jsonify({
            'available': True,
            'mrr_usd': round(mrr_cents / 100, 2),
            'commander_count': commander_count,
            'recent_charges': recent_charges,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        })
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})


@app.route('/admin/youtube-auth')
@login_required
@admin_required
def admin_youtube_auth():
    """YouTube OAuth authorization page"""
    from services.youtube_service import YouTubeService
    yt = YouTubeService()
    
    is_configured = yt.is_oauth_configured()
    is_authorized = yt.is_upload_authorized()
    channel_info = yt.get_authorized_channel_info() if is_authorized else None
    auth_url = None
    
    if is_configured and not is_authorized:
        auth_url, state = yt.get_oauth_url()
        session['youtube_oauth_state'] = state
    
    return render_template('admin/youtube_auth.html',
                          is_configured=is_configured,
                          is_authorized=is_authorized,
                          channel_info=channel_info,
                          auth_url=auth_url)

@app.route('/oauth/youtube/callback')
def youtube_oauth_callback():
    """Handle YouTube OAuth callback"""
    from services.youtube_service import YouTubeService
    yt = YouTubeService()
    
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        flash(f'YouTube authorization failed: {error}', 'error')
        return redirect('/admin/youtube-auth')
    
    if not code:
        flash('No authorization code received', 'error')
        return redirect('/admin/youtube-auth')
    
    tokens = yt.exchange_oauth_code(code)
    
    if tokens and tokens.get('refresh_token'):
        refresh_token = tokens['refresh_token']
        flash(f'YouTube authorized successfully! Add this refresh token to your secrets as YOUTUBE_REFRESH_TOKEN: {refresh_token[:20]}...', 'success')
        return render_template('admin/youtube_token.html', refresh_token=refresh_token)
    else:
        flash('Failed to get refresh token. Please try again.', 'error')
        return redirect('/admin/youtube-auth')

@app.route('/admin/api/upload-short', methods=['POST'])
@login_required
@admin_required
def admin_upload_short():
    """Upload a video clip as a YouTube Short"""
    from services.youtube_service import YouTubeService
    yt = YouTubeService()
    
    data = request.get_json()
    clip_path = data.get('clip_path')
    title = data.get('title', 'Protocol Pulse Signal')
    description = data.get('description')
    tags = data.get('tags')
    privacy = data.get('privacy', 'private')
    
    if not clip_path:
        return jsonify({'success': False, 'error': 'No clip path provided'}), 400
    
    result = yt.upload_short(clip_path, title, description, tags, privacy)
    return jsonify(result)

@app.route('/admin/api/post-to-x', methods=['POST'])
@login_required
@admin_required
def admin_post_to_x():
    """Post a video clip or text to X/Twitter"""
    from services.x_service import XService
    x_service = XService()
    
    data = request.get_json()
    clip_path = data.get('clip_path')
    caption = data.get('caption', 'Protocol Pulse Signal')
    article_url = data.get('article_url')
    
    # Check if X is configured
    status = x_service.get_upload_status()
    if not status['configured']:
        return jsonify({'success': False, 'error': 'X/Twitter API not configured'}), 400
    
    if clip_path:
        # Post video clip
        if not os.path.exists(clip_path):
            return jsonify({'success': False, 'error': f'Clip not found: {clip_path}'}), 404
        
        tweet_id = x_service.post_clip_with_link(
            video_path=clip_path,
            title=caption,
            article_url=article_url
        )
        
        if tweet_id:
            return jsonify({
                'success': True, 
                'tweet_id': tweet_id,
                'tweet_url': f'https://x.com/i/status/{tweet_id}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to post video to X'}), 500
    else:
        # Post text only (for article promotion)
        tweet_id = x_service.post_article_tweet(
            type('Article', (), {'title': caption, 'id': data.get('article_id', '')})(),
            base_url=request.host_url.rstrip('/')
        )
        
        if tweet_id:
            return jsonify({
                'success': True,
                'tweet_id': str(tweet_id),
                'tweet_url': f'https://x.com/i/status/{tweet_id}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to post to X'}), 500

@app.route('/admin/api/x-status')
@login_required
@admin_required
def admin_x_status():
    """Check X/Twitter API status"""
    from services.x_service import XService
    x_service = XService()
    return jsonify(x_service.get_upload_status())

@app.route('/admin/api/dry-run-dual-image-news', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dry_run_dual_image_news():
    """
    Dry-run breaking news dual-image post: draft text + cover + branded asset, no actual post.
    Query/body: article_id (int). Uses article title and header_image_url; returns what would be posted.
    """
    article_id = request.args.get('article_id') or (request.get_json(silent=True) or {}).get('article_id')
    if article_id is None or article_id == '':
        return jsonify({'success': False, 'error': 'article_id required'}), 400
    try:
        article_id = int(article_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'article_id must be an integer'}), 400
    article = models.Article.query.get(article_id)
    if not article:
        return jsonify({'success': False, 'error': 'Article not found'}), 404
    base_url = request.host_url.rstrip('/')
    article_url = f"{base_url}/articles/{article.id}"
    draft_text = (article.title[:200] + "..." if len(article.title) > 200 else article.title) + "\n\n" + article_url
    if len(draft_text) > 280:
        draft_text = draft_text[:277] + "..."
    cover_url = article.header_image_url or None
    if not cover_url:
        cover_url = f"{base_url}/static/images/default-header.png"
    from services.x_service import XService
    x_service = XService()
    result = x_service.post_dual_image_news(draft_text, cover_url, dry_run=True)
    result['article_id'] = article_id
    result['article_title'] = article.title
    result['cover_url_resolved'] = cover_url
    return jsonify({'success': True, 'dry_run': result})

@app.route('/admin/generate')
@login_required
@admin_required
def admin_generate():
    """Content Command Center - All content generation tools"""
    prompts = models.ContentPrompt.query.filter_by(active=True).all()
    total_articles = models.Article.query.count()
    published_articles = models.Article.query.filter_by(published=True).count()
    total_podcasts = models.Podcast.query.count()
    
    # Count clips
    try:
        from services.ai_clips_service import ai_clips_service
        total_clips = len(ai_clips_service.get_all_clips())
    except:
        total_clips = 0
    
    return render_template('admin/content_command.html', 
                          prompts=prompts,
                          total_articles=total_articles,
                          published_articles=published_articles,
                          total_podcasts=total_podcasts,
                          total_clips=total_clips)

@app.route('/api/generate-article', methods=['POST'])
@login_required
@admin_required
def api_generate_article():
    """API endpoint to generate articles
    
    Supports headline_style parameter:
    - 'question': Generate question-style headlines (e.g., "Is Bitcoin Mining Decentralizing?")
    - 'statement': Generate statement-style headlines (e.g., "Bitcoin Network Reaches 850 EH/s")
    - None/omitted: Randomly select between question and statement styles
    """
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip().replace('<', '&lt;').replace('>', '&gt;')
        source_type = data.get('source_type', 'ai_generated')
        prompt_id = data.get('prompt_id')
        headline_style = data.get('headline_style')  # 'question', 'statement', or None for random
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Get trending topics from Reddit if source is reddit
        if source_type == 'reddit':
            reddit_posts = reddit_service.get_trending_topics(['cryptocurrency', 'bitcoin', 'ethereum', 'web3'])
            if reddit_posts:
                # Use the first relevant post as context
                topic = f"{topic} - Context from Reddit: {reddit_posts[0].get('title', '')}"
        
        # Generate article using AI with headline style support
        article_data = content_generator.generate_article(topic, prompt_id, headline_style=headline_style)
        
        if not article_data:
            return jsonify({'error': 'Failed to generate article'}), 500
        
        # FACT-CHECK GATE: Block auto-publishing if fact-check failed
        fact_check_warnings = article_data.get('fact_check_warnings', [])
        fact_check_passed = article_data.get('fact_check_passed', True)
        
        if not fact_check_passed:
            # Save as DRAFT for human review - do NOT auto-publish
            logging.warning(f"FACT-CHECK BLOCKED: Article '{article_data['title'][:50]}' has verification errors: {fact_check_warnings}")
            
            article = models.Article(
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
        article = models.Article(
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
        article = models.Article.query.get_or_404(article_id)
        
        # Use AI review and approval workflow BEFORE setting published=True
        approval_result = content_engine.approve_and_publish_article(article_id)
        if not approval_result["success"]:
            return jsonify({'error': f'AI review failed: {approval_result.get("errors", ["Unknown error"])}'}, 500)
        
        # Only set published after AI approval
        article.published = True
        db.session.commit()

        # LAW 1: Trigger sentiment classification within 60s of publication (non-blocking)
        _trigger_sentiment_classification(article_id)

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
            
        article = models.Article.query.get_or_404(article_id)
        
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
        
        article = models.Article.query.get_or_404(article_id)
        
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

@app.route('/admin/sentiment-report', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_sentiment_report():
    """View and trigger daily sentiment reports"""
    
    if request.method == 'POST':
        try:
            from services.sentiment_tracker_service import sentiment_tracker
            article_id = sentiment_tracker.run_daily_report()
            if article_id:
                flash(f'Sentiment report generated! Article ID: {article_id}', 'success')
            else:
                flash('No report generated - may already exist for today', 'warning')
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('admin_sentiment_report'))
    
    reports = models.SentimentReport.query.order_by(models.SentimentReport.report_date.desc()).limit(30).all()
    return render_template('admin/sentiment_reports.html', reports=reports)


@app.route('/api/sentiment/generate', methods=['POST'])
def api_generate_sentiment():
    """API endpoint to trigger sentiment report generation"""
    try:
        from services.sentiment_tracker_service import sentiment_tracker
        article_id = sentiment_tracker.run_daily_report()
        if article_id:
            return jsonify({'success': True, 'article_id': article_id})
        return jsonify({'success': False, 'message': 'Report already exists for today'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sentiment')
def sentiment_dashboard():
    """Public sentiment dashboard — real-time article classification + narrative intelligence."""
    import json as _json
    from sqlalchemy import text as _text

    # ── Latest sentiment report ───────────────────────────────────────────────
    try:
        latest_report = db.session.execute(
            _text("""SELECT report_date, overall_sentiment, score, bullish_pct, bearish_pct,
                            neutral_pct, narrative, top_bullish_signals, top_bearish_signals,
                            dominant_narrative, anomaly_detected, created_at
                     FROM sentiment_reports ORDER BY report_date DESC LIMIT 1""")
        ).fetchone()
    except Exception:
        latest_report = None

    # ── 7-day score history ───────────────────────────────────────────────────
    try:
        score_rows = db.session.execute(
            _text("""SELECT report_date, score, overall_sentiment
                     FROM sentiment_reports ORDER BY report_date DESC LIMIT 7""")
        ).fetchall()
        score_history = [
            {"date": str(r[0]), "score": float(r[1] or 50), "sentiment": r[2] or "neutral"}
            for r in reversed(score_rows)
        ]
    except Exception:
        score_history = []

    # ── Recent classified articles ────────────────────────────────────────────
    try:
        article_rows = db.session.execute(
            _text("""SELECT id, title, summary, sentiment, sentiment_confidence,
                            narrative_label, importance_score, source_url, created_at
                     FROM articles
                     WHERE published=1
                     ORDER BY importance_score DESC NULLS LAST, created_at DESC
                     LIMIT 20""")
        ).fetchall()
        recent_articles = []
        for r in article_rows:
            recent_articles.append({
                "id": r[0], "title": r[1], "summary": (r[2] or "")[:200],
                "sentiment": r[3] or "unclassified",
                "confidence": float(r[4] or 0),
                "narrative_label": r[5] or "—",
                "importance_score": int(r[6] or 50),
                "source_url": r[7],
                "created_at": str(r[8]),
            })
    except Exception:
        recent_articles = []

    # ── Anomaly events ────────────────────────────────────────────────────────
    try:
        anomaly_rows = db.session.execute(
            _text("""SELECT id, event_type, severity, description, created_at
                     FROM intelligence_events
                     WHERE severity IN ('warning', 'critical')
                     ORDER BY created_at DESC LIMIT 5""")
        ).fetchall()
        anomaly_events = [
            {"id": r[0], "type": r[1], "severity": r[2], "description": r[3], "created_at": str(r[4])}
            for r in anomaly_rows
        ]
    except Exception:
        anomaly_events = []

    # ── Parse signals from JSON ───────────────────────────────────────────────
    top_bullish = []
    top_bearish = []
    if latest_report:
        try:
            top_bullish = _json.loads(latest_report[7] or "[]")[:5]
        except Exception:
            pass
        try:
            top_bearish = _json.loads(latest_report[8] or "[]")[:5]
        except Exception:
            pass

    return render_template(
        'sentiment_dashboard.html',
        latest_report=latest_report,
        score_history=score_history,
        score_history_json=_json.dumps(score_history),
        recent_articles=recent_articles,
        top_bullish=top_bullish,
        top_bearish=top_bearish,
        anomaly_events=anomaly_events,
    )


@app.route('/intelligence/legacy')
def intelligence_page():
    """
    SESSION 12 UPGRADE — Signal Intelligence command center (legacy).
    /intelligence now serves the Intelligence Terminal (Phase 1 blueprint).
    """
    import json as _json
    from sqlalchemy import text as _text
    from datetime import timedelta as _td

    try:
        from services.intelligence_service import (
            get_signal_strength, get_trending_topics,
            get_entity_tracker, get_narrative_timeline, get_intelligence_events
        )
        signal = get_signal_strength()
        trending = get_trending_topics(hours=24)
        entities = get_entity_tracker(hours=48)
        narrative_timeline = get_narrative_timeline(days=7)
        intel_events = get_intelligence_events(limit=8)
    except Exception as e:
        logging.error("intelligence_page service error: %s", e)
        signal = {"composite": 50, "label": "NEUTRAL", "color": "#f8c15c", "components": {}, "trajectory": "UNKNOWN"}
        trending = []
        entities = []
        narrative_timeline = []
        intel_events = []

    # ── 24h article count ─────────────────────────────────────────────────────
    try:
        cutoff_24h = (datetime.utcnow() - _td(hours=24)).isoformat()
        article_count_24h = db.session.execute(
            _text("SELECT COUNT(*) FROM articles WHERE published=1 AND created_at >= :c"),
            {"c": cutoff_24h}
        ).fetchone()[0]
    except Exception:
        article_count_24h = 0

    # ── Top articles by importance ────────────────────────────────────────────
    try:
        imp_rows = db.session.execute(
            _text("""SELECT id, title, sentiment, narrative_label, importance_score,
                            market_impact_magnitude, created_at
                     FROM articles WHERE published=1
                     ORDER BY importance_score DESC NULLS LAST, created_at DESC
                     LIMIT 15""")
        ).fetchall()
        top_articles = [
            {
                "id": r[0], "title": r[1],
                "sentiment": r[2] or "unclassified",
                "narrative_label": r[3] or "—",
                "importance_score": int(r[4] or 50),
                "impact": float(r[5] or 5.0),
                "created_at": str(r[6]),
            }
            for r in imp_rows
        ]
    except Exception:
        top_articles = []

    # ── SESSION 12: Sentiment summary + heatmap + anomaly ────────────────────
    try:
        from core.services.sentiment_engine import (
            get_sentiment_summary, get_category_heatmap, check_anomaly
        )
        sentiment_summary = get_sentiment_summary(db.session, _text)
        category_heatmap = get_category_heatmap(db.session, _text)
        anomaly_active = check_anomaly(db.session, _text)
    except Exception as e:
        logging.warning("intelligence_page: sentiment engine error: %s", e)
        sentiment_summary = {
            "overall_sentiment": "neutral", "score": 50,
            "bullish_pct": 33, "bearish_pct": 33, "neutral_pct": 34,
            "dominant_narrative": "other", "momentum": "stable",
            "updated_at": datetime.utcnow().isoformat(),
        }
        category_heatmap = []
        anomaly_active = False

    return render_template(
        'intelligence_page.html',
        signal=signal,
        trending=trending,
        entities=entities,
        narrative_timeline=narrative_timeline,
        intel_events=intel_events,
        article_count_24h=article_count_24h,
        top_articles=top_articles,
        signal_json=_json.dumps(signal, default=str),
        trending_json=_json.dumps(trending),
        # SESSION 12 additions
        sentiment_summary=sentiment_summary,
        category_heatmap=category_heatmap,
        category_heatmap_json=_json.dumps(category_heatmap),
        anomaly_active=anomaly_active,
        sentiment_summary_json=_json.dumps(sentiment_summary),
    )


@app.route('/api/stream/sentiment')
def stream_sentiment():
    """
    SSE endpoint — push classification events as they happen.
    Client connects once and receives events in real-time.
    """
    import queue
    import time as _time

    def event_stream():
        try:
            from services.sentiment_analyzer import register_sse_subscriber, unregister_sse_subscriber
        except Exception as e:
            logging.error("stream_sentiment: import failed: %s", e)
            yield "data: {\"error\": \"service unavailable\"}\n\n"
            return

        q = queue.Queue(maxsize=50)
        register_sse_subscriber(q)
        try:
            # Send initial connection confirmation
            yield "retry: 5000\n"
            yield "data: {\"type\": \"connected\", \"ts\": " + str(int(_time.time())) + "}\n\n"

            heartbeat_interval = 30  # seconds
            last_heartbeat = _time.monotonic()

            while True:
                try:
                    # Wait up to 1 second for new event
                    event = q.get(timeout=1.0)
                    import json as _j
                    yield f"data: {_j.dumps(event, default=str)}\n\n"
                    last_heartbeat = _time.monotonic()
                except queue.Empty:
                    # Heartbeat to keep connection alive
                    if _time.monotonic() - last_heartbeat >= heartbeat_interval:
                        yield ": heartbeat\n\n"
                        last_heartbeat = _time.monotonic()
        except GeneratorExit:
            pass
        finally:
            unregister_sse_subscriber(q)

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response


@app.route('/api/sentiment/classify', methods=['POST'])
def api_classify_article():
    """Trigger classification of a specific article. Admin or internal use."""
    try:
        data = request.get_json(silent=True) or {}
        article_id = data.get('article_id')
        if not article_id:
            return jsonify({'success': False, 'error': 'article_id required'}), 400

        from services.sentiment_analyzer import classify_article
        result = classify_article(int(article_id))
        if result:
            return jsonify({'success': True, 'result': result})
        return jsonify({'success': False, 'error': 'classification failed'})
    except ValueError:
        return jsonify({'success': False, 'error': 'invalid article_id'}), 400
    except Exception as e:
        logging.error("api_classify_article error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sentiment/batch', methods=['POST'])
def api_batch_classify():
    """Trigger batch classification. Rate-limited."""
    try:
        data = request.get_json(silent=True) or {}
        hours = int(data.get('hours', 6))
        hours = max(1, min(48, hours))  # clamp to 1-48h

        from services.sentiment_analyzer import batch_classify
        result = batch_classify(hours=hours)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logging.error("api_batch_classify error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/intelligence/signal')
def api_signal_strength():
    """Return signal strength composite. Cached 5 minutes."""
    try:
        from services.intelligence_service import get_signal_strength
        result = get_signal_strength()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error("api_signal_strength error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── SESSION 12: Sentiment Intelligence Engine ────────────────────────────────

@app.route('/api/v2/sentiment/summary')
def api_v2_sentiment_summary():
    """
    SESSION 12 — Aggregate sentiment summary.
    Returns: overall_sentiment, score, bullish_pct, bearish_pct, neutral_pct,
             dominant_narrative, momentum, anomaly, updated_at
    """
    from sqlalchemy import text as _t
    try:
        from core.services.sentiment_engine import (
            get_sentiment_summary, check_anomaly
        )
        summary = get_sentiment_summary(db.session, _t)
        anomaly = check_anomaly(db.session, _t)
        summary["anomaly"] = anomaly
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        logging.error("api_v2_sentiment_summary error: %s", e)
        # Graceful fallback
        return jsonify({
            "success": True,
            "data": {
                "overall_sentiment": "neutral",
                "score": 50,
                "bullish_pct": 33,
                "bearish_pct": 33,
                "neutral_pct": 34,
                "dominant_narrative": "other",
                "momentum": "stable",
                "anomaly": False,
                "updated_at": datetime.utcnow().isoformat(),
            }
        })


@app.route('/api/v2/sentiment/heatmap')
def api_v2_sentiment_heatmap():
    """
    SESSION 12 — Per-category sentiment heatmap data.
    Returns list of category cells with bullish/bearish/neutral counts.
    """
    from sqlalchemy import text as _t
    try:
        from core.services.sentiment_engine import get_category_heatmap
        cells = get_category_heatmap(db.session, _t)
        return jsonify({"success": True, "data": cells})
    except Exception as e:
        logging.error("api_v2_sentiment_heatmap error: %s", e)
        return jsonify({"success": True, "data": []})


@app.route('/sarah-briefing')
def sarah_briefing():
    """Sarah's Daily Intelligence Briefing page"""
    
    latest_brief = models.SarahBrief.query.order_by(models.SarahBrief.brief_date.desc()).first()
    
    past_briefs = models.SarahBrief.query.order_by(models.SarahBrief.brief_date.desc()).offset(1).limit(7).all()
    
    emergency_flash = models.EmergencyFlash.query.filter(
        models.EmergencyFlash.acknowledged == False
    ).order_by(models.EmergencyFlash.triggered_at.desc()).first()
    
    return render_template('sarah_briefing.html',
                          latest_brief=latest_brief,
                          past_briefs=past_briefs,
                          emergency_flash=emergency_flash)


@app.route('/api/sarah-briefing/generate', methods=['POST'])
def api_generate_sarah_briefing():
    """API endpoint to trigger Sarah's daily briefing generation"""
    import traceback
    try:
        from services.briefing_engine import briefing_engine
        article_id = briefing_engine.generate_daily_brief()
        if article_id:
            return jsonify({'success': True, 'article_id': article_id})
        return jsonify({'success': False, 'message': 'Briefing already exists for today or no signals available'})
    except Exception as e:
        import logging
        logging.error(f"Sarah briefing API error: {e}")
        logging.error(traceback.format_exc())
        error_msg = str(e) if str(e) else repr(e)
        return jsonify({'success': False, 'error': error_msg})


@app.route('/api/sarah-briefing/check-flash', methods=['POST'])
def api_check_emergency_flash():
    """API endpoint to check for emergency sentiment shifts"""
    try:
        from services.briefing_engine import briefing_engine
        result = briefing_engine.check_emergency_flash()
        if result:
            return jsonify({'success': True, 'flash': result})
        return jsonify({'success': True, 'flash': None, 'message': 'No emergency conditions detected'})
    except Exception as e:
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
            article = models.Article(
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
        result = generate_podcasts_from_partners()
        return jsonify({
            'success': True,
            'message': 'Partner podcast generation completed',
            'videos_found': result.get('videos_found'),
            'articles_generated': len(result.get('articles_generated', [])),
            'podcasts_generated': len(result.get('podcasts_generated', [])),
        })
    except Exception as e:
        logging.error(f"Batch podcast generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/admin/spaces/recap', methods=['POST'])
@login_required
@admin_required
def admin_space_recap():
    """
    Generate a post-Space recap tweet from a transcript and optionally post to X.
    Body: JSON with keys:
      - space_id (optional, used if transcript_text is empty)
      - transcript_text (optional; if omitted we call get_space_transcript)
      - provider (optional, default 'xspacestream')
      - auto_post (bool, default True)
    """
    data = request.get_json(force=True, silent=True) or {}
    space_id = data.get('space_id') or ''
    transcript_text = (data.get('transcript_text') or '').strip()
    provider = data.get('provider') or 'xspacestream'
    auto_post = bool(data.get('auto_post', True))

    if not transcript_text and not space_id:
        return jsonify({'success': False, 'error': 'space_id or transcript_text required'}), 400

    try:
        if not transcript_text and space_id:
            space_data = get_space_transcript(space_id=space_id, provider=provider)
            transcript_text = (space_data or {}).get('transcript_text', '') or ''

        recap = summarize_for_tweet(transcript_text)
        tweet_text = (recap.get('tweet_text') or '').strip()
        if not tweet_text:
            return jsonify({'success': False, 'error': 'No recap text could be generated'}), 500

        tweet_id = None
        x_status = "not_posted"
        if auto_post:
            try:
                from services.x_service import XService
                x = XService()
                if x.client:
                    tweet_id = x.client.update_status(tweet_text).id
                    x_status = "posted"
                else:
                    x_status = "skipped_no_client"
            except Exception as e:
                logging.error("Space recap X post failed: %s", e)
                x_status = "error"

        return jsonify({
            'success': True,
            'recap': recap,
            'tweet_text': tweet_text,
            'tweet_id': tweet_id,
            'x_status': x_status,
        })
    except Exception as e:
        logging.error("admin_space_recap failed: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/extract-clips', methods=['POST'])
@login_required
@admin_required
def api_extract_clips():
    """Extract viral clips from a YouTube video using AI transcript analysis"""
    try:
        from services.ai_clips_service import ai_clips_service
        
        data = request.get_json() or {}
        video_id = data.get('video_id')
        num_clips = data.get('num_clips', 5)
        
        if not video_id:
            return jsonify({'success': False, 'error': 'Video ID required'})
        
        result = ai_clips_service.process_video(video_id, max_clips=num_clips)
        
        return jsonify({
            'success': True,
            'message': f"Extracted {len(result.get('clips', []))} clips from video",
            'clips': result.get('clips', [])
        })
    except Exception as e:
        logging.error(f"Clip extraction failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/api/process-partner-clips', methods=['POST'])
@login_required
@admin_required
def api_process_partner_clips():
    """Process all partner channels for viral clips"""
    try:
        from services.ai_clips_service import ai_clips_service
        
        result = ai_clips_service.process_partner_channels()
        
        return jsonify({
            'success': True,
            'clips_created': result.get('clips_created', 0),
            'channels_processed': result.get('channels_processed', 0)
        })
    except Exception as e:
        logging.error(f"Partner clip processing failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/process-partner-channels', methods=['POST'])
@login_required
@admin_required
def process_partner_channels():
    """Process all partner YouTube channels for new content"""
    try:
        from services.automation import process_all_partner_channels
        
        result = process_all_partner_channels()
        
        return jsonify({
            'success': True,
            'message': 'Partner channels processed',
            'videos_found': result.get('videos_found', 0),
            'articles_generated': result.get('articles_generated', 0),
            'podcasts_generated': result.get('podcasts_generated', 0)
        })
    except Exception as e:
        logging.error(f"Partner channel processing failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/run-daily-pipeline', methods=['POST'])
@login_required
@admin_required
def run_daily_pipeline():
    """Run the full daily content automation pipeline"""
    try:
        data = request.get_json() or {}
        include_reddit = data.get('include_reddit', True)
        include_youtube = data.get('include_youtube', True)
        auto_publish = data.get('auto_publish', False)
        
        results = {
            'reddit_articles': 0,
            'youtube_content': 0,
            'total_generated': 0
        }
        
        if include_reddit:
            try:
                from services.automation import generate_from_trending_reddit
                reddit_result = generate_from_trending_reddit()
                results['reddit_articles'] = reddit_result.get('articles_generated', 0)
            except Exception as e:
                logging.warning(f"Reddit generation skipped: {e}")
        
        if include_youtube:
            try:
                from services.automation import process_all_partner_channels
                yt_result = process_all_partner_channels()
                results['youtube_content'] = yt_result.get('articles_generated', 0) + yt_result.get('podcasts_generated', 0)
            except Exception as e:
                logging.warning(f"YouTube processing skipped: {e}")
        
        results['total_generated'] = results['reddit_articles'] + results['youtube_content']
        
        return jsonify({
            'success': True,
            'message': f"Daily pipeline complete. Generated {results['total_generated']} pieces of content.",
            'results': results
        })
    except Exception as e:
        logging.error(f"Daily pipeline failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate-social-package', methods=['POST'])
@login_required
@admin_required
def admin_generate_social_package():
    """Alias route for social package generation from content command center"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Partner Channel')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'Video ID required'})
    
    try:
        package = podcast_generator.create_full_social_package(
            video_id=video_id,
            channel_name=channel_name
        )
        
        return jsonify({
            'success': True,
            'message': f"Full social package created for {channel_name}",
            'package': package
        })
    except Exception as e:
        logging.error(f"Social package generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate-bitcoin-lens', methods=['POST'])
@login_required
@admin_required
def admin_generate_bitcoin_lens():
    """Generate Bitcoin Lens reactionary article from content command center"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Content Creator')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'Video ID required'})
    
    try:
        result = podcast_generator.generate_bitcoin_lens_article(
            video_id=video_id,
            channel_name=channel_name
        )
        
        return jsonify({
            'success': True,
            'message': f"Bitcoin Lens article generated for {channel_name}",
            'article_id': result.get('article_id'),
            'title': result.get('title')
        })
    except Exception as e:
        logging.error(f"Bitcoin Lens generation failed: {e}")
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
    articles = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(10).all()
    return jsonify([{'id': a.id, 'title': a.title, 'summary': a.summary, 'header_image_url': a.header_image_url or '/static/images/placeholder.jpg'} for a in articles])


@app.route('/api/v2/articles')
def api_v2_articles():
    """V2 JSON articles API for Next.js frontend."""
    from flask import jsonify
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    category = request.args.get('category', None)
    sort = request.args.get('sort', 'newest')

    q = models.Article.query
    if category:
        q = q.filter(models.Article.category.ilike(f'%{category}%'))
    if sort == 'popular':
        q = q.order_by(models.Article.read_count.desc(), models.Article.created_at.desc())
    else:
        q = q.order_by(models.Article.created_at.desc())

    total = q.count()
    articles = q.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'articles': [{
            'id': a.id,
            'title': a.title or '',
            'slug': a.slug or str(a.id),
            'summary': re.sub(r'<[^>]+>', ' ', (a.summary or a.content or '')).strip()[:300],
            'content': a.content or '',
            'category': a.category or 'Bitcoin',
            'cover_image_url': a.cover_image_url or '',
            'author': a.author or 'Protocol Pulse',
            'created_at': a.created_at.isoformat() if a.created_at else '',
            'read_count': a.read_count or 0,
            'published': True,
        } for a in articles],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page),
        'pagination': {
            'page': page,
            'total_pages': max(1, (total + per_page - 1) // per_page),
            'has_prev': page > 1,
            'has_next': page < max(1, (total + per_page - 1) // per_page),
        },
    })


@app.route('/api/v2/articles/<slug>')
def api_v2_article_detail(slug):
    """Single article by slug or id for Next.js frontend."""
    from flask import jsonify
    # Try slug first, then id
    a = models.Article.query.filter_by(slug=slug).first()
    if not a:
        try:
            a = models.Article.query.get(int(slug))
        except (ValueError, TypeError):
            pass
    if not a:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'article': {
        'id': a.id,
        'title': a.title or '',
        'slug': a.slug or str(a.id),
        'summary': (a.summary or a.content or '')[:300],
        'content': a.content or '',
        'category': a.category or 'Bitcoin',
        'cover_image_url': a.cover_image_url or '',
        'author': a.author or 'Protocol Pulse',
        'created_at': a.created_at.isoformat() if a.created_at else '',
        'read_count': a.read_count or 0,
        'published': True,
    }})


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

# Register social monitoring blueprint (optional)
try:
    from routes_social import social
    app.register_blueprint(social)
except (ModuleNotFoundError, ImportError) as e:
    logging.warning("routes_social not loaded - social monitoring blueprint not registered: %s", e)

# Register Terminal API / Premium API blueprint (skip if already registered by app.py)
try:
    from routes_premium_api import premium_api
    if 'premium_api' not in [bp.name for bp in app.iter_blueprints()]:
        app.register_blueprint(premium_api)
        logging.info("Terminal API blueprint (routes_premium_api) registered from routes.py")
except (ModuleNotFoundError, ImportError, ValueError) as e:
    logging.warning("routes_premium_api not loaded: %s", e)

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
        
        article = models.Article(
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
    article = models.Article.query.get_or_404(article_id)
    
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
        article = models.Article.query.get_or_404(article_id)
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
    ads = models.Advertisement.query.all()
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
        ad = models.Advertisement(
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
        ad = models.Advertisement.query.get_or_404(ad_id)
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
        ad = models.Advertisement.query.get_or_404(ad_id)
        
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
        active_ads = models.Advertisement.query.filter_by(is_active=True).all()
        
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

@app.route('/api/live-tweets')
def api_live_tweets():
    """API endpoint to get live tweets from designated Bitcoin thought leaders"""
    from datetime import datetime, timedelta
    import random
    
    sovereign_handles = [
        {'handle': 'saylor', 'name': 'Michael Saylor', 'verified': True, 'avatar': '🟠'},
        {'handle': 'gladstein', 'name': 'Alex Gladstein', 'verified': True, 'avatar': '⚡'},
        {'handle': 'LynAldenContact', 'name': 'Lyn Alden', 'verified': True, 'avatar': '📊'},
        {'handle': 'jack', 'name': 'jack', 'verified': True, 'avatar': '🔵'},
        {'handle': 'DocumentingBTC', 'name': 'Documenting Bitcoin', 'verified': True, 'avatar': '📜'},
        {'handle': 'lopp', 'name': 'Jameson Lopp', 'verified': True, 'avatar': '🔐'},
        {'handle': 'NickSzabo4', 'name': 'Nick Szabo', 'verified': True, 'avatar': '💡'},
        {'handle': 'adam3us', 'name': 'Adam Back', 'verified': True, 'avatar': '⛏️'},
        {'handle': 'LawrenceLepard', 'name': 'Lawrence Lepard', 'verified': True, 'avatar': '🦁'},
        {'handle': 'CaitlinLong_', 'name': 'Caitlin Long', 'verified': True, 'avatar': '🏦'},
        {'handle': 'jackmallers', 'name': 'Jack Mallers', 'verified': True, 'avatar': '⚡'},
        {'handle': 'BitcoinMagazine', 'name': 'Bitcoin Magazine', 'verified': True, 'avatar': '📰'},
    ]
    
    sample_tweets = [
        "The network fundamentals have never been stronger. Hashrate at ATH. Difficulty adjusting up. Sovereign nodes increasing.",
        "Bitcoin is the only asset in history that gets more secure and more decentralized as it becomes more valuable.",
        "Central banks are trapped. They can print more money or watch the system collapse. Bitcoin fixes this.",
        "Another day, another record hashrate. The miners are speaking. Are you listening?",
        "Self-custody is not optional. Your keys, your coins. Their keys, their coins.",
        "The Lightning Network is processing more transactions per day than ever. Layer 2 is working.",
        "When you understand Bitcoin, you understand that fiat is the exit scam.",
        "Difficulty adjustment incoming. The protocol doesn't care about your feelings—it just works.",
        "Stack sats. Stay humble. Think in decades, not days.",
        "The separation of money and state is the most important development of our lifetime.",
        "If you don't hold your keys, you don't own your Bitcoin. It's really that simple.",
        "Every 10 minutes, a new block is mined. Every block, the network gets stronger.",
    ]
    
    try:
        tweets = []
        now = datetime.utcnow()
        
        selected_handles = random.sample(sovereign_handles, min(6, len(sovereign_handles)))
        for i, handle_info in enumerate(selected_handles):
            minutes_ago = random.randint(2, 180)
            tweet_time = now - timedelta(minutes=minutes_ago)
            
            if minutes_ago < 60:
                time_ago = f"{minutes_ago}m"
            else:
                time_ago = f"{minutes_ago // 60}h"
            
            tweets.append({
                'id': f'tweet_{handle_info["handle"]}_{i}',
                'handle': f'@{handle_info["handle"]}',
                'name': handle_info['name'],
                'avatar': handle_info['avatar'],
                'text': random.choice(sample_tweets),
                'time_ago': time_ago,
                'created_at': tweet_time.isoformat(),
                'verified': handle_info['verified'],
                'metrics': {
                    'likes': random.randint(50, 5000),
                    'retweets': random.randint(10, 1000),
                    'replies': random.randint(5, 500)
                }
            })
        
        tweets.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'tweets': tweets,
            'connection_status': 'SIMULATED',
            'is_demo': True,
            'last_updated': now.isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching live tweets: {e}")
        return jsonify({
            'success': False,
            'tweets': [],
            'connection_status': 'OFFLINE',
            'error': str(e)
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
    """Webhook endpoint to trigger article generation (cron or admin). Use ?force=1 with POST when logged in as admin to skip cooldown."""
    from services.automation import generate_article_with_tracking

    force = request.args.get("force") in ("1", "true", "yes")
    if force and request.method == "POST":
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            return jsonify({"status": "error", "message": "Admin required to use force=1"}), 403
    result = generate_article_with_tracking(force=force)
    
    if result.get('success'):
        msg = f"Article generated: {result.get('title')}"
        if result.get('stub'):
            msg += " (stub — add OPENAI_API_KEY or GEMINI_API_KEY or ANTHROPIC_API_KEY to enable real drafting)"
        return jsonify({
            'status': 'success',
            'message': msg,
            'article_id': result.get('article_id'),
            'stub': result.get('stub'),
            'error': result.get('error'),
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
    sequences = models.LaunchSequence.query.order_by(models.LaunchSequence.created_at.desc()).all()
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
        
        seq = models.LaunchSequence(
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
    
    articles = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(20).all()
    podcasts = models.Podcast.query.order_by(models.Podcast.published_date.desc()).limit(20).all()
    return render_template('create_launch_sequence.html', articles=articles, podcasts=podcasts)

@app.route('/admin/launch-sequence/<int:seq_id>')
@login_required
@admin_required
def view_launch_sequence(seq_id):
    """View a specific launch sequence"""
    import json
    seq = models.LaunchSequence.query.get_or_404(seq_id)
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
    seq = models.LaunchSequence.query.get_or_404(seq_id)
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
    
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    
    content = seq.primary_post_copy or ""
    if seq.content_id and seq.content_type == 'article':
        article = models.Article.query.get(seq.content_id)
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
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    
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
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    
    data = request.get_json() or {}
    seq.status = 'analyzed'
    seq.actual_velocity_score = data.get('velocity_score', 0)
    seq.replies_first_5min = data.get('replies_early', 0)
    seq.total_engagement = data.get('total_engagement', 0)
    seq.reached_for_you = data.get('reached_for_you', False)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/launch-console/<int:seq_id>/replies')
@login_required
@admin_required
def get_launch_replies(seq_id):
    """Get real-time replies for the launch console"""
    from services.x_service import XService
    
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    x_service = XService()
    
    twitter_handle = seq.twitter_handle if hasattr(seq, 'twitter_handle') else 'ProtocolPulseIO'
    
    if seq.tweet_id:
        metrics = x_service.get_velocity_metrics(seq.tweet_id, seq.published_at, twitter_handle)
    else:
        metrics = {
            'total_replies': 0,
            'replies_0_5': 0,
            'replies_5_15': 0,
            'replies_15_30': 0,
            'velocity_score': 0,
            'reached_threshold': False,
            'replies': x_service._get_mock_replies()
        }
    
    return jsonify(metrics)


@app.route('/launch-console/<int:seq_id>/generate-draft', methods=['POST'])
@login_required
@admin_required
def generate_reply_draft(seq_id):
    """Generate a new reply draft for a specific incoming reply"""
    from services.launch_sequence import launch_sequence_service
    
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    data = request.get_json() or {}
    incoming_text = data.get('incoming_text', '')
    strategy = data.get('strategy', 'Technical')
    
    if not launch_sequence_service.client:
        return jsonify({'draft': 'AI service not available. Use manual reply.'})
    
    try:
        prompt = f"""You are PBX from Protocol Pulse. Generate a reply to this tweet:
        
"{incoming_text}"

Strategy: {strategy}
Your reply must be under 280 characters. Be substantive but concise.
Add value to the conversation. Reference Bitcoin/crypto context when relevant."""

        response = launch_sequence_service.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=150
        )
        
        draft = (response.choices[0].message.content or '').strip()
        return jsonify({'draft': draft, 'strategy': strategy})
        
    except Exception as e:
        logging.error(f"Error generating reply draft: {e}")
        return jsonify({'draft': 'Error generating draft. Try again.', 'error': str(e)})


# ============================================
# TARGET ALERT ROUTES
# ============================================

@app.route('/admin/target-alerts')
@login_required
@admin_required
def admin_target_alerts():
    """View all target alerts"""
    alerts = models.TargetAlert.query.order_by(models.TargetAlert.created_at.desc()).limit(50).all()
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
        
        alert = models.TargetAlert(
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
    alert = models.TargetAlert.query.get_or_404(alert_id)
    alert.status = 'approved'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/target-alert/<int:alert_id>/skip', methods=['POST'])
@login_required
@admin_required
def skip_alert(alert_id):
    """Skip an alert"""
    alert = models.TargetAlert.query.get_or_404(alert_id)
    alert.status = 'skipped'
    db.session.commit()
    return jsonify({'success': True})

# ============================================
# ============================================
# NOSTR INTELLIGENCE ROUTES (F4)
# Gospel: GOSPEL.md — LAW 1-5 compliant
# ============================================

@app.route('/nostr')
def nostr_page():
    """Public-facing Nostr onboarding + live signal feed."""
    try:
        from services.nostr_service import get_top_content, get_relay_status
        top_content = get_top_content(limit=10)
        relay_status = get_relay_status()
    except Exception as e:
        logging.warning("nostr_page service error: %s", e)
        top_content = []
        relay_status = [
            {"relay": r, "connected": False, "last_event_at": None, "events_today": 0}
            for r in ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band", "wss://relay.primal.net"]
        ]

    pp_npub = os.environ.get("NOSTR_NPUB", "npub1protocolpulsexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    return render_template(
        'nostr.html',
        top_content=top_content,
        relay_status=relay_status,
        pp_npub=pp_npub,
    )


@app.route('/api/nostr/top')
def nostr_top():
    """GET → top 10 Nostr events by engagement score."""
    try:
        limit = min(int(request.args.get('limit', 10)), 25)
        from services.nostr_service import get_top_content
        content = get_top_content(limit=limit)
        return jsonify(content)
    except Exception as e:
        logging.warning("nostr_top error: %s", e)
        return jsonify([])


@app.route('/api/nostr/relay-status')
def nostr_relay_status():
    """GET → relay connection status."""
    try:
        from services.nostr_service import get_relay_status
        status = get_relay_status()
        return jsonify(status)
    except Exception as e:
        logging.warning("nostr_relay_status error: %s", e)
        relays = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band", "wss://relay.primal.net"]
        return jsonify([
            {"relay": r, "connected": False, "last_event_at": None, "events_today": 0}
            for r in relays
        ])


@app.route('/api/nostr/publish', methods=['POST'])
@login_required
@admin_required
def nostr_publish():
    """POST {content, kind} → publish to all Nostr relays. Admin only. LAW 5 enforced."""
    try:
        data = request.get_json(silent=True) or {}
        content = (data.get('content') or '').strip()
        kind = int(data.get('kind', 1))

        if not content:
            return jsonify({"success": False, "error": "content required"}), 400
        if len(content) > 4096:
            return jsonify({"success": False, "error": "content too long (max 4096 chars)"}), 400
        if kind not in (1, 30023):
            return jsonify({"success": False, "error": "kind must be 1 or 30023"}), 400

        from nostr.nostr_publisher import sign_and_publish, get_daily_post_count
        result = sign_and_publish(content=content, kind=kind)
        result["daily_count"] = get_daily_post_count()
        return jsonify(result)
    except Exception as e:
        logging.error("nostr_publish error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/nostr/stats')
def nostr_stats():
    """GET → aggregate stats (event count, relay status)."""
    try:
        from services.nostr_service import get_stats, get_relay_status
        stats = get_stats()
        relay_status = get_relay_status()
        connected = sum(1 for r in relay_status if r.get("connected"))
        stats["relays_connected"] = connected
        stats["relays_total"] = len(relay_status)
        return jsonify(stats)
    except Exception as e:
        logging.warning("nostr_stats error: %s", e)
        return jsonify({"total_events": 0, "events_today": 0, "tracked_pubkeys": 0, "relays_connected": 0, "relays_total": 4})


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
    events = models.NostrEvent.query.order_by(models.NostrEvent.created_at.desc()).limit(50).all()
    
    return render_template('admin_nostr.html', status=status, events=events)

@app.route('/admin/nostr/test', methods=['POST'])
@login_required
@admin_required
def test_nostr():
    """Test Nostr broadcast"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    result = nostr_broadcaster.test_connection()
    
    if result.get('success'):
        event = models.NostrEvent(
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
        event = models.NostrEvent(
            event_id=result.get('event_id'),
            content_type=content_type,
            content_id=content_id,
            relays_success=json.dumps(result.get('relays_success', [])),
            relays_failed=json.dumps(result.get('relays_failed', []))
        )
        db.session.add(event)
        db.session.commit()
    
    return jsonify(result)

# ============================================
# INTELLIGENCE DASHBOARD
# ============================================

@app.route('/admin/intelligence')
@login_required
@admin_required
def intelligence_dashboard():
    """Main intelligence dashboard with all metrics"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    articles_count = models.Article.query.filter_by(published=True).count()
    podcasts_count = models.Podcast.query.count()
    
    launch_sequences = models.LaunchSequence.query.order_by(models.LaunchSequence.created_at.desc()).limit(5).all()
    pending_sequences = models.LaunchSequence.query.filter_by(status='draft').count()
    
    target_alerts = models.TargetAlert.query.filter_by(status='pending').order_by(models.TargetAlert.created_at.desc()).limit(5).all()
    pending_alerts = models.TargetAlert.query.filter_by(status='pending').count()
    
    nostr_status = nostr_broadcaster.get_relay_status()
    nostr_events = models.NostrEvent.query.count()
    total_zaps = db.session.query(db.func.sum(models.NostrEvent.zaps_amount_sats)).scalar() or 0
    
    avg_velocity = db.session.query(db.func.avg(models.LaunchSequence.actual_velocity_score)).filter(
        models.LaunchSequence.actual_velocity_score.isnot(None)
    ).scalar() or 0
    
    reply_squad = models.ReplySquadMember.query.filter_by(active=True).order_by(
        models.ReplySquadMember.reciprocal_engagements.desc()
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
    members = models.ReplySquadMember.query.order_by(models.ReplySquadMember.priority, models.ReplySquadMember.handle).all()
    return render_template('admin_reply_squad.html', members=members)

@app.route('/admin/reply-squad/add', methods=['POST'])
@login_required
@admin_required
def add_reply_squad_member():
    """Add a new reply squad member"""
    data = request.get_json() or request.form
    
    member = models.ReplySquadMember(
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
        existing = models.ReplySquadMember.query.filter_by(handle=member_data['handle']).first()
        if not existing:
            member = models.ReplySquadMember(
                handle=member_data['handle'],
                display_name=member_data.get('name', ''),
                category=member_data.get('category', 'general'),
                priority=member_data.get('priority', 2)
            )
            db.session.add(member)
    
    db.session.commit()
    flash('Reply squad initialized!')
    return redirect(url_for('admin_reply_squad'))

@app.route('/api/prediction-oracle')
def api_prediction_oracle():
    """Prediction Oracle API - Returns live prediction market odds"""
    import random
    
    # Simulated prediction market data (Polymarket/Kalshi style)
    predictions = [
        {
            'id': 'btc_100k_2026',
            'question': 'BTC > $100K by Dec 2026?',
            'yes_odds': 72 + random.randint(-5, 5),
            'no_odds': 28 + random.randint(-5, 5),
            'volume': random.randint(500000, 2000000),
            'source': 'Protocol Pulse Oracle'
        },
        {
            'id': 'eth_etf_approval',
            'question': 'Spot ETH ETF approval by Q2 2026?',
            'yes_odds': 85 + random.randint(-3, 3),
            'no_odds': 15 + random.randint(-3, 3),
            'volume': random.randint(200000, 800000),
            'source': 'Protocol Pulse Oracle'
        },
        {
            'id': 'fed_rate_cut',
            'question': 'Fed rate cut before June 2026?',
            'yes_odds': 58 + random.randint(-8, 8),
            'no_odds': 42 + random.randint(-8, 8),
            'volume': random.randint(1000000, 5000000),
            'source': 'Protocol Pulse Oracle'
        },
        {
            'id': 'btc_strategic_reserve',
            'question': 'US Strategic Bitcoin Reserve by 2027?',
            'yes_odds': 35 + random.randint(-10, 10),
            'no_odds': 65 + random.randint(-10, 10),
            'volume': random.randint(300000, 1200000),
            'source': 'Protocol Pulse Oracle'
        }
    ]
    
    return jsonify({
        'success': True,
        'predictions': predictions,
        'updated': datetime.utcnow().isoformat()
    })

@app.route('/admin/auth-cleanup', methods=['POST'])
@login_required
@admin_required
def admin_auth_cleanup():
    """Purge all Orange Is The New Jill related data from database"""
    try:
        purged_count = 0
        
        # Clean up articles with Orange Is The New Jill content
        articles = models.Article.query.filter(
            db.or_(
                models.Article.title.ilike('%orange is the new jill%'),
                models.Article.title.ilike('%orange is the nw jill%'),
                models.Article.content.ilike('%orange is the new jill%')
            )
        ).all()
        
        for article in articles:
            db.session.delete(article)
            purged_count += 1
        
        # Clean up podcasts with Orange Is The New Jill content
        podcasts = models.Podcast.query.filter(
            db.or_(
                models.Podcast.title.ilike('%orange is the new jill%'),
                models.Podcast.title.ilike('%orange is the nw jill%'),
                models.Podcast.description.ilike('%orange is the new jill%')
            )
        ).all()
        
        for podcast in podcasts:
            db.session.delete(podcast)
            purged_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'purged_count': purged_count,
            'message': f'Successfully purged {purged_count} Orange Is The New Jill items'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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


@app.route('/hub')
@login_required
@premium_hub_required
def premium_hub():
    """Premium Hub: tiered command center for Operator / Commander / Sovereign subscribers."""
    from datetime import datetime, timedelta
    try:
        network = NodeService.get_network_stats()
    except Exception:
        network = {}
    try:
        mempool_data = fetch_mempool_data()
    except Exception:
        mempool_data = {}
    try:
        prices = price_service.get_prices()
    except Exception:
        prices = {}
    # Latest briefs (all subs)
    latest_briefs = models.Article.query.filter_by(published=True).order_by(models.Article.updated_at.desc()).limit(5).all()
    # Commander+ only: Pro Briefs (premium_tier commander/sovereign or featured)
    try:
        commander_briefs = models.Article.query.filter(
            models.Article.published.is_(True),
            db.or_(
                models.Article.premium_tier.in_(['commander', 'sovereign']),
                models.Article.featured.is_(True)
            )
        ).order_by(models.Article.updated_at.desc()).limit(5).all()
    except Exception:
        commander_briefs = models.Article.query.filter_by(
            published=True, featured=True
        ).order_by(models.Article.updated_at.desc()).limit(5).all()
    # Whale feed (last 24h) and alert summary — Commander+
    since_24h = datetime.utcnow() - timedelta(hours=24)
    since_7d = datetime.utcnow() - timedelta(days=7)
    hub_whales = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.detected_at >= since_24h
    ).order_by(models.WhaleTransaction.detected_at.desc()).limit(20).all()
    whale_count_24h = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.detected_at >= since_24h
    ).count()
    mega_count_24h = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.detected_at >= since_24h,
        models.WhaleTransaction.is_mega.is_(True)
    ).count()
    whale_count_7d = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.detected_at >= since_7d
    ).count()
    mega_count_7d = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.detected_at >= since_7d,
        models.WhaleTransaction.is_mega.is_(True)
    ).count()
    # 24h whale volume in USD (for premium metric card)
    btc_price = (prices or {}).get('btc') or 0
    whale_volume_usd_24h = sum((w.usd_value or (w.btc_amount * btc_price) or 0) for w in hub_whales)
    # Pro Brief of the week (single highlighted for Commander+)
    brief_of_the_week = (commander_briefs[0] if commander_briefs else None)
    # Sovereign: monthly ask status
    sovereign_ask = None
    sovereign_asks_this_month = 0
    if getattr(current_user, 'subscription_tier', None) == 'sovereign':
        try:
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            sovereign_asks_this_month = models.PremiumAsk.query.filter(
                models.PremiumAsk.user_id == current_user.id,
                models.PremiumAsk.created_at >= month_start
            ).count()
            sovereign_ask = models.PremiumAsk.query.filter_by(
                user_id=current_user.id
            ).order_by(models.PremiumAsk.created_at.desc()).first()
        except Exception:
            pass
    tier = getattr(current_user, 'subscription_tier', 'free')
    mega_whale_alerts_enabled = getattr(current_user, 'mega_whale_email_alerts', False)
    return render_template('premium_hub.html',
                         network=network,
                         mempool_data=mempool_data,
                         prices=prices,
                         latest_briefs=latest_briefs,
                         commander_briefs=commander_briefs,
                         brief_of_the_week=brief_of_the_week,
                         hub_whales=hub_whales,
                         whale_count_24h=whale_count_24h,
                         mega_count_24h=mega_count_24h,
                         whale_count_7d=whale_count_7d,
                         mega_count_7d=mega_count_7d,
                         whale_volume_usd_24h=whale_volume_usd_24h,
                         sovereign_ask=sovereign_ask,
                         sovereign_asks_this_month=sovereign_asks_this_month,
                         tier=tier,
                         mega_whale_alerts_enabled=mega_whale_alerts_enabled)


@app.route('/hub/ask', methods=['POST'])
@login_required
def hub_submit_ask():
    """Sovereign Elite: submit monthly research ask (1 per month)."""
    if getattr(current_user, 'subscription_tier', None) != 'sovereign':
        flash('Monthly ask is available for Sovereign Elite only.')
        return redirect(url_for('premium_hub'))
    from datetime import datetime
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = models.PremiumAsk.query.filter(
        models.PremiumAsk.user_id == current_user.id,
        models.PremiumAsk.created_at >= month_start
    ).count()
    if used >= 1:
        flash('You have already used your monthly ask this month. Next resets at month start.')
        return redirect(url_for('premium_hub'))
    question = (request.form.get('question') or '').strip()
    if not question or len(question) < 10:
        flash('Please submit a question of at least 10 characters.')
        return redirect(url_for('premium_hub'))
    try:
        ask = models.PremiumAsk(user_id=current_user.id, question_text=question[:2000], status='pending')
        db.session.add(ask)
        db.session.commit()
        flash('Your monthly ask has been submitted. The team will respond via email or in this hub.')
    except Exception as e:
        logging.warning("PremiumAsk submit failed (table may not exist): %s", e)
        flash('Submit temporarily unavailable. Please try again or contact support.')
    return redirect(url_for('premium_hub'))


@app.route('/hub/alerts', methods=['POST'])
@login_required
@premium_hub_required
def hub_alerts_preference():
    """Commander+: toggle mega whale email alerts preference."""
    if not getattr(current_user, 'has_commander_tier', lambda: False)():
        flash('Mega whale alerts are for Commander tier and above.')
        return redirect(url_for('premium_hub'))
    enabled = request.form.get('mega_whale_email') == 'on'
    try:
        current_user.mega_whale_email_alerts = enabled
        db.session.commit()
        flash('Mega whale email alerts ' + ('enabled' if enabled else 'disabled') + '.')
    except Exception as e:
        if getattr(current_user, 'mega_whale_email_alerts', None) is None:
            flash('Alert preference not available yet. Try again after a refresh.')
        else:
            flash('Could not save preference.')
        logging.warning("Hub alerts preference save failed: %s", e)
    return redirect(url_for('premium_hub'))


@app.route('/subscribe/premium/<tier>')
@login_required
def subscribe_premium(tier):
    """Initiate premium subscription checkout"""
    from services.monetization_service import monetization_service
    
    if tier not in ['operator', 'commander', 'sovereign']:
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
@limiter.limit("10 per minute")
def donate():
    """One-time donation page"""
    from services.monetization_service import monetization_service

    if request.method == 'POST':
        _require_csrf()
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

def _schedule_welcome_emails(email: str, tier: str):
    """Schedule 3-email post-payment welcome sequence via background threads."""
    import threading

    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        logging.warning("RESEND_API_KEY not set — skipping welcome email sequence for %s", email)
        return

    def _send_email(subject: str, html_body: str):
        try:
            import requests as _req
            _req.post("https://api.resend.com/emails", json={
                "from": "Protocol Pulse <terminal@protocolpulse.io>",
                "to": [email],
                "subject": subject,
                "html": html_body,
            }, headers={"Authorization": f"Bearer {resend_key}"}, timeout=15)
            logging.info("Welcome email sent to %s: %s", email, subject)
        except Exception as e:
            logging.error("Failed to send welcome email to %s: %s", email, e)

    # Email 1 — Immediate
    def send_email_1():
        _send_email(
            "Terminal access granted — here's what you're seeing",
            "<div style='font-family:monospace;color:#E2E2EF;background:#0A0A0F;padding:32px;'>"
            "<h1 style='color:#FF0033;font-size:16px;letter-spacing:2px;'>TERMINAL ACCESS GRANTED</h1>"
            "<p>Commander,</p>"
            "<p>Your Intelligence Terminal is live. Right now, PCAF is scanning every block for anomalies. "
            "The Convergence Matrix is correlating 8 independent data feeds. The Monte Carlo engine is "
            "running probability distributions across 5 scenarios.</p>"
            "<p>This isn't a dashboard. It's a war room.</p>"
            "<p style='margin-top:24px;'><a href='https://protocolpulse.io/intelligence' "
            "style='color:#00D4FF;'>Enter the Terminal →</a></p>"
            "<p style='color:#555;font-size:12px;margin-top:32px;'>Protocol Pulse · Sovereign Infrastructure</p>"
            "</div>"
        )

    # Email 2 — 72h later
    def send_email_2():
        import time as _time
        _time.sleep(259200)  # 72 hours
        _send_email(
            "PCAF is watching — your first anomaly patterns",
            "<div style='font-family:monospace;color:#E2E2EF;background:#0A0A0F;padding:32px;'>"
            "<h1 style='color:#FFAA00;font-size:16px;letter-spacing:2px;'>PCAF ACTIVE</h1>"
            "<p>Commander,</p>"
            "<p>PCAF v1 uses a Graph Neural Network autoencoder to detect anomalies in Bitcoin's chain state. "
            "When the anomaly score crosses 0.7, it means the GNN reconstruction error is elevated — "
            "something in the mempool, hashrate, or fee structure doesn't fit the pattern.</p>"
            "<p>Most alerts are noise. The ones that aren't tend to precede significant moves by 12-48 hours.</p>"
            "<p>Check your alert history and start voting on accuracy — it calibrates the model.</p>"
            "<p style='margin-top:24px;'><a href='https://protocolpulse.io/intelligence/alerts' "
            "style='color:#00D4FF;'>View Alert History →</a></p>"
            "<p style='color:#555;font-size:12px;margin-top:32px;'>Protocol Pulse · Sovereign Infrastructure</p>"
            "</div>"
        )

    # Email 3 — 7 days later
    def send_email_3():
        import time as _time
        _time.sleep(604800)  # 7 days
        _send_email(
            "The scenario that's forming right now",
            "<div style='font-family:monospace;color:#E2E2EF;background:#0A0A0F;padding:32px;'>"
            "<h1 style='color:#00FF88;font-size:16px;letter-spacing:2px;'>SCENARIO UPDATE</h1>"
            "<p>Commander,</p>"
            "<p>The Monte Carlo engine has been running for a week now. Five scenarios are being tracked, "
            "each with probability distributions updated every 6 hours based on 28 precursor signals.</p>"
            "<p>The engine doesn't predict. It maps probability space — and when probabilities shift, "
            "the contradiction detector flags conflicting signals before you act on incomplete data.</p>"
            "<p>Check which scenario has the highest probability right now.</p>"
            "<p style='margin-top:24px;'><a href='https://protocolpulse.io/intelligence/scenarios' "
            "style='color:#00D4FF;'>View Scenarios →</a></p>"
            "<p style='color:#555;font-size:12px;margin-top:32px;'>Protocol Pulse · Sovereign Infrastructure</p>"
            "</div>"
        )

    threading.Thread(target=send_email_1, daemon=True).start()
    threading.Thread(target=send_email_2, daemon=True).start()
    threading.Thread(target=send_email_3, daemon=True).start()
    logging.info("Welcome email sequence scheduled for %s (%s tier)", email, tier)


@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events including merch orders"""
    import stripe
    from services.monetization_service import monetization_service
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    
    # Check if this is a merch order (custom handling)
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    if stripe_key and webhook_secret:
        stripe.api_key = stripe_key
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            
            if event['type'] == 'checkout.session.completed':
                session_obj = event['data']['object']
                metadata = session_obj.get('metadata', {})

                # Terminal API subscription: provision ApiSubscriber
                if metadata.get('subscription_type') == 'terminal_api':
                    try:
                        from services.stripe_service import provision_terminal_subscriber
                        result = provision_terminal_subscriber(session_obj, db, models)
                        if result.get('success') and result.get('api_key') and result.get('email'):
                            import threading
                            from routes_premium_api import _send_welcome_email
                            t = threading.Thread(
                                target=_send_welcome_email,
                                args=(result['email'], result['api_key']),
                                daemon=True,
                            )
                            t.start()
                    except Exception as e:
                        logging.error(f"Terminal subscriber provisioning error: {e}")

                # Subscription: set user tier by email
                tier = metadata.get('tier')
                if tier in ('operator', 'commander', 'sovereign') and metadata.get('subscription_type') != 'terminal_api':
                    email = session_obj.get('customer_email') or (session_obj.get('customer_details') or {}).get('email')
                    if email:
                        user = models.User.query.filter_by(email=email).first()
                        if user:
                            user.subscription_tier = tier
                            user.stripe_customer_id = session_obj.get('customer')
                            user.stripe_subscription_id = session_obj.get('subscription')
                            try:
                                db.session.commit()
                                logging.info(f"Subscription tier set: {email} -> {tier}")
                                # Post-payment welcome email sequence
                                _schedule_welcome_emails(email, tier)
                            except Exception as e:
                                db.session.rollback()
                                logging.error(f"Error setting subscription tier: {e}")

                # Handle merch orders - submit to Printful
                if metadata.get('type') == 'merch_order':
                    try:
                        printful_items_json = metadata.get('printful_items', '[]')
                        printful_items = json.loads(printful_items_json)
                        shipping = session_obj.get('shipping_details', {})
                        address = shipping.get('address', {})
                        
                        # Create Printful order
                        order_data = {
                            'recipient': {
                                'name': shipping.get('name', ''),
                                'address1': address.get('line1', ''),
                                'address2': address.get('line2', ''),
                                'city': address.get('city', ''),
                                'state_code': address.get('state', ''),
                                'country_code': address.get('country', 'US'),
                                'zip': address.get('postal_code', ''),
                                'email': session_obj.get('customer_details', {}).get('email', '')
                            },
                            'items': printful_items
                        }
                        
                        # Submit to Printful as draft (for review)
                        result = printful_service.create_order(order_data, confirm=False)
                        if result:
                            logging.info(f"Printful order created: {result.get('id')}")
                        else:
                            logging.error("Failed to create Printful order")
                            
                    except Exception as e:
                        logging.error(f"Error processing merch order: {e}")
                    
                    return jsonify({'success': True}), 200
                    
        except Exception as e:
            logging.error(f"Webhook signature verification failed: {e}")
    
    # Fall back to monetization service for other events
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


@app.route('/admin/contact-submissions')
@login_required
@admin_required
def admin_contact_submissions():
    """List contact form submissions; filter by read/unread."""
    read_filter = request.args.get('read', '')
    q = models.ContactSubmission.query
    if read_filter == 'read':
        q = q.filter_by(read=True)
    elif read_filter == 'unread':
        q = q.filter_by(read=False)
    submissions = q.order_by(models.ContactSubmission.created_at.desc()).limit(200).all()
    unread_count = models.ContactSubmission.query.filter_by(read=False).count()
    return render_template('admin/contact_submissions.html', submissions=submissions, read_filter=read_filter, unread_count=unread_count)


@app.route('/admin/contact-submissions/<int:sub_id>/read', methods=['POST'])
@login_required
@admin_required
def admin_contact_submission_mark_read(sub_id):
    """Mark a contact submission as read."""
    _require_csrf()
    sub = models.ContactSubmission.query.get_or_404(sub_id)
    sub.read = True
    db.session.commit()
    flash('Marked as read.', 'success')
    return redirect(url_for('admin_contact_submissions'))


@app.route('/admin/premium-asks')
@login_required
@admin_required
def admin_premium_asks():
    """List Sovereign Elite monthly asks; filter by status."""
    status_filter = request.args.get('status', '')
    q = models.PremiumAsk.query
    if status_filter in ('pending', 'answered'):
        q = q.filter_by(status=status_filter)
    asks = q.order_by(models.PremiumAsk.created_at.desc()).limit(100).all()
    pending_count = models.PremiumAsk.query.filter_by(status='pending').count()
    return render_template('admin/premium_asks.html', asks=asks, status_filter=status_filter, pending_count=pending_count)


@app.route('/admin/premium-asks/<int:ask_id>/answer', methods=['POST'])
@login_required
@admin_required
def admin_premium_ask_answer(ask_id):
    """Mark a PremiumAsk as answered with optional text and URL."""
    from datetime import datetime
    ask = models.PremiumAsk.query.get_or_404(ask_id)
    answer_text = (request.form.get('answer_text') or '').strip()
    answer_url = (request.form.get('answer_url') or '').strip()[:500]
    ask.answer_text = answer_text or None
    ask.answer_url = answer_url or None
    ask.status = 'answered'
    ask.answered_at = datetime.utcnow()
    db.session.commit()
    flash('Ask marked as answered.')
    return redirect(url_for('admin_premium_asks'))


# ============================================
# CAPTIONS.AI VIDEO GENERATION
# ============================================
@app.route('/admin/captions')
@login_required
@admin_required
def admin_captions():
    """Captions.ai video generation dashboard"""
    from services.captions_service import captions_service
    return render_template('admin_captions.html', 
                         initialized=captions_service.initialized,
                         avatars=captions_service.AVATARS)

@app.route('/admin/api/captions/generate', methods=['POST'])
@login_required
@admin_required
def generate_captions_video():
    """Generate AI avatar video via Captions.ai"""
    from services.captions_service import captions_service
    
    data = request.get_json()
    script = data.get('script', '')
    avatar_type = data.get('avatar', 'alex')
    
    if not script:
        return jsonify({'error': 'Script is required'}), 400
    
    if len(script) > 800:
        return jsonify({'error': 'Script must be 800 characters or less'}), 400
    
    result = captions_service.create_video(script, avatar_type)
    
    if result:
        return jsonify({
            'success': True,
            'video_id': result.get('video_id'),
            'status': result.get('status'),
            'message': 'Video generation started'
        })
    else:
        return jsonify({'error': 'Failed to start video generation'}), 500

@app.route('/admin/api/captions/status/<video_id>')
@login_required
@admin_required
def check_captions_status(video_id):
    """Check status of Captions.ai video generation"""
    from services.captions_service import captions_service
    
    result = captions_service.check_video_status(video_id)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to check video status'}), 500

@app.route('/admin/api/captions/daily-brief', methods=['POST'])
@login_required
@admin_required
def generate_daily_brief_video():
    """Generate daily brief video with network data"""
    from services.captions_service import captions_service
    from services.node_service import node_service
    
    data = request.get_json()
    avatar_type = data.get('avatar', 'sarah')
    
    # Get current network data
    network_data = node_service.get_network_stats()
    network_data['price'] = node_service.get_bitcoin_price() or 0
    
    result = captions_service.generate_daily_brief(network_data, avatar_type)
    
    if result:
        return jsonify({
            'success': True,
            'video_id': result.get('video_id'),
            'status': result.get('status'),
            'message': 'Daily brief video generation started'
        })
    else:
        return jsonify({'error': 'Failed to generate daily brief'}), 500

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
    articles = models.Article.query.filter(
        models.Article.published == True,
        models.Article.category.ilike('%cypherpunk%')
    ).order_by(models.Article.created_at.desc()).limit(20).all()
    
    return render_template('cypherpunks.html', 
                          articles=articles,
                          pioneers=CYPHERPUNKS)

@app.route('/guides/cold-storage')
@app.route('/sovereign-custody')
def cold_storage_guide():
    """Sovereign Custody Manual - Hardware wallet setup guides powered by BTC Sessions"""
    return render_template('guides/cold_storage.html')

CYPHERPUNK_DOSSIERS = {
    'Satoshi Nakamoto': {
        'bio': 'The pseudonymous creator of Bitcoin who released the whitepaper in October 2008 and launched the network in January 2009. Satoshi mined the genesis block, communicated via email and forums, then vanished in 2010, leaving behind a revolutionary decentralized monetary system.',
        'quote': 'The root problem with conventional currency is all the trust that\'s required to make it work.',
        'contributions': ['Bitcoin Protocol', 'Proof-of-Work', 'Genesis Block', 'Blockchain']
    },
    'Hal Finney': {
        'bio': 'Legendary cryptographer and cypherpunk who received the first Bitcoin transaction from Satoshi. Creator of Reusable Proofs of Work (RPOW) and key contributor to PGP. Ran Bitcoin\'s first node alongside Satoshi and remained a devoted Bitcoiner until his death in 2014.',
        'quote': 'For Bitcoin to succeed and become secure, I believe that computing power must be distributed among many participants.',
        'contributions': ['First BTC Recipient', 'RPOW', 'PGP Development', 'Early Bitcoin Mining']
    },
    'Wei Dai': {
        'bio': 'Computer engineer and cryptographer who proposed b-money in 1998, a decentralized digital currency concept that directly influenced Bitcoin. His work on theoretical electronic cash systems laid crucial groundwork for cryptocurrency.',
        'quote': 'Unlike conventional money, the b-money system does not require a central authority to create units of currency.',
        'contributions': ['b-money Proposal', 'Crypto++ Library', 'Digital Cash Theory']
    },
    'Nick Szabo': {
        'bio': 'Computer scientist, legal scholar, and cryptographer who created bit gold in 1998, widely considered the most direct precursor to Bitcoin. Coined the term "smart contracts" and developed pioneering work on digital property rights.',
        'quote': 'Trusted third parties are security holes.',
        'contributions': ['Bit Gold', 'Smart Contracts', 'Digital Property Rights']
    },
    'Adam Back': {
        'bio': 'British cryptographer who invented Hashcash in 1997, the proof-of-work system that became the foundation of Bitcoin mining. CEO of Blockstream and one of the most cited individuals in the Bitcoin whitepaper.',
        'quote': 'Bitcoin represents the first time we have achieved true digital scarcity.',
        'contributions': ['Hashcash', 'Proof-of-Work Mining', 'Blockstream', 'Liquid Network']
    },
    'David Chaum': {
        'bio': 'Pioneer of digital cash who invented DigiCash and ecash in the 1980s-90s. Created foundational concepts for anonymous digital payments and secure voting systems. Often called the godfather of digital currency.',
        'quote': 'Security without identification protects the privacy of the individual.',
        'contributions': ['DigiCash', 'Blind Signatures', 'Mix Networks', 'Ecash']
    },
    'Timothy May': {
        'bio': 'Intel physicist turned cryptoanarchist who authored "The Crypto Anarchist Manifesto" in 1988 and co-founded the Cypherpunks mailing list. Envisioned a world where cryptography enables individual sovereignty.',
        'quote': 'Crypto anarchy is about using cryptography to avoid and reduce coercion.',
        'contributions': ['Crypto Anarchist Manifesto', 'Cypherpunks Mailing List', 'BlackNet Concept']
    },
    'Eric Hughes': {
        'bio': 'Mathematician and programmer who co-founded the Cypherpunks movement and wrote "A Cypherpunk\'s Manifesto" in 1993. Advocated for privacy through code, not legislation.',
        'quote': 'Cypherpunks write code. We know that someone has to write software to defend privacy.',
        'contributions': ['Cypherpunk Manifesto', 'Cypherpunks Movement', 'Anonymous Remailers']
    },
    'Whitfield Diffie': {
        'bio': 'American cryptographer who, with Martin Hellman, invented public-key cryptography in 1976. This breakthrough enabled secure communication without pre-shared secrets, making cryptocurrency possible.',
        'quote': 'Public-key cryptography turned the field upside down.',
        'contributions': ['Diffie-Hellman Key Exchange', 'Public-Key Cryptography']
    },
    'Ralph Merkle': {
        'bio': 'Computer scientist who independently invented public-key cryptography and created Merkle trees in the 1970s. Merkle trees are now fundamental to Bitcoin\'s block structure and transaction verification.',
        'quote': 'The goal of cryptography is to enable two entities to communicate in a way that is private.',
        'contributions': ['Merkle Trees', 'Public-Key Cryptography', 'Cryptographic Hashing']
    }
}

@app.route('/api/cypherpunk-dossier')
def api_cypherpunk_dossier():
    """Return dossier data for a specific cypherpunk pioneer"""
    name = request.args.get('name', '')
    
    if name in CYPHERPUNK_DOSSIERS:
        return jsonify({
            'success': True,
            'dossier': CYPHERPUNK_DOSSIERS[name]
        })
    
    return jsonify({'success': False, 'error': 'Pioneer not found'}), 404

# ============================================
# WHALE TRANSACTION API
# ============================================

@app.route('/api/whales')
def api_whales():
    """Get stored whale transactions"""
    
    whales = models.WhaleTransaction.query.order_by(models.WhaleTransaction.detected_at.desc()).limit(50).all()
    
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
    
    data = request.get_json()
    if not data or 'txid' not in data:
        return jsonify({'error': 'Missing txid'}), 400
    
    existing = models.WhaleTransaction.query.filter_by(txid=data['txid']).first()
    if existing:
        return jsonify({'status': 'exists', 'id': existing.id})
    
    btc_amount = data.get('btc', 0)
    is_mega = btc_amount >= 1000
    
    whale = models.WhaleTransaction(
        txid=data['txid'],
        btc_amount=btc_amount,
        usd_value=data.get('usd'),
        fee_sats=data.get('fee'),
        block_height=data.get('block'),
        is_mega=is_mega
    )
    db.session.add(whale)
    db.session.commit()
    
    sms_result = None
    if is_mega:
        try:
            from services.sms_service import sms_service
            source = "cold storage" if data.get('from_cold', False) else "unknown wallet"
            destination = "Exchange" if data.get('to_exchange', False) else "unknown destination"
            alex_analysis = f"High-volume movement detected - {btc_amount:,.0f} BTC indicates significant market activity"
            sms_result = sms_service.mega_whale_alert(btc_amount, source, destination, alex_analysis)
            logging.info(f"MEGA-WHALE SMS DISPATCH: {btc_amount} BTC - {sms_result.get('total_sent', 0)} operatives notified")
        except Exception as sms_err:
            logging.error(f"Mega-whale SMS dispatch error: {sms_err}")
    
    return jsonify({'status': 'saved', 'id': whale.id, 'is_mega': is_mega, 'sms_dispatched': sms_result})

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
    
    data = request.get_json() or {}
    amount_sats = data.get('amount_sats', 21000)
    message = data.get('message', '')
    email = data.get('email', '')
    
    donation = models.BitcoinDonation(
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
                article = models.Article.query.get(int(article_id))
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

# ==================== SOVEREIGN ANALYTICS ENGINE ====================

@app.route('/admin/analytics')
@admin_required
def analytics_dashboard():
    """Sovereign Analytics Dashboard - Self-learning intelligence metrics."""
    from services.analytics_service import analytics_service

    # Get key metrics
    velocity_leaders = analytics_service.get_velocity_leaders(hours=24, limit=10)
    persona_comparison = analytics_service.get_persona_comparison(days=7)
    strategy_effectiveness = analytics_service.get_strategy_effectiveness(days=7)
    hourly_performance = analytics_service.get_hourly_performance(days=7)
    window_stats = analytics_service.get_30min_window_stats(days=7)
    sponsor_metrics = analytics_service.get_sponsor_metrics(days=30)
    
    # Recent events
    recent_events = models.EngagementEvent.query.order_by(
        models.EngagementEvent.created_at.desc()
    ).limit(20).all()
    
    # Top performers all-time
    top_performers = models.ContentPerformance.query.order_by(
        models.ContentPerformance.grok_score_total.desc()
    ).limit(5).all()
    
    return render_template('admin/analytics_dashboard.html',
        velocity_leaders=velocity_leaders,
        persona_comparison=persona_comparison,
        strategy_effectiveness=strategy_effectiveness,
        hourly_performance=hourly_performance,
        window_stats=window_stats,
        sponsor_metrics=sponsor_metrics,
        recent_events=recent_events,
        top_performers=top_performers
    )


@app.route('/api/analytics/track', methods=['POST'])
@admin_required
def track_engagement():
    """API endpoint to track engagement events (admin only for security)."""
    from services.analytics_service import analytics_service
    
    data = request.get_json() or {}
    
    required = ['event_type', 'content_type', 'content_id']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate content exists
    if not analytics_service.validate_content_exists(data['content_type'], int(data['content_id'])):
        return jsonify({'error': 'Content not found'}), 404
    
    request_info = {
        'user_agent': request.headers.get('User-Agent'),
        'referrer': request.headers.get('Referer'),
        'ip': request.remote_addr
    }
    
    try:
        event = analytics_service.track_event(
            event_type=data['event_type'],
            content_type=data['content_type'],
            content_id=int(data['content_id']),
            source_platform=data.get('source_platform', 'website'),
            persona=data.get('persona'),
            strategy=data.get('strategy'),
            request_info=request_info
        )
        
        return jsonify({
            'success': True,
            'event_id': event.id,
            'grok_score': event.grok_score_contribution
        })
    except Exception as e:
        logging.error(f"Analytics tracking error: {e}")
        return jsonify({'error': str(e)}), 500


# Internal tracking endpoint (for programmatic use from services)
def track_internal_event(event_type: str, content_type: str, content_id: int, **kwargs):
    """Internal function for tracking events from services (not exposed as API)."""
    from services.analytics_service import analytics_service
    try:
        return analytics_service.track_event(
            event_type=event_type,
            content_type=content_type,
            content_id=content_id,
            **kwargs
        )
    except Exception as e:
        logging.error(f"Internal tracking error: {e}")
        return None


@app.route('/api/analytics/velocity-leaders')
def api_velocity_leaders():
    """Get top performing content by velocity score."""
    from services.analytics_service import analytics_service
    
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    leaders = analytics_service.get_velocity_leaders(hours=hours, limit=limit)
    return jsonify(leaders)


@app.route('/api/analytics/persona-comparison')
def api_persona_comparison():
    """Compare Alex vs Sarah persona performance."""
    from services.analytics_service import analytics_service
    
    days = request.args.get('days', 7, type=int)
    comparison = analytics_service.get_persona_comparison(days=days)
    return jsonify(comparison)


@app.route('/api/analytics/strategy-effectiveness')
def api_strategy_effectiveness():
    """Get reply strategy effectiveness rankings."""
    from services.analytics_service import analytics_service
    
    days = request.args.get('days', 7, type=int)
    strategies = analytics_service.get_strategy_effectiveness(days=days)
    return jsonify(strategies)


@app.route('/api/analytics/sponsor-metrics')
@admin_required
def api_sponsor_metrics():
    """Get sponsor-ready metrics for pitch decks."""
    from services.analytics_service import analytics_service
    
    days = request.args.get('days', 30, type=int)
    metrics = analytics_service.get_sponsor_metrics(days=days)
    return jsonify(metrics)


@app.route('/api/analytics/export/<format>')
@admin_required
def export_analytics(format):
    """Export analytics data for sponsors (CSV or JSON)."""
    from services.analytics_service import analytics_service
    import csv
    from io import StringIO
    
    days = request.args.get('days', 30, type=int)
    sponsor_metrics = analytics_service.get_sponsor_metrics(days=days)
    velocity_leaders = analytics_service.get_velocity_leaders(hours=days*24, limit=20)
    persona_comparison = analytics_service.get_persona_comparison(days=days)
    
    if format == 'json':
        return jsonify({
            'report_date': datetime.utcnow().isoformat(),
            'period_days': days,
            'sponsor_metrics': sponsor_metrics,
            'velocity_leaders': velocity_leaders,
            'persona_comparison': persona_comparison
        })
    
    elif format == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Protocol Pulse - Sovereign Analytics Report'])
        writer.writerow([f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}'])
        writer.writerow([f'Period: Last {days} days'])
        writer.writerow([])
        
        writer.writerow(['SPONSOR METRICS'])
        for key, value in sponsor_metrics.items():
            writer.writerow([key.replace('_', ' ').title(), value])
        
        writer.writerow([])
        writer.writerow(['TOP PERFORMING CONTENT'])
        writer.writerow(['Title', 'Type', 'Velocity Score', 'Grok Score', 'Replies', 'Profile Visits'])
        for content in velocity_leaders:
            writer.writerow([
                content['title'],
                content['content_type'],
                content['velocity_score'],
                content['grok_score'],
                content['total_replies'],
                content['profile_visits']
            ])
        
        writer.writerow([])
        writer.writerow(['PERSONA A/B TEST RESULTS'])
        writer.writerow(['Alex Engagements', persona_comparison['alex_engagements']])
        writer.writerow(['Sarah Engagements', persona_comparison['sarah_engagements']])
        writer.writerow(['Winner', persona_comparison['winner'].upper()])
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=protocol_pulse_analytics_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        return response
    
    return jsonify({'error': 'Invalid format. Use json or csv'}), 400


# Track real-time operative density across all pages
@app.before_request
def track_operative_activity():
    """Track active operatives on each page for heatmap display"""
    if request.method != 'GET':
        return
    if request.path.startswith('/static/') or request.path.startswith('/api/'):
        return
    if request.path.startswith('/admin/') and not request.path == '/admin':
        return
    
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(bot in user_agent for bot in ['bot', 'crawler', 'spider', 'curl', 'wget', 'replit']):
        return
    
    try:
        import hashlib
        session_hash = hashlib.sha256(
            f"{request.remote_addr}:{request.headers.get('User-Agent', '')}".encode()
        ).hexdigest()[:32]
        
        page_names = {
            '/': 'Home',
            '/live': 'Live Terminal',
            '/media-hub': 'Media Hub',
            '/drill': 'Recovery Drill',
            '/operator-costs': 'Operator Costs',
            '/scorecard': 'Sovereign Scorecard',
            '/whale-watcher': 'Whale Watcher',
            '/value-stream': 'Value Stream',
            '/sovereign-custody': 'Custody Manual',
            '/clips': 'Signal Clips',
            '/solo-slayers': 'Solo Slayers',
            '/freedom-tech': 'Freedom Tech',
            '/merch': 'Sovereign Merch',
            '/meetups': 'Meetups',
            '/podcast': 'Podcasts',
            '/articles': 'Articles',
        }
        
        page_path = request.path.rstrip('/')
        if not page_path:
            page_path = '/'
        page_name = page_names.get(page_path, page_path.split('/')[-1].title() if page_path else 'Home')
        
        models.RollingActivity.record_activity(page_path, page_name, session_hash)
        
        # Cleanup stale records every 100th request (probabilistic)
        import random
        if random.random() < 0.01:  # ~1% of requests trigger cleanup
            models.RollingActivity.cleanup_stale()
    except Exception as e:
        logging.debug(f"Activity tracking error: {e}")


@app.route('/api/activity-heatmap')
def api_activity_heatmap():
    """Get real-time operative density across pages for What's Hot display"""
    try:
        results = models.RollingActivity.get_operative_density(window_minutes=30, limit=8)
        
        heatmap = []
        max_count = max([r.operative_count for r in results], default=1)
        
        for r in results:
            heatmap.append({
                'path': r.page_path,
                'name': r.page_name or r.page_path,
                'operatives': r.operative_count,
                'intensity': min(r.operative_count / max(max_count, 1), 1.0)
            })
        
        return jsonify({
            'success': True,
            'heatmap': heatmap,
            'total_operatives': sum([r.operative_count for r in results]),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logging.error(f"Activity heatmap error: {e}")
        return jsonify({
            'success': False,
            'heatmap': [],
            'error': str(e)
        })


# Track article views with deduplication
_view_cache = {}  # Simple in-memory cache for view deduplication

@app.before_request
def track_article_view():
    """Auto-track article views for analytics with deduplication."""
    if request.path.startswith('/article/') and request.method == 'GET':
        try:
            # Skip bots and admin paths
            user_agent = request.headers.get('User-Agent', '').lower()
            if any(bot in user_agent for bot in ['bot', 'crawler', 'spider', 'curl', 'wget']):
                return
            
            parts = request.path.split('/')
            if len(parts) >= 3 and parts[2].isdigit():
                article_id = int(parts[2])
                
                # Deduplicate views: 1 view per IP per article per 5 minutes
                import hashlib
                ip_hash = hashlib.sha256(request.remote_addr.encode()).hexdigest()[:16]
                cache_key = f"{ip_hash}:{article_id}"
                now = datetime.utcnow().timestamp()
                
                if cache_key in _view_cache:
                    if now - _view_cache[cache_key] < 300:  # 5 minutes
                        return  # Skip duplicate view
                
                _view_cache[cache_key] = now
                
                # Clean old cache entries (keep last 1000)
                if len(_view_cache) > 1000:
                    sorted_keys = sorted(_view_cache, key=_view_cache.get)
                    for k in sorted_keys[:500]:
                        del _view_cache[k]
                
                from services.analytics_service import analytics_service
                
                request_info = {
                    'user_agent': request.headers.get('User-Agent'),
                    'referrer': request.headers.get('Referer'),
                    'ip': request.remote_addr
                }
                
                analytics_service.track_event(
                    event_type='view',
                    content_type='article',
                    content_id=article_id,
                    source_platform='website',
                    request_info=request_info
                )
        except Exception as e:
            logging.debug(f"Article view tracking skipped: {e}")


# ==================== MULTI-AGENT SUPERVISOR ROUTES ====================

@app.route('/admin/supervisor')
@admin_required
def supervisor_dashboard():
    """Multi-Agent Supervisor Dashboard - Alex & Sarah orchestration."""
    return render_template('admin/supervisor_dashboard.html')


@app.route('/api/supervisor/run-task', methods=['POST'])
@admin_required
def run_supervisor_task():
    """Execute a multi-agent task with Alex + Sarah coordination."""
    try:
        from services.multi_agent_supervisor import supervisor, TaskType
        
        data = request.get_json() or {}
        topic = data.get('topic', 'Bitcoin network analysis')
        task_type_str = data.get('task_type', 'ground_truth')
        audience_segment = data.get('audience_segment')
        
        task_type_map = {
            'deep_dive_research': TaskType.DEEP_DIVE_RESEARCH,
            'viral_hook': TaskType.VIRAL_HOOK,
            'ground_truth': TaskType.GROUND_TRUTH,
            'macro_analysis': TaskType.MACRO_ANALYSIS,
            'segment_targeting': TaskType.SEGMENT_TARGETING
        }
        
        task_type = task_type_map.get(task_type_str, TaskType.GROUND_TRUTH)
        
        result = supervisor.run_task(
            topic=topic,
            task_type=task_type,
            audience_segment=audience_segment
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Supervisor task error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/supervisor/auto-assign', methods=['POST'])
@admin_required
def auto_assign_tasks():
    """Auto-assign tasks from trending topics (self-learning loop)."""
    try:
        from services.multi_agent_supervisor import supervisor
        
        data = request.get_json() or {}
        trending_topics = data.get('topics', [])
        
        if not trending_topics:
            trending_topics = [
                {'title': 'Bitcoin network hashrate reaches new ATH'},
                {'title': 'Institutional adoption accelerates in Q1 2025'}
            ]
        
        results = supervisor.auto_assign_from_insights(trending_topics)
        
        return jsonify({
            'success': True,
            'tasks_assigned': len(results),
            'results': results
        })
        
    except Exception as e:
        logging.error(f"Auto-assign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/supervisor/auto-publish', methods=['POST'])
@admin_required
def supervisor_auto_publish():
    """Auto-publish content via Multi-Agent Supervisor to Nostr and X."""
    try:
        from services.launch_sequence import launch_sequence_service
        
        data = request.get_json() or {}
        topic = data.get('topic')
        article_id = data.get('article_id')
        
        result = launch_sequence_service.auto_publish_supervisor_content(
            topic=topic,
            article_id=article_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Auto-publish error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== AUDIENCE SEGMENTATION ROUTES ====================

@app.route('/admin/segments')
@admin_required
def segments_dashboard():
    """Audience Segmentation Dashboard - K-Means clustering visualization."""
    try:
        from services.audience_segmentation import segmentation_engine
        
        summary = segmentation_engine.get_segment_summary()
        
        return render_template(
            'admin/segments_dashboard.html',
            segments=summary.get('segments', []),
            total_users=summary.get('total_users', 0),
            is_trained=segmentation_engine.is_trained
        )
    except Exception as e:
        logging.error(f"Segments dashboard error: {e}")
        return render_template(
            'admin/segments_dashboard.html',
            segments=[],
            total_users=0,
            is_trained=False,
            error=str(e)
        )


@app.route('/api/segments/train', methods=['POST'])
@admin_required
def train_segmentation():
    """Train the K-Means audience segmentation model."""
    try:
        from services.audience_segmentation import segmentation_engine
        
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        result = segmentation_engine.train(days=days)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Segmentation training error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/segments/summary')
@admin_required
def get_segment_summary():
    """Get summary of all audience segments for sponsor reporting."""
    try:
        from services.audience_segmentation import segmentation_engine
        
        summary = segmentation_engine.get_segment_summary()
        
        return jsonify(summary)
        
    except Exception as e:
        logging.error(f"Segment summary error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/segments/recommend', methods=['POST'])
@admin_required
def recommend_segment():
    """Get targeting recommendation for a topic."""
    try:
        from services.audience_segmentation import segmentation_engine
        
        data = request.get_json() or {}
        topic = data.get('topic', '')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        recommendation = segmentation_engine.get_targeting_recommendation(topic)
        
        return jsonify(recommendation)
        
    except Exception as e:
        logging.error(f"Segment recommendation error: {e}")
        return jsonify({'error': str(e)}), 500


# Sentry Megaphone (public) and Real-Time Sponsorship Deck (admin)
@app.route('/sentry')
def sentry():
    """Sentry Megaphone: list social drafts (SentryJob) and legacy queue. No login required."""
    try:
        sentry_jobs = models.SentryJob.query.order_by(models.SentryJob.created_at.desc()).limit(50).all()
    except Exception:
        sentry_jobs = []
    try:
        queue_rows = models.SentryQueue.query.order_by(models.SentryQueue.created_at.desc()).limit(20).all()
        queue_count = models.SentryQueue.query.filter(
            models.SentryQueue.status.in_(["pending", "draft"])
        ).count()
    except Exception:
        queue_rows = []
        queue_count = 0
    return render_template(
        'admin/sentry.html',
        sentry_jobs=sentry_jobs,
        queue_count=queue_count,
        suggestions=[],
        queue_rows=queue_rows,
    )


@app.route('/admin/deck')
@login_required
@admin_required
def admin_deck():
    """Real-Time Sponsorship Deck: live views and impressions for sponsor conversations."""
    from services.sponsorship_metrics_service import get_sponsorship_metrics
    from pathlib import Path
    data_dir = Path(app.root_path) / "data"
    metrics = get_sponsorship_metrics(data_dir=data_dir, db_session=db.session, days_back=30)
    return render_template('admin/sponsorship_deck.html', metrics=metrics)


@app.route('/admin/deck/export-pdf')
@login_required
@admin_required
def admin_deck_export_pdf():
    """Generate Red/Black/White PDF summary of sponsorship metrics."""
    from services.sponsorship_metrics_service import get_sponsorship_metrics
    from pathlib import Path
    from io import BytesIO
    data_dir = Path(app.root_path) / "data"
    metrics = get_sponsorship_metrics(data_dir=data_dir, db_session=db.session, days_back=30)
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        return "reportlab not installed. pip install reportlab", 503
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="DeckTitle", parent=styles["Heading1"], textColor=colors.HexColor("#dc2626"), fontName="Helvetica-Bold", fontSize=18)
    body_style = ParagraphStyle(name="DeckBody", parent=styles["Normal"], textColor=colors.white, fontName="Helvetica", fontSize=10)
    white = colors.HexColor("#ffffff")
    red = colors.HexColor("#dc2626")
    black = colors.HexColor("#0a0a0a")
    story = []
    story.append(Paragraph("PROTOCOL PULSE — SPONSORSHIP METRICS", title_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Period: last {metrics['period_days']} days. Generated: {metrics['generated_at'][:19]} UTC.", body_style))
    story.append(Spacer(1, 0.4 * inch))
    data = [
        ["Metric", "Value", "Source"],
        ["YouTube views", str(metrics.get("youtube_views", 0)), metrics.get("youtube_source", "—")],
        ["Website unique visits", str(metrics.get("website_unique_visits", 0)), metrics.get("website_source", "—")],
        ["Social impressions (X)", str(metrics.get("social_impressions", 0)), metrics.get("social_source", "—")],
    ]
    t = Table(data, colWidths=[2.2 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), red),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), black),
        ("TEXTCOLOR", (0, 1), (-1, -1), white),
        ("GRID", (0, 0), (-1, -1), 0.5, red),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [black, colors.HexColor("#1a1a1a")]),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="protocol_pulse_sponsorship_deck.pdf")


# Sovereign Command Deck Routes
@app.route('/admin/command-deck')
@admin_required
def command_deck():
    """Sovereign Command Deck - System control center"""
    scheduler_status = {'running': False, 'jobs': []}
    telegram_status = {'initialized': False}
    try:
        from services.scheduler import get_scheduler_status
        scheduler_status = get_scheduler_status()
    except Exception as e:
        logging.debug("Scheduler not available: %s", e)
    try:
        from services.telegram_bot import pulse_operative
        telegram_status = pulse_operative.get_status()
    except Exception:
        pass  # telegram_bot optional
    return render_template('admin/command_deck.html',
        scheduler_status=scheduler_status,
        telegram_status=telegram_status,
        deck_time=datetime.utcnow()
    )


@app.route('/admin/api/activate-scheduler', methods=['POST'])
@admin_required
def activate_scheduler():
    """Activate the sovereign scheduler"""
    try:
        from services.scheduler import initialize_scheduler, get_scheduler_status
        
        initialize_scheduler()
        status = get_scheduler_status()
        
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logging.error(f"Scheduler activation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/send-heartbeat', methods=['POST'])
@admin_required
def send_heartbeat():
    """Send Empire Ready heartbeat to Telegram"""
    try:
        from services.sovereign_heartbeat import send_heartbeat_sync, get_system_status
        
        result = send_heartbeat_sync()
        status = get_system_status()
        
        return jsonify({
            'success': result.get('success', False),
            'error': result.get('error'),
            'system_status': status
        })
    except Exception as e:
        logging.error(f"Heartbeat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/system-status')
@admin_required
def get_system_status_api():
    """Get current system status"""
    try:
        from services.sovereign_heartbeat import get_system_status
        return jsonify(get_system_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/clips/status')
@admin_required
def clips_status_api():
    """Get AI Clips service status"""
    try:
        from services.ai_clips_service import ai_clips_service
        return jsonify(ai_clips_service.get_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/clips/generate', methods=['POST'])
@admin_required
def generate_clips_api():
    """Trigger daily clips generation job"""
    try:
        from services.ai_clips_service import ai_clips_service
        results = ai_clips_service.run_daily_clips_job()
        return jsonify(results)
    except Exception as e:
        logging.error(f"Clips generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/clips/process-video', methods=['POST'])
@admin_required
def process_video_clips_api():
    """Process a specific YouTube video for clips"""
    try:
        from services.ai_clips_service import ai_clips_service
        data = request.get_json()
        video_id = data.get('video_id')
        video_title = data.get('title', 'Untitled')
        channel_name = data.get('channel', 'Manual')
        max_clips = data.get('max_clips', 2)
        
        if not video_id:
            return jsonify({'error': 'video_id required'}), 400
        
        results = ai_clips_service.process_video(video_id, video_title, channel_name, max_clips)
        return jsonify({'success': True, 'clips': results})
    except Exception as e:
        logging.error(f"Video processing error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/clips/channels')
@admin_required
def get_clips_channels_api():
    """Get configured clips channels"""
    try:
        from services.ai_clips_service import ai_clips_service
        channels = []
        for ch in ai_clips_service.CLIPS_CHANNELS:
            daily_count = ai_clips_service._get_daily_count(ch['id'])
            channels.append({
                **ch,
                'today_count': daily_count,
                'remaining': ch.get('daily_limit', 1) - daily_count
            })
        return jsonify(channels)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/collect-signals', methods=['POST'])
@admin_required
def collect_signals_api():
    """Trigger signal collection from X, Nostr, and Stacker News APIs"""
    try:
        from services.sentiment_tracker_service import SentimentTrackerService
        tracker = SentimentTrackerService()
        
        x_posts = tracker.fetch_x_posts(hours_back=24)
        nostr_notes = tracker.fetch_nostr_notes(hours_back=24)
        stacker_posts = tracker.fetch_stacker_news(limit=15)
        all_posts = x_posts + nostr_notes + stacker_posts
        saved = tracker.save_signals_to_db(all_posts)
        return jsonify({
            'success': True,
            'collected': {
                'x_posts': len(x_posts),
                'nostr_notes': len(nostr_notes),
                'stacker_news': len(stacker_posts)
            },
            'saved_to_db': saved,
            'message': f'Collected {len(x_posts)} X, {len(nostr_notes)} Nostr, {len(stacker_posts)} Stacker News; saved {saved} new signals'
        })
    except Exception as e:
        logging.error(f"Signal collection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/signals')
@admin_required
def get_collected_signals_api():
    """Get collected signals from database"""
    try:
        
        limit = request.args.get('limit', 50, type=int)
        platform = request.args.get('platform', None)
        legendary_only = request.args.get('legendary', 'false').lower() == 'true'
        
        query = models.CollectedSignal.query.filter(models.CollectedSignal.is_verified == True)
        
        if platform:
            query = query.filter(models.CollectedSignal.platform == platform)
        if legendary_only:
            query = query.filter(models.CollectedSignal.is_legendary == True)
        
        signals = query.order_by(
            models.CollectedSignal.is_legendary.desc(),
            models.CollectedSignal.engagement_score.desc()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(signals),
            'signals': [{
                'id': s.id,
                'platform': s.platform,
                'author_name': s.author_name,
                'author_handle': s.author_handle,
                'author_tier': s.author_tier,
                'content': s.content,
                'url': s.url,
                'engagement_score': s.engagement_score,
                'is_legendary': s.is_legendary,
                'posted_at': s.posted_at.isoformat() if s.posted_at else None,
                'collected_at': s.collected_at.isoformat() if s.collected_at else None
            } for s in signals]
        })
    except Exception as e:
        logging.error(f"Error fetching signals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verified-signals')
def get_verified_signals_public():
    """Public API endpoint for verified signals with proper citations"""
    try:
        
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        signals = models.CollectedSignal.query.filter(
            models.CollectedSignal.is_verified == True,
            models.CollectedSignal.collected_at >= datetime.utcnow() - timedelta(hours=48)
        ).order_by(
            models.CollectedSignal.is_legendary.desc(),
            models.CollectedSignal.engagement_score.desc()
        ).limit(limit).all()
        
        return jsonify({
            'signals': [{
                'author': s.author_name,
                'handle': f"@{s.author_handle}" if not s.author_handle.startswith('@') else s.author_handle,
                'content': s.content[:200] + '...' if len(s.content) > 200 else s.content,
                'url': s.url,
                'platform': s.platform,
                'engagement': s.engagement_score,
                'is_legendary': s.is_legendary,
                'tier': s.author_tier,
                'timestamp': s.posted_at.isoformat() if s.posted_at else s.collected_at.isoformat()
            } for s in signals]
        })
    except Exception as e:
        logging.error(f"Error fetching verified signals: {e}")
        return jsonify({'signals': [], 'error': str(e)}), 200

@app.route('/admin/api/zero-hour-audit', methods=['GET'])
@admin_required
def zero_hour_audit():
    """Zero Hour Readiness Audit - Test all system connections"""
    from sqlalchemy import text
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'telegram': {'status': 'UNKNOWN', 'message': ''},
        'ghl': {'status': 'UNKNOWN', 'message': ''},
        'database': {'status': 'UNKNOWN', 'message': ''},
        'overall': 'CHECKING'
    }
    
    try:
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        results['database'] = {'status': 'ONLINE', 'message': 'PostgreSQL connection verified'}
    except Exception as e:
        results['database'] = {'status': 'OFFLINE', 'message': str(e)}
    
    try:
        ghl_result = ghl_service.verify_api_connection()
        if ghl_result.get('success'):
            results['ghl'] = {'status': 'ONLINE', 'message': f"API verified - Status {ghl_result.get('status_code', 200)}"}
        else:
            results['ghl'] = {'status': 'DEGRADED', 'message': ghl_result.get('error', 'Unknown error')}
    except Exception as e:
        results['ghl'] = {'status': 'OFFLINE', 'message': str(e)}
    
    try:
        from services.telegram_bot import pulse_operative
        if pulse_operative and pulse_operative.initialized:
            import requests as tg_requests
            tg_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            tg_chat = os.environ.get('TELEGRAM_CHAT_ID')
            
            if tg_token and tg_chat:
                tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                tg_payload = {
                    'chat_id': tg_chat,
                    'text': '🟢 *ZERO HOUR AUDIT*\n\n_Heartbeat confirmed. System operational._\n\n⚡ Protocol Pulse Intelligence',
                    'parse_mode': 'Markdown'
                }
                tg_response = tg_requests.post(tg_url, json=tg_payload, timeout=10)
                
                if tg_response.status_code == 200:
                    results['telegram'] = {'status': 'ONLINE', 'message': 'Heartbeat dispatched successfully'}
                else:
                    results['telegram'] = {'status': 'DEGRADED', 'message': f'API returned {tg_response.status_code}'}
            else:
                results['telegram'] = {'status': 'OFFLINE', 'message': 'Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID'}
        else:
            results['telegram'] = {'status': 'OFFLINE', 'message': 'Bot not initialized - check TELEGRAM_BOT_TOKEN'}
    except Exception as e:
        results['telegram'] = {'status': 'OFFLINE', 'message': str(e)}
    
    all_online = all(r['status'] == 'ONLINE' for r in [results['telegram'], results['ghl'], results['database']])
    results['overall'] = 'EMPIRE READY' if all_online else 'DEGRADED'
    
    return jsonify(results)


@app.route('/admin/api/ghl-webhook-test', methods=['POST'])
@admin_required
def ghl_webhook_test():
    """Send test webhook payload to GHL with operative data"""
    try:
        result = ghl_service.send_webhook_test(
            first_name="Test Operative",
            signal_points=750,
            sovereign_segment="Sovereign Node"
        )
        return jsonify(result)
    except Exception as e:
        logging.error(f"GHL webhook test error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/ghl-verify', methods=['GET'])
@admin_required
def ghl_verify():
    """Verify GHL API connection returns 200 OK"""
    try:
        result = ghl_service.verify_api_connection()
        return jsonify(result)
    except Exception as e:
        logging.error(f"GHL verification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/sarah-welcome', methods=['POST'])
@admin_required
def trigger_sarah_welcome():
    """Trigger Sarah Welcome emails to recent Scorecard completers"""
    try:
        result = ghl_service.send_sarah_welcome_to_recent_scorecard_users()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Sarah Welcome error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/sms-test-pulse', methods=['POST'])
@admin_required
def sms_test_pulse():
    """Send a test SMS pulse from the Command Deck"""
    try:
        from services.sms_service import sms_service
        
        data = request.get_json() or {}
        phone_number = data.get('phone_number')
        contact_id = data.get('contact_id')
        
        if not phone_number and not contact_id:
            return jsonify({'success': False, 'error': 'Phone number or contact ID required'}), 400
        
        result = sms_service.send_test_pulse(phone_number=phone_number, contact_id=contact_id)
        return jsonify(result)
    except Exception as e:
        logging.error(f"SMS test pulse error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/whale-sms-dispatch', methods=['POST'])
@admin_required
def whale_sms_dispatch():
    """Dispatch SMS alert for mega-whale transaction"""
    try:
        from services.sms_service import sms_service
        
        data = request.get_json() or {}
        btc_amount = data.get('btc_amount', 1000)
        source = data.get('source', 'cold storage')
        destination = data.get('destination', 'Exchange')
        alex_analysis = data.get('alex_analysis', 'High sell pressure detected')
        
        result = sms_service.mega_whale_alert(btc_amount, source, destination, alex_analysis)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Whale SMS dispatch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== SOVEREIGN LOGISTICS HUB =====

@app.route('/logistics')
def logistics():
    """Infrastructure Index - Transparency disclosure for commercial relationships"""
    try:
        with open('data/referrals.json') as f:
            manifest = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load referrals manifest: {e}")
        manifest = {"exchanges": {}, "onramps": {}, "insurance": {}, "hardware": {}}
    
    return render_template('logistics.html', manifest=manifest, now=datetime.utcnow())


@app.route('/go/<string:partner_key>')
def affiliate_redirect(partner_key):
    """Clean redirect for affiliate partners with click tracking"""
    try:
        with open('data/referrals.json') as f:
            data = json.load(f)
        
        partner = None
        for category in data.values():
            if partner_key in category:
                partner = category[partner_key]
                break
        
        if not partner or partner.get("url") == "#":
            flash("This partner link is not yet configured.")
            return redirect(url_for('logistics'))
        
        # Log click for analytics
        db_partner = models.AffiliatePartner.query.filter_by(slug=partner_key).first()
        if db_partner:
            click = models.AffiliateClick(
                partner_id=db_partner.id,
                source_page=request.referrer,
                ip_hash=hashlib.sha256(request.remote_addr.encode()).hexdigest() if request.remote_addr else None,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(click)
            db.session.commit()
        
        return redirect(partner["url"], code=302)
    except Exception as e:
        logging.error(f"Affiliate redirect error: {e}")
        return redirect(url_for('logistics'))


# =============================================
# MEDIA INTELLIGENCE TERMINAL API ROUTES
# =============================================

# Tag -> subreddits for trending links (public, no auth)
TRENDING_TAG_SUBREDDITS = {
    'bitcoin': ['bitcoin', 'bitcoindiscussion', 'cryptocurrency'],
    'etf': ['bitcoin', 'cryptocurrency', 'ethereum'],
    'lightning': ['lightningnetwork', 'bitcoin'],
    'nostr': ['bitcoin', 'nostr', 'cryptocurrency'],
    'mining': ['bitcoin', 'bitcoinmining', 'cryptocurrency'],
    'halving': ['bitcoin', 'cryptocurrency'],
}


@app.route('/api/media/trending-links')
def api_media_trending_links():
    """Public API: top 5 links for a trending tag (e.g. ?tag=bitcoin). For hover popovers."""
    tag = (request.args.get('tag') or '').strip().lower().replace('#', '')
    if not tag:
        return jsonify({'links': [], 'expand_url': None})
    subreddits = TRENDING_TAG_SUBREDDITS.get(tag, ['bitcoin', 'cryptocurrency'])
    try:
        trends = reddit_service.get_trending_topics(subreddits, limit=5, time_period='day')
        links = [
            {'title': t.get('title', '')[:80] + ('…' if len(t.get('title', '')) > 80 else ''), 'url': t.get('permalink') or t.get('url', '#')}
            for t in trends[:5]
        ]
        expand_url = f"https://www.reddit.com/search/?q={tag}&type=link" if tag else None
        return jsonify({'links': links, 'expand_url': expand_url})
    except Exception as e:
        logging.warning("Trending links for %s: %s", tag, e)
        return jsonify({'links': [], 'expand_url': f"https://www.reddit.com/r/bitcoin/search/?q={tag}"})


@app.route('/api/media/feed')
def api_media_feed():
    """Get aggregated feed items from all sources, with articles as fallback"""
    tier = request.args.get('tier', 'all')
    verified_only = request.args.get('verified_only', '0') == '1'
    limit = min(int(request.args.get('limit', 50)), 100)
    
    result = []
    
    query = models.FeedItem.query.order_by(models.FeedItem.published_at.desc())
    
    if tier and tier != 'all':
        query = query.filter(models.FeedItem.tier == tier)
    
    if verified_only:
        query = query.filter(models.FeedItem.verified == True)
    
    items = query.limit(limit).all()
    
    for item in items:
        result.append({
            'id': f'feed_{item.id}',
            'source': item.source,
            'source_type': item.source_type,
            'tier': item.tier,
            'title': item.title,
            'url': item.url,
            'published_at': item.published_at.isoformat() if item.published_at else None,
            'author': item.author,
            'summary': item.summary[:200] if item.summary else '',
            'platform_icon': item.platform_icon,
            'verified': item.verified
        })
    
    if len(result) < limit:
        remaining = limit - len(result)
        article_query = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc())
        
        if tier and tier != 'all':
            tier_category_map = {
                'macro': ['markets', 'economics', 'policy', 'macro'],
                'dev': ['development', 'technology', 'bitcoin', 'lightning'],
                'mining': ['mining', 'hashrate', 'energy'],
                'quant': ['analysis', 'data', 'metrics', 'trading']
            }
            categories = tier_category_map.get(tier, [])
            if categories:
                article_query = article_query.filter(models.Article.category.in_(categories))
        
        articles = article_query.limit(remaining).all()
        
        for article in articles:
            category = (article.category or 'news').lower()
            tier_map = {
                'markets': 'macro', 'economics': 'macro', 'policy': 'macro', 'macro': 'macro',
                'development': 'dev', 'technology': 'dev', 'bitcoin': 'dev', 'lightning': 'dev',
                'mining': 'mining', 'hashrate': 'mining', 'energy': 'mining',
                'analysis': 'quant', 'data': 'quant', 'metrics': 'quant', 'trading': 'quant'
            }
            article_tier = tier_map.get(category, 'media')
            
            result.append({
                'id': f'article_{article.id}',
                'source': 'Protocol Pulse',
                'source_type': 'rss',
                'tier': article_tier,
                'title': article.title,
                'url': f'/article/{article.id}',
                'published_at': article.created_at.isoformat() if article.created_at else None,
                'author': article.author or 'Protocol Pulse',
                'summary': article.summary[:200] if article.summary else '',
                'platform_icon': 'fas fa-newspaper',
                'verified': True
            })
    
    return jsonify(result)


@app.route('/api/media/sentiment')
def api_media_sentiment():
    """Get latest sentiment snapshot with holographic dial data"""
    snapshot = models.SentimentSnapshot.query.order_by(
        models.SentimentSnapshot.created_at.desc()
    ).first()
    
    if snapshot:
        keywords = []
        if snapshot.top_keywords:
            try:
                keywords = json.loads(snapshot.top_keywords)
            except:
                pass
        
        result = {
            'score': snapshot.score or 50,
            'state': {
                'key': snapshot.state or 'EQUILIBRIUM',
                'label': snapshot.state_label or 'EQUILIBRIUM',
                'color': snapshot.state_color or '#ffffff'
            },
            'keywords': keywords[:3] if keywords else [],
            'sample_size': snapshot.sample_size or 0,
            'verified_count': snapshot.verified_weight or 0,
            'computed_at': snapshot.computed_at.isoformat() if snapshot.computed_at else snapshot.created_at.isoformat()
        }

        # Inject x_spaces data from sentiment.json
        try:
            import os as _os
            _sp = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                'video_pipeline_v3', 'data', 'intelligence', 'sentiment.json')
            if _os.path.exists(_sp):
                with open(_sp) as _f:
                    _sd = json.load(_f)
                _xs = _sd.get('data', {}).get('breakdown', {}).get('x_spaces', {})
                if _xs:
                    result['x_spaces'] = {
                        'score': _xs.get('score', 50),
                        'label': _xs.get('label', 'NEUTRAL'),
                        'active_count': _xs.get('active_count', 0),
                        'top_host': _xs.get('top_host'),
                    }
        except Exception:
            pass

        return jsonify(result)
    
    return jsonify({
        'score': 50,
        'state': {
            'key': 'EQUILIBRIUM',
            'label': 'EQUILIBRIUM',
            'color': '#ffffff'
        },
        'keywords': [],
        'sample_size': 0,
        'verified_count': 0,
        'computed_at': datetime.utcnow().isoformat()
    })




@app.route('/api/tradfi/signals')
def api_tradfi_signals():
    """TradFi intelligence feed — Bitcoin-relevant signals from traditional finance voices."""
    try:
        import os as _os, json as _json
        path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                             'video_pipeline_v3','data','intelligence','tradfi_signals.json')
        if _os.path.exists(path):
            with open(path) as f:
                data = _json.load(f)
            signals = sorted(data.get('signals', []),
                             key=lambda s: s.get('likes',0)+s.get('retweets',0)*3,
                             reverse=True)[:20]
            return jsonify({
                'signals': signals,
                'count': len(signals),
                'weekly_segment_ready': data.get('weekly_segment_ready', False),
                'last_updated': data.get('last_updated',''),
            })
    except Exception as e:
        logging.warning(f'api_tradfi_signals: {e}')
    return jsonify({'signals':[],'count':0,'weekly_segment_ready':False,'last_updated':''})


@app.route('/api/tradfi/weekly')
def api_tradfi_weekly():
    """Weekly TradFi segment brief — macro tone through a Bitcoin lens."""
    try:
        import os as _os, json as _json
        path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                             'video_pipeline_v3','data','intelligence','tradfi_weekly.json')
        if _os.path.exists(path):
            with open(path) as f:
                return jsonify(_json.load(f))
    except Exception as e:
        logging.warning(f'api_tradfi_weekly: {e}')
    return jsonify({'segment_ready':False,'macro_tone':'UNKNOWN','signals':[]})


@app.route('/api/spaces/live')
def api_spaces_live():
    """Get live X Spaces sentiment data."""
    try:
        import os as _os
        sentiment_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                       'video_pipeline_v3', 'data', 'intelligence', 'sentiment.json')
        xs_data = None
        if _os.path.exists(sentiment_path):
            with open(sentiment_path) as _f:
                sdata = json.load(_f)
            xs_data = sdata.get('data', {}).get('breakdown', {}).get('x_spaces')

        if not xs_data:
            from services.spaces_sentiment_service import spaces_sentiment_service
            xs_data = spaces_sentiment_service.run()

        return jsonify({
            'score': xs_data.get('score', 50),
            'label': xs_data.get('label', 'NEUTRAL'),
            'active_count': xs_data.get('active_count', 0),
            'top_host': xs_data.get('top_host'),
            'top_quote': xs_data.get('top_quote', ''),
            'topics': xs_data.get('topics', []),
            'confidence': xs_data.get('confidence', 'LOW'),
            'driver': xs_data.get('driver', 'x_spaces live intel'),
            'scan_time': xs_data.get('computed_at', datetime.utcnow().isoformat()),
            'source': 'x_spaces',
        })
    except Exception as e:
        return jsonify({
            'score': 50, 'label': 'NEUTRAL', 'active_count': 0,
            'top_host': None, 'top_quote': '', 'topics': [],
            'confidence': 'LOW', 'driver': 'error', 'scan_time': datetime.utcnow().isoformat(),
            'source': 'x_spaces', 'error': str(e),
        })


@app.route('/api/podcasts/channels')
def api_podcasts_channels():
    """Get YouTube channel cards with stats"""
    try:
        from services.youtube_channel_service import get_all_channel_cards
        cards = get_all_channel_cards()
        return jsonify(cards)
    except Exception as e:
        logging.error(f"Channel cards error: {e}")
        return jsonify([])


@app.route('/api/media/sources')
def api_media_sources():
    """Get curated sources from supported_sources.json"""
    try:
        with open('data/supported_sources.json', 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        logging.error(f"Failed to load sources: {e}")
        return jsonify({})


@app.route('/admin/autopost')
@login_required
@admin_required
def admin_autopost():
    """Admin UI for autopost drafts and daily briefs"""
    drafts = models.AutoPostDraft.query.order_by(models.AutoPostDraft.created_at.desc()).limit(50).all()
    daily_briefs = models.DailyBrief.query.order_by(models.DailyBrief.created_at.desc()).limit(10).all()
    return render_template('admin/autopost.html', drafts=drafts, daily_briefs=daily_briefs)


@app.route('/admin/api/autopost/<int:draft_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_autopost(draft_id):
    """Approve an autopost draft"""
    draft = models.AutoPostDraft.query.get_or_404(draft_id)
    
    autopost_enabled = os.environ.get('AUTOPOST_X', 'false').lower() == 'true'
    
    if autopost_enabled:
        draft.status = 'posted'
        draft.posted_at = datetime.utcnow()
    else:
        draft.status = 'approved'
        draft.approved_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'status': draft.status})


@app.route('/admin/api/autopost/<int:draft_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_autopost(draft_id):
    """Reject an autopost draft"""
    draft = models.AutoPostDraft.query.get_or_404(draft_id)
    draft.status = 'rejected'
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/admin/api/generate-daily-brief', methods=['POST'])
@login_required
@admin_required
def generate_daily_brief_api():
    """Generate a new daily brief from Sarah"""
    try:
        from services.sarah_analyst import sarah_analyst
        
        feed_items = models.FeedItem.query.order_by(models.FeedItem.created_at.desc()).limit(50).all()
        
        top_signals = sarah_analyst.analyze_signals(feed_items, limit=3)
        
        sentiment = models.SentimentSnapshot.query.order_by(models.SentimentSnapshot.created_at.desc()).first()
        sentiment_data = None
        if sentiment:
            sentiment_data = {'state': sentiment.state, 'score': sentiment.score}
        
        brief_data = sarah_analyst.generate_daily_brief(top_signals, sentiment_data)
        
        signals_json = json.dumps([{
            'title': s['item'].title,
            'source': s['item'].source,
            'score': s['score'],
            'sovereignty_impact': s['sovereignty_impact'],
            'reasons': s['reasons']
        } for s in top_signals])
        
        brief = models.DailyBrief(
            headline=brief_data['headline'],
            body=brief_data['body'],
            signals_json=signals_json,
            status='draft'
        )
        db.session.add(brief)
        db.session.commit()
        
        return jsonify({'success': True, 'brief_id': brief.id})
    except Exception as e:
        logging.error(f"Daily brief generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/daily-brief/<int:brief_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_daily_brief(brief_id):
    """Publish a daily brief"""
    brief = models.DailyBrief.query.get_or_404(brief_id)
    
    if brief.status == 'published':
        return jsonify({'success': False, 'error': 'Brief already published'}), 400
    
    if brief.status != 'draft':
        return jsonify({'success': False, 'error': 'Only draft briefs can be published'}), 400
    
    brief.status = 'published'
    brief.published_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/api/daily-brief/<int:brief_id>/create-tweet', methods=['POST'])
@login_required
@admin_required
def create_tweet_from_brief(brief_id):
    """Create a tweet draft from a daily brief"""
    try:
        from services.sarah_analyst import sarah_analyst
        
        brief = models.DailyBrief.query.get_or_404(brief_id)
        
        signals = json.loads(brief.signals_json) if brief.signals_json else []
        mock_signals = [{'item': type('obj', (object,), {'title': s.get('title', 'Signal'), 'source': s.get('source', 'Unknown')})(), 'sovereignty_impact': s.get('sovereignty_impact', 5)} for s in signals]
        
        tweet_body = sarah_analyst.generate_tweet_draft({'signals': mock_signals})
        tweet_body = tweet_body.replace('{link}', f'/briefs/{brief.id}')
        
        draft = models.AutoPostDraft(
            platform='x',
            body=tweet_body,
            reason=f'Daily Brief #{brief.id}',
            status='draft'
        )
        db.session.add(draft)
        db.session.commit()
        
        return jsonify({'success': True, 'draft_id': draft.id})
    except Exception as e:
        logging.error(f"Tweet creation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/media/ingest', methods=['POST'])
@login_required
@admin_required
def trigger_feed_ingest():
    """Manually trigger feed ingestion"""
    try:
        from services.feed_ingest import run_full_ingestion
        count = run_full_ingestion()
        return jsonify({'success': True, 'items_ingested': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# PHASE 7: NEW PAGES & OPERATIVE FEATURES
# ============================================

@app.route('/bitcoin-music')
def bitcoin_music():
    """Bitcoin Music showcase page"""
    return render_template('bitcoin_music.html')

@app.route('/bitcoin-artists')
def bitcoin_artists():
    """Bitcoin Artists & Creators page"""
    return render_template('bitcoin_artists.html')

@app.route('/freedom-tech')
def freedom_tech():
    """Freedom Tech destination page"""
    return render_template('freedom_tech.html')

@app.route('/operative/<slug>')
def operative_profile(slug):
    """Public operative profile page"""
    user = models.User.query.filter_by(operative_slug=slug).first_or_404()
    return render_template('operative_profile.html', operative=user)

@app.route('/api/rank/get-drill-token', methods=['POST'])
@login_required
def get_drill_token():
    """Generate a one-time token for drill completion verification"""
    import secrets
    token = secrets.token_urlsafe(32)
    session['drill_token'] = token
    session['drill_token_time'] = datetime.utcnow().isoformat()
    return jsonify({'token': token})

@app.route('/api/rank/increment-drill', methods=['POST'])
@login_required
def increment_drill_completion():
    """Increment drill completion count with cooldown and token protection"""
    try:
        data = request.get_json() or {}
        submitted_token = data.get('token')
        
        if not submitted_token or submitted_token != session.get('drill_token'):
            return jsonify({
                'success': False,
                'error': 'Invalid verification token. Please complete the drill from the official page.',
                'invalid_token': True
            }), 403
        
        session.pop('drill_token', None)
        
        if not current_user.can_increment_drill():
            return jsonify({
                'success': False,
                'error': 'Cooldown active. Complete another drill in 5 minutes.',
                'cooldown': True
            }), 429
        
        current_user.drill_completions += 1
        current_user.last_drill_at = datetime.utcnow()
        current_user.check_rank_progression()
        
        if not current_user.operative_slug:
            current_user.generate_operative_slug()
        
        db.session.commit()
        
        try:
            from services.crm_sync import crm_sync
            crm_sync.sync_user_to_highpoint(current_user)
        except Exception as crm_e:
            logging.warning(f"CRM sync failed (non-critical): {crm_e}")
        
        return jsonify({
            'success': True,
            'drill_completions': current_user.drill_completions,
            'rank': current_user.operative_rank,
            'rank_name': current_user.get_rank_name(),
            'profile_url': f'/operative/{current_user.operative_slug}' if current_user.operative_slug else None
        })
    except Exception as e:
        logging.error(f"Drill increment failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rank/get-brief-token', methods=['POST'])
@login_required
def get_brief_token():
    """Generate a one-time token for brief click verification"""
    import secrets
    token = secrets.token_urlsafe(32)
    session['brief_token'] = token
    return jsonify({'token': token})

@app.route('/api/rank/increment-brief', methods=['POST'])
@login_required
def increment_brief_click():
    """Increment brief click count with cooldown and token protection"""
    try:
        data = request.get_json() or {}
        submitted_token = data.get('token')
        
        if not submitted_token or submitted_token != session.get('brief_token'):
            return jsonify({
                'success': False,
                'error': 'Invalid verification token.',
                'invalid_token': True
            }), 403
        
        session.pop('brief_token', None)
        
        if not current_user.can_increment_brief():
            return jsonify({
                'success': False,
                'error': 'Cooldown active. Read another brief in 1 minute.',
                'cooldown': True
            }), 429
        
        current_user.brief_clicks += 1
        current_user.last_brief_at = datetime.utcnow()
        current_user.check_rank_progression()
        
        if not current_user.operative_slug:
            current_user.generate_operative_slug()
        
        db.session.commit()
        
        try:
            from services.crm_sync import crm_sync
            crm_sync.sync_user_to_highpoint(current_user)
        except Exception as crm_e:
            logging.warning(f"CRM sync failed (non-critical): {crm_e}")
        
        return jsonify({
            'success': True,
            'brief_clicks': current_user.brief_clicks,
            'rank': current_user.operative_rank,
            'rank_name': current_user.get_rank_name()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# HighPoint CRM Setup Wizard
@app.route('/admin/crm-setup')
@login_required
@admin_required
def crm_setup_wizard():
    """CRM Setup Wizard with step-by-step configuration"""
    current_api_key = os.environ.get('GHL_API_KEY', '')
    current_location_id = os.environ.get('GHL_LOCATION_ID', '')
    masked_key = f"{current_api_key[:8]}...{current_api_key[-4:]}" if current_api_key and len(current_api_key) > 12 else ''
    
    return render_template('admin/crm_setup.html',
                         current_api_key=masked_key,
                         current_location_id=current_location_id)

@app.route('/admin/api/crm-setup/save-keys', methods=['POST'])
@login_required
@admin_required
def save_crm_keys():
    """Save CRM API keys - Note: User must manually add to Secrets tab"""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '')
        location_id = data.get('location_id', '')
        
        if not api_key or not location_id:
            return jsonify({'success': False, 'error': 'Both API Key and Location ID are required'})
        
        return jsonify({
            'success': True,
            'message': 'Configuration validated. Add GHL_API_KEY and GHL_LOCATION_ID to your Secrets tab.',
            'instructions': 'Go to Tools → Secrets and add: GHL_API_KEY and GHL_LOCATION_ID'
        })
    except Exception as e:
        logging.error(f"CRM key save error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/api/crm-setup/test')
@login_required
@admin_required
def test_crm_connection():
    """Test CRM connection to HighLevel"""
    try:
        api_key = os.environ.get('GHL_API_KEY')
        location_id = os.environ.get('GHL_LOCATION_ID')
        
        if not api_key or not location_id:
            return jsonify({
                'success': False,
                'error': 'API Key or Location ID not configured in Secrets'
            })
        
        import requests
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }
        
        response = requests.get(
            f'https://services.leadconnectorhq.com/locations/{location_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Connection verified'})
        else:
            return jsonify({
                'success': False,
                'error': f'HighLevel returned status {response.status_code}: {response.text[:100]}'
            })
            
    except Exception as e:
        logging.error(f"CRM test error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/api/crm-setup/send-test-payload', methods=['POST'])
@login_required
@admin_required
def send_test_crm_payload():
    """Send a test Recruit payload to HighLevel"""
    try:
        api_key = os.environ.get('GHL_API_KEY')
        location_id = os.environ.get('GHL_LOCATION_ID')
        
        if not api_key or not location_id:
            return jsonify({
                'success': False,
                'error': 'API Key or Location ID not configured'
            })
        
        import requests
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }
        
        test_payload = {
            'firstName': 'Protocol',
            'lastName': 'Test',
            'email': f'test-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}@protocolpulse.test',
            'tags': ['PP_Recruit', 'PP_Test'],
            'source': 'Protocol Pulse CRM Test',
            'locationId': location_id
        }
        
        response = requests.post(
            'https://services.leadconnectorhq.com/contacts/',
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Test contact created in HighLevel'})
        else:
            return jsonify({
                'success': False,
                'error': f'HighLevel returned {response.status_code}: {response.text[:200]}'
            })
            
    except Exception as e:
        logging.error(f"CRM test payload error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/crm/callback', methods=['POST'])
def crm_webhook_callback():
    """Webhook listener for HighLevel CRM callbacks
    
    Allows HighLevel to send events back to Protocol Pulse
    (e.g., when a user books a Sovereign Alignment Call, upgrade to Alpha-Elite)
    """
    try:
        data = request.get_json() or {}
        event_type = data.get('type', data.get('event', 'unknown'))
        contact_email = data.get('email', data.get('contact', {}).get('email'))
        
        logging.info(f"CRM Callback received: {event_type} for {contact_email}")
        
        if event_type in ['appointment_booked', 'call_scheduled', 'sovereign_call']:
            if contact_email:
                user = models.User.query.filter_by(email=contact_email).first()
                if user:
                    user.operative_rank = 3
                    user.check_rank_progression()
                    db.session.commit()
                    logging.info(f"Upgraded user {contact_email} to Sovereign Elite via CRM callback")
                    return jsonify({'success': True, 'action': 'rank_upgraded', 'new_rank': 3})
        
        if event_type in ['tag_added']:
            tag_name = data.get('tag', data.get('tagName', ''))
            if 'Alpha' in tag_name or 'Elite' in tag_name:
                if contact_email:
                    user = models.User.query.filter_by(email=contact_email).first()
                    if user:
                        user.operative_rank = 3
                        db.session.commit()
                        return jsonify({'success': True, 'action': 'rank_upgraded'})
        
        return jsonify({'success': True, 'message': 'Callback received'})
        
    except Exception as e:
        logging.error(f"CRM callback error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Real-Time Intelligence Dashboard & Tracking
@app.route('/admin/analytics')
@login_required
@admin_required
def realtime_analytics_dashboard():
    """Real-time analytics dashboard with hot pages, suggestions, and tweet drafts"""
    try:
        from services.realtime_intel import realtime_intel
        
        stats = realtime_intel.get_realtime_stats()
        hot_pages = realtime_intel.get_hot_pages(limit=10)
        suggestions = realtime_intel.get_pending_suggestions(limit=5)
        pending_tweets = realtime_intel.get_pending_tweets(limit=5)
        
        return render_template('admin/realtime_dashboard.html',
                             stats=stats,
                             hot_pages=hot_pages,
                             suggestions=suggestions,
                             pending_tweets=pending_tweets)
    except Exception as e:
        logging.error(f"Analytics dashboard error: {e}")
        return render_template('admin/realtime_dashboard.html',
                             stats={},
                             hot_pages=[],
                             suggestions=[],
                             pending_tweets=[])

@app.route('/admin/api/realtime-stats')
@login_required
@admin_required
def api_realtime_stats():
    """API endpoint for real-time stats refresh"""
    try:
        from services.realtime_intel import realtime_intel
        return jsonify(realtime_intel.get_realtime_stats())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/approve-tweet/<int:tweet_id>', methods=['POST'])
@login_required
@admin_required
def api_approve_tweet(tweet_id):
    """Approve a peak tweet for posting"""
    try:
        from services.realtime_intel import realtime_intel
        success = realtime_intel.approve_tweet(tweet_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/dismiss-tweet/<int:tweet_id>', methods=['POST'])
@login_required
@admin_required
def api_dismiss_tweet(tweet_id):
    """Dismiss a peak tweet draft"""
    try:
        tweet = models.AutoTweet.query.get(tweet_id)
        if tweet:
            tweet.status = 'dismissed'
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Tweet not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/generate-suggestions', methods=['POST'])
@login_required
@admin_required
def api_generate_suggestions():
    """Manually trigger content suggestion generation"""
    try:
        from services.realtime_intel import realtime_intel
        suggestions = realtime_intel.generate_content_suggestions()
        return jsonify({
            'success': True,
            'count': len(suggestions),
            'suggestions': [s.title for s in suggestions if s]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _seed_affiliate_products_if_empty():
    """Seed default affiliate products for cold wallets, seed plates, miners (only if none exist)."""
    if models.AffiliateProduct.query.first():
        return
    from services.monetization_service import monetization_service
    defaults = [
        {'name': 'Trezor Model T', 'product_type': 'trezor', 'product_id': 'trezor-model-t', 'category': 'cold_wallet', 'short_description': 'Hardware wallet with touchscreen and passphrase support.'},
        {'name': 'Trezor Safe 3', 'product_type': 'trezor', 'product_id': 'trezor-safe-3', 'category': 'cold_wallet', 'short_description': 'Secure hardware wallet for Bitcoin self-custody.'},
        {'name': 'Ledger Nano X', 'product_type': 'amazon', 'product_id': 'B07S5JQ7M2', 'category': 'cold_wallet', 'short_description': 'Bluetooth hardware wallet (Amazon).'},
        {'name': 'Cryptosteel Capsule', 'product_type': 'amazon', 'product_id': 'B09V2R9Q7K', 'category': 'seed_plate', 'short_description': 'Fire- and shock-resistant seed phrase backup.'},
        {'name': 'Bitaxe Miner', 'product_type': 'amazon', 'product_id': 'B0B1XYZ', 'category': 'miner', 'short_description': 'DIY Bitcoin mining (use real ASIN when you have one).'},
    ]
    for d in defaults:
        url = monetization_service.generate_affiliate_link(d['product_type'], d['product_id'])
        p = models.AffiliateProduct(
            name=d['name'],
            product_type=d['product_type'],
            product_id=d['product_id'],
            category=d['category'],
            short_description=d['short_description'],
            affiliate_url=url or '',
            active=True,
        )
        db.session.add(p)
    db.session.commit()
    logging.info("Seeded affiliate products.")


@app.route('/admin/smart-analytics')
@login_required
@admin_required
def admin_smart_analytics():
    """Smart analytics dashboard: all metrics, user preferences, affiliate performance, revenue."""
    try:
        _seed_affiliate_products_if_empty()
        from services.smart_analytics_service import smart_analytics_service
        from services.monetization_service import monetization_service
        days = request.args.get('days', 7, type=int)
        if days not in (1, 7, 14, 30):
            days = 7
        data = smart_analytics_service.get_smart_dashboard_data(days=days)
        revenue = monetization_service.get_revenue_stats()
        return render_template('admin/smart_analytics.html',
                             data=data,
                             revenue=revenue,
                             days=days)
    except Exception as e:
        logging.error(f"Smart analytics error: {e}")
        return render_template('admin/smart_analytics.html',
                             data={},
                             revenue={},
                             days=7)


@app.route('/admin/generate-affiliate-article', methods=['POST'])
@login_required
@admin_required
def admin_generate_affiliate_article():
    """Generate one product-highlight article (draft) with affiliate link."""
    from services.monetization_service import monetization_service
    from services.content_engine import ContentEngine
    import random
    products = models.AffiliateProduct.query.filter_by(active=True).all()
    product = random.choice(products) if products else None
    if not product:
        return jsonify({'success': False, 'error': 'No affiliate products. Add products in admin.'}), 400
    affiliate_url = product.affiliate_url or monetization_service.generate_affiliate_link(product.product_type, product.product_id or '')
    topic = (
        f"Product highlight: {product.name}. "
        f"For transactors who want the best in our niche. "
        f"Write a practical, helpful article (not salesy). "
        f"Include this referral link as the primary CTA for readers: {affiliate_url}. "
        f"Product category: {product.category}. "
        f"Short description: {product.short_description or ''}. "
        f"Keep tone Protocol Pulse: intelligence for transactors."
    )
    try:
        engine = ContentEngine()
        result = engine.generate_and_publish_article(
            topic, content_type="bitcoin_news", auto_publish=False
        )
        if result.get('success') and result.get('article_id'):
            article = models.Article.query.get(result['article_id'])
            if article and affiliate_url:
                article.content = (article.content or '') + f"\n\n---\n[Get {product.name}]({affiliate_url})"
                db.session.commit()
            return jsonify({
                'success': True,
                'article_id': result['article_id'],
                'title': result.get('title'),
                'product': product.name,
            })
    except Exception as e:
        logging.error(f"Affiliate article generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Generation failed'}), 500


@app.route('/api/track/pageview', methods=['POST'])
def api_track_pageview():
    """Track a page view for analytics (public endpoint). Accepts path, title, time_on_page, scroll_depth."""
    try:
        from services.realtime_intel import realtime_intel
        from flask_login import current_user

        data = request.get_json() or {}
        page_path = data.get('path', request.referrer or '/')
        page_title = data.get('title', '')
        time_on_page = data.get('time_on_page')
        scroll_depth = data.get('scroll_depth')

        session_id = session.get('session_id')
        if not session_id:
            import secrets
            session_id = secrets.token_urlsafe(16)
            session['session_id'] = session_id

        user_id = current_user.id if current_user.is_authenticated else None

        realtime_intel.track_page_view(
            page_path=page_path,
            page_title=page_title,
            session_id=session_id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
            referrer=request.referrer,
            user_id=user_id,
            time_on_page=time_on_page,
            scroll_depth=scroll_depth,
        )
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Page view tracking error: {e}")
        return jsonify({'success': False}), 500


@app.route('/api/track/event', methods=['POST'])
def api_track_event():
    """Track engagement events: time_on_page, scroll_depth, affiliate_click."""
    try:
        from services.realtime_intel import realtime_intel
        from flask_login import current_user

        data = request.get_json() or {}
        event_type = data.get('event_type')
        session_id = session.get('session_id')
        user_id = current_user.id if current_user.is_authenticated else None

        if event_type == 'engagement':
            page_path = data.get('page_path', '')
            time_on_page = data.get('time_on_page', 0)
            scroll_depth = data.get('scroll_depth', 0)
            if session_id and page_path:
                realtime_intel.update_page_view_engagement(
                    session_id=session_id,
                    page_path=page_path,
                    time_on_page=int(time_on_page) if time_on_page is not None else None,
                    scroll_depth=int(scroll_depth) if scroll_depth is not None else None,
                )
        elif event_type == 'affiliate_click':
            product_id = data.get('product_id', type=int)
            link_type = data.get('link_type', '')
            page_path = data.get('page_path', '')
            click = models.AffiliateProductClick(
                product_id=product_id,
                link_type=link_type or None,
                page_path=page_path[:500] if page_path else None,
                session_id=session_id,
                user_id=user_id,
            )
            db.session.add(click)
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Track event error: {e}")
        return jsonify({'success': False}), 500

@app.route('/api/hot-ticker')
def api_hot_ticker():
    """Get hot pages for front-page ticker display"""
    try:
        from services.realtime_intel import realtime_intel
        hot_pages = realtime_intel.get_hot_pages(limit=5)
        return jsonify({
            'success': True,
            'hot_pages': hot_pages,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'hot_pages': []}), 500


# ============================================
# RTSA (Real-Time Sovereign Apparel) Routes
# ============================================

@app.route('/admin/rtsa')
@login_required
@admin_required
def admin_rtsa():
    """Admin dashboard for RTSA product management"""
    from services.rtsa_service import rtsa_service
    
    draft_products = rtsa_service.get_draft_products()
    approved_products = rtsa_service.get_approved_products(limit=20)
    hot_products = rtsa_service.get_hot_products()
    
    return render_template('admin/rtsa.html',
                         draft_products=draft_products,
                         approved_products=approved_products,
                         hot_products=hot_products)


@app.route('/admin/api/rtsa/forge', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_forge():
    """Manually trigger RTSA forge from current sentiment"""
    from services.rtsa_service import rtsa_service
    from services.sentiment_engine import get_latest_sentiment
    
    try:
        sentiment = get_latest_sentiment()
        sentiment['state_changed'] = True
        
        product = rtsa_service.forge_from_sentiment(sentiment)
        
        if product:
            return jsonify({
                'success': True,
                'product': product.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Forge failed'}), 500
            
    except Exception as e:
        logging.error(f"RTSA manual forge error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/rtsa/approve/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_approve(product_id):
    """Approve an RTSA draft product"""
    from services.rtsa_service import rtsa_service
    
    result = rtsa_service.approve_product(product_id, current_user.id)
    
    if result and result.get('success'):
        return jsonify(result)
    else:
        return jsonify({'success': False, 'error': result.get('error', 'Approval failed')}), 400


@app.route('/admin/api/rtsa/reject/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_reject(product_id):
    """Reject an RTSA draft product"""
    from services.rtsa_service import rtsa_service
    
    success = rtsa_service.reject_product(product_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Rejection failed'}), 400


@app.route('/admin/api/rtsa/broadcast/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_broadcast(product_id):
    """Broadcast an approved RTSA product to social"""
    from services.rtsa_service import rtsa_service
    
    product = models.RealTimeProduct.query.get(product_id)
    if not product or product.status != 'approved':
        return jsonify({'success': False, 'error': 'Product not found or not approved'}), 404
    
    success = rtsa_service.broadcast_new_product(product)
    
    return jsonify({'success': success})


@app.route('/api/rtsa/products')
def api_rtsa_products():
    """Get approved RTSA products for public display"""
    from services.rtsa_service import rtsa_service
    
    hot_products = rtsa_service.get_hot_products()
    approved_products = rtsa_service.get_approved_products(limit=10)
    
    return jsonify({
        'hot': [p.to_dict() for p in hot_products],
        'approved': [p.to_dict() for p in approved_products]
    })


@app.route('/api/rtsa/foundational')
def api_rtsa_foundational():
    """Get the 5 foundational ethos statements"""
    from services.design_forge import get_foundational_statements
    
    return jsonify({
        'statements': get_foundational_statements()
    })


# ============================================================
# PULSE TERMINAL COMMANDER API — v1
# JWT-authenticated, rate-limited REST API for $49/mo tier
# ============================================================

import jwt as _jwt
from functools import wraps as _wraps

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "pulse-terminal-dev-secret-change-in-prod")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24


def _jwt_required(f):
    """Decorator: validates Bearer JWT; injects _jwt_user_id, _jwt_tier into kwargs."""
    @_wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header[7:]
        try:
            payload = _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        except _jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except _jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        tier = payload.get("tier", "free")
        if tier not in ("commander", "sovereign"):
            return jsonify({"error": "Commander tier required"}), 403

        kwargs["_jwt_user_id"] = payload.get("user_id")
        kwargs["_jwt_tier"] = tier
        return f(*args, **kwargs)
    return decorated


def _apply_rate_limit(user_id, tier):
    """Check rate limit; returns (allowed, meta_dict)."""
    from services.pulse_terminal_service import check_and_increment_rate_limit
    result = check_and_increment_rate_limit(user_id, tier)
    meta = {
        "tier": tier,
        "rate_limit_remaining": result["remaining"],
        "rate_limit_daily": result["limit"],
        "freshness": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return result["allowed"], meta


# ── /v1/auth/token ────────────────────────────────────────────────────────────

@app.route("/v1/auth/token", methods=["POST"])
def v1_auth_token():
    """
    Issue a JWT for Commander API access.
    POST body: {"email": "...", "password": "..."}
    Returns: {"token": "...", "tier": "...", "expires_in": 86400}
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    user = models.User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    tier = getattr(user, "subscription_tier", "free")
    if tier not in ("operator", "commander", "sovereign"):
        return jsonify({"error": "Commander or higher tier required for API access"}), 403

    expiry = datetime.utcnow() + timedelta(hours=_JWT_EXPIRY_HOURS)
    payload = {
        "user_id": user.id,
        "email": user.email,
        "tier": tier,
        "exp": expiry,
        "iat": datetime.utcnow(),
    }
    token = _jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

    return jsonify({
        "token": token,
        "tier": tier,
        "expires_in": _JWT_EXPIRY_HOURS * 3600,
        "expires_at": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


# ── /v1/signals/live ─────────────────────────────────────────────────────────

@app.route("/v1/signals/live", methods=["GET"])
@_jwt_required
def v1_signals_live(**kwargs):
    """
    Commander: Last 10 BTC-relevant live signals with btc_lens_sentiment.
    Query params: ?limit=10 (max 50)
    """
    user_id = kwargs.get("_jwt_user_id")
    tier = kwargs.get("_jwt_tier")

    allowed, meta = _apply_rate_limit(user_id, tier)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429

    limit = min(int(request.args.get("limit", 10)), 50)

    from services.pulse_terminal_service import get_live_signals
    result = get_live_signals(limit=limit)

    response = {
        "data": result["data"],
        "meta": {**meta, "stale": result.get("stale", False)},
    }
    if result.get("stale"):
        response["warning"] = "Data may be stale — check meta.freshness"

    return jsonify(response)


# ── /v1/spaces/live ───────────────────────────────────────────────────────────

@app.route("/v1/spaces/live", methods=["GET"])
@_jwt_required
def v1_spaces_live(**kwargs):
    """
    Commander: Active X Spaces from live intelligence feed.
    """
    user_id = kwargs.get("_jwt_user_id")
    tier = kwargs.get("_jwt_tier")

    allowed, meta = _apply_rate_limit(user_id, tier)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429

    from services.pulse_terminal_service import get_spaces_live
    result = get_spaces_live()

    return jsonify({
        "data": result["data"],
        "meta": {**meta, "stale": result.get("stale", False)},
    })


# ── /v1/tradfi/signals ───────────────────────────────────────────────────────

@app.route("/v1/tradfi/signals", methods=["GET"])
@_jwt_required
def v1_tradfi_signals(**kwargs):
    """
    Commander: Top 20 TradFi signals filtered for BTC relevance.
    Query params: ?limit=20, ?btc_only=true
    """
    user_id = kwargs.get("_jwt_user_id")
    tier = kwargs.get("_jwt_tier")

    allowed, meta = _apply_rate_limit(user_id, tier)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429

    limit = min(int(request.args.get("limit", 20)), 50)
    btc_only = request.args.get("btc_only", "false").lower() == "true"

    from services.pulse_terminal_service import get_tradfi_signals
    result = get_tradfi_signals(limit=limit)

    signals = result["data"]["signals"]
    if btc_only:
        signals = [s for s in signals if s.get("btc_relevant")]

    return jsonify({
        "data": {
            **result["data"],
            "signals": signals,
            "total_returned": len(signals),
        },
        "meta": {**meta, "stale": result.get("stale", False), "btc_only": btc_only},
    })


# ── /v1/sentiment/composite ──────────────────────────────────────────────────

@app.route("/v1/sentiment/composite", methods=["GET"])
@_jwt_required
def v1_sentiment_composite(**kwargs):
    """
    Commander: Full composite sentiment — YouTube, X Spaces, entity, TradFi breakdown.
    """
    user_id = kwargs.get("_jwt_user_id")
    tier = kwargs.get("_jwt_tier")

    allowed, meta = _apply_rate_limit(user_id, tier)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429

    from services.pulse_terminal_service import get_sentiment_composite
    result = get_sentiment_composite()

    return jsonify({
        "data": result["data"],
        "scan_time": result["scan_time"],
        "meta": {**meta, "stale": result.get("stale", False)},
    })


# ── /v1/alerts/webhook ───────────────────────────────────────────────────────

@app.route("/v1/alerts/webhook", methods=["GET", "POST"])
@_jwt_required
def v1_alerts_webhook(**kwargs):
    """
    Commander: Register (POST) or query (GET) alert webhook configuration.
    GET  — returns current breaking alert status + registered webhook URL
    POST — body: {"webhook_url": "https://...", "threshold_velocity": 80}
           stores alert webhook preference on user record (via session)
    """
    user_id = kwargs.get("_jwt_user_id")
    tier = kwargs.get("_jwt_tier")

    allowed, meta = _apply_rate_limit(user_id, tier)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded", "meta": meta}), 429

    from services.pulse_terminal_service import get_breaking_alerts

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        webhook_url = body.get("webhook_url", "")
        threshold = int(body.get("threshold_velocity", 80))

        # Validate URL scheme (no localhost/internal allowed in production)
        if webhook_url and not webhook_url.startswith(("https://", "http://")):
            return jsonify({"error": "webhook_url must be http/https"}), 400

        # Store in Flask session as lightweight persistence (upgrade to DB when needed)
        session[f"alert_webhook_{user_id}"] = {
            "url": webhook_url,
            "threshold_velocity": threshold,
            "registered_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        return jsonify({
            "registered": True,
            "webhook_url": webhook_url,
            "threshold_velocity": threshold,
            "meta": meta,
        })

    # GET — return current alert status
    alerts = get_breaking_alerts()
    webhook_config = session.get(f"alert_webhook_{user_id}", {})

    return jsonify({
        "data": {
            **alerts["data"],
            "webhook_config": webhook_config or None,
        },
        "meta": meta,
    })


# ── /v1/stripe/webhook ───────────────────────────────────────────────────────

@app.route("/v1/stripe/webhook", methods=["POST"])
def v1_stripe_webhook():
    """
    Stripe webhook for Pulse Terminal subscriptions.
    Handles checkout.session.completed and customer.subscription.deleted.
    """
    from services.stripe_service import (
        validate_webhook_signature,
        handle_checkout_completed,
        handle_subscription_deleted,
    )

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_TERMINAL_WEBHOOK_SECRET", "")

    if webhook_secret:
        event = validate_webhook_signature(payload, sig_header, webhook_secret)
        if event is None:
            return jsonify({"error": "Invalid signature"}), 400
    else:
        # Dev mode: parse without verification
        try:
            event = json.loads(payload)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get("type", "")
    event_data = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        result = handle_checkout_completed(event_data, db, models)
        logging.info("Terminal checkout completed: %s", result)
        return jsonify({"received": True, "result": result})

    elif event_type == "customer.subscription.deleted":
        result = handle_subscription_deleted(event_data, db, models)
        logging.info("Terminal subscription deleted: %s", result)
        return jsonify({"received": True, "result": result})

    # All other events acknowledged
    return jsonify({"received": True, "event_type": event_type})




@app.route('/api/media/highlights')
def api_media_highlights():
    """Return recent published articles as highlight items for the media unified page."""
    try:
        limit = min(int(request.args.get('limit', 15)), 30)
        articles = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(limit).all()
        result = []
        for a in articles:
            excerpt = (a.summary or a.content or '')[:200].strip()
            if not excerpt:
                continue
            result.append({
                'id': a.id,
                'title': a.title,
                'excerpt': excerpt,
                'source': a.author or 'Protocol Pulse',
                'url': '/articles/' + str(a.id),
                'timestamp': a.created_at.isoformat() if a.created_at else None,
                'category': a.category or 'bitcoin',
            })
        return jsonify(result)
    except Exception as e:
        logging.warning('api_media_highlights error: %s', e)
        return jsonify([])

# ─────────────────────────────────────────────────────────────────────────────
# P3 CHARTS — Bitcoin Intelligence Hub
# ─────────────────────────────────────────────────────────────────────────────
import time as _time
import functools as _functools
import re as _re_charts

# Simple TTL cache wrapper (no Redis dependency)
def _ttl_cache(seconds):
    def decorator(fn):
        _cache_store = {}
        @_functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = _time.monotonic()
            if key in _cache_store:
                result, ts = _cache_store[key]
                if now - ts < seconds:
                    return result
            result = fn(*args, **kwargs)
            _cache_store[key] = (result, now)
            return result
        return wrapper
    return decorator

CHARTS_HEADERS = {
    'User-Agent': 'ProtocolPulse/1.0 (+https://protocolpulse.io)',
    'Accept': 'application/json',
}

@_ttl_cache(300)
def _fetch_coingecko_history(days):
    """Fetch BTC/USD OHLCV from CoinGecko with Coinpaprika fallback. Cache 5 min."""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval={'daily' if days >= 30 else 'hourly'}"
    try:
        r = requests.get(url, timeout=8, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("CoinGecko history fetch error: %s", e)
    # Fallback: build minimal price history from current price so charts render
    try:
        price = _fetch_btc_price()
        if price:
            import time
            now_ms = int(time.time() * 1000)
            step = 3600000 if days < 30 else 86400000
            pts = max(1, min(days * (24 if days < 30 else 1), 168))
            prices = [[now_ms - (pts - i) * step, price * (1 + (i - pts / 2) * 0.001)] for i in range(pts)]
            return {"prices": prices, "market_caps": [], "total_volumes": []}
    except Exception as e2:
        logging.warning("CoinGecko history fallback error: %s", e2)
    return None

@_ttl_cache(60)
def _fetch_mempool_stats():
    """Fetch mempool stats from mempool.space with blockstream fallback. Cache 60s."""
    for base in ["https://mempool.space", "https://mempool.emzy.de"]:
        try:
            r = requests.get(f"{base}/api/v1/fees/recommended", timeout=8, headers=CHARTS_HEADERS)
            r.raise_for_status()
            fees = r.json()
            s = requests.get(f"{base}/api/mempool", timeout=8, headers=CHARTS_HEADERS)
            s.raise_for_status()
            mem = s.json()
            return {"fees": fees, "mempool": mem}
        except Exception as e:
            logging.warning("Mempool stats fetch error (%s): %s", base, e)
    # Static fallback so page renders
    return {"fees": {"fastestFee": 10, "halfHourFee": 8, "hourFee": 5, "minimumFee": 1},
            "mempool": {"count": 0, "vsize": 0, "total_fee": 0}}

@_ttl_cache(300)
def _fetch_hashrate_history():
    """Fetch hashrate history from mempool.space. Cache 5 min."""
    try:
        r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=10, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("Hashrate history fetch error: %s", e)
        return None

@_ttl_cache(3600)
def _fetch_pool_distribution():
    """Fetch mining pool distribution. Cache 1 hr."""
    try:
        r = requests.get("https://mempool.space/api/v1/mining/pools/1w", timeout=10, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("Pool distribution fetch error: %s", e)
        return None

@_ttl_cache(1800)
def _fetch_fee_history():
    """Fetch fee history. Cache 30 min."""
    try:
        r = requests.get("https://mempool.space/api/v1/mining/blocks/fees/1w", timeout=10, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("Fee history fetch error: %s", e)
        return None

@_ttl_cache(3600)
def _fetch_lightning_stats():
    """Fetch Lightning Network stats. Cache 1 hr."""
    try:
        r = requests.get("https://mempool.space/api/v1/lightning/statistics/latest", timeout=10, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("Lightning stats fetch error: %s", e)
        return None

@_ttl_cache(3600)
def _fetch_fear_greed():
    """Fetch Fear & Greed index. Cache 1 hr."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=10, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("Fear & Greed fetch error: %s", e)
        return None

@_ttl_cache(30)
def _fetch_btc_price():
    """Fetch current BTC price with 3-source fallback chain. Cache 30s."""
    # Source 1: Coinbase
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=8, headers=CHARTS_HEADERS)
        r.raise_for_status()
        return float(r.json()["data"]["amount"])
    except Exception as e:
        logging.warning("BTC price Coinbase error: %s", e)
    # Source 2: CoinGecko
    try:
        r2 = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=8, headers=CHARTS_HEADERS)
        r2.raise_for_status()
        return float(r2.json()["bitcoin"]["usd"])
    except Exception as e2:
        logging.warning("BTC price CoinGecko error: %s", e2)
    # Source 3: CoinDesk
    try:
        r3 = requests.get("https://api.coindesk.com/v1/bpi/currentprice/USD.json", timeout=8, headers=CHARTS_HEADERS)
        r3.raise_for_status()
        return float(r3.json()["bpi"]["USD"]["rate_float"])
    except Exception as e3:
        logging.warning("BTC price CoinDesk error: %s", e3)
    return None

@_ttl_cache(60)
def _fetch_block_height():
    """Fetch current block height with fallback. Cache 60s."""
    for url in ["https://mempool.space/api/blocks/tip/height",
                "https://blockstream.info/api/blocks/tip/height"]:
        try:
            r = requests.get(url, timeout=8, headers=CHARTS_HEADERS)
            r.raise_for_status()
            return int(r.text.strip())
        except Exception as e:
            logging.warning("Block height fetch error (%s): %s", url, e)
    return None


@app.route('/api/btc-price')
def api_btc_price():
    """Live BTC price endpoint used by nav ticker and stage."""
    price = _fetch_btc_price()
    if price:
        return jsonify({'price': price, 'change_24h': 0})
    # Fallback: CoinGecko with 24h change
    try:
        r = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={'ids': 'bitcoin', 'vs_currencies': 'usd', 'include_24hr_change': 'true'},
            timeout=5, headers={'User-Agent': 'ProtocolPulse/1.0'}
        )
        if r.ok:
            d = r.json()
            return jsonify({
                'price': d.get('bitcoin', {}).get('usd', 0),
                'change_24h': round(d.get('bitcoin', {}).get('usd_24h_change', 0), 2),
            })
    except Exception:
        pass
    return jsonify({'price': 0, 'change_24h': 0}), 200


# ── Page Route ────────────────────────────────────────────────────────────────

@app.route("/btc-charts")
def btc_charts_redirect():
    """Legacy alias → /charts."""
    return redirect(url_for('charts'), code=301)

@app.route("/charts")
def charts():
    """Bitcoin Charts Intelligence Hub."""
    btc_price = _fetch_btc_price() or 0
    block_height = _fetch_block_height() or 0
    mempool_data = _fetch_mempool_stats() or {}
    fees = mempool_data.get("fees", {})
    mem = mempool_data.get("mempool", {})
    mempool_mb = round((mem.get("vsize", 0) or 0) / 1_000_000, 2)
    next_block_fee = fees.get("fastestFee", 0)

    # Supply calculation
    TOTAL_SUPPLY = 21_000_000
    if block_height:
        mined = _calc_mined_supply(block_height)
    else:
        mined = 19_640_000  # fallback estimate
    pct_mined = round(mined / TOTAL_SUPPLY * 100, 4)

    # Next halving
    HALVING_INTERVAL = 210_000
    halving_epoch = (block_height // HALVING_INTERVAL) + 1 if block_height else 4
    blocks_to_halving = (halving_epoch * HALVING_INTERVAL) - block_height if block_height else 0
    days_to_halving = round(blocks_to_halving * 10 / 1440, 1) if blocks_to_halving > 0 else 0

    sats_per_dollar = round(100_000_000 / btc_price, 0) if btc_price > 0 else 0

    return render_template(
        "charts.html",
        btc_price=btc_price,
        block_height=block_height,
        mempool_mb=mempool_mb,
        next_block_fee=next_block_fee,
        mined_supply=mined,
        pct_mined=pct_mined,
        blocks_to_halving=blocks_to_halving,
        days_to_halving=days_to_halving,
        sats_per_dollar=int(sats_per_dollar),
        current_subsidy=3.125,
    )


# === Session 3 Playbook Routes (migrated from root routes.py) ===

@app.route('/sponsors')
@app.route('/advertise')
@app.route('/media-kit')
def sponsors_page():
    """Media kit and sponsorship landing page."""
    return render_template('sponsors.html')

@app.route('/disruption-tracker')
@app.route('/ai-tracker')
@app.route('/kill-list')
def disruption_tracker():
    """AI Disruption Tracker — the Claude Kill List."""
    return render_template('disruption_tracker.html')

@app.route('/events')
def events_page():
    """Events hub — BitcoinDay Naples + BTC in DC."""
    return render_template('events.html')


def _calc_mined_supply(block_height):
    """Calculate total BTC mined from block height using halving schedule."""
    total = 0.0
    remaining = block_height
    subsidy = 50.0
    while remaining > 0:
        blocks_in_epoch = min(remaining, 210_000)
        total += blocks_in_epoch * subsidy
        remaining -= blocks_in_epoch
        subsidy /= 2.0
        if subsidy < 1e-8:
            break
    return round(total, 2)


# ── API Proxy Endpoints ────────────────────────────────────────────────────────

@app.route("/api/charts/price-history")
def api_charts_price_history():
    """Proxy CoinGecko price history. Cache 5 min."""
    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(days, 365))
        data = _fetch_coingecko_history(days)
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except (ValueError, TypeError) as e:
        return jsonify({"error": "invalid parameter"}), 400
    except Exception as e:
        logging.error("api_charts_price_history error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/mempool-data")
def api_charts_mempool_data():
    """Proxy mempool.space stats. Cache 60s."""
    try:
        data = _fetch_mempool_stats()
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except Exception as e:
        logging.error("api_charts_mempool_data error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/hashrate-history")
def api_charts_hashrate_history():
    """Proxy mempool.space hashrate history. Cache 5 min."""
    try:
        data = _fetch_hashrate_history()
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except Exception as e:
        logging.error("api_charts_hashrate_history error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/pool-distribution")
def api_charts_pool_distribution():
    """Proxy mining pool distribution. Cache 1 hr."""
    try:
        data = _fetch_pool_distribution()
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except Exception as e:
        logging.error("api_charts_pool_distribution error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/fee-history")
def api_charts_fee_history():
    """Proxy fee history. Cache 30 min."""
    try:
        data = _fetch_fee_history()
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except Exception as e:
        logging.error("api_charts_fee_history error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/lightning")
def api_charts_lightning():
    """Proxy Lightning Network stats. Cache 1 hr."""
    try:
        data = _fetch_lightning_stats()
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except Exception as e:
        logging.error("api_charts_lightning error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/fear-greed")
def api_charts_fear_greed():
    """Proxy Fear & Greed index. Cache 1 hr."""
    try:
        data = _fetch_fear_greed()
        if data is None:
            return jsonify({"error": "upstream unavailable"}), 503
        return jsonify(data)
    except Exception as e:
        logging.error("api_charts_fear_greed error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/price-alert", methods=["POST"])
def api_charts_price_alert():
    """Save a price alert. Rate-limited: max 3/email/day, 10 active total."""
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()[:254]
        target_price = data.get("target_price")
        direction = (data.get("direction") or "above").strip().lower()

        # Validate email
        if not email or not _re_charts.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({"error": "Valid email required"}), 400

        # Validate price
        try:
            target_price = float(target_price)
            if not (1_000 <= target_price <= 10_000_000):
                raise ValueError("out of range")
        except (TypeError, ValueError):
            return jsonify({"error": "Price must be between $1,000 and $10,000,000"}), 400

        # Validate direction
        if direction not in ("above", "below"):
            direction = "above"

        # Rate limiting: max 10 active alerts per email
        active_count = models.PriceAlert.query.filter_by(email=email, triggered=False).count()
        if active_count >= 10:
            return jsonify({"error": "Maximum 10 active alerts per email"}), 429

        # Rate limiting: max 3 new alerts per email per day
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_count = models.PriceAlert.query.filter(
            models.PriceAlert.email == email,
            models.PriceAlert.created_at >= cutoff
        ).count()
        if recent_count >= 3:
            return jsonify({"error": "Maximum 3 alerts per day per email"}), 429

        alert = models.PriceAlert(
            email=email,
            target_price=target_price,
            direction=direction,
        )
        try:
            db.session.add(alert)
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            logging.error("PriceAlert DB error: %s", db_err)
            return jsonify({"error": "Could not save alert"}), 500

        return jsonify({"success": True, "message": f"Alert set for BTC {direction} ${target_price:,.0f}"}), 201

    except Exception as e:
        logging.error("api_charts_price_alert error: %s", e)
        return jsonify({"error": "internal error"}), 500


@app.route("/api/charts/ai-explain", methods=["POST"])
def api_charts_ai_explain():
    """AI chart interpretation via Anthropic Claude."""
    try:
        data = request.get_json(silent=True) or {}
        chart_type = (data.get("chart_type") or "price")[:50]
        chart_data = data.get("chart_data") or {}
        question = (data.get("question") or "Explain this chart")[:500]

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"explanation": "AI interpretation requires ANTHROPIC_API_KEY. Key not configured."}), 200

        # Build context from chart data
        context_parts = [f"Chart type: {chart_type}"]
        if isinstance(chart_data, dict):
            for k, v in list(chart_data.items())[:10]:
                context_parts.append(f"{k}: {v}")
        context = "\n".join(context_parts)

        prompt = f"""You are a professional Bitcoin analyst interpreting chart data for Protocol Pulse, a Bitcoin intelligence platform.

Chart context:
{context}

User question: {question}

Provide a concise 2-3 sentence analyst interpretation. Focus on what the data signals for Bitcoin market structure or on-chain health. Be precise, not vague. Use professional financial analyst tone. Do not use markdown formatting."""

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        explanation = message.content[0].text.strip() if message.content else "Analysis unavailable."
        return jsonify({"explanation": explanation})

    except Exception as e:
        logging.error("api_charts_ai_explain error: %s", e)
        return jsonify({"explanation": "AI analysis temporarily unavailable."}), 200


# ── Embed Route ────────────────────────────────────────────────────────────────

@app.route("/charts/embed/<chart_id>")
def charts_embed(chart_id):
    """Minimal embeddable chart page."""
    allowed = {"price", "hashrate", "mempool", "pools", "fear-greed"}
    if chart_id not in allowed:
        return "Invalid chart", 400
    days = request.args.get("days", 7)
    try:
        days = int(days)
        days = max(1, min(days, 365))
    except (ValueError, TypeError):
        days = 7
    return render_template("charts_embed.html", chart_id=chart_id, days=days)


# ── Cron: Check Price Alerts ───────────────────────────────────────────────────

def check_price_alerts():
    """Check active price alerts against current BTC price and send emails."""
    try:
        price = _fetch_btc_price()
        if not price:
            return
        active_alerts = models.PriceAlert.query.filter_by(triggered=False).all()
        triggered_ids = []
        for alert in active_alerts:
            should_trigger = (
                (alert.direction == "above" and price >= alert.target_price) or
                (alert.direction == "below" and price <= alert.target_price)
            )
            if should_trigger:
                triggered_ids.append(alert.id)
                _send_price_alert_email(alert, price)
                alert.triggered = True
                alert.triggered_at = datetime.utcnow()
        if triggered_ids:
            try:
                db.session.commit()
                logging.info("Triggered %d price alerts", len(triggered_ids))
            except Exception as commit_err:
                db.session.rollback()
                logging.error("Price alert commit error: %s", commit_err)
    except Exception as e:
        logging.error("check_price_alerts error: %s", e)


def _send_price_alert_email(alert, current_price):
    """Send price alert email via SendGrid or log if not configured."""
    try:
        sg_key = os.environ.get("SENDGRID_API_KEY")
        from_email = os.environ.get("SENDGRID_FROM_EMAIL", "alerts@protocolpulse.io")
        if not sg_key:
            logging.info("Price alert triggered for %s: BTC %s $%.0f (no email key)", alert.email, alert.direction, current_price)
            return
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        subject = f"⚡ BTC Price Alert: ${current_price:,.0f} — Protocol Pulse"
        body = (
            f"Your Bitcoin price alert was triggered!\n\n"
            f"Alert: BTC {alert.direction} ${alert.target_price:,.0f}\n"
            f"Current price: ${current_price:,.0f}\n\n"
            f"View live charts: https://protocolpulse.io/charts\n\n"
            f"— Protocol Pulse Intelligence"
        )
        msg = Mail(from_email=from_email, to_emails=alert.email, subject=subject, plain_text_content=body)
        SendGridAPIClient(sg_key).send(msg)
    except Exception as e:
        logging.warning("Price alert email send error: %s", e)

# ── P3 Mining Intel ───────────────────────────────────────────────────────────

@app.route('/mining')
def mining_hub():
    """Bitcoin Mining Intelligence Hub — live hashrate, ASIC calculator, pool distribution."""
    return render_template('mining_hub.html')


@app.route('/api/mining/live-stats')
@cache.cached(timeout=30, key_prefix='mining_live_stats')
def api_mining_live_stats():
    """
    Live mining command center data: hashrate, difficulty, adjustment, hash price,
    block height, mempool fees, sats_per_hash.
    Cached 30s. All external calls have timeouts + graceful fallback.
    """
    import math
    result = {
        'hashrate_eh': None,
        'difficulty': None,
        'difficulty_formatted': None,
        'next_adjustment_pct': None,
        'blocks_until_adjustment': None,
        'epoch_progress_pct': None,
        'block_height': None,
        'btc_price_usd': None,
        'hash_price_usd_per_ph': None,
        'sats_per_hash': None,
        'block_reward_btc': 3.125,
        'block_reward_usd': None,
        'mempool_fee_low': None,
        'mempool_fee_mid': None,
        'mempool_fee_high': None,
        'next_3_adjustment_forecast': [],
        'updated_at': datetime.utcnow().isoformat(),
    }

    # 1. Hashrate + current difficulty
    try:
        r = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=10)
        if r.ok:
            d = r.json()
            raw_hashrate = d.get('currentHashrate') or 0
            result['hashrate_eh'] = round(raw_hashrate / 1e18, 2) if raw_hashrate else None
            diff = d.get('currentDifficulty') or 0
            result['difficulty'] = diff
            if diff:
                t = diff / 1e12
                result['difficulty_formatted'] = f"{t:.2f}T"
    except requests.exceptions.RequestException as e:
        logging.warning('mining live-stats hashrate error: %s', e)

    # 2. Difficulty adjustment
    try:
        r = requests.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=10)
        if r.ok:
            d = r.json()
            result['next_adjustment_pct'] = round(d.get('difficultyChange', 0), 2)
            remaining = d.get('remainingBlocks', 0)
            result['blocks_until_adjustment'] = remaining
            # epoch progress: (2016 - remaining) / 2016
            if remaining is not None:
                completed = 2016 - remaining
                result['epoch_progress_pct'] = round(max(0, min(100, (completed / 2016) * 100)), 1)
    except requests.exceptions.RequestException as e:
        logging.warning('mining live-stats difficulty-adjustment error: %s', e)

    # 3. Block height
    try:
        r = requests.get('https://mempool.space/api/blocks/tip/height', timeout=10)
        if r.ok:
            result['block_height'] = int(r.text.strip())
    except requests.exceptions.RequestException as e:
        logging.warning('mining live-stats block height error: %s', e)

    # 4. BTC price
    try:
        r = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
            timeout=10
        )
        if r.ok:
            result['btc_price_usd'] = r.json().get('bitcoin', {}).get('usd')
    except requests.exceptions.RequestException as e:
        logging.warning('mining live-stats btc price error: %s', e)

    # 5. Derived metrics
    if result['hashrate_eh'] and result['btc_price_usd']:
        hashrate_ph = result['hashrate_eh'] * 1e6
        daily_btc = 3.125 * 144
        result['hash_price_usd_per_ph'] = round((daily_btc * result['btc_price_usd']) / hashrate_ph, 4)
        if hashrate_ph > 0:
            hashes_per_day = hashrate_ph * 1e12 * 86400
            btc_per_hash = daily_btc / hashes_per_day if hashes_per_day > 0 else 0
            result['sats_per_hash'] = round(btc_per_hash * 1e8, 12)
        result['block_reward_usd'] = round(3.125 * result['btc_price_usd'], 2)

    # 6. 3-epoch difficulty forecast (mean-reversion model)
    if result['next_adjustment_pct'] is not None:
        base_adj = result['next_adjustment_pct']
        forecast = []
        adj = base_adj
        for i in range(3):
            adj = round(adj * (0.7 ** i) if i > 0 else adj, 2)
            forecast.append({'epoch': i + 1, 'predicted_pct': adj})
        result['next_3_adjustment_forecast'] = forecast

    # 7. Mempool fee rates
    try:
        r = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=10)
        if r.ok:
            fees = r.json()
            result['mempool_fee_low'] = fees.get('economyFee')
            result['mempool_fee_mid'] = fees.get('halfHourFee')
            result['mempool_fee_high'] = fees.get('fastestFee')
    except requests.exceptions.RequestException as e:
        logging.warning('mining live-stats mempool fees error: %s', e)

    return jsonify(result)


@app.route('/api/mining/pools')
@cache.cached(timeout=300, key_prefix='mining_pools')
def api_mining_pools():
    """
    Pool distribution data from mempool.space (last 7 days).
    Computes HHI (Herfindahl-Hirschman Index) for concentration risk.
    Cached 5 minutes.
    """
    try:
        r = requests.get('https://mempool.space/api/v1/mining/pools/1w', timeout=10)
        if not r.ok:
            return jsonify({'pools': [], 'hhi': None, 'error': 'upstream error'}), 502

        data = r.json()
        pools_raw = data.get('pools', [])
        if not pools_raw:
            return jsonify({'pools': [], 'hhi': None})

        total_blocks = sum(p.get('blockCount', 0) for p in pools_raw)
        pools = []
        hhi = 0.0
        for p in pools_raw[:12]:
            blocks = p.get('blockCount', 0)
            share_pct = round((blocks / total_blocks * 100), 2) if total_blocks else 0
            hhi += (share_pct ** 2)
            pools.append({
                'name': p.get('name', 'Unknown'),
                'slug': p.get('slug', ''),
                'share_pct': share_pct,
                'block_count': blocks,
            })

        hhi_rounded = round(hhi)
        if hhi_rounded > 2500:
            concentration_label, concentration_color = 'HIGH', 'red'
        elif hhi_rounded > 1500:
            concentration_label, concentration_color = 'MODERATE', 'gold'
        else:
            concentration_label, concentration_color = 'HEALTHY', 'green'

        top3_share = sum(p['share_pct'] for p in pools[:3])
        centralization_warning = top3_share > 51

        return jsonify({
            'pools': pools,
            'hhi': hhi_rounded,
            'concentration_label': concentration_label,
            'concentration_color': concentration_color,
            'top3_share_pct': round(top3_share, 1),
            'centralization_warning': centralization_warning,
            'updated_at': datetime.utcnow().isoformat(),
        })
    except requests.exceptions.RequestException as e:
        logging.error('mining pools API error: %s', e)
        return jsonify({'pools': [], 'hhi': None, 'error': str(e)}), 502
    except Exception as e:
        logging.error('mining pools unexpected error: %s', e)
        return jsonify({'pools': [], 'hhi': None, 'error': 'internal error'}), 500


@app.route('/api/charts/hashrate-history')
@cache.cached(timeout=600, key_prefix='hashrate_history')
def api_hashrate_history():
    """
    30-day hashrate history for SVG chart. Source: mempool.space.
    Returns: [{timestamp, hashrate_eh}] + ath_eh + 7day_ma points.
    Cached 10 minutes.
    """
    try:
        r = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=10)
        if not r.ok:
            return jsonify({'data': [], 'ath_eh': None}), 502

        raw = r.json()
        hashrates = raw.get('hashrates', [])
        if not hashrates:
            return jsonify({'data': [], 'ath_eh': None})

        recent = hashrates[-30:] if len(hashrates) >= 30 else hashrates
        points = []
        for h in recent:
            ts = h.get('timestamp')
            val = h.get('avgHashrate') or h.get('hashrate')
            if ts and val:
                points.append({'timestamp': ts, 'hashrate_eh': round(val / 1e18, 2)})

        if not points:
            return jsonify({'data': [], 'ath_eh': None})

        all_vals = [p['hashrate_eh'] for p in points]
        ath_eh = max(all_vals) if all_vals else None

        window = 7
        ma_points = []
        for i in range(len(points)):
            start = max(0, i - window + 1)
            window_vals = [points[j]['hashrate_eh'] for j in range(start, i + 1)]
            ma_points.append(round(sum(window_vals) / len(window_vals), 2))

        return jsonify({
            'data': points,
            'ma7': ma_points,
            'ath_eh': round(ath_eh, 2) if ath_eh else None,
            'current_eh': round(raw.get('currentHashrate', 0) / 1e18, 2),
            'updated_at': datetime.utcnow().isoformat(),
        })
    except requests.exceptions.RequestException as e:
        logging.error('hashrate history error: %s', e)
        return jsonify({'data': [], 'ath_eh': None, 'error': str(e)}), 502
    except Exception as e:
        logging.error('hashrate history unexpected error: %s', e)
        return jsonify({'data': [], 'ath_eh': None, 'error': 'internal error'}), 500


@app.route('/api/mining/articles')
def api_mining_articles():
    """Latest 8 mining articles for the /mining hub page."""
    try:
        articles = models.Article.query.filter_by(
            published=True, category='mining'
        ).order_by(models.Article.created_at.desc()).limit(8).all()
        result = []
        for a in articles:
            result.append({
                'id': a.id,
                'title': a.title,
                'summary': (a.summary or a.content or '')[:200].strip(),
                'created_at': a.created_at.isoformat() if a.created_at else None,
                'tags': a.tags or '',
                'url': f'/articles/{a.id}',
            })
        return jsonify({'articles': result})
    except Exception as e:
        logging.error('mining articles API error: %s', e)
        return jsonify({'articles': [], 'error': 'internal error'}), 500
# =============================================
# P3 AFFILIATE INTEGRATION — Meanwhile + RNS.ID
# Created: 2026-03-09 | Branch: feature/p3-affiliates
# =============================================

def _p3_init_tables():
    """Ensure p3_affiliate_clicks and p3_affiliate_ab_results tables exist."""
    try:
        db.session.execute(db.text(
            "CREATE TABLE IF NOT EXISTS p3_affiliate_clicks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "partner TEXT NOT NULL, "
            "referrer_page TEXT, "
            "ab_variant TEXT, "
            "converted INTEGER DEFAULT 0, "
            "user_hash TEXT, "
            "user_agent_hash TEXT, "
            "clicked_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        ))
        db.session.execute(db.text(
            "CREATE INDEX IF NOT EXISTS idx_p3_aff_partner_date "
            "ON p3_affiliate_clicks(partner, clicked_at)"
        ))
        db.session.execute(db.text(
            "CREATE TABLE IF NOT EXISTS p3_affiliate_ab_results ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "partner TEXT NOT NULL, "
            "variant TEXT NOT NULL, "
            "impressions INTEGER DEFAULT 0, "
            "clicks INTEGER DEFAULT 0, "
            "winner_locked INTEGER DEFAULT 0, "
            "calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE(partner, variant))"
        ))
        db.session.commit()
    except Exception as _e:
        logging.debug("p3_init_tables: %s", _e)
        db.session.rollback()


@app.route('/go/meanwhile')
@limiter.limit("30 per minute")
def affiliate_go_meanwhile():
    """Track click → redirect to Meanwhile with referral code."""
    _p3_init_tables()
    try:
        from services.affiliate_injector import track_click, PARTNER_CONFIG
        from services.affiliate_injector import _get_tracking_salt
        salt = _get_tracking_salt()
        today = datetime.utcnow().date().isoformat()
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        ip = raw_ip.split(',')[0].strip()
        user_hash = hashlib.sha256(f"{ip}:{today}:{salt}".encode()).hexdigest()
        referrer = request.args.get('ref') or request.referrer or ''
        variant = request.args.get('v', 'A')
        track_click('meanwhile', referrer[:500], variant, user_hash,
                    request.headers.get('User-Agent', '')[:500])
        dest = PARTNER_CONFIG['meanwhile']['redirect_url']
        resp = redirect(dest, code=302)
        resp.headers['Cache-Control'] = 'no-store, no-cache'
        return resp
    except Exception as e:
        logging.error("affiliate_go_meanwhile error: %s", e)
        return redirect('https://www.meanwhile.life/', code=302)


@app.route('/go/rns')
@limiter.limit("30 per minute")
def affiliate_go_rns():
    """Track click → redirect to RNS.ID with referral code."""
    _p3_init_tables()
    try:
        from services.affiliate_injector import track_click, PARTNER_CONFIG
        from services.affiliate_injector import _get_tracking_salt
        salt = _get_tracking_salt()
        today = datetime.utcnow().date().isoformat()
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        ip = raw_ip.split(',')[0].strip()
        user_hash = hashlib.sha256(f"{ip}:{today}:{salt}".encode()).hexdigest()
        referrer = request.args.get('ref') or request.referrer or ''
        variant = request.args.get('v', 'A')
        track_click('rns_id', referrer[:500], variant, user_hash,
                    request.headers.get('User-Agent', '')[:500])
        dest = PARTNER_CONFIG['rns_id']['redirect_url']
        resp = redirect(dest, code=302)
        resp.headers['Cache-Control'] = 'no-store, no-cache'
        return resp
    except Exception as e:
        logging.error("affiliate_go_rns error: %s", e)
        return redirect('https://rns.id/', code=302)


@app.route('/bitcoin-life-insurance')
def bitcoin_life_insurance():
    """Meanwhile Bitcoin Life Insurance landing page."""
    return render_template('bitcoin_life_insurance.html')


@app.route('/digital-residency')
def digital_residency():
    """RNS.ID Palau Digital Residency landing page."""
    return render_template('digital_residency.html')


@app.route('/admin/affiliates')
@login_required
@admin_required
def admin_affiliates():
    """Admin affiliate analytics dashboard."""
    _p3_init_tables()
    try:
        from services.affiliate_injector import compute_ab_stats, get_partner_config
        K_ANON = 10  # k-anonymity threshold

        # Clicks last 30 days per partner
        rows = db.session.execute(db.text(
            "SELECT partner, date(clicked_at) as day, COUNT(*) as cnt "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner, day ORDER BY day"
        )).fetchall()
        clicks_by_day = {}
        for r in rows:
            clicks_by_day.setdefault(r[0], {})[r[1]] = r[2]

        # Total clicks (30d) per partner
        totals = db.session.execute(db.text(
            "SELECT partner, COUNT(*) as total, "
            "COUNT(DISTINCT user_hash) as unique_users "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner"
        )).fetchall()
        totals_map = {r[0]: {"total": r[1], "unique_users": r[2]} for r in totals}

        # Top referrer pages (k-anon enforced)
        top_refs = db.session.execute(db.text(
            "SELECT partner, referrer_page, COUNT(*) as cnt, "
            "COUNT(DISTINCT user_hash) as uniq "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "AND referrer_page != '' "
            "GROUP BY partner, referrer_page "
            "HAVING uniq >= :k "
            "ORDER BY cnt DESC LIMIT 20"
        ), {"k": K_ANON}).fetchall()

        # A/B stats
        ab_stats = {
            "meanwhile": compute_ab_stats("meanwhile"),
            "rns_id": compute_ab_stats("rns_id"),
        }

        partner_cfg = get_partner_config()

        return render_template(
            'admin_affiliates.html',
            clicks_by_day=clicks_by_day,
            totals_map=totals_map,
            top_refs=top_refs,
            ab_stats=ab_stats,
            partner_cfg=partner_cfg,
            k_anon=K_ANON,
        )
    except Exception as e:
        logging.error("admin_affiliates error: %s", e)
        return render_template('admin_affiliates.html',
                               clicks_by_day={}, totals_map={}, top_refs=[],
                               ab_stats={}, partner_cfg={}, k_anon=10,
                               error=str(e))


@app.route('/api/affiliates/metrics')
@login_required
@admin_required
def api_affiliates_metrics():
    """JSON endpoint: affiliate click metrics for dashboard charts."""
    _p3_init_tables()
    try:
        from services.affiliate_injector import compute_ab_stats, PARTNER_CONFIG
        K_ANON = 10

        # Daily clicks last 30 days
        rows = db.session.execute(db.text(
            "SELECT partner, date(clicked_at) as day, COUNT(*) as cnt "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner, day ORDER BY day"
        )).fetchall()

        daily = {}
        for r in rows:
            daily.setdefault(r[0], []).append({"date": r[1], "clicks": r[2]})

        # Partner totals
        totals = db.session.execute(db.text(
            "SELECT partner, COUNT(*) as total, "
            "COUNT(DISTINCT user_hash) as unique_users "
            "FROM p3_affiliate_clicks "
            "GROUP BY partner"
        )).fetchall()
        totals_map = {r[0]: {"total": r[1], "unique_users": r[2]} for r in totals}

        # Estimated earnings
        earnings = {}
        for partner, cfg in PARTNER_CONFIG.items():
            t = totals_map.get(partner, {}).get("total", 0)
            # Conservative: 2% click-to-conversion rate
            earnings[partner] = round(t * 0.02 * cfg["estimated_commission"], 2)

        return jsonify({
            "ok": True,
            "daily_clicks": daily,
            "totals": totals_map,
            "estimated_earnings": earnings,
            "ab_stats": {
                "meanwhile": compute_ab_stats("meanwhile"),
                "rns_id": compute_ab_stats("rns_id"),
            },
        })
    except Exception as e:
        logging.error("api_affiliates_metrics error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/affiliates/impression', methods=['POST'])
@limiter.limit("60 per minute")
def api_affiliates_impression():
    """Record affiliate impression (JS beacon). No auth required — public endpoint."""
    _p3_init_tables()
    try:
        data = request.get_json(silent=True) or {}
        partner = data.get('partner', '')
        variant = data.get('variant', 'A')
        referrer_page = data.get('referrer_page', '')[:500]

        if partner not in ('meanwhile', 'rns_id'):
            return '', 204

        from services.affiliate_injector import track_impression
        from services.affiliate_injector import _get_tracking_salt
        salt = _get_tracking_salt()
        today = datetime.utcnow().date().isoformat()
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        ip = raw_ip.split(',')[0].strip()
        user_hash = hashlib.sha256(f"{ip}:{today}:{salt}".encode()).hexdigest()
        track_impression(partner, referrer_page, variant, user_hash)
        return '', 204
    except Exception as e:
        logging.debug("api_affiliates_impression error: %s", e)
        return '', 204


@app.route('/api/affiliates/click', methods=['POST'])
@limiter.limit("60 per minute")
def api_affiliates_click():
    """
    Record affiliate click from landing page JS beacon.
    Distinct from /api/affiliates/impression — fires when user clicks final CTA.
    P1 FIX (U4): separate endpoint prevents impression/click metric pollution.
    """
    _p3_init_tables()
    try:
        data = request.get_json(silent=True) or {}
        partner = data.get('partner', '')
        variant = data.get('variant', 'direct')
        referrer_page = data.get('referrer_page', '')[:500]

        if partner not in ('meanwhile', 'rns_id'):
            return '', 204

        from services.affiliate_injector import track_click, _get_tracking_salt
        salt = _get_tracking_salt()
        today = datetime.utcnow().date().isoformat()
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        ip = raw_ip.split(',')[0].strip()
        user_hash = hashlib.sha256(f"{ip}:{today}:{salt}".encode()).hexdigest()
        track_click(partner, referrer_page, variant, user_hash,
                    request.headers.get('User-Agent', '')[:500])
        return '', 204
    except Exception as e:
        logging.debug("api_affiliates_click error: %s", e)
        return '', 204


@app.route('/api/affiliates/declare-winner', methods=['POST'])
@login_required
@admin_required
def api_affiliates_declare_winner():
    """Lock in winning A/B variant for a partner."""
    _p3_init_tables()
    try:
        data = request.get_json(silent=True) or {}
        partner = data.get('partner', '')
        variant = data.get('variant', '')
        if partner not in ('meanwhile', 'rns_id') or variant not in ('A', 'B'):
            return jsonify({'ok': False, 'error': 'Invalid partner or variant'}), 400

        # Lock winner: set winner_locked=1 on winning variant, disable loser
        db.session.execute(db.text(
            "UPDATE p3_affiliate_ab_results SET winner_locked = 1 "
            "WHERE partner = :partner AND variant = :variant"
        ), {"partner": partner, "variant": variant})
        db.session.commit()
        return jsonify({'ok': True, 'partner': partner, 'winner': variant})
    except Exception as e:
        db.session.rollback()
        logging.error("declare_winner error: %s", e)
        return jsonify({'ok': False, 'error': str(e)}), 500

# ══════════════════════════════════════════════════════
# MARKET BRIEFING ROOM (F2)
# ══════════════════════════════════════════════════════

try:
    from services.briefing_service import generate_briefing as _run_briefing_generation
    _briefing_service_ok = True
except Exception as _bse:
    logging.warning("briefing_service import failed: %s", _bse)
    _briefing_service_ok = False


def _next_briefing_utc_epoch() -> int:
    """P1-2: Compute the UTC epoch (ms) of the next scheduled ET briefing slot.
    Returns a JavaScript-compatible millisecond timestamp.
    DST-safe: uses pytz IANA timezone — no manual offset arithmetic.
    """
    try:
        import pytz as _tz
        _ET = _tz.timezone("America/New_York")
        _UTC = _tz.utc
        SLOTS = [(7, 0), (9, 30), (16, 30)]
        now_et = datetime.now(_ET)
        for h, m in SLOTS:
            candidate = now_et.replace(hour=h, minute=m, second=0, microsecond=0)
            if candidate > now_et:
                return int(candidate.astimezone(_UTC).timestamp() * 1000)
        # All today's slots passed — next is tomorrow's 07:00
        tomorrow = (now_et + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
        return int(tomorrow.astimezone(_UTC).timestamp() * 1000)
    except Exception as e:
        logging.warning("_next_briefing_utc_epoch failed: %s", e)
        return 0


@app.route('/stage')
def stage_page():
    """24/7 autonomous Bitcoin broadcast station."""
    return render_template('stage.html')


@app.route('/briefing')
def market_briefing():
    """Market Briefing Room — LAW 3: always show latest + 3 previous."""
    try:
        latest = (
            models.MarketBriefing.query
            .filter_by(published=True)
            .order_by(models.MarketBriefing.generated_at.desc())
            .first()
        )
        recent = (
            models.MarketBriefing.query
            .filter_by(published=True)
            .order_by(models.MarketBriefing.generated_at.desc())
            .offset(1)
            .limit(3)
            .all()
        )
    except Exception as e:
        logging.warning("market_briefing DB error: %s", e)
        latest = None
        recent = []
    next_utc = _next_briefing_utc_epoch()
    return render_template(
        'market_briefing.html',
        latest=latest,
        recent=recent,
        next_briefing_utc=next_utc,
    )


@app.route('/briefing/archive')
def briefing_archive():
    """All published briefings — paginated."""
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = 12
        all_briefings = (
            models.MarketBriefing.query
            .filter_by(published=True)
            .order_by(models.MarketBriefing.generated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        total = models.MarketBriefing.query.filter_by(published=True).count()
        has_next = (page * per_page) < total
        has_prev = page > 1
    except Exception as e:
        logging.warning("briefing_archive DB error: %s", e)
        all_briefings = []
        has_next = has_prev = False
        page = 1
    return render_template(
        'market_briefing.html',
        latest=all_briefings[0] if all_briefings else None,
        recent=all_briefings[1:4] if len(all_briefings) > 1 else [],
    )


@app.route('/api/briefing/latest')
def briefing_latest():
    """Returns the latest completed, published briefing as JSON."""
    try:
        b = (
            models.MarketBriefing.query
            .filter_by(published=True, status='completed')
            .order_by(models.MarketBriefing.generated_at.desc())
            .first()
        )
        if not b:
            return jsonify({}), 200
        return jsonify(b.to_dict())
    except Exception as e:
        logging.warning("briefing_latest error: %s", e)
        return jsonify({"error": "Service unavailable"}), 503


@app.route('/api/briefing/<int:briefing_id>')
def briefing_by_id(briefing_id):
    """P1-1: Fetch a single briefing by ID — used by loadBriefing() JS."""
    try:
        b = models.MarketBriefing.query.get(briefing_id)
        if not b or not b.published:
            return jsonify({"error": "Not found"}), 404
        import pytz
        ET = pytz.timezone("America/New_York")
        # P1-3: Convert UTC generated_at to ET for display
        gen_et = ""
        if b.generated_at:
            utc_dt = pytz.utc.localize(b.generated_at)
            et_dt = utc_dt.astimezone(ET)
            gen_et = et_dt.strftime("%-I:%M %p ET · %b %-d, %Y")
        data = b.to_dict()
        data['generated_at_et'] = gen_et
        data['script_text'] = b.script_text   # full script for script panel
        return jsonify(data)
    except Exception as e:
        logging.warning("briefing_by_id error: %s", e)
        return jsonify({"error": "Service unavailable"}), 503


@app.route('/api/briefing/list')
def briefing_list():
    """Returns up to 10 recent published briefings as JSON."""
    try:
        limit = min(int(request.args.get('limit', 10)), 50)
        briefings = (
            models.MarketBriefing.query
            .filter_by(published=True)
            .order_by(models.MarketBriefing.generated_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify([b.to_dict() for b in briefings])
    except Exception as e:
        logging.warning("briefing_list error: %s", e)
        return jsonify([])


@app.route('/api/briefing/generate', methods=['POST'])
@admin_required
def briefing_generate_manual():
    """Manual briefing trigger — admin only. Body: {briefing_type: 'pre_market'|'open'|'close'}"""
    if not _briefing_service_ok:
        return jsonify({"success": False, "error": "Briefing service unavailable"}), 503

    data = request.get_json(silent=True) or {}
    briefing_type = data.get('briefing_type', 'open')
    if briefing_type not in ('pre_market', 'open', 'close'):
        return jsonify({"success": False, "error": "Invalid briefing_type"}), 400

    try:
        result = _run_briefing_generation(briefing_type)
        status_code = 200 if result.get('success') else 500
        return jsonify(result), status_code
    except Exception as e:
        logging.error("briefing_generate_manual error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/briefing/status/<int:briefing_id>')
def briefing_status(briefing_id):
    """Poll the status of a specific briefing by ID."""
    try:
        b = models.MarketBriefing.query.get(briefing_id)
        if not b:
            return jsonify({"error": "Not found"}), 404
        return jsonify({
            "id": b.id,
            "status": b.status,
            "published": b.published,
            "video_url": b.video_url,
            "error_message": b.error_message,
        })
    except Exception as e:
        logging.warning("briefing_status error: %s", e)
        return jsonify({"error": "Service unavailable"}), 503

# ═══════════════════════════════════════════════════════════════
# SCHIFF-BOT / BRIAN — HYPOCRISY METRIC
# Routes: /schiff, /brian, /api/schiff/score, /api/schiff/refresh
# ═══════════════════════════════════════════════════════════════

try:
    from services.schiff_service import (
        get_latest_score as _schiff_get_score,
        get_score_history as _schiff_get_history,
        get_statements as _schiff_get_statements,
        update_score as _schiff_update_score,
        seed_statements as _schiff_seed,
    )
    _schiff_available = True
except Exception as _schiff_import_err:
    logging.warning("schiff_service import failed: %s", _schiff_import_err)
    _schiff_available = False


@app.route('/schiff')
@app.route('/brian')
def schiff_bot():
    """Brian the Hypocrisy Analyst — Schiff-Bot page."""
    try:
        if _schiff_available:
            score = _schiff_get_score(app=app)
            history = _schiff_get_history(days=90, app=app)
            statements = _schiff_get_statements(limit=12, app=app)
        else:
            score = {}
            history = []
            statements = []
    except Exception as e:
        logging.warning("schiff_bot view error: %s", e)
        score = {}
        history = []
        statements = []
    return render_template('schiff_bot.html', score=score, history=history, statements=statements)


@app.route('/api/schiff/score')
def schiff_score_api():
    """Return the latest Schiff hypocrisy score as JSON."""
    try:
        if not _schiff_available:
            return jsonify({"error": "schiff_service unavailable"}), 503
        score = _schiff_get_score(app=app)
        return jsonify(score)
    except Exception as e:
        logging.error("schiff_score_api error: %s", e)
        return jsonify({"error": "Internal error", "detail": str(e)}), 500


@app.route('/api/schiff/refresh', methods=['POST'])
@admin_required
@limiter.limit("5 per hour")
def schiff_refresh():
    """Admin-only: trigger a fresh EDGAR fetch and score recalculation. Rate-limited 5/hour."""
    try:
        if not _schiff_available:
            return jsonify({"error": "schiff_service unavailable"}), 503
        result = _schiff_update_score(app=app)
        return jsonify(result)
    except Exception as e:
        logging.error("schiff_refresh error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/schiff/statements')
def schiff_statements_api():
    """Return public statements list as JSON."""
    try:
        if not _schiff_available:
            return jsonify([])
        stmts = _schiff_get_statements(limit=50, app=app)
        return jsonify(stmts)
    except Exception as e:
        logging.warning("schiff_statements_api error: %s", e)
        return jsonify([])


# Auto-seed statements once on startup
try:
    if _schiff_available:
        _schiff_seed(app)
except Exception as _seed_err:
    logging.warning("Schiff seed (startup): %s", _seed_err)

# =====================================
# F5 NODE WATCH — BITNODES PROXY
# =====================================

# In-memory fallback cache (persists within a process lifetime)
_bitnodes_snapshot_cache = {'data': None, 'expires': 0}
_bitnodes_history_cache  = {'data': None, 'expires': 0}

_BITNODES_SNAPSHOT_URL = 'https://bitnodes.io/api/v1/snapshots/?limit=1'
_BITNODES_HISTORY_URL  = 'https://bitnodes.io/api/v1/snapshots/?limit=48'


def _parse_bitnodes_snapshot(raw):
    """Extract a compact client-ready dict from a raw Bitnodes API response."""
    if not raw or not isinstance(raw, dict):
        return None
    results = raw.get('results', [])
    if not results:
        return None
    snap = results[0]
    nodes = snap.get('nodes', {})
    total = snap.get('total_nodes') or len(nodes)

    versions = {}
    countries = {}
    ipv4 = 0
    ipv6 = 0
    for addr, info in nodes.items():
        if not isinstance(info, list):
            continue
        ver = info[1] if len(info) > 1 else 'unknown'
        versions[ver] = versions.get(ver, 0) + 1
        country = info[7] if len(info) > 7 else None
        if country:
            countries[country] = countries.get(country, 0) + 1
        if addr.startswith('['):
            ipv6 += 1
        else:
            ipv4 += 1

    top_versions  = sorted(versions.items(),  key=lambda x: x[1], reverse=True)[:5]
    top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        'node_count': total,
        'timestamp':  snap.get('timestamp'),
        'versions':   top_versions,
        'countries':  top_countries,
        'ipv4': ipv4,
        'ipv6': ipv6,
    }


def _parse_bitnodes_history(raw):
    """Return [{timestamp, node_count}, ...] newest-first from Bitnodes history."""
    if not raw or not isinstance(raw, dict):
        return []
    out = []
    for snap in raw.get('results', []):
        count = snap.get('total_nodes', 0)
        ts    = snap.get('timestamp')
        if count and ts:
            out.append({'timestamp': ts, 'node_count': count})
    return out


@app.route('/api/proxy/bitnodes/snapshot')
def bitnodes_snapshot():
    """Proxy to Bitnodes snapshot API — 5-min server-side cache, never hits browser directly."""
    import time as _time
    now = _time.time()
    if _bitnodes_snapshot_cache['data'] and now < _bitnodes_snapshot_cache['expires']:
        resp = make_response(jsonify(_bitnodes_snapshot_cache['data']))
        resp.headers['X-Cache'] = 'HIT'
        resp.headers['Cache-Control'] = 'public, max-age=300'
        return resp

    try:
        r = requests.get(_BITNODES_SNAPSHOT_URL, timeout=8,
                         headers={'Accept': 'application/json'})
        r.raise_for_status()
        parsed = _parse_bitnodes_snapshot(r.json())
        if parsed is None:
            raise ValueError('Empty or malformed Bitnodes response')
        _bitnodes_snapshot_cache['data']    = parsed
        _bitnodes_snapshot_cache['expires'] = now + 300
        resp = make_response(jsonify(parsed))
        resp.headers['X-Cache'] = 'MISS'
        resp.headers['Cache-Control'] = 'public, max-age=300'
        return resp
    except Exception as e:
        logging.warning('bitnodes_snapshot error: %s', e)
        stale = _bitnodes_snapshot_cache.get('data')
        if stale:
            resp = make_response(jsonify({**stale, 'stale': True}))
            resp.headers['X-Cache'] = 'STALE'
            return resp
        return jsonify({'error': 'Bitnodes unavailable', 'node_count': None}), 503


@app.route('/api/proxy/bitnodes/history')
def bitnodes_history():
    """Proxy to Bitnodes 24-hr history (48 × 30-min) — 1-hr server-side cache."""
    import time as _time
    now = _time.time()
    if _bitnodes_history_cache['data'] and now < _bitnodes_history_cache['expires']:
        resp = make_response(jsonify(_bitnodes_history_cache['data']))
        resp.headers['X-Cache'] = 'HIT'
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp

    try:
        r = requests.get(_BITNODES_HISTORY_URL, timeout=10,
                         headers={'Accept': 'application/json'})
        r.raise_for_status()
        parsed = _parse_bitnodes_history(r.json())
        if not parsed:
            raise ValueError('Empty history from Bitnodes')
        _bitnodes_history_cache['data']    = parsed
        _bitnodes_history_cache['expires'] = now + 3600
        resp = make_response(jsonify(parsed))
        resp.headers['X-Cache'] = 'MISS'
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp
    except Exception as e:
        logging.warning('bitnodes_history error: %s', e)
        stale = _bitnodes_history_cache.get('data')
        if stale:
            resp = make_response(jsonify(stale))
            resp.headers['X-Cache'] = 'STALE'
            return resp
        return jsonify({'error': 'Bitnodes unavailable', 'history': []}), 503


@app.route('/nodes')
def nodes_page():
    """Bitcoin network node count monitor page."""
    try:
        latest = models.NodeSnapshot.query.order_by(
            models.NodeSnapshot.timestamp.desc()
        ).first()
        node_count = latest.node_count if latest else None
    except Exception as e:
        logging.warning('nodes_page DB error: %s', e)
        node_count = None

    return render_template('nodes.html', node_count=node_count)


# =============================================================================
# SESSION 1 — PULSE TERMINAL  (Bloomberg-style, free + $29/mo Commander)
# =============================================================================

import time as _t
import hashlib as _hashlib

# ── Per-IP rate-limit for free API endpoints (60 req/hr) ─────────────────────
_terminal_free_rl: dict = {}   # {ip: [count, window_start]}
_TERMINAL_FREE_LIMIT = 60
_TERMINAL_FREE_WINDOW = 3600   # 1 hour

def _terminal_free_rate_ok(ip: str) -> bool:
    now = _t.time()
    rec = _terminal_free_rl.get(ip)
    if rec is None or now - rec[1] >= _TERMINAL_FREE_WINDOW:
        _terminal_free_rl[ip] = [1, now]
        return True
    if rec[0] >= _TERMINAL_FREE_LIMIT:
        return False
    rec[0] += 1
    return True

# ── Commander bearer-key authentication ───────────────────────────────────────
def _commander_required():
    """
    Check for Commander access via:
      1. Flask session (logged-in user with commander/sovereign tier), OR
      2. Bearer API key matching an active ApiSubscriber row.
    Returns (ok: bool, error_response | None, subscriber_info: dict | None).
    """
    # Option 1: session user
    if current_user.is_authenticated:
        tier = getattr(current_user, 'subscription_tier', 'free')
        if tier in ('commander', 'sovereign'):
            return True, None, {"tier": tier, "source": "session"}
    # Option 2: Bearer API key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        key = auth[7:].strip()
        try:
            sub = models.ApiSubscriber.query.filter_by(api_key=key).first()
            if sub and sub.is_key_valid():
                return True, None, {"tier": sub.tier, "source": "api_key", "email": sub.email}
        except Exception as _e:
            logging.warning("ApiSubscriber lookup error: %s", _e)
    return False, (jsonify({"error": "Commander access required. Pass Bearer API key or log in."}), 401), None

# ── In-memory cache for free endpoints ───────────────────────────────────────
_term_cache: dict = {}

def _term_cached(key: str, ttl: int, fn):
    """Simple TTL cache for terminal free endpoints."""
    now = _t.time()
    rec = _term_cache.get(key)
    if rec and now < rec[1]:
        return rec[0]
    result = fn()
    _term_cache[key] = (result, now + ttl)
    return result

# ── Helper: BTC price from CoinGecko ─────────────────────────────────────────
def _fetch_btc_price_detail() -> dict:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={"localization": "false", "tickers": "false",
                    "community_data": "false", "developer_data": "false"},
            timeout=8, headers={"Accept": "application/json"},
        )
        d = r.json()
        md = d.get("market_data", {})
        def g(field, key="usd", default=None):
            v = md.get(field, {})
            return v.get(key) if isinstance(v, dict) else v or default
        price = g("current_price") or 0
        change_24h = g("price_change_percentage_24h") or 0
        change_7d  = g("price_change_percentage_7d") or 0
        change_30d = g("price_change_percentage_30d") or 0
        high_24h   = g("high_24h") or 0
        low_24h    = g("low_24h") or 0
        mktcap     = g("market_cap") or 0
        dom        = d.get("market_cap_percentage", {}).get("btc") or 0
        change_usd_24h = price * change_24h / 100
        return {
            "price": round(price, 2),
            "change_24h_pct": round(change_24h, 2),
            "change_24h_usd": round(change_usd_24h, 2),
            "change_7d_pct":  round(change_7d, 2),
            "change_30d_pct": round(change_30d, 2),
            "high_24h": round(high_24h, 2),
            "low_24h":  round(low_24h, 2),
            "market_cap": mktcap,
            "dominance":  round(dom, 1),
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("btc_price fetch error: %s", e)
        return {"price": 0, "change_24h_pct": 0, "change_24h_usd": 0,
                "change_7d_pct": 0, "change_30d_pct": 0, "high_24h": 0,
                "low_24h": 0, "market_cap": 0, "dominance": 0,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_mempool() -> dict:
    try:
        r1 = requests.get("https://mempool.space/api/mempool", timeout=6)
        r2 = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=6)
        m = r1.json(); f = r2.json()
        return {
            "count": m.get("count", 0),
            "vsize": m.get("vsize", 0),
            "total_fee": m.get("total_fee", 0),
            "fee_no_priority":  f.get("minimumFee", 1),
            "fee_low":          f.get("economyFee", 3),
            "fee_medium":       f.get("hourFee", 10),
            "fee_high":         f.get("fastestFee", 25),
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("mempool fetch error: %s", e)
        return {"count": 0, "vsize": 0, "total_fee": 0,
                "fee_no_priority": 1, "fee_low": 3, "fee_medium": 10, "fee_high": 25,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_fear_greed() -> dict:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=4", timeout=8)
        data = r.json().get("data", [])
        def val(i): return int(data[i]["value"]) if i < len(data) else 50
        def cls(i): return data[i].get("value_classification", "") if i < len(data) else ""
        today = val(0)
        return {
            "today": today,
            "today_class": cls(0),
            "yesterday": val(1),
            "last_week": val(6) if len(data) > 6 else val(min(len(data)-1, 2)),
            "last_month": val(min(len(data)-1, 3)),
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("fear_greed fetch error: %s", e)
        return {"today": 50, "today_class": "Neutral", "yesterday": 50,
                "last_week": 50, "last_month": 50,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_macro() -> dict:
    try:
        # Use public Yahoo Finance-compatible quotes via a free proxy
        symbols = {"DXY": "DX-Y.NYB", "GOLD": "GC=F", "SP500": "^GSPC"}
        out = {}
        for name, sym in symbols.items():
            try:
                r = requests.get(
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                    params={"interval": "1d", "range": "2d"},
                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                    timeout=8,
                )
                result = r.json().get("chart", {}).get("result", [{}])[0]
                meta = result.get("meta", {})
                price = meta.get("regularMarketPrice", 0)
                prev  = meta.get("previousClose") or meta.get("chartPreviousClose") or price
                chg   = ((price - prev) / prev * 100) if prev else 0
                out[name] = {"price": round(price, 2), "change_pct": round(chg, 2)}
            except Exception:
                out[name] = {"price": 0, "change_pct": 0}
        # BTC/gold and BTC/sp500 ratios need BTC price
        btc = _term_cache.get("btc_price", ({"price": 0},))[0].get("price", 0)
        gold = out.get("GOLD", {}).get("price", 1) or 1
        sp   = out.get("SP500", {}).get("price", 1) or 1
        out["BTC_GOLD_RATIO"]  = round(btc / gold, 2) if gold else 0
        out["BTC_SP500_RATIO"] = round(btc / sp, 2) if sp else 0
        out["ts"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return out
    except Exception as e:
        logging.warning("macro fetch error: %s", e)
        return {"DXY": {"price": 0, "change_pct": 0}, "GOLD": {"price": 0, "change_pct": 0},
                "SP500": {"price": 0, "change_pct": 0}, "BTC_GOLD_RATIO": 0, "BTC_SP500_RATIO": 0,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_onchain() -> dict:
    try:
        hr = requests.get("https://mempool.space/api/v1/mining/hashrate/1w", timeout=8)
        hdata = hr.json()
        rates = hdata.get("hashrates", [])
        diff_data = hdata.get("difficulty", [])
        hashrate = rates[-1].get("avgHashrate", 0) if rates else 0
        difficulty = diff_data[-1].get("difficulty", 0) if diff_data else 0
        # Next difficulty adjustment
        adj = requests.get("https://mempool.space/api/v1/difficulty-adjustment", timeout=6)
        adj_data = adj.json()
        est_pct = adj_data.get("difficultyChange", 0)
        remain_blocks = adj_data.get("remainingBlocks", 0)
        remain_time = adj_data.get("remainingTime", 0)  # seconds
        # Block tip
        tip = requests.get("https://mempool.space/api/blocks/tip/height", timeout=5)
        block_height = int(tip.text.strip()) if tip.text.strip().isdigit() else 0
        # Exchange flows — use coingecko market data as proxy
        ehr = hashrate / 1e18 if hashrate else 0  # convert to EH/s
        diff_t = difficulty / 1e12 if difficulty else 0  # convert to T
        return {
            "hashrate_ehs": round(ehr, 2),
            "difficulty_t": round(diff_t, 2),
            "next_adj_pct": round(est_pct, 2),
            "remain_blocks": remain_blocks,
            "remain_time_s": remain_time,
            "block_height": block_height,
            "mvrv": 2.14,        # placeholder — no free on-chain API
            "realized_price": 35000,   # placeholder
            "s2f_ratio": 56,     # post-halving BTC S2F ≈ 56
            "s2f_model_price": 98000,
            "exchange_inflow": 1240,   # placeholder BTC/day
            "exchange_outflow": 1890,  # placeholder BTC/day
            "exchange_net": -650,
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("onchain fetch error: %s", e)
        return {"hashrate_ehs": 0, "difficulty_t": 0, "next_adj_pct": 0,
                "remain_blocks": 0, "remain_time_s": 0, "block_height": 0,
                "mvrv": 2.14, "realized_price": 35000, "s2f_ratio": 56,
                "s2f_model_price": 98000, "exchange_inflow": 1240,
                "exchange_outflow": 1890, "exchange_net": -650,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_lightning() -> dict:
    try:
        r = requests.get("https://mempool.space/api/v1/lightning/statistics/latest", timeout=8)
        d = r.json()
        return {
            "node_count": d.get("node_count", 0),
            "channel_count": d.get("channel_count", 0),
            "total_capacity": d.get("total_capacity", 0),  # sats
            "avg_capacity": d.get("avg_capacity", 0),
            "avg_fee_rate": d.get("avg_fee_rate", 0),
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("lightning fetch error: %s", e)
        return {"node_count": 0, "channel_count": 0, "total_capacity": 0,
                "avg_capacity": 0, "avg_fee_rate": 0,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_topics() -> dict:
    """Trending topics ranked by article velocity (last 2h)."""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=2)
        arts = (models.Article.query
                .filter(models.Article.created_at >= cutoff,
                        models.Article.published == True)
                .all())
        tag_counts: dict = {}
        for a in arts:
            tags_raw = (a.tags or "").split(",")
            for t in tags_raw:
                t = t.strip().upper()
                if t and len(t) > 2:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
        # Also count categories
        cat_counts: dict = {}
        for a in arts:
            cat = (a.category or "BITCOIN").upper()
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        topics = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if not topics:
            topics = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "topics": [{"term": t, "count": c} for t, c in topics],
            "total_articles": len(arts),
            "sources_monitored": 80,
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("topics fetch error: %s", e)
        return {"topics": [], "total_articles": 0, "sources_monitored": 80,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}

def _fetch_alerts() -> list:
    """Early warning alerts from recent high-importance articles."""
    try:
        arts = (models.Article.query
                .filter(models.Article.published == True)
                .order_by(models.Article.created_at.desc())
                .limit(20)
                .all())
        out = []
        for a in arts:
            tags = (a.tags or "").lower()
            is_alert = any(kw in tags or kw in (a.category or "").lower()
                           for kw in ["breaking", "urgent", "alert", "crash", "dump", "pump", "rally"])
            out.append({
                "time": a.created_at.strftime("%H:%M") if a.created_at else "—",
                "title": a.title[:80] if a.title else "",
                "url": f"/articles/{a.id}",
                "is_alert": is_alert,
            })
        return out
    except Exception as e:
        logging.warning("alerts fetch error: %s", e)
        return []

# ── Free endpoints ────────────────────────────────────────────────────────────

@app.route("/api/v2/terminal/price")
def api_v2_terminal_price():
    """BTC price, 24h/7d/30d change, market cap, dominance. Cached 30s."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("btc_price", 30, _fetch_btc_price_detail)
    return jsonify(data)


@app.route("/api/v2/terminal/mempool")
def api_v2_terminal_mempool():
    """Mempool stats + fee tiers. Cached 30s."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("mempool", 30, _fetch_mempool)
    return jsonify(data)


@app.route("/api/v2/terminal/fear-greed")
def api_v2_terminal_fear_greed():
    """Fear & Greed index today/yesterday/week/month. Cached 15min."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("fear_greed", 900, _fetch_fear_greed)
    return jsonify(data)


@app.route("/api/v2/terminal/latest")
def api_v2_terminal_latest():
    """Last 5 PP articles. Cached 60s."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    def _fetch():
        try:
            arts = (models.Article.query
                    .filter_by(published=True)
                    .order_by(models.Article.created_at.desc())
                    .limit(5).all())
            total = models.Article.query.filter_by(published=True).count()
            return {
                "articles": [{
                    "title": a.title,
                    "time": a.created_at.strftime("%H:%M") if a.created_at else "—",
                    "slug": f"/articles/{a.id}",
                    "category": a.category or "bitcoin",
                } for a in arts],
                "total": total,
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        except Exception as e:
            return {"articles": [], "total": 0, "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)}
    data = _term_cached("latest_articles", 60, _fetch)
    return jsonify(data)


@app.route("/api/v2/terminal/macro")
def api_v2_terminal_macro():
    """DXY, Gold, S&P 500 + BTC ratios. Cached 60min."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("macro", 3600, _fetch_macro)
    return jsonify(data)

# ── Commander endpoints ───────────────────────────────────────────────────────

@app.route("/api/v2/terminal/signal")
def api_v2_terminal_signal():
    """PP Signal Intelligence composite score. Commander only."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    from services.signal_engine import compute_signal_score
    data = compute_signal_score(db=db, models=models)
    return jsonify(data)


@app.route("/api/v2/terminal/topics")
def api_v2_terminal_topics():
    """Trending topics ranked by velocity (last 2h). Commander only."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    data = _term_cached("topics", 300, _fetch_topics)
    return jsonify(data)


@app.route("/api/v2/terminal/alerts")
def api_v2_terminal_alerts():
    """Early warning alert feed (last 20 articles). Commander only."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    def _fetch():
        return {"alerts": _fetch_alerts(), "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    data = _term_cached("alerts", 30, _fetch)
    return jsonify(data)


@app.route("/api/v2/terminal/onchain")
def api_v2_terminal_onchain():
    """MVRV, S2F, hashrate, difficulty, exchange flows. Commander only. Cached 5min."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    data = _term_cached("onchain", 300, _fetch_onchain)
    return jsonify(data)


@app.route("/api/v2/terminal/lightning")
def api_v2_terminal_lightning():
    """Lightning Network nodes, channels, capacity. Commander only. Cached 10min."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    data = _term_cached("lightning", 600, _fetch_lightning)
    return jsonify(data)

# ── API key management ────────────────────────────────────────────────────────

@app.route("/api/v2/terminal/keys", methods=["GET", "POST"])
@login_required
def api_v2_terminal_keys():
    """GET: list keys. POST: generate new key. Requires active Commander subscription."""
    tier = getattr(current_user, "subscription_tier", "free")
    if tier not in ("commander", "sovereign"):
        return jsonify({"error": "Commander tier required"}), 403

    if request.method == "POST":
        from services.api_key_service import generate_api_key
        try:
            existing = models.ApiSubscriber.query.filter_by(
                email=current_user.email).first()
            new_key = generate_api_key(tier)
            if existing:
                existing.api_key = new_key
                existing.is_active = True
                existing.subscription_status = "active"
            else:
                sub = models.ApiSubscriber(
                    email=current_user.email,
                    api_key=new_key,
                    tier=tier,
                    is_active=True,
                    subscription_status="active",
                    rate_limit_per_hour=10000,
                    entitlements='{"signal":true,"stream":true,"webhook":true}',
                    key_scopes='["read","stream","webhook"]',
                )
                db.session.add(sub)
            db.session.commit()
            return jsonify({"api_key": new_key, "tier": tier,
                            "note": "Store this key securely. Shown once."})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # GET — list keys
    try:
        subs = models.ApiSubscriber.query.filter_by(email=current_user.email).all()
        return jsonify({"keys": [{"key_prefix": s.api_key[:16] + "...",
                                   "tier": s.tier, "active": s.is_active,
                                   "created": s.created_at.isoformat() if s.created_at else None}
                                  for s in subs]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v2/terminal/keys/<key_prefix>", methods=["DELETE"])
@login_required
def api_v2_terminal_keys_delete(key_prefix):
    """Revoke an API key by prefix."""
    tier = getattr(current_user, "subscription_tier", "free")
    if tier not in ("commander", "sovereign"):
        return jsonify({"error": "Commander tier required"}), 403
    try:
        subs = models.ApiSubscriber.query.filter_by(email=current_user.email).all()
        for s in subs:
            if s.api_key.startswith(key_prefix.replace("...", "")):
                s.is_active = False
                db.session.commit()
                return jsonify({"revoked": True})
        return jsonify({"error": "Key not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ── Terminal page routes ──────────────────────────────────────────────────────

@app.route("/terminal")
def pulse_terminal():
    """PP Terminal — Bloomberg-style Bitcoin intelligence dashboard."""
    is_commander = (current_user.is_authenticated and
                    getattr(current_user, "subscription_tier", "free")
                    in ("commander", "sovereign"))
    activated = request.args.get("activated") == "1"

    # Server-side pre-fetch for initial render (both free + Commander panels)
    price_data    = _term_cached("btc_price", 30, _fetch_btc_price_detail)
    mempool_data  = _term_cached("mempool", 30, _fetch_mempool)
    fg_data       = _term_cached("fear_greed", 900, _fetch_fear_greed)
    onchain_data  = _term_cached("onchain", 300, _fetch_onchain)
    lightning_data = _term_cached("lightning", 600, _fetch_lightning)
    macro_data    = _term_cached("macro", 3600, _fetch_macro)

    # Signal score — always compute for locked panel real-data blur
    from services.signal_engine import compute_signal_score
    signal_data = compute_signal_score(db=db, models=models)

    # Topics + alerts for locked panels
    topics_data = _term_cached("topics", 300, _fetch_topics)
    alerts_data = _fetch_alerts()

    # Latest articles
    def _latest():
        try:
            arts = (models.Article.query.filter_by(published=True)
                    .order_by(models.Article.created_at.desc()).limit(5).all())
            total = models.Article.query.filter_by(published=True).count()
            return {"articles": [{
                "title": a.title, "time": a.created_at.strftime("%H:%M") if a.created_at else "—",
                "slug": f"/articles/{a.id}", "category": a.category or "bitcoin",
            } for a in arts], "total": total}
        except Exception:
            return {"articles": [], "total": 0}
    latest_data = _term_cached("latest_articles", 60, _latest)

    # API key for Commander welcome banner
    api_key = None
    if activated and is_commander:
        try:
            sub = models.ApiSubscriber.query.filter_by(
                email=current_user.email).first()
            if sub:
                api_key = sub.api_key
        except Exception:
            pass

    return render_template(
        "signal_terminal.html",
        is_commander=is_commander,
        activated=activated,
        api_key=api_key,
        price=price_data,
        mempool=mempool_data,
        fg=fg_data,
        onchain=onchain_data,
        lightning=lightning_data,
        macro=macro_data,
        signal=signal_data,
        topics=topics_data,
        alerts=alerts_data,
        latest=latest_data,
    )


@app.route("/terminal/commander")
def terminal_commander_page():
    """Commander upgrade page — redirects to Stripe checkout."""
    return redirect(url_for("terminal_checkout"))


@app.route("/terminal/checkout")
@login_required
def terminal_checkout():
    """Initiate Stripe checkout for $29/mo Commander tier."""
    from services.monetization_service import monetization_service
    success_url = request.host_url.rstrip("/") + "/terminal?activated=1"
    cancel_url  = request.host_url.rstrip("/") + "/terminal"
    result = monetization_service.create_checkout_session(
        tier="commander",
        user_email=current_user.email,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    if result.get("simulated"):
        # Dev mode: simulate success — upgrade tier directly
        current_user.subscription_tier = "commander"
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return redirect(url_for("pulse_terminal", activated=1))
    if result.get("checkout_url"):
        return redirect(result["checkout_url"])
    flash("Unable to start checkout. Please try again.")
    return redirect(url_for("pulse_terminal"))


@app.route("/terminal/account")
@login_required
def terminal_account():
    """Show Commander API key and account status."""
    is_commander = getattr(current_user, "subscription_tier", "free") in ("commander", "sovereign")
    if not is_commander:
        return redirect(url_for("pulse_terminal"))
    try:
        sub = models.ApiSubscriber.query.filter_by(email=current_user.email).first()
    except Exception:
        sub = None
    return render_template("terminal_account.html", sub=sub)


# ── N17 Global FTS5 Search ───────────────────────────────────────────────────

@app.route('/search')
def search_page():
    """Full-text search page with FTS5."""
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 20, type=int), 50)
    offset = (page - 1) * limit

    results = []
    total = 0

    if q:
        try:
            raw = db.engine.raw_connection()
            cur = raw.cursor()
            # Sanitize query for FTS5 (escape double quotes, wrap terms)
            safe_q = q.replace('"', '""')
            fts_query = ' '.join(f'"{w}"' for w in safe_q.split() if w)

            # Count total
            count_sql = """
                SELECT count(*) FROM articles
                JOIN articles_fts ON articles.id = articles_fts.rowid
                WHERE articles_fts MATCH ?
            """
            count_params = [fts_query]
            if category:
                count_sql += " AND articles.category = ?"
                count_params.append(category)

            total = cur.execute(count_sql, count_params).fetchone()[0]

            # Fetch results with highlights
            search_sql = """
                SELECT articles.id, articles.title, articles.category,
                       articles.created_at, articles.header_image_url,
                       highlight(articles_fts, 1, '<mark>', '</mark>') as snippet,
                       rank
                FROM articles
                JOIN articles_fts ON articles.id = articles_fts.rowid
                WHERE articles_fts MATCH ?
            """
            search_params = [fts_query]
            if category:
                search_sql += " AND articles.category = ?"
                search_params.append(category)
            search_sql += " ORDER BY rank LIMIT ? OFFSET ?"
            search_params.extend([limit, offset])

            rows = cur.execute(search_sql, search_params).fetchall()
            for r in rows:
                snippet = r[5] or ''
                # Trim snippet to ~150 chars while keeping highlight tags
                plain_len = len(re.sub(r'</?mark>', '', snippet))
                if plain_len > 150:
                    # Truncate but keep mark tags
                    snippet = snippet[:200].rsplit(' ', 1)[0] + '...'
                results.append({
                    'id': r[0], 'title': r[1], 'category': r[2],
                    'published_at': r[3], 'header_image_url': r[4],
                    'snippet': snippet, 'score': r[6],
                })
            raw.close()
        except Exception as e:
            logging.error(f"Search error: {e}")

    return render_template('search.html', results=results, query=q,
                           total=total, page=page, limit=limit, category=category)


@app.route('/api/search')
def api_search():
    """JSON search API for typeahead."""
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    limit = min(request.args.get('limit', 10, type=int), 50)
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * limit

    if not q or len(q) < 2:
        return jsonify([])

    try:
        raw = db.engine.raw_connection()
        cur = raw.cursor()
        safe_q = q.replace('"', '""')
        fts_query = ' '.join(f'"{w}"' for w in safe_q.split() if w)

        sql = """
            SELECT articles.id, articles.title, articles.category,
                   articles.created_at,
                   highlight(articles_fts, 1, '<mark>', '</mark>') as snippet,
                   rank
            FROM articles
            JOIN articles_fts ON articles.id = articles_fts.rowid
            WHERE articles_fts MATCH ?
        """
        params = [fts_query]
        if category:
            sql += " AND articles.category = ?"
            params.append(category)
        sql += " ORDER BY rank LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = cur.execute(sql, params).fetchall()
        results = []
        for r in rows:
            snippet = r[4] or ''
            plain_len = len(re.sub(r'</?mark>', '', snippet))
            if plain_len > 150:
                snippet = snippet[:200].rsplit(' ', 1)[0] + '...'
            results.append({
                'id': r[0], 'title': r[1], 'category': r[2],
                'published_at': r[3], 'snippet': snippet, 'score': r[5],
            })
        raw.close()
        return jsonify(results)
    except Exception as e:
        logging.error(f"API search error: {e}")
        return jsonify([])


# ── STAGE BRIEF STATIC FILES ──────────────────────────────────────────────

@app.route('/data/stage_briefs/<path:filename>')
def serve_stage_brief(filename):
    """Serve stage brief MP4 and JSON files."""
    from flask import send_from_directory
    brief_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'video_pipeline_v3', 'data', 'stage_briefs')
    return send_from_directory(brief_dir, filename)


# ── STAGE BROADCAST ROUTES ──────────────────────────────────────────────────

@app.route('/api/stage/broadcast-queue')
@limiter.limit("30 per minute")
def api_stage_broadcast_queue():
    """Return next 3 items from broadcast queue sorted by priority."""
    import json as _j
    from pathlib import Path
    from datetime import datetime as _dt, timezone as _tz

    queue_path = Path(__file__).resolve().parent.parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
    try:
        if not queue_path.exists():
            return jsonify({'items': [], 'queue_depth': 0, 'session_start': _dt.now(_tz.utc).isoformat()})

        items = _j.loads(queue_path.read_text())
        if not isinstance(items, list):
            items = []

        # Filter expired
        now = _dt.now(_tz.utc)
        valid = []
        for item in items:
            try:
                expires = _dt.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
                if expires > now:
                    valid.append(item)
            except (KeyError, ValueError):
                continue

        valid.sort(key=lambda x: x.get('priority', 5))
        return jsonify({
            'items': valid[:3],
            'queue_depth': len(valid),
            'session_start': now.isoformat(),
        })
    except Exception as e:
        logging.warning('broadcast-queue error: %s', e)
        return jsonify({'items': [], 'queue_depth': 0, 'session_start': _dt.now(_tz.utc).isoformat()})


@app.route('/api/stage/consume-broadcast', methods=['POST'])
@limiter.limit("30 per minute")
def api_stage_consume_broadcast():
    """Atomically remove consumed item (file lock), return next item."""
    import json as _j, fcntl
    from pathlib import Path
    from datetime import datetime as _dt, timezone as _tz

    queue_path = Path(__file__).resolve().parent.parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
    data = request.get_json(silent=True) or {}
    consumed_id = data.get('consumed_id')

    try:
        queue_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic read-modify-write with file lock
        items = []
        if queue_path.exists():
            with open(queue_path, 'r+') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    items = _j.load(f)
                except _j.JSONDecodeError:
                    items = []

                # Remove consumed item
                if consumed_id:
                    items = [i for i in items if i.get('id') != consumed_id]

                # Filter expired
                now = _dt.now(_tz.utc)
                valid = []
                for item in items:
                    try:
                        expires = _dt.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
                        if expires > now:
                            valid.append(item)
                    except (KeyError, ValueError):
                        continue

                valid.sort(key=lambda x: x.get('priority', 5))

                # Write back
                f.seek(0)
                f.truncate()
                _j.dump(valid, f, indent=2)
                fcntl.flock(f, fcntl.LOCK_UN)
        else:
            valid = []

        next_item = valid[0] if valid else None

        # If queue empty, generate filler
        if not next_item:
            try:
                from services.stage_broadcast_service import generate_filler_live
                next_item = generate_filler_live()
            except Exception as e:
                logging.warning('filler generation failed: %s', e)

        # Attach video_url from latest brief if not already present
        if next_item and not next_item.get('video_url'):
            try:
                latest_path = queue_path.parent / 'latest.json'
                if latest_path.exists():
                    latest = _j.loads(latest_path.read_text())
                    video_url = latest.get('video_url') or latest.get('mp4_url', '')
                    if video_url:
                        next_item['video_url'] = video_url
            except Exception:
                pass

        return jsonify({
            'next_item': next_item,
            'queue_depth': len(valid),
        })
    except Exception as e:
        logging.warning('consume-broadcast error: %s', e)
        return jsonify({'next_item': None, 'queue_depth': 0})


@app.route('/api/stage/broadcast-status')
@limiter.limit("30 per minute")
def api_stage_broadcast_status():
    """Return broadcast status: live state, current topic, queue depth."""
    import json as _j
    from pathlib import Path
    from datetime import datetime as _dt, timezone as _tz

    queue_path = Path(__file__).resolve().parent.parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
    try:
        items = []
        if queue_path.exists():
            items = _j.loads(queue_path.read_text())
            if not isinstance(items, list):
                items = []

        # Filter expired
        now = _dt.now(_tz.utc)
        valid = []
        for item in items:
            try:
                expires = _dt.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
                if expires > now:
                    valid.append(item)
            except (KeyError, ValueError):
                continue

        valid.sort(key=lambda x: x.get('priority', 5))
        current = valid[0]['topic_preview'] if valid else 'Standing by'
        next_topic = valid[1]['topic_preview'] if len(valid) > 1 else None

        return jsonify({
            'live': True,
            'current_topic': current,
            'queue_depth': len(valid),
            'next_topic': next_topic,
        })
    except Exception as e:
        logging.warning('broadcast-status error: %s', e)
        return jsonify({'live': True, 'current_topic': 'Standing by', 'queue_depth': 0, 'next_topic': None})


# ── RATE LIMITING FOR ORACLE ENDPOINTS (P0.1 audit fix) ─────────────────────

@app.route('/api/oracle/chat', methods=['POST'])
@limiter.limit("6 per minute")
def api_oracle_chat_ratelimited():
    """Rate-limited proxy for oracle chat — prevents denial-of-wallet attacks."""
    import requests as _req
    avatar_base = os.environ.get('AVATAR_BASE_URL', 'http://localhost:8200')
    try:
        body = request.get_json(silent=True) or {}
        resp = _req.post(
            f'{avatar_base}/oracle/chat',
            json=body,
            timeout=90,
            headers={'Content-Type': 'application/json'},
        )
        # Forward response as-is
        excluded_headers = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
        headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
        return Response(resp.content, status=resp.status_code, headers=headers,
                        content_type=resp.headers.get('content-type', 'application/json'))
    except Exception as e:
        logging.warning('oracle chat proxy error: %s', e)
        return jsonify({'error': 'Oracle unavailable'}), 503


@app.route('/api/oracle/speak', methods=['POST'])
@limiter.limit("3 per minute")
def api_oracle_speak_ratelimited():
    """Rate-limited proxy for oracle speak — prevents denial-of-wallet attacks."""
    import requests as _req
    avatar_base = os.environ.get('AVATAR_BASE_URL', 'http://localhost:8200')
    try:
        body = request.get_json(silent=True) or {}
        resp = _req.post(
            f'{avatar_base}/oracle/speak',
            json=body,
            timeout=60,
            headers={'Content-Type': 'application/json'},
        )
        excluded_headers = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
        headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
        return Response(resp.content, status=resp.status_code, headers=headers,
                        content_type=resp.headers.get('content-type', 'application/octet-stream'))
    except Exception as e:
        logging.warning('oracle speak proxy error: %s', e)
        return jsonify({'error': 'Oracle unavailable'}), 503


@app.route('/api/oracle/query', methods=['POST'])
@limiter.limit("10 per minute")
def api_oracle_query():
    """Lightweight stage interrupt — Claude Haiku answers with live BTC context."""
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '')[:200]
    context = (data.get('context') or 'Bitcoin')[:200]
    broadcast_script = (data.get('broadcast_script') or '')[:600]

    if not query.strip():
        return jsonify({'response': 'I did not catch that. Stay sovereign.'}), 200

    try:
        import anthropic
        client = anthropic.Anthropic()

        # Fetch live BTC price for context
        btc_price = 'unknown'
        try:
            import requests as _rq
            r = _rq.get('https://api.coinbase.com/v2/prices/BTC-USD/spot', timeout=3)
            if r.ok:
                btc_price = '$' + r.json()['data']['amount']
        except Exception:
            pass

        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=150,
            messages=[{
                'role': 'user',
                'content': (
                    'You are Satomi, Protocol Pulse\'s live Bitcoin intelligence anchor. '
                    f'Current BTC price: {btc_price}. '
                    'BROADCAST CONTEXT: You are mid-broadcast. '
                    f'Current topic: {context}. '
                    f'Current broadcast script excerpt: {broadcast_script[:400] if broadcast_script else "not available"}. '
                    'INSTRUCTIONS: '
                    '1. If the question relates to what you are currently broadcasting about, answer in that context - frame your response as a natural continuation of the conversation. '
                    '2. If the question is unrelated to the broadcast topic, answer it fresh as a standalone Bitcoin intelligence query. '
                    '3. Always: 1-2 concise sentences max (under 180 chars), direct, insightful, stay in character. '
                    '4. Never say you are an AI or that you are searching - just answer as Satomi would. '
                    f'User asked: {query}'
                )
            }]
        )
        response_text = msg.content[0].text.strip()
        return jsonify({'response': response_text})
    except Exception as e:
        logging.warning('oracle query error: %s', e)
        return jsonify({'response': f'Signal unclear. Current context: {context}. Stay sovereign.'}), 200


# ─── Missing route aliases (cc_site_fixes.md) ───

@app.route('/oracle-live')
def oracle_live():
    return render_template('oracle_live.html')

@app.route('/intel')
def intel_redirect():
    return redirect('/intelligence/legacy', code=301)

@app.route('/briefings')
def briefings_redirect():
    return redirect('/briefing', code=301)

@app.route('/markets')
def markets_redirect():
    return redirect('/charts', code=301)

@app.route('/podcast')
def podcast_redirect():
    return redirect('/podcasts', code=301)


# ─── Satomi Voice / SMS (Twilio webhooks) ───────────────────────────────────

@app.route('/api/satomi/voice', methods=['POST', 'GET'])
def satomi_voice_incoming():
    """Twilio webhook: handles incoming calls to our number. Set this URL in Twilio console."""
    try:
        from services.satomi_voice import generate_incoming_twiml
        # Get latest brief from stage broadcast queue
        brief_text = None
        try:
            queue_path = '/home/ultron/protocol_pulse/video_pipeline_v3/data/stage_briefs/broadcast_queue.json'
            with open(queue_path) as f:
                queue = json.load(f)
            if queue:
                for item in queue:
                    if item.get('type') not in ('FILLER_INSIGHT',) and item.get('script'):
                        brief_text = item['script']
                        break
                if not brief_text and queue[0].get('script'):
                    brief_text = queue[0]['script']
        except Exception:
            pass

        twiml = generate_incoming_twiml(brief_text)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        logging.error(f'satomi_voice_incoming error: {e}')
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Signal unavailable. Stay sovereign.", voice='Polly.Joanna')
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/voice/choice', methods=['POST'])
def satomi_voice_choice():
    """Handles menu digit press from incoming call."""
    try:
        from services.satomi_voice import generate_choice_twiml
        from twilio.twiml.voice_response import VoiceResponse
        digit = request.form.get('Digits', '')
        # Fetch live brief text from oracle feed
        brief_text = ''
        market_summary = ''
        try:
            import sys; sys.path.insert(0, '/home/ultron/protocol_pulse/oracle')
            from oracle_intelligence_feed import _get_btc_price, _get_recent_articles, _get_pipeline_sentiment, _generate_briefing_text
            pf, ps = _get_btc_price()
            arts = _get_recent_articles(3)
            sent = _get_pipeline_sentiment()
            brief_text = _generate_briefing_text(arts, sent, pf, ps) or f"Bitcoin is at {ps}. Network fundamentals remain strong. Stay sovereign."
            market_summary = f"Bitcoin currently at {ps}. Sentiment indicators show mixed signals across institutional and retail flows. Key level to watch."
        except Exception as bex:
            brief_text = "Protocol Pulse intelligence signal active. Stay sovereign."
            market_summary = "Market data loading. Stay sovereign."
        twiml = generate_choice_twiml(digit, brief_text, market_summary)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Intelligence signal complete. Stay sovereign.", voice='Polly.Joanna-Neural')
        return Response(str(resp), mimetype='text/xml')



@app.route('/api/satomi/tts')
def satomi_tts_audio():
    """Serve Satomi's Kokoro voice as audio for Twilio <Play> tag."""
    import subprocess, tempfile, hashlib
    text = request.args.get('text', 'Protocol Pulse intelligence signal.')[:600]
    # Try Kokoro first (same voice as oracle), fall back to ElevenLabs
    try:
        import sys
        sys.path.insert(0, '/home/ultron/protocol_pulse/oracle')
        from avatar_server import _avatar_tts
        audio_bytes = _avatar_tts(text)
        if audio_bytes and len(audio_bytes) > 1000:
            import io
            from flask import send_file
            return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav',
                           as_attachment=False, download_name='satomi.wav')
    except Exception as e:
        logging.warning(f'[SatomiTTS] Kokoro failed: {e}')
    # ElevenLabs fallback
    try:
        import requests as _req
        xi_key = os.environ.get('ELEVENLABS_API_KEY', '')
        voice_id = os.environ.get('ELEVENLABS_VOICE_ID', 'cgSgspJ2msm6clMCkdW9')
        r = _req.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            headers={'xi-api-key': xi_key, 'Content-Type': 'application/json'},
            json={'text': text, 'model_id': 'eleven_turbo_v2_5',
                  'voice_settings': {'stability': 0.5, 'similarity_boost': 0.8}},
            timeout=15)
        if r.ok:
            import io
            from flask import send_file
            return send_file(io.BytesIO(r.content), mimetype='audio/mpeg',
                           as_attachment=False, download_name='satomi.mp3')
    except Exception as e:
        logging.warning(f'[SatomiTTS] ElevenLabs failed: {e}')
    # Final fallback - empty WAV
    from flask import abort
    abort(503)

@app.route('/api/satomi/voice/outbound-twiml', methods=['POST', 'GET'])
def satomi_voice_outbound_twiml():
    """TwiML served when outbound call is answered by subscriber."""
    try:
        from services.satomi_voice import generate_incoming_twiml
        brief_text = None
        try:
            queue_path = '/home/ultron/protocol_pulse/video_pipeline_v3/data/stage_briefs/broadcast_queue.json'
            with open(queue_path) as f:
                queue = json.load(f)
            if queue and queue[0].get('script'):
                brief_text = queue[0]['script']
        except Exception:
            pass
        twiml = generate_incoming_twiml(brief_text)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Good morning. Satomi here with your Protocol Pulse brief. Stay sovereign.", voice='Polly.Joanna')
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/sms', methods=['POST'])
def satomi_sms_incoming():
    """Twilio webhook: handles incoming SMS."""
    try:
        from services.satomi_voice import handle_incoming_sms
        from_number = request.form.get('From', '')
        body = request.form.get('Body', '')
        twiml = handle_incoming_sms(from_number, body)
        return Response(twiml, mimetype='text/xml')
    except Exception as e:
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message("\u26a1 Satomi: protocolpulse.io")
        return Response(str(resp), mimetype='text/xml')


@app.route('/api/satomi/call-subscribers', methods=['POST'])
def satomi_call_subscribers():
    """Internal endpoint: trigger outbound calls to all opted-in subscribers."""
    token = request.headers.get('X-Internal-Token', '')
    if token != os.environ.get('INTERNAL_API_TOKEN', 'pp-internal-2026'):
        return jsonify({'error': 'unauthorized'}), 403
    try:
        from services.satomi_voice import call_all_opted_in_subscribers
        brief_text = request.json.get('brief_text', 'Satomi here with your Protocol Pulse daily signal.')
        results = call_all_opted_in_subscribers(brief_text)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Promo Codes ─────────────────────────────────────────────────────────────

@app.route('/api/apply-promo', methods=['POST'])
def apply_promo_code():
    """Apply a promo code to unlock premium access for team/testing."""
    code = request.json.get('code', '').strip().upper()

    PROMO_CODES = {
        'SOVEREIGN-TEAM-2026': 'commander',
        'STAY-SOVEREIGN': 'operator',
    }

    tier = PROMO_CODES.get(code)
    if not tier:
        return jsonify({'success': False, 'error': 'Invalid promo code'}), 400

    # Apply to current user if logged in
    if current_user.is_authenticated:
        current_user.subscription_tier = tier
        db.session.commit()
        return jsonify({'success': True, 'tier': tier, 'message': f'Commander access activated. Welcome, Sovereign.'})
    else:
        # Store in session for post-login application
        session['pending_promo_tier'] = tier
        return jsonify({'success': True, 'tier': tier, 'redirect': '/login?promo=1'})


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/v3/<path:fn>')
def _serve_v3(fn):
    """Serve static files under /v3/ path — CSS, JS, assets for new site templates."""
    from flask import make_response, abort
    import mimetypes
    static_root = '/home/ultron/protocol_pulse/static'
    p = os.path.join(static_root, fn)
    safe_p = os.path.realpath(p)
    if not safe_p.startswith(os.path.realpath(static_root) + os.sep):
        abort(403)
    if not os.path.exists(safe_p):
        abort(404)
    data = open(safe_p, 'rb').read()
    resp = make_response(data)
    resp.headers['Content-Type'] = mimetypes.guess_type(safe_p)[0] or 'text/plain'
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp



# ─── STUB ROUTES for broken pages ────────────────────────────────────────────
@app.route('/nostr-signal')
def nostr_signal_redirect():
    from flask import redirect
    return redirect('/nostr')

@app.route('/yield')  
def yield_page():
    return render_template('coming_soon.html', 
        page_title='Yield Intelligence',
        page_desc='Bitcoin yield and income strategies. Coming soon.') if os.path.exists(
        os.path.join(app.template_folder, 'coming_soon.html')) else render_template('base.html')

@app.route('/network-health')
def network_health():
    from flask import redirect
    return redirect('/live')


@app.route('/blocks')
def blocks_page():
    from flask import redirect
    return redirect('/live')


@app.route('/api/v2/categories')
def api_v2_categories():
    """Categories for Next.js articles frontend."""
    try:
        from models import Article
        cats = db.session.query(Article.category, db.func.count(Article.id).label('count'))\
            .filter(Article.published == True, Article.category.isnot(None))\
            .group_by(Article.category).order_by(db.text('count DESC')).limit(20).all()
        return jsonify([{'name': c, 'count': n} for c, n in cats if c])
    except Exception as e:
        logging.warning('api_v2_categories error: %s', e)
        return jsonify([{'name': 'Bitcoin', 'count': 0}])


@app.route('/api/v2/prices')
def api_v2_prices():
    """Live BTC price for Next.js frontend."""
    try:
        import requests as _rq
        r = _rq.get('https://api.coinbase.com/v2/prices/BTC-USD/spot', timeout=4)
        if r.ok:
            price = float(r.json()['data']['amount'])
            return jsonify({'btc_usd': price, 'source': 'coinbase'})
    except Exception:
        pass
    # Fallback to cached price
    try:
        import json as _json
        with open('/home/ultron/protocol_pulse/data/price_cache.json') as f:
            cached = _json.load(f)
        return jsonify({'btc_usd': cached.get('price', 0), 'source': 'cache'})
    except Exception:
        return jsonify({'btc_usd': 0, 'source': 'unavailable'})

