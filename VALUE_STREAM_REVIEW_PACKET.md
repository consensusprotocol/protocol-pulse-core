# Value Stream Review Packet

## File: routes.py (value stream routes + APIs)
```python
# =====================================
# VALUE STREAM - Decentralized Social Aggregator
# =====================================

def _get_value_stream_service():
    """Best-effort import so Value Stream pages still render without optional service module."""
    try:
        from services.value_stream_service import value_stream_service
        return value_stream_service
    except Exception as e:
        logging.warning("value_stream_service unavailable, using DB fallback: %s", e)
        return None


def _infer_platform_from_url(url: str) -> str:
    parsed = urlparse(url or "")
    host = (parsed.netloc or "").lower()
    if "x.com" in host or "twitter.com" in host:
        return "x"
    if "nostr" in host or "primal.net" in host or "damus.io" in host:
        return "nostr"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "reddit.com" in host:
        return "reddit"
    if "stacker.news" in host:
        return "stacker"
    return "web"

@app.route('/value-stream')
def value_stream():
    """Value Stream - Content curated by economic signals"""
    value_stream_service = _get_value_stream_service()
    platform = request.args.get('platform')

    if value_stream_service is not None:
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
    else:
        post_query = models.CuratedPost.query
        if platform:
            post_query = post_query.filter(models.CuratedPost.platform == platform)
        post_objects = post_query.order_by(
            models.CuratedPost.signal_score.desc(),
            models.CuratedPost.submitted_at.desc()
        ).limit(50).all()
        curator_objects = models.ValueCreator.query.order_by(
            models.ValueCreator.curator_score.desc(),
            models.ValueCreator.total_sats_received.desc()
        ).limit(10).all()
    
    return render_template('value_stream.html', 
                          posts=post_objects,
                          curators=curator_objects,
                          selected_platform=platform)

@app.route('/signal-terminal')
def signal_terminal():
    """Signal Terminal - Premium 3-panel value stream interface"""
    value_stream_service = _get_value_stream_service()
    from datetime import datetime, timedelta

    if value_stream_service is not None:
        posts = value_stream_service.get_value_stream_enhanced(limit=50)
        curators = value_stream_service.get_top_curators(limit=10)
        curator_objects = []
        for c in curators:
            curator = models.ValueCreator.query.get(c['id'])
            if curator:
                curator_objects.append(curator)
    else:
        posts = models.CuratedPost.query.order_by(
            models.CuratedPost.signal_score.desc(),
            models.CuratedPost.submitted_at.desc()
        ).limit(50).all()
        curator_objects = models.ValueCreator.query.order_by(
            models.ValueCreator.curator_score.desc(),
            models.ValueCreator.total_sats_received.desc()
        ).limit(10).all()
    
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
    value_stream_service = _get_value_stream_service()
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
    
    if value_stream_service is not None:
        result = value_stream_service.submit_content(url, curator_id, title)
        return jsonify(result)

    existing = models.CuratedPost.query.filter_by(original_url=url).first()
    if existing:
        return jsonify({'success': True, 'post_id': existing.id, 'message': 'already indexed'})

    post = models.CuratedPost(
        platform=_infer_platform_from_url(url),
        original_url=url,
        title=title or url,
        content_preview='queued from fallback ingest',
        curator_id=curator_id,
        total_sats=0,
        zap_count=0,
        signal_score=0,
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'success': True, 'post_id': post.id, 'message': 'content submitted'})

@app.route('/api/value-stream/zap/<int:post_id>', methods=['POST'])
def api_zap_content(post_id):
    """API endpoint for zapping content"""
    value_stream_service = _get_value_stream_service()
    
    data = request.get_json() or {}
    amount = data.get('amount_sats', 1000)
    payment_hash = data.get('payment_hash')
    sender_id = data.get('sender_id')
    
    if value_stream_service is not None:
        result = value_stream_service.process_zap(post_id, sender_id, amount, payment_hash)
        return jsonify(result)

    post = models.CuratedPost.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'error': 'Post not found'}), 404

    post.total_sats = (post.total_sats or 0) + int(amount)
    post.zap_count = (post.zap_count or 0) + 1
    post.calculate_signal_score()
    db.session.add(models.ZapEvent(
        post_id=post_id,
        sender_id=sender_id,
        amount_sats=int(amount),
        payment_hash=payment_hash,
        status='settled',
        source='fallback',
    ))
    db.session.commit()
    return jsonify({'success': True, 'post_id': post_id, 'amount_sats': int(amount)})

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
    value_stream_service = _get_value_stream_service()
    if value_stream_service is not None:
        curators = value_stream_service.get_top_curators(limit=20)
        return jsonify({'success': True, 'curators': curators})

    curators = models.ValueCreator.query.order_by(
        models.ValueCreator.curator_score.desc(),
```

