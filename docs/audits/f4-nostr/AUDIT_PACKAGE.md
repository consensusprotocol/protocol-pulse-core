# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: f4-nostr
# Branch: feature/f4-nostr
# Generated: 2026-03-09 02:39 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
Nostr is the censorship-resistant social protocol that Bitcoin's cypherpunk
community has adopted. Protocol Pulse monitors Nostr for Bitcoin signal,
scores content by engagement and quality, surfaces the best content on the
platform, and publishes Protocol Pulse's own content to Nostr automatically.

Two deliverables:
1. **nostr_monitor.py** — backend service that connects to Nostr relays,
   subscribes to Bitcoin topics, scores content, stores in DB
2. **/nostr onboarding page** — public-facing page explaining Nostr +
   showing live top Nostr content from our monitor

---

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS

### LAW 1: Engagement scoring formula is fixed
```
ENGAGEMENT_SCORE = (
    zaps * 10 +        # Bitcoin payments = strongest signal
    quotes * 5 +       # Quoted reposts = editorial endorsement
    reposts * 3 +      # Simple reposts = amplification
    replies * 2 +      # Conversation = engagement
    reactions * 1      # Likes/reactions = passive appreciation
)
```

### LAW 2: Approved relay list (use all 4, failover gracefully)
```python
NOSTR_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://relay.primal.net"
]
```
If a relay disconnects, reconnect with exponential backoff (1s, 2s, 4s, max 60s).
Never crash on relay disconnect.

### LAW 3: Bitcoin signal filter — only track relevant content
Subscribe to NIP-01 events with these filter criteria:
```json
{"kinds": [1, 30023], "#t": ["bitcoin", "btc", "lightning", "nostr", "sovereignty"]}
```
Also monitor specific high-signal pubkeys (seed list — update as community grows).

### LAW 4: nostr_monitor.py runs as asyncio, not threads
- Single event loop, websockets library for relay connections
- 4 concurrent websocket connections (one per relay)
- Event deduplication by event ID before scoring
- Max queue depth: 1000 events in memory — flush to DB every 60s

### LAW 5: Protocol Pulse publishes to Nostr
- Every new article published on PP → auto-post to Nostr (NIP-23 long-form)
- Every daily video published → auto-post to Nostr (NIP-1 short note with link)
- PP Nostr identity: generate keypair once, store in .env as NOSTR_PRIVATE_KEY
- DO NOT post more than 10 times per day from PP account (avoid spam reputation)

---



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: app.py (313 lines)
```
   1 | import os
   2 | from pathlib import Path
   3 | from dotenv import load_dotenv
   4 | # Load .env from the same directory as this file (core/) so it works from any cwd
   5 | load_dotenv(Path(__file__).resolve().parent / ".env")
   6 | 
   7 | import logging
   8 | import json
   9 | import random
  10 | from flask import Flask, session
  11 | from flask_sqlalchemy import SQLAlchemy
  12 | from flask_migrate import Migrate
  13 | from sqlalchemy.orm import DeclarativeBase
  14 | from flask_login import LoginManager
  15 | from flask_limiter import Limiter
  16 | from flask_limiter.util import get_remote_address
  17 | try:
  18 |     from flask_socketio import SocketIO
  19 | except ImportError:
  20 |     SocketIO = None
  21 | try:
  22 |     from flask_caching import Cache
  23 |     _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
  24 | except ImportError:
  25 |     _cache = None
  26 | 
  27 | # Configure logging (default info; keep noisy transport libs quiet).
  28 | logging.basicConfig(level=logging.INFO)
  29 | logging.getLogger("urllib3").setLevel(logging.WARNING)
  30 | logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
  31 | logging.getLogger("requests").setLevel(logging.WARNING)
  32 | logging.getLogger("werkzeug").setLevel(logging.INFO)
  33 | 
  34 | class Base(DeclarativeBase):
  35 |     pass
  36 | 
  37 | # 1. Initialize DB WITHOUT app first to prevent circular loops
  38 | db = SQLAlchemy(model_class=Base)
  39 | 
  40 | # 2. Create the app instance — use absolute paths so templates/static are always found
  41 | #    whether run as "app:app" from core/ or "core.app:app" from project root
  42 | _core_dir = Path(__file__).resolve().parent
  43 | app = Flask(__name__, template_folder=str(_core_dir / "templates"), static_folder=str(_core_dir / "static"))
  44 | 
  45 | # Security: Uses .env secret, but provides a fallback for local dev
  46 | app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_protocol_pulse_2026")
  47 | 
  48 | # Public network endpoints (local by default, cloudflared-ready when set in .env)
  49 | app.config["PUBLIC_HUB_URL"] = os.environ.get("PUBLIC_HUB_URL", "http://127.0.0.1:5000").rstrip("/")
  50 | app.config["PUBLIC_AI_URL"] = os.environ.get("PUBLIC_AI_URL", "http://127.0.0.1:11434").rstrip("/")
  51 | app.config["PUBLIC_SSH_HOST"] = os.environ.get("PUBLIC_SSH_HOST", "").strip()
  52 | app.config["USE_DOUBLE_PIPE"] = os.environ.get("USE_DOUBLE_PIPE", "false").strip().lower() in {
  53 |     "1", "true", "yes", "on"
  54 | }
  55 | 
  56 | # Configure the database
  57 | database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
  58 | # Replit (and some Heroku-style hosts) emit postgres:// — SQLAlchemy 1.4+ requires postgresql://
  59 | if database_url.startswith("postgres://"):
  60 |     database_url = database_url.replace("postgres://", "postgresql://", 1)
  61 | if database_url.startswith("sqlite:"):
  62 |     # SQLite: remove unsupported charset param added by older code
  63 |     if "charset=utf8mb4" in database_url:
  64 |         database_url = database_url.replace("?charset=utf8mb4", "").replace("&charset=utf8mb4", "")
  65 | 
  66 | app.config["SQLALCHEMY_DATABASE_URI"] = database_url
  67 | app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
  68 |     "pool_recycle": 300,
  69 |     "pool_pre_ping": True,
  70 | }
  71 | 
  72 | # Startup env diagnostics (warnings only; never hard-crash startup).
  73 | _required_env = ["SESSION_SECRET", "DATABASE_URL"]
  74 | _recommended_env = [
  75 |     "TWITTER_API_KEY",
  76 |     "TWITTER_API_SECRET",
  77 |     "TWITTER_ACCESS_TOKEN",
  78 |     "TWITTER_ACCESS_TOKEN_SECRET",
  79 | ]
  80 | for _name in _required_env:
  81 |     if not os.environ.get(_name):
  82 |         logging.warning("%s missing; using fallback/default where available.", _name)
  83 | for _name in _recommended_env:
  84 |     if not os.environ.get(_name):
  85 |         logging.info("%s not configured (related integration stays degraded/off).", _name)
  86 | 
  87 | app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 1 day default for send_file
  88 | 
  89 | # 3. Initialize extensions
  90 | db.init_app(app)
  91 | migrate = Migrate(app, db)
  92 | login_manager = LoginManager()
  93 | login_manager.init_app(app)
  94 | login_manager.login_view = "login"
  95 | 
  96 | limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
  97 | limiter.init_app(app)
  98 | 
  99 | if _cache is not None:
 100 |     _cache.init_app(app)
 101 |     cache = _cache
 102 | else:
 103 |     class _NullCache:
 104 |         def init_app(self, app): pass
 105 |         def cached(self, timeout=None, key_prefix=None):
 106 |             def decorator(f): return f
 107 |             return decorator
 108 |     cache = _NullCache()
 109 | 
 110 | if SocketIO is not None:
 111 |     socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
 112 | else:
 113 |     socketio = None
 114 | 
 115 | @app.context_processor
 116 | def inject_csrf():
 117 |     """Inject CSRF token for forms. Generate once per session."""
 118 |     if "csrf_token" not in session:
 119 |         session["csrf_token"] = os.urandom(32).hex()
 120 |     return {
 121 |         "csrf_token": session.get("csrf_token"),
 122 |         "public_hub_url": app.config.get("PUBLIC_HUB_URL"),
 123 |         "public_ai_url": app.config.get("PUBLIC_AI_URL"),
 124 |         "public_ssh_host": app.config.get("PUBLIC_SSH_HOST"),
 125 |         "use_double_pipe": app.config.get("USE_DOUBLE_PIPE", False),
 126 |     }
 127 | 
 128 | 
 129 | @app.after_request
 130 | def add_headers(response):
 131 |     """Add cache, security, and performance headers to every response."""
 132 |     from flask import request
 133 | 
 134 |     # ── Security headers ──
 135 |     response.headers["X-Content-Type-Options"] = "nosniff"
 136 |     response.headers["X-Frame-Options"] = "SAMEORIGIN"
 137 |     response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
 138 |     response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
 139 |     response.headers["X-XSS-Protection"] = "1; mode=block"
 140 | 
 141 |     # ── Cache strategy ──
 142 |     if request.path.startswith("/static/"):
 143 |         # Versioned assets (?v=X) get long cache; images get 1 week; CSS/JS get 1 day
 144 |         if any(request.path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')):
 145 |             response.cache_control.max_age = 604800  # 1 week
 146 |             response.cache_control.public = True
 147 |         elif any(request.path.endswith(ext) for ext in ('.css', '.js')):
 148 |             response.cache_control.max_age = 86400  # 1 day
 149 |             response.cache_control.public = True
 150 |         else:
 151 |             response.cache_control.max_age = 86400
 152 |             response.cache_control.public = True
 153 |     elif request.path.startswith("/api/"):
 154 |         # API endpoints: short cache
 155 |         if "Cache-Control" not in response.headers:
 156 |             response.cache_control.max_age = 60
 157 |             response.cache_control.public = True
 158 |     else:
 159 |         # HTML pages: no-cache but allow revalidation
 160 |         if "Cache-Control" not in response.headers:
 161 |             response.headers["Cache-Control"] = "public, no-cache, must-revalidate"
 162 | 
 163 |     return response
 164 | 
 165 | 
 166 | # 4. Define Template Filters
 167 | @app.template_filter('inject_ads')
 168 | def inject_ads(content):
 169 |     import models
 170 |     try:
 171 |         active_ads = models.Advertisement.query.filter_by(is_active=True).all()
 172 |         if not active_ads:
 173 |             return content
 174 |         ad = random.choice(active_ads)
 175 |         ad_html = f'''
 176 |         <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
 177 |             <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
 178 |             <a href="/ads/go/{ad.id}" rel="noopener" class="text-decoration-none">
 179 |                 <img src="{ad.image_url}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{ad.name}">
 180 |                 <p class="mb-0 text-white fw-bold">{ad.name}</p>
 181 |             </a>
 182 |         </div>
 183 |         '''
 184 |         parts = content.split('</p>', 2)
 185 |         if len(parts) > 2:
 186 |             return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
 187 |         return content + ad_html
 188 |     except Exception as e:
 189 |         logging.warning(f"Ad injection failed: {e}")
 190 |         return content
 191 | 
 192 | @app.template_filter('basename')
 193 | def basename_filter(path):
 194 |     """Return the basename of a path for use in templates (e.g. clip filename)."""
 195 |     if not path:
 196 |         return ""
 197 |     return os.path.basename(str(path).strip())
 198 | 
 199 | @app.template_filter('from_json')
 200 | def from_json_filter(value):
 201 |     if not value:
 202 |         return []
 203 |     try:
 204 |         return json.loads(value)
 205 |     except (json.JSONDecodeError, TypeError):
 206 |         return []
 207 | 
 208 | # Distinct header image per article: when stored URL is missing or the old single default, use pool by title
 209 | _OLD_SINGLE_DEFAULT_HEADER = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"
 210 | 
 211 | @app.template_filter('article_header_display')
 212 | def article_header_display_filter(article):
 213 |     """Return a distinct header image URL for this article (avoids same image on every card)."""
 214 |     if article is None:
 215 |         return _OLD_SINGLE_DEFAULT_HEADER
 216 |     stored = (getattr(article, "header_image_url", None) or "").strip()
 217 |     if stored and stored != _OLD_SINGLE_DEFAULT_HEADER:
 218 |         return stored
 219 |     return "/static/images/default-header.png"
 220 | 
 221 | # 5. User loader for Flask-Login
 222 | @login_manager.user_loader
 223 | def load_user(user_id):
 224 |     import models
 225 |     return models.User.query.get(int(user_id))
 226 | 
 227 | # =====================================
 228 | # THE IGNITION ZONE (CRITICAL ORDER)
 229 | # =====================================
 230 | # When we run as python app.py, __name__ is "__main__". Later, "import routes" does
 231 | # "from app import app", which loads this file again as module "app" (a second Flask
 232 | # app). Routes then register on that second app, but we call app.run() on this one → 404.
 233 | # So make "app" resolve to this same module when we are the main script.
 234 | if __name__ == "__main__":
 235 |     import sys
 236 |     sys.modules["app"] = sys.modules["__main__"]
 237 | 
 238 | with app.app_context():
 239 |     # 1. Load the models into memory first
 240 |     import models
 241 |     # Create any missing tables at startup (idempotent — safe to always run).
 242 |     # Set ENABLE_RUNTIME_DB_CREATE_ALL=false to suppress on managed migration envs.
 243 |     if os.environ.get("ENABLE_RUNTIME_DB_CREATE_ALL", "true").strip().lower() not in {"0", "false", "no", "off"}:
 244 |         try:
 245 |             db.create_all()
 246 |         except Exception as _dbe:
 247 |             logging.warning("db.create_all() failed (non-fatal): %s", _dbe)
 248 | 
 249 | def _run_dev_server():
 250 |     port = 5000
 251 |     host = "0.0.0.0"
 252 |     print(f"Starting Protocol Pulse -> http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
 253 |     # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
 254 |     if socketio is not None:
 255 |         socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
 256 |     else:
 257 |         app.run(host=host, port=port, debug=False, use_reloader=False)
 258 | 
 259 | # Keep routes import near the very bottom so the app object and extensions are fully initialized first.
 260 | import routes
 261 | from routes_api_v2 import api_v2
 262 | try:
 263 |     from routes_api_terminal import terminal_bp
 264 |     app.register_blueprint(terminal_bp)
 265 | except Exception as e:
 266 |     print(f'Terminal API not loaded: {e}')
 267 | try:
 268 |     from routes_commander import commander_bp
 269 |     app.register_blueprint(commander_bp)
 270 |     import logging; logging.info("Commander API blueprint registered at /api/v1")
 271 | except Exception as _e:
 272 |     import logging; logging.warning("Commander blueprint not loaded: %s", _e)
 273 | try:
 274 |     from routes_newsletter_trigger import newsletter_trigger_bp
 275 |     app.register_blueprint(newsletter_trigger_bp)
 276 | except Exception as e:
 277 |     print(f'Newsletter trigger not loaded: {e}')
 278 | app.register_blueprint(api_v2)
 279 | from onboarding_routes import onboarding_bp
 280 | app.register_blueprint(onboarding_bp)
 281 | 
 282 | from oracle_routes import oracle_bp
 283 | app.register_blueprint(oracle_bp)
 284 | 
 285 | try:
 286 |     from services.video_engine.dashboard.app import dashboard_bp
 287 |     app.register_blueprint(dashboard_bp)
 288 |     logging.info("Dashboard blueprint registered at /dashboard/")
 289 | except ImportError as _e:
 290 |     logging.warning("Dashboard blueprint not loaded: %s", _e)
 291 | 
 292 | # Start background APScheduler only when explicitly enabled for this process.
 293 | if os.environ.get("ENABLE_APSCHEDULER", "false").strip().lower() in {"1", "true", "yes", "on"}:
 294 |     try:
 295 |         from services.scheduler import initialize_scheduler
 296 |         _sch = initialize_scheduler()
 297 |         logging.info("Scheduler initialized: %s", _sch)
 298 |     except Exception as _e:
 299 |         logging.warning("Scheduler init skipped: %s", _e)
 300 | 
 301 | # Diagnose after routes import so startup logs reflect the real routing table.
 302 | try:
 303 |     rules = [r.rule for r in app.url_map.iter_rules()]
 304 |     has_root = "/" in rules
 305 |     logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
 306 |     if not has_root:
 307 |         logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
 308 | except Exception as e:
 309 |     logging.warning("Could not list routes: %s", e)
 310 | 
 311 | if __name__ == "__main__":
 312 |     _run_dev_server()
 313 | 
```

