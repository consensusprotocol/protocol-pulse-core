"""
routes_pages.py — Pages routes blueprint for Protocol Pulse.
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
    _index_cache_key,
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
from datetime import datetime, timedelta
import threading
import time
from services.node_service import NodeService

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/debug-routes')
def debug_routes():
    """List all registered URL rules (for 404 debugging: confirm / is in the app that is actually running)."""
    rules = [{"rule": r.rule, "endpoint": r.endpoint, "methods": list(r.methods - {"HEAD", "OPTIONS"})}
             for r in app.url_map.iter_rules()]
    return jsonify({"app": "Protocol Pulse", "rules": sorted(rules, key=lambda x: x["rule"])})

@pages_bp.route('/health')
def health():
    """Liveness: app is up. Used by load balancers and Render."""
    return jsonify({"status": "ok", "service": "protocol-pulse"}), 200

@pages_bp.route('/ready')
def ready():
    """Readiness: app and DB are responsive. Used by orchestrators before sending traffic."""
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ready", "db": "ok"}), 200
    except Exception as e:
        logging.warning("Ready check failed: %s", e)
        return jsonify({"status": "not_ready", "db": "error"}), 503

@pages_bp.route('/robots.txt', endpoint='robots_txt_core')
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
        "Sitemap: https://protocolpulse.io/sitemap.xml",  # V31 SEO FIX
    ]
    return Response("\n".join(lines), mimetype="text/plain")

@pages_bp.route('/sitemap.xml')
def sitemap_xml():
    """Simple sitemap for SEO: home, articles, key public pages."""
    base = "https://protocolpulse.io"  # V31 SEO FIX: hardcode production URL (was localhost via tunnel)
    pages = [
        ("/", "daily", "1.0"),
        ("/articles", "daily", "0.9"),
        ("/terminal", "daily", "0.9"),
        ("/dossier", "weekly", "0.9"),
        ("/podcasts", "weekly", "0.8"),
        ("/media", "daily", "0.8"),
        ("/live", "daily", "0.8"),
        ("/whale-watcher", "daily", "0.8"),
        ("/briefing", "daily", "0.8"),
        ("/freedom-tech", "weekly", "0.7"),
        ("/map", "weekly", "0.7"),
        ("/charts", "daily", "0.7"),
        ("/mining", "daily", "0.7"),
        ("/newsletter", "monthly", "0.6"),
        ("/premium", "monthly", "0.6"),
        ("/about", "monthly", "0.5"),
        ("/contact", "monthly", "0.5"),
        ("/donate", "monthly", "0.5"),
        ("/donate/bitcoin", "monthly", "0.5"),
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

@pages_bp.route('/')
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
    for a in list(featured_articles) + list(recent_articles) + list(bento_articles):
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

@pages_bp.route('/live')
def live_terminal():
    """Live Settlement Terminal - Real-time Bitcoin network visualization"""
    return render_template('live_terminal.html')


@pages_bp.route('/sovereign-money')
def sovereign_money():
    """The Case for Sovereign Money — purchasing power decay thesis"""
    return render_template('sovereign_money.html')

@pages_bp.route('/bitfeed-live')
@pages_bp.route('/kinetic')
@pages_bp.route('/gravity-well')
def kinetic_terminal():
    """Redirect to Live Terminal - Sovereign Uplift Terminal with Three.js"""
    from flask import redirect
    return redirect('/live')

@pages_bp.route('/hud')
def predictive_hud():
    """Predictive HUD - AI-powered network predictions for miners and traders"""
    return render_template('predictive_hud.html')

@pages_bp.route('/map')
def merchant_map():
    """Sovereign Merchant Map - Interactive BTC vendor locator"""
    return render_template('merchant_map.html')

@pages_bp.route('/offline')
def offline():
    """Offline fallback page for PWA"""
    return render_template('offline.html')

@pages_bp.route('/whale-watcher')
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

@pages_bp.route('/bitfeed-live')
@pages_bp.route('/bitfeed-ultimate')
def bitfeed_ultimate():
    """Ultimate Bitfeed Visualizer - Blocks assemble into B, explode on new block"""
    return render_template('bitfeed_ultimate.html')

@pages_bp.route('/value-stream')
def value_stream():
    """Value Stream - Commander Pricing Page"""
    from flask import make_response
    resp = make_response(render_template('value_stream.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Vary'] = '*'
    resp.headers['Expires'] = '0'
    return resp

@pages_bp.route('/value-stream-legacy')
def value_stream_legacy():
    """Value Stream Legacy - Sovereign Intelligence Market"""
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

@pages_bp.route('/terminal')
@pages_bp.route('/signal-terminal')
def signal_terminal():
    """Signal Terminal — Bloomberg-grade Bitcoin intelligence dashboard."""
    import requests as _req
    price = {'price': 0, 'change_24h': 0, 'change_7d': 0, 'change_30d': 0,
             'market_cap': 0, 'volume_24h': 0, 'dominance': 0}
    mempool = {'fee_low': 1, 'fee_mid': 5, 'fee_high': 20, 'tx_count': 0, 'size_mb': 0}
    onchain = {'hashrate': 0, 'difficulty': 0, 'block_height': 0, 'next_halving': 0}
    lightning = {'capacity': 0, 'channels': 0, 'nodes': 0}
    fg = 25
    fg_class = 'extreme-fear'
    signal = {'score': 0, 'direction': 'neutral', 'classification': 'NEUTRAL', 'delta': 0}
    # Pull real data from convergence engine
    try:
        import json as _sj2
        ctx_path = "/home/ultron/protocol_pulse/data/sovereign_context/latest.json"
        with open(ctx_path) as _cf2:
            _sc = _sj2.load(_cf2)
        _idx = _sc.get('indices', {})
        _mc = _idx.get('miner_conviction', {})
        _ep = _idx.get('exchange_pressure', {})
        _sd = _idx.get('social_divergence', {})
        # Composite from convergence
        import json as _oj
        with open('/home/ultron/protocol_pulse/data/sovereign_context/latest.json') as _of:
            _orb_data = _oj.load(_of)
        _orb_resp = {'composite': {'score': 50, 'pattern': 'NEUTRAL'}, 'nodes': {}}
        if 'indices' in _orb_data:
            _idxd = _orb_data['indices']
            _orb_resp['composite'] = {'score': _idxd.get('convergence_score', {}).get('score', 50), 'pattern': _idxd.get('convergence_score', {}).get('pattern', 'NEUTRAL')}
        _comp = _orb_resp.get('composite', {})
        _comp_score = round(_comp.get('score', 0))
        _pattern = _comp.get('pattern', 'NEUTRAL')
        if _comp_score >= 65:
            _class = 'BULLISH'
        elif _comp_score >= 55:
            _class = 'CAUTIOUS BULLISH'
        elif _comp_score <= 35:
            _class = 'BEARISH'
        elif _comp_score <= 45:
            _class = 'CAUTIOUS BEARISH'
        else:
            _class = 'NEUTRAL'
        signal = {
            'score': _comp_score,
            'direction': 'bullish' if _comp_score >= 55 else ('bearish' if _comp_score <= 45 else 'neutral'),
            'classification': _class,
            'delta': 0,
            'pattern': _pattern,
            'miner_conviction': _mc.get('score', 0),
            'exchange_pressure': _ep.get('score', 0),
        }
    except Exception:
        pass
    latest = []
    try:
        import json as _stj
        ctx_path = "/home/ultron/protocol_pulse/data/sovereign_context/latest.json"
        with open(ctx_path) as _cf:
            _ctx = _stj.load(_cf)
        # Price: use internal API (CoinGecko via price_service works for this endpoint)
        try:
            _btc_data = _ctx.get('btc', {})
            _btc_price = _btc_data.get('price', 0) or 0
            _btc_change = _btc_data.get('change_24h', 0) or 0
        except Exception:
            _btc_price = 0
            _btc_change = 0
        _btc_ctx = _ctx.get('btc', {})
        price = {
            'price': _btc_price,
            'change_24h': _btc_change,
            'change_7d': _btc_ctx.get('change_7d', 0) or 0,
            'change_30d': _btc_ctx.get('change_30d', 0) or 0,
            'market_cap': _btc_ctx.get('market_cap', 0) or 0,
            'volume_24h': _btc_ctx.get('volume_24h', 0) or 0,
            'dominance': _btc_ctx.get('dominance', 0) or 0,
            'circulating': '19.85M BTC',
        }
        # F&G from sovereign context
        _fg = _ctx.get('fear_greed', {})
        fg = int(_fg.get('value', 25))
        fg_class = str(_fg.get('label', 'Fear')).lower().replace(' ', '-')
        # Mining from sovereign context
        _net = _ctx.get('network', {})
        onchain['hashrate'] = _net.get('hashrate_eh', 0)
        onchain['difficulty'] = _net.get('difficulty', 0)
        onchain['block_height'] = _ctx.get('block_height', 0)
    except Exception as e:
        logging.warning(f'[SignalTerminal] data load: {e}')
    # F&G already loaded from sovereign_context above — no external API needed
    try:
        r = _req.get('https://mempool.space/api/v1/fees/recommended', timeout=1.5)
        if r.ok:
            d = r.json()
            mempool['fee_low'] = d.get('hourFee', 1)
            mempool['fee_mid'] = d.get('halfHourFee', 5)
            mempool['fee_high'] = d.get('fastestFee', 20)
    except:
        pass
    # Latest block data (TX count + time since)
    try:
        r = _req.get('https://mempool.space/api/v1/blocks', timeout=2)
        if r.ok:
            blocks = r.json()
            if blocks and len(blocks) > 0:
                latest_block = blocks[0]
                mempool['block_tx_count'] = latest_block.get('tx_count', 0)
                mempool['block_timestamp'] = latest_block.get('timestamp', 0)
    except:
        pass
    # Mempool enrichment moved to sovereign_ctx block below
    try:
        r = _req.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=1.5)
        if r.ok:
            d = r.json()
            hs = d.get('currentHashrate', 0)
            onchain['hashrate'] = round(hs / 1e18, 1) if hs else 0
            diff = d.get('currentDifficulty', 0)
            if diff:
                onchain['difficulty'] = round(diff / 1e12, 2)
    except:
        pass
    # Fallback: fetch difficulty directly
    if not onchain.get('difficulty'):
        try:
            r2 = _req.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=1.5)
            if r2.ok:
                da = r2.json()
                diff2 = da.get('difficultyChange', 0)
                onchain['difficulty'] = round(da.get('difficulty', 0) / 1e12, 2) if da.get('difficulty') else 0
                onchain['next_adj_pct'] = round(da.get('estimatedRetargetPercentage', 0), 1)
                onchain['next_adj_blocks'] = da.get('remainingBlocks', 0)
                onchain['blocks_to_halving'] = max(0, 1050000 - (sovereign_ctx.get('block_height', 0) or 0))
        except:
            pass
    macro = {}
    try:
        _macro_raw = _ctx.get('macro', {})
        _gold = _macro_raw.get('gold_price') or 0
        _sp = _macro_raw.get('sp500') or 0
        _dxy = _macro_raw.get('dxy') or 0
        macro = {
            'dxy': round(_dxy, 1) if _dxy else None,
            'gold': round(_gold, 1) if _gold else None,
            'sp500': round(_sp, 2) if _sp else None,
            'btc_gold_ratio': round(price.get('price', 0) / _gold, 2) if _gold else None,
            'btc_gold_corr': _macro_raw.get('btc_vs_gold_30d_corr'),
        }
    except Exception:
        pass
    try:
        from models import Article
        latest = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).limit(8).all()
    except:
        pass
    is_commander = False
    try:
        if current_user.is_authenticated:
            t = getattr(current_user, 'subscription_tier', 'free')
            is_commander = t in ('commander', 'sovereign', 'admin')
    except:
        pass
    # Build alerts from latest articles for the Intelligence Feed
    alerts = []
    try:
        for art in latest:
            alerts.append({
                'time': art.created_at.strftime('%H:%M') if art.created_at else '--:--',
                'title': art.title,
                'url': f'/articles/{art.slug or art.id}',
                'is_alert': False,
            })
    except Exception:
        pass

    # Pass fg as dict (template expects fg.value / fg.classification)
    fg_dict = {'value': fg, 'classification': fg_class.replace('-', ' ').title()}

    # Pass FULL sovereign context for rich data display
    sovereign_ctx = {}
    try:
        import json as _stj2
        with open("/home/ultron/protocol_pulse/data/sovereign_context/latest.json") as _cf3:
            sovereign_ctx = _stj2.load(_cf3)
        # Enrich price with sovereign data
        _sbtc = sovereign_ctx.get('btc', {})
        if price.get('market_cap', 0) == 0 and _sbtc.get('market_cap'):
            price['market_cap'] = _sbtc.get('market_cap', 0)
        if price.get('volume_24h', 0) == 0 and _sbtc.get('volume_24h'):
            price['volume_24h'] = _sbtc.get('volume_24h', 0)
        if price.get('dominance', 0) == 0 and _sbtc.get('dominance'):
            price['dominance'] = _sbtc.get('dominance', 0)
        if price.get('change_24h', 0) == 0 and _sbtc.get('change_24h'):
            price['change_24h'] = _sbtc.get('change_24h', 0)
        # Enrich mempool from sovereign context
        _smem = sovereign_ctx.get('mempool', {})
        mempool['unconfirmed_count'] = _smem.get('unconfirmed', 0)
        mempool['size_mb'] = _smem.get('size_mb', 0)
        mempool['block_height'] = sovereign_ctx.get('block_height', 0)
        # Enrich lightning
        _sln = sovereign_ctx.get('lightning', {})
        _ln_cap = _sln.get('capacity_btc', 0) or 0
        _ln_ch = _sln.get('channels', 0) or 0
        lightning = {
            'capacity': _ln_cap,
            'channels': _ln_ch,
            'nodes': _sln.get('nodes', 0),
            'avg_capacity': round(_ln_cap / _ln_ch, 4) if _ln_ch > 0 else 0,
        }
        # Enrich onchain
        _snet = sovereign_ctx.get('network', {})
        onchain['block_height'] = sovereign_ctx.get('block_height', 0)
        onchain['next_adj_pct'] = _snet.get('next_adj_pct', 0)
        onchain['next_adj_blocks'] = _snet.get('next_adj_blocks', 0)
        onchain['next_adjustment'] = str(round(_snet.get('next_adj_pct', 0), 1)) + '%' if _snet.get('next_adj_pct') else None
        onchain['blocks_to_halving'] = max(0, 1050000 - (sovereign_ctx.get('block_height', 0) or 0))
        # Build macro from sovereign
        _smac = sovereign_ctx.get('macro', {})
        macro = {
            'dxy': _smac.get('dxy'),
            'gold': _smac.get('gold_price'),
            'sp500': _smac.get('sp500'),
            'btc_gold_ratio': round(price.get('price', 0) / _smac['gold_price'], 2) if _smac.get('gold_price') else None,
        }
        # Options + Futures
        _sopt = sovereign_ctx.get('options', {})
        _sfut = sovereign_ctx.get('futures', {})
    except Exception as _e:
        logging.warning(f'[Terminal] sovereign enrichment: {_e}')
        macro = {}
        _sopt = {}
        _sfut = {}

    return render_template('signal_terminal.html',
        price=price, mempool=mempool, onchain=onchain,
        lightning=lightning, fg=fg_dict, fg_class=fg_class,
        signal=signal, latest=latest, is_commander=is_commander,
        alerts=alerts, macro=macro, sovereign_ctx=sovereign_ctx,
        options=_sopt, futures=_sfut)

@pages_bp.route('/extension')
def extension_page():
    """Browser extension download and info page"""
    return render_template('extension.html')

@pages_bp.route('/extension/download')
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

@pages_bp.route('/scorecard')
def sovereign_scorecard():
    """Sovereign Scorecard - Security self-assessment quiz"""
    return render_template('sovereign_scorecard.html')

@pages_bp.route('/drill')
def recovery_drill():
    """Recovery Drill - Seed phrase practice without real keys"""
    return render_template('recovery_drill.html')

@pages_bp.route('/operator-costs')
def operator_costs():
    """Operator Costs - Fee leakage calculator"""
    return render_template('operator_costs.html')

@pages_bp.route('/solo-slayers')
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

@pages_bp.route('/dossier')
def dossier():
    """The Protocol Pulse Dossier — Sovereign 7 (7 chapters). Main dossier template is dossier.html."""
    chapters = _get_sovereign7_chapters()
    resp = make_response(render_template('dossier.html', chapters=chapters))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@pages_bp.route('/dossier/classic')
def dossier_classic():
    """The Protocol Pulse Dossier — full 32-slide version."""
    manifest_path = _dossier_manifest_path()
    manifest = _load_json_manifest(manifest_path)
    return render_template('dossier_classic.html', manifest=manifest)

@pages_bp.route('/mining-risk')
def mining_risk():
    """Mining Risk by Geography — risk factor by deployment location with real-time metrics"""
    return render_template('mining_risk.html')

@pages_bp.route('/.well-known/nostr.json')
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

@pages_bp.route('/chat')
def ask_alex_chat():
    """Ask Alex Chat - LangGraph conversational agent for Bitcoin intelligence"""
    from flask import redirect; return redirect('/oracle-live')  # replaced by Oracle

@pages_bp.route('/clips')
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

@pages_bp.route('/dashboard')
@login_required
def commander_dashboard():
    """Commander Terminal — $29/mo subscriber dashboard (Bloomberg-grade)."""
    if not current_user.has_commander_tier():
        flash('Commander tier required for dashboard access.', 'warning')
        return redirect(url_for('auth.join_page'))

    # Auto-generate API key on first visit
    if not current_user.api_key:
        import secrets as _sec
        current_user.api_key = 'pp_live_' + _sec.token_hex(20)
        db.session.commit()

    # Latest articles for feed
    articles = models.Article.query.filter_by(published=True).order_by(
        models.Article.created_at.desc()
    ).limit(10).all()

    return render_template('dashboard.html', user=current_user, articles=articles)

@pages_bp.route('/articles')
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
    if not content: return ""
    import re as _rx
    content = _rx.sub(r'<div[^>]*class=["\'][^"\']*tldr[^"\']*["\'][^>]*>.*?</div>', '', content, flags=_rx.DOTALL|_rx.IGNORECASE)
    content = _rx.sub(r'<p[^>]*>.*?TL;DR:.*?</p>', '', content, flags=_rx.DOTALL|_rx.IGNORECASE)
    content = _rx.sub(r'<h1[^>]*>.*?</h1>', '', content, flags=_rx.DOTALL|_rx.IGNORECASE)
    # Return full content after h1/tldr removal — do NOT truncate at h2
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

@pages_bp.route('/articles/<int:article_id>')
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
    # Resolve and SAVE image to DB if missing (fixes blank images on detail page)
    header_image_url = article.resolve_cover_image() if hasattr(article, 'resolve_cover_image') else (article.cover_image_url or article.header_image_url or "/static/images/default-header.png")
    if not header_image_url or header_image_url == "/static/images/default-header.png":
        try:
            from services.pexels_image import get_pexels_image
            fetched = get_pexels_image(article.title or "", article.category or "bitcoin")
            if fetched and fetched != "/static/images/default-header.png":
                header_image_url = fetched
                article.cover_image_url = fetched
                db.session.commit()
        except Exception:
            pass

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

@pages_bp.route('/category/<category>')
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

@pages_bp.route('/podcasts')
def podcasts():
    """Cypherpunk'd series showcase — dedicated podcast page."""
    series_config = {
        'everything_21m': {
            'key': 'everything_21m',
            'title': 'Everything Divided by 21 Million',
            'host': 'Matty Ice & Knut Svanholm',
            'description': "A cinematic exploration of Bitcoin's relationship to time, money, freedom, and human progress.",
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
                {'id': 'M3M61rLBTl0', 'title': "Bitcoin is God's Gift | Episode 8"},
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
                {'id': '3VDVbbSZYPc', 'title': "The Peasants' Revolt | Episode 4"},
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
            'description': "Exploring the origins of Bitcoin through Aaron van Wirdum's seminal work on Austrian economics and the cypherpunk movement.",
            'playlist_url': 'https://www.youtube.com/playlist?list=PLQ4MjCv9OedqhL5At0WQs06GShfVkgPvT',
            'episodes': [
                {'id': '3TslgynKeaA', 'title': 'Austrian Economics & Money | Episode 1'},
                {'id': 'PFi6no-0wSE', 'title': 'Neutral Money & Denationalization | Episode 2'},
                {'id': 'PLWhV1JBfCA', 'title': 'Free and Open Source Software | Episode 3'},
                {'id': 'J5b24c0QzCE', 'title': 'Cryptography & Spies | Episode 4'},
                {'id': 'FzrKToH9AT0', 'title': 'eCash & Timestamps | Episode 5'},
                {'id': 'c3Nafsnts-Q', 'title': 'The Extropians & High Tech Hayekians | Episode 6'},
                {'id': 'wDUePxNsgLs', 'title': 'The Rise of the Cypherpunks | Episode 7'},
                {'id': 'WB5-IR5xrAE', 'title': 'Hashcash & Bit Gold | Episode 8'},
                {'id': 'vydVrF07QGA', 'title': 'B-money and RPOW | Episode 9'},
                {'id': 'VDdc67_HnVE', 'title': "Bitcoin's Revolutionary Origins | Episode 10"},
            ]
        },
        'bitcoin_boomers': {
            'key': 'bitcoin_boomers',
            'title': 'Bitcoin Boomers',
            'host': 'Guy Swann & Mark Moss',
            'description': 'Breaking down Bitcoin for the generation that built the world and is now watching fiat destroy it. Straightforward Bitcoin education for those who came of age before the internet.',
            'playlist_url': 'https://www.youtube.com/channel/UCOp_-d0z7r-s02CWsJTbVoA',
            'episodes': [
                {'id': 'nSbbx_2ziIU', 'title': 'What Happens at the Next Bitcoin Halving'},
                {'id': 'bNkM6ICRU3g', 'title': 'Bitcoin Follows a Commodity Like Cycle with Lawrence Lepard'},
                {'id': 'kYePThn-uLY', 'title': 'Who is in Charge of Bitcoin?'},
                {'id': 'x49S0mjhfX4', 'title': 'Bitcoin Your Escape Hatch to Financial Freedom & Peace'},
                {'id': '1SpHk6W4dIg', 'title': 'Bitcoin is Volatile But Ultimately Is the Future of Sound Money'},
                {'id': 'Ou66PgqPcyU', 'title': 'Financial Advisors Were WRONG About Bitcoin'},
            ]
        },
    }
    series_list = []
    for key, s in series_config.items():
        series_list.append({
            'key': key,
            'title': s['title'],
            'host': s['host'],
            'description': s['description'],
            'first_id': s['episodes'][0]['id'] if s['episodes'] else '',
            'ep_count': len(s['episodes']),
            'playlist_url': s.get('playlist_url', ''),
        })

    # Bitcoin Boomers latest episodes (YouTube channel UCOp_-d0z7r-s02CWsJTbVoA)
    boomers_episodes = []
    try:
        import feedparser as _fp
        import requests as _req
        _boomers_rss = 'https://www.youtube.com/feeds/videos.xml?channel_id=UCOp_-d0z7r-s02CWsJTbVoA'
        _br = _req.get(_boomers_rss, headers={'User-Agent': 'Mozilla/5.0 (compatible; ProtocolPulse/1.0)'}, timeout=10)
        _bf = _fp.parse(_br.text)
        for _be in _bf.entries[:6]:
            _vid = _be.get('yt_videoid', '')
            if _vid:
                boomers_episodes.append({'id': _vid, 'title': _be.get('title', '').strip()})
    except Exception:
        pass
    # Fallback if RSS fails
    if not boomers_episodes:
        boomers_episodes = [
            {'id': 'nSbbx_2ziIU', 'title': 'What Happens at the Next Bitcoin Halving'},
            {'id': 'bNkM6ICRU3g', 'title': 'Bitcoin Follows a Commodity Like Cycle with Lawrence Lepard'},
            {'id': 'kYePThn-uLY', 'title': 'Who is in Charge of Bitcoin?'},
            {'id': 'x49S0mjhfX4', 'title': 'Bitcoin Your Escape Hatch to Financial Freedom & Peace'},
            {'id': '1SpHk6W4dIg', 'title': 'Bitcoin is Volatile But Ultimately Is the Future of Sound Money'},
            {'id': 'Ou66PgqPcyU', 'title': 'Financial Advisors Were WRONG About Bitcoin'},
        ]

    total_episodes = sum(len(s['episodes']) for s in series_config.values()) + len(boomers_episodes)

    return render_template('podcasts.html',
                           series_list=series_list,
                           series_data=series_config,
                           total_episodes=total_episodes,
                           boomers_episodes=boomers_episodes)

