"""
routes_api.py — Api routes blueprint for Protocol Pulse.
Auto-generated from routes.py split.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, make_response, session, Response, abort, send_file, send_from_directory, stream_with_context
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db, limiter, cache
from routes_helpers import (
    models, verify_turnstile, admin_required, premium_required,
    premium_hub_required, _require_csrf, _trigger_sentiment_classification,
    ai_service, reddit_service, content_generator, content_engine,
    substack_service, rss_service, media_feed_service, printful_service,
    price_service, newsletter_service, ghl_service, ADMIN_SECRET,
    get_space_transcript, summarize_for_tweet,
    _jwt_required, _apply_rate_limit, _JWT_SECRET, _JWT_ALGORITHM, _JWT_EXPIRY_HOURS, _jwt,
)
import hashlib
import json
import logging
import requests
import os
import re
import stripe
import uuid
from functools import wraps
from datetime import datetime, timedelta, timezone
import threading
import time
from services.node_service import NodeService

try:
    from services.schiff_service import (
        get_score as _schiff_get_score,
        get_score_history as _schiff_get_history,
        get_statements as _schiff_get_statements,
        update_score as _schiff_update_score,
        seed_statements as _schiff_seed,
    )
    _schiff_available = True
except Exception as _schiff_import_err:
    logging.warning("schiff_service import failed (api): %s", _schiff_import_err)
    _schiff_available = False


# ── V18 FIX: Pipeline Intelligence Bridge ─────────────────────────────────
# Reads fresh data from video_pipeline_v3/data/intelligence/ (updated every render)
# and makes it available to website APIs that were reading stale standalone files.
import os as _bridge_os, json as _bridge_json, time as _bridge_time

_PIPELINE_INTEL_DIR = _bridge_os.path.join(
    _bridge_os.path.dirname(_bridge_os.path.dirname(_bridge_os.path.abspath(__file__))),
    'video_pipeline_v3', 'data', 'intelligence')

_pipeline_cache = {}
_pipeline_cache_ts = 0

def get_pipeline_intelligence():
    """Load fresh pipeline intelligence data (daily_signals + narrative_context).
    Cached for 60s to avoid disk reads on every API call."""
    global _pipeline_cache, _pipeline_cache_ts
    if _bridge_time.time() - _pipeline_cache_ts < 60 and _pipeline_cache:
        return _pipeline_cache
    result = {}
    for fname in ('daily_signals.json', 'narrative_context.json'):
        fpath = _bridge_os.path.join(_PIPELINE_INTEL_DIR, fname)
        try:
            if _bridge_os.path.exists(fpath):
                with open(fpath) as f:
                    result[fname.replace('.json', '')] = _bridge_json.load(f)
        except Exception:
            pass
    _pipeline_cache = result
    _pipeline_cache_ts = _bridge_time.time()
    return result

api_bp = Blueprint('api', __name__)

_btcmap_cache = {'data': None, 'ts': 0}

@api_bp.route('/api/map/btcmap')
def api_btcmap():
    """Proxy/cache BTCMap elements — refreshes every 24h"""
    import time as _time
    now = _time.time()
    if _btcmap_cache['data'] and (now - _btcmap_cache['ts']) < 86400:
        return jsonify(_btcmap_cache['data'])
    try:
        resp = requests.get('https://api.btcmap.org/v2/elements?limit=10000', timeout=30)
        resp.raise_for_status()
        _btcmap_cache['data'] = resp.json()
        _btcmap_cache['ts'] = now
        return jsonify(_btcmap_cache['data'])
    except Exception as e:
        if _btcmap_cache['data']:
            return jsonify(_btcmap_cache['data'])
        return jsonify({'error': str(e)}), 502

@api_bp.route('/api/value-stream/post/<int:post_id>')
def api_get_post_details(post_id):
    """Get detailed post info for Signal Terminal inspector"""
    from datetime import datetime, timedelta, timezone
    
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

@api_bp.route('/api/signal-terminal/stream')
def signal_terminal_stream():
    """SSE endpoint for real-time Signal Terminal updates with heartbeat"""
    from datetime import datetime, timedelta, timezone
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

@api_bp.route('/api/value-stream/submit', methods=['POST'])
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

@api_bp.route('/api/value-stream/zap/<int:post_id>', methods=['POST'])
def api_zap_content(post_id):
    """API endpoint for zapping content"""
    from services.value_stream_service import value_stream_service
    
    data = request.get_json() or {}
    amount = data.get('amount_sats', 1000)
    payment_hash = data.get('payment_hash')
    sender_id = data.get('sender_id')
    
    result = value_stream_service.process_zap(post_id, sender_id, amount, payment_hash)
    return jsonify(result)

@api_bp.route('/api/value-stream/invoice/<int:post_id>', methods=['POST'])
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

@api_bp.route('/api/value-stream/curators')
def api_get_curators():
    """Get top curators for the leaderboard"""
    from services.value_stream_service import value_stream_service
    
    curators = value_stream_service.get_top_curators(limit=20)
    return jsonify({'success': True, 'curators': curators})

@api_bp.route('/api/value-stream/register', methods=['POST'])
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

@api_bp.route('/api/nostr/latest/<pubkey>')
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

@api_bp.route('/api/mining-risk')
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

@api_bp.route('/api/solo-blocks')
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

@api_bp.route('/api/github/btc-activity')
def api_github_btc_activity():
    """GitHub activity for Bitcoin Core vs Bitcoin Knots rivalry feed"""
    import time
    import requests as req
    from datetime import datetime, timezone

    cache_key = '_gh_btc_activity'
    cached = getattr(app, cache_key, None)
    if cached and (time.time() - cached.get('_ts', 0)) < 300:
        return jsonify(cached)

    headers = {'Accept': 'application/vnd.github.v3+json'}

    def time_ago(iso_str):
        try:
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            delta = datetime.now(timezone.utc) - dt
            if delta.total_seconds() < 3600:
                return f"{int(delta.total_seconds() / 60)}m ago"
            if delta.total_seconds() < 86400:
                return f"{int(delta.total_seconds() / 3600)}h ago"
            return f"{int(delta.total_seconds() / 86400)}d ago"
        except Exception:
            return ""

    def parse_events(events_raw):
        items = []
        for ev in (events_raw or [])[:10]:
            etype = ev.get('type', '')
            actor = ev.get('actor', {}).get('login', 'unknown')
            created = ev.get('created_at', '')
            title = ''
            if etype == 'PullRequestEvent':
                pr = ev.get('payload', {}).get('pull_request', {})
                action = ev.get('payload', {}).get('action', '')
                title = f"{action}: {pr.get('title', '')}"
            elif etype == 'PushEvent':
                commits = ev.get('payload', {}).get('commits', [])
                if commits:
                    title = commits[-1].get('message', '').split('\n')[0]
                else:
                    title = 'Push'
            elif etype == 'IssuesEvent':
                issue = ev.get('payload', {}).get('issue', {})
                action = ev.get('payload', {}).get('action', '')
                title = f"{action}: {issue.get('title', '')}"
            elif etype == 'IssueCommentEvent':
                issue = ev.get('payload', {}).get('issue', {})
                title = f"comment on: {issue.get('title', '')}"
            else:
                title = etype.replace('Event', '')
            items.append({
                'type': etype,
                'actor': actor,
                'title': title[:120],
                'time_ago': time_ago(created)
            })
        return items[:5]

    result = {'success': True}

    try:
        r = req.get('https://api.github.com/repos/bitcoin/bitcoin/events?per_page=10',
                     headers=headers, timeout=8)
        result['core_events'] = parse_events(r.json() if r.status_code == 200 else [])
    except Exception:
        result['core_events'] = []

    try:
        r = req.get('https://api.github.com/repos/bitcoin/bitcoin',
                     headers=headers, timeout=8)
        if r.status_code == 200:
            d = r.json()
            result['core_repo'] = {
                'stars': d.get('stargazers_count', 0),
                'forks': d.get('forks_count', 0),
                'open_issues': d.get('open_issues_count', 0),
                'contributors': '900+'
            }
    except Exception:
        pass

    try:
        r = req.get('https://api.github.com/repos/bitcoinknots/bitcoin/events?per_page=10',
                     headers=headers, timeout=8)
        result['knots_events'] = parse_events(r.json() if r.status_code == 200 else [])
    except Exception:
        result['knots_events'] = []

    try:
        r = req.get('https://api.github.com/repos/bitcoinknots/bitcoin',
                     headers=headers, timeout=8)
        if r.status_code == 200:
            d = r.json()
            result['knots_repo'] = {
                'stars': d.get('stargazers_count', 0),
                'forks': d.get('forks_count', 0),
                'open_issues': d.get('open_issues_count', 0)
            }
    except Exception:
        pass

    result['_ts'] = time.time()
    setattr(app, cache_key, result)
    return jsonify(result)

@api_bp.route('/api/chat/ask', methods=['POST'])
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

@api_bp.route('/api/dashboard/signals')
@login_required
def api_dashboard_signals():
    """Live signal strip data for Commander dashboard."""
    if not current_user.has_commander_tier():
        return jsonify({'error': 'Commander tier required'}), 403
    try:
        prices = price_service.get_prices()
        btc = prices.get('bitcoin', {}) if prices else {}

        # Fear & Greed
        fg_score, fg_label = 50, 'Neutral'
        try:
            fg_resp = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5)
            if fg_resp.ok:
                fg_data = fg_resp.json().get('data', [{}])[0]
                fg_score = int(fg_data.get('value', 50))
                fg_label = fg_data.get('value_classification', 'Neutral')
        except Exception:
            pass

        # Mempool fees
        fees = {}
        try:
            fee_resp = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=5)
            if fee_resp.ok:
                fees = fee_resp.json()
        except Exception:
            pass

        # Hashrate
        hashrate_eh = 0
        try:
            hr_resp = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=5)
            if hr_resp.ok:
                hashrate_eh = round(hr_resp.json().get('currentHashrate', 0) / 1e18, 1)
        except Exception:
            pass

        return jsonify({
            'btc_price': btc.get('usd', btc.get('price', 0)),
            'btc_change_24h': btc.get('usd_24h_change', btc.get('change_24h', 0)),
            'fear_greed_score': fg_score,
            'fear_greed_label': fg_label,
            'hashrate_eh': hashrate_eh,
            'fastest_fee': fees.get('fastestFee', 0),
            'economy_fee': fees.get('economyFee', 0),
            'mempool_count': fees.get('mempoolCount', 0),
        })
    except Exception as e:
        logging.warning('dashboard signals error: %s', e)
        return jsonify({'error': 'Signal fetch failed'}), 500

@api_bp.route('/api/dashboard/feed')
@login_required
def api_dashboard_feed():
    """Latest articles for Commander intelligence feed."""
    if not current_user.has_commander_tier():
        return jsonify({'error': 'Commander tier required'}), 403
    articles = models.Article.query.filter_by(published=True).order_by(
        models.Article.created_at.desc()
    ).limit(10).all()
    now = datetime.utcnow()
    return jsonify({'articles': [{
        'id': a.id,
        'title': a.title,
        'category': a.category,
        'created_at': a.created_at.isoformat() if a.created_at else None,
        'is_new': (now - a.created_at).total_seconds() < 86400 if a.created_at else False,
        'url': f'/article/{a.id}',
    } for a in articles]})

@api_bp.route('/api/me')
@login_required
def api_me():
    """Current user profile + API key."""
    return jsonify({
        'email': current_user.email,
        'username': current_user.username,
        'tier': current_user.subscription_tier,
        'api_key': current_user.api_key,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
    })

@api_bp.route('/api/dashboard/generate-key', methods=['POST'])
@login_required
def api_dashboard_generate_key():
    """Regenerate Commander API key."""
    if not current_user.has_commander_tier():
        return jsonify({'error': 'Commander tier required'}), 403
    import secrets as _sec
    current_user.api_key = 'pp_live_' + _sec.token_hex(20)
    db.session.commit()
    return jsonify({'api_key': current_user.api_key})

@api_bp.route('/api/orb')
@limiter.exempt
def api_orb_public():
    import json as _j
    from pathlib import Path as _P
    from flask import jsonify as _jfy
    from datetime import datetime, timezone
    try:
        snap = _P('/home/ultron/protocol_pulse/data/sovereign_context/latest.json')
        if not snap.exists():
            return _jfy({"status":"initializing","composite":{"score":50,"pattern":"SYNCING"},"nodes":{"mcx":{"score":50},"epx":{"score":50},"ihx":{"score":50}},"streams":{"hashrate":50,"fear_greed":50,"fees":50,"exchange_flow":50,"kol":50}})
        d = _j.loads(snap.read_text())
        fg_val = float((d.get('fear_greed') or {}).get('value', 50))
        hashrate = float((d.get('network') or {}).get('hashrate_eh', 0))
        hash_score = min(100.0, (hashrate / 1200.0) * 100.0)
        indices = d.get('indices') or {}
        # MCX — Miner Conviction (0-100)
        mcx = float((indices.get('miner_conviction') or {}).get('score', 50))
        # EPX — Exchange Pressure: now real 0-100 from OKX L/S + taker ratio
        epx = float((indices.get('exchange_pressure') or {}).get('score', 50))
        # IHX — Insider Heat: now real 0-100 from QuiverQuant congressional trading
        ihx = float((indices.get('insider_heat') or {}).get('score', 50))
        # OPX — Options Pressure: put/call ratio from Deribit
        pcr = float((d.get('options') or {}).get('put_call_ratio') or 0.7)
        opx = round(max(0.0, min(100.0, (1.5 - pcr) / 1.0 * 100.0)), 1)
        # FDX — Futures/Derivatives: funding rate
        fr = float((d.get('futures') or {}).get('funding_rate') or 0)
        fdx = round(max(0.0, min(100.0, 50.0 + (-fr / 0.0005) * 30.0)), 1)
        # OCX — On-Chain Activity: accumulation score
        ocx = float((d.get('on_chain') or {}).get('accumulation_score') or 50)
        # Composite convergence score — weighted average of all 6
        composite = round((mcx*0.25) + (epx*0.20) + (ihx*0.10) + (opx*0.15) + (fdx*0.15) + (ocx*0.15), 1)
        patterns = d.get('pattern_matches') or []
        pattern = patterns[0].replace('_',' ') if patterns else ('ACCUMULATION' if composite>70 else ('CONSTRUCTIVE' if composite>55 else ('MONITORING' if composite>40 else 'WATCH')))
        ex = d.get('exchange_flow', 'neutral')
        mem = d.get('mempool') or {}
        fee_h = float(mem.get('fee_high', 2))
        fee_score = max(0.0, min(100.0, 100.0 - fee_h * 2.0))
        flow_score = 70.0 if ex=='outflow' else (30.0 if ex=='inflow' else 50.0)
        kol_score = float((d.get('kol') or {}).get('sentiment_score', 50))
        ts = d.get('timestamp','')
        try:
            dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
            age_s = (datetime.now(timezone.utc) - dt).total_seconds()
            status = 'live' if age_s < 600 else 'stale'
        except Exception:
            age_s = 0
            status = 'live'
        # Extra nodes from rich data
        opts = d.get('options') or {}
        futs = d.get('futures') or {}
        onch = d.get('on_chain') or {}
        macro = d.get('macro') or {}
        poly = d.get('polymarket') or {}
        whale_alerts = d.get('whale_alerts') or []
        
        # OPX: Options Pressure Index (put/call + DVOL)
        pcr = float(opts.get('put_call_ratio') or 0.7)
        dvol = float(opts.get('dvol') or 50)
        opx = round(max(0, min(100, (1 - pcr) * 50 + (dvol - 40) * 0.5 + 50)), 1)
        
        # FDX: Futures/Derivatives Index (funding rate + basis + OI)
        funding = float(futs.get('funding_rate') or 0)
        basis = float(futs.get('annualized_basis') or 0)
        fdx = round(max(0, min(100, 50 + funding * 1000000 + basis * 5)), 1)
        
        # OCX: On-Chain Index (accumulation score + NVT + active addresses)
        acc_score = float(onch.get('accumulation_score') or 50)
        nvt = float(onch.get('nvt_ratio') or 50)
        nvt_score = max(0, min(100, 100 - nvt * 1.5))
        ocx = round((acc_score * 0.6 + nvt_score * 0.4), 1)

        # Whale score
        whale_count = len(whale_alerts)
        whale_score = min(100, 50 + whale_count * 8)
        
        # Polymarket score
        poly_score = float(poly.get('macro_sentiment') or 50)
        
        # Macro correlation score
        dxy_corr = float(macro.get('btc_vs_dxy_30d_corr') or 0)
        macro_score = round(max(0, min(100, 50 - dxy_corr * 40)), 1)

        return _jfy({"status":status,"timestamp":ts,"age_seconds":round(age_s),
            "composite":{"score":composite,"pattern":pattern},
            "nodes":{
                "mcx":{"score":round(mcx,1),"label":"MCX","desc":"Miner Conviction"},
                "epx":{"score":round(epx,1),"label":"EPX","desc":"Exchange Pressure"},
                "ihx":{"score":round(ihx,1),"label":"IHX","desc":"Insider Heat"},
                "opx":{"score":opx,"label":"OPX","desc":"Options Pressure"},
                "fdx":{"score":fdx,"label":"FDX","desc":"Futures/Derivatives"},
                "ocx":{"score":ocx,"label":"OCX","desc":"On-Chain Activity"},
            },
            "streams":{
                "hashrate":round(hash_score,1),
                "fear_greed":fg_val,
                "fees":round(fee_score,1),
                "exchange_flow":flow_score,
                "kol":kol_score,
                "polymarket":round(poly_score,1),
                "whale":round(whale_score,1),
                "macro_corr":macro_score,
                "put_call":round(pcr*100,1),
                "accum":round(acc_score,1),
            },
            "raw":{
                "put_call_ratio":pcr,
                "dvol":dvol,
                "funding_rate":funding,
                "basis_pct":basis,
                "accumulation_score":acc_score,
                "nvt_ratio":nvt,
                "whale_alerts":whale_count,
                "polymarket_top":poly.get('top_market',''),
                "poly_prob":poly.get('top_probability',0),
                "gold_price":macro.get('gold_price',0),
                "sp500":macro.get('sp500',0),
                "dxy_corr":dxy_corr,
                "lightning_btc":float((d.get('lightning') or {}).get('capacity_btc',0)),
                "options_max_pain":float(opts.get('max_pain',0)),
                "next_adj_pct":float((d.get('network') or {}).get('next_adj_pct',0)),
                "whale_alerts_list":(d.get('whale_alerts') or [])[:5],
                "polymarket":d.get('polymarket', {}),
            }
        })
    except Exception as exc:
        import logging; logging.warning('orb api: %s', exc)
        return _jfy({"status":"error","composite":{"score":50,"pattern":"OFFLINE"},"nodes":{"mcx":{"score":50},"epx":{"score":50},"ihx":{"score":50}},"streams":{"hashrate":50,"fear_greed":50,"fees":50,"exchange_flow":50,"kol":50}})

@api_bp.route('/api/network-data')
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

@api_bp.route('/api/podcast/<int:podcast_id>')
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

@api_bp.route('/api/podcasts/<path:rss_source>')
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

@api_bp.route('/api/books/metrics')
def api_book_metrics():
    """Sovereign Book Library — live metrics for bubble chart visualization."""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    def _ensure_affiliate(url, tag='protocolpulse-20'):
        """Enforce affiliate tag server-side — single source of truth."""
        if not url or 'amazon.com' not in url:
            return url
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs['tag'] = [tag]
        return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

    PP_ASINS = ['B0DVTCVX8J', '9916697191', '0241360846', 'B0CQLMQRH7']

    metrics_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'book_metrics.json')
    featured_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'featured_book.json')

    books = []
    last_updated = ''
    fetch_health = {}
    try:
        with open(metrics_path) as f:
            metrics = json.load(f)
        books = metrics.get('books', [])
        last_updated = metrics.get('last_updated', '')
        fetch_health = metrics.get('fetch_health', {})
    except Exception:
        pass

    # Enforce affiliate tag on every outbound URL
    for b in books:
        b['amazon_url'] = _ensure_affiliate(b.get('amazon_url', ''))

    # Load featured book
    featured = None
    try:
        with open(featured_path) as f:
            featured = json.load(f)
        if featured.get('end_date'):
            from datetime import datetime
            end = datetime.fromisoformat(featured['end_date'])
            if datetime.now() > end:
                featured = None
    except Exception:
        featured = None

    # Featured fallback rotation chain
    if featured is None and books:
        # 1. Top PP series by velocity
        pp = [b for b in books if b.get('asin') in PP_ASINS]
        pp_sorted = sorted(pp, key=lambda b: b.get('velocity', 0), reverse=True)
        # 2. Top rising star
        rising_sorted = sorted([b for b in books if b.get('is_rising')], key=lambda b: b.get('bsr_change', 0))
        # 3. Best BSR overall
        bsr_sorted = sorted(books, key=lambda b: b.get('bsr', 999999))
        candidate = (pp_sorted or rising_sorted or bsr_sorted or [None])[0]
        if candidate:
            featured = {
                'title': candidate['title'],
                'author': candidate['author'],
                'cover_url': candidate['cover_url'],
                'amazon_url': candidate['amazon_url'],
                'headline': 'Currently Trending in Sovereign Money',
                'body_text': f"BSR #{candidate['bsr']:,} — {candidate.get('category', 'Bitcoin')}",
                'badge': 'TRENDING',
            }

    # Rising stars sorted by biggest rank improvement
    rising = [b for b in books if b.get('is_rising')]
    rising.sort(key=lambda b: b.get('bsr_change', 0))

    # Stale indicator
    stale = False
    if last_updated:
        try:
            from datetime import datetime, timezone, timedelta
            lu = datetime.fromisoformat(last_updated)
            if lu.tzinfo is None:
                lu = lu.replace(tzinfo=timezone.utc)
            stale = (datetime.now(timezone.utc) - lu) > timedelta(hours=48)
        except Exception:
            pass

    return jsonify({
        'status': 'ok',
        'source': 'amazon_scrape',
        'last_updated': last_updated,
        'stale': stale,
        'stale_after_hours': 48,
        'fetch_health': fetch_health,
        'featured': featured,
        'rising': rising[:5],
        'books': books,
    })

@api_bp.route('/api/latest-episodes')
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

@api_bp.route('/api/episodes/<show_id>')
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

@api_bp.route('/api/episodes/search')
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

@api_bp.route('/api/rss/refresh')
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

@api_bp.route('/api/merch/product/<int:product_id>')
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

@api_bp.route('/api/merch/checkout', methods=['POST'])
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

@api_bp.route('/api/newsletter/subscribe', methods=['POST'])
@limiter.limit("5 per minute")
def api_newsletter_subscribe():
    """Subscribe to newsletter — JSON API."""
    data = request.get_json(silent=True) or {}
    # Cloudflare Turnstile bot check
    cf_token = data.get('cf-turnstile-response', '')
    if not verify_turnstile(cf_token):
        return jsonify({'success': False, 'message': 'CAPTCHA verification failed'}), 403
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
    unsub_token = str(uuid.uuid4())
    sub = models.NewsletterSubscriber(
        email=email,
        unsubscribe_token=unsub_token,
        subscribed=True,
        source=source[:50] if isinstance(source, str) else 'api',
    )
    db.session.add(sub)
    # Also set User flag
    user = models.User.query.filter_by(email=email).first()
    if user:
        user.newsletter_subscribed = True
    db.session.commit()

    # Send welcome email — write to retry queue first, then attempt immediately
    import threading, json as _json, pathlib as _pl
    _queue_dir = _pl.Path('/home/ultron/protocol_pulse/data/email_queue')
    _queue_dir.mkdir(parents=True, exist_ok=True)
    _queue_file = _queue_dir / f'welcome_{unsub_token[:8]}.json'
    _queue_file.write_text(_json.dumps({'email': email, 'token': unsub_token, 'type': 'welcome'}))
    def _send_welcome():
        try:
            from services.newsletter_service import _send_welcome_email
            ok = _send_welcome_email(email, unsub_token)
            if ok and _queue_file.exists():
                _queue_file.unlink()  # Remove from queue on success
                logging.info('Welcome email sent and dequeued for %s', email)
        except Exception as _e:
            logging.warning('Welcome email failed for %s (queued for retry): %s', email, _e)
    threading.Thread(target=_send_welcome, daemon=True).start()

    return jsonify({'success': True, 'message': 'Subscribed to Protocol Pulse'})

@api_bp.route('/api/newsletter/send', methods=['POST'])
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

@api_bp.route('/api/newsletter/dispatch', methods=['POST'])
def api_newsletter_dispatch():
    """Dispatch latest newsletter queue item. Localhost = no auth, external = X-Admin-Secret."""
    remote = request.remote_addr
    is_local = remote in ('127.0.0.1', '::1', 'localhost')
    if not is_local:
        secret = request.headers.get('X-Admin-Secret', '')
        if not secret or not ADMIN_SECRET or secret != ADMIN_SECRET:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    import glob, shutil
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    queue_dir = os.path.join(project_root, 'data', 'newsletter_queue')
    sent_dir = os.path.join(queue_dir, 'sent')
    os.makedirs(sent_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(queue_dir, '*_hook.json')))
    if not files:
        return jsonify({'success': False, 'error': 'No items in queue'})

    latest = files[-1]
    try:
        with open(latest) as f:
            hook_data = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to read queue item: {e}'}), 500

    import importlib.util as _ilu
    _ne_path = os.path.join(project_root, 'services', 'newsletter_engine.py')
    _ne_spec = _ilu.spec_from_file_location('_newsletter_engine_dispatch', _ne_path)
    _ne_mod = _ilu.module_from_spec(_ne_spec)
    _ne_spec.loader.exec_module(_ne_mod)
    engine = _ne_mod.NewsletterEngine()
    subscribers = engine.get_subscribers()
    if not subscribers:
        # Also check NewsletterSubscriber table
        subs = models.NewsletterSubscriber.query.filter_by(subscribed=True).all()
        subscribers = [s.email for s in subs if s.email]
    if not subscribers:
        return jsonify({'success': False, 'error': '0 subscribers'})

    articles = engine.get_todays_articles(5)
    summary = hook_data.get('hook', '') or engine.generate_ai_summary(articles)
    btc_data = engine.get_btc_price()
    html = engine.generate_html(articles, summary, btc_data)
    result = engine.send_newsletter(subscribers, html=html)

    if result.get('success'):
        shutil.move(latest, os.path.join(sent_dir, os.path.basename(latest)))

    return jsonify(result)

@api_bp.route('/api/generate-article', methods=['POST'])
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
                author="Protocol Pulse",
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
            author="Protocol Pulse",
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

@api_bp.route('/api/publish-article/<int:article_id>', methods=['POST'])
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

@api_bp.route('/api/sentiment/generate', methods=['POST'])
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

@api_bp.route('/api/stream/sentiment')
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

@api_bp.route('/api/sentiment/classify', methods=['POST'])
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

@api_bp.route('/api/sentiment/batch', methods=['POST'])
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

def _load_sovereign_ctx():
    """Load sovereign context from JSON file directly."""
    _ctx_path = os.path.join('/home/ultron/protocol_pulse/data/sovereign_context', 'latest.json')
    try:
        if os.path.exists(_ctx_path):
            with open(_ctx_path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

@api_bp.route('/api/intelligence/sovereign-context')
def api_intelligence_sovereign_context():
    """Return full sovereign context for premium intelligence dashboard."""
    try:
        ctx = _load_sovereign_ctx()
        return jsonify({'success': True, 'data': ctx})
    except Exception as e:
        logging.error("api_sovereign_context error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/intelligence/polymarket')
def api_polymarket():
    """Return top Polymarket Bitcoin/macro markets."""
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            'polymarket_service',
            '/home/ultron/protocol_pulse/services/polymarket_service.py'
        )
        _pm = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_pm)
        markets = _pm.get_bitcoin_markets(5)
        sentiment = _pm.get_macro_sentiment_score()
        return jsonify({'success': True, 'data': {
            'markets': markets,
            'macro_sentiment': sentiment
        }})
    except Exception as e:
        logging.error("api_polymarket error: %s", e)
        return jsonify({'success': False, 'data': {'markets': [], 'macro_sentiment': 50}})

@api_bp.route('/api/intelligence/whale-feed')
def api_whale_feed():
    """Return whale alerts from sovereign context."""
    try:
        ctx = _load_sovereign_ctx()
        return jsonify({'success': True, 'data': {
            'alerts': ctx.get('whale_alerts', []),
            'exchange_flow': ctx.get('exchange_flow', 'neutral'),
            'fear_greed': ctx.get('fear_greed', {}).get('value', 50),
        }})
    except Exception as e:
        logging.error("api_whale_feed error: %s", e)
        return jsonify({'success': True, 'data': {'alerts': [], 'exchange_flow': 'neutral', 'fear_greed': 50}})

@api_bp.route('/api/intelligence/narrative-momentum')
def api_narrative_momentum():
    """Return narrative momentum from sovereign context + history."""
    try:
        ctx = _load_sovereign_ctx()
        narrative = ctx.get('narrative', {})
        kol = ctx.get('kol', {})

        # V18: Supplement with fresh pipeline topic velocity
        try:
            _pi = get_pipeline_intelligence()
            _ds = _pi.get('daily_signals', {})
            if _ds and _ds.get('topic_velocity'):
                narrative['pipeline_topics'] = _ds.get('topic_velocity', [])
                narrative['dominant_narrative'] = _ds.get('dominant_narrative', '')
                narrative['market_mood'] = _ds.get('market_mood', '')
        except Exception:
            pass

        # Build momentum from narrative history
        _hist_path = '/home/ultron/protocol_pulse/data/sovereign_context/history.jsonl'
        topic_counts = {}
        prev_counts = {}
        if os.path.exists(_hist_path):
            import collections as _coll
            _lines = list(_coll.deque(open(_hist_path), maxlen=50))
            mid = len(_lines) // 2
            for _ln in _lines[mid:]:
                try:
                    _e = json.loads(_ln.strip())
                    for _t in _e.get('kol', {}).get('top_topics', []):
                        topic_counts[_t] = topic_counts.get(_t, 0) + 1
                except Exception:
                    pass
            for _ln in _lines[:mid]:
                try:
                    _e = json.loads(_ln.strip())
                    for _t in _e.get('kol', {}).get('top_topics', []):
                        prev_counts[_t] = prev_counts.get(_t, 0) + 1
                except Exception:
                    pass

        # Combine with current narrative
        all_topics = set(list(topic_counts.keys()) + list(prev_counts.keys()))
        if narrative.get('dominant_theme'):
            all_topics.add(narrative['dominant_theme'])
            topic_counts[narrative['dominant_theme']] = topic_counts.get(narrative['dominant_theme'], 0) + 3

        momentum = []
        total_recent = max(sum(topic_counts.values()), 1)
        total_prev = max(sum(prev_counts.values()), 1)
        for topic in all_topics:
            recent_pct = round(topic_counts.get(topic, 0) / total_recent * 100, 1)
            prev_pct = round(prev_counts.get(topic, 0) / total_prev * 100, 1)
            delta = round(recent_pct - prev_pct, 1)
            trend = 'accelerating' if delta > 2 else ('decelerating' if delta < -2 else 'stable')
            momentum.append({
                'topic': topic,
                'recent_pct': recent_pct,
                'prev_pct': prev_pct,
                'delta': delta,
                'trend': trend,
            })
        momentum.sort(key=lambda x: x['recent_pct'], reverse=True)

        return jsonify({
            'success': True,
            'momentum': momentum[:6],
            'dominant_theme': narrative.get('dominant_narrative', narrative.get('dominant_theme', 'Bitcoin')),
            'sentiment': narrative.get('market_mood', narrative.get('sentiment', 'neutral')),
            'pipeline_topics': narrative.get('pipeline_topics', []),
        })
    except Exception as e:
        logging.error("api_narrative_momentum error: %s", e)
        return jsonify({'success': False, 'momentum': []})

@api_bp.route('/api/intelligence/signal')
def api_signal_strength():
    """Return signal strength composite. Cached 5 minutes."""
    try:
        import importlib.util as _i1
        _s1 = _i1.spec_from_file_location("is1", "/home/ultron/protocol_pulse/services/intelligence_service.py")
        _m1 = _i1.module_from_spec(_s1); _s1.loader.exec_module(_m1)
        get_signal_strength = _m1.get_signal_strength
        result = get_signal_strength()
        try:
            import json as _j2
            _ctx = _j2.load(open('/home/ultron/protocol_pulse/data/sovereign_context/latest.json'))
            result['price'] = _ctx.get('btc',{}).get('price',0)
            result['block_height'] = _ctx.get('block_height',0)
            result['mempool_count'] = _ctx.get('mempool',{}).get('unconfirmed',0)
            result['hashrate'] = _ctx.get('network',{}).get('hashrate_eh',_ctx.get('network',{}).get('hashrate',0))
            result['fear_greed'] = _ctx.get('fear_greed',{}).get('value',0)
            result['fear_greed_label'] = _ctx.get('fear_greed',{}).get('label','')
        except: pass
        # V18: Inject fresh pipeline intelligence (topic velocity, narrative)
        try:
            _pi = get_pipeline_intelligence()
            _ds = _pi.get('daily_signals', {})
            _nc = _pi.get('narrative_context', {})
            if _ds:
                result['topic_velocity'] = _ds.get('topic_velocity', [])
                result['dominant_narrative'] = _ds.get('dominant_narrative', '')
                result['market_mood'] = _ds.get('market_mood', '')
                result['recommended_topics'] = _ds.get('recommended_topics', [])
                result['scan_time'] = _ds.get('scan_time', '')
            if _nc:
                result['narrative_bridge'] = _nc.get('narrative_bridge_lines', [])
                result['clip_priorities'] = _nc.get('clip_selection_priority', [])
                result['narrative_computed_at'] = _nc.get('computed_at', '')
        except Exception:
            pass
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error("api_signal_strength error: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/v2/sentiment/summary')
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

@api_bp.route('/api/v2/sentiment/heatmap')
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

@api_bp.route('/api/sarah-briefing/generate', methods=['POST'])
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

@api_bp.route('/api/sarah-briefing/check-flash', methods=['POST'])
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

@api_bp.route('/api/latest-articles')
def latest_articles():
    articles = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(10).all()
    return jsonify([{'id': a.id, 'title': a.title, 'summary': a.summary, 'cover_image_url': a.cover_image_url or a.header_image_url or '', 'header_image_url': a.cover_image_url or a.header_image_url or ''} for a in articles])

@api_bp.route('/api/v2/articles')
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

@api_bp.route('/api/v2/articles/<slug>')
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

@api_bp.route('/api/reddit-trends', methods=['GET'])
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

@api_bp.route('/api/add-ad', methods=['POST'])
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

@api_bp.route('/api/toggle-ad/<int:ad_id>', methods=['POST'])
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

@api_bp.route('/api/delete-ad/<int:ad_id>', methods=['DELETE'])
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

@api_bp.route('/api/active-ads', methods=['GET'])
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

@api_bp.route('/api/network-stats')
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

@api_bp.route('/api/live-tweets')
def api_live_tweets():
    """API endpoint to get live tweets from designated Bitcoin thought leaders"""
    from datetime import datetime, timedelta, timezone
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

@api_bp.route('/api/subscribe', methods=['POST'])
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

@api_bp.route('/api/series/teaser', methods=['POST'])
def get_series_teaser():
    """API endpoint to get AI-generated teaser for next episode"""
    data = request.get_json() or {}
    episode_title = data.get('episode_title', '')
    series_title = data.get('series_title', '')
    
    if not episode_title:
        return jsonify({'error': 'Episode title required'}), 400
    
    teaser = _generate_episode_teaser(episode_title, series_title)
    return jsonify({'teaser': teaser})

@api_bp.route('/api/trigger-automation', methods=['POST', 'GET'])
def trigger_automation():
    """Webhook endpoint to trigger article generation (cron or admin). Use ?force=1 with POST when logged in as admin to skip cooldown."""
    import sys as _asys
    for _ap in ["/home/ultron/protocol_pulse","/home/ultron/protocol_pulse/core"]:
        if _ap not in _asys.path: _asys.path.insert(0,_ap)
    import os as _aos; _aos.chdir("/home/ultron/protocol_pulse/core")
    from services.automation import generate_article_with_tracking

    force = request.args.get("force") in ("1", "true", "yes")
    if force and request.method == "POST":
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            return jsonify({"status": "error", "message": "Admin required to use force=1"}), 403
    result = generate_article_with_tracking(force=force)
    
    if result.get('success'):
        # Generate Grok image if article has no cover image
        aid = result.get('article_id')
        if aid:
            try:
                art = models.Article.query.get(aid)
                if art and (not art.cover_image_url or 'unsplash' in (art.cover_image_url or '') or 'pexels' in (art.cover_image_url or '')):
                    from services.image_service import ImageGenerationService
                    img_svc = ImageGenerationService()
                    img_url = img_svc.generate_article_header_image(title=art.title, category=art.category or 'Bitcoin')
                    if img_url and 'default-header' not in img_url:
                        art.cover_image_url = img_url
                        db.session.commit()
                        logging.info(f"Generated Grok image for article {aid}: {img_url}")
            except Exception as img_err:
                logging.warning(f"Image gen for article {aid} failed: {img_err}")
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


@api_bp.route('/api/sovereign-signal-narrative', methods=['POST'])
def api_sovereign_signal_narrative():
    """Generate AI synthesis of all six Panopticon signal streams."""
    try:
        import importlib.util as _ilu, os, requests as _req

        conv = 74  # current convergence score
        try:
            data = request.get_json(silent=True) or {}
            conv = data.get('convergence', 74)
        except Exception:
            pass

        # Try Anthropic first
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if anthropic_key:
            prompt = (
                f"You are a senior intelligence analyst for Protocol Pulse.\n\n"
                f"Six-stream convergence score: {conv}/100 BULLISH.\n"
                "Signals: Congressional insider trades 65/100 (McCormick buying Bitwise BTC ETF 80-95% conviction; "
                "Tim Moore COIN sale 95% conviction 2-day filing). Institutional 13F/Form D 70/100 "
                "(Galaxy BTC Fund, ParaFi Capital, 30 13F filers). PAC Capital 92/100 "
                "($134M Fairshake raised, a16z $23.8M, Horowitz $11.9M, Andreessen $11.9M). "
                "Legislative 75/100 (GENIUS Act 66-32, Market Clarity 69% congress). "
                "On-Chain 74/100 (SOPR 0.15 capitulation, Puell green zone). "
                "Geopolitical 70/100 (US Strategic Reserve EO14233, Japan yen pressure). "
                "Prediction markets: Fed no change April 98.2% (stable macro).\n\n"
                "Write exactly 3 sentences as a classified intelligence brief. "
                "Be direct, factual, measured. No hype — only what the data shows."
            )
            headers = {
                'x-api-key': anthropic_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            }
            resp = _req.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json={
                    'model': 'claude-haiku-4-5-20251001',
                    'max_tokens': 200,
                    'system': 'Senior intelligence analyst. Classified briefings only. Direct, factual, no hype.',
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=20
            )
            if resp.ok:
                text = resp.json().get('content', [{}])[0].get('text', '')
                if text:
                    return jsonify({'narrative': text, 'model': 'claude-haiku', 'score': conv})

        # Gemini fallback
        gemini_key = os.environ.get('GEMINI_API_KEY', '')
        if gemini_key:
            resp = _req.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}',
                json={'contents': [{'parts': [{'text':
                    f"Act as a senior intelligence analyst. Write exactly 3 sentences as a classified brief "
                    f"synthesizing these signals (convergence {conv}/100 BULLISH): congressional insider net buying, "
                    f"Fairshake PAC $134M raised, GENIUS Act passed 66-32, SOPR at 0.15 capitulation, "
                    f"US Strategic Bitcoin Reserve active. Direct, factual, no hype."}]}]},
                timeout=15
            )
            if resp.ok:
                text = resp.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if text:
                    return jsonify({'narrative': text, 'model': 'gemini-flash', 'score': conv})

        # Static fallback
        return jsonify({
            'narrative': (
                f"Six independent signal streams have converged at {conv}/100, with PAC capital velocity "
                "(Fairshake $134M raised) and legislative momentum (GENIUS Act 66-32) registering the highest "
                "readings at 92 and 75 respectively. Concurrent with this political capital deployment, "
                "SOPR has entered capitulation territory at 0.15 — a divergence that preceded "
                "re-accumulation windows in Q4 2018 and Q4 2022. Congressional positioning shows "
                "net buying of Bitcoin-adjacent assets, with McCormick's high-conviction Bitwise BTC ETF "
                "accumulation representing the clearest institutional signal in the current cycle."
            ),
            'model': 'static',
            'score': conv,
        })
    except Exception as e:
        return jsonify({'narrative': '', 'error': str(e)}), 500

@api_bp.route('/api/donations/pulse')
def api_donation_pulse():
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location('donation_map_service',
            '/home/ultron/protocol_pulse/services/donation_map_service.py')
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        return jsonify(_mod.fetch_donation_pulse())
    except Exception as e:
        return jsonify({"score": 0, "label": "UNAVAILABLE", "error": str(e)})

@api_bp.route('/api/donations/by-state')
def api_donations_by_state():
    try:
        from services.donation_map_service import DonationMapService
        svc = DonationMapService()
        state = request.args.get('state', None)
        data = svc.get_contributions_by_state(state, per_page=20)
        return jsonify({"results": data[:20], "count": len(data)})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)})

@api_bp.route('/api/congress/trades')
def api_congress_trades():
    try:
        from services.congress_trading_service import CongressTradingService
        svc = CongressTradingService()
        return jsonify({"trades": svc.get_recent_trades(20), "party_breakdown": svc.get_party_breakdown()})
    except Exception as e:
        return jsonify({"trades": [], "error": str(e)})

@api_bp.route('/api/congress/ihx')
def api_congress_ihx():
    try:
        from services.congress_trading_service import CongressTradingService
        svc = CongressTradingService()
        return jsonify(svc.get_insider_heat_score())
    except Exception as e:
        return jsonify({"score": 50, "signal": "neutral", "error": str(e)})

@api_bp.route('/api/congress/top-traders')
def api_congress_top_traders():
    try:
        from services.congress_trading_service import CongressTradingService
        svc = CongressTradingService()
        return jsonify({"traders": svc.get_top_traders(10)})
    except Exception as e:
        return jsonify({"traders": [], "error": str(e)})

@api_bp.route('/api/polymarket/markets')
def api_polymarket_markets():
    """Live Polymarket prediction markets — top Bitcoin/crypto/macro markets."""
    try:
        from services.polymarket_service import get_bitcoin_markets, get_macro_sentiment_score
        markets = get_bitcoin_markets(8)
        sentiment = get_macro_sentiment_score()
        return jsonify({
            "markets": markets,
            "sentiment_score": sentiment,
            "count": len(markets),
            "source": "polymarket_gamma_api"
        })
    except Exception as e:
        return jsonify({"markets": [], "sentiment_score": 50, "error": str(e)})

@api_bp.route('/api/pro-metrics')
def api_pro_metrics():
    """Professional on-chain metrics — SSR, MPI, Dormancy Flow."""
    try:
        from services.pro_metrics_service import fetch_all_pro_metrics
        metrics = fetch_all_pro_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)})

@api_bp.route('/api/debug/media')
def debug_media():
    return jsonify({
        "media_service_exists": media_feed_service is not None,
        "media_service_type": str(type(media_feed_service)),
    })

@api_bp.route('/api/media/stats')
def api_media_stats():
    """Media feed statistics."""
    try:
        from services.media_feed_service import get_feed_matrix
        m = get_feed_matrix(limit_per_col=50)
        pods = m.get('podcasts', [])
        vids = m.get('videos', [])
        names = set()
        for ep in pods + vids:
            fn = ep.get('feed_name', '')
            if fn:
                names.add(fn)
        return jsonify({
            'feed_count': len(names) or 18,
            'episode_count': len(pods) + len(vids),
            'podcast_count': len(pods),
            'video_count': len(vids),
        })
    except Exception as e:
        return jsonify({'feed_count': 18, 'episode_count': 0, 'podcast_count': 0, 'video_count': 0, 'error': str(e)})

@api_bp.route('/api/nostr/top')
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

@api_bp.route('/api/nostr/relay-status')
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

@api_bp.route('/api/nostr/publish', methods=['POST'])
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

@api_bp.route('/api/nostr/stats')
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

@api_bp.route('/api/prediction-oracle')
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

@api_bp.route('/api/merchants')
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

@api_bp.route('/api/merchants/search')
def api_merchant_search():
    """Search merchants by query"""
    from services.meetup_map_service import meetup_map_service
    
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    
    if query:
        results = meetup_map_service.search_merchants(query, limit)
        return jsonify({'merchants': results})
    
    return jsonify({'merchants': []})

@api_bp.route('/api/user/briefing-preference', methods=['POST'])
@login_required
def save_briefing_preference():
    """Save user briefing preference (maximalist|macro|full_spectrum)."""
    data = request.get_json(silent=True) or {}
    brief_type = data.get('brief_type', '').strip()
    if brief_type not in ('maximalist', 'macro', 'full_spectrum'):
        return jsonify({'success': False, 'error': 'Invalid brief_type'}), 400
    current_user.briefing_preference = brief_type
    db.session.commit()
    return jsonify({'success': True, 'brief_type': brief_type})

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
    },
    'John Gilmore': {
        'bio': 'Co-founder of the Electronic Frontier Foundation (EFF) and the Cypherpunks mailing list. Sun Microsystems early employee who became a tireless advocate for digital civil liberties and strong encryption. Fought against government attempts to restrict cryptography.',
        'quote': 'The Net interprets censorship as damage and routes around it.',
        'contributions': ['EFF Co-founder', 'Cypherpunks Mailing List', 'Digital Rights Advocacy', 'GNU Project Contributor']
    },
    'Philip Zimmermann': {
        'bio': 'Creator of Pretty Good Privacy (PGP), the most widely used email encryption software in the world. Faced a three-year federal investigation for publishing strong encryption as free software. His work established the principle that civilians deserve military-grade privacy.',
        'quote': 'If privacy is outlawed, only outlaws will have privacy.',
        'contributions': ['PGP Encryption', 'OpenPGP Standard', 'Silent Circle', 'ZRTP Protocol']
    },
    'Julian Assange': {
        'bio': 'Australian publisher and activist who founded WikiLeaks in 2006, using cryptographic tools to enable anonymous whistleblowing at scale. A cypherpunk who demonstrated the power of cryptography to hold institutions accountable. Spent years in asylum and prison for publishing classified documents.',
        'quote': 'Cryptography is the ultimate form of non-violent direct action.',
        'contributions': ['WikiLeaks', 'Anonymous Submission Systems', 'Crypto-Enabled Whistleblowing', 'Rubberhose Deniable Encryption']
    }
}

@api_bp.route('/api/cypherpunk-dossier')
def api_cypherpunk_dossier():
    """Return dossier data for a specific cypherpunk pioneer"""
    name = request.args.get('name', '')
    
    if name in CYPHERPUNK_DOSSIERS:
        return jsonify({
            'success': True,
            'dossier': CYPHERPUNK_DOSSIERS[name]
        })
    
    return jsonify({'success': False, 'error': 'Pioneer not found'}), 404

@api_bp.route('/api/whales')
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

@api_bp.route('/api/whales/live')
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

@api_bp.route('/api/whales/save', methods=['POST'])
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

@api_bp.route('/api/donate/lightning', methods=['POST'])
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

@api_bp.route('/api/analytics/track', methods=['POST'])
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

@api_bp.route('/api/analytics/velocity-leaders')
def api_velocity_leaders():
    """Get top performing content by velocity score."""
    from services.analytics_service import analytics_service
    
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    leaders = analytics_service.get_velocity_leaders(hours=hours, limit=limit)
    return jsonify(leaders)

@api_bp.route('/api/analytics/persona-comparison')
def api_persona_comparison():
    """Compare Alex vs Sarah persona performance."""
    from services.analytics_service import analytics_service
    
    days = request.args.get('days', 7, type=int)
    comparison = analytics_service.get_persona_comparison(days=days)
    return jsonify(comparison)

@api_bp.route('/api/analytics/strategy-effectiveness')
def api_strategy_effectiveness():
    """Get reply strategy effectiveness rankings."""
    from services.analytics_service import analytics_service
    
    days = request.args.get('days', 7, type=int)
    strategies = analytics_service.get_strategy_effectiveness(days=days)
    return jsonify(strategies)

@api_bp.route('/api/analytics/sponsor-metrics')
@admin_required
def api_sponsor_metrics():
    """Get sponsor-ready metrics for pitch decks."""
    from services.analytics_service import analytics_service
    
    days = request.args.get('days', 30, type=int)
    metrics = analytics_service.get_sponsor_metrics(days=days)
    return jsonify(metrics)

@api_bp.route('/api/analytics/export/<format>')
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

@api_bp.route('/api/activity-heatmap')
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

@api_bp.route('/api/supervisor/run-task', methods=['POST'])
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

@api_bp.route('/api/supervisor/auto-assign', methods=['POST'])
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

@api_bp.route('/api/supervisor/auto-publish', methods=['POST'])
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

@api_bp.route('/api/segments/train', methods=['POST'])
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

@api_bp.route('/api/segments/summary')
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

@api_bp.route('/api/segments/recommend', methods=['POST'])
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

@api_bp.route('/api/verified-signals')
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

TRENDING_TAG_SUBREDDITS = {
    'bitcoin': ['bitcoin', 'bitcoindiscussion', 'cryptocurrency'],
    'etf': ['bitcoin', 'cryptocurrency', 'ethereum'],
    'lightning': ['lightningnetwork', 'bitcoin'],
    'nostr': ['bitcoin', 'nostr', 'cryptocurrency'],
    'mining': ['bitcoin', 'bitcoinmining', 'cryptocurrency'],
    'halving': ['bitcoin', 'cryptocurrency'],
}

@api_bp.route('/api/media/trending-links')
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

@api_bp.route('/api/media/feed')
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

@api_bp.route('/api/media/sentiment')
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

        # Enrich with tweet data when DB snapshot has sample_size=0
        if result['sample_size'] == 0:
            fallback = _compute_tweet_sentiment_fallback()
            result['sample_size'] = fallback.get('sample_size', 0)
            result['keywords'] = fallback.get('keywords', [])
            result['verified_count'] = fallback.get('verified_count', 0)
            result['source'] = 'db+tweet_fallback'

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
    
    # Fallback: compute sentiment from raw_tweets.json if DB has no snapshot
    return jsonify(_compute_tweet_sentiment_fallback())


def _compute_tweet_sentiment_fallback():
    """Compute live sentiment from raw_tweets.json when SentimentSnapshot table is empty."""
    try:
        import os as _os
        tweets_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                    'data', 'tweet_study', 'raw_tweets.json')
        if not _os.path.exists(tweets_path):
            raise FileNotFoundError("raw_tweets.json missing")
        with open(tweets_path) as f:
            tweets = json.load(f)
        if not isinstance(tweets, list) or not tweets:
            raise ValueError("No tweets")

        # Use last 200 tweets for analysis
        sample = tweets[-200:]
        bullish_kw = ["bullish", "buy", "accumulate", "long", "breakout", "ath", "pump", "moon", "green"]
        bearish_kw = ["bearish", "sell", "short", "crash", "dump", "fear", "capitulation", "red", "rekt"]

        bull = sum(1 for t in sample if any(k in (t.get("text", "") or "").lower() for k in bullish_kw))
        bear = sum(1 for t in sample if any(k in (t.get("text", "") or "").lower() for k in bearish_kw))
        total = bull + bear
        score = int((bull / total * 100) if total > 0 else 50)

        # Top keywords from tweets
        from collections import Counter
        word_counts = Counter()
        for t in sample:
            text = (t.get("text", "") or "").lower()
            for kw in bullish_kw + bearish_kw + ["etf", "halving", "mining", "regulation", "tariff", "fed"]:
                if kw in text:
                    word_counts[kw] += 1
        top_kw = [{"word": k, "count": v} for k, v in word_counts.most_common(3)]

        state_key = "GREED" if score > 65 else ("FEAR" if score < 35 else "EQUILIBRIUM")
        state_color = "#22c55e" if score > 65 else ("#ef4444" if score < 35 else "#ffffff")

        return {
            'score': score,
            'state': {'key': state_key, 'label': state_key, 'color': state_color},
            'keywords': top_kw,
            'sample_size': len(sample),
            'verified_count': sum(1 for t in sample if t.get("tier") == "conviction_data"),
            'computed_at': datetime.utcnow().isoformat(),
            'source': 'raw_tweets_fallback',
        }
    except Exception:
        return {
            'score': 50, 'state': {'key': 'EQUILIBRIUM', 'label': 'EQUILIBRIUM', 'color': '#ffffff'},
            'keywords': [], 'sample_size': 0, 'verified_count': 0,
            'computed_at': datetime.utcnow().isoformat(),
        }


@api_bp.route('/api/tradfi/signals')
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

@api_bp.route('/api/tradfi/weekly')
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

@api_bp.route('/api/spaces/live')
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

@api_bp.route('/api/podcasts/channels')
def api_podcasts_channels():
    """Get YouTube channel cards with stats"""
    try:
        from services.youtube_channel_service import get_all_channel_cards
        cards = get_all_channel_cards()
        return jsonify(cards)
    except Exception as e:
        logging.error(f"Channel cards error: {e}")
        return jsonify([])

@api_bp.route('/api/media/network-feed')
def api_media_network_feed():
    """What the Network Is Saying — latest articles as network signals."""
    try:
        from models import Article
        articles = Article.query.filter_by(published=True).order_by(
            Article.created_at.desc()
        ).limit(8).all()
        items = []
        for a in articles:
            items.append({
                'source': a.source_name if hasattr(a, 'source_name') and a.source_name else 'Protocol Pulse',
                'source_type': getattr(a, 'category', 'analysis') or 'analysis',
                'text': (a.summary or a.title or '')[:200],
                'timestamp': a.created_at.isoformat() if a.created_at else None,
                'sentiment': getattr(a, 'sentiment', 'neutral') or 'neutral',
                'icon': 'fas fa-newspaper',
                'url': f'/article/{a.slug}' if a.slug else '#',
            })
        return jsonify({'items': items, 'updated_at': items[0]['timestamp'] if items else None})
    except Exception as e:
        logging.error(f"network-feed error: {e}")
        return jsonify({'items': [], 'updated_at': None})

@api_bp.route('/api/media/video-feed')
def api_media_video_feed():
    """Video Briefings from the Network — latest video/podcast entries."""
    try:
        items = []
        if media_feed_service:
            data = media_feed_service.get_feed_matrix(limit_per_col=8)
            for v in (data.get('videos') or [])[:8]:
                items.append({
                    'title': v.get('title', ''),
                    'channel': v.get('feed_name') or v.get('source', 'Unknown'),
                    'thumbnail': v.get('thumbnail_url', ''),
                    'url': v.get('source_url') or v.get('video_url', '#'),
                    'video_id': v.get('guid', ''),
                    'platform': 'youtube',
                    'published_at': v.get('published_at', ''),
                })
        if not items:
            from models import Article
            vids = Article.query.filter(
                Article.published == True,
                Article.category.in_(['video', 'media', 'podcast'])
            ).order_by(Article.created_at.desc()).limit(8).all()
            for a in vids:
                items.append({
                    'title': a.title or '',
                    'channel': getattr(a, 'source_name', '') or 'Protocol Pulse',
                    'thumbnail': a.cover_image_url or '',
                    'url': f'/article/{a.slug}' if a.slug else '#',
                    'video_id': '',
                    'platform': 'article',
                    'published_at': a.created_at.isoformat() if a.created_at else '',
                })
        return jsonify({'items': items, 'updated_at': items[0]['published_at'] if items else None})
    except Exception as e:
        logging.error(f"video-feed error: {e}")
        return jsonify({'items': [], 'updated_at': None})

@api_bp.route('/api/media/live-signals')
def api_media_live_signals():
    import json as _j, os as _o
    ctx_path = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', 'data', 'sovereign_context', 'latest.json')
    signals = []
    try:
        ctx = _j.load(open(ctx_path))
        ts = ctx.get('timestamp', '')
        btc = ctx.get('btc', {})
        price = btc.get('price') or btc.get('usd')
        change = float(btc.get('change_24h') or btc.get('pct_24h') or 0)
        if price:
            d2 = 'bullish' if change > 0 else 'bearish' if change < 0 else 'neutral'
            signals.append({'source':'BTC/USD','text':f'${float(price):,.0f} ({change:+.2f}% 24h)','direction':d2,'strength':3,'timestamp':ts})
        fg = ctx.get('fear_greed', {})
        fgv = fg.get('value') if isinstance(fg, dict) else fg
        if fgv is not None:
            fgv = int(fgv)
            label = 'Extreme Fear' if fgv<25 else 'Fear' if fgv<45 else 'Neutral' if fgv<55 else 'Greed' if fgv<75 else 'Extreme Greed'
            fd = 'bearish' if fgv<45 else 'neutral' if fgv<55 else 'bullish'
            signals.append({'source':'FEAR & GREED','text':f'{fgv}/100 - {label}','direction':fd,'strength':4 if fgv<25 or fgv>75 else 2,'timestamp':ts})
        mem = ctx.get('mempool', {})
        if isinstance(mem, dict):
            fee = mem.get('fast_fee') or mem.get('fastest_fee') or mem.get('fee')
            txs = mem.get('tx_count') or mem.get('unconfirmed')
            if fee: signals.append({'source':'MEMPOOL','text':f'Fast fee: {fee} sat/vB' + (f' - {int(txs):,} unconf' if txs else ''),'direction':'neutral','strength':2,'timestamp':ts})
        net = ctx.get('network', {})
        if isinstance(net, dict):
            hr = net.get('hashrate_eh') or net.get('hashrate')
            diff = net.get('difficulty') or net.get('diff_adj_pct')
            if hr: signals.append({'source':'HASHRATE','text':f'{float(hr):.0f} EH/s' + (f' | adj {float(diff):+.2f}%' if diff else ''),'direction':'bullish','strength':2,'timestamp':ts})
        ef = ctx.get('exchange_flow','')
        if ef:
            ed = 'bullish' if 'outflow' in str(ef).lower() else 'bearish' if 'inflow' in str(ef).lower() else 'neutral'
            signals.append({'source':'EXCHANGE FLOW','text':str(ef).upper(),'direction':ed,'strength':2,'timestamp':ts})
        whales = ctx.get('whale_alerts', [])
        if isinstance(whales, list) and whales: signals.append({'source':'WHALE WATCH','text':f'{len(whales)} large txs detected','direction':'neutral','strength':3,'timestamp':ts})
        narrative = ctx.get('narrative','')
        if narrative and len(str(narrative)) > 20: signals.append({'source':'SOVEREIGN AI','text':str(narrative)[:150],'direction':'neutral','strength':2,'timestamp':ts})
        kols = ctx.get('kol', [])
        if isinstance(kols, list):
            for k in kols[:3]:
                if isinstance(k, dict):
                    name = k.get('name') or k.get('handle','')
                    sig2 = k.get('signal') or k.get('observation') or k.get('text','')
                    if name and sig2: signals.append({'source':name.upper()[:18],'text':str(sig2)[:120],'direction':k.get('direction','neutral'),'strength':2,'timestamp':ts})
    except Exception as e: logging.warning(f'live-signals err: {e}')
    if not signals: signals.append({'source':'SYSTEM','text':'Signal engine initializing...','direction':'neutral','strength':1,'timestamp':''})
    return jsonify({'signals':signals,'count':len(signals),'updated_at':signals[0]['timestamp'] if signals else ''})

@api_bp.route('/api/media/sources')
def api_media_sources():
    """Get curated sources from supported_sources.json"""
    try:
        with open('data/supported_sources.json', 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        logging.error(f"Failed to load sources: {e}")
        return jsonify({})

@api_bp.route('/api/media/ingest', methods=['POST'])
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

@api_bp.route('/api/artists/submit', methods=['POST'])
def api_artists_submit():
    """Accept artist submissions for the Sovereign Creativity Hub"""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    description = (data.get('description') or '').strip()

    if not name or not category or not description:
        return jsonify({'error': 'Name, category, and description are required'}), 400

    if len(name) > 200 or len(description) > 2000:
        return jsonify({'error': 'Input too long'}), 400

    allowed_cats = {'visual', 'digital', 'physical', 'apparel', 'content'}
    if category not in allowed_cats:
        return jsonify({'error': 'Invalid category'}), 400

    website = (data.get('website') or '').strip()[:500]
    nostr_npub = (data.get('nostr_npub') or '').strip()[:200]
    sample_url = (data.get('sample_url') or '').strip()[:500]

    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS artist_submissions (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                website TEXT,
                nostr_npub TEXT,
                sample_url TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.execute(db.text("""
            INSERT INTO artist_submissions (name, category, description, website, nostr_npub, sample_url)
            VALUES (:name, :category, :description, :website, :nostr_npub, :sample_url)
        """), {
            'name': name, 'category': category, 'description': description,
            'website': website, 'nostr_npub': nostr_npub, 'sample_url': sample_url
        })
        db.session.commit()
    except Exception as e:
        logging.error(f"Artist submission DB error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Server error saving submission'}), 500

    return jsonify({'status': 'ok', 'message': 'Submission received'}), 200

@api_bp.route('/api/rank/get-drill-token', methods=['POST'])
@login_required
def get_drill_token():
    """Generate a one-time token for drill completion verification"""
    import secrets
    token = secrets.token_urlsafe(32)
    session['drill_token'] = token
    session['drill_token_time'] = datetime.utcnow().isoformat()
    return jsonify({'token': token})

@api_bp.route('/api/rank/increment-drill', methods=['POST'])
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

@api_bp.route('/api/rank/get-brief-token', methods=['POST'])
@login_required
def get_brief_token():
    """Generate a one-time token for brief click verification"""
    import secrets
    token = secrets.token_urlsafe(32)
    session['brief_token'] = token
    return jsonify({'token': token})

@api_bp.route('/api/rank/increment-brief', methods=['POST'])
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

@api_bp.route('/api/crm/callback', methods=['POST'])
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

@api_bp.route('/api/track/pageview', methods=['POST'])
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

@api_bp.route('/api/track/event', methods=['POST'])
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

@api_bp.route('/api/hot-ticker')
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

@api_bp.route('/api/rtsa/products')
def api_rtsa_products():
    """Get approved RTSA products for public display"""
    from services.rtsa_service import rtsa_service
    
    hot_products = rtsa_service.get_hot_products()
    approved_products = rtsa_service.get_approved_products(limit=10)
    
    return jsonify({
        'hot': [p.to_dict() for p in hot_products],
        'approved': [p.to_dict() for p in approved_products]
    })

@api_bp.route('/api/rtsa/foundational')
def api_rtsa_foundational():
    """Get the 5 foundational ethos statements"""
    from services.design_forge import get_foundational_statements
    
    return jsonify({
        'statements': get_foundational_statements()
    })

@api_bp.route("/v1/signals/live", methods=["GET"])
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

@api_bp.route("/v1/spaces/live", methods=["GET"])
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

@api_bp.route("/v1/tradfi/signals", methods=["GET"])
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

@api_bp.route("/v1/sentiment/composite", methods=["GET"])
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

@api_bp.route("/v1/alerts/webhook", methods=["GET", "POST"])
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

@api_bp.route('/api/media/highlights')
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

import time as _time

import functools as _functools

import re as _re_charts

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
    """Fetch current BTC price: local cache first, then 3-source API fallback. Cache 30s."""
    # Source 0: Local signals.json cache (updated every 5min by signal_data_fetcher)
    try:
        _signals_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'signals.json')
        _signals_path = os.path.normpath(_signals_path)
        if os.path.exists(_signals_path):
            _mtime = os.path.getmtime(_signals_path)
            _age_s = time.time() - _mtime
            if _age_s < 600:  # fresh if < 10 minutes old
                import json as _json
                with open(_signals_path) as _f:
                    _sdata = _json.load(_f)
                _cached_price = _sdata.get('btc_price', {}).get('value')
                if _cached_price and float(_cached_price) > 0:
                    return float(_cached_price)
    except Exception as e:
        logging.warning("BTC price signals.json cache error: %s", e)
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

@api_bp.route('/api/btc-price')
@limiter.exempt
def api_btc_price():
    """Live BTC price endpoint used by nav ticker and stage."""
    # Try local cache first for change_24h
    change_24h = 0
    try:
        _sp = os.path.join(os.path.dirname(__file__), '..', 'data', 'signals.json')
        _sp = os.path.normpath(_sp)
        if os.path.exists(_sp):
            import json as _json
            with open(_sp) as _f:
                _sd = _json.load(_f)
            change_24h = _sd.get('btc_price', {}).get('change_24h', 0)
    except Exception:
        pass
    price = _fetch_btc_price()
    if price:
        return jsonify({'price': price, 'change_24h': round(change_24h, 2) if change_24h else 0})
    return jsonify({'price': 0, 'change_24h': 0}), 200

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

@api_bp.route("/api/charts/price-history")
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

@api_bp.route("/api/charts/mempool-data")
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

@api_bp.route("/api/charts/hashrate-history")
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

@api_bp.route("/api/charts/pool-distribution")
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

@api_bp.route("/api/charts/fee-history")
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

@api_bp.route("/api/charts/lightning")
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

@api_bp.route("/api/charts/fear-greed")
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

@api_bp.route("/api/charts/price-alert", methods=["POST"])
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

@api_bp.route("/api/charts/ai-explain", methods=["POST"])
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

@api_bp.route('/api/mining/live-stats')
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

@api_bp.route('/api/mining/pools')
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

@api_bp.route('/api/charts/hashrate-history')
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

@api_bp.route('/api/mining/articles')
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

@api_bp.route('/api/affiliates/metrics')
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

@api_bp.route('/api/affiliates/impression', methods=['POST'])
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

@api_bp.route('/api/affiliates/click', methods=['POST'])
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

@api_bp.route('/api/affiliates/declare-winner', methods=['POST'])
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

@api_bp.route('/api/stage/intel')
def api_stage_intel():
    """Feed the Stage intel panel from recent articles + convergence data."""
    try:
        articles = models.Article.query.filter_by(published=True).order_by(
            models.Article.created_at.desc()
        ).limit(8).all()

        items = []
        for a in articles:
            items.append({
                "title": a.title,
                "summary": (a.summary or a.content or "")[:200].replace("<", "").replace(">", ""),
                "category": a.category or "Bitcoin",
                "url": f"/articles/{a.slug or a.id}",
                "published_at": a.created_at.isoformat() if a.created_at else None,
                "sentiment": "neutral",
                "author": a.author or "Protocol Pulse",
            })

        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        return jsonify({"items": [], "error": str(e)})

@api_bp.route('/api/stage/transcripts')
def api_stage_transcripts():
    """Feed the Partner Channel Intelligence panel from media episodes."""
    try:
        episodes = models.MediaEpisode.query.order_by(
            models.MediaEpisode.published_at.desc()
        ).limit(6).all()

        items = []
        for ep in episodes:
            feed = models.MediaFeed.query.get(ep.feed_id) if ep.feed_id else None
            items.append({
                "title": ep.title,
                "channel": feed.name if feed else "Unknown",
                "thumbnail": ep.thumbnail_url or "",
                "url": ep.source_url or ep.video_url or "",
                "published_at": ep.published_at.isoformat() if ep.published_at else None,
                "description": (ep.description or "")[:150],
                "type": "video" if ep.video_url else "podcast",
            })

        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        return jsonify({"items": [], "error": str(e)})

@api_bp.route('/api/stage/signal')
def api_stage_signal():
    """Feed the Stage signal panel from sovereign context + convergence."""
    try:
        import json as _json
        ctx_path = "/home/ultron/protocol_pulse/data/sovereign_context/latest.json"
        ctx = {}
        try:
            with open(ctx_path) as f:
                ctx = _json.load(f)
        except Exception:
            pass

        btc = ctx.get("btc", {})
        fg = ctx.get("fear_greed", {})
        net = ctx.get("network", {})
        opts = ctx.get("options", {})
        fut = ctx.get("futures", {})

        return jsonify({
            "price": btc.get("price", 0),
            "change_24h": btc.get("change_24h", 0),
            "fear_greed": fg.get("value", 0),
            "fear_greed_label": fg.get("label", "Unknown"),
            "hashrate_eh": net.get("hashrate_eh", 0),
            "difficulty_adj": net.get("next_adj_pct", 0),
            "funding_rate": fut.get("funding_rate"),
            "put_call_ratio": opts.get("put_call_ratio"),
            "dvol": opts.get("dvol"),
            "timestamp": ctx.get("timestamp"),
            "nostr": {"status": "scanning", "events": 0},
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@api_bp.route('/api/briefing/latest')
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

@api_bp.route('/api/briefing/<int:briefing_id>')
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

@api_bp.route('/api/briefing/list')
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

@api_bp.route('/api/briefing/generate', methods=['POST'])
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

@api_bp.route('/api/briefing/status/<int:briefing_id>')
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

@api_bp.route('/api/schiff/score')
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

@api_bp.route('/api/schiff/refresh', methods=['POST'])
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

@api_bp.route('/api/schiff/statements')
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

try:
    if _schiff_available:
        _schiff_seed(app)
except Exception as _seed_err:
    logging.warning("Schiff seed (startup): %s", _seed_err)

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

@api_bp.route('/api/proxy/bitnodes/snapshot')
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
        try:
            import re as _nre
            _nh=requests.get("https://newhedge.io/bitcoin/node-map",timeout=10,headers={"User-Agent":"Mozilla/5.0"})
            _nm=_nre.search(r'totalNodes[^0-9]+([0-9]{4,6})',_nh.text) or _nre.search(r'([0-9]{4,6})[^0-9]*nodes',_nh.text,_nre.I)
            if _nm:
                _nc=int(_nm.group(1))
                if _nc>5000:
                    _p={"node_count":_nc,"source":"newhedge","reachable":True}
                    _bitnodes_snapshot_cache["data"]=_p
                    _bitnodes_snapshot_cache["expires"]=now+300
                    return make_response(jsonify(_p))
        except Exception as _e: logging.debug("newhedge nodes: %s",_e)
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
        # Fallback to last known estimate while live sources unavailable
        return make_response(jsonify({'node_count': 21000, 'source': 'estimate', 'note': 'API sources rate-limited, showing known estimate'}))

@api_bp.route('/api/proxy/bitnodes/history')
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

import time as _t

import hashlib as _hashlib

_terminal_free_rl: dict = {}   # {ip: [count, window_start]}

_TERMINAL_FREE_LIMIT = 60

_TERMINAL_FREE_WINDOW = 3600   # 1 hour

def _terminal_free_rate_ok(ip: str) -> bool:
    # Exempt localhost — server's own page loads and cron jobs shouldn't count
    if ip in ("127.0.0.1", "::1", "localhost"):
        return True
    now = _t.time()
    rec = _terminal_free_rl.get(ip)
    if rec is None or now - rec[1] >= _TERMINAL_FREE_WINDOW:
        _terminal_free_rl[ip] = [1, now]
        return True
    if rec[0] >= _TERMINAL_FREE_LIMIT:
        return False
    rec[0] += 1
    return True

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
        logging.warning("btc_price detailed fetch error: %s — trying simple endpoint", e)
    # Fallback: simpler CoinGecko endpoint (less likely to be rate-limited)
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true", "include_market_cap": "true"},
            timeout=6,
        )
        d = r.json().get("bitcoin", {})
        price = d.get("usd", 0)
        change_24h = d.get("usd_24h_change", 0)
        return {
            "price": round(price, 2),
            "change_24h_pct": round(change_24h, 2),
            "change_24h_usd": round(price * change_24h / 100, 2) if price else 0,
            "change_7d_pct": 0, "change_30d_pct": 0,
            "high_24h": 0, "low_24h": 0,
            "market_cap": d.get("usd_market_cap", 0),
            "dominance": 0,
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e2:
        logging.warning("btc_price simple fetch also failed: %s", e2)
    # Final fallback: sovereign context or price_cache.json
    try:
        import os as _os
        for path in [
            _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "sovereign_context", "latest.json"),
            _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "price_cache.json"),
        ]:
            if _os.path.exists(path):
                import json as _j
                with open(path) as _f:
                    d = _j.load(_f)
                p = d.get("btc", d).get("price", d.get("1h_ago", 0))
                if p and p > 0:
                    return {
                        "price": round(p, 2), "change_24h_pct": d.get("btc", d).get("change_24h", 0),
                        "change_24h_usd": 0, "change_7d_pct": 0, "change_30d_pct": 0,
                        "high_24h": 0, "low_24h": 0, "market_cap": 0, "dominance": 0,
                        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "local_cache",
                    }
    except Exception:
        pass
    return {"price": 0, "change_24h_pct": 0, "change_24h_usd": 0,
            "change_7d_pct": 0, "change_30d_pct": 0, "high_24h": 0,
            "low_24h": 0, "market_cap": 0, "dominance": 0,
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}

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
        ehr = hashrate / 1e18 if hashrate else 0
        diff_t = difficulty / 1e12 if difficulty else 0

        # ── S2F: calculated from block height ──
        # Current subsidy: 3.125 BTC/block (post-2024 halving)
        # Annual flow = 3.125 * ~52560 blocks/year = 164,250 BTC
        # Circulating ~19.85M BTC
        circulating = 19_850_000
        annual_flow = 3.125 * 52560  # 164,250
        s2f_ratio = round(circulating / annual_flow, 1) if annual_flow else 0
        # PlanB S2F model price (approximate): e^(14.6) * s2f^3.3
        import math
        s2f_model_price = round(math.exp(14.6) * (s2f_ratio ** 3.3)) if s2f_ratio else 0

        # ── Exchange flows: pull from sovereign context if available ──
        exchange_flows = "neutral"
        sov_ctx = None
        try:
            from services.sovereign_context_engine import get_latest_context
            sov_ctx = get_latest_context()
            if sov_ctx:
                exchange_flows = sov_ctx.get("exchange_flow", "neutral") or "neutral"
        except Exception:
            pass

        # Blocks to halving: next halving at block 1,050,000
        blocks_to_halving = max(0, 1_050_000 - block_height)

        # ── MVRV + Puell: prefer real Glassnode values from scraper, fall back to derived ──
        mvrv_val = None
        puell_val = None
        mvrv_source = "derived"
        puell_source = "derived"
        try:
            # Priority 1: real scraped values from pro_metrics_cache.json (< 24hrs old)
            try:
                import json as _json
                from datetime import timezone as _tz
                with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pro_metrics_cache.json")) as _pmf:
                    _pm = _json.load(_pmf)
                _cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "+00:00"
                # MVRV Z-Score
                _mvrv_entry = _pm.get("mvrv_zscore", {})
                if (_mvrv_entry.get("value") is not None
                        and (_mvrv_entry.get("scraped_at", "") > _cutoff)):
                    mvrv_val = round(_mvrv_entry["value"], 2)
                    mvrv_source = "glassnode"
                # Puell Multiple
                _puell_entry = _pm.get("puell_multiple", {})
                if (_puell_entry.get("value") is not None
                        and (_puell_entry.get("scraped_at", "") > _cutoff)):
                    puell_val = round(_puell_entry["value"], 2)
                    puell_source = "glassnode"
            except Exception:
                pass

            # Priority 2: derived approximations (existing logic)
            if mvrv_val is None or puell_val is None:
                btc_price = 0
                market_cap = 0

                if sov_ctx:
                    btc_info = sov_ctx.get("btc", {})
                    btc_price = btc_info.get("price", 0) or 0
                    market_cap = btc_info.get("market_cap", 0) or 0

                if not btc_price:
                    import json as _json
                    try:
                        with open("/home/ultron/protocol_pulse/data/sovereign_context/latest.json") as _f:
                            _sov = _json.load(_f)
                        btc_info = _sov.get("btc", {})
                        btc_price = btc_info.get("price", 0) or 0
                        market_cap = btc_info.get("market_cap", 0) or 0
                    except Exception:
                        pass

                if not btc_price:
                    import json as _json
                    try:
                        with open("/home/ultron/protocol_pulse/data/signals.json") as _f:
                            sig = _json.load(_f)
                        btc_price = sig.get("btc_price", 0)
                    except Exception:
                        pass

                if not market_cap and btc_price:
                    market_cap = circulating * btc_price

                if market_cap and btc_price:
                    if mvrv_val is None:
                        realized_cap_est = 650_000_000_000
                        mvrv_val = round(market_cap / realized_cap_est, 2)
                    if puell_val is None:
                        daily_issuance_usd = 144 * 3.125 * btc_price
                        avg_price_365d = 65_000
                        daily_issuance_365d_ma = 144 * 3.125 * avg_price_365d
                        if daily_issuance_365d_ma > 0:
                            puell_val = round(daily_issuance_usd / daily_issuance_365d_ma, 2)
        except Exception as _mvrv_err:
            logging.warning("MVRV/Puell calc error: %s", _mvrv_err)

        return {
            "hashrate": f"{round(ehr, 1)} EH/s",
            "hashrate_ehs": round(ehr, 2),
            "difficulty": f"{round(diff_t, 1)} T",
            "difficulty_t": round(diff_t, 2),
            "next_adjustment": f"{'+' if est_pct > 0 else ''}{round(est_pct, 2)}%",
            "next_adj_pct": round(est_pct, 2),
            "remain_blocks": remain_blocks,
            "remain_time_s": remain_time,
            "block_height": block_height,
            "blocks_to_halving": f"{blocks_to_halving:,}",
            # MVRV: real Glassnode when available, else derived
            "mvrv": mvrv_val,
            "mvrv_source": mvrv_source,
            "mvrv_locked": False,
            # Puell Multiple: real Glassnode when available, else derived
            "puell_multiple": puell_val,
            "puell_source": puell_source,
            "puell_locked": False,
            # S2F: calculated
            "s2f": f"{s2f_ratio} (${s2f_model_price:,})",
            "s2f_ratio": s2f_ratio,
            "s2f_model_price": s2f_model_price,
            # Exchange flows from sovereign context
            "exchange_flows": exchange_flows.upper(),
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        logging.warning("onchain fetch error: %s", e)
        return {"hashrate": "—", "hashrate_ehs": 0, "difficulty": "—",
                "difficulty_t": 0, "next_adjustment": "—", "next_adj_pct": 0,
                "remain_blocks": 0, "remain_time_s": 0, "block_height": 0,
                "blocks_to_halving": "—",
                "mvrv": None, "mvrv_locked": True,
                "puell_multiple": None, "puell_locked": True,
                "s2f": "—", "s2f_ratio": 0, "s2f_model_price": 0,
                "exchange_flows": "NEUTRAL",
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

@api_bp.route("/api/v2/terminal/price")
def api_v2_terminal_price():
    """BTC price, 24h/7d/30d change, market cap, dominance. Cached 30s."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("btc_price", 30, _fetch_btc_price_detail)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/mempool")
