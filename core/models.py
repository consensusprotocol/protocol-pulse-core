import json
from datetime import datetime, timedelta
import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db  # This stays here; we will fix the 'loop' in app.py

# =====================================
# USER & OPERATIVE MODELS
# =====================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    newsletter_subscribed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    operative_rank = db.Column(db.Integer, default=1)
    drill_completions = db.Column(db.Integer, default=0)
    brief_clicks = db.Column(db.Integer, default=0)
    operative_slug = db.Column(db.String(100), unique=True)
    crm_synced_at = db.Column(db.DateTime)
    last_drill_at = db.Column(db.DateTime)
    last_brief_at = db.Column(db.DateTime)
    
    # Premium subscription (free | operator | commander | sovereign)
    subscription_tier = db.Column(db.String(30), default='free')
    stripe_customer_id = db.Column(db.String(120))
    stripe_subscription_id = db.Column(db.String(120))
    subscription_expires_at = db.Column(db.DateTime)
    # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
    mega_whale_email_alerts = db.Column(db.Boolean, default=False)
    
    # --- Auth Methods ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Operative Logic ---
    def get_rank_name(self):
        if self.operative_rank >= 3:
            return 'SOVEREIGN ELITE'
        elif self.operative_rank >= 2:
            return 'OPERATIVE'
        return 'RECRUIT'
    
    def check_rank_progression(self):
        if self.drill_completions >= 5 and self.brief_clicks >= 10:
            self.operative_rank = 3
        elif self.drill_completions >= 1:
            self.operative_rank = 2
        else:
            self.operative_rank = 1
    
    def generate_operative_slug(self):
        import hashlib
        import time
        if not self.operative_slug:
            base = self.username.lower().replace(' ', '-')[:20]
            unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
            self.operative_slug = f"{base}-{unique_hash}"
        return self.operative_slug
    
    def can_increment_drill(self):
        if not self.last_drill_at:
            return True
        cooldown = datetime.utcnow() - self.last_drill_at
        return cooldown.total_seconds() >= 300
    
    def can_increment_brief(self):
        if not self.last_brief_at:
            return True
        cooldown = datetime.utcnow() - self.last_brief_at
        return cooldown.total_seconds() >= 60
    
    def has_premium(self):
        """True if user has any paid tier (operator, commander, sovereign)."""
        tier = getattr(self, 'subscription_tier', None)
        return tier and tier != 'free'

    def has_commander_tier(self):
        """True if user has $99/mo Commander (or higher) tier."""
        tier = getattr(self, 'subscription_tier', None)
        return tier in ('commander', 'sovereign')

# =====================================
# CONTENT & INTELLIGENCE MODELS
# =====================================

class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    author = db.Column(db.String(100), default="Protocol Pulse AI")
    category = db.Column(db.String(50), default="Web3")
    tags = db.Column(db.String(500))
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))
    featured = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
    premium_tier = db.Column(db.String(30), default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    substack_url = db.Column(db.String(500))
    published_at = db.Column(db.DateTime, nullable=True)
    header_image_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    image_status = db.Column(db.String(30), default="ok")
    image_phash = db.Column(db.String(64))
    slug = db.Column(db.String(300), unique=True, index=True)
    read_count = db.Column(db.Integer, default=0)
    fact_check_passed = db.Column(db.Boolean)
    grok_review_score = db.Column(db.Float)
    gemini_review_score = db.Column(db.Float)
    quality_tier = db.Column(db.String(30))
    content_hash = db.Column(db.String(64))
    screenshot_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    # ── SESSION 12: Sentiment Intelligence Engine ─────────────────────────────
    sentiment = db.Column(db.String(20))          # bullish | bearish | neutral
    sentiment_confidence = db.Column(db.Float)    # 0.0–1.0 (adjusted for source trust)
    narrative_label = db.Column(db.String(80))    # from NARRATIVES taxonomy
    importance_score = db.Column(db.Integer, default=50)  # 1–100
    sentiment_dimensions = db.Column(db.Text)     # JSON: target_dimension, key_signal, source_trust
    market_impact_magnitude = db.Column(db.Float) # 1.0–10.0
    sentiment_at = db.Column(db.DateTime)         # when last classified

    def resolve_cover_image(self):
        """Law 1: cover_image_url is the single source of truth for images."""
        url = (self.cover_image_url or "").strip()
        if url and url.startswith("http"):
            return url
        url = (self.header_image_url or "").strip()
        if url and url.startswith("http"):
            return url
        return "/static/images/default-header.png"

class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    host = db.Column(db.String(100))
    episode_number = db.Column(db.Integer)
    duration = db.Column(db.String(20))
    audio_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    featured = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default="Web3")
    rss_source = db.Column(db.String(100))