@pages_bp.route('/rss/podcasts.xml')
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

@pages_bp.route('/media-terminal')
def media_terminal():
    """Redirect media-terminal to the unified media hub"""
    return redirect(url_for('pages.media_hub'))

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

@pages_bp.route('/media')
@pages_bp.route('/media-hub')
def media_hub():
    """Bitcoin Media Command Center — RSS feeds, YouTube, D3 network, signal scores"""
    our_books, recommended_books = _get_media_hub_books()

    # Build all_books with category tags for the template book sections
    all_books = []
    for b in our_books:
        b['category'] = 'series'
        all_books.append(b)
    for b in recommended_books:
        if b.get('bestseller'):
            b['category'] = 'essential'
        else:
            b['category'] = 'economics'
        all_books.append(b)

    # Feed matrix, ticker, stats from media_feed_service
    feed_matrix = {'podcasts': [], 'videos': []}
    ticker_items = []
    feed_stats = {'feed_count': 0, 'episode_count': 0, 'podcast_count': 0, 'video_count': 0}
    # Use the global media_feed_service instance (same one API uses — confirmed working)
    try:
        feed_matrix = media_feed_service.get_feed_matrix(limit_per_col=20)
        ticker_items = media_feed_service.get_ticker_items(limit=30)
        pods = feed_matrix.get('podcasts', [])
        vids = feed_matrix.get('videos', [])
        feed_names = set()
        for ep in pods + vids:
            fn = ep.get('feed_name', '') or ep.get('source', '')
            if fn:
                feed_names.add(fn)
        feed_stats = {
            'feed_count': len(feed_names) or 18,
            'episode_count': len(pods) + len(vids),
            'podcast_count': len(pods),
            'video_count': len(vids),
        }
        # Kick background sync (non-blocking)
        import threading
        threading.Thread(target=lambda: sync_all_feeds(app), daemon=True).start()
    except Exception as e:
        logging.error('media data fetch error: %s', e)

    # YouTube series data for Original Series section — hardcoded for reliability
    series_config = {
        'everything_21m': {
            'key': 'everything_21m',
            'title': 'Everything Divided by 21 Million',
            'host': 'Matty Ice & Knut Svanholm',
            'description': "A cinematic exploration of Bitcoin's relationship to time, money, freedom, and human progress.",
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
                {'id': 'M3M61rLBTl0', 'title': "Bitcoin is God's Gift | Episode 8"},
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
                {'id': '3VDVbbSZYPc', 'title': "The Peasants' Revolt | Episode 4"},
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
            'description': "Exploring the origins of Bitcoin through Aaron van Wirdum's seminal work on Austrian economics and the cypherpunk movement.",
            'playlist_url': 'https://www.youtube.com/playlist?list=PLQ4MjCv9OedqhL5At0WQs06GShfVkgPvT',
            'episodes': [
                {'id': '3TslgynKeaA', 'title': 'Austrian Economics & Money | Episode 1'},
                {'id': 'PFi6no-0wSE', 'title': 'Neutral Money & Denationalization | Episode 2'},
                {'id': 'PLWhV1JBfCA', 'title': 'Free and Open Source Software | Episode 3'},
                {'id': 'J5b24c0QzCE', 'title': 'Cryptography & Spies | Episode 4'},
                {'id': 'FzrKToH9AT0', 'title': 'eCash & Timestamps | Episode 5'},
                {'id': 'c3Nafsnts-Q', 'title': 'The Extropians & High Tech Hayekians | Episode 6'},
                {'id': 'wDUePxNsgLs', 'title': 'The Rise of the Cypherpunks | Episode 7'},
                {'id': 'WB5-IR5xrAE', 'title': 'Hashcash & Bit Gold | Episode 8'},
                {'id': 'vydVrF07QGA', 'title': 'B-money and RPOW | Episode 9'},
                {'id': 'VDdc67_HnVE', 'title': "Bitcoin's Revolutionary Origins | Episode 10"},
            ]
        },
    }
    series_list = []
    series_data = series_config
    for key, s in series_config.items():
        series_list.append({
            'key': key,
            'title': s['title'],
            'host': s['host'],
            'description': s['description'],
            'first_id': s['episodes'][0]['id'] if s['episodes'] else '',
            'ep_count': len(s['episodes']),
            'playlist_url': s.get('playlist_url', ''),
        })

    # Latest Cypherpunk'd episodes (from media_feed_service DB)
    latest_episodes = []
    try:
        cypher_feed = models.MediaFeed.query.filter(models.MediaFeed.name.like("%Cypherpunk%")).first()
        if cypher_feed:
            cypher_eps = models.MediaEpisode.query.filter_by(feed_id=cypher_feed.id).order_by(
                models.MediaEpisode.published_at.desc()).limit(8).all()
            for ep in cypher_eps:
                latest_episodes.append({
                    'title': ep.title,
                    'audio_url': ep.audio_url or '',
                    'duration': ep.duration or '',
                })
    except Exception:
        pass

    # Commander check
    is_commander = False
    try:
        if current_user.is_authenticated:
            is_commander = getattr(current_user, 'subscription_tier', '') in ('commander', 'sovereign')
    except Exception:
        pass

    return render_template('media_hub.html',
                           ticker_items=ticker_items,
                           feed_stats=feed_stats,
                           feed_matrix=feed_matrix,
                           series_list=series_list,
                           series_data=series_data,
                           latest_episodes=latest_episodes,
                           all_books=all_books,
                           our_books=our_books,
                           recommended_books=recommended_books,
                           is_commander=is_commander)

