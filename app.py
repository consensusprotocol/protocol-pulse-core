import os
from pathlib import Path
from dotenv import load_dotenv
# Load .env from the same directory as this file (core/) so it works from any cwd
load_dotenv(Path(__file__).resolve().parent / ".env")

import logging
import json
import random
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
try:
    from flask_socketio import SocketIO
except ImportError:
    SocketIO = None
try:
    from flask_caching import Cache
    _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
except ImportError:
    _cache = None

# Configure logging (default info; keep noisy transport libs quiet).
logging.basicConfig(level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.INFO)

class Base(DeclarativeBase):
    pass

# 1. Initialize DB WITHOUT app first to prevent circular loops
db = SQLAlchemy(model_class=Base)

# 2. Create the app instance — use absolute paths so templates/static are always found
#    whether run as "app:app" from core/ or "core.app:app" from project root
_core_dir = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(_core_dir / "templates"), static_folder=str(_core_dir / "static"))

# Security: SECRET must be set in environment — no silent insecure fallback
_session_secret = os.environ.get("SESSION_SECRET", "")
if not _session_secret:
    logging.critical("SESSION_SECRET not set — using ephemeral key. Set SESSION_SECRET in environment for production.")
    import secrets as _secrets_mod
    _session_secret = _secrets_mod.token_hex(32)
app.secret_key = _session_secret

# Public network endpoints (local by default, cloudflared-ready when set in .env)
app.config["PUBLIC_HUB_URL"] = os.environ.get("PUBLIC_HUB_URL", "http://127.0.0.1:5000").rstrip("/")
app.config["PUBLIC_AI_URL"] = os.environ.get("PUBLIC_AI_URL", "http://127.0.0.1:11434").rstrip("/")
app.config["PUBLIC_SSH_HOST"] = os.environ.get("PUBLIC_SSH_HOST", "").strip()
app.config["USE_DOUBLE_PIPE"] = os.environ.get("USE_DOUBLE_PIPE", "false").strip().lower() in {
    "1", "true", "yes", "on"
}

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
# Replit (and some Heroku-style hosts) emit postgres:// — SQLAlchemy 1.4+ requires postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
if database_url.startswith("sqlite:"):
    # SQLite: remove unsupported charset param added by older code
    if "charset=utf8mb4" in database_url:
        database_url = database_url.replace("?charset=utf8mb4", "").replace("&charset=utf8mb4", "")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Startup env diagnostics.
# Required vars: missing → log CRITICAL (feature is broken without these).
# Recommended vars: missing → log INFO (integration degrades gracefully).
_required_env = ["SESSION_SECRET", "DATABASE_URL", "RESEND_API_KEY"]
_recommended_env = [
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
]
for _name in _required_env:
    if not os.environ.get(_name):
        logging.critical(
            "REQUIRED env var %s is missing — dependent features will fail.", _name
        )
for _name in _recommended_env:
    if not os.environ.get(_name):
        logging.info("%s not configured (related integration stays degraded/off).", _name)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 1 day default for send_file

# 3. Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
limiter.init_app(app)

if _cache is not None:
    _cache.init_app(app)
    cache = _cache
else:
    class _NullCache:
        def init_app(self, app): pass
        def cached(self, timeout=None, key_prefix=None):
            def decorator(f): return f
            return decorator
    cache = _NullCache()

if SocketIO is not None:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
else:
    socketio = None

@app.context_processor
def inject_csrf():
    """Inject CSRF token for forms. Generate once per session."""
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(32).hex()
    return {
        "csrf_token": session.get("csrf_token"),
        "public_hub_url": app.config.get("PUBLIC_HUB_URL"),
        "public_ai_url": app.config.get("PUBLIC_AI_URL"),
        "public_ssh_host": app.config.get("PUBLIC_SSH_HOST"),
        "use_double_pipe": app.config.get("USE_DOUBLE_PIPE", False),
    }


