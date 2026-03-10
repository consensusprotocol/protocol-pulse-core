# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: f1-avatar-oracle
# Branch: feature/f1-avatar-oracle
# Generated: 2026-03-09 02:39 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The Oracle page is Protocol Pulse's most powerful differentiator — a live AI
avatar that delivers Bitcoin intelligence on demand. Right now it's broken,
inconsistent, and visually unfinished. This gospel defines the complete,
production-grade implementation.

Two parallel deliverables:
1. **Oracle Avatar Identity** — a distinct visual persona (anime-realism female,
   cyberpunk Bloomberg aesthetic) with locked assets, voice, and personality
2. **Oracle Sanctuary UI** — a fully rebuilt oracle.html that matches the
   VISUAL_DESIGN_SYSTEM.md standard (gold info bar, red/cyan/gold radial glow,
   animated SVG elements, skewed sweep transitions)

---

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS (inviolable — never override without PBX approval)

### LAW 1: Wav2Lip is the ONLY approved lip-sync engine
- batch_size=48, FP16, GPU-cached at startup
- 134fps on 4090 = 3.8s generation for 10s audio
- DO NOT install MuseTalk, SadTalker, or any other lip-sync library
- DO NOT call HeyGen for the Oracle avatar (HeyGen is for Market Briefing Room only)

### LAW 2: apply_blink() is permanently disabled
- The blink engine creates black oval artifacts
- Body of apply_blink() must be: `return frame`
- Do not attempt to fix the blink engine — disable it, ship without blinking

### LAW 3: Voice = Jessica only
- ElevenLabs voice ID: cgSgspJ2msm6clMCkdW9
- Model: eleven_turbo_v2_5
- Settings: stability=0.45, similarity_boost=0.75, style=0.20
- Do not change the voice without PBX explicit approval

### LAW 4: No Three.js, no VR, no DAO, no WebGL shaders
- Oracle Sanctuary uses CSS/SVG animations only
- Background: CSS radial gradients + animated SVG data streams
- Glow effects: CSS box-shadow and filter:blur only

### LAW 5: avatar_server.py is the authoritative file
- Path: ~/protocol_pulse/oracle/avatar_server.py (currently 977 lines)
- Port: 8200, served via avatar.protocolpulse.io
- GPU cache warms at startup — never cold-start Wav2Lip per request
- ModelRegistry pattern must be preserved

### LAW 6: Proto-P avatar asset
- Source image: oracle/assets/Proto_P_Avatar_512.png
- This is the current avatar face used for lip sync
- New anime-realism female avatar replaces this ONLY when new asset is approved
- Until PBX provides new asset, use Proto_P_Avatar_512.png

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

### File: logs/monetization_engine.report.json (22 lines)
```
   1 | {
   2 |   "finished_at": "2026-03-04T04:08:49.865496",
   3 |   "briefs": {
   4 |     "scanned": 0,
   5 |     "injected": 0
   6 |   },
   7 |   "x_drafts": {
   8 |     "scanned": 0,
   9 |     "injected": 0
  10 |   },
  11 |   "totals": {
  12 |     "scanned": 0,
  13 |     "injected": 0
  14 |   },
  15 |   "metrics": {
  16 |     "scanned": 0,
  17 |     "injected": 0,
  18 |     "injection_rate_pct": 0.0,
  19 |     "clicks_7d": 0,
  20 |     "click_rate_vs_injected_pct": 0.0
  21 |   }
  22 | }
```

### File: logs/runtime_status.json (33 lines)
```
   1 | {
   2 |   "sentry": {
   3 |     "last_run": "2026-03-04T04:18:26.041111",
   4 |     "fetched": 0,
   5 |     "drafted": 0,
   6 |     "handles": [],
   7 |     "dry_run": false
   8 |   },
   9 |   "updated_at": "2026-03-04T04:18:28.007006",
  10 |   "nostr_sentry": {
  11 |     "last_run": "2026-03-04T04:18:26.043229",
  12 |     "fetched": 0,
  13 |     "drafted": 0,
  14 |     "handles": [],
  15 |     "dry_run": false
  16 |   },
  17 |   "whale": {
  18 |     "last_run": "2026-03-04T04:18:26.044475",
  19 |     "scanned": 0,
  20 |     "inserted": 0,
  21 |     "mega_inserted": 0,
  22 |     "avg_fee_btc": 0.0,
  23 |     "mega_events": []
  24 |   },
  25 |   "ghostwriter": {
  26 |     "last_run": "2026-03-04T04:18:28.006879",
  27 |     "scanned": 0,
  28 |     "drafted": 0
  29 |   },
  30 |   "heartbeat": {
  31 |     "last_heartbeat": "2026-03-04T04:18:26.040353"
  32 |   }
  33 | }
```

