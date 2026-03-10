# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: session2-newsletter
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REVIEW: session2-newsletter

I am conducting a forensic review of the provided codebase for the `feature/session2-newsletter` branch of Protocol Pulse. My analysis will be thorough, citing specific line numbers where issues are identified, and will cover correctness, compliance with governing laws, security, frontend and backend quality, world-class gap analysis, and actionable recommendations.

---

### SECTION 1: CORRECTNESS
**Main User Flow Analysis (Newsletter Subscription and Delivery):**
- **Subscription Flow:** The code for subscribing users to the newsletter is not explicitly shown in the provided files. Without a subscription endpoint or form handling in `app.py` or other files, I cannot confirm if users can subscribe as intended. If this is handled elsewhere, it needs to be verified for correct token generation and storage.
- **Newsletter Generation and Sending:** The scheduler in `services/scheduler.py` includes tasks like `sarah_intelligence_briefing` (lines 333-341) for generating daily briefs, but there is no explicit task or function for sending newsletters to subscribers. The `daily_distribution_brief_9am_est` task (lines 361-369) dispatches a brief, but it’s unclear if this includes newsletter emails to subscribers as per LAW 2 (one per day).
- **Unsubscribe Flow:** There is no visible route or function in the provided code for handling `/unsubscribe?token={unsubscribe_token}` as mandated by LAW 4. Without this, users cannot unsubscribe, which is a critical correctness issue.
- **Logic Errors:** In `services/scheduler.py`, the `auto_viral_reel` function (line 101-202) and `intel_medley` (line 431-432) redundantly call the same function, which could lead to confusion or unintended duplicate processing.
- **Race Conditions:** The scheduler in `services/scheduler.py` uses `max_instances=1` for some tasks (e.g., line 550), which helps prevent concurrent runs, but tasks like `sentry_megaphone` (line 541) lack this safeguard, risking race conditions if multiple instances attempt to write to `pulseevents.jsonl` simultaneously.
- **N+1 Query Problems:** In `core/blueprints/articles.py`, the `article_get_related` function (lines 162-183) performs multiple queries without batching, potentially leading to N+1 issues when fetching related articles for multiple articles in a loop (e.g., in `build_article_data` at line 216-231).
- **Edge Cases:** 
  - Empty DB: The `api_articles` endpoint (line 298-370 in `articles.py`) handles an empty published articles list by falling back to all articles (lines 315-317), but does not handle a completely empty DB, which could return misleading results.
  - API Timeout: External API calls in `auto_viral_reel` (e.g., Telegram post at line 173-180) have a timeout of 10 seconds, but there’s no retry mechanism, risking silent failures on transient issues.
  - Bad Input: The `article_find_by_slug` function (line 93-101 in `articles.py`) assumes the slug has an ID prefix, but does not validate or sanitize input, risking crashes on malformed slugs.

---

### SECTION 2: LAW COMPLIANCE
- **LAW 1: Resend API only (RESEND_API_KEY in .env)**
  - **PARTIAL**: The code checks for `RESEND_API_KEY` in `app.py` (line 80) as a required environment variable, logging a critical error if missing (lines 88-91). However, there is no explicit usage of the Resend API for sending newsletters in the provided files. If implemented elsewhere, compliance needs verification; otherwise, this is a violation.
- **LAW 2: One newsletter per day. Never two in the same day.**
  - **PARTIAL**: The `daily_distribution_brief_9am_est` task in `services/scheduler.py` (lines 361-369) is scheduled at 09:00 EST via cron (line 58), suggesting a single daily dispatch. However, without explicit code for newsletter sending or a check to prevent multiple dispatches within a day, compliance is not guaranteed. Additional tasks like `sarah_intelligence_briefing` (line 333-341) could potentially trigger overlapping content distribution.
- **LAW 3: Newsletter format**
  - **VIOLATION**: There is no code in the provided files that defines or enforces the newsletter format as specified (Subject, From, Content structure with top story, 4 articles, network stat, oracle signal, CTA, and footer). Without this, the format cannot be compliant. If implemented in `distribution_manager.dispatch_daily_brief()` (referenced at line 364), it must be reviewed.
- **LAW 4: Unsubscribe must work (CAN-SPAM compliance)**
  - **VIOLATION**: There is no route or function in the provided code for handling `/unsubscribe?token={unsubscribe_token}`. No evidence of UUID token generation or storage in a `newsletter_subscribers` table is present (e.g., in `app.py` or other files). This is a critical non-compliance with CAN-SPAM requirements.

---

### SECTION 3: SECURITY
- **SQL Injection:** 
  - In `articles.py`, the `api_articles` endpoint (lines 319-328) uses `ilike` with user input (`category` and `search`) without explicit sanitizati

## GEMINI — CYCLE 1 OUTPUT
This is an audit of **Protocol Pulse — CODE AUDIT PACKAGE** for feature **session2-newsletter**.

## SECTION 1: CORRECTNESS

The provided code focuses on application setup, article data handling, and task scheduling. The core logic for newsletter assembly and sending is absent, presumably in `routes_newsletter_b1.py` and other un-audited files. My review is based on the provided infrastructure.

-   **N+1 Query Problem:** The `build_article_data` function in `core/blueprints/articles.py` (line 216) iterates through a list of articles and calls helper functions for each. One of these, `article_get_related` (line 162), executes one or two database queries per article to find related content. If the main article list page calls `build_article_data` for 20 articles, this could result in 1 (initial query) + 20*2 (related queries) = 41 database queries, which will not scale to the specified 1000 concurrent users. A more efficient approach would involve pre-loading related articles.

-   **N+1 Query Problem (Template Filter):** `app.py`, line 176, the `inject_ads` template filter queries the database for active ads. While it caches the result in `flask.g` for the duration of a single request, if this filter is applied inside a loop in a template (e.g., to multiple article bodies on a list page), it will still execute the query once per request. On a high-traffic page, this adds unnecessary DB load. The query should be performed once in the view function.

-   **Redundant Database Query:** In `core/blueprints/articles.py` at line 314, `total = q.count()` executes a `SELECT COUNT(*)` query. The code then adds more filters (category, search) before calling `q.paginate()`. The `paginate()` method *also* executes its own `COUNT(*)` query on the filtered dataset. This makes the first `q.count()` call entirely redundant and inefficient.

-   **Logic Error / Duplication:** In `services/scheduler.py`, the task `intel_medley` (line 431) incorrectly calls `auto_viral_reel()`. This appears to be a copy-paste error; it should likely have its own implementation logic.

-   **Silent Failure / Edge Case:** In `app.py`, line 88, if a required environment variable like `RESEND_API_KEY` is missing, the application logs a `CRITICAL` error but continues to run. This means the server can start and appear healthy, but the newsletter feature will be completely broken. For truly critical dependencies, the application should fail to start.

## SECTION 2: LAW COMPLIANCE

The most critical files for assessing law compliance (the ones that build and send the email) are not included in this audit package. Assessment is based on inference from the provided infrastructure.

-   **LAW 1: Resend API only:** **PARTIAL**. `app.py:80` lists `RESEND_API_KEY` as a required environment variable, and the application startup checks for its presence. This strongly suggests the intent to use Resend. However, `services/scheduler.py:72` contains a helper function `_send_alert_email` that explicitly uses `sendgrid`. This creates ambiguity and a potential violation if this function were ever re-used for newsletters. Without the sending code, I cannot confirm full compliance.

-   **LAW 2: One newsletter per day:** **COMPLIANT**. `services/scheduler.py` defines two plausible newsletter tasks: `sarah_intelligence_briefing` at 06:00 UTC (line 51) and `daily_distribution_brief_9am_est` at 09:00 EST (line 54). Both are scheduled with a daily cron trigger. Assuming these tasks do not overlap in function and the trigger endpoint is secured, this law appears to be met by the scheduling logic.

-   **LAW 3: Newsletter format:** **VIOLATION**. The code that assembles the newsletter subject and content is not provided. It is impossible to verify compliance with the specified format.

-   **LAW 4: Unsubscribe must work:** **VIOLATION**. The code for generating unsubscribe tokens, storing them in the `newsletter_subscribers` table, and handling the `/unsubscribe` route is not provided. It is impossible to verify compliance.

## SECTION 3: SECURITY

-   **SQL Injection:** **PASSED**. The application consistently uses the SQLAlchemy ORM for database queries. User-supplied input in `core/blueprints/articles.py:297` (`api_articles`) is passed to ORM methods like `.filter()` and `.ilike()`, which correctly parameterize queries, preventing SQL injection.

-   **Authentication Bypass:** **POTENTIAL RISK**. `app.py:298` registers a blueprint named `newsletter_trigger_bp`. The name implies an endpoint that can trigger a newsletter send. If this endpoint is not protected by strong authentication (e.g., admin-only, internal API key with IP whitelisting), it could be abused to violate LAW 2 (One newsletter per day) and incur API costs. The code for this blueprint is not provided for review.

