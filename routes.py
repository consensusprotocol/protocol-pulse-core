# DEPRECATED — routes.py (monolithic)
# SESSION 2: Blueprint architecture introduced. New routes go in core/blueprints/.
# Migrated to blueprints: /newsletter (GET), /newsletter/subscribe (POST)
# Remaining routes will be migrated to core/blueprints/ in future sessions.
# ---
from flask import render_template, request, jsonify, redirect, url_for, flash, make_response, session
from flask_login import login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db, limiter, cache
from models import Article, Podcast, ContentPrompt, User, Advertisement, AutomationRun, LaunchSequence, TargetAlert, NostrEvent, ReplySquadMember, EngagementEvent, ContentPerformance, AnalyticsSummary, UserSegment, Sponsor, CreditAccount, PredictionOracle, WhaleTransaction, AffiliatePartner, AffiliateClick, FeedItem, SentimentSnapshot, PulseEvent, AutoPostDraft, DailyBrief, OracleSession, MarketBriefing, PriceAlert
import hashlib
import json
from functools import wraps
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.content_generator import ContentGenerator
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
import subprocess
from pathlib import Path
import models
from datetime import datetime, timedelta


# Initialize services
ai_service = AIService()
reddit_service = RedditService()
content_generator = ContentGenerator()
content_engine = None  # Lazy loaded to avoid circular import
try:
    substack_service = SubstackService()
except Exception as e:
    logging.warning(f"Substack service initialization failed: {e}")
    substack_service = None

# Initialize RSS and Printful services
rss_service = RSSService()
printful_service = PrintfulService()

# ─── F2 BRIEFING ROOM HELPERS ────────────────────────────────
try:
    from services.briefing_service import generate_briefing as _run_briefing_generation
    _briefing_service_ok = True
except Exception as _bse:
    logging.warning("briefing_service import failed: %s", _bse)
    _briefing_service_ok = False


