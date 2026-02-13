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

# Security: Uses .env secret, but provides a fallback for local dev
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_protocol_pulse_2026")

# Public network endpoints (local by default, cloudflared-ready when set in .env)
app.config["PUBLIC_HUB_URL"] = os.environ.get("PUBLIC_HUB_URL", "http://127.0.0.1:5000").rstrip("/")
app.config["PUBLIC_AI_URL"] = os.environ.get("PUBLIC_AI_URL", "http://127.0.0.1:11434").rstrip("/")
app.config["PUBLIC_SSH_HOST"] = os.environ.get("PUBLIC_SSH_HOST", "").strip()
app.config["USE_DOUBLE_PIPE"] = os.environ.get("USE_DOUBLE_PIPE", "false").strip().lower() in {
    "1", "true", "yes", "on"
}

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
if database_url.startswith("sqlite:"):
    # Ensure UTF-8 support for Bitcoin symbols
    if "?" not in database_url:
        database_url += "?charset=utf8mb4"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Startup env diagnostics (warnings only; never hard-crash startup).
_required_env = ["SESSION_SECRET", "DATABASE_URL"]
_recommended_env = [
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
]
for _name in _required_env:
    if not os.environ.get(_name):
        logging.warning("%s missing; using fallback/default where available.", _name)
for _name in _recommended_env:
    if not os.environ.get(_name):
        logging.info("%s not configured (related integration stays degraded/off).", _name)

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
def add_static_cache_headers(response):
    """Allow browsers to cache static assets for 1 day."""
    from flask import request
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 86400
        response.cache_control.public = True
    return response


# 4. Define Template Filters
@app.template_filter('inject_ads')
def inject_ads(content):
    import models
    try:
        active_ads = models.Advertisement.query.filter_by(is_active=True).all()
        if not active_ads:
            return content
        ad = random.choice(active_ads)
        ad_html = f'''
        <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
            <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
            <a href="/ads/go/{ad.id}" rel="noopener" class="text-decoration-none">
                <img src="{ad.image_url}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{ad.name}">
                <p class="mb-0 text-white fw-bold">{ad.name}</p>
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

@app.template_filter('from_json')
def from_json_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

# 5. User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    import models
    return models.User.query.get(int(user_id))

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
    # Runtime create_all is disabled in production; use Flask-Migrate:
    #   flask db upgrade
    if os.environ.get("ENABLE_RUNTIME_DB_CREATE_ALL", "false").strip().lower() in {"1", "true", "yes", "on"}:
        db.create_all()
        logging.warning("ENABLE_RUNTIME_DB_CREATE_ALL=true used; migration workflow is recommended.")

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
from onboarding_routes import onboarding_bp
app.register_blueprint(onboarding_bp)

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