-   **Rate Limiting Gaps:** **PASSED**. `app.py:105` correctly implements a global rate limiter (`200 per day` per IP). While specific endpoints might need more aggressive limits, this provides a s

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main user flow: newsletter feature
The provided diff does **not actually include the core newsletter sending implementation**. `app.py` only registers newsletter blueprints:

- `routes_newsletter_trigger` registered at `app.py:297-300`
- `routes_newsletter_b1` registered at `app.py:303-305`

So for the stated feature `session2-newsletter`, the critical flow is **not auditable from the supplied code**. That alone is a release risk because the laws are mostly about newsletter behavior, and the relevant implementation is missing.

### What can be verified from supplied code

#### 1) App boot / feature registration
- App initializes correctly in a generally sane order: DB, migrate, login, limiter, cache, socketio, context processor, headers, then routes/blueprints. Good.
- `db.create_all()` at startup (`app.py:257-263`) is non-fatal and can mask migration drift in production. It may create partial schema state inconsistent with Alembic migrations.
- The app logs missing required env vars but does **not fail fast** (`app.py:77-95`). For newsletter, missing `RESEND_API_KEY` is logged as critical but app still boots. That means the feature can appear deployed while silently broken.

#### 2) Article detail flow
`core/blueprints/articles.py` is mostly functional:
- `/article/<slug>` parses ID prefix and fetches by PK (`93-100`, `239-286`)
- canonical redirect works (`250-253`)
- related articles are fetched (`162-183`, `262`)
- API listing supports pagination/filter/search/sort (`297-370`)

But there are correctness issues:

##### a) Unpublished article exposure
- `article_by_slug()` does **not** check `Article.published.is_(True)` before rendering (`245-286`).
- `article_find_by_slug()` fetches by PK only (`93-100`).
- Result: any unpublished/draft article is publicly accessible if its ID/slug is known.

##### b) Search/filter performance and semantics
- `category` filter uses `ilike("%...%")` (`319-320`) instead of exact normalized category match. That is semantically loose and defeats indexing.
- Search uses `ilike` across title/summary/tags (`322-328`), which is acceptable functionally but likely slow on SQLite without FTS.

##### c) Query count inefficiency
- In `api_articles()`, it does:
  - `q = Article.query.filter(published=True)` then `q.count()` (`313-315`)
  - if zero, resets to `Article.query` and `count()` again (`316-317`)
- That is two counts before pagination, then pagination itself issues more queries. Wasteful under load.

##### d) Deprecated ORM API
- `Query.get()` used in several places (`98`, `239`, `293`). In SQLAlchemy 2.x this is legacy. Not a production breaker, but technical debt.

#### 3) Scheduler flow
`services/scheduler.py` is broad and mostly resilient, but there are serious issues:

##### a) LAW 1 violation via SendGrid
- `_send_alert_email()` uses SendGrid (`72-97`), directly violating “Resend API only”.
- Even if “alert email” is not newsletter email, the law says **Resend API only**. This codebase is not compliant.

##### b) Potential NameError bug
- In `btc_milestone_check`, `fired` is only defined inside `if btc_price > 0:` (`458-463`), but the return expression guards it, so this is safe. No bug there.

##### c) File write race
- `sentry_megaphone` appends to a shared JSONL file in a loop (`233-248`) with no file lock.
- If multiple scheduler processes run, writes can interleave and duplicate jobs can be processed because rows are selected by status then updated later.
- There is also no row-level claim/lock before processing queued jobs.

##### d) External calls inconsistently hardened
- Telegram call has timeout (`174-177`) — good.
- SendGrid send has no explicit timeout control (`93`).
- X posting path depends on client internals; no retry/backoff.
- Many service calls in `run_task()` have no timeout boundaries because they delegate to other services not shown.

#### 4) Race conditions
- `db.create_all()` at startup in multiple app instances (`257-263`) can race during deploy scale-up.
- APScheduler initialization is guarded by a process-local lock only (`28`, `536-538`), not a distributed lock. Multiple app processes with `ENABLE_APSCHEDULER=true` will all schedule the same jobs.
- For newsletter specifically, if sending is scheduler-driven and lacks a DB uniqueness guard, this architecture is vulnerable to duplicate sends. The supplied code does not prove Law 2 is enforced anywhere.

#### 5) N+1 / repeated queries
- `inject_ads` caches active ads in `g` per request (`181-183`), so not N+1 within a request. Fine.
- `build_article_data()` itself is okay, but `article_get_sentiment()` may sort relationship lists in Python (`124-137`) for every article. If relationship loading is lazy, this can become N+1 on article lists.
- `article_get_related()` performs up to two queries per article detail page (`166-180`), acceptable.

#### 6) Edge cases
- Empty DB in article API: falls back to all articles if no published articles exist (`314-317`). That me

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — SESSION2-NEWSLETTER — CYCLE 1
**Generated:** 2026-03-10 04:12  
**Models:** Grok-3, Gemini 2.5 Pro, GPT-4o  
**Feature:** `feature/session2-newsletter` (Protocol Pulse)

---

## SCORES

| Subsystem              | Gemini | GPT-4o | Grok | Consensus |
|------------------------|--------|--------|------|-----------|
| Correctness            | 6.5/10 | 5.5/10 | 6/10 | **6.0/10** |
| Law Compliance         | 2/10   | 1.5/10 | 2/10 | **1.8/10** |
| Security               | 7.5/10 | 6/10   | 6.5/10 | **6.7/10** |
| Frontend Quality       | N/A    | N/A    | 4/10 | **N/A**    |
| Backend Quality        | 7/10   | 6.5/10 | 5.5/10 | **6.3/10** |
| World-Class Gap        | 3/10   | N/A    | 3/10 | **3.0/10** |
| **OVERALL READINESS**  | —      | —      | —    | **FAIL — Major rework needed** |

---

## UNANIMOUS FINDINGS (All 3 models agree — implement unconditionally)

### 1. **SendGrid in production codebase violates LAW 1 (Resend API only)**
- **What:** `services/scheduler.py:72-97` contains `_send_alert_email()` using SendGrid API.
- **Why it matters:** LAW 1 mandates **Resend API exclusively**. Any other email provider is a violation.
- **Fix:** Remove SendGrid dependency entirely. Replace with Resend-only implementation. Audit all imports for other email providers.
- **File/Line:** `services/scheduler.py:72-97`, `requirements.txt` (if sendgrid listed), any sendgrid imports
- **Priority:** P0 CRITICAL

---

### 2. **No unsubscribe implementation violates LAW 4 (CAN-SPAM compliance)**
- **What:** No `/unsubscribe?token={unsubscribe_token}` route, no UUID token generation, no `newsletter_subscribers` table management.
- **Why it matters:** CAN-SPAM legally requires a working unsubscribe mechanism. Absence is a regulatory violation.
- **Fix:** Implement full unsubscribe flow:
  - Generate UUID token per subscriber at signup
  - Store in `newsletter_subscribers.unsubscribe_token`
  - Create `/unsubscribe` GET route that validates token and marks subscriber as unsubscribed
  - Include unsubscribe link in all newsletter emails
- **File/Line:** `routes_newsletter_b1.py` (not provided, but must be created/audited)
- **Priority:** P0 CRITICAL

---

### 3. **Newsletter sending code not in audit package (core feature missing)**
- **What:** `routes_newsletter_b1.py` and `routes_newsletter_trigger.py` are registered in `app.py:303-305` but **not provided for review**. These contain the newsletter assembly, sending, and LAW 2/LAW 3 compliance logic.
- **Why it matters:** Without this code, audit cannot verify that:
  - Only one newsletter per day is sent (LAW 2)
  - Newsletter format matches spec (LAW 3)
  - Resend API is actually used (LAW 1)
  - Unsubscribe tokens are included (LAW 4)
- **Fix:** Include `routes_newsletter_*.py` and all referenced utility modules in next audit cycle.
- **File/Line:** `app.py:303-305` (blueprint registration), missing files
- **Priority:** P0 CRITICAL (blocks audit sign-off)

---

### 4. **Missing fail-fast for r

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

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
 313 | # SESSION 6 — Schiff Bot Blueprint
 314 | try:
 315 |     from core.blueprints.schiff import schiff_bp
 316 |     app.register_blueprint(schiff_bp)
 317 |     logging.info("Schiff Bot blueprint registered (/schiff, /api/schiff/*)")
 318 | except Exception as _e:
 319 |     logging.warning("Schiff Bot blueprint not loaded: %s", _e)
 320 | 
 321 | # SESSION 10 — Article Rebuild Blueprint
 322 | try:
 323 |     from core.blueprints.articles import articles_bp
 324 |     app.register_blueprint(articles_bp)
 325 |     logging.info("Articles blueprint registered (/article/<slug>, /api/v2/articles)")
 326 | except Exception as _e:
 327 |     logging.warning("Articles blueprint not loaded: %s", _e)
 328 | 
 329 | # SESSION 9 — Node Watch Blueprint
 330 | try:
 331 |     from core.blueprints.node_watch import node_watch_bp
 332 |     app.register_blueprint(node_watch_bp)
 333 |     logging.info("Node Watch blueprint registered (/node-watch, /api/nodes/*)")
 334 | except Exception as _e:
 335 |     logging.warning("Node Watch blueprint not loaded: %s", _e)
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