class PodcastEpisode(db.Model):
    """SESSION 16 — CypherPunk'd podcast episodes."""
    __tablename__ = 'podcast_episodes'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    episode_number = db.Column(db.Integer)
    guest_name = db.Column(db.String(200))
    guest_bio = db.Column(db.Text)
    guest_image_url = db.Column(db.String(500))
    youtube_url = db.Column(db.String(500))
    audio_url = db.Column(db.String(500))
    duration = db.Column(db.String(20))  # "1:23:45"
    published_at = db.Column(db.DateTime)
    show_notes = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON array
    featured = db.Column(db.Boolean, default=False)
    thumbnail_url = db.Column(db.String(500))

    @property
    def tags_list(self):
        import json
        try:
            return json.loads(self.tags or '[]')
        except Exception:
            return []

    @property
    def youtube_embed_url(self):
        """Convert watch URL to embed URL."""
        if not self.youtube_url:
            return None
        import re
        m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', self.youtube_url)
        if m:
            return f"https://www.youtube.com/embed/{m.group(1)}"
        m2 = re.search(r'youtu\.be/([A-Za-z0-9_-]{11})', self.youtube_url)
        if m2:
            return f"https://www.youtube.com/embed/{m2.group(1)}"
        return None


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


class AffiliateProduct(db.Model):
    """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
    __tablename__ = 'affiliate_product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
    product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
    affiliate_url = db.Column(db.String(500))
    category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
    short_description = db.Column(db.String(500))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AffiliateProductClick(db.Model):
    """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
    __tablename__ = 'affiliate_product_click'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
    link_type = db.Column(db.String(50))  # amazon, trezor, etc.
    page_path = db.Column(db.String(500))
    session_id = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =====================================
# AUTOMATION & LOGISTICS
# =====================================

class AutomationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    error = db.Column(db.String(500))

class LaunchSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer)
    content_type = db.Column(db.String(50))
    primary_post_copy = db.Column(db.Text)
    thread_replies = db.Column(db.Text)
    quote_variants = db.Column(db.Text)
    reply_drafts = db.Column(db.Text)
    hashtags = db.Column(db.String(500))
    posting_time = db.Column(db.Time)
    velocity_prediction = db.Column(db.Float)
    first_reply_link = db.Column(db.String(500))
    call_to_action = db.Column(db.String(300))
    status = db.Column(db.String(50), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    tweet_id = db.Column(db.String(100))
    actual_velocity_score = db.Column(db.Float)
    replies_first_5min = db.Column(db.Integer, default=0)
    total_engagement = db.Column(db.Integer, default=0)
    reached_for_you = db.Column(db.Boolean, default=False)
    dispatch_window = db.Column(db.String(20))
    dispatch_timezone = db.Column(db.String(50), default='America/New_York')
    persona_debate = db.Column(db.Text)
    is_autonomous = db.Column(db.Boolean, default=False)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    ground_truth = db.Column(db.Text)
    target_segment = db.Column(db.String(100))
    generated_by = db.Column(db.String(50))
    nostr_event_id = db.Column(db.String(100))
    x_tweet_id = db.Column(db.String(100))
    is_approved = db.Column(db.Boolean, default=False)
    is_posted = db.Column(db.Boolean, default=False)

class TargetAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(50))
    source_url = db.Column(db.String(500))
    source_account = db.Column(db.String(100))
    content_snippet = db.Column(db.Text)
    priority = db.Column(db.Integer, default=2)
    strategy_suggested = db.Column(db.String(100))
    draft_replies = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

class NostrEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100))
    content_type = db.Column(db.String(50))
    content_id = db.Column(db.Integer)
    relays_success = db.Column(db.Text)
    relays_failed = db.Column(db.Text)
    zaps_received = db.Column(db.Integer, default=0)
    zaps_amount_sats = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReplySquadMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(150))
    category = db.Column(db.String(100))
    priority = db.Column(db.Integer, default=2)
    reciprocal_engagements = db.Column(db.Integer, default=0)
    last_engagement = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =====================================
# BITCOIN NETWORK & DONATIONS
# =====================================

class WhaleTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txid = db.Column(db.String(100), unique=True, nullable=False)
    btc_amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float)
    fee_sats = db.Column(db.Integer)
    block_height = db.Column(db.Integer)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_mega = db.Column(db.Boolean, default=False)


class ContactSubmission(db.Model):
    """Contact form submissions (stored for admin; optional email notification)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)


class PremiumAsk(db.Model):
    """Sovereign Elite monthly ask: one research/question per month, answered by team."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending | answered
    answer_text = db.Column(db.Text)
    answer_url = db.Column(db.String(500))  # optional link to brief or doc
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime)
    user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))