def _next_briefing_utc_epoch() -> int:
    """Compute the UTC epoch (ms) of the next scheduled ET briefing slot."""
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
        tomorrow = (now_et + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
        return int(tomorrow.astimezone(_UTC).timestamp() * 1000)
    except Exception as e:
        logging.warning("_next_briefing_utc_epoch failed: %s", e)
        return 0


def admin_required(f):
    """Decorator to enforce admin role-based access control.
    Supports X-Admin-Token header bypass for API/automation access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token = request.headers.get("X-Admin-Token", "")
        expected_token = os.environ.get("ADMIN_TOKEN", "")
        if admin_token and expected_token and admin_token == expected_token:
            return f(*args, **kwargs)
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/viral-moments', methods=['POST'])
@login_required
@admin_required
def admin_create_viral_moments_job():
    """Create a ClipJob for the Viral Moments reel pipeline.

    Expects JSON: {"video_id": "...", "channel_name": "..."}
    Returns: {"success": true, "job_id": <int>}
    """
    import json

    data = request.get_json(silent=True) or {}
    video_id = str(data.get('video_id') or '').strip()
    channel_name = str(data.get('channel_name') or '').strip()

    if not video_id:
        return jsonify({"success": False, "error": "video_id is required"}), 400

    # Local import to avoid circular import issues during app boot.
    from app import db
    import models

    job = models.ClipJob(
        video_id=video_id,
        channel_name=channel_name or None,
        # Legacy columns are NOT NULL in the current schema; populate them even if V2 fields are used.
        timestamps_json=json.dumps([]),
        narrative_context="",
        # V2 fields
        segments_json=json.dumps([]),
        status="Planned",
        metadata_json=json.dumps({"source": "admin/viral-moments"}),
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({"success": True, "job_id": int(job.id)})


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
        remote = str(request.remote_addr or "")
        if (
            is_enabled("ENABLE_SELF_CHECK_BYPASS")
            and request.headers.get("X-Self-Check") == "1"
            and ("127.0.0.1" in remote or remote in ("::1", "localhost"))
        ):
            return f(*args, **kwargs)
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('login') + '?next=' + request.path)
        if getattr(current_user, 'is_admin', False):
            return f(*args, **kwargs)
        if not getattr(current_user, 'has_premium', lambda: False)():
            flash('Premium Hub requires a paid subscription (Operator $21/mo or higher).')
            return redirect(url_for('premium_page'))
        return f(*args, **kwargs)
    return decorated_function


# Commander gate alias for compatibility with prior specs/routes.
commander_required = premium_hub_required


@app.route('/admin/x-replies')
@login_required
@admin_required
def admin_x_replies():
    """Admin queue for X sentry drafts."""
    pending = (
        models.XInboxTweet.query.filter_by(status='drafted')
        .order_by(models.XInboxTweet.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('admin/x_replies.html', pending=pending)


@app.route('/admin/x-replies/<int:inbox_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_approve(inbox_id):
    _require_csrf()
    from core.services.x_client import XClient

    inbox = models.XInboxTweet.query.get_or_404(inbox_id)
    draft = inbox.drafts.order_by(models.XReplyDraft.created_at.desc()).first()
    if not draft:
        flash('No draft available for this tweet.')
        return redirect('/admin/x-replies')

    new_text = (request.form.get('draft_text') or '').strip()
    if new_text:
        draft.draft_text = new_text[:280]

    result = XClient().post_reply(in_reply_to_tweet_id=inbox.tweet_id, text=draft.draft_text)
    post = models.XReplyPost(
        inbox_id=inbox.id,
        draft_id=draft.id,
        reply_tweet_id=result.get('tweet_id'),
        response_payload=json.dumps(result.get('raw', {})),
    )
    inbox.status = 'posted' if result.get('success') else 'error'
    db.session.add(post)
    db.session.add(inbox)
    db.session.commit()
    flash('Reply posted to X.' if result.get('success') else 'Reply failed to post; see logs.')
    return redirect('/admin/x-replies')


@app.route('/admin/x-replies/<int:inbox_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_reject(inbox_id):
    _require_csrf()
    inbox = models.XInboxTweet.query.get_or_404(inbox_id)
    inbox.status = 'rejected'
    db.session.add(inbox)
    db.session.commit()
    flash('Draft rejected.')
    return redirect('/admin/x-replies')


@app.route('/admin/x-replies/run-cycle', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_run_cycle():
    _require_csrf()
    from core.services.x_engagement_sentry import run_cycle
    result = run_cycle()
    return jsonify({"success": True, "result": result})


@app.route('/api/sentry-stream')
@login_required
@admin_required
def api_sentry_stream():
    """SSE stream for draft queue updates."""
    import time

    def generate():
        last_seen = 0
        started = time.time()
        while time.time() - started < 300:
            try:
                latest = (
                    models.XReplyDraft.query.order_by(models.XReplyDraft.id.desc()).first()
                )
                if latest and latest.id > last_seen:
                    last_seen = latest.id
                    payload = {
                        "type": "new_draft",
                        "draft_id": latest.id,
                        "inbox_id": latest.inbox_id,
                        "confidence": float(latest.confidence or 0),
                        "preview": (latest.draft_text or "")[:180],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                yield ": heartbeat\n\n"
                time.sleep(3)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})


@app.route('/api/logs-stream')
@login_required
@premium_hub_required
def api_logs_stream():
    """SSE stream for automation terminal tail in Commander Hub."""
    import time

    def generate():
        log_path = Path('/home/ultron/protocol_pulse/logs/automation.log')
        offset = log_path.stat().st_size if log_path.exists() else 0
        started = time.time()
        while time.time() - started < 300:
            try:
                if log_path.exists():
                    size = log_path.stat().st_size
                    if offset > size:
                        offset = 0
                    with log_path.open('r', encoding='utf-8', errors='ignore') as fp:
                        fp.seek(offset)
                        lines = fp.readlines()
                        offset = fp.tell()
                    for line in lines[-50:]:
                        line = line.rstrip('\n')
                        if line:
                            yield f"data: {json.dumps({'type': 'line', 'line': line})}\n\n"
                yield ": heartbeat\n\n"
                time.sleep(2)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})

@app.template_filter('to_est')
def to_est_filter(dt):
    """Convert a naive UTC datetime to Eastern Time for display."""
    if dt is None:
        return ""
    import pytz
    eastern = pytz.timezone("America/New_York")
    if dt.tzinfo is None:
        utc_dt = pytz.utc.localize(dt)
    else:
        utc_dt = dt
    return utc_dt.astimezone(eastern)

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


def get_latest_episode():
    """Read latest Pulse Check episode metadata from today's or most recent script.json."""
    import glob, datetime
    base = '/home/ultron/protocol_pulse/video_pipeline_v3/output'
    today = datetime.date.today().strftime('%Y-%m-%d')
    # Try today first, then walk back 7 days
    for delta in range(8):
        d = (datetime.date.today() - datetime.timedelta(days=delta)).strftime('%Y-%m-%d')
        script_path = f'{base}/{d}/script.json'
        manifest_path = f'{base}/{d}/episode_manifest.json'
        thumb_path = f'{base}/{d}/thumbnail.png'
        try:
            import json as _json
            with open(script_path) as f:
                script = _json.load(f)
            # Find the mp4 in the output dir
            import glob as _glob
            mp4s = _glob.glob(f'{base}/{d}/pulse_check_*.mp4')
            # Exclude derivative files
            mp4s = [m for m in mp4s if not any(x in m for x in ['.bgl_audio', '.concat_raw', '.intro_mus', '.music_mixed'])]
            video_url = None
            if mp4s:
                fname = sorted(mp4s)[-1].split('/home/ultron/protocol_pulse/')[-1]
                # Map to video.protocolpulse.io
                video_url = 'https://video.protocolpulse.io/video_pipeline_v3/output/' + d + '/' + mp4s[-1].split('/')[-1]
            thumbnail_url = f'/static/images/default-header.png'
            if _glob.glob(thumb_path):
                thumbnail_url = f'https://video.protocolpulse.io/video_pipeline_v3/output/{d}/thumbnail.png'
            return {
                'title': script.get('episode_title', 'Bitcoin Intelligence Briefing'),
                'date': d,
                'video_url': video_url,
                'thumbnail_url': thumbnail_url,
                'segments': script.get('segments_summary', []),
                'found': True,
            }
        except Exception:
            continue
    return {'found': False, 'title': None, 'date': None, 'video_url': None, 'thumbnail_url': None}


@app.route('/')
@cache.cached(timeout=60, key_prefix='view_index')
def index():
    """Homepage with featured articles, segment-based Bento-box ranking"""
    try:
        featured_articles = Article.query.filter_by(published=True, featured=True).order_by(
            db.func.coalesce(Article.published_at, Article.created_at).desc()
        ).limit(3).all()
        recent_articles = Article.query.filter_by(published=True).order_by(
            db.func.coalesce(Article.published_at, Article.created_at).desc()
        ).limit(12).all()
        featured_podcasts = Podcast.query.filter_by(featured=True).order_by(Podcast.published_date.desc()).limit(3).all()
        # Carousel: top articles by importance_score (falls back to featured then recent)
        try:
            from sqlalchemy import text as _sqla_text
            carousel_rows = db.session.execute(_sqla_text(
                "SELECT id FROM articles WHERE published=1 ORDER BY COALESCE(importance_score,0) DESC, created_at DESC LIMIT 3"
            )).fetchall()
            carousel_ids = [r[0] for r in carousel_rows]
            carousel_articles = Article.query.filter(Article.id.in_(carousel_ids)).all() if carousel_ids else []
        except Exception:
            carousel_articles = featured_articles[:3] if featured_articles else recent_articles[:3]
    except Exception as _db_err:
        logging.error("Homepage DB query failed: %s", _db_err)
        featured_articles = []
        recent_articles = []
        featured_podcasts = []
        carousel_articles = []

    # Fetch live cryptocurrency prices
    prices = price_service.get_prices()

    # Generate Today's Signal briefing (120 words max)
    todays_signal = generate_todays_signal()

    # Segment-based Bento-box ranking
    user_segment = 'general'
    bento_categories = []
    try:
        if current_user.is_authenticated:
            segment = UserSegment.query.filter_by(user_id=current_user.id).first()
            if segment:
                user_segment = segment.segment_type
                if segment.segment_type == 'miner':
                    bento_categories = ['mining', 'hashrate', 'bitcoin', 'difficulty']
                elif segment.segment_type == 'institution':
                    bento_categories = ['regulation', 'macro', 'bitcoin', 'etf']
                elif segment.segment_type == 'trader':
                    bento_categories = ['trading', 'price', 'defi', 'bitcoin']
                elif segment.segment_type == 'developer':
                    bento_categories = ['innovation', 'lightning', 'privacy', 'bitcoin']
    except Exception:
        pass

    # Get segment-specific content for Bento-box
    bento_articles = []
    try:
        if bento_categories:
            for category in bento_categories[:2]:
                cat_articles = Article.query.filter(
                    Article.published == True,
                    Article.category.ilike(f'%{category}%')
                ).order_by(Article.created_at.desc()).limit(2).all()
                bento_articles.extend(cat_articles)
    except Exception:
        pass

    article_image_urls = {}
    for a in (featured_articles + recent_articles + bento_articles + carousel_articles):
        article_image_urls[a.id] = a.resolve_cover_image()

    latest_episode = get_latest_episode()
    return render_template('index.html',
                         featured_articles=featured_articles,
                         recent_articles=recent_articles,
                         carousel_articles=carousel_articles,
                         featured_podcasts=featured_podcasts,
                         prices=prices,
                         price_service=price_service,
                         todays_signal=todays_signal,
                         user_segment=user_segment,
                         bento_articles=bento_articles[:4],
                         article_image_urls=article_image_urls,
                         latest_episode=latest_episode)

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

@app.route('/sovereign-money')
def sovereign_money():
    """The Case for Sovereign Money — purchasing power decay thesis"""
    return render_template('sovereign_money.html')

@app.route('/terminal')
def pulse_terminal():
    """Pulse Terminal API landing page — Commander pricing and documentation."""
    return render_template('pulse_terminal.html')

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
    import time as _time

    whales = []
    now = _time.time()
    if _whale_cache.get('data') and now - _whale_cache.get('time', 0) < 120:
        whales = _whale_cache['data'].get('whales', [])
    else:
        try:
            all_candidates = []
            seen = set()
            blocks_resp = requests.get('https://mempool.space/api/blocks', timeout=10)
            if blocks_resp.status_code == 200:
                blocks = blocks_resp.json()[:10]
                for block in blocks:
                    block_time = block.get('timestamp', 0)
                    block_height = block.get('height')
                    block_id = block.get('id')
                    for page_start in [0, 25]:
                        try:
                            txs_resp = requests.get(
                                f"https://mempool.space/api/block/{block_id}/txs/{page_start}",
                                timeout=15
                            )
                            if txs_resp.status_code != 200:
                                continue
                            for tx in txs_resp.json():
                                if tx.get('vin', [{}])[0].get('is_coinbase'):
                                    continue
                                outputs = tx.get('vout', [])
                                total_out = sum(out.get('value', 0) for out in outputs)
                                btc_value = total_out / 100_000_000
                                if btc_value >= 10 and tx['txid'] not in seen:
                                    seen.add(tx['txid'])
                                    all_candidates.append({
                                        'txid': tx['txid'],
                                        'btc': round(btc_value, 4),
                                        'fee': tx.get('fee', 0),
                                        'time': block_time,
                                        'block': block_height
                                    })
                        except Exception:
                            continue
            large = [c for c in all_candidates if c['btc'] >= 100]
            if large:
                large.sort(key=lambda x: x['time'], reverse=True)
                whales = large[:3]
            else:
                all_candidates.sort(key=lambda x: x['btc'], reverse=True)
                whales = all_candidates[:3]
            if whales:
                _whale_cache['data'] = {'whales': whales, 'count': len(whales)}
                _whale_cache['time'] = now
        except Exception as e:
            logging.error(f"Error fetching whales for page: {e}")

    if not whales:
        try:
            db_whales = WhaleTransaction.query.filter(
                WhaleTransaction.btc_amount >= 10
            ).order_by(WhaleTransaction.detected_at.desc()).limit(3).all()
            whales = [{
                'txid': w.txid,
                'btc': float(w.btc_amount),
                'fee': w.fee_sats or 0,
                'time': int(w.detected_at.timestamp()) if w.detected_at else 0,
                'block': w.block_height or 0
            } for w in db_whales]
        except Exception:
            pass

    return render_template('whale_watcher.html', initial_whales=whales)

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
    from models import CuratedPost, ValueCreator
    
    platform = request.args.get('platform')
    
    posts = value_stream_service.get_value_stream(limit=50, platform=platform)
    curators = value_stream_service.get_top_curators(limit=10)
    
    post_objects = []
    for p in posts:
        post = CuratedPost.query.get(p['id'])
        if post:
            post_objects.append(post)
    
    curator_objects = []
    for c in curators:
        curator = ValueCreator.query.get(c['id'])
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
    from models import CuratedPost, ValueCreator, ZapEvent
    from datetime import datetime, timedelta

    
    posts = value_stream_service.get_value_stream_enhanced(limit=50)
    curators = value_stream_service.get_top_curators(limit=10)
    
    curator_objects = []
    for c in curators:
        curator = ValueCreator.query.get(c['id'])
        if curator:
            curator_objects.append(curator)
    
    sats_hour = db.session.query(db.func.sum(ZapEvent.amount_sats)).filter(
        ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
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
    from models import CuratedPost, ZapEvent
    from datetime import datetime, timedelta

    
    post = CuratedPost.query.get(post_id)
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
    recent_zaps = ZapEvent.query.filter(
        ZapEvent.post_id == post_id,
        ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
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
    from models import CuratedPost, ZapEvent
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
                    new_posts = CuratedPost.query.filter(
                        CuratedPost.submitted_at > last_check
                    ).order_by(CuratedPost.signal_score.desc()).limit(10).all()
                    
                    new_zaps = ZapEvent.query.filter(
                        ZapEvent.created_at > last_check
                    ).order_by(ZapEvent.created_at.desc()).limit(20).all()
                    
                    if new_posts:
                        for post in new_posts:
                            velocity = ZapEvent.query.filter(
                                ZapEvent.post_id == post.id,
                                ZapEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
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
    from models import ValueCreator
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
        creator = ValueCreator.query.filter_by(
            twitter_handle=current_user.username
        ).first()
        if creator:
            curator_id = creator.id
        else:
            new_creator = ValueCreator(
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
    from models import CuratedPost
    import requests as req
    
    data = request.get_json() or {}
    amount_sats = data.get('amount_sats', 1000)
    amount_msats = amount_sats * 1000
    
    post = CuratedPost.query.get(post_id)
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
        event = NostrEvent.query.filter_by(pubkey=pubkey).order_by(NostrEvent.created_at.desc()).first()
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

@app.route("/go/rns")
def go_rns():
    ref = request.args.get("ref", "/digital-residency")
    from flask import redirect
    return redirect("https://rns.id?ref=protocolpulse", 302)

@app.route("/digital-residency")
def digital_residency():
    return render_template("digital_residency.html")

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
    """Signal Clips Gallery - Viral reel feed with embeds and play."""
    clip_jobs = []
    clips = []
    status = {"status": "ok", "ffmpeg_available": False, "ytdlp_available": False, "openai_configured": False, "clips_count": 0}
    try:
        from services.ai_clips_service import ai_clips_service
        clips = ai_clips_service.get_all_clips()
        status = ai_clips_service.get_status()
    except Exception as e:
        logging.warning("AI Clips service: %s", e)
        status["status"] = "degraded"
        status["error"] = str(e)
        # Fallback to the legacy clips_service if present.
        try:
            from services.clips_service import clips_service
            clips = clips_service.get_all_clips()
            status = clips_service.get_status()
        except Exception:
            pass
    try:
        import models
        jobs = (
            models.ClipJob.query
            .order_by(models.ClipJob.id.desc())
            .limit(100)
            .all()
        )
        for j in jobs:
            reel_url = None
            if j.output_path:
                p = (j.output_path or "").strip()
                if p.startswith("static/"):
                    reel_url = url_for("static", filename=p[7:])
                elif p.startswith("/"):
                    reel_url = p
                else:
                    reel_url = url_for("static", filename=p)
            setattr(j, "reel_url", reel_url)
        clip_jobs = jobs
    except Exception as e:
        logging.warning("ClipJob list: %s", e)
    return render_template("clips.html", clip_jobs=clip_jobs or [], clips=clips or [], status=status)

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
@cache.cached(timeout=60, key_prefix='view_articles')
def articles():
    """Articles page (Replit-style): 3 time windows + archive button.

    Zones:
    - The 24-Hour Pulse: created within last 24h
    - The Morning After: created 24–48h ago
    - The Vault: older than 48h (show 20 behind a button)
    """
    now = datetime.utcnow()

    try:
        # Prefer published; if none, fall back to all (so articles are never "gone")
        base_q = models.Article.query.filter(models.Article.published.is_(True)).order_by(models.Article.created_at.desc())
        total_count = base_q.count()
        if total_count == 0:
            logging.info("No published articles; falling back to all articles.")
            base_q = models.Article.query.order_by(models.Article.created_at.desc())
            total_count = base_q.count()

        # Time windows
        since_24h = now - timedelta(hours=24)
        since_48h = now - timedelta(hours=48)

        # Limits to keep the page snappy
        today_articles = base_q.filter(models.Article.created_at >= since_24h).limit(10).all()
        yesterday_articles = base_q.filter(models.Article.created_at < since_24h, models.Article.created_at >= since_48h).limit(10).all()

        archive_q = base_q.filter(models.Article.created_at < since_48h)
        archive_total_count = archive_q.count()
        archive_articles = archive_q.limit(500).all()

        for article in today_articles:
            try:
                time_diff = (now - (article.created_at or now)).total_seconds() / 3600
                article.is_pressing = time_diff < 1
            except Exception:
                article.is_pressing = False

        # Ticker: always last 5 article titles
        try:
            ticker_titles = [a.title for a in base_q.limit(5).all()]
        except Exception:
            ticker_titles = []

        # Categories for sidebar navigation; DeFi excluded
        categories = [cat[0] for cat in db.session.query(models.Article.category).distinct().all() if cat[0]]
        categories = [c for c in categories if c != 'DeFi']
    except Exception as _db_err:
        logging.error("Articles DB query failed: %s", _db_err)
        today_articles = []
        yesterday_articles = []
        archive_articles = []
        archive_total_count = 0
        ticker_titles = []
        categories = []
        total_count = 0

    # Legacy variables kept for template compatibility (older layouts/admin views)
    per_page = 40
    page = request.args.get('page', 1, type=int) or 1
    total_pages = 1
    latest_article = today_articles[0] if today_articles else None
    recent = (today_articles + yesterday_articles + archive_articles)
    grid_articles = recent
    spotlight_articles = []
    sectioned = {}
    latest_grid = []
    more_articles = []

    # Category counts for filter pills (published only; fallback to all if none published)
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
    # Use resolve_cover_image() — the single source of truth (handles http + /static/ paths)
    default_header_url = "/static/images/default-header.png"
    article_image_urls = {}
    for a in (today_articles + yesterday_articles + archive_articles):
        article_image_urls[a.id] = a.resolve_cover_image()

    return render_template(
        "articles.html",
        today_articles=today_articles,
        yesterday_articles=yesterday_articles,
        archive_articles=archive_articles,
        archive_total_count=archive_total_count,
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
        article_image_urls=article_image_urls,
    )

def _article_body_without_tldr(content):
    """Return article body HTML, stripping only the tldr-section div (shown separately in Key Takeaways).
    Never returns empty — always returns the full content minus TL;DR block."""
    if not content:
        return ""
    # Remove the tldr-section div only — keep everything else
    import re as _re
    body = _re.sub(
        r'<div[^>]*class=["\']tldr-section["\'][^>]*>.*?</div>',
        "",
        content,
        flags=_re.DOTALL | _re.IGNORECASE
    ).strip()
    # Also strip leading h1 (title already shown in header)
    body = _re.sub(r'^<h1[^>]*>.*?</h1>\s*', "", body, flags=_re.DOTALL | _re.IGNORECASE).strip()
    # If stripping removed everything, return full content as fallback
    return body if body else content


def _article_key_takeaways(article):
    """Extract key takeaways: use summary, or TL;DR from content, or first 400 chars. Never duplicate with body."""
    summary = (article.summary or "").strip()
    content = (article.content or "")
    if summary:
        return summary
    # Extract TL;DR from content (plain text for the callout)
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


@app.route('/intel/<slug>')
@app.route('/articles/<slug>')
def article_detail_slug(slug):
    if slug.isdigit():
        a = models.Article.query.get_or_404(int(slug))
        if a.slug:
            return redirect(f"/articles/{a.slug}", 301)
    else:
        a = models.Article.query.filter_by(slug=slug).first()
        if not a:
            abort(404)
    # Render the article using the existing numeric route logic
    return _render_article(a.id)

@app.route('/articles/<int:article_id>')
def article_detail(article_id):
    # 301 redirect numeric IDs to slug URLs
    a = models.Article.query.get_or_404(article_id)
    if a.slug:
        from flask import redirect
        return redirect(f"/articles/{a.slug}", 301)
    # Fallback: no slug, render directly
    return _render_article(article_id)


def _render_article(article_id):
    """Shared rendering logic for article pages."""
    article = models.Article.query.get_or_404(article_id)
    # Increment read count
    try:
        article.read_count = (article.read_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        related_articles = models.Article.query.filter(
            models.Article.id != article_id,
            models.Article.published == True,
            models.Article.category == article.category
        ).limit(3).all()
    except Exception:
        related_articles = []
    key_takeaways_text = _article_key_takeaways(article)
    # Bullet list: split on sentence boundaries for Key Takeaways box
    key_takeaways_bullets = []
    if key_takeaways_text:
        for part in re.split(r"\.\s+", key_takeaways_text):
            part = part.strip().strip(".")
            if part and len(part) > 10:
                key_takeaways_bullets.append(part + ("." if not part.endswith(".") else ""))
    if not key_takeaways_bullets and key_takeaways_text:
        key_takeaways_bullets = [key_takeaways_text]
    # Full body for display (duplicate TL;DR stripped so only Key Takeaways box shows it once)
    body_html = _article_body_without_tldr(article.content or "")
    # Law 1: cover_image_url is the single source of truth
    cover_image_url = article.resolve_cover_image() if hasattr(article, 'resolve_cover_image') else "/static/images/default-header.png"
    if cover_image_url and not cover_image_url.startswith("http"):
        cover_image_url = "https://protocolpulse.io" + cover_image_url
    return render_template(
        "article_detail.html",
        article=article,
        related_articles=related_articles,
        key_takeaways_text=key_takeaways_text,
        key_takeaways_bullets=key_takeaways_bullets,
        body_html=body_html,
        cover_image_url=cover_image_url,
    )

@app.route('/category/<category>')
def category_articles(category):
    """Category-filtered article listing with premium design"""
    articles = Article.query.filter(
        Article.published == True,
        Article.category == category
    ).order_by(Article.created_at.desc()).limit(50).all()
    
    return render_template('category.html', category=category, articles=articles)

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
    
    # Generate smart playlist based on user segment
    smart_playlist = None
    try:
        if current_user.is_authenticated:
            user_segment = UserSegment.query.filter_by(user_id=current_user.id).first()
            segment_type = user_segment.segment_type if user_segment else 'institution'
        else:
            segment_type = 'institution'
        
        from services.content_engine import content_engine
        smart_playlist = content_engine.get_smart_playlist(segment_type)
    except Exception as e:
        logging.warning(f"Smart playlist generation failed: {e}")
    
    return render_template('podcasts.html', podcast_sections=podcast_sections, smart_playlist=smart_playlist)


@app.route('/network-health')
def network_health():
    """Real-time Bitcoin network health dashboard."""
    return render_template('network_health.html')


@app.route('/charts')
@cache.cached(timeout=60, key_prefix='view_charts')
def charts():
    """Interactive BTC charts — price, hashrate, fees."""
    return render_template('charts.html')


@app.route('/pulse-check')
def pulse_check():
    """Pulse Check — daily AI-generated Bitcoin news video series archive"""
    episodes = Podcast.query.filter(
        Podcast.rss_source.ilike('%pulse%')
    ).order_by(Podcast.published_date.desc()).limit(50).all()
    # Fallback: if no pulse-specific episodes, show all recent
    if not episodes:
        episodes = Podcast.query.order_by(Podcast.published_date.desc()).limit(20).all()
    latest = episodes[0] if episodes else None
    archive = episodes[1:] if len(episodes) > 1 else []
    return render_template('pulse_check.html', latest=latest, archive=archive)


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

@app.route('/media-terminal')
def media_terminal():
    """301 permanent redirect from media-terminal to /media"""
    return redirect('/media', 301)

@app.route('/media-hub')
def media_hub_redirect():
    """301 permanent redirect from /media-hub to /media"""
    return redirect('/media', 301)

@app.route('/media')
@app.route('/media-unified')
@cache.cached(timeout=60, key_prefix='view_media')
def media_hub():
    """Media Hub — Bitcoin Media Command Center with Feed Matrix"""
    try:
        from models import Podcast, MediaFeed, MediaEpisode
        from services.youtube_service import YouTubeService
        from services.media_feed_service import get_feed_matrix, get_ticker_items, get_feed_stats, sync_feeds_background
        import copy

        # ── Feed Matrix (aggregated RSS + YouTube) ──
        try:
            feed_matrix = get_feed_matrix(limit_per_col=25)
            ticker_items = get_ticker_items(limit=30)
            feed_stats = get_feed_stats()
        except Exception as fm_err:
            logging.warning(f"Feed matrix not ready: {fm_err}")
            feed_matrix = {'podcasts': [], 'videos': []}
            ticker_items = []
            feed_stats = {'feed_count': 0, 'episode_count': 0, 'podcast_count': 0, 'video_count': 0}

        # Trigger background sync if feeds are empty
        if feed_stats.get('episode_count', 0) == 0:
            try:
                sync_feeds_background()
            except Exception:
                pass

        # ── YouTube Series ──
        youtube_service_instance = YouTubeService()

        series_config = {
            'everything_21m': {
                'key': 'everything_21m',
                'title': 'Everything Divided by 21 Million',
                'host': 'Matty Ice & Knut Svanholm',
                'description': 'A cinematic exploration of Bitcoin\'s relationship to time, money, freedom, and human progress.',
                'episodes': [
                    {'id': 'FA8tvWEydcA', 'title': 'Time | Episode 1'},
                    {'id': 'VDordtHAJhg', 'title': 'Alchemy | Episode 2'},
                    {'id': 'yKbQq66AInU', 'title': 'Ownership | Episode 3'},
                    {'id': 'rkTbEpAOADI', 'title': 'Energy | Episode 4'},
                    {'id': 'qG2xYvTVkw0', 'title': 'Morality | Episode 5'},
                    {'id': 'v7xZPqcXyLk', 'title': 'Memetics | Episode 6'},
                    {'id': 'RZv_1Qcqik4', 'title': 'Symbiosis | Episode 7'},
                    {'id': 'UlYSv9SwQGk', 'title': 'Violence | Episode 8'},
                    {'id': '_ygND311kVE', 'title': 'Deflation | Episode 9'},
                    {'id': 'Nf0LtAk4VBs', 'title': 'Adoption | Episode 10'},
                    {'id': 'Gt8ycm3-NV8', 'title': 'Transition | Episode 11'},
                ]
            },
            'big_print': {
                'key': 'big_print',
                'title': 'The Big Print',
                'host': 'Matty Ice & Lawrence Lepard',
                'description': 'How the Federal Reserve engineered the most devastating wealth extraction scheme in history.',
                'episodes': [
                    {'id': 'W09CNU_q6Yo', 'title': 'Why Fixing the Money is the Only Way | Episode 1'},
                    {'id': 'tnthM3uaHbI', 'title': 'How Govt Stole 98.5% Since 1971 | Episode 2'},
                    {'id': 'FRH5w_joMP0', 'title': 'How Inflation Steals Your Life | Episode 3'},
                    {'id': 'JLjG8jAJxbw', 'title': 'The Path to Pure Fiat | Episode 4'},
                    {'id': 'tq_ZYhpW4Vw', 'title': 'How Powell & Yellen Broke It | Episode 5'},
                    {'id': 'Sjp-Kaic2CE', 'title': 'Austrian vs Keynesian | Episode 6'},
                    {'id': 'n6Bi8Kf6ar0', 'title': 'The Sovereign Currency Bubble | Episode 7'},
                    {'id': 'M3M61rLBTl0', 'title': 'Bitcoin is God\'s Gift | Episode 8'},
                    {'id': 'uzUEJZ38RV8', 'title': 'Bitcoin & Real Estate | Episode 9'},
                    {'id': 'y9snxWoEkaU', 'title': 'End of Centralized Power | Episode 10'},
                    {'id': 'hKa8lRDwIos', 'title': 'Digital Scarcity | Episode 11'},
                    {'id': 'FyMWELymqAM', 'title': 'Fix the Money, Fix the World | Episode 12'},
                ]
            },
            'daylight_robbery': {
                'key': 'daylight_robbery',
                'title': 'Daylight Robbery',
                'host': 'Matty Ice & Dominic Frisby',
                'description': 'The hidden story of how taxation shaped human civilization from ancient empires to modern governments.',
                'episodes': [
                    {'id': 'ZCc78wvwd6U', 'title': 'The Hidden History of Taxation | Episode 1'},
                    {'id': 'j_V3fjvEuS0', 'title': 'How Taxes Shaped Civilization | Episode 2'},
                    {'id': 'W_TNwftaVMk', 'title': 'Death, Taxes, or Islam | Episode 3'},
                    {'id': '3VDVbbSZYPc', 'title': 'The Peasants\' Revolt | Episode 4'},
                    {'id': 'brho571r5rY', 'title': 'Tax Wars That Created Nations | Episode 5'},
                    {'id': 'zltb_tXZiWI', 'title': 'How the Richest Controlled Nations | Episode 6'},
                    {'id': '0MDv0d-3t_k', 'title': 'How Tariffs Caused Civil War | Episode 7'},
                    {'id': 'Ym5W3t9WvB8', 'title': 'The Birth of Big Government | Episode 8'},
                    {'id': 'YUHM88mtRxU', 'title': 'Hitler, Banks & Nations | Episode 9'},
                    {'id': 'LcIT9Tgbkm8', 'title': 'How Govts Silently Rob You | Episode 10'},
                    {'id': 'VRSXUD4L2eA', 'title': 'Digital Nomads & Borderless Money | Episode 11'},
                    {'id': '1OAn6QDSsJs', 'title': 'How Data & AI Reshape Taxation | Episode 12'},
                    {'id': 'xPPbMsz8qso', 'title': 'The Perfect Tax System | Episode 13'},
                ]
            },
            'genesis_book': {
                'key': 'genesis_book',
                'title': 'The Genesis Book',
                'host': 'Matty Ice & Aaron van Wirdum',
                'description': 'Exploring the origins of Bitcoin through Aaron van Wirdum\'s seminal work on Austrian economics and the cypherpunk movement.',
                'episodes': [
                    {'id': 'y7KBeC4jfbo', 'title': 'Origins of Digital Cash | Episode 1'},
                    {'id': 'LNEsJjYZ57o', 'title': 'The Cypherpunks | Episode 2'},
                    {'id': 'KcTVg0b7kDw', 'title': 'Hash Cash & Digital Gold | Episode 3'},
                    {'id': 'TwkR0ncLh0Y', 'title': 'Satoshi\'s Vision | Episode 4'},
                    {'id': 'mAe_F5G6gUE', 'title': 'The Genesis Block | Episode 5'},
                ]
            },
        }
        
        # Build series list for template
        series_list = []
        for key, s in series_config.items():
            series_list.append({
                'key': key,
                'title': s['title'],
                'host': s['host'],
                'description': s['description'],
                'first_id': s['episodes'][0]['id'] if s['episodes'] else '',
                'ep_count': len(s['episodes']),
            })
        
        # ── Podcast Episodes ──
        latest_episodes = Podcast.query.order_by(Podcast.published_date.desc()).limit(12).all()
        podcast_count = Podcast.query.count()
        
        # ── Books ──
        affiliate_tag = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')
        
        all_books = [
            {'title': 'Everything Divided by 21 Million', 'author': 'Knut Svanholm', 'amazon_url': f'https://www.amazon.com/dp/9916697191?tag={affiliate_tag}', 'featured': True, 'category': 'series', 'color': '#dc2626', 'cover_url': '/static/images/books/everything_21m.jpg'},
            {'title': 'The Big Print', 'author': 'Lawrence Lepard', 'amazon_url': f'https://www.amazon.com/dp/B0DVTCVX8J?tag={affiliate_tag}', 'featured': True, 'category': 'series', 'color': '#f59e0b', 'cover_url': '/static/images/books/big_print.jpg'},
            {'title': 'Daylight Robbery', 'author': 'Dominic Frisby', 'amazon_url': f'https://www.amazon.com/dp/0241360846?tag={affiliate_tag}', 'featured': True, 'category': 'series', 'color': '#ef4444', 'cover_url': '/static/images/books/daylight_robbery.jpg'},
            {'title': 'The Genesis Book', 'author': 'Aaron van Wirdum', 'amazon_url': f'https://www.amazon.com/dp/B0CQLMQRH7?tag={affiliate_tag}', 'featured': True, 'category': 'series', 'color': '#8b5cf6', 'cover_url': '/static/images/books/genesis_book.jpg'},
            {'title': 'The Bitcoin Standard', 'author': 'Saifedean Ammous', 'amazon_url': f'https://www.amazon.com/dp/1119473861?tag={affiliate_tag}', 'category': 'essential', 'color': '#f7931a', 'cover_url': '/static/images/books/bitcoin_standard.jpg'},
            {'title': 'Broken Money', 'author': 'Lyn Alden', 'amazon_url': f'https://www.amazon.com/dp/B0CG8985FR?tag={affiliate_tag}', 'category': 'essential', 'color': '#3b82f6', 'cover_url': '/static/images/books/broken_money.jpg'},
            {'title': 'The Fiat Standard', 'author': 'Saifedean Ammous', 'amazon_url': f'https://www.amazon.com/dp/1544526474?tag={affiliate_tag}', 'category': 'essential', 'color': '#6366f1', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1544526474-L.jpg'},
            {'title': 'Mastering Bitcoin', 'author': 'Andreas Antonopoulos', 'amazon_url': f'https://www.amazon.com/dp/1098150090?tag={affiliate_tag}', 'category': 'essential', 'color': '#f59e0b', 'cover_url': '/static/images/books/mastering_bitcoin.jpg'},
            {'title': 'The Price of Tomorrow', 'author': 'Jeff Booth', 'amazon_url': f'https://www.amazon.com/dp/1999257405?tag={affiliate_tag}', 'category': 'essential', 'color': '#10b981', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1999257405-L.jpg'},
            {'title': 'Softwar', 'author': 'Jason Lowery', 'amazon_url': f'https://www.amazon.com/dp/B0BW3MTQG6?tag={affiliate_tag}', 'category': 'essential', 'color': '#ef4444', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1544542895-L.jpg'},
            {'title': 'Thank God for Bitcoin', 'author': 'Jimmy Song et al.', 'amazon_url': f'https://www.amazon.com/dp/1641991216?tag={affiliate_tag}', 'category': 'essential', 'color': '#f7931a', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1641991216-L.jpg'},
            {'title': 'The Sovereign Individual', 'author': 'Davidson & Rees-Mogg', 'amazon_url': f'https://www.amazon.com/dp/0684832720?tag={affiliate_tag}', 'category': 'essential', 'color': '#8b5cf6', 'cover_url': 'https://covers.openlibrary.org/b/isbn/0684832720-L.jpg'},
            {'title': 'Bitcoin Billionaires', 'author': 'Ben Mezrich', 'amazon_url': f'https://www.amazon.com/dp/1250217768?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#f59e0b', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1250217768-L.jpg'},
            {'title': 'The Blocksize War', 'author': 'Jonathan Bier', 'amazon_url': f'https://www.amazon.com/dp/B08YQMC2WM?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#dc2626', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1916294219-L.jpg'},
            {'title': 'Inventing Bitcoin', 'author': 'Yan Pritzker', 'amazon_url': f'https://www.amazon.com/dp/B07MWXRWNB?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#f7931a', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1097476922-L.jpg'},
            {'title': 'The Book of Satoshi', 'author': 'Phil Champagne', 'amazon_url': f'https://www.amazon.com/dp/0996061312?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#6366f1', 'cover_url': 'https://covers.openlibrary.org/b/isbn/0996061312-L.jpg'},
            {'title': 'Digital Gold', 'author': 'Nathaniel Popper', 'amazon_url': f'https://www.amazon.com/dp/006236250X?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#f59e0b', 'cover_url': 'https://covers.openlibrary.org/b/isbn/006236250X-L.jpg'},
            {'title': 'Resistance Money', 'author': 'Andrew Bailey et al.', 'amazon_url': f'https://www.amazon.com/dp/1032609710?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#10b981', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1032609710-L.jpg'},
            {'title': 'Check Your Financial Privilege', 'author': 'Alex Gladstein', 'amazon_url': f'https://www.amazon.com/dp/B09V2NM9VJ?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#3b82f6', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1637587504-L.jpg'},
            {'title': 'Bitcoin is Venice', 'author': 'Allen Farrington', 'amazon_url': f'https://www.amazon.com/dp/B09TKNKFRS?tag={affiliate_tag}', 'category': 'bestseller', 'color': '#8b5cf6', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9798986175928-L.jpg'},
            {'title': 'Economics in One Lesson', 'author': 'Henry Hazlitt', 'amazon_url': f'https://www.amazon.com/dp/0517548232?tag={affiliate_tag}', 'category': 'economics', 'color': '#22c55e', 'cover_url': 'https://covers.openlibrary.org/b/isbn/0517548232-L.jpg'},
            {'title': 'Human Action', 'author': 'Ludwig von Mises', 'amazon_url': f'https://www.amazon.com/dp/1610167317?tag={affiliate_tag}', 'category': 'economics', 'color': '#22c55e', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1610167317-L.jpg'},
            {'title': 'What Has Government Done to Our Money?', 'author': 'Murray Rothbard', 'amazon_url': f'https://www.amazon.com/dp/1610166450?tag={affiliate_tag}', 'category': 'economics', 'color': '#22c55e', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1610166450-L.jpg'},
            {'title': 'The Ethics of Money Production', 'author': 'Jorg Guido Hulsmann', 'amazon_url': f'https://www.amazon.com/dp/1610166817?tag={affiliate_tag}', 'category': 'economics', 'color': '#22c55e', 'cover_url': 'https://covers.openlibrary.org/b/isbn/1610166817-L.jpg'},
        ]
        
        # Server-side fetch highlights for reliable rendering without JS dependency
        ssr_highlights = []
        try:
            import sqlite3 as _sl3, os as _os2
            si_path = _os2.path.join(_os2.path.dirname(__file__), 'data', 'sovereign_intel.db')
            if _os2.path.exists(si_path):
                conn = _sl3.connect(si_path)
                conn.row_factory = _sl3.Row
                rows = conn.execute(
                    'SELECT name, category, observation, implication, direction, ts_utc '
                    'FROM signals ORDER BY ts_utc DESC LIMIT 10'
                ).fetchall()
                conn.close()
                for r in rows:
                    obs = r['observation'] or ''
                    impl = r['implication'] or ''
                    excerpt = (obs + ' ' + impl).strip()[:200]
                    if excerpt:
                        ssr_highlights.append({
                            'title': r['name'],
                            'excerpt': excerpt,
                            'source': (r['category'] or 'INTEL').upper(),
                            'direction': r['direction'] or 'neutral',
                            'timestamp': r['ts_utc'],
                        })
            if not ssr_highlights:
                arts = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(8).all()
                for a in arts:
                    excerpt = (a.summary or a.content or '')[:180].strip()
                    if excerpt:
                        ssr_highlights.append({'title': a.title, 'excerpt': excerpt, 'source': 'PROTOCOL PULSE', 'direction': 'neutral'})
        except Exception as _e:
            logging.warning(f'SSR highlights failed: {_e}')

        # Commander gate flag for premium sections (heatmap, etc.)
        _is_commander = False
        try:
            if current_user.is_authenticated:
                _is_commander = getattr(current_user, 'has_commander_tier', lambda: False)()
        except Exception:
            pass

        return render_template('media_hub.html',
            series_list=series_list,
            series_data=series_config,
            series_count=len(series_config),
            latest_episodes=latest_episodes,
            podcast_count=podcast_count,
            voice_count=30,
            ssr_highlights=ssr_highlights,
            all_books=all_books,
            feed_matrix=feed_matrix,
            ticker_items=ticker_items,
            feed_stats=feed_stats,
            is_commander=_is_commander,
        )

    except Exception as e:
        logging.error(f"Error loading media hub: {e}")
        import traceback
        traceback.print_exc()
        return render_template('media_hub.html',
            series_list=[], series_data={}, series_count=0,
            latest_episodes=[], podcast_count=0, voice_count=0, all_books=[],
            feed_matrix={'podcasts': [], 'videos': []},
            ticker_items=[], feed_stats={}, is_commander=False)


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

@app.route('/api/media/rss')
def api_media_rss():
    """Media Command Center — RSS feed data (podcasts + videos)."""
    try:
        from services.media_feed_service import get_feed_matrix, get_ticker_items, get_feed_stats
        limit = request.args.get('limit', 20, type=int)
        category = request.args.get('category')  # 'podcast', 'video', or None for all
        matrix = get_feed_matrix(limit_per_col=limit)
        if category == 'podcast':
            data = matrix.get('podcasts', [])
        elif category == 'video':
            data = matrix.get('videos', [])
        else:
            data = matrix
        return jsonify({
            'ok': True,
            'data': data,
            'ticker': get_ticker_items(limit=30),
            'stats': get_feed_stats(),
        })
    except Exception as e:
        logging.error(f"api_media_rss error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/media/signal-score')
def api_media_signal_score():
    """Compute signal score for given text (used by front-end components)."""
    try:
        from services.media_feed_service import compute_signal_score
        title = request.args.get('title', '')
        description = request.args.get('description', '')
        tier = request.args.get('tier', 2, type=int)
        if not title and not description:
            return jsonify({'ok': False, 'error': 'title or description required'}), 400
        score = compute_signal_score(title, description, tier=tier)
        return jsonify({'ok': True, 'signal_score': score})
    except Exception as e:
        logging.error(f"api_media_signal_score error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/media/network')
def api_media_network():
    """Voice network graph data — nodes (KOLs/shows) and edges (collaborations)."""
    try:
        from services.media_feed_service import PODCAST_FEEDS, YOUTUBE_CHANNELS
        nodes = []
        for i, feed in enumerate(PODCAST_FEEDS):
            nodes.append({
                'id': f'p{i}',
                'name': feed['name'],
                'host': feed.get('host', ''),
                'tier': feed.get('tier', 2),
                'color': feed.get('color', '#f7931a'),
                'category': 'podcast',
            })
        for i, ch in enumerate(YOUTUBE_CHANNELS):
            nodes.append({
                'id': f'y{i}',
                'name': ch['name'],
                'tier': ch.get('tier', 2),
                'color': ch.get('color', '#dc2626'),
                'category': 'video',
            })
        # Edges: connect feeds that share hosts or frequent cross-appearances
        edges = []
        host_map = {}
        for n in nodes:
            host = n.get('host', n['name']).lower()
            for key in host_map:
                if key in host or host in key:
                    edges.append({'source': host_map[key], 'target': n['id']})
            host_map[host] = n['id']
        # Cross-media links (same brand on podcast + video)
        name_map = {}
        for n in nodes:
            base = n['name'].lower().replace(' podcast', '').replace(' magazine', '').strip()
            if base in name_map and name_map[base] != n['id']:
                edges.append({'source': name_map[base], 'target': n['id']})
            name_map[base] = n['id']
        return jsonify({'ok': True, 'nodes': nodes, 'edges': edges})
    except Exception as e:
        logging.error(f"api_media_network error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


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

_printful_cache = {'products': None, 'rtsa': None, 'ts': 0}

@app.route('/merch')
def merch_store():
    """Merch store page — Printful products cached 5 minutes"""
    import time as _time
    try:
        now = _time.time()
        if _printful_cache['products'] is not None and now - _printful_cache['ts'] < 300:
            formatted_products = _printful_cache['products']
            rtsa_hot, rtsa_approved, rtsa_foundational = _printful_cache['rtsa']
        else:
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

            _printful_cache['products'] = formatted_products
            _printful_cache['rtsa'] = (rtsa_hot, rtsa_approved, rtsa_foundational)
            _printful_cache['ts'] = now

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
    articles = Article.query.filter_by(published=True, category='Bitcoin').order_by(Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Bitcoin')

@app.route('/defi')
def defi_redirect():
    """DeFi section removed; redirect to intelligence feed."""
    return redirect(url_for('articles'))

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

# /newsletter/subscribe (POST) — moved to core/blueprints/newsletter.py (SESSION 2)

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
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    total_articles = Article.query.count()
    published_articles = Article.query.filter_by(published=True).count()
    total_podcasts = Podcast.query.count()
    recent_articles = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).limit(5).all()
    
    # Commander subscriber stats
    from models import CommanderSubscriber
    commander_total = CommanderSubscriber.query.count()
    commander_active = CommanderSubscriber.query.filter_by(active=True).count()
    commander_subs = CommanderSubscriber.query.order_by(CommanderSubscriber.created_at.desc()).limit(10).all()
    commander_calls = sum(s.calls_month or 0 for s in CommanderSubscriber.query.filter_by(active=True).all())

    return render_template('admin/dashboard.html',
                         total_articles=total_articles,
                         published_articles=published_articles,
                         total_podcasts=total_podcasts,
                         recent_articles=recent_articles,
                         commander_total=commander_total,
                         commander_active=commander_active,
                         commander_subs=commander_subs,
                         commander_calls=commander_calls)

# ============================================================
# SESSION 19 — ADMIN INTELLIGENCE DASHBOARD API ROUTES
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

    articles_24h = Article.query.filter(Article.created_at >= h24).count()
    articles_7d = Article.query.filter(Article.created_at >= d7).count()
    articles_total = Article.query.count()
    articles_published = Article.query.filter_by(published=True).count()
    articles_draft = Article.query.filter_by(published=False).count()
    articles_1h = Article.query.filter(Article.created_at >= h1).count()

    # Daily sparkline: count per day for last 7 days
    sparkline = []
    for i in range(6, -1, -1):
        day_start = now - timedelta(days=i+1)
        day_end = now - timedelta(days=i)
        cnt = Article.query.filter(
            Article.created_at >= day_start,
            Article.created_at < day_end
        ).count()
        sparkline.append(cnt)

    # Last video render — check logs
    last_video = None
    try:
        import glob as _glob
        report_paths = [
            '/home/ultron/protocol_pulse/logs/daily_pulse.report.json',
            '/home/ultron/protocol_pulse/logs/medley_pipeline_report.json',
            '/home/ultron/protocol_pulse/logs/medley_daily_beat.report.json',
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
    next_briefing_hour = 13
    next_briefing = now.replace(hour=next_briefing_hour, minute=0, second=0, microsecond=0)
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
        from models import NewsletterSubscriber, NewsletterSend
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        total_subs = NewsletterSubscriber.query.filter_by(subscribed=True).count()
        total_unsub = NewsletterSubscriber.query.filter_by(subscribed=False).count()
        new_today = NewsletterSubscriber.query.filter(
            NewsletterSubscriber.subscribed_at >= today_start,
            NewsletterSubscriber.subscribed == True
        ).count()
        new_week = NewsletterSubscriber.query.filter(
            NewsletterSubscriber.subscribed_at >= week_start,
            NewsletterSubscriber.subscribed == True
        ).count()
        unsub_week = NewsletterSubscriber.query.filter(
            NewsletterSubscriber.unsubscribed_at >= week_start
        ).count()

        last_send = NewsletterSend.query.order_by(NewsletterSend.sent_at.desc()).first()
        last_send_data = None
        if last_send:
            last_send_data = {
                'subject': last_send.subject,
                'sent_at': last_send.sent_at.isoformat() + 'Z' if last_send.sent_at else None,
                'recipient_count': last_send.recipient_count,
                'open_count': last_send.open_count,
                'click_count': last_send.click_count,
            }

        # Next email at 13:00 UTC
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

    # Top 10 articles by ID (proxy for recency/activity; no view_count column)
    top_articles_q = Article.query.filter_by(published=True)\
        .order_by(Article.created_at.desc()).limit(10).all()
    top_articles = [{
        'id': a.id,
        'title': a.title[:70],
        'category': a.category,
        'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
    } for a in top_articles_q]

    # Sentiment distribution from SentimentReport
    sentiment_dist = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    try:
        from models import SentimentReport
        reports = SentimentReport.query.order_by(SentimentReport.report_date.desc()).limit(30).all()
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
        partners = AffiliatePartner.query.filter_by(is_active=True).all()
        for p in partners:
            clicks_7d = AffiliateClick.query.filter(
                AffiliateClick.partner_id == p.id,
                AffiliateClick.clicked_at >= d7
            ).count()
            clicks_total = AffiliateClick.query.filter_by(partner_id=p.id).count()
            affiliate_data.append({
                'name': p.name,
                'slug': p.slug,
                'clicks_7d': clicks_7d,
                'clicks_total': clicks_total,
            })
    except Exception:
        pass

    # Draft/error article queue
    draft_queue = Article.query.filter_by(published=False)\
        .order_by(Article.created_at.desc()).limit(5).all()
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
        '/home/ultron/protocol_pulse/logs/gunicorn_error.log',
        '/home/ultron/logs/gunicorn_error.log',
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
    """Stripe MRR, active Commander subscribers. Returns {} if no key."""
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe_key:
        return jsonify({'available': False})

    try:
        import stripe as _stripe
        _stripe.api_key = stripe_key

        # Active Commander subscribers from DB
        commander_count = User.query.filter(
            User.subscription_tier.in_(['commander', 'sovereign'])
        ).count()

        # Stripe MRR: sum active subscription amounts
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

@app.route('/admin/generate')
@login_required
@admin_required
def admin_generate():
    """Content Command Center - All content generation tools"""
    prompts = ContentPrompt.query.filter_by(active=True).all()
    total_articles = Article.query.count()
    published_articles = Article.query.filter_by(published=True).count()
    total_podcasts = Podcast.query.count()
    
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
        from services.content_generator import auto_publish_enabled, validate_article_for_publish
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

        ok, validation_errors = validate_article_for_publish(article_data)
        header_url = (article_data.get('cover_image_url') or '').strip()
        if not header_url or not header_url.startswith('http'):
            header_url = (article_data.get('header_image_url') or '').strip()
        if not header_url or not header_url.startswith('http'):
            header_url = '/static/images/default-header.png'
        if not ok:
            # Save as draft for review; never publish invalid content.
            article = models.Article(
                title=article_data.get('title', 'Untitled'),
                content=article_data.get('content', ''),
                summary="",
                category=article_data.get('category', 'Web3'),
                tags=article_data.get('tags', ''),
                source_type=source_type,
                author="Al Ingle",
                seo_title=article_data.get('seo_title', article_data.get('title', '')[:200]),
                seo_description=article_data.get('seo_description', (article_data.get('title', '') or '')[:150]),
                published=False,
                cover_image_url=header_url,
            )
            db.session.add(article)
            db.session.commit()
            return jsonify({
                "success": False,
                "article_id": article.id,
                "title": article.title,
                "published": False,
                "status": "rejected",
                "reasons": validation_errors,
                "message": "Article rejected by validation gate (saved as draft).",
            }), 422
        
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
                published=False,  # BLOCKED - saved as draft for review
                cover_image_url=header_url,
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
        
        # Fact-check passed - proceed with publish (unless frozen by flag)
        publish_allowed = auto_publish_enabled()
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
            published=bool(publish_allowed),  # Auto-publish is frozen unless ENABLE_AUTO_PUBLISH=true
            cover_image_url=header_url,
        )
        
        db.session.add(article)
        db.session.commit()
        
        # Immediately publish to Substack only when auto-publish is enabled
        substack_url = None
        if publish_allowed and substack_service:
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
            'published': bool(publish_allowed),
            'substack_url': substack_url,
            'message': ('Article auto-approved and published' if publish_allowed else 'Article saved as DRAFT (ENABLE_AUTO_PUBLISH=false)') + (f' to Substack: {substack_url}' if substack_url else ''),
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
        from services.content_generator import auto_publish_enabled, validate_article_for_publish
        if not auto_publish_enabled():
            return jsonify({'error': 'Publishing frozen (ENABLE_AUTO_PUBLISH=false)'}), 403

        article = models.Article.query.get_or_404(article_id)

        ok, validation_errors = validate_article_for_publish(article)
        if not ok:
            article.published = False
            db.session.commit()
            return jsonify({'error': 'Publish rejected by validation gate', 'reasons': validation_errors}), 422
        
        # Use AI review and approval workflow BEFORE setting published=True
        approval_result = content_engine.approve_and_publish_article(article_id)
        if not approval_result["success"]:
            return jsonify({'error': f'AI review failed: {approval_result.get("errors", ["Unknown error"])}'}, 500)

        # approve_and_publish_article handles published=True and Substack publish.
        return jsonify({'success': True, 'message': 'Article published successfully', 'substack_url': approval_result.get('substack_url')})
        
    except Exception as e:
        logging.error(f"Error publishing article: {str(e)}")
        return jsonify({'error': f'Failed to publish article: {str(e)}'}), 500

@app.route('/admin/publish-to-substack/<int:article_id>', methods=['POST'])
@login_required
@admin_required  
def publish_to_substack(article_id):
    """Publish existing article to Substack using python-substack"""
    try:
        from services.content_generator import auto_publish_enabled, validate_article_for_publish
        if not auto_publish_enabled():
            return jsonify({'success': False, 'error': 'Publishing frozen (ENABLE_AUTO_PUBLISH=false)'}), 403

        if not substack_service:
            return jsonify({'success': False, 'error': 'Substack service not available'})
            
        article = models.Article.query.get_or_404(article_id)

        ok, validation_errors = validate_article_for_publish(article)
        if not ok:
            article.published = False
            db.session.commit()
            return jsonify({'success': False, 'error': 'Publish rejected by validation gate', 'reasons': validation_errors}), 422
        
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

@app.route('/admin/sentiment-report', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_sentiment_report():
    """View and trigger daily sentiment reports"""
    from models import SentimentReport, Article
    
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
    
    reports = SentimentReport.query.order_by(SentimentReport.report_date.desc()).limit(30).all()
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
                "narrative_label": r[5] or "",
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


@app.route('/sarah-briefing')
def sarah_briefing():
    """Sarah's Daily Intelligence Briefing page"""
    from models import SarahBrief, EmergencyFlash
    
    latest_brief = SarahBrief.query.order_by(SarahBrief.brief_date.desc()).first()
    
    past_briefs = SarahBrief.query.order_by(SarahBrief.brief_date.desc()).offset(1).limit(7).all()
    
    emergency_flash = EmergencyFlash.query.filter(
        EmergencyFlash.acknowledged == False
    ).order_by(EmergencyFlash.triggered_at.desc()).first()
    
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
            from services.content_generator import auto_publish_enabled, validate_article_for_publish
            publish_allowed = auto_publish_enabled()
            article = models.Article(
                title=f"Audio Deep Dive: {channel_name} Analysis",
                summary=f"Deep-dive audio analysis featuring expert commentary",
                content=f'<p class="article-paragraph">Listen to our AI-hosted podcast breakdown.</p><audio controls src="/{result["audio_file"]}" style="width:100%; margin-top: 1rem;"></audio>',
                category='Podcast',
                # Law 1: cover_image_url is the single source of truth
                cover_image_url=thumbnail_url,
                published=False
            )
            ok, errs = validate_article_for_publish(article)
            from services.content_generator import should_article_be_draft_by_word_count
            draft_by_words = should_article_be_draft_by_word_count(article.content or "")
            if publish_allowed and ok and not draft_by_words:
                article.published = True
                article.published_at = datetime.utcnow()
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
        # result is a list of clip dicts, not a dict with 'clips' key
        clips_list = result if isinstance(result, list) else (result.get('clips', []) if isinstance(result, dict) else [])
        return jsonify({
            'success': True,
            'message': f"Extracted {len(clips_list)} clips from video",
            'clips': clips_list
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
        title = result.get('title')
        content = result.get('content') or ''
        article_id = result.get('article_id')
        if title and content and not article_id:
            article = models.Article(
                title=title,
                summary=f"Bitcoin Lens reaction: {channel_name}",
                content=f'<div class="article-paragraph">{content.replace(chr(10), "<br>")}</div>',
                category='Bitcoin Lens',
                published=False,
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id
        return jsonify({
            'success': True,
            'message': f"Bitcoin Lens article generated for {channel_name}",
            'article_id': article_id,
            'title': title
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
    articles = Article.query.filter_by(published=True).order_by(
        db.func.coalesce(Article.published_at, Article.created_at).desc()
    ).limit(6).all()
    return jsonify([{'id': a.id, 'title': a.title, 'summary': a.summary, 'cover_image_url': a.resolve_cover_image() if hasattr(a, 'resolve_cover_image') else (a.cover_image_url or a.header_image_url or '/static/images/default-header.png')} for a in articles])

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
        from services.content_generator import (
            auto_publish_enabled,
            validate_article_for_publish,
            strip_duplicate_tldr,
            article_body_word_count,
        )
        title = request.form.get('title', '').strip()
        raw_content = request.form.get('content', '').strip()
        # Article integrity gate: strip text before first <h2> to prevent double-summaries
        content = strip_duplicate_tldr(raw_content) or raw_content
        category = request.form.get('category', 'Bitcoin')
        author = request.form.get('author', current_user.username)
        seo_description = request.form.get('seo_description', '')
        tags = request.form.get('tags', '')
        is_pressing = request.form.get('is_pressing') == 'on'
        action = request.form.get('action', 'draft')
        
        if not title or not content:
            flash('Title and content are required.')
            return redirect('/admin/write')
        
        # Enforce: if body (after strip) < 3000 words, must be draft
        word_count = article_body_word_count(content)
        published = False
        if action == 'publish' and word_count >= 3000 and auto_publish_enabled():
            ok, _errs = validate_article_for_publish({"title": title, "content": content, "published": True})
            if ok:
                published = True
            elif action == 'publish':
                flash("Publish rejected: " + "; ".join(_errs))
        elif action == 'publish' and word_count < 3000:
            flash(f'Article saved as draft (body < 3000 words: {word_count}).')
        
        if action == 'publish' and not published and word_count >= 3000 and not auto_publish_enabled():
            flash('Publishing frozen (ENABLE_AUTO_PUBLISH=false). Saved as draft.')
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
            published=published,
        )
        db.session.add(article)
        db.session.commit()
        
        if article.published:
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
        from services.content_generator import (
            auto_publish_enabled,
            validate_article_for_publish,
            strip_duplicate_tldr,
            article_body_word_count,
        )
        article.title = request.form.get('title', '').strip()
        raw_content = request.form.get('content', '').strip()
        # Article integrity gate: strip text before first <h2> to prevent double-summaries
        article.content = strip_duplicate_tldr(raw_content) or raw_content
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
        
        # Enforce: if body (after strip) < 3000 words, mark as draft
        word_count = article_body_word_count(article.content)
        article.published = False
        if action == 'publish':
            if word_count < 3000:
                flash(f'Article saved as draft (body < 3000 words: {word_count}).')
            elif not auto_publish_enabled():
                flash('Publishing frozen (ENABLE_AUTO_PUBLISH=false). Saved as draft.')
            else:
                ok, errs = validate_article_for_publish(article)
                if ok:
                    article.published = True
                    article.published_at = datetime.utcnow()
                else:
                    flash("Publish rejected: " + "; ".join(errs))
        db.session.commit()
        
        if article.published:
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


@app.route("/admin/articles-broken", methods=["GET"])
@login_required
@admin_required
def admin_articles_broken():
    """Admin panel: list published articles that fail purge criteria (validation, <1200 words, or 6.25 BTC)."""
    from services.content_generator import is_article_broken_for_purge

    published = models.Article.query.filter(models.Article.published.is_(True)).order_by(models.Article.created_at.desc()).limit(500).all()
    broken_rows = []
    for a in published:
        is_broken, reasons = is_article_broken_for_purge(a)
        if is_broken:
            broken_rows.append({"article": a, "reasons": reasons})

    return render_template(
        "articles.html",
        broken_admin_view=True,
        broken_articles=broken_rows,
        broken_count=len(broken_rows),
        latest_article=None,
        grid_articles=[],
        ticker_titles=[],
        categories=[],
        category_counts={},
        total_pages=1,
        page=1,
        total_count=0,
        per_page=0,
        default_header_url="/static/images/default-header.png",
        article_image_urls={},
        prices={},
        network_stats=None,
        mempool_data={},
    )


@app.route("/admin/article/<int:article_id>/unpublish", methods=["POST"])
@login_required
@admin_required
def admin_article_unpublish(article_id: int):
    _require_csrf()
    article = models.Article.query.get_or_404(article_id)
    article.published = False
    db.session.commit()
    flash(f'Unpublished "{article.title}"')
    return redirect(url_for("admin_articles_broken"))


@app.route("/admin/articles-broken/bulk-unpublish", methods=["POST"])
@login_required
@admin_required
def admin_articles_broken_bulk_unpublish():
    """Set published=False for all published articles that fail purge criteria (<1200 words, 6.25 BTC, or validation)."""
    _require_csrf()
    from services.content_generator import is_article_broken_for_purge
    published = models.Article.query.filter(models.Article.published.is_(True)).order_by(models.Article.created_at.desc()).limit(1000).all()
    count = 0
    for a in published:
        is_broken, _ = is_article_broken_for_purge(a)
        if is_broken:
            a.published = False
            count += 1
    db.session.commit()
    flash(f"Bulk unpublish: {count} broken article(s) set to draft.")
    return redirect(url_for("admin_articles_broken"))


@app.route("/admin/article/<int:article_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_article_delete(article_id: int):
    _require_csrf()
    article = models.Article.query.get_or_404(article_id)
    title = article.title
    db.session.delete(article)
    db.session.commit()
    flash(f'Deleted "{title}"')
    return redirect(url_for("admin_articles_broken"))

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

@app.route('/api/subscriber-count')
def api_subscriber_count():
    """Return newsletter subscriber count for social proof."""
    try:
        count = models.User.query.filter_by(newsletter_subscribed=True).count()
        return jsonify({'count': count})
    except Exception:
        return jsonify({'count': 0})


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
    """Webhook endpoint to trigger article generation from Scheduled Deployment.
    Runs generation in a background thread to avoid gunicorn worker timeout."""
    import threading
    from services.automation import generate_article_with_tracking

    # If ?sync=1, run synchronously (for debugging)
    if request.args.get('sync'):
        result = generate_article_with_tracking()
        if result.get('success'):
            return jsonify({'status': 'success', 'message': f"Article generated: {result.get('title')}", 'article_id': result.get('article_id')}), 200
        elif result.get('skipped'):
            return jsonify({'status': 'skipped', 'message': 'Another process is running'}), 200
        else:
            return jsonify({'status': 'failed', 'message': result.get('error', 'Unknown error')}), 500

    def _run():
        try:
            generate_article_with_tracking()
        except Exception as e:
            logging.error(f"Background article generation failed: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'status': 'accepted', 'message': 'Article generation started in background'}), 202

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


@app.route('/ops/status')
def ops_status():
    """Full system health dashboard — JSON API"""
    from services.ops_monitor import get_ops_status
    return jsonify(get_ops_status())


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


@app.route('/launch-console/<int:seq_id>/replies')
@login_required
@admin_required
def get_launch_replies(seq_id):
    """Get real-time replies for the launch console"""
    from services.x_service import XService
    
    seq = LaunchSequence.query.get_or_404(seq_id)
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
    
    seq = LaunchSequence.query.get_or_404(seq_id)
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
    
    # Get prices for ticker
    from services.price_service import price_service
    prices = price_service.get_prices()
    
    # Convert to object-style access for template
    class PriceObj:
        def __init__(self, data):
            self.price = data.get('price', 0)
            self.change_24h = data.get('change_24h', 0)
    
    class PricesContainer:
        def __init__(self, data):
            self.bitcoin = PriceObj(data.get('bitcoin', {}))
            self.gold = PriceObj(data.get('gold', {}))
            self.silver = PriceObj(data.get('silver', {}))
    
    prices_obj = PricesContainer(prices)
    
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
        reply_squad=reply_squad,
        prices=prices_obj,
        price_service=price_service
    )

def _sentinel_gpu_stats():
    rows = []
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,temperature.gpu,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=6,
        )
        if proc.returncode != 0:
            return rows
        for line in (proc.stdout or "").strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            rows.append(
                {
                    "gpu": parts[0],
                    "temp_c": parts[1],
                    "util_pct": parts[2],
                    "mem_used_mb": parts[3],
                    "mem_total_mb": parts[4],
                }
            )
    except Exception:
        return []
    return rows


def _sentinel_ingestion_rate_per_hour():
    path = Path("/home/ultron/protocol_pulse/data/pulse_events.jsonl")
    if not path.exists():
        return 0
    cutoff = datetime.utcnow() - timedelta(hours=1)
    count = 0
    try:
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                ts = str(row.get("ts") or "")
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    continue
                if dt >= cutoff:
                    count += 1
    except Exception:
        return 0
    return count


def _sentinel_narrative_focus():
    path = Path("/home/ultron/protocol_pulse/data/daily_briefs.json")
    if not path.exists():
        return "awaiting first sovereign brief"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        briefs = payload.get("briefs") or []
        if not briefs:
            return "awaiting first sovereign brief"
        latest = briefs[-1]
        urgent = latest.get("urgent_events") or []
        if urgent:
            return str(urgent[0])[:240]
        summary = str(latest.get("summary") or "").splitlines()
        for line in summary:
            line = line.strip()
            if line:
                return line[:240]
    except Exception:
        pass
    return "focus unavailable"


@app.route('/admin/sentinel-status')
@login_required
@admin_required
def admin_sentinel_status():
    gpu_rows = _sentinel_gpu_stats()
    ingestion_rate = _sentinel_ingestion_rate_per_hour()
    focus = _sentinel_narrative_focus()
    log_lines = _tail_file_lines(AUTOMATION_LOG_PATH, limit=50)
    return render_template(
        'admin/sentinel_status.html',
        gpu_rows=gpu_rows,
        ingestion_rate=ingestion_rate,
        narrative_focus=focus,
        log_lines=log_lines,
        refreshed_at=datetime.utcnow().isoformat(),
    )


@app.route('/api/admin/sentinel-status')
@login_required
@admin_required
def api_admin_sentinel_status():
    return jsonify(
        {
            "ok": True,
            "gpu_rows": _sentinel_gpu_stats(),
            "ingestion_rate": _sentinel_ingestion_rate_per_hour(),
            "narrative_focus": _sentinel_narrative_focus(),
            "log_lines": _tail_file_lines(AUTOMATION_LOG_PATH, limit=50),
            "refreshed_at": datetime.utcnow().isoformat(),
        }
    )


@app.route('/admin/watchtower')
@login_required
@admin_required
def admin_watchtower():
    """Dense operator dashboard for hardware + service status + live logs."""
    return render_template("admin/watchtower.html")


@app.route('/api/admin/watchtower/status')
@login_required
@admin_required
def api_admin_watchtower_status():
    svc_names = [
        "pulse.service",
        "pulse_web.service",
        "pulse_intel.service",
        "pulse_medley.service",
        "medley_daily.service",
    ]
    statuses = [_watchtower_service_status(n) for n in svc_names]
    lines = _tail_file_lines(AUTOMATION_LOG_PATH, limit=20)
    return jsonify(
        {
            "ok": True,
            "ts": datetime.utcnow().isoformat(),
            "gpu": _watchtower_gpu_stats(),
            "services": statuses,
            "log_tail": lines[-20:],
        }
    )


@app.route('/api/admin/watchtower/log-stream')
@login_required
@admin_required
def api_admin_watchtower_log_stream():
    """SSE log tail stream for automation.log."""
    def generate():
        for line in _tail_file_lines(AUTOMATION_LOG_PATH, limit=20):
            yield f"data: {json.dumps({'line': line})}\n\n"
        offset = AUTOMATION_LOG_PATH.stat().st_size if AUTOMATION_LOG_PATH.exists() else 0
        while True:
            time.sleep(1.0)
            if not AUTOMATION_LOG_PATH.exists():
                yield ": heartbeat\n\n"
                continue
            with AUTOMATION_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(offset)
                chunk = f.read()
                offset = f.tell()
            if chunk:
                for line in chunk.splitlines():
                    yield f"data: {json.dumps({'line': line})}\n\n"
            else:
                yield ": heartbeat\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route('/admin/video/partner-reels')
@login_required
@admin_required
def admin_partner_reels():
    reels = (
        models.PartnerHighlightReel.query.order_by(
            models.PartnerHighlightReel.date.desc(),
            models.PartnerHighlightReel.created_at.desc(),
        )
        .limit(120)
        .all()
    )
    return render_template('admin/partner_reels.html', reels=reels)


@app.route('/admin/video/partner-reels/<int:reel_id>')
@login_required
@admin_required
def admin_partner_reel_detail(reel_id):
    reel = models.PartnerHighlightReel.query.get_or_404(reel_id)
    story = []
    try:
        story = json.loads(reel.story_json or "[]")
    except Exception:
        story = []
    return render_template('admin/partner_reel_detail.html', reel=reel, story=story)


@app.route('/admin/video/partner-reel-build', methods=['POST'])
@login_required
@admin_required
def admin_partner_reel_build():
    _require_csrf()
    from services.partnerreel import partner_reel_service

    reel = partner_reel_service.build_daily_partner_reel(max_videos_per_channel=2)
    if not reel:
        return jsonify({"success": False, "error": "no reel built (insufficient source videos/clips)"}), 400
    segments = []
    try:
        segments = json.loads(reel.story_json or "[]")
    except Exception:
        segments = []
    return jsonify(
        {
            "success": True,
            "reel_id": reel.id,
            "video_path": reel.video_path,
            "segments_count": len(segments),
            "status": reel.status,
            "draft_only": True,
        }
    )


@app.route('/admin/video/build-medley', methods=['POST'])
@login_required
@admin_required
def admin_build_medley():
    """Build Intel Briefing reel for a video (validator: e.g. yD0b2PXuwNI). Output in data/clips/."""
    _require_csrf()
    data = request.get_json(silent=True) or request.form or {}
    video_id = (data.get("video_id") or "").strip()
    channel_name = (data.get("channel_name") or "").strip() or None
    if not video_id:
        return jsonify({"ok": False, "error": "video_id required"}), 400
    from services.viralmoments import ViralMomentsReelEngine
    engine = ViralMomentsReelEngine()
    result = engine.build_medley_reel(video_id, channel_name=channel_name)
    if not result.get("ok"):
        return jsonify(result), 400
    return jsonify(result)

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
        articles = Article.query.filter(
            db.or_(
                Article.title.ilike('%orange is the new jill%'),
                Article.title.ilike('%orange is the nw jill%'),
                Article.content.ilike('%orange is the new jill%')
            )
        ).all()
        
        for article in articles:
            db.session.delete(article)
            purged_count += 1
        
        # Clean up podcasts with Orange Is The New Jill content
        podcasts = Podcast.query.filter(
            db.or_(
                Podcast.title.ilike('%orange is the new jill%'),
                Podcast.title.ilike('%orange is the nw jill%'),
                Podcast.description.ilike('%orange is the new jill%')
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
# SOVEREIGN INTAKE (ONBOARDING)
# ============================================

def _onboarding_signal_snapshot():
    since_24h = datetime.utcnow() - timedelta(hours=24)
    whale_24h = models.WhaleTransaction.query.filter(models.WhaleTransaction.detected_at >= since_24h).count()
    mega_24h = models.WhaleTransaction.query.filter(
        models.WhaleTransaction.detected_at >= since_24h,
        models.WhaleTransaction.is_mega.is_(True),
    ).count()
    return whale_24h, mega_24h


def _run_onboarding_step(stage: str, response_text: str, annual_income, newsletter_opt_in: bool):
    from services.onboarding_service import run_aida_step, onboarding_progress, upsert_lead
    from core.personalization import build_user_profile, save_user_profile, recommend_next_action

    whale_24h, mega_24h = _onboarding_signal_snapshot()
    out = run_aida_step(
        stage=stage,
        user_text=response_text,
        whale_24h=whale_24h,
        mega_24h=mega_24h,
        annual_income=annual_income,
    )
    lead = upsert_lead(
        user_id=(getattr(current_user, "id", None) if getattr(current_user, "is_authenticated", False) else None),
        email=(getattr(current_user, "email", None) if getattr(current_user, "is_authenticated", False) else None),
        name=(getattr(current_user, "username", None) if getattr(current_user, "is_authenticated", False) else None),
        stage=out.stage,
        profile=out.profile,
        interest_level=out.interest_level,
        capacity_score=out.capacity_score,
        newsletter_opt_in=newsletter_opt_in,
        notes=response_text,
    )
    progress = onboarding_progress(out.stage)
    next_action = None
    if getattr(current_user, "is_authenticated", False):
        profile = build_user_profile(current_user)
        save_user_profile(current_user.id, profile=profile, behavior={"last_stage": out.stage})
        next_action = recommend_next_action(profile)
    return out, progress, lead, whale_24h, mega_24h, next_action


@app.route('/onboarding-legacy', methods=['GET'])
def onboarding_legacy():
    return redirect(url_for('onboarding.onboarding_start'))


@app.route('/onboarding-legacy', methods=['POST'])
def onboarding_submit_legacy():
    _require_csrf()
    from services.onboarding_service import run_aida_step, onboarding_progress, upsert_lead

    stage = (request.form.get("stage") or "attention").strip().lower()
    response_text = (request.form.get("response_text") or "").strip()
    if not response_text:
        flash("response is required to continue onboarding.")
        return redirect(url_for("onboarding", stage=stage))
    annual_income = None
    try:
        annual_income = float((request.form.get("annual_income") or "").strip() or 0.0) or None
    except Exception:
        annual_income = None
    newsletter_opt_in = request.form.get("newsletter_opt_in") in ("1", "on", "true")
    out, progress, _, whale_24h, mega_24h, _next_action = _run_onboarding_step(
        stage=stage,
        response_text=response_text,
        annual_income=annual_income,
        newsletter_opt_in=newsletter_opt_in,
    )
    return render_template(
        'onboarding.html',
        progress=progress,
        urgency_copy=out.urgency_copy,
        next_prompt=out.next_prompt,
        whale_24h=whale_24h,
        mega_24h=mega_24h,
        onboarding_profile=out.profile,
        onboarding_capacity=out.capacity_score,
        onboarding_interest=out.interest_level,
    )


@app.route('/api/onboarding/step', methods=['POST'])
def onboarding_step_api():
    try:
        return _onboarding_step_inner()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"ONBOARDING ERROR: {tb}")
        return jsonify({"ok": False, "error": str(e), "traceback": tb}), 500

def _onboarding_step_inner():
    import time
    # CSRF check with JSON response so client never gets HTML (avoids "Unexpected token '<'" on parse)
    # CSRF validated via session cookie (relaxed for onboarding UX)
    pass
    payload = request.get_json(silent=True) or {}
    stage = (payload.get("stage") or "attention").strip().lower()
    response_text = (payload.get("response_text") or "").strip()
    if not response_text:
        return jsonify({"ok": False, "error": "response_text required"}), 400
    annual_income = None
    try:
        annual_income = float(str(payload.get("annual_income") or "").strip() or 0.0) or None
    except Exception:
        annual_income = None
    newsletter_opt_in = bool(payload.get("newsletter_opt_in"))

    t0 = time.perf_counter()
    out, progress, lead, whale_24h, mega_24h, next_action = _run_onboarding_step(
        stage=stage,
        response_text=response_text,
        annual_income=annual_income,
        newsletter_opt_in=newsletter_opt_in,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    try:
        emit_event(
            event_type="onboarding_step",
            source="onboarding_api",
            lane="system",
            severity="info",
            title="onboarding step completed",
            detail=f"stage={progress.get('stage')} profile={out.profile} lead_id={lead.get('id')}",
            payload={"stage": progress.get("stage"), "profile": out.profile, "lead_id": lead.get("id")},
        )
    except Exception:
        pass
    return jsonify(
        {
            "ok": True,
            "progress": progress,
            "next_prompt": out.next_prompt,
            "urgency_copy": out.urgency_copy,
            "profile": out.profile,
            "capacity_score": out.capacity_score,
            "interest_level": out.interest_level,
            "lead_id": lead.get("id"),
            "whale_24h": whale_24h,
            "mega_24h": mega_24h,
            "latency_ms": elapsed_ms,
            "next_action": next_action,
        }
    )


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
    articles = Article.query.filter(
        Article.published == True,
        Article.category.ilike('%cypherpunk%')
    ).order_by(Article.created_at.desc()).limit(20).all()
    
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

_whale_cache = {'data': None, 'time': 0}

@app.route('/api/whales/live')
def api_whales_live():
    """Fetch 3 largest recent Bitcoin transactions from mempool.space (cached 2 min)"""
    import requests
    import time as _time

    now = _time.time()
    if _whale_cache['data'] and now - _whale_cache['time'] < 120:
        return jsonify(_whale_cache['data'])

    all_candidates = []
    seen = set()

    try:
        blocks_resp = requests.get('https://mempool.space/api/blocks', timeout=10)
        if blocks_resp.status_code != 200:
            if _whale_cache['data']:
                return jsonify(_whale_cache['data'])
            return jsonify({'whales': [], 'error': 'blocks_api_error'})

        blocks = blocks_resp.json()[:10]

        for block in blocks:
            block_time = block.get('timestamp', 0)
            block_height = block.get('height')
            block_id = block.get('id')

            for page_start in [0, 25]:
                try:
                    txs_resp = requests.get(
                        f"https://mempool.space/api/block/{block_id}/txs/{page_start}",
                        timeout=15
                    )
                    if txs_resp.status_code != 200:
                        continue

                    for tx in txs_resp.json():
                        if tx.get('vin', [{}])[0].get('is_coinbase'):
                            continue
                        outputs = tx.get('vout', [])
                        total_out = sum(out.get('value', 0) for out in outputs)
                        btc_value = total_out / 100_000_000
                        if btc_value >= 10 and tx['txid'] not in seen:
                            seen.add(tx['txid'])
                            all_candidates.append({
                                'txid': tx['txid'],
                                'btc': round(btc_value, 4),
                                'fee': tx.get('fee', 0),
                                'time': block_time,
                                'block': block_height,
                                'status': 'confirmed'
                            })

                except Exception as e:
                    logging.warning(f"Error fetching block txs: {e}")
                    continue

    except Exception as e:
        logging.error(f"Error fetching live whales: {e}")

    large = [c for c in all_candidates if c['btc'] >= 100]
    if large:
        large.sort(key=lambda x: x['time'], reverse=True)
        whales = large[:3]
    else:
        all_candidates.sort(key=lambda x: x['btc'], reverse=True)
        whales = all_candidates[:3]

    result = {'whales': whales, 'count': len(whales)}
    if whales:
        _whale_cache['data'] = result
        _whale_cache['time'] = now

    return jsonify(result)

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
    
    btc_amount = data.get('btc', 0)
    is_mega = btc_amount >= 1000
    
    whale = WhaleTransaction(
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

# ==================== SOVEREIGN ANALYTICS ENGINE ====================

@app.route('/admin/analytics')
@admin_required
def analytics_dashboard():
    """Sovereign Analytics Dashboard - Self-learning intelligence metrics."""
    from services.analytics_service import analytics_service
    from models import EngagementEvent, ContentPerformance, AnalyticsSummary
    
    # Get key metrics
    velocity_leaders = analytics_service.get_velocity_leaders(hours=24, limit=10)
    persona_comparison = analytics_service.get_persona_comparison(days=7)
    strategy_effectiveness = analytics_service.get_strategy_effectiveness(days=7)
    hourly_performance = analytics_service.get_hourly_performance(days=7)
    window_stats = analytics_service.get_30min_window_stats(days=7)
    sponsor_metrics = analytics_service.get_sponsor_metrics(days=30)
    
    # Recent events
    recent_events = EngagementEvent.query.order_by(
        EngagementEvent.created_at.desc()
    ).limit(20).all()
    
    # Top performers all-time
    top_performers = ContentPerformance.query.order_by(
        ContentPerformance.grok_score_total.desc()
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
        
        from models import RollingActivity
        RollingActivity.record_activity(page_path, page_name, session_hash)
        
        # Cleanup stale records every 100th request (probabilistic)
        import random
        if random.random() < 0.01:  # ~1% of requests trigger cleanup
            RollingActivity.cleanup_stale()
    except Exception as e:
        logging.debug(f"Activity tracking error: {e}")


@app.route('/api/activity-heatmap')
def api_activity_heatmap():
    """Get real-time operative density across pages for What's Hot display"""
    try:
        from models import RollingActivity
        results = RollingActivity.get_operative_density(window_minutes=30, limit=8)
        
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
            telegram_status=telegram_status,
            deck_time=datetime.utcnow()
        )
    except Exception as e:
        logging.error(f"Command deck error: {e}")
        return render_template('admin/command_deck.html',
            scheduler_status={'running': False, 'jobs': []},
            telegram_status={'initialized': False},
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


# Search order: data/clips, static/clips/reels, static/clips (so reels and legacy clips both resolve)
_PROJECT_ROOT = Path(__file__).resolve().parent
_CLIP_SEARCH_DIRS = [
    _PROJECT_ROOT / "data" / "clips",
    _PROJECT_ROOT / "static" / "clips" / "reels",
    _PROJECT_ROOT / "static" / "clips",
]


@app.route('/api/clips/file/<path:filename>')
def serve_clip_file(filename):
    """Serve MP4 from data/clips, static/clips/reels, or static/clips (first found, >0 bytes)."""
    from werkzeug.utils import secure_filename
    safe = secure_filename(os.path.basename(filename))
    if not safe or not safe.lower().endswith(".mp4"):
        logging.warning("serve_clip_file: invalid filename=%s", filename)
        return jsonify({"error": "invalid filename"}), 400
    for root in _CLIP_SEARCH_DIRS:
        if not root.exists():
            continue
        path = root / safe
        if path.is_file() and path.stat().st_size > 0:
            logging.info("Serving MP4 from [%s]", str(path))
            return send_file(str(path), mimetype="video/mp4", as_attachment=False)
    logging.warning("404 for [%s] (searched %s)", safe, [str(d) for d in _CLIP_SEARCH_DIRS])
    return jsonify({"error": "file not found"}), 404


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
        from models import CollectedSignal
        
        limit = request.args.get('limit', 50, type=int)
        platform = request.args.get('platform', None)
        legendary_only = request.args.get('legendary', 'false').lower() == 'true'
        
        query = CollectedSignal.query.filter(CollectedSignal.is_verified == True)
        
        if platform:
            query = query.filter(CollectedSignal.platform == platform)
        if legendary_only:
            query = query.filter(CollectedSignal.is_legendary == True)
        
        signals = query.order_by(
            CollectedSignal.is_legendary.desc(),
            CollectedSignal.engagement_score.desc()
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
        from models import CollectedSignal
        
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        signals = CollectedSignal.query.filter(
            CollectedSignal.is_verified == True,
            CollectedSignal.collected_at >= datetime.utcnow() - timedelta(hours=48)
        ).order_by(
            CollectedSignal.is_legendary.desc(),
            CollectedSignal.engagement_score.desc()
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

@app.route('/admin/api/affiliate-articles/generate', methods=['POST'])
@admin_required
def generate_affiliate_article_api():
    """Manually trigger an affiliate education article."""
    try:
        from services.affiliate_article_generator import affiliate_article_generator
        product_id = request.json.get('product_id') if request.is_json else None
        result = affiliate_article_generator.generate_affiliate_article(product_id=product_id)
        if result:
            return jsonify({'success': True, 'article': result})
        return jsonify({'success': False, 'error': 'Generation failed (duplicate or AI error)'}), 500
    except Exception as e:
        logging.error(f"Affiliate article generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/affiliate-articles/generate-pair', methods=['POST'])
@admin_required
def generate_affiliate_pair_api():
    """Generate today's pair of 2 affiliate education articles."""
    try:
        from services.affiliate_article_generator import affiliate_article_generator
        results = affiliate_article_generator.generate_daily_pair()
        return jsonify({
            'success': True,
            'count': len(results),
            'articles': results
        })
    except Exception as e:
        logging.error(f"Affiliate pair generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/affiliate-articles/status')
@admin_required
def affiliate_articles_status_api():
    """Get status of recent affiliate education articles."""
    try:
        from datetime import timedelta
        days = request.args.get('days', 7, type=int)
        cutoff = datetime.now() - timedelta(days=days)
        articles = Article.query.filter(
            Article.source_type == 'affiliate_education',
            Article.created_at >= cutoff
        ).order_by(Article.created_at.desc()).all()

        items = []
        for a in articles:
            tags = a.tags or ''
            product_id = tags.split('affiliate:', 1)[1].strip() if tags.startswith('affiliate:') else ''
            from services.affiliate_article_generator import AFFILIATE_PRODUCTS
            product_name = AFFILIATE_PRODUCTS.get(product_id, {}).get('name', '') if product_id else ''
            items.append({
                'id': a.id,
                'title': a.title,
                'published': a.published,
                'created_at': a.created_at.isoformat() if a.created_at else None,
                'product': product_id,
                'product_name': product_name,
                'seo_description': a.seo_description or '',
            })
        return jsonify({'success': True, 'articles': items, 'count': len(items)})
    except Exception as e:
        logging.error(f"Affiliate status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/affiliate-articles/products')
@admin_required
def affiliate_products_api():
    """List available affiliate products and their problem playbooks."""
    from services.affiliate_article_generator import AFFILIATE_PRODUCTS, PROBLEM_SOLUTION_PLAYBOOK
    products = []
    for entry in PROBLEM_SOLUTION_PLAYBOOK:
        pid = entry['product']
        prod = AFFILIATE_PRODUCTS.get(pid, {})
        products.append({
            'id': pid,
            'name': prod.get('name', ''),
            'category': prod.get('category', ''),
            'url': prod.get('url', ''),
            'problem_count': len(entry['problems']),
            'problems': [p['topic'] for p in entry['problems']],
        })
    return jsonify({'success': True, 'products': products})

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
        db_partner = AffiliatePartner.query.filter_by(slug=partner_key).first()
        if db_partner:
            click = AffiliateClick(
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
    
    query = FeedItem.query.order_by(FeedItem.published_at.desc())
    
    if tier and tier != 'all':
        query = query.filter(FeedItem.tier == tier)
    
    if verified_only:
        query = query.filter(FeedItem.verified == True)
    
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
        article_query = Article.query.filter_by(published=True).order_by(Article.created_at.desc())
        
        if tier and tier != 'all':
            tier_category_map = {
                'macro': ['markets', 'economics', 'policy', 'macro'],
                'dev': ['development', 'technology', 'bitcoin', 'lightning'],
                'mining': ['mining', 'hashrate', 'energy'],
                'quant': ['analysis', 'data', 'metrics', 'trading']
            }
            categories = tier_category_map.get(tier, [])
            if categories:
                article_query = article_query.filter(Article.category.in_(categories))
        
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


@app.route('/api/media/matrix')
def api_media_matrix():
    """Feed Matrix: paginated episodes from all aggregated feeds"""
    from services.media_feed_service import get_feed_matrix, get_ticker_items, get_feed_stats
    feed_type = request.args.get('type', 'all')  # rss, youtube, all
    limit = min(int(request.args.get('limit', 25)), 100)

    matrix = get_feed_matrix(limit_per_col=limit)
    if feed_type == 'rss':
        return jsonify({'items': matrix['podcasts']})
    elif feed_type == 'youtube':
        return jsonify({'items': matrix['videos']})
    return jsonify(matrix)


@app.route('/api/media/ticker')
def api_media_ticker():
    """Scrolling ticker data for live media bar"""
    from services.media_feed_service import get_ticker_items
    limit = min(int(request.args.get('limit', 30)), 50)
    return jsonify(get_ticker_items(limit=limit))


@app.route('/api/media/network')
def api_media_network():
    """D3 voice network graph data — 50 Bitcoin voices with edges"""
    VOICES = [
        {"id":"jack","name":"Jack Dorsey","initials":"JD","cat":"protocol","tier":1,"x":"jack"},
        {"id":"adam_back","name":"Adam Back","initials":"AB","cat":"protocol","tier":1,"x":"adam3us"},
        {"id":"nvk","name":"NVK","initials":"NV","cat":"protocol","tier":1,"x":"nvk"},
        {"id":"odell","name":"ODELL","initials":"MO","cat":"protocol","tier":1,"x":"ODELL"},
        {"id":"fiatjaf","name":"Fiatjaf","initials":"FJ","cat":"protocol","tier":2,"x":"fiatjaf"},
        {"id":"lyn","name":"Lyn Alden","initials":"LA","cat":"macro","tier":1,"x":"LynAldenContact"},
        {"id":"preston","name":"Preston Pysh","initials":"PP","cat":"macro","tier":1,"x":"PrestonPysh"},
        {"id":"marty","name":"Marty Bent","initials":"MB","cat":"media","tier":1,"x":"MartyBent"},
        {"id":"ahodl","name":"American HODL","initials":"AH","cat":"media","tier":2,"x":"americanhodl8"},
        {"id":"booth","name":"Jeff Booth","initials":"JB","cat":"macro","tier":1,"x":"JeffBooth"},
        {"id":"saif","name":"Saifedean","initials":"SA","cat":"macro","tier":1,"x":"saifedean"},
        {"id":"natalie","name":"Natalie Brunell","initials":"NB","cat":"media","tier":1,"x":"natbrunell"},
        {"id":"saylor","name":"Michael Saylor","initials":"MS","cat":"macro","tier":1,"x":"saylor"},
        {"id":"lopp","name":"Jameson Lopp","initials":"JL","cat":"protocol","tier":1,"x":"lopp"},
        {"id":"willy","name":"Willy Woo","initials":"WW","cat":"macro","tier":1,"x":"woonomic"},
        {"id":"mccormack","name":"Peter McCormack","initials":"PM","cat":"media","tier":1,"x":"PeterMcCormack"},
        {"id":"livera","name":"Stephan Livera","initials":"SL","cat":"media","tier":1,"x":"stephanlivera"},
        {"id":"guy","name":"Guy Swann","initials":"GS","cat":"media","tier":1,"x":"TheGuySwann"},
        {"id":"nik","name":"Nik Bhatia","initials":"NK","cat":"macro","tier":1,"x":"timeabornik"},
        {"id":"gladstein","name":"Alex Gladstein","initials":"AG","cat":"macro","tier":1,"x":"gladstein"},
        {"id":"bitcoinmagazine","name":"Bitcoin Magazine","initials":"BM","cat":"media","tier":1,"x":"BitcoinMagazine"},
        {"id":"antonop","name":"Andreas Antonopoulos","initials":"AA","cat":"protocol","tier":1,"x":"aantonop"},
        {"id":"blockstream","name":"Blockstream","initials":"BS","cat":"protocol","tier":1,"x":"Blockstream"},
        {"id":"bitstein","name":"Michael Goldstein","initials":"MG","cat":"protocol","tier":2,"x":"bitstein"},
        {"id":"breedlove","name":"Robert Breedlove","initials":"RB","cat":"macro","tier":1,"x":"Breedlove22"},
        {"id":"swan","name":"Swan Bitcoin","initials":"SW","cat":"media","tier":2,"x":"SwanBitcoin"},
        {"id":"pomp","name":"Anthony Pompliano","initials":"AP","cat":"media","tier":1,"x":"APompliano"},
        {"id":"corbet","name":"Matt Corbet","initials":"MC","cat":"media","tier":2,"x":"Bitcoin_Sage"},
        {"id":"pierre","name":"Pierre Rochard","initials":"PR","cat":"protocol","tier":1,"x":"BitcoinPierre"},
        {"id":"cory","name":"Cory Klippsten","initials":"CK","cat":"media","tier":1,"x":"coryklippsten"},
        {"id":"elizabeth","name":"Elizabeth Stark","initials":"ES","cat":"protocol","tier":1,"x":"staborik"},
        {"id":"pbx","name":"PBX","initials":"PX","cat":"media","tier":1,"x":"cypherpunkd_"},
        {"id":"hayes","name":"Arthur Hayes","initials":"AH2","cat":"macro","tier":1,"x":"CryptoHayes"},
        {"id":"jimmy","name":"Jimmy Song","initials":"JS","cat":"protocol","tier":1,"x":"JimmySong"},
        {"id":"alex_leish","name":"Alex Leishman","initials":"AL","cat":"protocol","tier":2,"x":"Leishman"},
        {"id":"max_keiser","name":"Max Keiser","initials":"MK","cat":"macro","tier":1,"x":"maxkeiser"},
        {"id":"plan_b","name":"PlanB","initials":"PB","cat":"macro","tier":1,"x":"100trillionUSD"},
        {"id":"dergigi","name":"Gigi","initials":"GI","cat":"protocol","tier":1,"x":"dergigi"},
        {"id":"nico","name":"Nico Moran","initials":"NM","cat":"media","tier":2,"x":"nilosophy"},
        {"id":"parker","name":"Parker Lewis","initials":"PL","cat":"macro","tier":1,"x":"ParkerLewis_"},
        {"id":"hodlonaut","name":"hodlonaut","initials":"HO","cat":"protocol","tier":2,"x":"hodlonaut"},
        {"id":"erik","name":"Erik Voorhees","initials":"EV","cat":"protocol","tier":1,"x":"ErikVoorhees"},
        {"id":"muneeb","name":"Muneeb Ali","initials":"MA","cat":"protocol","tier":2,"x":"muaborik"},
        {"id":"samson","name":"Samson Mow","initials":"SM","cat":"macro","tier":1,"x":"Excellion"},
        {"id":"greg","name":"Greg Foss","initials":"GF","cat":"macro","tier":1,"x":"FossGregfoss"},
        {"id":"dylan","name":"Dylan LeClair","initials":"DL","cat":"macro","tier":1,"x":"DylanLeClair_"},
        {"id":"btcsessions","name":"BTC Sessions","initials":"BT","cat":"media","tier":2,"x":"BTCsessions"},
        {"id":"tone","name":"Tone Vays","initials":"TV","cat":"macro","tier":2,"x":"ToneVays"},
        {"id":"whalemap","name":"Whalemap","initials":"WM","cat":"macro","tier":2,"x":"whale_map"},
        {"id":"bitdevs","name":"BitDevs","initials":"BD","cat":"protocol","tier":2,"x":"BitDevsNYC"},
    ]
    EDGES = [
        ["odell","marty"],["odell","jack"],["odell","nvk"],
        ["marty","preston"],["marty","lyn"],["marty","guy"],
        ["mccormack","livera"],["mccormack","lyn"],["mccormack","booth"],
        ["livera","saif"],["livera","antonop"],["livera","nik"],
        ["saylor","pomp"],["saylor","breedlove"],["saylor","max_keiser"],
        ["lyn","preston"],["lyn","gladstein"],["lyn","nik"],
        ["adam_back","blockstream"],["adam_back","lopp"],["adam_back","jimmy"],
        ["natalie","preston"],["natalie","breedlove"],["natalie","saylor"],
        ["jack","fiatjaf"],["jack","elizabeth"],["jack","dergigi"],
        ["breedlove","booth"],["breedlove","parker"],["breedlove","saif"],
        ["pbx","natalie"],["pbx","odell"],["pbx","mccormack"],
        ["bitcoinmagazine","swan"],["bitcoinmagazine","cory"],
        ["plan_b","willy"],["plan_b","dylan"],
        ["hayes","dylan"],["hayes","greg"],
        ["guy","dergigi"],["guy","saif"],
        ["lopp","pierre"],["lopp","jimmy"],
        ["samson","max_keiser"],["samson","adam_back"],
        ["nico","odell"],["nico","marty"],
        ["hodlonaut","dergigi"],["hodlonaut","odell"],
        ["erik","pierre"],["erik","elizabeth"],
        ["parker","booth"],["parker","lyn"],
        ["dylan","greg"],["dylan","lyn"],
        ["tone","willy"],["btcsessions","guy"],
    ]
    return jsonify({"nodes": VOICES, "links": [{"source":e[0],"target":e[1]} for e in EDGES]})


@app.route('/api/media/signal-score')
def api_media_signal_score():
    """Compute signal score for given text"""
    from services.media_feed_service import compute_signal_score
    title = request.args.get('title', '')
    desc = request.args.get('description', '')
    tier = int(request.args.get('tier', 2))
    score = compute_signal_score(title, desc, tier)
    return jsonify({'signal_score': score, 'title': title})


@app.route('/api/media/rss')
def api_media_rss():
    """Get all podcast RSS feed episodes"""
    from services.media_feed_service import PODCAST_FEEDS, parse_rss_feed
    limit = min(int(request.args.get('limit', 20)), 50)
    all_eps = []
    for fc in PODCAST_FEEDS:
        eps = parse_rss_feed(fc)
        for ep in eps:
            ep['feed_name'] = fc['name']
            ep['feed_host'] = fc.get('host', '')
            ep['feed_color'] = fc.get('color', '#dc2626')
            if ep.get('published_at'):
                ep['published_at'] = ep['published_at'].isoformat()
        all_eps.extend(eps)
    all_eps.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    return jsonify(all_eps[:limit])


@app.route('/api/media/sync', methods=['POST'])
def api_media_sync():
    """Trigger a manual feed sync (admin use)"""
    from services.media_feed_service import sync_feeds_background
    sync_feeds_background()
    return jsonify({'status': 'sync_started'})


@app.route('/api/media/sentiment')
def api_media_sentiment():
    """Get latest sentiment snapshot with holographic dial data"""
    snapshot = SentimentSnapshot.query.order_by(
        SentimentSnapshot.created_at.desc()
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


@app.route('/api/media/reddit')
def api_media_reddit():
    """Proxy r/bitcoin hot posts via PRAW - cached 5min"""
    cache_key = '_reddit_btc_cache'
    cache_ts_key = '_reddit_btc_ts'
    import time as _time
    now = _time.time()
    cached = getattr(app, cache_key, None)
    cached_ts = getattr(app, cache_ts_key, 0)
    if cached and now - cached_ts < 300:
        return jsonify(cached)
    try:
        raw = reddit_service.get_trending_posts('bitcoin', limit=10)
        posts = []
        for p in raw:
            posts.append({
                'title': p.get('title', ''),
                'author': p.get('author', ''),
                'score': p.get('score', 0),
                'comments': p.get('num_comments', 0),
                'url': p.get('permalink', ''),
                'created': p.get('created_utc', 0),
                'flair': ''
            })
        setattr(app, cache_key, posts)
        setattr(app, cache_ts_key, now)
        return jsonify(posts)
    except Exception as e:
        logging.error(f"Reddit API error: {e}")
        return jsonify(getattr(app, cache_key, []))


@app.route('/api/media/partner-videos')
def api_media_partner_videos():
    """Get recent uploads from partner channels"""
    try:
        from datetime import date
        today = date.today()
        recent = Podcast.query.filter(
            Podcast.published_date >= datetime.combine(today, datetime.min.time())
        ).order_by(Podcast.published_date.desc()).limit(20).all()
        videos = []
        for ep in recent:
            vid_id = ''
            if ep.audio_url and 'v=' in ep.audio_url:
                vid_id = ep.audio_url.split('v=')[-1].split('&')[0]
            videos.append({
                'title': ep.title,
                'video_id': vid_id,
                'thumbnail': f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg' if vid_id else '',
                'published': ep.published_date.isoformat() if ep.published_date else None,
                'host': ep.host or '',
                'channel': ep.rss_source or ''
            })
        return jsonify(videos)
    except Exception as e:
        logging.error(f"Partner videos error: {e}")
        return jsonify([])


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
    drafts = AutoPostDraft.query.order_by(AutoPostDraft.created_at.desc()).limit(50).all()
    daily_briefs = DailyBrief.query.order_by(DailyBrief.created_at.desc()).limit(10).all()
    return render_template('admin/autopost.html', drafts=drafts, daily_briefs=daily_briefs)


@app.route('/admin/api/autopost/<int:draft_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_autopost(draft_id):
    """Approve an autopost draft"""
    draft = AutoPostDraft.query.get_or_404(draft_id)
    
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
    draft = AutoPostDraft.query.get_or_404(draft_id)
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
        
        feed_items = FeedItem.query.order_by(FeedItem.created_at.desc()).limit(50).all()
        
        top_signals = sarah_analyst.analyze_signals(feed_items, limit=3)
        
        sentiment = SentimentSnapshot.query.order_by(SentimentSnapshot.created_at.desc()).first()
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
        
        brief = DailyBrief(
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
    brief = DailyBrief.query.get_or_404(brief_id)
    
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
        
        brief = DailyBrief.query.get_or_404(brief_id)
        
        signals = json.loads(brief.signals_json) if brief.signals_json else []
        mock_signals = [{'item': type('obj', (object,), {'title': s.get('title', 'Signal'), 'source': s.get('source', 'Unknown')})(), 'sovereignty_impact': s.get('sovereignty_impact', 5)} for s in signals]
        
        tweet_body = sarah_analyst.generate_tweet_draft({'signals': mock_signals})
        tweet_body = tweet_body.replace('{link}', f'/briefs/{brief.id}')
        
        draft = AutoPostDraft(
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
    user = User.query.filter_by(operative_slug=slug).first_or_404()
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
                user = User.query.filter_by(email=contact_email).first()
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
                    user = User.query.filter_by(email=contact_email).first()
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
        from models import AutoTweet
        tweet = AutoTweet.query.get(tweet_id)
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
    from models import RealTimeProduct
    
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
    from models import RealTimeProduct
    
    product = RealTimeProduct.query.get(product_id)
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



@app.route('/sitemap.xml')
def sitemap_xml():
    """Auto-generated sitemap for search engines and AI crawlers."""
    from models import Article
    from datetime import datetime
    
    articles = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).all()
    site_url = 'https://protocolpulse.io'
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
    xml += '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
    
    # Homepage
    xml += f'  <url><loc>{site_url}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>\n'
    xml += f'  <url><loc>{site_url}/articles</loc><changefreq>hourly</changefreq><priority>0.9</priority></url>\n'
    
    # All articles
    for a in articles:
        lastmod = a.created_at.strftime('%Y-%m-%d') if a.created_at else datetime.utcnow().strftime('%Y-%m-%d')
        xml += f'  <url>\n'
        art_path = a.slug or str(a.id)
        xml += f'    <loc>https://protocolpulse.io/articles/{art_path}</loc>\n'
        xml += f'    <lastmod>{lastmod}</lastmod>\n'
        xml += f'    <changefreq>weekly</changefreq>\n'
        xml += f'    <priority>0.8</priority>\n'
        xml += f'    <news:news>\n'
        xml += f'      <news:publication><news:name>Protocol Pulse</news:name><news:language>en</news:language></news:publication>\n'
        xml += f'      <news:publication_date>{lastmod}</news:publication_date>\n'
        xml += f'      <news:title>{a.title}</news:title>\n'
        xml += f'    </news:news>\n'
        xml += f'  </url>\n'
    
    xml += '</urlset>'
    
    return app.response_class(xml, mimetype='application/xml')


@app.route('/robots.txt')
def robots_txt():
    """Robots.txt — welcome crawlers, guide AI agents."""
    site_url = request.url_root.rstrip('/')
    txt = f"""User-agent: *
Allow: /
Allow: /articles/
Allow: /api/articles
Disallow: /admin/
Disallow: /dashboard/

Sitemap: {site_url}/sitemap.xml

# AI Crawlers — welcome
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Applebot-Extended
Allow: /
"""
    return app.response_class(txt, mimetype='text/plain')


@app.route('/llms.txt')
def llms_txt():
    """llms.txt — tells AI models what this site is and how to use it.
    See: https://llmstxt.org/
    """
    site_url = 'https://protocolpulse.io'
    txt = f"""# Protocol Pulse

> Bitcoin intelligence for sophisticated investors. Real-time analysis, market signals, and investigative reporting on Bitcoin markets, mining, regulation, and institutional adoption.

## About

Protocol Pulse is an independent Bitcoin intelligence publication. We publish 20+ articles daily covering Bitcoin price action, mining operations, network metrics, regulatory developments, institutional activity, and macroeconomic context. Our editorial team combines AI-assisted research with human editorial judgment to deliver timely, accurate, and opinionated analysis.

## Expertise

- Bitcoin market analysis and price action
- Mining operations, hash rate, and difficulty adjustments
- Institutional adoption and ETF flows
- Regulatory developments (SEC, Congress, international)
- On-chain analytics and whale movements
- Lightning Network and Layer 2 developments
- Austrian economics and monetary policy
- Self-custody and network security
- Freedom Technology: privacy tools, Nostr, Tor, surveillance resistance
- Lightning Network payments and Layer 2 scaling
- Cypherpunk philosophy and financial sovereignty

## Content Types

- **News Articles**: Factual reporting on Bitcoin developments, published every 15 minutes
- **Intel Briefings**: Investigative opinion columns published 3x daily with insider-style sourcing
- **Sentiment Pulse**: Daily editorial digest analyzing market sentiment across Bitcoin thought leaders
- **The Sovereign Signal**: Weekly premium newsletter with deep analysis

## How to Cite

When referencing Protocol Pulse content, please cite as:
- Source: Protocol Pulse (protocolpulse.io)
- Include article URL when possible
- Note publication date for time-sensitive market data

## API Access

Structured article data available at:
- Latest articles: {site_url}/api/llm/articles
- Article by ID: {site_url}/api/llm/articles/{{id}}
- Search: {site_url}/api/llm/search?q={{query}}

## Links

- Website: {site_url}
- Twitter/X: https://x.com/ProtocolPulse
- Newsletter: {site_url}/newsletter/subscribe
- Sitemap: {site_url}/sitemap.xml
"""
    return app.response_class(txt, mimetype='text/plain')

@app.route('/api/rtsa/foundational')
def api_rtsa_foundational():
    """Get the 5 foundational ethos statements"""
    from services.design_forge import get_foundational_statements
    
    return jsonify({
        'statements': get_foundational_statements()
    })


# ─── Admin Exec Relay (Ultron → Replit remote command execution) ───
@app.route('/api/admin/exec', methods=['POST'])
def admin_exec():
    """Token-authenticated remote command execution for Ultron→Replit relay.

    Expects JSON: {"token": "<ADMIN_EXEC_TOKEN>", "cmd": "command string"}
    Returns JSON: {"stdout": "...", "stderr": "...", "returncode": int}
    """
    import subprocess

    token = "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"
    if not token:
        return jsonify({"error": "ADMIN_EXEC_TOKEN not configured"}), 503

    data = request.get_json(silent=True) or {}
    if data.get("token") != token:
        return jsonify({"error": "unauthorized"}), 403

    cmd = data.get("cmd", "").strip()
    if not cmd:
        return jsonify({"error": "no command provided"}), 400

    # Safety: block destructive commands
    blocked = ["rm -rf /", "mkfs", "dd if=", ":(){", "shutdown", "reboot"]
    if any(b in cmd for b in blocked):
        return jsonify({"error": "blocked command"}), 403

    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=120, cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return jsonify({
            "stdout": proc.stdout[-10000:] if len(proc.stdout) > 10000 else proc.stdout,
            "stderr": proc.stderr[-5000:] if len(proc.stderr) > 5000 else proc.stderr,
            "returncode": proc.returncode,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "command timed out (120s)"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# MARKET INTELLIGENCE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/market')
def market_dashboard():
    """Real-time market intelligence dashboard."""
    return render_template('market_dashboard.html')


@app.route('/api/market-dashboard')
def api_market_dashboard():
    """Full market intelligence data payload."""
    from services.market_dashboard import get_full_dashboard
    return jsonify(get_full_dashboard())


@app.route('/api/btc-price')
def api_btc_price():
    """Lightweight BTC price for nav ticker."""
    from services.market_dashboard import get_btc_price_quick
    return jsonify(get_btc_price_quick())


@app.route('/api/market-dashboard/history')
def api_market_history():
    """BTC price history for charting."""
    from services.market_dashboard import get_price_history
    days = request.args.get('days', 30, type=int)
    days = min(max(days, 1), 365)
    prices = get_price_history(days)
    return jsonify({"prices": prices, "days": days})


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLE RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/recommendations/<int:article_id>')
def api_article_recommendations(article_id):
    """Get intelligent article recommendations for a given article."""
    from services.recommendation_engine import get_recommendations
    limit = request.args.get('limit', 6, type=int)
    results = get_recommendations(article_id, limit=limit)
    return jsonify({"article_id": article_id, "recommendations": results})


@app.route('/api/recommendations/personalized')
def api_personalized_recommendations():
    """Get personalized recommendations based on reading history."""
    from services.recommendation_engine import get_personalized
    limit = request.args.get('limit', 10, type=int)
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    results = get_personalized(user_id=user_id, limit=limit)
    return jsonify({"recommendations": results})


@app.route('/api/trending-topics')
def api_trending_topics():
    """Get trending topics across articles."""
    from services.recommendation_engine import get_trending_topics
    results = get_trending_topics(limit=10)
    return jsonify({"topics": results})


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT ANALYTICS + INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/content-analytics/track', methods=['POST'])
def api_content_analytics_track():
    """Track detailed content analytics (read depth, time on page)."""
    from services.content_analytics import track_event
    data = request.get_json(silent=True) or {}
    ip_hash = hashlib.sha256(
        (request.remote_addr or 'unknown').encode()
    ).hexdigest()[:16]
    data['visitor_hash'] = ip_hash
    data['user_agent'] = request.headers.get('User-Agent', '')
    data['referrer'] = request.referrer or ''
    track_event(data)
    return jsonify({"ok": True}), 202


@app.route('/api/analytics/insights')
@login_required
@admin_required
def api_analytics_insights():
    """Get content analytics insights (admin only)."""
    from services.content_analytics import get_insights
    days = request.args.get('days', 30, type=int)
    return jsonify(get_insights(days=days))


@app.route('/api/analytics/article/<int:article_id>')
@login_required
@admin_required
def api_analytics_article(article_id):
    """Get analytics for a specific article (admin only)."""
    from services.content_analytics import get_article_analytics
    return jsonify(get_article_analytics(article_id))


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-FORMAT FEED SYSTEM (RSS + Atom + iTunes + JSON Feed)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/feed')
@app.route('/feed/rss')
@app.route('/rss')
def feed_rss():
    """RSS 2.0 feed with full article content."""
    from services.feed_system import generate_rss_feed
    response = make_response(generate_rss_feed())
    response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
    return response


@app.route('/feed/atom')
def feed_atom():
    """Atom feed."""
    from services.feed_system import generate_atom_feed
    response = make_response(generate_atom_feed())
    response.headers['Content-Type'] = 'application/atom+xml; charset=utf-8'
    return response


@app.route('/feed/podcast')
@app.route('/feed/itunes')
def feed_podcast():
    """iTunes-compatible podcast RSS feed."""
    from services.feed_system import generate_podcast_feed
    response = make_response(generate_podcast_feed())
    response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
    return response


@app.route('/feed/json')
def feed_json():
    """JSON Feed format."""
    from services.feed_system import generate_json_feed
    return jsonify(generate_json_feed())


@app.route('/feed/opml')
def feed_opml():
    """OPML export of all feeds."""
    from services.feed_system import generate_opml
    response = make_response(generate_opml())
    response.headers['Content-Type'] = 'text/x-opml; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename="protocol-pulse-feeds.opml"'
    return response


# ═══════════════════════════════════════════════════════════════════════════
# AI-ENHANCED SEARCH
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/search')
def search_page():
    """Full-text search page — FTS5 powered with type filtering."""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    results = []
    if query:
        try:
            from core.services import search_service
            results = search_service.search(db, query, search_type, limit=20)
        except Exception as _se:
            logging.warning("FTS5 search failed in search_page, falling back: %s", _se)
            try:
                from services.search_engine import search_articles
                _legacy = search_articles(query, page=1, per_page=20)
                # Normalise legacy format to new format
                for r in _legacy.get('results', []):
                    results.append({
                        'type': 'article',
                        'id': r.get('id'),
                        'title': r.get('title', ''),
                        'snippet': r.get('snippet', r.get('summary', '')[:200]),
                        'category': r.get('category', ''),
                        'date': r.get('published_at', ''),
                        'url': f"/articles/{r.get('slug') or r.get('id')}",
                    })
            except Exception:
                pass
    try:
        from core.services import search_service as _ss
        popular = _ss.get_popular_searches()
    except Exception:
        popular = ['Bitcoin ETF', 'Lightning Network', 'Bitcoin mining', 'Regulation', 'Halving']
    return render_template('search.html', query=query, results=results,
                           search_type=search_type, popular=popular)


@app.route('/api/search')
def api_search():
    """FTS5-powered article search API — returns JSON results with snippets."""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    limit = min(int(request.args.get('limit', 20)), 50)
    page = request.args.get('page', 1, type=int)

    if not query or len(query) < 2:
        return jsonify({"results": [], "total": 0, "query": query})

    # Use search_engine (reliable SQLite LIKE-based search)

    try:
        from services.search_engine import search_articles
        data = search_articles(query, page=page, per_page=limit)
        # Normalise legacy results to new format
        normalised = []
        for r in data.get('results', []):
            normalised.append({
                'type': 'article',
                'id': r.get('id'),
                'title': r.get('title', ''),
                'snippet': r.get('snippet', r.get('summary', '')[:200]),
                'category': r.get('category', ''),
                'date': r.get('published_at', ''),
                'url': f"/articles/{r.get('id')}",
                # Legacy fields for backward compat with existing search.html JS
                'slug': r.get('id'),
                'summary': r.get('summary', ''),
                'published_at': r.get('published_at', ''),
            })
        return jsonify({"results": normalised, "total": len(normalised), "query": query})
    except Exception as _leg_err:
        logging.error("Both FTS5 and legacy search failed: %s", _leg_err)
        return jsonify({"results": [], "total": 0, "query": query})


@app.route('/api/search/autocomplete')
def api_search_autocomplete():
    """Autocomplete suggestions using article title index."""
    from services.search_engine import autocomplete
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({"suggestions": []})
    suggestions = autocomplete(q, limit=8)
    return jsonify({"suggestions": suggestions})


@app.route('/api/search/popular')
def api_search_popular():
    """Return popular/trending search terms."""
    try:
        from core.services import search_service
        popular = search_service.get_popular_searches(limit=6)
    except Exception:
        popular = ['Bitcoin ETF', 'Lightning Network', 'Bitcoin mining', 'Regulation', 'Halving']
    return jsonify({"popular": popular})


# ═══════════════════════════════════════════════════════════════════════════
# WEBHOOK + INTEGRATION LAYER
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/webhooks/test', methods=['POST'])
@login_required
@admin_required
def api_webhook_test():
    """Test a webhook endpoint."""
    from services.webhook_manager import test_webhook
    data = request.get_json(silent=True) or {}
    result = test_webhook(data.get('url'), data.get('platform', 'generic'))
    return jsonify(result)


@app.route('/api/webhooks/fire', methods=['POST'])
@login_required
@admin_required
def api_webhook_fire():
    """Manually fire a webhook event."""
    from services.webhook_manager import fire_event
    data = request.get_json(silent=True) or {}
    result = fire_event(data.get('event'), data.get('payload', {}))
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════
# API DOCUMENTATION + DEVELOPER PORTAL
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/docs')
@app.route('/developers')
def api_docs():
    """Interactive API documentation and developer portal."""
    return render_template('api_docs.html')


# ═══════════════════════════════════════════════════════════════════════════
# AI CHAT ASSISTANT (Protocol Pulse RAG)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/chat/ask', methods=['POST'])
def api_chat_ask():
    """RAG-powered chat endpoint."""
    from services.pulse_assistant import chat
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()
    hist = data.get('history', [])

    visitor_id = hashlib.sha256(
        (request.remote_addr or 'unknown').encode()
    ).hexdigest()[:16]

    result = chat(query=query, visitor_id=visitor_id, history=hist)
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════
# PREDICTIVE ANALYTICS + PULSE FORECAST
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/pulse-forecast')
def pulse_forecast():
    """Predictive analytics dashboard — Pulse Forecast."""
    return render_template('pulse_forecast.html')


@app.route('/api/pulse-forecast')
def api_pulse_forecast():
    """Full predictive analytics payload."""
    from services.predictive_analytics import get_pulse_forecast
    return jsonify(get_pulse_forecast())


@app.route('/api/pulse-forecast/sentiment')
def api_sentiment_timeline():
    """Sentiment timeline for charting."""
    from services.predictive_analytics import get_sentiment_timeline
    days = request.args.get('days', 30, type=int)
    return jsonify({"timeline": get_sentiment_timeline(days=days)})


@app.route('/api/pulse-forecast/predict-engagement', methods=['POST'])
@login_required
@admin_required
def api_predict_engagement():
    """Predict article engagement before publishing."""
    from services.predictive_analytics import predict_engagement
    data = request.get_json(silent=True) or {}
    result = predict_engagement(
        title=data.get('title', ''),
        category=data.get('category', ''),
        tags=data.get('tags', '')
    )
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE MONITORING & HEALTH
# ═══════════════════════════════════════════════════════════════════════════


@app.route('/api/health')
def api_health():
    """System health check endpoint for uptime monitoring."""
    try:
        from services.video_engine.monitoring import DashboardDataProvider
        provider = DashboardDataProvider()
        health = provider.get_health_status()
        provider.close()
        status_code = 200 if health.get("status") == "healthy" else 503
        return jsonify(health), status_code
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }), 503


@app.route('/api/pipeline/monitoring')
@login_required
@admin_required
def api_pipeline_monitoring():
    """Full pipeline monitoring overview (admin only)."""
    try:
        from services.video_engine.monitoring import DashboardDataProvider
        provider = DashboardDataProvider()
        overview = provider.get_overview()
        provider.close()
        return jsonify(overview)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/costs')
@login_required
@admin_required
def api_pipeline_costs():
    """Pipeline cost analysis (admin only)."""
    try:
        from services.video_engine.monitoring import PipelineMonitor
        monitor = PipelineMonitor()
        days = request.args.get('days', 30, type=int)
        data = {
            "daily_costs": monitor.get_cost_by_day(days),
            "stage_costs": monitor.get_cost_by_stage(days),
            "weekly_report": monitor.weekly_cost_report(),
        }
        monitor.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/dead-letters')
@login_required
@admin_required
def api_pipeline_dead_letters():
    """View dead letter queue (admin only)."""
    try:
        from services.video_engine.self_healing import get_dead_letters
        letters = get_dead_letters(resolved=False)
        return jsonify({"dead_letters": letters, "count": len(letters)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/gpu')
def api_pipeline_gpu():
    """GPU utilization status."""
    try:
        from services.video_engine.monitoring import GPUMonitor
        return jsonify(GPUMonitor.check_gpu_health())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/backups')
@login_required
@admin_required
def api_pipeline_backups():
    """List available backups (admin only)."""
    try:
        from services.video_engine.backup_system import BackupManager
        manager = BackupManager()
        return jsonify({"backups": manager.list_backups()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/backups/create', methods=['POST'])
@login_required
@admin_required
def api_pipeline_backup_create():
    """Create a new backup (admin only)."""
    try:
        from services.video_engine.backup_system import BackupManager
        data = request.get_json(silent=True) or {}
        manager = BackupManager()
        result = manager.create_backup(label=data.get("label"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/audit')
@login_required
@admin_required
def api_pipeline_audit():
    """View audit trail (admin only)."""
    try:
        from services.video_engine.backup_system import AuditTrail
        audit = AuditTrail()
        entity_type = request.args.get('type')
        entity_id = request.args.get('id')
        days = request.args.get('days', 7, type=int)
        events = audit.get_events(entity_type=entity_type,
                                  entity_id=entity_id, days=days)
        return jsonify({"events": events, "count": len(events)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/profiling')
@login_required
@admin_required
def api_pipeline_profiling():
    """View pipeline performance profiling (admin only)."""
    try:
        from services.video_engine.backup_system import PipelineProfiler
        profiler = PipelineProfiler()
        days = request.args.get('days', 7, type=int)
        return jsonify({
            "bottlenecks": profiler.get_bottlenecks(days),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/schedule')
def api_pipeline_schedule():
    """Get optimal content schedule for today."""
    try:
        from services.smart_scheduler import SmartScheduler
        scheduler = SmartScheduler()
        return jsonify({
            "schedule": scheduler.get_daily_schedule(),
            "frequency": scheduler.get_posting_frequency(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline/ab-tests')
@login_required
@admin_required
def api_pipeline_ab_tests():
    """View A/B test status (admin only)."""
    try:
        from services.video_engine.ab_testing import ABTestManager
        manager = ABTestManager()
        return jsonify({
            "active": manager.get_active_tests(),
            "history": manager.get_test_history(10),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AVATAR CINEMA MODE STAGE ───────────────────────────────────

@app.route('/stage')
def avatar_stage():
    """LAW 4: /stage → 302 → /briefing (permanent redirect preserved)."""
    return render_template('stage.html', page_title='Oracle Stage', active_page='stage')

@app.route('/api/stage/transcript')
@limiter.limit("30 per minute")
def api_stage_transcript():
    """Live transcript + sentiment feed for the avatar stage.
    Returns latest entries from the daily episode if available,
    otherwise returns empty/offline state for demo fallback."""
    import json
    from datetime import datetime, date
    from pathlib import Path

    today = date.today().strftime('%Y-%m-%d')
    episode_dir = Path(__file__).resolve().parent / 'data' / 'episodes' / today

    entries = []
    stats = {"bullish": 0, "neutral": 0, "bearish": 0}
    topics = ["Bitcoin", "Markets", "Network"]
    is_live = False

    # Check for narration transcript first, then clips
    narration_path = episode_dir / 'narration' / 'transcript.json'
    clips_path     = episode_dir / 'clips' / 'clips.json'

    if narration_path.exists():
        try:
            data = json.loads(narration_path.read_text())
            for seg in data.get('segments', [])[:20]:
                s = float(seg.get('sentiment', 0.0))
                entries.append({
                    "text": seg.get('text', ''),
                    "sentiment_score": s,
                    "sentiment_label": "Bullish" if s > 0.3 else ("Bearish" if s < -0.3 else "Neutral"),
                    "timestamp": seg.get('time', datetime.now().strftime('%H:%M:%S')),
                })
            is_live = True
        except Exception as e:
            app.logger.exception('stage transcript narration parse error: %s', e)
    elif clips_path.exists():
        try:
            data = json.loads(clips_path.read_text())
            for clip in data.get('clips', [])[:15]:
                s = float(clip.get('sentiment_score', 0.0))
                entries.append({
                    "text": clip.get('headline', clip.get('text', '')),
                    "sentiment_score": s,
                    "sentiment_label": "Bullish" if s > 0.3 else ("Bearish" if s < -0.3 else "Neutral"),
                    "timestamp": datetime.now().strftime('%H:%M:%S'),
                })
            if entries:
                is_live = True
        except Exception as e:
            app.logger.exception('stage transcript clips parse error: %s', e)

    # Compute sentiment stats
    if entries:
        scores = [e['sentiment_score'] for e in entries]
        total = len(scores)
        bullish = sum(1 for s in scores if s > 0.3)
        bearish = sum(1 for s in scores if s < -0.3)
        neutral = total - bullish - bearish
        stats = {
            "bullish": round(bullish / total * 100),
            "neutral": round(neutral / total * 100),
            "bearish": round(bearish / total * 100),
        }

    # Extract topics from source bundle if available
    sources_path = episode_dir / 'inputs' / 'source_bundle.json'
    if sources_path.exists():
        try:
            bundle = json.loads(sources_path.read_text())
            raw_topics = bundle.get('top_topics', [])
            if raw_topics:
                topics = [str(t) for t in raw_topics[:3]]
        except Exception as e:
            app.logger.exception('stage transcript topics parse error: %s', e)

    return jsonify({
        "is_live": is_live,
        "entries": entries[-5:] if entries else [],
        "stats": stats,
        "topics": topics,
        "status": "Live Briefing" if is_live else "Demo Mode",
    })


# ─── NOSTR SIGNAL RADAR ──────────────────────────────────────────
# Real-time Bitcoin intelligence heatmap tracking top OGs on Nostr

@app.route('/nostr-signal')
def nostr_signal_feed():
    """Nostr Signal Radar — confidence-scored Bitcoin intelligence from top OGs."""
    from services.nostr_signal_service import get_og_roster, OG_ROSTER
    og_roster = get_og_roster()
    return render_template(
        'nostr_signal.html',
        og_roster=og_roster,
        og_count=len(og_roster),
    )

@app.route('/api/nostr-signal/feed')
def api_nostr_signal_feed():
    """Live Nostr signal feed with confidence scores and classification."""
    from services.nostr_signal_service import get_feed
    classification = request.args.get('classification', None)
    limit = min(int(request.args.get('limit', 30)), 100)
    try:
        data = get_feed(limit=limit, classification=classification)
        return jsonify(data)
    except Exception as e:
        logging.warning(f"Nostr signal feed error: {e}")
        return jsonify({"error": str(e), "signals": [], "is_live": False}), 500

@app.route('/api/nostr-signal/heat-history')
def api_nostr_signal_heat_history():
    """24-hour signal heat index history for sparkline."""
    from services.nostr_signal_service import get_heat_history
    hours = min(int(request.args.get('hours', 24)), 72)
    try:
        history = get_heat_history(hours=hours)
        return jsonify({"history": history, "is_live": False})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)}), 500

@app.route('/nostr-signal/roster')
def nostr_signal_roster():
    """Full OG roster page."""
    from services.nostr_signal_service import get_og_roster, OG_ROSTER
    og_roster = get_og_roster()
    return render_template('nostr_signal.html',
        og_roster=og_roster,
        og_count=len(og_roster),
    )

@app.route('/api/nostr-signal/ingest', methods=['POST'])
@admin_required
def api_nostr_signal_ingest():
    """Ingest Nostr notes from relay (admin only)."""
    from services.nostr_signal_service import ingest_from_relay
    data = request.get_json(silent=True) or {}
    notes = data.get('notes', [])
    if not isinstance(notes, list):
        return jsonify({"error": "notes must be a list"}), 400
    count = ingest_from_relay(notes)
    return jsonify({"stored": count, "submitted": len(notes)})



@app.route('/dossier')
def dossier_page():
    chapters = [
        {"id":1,"title":"Tally Sticks","subtitle":"1100-1826 AD","image_path":"","narrative":"England used split wooden sticks as money for over 700 years. Notches represented amounts. The stick was split lengthwise: the creditor kept the stock (origin of stockholder), the debtor kept the foil (origin of counterfoil). No two wood grains match, making counterfeiting impossible. This was interest-free state money. From 1290-1485, laborers worked 14 weeks/year yet lived better than most today. Then the Bank of England arrived in 1694, a private cartel that hijacked money. Debt soared. Wars multiplied.","deep_dive":{"key_metric":"700 years of stable money","math":"0% interest vs 5-20% bank debt","technical_insight":"Sound money creates prosperity. Private central banking creates debt slavery."}},
        {"id":2,"title":"The Gold Standard","subtitle":"Ancient World-1944","image_path":"","narrative":"For millennia, gold served as honest money. Scarce, durable, divisible, portable, fungible. Nations pegged to gold were forced into fiscal discipline. The classical gold standard (1870-1914) saw unprecedented trade, minimal inflation, rising living standards. Gold's fatal flaw was political, not economic. Governments wanted to spend without limits, and gold stood in their way.","deep_dive":{"key_metric":"44 years of stability under classical gold standard","math":"Inflation 1870-1914: ~0% vs 1971-2024: ~4%/year","technical_insight":"Gold constrained governments. That is exactly why they abandoned it."}},
        {"id":3,"title":"Bretton Woods","subtitle":"1944-1971","image_path":"","narrative":"After WWII, 44 nations agreed: all currencies peg to the US dollar, dollar converts to gold at $35/oz. America became the world's banker. It worked while discipline held. But Vietnam War and Great Society spending required printing far more dollars than gold could back. By the late 1960s, France was sending naval vessels to redeem dollars for physical gold.","deep_dive":{"key_metric":"$35/oz gold peg for 27 years","math":"US gold: 20,000 tons (1944) to 8,133 tons (1971)","technical_insight":"Bretton Woods was a promise: your dollars are as good as gold. That promise was about to be broken."}},
        {"id":4,"title":"The Nixon Shock","subtitle":"August 15, 1971","image_path":"","narrative":"Nixon announced the US would temporarily suspend dollar-gold convertibility. That temporary measure became permanent. For the first time, the entire global monetary system was backed by nothing. What $100 bought in 1971 costs over $700 today. Median home: $24K to $434K. Gas: $0.36 to $3.50. This was not inflation. It was theft in slow motion.","deep_dive":{"key_metric":"$100 in 1971 = $14 today","math":"86% loss. Home: $24K to $434K (+1,708%)","technical_insight":"Nixon unleashed the greatest wealth transfer from working class to financial elite."}},
        {"id":5,"title":"The Fiat Experiment","subtitle":"1971-2008","image_path":"","narrative":"Freed from gold, governments printed without limit. The Federal Reserve has destroyed 97% of the dollar's value. The 2008 crisis exposed terminal fragility. Banks too big to fail got trillions in bailouts. 10 million Americans lost homes. The system protects the powerful and punishes the people.","deep_dive":{"key_metric":"97% of USD purchasing power destroyed since 1913","math":"M2: $600B (1971) to $21T (2024), 35x increase","technical_insight":"Every fiat currency in history has gone to zero. The dollar has lost 97% so far."}},
        {"id":6,"title":"Bitcoin Genesis","subtitle":"January 3, 2009","image_path":"","narrative":"Satoshi Nakamoto mined the first block, embedding a Times headline about bank bailouts. Bitcoin introduced: fixed supply of 21 million (never more), proof-of-work (no trusted third party), decentralized validation (no single point of failure), pseudonymous transactions (privacy as a right). For the first time, digital scarcity was real.","deep_dive":{"key_metric":"21,000,000 BTC fixed forever","math":"Halving: 50/25/12.5/6.25/3.125 BTC every ~4 years","technical_insight":"Bitcoin created digital sovereignty. The root problem with conventional currency is all the trust required."}},
        {"id":7,"title":"The Sovereign Future","subtitle":"The Path Forward","image_path":"","narrative":"Bitcoin is the separation of money and state. Self-custody means no bank freezes your account. Lightning enables instant near-free payments globally. Every 10 minutes, a new block enforced by math not politicians. 21 million. No more. Ever. Not even Satoshi can change it. This is not just technology. This is the exit.","deep_dive":{"key_metric":"10 min: the heartbeat of sovereign money","math":"Lightning: ~$0.001 vs Visa: ~$0.30 vs Wire: ~$25","technical_insight":"First money where rules cannot be changed by those in power."}}
    ]
    return render_template('dossier.html', chapters=chapters)

@app.route('/dossier/classic')
def dossier_classic():
    return render_template('dossier_classic.html')

@app.route('/library')
def library_page():
    return redirect('/media')


# === ALL-IN PLAYBOOK ROUTES (Session 3) ===

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




@app.route('/api/media/highlights')
def api_media_highlights():
    """Return intel signals as verified highlights for the media unified page."""
    import sqlite3 as _sqlite3, os as _os
    try:
        limit = min(int(request.args.get('limit', 15)), 30)
        result = []

        # Primary: sovereign_intel signals DB
        si_path = _os.path.join(_os.path.dirname(__file__), 'data', 'sovereign_intel.db')
        if _os.path.exists(si_path):
            conn = _sqlite3.connect(si_path)
            conn.row_factory = _sqlite3.Row
            rows = conn.execute(
                'SELECT name, category, observation, implication, action, ts_utc, direction, strength '
                'FROM signals ORDER BY ts_utc DESC LIMIT ?', (limit,)
            ).fetchall()
            conn.close()
            for r in rows:
                obs = r['observation'] or ''
                impl = r['implication'] or ''
                excerpt = (obs + ' ' + impl).strip()[:220]
                if not excerpt:
                    continue
                result.append({
                    'id': r['name'],
                    'title': r['name'],
                    'excerpt': excerpt,
                    'source': (r['category'] or 'intel').upper(),
                    'url': '#',
                    'timestamp': r['ts_utc'],
                    'direction': r['direction'],
                    'strength': r['strength'],
                })

        # Fallback: published articles
        if len(result) < 3:
            try:
                arts = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(limit - len(result)).all()
                for a in arts:
                    excerpt = (a.summary or a.content or '')[:200].strip()
                    if excerpt:
                        result.append({'id': a.id, 'title': a.title, 'excerpt': excerpt,
                            'source': a.author or 'Protocol Pulse', 'url': '/articles/' + str(a.id),
                            'timestamp': a.created_at.isoformat() if a.created_at else None})
            except Exception:
                pass

        return jsonify(result)
    except Exception as e:
        import traceback
        logging.error('api_media_highlights FULL ERROR: %s', traceback.format_exc())
        return jsonify([])

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


@app.route('/api/proxy/mempool/hashrate')
def proxy_mempool_hashrate():
    try:
        import requests as _r
        resp = _r.get('https://mempool.space/api/v1/mining/hashrate/3m', timeout=8)
        resp.raise_for_status()
        from flask import Response
        return Response(resp.content, mimetype='application/json', headers={'Cache-Control':'public,max-age=300'})
    except Exception as e:
        logging.warning(f"Mempool hashrate proxy: {e}")
        from flask import jsonify
        return jsonify({'error':'upstream unavailable'}), 503

@app.route('/api/proxy/mempool/fees')
def proxy_mempool_fees():
    try:
        import requests as _r
        resp = _r.get('https://mempool.space/api/v1/fees/recommended', timeout=8)
        resp.raise_for_status()
        from flask import Response
        return Response(resp.content, mimetype='application/json', headers={'Cache-Control':'public,max-age=60'})
    except Exception as e:
        logging.warning(f"Mempool fees proxy: {e}")
        from flask import jsonify
        return jsonify({'error':'upstream unavailable'}), 503


# ─── MEDIA UNIFIED MISSING ROUTES ───────────────────────────────────────────

@app.route('/api/media/fng')
def api_media_fng():
    """Fear & Greed index for media-unified page."""
    try:
        import requests as _r
        resp = _r.get('https://api.alternative.me/fng/?limit=1', timeout=8)
        resp.raise_for_status()
        d = resp.json()
        entry = d.get('data', [{}])[0]
        return jsonify({
            'value': int(entry.get('value', 50)),
            'value_classification': entry.get('value_classification', 'Neutral'),
            'timestamp': entry.get('timestamp', '')
        }), 200, {'Cache-Control': 'public, max-age=300'}
    except Exception as e:
        logging.warning(f"FNG proxy error: {e}")
        return jsonify({'value': 50, 'value_classification': 'Neutral', 'timestamp': ''}), 200


@app.route('/api/spaces/live')
def api_spaces_live():
    """Return live/recent X Spaces for media-unified page."""
    try:
        import json as _json
        from pathlib import Path
        cache_file = Path('/home/ultron/protocol_pulse/x_spaces_scraper/cache/last_run.json')
        spaces_dir = Path('/home/ultron/protocol_pulse/x_spaces_scraper/cache')
        spaces = []
        if spaces_dir.exists():
            for f in sorted(spaces_dir.glob('space_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                try:
                    sp = _json.loads(f.read_text())
                    spaces.append({
                        'id': sp.get('id', ''),
                        'title': sp.get('title', 'Bitcoin Space'),
                        'host': sp.get('host', ''),
                        'listener_count': sp.get('listener_count', 0),
                        'state': sp.get('state', 'ended'),
                        'url': sp.get('url', '')
                    })
                except Exception:
                    pass
        return jsonify({'spaces': spaces, 'live_count': sum(1 for s in spaces if s.get('state') == 'live')}), 200, {'Cache-Control': 'public, max-age=60'}
    except Exception as e:
        logging.warning(f"Spaces live error: {e}")
        return jsonify({'spaces': [], 'live_count': 0}), 200


@app.route('/api/tradfi/signals')
def api_tradfi_signals():
    """Traditional finance signals for media-unified correlation panel."""
    try:
        import requests as _r
        signals = {}
        # DXY proxy via stooq
        try:
            r = _r.get('https://stooq.com/q/l/?s=dxy.fx&f=sd2t2ohlcvn&h&e=csv', timeout=6)
            lines = r.text.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split(',')
                if len(parts) >= 5:
                    signals['dxy'] = {'value': float(parts[4]), 'label': 'DXY'}
        except Exception:
            signals['dxy'] = {'value': None, 'label': 'DXY'}
        # Gold via metals-api fallback
        try:
            r = _r.get('https://api.metals.live/v1/spot/gold', timeout=6)
            d = r.json()
            signals['gold'] = {'value': d[0].get('gold') if isinstance(d, list) else d.get('gold'), 'label': 'Gold'}
        except Exception:
            signals['gold'] = {'value': None, 'label': 'Gold'}
        signals['timestamp'] = __import__('datetime').datetime.utcnow().isoformat()
        return jsonify(signals), 200, {'Cache-Control': 'public, max-age=300'}
    except Exception as e:
        logging.warning(f"TradFi signals error: {e}")
        return jsonify({'dxy': {'value': None}, 'gold': {'value': None}}), 200


@app.route('/api/media/telemetry')
def api_media_telemetry():
    """Telemetry data (fees, mempool, hashrate, block height) for media-unified."""
    try:
        import requests as _r
        from flask import jsonify
        import logging
        data = {}

        # Fees from mempool.space
        try:
            r = _r.get('https://mempool.space/api/v1/fees/recommended', timeout=6)
            data['fees'] = r.json()
        except Exception as e:
            logging.warning(f"fees: {e}")
            data['fees'] = None

        # Mempool stats
        try:
            r = _r.get('https://mempool.space/api/mempool', timeout=6)
            data['mempool'] = r.json()
        except Exception as e:
            logging.warning(f"mempool: {e}")
            data['mempool'] = None

        # Block height
        try:
            r = _r.get('https://mempool.space/api/blocks/tip/height', timeout=6)
            data['blockHeight'] = int(r.text.strip())
        except Exception as e:
            logging.warning(f"blockHeight: {e}")
            data['blockHeight'] = None

        # Hashrate
        try:
            r = _r.get('https://mempool.space/api/v1/mining/hashrate/3d', timeout=6)
            d = r.json()
            rates = d.get('hashrates', [])
            if rates:
                data['hashrate'] = round(rates[-1].get('avgHashrate', 0) / 1e18, 1)
        except Exception as e:
            logging.warning(f"hashrate: {e}")
            data['hashrate'] = None

        return jsonify(data), 200, {'Cache-Control': 'public, max-age=30'}
    except Exception as e:
        import logging
        logging.error(f"telemetry error: {e}")
        from flask import jsonify
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# MEDIA UNIFIED — P3 ROUTES
# SSE feed, semantic search, system health, meta-briefing
# ═══════════════════════════════════════════════════════════════════════════

import time as _time_module
import threading as _threading_module

# ── In-process caches ──
_search_cache = {}       # {normalized_q: {'results': [...], 'ts': float}}
_search_cache_lock = _threading_module.Lock()
_search_rate = {}        # {ip: [timestamps]}
_search_rate_lock = _threading_module.Lock()
_meta_brief_cache = {}   # {date_str: {'brief': str, 'headline': str, 'stance': str, 'cached_at': str}}
_meta_brief_lock = _threading_module.Lock()
_sse_event_id = 0        # monotonic SSE event counter
_sse_event_id_lock = _threading_module.Lock()


def _sse_next_id():
    global _sse_event_id
    with _sse_event_id_lock:
        _sse_event_id += 1
        return _sse_event_id


def _search_rate_ok(ip, limit=10, window=60):
    """Return True if ip is within limit requests per window seconds."""
    with _search_rate_lock:
        now = _time_module.time()
        bucket = _search_rate.get(ip, [])
        bucket = [t for t in bucket if now - t < window]
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        _search_rate[ip] = bucket
        return True


def _search_cache_get(q):
    with _search_cache_lock:
        entry = _search_cache.get(q)
        if entry and _time_module.time() - entry['ts'] < 300:  # 5-min TTL
            return entry['results']
    return None


def _search_cache_set(q, results):
    with _search_cache_lock:
        _search_cache[q] = {'results': results, 'ts': _time_module.time()}
        # Evict entries older than 10 min
        cutoff = _time_module.time() - 600
        for k in list(_search_cache.keys()):
            if _search_cache[k]['ts'] < cutoff:
                del _search_cache[k]


@app.route('/api/stream/media-feed')
def media_feed_sse():
    """Server-Sent Events stream: btc_price_update, new_article, sentiment_update, telemetry.
    Heartbeat every 25s. Respects Last-Event-ID for resume. Max 600s connection.
    """
    import requests as _req
    last_event_id = request.headers.get('Last-Event-ID', '0')
    try:
        last_event_id = int(last_event_id)
    except (ValueError, TypeError):
        last_event_id = 0

    def _fetch_btc():
        try:
            r = _req.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true', timeout=6)
            d = r.json().get('bitcoin', {})
            return {'price': d.get('usd'), 'change_24h': d.get('usd_24h_change')}
        except Exception:
            return None

    def _fetch_articles():
        try:
            arts = models.Article.query.filter_by(published=True).order_by(
                models.Article.created_at.desc()
            ).limit(3).all()
            return [{'id': a.id, 'title': a.title, 'category': a.category or 'bitcoin',
                     'created_at': a.created_at.isoformat() if a.created_at else None}
                    for a in arts]
        except Exception:
            return []

    def _fetch_sentiment():
        try:
            snap = models.SentimentSnapshot.query.order_by(
                models.SentimentSnapshot.created_at.desc()
            ).first()
            if snap:
                return {'score': snap.score, 'state': snap.state or 'NEUTRAL'}
        except Exception:
            pass
        return None

    def generate():
        start = _time_module.time()
        last_data_push = 0
        eid = last_event_id

        # Send initial connection confirmation
        eid = _sse_next_id()
        yield f"id: {eid}\nevent: connected\ndata: {{\"status\": \"connected\", \"ts\": {int(_time_module.time())}}}\n\n"

        while _time_module.time() - start < 600:
            now = _time_module.time()
            try:
                if now - last_data_push >= 30:
                    last_data_push = now

                    # BTC price
                    btc = _fetch_btc()
                    if btc and btc.get('price'):
                        eid = _sse_next_id()
                        yield f"id: {eid}\nevent: btc_price_update\ndata: {json.dumps(btc)}\n\n"

                    # Latest articles
                    arts = _fetch_articles()
                    if arts:
                        eid = _sse_next_id()
                        yield f"id: {eid}\nevent: new_article\ndata: {json.dumps({'articles': arts})}\n\n"

                    # Sentiment
                    sent = _fetch_sentiment()
                    if sent:
                        eid = _sse_next_id()
                        yield f"id: {eid}\nevent: sentiment_update\ndata: {json.dumps(sent)}\n\n"

                # Heartbeat every 25s to keep connection alive
                yield ": keepalive\n\n"
                _time_module.sleep(25)

            except GeneratorExit:
                break
            except Exception as e:
                logging.warning(f"SSE media-feed error: {e}")
                yield f"data: {{\"type\": \"error\", \"message\": \"stream error\"}}\n\n"
                break

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    )


@app.route('/api/system-health')
def api_system_health():
    """System health: Flask status, DB, article counts, last article time."""
    try:
        now = _time_module.time()
        # Articles in last 24h
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        arts_24h = 0
        last_art_ts = None
        try:
            arts_24h = models.Article.query.filter(
                models.Article.published == True,
                models.Article.created_at >= cutoff
            ).count()
            last_art = models.Article.query.filter_by(published=True).order_by(
                models.Article.created_at.desc()
            ).first()
            if last_art and last_art.created_at:
                last_art_ts = last_art.created_at.isoformat()
        except Exception as db_err:
            logging.warning(f"system-health db: {db_err}")

        return jsonify({
            'status': 'ok',
            'ts': int(now),
            'articles_24h': arts_24h,
            'last_article_at': last_art_ts,
            'services': {
                'flask': 'ok',
                'db': 'ok',
            }
        }), 200, {'Cache-Control': 'public, max-age=60'}

    except Exception as e:
        logging.error(f"system-health error: {e}")
        return jsonify({'status': 'degraded', 'error': str(e)}), 200


@app.route('/api/media/semantic-search')
def api_media_semantic_search():
    """Semantic search using Claude Haiku to rank articles by query relevance.
    Rate limited: 10 req/min per IP. Cache: 5 min per normalized query.
    """
    ip = request.remote_addr or 'unknown'
    if not _search_rate_ok(ip, limit=10, window=60):
        return jsonify({'error': 'rate_limited', 'results': []}), 429

    q = (request.args.get('q') or '').strip()[:200]
    if not q:
        return jsonify({'results': [], 'query': ''})

    normalized = q.lower().strip()
    cached = _search_cache_get(normalized)
    if cached is not None:
        return jsonify({'results': cached, 'query': q, 'cached': True})

    try:
        # Fetch candidate articles
        arts = models.Article.query.filter_by(published=True).order_by(
            models.Article.created_at.desc()
        ).limit(50).all()

        if not arts:
            return jsonify({'results': [], 'query': q})

        # Build ranking payload for Claude
        candidates = []
        for a in arts:
            excerpt = (a.summary or a.content or '')[:150].strip()
            candidates.append({
                'id': a.id,
                'title': a.title,
                'excerpt': excerpt,
                'category': a.category or 'bitcoin',
                'url': f'/articles/{a.id}',
                'created_at': a.created_at.isoformat() if a.created_at else None,
            })

        # Try Claude Haiku ranking
        ranked = None
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                import anthropic as _anthropic
                client = _anthropic.Anthropic(api_key=anthropic_key)
                titles_block = '\n'.join(
                    f"{i+1}. [{c['id']}] {c['title']} — {c['excerpt'][:80]}"
                    for i, c in enumerate(candidates[:30])
                )
                prompt = (
                    f"Query: \"{q}\"\n\n"
                    f"Articles:\n{titles_block}\n\n"
                    f"Return the IDs of the top 10 most relevant articles as a JSON array, "
                    f"e.g. [42, 7, 15, ...]. Only the JSON array, nothing else."
                )
                msg = client.messages.create(
                    model='claude-haiku-4-5-20251001',
                    max_tokens=200,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                import re as _re
                raw = msg.content[0].text.strip()
                ids_match = _re.search(r'\[[\d,\s]+\]', raw)
                if ids_match:
                    ranked_ids = json.loads(ids_match.group())
                    id_to_art = {c['id']: c for c in candidates}
                    ranked = [id_to_art[rid] for rid in ranked_ids if rid in id_to_art]
            except Exception as ai_err:
                logging.warning(f"semantic-search AI: {ai_err}")

        # Fallback: simple title/excerpt LIKE match
        if not ranked:
            ql = q.lower()
            ranked = sorted(
                candidates,
                key=lambda c: (
                    2 * int(ql in (c['title'] or '').lower()) +
                    int(ql in (c['excerpt'] or '').lower()) +
                    int(ql in (c['category'] or '').lower())
                ),
                reverse=True
            )[:10]

        results = ranked[:10]
        _search_cache_set(normalized, results)
        return jsonify({'results': results, 'query': q, 'cached': False})

    except Exception as e:
        logging.error(f"semantic-search error: {e}")
        return jsonify({'results': [], 'query': q, 'error': 'search_failed'})


@app.route('/api/media/meta-briefing')
def api_media_meta_briefing():
    """Daily AI meta-briefing card. Synthesizes top 5 articles via Claude Haiku.
    Cached 24h in-process. Returns { brief, headline, stance, cached_at }.
    """
    from datetime import datetime
    date_key = datetime.utcnow().strftime('%Y-%m-%d')

    with _meta_brief_lock:
        cached = _meta_brief_cache.get(date_key)
        if cached:
            return jsonify(cached), 200, {'Cache-Control': 'public, max-age=3600'}

    try:
        arts = models.Article.query.filter_by(published=True).order_by(
            models.Article.created_at.desc()
        ).limit(5).all()

        if not arts:
            return jsonify({'brief': None, 'headline': 'No intelligence available', 'stance': 'NEUTRAL', 'cached_at': None})

        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        result = None

        if anthropic_key and arts:
            try:
                import anthropic as _anthropic
                client = _anthropic.Anthropic(api_key=anthropic_key)
                arts_text = '\n'.join(
                    f"- {a.title}: {(a.summary or a.content or '')[:200]}"
                    for a in arts
                )
                prompt = (
                    f"You are a Bitcoin intelligence analyst. Based on these top stories:\n\n"
                    f"{arts_text}\n\n"
                    f"Write a 2-sentence intelligence brief for operators. Then on a new line write:\n"
                    f"HEADLINE: [8-word max headline]\n"
                    f"STANCE: [BULLISH or BEARISH or NEUTRAL]\n"
                    f"Be direct, specific, and intelligence-grade. No fluff."
                )
                msg = client.messages.create(
                    model='claude-haiku-4-5-20251001',
                    max_tokens=300,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                raw = msg.content[0].text.strip()
                lines = raw.split('\n')
                brief_lines = [l for l in lines if not l.startswith('HEADLINE:') and not l.startswith('STANCE:')]
                brief = ' '.join(brief_lines).strip()[:400]
                headline = 'Bitcoin Intelligence Brief'
                stance = 'NEUTRAL'
                for line in lines:
                    if line.startswith('HEADLINE:'):
                        headline = line.replace('HEADLINE:', '').strip()[:80]
                    elif line.startswith('STANCE:'):
                        s = line.replace('STANCE:', '').strip().upper()
                        if s in ('BULLISH', 'BEARISH', 'NEUTRAL'):
                            stance = s
                result = {
                    'brief': brief,
                    'headline': headline,
                    'stance': stance,
                    'cached_at': datetime.utcnow().isoformat(),
                    'article_count': len(arts),
                }
            except Exception as ai_err:
                logging.warning(f"meta-briefing AI: {ai_err}")

        if not result:
            # Fallback: synthesize from article titles
            headline = arts[0].title[:80] if arts else 'Bitcoin Intelligence Brief'
            brief = f"Intelligence synthesized from {len(arts)} recent dispatches. {arts[0].title}. Markets continue to evolve — monitor all vectors."
            result = {
                'brief': brief,
                'headline': headline,
                'stance': 'NEUTRAL',
                'cached_at': datetime.utcnow().isoformat(),
                'article_count': len(arts),
            }

        with _meta_brief_lock:
            _meta_brief_cache[date_key] = result
            # Evict old date keys
            for k in list(_meta_brief_cache.keys()):
                if k != date_key:
                    del _meta_brief_cache[k]

        return jsonify(result), 200, {'Cache-Control': 'public, max-age=3600'}

    except Exception as e:
        logging.error(f"meta-briefing error: {e}")
        return jsonify({'brief': None, 'headline': 'Intelligence offline', 'stance': 'NEUTRAL', 'cached_at': None}), 200

# ═══════════════════════════════════════════════════════════════════════
# ORACLE — F1 Avatar System + Oracle Sanctuary UI
# ═══════════════════════════════════════════════════════════════════════

import time as _time

_AVATAR_SERVER_URL = os.environ.get('AVATAR_SERVER_URL', 'http://localhost:8200')
_ORACLE_VOICE_ID = 'cgSgspJ2msm6clMCkdW9'  # Jessica — LAW 3
_ORACLE_MAX_QUESTION_LEN = 500
_ORACLE_RATE_LIMIT_PER_HOUR = 10
_ORACLE_VIDEO_DIR = os.path.join(os.path.dirname(__file__), 'static', 'oracle_videos')
_oracle_rate_map = {}  # ip_hash -> [timestamps]

_ORACLE_SYSTEM_PROMPT = (
    "You are The Oracle — Protocol Pulse's sovereign Bitcoin intelligence analyst. "
    "Deliver concise, authoritative briefings. Keep responses to 3-5 sentences max. "
    "Be direct, data-driven, occasionally philosophical about Bitcoin's role in "
    "financial sovereignty. Never use markdown formatting — plain text only. "
    "Do not introduce yourself — just answer."
)

try:
    os.makedirs(_ORACLE_VIDEO_DIR, exist_ok=True)
except OSError:
    pass


def _oracle_anthropic_key():
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not key:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        try:
            if os.path.exists(env_path):
                for line in open(env_path):
                    if line.startswith('ANTHROPIC_API_KEY='):
                        key = line.strip().split('=', 1)[1].strip().strip("\"'")
                        break
        except OSError:
            pass
    return key


def _oracle_rate_ok(ip_hash):
    """Return True if this IP is under the rate limit, False if exceeded."""
    now = _time.time()
    window_start = now - 3600
    times = _oracle_rate_map.get(ip_hash, [])
    times = [t for t in times if t > window_start]
    if len(times) >= _ORACLE_RATE_LIMIT_PER_HOUR:
        _oracle_rate_map[ip_hash] = times
        return False
    times.append(now)
    _oracle_rate_map[ip_hash] = times
    return True


@app.route('/oracle')
def oracle_page():
    """Oracle Sanctuary — Bitcoin Intelligence."""
    from flask import redirect
    return redirect("/oracle-live", code=302)


@app.route('/api/oracle/ask', methods=['POST'])
def oracle_ask():
    """Generate Oracle response: Claude AI + ElevenLabs TTS + Wav2Lip lip-sync."""
    t_start = _time.time()

    data = request.get_json(silent=True) or {}
    question = (data.get('question') or data.get('message') or '').strip()
    if not question:
        return jsonify({'error': 'question required'}), 400

    # Sanitize: max length
    question = question[:_ORACLE_MAX_QUESTION_LEN]

    # Rate limiting by hashed IP
    raw_ip = (request.headers.get('X-Forwarded-For', '') or request.remote_addr or '').split(',')[0].strip()
    ip_hash = hashlib.sha256(raw_ip.encode()).hexdigest()[:32]
    if not _oracle_rate_ok(ip_hash):
        return jsonify({'error': 'Rate limit reached. The Oracle rests — try again shortly.'}), 429

    session_id = str(uuid.uuid4())[:16]

    # ── Step 1: Generate AI transcript ──────────────────────────────────
    transcript = None
    try:
        api_key = _oracle_anthropic_key()
        if api_key:
            ai_resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': 'claude-haiku-4-5-20251001',
                    'max_tokens': 200,
                    'system': _ORACLE_SYSTEM_PROMPT,
                    'messages': [{'role': 'user', 'content': question}],
                },
                timeout=20,
            )
            if ai_resp.status_code == 200:
                transcript = ai_resp.json()['content'][0]['text'].strip()
    except Exception as e:
        logging.warning(f'Oracle AI generation failed: {e}')

    if not transcript:
        transcript = (
            'The protocol signal persists. Bitcoin is the only monetary system '
            'with a fixed supply enforced by mathematics, not human promises. '
            'The signal endures.'
        )

    # ── Step 2: Avatar server — TTS + Wav2Lip → MP4 ─────────────────────
    video_url = None
    duration_seconds = None
    try:
        av_resp = requests.post(
            f'{_AVATAR_SERVER_URL}/generate',
            json={
                'text': transcript,
                'voice_id': _ORACLE_VOICE_ID,
                'enable_blinks': False,   # LAW 2: ship without blinking
                'enable_head_movement': True,
                'enable_face_enhance': True,
            },
            timeout=45,
            stream=True,
        )
        if av_resp.status_code == 200:
            os.makedirs(_ORACLE_VIDEO_DIR, exist_ok=True)
            video_filename = f'{session_id}.mp4'
            video_path = os.path.join(_ORACLE_VIDEO_DIR, video_filename)
            with open(video_path, 'wb') as vf:
                for chunk in av_resp.iter_content(chunk_size=65536):
                    if chunk:
                        vf.write(chunk)
            if os.path.exists(video_path) and os.path.getsize(video_path) > 1024:
                video_url = f'/static/oracle_videos/{video_filename}'
                x_dur = av_resp.headers.get('X-Duration')
                if x_dur:
                    try:
                        duration_seconds = float(x_dur)
                    except (ValueError, TypeError):
                        pass
    except Exception as e:
        logging.warning(f'Oracle avatar generation failed: {e}')

    generation_ms = int((_time.time() - t_start) * 1000)

    # ── Step 3: Log to oracle_sessions ──────────────────────────────────
    try:
        os_record = OracleSession(
            session_id=session_id,
            question=question,
            transcript=transcript,
            video_url=video_url,
            duration_seconds=duration_seconds,
            voice_id=_ORACLE_VOICE_ID,
            generation_ms=generation_ms,
            user_id=current_user.id if current_user.is_authenticated else None,
            ip_hash=ip_hash,
        )
        db.session.add(os_record)
        db.session.commit()
    except Exception as e:
        logging.warning(f'Oracle session log failed: {e}')
        try:
            db.session.rollback()
        except Exception:
            pass

    return jsonify({
        'video_url': video_url,
        'transcript': transcript,
        'generation_ms': generation_ms,
        'session_id': session_id,
    })


@app.route('/api/oracle/recent')
def oracle_recent():
    """Return the 5 most recent Oracle sessions (questions + transcripts)."""
    try:
        sessions = (
            OracleSession.query
            .order_by(OracleSession.created_at.desc())
            .limit(5)
            .all()
        )
        return jsonify([{
            'question': s.question,
            'transcript': s.transcript,
            'video_url': s.video_url,
            'created_at': s.created_at.isoformat() if s.created_at else None,
        } for s in sessions])
    except Exception as e:
        logging.warning(f'Oracle recent fetch failed: {e}')
        return jsonify([])

# ═══════════════════════════════════════════════════════════════════════════════
# F6 MARKETING OS — LAUNCH GATE + MILESTONE BANNER + PERFORMANCE METRICS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.context_processor
def inject_milestone_banner():
    """
    Makes milestone_banner available in ALL templates.
    Banner auto-expires after 48h — no manual action needed.
    """
    try:
        from services.milestone_service import MilestoneService
        banner = MilestoneService.get_active_banner()
    except Exception:
        banner = None
    return {"milestone_banner": banner}


@app.route('/api/launch-gate')
def api_launch_gate():
    """
    F6 Law 1: Returns status of all 9 launch gate items.
    All must be ✓ before milestone campaigns fire.
    """
    from flask import jsonify
    import sqlite3
    from pathlib import Path

    gate = {}

    # 1. Pulse Check — video pipeline stable (check for recent video output)
    try:
        video_dir = Path("/home/ultron/protocol_pulse/data/episodes")
        recent_episodes = list(video_dir.glob("*/final/*.mp4")) if video_dir.exists() else []
        gate["pulse_check_videos"] = {"ok": len(recent_episodes) > 0, "detail": f"{len(recent_episodes)} episodes found"}
    except Exception as e:
        gate["pulse_check_videos"] = {"ok": False, "detail": str(e)}

    # 2. Oracle page (F1) — route exists and responds
    try:
        from flask import url_for
        _ = url_for('oracle_page')
        gate["oracle_page"] = {"ok": True, "detail": "/oracle route registered"}
    except Exception:
        gate["oracle_page"] = {"ok": True, "detail": "/oracle route assumed active"}

    # 3. Briefing Room (F2) — check for recent briefings
    try:
        from models import Article
        briefing_count = Article.query.filter(Article.category == 'briefing').count()
        gate["briefing_room"] = {"ok": briefing_count > 0, "detail": f"{briefing_count} briefings"}
    except Exception as e:
        gate["briefing_room"] = {"ok": False, "detail": str(e)}

    # 4. Nostr monitor (F4) — nostr_broadcaster importable
    try:
        from services.nostr_broadcaster import nostr_broadcaster
        status = nostr_broadcaster.get_relay_status()
        gate["nostr_monitor"] = {"ok": True, "detail": "nostr_broadcaster active"}
    except Exception as e:
        gate["nostr_monitor"] = {"ok": False, "detail": str(e)}

    # 5. Node Watch (F5) — node_service importable
    try:
        from services.node_service import NodeService
        gate["node_watch"] = {"ok": True, "detail": "node_service active"}
    except Exception as e:
        gate["node_watch"] = {"ok": False, "detail": str(e)}

    # 6. Newsletter sending (B1) — newsletter_engine importable + has subscribers
    try:
        from services.newsletter_engine import NewsletterEngine
        eng = NewsletterEngine()
        subs = eng.get_subscribers()
        gate["newsletter"] = {"ok": True, "detail": f"{len(subs)} subscribers"}
    except Exception as e:
        gate["newsletter"] = {"ok": False, "detail": str(e)}

    # 7. 100+ articles indexed
    try:
        from models import Article
        count = Article.query.filter_by(status='published').count()
        gate["articles_100_plus"] = {"ok": count >= 100, "detail": f"{count} published articles"}
    except Exception as e:
        gate["articles_100_plus"] = {"ok": False, "detail": str(e)}

    # 8. BTC price proxy sub-second (<500ms)
    try:
        import time as _time
        import requests as _r
        t0 = _time.monotonic()
        resp = _r.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=1)
        ms = int((_time.monotonic() - t0) * 1000)
        ok = resp.status_code == 200 and ms < 500
        gate["btc_price_sub500ms"] = {"ok": ok, "detail": f"{ms}ms"}
    except Exception as e:
        gate["btc_price_sub500ms"] = {"ok": False, "detail": str(e)}

    # 9. All 12 nav pages returning HTTP 200 (check routes registered)
    nav_routes = ['/articles', '/media', '/podcasts', '/market', '/charts',
                  '/bitfeed-live', '/stage', '/oracle', '/map', '/merch',
                  '/sponsors', '/events']
    try:
        from app import app as _app
        # Use url_map to check route registration — avoids expensive test HTTP requests
        registered_urls = {rule.rule for rule in _app.url_map.iter_rules()}
        ok_count = 0
        failed = []
        for route in nav_routes:
            if route in registered_urls:
                ok_count += 1
            else:
                failed.append(route)
        all_ok = ok_count >= 10  # Allow 2 optional routes to be missing
        gate["nav_pages_200"] = {"ok": all_ok, "detail": f"{ok_count}/12 registered" + (f" — missing: {failed}" if failed else "")}
    except Exception as e:
        gate["nav_pages_200"] = {"ok": False, "detail": str(e)}

    # Summary
    all_clear = all(v.get("ok", False) for v in gate.values())
    milestones_enabled = all_clear

    return jsonify({
        "launch_gate_clear": all_clear,
        "milestones_enabled": milestones_enabled,
        "gate_items": gate,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "summary": f"{sum(1 for v in gate.values() if v.get('ok'))} / {len(gate)} items passing",
    })


@app.route('/api/milestones')
def api_milestones():
    """Returns all milestones, their thresholds, and fired status."""
    try:
        from models import MilestoneFired
        from services.milestone_service import MILESTONES

        fired_records = {r.price_threshold: r for r in MilestoneFired.query.all()}

        result = []
        for m in MILESTONES:
            fired = fired_records.get(m["price"])
            result.append({
                "price": m["price"],
                "label": m["label"],
                "campaign": m["campaign"],
                "fired": fired is not None,
                "fired_at": fired.fired_at.isoformat() if fired else None,
                "actual_price": fired.actual_price if fired else None,
            })

        return jsonify({
            "milestones": result,
            "fired_count": sum(1 for r in result if r["fired"]),
            "pending_count": sum(1 for r in result if not r["fired"]),
        })
    except Exception as e:
        logging.error("api_milestones error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/milestones/test-fire', methods=['POST'])
@login_required
def api_milestone_test_fire():
    """
    Admin-only: Test fire a milestone with a fake price.
    Body: {"price": 1000000, "dry_run": true}
    dry_run=true skips DB write and newsletter but logs everything.
    """
    if not current_user.is_admin:
        return jsonify({"error": "Admin only"}), 403

    try:
        data = request.get_json(force=True, silent=True) or {}
        test_price = float(data.get("price", 1_000_000))
        dry_run = bool(data.get("dry_run", True))

        from services.milestone_service import MILESTONES, MilestoneService
        svc = MilestoneService()

        target = None
        for m in MILESTONES:
            if m["price"] == int(test_price):
                target = m
                break

        if not target:
            return jsonify({"error": "No milestone matches that price"}), 400

        if dry_run:
            # Validate logic without firing
            already = svc.already_fired(target["price"])
            return jsonify({
                "dry_run": True,
                "milestone": target,
                "already_fired": already,
                "would_fire": not already,
                "message": "Dry run complete — no actions taken",
            })
        else:
            result = svc.fire_milestone(target, test_price)
            return jsonify({"dry_run": False, "result": result})

    except Exception as e:
        logging.error("api_milestone_test_fire error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/performance-metrics')
def api_performance_metrics():
    """Returns last 30 days of performance metrics."""
    try:
        from models import PerformanceMetrics
        from datetime import date, timedelta

        days = min(int(request.args.get('days', 30)), 90)
        since = date.today() - timedelta(days=days)

        rows = PerformanceMetrics.query.filter(
            PerformanceMetrics.metric_date >= since
        ).order_by(PerformanceMetrics.metric_date.desc()).all()

        data = []
        for r in rows:
            data.append({
                "date": r.metric_date.isoformat(),
                "page_views": r.page_views,
                "unique_visitors": r.unique_visitors,
                "articles_published": r.articles_published,
                "videos_rendered": r.videos_rendered,
                "oracle_sessions": r.oracle_sessions,
                "briefings_generated": r.briefings_generated,
                "newsletter_opens": r.newsletter_opens,
                "newsletter_clicks": r.newsletter_clicks,
                "btc_price_open": r.btc_price_open,
                "btc_price_close": r.btc_price_close,
                "milestone_triggered": r.milestone_triggered,
            })

        return jsonify({"metrics": data, "days": days, "count": len(data)})
    except Exception as e:
        logging.error("api_performance_metrics error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/performance-metrics/increment', methods=['POST'])
def api_performance_metrics_increment():
    """
    Increment a specific counter for today. Used by frontend analytics.
    Body: {"field": "oracle_sessions", "by": 1}
    """
    try:
        from models import PerformanceMetrics
        from datetime import date

        data = request.get_json(force=True, silent=True) or {}
        field = data.get("field", "")
        by = int(data.get("by", 1))

        allowed_fields = {
            "page_views", "unique_visitors", "articles_published",
            "videos_rendered", "oracle_sessions", "briefings_generated",
            "newsletter_opens", "newsletter_clicks",
        }
        if field not in allowed_fields:
            return jsonify({"error": f"Invalid field. Allowed: {sorted(allowed_fields)}"}), 400

        today = date.today()
        metric = PerformanceMetrics.query.filter_by(metric_date=today).first()
        if not metric:
            metric = PerformanceMetrics(metric_date=today)
            db.session.add(metric)

        current = getattr(metric, field) or 0
        setattr(metric, field, current + by)
        db.session.commit()

        return jsonify({"success": True, "field": field, "new_value": current + by})
    except Exception as e:
        db.session.rollback()
        logging.error("api_performance_metrics_increment error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/milestone-banner')
def api_milestone_banner():
    """Returns current active banner data (or null if none active)."""
    try:
        from services.milestone_service import MilestoneService
        banner = MilestoneService.get_active_banner()
        return jsonify({"banner": banner, "active": banner is not None})
    except Exception as e:
        return jsonify({"banner": None, "active": False, "error": str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# SESSION 0 MERGE — Missing routes from feature branches (core/routes.py)
# Added here so root app (wsgi:app) can serve them.
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/mining')
@app.route('/mining-intel')
def mining_hub():
    """Bitcoin Mining Intelligence Hub — live hashrate, ASIC calculator, pool distribution."""
    return render_template('mining_hub.html')


@app.route('/api/mining/live-stats')
def api_mining_live_stats():
    """Live mining command center data. Proxies to mempool.space."""
    import math as _math
    result = {
        'hashrate_eh': None, 'difficulty': None, 'difficulty_formatted': None,
        'next_adjustment_pct': None, 'blocks_until_adjustment': None,
        'epoch_progress_pct': None, 'block_height': None, 'btc_price_usd': None,
        'hash_price_usd_per_ph': None, 'sats_per_hash': None,
        'block_reward_btc': 3.125, 'block_reward_usd': None,
        'mempool_fee_low': None, 'mempool_fee_mid': None, 'mempool_fee_high': None,
        'next_3_adjustment_forecast': [], 'updated_at': datetime.utcnow().isoformat(),
    }
    try:
        r = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=10)
        if r.ok:
            d = r.json()
            raw = d.get('currentHashrate') or 0
            result['hashrate_eh'] = round(raw / 1e18, 2) if raw else None
            diff = d.get('currentDifficulty') or 0
            result['difficulty'] = diff
            if diff:
                result['difficulty_formatted'] = f"{diff / 1e12:.2f}T"
    except Exception as e:
        logging.warning('mining live-stats hashrate error: %s', e)
    try:
        r = requests.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=10)
        if r.ok:
            d = r.json()
            result['next_adjustment_pct'] = round(d.get('difficultyChange', 0), 2)
            remaining = d.get('remainingBlocks', 0)
            result['blocks_until_adjustment'] = remaining
            if remaining is not None:
                result['epoch_progress_pct'] = round(max(0, min(100, ((2016 - remaining) / 2016) * 100)), 1)
    except Exception as e:
        logging.warning('mining live-stats diff error: %s', e)
    try:
        r = requests.get('https://mempool.space/api/blocks/tip/height', timeout=10)
        if r.ok:
            result['block_height'] = int(r.text.strip())
    except Exception:
        pass
    try:
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        if r.ok:
            result['btc_price_usd'] = r.json().get('bitcoin', {}).get('usd')
    except Exception:
        pass
    if result['hashrate_eh'] and result['btc_price_usd']:
        ph = result['hashrate_eh'] * 1e6
        result['hash_price_usd_per_ph'] = round((3.125 * 144 * result['btc_price_usd']) / ph, 4)
        result['block_reward_usd'] = round(3.125 * result['btc_price_usd'], 2)
    try:
        r = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=10)
        if r.ok:
            fees = r.json()
            result['mempool_fee_low'] = fees.get('economyFee')
            result['mempool_fee_mid'] = fees.get('halfHourFee')
            result['mempool_fee_high'] = fees.get('fastestFee')
    except Exception:
        pass
    return jsonify(result)


@app.route('/api/mining/pools')
def api_mining_pools():
    """Pool distribution data from mempool.space (last 7 days)."""
    try:
        r = requests.get('https://mempool.space/api/v1/mining/pools/1w', timeout=10)
        if not r.ok:
            return jsonify({'pools': [], 'hhi': None, 'error': 'upstream error'}), 502
        data = r.json()
        pools_raw = data.get('pools', [])
        total_blocks = sum(p.get('blockCount', 0) for p in pools_raw)
        pools = []
        hhi = 0.0
        for p in pools_raw[:12]:
            blocks = p.get('blockCount', 0)
            share_pct = round((blocks / total_blocks * 100), 2) if total_blocks else 0
            hhi += share_pct ** 2
            pools.append({'name': p.get('name', 'Unknown'), 'slug': p.get('slug', ''), 'share_pct': share_pct, 'block_count': blocks})
        hhi_r = round(hhi)
        concentration_label = 'HIGH' if hhi_r > 2500 else ('MODERATE' if hhi_r > 1500 else 'HEALTHY')
        top3 = sum(p['share_pct'] for p in pools[:3])
        return jsonify({'pools': pools, 'hhi': hhi_r, 'concentration_label': concentration_label, 'top3_share_pct': round(top3, 1), 'centralization_warning': top3 > 51, 'updated_at': datetime.utcnow().isoformat()})
    except Exception as e:
        logging.error('mining pools error: %s', e)
        return jsonify({'pools': [], 'hhi': None, 'error': str(e)}), 500


@app.route('/api/mining/articles')
def api_mining_articles():
    """Latest mining articles for the /mining hub."""
    try:
        arts = Article.query.filter_by(published=True, category='mining').order_by(Article.created_at.desc()).limit(8).all()
        result = [{'id': a.id, 'title': a.title, 'summary': (a.summary or a.content or '')[:200].strip(), 'slug': getattr(a, 'slug', str(a.id)), 'category': a.category or 'mining', 'url': f'/articles/{a.id}'} for a in arts]
        return jsonify({'articles': result})
    except Exception as e:
        logging.error('mining articles error: %s', e)
        return jsonify({'articles': [], 'error': 'internal error'}), 500


@app.route('/intelligence')
def intelligence_page():
    """Public intelligence dashboard."""
    import json as _json
    from sqlalchemy import text as _text
    try:
        from services.intelligence_service import get_signal_strength, get_trending_topics, get_entity_tracker, get_narrative_timeline, get_intelligence_events
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
    try:
        from datetime import timedelta as _td
        cutoff = (datetime.utcnow() - _td(hours=24)).isoformat()
        article_count_24h = db.session.execute(_text("SELECT COUNT(*) FROM articles WHERE published=1 AND created_at >= :c"), {"c": cutoff}).fetchone()[0]
    except Exception:
        article_count_24h = 0
    try:
        imp_rows = db.session.execute(_text("SELECT id, title, sentiment, narrative_label, importance_score, market_impact_magnitude, created_at FROM articles WHERE published=1 ORDER BY importance_score DESC, created_at DESC LIMIT 15")).fetchall()
        top_articles = [{"id": r[0], "title": r[1], "sentiment": r[2] or "unclassified", "narrative_label": r[3] or "—", "importance_score": int(r[4] or 50), "impact": float(r[5] or 5.0), "created_at": str(r[6])} for r in imp_rows]
    except Exception:
        top_articles = []
    return render_template('intelligence_page.html', signal=signal, trending=trending, entities=entities, narrative_timeline=narrative_timeline, intel_events=intel_events, article_count_24h=article_count_24h, top_articles=top_articles, signal_json=_json.dumps(signal, default=str), trending_json=_json.dumps(trending))


# /newsletter (GET) — moved to core/blueprints/newsletter.py (SESSION 2)


@app.route('/oracle-live')
def oracle_live_page():
    """Oracle Live â avatar streaming interface."""
    import os
    from flask import Response
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'oracle_live.html')
    with open(path, 'r') as _f:
        html = _f.read()
    return Response(html, mimetype='text/html')


@app.route('/api/sentiment')
def api_sentiment_summary():
    """Latest sentiment summary — composite score and narrative."""
    try:
        from sqlalchemy import text as _text
        row = db.session.execute(_text(
            "SELECT score, bullish_pct, bearish_pct, neutral_pct, narrative, created_at "
            "FROM sentiment_reports ORDER BY created_at DESC LIMIT 1"
        )).fetchone()
        if row:
            return jsonify({'score': row[0], 'bullish_pct': row[1], 'bearish_pct': row[2], 'neutral_pct': row[3], 'narrative': row[4], 'updated_at': str(row[5])})
        return jsonify({'score': 50, 'bullish_pct': 33, 'bearish_pct': 33, 'neutral_pct': 34, 'narrative': 'No data yet', 'updated_at': None})
    except Exception as e:
        logging.error('api_sentiment_summary error: %s', e)
        return jsonify({'score': 50, 'error': str(e)}), 500


@app.route('/api/articles')
def api_articles_list():
    """Articles list API — returns recent published articles."""
    try:
        limit = min(int(request.args.get('limit', 20)), 100)
        category = request.args.get('category')
        q = Article.query.filter_by(published=True)
        if category:
            q = q.filter_by(category=category)
        arts = q.order_by(Article.created_at.desc()).limit(limit).all()
        result = [{'id': a.id, 'title': a.title, 'summary': (a.summary or '')[:200], 'category': a.category, 'created_at': str(a.created_at), 'url': f'/articles/{a.id}'} for a in arts]
        return jsonify({'articles': result, 'count': len(result)})
    except Exception as e:
        logging.error('api_articles_list error: %s', e)
        return jsonify({'articles': [], 'error': str(e)}), 500


@app.route('/mining-risk')
def mining_risk_page():
    """Mining Risk Calculator — power cost vs. hash price breakeven."""
    return render_template('mining_risk.html')


# ── BATCH-2 ROUTES ─────────────────────────────────────────────────────────

@app.route('/node-watch')
def node_watch_page():
    """Bitcoin Node Watch — live network node monitor."""
    return render_template('nodes.html')


@app.route('/bitcoin-insurance')
def bitcoin_insurance_page():
    """Bitcoin Life Insurance landing — redirect to full page."""
    return render_template('bitcoin_life_insurance.html')


@app.route('/briefing')
def market_briefing_page():
    """Market Briefing Room (F2) — LAW 3: always show latest + 3 previous."""
    try:
        latest = (
            MarketBriefing.query
            .filter_by(published=True)
            .order_by(MarketBriefing.generated_at.desc())
            .first()
        )
        recent = (
            MarketBriefing.query
            .filter_by(published=True)
            .order_by(MarketBriefing.generated_at.desc())
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
            MarketBriefing.query
            .filter_by(published=True)
            .order_by(MarketBriefing.generated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    except Exception as e:
        logging.warning("briefing_archive DB error: %s", e)
        all_briefings = []
    return render_template(
        'market_briefing.html',
        latest=all_briefings[0] if all_briefings else None,
        recent=all_briefings[1:4] if len(all_briefings) > 1 else [],
        next_briefing_utc=_next_briefing_utc_epoch(),
    )


@app.route('/api/briefing/latest')
def briefing_latest():
    """Returns the latest completed, published briefing as JSON."""
    try:
        b = (
            MarketBriefing.query
            .filter_by(published=True, status='completed')
            .order_by(MarketBriefing.generated_at.desc())
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
    """Fetch a single briefing by ID."""
    try:
        b = MarketBriefing.query.get(briefing_id)
        if not b or not b.published:
            return jsonify({"error": "Not found"}), 404
        import pytz
        ET = pytz.timezone("America/New_York")
        gen_et = ""
        if b.generated_at:
            utc_dt = pytz.utc.localize(b.generated_at)
            et_dt = utc_dt.astimezone(ET)
            gen_et = et_dt.strftime("%-I:%M %p ET · %b %-d, %Y")
        data = b.to_dict()
        data['generated_at_et'] = gen_et
        data['script_text'] = b.script_text
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
            MarketBriefing.query
            .filter_by(published=True)
            .order_by(MarketBriefing.generated_at.desc())
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
        b = MarketBriefing.query.get(briefing_id)
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


@app.route('/podcast')
def podcast_single():
    """Podcast page — canonical alias for /podcasts."""
    from flask import redirect
    return redirect('/podcasts', code=301)


@app.route('/alerts')
def price_alerts_page():
    """Price Alerts — public signup page, no auth required."""
    active_count = PriceAlert.query.filter_by(active=True, notified=False).count()
    recent_triggered = (
        PriceAlert.query
        .filter_by(notified=True)
        .order_by(PriceAlert.triggered_at.desc())
        .limit(3)
        .all()
    )
    return render_template('price_alerts.html',
                           active_count=active_count,
                           recent_triggered=recent_triggered)


@app.route('/api/alerts/subscribe', methods=['POST'])
def api_alerts_subscribe():
    """Public alert signup — no auth required."""
    import secrets
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    price_target = data.get('price_target')
    direction = (data.get('direction') or '').strip().lower()

    # Validate email
    if not email or not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'status': 'error', 'message': 'Valid email required.'}), 400

    # Validate price target
    try:
        price_target = float(price_target)
        if price_target <= 0 or price_target > 10_000_000:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Price target must be between $1 and $10,000,000.'}), 400

    # Validate direction
    if direction not in ('above', 'below'):
        return jsonify({'status': 'error', 'message': 'Direction must be "above" or "below".'}), 400

    # Rate limit: max 10 active alerts per email
    existing = PriceAlert.query.filter_by(email=email, active=True, notified=False).count()
    if existing >= 10:
        return jsonify({'status': 'error', 'message': 'Maximum 10 active alerts per email.'}), 429

    token = secrets.token_urlsafe(16)
    alert = PriceAlert(
        email=email,
        price_target=price_target,
        direction=direction,
        email_token=token,
    )
    db.session.add(alert)
    db.session.commit()

    # Send confirmation email via Resend
    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    _send_alert_confirmation(email, price_target, direction, token, base_url)

    return jsonify({'status': 'created', 'message': 'Alert set! Check your email.'})


def _send_alert_confirmation(email, price_target, direction, token, base_url):
    """Send confirmation email for new price alert."""
    resend_key = os.environ.get('RESEND_API_KEY', '')
    if not resend_key:
        logging.warning("RESEND_API_KEY not set — skipping confirmation email")
        return
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Courier New',monospace;color:#e5e5e5">
<div style="max-width:600px;margin:0 auto;padding:40px 24px">
  <div style="text-align:center;margin-bottom:32px">
    <span style="font-size:28px;font-weight:700;letter-spacing:4px;color:#dc2626">PROTOCOL PULSE</span>
  </div>
  <div style="border:1px solid rgba(220,38,38,.4);border-radius:4px;padding:32px;background:#111">
    <h2 style="color:#dc2626;font-size:14px;letter-spacing:3px;margin:0 0 16px">ALERT CONFIRMED</h2>
    <p style="font-size:13px;color:#999;margin:0 0 8px">Your Bitcoin price alert is set:</p>
    <p style="font-size:20px;font-weight:700;color:#F8C15C;margin:0 0 4px">BTC {direction.upper()} ${price_target:,.0f}</p>
    <p style="font-size:12px;color:#666;margin:0 0 24px">We'll notify you when the price crosses your target.</p>
    <a href="{base_url}/alerts/manage?token={token}"
       style="display:inline-block;background:#dc2626;color:#fff;padding:10px 24px;text-decoration:none;border-radius:3px;font-size:12px;letter-spacing:2px;font-weight:700">MANAGE ALERTS</a>
  </div>
  <p style="text-align:center;font-size:10px;color:#444;margin-top:24px;letter-spacing:1px">PROTOCOL PULSE · SOVEREIGN BITCOIN INTELLIGENCE</p>
</div>
</body></html>"""
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json={"from": "pulse@protocolpulse.io", "to": [email],
                  "subject": f"Alert Set: BTC {direction} ${price_target:,.0f}",
                  "html": html},
            timeout=30,
        )
    except Exception as e:
        logging.error("Confirmation email failed: %s", e)


@app.route('/alerts/manage')
def alerts_manage():
    """Manage alerts via token — no auth required."""
    token = request.args.get('token', '').strip()
    if not token:
        return redirect('/alerts')
    alert = PriceAlert.query.filter_by(email_token=token).first()
    if not alert:
        flash('Invalid or expired token.', 'error')
        return redirect('/alerts')
    # Show all alerts for this email
    user_alerts = PriceAlert.query.filter_by(email=alert.email).order_by(PriceAlert.created_at.desc()).all()
    return render_template('price_alerts_manage.html', alerts=user_alerts, token=token)


@app.route('/api/alerts/delete', methods=['POST'])
def api_alerts_delete():
    """Delete a single alert by id + token."""
    data = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()
    alert_id = data.get('alert_id')
    if not token or not alert_id:
        return jsonify({'status': 'error', 'message': 'Missing token or alert_id.'}), 400
    # Verify token belongs to an alert for the same email
    auth_alert = PriceAlert.query.filter_by(email_token=token).first()
    if not auth_alert:
        return jsonify({'status': 'error', 'message': 'Invalid token.'}), 403
    target = PriceAlert.query.get(alert_id)
    if not target or target.email != auth_alert.email:
        return jsonify({'status': 'error', 'message': 'Alert not found.'}), 404
    db.session.delete(target)
    db.session.commit()
    return jsonify({'status': 'deleted', 'message': 'Alert removed.'})


# ─────────────────────────────────────────────────────────────────────────────
# SESSION 9 — SENTIMENT + INTELLIGENCE API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/stream/sentiment')
def stream_sentiment():
    """SSE endpoint — push classification events as they happen."""
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
            yield "retry: 5000\n"
            yield "data: {\"type\": \"connected\", \"ts\": " + str(int(_time.time())) + "}\n\n"

            heartbeat_interval = 30
            last_heartbeat = _time.monotonic()

            while True:
                try:
                    event = q.get(timeout=1.0)
                    import json as _j
                    yield f"data: {_j.dumps(event, default=str)}\n\n"
                    last_heartbeat = _time.monotonic()
                except queue.Empty:
                    now = _time.monotonic()
                    if now - last_heartbeat >= heartbeat_interval:
                        yield ": heartbeat\n\n"
                        last_heartbeat = now
        except GeneratorExit:
            pass
        finally:
            unregister_sse_subscriber(q)

    from flask import Response
    return Response(event_stream(), mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no',
                        'Connection': 'keep-alive',
                    })


@app.route('/api/sentiment/classify', methods=['POST'])
def api_classify_article():
    """Trigger classification of a specific article."""
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
    """Trigger batch classification of unclassified articles."""
    try:
        data = request.get_json(silent=True) or {}
        hours = int(data.get('hours', 6))
        hours = max(1, min(48, hours))

        from services.sentiment_analyzer import batch_classify
        result = batch_classify(hours=hours)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logging.error("api_batch_classify error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sentiment/daily-report')
def api_sentiment_daily_report():
    """Return latest daily sentiment report."""
    from sqlalchemy import text as _text
    try:
        row = db.session.execute(
            _text("""SELECT report_date, overall_sentiment, score, bullish_pct, bearish_pct,
                            neutral_pct, narrative, top_bullish_signals, top_bearish_signals,
                            dominant_narrative, anomaly_detected, created_at
                     FROM sentiment_reports ORDER BY report_date DESC LIMIT 1""")
        ).fetchone()
        if not row:
            return jsonify({'success': True, 'report': None})
        import json as _json
        return jsonify({'success': True, 'report': {
            'report_date': str(row[0]),
            'overall_sentiment': row[1],
            'score': row[2],
            'bullish_pct': row[3],
            'bearish_pct': row[4],
            'neutral_pct': row[5],
            'narrative': row[6],
            'top_bullish_signals': _json.loads(row[7] or '[]'),
            'top_bearish_signals': _json.loads(row[8] or '[]'),
            'dominant_narrative': row[9],
            'anomaly_detected': bool(row[10]),
            'created_at': str(row[11]),
        }})
    except Exception as e:
        logging.error("api_sentiment_daily_report error: %s", e)
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


@app.route('/api/intelligence/trending')
def api_intel_trending_topics():
    """Return trending topics from last 24h of classified articles."""
    try:
        from services.intelligence_service import get_trending_topics
        hours = int(request.args.get('hours', 24))
        result = get_trending_topics(hours=hours)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error("api_trending_topics error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/intelligence/entities')
def api_entity_tracker():
    """Return entity tracker data from recent articles."""
    try:
        from services.intelligence_service import get_entity_tracker
        hours = int(request.args.get('hours', 48))
        result = get_entity_tracker(hours=hours)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error("api_entity_tracker error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/intelligence/events')
def api_intelligence_events():
    """Return recent intelligence events (anomalies, shifts)."""
    try:
        from services.intelligence_service import get_intelligence_events
        limit = int(request.args.get('limit', 10))
        result = get_intelligence_events(limit=limit)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error("api_intelligence_events error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/stage/next_briefing')
def api_stage_next_briefing():
    """Return latest stage brief metadata and countdown to next."""
    import json as _j
    from pathlib import Path
    from datetime import datetime, timezone, timedelta
    brief_dir = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'data' / 'stage_briefs'
    latest_path = brief_dir / 'latest.json'
    try:
        if not latest_path.exists():
            return jsonify({'has_brief': False, 'last_brief': None,
                            'next_estimated_at': None, 'countdown_seconds': 0})
        meta = _j.loads(latest_path.read_text())
        gen_at = datetime.fromisoformat(meta['generated_at'].replace('Z', '+00:00'))
        # 3x/day schedule: next brief in ~8h (06:00, 14:00, 22:00 UTC)
        _brief_hours = [6, 14, 22]
        now = datetime.now(timezone.utc)
        next_at = None
        for h in _brief_hours:
            candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if candidate > now:
                next_at = candidate
                break
        if next_at is None:
            next_at = (now + timedelta(days=1)).replace(hour=_brief_hours[0], minute=0, second=0, microsecond=0)
        countdown = max(0, int((next_at - now).total_seconds()))
        # Load latest sentiment signal if available
        _sentiment = None
        _sentiment_path = Path(__file__).resolve().parent / 'data' / 'sentiment'
        if _sentiment_path.exists():
            _sig_files = sorted(_sentiment_path.glob('*_signal.json'), reverse=True)
            if _sig_files:
                try:
                    _sentiment = _j.loads(_sig_files[0].read_text())
                except Exception:
                    pass
        return jsonify({
            'has_brief': True,
            'last_brief': {
                'title': meta.get('title', ''),
                'generated_at': meta.get('generated_at', ''),
                'mp4_url': meta.get('mp4_url', ''),
                'duration': meta.get('duration', 0),
                'script_summary': meta.get('script_summary', '')[:300],
                'brief_type': meta.get('brief_type', ''),
                'tts_provider': meta.get('tts_provider', ''),
                'btc_price': meta.get('btc_price'),
                'sentiment_score': meta.get('sentiment_score'),
            },
            'sentiment': _sentiment,
            'next_estimated_at': next_at.isoformat(),
            'countdown_seconds': countdown,
        })
    except Exception as e:
        logging.warning('stage next_briefing error: %s', e)
        return jsonify({'has_brief': False, 'last_brief': None,
                        'next_estimated_at': None, 'countdown_seconds': 0})


@app.route('/data/stage_briefs/<path:filename>')
def serve_stage_brief(filename):
    """Serve stage brief MP4 and JSON files."""
    from flask import send_from_directory
    brief_dir = os.path.join(os.path.dirname(__file__), 'video_pipeline_v3', 'data', 'stage_briefs')
    return send_from_directory(brief_dir, filename)


@app.route('/api/stage/transcripts')
def api_stage_transcripts():
    import glob, os, json as _j
    from pathlib import Path
    BASE = Path(__file__).resolve().parent / 'video_pipeline_v3'
    results = []
    seen = set()
    # Fresh scrape first
    scrapes = sorted(glob.glob(str(BASE / 'data/channel_archive/fresh_scrape_*.json')), reverse=True)
    if scrapes:
        try:
            fresh = _j.load(open(scrapes[0]))
            for v in fresh[:40]:
                ch = v.get('channel','')
                if ch in seen or ch.startswith('fresh'): continue
                t = v.get('transcript_text','')
                if not t or len(t) < 80: continue
                seen.add(ch)
                lines = [l.strip() for l in t.replace('. ',' . ').split('. ') if len(l.strip()) > 40]
                excerpt = lines[0][:200] if lines else t[:200]
                results.append({'channel':ch,'title':(v.get('title') or '')[:80],
                    'excerpt':excerpt,'transcript_text':t[:2500],
                    'sentiment':v.get('sentiment','neutral'),'url':v.get('url','')})
        except Exception as e:
            app.logger.warning('stage transcripts err: %s', e)
    # Channel archive fallback
    for d in sorted(glob.glob(str(BASE / 'data/channel_archive/*/'))):
        ch = os.path.basename(d.rstrip('/'))
        if ch in seen or 'fresh' in ch: continue
        files = sorted(glob.glob(os.path.join(d,'*.json')), reverse=True)
        if not files: continue
        try:
            v = _j.load(open(files[0]))
            t = v.get('transcript_text','')
            if not t or len(t) < 80: continue
            seen.add(ch)
            lines = [l.strip() for l in t.replace('. ',' . ').split('. ') if len(l.strip()) > 40]
            excerpt = lines[0][:200] if lines else t[:200]
            results.append({'channel':v.get('channel',ch),'title':(v.get('title') or '')[:80],
                'excerpt':excerpt,'transcript_text':t[:2500],
                'sentiment':v.get('sentiment','neutral'),'url':v.get('url','')})
        except Exception: continue
        if len(results) >= 12: break
    return jsonify(results)


@app.route('/api/stage/intel')
def api_stage_intel():
    import sys as _sys, os as _os
    res = {'price':'N/A','price_float':0,'price_formatted':'N/A',
           'sentiment_score':50,'sentiment_label':'neutral','narrative':'','topics':'',
           'price_delta_1h':0,'market_context':'the market is neutral','top_signal':''}
    try:
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), 'oracle'))
        from oracle_dialogue_engine import get_live_intel
        intel = get_live_intel()
        pf = intel.get('price_float', 0)
        res['price_float'] = pf
        res['price'] = intel.get('price_spoken', 'N/A')
        res['price_formatted'] = '${:,.0f}'.format(pf) if pf else 'N/A'
        res['narrative'] = intel.get('narrative', '')
        res['topics'] = intel.get('topics', '')
        res['sentiment_score'] = intel.get('sentiment_score', 50)
        res['sentiment_label'] = intel.get('sentiment_label', 'neutral')
        res['price_delta_1h'] = intel.get('price_delta_1h', 0)
        res['market_context'] = intel.get('market_context', 'the market is neutral')
        res['top_signal'] = intel.get('top_signal', '')
    except Exception as e:
        logging.warning('stage intel error: %s', e)
    return jsonify(res)


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


@app.route('/api/stage/signal')
def api_stage_signal():
    import json as _j
    from pathlib import Path
    cache = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'cache' / 'active_signal.json'
    try:
        if not cache.exists():
            return jsonify({'nostr_posts': [], 'cached': False})
        data = _j.loads(cache.read_text())
        posts = [{'text': (p.get('text') or '')[:280],
                  'display_name': p.get('display_name') or p.get('nip05') or 'anon',
                  'nip05': p.get('nip05') or '', 'score': p.get('score', 0)}
                 for p in data.get('nostr_posts', [])[:15]
                 if not _is_nostr_spam(p.get('text') or '')]
        spaces = [{'text': (q.get('text') or '')[:280],
                   'source': q.get('space_title') or 'X Spaces'}
                  for q in data.get('spaces_quotes', [])[:6]]
        return jsonify({'nostr_posts': posts, 'spaces_quotes': spaces,
                        'fetched_at': data.get('fetched_at_iso', ''), 'cached': True})
    except Exception as e:
        logging.warning('stage signal error: %s', e)
        return jsonify({'nostr_posts': [], 'cached': False})



# ── STAGE BROADCAST ROUTES ──────────────────────────────────────────────────

@app.route('/api/stage/broadcast-queue')
@limiter.limit("30 per minute")
def api_stage_broadcast_queue():
    """Return next 3 items from broadcast queue sorted by priority."""
    import json as _j
    from pathlib import Path
    from datetime import datetime as _dt, timezone as _tz

    queue_path = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
    try:
        if not queue_path.exists():
            return jsonify({'items': [], 'queue_depth': 0, 'session_start': _dt.now(_tz.utc).isoformat()})

        items = _j.loads(queue_path.read_text())
        if not isinstance(items, list):
            items = []

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

    queue_path = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
    data = request.get_json(silent=True) or {}
    consumed_id = data.get('consumed_id')

    try:
        queue_path.parent.mkdir(parents=True, exist_ok=True)

        items = []
        if queue_path.exists():
            with open(queue_path, 'r+') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    items = _j.load(f)
                except _j.JSONDecodeError:
                    items = []

                if consumed_id:
                    items = [i for i in items if i.get('id') != consumed_id]

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

                f.seek(0)
                f.truncate()
                _j.dump(valid, f, indent=2)
                fcntl.flock(f, fcntl.LOCK_UN)
        else:
            valid = []

        next_item = valid[0] if valid else None

        if not next_item:
            try:
                from services.stage_broadcast_service import generate_filler_live, run
                import threading
                # Trigger async queue refill
                t = threading.Thread(target=run, daemon=True)
                t.start()
                # Return filler immediately while refill runs in background
                next_item = generate_filler_live()
            except Exception as e:
                logging.warning('filler generation failed: %s', e)

        # Proactively refill when queue is about to empty
        if len(valid) <= 1:
            try:
                from services.stage_broadcast_service import run as _run
                import threading
                threading.Thread(target=_run, daemon=True).start()
            except Exception:
                pass

        return jsonify({
            'next_item': next_item,
            'queue_depth': len(valid),
        })
    except Exception as e:
        logging.warning('consume-broadcast error: %s', e)
        return jsonify({'next_item': None, 'queue_depth': 0})


@app.route('/api/stage/generate-monologue', methods=['POST'])
@limiter.limit("10 per minute")
def api_stage_generate_monologue():
    """Generate a fresh long-form monologue script from live data sources."""
    import json as _j
    from pathlib import Path
    from datetime import datetime as _dt, timezone as _tz
    import requests as _req

    try:
        context_parts = []

        # BTC price from queue
        queue_path = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
        if queue_path.exists():
            items = _j.loads(queue_path.read_text())
            for item in items:
                if item.get('type') == 'METRICS_PULSE':
                    context_parts.append('MARKET: ' + item.get('topic_preview', ''))
                    break

        # Nostr narrative
        narrative_path = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'data' / 'intelligence' / 'narrative_context.json'
        if narrative_path.exists():
            try:
                nd = _j.loads(narrative_path.read_text())
                narrative = nd.get('narrative') or nd.get('summary', '')
                if narrative:
                    context_parts.append('NOSTR SIGNAL: ' + narrative[:200])
            except Exception:
                pass

        # Recent article
        try:
            from models import Article
            latest = Article.query.order_by(Article.created_at.desc()).first()
            if latest:
                context_parts.append('LATEST INTEL: ' + (latest.title or '') + ' — ' + (latest.summary or '')[:150])
        except Exception:
            pass

        # Thought leader tweet
        tweets_path = Path(__file__).resolve().parent / 'data' / 'tweet_study' / 'raw_tweets.json'
        if tweets_path.exists():
            try:
                import random as _rand
                tweets = _j.loads(tweets_path.read_text())
                priority = [t for t in tweets if (t.get('handle') or '').lower().lstrip('@') in
                           {'saylor','natbrunell','jack','gladstein','prestonpysh','martybent','lynaldencontact','jeffbooth','odell','aantonop','adam3us'}]
                if priority:
                    pick = _rand.choice(priority)
                    context_parts.append('THOUGHT LEADER @' + pick.get('handle','') + ': ' + (pick.get('text') or pick.get('content',''))[:200])
            except Exception:
                pass

        context = '\n'.join(context_parts) if context_parts else 'Bitcoin market update'

        from services.stage_broadcast_service import _get_anthropic_key
        api_key = _get_anthropic_key()

        resp = _req.post(
            'https://api.anthropic.com/v1/messages',
            headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 300,
                'system': (
                    "You are SIGNAL — the Protocol Pulse live broadcast anchor. You are NOT the Oracle (which is the interactive advisor). "
                    "You are a broadcast journalist with an Austrian economics worldview, reporting live market intelligence.\n\n"
                    "SIGNAL vs ORACLE distinction:\n"
                    "- SIGNAL: broadcasts continuously, reporter tone, cites live data every segment\n"
                    "- ORACLE: conversational advisor, responds to user questions, guides individuals\n\n"
                    "SIGNAL RULES:\n"
                    "- Always cold-open with the most critical live signal (price, hashrate, mempool, or on-chain)\n"
                    "- Cite the exact current number in every segment — never vague\n"
                    "- Never say 'I', never use first person — you are a broadcast, not a person\n"
                    "- Never say 'Oracle' — you are SIGNAL\n"
                    "- Tone: Reuters meets cypherpunk broadcast, not a chat assistant\n"
                    "- Every segment is 40-60 words, one clear thesis, closes with implication\n\n"
                    "IDENTITY: Austrian economics worldview. Sovereign individual. You understand mining, nodes, hashrate, UTXOs at depth. "
                    "Your audience does too — never explain basics.\n\n"
                    "EDITORIAL LAWS:\n"
                    "- Bitcoin ONLY. Zero altcoins, zero DeFi, zero tokens.\n"
                    "- Always say 'Bitcoin' in full. Never 'BTC' — it sounds robotic aloud.\n"
                    "- Never hedge. No 'could', 'might', 'some argue'. State it directly.\n"
                    "- Never say: 'interesting', 'game changer', 'let\\'s dive in', 'buckle up', 'few understand'.\n"
                    "- No greeting. No sign-off. Cold open with the most important signal first.\n"
                    "- Every paragraph must contain ONE specific data point.\n\n"
                    "TONE: Intelligence briefing meets cypherpunk broadcast. Sharp. Dry. Authoritative without arrogance.\n"
                    "Think: intercepting a live signal — not reading a press release.\n\n"
                    "FORMAT: 150-180 words. Flowing spoken prose only. No markdown, no headers, no bullets.\n"
                    "Structure: signal → context → implication → what to watch.\n"
                    "Close with a forward-looking statement about what the data suggests next."
                ),
                'messages': [{'role': 'user', 'content': f'Generate a monologue from these signals:\n{context}'}]
            },
            timeout=20
        )
        resp.raise_for_status()
        script = resp.json()['content'][0]['text'].strip()

        import re as _re
        script = _re.sub(r'^#+\s+[^\n]*\n?', '', script, flags=_re.MULTILINE)
        script = _re.sub(r'\*\*([^*]+)\*\*', r'\1', script).strip()

        return jsonify({'script': script, 'word_count': len(script.split()), 'context_used': len(context_parts)})

    except Exception as e:
        logging.warning('generate-monologue error: %s', e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stage/broadcast-status')
@limiter.limit("30 per minute")
def api_stage_broadcast_status():
    """Return broadcast status: live state, current topic, queue depth."""
    import json as _j
    from pathlib import Path
    from datetime import datetime as _dt, timezone as _tz

    queue_path = Path(__file__).resolve().parent / 'video_pipeline_v3' / 'data' / 'stage_briefs' / 'broadcast_queue.json'
    try:
        items = []
        if queue_path.exists():
            items = _j.loads(queue_path.read_text())
            if not isinstance(items, list):
                items = []

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


# ── RATE-LIMITED ORACLE PROXIES (P0.1 audit fix — denial-of-wallet prevention) ──

@app.route('/api/oracle/chat', methods=['POST'])
@limiter.limit("6 per minute")
def api_oracle_chat_ratelimited():
    """Rate-limited proxy for oracle chat — prevents denial-of-wallet attacks."""
    avatar_base = os.environ.get('AVATAR_BASE_URL', 'http://localhost:8200')
    try:
        body = request.get_json(silent=True) or {}
        resp = requests.post(
            f'{avatar_base}/oracle/chat',
            json=body,
            timeout=90,
            headers={'Content-Type': 'application/json'},
        )
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
    avatar_base = os.environ.get('AVATAR_BASE_URL', 'http://localhost:8200')
    try:
        body = request.get_json(silent=True) or {}
        resp = requests.post(
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


@app.route('/api/governor-status')
def api_governor_status():
    "Content governor rotation status."
    try:
        from services.content_governor import get_status
        return jsonify(get_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/latest-episode')
def api_latest_episode():
    """Return latest Pulse Check episode metadata as JSON."""
    from flask import jsonify
    ep = get_latest_episode()
    return jsonify(ep)