## File: templates/value_stream.html
```html
{% extends "base.html" %}

{% block title %}Value Stream - Protocol Pulse{% endblock %}

{% block extra_head %}
<style>
    .value-stream-hero {
        background: linear-gradient(135deg, #0a0a12 0%, #1a0a2e 50%, #0a0a12 100%);
        padding: 60px 0;
        border-bottom: 1px solid rgba(138, 43, 226, 0.3);
    }
    
    .stream-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.5rem;
        color: #f7931a;
        text-shadow: 0 0 30px rgba(247, 147, 26, 0.5);
    }
    
    .stream-subtitle {
        color: rgba(255,255,255,0.7);
        font-size: 1.1rem;
        max-width: 600px;
        margin: 0 auto;
    }
    
    .platform-filters {
        display: flex;
        gap: 12px;
        justify-content: center;
        flex-wrap: wrap;
        margin: 30px 0;
    }
    
    .platform-btn {
        background: rgba(138, 43, 226, 0.2);
        border: 1px solid rgba(138, 43, 226, 0.4);
        color: #fff;
        padding: 8px 20px;
        border-radius: 20px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }
    
    .platform-btn:hover, .platform-btn.active {
        background: rgba(247, 147, 26, 0.3);
        border-color: #f7931a;
        color: #f7931a;
    }
    
    .content-card {
        background: rgba(20, 20, 35, 0.9);
        border: 1px solid rgba(138, 43, 226, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .content-card:hover {
        border-color: #f7931a;
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(247, 147, 26, 0.15);
    }
    
    .content-card.featured {
        border-color: #f7931a;
        background: linear-gradient(135deg, rgba(247, 147, 26, 0.1), rgba(20, 20, 35, 0.9));
    }
    
    .platform-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .platform-twitter { background: rgba(29, 161, 242, 0.2); color: #1da1f2; }
    .platform-youtube { background: rgba(255, 0, 0, 0.2); color: #ff0000; }
    .platform-reddit { background: rgba(255, 69, 0, 0.2); color: #ff4500; }
    .platform-nostr { background: rgba(138, 43, 226, 0.2); color: #8a2be2; }
    .platform-stacker_news { background: rgba(247, 147, 26, 0.2); color: #f7931a; }
    
    .signal-score {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        color: #00ff88;
        text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
    }
    
    .sats-count {
        color: #f7931a;
        font-weight: 600;
    }
    
    .zap-count {
        color: rgba(255,255,255,0.6);
    }
    
    .curator-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        background: rgba(138, 43, 226, 0.2);
        border-radius: 20px;
        font-size: 0.85rem;
    }
    
    .curator-badge.verified::after {
        content: "✓";
        color: #00ff88;
        margin-left: 4px;
    }
    
    .zap-btn {
        background: linear-gradient(135deg, #f7931a, #ff6b00);
        border: none;
        color: #000;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.3s ease;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .zap-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 20px rgba(247, 147, 26, 0.4);
    }
    
    .curator-leaderboard {
        background: rgba(20, 20, 35, 0.9);
        border: 1px solid rgba(138, 43, 226, 0.3);
        border-radius: 12px;
        padding: 20px;
    }
    
    .curator-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid rgba(138, 43, 226, 0.2);
    }
    
    .curator-row:last-child {
        border-bottom: none;
    }
    
    .curator-rank {
        width: 30px;
        font-family: 'JetBrains Mono', monospace;
        color: #f7931a;
    }
    
    .extension-promo {
        background: linear-gradient(135deg, rgba(247, 147, 26, 0.2), rgba(138, 43, 226, 0.2));
        border: 1px solid rgba(247, 147, 26, 0.4);
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        margin: 40px 0;
    }
    
    .extension-btn {
        background: linear-gradient(135deg, #8a2be2, #6b1fa9);
        border: none;
        color: #fff;
        padding: 14px 32px;
        border-radius: 8px;
        font-weight: 700;
        cursor: pointer;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .extension-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 20px rgba(138, 43, 226, 0.4);
    }
    
    .how-it-works {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 24px;
        margin: 40px 0;
    }
    
    .how-card {
        background: rgba(20, 20, 35, 0.8);
        border: 1px solid rgba(138, 43, 226, 0.3);
        border-radius: 12px;
        padding: 24px;
        text-align: center;
    }
    
    .how-icon {
        font-size: 2.5rem;
        margin-bottom: 16px;
    }
    
    .empty-stream {
        text-align: center;
        padding: 60px;
        color: rgba(255,255,255,0.5);
    }
    
    .submit-form {
        background: rgba(20, 20, 35, 0.9);
        border: 1px solid rgba(138, 43, 226, 0.3);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 30px;
    }
    
    .submit-input {
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(138, 43, 226, 0.4);
        color: #fff;
        padding: 12px 16px;
        border-radius: 8px;
        width: 100%;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .submit-input:focus {
        outline: none;
        border-color: #f7931a;
    }
</style>
{% endblock %}

{% block content %}
<div class="value-stream-hero text-center">
    <div class="container">
        <h1 class="stream-title">
            <i class="fas fa-bolt"></i> VALUE STREAM
        </h1>
        <p class="stream-subtitle">
            Decentralized content curation powered by sats. The best content rises based on 
            real economic signals, not engagement farming. Zap to signal value.
        </p>
        
        <div class="platform-filters">
            <button class="platform-btn active" data-platform="all">ALL PLATFORMS</button>
            <button class="platform-btn" data-platform="twitter">X/TWITTER</button>
            <button class="platform-btn" data-platform="youtube">YOUTUBE</button>
            <button class="platform-btn" data-platform="nostr">NOSTR</button>
            <button class="platform-btn" data-platform="reddit">REDDIT</button>
            <button class="platform-btn" data-platform="stacker_news">STACKER NEWS</button>
        </div>
    </div>
</div>

<div class="container py-5">
    <div class="row">
        <div class="col-lg-8">
            <div class="submit-form">
                <h5 class="text-white mb-3"><i class="fas fa-plus-circle text-warning"></i> Curate Content</h5>
                <form id="submit-content-form" class="d-flex gap-3">
                    <input type="url" class="submit-input flex-grow-1" id="content-url" 
                           placeholder="Paste URL from any platform..." required>
                    <button type="submit" class="zap-btn">
                        <i class="fas fa-paper-plane"></i> SUBMIT
                    </button>
                </form>
                <small class="text-muted mt-2 d-block">Share valuable content and earn curator splits when others zap</small>
            </div>
            
            <div id="value-stream-feed">
                {% if posts %}
                    {% for post in posts %}
                    <div class="content-card {% if post.is_featured %}featured{% endif %}">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div>
                                <span class="platform-badge platform-{{ post.platform }}">
                                    {{ post.platform }}
                                </span>
                                {% if post.is_featured %}
                                <span class="badge bg-warning text-dark ms-2">FEATURED</span>
                                {% endif %}
                            </div>
                            <div class="signal-score" title="Signal Score">
                                {{ "%.1f"|format(post.signal_score) }}
                            </div>
                        </div>
                        
                        <h5 class="text-white mb-2">
                            <a href="{{ post.original_url }}" target="_blank" class="text-decoration-none text-white">
                                {{ post.title or 'Untitled Content' }}
                                <i class="fas fa-external-link-alt fa-xs ms-2 text-muted"></i>
                            </a>
                        </h5>
                        
                        {% if post.content_preview %}
                        <p class="text-muted mb-3">{{ post.content_preview[:200] }}...</p>
                        {% endif %}
                        
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            <div class="d-flex gap-4">
                                <span class="sats-count">
                                    <i class="fas fa-bolt"></i> {{ "{:,}".format(post.total_sats) }} sats
                                </span>
                                <span class="zap-count">
                                    {{ post.zap_count }} zaps
                                </span>
                            </div>
                            
                            <div class="d-flex align-items-center gap-3">
                                {% if post.curator %}
                                <div class="curator-badge {% if post.curator.verified %}verified{% endif %}">
                                    <i class="fas fa-user-check"></i>
                                    {{ post.curator.display_name }}
                                </div>
                                {% endif %}
                                
                                <button class="zap-btn zap-content-btn" data-post-id="{{ post.id }}">
                                    <i class="fas fa-bolt"></i> ZAP
                                </button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-stream">
                        <i class="fas fa-stream fa-3x mb-3"></i>
                        <h4>No Curated Content Yet</h4>
                        <p>Be the first to curate valuable content and earn sats when others zap!</p>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <div class="col-lg-4">
            <div class="extension-promo mb-4">
                <h4 class="text-white mb-3">
                    <i class="fas fa-puzzle-piece"></i> Browser Extension
                </h4>
                <p class="text-muted mb-4">
                    Zap content anywhere on the web. Curate from any site. 
                    Connect your Lightning wallet.
                </p>
                <a href="/extension" class="extension-btn text-decoration-none">
                    <i class="fas fa-download me-2"></i> GET EXTENSION
                </a>
            </div>
            
            <div class="curator-leaderboard">
                <h5 class="text-white mb-3">
                    <i class="fas fa-trophy text-warning"></i> Top Curators
                </h5>
                
                {% if curators %}
                    {% for curator in curators[:10] %}
                    <div class="curator-row">
                        <div class="d-flex align-items-center gap-3">
                            <span class="curator-rank">#{{ loop.index }}</span>
                            <div>
                                <div class="text-white">
                                    {{ curator.display_name }}
                                    {% if curator.verified %}
                                    <i class="fas fa-check-circle text-success fa-xs"></i>
                                    {% endif %}
                                </div>
                                <small class="text-muted">Score: {{ curator.curator_score }}</small>
                            </div>
                        </div>
                        <div class="text-end">
                            <div class="sats-count small">{{ "{:,}".format(curator.total_sats_received) }}</div>
                            <small class="text-muted">{{ curator.total_zaps }} zaps</small>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="text-muted text-center py-3">No curators yet</p>
                {% endif %}
            </div>
            
            <div class="how-it-works mt-4">
                <div class="how-card">
                    <div class="how-icon">🔗</div>
                    <h6 class="text-white">1. Curate</h6>
                    <p class="text-muted small mb-0">Share valuable content from any platform</p>
                </div>
                <div class="how-card">
                    <div class="how-icon">⚡</div>
                    <h6 class="text-white">2. Zap</h6>
                    <p class="text-muted small mb-0">Send sats to signal content value</p>
                </div>
                <div class="how-card">
                    <div class="how-icon">📈</div>
                    <h6 class="text-white">3. Rise</h6>
                    <p class="text-muted small mb-0">Best content surfaces via economic signal</p>
                </div>
                <div class="how-card">
                    <div class="how-icon">💰</div>
                    <h6 class="text-white">4. Earn</h6>
                    <p class="text-muted small mb-0">Curators get 10% of zaps to content they share</p>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.querySelectorAll('.platform-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        const platform = this.dataset.platform;
        window.location.href = platform === 'all' ? '/value-stream' : `/value-stream?platform=${platform}`;
    });
});

document.getElementById('submit-content-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const url = document.getElementById('content-url').value;
    
    try {
        const response = await fetch('/api/value-stream/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url: url})
        });
        const data = await response.json();
        
        if (data.success) {
            alert('Content curated successfully!');
            window.location.reload();
        } else {
            alert(data.error || 'Failed to curate content');
        }
    } catch (err) {
        alert('Error submitting content');
    }
});

document.querySelectorAll('.zap-content-btn').forEach(btn => {
    btn.addEventListener('click', async function() {
        const postId = this.dataset.postId;
        
        if (typeof webln !== 'undefined') {
            try {
                await webln.enable();
                const response = await fetch(`/api/value-stream/invoice/${postId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({amount_sats: 1000})
                });
                const data = await response.json();
                
                if (data.invoice) {
                    const result = await webln.sendPayment(data.invoice);
                    alert('Zap sent! Thank you for signaling value.');
                    window.location.reload();
                }
            } catch (err) {
                alert('WebLN payment failed: ' + err.message);
            }
        } else {
            alert('Please install a WebLN-compatible wallet extension (Alby, etc.)');
        }
    });
});
</script>
{% endblock %}
```

## File: models.py (value stream models)
```python
# =====================================
# VALUE STREAM MODELS
# =====================================

