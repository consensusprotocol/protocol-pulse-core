import os
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))
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
    from flask_compress import Compress as _FlaskCompress
except Exception as _compress_err:
    _FlaskCompress = None
    logging.warning("flask-compress not available (%s) — responses will not be gzipped.", _compress_err)
try:
    from flask_caching import Cache
    _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
except ImportError:
    _cache = None
    logging.warning("flask_caching not available — running with null cache. Install flask-caching for production.")

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
app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent / "templates"), static_folder=str(Path(__file__).resolve().parent / "static"))
# Search both templates/ AND core/templates/ so intelligence terminal works
from jinja2 import ChoiceLoader, FileSystemLoader
_root_templates = str(Path(__file__).resolve().parent / "templates")
_core_templates = str(Path(__file__).resolve().parent / "core" / "templates")
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(_root_templates),
    FileSystemLoader(_core_templates),
])


# Security: SECRET must be set in environment — no silent insecure fallback
_session_secret = os.environ.get("SESSION_SECRET", "")
if not _session_secret:
    logging.critical("SESSION_SECRET not set — using ephemeral key. Set SESSION_SECRET in environment for production.")
    if not os.environ.get("FLASK_DEBUG", ""):
        raise RuntimeError("SESSION_SECRET must be set in production. Run: python3 scripts/generate_secret.py")
    import secrets as _secrets_mod
    _session_secret = _secrets_mod.token_hex(32)
app.secret_key = _session_secret

# Public network endpoints (local by default, cloudflared-ready when set in .env)
app.config["PUBLIC_HUB_URL"] = os.environ.get("PUBLIC_HUB_URL", "http://127.0.0.1:5000").rstrip("/")
app.config["PUBLIC_AI_URL"] = os.environ.get("PUBLIC_AI_URL", "http://127.0.0.1:11434").rstrip("/")
app.config["PUBLIC_SSH_HOST"] = os.environ.get("PUBLIC_SSH_HOST", "").strip()
app.config["TURNSTILE_SITE_KEY"] = os.environ.get("TURNSTILE_SITE_KEY", "")
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
    # SQLite: resolve relative paths against the app directory so gunicorn CWD doesn't matter
    _prefix = "sqlite:///"
    if database_url.startswith(_prefix) and not database_url[len(_prefix):].startswith("/"):
        _rel_path = database_url[len(_prefix):]
        database_url = _prefix + os.path.join(os.path.dirname(os.path.abspath(__file__)), _rel_path)

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

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year for versioned static assets

# 3. Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
limiter.init_app(app)

