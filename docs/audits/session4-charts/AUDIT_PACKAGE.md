# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: session4-charts
# Branch: feature/session4-charts
# Generated: 2026-03-10 04:07 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


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

### File: PIPELINE_LAWS.md (154 lines)
```
   1 | # PROTOCOL PULSE — PIPELINE LAWS
   2 | ## Status: ACTIVE (being refined via 10-cycle gauntlet)
   3 | 
   4 | ---
   5 | 
   6 | ## PIXEL ZONES (confirmed spec)
   7 | - Background: full 1920×1080, color #0A0A0F (never pure black #000000)
   8 | - Text zone (narration): x=40-960, y=80-760 (left half only)
   9 | - PiP zone: x=960-1880, y=0-540 (top right)
  10 | - Subtitle band: y=778-885, full width (1920px), dark glass rgba(0,0,0,0.75), 4px red left bar
  11 | - Info rail (gold): bottom, y≈1032-1080, full width, #F8C15C text
  12 | - Title card: full canvas, no thumbnail bleed
  13 | 
  14 | ## COLOR PALETTE (locked)
  15 | - Background: #0A0A0F (VDS dark navy)
  16 | - Accent / border: #FF3333 (red, 2px borders)
  17 | - Gold info text: #F8C15C
  18 | - Primary text: #FFFFFF
  19 | - Subtitle band bg: rgba(0,0,0,0.75) + blur
  20 | 
  21 | ## AUDIO TARGETS (locked)
  22 | - Integrated LUFS: -14 ±2
  23 | - True peak: ≤ -1.5dBTP
  24 | - LRA: 7 LU
  25 | - Single loudnorm: only in concatenate_parts() — no per-segment loudnorm
  26 | - Sample rate: 48000 Hz
  27 | - Bitrate: 192k (audio)
  28 | 
  29 | ## TTS (locked)
  30 | - Voice: Mark (ID: 1SM7GgM6IMuvQlz2BwM3) at 1.10x speed
  31 | - Both host=1 and host=2 → Mark (single narrator)
  32 | - Speed param: top-level body param, NOT inside voice_settings
  33 | - Fallback chain: ElevenLabs → pyttsx3 → gTTS → silence
  34 | - TTS cache: tts_cache/ SHA256(voice_id:segment_type:text)[:16].m4a
  35 | 
  36 | ## FFMPEG TIMEOUTS (locked)
  37 | - Default run_ffmpeg_filtergraph() timeout: 300s (was 120s)
  38 | - Heavy filtergraphs (make_intro_coldopen, PiP): 300s minimum
  39 | - concatenate_parts(): 600s
  40 | 
  41 | ## TIMING SPEC
  42 | - Title card: 2.0s exactly
  43 | - Cold open: 10-14s
  44 | - Narration segments: 15-35s each
  45 | - Clip segments: natural duration
  46 | - Tweet cards: 8-12s
  47 | - Outro: 10-15s
  48 | - Total: 8-15 minutes
  49 | 
  50 | ## PRODUCTION RULES
  51 | - debug_mode = False in all production renders
  52 | - No debug overlays ("ORACLE NARRATION ACTIVE" etc.) — instant F grade if visible
  53 | - Cold open: NO logos, bars, watermarks — pure dramatic clip
  54 | - Clip segments: full-screen 1920×1080, NO narration overlays bleeding through
  55 | - Continuous BGM: music mixed ONCE in concatenate_parts(), not per-segment
  56 | - AV sync: nuclear PTS in fix_av_sync() + concatenate_parts()
  57 | 
  58 | ## PRESERVED ELEMENTS (never touch)
  59 | - Gold bottom bar text color #F8C15C
  60 | - Red border thickness 2px where intentionally present
  61 | - Watermark: "PROTOCOL PULSE" white, lower-right, opacity 0.5
  62 | - PiP position: top-right, no text overlap
  63 | 
  64 | ---
  65 | 
  66 | ## CYCLE LEARNINGS
  67 | 
  68 | ### PRE-GAUNTLET (cycles 1-3 on feature/video-audio-fix)
  69 | - Fixed: ElevenLabs fallback chain (gTTS added), AV sync, gold rail in make_host_visual, subtitle band in make_host_visual, per-segment loudnorm removed, bg color 0x0A0A0F, ffmpeg timeout raised to 300s
  70 | - Locked: Single loudnorm in concatenate_parts()
  71 | - Open: Subtitle band inconsistency (~50% of frames missing it), LUFS low (-17.7) due to cached silence audio
  72 | 
  73 | 
  74 | 
  75 | ---
  76 | 
  77 | ## QC PIPELINE LAW — PERMANENT — NEVER SKIP
  78 | 
  79 | ### THE TWO-STAGE QC GATE:
  80 | 
  81 | STAGE 1 — GEMINI (automated, runs after every render):
  82 | - Gemini video analysis runs automatically as Step 8 of daily_run.py
  83 | - Output: GEMINI_QC_REPORT.json + GEMINI_QC_REPORT.md with scores per dimension
  84 | - The gauntlet MUST read EVERY score and EVERY finding from this report
  85 | - EVERY dimension scoring below 8/10 maps to a specific code fix — no exceptions
  86 | - EVERY bug listed maps to a specific code fix with file + line — no exceptions
  87 | - Nothing is summarized, nothing is skipped, nothing is cherry-picked
  88 | - Re-render after fixes → Gemini runs again → repeat until ALL dimensions ≥ 8/10 and grade = A
  89 | - ONLY when Gemini grades A does the video get served to PBX
  90 | 
  91 | STAGE 2 — GROK (manual, PBX-run, after Gemini A-grade confirmed):
  92 | - PBX takes the silver platter URL and runs it through Grok browser video analysis tool
  93 | - Grok produces a breakdown of any remaining issues
  94 | - Every Grok finding maps to a code fix in the NEXT render cycle
  95 | - Grok findings are treated with the same weight as Gemini findings — nothing ignored
  96 | 
  97 | ### THE SILVER PLATTER RULE:
  98 | Video is NEVER shown to PBX until Gemini grades it A.
  99 | When Gemini grades A: post the URL as: 
 100 |   🎬 SILVER PLATTER: https://video.protocolpulse.io/[filename]
 101 |   Gemini grade: A | Scores: [all dimensions] | Ready for Grok review.
 102 | 
 103 | ### WHAT COUNTS AS GRADE A (ALL must be true):
 104 | - pip ≥ 8/10
 105 | - cold_open ≥ 8/10  
 106 | - background ≥ 8/10
 107 | - voices = 10/10 (already achieved — never regress)
 108 | - audio_quality ≥ 9/10 (already achieved — never regress)
 109 | - debug_text = 10/10 (already achieved — never regress)
 110 | - Zero black frames detected by ffprobe blackdetect
 111 | - Zero silence segments detected by ffprobe silencedetect
 112 | - LUFS between -15 and -13 (target -14)
 113 | 
 114 | 
 115 | 
 116 | ---
 117 | 
 118 | ## QC PIPELINE LAW — PERMANENT — NEVER SKIP
 119 | 
 120 | ### THE TWO-STAGE QC GATE:
 121 | 
 122 | STAGE 1 — GEMINI (automated, runs after every render):
 123 | - Gemini video analysis runs automatically as Step 8 of daily_run.py
 124 | - Output: GEMINI_QC_REPORT.json + GEMINI_QC_REPORT.md with scores per dimension
 125 | - The gauntlet MUST read EVERY score and EVERY finding from this report
 126 | - EVERY dimension scoring below 8/10 maps to a specific code fix — no exceptions
 127 | - EVERY bug listed maps to a specific code fix with file + line — no exceptions
 128 | - Nothing is summarized, nothing is skipped, nothing is cherry-picked
 129 | - Re-render after fixes → Gemini runs again → repeat until ALL dimensions ≥ 8/10 and grade = A
 130 | - ONLY when Gemini grades A does the video get served to PBX
 131 | 
 132 | STAGE 2 — GROK (manual, PBX-run, after Gemini A-grade confirmed):
 133 | - PBX takes the silver platter URL and runs it through Grok browser video analysis tool
 134 | - Grok produces a breakdown of any remaining issues
 135 | - Every Grok finding maps to a code fix in the NEXT render cycle
 136 | - Grok findings are treated with the same weight as Gemini findings — nothing ignored
 137 | 
 138 | ### THE SILVER PLATTER RULE:
 139 | Video is NEVER shown to PBX until Gemini grades it A.
 140 | When Gemini grades A: post the URL as: 
 141 |   🎬 SILVER PLATTER: https://video.protocolpulse.io/[filename]
 142 |   Gemini grade: A | Scores: [all dimensions] | Ready for Grok review.
 143 | 
 144 | ### WHAT COUNTS AS GRADE A (ALL must be true):
 145 | - pip ≥ 8/10
 146 | - cold_open ≥ 8/10  
 147 | - background ≥ 8/10
 148 | - voices = 10/10 (already achieved — never regress)
 149 | - audio_quality ≥ 9/10 (already achieved — never regress)
 150 | - debug_text = 10/10 (already achieved — never regress)
 151 | - Zero black frames detected by ffprobe blackdetect
 152 | - Zero silence segments detected by ffprobe silencedetect
 153 | - LUFS between -15 and -13 (target -14)
 154 | 
```

