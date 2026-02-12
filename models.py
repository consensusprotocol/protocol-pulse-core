from datetime import datetime, timedelta
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
    header_image_url = db.Column(db.String(500))
    screenshot_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))

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
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
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


class PartnerClick(db.Model):
    """Hub partner-ramp click tracking (thin-slice V1)."""
    __tablename__ = 'partner_click'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=True)
    partner_slug = db.Column(db.String(80), nullable=False, index=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    referral_code = db.Column(db.String(120))
    source_page = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class PartnerConversionNote(db.Model):
    """Admin notes for partner performance and conversion context."""
    __tablename__ = 'partner_conversion_note'
    id = db.Column(db.Integer, primary_key=True)
    partner_slug = db.Column(db.String(80), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

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
# X ENGAGEMENT SENTRY MODELS
# =====================================

class XInboxTweet(db.Model):
    __tablename__ = 'x_inbox_tweet'
    __table_args__ = (db.Index('idx_x_inbox_status_created', 'status', 'created_at'),)

    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    author_handle = db.Column(db.String(50), nullable=False, index=True)
    author_name = db.Column(db.String(100))
    tweet_text = db.Column(db.Text, nullable=False)
    tweet_url = db.Column(db.String(500))
    tweet_created_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='new', index=True)
    tier = db.Column(db.String(30))
    style = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class XReplyDraft(db.Model):
    __tablename__ = 'x_reply_draft'
    __table_args__ = (db.Index('idx_x_reply_draft_confidence', 'confidence'),)

    id = db.Column(db.Integer, primary_key=True)
    inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False, index=True)
    draft_text = db.Column(db.String(300), nullable=False)
    confidence = db.Column(db.Float)
    reasoning = db.Column(db.Text)
    style_used = db.Column(db.String(30))
    risk_flags = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))


class XReplyPost(db.Model):
    __tablename__ = 'x_reply_post'
    __table_args__ = (db.Index('idx_x_reply_post_posted_at', 'posted_at'),)

    id = db.Column(db.Integer, primary_key=True)
    inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False, index=True)
    draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
    reply_tweet_id = db.Column(db.String(64), index=True)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    response_payload = db.Column(db.Text)

    inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
    draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))


class MiningSnapshot(db.Model):
    __tablename__ = 'mining_snapshot'
    __table_args__ = (db.Index('idx_mining_snapshot_location_captured', 'location_id', 'captured_at'),)

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.String(80), nullable=False, index=True)
    location_name = db.Column(db.String(120))
    overall_score = db.Column(db.Float, nullable=False)
    political_score = db.Column(db.Float, default=0)
    economic_score = db.Column(db.Float, default=0)
    operational_score = db.Column(db.Float, default=0)
    factors_json = db.Column(db.Text)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

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
        if self.submitted_at is None:
            self.submitted_at = datetime.utcnow()
        age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
        time_decay = max(0.1, 1 - (age_hours / 168))
        raw_score = (self.total_sats or 0) * 0.001 + (self.zap_count or 0) * 10
        self.signal_score = raw_score * time_decay * (self.decay_factor or 1.0)
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


class ClaimPayout(db.Model):
    """Sovereign Claim Portal: payout history to prevent double-spend and enforce rate limit."""
    __tablename__ = 'claim_payout'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
    amount_sats = db.Column(db.BigInteger, nullable=False)
    lightning_address = db.Column(db.String(200))
    claimed_by_pubkey = db.Column(db.String(128), nullable=False, index=True)  # Nostr pubkey who claimed
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    payment_hash = db.Column(db.String(128))
    error_message = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime)
    creator = db.relationship('ValueCreator', backref=db.backref('claim_payouts', lazy='dynamic'))


# =====================================
# SOVEREIGN INTELLIGENCE NEXUS
# =====================================

class KOLPulseItem(db.Model):
    """Live feed item from KOLs: X, Nostr, YouTube. Command Log / Pulse stream."""
    __tablename__ = 'kol_pulse_item'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20), nullable=False, index=True)  # x, nostr, youtube
    author_handle = db.Column(db.String(100), nullable=False, index=True)
    author_name = db.Column(db.String(200))
    content = db.Column(db.Text)
    url = db.Column(db.String(1000))
    external_id = db.Column(db.String(128), unique=True, nullable=False, index=True)  # tweet_id, note_id, video_id
    raw_json = db.Column(db.Text)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class ZapCommentLog(db.Model):
    """Log of automated X/Nostr replies posted after a zap (Diplomat bridge)."""
    __tablename__ = 'zap_comment_log'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
    zap_event_id = db.Column(db.Integer, db.ForeignKey('zap_event.id'))
    platform = db.Column(db.String(20), nullable=False)  # x, nostr
    external_id = db.Column(db.String(128))  # tweet_id or note_id we replied to
    reply_id = db.Column(db.String(128))  # our reply tweet/note id
    message = db.Column(db.Text)
    claim_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post = db.relationship('CuratedPost', backref=db.backref('zap_comments', lazy='dynamic'))


class DailyMedley(db.Model):
    """Pinned Daily Value Medley: top-zapped clips spliced + narrated. Featured at top of stream."""
    __tablename__ = 'daily_medley'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    media_url = db.Column(db.String(500))  # uploaded video URL
    source_post_ids = db.Column(db.Text)  # JSON array of curated_post ids
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
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
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
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
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    article = db.relationship('Article', backref='emergency_flash', lazy=True)

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