class BitcoinDonation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100))
    amount_sats = db.Column(db.Integer)
    amount_usd = db.Column(db.Float)
    donor_email = db.Column(db.String(200))
    donor_name = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)

# =====================================
# ANALYTICS & PERFORMANCE
# =====================================

class EngagementEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    content_type = db.Column(db.String(50))
    content_id = db.Column(db.Integer)
    source_platform = db.Column(db.String(50))
    source_url = db.Column(db.String(500))
    persona = db.Column(db.String(50))
    strategy = db.Column(db.String(100))
    minutes_after_post = db.Column(db.Float)
    is_30min_window = db.Column(db.Boolean, default=False)
    grok_score_contribution = db.Column(db.Integer, default=0)
    user_agent = db.Column(db.String(300))
    referrer = db.Column(db.String(500))
    ip_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContentPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(50), nullable=False)
    content_id = db.Column(db.Integer, nullable=False)
    content_title = db.Column(db.String(300))
    total_views = db.Column(db.Integer, default=0)
    total_clicks = db.Column(db.Integer, default=0)
    total_replies = db.Column(db.Integer, default=0)
    total_retweets = db.Column(db.Integer, default=0)
    total_quotes = db.Column(db.Integer, default=0)
    total_likes = db.Column(db.Integer, default=0)
    profile_visits = db.Column(db.Integer, default=0)
    replies_0_5min = db.Column(db.Integer, default=0)
    replies_5_15min = db.Column(db.Integer, default=0)
    replies_15_30min = db.Column(db.Integer, default=0)
    replies_30plus_min = db.Column(db.Integer, default=0)
    velocity_score = db.Column(db.Float, default=0)
    grok_score_total = db.Column(db.Integer, default=0)
    reached_for_you = db.Column(db.Boolean, default=False)
    peak_velocity_minute = db.Column(db.Integer)
    alex_engagements = db.Column(db.Integer, default=0)
    sarah_engagements = db.Column(db.Integer, default=0)
    best_performing_strategy = db.Column(db.String(100))
    best_performing_time = db.Column(db.String(20))
    published_at = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnalyticsSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_type = db.Column(db.String(20), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    total_posts = db.Column(db.Integer, default=0)
    total_impressions = db.Column(db.Integer, default=0)
    total_engagements = db.Column(db.Integer, default=0)
    total_profile_visits = db.Column(db.Integer, default=0)
    total_followers_gained = db.Column(db.Integer, default=0)
    avg_velocity_score = db.Column(db.Float, default=0)
    avg_grok_score = db.Column(db.Float, default=0)
    for_you_reach_rate = db.Column(db.Float, default=0)
    top_performing_content_id = db.Column(db.Integer)
    top_performing_content_type = db.Column(db.String(50))
    top_performing_strategy = db.Column(db.String(100))
    alex_total_score = db.Column(db.Integer, default=0)
    sarah_total_score = db.Column(db.Integer, default=0)
    persona_winner = db.Column(db.String(50))
    best_posting_hour = db.Column(db.Integer)
    best_posting_day = db.Column(db.Integer)
    sponsor_value_estimate = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    email = db.Column(db.String(200))
    website_url = db.Column(db.String(500))
    logo_url = db.Column(db.String(500))
    tier = db.Column(db.String(50), default='standard')
    status = db.Column(db.String(50), default='pending')
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    ctr = db.Column(db.Float, default=0)
    budget_sats = db.Column(db.Integer, default=0)
    spent_sats = db.Column(db.Integer, default=0)
    cpm_sats = db.Column(db.Integer, default=1000)
    target_categories = db.Column(db.String(500))
    target_personas = db.Column(db.String(200))
    ad_copy = db.Column(db.Text)
    cta_text = db.Column(db.String(100))
    cta_url = db.Column(db.String(500))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CreditAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signal_points = db.Column(db.Integer, default=0)
    lifetime_points = db.Column(db.Integer, default=0)
    tier = db.Column(db.String(50), default='recruit')
    tier_progress = db.Column(db.Float, default=0)
    articles_read = db.Column(db.Integer, default=0)
    podcasts_listened = db.Column(db.Integer, default=0)
    quizzes_completed = db.Column(db.Integer, default=0)
    referrals_made = db.Column(db.Integer, default=0)
    streak_days = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime)
    badges = db.Column(db.Text)
    achievements = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('credit_account', uselist=False))

class PredictionOracle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    prediction_type = db.Column(db.String(50))
    prediction_value = db.Column(db.Float)
    target_date = db.Column(db.DateTime)
    actual_value = db.Column(db.Float)
    accuracy_score = db.Column(db.Float)
    status = db.Column(db.String(50), default='pending')
    is_correct = db.Column(db.Boolean)
    signal_points_wagered = db.Column(db.Integer, default=0)
    signal_points_won = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

