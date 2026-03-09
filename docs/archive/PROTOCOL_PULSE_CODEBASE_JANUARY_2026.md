# Protocol Pulse Complete Codebase Reference
## Generated: January 27, 2026

---

## 1. PROJECT OVERVIEW

Protocol Pulse is a world-class Bitcoin intelligence hub and Web3 media platform featuring:
- AI-powered content generation (GPT-4o, Claude, Gemini, Grok)
- Real-time Bitcoin network monitoring (Whale Watcher, Live Terminal)
- Global Bitcoin community mapping (Meetups, Merchants, ATMs)
- Launch Sequence Manager for X/Twitter distribution
- Premium Stripe monetization integration
- HighLevel CRM integration
- Nostr broadcasting capabilities

### Technology Stack
- **Backend**: Python Flask with SQLAlchemy ORM
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Bootstrap 5, Jinja2 templates, vanilla JavaScript
- **Maps**: Leaflet.js with marker clustering
- **APIs**: Mempool.space, BTCMap.org, OpenAI, Anthropic, Gemini, ElevenLabs

---

## 2. FILE STRUCTURE

```
/
├── app.py                    # Flask application factory (107 lines)
├── main.py                   # Application entry point (227 lines)
├── routes.py                 # All route definitions (2,679 lines)
├── models.py                 # Database models (164 lines)
├── replit.md                 # Project documentation
│
├── services/                 # Business logic (34 Python files)
│   ├── ai_service.py         # OpenAI/Claude integration
│   ├── automation.py         # Scheduled task automation
│   ├── clips_service.py      # Video clip processing
│   ├── content_engine.py     # Multimodal content generation
│   ├── content_generator.py  # Article generation
│   ├── elevenlabs_service.py # Voice synthesis
│   ├── gemini_service.py     # Google Gemini integration
│   ├── ghl_service.py        # HighLevel CRM integration
│   ├── grok_service.py       # xAI Grok integration
│   ├── heygen_service.py     # Avatar video generation
│   ├── image_service.py      # Image generation
│   ├── launch_sequence.py    # X/Twitter post management
│   ├── meetup_map_service.py # Bitcoin meetups worldwide
│   ├── monetization_service.py # Stripe/premium features
│   └── ... (20+ more services)
│
├── templates/                # Jinja2 HTML templates (40 files)
│   ├── base.html             # Base template with navigation
│   ├── index.html            # Homepage with dashboard
│   ├── articles.html         # Article listing
│   ├── whale_watcher.html    # Whale transaction monitor
│   ├── meetup_map.html       # Global Bitcoin meetups
│   ├── merchant_map.html     # Bitcoin merchants worldwide
│   ├── live_terminal.html    # Real-time Bitcoin data
│   ├── dashboard.html        # Admin dashboard
│   └── ...
│
├── static/
│   ├── js/
│   │   ├── main.js           # Core JavaScript
│   │   └── coindesk.js       # Price widget
│   └── css/
│       └── style.css         # Custom styles
│
└── PROTOCOL_PULSE_COMPLETE_CODEBASE.md  # Previous documentation
```

---

## 3. DATABASE MODELS (models.py)

### User Model
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    newsletter_subscribed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Article Model
```python
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    author = db.Column(db.String(100), default="Protocol Pulse AI")
    category = db.Column(db.String(50), default="Web3")
    tags = db.Column(db.String(500))
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))  # reddit, ai_generated, manual
    featured = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    header_image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
```

### Podcast Model
```python
class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    host = db.Column(db.String(100))
    episode_number = db.Column(db.Integer)
    duration = db.Column(db.String(20))
    audio_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
```

### LaunchSequence Model (X/Twitter Distribution)
```python
class LaunchSequence(db.Model):
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
    status = db.Column(db.String(50), default='draft')
    tweet_id = db.Column(db.String(100))
    total_engagement = db.Column(db.Integer, default=0)
```

### TargetAlert Model (Reply Squad)
```python
class TargetAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(50))  # reply_squad, trending, partner
    source_url = db.Column(db.String(500))
    source_account = db.Column(db.String(100))
    content_snippet = db.Column(db.Text)
    priority = db.Column(db.Integer, default=2)
    strategy_suggested = db.Column(db.String(100))
    draft_replies = db.Column(db.Text)  # JSON array
    status = db.Column(db.String(50), default='pending')
```

### WhaleTransaction Model
```python
class WhaleTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txid = db.Column(db.String(100), unique=True, nullable=False)
    btc_amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float)
    fee_sats = db.Column(db.Integer)
    block_height = db.Column(db.Integer)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_mega = db.Column(db.Boolean, default=False)  # 1000+ BTC
```

### Additional Models
- **ContentPrompt**: AI prompt templates
- **Advertisement**: Ad placement management
- **AutomationRun**: Task scheduling logs
- **NostrEvent**: Nostr broadcast tracking
- **ReplySquadMember**: Engagement target accounts
- **BitcoinDonation**: Lightning/on-chain donations

---

## 4. KEY ROUTES (routes.py - 2,679 lines)

### Public Routes
```
GET /                         # Homepage with live Bitcoin data
GET /articles                 # Article listing
GET /article/<id>             # Single article view
GET /podcasts                 # Podcast directory
GET /whale-watcher            # Real-time whale monitoring
GET /meetup-map               # Global Bitcoin meetups (75+)
GET /map                      # Bitcoin merchants worldwide (Sovereign Merchant Map)
GET /live-terminal            # Live settlement terminal
GET /scorecard                # Sovereign security quiz
GET /clips                    # Signal clips gallery
```

### API Routes
```
GET /api/whales/live          # Live whale transactions (10+ BTC)
GET /api/whales               # Historical whale data
GET /api/bitcoin/stats        # Network statistics
GET /api/meetups              # Bitcoin meetup data
GET /api/merchants            # Merchant locations
```

### Admin Routes
```
GET /admin                    # Admin dashboard
GET /admin/articles           # Article management
GET /admin/generate-article   # AI article generation
GET /admin/launch-sequence    # X/Twitter post management
GET /admin/target-monitor     # Reply Squad alerts
GET /admin/nostr              # Nostr broadcaster
```

---

## 5. SERVICES DOCUMENTATION

### meetup_map_service.py (34,914 bytes)
Global Bitcoin meetup database with 75+ verified locations:

**Regions Covered:**
- North America (28 meetups): Austin, Miami, NYC, SF, Nashville, Chicago, LA, Seattle, Denver, Boston, Phoenix, Atlanta, Dallas, Houston, Portland, Las Vegas, San Diego, Raleigh, Salt Lake City, Minneapolis, Naples, Toronto, Vancouver, Montreal, Calgary, Ottawa, Mexico City, Guadalajara
- Latin America (12 meetups): El Salvador, Bitcoin Beach, Buenos Aires, São Paulo, Rio, Bogotá, Santiago, Lima, Caracas, San José, Guatemala City, Panama City
- Europe (24 meetups): London, Amsterdam, Paris, Berlin, Munich, Zurich, Vienna, Brussels, Dublin, Lisbon, Madrid, Barcelona, Milan, Rome, Frankfurt, Stockholm, Oslo, Copenhagen, Helsinki, Prague, Warsaw, Budapest, Bucharest, Tallinn
- Asia (13 meetups): Tokyo, Singapore, Hong Kong, Seoul, Bangkok, Manila, Taipei, Jakarta, Kuala Lumpur, Ho Chi Minh City, Bangalore, Mumbai, Delhi
- Middle East (3 meetups): Dubai, Tel Aviv, Riyadh
- Oceania (5 meetups): Sydney, Melbourne, Brisbane, Auckland, Perth
- Africa (7 meetups): Lagos, Nairobi, Cape Town, Johannesburg, Accra, Cairo, Addis Ababa

**Key Methods:**
```python
get_bitcoin_meetups()           # Returns all 75+ meetups
get_meetups_by_region(region)   # Filter by region
get_meetup_stats()              # Aggregate statistics
get_merchants_by_bounds()       # BTCMap.org integration
get_bitcoin_atms()              # ATM locations
```

### ai_service.py
Multi-provider AI integration:
- OpenAI GPT-4o for content generation
- Anthropic Claude for alternative analysis
- Configurable model selection
- Token optimization

### content_generator.py (31,965 bytes)
Article generation with enforced structure:
1. TL;DR section
2. The Report (main content)
3. The Bitcoin Lens (Bitcoin-centric analysis)
4. Transactor Intelligence (actionable insights)
5. Sources

### launch_sequence.py (13,563 bytes)
X/Twitter distribution automation:
- Primary post copy generation
- Thread reply sequences
- Quote variants for retweets
- Reply draft templates
- Velocity prediction scoring

### ghl_service.py (14,270 bytes)
HighLevel CRM integration:
- Subscriber synchronization
- Bitcoin network metrics push
- Daily intel briefing automation

---

## 6. FRONTEND TEMPLATES

### base.html
- Responsive navigation with Bootstrap 5
- Dark theme with Protocol Pulse branding
- EST network time display (live updating)
- 2028 halving countdown clock
- Gas/fee alert system
- Footer with quick links

### index.html (Homepage)
- Hero section: "Sovereign Intelligence. Real-Time Signal."
- Live Bitcoin price and network stats
- Featured articles carousel
- Hashrate chart visualization
- Difficulty adjustment gauge
- Quick access to all features

### whale_watcher.html
- Real-time whale transaction monitoring
- Minimum threshold: 10+ BTC
- Mega whale highlighting (100+ BTC)
- Live price integration
- Transaction details with Mempool links

### meetup_map.html
- Leaflet.js interactive world map
- Marker clustering for performance
- Region filter buttons (7 regions)
- Sidebar with meetup list
- Click-to-fly navigation
- Statistics bar (75+ meetups, 60K+ members)

### merchant_map.html (Upgraded January 2026)
- Full-screen interactive map
- Sidebar with merchant list
- Category filtering (Food, Retail, Lodging, ATM, Lightning)
- Real-time BTCMap.org integration
- Lightning network indicators
- Mobile-responsive panel

---

## 7. ENVIRONMENT VARIABLES

### Required Secrets
```
DATABASE_URL              # PostgreSQL connection string
OPENAI_API_KEY           # OpenAI GPT-4o access
ANTHROPIC_API_KEY        # Claude Sonnet access
GEMINI_API_KEY           # Google Gemini access
XAI_API_KEY              # Grok integration
ELEVENLABS_API_KEY       # Voice synthesis
HEYGEN_API_KEY           # Avatar video generation
ASSEMBLYAI_API_KEY       # Audio transcription
STRIPE_SECRET_KEY        # Payment processing
STRIPE_WEBHOOK_SECRET    # Stripe webhooks
GHL_API_KEY              # HighLevel CRM
GHL_LOCATION_ID          # HighLevel location
REDDIT_CLIENT_ID         # Reddit API
REDDIT_CLIENT_SECRET     # Reddit API
YOUTUBE_API_KEY          # YouTube monitoring
```

### Optional Secrets
```
NOSTR_PRIVATE_KEY        # Nostr broadcasting
SENDGRID_API_KEY         # Email delivery
SLACK_BOT_TOKEN          # Slack integration
```

---

## 8. RECENT CHANGES (January 2026)

### January 27, 2026
1. **EST Time Display**: Added live EST network time in footer
2. **Meetup URLs Fixed**: Verified and updated all 75+ meetup URLs with correct lowercase format
3. **Naples Bitcoin + Blockchain Meetup Added**: https://www.meetup.com/naples-bitcoin-blockchain-group/
4. **Merchant Map Upgraded**: 
   - Added sidebar with merchant list
   - Category filtering (Food, Retail, Lodging, ATM, Lightning)
   - Marker clustering for performance
   - Mobile-responsive design
   - Lightning network highlighting

### January 26, 2026
1. **Whale Watcher Fix**: Created /api/whales/live endpoint scanning Mempool.space
2. **Meetup Map Enhancement**: Expanded from 10 to 75+ worldwide meetups
3. **Hero Section Update**: "Sovereign Intelligence. Real-Time Signal."

---

## 9. API ENDPOINTS REFERENCE

### Whale Watcher API
```
GET /api/whales/live
Response: {
    "whales": [
        {
            "txid": "abc123...",
            "btc": 512.95,
            "fee": 15000,
            "time": 1706340000000,
            "status": "confirmed",
            "block": 879234
        }
    ],
    "min_btc": 10,
    "count": 5
}
```

### Bitcoin Stats API
```
GET /api/bitcoin/stats
Response: {
    "price": 104500,
    "blockHeight": 879234,
    "difficulty": "146.47T",
    "hashrate": "1046 EH/s",
    "mempoolSize": 45000,
    "fees": {
        "fastest": 25,
        "halfHour": 18,
        "hour": 12
    }
}
```

---

## 10. DEPLOYMENT

### Running Locally
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Production
- Hosted on Replit with automatic scaling
- PostgreSQL database (Neon-backed)
- Environment secrets managed via Replit Secrets
- Automatic HTTPS via Replit

---

## 11. DESIGN PATTERNS

### Human-in-the-Loop
All AI-generated content requires editorial approval before publishing.

### Editorial Accuracy Mandate
5-section article structure enforced with validation and auto-retry.

### 3-Tier Duplicate Detection
1. Title similarity check
2. Content hash comparison
3. Source URL matching

---

*Document generated by Protocol Pulse AI System*
*Last updated: January 27, 2026*