@pages_bp.route('/curated-mining')
def curated_mining_page():
    """Curated Mining — white-glove Bitcoin mining service."""
    return render_template('curated_mining.html')

@pages_bp.route('/merch')
def merch_store():
    """Merch store page"""
    try:
        products = printful_service.get_store_products()
        formatted_products = []
        
        for product in products:
            formatted_product = printful_service.format_product_for_display(product)
            if not formatted_product.get('is_ignored', False):
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
        
        app.logger.warning(f'MERCH_DEBUG: returning {len(formatted_products)} products')
        return render_template('merch.html', 
                             products=formatted_products,
                             rtsa_hot=rtsa_hot,
                             rtsa_approved=rtsa_approved,
                             rtsa_foundational=rtsa_foundational)
    except Exception as e:
        logging.error(f"Error loading merch store: {e}")
        flash('Error loading merchandise. Please try again later.')
        return render_template('merch.html', products=[], rtsa_hot=[], rtsa_approved=[], rtsa_foundational=[])

@pages_bp.route('/merch/success')
def merch_success():
    """Merch purchase success page"""
    session_id = request.args.get('session_id', '')
    return render_template('merch_success.html', session_id=session_id)

@pages_bp.route('/bitcoin')
def bitcoin_category():
    """Bitcoin category page"""
    articles = models.Article.query.filter_by(published=True, category='Bitcoin').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Bitcoin')

@pages_bp.route('/defi')
def defi_category():
    """DeFi category page"""
    articles = models.Article.query.filter_by(published=True, category='DeFi').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='DeFi')

@pages_bp.route('/regulation')
def regulation_category():
    """Regulation category page"""
    articles = models.Article.query.filter_by(published=True, category='Regulation').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Regulation')

@pages_bp.route('/privacy')
def privacy_category():
    """Privacy category page"""
    articles = models.Article.query.filter_by(published=True, category='Privacy').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Privacy')

@pages_bp.route('/innovation')
def innovation_category():
    """Innovation category page"""
    articles = models.Article.query.filter_by(published=True, category='Innovation').order_by(models.Article.created_at.desc()).all()
    return render_template('category.html', articles=articles, category='Innovation')

@pages_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@pages_bp.route('/privacy-policy')
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

@pages_bp.route('/contact', methods=['GET', 'POST'])
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
        return redirect(url_for("pages.contact"))
    return render_template('contact.html')

@pages_bp.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    """Handle newsletter subscription requests"""
    try:
        email = request.form.get('email')
        if not email:
            flash('Email address is required.', 'error')
            return redirect(url_for('pages.index'))
        
        success = newsletter_service.subscribe_user(email)
        if success:
            flash('Successfully subscribed to Protocol Pulse newsletter!', 'success')
        else:
            flash('Newsletter subscription failed. Please try again.', 'error')
    except Exception as e:
        logging.error(f"Newsletter subscription error: {e}")
        flash('An error occurred. Please try again.', 'error')
    
    return redirect(url_for('pages.index'))

@pages_bp.route('/unsubscribe')
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


# ═══════════════════════════════════════════════════════════════════════
# THE BITCOIN BOOMERS — Standalone brand presence within Protocol Pulse
# ═══════════════════════════════════════════════════════════════════════

# Canonical episode catalog — used by index + episode detail views
_BOOMERS_EPISODES = [
    {
        'num': '07',
        'slug': 'cpa-wrong-about-bitcoin',
        'date': 'April 14, 2026',
        'duration': '52 min',
        'title': 'Why Your CPA Is Wrong About Bitcoin',
        'desc': 'Cost basis, tax lots, and the one rule every retiree with BTC needs to memorize before year-end.',
        'summary': 'Larry walks through the three most common cost-basis mistakes he sees on client K-1s, Bob explains why mining income is a different beast entirely, and Gary shares the one-pager he mails to every new BTC-curious friend over 60.',
        'topics': [
            'Cost-basis methods: FIFO, LIFO, specific-ID — what actually saves tax',
            'Why your CPA does not understand what a sat actually is',
            'Mining income and the self-employment tax trap',
            'Gifting BTC to heirs: the stepped-up basis window',
            'Year-end tax-loss harvesting when BTC is up 200%',
        ],
    },
    {
        'num': '06',
        'slug': 'pension-crisis-nobody-talks-about',
        'date': 'April 07, 2026',
        'duration': '48 min',
        'title': 'The Pension Crisis Nobody Wants to Talk About',
        'desc': 'Underfunded liabilities, 60/40 failure, and why Bitcoin is the only escape hatch left for retirees.',
        'summary': 'A hard look at the $5T of unfunded pension liabilities, what happens when boomers retire into a broken 60/40, and why a small BTC allocation now is the cheapest hedge money can buy.',
        'topics': [
            'The math behind a 0% real-return decade',
            'Why corporate pension plans are quietly allocating to BTC',
            'The 2% rule: small allocation, asymmetric upside',
            'Sequence-of-returns risk for new retirees',
        ],
    },
    {
        'num': '05',
        'slug': 'passing-sats-to-grandkids',
        'date': 'March 31, 2026',
        'duration': '61 min',
        'title': 'Passing Sats to the Grandkids — The Right Way',
        'desc': 'Multi-sig, inheritance protocols, and the estate-planning conversations your attorney has never had.',
        'summary': 'The estate-planning playbook for BTC holders: why a standard will is not enough, how Unchained and Casa are solving this, and what to put in writing before you cannot write anything.',
        'topics': [
            'Why a standard will does nothing for your BTC',
            'Multi-sig inheritance: Unchained, Casa, and DIY',
            'The "letter of final instructions" template',
            'Training heirs: custody literacy without exposure',
        ],
    },
]


@pages_bp.route('/bitcoin-boomers')
def boomers_index():
    """The Bitcoin Boomers — standalone brand landing page."""
    return render_template('boomers/index.html', episodes=_BOOMERS_EPISODES)


@pages_bp.route('/bitcoin-boomers/episode/<slug>')
def boomers_episode(slug):
    """Single episode page for The Bitcoin Boomers."""
    episode = next((e for e in _BOOMERS_EPISODES if e['slug'] == slug), None)
    if not episode:
        return render_template('boomers/episode.html', episode=None), 404
    return render_template('boomers/episode.html', episode=episode)


@pages_bp.route('/bitcoin-boomers/subscribe', methods=['POST'])
def boomers_subscribe():
    """Subscribe to The Boomers Dispatch — writes to newsletter_subscribers with source='boomers'."""
    email = (request.form.get('email') or '').strip().lower()
    if not email or '@' not in email or '.' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('pages.boomers_index') + '#subscribe')

    try:
        existing = models.NewsletterSubscriber.query.filter_by(email=email).first()
        if existing:
            if not existing.subscribed:
                existing.subscribed = True
                existing.unsubscribed_at = None
                db.session.commit()
            flash('You are already on the Boomers Dispatch list. Welcome back.', 'success')
        else:
            sub = models.NewsletterSubscriber(
                email=email,
                unsubscribe_token=str(uuid.uuid4()),
                subscribed=True,
                source='boomers',
            )
            db.session.add(sub)
            db.session.commit()
            flash('Subscribed. Your first Boomers Dispatch arrives Sunday.', 'success')
    except Exception as e:
        logging.error(f"Boomers subscribe error: {e}")
        db.session.rollback()
        flash('Subscription failed. Please try again.', 'error')

    return redirect(url_for('pages.boomers_index') + '#subscribe')


@pages_bp.route('/bitcoin-boomers/social-card/<slug>')
def boomers_social_card(slug):
    """1200x630 social card for episode announcements. Render to PNG via browser screenshot."""
    episode = next((e for e in _BOOMERS_EPISODES if e['slug'] == slug), None)
    return render_template('boomers/social_card.html', episode=episode)


@pages_bp.route('/test/generate-article', methods=['POST'])
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

@pages_bp.route('/sentiment')
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

@pages_bp.route('/intelligence')
def intelligence_main():
    """Intelligence → Signal Terminal (merged)."""
    return redirect('/terminal', code=302)