class ValueCreator(db.Model):
    __tablename__ = 'value_creator'
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)
    nostr_pubkey = db.Column(db.String(128), unique=True)
    lightning_address = db.Column(db.String(200))
    nip05 = db.Column(db.String(200))
    twitter_handle = db.Column(db.String(50))
    youtube_channel_id = db.Column(db.String(50))
    reddit_username = db.Column(db.String(50))
    stacker_news_username = db.Column(db.String(50))
    profile_image = db.Column(db.String(500))
    bio = db.Column(db.Text)
    total_sats_received = db.Column(db.BigInteger, default=0)
    total_zaps = db.Column(db.Integer, default=0)
    curator_score = db.Column(db.Float, default=0)
    verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
                                     foreign_keys='CuratedPost.creator_id')
    submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
                                       foreign_keys='CuratedPost.curator_id')

class CuratedPost(db.Model):
    __tablename__ = 'curated_post'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(30), nullable=False)
    original_url = db.Column(db.String(1000), nullable=False, unique=True)
    original_id = db.Column(db.String(200))
    title = db.Column(db.String(500))
    content_preview = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(500))
    creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
    curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
    total_sats = db.Column(db.BigInteger, default=0)
    zap_count = db.Column(db.Integer, default=0)
    boost_sats = db.Column(db.BigInteger, default=0)
    signal_score = db.Column(db.Float, default=0)
    decay_factor = db.Column(db.Float, default=1.0)
    is_verified = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_zap_at = db.Column(db.DateTime)
    
    def calculate_signal_score(self):
        age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
        time_decay = max(0.1, 1 - (age_hours / 168))
        raw_score = (self.total_sats * 0.001) + (self.zap_count * 10)
        self.signal_score = raw_score * time_decay * self.decay_factor
        return self.signal_score

