import os
from blueprints.curated_mining import curated_mining_bp
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
    from flask_caching import Cache
    _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
except ImportError:
    _cache = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:////home/ultron/protocol_pulse/instance/protocol_pulse.db")
if database_url.startswith("sqlite:"):
    # SQLite doesn't support charset param — strip it if present (breaks file path)
    if "charset=utf8mb4" in database_url:
        database_url = database_url.replace("?charset=utf8mb4", "").replace("&charset=utf8mb4", "")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

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

@app.context_processor
def inject_csrf():
    """Inject CSRF token for forms. Generate once per session."""
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(32).hex()
    return {"csrf_token": session.get("csrf_token")}


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
            <a href="{ad.target_url}" target="_blank" rel="noopener" class="text-decoration-none">
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
    """Return the basename of a path for use in templates."""
    if not path:
        return ""
    return os.path.basename(str(path).strip())

@app.template_filter('article_header_display')
def article_header_display_filter(article):
    """Return a distinct header image URL for this article."""
    _OLD_DEFAULT = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"
    if article is None:
        return _OLD_DEFAULT
    stored = (getattr(article, "header_image_url", None) or "").strip()
    if stored and stored != _OLD_DEFAULT:
        return stored
    return "/static/images/default-header.png"

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
    # 2. Create the tables (migration-safe: adds new columns/tables without dropping existing)
    db.create_all()
    # 2b. SESSION 12 — Run sentiment intelligence migrations (adds article sentiment columns + tables)
    try:
        from utils.db_migrate_sentiment import run_migrations
        run_migrations(db)
        logging.info("SESSION 12: sentiment-intel migrations applied")
    except Exception as _e:
        logging.warning("SESSION 12: db_migrate_sentiment failed: %s", _e)
    # 3. ONLY NOW load the routes
    import routes
    # 4. Register Terminal API blueprint
    try:
        from routes_premium_api import premium_api
        app.register_blueprint(premium_api)
        logging.info("Terminal API blueprint registered")
        # 5. Provision demo API key for playground
        from services.api_key_service import provision_demo_key
        provision_demo_key(db, models)
    except Exception as e:
        logging.warning("Terminal API blueprint not loaded: %s", e)
    # 6. Initialize FTS5 search index (SESSION 17 — GLOBAL SEARCH)
    try:
        import importlib.util as _ilu
        import os as _os
        _svc_path = _os.path.join(_os.path.dirname(__file__), 'services', 'search_service.py')
        _spec = _ilu.spec_from_file_location('search_service', _svc_path)
        _search_svc = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_search_svc)
        _search_svc.init_fts_index(db)
        _search_svc.populate_fts_index(db)
        logging.info("FTS5 search index initialized")
    except Exception as _fts_init_err:
        logging.warning("FTS5 search index init failed (non-fatal): %s", _fts_init_err)

app.register_blueprint(curated_mining_bp)

# ── Intelligence Terminal Blueprint ──────────────────────────────────────
try:
    from blueprints.intelligence import intelligence_bp
    app.register_blueprint(intelligence_bp)
    logging.info("Intelligence Terminal blueprint registered")
except Exception as _intel_err:
    logging.warning("Intelligence Terminal blueprint not loaded: %s", _intel_err)

# ── Start Sentinel Daemon ────────────────────────────────────────────────
try:
    import importlib.util as _ilu_sentinel
    _sentinel_path = str(Path(__file__).resolve().parent.parent / "services" / "sentinel.py")
    _sentinel_spec = _ilu_sentinel.spec_from_file_location("_sentinel_daemon_boot", _sentinel_path)
    _sentinel_boot = _ilu_sentinel.module_from_spec(_sentinel_spec)
    _sentinel_spec.loader.exec_module(_sentinel_boot)
    _sentinel_boot.start_sentinel()
    logging.info("Sentinel daemon started")
except Exception as _sentinel_err:
    logging.warning("Sentinel daemon failed to start: %s", _sentinel_err)

# Diagnose: confirm / and /debug-routes are registered (debug 404)
try:
    rules = [r.rule for r in app.url_map.iter_rules()]
    has_root = "/" in rules
    logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
    if not has_root:
        logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
except Exception as e:
    logging.warning("Could not list routes: %s", e)



@app.route('/video/<filename>')
def serve_video(filename):
    import os, glob
    from flask import send_from_directory, abort
    pattern = '/home/ultron/protocol_pulse/video_pipeline_v3/output/**/' + filename
    matches = glob.glob(pattern, recursive=True)
    if matches:
        d = os.path.dirname(matches[0])
        return send_from_directory(d, filename, mimetype='video/mp4', as_attachment=False)
    abort(404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Protocol Pulse → http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
    # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)