if _FlaskCompress is not None:
    app.config['COMPRESS_REGISTER'] = True
    app.config['COMPRESS_MIN_SIZE'] = 500
    _FlaskCompress(app)

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
    response.headers["Permissions-Policy"] = "geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # ── Cache strategy ──
    if request.path.startswith("/static/"):
        # Versioned assets (?v=X) get long cache; images get 1 week; CSS/JS get 1 day
        if any(request.path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')):
            response.cache_control.max_age = 31536000  # 1 year
            response.cache_control.public = True
        elif any(request.path.endswith(ext) for ext in ('.css', '.js')):
            response.cache_control.max_age = 604800  # 1 week
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

@app.template_filter('to_est')
def to_est_filter(dt):
    """Convert a naive UTC datetime to Eastern Time for display."""
    if dt is None:
        return ""
    import pytz
    eastern = pytz.timezone("America/New_York")
    if dt.tzinfo is None:
        utc_dt = pytz.utc.localize(dt)
    else:
        utc_dt = dt
    return utc_dt.astimezone(eastern)

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
    from routes_api_terminal import terminal_bp, provision_demo_key
    app.register_blueprint(terminal_bp)
    with app.app_context():
        provision_demo_key()
except Exception as e:
    logging.critical("Terminal API blueprint failed to load: %s", e)
try:
    from routes_commander import commander_bp, commander_pages_bp
    app.register_blueprint(commander_bp)
    app.register_blueprint(commander_pages_bp)
    logging.info("Commander API blueprint registered at /api/v1")
except Exception as _e:
    logging.critical("Commander blueprint not loaded: %s", _e)
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
assert 'oracle' in app.blueprints, 'FATAL: Oracle blueprint failed to register'

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


# CURATED MINING — White-glove service landing page
try:
    from core.blueprints.curated_mining import curated_mining_bp
    app.register_blueprint(curated_mining_bp)
    logging.info("Curated Mining blueprint registered at /curated-mining")
except Exception as _e:
    logging.warning("Curated Mining blueprint not loaded: %s", _e)
# SESSION 7 — Oracle Avatar Blueprint
try:
    from core.blueprints.oracle_avatar import oracle_avatar_bp
    app.register_blueprint(oracle_avatar_bp)
    logging.info("Oracle Avatar blueprint registered (/oracle-live, /api/oracle/*)")
except Exception as _e:
    logging.critical("Oracle Avatar blueprint not loaded: %s", _e)

try:
    from services.video_engine.dashboard.app import dashboard_bp
    app.register_blueprint(dashboard_bp)
    logging.info("Dashboard blueprint registered at /dashboard/")
except ImportError as _e:
    logging.warning("Dashboard blueprint not loaded: %s", _e)

# SPONSOR AGENT V2 — Outreach pipeline
try:
    from core.blueprints.sponsor import sponsor_bp
    app.register_blueprint(sponsor_bp)
    logging.info("Sponsor Agent blueprint registered at /sponsor-agent")
except Exception as _e:
    logging.warning("Sponsor Agent blueprint not loaded: %s", _e)

# F4/F7 — Briefings Blueprint (public /briefings page)
try:
    from core.blueprints.briefings import briefings_bp
    app.register_blueprint(briefings_bp)
    logging.info("Briefings blueprint registered at /briefings")
except Exception as _e:
    logging.warning("Briefings blueprint not loaded: %s", _e)

# Montage Blueprint (daily highlights montage)
try:
    from core.blueprints.montage_routes import montage_bp
    app.register_blueprint(montage_bp)
    logging.info("Montage blueprint registered at /montage")
except Exception as _e:
    logging.warning("Montage blueprint not loaded: %s", _e)

# Intelligence Terminal Blueprint
try:
    from blueprints.intelligence import intelligence_bp
    app.register_blueprint(intelligence_bp)
    logging.info("Intelligence Terminal blueprint registered")
except Exception as _e:
    logging.warning("Intelligence Terminal blueprint not loaded: %s", _e)

# PANOPTICON — Congressional Disclosure & Whale Intelligence Dashboard
try:
    from core.blueprints.panopticon import panopticon_bp
    app.register_blueprint(panopticon_bp)
    logging.info("Panopticon blueprint registered at /panopticon")
except Exception as _e:
    logging.warning("Panopticon blueprint not loaded: %s", _e)

# Sovereign Context Engine — unified intelligence API
@app.route('/api/sovereign-context')
def api_sovereign_context():
    """Serve the latest sovereign context world-state snapshot."""
    from flask import jsonify
    try:
        from services.sovereign_context_engine import get_latest_context, get_recent_alerts
        ctx = get_latest_context()
        if not ctx:
            return jsonify({"error": "No context available — run a cycle first"}), 503
        return jsonify(ctx)
    except Exception as _e:
        logging.warning("Sovereign context API error: %s", _e)
        return jsonify({"error": str(_e)}), 500


@app.route('/api/sovereign-alerts')
def api_sovereign_alerts():
    """Serve recent sovereign pattern-match alerts."""
    from flask import jsonify, request
    try:
        from services.sovereign_context_engine import get_recent_alerts
        limit = min(int(request.args.get('limit', 20)), 100)
        alerts = get_recent_alerts(limit)
        return jsonify({"alerts": alerts, "count": len(alerts)})
    except Exception as _e:
        logging.warning("Sovereign alerts API error: %s", _e)
        return jsonify({"error": str(_e)}), 500


# Start background APScheduler only when explicitly enabled for this process.
if os.environ.get("ENABLE_APSCHEDULER", "false").strip().lower() in {"1", "true", "yes", "on"}:
    try:
        from services.scheduler import initialize_scheduler
        _sch = initialize_scheduler()
        logging.info("Scheduler initialized: %s", _sch)
    except Exception as _e:
        logging.warning("Scheduler init skipped: %s", _e)

# Media Feed Service — 15-minute background RSS polling
try:
    from services.media_feed_service import start_feed_polling
    start_feed_polling(app)
    logging.info("Media feed polling started (every 15 min)")
except Exception as _e:
    logging.warning("Media feed polling not started: %s", _e)

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
_STATIC_ROOT = os.path.realpath('/home/ultron/protocol_pulse/static')

@app.route('/a/<path:fn>')
def _serve_asset(fn):
    from flask import make_response, abort
    import mimetypes, os as _o
    p = _o.path.join('/home/ultron/protocol_pulse/static', fn)
    safe_p = _o.path.realpath(p)
    if not safe_p.startswith(_STATIC_ROOT + _o.sep):
        abort(403)
    if not _o.path.exists(safe_p): abort(404)
    data = open(safe_p,'rb').read()
    resp = make_response(data)
    resp.headers['Content-Type'] = mimetypes.guess_type(safe_p)[0] or 'text/plain'
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp

@app.route('/v3/<path:fn>')
def _serve_v3(fn):
    from flask import make_response, abort
    import mimetypes, os as _o
    p = _o.path.join('/home/ultron/protocol_pulse/static', fn)
    safe_p = _o.path.realpath(p)
    if not safe_p.startswith(_STATIC_ROOT + _o.sep):
        abort(403)
    if not _o.path.exists(safe_p): abort(404)
    data = open(safe_p,'rb').read()
    resp = make_response(data)
    resp.headers['Content-Type'] = mimetypes.guess_type(safe_p)[0] or 'text/plain'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp
