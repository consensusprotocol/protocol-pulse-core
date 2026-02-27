# Protocol Pulse - Complete Project Analysis
## For LLM Verification and Code Review

**Generated:** December 19, 2025
**Status:** Production-ready with automated article generation

---

## 1. PROJECT OVERVIEW

### What This Is
Protocol Pulse is a Web3/cryptocurrency news platform that uses AI to automatically generate and publish articles every 15 minutes. It features:
- Automated article generation using Google Gemini AI
- Live cryptocurrency prices from CoinGecko API
- Dark-themed professional CoinDesk-style design
- Admin dashboard for content management
- Substack auto-publishing integration
- Podcast aggregation from RSS feeds
- Merchandise store via Printful

### Business Model
- Automated 24/7 Bitcoin-focused news generation
- Pro-decentralization, pro-Bitcoin editorial stance
- "Walter Cronkite" authoritative journalism style
- Newsletter/Substack integration for audience building

---

## 2. TECH STACK

| Component | Technology |
|-----------|------------|
| Backend | Flask (Python 3.11) |
| Database | PostgreSQL (Neon via Replit) |
| ORM | SQLAlchemy + Flask-Migrate |
| Auth | Flask-Login |
| AI Provider | Google Gemini 2.5 Flash (primary) |
| Backup AI | Grok (xAI), OpenAI, Anthropic |
| Price Data | CoinGecko API (free) |
| Scheduler | APScheduler (BackgroundScheduler) |
| WSGI | Gunicorn |
| Frontend | Bootstrap 5, Font Awesome, Jinja2 |

---

## 3. ENVIRONMENT VARIABLES REQUIRED

```
# REQUIRED - These must be set:
DATABASE_URL          # PostgreSQL connection string (auto-provided by Replit)
GEMINI_API_KEY        # Google AI API key for article generation
SESSION_SECRET        # Flask session secret

# OPTIONAL - For additional features:
XAI_API_KEY           # Grok/xAI backup AI
OPENAI_API_KEY        # OpenAI backup AI
ANTHROPIC_API_KEY     # Claude backup AI
ELEVENLABS_API_KEY    # Text-to-speech
HEYGEN_API_KEY        # Video generation
PRINTFUL_API_KEY      # Merchandise store
SENDGRID_API_KEY      # Newsletter emails
REDDIT_CLIENT_ID      # Reddit integration
REDDIT_CLIENT_SECRET  # Reddit integration
SUBSTACK_EMAIL        # Substack auto-publishing
SUBSTACK_PASSWORD     # Substack auto-publishing
```

---

## 4. FILE STRUCTURE

```
/
├── app.py                    # Flask app initialization, DB config
├── main.py                   # Entry point with APScheduler (15-min automation)
├── models.py                 # SQLAlchemy models (User, Article, Podcast, etc.)
├── routes.py                 # All HTTP routes and API endpoints
├── routes_social.py          # Social media monitoring routes
│
├── services/
│   ├── automation.py         # Core automation logic with DB locking
│   ├── gemini_service.py     # Google Gemini AI integration
│   ├── grok_service.py       # xAI Grok integration
│   ├── ai_service.py         # Multi-AI abstraction layer
│   ├── content_generator.py  # Article generation with prompts
│   ├── content_engine.py     # Content orchestration
│   ├── price_service.py      # CoinGecko live price fetching
│   ├── reddit_service.py     # Reddit trend monitoring
│   ├── substack_service.py   # Substack publishing
│   ├── rss_service.py        # Podcast RSS aggregation
│   ├── printful_service.py   # Merchandise integration
│   └── ...other services
│
├── templates/
│   ├── base.html             # Base template with navbar/footer
│   ├── index.html            # Homepage with prices widget
│   ├── articles.html         # Article listing page
│   ├── article_detail.html   # Single article view
│   ├── podcasts.html         # Podcast listings
│   ├── merch.html            # Merchandise store
│   └── admin/                # Admin dashboard templates
│
├── static/
│   ├── css/
│   │   ├── style.css         # Main styles
│   │   └── coindesk-style.css # Professional dark theme
│   ├── js/
│   │   └── main.js           # Frontend JavaScript
│   └── images/               # Logos and assets
│
└── migrations/               # Flask-Migrate database migrations
```

---

## 5. DATABASE SCHEMA

### User
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

### Article
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    substack_url = db.Column(db.String(500))
    header_image_url = db.Column(db.String(500))
```

### AutomationRun (Prevents duplicate runs)
```python
class AutomationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # running, success, failed, skipped
    error = db.Column(db.String(500))
```

---

## 6. AUTOMATION SYSTEM (CRITICAL)

### How It Works

1. **main.py** starts APScheduler when the app boots
2. Every 15 minutes, `run_automation()` is called
3. It calls `generate_article_with_tracking()` in `services/automation.py`
4. The function:
   - Acquires a database lock (prevents duplicate runs)
   - Picks a random topic from predefined list
   - Calls Gemini AI to generate article content
   - Saves article to database with `published=True`
   - Attempts Substack publishing (non-blocking)
   - Releases the lock

### main.py (Entry Point with Scheduler)
```python
from app import app
import os
import logging
import atexit
import fcntl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

application = app
_scheduler = None
_scheduler_started = False

def start_scheduler():
    global _scheduler, _scheduler_started
    if _scheduler_started:
        return _scheduler
    
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    
    scheduler = BackgroundScheduler()
    
    def run_automation():
        try:
            with app.app_context():
                from services.automation import generate_article_with_tracking
                logger.info("=== SCHEDULED AUTOMATION TRIGGERED ===")
                result = generate_article_with_tracking()
                # ... handle result
        except Exception as e:
            logger.error(f"Automation error: {e}")
    
    scheduler.add_job(
        func=run_automation,
        trigger=IntervalTrigger(minutes=15),
        id='article_automation',
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.start()
    _scheduler = scheduler
    _scheduler_started = True
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler

def try_start_scheduler_once():
    """Use file lock to ensure only one Gunicorn worker starts scheduler"""
    lock_file = '/tmp/protocol_pulse_scheduler.lock'
    try:
        lock_fd = open(lock_file, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("Acquired scheduler lock - starting scheduler")
        start_scheduler()
    except (IOError, OSError):
        logger.info("Another worker owns the scheduler lock - skipping")

# Start scheduler on module import (works with Gunicorn)
try_start_scheduler_once()
```

### services/automation.py (Core Logic)
```python
def generate_article_with_tracking():
    with app.app_context():
        # Acquire lock to prevent duplicate execution
        run = acquire_lock()
        if not run:
            return {'skipped': True}
        
        try:
            generator = ContentGenerator()
            topic = random.choice(TOPICS)
            
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='ai_generated'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.category = article_data.get('category', 'Bitcoin')
                article.author = "Al Ingle"
                article.published = True
                article.featured = True
                db.session.add(article)
                db.session.commit()
                
                release_lock(run, 'success')
                return {'success': True, 'article_id': article.id}
            else:
                release_lock(run, 'failed', 'No article data')
                return {'success': False}
                
        except Exception as e:
            release_lock(run, 'failed', e)
            return {'success': False, 'error': str(e)}
```

---

## 7. API ENDPOINTS

### Public Routes
| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Homepage with prices and articles |
| `/articles` | GET | Article listing page |
| `/articles/<id>` | GET | Single article view |
| `/podcasts` | GET | Podcast listings |
| `/merch` | GET | Merchandise store |
| `/bitcoin` | GET | Bitcoin category articles |
| `/defi` | GET | DeFi category articles |

### API Routes
| Route | Method | Description |
|-------|--------|-------------|
| `/api/trigger-automation` | GET/POST | Manually trigger article generation |
| `/health/automation` | GET | Check automation status |
| `/api/podcast/<id>` | GET | Get podcast data |
| `/api/subscribe` | POST | Newsletter signup |

### Admin Routes (require login)
| Route | Method | Description |
|-------|--------|-------------|
| `/admin` | GET | Admin dashboard |
| `/admin/articles` | GET | Article management |
| `/admin/generate-article` | POST | Generate article manually |
| `/admin/advertisements` | GET | Ad management |

---

## 8. LIVE PRICE SERVICE

### services/price_service.py
```python
class PriceService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}
        self.cache_duration = 60  # seconds
    
    def get_prices(self):
        # Fetch BTC, ETH, SOL prices from CoinGecko
        # Returns: {'bitcoin': {'price': 87000, 'change_24h': 2.5}, ...}
        
    def format_price(self, price):
        # Returns: "$87,000" or "$2,960.50"
        
    def format_change(self, change):
        # Returns: "+2.5%" or "-1.2%"
```

Prices are fetched on every homepage load and cached for 60 seconds.

---

## 9. AI CONTENT GENERATION

### Provider Priority
1. **Gemini 2.5 Flash** (primary) - You have GEMINI_API_KEY
2. **OpenAI GPT-4** (fallback) - Requires OPENAI_API_KEY
3. **Anthropic Claude** (fallback) - Requires ANTHROPIC_API_KEY

### Content Style
- Walter Cronkite authoritative journalism
- Pro-Bitcoin, pro-decentralization stance
- Two sections: "The Report" (facts) + "The Bitcoin Lens" (philosophy)
- Clean HTML output with specific CSS classes
- TL;DR at the start of every article

---

## 10. KNOWN ISSUES / LIMITATIONS

1. **No OpenAI API Key**: Image generation service disabled (non-critical)
2. **Substack CAPTCHA**: Manual verification sometimes required for publishing
3. **No Scheduled Deployments**: User's Replit plan doesn't include this feature, so APScheduler runs in-app instead
4. **Production URL Shield**: External services can't hit `/api/trigger-automation` directly due to Replit's protection

---

## 11. HOW TO VERIFY IT'S WORKING

### Check Scheduler is Running
Look in logs for:
```
=== SCHEDULER STARTED: Articles will generate every 15 minutes ===
Next wakeup is due at 2025-12-19 17:52:12
```

### Check Last Automation Run
```bash
curl http://localhost:5000/health/automation
```
Response should show `status: healthy` with recent `last_run` timestamp.

### Check Prices are Live
Visit homepage - should show current BTC/ETH/SOL prices (not hardcoded).

### Manually Trigger Article
```bash
curl -X POST http://localhost:5000/api/trigger-automation
```
Should return:
```json
{"status":"success","message":"Article generated: ...","article_id":19}
```

---

## 12. COMPLETE FILE CONTENTS

Below are the complete contents of the most critical files for verification:

### app.py
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
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "protocol-pulse-secret-key-2025")

port = int(os.environ.get("PORT", 5000))

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

import routes
```

### Gunicorn Command (workflow)
```
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

---

## 13. SUMMARY FOR OTHER LLMs

**This is a working Flask application that:**
1. Runs on Replit with PostgreSQL database
2. Uses APScheduler to generate AI articles every 15 minutes
3. Uses Google Gemini as the primary AI for content
4. Fetches live crypto prices from CoinGecko
5. Has admin dashboard at `/admin` (requires login)
6. Publishes to Substack automatically (when CAPTCHA doesn't block)

**To verify it's working:**
1. Check logs show "SCHEDULER STARTED"
2. Hit `/health/automation` to see last run status
3. Visit homepage to see live prices
4. Wait 15 minutes and check for new article in database

**The scheduler runs inside the Flask app (not as separate cron) because Replit Scheduled Deployments are not available on this user's plan.**
