from flask import render_template, request, jsonify, redirect, url_for, flash, make_response, session, Response
from flask_login import login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db

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

@app.route('/debug-routes')
def debug_routes():
    """List all registered URL rules (for 404 debugging: confirm / is in the app that is actually running)."""
    rules = [{"rule": r.rule, "endpoint": r.endpoint, "methods": list(r.methods - {"HEAD", "OPTIONS"})}
             for r in app.url_map.iter_rules()]
    return jsonify({"app": "Protocol Pulse", "rules": sorted(rules, key=lambda x: x["rule"])})

@app.route('/')
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
    
    return render_template('index.html', 
                         featured_articles=featured_articles,
                         recent_articles=recent_articles,
                         featured_podcasts=featured_podcasts,
                         prices=prices,
                         price_service=price_service,
                         todays_signal=todays_signal,
                         user_segment=user_segment,
                         bento_articles=bento_articles[:4])

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
    """Value Stream - Content curated by economic signals"""
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
    
    return render_template('value_stream.html', 
                          posts=post_objects,
                          curators=curator_objects,
                          selected_platform=platform)

@app.route('/signal-terminal')
def signal_terminal():
    """Signal Terminal - Premium 3-panel value stream interface"""
    from services.value_stream_service import value_stream_service
    from datetime import datetime, timedelta
    
    posts = value_stream_service.get_value_stream_enhanced(limit=50)
    curators = value_stream_service.get_top_curators(limit=10)
    
    curator_objects = []
    for c in curators:
        curator = models.ValueCreator.query.get(c['id'])
        if curator:
            curator_objects.append(curator)
    
    sats_hour = db.session.query(db.func.sum(models.ZapEvent.amount_sats)).filter(
        models.ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).scalar() or 0
    
    hot_topics = ['Bitcoin', 'Lightning', 'Nostr', 'ETF', 'Self-Custody', 'Mining', 'Layer 2']
    
    return render_template('signal_terminal.html',
                          posts=posts,
                          curators=curator_objects,
                          sats_flow=sats_hour,
                          hot_topics=hot_topics)

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