### File: media_reforge/static/js/media_unified.js (1230 lines)
```
   1 | /* ═══════════════════════════════════════════════════════
   2 |    PROTOCOL PULSE — MEDIA UNIFIED ENGINE v3.0
   3 |    Phase 3: The Network — Merged Intelligence Terminal
   4 |    ═══════════════════════════════════════════════════════ */
   5 | 'use strict';
   6 | 
   7 | (function() {
   8 | 
   9 | // ─── CONFIG ───────────────────────────────────────────
  10 | var NOSTR_RELAYS = [
  11 |   'wss://relay.damus.io',
  12 |   'wss://nos.lol',
  13 |   'wss://relay.nostr.band'
  14 | ];
  15 | 
  16 | var NOSTR_META_RELAY = 'wss://purplepag.es';
  17 | 
  18 | var POLL_INTERVALS = {
  19 |   telemetry:  30000,
  20 |   fng:       300000,
  21 |   signal:     15000,
  22 |   feed:       60000,
  23 |   sentiment: 300000
  24 | };
  25 | 
  26 | var SPACES_ACCOUNTS = [
  27 |   { handle: 'sabordebitcoin',  name: 'Sabor de Bitcoin'  },
  28 |   { handle: 'BitcoinMagazine', name: 'Bitcoin Magazine'  },
  29 |   { handle: 'thebitcoinlayer', name: 'The Bitcoin Layer' },
  30 |   { handle: 'WhatBitcoinDid',  name: 'What Bitcoin Did'  }
  31 | ];
  32 | 
  33 | var PLATFORM_CONFIG = {
  34 |   x:       { label: 'X',            color: '#1DA1F2' },
  35 |   twitter: { label: 'X',            color: '#1DA1F2' },
  36 |   reddit:  { label: 'REDDIT',       color: '#FF4500' },
  37 |   rss:     { label: 'RSS',          color: '#6B7280' },
  38 |   news:    { label: 'NEWS',         color: '#6B7280' },
  39 |   stacker: { label: 'STACKER NEWS', color: '#F7931A' },
  40 |   nostr:   { label: 'NOSTR',        color: '#7c3aed' }
  41 | };
  42 | 
  43 | // Series data (all episodes for expandable panels)
  44 | var SD = {
  45 |   everything_21m: {
  46 |     title: 'Everything Divided by 21 Million',
  47 |     host: 'Matty Ice & Knut Svanholm',
  48 |     episodes: [
  49 |       {id:'FA8tvWEydcA',title:'Time | Episode 1'},
  50 |       {id:'VDordtHAJhg',title:'Alchemy | Episode 2'},
  51 |       {id:'yKbQq66AInU',title:'Ownership | Episode 3'},
  52 |       {id:'rkTbEpAOADI',title:'Energy | Episode 4'},
  53 |       {id:'qG2xYvTVkw0',title:'Morality | Episode 5'},
  54 |       {id:'v7xZPqcXyLk',title:'Memetics | Episode 6'},
  55 |       {id:'RZv_1Qcqik4',title:'Symbiosis | Episode 7'},
  56 |       {id:'UlYSv9SwQGk',title:'Violence | Episode 8'},
  57 |       {id:'_ygND311kVE',title:'Deflation | Episode 9'},
  58 |       {id:'Nf0LtAk4VBs',title:'Adoption | Episode 10'},
  59 |       {id:'Gt8ycm3-NV8',title:'Transition | Episode 11'}
  60 |     ]
  61 |   },
  62 |   big_print: {
  63 |     title: 'The Big Print',
  64 |     host: 'Matty Ice & Lawrence Lepard',
  65 |     episodes: [
  66 |       {id:'W09CNU_q6Yo',title:'Why Fixing the Money is the Only Way | Episode 1'},
  67 |       {id:'tnthM3uaHbI',title:'How Govt Stole 98.5% Since 1971 | Episode 2'},
  68 |       {id:'FRH5w_joMP0',title:'How Inflation Steals Your Life | Episode 3'},
  69 |       {id:'JLjG8jAJxbw',title:'The Path to Pure Fiat | Episode 4'},
  70 |       {id:'tq_ZYhpW4Vw',title:'How Powell & Yellen Broke It | Episode 5'},
  71 |       {id:'Sjp-Kaic2CE',title:'Austrian vs Keynesian | Episode 6'},
  72 |       {id:'n6Bi8Kf6ar0',title:'The Sovereign Currency Bubble | Episode 7'},
  73 |       {id:'M3M61rLBTl0',title:'Bitcoin is God\'s Gift | Episode 8'},
  74 |       {id:'uzUEJZ38RV8',title:'Bitcoin & Real Estate | Episode 9'},
  75 |       {id:'y9snxWoEkaU',title:'End of Centralized Power | Episode 10'},
  76 |       {id:'hKa8lRDwIos',title:'Digital Scarcity | Episode 11'},
  77 |       {id:'FyMWELymqAM',title:'Fix the Money, Fix the World | Episode 12'}
  78 |     ]
  79 |   },
  80 |   daylight_robbery: {
  81 |     title: 'Daylight Robbery',
  82 |     host: 'Matty Ice & Dominic Frisby',
  83 |     episodes: [
  84 |       {id:'ZCc78wvwd6U',title:'The Hidden History of Taxation | Episode 1'},
  85 |       {id:'j_V3fjvEuS0',title:'How Taxes Shaped Civilization | Episode 2'},
  86 |       {id:'W_TNwftaVMk',title:'Death, Taxes, or Islam | Episode 3'},
  87 |       {id:'3VDVbbSZYPc',title:'The Peasants\' Revolt | Episode 4'},
  88 |       {id:'brho571r5rY',title:'Tax Wars That Created Nations | Episode 5'},
  89 |       {id:'zltb_tXZiWI',title:'How the Richest Controlled Nations | Episode 6'},
  90 |       {id:'0MDv0d-3t_k',title:'How Tariffs Caused Civil War | Episode 7'},
  91 |       {id:'Ym5W3t9WvB8',title:'The Birth of Big Government | Episode 8'},
  92 |       {id:'YUHM88mtRxU',title:'Hitler, Banks & Nations | Episode 9'},
  93 |       {id:'LcIT9Tgbkm8',title:'How Govts Silently Rob You | Episode 10'},
  94 |       {id:'VRSXUD4L2eA',title:'Digital Nomads & Borderless Money | Episode 11'},
  95 |       {id:'1OAn6QDSsJs',title:'How Data & AI Reshape Taxation | Episode 12'},
  96 |       {id:'xPPbMsz8qso',title:'The Perfect Tax System | Episode 13'}
  97 |     ]
  98 |   },
  99 |   genesis_book: {
 100 |     title: 'The Genesis Book',
 101 |     host: 'Matty Ice & Aaron van Wirdum',
 102 |     episodes: [
 103 |       {id:'y7KBeC4jfbo',title:'Origins of Digital Cash | Episode 1'},
 104 |       {id:'LNEsJjYZ57o',title:'The Cypherpunks | Episode 2'},
 105 |       {id:'KcTVg0b7kDw',title:'Hash Cash & Digital Gold | Episode 3'},
 106 |       {id:'TwkR0ncLh0Y',title:'Satoshi\'s Vision | Episode 4'},
 107 |       {id:'mAe_F5G6gUE',title:'The Genesis Block | Episode 5'}
 108 |     ]
 109 |   }
 110 | };
 111 | 
 112 | // ─── STATE ────────────────────────────────────────────
 113 | var state = {
 114 |   nostrNotes: [],
 115 |   chainData: null,
 116 |   fngData: null,
 117 |   signalScore: 0,
 118 |   sparkData: { btc: [], fees: [], mempool: [], hashrate: [] },
 119 |   currentSeries: null,
 120 |   audioPlaying: false
 121 | };
 122 | 
 123 | // ─── UTILITIES ────────────────────────────────────────
 124 | function $(sel) { return document.querySelector(sel); }
 125 | function $$(sel) { return document.querySelectorAll(sel); }
 126 | 
 127 | function escapeHtml(str) {
 128 |   if (!str) return '';
 129 |   var d = document.createElement('div');
 130 |   d.textContent = str;
 131 |   return d.innerHTML;
 132 | }
 133 | 
 134 | function linkify(text) {
 135 |   return text.replace(/(https?:\/\/[^\s<]+)/g,
 136 |     '<a href="$1" target="_blank" rel="noopener">$1</a>');
 137 | }
 138 | 
 139 | function formatTimeAgo(ts) {
 140 |   var diff = Date.now() - ts;
 141 |   var secs = Math.floor(diff / 1000);
 142 |   if (secs < 60)   return secs + 's';
 143 |   var mins = Math.floor(secs / 60);
 144 |   if (mins < 60)   return mins + 'm';
 145 |   var hrs = Math.floor(mins / 60);
 146 |   if (hrs < 24)    return hrs + 'h';
 147 |   return Math.floor(hrs / 24) + 'd';
 148 | }
 149 | 
 150 | function formatNumber(n) {
 151 |   if (n == null) return '--';
 152 |   return n.toLocaleString();
 153 | }
 154 | 
 155 | // ─── SPLIT-FLAP ANIMATION ─────────────────────────────
 156 | function splitFlap(el, newVal) {
 157 |   if (!el) return;
 158 |   if (el.textContent === String(newVal)) return;
 159 |   el.classList.add('mu-flap-out');
 160 |   setTimeout(function() {
 161 |     el.textContent = newVal;
 162 |     el.classList.remove('mu-flap-out');
 163 |     el.classList.add('mu-flap-in');
 164 |     setTimeout(function() { el.classList.remove('mu-flap-in'); }, 150);
 165 |   }, 150);
 166 | }
 167 | 
 168 | // ─── SPARKLINE RENDERER ───────────────────────────────
 169 | function SparklineRenderer(canvasId, color) {
 170 |   this.canvas = document.getElementById(canvasId);
 171 |   this.color = color || 'rgba(255,255,255,0.5)';
 172 |   if (this.canvas) {
 173 |     this.ctx = this.canvas.getContext('2d');
 174 |     this.w = this.canvas.width;
 175 |     this.h = this.canvas.height;
 176 |   }
 177 | }
 178 | 
 179 | SparklineRenderer.prototype.draw = function(data) {
 180 |   if (!this.ctx || !data || data.length < 2) return;
 181 |   var pts = data.slice(-24);
 182 |   var min = Math.min.apply(null, pts);
 183 |   var max = Math.max.apply(null, pts);
 184 |   var range = max - min || 1;
 185 | 
 186 |   this.ctx.clearRect(0, 0, this.w, this.h);
 187 |   this.ctx.beginPath();
 188 |   this.ctx.strokeStyle = this.color;
 189 |   this.ctx.lineWidth = 1;
 190 |   this.ctx.lineJoin = 'round';
 191 | 
 192 |   for (var i = 0; i < pts.length; i++) {
 193 |     var x = (i / (pts.length - 1)) * this.w;
 194 |     var y = this.h - ((pts[i] - min) / range) * (this.h - 2) - 1;
 195 |     if (i === 0) this.ctx.moveTo(x, y);
 196 |     else         this.ctx.lineTo(x, y);
 197 |   }
 198 |   this.ctx.stroke();
 199 | };
 200 | 
 201 | // ─── TELEMETRY ENGINE ─────────────────────────────────
 202 | function TelemetryEngine() {
 203 |   var RED = 'rgba(204,0,0,0.8)';
 204 |   this.sparks = {
 205 |     btc:      new SparklineRenderer('spark-btc', RED),
 206 |     fees:     new SparklineRenderer('spark-fees', RED),
 207 |     mempool:  new SparklineRenderer('spark-mempool', RED),
 208 |     hashrate: new SparklineRenderer('spark-hashrate', RED)
 209 |   };
 210 | }
 211 | 
 212 | TelemetryEngine.prototype.start = function() {
 213 |   this.fetchAll();
 214 |   this.fetchFNG();
 215 |   var self = this;
 216 |   setInterval(function() { self.fetchAll(); }, POLL_INTERVALS.telemetry);
 217 |   setInterval(function() { self.fetchFNG(); }, POLL_INTERVALS.fng);
 218 | };
 219 | 
 220 | TelemetryEngine.prototype.fetchAll = function() {
 221 |   var self = this;
 222 |   Promise.allSettled([
 223 |     fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true'),
 224 |     fetch('https://mempool.space/api/v1/fees/recommended'),
 225 |     fetch('https://mempool.space/api/mempool'),
 226 |     fetch('https://mempool.space/api/blocks/tip/height'),
 227 |     fetch('https://mempool.space/api/v1/mining/hashrate/3m')
 228 |   ]).then(function(results) {
 229 |     var priceRes = results[0], feesRes = results[1], mempoolRes = results[2], blockRes = results[3], hrRes = results[4];
 230 | 
 231 |     if (priceRes.status === 'fulfilled' && priceRes.value.ok) {
 232 |       priceRes.value.json().then(function(pd) {
 233 |         var btcUsd = pd && pd.bitcoin && pd.bitcoin.usd;
 234 |         var chg = pd && pd.bitcoin && pd.bitcoin.usd_24h_change;
 235 |         if (btcUsd != null) {
 236 |           splitFlap($('#telem-btc-price'), '$' + Math.round(btcUsd).toLocaleString());
 237 |           state.sparkData.btc.push(btcUsd);
 238 |           if (state.sparkData.btc.length > 24) state.sparkData.btc.shift();
 239 |           self.sparks.btc.draw(state.sparkData.btc);
 240 |         }
 241 |         if (chg != null) {
 242 |           var chgEl = $('#telem-btc-change');
 243 |           if (chgEl) {
 244 |             chgEl.textContent = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';
 245 |             chgEl.className = 'mu-telem-change ' + (chg > 0.05 ? 'up' : chg < -0.05 ? 'down' : 'flat');
 246 |           }
 247 |         }
 248 |       });
 249 |     }
 250 | 
 251 |     if (feesRes.status === 'fulfilled' && feesRes.value.ok) {
 252 |       feesRes.value.json().then(function(fd) {
 253 |         var feeVal = fd.fastestFee || fd.halfHourFee || fd.economyFee || '--';
 254 |         splitFlap($('#telem-fees'), feeVal);
 255 |         state.sparkData.fees.push(parseFloat(feeVal) || 0);
 256 |         if (state.sparkData.fees.length > 24) state.sparkData.fees.shift();
 257 |         self.sparks.fees.draw(state.sparkData.fees);
 258 |       });
 259 |     }
 260 | 
 261 |     if (mempoolRes.status === 'fulfilled' && mempoolRes.value.ok) {
 262 |       mempoolRes.value.json().then(function(md) {
 263 |         state.chainData = { mempool: md };
 264 |         var mbVal = md.vsize ? (md.vsize / 1e6).toFixed(1) : '--';
 265 |         splitFlap($('#telem-mempool'), mbVal);
 266 |         state.sparkData.mempool.push(parseFloat(mbVal) || 0);
 267 |         if (state.sparkData.mempool.length > 24) state.sparkData.mempool.shift();
 268 |         self.sparks.mempool.draw(state.sparkData.mempool);
 269 |         self.updateThermalBorder(md);
 270 |       });
 271 |     }
 272 | 
 273 |     if (blockRes.status === 'fulfilled' && blockRes.value.ok) {
 274 |       blockRes.value.text().then(function(blk) {
 275 |         var blkNum = parseInt(blk.trim());
 276 |         if (!isNaN(blkNum)) splitFlap($('#telem-block'), formatNumber(blkNum));
 277 |       });
 278 |     }
 279 | 
 280 |     if (hrRes.status === 'fulfilled' && hrRes.value.ok) {
 281 |       hrRes.value.json().then(function(hrd) {
 282 |         var hrRaw = hrd.currentHashrate || (hrd.hashrates && hrd.hashrates.length && hrd.hashrates[hrd.hashrates.length - 1].avgHashrate);
 283 |         if (hrRaw != null) {
 284 |           var ehs = (hrRaw / 1e18).toFixed(0);
 285 |           splitFlap($('#telem-hashrate'), ehs);
 286 |           state.sparkData.hashrate.push(parseFloat(ehs) || 0);
 287 |           if (state.sparkData.hashrate.length > 24) state.sparkData.hashrate.shift();
 288 |           self.sparks.hashrate.draw(state.sparkData.hashrate);
 289 |         }
 290 |       });
 291 |     }
 292 | 
 293 |     setHealth('health-telemetry', 'connected');
 294 |   }).catch(function() {
 295 |     setHealth('health-telemetry', 'error');
 296 |   });
 297 | };
 298 | 
 299 | TelemetryEngine.prototype.fetchFNG = function() {
 300 |   fetch('https://api.alternative.me/fng/?limit=1').then(function(res) {
 301 |     if (!res.ok) return;
 302 |     return res.json();
 303 |   }).then(function(d) {
 304 |     if (!d) return;
 305 |     state.fngData = d;
 306 |     var entry = (d.data && d.data[0]) || d;
 307 |     var val = parseInt(entry.value || 50);
 308 | 
 309 |     var dot = $('#sentiment-dot');
 310 |     var num = $('#sentiment-num');
 311 |     if (dot) dot.style.left = val + '%';
 312 |     if (num) splitFlap(num, val);
 313 | 
 314 |     setHealth('health-sentiment', 'connected');
 315 |   }).catch(function() {
 316 |     setHealth('health-sentiment', 'error');
 317 |   });
 318 | };
 319 | 
 320 | TelemetryEngine.prototype.updateThermalBorder = function(mempoolData) {
 321 |   var border = $('#thermal-border');
 322 |   if (!border) return;
 323 |   border.classList.remove('congested', 'clearing');
 324 |   var count = (mempoolData && mempoolData.count) || 0;
 325 |   if (count > 50000)      border.classList.add('congested');
 326 |   else if (count < 10000) border.classList.add('clearing');
 327 | };
 328 | 
 329 | // ─── AVATAR UTILITIES ─────────────────────────────────
 330 | function getAvatarColor(seed) {
 331 |   var hash = 0;
 332 |   var s = seed || '?';
 333 |   for (var i = 0; i < s.length; i++) {
 334 |     hash = s.charCodeAt(i) + ((hash << 5) - hash);
 335 |   }
 336 |   var palette = ['#7c3aed','#2563eb','#059669','#d97706','#0891b2','#be185d','#0369a1','#7e22ce'];
 337 |   return palette[Math.abs(hash) % palette.length];
 338 | }
 339 | 
 340 | function renderAvatar(name, imgUrl, size) {
 341 |   var sz = size || 32;
 342 |   var letter = (name || '?')[0].toUpperCase();
 343 |   var color = getAvatarColor(name || '?');
 344 |   var imgHtml = imgUrl
 345 |     ? '<img src="' + escapeHtml(imgUrl) + '" loading="lazy" width="' + sz + '" height="' + sz + '" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
 346 |     : '';
 347 |   var fallbackStyle = imgUrl ? ' style="display:none"' : '';
 348 |   return '<div class="mu-avatar" style="--avatar-color:' + color + ';width:' + sz + 'px;height:' + sz + 'px">' + imgHtml + '<span class="mu-avatar-fallback"' + fallbackStyle + '>' + letter + '</span></div>';
 349 | }
 350 | 
 351 | // ─── NOSTR FEED ───────────────────────────────────────
 352 | function NostrFeed() {
 353 |   this.sockets = {};
 354 |   this.seen = new Set();
 355 |   this.reconnectDelay = {};
 356 |   this.allowlist = [];
 357 |   this.pubkeyMap = {};
 358 |   this.metaCache = new Map();
 359 |   this.metaWs = null;
 360 |   this.metaFetched = new Set();
 361 | }
 362 | 
 363 | NostrFeed.prototype.init = function() {
 364 |   var self = this;
 365 |   fetch('/api/media/sources').then(function(res) {
 366 |     if (res.ok) return res.json();
 367 |   }).then(function(data) {
 368 |     if (data) {
 369 |       self.allowlist = data.nostr_allowlist || [];
 370 |       self.allowlist.forEach(function(p) {
 371 |         if (p.pubkey) self.pubkeyMap[p.pubkey] = p.name;
 372 |       });
 373 |     }
 374 |   }).catch(function() {}).finally(function() {
 375 |     self.connectAll();
 376 |     self.connectMetaRelay();
 377 |     setHealth('health-nostr', 'loading');
 378 |   });
 379 | };
 380 | 
 381 | NostrFeed.prototype.connectAll = function() {
 382 |   var self = this;
 383 |   NOSTR_RELAYS.forEach(function(url) { self.connect(url); });
 384 | };
 385 | 
 386 | NostrFeed.prototype.connect = function(url) {
 387 |   var self = this;
 388 |   try {
 389 |     if (this.sockets[url] && this.sockets[url].readyState === WebSocket.OPEN) return;
 390 | 
 391 |     var ws = new WebSocket(url);
 392 |     this.sockets[url] = ws;
 393 |     this.reconnectDelay[url] = this.reconnectDelay[url] || 2000;
 394 | 
 395 |     ws.onopen = function() {
 396 |       self.reconnectDelay[url] = 2000;
 397 |       setHealth('health-nostr', 'connected');
 398 |       setHealth('health-nostr-col', 'connected');
 399 | 
 400 |       var filter = {
 401 |         kinds: [1],
 402 |         limit: 30,
 403 |         since: Math.floor(Date.now() / 1000) - 86400
 404 |       };
 405 | 
 406 |       var authors = self.allowlist.map(function(p) { return p.pubkey; }).filter(Boolean);
 407 |       if (authors.length > 0) filter.authors = authors;
 408 | 
 409 |       ws.send(JSON.stringify(['REQ', 'pp-' + Math.random().toString(36).slice(2, 8), filter]));
 410 |     };
 411 | 
 412 |     ws.onmessage = function(evt) {
 413 |       try {
 414 |         var msg = JSON.parse(evt.data);
 415 |         if (msg[0] === 'EVENT' && msg[2]) self.handleEvent(msg[2]);
 416 |       } catch (e) {}
 417 |     };
 418 | 
 419 |     ws.onclose = function() {
 420 |       var delay = Math.min((self.reconnectDelay[url] || 2000) * 1.5, 30000);
 421 |       self.reconnectDelay[url] = delay;
 422 |       var countEl = $('#nostr-count');
 423 |       if (countEl) countEl.textContent = 'reconnecting...';
 424 |       setTimeout(function() { self.connect(url); }, delay);
 425 |     };
 426 | 
 427 |     ws.onerror = function() {
 428 |       setHealth('health-nostr', 'error');
 429 |       ws.close();
 430 |     };
 431 |   } catch (e) {
 432 |     setHealth('health-nostr', 'error');
 433 |   }
 434 | };
 435 | 
 436 | NostrFeed.prototype.connectMetaRelay = function() {
 437 |   var self = this;
 438 |   try {
 439 |     var ws = new WebSocket(NOSTR_META_RELAY);
 440 |     this.metaWs = ws;
 441 | 
 442 |     ws.onopen = function() {
 443 |       var keys = self.allowlist.map(function(p) { return p.pubkey; }).filter(Boolean);
 444 |       if (keys.length > 0) {
 445 |         ws.send(JSON.stringify(['REQ', 'pp-meta-init', { kinds: [0], authors: keys }]));
 446 |         keys.forEach(function(k) { self.metaFetched.add(k); });
 447 |       }
 448 |     };
 449 | 
 450 |     ws.onmessage = function(evt) {
 451 |       try {
 452 |         var msg = JSON.parse(evt.data);
 453 |         if (msg[0] === 'EVENT' && msg[2] && msg[2].kind === 0) self.handleMeta(msg[2]);
 454 |       } catch (e) {}
 455 |     };
 456 | 
 457 |     ws.onclose = function() { setTimeout(function() { self.connectMetaRelay(); }, 30000); };
 458 |     ws.onerror = function() { ws.close(); };
 459 |   } catch (e) {}
 460 | };
 461 | 
 462 | NostrFeed.prototype.handleMeta = function(evt) {
 463 |   if (!evt.pubkey) return;
 464 |   try {
 465 |     var profile = JSON.parse(evt.content || '{}');
 466 |     var name = profile.display_name || profile.name || '';
 467 |     var picture = profile.picture || '';
 468 |     this.metaCache.set(evt.pubkey, { name: name, picture: picture });
 469 | 
 470 |     // Update rendered notes
 471 |     document.querySelectorAll('.nostr-note[data-pubkey="' + CSS.escape(evt.pubkey) + '"]').forEach(function(el) {
 472 |       if (picture) {
 473 |         var av = el.querySelector('.mu-avatar');
 474 |         var fb = el.querySelector('.mu-avatar-fallback');
 475 |         var existingImg = el.querySelector('.mu-avatar img');
 476 |         if (!existingImg && av) {
 477 |           var newImg = document.createElement('img');
 478 |           newImg.src = picture;
 479 |           newImg.loading = 'lazy';
 480 |           newImg.width = 32;
 481 |           newImg.height = 32;
 482 |           newImg.onerror = function() { this.style.display = 'none'; if (fb) fb.style.display = 'flex'; };
 483 |           av.insertBefore(newImg, av.firstChild);
 484 |           if (fb) fb.style.display = 'none';
 485 |         }
 486 |       }
 487 |       if (name) {
 488 |         var authorEl = el.querySelector('.nostr-note-author');
 489 |         if (authorEl && authorEl.dataset.isDefault === '1') {
 490 |           authorEl.textContent = name;
 491 |         }
 492 |       }
 493 |     });
 494 |   } catch (e) {}
 495 | };
 496 | 
 497 | NostrFeed.prototype.handleEvent = function(evt) {
 498 |   var id = evt.id;
 499 |   if (!id || this.seen.has(id)) return;
 500 |   this.seen.add(id);
 501 | 
 502 |   if (this.seen.size > 500) {
 503 |     var arr = Array.from(this.seen).slice(-300);
 504 |     this.seen = new Set(arr);
 505 |   }
 506 | 
 507 |   var meta = evt.pubkey ? this.metaCache.get(evt.pubkey) : null;
 508 |   var allowlistName = evt.pubkey ? this.pubkeyMap[evt.pubkey] : null;
 509 |   var isDefault = !allowlistName && !(meta && meta.name);
 510 |   var name = allowlistName || (meta && meta.name) || (evt.pubkey ? evt.pubkey.slice(0, 8) + '...' : 'Anon');
 511 |   var picture = (meta && meta.picture) || null;
 512 | 
 513 |   var note = {
 514 |     id: id,
 515 |     name: name,
 516 |     picture: picture,
 517 |     content: evt.content || '',
 518 |     created_at: evt.created_at || Math.floor(Date.now() / 1000),
 519 |     pubkey: evt.pubkey || '',
 520 |     isDefault: isDefault
 521 |   };
 522 | 
 523 |   state.nostrNotes.unshift(note);
 524 |   if (state.nostrNotes.length > 100) state.nostrNotes.pop();
 525 | 
 526 |   this.renderNote(note);
 527 |   updateNostrCount();
 528 | 
 529 |   // Fetch metadata for unknown pubkeys
 530 |   if (evt.pubkey && !this.metaFetched.has(evt.pubkey) && this.metaWs && this.metaWs.readyState === WebSocket.OPEN) {
 531 |     this.metaFetched.add(evt.pubkey);
 532 |     this.metaWs.send(JSON.stringify(['REQ', 'pp-m-' + evt.pubkey.slice(0, 8), { kinds: [0], authors: [evt.pubkey] }]));
 533 |   }
 534 | };
 535 | 
 536 | NostrFeed.prototype.renderNote = function(note) {
 537 |   var feed = $('#nostr-feed');
 538 |   if (!feed) return;
 539 | 
 540 |   feed.querySelectorAll('.mu-skeleton').forEach(function(s) { s.remove(); });
 541 | 
 542 |   var truncated = note.content.length > 280;
 543 |   var display = truncated ? note.content.slice(0, 280) : note.content;
 544 | 
 545 |   var el = document.createElement('div');
 546 |   el.className = 'intel-card nostr-note nostr-new';
 547 |   el.dataset.pubkey = note.pubkey;
 548 | 
 549 |   el.innerHTML =
 550 |     '<div class="intel-card-header">' +
 551 |       renderAvatar(note.name, note.picture, 32) +
 552 |       '<div class="intel-card-meta">' +
 553 |         '<span class="nostr-note-author"' + (note.isDefault ? ' data-is-default="1"' : '') + '>' + escapeHtml(note.name) + '</span>' +
 554 |         '<span class="intel-badge intel-badge-nostr">NOSTR</span>' +
 555 |       '</div>' +
 556 |       '<span class="intel-card-time">' + formatTimeAgo(note.created_at * 1000) + '</span>' +
 557 |     '</div>' +
 558 |     '<div class="intel-card-body">' + linkify(escapeHtml(display)) + (truncated ? '<span class="intel-expand-btn"> more</span>' : '') + '</div>';
 559 | 
 560 |   if (truncated) {
 561 |     var btn = el.querySelector('.intel-expand-btn');
 562 |     if (btn) {
 563 |       btn.addEventListener('click', function() {
 564 |         var body = el.querySelector('.intel-card-body');
 565 |         if (body) {
 566 |           body.innerHTML = linkify(escapeHtml(note.content));
 567 |           body.classList.add('expanded');
 568 |         }
 569 |       });
 570 |     }
 571 |   }
 572 | 
 573 |   // Remove new glow after animation
 574 |   setTimeout(function() { el.classList.remove('nostr-new'); }, 600);
 575 | 
 576 |   feed.prepend(el);
 577 |   while (feed.children.length > 30) feed.removeChild(feed.lastChild);
 578 | };
 579 | 
 580 | // ─── PLATFORM DETECTION ───────────────────────────────
 581 | function detectPlatform(item) {
 582 |   var src = (item.source || '').toLowerCase();
 583 |   var type = (item.source_type || '').toLowerCase();
 584 |   var icon = (item.platform_icon || '').toLowerCase();
 585 | 
 586 |   if (src.indexOf('stacker') >= 0 || src.indexOf('stackernews') >= 0) return PLATFORM_CONFIG.stacker;
 587 |   if (type === 'x' || type === 'twitter' || src.indexOf('twitter') >= 0 || icon.indexOf('twitter') >= 0) return PLATFORM_CONFIG.x;
 588 |   if (type === 'reddit' || src.indexOf('reddit') >= 0) return PLATFORM_CONFIG.reddit;
 589 |   if (type === 'nostr' || src.indexOf('nostr') >= 0) return PLATFORM_CONFIG.nostr;
 590 |   return PLATFORM_CONFIG.rss;
 591 | }
 592 | 
 593 | // ─── COMBINED INTELLIGENCE FEED ───────────────────────
 594 | function CombinedFeed() {
 595 |   this.lastReceived = {};
 596 |   this.items = [];
 597 |   this._firstLoad = true;
 598 |   this.activeFilter = 'all';
 599 | }
 600 | 
 601 | CombinedFeed.prototype.start = function() {
 602 |   this.fetch();
 603 |   var self = this;
 604 |   setInterval(function() { self.fetch(); }, POLL_INTERVALS.feed);
 605 | };
 606 | 
 607 | CombinedFeed.prototype.fetch = function() {
 608 |   var self = this;
 609 |   fetch('/api/media/feed').then(function(res) {
 610 |     if (!res.ok) return null;
 611 |     return res.json();
 612 |   }).then(function(data) {
 613 |     if (!data || !Array.isArray(data)) return;
 614 |     self.items = data;
 615 |     data.forEach(function(item) {
 616 |       var p = detectPlatform(item);
 617 |       var key = p.label.toLowerCase().replace(/\s+/g, '_');
 618 |       self.lastReceived[key] = Date.now();
 619 |     });
 620 |     self.render(data);
 621 |     updateSourceHealth(self.lastReceived);
 622 |   }).catch(function() {});
 623 | };
 624 | 
 625 | CombinedFeed.prototype.render = function(items) {
 626 |   var feed = $('#combined-feed');
 627 |   if (!feed) return;
 628 |   feed.querySelectorAll('.mu-skeleton').forEach(function(s) { s.remove(); });
 629 | 
 630 |   if (!items.length) {
 631 |     feed.innerHTML = '<div class="intel-empty"><i class="fas fa-satellite-dish"></i>Monitoring signal channels...<div class="intel-loader"></div></div>';
 632 |     return;
 633 |   }
 634 | 
 635 |   var sorted = items.slice().sort(function(a, b) {
 636 |     var ta = a.published_at ? new Date(a.published_at).getTime() : 0;
 637 |     var tb = b.published_at ? new Date(b.published_at).getTime() : 0;
 638 |     return tb - ta;
 639 |   });
 640 | 
 641 |   // Apply filter
 642 |   var self = this;
 643 |   var filtered = sorted;
 644 |   if (this.activeFilter !== 'all') {
 645 |     filtered = sorted.filter(function(item) {
 646 |       var p = detectPlatform(item);
 647 |       var label = p.label.toLowerCase();
 648 |       if (self.activeFilter === 'x') return label === 'x';
 649 |       if (self.activeFilter === 'reddit') return label === 'reddit';
 650 |       if (self.activeFilter === 'stacker') return label === 'stacker news';
 651 |       if (self.activeFilter === 'rss') return label === 'rss' || label === 'news';
 652 |       return true;
 653 |     });
 654 |   }
 655 | 
 656 |   var isRefresh = !this._firstLoad;
 657 |   this._firstLoad = false;
 658 | 
 659 |   if (isRefresh) {
 660 |     feed.style.opacity = '0.5';
 661 |     feed.style.transition = 'opacity 200ms ease';
 662 |     setTimeout(function() {
 663 |       feed.innerHTML = filtered.slice(0, 30).map(function(item) { return self.renderCard(item); }).join('');
 664 |       feed.style.opacity = '1';
 665 |       self.bindExpand(feed);
 666 |     }, 200);
 667 |   } else {
 668 |     feed.innerHTML = filtered.slice(0, 30).map(function(item) { return self.renderCard(item); }).join('');
 669 |     this.bindExpand(feed);
 670 |   }
 671 | };
 672 | 
 673 | CombinedFeed.prototype.bindExpand = function(feed) {
 674 |   feed.querySelectorAll('.intel-expand-btn[data-full]').forEach(function(btn) {
 675 |     btn.addEventListener('click', function() {
 676 |       var body = this.closest('.intel-card-body');
 677 |       if (body) {
 678 |         body.innerHTML = linkify(escapeHtml(this.dataset.full || ''));
 679 |         body.classList.add('expanded');
 680 |       }
 681 |     });
 682 |   });
 683 | };
 684 | 
 685 | CombinedFeed.prototype.renderCard = function(item) {
 686 |   var platform = detectPlatform(item);
 687 |   var author = item.author || item.source || 'Unknown';
 688 |   var content = item.summary || item.description || item.title || '';
 689 |   var truncated = content.length > 280;
 690 |   var display = truncated ? content.slice(0, 280) : content;
 691 |   var ts = item.published_at ? new Date(item.published_at).getTime() : Date.now();
 692 |   var avatarColor = getAvatarColor(author);
 693 | 
 694 |   var imgSrc = '';
 695 |   var isX = platform.label === 'X';
 696 |   var cleanHandle = author.replace(/^@/, '');
 697 |   if (isX && cleanHandle && cleanHandle.indexOf(' ') < 0) {
 698 |     imgSrc = 'https://unavatar.io/twitter/' + encodeURIComponent(cleanHandle);
 699 |   }
 700 | 
 701 |   var letter = (author[0] || '?').toUpperCase();
 702 |   var avatarHtml = '<div class="mu-avatar" style="--avatar-color:' + avatarColor + ';width:28px;height:28px">' +
 703 |     (imgSrc ? '<img src="' + escapeHtml(imgSrc) + '" loading="lazy" width="28" height="28" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' : '') +
 704 |     '<span class="mu-avatar-fallback"' + (imgSrc ? ' style="display:none"' : '') + '>' + letter + '</span></div>';
 705 | 
 706 |   var badgeHtml = '<span class="intel-badge" style="background:' + platform.color + '1a;color:' + platform.color + ';border-color:' + platform.color + '40">' + platform.label + '</span>';
 707 | 
 708 |   var expandHtml = truncated
 709 |     ? '<span class="intel-expand-btn" data-full="' + escapeHtml(content) + '"> more</span>'
 710 |     : '';
 711 | 
 712 |   return '<div class="feed-card" style="--platform-color:' + platform.color + '">' +
 713 |     '<div class="intel-card-left-border"></div>' +
 714 |     '<div class="intel-card-content">' +
 715 |       '<div class="intel-card-header">' +
 716 |         avatarHtml +
 717 |         '<div class="intel-card-meta">' +
 718 |           '<span class="intel-card-author">' + escapeHtml(author) + '</span>' +
 719 |           badgeHtml +
 720 |         '</div>' +
 721 |         '<span class="intel-card-time">' + formatTimeAgo(ts) + '</span>' +
 722 |       '</div>' +
 723 |       '<div class="intel-card-body">' + linkify(escapeHtml(display)) + expandHtml + '</div>' +
 724 |       '<div class="intel-card-source">via ' + escapeHtml(item.source || '') + '</div>' +
 725 |     '</div>' +
 726 |   '</div>';
 727 | };
 728 | 
 729 | // ─── VOICE INTEL ──────────────────────────────────────
 730 | function VoiceIntel() {
 731 |   this.gaugeScore = null;
 732 | }
 733 | 
 734 | VoiceIntel.prototype.start = function() {
 735 |   this.fetchSentiment();
 736 |   this.renderSpacesRadar();
 737 |   this.renderSourceHealth();
 738 |   var self = this;
 739 |   setInterval(function() { self.fetchSentiment(); }, POLL_INTERVALS.sentiment);
 740 | };
 741 | 
 742 | VoiceIntel.prototype.fetchSentiment = function() {
 743 |   var self = this;
 744 |   fetch('/api/media/sentiment').then(function(res) {
 745 |     if (!res.ok) return null;
 746 |     return res.json();
 747 |   }).then(function(data) {
 748 |     if (!data) return;
 749 |     var fngScore = state.fngData && state.fngData.data && state.fngData.data[0]
 750 |       ? parseInt(state.fngData.data[0].value) : null;
 751 |     var score = fngScore !== null ? fngScore : (data.score || 50);
 752 | 
 753 |     self.gaugeScore = score;
 754 |     self.drawGauge(score);
 755 |     self.renderKeywords(data.keywords || []);
 756 |     setHealth('health-sentiment', 'connected');
 757 |   }).catch(function() {});
 758 | };
 759 | 
 760 | VoiceIntel.prototype.drawGauge = function(score) {
 761 |   var canvas = document.getElementById('sentiment-gauge');
 762 |   if (!canvas) return;
 763 |   var ctx = canvas.getContext('2d');
 764 |   var w = canvas.width, h = canvas.height;
 765 |   var cx = w / 2, cy = h - 6;
 766 |   var r = Math.min(cx - 4, cy) * 0.9;
 767 | 
 768 |   ctx.clearRect(0, 0, w, h);
 769 | 
 770 |   ctx.beginPath();
 771 |   ctx.arc(cx, cy, r, Math.PI, 0, false);
 772 |   ctx.strokeStyle = 'rgba(255,255,255,0.07)';
 773 |   ctx.lineWidth = 10;
 774 |   ctx.lineCap = 'butt';
 775 |   ctx.stroke();
 776 | 
 777 |   var color;
 778 |   if      (score <= 20) color = '#dc2626';
 779 |   else if (score <= 40) color = '#f97316';
 780 |   else if (score <= 60) color = '#e2e2e2';
 781 |   else if (score <= 80) color = '#86efac';
 782 |   else                  color = '#22c55e';
 783 | 
 784 |   var endAngle = Math.PI + (score / 100) * Math.PI;
 785 |   ctx.beginPath();
 786 |   ctx.arc(cx, cy, r, Math.PI, endAngle, false);
 787 |   ctx.strokeStyle = color;
 788 |   ctx.lineWidth = 10;
 789 |   ctx.lineCap = 'round';
 790 |   ctx.stroke();
 791 | 
 792 |   var valEl = document.getElementById('gauge-val');
 793 |   if (valEl) { valEl.textContent = Math.round(score); valEl.style.color = color; }
 794 | 
 795 |   var labelEl = document.getElementById('gauge-label');
 796 |   if (labelEl) {
 797 |     var label;
 798 |     if      (score <= 20) label = 'EXTREME FEAR';
 799 |     else if (score <= 40) label = 'FEAR';
 800 |     else if (score <= 60) label = 'NEUTRAL';
 801 |     else if (score <= 80) label = 'GREED';
 802 |     else                  label = 'EXTREME GREED';
 803 |     labelEl.textContent = label;
 804 |     labelEl.style.color = color;
 805 |   }
 806 | };
 807 | 
 808 | VoiceIntel.prototype.renderKeywords = function(keywords) {
 809 |   var el = document.getElementById('intel-keywords');
 810 |   if (!el) return;
 811 |   el.querySelectorAll('.mu-skeleton').forEach(function(s) { s.remove(); });
 812 | 
 813 |   if (!keywords.length) {
 814 |     el.innerHTML = '<span class="intel-empty-sm">No keywords available</span>';
 815 |     return;
 816 |   }
 817 | 
 818 |   var maxWeight = Math.max.apply(null, keywords.map(function(k) { return k.weight || 1; }));
 819 |   el.innerHTML = keywords.slice(0, 14).map(function(kw) {
 820 |     var w = kw.weight || 1;
 821 |     var ratio = w / maxWeight;
 822 |     var fontSize = 9 + Math.round(ratio * 5);
 823 |     var opacity = 0.5 + ratio * 0.5;
 824 |     var word = kw.keyword || '';
 825 |     var isBear = /FUD|BEAR|DUMP|CRASH|FEAR/i.test(word);
 826 |     var color = isBear ? '#f97316' : 'rgba(204,0,0,0.85)';
 827 |     return '<span class="intel-keyword" style="font-size:' + fontSize + 'px;opacity:' + opacity + ';border-color:' + color + '25;color:' + color + '">' + escapeHtml(word) + '</span>';
 828 |   }).join('');
 829 | };
 830 | 
 831 | VoiceIntel.prototype.renderSpacesRadar = function() {
 832 |   var el = document.getElementById('intel-spaces');
 833 |   if (!el) return;
 834 | 
 835 |   el.innerHTML = SPACES_ACCOUNTS.map(function(acc) {
 836 |     var imgUrl = 'https://unavatar.io/twitter/' + encodeURIComponent(acc.handle);
 837 |     var profileUrl = 'https://x.com/' + encodeURIComponent(acc.handle);
 838 |     var avatarColor = getAvatarColor(acc.handle);
 839 |     return '<a class="intel-spaces-row" href="' + escapeHtml(profileUrl) + '" target="_blank" rel="noopener">' +
 840 |       '<div class="mu-avatar" style="--avatar-color:' + avatarColor + ';width:28px;height:28px">' +
 841 |         '<img src="' + escapeHtml(imgUrl) + '" loading="lazy" width="28" height="28" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' +
 842 |         '<span class="mu-avatar-fallback" style="display:none">' + acc.name[0].toUpperCase() + '</span>' +
 843 |       '</div>' +
 844 |       '<div class="intel-spaces-info">' +
 845 |         '<span class="intel-spaces-name">@' + escapeHtml(acc.handle) + '</span>' +
 846 |         '<span class="intel-spaces-sub">' + escapeHtml(acc.name) + '</span>' +
 847 |       '</div>' +
 848 |       '<span class="intel-spaces-link">&rarr;</span>' +
 849 |     '</a>';
 850 |   }).join('');
 851 | };
 852 | 
 853 | VoiceIntel.prototype.renderSourceHealth = function() {
 854 |   var el = document.getElementById('intel-health');
 855 |   if (!el) return;
 856 | 
 857 |   var sources = [
 858 |     { key: 'nostr',  label: 'Nostr'       },
 859 |     { key: 'x',      label: 'X / Twitter'  },
 860 |     { key: 'reddit', label: 'Reddit'       },
 861 |     { key: 'rss',    label: 'RSS / News'   }
 862 |   ];
 863 | 
 864 |   el.innerHTML = sources.map(function(s) {
 865 |     return '<div class="intel-health-row">' +
 866 |       '<div class="mu-health-dot loading" id="sh-dot-' + s.key + '"></div>' +
 867 |       '<span class="intel-health-label">' + s.label + '</span>' +
 868 |       '<span class="intel-health-time" id="sh-time-' + s.key + '">--</span>' +
 869 |     '</div>';
 870 |   }).join('');
 871 | };
 872 | 
 873 | // ─── SOURCE HEALTH UPDATER ────────────────────────────
 874 | function updateSourceHealth(lastReceived) {
 875 |   var now = Date.now();
 876 |   var fiveMin = 5 * 60 * 1000;
 877 | 
 878 |   var labelToKey = {
 879 |     'X': 'x', 'REDDIT': 'reddit', 'RSS': 'rss', 'NEWS': 'rss',
 880 |     'STACKER NEWS': 'rss', 'NOSTR': 'nostr'
 881 |   };
 882 | 
 883 |   var slotBest = {};
 884 |   Object.keys(lastReceived).forEach(function(platformLabel) {
 885 |     var ts = lastReceived[platformLabel];
 886 |     var key = labelToKey[platformLabel.toUpperCase()] || 'rss';
 887 |     if (!slotBest[key] || ts > slotBest[key]) slotBest[key] = ts;
 888 |   });
 889 | 
 890 |   ['nostr', 'x', 'reddit', 'rss'].forEach(function(key) {
 891 |     var dotEl = document.getElementById('sh-dot-' + key);
 892 |     var timeEl = document.getElementById('sh-time-' + key);
 893 |     var ts = slotBest[key];
 894 | 
 895 |     if (!dotEl) return;
 896 |     if (ts && now - ts < fiveMin) {
 897 |       dotEl.classList.remove('loading', 'error');
 898 |       dotEl.classList.add('connected');
 899 |       if (timeEl) timeEl.textContent = formatTimeAgo(ts) + ' ago';
 900 |     } else if (ts) {
 901 |       dotEl.classList.remove('loading', 'connected');
 902 |       dotEl.classList.add('error');
 903 |       if (timeEl) timeEl.textContent = formatTimeAgo(ts) + ' ago';
 904 |     }
 905 |   });
 906 | }
 907 | 
 908 | function markNostrSourceHealthActive() {
 909 |   var dotEl = document.getElementById('sh-dot-nostr');
 910 |   var timeEl = document.getElementById('sh-time-nostr');
 911 |   if (dotEl) { dotEl.classList.remove('loading', 'error'); dotEl.classList.add('connected'); }
 912 |   if (timeEl) timeEl.textContent = 'live';
 913 | }
 914 | 
 915 | // ─── SIGNAL STRENGTH ──────────────────────────────────
 916 | function updateSignalStrength() {
 917 |   var oneHourAgo = Date.now() / 1000 - 3600;
 918 |   var recentNotes = state.nostrNotes.filter(function(n) { return n.created_at > oneHourAgo; }).length;
 919 |   var nostrScore = Math.min(recentNotes / 30 * 100, 100);
 920 | 
 921 |   var chainScore = 50;
 922 |   if (state.chainData && state.chainData.mempool) {
 923 |     var count = state.chainData.mempool.count || 0;
 924 |     chainScore = Math.min(count / 100000 * 100, 100);
 925 |   }
 926 | 
 927 |   var sentimentScore = (state.fngData && state.fngData.data && state.fngData.data[0])
 928 |     ? parseInt(state.fngData.data[0].value) : 50;
 929 | 
 930 |   state.signalScore = Math.round(nostrScore * 0.35 + chainScore * 0.30 + sentimentScore * 0.35);
 931 | 
 932 |   var fill = $('#signal-fill');
 933 |   var label = $('#telem-signal');
 934 |   if (fill) {
 935 |     fill.style.width = state.signalScore + '%';
 936 |     if      (state.signalScore > 70) fill.style.background = '#22c55e';
 937 |     else if (state.signalScore > 40) fill.style.background = '#f7931a';
 938 |     else                             fill.style.background = '#cc0000';
 939 |   }
 940 |   if (label) splitFlap(label, state.signalScore);
 941 | }
 942 | 
 943 | function updateNostrCount() {
 944 |   var el = $('#nostr-count');
 945 |   if (el) {
 946 |     el.textContent = state.nostrNotes.length + ' notes';
 947 |     markNostrSourceHealthActive();
 948 |   }
 949 |   // Update hero live notes count
 950 |   var liveN = $('#liveN');
 951 |   if (liveN) liveN.textContent = state.nostrNotes.length;
 952 | }
 953 | 
 954 | // ─── HEALTH HELPER ────────────────────────────────────
 955 | function setHealth(id, status) {
 956 |   var dot = document.getElementById(id);
 957 |   if (!dot) return;
 958 |   dot.classList.remove('loading', 'connected', 'error');
 959 |   dot.classList.add(status);
 960 | }
 961 | 
 962 | // ═══════════════════════════════════════════════════════
 963 | // OLD /media FUNCTIONS — Series Panel, Podcast, Books
 964 | // ═══════════════════════════════════════════════════════
 965 | 
 966 | // ─── SERIES EPISODE PANEL ─────────────────────────────
 967 | window.toggleSD = function(k) {
 968 |   var p = document.getElementById('sdPanel');
 969 |   if (state.currentSeries === k && p.classList.contains('active')) {
 970 |     window.closeSD();
 971 |     return;
 972 |   }
 973 |   var s = SD[k];
 974 |   if (!s || !s.episodes || !s.episodes.length) return;
 975 |   state.currentSeries = k;
 976 |   document.getElementById('sdTitle').textContent = s.title || k;
 977 |   var e0 = s.episodes[0];
 978 |   document.getElementById('sdIf').src = 'https://www.youtube.com/embed/' + e0.id + '?autoplay=1';
 979 |   var sb = document.getElementById('sdEps');
 980 |   sb.innerHTML = s.episodes.map(function(ep, i) {
 981 |     return '<div class="sd-ep' + (i === 0 ? ' active' : '') + '" onclick="playSE(\'' + ep.id + '\',' + i + ',this)">' +
 982 |       '<img class="sd-ep-img" src="https://img.youtube.com/vi/' + ep.id + '/mqdefault.jpg" loading="lazy">' +
 983 |       '<div class="sd-ep-info"><div class="sd-ep-n">EP ' + (i + 1) + '</div><div class="sd-ep-t">' + ep.title + '</div></div></div>';
 984 |   }).join('');
 985 |   p.classList.add('active');
 986 |   setTimeout(function() { p.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 100);
 987 | };
 988 | 
 989 | window.playSE = function(id, i, el) {
 990 |   document.getElementById('sdIf').src = 'https://www.youtube.com/embed/' + id + '?autoplay=1';
 991 |   document.querySelectorAll('.sd-ep').forEach(function(e) { e.classList.remove('active'); });
 992 |   if (el) el.classList.add('active');
 993 | };
 994 | 
 995 | window.closeSD = function() {
 996 |   document.getElementById('sdIf').src = '';
 997 |   document.getElementById('sdPanel').classList.remove('active');
 998 |   state.currentSeries = null;
 999 | };
1000 | 
1001 | // ─── PODCAST AUDIO PLAYER ─────────────────────────────
1002 | var au = null;
1003 | 
1004 | window.playEp = function(u, t) {
1005 |   if (!u) return;
1006 |   if (!au) au = document.getElementById('aEl');
1007 |   if (!au) return;
1008 |   au.src = u;
1009 |   au.play().catch(function() {});
1010 |   state.audioPlaying = true;
1011 |   document.getElementById('aNow').textContent = t;
1012 |   document.getElementById('aIcon').className = 'fas fa-pause';
1013 |   document.getElementById('abar').classList.add('active');
1014 | };
1015 | 
1016 | window.togA = function() {
1017 |   if (!au) au = document.getElementById('aEl');
1018 |   if (!au) return;
1019 |   if (state.audioPlaying) {
1020 |     au.pause();
1021 |     document.getElementById('aIcon').className = 'fas fa-play';
1022 |   } else {
1023 |     au.play().catch(function() {});
1024 |     document.getElementById('aIcon').className = 'fas fa-pause';
1025 |   }
1026 |   state.audioPlaying = !state.audioPlaying;
1027 | };
1028 | 
1029 | window.stopA = function() {
1030 |   if (!au) au = document.getElementById('aEl');
1031 |   if (!au) return;
1032 |   au.pause();
1033 |   au.src = '';
1034 |   state.audioPlaying = false;
1035 |   document.getElementById('abar').classList.remove('active');
1036 | };
1037 | 
1038 | // ─── BOOKS SHOW MORE TOGGLE ──────────────────────────
1039 | window.togB = function() {
1040 |   document.getElementById('bmore').classList.toggle('show');
1041 |   document.getElementById('btog').classList.toggle('open');
1042 | };
1043 | 
1044 | // ─── COMMAND PALETTE ──────────────────────────────────
1045 | function CommandPalette() {
1046 |   this.overlay = $('#cmd-overlay');
1047 |   this.input = $('#cmd-input');
1048 |   this.results = $('#cmd-results');
1049 |   this.selectedIdx = -1;
1050 |   this.commands = [
1051 |     { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Intelligence Feed', action: function() { var el = $('#mu-signals'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
1052 |     { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Series',            action: function() { var el = $('#mu-series'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
1053 |     { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Podcasts',          action: function() { var el = $('#mu-podcasts'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
1054 |     { group: 'NAVIGATE', icon: '\u25cb', label: 'Go to Library',           action: function() { var el = $('#mu-library'); if (el) el.scrollIntoView({ behavior: 'smooth' }); } },
1055 |     { group: 'ACTIONS',  icon: '\u25cb', label: 'Fullscreen',              action: function() { if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen(); } },
1056 |     { group: 'ACTIONS',  icon: '\u25cb', label: 'Open mempool.space',      action: function() { window.open('https://mempool.space', '_blank'); } },
1057 |     { group: 'ACTIONS',  icon: '\u25cb', label: 'Copy share link',         action: function() { if (navigator.clipboard) navigator.clipboard.writeText(location.href); } }
1058 |   ];
1059 |   this._bind();
1060 | }
1061 | 
1062 | CommandPalette.prototype._bind = function() {
1063 |   var self = this;
1064 |   document.addEventListener('keydown', function(e) {
1065 |     if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); self.toggle(); }
1066 |     if (e.key === 'Escape' && self.overlay && self.overlay.classList.contains('active')) { e.preventDefault(); self.close(); }
1067 |   });
1068 | 
1069 |   if (this.input) {
1070 |     this.input.addEventListener('input', function() { self._render(); });
1071 |     this.input.addEventListener('keydown', function(e) {
1072 |       if (e.key === 'ArrowDown') { self.selectedIdx++; self._render(); e.preventDefault(); }
1073 |       if (e.key === 'ArrowUp')   { self.selectedIdx--; self._render(); e.preventDefault(); }
1074 |       if (e.key === 'Enter')     { self._execute(); e.preventDefault(); }
1075 |     });
1076 |   }
1077 | 
1078 |   if (this.overlay) {
1079 |     this.overlay.addEventListener('click', function(e) { if (e.target === self.overlay) self.close(); });
1080 |   }
1081 | };
1082 | 
1083 | CommandPalette.prototype.toggle = function() {
1084 |   if (this.overlay && this.overlay.classList.contains('active')) this.close();
1085 |   else this.open();
1086 | };
1087 | 
1088 | CommandPalette.prototype.open = function() {
1089 |   if (this.overlay) this.overlay.classList.add('active');
1090 |   if (this.input) { this.input.focus(); this.input.value = ''; }
1091 |   this.selectedIdx = -1;
1092 |   this._render();
1093 | };
1094 | 
1095 | CommandPalette.prototype.close = function() {
1096 |   if (this.overlay) this.overlay.classList.remove('active');
1097 | };
1098 | 
1099 | CommandPalette.prototype._render = function() {
1100 |   if (!this.results) return;
1101 |   var q = (this.input && this.input.value || '').toLowerCase();
1102 |   var filtered = q ? this.commands.filter(function(c) { return c.label.toLowerCase().indexOf(q) >= 0; }) : this.commands;
1103 |   this.selectedIdx = Math.max(-1, Math.min(this.selectedIdx, filtered.length - 1));
1104 | 
1105 |   var html = '';
1106 |   var lastGroup = '';
1107 |   var self = this;
1108 |   filtered.forEach(function(cmd, i) {
1109 |     if (cmd.group !== lastGroup) {
1110 |       html += '<div class="mu-cmd-group-label">' + cmd.group + '</div>';
1111 |       lastGroup = cmd.group;
1112 |     }
1113 |     html += '<div class="mu-cmd-item' + (i === self.selectedIdx ? ' selected' : '') + '" data-idx="' + i + '">' +
1114 |       '<span class="icon">' + cmd.icon + '</span>' +
1115 |       '<span class="label">' + cmd.label + '</span>' +
1116 |     '</div>';
1117 |   });
1118 |   this.results.innerHTML = html;
1119 | 
1120 |   this.results.querySelectorAll('.mu-cmd-item').forEach(function(el) {
1121 |     el.addEventListener('click', function() {
1122 |       var idx = parseInt(el.dataset.idx);
1123 |       var q2 = (self.input && self.input.value || '').toLowerCase();
1124 |       var f2 = q2 ? self.commands.filter(function(c) { return c.label.toLowerCase().indexOf(q2) >= 0; }) : self.commands;
1125 |       if (f2[idx]) { f2[idx].action(); self.close(); }
1126 |     });
1127 |   });
1128 | };
1129 | 
1130 | CommandPalette.prototype._execute = function() {
1131 |   var q = (this.input && this.input.value || '').toLowerCase();
1132 |   var filtered = q ? this.commands.filter(function(c) { return c.label.toLowerCase().indexOf(q) >= 0; }) : this.commands;
1133 |   var cmd = filtered[Math.max(0, this.selectedIdx)];
1134 |   if (cmd) { cmd.action(); this.close(); }
1135 | };
1136 | 
1137 | // ─── FEED FILTER CHIPS ────────────────────────────────
1138 | function initFeedFilters(combinedFeed) {
1139 |   var chips = $$('.intel-chip[data-filter]');
1140 |   chips.forEach(function(chip) {
1141 |     chip.addEventListener('click', function() {
1142 |       chips.forEach(function(c) { c.classList.remove('active'); });
1143 |       chip.classList.add('active');
1144 |       combinedFeed.activeFilter = chip.dataset.filter;
1145 |       if (combinedFeed.items.length > 0) {
1146 |         combinedFeed._firstLoad = true;
1147 |         combinedFeed.render(combinedFeed.items);
1148 |       }
1149 |     });
1150 |   });
1151 | }
1152 | 
1153 | // ─── SCROLL REVEAL (IntersectionObserver) ─────────────
1154 | function initScrollReveal() {
1155 |   if (!('IntersectionObserver' in window)) {
1156 |     $$('.mu-reveal').forEach(function(el) { el.classList.add('visible'); });
1157 |     return;
1158 |   }
1159 | 
1160 |   var observer = new IntersectionObserver(function(entries) {
1161 |     entries.forEach(function(entry) {
1162 |       if (entry.isIntersecting) {
1163 |         entry.target.classList.add('visible');
1164 |         observer.unobserve(entry.target);
1165 |       }
1166 |     });
1167 |   }, { threshold: 0.05, rootMargin: '0px 0px -40px 0px' });
1168 | 
1169 |   $$('.mu-reveal').forEach(function(el) { observer.observe(el); });
1170 | }
1171 | 
1172 | // ─── TIMESTAMP UPDATER ────────────────────────────────
1173 | function initTimeUpdater() {
1174 |   setInterval(function() {
1175 |     $$('.intel-card-time').forEach(function(el) {
1176 |       var ts = parseInt(el.dataset.ts);
1177 |       if (ts) el.textContent = formatTimeAgo(ts);
1178 |     });
1179 |   }, 30000);
1180 | }
1181 | 
1182 | // ─── KEYBOARD: Escape closes series panel ─────────────
1183 | document.addEventListener('keydown', function(e) {
1184 |   if (e.key === 'Escape') {
1185 |     var sdPanel = document.getElementById('sdPanel');
1186 |     if (sdPanel && sdPanel.classList.contains('active')) window.closeSD();
1187 |   }
1188 | });
1189 | 
1190 | // ─── INIT ─────────────────────────────────────────────
1191 | document.addEventListener('DOMContentLoaded', function() {
1192 |   // Core engines
1193 |   var nostrFeed    = new NostrFeed();
1194 |   var telemetry    = new TelemetryEngine();
1195 |   var combinedFeed = new CombinedFeed();
1196 |   var voiceIntel   = new VoiceIntel();
1197 |   var cmdPalette   = new CommandPalette();
1198 | 
1199 |   // Start data flows
1200 |   nostrFeed.init();
1201 |   telemetry.start();
1202 |   combinedFeed.start();
1203 |   voiceIntel.start();
1204 | 
1205 |   // Signal strength
1206 |   setInterval(updateSignalStrength, POLL_INTERVALS.signal);
1207 |   setTimeout(updateSignalStrength, 5000);
1208 | 
1209 |   // UI modules
1210 |   initFeedFilters(combinedFeed);
1211 |   initScrollReveal();
1212 |   initTimeUpdater();
1213 | 
1214 |   // Cmd+K hint
1215 |   var cmdHint = $('#cmd-k-hint');
1216 |   if (cmdHint) cmdHint.addEventListener('click', function() { cmdPalette.open(); });
1217 | 
1218 |   // Loading skeletons safety net
1219 |   ['#nostr-feed', '#combined-feed'].forEach(function(sel) {
1220 |     var el = $(sel);
1221 |     if (el && !el.children.length) {
1222 |       el.innerHTML = '<div class="mu-skeleton mu-skel-block"></div><div class="mu-skeleton mu-skel-block"></div><div class="mu-skeleton mu-skel-block"></div>';
1223 |     }
1224 |   });
1225 | 
1226 |   console.log('[Media Unified v3.0] Phase 3: The Network online. Relays:', NOSTR_RELAYS.length);
1227 | });
1228 | 
1229 | })();
1230 | 
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