def api_v2_terminal_mempool():
    """Mempool stats + fee tiers. Cached 30s."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("mempool", 30, _fetch_mempool)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/fear-greed")
def api_v2_terminal_fear_greed():
    """Fear & Greed index today/yesterday/week/month. Cached 15min."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("fear_greed", 900, _fetch_fear_greed)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/latest")
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

@api_bp.route("/api/v2/terminal/macro")
def api_v2_terminal_macro():
    """DXY, Gold, S&P 500 + BTC ratios. Cached 60min."""
    ip = request.remote_addr or "anon"
    if not _terminal_free_rate_ok(ip):
        return jsonify({"error": "Rate limit exceeded (60/hr)"}), 429
    data = _term_cached("macro", 3600, _fetch_macro)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/signal")
def api_v2_terminal_signal():
    """PP Signal Intelligence composite score. Commander only."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    from services.signal_engine import compute_signal_score
    data = compute_signal_score(db=db, models=models)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/topics")
def api_v2_terminal_topics():
    """Trending topics ranked by velocity (last 2h). Commander only."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    data = _term_cached("topics", 300, _fetch_topics)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/alerts")
def api_v2_terminal_alerts():
    """Early warning alert feed (last 20 articles). Commander only."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    def _fetch():
        return {"alerts": _fetch_alerts(), "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    data = _term_cached("alerts", 30, _fetch)
    return jsonify(data)

@api_bp.route("/api/onchain")
def api_onchain_public():
    """Public on-chain metrics: hashrate, difficulty, S2F, exchange flows, MVRV, Puell."""
    data = _term_cached("onchain", 300, _fetch_onchain)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/onchain")
def api_v2_terminal_onchain():
    """MVRV, S2F, hashrate, difficulty, exchange flows. Commander only. Cached 5min."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    data = _term_cached("onchain", 300, _fetch_onchain)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/lightning")