### File: core/models.py (979 lines)
```
   1 | from datetime import datetime, timedelta
   2 | from flask_login import UserMixin
   3 | from werkzeug.security import generate_password_hash, check_password_hash
   4 | from app import db  # This stays here; we will fix the 'loop' in app.py
   5 | 
   6 | # =====================================
   7 | # USER & OPERATIVE MODELS
   8 | # =====================================
   9 | 
  10 | class User(UserMixin, db.Model):
  11 |     id = db.Column(db.Integer, primary_key=True)
  12 |     username = db.Column(db.String(80), unique=True, nullable=False)
  13 |     email = db.Column(db.String(120), unique=True, nullable=False)
  14 |     password_hash = db.Column(db.String(256))
  15 |     is_admin = db.Column(db.Boolean, default=False)
  16 |     newsletter_subscribed = db.Column(db.Boolean, default=False)
  17 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
  18 |     
  19 |     operative_rank = db.Column(db.Integer, default=1)
  20 |     drill_completions = db.Column(db.Integer, default=0)
  21 |     brief_clicks = db.Column(db.Integer, default=0)
  22 |     operative_slug = db.Column(db.String(100), unique=True)
  23 |     crm_synced_at = db.Column(db.DateTime)
  24 |     last_drill_at = db.Column(db.DateTime)
  25 |     last_brief_at = db.Column(db.DateTime)
  26 |     
  27 |     # Premium subscription (free | operator | commander | sovereign)
  28 |     subscription_tier = db.Column(db.String(30), default='free')
  29 |     stripe_customer_id = db.Column(db.String(120))
  30 |     stripe_subscription_id = db.Column(db.String(120))
  31 |     subscription_expires_at = db.Column(db.DateTime)
  32 |     # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
  33 |     mega_whale_email_alerts = db.Column(db.Boolean, default=False)
  34 |     
  35 |     # --- Auth Methods ---
  36 |     def set_password(self, password):
  37 |         self.password_hash = generate_password_hash(password)
  38 | 
  39 |     def check_password(self, password):
  40 |         return check_password_hash(self.password_hash, password)
  41 | 
  42 |     # --- Operative Logic ---
  43 |     def get_rank_name(self):
  44 |         if self.operative_rank >= 3:
  45 |             return 'SOVEREIGN ELITE'
  46 |         elif self.operative_rank >= 2:
  47 |             return 'OPERATIVE'
  48 |         return 'RECRUIT'
  49 |     
  50 |     def check_rank_progression(self):
  51 |         if self.drill_completions >= 5 and self.brief_clicks >= 10:
  52 |             self.operative_rank = 3
  53 |         elif self.drill_completions >= 1:
  54 |             self.operative_rank = 2
  55 |         else:
  56 |             self.operative_rank = 1
  57 |     
  58 |     def generate_operative_slug(self):
  59 |         import hashlib
  60 |         import time
  61 |         if not self.operative_slug:
  62 |             base = self.username.lower().replace(' ', '-')[:20]
  63 |             unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
  64 |             self.operative_slug = f"{base}-{unique_hash}"
  65 |         return self.operative_slug
  66 |     
  67 |     def can_increment_drill(self):
  68 |         if not self.last_drill_at:
  69 |             return True
  70 |         cooldown = datetime.utcnow() - self.last_drill_at
  71 |         return cooldown.total_seconds() >= 300
  72 |     
  73 |     def can_increment_brief(self):
  74 |         if not self.last_brief_at:
  75 |             return True
  76 |         cooldown = datetime.utcnow() - self.last_brief_at
  77 |         return cooldown.total_seconds() >= 60
  78 |     
  79 |     def has_premium(self):
  80 |         """True if user has any paid tier (operator, commander, sovereign)."""
  81 |         tier = getattr(self, 'subscription_tier', None)
  82 |         return tier and tier != 'free'
  83 | 
  84 |     def has_commander_tier(self):
  85 |         """True if user has $99/mo Commander (or higher) tier."""
  86 |         tier = getattr(self, 'subscription_tier', None)
  87 |         return tier in ('commander', 'sovereign')
  88 | 
  89 | # =====================================
  90 | # CONTENT & INTELLIGENCE MODELS
  91 | # =====================================
  92 | 
  93 | class Article(db.Model):
  94 |     __tablename__ = "articles"
  95 |     id = db.Column(db.Integer, primary_key=True)
  96 |     title = db.Column(db.String(200), nullable=False)
  97 |     content = db.Column(db.Text, nullable=False)
  98 |     summary = db.Column(db.Text)
  99 |     author = db.Column(db.String(100), default="Protocol Pulse AI")
 100 |     category = db.Column(db.String(50), default="Web3")
 101 |     tags = db.Column(db.String(500))
 102 |     source_url = db.Column(db.String(500))
 103 |     source_type = db.Column(db.String(50))
 104 |     featured = db.Column(db.Boolean, default=False)
 105 |     published = db.Column(db.Boolean, default=False)
 106 |     # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
 107 |     premium_tier = db.Column(db.String(30), default=None)
 108 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 109 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 110 |     seo_title = db.Column(db.String(200))
 111 |     seo_description = db.Column(db.String(300))
 112 |     substack_url = db.Column(db.String(500))
 113 |     header_image_url = db.Column(db.String(500))
 114 |     screenshot_url = db.Column(db.String(500))
 115 |     video_url = db.Column(db.String(500))
 116 | 
 117 | class Podcast(db.Model):
 118 |     id = db.Column(db.Integer, primary_key=True)
 119 |     title = db.Column(db.String(200), nullable=False)
 120 |     description = db.Column(db.Text)
 121 |     host = db.Column(db.String(100))
 122 |     episode_number = db.Column(db.Integer)
 123 |     duration = db.Column(db.String(20))
 124 |     audio_url = db.Column(db.String(500))
 125 |     cover_image_url = db.Column(db.String(500))
 126 |     published_date = db.Column(db.DateTime, default=datetime.utcnow)
 127 |     featured = db.Column(db.Boolean, default=False)
 128 |     category = db.Column(db.String(50), default="Web3")
 129 |     rss_source = db.Column(db.String(100))
 130 | 
 131 | class ContentPrompt(db.Model):
 132 |     id = db.Column(db.Integer, primary_key=True)
 133 |     name = db.Column(db.String(100), nullable=False)
 134 |     prompt_text = db.Column(db.Text, nullable=False)
 135 |     category = db.Column(db.String(50))
 136 |     active = db.Column(db.Boolean, default=True)
 137 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 138 | 
 139 | class Advertisement(db.Model):
 140 |     id = db.Column(db.Integer, primary_key=True)
 141 |     name = db.Column(db.String(150), nullable=False)
 142 |     image_url = db.Column(db.String(300), nullable=False)
 143 |     target_url = db.Column(db.String(300), nullable=False)
 144 |     is_active = db.Column(db.Boolean, default=False)
 145 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 146 | 
 147 | 
 148 | class AffiliateProduct(db.Model):
 149 |     """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
 150 |     __tablename__ = 'affiliate_product'
 151 |     id = db.Column(db.Integer, primary_key=True)
 152 |     name = db.Column(db.String(200), nullable=False)
 153 |     product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
 154 |     product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
 155 |     affiliate_url = db.Column(db.String(500))
 156 |     category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
 157 |     short_description = db.Column(db.String(500))
 158 |     active = db.Column(db.Boolean, default=True)
 159 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 160 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 161 | 
 162 | 
 163 | class AffiliateProductClick(db.Model):
 164 |     """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
 165 |     __tablename__ = 'affiliate_product_click'
 166 |     id = db.Column(db.Integer, primary_key=True)
 167 |     product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
 168 |     link_type = db.Column(db.String(50))  # amazon, trezor, etc.
 169 |     page_path = db.Column(db.String(500))
 170 |     session_id = db.Column(db.String(64))
 171 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 172 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 173 | 
 174 | 
 175 | # =====================================
 176 | # AUTOMATION & LOGISTICS
 177 | # =====================================
 178 | 
 179 | class AutomationRun(db.Model):
 180 |     id = db.Column(db.Integer, primary_key=True)
 181 |     task_name = db.Column(db.String(100), nullable=False)
 182 |     started_at = db.Column(db.DateTime, nullable=False)
 183 |     finished_at = db.Column(db.DateTime)
 184 |     status = db.Column(db.String(20))
 185 |     error = db.Column(db.String(500))
 186 | 
 187 | class LaunchSequence(db.Model):
 188 |     id = db.Column(db.Integer, primary_key=True)
 189 |     content_id = db.Column(db.Integer)
 190 |     content_type = db.Column(db.String(50))
 191 |     primary_post_copy = db.Column(db.Text)
 192 |     thread_replies = db.Column(db.Text)
 193 |     quote_variants = db.Column(db.Text)
 194 |     reply_drafts = db.Column(db.Text)
 195 |     hashtags = db.Column(db.String(500))
 196 |     posting_time = db.Column(db.Time)
 197 |     velocity_prediction = db.Column(db.Float)
 198 |     first_reply_link = db.Column(db.String(500))
 199 |     call_to_action = db.Column(db.String(300))
 200 |     status = db.Column(db.String(50), default='draft')
 201 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 202 |     approved_at = db.Column(db.DateTime)
 203 |     published_at = db.Column(db.DateTime)
 204 |     tweet_id = db.Column(db.String(100))
 205 |     actual_velocity_score = db.Column(db.Float)
 206 |     replies_first_5min = db.Column(db.Integer, default=0)
 207 |     total_engagement = db.Column(db.Integer, default=0)
 208 |     reached_for_you = db.Column(db.Boolean, default=False)
 209 |     dispatch_window = db.Column(db.String(20))
 210 |     dispatch_timezone = db.Column(db.String(50), default='America/New_York')
 211 |     persona_debate = db.Column(db.Text)
 212 |     is_autonomous = db.Column(db.Boolean, default=False)
 213 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 214 |     ground_truth = db.Column(db.Text)
 215 |     target_segment = db.Column(db.String(100))
 216 |     generated_by = db.Column(db.String(50))
 217 |     nostr_event_id = db.Column(db.String(100))
 218 |     x_tweet_id = db.Column(db.String(100))
 219 |     is_approved = db.Column(db.Boolean, default=False)
 220 |     is_posted = db.Column(db.Boolean, default=False)
 221 | 
 222 | class TargetAlert(db.Model):
 223 |     id = db.Column(db.Integer, primary_key=True)
 224 |     trigger_type = db.Column(db.String(50))
 225 |     source_url = db.Column(db.String(500))
 226 |     source_account = db.Column(db.String(100))
 227 |     content_snippet = db.Column(db.Text)
 228 |     priority = db.Column(db.Integer, default=2)
 229 |     strategy_suggested = db.Column(db.String(100))
 230 |     draft_replies = db.Column(db.Text)
 231 |     status = db.Column(db.String(50), default='pending')
 232 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 233 |     responded_at = db.Column(db.DateTime)
 234 | 
 235 | class NostrEvent(db.Model):
 236 |     id = db.Column(db.Integer, primary_key=True)
 237 |     event_id = db.Column(db.String(100))
 238 |     content_type = db.Column(db.String(50))
 239 |     content_id = db.Column(db.Integer)
 240 |     relays_success = db.Column(db.Text)
 241 |     relays_failed = db.Column(db.Text)
 242 |     zaps_received = db.Column(db.Integer, default=0)
 243 |     zaps_amount_sats = db.Column(db.Integer, default=0)
 244 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 245 | 
 246 | class ReplySquadMember(db.Model):
 247 |     id = db.Column(db.Integer, primary_key=True)
 248 |     handle = db.Column(db.String(100), nullable=False)
 249 |     display_name = db.Column(db.String(150))
 250 |     category = db.Column(db.String(100))
 251 |     priority = db.Column(db.Integer, default=2)
 252 |     reciprocal_engagements = db.Column(db.Integer, default=0)
 253 |     last_engagement = db.Column(db.DateTime)
 254 |     notes = db.Column(db.Text)
 255 |     active = db.Column(db.Boolean, default=True)
 256 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 257 | 
 258 | # =====================================
 259 | # BITCOIN NETWORK & DONATIONS
 260 | # =====================================
 261 | 
 262 | class WhaleTransaction(db.Model):
 263 |     id = db.Column(db.Integer, primary_key=True)
 264 |     txid = db.Column(db.String(100), unique=True, nullable=False)
 265 |     btc_amount = db.Column(db.Float, nullable=False)
 266 |     usd_value = db.Column(db.Float)
 267 |     fee_sats = db.Column(db.Integer)
 268 |     block_height = db.Column(db.Integer)
 269 |     detected_at = db.Column(db.DateTime, default=datetime.utcnow)
 270 |     is_mega = db.Column(db.Boolean, default=False)
 271 | 
 272 | 
 273 | class ContactSubmission(db.Model):
 274 |     """Contact form submissions (stored for admin; optional email notification)."""
 275 |     id = db.Column(db.Integer, primary_key=True)
 276 |     name = db.Column(db.String(200), nullable=False)
 277 |     email = db.Column(db.String(200), nullable=False)
 278 |     subject = db.Column(db.String(100), nullable=False)
 279 |     message = db.Column(db.Text, nullable=False)
 280 |     ip_address = db.Column(db.String(64))
 281 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 282 |     read = db.Column(db.Boolean, default=False)
 283 | 
 284 | 
 285 | class PremiumAsk(db.Model):
 286 |     """Sovereign Elite monthly ask: one research/question per month, answered by team."""
 287 |     id = db.Column(db.Integer, primary_key=True)
 288 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 289 |     question_text = db.Column(db.Text, nullable=False)
 290 |     status = db.Column(db.String(20), default='pending')  # pending | answered
 291 |     answer_text = db.Column(db.Text)
 292 |     answer_url = db.Column(db.String(500))  # optional link to brief or doc
 293 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 294 |     answered_at = db.Column(db.DateTime)
 295 |     user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))
 296 | 
 297 | 
 298 | class BitcoinDonation(db.Model):
 299 |     id = db.Column(db.Integer, primary_key=True)
 300 |     payment_id = db.Column(db.String(100))
 301 |     amount_sats = db.Column(db.Integer)
 302 |     amount_usd = db.Column(db.Float)
 303 |     donor_email = db.Column(db.String(200))
 304 |     donor_name = db.Column(db.String(200))
 305 |     message = db.Column(db.Text)
 306 |     status = db.Column(db.String(50), default='pending')
 307 |     payment_method = db.Column(db.String(50))
 308 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 309 |     confirmed_at = db.Column(db.DateTime)
 310 | 
 311 | # =====================================
 312 | # ANALYTICS & PERFORMANCE
 313 | # =====================================
 314 | 
 315 | class EngagementEvent(db.Model):
 316 |     id = db.Column(db.Integer, primary_key=True)
 317 |     event_type = db.Column(db.String(50), nullable=False)
 318 |     content_type = db.Column(db.String(50))
 319 |     content_id = db.Column(db.Integer)
 320 |     source_platform = db.Column(db.String(50))
 321 |     source_url = db.Column(db.String(500))
 322 |     persona = db.Column(db.String(50))
 323 |     strategy = db.Column(db.String(100))
 324 |     minutes_after_post = db.Column(db.Float)
 325 |     is_30min_window = db.Column(db.Boolean, default=False)
 326 |     grok_score_contribution = db.Column(db.Integer, default=0)
 327 |     user_agent = db.Column(db.String(300))
 328 |     referrer = db.Column(db.String(500))
 329 |     ip_hash = db.Column(db.String(64))
 330 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 331 | 
 332 | class ContentPerformance(db.Model):
 333 |     id = db.Column(db.Integer, primary_key=True)
 334 |     content_type = db.Column(db.String(50), nullable=False)
 335 |     content_id = db.Column(db.Integer, nullable=False)
 336 |     content_title = db.Column(db.String(300))
 337 |     total_views = db.Column(db.Integer, default=0)
 338 |     total_clicks = db.Column(db.Integer, default=0)
 339 |     total_replies = db.Column(db.Integer, default=0)
 340 |     total_retweets = db.Column(db.Integer, default=0)
 341 |     total_quotes = db.Column(db.Integer, default=0)
 342 |     total_likes = db.Column(db.Integer, default=0)
 343 |     profile_visits = db.Column(db.Integer, default=0)
 344 |     replies_0_5min = db.Column(db.Integer, default=0)
 345 |     replies_5_15min = db.Column(db.Integer, default=0)
 346 |     replies_15_30min = db.Column(db.Integer, default=0)
 347 |     replies_30plus_min = db.Column(db.Integer, default=0)
 348 |     velocity_score = db.Column(db.Float, default=0)
 349 |     grok_score_total = db.Column(db.Integer, default=0)
 350 |     reached_for_you = db.Column(db.Boolean, default=False)
 351 |     peak_velocity_minute = db.Column(db.Integer)
 352 |     alex_engagements = db.Column(db.Integer, default=0)
 353 |     sarah_engagements = db.Column(db.Integer, default=0)
 354 |     best_performing_strategy = db.Column(db.String(100))
 355 |     best_performing_time = db.Column(db.String(20))
 356 |     published_at = db.Column(db.DateTime)
 357 |     last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 358 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 359 | 
 360 | class AnalyticsSummary(db.Model):
 361 |     id = db.Column(db.Integer, primary_key=True)
 362 |     period_type = db.Column(db.String(20), nullable=False)
 363 |     period_start = db.Column(db.Date, nullable=False)
 364 |     period_end = db.Column(db.Date, nullable=False)
 365 |     total_posts = db.Column(db.Integer, default=0)
 366 |     total_impressions = db.Column(db.Integer, default=0)
 367 |     total_engagements = db.Column(db.Integer, default=0)
 368 |     total_profile_visits = db.Column(db.Integer, default=0)
 369 |     total_followers_gained = db.Column(db.Integer, default=0)
 370 |     avg_velocity_score = db.Column(db.Float, default=0)
 371 |     avg_grok_score = db.Column(db.Float, default=0)
 372 |     for_you_reach_rate = db.Column(db.Float, default=0)
 373 |     top_performing_content_id = db.Column(db.Integer)
 374 |     top_performing_content_type = db.Column(db.String(50))
 375 |     top_performing_strategy = db.Column(db.String(100))
 376 |     alex_total_score = db.Column(db.Integer, default=0)
 377 |     sarah_total_score = db.Column(db.Integer, default=0)
 378 |     persona_winner = db.Column(db.String(50))
 379 |     best_posting_hour = db.Column(db.Integer)
 380 |     best_posting_day = db.Column(db.Integer)
 381 |     sponsor_value_estimate = db.Column(db.Float)
 382 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 383 | 
 384 | class Sponsor(db.Model):
 385 |     id = db.Column(db.Integer, primary_key=True)
 386 |     name = db.Column(db.String(200), nullable=False)
 387 |     company = db.Column(db.String(200))
 388 |     email = db.Column(db.String(200))
 389 |     website_url = db.Column(db.String(500))
 390 |     logo_url = db.Column(db.String(500))
 391 |     tier = db.Column(db.String(50), default='standard')
 392 |     status = db.Column(db.String(50), default='pending')
 393 |     impressions = db.Column(db.Integer, default=0)
 394 |     clicks = db.Column(db.Integer, default=0)
 395 |     ctr = db.Column(db.Float, default=0)
 396 |     budget_sats = db.Column(db.Integer, default=0)
 397 |     spent_sats = db.Column(db.Integer, default=0)
 398 |     cpm_sats = db.Column(db.Integer, default=1000)
 399 |     target_categories = db.Column(db.String(500))
 400 |     target_personas = db.Column(db.String(200))
 401 |     ad_copy = db.Column(db.Text)
 402 |     cta_text = db.Column(db.String(100))
 403 |     cta_url = db.Column(db.String(500))
 404 |     start_date = db.Column(db.DateTime)
 405 |     end_date = db.Column(db.DateTime)
 406 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 407 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 408 | 
 409 | class CreditAccount(db.Model):
 410 |     id = db.Column(db.Integer, primary_key=True)
 411 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 412 |     signal_points = db.Column(db.Integer, default=0)
 413 |     lifetime_points = db.Column(db.Integer, default=0)
 414 |     tier = db.Column(db.String(50), default='recruit')
 415 |     tier_progress = db.Column(db.Float, default=0)
 416 |     articles_read = db.Column(db.Integer, default=0)
 417 |     podcasts_listened = db.Column(db.Integer, default=0)
 418 |     quizzes_completed = db.Column(db.Integer, default=0)
 419 |     referrals_made = db.Column(db.Integer, default=0)
 420 |     streak_days = db.Column(db.Integer, default=0)
 421 |     longest_streak = db.Column(db.Integer, default=0)
 422 |     last_activity = db.Column(db.DateTime)
 423 |     badges = db.Column(db.Text)
 424 |     achievements = db.Column(db.Text)
 425 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 426 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 427 |     user = db.relationship('User', backref=db.backref('credit_account', uselist=False))
 428 | 
 429 | class PredictionOracle(db.Model):
 430 |     id = db.Column(db.Integer, primary_key=True)
 431 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 432 |     prediction_type = db.Column(db.String(50))
 433 |     prediction_value = db.Column(db.Float)
 434 |     target_date = db.Column(db.DateTime)
 435 |     actual_value = db.Column(db.Float)
 436 |     accuracy_score = db.Column(db.Float)
 437 |     status = db.Column(db.String(50), default='pending')
 438 |     is_correct = db.Column(db.Boolean)
 439 |     signal_points_wagered = db.Column(db.Integer, default=0)
 440 |     signal_points_won = db.Column(db.Integer, default=0)
 441 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 442 |     resolved_at = db.Column(db.DateTime)
 443 | 
 444 | class UserSegment(db.Model):
 445 |     id = db.Column(db.Integer, primary_key=True)
 446 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 447 |     segment_type = db.Column(db.String(50), default='general')
 448 |     confidence = db.Column(db.Float, default=0.5)
 449 |     hashrate_interest = db.Column(db.Float, default=0)
 450 |     macro_interest = db.Column(db.Float, default=0)
 451 |     technical_interest = db.Column(db.Float, default=0)
 452 |     trading_interest = db.Column(db.Float, default=0)
 453 |     privacy_interest = db.Column(db.Float, default=0)
 454 |     articles_viewed = db.Column(db.Integer, default=0)
 455 |     avg_read_time = db.Column(db.Float, default=0)
 456 |     preferred_categories = db.Column(db.Text)
 457 |     last_classification = db.Column(db.DateTime, default=datetime.utcnow)
 458 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 459 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 460 |     user = db.relationship('User', backref=db.backref('segment', uselist=False))
 461 | 
 462 | class AffiliatePartner(db.Model):
 463 |     __tablename__ = 'affiliate_partner'
 464 |     id = db.Column(db.Integer, primary_key=True)
 465 |     name = db.Column(db.String(100), unique=True, nullable=False)
 466 |     slug = db.Column(db.String(50), unique=True, nullable=False)
 467 |     category = db.Column(db.String(50))
 468 |     url = db.Column(db.String(500))
 469 |     benefit = db.Column(db.String(200))
 470 |     is_active = db.Column(db.Boolean, default=True)
 471 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 472 |     clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')
 473 | 
 474 | class AffiliateClick(db.Model):
 475 |     __tablename__ = 'affiliate_click'
 476 |     id = db.Column(db.Integer, primary_key=True)
 477 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
 478 |     source_page = db.Column(db.String(500))
 479 |     ip_hash = db.Column(db.String(64))
 480 |     user_agent = db.Column(db.String(500))
 481 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 482 | 
 483 | class FeedItem(db.Model):
 484 |     __tablename__ = 'feed_item'
 485 |     id = db.Column(db.Integer, primary_key=True)
 486 |     source = db.Column(db.String(100), nullable=False)
 487 |     source_type = db.Column(db.String(50), nullable=False)
 488 |     tier = db.Column(db.String(20))
 489 |     title = db.Column(db.String(500))
 490 |     url = db.Column(db.String(1000), unique=True)
 491 |     published_at = db.Column(db.DateTime)
 492 |     author = db.Column(db.String(100))
 493 |     summary = db.Column(db.Text)
 494 |     platform_icon = db.Column(db.String(50))
 495 |     raw_json = db.Column(db.Text)
 496 |     verified = db.Column(db.Boolean, default=False)
 497 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 498 | 
 499 | class SentimentSnapshot(db.Model):
 500 |     __tablename__ = 'sentiment_snapshot'
 501 |     id = db.Column(db.Integer, primary_key=True)
 502 |     score = db.Column(db.Float, default=50.0)
 503 |     state = db.Column(db.String(50), default='EQUILIBRIUM')
 504 |     state_label = db.Column(db.String(50), default='EQUILIBRIUM')
 505 |     state_color = db.Column(db.String(20), default='#ffffff')
 506 |     velocity = db.Column(db.Float, default=0.0)
 507 |     top_keywords = db.Column(db.Text)
 508 |     top_topics_json = db.Column(db.Text)
 509 |     sample_size = db.Column(db.Integer, default=0)
 510 |     verified_weight = db.Column(db.Integer, default=0)
 511 |     computed_at = db.Column(db.DateTime, default=datetime.utcnow)
 512 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 513 | 
 514 | class PulseEvent(db.Model):
 515 |     __tablename__ = 'pulse_event'
 516 |     id = db.Column(db.Integer, primary_key=True)
 517 |     event_type = db.Column(db.String(50), nullable=False)
 518 |     from_state = db.Column(db.String(50))
 519 |     to_state = db.Column(db.String(50))
 520 |     score = db.Column(db.Float)
 521 |     triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
 522 |     payload_json = db.Column(db.Text)
 523 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 524 | 
 525 | class AutoPostDraft(db.Model):
 526 |     __tablename__ = 'autopost_draft'
 527 |     id = db.Column(db.Integer, primary_key=True)
 528 |     platform = db.Column(db.String(30), nullable=False)
 529 |     status = db.Column(db.String(20), default='draft')
 530 |     body = db.Column(db.Text)
 531 |     reason = db.Column(db.String(200))
 532 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 533 |     approved_at = db.Column(db.DateTime)
 534 |     posted_at = db.Column(db.DateTime)
 535 | 
 536 | class DailyBrief(db.Model):
 537 |     __tablename__ = 'daily_brief'
 538 |     id = db.Column(db.Integer, primary_key=True)
 539 |     headline = db.Column(db.String(500))
 540 |     body = db.Column(db.Text)
 541 |     signals_json = db.Column(db.Text)
 542 |     status = db.Column(db.String(20), default='draft')
 543 |     published_at = db.Column(db.DateTime)
 544 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 545 | 
 546 | class PageView(db.Model):
 547 |     __tablename__ = 'page_view'
 548 |     id = db.Column(db.Integer, primary_key=True)
 549 |     page_path = db.Column(db.String(500), nullable=False)
 550 |     page_title = db.Column(db.String(300))
 551 |     page_category = db.Column(db.String(50))
 552 |     session_id = db.Column(db.String(64))
 553 |     ip_hash = db.Column(db.String(64))
 554 |     user_agent = db.Column(db.String(300))
 555 |     referrer = db.Column(db.String(500))
 556 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 557 |     time_on_page = db.Column(db.Integer, default=0)
 558 |     scroll_depth = db.Column(db.Integer, default=0)
 559 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 560 | 
 561 | class HotMoment(db.Model):
 562 |     __tablename__ = 'hot_moment'
 563 |     id = db.Column(db.Integer, primary_key=True)
 564 |     page_path = db.Column(db.String(500), nullable=False)
 565 |     page_title = db.Column(db.String(300))
 566 |     page_category = db.Column(db.String(50))
 567 |     views_in_window = db.Column(db.Integer, default=0)
 568 |     unique_visitors = db.Column(db.Integer, default=0)
 569 |     heat_score = db.Column(db.Float, default=0)
 570 |     is_peak = db.Column(db.Boolean, default=False)
 571 |     peak_detected_at = db.Column(db.DateTime)
 572 |     tweet_drafted = db.Column(db.Boolean, default=False)
 573 |     tweet_content = db.Column(db.Text)
 574 |     tweet_posted_at = db.Column(db.DateTime)
 575 |     window_start = db.Column(db.DateTime, nullable=False)
 576 |     window_end = db.Column(db.DateTime, nullable=False)
 577 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 578 | 
 579 | class ContentSuggestion(db.Model):
 580 |     __tablename__ = 'content_suggestion'
 581 |     id = db.Column(db.Integer, primary_key=True)
 582 |     suggestion_type = db.Column(db.String(50))
 583 |     title = db.Column(db.String(300))
 584 |     description = db.Column(db.Text)
 585 |     reasoning = db.Column(db.Text)
 586 |     based_on_page = db.Column(db.String(500))
 587 |     based_on_trend = db.Column(db.String(200))
 588 |     confidence_score = db.Column(db.Float, default=0)
 589 |     status = db.Column(db.String(20), default='pending')
 590 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 591 |     actioned_at = db.Column(db.DateTime)
 592 | 
 593 | class AutoTweet(db.Model):
 594 |     __tablename__ = 'auto_tweet'
 595 |     id = db.Column(db.Integer, primary_key=True)
 596 |     trigger_type = db.Column(db.String(50))
 597 |     trigger_page = db.Column(db.String(500))
 598 |     heat_score_at_trigger = db.Column(db.Float)
 599 |     tweet_content = db.Column(db.Text, nullable=False)
 600 |     hashtags = db.Column(db.String(200))
 601 |     status = db.Column(db.String(20), default='draft')
 602 |     approved_at = db.Column(db.DateTime)
 603 |     posted_at = db.Column(db.DateTime)
 604 |     post_url = db.Column(db.String(500))
 605 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 606 | 
 607 | 
 608 | # =====================================
 609 | # X ENGAGEMENT SENTRY (TWEET REPLIES)
 610 | # =====================================
 611 | 
 612 | 
 613 | class XInboxTweet(db.Model):
 614 |     """Incoming tweets from monitored X accounts for Sovereign Sentry."""
 615 |     __tablename__ = 'x_inbox_tweet'
 616 | 
 617 |     id = db.Column(db.Integer, primary_key=True)
 618 |     tweet_id = db.Column(db.String(64), unique=True, nullable=False)
 619 |     author_handle = db.Column(db.String(50), nullable=False, index=True)
 620 |     author_name = db.Column(db.String(100))
 621 |     tweet_text = db.Column(db.Text, nullable=False)
 622 |     tweet_url = db.Column(db.String(500))
 623 |     tweet_created_at = db.Column(db.DateTime)
 624 |     status = db.Column(
 625 |         db.String(20),
 626 |         default='new',
 627 |     )  # new | drafted | approved | posted | rejected | skipped | error
 628 |     tier = db.Column(db.String(30))
 629 |     style = db.Column(db.String(30))
 630 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 631 | 
 632 | 
 633 | class XReplyDraft(db.Model):
 634 |     """Generated reply drafts evaluated by Sovereign Sentry."""
 635 |     __tablename__ = 'x_reply_draft'
 636 | 
 637 |     id = db.Column(db.Integer, primary_key=True)
 638 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 639 |     draft_text = db.Column(db.String(300), nullable=False)
 640 |     confidence = db.Column(db.Float)
 641 |     reasoning = db.Column(db.Text)
 642 |     style_used = db.Column(db.String(30))
 643 |     risk_flags = db.Column(db.Text)  # optional JSON array string
 644 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 645 | 
 646 |     inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))
 647 | 
 648 | 
 649 | class XReplyPost(db.Model):
 650 |     """Log of replies actually posted to X."""
 651 |     __tablename__ = 'x_reply_post'
 652 | 
 653 |     id = db.Column(db.Integer, primary_key=True)
 654 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 655 |     draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
 656 |     reply_tweet_id = db.Column(db.String(64))
 657 |     posted_at = db.Column(db.DateTime, default=datetime.utcnow)
 658 |     response_payload = db.Column(db.Text)  # raw JSON from X API
 659 | 
 660 |     inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
 661 |     draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))
 662 | 
 663 | 
 664 | # =====================================
 665 | # VALUE STREAM MODELS
 666 | # =====================================
 667 | 
 668 | class ValueCreator(db.Model):
 669 |     __tablename__ = 'value_creator'
 670 |     id = db.Column(db.Integer, primary_key=True)
 671 |     display_name = db.Column(db.String(100), nullable=False)
 672 |     nostr_pubkey = db.Column(db.String(128), unique=True)
 673 |     lightning_address = db.Column(db.String(200))
 674 |     nip05 = db.Column(db.String(200))
 675 |     twitter_handle = db.Column(db.String(50))
 676 |     youtube_channel_id = db.Column(db.String(50))
 677 |     reddit_username = db.Column(db.String(50))
 678 |     stacker_news_username = db.Column(db.String(50))
 679 |     profile_image = db.Column(db.String(500))
 680 |     bio = db.Column(db.Text)
 681 |     total_sats_received = db.Column(db.BigInteger, default=0)
 682 |     total_zaps = db.Column(db.Integer, default=0)
 683 |     curator_score = db.Column(db.Float, default=0)
 684 |     verified = db.Column(db.Boolean, default=False)
 685 |     verified_at = db.Column(db.DateTime)
 686 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 687 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 688 |     curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
 689 |                                      foreign_keys='CuratedPost.creator_id')
 690 |     submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
 691 |                                        foreign_keys='CuratedPost.curator_id')
 692 | 
 693 | class CuratedPost(db.Model):
 694 |     __tablename__ = 'curated_post'
 695 |     id = db.Column(db.Integer, primary_key=True)
 696 |     platform = db.Column(db.String(30), nullable=False)
 697 |     original_url = db.Column(db.String(1000), nullable=False, unique=True)
 698 |     original_id = db.Column(db.String(200))
 699 |     title = db.Column(db.String(500))
 700 |     content_preview = db.Column(db.Text)
 701 |     thumbnail_url = db.Column(db.String(500))
 702 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 703 |     curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 704 |     total_sats = db.Column(db.BigInteger, default=0)
 705 |     zap_count = db.Column(db.Integer, default=0)
 706 |     boost_sats = db.Column(db.BigInteger, default=0)
 707 |     signal_score = db.Column(db.Float, default=0)
 708 |     decay_factor = db.Column(db.Float, default=1.0)
 709 |     is_verified = db.Column(db.Boolean, default=False)
 710 |     is_featured = db.Column(db.Boolean, default=False)
 711 |     submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
 712 |     last_zap_at = db.Column(db.DateTime)
 713 |     
 714 |     def calculate_signal_score(self):
 715 |         age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
 716 |         time_decay = max(0.1, 1 - (age_hours / 168))
 717 |         raw_score = (self.total_sats * 0.001) + (self.zap_count * 10)
 718 |         self.signal_score = raw_score * time_decay * self.decay_factor
 719 |         return self.signal_score
 720 | 
 721 | class ZapEvent(db.Model):
 722 |     __tablename__ = 'zap_event'
 723 |     id = db.Column(db.Integer, primary_key=True)
 724 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 725 |     sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 726 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 727 |     creator_share = db.Column(db.BigInteger)
 728 |     curator_share = db.Column(db.BigInteger)
 729 |     platform_share = db.Column(db.BigInteger)
 730 |     payment_hash = db.Column(db.String(128))
 731 |     bolt11_invoice = db.Column(db.Text)
 732 |     preimage = db.Column(db.String(128))
 733 |     status = db.Column(db.String(20), default='pending')
 734 |     source = db.Column(db.String(30))
 735 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 736 |     settled_at = db.Column(db.DateTime)
 737 |     post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))
 738 | 
 739 | class TrustEdge(db.Model):
 740 |     __tablename__ = 'trust_edge'
 741 |     id = db.Column(db.Integer, primary_key=True)
 742 |     truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 743 |     trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 744 |     trust_weight = db.Column(db.Float, default=1.0)
 745 |     total_sats_via = db.Column(db.BigInteger, default=0)
 746 |     successful_curations = db.Column(db.Integer, default=0)
 747 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 748 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 749 |     __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)
 750 | 
 751 | class BoostStake(db.Model):
 752 |     __tablename__ = 'boost_stake'
 753 |     id = db.Column(db.Integer, primary_key=True)
 754 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 755 |     staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 756 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 757 |     boost_multiplier = db.Column(db.Float, default=1.0)
 758 |     expires_at = db.Column(db.DateTime)
 759 |     refunded = db.Column(db.Boolean, default=False)
 760 |     refund_amount = db.Column(db.BigInteger, default=0)
 761 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 762 |     post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))
 763 | 
 764 | class ExtensionSession(db.Model):
 765 |     __tablename__ = 'extension_session'
 766 |     id = db.Column(db.Integer, primary_key=True)
 767 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 768 |     session_token = db.Column(db.String(128), unique=True, nullable=False)
 769 |     browser_fingerprint = db.Column(db.String(128))
 770 |     user_agent = db.Column(db.String(500))
 771 |     is_active = db.Column(db.Boolean, default=True)
 772 |     last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
 773 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 774 |     expires_at = db.Column(db.DateTime)
 775 |     creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
 776 | 
 777 | class RollingActivity(db.Model):
 778 |     __tablename__ = 'rolling_activity'
 779 |     id = db.Column(db.Integer, primary_key=True)
 780 |     page_path = db.Column(db.String(500), nullable=False, index=True)
 781 |     page_name = db.Column(db.String(200))
 782 |     session_hash = db.Column(db.String(64), nullable=False)
 783 |     last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 784 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 785 |     
 786 |     @classmethod
 787 |     def record_activity(cls, page_path, page_name, session_hash):
 788 |         existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
 789 |         if existing:
 790 |             existing.last_seen = datetime.utcnow()
 791 |         else:
 792 |             activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
 793 |             db.session.add(activity)
 794 |         try:
 795 |             db.session.commit()
 796 |         except Exception:
 797 |             db.session.rollback()
 798 | 
 799 |     @classmethod
 800 |     def get_operative_density(cls, window_minutes=30, limit=5):
 801 |         from sqlalchemy import func
 802 |         cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
 803 |         results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
 804 |         return results
 805 | 
 806 | class RealTimeProduct(db.Model):
 807 |     __tablename__ = 'realtime_product'
 808 |     id = db.Column(db.Integer, primary_key=True)
 809 |     statement_text = db.Column(db.String(100), nullable=False)
 810 |     design_url = db.Column(db.String(500))
 811 |     design_style = db.Column(db.String(50), default='center_chest')
 812 |     text_color = db.Column(db.String(20), default='#FFFFFF')
 813 |     trigger_state = db.Column(db.String(50))
 814 |     trigger_keywords = db.Column(db.Text)
 815 |     sentiment_score = db.Column(db.Float)
 816 |     status = db.Column(db.String(20), default='draft')
 817 |     approved_at = db.Column(db.DateTime)
 818 |     approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
 819 |     printful_product_id = db.Column(db.String(100))
 820 |     printful_sync_status = db.Column(db.String(50), default='pending')
 821 |     heat_multiplier = db.Column(db.Float, default=2.0)
 822 |     heat_expires_at = db.Column(db.DateTime)
 823 |     sarah_description = db.Column(db.Text)
 824 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 825 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 826 |     
 827 |     def is_hot(self):
 828 |         return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at
 829 | 
 830 | class IntelligencePost(db.Model):
 831 |     id = db.Column(db.Integer, primary_key=True)
 832 |     persona = db.Column(db.String(20))
 833 |     partner_name = db.Column(db.String(100))
 834 |     partner_handle = db.Column(db.String(100))
 835 |     primary_tweet = db.Column(db.Text, nullable=False)
 836 |     thread_content = db.Column(db.Text)
 837 |     key_insight = db.Column(db.Text)
 838 |     source_video_id = db.Column(db.String(50))
 839 |     source_video_title = db.Column(db.String(500))
 840 |     x_tweet_id = db.Column(db.String(100))
 841 |     nostr_event_id = db.Column(db.String(100))
 842 |     engagement_likes = db.Column(db.Integer, default=0)
 843 |     engagement_retweets = db.Column(db.Integer, default=0)
 844 |     engagement_replies = db.Column(db.Integer, default=0)
 845 |     published_at = db.Column(db.DateTime, default=datetime.utcnow)
 846 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 847 | 
 848 | class SentimentReport(db.Model):
 849 |     id = db.Column(db.Integer, primary_key=True)
 850 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 851 |     report_date = db.Column(db.Date, nullable=False, unique=True)
 852 |     overall_sentiment = db.Column(db.String(20))
 853 |     sentiment_score = db.Column(db.Float)
 854 |     x_posts_analyzed = db.Column(db.Integer, default=0)
 855 |     nostr_notes_analyzed = db.Column(db.Integer, default=0)
 856 |     top_themes = db.Column(db.Text)
 857 |     key_narratives = db.Column(db.Text)
 858 |     cited_sources = db.Column(db.Text)
 859 |     raw_analysis = db.Column(db.Text)
 860 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 861 |     article = db.relationship('Article', backref='sentiment_report', lazy=True)
 862 | 
 863 | class SarahBrief(db.Model):
 864 |     __tablename__ = 'sarah_brief'
 865 |     id = db.Column(db.Integer, primary_key=True)
 866 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 867 |     brief_date = db.Column(db.Date, nullable=False, unique=True)
 868 |     macro_state = db.Column(db.Text)
 869 |     network_calibration = db.Column(db.Text)
 870 |     signal_1_title = db.Column(db.String(500))
 871 |     signal_1_source = db.Column(db.String(500))
 872 |     signal_1_url = db.Column(db.String(500))
 873 |     signal_1_impact = db.Column(db.Float, default=0.0)
 874 |     signal_2_title = db.Column(db.String(500))
 875 |     signal_2_source = db.Column(db.String(500))
 876 |     signal_2_url = db.Column(db.String(500))
 877 |     signal_2_impact = db.Column(db.Float, default=0.0)
 878 |     signal_3_title = db.Column(db.String(500))
 879 |     signal_3_source = db.Column(db.String(500))
 880 |     signal_3_url = db.Column(db.String(500))
 881 |     signal_3_impact = db.Column(db.Float, default=0.0)
 882 |     mempool_state = db.Column(db.Text)
 883 |     hashrate_state = db.Column(db.Text)
 884 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 885 |     article = db.relationship('Article', backref='sarah_brief', lazy=True)
 886 | 
 887 | class SentimentBuffer(db.Model):
 888 |     id = db.Column(db.Integer, primary_key=True)
 889 |     timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 890 |     sentiment_score = db.Column(db.Float, nullable=False)
 891 |     post_count = db.Column(db.Integer, default=0)
 892 |     dominant_theme = db.Column(db.String(200))
 893 |     source_breakdown = db.Column(db.Text)
 894 | 
 895 | class EmergencyFlash(db.Model):
 896 |     id = db.Column(db.Integer, primary_key=True)
 897 |     triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 898 |     previous_score = db.Column(db.Float)
 899 |     current_score = db.Column(db.Float)
 900 |     drift_magnitude = db.Column(db.Float)
 901 |     direction = db.Column(db.String(20))
 902 |     trigger_reason = db.Column(db.Text)
 903 |     top_signal_url = db.Column(db.String(500))
 904 |     top_signal_author = db.Column(db.String(200))
 905 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 906 |     acknowledged = db.Column(db.Boolean, default=False)
 907 |     acknowledged_at = db.Column(db.DateTime)
 908 |     article = db.relationship('Article', backref='emergency_flash', lazy=True)
 909 | 
 910 | # =====================================
 911 | # NOSTR INTELLIGENCE MONITOR (F4)
 912 | # =====================================
 913 | 
 914 | class NostrMonitorEvent(db.Model):
 915 |     """Inbound Nostr events captured by the relay monitor."""
 916 |     __tablename__ = 'nostr_monitor_events'
 917 |     id = db.Column(db.Integer, primary_key=True)
 918 |     event_id = db.Column(db.String(64), unique=True, nullable=False)
 919 |     pubkey = db.Column(db.String(64), nullable=False)
 920 |     kind = db.Column(db.Integer, nullable=False)
 921 |     content = db.Column(db.Text, nullable=False)
 922 |     engagement_score = db.Column(db.Float, default=0.0)
 923 |     zaps = db.Column(db.Integer, default=0)
 924 |     quotes = db.Column(db.Integer, default=0)
 925 |     reposts = db.Column(db.Integer, default=0)
 926 |     replies = db.Column(db.Integer, default=0)
 927 |     reactions = db.Column(db.Integer, default=0)
 928 |     bitcoin_relevance = db.Column(db.Float, default=0.0)
 929 |     relay_source = db.Column(db.String(100))
 930 |     created_at = db.Column(db.Integer, nullable=False)       # Nostr unix timestamp
 931 |     fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
 932 | 
 933 |     __table_args__ = (
 934 |         db.Index('idx_nostr_score', 'engagement_score'),
 935 |         db.Index('idx_nostr_created', 'created_at'),
 936 |         db.Index('idx_nostr_relevance', 'bitcoin_relevance'),
 937 |     )
 938 | 
 939 | 
 940 | class NostrTrackedPubkey(db.Model):
 941 |     """High-signal Nostr pubkeys tracked by Protocol Pulse."""
 942 |     __tablename__ = 'nostr_tracked_pubkeys'
 943 |     id = db.Column(db.Integer, primary_key=True)
 944 |     pubkey = db.Column(db.String(64), unique=True, nullable=False)
 945 |     display_name = db.Column(db.String(150))
 946 |     nip05 = db.Column(db.String(200))
 947 |     follower_tier = db.Column(db.String(20), default='standard')  # 'vip', 'standard'
 948 |     added_at = db.Column(db.DateTime, default=datetime.utcnow)
 949 | 
 950 |     __table_args__ = (
 951 |         db.Index('idx_nostr_pubkey_tier', 'follower_tier'),
 952 |     )
 953 | 
 954 | 
 955 | class CollectedSignal(db.Model):
 956 |     __tablename__ = 'collected_signal'
 957 |     id = db.Column(db.Integer, primary_key=True)
 958 |     platform = db.Column(db.String(20), nullable=False)
 959 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
 960 |     author_name = db.Column(db.String(200), nullable=False)
 961 |     author_handle = db.Column(db.String(100), nullable=False)
 962 |     author_tier = db.Column(db.String(50), default='general')
 963 |     content = db.Column(db.Text, nullable=False)
 964 |     url = db.Column(db.String(500), nullable=False)
 965 |     engagement_likes = db.Column(db.Integer, default=0)
 966 |     engagement_reposts = db.Column(db.Integer, default=0)
 967 |     engagement_replies = db.Column(db.Integer, default=0)
 968 |     engagement_score = db.Column(db.Float, default=0.0)
 969 |     sentiment = db.Column(db.String(20))
 970 |     sentiment_score = db.Column(db.Float)
 971 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
 972 |     posted_at = db.Column(db.DateTime)
 973 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
 974 |     is_verified = db.Column(db.Boolean, default=True)
 975 |     is_legendary = db.Column(db.Boolean, default=False)
 976 |     __table_args__ = (
 977 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
 978 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
 979 |     )
```