### File: app.py (365 lines)
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
  45 | # Security: SECRET must be set in environment — no silent insecure fallback
  46 | _session_secret = os.environ.get("SESSION_SECRET", "")
  47 | if not _session_secret:
  48 |     logging.critical("SESSION_SECRET not set — using ephemeral key. Set SESSION_SECRET in environment for production.")
  49 |     import secrets as _secrets_mod
  50 |     _session_secret = _secrets_mod.token_hex(32)
  51 | app.secret_key = _session_secret
  52 | 
  53 | # Public network endpoints (local by default, cloudflared-ready when set in .env)
  54 | app.config["PUBLIC_HUB_URL"] = os.environ.get("PUBLIC_HUB_URL", "http://127.0.0.1:5000").rstrip("/")
  55 | app.config["PUBLIC_AI_URL"] = os.environ.get("PUBLIC_AI_URL", "http://127.0.0.1:11434").rstrip("/")
  56 | app.config["PUBLIC_SSH_HOST"] = os.environ.get("PUBLIC_SSH_HOST", "").strip()
  57 | app.config["USE_DOUBLE_PIPE"] = os.environ.get("USE_DOUBLE_PIPE", "false").strip().lower() in {
  58 |     "1", "true", "yes", "on"
  59 | }
  60 | 
  61 | # Configure the database
  62 | database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
  63 | # Replit (and some Heroku-style hosts) emit postgres:// — SQLAlchemy 1.4+ requires postgresql://
  64 | if database_url.startswith("postgres://"):
  65 |     database_url = database_url.replace("postgres://", "postgresql://", 1)
  66 | if database_url.startswith("sqlite:"):
  67 |     # SQLite: remove unsupported charset param added by older code
  68 |     if "charset=utf8mb4" in database_url:
  69 |         database_url = database_url.replace("?charset=utf8mb4", "").replace("&charset=utf8mb4", "")
  70 | 
  71 | app.config["SQLALCHEMY_DATABASE_URI"] = database_url
  72 | app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
  73 |     "pool_recycle": 300,
  74 |     "pool_pre_ping": True,
  75 | }
  76 | 
  77 | # Startup env diagnostics.
  78 | # Required vars: missing → log CRITICAL (feature is broken without these).
  79 | # Recommended vars: missing → log INFO (integration degrades gracefully).
  80 | _required_env = ["SESSION_SECRET", "DATABASE_URL", "RESEND_API_KEY"]
  81 | _recommended_env = [
  82 |     "TWITTER_API_KEY",
  83 |     "TWITTER_API_SECRET",
  84 |     "TWITTER_ACCESS_TOKEN",
  85 |     "TWITTER_ACCESS_TOKEN_SECRET",
  86 | ]
  87 | for _name in _required_env:
  88 |     if not os.environ.get(_name):
  89 |         logging.critical(
  90 |             "REQUIRED env var %s is missing — dependent features will fail.", _name
  91 |         )
  92 | for _name in _recommended_env:
  93 |     if not os.environ.get(_name):
  94 |         logging.info("%s not configured (related integration stays degraded/off).", _name)
  95 | 
  96 | app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 1 day default for send_file
  97 | 
  98 | # 3. Initialize extensions
  99 | db.init_app(app)
 100 | migrate = Migrate(app, db)
 101 | login_manager = LoginManager()
 102 | login_manager.init_app(app)
 103 | login_manager.login_view = "login"
 104 | 
 105 | limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
 106 | limiter.init_app(app)
 107 | 
 108 | if _cache is not None:
 109 |     _cache.init_app(app)
 110 |     cache = _cache
 111 | else:
 112 |     class _NullCache:
 113 |         def init_app(self, app): pass
 114 |         def cached(self, timeout=None, key_prefix=None):
 115 |             def decorator(f): return f
 116 |             return decorator
 117 |     cache = _NullCache()
 118 | 
 119 | if SocketIO is not None:
 120 |     socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
 121 | else:
 122 |     socketio = None
 123 | 
 124 | @app.context_processor
 125 | def inject_csrf():
 126 |     """Inject CSRF token for forms. Generate once per session."""
 127 |     if "csrf_token" not in session:
 128 |         session["csrf_token"] = os.urandom(32).hex()
 129 |     return {
 130 |         "csrf_token": session.get("csrf_token"),
 131 |         "public_hub_url": app.config.get("PUBLIC_HUB_URL"),
 132 |         "public_ai_url": app.config.get("PUBLIC_AI_URL"),
 133 |         "public_ssh_host": app.config.get("PUBLIC_SSH_HOST"),
 134 |         "use_double_pipe": app.config.get("USE_DOUBLE_PIPE", False),
 135 |     }
 136 | 
 137 | 
 138 | @app.after_request
 139 | def add_headers(response):
 140 |     """Add cache, security, and performance headers to every response."""
 141 |     from flask import request
 142 | 
 143 |     # ── Security headers ──
 144 |     response.headers["X-Content-Type-Options"] = "nosniff"
 145 |     response.headers["X-Frame-Options"] = "SAMEORIGIN"
 146 |     response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
 147 |     response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
 148 |     response.headers["X-XSS-Protection"] = "1; mode=block"
 149 | 
 150 |     # ── Cache strategy ──
 151 |     if request.path.startswith("/static/"):
 152 |         # Versioned assets (?v=X) get long cache; images get 1 week; CSS/JS get 1 day
 153 |         if any(request.path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')):
 154 |             response.cache_control.max_age = 604800  # 1 week
 155 |             response.cache_control.public = True
 156 |         elif any(request.path.endswith(ext) for ext in ('.css', '.js')):
 157 |             response.cache_control.max_age = 86400  # 1 day
 158 |             response.cache_control.public = True
 159 |         else:
 160 |             response.cache_control.max_age = 86400
 161 |             response.cache_control.public = True
 162 |     elif request.path.startswith("/api/"):
 163 |         # P1-3: API endpoints default to private/no-store — prevents user-specific
 164 |         # data leaking through shared caches. Individual routes may opt into caching.
 165 |         if "Cache-Control" not in response.headers:
 166 |             response.headers["Cache-Control"] = "private, no-store"
 167 |     else:
 168 |         # HTML pages: no-cache but allow revalidation
 169 |         if "Cache-Control" not in response.headers:
 170 |             response.headers["Cache-Control"] = "public, no-cache, must-revalidate"
 171 | 
 172 |     return response
 173 | 
 174 | 
 175 | # 4. Define Template Filters
 176 | @app.template_filter('inject_ads')
 177 | def inject_ads(content):
 178 |     import models
 179 |     from flask import g
 180 |     try:
 181 |         if not hasattr(g, '_active_ads'):
 182 |             g._active_ads = models.Advertisement.query.filter_by(is_active=True).all()
 183 |         active_ads = g._active_ads
 184 |         if not active_ads:
 185 |             return content
 186 |         ad = random.choice(active_ads)
 187 |         from markupsafe import escape as _esc
 188 |         ad_html = f'''
 189 |         <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
 190 |             <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
 191 |             <a href="/ads/go/{ad.id}" rel="noopener" class="text-decoration-none">
 192 |                 <img src="{_esc(ad.image_url or '')}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{_esc(ad.name or '')}">
 193 |                 <p class="mb-0 text-white fw-bold">{_esc(ad.name or '')}</p>
 194 |             </a>
 195 |         </div>
 196 |         '''
 197 |         parts = content.split('</p>', 2)
 198 |         if len(parts) > 2:
 199 |             return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
 200 |         return content + ad_html
 201 |     except Exception as e:
 202 |         logging.warning(f"Ad injection failed: {e}")
 203 |         return content
 204 | 
 205 | @app.template_filter('basename')
 206 | def basename_filter(path):
 207 |     """Return the basename of a path for use in templates (e.g. clip filename)."""
 208 |     if not path:
 209 |         return ""
 210 |     return os.path.basename(str(path).strip())
 211 | 
 212 | @app.template_filter('from_json')
 213 | def from_json_filter(value):
 214 |     if not value:
 215 |         return []
 216 |     try:
 217 |         return json.loads(value)
 218 |     except (json.JSONDecodeError, TypeError):
 219 |         return []
 220 | 
 221 | # Distinct header image per article: when stored URL is missing or the old single default, use pool by title
 222 | _OLD_SINGLE_DEFAULT_HEADER = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"
 223 | 
 224 | @app.template_filter('article_header_display')
 225 | def article_header_display_filter(article):
 226 |     """Return a distinct header image URL for this article (avoids same image on every card)."""
 227 |     if article is None:
 228 |         return _OLD_SINGLE_DEFAULT_HEADER
 229 |     stored = (getattr(article, "header_image_url", None) or "").strip()
 230 |     if stored and stored != _OLD_SINGLE_DEFAULT_HEADER:
 231 |         return stored
 232 |     return "/static/images/default-header.png"
 233 | 
 234 | # 5. User loader for Flask-Login
 235 | @login_manager.user_loader
 236 | def load_user(user_id):
 237 |     import models
 238 |     try:
 239 |         return models.User.query.get(int(user_id))
 240 |     except (ValueError, TypeError):
 241 |         return None
 242 | 
 243 | # =====================================
 244 | # THE IGNITION ZONE (CRITICAL ORDER)
 245 | # =====================================
 246 | # When we run as python app.py, __name__ is "__main__". Later, "import routes" does
 247 | # "from app import app", which loads this file again as module "app" (a second Flask
 248 | # app). Routes then register on that second app, but we call app.run() on this one → 404.
 249 | # So make "app" resolve to this same module when we are the main script.
 250 | if __name__ == "__main__":
 251 |     import sys
 252 |     sys.modules["app"] = sys.modules["__main__"]
 253 | 
 254 | with app.app_context():
 255 |     # 1. Load the models into memory first
 256 |     import models
 257 |     # Create any missing tables at startup (idempotent — safe to always run).
 258 |     # Set ENABLE_RUNTIME_DB_CREATE_ALL=false to suppress on managed migration envs.
 259 |     if os.environ.get("ENABLE_RUNTIME_DB_CREATE_ALL", "true").strip().lower() not in {"0", "false", "no", "off"}:
 260 |         try:
 261 |             db.create_all()
 262 |         except Exception as _dbe:
 263 |             logging.warning("db.create_all() failed (non-fatal): %s", _dbe)
 264 | 
 265 |     # p3-sentiment-intel: migration-safe column/table additions
 266 |     try:
 267 |         from utils.db_migrate_sentiment import run_migrations
 268 |         run_migrations(db)
 269 |     except Exception as _mige:
 270 |         logging.warning("db_migrate_sentiment failed (non-fatal): %s", _mige)
 271 | 
 272 | def _run_dev_server():
 273 |     port = 5000
 274 |     host = "0.0.0.0"
 275 |     print(f"Starting Protocol Pulse -> http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
 276 |     # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
 277 |     if socketio is not None:
 278 |         socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
 279 |     else:
 280 |         app.run(host=host, port=port, debug=False, use_reloader=False)
 281 | 
 282 | # Keep routes import near the very bottom so the app object and extensions are fully initialized first.
 283 | import routes
 284 | from routes_api_v2 import api_v2
 285 | try:
 286 |     from routes_api_terminal import terminal_bp
 287 |     app.register_blueprint(terminal_bp)
 288 | except Exception as e:
 289 |     logging.critical("Terminal API blueprint failed to load: %s", e)
 290 | try:
 291 |     from routes_commander import commander_bp
 292 |     app.register_blueprint(commander_bp)
 293 |     logging.info("Commander API blueprint registered at /api/v1")
 294 | except Exception as _e:
 295 |     logging.warning("Commander blueprint not loaded: %s", _e)
 296 | try:
 297 |     from routes_newsletter_trigger import newsletter_trigger_bp
 298 |     app.register_blueprint(newsletter_trigger_bp)
 299 | except Exception as e:
 300 |     logging.critical("Newsletter trigger blueprint failed to load: %s", e)
 301 | 
 302 | # B1 Newsletter Engine — hard fail if feature is active
 303 | from routes_newsletter_b1 import newsletter_b1_bp
 304 | app.register_blueprint(newsletter_b1_bp)
 305 | logging.info("B1 Newsletter blueprint registered")
 306 | app.register_blueprint(api_v2)
 307 | from onboarding_routes import onboarding_bp
 308 | app.register_blueprint(onboarding_bp)
 309 | 
 310 | from oracle_routes import oracle_bp
 311 | app.register_blueprint(oracle_bp)
 312 | 
 313 | # SESSION 3 — Media Unified Blueprint
 314 | try:
 315 |     from core.blueprints.media import media_bp
 316 |     app.register_blueprint(media_bp)
 317 |     logging.info("Media Unified blueprint registered (/media, /api/signal/composite, /api/sentiment/heatmap, /api/media/sources/health, /api/media/feed/*)")
 318 | except Exception as _e:
 319 |     logging.warning("Media Unified blueprint not loaded: %s", _e)
 320 | 
 321 | # SESSION 6 — Schiff Bot Blueprint
 322 | try:
 323 |     from core.blueprints.schiff import schiff_bp
 324 |     app.register_blueprint(schiff_bp)
 325 |     logging.info("Schiff Bot blueprint registered (/schiff, /api/schiff/*)")
 326 | except Exception as _e:
 327 |     logging.warning("Schiff Bot blueprint not loaded: %s", _e)
 328 | 
 329 | # SESSION 7 — Oracle Avatar Blueprint
 330 | try:
 331 |     from core.blueprints.oracle_avatar import oracle_avatar_bp
 332 |     app.register_blueprint(oracle_avatar_bp)
 333 |     logging.info("Oracle Avatar blueprint registered (/oracle-live, /api/oracle/*)")
 334 | except Exception as _e:
 335 |     logging.warning("Oracle Avatar blueprint not loaded: %s", _e)
 336 | 
 337 | try:
 338 |     from services.video_engine.dashboard.app import dashboard_bp
 339 |     app.register_blueprint(dashboard_bp)
 340 |     logging.info("Dashboard blueprint registered at /dashboard/")
 341 | except ImportError as _e:
 342 |     logging.warning("Dashboard blueprint not loaded: %s", _e)
 343 | 
 344 | # Start background APScheduler only when explicitly enabled for this process.
 345 | if os.environ.get("ENABLE_APSCHEDULER", "false").strip().lower() in {"1", "true", "yes", "on"}:
 346 |     try:
 347 |         from services.scheduler import initialize_scheduler
 348 |         _sch = initialize_scheduler()
 349 |         logging.info("Scheduler initialized: %s", _sch)
 350 |     except Exception as _e:
 351 |         logging.warning("Scheduler init skipped: %s", _e)
 352 | 
 353 | # Diagnose after routes import so startup logs reflect the real routing table.
 354 | try:
 355 |     rules = [r.rule for r in app.url_map.iter_rules()]
 356 |     has_root = "/" in rules
 357 |     logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
 358 |     if not has_root:
 359 |         logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
 360 | except Exception as e:
 361 |     logging.warning("Could not list routes: %s", e)
 362 | 
 363 | if __name__ == "__main__":
 364 |     _run_dev_server()
 365 | 
```

### File: core/blueprints/__init__.py (1 lines)
```
   1 | 
```

### File: core/blueprints/charts.py (460 lines)
```
   1 | """
   2 | SESSION 4 — CHARTS BLUEPRINT
   3 | Bloomberg terminal-grade Bitcoin intelligence charts.
   4 | 
   5 | New API endpoints (no conflict with routes.py):
   6 |   GET /api/charts/price?period=7d          — CoinGecko price history
   7 |   GET /api/charts/hashrate?period=1y       — mempool.space hashrate history
   8 |   GET /api/charts/difficulty?period=1y     — mempool.space difficulty history
   9 |   GET /api/charts/mvrv?period=1y           — CoinMetrics community MVRV
  10 |   GET /api/charts/realized-price?period=1y — CoinMetrics community realized price
  11 |   GET /api/charts/fg-history?period=1y     — alternative.me F&G history (365 pts)
  12 |   GET /api/charts/s2f?period=all           — Stock-to-Flow model price (computed, no API)
  13 |   GET /api/charts/og-image?chart=price     — matplotlib server-side OG image
  14 | 
  15 | Existing routes.py endpoints preserved:
  16 |   /api/charts/price-history, /api/charts/hashrate-history,
  17 |   /api/charts/fear-greed, /api/charts/mempool-data, /api/charts/fee-history,
  18 |   /api/charts/pool-distribution, /api/charts/lightning, /api/charts/ai-explain,
  19 |   /api/charts/price-alert, /charts/embed/<chart_id>
  20 | """
  21 | 
  22 | from flask import Blueprint, request, jsonify, Response
  23 | import requests as _req
  24 | import time as _time
  25 | import logging
  26 | import functools
  27 | import math
  28 | from datetime import datetime, timezone, timedelta
  29 | 
  30 | charts_bp = Blueprint("charts_bp", __name__)
  31 | 
  32 | _HEADERS = {
  33 |     "User-Agent": "ProtocolPulse/1.0 (+https://protocolpulse.io)",
  34 |     "Accept": "application/json",
  35 | }
  36 | 
  37 | 
  38 | # ── In-process TTL cache ───────────────────────────────────────────────────────
  39 | 
  40 | def _ttl_cache(seconds):
  41 |     """Simple in-process TTL cache decorator."""
  42 |     def decorator(fn):
  43 |         _store = {}
  44 | 
  45 |         @functools.wraps(fn)
  46 |         def wrapper(*args, **kwargs):
  47 |             key = (args, tuple(sorted(kwargs.items())))
  48 |             now = _time.monotonic()
  49 |             if key in _store:
  50 |                 result, ts = _store[key]
  51 |                 if now - ts < seconds:
  52 |                     return result
  53 |             result = fn(*args, **kwargs)
  54 |             _store[key] = (result, now)
  55 |             return result
  56 | 
  57 |         return wrapper
  58 |     return decorator
  59 | 
  60 | 
  61 | def _period_to_days(period):
  62 |     """Convert period string ('7d', '1m', '1y', 'all') → int days or 'max'."""
  63 |     mapping = {
  64 |         "1d": 1, "7d": 7, "1m": 30, "3m": 90,
  65 |         "6m": 180, "1y": 365, "all": "max",
  66 |     }
  67 |     return mapping.get(str(period).lower().strip(), 7)
  68 | 
  69 | 
  70 | def _now_iso():
  71 |     return datetime.now(timezone.utc).isoformat()
  72 | 
  73 | 
  74 | # ── Data Fetchers ──────────────────────────────────────────────────────────────
  75 | 
  76 | @_ttl_cache(300)
  77 | def _fetch_price_history(days):
  78 |     """Fetch BTC/USD price history from CoinGecko. Cache 5 min."""
  79 |     try:
  80 |         if days == "max":
  81 |             url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=max"
  82 |         else:
  83 |             interval = "daily" if int(days) >= 30 else "hourly"
  84 |             url = (
  85 |                 f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
  86 |                 f"?vs_currency=usd&days={days}&interval={interval}"
  87 |             )
  88 |         r = _req.get(url, timeout=12, headers=_HEADERS)
  89 |         r.raise_for_status()
  90 |         data = r.json()
  91 |         return data.get("prices", [])  # [[ts_ms, price], ...]
  92 |     except Exception as e:
  93 |         logging.warning("CoinGecko price history error: %s", e)
  94 |         return None
  95 | 
  96 | 
  97 | @_ttl_cache(600)
  98 | def _fetch_hashrate_history(period_days):
  99 |     """Fetch hashrate history from mempool.space. Cache 10 min."""
 100 |     try:
 101 |         d = period_days if period_days != "max" else 1095
 102 |         span = "3m" if int(d) <= 90 else ("6m" if int(d) <= 180 else ("1y" if int(d) <= 365 else "3y"))
 103 |         r = _req.get(f"https://mempool.space/api/v1/mining/hashrate/{span}", timeout=12, headers=_HEADERS)
 104 |         r.raise_for_status()
 105 |         raw = r.json()
 106 |         cutoff_ts = _time.time() - int(d) * 86400
 107 |         pts = [
 108 |             [h["timestamp"] * 1000, round(h["avgHashrate"] / 1e18, 2)]
 109 |             for h in raw.get("hashrates", [])
 110 |             if h.get("timestamp", 0) >= cutoff_ts
 111 |         ]
 112 |         return pts
 113 |     except Exception as e:
 114 |         logging.warning("Mempool hashrate error: %s", e)
 115 |         return None
 116 | 
 117 | 
 118 | @_ttl_cache(600)
 119 | def _fetch_difficulty_history(period_days):
 120 |     """Fetch difficulty adjustment history from mempool.space. Cache 10 min."""
 121 |     try:
 122 |         d = period_days if period_days != "max" else 1095
 123 |         span = "3m" if int(d) <= 90 else ("6m" if int(d) <= 180 else ("1y" if int(d) <= 365 else "3y"))
 124 |         r = _req.get(f"https://mempool.space/api/v1/mining/hashrate/{span}", timeout=12, headers=_HEADERS)
 125 |         r.raise_for_status()
 126 |         raw = r.json()
 127 |         cutoff_ts = _time.time() - int(d) * 86400
 128 |         pts = [
 129 |             [entry["time"] * 1000, round(entry["difficulty"] / 1e12, 4)]
 130 |             for entry in raw.get("difficulty", [])
 131 |             if entry.get("time", 0) >= cutoff_ts
 132 |         ]
 133 |         return pts
 134 |     except Exception as e:
 135 |         logging.warning("Mempool difficulty error: %s", e)
 136 |         return None
 137 | 
 138 | 
 139 | @_ttl_cache(3600)
 140 | def _fetch_coinmetrics(metric, limit):
 141 |     """Fetch from CoinMetrics community API (free, no key). Cache 1 hr."""
 142 |     try:
 143 |         url = (
 144 |             f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
 145 |             f"?assets=btc&metrics={metric}&frequency=1d"
 146 |             f"&limit_per_asset={limit}&page_size={limit}"
 147 |         )
 148 |         r = _req.get(url, timeout=15, headers=_HEADERS)
 149 |         r.raise_for_status()
 150 |         pts = []
 151 |         for row in r.json().get("data", []):
 152 |             try:
 153 |                 ts = int(datetime.fromisoformat(
 154 |                     row["time"].rstrip("Z") + "+00:00"
 155 |                 ).timestamp() * 1000)
 156 |                 val = float(row.get(metric) or 0)
 157 |                 if val > 0:
 158 |                     pts.append([ts, val])
 159 |             except Exception:
 160 |                 pass
 161 |         return pts
 162 |     except Exception as e:
 163 |         logging.warning("CoinMetrics %s error: %s", metric, e)
 164 |         return None
 165 | 
 166 | 
 167 | @_ttl_cache(3600)
 168 | def _fetch_fg_history(limit):
 169 |     """Fetch Fear & Greed historical index from alternative.me. Cache 1 hr."""
 170 |     try:
 171 |         r = _req.get(
 172 |             f"https://api.alternative.me/fng/?limit={limit}&format=json",
 173 |             timeout=12, headers=_HEADERS
 174 |         )
 175 |         r.raise_for_status()
 176 |         pts = []
 177 |         for e in r.json().get("data", []):
 178 |             try:
 179 |                 pts.append([int(e["timestamp"]) * 1000, int(e["value"])])
 180 |             except Exception:
 181 |                 pass
 182 |         pts.sort(key=lambda x: x[0])  # ascending chronological
 183 |         return pts
 184 |     except Exception as e:
 185 |         logging.warning("Fear & Greed history error: %s", e)
 186 |         return None
 187 | 
 188 | 
 189 | # ── API Endpoints ──────────────────────────────────────────────────────────────
 190 | 
 191 | @charts_bp.route("/api/charts/price")
 192 | def api_charts_price():
 193 |     """BTC/USD price history from CoinGecko. Cached 5 min."""
 194 |     try:
 195 |         period = request.args.get("period", "7d")
 196 |         days = _period_to_days(period)
 197 |         pts = _fetch_price_history(days)
 198 |         if pts is None:
 199 |             return jsonify({"error": "upstream unavailable", "data": []}), 503
 200 |         return jsonify({
 201 |             "data": pts,
 202 |             "source": "CoinGecko",
 203 |             "unit": "USD",
 204 |             "cached_until": _now_iso(),
 205 |             "period": period,
 206 |         })
 207 |     except Exception as e:
 208 |         logging.error("api_charts_price error: %s", e)
 209 |         return jsonify({"error": "internal error", "data": []}), 500
 210 | 
 211 | 
 212 | @charts_bp.route("/api/charts/hashrate")
 213 | def api_charts_hashrate():
 214 |     """Bitcoin network hashrate history (EH/s) from mempool.space. Cached 10 min."""
 215 |     try:
 216 |         period = request.args.get("period", "1y")
 217 |         days = _period_to_days(period)
 218 |         pts = _fetch_hashrate_history(days)
 219 |         if pts is None:
 220 |             return jsonify({"error": "upstream unavailable", "data": []}), 503
 221 |         return jsonify({
 222 |             "data": pts,
 223 |             "source": "mempool.space",
 224 |             "unit": "EH/s",
 225 |             "period": period,
 226 |         })
 227 |     except Exception as e:
 228 |         logging.error("api_charts_hashrate error: %s", e)
 229 |         return jsonify({"error": "internal error", "data": []}), 500
 230 | 
 231 | 
 232 | @charts_bp.route("/api/charts/difficulty")
 233 | def api_charts_difficulty():
 234 |     """Bitcoin mining difficulty history (T) from mempool.space. Cached 10 min."""
 235 |     try:
 236 |         period = request.args.get("period", "1y")
 237 |         days = _period_to_days(period)
 238 |         pts = _fetch_difficulty_history(days)
 239 |         if pts is None:
 240 |             return jsonify({"error": "upstream unavailable", "data": []}), 503
 241 |         return jsonify({
 242 |             "data": pts,
 243 |             "source": "mempool.space",
 244 |             "unit": "T",
 245 |             "period": period,
 246 |         })
 247 |     except Exception as e:
 248 |         logging.error("api_charts_difficulty error: %s", e)
 249 |         return jsonify({"error": "internal error", "data": []}), 500
 250 | 
 251 | 
 252 | @charts_bp.route("/api/charts/mvrv")
 253 | def api_charts_mvrv():
 254 |     """MVRV ratio from CoinMetrics community API. Cached 1 hr."""
 255 |     try:
 256 |         period = request.args.get("period", "1y")
 257 |         days = _period_to_days(period)
 258 |         limit = days if isinstance(days, int) else 1095
 259 |         pts = _fetch_coinmetrics("CapMVRVCur", limit)
 260 |         if pts is None:
 261 |             return jsonify({"error": "upstream unavailable", "data": []}), 503
 262 |         return jsonify({
 263 |             "data": pts,
 264 |             "source": "CoinMetrics (community)",
 265 |             "unit": "ratio",
 266 |             "period": period,
 267 |         })
 268 |     except Exception as e:
 269 |         logging.error("api_charts_mvrv error: %s", e)
 270 |         return jsonify({"error": "internal error", "data": []}), 500
 271 | 
 272 | 
 273 | @charts_bp.route("/api/charts/realized-price")
 274 | def api_charts_realized_price():
 275 |     """Bitcoin realized price from CoinMetrics community API. Cached 1 hr."""
 276 |     try:
 277 |         period = request.args.get("period", "1y")
 278 |         days = _period_to_days(period)
 279 |         limit = days if isinstance(days, int) else 1095
 280 |         pts = _fetch_coinmetrics("PriceRealizedUSD", limit)
 281 |         if pts is None:
 282 |             return jsonify({"error": "upstream unavailable", "data": []}), 503
 283 |         return jsonify({
 284 |             "data": pts,
 285 |             "source": "CoinMetrics (community)",
 286 |             "unit": "USD",
 287 |             "period": period,
 288 |         })
 289 |     except Exception as e:
 290 |         logging.error("api_charts_realized_price error: %s", e)
 291 |         return jsonify({"error": "internal error", "data": []}), 500
 292 | 
 293 | 
 294 | @charts_bp.route("/api/charts/fg-history")
 295 | def api_charts_fg_history():
 296 |     """Fear & Greed index history from alternative.me. Cached 1 hr."""
 297 |     try:
 298 |         period = request.args.get("period", "1y")
 299 |         days = _period_to_days(period)
 300 |         limit = days if isinstance(days, int) else 365
 301 |         limit = min(limit, 365)
 302 |         pts = _fetch_fg_history(limit)
 303 |         if pts is None:
 304 |             return jsonify({"error": "upstream unavailable", "data": []}), 503
 305 |         return jsonify({
 306 |             "data": pts,
 307 |             "source": "alternative.me",
 308 |             "unit": "F&G 0-100",
 309 |             "period": period,
 310 |         })
 311 |     except Exception as e:
 312 |         logging.error("api_charts_fg_history error: %s", e)
 313 |         return jsonify({"error": "internal error", "data": []}), 500
 314 | 
 315 | 
 316 | @charts_bp.route("/api/charts/s2f")
 317 | def api_charts_s2f():
 318 |     """
 319 |     Stock-to-Flow model price series — computed server-side, no external API.
 320 |     Returns both the S2F model price and the ratio.
 321 |     """
 322 |     try:
 323 |         period = request.args.get("period", "1y")
 324 |         days = _period_to_days(period)
 325 |         days_back = days if isinstance(days, int) else 1825  # max=5y
 326 | 
 327 |         HALVINGS = [
 328 |             (datetime(2009,  1,  3, tzinfo=timezone.utc), 50.0),
 329 |             (datetime(2012, 11, 28, tzinfo=timezone.utc), 25.0),
 330 |             (datetime(2016,  7,  9, tzinfo=timezone.utc), 12.5),
 331 |             (datetime(2020,  5, 11, tzinfo=timezone.utc), 6.25),
 332 |             (datetime(2024,  4, 20, tzinfo=timezone.utc), 3.125),
 333 |         ]
 334 |         BLOCKS_PER_YEAR = 52_560   # 144 blocks/day × 365
 335 |         BLOCKS_PER_DAY  = 144
 336 | 
 337 |         def _subsidy_at(dt):
 338 |             s = 50.0
 339 |             for halving_dt, sub in HALVINGS:
 340 |                 if dt >= halving_dt:
 341 |                     s = sub
 342 |             return s
 343 | 
 344 |         def _supply_at(dt):
 345 |             total = 0.0
 346 |             for i, (halving_dt, sub) in enumerate(HALVINGS):
 347 |                 epoch_end = HALVINGS[i + 1][0] if i + 1 < len(HALVINGS) else dt
 348 |                 if dt <= halving_dt:
 349 |                     break
 350 |                 end = min(dt, epoch_end)
 351 |                 days_in_epoch = max(0, (end - halving_dt).days)
 352 |                 total += days_in_epoch * BLOCKS_PER_DAY * sub
 353 |             return total
 354 | 
 355 |         now = datetime.now(timezone.utc)
 356 |         start = now - timedelta(days=days_back)
 357 |         pts = []
 358 |         cur = start
 359 |         step = timedelta(days=7)
 360 |         while cur <= now:
 361 |             supply = _supply_at(cur)
 362 |             subsidy = _subsidy_at(cur)
 363 |             flow = BLOCKS_PER_YEAR * subsidy
 364 |             if flow > 0 and supply > 0:
 365 |                 s2f_ratio = supply / flow
 366 |                 # PlanB's simplified model: price ≈ exp(−1.84) × SF^3.36
 367 |                 model_price = round(math.exp(-1.84) * (s2f_ratio ** 3.36), 2)
 368 |                 pts.append([int(cur.timestamp() * 1000), model_price])
 369 |             cur += step
 370 | 
 371 |         return jsonify({
 372 |             "data": pts,
 373 |             "source": "Computed (PlanB S2F model)",
 374 |             "unit": "USD model",
 375 |             "period": period,
 376 |             "note": "S2F model price = exp(-1.84) × SF^3.36",
 377 |         })
 378 |     except Exception as e:
 379 |         logging.error("api_charts_s2f error: %s", e)
 380 |         return jsonify({"error": "internal error", "data": []}), 500
 381 | 
 382 | 
 383 | @charts_bp.route("/api/charts/og-image")
 384 | def api_charts_og_image():
 385 |     """
 386 |     Generate OG image (PNG) of requested chart via matplotlib.
 387 |     Query params: chart=(price|hashrate|fear-greed), period=(7d|1m|1y|all)
 388 |     """
 389 |     try:
 390 |         chart = request.args.get("chart", "price")
 391 |         period = request.args.get("period", "7d")
 392 |         days = _period_to_days(period)
 393 | 
 394 |         try:
 395 |             import matplotlib
 396 |             matplotlib.use("Agg")
 397 |             import matplotlib.pyplot as plt
 398 |             import matplotlib.ticker as mticker
 399 |             import matplotlib.dates as mdates
 400 |             import io as _io
 401 |         except ImportError:
 402 |             logging.warning("matplotlib not available for OG image generation")
 403 |             return jsonify({"error": "matplotlib not available"}), 503
 404 | 
 405 |         # Fetch data based on chart type
 406 |         if chart == "price":
 407 |             raw = _fetch_price_history(days)
 408 |             line_color = "#F59E0B"
 409 |             title = f"BTC/USD — {period.upper()}"
 410 |             y_fmt = lambda v, _: f"${v:,.0f}"
 411 |         elif chart == "hashrate":
 412 |             raw = _fetch_hashrate_history(days if days != "max" else 365)
 413 |             line_color = "#5DE4FF"
 414 |             title = f"Bitcoin Hashrate — {period.upper()}"
 415 |             y_fmt = lambda v, _: f"{v:.0f} EH/s"
 416 |         elif chart == "fear-greed":
 417 |             limit = days if isinstance(days, int) else 365
 418 |             raw = _fetch_fg_history(min(limit, 365))
 419 |             line_color = "#89FFB8"
 420 |             title = f"Fear & Greed Index — {period.upper()}"
 421 |             y_fmt = lambda v, _: f"{v:.0f}"
 422 |         else:
 423 |             return jsonify({"error": "unsupported chart type"}), 400
 424 | 
 425 |         if not raw:
 426 |             return jsonify({"error": "no data available"}), 503
 427 | 
 428 |         xs = [datetime.fromtimestamp(p[0] / 1000) for p in raw]
 429 |         ys = [p[1] for p in raw]
 430 | 
 431 |         fig, ax = plt.subplots(figsize=(12, 6.3), facecolor="#080810")
 432 |         ax.set_facecolor("#080810")
 433 |         ax.plot(xs, ys, color=line_color, linewidth=2.5, solid_capstyle="round")
 434 |         ax.fill_between(xs, ys, alpha=0.2, color=line_color)
 435 |         ax.set_title(title, color="#FFFFFF", fontsize=18, fontweight="bold", pad=20)
 436 |         ax.tick_params(colors="#95A0BA", labelsize=9)
 437 |         ax.yaxis.set_major_formatter(mticker.FuncFormatter(y_fmt))
 438 |         ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
 439 |         ax.xaxis.set_major_locator(mdates.AutoDateLocator())
 440 |         for spine in ax.spines.values():
 441 |             spine.set_edgecolor("#1C1C2E")
 442 |         ax.grid(color="#1C1C2E", linewidth=0.5, alpha=0.8, linestyle="--")
 443 |         fig.text(0.98, 0.02, "protocolpulse.io", ha="right",
 444 |                  color="#5DE4FF", fontsize=9, alpha=0.7)
 445 |         fig.tight_layout()
 446 | 
 447 |         buf = _io.BytesIO()
 448 |         plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
 449 |                     facecolor="#080810", edgecolor="none")
 450 |         plt.close(fig)
 451 |         buf.seek(0)
 452 | 
 453 |         return Response(buf.read(), mimetype="image/png", headers={
 454 |             "Cache-Control": "public, max-age=300",
 455 |             "Content-Disposition": f'inline; filename="btc-{chart}-{period}.png"',
 456 |         })
 457 |     except Exception as e:
 458 |         logging.error("api_charts_og_image error: %s", e)
 459 |         return jsonify({"error": "internal error"}), 500
 460 | 
```

### File: core/blueprints/media.py (633 lines)
```
   1 | """
   2 | SESSION 3 — MEDIA UNIFIED BLUEPRINT
   3 | =====================================
   4 | Routes:
   5 |   GET  /media                         — Media Intelligence page
   6 |   GET  /media-unified                 — Alias redirect → /media
   7 |   GET  /api/signal/composite          — Weighted signal score (cached 2min)
   8 |   GET  /api/sentiment/heatmap         — Category sentiment grid (last 2h)
   9 |   GET  /api/media/sources/health      — Source scraper health
  10 |   GET  /api/media/feed/intelligence   — Latest 20 PP articles with sentiment
  11 |   GET  /api/media/feed/stream         — SSE stream for real-time feed
  12 | """
  13 | 
  14 | import json
  15 | import logging
  16 | import time
  17 | from datetime import datetime, timedelta
  18 | 
  19 | import requests
  20 | from flask import Blueprint, Response, jsonify, redirect, render_template, request, stream_with_context
  21 | 
  22 | log = logging.getLogger(__name__)
  23 | 
  24 | media_bp = Blueprint("media", __name__)
  25 | 
  26 | # ── In-process cache ───────────────────────────────────────────────────────
  27 | _cache: dict = {}
  28 | 
  29 | 
  30 | def _cached(key: str, ttl: int, fn):
  31 |     """Simple TTL cache. Runs fn() to refresh if stale."""
  32 |     entry = _cache.get(key)
  33 |     now = time.time()
  34 |     if entry and now - entry["ts"] < ttl:
  35 |         return entry["data"]
  36 |     try:
  37 |         data = fn()
  38 |         _cache[key] = {"ts": now, "data": data}
  39 |         return data
  40 |     except Exception as exc:
  41 |         log.warning("cache refresh failed for %s: %s", key, exc)
  42 |         return entry["data"] if entry else None
  43 | 
  44 | 
  45 | # ── Helpers ────────────────────────────────────────────────────────────────
  46 | 
  47 | def _utcnow():
  48 |     return datetime.utcnow()
  49 | 
  50 | 
  51 | def _sentiment_label(score: float) -> str:
  52 |     if score is None:
  53 |         return "NEUTRAL"
  54 |     if score >= 65:
  55 |         return "BULLISH"
  56 |     if score <= 35:
  57 |         return "BEARISH"
  58 |     return "NEUTRAL"
  59 | 
  60 | 
  61 | def _sentiment_color(score: float) -> str:
  62 |     if score is None:
  63 |         return "#9ca3af"
  64 |     if score >= 65:
  65 |         return "#22c55e"
  66 |     if score <= 35:
  67 |         return "#ef4444"
  68 |     return "#f59e0b"
  69 | 
  70 | 
  71 | def _signal_color(score: float) -> str:
  72 |     if score >= 60:
  73 |         return "#22c55e"
  74 |     if score >= 30:
  75 |         return "#f59e0b"
  76 |     return "#ef4444"
  77 | 
  78 | 
  79 | def _signal_label(score: float) -> str:
  80 |     if score >= 75:
  81 |         return "STRONG"
  82 |     if score >= 60:
  83 |         return "ELEVATED"
  84 |     if score >= 40:
  85 |         return "MODERATE"
  86 |     if score >= 20:
  87 |         return "WEAK"
  88 |     return "MINIMAL"
  89 | 
  90 | 
  91 | # ── Signal Composite Logic ─────────────────────────────────────────────────
  92 | 
  93 | def _compute_composite_signal():
  94 |     """
  95 |     Weighted composite signal from 4 sub-components:
  96 |       Article Velocity   30%
  97 |       Sentiment Trend    25%
  98 |       Network Activity   20%
  99 |       Social Volume      15%
 100 |       Fear & Greed       10%
 101 |     Returns dict with overall score + sub-components.
 102 |     """
 103 |     from app import db
 104 |     from models import Article, FeedItem, SentimentSnapshot
 105 | 
 106 |     now = _utcnow()
 107 |     cutoff_1h = now - timedelta(hours=1)
 108 |     cutoff_2h = now - timedelta(hours=2)
 109 |     cutoff_24h = now - timedelta(hours=24)
 110 | 
 111 |     # ── Article Velocity (30%) ──
 112 |     try:
 113 |         articles_1h = Article.query.filter(
 114 |             Article.published == True,
 115 |             Article.created_at >= cutoff_1h,
 116 |         ).count()
 117 |         articles_24h = Article.query.filter(
 118 |             Article.published == True,
 119 |             Article.created_at >= cutoff_24h,
 120 |         ).count()
 121 |         hourly_avg = max(articles_24h / 24.0, 0.5)
 122 |         velocity_ratio = min(articles_1h / hourly_avg, 3.0)
 123 |         # Map 0-3x ratio → 0-100
 124 |         velocity_score = min(round(velocity_ratio / 3.0 * 100), 100)
 125 |         velocity_delta = round((velocity_ratio - 1.0) * 100)  # % vs baseline
 126 |     except Exception as exc:
 127 |         log.warning("velocity calc failed: %s", exc)
 128 |         articles_1h, articles_24h, velocity_score, velocity_delta = 0, 0, 50, 0
 129 | 
 130 |     # ── Sentiment Trend (25%) ──
 131 |     try:
 132 |         snapshot = (
 133 |             SentimentSnapshot.query
 134 |             .order_by(SentimentSnapshot.created_at.desc())
 135 |             .first()
 136 |         )
 137 |         sentiment_score = round(snapshot.score or 50) if snapshot else 50
 138 |         # 24h ago snapshot for delta
 139 |         snap_24h = (
 140 |             SentimentSnapshot.query
 141 |             .filter(SentimentSnapshot.created_at <= cutoff_24h)
 142 |             .order_by(SentimentSnapshot.created_at.desc())
 143 |             .first()
 144 |         )
 145 |         sentiment_delta = round(sentiment_score - (snap_24h.score or 50)) if snap_24h else 0
 146 |     except Exception as exc:
 147 |         log.warning("sentiment calc failed: %s", exc)
 148 |         sentiment_score, sentiment_delta = 50, 0
 149 | 
 150 |     # ── Network Activity (20%) — mempool.space ──
 151 |     def _fetch_mempool():
 152 |         r = requests.get(
 153 |             "https://mempool.space/api/mempool",
 154 |             timeout=5,
 155 |             headers={"User-Agent": "ProtocolPulse/3.0"},
 156 |         )
 157 |         r.raise_for_status()
 158 |         return r.json()
 159 | 
 160 |     try:
 161 |         mempool_data = _cached("mempool_stats", 120, _fetch_mempool)
 162 |         pending_txs = (mempool_data or {}).get("count", 0)
 163 |         # 0 pending → score 20, 200k+ → score 80 (high activity)
 164 |         network_score = min(max(int(20 + (pending_txs / 200000) * 60), 20), 85)
 165 |         network_delta = 0  # directional delta not available from single snapshot
 166 |     except Exception as exc:
 167 |         log.warning("mempool calc failed: %s", exc)
 168 |         pending_txs, network_score, network_delta = 0, 50, 0
 169 | 
 170 |     # ── Social Volume (15%) — FeedItem count last 1h ──
 171 |     try:
 172 |         social_1h = FeedItem.query.filter(
 173 |             FeedItem.created_at >= cutoff_1h,
 174 |         ).count()
 175 |         social_24h = FeedItem.query.filter(
 176 |             FeedItem.created_at >= cutoff_24h,
 177 |         ).count()
 178 |         social_avg = max(social_24h / 24.0, 0.5)
 179 |         social_ratio = min(social_1h / social_avg, 3.0)
 180 |         social_score = min(round(social_ratio / 3.0 * 100), 100)
 181 |         social_delta = round((social_ratio - 1.0) * 100)
 182 |     except Exception as exc:
 183 |         log.warning("social volume calc failed: %s", exc)
 184 |         social_1h, social_score, social_delta = 0, 50, 0
 185 | 
 186 |     # ── Fear & Greed (10%) ──
 187 |     def _fetch_fng():
 188 |         r = requests.get(
 189 |             "https://api.alternative.me/fng/?limit=2",
 190 |             timeout=5,
 191 |             headers={"User-Agent": "ProtocolPulse/3.0"},
 192 |         )
 193 |         r.raise_for_status()
 194 |         return r.json()
 195 | 
 196 |     try:
 197 |         fng_data = _cached("fng_latest", 3600, _fetch_fng)
 198 |         fng_items = (fng_data or {}).get("data", [])
 199 |         fng_score = int(fng_items[0]["value"]) if fng_items else 50
 200 |         fng_delta = (
 201 |             int(fng_items[0]["value"]) - int(fng_items[1]["value"])
 202 |             if len(fng_items) >= 2
 203 |             else 0
 204 |         )
 205 |         fng_label = (fng_items[0].get("value_classification") or "Neutral").upper() if fng_items else "NEUTRAL"
 206 |     except Exception as exc:
 207 |         log.warning("fng calc failed: %s", exc)
 208 |         fng_score, fng_delta, fng_label = 50, 0, "NEUTRAL"
 209 | 
 210 |     # ── Weighted Composite ──
 211 |     composite = round(
 212 |         velocity_score * 0.30
 213 |         + sentiment_score * 0.25
 214 |         + network_score * 0.20
 215 |         + social_score * 0.15
 216 |         + fng_score * 0.10
 217 |     )
 218 | 
 219 |     return {
 220 |         "score": composite,
 221 |         "label": _signal_label(composite),
 222 |         "color": _signal_color(composite),
 223 |         "components": {
 224 |             "article_velocity": {
 225 |                 "label": "Article Velocity",
 226 |                 "score": velocity_score,
 227 |                 "delta": velocity_delta,
 228 |                 "detail": f"{articles_1h} articles/hr",
 229 |                 "weight": 30,
 230 |             },
 231 |             "sentiment_trend": {
 232 |                 "label": "Sentiment Trend",
 233 |                 "score": sentiment_score,
 234 |                 "delta": sentiment_delta,
 235 |                 "detail": _sentiment_label(sentiment_score),
 236 |                 "weight": 25,
 237 |             },
 238 |             "network_activity": {
 239 |                 "label": "Network Activity",
 240 |                 "score": network_score,
 241 |                 "delta": network_delta,
 242 |                 "detail": f"{pending_txs:,} mempool txs",
 243 |                 "weight": 20,
 244 |             },
 245 |             "social_volume": {
 246 |                 "label": "Social Volume",
 247 |                 "score": social_score,
 248 |                 "delta": social_delta,
 249 |                 "detail": f"{social_1h} signals/hr",
 250 |                 "weight": 15,
 251 |             },
 252 |             "fear_greed": {
 253 |                 "label": "Fear & Greed",
 254 |                 "score": fng_score,
 255 |                 "delta": fng_delta,
 256 |                 "detail": fng_label,
 257 |                 "weight": 10,
 258 |             },
 259 |         },
 260 |         "computed_at": now.isoformat() + "Z",
 261 |     }
 262 | 
 263 | 
 264 | # ── Sentiment Heatmap Logic ────────────────────────────────────────────────
 265 | 
 266 | _HEATMAP_CATEGORIES = {
 267 |     "Mining": ["mining", "hashrate", "miner", "asic", "difficulty", "pool"],
 268 |     "Regulation": ["regulation", "regulatory", "sec", "etf", "law", "policy", "government", "ban", "legal"],
 269 |     "ETFs": ["etf", "blackrock", "fidelity", "spot", "fund", "institutional"],
 270 |     "Lightning": ["lightning", "ln", "channel", "payment", "l2", "layer 2"],
 271 |     "DeFi": ["defi", "defi", "wrapped", "taproot", "ordinals", "runes"],
 272 |     "Macro": ["macro", "inflation", "fed", "interest rate", "economy", "dollar", "usd", "gold", "gdp"],
 273 | }
 274 | 
 275 | 
 276 | def _compute_heatmap():
 277 |     """Return category sentiment grid from articles in last 2h."""
 278 |     from app import db
 279 |     from models import Article
 280 | 
 281 |     cutoff_2h = _utcnow() - timedelta(hours=2)
 282 |     cutoff_24h = _utcnow() - timedelta(hours=24)
 283 | 
 284 |     try:
 285 |         recent = (
 286 |             Article.query
 287 |             .filter(Article.published == True, Article.created_at >= cutoff_24h)
 288 |             .with_entities(
 289 |                 Article.category,
 290 |                 Article.tags,
 291 |                 Article.created_at,
 292 |             )
 293 |             .order_by(Article.created_at.desc())
 294 |             .limit(500)
 295 |             .all()
 296 |         )
 297 |     except Exception as exc:
 298 |         log.warning("heatmap query failed: %s", exc)
 299 |         recent = []
 300 | 
 301 |     # Bucket articles into categories
 302 |     buckets = {cat: {"count_2h": 0, "count_24h": 0} for cat in _HEATMAP_CATEGORIES}
 303 | 
 304 |     for row in recent:
 305 |         text = " ".join([
 306 |             (row.category or "").lower(),
 307 |             (row.tags or "").lower(),
 308 |         ])
 309 |         is_2h = row.created_at >= cutoff_2h if row.created_at else False
 310 |         for cat, keywords in _HEATMAP_CATEGORIES.items():
 311 |             if any(kw in text for kw in keywords):
 312 |                 buckets[cat]["count_24h"] += 1
 313 |                 if is_2h:
 314 |                     buckets[cat]["count_2h"] += 1
 315 | 
 316 |     # Build response cells
 317 |     cells = []
 318 |     for cat, data in buckets.items():
 319 |         count = data["count_2h"]
 320 |         count_24h = data["count_24h"]
 321 |         # Simple sentiment proxy: more articles = more coverage = higher buzz
 322 |         # Score from 0-100 based on coverage vs average
 323 |         avg_24h = max(sum(v["count_24h"] for v in buckets.values()) / len(buckets), 1)
 324 |         raw_score = min((count_24h / avg_24h) * 50, 100)
 325 |         score = round(raw_score)
 326 |         cells.append({
 327 |             "category": cat,
 328 |             "count_2h": count,
 329 |             "count_24h": count_24h,
 330 |             "score": score,
 331 |             "label": _sentiment_label(score),
 332 |             "color": _sentiment_color(score),
 333 |         })
 334 | 
 335 |     return {"cells": cells, "computed_at": _utcnow().isoformat() + "Z"}
 336 | 
 337 | 
 338 | # ── Source Health Logic ────────────────────────────────────────────────────
 339 | 
 340 | _KEY_SOURCES = [
 341 |     "Bitcoin Magazine", "CoinDesk", "Cointelegraph", "Decrypt",
 342 |     "The Block", "Blockworks", "Bitcoin.com", "Newsbtc",
 343 |     "Ambcrypto", "Bitcoinist", "CryptoSlate", "99Bitcoins",
 344 | ]
 345 | 
 346 | 
 347 | def _compute_source_health():
 348 |     """Return health status for key article sources."""
 349 |     from app import db
 350 |     from models import Article
 351 |     from sqlalchemy import func
 352 | 
 353 |     try:
 354 |         now = _utcnow()
 355 |         rows = (
 356 |             Article.query
 357 |             .filter(Article.published == True)
 358 |             .with_entities(
 359 |                 Article.author,
 360 |                 func.count(Article.id).label("total"),
 361 |                 func.max(Article.created_at).label("last_at"),
 362 |                 func.sum(
 363 |                     db.case(
 364 |                         (Article.created_at >= now - timedelta(hours=24), 1),
 365 |                         else_=0,
 366 |                     )
 367 |                 ).label("today"),
 368 |             )
 369 |             .group_by(Article.author)
 370 |             .order_by(func.count(Article.id).desc())
 371 |             .limit(30)
 372 |             .all()
 373 |         )
 374 |     except Exception as exc:
 375 |         log.warning("source health query failed: %s", exc)
 376 |         rows = []
 377 | 
 378 |     now = _utcnow()
 379 |     sources = []
 380 |     for row in rows:
 381 |         if not row.author or row.author in ("Protocol Pulse AI", ""):
 382 |             continue
 383 |         last_at = row.last_at
 384 |         if last_at is None:
 385 |             continue
 386 |         age_hours = (now - last_at).total_seconds() / 3600
 387 |         if age_hours < 1:
 388 |             status = "green"
 389 |             status_label = "LIVE"
 390 |         elif age_hours < 6:
 391 |             status = "amber"
 392 |             status_label = "RECENT"
 393 |         elif age_hours < 24:
 394 |             status = "red"
 395 |             status_label = "STALE"
 396 |         else:
 397 |             status = "red"
 398 |             status_label = "OFFLINE"
 399 | 
 400 |         sources.append({
 401 |             "name": row.author[:30],
 402 |             "last_scraped": last_at.isoformat() + "Z",
 403 |             "articles_today": int(row.today or 0),
 404 |             "total": int(row.total or 0),
 405 |             "status": status,
 406 |             "status_label": status_label,
 407 |             "age_hours": round(age_hours, 1),
 408 |         })
 409 |         if len(sources) >= 12:
 410 |             break
 411 | 
 412 |     return {"sources": sources, "computed_at": _utcnow().isoformat() + "Z"}
 413 | 
 414 | 
 415 | # ── Intelligence Feed Logic ────────────────────────────────────────────────
 416 | 
 417 | def _get_intelligence_feed(limit=20):
 418 |     """Latest articles with sentiment badges."""
 419 |     from app import db
 420 |     from models import Article
 421 |     from sqlalchemy import text as _sa_text
 422 | 
 423 |     try:
 424 |         # Use with_entities to select only columns we know exist (avoids schema mismatch on older DBs)
 425 |         articles = (
 426 |             Article.query
 427 |             .filter(Article.published == True)
 428 |             .with_entities(
 429 |                 Article.id,
 430 |                 Article.title,
 431 |                 Article.summary,
 432 |                 Article.author,
 433 |                 Article.category,
 434 |                 Article.tags,
 435 |                 Article.created_at,
 436 |             )
 437 |             .order_by(Article.created_at.desc())
 438 |             .limit(limit)
 439 |             .all()
 440 |         )
 441 |     except Exception as exc:
 442 |         log.warning("intelligence feed query failed: %s", exc)
 443 |         return {"items": [], "computed_at": _utcnow().isoformat() + "Z"}
 444 | 
 445 |     items = []
 446 |     bullish_words = ["bull", "surge", "rally", "growth", "adoption", "all-time", "record", "approved", "launch"]
 447 |     bearish_words = ["bear", "crash", "drop", "ban", "hack", "attack", "decline", "loss", "fail"]
 448 |     for a in articles:
 449 |         # with_entities returns named tuples
 450 |         aid = a.id
 451 |         title = a.title or ""
 452 |         summary = (a.summary or "")[:200]
 453 |         author = a.author or "Protocol Pulse"
 454 |         category = a.category or "News"
 455 |         tags = a.tags or ""
 456 |         created_at = a.created_at
 457 | 
 458 |         text = " ".join([category.lower(), tags.lower(), title.lower()])
 459 |         bull_score = sum(1 for w in bullish_words if w in text)
 460 |         bear_score = sum(1 for w in bearish_words if w in text)
 461 |         if bull_score > bear_score:
 462 |             sentiment = "BULLISH"
 463 |             sentiment_color = "#22c55e"
 464 |         elif bear_score > bull_score:
 465 |             sentiment = "BEARISH"
 466 |             sentiment_color = "#ef4444"
 467 |         else:
 468 |             sentiment = "NEUTRAL"
 469 |             sentiment_color = "#f59e0b"
 470 | 
 471 |         items.append({
 472 |             "id": aid,
 473 |             "title": title,
 474 |             "summary": summary,
 475 |             "source": author,
 476 |             "category": category,
 477 |             "url": f"/article/{aid}",
 478 |             "timestamp": created_at.isoformat() + "Z" if created_at else None,
 479 |             "sentiment": sentiment,
 480 |             "sentiment_color": sentiment_color,
 481 |             "cover_image": "",
 482 |         })
 483 | 
 484 |     return {"items": items, "computed_at": _utcnow().isoformat() + "Z"}
 485 | 
 486 | 
 487 | # ── Live BTC Price (for health strip) ─────────────────────────────────────
 488 | 
 489 | def _fetch_btc_price():
 490 |     r = requests.get(
 491 |         "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
 492 |         timeout=5,
 493 |         headers={"User-Agent": "ProtocolPulse/3.0"},
 494 |     )
 495 |     r.raise_for_status()
 496 |     data = r.json()
 497 |     return {
 498 |         "price": data["bitcoin"]["usd"],
 499 |         "change_24h": round(data["bitcoin"].get("usd_24h_change", 0), 2),
 500 |     }
 501 | 
 502 | 
 503 | # ═══════════════════════════════════════════════════════════════════════════
 504 | #  ROUTES
 505 | # ═══════════════════════════════════════════════════════════════════════════
 506 | 
 507 | @media_bp.route("/media")
 508 | @media_bp.route("/media-unified")
 509 | def media_page():
 510 |     """Media Unified Intelligence page."""
 511 |     try:
 512 |         # SSR initial data so the page is meaningful before JS kicks in
 513 |         signal = _cached("signal_composite", 120, _compute_composite_signal)
 514 |         feed = _get_intelligence_feed(limit=10)
 515 |         return render_template(
 516 |             "media_unified.html",
 517 |             initial_signal=signal,
 518 |             initial_feed=feed,
 519 |         )
 520 |     except Exception as exc:
 521 |         log.error("media_page error: %s", exc, exc_info=True)
 522 |         return render_template(
 523 |             "media_unified.html",
 524 |             initial_signal=None,
 525 |             initial_feed=None,
 526 |         )
 527 | 
 528 | 
 529 | @media_bp.route("/api/signal/composite")
 530 | def api_signal_composite():
 531 |     """Weighted composite signal score. Cached 2min."""
 532 |     data = _cached("signal_composite", 120, _compute_composite_signal)
 533 |     if data is None:
 534 |         data = {
 535 |             "score": 50,
 536 |             "label": "MODERATE",
 537 |             "color": "#f59e0b",
 538 |             "components": {},
 539 |             "computed_at": _utcnow().isoformat() + "Z",
 540 |         }
 541 |     return jsonify(data)
 542 | 
 543 | 
 544 | @media_bp.route("/api/sentiment/heatmap")
 545 | def api_sentiment_heatmap():
 546 |     """Category sentiment heatmap from last 2h of articles."""
 547 |     data = _cached("sentiment_heatmap", 300, _compute_heatmap)
 548 |     if data is None:
 549 |         data = {"cells": [], "computed_at": _utcnow().isoformat() + "Z"}
 550 |     return jsonify(data)
 551 | 
 552 | 
 553 | @media_bp.route("/api/media/sources/health")
 554 | def api_media_sources_health():
 555 |     """Source health status grid."""
 556 |     data = _cached("sources_health", 300, _compute_source_health)
 557 |     if data is None:
 558 |         data = {"sources": [], "computed_at": _utcnow().isoformat() + "Z"}
 559 |     return jsonify(data)
 560 | 
 561 | 
 562 | @media_bp.route("/api/media/feed/intelligence")
 563 | def api_media_feed_intelligence():
 564 |     """Latest 20 PP articles with sentiment badges."""
 565 |     limit = min(int(request.args.get("limit", 20)), 50)
 566 |     data = _get_intelligence_feed(limit=limit)
 567 |     return jsonify(data)
 568 | 
 569 | 
 570 | @media_bp.route("/api/media/feed/stream")
 571 | def api_media_feed_stream():
 572 |     """
 573 |     Server-sent events for real-time intelligence feed.
 574 |     Polls DB every 30s for new articles and pushes them to the client.
 575 |     """
 576 |     def generate():
 577 |         from models import Article
 578 |         last_id = 0
 579 |         try:
 580 |             latest = Article.query.filter(Article.published == True).order_by(Article.id.desc()).first()
 581 |             if latest:
 582 |                 last_id = latest.id
 583 |         except Exception:
 584 |             pass
 585 | 
 586 |         # Send initial heartbeat
 587 |         yield "event: heartbeat\ndata: {}\n\n"
 588 | 
 589 |         while True:
 590 |             try:
 591 |                 new_articles = (
 592 |                     Article.query
 593 |                     .filter(Article.published == True, Article.id > last_id)
 594 |                     .with_entities(Article.id, Article.title, Article.author, Article.category, Article.tags, Article.created_at)
 595 |                     .order_by(Article.id.asc())
 596 |                     .limit(5)
 597 |                     .all()
 598 |                 )
 599 |                 _bw = ["bull", "surge", "rally", "growth", "adoption", "record", "approved"]
 600 |                 _be = ["bear", "crash", "drop", "ban", "hack", "decline", "loss"]
 601 |                 for a in new_articles:
 602 |                     last_id = a.id
 603 |                     text = " ".join([(a.category or "").lower(), (a.tags or "").lower(), (a.title or "").lower()])
 604 |                     bs = sum(1 for w in _bw if w in text)
 605 |                     es = sum(1 for w in _be if w in text)
 606 |                     sentiment = "BULLISH" if bs > es else ("BEARISH" if es > bs else "NEUTRAL")
 607 |                     item = {
 608 |                         "id": a.id,
 609 |                         "title": a.title,
 610 |                         "source": a.author or "Protocol Pulse",
 611 |                         "category": a.category or "News",
 612 |                         "url": f"/article/{a.id}",
 613 |                         "timestamp": a.created_at.isoformat() + "Z" if a.created_at else None,
 614 |                         "sentiment": sentiment,
 615 |                     }
 616 |                     yield f"event: article\ndata: {json.dumps(item)}\n\n"
 617 |             except Exception as exc:
 618 |                 log.warning("SSE stream error: %s", exc)
 619 |                 yield f"event: error\ndata: {json.dumps({'msg': 'stream error'})}\n\n"
 620 | 
 621 |             # Heartbeat every 30s
 622 |             time.sleep(30)
 623 |             yield "event: heartbeat\ndata: {}\n\n"
 624 | 
 625 |     return Response(
 626 |         stream_with_context(generate()),
 627 |         mimetype="text/event-stream",
 628 |         headers={
 629 |             "Cache-Control": "no-cache",
 630 |             "X-Accel-Buffering": "no",
 631 |         },
 632 |     )
 633 | 
```

### File: core/blueprints/node_watch.py (493 lines)
```
   1 | """
   2 | SESSION 9 — NODE WATCH
   3 | Blueprint: node_watch_bp
   4 | Routes:
   5 |   GET /node-watch                 — page
   6 |   GET /api/nodes/summary          — reachable/total/IPv4/IPv6/Tor/I2P + health score (cache 5min)
   7 |   GET /api/nodes/countries        — top 15 countries with % (cache 1h)
   8 |   GET /api/nodes/versions         — version distribution (cache 1h)
   9 |   GET /api/nodes/history          — node count over time (cache 24h)
  10 | 
  11 | Data strategy:
  12 |   - Bitnodes /api/v1/snapshots/ → total node count + snapshot URL
  13 |   - Bitnodes snapshot detail URL → full node data (country/version/network type)
  14 |   - ONE shared raw-snapshot cache avoids repeated API hits (cache 1h for detail)
  15 |   - History: /api/v1/snapshots/?limit=100 (each ~2h apart ≈ 200 days)
  16 |   - Rate-limit safeguard: all endpoints degrade gracefully to stale or empty state
  17 | """
  18 | 
  19 | import logging
  20 | import re
  21 | import time
  22 | from typing import Optional
  23 | 
  24 | import requests
  25 | from flask import Blueprint, jsonify, make_response, render_template
  26 | 
  27 | node_watch_bp = Blueprint("node_watch", __name__)
  28 | log = logging.getLogger(__name__)
  29 | 
  30 | BITNODES_BASE = "https://bitnodes.io/api/v1"
  31 | _HEADERS = {
  32 |     "Accept": "application/json",
  33 |     "User-Agent": "ProtocolPulse/1.0 (bitcoin-network-monitor)",
  34 | }
  35 | _TIMEOUT = 12  # seconds
  36 | 
  37 | # ---------------------------------------------------------------------------
  38 | # Shared raw-data cache — ONE fetch populates all derived endpoints
  39 | # ---------------------------------------------------------------------------
  40 | _raw: dict = {
  41 |     # Snapshot list: total count + snapshot URL + previous count
  42 |     "list": {"data": None, "expires": 0.0},
  43 |     # Full node detail: parsed per-node data (versions, countries, net types)
  44 |     "detail": {"data": None, "expires": 0.0},
  45 |     # History: [{ts, count}, ...]
  46 |     "history": {"data": None, "expires": 0.0},
  47 | }
  48 | 
  49 | _TTL_LIST   = 5 * 60        # 5 min — refreshes the total count
  50 | _TTL_DETAIL = 60 * 60       # 1 h  — per-node breakdown
  51 | _TTL_HISTORY = 24 * 60 * 60 # 24 h
  52 | 
  53 | 
  54 | # ---------------------------------------------------------------------------
  55 | # Country meta
  56 | # ---------------------------------------------------------------------------
  57 | _CC_NAMES: dict[str, str] = {
  58 |     "US": "United States", "DE": "Germany",    "FR": "France",
  59 |     "NL": "Netherlands",   "CA": "Canada",     "GB": "United Kingdom",
  60 |     "JP": "Japan",         "AU": "Australia",  "SG": "Singapore",
  61 |     "RU": "Russia",        "CH": "Switzerland","FI": "Finland",
  62 |     "SE": "Sweden",        "HK": "Hong Kong",  "CN": "China",
  63 |     "AT": "Austria",       "BR": "Brazil",     "NO": "Norway",
  64 |     "IT": "Italy",         "ES": "Spain",      "PL": "Poland",
  65 |     "CZ": "Czech Republic","RO": "Romania",    "IN": "India",
  66 |     "KR": "South Korea",   "NZ": "New Zealand","BE": "Belgium",
  67 |     "AR": "Argentina",     "MX": "Mexico",     "UA": "Ukraine",
  68 |     "ZA": "South Africa",  "TR": "Turkey",     "TW": "Taiwan",
  69 |     "IL": "Israel",        "IR": "Iran",       "ID": "Indonesia",
  70 |     "PT": "Portugal",      "DK": "Denmark",    "HU": "Hungary",
  71 |     "??": "Unknown",
  72 | }
  73 | 
  74 | CC_COORDS: dict[str, list] = {
  75 |     "US": [37.09, -95.71],   "DE": [51.17, 10.45],   "FR": [46.23, 2.21],
  76 |     "NL": [52.13, 5.29],     "CA": [56.13, -106.35], "GB": [55.38, -3.44],
  77 |     "JP": [36.20, 138.25],   "AU": [-25.27, 133.78], "SG": [1.35, 103.82],
  78 |     "RU": [61.52, 105.32],   "CH": [46.82, 8.23],    "FI": [61.92, 25.75],
  79 |     "SE": [60.13, 18.64],    "HK": [22.30, 114.18],  "CN": [35.86, 104.20],
  80 |     "AT": [47.52, 14.55],    "BR": [-14.24, -51.93], "NO": [60.47, 8.47],
  81 |     "IT": [41.87, 12.57],    "ES": [40.46, -3.75],   "PL": [51.92, 19.15],
  82 |     "CZ": [49.82, 15.47],    "RO": [45.94, 24.97],   "IN": [20.59, 78.96],
  83 |     "KR": [35.91, 127.77],   "NZ": [-40.90, 174.89], "BE": [50.50, 4.47],
  84 |     "AR": [-38.42, -63.62],  "MX": [23.63, -102.55], "UA": [48.38, 31.17],
  85 |     "ZA": [-30.56, 22.94],   "TR": [38.96, 35.24],   "TW": [23.70, 121.00],
  86 |     "IL": [31.05, 34.85],    "IR": [32.43, 53.69],   "ID": [-0.79, 113.92],
  87 |     "PT": [39.40, -8.22],    "DK": [56.26, 9.50],    "HU": [47.16, 19.50],
  88 | }
  89 | 
  90 | 
  91 | # ---------------------------------------------------------------------------
  92 | # Internal fetchers
  93 | # ---------------------------------------------------------------------------
  94 | 
  95 | def _get(url: str) -> Optional[dict]:
  96 |     """GET → parsed JSON or None.  Never raises."""
  97 |     try:
  98 |         r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
  99 |         if r.status_code == 429:
 100 |             log.warning("Bitnodes rate-limited (429) for %s — using stale cache", url)
 101 |             return None
 102 |         r.raise_for_status()
 103 |         return r.json()
 104 |     except Exception as exc:
 105 |         log.warning("Bitnodes fetch error %s: %s", url, exc)
 106 |         return None
 107 | 
 108 | 
 109 | def _classify_addr(addr: str) -> str:
 110 |     if ".onion" in addr:
 111 |         return "tor"
 112 |     if ".i2p" in addr:
 113 |         return "i2p"
 114 |     if addr.startswith("["):
 115 |         return "ipv6"
 116 |     return "ipv4"
 117 | 
 118 | 
 119 | def _norm_agent(raw_agent: str) -> str:
 120 |     """'/Satoshi:28.0.0/' → 'Bitcoin Core 28.0.0'"""
 121 |     m = re.search(r"Satoshi:([\d.]+)", raw_agent or "")
 122 |     if m:
 123 |         return f"Bitcoin Core {m.group(1)}"
 124 |     if not raw_agent or raw_agent == "/unknown/":
 125 |         return "Unknown"
 126 |     # Truncate and clean other agents
 127 |     clean = (raw_agent or "").strip("/").replace("/", " ").strip()
 128 |     return clean[:45] if clean else "Unknown"
 129 | 
 130 | 
 131 | # ---------------------------------------------------------------------------
 132 | # Step 1: Fetch snapshot list (fast, just counts + snapshot URL)
 133 | # ---------------------------------------------------------------------------
 134 | 
 135 | def _fetch_list() -> Optional[dict]:
 136 |     """
 137 |     Returns:
 138 |       {total: int, prev_total: int, timestamp: int, snapshot_url: str}
 139 |     or None on failure.
 140 |     """
 141 |     now = time.time()
 142 |     c = _raw["list"]
 143 |     if c["data"] and now < c["expires"]:
 144 |         return c["data"]
 145 | 
 146 |     raw = _get(f"{BITNODES_BASE}/snapshots/?limit=2")
 147 |     if not raw:
 148 |         return c["data"]  # return stale or None
 149 | 
 150 |     results = raw.get("results", [])
 151 |     if not results:
 152 |         return c["data"]
 153 | 
 154 |     r0 = results[0]
 155 |     r1 = results[1] if len(results) > 1 else {}
 156 | 
 157 |     parsed = {
 158 |         "total":        r0.get("total_nodes") or 0,
 159 |         "prev_total":   r1.get("total_nodes") or 0,
 160 |         "timestamp":    r0.get("timestamp"),
 161 |         "snapshot_url": r0.get("url", ""),
 162 |     }
 163 |     c["data"]    = parsed
 164 |     c["expires"] = now + _TTL_LIST
 165 |     return parsed
 166 | 
 167 | 
 168 | # ---------------------------------------------------------------------------
 169 | # Step 2: Fetch snapshot detail (slow, but cached 1h)
 170 | # Bitnodes snapshot detail URL contains the full {nodes: {addr: [info]}} blob.
 171 | # ---------------------------------------------------------------------------
 172 | 
 173 | def _fetch_detail(snapshot_url: str) -> Optional[dict]:
 174 |     """
 175 |     Fetch the full node-level detail from a snapshot URL.
 176 |     Returns parsed dict: {versions, countries, net} or None.
 177 |     """
 178 |     now = time.time()
 179 |     c = _raw["detail"]
 180 |     if c["data"] and now < c["expires"]:
 181 |         return c["data"]
 182 | 
 183 |     if not snapshot_url:
 184 |         return c["data"]
 185 | 
 186 |     raw = _get(snapshot_url)
 187 |     if not raw:
 188 |         return c["data"]
 189 | 
 190 |     nodes: dict = raw.get("nodes", {})
 191 |     if not nodes:
 192 |         log.info("Bitnodes snapshot has no node-level data at %s", snapshot_url)
 193 |         return c["data"]
 194 | 
 195 |     versions: dict[str, int] = {}
 196 |     countries: dict[str, int] = {}
 197 |     net: dict[str, int] = {"ipv4": 0, "ipv6": 0, "tor": 0, "i2p": 0}
 198 | 
 199 |     for addr, info in nodes.items():
 200 |         if not isinstance(info, list):
 201 |             continue
 202 |         # Network type
 203 |         n = _classify_addr(addr)
 204 |         net[n] = net.get(n, 0) + 1
 205 |         # Version agent (index 1)
 206 |         agent = info[1] if len(info) > 1 else ""
 207 |         label = _norm_agent(agent)
 208 |         versions[label] = versions.get(label, 0) + 1
 209 |         # Country (index 7)
 210 |         cc = (info[7] or "??") if len(info) > 7 else "??"
 211 |         countries[cc] = countries.get(cc, 0) + 1
 212 | 
 213 |     top_ver = sorted(versions.items(),  key=lambda x: x[1], reverse=True)[:15]
 214 |     top_cc  = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:15]
 215 | 
 216 |     parsed = {"versions": top_ver, "countries": top_cc, "net": net}
 217 |     c["data"]    = parsed
 218 |     c["expires"] = now + _TTL_DETAIL
 219 |     return parsed
 220 | 
 221 | 
 222 | # ---------------------------------------------------------------------------
 223 | # Step 3: History
 224 | # ---------------------------------------------------------------------------
 225 | 
 226 | def _fetch_history() -> list:
 227 |     now = time.time()
 228 |     c = _raw["history"]
 229 |     if c["data"] and now < c["expires"]:
 230 |         return c["data"]
 231 | 
 232 |     # 100 snapshots ≈ 200 days at ~2h interval
 233 |     raw = _get(f"{BITNODES_BASE}/snapshots/?limit=100")
 234 |     if not raw:
 235 |         return c["data"] or []
 236 | 
 237 |     pts = []
 238 |     for snap in reversed(raw.get("results", [])):  # oldest → newest
 239 |         ts  = snap.get("timestamp")
 240 |         cnt = snap.get("total_nodes")
 241 |         if ts and cnt:
 242 |             pts.append({"ts": ts, "count": cnt})
 243 | 
 244 |     c["data"]    = pts
 245 |     c["expires"] = now + _TTL_HISTORY
 246 |     return pts
 247 | 
 248 | 
 249 | # ---------------------------------------------------------------------------
 250 | # Health Score
 251 | # ---------------------------------------------------------------------------
 252 | 
 253 | def _health_score(total: int, delta: int, detail: Optional[dict]) -> dict:
 254 |     # 1. Node level (15 pts)
 255 |     node_pts = (15 if total >= 16000 else 12 if total >= 13000
 256 |                 else 8 if total >= 10000 else 4 if total >= 7000 else 0)
 257 | 
 258 |     # 2. Growth (20 pts)
 259 |     growth_pts = (20 if delta > 200 else 15 if delta > 0
 260 |                   else 10 if delta > -100 else 5 if delta > -500 else 0)
 261 | 
 262 |     # 3. Version currency (25 pts)
 263 |     ver_pts = 2
 264 |     currency_pct = 0.0
 265 |     if detail and detail.get("versions") and total:
 266 |         current = sum(c for v, c in detail["versions"]
 267 |                       if "Core 28." in v or "Core 27." in v or "Core 26." in v)
 268 |         currency_pct = current / total * 100
 269 |         ver_pts = (25 if currency_pct >= 60 else 18 if currency_pct >= 40
 270 |                    else 12 if currency_pct >= 20 else 6 if currency_pct >= 10 else 2)
 271 | 
 272 |     # 4. Geo diversity (20 pts)
 273 |     geo_pts = 10  # default moderate
 274 |     top_cc_pct = 0.0
 275 |     if detail and detail.get("countries") and total:
 276 |         top_cc_pct = detail["countries"][0][1] / total * 100
 277 |         geo_pts = (20 if top_cc_pct < 20 else 17 if top_cc_pct < 25
 278 |                    else 12 if top_cc_pct < 35 else 6 if top_cc_pct < 50 else 2)
 279 | 
 280 |     # 5. Privacy (10 pts)
 281 |     priv_pts = 3
 282 |     if detail and detail.get("net") and total:
 283 |         priv = detail["net"].get("tor", 0) + detail["net"].get("i2p", 0)
 284 |         priv_pct = priv / total * 100
 285 |         priv_pts = (10 if priv_pct >= 15 else 7 if priv_pct >= 8
 286 |                     else 5 if priv_pct >= 4 else 3 if priv_pct >= 1 else 1)
 287 | 
 288 |     # 6. Freshness (10 pts)
 289 |     fresh_pts = 10  # we just fetched it
 290 | 
 291 |     score = min(100, max(0, node_pts + growth_pts + ver_pts + geo_pts + priv_pts + fresh_pts))
 292 | 
 293 |     if score >= 75:
 294 |         label, colour = "STRONG", "#22c55e"
 295 |     elif score >= 45:
 296 |         label, colour = "MODERATE", "#f59e0b"
 297 |     else:
 298 |         label, colour = "WEAK", "#dc2626"
 299 | 
 300 |     # One-sentence reason
 301 |     if score >= 75:
 302 |         reason = f"Network running strong with {total:,} reachable nodes and healthy decentralisation."
 303 |     elif geo_pts < 10:
 304 |         reason = f"Geographic concentration: top country holds {top_cc_pct:.0f}% of reachable nodes."
 305 |     elif ver_pts < 10:
 306 |         reason = f"Version diversity gap: only {currency_pct:.0f}% of nodes on current major release."
 307 |     elif node_pts < 8:
 308 |         reason = f"Node count below typical level at {total:,} reachable nodes."
 309 |     elif detail is None:
 310 |         reason = f"Network stable with {total:,} reachable nodes. Detailed breakdown loading."
 311 |     else:
 312 |         reason = f"Network stable — {total:,} reachable nodes with moderate geographic spread."
 313 | 
 314 |     return {
 315 |         "score":  score,
 316 |         "label":  label,
 317 |         "colour": colour,
 318 |         "reason": reason,
 319 |         "components": {
 320 |             "node_level":       node_pts,
 321 |             "growth_trend":     growth_pts,
 322 |             "version_currency": ver_pts,
 323 |             "geo_diversity":    geo_pts,
 324 |             "privacy_nodes":    priv_pts,
 325 |             "data_freshness":   fresh_pts,
 326 |         },
 327 |     }
 328 | 
 329 | 
 330 | # ---------------------------------------------------------------------------
 331 | # Page route
 332 | # ---------------------------------------------------------------------------
 333 | 
 334 | @node_watch_bp.route("/node-watch")
 335 | def node_watch_page():
 336 |     return render_template("node_watch.html")
 337 | 
 338 | 
 339 | # ---------------------------------------------------------------------------
 340 | # API — summary
 341 | # ---------------------------------------------------------------------------
 342 | 
 343 | @node_watch_bp.route("/api/nodes/summary")
 344 | def api_nodes_summary():
 345 |     """
 346 |     Reachable count, IPv4/IPv6/Tor/I2P, 24h delta, Network Health Score.
 347 |     Cache: 5 min.
 348 |     """
 349 |     try:
 350 |         lst = _fetch_list()
 351 |         if not lst:
 352 |             stale = _raw["list"].get("data") or {}
 353 |             return jsonify({**stale, "stale": True, "error": "Bitnodes unavailable"}), 200
 354 | 
 355 |         total      = lst["total"]
 356 |         prev_total = lst["prev_total"]
 357 |         delta      = total - prev_total if prev_total else 0
 358 |         ts         = lst["timestamp"]
 359 | 
 360 |         # Try to get network-type breakdown from detail (may be None if rate-limited)
 361 |         detail = None
 362 |         snap_url = lst.get("snapshot_url")
 363 |         if snap_url:
 364 |             detail = _fetch_detail(snap_url)
 365 | 
 366 |         net = detail.get("net", {}) if detail else {}
 367 |         health = _health_score(total, delta, detail)
 368 | 
 369 |         data = {
 370 |             "reachable":    total,
 371 |             "ipv4":         net.get("ipv4", 0),
 372 |             "ipv6":         net.get("ipv6", 0),
 373 |             "tor":          net.get("tor",  0),
 374 |             "i2p":          net.get("i2p",  0),
 375 |             "timestamp":    ts,
 376 |             "delta_24h":    delta,
 377 |             "health":       health,
 378 |             "stale":        False,
 379 |             "detail_ready": detail is not None,
 380 |         }
 381 |     except Exception as exc:
 382 |         log.exception("api_nodes_summary error: %s", exc)
 383 |         data = {"error": str(exc), "stale": True, "reachable": 0, "delta_24h": 0}
 384 | 
 385 |     resp = make_response(jsonify(data))
 386 |     resp.headers["Cache-Control"] = "public, max-age=300"
 387 |     return resp
 388 | 
 389 | 
 390 | # ---------------------------------------------------------------------------
 391 | # API — countries
 392 | # ---------------------------------------------------------------------------
 393 | 
 394 | @node_watch_bp.route("/api/nodes/countries")
 395 | def api_nodes_countries():
 396 |     """Top 15 countries by node count. Cache: 1 h."""
 397 |     try:
 398 |         lst    = _fetch_list()
 399 |         detail = None
 400 |         if lst and lst.get("snapshot_url"):
 401 |             detail = _fetch_detail(lst["snapshot_url"])
 402 | 
 403 |         total = (lst["total"] if lst else 0) or 1
 404 | 
 405 |         if not detail or not detail.get("countries"):
 406 |             stale = _raw["detail"].get("data") or {}
 407 |             return jsonify({
 408 |                 "countries": [], "total": total,
 409 |                 "stale": True,
 410 |                 "note": "Country breakdown not yet available — Bitnodes rate-limit or loading."
 411 |             }), 200
 412 | 
 413 |         rows = []
 414 |         for cc, cnt in detail["countries"]:
 415 |             coords = CC_COORDS.get(cc)
 416 |             rows.append({
 417 |                 "cc":   cc,
 418 |                 "name": _CC_NAMES.get(cc, cc),
 419 |                 "count": cnt,
 420 |                 "pct":  round(cnt / total * 100, 1),
 421 |                 "lat":  coords[0] if coords else None,
 422 |                 "lng":  coords[1] if coords else None,
 423 |             })
 424 | 
 425 |         data = {"countries": rows, "total": total, "stale": False}
 426 |     except Exception as exc:
 427 |         log.exception("api_nodes_countries error: %s", exc)
 428 |         data = {"error": str(exc), "stale": True, "countries": []}
 429 | 
 430 |     resp = make_response(jsonify(data))
 431 |     resp.headers["Cache-Control"] = "public, max-age=3600"
 432 |     return resp
 433 | 
 434 | 
 435 | # ---------------------------------------------------------------------------
 436 | # API — versions
 437 | # ---------------------------------------------------------------------------
 438 | 
 439 | @node_watch_bp.route("/api/nodes/versions")
 440 | def api_nodes_versions():
 441 |     """Version distribution. Cache: 1 h."""
 442 |     try:
 443 |         lst    = _fetch_list()
 444 |         detail = None
 445 |         if lst and lst.get("snapshot_url"):
 446 |             detail = _fetch_detail(lst["snapshot_url"])
 447 | 
 448 |         total = (lst["total"] if lst else 0) or 1
 449 | 
 450 |         if not detail or not detail.get("versions"):
 451 |             return jsonify({
 452 |                 "versions": [], "total": total,
 453 |                 "stale": True,
 454 |                 "note": "Version breakdown not yet available — Bitnodes rate-limit or loading."
 455 |             }), 200
 456 | 
 457 |         rows = []
 458 |         for ver, cnt in detail["versions"]:
 459 |             rows.append({
 460 |                 "version": ver,
 461 |                 "count":   cnt,
 462 |                 "pct":     round(cnt / total * 100, 1),
 463 |                 "current": ("28." in ver or "27." in ver or "26." in ver),
 464 |             })
 465 | 
 466 |         data = {"versions": rows, "total": total, "stale": False}
 467 |     except Exception as exc:
 468 |         log.exception("api_nodes_versions error: %s", exc)
 469 |         data = {"error": str(exc), "stale": True, "versions": []}
 470 | 
 471 |     resp = make_response(jsonify(data))
 472 |     resp.headers["Cache-Control"] = "public, max-age=3600"
 473 |     return resp
 474 | 
 475 | 
 476 | # ---------------------------------------------------------------------------
 477 | # API — history
 478 | # ---------------------------------------------------------------------------
 479 | 
 480 | @node_watch_bp.route("/api/nodes/history")
 481 | def api_nodes_history():
 482 |     """Node count history (~200 days). Cache: 24 h."""
 483 |     try:
 484 |         pts = _fetch_history()
 485 |         data = {"history": pts, "stale": not pts}
 486 |     except Exception as exc:
 487 |         log.exception("api_nodes_history error: %s", exc)
 488 |         data = {"error": str(exc), "stale": True, "history": []}
 489 | 
 490 |     resp = make_response(jsonify(data))
 491 |     resp.headers["Cache-Control"] = "public, max-age=86400"
 492 |     return resp
 493 | 