class UserSegment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    segment_type = db.Column(db.String(50), default='general')
    confidence = db.Column(db.Float, default=0.5)
    hashrate_interest = db.Column(db.Float, default=0)
    macro_interest = db.Column(db.Float, default=0)
    technical_interest = db.Column(db.Float, default=0)
    trading_interest = db.Column(db.Float, default=0)
    privacy_interest = db.Column(db.Float, default=0)
    articles_viewed = db.Column(db.Integer, default=0)
    avg_read_time = db.Column(db.Float, default=0)
    preferred_categories = db.Column(db.Text)
    last_classification = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('segment', uselist=False))

class AffiliatePartner(db.Model):
    __tablename__ = 'affiliate_partner'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))
    url = db.Column(db.String(500))
    benefit = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')

class AffiliateClick(db.Model):
    __tablename__ = 'affiliate_click'
    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
    source_page = db.Column(db.String(500))
    ip_hash = db.Column(db.String(64))
    user_agent = db.Column(db.String(500))
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# P3 AFFILIATE TABLES — Meanwhile + RNS.ID
# Created: 2026-03-09
# ============================================================

class P3AffiliateClick(db.Model):
    """Privacy-first click tracking for Meanwhile + RNS.ID affiliate programs."""
    __tablename__ = 'p3_affiliate_clicks'
    id = db.Column(db.Integer, primary_key=True)
    partner = db.Column(db.String(50), nullable=False)       # meanwhile | rns_id
    referrer_page = db.Column(db.String(500))                # /articles/123, etc.
    ab_variant = db.Column(db.String(1))                     # A | B
    converted = db.Column(db.Integer, default=0)             # 1 if reached partner site
    user_hash = db.Column(db.String(64))                     # SHA256(ip+date+salt)
    user_agent_hash = db.Column(db.String(64))               # SHA256(user_agent)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_p3_aff_partner_date', 'partner', 'clicked_at'),
        db.Index('idx_p3_aff_variant', 'partner', 'ab_variant'),
        # P1 FIX (I7): indexes for referrer_page and user_hash (used in analytics/k-anon queries)
        db.Index('idx_p3_aff_referrer', 'referrer_page'),
        db.Index('idx_p3_aff_user_hash', 'user_hash'),
    )


class P3AffiliateAbResults(db.Model):
    """A/B test aggregates for Thompson Sampling MAB."""
    __tablename__ = 'p3_affiliate_ab_results'
    id = db.Column(db.Integer, primary_key=True)
    partner = db.Column(db.String(50), nullable=False)       # meanwhile | rns_id
    variant = db.Column(db.String(1), nullable=False)        # A | B
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    winner_locked = db.Column(db.Boolean, default=False)     # True = MAB frozen
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('partner', 'variant', name='uq_p3_ab_partner_variant'),
    )


class FeedItem(db.Model):
    __tablename__ = 'feed_item'
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)
    tier = db.Column(db.String(20))
    title = db.Column(db.String(500))
    url = db.Column(db.String(1000), unique=True)
    published_at = db.Column(db.DateTime)
    author = db.Column(db.String(100))
    summary = db.Column(db.Text)
    platform_icon = db.Column(db.String(50))
    raw_json = db.Column(db.Text)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SentimentSnapshot(db.Model):
    __tablename__ = 'sentiment_snapshot'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float, default=50.0)
    state = db.Column(db.String(50), default='EQUILIBRIUM')
    state_label = db.Column(db.String(50), default='EQUILIBRIUM')
    state_color = db.Column(db.String(20), default='#ffffff')
    velocity = db.Column(db.Float, default=0.0)
    top_keywords = db.Column(db.Text)
    top_topics_json = db.Column(db.Text)
    sample_size = db.Column(db.Integer, default=0)
    verified_weight = db.Column(db.Integer, default=0)
    computed_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PulseEvent(db.Model):
    __tablename__ = 'pulse_event'
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    from_state = db.Column(db.String(50))
    to_state = db.Column(db.String(50))
    score = db.Column(db.Float)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    payload_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AutoPostDraft(db.Model):
    __tablename__ = 'autopost_draft'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default='draft')
    body = db.Column(db.Text)
    reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    posted_at = db.Column(db.DateTime)