### File: core/services/nostr_service.py (277 lines)
```
   1 | """
   2 | core/services/nostr_service.py — DB interface for Nostr Intelligence (F4).
   3 | 
   4 | Provides:
   5 |   - get_top_content(limit) → top scored events from nostr_monitor_events
   6 |   - get_relay_status() → live relay connection status from nostr_monitor
   7 |   - seed_tracked_pubkeys() → insert high-signal Bitcoin pubkeys on first run
   8 |   - get_tracked_pubkeys() → list of seeded pubkeys
   9 | """
  10 | import logging
  11 | import os
  12 | import time
  13 | from datetime import datetime, timedelta, timezone
  14 | from typing import Dict, List, Optional
  15 | 
  16 | logger = logging.getLogger(__name__)
  17 | 
  18 | # ── High-signal Bitcoin Nostr pubkeys (seed list, LAW 3) ─────────────────────
  19 | # Sources: well-known Bitcoin community members on Nostr
  20 | SEED_PUBKEYS: List[Dict] = [
  21 |     {
  22 |         "pubkey": "82341f882b6eabcd2ba7f1ef90aad961cf074af15b9ef44a09f9d2a8fbfbe6a2",
  23 |         "display_name": "Jack Dorsey",
  24 |         "nip05": "jack@cash.app",
  25 |         "follower_tier": "vip",
  26 |     },
  27 |     {
  28 |         "pubkey": "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d",
  29 |         "display_name": "Fiatjaf (NIP inventor)",
  30 |         "nip05": "fiatjaf@fiatjaf.com",
  31 |         "follower_tier": "vip",
  32 |     },
  33 |     {
  34 |         "pubkey": "126103bfddc8df256b6e0abfd7f3797c80dcc4ea88f7c2f87dd4104220b4d65",
  35 |         "display_name": "Marty Bent",
  36 |         "nip05": "marty@bitcoinmagazine.com",
  37 |         "follower_tier": "vip",
  38 |     },
  39 |     {
  40 |         "pubkey": "04c915daefee38317fa734444acee390a8269fe5810b2241e5e6dd343dfbecc",
  41 |         "display_name": "ODELL",
  42 |         "nip05": "odell@odell.xyz",
  43 |         "follower_tier": "vip",
  44 |     },
  45 |     {
  46 |         "pubkey": "e88a691e98d9987c964521dff60025f60700378a4879180dcbbb4a5027850411",
  47 |         "display_name": "NVK (CoinKite)",
  48 |         "nip05": "nvk@nvk.org",
  49 |         "follower_tier": "vip",
  50 |     },
  51 |     {
  52 |         "pubkey": "b9e76546ba06456ed301d9e52bc49fa48e70a6bf2282be7a1ae72947612023dc",
  53 |         "display_name": "Luke Dashjr",
  54 |         "nip05": None,
  55 |         "follower_tier": "vip",
  56 |     },
  57 |     {
  58 |         "pubkey": "dd664d5e4016433a8cd69f005ae1480804351789b59de5af06276de65633dcdc",
  59 |         "display_name": "Lyn Alden",
  60 |         "nip05": None,
  61 |         "follower_tier": "vip",
  62 |     },
  63 |     {
  64 |         "pubkey": "6ad3e2a34818b153c81f48c58f44e5199d7b4d925ba3f1d5b7dece969c99b34",
  65 |         "display_name": "Jeff Booth",
  66 |         "nip05": None,
  67 |         "follower_tier": "standard",
  68 |     },
  69 |     {
  70 |         "pubkey": "85080d3bad70ccdcd7f74c29a44f55bb85cbcd3dd0cbb957da1d215bdb931204",
  71 |         "display_name": "Will Cole (Iris.to)",
  72 |         "nip05": None,
  73 |         "follower_tier": "standard",
  74 |     },
  75 |     {
  76 |         "pubkey": "7fa56f5d6962ab1e3cd424e758c3002b8665f7b0d8dcee9fe9e288d7751ac194",
  77 |         "display_name": "Walker (Bitcoin Magazine)",
  78 |         "nip05": None,
  79 |         "follower_tier": "standard",
  80 |     },
  81 | ]
  82 | 
  83 | 
  84 | def seed_tracked_pubkeys() -> int:
  85 |     """
  86 |     Insert high-signal pubkeys into nostr_tracked_pubkeys on first run.
  87 |     Returns number of new records inserted.
  88 |     """
  89 |     try:
  90 |         from app import app, db
  91 |         import models
  92 | 
  93 |         inserted = 0
  94 |         with app.app_context():
  95 |             for entry in SEED_PUBKEYS:
  96 |                 try:
  97 |                     existing = db.session.execute(
  98 |                         db.select(models.NostrTrackedPubkey).where(
  99 |                             models.NostrTrackedPubkey.pubkey == entry["pubkey"]
 100 |                         )
 101 |                     ).scalar_one_or_none()
 102 |                     if existing:
 103 |                         continue
 104 |                     record = models.NostrTrackedPubkey(
 105 |                         pubkey=entry["pubkey"],
 106 |                         display_name=entry.get("display_name"),
 107 |                         nip05=entry.get("nip05"),
 108 |                         follower_tier=entry.get("follower_tier", "standard"),
 109 |                     )
 110 |                     db.session.add(record)
 111 |                     inserted += 1
 112 |                 except Exception as e:
 113 |                     logger.warning("Error seeding pubkey %s: %s", entry.get("display_name"), e)
 114 |                     db.session.rollback()
 115 |             try:
 116 |                 db.session.commit()
 117 |                 logger.info("Seeded %d new tracked pubkeys", inserted)
 118 |             except Exception as e:
 119 |                 logger.error("Seed commit failed: %s", e)
 120 |                 db.session.rollback()
 121 |         return inserted
 122 |     except Exception as e:
 123 |         logger.error("seed_tracked_pubkeys failed: %s", e)
 124 |         return 0
 125 | 
 126 | 
 127 | def get_top_content(limit: int = 10) -> List[Dict]:
 128 |     """
 129 |     Return top N Nostr events by engagement score from the last 24h.
 130 |     Falls back to all-time if no recent events exist.
 131 |     """
 132 |     try:
 133 |         from app import app, db
 134 |         import models
 135 | 
 136 |         with app.app_context():
 137 |             cutoff = int(time.time()) - 86400  # 24h ago
 138 | 
 139 |             # Try recent first
 140 |             events = db.session.execute(
 141 |                 db.select(models.NostrMonitorEvent)
 142 |                 .where(models.NostrMonitorEvent.created_at >= cutoff)
 143 |                 .order_by(models.NostrMonitorEvent.engagement_score.desc())
 144 |                 .limit(limit)
 145 |             ).scalars().all()
 146 | 
 147 |             # Fallback: all-time top if no recent events
 148 |             if not events:
 149 |                 events = db.session.execute(
 150 |                     db.select(models.NostrMonitorEvent)
 151 |                     .order_by(models.NostrMonitorEvent.engagement_score.desc())
 152 |                     .limit(limit)
 153 |                 ).scalars().all()
 154 | 
 155 |             result = []
 156 |             for ev in events:
 157 |                 content_preview = (ev.content or "")[:280]
 158 |                 result.append({
 159 |                     "event_id": ev.event_id,
 160 |                     "pubkey": ev.pubkey,
 161 |                     "pubkey_short": ev.pubkey[:8] + "..." if ev.pubkey else "",
 162 |                     "kind": ev.kind,
 163 |                     "content": content_preview,
 164 |                     "content_full": ev.content or "",
 165 |                     "engagement_score": round(ev.engagement_score or 0, 1),
 166 |                     "zaps": ev.zaps or 0,
 167 |                     "quotes": ev.quotes or 0,
 168 |                     "reposts": ev.reposts or 0,
 169 |                     "replies": ev.replies or 0,
 170 |                     "reactions": ev.reactions or 0,
 171 |                     "bitcoin_relevance": round(ev.bitcoin_relevance or 0, 2),
 172 |                     "relay_source": ev.relay_source or "",
 173 |                     "created_at": ev.created_at,
 174 |                     "created_at_iso": datetime.fromtimestamp(
 175 |                         ev.created_at, tz=timezone.utc
 176 |                     ).isoformat() if ev.created_at else None,
 177 |                     "fetched_at": ev.fetched_at.isoformat() if ev.fetched_at else None,
 178 |                     "nostr_link": f"https://njump.me/{ev.event_id}" if ev.event_id else "",
 179 |                 })
 180 |             return result
 181 |     except Exception as e:
 182 |         logger.error("get_top_content error: %s", e)
 183 |         return []
 184 | 
 185 | 
 186 | def get_relay_status() -> List[Dict]:
 187 |     """
 188 |     Return relay connection status.
 189 |     Reads from state/nostr_relay_status.json written by the monitor process.
 190 |     Falls back to static disconnected list if monitor not running.
 191 |     """
 192 |     import json as _json
 193 |     from pathlib import Path as _Path
 194 | 
 195 |     status_file = _Path(__file__).resolve().parent.parent.parent / "state" / "nostr_relay_status.json"
 196 |     try:
 197 |         if status_file.exists():
 198 |             data = _json.loads(status_file.read_text(encoding="utf-8"))
 199 |             if isinstance(data, list) and data:
 200 |                 return data
 201 |     except Exception as e:
 202 |         logger.debug("Could not read relay status file: %s", e)
 203 | 
 204 |     # Fallback: static disconnected
 205 |     relays = [
 206 |         "wss://relay.damus.io",
 207 |         "wss://nos.lol",
 208 |         "wss://relay.nostr.band",
 209 |         "wss://relay.primal.net",
 210 |     ]
 211 |     return [
 212 |         {
 213 |             "relay": r,
 214 |             "connected": False,
 215 |             "last_event_at": None,
 216 |             "events_today": 0,
 217 |         }
 218 |         for r in relays
 219 |     ]
 220 | 
 221 | 
 222 | def get_tracked_pubkeys() -> List[Dict]:
 223 |     """Return all tracked pubkeys from DB."""
 224 |     try:
 225 |         from app import app, db
 226 |         import models
 227 | 
 228 |         with app.app_context():
 229 |             rows = db.session.execute(
 230 |                 db.select(models.NostrTrackedPubkey)
 231 |                 .order_by(models.NostrTrackedPubkey.follower_tier.desc())
 232 |             ).scalars().all()
 233 |             return [
 234 |                 {
 235 |                     "pubkey": r.pubkey,
 236 |                     "display_name": r.display_name,
 237 |                     "nip05": r.nip05,
 238 |                     "follower_tier": r.follower_tier,
 239 |                     "added_at": r.added_at.isoformat() if r.added_at else None,
 240 |                 }
 241 |                 for r in rows
 242 |             ]
 243 |     except Exception as e:
 244 |         logger.error("get_tracked_pubkeys error: %s", e)
 245 |         return []
 246 | 
 247 | 
 248 | def get_stats() -> Dict:
 249 |     """Return aggregate stats for the admin dashboard."""
 250 |     try:
 251 |         from app import app, db
 252 |         import models
 253 | 
 254 |         with app.app_context():
 255 |             total = db.session.execute(
 256 |                 db.select(db.func.count(models.NostrMonitorEvent.id))
 257 |             ).scalar() or 0
 258 | 
 259 |             cutoff = int(time.time()) - 86400
 260 |             today = db.session.execute(
 261 |                 db.select(db.func.count(models.NostrMonitorEvent.id))
 262 |                 .where(models.NostrMonitorEvent.created_at >= cutoff)
 263 |             ).scalar() or 0
 264 | 
 265 |             tracked = db.session.execute(
 266 |                 db.select(db.func.count(models.NostrTrackedPubkey.id))
 267 |             ).scalar() or 0
 268 | 
 269 |             return {
 270 |                 "total_events": total,
 271 |                 "events_today": today,
 272 |                 "tracked_pubkeys": tracked,
 273 |             }
 274 |     except Exception as e:
 275 |         logger.error("get_stats error: %s", e)
 276 |         return {"total_events": 0, "events_today": 0, "tracked_pubkeys": 0}
 277 | 
```