```

### File: core/blueprints/oracle_avatar.py (380 lines)
```
   1 | """
   2 | SESSION 7 — ORACLE AVATAR
   3 | Blueprint: oracle_avatar_bp
   4 | 
   5 | Routes:
   6 |   GET  /oracle-live                — page (hero video, schedule, archive, status sidebar)
   7 |   GET  /api/oracle/briefings       — today + last 7 days briefings list
   8 |   GET  /api/oracle/status          — system health, next scheduled, last generated
   9 |   POST /api/oracle/generate        — manual trigger (admin only, IP-gated)
  10 | """
  11 | 
  12 | from __future__ import annotations
  13 | 
  14 | import logging
  15 | import os
  16 | import time
  17 | from datetime import datetime, timedelta, date
  18 | from pathlib import Path
  19 | 
  20 | import pytz
  21 | import requests
  22 | from flask import Blueprint, jsonify, render_template, request, abort
  23 | 
  24 | logger = logging.getLogger(__name__)
  25 | 
  26 | ET = pytz.timezone("America/New_York")
  27 | 
  28 | BRIEFING_SLOTS = {
  29 |     "pre_market": {
  30 |         "label":       "Pre-Market Briefing",
  31 |         "time_et":     "7:45 AM ET",
  32 |         "time_utc":    "12:45 UTC",
  33 |         "description": "Overnight BTC moves, Asian session wrap, key levels for the day",
  34 |         "publish_hour_et": 8,   # 08:00 ET publish time
  35 |     },
  36 |     "open": {
  37 |         "label":       "Market Open Briefing",
  38 |         "time_et":     "12:00 PM ET",
  39 |         "time_utc":    "17:00 UTC",
  40 |         "description": "Mid-session update — mempool status, fee market, notable developments",
  41 |         "publish_hour_et": 12,
  42 |     },
  43 |     "close": {
  44 |         "label":       "Daily Close Briefing",
  45 |         "time_et":     "5:00 PM ET",
  46 |         "time_utc":    "22:00 UTC",
  47 |         "description": "Day summary, Signal score, tomorrow's outlook",
  48 |         "publish_hour_et": 17,
  49 |     },
  50 | }
  51 | 
  52 | # Ultron LAN / cloudflare tunnel IPs allowed for admin trigger
  53 | ADMIN_ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}
  54 | ADMIN_TOKEN = os.environ.get("ORACLE_ADMIN_TOKEN", "")
  55 | 
  56 | oracle_avatar_bp = Blueprint("oracle_avatar", __name__)
  57 | 
  58 | 
  59 | # ---------------------------------------------------------------------------
  60 | # Helpers
  61 | # ---------------------------------------------------------------------------
  62 | 
  63 | def _get_et_now() -> datetime:
  64 |     return datetime.now(ET)
  65 | 
  66 | 
  67 | def _et_date_str(dt: datetime | None = None) -> str:
  68 |     d = dt or _get_et_now()
  69 |     return d.strftime("%Y-%m-%d")
  70 | 
  71 | 
  72 | def _load_env_keys():
  73 |     """Load root .env keys not present in core/.env."""
  74 |     root_env = Path(__file__).resolve().parent.parent.parent / ".env"
  75 |     if root_env.exists() and not os.environ.get("HEYGEN_API_KEY"):
  76 |         for line in root_env.read_text().splitlines():
  77 |             line = line.strip()
  78 |             if line and not line.startswith("#") and "=" in line:
  79 |                 k, v = line.split("=", 1)
  80 |                 os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
  81 | 
  82 | 
  83 | def _live_btc_price() -> float | None:
  84 |     try:
  85 |         r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
  86 |         if r.status_code == 200:
  87 |             price = r.json().get("USD")
  88 |             if price:
  89 |                 return float(price)
  90 |     except Exception:
  91 |         pass
  92 |     try:
  93 |         r = requests.get(
  94 |             "https://api.coingecko.com/api/v3/simple/price",
  95 |             params={"ids": "bitcoin", "vs_currencies": "usd"},
  96 |             timeout=5,
  97 |         )
  98 |         if r.status_code == 200:
  99 |             return float(r.json().get("bitcoin", {}).get("usd", 0)) or None
 100 |     except Exception:
 101 |         pass
 102 |     return None
 103 | 
 104 | 
 105 | def _live_fear_greed() -> dict:
 106 |     try:
 107 |         r = requests.get("https://api.alternative.me/fng/", timeout=5)
 108 |         if r.status_code == 200:
 109 |             fng = r.json().get("data", [{}])[0]
 110 |             return {"value": fng.get("value"), "label": fng.get("value_classification")}
 111 |     except Exception:
 112 |         pass
 113 |     return {"value": None, "label": "Unavailable"}
 114 | 
 115 | 
 116 | def _heygen_api_ok() -> bool:
 117 |     key = os.environ.get("HEYGEN_API_KEY", "")
 118 |     return bool(key and len(key) > 10)
 119 | 
 120 | 
 121 | def _elevenlabs_api_ok() -> bool:
 122 |     key = os.environ.get("ELEVENLABS_API_KEY", "")
 123 |     return bool(key and len(key) > 10)
 124 | 
 125 | 
 126 | def _anthropic_api_ok() -> bool:
 127 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
 128 |     return bool(key and len(key) > 10)
 129 | 
 130 | 
 131 | def _next_scheduled_briefing() -> dict:
 132 |     """Return info about the next upcoming briefing slot."""
 133 |     now_et = _get_et_now()
 134 |     for slot_type, slot in BRIEFING_SLOTS.items():
 135 |         slot_time = now_et.replace(
 136 |             hour=slot["publish_hour_et"],
 137 |             minute=0,
 138 |             second=0,
 139 |             microsecond=0,
 140 |         )
 141 |         if slot_time > now_et:
 142 |             diff = slot_time - now_et
 143 |             hours, rem = divmod(int(diff.total_seconds()), 3600)
 144 |             minutes = rem // 60
 145 |             return {
 146 |                 "type": slot_type,
 147 |                 "label": slot["label"],
 148 |                 "time_et": slot["time_et"],
 149 |                 "seconds_until": int(diff.total_seconds()),
 150 |                 "eta_str": f"{hours}h {minutes}m" if hours else f"{minutes}m",
 151 |             }
 152 |     # All today's slots passed — next is tomorrow's pre_market
 153 |     tomorrow_et = (now_et + timedelta(days=1)).replace(
 154 |         hour=7, minute=45, second=0, microsecond=0
 155 |     )
 156 |     diff = tomorrow_et - now_et
 157 |     hours, rem = divmod(int(diff.total_seconds()), 3600)
 158 |     minutes = rem // 60
 159 |     return {
 160 |         "type": "pre_market",
 161 |         "label": "Pre-Market Briefing",
 162 |         "time_et": "7:45 AM ET (tomorrow)",
 163 |         "seconds_until": int(diff.total_seconds()),
 164 |         "eta_str": f"{hours}h {minutes}m",
 165 |     }
 166 | 
 167 | 
 168 | def _get_briefings_list(days_back: int = 7) -> list[dict]:
 169 |     """Return briefings from today + last N days, newest first."""
 170 |     try:
 171 |         import models
 172 |         from app import app
 173 |         with app.app_context():
 174 |             cutoff = datetime.utcnow() - timedelta(days=days_back)
 175 |             briefings = (
 176 |                 models.MarketBriefing.query
 177 |                 .filter(models.MarketBriefing.generated_at >= cutoff)
 178 |                 .order_by(models.MarketBriefing.generated_at.desc())
 179 |                 .limit(30)
 180 |                 .all()
 181 |             )
 182 |             return [b.to_dict() for b in briefings]
 183 |     except Exception as exc:
 184 |         logger.warning("Briefings list fetch failed: %s", exc)
 185 |         return []
 186 | 
 187 | 
 188 | def _get_today_briefings() -> dict:
 189 |     """Return {pre_market, open, close} slots with their DB status for today."""
 190 |     et_date = _et_date_str()
 191 |     slots: dict = {k: {"slot": v, "briefing": None} for k, v in BRIEFING_SLOTS.items()}
 192 |     try:
 193 |         import models
 194 |         from app import app
 195 |         with app.app_context():
 196 |             today_briefings = (
 197 |                 models.MarketBriefing.query
 198 |                 .filter_by(scheduled_date=et_date)
 199 |                 .all()
 200 |             )
 201 |             for b in today_briefings:
 202 |                 if b.briefing_type in slots:
 203 |                     slots[b.briefing_type]["briefing"] = b.to_dict()
 204 |     except Exception as exc:
 205 |         logger.warning("Today briefings fetch failed: %s", exc)
 206 |     return slots
 207 | 
 208 | 
 209 | def _is_admin_request() -> bool:
 210 |     """IP gate + optional token check for manual trigger."""
 211 |     ip = request.remote_addr or ""
 212 |     if ip in ADMIN_ALLOWED_IPS:
 213 |         return True
 214 |     token = request.headers.get("X-Admin-Token", "") or request.args.get("token", "")
 215 |     if ADMIN_TOKEN and token == ADMIN_TOKEN:
 216 |         return True
 217 |     return False
 218 | 
 219 | 
 220 | # ---------------------------------------------------------------------------
 221 | # Routes
 222 | # ---------------------------------------------------------------------------
 223 | 
 224 | @oracle_avatar_bp.route("/oracle-live")
 225 | def oracle_live():
 226 |     """Oracle Live — cinematic briefing viewer."""
 227 |     _load_env_keys()
 228 | 
 229 |     today_slots = _get_today_briefings()
 230 |     recent_briefings = _get_briefings_list(days_back=7)
 231 |     btc_price = _live_btc_price()
 232 |     fear_greed = _live_fear_greed()
 233 |     next_slot = _next_scheduled_briefing()
 234 | 
 235 |     # Latest published video for hero player
 236 |     hero_briefing = next(
 237 |         (b for b in recent_briefings if b.get("status") == "completed" and b.get("video_url")),
 238 |         None,
 239 |     )
 240 | 
 241 |     system_status = {
 242 |         "heygen":     {"ok": _heygen_api_ok(),     "label": "HeyGen API"},
 243 |         "elevenlabs": {"ok": _elevenlabs_api_ok(), "label": "ElevenLabs"},
 244 |         "anthropic":  {"ok": _anthropic_api_ok(),  "label": "Script Gen"},
 245 |     }
 246 | 
 247 |     # Count today's completed briefings
 248 |     today_completed = sum(
 249 |         1 for s in today_slots.values()
 250 |         if s.get("briefing") and s["briefing"].get("status") == "completed"
 251 |     )
 252 | 
 253 |     return render_template(
 254 |         "oracle_live.html",
 255 |         hero_briefing=hero_briefing,
 256 |         today_slots=today_slots,
 257 |         today_completed=today_completed,
 258 |         recent_briefings=recent_briefings,
 259 |         system_status=system_status,
 260 |         next_slot=next_slot,
 261 |         btc_price=btc_price,
 262 |         fear_greed=fear_greed,
 263 |         et_date=_et_date_str(),
 264 |         now_et=_get_et_now().strftime("%H:%M ET"),
 265 |     )
 266 | 
 267 | 
 268 | @oracle_avatar_bp.route("/api/oracle/briefings")
 269 | def api_oracle_briefings():
 270 |     """List briefings: today's slots + last 7 days archive."""
 271 |     _load_env_keys()
 272 |     days_back = min(int(request.args.get("days", 7)), 30)
 273 | 
 274 |     today_slots = _get_today_briefings()
 275 |     archive = _get_briefings_list(days_back=days_back)
 276 | 
 277 |     # Serialize today slots
 278 |     today_out = {}
 279 |     for slot_type, slot_data in today_slots.items():
 280 |         today_out[slot_type] = {
 281 |             "slot_label": slot_data["slot"]["label"],
 282 |             "time_et": slot_data["slot"]["time_et"],
 283 |             "description": slot_data["slot"]["description"],
 284 |             "briefing": slot_data["briefing"],
 285 |         }
 286 | 
 287 |     return jsonify({
 288 |         "today": today_out,
 289 |         "archive": archive,
 290 |         "et_date": _et_date_str(),
 291 |         "total": len(archive),
 292 |     })
 293 | 
 294 | 
 295 | @oracle_avatar_bp.route("/api/oracle/status")
 296 | def api_oracle_status():
 297 |     """System health + scheduling metadata."""
 298 |     _load_env_keys()
 299 | 
 300 |     next_slot = _next_scheduled_briefing()
 301 |     today_slots = _get_today_briefings()
 302 |     today_completed = sum(
 303 |         1 for s in today_slots.values()
 304 |         if s.get("briefing") and s["briefing"].get("status") == "completed"
 305 |     )
 306 | 
 307 |     # Most recent completed briefing
 308 |     recent = _get_briefings_list(days_back=1)
 309 |     last_completed = next(
 310 |         (b for b in recent if b.get("status") == "completed"), None
 311 |     )
 312 | 
 313 |     last_generated_ago = None
 314 |     if last_completed and last_completed.get("generated_at"):
 315 |         try:
 316 |             ts = datetime.fromisoformat(last_completed["generated_at"])
 317 |             diff = datetime.utcnow() - ts.replace(tzinfo=None)
 318 |             h, rem = divmod(int(diff.total_seconds()), 3600)
 319 |             m = rem // 60
 320 |             last_generated_ago = f"{h}h {m}m ago" if h else f"{m}m ago"
 321 |         except Exception:
 322 |             pass
 323 | 
 324 |     system_status = {
 325 |         "heygen":     {"ok": _heygen_api_ok(),     "label": "HeyGen API"},
 326 |         "elevenlabs": {"ok": _elevenlabs_api_ok(), "label": "ElevenLabs TTS"},
 327 |         "anthropic":  {"ok": _anthropic_api_ok(),  "label": "Script Generation"},
 328 |     }
 329 |     all_ok = all(v["ok"] for v in system_status.values())
 330 | 
 331 |     return jsonify({
 332 |         "system": system_status,
 333 |         "all_systems_go": all_ok,
 334 |         "next_scheduled": next_slot,
 335 |         "today_completed": today_completed,
 336 |         "today_total_slots": len(BRIEFING_SLOTS),
 337 |         "last_generated": last_completed,
 338 |         "last_generated_ago": last_generated_ago,
 339 |         "et_now": _get_et_now().strftime("%Y-%m-%d %H:%M ET"),
 340 |     })
 341 | 
 342 | 
 343 | @oracle_avatar_bp.route("/api/oracle/generate", methods=["POST"])
 344 | def api_oracle_generate():
 345 |     """Manual briefing generation — admin only (IP-gated + token)."""
 346 |     _load_env_keys()
 347 | 
 348 |     if not _is_admin_request():
 349 |         logger.warning(
 350 |             "Unauthorized oracle generate attempt from %s", request.remote_addr
 351 |         )
 352 |         abort(403)
 353 | 
 354 |     body = request.get_json(silent=True) or {}
 355 |     briefing_type = body.get("briefing_type", "open")
 356 |     if briefing_type not in BRIEFING_SLOTS:
 357 |         return jsonify({
 358 |             "success": False,
 359 |             "error": f"Invalid briefing_type: {briefing_type}. Valid: {list(BRIEFING_SLOTS)}",
 360 |         }), 400
 361 | 
 362 |     try:
 363 |         from core.services.briefing_service import generate_briefing
 364 |         result = generate_briefing(briefing_type)
 365 |     except ImportError:
 366 |         try:
 367 |             import sys
 368 |             sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
 369 |             from services.briefing_service import generate_briefing
 370 |             result = generate_briefing(briefing_type)
 371 |         except Exception as exc:
 372 |             logger.error("Oracle generate import failed: %s", exc)
 373 |             return jsonify({"success": False, "error": str(exc)}), 500
 374 |     except Exception as exc:
 375 |         logger.error("Oracle generate failed: %s", exc)
 376 |         return jsonify({"success": False, "error": str(exc)}), 500
 377 | 
 378 |     status_code = 200 if result.get("success") else 500
 379 |     return jsonify(result), status_code
 380 | 
```

### File: core/services/oracle_scheduler.py (139 lines)
```
   1 | """
   2 | Oracle Scheduler — SESSION 7
   3 | Wraps briefing_service.generate_briefing() for 3x daily scheduled runs.
   4 | 
   5 | Schedule (ET):
   6 |   07:45 → pre_market   (publishes 08:00)
   7 |   11:45 → open         (publishes 12:00)
   8 |   16:45 → close        (publishes 17:00)
   9 | 
  10 | Called from: scheduler.py (registered jobs) or cron
  11 | Usage:
  12 |   python3 -m core.services.oracle_scheduler --slot pre_market
  13 |   python3 -m core.services.oracle_scheduler --slot open
  14 |   python3 -m core.services.oracle_scheduler --slot close
  15 | """
  16 | 
  17 | from __future__ import annotations
  18 | 
  19 | import argparse
  20 | import logging
  21 | import os
  22 | import sys
  23 | from pathlib import Path
  24 | 
  25 | logger = logging.getLogger(__name__)
  26 | 
  27 | VALID_SLOTS = ("pre_market", "open", "close")
  28 | 
  29 | 
  30 | def _load_root_env():
  31 |     """Ensure root .env is loaded so HEYGEN/ANTHROPIC keys are available."""
  32 |     try:
  33 |         from dotenv import load_dotenv
  34 |         root_env = Path(__file__).resolve().parent.parent.parent / ".env"
  35 |         if root_env.exists():
  36 |             load_dotenv(root_env, override=False)
  37 |     except ImportError:
  38 |         # Manual fallback
  39 |         root_env = Path(__file__).resolve().parent.parent.parent / ".env"
  40 |         if root_env.exists():
  41 |             for line in root_env.read_text().splitlines():
  42 |                 line = line.strip()
  43 |                 if line and not line.startswith("#") and "=" in line:
  44 |                     k, v = line.split("=", 1)
  45 |                     os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
  46 | 
  47 | 
  48 | def run_slot(briefing_type: str) -> dict:
  49 |     """Generate a single briefing slot. Returns result dict."""
  50 |     if briefing_type not in VALID_SLOTS:
  51 |         return {"success": False, "error": f"Invalid slot: {briefing_type}"}
  52 | 
  53 |     _load_root_env()
  54 | 
  55 |     logger.info("Oracle scheduler: triggering %s briefing", briefing_type)
  56 | 
  57 |     try:
  58 |         from services.briefing_service import generate_briefing
  59 |     except ImportError:
  60 |         # Try core-relative import
  61 |         sys.path.insert(0, str(Path(__file__).resolve().parent))
  62 |         try:
  63 |             from briefing_service import generate_briefing
  64 |         except ImportError as exc:
  65 |             logger.error("Could not import briefing_service: %s", exc)
  66 |             return {"success": False, "error": str(exc)}
  67 | 
  68 |     result = generate_briefing(briefing_type)
  69 | 
  70 |     if result.get("success"):
  71 |         logger.info(
  72 |             "Oracle %s completed — briefing_id=%s video=%s",
  73 |             briefing_type,
  74 |             result.get("briefing_id"),
  75 |             result.get("video_url"),
  76 |         )
  77 |     else:
  78 |         logger.error("Oracle %s failed: %s", briefing_type, result.get("error"))
  79 | 
  80 |     return result
  81 | 
  82 | 
  83 | def schedule_all_slots(scheduler_instance=None):
  84 |     """Register oracle briefing jobs with the app scheduler.
  85 | 
  86 |     Passes scheduler_instance (APScheduler/custom) if available,
  87 |     otherwise logs the schedule for cron configuration.
  88 |     """
  89 |     slots = [
  90 |         ("pre_market", "07:45", "12:45 UTC"),
  91 |         ("open",       "11:45", "16:45 UTC"),
  92 |         ("close",      "16:45", "21:45 UTC"),
  93 |     ]
  94 | 
  95 |     if scheduler_instance is None:
  96 |         logger.info("Oracle briefing schedule (ET):")
  97 |         for slot_type, time_et, time_utc in slots:
  98 |             logger.info("  %s at %s ET (%s)", slot_type, time_et, time_utc)
  99 |         logger.info(
 100 |             "Add to cron: 45 12,16,21 * * * cd /home/ultron/protocol_pulse && "
 101 |             "python3 -m core.services.oracle_scheduler --slot <type>"
 102 |         )
 103 |         return
 104 | 
 105 |     for slot_type, time_et, _ in slots:
 106 |         h, m = map(int, time_et.split(":"))
 107 |         try:
 108 |             import pytz
 109 |             et = pytz.timezone("America/New_York")
 110 |             scheduler_instance.add_job(
 111 |                 func=run_slot,
 112 |                 args=[slot_type],
 113 |                 trigger="cron",
 114 |                 hour=h,
 115 |                 minute=m,
 116 |                 timezone=et,
 117 |                 id=f"oracle_{slot_type}",
 118 |                 replace_existing=True,
 119 |                 max_instances=1,
 120 |                 misfire_grace_time=300,
 121 |             )
 122 |             logger.info("Registered oracle_%s job at %s ET", slot_type, time_et)
 123 |         except Exception as exc:
 124 |             logger.warning("Could not register oracle_%s job: %s", slot_type, exc)
 125 | 
 126 | 
 127 | if __name__ == "__main__":
 128 |     logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
 129 |     parser = argparse.ArgumentParser(description="Oracle briefing scheduler")
 130 |     parser.add_argument(
 131 |         "--slot",
 132 |         choices=list(VALID_SLOTS),
 133 |         required=True,
 134 |         help="Briefing slot to generate",
 135 |     )
 136 |     args = parser.parse_args()
 137 |     result = run_slot(args.slot)
 138 |     sys.exit(0 if result.get("success") else 1)
 139 | 