class DailyBrief(db.Model):
    __tablename__ = 'daily_brief'
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String(500))
    body = db.Column(db.Text)
    signals_json = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PageView(db.Model):
    __tablename__ = 'page_view'
    id = db.Column(db.Integer, primary_key=True)
    page_path = db.Column(db.String(500), nullable=False)
    page_title = db.Column(db.String(300))
    page_category = db.Column(db.String(50))
    session_id = db.Column(db.String(64))
    ip_hash = db.Column(db.String(64))
    user_agent = db.Column(db.String(300))
    referrer = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    time_on_page = db.Column(db.Integer, default=0)
    scroll_depth = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HotMoment(db.Model):
    __tablename__ = 'hot_moment'
    id = db.Column(db.Integer, primary_key=True)
    page_path = db.Column(db.String(500), nullable=False)
    page_title = db.Column(db.String(300))
    page_category = db.Column(db.String(50))
    views_in_window = db.Column(db.Integer, default=0)
    unique_visitors = db.Column(db.Integer, default=0)
    heat_score = db.Column(db.Float, default=0)
    is_peak = db.Column(db.Boolean, default=False)
    peak_detected_at = db.Column(db.DateTime)
    tweet_drafted = db.Column(db.Boolean, default=False)
    tweet_content = db.Column(db.Text)
    tweet_posted_at = db.Column(db.DateTime)
    window_start = db.Column(db.DateTime, nullable=False)
    window_end = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContentSuggestion(db.Model):
    __tablename__ = 'content_suggestion'
    id = db.Column(db.Integer, primary_key=True)
    suggestion_type = db.Column(db.String(50))
    title = db.Column(db.String(300))
    description = db.Column(db.Text)
    reasoning = db.Column(db.Text)
    based_on_page = db.Column(db.String(500))
    based_on_trend = db.Column(db.String(200))
    confidence_score = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actioned_at = db.Column(db.DateTime)

class AutoTweet(db.Model):
    __tablename__ = 'auto_tweet'
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(50))
    trigger_page = db.Column(db.String(500))
    heat_score_at_trigger = db.Column(db.Float)
    tweet_content = db.Column(db.Text, nullable=False)
    hashtags = db.Column(db.String(200))
    status = db.Column(db.String(20), default='draft')
    approved_at = db.Column(db.DateTime)
    posted_at = db.Column(db.DateTime)
    post_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =====================================
# X ENGAGEMENT SENTRY (TWEET REPLIES)
# =====================================


class XInboxTweet(db.Model):
    """Incoming tweets from monitored X accounts for Sovereign Sentry."""
    __tablename__ = 'x_inbox_tweet'

    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String(64), unique=True, nullable=False)
    author_handle = db.Column(db.String(50), nullable=False, index=True)
    author_name = db.Column(db.String(100))
    tweet_text = db.Column(db.Text, nullable=False)
    tweet_url = db.Column(db.String(500))
    tweet_created_at = db.Column(db.DateTime)
    status = db.Column(
        db.String(20),
        default='new',
    )  # new | drafted | approved | posted | rejected | skipped | error
    tier = db.Column(db.String(30))
    style = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class XReplyDraft(db.Model):
    """Generated reply drafts evaluated by Sovereign Sentry."""
    __tablename__ = 'x_reply_draft'

    id = db.Column(db.Integer, primary_key=True)
    inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
    draft_text = db.Column(db.String(300), nullable=False)
    confidence = db.Column(db.Float)
    reasoning = db.Column(db.Text)
    style_used = db.Column(db.String(30))
    risk_flags = db.Column(db.Text)  # optional JSON array string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))


class XReplyPost(db.Model):
    """Log of replies actually posted to X."""
    __tablename__ = 'x_reply_post'

    id = db.Column(db.Integer, primary_key=True)
    inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
    draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
    reply_tweet_id = db.Column(db.String(64))
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_payload = db.Column(db.Text)  # raw JSON from X API

    inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
    draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))


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