@pages_bp.route('/intelligence/legacy')
def intelligence_legacy_page():
    """Legacy Intelligence Dashboard — world-class redesign (kept for reference)."""
    import json as _json
    from datetime import timedelta as _td
    from sqlalchemy import text as _text

    # ── Commander status ──
    is_commander = False
    try:
        from flask_login import current_user as _cu
        if _cu.is_authenticated:
            is_commander = getattr(_cu, 'subscription_tier', '') in ('commander', 'sovereign')
    except Exception:
        pass

    # ── Signal + content data ──
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
    except Exception:
        signal = {"composite": 50, "label": "NEUTRAL", "color": "#f8c15c", "components": {}, "trajectory": "UNKNOWN"}
        trending, entities, narrative_timeline, intel_events = [], [], [], []

    # ── Top articles ──
    top_articles = []
    try:
        imp_rows = db.session.execute(
            _text("""SELECT id, title, sentiment, narrative_label, importance_score,
                            market_impact_magnitude, created_at
                     FROM articles WHERE published=1
                     ORDER BY importance_score DESC NULLS LAST, created_at DESC
                     LIMIT 15""")
        ).fetchall()
        top_articles = [
            {"id": r[0], "title": r[1], "sentiment": r[2] or "unclassified",
             "narrative_label": r[3] or "\u2014", "importance_score": int(r[4] or 50),
             "impact": float(r[5] or 5.0), "created_at": str(r[6])}
            for r in imp_rows
        ]
    except Exception:
        pass

    # ── Sovereign context ──
    sovereign_ctx = {}
    try:
        sovereign_ctx = _load_sovereign_ctx()
    except Exception:
        try:
            _ctx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sovereign_context', 'latest.json')
            if os.path.exists(_ctx_path):
                with open(_ctx_path) as f:
                    sovereign_ctx = json.load(f)
        except Exception:
            pass

    # ── Polymarket ──
    polymarket_markets, polymarket_sentiment = [], 50
    try:
        import importlib.util as _ilu
        _pm_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services', 'polymarket_service.py')
        _spec = _ilu.spec_from_file_location('polymarket_service', _pm_path)
        _pm = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_pm)
        polymarket_markets = _pm.get_bitcoin_markets(5)
        polymarket_sentiment = _pm.get_macro_sentiment_score()
    except Exception:
        pass

    # ── Intelligence Engine V2 — sentient brain ──
    v2_ctx = {}
    try:
        from services.intelligence_engine_v2 import IntelligenceEngineV2
        _v2 = IntelligenceEngineV2()
        v2_ctx = _v2.get_sovereign_context()
    except Exception:
        pass

    return render_template(
        'intelligence_page.html',
        signal=signal, trending=trending, entities=entities,
        narrative_timeline=narrative_timeline, intel_events=intel_events,
        top_articles=top_articles,
        signal_json=_json.dumps(signal, default=str),
        sovereign_ctx=sovereign_ctx,
        sovereign_ctx_json=_json.dumps(sovereign_ctx, default=str),
        polymarket_markets=polymarket_markets,
        polymarket_sentiment=polymarket_sentiment,
        is_commander=is_commander,
        v2_ctx=v2_ctx,
        v2_ctx_json=_json.dumps(v2_ctx, default=str),
    )

@pages_bp.route('/intelligence/scenarios')
def intelligence_scenarios():
    """Intelligence Terminal - Scenarios tab."""
    try:
        return render_template('intelligence_terminal.html', active_tab='scenarios')
    except Exception as e:
        return render_template('intelligence_terminal.html'), 200

@pages_bp.route('/intelligence/alerts')
def intelligence_alerts():
    """Intelligence Terminal - Alerts tab."""
    return render_template('intelligence_terminal.html', active_tab='alerts')

@pages_bp.route('/intelligence/stats')
def intelligence_stats():
    """Intelligence Terminal - Stats tab."""
    return render_template('intelligence_terminal.html', active_tab='stats')

@pages_bp.route('/intelligence/backtest')
def intelligence_backtest():
    """Intelligence Terminal - Backtest tab."""
    return render_template('intelligence_terminal.html', active_tab='backtest')

@pages_bp.route('/intelligence/api')
def intelligence_api():
    """Intelligence Terminal - API tab."""
    return render_template('intelligence_terminal.html', active_tab='api')

@pages_bp.route('/intelligence/legacy-v1')
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

    # ── Sovereign context for premium panels ──────────────────────────────────
    try:
        sovereign_ctx = _load_sovereign_ctx()
        # Recent alerts from history file
        sovereign_alerts = []
        _hist_path = '/home/ultron/protocol_pulse/data/sovereign_context/history.jsonl'
        if os.path.exists(_hist_path):
            import collections as _coll
            _lines = _coll.deque(open(_hist_path), maxlen=20)
            for _ln in reversed(list(_lines)):
                try:
                    _entry = json.loads(_ln.strip())
                    for _a in _entry.get('whale_alerts', []):
                        sovereign_alerts.append(_a)
                except Exception:
                    pass
            sovereign_alerts = sovereign_alerts[:20]
    except Exception as e:
        logging.warning("intelligence_page: sovereign context error: %s", e)
        sovereign_ctx = {}
        sovereign_alerts = []

    # ── Polymarket data ───────────────────────────────────────────────────────
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            'polymarket_service',
            '/home/ultron/protocol_pulse/services/polymarket_service.py'
        )
        _pm = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_pm)
        polymarket_markets = _pm.get_bitcoin_markets(5)
        polymarket_sentiment = _pm.get_macro_sentiment_score()
    except Exception:
        polymarket_markets = []
        polymarket_sentiment = 50

    # ── Commander status ──────────────────────────────────────────────────────
    is_commander = False
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            is_commander = getattr(current_user, 'subscription_tier', '') in ('commander', 'sovereign')
    except Exception:
        pass

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
        # Premium dashboard additions
        sovereign_ctx=sovereign_ctx,
        sovereign_ctx_json=_json.dumps(sovereign_ctx, default=str),
        sovereign_alerts=sovereign_alerts,
        polymarket_markets=polymarket_markets,
        polymarket_markets_json=_json.dumps(polymarket_markets, default=str),
        polymarket_sentiment=polymarket_sentiment,
        is_commander=is_commander,
    )

@pages_bp.route('/sarah-briefing')
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

@pages_bp.route('/subscribe/ghl', methods=['GET', 'POST'])
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
            return redirect(url_for('pages.subscribe_ghl'))
        
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
            return redirect(url_for('pages.index'))
            
    except Exception as e:
        logging.error(f"GHL subscription error: {e}")
        flash('Subscription failed. Please try again.', 'error')
        return redirect(url_for('pages.subscribe_ghl'))

@pages_bp.route('/series/<series_slug>')
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
        return redirect(url_for('pages.media_hub'))
    
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

@pages_bp.route('/health/automation')
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

@pages_bp.route('/launch-console/<int:seq_id>')
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

@pages_bp.route('/launch-console/<int:seq_id>/complete', methods=['POST'])
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

@pages_bp.route('/launch-console/<int:seq_id>/replies')
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

@pages_bp.route('/launch-console/<int:seq_id>/generate-draft', methods=['POST'])
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

@pages_bp.route('/nostr')
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

    pp_npub = os.environ.get("NOSTR_NPUB", "npub1a38uwcec9u4pqd4dutezcfg3ujfapfm90vzzjtkq9cs2u5tws50stujyhm")
    return render_template(
        'nostr.html',
        top_content=top_content,
        relay_status=relay_status,
        pp_npub=pp_npub,
    )

import json

@pages_bp.route('/meetup-map')
def meetup_map():
    """Bitcoin meetup and merchant map"""
    from services.meetup_map_service import meetup_map_service
    
    stats = meetup_map_service.get_global_stats()
    meetups = meetup_map_service.get_bitcoin_meetups()
    
    return render_template('meetup_map.html', stats=stats, meetups=meetups)

@pages_bp.route('/premium')
def premium_page():
    """Premium subscription pricing page"""
    from services.monetization_service import monetization_service

    tiers = monetization_service.get_subscription_tiers()
    return render_template('premium.html', tiers=tiers)

@pages_bp.route('/hub')
@login_required
@premium_hub_required
def premium_hub():
    """Commander Hub v2: configurable widget-based intelligence dashboard.

    Hub v2 is client-side driven — template only receives the user's tier and
    admin flag. All widget data is fetched from /api/hub/intel (5-min cached)
    and layout from /api/hub/layout. See templates/premium_hub.html.
    """
    tier = getattr(current_user, 'subscription_tier', 'free')
    return render_template('premium_hub.html', tier=tier)