```

### File: core/templates/charts.html (857 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Bitcoin Charts — Bloomberg Terminal Intelligence | Protocol Pulse{% endblock %}
   4 | {% block meta_description %}Real-time Bitcoin charts: price history, hashrate, difficulty, MVRV Z-Score, realized price, Fear & Greed, and fee market. Bloomberg terminal aesthetic. No account needed.{% endblock %}
   5 | 
   6 | {% block extra_css %}
   7 | <style>
   8 | /* ── SESSION 4 CHARTS — Bloomberg Terminal Design ───────────────────────── */
   9 | :root {
  10 |   --bg:        #06070b;
  11 |   --panel:     #0d1118;
  12 |   --panel-2:   #121824;
  13 |   --border:    rgba(255,255,255,0.07);
  14 |   --text:      #eef2ff;
  15 |   --muted:     #95a0ba;
  16 |   --gold:      #F59E0B;
  17 |   --cyan:      #5DE4FF;
  18 |   --lime:      #89FFB8;
  19 |   --coral:     #FF8BA0;
  20 |   --red:       #FF3B5F;
  21 | }
  22 | *, *::before, *::after { box-sizing: border-box; }
  23 | body { background: var(--bg); color: var(--text); font-family: 'JetBrains Mono', monospace; }
  24 | 
  25 | /* ── Stat Bar ─────────────────────────────────────────────────────────── */
  26 | .stat-bar {
  27 |   display: grid;
  28 |   grid-template-columns: repeat(6, 1fr);
  29 |   gap: .4rem;
  30 |   padding: .75rem 0;
  31 |   position: sticky; top: 0; z-index: 50;
  32 |   background: linear-gradient(180deg, rgba(6,7,11,.98) 80%, transparent);
  33 |   backdrop-filter: blur(12px);
  34 |   border-bottom: 1px solid var(--border);
  35 | }
  36 | .stat-card {
  37 |   background: var(--panel);
  38 |   border: 1px solid var(--border);
  39 |   border-radius: 8px;
  40 |   padding: .5rem .8rem;
  41 |   display: flex; flex-direction: column; gap: .1rem;
  42 | }
  43 | .sc-label { font-size: 9px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; color: var(--muted); }
  44 | .sc-value  { font-size: 1rem; font-weight: 900; color: var(--text); line-height: 1; }
  45 | .sc-delta  { font-size: 10px; font-weight: 700; }
  46 | .delta-up  { color: var(--lime); }
  47 | .delta-down{ color: var(--coral); }
  48 | .live-pulse {
  49 |   display: inline-block; width: 6px; height: 6px;
  50 |   border-radius: 50%; background: var(--lime);
  51 |   margin-right: 3px; vertical-align: middle;
  52 |   animation: livePulse 2s ease-in-out infinite;
  53 | }
  54 | @keyframes livePulse { 0%,100%{opacity:1}50%{opacity:.2} }
  55 | 
  56 | /* ── 3-Column Layout ──────────────────────────────────────────────────── */
  57 | .charts-page { max-width: 1600px; margin: 0 auto; padding: 0 .75rem 4rem; }
  58 | .charts-layout {
  59 |   display: grid;
  60 |   grid-template-columns: 200px 1fr 200px;
  61 |   gap: 1rem;
  62 |   align-items: start;
  63 |   margin-top: 1rem;
  64 | }
  65 | 
  66 | /* ── Left Sidebar: Chart Selector ─────────────────────────────────────── */
  67 | .chart-selector {
  68 |   position: sticky; top: 90px;
  69 |   background: var(--panel);
  70 |   border: 1px solid var(--border);
  71 |   border-radius: 12px;
  72 |   overflow: hidden;
  73 |   user-select: none;
  74 | }
  75 | .sidebar-hdr {
  76 |   padding: .75rem 1rem;
  77 |   border-bottom: 1px solid var(--border);
  78 |   font-size: 9px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
  79 | }
  80 | .chart-cat {
  81 |   padding: .4rem 1rem .15rem;
  82 |   font-size: 8px; font-weight: 800; letter-spacing: .2em; text-transform: uppercase;
  83 |   color: rgba(245,158,11,.5);
  84 |   margin-top: .2rem;
  85 | }
  86 | .chart-item {
  87 |   display: flex; align-items: center; justify-content: space-between;
  88 |   padding: .45rem 1rem;
  89 |   cursor: pointer;
  90 |   border-left: 2px solid transparent;
  91 |   transition: background .1s, border-color .1s;
  92 |   gap: .3rem;
  93 | }
  94 | .chart-item:hover { background: rgba(255,255,255,.03); }
  95 | .chart-item.active { background: rgba(245,158,11,.07); border-left-color: var(--gold); }
  96 | .chart-item.active .ci-name { color: var(--gold); }
  97 | .ci-name  { font-size: 11px; font-weight: 700; color: var(--text); flex:1; }
  98 | .ci-value { font-size: 9px; font-weight: 800; color: var(--muted); }
  99 | .ci-delta { font-size: 8px; font-weight: 700; }
 100 | 
 101 | /* ── Main Chart Area ──────────────────────────────────────────────────── */
 102 | .chart-main {
 103 |   background: var(--panel);
 104 |   border: 1px solid var(--border);
 105 |   border-radius: 12px;
 106 |   overflow: hidden;
 107 | }
 108 | .chart-topbar {
 109 |   display: flex; align-items: center; justify-content: space-between;
 110 |   padding: .85rem 1.25rem;
 111 |   border-bottom: 1px solid var(--border);
 112 |   flex-wrap: wrap; gap: .4rem;
 113 | }
 114 | .chart-name-block .chart-ttl   { font-size: 13px; font-weight: 900; color: var(--text); }
 115 | .chart-name-block .chart-sub   { font-size: 9px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin-top:.1rem; }
 116 | .tf-row { display: flex; gap: .25rem; align-items: center; }
 117 | .tf-btn {
 118 |   background: rgba(255,255,255,.04);
 119 |   border: 1px solid var(--border);
 120 |   border-radius: 5px;
 121 |   padding: 3px 9px;
 122 |   font-family: 'JetBrains Mono', monospace;
 123 |   font-size: 10px; font-weight: 700;
 124 |   color: var(--muted); cursor: pointer; transition: all .12s;
 125 | }
 126 | .tf-btn:hover { border-color: rgba(245,158,11,.4); color: var(--gold); }
 127 | .tf-btn.active { background: rgba(245,158,11,.1); border-color: var(--gold); color: var(--gold); }
 128 | .action-row { display: flex; gap: .3rem; }
 129 | .action-btn {
 130 |   background: rgba(255,255,255,.04);
 131 |   border: 1px solid var(--border);
 132 |   border-radius: 5px;
 133 |   padding: 3px 8px;
 134 |   font-family: 'JetBrains Mono', monospace;
 135 |   font-size: 9px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase;
 136 |   color: var(--muted); cursor: pointer; transition: all .12s;
 137 | }
 138 | .ai-btn  { border-color: rgba(93,228,255,.2); color: var(--cyan); }
 139 | .ai-btn:hover  { background: rgba(93,228,255,.08); }
 140 | .dl-btn  { border-color: rgba(137,255,184,.2); color: var(--lime); }
 141 | .dl-btn:hover  { background: rgba(137,255,184,.08); }
 142 | 
 143 | /* D3 chart container */
 144 | .d3-container {
 145 |   position: relative;
 146 |   padding: .75rem 1rem 1rem;
 147 |   min-height: 380px;
 148 | }
 149 | .d3-svg-wrap { position: relative; width: 100%; }
 150 | .d3-svg-wrap svg { display: block; overflow: visible; }
 151 | 
 152 | /* Loading/error overlay */
 153 | .chart-overlay {
 154 |   position: absolute; inset: 0;
 155 |   display: flex; align-items: center; justify-content: center;
 156 |   background: rgba(6,7,11,.88); backdrop-filter: blur(4px);
 157 |   border-radius: 8px; z-index: 20; flex-direction: column; gap: .5rem;
 158 | }
 159 | .chart-overlay.hidden { display: none; }
 160 | .spinner {
 161 |   width: 22px; height: 22px;
 162 |   border: 2px solid var(--border); border-top-color: var(--gold);
 163 |   border-radius: 50%; animation: spin .7s linear infinite;
 164 | }
 165 | @keyframes spin { to{transform:rotate(360deg)} }
 166 | .overlay-msg { font-size: 11px; color: var(--muted); }
 167 | 
 168 | /* AI box */
 169 | .ai-box {
 170 |   margin: 0 1rem .75rem;
 171 |   background: rgba(93,228,255,.05);
 172 |   border: 1px solid rgba(93,228,255,.15);
 173 |   border-radius: 8px; padding: .7rem 1rem;
 174 |   font-size: 12px; line-height: 1.55; color: #c8e8f0; display: none;
 175 | }
 176 | .ai-box.show { display: block; }
 177 | .ai-box-lbl { font-size: 8px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; color: var(--cyan); margin-bottom: .4rem; }
 178 | .source-tag { font-size: 8px; color: rgba(149,160,186,.45); padding: .3rem 1rem; text-align: right; border-top: 1px solid var(--border); }
 179 | 
 180 | /* ── Right Stats Sidebar ──────────────────────────────────────────────── */
 181 | .stats-sidebar {
 182 |   position: sticky; top: 90px;
 183 |   background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
 184 | }
 185 | .stats-hdr { padding: .75rem 1rem; border-bottom: 1px solid var(--border); font-size: 9px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); }
 186 | .stat-blk { padding: .6rem 1rem; border-bottom: 1px solid var(--border); }
 187 | .stat-blk:last-child { border-bottom: none; }
 188 | .sb-lbl { font-size: 8px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); display: block; }
 189 | .sb-val { font-size: 1rem; font-weight: 900; color: var(--text); display: block; margin-top: .1rem; word-break: break-all; }
 190 | .sb-sub { font-size: 9px; color: var(--muted); margin-top: .1rem; }
 191 | .rolling-sec { padding: .5rem 1rem; border-top: 1px solid var(--border); }
 192 | .rolling-ttl { font-size: 8px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin-bottom: .4rem; }
 193 | .rolling-row { display: flex; justify-content: space-between; font-size: 10px; padding: .18rem 0; }
 194 | .rr-key { color: var(--muted); }
 195 | .rr-val { color: var(--text); font-weight: 700; }
 196 | 
 197 | /* ── Mobile horizontal tab scroll ───────────────────────────────────── */
 198 | .mobile-tabs { display: none; overflow-x: auto; gap: .35rem; padding: .5rem 0; scrollbar-width: none; }
 199 | .mobile-tabs::-webkit-scrollbar { display: none; }
 200 | .mobile-tab {
 201 |   flex-shrink: 0;
 202 |   background: var(--panel); border: 1px solid var(--border); border-radius: 6px;
 203 |   padding: .3rem .75rem; font-size: 10px; font-weight: 700;
 204 |   color: var(--muted); cursor: pointer; transition: all .12s; white-space: nowrap;
 205 | }
 206 | .mobile-tab.active { background: rgba(245,158,11,.1); border-color: var(--gold); color: var(--gold); }
 207 | 
 208 | /* ── Responsive ──────────────────────────────────────────────────────── */
 209 | @media(max-width:1100px){
 210 |   .charts-layout { grid-template-columns: 180px 1fr; }
 211 |   .stats-sidebar { grid-column: 1/-1; position: static; }
 212 |   .stats-sidebar-inner { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px,1fr)); }
 213 |   .stat-blk { border-right: 1px solid var(--border); }
 214 | }
 215 | @media(max-width:768px){
 216 |   .stat-bar { grid-template-columns: repeat(3,1fr); }
 217 |   .charts-layout { grid-template-columns: 1fr; }
 218 |   .chart-selector { display: none; }
 219 |   .mobile-tabs { display: flex; }
 220 |   .stats-sidebar { position: static; }
 221 | }
 222 | @media(max-width:480px){
 223 |   .stat-bar { grid-template-columns: repeat(2,1fr); }
 224 |   .chart-topbar { flex-direction: column; align-items: flex-start; }
 225 | }
 226 | </style>
 227 | {% endblock %}
 228 | 
 229 | {% block content %}
 230 | <div class="charts-page">
 231 | 
 232 |   <!-- Stat Bar -->
 233 |   <div class="stat-bar">
 234 |     <div class="stat-card">
 235 |       <span class="sc-label"><span class="live-pulse"></span>BTC / USD</span>
 236 |       <span class="sc-value" id="sb-price">${{ "{:,.0f}".format(btc_price) if btc_price else "---" }}</span>
 237 |       <span class="sc-delta" id="sb-change">—</span>
 238 |     </div>
 239 |     <div class="stat-card">
 240 |       <span class="sc-label">Block Height</span>
 241 |       <span class="sc-value">{{ "{:,}".format(block_height) if block_height else "—" }}</span>
 242 |       <span class="sc-delta" style="color:var(--muted);font-size:9px">mainnet</span>
 243 |     </div>
 244 |     <div class="stat-card">
 245 |       <span class="sc-label">Mempool</span>
 246 |       <span class="sc-value">{{ mempool_mb }} MB</span>
 247 |       <span class="sc-delta" style="color:var(--muted);font-size:9px">{{ next_block_fee }} sat/vB</span>
 248 |     </div>
 249 |     <div class="stat-card">
 250 |       <span class="sc-label">Supply Mined</span>
 251 |       <span class="sc-value">{{ "{:,.0f}".format(mined_supply) }}</span>
 252 |       <span class="sc-delta" style="color:var(--muted);font-size:9px">{{ pct_mined }}% of 21M</span>
 253 |     </div>
 254 |     <div class="stat-card">
 255 |       <span class="sc-label">Next Halving</span>
 256 |       <span class="sc-value" style="color:var(--red)">{{ "{:,}".format(blocks_to_halving) }}</span>
 257 |       <span class="sc-delta" style="color:var(--muted);font-size:9px">blocks · ~{{ days_to_halving }}d</span>
 258 |     </div>
 259 |     <div class="stat-card">
 260 |       <span class="sc-label">Sats / Dollar</span>
 261 |       <span class="sc-value" style="color:var(--gold)">{{ "{:,}".format(sats_per_dollar) }}</span>
 262 |       <span class="sc-delta" style="color:var(--muted);font-size:9px">{{ current_subsidy }} BTC/block</span>
 263 |     </div>
 264 |   </div>
 265 | 
 266 |   <!-- Mobile tabs -->
 267 |   <div class="mobile-tabs" id="mobile-tabs">
 268 |     <button class="mobile-tab active" data-chart="price" data-period="7d">BTC/USD</button>
 269 |     <button class="mobile-tab" data-chart="hashrate" data-period="1y">Hashrate</button>
 270 |     <button class="mobile-tab" data-chart="difficulty" data-period="1y">Difficulty</button>
 271 |     <button class="mobile-tab" data-chart="mvrv" data-period="1y">MVRV</button>
 272 |     <button class="mobile-tab" data-chart="realized-price" data-period="1y">Realized Price</button>
 273 |     <button class="mobile-tab" data-chart="s2f" data-period="all">S2F Model</button>
 274 |     <button class="mobile-tab" data-chart="fear-greed" data-period="1y">Fear & Greed</button>
 275 |     <button class="mobile-tab" data-chart="mempool" data-period="7d">Mempool</button>
 276 |     <button class="mobile-tab" data-chart="fees" data-period="30d">Fees</button>
 277 |   </div>
 278 | 
 279 |   <!-- 3-column layout -->
 280 |   <div class="charts-layout">
 281 | 
 282 |     <!-- LEFT: Chart Selector Sidebar -->
 283 |     <aside class="chart-selector">
 284 |       <div class="sidebar-hdr">CHARTS</div>
 285 | 
 286 |       <div class="chart-cat">PRICE</div>
 287 |       <div class="chart-item active" data-chart="price" data-period="7d">
 288 |         <span class="ci-name">BTC / USD</span>
 289 |         <div style="text-align:right">
 290 |           <div class="ci-value" id="ci-val-price">—</div>
 291 |           <div class="ci-delta" id="ci-delta-price">—</div>
 292 |         </div>
 293 |       </div>
 294 | 
 295 |       <div class="chart-cat">NETWORK</div>
 296 |       <div class="chart-item" data-chart="hashrate" data-period="1y">
 297 |         <span class="ci-name">Hashrate</span>
 298 |         <div style="text-align:right">
 299 |           <div class="ci-value" id="ci-val-hashrate">—</div>
 300 |           <div class="ci-delta" id="ci-delta-hashrate">—</div>
 301 |         </div>
 302 |       </div>
 303 |       <div class="chart-item" data-chart="difficulty" data-period="1y">
 304 |         <span class="ci-name">Difficulty</span>
 305 |         <div style="text-align:right">
 306 |           <div class="ci-value" id="ci-val-difficulty">—</div>
 307 |           <div class="ci-delta" id="ci-delta-difficulty">—</div>
 308 |         </div>
 309 |       </div>
 310 | 
 311 |       <div class="chart-cat">VALUATION</div>
 312 |       <div class="chart-item" data-chart="mvrv" data-period="1y">
 313 |         <span class="ci-name">MVRV Z-Score</span>
 314 |         <div style="text-align:right">
 315 |           <div class="ci-value" id="ci-val-mvrv">—</div>
 316 |           <div class="ci-delta" id="ci-delta-mvrv">—</div>
 317 |         </div>
 318 |       </div>
 319 |       <div class="chart-item" data-chart="realized-price" data-period="1y">
 320 |         <span class="ci-name">Realized Price</span>
 321 |         <div style="text-align:right">
 322 |           <div class="ci-value" id="ci-val-realized-price">—</div>
 323 |           <div class="ci-delta" id="ci-delta-realized-price">—</div>
 324 |         </div>
 325 |       </div>
 326 |       <div class="chart-item" data-chart="s2f" data-period="all">
 327 |         <span class="ci-name">S2F Model</span>
 328 |         <div style="text-align:right">
 329 |           <div class="ci-value" id="ci-val-s2f">—</div>
 330 |           <div class="ci-delta" id="ci-delta-s2f">—</div>
 331 |         </div>
 332 |       </div>
 333 | 
 334 |       <div class="chart-cat">MARKET</div>
 335 |       <div class="chart-item" data-chart="fear-greed" data-period="1y">
 336 |         <span class="ci-name">Fear & Greed</span>
 337 |         <div style="text-align:right">
 338 |           <div class="ci-value" id="ci-val-fear-greed">—</div>
 339 |           <div class="ci-delta" id="ci-delta-fear-greed">—</div>
 340 |         </div>
 341 |       </div>
 342 | 
 343 |       <div class="chart-cat">FEES</div>
 344 |       <div class="chart-item" data-chart="mempool" data-period="7d">
 345 |         <span class="ci-name">Mempool Size</span>
 346 |         <div style="text-align:right">
 347 |           <div class="ci-value" id="ci-val-mempool">—</div>
 348 |           <div class="ci-delta" id="ci-delta-mempool">—</div>
 349 |         </div>
 350 |       </div>
 351 |       <div class="chart-item" data-chart="fees" data-period="30d">
 352 |         <span class="ci-name">Fee History</span>
 353 |         <div style="text-align:right">
 354 |           <div class="ci-value" id="ci-val-fees">{{ next_block_fee }} sat/vB</div>
 355 |           <div class="ci-delta" id="ci-delta-fees">—</div>
 356 |         </div>
 357 |       </div>
 358 |     </aside>
 359 | 
 360 |     <!-- CENTER: Main D3 Chart -->
 361 |     <main class="chart-main">
 362 |       <div class="chart-topbar">
 363 |         <div class="chart-name-block">
 364 |           <div class="chart-ttl" id="chart-title">BTC / USD</div>
 365 |           <div class="chart-sub" id="chart-subtitle">Bitcoin / US Dollar</div>
 366 |         </div>
 367 |         <div class="tf-row">
 368 |           <button class="tf-btn" data-tf="1d">1D</button>
 369 |           <button class="tf-btn active" data-tf="7d">7D</button>
 370 |           <button class="tf-btn" data-tf="1m">1M</button>
 371 |           <button class="tf-btn" data-tf="3m">3M</button>
 372 |           <button class="tf-btn" data-tf="1y">1Y</button>
 373 |           <button class="tf-btn" data-tf="all">ALL</button>
 374 |         </div>
 375 |         <div class="action-row">
 376 |           <button class="action-btn ai-btn" id="btn-ai">⚡ AI</button>
 377 |           <button class="action-btn dl-btn"  id="btn-og">↗ OG</button>
 378 |         </div>
 379 |       </div>
 380 | 
 381 |       <div class="d3-container">
 382 |         <div class="chart-overlay" id="chart-loading">
 383 |           <div class="spinner"></div>
 384 |           <span class="overlay-msg">Loading data…</span>
 385 |         </div>
 386 |         <div class="chart-overlay hidden" id="chart-error">
 387 |           <span class="overlay-msg">⚠ Data unavailable — upstream API unreachable</span>
 388 |         </div>
 389 |         <div class="d3-svg-wrap" id="d3-wrap"></div>
 390 |       </div>
 391 | 
 392 |       <div class="ai-box" id="ai-box">
 393 |         <div class="ai-box-lbl">⚡ AI ANALYSIS</div>
 394 |         <span id="ai-box-text"></span>
 395 |       </div>
 396 | 
 397 |       <div class="source-tag" id="chart-source">SOURCE: —</div>
 398 |     </main>
 399 | 
 400 |     <!-- RIGHT: Stats Sidebar -->
 401 |     <aside class="stats-sidebar">
 402 |       <div class="stats-hdr">STATISTICS</div>
 403 |       <div class="stats-sidebar-inner">
 404 |         <div class="stat-blk">
 405 |           <span class="sb-lbl">Current</span>
 406 |           <span class="sb-val" id="ss-current">—</span>
 407 |           <span class="sb-sub" id="ss-current-sub"></span>
 408 |         </div>
 409 |         <div class="stat-blk">
 410 |           <span class="sb-lbl">Period High</span>
 411 |           <span class="sb-val" id="ss-ath" style="color:var(--lime)">—</span>
 412 |           <span class="sb-sub" id="ss-ath-date"></span>
 413 |         </div>
 414 |         <div class="stat-blk">
 415 |           <span class="sb-lbl">Period Low</span>
 416 |           <span class="sb-val" id="ss-atl" style="color:var(--coral)">—</span>
 417 |           <span class="sb-sub" id="ss-atl-date"></span>
 418 |         </div>
 419 |         <div class="stat-blk">
 420 |           <span class="sb-lbl">24h Change</span>
 421 |           <span class="sb-val" id="ss-24h">—</span>
 422 |         </div>
 423 |         <div class="stat-blk">
 424 |           <span class="sb-lbl">7d Change</span>
 425 |           <span class="sb-val" id="ss-7d">—</span>
 426 |         </div>
 427 |         <div class="stat-blk">
 428 |           <span class="sb-lbl">30d Change</span>
 429 |           <span class="sb-val" id="ss-30d">—</span>
 430 |         </div>
 431 |         <div class="rolling-sec">
 432 |           <div class="rolling-ttl">PERIOD STATS</div>
 433 |           <div class="rolling-row"><span class="rr-key">Avg</span><span class="rr-val" id="rs-avg">—</span></div>
 434 |           <div class="rolling-row"><span class="rr-key">Median</span><span class="rr-val" id="rs-median">—</span></div>
 435 |           <div class="rolling-row"><span class="rr-key">Std Dev</span><span class="rr-val" id="rs-std">—</span></div>
 436 |           <div class="rolling-row"><span class="rr-key">Points</span><span class="rr-val" id="rs-count">—</span></div>
 437 |         </div>
 438 |       </div>
 439 |     </aside>
 440 | 
 441 |   </div><!-- .charts-layout -->
 442 | </div><!-- .charts-page -->
 443 | 
 444 | <!-- ── D3.js v7 ─────────────────────────────────────────────────────────── -->
 445 | <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
 446 | <script>
 447 | 'use strict';
 448 | 
 449 | /* ── Chart configuration map ──────────────────────────────────────────── */
 450 | const CHART_CONFIG = {
 451 |   price: {
 452 |     title: 'BTC / USD', subtitle: 'Bitcoin / US Dollar',
 453 |     apiPath: '/api/charts/price', color: '#F59E0B', unit: 'USD', defaultPeriod: '7d',
 454 |     fmtVal:  v => '$' + d3.format(',.0f')(v),
 455 |     fmtAxis: v => '$' + (v >= 1e6 ? d3.format('.3s')(v) : d3.format(',.0f')(v)),
 456 |   },
 457 |   hashrate: {
 458 |     title: 'Network Hashrate', subtitle: 'EH/s — Exahashes per second',
 459 |     apiPath: '/api/charts/hashrate', color: '#5DE4FF', unit: 'EH/s', defaultPeriod: '1y',
 460 |     fmtVal:  v => d3.format(',.2f')(v) + ' EH/s',
 461 |     fmtAxis: v => d3.format(',.0f')(v),
 462 |   },
 463 |   difficulty: {
 464 |     title: 'Mining Difficulty', subtitle: 'Trillion (T) — adjustment epochs',
 465 |     apiPath: '/api/charts/difficulty', color: '#A78BFA', unit: 'T', defaultPeriod: '1y',
 466 |     fmtVal:  v => d3.format(',.2f')(v) + 'T',
 467 |     fmtAxis: v => d3.format(',.1f')(v) + 'T',
 468 |   },
 469 |   mvrv: {
 470 |     title: 'MVRV Ratio', subtitle: 'Market Value / Realized Value',
 471 |     apiPath: '/api/charts/mvrv', color: '#FB923C', unit: 'ratio', defaultPeriod: '1y',
 472 |     fmtVal:  v => d3.format(',.4f')(v),
 473 |     fmtAxis: v => d3.format(',.2f')(v),
 474 |   },
 475 |   'realized-price': {
 476 |     title: 'Realized Price', subtitle: 'Volume-weighted cost basis (USD)',
 477 |     apiPath: '/api/charts/realized-price', color: '#60A5FA', unit: 'USD', defaultPeriod: '1y',
 478 |     fmtVal:  v => '$' + d3.format(',.0f')(v),
 479 |     fmtAxis: v => '$' + d3.format(',.0f')(v),
 480 |   },
 481 |   s2f: {
 482 |     title: 'Stock-to-Flow Model', subtitle: 'PlanB S2F model price (USD)',
 483 |     apiPath: '/api/charts/s2f', color: '#D97706', unit: 'USD model', defaultPeriod: 'all',
 484 |     fmtVal:  v => '$' + d3.format(',.0f')(v),
 485 |     fmtAxis: v => '$' + (v >= 1e6 ? d3.format('.2s')(v) : d3.format(',.0f')(v)),
 486 |   },
 487 |   'fear-greed': {
 488 |     title: 'Fear & Greed Index', subtitle: '0 = Extreme Fear · 100 = Extreme Greed',
 489 |     apiPath: '/api/charts/fg-history', color: '#89FFB8', unit: 'F&G', defaultPeriod: '1y',
 490 |     fmtVal:  v => Math.round(v).toString(),
 491 |     fmtAxis: v => Math.round(v).toString(),
 492 |   },
 493 |   mempool: {
 494 |     title: 'Mempool Size', subtitle: 'Unconfirmed transactions (MB)',
 495 |     apiPath: null, color: '#FF3B5F', unit: 'MB', defaultPeriod: '7d',
 496 |     fmtVal:  v => d3.format(',.2f')(v) + ' MB',
 497 |     fmtAxis: v => d3.format(',.1f')(v),
 498 |   },
 499 |   fees: {
 500 |     title: 'Fee Market History', subtitle: 'Average fee rate (sat/vB)',
 501 |     apiPath: null, color: '#F59E0B', unit: 'sat/vB', defaultPeriod: '30d',
 502 |     fmtVal:  v => Math.round(v) + ' sat/vB',
 503 |     fmtAxis: v => Math.round(v).toString(),
 504 |   },
 505 | };
 506 | 
 507 | /* ── State ────────────────────────────────────────────────────────────── */
 508 | const state = { chart: 'price', period: '7d', data: null, busy: false };
 509 | 
 510 | /* ── DOM ──────────────────────────────────────────────────────────────── */
 511 | const wrap    = document.getElementById('d3-wrap');
 512 | const loadOvl = document.getElementById('chart-loading');
 513 | const errOvl  = document.getElementById('chart-error');
 514 | const aiBox   = document.getElementById('ai-box');
 515 | const aiTxt   = document.getElementById('ai-box-text');
 516 | const srcTag  = document.getElementById('chart-source');
 517 | 
 518 | const showLoad = on => loadOvl.classList.toggle('hidden', !on);
 519 | const showErr  = on => errOvl.classList.toggle('hidden', !on);
 520 | 
 521 | /* ── Value formatting helpers ─────────────────────────────────────────── */
 522 | function fmtDelta(pct) {
 523 |   const sign = pct >= 0 ? '+' : '';
 524 |   const cls  = pct >= 0 ? 'delta-up' : 'delta-down';
 525 |   return `<span class="${cls}">${sign}${pct.toFixed(2)}%</span>`;
 526 | }
 527 | 
 528 | /* ── Statistics ───────────────────────────────────────────────────────── */
 529 | function computeStats(data) {
 530 |   if (!data || data.length < 2) return null;
 531 |   const vals = data.map(d => d[1]);
 532 |   const last  = vals[vals.length - 1];
 533 |   const max   = Math.max(...vals);
 534 |   const min   = Math.min(...vals);
 535 |   const miMax = vals.indexOf(max);
 536 |   const miMin = vals.indexOf(min);
 537 | 
 538 |   const now = Date.now();
 539 |   const near = ms => {
 540 |     let best = data[0];
 541 |     for (const d of data) if (Math.abs(d[0] - (now - ms)) < Math.abs(best[0] - (now - ms))) best = d;
 542 |     return best[1];
 543 |   };
 544 | 
 545 |   const avg    = vals.reduce((a,b) => a+b,0) / vals.length;
 546 |   const sorted = [...vals].sort((a,b)=>a-b);
 547 |   const mid    = Math.floor(sorted.length/2);
 548 |   const median = sorted.length % 2 ? sorted[mid] : (sorted[mid-1]+sorted[mid])/2;
 549 |   const std    = Math.sqrt(vals.reduce((a,b)=>a+(b-avg)**2,0)/vals.length);
 550 | 
 551 |   return {
 552 |     current: last, high: max, low: min,
 553 |     highDate: new Date(data[miMax][0]).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}),
 554 |     lowDate:  new Date(data[miMin][0]).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}),
 555 |     chg24h:  ((last - near(86400e3))    / near(86400e3))    * 100,
 556 |     chg7d:   ((last - near(7*86400e3))  / near(7*86400e3))  * 100,
 557 |     chg30d:  ((last - near(30*86400e3)) / near(30*86400e3)) * 100,
 558 |     avg, median, std, count: vals.length,
 559 |   };
 560 | }
 561 | 
 562 | function renderStats(data) {
 563 |   const cfg = CHART_CONFIG[state.chart];
 564 |   const s   = computeStats(data);
 565 |   if (!s) return;
 566 |   document.getElementById('ss-current').textContent = cfg.fmtVal(s.current);
 567 |   document.getElementById('ss-ath').textContent     = cfg.fmtVal(s.high);
 568 |   document.getElementById('ss-ath-date').textContent= s.highDate;
 569 |   document.getElementById('ss-atl').textContent     = cfg.fmtVal(s.low);
 570 |   document.getElementById('ss-atl-date').textContent= s.lowDate;
 571 |   document.getElementById('ss-24h').innerHTML  = fmtDelta(s.chg24h);
 572 |   document.getElementById('ss-7d').innerHTML   = fmtDelta(s.chg7d);
 573 |   document.getElementById('ss-30d').innerHTML  = fmtDelta(s.chg30d);
 574 |   document.getElementById('rs-avg').textContent    = cfg.fmtVal(s.avg);
 575 |   document.getElementById('rs-median').textContent = cfg.fmtVal(s.median);
 576 |   document.getElementById('rs-std').textContent    = cfg.fmtVal(s.std);
 577 |   document.getElementById('rs-count').textContent  = s.count;
 578 | }
 579 | 
 580 | function updateSidebarItem(key, data) {
 581 |   const valEl = document.getElementById(`ci-val-${key}`);
 582 |   const dltEl = document.getElementById(`ci-delta-${key}`);
 583 |   if (!valEl || !data || data.length < 2) return;
 584 |   const cfg  = CHART_CONFIG[key];
 585 |   const last = data[data.length-1][1];
 586 |   const prev = data[Math.max(0, data.length-7)][1];
 587 |   const pct  = ((last - prev) / prev) * 100;
 588 |   valEl.textContent = cfg.fmtVal(last);
 589 |   dltEl.innerHTML   = fmtDelta(pct);
 590 | }
 591 | 
 592 | /* ── D3 renderer ──────────────────────────────────────────────────────── */
 593 | function renderD3(data, cfg) {
 594 |   d3.select(wrap).selectAll('*').remove();
 595 | 
 596 |   const W  = wrap.offsetWidth || 640;
 597 |   const mg = { top: 16, right: 16, bottom: 38, left: 72 };
 598 |   const w  = W - mg.left - mg.right;
 599 |   const h  = 340;
 600 |   const c  = cfg.color;
 601 | 
 602 |   const svg = d3.select(wrap).append('svg')
 603 |     .attr('width','100%').attr('height', h + mg.top + mg.bottom)
 604 |     .style('overflow','visible');
 605 | 
 606 |   const g = svg.append('g').attr('transform',`translate(${mg.left},${mg.top})`);
 607 | 
 608 |   // Scales
 609 |   const x = d3.scaleTime()
 610 |     .domain(d3.extent(data, d => new Date(d[0])))
 611 |     .range([0, w]);
 612 |   const [yMin,yMax] = d3.extent(data, d => d[1]);
 613 |   const yPad = (yMax - yMin) * 0.05 || Math.abs(yMax) * 0.05 || 1;
 614 |   const y = d3.scaleLinear().domain([yMin - yPad, yMax + yPad]).range([h, 0]);
 615 | 
 616 |   // Grid
 617 |   g.append('g').call(d3.axisLeft(y).tickSize(-w).tickFormat(''))
 618 |     .call(gg => gg.select('.domain').remove())
 619 |     .call(gg => gg.selectAll('line').style('stroke','#1C1C2E').style('stroke-dasharray','2,5').style('opacity',.7));
 620 | 
 621 |   // Gradient fill
 622 |   const gid = 'grad-' + Math.random().toString(36).slice(2,8);
 623 |   const defs = svg.append('defs');
 624 |   const grad = defs.append('linearGradient').attr('id',gid).attr('x1','0').attr('y1','0').attr('x2','0').attr('y2','1');
 625 |   grad.append('stop').attr('offset','0%').attr('stop-color',c).attr('stop-opacity',0.28);
 626 |   grad.append('stop').attr('offset','100%').attr('stop-color',c).attr('stop-opacity',0.01);
 627 | 
 628 |   // Area + line
 629 |   const area = d3.area().x(d=>x(new Date(d[0]))).y0(h).y1(d=>y(d[1])).curve(d3.curveMonotoneX);
 630 |   const line = d3.line().x(d=>x(new Date(d[0]))).y(d=>y(d[1])).curve(d3.curveMonotoneX);
 631 |   g.append('path').datum(data).attr('fill',`url(#${gid})`).attr('d',area);
 632 |   g.append('path').datum(data).attr('fill','none').attr('stroke',c).attr('stroke-width',2).attr('d',line);
 633 | 
 634 |   // Axes
 635 |   const ticks = w < 400 ? 4 : 6;
 636 |   g.append('g').attr('transform',`translate(0,${h})`)
 637 |     .call(d3.axisBottom(x).ticks(ticks))
 638 |     .call(ax=>ax.select('.domain').attr('stroke','#1C1C2E'))
 639 |     .call(ax=>ax.selectAll('.tick text').style('fill','#95A0BA').style('font-family','JetBrains Mono,monospace').style('font-size','9px'));
 640 |   g.append('g')
 641 |     .call(d3.axisLeft(y).ticks(6).tickFormat(v=>cfg.fmtAxis(v)))
 642 |     .call(ax=>ax.select('.domain').attr('stroke','#1C1C2E'))
 643 |     .call(ax=>ax.selectAll('.tick text').style('fill','#95A0BA').style('font-family','JetBrains Mono,monospace').style('font-size','9px'));
 644 | 
 645 |   // ── Crosshair + Tooltip ──────────────────────────────────────────────
 646 |   const bisect = d3.bisector(d=>d[0]).left;
 647 | 
 648 |   const vLine = g.append('line').attr('y1',0).attr('y2',h)
 649 |     .style('stroke','rgba(255,255,255,.3)').style('stroke-width',1)
 650 |     .style('stroke-dasharray','3,3').style('opacity',0).style('pointer-events','none');
 651 |   const hLine = g.append('line').attr('x1',0).attr('x2',w)
 652 |     .style('stroke','rgba(255,255,255,.3)').style('stroke-width',1)
 653 |     .style('stroke-dasharray','3,3').style('opacity',0).style('pointer-events','none');
 654 |   const dot = g.append('circle').attr('r',4)
 655 |     .attr('fill',c).attr('stroke','#080810').attr('stroke-width',2)
 656 |     .style('opacity',0).style('pointer-events','none');
 657 | 
 658 |   const tt = d3.select(wrap).append('div')
 659 |     .style('position','absolute').style('background','rgba(13,17,24,.96)')
 660 |     .style('border',`1px solid ${c}33`).style('border-radius','8px')
 661 |     .style('padding','7px 11px').style('font-family','JetBrains Mono,monospace')
 662 |     .style('font-size','11px').style('color','#EEF2FF')
 663 |     .style('pointer-events','none').style('z-index','100')
 664 |     .style('opacity','0').style('min-width','130px').style('white-space','nowrap');
 665 | 
 666 |   g.append('rect').attr('width',w).attr('height',h)
 667 |     .style('fill','none').style('pointer-events','all')
 668 |     .on('mousemove', function(ev) {
 669 |       const [mx] = d3.pointer(ev);
 670 |       const xms  = x.invert(mx).getTime();
 671 |       const idx  = Math.min(bisect(data, xms, 1), data.length-1);
 672 |       const d    = data[idx];
 673 |       const px   = x(new Date(d[0]));
 674 |       const py   = y(d[1]);
 675 |       vLine.attr('x1',px).attr('x2',px).style('opacity',.6);
 676 |       hLine.attr('y1',py).attr('y2',py).style('opacity',.6);
 677 |       dot.attr('cx',px).attr('cy',py).style('opacity',1);
 678 |       const ds = new Date(d[0]).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});
 679 |       const lo = mg.left + px + (px > w*.65 ? -155 : 14);
 680 |       const to = mg.top  + py - 33;
 681 |       tt.html(`<div style="color:#95A0BA;font-size:8px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:3px">${ds}</div>
 682 |                <div style="font-size:15px;font-weight:900;color:${c}">${cfg.fmtVal(d[1])}</div>`)
 683 |         .style('left', lo + 'px').style('top', to + 'px').style('opacity','1');
 684 |     })
 685 |     .on('mouseleave',function(){
 686 |       vLine.style('opacity',0); hLine.style('opacity',0);
 687 |       dot.style('opacity',0);   tt.style('opacity','0');
 688 |     });
 689 | }
 690 | 
 691 | /* ── Data fetchers ────────────────────────────────────────────────────── */
 692 | async function fetchData(chartKey, period) {
 693 |   const cfg = CHART_CONFIG[chartKey];
 694 |   if (chartKey === 'mempool') {
 695 |     try {
 696 |       const r = await fetch('/api/charts/mempool-data');
 697 |       if (!r.ok) return null;
 698 |       const d = await r.json();
 699 |       const mb = (d.mempool?.vsize || 0) / 1e6;
 700 |       return [[Date.now(), Math.round(mb * 100) / 100]];
 701 |     } catch { return null; }
 702 |   }
 703 |   if (chartKey === 'fees') {
 704 |     try {
 705 |       const r = await fetch('/api/charts/fee-history');
 706 |       if (!r.ok) return null;
 707 |       const raw = await r.json();
 708 |       if (!Array.isArray(raw)) return null;
 709 |       return raw
 710 |         .filter(b => b.avgFee != null && b.timestamp != null)
 711 |         .map(b => [b.timestamp * 1000, b.avgFee])
 712 |         .slice(-180);
 713 |     } catch { return null; }
 714 |   }
 715 |   try {
 716 |     const r = await fetch(`${cfg.apiPath}?period=${encodeURIComponent(period)}`);
 717 |     if (!r.ok) return null;
 718 |     const d = await r.json();
 719 |     return Array.isArray(d.data) && d.data.length ? d.data : null;
 720 |   } catch { return null; }
 721 | }
 722 | 
 723 | /* ── Main loader ──────────────────────────────────────────────────────── */
 724 | async function loadChart(chartKey, period, silent = false) {
 725 |   if (state.busy) return;
 726 |   state.busy = true; state.chart = chartKey; state.period = period;
 727 |   const cfg = CHART_CONFIG[chartKey];
 728 | 
 729 |   document.getElementById('chart-title').textContent    = cfg.title;
 730 |   document.getElementById('chart-subtitle').textContent = cfg.subtitle;
 731 |   aiBox.classList.remove('show');
 732 | 
 733 |   // Active states
 734 |   document.querySelectorAll('.chart-item').forEach(el => el.classList.toggle('active', el.dataset.chart === chartKey));
 735 |   document.querySelectorAll('.mobile-tab').forEach(el => el.classList.toggle('active', el.dataset.chart === chartKey));
 736 |   document.querySelectorAll('.tf-btn').forEach(el => el.classList.toggle('active', el.dataset.tf === period));
 737 | 
 738 |   if (!silent) { showErr(false); showLoad(true); }
 739 | 
 740 |   try {
 741 |     const data = await fetchData(chartKey, period);
 742 |     if (!data || !data.length) { showLoad(false); showErr(true); state.busy = false; return; }
 743 |     state.data = data;
 744 |     showLoad(false); showErr(false);
 745 |     renderD3(data, cfg);
 746 |     renderStats(data);
 747 |     updateSidebarItem(chartKey, data);
 748 |     srcTag.textContent = `SOURCE: ${
 749 |       cfg.apiPath
 750 |         ? (cfg.apiPath.includes('price') ? 'CoinGecko' :
 751 |            cfg.apiPath.includes('hash') || cfg.apiPath.includes('diff') ? 'mempool.space' :
 752 |            cfg.apiPath.includes('mvrv') || cfg.apiPath.includes('realized') ? 'CoinMetrics community' :
 753 |            cfg.apiPath.includes('fg') ? 'alternative.me' : 'Protocol Pulse')
 754 |         : 'mempool.space'
 755 |     } · ${data.length} POINTS · ${period.toUpperCase()}`;
 756 |   } catch(e) { console.error('loadChart error:', e); showLoad(false); showErr(true); }
 757 |   state.busy = false;
 758 | }
 759 | 
 760 | /* ── Event listeners ──────────────────────────────────────────────────── */
 761 | document.querySelectorAll('.chart-item').forEach(el => {
 762 |   el.addEventListener('click', () => {
 763 |     const p = el.dataset.period || CHART_CONFIG[el.dataset.chart]?.defaultPeriod || '7d';
 764 |     loadChart(el.dataset.chart, p);
 765 |     document.querySelectorAll('.tf-btn').forEach(b => b.classList.toggle('active', b.dataset.tf === p));
 766 |   });
 767 | });
 768 | document.querySelectorAll('.mobile-tab').forEach(el => {
 769 |   el.addEventListener('click', () => {
 770 |     const p = el.dataset.period || CHART_CONFIG[el.dataset.chart]?.defaultPeriod || '7d';
 771 |     loadChart(el.dataset.chart, p);
 772 |   });
 773 | });
 774 | document.querySelectorAll('.tf-btn').forEach(b => {
 775 |   b.addEventListener('click', () => {
 776 |     document.querySelectorAll('.tf-btn').forEach(x => x.classList.remove('active'));
 777 |     b.classList.add('active');
 778 |     loadChart(state.chart, b.dataset.tf);
 779 |   });
 780 | });
 781 | 
 782 | document.getElementById('btn-ai').addEventListener('click', async () => {
 783 |   if (!state.data || !state.data.length) return;
 784 |   const cfg  = CHART_CONFIG[state.chart];
 785 |   const vals = state.data.map(d => d[1]);
 786 |   aiBox.classList.add('show'); aiTxt.textContent = 'Analysing…';
 787 |   try {
 788 |     const r = await fetch('/api/charts/ai-explain', {
 789 |       method: 'POST', headers: {'Content-Type':'application/json'},
 790 |       body: JSON.stringify({
 791 |         chart_type: state.chart,
 792 |         chart_data: {
 793 |           current: vals[vals.length-1], period_high: Math.max(...vals),
 794 |           period_low: Math.min(...vals), period: state.period,
 795 |           unit: cfg.unit, data_points: vals.length,
 796 |         },
 797 |         question: `Analyse this ${cfg.title} chart for the ${state.period} period.`,
 798 |       })
 799 |     });
 800 |     const d = await r.json();
 801 |     aiTxt.textContent = d.explanation || 'Analysis unavailable.';
 802 |   } catch { aiTxt.textContent = 'AI analysis temporarily unavailable.'; }
 803 | });
 804 | 
 805 | document.getElementById('btn-og').addEventListener('click', () => {
 806 |   const c = ['price','hashrate','fear-greed'].includes(state.chart) ? state.chart : 'price';
 807 |   window.open(`/api/charts/og-image?chart=${c}&period=${state.period}`, '_blank');
 808 | });
 809 | 
 810 | /* ── Resize re-render ─────────────────────────────────────────────────── */
 811 | let _rt = null;
 812 | window.addEventListener('resize', () => {
 813 |   clearTimeout(_rt);
 814 |   _rt = setTimeout(() => { if (state.data) renderD3(state.data, CHART_CONFIG[state.chart]); }, 250);
 815 | });
 816 | 
 817 | /* ── Stat bar price refresh ───────────────────────────────────────────── */
 818 | async function refreshPrice() {
 819 |   try {
 820 |     const r = await fetch('/api/charts/price-history?days=1');
 821 |     if (!r.ok) return;
 822 |     const d = await r.json();
 823 |     const pts = d.prices || [];
 824 |     if (pts.length < 2) return;
 825 |     const last  = pts[pts.length-1][1];
 826 |     const first = pts[0][1];
 827 |     const pct   = ((last - first) / first) * 100;
 828 |     const el = document.getElementById('sb-price');
 829 |     if (el) el.textContent = '$' + d3.format(',.0f')(last);
 830 |     const de = document.getElementById('sb-change');
 831 |     if (de) de.innerHTML = fmtDelta(pct);
 832 |   } catch {}
 833 | }
 834 | 
 835 | /* ── Background prefetch sidebar values ──────────────────────────────── */
 836 | async function prefetchSidebar() {
 837 |   const keys = ['price','hashrate','difficulty','mvrv','realized-price','s2f','fear-greed'];
 838 |   for (const key of keys) {
 839 |     try {
 840 |       const cfg  = CHART_CONFIG[key];
 841 |       const data = await fetchData(key, cfg.defaultPeriod);
 842 |       if (data && data.length) updateSidebarItem(key, data);
 843 |     } catch {}
 844 |     await new Promise(r => setTimeout(r, 450));
 845 |   }
 846 | }
 847 | 
 848 | /* ── Init ─────────────────────────────────────────────────────────────── */
 849 | (async () => {
 850 |   await loadChart('price', '7d');
 851 |   await refreshPrice();
 852 |   prefetchSidebar();
 853 |   setInterval(refreshPrice, 60000);
 854 | })();
 855 | </script>
 856 | {% endblock %}
 857 | 