class RollingActivity(db.Model):
    __tablename__ = 'rolling_activity'
    id = db.Column(db.Integer, primary_key=True)
    page_path = db.Column(db.String(500), nullable=False, index=True)
    page_name = db.Column(db.String(200))
    session_hash = db.Column(db.String(64), nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def record_activity(cls, page_path, page_name, session_hash):
        existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
        if existing:
            existing.last_seen = datetime.utcnow()
        else:
            activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
            db.session.add(activity)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    @classmethod
    def get_operative_density(cls, window_minutes=30, limit=5):
        from sqlalchemy import func
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
        return results

class RealTimeProduct(db.Model):
    __tablename__ = 'realtime_product'
    id = db.Column(db.Integer, primary_key=True)
    statement_text = db.Column(db.String(100), nullable=False)
    design_url = db.Column(db.String(500))
    design_style = db.Column(db.String(50), default='center_chest')
    text_color = db.Column(db.String(20), default='#FFFFFF')
    trigger_state = db.Column(db.String(50))
    trigger_keywords = db.Column(db.Text)
    sentiment_score = db.Column(db.Float)
    status = db.Column(db.String(20), default='draft')
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    printful_product_id = db.Column(db.String(100))
    printful_sync_status = db.Column(db.String(50), default='pending')
    heat_multiplier = db.Column(db.Float, default=2.0)
    heat_expires_at = db.Column(db.DateTime)
    sarah_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_hot(self):
        return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at

class IntelligencePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    persona = db.Column(db.String(20))
    partner_name = db.Column(db.String(100))
    partner_handle = db.Column(db.String(100))
    primary_tweet = db.Column(db.Text, nullable=False)
    thread_content = db.Column(db.Text)
    key_insight = db.Column(db.Text)
    source_video_id = db.Column(db.String(50))
    source_video_title = db.Column(db.String(500))
    x_tweet_id = db.Column(db.String(100))
    nostr_event_id = db.Column(db.String(100))
    engagement_likes = db.Column(db.Integer, default=0)
    engagement_retweets = db.Column(db.Integer, default=0)
    engagement_replies = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SentimentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    report_date = db.Column(db.Date, nullable=False, unique=True)
    overall_sentiment = db.Column(db.String(20))
    sentiment_score = db.Column(db.Float)
    x_posts_analyzed = db.Column(db.Integer, default=0)
    nostr_notes_analyzed = db.Column(db.Integer, default=0)
    top_themes = db.Column(db.Text)
    key_narratives = db.Column(db.Text)
    cited_sources = db.Column(db.Text)
    raw_analysis = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    article = db.relationship('Article', backref='sentiment_report', lazy=True)

class SarahBrief(db.Model):
    __tablename__ = 'sarah_brief'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    brief_date = db.Column(db.Date, nullable=False, unique=True)
    macro_state = db.Column(db.Text)
    network_calibration = db.Column(db.Text)
    signal_1_title = db.Column(db.String(500))
    signal_1_source = db.Column(db.String(500))
    signal_1_url = db.Column(db.String(500))
    signal_1_impact = db.Column(db.Float, default=0.0)
    signal_2_title = db.Column(db.String(500))
    signal_2_source = db.Column(db.String(500))
    signal_2_url = db.Column(db.String(500))
    signal_2_impact = db.Column(db.Float, default=0.0)
    signal_3_title = db.Column(db.String(500))
    signal_3_source = db.Column(db.String(500))
    signal_3_url = db.Column(db.String(500))
    signal_3_impact = db.Column(db.Float, default=0.0)
    mempool_state = db.Column(db.Text)
    hashrate_state = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    article = db.relationship('Article', backref='sarah_brief', lazy=True)

class SentimentBuffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sentiment_score = db.Column(db.Float, nullable=False)
    post_count = db.Column(db.Integer, default=0)
    dominant_theme = db.Column(db.String(200))
    source_breakdown = db.Column(db.Text)

class EmergencyFlash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    previous_score = db.Column(db.Float)
    current_score = db.Column(db.Float)
    drift_magnitude = db.Column(db.Float)
    direction = db.Column(db.String(20))
    trigger_reason = db.Column(db.Text)
    top_signal_url = db.Column(db.String(500))
    top_signal_author = db.Column(db.String(200))
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    article = db.relationship('Article', backref='emergency_flash', lazy=True)

# =====================================
# NOSTR INTELLIGENCE MONITOR (F4)
# =====================================

class NostrMonitorEvent(db.Model):
    """Inbound Nostr events captured by the relay monitor."""
    __tablename__ = 'nostr_monitor_events'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(64), unique=True, nullable=False)
    pubkey = db.Column(db.String(64), nullable=False)
    kind = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    engagement_score = db.Column(db.Float, default=0.0)
    zaps = db.Column(db.Integer, default=0)
    quotes = db.Column(db.Integer, default=0)
    reposts = db.Column(db.Integer, default=0)
    replies = db.Column(db.Integer, default=0)
    reactions = db.Column(db.Integer, default=0)
    bitcoin_relevance = db.Column(db.Float, default=0.0)
    relay_source = db.Column(db.String(100))
    created_at = db.Column(db.Integer, nullable=False)       # Nostr unix timestamp
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_nostr_score', 'engagement_score'),
        db.Index('idx_nostr_created', 'created_at'),
        db.Index('idx_nostr_relevance', 'bitcoin_relevance'),
    )


class NostrTrackedPubkey(db.Model):
    """High-signal Nostr pubkeys tracked by Protocol Pulse."""
    __tablename__ = 'nostr_tracked_pubkeys'
    id = db.Column(db.Integer, primary_key=True)
    pubkey = db.Column(db.String(64), unique=True, nullable=False)
    display_name = db.Column(db.String(150))
    nip05 = db.Column(db.String(200))
    follower_tier = db.Column(db.String(20), default='standard')  # 'vip', 'standard'
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_nostr_pubkey_tier', 'follower_tier'),
    )