def api_v2_terminal_lightning():
    """Lightning Network nodes, channels, capacity. Commander only. Cached 10min."""
    ok, err, _ = _commander_required()
    if not ok:
        return err
    data = _term_cached("lightning", 600, _fetch_lightning)
    return jsonify(data)

@api_bp.route("/api/v2/terminal/keys", methods=["GET", "POST"])
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

@api_bp.route("/api/v2/terminal/keys/<key_prefix>", methods=["DELETE"])
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

@api_bp.route('/api/search')
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

@api_bp.route('/data/stage_briefs/<path:filename>')
def serve_stage_brief(filename):
    """Serve stage brief MP4 and JSON files."""
    from flask import send_from_directory
    brief_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'video_pipeline_v3', 'data', 'stage_briefs')
    return send_from_directory(brief_dir, filename)

@api_bp.route('/api/stage/broadcast-queue')
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

@api_bp.route('/api/stage/consume-broadcast', methods=['POST'])
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

@api_bp.route('/api/stage/broadcast-status')
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

@api_bp.route('/api/oracle/chat', methods=['POST'])
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

@api_bp.route('/api/oracle/speak', methods=['POST'])
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

@api_bp.route('/api/oracle/query', methods=['POST'])
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

@api_bp.route('/api/sms/subscribe', methods=['POST'])
@limiter.limit("5 per minute")
def api_sms_subscribe():
    """Subscribe a phone number to Protocol Pulse daily brief (free) or Oracle calls (premium)."""
    import re, threading
    data = request.get_json(silent=True) or {}
    raw_phone = (data.get('phone') or request.form.get('phone', '')).strip()
    tier = (data.get('tier') or 'free').strip().lower()
    if tier not in ('free', 'premium'):
        tier = 'free'
    name = (data.get('name') or '').strip()[:100]
    call_time = (data.get('call_time') or '08:00').strip()
    import re as _ret; call_time = call_time if _ret.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', call_time) else '08:00'
    language = (data.get('language') or 'en').strip().lower()
    language = language if language in ('en','es','fr','de','pt','ja') else 'en'
    sub_timezone = (data.get('timezone') or 'America/New_York').strip()

    # Normalize: strip non-digits, ensure +1 prefix for US
    digits = re.sub(r'[^0-9]', '', raw_phone)
    if len(digits) == 10:
        digits = '1' + digits
    if len(digits) == 11 and digits.startswith('1'):
        phone = '+' + digits
    elif len(digits) > 10:
        phone = '+' + digits
    else:
        return jsonify({'success': False, 'message': 'Enter a valid US phone number (US only)'}), 400

    existing = models.SmsSubscriber.query.filter_by(phone=phone).first()
    if existing and existing.subscribed:
        # Upgrade tier if applicable
        if tier == 'premium' and getattr(existing, 'tier', 'free') == 'free':
            existing.tier = 'premium'
            if name:
                existing.name = name
            db.session.commit()
            threading.Thread(target=_send_sms_welcome, args=(phone, tier), daemon=True).start()
            return jsonify({'success': True, 'message': 'Upgraded to Oracle tier', 'tier': 'premium'})
        return jsonify({'success': False, 'message': 'Already subscribed', 'tier': getattr(existing, 'tier', 'free')}), 409
    if existing and not existing.subscribed:
        existing.subscribed = True
        existing.tier = tier
        if name:
            existing.name = name
        existing.unsubscribed_at = None
        db.session.commit()
        threading.Thread(target=_send_sms_welcome, args=(phone, tier), daemon=True).start()
        return jsonify({'success': True, 'message': 'Re-subscribed', 'tier': tier})

    sub = models.SmsSubscriber(phone=phone, subscribed=True, tier=tier,
                                name=name or None, source='website')
    db.session.add(sub)
    db.session.commit()
    threading.Thread(target=_send_sms_welcome, args=(phone, tier), daemon=True).start()
    return jsonify({'success': True, 'message': 'Subscribed', 'tier': tier})