### File: core/blueprints/articles.py (385 lines)
```
   1 | """
   2 | SESSION 10 — ARTICLE REBUILD
   3 | core/blueprints/articles.py
   4 | 
   5 | Registered in both core/app.py and app.py.
   6 | 
   7 | Routes:
   8 |   GET /article/<slug>           — article detail by slug (NEW — no conflict with routes.py)
   9 |   GET /articles/<int:id>/slug   — redirect to /article/<slug>
  10 |   GET /api/v2/articles          — JSON listing API (paginated, filterable)
  11 | 
  12 | Helper functions (imported by routes.py for /articles list page):
  13 |   build_article_data()          — builds rich dicts for template rendering
  14 |   article_get_image()           — normalised image URL
  15 |   article_get_sentiment()       — BULLISH/BEARISH/NEUTRAL dict
  16 |   article_get_read_time()       — minutes at 200 wpm
  17 |   article_get_related()         — always-3 related articles
  18 |   article_cat_color()           — hex colour per category
  19 |   article_cat_gradient()        — CSS gradient per category
  20 |   article_make_slug()           — {id}-{title-slug}
  21 |   article_tldr_bullets()        — "What you need to know" 3-bullet list
  22 | """
  23 | 
  24 | from __future__ import annotations
  25 | 
  26 | import logging
  27 | import re
  28 | from datetime import datetime
  29 | 
  30 | from flask import Blueprint, jsonify, redirect, render_template, request, url_for
  31 | 
  32 | logger = logging.getLogger(__name__)
  33 | 
  34 | # ─── Category colour / gradient maps ─────────────────────────────────────────
  35 | 
  36 | CATEGORY_COLORS: dict[str, str] = {
  37 |     "mining":       "#f7931a",
  38 |     "regulation":   "#dc2626",
  39 |     "etfs":         "#3b82f6",
  40 |     "lightning":    "#eab308",
  41 |     "macro":        "#a855f7",
  42 |     "technical":    "#06b6d4",
  43 |     "bitcoin":      "#f97316",
  44 |     "editorial":    "#10b981",
  45 |     "defi":         "#6366f1",
  46 |     "web3":         "#8b5cf6",
  47 |     "security":     "#ef4444",
  48 |     "institutional":"#0ea5e9",
  49 |     "markets":      "#14b8a6",
  50 |     "adoption":     "#22c55e",
  51 |     "default":      "#9ca3af",
  52 | }
  53 | 
  54 | CATEGORY_GRADIENTS: dict[str, str] = {
  55 |     "mining":       "linear-gradient(135deg,#1a1200,#2d1e00)",
  56 |     "regulation":   "linear-gradient(135deg,#1a0a0a,#2d1515)",
  57 |     "etfs":         "linear-gradient(135deg,#0a1628,#0f2545)",
  58 |     "lightning":    "linear-gradient(135deg,#1a1500,#2d2400)",
  59 |     "macro":        "linear-gradient(135deg,#120a1a,#1f1030)",
  60 |     "technical":    "linear-gradient(135deg,#0a1a1a,#0f2d2d)",
  61 |     "bitcoin":      "linear-gradient(135deg,#1a0e00,#2d1800)",
  62 |     "editorial":    "linear-gradient(135deg,#0a1a12,#0f2d1e)",
  63 |     "default":      "linear-gradient(135deg,#0d0d1a,#1a1a2e)",
  64 | }
  65 | 
  66 | SENTIMENT_MAP: dict[str, dict] = {
  67 |     "bullish":  {"label": "BULLISH",  "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
  68 |     "bearish":  {"label": "BEARISH",  "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
  69 |     "neutral":  {"label": "NEUTRAL",  "color": "#6b7280", "bg": "rgba(107,114,128,0.12)"},
  70 |     "positive": {"label": "BULLISH",  "color": "#22c55e", "bg": "rgba(34,197,94,0.12)"},
  71 |     "negative": {"label": "BEARISH",  "color": "#dc2626", "bg": "rgba(220,38,38,0.12)"},
  72 | }
  73 | 
  74 | _BULLISH_SIGNALS = {
  75 |     "ath", "all-time high", "rally", "surge", "breakout", "adoption", "etf approved",
  76 |     "approval", "institutional", "accumulate", "bullish", "hodl", "all time high",
  77 |     "record", "positive", "growth", "expand", "partnership", "launch", "inflows",
  78 | }
  79 | _BEARISH_SIGNALS = {
  80 |     "ban", "crackdown", "hack", "exploit", "fraud", "scam", "crash", "dump",
  81 |     "lawsuit", "sec charges", "warning", "concern", "liquidation", "fud",
  82 |     "decline", "bearish", "sell-off", "capitulation",
  83 | }
  84 | 
  85 | # ─── Helper functions ─────────────────────────────────────────────────────────
  86 | 
  87 | def article_make_slug(article) -> str:
  88 |     """Return URL-safe slug: {id}-{title-words}. ID prefix enables O(1) lookup."""
  89 |     title_part = re.sub(r"[^a-z0-9]+", "-", (article.title or "").lower()).strip("-")[:60]
  90 |     return f"{article.id}-{title_part}"
  91 | 
  92 | 
  93 | def article_find_by_slug(slug: str):
  94 |     """Extract article ID from slug prefix and look up by PK. Never crashes."""
  95 |     try:
  96 |         from models import Article
  97 |         article_id = int(slug.split("-", 1)[0])
  98 |         return Article.query.get(article_id)
  99 |     except Exception:
 100 |         return None
 101 | 
 102 | 
 103 | def article_get_image(article) -> str:
 104 |     """Return best available image URL — cover_image_url preferred (ARTICLE_PAGE_LAWS Law 1)."""
 105 |     for attr in ("cover_image_url", "header_image_url"):
 106 |         url = (getattr(article, attr, None) or "").strip()
 107 |         if url and url.startswith("http"):
 108 |             return url
 109 |         if url and url.startswith("/static/") and "default-header" not in url:
 110 |             return url
 111 |     return ""
 112 | 
 113 | 
 114 | def article_get_sentiment(article) -> dict:
 115 |     """Return BULLISH/BEARISH/NEUTRAL dict. Never crashes."""
 116 |     try:
 117 |         # 1. DB column (added by p3-sentiment-intel migration)
 118 |         col_val = getattr(article, "sentiment", None)
 119 |         if col_val:
 120 |             key = col_val.lower().strip()
 121 |             if key in SENTIMENT_MAP:
 122 |                 return SENTIMENT_MAP[key]
 123 |         # 2. SentimentReport backref (ORM relationship)
 124 |         reports = getattr(article, "sentiment_report", None)
 125 |         if reports:
 126 |             report = sorted(reports, key=lambda r: r.id, reverse=True)[0] if isinstance(reports, list) else reports
 127 |             if report:
 128 |                 if report.overall_sentiment:
 129 |                     key = report.overall_sentiment.lower().strip()
 130 |                     if key in SENTIMENT_MAP:
 131 |                         return SENTIMENT_MAP[key]
 132 |                 if report.sentiment_score is not None:
 133 |                     if report.sentiment_score > 55:
 134 |                         return SENTIMENT_MAP["bullish"]
 135 |                     if report.sentiment_score < 40:
 136 |                         return SENTIMENT_MAP["bearish"]
 137 |                     return SENTIMENT_MAP["neutral"]
 138 |     except Exception:
 139 |         pass
 140 |     # 3. Keyword inference
 141 |     text = " ".join([
 142 |         (getattr(article, "title", None) or ""),
 143 |         (getattr(article, "summary", None) or "")[:200],
 144 |         (getattr(article, "tags", None) or ""),
 145 |     ]).lower()
 146 |     bull = sum(1 for w in _BULLISH_SIGNALS if w in text)
 147 |     bear = sum(1 for w in _BEARISH_SIGNALS if w in text)
 148 |     if bull > bear and bull >= 2:
 149 |         return SENTIMENT_MAP["bullish"]
 150 |     if bear > bull and bear >= 2:
 151 |         return SENTIMENT_MAP["bearish"]
 152 |     return SENTIMENT_MAP["neutral"]
 153 | 
 154 | 
 155 | def article_get_read_time(article) -> int:
 156 |     """Estimate read time in minutes at 200 wpm."""
 157 |     content = getattr(article, "content", None) or ""
 158 |     word_count = len(re.sub(r"<[^>]+>", "", content).split())
 159 |     return max(1, round(word_count / 200))
 160 | 
 161 | 
 162 | def article_get_related(article, db, Article, limit: int = 3) -> list:
 163 |     """Always returns exactly `limit` articles. Same-category first, then pads."""
 164 |     related: list = []
 165 |     try:
 166 |         if article.category:
 167 |             related = (
 168 |                 Article.query
 169 |                 .filter(Article.id != article.id, Article.published.is_(True),
 170 |                         Article.category == article.category)
 171 |                 .order_by(Article.created_at.desc()).limit(limit).all()
 172 |             )
 173 |         if len(related) < limit:
 174 |             exc_ids = [article.id] + [r.id for r in related]
 175 |             pad = (
 176 |                 Article.query
 177 |                 .filter(~Article.id.in_(exc_ids), Article.published.is_(True))
 178 |                 .order_by(Article.created_at.desc()).limit(limit - len(related)).all()
 179 |             )
 180 |             related.extend(pad)
 181 |     except Exception as exc:
 182 |         logger.warning("article_get_related failed: %s", exc)
 183 |     return related[:limit]
 184 | 
 185 | 
 186 | def article_cat_color(category: str | None) -> str:
 187 |     return CATEGORY_COLORS.get((category or "default").lower(), CATEGORY_COLORS["default"])
 188 | 
 189 | 
 190 | def article_cat_gradient(category: str | None) -> str:
 191 |     return CATEGORY_GRADIENTS.get((category or "default").lower(), CATEGORY_GRADIENTS["default"])
 192 | 
 193 | 
 194 | def article_tldr_bullets(article, max_bullets: int = 3) -> list[str]:
 195 |     """
 196 |     'What you need to know' — 3 bullet TL;DR above article body.
 197 |     Derived from summary (sentence split) or first sentences of content.
 198 |     No Claude API call — instant, never crashes.
 199 |     """
 200 |     try:
 201 |         text = (getattr(article, "summary", None) or "").strip()
 202 |         if not text:
 203 |             # Fall back to stripped content first 500 chars
 204 |             raw = re.sub(r"<[^>]+>", " ", getattr(article, "content", None) or "")
 205 |             text = re.sub(r"\s+", " ", raw).strip()[:600]
 206 |         # Split on sentence boundaries
 207 |         sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip() and len(s.strip()) > 15]
 208 |         bullets = sentences[:max_bullets]
 209 |         # Ensure sentences end with punctuation
 210 |         bullets = [b if b[-1] in ".!?" else b + "." for b in bullets]
 211 |         return bullets
 212 |     except Exception:
 213 |         return []
 214 | 
 215 | 
 216 | def build_article_data(articles, limit: int = 0) -> list[dict]:
 217 |     """Build article_data list for template rendering."""
 218 |     if limit:
 219 |         articles = articles[:limit]
 220 |     result = []
 221 |     for a in articles:
 222 |         result.append({
 223 |             "article":      a,
 224 |             "image_url":    article_get_image(a),
 225 |             "sentiment":    article_get_sentiment(a),
 226 |             "read_time":    article_get_read_time(a),
 227 |             "cat_color":    article_cat_color(a.category),
 228 |             "cat_gradient": article_cat_gradient(a.category),
 229 |             "slug":         article_make_slug(a),
 230 |         })
 231 |     return result
 232 | 
 233 | 
 234 | # ─── Blueprint ────────────────────────────────────────────────────────────────
 235 | 
 236 | articles_bp = Blueprint("articles_bp", __name__)
 237 | 
 238 | 
 239 | @articles_bp.route("/article/<slug>")
 240 | def article_by_slug(slug):
 241 |     """Individual article page — slug-based URL (SESSION 10 spec)."""
 242 |     from app import db
 243 |     from models import Article
 244 | 
 245 |     article = article_find_by_slug(slug)
 246 |     if article is None:
 247 |         from flask import abort
 248 |         abort(404)
 249 | 
 250 |     # Redirect to canonical slug if URL doesn't match
 251 |     canonical = article_make_slug(article)
 252 |     if slug != canonical:
 253 |         return redirect(url_for("articles_bp.article_by_slug", slug=canonical), 301)
 254 | 
 255 |     # Enrich
 256 |     sentiment     = article_get_sentiment(article)
 257 |     cat_color     = article_cat_color(article.category)
 258 |     cat_gradient  = article_cat_gradient(article.category)
 259 |     read_time     = article_get_read_time(article)
 260 |     header_image  = article_get_image(article) or "/static/images/default-header.png"
 261 |     tldr_bullets  = article_tldr_bullets(article)
 262 |     related_list  = article_get_related(article, db, Article, 3)
 263 |     related_data  = build_article_data(related_list)
 264 | 
 265 |     # Key takeaways (same as TL;DR bullets for now — spec says Claude-generated,
 266 |     # but we use instant extraction to avoid API calls on every page view)
 267 |     key_takeaways_bullets = tldr_bullets
 268 | 
 269 |     # Body HTML: strip duplicate TL;DR block if content generator embedded it
 270 |     body_html = _strip_tldr_block(article.content or "")
 271 | 
 272 |     return render_template(
 273 |         "article_detail.html",
 274 |         article=article,
 275 |         sentiment=sentiment,
 276 |         cat_color=cat_color,
 277 |         cat_gradient=cat_gradient,
 278 |         read_time=read_time,
 279 |         header_image_url=header_image,
 280 |         tldr_bullets=tldr_bullets,
 281 |         key_takeaways_bullets=key_takeaways_bullets,
 282 |         related_articles=related_list,
 283 |         related_data=related_data,
 284 |         body_html=body_html,
 285 |         article_slug=canonical,
 286 |     )
 287 | 
 288 | 
 289 | @articles_bp.route("/articles/<int:article_id>/slug")
 290 | def article_id_to_slug(article_id):
 291 |     """Redirect legacy ID URLs to canonical slug URL."""
 292 |     from models import Article
 293 |     article = Article.query.get_or_404(article_id)
 294 |     return redirect(url_for("articles_bp.article_by_slug", slug=article_make_slug(article)), 301)
 295 | 
 296 | 
 297 | @articles_bp.route("/api/v2/articles")
 298 | def api_articles():
 299 |     """
 300 |     Paginated JSON API — used by Load More and client-side search.
 301 |     Params: page, per_page, category, q (search), sort
 302 |     """
 303 |     from app import db
 304 |     from models import Article
 305 | 
 306 |     try:
 307 |         page     = max(1, request.args.get("page", 1, type=int))
 308 |         per_page = min(50, request.args.get("per_page", 24, type=int))
 309 |         category = request.args.get("category", "").strip()
 310 |         search   = request.args.get("q", request.args.get("search", "")).strip()
 311 |         sort     = request.args.get("sort", "newest")
 312 | 
 313 |         q = Article.query.filter(Article.published.is_(True))
 314 |         total = q.count()
 315 |         if total == 0:
 316 |             q = Article.query
 317 |             total = q.count()
 318 | 
 319 |         if category and category.lower() != "all":
 320 |             q = q.filter(Article.category.ilike(f"%{category}%"))
 321 | 
 322 |         if search:
 323 |             like = f"%{search}%"
 324 |             q = q.filter(db.or_(
 325 |                 Article.title.ilike(like),
 326 |                 Article.summary.ilike(like),
 327 |                 Article.tags.ilike(like),
 328 |             ))
 329 | 
 330 |         if sort == "oldest":
 331 |             q = q.order_by(Article.created_at.asc())
 332 |         else:
 333 |             q = q.order_by(Article.created_at.desc())
 334 | 
 335 |         paged = q.paginate(page=page, per_page=per_page, error_out=False)
 336 | 
 337 |         def _to_dict(a):
 338 |             img  = article_get_image(a)
 339 |             sent = article_get_sentiment(a)
 340 |             return {
 341 |                 "id":               a.id,
 342 |                 "slug":             article_make_slug(a),
 343 |                 "title":            a.title or "",
 344 |                 "summary":          a.summary or re.sub(r"<[^>]+>", "", a.content or "")[:280],
 345 |                 "category":         a.category or "Bitcoin",
 346 |                 "category_color":   article_cat_color(a.category),
 347 |                 "category_gradient":article_cat_gradient(a.category),
 348 |                 "cover_image_url":  img,
 349 |                 "sentiment_label":  sent["label"],
 350 |                 "sentiment_color":  sent["color"],
 351 |                 "sentiment_bg":     sent["bg"],
 352 |                 "source":           a.author or a.source_type or "Protocol Pulse",
 353 |                 "read_time":        article_get_read_time(a),
 354 |                 "created_at":       a.created_at.isoformat() if a.created_at else "",
 355 |                 "url":              f"/article/{article_make_slug(a)}",
 356 |                 "is_featured":      bool(getattr(a, "featured", False)),
 357 |             }
 358 | 
 359 |         return jsonify({
 360 |             "articles":    [_to_dict(a) for a in paged.items],
 361 |             "page":        page,
 362 |             "per_page":    per_page,
 363 |             "total":       paged.total,
 364 |             "total_pages": paged.pages,
 365 |             "has_more":    paged.has_next,
 366 |             "meta": {"generated_at": datetime.utcnow().isoformat() + "Z"},
 367 |         })
 368 |     except Exception as err:
 369 |         logger.error("api_articles error: %s", err)
 370 |         return jsonify({"articles": [], "error": str(err), "has_more": False}), 500
 371 | 
 372 | 
 373 | # ─── Private helpers ──────────────────────────────────────────────────────────
 374 | 
 375 | def _strip_tldr_block(content: str) -> str:
 376 |     """Remove duplicate TL;DR block that content_generator sometimes embeds."""
 377 |     try:
 378 |         from services.content_generator import strip_duplicate_tldr
 379 |         return strip_duplicate_tldr(content)
 380 |     except Exception:
 381 |         pass
 382 |     # Fallback: strip common TL;DR markers
 383 |     content = re.sub(r"<[^>]*>\s*TL;DR.*?</[^>]*>", "", content, flags=re.IGNORECASE | re.DOTALL)
 384 |     return content
 385 | 
```