class CollectedSignal(db.Model):
    __tablename__ = 'collected_signal'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20), nullable=False)
    post_id = db.Column(db.String(100), nullable=False, unique=True)
    author_name = db.Column(db.String(200), nullable=False)
    author_handle = db.Column(db.String(100), nullable=False)
    author_tier = db.Column(db.String(50), default='general')
    content = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(500), nullable=False)
    engagement_likes = db.Column(db.Integer, default=0)
    engagement_reposts = db.Column(db.Integer, default=0)
    engagement_replies = db.Column(db.Integer, default=0)
    engagement_score = db.Column(db.Float, default=0.0)
    sentiment = db.Column(db.String(20))
    sentiment_score = db.Column(db.Float)
    is_bitcoin_related = db.Column(db.Boolean, default=True)
    posted_at = db.Column(db.DateTime)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=True)
    is_legendary = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
        db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
    )


class PriceAlert(db.Model):
    """Bitcoin price alert subscriptions — double opt-in, Resend delivery."""
    __tablename__ = 'price_alerts'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, index=True)
    target_price = db.Column(db.Float, nullable=False)
    direction = db.Column(db.String(5), nullable=False)  # 'above' or 'below'
    # Legacy field kept for backward compat with old /api/charts/price-alert route
    triggered = db.Column(db.Boolean, default=False, nullable=False)
    triggered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Double opt-in fields (SESSION 20)
    active = db.Column(db.Boolean, default=False)      # False until confirmed
    confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(86), unique=True)
    cancel_token = db.Column(db.String(86), unique=True)
    expires_at = db.Column(db.DateTime)                # 24hr for unconfirmed
    __table_args__ = (
        db.Index('idx_price_alerts_email_triggered', 'email', 'triggered'),
        db.Index('idx_price_alerts_active', 'triggered', 'target_price'),
        db.Index('idx_price_alerts_confirm', 'confirm_token'),
        db.Index('idx_price_alerts_cancel', 'cancel_token'),
    )

    @staticmethod
    def generate_token():
        import secrets
        return secrets.token_urlsafe(32)

# =====================================
# TERMINAL API SUBSCRIBER MODELS
# =====================================

class ApiSubscriber(db.Model):
    """Standalone API subscriber — email + Stripe + API key. No User account required."""
    __tablename__ = 'api_subscribers'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    api_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    tier = db.Column(db.String(30), default='commander')  # commander|enterprise|demo
    stripe_customer_id = db.Column(db.String(120), index=True)
    stripe_subscription_id = db.Column(db.String(120), unique=True)
    stripe_price_id = db.Column(db.String(120))

    # Rate limiting
    rate_limit_per_hour = db.Column(db.Integer, default=1000)
    requests_this_hour = db.Column(db.Integer, default=0)
    requests_today = db.Column(db.Integer, default=0)
    requests_total = db.Column(db.Integer, default=0)
    rate_window_start = db.Column(db.DateTime)  # when current hour window started

    # Scoped entitlements (JSON: {"stream": true, "webhook": true, "signal": true})
    entitlements = db.Column(db.Text, default='{}')
    # Key scopes (JSON array: ["read", "stream", "webhook"])
    key_scopes = db.Column(db.Text, default='["read"]')
    # Key expiry (NULL = no expiry)
    key_expires_at = db.Column(db.DateTime, nullable=True)

    # Webhook delivery
    webhook_url = db.Column(db.String(500))
    webhook_secret = db.Column(db.String(100))  # HMAC secret

    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    subscription_status = db.Column(db.String(30), default='active')  # active|past_due|canceled
    current_period_end = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)
    welcome_email_sent = db.Column(db.Boolean, default=False)
    past_due_since = db.Column(db.DateTime, nullable=True)
    previous_api_key = db.Column(db.String(64), nullable=True)
    previous_key_expires_at = db.Column(db.DateTime, nullable=True)

    def get_entitlements(self):
        """Return entitlements as dict."""
        try:
            return json.loads(self.entitlements or '{}')
        except (ValueError, TypeError):
            return {}

    def has_entitlement(self, feature: str) -> bool:
        return self.get_entitlements().get(feature, False)

    def get_scopes(self):
        try:
            return json.loads(self.key_scopes or '["read"]')
        except (ValueError, TypeError):
            return ['read']

    def is_key_valid(self):
        """Check key is active and not expired."""
        if not self.is_active:
            return False
        if self.subscription_status == 'canceled':
            return False
        if self.key_expires_at and datetime.utcnow() > self.key_expires_at:
            return False
        if self.subscription_status == "past_due":
            # Allow 72-hour grace period after payment failure
            if self.past_due_since:
                grace_end = self.past_due_since + timedelta(hours=72)
                if datetime.utcnow() > grace_end:
                    return False
        return True