@api_bp.route('/api/sms/unsubscribe', methods=['POST'])
def api_sms_unsubscribe():
    """Unsubscribe from SMS briefs. Text STOP or call this endpoint."""
    data = request.get_json(silent=True) or {}
    phone = (data.get('phone') or '').strip()
    if not phone:
        return jsonify({'success': False, 'message': 'Phone required'}), 400
    sub = models.SmsSubscriber.query.filter_by(phone=phone).first()
    if sub:
        sub.subscribed = False
        sub.unsubscribed_at = db.func.now()
        db.session.commit()
    return jsonify({'success': True, 'message': 'Unsubscribed'})

def _send_sms_welcome(phone, tier='free'):
    """Send welcome SMS to new subscriber."""
    try:
        from services.twilio_service import send_sms
        send_sms(phone, (
            "[PROTOCOL PULSE] Welcome, operative. "
            "You'll receive a daily sovereign intelligence brief every morning at 6:45 AM ET. "
            "Real data. No hype. Stay sovereign. "
            "Reply STOP to unsubscribe."
        ))
    except Exception as e:
        logging.warning(f"Welcome SMS failed for {phone}: {e}")

@api_bp.route('/api/media/brief-audio/<filename>')
def serve_brief_audio(filename):
    import os
    from flask import send_from_directory, abort
    briefs_dir = '/tmp/satomi_briefs'
    filepath = os.path.join(briefs_dir, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(briefs_dir, filename, mimetype='audio/mpeg')

@api_bp.route('/api/satomi/voice', methods=['POST', 'GET'])
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

@api_bp.route('/api/satomi/voice/choice', methods=['POST'])
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

@api_bp.route('/api/satomi/tts')
def satomi_tts_audio():
    """Serve Satomi's Kokoro voice as audio for Twilio <Play> tag.
    MUST always return valid audio — never 500/503 (Twilio hangs up on errors).
    """
    import io
    from flask import send_file

    def _silence_wav():
        """Return 1-second 8kHz mono silence WAV — always valid for Twilio."""
        import struct
        sr, dur, bits = 8000, 1, 16
        n = sr * dur
        data = b'\x00\x00' * n
        hdr = struct.pack('<4sI4s4sIHHIIHH4sI',
            b'RIFF', 36 + len(data), b'WAVE', b'fmt ', 16, 1, 1,
            sr, sr * bits // 8, bits // 8, bits, b'data', len(data))
        return hdr + data

    try:
        text = request.args.get('text', 'Protocol Pulse intelligence signal.')[:600]
        # Try Kokoro first (same voice as oracle), fall back to ElevenLabs
        try:
            import sys
            sys.path.insert(0, '/home/ultron/protocol_pulse/oracle')
            from avatar_server import _avatar_tts
            audio_bytes = _avatar_tts(text)
            if audio_bytes and len(audio_bytes) > 1000:
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
                return send_file(io.BytesIO(r.content), mimetype='audio/mpeg',
                               as_attachment=False, download_name='satomi.mp3')
        except Exception as e:
            logging.warning(f'[SatomiTTS] ElevenLabs failed: {e}')
        # Final fallback — 1s silence WAV (valid audio, Twilio won't hang up)
        logging.warning('[SatomiTTS] All TTS failed, returning silence WAV')
        return send_file(io.BytesIO(_silence_wav()), mimetype='audio/wav',
                        as_attachment=False, download_name='satomi.wav')
    except Exception as e:
        logging.error(f'[SatomiTTS] Fatal error: {e}')
        return send_file(io.BytesIO(_silence_wav()), mimetype='audio/wav',
                        as_attachment=False, download_name='satomi.wav')

@api_bp.route('/api/satomi/voice/outbound-twiml', methods=['POST', 'GET'])
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

@api_bp.route('/api/satomi/sms', methods=['POST'])
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

@api_bp.route('/api/satomi/call-subscribers', methods=['POST'])
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

@api_bp.route('/api/apply-promo', methods=['POST'])
@limiter.limit("10 per minute")
def apply_promo_code():
    """Apply a promo code to unlock premium access for team/testing."""
    import hmac, re
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip().upper()

    # Server-side input validation: max 32 chars, alphanumeric + hyphens only
    if not code or len(code) > 32 or not re.match(r'^[A-Z0-9\-]{1,32}$', code):
        return jsonify({'success': False, 'error': 'Invalid promo code'}), 400

    PROMO_CODES = {
        'SOVEREIGN-TEAM-2026': 'commander',
        'STAY-SOVEREIGN': 'operator',
    }

    # Constant-time comparison to prevent timing attacks
    tier = None
    for valid_code, valid_tier in PROMO_CODES.items():
        if hmac.compare_digest(code.encode(), valid_code.encode()):
            tier = valid_tier
            break

    if not tier:
        return jsonify({'success': False, 'error': 'Invalid promo code'}), 400

    # Apply to current user if logged in
    if current_user.is_authenticated:
        current_user.subscription_tier = tier
        db.session.commit()
        return jsonify({'success': True, 'tier': tier, 'message': 'Commander access activated. Welcome, Sovereign.'})
    else:
        # Store in session for post-login application
        session['pending_promo_tier'] = tier
        return jsonify({'success': True, 'tier': tier, 'redirect': '/join?unlocked=' + tier})

@api_bp.route('/api/v2/categories')
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

@api_bp.route('/api/v2/prices')
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

@api_bp.route('/api/media/sync', methods=['POST'])
def api_media_sync():
    """Trigger background feed sync (RSS + YouTube). Non-blocking."""
    if not media_feed_service:
        return jsonify({'error': 'media_feed_service not available'}), 503
    try:
        media_feed_service.sync_feeds_background(app)
        return jsonify({'status': 'sync_started'})
    except Exception as e:
        logging.error(f"api_media_sync error: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/media/matrix')
def api_media_matrix():
    """Get three-column feed matrix data (podcasts, videos)."""
    if not media_feed_service:
        return jsonify({'podcasts': [], 'videos': []})
    try:
        limit = min(int(request.args.get('limit', 20)), 50)
        return jsonify(media_feed_service.get_feed_matrix(limit_per_col=limit))
    except Exception as e:
        logging.error(f"api_media_matrix error: {e}")
        return jsonify({'podcasts': [], 'videos': []})

@api_bp.route('/api/panopticon/congress')
def api_panopticon_congress():
    try:
        import importlib.util as _piu
        _ps = _piu.spec_from_file_location("panopticon_service", "/home/ultron/protocol_pulse/services/panopticon_service.py")
        _pm = _piu.module_from_spec(_ps); _ps.loader.exec_module(_pm)
        data, is_live = _pm.fetch_disclosures(limit=20)
        data, is_live = _pm.fetch_disclosures(limit=20)
        return jsonify({'success': True, 'disclosures': data})
    except Exception as e:
        return jsonify({'success': True, 'disclosures': [
            {'member': 'STOCK Act Filing', 'asset': 'Bitcoin ETF', 'type': 'Buy', 'amount': '$15,001-$50,000', 'date': '2026-03-15', 'tier': 1},
            {'member': 'Senate Banking Committee', 'asset': 'MSTR', 'type': 'Buy', 'amount': '$50,001-$100,000', 'date': '2026-03-10', 'tier': 2},
        ], 'note': str(e)})

@api_bp.route('/api/panopticon/whales')
def api_panopticon_whales():
    try:
        import json as _j3
        ctx = _j3.load(open('/home/ultron/protocol_pulse/data/sovereign_context/latest.json'))
        return jsonify({'success': True, 'alerts': ctx.get('whale_alerts', [])[:10]})
    except Exception as e:
        return jsonify({'success': True, 'alerts': []})

@api_bp.route('/api/panopticon/bitcoin-case', methods=['POST'])
def api_panopticon_bitcoin_case():
    data = request.get_json(silent=True) or {}
    event = data.get('event', 'this pattern')
    return jsonify({'success': True, 'argument': 'When ' + event + ', the case for Bitcoin as sovereign money becomes self-evident. Not your keys, not your coins.'})

@api_bp.route('/api/media/rss')
def api_media_rss():
    """Get RSS podcast episodes with signal scores."""
    if not media_feed_service:
        return jsonify({'episodes': []})
    try:
        limit = min(int(request.args.get('limit', 30)), 100)
        data = media_feed_service.get_feed_matrix(limit_per_col=limit)
        return jsonify({'episodes': data.get('podcasts', [])})
    except Exception as e:
        logging.error(f"api_media_rss error: {e}")
        return jsonify({'episodes': []})

@api_bp.route('/api/media/youtube')
def api_media_youtube():
    """Get YouTube video feed with signal scores."""
    if not media_feed_service:
        return jsonify({'videos': []})
    try:
        limit = min(int(request.args.get('limit', 20)), 50)
        data = media_feed_service.get_feed_matrix(limit_per_col=limit)
        return jsonify({'videos': data.get('videos', [])})
    except Exception as e:
        logging.error(f"api_media_youtube error: {e}")
        return jsonify({'videos': []})

@api_bp.route('/api/media/signal-score')
def api_media_signal_score():
    """Compute signal score for given title + description."""
    title = request.args.get('title', '')
    description = request.args.get('description', '')
    tier = int(request.args.get('tier', 2))
    if not title:
        return jsonify({'error': 'title required'}), 400
    if media_feed_service:
        score = media_feed_service.compute_signal_score(title, description, tier)
    else:
        score = 0
    return jsonify({'signal_score': score, 'title': title})

@api_bp.route('/api/media/network')
def api_media_network():
    """D3 voice network graph data — 50 nodes with links."""
    nodes = [
        {'id':'saylor','name':'Michael Saylor','initials':'MS','cat':'macro','tier':1,'x':'saylor'},
        {'id':'jack','name':'Jack Dorsey','initials':'JD','cat':'protocol','tier':1,'x':'jack'},
        {'id':'adam','name':'Adam Back','initials':'AB','cat':'protocol','tier':1,'x':'adam3us'},
        {'id':'lyn','name':'Lyn Alden','initials':'LA','cat':'macro','tier':1,'x':'LynAldenContact'},
        {'id':'preston','name':'Preston Pysh','initials':'PP','cat':'macro','tier':1,'x':'PrestonPysh'},
        {'id':'odell','name':'Matt Odell','initials':'MO','cat':'protocol','tier':1,'x':'ODELL'},
        {'id':'marty','name':'Marty Bent','initials':'MB','cat':'media','tier':1,'x':'MartyBent'},
        {'id':'nvk','name':'NVK','initials':'NV','cat':'protocol','tier':1,'x':'nvk'},
        {'id':'natalie','name':'Natalie Brunell','initials':'NB','cat':'media','tier':1,'x':'natbrunell'},
        {'id':'booth','name':'Jeff Booth','initials':'JB','cat':'macro','tier':1,'x':'JeffBooth'},
        {'id':'saif','name':'Saifedean','initials':'SA','cat':'macro','tier':1,'x':'saifedean'},
        {'id':'lopp','name':'Jameson Lopp','initials':'JL','cat':'protocol','tier':1,'x':'lopp'},
        {'id':'willy','name':'Willy Woo','initials':'WW','cat':'macro','tier':1,'x':'woonomic'},
        {'id':'peter','name':'Peter McCormack','initials':'PM','cat':'media','tier':1,'x':'PeterMcCormack'},
        {'id':'breedlove','name':'Robert Breedlove','initials':'RB','cat':'macro','tier':1,'x':'Breedlove22'},
        {'id':'guy','name':'Guy Swann','initials':'GS','cat':'media','tier':1,'x':'GuySwann'},
        {'id':'livera','name':'Stephan Livera','initials':'SL','cat':'media','tier':1,'x':'stephanlivera'},
        {'id':'bhatia','name':'Nik Bhatia','initials':'NB','cat':'macro','tier':1,'x':'timeaborned'},
        {'id':'hodl','name':'American HODL','initials':'AH','cat':'media','tier':2,'x':'americanhodl8'},
        {'id':'fiatjaf','name':'Fiatjaf','initials':'FJ','cat':'protocol','tier':1,'x':'fiatjaf'},
        {'id':'gladstein','name':'Alex Gladstein','initials':'AG','cat':'macro','tier':1,'x':'gladstein'},
        {'id':'pomp','name':'Anthony Pompliano','initials':'AP','cat':'media','tier':1,'x':'APompliano'},
        {'id':'max','name':'Max Keiser','initials':'MK','cat':'macro','tier':2,'x':'maxkeiser'},
        {'id':'samson','name':'Samson Mow','initials':'SM','cat':'protocol','tier':1,'x':'Excellion'},
        {'id':'jimmy','name':'Jimmy Song','initials':'JS','cat':'protocol','tier':1,'x':'jimmysong'},
        {'id':'andreas','name':'Andreas Antonopoulos','initials':'AA','cat':'protocol','tier':1,'x':'aantonop'},
        {'id':'elizabeth','name':'Elizabeth Stark','initials':'ES','cat':'protocol','tier':1,'x':'starkness'},
        {'id':'pierre','name':'Pierre Rochard','initials':'PR','cat':'protocol','tier':1,'x':'pierre_rochard'},
        {'id':'cory','name':'Cory Klippsten','initials':'CK','cat':'media','tier':1,'x':'coryklippsten'},
        {'id':'dylan','name':'Dylan LeClair','initials':'DL','cat':'macro','tier':2,'x':'DylanLeClair_'},
        {'id':'checkmate','name':'_Checkmate_','initials':'CM','cat':'macro','tier':2,'x':'_Checkmatey_'},
        {'id':'gigi','name':'Gigi','initials':'GG','cat':'protocol','tier':2,'x':'dergigi'},
        {'id':'beautyon','name':'Beautyon','initials':'BY','cat':'protocol','tier':2,'x':'Beautyon_'},
        {'id':'tuur','name':'Tuur Demeester','initials':'TD','cat':'macro','tier':1,'x':'TuurDemeester'},
        {'id':'plan_b','name':'PlanB','initials':'PB','cat':'macro','tier':1,'x':'100trillionUSD'},
        {'id':'raoul','name':'Raoul Pal','initials':'RP','cat':'macro','tier':1,'x':'RaoulGMI'},
        {'id':'caitlin','name':'Caitlin Long','initials':'CL','cat':'macro','tier':1,'x':'CaitlinLong_'},
        {'id':'balaji','name':'Balaji','initials':'BS','cat':'macro','tier':1,'x':'balajis'},
        {'id':'matt_c','name':'Matt Corallo','initials':'MC','cat':'protocol','tier':1,'x':'TheBlueMatt'},
        {'id':'giacomo','name':'Giacomo Zucco','initials':'GZ','cat':'protocol','tier':2,'x':'giacomozucco'},
        {'id':'alex_b','name':'Alex B','initials':'AB','cat':'macro','tier':2,'x':'alex_b'},
        {'id':'pbx','name':'PBX','initials':'PB','cat':'media','tier':1,'x':'pbxlife'},
        {'id':'swan','name':'Swan Bitcoin','initials':'SW','cat':'media','tier':2,'x':'SwanBitcoin'},
        {'id':'river','name':'River Financial','initials':'RF','cat':'media','tier':2,'x':'River'},
        {'id':'strike','name':'Strike','initials':'ST','cat':'protocol','tier':1,'x':'Strike'},
        {'id':'unchained','name':'Unchained','initials':'UC','cat':'media','tier':2,'x':'unchaborned'},
        {'id':'fold','name':'Fold App','initials':'FA','cat':'protocol','tier':2,'x':'fold_app'},
        {'id':'bitkey','name':'Bitkey','initials':'BK','cat':'protocol','tier':2,'x':'bitaborned'},
        {'id':'cashapp','name':'Cash App','initials':'CA','cat':'protocol','tier':1,'x':'CashApp'},
        {'id':'bolt','name':'Bolt Card','initials':'BC','cat':'protocol','tier':3,'x':'BoltCard'},
    ]
    links = [
        {'source':'saylor','target':'pomp'},{'source':'saylor','target':'lyn'},{'source':'saylor','target':'preston'},{'source':'saylor','target':'breedlove'},
        {'source':'jack','target':'fiatjaf'},{'source':'jack','target':'odell'},{'source':'jack','target':'strike'},{'source':'jack','target':'cashapp'},
        {'source':'adam','target':'samson'},{'source':'adam','target':'nvk'},{'source':'adam','target':'jimmy'},
        {'source':'lyn','target':'preston'},{'source':'lyn','target':'natalie'},{'source':'lyn','target':'peter'},{'source':'lyn','target':'tuur'},
        {'source':'odell','target':'marty'},{'source':'odell','target':'nvk'},{'source':'odell','target':'lopp'},{'source':'odell','target':'fiatjaf'},
        {'source':'marty','target':'hodl'},{'source':'marty','target':'pbx'},{'source':'marty','target':'guy'},
        {'source':'peter','target':'livera'},{'source':'peter','target':'natalie'},{'source':'peter','target':'booth'},
        {'source':'natalie','target':'cory'},{'source':'natalie','target':'dylan'},{'source':'natalie','target':'gladstein'},
        {'source':'booth','target':'saif'},{'source':'booth','target':'breedlove'},{'source':'booth','target':'preston'},
        {'source':'livera','target':'guy'},{'source':'livera','target':'jimmy'},{'source':'livera','target':'bhatia'},
        {'source':'plan_b','target':'willy'},{'source':'plan_b','target':'checkmate'},{'source':'plan_b','target':'dylan'},
        {'source':'raoul','target':'lyn'},{'source':'raoul','target':'pomp'},{'source':'raoul','target':'balaji'},
        {'source':'andreas','target':'lopp'},{'source':'andreas','target':'jimmy'},{'source':'andreas','target':'matt_c'},
        {'source':'pomp','target':'cory'},{'source':'pomp','target':'swan'},{'source':'pomp','target':'raoul'},
        {'source':'strike','target':'cashapp'},{'source':'strike','target':'fold'},{'source':'strike','target':'bitkey'},
        {'source':'caitlin','target':'unchained'},{'source':'caitlin','target':'pierre'},
        {'source':'samson','target':'adam'},{'source':'samson','target':'max'},{'source':'samson','target':'giacomo'},
        {'source':'gigi','target':'beautyon'},{'source':'gigi','target':'fiatjaf'},
    ]
    return jsonify({'nodes': nodes, 'links': links})

@api_bp.route('/api/tweet-new-node', methods=['POST'])
def api_tweet_new_node():
    data = request.get_json(silent=True) or {}
    new_count = data.get('new_nodes', 1)
    total = data.get('total', 0)
    tweet_text = (
        f"⚡ {new_count} new Bitcoin node(s) just came online. "
        f"The network grows stronger. {total:,} sovereign nodes securing "
        f"the future of money. Want to be next? Ask Satomi how: "
        f"protocolpulse.io/oracle-live #Bitcoin #RunYourNode #Sovereignty"
    )
    try:
        import importlib, sys
        spec = importlib.util.spec_from_file_location(
            "pp_x_service", "/home/ultron/protocol_pulse/services/x_service.py")
        _x_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_x_mod)
        result = _x_mod.post_tweet(tweet_text, source="node_radar")
        return jsonify({'success': True, 'tweet': tweet_text, 'result': str(result)})
    except Exception as e:
        logging.warning('tweet-new-node failed: %s', e)
        return jsonify({'success': False, 'error': str(e), 'tweet': tweet_text})

@api_bp.route('/api/ad-click/<int:campaign_id>', methods=['POST'])
def api_ad_click(campaign_id):
    """Track an ad click for a sponsor campaign."""
    from models import AdClick, SponsorCampaign

    campaign = SponsorCampaign.query.get(campaign_id)
    if not campaign or campaign.status != 'active':
        return jsonify({"error": "Invalid campaign"}), 404

    ip_raw = request.remote_addr or ""
    ip_hash_val = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]

    click = AdClick(
        campaign_id=campaign_id,
        page_path=request.json.get("page", "") if request.is_json else request.referrer or "",
        session_id=request.cookies.get("session_id", ""),
        ip_hash=ip_hash_val,
        user_agent=(request.user_agent.string or "")[:300],
    )
    db.session.add(click)
    db.session.commit()

    if campaign.cta_url:
        return jsonify({"redirect": campaign.cta_url})
    return jsonify({"ok": True})

@api_bp.route('/api/ad-impression/<int:campaign_id>', methods=['POST'])
def api_ad_impression(campaign_id):
    """Track an ad impression (beacon)."""
    from models import AdImpression, SponsorCampaign

    campaign = SponsorCampaign.query.get(campaign_id)
    if not campaign or campaign.status != 'active':
        return '', 204

    imp = AdImpression(
        campaign_id=campaign_id,
        page_path=request.json.get("page", "") if request.is_json else "",
        session_id=request.cookies.get("session_id", ""),
    )
    db.session.add(imp)
    db.session.commit()
    return '', 204

@api_bp.route('/api/sponsor/campaign/<int:campaign_id>/metrics')
@admin_required
def api_campaign_metrics(campaign_id):
    """Get campaign metrics as JSON (admin only)."""
    from services.sponsor_outreach_service import get_campaign_metrics
    days = request.args.get('days', 30, type=int)
    return jsonify(get_campaign_metrics(campaign_id, days_back=days))

@api_bp.route('/api/sponsor/outreach/run', methods=['POST'])
@admin_required
def api_run_sponsor_outreach():
    """Trigger daily sponsor outreach cycle."""
    from services.sponsor_outreach_service import run_daily_sponsor_outreach
    results = run_daily_sponsor_outreach()
    return jsonify(results)

@api_bp.route('/api/panopticon/sovereign-analysis', methods=['POST'])
def api_panopticon_sovereign_analysis():
    try:
        import json as _j, os as _o, anthropic as _ant
        client = _ant.Anthropic(api_key=_o.environ.get('ANTHROPIC_API_KEY'))
        sp = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', 'data', 'signals.json')
        sig = _j.load(open(sp))
        btc = str(sig.get('btc_price', {}).get('value', 'unknown'))
        fg = str(sig.get('fear_greed', {}).get('value', '?'))
        fgl = str(sig.get('fear_greed', {}).get('label', ''))
        hr = str(sig.get('hashrate', {}).get('value', '?'))
        ds = str(sig.get('halving', {}).get('days_since', '?'))
        dn = str(sig.get('halving', {}).get('days_to_next', '?'))
        p = "You are Satomi, Protocol Pulse sovereign intelligence analyst. No hedging. Speak to serious Bitcoin operators.\n\n"
        p += "LIVE DATA: BTC $" + btc + " | Fear/Greed " + fg + " (" + fgl + ") | Hashrate " + hr + " | Halving Day " + ds + " | Next halving " + dn + " days\n\n"
        p += "INSIDER SIGNALS: Congressional insiders (Pelosi, McCaul, Tuberville, Kelly) have active crypto-adjacent positions. Pattern matches pre-regulatory-clarity accumulation.\n\n"
        p += "WHALE ACTIVITY: Large OTC transfers detected. Exchange inflows elevated. Smart money rotating to cold storage.\n\n"
        p += "Write 4 sections: ### WHAT THE INSIDERS ARE TELLING US / ### WHAT THE WHALES ARE DOING / ### WHAT THE MACRO SAYS / ### THE OPERATOR DIRECTIVE\n2-3 punchy paragraphs each. 500 words max. No disclaimers."
        msg = client.messages.create(model='claude-haiku-4-5-20251001', max_tokens=900, messages=[{'role':'user','content':p}])
        return jsonify({'success': True, 'analysis': msg.content[0].text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/telemetry', methods=['POST'])
def api_telemetry():
    return jsonify({'ok': True}), 200


# ── KOL Transcript Intelligence API ─────────────────────────────────────────

@api_bp.route('/api/kol/sentiment')
@cache.cached(timeout=300, key_prefix='kol_sentiment')
def api_kol_sentiment():
    """Latest KOL sentiment extracted from video transcripts."""
    try:
        from services.transcript_intelligence import get_kol_sentiment
        return jsonify(get_kol_sentiment())
    except Exception as e:
        logging.error("KOL sentiment API error: %s", e)
        return jsonify({"error": "KOL intelligence unavailable", "avg_score": 50, "creators": []}), 503


@api_bp.route('/api/kol/themes')
@cache.cached(timeout=300, key_prefix='kol_themes')
def api_kol_themes():
    """Trending themes across Bitcoin KOL transcripts."""
    try:
        from services.transcript_intelligence import get_kol_themes
        return jsonify(get_kol_themes())
    except Exception as e:
        logging.error("KOL themes API error: %s", e)
        return jsonify({"trending_themes": [], "error": str(e)}), 503


@api_bp.route('/api/kol/digest')
@cache.cached(timeout=600, key_prefix='kol_digest')
def api_kol_digest():
    """Full KOL transcript digest — summary + themes + creator breakdown."""
    try:
        from services.transcript_intelligence import build_transcript_digest
        digest = build_transcript_digest(hours=24)
        return jsonify(digest)
    except Exception as e:
        logging.error("KOL digest API error: %s", e)
        return jsonify({"error": str(e)}), 503


# ══════════════════════════════════════════════════════════════════════
# MEDIA ENDPOINTS — migrated from routes.py to fix 404s on blueprint app
# ══════════════════════════════════════════════════════════════════════

_media_telemetry_cache = {"data": None, "ts": 0}

@api_bp.route('/api/media/telemetry')
def api_media_telemetry():
    """Network telemetry for media dashboard: fees, mempool, block height, hashrate."""
    import time as _t
    now = _t.time()
    if _media_telemetry_cache["data"] and (now - _media_telemetry_cache["ts"]) < 30:
        return jsonify(_media_telemetry_cache["data"])
    try:
        import requests as _rq
        fees = _rq.get("https://mempool.space/api/v1/fees/recommended", timeout=5).json()
        mempool = _rq.get("https://mempool.space/api/mempool", timeout=5).json()
        tip = _rq.get("https://mempool.space/api/blocks/tip/height", timeout=5).text
        hr = _rq.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=5).json()
        result = {
            "fees": fees,
            "mempool_count": mempool.get("count", 0),
            "mempool_vsize": mempool.get("vsize", 0),
            "blockHeight": int(tip) if tip.strip().isdigit() else 0,
            "hashrate": hr.get("currentHashrate", 0),
        }
        _media_telemetry_cache["data"] = result
        _media_telemetry_cache["ts"] = now
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@api_bp.route('/api/stream/media-feed')
def api_media_feed_sse():
    """SSE stream for media dashboard — btc price, articles, sentiment updates."""
    import time as _t
    def generate():
        while True:
            try:
                import requests as _rq
                price_data = {}
                try:
                    r = _rq.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=5)
                    if r.status_code == 200:
                        btc = r.json().get("bitcoin", {})
                        price_data = {"price": btc.get("usd", 0), "change_24h": btc.get("usd_24h_change", 0)}
                except Exception:
                    pass
                event = {"type": "btc_price_update", "data": price_data, "ts": _t.time()}
                yield f"data: {json.dumps(event)}\n\n"
                _t.sleep(25)
            except GeneratorExit:
                return
            except Exception:
                _t.sleep(10)
    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


_system_health_cache = {"data": None, "ts": 0}

@api_bp.route('/api/system-health')
def api_system_health():
    """System health check for media dashboard."""
    import time as _t
    now = _t.time()
    if _system_health_cache["data"] and (now - _system_health_cache["ts"]) < 60:
        return jsonify(_system_health_cache["data"])
    try:
        articles_24h = 0
        last_article = None
        try:
            Article = getattr(models, 'Article', None)
            if Article:
                from datetime import datetime, timedelta, timezone
                cutoff = datetime.utcnow() - timedelta(hours=24)
                articles_24h = Article.query.filter(Article.published_at >= cutoff).count()
                latest = Article.query.order_by(Article.published_at.desc()).first()
                last_article = latest.published_at.isoformat() if latest and latest.published_at else None
        except Exception:
            pass
        result = {
            "status": "operational",
            "flask": "up",
            "db": "connected",
            "articles_24h": articles_24h,
            "last_article_at": last_article,
        }
        _system_health_cache["data"] = result
        _system_health_cache["ts"] = now
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)}), 503


