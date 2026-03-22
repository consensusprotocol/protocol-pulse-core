# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: f5-node-watch
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
{
  "reviewer": "GPT-4o",
  "timestamp": "2026-03-09T03:00:00Z",
  "feature": "f5-node-watch",
  "branch": "feature/f5-node-watch",

  "section_1_correctness": {
    "main_user_flow": {
      "description": "The feature polls Bitnodes API every 15 minutes via cron (cron/node_watch_cron.py), stores node count snapshots in the database (models.py:941-964), checks for alert thresholds (cron/node_watch_cron.py:96-155), and saves alerts if triggered. The flow is logically sound for data collection and storage.",
      "issues": [
        {
          "type": "Logic Error",
          "file": "cron/node_watch_cron.py",
          "line": 106-113,
          "description": "ATH alert check uses a query to find the historical maximum node count, but if the database is empty or the first snapshot is being added, this could fail silently or return incorrect results. It assumes a previous record exists without fallback."
        },
        {
          "type": "Race Condition",
          "file": "cron/node_watch_cron.py",
          "line": 102-104,
          "description": "Multiple cron instances running concurrently could query the same 'previous' snapshot and trigger duplicate alerts since there's no locking mechanism or transaction isolation for alert checks."
        },
        {
          "type": "Edge Case",
          "file": "cron/node_watch_cron.py",
          "line": 59-66,
          "description": "If Bitnodes API returns zero nodes or empty results, the script raises an error and exits without a fallback or retry mechanism, potentially missing snapshots during temporary API outages."
        }
      ]
    }
  },

  "section_2_law_compliance": {
    "law_1": {
      "status": "COMPLIANT",
      "note": "The feature does not involve browser-side requests to Bitnodes. All API calls are made server-side via cron/node_watch_cron.py:49-54, adhering to the proxy endpoint law."
    },
    "law_2": {
      "status": "COMPLIANT",
      "note": "Alert thresholds are implemented as specified in cron/node_watch_cron.py:106-155, with edge-triggered logic to prevent repeated alerts (e.g., lines 135-137 for daily delta and 151-153 for weekly drop). All conditions (±500 daily, ATH, milestones, -1000 weekly) are covered."
    },
    "law_3": {
      "status": "COMPLIANT",
      "note": "Polling is handled via cron every 15 minutes as per cron/node_watch_cron.py:7-8, storing snapshots in node_snapshots table (models.py:941-964), and alert checks run post-snapshot (cron/node_watch_cron.py:185-189)."
    }
  },

  "section_3_security": {
    "issues": [
      {
        "type": "Rate Limiting Gap",
        "file": "cron/node_watch_cron.py",
        "line": 49-54,
        "description": "No rate limiting or backoff mechanism for Bitnodes API calls. If the API imposes limits or temporary bans, the cron job will fail repeatedly without mitigation."
      },
      {
        "type": "Unvalidated Input",
        "file": "cron/node_watch_cron.py",
        "line": 57-84,
        "description": "API response data from Bitnodes is not fully validated before processing. Malformed or malicious data could cause parsing errors or unexpected behavior, though it doesn't reach DB directly without sanitization."
      }
    ],
    "note": "No SQL injection risks as no raw queries or user input are involved. No hardcoded secrets found. Authentication bypass not applicable as this is a cron job."
  },

  "section_4_frontend_quality": {
    "assessment": "Not applicable in full as no frontend code is provided for this feature in the submitted files. Assuming a UI exists to display node counts and alerts, the following gaps are inferred from the backend structure.",
    "issues": [
      {
        "type": "Missing States",
        "file": "N/A",
        "description": "No evidence of loading/error/empty states for node data display in the provided code. If the UI fetches data from an API endpoint, these states must be handled."
      },
      {
        "type": "World-Class Gap",
        "file": "N/A",
        "description": "Without frontend code, it's unclear if the UI matches a professional layout or provides mobile responsiveness. A world-class product would need real-time node count updates with visualizations (e.g., charts over time)."
      }
    ]
  },

  "section_5_backend_quality": {
    "issues": [
      {
        "type": "Error Handling",
        "file": "cron/node_watch_cron.py",
        "line": 162-166",
        "description": "Bitnodes API fetch has basic error handling with try/except, but no retry logic or graceful degradation. A single failure stops the entire process."
      },
      {
        "type": "DB Operation",
        "file": "cron/node_watch_cron.py",
        "line": 205-212",
        "description": "DB write operation includes rollback on failure, which is good. However, no retry mechanism if the DB is temporarily unavailable."
      },
      {
        "type": "Logging",
        "file": "cron/node_watch_cron.py",
        "line"

## GEMINI — CYCLE 1 OUTPUT
Here is the full code audit for the `f5-node-watch` feature.

### SECTION 1: CORRECTNESS

The code's primary logic resides in `cron/node_watch_cron.py`. It correctly polls an external API, parses the data, and stores it. However, there are subtle but significant logic errors in the alerting mechanism.

-   **Logic Error (Alerts):** The "edge-triggered" alert logic in `check_alerts` (`node_watch_cron.py:96-155`) is flawed. It prevents re-firing an alert only if the *immediately preceding* snapshot had an alert of the *same type*. For example, `node_watch_cron.py:135-136` checks if `prev.alert_fired` starts with `NETWORK CHANGE:`.
    -   **Scenario 1:** Node count fluctuates across the threshold. Day 1: +501 (fires alert). Day 2: +499 (no alert). Day 3: +502 (fires alert again). This violates the "fire once per crossing" spirit of LAW 2.
    -   **Scenario 2:** Two different alert conditions are met back-to-back. Snapshot A meets the daily threshold and fires a "NETWORK CHANGE" alert. The very next snapshot (15 mins later) still meets the daily threshold, but also crosses a milestone. The milestone alert will fire, and the snapshot after *that* could fire the "NETWORK CHANGE" alert again, because the preceding alert was "MILESTONE", not "NETWORK CHANGE". The code should track the active *state* of an alert, not just the last fired event.

-   **N+1 Query Problems:** No N+1 query issues were found. The `check_alerts` function performs four separate queries, but none are inside a loop. The queries are efficient, using `first()` and `limit()`.

-   **Edge Cases:**
    -   **Empty DB:** The code correctly handles an empty `node_snapshots` table. `node_watch_cron.py:102` checks `if prev` and initializes `prev_count` to 0, which is robust.
    -   **API Failure:** The `fetch_bitnodes_snapshot` function includes a request timeout (`node_watch_cron.py:33`) and checks the HTTP status code (`node_watch_cron.py:54`). The main function wraps the call in a `try/except` block (`node_watch_cron.py:162`), logging the error and exiting gracefully. This is well-handled.
    -   **Unexpected API Data:** The parsing logic in `fetch_bitnodes_snapshot` uses `.get()` and checks for an empty `results` list (`node_watch_cron.py:58`), which provides good protection against malformed API responses.

### SECTION 2: LAW COMPLIANCE

-   **LAW 1: Proxy endpoints only — never hit Bitnodes from the browser**
    -   **Status: VIOLATION**
    -   The cron job at `cron/node_watch_cron.py:49` hits the Bitnodes API directly (`BITNODES_SNAPSHOT_URL = 'https://bitnodes.io/api/v1/snapshots/?limit=1'`). While this is not a browser request, it violates the architectural principle of the law, which is to centralize all external Bitnodes API calls through a single, cacheable proxy layer within the Flask application. This cron job should be calling an internal `/api/proxy/bitnodes/snapshot` endpoint instead of the public URL.

-   **LAW 2: Alert thresholds (fire once per crossing, not every poll)**
    -   **Status: PARTIAL VIOLATION**
    -   The implementation attempts to be edge-triggered (`node_watch_cron.py:135-136`, `151-152`) but is flawed, as detailed in Section 1. It can re-fire alerts under common scenarios, violating the "fire once per crossing" requirement. It only prevents firing if the immediately preceding record had the exact same alert type.

-   **LAW 3: Poll every 15 minutes via cron, not per-request**
    -   **Status: COMPLIANT**
    -   The feature is implemented entirely within `cron/node_watch_cron.py`, and the file header includes the correct crontab entry (`*/15 * * * * ...`) to run every 15 minutes. The database model `NodeSnapshot` is designed to store these periodic snapshots.

### SECTION 3: SECURITY

-   **SQL Injection:** No vulnerabilities found. All database interactions use the SQLAlchemy ORM, which properly sanitizes inputs. No raw SQL is used.
-   **Authentication Bypasses:** Not applicable. The code being audited is a cron job and does not expose any web routes.
-   **Rate Limiting Gaps:** Not applicable to this cron job.
-   **Secrets in Code:** No secrets are hardcoded. The application correctly loads secrets from a `.env` file (`app.py:5`).
-   **Unvalidated User Input:** The input from the Bitnodes API is treated as untrusted. The parsing logic in `fetch_bitnodes_snapshot` is defensive and does not introduce vulnerabilities.

The security posture of the submitted code is excellent.

### SECTION 4: FRONTEND QUALITY

No frontend files were provided for this feature. A review of frontend quality is not possible.

### SECTION 5: BACKEND QUALITY

-   **DB Operations:** Excellent. Every database write operation in `node_watch_cron.py` (`206-212`) is wrapped in a `try/except` block, and `db.session.rollback()` is correctly called on failure. This ensures data integrity.
-   **External API Calls:** Very good. All external calls in `fetch_bitnodes_snapshot` include a timeout (`node_watch_cron.py:51`) and status code che

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

Main flow for **f5-node-watch** appears to be:

1. Cron runs every 15 minutes.
2. Cron fetches Bitnodes snapshot.
3. Cron computes alerts from historical snapshots.
4. Cron stores a new `NodeSnapshot`.
5. Presumably frontend/API later reads from DB or proxy endpoints.

### What works
- `NodeSnapshot` model exists with indexes on `timestamp` and `node_count` (`core/models.py:941-956`).
- Cron fetch has a timeout (`cron/node_watch_cron.py:49-53`).
- Cron stores a snapshot and rolls back on DB write failure (`cron/node_watch_cron.py:194-213`).
- Empty Bitnodes response and zero-node outage are explicitly rejected (`cron/node_watch_cron.py:57-65`).

### Major correctness issues

#### 1) Alert logic does **not** fully implement the spec wording
- Spec requires:
  - `±500 nodes from yesterday's count → "Network change alert"`
  - `New all-time high → "ATH ALERT: Bitcoin nodes hit [N]"`
  - `Round milestones (20000, 25000, etc.) → milestone celebration`
  - `-1000 over 7 days → "Network contraction warning"`
- Actual strings differ:
  - `"NETWORK CHANGE: {:,} node {} vs 24hr ago"` (`cron/node_watch_cron.py:133`)
  - `"MILESTONE: Bitcoin nodes crossed {:,}"` (`cron/node_watch_cron.py:119`)
  - `"CONTRACTION WARNING: -{:,} nodes over 7 days"` (`cron/node_watch_cron.py:150`)
- This is not just cosmetic if downstream UI/tests/keying depend on exact alert classes/messages.

#### 2) “Fire once per crossing” is only partially implemented
- Daily and weekly alerts suppress repeats only if the **immediately previous snapshot** had the same prefix (`cron/node_watch_cron.py:134-136`, `151-152`).
- That means if counts remain above threshold, then an ATH or milestone fires in between, the next poll can re-fire the daily/weekly alert even though no new threshold crossing occurred.
- This violates the “once per crossing, not every poll” law. True edge-triggering requires comparing previous state vs current state, not just previous alert text.

#### 3) Milestone logic is too broad and may celebrate wrong thresholds
- `MILESTONE_STEP = 5000` (`cron/node_watch_cron.py:38`)
- Law examples are `20000, 25000, etc.` which implies 5k steps starting at 20k, but current logic would also celebrate 5k, 10k, 15k if historical data ever crosses them (`cron/node_watch_cron.py:115-119`).
- If product intent is only meaningful modern milestones, this is off-spec.

#### 4) Alert precedence may suppress more important alerts
- ATH is checked first, then milestone, then daily, then weekly (`cron/node_watch_cron.py:105-154`).
- Only one `alert_fired` string can be stored (`core/models.py:954-955`).
- If a snapshot simultaneously triggers ATH + milestone + daily delta, only ATH is retained.
- That may be acceptable if intentional, but the feature description suggests multiple alert classes matter. There is no evidence of explicit prioritization in the spec.

#### 5) Snapshot timestamp ignores upstream timestamp
- Fetched payload includes Bitnodes timestamp (`cron/node_watch_cron.py:87`), but stored row uses `datetime.utcnow()` instead (`cron/node_watch_cron.py:197`).
- This can skew “yesterday” and “7 days ago” comparisons if cron is delayed or Bitnodes snapshot time lags/leads.
- Since alert logic is based on stored timestamps, this introduces drift over time.

#### 6) Potentially huge payload assumption may be wrong for `limit=1`
- Code expects `snap.get('nodes', {})` to contain full node map (`cron/node_watch_cron.py:61-84`).
- If Bitnodes snapshot endpoint returns summary-only data or paginated/trimmed node details, `versions/countries/ipv4/ipv6` may silently be incomplete while `total_nodes` remains large.
- No validation exists to detect mismatch between `total_nodes` and parsed `nodes`.

### App/model integration issues

#### 7) `db.create_all()` at app startup is risky in production
- `app.py:238-247` runs `db.create_all()` on startup by default.
- This is not a correctness bug for node watch specifically, but it creates schema drift risk and masks migration problems.

#### 8) `load_user` uses legacy query API
- `app.py:222-225` uses `models.User.query.get(int(user_id))`.
- Not a production breaker, but dated and can emit warnings under newer SQLAlchemy patterns.

### N+1 / query efficiency
No obvious N+1 in the node-watch path. Alert logic does 3 small indexed queries per cron run:
- latest snapshot by timestamp
- max node_count
- latest snapshot before yesterday
- latest snapshot before week ago

Given indexes on `timestamp` and `node_count`, this is acceptable.

---

## SECTION 2: LAW COMPLIANCE

### LAW 1: Proxy endpoints only — never hit Bitnodes from the browser
**PARTIAL**

- I see no browser JS here hitting Bitnodes directly, so no direct violation is visible in provided files.
- But the required proxy endpoints are not implemented in the provided code:
  - `/api/proxy/bitnodes/snapshot`
  - `/api/proxy/bitnodes/history`
- Cron directly hits Bitnodes server-side, which is fine.
- Missing evidence of require

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — F5-NODE-WATCH — CYCLE 1
Generated: 2026-03-09 02:36
Models: Grok-3, Gemini 2.5 Pro, GPT-4o

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Backend Logic   | 70     | ~65*   | 80   | **72**    |
| Frontend/UI     | N/A    | N/A    | 0†   | **N/A**   |
| Error Handling  | 95     | ~70*   | 60   | **75**    |
| Security        | 100    | ~70*   | 85   | **85**    |
| Performance     | 90     | ~85*   | 75   | **83**    |
| Law Compliance  | 40     | ~50*   | 100  | **63**    |
| World-Class Gap | N/A    | N/A    | 40   | **40**    |
| **Overall**     | —      | —      | 63   | **65**    |

> *GPT-4o did not emit a numeric score table; values are synthesized from its written assessments.
> †Grok scored frontend 0 due to absence of submitted frontend files, not a quality failure.
> **Synthesizer note:** Grok scored Law Compliance 100 — this is an outlier and an error in Grok's own output (its reviewer field says "GPT-4o", suggesting a metadata mix-up). Gemini's 40 and GPT-4o's ~50 are better calibrated given the clear violations found.

---

## UNANIMOUS FINDINGS
*All 3 models agree — implement unconditionally.*

---

### U1 — "Fire once per crossing" alert logic is broken
**File:** `cron/node_watch_cron.py:134-136, 151-152`

**What it is:** All three models independently identified that the edge-trigger suppression only checks whether the *immediately preceding snapshot* carried the same alert prefix. This means:
- If an ATH or milestone fires between two daily-threshold breaches, the daily alert re-fires on the third snapshot even though the node count never re-crossed the threshold.
- Any oscillation around a threshold (e.g., +501, +499, +503 over three polls) fires the alert on polls 1 and 3, violating "fire once per crossing."

**What to change:** Replace the "did the last snapshot have this prefix?" check with a proper **stateful threshold tracker**. Store the node count at which each alert *type* last fired (or a boolean `alert_active` per type) in the DB or a dedicated `AlertState` table. An alert fires only when transitioning from "not triggered" → "triggered." It resets only when the condition clears — i.e., the metric returns to the non-alert side of the threshold.

**Concrete approach:**
```python
# New DB columns or a separate AlertState model:
# daily_alert_active: bool, daily_alert_baseline: int
# weekly_alert_active: bool, ath_alert_active: bool, milestone_last_crossed: int

# Logic change for daily delta:
currently_above_threshold = abs(delta_24h) >= 500
was_above_threshold = prev_snapshot.daily_alert_active  # read from DB

if currently_above_threshold and not was_above_threshold:
    alert_fired = f"NETWORK CHANGE: ..."  # fire
elif not currently_above_threshold:
    current_snapshot.daily_alert_active = False  # reset state
```

---

### U2 — No retry / backoff on Bitnodes API failure
**File:** `cron/node_watch_cron.py:49-66`



---

## ORIGINAL CODE (same code as Cycle 1)
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

### File: core/models.py (965 lines)
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
 910 | class CollectedSignal(db.Model):
 911 |     __tablename__ = 'collected_signal'
 912 |     id = db.Column(db.Integer, primary_key=True)
 913 |     platform = db.Column(db.String(20), nullable=False)
 914 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
 915 |     author_name = db.Column(db.String(200), nullable=False)
 916 |     author_handle = db.Column(db.String(100), nullable=False)
 917 |     author_tier = db.Column(db.String(50), default='general')
 918 |     content = db.Column(db.Text, nullable=False)
 919 |     url = db.Column(db.String(500), nullable=False)
 920 |     engagement_likes = db.Column(db.Integer, default=0)
 921 |     engagement_reposts = db.Column(db.Integer, default=0)
 922 |     engagement_replies = db.Column(db.Integer, default=0)
 923 |     engagement_score = db.Column(db.Float, default=0.0)
 924 |     sentiment = db.Column(db.String(20))
 925 |     sentiment_score = db.Column(db.Float)
 926 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
 927 |     posted_at = db.Column(db.DateTime)
 928 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
 929 |     is_verified = db.Column(db.Boolean, default=True)
 930 |     is_legendary = db.Column(db.Boolean, default=False)
 931 |     __table_args__ = (
 932 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
 933 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
 934 |     )
 935 | 
 936 | 
 937 | # =====================================
 938 | # NODE WATCH
 939 | # =====================================
 940 | 
 941 | class NodeSnapshot(db.Model):
 942 |     """Bitcoin network node count snapshot — polled every 15 min via cron."""
 943 |     __tablename__ = 'node_snapshots'
 944 |     __table_args__ = (
 945 |         db.Index('idx_node_snapshots_timestamp', 'timestamp'),
 946 |         db.Index('idx_node_snapshots_node_count', 'node_count'),
 947 |     )
 948 | 
 949 |     id = db.Column(db.Integer, primary_key=True)
 950 |     node_count = db.Column(db.Integer, nullable=False)
 951 |     timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
 952 |     # JSON blob: {versions: {...}, countries: {...}, ipv4: N, ipv6: N}
 953 |     snapshot_data = db.Column(db.Text)
 954 |     # NULL = no alert; otherwise the alert type string
 955 |     alert_fired = db.Column(db.String(120))
 956 | 
 957 |     def to_dict(self):
 958 |         return {
 959 |             'id': self.id,
 960 |             'node_count': self.node_count,
 961 |             'timestamp': self.timestamp.isoformat(),
 962 |             'alert_fired': self.alert_fired,
 963 |         }
 964 | 
 965 | 
```

### File: cron/node_watch_cron.py (218 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Protocol Pulse — Bitcoin Node Watch Cron
   4 | Polls Bitnodes API every 15 minutes, stores snapshot, fires threshold alerts.
   5 | 
   6 | Crontab:
   7 |     */15 * * * * /usr/bin/python3 /home/ultron/protocol_pulse/cron/node_watch_cron.py >> /var/log/node_watch.log 2>&1
   8 | """
   9 | 
  10 | import sys
  11 | import os
  12 | import json
  13 | import logging
  14 | import requests
  15 | from datetime import datetime, timedelta
  16 | 
  17 | # ── Project root ──────────────────────────────────────────────────────────────
  18 | _CRON_DIR    = os.path.dirname(os.path.abspath(__file__))
  19 | _PROJECT_DIR = os.path.dirname(_CRON_DIR)
  20 | sys.path.insert(0, _PROJECT_DIR)
  21 | sys.path.insert(0, os.path.join(_PROJECT_DIR, 'core'))
  22 | 
  23 | # ── Logging ───────────────────────────────────────────────────────────────────
  24 | logging.basicConfig(
  25 |     level=logging.INFO,
  26 |     format='%(asctime)s [node_watch] %(levelname)s %(message)s',
  27 |     datefmt='%Y-%m-%dT%H:%M:%SZ',
  28 | )
  29 | log = logging.getLogger('node_watch')
  30 | 
  31 | # ── Constants ─────────────────────────────────────────────────────────────────
  32 | BITNODES_SNAPSHOT_URL = 'https://bitnodes.io/api/v1/snapshots/?limit=1'
  33 | REQUEST_TIMEOUT       = 15  # seconds
  34 | 
  35 | # Alert thresholds
  36 | ALERT_DAILY_DELTA  = 500   # ±500 nodes vs yesterday
  37 | ALERT_WEEKLY_DROP  = 1000  # -1000 over 7 days
  38 | MILESTONE_STEP     = 5000  # 20k, 25k, 30k …
  39 | 
  40 | 
  41 | # ── Bitnodes fetch ────────────────────────────────────────────────────────────
  42 | def fetch_bitnodes_snapshot():
  43 |     """
  44 |     Returns:
  45 |         {'node_count': int, 'timestamp': int, 'versions': dict,
  46 |          'countries': dict, 'ipv4': int, 'ipv6': int}
  47 |     Raises on failure.
  48 |     """
  49 |     r = requests.get(
  50 |         BITNODES_SNAPSHOT_URL,
  51 |         timeout=REQUEST_TIMEOUT,
  52 |         headers={'Accept': 'application/json'},
  53 |     )
  54 |     r.raise_for_status()
  55 |     raw = r.json()
  56 | 
  57 |     results = raw.get('results', [])
  58 |     if not results:
  59 |         raise ValueError('Bitnodes returned empty results')
  60 | 
  61 |     snap  = results[0]
  62 |     nodes = snap.get('nodes', {})
  63 |     total = snap.get('total_nodes') or len(nodes)
  64 |     if total == 0:
  65 |         raise ValueError('Node count is zero — likely API outage')
  66 | 
  67 |     versions: dict  = {}
  68 |     countries: dict = {}
  69 |     ipv4 = 0
  70 |     ipv6 = 0
  71 | 
  72 |     for addr, info in nodes.items():
  73 |         if not isinstance(info, list):
  74 |             continue
  75 |         ver     = info[1] if len(info) > 1 else 'unknown'
  76 |         country = info[7] if len(info) > 7 else None
  77 |         versions[ver] = versions.get(ver, 0) + 1
  78 |         if country:
  79 |             countries[country] = countries.get(country, 0) + 1
  80 |         if addr.startswith('['):
  81 |             ipv6 += 1
  82 |         else:
  83 |             ipv4 += 1
  84 | 
  85 |     return {
  86 |         'node_count': total,
  87 |         'timestamp':  snap.get('timestamp', 0),
  88 |         'versions':   dict(sorted(versions.items(),  key=lambda x: x[1], reverse=True)[:20]),
  89 |         'countries':  dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:30]),
  90 |         'ipv4': ipv4,
  91 |         'ipv6': ipv6,
  92 |     }
  93 | 
  94 | 
  95 | # ── Alert logic (edge-triggered) ──────────────────────────────────────────────
  96 | def check_alerts(NodeSnapshot, new_count):
  97 |     """
  98 |     Returns alert_type string or None.
  99 |     Edge-triggered: does NOT re-fire if the same alert already appears on the
 100 |     most recent snapshot.
 101 |     """
 102 |     prev = NodeSnapshot.query.order_by(NodeSnapshot.timestamp.desc()).first()
 103 |     prev_count = prev.node_count if prev else 0
 104 | 
 105 |     # ATH
 106 |     ath = (
 107 |         NodeSnapshot.query
 108 |         .order_by(NodeSnapshot.node_count.desc())
 109 |         .with_entities(NodeSnapshot.node_count)
 110 |         .first()
 111 |     )
 112 |     if ath and new_count > ath[0]:
 113 |         return 'ATH ALERT: Bitcoin nodes hit {:,}'.format(new_count)
 114 | 
 115 |     # Milestone (crossed a MILESTONE_STEP boundary since last snapshot)
 116 |     prev_ms = (prev_count // MILESTONE_STEP) * MILESTONE_STEP
 117 |     cur_ms  = (new_count  // MILESTONE_STEP) * MILESTONE_STEP
 118 |     if cur_ms > prev_ms and new_count >= cur_ms and cur_ms > 0:
 119 |         return 'MILESTONE: Bitcoin nodes crossed {:,}'.format(cur_ms)
 120 | 
 121 |     # Daily ±500
 122 |     yesterday = datetime.utcnow() - timedelta(hours=24)
 123 |     day_snap = (
 124 |         NodeSnapshot.query
 125 |         .filter(NodeSnapshot.timestamp <= yesterday)
 126 |         .order_by(NodeSnapshot.timestamp.desc())
 127 |         .first()
 128 |     )
 129 |     if day_snap:
 130 |         delta = new_count - day_snap.node_count
 131 |         if abs(delta) >= ALERT_DAILY_DELTA:
 132 |             direction = 'surge' if delta > 0 else 'drop'
 133 |             alert = 'NETWORK CHANGE: {:,} node {} vs 24hr ago'.format(abs(delta), direction)
 134 |             # Edge: skip if previous snapshot already has same type
 135 |             if prev and prev.alert_fired and prev.alert_fired.startswith('NETWORK CHANGE:'):
 136 |                 return None
 137 |             return alert
 138 | 
 139 |     # Weekly -1000
 140 |     week_ago = datetime.utcnow() - timedelta(days=7)
 141 |     week_snap = (
 142 |         NodeSnapshot.query
 143 |         .filter(NodeSnapshot.timestamp <= week_ago)
 144 |         .order_by(NodeSnapshot.timestamp.desc())
 145 |         .first()
 146 |     )
 147 |     if week_snap:
 148 |         weekly_delta = new_count - week_snap.node_count
 149 |         if weekly_delta <= -ALERT_WEEKLY_DROP:
 150 |             alert = 'CONTRACTION WARNING: -{:,} nodes over 7 days'.format(abs(weekly_delta))
 151 |             if prev and prev.alert_fired and prev.alert_fired.startswith('CONTRACTION WARNING:'):
 152 |                 return None
 153 |             return alert
 154 | 
 155 |     return None
 156 | 
 157 | 
 158 | # ── Main ──────────────────────────────────────────────────────────────────────
 159 | def main():
 160 |     log.info('node_watch_cron starting')
 161 | 
 162 |     try:
 163 |         data = fetch_bitnodes_snapshot()
 164 |     except Exception as e:
 165 |         log.error('Bitnodes fetch failed: %s', e)
 166 |         sys.exit(1)
 167 | 
 168 |     log.info('Bitnodes OK — %d nodes', data['node_count'])
 169 | 
 170 |     try:
 171 |         os.environ.setdefault('FLASK_ENV', 'production')
 172 |         from app import app, db
 173 |         import models
 174 |         NodeSnapshot = models.NodeSnapshot
 175 |     except Exception as e:
 176 |         log.error('App boot failed: %s', e)
 177 |         sys.exit(1)
 178 | 
 179 |     with app.app_context():
 180 |         try:
 181 |             db.create_all()
 182 |         except Exception as e:
 183 |             log.warning('db.create_all: %s', e)
 184 | 
 185 |         try:
 186 |             alert = check_alerts(NodeSnapshot, data['node_count'])
 187 |         except Exception as e:
 188 |             log.warning('Alert check error: %s', e)
 189 |             alert = None
 190 | 
 191 |         if alert:
 192 |             log.warning('ALERT: %s', alert)
 193 | 
 194 |         try:
 195 |             snap = NodeSnapshot(
 196 |                 node_count=data['node_count'],
 197 |                 timestamp=datetime.utcnow(),
 198 |                 snapshot_data=json.dumps({
 199 |                     'versions':  data['versions'],
 200 |                     'countries': data['countries'],
 201 |                     'ipv4':      data['ipv4'],
 202 |                     'ipv6':      data['ipv6'],
 203 |                 }),
 204 |                 alert_fired=alert,
 205 |             )
 206 |             db.session.add(snap)
 207 |             db.session.commit()
 208 |             log.info('Snapshot saved — id=%d count=%d alert=%s',
 209 |                      snap.id, snap.node_count, alert or 'none')
 210 |         except Exception as e:
 211 |             db.session.rollback()
 212 |             log.error('DB write failed: %s', e)
 213 |             sys.exit(1)
 214 | 
 215 | 
 216 | if __name__ == '__main__':
 217 |     main()
 218 | 
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