### File: core/templates/nostr.html (800 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Nostr Intelligence — Censorship-Resistant Bitcoin Signal | Protocol Pulse{% endblock %}
   3 | 
   4 | {% block meta_description %}Real-time Bitcoin signal from Nostr — the censorship-resistant protocol. Top posts scored by engagement, relay status, and Protocol Pulse's own Nostr feed.{% endblock %}
   5 | 
   6 | {% block og_meta %}
   7 | <meta property="og:title" content="Nostr Intelligence — Protocol Pulse">
   8 | <meta property="og:description" content="Live Bitcoin signal from Nostr. Censorship-resistant, scored by engagement. Follow Protocol Pulse on Nostr.">
   9 | <meta property="og:type" content="website">
  10 | <meta property="og:site_name" content="Protocol Pulse">
  11 | <meta property="og:image" content="{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}">
  12 | <meta property="og:url" content="{{ request.url }}">
  13 | <meta name="twitter:card" content="summary_large_image">
  14 | <meta name="twitter:site" content="@ProtocolPulse">
  15 | {% endblock %}
  16 | 
  17 | {% block head %}
  18 | <style>
  19 | /* ================================================================
  20 |    NOSTR INTELLIGENCE PAGE — Protocol Pulse F4
  21 |    Design: Dark terminal × Bitcoin orange × Nostr purple accent
  22 |    ================================================================ */
  23 | :root {
  24 |     --ni-bg:        #000000;
  25 |     --ni-surface:   #0a0a0a;
  26 |     --ni-surface2:  #111111;
  27 |     --ni-border:    rgba(255,255,255,0.07);
  28 |     --ni-red:       #dc2626;
  29 |     --ni-orange:    #f97316;
  30 |     --ni-purple:    #a855f7;
  31 |     --ni-green:     #22c55e;
  32 |     --ni-yellow:    #eab308;
  33 |     --ni-text:      #e5e5e5;
  34 |     --ni-muted:     rgba(255,255,255,0.45);
  35 |     --ni-mono:      'JetBrains Mono', monospace;
  36 |     --ni-sans:      'DM Sans', sans-serif;
  37 | }
  38 | 
  39 | body { background: var(--ni-bg) !important; }
  40 | 
  41 | /* ── Header ── */
  42 | .ni-hero {
  43 |     padding: 100px 0 48px;
  44 |     text-align: center;
  45 |     position: relative;
  46 |     overflow: hidden;
  47 | }
  48 | .ni-hero::before {
  49 |     content: '';
  50 |     position: absolute;
  51 |     inset: 0;
  52 |     background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(168,85,247,0.08) 0%, transparent 70%);
  53 |     pointer-events: none;
  54 | }
  55 | .ni-eyebrow {
  56 |     font-family: var(--ni-mono);
  57 |     font-size: 0.72rem;
  58 |     letter-spacing: 0.18em;
  59 |     color: var(--ni-purple);
  60 |     text-transform: uppercase;
  61 |     margin-bottom: 12px;
  62 | }
  63 | .ni-title {
  64 |     font-family: var(--ni-sans);
  65 |     font-size: clamp(2rem, 5vw, 3.2rem);
  66 |     font-weight: 700;
  67 |     color: #fff;
  68 |     margin-bottom: 10px;
  69 |     line-height: 1.1;
  70 | }
  71 | .ni-title span { color: var(--ni-orange); }
  72 | .ni-subtitle {
  73 |     font-family: var(--ni-sans);
  74 |     font-size: 1.05rem;
  75 |     color: var(--ni-muted);
  76 |     max-width: 560px;
  77 |     margin: 0 auto 32px;
  78 | }
  79 | .ni-pulse-dot {
  80 |     display: inline-block;
  81 |     width: 8px; height: 8px;
  82 |     border-radius: 50%;
  83 |     background: var(--ni-green);
  84 |     animation: ni-blink 1.6s ease-in-out infinite;
  85 |     margin-right: 6px;
  86 |     vertical-align: middle;
  87 | }
  88 | @keyframes ni-blink {
  89 |     0%,100% { opacity: 1; }
  90 |     50%      { opacity: 0.25; }
  91 | }
  92 | 
  93 | /* ── What is Nostr section ── */
  94 | .ni-section { padding: 0 0 40px; }
  95 | .ni-section-label {
  96 |     font-family: var(--ni-mono);
  97 |     font-size: 0.68rem;
  98 |     letter-spacing: 0.2em;
  99 |     color: var(--ni-purple);
 100 |     text-transform: uppercase;
 101 |     margin-bottom: 16px;
 102 |     display: flex;
 103 |     align-items: center;
 104 |     gap: 10px;
 105 | }
 106 | .ni-section-label::after {
 107 |     content: '';
 108 |     flex: 1;
 109 |     height: 1px;
 110 |     background: var(--ni-border);
 111 | }
 112 | .ni-card {
 113 |     background: var(--ni-surface);
 114 |     border: 1px solid var(--ni-border);
 115 |     border-radius: 12px;
 116 |     padding: 28px;
 117 |     margin-bottom: 20px;
 118 |     transition: border-color 0.2s;
 119 | }
 120 | .ni-card:hover { border-color: rgba(168,85,247,0.25); }
 121 | 
 122 | /* ── What is Nostr explainer ── */
 123 | .ni-explainer p {
 124 |     font-family: var(--ni-sans);
 125 |     font-size: 1rem;
 126 |     color: var(--ni-text);
 127 |     line-height: 1.7;
 128 |     margin-bottom: 14px;
 129 | }
 130 | .ni-explainer p:last-child { margin-bottom: 0; }
 131 | .ni-highlight { color: var(--ni-orange); font-weight: 600; }
 132 | 
 133 | /* ── Follow CTA ── */
 134 | .ni-follow-card {
 135 |     background: linear-gradient(135deg, #0a0a0a 0%, #150a1e 100%);
 136 |     border: 1px solid rgba(168,85,247,0.3);
 137 |     border-radius: 12px;
 138 |     padding: 28px;
 139 |     display: flex;
 140 |     align-items: center;
 141 |     gap: 28px;
 142 |     flex-wrap: wrap;
 143 | }
 144 | .ni-qr-placeholder {
 145 |     width: 110px; height: 110px;
 146 |     background: #fff;
 147 |     border-radius: 8px;
 148 |     display: flex;
 149 |     align-items: center;
 150 |     justify-content: center;
 151 |     flex-shrink: 0;
 152 |     overflow: hidden;
 153 | }
 154 | .ni-qr-placeholder canvas, .ni-qr-placeholder img { width: 100%; height: 100%; }
 155 | .ni-follow-info { flex: 1; min-width: 200px; }
 156 | .ni-follow-label {
 157 |     font-family: var(--ni-mono);
 158 |     font-size: 0.68rem;
 159 |     letter-spacing: 0.15em;
 160 |     color: var(--ni-purple);
 161 |     text-transform: uppercase;
 162 |     margin-bottom: 8px;
 163 | }
 164 | .ni-npub {
 165 |     font-family: var(--ni-mono);
 166 |     font-size: 0.78rem;
 167 |     color: var(--ni-orange);
 168 |     word-break: break-all;
 169 |     background: rgba(249,115,22,0.07);
 170 |     border: 1px solid rgba(249,115,22,0.15);
 171 |     border-radius: 6px;
 172 |     padding: 8px 12px;
 173 |     margin-bottom: 12px;
 174 |     cursor: pointer;
 175 |     transition: background 0.2s;
 176 | }
 177 | .ni-npub:hover { background: rgba(249,115,22,0.14); }
 178 | .ni-copy-hint {
 179 |     font-family: var(--ni-mono);
 180 |     font-size: 0.65rem;
 181 |     color: var(--ni-muted);
 182 |     margin-top: 4px;
 183 | }
 184 | .ni-copy-hint.copied { color: var(--ni-green); }
 185 | .ni-follow-apps {
 186 |     display: flex;
 187 |     gap: 8px;
 188 |     flex-wrap: wrap;
 189 |     margin-top: 10px;
 190 | }
 191 | .ni-app-badge {
 192 |     font-family: var(--ni-mono);
 193 |     font-size: 0.68rem;
 194 |     padding: 4px 10px;
 195 |     border-radius: 20px;
 196 |     border: 1px solid var(--ni-border);
 197 |     color: var(--ni-muted);
 198 |     text-decoration: none;
 199 |     transition: all 0.2s;
 200 | }
 201 | .ni-app-badge:hover {
 202 |     border-color: rgba(168,85,247,0.4);
 203 |     color: var(--ni-purple);
 204 | }
 205 | 
 206 | /* ── Top signal feed ── */
 207 | .ni-feed-header {
 208 |     display: flex;
 209 |     align-items: center;
 210 |     justify-content: space-between;
 211 |     margin-bottom: 16px;
 212 |     flex-wrap: wrap;
 213 |     gap: 10px;
 214 | }
 215 | .ni-refresh-info {
 216 |     font-family: var(--ni-mono);
 217 |     font-size: 0.68rem;
 218 |     color: var(--ni-muted);
 219 |     display: flex;
 220 |     align-items: center;
 221 |     gap: 6px;
 222 | }
 223 | .ni-countdown {
 224 |     color: var(--ni-orange);
 225 |     font-weight: 600;
 226 | }
 227 | 
 228 | /* Post cards */
 229 | .ni-post {
 230 |     background: var(--ni-surface);
 231 |     border: 1px solid var(--ni-border);
 232 |     border-radius: 10px;
 233 |     padding: 18px 20px;
 234 |     margin-bottom: 12px;
 235 |     transition: border-color 0.2s, transform 0.15s;
 236 |     cursor: default;
 237 | }
 238 | .ni-post:hover {
 239 |     border-color: rgba(220,38,38,0.3);
 240 |     transform: translateX(2px);
 241 | }
 242 | .ni-post-header {
 243 |     display: flex;
 244 |     align-items: center;
 245 |     justify-content: space-between;
 246 |     margin-bottom: 10px;
 247 |     gap: 10px;
 248 |     flex-wrap: wrap;
 249 | }
 250 | .ni-author {
 251 |     display: flex;
 252 |     align-items: center;
 253 |     gap: 8px;
 254 | }
 255 | .ni-author-avatar {
 256 |     width: 32px; height: 32px;
 257 |     border-radius: 50%;
 258 |     background: linear-gradient(135deg, var(--ni-purple), var(--ni-red));
 259 |     display: flex;
 260 |     align-items: center;
 261 |     justify-content: center;
 262 |     font-family: var(--ni-mono);
 263 |     font-size: 0.7rem;
 264 |     color: #fff;
 265 |     font-weight: 700;
 266 |     flex-shrink: 0;
 267 | }
 268 | .ni-pubkey-short {
 269 |     font-family: var(--ni-mono);
 270 |     font-size: 0.72rem;
 271 |     color: var(--ni-muted);
 272 | }
 273 | .ni-score-badge {
 274 |     display: flex;
 275 |     align-items: center;
 276 |     gap: 6px;
 277 | }
 278 | .ni-score {
 279 |     font-family: var(--ni-mono);
 280 |     font-size: 0.78rem;
 281 |     font-weight: 700;
 282 |     color: var(--ni-orange);
 283 |     background: rgba(249,115,22,0.08);
 284 |     border: 1px solid rgba(249,115,22,0.15);
 285 |     padding: 2px 8px;
 286 |     border-radius: 4px;
 287 | }
 288 | .ni-kind-badge {
 289 |     font-family: var(--ni-mono);
 290 |     font-size: 0.62rem;
 291 |     padding: 2px 6px;
 292 |     border-radius: 4px;
 293 |     border: 1px solid var(--ni-border);
 294 |     color: var(--ni-muted);
 295 | }
 296 | .ni-kind-badge.kind-30023 {
 297 |     border-color: rgba(168,85,247,0.3);
 298 |     color: var(--ni-purple);
 299 | }
 300 | .ni-post-content {
 301 |     font-family: var(--ni-sans);
 302 |     font-size: 0.92rem;
 303 |     color: var(--ni-text);
 304 |     line-height: 1.6;
 305 |     margin-bottom: 12px;
 306 |     word-break: break-word;
 307 | }
 308 | .ni-post-content.truncated { max-height: 4.8em; overflow: hidden; }
 309 | .ni-post-meta {
 310 |     display: flex;
 311 |     align-items: center;
 312 |     gap: 14px;
 313 |     flex-wrap: wrap;
 314 | }
 315 | .ni-meta-item {
 316 |     font-family: var(--ni-mono);
 317 |     font-size: 0.65rem;
 318 |     color: var(--ni-muted);
 319 |     display: flex;
 320 |     align-items: center;
 321 |     gap: 4px;
 322 | }
 323 | .ni-meta-item i { font-size: 0.6rem; }
 324 | .ni-meta-item.zap { color: var(--ni-yellow); }
 325 | .ni-relay-tag {
 326 |     font-family: var(--ni-mono);
 327 |     font-size: 0.6rem;
 328 |     color: rgba(168,85,247,0.6);
 329 |     margin-left: auto;
 330 | }
 331 | .ni-open-link {
 332 |     font-family: var(--ni-mono);
 333 |     font-size: 0.65rem;
 334 |     color: var(--ni-muted);
 335 |     text-decoration: none;
 336 |     padding: 3px 8px;
 337 |     border: 1px solid var(--ni-border);
 338 |     border-radius: 4px;
 339 |     transition: all 0.2s;
 340 | }
 341 | .ni-open-link:hover {
 342 |     border-color: rgba(168,85,247,0.4);
 343 |     color: var(--ni-purple);
 344 | }
 345 | 
 346 | /* Empty / loading states */
 347 | .ni-loading {
 348 |     text-align: center;
 349 |     padding: 60px 20px;
 350 |     font-family: var(--ni-mono);
 351 |     font-size: 0.85rem;
 352 |     color: var(--ni-muted);
 353 | }
 354 | .ni-spinner {
 355 |     display: inline-block;
 356 |     width: 20px; height: 20px;
 357 |     border: 2px solid rgba(168,85,247,0.2);
 358 |     border-top-color: var(--ni-purple);
 359 |     border-radius: 50%;
 360 |     animation: ni-spin 0.8s linear infinite;
 361 |     margin-bottom: 12px;
 362 | }
 363 | @keyframes ni-spin {
 364 |     to { transform: rotate(360deg); }
 365 | }
 366 | .ni-empty {
 367 |     text-align: center;
 368 |     padding: 48px 20px;
 369 |     font-family: var(--ni-mono);
 370 |     font-size: 0.8rem;
 371 |     color: var(--ni-muted);
 372 | }
 373 | .ni-error {
 374 |     font-family: var(--ni-mono);
 375 |     font-size: 0.8rem;
 376 |     color: var(--ni-red);
 377 |     background: rgba(220,38,38,0.06);
 378 |     border: 1px solid rgba(220,38,38,0.15);
 379 |     border-radius: 8px;
 380 |     padding: 14px 18px;
 381 |     margin-bottom: 16px;
 382 |     display: none;
 383 | }
 384 | 
 385 | /* ── Relay status ── */
 386 | .ni-relay-grid {
 387 |     display: grid;
 388 |     grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
 389 |     gap: 12px;
 390 | }
 391 | .ni-relay-item {
 392 |     background: var(--ni-surface2);
 393 |     border: 1px solid var(--ni-border);
 394 |     border-radius: 8px;
 395 |     padding: 14px 16px;
 396 |     display: flex;
 397 |     align-items: center;
 398 |     gap: 12px;
 399 |     transition: border-color 0.3s;
 400 | }
 401 | .ni-relay-item.connected { border-color: rgba(34,197,94,0.2); }
 402 | .ni-relay-item.disconnected { border-color: rgba(220,38,38,0.15); }
 403 | .ni-relay-dot {
 404 |     width: 10px; height: 10px;
 405 |     border-radius: 50%;
 406 |     flex-shrink: 0;
 407 |     background: var(--ni-red);
 408 | }
 409 | .ni-relay-item.connected .ni-relay-dot {
 410 |     background: var(--ni-green);
 411 |     animation: ni-blink 2s ease-in-out infinite;
 412 | }
 413 | .ni-relay-info { flex: 1; min-width: 0; }
 414 | .ni-relay-url {
 415 |     font-family: var(--ni-mono);
 416 |     font-size: 0.7rem;
 417 |     color: var(--ni-text);
 418 |     white-space: nowrap;
 419 |     overflow: hidden;
 420 |     text-overflow: ellipsis;
 421 | }
 422 | .ni-relay-stat {
 423 |     font-family: var(--ni-mono);
 424 |     font-size: 0.6rem;
 425 |     color: var(--ni-muted);
 426 |     margin-top: 2px;
 427 | }
 428 | .ni-relay-status-text {
 429 |     font-family: var(--ni-mono);
 430 |     font-size: 0.62rem;
 431 |     font-weight: 700;
 432 |     letter-spacing: 0.05em;
 433 | }
 434 | .connected .ni-relay-status-text { color: var(--ni-green); }
 435 | .disconnected .ni-relay-status-text { color: var(--ni-red); }
 436 | 
 437 | /* ── Score legend ── */
 438 | .ni-legend {
 439 |     display: flex;
 440 |     gap: 20px;
 441 |     flex-wrap: wrap;
 442 |     font-family: var(--ni-mono);
 443 |     font-size: 0.65rem;
 444 |     color: var(--ni-muted);
 445 |     margin-bottom: 16px;
 446 | }
 447 | .ni-legend-item { display: flex; align-items: center; gap: 5px; }
 448 | .ni-legend-dot {
 449 |     width: 6px; height: 6px;
 450 |     border-radius: 50%;
 451 | }
 452 | 
 453 | /* ── Mobile ── */
 454 | @media (max-width: 768px) {
 455 |     .ni-hero { padding: 80px 0 36px; }
 456 |     .ni-follow-card { flex-direction: column; align-items: flex-start; }
 457 |     .ni-qr-placeholder { width: 90px; height: 90px; }
 458 |     .ni-relay-grid { grid-template-columns: 1fr; }
 459 |     .ni-post-header { flex-direction: column; align-items: flex-start; }
 460 | }
 461 | </style>
 462 | {% endblock %}
 463 | 
 464 | {% block content %}
 465 | <div style="background: var(--ni-bg, #000); min-height: 100vh;">
 466 | <div class="container" style="max-width: 860px;">
 467 | 
 468 | <!-- ═══════════════════════════════════════════
 469 |      HERO
 470 | ═══════════════════════════════════════════ -->
 471 | <div class="ni-hero">
 472 |     <div class="ni-eyebrow">⚡ Protocol Pulse</div>
 473 |     <h1 class="ni-title">NOSTR <span>INTELLIGENCE</span></h1>
 474 |     <p class="ni-subtitle">
 475 |         Censorship-resistant Bitcoin signal — scored, ranked, and live.
 476 |         <span class="ni-pulse-dot"></span>Monitoring 4 relays.
 477 |     </p>
 478 | </div>
 479 | 
 480 | <!-- ═══════════════════════════════════════════
 481 |      WHAT IS NOSTR?
 482 | ═══════════════════════════════════════════ -->
 483 | <div class="ni-section">
 484 |     <div class="ni-section-label">What is Nostr?</div>
 485 |     <div class="ni-card ni-explainer">
 486 |         <p>
 487 |             <span class="ni-highlight">Nostr</span> (Notes and Other Stuff Transmitted by Relays)
 488 |             is a decentralized communication protocol built for censorship resistance.
 489 |             Unlike X (Twitter) or Facebook, no single company can ban you, shadow-ban your account,
 490 |             or decide what you're allowed to say — your identity is a cryptographic keypair you control.
 491 |         </p>
 492 |         <p>
 493 |             Bitcoin's cypherpunk community has adopted Nostr as its primary uncensorable layer.
 494 |             Developers, analysts, and OGs post <span class="ni-highlight">raw signal</span> here that
 495 |             surfaces 15–30 minutes before mainstream crypto media catches on.
 496 |             Engagement is measured in <span class="ni-highlight">zaps</span> — actual Bitcoin payments
 497 |             via Lightning that represent real conviction, not empty likes.
 498 |         </p>
 499 |         <p>
 500 |             Protocol Pulse monitors Nostr continuously, scoring every post by engagement quality
 501 |             (zaps 10× > reposts 3× > replies 2× > reactions 1×) and Bitcoin relevance, then
 502 |             surfaces the top signal for you here — updated every 5 minutes.
 503 |         </p>
 504 |     </div>
 505 | </div>
 506 | 
 507 | <!-- ═══════════════════════════════════════════
 508 |      FOLLOW PROTOCOL PULSE
 509 | ═══════════════════════════════════════════ -->
 510 | <div class="ni-section">
 511 |     <div class="ni-section-label">Follow Protocol Pulse on Nostr</div>
 512 |     <div class="ni-follow-card">
 513 |         <div class="ni-qr-placeholder" id="qr-container">
 514 |             <!-- QR generated by JS -->
 515 |             <canvas id="qr-canvas"></canvas>
 516 |         </div>
 517 |         <div class="ni-follow-info">
 518 |             <div class="ni-follow-label">Protocol Pulse npub</div>
 519 |             <div class="ni-npub" id="npub-display" onclick="copyNpub()" title="Click to copy">
 520 |                 {{ pp_npub }}
 521 |             </div>
 522 |             <div class="ni-copy-hint" id="copy-hint">Click to copy npub address</div>
 523 |             <div class="ni-follow-apps">
 524 |                 <a href="https://damus.io" target="_blank" rel="noopener" class="ni-app-badge">Damus (iOS)</a>
 525 |                 <a href="https://primal.net" target="_blank" rel="noopener" class="ni-app-badge">Primal</a>
 526 |                 <a href="https://iris.to" target="_blank" rel="noopener" class="ni-app-badge">Iris.to</a>
 527 |                 <a href="https://snort.social" target="_blank" rel="noopener" class="ni-app-badge">Snort</a>
 528 |                 <a href="https://njump.me/{{ pp_npub }}" target="_blank" rel="noopener" class="ni-app-badge">njump.me</a>
 529 |             </div>
 530 |         </div>
 531 |     </div>
 532 | </div>
 533 | 
 534 | <!-- ═══════════════════════════════════════════
 535 |      TOP SIGNAL RIGHT NOW
 536 | ═══════════════════════════════════════════ -->
 537 | <div class="ni-section">
 538 |     <div class="ni-section-label">Top Signal Right Now</div>
 539 | 
 540 |     <div class="ni-feed-header">
 541 |         <div class="ni-legend">
 542 |             <div class="ni-legend-item">
 543 |                 <div class="ni-legend-dot" style="background:#eab308;"></div>⚡ Zap ×10
 544 |             </div>
 545 |             <div class="ni-legend-item">
 546 |                 <div class="ni-legend-dot" style="background:#3b82f6;"></div>↩ Quote ×5
 547 |             </div>
 548 |             <div class="ni-legend-item">
 549 |                 <div class="ni-legend-dot" style="background:#22c55e;"></div>↗ Repost ×3
 550 |             </div>
 551 |             <div class="ni-legend-item">
 552 |                 <div class="ni-legend-dot" style="background:#a855f7;"></div>💬 Reply ×2
 553 |             </div>
 554 |         </div>
 555 |         <div class="ni-refresh-info">
 556 |             Auto-refresh in <span class="ni-countdown" id="refresh-countdown">5:00</span>
 557 |         </div>
 558 |     </div>
 559 | 
 560 |     <div class="ni-error" id="feed-error">
 561 |         Failed to load Nostr signal. Relay connection may be down — retrying...
 562 |     </div>
 563 | 
 564 |     <div id="feed-container">
 565 |         {% if top_content %}
 566 |             {% for post in top_content %}
 567 |             <div class="ni-post" data-event-id="{{ post.event_id }}">
 568 |                 <div class="ni-post-header">
 569 |                     <div class="ni-author">
 570 |                         <div class="ni-author-avatar">{{ post.pubkey_short[:2].upper() if post.pubkey_short else 'NK' }}</div>
 571 |                         <span class="ni-pubkey-short">{{ post.pubkey_short }}</span>
 572 |                     </div>
 573 |                     <div class="ni-score-badge">
 574 |                         <span class="ni-score">{{ post.engagement_score }}</span>
 575 |                         <span class="ni-kind-badge {% if post.kind == 30023 %}kind-30023{% endif %}">
 576 |                             {% if post.kind == 30023 %}ARTICLE{% else %}NOTE{% endif %}
 577 |                         </span>
 578 |                     </div>
 579 |                 </div>
 580 |                 <div class="ni-post-content">{{ post.content[:400] }}{% if post.content|length > 400 %}...{% endif %}</div>
 581 |                 <div class="ni-post-meta">
 582 |                     {% if post.zaps > 0 %}
 583 |                     <span class="ni-meta-item zap"><i class="fas fa-bolt"></i> {{ post.zaps }}</span>
 584 |                     {% endif %}
 585 |                     {% if post.reposts > 0 %}
 586 |                     <span class="ni-meta-item"><i class="fas fa-retweet"></i> {{ post.reposts }}</span>
 587 |                     {% endif %}
 588 |                     {% if post.replies > 0 %}
 589 |                     <span class="ni-meta-item"><i class="fas fa-comment"></i> {{ post.replies }}</span>
 590 |                     {% endif %}
 591 |                     {% if post.reactions > 0 %}
 592 |                     <span class="ni-meta-item"><i class="fas fa-heart"></i> {{ post.reactions }}</span>
 593 |                     {% endif %}
 594 |                     <span class="ni-meta-item"><i class="fas fa-clock"></i>
 595 |                         {{ post.created_at_iso[:10] if post.created_at_iso else '—' }}
 596 |                     </span>
 597 |                     {% if post.nostr_link %}
 598 |                     <a href="{{ post.nostr_link }}" target="_blank" rel="noopener" class="ni-open-link">
 599 |                         View <i class="fas fa-external-link-alt"></i>
 600 |                     </a>
 601 |                     {% endif %}
 602 |                     <span class="ni-relay-tag">{{ post.relay_source.replace('wss://','') if post.relay_source else '' }}</span>
 603 |                 </div>
 604 |             </div>
 605 |             {% endfor %}
 606 |         {% else %}
 607 |             <div class="ni-empty" id="feed-empty">
 608 |                 <div class="ni-spinner"></div><br>
 609 |                 Monitor is warming up — events will appear within 60 seconds of first relay connection.
 610 |             </div>
 611 |         {% endif %}
 612 |     </div>
 613 | </div>
 614 | 
 615 | <!-- ═══════════════════════════════════════════
 616 |      RELAY STATUS
 617 | ═══════════════════════════════════════════ -->
 618 | <div class="ni-section">
 619 |     <div class="ni-section-label">Relay Status</div>
 620 |     <div class="ni-relay-grid" id="relay-grid">
 621 |         {% for relay in relay_status %}
 622 |         <div class="ni-relay-item {{ 'connected' if relay.connected else 'disconnected' }}" data-relay="{{ relay.relay }}">
 623 |             <div class="ni-relay-dot"></div>
 624 |             <div class="ni-relay-info">
 625 |                 <div class="ni-relay-url">{{ relay.relay.replace('wss://','') }}</div>
 626 |                 <div class="ni-relay-stat">
 627 |                     {% if relay.events_today %}{{ relay.events_today }} events today{% else %}No events yet{% endif %}
 628 |                     {% if relay.last_event_at %} · {{ relay.last_event_at[:16] if relay.last_event_at else '' }}{% endif %}
 629 |                 </div>
 630 |             </div>
 631 |             <div class="ni-relay-status-text">{{ 'LIVE' if relay.connected else 'OFF' }}</div>
 632 |         </div>
 633 |         {% endfor %}
 634 |     </div>
 635 | </div>
 636 | 
 637 | </div><!-- /container -->
 638 | </div><!-- /bg wrapper -->
 639 | {% endblock %}
 640 | 
 641 | {% block extra_js %}
 642 | <!-- QR Code library (lightweight, CDN) -->
 643 | <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
 644 | 
 645 | <script>
 646 | /* ── QR Code generation ── */
 647 | (function(){
 648 |     var npub = {{ pp_npub | tojson }};
 649 |     if (npub && typeof QRCode !== 'undefined') {
 650 |         QRCode.toCanvas(document.getElementById('qr-canvas'), npub, {
 651 |             width: 110,
 652 |             margin: 1,
 653 |             color: { dark: '#000000', light: '#ffffff' }
 654 |         }, function(err) {
 655 |             if (err) console.warn('QR error:', err);
 656 |         });
 657 |     }
 658 | })();
 659 | 
 660 | /* ── Copy npub ── */
 661 | function copyNpub() {
 662 |     var npub = document.getElementById('npub-display').textContent.trim();
 663 |     if (!npub) return;
 664 |     navigator.clipboard.writeText(npub).then(function() {
 665 |         var hint = document.getElementById('copy-hint');
 666 |         hint.textContent = 'Copied!';
 667 |         hint.classList.add('copied');
 668 |         setTimeout(function() {
 669 |             hint.textContent = 'Click to copy npub address';
 670 |             hint.classList.remove('copied');
 671 |         }, 2000);
 672 |     }).catch(function() {
 673 |         // Fallback for non-HTTPS
 674 |         var el = document.createElement('textarea');
 675 |         el.value = npub;
 676 |         document.body.appendChild(el);
 677 |         el.select();
 678 |         document.execCommand('copy');
 679 |         document.body.removeChild(el);
 680 |     });
 681 | }
 682 | 
 683 | /* ── Auto-refresh countdown (5 min) ── */
 684 | var REFRESH_SECS = 300;
 685 | var _remaining = REFRESH_SECS;
 686 | var _countdownEl = document.getElementById('refresh-countdown');
 687 | 
 688 | function _updateCountdown() {
 689 |     var m = Math.floor(_remaining / 60);
 690 |     var s = _remaining % 60;
 691 |     if (_countdownEl) {
 692 |         _countdownEl.textContent = m + ':' + (s < 10 ? '0' : '') + s;
 693 |     }
 694 |     if (_remaining <= 0) {
 695 |         refreshFeed();
 696 |         _remaining = REFRESH_SECS;
 697 |     } else {
 698 |         _remaining--;
 699 |     }
 700 | }
 701 | setInterval(_updateCountdown, 1000);
 702 | 
 703 | /* ── Live feed refresh ── */
 704 | function refreshFeed() {
 705 |     fetch('/api/nostr/top')
 706 |         .then(function(r) {
 707 |             if (!r.ok) throw new Error('HTTP ' + r.status);
 708 |             return r.json();
 709 |         })
 710 |         .then(function(data) {
 711 |             document.getElementById('feed-error').style.display = 'none';
 712 |             renderFeed(data);
 713 |         })
 714 |         .catch(function(err) {
 715 |             var errEl = document.getElementById('feed-error');
 716 |             if (errEl) errEl.style.display = 'block';
 717 |             console.warn('Feed refresh error:', err);
 718 |         });
 719 | }
 720 | 
 721 | function renderFeed(posts) {
 722 |     var container = document.getElementById('feed-container');
 723 |     if (!container) return;
 724 |     if (!posts || posts.length === 0) {
 725 |         container.innerHTML = '<div class="ni-empty">No signal yet — monitor is connecting to relays...</div>';
 726 |         return;
 727 |     }
 728 |     var html = posts.map(function(p) {
 729 |         var kind_label = p.kind === 30023 ? 'ARTICLE' : 'NOTE';
 730 |         var kind_class = p.kind === 30023 ? 'kind-30023' : '';
 731 |         var avatar_init = (p.pubkey_short || 'NK').substring(0,2).toUpperCase();
 732 |         var content_safe = escapeHtml((p.content || '').substring(0, 400));
 733 |         var has_more = (p.content || '').length > 400;
 734 |         var time_str = p.created_at_iso ? p.created_at_iso.substring(0,10) : '—';
 735 |         var relay_short = (p.relay_source || '').replace('wss://','');
 736 |         var nostr_link = p.nostr_link || '';
 737 | 
 738 |         var meta_parts = [];
 739 |         if (p.zaps > 0) meta_parts.push('<span class="ni-meta-item zap"><i class="fas fa-bolt"></i> ' + p.zaps + '</span>');
 740 |         if (p.reposts > 0) meta_parts.push('<span class="ni-meta-item"><i class="fas fa-retweet"></i> ' + p.reposts + '</span>');
 741 |         if (p.replies > 0) meta_parts.push('<span class="ni-meta-item"><i class="fas fa-comment"></i> ' + p.replies + '</span>');
 742 |         if (p.reactions > 0) meta_parts.push('<span class="ni-meta-item"><i class="fas fa-heart"></i> ' + p.reactions + '</span>');
 743 |         meta_parts.push('<span class="ni-meta-item"><i class="fas fa-clock"></i> ' + time_str + '</span>');
 744 |         if (nostr_link) meta_parts.push('<a href="' + nostr_link + '" target="_blank" rel="noopener" class="ni-open-link">View <i class="fas fa-external-link-alt"></i></a>');
 745 |         if (relay_short) meta_parts.push('<span class="ni-relay-tag">' + escapeHtml(relay_short) + '</span>');
 746 | 
 747 |         return '<div class="ni-post" data-event-id="' + escapeHtml(p.event_id || '') + '">' +
 748 |             '<div class="ni-post-header">' +
 749 |                 '<div class="ni-author">' +
 750 |                     '<div class="ni-author-avatar">' + avatar_init + '</div>' +
 751 |                     '<span class="ni-pubkey-short">' + escapeHtml(p.pubkey_short || '') + '</span>' +
 752 |                 '</div>' +
 753 |                 '<div class="ni-score-badge">' +
 754 |                     '<span class="ni-score">' + (p.engagement_score || 0) + '</span>' +
 755 |                     '<span class="ni-kind-badge ' + kind_class + '">' + kind_label + '</span>' +
 756 |                 '</div>' +
 757 |             '</div>' +
 758 |             '<div class="ni-post-content">' + content_safe + (has_more ? '...' : '') + '</div>' +
 759 |             '<div class="ni-post-meta">' + meta_parts.join('') + '</div>' +
 760 |         '</div>';
 761 |     }).join('');
 762 |     container.innerHTML = html;
 763 | }
 764 | 
 765 | /* ── Relay status refresh (every 30s) ── */
 766 | function refreshRelayStatus() {
 767 |     fetch('/api/nostr/relay-status')
 768 |         .then(function(r) { return r.json(); })
 769 |         .then(function(data) {
 770 |             if (!data || !data.length) return;
 771 |             data.forEach(function(relay) {
 772 |                 var el = document.querySelector('[data-relay="' + relay.relay + '"]');
 773 |                 if (!el) return;
 774 |                 el.className = 'ni-relay-item ' + (relay.connected ? 'connected' : 'disconnected');
 775 |                 var stat = el.querySelector('.ni-relay-stat');
 776 |                 if (stat) {
 777 |                     var ev = relay.events_today || 0;
 778 |                     stat.textContent = ev + ' events today';
 779 |                 }
 780 |                 var txt = el.querySelector('.ni-relay-status-text');
 781 |                 if (txt) txt.textContent = relay.connected ? 'LIVE' : 'OFF';
 782 |             });
 783 |         })
 784 |         .catch(function() {});
 785 | }
 786 | setInterval(refreshRelayStatus, 30000);
 787 | 
 788 | /* ── Utility ── */
 789 | function escapeHtml(str) {
 790 |     if (!str) return '';
 791 |     return String(str)
 792 |         .replace(/&/g, '&amp;')
 793 |         .replace(/</g, '&lt;')
 794 |         .replace(/>/g, '&gt;')
 795 |         .replace(/"/g, '&quot;')
 796 |         .replace(/'/g, '&#39;');
 797 | }
 798 | </script>
 799 | {% endblock %}
 800 | 
```

### File: cron/nostr_cron.py (115 lines)
```
   1 | """
   2 | cron/nostr_cron.py — Hourly Nostr top-content refresh.
   3 | 
   4 | Scheduled to run every hour via system cron or the PP scheduler.
   5 | Refreshes the nostr_monitor_events cache and prunes old low-score events.
   6 | """
   7 | import logging
   8 | import sys
   9 | import time
  10 | from datetime import datetime, timezone
  11 | from pathlib import Path
  12 | 
  13 | # Ensure project root is in path
  14 | _ROOT = Path(__file__).resolve().parent.parent
  15 | sys.path.insert(0, str(_ROOT))
  16 | sys.path.insert(0, str(_ROOT / "core"))
  17 | 
  18 | logger = logging.getLogger("nostr_cron")
  19 | logging.basicConfig(
  20 |     level=logging.INFO,
  21 |     format="%(asctime)s [nostr_cron] %(levelname)s %(message)s",
  22 | )
  23 | 
  24 | 
  25 | def prune_old_events(max_age_days: int = 7, min_score: float = 5.0) -> int:
  26 |     """
  27 |     Remove events older than max_age_days with score below min_score.
  28 |     Keeps top content and VIP pubkey content indefinitely.
  29 |     Returns number of rows deleted.
  30 |     """
  31 |     try:
  32 |         from app import app, db
  33 |         import models
  34 | 
  35 |         cutoff = int(time.time()) - (max_age_days * 86400)
  36 | 
  37 |         with app.app_context():
  38 |             # Get VIP pubkeys to protect their content
  39 |             vip_pubkeys = [
  40 |                 row.pubkey
  41 |                 for row in db.session.execute(
  42 |                     db.select(models.NostrTrackedPubkey).where(
  43 |                         models.NostrTrackedPubkey.follower_tier == "vip"
  44 |                     )
  45 |                 ).scalars().all()
  46 |             ]
  47 | 
  48 |             # Delete old low-score events not from VIP pubkeys
  49 |             query = (
  50 |                 db.delete(models.NostrMonitorEvent)
  51 |                 .where(models.NostrMonitorEvent.created_at < cutoff)
  52 |                 .where(models.NostrMonitorEvent.engagement_score < min_score)
  53 |             )
  54 |             if vip_pubkeys:
  55 |                 query = query.where(
  56 |                     ~models.NostrMonitorEvent.pubkey.in_(vip_pubkeys)
  57 |                 )
  58 | 
  59 |             result = db.session.execute(query)
  60 |             deleted = result.rowcount
  61 |             db.session.commit()
  62 |             logger.info("Pruned %d old low-score events", deleted)
  63 |             return deleted
  64 |     except Exception as e:
  65 |         logger.error("Prune error: %s", e)
  66 |         try:
  67 |             from app import db
  68 |             db.session.rollback()
  69 |         except Exception:
  70 |             pass
  71 |         return 0
  72 | 
  73 | 
  74 | def seed_pubkeys_if_needed() -> int:
  75 |     """Ensure tracked pubkeys are seeded."""
  76 |     try:
  77 |         from services.nostr_service import seed_tracked_pubkeys
  78 |         return seed_tracked_pubkeys()
  79 |     except Exception as e:
  80 |         logger.error("Seed pubkeys error: %s", e)
  81 |         return 0
  82 | 
  83 | 
  84 | def log_stats():
  85 |     """Log current collection stats."""
  86 |     try:
  87 |         from services.nostr_service import get_stats
  88 |         stats = get_stats()
  89 |         logger.info(
  90 |             "Stats: %d total events, %d today, %d tracked pubkeys",
  91 |             stats.get("total_events", 0),
  92 |             stats.get("events_today", 0),
  93 |             stats.get("tracked_pubkeys", 0),
  94 |         )
  95 |     except Exception as e:
  96 |         logger.error("Stats error: %s", e)
  97 | 
  98 | 
  99 | def run():
 100 |     """Main cron job: seed → prune → log."""
 101 |     logger.info("=== Nostr cron job starting === %s", datetime.now(timezone.utc).isoformat())
 102 | 
 103 |     seeded = seed_pubkeys_if_needed()
 104 |     if seeded:
 105 |         logger.info("Seeded %d new pubkeys", seeded)
 106 | 
 107 |     pruned = prune_old_events(max_age_days=7, min_score=5.0)
 108 |     log_stats()
 109 | 
 110 |     logger.info("=== Nostr cron job complete (pruned %d) ===", pruned)
 111 | 
 112 | 
 113 | if __name__ == "__main__":
 114 |     run()
 115 | 
```

### File: docs/audits/run_mu_audit.py (178 lines)
```
   1 | #!/usr/bin/env python3
   2 | import os, sys, json, time, threading
   3 | from pathlib import Path
   4 | from datetime import datetime
   5 | from dotenv import load_dotenv
   6 | 
   7 | load_dotenv(Path.home() / "protocol_pulse/.env")
   8 | 
   9 | JS   = (Path.home() / "protocol_pulse/static/js/media_unified_v4.js").read_text()
  10 | 
  11 | HTML_FACTS = """
  12 | EXACT HTML IDs: relay-status-bar, nostr-feed, nostr-count, highlights-feed,
  13 | signal-strength-gauge, signal-breakdown, sig-sentiment, sig-spaces, sig-composite,
  14 | signal-fill, telem-signal, health-nostr, health-nostr-col, health-highlights-col
  15 | 
  16 | RELAY BAR HTML:
  17 | <div id="relay-status-bar">
  18 |   <div class="mu-relay-item" data-relay="relay.damus.io">  <!-- NO wss:// -->
  19 |     <div class="mu-relay-dot"></div>
  20 |     <span class="mu-relay-name">damus</span>
  21 |     <span class="mu-relay-status">OFFLINE</span>  <!-- class=mu-relay-status NOT mu-relay-label -->
  22 |     <span class="mu-relay-count">0 notes</span>
  23 |   </div>
  24 | </div>
  25 | 
  26 | SIGNAL GAUGE HTML:
  27 | <div id="signal-strength-gauge">
  28 |   <div id="sig-composite">--</div>
  29 |   <div id="signal-breakdown">
  30 |     <span id="sig-sentiment">--</span>
  31 |     <span id="sig-spaces">--</span>
  32 |   </div>
  33 | </div>
  34 | NOTE: signal-fill and telem-signal are in telemetry ribbon, NOT in gauge section.
  35 | 
  36 | NOSTR_RELAYS in JS: wss://relay.damus.io, wss://nos.lol, wss://relay.nostr.band
  37 | rm.sockets keyed WITH wss://. data-relay HTML has NO wss:// prefix.
  38 | """
  39 | 
  40 | PROMPT = """You are auditing broken production JavaScript for a Bitcoin intelligence dashboard.
  41 | 
  42 | 3 features are broken and have NEVER worked:
  43 | 1. NOSTR FEED — all relays show OFFLINE, 0 notes
  44 | 2. VERIFIED HIGHLIGHTS — always blank (API returns 27 items)
  45 | 3. SIGNAL GAUGE — always shows -- and LOADING
  46 | 
  47 | HTML STRUCTURE:
  48 | """ + HTML_FACTS + """
  49 | 
  50 | FULL JS:
  51 | """ + JS[:16000] + """
  52 | 
  53 | Return ONLY valid JSON (no markdown, no code fences):
  54 | {
  55 |   "verdict": "one sentence on root causes",
  56 |   "npub_bug": "are npub strings valid hex for Nostr REQ authors filter? yes/no and why this matters",
  57 |   "signal_bug": "does updateSignalStrength() write to sig-sentiment/sig-spaces/sig-composite? or different IDs?",
  58 |   "highlights_bug": "trace fetchHighlights to renderHighlights - where exactly does it break?",
  59 |   "critical_bugs": [
  60 |     {
  61 |       "feature": "nostr or highlights or signal",
  62 |       "bug": "name",
  63 |       "location": "function",
  64 |       "root_cause": "why",
  65 |       "fix_before": "wrong code",
  66 |       "fix_after": "correct code"
  67 |     }
  68 |   ],
  69 |   "high_bugs": [],
  70 |   "score": 0
  71 | }"""
  72 | 
  73 | results = {}
  74 | errors = {}
  75 | 
  76 | def call_gemini():
  77 |     try:
  78 |         import google.generativeai as genai
  79 |         genai.configure(api_key=os.environ["GEMINI_API_KEY"])
  80 |         model = genai.GenerativeModel("gemini-2.0-flash")
  81 |         resp = model.generate_content(PROMPT)
  82 |         text = resp.text.strip()
  83 |         for fence in ["```json", "```"]:
  84 |             text = text.replace(fence, "")
  85 |         results["gemini"] = json.loads(text.strip())
  86 |         print("[GEMINI] Done score=" + str(results["gemini"].get("score","?")), file=sys.stderr)
  87 |     except Exception as e:
  88 |         errors["gemini"] = str(e)
  89 |         print("[GEMINI] ERROR: " + str(e), file=sys.stderr)
  90 | 
  91 | def call_gpt4o():
  92 |     try:
  93 |         from openai import OpenAI
  94 |         client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
  95 |         resp = client.chat.completions.create(
  96 |             model="gpt-4o",
  97 |             messages=[{"role": "user", "content": PROMPT}],
  98 |             response_format={"type": "json_object"},
  99 |             max_tokens=3000,
 100 |         )
 101 |         results["gpt4o"] = json.loads(resp.choices[0].message.content)
 102 |         print("[GPT4o] Done score=" + str(results["gpt4o"].get("score","?")), file=sys.stderr)
 103 |     except Exception as e:
 104 |         errors["gpt4o"] = str(e)
 105 |         print("[GPT4o] ERROR: " + str(e), file=sys.stderr)
 106 | 
 107 | def call_grok():
 108 |     try:
 109 |         from openai import OpenAI
 110 |         client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
 111 |         resp = client.chat.completions.create(
 112 |             model="grok-3-mini",
 113 |             messages=[{"role": "user", "content": PROMPT}],
 114 |             max_tokens=3000,
 115 |         )
 116 |         text = resp.choices[0].message.content.strip()
 117 |         for fence in ["```json", "```"]:
 118 |             text = text.replace(fence, "")
 119 |         results["grok"] = json.loads(text.strip())
 120 |         print("[GROK] Done score=" + str(results["grok"].get("score","?")), file=sys.stderr)
 121 |     except Exception as e:
 122 |         errors["grok"] = str(e)
 123 |         print("[GROK] ERROR: " + str(e), file=sys.stderr)
 124 | 
 125 | print("[AUDIT] Firing Round 1 in parallel...", file=sys.stderr)
 126 | threads = [threading.Thread(target=f) for f in [call_gemini, call_gpt4o, call_grok]]
 127 | for t in threads: t.start()
 128 | for t in threads: t.join(timeout=90)
 129 | print("[AUDIT] Round 1 complete. Got: " + str(list(results.keys())), file=sys.stderr)
 130 | 
 131 | # Round 2 synthesis
 132 | synth_prompt = """Synthesize these 3 code audits into a consensus prioritized fix list.
 133 | 
 134 | AUDIT RESULTS:
 135 | """ + json.dumps(results, indent=2)[:8000] + """
 136 | 
 137 | Return ONLY valid JSON:
 138 | {
 139 |   "consensus_verdict": "2 sentences on root causes",
 140 |   "winner": "gemini or gpt4o or grok",
 141 |   "winner_reason": "why most accurate",
 142 |   "priority_fixes": [
 143 |     {
 144 |       "priority": "P0 or P1 or P2",
 145 |       "feature": "nostr or highlights or signal",
 146 |       "fix": "description",
 147 |       "before": "exact wrong code",
 148 |       "after": "exact correct code",
 149 |       "agreed_by": ["gemini","gpt4o"]
 150 |     }
 151 |   ],
 152 |   "missed_by_all": "bugs none caught"
 153 | }"""
 154 | 
 155 | synthesis = {}
 156 | try:
 157 |     import anthropic
 158 |     client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY",""))
 159 |     msg = client.messages.create(
 160 |         model="claude-opus-4-5",
 161 |         max_tokens=2000,
 162 |         messages=[{"role": "user", "content": synth_prompt}]
 163 |     )
 164 |     text = msg.content[0].text.strip()
 165 |     for fence in ["```json", "```"]:
 166 |         text = text.replace(fence, "")
 167 |     synthesis = json.loads(text.strip())
 168 |     print("[SYNTH] Done winner=" + str(synthesis.get("winner","?")), file=sys.stderr)
 169 | except Exception as e:
 170 |     synthesis = {"error": str(e)}
 171 |     print("[SYNTH] ERROR: " + str(e), file=sys.stderr)
 172 | 
 173 | output = {"timestamp": datetime.now().isoformat(), "round1_results": results, "round1_errors": errors, "synthesis": synthesis}
 174 | out_path = Path.home() / "protocol_pulse/docs/audits/media_unified_audit.json"
 175 | out_path.parent.mkdir(exist_ok=True)
 176 | out_path.write_text(json.dumps(output, indent=2))
 177 | print(json.dumps(output))
 178 | 
```

### File: docs/intel/run_multi_llm_audit.py (182 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Protocol Pulse Intel Dashboard - Multi-LLM Audit Runner
   4 | Fires spec at Gemini 2.5 Pro, GPT-4o, and Grok simultaneously.
   5 | Synthesizes with Claude. Writes final report.
   6 | """
   7 | import os, sys, json, time, threading
   8 | from pathlib import Path
   9 | from datetime import datetime
  10 | 
  11 | SPEC_PATH = Path.home() / "protocol_pulse/docs/intel/INTEL_DASHBOARD_AUDIT_SPEC.md"
  12 | spec = SPEC_PATH.read_text()
  13 | 
  14 | AUDIT_PROMPT = """You are performing a senior technical architecture review of a Bitcoin intelligence dashboard.
  15 | 
  16 | This is a PRE-BUILD AUDIT. Your job is forensic - find weaknesses before they become bugs.
  17 | 
  18 | Be direct. Be specific. Prioritize ruthlessly. Rate each concern: CRITICAL / HIGH / MEDIUM / LOW.
  19 | 
  20 | Focus your review on:
  21 | 1. The Sentinel Algorithm - is the multi-factor weighting formula mathematically sound? Edge cases? Gaming risks?
  22 | 2. Behavioral analytics - are the archetype classifications and churn model defensible?
  23 | 3. WebSocket architecture - scalability on Replit? Failure modes?
  24 | 4. Stripe integration gaps - what critical webhook scenarios are missing?
  25 | 5. Database schema - missing indexes, N+1 query risks, data integrity issues?
  26 | 6. Missing data sources - what real-time Bitcoin signals are we not collecting?
  27 | 7. Priority verdict - what is the single highest-leverage thing to ship first?
  28 | 
  29 | Return ONLY valid JSON, no markdown fences:
  30 | {
  31 |   "verdict": "one sentence overall verdict",
  32 |   "critical_issues": [{"issue": "...", "impact": "...", "fix": "..."}],
  33 |   "high_issues": [{"issue": "...", "impact": "...", "fix": "..."}],
  34 |   "medium_issues": [{"issue": "...", "impact": "...", "fix": "..."}],
  35 |   "algorithm_verdict": "detailed assessment of the Sentinel formula",
  36 |   "missing_data_sources": ["list of important missing signals"],
  37 |   "ship_first": "what to build first and why",
  38 |   "moat_assessment": "is this genuinely defensible IP or easily replicated?",
  39 |   "score": 0
  40 | }
  41 | 
  42 | THE SPEC:
  43 | """ + spec[:12000]
  44 | 
  45 | results = {}
  46 | errors = {}
  47 | 
  48 | def call_gemini():
  49 |     try:
  50 |         import google.generativeai as genai
  51 |         genai.configure(api_key=os.environ["GEMINI_API_KEY"])
  52 |         model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
  53 |         resp = model.generate_content(AUDIT_PROMPT)
  54 |         text = resp.text.strip()
  55 |         if "```" in text:
  56 |             lines = text.split("\n")
  57 |             text = "\n".join(l for l in lines if not l.strip().startswith("```"))
  58 |         results["gemini"] = json.loads(text)
  59 |         print("[GEMINI] Done - score:", results["gemini"].get("score"))
  60 |     except Exception as e:
  61 |         errors["gemini"] = str(e)
  62 |         print(f"[GEMINI] ERROR: {e}")
  63 | 
  64 | def call_gpt4o():
  65 |     try:
  66 |         from openai import OpenAI
  67 |         client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
  68 |         resp = client.chat.completions.create(
  69 |             model="gpt-5.4",
  70 |             messages=[{"role": "user", "content": AUDIT_PROMPT}],
  71 |             response_format={"type": "json_object"},
  72 |             max_completion_tokens=3000,
  73 |         )
  74 |         results["gpt4o"] = json.loads(resp.choices[0].message.content)
  75 |         print("[GPT-4o] Done - score:", results["gpt4o"].get("score"))
  76 |     except Exception as e:
  77 |         errors["gpt4o"] = str(e)
  78 |         print(f"[GPT-4o] ERROR: {e}")
  79 | 
  80 | def call_grok():
  81 |     try:
  82 |         from openai import OpenAI
  83 |         client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
  84 |         resp = client.chat.completions.create(
  85 |             model="grok-3-latest",
  86 |             messages=[{"role": "user", "content": AUDIT_PROMPT}],
  87 |             response_format={"type": "json_object"},
  88 |             max_completion_tokens=3000,
  89 |         )
  90 |         results["grok"] = json.loads(resp.choices[0].message.content)
  91 |         print("[GROK]  Done - score:", results["grok"].get("score"))
  92 |     except Exception as e:
  93 |         errors["grok"] = str(e)
  94 |         print(f"[GROK]  ERROR: {e}")
  95 | 
  96 | print(f"[AUDIT] Firing at {datetime.now().strftime('%H:%M:%S')} - all 3 LLMs in parallel...")
  97 | threads = [
  98 |     threading.Thread(target=call_gemini),
  99 |     threading.Thread(target=call_gpt4o),
 100 |     threading.Thread(target=call_grok),
 101 | ]
 102 | for t in threads: t.start()
 103 | for t in threads: t.join()
 104 | 
 105 | print(f"[AUDIT] Completed: {list(results.keys())} | Errors: {list(errors.keys())}")
 106 | 
 107 | # Synthesize with Claude
 108 | if results:
 109 |     import anthropic
 110 |     client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
 111 |     
 112 |     parts = []
 113 |     for name, data in results.items():
 114 |         parts.append(f"## {name.upper()}\n{json.dumps(data, indent=2)[:3000]}")
 115 |     
 116 |     synthesis_prompt = """Synthesize this multi-LLM architecture audit into a final report.
 117 | 
 118 | Three LLMs independently reviewed the Protocol Pulse Intel Dashboard spec:
 119 | 
 120 | """ + "\n\n".join(parts) + """
 121 | 
 122 | Errors: """ + json.dumps(errors) + """
 123 | 
 124 | Write a final audit report with these sections:
 125 | 1. CONSENSUS ISSUES - things 2+ LLMs flagged (these are highest priority)
 126 | 2. UNIQUE INSIGHTS - important points only one LLM caught  
 127 | 3. DISAGREEMENTS - where they diverged and who is right
 128 | 4. SENTINEL ALGORITHM VERDICT - final consensus on the weighting formula
 129 | 5. FINAL BUILD ORDER - ordered list, most important first
 130 | 6. GREEN LIGHT STATUS - is this ready to build, or what must change first?
 131 | 
 132 | Be decisive. This is the final gate before execution."""
 133 | 
 134 |     msg = client.messages.create(
 135 |         model="claude-sonnet-4-6",
 136 |         max_tokens=4000,
 137 |         messages=[{"role": "user", "content": synthesis_prompt}]
 138 |     )
 139 |     synthesis = msg.content[0].text
 140 |     print("[CLAUDE] Synthesis complete")
 141 | else:
 142 |     synthesis = "CRITICAL: No LLM responses. Check API keys.\nErrors: " + json.dumps(errors)
 143 | 
 144 | # Write reports
 145 | out_dir = Path.home() / "protocol_pulse/docs/intel"
 146 | out_dir.mkdir(parents=True, exist_ok=True)
 147 | 
 148 | json_path = out_dir / "MULTI_LLM_AUDIT_RESULTS.json"
 149 | json_path.write_text(json.dumps({
 150 |     "generated_at": datetime.now().isoformat(),
 151 |     "results": results,
 152 |     "errors": errors,
 153 |     "synthesis": synthesis,
 154 | }, indent=2))
 155 | 
 156 | scores = {k: v.get("score","?") for k,v in results.items() if isinstance(v,dict)}
 157 | score_lines = "\n".join(f"- {k.upper()}: {v}/100" for k,v in scores.items())
 158 | llm_status = "\n".join(f"- {k}: {chr(10003) if k in results else chr(10007) + ' ' + errors.get(k,'?')}" for k in ["gemini","gpt4o","grok"])
 159 | 
 160 | md_content = f"""# Intel Dashboard — Multi-LLM Audit Results
 161 | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
 162 | 
 163 | ## LLMs Queried
 164 | {llm_status}
 165 | 
 166 | ## Scores
 167 | {score_lines}
 168 | 
 169 | ## Synthesis
 170 | 
 171 | {synthesis}
 172 | """
 173 | md_path = out_dir / "MULTI_LLM_AUDIT_RESULTS.md"
 174 | md_path.write_text(md_content)
 175 | 
 176 | print(f"[AUDIT] Reports written to {out_dir}")
 177 | print("=" * 60)
 178 | print("SYNTHESIS PREVIEW:")
 179 | print(synthesis[:1200])
 180 | print("=" * 60)
 181 | print("AUDIT_COMPLETE")
 182 | 
```

### File: launch_all_features.sh (121 lines)
```
   1 | #!/bin/bash
   2 | # PROTOCOL PULSE — PARALLEL FEATURE BUILD + AUDIT LAUNCHER
   3 | # Flow: Build code -> 2-cycle LLM audit -> second pass -> PR-ready
   4 | # Usage: bash launch_all_features.sh [f1-avatar-oracle f5-node-watch ...] or no args = all
   5 | 
   6 | set -e
   7 | BASE_DIR=~/protocol_pulse
   8 | GOSPELS_DIR=$BASE_DIR/docs/gospels
   9 | WORKTREES_DIR=~/worktrees
  10 | LOG_DIR=$BASE_DIR/logs/feature_builds
  11 | AUDIT_ENGINE=$BASE_DIR/utils/cross_llm_audit.py
  12 | 
  13 | mkdir -p $WORKTREES_DIR $LOG_DIR $BASE_DIR/docs/audits
  14 | 
  15 | FEATURES=(
  16 |   "f1-avatar-oracle|feature/f1-avatar-oracle|F1_AVATAR_ORACLE_GOSPEL.md|y"
  17 |   "f2-briefing-room|feature/f2-briefing-room|F2_BRIEFING_ROOM_GOSPEL.md|y"
  18 |   "f3-schiff-bot|feature/f3-schiff-bot|F3_SCHIFF_BOT_GOSPEL.md|n"
  19 |   "f4-nostr|feature/f4-nostr|F4_NOSTR_GOSPEL.md|n"
  20 |   "f5-node-watch|feature/f5-node-watch|F5_NODE_WATCH_GOSPEL.md|n"
  21 |   "f6-marketing-os|feature/f6-marketing-os|F6_MARKETING_OS_GOSPEL.md|n"
  22 |   "v30-terminal-api|feature/v30-terminal-api|V30_TERMINAL_API_GOSPEL.md|y"
  23 |   "b1-newsletter|feature/b1-newsletter|B1_NEWSLETTER_GOSPEL.md|n"
  24 |   "v22-multi-format|feature/v22-multi-format|V22_MULTI_FORMAT_GOSPEL.md|y"
  25 | )
  26 | 
  27 | launch_feature() {
  28 |   local NAME=$1 BRANCH=$2 GOSPEL=$3 HIGH_STAKES=$4
  29 |   local WORKTREE=$WORKTREES_DIR/$NAME
  30 |   local LOG=$LOG_DIR/${NAME}.log
  31 | 
  32 |   echo ""; echo "=== LAUNCHING: $NAME ===" ; echo "  branch: $BRANCH  log: $LOG"
  33 | 
  34 |   cd $BASE_DIR
  35 |   if [ ! -d "$WORKTREE" ]; then
  36 |     git worktree add $WORKTREE -b $BRANCH 2>/dev/null || git worktree add $WORKTREE $BRANCH
  37 |   fi
  38 | 
  39 |   cp $GOSPELS_DIR/$GOSPEL $WORKTREE/GOSPEL.md
  40 |   cp $GOSPELS_DIR/POST_BUILD_AUDIT_PROTOCOL.md $WORKTREE/AUDIT_PROTOCOL.md 2>/dev/null || true
  41 | 
  42 |   # Write the prompt to a file
  43 |   cat > /tmp/cc_prompt_${NAME}.txt << PROMPT_EOF
  44 | Read $WORKTREE/GOSPEL.md IN FULL before writing a single line of code.
  45 | This is your complete specification. Every law in it is inviolable.
  46 | 
  47 | You are building feature: $NAME
  48 | Branch: $BRANCH | Worktree: $WORKTREE | Base repo: $BASE_DIR
  49 | 
  50 | PHASE 1 - BUILD:
  51 | Execute the BUILD section of GOSPEL.md step by step.
  52 | Build complete frontend AND backend. World-class quality, not a prototype.
  53 | Every route: try/except. Every API call: timeout + fallback. Every DB write: rollback.
  54 | Every async frontend op: loading/error/empty states all handled.
  55 | Every ORDER BY / WHERE column: indexed.
  56 | CSS animations only - no Three.js, no WebGL.
  57 | 
  58 | When complete:
  59 | 1. cd $BASE_DIR && bash regression_test.sh -- fix until zero FAILs
  60 | 2. git add -A && git commit -m "feat($NAME): initial build"
  61 | 3. git push origin $BRANCH
  62 | 
  63 | PHASE 2 - LLM AUDIT (fires automatically after build):
  64 | python3 $BASE_DIR/utils/cross_llm_audit.py --feature $NAME
  65 | This fires 2-cycle audit with Gemini+OpenAI+Grok, writes FINAL_CONSENSUS.md.
  66 | Wait for it to complete -- it will print AUDIT COMPLETE when done.
  67 | 
  68 | PHASE 3 - SECOND PASS:
  69 | Read $BASE_DIR/docs/audits/$NAME/FINAL_CONSENSUS.md
  70 | Implement every P0 and P1 item from the FINAL ACTION PLAN.
  71 | Do NOT change anything in VALIDATED STRENGTHS.
  72 | regression_test.sh -- zero FAILs required.
  73 | git add -A && git commit -m "feat($NAME): post-audit second pass"
  74 | git push origin $BRANCH
  75 | 
  76 | Print final summary: files created, test results, audit scores, PR ready: YES/NO
  77 | PROMPT_EOF
  78 | 
  79 |   tmux kill-session -t "build_${NAME}" 2>/dev/null || true
  80 |   tmux new-session -d -s "build_${NAME}" \
  81 |     "cd $WORKTREE && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions < /tmp/cc_prompt_${NAME}.txt 2>&1 | tee $LOG; echo SESSION_COMPLETE_${NAME} >> $LOG"
  82 | 
  83 |   echo "  session launched: build_${NAME}"
  84 | }
  85 | 
  86 | if [ $# -gt 0 ]; then TARGETS=("$@")
  87 | else
  88 |   TARGETS=()
  89 |   for f in "${FEATURES[@]}"; do TARGETS+=("$(echo $f | cut -d'|' -f1)"); done
  90 | fi
  91 | 
  92 | echo ""; echo "PROTOCOL PULSE PARALLEL BUILD LAUNCHER"
  93 | echo "Launching ${#TARGETS[@]} sessions: Build + 2-cycle audit + second pass"
  94 | echo ""
  95 | 
  96 | cd $BASE_DIR && git pull origin main --quiet 2>/dev/null || true
  97 | 
  98 | LAUNCHED=0
  99 | for feature_def in "${FEATURES[@]}"; do
 100 |   NAME=$(echo $feature_def | cut -d'|' -f1)
 101 |   BRANCH=$(echo $feature_def | cut -d'|' -f2)
 102 |   GOSPEL=$(echo $feature_def | cut -d'|' -f3)
 103 |   HIGH=$(echo $feature_def | cut -d'|' -f4)
 104 |   for target in "${TARGETS[@]}"; do
 105 |     if [ "$target" == "$NAME" ]; then
 106 |       launch_feature $NAME $BRANCH $GOSPEL $HIGH
 107 |       LAUNCHED=$((LAUNCHED + 1))
 108 |       sleep 8
 109 |       break
 110 |     fi
 111 |   done
 112 | done
 113 | 
 114 | echo ""; echo "$LAUNCHED SESSIONS LAUNCHED"
 115 | echo ""
 116 | echo "Monitor: tmux ls | grep build_"
 117 | echo "Attach:  tmux attach -t build_f1-avatar-oracle  (Ctrl+B D to detach)"
 118 | echo "Logs:    tail -f $LOG_DIR/*.log"
 119 | echo "Audits:  ls $BASE_DIR/docs/audits/*/FINAL_CONSENSUS.md"
 120 | echo "Branches: cd $BASE_DIR && git branch -a | grep feature/"
 121 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?