```

### File: routes_articles.py (259 lines)
```
   1 | """
   2 | SESSION 10 — ARTICLE REBUILD: helpers + new API blueprint
   3 | Helper functions are imported by routes.py to enrich the existing page handlers.
   4 | New API endpoint /api/v2/articles is registered here as a Blueprint.
   5 | """
   6 | 
   7 | from __future__ import annotations
   8 | 
   9 | import logging
  10 | import re
  11 | from datetime import datetime
  12 | 
  13 | from flask import Blueprint, jsonify, request
  14 | 
  15 | logger = logging.getLogger(__name__)
  16 | 
  17 | # ─── Article helper functions (imported by routes.py) ─────────────────────────
  18 | 
  19 | CATEGORY_COLORS: dict[str, str] = {
  20 |     "mining": "#f7931a",
  21 |     "regulation": "#dc2626",
  22 |     "etfs": "#3b82f6",
  23 |     "lightning": "#eab308",
  24 |     "macro": "#a855f7",
  25 |     "technical": "#06b6d4",
  26 |     "bitcoin": "#f97316",
  27 |     "editorial": "#10b981",
  28 |     "defi": "#6366f1",
  29 |     "web3": "#8b5cf6",
  30 |     "security": "#ef4444",
  31 |     "institutional": "#0ea5e9",
  32 |     "markets": "#14b8a6",
  33 |     "adoption": "#22c55e",
  34 |     "default": "#9ca3af",
  35 | }
  36 | 
  37 | CATEGORY_GRADIENTS: dict[str, str] = {
  38 |     "mining": "linear-gradient(135deg,#1a1200,#2d1e00)",
  39 |     "regulation": "linear-gradient(135deg,#1a0a0a,#2d1515)",
  40 |     "etfs": "linear-gradient(135deg,#0a1628,#0f2545)",
  41 |     "lightning": "linear-gradient(135deg,#1a1500,#2d2400)",
  42 |     "macro": "linear-gradient(135deg,#120a1a,#1f1030)",
  43 |     "technical": "linear-gradient(135deg,#0a1a1a,#0f2d2d)",
  44 |     "bitcoin": "linear-gradient(135deg,#1a0e00,#2d1800)",
  45 |     "editorial": "linear-gradient(135deg,#0a1a12,#0f2d1e)",
  46 |     "default": "linear-gradient(135deg,#0d0d1a,#1a1a2e)",
  47 | }
  48 | 
  49 | SENTIMENT_MAP: dict[str, dict] = {
  50 |     "bullish": {"label": "BULLISH", "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
  51 |     "bearish": {"label": "BEARISH", "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
  52 |     "neutral": {"label": "NEUTRAL", "color": "#6b7280", "bg": "rgba(107,114,128,0.12)"},
  53 |     "positive": {"label": "BULLISH", "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
  54 |     "negative": {"label": "BEARISH", "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
  55 | }
  56 | 
  57 | _BULLISH_SIGNALS = {
  58 |     "ath", "all-time high", "rally", "surge", "breakout", "adoption", "etf approved",
  59 |     "approval", "institutional", "accumulate", "bullish", "hodl", "all time high",
  60 |     "record", "positive", "growth", "expand", "partnership", "launch", "inflows",
  61 | }
  62 | _BEARISH_SIGNALS = {
  63 |     "ban", "crackdown", "hack", "exploit", "fraud", "scam", "crash", "dump",
  64 |     "lawsuit", "sec charges", "warning", "concern", "liquidation", "fud",
  65 |     "decline", "bearish", "sell-off", "capitulation", "regulation ban",
  66 | }
  67 | 
  68 | 
  69 | def article_get_image(article) -> str:
  70 |     """Return best available image URL. Returns empty string if none found (template handles fallback)."""
  71 |     for attr in ("cover_image_url", "header_image_url"):
  72 |         url = (getattr(article, attr, None) or "").strip()
  73 |         if url and url.startswith("http"):
  74 |             return url
  75 |         if url and url.startswith("/static/") and "default-header" not in url:
  76 |             return url
  77 |     return ""
  78 | 
  79 | 
  80 | def article_get_sentiment(article) -> dict:
  81 |     """Return sentiment dict: label, color, bg. Never crashes."""
  82 |     try:
  83 |         reports = getattr(article, "sentiment_report", None)
  84 |         if reports:
  85 |             if isinstance(reports, list) and reports:
  86 |                 report = sorted(reports, key=lambda r: r.id, reverse=True)[0]
  87 |             else:
  88 |                 report = reports
  89 |             if report:
  90 |                 if report.overall_sentiment:
  91 |                     key = report.overall_sentiment.lower().strip()
  92 |                     if key in SENTIMENT_MAP:
  93 |                         return SENTIMENT_MAP[key]
  94 |                 if report.sentiment_score is not None:
  95 |                     if report.sentiment_score > 55:
  96 |                         return SENTIMENT_MAP["bullish"]
  97 |                     if report.sentiment_score < 40:
  98 |                         return SENTIMENT_MAP["bearish"]
  99 |                     return SENTIMENT_MAP["neutral"]
 100 |     except Exception:
 101 |         pass
 102 | 
 103 |     # Keyword inference from title + summary + tags
 104 |     text = " ".join([
 105 |         (getattr(article, "title", None) or ""),
 106 |         (getattr(article, "summary", None) or "")[:200],
 107 |         (getattr(article, "tags", None) or ""),
 108 |     ]).lower()
 109 |     bull = sum(1 for w in _BULLISH_SIGNALS if w in text)
 110 |     bear = sum(1 for w in _BEARISH_SIGNALS if w in text)
 111 |     if bull > bear and bull >= 2:
 112 |         return SENTIMENT_MAP["bullish"]
 113 |     if bear > bull and bear >= 2:
 114 |         return SENTIMENT_MAP["bearish"]
 115 |     return SENTIMENT_MAP["neutral"]
 116 | 
 117 | 
 118 | def article_get_read_time(article) -> int:
 119 |     """Estimate read time in minutes at 200 wpm."""
 120 |     content = getattr(article, "content", None) or ""
 121 |     word_count = len(re.sub(r"<[^>]+>", "", content).split())
 122 |     return max(1, round(word_count / 200))
 123 | 
 124 | 
 125 | def article_get_related(article, db, Article, limit: int = 3) -> list:
 126 |     """Always returns `limit` articles. Same category first, then any recent."""
 127 |     related = []
 128 |     try:
 129 |         if article.category:
 130 |             related = (
 131 |                 Article.query
 132 |                 .filter(
 133 |                     Article.id != article.id,
 134 |                     Article.published.is_(True),
 135 |                     Article.category == article.category,
 136 |                 )
 137 |                 .order_by(Article.created_at.desc())
 138 |                 .limit(limit)
 139 |                 .all()
 140 |             )
 141 |         if len(related) < limit:
 142 |             exc_ids = [article.id] + [r.id for r in related]
 143 |             pad = (
 144 |                 Article.query
 145 |                 .filter(
 146 |                     ~Article.id.in_(exc_ids),
 147 |                     Article.published.is_(True),
 148 |                 )
 149 |                 .order_by(Article.created_at.desc())
 150 |                 .limit(limit - len(related))
 151 |                 .all()
 152 |             )
 153 |             related.extend(pad)
 154 |     except Exception as exc:
 155 |         logger.warning("article_get_related failed: %s", exc)
 156 |     return related[:limit]
 157 | 
 158 | 
 159 | def article_cat_color(category: str | None) -> str:
 160 |     key = (category or "default").lower()
 161 |     return CATEGORY_COLORS.get(key, CATEGORY_COLORS["default"])
 162 | 
 163 | 
 164 | def article_cat_gradient(category: str | None) -> str:
 165 |     key = (category or "default").lower()
 166 |     return CATEGORY_GRADIENTS.get(key, CATEGORY_GRADIENTS["default"])
 167 | 
 168 | 
 169 | def build_article_data(articles, sentiment_fn=None, img_fn=None) -> list[dict]:
 170 |     """Build article_data list for template rendering."""
 171 |     result = []
 172 |     for a in articles:
 173 |         result.append({
 174 |             "article": a,
 175 |             "image_url": article_get_image(a),
 176 |             "sentiment": article_get_sentiment(a),
 177 |             "read_time": article_get_read_time(a),
 178 |             "cat_color": article_cat_color(a.category),
 179 |             "cat_gradient": article_cat_gradient(a.category),
 180 |         })
 181 |     return result
 182 | 
 183 | 
 184 | # ─── Blueprint: new JSON API endpoint ─────────────────────────────────────────
 185 | 
 186 | articles_api_bp = Blueprint("articles_api_bp", __name__)
 187 | 
 188 | 
 189 | @articles_api_bp.route("/api/v2/articles")
 190 | def api_v2_articles():
 191 |     """
 192 |     Articles JSON API — paginated, filterable, searchable.
 193 |     Supports: ?page=N&per_page=24&category=Mining&q=searchterm
 194 |     Used by the Load More button and client-side search on /articles.
 195 |     """
 196 |     from app import db
 197 |     from models import Article
 198 | 
 199 |     try:
 200 |         page = max(1, request.args.get("page", 1, type=int))
 201 |         per_page = min(48, request.args.get("per_page", 24, type=int))
 202 |         category = request.args.get("category", "").strip()
 203 |         search = request.args.get("q", "").strip()
 204 | 
 205 |         q = Article.query.filter(Article.published.is_(True))
 206 |         total = q.count()
 207 |         if total == 0:  # dev fallback
 208 |             q = Article.query
 209 |             total = q.count()
 210 | 
 211 |         if category and category.lower() != "all":
 212 |             q = q.filter(Article.category.ilike(f"%{category}%"))
 213 | 
 214 |         if search:
 215 |             like = f"%{search}%"
 216 |             q = q.filter(
 217 |                 db.or_(
 218 |                     Article.title.ilike(like),
 219 |                     Article.summary.ilike(like),
 220 |                     Article.tags.ilike(like),
 221 |                 )
 222 |             )
 223 | 
 224 |         q = q.order_by(Article.created_at.desc())
 225 |         paged = q.paginate(page=page, per_page=per_page, error_out=False)
 226 | 
 227 |         def to_dict(a):
 228 |             img = article_get_image(a)
 229 |             sent = article_get_sentiment(a)
 230 |             return {
 231 |                 "id": a.id,
 232 |                 "title": a.title or "",
 233 |                 "summary": (a.summary or re.sub(r"<[^>]+>", "", a.content or "")[:280]),
 234 |                 "category": a.category or "Bitcoin",
 235 |                 "category_color": article_cat_color(a.category),
 236 |                 "category_gradient": article_cat_gradient(a.category),
 237 |                 "image_url": img,
 238 |                 "sentiment_label": sent["label"],
 239 |                 "sentiment_color": sent["color"],
 240 |                 "sentiment_bg": sent["bg"],
 241 |                 "source": a.author or a.source_type or "Protocol Pulse",
 242 |                 "read_time": article_get_read_time(a),
 243 |                 "created_at": a.created_at.isoformat() if a.created_at else "",
 244 |                 "url": f"/articles/{a.id}",
 245 |                 "is_featured": bool(a.featured),
 246 |             }
 247 | 
 248 |         return jsonify({
 249 |             "articles": [to_dict(a) for a in paged.items],
 250 |             "page": page,
 251 |             "per_page": per_page,
 252 |             "total": paged.total,
 253 |             "total_pages": paged.pages,
 254 |             "has_more": paged.has_next,
 255 |         })
 256 |     except Exception as err:
 257 |         logger.error("api_v2_articles error: %s", err)
 258 |         return jsonify({"articles": [], "error": str(err), "has_more": False}), 500
 259 | 
```

### File: templates/article_detail.html (461 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}{{ article.title }} — Protocol Pulse{% endblock %}
   4 | 
   5 | {% block meta_description %}{{ article.seo_description or article.summary or article.content[:160]|striptags }}{% endblock %}
   6 | 
   7 | {% block og_meta %}
   8 | <meta property="og:title" content="{{ article.title }}">
   9 | <meta property="og:description" content="{{ article.summary or article.content[:200]|striptags }}">
  10 | <meta property="og:image" content="{{ header_image_url or url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}">
  11 | <meta property="og:url" content="{{ request.url }}">
  12 | <meta property="og:type" content="article">
  13 | <meta property="og:site_name" content="Protocol Pulse">
  14 | <meta property="article:published_time" content="{{ article.published_at.isoformat() if article.published_at else article.created_at.isoformat() }}">
  15 | <meta property="article:section" content="{{ article.category or 'Bitcoin' }}">
  16 | <meta name="twitter:card" content="summary_large_image">
  17 | <meta name="twitter:site" content="@ProtocolPulse">
  18 | <meta name="twitter:title" content="{{ article.title }}">
  19 | <meta name="twitter:description" content="{{ article.summary or article.content[:200]|striptags }}">
  20 | <meta name="twitter:image" content="{{ header_image_url or url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}">
  21 | {% endblock %}
  22 | 
  23 | {% block schema %}
  24 | <script type="application/ld+json">
  25 | {
  26 |   "@context":"https://schema.org","@type":"NewsArticle",
  27 |   "headline":"{{ article.title }}",
  28 |   "description":"{{ article.summary or article.content[:200]|striptags }}",
  29 |   "image":"{{ header_image_url or '' }}",
  30 |   "datePublished":"{{ article.published_at.isoformat() if article.published_at else article.created_at.isoformat() }}",
  31 |   "dateModified":"{{ article.updated_at.isoformat() if article.updated_at else article.created_at.isoformat() }}",
  32 |   "author":{"@type":"Organization","name":"Protocol Pulse","url":"https://protocolpulse.io"},
  33 |   "publisher":{"@type":"Organization","name":"Protocol Pulse","logo":{"@type":"ImageObject","url":"{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}"}},
  34 |   "mainEntityOfPage":{"@type":"WebPage","@id":"{{ request.url }}"},
  35 |   "articleSection":"{{ article.category or 'Bitcoin' }}",
  36 |   "keywords":"{{ article.tags or 'Bitcoin, cryptocurrency' }}"
  37 | }
  38 | </script>
  39 | <script type="application/ld+json">
  40 | {
  41 |   "@context":"https://schema.org","@type":"BreadcrumbList",
  42 |   "itemListElement":[
  43 |     {"@type":"ListItem","position":1,"name":"Home","item":"{{ request.url_root }}"},
  44 |     {"@type":"ListItem","position":2,"name":"Intelligence","item":"{{ request.url_root }}articles"},
  45 |     {"@type":"ListItem","position":3,"name":"{{ article.title }}"}
  46 |   ]
  47 | }
  48 | </script>
  49 | {% endblock %}
  50 | 
  51 | {% block head %}
  52 | <style>
  53 | /* SESSION 10 — Article Detail */
  54 | :root{
  55 |   --ad-bg:#030303;--ad-surface:#0a0a0a;--ad-surface2:#111;
  56 |   --ad-border:rgba(255,255,255,0.06);--ad-border2:rgba(255,255,255,0.1);
  57 |   --ad-red:#dc2626;--ad-red-dim:rgba(220,38,38,0.08);
  58 |   --ad-gold:#f7931a;--ad-gold-dim:rgba(247,147,26,0.1);
  59 |   --ad-text:#f0f0f0;--ad-text2:#999;--ad-text3:#5a5a5a;
  60 |   --ad-mono:'JetBrains Mono',monospace;
  61 |   --ad-serif:'Crimson Pro',Georgia,serif;
  62 |   --ad-sans:'DM Sans',system-ui,sans-serif;
  63 |   --ad-content:720px;
  64 | }
  65 | body{background:var(--ad-bg);}
  66 | /* Reading progress */
  67 | #adProgress{position:fixed;top:0;left:0;width:0%;height:3px;background:linear-gradient(90deg,var(--ad-red),var(--ad-gold));z-index:1100;transition:width .1s linear;}
  68 | /* Hero */
  69 | .ad-hero{width:100%;height:420px;position:relative;overflow:hidden;background:var(--ad-surface);}
  70 | .ad-hero img{width:100%;height:100%;object-fit:cover;display:block;}
  71 | .ad-hero-grad{width:100%;height:100%;display:flex;align-items:center;justify-content:center;}
  72 | .ad-hero-grad i{font-size:4rem;opacity:.08;color:#fff;}
  73 | .ad-hero-overlay{position:absolute;inset:0;background:linear-gradient(transparent 35%,rgba(3,3,3,.9) 100%);}
  74 | @media(max-width:768px){.ad-hero{height:260px;}}
  75 | /* Container */
  76 | .ad-container{max-width:1200px;margin:0 auto;padding:0 1.5rem;}
  77 | /* Breadcrumb */
  78 | .ad-breadcrumb{padding:1.2rem 0;font-family:var(--ad-mono);font-size:.6rem;color:var(--ad-text3);letter-spacing:.04em;}
  79 | .ad-breadcrumb a{color:var(--ad-text3);text-decoration:none;transition:color .15s;}
  80 | .ad-breadcrumb a:hover{color:var(--ad-gold);}
  81 | .ad-breadcrumb span{margin:0 8px;opacity:.3;}
  82 | /* Article header */
  83 | .ad-header{padding:2rem 0 1.5rem;max-width:var(--ad-content);}
  84 | .ad-meta-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:1.2rem;}
  85 | .ad-badge{font-family:var(--ad-mono);font-size:.5rem;text-transform:uppercase;letter-spacing:.1em;padding:4px 10px;border-radius:3px;border:1px solid;font-weight:700;white-space:nowrap;}
  86 | .ad-badge-cat{background:rgba(0,0,0,.5);}
  87 | .ad-badge-sent{/* dynamic via inline style */}
  88 | .ad-badge-premium{background:rgba(247,147,26,.1);border-color:rgba(247,147,26,.3);color:var(--ad-gold);}
  89 | .ad-badge-time{font-family:var(--ad-mono);font-size:.56rem;color:var(--ad-text3);}
  90 | /* Title — gold monospace per SESSION 10 spec */
  91 | .ad-title{font-family:var(--ad-mono);font-size:clamp(1.5rem,3.5vw,2.4rem);font-weight:700;line-height:1.2;letter-spacing:-.01em;color:var(--ad-gold);margin:0 0 1rem;max-width:var(--ad-content);}
  92 | /* Meta row */
  93 | .ad-meta-row{display:flex;align-items:center;gap:12px;font-family:var(--ad-mono);font-size:.62rem;color:var(--ad-text3);margin-bottom:1.2rem;flex-wrap:wrap;}
  94 | .ad-meta-sep{opacity:.25;}
  95 | /* Share */
  96 | .ad-share{display:flex;gap:8px;margin-bottom:0;}
  97 | .ad-share-btn{width:34px;height:34px;display:flex;align-items:center;justify-content:center;background:var(--ad-surface);border:1px solid var(--ad-border2);border-radius:5px;color:var(--ad-text3);cursor:pointer;transition:all .15s;font-size:.8rem;font-family:var(--ad-mono);}
  98 | .ad-share-btn:hover{border-color:var(--ad-gold);color:var(--ad-gold);}
  99 | /* Layout */
 100 | .ad-layout{display:grid;grid-template-columns:1fr;gap:48px;padding:0 0 3rem;}
 101 | @media(min-width:1024px){.ad-layout{grid-template-columns:minmax(0,var(--ad-content)) 260px;}}
 102 | /* TL;DR */
 103 | .ad-tldr{max-width:var(--ad-content);margin-bottom:1.5rem;border:1px solid rgba(247,147,26,.2);border-radius:8px;overflow:hidden;background:rgba(247,147,26,.03);}
 104 | .ad-tldr-toggle{width:100%;display:flex;align-items:center;justify-content:space-between;padding:11px 16px;background:none;border:none;cursor:pointer;color:var(--ad-text);font-family:var(--ad-mono);font-size:.68rem;font-weight:700;letter-spacing:.06em;text-align:left;transition:background .15s;}
 105 | .ad-tldr-toggle:hover{background:rgba(247,147,26,.05);}
 106 | .ad-tldr-label{display:flex;align-items:center;gap:8px;color:var(--ad-gold);text-transform:uppercase;letter-spacing:.1em;}
 107 | .ad-tldr-caret{font-size:.55rem;color:var(--ad-text3);transition:transform .2s;}
 108 | .ad-tldr-toggle[aria-expanded="true"] .ad-tldr-caret{transform:rotate(180deg);}
 109 | .ad-tldr-body{padding:0 16px 14px;font-size:.9375rem;line-height:1.6;color:var(--ad-text2);border-top:1px solid rgba(247,147,26,.1);}
 110 | /* Key Takeaways */
 111 | .ad-takeaways{padding:20px 24px;background:rgba(247,147,26,.04);border:1px solid rgba(247,147,26,.15);border-radius:8px;margin-bottom:2rem;}
 112 | .ad-takeaways-hdr{display:flex;align-items:center;gap:8px;font-family:var(--ad-mono);font-size:.62rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ad-gold);margin-bottom:12px;}
 113 | .ad-takeaways-list{list-style:none;padding:0;margin:0;}
 114 | .ad-takeaways-list li{position:relative;padding-left:20px;margin-bottom:8px;font-size:.9375rem;color:var(--ad-text2);line-height:1.6;}
 115 | .ad-takeaways-list li::before{content:'';position:absolute;left:0;top:9px;width:6px;height:6px;background:var(--ad-gold);border-radius:50%;}
 116 | /* Article body */
 117 | .ad-body{max-width:var(--ad-content);font-size:1.0625rem;line-height:1.8;color:var(--ad-text2);}
 118 | .ad-body h1,.ad-body h2,.ad-body h3,.ad-body h4,.ad-body h5,.ad-body h6{color:var(--ad-text);margin:2em 0 .75em;font-weight:700;line-height:1.3;}
 119 | .ad-body h2{font-size:1.5rem;}.ad-body h3{font-size:1.25rem;}.ad-body h4{font-size:1.1rem;}
 120 | .ad-body p{margin:0 0 1.5em;}
 121 | .ad-body a{color:var(--ad-gold);text-decoration:underline;text-underline-offset:2px;}
 122 | .ad-body a:hover{opacity:.8;}
 123 | .ad-body img{max-width:100%;height:auto;border-radius:6px;margin:1.5em 0;}
 124 | .ad-body blockquote{border-left:3px solid var(--ad-gold);padding:16px 24px;margin:1.5em 0;background:var(--ad-gold-dim);border-radius:0 6px 6px 0;color:var(--ad-text);font-style:italic;}
 125 | .ad-body code{padding:2px 6px;background:var(--ad-surface2);border-radius:3px;font-family:var(--ad-mono);font-size:.9em;color:var(--ad-gold);}
 126 | .ad-body pre{padding:20px;background:var(--ad-surface);border:1px solid var(--ad-border);border-radius:6px;overflow-x:auto;margin:1.5em 0;}
 127 | .ad-body pre code{padding:0;background:none;color:var(--ad-text2);}
 128 | .ad-body ul,.ad-body ol{padding-left:24px;margin:0 0 1.5em;}
 129 | .ad-body li{margin-bottom:.5em;}
 130 | .ad-body table{width:100%;border-collapse:collapse;margin:1.5em 0;font-size:.9375rem;}
 131 | .ad-body th,.ad-body td{padding:10px 14px;border:1px solid var(--ad-border);text-align:left;}
 132 | .ad-body th{background:var(--ad-surface);color:var(--ad-text);font-weight:600;}
 133 | .ad-body hr{border:none;height:1px;background:var(--ad-border);margin:2em 0;}
 134 | /* Tags */
 135 | .ad-tags{display:flex;flex-wrap:wrap;gap:8px;padding:1.5rem 0;border-top:1px solid var(--ad-border);margin-top:2rem;}
 136 | .ad-tag{font-family:var(--ad-mono);font-size:.55rem;text-transform:uppercase;letter-spacing:.06em;padding:5px 11px;border-radius:4px;border:1px solid var(--ad-border);color:var(--ad-text3);text-decoration:none;transition:all .15s;}
 137 | .ad-tag:hover{border-color:var(--ad-gold);color:var(--ad-gold);}
 138 | /* Tip jar */
 139 | .ad-tipjar{padding:28px;background:var(--ad-surface);border:1px solid var(--ad-border);border-radius:10px;text-align:center;margin-top:2rem;}
 140 | .ad-tipjar h5{font-family:var(--ad-mono);font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--ad-text);margin:0 0 6px;}
 141 | .ad-tipjar p{font-size:.84rem;color:var(--ad-text3);margin:0 0 16px;}
 142 | .ad-tip-btns{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;}
 143 | .ad-tip-btn{padding:9px 18px;border-radius:20px;font-family:var(--ad-mono);font-size:.72rem;cursor:pointer;display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(247,147,26,.4);background:rgba(247,147,26,.1);color:var(--ad-gold);transition:all .2s;}
 144 | .ad-tip-btn:hover{background:rgba(247,147,26,.2);transform:translateY(-2px);box-shadow:0 4px 14px rgba(247,147,26,.2);}
 145 | .ad-tip-btn.featured{background:var(--ad-gold);color:#000;border-color:transparent;font-weight:700;}
 146 | .ad-tip-btn.featured:hover{box-shadow:0 4px 20px rgba(247,147,26,.4);}
 147 | /* Bottom actions */
 148 | .ad-bottom-actions{display:flex;align-items:center;justify-content:space-between;padding-top:1.5rem;margin-top:2rem;border-top:1px solid var(--ad-border);}
 149 | .ad-btn-ghost{font-family:var(--ad-mono);font-size:.65rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ad-text3);background:var(--ad-surface);border:1px solid var(--ad-border);padding:9px 18px;border-radius:5px;text-decoration:none;display:inline-flex;align-items:center;gap:8px;transition:all .15s;}
 150 | .ad-btn-ghost:hover{border-color:var(--ad-border2);color:var(--ad-text);}
 151 | /* Sidebar */
 152 | .ad-sidebar{display:flex;flex-direction:column;gap:20px;}
 153 | @media(min-width:1024px){.ad-sidebar{position:sticky;top:80px;align-self:start;}}
 154 | .ad-sidebar-panel{padding:16px;background:var(--ad-surface);border:1px solid var(--ad-border);border-radius:8px;}
 155 | .ad-sidebar-label{font-family:var(--ad-mono);font-size:.55rem;text-transform:uppercase;letter-spacing:.12em;color:var(--ad-text3);margin-bottom:12px;display:block;}
 156 | /* Sidebar ToC */
 157 | #adToc{display:none;}
 158 | .ad-toc-link{display:block;padding:6px 0 6px 12px;font-size:.78rem;color:var(--ad-text3);text-decoration:none;border-left:2px solid transparent;transition:all .15s;line-height:1.4;}
 159 | .ad-toc-link:hover,.ad-toc-link.active{color:var(--ad-gold);border-left-color:var(--ad-gold);}
 160 | .ad-toc-link.h3{padding-left:22px;font-size:.72rem;}
 161 | /* Sidebar related */
 162 | .ad-related-item{display:block;padding:10px 0;border-bottom:1px solid var(--ad-border);text-decoration:none;transition:all .15s;}
 163 | .ad-related-item:last-child{border-bottom:none;}
 164 | .ad-related-item:hover .ad-related-title{color:var(--ad-gold);}
 165 | .ad-related-title{font-size:.82rem;font-weight:600;color:var(--ad-text);line-height:1.4;margin-bottom:4px;}
 166 | .ad-related-meta{font-family:var(--ad-mono);font-size:.54rem;color:var(--ad-text3);}
 167 | /* MORE INTELLIGENCE bottom grid */
 168 | .ad-more-section{padding:2rem 0 3rem;border-top:1px solid var(--ad-border);margin-top:3rem;}
 169 | .ad-more-label{font-family:var(--ad-mono);font-size:.58rem;text-transform:uppercase;letter-spacing:.2em;color:var(--ad-red);display:flex;align-items:center;gap:8px;margin-bottom:1.5rem;}
 170 | .ad-more-label::before{content:'';width:4px;height:4px;background:var(--ad-red);border-radius:50%;box-shadow:0 0 6px var(--ad-red);}
 171 | .ad-more-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;}
 172 | @media(max-width:1024px){.ad-more-grid{grid-template-columns:repeat(2,1fr);}}
 173 | @media(max-width:640px){.ad-more-grid{grid-template-columns:1fr;}}
 174 | /* Related cards */
 175 | .ad-rel-card{background:var(--ad-surface);border:1px solid var(--ad-border);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit;transition:border-color .3s,transform .3s,box-shadow .3s;}
 176 | .ad-rel-card:hover{border-color:rgba(247,147,26,.3);transform:translateY(-3px);box-shadow:0 14px 40px rgba(0,0,0,.5);}
 177 | .ad-rel-img{height:160px;position:relative;overflow:hidden;background:#0d0d0d;flex-shrink:0;}
 178 | .ad-rel-img img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s;}
 179 | .ad-rel-card:hover .ad-rel-img img{transform:scale(1.04);}
 180 | .ad-rel-img-grad{width:100%;height:100%;display:flex;align-items:center;justify-content:center;}
 181 | .ad-rel-img-grad i{font-size:2rem;opacity:.1;color:#fff;}
 182 | .ad-rel-badges{position:absolute;top:8px;left:8px;right:8px;display:flex;justify-content:space-between;align-items:flex-start;gap:4px;}
 183 | .ad-rel-badge{font-family:var(--ad-mono);font-size:.48rem;text-transform:uppercase;letter-spacing:.08em;padding:3px 7px;border-radius:3px;border:1px solid;backdrop-filter:blur(4px);background:rgba(0,0,0,.6);font-weight:700;white-space:nowrap;}
 184 | .ad-rel-body{padding:1rem 1.1rem 1.1rem;display:flex;flex-direction:column;flex:1;}
 185 | .ad-rel-title{font-family:var(--ad-mono);font-size:.88rem;font-weight:700;line-height:1.35;color:var(--ad-text);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;transition:color .2s;}
 186 | .ad-rel-card:hover .ad-rel-title{color:var(--ad-gold);}
 187 | .ad-rel-meta{font-size:.6rem;color:var(--ad-text3);margin-top:auto;padding-top:.6rem;font-family:var(--ad-mono);}
 188 | /* Video embed */
 189 | .ad-video-wrap{position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;margin:1.5em 0;}
 190 | .ad-video-wrap iframe{position:absolute;top:0;left:0;width:100%;height:100%;}
 191 | /* Mobile */
 192 | @media(max-width:767px){
 193 |   .ad-container{padding:0 1rem;}
 194 |   .ad-title{font-size:1.4rem;}
 195 |   .ad-body{font-size:1rem;}
 196 |   .ad-tipjar{padding:20px 16px;}
 197 |   .ad-bottom-actions{flex-direction:column;align-items:flex-start;gap:12px;}
 198 | }
 199 | </style>
 200 | {% endblock %}
 201 | 
 202 | {% block content %}
 203 | <div id="adProgress"></div>
 204 | 
 205 | <!-- Hero -->
 206 | <div class="ad-hero">
 207 |   {% if header_image_url and header_image_url != '/static/images/default-header.png' %}
 208 |   <img src="{{ header_image_url }}" alt="{{ article.title }}"
 209 |     onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
 210 |   <div class="ad-hero-grad" style="background:{{ cat_gradient }};display:none;">
 211 |     <i class="fas fa-broadcast-tower"></i>
 212 |   </div>
 213 |   {% else %}
 214 |   <div class="ad-hero-grad" style="background:{{ cat_gradient }};">
 215 |     <i class="fas fa-broadcast-tower"></i>
 216 |   </div>
 217 |   {% endif %}
 218 |   <div class="ad-hero-overlay"></div>
 219 | </div>
 220 | 
 221 | <div class="ad-container">
 222 |   <!-- Breadcrumb -->
 223 |   <nav class="ad-breadcrumb" aria-label="Breadcrumb">
 224 |     <a href="/">Home</a><span>/</span>
 225 |     <a href="/articles">Intelligence</a><span>/</span>
 226 |     {{ article.title[:55] }}{% if article.title|length > 55 %}...{% endif %}
 227 |   </nav>
 228 | 
 229 |   <!-- Header -->
 230 |   <header class="ad-header">
 231 |     <div class="ad-meta-top">
 232 |       <span class="ad-badge ad-badge-cat" style="color:{{ cat_color }};border-color:{{ cat_color }}40;">{{ article.category or 'Bitcoin' }}</span>
 233 |       {% if sentiment %}
 234 |       <span class="ad-badge ad-badge-sent" style="color:{{ sentiment.color }};border-color:{{ sentiment.color }}40;background:{{ sentiment.bg }};">{{ sentiment.label }}</span>
 235 |       {% endif %}
 236 |       {% if article.premium_tier %}
 237 |       <span class="ad-badge ad-badge-premium"><i class="fas fa-crown" style="font-size:.45rem;"></i>&nbsp;COMMANDER BRIEF</span>
 238 |       {% endif %}
 239 |       <span class="ad-badge-time"><i class="fas fa-clock" style="margin-right:4px;"></i>{{ read_time }}m read</span>
 240 |     </div>
 241 | 
 242 |     <h1 class="ad-title">{{ article.title }}</h1>
 243 | 
 244 |     <div class="ad-meta-row">
 245 |       <span>{{ article.author or 'Protocol Pulse' }}</span>
 246 |       <span class="ad-meta-sep">&bull;</span>
 247 |       <time datetime="{{ article.published_at.isoformat() if article.published_at else article.created_at.isoformat() }}">
 248 |         {{ article.published_at.strftime('%B %d, %Y') if article.published_at else article.created_at.strftime('%B %d, %Y') }}
 249 |       </time>
 250 |       {% if article.source_url %}
 251 |       <span class="ad-meta-sep">&bull;</span>
 252 |       <a href="{{ article.source_url }}" target="_blank" rel="noopener" style="color:var(--ad-text3);text-decoration:none;">Source ↗</a>
 253 |       {% endif %}
 254 |     </div>
 255 | 
 256 |     <div class="ad-share">
 257 |       <button class="ad-share-btn" onclick="adShareX()" aria-label="Share on X"><i class="fab fa-x-twitter"></i></button>
 258 |       <button class="ad-share-btn" onclick="adShareNostr()" aria-label="Share on Nostr" title="Share on Nostr" style="font-size:.6rem;font-weight:800;">NOS</button>
 259 |       <button class="ad-share-btn" onclick="adCopyLink(this)" aria-label="Copy link"><i class="fas fa-link"></i></button>
 260 |       <button class="ad-share-btn" onclick="adShareEmail()" aria-label="Email"><i class="fas fa-envelope"></i></button>
 261 |     </div>
 262 |   </header>
 263 | 
 264 |   <!-- TL;DR -->
 265 |   {% if article.summary %}
 266 |   <div class="ad-tldr">
 267 |     <button class="ad-tldr-toggle" onclick="adToggleTldr(this)" aria-expanded="false">
 268 |       <span class="ad-tldr-label"><i class="fas fa-bolt"></i>TL;DR</span>
 269 |       <i class="fas fa-chevron-down ad-tldr-caret"></i>
 270 |     </button>
 271 |     <div class="ad-tldr-body" id="adTldrBody" hidden>{{ article.summary }}</div>
 272 |   </div>
 273 |   {% endif %}
 274 | 
 275 |   <!-- Layout -->
 276 |   <div class="ad-layout">
 277 |     <!-- Main column -->
 278 |     <div>
 279 |       <!-- Key Takeaways -->
 280 |       {% if key_takeaways_bullets %}
 281 |       <div class="ad-takeaways">
 282 |         <div class="ad-takeaways-hdr"><i class="fas fa-bolt"></i>KEY TAKEAWAYS</div>
 283 |         <ul class="ad-takeaways-list">
 284 |           {% for b in key_takeaways_bullets %}<li>{{ b }}</li>{% endfor %}
 285 |         </ul>
 286 |       </div>
 287 |       {% endif %}
 288 | 
 289 |       <!-- Body -->
 290 |       <div class="ad-body" id="adBody">
 291 |         {% if article.video_url %}
 292 |         <div class="ad-video-wrap"><iframe src="{{ article.video_url }}" allowfullscreen></iframe></div>
 293 |         {% endif %}
 294 |         {{ body_html|safe if body_html else article.content|safe }}
 295 |       </div>
 296 | 
 297 |       <!-- Tags -->
 298 |       {% if article.tags %}
 299 |       <div class="ad-tags">
 300 |         {% for tag in article.tags.split(',') %}
 301 |         <a href="/articles?q={{ tag.strip()|urlencode }}" class="ad-tag">{{ tag.strip() }}</a>
 302 |         {% endfor %}
 303 |       </div>
 304 |       {% endif %}
 305 | 
 306 |       <!-- Tip jar -->
 307 |       <div class="ad-tipjar">
 308 |         <h5>Value this Intelligence Brief?</h5>
 309 |         <p>Support freedom tech journalism. Every sat funds the signal.</p>
 310 |         <div class="ad-tip-btns">
 311 |           <button class="ad-tip-btn" onclick="adZapSats(1000)"><i class="fas fa-bolt"></i>1K sats</button>
 312 |           <button class="ad-tip-btn" onclick="adZapSats(5000)"><i class="fas fa-bolt"></i>5K sats</button>
 313 |           <button class="ad-tip-btn featured" onclick="adZapSats(21000)"><i class="fas fa-bolt"></i>21K sats</button>
 314 |         </div>
 315 |       </div>
 316 | 
 317 |       <!-- Bottom actions -->
 318 |       <div class="ad-bottom-actions">
 319 |         <a href="/articles" class="ad-btn-ghost"><i class="fas fa-arrow-left"></i>All Intelligence</a>
 320 |         <div style="display:flex;gap:8px;">
 321 |           <button class="ad-share-btn" onclick="adShareX()"><i class="fab fa-x-twitter"></i></button>
 322 |           <button class="ad-share-btn" onclick="adCopyLink(this)"><i class="fas fa-link"></i></button>
 323 |         </div>
 324 |       </div>
 325 |     </div>
 326 | 
 327 |     <!-- Sidebar -->
 328 |     <aside class="ad-sidebar">
 329 |       <!-- ToC (auto-generated) -->
 330 |       <div class="ad-sidebar-panel" id="adToc">
 331 |         <span class="ad-sidebar-label">Table of Contents</span>
 332 |         <nav id="adTocNav"></nav>
 333 |       </div>
 334 | 
 335 |       <!-- Related briefs -->
 336 |       {% if related_data %}
 337 |       <div class="ad-sidebar-panel">
 338 |         <span class="ad-sidebar-label">Related Briefs</span>
 339 |         {% for rd in related_data %}
 340 |         {% set ra = rd.article %}
 341 |         <a href="/articles/{{ ra.id }}" class="ad-related-item">
 342 |           <div class="ad-related-title">{{ ra.title[:70] }}{% if ra.title|length > 70 %}...{% endif %}</div>
 343 |           <div class="ad-related-meta">
 344 |             <span style="color:{{ rd.cat_color }};">{{ ra.category or 'Bitcoin' }}</span>
 345 |             &bull; {{ ra.created_at.strftime('%b %d') if ra.created_at else '' }}
 346 |           </div>
 347 |         </a>
 348 |         {% endfor %}
 349 |       </div>
 350 |       {% endif %}
 351 |     </aside>
 352 |   </div>
 353 | 
 354 |   <!-- MORE INTELLIGENCE — always-3 related grid -->
 355 |   {% if related_data %}
 356 |   <div class="ad-more-section">
 357 |     <div class="ad-more-label">More Intelligence</div>
 358 |     <div class="ad-more-grid">
 359 |       {% for rd in related_data %}
 360 |       {% set ra = rd.article %}
 361 |       <a href="/articles/{{ ra.id }}" class="ad-rel-card">
 362 |         <div class="ad-rel-img">
 363 |           {% if rd.image_url %}
 364 |           <img src="{{ rd.image_url }}" alt="{{ ra.title }}" loading="lazy"
 365 |             onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
 366 |           <div class="ad-rel-img-grad" style="background:{{ rd.cat_gradient }};display:none;"><i class="fas fa-broadcast-tower"></i></div>
 367 |           {% else %}
 368 |           <div class="ad-rel-img-grad" style="background:{{ rd.cat_gradient }};"><i class="fas fa-broadcast-tower"></i></div>
 369 |           {% endif %}
 370 |           <div class="ad-rel-badges">
 371 |             <span class="ad-rel-badge" style="color:{{ rd.cat_color }};border-color:{{ rd.cat_color }}35;">{{ ra.category or 'Bitcoin' }}</span>
 372 |             <span class="ad-rel-badge" style="color:{{ rd.sentiment.color }};border-color:{{ rd.sentiment.color }}35;background:{{ rd.sentiment.bg }};">{{ rd.sentiment.label }}</span>
 373 |           </div>
 374 |         </div>
 375 |         <div class="ad-rel-body">
 376 |           <div class="ad-rel-title">{{ ra.title }}</div>
 377 |           <div class="ad-rel-meta">
 378 |             {{ ra.author or 'Protocol Pulse' }} &bull; {{ ra.created_at.strftime('%b %d, %Y') if ra.created_at else '' }}
 379 |             &bull; {{ rd.read_time }}m read
 380 |           </div>
 381 |         </div>
 382 |       </a>
 383 |       {% endfor %}
 384 |     </div>
 385 |   </div>
 386 |   {% endif %}
 387 | </div>
 388 | 
 389 | <script>
 390 | /* Reading progress */
 391 | window.addEventListener('scroll',function(){
 392 |   var body=document.getElementById('adBody');
 393 |   var bar=document.getElementById('adProgress');
 394 |   if(!body||!bar) return;
 395 |   var pct=Math.min(100,Math.max(0,((window.pageYOffset-body.offsetTop+window.innerHeight)/body.offsetHeight)*100));
 396 |   bar.style.width=pct+'%';
 397 | },{passive:true});
 398 | 
 399 | /* Share */
 400 | function adShareX(){
 401 |   var u=encodeURIComponent(location.href),t=encodeURIComponent(document.title+' via @ProtocolPulse');
 402 |   window.open('https://x.com/intent/tweet?url='+u+'&text='+t,'_blank','width=600,height=400');
 403 | }
 404 | function adCopyLink(btn){
 405 |   navigator.clipboard.writeText(location.href).then(function(){
 406 |     var orig=btn.innerHTML;btn.innerHTML='<i class="fas fa-check"></i>';
 407 |     btn.style.cssText+='border-color:var(--ad-gold);color:var(--ad-gold);';
 408 |     setTimeout(function(){btn.innerHTML=orig;btn.removeAttribute('style');},2000);
 409 |   }).catch(function(){var t=document.createElement('textarea');t.value=location.href;document.body.appendChild(t);t.select();document.execCommand('copy');document.body.removeChild(t);});
 410 | }
 411 | function adShareEmail(){window.location.href='mailto:?subject='+encodeURIComponent(document.title)+'&body='+encodeURIComponent('Check this out: '+location.href);}
 412 | function adShareNostr(){window.open('https://nostr.com/?text='+encodeURIComponent(document.title+' — '+location.href+' via @ProtocolPulse'),'_blank','noopener');}
 413 | 
 414 | /* TL;DR */
 415 | function adToggleTldr(btn){
 416 |   var body=document.getElementById('adTldrBody');
 417 |   var exp=btn.getAttribute('aria-expanded')==='true';
 418 |   btn.setAttribute('aria-expanded',!exp);
 419 |   body.hidden=exp;
 420 | }
 421 | 
 422 | /* Lightning tips */
 423 | async function adZapSats(amt){
 424 |   if(typeof window.webln!=='undefined'){
 425 |     try{await window.webln.enable();await window.webln.makeInvoice({amount:amt,defaultMemo:'Protocol Pulse tip'});alert('Zapped '+amt+' sats! Thank you.');}
 426 |     catch(e){alert('WebLN: '+e.message);}
 427 |   } else {alert('Install Alby wallet for Lightning tips, or visit /donate.');}
 428 | }
 429 | 
 430 | /* Auto ToC */
 431 | (function(){
 432 |   var body=document.getElementById('adBody');
 433 |   var toc=document.getElementById('adToc');
 434 |   var nav=document.getElementById('adTocNav');
 435 |   if(!body||!toc||!nav) return;
 436 |   var hs=body.querySelectorAll('h2,h3');
 437 |   if(hs.length<3) return;
 438 |   toc.style.display='block';
 439 |   var html='';
 440 |   hs.forEach(function(h,i){
 441 |     var id='toc-'+i;h.id=id;
 442 |     var cls=h.tagName==='H3'?' h3':'';
 443 |     html+='<a href="#'+id+'" class="ad-toc-link'+cls+'">'+h.textContent.trim().substring(0,60)+'</a>';
 444 |   });
 445 |   nav.innerHTML=html;
 446 |   if(!('IntersectionObserver' in window)) return;
 447 |   var links=nav.querySelectorAll('a');
 448 |   var obs=new IntersectionObserver(function(entries){
 449 |     entries.forEach(function(e){
 450 |       if(e.isIntersecting){
 451 |         links.forEach(function(l){l.classList.remove('active');});
 452 |         var a=nav.querySelector('a[href="#'+e.target.id+'"]');
 453 |         if(a) a.classList.add('active');
 454 |       }
 455 |     });
 456 |   },{rootMargin:'-64px 0px -80% 0px'});
 457 |   hs.forEach(function(h){obs.observe(h);});
 458 | })();
 459 | </script>
 460 | {% endblock %}
 461 | 
```

### File: templates/articles.html (322 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Intelligence Feed — Protocol Pulse{% endblock %}
   4 | 
   5 | {% block og_meta %}
   6 | <meta property="og:title" content="Bitcoin Intelligence Feed — Protocol Pulse">
   7 | <meta property="og:description" content="{{ total_count }} intelligence briefs. Real-time Bitcoin news, analysis, and market intelligence.">
   8 | <meta property="og:type" content="website">
   9 | <meta property="og:site_name" content="Protocol Pulse">
  10 | <meta property="og:image" content="{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}">
  11 | <meta property="og:url" content="{{ request.url }}">
  12 | <meta name="twitter:card" content="summary_large_image">
  13 | <meta name="twitter:site" content="@ProtocolPulse">
  14 | {% endblock %}
  15 | 
  16 | {% block schema %}
  17 | {{ super() }}
  18 | <script type="application/ld+json">
  19 | {"@context":"https://schema.org","@type":"CollectionPage","name":"Bitcoin Intelligence Feed","description":"Real-time Bitcoin news and analysis from Protocol Pulse.","publisher":{"@type":"Organization","name":"Protocol Pulse","url":"https://protocolpulse.io"}}
  20 | </script>
  21 | {% endblock %}
  22 | 
  23 | {% block head %}
  24 | <style>
  25 | /* SESSION 10 — Article Rebuild */
  26 | :root {
  27 |   --art-bg:#030303;--art-surface:#0a0a0a;--art-border:rgba(255,255,255,0.06);
  28 |   --art-border-hover:rgba(220,38,38,0.35);--art-red:#dc2626;
  29 |   --art-red-dim:rgba(220,38,38,0.08);--art-gold:#f7931a;
  30 |   --art-text:#f0f0f0;--art-text2:#999;--art-text3:#5a5a5a;
  31 |   --art-mono:'JetBrains Mono',monospace;
  32 |   --art-serif:'Crimson Pro',Georgia,serif;
  33 |   --art-sans:'DM Sans',system-ui,sans-serif;
  34 | }
  35 | body{background:var(--art-bg);color:var(--art-text);}
  36 | .art-page-header{background:var(--art-bg);border-bottom:1px solid var(--art-border);padding:2rem 0 1.5rem;}
  37 | .art-header-inner{max-width:1340px;margin:0 auto;padding:0 1.5rem;}
  38 | .art-header-eyebrow{font-family:var(--art-mono);font-size:.6rem;letter-spacing:.3em;text-transform:uppercase;color:var(--art-red);display:flex;align-items:center;gap:8px;margin-bottom:.6rem;}
  39 | .art-header-eyebrow::before{content:'';width:5px;height:5px;background:var(--art-red);border-radius:50%;box-shadow:0 0 8px var(--art-red);animation:livePulse 2s infinite;}
  40 | @keyframes livePulse{0%,100%{opacity:1}50%{opacity:.3}}
  41 | .art-header-title{font-family:var(--art-mono);font-size:clamp(1rem,2vw,1.35rem);font-weight:700;color:#fff;letter-spacing:.05em;text-transform:uppercase;margin-bottom:.35rem;}
  42 | .art-header-title span{color:var(--art-red);}
  43 | .art-header-meta{font-family:var(--art-mono);font-size:.62rem;color:var(--art-text3);letter-spacing:.04em;}
  44 | .art-controls{max-width:1340px;margin:0 auto;padding:1rem 1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;border-bottom:1px solid var(--art-border);}
  45 | .art-search-wrap{position:relative;flex:1;min-width:180px;max-width:340px;}
  46 | .art-search-wrap i{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--art-text3);font-size:.7rem;}
  47 | .art-search{width:100%;background:var(--art-surface);border:1px solid var(--art-border);border-radius:6px;padding:7px 11px 7px 30px;color:var(--art-text);font-family:var(--art-mono);font-size:.72rem;outline:none;transition:border-color .2s;}
  48 | .art-search:focus{border-color:var(--art-red);}
  49 | .art-search::placeholder{color:var(--art-text3);}
  50 | .art-filters{display:flex;gap:6px;flex-wrap:wrap;align-items:center;}
  51 | .art-filter-pill{font-family:var(--art-mono);font-size:.58rem;text-transform:uppercase;letter-spacing:.08em;padding:5px 11px;border-radius:4px;border:1px solid var(--art-border);background:transparent;color:var(--art-text3);cursor:pointer;transition:all .2s;white-space:nowrap;}
  52 | .art-filter-pill:hover{border-color:var(--art-red);color:var(--art-text);}
  53 | .art-filter-pill.active{background:var(--art-red-dim);border-color:var(--art-red);color:var(--art-red);}
  54 | .art-filter-count{display:inline-block;margin-left:4px;opacity:.45;font-size:.52rem;}
  55 | .art-main{max-width:1340px;margin:0 auto;padding:1.5rem 1.5rem 3rem;}
  56 | .art-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;}
  57 | @media(max-width:1100px){.art-grid{grid-template-columns:repeat(2,1fr);}}
  58 | @media(max-width:640px){.art-grid{grid-template-columns:1fr;}}
  59 | .art-card{background:var(--art-surface);border:1px solid var(--art-border);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;transition:border-color .3s,transform .3s,box-shadow .3s;text-decoration:none;color:inherit;}
  60 | .art-card:hover{border-color:var(--art-border-hover);transform:translateY(-3px);box-shadow:0 16px 48px rgba(0,0,0,.5),0 0 0 1px rgba(220,38,38,.08);color:inherit;text-decoration:none;}
  61 | .art-card-img-wrap{height:180px;position:relative;overflow:hidden;flex-shrink:0;background:#0d0d0d;}
  62 | .art-card-img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s;}
  63 | .art-card:hover .art-card-img{transform:scale(1.04);}
  64 | .art-card-img-grad{width:100%;height:100%;display:flex;align-items:center;justify-content:center;}
  65 | .art-card-img-grad i{font-size:2rem;opacity:.12;color:#fff;}
  66 | .art-card-img-overlay{position:absolute;bottom:0;left:0;right:0;height:55%;background:linear-gradient(transparent,var(--art-surface));pointer-events:none;}
  67 | .art-card-badges{position:absolute;top:10px;left:10px;right:10px;display:flex;justify-content:space-between;align-items:flex-start;gap:6px;}
  68 | .art-badge-cat,.art-badge-sent{font-family:var(--art-mono);font-size:.5rem;text-transform:uppercase;letter-spacing:.08em;padding:3px 8px;border-radius:3px;font-weight:700;border:1px solid;backdrop-filter:blur(4px);}
  69 | .art-badge-cat{background:rgba(0,0,0,.6);max-width:55%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  70 | .art-card-body{padding:1.1rem 1.2rem 1.2rem;display:flex;flex-direction:column;flex:1;}
  71 | .art-card-title{font-family:var(--art-serif);font-size:1.1rem;font-weight:700;line-height:1.3;color:#fff;margin-bottom:.55rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;transition:color .2s;}
  72 | .art-card:hover .art-card-title{color:var(--art-red);}
  73 | .art-card-summary{font-family:var(--art-sans);font-size:.84rem;line-height:1.6;color:var(--art-text2);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;flex:1;margin-bottom:.85rem;}
  74 | .art-card-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;padding-top:.7rem;border-top:1px solid var(--art-border);margin-top:auto;}
  75 | .art-meta-left{display:flex;align-items:center;gap:8px;min-width:0;}
  76 | .art-meta-source{font-family:var(--art-mono);font-size:.56rem;color:var(--art-text3);text-transform:uppercase;letter-spacing:.04em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px;}
  77 | .art-meta-sep{color:var(--art-border);font-size:.5rem;}
  78 | .art-meta-time,.art-meta-read{font-family:var(--art-mono);font-size:.56rem;color:var(--art-text3);white-space:nowrap;}
  79 | .art-meta-read{display:flex;align-items:center;gap:4px;}
  80 | .art-meta-read i{font-size:.48rem;}
  81 | .art-empty{text-align:center;padding:5rem 2rem;border:1px dashed var(--art-border);border-radius:12px;color:var(--art-text3);}
  82 | .art-empty i{font-size:2rem;margin-bottom:1rem;opacity:.35;color:var(--art-red);display:block;}
  83 | .art-load-more-wrap{text-align:center;padding:2.5rem 0 1rem;}
  84 | .art-load-more-btn{font-family:var(--art-mono);font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;color:var(--art-text3);background:var(--art-surface);border:1px solid var(--art-border);padding:11px 30px;border-radius:6px;cursor:pointer;transition:all .25s;display:inline-flex;align-items:center;gap:8px;}
  85 | .art-load-more-btn:hover{border-color:var(--art-red);color:var(--art-red);background:var(--art-red-dim);}
  86 | .art-load-more-btn:disabled{opacity:.5;cursor:not-allowed;}
  87 | .art-load-more-btn .spinner{width:12px;height:12px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite;display:none;}
  88 | .art-load-more-btn.loading .spinner{display:block;}
  89 | .art-load-more-btn.loading .btn-text{display:none;}
  90 | @keyframes spin{to{transform:rotate(360deg)}}
  91 | #art-no-results{display:none;text-align:center;padding:3rem;color:var(--art-text3);font-family:var(--art-mono);font-size:.72rem;}
  92 | .art-card.art-hidden{display:none;}
  93 | @media(max-width:768px){.art-card-img-wrap{height:160px;}.art-controls{padding:.75rem 1rem;}.art-main{padding:1rem 1rem 2rem;}.art-header-inner{padding:0 1rem;}}
  94 | </style>
  95 | {% endblock %}
  96 | 
  97 | {% block content %}
  98 | <div style="background:var(--art-bg,#030303);min-height:100vh;">
  99 | 
 100 |   <div class="art-page-header">
 101 |     <div class="art-header-inner">
 102 |       <div class="art-header-eyebrow">Live Intelligence Feed</div>
 103 |       <h1 class="art-header-title">PROTOCOL PULSE <span>//</span> INTELLIGENCE FEED</h1>
 104 |       <div class="art-header-meta">
 105 |         {% if total_count %}
 106 |           {{ "{:,}".format(total_count) }} brief{{ 's' if total_count != 1 }} &middot;
 107 |           {{ categories|length }} categor{{ 'ies' if categories|length != 1 else 'y' }}
 108 |           &middot; updated {{ (last_updated | to_est).strftime('%b %d, %Y %I:%M %p') }} ET
 109 |         {% else %}
 110 |           Intelligence feed loading...
 111 |         {% endif %}
 112 |       </div>
 113 |     </div>
 114 |   </div>
 115 | 
 116 |   <div class="art-controls">
 117 |     <div class="art-search-wrap">
 118 |       <i class="fas fa-search"></i>
 119 |       <input type="text" class="art-search" id="artSearch"
 120 |         placeholder="Search intelligence..." autocomplete="off"
 121 |         value="{{ search_q or '' }}" aria-label="Search articles">
 122 |     </div>
 123 |     <div class="art-filters" id="artFilters">
 124 |       <button class="art-filter-pill {% if not category_filter or category_filter.lower() == 'all' %}active{% endif %}" data-cat="all">
 125 |         All <span class="art-filter-count">{{ "{:,}".format(total_count) }}</span>
 126 |       </button>
 127 |       {% for cat in categories %}
 128 |       <button class="art-filter-pill {% if category_filter and category_filter.lower() == cat.lower() %}active{% endif %}" data-cat="{{ cat }}">
 129 |         {{ cat }}<span class="art-filter-count">{{ category_counts.get(cat, 0) }}</span>
 130 |       </button>
 131 |       {% endfor %}
 132 |     </div>
 133 |   </div>
 134 | 
 135 |   <div class="art-main">
 136 |     <div id="artGrid" class="art-grid">
 137 |       {% for d in article_data %}
 138 |       {% set a = d.article %}
 139 |       <a href="{{ url_for('article_detail', article_id=a.id) }}"
 140 |         class="art-card"
 141 |         data-title="{{ a.title|lower }}"
 142 |         data-summary="{{ (a.summary or '')|lower|truncate(200,true,'') }}"
 143 |         data-cat="{{ (a.category or '')|lower }}"
 144 |         data-tags="{{ (a.tags or '')|lower }}">
 145 |         <div class="art-card-img-wrap">
 146 |           {% if d.image_url %}
 147 |           <img class="art-card-img" src="{{ d.image_url }}" alt="{{ a.title }}" loading="lazy" decoding="async"
 148 |             onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
 149 |           <div class="art-card-img-grad" style="background:{{ d.cat_gradient }};display:none;">
 150 |             <i class="fas fa-broadcast-tower"></i>
 151 |           </div>
 152 |           {% else %}
 153 |           <div class="art-card-img-grad" style="background:{{ d.cat_gradient }};">
 154 |             <i class="fas fa-broadcast-tower"></i>
 155 |           </div>
 156 |           {% endif %}
 157 |           <div class="art-card-img-overlay"></div>
 158 |           <div class="art-card-badges">
 159 |             <span class="art-badge-cat" style="color:{{ d.cat_color }};border-color:{{ d.cat_color }}35;">{{ a.category or 'Bitcoin' }}</span>
 160 |             <span class="art-badge-sent" style="color:{{ d.sentiment.color }};border-color:{{ d.sentiment.color }}35;background:{{ d.sentiment.bg }};">{{ d.sentiment.label }}</span>
 161 |           </div>
 162 |         </div>
 163 |         <div class="art-card-body">
 164 |           <h3 class="art-card-title">{{ a.title }}</h3>
 165 |           <p class="art-card-summary">
 166 |             {% if a.summary %}{{ a.summary[:260] }}{% else %}{{ a.content | clean_preview(200) }}{% endif %}
 167 |           </p>
 168 |           <div class="art-card-meta">
 169 |             <div class="art-meta-left">
 170 |               <span class="art-meta-source">{{ a.author or a.source_type or 'Protocol Pulse' }}</span>
 171 |               <span class="art-meta-sep">&bull;</span>
 172 |               <span class="art-meta-time">
 173 |                 {% if a.created_at %}
 174 |                   {% set diff = (last_updated - a.created_at).total_seconds() %}
 175 |                   {% if diff < 3600 %}{{ (diff / 60)|int }}m ago
 176 |                   {% elif diff < 86400 %}{{ (diff / 3600)|int }}h ago
 177 |                   {% elif diff < 604800 %}{{ (diff / 86400)|int }}d ago
 178 |                   {% else %}{{ a.created_at.strftime('%b %d') }}{% endif %}
 179 |                 {% endif %}
 180 |               </span>
 181 |             </div>
 182 |             <span class="art-meta-read"><i class="fas fa-clock"></i>{{ d.read_time }}m</span>
 183 |           </div>
 184 |         </div>
 185 |       </a>
 186 |       {% endfor %}
 187 |     </div>
 188 | 
 189 |     <div id="art-no-results">
 190 |       <i class="fas fa-search" style="font-size:1.4rem;opacity:.25;display:block;margin-bottom:.6rem;"></i>
 191 |       No intelligence matching your filter.
 192 |     </div>
 193 | 
 194 |     {% if not article_data %}
 195 |     <div class="art-empty">
 196 |       <i class="fas fa-satellite-dish"></i>
 197 |       <p style="font-family:var(--art-sans);">Scanning networks for intelligence...</p>
 198 |     </div>
 199 |     {% endif %}
 200 | 
 201 |     {% if has_more or (article_data|length >= 24) %}
 202 |     <div class="art-load-more-wrap" id="artLoadMoreWrap">
 203 |       <button class="art-load-more-btn" id="artLoadMore" onclick="loadMoreArticles()">
 204 |         <span class="btn-text"><i class="fas fa-chevron-down"></i>&nbsp;LOAD MORE INTELLIGENCE</span>
 205 |         <span class="spinner"></span>
 206 |       </button>
 207 |     </div>
 208 |     {% endif %}
 209 |   </div>
 210 | </div>
 211 | 
 212 | <script>
 213 | (function(){
 214 |   'use strict';
 215 |   var currentPage=1,currentCat='{{ category_filter or "all" }}',isLoading=false;
 216 |   var hasMore={{ 'true' if has_more or (article_data|length >= 24) else 'false' }};
 217 |   var cachedCards=null;
 218 | 
 219 |   function getCards(){
 220 |     if(!cachedCards) cachedCards=document.querySelectorAll('#artGrid .art-card');
 221 |     return cachedCards;
 222 |   }
 223 | 
 224 |   function applyFilters(){
 225 |     var search=(document.getElementById('artSearch')||{value:''}).value.toLowerCase().trim();
 226 |     var active=document.querySelector('.art-filter-pill.active');
 227 |     var cat=active?active.dataset.cat.toLowerCase():'all';
 228 |     var visible=0;
 229 |     getCards().forEach(function(c){
 230 |       var titleOk=!search||(c.dataset.title||'').indexOf(search)!==-1||(c.dataset.summary||'').indexOf(search)!==-1||(c.dataset.tags||'').indexOf(search)!==-1;
 231 |       var catOk=cat==='all'||(c.dataset.cat||'').indexOf(cat)!==-1;
 232 |       if(titleOk&&catOk){c.classList.remove('art-hidden');visible++;}
 233 |       else c.classList.add('art-hidden');
 234 |     });
 235 |     var nr=document.getElementById('art-no-results');
 236 |     if(nr) nr.style.display=visible===0?'block':'none';
 237 |     var lmw=document.getElementById('artLoadMoreWrap');
 238 |     if(lmw) lmw.style.display=(search||cat!=='all')?'none':'';
 239 |   }
 240 | 
 241 |   var si=document.getElementById('artSearch');
 242 |   if(si){var t;si.addEventListener('input',function(){clearTimeout(t);t=setTimeout(applyFilters,180);});}
 243 | 
 244 |   document.getElementById('artFilters').addEventListener('click',function(e){
 245 |     var p=e.target.closest('.art-filter-pill');
 246 |     if(!p) return;
 247 |     document.querySelectorAll('.art-filter-pill').forEach(function(x){x.classList.remove('active');});
 248 |     p.classList.add('active');
 249 |     currentCat=p.dataset.cat;
 250 |     currentPage=1;
 251 |     applyFilters();
 252 |   });
 253 | 
 254 |   window.loadMoreArticles=function(){
 255 |     if(isLoading||!hasMore) return;
 256 |     isLoading=true;
 257 |     var btn=document.getElementById('artLoadMore');
 258 |     if(btn) btn.classList.add('loading');
 259 |     currentPage++;
 260 |     var url='/api/v2/articles?page='+currentPage+'&per_page=24';
 261 |     if(currentCat&&currentCat!=='all') url+='&category='+encodeURIComponent(currentCat);
 262 |     var q=(document.getElementById('artSearch')||{value:''}).value.trim();
 263 |     if(q) url+='&q='+encodeURIComponent(q);
 264 |     fetch(url).then(function(r){return r.json();}).then(function(data){
 265 |       hasMore=data.has_more;
 266 |       if(!data.articles||!data.articles.length){
 267 |         hasMore=false;
 268 |         var lmw=document.getElementById('artLoadMoreWrap');
 269 |         if(lmw) lmw.style.display='none';
 270 |         return;
 271 |       }
 272 |       appendCards(data.articles);
 273 |       cachedCards=null;
 274 |       if(!hasMore){
 275 |         var lmw=document.getElementById('artLoadMoreWrap');
 276 |         if(lmw) lmw.style.display='none';
 277 |       }
 278 |     }).catch(function(e){console.error('loadMore:',e);currentPage--;})
 279 |     .finally(function(){isLoading=false;if(btn) btn.classList.remove('loading');});
 280 |   };
 281 | 
 282 |   function timeAgo(s){
 283 |     if(!s) return '';
 284 |     var d=(Date.now()-new Date(s).getTime())/1000;
 285 |     if(d<3600) return Math.floor(d/60)+'m ago';
 286 |     if(d<86400) return Math.floor(d/3600)+'h ago';
 287 |     if(d<604800) return Math.floor(d/86400)+'d ago';
 288 |     return new Date(s).toLocaleDateString('en-US',{month:'short',day:'numeric'});
 289 |   }
 290 | 
 291 |   function esc(s){return s?s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'):'';}
 292 | 
 293 |   function appendCards(arts){
 294 |     var grid=document.getElementById('artGrid');
 295 |     if(!grid) return;
 296 |     arts.forEach(function(a){
 297 |       var imgHtml=a.image_url
 298 |         ?'<img class="art-card-img" src="'+esc(a.image_url)+'" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';">'
 299 |          +'<div class="art-card-img-grad" style="background:'+esc(a.category_gradient)+';display:none;"><i class="fas fa-broadcast-tower"></i></div>'
 300 |         :'<div class="art-card-img-grad" style="background:'+esc(a.category_gradient)+'"><i class="fas fa-broadcast-tower"></i></div>';
 301 |       var html='<a href="'+esc(a.url)+'" class="art-card" data-title="'+esc((a.title||'').toLowerCase())+'" data-summary="'+esc((a.summary||'').toLowerCase().substring(0,200))+'" data-cat="'+esc((a.category||'').toLowerCase())+'" data-tags="">'
 302 |         +'<div class="art-card-img-wrap">'+imgHtml+'<div class="art-card-img-overlay"></div>'
 303 |         +'<div class="art-card-badges"><span class="art-badge-cat" style="color:'+esc(a.category_color)+';border-color:'+esc(a.category_color)+'35;">'+esc(a.category||'Bitcoin')+'</span>'
 304 |         +'<span class="art-badge-sent" style="color:'+esc(a.sentiment_color)+';border-color:'+esc(a.sentiment_color)+'35;background:'+esc(a.sentiment_bg)+';">'+esc(a.sentiment_label)+'</span>'
 305 |         +'</div></div>'
 306 |         +'<div class="art-card-body"><h3 class="art-card-title">'+esc(a.title)+'</h3>'
 307 |         +'<p class="art-card-summary">'+esc((a.summary||'').substring(0,260))+'</p>'
 308 |         +'<div class="art-card-meta"><div class="art-meta-left">'
 309 |         +'<span class="art-meta-source">'+esc(a.source||'Protocol Pulse')+'</span>'
 310 |         +'<span class="art-meta-sep">&bull;</span>'
 311 |         +'<span class="art-meta-time">'+timeAgo(a.created_at)+'</span>'
 312 |         +'</div><span class="art-meta-read"><i class="fas fa-clock"></i>'+(a.read_time||1)+'m</span>'
 313 |         +'</div></div></a>';
 314 |       var d=document.createElement('div');
 315 |       d.innerHTML=html;
 316 |       grid.appendChild(d.firstChild);
 317 |     });
 318 |   }
 319 | })();
 320 | </script>
 321 | {% endblock %}
 322 | 
```

### File: templates/media_unified.html (331 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 |   <meta charset="UTF-8">
   5 |   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   6 |   <title>Media Intelligence — Protocol Pulse</title>
   7 |   <meta name="description" content="Real-time Bitcoin media intelligence. Signal strength, sentiment heatmap, source health, live intelligence feed.">
   8 |   <link rel="icon" href="/static/favicon.ico" type="image/x-icon">
   9 |   <style>
  10 |     *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  11 |     :root{
  12 |       --bg:#000;--bg-s:#0a0a0a;--bg-c:#111;--bg-p:#141414;
  13 |       --bdr:#1e1e1e;--bdr2:#2a2a2a;
  14 |       --red:#dc2626;--gold:#f59e0b;--green:#22c55e;--amber:#f59e0b;
  15 |       --cyan:#06b6d4;--text:#e5e7eb;--dim:#6b7280;--muted:#374151;
  16 |       --mono:'JetBrains Mono','Fira Code',monospace;
  17 |     }
  18 |     html{scroll-behavior:smooth}
  19 |     body{background:var(--bg);color:var(--text);font-family:var(--mono);font-size:13px;line-height:1.5;min-height:100vh;overflow-x:hidden}
  20 |     ::-webkit-scrollbar{width:4px;height:4px}
  21 |     ::-webkit-scrollbar-track{background:var(--bg)}
  22 |     ::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:2px}
  23 |     #hbar{position:fixed;top:0;left:0;right:0;height:44px;background:rgba(0,0,0,.96);border-bottom:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between;padding:0 16px;z-index:100;backdrop-filter:blur(8px)}
  24 |     #hbar-l{font-size:11px;font-weight:700;letter-spacing:.12em;color:#fff}
  25 |     #hbar-l span{color:var(--red)}
  26 |     #hbar-c{display:flex;align-items:center;gap:8px}
  27 |     #hdr-sig-lbl{font-size:10px;letter-spacing:.1em;color:var(--dim)}
  28 |     #hdr-sig-val{font-size:16px;font-weight:700;transition:color .4s}
  29 |     #hdr-sig-bdg{font-size:9px;font-weight:700;letter-spacing:.1em;padding:2px 6px;border-radius:3px;border:1px solid currentColor}
  30 |     #hbar-r{display:flex;align-items:center;gap:10px;font-size:11px;color:var(--dim)}
  31 |     .ldot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);animation:pls 2s ease-in-out infinite;flex-shrink:0}
  32 |     @keyframes pls{0%,100%{opacity:1}50%{opacity:.4}}
  33 |     #utcclock{font-variant-numeric:tabular-nums}
  34 |     #wrap{margin-top:44px;padding:16px;display:grid;grid-template-columns:360px 1fr;gap:12px;max-width:1600px;margin-left:auto;margin-right:auto}
  35 |     #ci{grid-column:1;display:flex;flex-direction:column;gap:12px}
  36 |     #cf{grid-column:2;display:flex;flex-direction:column;gap:12px}
  37 |     #hs{grid-column:1/-1}
  38 |     .panel{background:var(--bg-c);border:1px solid var(--bdr);border-radius:4px;overflow:hidden}
  39 |     .ph{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--bdr);background:var(--bg-p)}
  40 |     .pt{font-size:10px;font-weight:700;letter-spacing:.12em;color:#fff}
  41 |     .pt span{color:var(--red)}
  42 |     .pm{font-size:9px;color:var(--dim);letter-spacing:.06em}
  43 |     .pb{padding:12px}
  44 |     #sig-ring{display:flex;align-items:center;gap:16px;margin-bottom:14px}
  45 |     .sc{position:relative;width:72px;height:72px;flex-shrink:0}
  46 |     .sc svg{transform:rotate(-90deg)}
  47 |     .sc-trk{fill:none;stroke:#1e1e1e;stroke-width:5}
  48 |     .sc-fill{fill:none;stroke-width:5;stroke-linecap:round;stroke-dasharray:188.5;stroke-dashoffset:188.5;transition:stroke-dashoffset 1s ease,stroke .4s}
  49 |     .sc-val{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700}
  50 |     .sig-info{flex:1}
  51 |     .sig-main{font-size:16px;font-weight:700;letter-spacing:.08em;margin-bottom:2px}
  52 |     .sig-sub{font-size:10px;color:var(--dim);margin-bottom:6px}
  53 |     .scomp{display:flex;align-items:center;gap:8px;margin-bottom:6px}
  54 |     .scomp-lbl{font-size:10px;color:var(--dim);width:110px;flex-shrink:0}
  55 |     .scomp-bw{flex:1;height:4px;background:#1e1e1e;border-radius:2px;overflow:hidden}
  56 |     .scomp-b{height:100%;border-radius:2px;transition:width 1s ease}
  57 |     .scomp-s{font-size:10px;font-weight:700;width:28px;text-align:right}
  58 |     .scomp-d{font-size:9px;width:36px;text-align:right}
  59 |     .hmg{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
  60 |     .hmc{background:var(--bg-p);border:1px solid var(--bdr);border-radius:3px;padding:8px;transition:border-color .2s}
  61 |     .hmc:hover{border-color:var(--bdr2)}
  62 |     .hmc-cat{font-size:9px;font-weight:700;letter-spacing:.1em;color:var(--dim);margin-bottom:4px}
  63 |     .hmc-sent{font-size:12px;font-weight:700;margin-bottom:2px}
  64 |     .hmc-cnt{font-size:9px;color:var(--dim)}
  65 |     .trow{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #111}
  66 |     .trow:last-child{border-bottom:none}
  67 |     .trnk{font-size:9px;color:var(--muted);width:16px;flex-shrink:0;text-align:center}
  68 |     .trnm{flex:1;font-size:11px}
  69 |     .trcnt{font-size:10px;font-weight:700;color:var(--gold)}
  70 |     .trnd{font-size:10px;width:14px;text-align:center}
  71 |     .sg{display:grid;grid-template-columns:repeat(2,1fr);gap:5px}
  72 |     .si{display:flex;align-items:center;gap:6px;padding:5px 7px;background:var(--bg-p);border:1px solid var(--bdr);border-radius:3px}
  73 |     .sdot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
  74 |     .sdot.green{background:var(--green);box-shadow:0 0 5px var(--green)}
  75 |     .sdot.amber{background:var(--amber)}
  76 |     .sdot.red{background:var(--red)}
  77 |     .si-info{flex:1;min-width:0}
  78 |     .si-name{font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  79 |     .si-meta{font-size:9px;color:var(--dim)}
  80 |     #feedbox{max-height:480px;overflow-y:auto}
  81 |     .fi{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #111;animation:fsi .4s ease}
  82 |     @keyframes fsi{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
  83 |     .fi:last-child{border-bottom:none}
  84 |     .fi-ts{font-size:9px;color:var(--dim);white-space:nowrap;width:38px;flex-shrink:0;padding-top:2px}
  85 |     .fi-body{flex:1;min-width:0}
  86 |     .fi-meta{display:flex;align-items:center;gap:6px;margin-bottom:3px;flex-wrap:wrap}
  87 |     .fi-src{font-size:9px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em}
  88 |     .fi-cat{font-size:8px;padding:1px 5px;border-radius:2px;background:#1e1e1e;color:var(--dim);letter-spacing:.05em}
  89 |     .fi-bdg{font-size:8px;font-weight:700;padding:1px 5px;border-radius:2px;border:1px solid currentColor;letter-spacing:.06em;margin-left:auto}
  90 |     .fi-ttl{font-size:12px;line-height:1.4;text-decoration:none;display:block;color:var(--text)}
  91 |     .fi-ttl:hover{color:var(--gold)}
  92 |     .rbar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
  93 |     .rpill{display:flex;align-items:center;gap:5px;padding:3px 8px;background:var(--bg-p);border:1px solid var(--bdr);border-radius:12px;font-size:9px}
  94 |     .rpill.conn{border-color:#22c55e44}.rpill.cnx{border-color:#f59e0b44}.rpill.err{border-color:#ef444444}
  95 |     .rdot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
  96 |     .rdot.g{background:var(--green)}.rdot.a{background:var(--amber);animation:pls 1.5s infinite}.rdot.r{background:var(--red)}
  97 |     #nbox{max-height:380px;overflow-y:auto}
  98 |     .ne{padding:8px;border-bottom:1px solid #111;animation:fsi .3s ease}
  99 |     .ne:last-child{border-bottom:none}
 100 |     .ne-meta{display:flex;align-items:center;gap:6px;margin-bottom:3px}
 101 |     .navt{width:20px;height:20px;border-radius:50%;background:#1e1e1e;flex-shrink:0;overflow:hidden}
 102 |     .navt img{width:100%;height:100%;object-fit:cover}
 103 |     .npk{font-size:9px;color:var(--cyan)}
 104 |     .nts{font-size:9px;color:var(--dim);margin-left:auto}
 105 |     .nc{font-size:11px;line-height:1.5;word-break:break-word}
 106 |     .nfb{padding:24px;text-align:center;color:var(--dim);font-size:11px}
 107 |     .nfb .nfi{font-size:24px;margin-bottom:8px}
 108 |     #hs{display:flex;gap:6px;flex-wrap:wrap}
 109 |     .hp{flex:1;min-width:110px;display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--bg-c);border:1px solid var(--bdr);border-radius:4px;text-decoration:none;transition:border-color .2s;cursor:pointer}
 110 |     .hp:hover{border-color:var(--bdr2)}
 111 |     .hp-ic{font-size:14px;flex-shrink:0}
 112 |     .hp-body{flex:1;min-width:0}
 113 |     .hp-lbl{font-size:9px;color:var(--dim);text-transform:uppercase;letter-spacing:.08em;white-space:nowrap}
 114 |     .hp-val{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 115 |     .hp-dlt{font-size:9px;font-weight:700}
 116 |     .lp{display:inline-block;width:100%;height:12px;background:linear-gradient(90deg,#111 0%,#1e1e1e 50%,#111 100%);background-size:200% 100%;animation:shim 1.5s infinite;border-radius:2px}
 117 |     @keyframes shim{0%{background-position:200% 0}100%{background-position:-200% 0}}
 118 |     .lr{margin-bottom:6px}
 119 |     .tg{color:var(--green)!important}.tr{color:var(--red)!important}.ta{color:var(--amber)!important}
 120 |     .tc{color:var(--cyan)!important}.td{color:var(--dim)!important}.tgd{color:var(--gold)!important}
 121 |     @media(max-width:1024px){ #wrap{grid-template-columns:1fr;padding:12px} #ci,#cf,#hs{grid-column:1} }
 122 |     @media(max-width:600px){ #wrap{padding:8px;gap:8px} .hmg{grid-template-columns:repeat(2,1fr)} .sg{grid-template-columns:1fr} #hbar-c{display:none} }
 123 |   </style>
 124 | </head>
 125 | <body>
 126 | <div id="hbar">
 127 |   <div id="hbar-l">PROTOCOL PULSE <span>//</span> MEDIA INTELLIGENCE</div>
 128 |   <div id="hbar-c">
 129 |     <span id="hdr-sig-lbl">SIGNAL</span>
 130 |     <span id="hdr-sig-val" style="color:#f59e0b">--</span>
 131 |     <span id="hdr-sig-bdg" style="color:#f59e0b">---</span>
 132 |   </div>
 133 |   <div id="hbar-r">
 134 |     <span id="utcclock">--:--:-- UTC</span>
 135 |     <div class="ldot"></div>
 136 |   </div>
 137 | </div>
 138 | <div id="wrap">
 139 |   <div id="ci">
 140 |     <div class="panel">
 141 |       <div class="ph"><span class="pt"><span>A</span> &#8212; SIGNAL STRENGTH COMPOSITE</span><span class="pm" id="sig-updated">LIVE</span></div>
 142 |       <div class="pb">
 143 |         <div id="sig-ring">
 144 |           <div class="sc">
 145 |             <svg viewBox="0 0 72 72" width="72" height="72">
 146 |               <circle class="sc-trk" cx="36" cy="36" r="30"/>
 147 |               <circle class="sc-fill" id="sc-arc" cx="36" cy="36" r="30"/>
 148 |             </svg>
 149 |             <div class="sc-val" id="sc-num">--</div>
 150 |           </div>
 151 |           <div class="sig-info">
 152 |             <div class="sig-main" id="sig-main">LOADING</div>
 153 |             <div class="sig-sub">Composite Intelligence Signal</div>
 154 |           </div>
 155 |         </div>
 156 |         <div id="sig-comps">
 157 |           <div class="lr"><div class="lp"></div></div>
 158 |           <div class="lr"><div class="lp" style="width:80%"></div></div>
 159 |           <div class="lr"><div class="lp" style="width:90%"></div></div>
 160 |           <div class="lr"><div class="lp" style="width:70%"></div></div>
 161 |           <div class="lr"><div class="lp" style="width:85%"></div></div>
 162 |         </div>
 163 |       </div>
 164 |     </div>
 165 |     <div class="panel">
 166 |       <div class="ph"><span class="pt"><span>B</span> &#8212; SENTIMENT HEATMAP</span><span class="pm">LAST 2H</span></div>
 167 |       <div class="pb">
 168 |         <div class="hmg" id="hmg">
 169 |           {% for cat in ['Mining','Regulation','ETFs','Lightning','DeFi','Macro'] %}
 170 |           <div class="hmc">
 171 |             <div class="hmc-cat">{{ cat.upper() }}</div>
 172 |             <div class="hmc-sent"><div class="lp" style="height:14px;width:60%"></div></div>
 173 |             <div class="hmc-cnt" style="margin-top:3px">-- articles</div>
 174 |           </div>
 175 |           {% endfor %}
 176 |         </div>
 177 |       </div>
 178 |     </div>
 179 |     <div class="panel">
 180 |       <div class="ph"><span class="pt"><span>C</span> &#8212; TRENDING TOPICS</span><span class="pm">24H VELOCITY</span></div>
 181 |       <div class="pb">
 182 |         <div id="topics">
 183 |           {% for i in range(8) %}
 184 |           <div class="trow">
 185 |             <span class="trnk">{{ i+1 }}</span>
 186 |             <span class="trnm"><div class="lp" style="width:{{ 60+i*4 }}%"></div></span>
 187 |             <span class="trcnt">--</span>
 188 |             <span class="trnd td">&#8212;</span>
 189 |           </div>
 190 |           {% endfor %}
 191 |         </div>
 192 |       </div>
 193 |     </div>
 194 |     <div class="panel">
 195 |       <div class="ph"><span class="pt"><span>D</span> &#8212; SOURCE HEALTH</span><span class="pm" id="src-updated">5MIN CACHE</span></div>
 196 |       <div class="pb">
 197 |         <div class="sg" id="srcg">
 198 |           {% for i in range(6) %}
 199 |           <div class="si">
 200 |             <div class="sdot amber"></div>
 201 |             <div class="si-info">
 202 |               <div class="si-name"><div class="lp" style="width:80%"></div></div>
 203 |               <div class="si-meta">&#8212;</div>
 204 |             </div>
 205 |           </div>
 206 |           {% endfor %}
 207 |         </div>
 208 |       </div>
 209 |     </div>
 210 |   </div>
 211 |   <div id="cf">
 212 |     <div class="panel">
 213 |       <div class="ph">
 214 |         <span class="pt"><span>E</span> &#8212; PP INTELLIGENCE STREAM</span>
 215 |         <div style="display:flex;align-items:center;gap:6px"><div class="ldot" style="width:5px;height:5px"></div><span class="pm" id="feed-cnt">-- articles</span></div>
 216 |       </div>
 217 |       <div class="pb" style="padding:0 12px">
 218 |         <div id="feedbox">
 219 |           {% if initial_feed and initial_feed.items %}
 220 |             {% for item in initial_feed.items %}
 221 |             <div class="fi">
 222 |               <span class="fi-ts">{{ item.timestamp[11:16] if item.timestamp else '--:--' }}</span>
 223 |               <div class="fi-body">
 224 |                 <div class="fi-meta">
 225 |                   <span class="fi-src">{{ (item.source or 'PP')[:20] }}</span>
 226 |                   <span class="fi-cat">{{ item.category or 'News' }}</span>
 227 |                   <span class="fi-bdg" style="color:{{ item.sentiment_color or '#f59e0b' }}">{{ item.sentiment or 'NEUTRAL' }}</span>
 228 |                 </div>
 229 |                 <a class="fi-ttl" href="{{ item.url }}">{{ item.title }}</a>
 230 |               </div>
 231 |             </div>
 232 |             {% endfor %}
 233 |           {% else %}
 234 |             {% for i in range(6) %}
 235 |             <div class="fi">
 236 |               <span class="fi-ts">--:--</span>
 237 |               <div class="fi-body">
 238 |                 <div class="fi-meta"><span class="fi-src"><div class="lp" style="width:70px;height:9px"></div></span></div>
 239 |                 <div class="lp" style="height:12px;margin-top:4px"></div>
 240 |               </div>
 241 |             </div>
 242 |             {% endfor %}
 243 |           {% endif %}
 244 |         </div>
 245 |       </div>
 246 |     </div>
 247 |     <div class="panel">
 248 |       <div class="ph"><span class="pt"><span>F</span> &#8212; NOSTR RELAY MANAGER</span><span class="pm" id="nostr-sum">CONNECTING</span></div>
 249 |       <div class="pb">
 250 |         <div class="rbar" id="rbar">
 251 |           <div class="rpill cnx"><div class="rdot a"></div><span>relay.damus.io</span></div>
 252 |           <div class="rpill cnx"><div class="rdot a"></div><span>nos.lol</span></div>
 253 |           <div class="rpill cnx"><div class="rdot a"></div><span>relay.nostr.band</span></div>
 254 |         </div>
 255 |         <div id="nbox">
 256 |           <div class="nfb"><div class="nfi">&#9889;</div><div>Connecting to Nostr network</div><div style="margin-top:4px;font-size:10px;color:#374151">Subscribing to #bitcoin events (kind:1)</div></div>
 257 |         </div>
 258 |       </div>
 259 |     </div>
 260 |   </div>
 261 |   <div id="hs">
 262 |     <a class="hp" href="/"><div class="hp-ic">&#8383;</div><div class="hp-body"><div class="hp-lbl">BTC PRICE</div><div class="hp-val tgd" id="hp-price">$--</div></div><div class="hp-dlt" id="hp-price-d">--</div></a>
 263 |     <a class="hp" href="/charts"><div class="hp-ic">&#128279;</div><div class="hp-body"><div class="hp-lbl">MEMPOOL</div><div class="hp-val" id="hp-mpool">-- txs</div></div><div class="hp-dlt td" id="hp-mpool-f">--</div></a>
 264 |     <a class="hp" href="/charts"><div class="hp-ic">&#9935;</div><div class="hp-body"><div class="hp-lbl">HASHRATE</div><div class="hp-val" id="hp-hash">-- EH/s</div></div><div class="hp-dlt td">NETWORK</div></a>
 265 |     <a class="hp" href="/charts"><div class="hp-ic">&#128202;</div><div class="hp-body"><div class="hp-lbl">FEAR &amp; GREED</div><div class="hp-val" id="hp-fng">--</div></div><div class="hp-dlt" id="hp-fng-l">--</div></a>
 266 |     <a class="hp" href="/articles"><div class="hp-ic">&#128240;</div><div class="hp-body"><div class="hp-lbl">ARTICLES/HR</div><div class="hp-val tc" id="hp-ahr">--</div></div><div class="hp-dlt td">LAST HOUR</div></a>
 267 |     <a class="hp" href="/sentiment"><div class="hp-ic">&#129504;</div><div class="hp-body"><div class="hp-lbl">SENTIMENT</div><div class="hp-val" id="hp-sent">--</div></div><div class="hp-dlt" id="hp-sent-l">--</div></a>
 268 |     <a class="hp" href="#" onclick="document.getElementById('ci').scrollIntoView({behavior:'smooth'});return false"><div class="hp-ic">&#128225;</div><div class="hp-body"><div class="hp-lbl">SIGNAL</div><div class="hp-val" id="hp-sig">--</div></div><div class="hp-dlt" id="hp-sig-l">--</div></a>
 269 |   </div>
 270 | </div>
 271 | <script>
 272 | 'use strict';
 273 | function clk(){var n=new Date(),h=String(n.getUTCHours()).padStart(2,'0'),m=String(n.getUTCMinutes()).padStart(2,'0'),s=String(n.getUTCSeconds()).padStart(2,'0');document.getElementById('utcclock').textContent=h+':'+m+':'+s+' UTC'}
 274 | setInterval(clk,1000);clk();
 275 | function ago(iso){if(!iso)return'--';var d=(Date.now()-new Date(iso))/1000;if(d<60)return Math.floor(d)+'s';if(d<3600)return Math.floor(d/60)+'m';if(d<86400)return Math.floor(d/3600)+'h';return Math.floor(d/86400)+'d'}
 276 | function stime(iso){if(!iso)return'--:--';var d=new Date(iso);return String(d.getUTCHours()).padStart(2,'0')+':'+String(d.getUTCMinutes()).padStart(2,'0')}
 277 | function fmt(n){if(n>=1e6)return(n/1e6).toFixed(2)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'K';return String(n)}
 278 | function scol(s){return s>=60?'#22c55e':s>=30?'#f59e0b':'#ef4444'}
 279 | function sentcol(s){return s>=65?'#22c55e':s<=35?'#ef4444':'#f59e0b'}
 280 | function sentlbl(s){return s>=65?'BULLISH':s<=35?'BEARISH':'NEUTRAL'}
 281 | function setArc(score,color){var arc=document.getElementById('sc-arc'),num=document.getElementById('sc-num');if(!arc||!num)return;var c=2*Math.PI*30;arc.style.strokeDashoffset=c*(1-score/100);arc.style.stroke=color;num.textContent=score;num.style.color=color}
 282 | function renderSignal(d){
 283 |   if(!d)return;var col=d.color||scol(d.score);
 284 |   var v=document.getElementById('hdr-sig-val'),b=document.getElementById('hdr-sig-bdg');
 285 |   if(v){v.textContent=d.score;v.style.color=col}if(b){b.textContent=d.label||'--';b.style.color=col}
 286 |   setArc(d.score,col);
 287 |   var ml=document.getElementById('sig-main');if(ml){ml.textContent=d.label;ml.style.color=col}
 288 |   var su=document.getElementById('sig-updated');if(su&&d.computed_at)su.textContent=ago(d.computed_at)+' AGO';
 289 |   var hs=document.getElementById('hp-sig'),hsl=document.getElementById('hp-sig-l');
 290 |   if(hs){hs.textContent=d.score;hs.style.color=col}if(hsl){hsl.textContent=d.label;hsl.style.color=col}
 291 |   var container=document.getElementById('sig-comps');if(!container||!d.components)return;
 292 |   container.innerHTML='';
 293 |   Object.values(d.components).forEach(function(c){var bc=scol(c.score),dc=c.delta>0?'tg':c.delta<0?'tr':'td',abs=Math.abs(c.delta);container.insertAdjacentHTML('beforeend','<div class="scomp"><span class="scomp-lbl">'+c.label+'</span><div class="scomp-bw"><div class="scomp-b" style="width:'+c.score+'%;background:'+bc+'"></div></div><span class="scomp-s" style="color:'+bc+'">'+c.score+'</span><span class="scomp-d '+dc+'">'+(c.delta!==0?abs+'%':'&mdash;')+'</span></div>')});
 294 | }
 295 | function renderHeatmap(d){if(!d||!d.cells)return;var g=document.getElementById('hmg');if(!g)return;g.innerHTML='';d.cells.forEach(function(c){g.insertAdjacentHTML('beforeend','<div class="hmc"><div class="hmc-cat">'+c.category.toUpperCase()+'</div><div class="hmc-sent" style="color:'+c.color+'">'+c.label+'</div><div class="hmc-cnt">'+c.count_2h+' articles (2h)</div></div>')})}
 296 | function renderTopics(d){var c=document.getElementById('topics');if(!c)return;var topics=(d&&d.topics)||[];if(!topics.length){c.innerHTML='<div class="td" style="padding:12px;font-size:11px">No topic data yet</div>';return}c.innerHTML='';topics.slice(0,10).forEach(function(t,i){var tr=i<3?'&#9650;':i>7?'&#9660;':'&mdash;',tc=i<3?'tg':i>7?'tr':'td';c.insertAdjacentHTML('beforeend','<div class="trow"><span class="trnk">'+(i+1)+'</span><span class="trnm">'+(t.topic||'&mdash;')+'</span><span class="trcnt">'+(t.count||0)+'</span><span class="trnd '+tc+'">'+tr+'</span></div>')})}
 297 | function renderSources(d){var g=document.getElementById('srcg');if(!g)return;var sources=(d&&d.sources)||[];if(!sources.length){g.innerHTML='<div class="td" style="padding:12px;font-size:11px;grid-column:1/-1">No source data</div>';return}g.innerHTML='';sources.slice(0,12).forEach(function(s){var age=s.age_hours<1?'just now':s.age_hours+'h ago';g.insertAdjacentHTML('beforeend','<div class="si"><div class="sdot '+s.status+'"></div><div class="si-info"><div class="si-name">'+s.name+'</div><div class="si-meta">'+s.articles_today+' today &middot; '+age+'</div></div></div>')});var u=document.getElementById('src-updated');if(u&&d.computed_at)u.textContent=ago(d.computed_at)+' AGO'}
 298 | var knownIds=new Set();
 299 | function mkFI(item){var bc=item.sentiment_color||(item.sentiment==='BULLISH'?'#22c55e':item.sentiment==='BEARISH'?'#ef4444':'#f59e0b');var ts=stime(item.timestamp);var el=document.createElement('div');el.className='fi';el.innerHTML='<span class="fi-ts">'+ts+'</span><div class="fi-body"><div class="fi-meta"><span class="fi-src">'+String(item.source||'PP').substring(0,20)+'</span><span class="fi-cat">'+(item.category||'News')+'</span><span class="fi-bdg" style="color:'+bc+'">'+(item.sentiment||'NEUTRAL')+'</span></div><a class="fi-ttl" href="'+item.url+'">'+item.title+'</a></div>';return el}
 300 | function renderFeed(d){if(!d||!d.items||!d.items.length)return;var box=document.getElementById('feedbox'),cnt=document.getElementById('feed-cnt');if(box)box.innerHTML='';if(cnt)cnt.textContent=d.items.length+' articles';d.items.forEach(function(item){knownIds.add(item.id);if(box)box.appendChild(mkFI(item))})}
 301 | function prependFI(item){var box=document.getElementById('feedbox');if(!box)return;box.insertBefore(mkFI(item),box.firstChild);while(box.children.length>30)box.removeChild(box.lastChild)}
 302 | function pollFeed(){fetch('/api/media/feed/intelligence?limit=20').then(function(r){return r.json()}).then(function(d){if(!d||!d.items)return;var cnt=document.getElementById('feed-cnt');if(cnt)cnt.textContent=d.items.length+' articles';var newI=d.items.filter(function(i){return!knownIds.has(i.id)});if(newI.length&&knownIds.size>0)newI.forEach(function(i){prependFI(i)});else if(knownIds.size===0)renderFeed(d);d.items.forEach(function(i){knownIds.add(i.id)})}).catch(function(){})}
 303 | function initFeed(){if(typeof EventSource!=='undefined'){var es=new EventSource('/api/media/feed/stream');es.addEventListener('article',function(e){try{var i=JSON.parse(e.data);if(i&&i.id&&!knownIds.has(i.id)){knownIds.add(i.id);prependFI(i)}}catch(_){}});es.onerror=function(){es.close();setInterval(pollFeed,30000)}}else{setInterval(pollFeed,30000)}}
 304 | var RELAYS=[{url:'wss://relay.damus.io',name:'relay.damus.io'},{url:'wss://nos.lol',name:'nos.lol'},{url:'wss://relay.nostr.band',name:'relay.nostr.band'}];
 305 | var NR={};
 306 | function updRelays(){var bar=document.getElementById('rbar'),sum=document.getElementById('nostr-sum');if(!bar)return;bar.innerHTML='';var conn=0;RELAYS.forEach(function(r){var s=NR[r.url]||{},st=s.status||'cnx';if(st==='conn')conn++;var dc=st==='conn'?'g':st==='cnx'?'a':'r',pc=st==='conn'?'conn':st==='cnx'?'cnx':'err';var rate=s.cnt&&s.at?Math.round(s.cnt/((Date.now()-s.at)/60000))+'/min':'';bar.insertAdjacentHTML('beforeend','<div class="rpill '+pc+'"><div class="rdot '+dc+'"></div><span>'+r.name+'</span>'+(rate?'<span class="td" style="margin-left:2px">'+rate+'</span>':'')+'</div>')});if(sum)sum.textContent=conn+'/'+RELAYS.length+' CONNECTED'}
 307 | function renderNostr(ev){if(!ev||!ev.content)return;var box=document.getElementById('nbox');if(!box)return;var fb=box.querySelector('.nfb');if(fb)fb.remove();var npk=(ev.pubkey||'').substring(0,12)+'&hellip;';var ts=ev.created_at?new Date(ev.created_at*1000).toISOString():null;var content=(ev.content||'').substring(0,280).replace(/</g,'&lt;').replace(/>/g,'&gt;');var rh='https://robohash.org/'+(ev.pubkey||'anon').substring(0,8)+'?set=set4&size=20x20';var el=document.createElement('div');el.className='ne';el.innerHTML='<div class="ne-meta"><div class="navt"><img src="'+rh+'" alt="" loading="lazy" onerror="this.style.display=\'none\'"></div><span class="npk">'+npk+'</span><span class="nts">'+(ts?ago(ts)+' ago':'')+'</span></div><div class="nc">'+content+'</div>';box.insertBefore(el,box.firstChild);while(box.children.length>25)box.removeChild(box.lastChild)}
 308 | function connectRelay(relay){if(!('WebSocket' in window))return;var s={status:'cnx',cnt:0,at:null,ws:null};NR[relay.url]=s;var ws;try{ws=new WebSocket(relay.url);s.ws=ws}catch(e){s.status='err';updRelays();return}var to=setTimeout(function(){if(s.status==='cnx'){s.status='err';updRelays();ws.close()}},8000);ws.onopen=function(){clearTimeout(to);s.status='conn';s.at=Date.now();updRelays();var sid='pp-'+Math.random().toString(36).slice(2,8);ws.send(JSON.stringify(['REQ',sid,{kinds:[1],'#t':['bitcoin','btc','lightning'],limit:20}]))};ws.onmessage=function(e){try{var m=JSON.parse(e.data);if(m[0]==='EVENT'){s.cnt++;var ev=m[2];if(ev&&ev.kind===1){renderNostr(ev);updRelays()}}}catch(_){}};ws.onerror=function(){s.status='err';updRelays()};ws.onclose=function(){if(s.status!=='err')s.status='err';updRelays();setTimeout(function(){connectRelay(relay)},30000)}}
 309 | function initNostr(){if(!('WebSocket' in window)){var b=document.getElementById('nbox');if(b)b.innerHTML='<div class="nfb"><div class="nfi">&#9889;</div><div>WebSocket not supported</div></div>';return}RELAYS.forEach(function(r){connectRelay(r)})}
 310 | function updPrice(){fetch('/api/v2/terminal/price').then(function(r){return r.json()}).then(function(d){var p=d.data&&d.data.usd,ch=d.data&&d.data.change_24h_pct;if(p){var el=document.getElementById('hp-price');if(el)el.textContent='$'+Number(p).toLocaleString()}if(ch!==undefined){var el=document.getElementById('hp-price-d');if(el){el.textContent=(ch>=0?'&#9650; ':'&#9660; ')+Math.abs(ch).toFixed(2)+'%';el.style.color=ch>=0?'#22c55e':'#ef4444'}}}).catch(function(){})}
 311 | function updMpool(){fetch('https://mempool.space/api/mempool').then(function(r){return r.json()}).then(function(d){var el=document.getElementById('hp-mpool');if(el)el.textContent=fmt(d.count||0)+' txs';var fe=document.getElementById('hp-mpool-f');if(fe&&d.vsize)fe.textContent=Math.round(d.vsize/1e6)+'MvB'}).catch(function(){})}
 312 | function updHash(){fetch('https://mempool.space/api/v1/mining/hashrate/1m').then(function(r){return r.json()}).then(function(d){var el=document.getElementById('hp-hash');if(el&&d.currentHashrate)el.textContent=(d.currentHashrate/1e18).toFixed(1)+' EH/s'}).catch(function(){})}
 313 | function updFng(){fetch('https://api.alternative.me/fng/?limit=1').then(function(r){return r.json()}).then(function(d){var item=d.data&&d.data[0];if(!item)return;var score=Number(item.value),lbl=item.value_classification,col=score>=60?'#22c55e':score>=40?'#f59e0b':'#ef4444';var fe=document.getElementById('hp-fng');if(fe){fe.textContent=score;fe.style.color=col}var fl=document.getElementById('hp-fng-l');if(fl){fl.textContent=lbl.toUpperCase();fl.style.color=col}}).catch(function(){})}
 314 | function updAhr(){fetch('/api/media/feed/intelligence?limit=50').then(function(r){return r.json()}).then(function(d){var items=d.items||[],cut=Date.now()-3600000;var n=items.filter(function(i){return i.timestamp&&new Date(i.timestamp).getTime()>cut}).length;var el=document.getElementById('hp-ahr');if(el)el.textContent=n}).catch(function(){})}
 315 | function updSent(){fetch('/api/media/sentiment').then(function(r){return r.json()}).then(function(d){var s=d.score||50,col=sentcol(s),lbl=sentlbl(s);var se=document.getElementById('hp-sent'),sl=document.getElementById('hp-sent-l');if(se){se.textContent=s;se.style.color=col}if(sl){sl.textContent=lbl;sl.style.color=col}}).catch(function(){})}
 316 | function fetchSignal(){return fetch('/api/signal/composite').then(function(r){return r.json()}).then(renderSignal).catch(function(e){console.warn('signal',e)})}
 317 | function fetchHmap(){return fetch('/api/sentiment/heatmap').then(function(r){return r.json()}).then(renderHeatmap).catch(function(e){console.warn('hmap',e)})}
 318 | function fetchTopics(){return fetch('/api/v2/terminal/topics').then(function(r){return r.json()}).then(function(d){var t=d.data?d.data.topics:(d.topics||d);renderTopics({topics:t})}).catch(function(e){console.warn('topics',e)})}
 319 | function fetchSrc(){return fetch('/api/media/sources/health').then(function(r){return r.json()}).then(renderSources).catch(function(e){console.warn('src',e)})}
 320 | function init(){
 321 |   Promise.all([fetchSignal(),fetchHmap(),fetchTopics(),fetchSrc()]).catch(function(){});
 322 |   pollFeed();initFeed();
 323 |   updPrice();updMpool();updHash();updFng();updAhr();updSent();
 324 |   initNostr();
 325 | }
 326 | setInterval(fetchSignal,120000);setInterval(fetchHmap,300000);setInterval(fetchTopics,300000);setInterval(fetchSrc,300000);
 327 | setInterval(updPrice,60000);setInterval(updMpool,30000);setInterval(updHash,300000);setInterval(updFng,3600000);setInterval(updAhr,60000);setInterval(updSent,120000);
 328 | init();
 329 | </script>
 330 | </body>
 331 | </html>
```

### File: templates/oracle_live.html (774 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Oracle Live — Protocol Pulse{% endblock %}
   3 | 
   4 | {% block head %}
   5 | <meta name="description" content="Oracle — Live AI briefings by Protocol Pulse. Three daily Bitcoin market updates delivered by Sarah.">
   6 | <style>
   7 | /* ═══════════════════════════════════════════════════════════
   8 |    ORACLE LIVE — SESSION 7
   9 |    Dark cinematic broadcast aesthetic
  10 | ═══════════════════════════════════════════════════════════ */
  11 | :root {
  12 |   --oracle-bg:       #050507;
  13 |   --oracle-surface:  #0c0c10;
  14 |   --oracle-card:     #111118;
  15 |   --oracle-border:   rgba(220,38,38,.18);
  16 |   --oracle-border-h: rgba(220,38,38,.42);
  17 |   --oracle-red:      #dc2626;
  18 |   --oracle-gold:     #f59e0b;
  19 |   --oracle-gold-dim: rgba(245,158,11,.15);
  20 |   --oracle-text:     #e5e5e5;
  21 |   --oracle-muted:    rgba(229,229,229,.45);
  22 |   --oracle-faint:    rgba(229,229,229,.18);
  23 |   --oracle-mono:     'JetBrains Mono','Courier New',monospace;
  24 |   --oracle-green:    #22c55e;
  25 |   --oracle-amber:    #f59e0b;
  26 | }
  27 | 
  28 | body { background: var(--oracle-bg) !important; }
  29 | .navbar, footer, .pp-ticker { display: none !important; }
  30 | 
  31 | /* ── page wrapper ── */
  32 | .oracle-wrap {
  33 |   min-height: 100vh;
  34 |   background: var(--oracle-bg);
  35 |   font-family: var(--oracle-mono);
  36 |   color: var(--oracle-text);
  37 |   padding-bottom: 80px;
  38 | }
  39 | 
  40 | /* ── top bar ── */
  41 | .oracle-topbar {
  42 |   position: sticky; top: 0; z-index: 100;
  43 |   background: rgba(5,5,7,.95);
  44 |   backdrop-filter: blur(12px);
  45 |   border-bottom: 1px solid var(--oracle-border);
  46 |   display: flex; align-items: center; justify-content: space-between;
  47 |   padding: 14px 32px;
  48 | }
  49 | .oracle-topbar-brand {
  50 |   font-size: .68rem; letter-spacing: .25em; color: var(--oracle-red);
  51 |   text-transform: uppercase; text-decoration: none;
  52 | }
  53 | .oracle-topbar-meta {
  54 |   display: flex; align-items: center; gap: 20px;
  55 |   font-size: .65rem; letter-spacing: .1em; color: var(--oracle-muted);
  56 | }
  57 | .live-dot {
  58 |   display: inline-block; width: 7px; height: 7px;
  59 |   border-radius: 50%; background: var(--oracle-red);
  60 |   animation: pulse-dot 1.8s ease-in-out infinite;
  61 | }
  62 | @keyframes pulse-dot {
  63 |   0%,100%{ opacity:1; transform:scale(1); }
  64 |   50%{ opacity:.4; transform:scale(.75); }
  65 | }
  66 | .oracle-topbar-btc {
  67 |   font-size: .7rem; color: var(--oracle-gold); letter-spacing: .05em;
  68 | }
  69 | 
  70 | /* ── hero section ── */
  71 | .oracle-hero {
  72 |   max-width: 1200px; margin: 0 auto;
  73 |   padding: 40px 24px 0;
  74 | }
  75 | .oracle-hero-inner {
  76 |   display: grid; grid-template-columns: 1fr 320px; gap: 24px;
  77 |   align-items: start;
  78 | }
  79 | @media (max-width: 900px) {
  80 |   .oracle-hero-inner { grid-template-columns: 1fr; }
  81 | }
  82 | 
  83 | /* ── video player ── */
  84 | .oracle-player-wrap {
  85 |   background: var(--oracle-card);
  86 |   border: 1px solid var(--oracle-border);
  87 |   border-radius: 4px;
  88 |   overflow: hidden;
  89 |   position: relative;
  90 | }
  91 | .oracle-player-badge {
  92 |   position: absolute; top: 14px; left: 14px; z-index: 10;
  93 |   background: rgba(220,38,38,.9);
  94 |   font-size: .58rem; letter-spacing: .18em; color: #fff;
  95 |   padding: 3px 8px; border-radius: 2px; text-transform: uppercase;
  96 |   display: flex; align-items: center; gap: 5px;
  97 | }
  98 | .oracle-video {
  99 |   width: 100%; aspect-ratio: 16/9;
 100 |   background: #000;
 101 |   display: block;
 102 | }
 103 | .oracle-video-placeholder {
 104 |   width: 100%; aspect-ratio: 16/9;
 105 |   background: linear-gradient(135deg, #0a0a0f 0%, #111120 100%);
 106 |   display: flex; flex-direction: column;
 107 |   align-items: center; justify-content: center;
 108 |   color: var(--oracle-muted); font-size: .7rem; letter-spacing: .12em;
 109 |   text-transform: uppercase; gap: 12px;
 110 | }
 111 | .oracle-video-placeholder svg { width: 48px; height: 48px; opacity: .3; }
 112 | .oracle-player-controls {
 113 |   padding: 12px 16px;
 114 |   display: flex; align-items: center; justify-content: space-between;
 115 |   border-top: 1px solid var(--oracle-border);
 116 | }
 117 | .oracle-player-title {
 118 |   font-size: .72rem; color: var(--oracle-text); letter-spacing: .04em;
 119 |   flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
 120 | }
 121 | .oracle-unmute-btn {
 122 |   background: rgba(220,38,38,.15); border: 1px solid rgba(220,38,38,.3);
 123 |   color: var(--oracle-red); font-family: var(--oracle-mono);
 124 |   font-size: .62rem; letter-spacing: .1em; text-transform: uppercase;
 125 |   padding: 5px 12px; cursor: pointer; border-radius: 2px;
 126 |   transition: background .2s;
 127 | }
 128 | .oracle-unmute-btn:hover { background: rgba(220,38,38,.28); }
 129 | .oracle-share-btn {
 130 |   background: none; border: 1px solid var(--oracle-border);
 131 |   color: var(--oracle-muted); font-family: var(--oracle-mono);
 132 |   font-size: .62rem; letter-spacing: .1em; text-transform: uppercase;
 133 |   padding: 5px 12px; cursor: pointer; border-radius: 2px; margin-left: 8px;
 134 |   transition: border-color .2s, color .2s;
 135 | }
 136 | .oracle-share-btn:hover { border-color: var(--oracle-gold); color: var(--oracle-gold); }
 137 | 
 138 | /* transcript */
 139 | .oracle-transcript-toggle {
 140 |   width: 100%; background: none;
 141 |   border: none; border-top: 1px solid var(--oracle-border);
 142 |   color: var(--oracle-muted); font-family: var(--oracle-mono);
 143 |   font-size: .63rem; letter-spacing: .12em; text-transform: uppercase;
 144 |   padding: 10px 16px; cursor: pointer; text-align: left;
 145 |   display: flex; align-items: center; justify-content: space-between;
 146 |   transition: color .2s;
 147 | }
 148 | .oracle-transcript-toggle:hover { color: var(--oracle-text); }
 149 | .oracle-transcript-body {
 150 |   display: none; padding: 16px;
 151 |   font-size: .68rem; line-height: 1.8; color: var(--oracle-muted);
 152 |   border-top: 1px solid rgba(220,38,38,.08);
 153 |   max-height: 180px; overflow-y: auto;
 154 | }
 155 | .oracle-transcript-body.open { display: block; }
 156 | 
 157 | /* ── status sidebar ── */
 158 | .oracle-sidebar { display: flex; flex-direction: column; gap: 16px; }
 159 | 
 160 | .oracle-status-card {
 161 |   background: var(--oracle-card);
 162 |   border: 1px solid var(--oracle-border);
 163 |   border-radius: 4px;
 164 |   padding: 16px;
 165 | }
 166 | .oracle-card-label {
 167 |   font-size: .58rem; letter-spacing: .22em; color: var(--oracle-muted);
 168 |   text-transform: uppercase; margin-bottom: 12px;
 169 |   border-bottom: 1px solid rgba(220,38,38,.08); padding-bottom: 8px;
 170 | }
 171 | 
 172 | /* system health row */
 173 | .sys-row {
 174 |   display: flex; align-items: center; justify-content: space-between;
 175 |   padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,.04);
 176 | }
 177 | .sys-row:last-child { border-bottom: none; }
 178 | .sys-name { font-size: .65rem; color: var(--oracle-text); }
 179 | .sys-status {
 180 |   font-size: .58rem; letter-spacing: .1em; text-transform: uppercase;
 181 |   display: flex; align-items: center; gap: 5px;
 182 | }
 183 | .sys-dot { width: 6px; height: 6px; border-radius: 50%; }
 184 | .sys-dot.ok { background: var(--oracle-green); }
 185 | .sys-dot.err { background: var(--oracle-red); }
 186 | 
 187 | /* countdown */
 188 | .oracle-countdown {
 189 |   text-align: center; padding: 8px 0;
 190 | }
 191 | .oracle-countdown-value {
 192 |   font-size: 1.6rem; color: var(--oracle-gold);
 193 |   letter-spacing: .05em; line-height: 1;
 194 | }
 195 | .oracle-countdown-label {
 196 |   font-size: .58rem; color: var(--oracle-muted); letter-spacing: .15em;
 197 |   margin-top: 6px; text-transform: uppercase;
 198 | }
 199 | .oracle-countdown-slot {
 200 |   font-size: .65rem; color: var(--oracle-text); margin-top: 4px;
 201 | }
 202 | 
 203 | /* meta pills */
 204 | .oracle-meta-row {
 205 |   display: flex; align-items: center; justify-content: space-between;
 206 |   padding: 5px 0;
 207 | }
 208 | .oracle-meta-key { font-size: .6rem; color: var(--oracle-muted); }
 209 | .oracle-meta-val { font-size: .65rem; color: var(--oracle-text); }
 210 | .oracle-progress-bar {
 211 |   width: 100%; height: 3px; background: rgba(255,255,255,.06);
 212 |   border-radius: 2px; margin-top: 8px; overflow: hidden;
 213 | }
 214 | .oracle-progress-fill {
 215 |   height: 100%; background: var(--oracle-red);
 216 |   border-radius: 2px; transition: width .5s ease;
 217 | }
 218 | 
 219 | /* ── schedule section ── */
 220 | .oracle-section {
 221 |   max-width: 1200px; margin: 32px auto 0;
 222 |   padding: 0 24px;
 223 | }
 224 | .oracle-section-title {
 225 |   font-size: .62rem; letter-spacing: .22em; color: var(--oracle-muted);
 226 |   text-transform: uppercase;
 227 |   border-bottom: 1px solid var(--oracle-border);
 228 |   padding-bottom: 10px; margin-bottom: 20px;
 229 | }
 230 | 
 231 | /* schedule grid */
 232 | .oracle-schedule-grid {
 233 |   display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
 234 | }
 235 | @media (max-width: 700px) {
 236 |   .oracle-schedule-grid { grid-template-columns: 1fr; }
 237 | }
 238 | 
 239 | .oracle-slot-card {
 240 |   background: var(--oracle-card);
 241 |   border: 1px solid var(--oracle-border);
 242 |   border-radius: 4px;
 243 |   padding: 16px;
 244 |   transition: border-color .2s;
 245 |   position: relative;
 246 |   overflow: hidden;
 247 | }
 248 | .oracle-slot-card:hover { border-color: var(--oracle-border-h); }
 249 | .oracle-slot-card.completed {
 250 |   border-color: rgba(34,197,94,.2);
 251 | }
 252 | .oracle-slot-card.completed::before {
 253 |   content: ''; position: absolute; top: 0; left: 0;
 254 |   width: 3px; height: 100%;
 255 |   background: var(--oracle-green);
 256 | }
 257 | .oracle-slot-card.generating {
 258 |   border-color: rgba(245,158,11,.3);
 259 | }
 260 | .oracle-slot-card.generating::before {
 261 |   content: ''; position: absolute; top: 0; left: 0;
 262 |   width: 3px; height: 100%;
 263 |   background: var(--oracle-gold);
 264 |   animation: gen-pulse 1.5s ease-in-out infinite;
 265 | }
 266 | @keyframes gen-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
 267 | 
 268 | .slot-time {
 269 |   font-size: .6rem; color: var(--oracle-muted); letter-spacing: .1em;
 270 |   text-transform: uppercase; margin-bottom: 6px;
 271 | }
 272 | .slot-title {
 273 |   font-size: .8rem; color: var(--oracle-text);
 274 |   margin-bottom: 6px;
 275 | }
 276 | .slot-desc {
 277 |   font-size: .6rem; color: var(--oracle-muted); line-height: 1.5;
 278 |   margin-bottom: 12px;
 279 | }
 280 | .slot-status {
 281 |   font-size: .58rem; letter-spacing: .12em; text-transform: uppercase;
 282 |   display: flex; align-items: center; gap: 6px;
 283 | }
 284 | .slot-badge {
 285 |   padding: 3px 8px; border-radius: 2px;
 286 |   font-size: .56rem; letter-spacing: .12em;
 287 | }
 288 | .slot-badge.ready {
 289 |   background: rgba(34,197,94,.12); color: var(--oracle-green);
 290 |   border: 1px solid rgba(34,197,94,.2);
 291 | }
 292 | .slot-badge.gen {
 293 |   background: rgba(245,158,11,.12); color: var(--oracle-gold);
 294 |   border: 1px solid rgba(245,158,11,.2);
 295 | }
 296 | .slot-badge.pending {
 297 |   background: rgba(229,229,229,.06); color: var(--oracle-muted);
 298 |   border: 1px solid rgba(229,229,229,.1);
 299 | }
 300 | .slot-watch-btn {
 301 |   display: inline-block; margin-top: 10px;
 302 |   background: none; border: 1px solid rgba(34,197,94,.25);
 303 |   color: var(--oracle-green); font-family: var(--oracle-mono);
 304 |   font-size: .6rem; letter-spacing: .12em; text-transform: uppercase;
 305 |   padding: 5px 12px; cursor: pointer; border-radius: 2px;
 306 |   text-decoration: none; transition: background .2s;
 307 | }
 308 | .slot-watch-btn:hover { background: rgba(34,197,94,.1); color: var(--oracle-green); }
 309 | .slot-duration {
 310 |   font-size: .58rem; color: var(--oracle-muted); margin-left: 8px;
 311 | }
 312 | 
 313 | /* thumbnail */
 314 | .slot-thumb {
 315 |   width: 100%; aspect-ratio: 16/9;
 316 |   object-fit: cover; border-radius: 2px;
 317 |   margin-bottom: 10px; display: block;
 318 | }
 319 | .slot-thumb-placeholder {
 320 |   width: 100%; aspect-ratio: 16/9;
 321 |   background: linear-gradient(135deg, #0a0a10, #12121e);
 322 |   border-radius: 2px; margin-bottom: 10px;
 323 |   display: flex; align-items: center; justify-content: center;
 324 |   color: var(--oracle-faint); font-size: .6rem; letter-spacing: .1em;
 325 |   text-transform: uppercase;
 326 | }
 327 | 
 328 | /* ── archive grid ── */
 329 | .oracle-archive-grid {
 330 |   display: grid;
 331 |   grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
 332 |   gap: 16px;
 333 | }
 334 | .oracle-archive-card {
 335 |   background: var(--oracle-card);
 336 |   border: 1px solid var(--oracle-border);
 337 |   border-radius: 4px;
 338 |   padding: 14px;
 339 |   transition: border-color .2s, transform .2s;
 340 |   cursor: pointer;
 341 | }
 342 | .oracle-archive-card:hover {
 343 |   border-color: var(--oracle-border-h);
 344 |   transform: translateY(-2px);
 345 | }
 346 | .archive-thumb {
 347 |   width: 100%; aspect-ratio: 16/9;
 348 |   object-fit: cover; border-radius: 2px;
 349 |   margin-bottom: 10px; display: block;
 350 | }
 351 | .archive-thumb-placeholder {
 352 |   width: 100%; aspect-ratio: 16/9;
 353 |   background: linear-gradient(135deg, #0a0a10, #12121e);
 354 |   border-radius: 2px; margin-bottom: 10px;
 355 |   display: flex; align-items: center; justify-content: center;
 356 |   color: var(--oracle-faint); font-size: .55rem; letter-spacing: .1em;
 357 | }
 358 | .archive-date { font-size: .58rem; color: var(--oracle-muted); margin-bottom: 4px; }
 359 | .archive-title { font-size: .72rem; color: var(--oracle-text); margin-bottom: 6px; line-height: 1.35; }
 360 | .archive-meta { font-size: .58rem; color: var(--oracle-muted); display: flex; gap: 8px; align-items: center; }
 361 | .archive-type-badge {
 362 |   background: rgba(220,38,38,.1); color: var(--oracle-red);
 363 |   border: 1px solid rgba(220,38,38,.2);
 364 |   padding: 2px 7px; border-radius: 2px;
 365 |   font-size: .54rem; letter-spacing: .1em; text-transform: uppercase;
 366 | }
 367 | .oracle-empty {
 368 |   text-align: center; padding: 40px 20px;
 369 |   color: var(--oracle-muted); font-size: .68rem; letter-spacing: .1em;
 370 |   text-transform: uppercase;
 371 | }
 372 | 
 373 | /* ── modal overlay for archive playback ── */
 374 | .oracle-modal {
 375 |   display: none; position: fixed; inset: 0; z-index: 200;
 376 |   background: rgba(0,0,0,.88);
 377 |   align-items: center; justify-content: center;
 378 | }
 379 | .oracle-modal.open { display: flex; }
 380 | .oracle-modal-inner {
 381 |   width: min(860px, 95vw);
 382 |   background: var(--oracle-card);
 383 |   border: 1px solid var(--oracle-border);
 384 |   border-radius: 4px;
 385 |   overflow: hidden;
 386 | }
 387 | .oracle-modal-video { width: 100%; aspect-ratio: 16/9; display: block; background: #000; }
 388 | .oracle-modal-info {
 389 |   padding: 16px;
 390 |   display: flex; align-items: center; justify-content: space-between;
 391 | }
 392 | .oracle-modal-title { font-size: .8rem; color: var(--oracle-text); }
 393 | .oracle-modal-close {
 394 |   background: none; border: 1px solid var(--oracle-border);
 395 |   color: var(--oracle-muted); font-family: var(--oracle-mono);
 396 |   font-size: .6rem; letter-spacing: .1em; padding: 5px 12px;
 397 |   cursor: pointer; border-radius: 2px;
 398 | }
 399 | .oracle-modal-close:hover { color: var(--oracle-text); border-color: var(--oracle-border-h); }
 400 | </style>
 401 | {% endblock %}
 402 | 
 403 | {% block content %}
 404 | <div class="oracle-wrap">
 405 | 
 406 |   {# ── TOP BAR ── #}
 407 |   <div class="oracle-topbar">
 408 |     <a href="/" class="oracle-topbar-brand">PROTOCOL PULSE // ORACLE</a>
 409 |     <div class="oracle-topbar-meta">
 410 |       {% if btc_price %}
 411 |       <span class="oracle-topbar-btc">BTC ${{ "{:,.0f}".format(btc_price) }}</span>
 412 |       {% endif %}
 413 |       <span><span class="live-dot"></span> {{ now_et }}</span>
 414 |       <span>{{ et_date }}</span>
 415 |     </div>
 416 |   </div>
 417 | 
 418 |   {# ── HERO — PLAYER + SIDEBAR ── #}
 419 |   <div class="oracle-hero">
 420 |     <div class="oracle-hero-inner">
 421 | 
 422 |       {# LEFT: video player #}
 423 |       <div>
 424 |         <div class="oracle-player-wrap" id="heroPlayerWrap">
 425 | 
 426 |           {% if hero_briefing and hero_briefing.video_url %}
 427 |             <div class="oracle-player-badge">
 428 |               <span class="live-dot"></span> ORACLE BRIEFING
 429 |             </div>
 430 |             <video
 431 |               id="heroVideo"
 432 |               class="oracle-video"
 433 |               autoplay
 434 |               muted
 435 |               playsinline
 436 |               controls
 437 |               preload="metadata"
 438 |               poster="{{ hero_briefing.thumbnail_url or '' }}"
 439 |               data-src="{{ hero_briefing.video_url }}"
 440 |             >
 441 |               <source src="{{ hero_briefing.video_url }}" type="video/mp4">
 442 |               Your browser does not support video.
 443 |             </video>
 444 |             <div class="oracle-player-controls">
 445 |               <span class="oracle-player-title">{{ hero_briefing.title or 'Oracle Briefing' }}</span>
 446 |               {% if hero_briefing.duration_seconds %}
 447 |               <span style="font-size:.6rem;color:var(--oracle-muted);margin-right:8px;">
 448 |                 {{ "%.0f"|format(hero_briefing.duration_seconds // 60) }}:{{ "%02d"|format((hero_briefing.duration_seconds % 60)|int) }}
 449 |               </span>
 450 |               {% endif %}
 451 |               <button class="oracle-unmute-btn" id="unmuteBtn" onclick="toggleMute()">UNMUTE</button>
 452 |               <button class="oracle-share-btn" onclick="shareBriefing()">SHARE ↗</button>
 453 |             </div>
 454 |             {% if hero_briefing.script_text %}
 455 |             <button class="oracle-transcript-toggle" onclick="toggleTranscript(this)">
 456 |               <span>TRANSCRIPT</span>
 457 |               <span>▼</span>
 458 |             </button>
 459 |             <div class="oracle-transcript-body" id="heroTranscript">
 460 |               {{ hero_briefing.script_text }}
 461 |             </div>
 462 |             {% endif %}
 463 | 
 464 |           {% else %}
 465 |             <div class="oracle-video-placeholder">
 466 |               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
 467 |                 <circle cx="12" cy="12" r="10"/>
 468 |                 <polygon points="10,8 16,12 10,16"/>
 469 |               </svg>
 470 |               <span>NEXT BRIEFING GENERATING</span>
 471 |               <span style="font-size:.55rem;color:var(--oracle-faint);">
 472 |                 Check back at {{ next_slot.time_et }}
 473 |               </span>
 474 |             </div>
 475 |             <div class="oracle-player-controls">
 476 |               <span class="oracle-player-title" style="color:var(--oracle-muted);">No briefings published yet today</span>
 477 |             </div>
 478 |           {% endif %}
 479 | 
 480 |         </div>{# /player-wrap #}
 481 |       </div>{# /left column #}
 482 | 
 483 |       {# RIGHT: status sidebar #}
 484 |       <div class="oracle-sidebar">
 485 | 
 486 |         {# System health #}
 487 |         <div class="oracle-status-card">
 488 |           <div class="oracle-card-label">System Status</div>
 489 |           {% for key, svc in system_status.items() %}
 490 |           <div class="sys-row">
 491 |             <span class="sys-name">{{ svc.label }}</span>
 492 |             <span class="sys-status">
 493 |               <span class="sys-dot {{ 'ok' if svc.ok else 'err' }}"></span>
 494 |               {{ 'ONLINE' if svc.ok else 'OFFLINE' }}
 495 |             </span>
 496 |           </div>
 497 |           {% endfor %}
 498 |         </div>
 499 | 
 500 |         {# Countdown #}
 501 |         <div class="oracle-status-card">
 502 |           <div class="oracle-card-label">Next Briefing</div>
 503 |           <div class="oracle-countdown">
 504 |             <div class="oracle-countdown-value" id="countdownDisplay">{{ next_slot.eta_str }}</div>
 505 |             <div class="oracle-countdown-label">until next briefing</div>
 506 |             <div class="oracle-countdown-slot">{{ next_slot.label }}</div>
 507 |             <div style="font-size:.58rem;color:var(--oracle-muted);margin-top:3px;">{{ next_slot.time_et }}</div>
 508 |           </div>
 509 |           <div class="oracle-progress-bar">
 510 |             <div class="oracle-progress-fill" id="countdownBar" style="width:0%"></div>
 511 |           </div>
 512 |         </div>
 513 | 
 514 |         {# Daily stats #}
 515 |         <div class="oracle-status-card">
 516 |           <div class="oracle-card-label">Today's Briefings</div>
 517 |           <div class="oracle-meta-row">
 518 |             <span class="oracle-meta-key">Generated</span>
 519 |             <span class="oracle-meta-val">{{ today_completed }}/3</span>
 520 |           </div>
 521 |           <div class="oracle-meta-row">
 522 |             <span class="oracle-meta-key">Schedule</span>
 523 |             <span class="oracle-meta-val">8AM · 12PM · 5PM ET</span>
 524 |           </div>
 525 |           {% if fear_greed.value %}
 526 |           <div class="oracle-meta-row">
 527 |             <span class="oracle-meta-key">Fear &amp; Greed</span>
 528 |             <span class="oracle-meta-val" style="color:var(--oracle-gold);">
 529 |               {{ fear_greed.value }} — {{ fear_greed.label }}
 530 |             </span>
 531 |           </div>
 532 |           {% endif %}
 533 |         </div>
 534 | 
 535 |       </div>{# /sidebar #}
 536 |     </div>{# /hero-inner #}
 537 |   </div>{# /hero #}
 538 | 
 539 |   {# ── TODAY'S BRIEFING SCHEDULE ── #}
 540 |   <div class="oracle-section">
 541 |     <div class="oracle-section-title">Today's Briefings — {{ et_date }}</div>
 542 |     <div class="oracle-schedule-grid">
 543 | 
 544 |       {% for slot_type, slot_data in today_slots.items() %}
 545 |       {% set slot = slot_data.slot %}
 546 |       {% set briefing = slot_data.briefing %}
 547 |       {% set status = briefing.status if briefing else 'pending' %}
 548 | 
 549 |       <div class="oracle-slot-card {{ status if status in ['completed','generating'] else '' }}">
 550 | 
 551 |         {% if briefing and briefing.thumbnail_url and status == 'completed' %}
 552 |           <img class="slot-thumb" src="{{ briefing.thumbnail_url }}"
 553 |                alt="{{ slot.label }}"
 554 |                onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
 555 |           <div class="slot-thumb-placeholder" style="display:none;">NO THUMBNAIL</div>
 556 |         {% else %}
 557 |           <div class="slot-thumb-placeholder">{{ 'GENERATING...' if status == 'generating' else 'SCHEDULED' }}</div>
 558 |         {% endif %}
 559 | 
 560 |         <div class="slot-time">{{ slot.time_et }} · {{ slot.time_utc }}</div>
 561 |         <div class="slot-title">{{ slot.label }}</div>
 562 |         <div class="slot-desc">{{ slot.description }}</div>
 563 | 
 564 |         <div class="slot-status">
 565 |           {% if status == 'completed' %}
 566 |             <span class="slot-badge ready">✓ READY</span>
 567 |             {% if briefing.duration_seconds %}
 568 |             <span class="slot-duration">{{ "%.0f"|format(briefing.duration_seconds) }}s</span>
 569 |             {% endif %}
 570 |           {% elif status == 'generating' %}
 571 |             <span class="slot-badge gen">⟳ GENERATING</span>
 572 |           {% else %}
 573 |             <span class="slot-badge pending">SCHEDULED</span>
 574 |           {% endif %}
 575 |         </div>
 576 | 
 577 |         {% if status == 'completed' and briefing.video_url %}
 578 |         <a class="slot-watch-btn" href="#"
 579 |            onclick="playVideo('{{ briefing.video_url }}','{{ briefing.title }}','{{ briefing.thumbnail_url or '' }}'); return false;">
 580 |           ▶ WATCH
 581 |         </a>
 582 |         {% endif %}
 583 | 
 584 |       </div>
 585 |       {% endfor %}
 586 | 
 587 |     </div>
 588 |   </div>
 589 | 
 590 |   {# ── 7-DAY ARCHIVE ── #}
 591 |   <div class="oracle-section" style="margin-top:40px;">
 592 |     <div class="oracle-section-title">Briefing Archive — Last 7 Days</div>
 593 | 
 594 |     {% set archive = recent_briefings | selectattr("status", "equalto", "completed") | list %}
 595 |     {% if archive %}
 596 |     <div class="oracle-archive-grid">
 597 |       {% for b in archive %}
 598 |       <div class="oracle-archive-card"
 599 |            onclick="playVideo('{{ b.video_url }}','{{ b.title }}','{{ b.thumbnail_url or '' }}')"
 600 |            title="{{ b.title }}">
 601 | 
 602 |         {% if b.thumbnail_url %}
 603 |         <img class="archive-thumb" src="{{ b.thumbnail_url }}"
 604 |              alt="{{ b.title }}"
 605 |              onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
 606 |         <div class="archive-thumb-placeholder" style="display:none;">{{ b.briefing_type | upper }}</div>
 607 |         {% else %}
 608 |         <div class="archive-thumb-placeholder">{{ b.briefing_type | upper }}</div>
 609 |         {% endif %}
 610 | 
 611 |         <div class="archive-date">
 612 |           {% if b.scheduled_date %}{{ b.scheduled_date }}{% elif b.generated_at %}{{ b.generated_at[:10] }}{% endif %}
 613 |           &nbsp;·&nbsp;{{ b.briefing_type | replace('_', ' ') | upper }}
 614 |         </div>
 615 |         <div class="archive-title">{{ b.title or 'Oracle Briefing' }}</div>
 616 |         <div class="archive-meta">
 617 |           <span class="archive-type-badge">{{ b.briefing_type | replace('_', ' ') }}</span>
 618 |           {% if b.duration_seconds %}
 619 |           <span>{{ "%.0f"|format(b.duration_seconds) }}s</span>
 620 |           {% endif %}
 621 |           {% if b.btc_price_at_generation %}
 622 |           <span>BTC ${{ "{:,.0f}".format(b.btc_price_at_generation) }}</span>
 623 |           {% endif %}
 624 |         </div>
 625 | 
 626 |       </div>
 627 |       {% endfor %}
 628 |     </div>
 629 | 
 630 |     {% else %}
 631 |     <div class="oracle-empty">
 632 |       <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display:block;margin:0 auto 12px;opacity:.25">
 633 |         <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
 634 |       </svg>
 635 |       No archived briefings yet — check back after the first briefing is generated.
 636 |     </div>
 637 |     {% endif %}
 638 |   </div>
 639 | 
 640 | </div>{# /oracle-wrap #}
 641 | 
 642 | {# ── VIDEO MODAL ── #}
 643 | <div class="oracle-modal" id="oracleModal" onclick="if(event.target===this)closeModal()">
 644 |   <div class="oracle-modal-inner">
 645 |     <video id="modalVideo" class="oracle-modal-video" controls autoplay playsinline>
 646 |       <source id="modalVideoSrc" src="" type="video/mp4">
 647 |     </video>
 648 |     <div class="oracle-modal-info">
 649 |       <span class="oracle-modal-title" id="modalTitle"></span>
 650 |       <button class="oracle-modal-close" onclick="closeModal()">CLOSE ✕</button>
 651 |     </div>
 652 |   </div>
 653 | </div>
 654 | 
 655 | <script>
 656 | /* ── countdown timer ── */
 657 | (function() {
 658 |   const secondsUntil = {{ next_slot.seconds_until | int }};
 659 |   const totalSlot = 8 * 3600; // assume ~8h slot window for progress
 660 |   let remaining = secondsUntil;
 661 |   const display = document.getElementById('countdownDisplay');
 662 |   const bar = document.getElementById('countdownBar');
 663 | 
 664 |   function fmt(s) {
 665 |     if (s <= 0) return '00:00';
 666 |     const h = Math.floor(s / 3600);
 667 |     const m = Math.floor((s % 3600) / 60);
 668 |     const sec = s % 60;
 669 |     if (h > 0) return h + 'h ' + String(m).padStart(2,'0') + 'm';
 670 |     return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
 671 |   }
 672 | 
 673 |   function updateBar() {
 674 |     const pct = Math.max(0, Math.min(100, (1 - remaining / totalSlot) * 100));
 675 |     if (bar) bar.style.width = pct + '%';
 676 |   }
 677 | 
 678 |   function tick() {
 679 |     if (remaining > 0) {
 680 |       remaining--;
 681 |       if (display) display.textContent = fmt(remaining);
 682 |       updateBar();
 683 |     }
 684 |   }
 685 | 
 686 |   updateBar();
 687 |   setInterval(tick, 1000);
 688 | })();
 689 | 
 690 | /* ── video controls ── */
 691 | function toggleMute() {
 692 |   const v = document.getElementById('heroVideo');
 693 |   if (!v) return;
 694 |   v.muted = !v.muted;
 695 |   const btn = document.getElementById('unmuteBtn');
 696 |   if (btn) btn.textContent = v.muted ? 'UNMUTE' : 'MUTE';
 697 | }
 698 | 
 699 | function toggleTranscript(btn) {
 700 |   const body = document.getElementById('heroTranscript');
 701 |   if (!body) return;
 702 |   body.classList.toggle('open');
 703 |   const arrow = btn.querySelector('span:last-child');
 704 |   if (arrow) arrow.textContent = body.classList.contains('open') ? '▲' : '▼';
 705 | }
 706 | 
 707 | /* ── modal player ── */
 708 | function playVideo(url, title, thumb) {
 709 |   if (!url) return;
 710 |   const modal = document.getElementById('oracleModal');
 711 |   const video = document.getElementById('modalVideo');
 712 |   const src = document.getElementById('modalVideoSrc');
 713 |   const titleEl = document.getElementById('modalTitle');
 714 |   if (!modal || !video || !src) return;
 715 |   src.src = url;
 716 |   video.load();
 717 |   video.play().catch(() => {});
 718 |   if (titleEl) titleEl.textContent = title || 'Oracle Briefing';
 719 |   modal.classList.add('open');
 720 |   document.body.style.overflow = 'hidden';
 721 | }
 722 | 
 723 | function closeModal() {
 724 |   const modal = document.getElementById('oracleModal');
 725 |   const video = document.getElementById('modalVideo');
 726 |   if (video) { video.pause(); video.src = ''; }
 727 |   if (modal) modal.classList.remove('open');
 728 |   document.body.style.overflow = '';
 729 | }
 730 | 
 731 | document.addEventListener('keydown', function(e) {
 732 |   if (e.key === 'Escape') closeModal();
 733 | });
 734 | 
 735 | /* ── share ── */
 736 | function shareBriefing() {
 737 |   const url = window.location.href;
 738 |   if (navigator.share) {
 739 |     navigator.share({ title: 'Oracle Briefing — Protocol Pulse', url });
 740 |   } else if (navigator.clipboard) {
 741 |     navigator.clipboard.writeText(url);
 742 |     const btn = document.querySelector('.oracle-share-btn');
 743 |     if (btn) { const old = btn.textContent; btn.textContent = 'COPIED!'; setTimeout(() => btn.textContent = old, 1500); }
 744 |   }
 745 | }
 746 | 
 747 | /* ── live status poll ── */
 748 | (function() {
 749 |   function pollStatus() {
 750 |     fetch('/api/oracle/status')
 751 |       .then(r => r.json())
 752 |       .then(data => {
 753 |         // Update system dots
 754 |         const statuses = data.system || {};
 755 |         Object.keys(statuses).forEach(key => {
 756 |           const rows = document.querySelectorAll('.sys-row');
 757 |           rows.forEach(row => {
 758 |             const name = row.querySelector('.sys-name');
 759 |             if (name && statuses[key] && name.textContent.trim().toLowerCase().includes(key.replace('_',' '))) {
 760 |               const dot = row.querySelector('.sys-dot');
 761 |               const txt = row.querySelector('.sys-status');
 762 |               if (dot) { dot.classList.remove('ok','err'); dot.classList.add(statuses[key].ok ? 'ok' : 'err'); }
 763 |               if (txt) { const span = txt.querySelector('span:last-child'); if (span) span.textContent = statuses[key].ok ? 'ONLINE' : 'OFFLINE'; }
 764 |             }
 765 |           });
 766 |         });
 767 |       })
 768 |       .catch(() => {});
 769 |   }
 770 |   setInterval(pollStatus, 60000);  // poll every 60s
 771 | })();
 772 | </script>
 773 | {% endblock %}
 774 | 
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