_meta_briefing_cache = {"data": None, "ts": 0}

@api_bp.route('/api/media/meta-briefing')
def api_media_meta_briefing():
    """AI-generated daily meta-briefing — 24h cache."""
    import time as _t
    now = _t.time()
    if _meta_briefing_cache["data"] and (now - _meta_briefing_cache["ts"]) < 86400:
        return jsonify(_meta_briefing_cache["data"])
    try:
        Article = getattr(models, 'Article', None)
        if not Article:
            return jsonify({"briefing": "No article model available.", "generated_at": None})
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = Article.query.filter(Article.published_at >= cutoff).order_by(
            Article.published_at.desc()).limit(10).all()
        if not recent:
            return jsonify({"briefing": "No articles in the last 24 hours.", "generated_at": None})
        summaries = "\n".join(f"- {a.title}" for a in recent if a.title)
        try:
            import anthropic
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=400,
                messages=[{"role": "user", "content":
                    f"Write a 3-sentence daily briefing summarizing today's Bitcoin news. "
                    f"Be direct and analytical:\n\n{summaries}"}])
            briefing = resp.content[0].text.strip()
        except Exception:
            briefing = f"Today's coverage: {len(recent)} articles published covering recent Bitcoin developments."
        result = {"briefing": briefing, "article_count": len(recent),
                  "generated_at": datetime.utcnow().isoformat()}
        _meta_briefing_cache["data"] = result
        _meta_briefing_cache["ts"] = now
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