class ApiRequestLog(db.Model):
    """Per-request log for rate limiting and usage analytics."""
    __tablename__ = 'api_request_log'
    __table_args__ = (
        db.Index('idx_api_log_key_time', 'api_key', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(64), nullable=False)
    endpoint = db.Column(db.String(200), nullable=False)
    response_time_ms = db.Column(db.Integer)
    status_code = db.Column(db.Integer)
    ip_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
# ── B1 Newsletter ───────────────────────────────────────────────────────────

class NewsletterSubscriber(db.Model):
    """LAW 4: Each subscriber has a unique unsubscribe_token (CAN-SPAM compliance)."""
    __tablename__ = 'newsletter_subscribers'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False)
    unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False)
    subscribed = db.Column(db.Boolean, default=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    unsubscribed_at = db.Column(db.DateTime)
    source = db.Column(db.String(50))  # 'homepage', 'api', 'import'

    __table_args__ = (
        db.Index('idx_newsletter_subscribers_email', 'email'),
        db.Index('idx_newsletter_subscribers_token', 'unsubscribe_token'),
        db.Index('idx_newsletter_subscribers_subscribed', 'subscribed'),
    )


class NewsletterSend(db.Model):
    """LAW 2: One newsletter per day — tracks sends for idempotency."""
    __tablename__ = 'newsletter_sends'

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.Text)
    resend_message_id = db.Column(db.String(100))
    resend_batch_id = db.Column(db.String(100))
    recipient_count = db.Column(db.Integer, default=0)
    open_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    article_ids = db.Column(db.Text)  # JSON array of article IDs included

    __table_args__ = (
        db.Index('idx_newsletter_sends_sent_at', 'sent_at'),
    )

# =====================================
# SCHIFF-BOT / BRIAN — HYPOCRISY METRIC
# =====================================

class SchiffHypocrisy(db.Model):
    """One calculated hypocrisy score snapshot per calendar day (score_date is unique)."""
    __tablename__ = 'schiff_hypocrisy'
    id = db.Column(db.Integer, primary_key=True)
    score_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)  # one row per day
    score = db.Column(db.Float, nullable=False)           # 0-100
    gold_holding_pct = db.Column(db.Float)                # 0-100 (% of AUM in gold/miners)
    anti_btc_tweet_rate = db.Column(db.Float)             # 0-100 (normalised statement rate)
    no_btc_holding_pct = db.Column(db.Float)              # 0 or 100 (binary: no BTC = 100)
    gold_vs_btc_perf_gap = db.Column(db.Float)            # 0-100 (normalised perf gap)
    total_aum_usd = db.Column(db.Float)
    btc_holdings_usd = db.Column(db.Float, default=0)
    gold_holdings_usd = db.Column(db.Float)
    filing_date = db.Column(db.Date)
    filing_type = db.Column(db.String(20), default='13F-HR')
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    data_sources = db.Column(db.Text)                     # JSON array of source URLs
    __table_args__ = (
        db.Index('idx_schiff_hypo_calculated_at', 'calculated_at'),
        db.Index('idx_schiff_hypo_score_date', 'score_date'),
        db.UniqueConstraint('score_date', name='uq_schiff_score_date'),
    )

# =====================================
# NODE WATCH
# =====================================

class NodeSnapshot(db.Model):
    """Bitcoin network node count snapshot — polled every 15 min via cron."""
    __tablename__ = 'node_snapshots'
    __table_args__ = (
        db.Index('idx_node_snapshots_timestamp', 'timestamp'),
        db.Index('idx_node_snapshots_node_count', 'node_count'),
    )

    id = db.Column(db.Integer, primary_key=True)
    node_count = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # JSON blob: {versions: {...}, countries: {...}, ipv4: N, ipv6: N}
    snapshot_data = db.Column(db.Text)
    # NULL = no alert; otherwise the alert type string (fired at this snapshot)
    alert_fired = db.Column(db.String(120))
    # Stateful edge-trigger flags — true while the condition is active.
    # An alert fires only when: currently True AND previous snapshot was False.
    daily_alert_active  = db.Column(db.Boolean, default=False, nullable=False)
    weekly_alert_active = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'node_count': self.node_count,
            'timestamp': self.timestamp.isoformat(),
            'alert_fired': self.alert_fired,
        }


class SchiffStatement(db.Model):
    """Manually-seeded public statements by Peter Schiff."""
    __tablename__ = 'schiff_public_statements'
    id = db.Column(db.Integer, primary_key=True)
    statement = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(50))          # 'twitter', 'podcast', 'interview'
    statement_date = db.Column(db.Date)
    anti_btc_score = db.Column(db.Integer, default=1)  # 1=anti-BTC, 0=neutral
    source_url = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.Index('idx_schiff_stmt_date', 'statement_date'),
    )