### File: services/scheduler.py (582 lines)
```
   1 | import os as _twt_os
   2 | _TWEETS_ON = _twt_os.environ.get("ENABLE_TWEETS", "false").lower() == "true"
   3 | 
   4 | """
   5 | Central scheduler for Protocol Pulse automation tasks.
   6 | Defines the 6 Replit-style tasks; run via cron hitting a single endpoint or run_task(name).
   7 | 
   8 | Tasks:
   9 | - Cypherpunk'd Loop: every 6h — article generation from trending
  10 | - Social Guard: every 10min — (optional) social listening / reply checks
  11 | - Sarah Daily Brief: 05:45 UTC — prep
  12 | - Sarah Intelligence Briefing: 06:00 UTC — generate and publish daily brief
  13 | - Sentiment Buffer Update: every 5min — rolling sentiment
  14 | - Emergency Flash Check: every 5min — detect 40%+ sentiment drift
  15 | """
  16 | 
  17 | import json
  18 | import logging
  19 | import os
  20 | import subprocess
  21 | from datetime import datetime
  22 | from typing import Dict, List, Optional
  23 | from threading import Lock
  24 | 
  25 | logger = logging.getLogger(__name__)
  26 | _scheduler_started_at: Optional[datetime] = None
  27 | _apscheduler = None  # BackgroundScheduler, set in initialize_scheduler
  28 | _scheduler_lock = Lock()
  29 | 
  30 | # When False (default), Queued SentryJob posts are only written to data/pulseevents.jsonl with [DRY-RUN]. No live posting.
  31 | ENABLE_LIVE_POSTING = os.environ.get("ENABLE_LIVE_POSTING", "false").strip().lower() in {"1", "true", "yes", "on"}
  32 | 
  33 | # New article draft schedule: burst 4 every 15 min (UTC 00–07), break (08–11), then 1/hour (12–23). Only active when set.
  34 | ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE = os.environ.get("ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE", "false").strip().lower() in {"1", "true", "yes", "on"}
  35 | 
  36 | # Replit-style: generate one breaking_news article every 15 minutes (with DB lock).
  37 | # Keep OFF until explicitly enabled.
  38 | ENABLE_ARTICLE_AUTOMATION_15M = os.environ.get("ENABLE_ARTICLE_AUTOMATION_15M", "false").strip().lower() in {"1", "true", "yes", "on"}
  39 | 
  40 | # UTC hour windows: burst = 0–7, break = 8–11, slow = 12–23
  41 | ARTICLE_DRAFT_BURST_HOURS = set(range(0, 8))   # 00:00–07:59 UTC
  42 | ARTICLE_DRAFT_SLOW_HOURS = set(range(12, 24)) # 12:00–23:59 UTC
  43 | 
  44 | TASKS = {
  45 |     "x_engagement_cycle": {"interval_minutes": 5, "description": "X Engagement Sentry cycle (every 5m)"},
  46 |     "sentry_megaphone": {"interval_minutes": 2, "description": "SentryJob Queued -> pulseevents.jsonl [DRY-RUN] (no live post when ENABLE_LIVE_POSTING=False)"},
  47 |     "mining_snapshot_hourly": {"interval_minutes": 60, "description": "Mining risk snapshot_all (hourly)"},
  48 |     "cypherpunk_loop": {"interval_minutes": 120, "description": "Article auto-draft from trending (every 2h, around the clock)"},
  49 |     "social_guard": {"interval_minutes": 10, "description": "Social listening / reply checks"},
  50 |     "sarah_brief_prep": {"cron": "05:45", "description": "Sarah daily brief prep (05:45 UTC)"},
  51 |     "sarah_intelligence_briefing": {"cron": "06:00", "description": "Sarah daily intelligence briefing (06:00 UTC)"},
  52 |     "sentiment_buffer_update": {"interval_minutes": 5, "description": "Rolling sentiment buffer update"},
  53 |     "emergency_flash_check": {"interval_minutes": 5, "description": "Emergency flash check (40%+ drift)"},
  54 |     "daily_distribution_brief_9am_est": {"cron_est": "09:00", "description": "Sentry auto-poster daily brief dispatch (09:00 EST)"},
  55 |     "daily_medley_gpu1": {"cron_est": "09:10", "description": "Daily Beat medley render (GPU 1, 60s)"},
  56 |     "monetization_injector": {"interval_minutes": 30, "description": "Smart-link injector scan for briefs + x drafts"},
  57 |     "pulse_drop_rebuild_5am": {"cron_est": "05:00", "description": "Pulse Drop daily rebuild (05:00 EST)"},
  58 |     "auto_viral_reel": {"interval_minutes": 30, "description": "Viral reel: monitor → clip → narration → publish (X/Telegram if ENABLE_LIVE_POSTING)"},
  59 |     "intel_medley": {"interval_minutes": 60, "description": "Automated Intel Medley: monitor UC9ZM3N0ybRtp44 + partners, 3-5 clips, 5-10 min briefing, outro + CTAs"},
  60 |     "article_draft_burst_4": {"interval_minutes": 15, "description": "Article draft burst: 4 articles every 15 min (UTC 00–07 only, when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE)"},
  61 |     "article_draft_hourly_1": {"interval_minutes": 60, "description": "Article draft slow: 1 article per hour (UTC 12–23 only, when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE)"},
  62 |     "article_generation_15m": {"interval_minutes": 15, "description": "Replit-style: generate 1 breaking_news article every 15 minutes (when ENABLE_ARTICLE_AUTOMATION_15M)"},
  63 |     "affiliate_education_morning": {"cron": "11:00", "description": "Affiliate education article #1 (11:00 UTC / 6am EST)"},
  64 |     "affiliate_education_evening": {"cron": "21:00", "description": "Affiliate education article #2 (21:00 UTC / 4pm EST)"},
  65 |     # F6 Marketing OS
  66 |     "btc_milestone_check": {"interval_minutes": 5, "description": "F6: BTC price milestone check — fires campaigns at 100K/120K/.../1M (never repeats)"},
  67 |     "daily_metrics_snapshot": {"interval_minutes": 60, "description": "F6: Daily performance metrics snapshot (hourly upsert)"},
  68 |     "weekly_performance_analysis": {"cron": "00:00", "cron_day": "sun", "description": "F6: Weekly performance analysis (Sunday 00:00 UTC)"},
  69 | }
  70 | 
  71 | 
  72 | def _send_alert_email(subject: str, body: str) -> bool:
  73 |     """Send alert email on failure. Uses SENDGRID_API_KEY and CONTACT_EMAIL or VIRAL_ALERT_EMAIL."""
  74 |     to = os.environ.get("VIRAL_ALERT_EMAIL") or os.environ.get("CONTACT_EMAIL") or os.environ.get("SENDGRID_FROM_EMAIL")
  75 |     if not to:
  76 |         return False
  77 |     try:
  78 |         from sendgrid import SendGridAPIClient
  79 |         from sendgrid.helpers.mail import Mail, Email, To, Content
  80 |     except ImportError:
  81 |         return False
  82 |     api_key = os.environ.get("SENDGRID_API_KEY")
  83 |     if not api_key:
  84 |         return False
  85 |     from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@protocolpulse.io")
  86 |     message = Mail(
  87 |         from_email=Email(from_email, "Protocol Pulse"),
  88 |         to_emails=To(to),
  89 |         subject=subject[:200],
  90 |         plain_text_content=Content("text/plain", body[:10000]),
  91 |     )
  92 |     try:
  93 |         SendGridAPIClient(api_key).send(message)
  94 |         return True
  95 |     except Exception as e:
  96 |         logger.warning("Alert email failed: %s", e)
  97 |         return False
  98 | 
  99 | 
 100 | def auto_viral_reel() -> Dict:
 101 |     """
 102 |     Batch 5: monitor → clip → narration → publish.
 103 |     Runs every 30m. If ENABLE_LIVE_POSTING, publishes to X and Telegram.
 104 |     On failure sends alert email.
 105 |     """
 106 |     try:
 107 |         from app import app
 108 |         import models
 109 |         from services.viralmoments import ViralMomentsReelEngine
 110 |         from pathlib import Path
 111 | 
 112 |         engine = ViralMomentsReelEngine()
 113 |         with app.app_context():
 114 |             # 1) Monitor partners (create ClipJobs for new videos)
 115 |             mon = engine.monitor_partners()
 116 |             job_ids = mon.get("job_ids") or []
 117 |             # 2) Pick one Planned job and render reel (or use latest Completed for publish-only)
 118 |             job = (
 119 |                 models.ClipJob.query.filter(models.ClipJob.status == "Planned")
 120 |                 .order_by(models.ClipJob.id.asc())
 121 |                 .first()
 122 |             )
 123 |             if not job:
 124 |                 return {
 125 |                     "success": True,
 126 |                     "message": "auto_viral_reel: no Planned job; monitor only",
 127 |                     "result": {"monitor": mon, "published": False},
 128 |                 }
 129 |             # 3) Render reel (includes optional voiceover if VIRAL_ADD_VOICEOVER=1)
 130 |             render = engine.render_reel(job)
 131 |             if not render.get("ok"):
 132 |                 _send_alert_email(
 133 |                     "[Protocol Pulse] auto_viral_reel render failed",
 134 |                     f"job_id={job.id} video_id={job.video_id}\nerror={render.get('error', 'unknown')}",
 135 |                 )
 136 |                 return {
 137 |                     "success": False,
 138 |                     "message": render.get("error", "render failed"),
 139 |                     "result": {"render": render},
 140 |                 }
 141 |             out_path = render.get("output_path")
 142 |             base_url = os.environ.get("BASE_URL", "https://protocolpulse.io").rstrip("/")
 143 |             reel_url = f"{base_url}/static/clips/reels/{Path(out_path or '').name}" if out_path else None
 144 |             if not reel_url and out_path:
 145 |                 reel_url = f"{base_url}/{out_path}" if not out_path.startswith("http") else out_path
 146 | 
 147 |             published_x = False
 148 |             published_tg = False
 149 |             if ENABLE_LIVE_POSTING and reel_url:
 150 |                 # 4a) Publish to X (tweet with link)
 151 |                 try:
 152 |                     from services.x_service import XService
 153 |                     x = XService()
 154 |                     if x.client or getattr(x, "client_v2", None):
 155 |                         text = f"New Intel Briefing reel — {job.channel_name or 'Partner'} | {reel_url}"
 156 |                         if len(text) > 280:
 157 |                             text = f"Intel Briefing | {job.channel_name or 'Partner'} {reel_url}"
 158 |                         if x.client:
 159 |                             x.client.update_status(text[:280])
 160 |                             published_x = True
 161 |                         elif getattr(x, "client_v2", None) and x.client_v2:
 162 |                             x.client_v2.create_tweet(text=text[:280])
 163 |                             published_x = True
 164 |                 except Exception as ex:
 165 |                     logger.warning("auto_viral_reel X post failed: %s", ex)
 166 |                     _send_alert_email("[Protocol Pulse] auto_viral_reel X post failed", str(ex))
 167 |                 # 4b) Publish to Telegram (message with link)
 168 |                 try:
 169 |                     token = os.environ.get("TELEGRAM_BOT_TOKEN")
 170 |                     chat_id = os.environ.get("TELEGRAM_CHAT_ID")
 171 |                     if token and chat_id:
 172 |                         import requests
 173 |                         msg = f"Intel Briefing reel — {job.channel_name or 'Partner'}\n{reel_url}"
 174 |                         r = requests.post(
 175 |                             f"https://api.telegram.org/bot{token}/sendMessage",
 176 |                             json={"chat_id": chat_id, "text": msg},
 177 |                             timeout=10,
 178 |                         )
 179 |                         published_tg = r.status_code == 200
 180 |                 except Exception as ex:
 181 |                     logger.warning("auto_viral_reel Telegram post failed: %s", ex)
 182 |                     _send_alert_email("[Protocol Pulse] auto_viral_reel Telegram failed", str(ex))
 183 | 
 184 |             return {
 185 |                 "success": True,
 186 |                 "message": "auto_viral_reel: reel rendered" + (" and published" if (published_x or published_tg) else ""),
 187 |                 "result": {
 188 |                     "job_id": job.id,
 189 |                     "reel_url": reel_url,
 190 |                     "published_x": published_x,
 191 |                     "published_tg": published_tg,
 192 |                     "monitor": mon,
 193 |                 },
 194 |             }
 195 |     except Exception as e:
 196 |         logger.exception("auto_viral_reel failed: %s", e)
 197 |         _send_alert_email(
 198 |             "[Protocol Pulse] auto_viral_reel failed",
 199 |             f"auto_viral_reel error:\n{type(e).__name__}: {e}",
 200 |         )
 201 |         return {"success": False, "message": str(e), "result": None}
 202 | 
 203 | 
 204 | def run_task(name: str) -> Dict:
 205 |     if name == "x_engagement_cycle":
 206 |         try:
 207 |             from app import app
 208 |             from core.services.x_engagement_sentry import run_cycle
 209 |             with app.app_context():
 210 |                 out = run_cycle()
 211 |             return {"success": bool(out.get("success")), "message": "X engagement cycle run", "result": out}
 212 |         except Exception as e:
 213 |             logger.warning("x_engagement_cycle failed: %s", e)
 214 |             return {"success": False, "message": str(e), "result": None}
 215 | 
 216 |     if name == "mining_snapshot_hourly":
 217 |         try:
 218 |             from app import app
 219 |             from services.mining_risk_service import snapshot_all
 220 |             with app.app_context():
 221 |                 out = snapshot_all()
 222 |             return {"success": bool(out.get("success")), "message": "Mining snapshot captured", "result": out}
 223 |         except Exception as e:
 224 |             logger.warning("mining_snapshot_hourly failed: %s", e)
 225 |             return {"success": False, "message": str(e), "result": None}
 226 | 
 227 |     if name == "sentry_megaphone":
 228 |         try:
 229 |             from app import app
 230 |             from pathlib import Path
 231 |             with app.app_context():
 232 |                 import models
 233 |                 jobs = models.SentryJob.query.filter_by(status="Queued").limit(50).all()
 234 |                 log_path = Path(app.root_path) / "data" / "pulseevents.jsonl"
 235 |                 log_path.parent.mkdir(parents=True, exist_ok=True)
 236 |                 written = 0
 237 |                 for job in jobs:
 238 |                     line = json.dumps({
 239 |                         "ts": datetime.utcnow().isoformat() + "Z",
 240 |                         "tag": "DRY-RUN",
 241 |                         "message": f"[DRY-RUN] SentryJob id={job.id} platform={job.platform}",
 242 |                         "sentry_job_id": job.id,
 243 |                         "platform": job.platform,
 244 |                         "content_preview": (job.content or "")[:200],
 245 |                     }) + "\n"
 246 |                     with open(log_path, "a", encoding="utf-8") as f:
 247 |                         f.write(line)
 248 |                     job.status = "Written"
 249 |                     written += 1
 250 |                 if written:
 251 |                     from app import db
 252 |                     db.session.commit()
 253 |             return {"success": True, "message": f"Sentry megaphone: {written} queued posts written to pulseevents.jsonl", "result": {"written": written, "live_posting": ENABLE_LIVE_POSTING}}
 254 |         except Exception as e:
 255 |             logger.warning("sentry_megaphone failed: %s", e)
 256 |             return {"success": False, "message": str(e), "result": None}
 257 | 
 258 |     """
 259 |     Run a single named task. Returns { success, message, result }.
 260 |     """
 261 |     if name == "cypherpunk_loop":
 262 |         if ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 263 |             return {"success": True, "message": "cypherpunk_loop disabled when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE is on", "result": None}
 264 |         try:
 265 |             from services.automation import generate_article_with_tracking
 266 |             out = generate_article_with_tracking()
 267 |             return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
 268 |         except Exception as e:
 269 |             logger.exception("cypherpunk_loop failed: %s", e)
 270 |             return {"success": False, "message": str(e), "result": None}
 271 | 
 272 |     if name == "article_draft_burst_4":
 273 |         if not ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 274 |             return {"success": True, "message": "article_draft_burst_4 skipped (new schedule disabled)", "result": None}
 275 |         hour_utc = datetime.utcnow().hour
 276 |         if hour_utc not in ARTICLE_DRAFT_BURST_HOURS:
 277 |             return {"success": True, "message": f"article_draft_burst_4 outside burst window (UTC hour {hour_utc})", "result": None}
 278 |         try:
 279 |             from services.automation import generate_article_with_tracking
 280 |             results = []
 281 |             for _ in range(4):
 282 |                 out = generate_article_with_tracking(force=True)
 283 |                 results.append(out)
 284 |             ok = any(r.get("success") for r in results)
 285 |             return {"success": ok, "message": f"Burst 4: {sum(1 for r in results if r.get('success'))}/4", "result": results}
 286 |         except Exception as e:
 287 |             logger.exception("article_draft_burst_4 failed: %s", e)
 288 |             return {"success": False, "message": str(e), "result": None}
 289 | 
 290 |     if name == "article_draft_hourly_1":
 291 |         if not ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 292 |             return {"success": True, "message": "article_draft_hourly_1 skipped (new schedule disabled)", "result": None}
 293 |         hour_utc = datetime.utcnow().hour
 294 |         if hour_utc not in ARTICLE_DRAFT_SLOW_HOURS:
 295 |             return {"success": True, "message": f"article_draft_hourly_1 outside slow window (UTC hour {hour_utc})", "result": None}
 296 |         try:
 297 |             from services.automation import generate_article_with_tracking
 298 |             out = generate_article_with_tracking(force=True)
 299 |             return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
 300 |         except Exception as e:
 301 |             logger.exception("article_draft_hourly_1 failed: %s", e)
 302 |             return {"success": False, "message": str(e), "result": None}
 303 | 
 304 |     if name == "article_generation_15m":
 305 |         if not ENABLE_ARTICLE_AUTOMATION_15M:
 306 |             return {"success": True, "message": "article_generation_15m skipped (disabled)", "result": None}
 307 |         try:
 308 |             from services.automation import generate_breaking_article_with_tracking
 309 |             out = generate_breaking_article_with_tracking()
 310 |             return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
 311 |         except Exception as e:
 312 |             logger.exception("article_generation_15m failed: %s", e)
 313 |             return {"success": False, "message": str(e), "result": None}
 314 | 
 315 |     if name == "social_guard":
 316 |         # Optional: social_listener check or reply queue
 317 |         return {"success": True, "message": "Social guard (no-op)", "result": None}
 318 | 
 319 |     if name == "sarah_brief_prep":
 320 |         # Optional: collect signals before brief
 321 |         try:
 322 |             from services.sentiment_tracker_service import SentimentTrackerService
 323 |             t = SentimentTrackerService()
 324 |             x = t.fetch_x_posts(hours_back=24)
 325 |             n = t.fetch_nostr_notes(hours_back=24)
 326 |             s = t.fetch_stacker_news(limit=15)
 327 |             t.save_signals_to_db(x + n + s)
 328 |             return {"success": True, "message": f"Signals collected: X={len(x)} Nostr={len(n)} Stacker={len(s)}", "result": None}
 329 |         except Exception as e:
 330 |             logger.warning("sarah_brief_prep: %s", e)
 331 |             return {"success": False, "message": str(e), "result": None}
 332 | 
 333 |     if name == "sarah_intelligence_briefing":
 334 |         try:
 335 |             from services.briefing_engine import briefing_engine
 336 |             article_id = briefing_engine.generate_daily_brief()
 337 |             return {"success": article_id is not None, "message": f"Brief article_id={article_id}", "result": {"article_id": article_id}}
 338 |         except Exception as e:
 339 |             logger.exception("sarah_intelligence_briefing failed: %s", e)
 340 |             return {"success": False, "message": str(e), "result": None}
 341 | 
 342 |     if name == "sentiment_buffer_update":
 343 |         try:
 344 |             from services.sentiment_service import sentiment_service
 345 |             result = sentiment_service.update_buffer()
 346 |             return {"success": True, "message": "Buffer updated", "result": result}
 347 |         except Exception as e:
 348 |             # sentiment_service may not exist yet
 349 |             logger.debug("sentiment_buffer_update: %s", e)
 350 |             return {"success": True, "message": "Sentiment service not configured", "result": None}
 351 | 
 352 |     if name == "emergency_flash_check":
 353 |         try:
 354 |             from services.briefing_engine import briefing_engine
 355 |             flash = briefing_engine.check_emergency_flash()
 356 |             return {"success": True, "message": "Flash checked", "result": flash}
 357 |         except Exception as e:
 358 |             logger.warning("emergency_flash_check: %s", e)
 359 |             return {"success": False, "message": str(e), "result": None}
 360 | 
 361 |     if name == "daily_distribution_brief_9am_est":
 362 |         try:
 363 |             from services.distribution_manager import distribution_manager
 364 |             result = distribution_manager.dispatch_daily_brief()
 365 |             return {"success": bool(result.get("success")), "message": "Daily distribution brief dispatch attempted", "result": result}
 366 |         except Exception as e:
 367 |             logger.warning("daily_distribution_brief_9am_est: %s", e)
 368 |             return {"success": False, "message": str(e), "result": None}
 369 | 
 370 |     if name == "daily_medley_gpu1":
 371 |         try:
 372 |             root = "/home/ultron/protocol_pulse"
 373 |             out = f"{root}/logs/medley_daily_beat.mp4"
 374 |             prog = f"{root}/logs/medley_daily_beat.progress"
 375 |             rep = f"{root}/logs/medley_daily_beat.report.json"
 376 |             env = os.environ.copy()
 377 |             env["CUDA_VISIBLE_DEVICES"] = "1"
 378 |             cmd = [
 379 |                 f"{root}/venv/bin/python",
 380 |                 f"{root}/medley_director.py",
 381 |                 "--output", out,
 382 |                 "--progress-file", prog,
 383 |                 "--report-file", rep,
 384 |                 "--duration", "60",
 385 |             ]
 386 |             proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
 387 |             ok = proc.returncode == 0
 388 |             return {
 389 |                 "success": ok,
 390 |                 "message": "Daily medley render attempted on GPU 1",
 391 |                 "result": {
 392 |                     "returncode": proc.returncode,
 393 |                     "output": out,
 394 |                     "report": rep,
 395 |                     "stderr_tail": (proc.stderr or "")[-300:],
 396 |                 },
 397 |             }
 398 |         except Exception as e:
 399 |             logger.warning("daily_medley_gpu1: %s", e)
 400 |             return {"success": False, "message": str(e), "result": None}
 401 | 
 402 |     if name == "monetization_injector":
 403 |         try:
 404 |             from app import app
 405 |             from services.monetization_engine import monetization_engine
 406 |             with app.app_context():
 407 |                 report = monetization_engine.run()
 408 |             return {"success": True, "message": "Monetization injector scan complete", "result": report}
 409 |         except Exception as e:
 410 |             logger.warning("monetization_injector: %s", e)
 411 |             return {"success": False, "message": str(e), "result": None}
 412 | 
 413 |     if name == "pulse_drop_rebuild_5am":
 414 |         try:
 415 |             from app import app
 416 |             from services.channel_monitor import channel_monitor_service
 417 |             from services.highlight_extractor import highlight_extractor_service
 418 |             from services.commentary_generator import commentary_generator_service
 419 |             with app.app_context():
 420 |                 h = channel_monitor_service.run_harvest(hours_back=24)
 421 |                 x = highlight_extractor_service.run(hours_back=24)
 422 |                 c = commentary_generator_service.run(hours_back=24)
 423 |             return {"success": True, "message": "Pulse Drop rebuild complete", "result": {"harvest": h, "extract": x, "commentary": c}}
 424 |         except Exception as e:
 425 |             logger.warning("pulse_drop_rebuild_5am: %s", e)
 426 |             return {"success": False, "message": str(e), "result": None}
 427 | 
 428 |     if name == "auto_viral_reel":
 429 |         return auto_viral_reel()
 430 | 
 431 |     if name == "intel_medley":
 432 |         return auto_viral_reel()
 433 | 
 434 |     if name in ("affiliate_education_morning", "affiliate_education_evening"):
 435 |         try:
 436 |             from app import app
 437 |             from services.affiliate_article_generator import affiliate_article_generator
 438 |             with app.app_context():
 439 |                 result = affiliate_article_generator.generate_affiliate_article()
 440 |             if result:
 441 |                 return {"success": True, "message": f"Affiliate article generated: {result.get('title', '')[:60]}", "result": result}
 442 |             return {"success": False, "message": "Affiliate article generation returned None (duplicate or AI failure)", "result": None}
 443 |         except Exception as e:
 444 |             logger.exception("affiliate_education task failed: %s", e)
 445 |             return {"success": False, "message": str(e), "result": None}
 446 | 
 447 |     # ─── F6 Marketing OS ─────────────────────────────────────────────────────
 448 | 
 449 |     if name == "btc_milestone_check":
 450 |         try:
 451 |             from app import app
 452 |             from services.price_service import PriceService
 453 |             from services.milestone_service import milestone_service
 454 |             with app.app_context():
 455 |                 price_svc = PriceService()
 456 |                 prices = price_svc.get_prices()
 457 |                 btc_price = prices.get("bitcoin", {}).get("price", 0)
 458 |                 if btc_price > 0:
 459 |                     fired = milestone_service.check_price(btc_price)
 460 |                     msg = f"Checked BTC ${btc_price:,.0f} — {len(fired)} milestone(s) fired"
 461 |                 else:
 462 |                     msg = "BTC price unavailable — skip milestone check"
 463 |             return {"success": True, "message": msg, "result": {"btc_price": btc_price, "fired_count": len(fired) if btc_price > 0 else 0}}
 464 |         except Exception as e:
 465 |             logger.warning("btc_milestone_check failed: %s", e)
 466 |             return {"success": False, "message": str(e), "result": None}
 467 | 
 468 |     if name == "daily_metrics_snapshot":
 469 |         try:
 470 |             from app import app, db
 471 |             from models import PerformanceMetrics
 472 |             from services.price_service import PriceService
 473 |             from datetime import date
 474 |             with app.app_context():
 475 |                 today = date.today()
 476 |                 metric = PerformanceMetrics.query.filter_by(metric_date=today).first()
 477 |                 if not metric:
 478 |                     metric = PerformanceMetrics(metric_date=today)
 479 |                     db.session.add(metric)
 480 |                 # Snapshot BTC close price
 481 |                 try:
 482 |                     prices = PriceService().get_prices()
 483 |                     btc = prices.get("bitcoin", {}).get("price", 0)
 484 |                     if btc > 0:
 485 |                         if metric.btc_price_open is None:
 486 |                             metric.btc_price_open = btc
 487 |                         metric.btc_price_close = btc
 488 |                 except Exception:
 489 |                     pass
 490 |                 db.session.commit()
 491 |             return {"success": True, "message": "Daily metrics snapshot updated", "result": {"date": str(today)}}
 492 |         except Exception as e:
 493 |             try:
 494 |                 from app import db
 495 |                 db.session.rollback()
 496 |             except Exception:
 497 |                 pass
 498 |             logger.warning("daily_metrics_snapshot failed: %s", e)
 499 |             return {"success": False, "message": str(e), "result": None}
 500 | 
 501 |     if name == "weekly_performance_analysis":
 502 |         try:
 503 |             from app import app
 504 |             from services.milestone_service import run_weekly_performance_analysis
 505 |             with app.app_context():
 506 |                 result = run_weekly_performance_analysis()
 507 |             return {"success": result.get("success", False), "message": "Weekly analysis complete", "result": result}
 508 |         except Exception as e:
 509 |             logger.warning("weekly_performance_analysis failed: %s", e)
 510 |             return {"success": False, "message": str(e), "result": None}
 511 | 
 512 |     return {"success": False, "message": f"Unknown task: {name}", "result": None}
 513 | 
 514 | 
 515 | def run_all_due() -> List[Dict]:
 516 |     """Run all tasks that are 'due' based on interval (simplified: run each once). For cron, prefer calling run_task per schedule."""
 517 |     results = []
 518 |     for task_name in TASKS:
 519 |         try:
 520 |             r = run_task(task_name)
 521 |             results.append({"task": task_name, **r})
 522 |         except Exception as e:
 523 |             results.append({"task": task_name, "success": False, "message": str(e), "result": None})
 524 |     return results
 525 | 
 526 | 
 527 | def initialize_scheduler() -> Dict:
 528 |     """
 529 |     Compatibility shim for admin command deck.
 530 |     We use systemd + endpoint-triggered tasks; this marks scheduler as active.
 531 |     """
 532 |     global _scheduler_started_at, _apscheduler
 533 |     from apscheduler.schedulers.background import BackgroundScheduler
 534 |     from apscheduler.triggers.cron import CronTrigger
 535 |     from apscheduler.triggers.interval import IntervalTrigger
 536 |     with _scheduler_lock:
 537 |         if _apscheduler and _apscheduler.running:
 538 |             return {"success": True, "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None, "already_running": True}
 539 | 
 540 |         _apscheduler = BackgroundScheduler(timezone="UTC")
 541 |         _apscheduler.add_job(lambda: run_task("x_engagement_cycle"), trigger=IntervalTrigger(minutes=5), id="x_engagement_cycle", replace_existing=True)
 542 |         _apscheduler.add_job(lambda: run_task("sentry_megaphone"), trigger=IntervalTrigger(minutes=2), id="sentry_megaphone", replace_existing=True)
 543 |         if ENABLE_ARTICLE_AUTOMATION_15M:
 544 |             _apscheduler.add_job(
 545 |                 lambda: run_task("article_generation_15m"),
 546 |                 trigger=IntervalTrigger(minutes=15),
 547 |                 id="article_generation_15m",
 548 |                 replace_existing=True,
 549 |                 max_instances=1,
 550 |             )
 551 |         if ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 552 |             _apscheduler.add_job(lambda: run_task("article_draft_burst_4"), trigger=IntervalTrigger(minutes=15), id="article_draft_burst_4", replace_existing=True)
 553 |             _apscheduler.add_job(lambda: run_task("article_draft_hourly_1"), trigger=IntervalTrigger(minutes=60), id="article_draft_hourly_1", replace_existing=True)
 554 |         else:
 555 |             _apscheduler.add_job(lambda: run_task("cypherpunk_loop"), trigger=IntervalTrigger(minutes=120), id="cypherpunk_loop", replace_existing=True)
 556 |         _apscheduler.add_job(lambda: run_task("mining_snapshot_hourly"), trigger=IntervalTrigger(hours=1), id="mining_snapshot_hourly", replace_existing=True)
 557 |         _apscheduler.add_job(lambda: run_task("daily_medley_gpu1"), trigger=CronTrigger(hour=23, minute=0), id="daily_medley_gpu1", replace_existing=True)
 558 |         _apscheduler.add_job(lambda: run_task("monetization_injector"), trigger=IntervalTrigger(minutes=30), id="monetization_injector", replace_existing=True)
 559 |         _apscheduler.add_job(lambda: run_task("pulse_drop_rebuild_5am"), trigger=CronTrigger(hour=10, minute=0), id="pulse_drop_rebuild_5am", replace_existing=True)
 560 |         _apscheduler.add_job(lambda: run_task("auto_viral_reel"), trigger=IntervalTrigger(minutes=30), id="auto_viral_reel", replace_existing=True)
 561 |         _apscheduler.add_job(lambda: run_task("intel_medley"), trigger=IntervalTrigger(minutes=60), id="intel_medley", replace_existing=True)
 562 |         _apscheduler.add_job(lambda: run_task("affiliate_education_morning"), trigger=CronTrigger(hour=11, minute=0), id="affiliate_education_morning", replace_existing=True, max_instances=1)
 563 |         _apscheduler.add_job(lambda: run_task("affiliate_education_evening"), trigger=CronTrigger(hour=21, minute=0), id="affiliate_education_evening", replace_existing=True, max_instances=1)
 564 |         # F6 Marketing OS jobs
 565 |         _apscheduler.add_job(lambda: run_task("btc_milestone_check"), trigger=IntervalTrigger(minutes=5), id="btc_milestone_check", replace_existing=True, max_instances=1)
 566 |         _apscheduler.add_job(lambda: run_task("daily_metrics_snapshot"), trigger=IntervalTrigger(hours=1), id="daily_metrics_snapshot", replace_existing=True, max_instances=1)
 567 |         _apscheduler.add_job(lambda: run_task("weekly_performance_analysis"), trigger=CronTrigger(day_of_week="sun", hour=0, minute=0), id="weekly_performance_analysis", replace_existing=True, max_instances=1)
 568 |         _apscheduler.start()
 569 |         _scheduler_started_at = datetime.utcnow()
 570 |     return {"success": True, "started_at": _scheduler_started_at.isoformat(), "mode": "apscheduler"}
 571 | 
 572 | 
 573 | def get_scheduler_status() -> Dict:
 574 |     """Compatibility status payload expected by command deck UI."""
 575 |     jobs = [{"name": name, **meta} for name, meta in TASKS.items()]
 576 |     return {
 577 |         "running": bool(_apscheduler and _apscheduler.running),
 578 |         "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None,
 579 |         "jobs": jobs,
 580 |         "mode": "apscheduler+systemd",
 581 |     }
 582 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