class ZapEvent(db.Model):
    __tablename__ = 'zap_event'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
    amount_sats = db.Column(db.BigInteger, nullable=False)
    creator_share = db.Column(db.BigInteger)
    curator_share = db.Column(db.BigInteger)
    platform_share = db.Column(db.BigInteger)
    payment_hash = db.Column(db.String(128))
    bolt11_invoice = db.Column(db.Text)
    preimage = db.Column(db.String(128))
    status = db.Column(db.String(20), default='pending')
    source = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime)
    post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))

class TrustEdge(db.Model):
    __tablename__ = 'trust_edge'
    id = db.Column(db.Integer, primary_key=True)
    truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
    trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
    trust_weight = db.Column(db.Float, default=1.0)
    total_sats_via = db.Column(db.BigInteger, default=0)
    successful_curations = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)

class BoostStake(db.Model):
    __tablename__ = 'boost_stake'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
    staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
    amount_sats = db.Column(db.BigInteger, nullable=False)
    boost_multiplier = db.Column(db.Float, default=1.0)
    expires_at = db.Column(db.DateTime)
    refunded = db.Column(db.Boolean, default=False)
    refund_amount = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))

class ExtensionSession(db.Model):
    __tablename__ = 'extension_session'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
    session_token = db.Column(db.String(128), unique=True, nullable=False)
    browser_fingerprint = db.Column(db.String(128))
    user_agent = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
```