@pages_bp.route('/hub/ask', methods=['POST'])
@login_required
def hub_submit_ask():
    """Sovereign Elite: submit monthly research ask (1 per month)."""
    if getattr(current_user, 'subscription_tier', None) != 'sovereign':
        flash('Monthly ask is available for Sovereign Elite only.')
        return redirect(url_for('pages.premium_hub'))
    from datetime import datetime
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = models.PremiumAsk.query.filter(
        models.PremiumAsk.user_id == current_user.id,
        models.PremiumAsk.created_at >= month_start
    ).count()
    if used >= 1:
        flash('You have already used your monthly ask this month. Next resets at month start.')
        return redirect(url_for('pages.premium_hub'))
    question = (request.form.get('question') or '').strip()
    if not question or len(question) < 10:
        flash('Please submit a question of at least 10 characters.')
        return redirect(url_for('pages.premium_hub'))
    try:
        ask = models.PremiumAsk(user_id=current_user.id, question_text=question[:2000], status='pending')
        db.session.add(ask)
        db.session.commit()
        flash('Your monthly ask has been submitted. The team will respond via email or in this hub.')
    except Exception as e:
        logging.warning("PremiumAsk submit failed (table may not exist): %s", e)
        flash('Submit temporarily unavailable. Please try again or contact support.')
    return redirect(url_for('pages.premium_hub'))

@pages_bp.route('/hub/alerts', methods=['POST'])
@login_required
@premium_hub_required
def hub_alerts_preference():
    """Commander+: toggle mega whale email alerts preference."""
    if not getattr(current_user, 'has_commander_tier', lambda: False)():
        flash('Mega whale alerts are for Commander tier and above.')
        return redirect(url_for('pages.premium_hub'))
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
    return redirect(url_for('pages.premium_hub'))

@pages_bp.route('/subscription/success')
@login_required
def subscription_success():
    """Redirect to commander onboarding if eligible, otherwise show success page."""
    tier = getattr(current_user, 'subscription_tier', 'free')
    if tier in ('commander', 'sovereign') and not getattr(current_user, 'onboarding_completed', False):
        return redirect(url_for('auth.commander_onboarding', member=current_user.id, tier=tier))
    session_id = request.args.get('session_id', '')
    return render_template('subscription_success.html', session_id=session_id)

@pages_bp.route('/donate', methods=['GET', 'POST'])
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
            return redirect(url_for('pages.donate'))
    
    return render_template('donate.html')

@pages_bp.route('/donate/thanks')
def donate_thanks():
    """Donation thank you page"""
    return render_template('donate_thanks.html')

@pages_bp.route('/tip/<int:amount>')
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
        return redirect(request.referrer or url_for('pages.index'))
    else:
        flash('Unable to process tip. Please try again.')
        return redirect(request.referrer or url_for('pages.donate'))

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
    {'name': 'Julian Assange', 'role': 'WikiLeaks Founder, Crypto Freedom Advocate', 'era': '2006-present'},
    {'name': 'Whitfield Diffie', 'role': 'Public-key Cryptography Pioneer', 'era': '1976-present'},
    {'name': 'Ralph Merkle', 'role': 'Merkle Trees, Public-key Cryptography', 'era': '1970s-present'},
]

@pages_bp.route('/cypherpunks')
def cypherpunks():
    """Cypherpunks category - honoring the pioneers"""
    articles = models.Article.query.filter(
        models.Article.published == True,
        models.Article.category.ilike('%cypherpunk%')
    ).order_by(models.Article.created_at.desc()).limit(20).all()
    
    return render_template('cypherpunks.html', 
                          articles=articles,
                          pioneers=CYPHERPUNKS)

@pages_bp.route('/guides/cold-storage')
@pages_bp.route('/sovereign-custody')
def cold_storage_guide():
    """Sovereign Custody Manual - Hardware wallet setup guides powered by BTC Sessions"""
    return render_template('guides/cold_storage.html')

@pages_bp.route('/donate/bitcoin')
def donate_bitcoin():
    """Bitcoin donation page with Lightning and on-chain options"""
    return render_template('donate_bitcoin.html')

@pages_bp.route('/og/<og_type>.png')
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

@pages_bp.route('/sentry')
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

@pages_bp.route('/logistics')
def logistics():
    """Infrastructure Index - Transparency disclosure for commercial relationships"""
    try:
        with open('data/referrals.json') as f:
            manifest = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load referrals manifest: {e}")
        manifest = {"exchanges": {}, "onramps": {}, "insurance": {}, "hardware": {}}
    
    return render_template('logistics.html', manifest=manifest, now=datetime.utcnow())

@pages_bp.route('/go/<string:partner_key>')
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
            return redirect(url_for('pages.logistics'))
        
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
        return redirect(url_for('pages.logistics'))

@pages_bp.route('/bitcoin-music')
def bitcoin_music():
    """Bitcoin Music showcase page"""
    return render_template('bitcoin_music.html')

@pages_bp.route('/bitcoin-artists')
def bitcoin_artists():
    """Sovereign Creativity Hub — Bitcoin Artists & Creators"""
    featured = None
    try:
        feat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'featured_artist.json')
        with open(feat_path, 'r') as f:
            featured = type('Featured', (), json.load(f))()
    except Exception:
        pass
    return render_template('bitcoin_artists.html', featured=featured)

@pages_bp.route('/freedom-tech')
def freedom_tech():
    """Freedom Tech destination page"""
    return render_template('freedom_tech.html')

@pages_bp.route('/operative/<slug>')
def operative_profile(slug):
    """Public operative profile page"""
    user = models.User.query.filter_by(operative_slug=slug).first_or_404()
    return render_template('operative_profile.html', operative=user)

@pages_bp.route('/wall')
def bitcoin_wall():
    """Bitcoin Intelligence Wall — ambient display."""
    return render_template('bitcoin_wall.html')

@pages_bp.route("/btc-charts")
def btc_charts_redirect():
    """Legacy alias → /charts."""
    return redirect(url_for('pages.charts'), code=301)

@pages_bp.route("/charts")
def charts():
    """Bitcoin Charts Intelligence Hub."""
    from routes_api import (_fetch_btc_price, _fetch_block_height,
                            _fetch_mempool_stats, _calc_mined_supply)
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

@pages_bp.route('/sponsors')
@pages_bp.route('/advertise')
@pages_bp.route('/media-kit')
def sponsors_page():
    """Media kit and sponsorship landing page."""
    return render_template('sponsors.html')

@pages_bp.route('/disruption-tracker')
@pages_bp.route('/ai-tracker')
@pages_bp.route('/kill-list')
def disruption_tracker():
    """AI Disruption Tracker — the Claude Kill List."""
    return render_template('disruption_tracker.html')

@pages_bp.route('/events')
def events_page():
    """Events hub — BitcoinDay Naples + BTC in DC."""
    return render_template('events.html')

@pages_bp.route("/charts/embed/<chart_id>")
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

@pages_bp.route('/mining')
def mining_hub():
    """Bitcoin Mining Intelligence Hub — live hashrate, ASIC calculator, pool distribution."""
    return render_template('mining_hub.html')

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

@pages_bp.route('/go/meanwhile')
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

@pages_bp.route('/go/rns')
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

@pages_bp.route('/bitcoin-life-insurance')
def bitcoin_life_insurance():
    """Meanwhile Bitcoin Life Insurance landing page."""
    return render_template('bitcoin_life_insurance.html')

@pages_bp.route('/digital-residency')
def digital_residency():
    """RNS.ID Palau Digital Residency landing page."""
    return render_template('digital_residency.html')

@pages_bp.route('/stage')
def stage_page():
    """24/7 autonomous Bitcoin broadcast station."""
    return render_template('stage.html')

def _next_briefing_utc_epoch():
    """Return UTC epoch of next 8am ET briefing."""
    from datetime import datetime, timezone
    import time
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo('America/New_York')
        now = datetime.now(et)
        next_8 = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour >= 8:
            from datetime import timedelta
            next_8 = next_8 + timedelta(days=1)
        return int(next_8.astimezone(timezone.utc).timestamp())
    except Exception:
        return int(time.time()) + 28800