@app.after_request
def add_headers(response):
    """Add cache, security, and performance headers to every response."""
    from flask import request

    # ── Security headers ──
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # ── Cache strategy ──
    if request.path.startswith("/static/"):
        # Versioned assets (?v=X) get long cache; images get 1 week; CSS/JS get 1 day
        if any(request.path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')):
            response.cache_control.max_age = 604800  # 1 week
            response.cache_control.public = True
        elif any(request.path.endswith(ext) for ext in ('.css', '.js')):
            response.cache_control.max_age = 86400  # 1 day
            response.cache_control.public = True
        else:
            response.cache_control.max_age = 86400
            response.cache_control.public = True
    elif request.path.startswith("/api/"):
        # P1-3: API endpoints default to private/no-store — prevents user-specific
        # data leaking through shared caches. Individual routes may opt into caching.
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "private, no-store"
    else:
        # HTML pages: no-cache but allow revalidation
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "public, no-cache, must-revalidate"

    return response


# 4. Define Template Filters
@app.template_filter('inject_ads')
def inject_ads(content):
    import models
    from flask import g
    try:
        if not hasattr(g, '_active_ads'):
            g._active_ads = models.Advertisement.query.filter_by(is_active=True).all()
        active_ads = g._active_ads
        if not active_ads:
            return content
        ad = random.choice(active_ads)
        from markupsafe import escape as _esc
        ad_html = f'''
        <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
            <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
            <a href="/ads/go/{ad.id}" rel="noopener" class="text-decoration-none">
                <img src="{_esc(ad.image_url or '')}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{_esc(ad.name or '')}">
                <p class="mb-0 text-white fw-bold">{_esc(ad.name or '')}</p>
            </a>
        </div>
        '''
        parts = content.split('</p>', 2)
        if len(parts) > 2:
            return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
        return content + ad_html
    except Exception as e:
        logging.warning(f"Ad injection failed: {e}")
        return content

@app.template_filter('basename')
def basename_filter(path):
    """Return the basename of a path for use in templates (e.g. clip filename)."""
    if not path:
        return ""
    return os.path.basename(str(path).strip())

@app.template_filter('from_json')
def from_json_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

# Distinct header image per article: when stored URL is missing or the old single default, use pool by title
_OLD_SINGLE_DEFAULT_HEADER = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"

@app.template_filter('article_header_display')
def article_header_display_filter(article):
    """Return a distinct header image URL for this article (avoids same image on every card)."""
    if article is None:
        return _OLD_SINGLE_DEFAULT_HEADER
    stored = (getattr(article, "header_image_url", None) or "").strip()
    if stored and stored != _OLD_SINGLE_DEFAULT_HEADER:
        return stored
    return "/static/images/default-header.png"

# 5. User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    import models
    try:
        return models.User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

# =====================================
# THE IGNITION ZONE (CRITICAL ORDER)
# =====================================
# When we run as python app.py, __name__ is "__main__". Later, "import routes" does
# "from app import app", which loads this file again as module "app" (a second Flask
# app). Routes then register on that second app, but we call app.run() on this one → 404.
# So make "app" resolve to this same module when we are the main script.
if __name__ == "__main__":
    import sys
    sys.modules["app"] = sys.modules["__main__"]

with app.app_context():
    # 1. Load the models into memory first
    import models
    # Create any missing tables at startup (idempotent — safe to always run).
    # Set ENABLE_RUNTIME_DB_CREATE_ALL=false to suppress on managed migration envs.
    if os.environ.get("ENABLE_RUNTIME_DB_CREATE_ALL", "true").strip().lower() not in {"0", "false", "no", "off"}:
        try:
            db.create_all()
        except Exception as _dbe:
            logging.warning("db.create_all() failed (non-fatal): %s", _dbe)

    # p3-sentiment-intel: migration-safe column/table additions
    try:
        from utils.db_migrate_sentiment import run_migrations
        run_migrations(db)
    except Exception as _mige:
        logging.warning("db_migrate_sentiment failed (non-fatal): %s", _mige)

def _run_dev_server():
    port = 5000
    host = "0.0.0.0"
    print(f"Starting Protocol Pulse -> http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
    # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
    if socketio is not None:
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=False, use_reloader=False)

# Keep routes import near the very bottom so the app object and extensions are fully initialized first.
import routes
from routes_api_v2 import api_v2
try:
    from routes_api_terminal import terminal_bp
    app.register_blueprint(terminal_bp)
except Exception as e:
    logging.critical("Terminal API blueprint failed to load: %s", e)
try:
    from routes_commander import commander_bp
    app.register_blueprint(commander_bp)
    logging.info("Commander API blueprint registered at /api/v1")
except Exception as _e:
    logging.warning("Commander blueprint not loaded: %s", _e)
try:
    from routes_newsletter_trigger import newsletter_trigger_bp
    app.register_blueprint(newsletter_trigger_bp)
except Exception as e:
    logging.critical("Newsletter trigger blueprint failed to load: %s", e)

# B1 Newsletter Engine — hard fail if feature is active
from routes_newsletter_b1 import newsletter_b1_bp
app.register_blueprint(newsletter_b1_bp)
logging.info("B1 Newsletter blueprint registered")
app.register_blueprint(api_v2)
from onboarding_routes import onboarding_bp
app.register_blueprint(onboarding_bp)

from oracle_routes import oracle_bp
app.register_blueprint(oracle_bp)

# SESSION 2: Blueprint Architecture — Newsletter main routes
try:
    from core.blueprints.newsletter import newsletter_bp
    app.register_blueprint(newsletter_bp)
    logging.info("Newsletter main blueprint registered (/newsletter)")
except Exception as _e:
    logging.warning("Newsletter main blueprint not loaded: %s", _e)

# SESSION 10 — Article Rebuild: new /api/v2/articles endpoint
try:
    from routes_articles import articles_api_bp
    app.register_blueprint(articles_api_bp)
    logging.info("Articles API blueprint registered (/api/v2/articles)")
except Exception as _e:
    logging.warning("Articles API blueprint not loaded: %s", _e)

# SESSION 8 — Nostr Feed
try:
    from routes_nostr import nostr_bp
    app.register_blueprint(nostr_bp)
    logging.info("Nostr Feed blueprint registered (/nostr)")
except Exception as _e:
    logging.warning("Nostr Feed blueprint not loaded: %s", _e)

# SESSION 5 — Mining Intel Blueprint
try:
    from core.blueprints.mining import mining_bp
    app.register_blueprint(mining_bp)
    logging.info("Mining Intel blueprint registered at /mining-intel")
except Exception as _e:
    logging.warning("Mining Intel blueprint not loaded: %s", _e)

# SESSION 6 — Schiff Bot Blueprint
try:
    from core.blueprints.schiff import schiff_bp
    app.register_blueprint(schiff_bp)
    logging.info("Schiff Bot blueprint registered (/schiff, /api/schiff/*)")
except Exception as _e:
    logging.warning("Schiff Bot blueprint not loaded: %s", _e)

# SESSION 7 — Oracle Avatar Blueprint
try:
    from core.blueprints.oracle_avatar import oracle_avatar_bp
    app.register_blueprint(oracle_avatar_bp)
    logging.info("Oracle Avatar blueprint registered (/oracle-live, /api/oracle/*)")
except Exception as _e:
    logging.warning("Oracle Avatar blueprint not loaded: %s", _e)

try:
    from services.video_engine.dashboard.app import dashboard_bp
    app.register_blueprint(dashboard_bp)
    logging.info("Dashboard blueprint registered at /dashboard/")
except ImportError as _e:
    logging.warning("Dashboard blueprint not loaded: %s", _e)

# Start background APScheduler only when explicitly enabled for this process.
if os.environ.get("ENABLE_APSCHEDULER", "false").strip().lower() in {"1", "true", "yes", "on"}:
    try:
        from services.scheduler import initialize_scheduler
        _sch = initialize_scheduler()
        logging.info("Scheduler initialized: %s", _sch)
    except Exception as _e:
        logging.warning("Scheduler init skipped: %s", _e)

# Diagnose after routes import so startup logs reflect the real routing table.
try:
    rules = [r.rule for r in app.url_map.iter_rules()]
    has_root = "/" in rules
    logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
    if not has_root:
        logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
except Exception as e:
    logging.warning("Could not list routes: %s", e)

if __name__ == "__main__":
    _run_dev_server()