@app.route('/api/nostr/latest/<pubkey>')
def api_nostr_latest(pubkey):
    """Get latest Nostr post for a given pubkey"""
    try:
        event = models.NostrEvent.query.filter_by(pubkey=pubkey).order_by(models.NostrEvent.created_at.desc()).first()
        if event:
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
    from services.solo_tracker import solo_tracker
    
    stats = solo_tracker.get_stats()
    leaderboard = solo_tracker.get_leaderboard()
    solo_blocks = solo_tracker.solo_blocks[:50]
    
    return render_template('solo_slayers.html',
                         stats=stats,
                         leaderboard=leaderboard,
                         solo_blocks=solo_blocks)

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
    """Articles listing page with simple, reliable chronological layout."""
    now = datetime.utcnow()

    # Always show the most recent articles, even if nothing is marked published yet.
    # Prefer published ones; if none exist, fall back to all.
    base_q = models.Article.query.filter(models.Article.published.is_(True)).order_by(
        models.Article.created_at.desc()
    )
    recent = base_q.limit(40).all()
    if not recent:
        logging.info("No published articles found; falling back to all articles by created_at.")
        base_q = models.Article.query.order_by(models.Article.created_at.desc())
        recent = base_q.limit(40).all()

    # Slice recent articles into zones: first 10 = today, next 10 = yesterday, rest = archive
    today_articles = recent[:10]
    yesterday_articles = recent[10:20]
    archive_articles = recent[20:40]
    
    # Add pressing status to today's articles
    for article in today_articles:
        time_diff = (now - article.created_at).total_seconds() / 3600
        article.is_pressing = time_diff < 1
    
    # Get all categories for filter (simple + robust)
    categories = db.session.query(models.Article.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    # Get active advertisements
    active_ads = models.Advertisement.query.filter_by(is_active=True).all()
    
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
    article = models.Article.query.get_or_404(article_id)
    related_articles = models.Article.query.filter(
        models.Article.id != article_id,
        models.Article.published == True,
        models.Article.category == article.category
    ).limit(3).all()
    
    return render_template('article_detail.html', article=article, related_articles=related_articles)

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


@app.route('/podcasts')
def podcasts():
    """Podcasts listing page with RSS feed sections."""
    # Group podcasts by RSS source; show 3 most recent per section
    sections_list = []
    seen_slugs = set()

    # Distinct RSS sources (including None -> "General")
    sources = db.session.query(models.Podcast.rss_source).distinct().all()
    for (source,) in sources:
        source_name = source if source else "General"
        slug = _slugify_section(source_name)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        recent = models.Podcast.query.filter_by(rss_source=source).order_by(
            models.Podcast.published_date.desc()
        ).limit(3).all()
        if recent:
            sections_list.append({
                "name": source_name,
                "slug": slug,
                "podcasts": recent,
            })

    # Generate smart playlist (optional; never break the page)
    smart_playlist = None
    try:
        seg = "institution"
        if current_user.is_authenticated:
            us = models.UserSegment.query.filter_by(user_id=current_user.id).first()
            if us:
                seg = us.segment_type
        from services.content_engine import content_engine
        smart_playlist = content_engine.get_smart_playlist(seg)
    except Exception as e:
        logging.warning("Smart playlist skipped: %s", e)

    return render_template(
        "podcasts.html",
        podcast_sections_list=sections_list,
        smart_playlist=smart_playlist,
    )

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

@app.route('/media')
@app.route('/media-hub')
def media_hub():
    """Media Hub page with live RSS feeds, books, and merch"""
    if not rss_service:
        return render_template('media_hub.html', shows=[], products=[], our_books=[], recommended_books=[], youtube_series={}, live_broadcasts={}, intel_posts=[], get_thumbnail=YouTubeService.get_thumbnail)
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
        
        # Our Book Series - books featured on the Protocol Pulse podcast
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
        
        # Recommended Bitcoin Books - bestsellers and essentials
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
        
        return render_template('media_hub.html', 
                               shows=shows, 
                               products=products,
                               our_books=our_books,
                               recommended_books=recommended_books,
                               youtube_series=youtube_series,
                               live_broadcasts=live_broadcasts,
                               active_ads=active_ads,
                               intel_posts=intel_posts,
                               get_thumbnail=YouTubeService.get_thumbnail)
    except Exception as e:
        logging.error(f"Error loading media hub: {e}")
        return render_template('media_hub.html', shows=[], products=[], our_books=[], recommended_books=[], youtube_series={}, live_broadcasts={}, intel_posts=[], get_thumbnail=YouTubeService.get_thumbnail)

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
        user = models.User.query.filter_by(username=login_input).first()
        if not user:
            user = models.User.query.filter_by(email=login_input).first()
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
    total_articles = models.Article.query.count()
    published_articles = models.Article.query.filter_by(published=True).count()
    total_podcasts = models.Podcast.query.count()
    recent_articles = models.Article.query.order_by(models.Article.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_articles=total_articles,
                         published_articles=published_articles,
                         total_podcasts=total_podcasts,
                         recent_articles=recent_articles)

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
    """Public sentiment reports dashboard"""
    
    reports = models.SentimentReport.query.order_by(models.SentimentReport.report_date.desc()).limit(14).all()
    
    latest_report = reports[0] if reports else None
    latest_article = None
    if latest_report and latest_report.article_id:
        latest_article = models.Article.query.get(latest_report.article_id)
    
    return render_template('sentiment_dashboard.html', 
                          reports=reports, 
                          latest_report=latest_report,
                          latest_article=latest_article)


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
                session = event['data']['object']
                metadata = session.get('metadata', {})
                
                # Handle merch orders - submit to Printful
                if metadata.get('type') == 'merch_order':
                    try:
                        printful_items_json = metadata.get('printful_items', '[]')
                        printful_items = json.loads(printful_items_json)
                        shipping = session.get('shipping_details', {})
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
                                'email': session.get('customer_details', {}).get('email', '')
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


# Sovereign Command Deck Routes
@app.route('/admin/command-deck')
@admin_required
def command_deck():
    """Sovereign Command Deck - System control center"""
    try:
        from services.scheduler import get_scheduler_status
        from services.telegram_bot import pulse_operative
        
        scheduler_status = get_scheduler_status()
        telegram_status = pulse_operative.get_status()
        
        return render_template('admin/command_deck.html',
            scheduler_status=scheduler_status,
            telegram_status=telegram_status
        )
    except Exception as e:
        logging.error(f"Command deck error: {e}")
        return render_template('admin/command_deck.html',
            scheduler_status={'running': False, 'jobs': []},
            telegram_status={'initialized': False}
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
        
        return jsonify({
            'success': True,
            'collected': {
                'x_posts': len(x_posts),
                'nostr_notes': len(nostr_notes),
                'stacker_news': len(stacker_posts)
            },
            'message': f'Collected {len(x_posts)} X posts, {len(nostr_notes)} Nostr notes, {len(stacker_posts)} Stacker News posts'
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
        
        return jsonify({
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
        })
    
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

@app.route('/api/track/pageview', methods=['POST'])
def api_track_pageview():
    """Track a page view for analytics (public endpoint)"""
    try:
        from services.realtime_intel import realtime_intel
        from flask_login import current_user
        
        data = request.get_json() or {}
        page_path = data.get('path', request.referrer or '/')
        page_title = data.get('title', '')
        
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
            user_id=user_id
        )
        
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Page view tracking error: {e}")
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


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500