@pages_bp.route('/briefing')
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

@pages_bp.route('/briefing/archive')
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

@pages_bp.route('/schiff')
@pages_bp.route('/brian')
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

@pages_bp.route('/nodes')
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

@pages_bp.route("/terminal")
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
    macro_data    = _term_cached("macro", 300, _fetch_macro)

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

@pages_bp.route('/search')
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

@pages_bp.route('/oracle-live')
def oracle_live():
    return render_template('oracle_live.html')

@pages_bp.route('/oracle')
def oracle_redirect():
    return redirect('/oracle-live', code=301)

@pages_bp.route('/intel')
def intel_redirect():
    return redirect('/intelligence/legacy', code=301)

@pages_bp.route('/briefings')
def briefings_redirect():
    return redirect('/briefing', code=301)

@pages_bp.route('/markets')
def markets_redirect():
    return redirect('/charts', code=301)

@pages_bp.route('/podcast')
def podcast_redirect():
    return redirect('/podcasts', code=301)

@pages_bp.route('/nostr-signal')
def nostr_signal_redirect():
    from flask import redirect
    return redirect('/nostr')

@pages_bp.route('/yield')  
def yield_page():
    return render_template('coming_soon.html', 
        page_title='Yield Intelligence',
        page_desc='Bitcoin yield and income strategies. Coming soon.') if os.path.exists(
        os.path.join(app.template_folder, 'coming_soon.html')) else render_template('base.html')

@pages_bp.route('/network-health')
def network_health():
    from flask import redirect
    return redirect('/live')

@pages_bp.route('/blocks')
def blocks_page():
    from flask import redirect
    return redirect('/live')

@pages_bp.route('/sponsor/dashboard/<token>')
def sponsor_dashboard(token):
    """Client-facing sponsor analytics dashboard. Token-based access, no login."""
    from models import SponsorCampaign
    from services.sponsor_outreach_service import get_campaign_metrics

    campaign = SponsorCampaign.query.filter_by(dashboard_token=token).first()
    if not campaign:
        return "Campaign not found", 404

    metrics = get_campaign_metrics(campaign.id, days_back=30)
    return render_template('sponsor_dashboard.html', campaign=campaign, metrics=metrics, token=token)

@pages_bp.route('/briefs')
def briefs_redirect():
    return redirect(url_for('pages.articles'), 302)

@pages_bp.route('/affiliates')
def affiliates():
    return render_template('affiliates.html')

@pages_bp.route("/video/hybrid-latest")
def video_hybrid_latest():
    import glob, os
    from flask import send_file, abort
    files = sorted(glob.glob("/home/ultron/protocol_pulse/video_pipeline_v4/output/**/*hybrid*.mp4", recursive=True))
    if not files: abort(404)
    return send_file(files[-1], mimetype="video/mp4", as_attachment=False, conditional=True)

@pages_bp.route('/video/v4-latest')
def video_v4_latest():
    import glob, os
    from flask import send_file, abort
    files = sorted(glob.glob('/home/ultron/protocol_pulse/video_pipeline_v4/output/**/*.mp4', recursive=True))
    full = [f for f in files if os.path.getsize(f) > 10_000_000]
    if not full: abort(404)
    return send_file(full[-1], mimetype='video/mp4', as_attachment=False, conditional=True)

@pages_bp.route('/sponsor-deck')
def sponsor_deck_public():
    """Public, token-gated sponsor one-pager. Logs view + alerts admin board."""
    token = (request.args.get('token') or '').strip()
    prospect = None
    deck_id = 'PP-SB-2026'
    prospect_company = None

    if token:
        try:
            prospect = models.SponsorOutreach.query.filter_by(deck_token=token).first()
        except Exception as _q_err:
            logging.warning('sponsor-deck token lookup failed: %s', _q_err)
            prospect = None

        if prospect:
            prospect_company = prospect.company
            deck_id = f'PP-SB-{prospect.id:04d}'
            try:
                ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
                ua = (request.headers.get('User-Agent') or '')[:500]
                ref = (request.headers.get('Referer') or '')[:500]
                # Count prior views for today BEFORE inserting the current one,
                # so autoflush doesn't include it in the count.
                today = datetime.utcnow().date()
                day_start = datetime.combine(today, datetime.min.time())
                existing_today = models.SponsorDeckView.query.filter(
                    models.SponsorDeckView.prospect_id == prospect.id,
                    models.SponsorDeckView.viewed_at >= day_start,
                ).count()

                view = models.SponsorDeckView(
                    prospect_id=prospect.id,
                    deck_token=token,
                    ip=ip,
                    user_agent=ua,
                    referer=ref,
                )
                db.session.add(view)
                db.session.commit()

                if existing_today == 0:
                    try:
                        pbx = models.User.query.filter_by(email='soldtwodragons@gmail.com').first()
                        if pbx:
                            card = models.BoardCard(
                                title=f'Sponsor deck viewed: {prospect.company}',
                                description=(
                                    f'{prospect.company} opened the sponsor brief.\n'
                                    f'IP: {ip or "unknown"}  ·  UA: {ua[:80] or "unknown"}\n'
                                    f'Referer: {ref or "direct"}\n'
                                    f'Follow up while they are warm.'
                                ),
                                column='in_progress',
                                priority='high',
                                tag='marketing',
                                creator_id=pbx.id,
                                position=0,
                            )
                            db.session.add(card)
                            db.session.commit()
                    except Exception as _alert_err:
                        logging.warning('sponsor-deck board alert failed: %s', _alert_err)
            except Exception as _view_err:
                logging.warning('sponsor-deck view log failed: %s', _view_err)
                try:
                    db.session.rollback()
                except Exception:
                    pass

    issued_date = datetime.utcnow().strftime('%Y-%m-%d')
    resp = make_response(render_template(
        'sponsor_deck_public.html',
        deck_id=deck_id,
        issued_date=issued_date,
        prospect_company=prospect_company,
        prospect=prospect,
    ))
    # Private link — don't cache, don't index.
    resp.headers['Cache-Control'] = 'private, no-store'
    resp.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return resp


@pages_bp.route('/video/latest')
def serve_latest_video():
    import os, glob
    output_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'video_pipeline_v3', 'output')
    pattern = os.path.join(output_base, '**', 'pulse_check_*.mp4')
    files = [f for f in glob.glob(pattern, recursive=True) if not any(x in f for x in ['.bgl_', '.intro_', '.music_', '.concat_'])]
    if not files:
        return 'No video available', 404
    latest = sorted(files)[-1]
    dirname = os.path.dirname(latest)
    filename = os.path.basename(latest)
    from flask import send_from_directory
    return send_from_directory(dirname, filename, mimetype='video/mp4')


@pages_bp.route('/.well-known/lnurlp/protocolpulse')
def lnurlp_handler():
    """LNURL-pay descriptor so any Lightning wallet can send to protocolpulse@protocolpulse.io."""
    import json as _j
    from flask import current_app
    body = {
        'tag': 'payRequest',
        'callback': 'https://protocolpulse.io/api/lnurl/pay',
        'maxSendable': 100000000,
        'minSendable': 1000,
        'metadata': _j.dumps([
            ['text/plain', 'Protocol Pulse Bitcoin Intelligence API'],
            ['text/identifier', 'protocolpulse@protocolpulse.io'],
        ]),
        'commentAllowed': 64,
    }
    return current_app.response_class(_j.dumps(body), mimetype='application/json')


@pages_bp.route('/api-access')
def api_access_page():
    """Public pricing page for LSAT-gated endpoints."""
    from services.lsat_service import ENDPOINT_PRICING, LIGHTNING_ADDRESS
    return render_template('api_access.html', pricing=ENDPOINT_PRICING, lightning_address=LIGHTNING_ADDRESS)
