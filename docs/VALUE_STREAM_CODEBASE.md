# Value Stream — Full Codebase

This document contains the **entire codebase** for the Protocol Pulse **Value Stream** page and APIs. Share it with other LLMs to evolve it into a world-class, high-value use case.

**What it is:** A decentralized content curation feed powered by sats (Bitcoin). Users curate URLs from any platform; others "zap" (send sats) to signal value. Content rises by economic signal; curators earn a split. Integrates with Lightning (LNURL), WebLN, and a browser extension.

**Stack:** Flask (Python), SQLAlchemy, Jinja2, vanilla JS. Frontend extends `base.html` (site chrome).

---

## 1. Database models (SQLAlchemy)

File: `models.py` (excerpt). Requires Flask app with `db = SQLAlchemy(app)` and `datetime`.

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
```

---

## 2. Service layer

File: `services/value_stream_service.py`

```python
"""
Value Stream — curated content feed and creator/curator APIs.
Powers /value-stream, /signal-terminal, and value-stream API endpoints.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _db():
    from app import db
    return db


def _models():
    import models
    return models


def get_value_stream(limit=50, platform=None):
    """Return list of post dicts with at least 'id' for CuratedPost.query.get."""
    models = _models()
    q = models.CuratedPost.query.order_by(models.CuratedPost.signal_score.desc().nullslast())
    if platform:
        q = q.filter(models.CuratedPost.platform == platform)
    posts = q.limit(limit).all()
    return [{"id": p.id} for p in posts]


def get_top_curators(limit=10):
    """Return list of curator dicts with at least 'id' for ValueCreator.query.get."""
    models = _models()
    curators = (
        models.ValueCreator.query
        .order_by(models.ValueCreator.curator_score.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [{"id": c.id} for c in curators]


def get_value_stream_enhanced(limit=50):
    """Enhanced feed for Signal Terminal: list of dicts with post + curator info."""
    models = _models()
    posts = (
        models.CuratedPost.query
        .order_by(models.CuratedPost.signal_score.desc().nullslast())
        .limit(limit)
        .all()
    )
    out = []
    for p in posts:
        c = p.curator if hasattr(p, "curator") else None
        out.append({
            "id": p.id,
            "platform": p.platform or "",
            "title": p.title or "Untitled",
            "content_preview": (p.content_preview or "")[:200],
            "original_url": p.original_url or "",
            "total_sats": p.total_sats or 0,
            "zap_count": p.zap_count or 0,
            "signal_score": round(p.signal_score or 0, 2),
            "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
            "curator_name": c.display_name if c else "Anonymous",
            "curator_id": c.id if c else None,
        })
    return out


def submit_content(url, curator_id, title):
    """Submit a new curated post. Returns {success, id} or {success: False, error}."""
    db = _db()
    models = _models()
    try:
        existing = models.CuratedPost.query.filter_by(original_url=url).first()
        if existing:
            return {"success": True, "id": existing.id, "existing": True}
        post = models.CuratedPost(
            platform="web",
            original_url=url,
            title=(title or "")[:500],
            curator_id=curator_id,
        )
        post.calculate_signal_score()
        db.session.add(post)
        db.session.commit()
        return {"success": True, "id": post.id}
    except Exception as e:
        logger.exception("submit_content failed")
        db.session.rollback()
        return {"success": False, "error": str(e)}


def process_zap(post_id, sender_id, amount, payment_hash):
    """Record a zap and update post totals. Returns {success, ...}."""
    db = _db()
    models = _models()
    try:
        post = models.CuratedPost.query.get(post_id)
        if not post:
            return {"success": False, "error": "Post not found"}
        zap = models.ZapEvent(
            post_id=post_id,
            sender_id=sender_id,
            amount_sats=amount,
            payment_hash=payment_hash or "",
            status="settled",
        )
        db.session.add(zap)
        post.total_sats = (post.total_sats or 0) + amount
        post.zap_count = (post.zap_count or 0) + 1
        post.last_zap_at = datetime.utcnow()
        post.calculate_signal_score()
        if post.curator_id:
            curator = models.ValueCreator.query.get(post.curator_id)
            if curator:
                curator.total_sats_received = (curator.total_sats_received or 0) + amount
                curator.total_zaps = (curator.total_zaps or 0) + 1
        db.session.commit()
        return {"success": True, "post_id": post_id, "amount_sats": amount}
    except Exception as e:
        logger.exception("process_zap failed")
        db.session.rollback()
        return {"success": False, "error": str(e)}


def register_creator(display_name, nostr_pubkey=None, lightning_address=None, nip05=None):
    """Register a new value creator. Returns {success, id} or {success: False, error}."""
    db = _db()
    models = _models()
    try:
        existing = models.ValueCreator.query.filter_by(display_name=display_name).first()
        if existing:
            return {"success": True, "id": existing.id, "existing": True}
        creator = models.ValueCreator(
            display_name=display_name[:100],
            nostr_pubkey=nostr_pubkey[:128] if nostr_pubkey else None,
            lightning_address=lightning_address[:200] if lightning_address else None,
            nip05=nip05[:200] if nip05 else None,
        )
        db.session.add(creator)
        db.session.commit()
        return {"success": True, "id": creator.id}
    except Exception as e:
        logger.exception("register_creator failed")
        db.session.rollback()
        return {"success": False, "error": str(e)}


class ValueStreamService:
    get_value_stream = staticmethod(get_value_stream)
    get_top_curators = staticmethod(get_top_curators)
    get_value_stream_enhanced = staticmethod(get_value_stream_enhanced)
    submit_content = staticmethod(submit_content)
    process_zap = staticmethod(process_zap)
    register_creator = staticmethod(register_creator)


value_stream_service = ValueStreamService()
```

---

## 3. Routes (Flask)

File: `routes.py` (value-stream section). Assumes `app`, `db`, `models`, `current_user`, `jsonify`, `request`, `render_template`, `Response`, `logging` are in scope.

```python
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
```

---

## 4. Template (Jinja2 + HTML + CSS + JS)

File: `templates/value_stream.html`. Extends `base.html` (provides nav, footer, `{% block title %}`, `{% block extra_head %}`, `{% block content %}`).

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

    .sats-count { color: #f7931a; font-weight: 600; }
    .zap-count { color: rgba(255,255,255,0.6); }

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

    .curator-row:last-child { border-bottom: none; }
    .curator-rank { width: 30px; font-family: 'JetBrains Mono', monospace; color: #f7931a; }

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

    .how-icon { font-size: 2.5rem; margin-bottom: 16px; }
    .empty-stream { text-align: center; padding: 60px; color: rgba(255,255,255,0.5); }

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

---

## 5. API summary

| Endpoint | Method | Purpose |
|----------|--------|--------|
| `/value-stream` | GET | Page: feed + curate form + leaderboard. Query: `?platform=twitter` etc. |
| `/api/value-stream/submit` | POST | Body: `{url, title?}`. Submit a URL; returns `{success, id}`. |
| `/api/value-stream/zap/<post_id>` | POST | Body: `{amount_sats, payment_hash?, sender_id?}`. Record a zap. |
| `/api/value-stream/invoice/<post_id>` | POST | Body: `{amount_sats}`. Get LNURL/Lightning invoice for zapping. |
| `/api/value-stream/curators` | GET | Top curators (for leaderboard). |
| `/api/value-stream/register` | POST | Body: `{display_name, nostr_pubkey?, lightning_address?, nip05?}`. Register creator. |

---

## 6. Dependencies

- Flask, Flask-SQLAlchemy, Flask-Login (for `current_user` on submit).
- Frontend: Bootstrap 5 (grid, utilities), Font Awesome (icons). Base template provides layout and nav.
- Optional: WebLN in browser for “Zap” (e.g. Alby). LNURL invoice creation uses `requests` to LNURL-p endpoint.

---

## 7. Possible directions for “world-class” improvements

- **Real Lightning flows:** LNURL-auth, hold invoices, keysend, proper split (creator/curator/platform) and payouts.
- **Trust & identity:** Nostr pubkey / NIP-05, verification, trust graph (TrustEdge), anti-sybil.
- **Discovery & ranking:** Better signal_score (velocity, recency, diversity), trending, personalization.
- **UX:** Inline zap amounts, zap history, real-time updates (SSE/WebSocket), mobile-friendly layout.
- **Moderation & safety:** URL validation, spam/abuse detection, reporting, optional allowlists.
- **Extension:** Deeper extension integration (zap from any page, one-click curate).
- **Analytics:** Curator stats, content performance, sats flow dashboards.

Use this codebase as the single source of truth when proposing or implementing changes.