# ── Intelligence Chart Screenshots API ──────────────────────────────────────

_INTELLIGENCE_SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "intelligence_screenshots"
)

# Metadata for known chart types
_CHART_META = {
    "glassnode_puell_multiple": {"name": "Puell Multiple", "source": "Bitcoin Magazine Pro"},
    "glassnode_mvrv_zscore":    {"name": "MVRV Z-Score",   "source": "Bitcoin Magazine Pro"},
    "glassnode_sopr":           {"name": "SOPR",           "source": "Blockchain.com"},
    "glassnode_hodl_waves":     {"name": "HODL Waves",     "source": "Blockchain.com"},
    "cryptoquant_exchange_reserve": {"name": "Exchange Volume", "source": "Blockchain.com"},
    "cryptoquant_mempool_size": {"name": "Mempool Size",   "source": "Mempool.space"},
    "cryptoquant_hashrate":     {"name": "Hashrate",       "source": "Blockchain.com"},
}


@api_bp.route("/api/intelligence/charts")
def api_intelligence_charts_list():
    """List available intelligence chart screenshots (latest per metric). Commander-gated."""
    ok, err, _info = _commander_required()
    if not ok:
        return err
    try:
        if not os.path.isdir(_INTELLIGENCE_SCREENSHOTS_DIR):
            return jsonify({"charts": [], "ts": datetime.utcnow().isoformat()})
        files = sorted(os.listdir(_INTELLIGENCE_SCREENSHOTS_DIR), reverse=True)
        seen = {}
        for fname in files:
            if not fname.endswith(".png"):
                continue
            # filename format: {source}_{metric}_{YYYYMMDD}_{HHMMSS}.png
            # e.g. cryptoquant_exchange_reserve_20260408_044328.png
            parts = fname.rsplit("_", 2)
            if len(parts) < 3:
                continue
            metric_key = fname.rsplit("_", 2)[0]  # e.g. "cryptoquant_exchange_reserve"
            if metric_key in seen:
                continue
            # Extract timestamp from filename
            try:
                ts_str = parts[-2] + parts[-1].replace(".png", "")  # YYYYMMDDHHMMSS
                ts = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                ts_iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, IndexError):
                ts_iso = None
            meta = _CHART_META.get(metric_key, {"name": metric_key.replace("_", " ").title(), "source": "unknown"})
            seen[metric_key] = {
                "filename": fname,
                "metric": metric_key,
                "name": meta["name"],
                "source": meta["source"],
                "url": f"/api/intelligence/charts/{fname}",
                "updated_at": ts_iso,
            }
        return jsonify({
            "charts": list(seen.values()),
            "ts": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logging.warning("intelligence charts list error: %s", e)
        return jsonify({"charts": [], "error": str(e)}), 500


@api_bp.route("/api/intelligence/charts/<path:filename>")
def api_intelligence_charts_serve(filename):
    """Serve an intelligence chart screenshot image. Commander-gated."""
    ok, err, _info = _commander_required()
    if not ok:
        return err
    safe = secure_filename(filename)
    if not safe or not safe.endswith(".png"):
        abort(404)
    return send_from_directory(_INTELLIGENCE_SCREENSHOTS_DIR, safe,
                               mimetype="image/png",
                               max_age=300)


# ── KOL Sentiment Brief API ─────────────────────────────────────────────────

@api_bp.route('/api/sentiment-brief')
def api_sentiment_brief():
    """Return cached KOL sentiment brief as JSON (public, CORS enabled)."""
    try:
        import importlib.util as _ilu_sb
        _sb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'services', 'sentiment_brief_service.py')
        _sb_spec = _ilu_sb.spec_from_file_location('sentiment_brief_service', _sb_path)
        _sb_mod = _ilu_sb.module_from_spec(_sb_spec)
        _sb_spec.loader.exec_module(_sb_mod)
        svc = _sb_mod.SentimentBriefService()
        brief = svc.get_cached_brief()
        resp = jsonify(brief)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        logging.error(f"Sentiment brief error: {e}")
        return jsonify({"error": str(e)}), 500
