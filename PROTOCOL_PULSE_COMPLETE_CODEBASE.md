# Protocol Pulse - Complete Codebase Reference

> **Version:** January 2026 | **Architecture:** Flask + SQLAlchemy + PostgreSQL  
> **Mission:** World-class Bitcoin intelligence hub with AI-powered content generation

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Application Files](#core-application-files)
3. [Database Models](#database-models)
4. [Routes & API Endpoints](#routes--api-endpoints)
5. [AI Services](#ai-services)
6. [Content Generation Engine](#content-generation-engine)
7. [Social Distribution Services](#social-distribution-services)
8. [Bitcoin Network Services](#bitcoin-network-services)
9. [CRM & Monetization](#crm--monetization)
10. [Automation & Scheduling](#automation--scheduling)
11. [Configuration & Environment](#configuration--environment)

---

## Architecture Overview

### System Design Philosophy

Protocol Pulse operates on a **Human-in-Loop** principle:
- AI generates content, drafts, and recommendations
- Humans approve and execute all social actions via Launch Console
- Zero tolerance for fabricated metrics (Editorial Accuracy Mandate)

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Flask 2.x with SQLAlchemy ORM |
| **Database** | PostgreSQL (Neon-backed) |
| **AI Providers** | OpenAI (GPT-4o), Anthropic (Claude), Google Gemini, xAI Grok |
| **Audio** | ElevenLabs multi-voice synthesis |
| **Video** | FFmpeg + yt-dlp for extraction |
| **Transcription** | AssemblyAI for X Spaces |
| **CRM** | HighLevel (GHL) API v2 |
| **Payments** | Stripe (pending configuration) |
| **Distribution** | Nostr Protocol, X/Twitter |

### Ground Truth Data (January 2026)

```
Bitcoin Difficulty: 146.47 T (below November 2025 peak of 155.9 T)
Network Hashrate: ~977 EH/s
PROHIBITION: Never claim "Record Highs" unless difficulty exceeds 155.9 T
```

---

## Core Application Files

### app.py - Application Configuration

```python
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app (single global instance)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Get port from environment for deployment
port = int(os.environ.get("PORT", 5000))

# Configure the database (SQLite default, PostgreSQL for production)
database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
if database_url.startswith("sqlite:"):
    database_url += "?charset=utf8mb4"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

with app.app_context():
    import models
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Template filters for ad injection and JSON parsing
@app.template_filter('inject_ads')
def inject_ads(content):
    """Injects native ads into article content"""
    # ... implementation
    
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string to Python object"""
    # ... implementation
```

### main.py - Application Entry Point

```python
from app import app
from routes import *

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

---

## Database Models

### models.py - Complete Schema (Actual Implementation)

```python
from app import db
from datetime import datetime
from flask_login import UserMixin


class User(UserMixin, db.Model):
    """User authentication and admin access"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    newsletter_subscribed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Article(db.Model):
    """AI-generated and curated articles"""
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
    substack_url = db.Column(db.String(500))
    header_image_url = db.Column(db.String(500))
    screenshot_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))


class Podcast(db.Model):
    """Podcast episodes from RSS or AI-generated"""
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
    rss_source = db.Column(db.String(100))


class ContentPrompt(db.Model):
    """Customizable AI prompt templates"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Advertisement(db.Model):
    """Native ad placements"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    target_url = db.Column(db.String(300), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AutomationRun(db.Model):
    """Track automation task executions"""
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # running, success, failed, skipped
    error = db.Column(db.String(500))


class LaunchSequence(db.Model):
    """X/Twitter distribution campaigns"""
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer)
    content_type = db.Column(db.String(50))  # episode, brief, clip, article
    
    primary_post_copy = db.Column(db.Text)
    thread_replies = db.Column(db.Text)  # JSON array
    quote_variants = db.Column(db.Text)  # JSON array
    reply_drafts = db.Column(db.Text)  # JSON array of 10 templates
    
    hashtags = db.Column(db.String(500))
    posting_time = db.Column(db.Time)
    velocity_prediction = db.Column(db.Float)
    
    first_reply_link = db.Column(db.String(500))
    call_to_action = db.Column(db.String(300))
    
    status = db.Column(db.String(50), default='draft')  # draft, approved, published, analyzed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    
    tweet_id = db.Column(db.String(100))
    actual_velocity_score = db.Column(db.Float)
    replies_first_5min = db.Column(db.Integer, default=0)
    total_engagement = db.Column(db.Integer, default=0)
    reached_for_you = db.Column(db.Boolean, default=False)


class TargetAlert(db.Model):
    """Target engagement opportunities"""
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(50))  # reply_squad, trending, partner
    source_url = db.Column(db.String(500))
    source_account = db.Column(db.String(100))
    content_snippet = db.Column(db.Text)
    priority = db.Column(db.Integer, default=2)  # 1 highest, 3 lowest
    strategy_suggested = db.Column(db.String(100))
    draft_replies = db.Column(db.Text)  # JSON array
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)


class NostrEvent(db.Model):
    """Nostr broadcast tracking"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100))
    content_type = db.Column(db.String(50))
    content_id = db.Column(db.Integer)
    relays_success = db.Column(db.Text)  # JSON array
    relays_failed = db.Column(db.Text)  # JSON array
    zaps_received = db.Column(db.Integer, default=0)
    zaps_amount_sats = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReplySquadMember(db.Model):
    """Monitored X accounts for engagement"""
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(150))
    category = db.Column(db.String(100))  # human_rights, macro, technical, mining
    priority = db.Column(db.Integer, default=2)
    reciprocal_engagements = db.Column(db.Integer, default=0)
    last_engagement = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WhaleTransaction(db.Model):
    """Large BTC transactions for Whale Watcher"""
    id = db.Column(db.Integer, primary_key=True)
    txid = db.Column(db.String(100), unique=True, nullable=False)
    btc_amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float)
    fee_sats = db.Column(db.Integer)
    block_height = db.Column(db.Integer)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_mega = db.Column(db.Boolean, default=False)  # 1000+ BTC


class BitcoinDonation(db.Model):
    """Bitcoin donations via Lightning/On-chain"""
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100))
    amount_sats = db.Column(db.Integer)
    amount_usd = db.Column(db.Float)
    donor_email = db.Column(db.String(200))
    donor_name = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50))  # onchain, lightning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
```

---

## Routes & API Endpoints

### routes.py - Complete Routing (Summary)

```python
# PUBLIC ROUTES
@app.route('/')                          # Homepage with featured articles
@app.route('/article/<slug>')            # Individual article page
@app.route('/category/<category>')       # Category archive
@app.route('/cypherpunks')               # Cypherpunks category
@app.route('/podcasts')                  # Podcast archive
@app.route('/meetup-map')                # Bitcoin Meetup Map
@app.route('/whale-watcher')             # 500+ BTC transaction monitor
@app.route('/series/<show_id>')          # Series guide with YouTube
@app.route('/sovereign-intel')           # Premium subscription landing
@app.route('/subscribe', methods=['POST']) # Newsletter signup

# INTELLIGENCE DASHBOARD (Requires Login)
@app.route('/intelligence')              # Main dashboard
@app.route('/launch-console')            # X/Twitter distribution
@app.route('/target-monitor')            # Reply Squad engagement

# API ENDPOINTS
@app.route('/api/network-stats')                           # Live Bitcoin data
@app.route('/api/launch-sequence/<id>/generate', POST)     # Generate campaign
@app.route('/api/launch-sequence/<id>/status', PUT)        # Update status
@app.route('/api/target-monitor/add', POST)                # Add target
@app.route('/api/target-monitor/<id>/scan', POST)          # Scan for opportunities
@app.route('/api/reply-draft/<id>/approve', POST)          # Approve draft
@app.route('/api/article/<id>/broadcast-nostr', POST)      # Nostr broadcast
@app.route('/api/podcast/generate/<id>', POST)             # Generate podcast
@app.route('/api/ghl/sync-metrics', POST)                  # Sync to GHL CRM
@app.route('/api/create-checkout', POST)                   # Stripe checkout
@app.route('/api/meetups')                                 # Nearby merchants
@app.route('/api/whales')                                  # Whale transactions
@app.route('/api/generate/reddit-trends', POST)            # Auto-generate from Reddit

# ADMIN ROUTES
@app.route('/admin')                     # Dashboard
@app.route('/admin/articles')            # Article management
@app.route('/admin/article/<id>/edit')   # Edit article
@app.route('/admin/generate')            # Content generation interface

# AUTHENTICATION
@app.route('/login', methods=['GET', 'POST'])
@app.route('/logout')
```

---

## AI Services

### services/ai_service.py - Multi-Provider AI Integration

```python
class AIService:
    """
    Multi-provider AI service with fallback logic.
    Priority: OpenAI (GPT-4o) → Gemini → Anthropic (Claude) → Grok
    """
    
    def generate_content(self, prompt: str, provider: str = "auto") -> Optional[str]:
        """Generate content using specified or best available provider"""
        
    def generate_content_openai(self, prompt: str, model: str = "gpt-4o") -> Optional[str]:
        """Generate using OpenAI GPT-4o"""
        
    def generate_content_anthropic(self, prompt: str, model: str = "claude-sonnet-4-20250514") -> Optional[str]:
        """Generate using Anthropic Claude"""
        
    def generate_content_gemini(self, prompt: str) -> Optional[str]:
        """Generate using Google Gemini 1.5 Pro"""
        
    def generate_content_grok(self, prompt: str, model: str = "grok-2-latest") -> Optional[str]:
        """Generate using xAI Grok"""
        
    def analyze_semantic_similarity(self, text1: str, text2: str) -> float:
        """Use Gemini to analyze semantic similarity (0.0-1.0)"""
```

---

## Content Generation Engine

### services/content_engine.py - Main Content Pipeline

```python
class ContentEngine:
    """
    Main content generation and publishing engine.
    Enforces Editorial Accuracy Mandate and 5-section structure.
    """
    
    ACCURACY_MANDATE = """
    === EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===
    - NEVER claim "all-time high" or "record high" without verification
    - NEVER hallucinate hashrate figures
    - NEVER assume difficulty is increasing
    - Only report what is EXPLICITLY stated in verified source material
    """
    
    def generate_article(self, topic: str, content_type: str) -> Dict:
        """Generate article with enforced 5-section structure"""
        
    def review_article_with_gemini(self, title: str, content: str) -> Dict:
        """Use Gemini as Editor-in-Chief for quality control"""

# 5-Section Article Structure:
# 1. TL;DR - Summary box
# 2. The Report - Main content
# 3. The Bitcoin Lens - Philosophical analysis
# 4. Transactor Intelligence - Actionable insights
# 5. Sources - Attribution
```

---

## Social Distribution Services

### services/launch_sequence.py - X/Twitter Distribution

```python
class LaunchSequenceService:
    """
    AI-powered X/Twitter distribution with human-in-loop approval.
    """
    
    KEYWORD_STRATEGIES = [
        "Sound money principles", "Censorship resistance",
        "Self-custody sovereignty", "Network security metrics",
        "Fiat debasement hedge", "Generational wealth transfer",
        "Permissionless innovation", "Decentralized verification"
    ]
    
    REPLY_STRATEGIES = [
        "agreement", "question", "insight", "historical", "contrarian",
        "amplification", "call_to_action", "technical", "philosophical", "news_hook"
    ]
    
    def create_launch_sequence(self, article: Article) -> Dict:
        """Create complete launch sequence for article distribution"""
        
    def _generate_primary_tweet(self, article: Article, keyword: str) -> str:
        """Generate primary tweet with character limit compliance"""
        
    def _generate_reply_drafts(self, article: Article, primary_tweet: str) -> List[Dict]:
        """Generate 10 reply drafts using different strategies"""
        
    def _predict_engagement_velocity(self, title: str) -> Dict:
        """Predict engagement velocity based on title analysis"""
```

### services/target_monitor.py - Reply Squad Engagement

```python
class TargetMonitorService:
    """
    Monitor target X/Twitter handles for engagement opportunities.
    """
    
    DEFAULT_TARGETS = [
        {"handle": "saborin", "priority": "high"},
        {"handle": "jack", "priority": "high"},
        {"handle": "michael_saylor", "priority": "high"},
        {"handle": "nic__carter", "priority": "medium"},
        {"handle": "adam3us", "priority": "high"}
    ]
    
    def scan_for_opportunities(self, target: TargetMonitor) -> Dict:
        """Scan target for engagement opportunities"""
        
    def get_pending_drafts(self) -> List[ReplyDraft]:
        """Get all pending reply drafts for review"""
        
    def approve_draft(self, draft_id: int) -> Optional[ReplyDraft]:
        """Approve draft for manual posting"""
```

### services/nostr_broadcaster.py - Censorship-Resistant Distribution

```python
class NostrBroadcaster:
    """
    Broadcast content to Nostr network.
    Supports kind:1 (short notes) and kind:30023 (long-form articles).
    """
    
    DEFAULT_RELAYS = [
        "wss://relay.damus.io", "wss://relay.snort.social",
        "wss://nos.lol", "wss://relay.primal.net",
        "wss://nostr.wine", "wss://relay.nostr.band"
    ]
    
    def broadcast_article(self, article) -> Dict:
        """Broadcast article as NIP-23 long-form content"""
        
    def broadcast_note(self, content: str, tags: List = None) -> Dict:
        """Broadcast short note (kind:1)"""
```

---

## Bitcoin Network Services

### services/node_service.py - Live Network Data

```python
class NodeService:
    """Service for fetching live Bitcoin network statistics from Mempool.space API"""
    
    @classmethod
    def get_network_stats(cls) -> Dict:
        """
        Returns:
        {
            "height": "879,123",
            "hashrate": "977.45 EH/s",
            "difficulty_progress": "45.2%",
            "difficulty_change": "+2.34%",
            "remaining_blocks": 1205,
            "status": "OPERATIONAL"
        }
        """
```

### services/meetup_map_service.py - BTC Map Integration

```python
class MeetupMapService:
    """Bitcoin Meetup Map using BTC Map API"""
    
    def get_nearby_merchants(self, lat: float, lon: float, radius_km: int = 50) -> List[Dict]:
        """Get Bitcoin-accepting merchants near a location"""
        
    def get_all_merchants(self) -> List[Dict]:
        """Get all Bitcoin merchants globally"""
```

---

## CRM & Monetization

### services/ghl_service.py - HighLevel CRM Integration

```python
class GHLService:
    """Service for HighLevel (GoHighLevel) CRM API v2"""
    
    def push_to_ghl(self, email: str, name: str = "", tag: str = "Protocol_Pulse_Subscriber") -> Dict:
        """Push subscriber to HighLevel CRM"""
        
    def update_custom_value(self, key: str, value: str) -> Dict:
        """Update Custom Value in GHL location settings"""
        
    def sync_network_metrics(self) -> Dict:
        """Sync Bitcoin network metrics to GHL Custom Values"""
```

### services/monetization_service.py - Stripe Subscriptions

```python
class MonetizationService:
    """
    Premium subscription management via Stripe.
    
    Tiers:
    - Free: Basic access
    - Sovereign ($21/month): Exclusive analysis, early access
    - Node Runner ($99/month): Direct intel channel, API access, strategy calls
    """
    
    def create_checkout_session(self, email: str, tier: str) -> Dict:
        """Create Stripe Checkout session"""
        
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        """Handle Stripe webhook events"""
```

---

## Automation & Scheduling

### services/automation.py - Content Pipeline Automation

```python
class AutomationService:
    """
    Automated content pipeline with 3-tier duplicate detection.
    
    Duplicate Detection Tiers:
    1. Core Topic Matching - Extract main topic, compare against processed
    2. Keyword Jaccard Similarity - Compare keyword sets (threshold: 0.6)
    3. Gemini Semantic Analysis - AI-powered similarity check (threshold: 0.75)
    """
    
    SUBREDDITS = ['Bitcoin', 'CryptoCurrency', 'BitcoinMarkets', 'btc', 'CryptoNews']
    JACCARD_THRESHOLD = 0.6
    SEMANTIC_THRESHOLD = 0.75
    
    def run_content_pipeline(self, max_articles: int = 5) -> Dict:
        """
        Run automated content generation:
        1. Fetch trending topics from Reddit
        2. Filter duplicates using 3-tier detection
        3. Generate articles for novel topics
        4. Save and optionally publish
        """
        
    def _check_duplicate(self, topic: Dict) -> tuple:
        """3-tier duplicate detection"""
```

### services/podcast_generator.py - Audio Content Generation

```python
class PodcastGenerator:
    """
    Generate multi-voice podcasts using ElevenLabs.
    Hosts: Alex (male, analytical) and Sarah (female, high-insight)
    """
    
    def generate_podcast_from_video(self, video_id: str, thumbnail_url: str = None) -> Dict:
        """Generate audio intelligence podcast from YouTube video"""
        
    def generate_from_article(self, article) -> Dict:
        """Generate podcast from existing Protocol Pulse article"""
        
    def _generate_dialogue_script(self, transcript: str, channel_name: str) -> List[Dict]:
        """Generate conversational dialogue script using AI"""
        
    def _synthesize_multi_voice(self, script_json: List[Dict]) -> str:
        """Synthesize multi-voice audio using ElevenLabs"""
```

### services/youtube_service.py - YouTube Monitoring

```python
class YouTubeService:
    """YouTube integration for podcast generation and reactionary articles"""
    
    PODCAST_CHANNELS = [
        {'name': 'Coin Bureau', 'id': 'UCqK_GSMbpiV8spgD3ZGloSw'},
        {'name': 'Natalie Brunell', 'id': 'UC6c1WLEK4w4qsKaIKqGptUw'},
        {'name': 'Bitcoin Magazine', 'id': 'UCni7PAlyNS0_12H-26DJJ3w'},
        {'name': 'Simply Bitcoin', 'id': 'UCNDkNyQe6ShQR3XjPPMnbvg'},
        {'name': 'Robert Breedlove', 'id': 'UCJLVQQf3LzXd7N_BuRZ3Vdw'},
        {'name': 'BTC Sessions', 'id': 'UChzLnWVsl3puKQwc5PoO6Zg'}
    ]
    
    def get_latest_video(self, channel_id: str) -> Dict:
        """Get latest video from channel for podcast generation"""
        
    def draft_reactionary_article(self, video_data: Dict) -> str:
        """Transcribe show and draft complementary review"""
```

---

## Configuration & Environment

### Required Environment Variables

```bash
# Core Application
SESSION_SECRET=your-secure-session-key
DATABASE_URL=postgresql://user:pass@host:port/dbname  # Falls back to SQLite if not set

# AI Providers (Multi-model fallback)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
XAI_API_KEY=xai-...

# Content Sources
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-secret
REDDIT_USER_AGENT=ProtocolPulse/1.0
YOUTUBE_API_KEY=AIza...

# Audio/Video Generation
ELEVENLABS_API_KEY=your-elevenlabs-key
ASSEMBLYAI_API_KEY=your-assemblyai-key

# Distribution
NOSTR_PRIVATE_KEY=nsec1...

# CRM Integration
GHL_API_KEY=pit-...
GHL_LOCATION_ID=your-location-id

# Monetization (Pending Configuration)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Database Schema Summary (Actual Tables)

| Table | Purpose |
|-------|---------|
| user | Authentication & admin access |
| article | AI-generated content with SEO |
| podcast | Audio episodes from RSS or AI-generated |
| content_prompt | Customizable AI prompt templates |
| advertisement | Native ad placements |
| automation_run | Track automation task executions |
| launch_sequence | X/Twitter distribution campaigns |
| target_alert | Target engagement opportunities |
| nostr_event | Nostr broadcast tracking |
| reply_squad_member | Monitored X accounts for engagement |
| whale_transaction | Large BTC transactions for Whale Watcher |
| bitcoin_donation | Bitcoin donations via Lightning/On-chain |

---

## Key Design Patterns

### 1. Human-in-Loop Principle

All social actions require human approval:
- Launch Console shows AI-generated tweets for review
- Target Monitor presents reply drafts for approval
- No automated posting - humans copy and paste

### 2. Editorial Accuracy Mandate

Zero tolerance for fabrication:
- All Bitcoin metrics verified against Mempool.space
- No "all-time high" claims without verification
- Ground truth data embedded in all prompts

### 3. Multi-Provider AI Fallback

```
Priority: OpenAI (GPT-4o) → Gemini → Anthropic (Claude) → Grok
```

### 4. 3-Tier Duplicate Detection

```
Tier 1: Core topic extraction
Tier 2: Keyword Jaccard similarity (threshold: 0.6)
Tier 3: Gemini semantic analysis (threshold: 0.75)
```

### 5. 5-Section Article Structure

Every article must contain:
1. TL;DR - Summary box
2. The Report - Main content
3. The Bitcoin Lens - Philosophical analysis
4. Transactor Intelligence - Actionable insights
5. Sources - Attribution

---

## File Structure

```
protocol-pulse/
├── app.py                      # Application factory
├── main.py                     # Entry point
├── models.py                   # SQLAlchemy models
├── routes.py                   # All routes & API endpoints
├── services/
│   ├── ai_service.py           # Multi-provider AI
│   ├── automation.py           # Content pipeline
│   ├── content_engine.py       # Article generation
│   ├── content_generator.py    # Generation utilities
│   ├── ghl_service.py          # HighLevel CRM
│   ├── launch_sequence.py      # X distribution
│   ├── meetup_map_service.py   # BTC Map integration
│   ├── monetization_service.py # Stripe subscriptions
│   ├── node_service.py         # Network stats
│   ├── nostr_broadcaster.py    # Nostr protocol
│   ├── podcast_generator.py    # ElevenLabs audio
│   ├── target_monitor.py       # Reply Squad
│   └── youtube_service.py      # YouTube monitoring
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── article.html
│   ├── intelligence_dashboard.html
│   ├── launch_console.html
│   ├── target_monitor.html
│   ├── meetup_map.html
│   ├── whale_watcher.html
│   └── admin/
├── static/
│   ├── css/
│   ├── js/
│   └── audio/
└── PROTOCOL_PULSE_COMPLETE_CODEBASE.md
```

---

**Last Updated:** January 26, 2026  
**Maintainer:** Protocol Pulse Development Team
