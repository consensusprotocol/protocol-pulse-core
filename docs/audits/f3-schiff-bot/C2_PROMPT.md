# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: f3-schiff-bot
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
{
  "review": {
    "section_1_correctness": {
      "main_user_flow": {
        "description": "The main user flow for the Schiff-Bot involves fetching SEC EDGAR data, calculating the Hypocrisy Score, and displaying it on the /schiff or /brian page with historical data and statements. The code in schiff_service.py handles data fetching (lines 145-181), parsing (lines 274-325), score calculation (lines 525-547), and persistence (lines 687-710). However, there are several correctness issues that could disrupt this flow.",
        "issues": [
          {
            "logic_error": "In schiff_service.py line 339, the gold price cache duration is 4 hours (14400 seconds), but BTC price cache is only 15 minutes (900 seconds). This mismatch could lead to inconsistent YTD performance calculations if gold price is stale while BTC updates frequently, skewing the gold_vs_btc_perf_gap component.",
            "impact": "Incorrect Hypocrisy Score due to price data inconsistency."
          },
          {
            "silent_failure": "In schiff_service.py lines 390-408, if both BTC price APIs fail, a hardcoded fallback of $85,000 is used without any alert or logging of the fallback usage beyond a warning. This could silently produce outdated scores for days.",
            "impact": "Users see outdated or incorrect data without knowing it's a fallback."
          },
          {
            "race_condition": "In schiff_service.py lines 131-140, the in-memory cache (_cache) is used without any locking mechanism. Concurrent requests during an update_score() call could read partially updated cache states, leading to inconsistent data being served.",
            "impact": "Users may see inconsistent or corrupted score data during updates."
          },
          {
            "edge_case": "In schiff_service.py line 519, if the database is empty or inaccessible, _count_anti_btc_statements() falls back to a hardcoded value of 10 without checking if this is reasonable based on historical data or logging the fallback. An empty DB on first run would overestimate anti-BTC sentiment.",
            "impact": "Score is skewed high on initial deployment or DB failure."
          }
        ]
      }
    },
    "section_2_law_compliance": {
      "law_1_data_sources": {
        "status": "COMPLIANT",
        "note": "Data is sourced exclusively from SEC EDGAR API as seen in schiff_service.py lines 145-181, using public endpoints with no speculation or invented data. Fallbacks use cached data or synthetic values only when EDGAR is down (lines 723-733), adhering to serving last cached data if under 7 days old."
      },
      "law_2_hypocrisy_formula": {
        "status": "COMPLIANT",
        "note": "The Hypocrisy Score formula is implemented exactly as specified in schiff_service.py lines 525-547, with no deviations from the defined weights (0.35, 0.30, 0.20, 0.15) and normalization to 0-100."
      },
      "law_3_brian_persona": {
        "status": "PARTIAL",
        "note": "There is no explicit mention of Brian's tone or persona in the provided code or templates (e.g., schiff_service.py or app.py). While the code avoids personal attacks by focusing on data, the tone (dry, analytical, slightly amused) is not enforced or visible in any output string or comment, leaving room for deviation in UI rendering not shown here."
      },
      "law_4_edgar_api": {
        "status": "COMPLIANT",
        "note": "EDGAR API rate limits are respected with a 250ms delay between calls (schiff_service.py line 148), exceeding the required 200ms. The User-Agent header is correctly set to 'Protocol Pulse contact@protocolpulse.io' (line 25 and used in lines 150, 172)."
      },
      "law_5_cache_aggressively": {
        "status": "PARTIAL",
        "note": "Caching for 13F filings is implemented with a 24-hour minimum in schiff_service.py lines 756-757, and score recalculation is daily (cron/schiff_cron.py). However, there is no explicit check to prevent hitting EDGAR more than once per hour for the same filing (lines 617-620 rely on cache but don't enforce hourly limit explicitly), risking accidental over-fetching if cache is invalidated."
      }
    },
    "section_3_security": {
      "issues": [
        {
          "in_memory_cache": "schiff_service.py lines 131-140 use an in-memory cache without access control or sanitization. If multiple processes or threads access this, there's a risk of data corruption or leakage of stale data to unauthorized users.",
          "impact": "Potential for inconsistent data exposure or race condition exploits."
        },
        {
          "no_rate_limiting_on_api": "There is no rate limiting on the Flask routes that trigger EDGAR fetches or score updates (app.py does have general rate limiting at lines 96-97, but it's not specific to EDGAR calls). A malicious user could spam requests to update_score(), exhausting server resources or hitting EDGAR limits.",
          "impact": "Service degradation or IP ban from E

## GEMINI — CYCLE 1 OUTPUT
An exhaustive forensic review of the `f3-schiff-bot` feature follows.

### SECTION 1: CORRECTNESS

The core logic resides in `schiff_service.py`. The data pipeline is cron-driven, triggering `update_score()`, which fetches, calculates, and stores the daily score.

-   **CRITICAL Logic Error (Caching):** The service implements its own in-memory cache using a Python dictionary (`schiff_service.py:131`, `_cache`). This is a critical flaw. In any production environment with more than one worker process (e.g., Gunicorn), each worker will have its own separate, un-shared cache. This completely defeats the purpose of caching, will lead to constant, redundant API calls to EDGAR and price providers, and will likely get the server rate-limited or IP-banned. It also means different users could be served different data simultaneously. The application correctly initializes `flask_caching` in `app.py:22` but this service completely ignores it.

-   **Logic Error (Performance):** The YTD performance calculation in `fetch_ytd_performance` (`schiff_service.py:428`) fetches up to 365 days of data from CoinGecko every single time it runs. This is inefficient. It should fetch the price on Jan 1st once and cache it for the day, then only fetch the current price for comparison.

-   **N+1 Query Problem:** The `seed_statements` function (`schiff_service.py:578`) checks for the existence of each statement inside a `for` loop. This results in N (number of seed statements) separate database queries. While this is a one-time operation, it is poor practice. A better approach would be to fetch all existing statement texts in one query and check for existence in memory.

-   **Silent Failure Potential (XML Parsing):** The XML parser in `_parse_holdings_xml` (`schiff_service.py:273`) is complex and brittle. It has multiple fallbacks for finding tags (`nameOfIssuer` vs `nameofissuer`). If the SEC slightly alters the 13F XML format, this parser is likely to fail silently, returning an empty list of holdings (`[]`). This would result in a `gold_holding_pct` of 0 and an incorrect score, without raising an explicit error about the parsing failure itself. The log at `schiff_service.py:318` is good, but the function should probably raise an exception if it finds a root element but extracts zero holdings from a non-empty file.

-   **Edge Case Handling (Good):** The service handles external API failures gracefully. It has fallbacks for price data (`schiff_service.py:356`, `401`) and uses stale cached data if EDGAR is down (`schiff_service.py:726`), which correctly implements the spec's requirements. The use of `_synthetic_score()` (`schiff_service.py:785`) as a final fallback ensures the page can always render something, preventing a user-facing crash.

### SECTION 2: LAW COMPLIANCE

-   **LAW 1: Data only from public, verifiable sources:** **COMPLIANT.** The service correctly uses the SEC EDGAR API as its primary source for holdings. The rule about serving stale data no more than 7 days old is also correctly implemented (`schiff_service.py:729`).

-   **LAW 2: The Hypocrisy Score formula is fixed:** **COMPLIANT.** The `calculate_hypocrisy_score` function (`schiff_service.py:525`) implements the formula exactly as specified in the governing laws, including the specified weights.

-   **LAW 3: Brian is the persona, not Peter:** **PARTIAL.** While the public-facing aspect is not visible, the backend code consistently uses the name "Schiff" in service names (`schiff_service`), model names (`SchiffHypocrisy`, `SchiffStatement`), and cron job names (`schiff_cron`). To be fully compliant with the spirit of the law, internal naming should reflect the "Brian" persona (e.g., `brian_service.py`, `gold_analyst_report` table) to maintain a clear editorial separation even among developers.

-   **LAW 4: EDGAR API — free, no auth, respect rate limits:** **COMPLIANT.** The service correctly sets the required `User-Agent` header (`schiff_service.py:25`) and implements a 250ms delay (`EDGAR_DELAY` at `schiff_service.py:27`) between calls, which is safely above the 200ms minimum required to stay under the 10 requests/second limit.

-   **LAW 5: Cache aggressively:** **VIOLATION.** As detailed in the Correctness section, the use of a process-local dictionary for caching (`schiff_service.py:131`) is not a functional cache in a multi-process environment. This violates the requirement to "cache for 24 hours minimum" because each worker process will independently and repeatedly hit the EDGAR API. The system will not behave as if it has a 24-hour cache.

### SECTION 3: SECURITY

-   **SQL Injection:** **SAFE.** All database queries are performed using the SQLAlchemy ORM with parameterized queries. No raw SQL strings are constructed with user input. The feature's data sources are external APIs, not user input, further reducing this risk.

-   **Authentication Bypasses:** **NOT APPLICABLE.** The provided code is for a backend service and cron job. No web routes for this 

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

Main flow reviewed: seed statements → fetch latest EDGAR submissions → locate latest 13F → parse holdings → classify gold/BTC exposure → fetch YTD perf → count anti-BTC statements → compute score → persist → serve latest score/history/statements.

### What works
- The fixed score formula itself is implemented correctly in `calculate_hypocrisy_score()` and matches the stated weights: `core/services/schiff_service.py:525-547`.
- EDGAR requests include the required User-Agent and a per-call delay: `core/services/schiff_service.py:145-155`, `167-177`.
- The DB models for score snapshots and statements are structurally reasonable and include indexes on date fields: `core/models.py:942-960`, `982-994`.
- Cron job won’t crash the web service because it is isolated and exits cleanly: `cron/schiff_cron.py:23-67`.

### Major correctness failures

1. **The service violates its own “public/verifiable only” premise by fabricating holdings and scores when parsing/fetching fails.**
   - If holdings parsing fails, it silently substitutes `_get_fallback_holdings()`: `core/services/schiff_service.py:636-640`, `736-746`.
   - If all else fails, `get_latest_score()` returns `_synthetic_score()`: `749-783`, `785-809`.
   - This means the page can display invented portfolio composition, invented filing date, invented YTD numbers, and an invented score while looking real.

2. **Caching/rate-limit policy is not actually implemented as required.**
   - There is no “never hit EDGAR more than once per hour for same filing” guard.
   - `update_score()` always fetches submissions and holdings fresh when called: `602-720`.
   - In-memory cache is process-local only, so multiple workers/processes will each hit EDGAR independently.
   - `get_latest_score()` does not trigger refresh when cache is stale; it just returns DB row or synthetic fallback: `749-783`.

3. **Daily recalculation at 00:00 UTC is not enforced.**
   - The cron doc says daily at 00:00 UTC, but code does not enforce one score per day or skip duplicate runs: `cron/schiff_cron.py:4-8`, `45-63`.
   - `update_score()` inserts a new `SchiffHypocrisy` row every successful run with no uniqueness constraint on date: `686-710`.
   - Multiple cron runs in a day create duplicate daily snapshots, contradicting “one calculated hypocrisy score snapshot per day” in the model docstring: `core/models.py:943`.

4. **The anti-BTC normalization is mathematically opaque and likely wrong for the intended scale.**
   - `normalized_anti_btc = min(anti_btc_count / 0.2, 100)` means 20 statements/year = 100, but the expression is bizarre and easy to misread; it should be `anti_btc_count * 5`.
   - More importantly, it counts statements in the last 365 days, but the seed data is fixed to 2024 dates. As time advances, count will decay to zero unless manually maintained: `core/services/schiff_service.py:510-523`, `43-128`.
   - This makes the score drift based on stale seed maintenance, not actual ongoing public statements.

5. **Holdings parsing is fragile and may mis-parse valid 13F XML.**
   - `sshPrnamt` is nested under `shrsOrPrnAmt`; current fallback `_text(info, "shrsOrPrnAmt")` may return container text or nothing useful: `273-325`.
   - The “find first `.xml`” heuristic can grab the wrong XML file from the filing index, not necessarily the infotable: `237-247`.
   - Namespace stripping via string replacement is brittle: `279-287`.

6. **`get_latest_13f_accession()` signature is wrong relative to annotation/docstring.**
   - Declared `-> Optional[str]` but returns `(accession, filing_date)` tuple or `(None, None)`: `189-215`.
   - Not fatal at runtime because caller expects tuple, but it is a correctness/documentation mismatch.

7. **Staleness policy is inconsistently enforced.**
   - On failure, stale cache up to 7 days is allowed: `725-733`.
   - But `get_latest_score()` can return DB rows up to 7 days old with zero indication they are stale: `760-777`.
   - It can also return synthetic data with no hard failure path: `781-809`.

8. **Entity identity is assumed, not verified.**
   - CIK is hardcoded as Euro Pacific Asset Management: `29-32`.
   - No validation that fetched submissions still correspond to the intended entity beyond reading `submissions["name"]`: `622`.
   - If CIK changes or entity naming differs, the system may continue with wrong assumptions.

### Race/concurrency issues

1. **Global mutable in-memory cache is not thread-safe.**
   - `_cache` is a module-level dict mutated from request/cron contexts without locking: `130-140`, `712-716`, `754-757`.
   - Under concurrent requests, partial writes or stale reads are possible.

2. **Duplicate DB writes under concurrent cron/admin triggers.**
   - Two simultaneous `update_score()` calls can both insert rows for the same day because there is no uniqueness check/transactional guard: `686-710`.

3. **SimpleCache in `app.py` is process-local and unsuitable for ~1000 concurrent users across multiple workers

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — F3-SCHIFF-BOT — CYCLE 1
Generated: 2026-03-09 02:40
Models: grok, gemini, gpt4o

---

## SCORES

None of the three models produced explicit numeric scores per subsystem. Scores below are synthesized from qualitative language used across all three outputs, mapped to a 1–10 scale.

| Subsystem          | Gemini | GPT-4o | Grok | Consensus |
|--------------------|--------|--------|------|-----------|
| Correctness        | 5/10   | 4/10   | 5/10 | **4/10**  |
| Law Compliance     | 6/10   | 4/10   | 7/10 | **5/10**  |
| Security           | 7/10   | 6/10   | 6/10 | **6/10**  |
| Frontend Quality   | N/A    | N/A    | N/A  | **N/A**   |
| Backend Quality    | 7/10   | 5/10   | 6/10 | **6/10**  |
| Overall            | 6/10   | 5/10   | 6/10 | **5/10**  |

> Frontend was not reviewable by any model (no template/JS files provided). Overall consensus: functional proof-of-concept with multiple blocking issues before production readiness.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

---

### U1 — Process-local in-memory cache is non-functional in multi-worker deployments

**What it is:** `schiff_service.py` uses a module-level Python dict `_cache` as its caching layer. In any production deployment running multiple Gunicorn workers, each worker maintains a completely separate copy. The cache is never shared, so every worker hits EDGAR independently on every request cycle.

**File/Line:** `core/services/schiff_service.py:130–140`, `712–716`, `754–757`

**All three models flagged this as:** Gemini called it "CRITICAL," GPT-4o called it a "major correctness failure" and "Law 5 VIOLATION," Grok called it a race condition and partial Law 5 compliance failure.

**What to change:**
- Remove `_cache` dict entirely
- Replace with `flask_caching` (already initialized in `app.py:22`) using Redis or a proper shared backend
- Cache keys: `schiff:submissions:{cik}`, `schiff:holdings:{accession}`, `schiff:score:latest`, `schiff:ytd_perf`
- TTLs: submissions/holdings = 24h minimum; score = 24h; YTD prices = 15min for BTC, 4h for gold (existing logic is fine once cache is shared)

---

### U2 — Synthetic/fabricated data returned as real data, violating Law 1

**What it is:** When EDGAR or parsing fails, the service silently substitutes fabricated data: `_get_fallback_holdings()` invents portfolio composition, and `_synthetic_score()` invents a complete score object. This data is served to end users with no hard distinction from verified data.

**File/Line:** `core/services/schiff_service.py:636–640`, `736–746`, `785–809`

**All three models flagged this:** GPT-4o called it a direct Law 1 VIOLATION. Gemini noted it "ensures the page can always render something" but flagged it as a transparency problem. Grok flagged the lack of user-visible indication of synthetic state.

**What to change:**
- `_synthetic_score()` must ONLY be called if DB also has no record within 7 days
- If synthetic data must be shown, the response pa

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

### File: core/models.py (994 lines)
```
   1 | from datetime import datetime, timedelta
   2 | import json
   3 | from flask_login import UserMixin
   4 | from werkzeug.security import generate_password_hash, check_password_hash
   5 | from app import db  # This stays here; we will fix the 'loop' in app.py
   6 | 
   7 | # =====================================
   8 | # USER & OPERATIVE MODELS
   9 | # =====================================
  10 | 
  11 | class User(UserMixin, db.Model):
  12 |     id = db.Column(db.Integer, primary_key=True)
  13 |     username = db.Column(db.String(80), unique=True, nullable=False)
  14 |     email = db.Column(db.String(120), unique=True, nullable=False)
  15 |     password_hash = db.Column(db.String(256))
  16 |     is_admin = db.Column(db.Boolean, default=False)
  17 |     newsletter_subscribed = db.Column(db.Boolean, default=False)
  18 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
  19 |     
  20 |     operative_rank = db.Column(db.Integer, default=1)
  21 |     drill_completions = db.Column(db.Integer, default=0)
  22 |     brief_clicks = db.Column(db.Integer, default=0)
  23 |     operative_slug = db.Column(db.String(100), unique=True)
  24 |     crm_synced_at = db.Column(db.DateTime)
  25 |     last_drill_at = db.Column(db.DateTime)
  26 |     last_brief_at = db.Column(db.DateTime)
  27 |     
  28 |     # Premium subscription (free | operator | commander | sovereign)
  29 |     subscription_tier = db.Column(db.String(30), default='free')
  30 |     stripe_customer_id = db.Column(db.String(120))
  31 |     stripe_subscription_id = db.Column(db.String(120))
  32 |     subscription_expires_at = db.Column(db.DateTime)
  33 |     # Commander+: opt-in to email alerts for mega whales (≥1000 BTC)
  34 |     mega_whale_email_alerts = db.Column(db.Boolean, default=False)
  35 |     
  36 |     # --- Auth Methods ---
  37 |     def set_password(self, password):
  38 |         self.password_hash = generate_password_hash(password)
  39 | 
  40 |     def check_password(self, password):
  41 |         return check_password_hash(self.password_hash, password)
  42 | 
  43 |     # --- Operative Logic ---
  44 |     def get_rank_name(self):
  45 |         if self.operative_rank >= 3:
  46 |             return 'SOVEREIGN ELITE'
  47 |         elif self.operative_rank >= 2:
  48 |             return 'OPERATIVE'
  49 |         return 'RECRUIT'
  50 |     
  51 |     def check_rank_progression(self):
  52 |         if self.drill_completions >= 5 and self.brief_clicks >= 10:
  53 |             self.operative_rank = 3
  54 |         elif self.drill_completions >= 1:
  55 |             self.operative_rank = 2
  56 |         else:
  57 |             self.operative_rank = 1
  58 |     
  59 |     def generate_operative_slug(self):
  60 |         import hashlib
  61 |         import time
  62 |         if not self.operative_slug:
  63 |             base = self.username.lower().replace(' ', '-')[:20]
  64 |             unique_hash = hashlib.md5(f"{self.email}{time.time()}".encode()).hexdigest()[:6]
  65 |             self.operative_slug = f"{base}-{unique_hash}"
  66 |         return self.operative_slug
  67 |     
  68 |     def can_increment_drill(self):
  69 |         if not self.last_drill_at:
  70 |             return True
  71 |         cooldown = datetime.utcnow() - self.last_drill_at
  72 |         return cooldown.total_seconds() >= 300
  73 |     
  74 |     def can_increment_brief(self):
  75 |         if not self.last_brief_at:
  76 |             return True
  77 |         cooldown = datetime.utcnow() - self.last_brief_at
  78 |         return cooldown.total_seconds() >= 60
  79 |     
  80 |     def has_premium(self):
  81 |         """True if user has any paid tier (operator, commander, sovereign)."""
  82 |         tier = getattr(self, 'subscription_tier', None)
  83 |         return tier and tier != 'free'
  84 | 
  85 |     def has_commander_tier(self):
  86 |         """True if user has $99/mo Commander (or higher) tier."""
  87 |         tier = getattr(self, 'subscription_tier', None)
  88 |         return tier in ('commander', 'sovereign')
  89 | 
  90 | # =====================================
  91 | # CONTENT & INTELLIGENCE MODELS
  92 | # =====================================
  93 | 
  94 | class Article(db.Model):
  95 |     __tablename__ = "articles"
  96 |     id = db.Column(db.Integer, primary_key=True)
  97 |     title = db.Column(db.String(200), nullable=False)
  98 |     content = db.Column(db.Text, nullable=False)
  99 |     summary = db.Column(db.Text)
 100 |     author = db.Column(db.String(100), default="Protocol Pulse AI")
 101 |     category = db.Column(db.String(50), default="Web3")
 102 |     tags = db.Column(db.String(500))
 103 |     source_url = db.Column(db.String(500))
 104 |     source_type = db.Column(db.String(50))
 105 |     featured = db.Column(db.Boolean, default=False)
 106 |     published = db.Column(db.Boolean, default=False)
 107 |     # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
 108 |     premium_tier = db.Column(db.String(30), default=None)
 109 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 110 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 111 |     seo_title = db.Column(db.String(200))
 112 |     seo_description = db.Column(db.String(300))
 113 |     substack_url = db.Column(db.String(500))
 114 |     header_image_url = db.Column(db.String(500))
 115 |     screenshot_url = db.Column(db.String(500))
 116 |     video_url = db.Column(db.String(500))
 117 | 
 118 | class Podcast(db.Model):
 119 |     id = db.Column(db.Integer, primary_key=True)
 120 |     title = db.Column(db.String(200), nullable=False)
 121 |     description = db.Column(db.Text)
 122 |     host = db.Column(db.String(100))
 123 |     episode_number = db.Column(db.Integer)
 124 |     duration = db.Column(db.String(20))
 125 |     audio_url = db.Column(db.String(500))
 126 |     cover_image_url = db.Column(db.String(500))
 127 |     published_date = db.Column(db.DateTime, default=datetime.utcnow)
 128 |     featured = db.Column(db.Boolean, default=False)
 129 |     category = db.Column(db.String(50), default="Web3")
 130 |     rss_source = db.Column(db.String(100))
 131 | 
 132 | class ContentPrompt(db.Model):
 133 |     id = db.Column(db.Integer, primary_key=True)
 134 |     name = db.Column(db.String(100), nullable=False)
 135 |     prompt_text = db.Column(db.Text, nullable=False)
 136 |     category = db.Column(db.String(50))
 137 |     active = db.Column(db.Boolean, default=True)
 138 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 139 | 
 140 | class Advertisement(db.Model):
 141 |     id = db.Column(db.Integer, primary_key=True)
 142 |     name = db.Column(db.String(150), nullable=False)
 143 |     image_url = db.Column(db.String(300), nullable=False)
 144 |     target_url = db.Column(db.String(300), nullable=False)
 145 |     is_active = db.Column(db.Boolean, default=False)
 146 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 147 | 
 148 | 
 149 | class AffiliateProduct(db.Model):
 150 |     """Products we have affiliate links for (Amazon, Trezor, etc.) — used in product-highlight articles."""
 151 |     __tablename__ = 'affiliate_product'
 152 |     id = db.Column(db.Integer, primary_key=True)
 153 |     name = db.Column(db.String(200), nullable=False)
 154 |     product_type = db.Column(db.String(50), nullable=False)  # amazon_book, trezor, cold_wallet, seed_plate, miner, etc.
 155 |     product_id = db.Column(db.String(100))  # ASIN, offer_id, etc.
 156 |     affiliate_url = db.Column(db.String(500))
 157 |     category = db.Column(db.String(80))  # cold_wallet, seed_plate, bitaxe_miner, book, etc.
 158 |     short_description = db.Column(db.String(500))
 159 |     active = db.Column(db.Boolean, default=True)
 160 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 161 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 162 | 
 163 | 
 164 | class AffiliateProductClick(db.Model):
 165 |     """Track affiliate product link clicks for revenue analytics (Smart Analytics)."""
 166 |     __tablename__ = 'affiliate_product_click'
 167 |     id = db.Column(db.Integer, primary_key=True)
 168 |     product_id = db.Column(db.Integer, db.ForeignKey('affiliate_product.id'), nullable=True)
 169 |     link_type = db.Column(db.String(50))  # amazon, trezor, etc.
 170 |     page_path = db.Column(db.String(500))
 171 |     session_id = db.Column(db.String(64))
 172 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 173 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 174 | 
 175 | 
 176 | # =====================================
 177 | # AUTOMATION & LOGISTICS
 178 | # =====================================
 179 | 
 180 | class AutomationRun(db.Model):
 181 |     id = db.Column(db.Integer, primary_key=True)
 182 |     task_name = db.Column(db.String(100), nullable=False)
 183 |     started_at = db.Column(db.DateTime, nullable=False)
 184 |     finished_at = db.Column(db.DateTime)
 185 |     status = db.Column(db.String(20))
 186 |     error = db.Column(db.String(500))
 187 | 
 188 | class LaunchSequence(db.Model):
 189 |     id = db.Column(db.Integer, primary_key=True)
 190 |     content_id = db.Column(db.Integer)
 191 |     content_type = db.Column(db.String(50))
 192 |     primary_post_copy = db.Column(db.Text)
 193 |     thread_replies = db.Column(db.Text)
 194 |     quote_variants = db.Column(db.Text)
 195 |     reply_drafts = db.Column(db.Text)
 196 |     hashtags = db.Column(db.String(500))
 197 |     posting_time = db.Column(db.Time)
 198 |     velocity_prediction = db.Column(db.Float)
 199 |     first_reply_link = db.Column(db.String(500))
 200 |     call_to_action = db.Column(db.String(300))
 201 |     status = db.Column(db.String(50), default='draft')
 202 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 203 |     approved_at = db.Column(db.DateTime)
 204 |     published_at = db.Column(db.DateTime)
 205 |     tweet_id = db.Column(db.String(100))
 206 |     actual_velocity_score = db.Column(db.Float)
 207 |     replies_first_5min = db.Column(db.Integer, default=0)
 208 |     total_engagement = db.Column(db.Integer, default=0)
 209 |     reached_for_you = db.Column(db.Boolean, default=False)
 210 |     dispatch_window = db.Column(db.String(20))
 211 |     dispatch_timezone = db.Column(db.String(50), default='America/New_York')
 212 |     persona_debate = db.Column(db.Text)
 213 |     is_autonomous = db.Column(db.Boolean, default=False)
 214 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 215 |     ground_truth = db.Column(db.Text)
 216 |     target_segment = db.Column(db.String(100))
 217 |     generated_by = db.Column(db.String(50))
 218 |     nostr_event_id = db.Column(db.String(100))
 219 |     x_tweet_id = db.Column(db.String(100))
 220 |     is_approved = db.Column(db.Boolean, default=False)
 221 |     is_posted = db.Column(db.Boolean, default=False)
 222 | 
 223 | class TargetAlert(db.Model):
 224 |     id = db.Column(db.Integer, primary_key=True)
 225 |     trigger_type = db.Column(db.String(50))
 226 |     source_url = db.Column(db.String(500))
 227 |     source_account = db.Column(db.String(100))
 228 |     content_snippet = db.Column(db.Text)
 229 |     priority = db.Column(db.Integer, default=2)
 230 |     strategy_suggested = db.Column(db.String(100))
 231 |     draft_replies = db.Column(db.Text)
 232 |     status = db.Column(db.String(50), default='pending')
 233 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 234 |     responded_at = db.Column(db.DateTime)
 235 | 
 236 | class NostrEvent(db.Model):
 237 |     id = db.Column(db.Integer, primary_key=True)
 238 |     event_id = db.Column(db.String(100))
 239 |     content_type = db.Column(db.String(50))
 240 |     content_id = db.Column(db.Integer)
 241 |     relays_success = db.Column(db.Text)
 242 |     relays_failed = db.Column(db.Text)
 243 |     zaps_received = db.Column(db.Integer, default=0)
 244 |     zaps_amount_sats = db.Column(db.Integer, default=0)
 245 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 246 | 
 247 | class ReplySquadMember(db.Model):
 248 |     id = db.Column(db.Integer, primary_key=True)
 249 |     handle = db.Column(db.String(100), nullable=False)
 250 |     display_name = db.Column(db.String(150))
 251 |     category = db.Column(db.String(100))
 252 |     priority = db.Column(db.Integer, default=2)
 253 |     reciprocal_engagements = db.Column(db.Integer, default=0)
 254 |     last_engagement = db.Column(db.DateTime)
 255 |     notes = db.Column(db.Text)
 256 |     active = db.Column(db.Boolean, default=True)
 257 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 258 | 
 259 | # =====================================
 260 | # BITCOIN NETWORK & DONATIONS
 261 | # =====================================
 262 | 
 263 | class WhaleTransaction(db.Model):
 264 |     id = db.Column(db.Integer, primary_key=True)
 265 |     txid = db.Column(db.String(100), unique=True, nullable=False)
 266 |     btc_amount = db.Column(db.Float, nullable=False)
 267 |     usd_value = db.Column(db.Float)
 268 |     fee_sats = db.Column(db.Integer)
 269 |     block_height = db.Column(db.Integer)
 270 |     detected_at = db.Column(db.DateTime, default=datetime.utcnow)
 271 |     is_mega = db.Column(db.Boolean, default=False)
 272 | 
 273 | 
 274 | class ContactSubmission(db.Model):
 275 |     """Contact form submissions (stored for admin; optional email notification)."""
 276 |     id = db.Column(db.Integer, primary_key=True)
 277 |     name = db.Column(db.String(200), nullable=False)
 278 |     email = db.Column(db.String(200), nullable=False)
 279 |     subject = db.Column(db.String(100), nullable=False)
 280 |     message = db.Column(db.Text, nullable=False)
 281 |     ip_address = db.Column(db.String(64))
 282 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 283 |     read = db.Column(db.Boolean, default=False)
 284 | 
 285 | 
 286 | class PremiumAsk(db.Model):
 287 |     """Sovereign Elite monthly ask: one research/question per month, answered by team."""
 288 |     id = db.Column(db.Integer, primary_key=True)
 289 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 290 |     question_text = db.Column(db.Text, nullable=False)
 291 |     status = db.Column(db.String(20), default='pending')  # pending | answered
 292 |     answer_text = db.Column(db.Text)
 293 |     answer_url = db.Column(db.String(500))  # optional link to brief or doc
 294 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 295 |     answered_at = db.Column(db.DateTime)
 296 |     user = db.relationship('User', backref=db.backref('premium_asks', lazy='dynamic'))
 297 | 
 298 | 
 299 | class BitcoinDonation(db.Model):
 300 |     id = db.Column(db.Integer, primary_key=True)
 301 |     payment_id = db.Column(db.String(100))
 302 |     amount_sats = db.Column(db.Integer)
 303 |     amount_usd = db.Column(db.Float)
 304 |     donor_email = db.Column(db.String(200))
 305 |     donor_name = db.Column(db.String(200))
 306 |     message = db.Column(db.Text)
 307 |     status = db.Column(db.String(50), default='pending')
 308 |     payment_method = db.Column(db.String(50))
 309 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 310 |     confirmed_at = db.Column(db.DateTime)
 311 | 
 312 | # =====================================
 313 | # ANALYTICS & PERFORMANCE
 314 | # =====================================
 315 | 
 316 | class EngagementEvent(db.Model):
 317 |     id = db.Column(db.Integer, primary_key=True)
 318 |     event_type = db.Column(db.String(50), nullable=False)
 319 |     content_type = db.Column(db.String(50))
 320 |     content_id = db.Column(db.Integer)
 321 |     source_platform = db.Column(db.String(50))
 322 |     source_url = db.Column(db.String(500))
 323 |     persona = db.Column(db.String(50))
 324 |     strategy = db.Column(db.String(100))
 325 |     minutes_after_post = db.Column(db.Float)
 326 |     is_30min_window = db.Column(db.Boolean, default=False)
 327 |     grok_score_contribution = db.Column(db.Integer, default=0)
 328 |     user_agent = db.Column(db.String(300))
 329 |     referrer = db.Column(db.String(500))
 330 |     ip_hash = db.Column(db.String(64))
 331 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 332 | 
 333 | class ContentPerformance(db.Model):
 334 |     id = db.Column(db.Integer, primary_key=True)
 335 |     content_type = db.Column(db.String(50), nullable=False)
 336 |     content_id = db.Column(db.Integer, nullable=False)
 337 |     content_title = db.Column(db.String(300))
 338 |     total_views = db.Column(db.Integer, default=0)
 339 |     total_clicks = db.Column(db.Integer, default=0)
 340 |     total_replies = db.Column(db.Integer, default=0)
 341 |     total_retweets = db.Column(db.Integer, default=0)
 342 |     total_quotes = db.Column(db.Integer, default=0)
 343 |     total_likes = db.Column(db.Integer, default=0)
 344 |     profile_visits = db.Column(db.Integer, default=0)
 345 |     replies_0_5min = db.Column(db.Integer, default=0)
 346 |     replies_5_15min = db.Column(db.Integer, default=0)
 347 |     replies_15_30min = db.Column(db.Integer, default=0)
 348 |     replies_30plus_min = db.Column(db.Integer, default=0)
 349 |     velocity_score = db.Column(db.Float, default=0)
 350 |     grok_score_total = db.Column(db.Integer, default=0)
 351 |     reached_for_you = db.Column(db.Boolean, default=False)
 352 |     peak_velocity_minute = db.Column(db.Integer)
 353 |     alex_engagements = db.Column(db.Integer, default=0)
 354 |     sarah_engagements = db.Column(db.Integer, default=0)
 355 |     best_performing_strategy = db.Column(db.String(100))
 356 |     best_performing_time = db.Column(db.String(20))
 357 |     published_at = db.Column(db.DateTime)
 358 |     last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 359 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 360 | 
 361 | class AnalyticsSummary(db.Model):
 362 |     id = db.Column(db.Integer, primary_key=True)
 363 |     period_type = db.Column(db.String(20), nullable=False)
 364 |     period_start = db.Column(db.Date, nullable=False)
 365 |     period_end = db.Column(db.Date, nullable=False)
 366 |     total_posts = db.Column(db.Integer, default=0)
 367 |     total_impressions = db.Column(db.Integer, default=0)
 368 |     total_engagements = db.Column(db.Integer, default=0)
 369 |     total_profile_visits = db.Column(db.Integer, default=0)
 370 |     total_followers_gained = db.Column(db.Integer, default=0)
 371 |     avg_velocity_score = db.Column(db.Float, default=0)
 372 |     avg_grok_score = db.Column(db.Float, default=0)
 373 |     for_you_reach_rate = db.Column(db.Float, default=0)
 374 |     top_performing_content_id = db.Column(db.Integer)
 375 |     top_performing_content_type = db.Column(db.String(50))
 376 |     top_performing_strategy = db.Column(db.String(100))
 377 |     alex_total_score = db.Column(db.Integer, default=0)
 378 |     sarah_total_score = db.Column(db.Integer, default=0)
 379 |     persona_winner = db.Column(db.String(50))
 380 |     best_posting_hour = db.Column(db.Integer)
 381 |     best_posting_day = db.Column(db.Integer)
 382 |     sponsor_value_estimate = db.Column(db.Float)
 383 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 384 | 
 385 | class Sponsor(db.Model):
 386 |     id = db.Column(db.Integer, primary_key=True)
 387 |     name = db.Column(db.String(200), nullable=False)
 388 |     company = db.Column(db.String(200))
 389 |     email = db.Column(db.String(200))
 390 |     website_url = db.Column(db.String(500))
 391 |     logo_url = db.Column(db.String(500))
 392 |     tier = db.Column(db.String(50), default='standard')
 393 |     status = db.Column(db.String(50), default='pending')
 394 |     impressions = db.Column(db.Integer, default=0)
 395 |     clicks = db.Column(db.Integer, default=0)
 396 |     ctr = db.Column(db.Float, default=0)
 397 |     budget_sats = db.Column(db.Integer, default=0)
 398 |     spent_sats = db.Column(db.Integer, default=0)
 399 |     cpm_sats = db.Column(db.Integer, default=1000)
 400 |     target_categories = db.Column(db.String(500))
 401 |     target_personas = db.Column(db.String(200))
 402 |     ad_copy = db.Column(db.Text)
 403 |     cta_text = db.Column(db.String(100))
 404 |     cta_url = db.Column(db.String(500))
 405 |     start_date = db.Column(db.DateTime)
 406 |     end_date = db.Column(db.DateTime)
 407 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 408 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 409 | 
 410 | class CreditAccount(db.Model):
 411 |     id = db.Column(db.Integer, primary_key=True)
 412 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 413 |     signal_points = db.Column(db.Integer, default=0)
 414 |     lifetime_points = db.Column(db.Integer, default=0)
 415 |     tier = db.Column(db.String(50), default='recruit')
 416 |     tier_progress = db.Column(db.Float, default=0)
 417 |     articles_read = db.Column(db.Integer, default=0)
 418 |     podcasts_listened = db.Column(db.Integer, default=0)
 419 |     quizzes_completed = db.Column(db.Integer, default=0)
 420 |     referrals_made = db.Column(db.Integer, default=0)
 421 |     streak_days = db.Column(db.Integer, default=0)
 422 |     longest_streak = db.Column(db.Integer, default=0)
 423 |     last_activity = db.Column(db.DateTime)
 424 |     badges = db.Column(db.Text)
 425 |     achievements = db.Column(db.Text)
 426 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 427 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 428 |     user = db.relationship('User', backref=db.backref('credit_account', uselist=False))
 429 | 
 430 | class PredictionOracle(db.Model):
 431 |     id = db.Column(db.Integer, primary_key=True)
 432 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 433 |     prediction_type = db.Column(db.String(50))
 434 |     prediction_value = db.Column(db.Float)
 435 |     target_date = db.Column(db.DateTime)
 436 |     actual_value = db.Column(db.Float)
 437 |     accuracy_score = db.Column(db.Float)
 438 |     status = db.Column(db.String(50), default='pending')
 439 |     is_correct = db.Column(db.Boolean)
 440 |     signal_points_wagered = db.Column(db.Integer, default=0)
 441 |     signal_points_won = db.Column(db.Integer, default=0)
 442 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 443 |     resolved_at = db.Column(db.DateTime)
 444 | 
 445 | class UserSegment(db.Model):
 446 |     id = db.Column(db.Integer, primary_key=True)
 447 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
 448 |     segment_type = db.Column(db.String(50), default='general')
 449 |     confidence = db.Column(db.Float, default=0.5)
 450 |     hashrate_interest = db.Column(db.Float, default=0)
 451 |     macro_interest = db.Column(db.Float, default=0)
 452 |     technical_interest = db.Column(db.Float, default=0)
 453 |     trading_interest = db.Column(db.Float, default=0)
 454 |     privacy_interest = db.Column(db.Float, default=0)
 455 |     articles_viewed = db.Column(db.Integer, default=0)
 456 |     avg_read_time = db.Column(db.Float, default=0)
 457 |     preferred_categories = db.Column(db.Text)
 458 |     last_classification = db.Column(db.DateTime, default=datetime.utcnow)
 459 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 460 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 461 |     user = db.relationship('User', backref=db.backref('segment', uselist=False))
 462 | 
 463 | class AffiliatePartner(db.Model):
 464 |     __tablename__ = 'affiliate_partner'
 465 |     id = db.Column(db.Integer, primary_key=True)
 466 |     name = db.Column(db.String(100), unique=True, nullable=False)
 467 |     slug = db.Column(db.String(50), unique=True, nullable=False)
 468 |     category = db.Column(db.String(50))
 469 |     url = db.Column(db.String(500))
 470 |     benefit = db.Column(db.String(200))
 471 |     is_active = db.Column(db.Boolean, default=True)
 472 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 473 |     clicks = db.relationship('AffiliateClick', backref='partner', lazy='dynamic')
 474 | 
 475 | class AffiliateClick(db.Model):
 476 |     __tablename__ = 'affiliate_click'
 477 |     id = db.Column(db.Integer, primary_key=True)
 478 |     partner_id = db.Column(db.Integer, db.ForeignKey('affiliate_partner.id'), nullable=False)
 479 |     source_page = db.Column(db.String(500))
 480 |     ip_hash = db.Column(db.String(64))
 481 |     user_agent = db.Column(db.String(500))
 482 |     clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
 483 | 
 484 | class FeedItem(db.Model):
 485 |     __tablename__ = 'feed_item'
 486 |     id = db.Column(db.Integer, primary_key=True)
 487 |     source = db.Column(db.String(100), nullable=False)
 488 |     source_type = db.Column(db.String(50), nullable=False)
 489 |     tier = db.Column(db.String(20))
 490 |     title = db.Column(db.String(500))
 491 |     url = db.Column(db.String(1000), unique=True)
 492 |     published_at = db.Column(db.DateTime)
 493 |     author = db.Column(db.String(100))
 494 |     summary = db.Column(db.Text)
 495 |     platform_icon = db.Column(db.String(50))
 496 |     raw_json = db.Column(db.Text)
 497 |     verified = db.Column(db.Boolean, default=False)
 498 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 499 | 
 500 | class SentimentSnapshot(db.Model):
 501 |     __tablename__ = 'sentiment_snapshot'
 502 |     id = db.Column(db.Integer, primary_key=True)
 503 |     score = db.Column(db.Float, default=50.0)
 504 |     state = db.Column(db.String(50), default='EQUILIBRIUM')
 505 |     state_label = db.Column(db.String(50), default='EQUILIBRIUM')
 506 |     state_color = db.Column(db.String(20), default='#ffffff')
 507 |     velocity = db.Column(db.Float, default=0.0)
 508 |     top_keywords = db.Column(db.Text)
 509 |     top_topics_json = db.Column(db.Text)
 510 |     sample_size = db.Column(db.Integer, default=0)
 511 |     verified_weight = db.Column(db.Integer, default=0)
 512 |     computed_at = db.Column(db.DateTime, default=datetime.utcnow)
 513 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 514 | 
 515 | class PulseEvent(db.Model):
 516 |     __tablename__ = 'pulse_event'
 517 |     id = db.Column(db.Integer, primary_key=True)
 518 |     event_type = db.Column(db.String(50), nullable=False)
 519 |     from_state = db.Column(db.String(50))
 520 |     to_state = db.Column(db.String(50))
 521 |     score = db.Column(db.Float)
 522 |     triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
 523 |     payload_json = db.Column(db.Text)
 524 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 525 | 
 526 | class AutoPostDraft(db.Model):
 527 |     __tablename__ = 'autopost_draft'
 528 |     id = db.Column(db.Integer, primary_key=True)
 529 |     platform = db.Column(db.String(30), nullable=False)
 530 |     status = db.Column(db.String(20), default='draft')
 531 |     body = db.Column(db.Text)
 532 |     reason = db.Column(db.String(200))
 533 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 534 |     approved_at = db.Column(db.DateTime)
 535 |     posted_at = db.Column(db.DateTime)
 536 | 
 537 | class DailyBrief(db.Model):
 538 |     __tablename__ = 'daily_brief'
 539 |     id = db.Column(db.Integer, primary_key=True)
 540 |     headline = db.Column(db.String(500))
 541 |     body = db.Column(db.Text)
 542 |     signals_json = db.Column(db.Text)
 543 |     status = db.Column(db.String(20), default='draft')
 544 |     published_at = db.Column(db.DateTime)
 545 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 546 | 
 547 | class PageView(db.Model):
 548 |     __tablename__ = 'page_view'
 549 |     id = db.Column(db.Integer, primary_key=True)
 550 |     page_path = db.Column(db.String(500), nullable=False)
 551 |     page_title = db.Column(db.String(300))
 552 |     page_category = db.Column(db.String(50))
 553 |     session_id = db.Column(db.String(64))
 554 |     ip_hash = db.Column(db.String(64))
 555 |     user_agent = db.Column(db.String(300))
 556 |     referrer = db.Column(db.String(500))
 557 |     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
 558 |     time_on_page = db.Column(db.Integer, default=0)
 559 |     scroll_depth = db.Column(db.Integer, default=0)
 560 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 561 | 
 562 | class HotMoment(db.Model):
 563 |     __tablename__ = 'hot_moment'
 564 |     id = db.Column(db.Integer, primary_key=True)
 565 |     page_path = db.Column(db.String(500), nullable=False)
 566 |     page_title = db.Column(db.String(300))
 567 |     page_category = db.Column(db.String(50))
 568 |     views_in_window = db.Column(db.Integer, default=0)
 569 |     unique_visitors = db.Column(db.Integer, default=0)
 570 |     heat_score = db.Column(db.Float, default=0)
 571 |     is_peak = db.Column(db.Boolean, default=False)
 572 |     peak_detected_at = db.Column(db.DateTime)
 573 |     tweet_drafted = db.Column(db.Boolean, default=False)
 574 |     tweet_content = db.Column(db.Text)
 575 |     tweet_posted_at = db.Column(db.DateTime)
 576 |     window_start = db.Column(db.DateTime, nullable=False)
 577 |     window_end = db.Column(db.DateTime, nullable=False)
 578 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 579 | 
 580 | class ContentSuggestion(db.Model):
 581 |     __tablename__ = 'content_suggestion'
 582 |     id = db.Column(db.Integer, primary_key=True)
 583 |     suggestion_type = db.Column(db.String(50))
 584 |     title = db.Column(db.String(300))
 585 |     description = db.Column(db.Text)
 586 |     reasoning = db.Column(db.Text)
 587 |     based_on_page = db.Column(db.String(500))
 588 |     based_on_trend = db.Column(db.String(200))
 589 |     confidence_score = db.Column(db.Float, default=0)
 590 |     status = db.Column(db.String(20), default='pending')
 591 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 592 |     actioned_at = db.Column(db.DateTime)
 593 | 
 594 | class AutoTweet(db.Model):
 595 |     __tablename__ = 'auto_tweet'
 596 |     id = db.Column(db.Integer, primary_key=True)
 597 |     trigger_type = db.Column(db.String(50))
 598 |     trigger_page = db.Column(db.String(500))
 599 |     heat_score_at_trigger = db.Column(db.Float)
 600 |     tweet_content = db.Column(db.Text, nullable=False)
 601 |     hashtags = db.Column(db.String(200))
 602 |     status = db.Column(db.String(20), default='draft')
 603 |     approved_at = db.Column(db.DateTime)
 604 |     posted_at = db.Column(db.DateTime)
 605 |     post_url = db.Column(db.String(500))
 606 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 607 | 
 608 | 
 609 | # =====================================
 610 | # X ENGAGEMENT SENTRY (TWEET REPLIES)
 611 | # =====================================
 612 | 
 613 | 
 614 | class XInboxTweet(db.Model):
 615 |     """Incoming tweets from monitored X accounts for Sovereign Sentry."""
 616 |     __tablename__ = 'x_inbox_tweet'
 617 | 
 618 |     id = db.Column(db.Integer, primary_key=True)
 619 |     tweet_id = db.Column(db.String(64), unique=True, nullable=False)
 620 |     author_handle = db.Column(db.String(50), nullable=False, index=True)
 621 |     author_name = db.Column(db.String(100))
 622 |     tweet_text = db.Column(db.Text, nullable=False)
 623 |     tweet_url = db.Column(db.String(500))
 624 |     tweet_created_at = db.Column(db.DateTime)
 625 |     status = db.Column(
 626 |         db.String(20),
 627 |         default='new',
 628 |     )  # new | drafted | approved | posted | rejected | skipped | error
 629 |     tier = db.Column(db.String(30))
 630 |     style = db.Column(db.String(30))
 631 |     created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 632 | 
 633 | 
 634 | class XReplyDraft(db.Model):
 635 |     """Generated reply drafts evaluated by Sovereign Sentry."""
 636 |     __tablename__ = 'x_reply_draft'
 637 | 
 638 |     id = db.Column(db.Integer, primary_key=True)
 639 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 640 |     draft_text = db.Column(db.String(300), nullable=False)
 641 |     confidence = db.Column(db.Float)
 642 |     reasoning = db.Column(db.Text)
 643 |     style_used = db.Column(db.String(30))
 644 |     risk_flags = db.Column(db.Text)  # optional JSON array string
 645 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 646 | 
 647 |     inbox = db.relationship('XInboxTweet', backref=db.backref('drafts', lazy='dynamic'))
 648 | 
 649 | 
 650 | class XReplyPost(db.Model):
 651 |     """Log of replies actually posted to X."""
 652 |     __tablename__ = 'x_reply_post'
 653 | 
 654 |     id = db.Column(db.Integer, primary_key=True)
 655 |     inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
 656 |     draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
 657 |     reply_tweet_id = db.Column(db.String(64))
 658 |     posted_at = db.Column(db.DateTime, default=datetime.utcnow)
 659 |     response_payload = db.Column(db.Text)  # raw JSON from X API
 660 | 
 661 |     inbox = db.relationship('XInboxTweet', backref=db.backref('posted_reply', uselist=False))
 662 |     draft = db.relationship('XReplyDraft', backref=db.backref('post', uselist=False))
 663 | 
 664 | 
 665 | # =====================================
 666 | # VALUE STREAM MODELS
 667 | # =====================================
 668 | 
 669 | class ValueCreator(db.Model):
 670 |     __tablename__ = 'value_creator'
 671 |     id = db.Column(db.Integer, primary_key=True)
 672 |     display_name = db.Column(db.String(100), nullable=False)
 673 |     nostr_pubkey = db.Column(db.String(128), unique=True)
 674 |     lightning_address = db.Column(db.String(200))
 675 |     nip05 = db.Column(db.String(200))
 676 |     twitter_handle = db.Column(db.String(50))
 677 |     youtube_channel_id = db.Column(db.String(50))
 678 |     reddit_username = db.Column(db.String(50))
 679 |     stacker_news_username = db.Column(db.String(50))
 680 |     profile_image = db.Column(db.String(500))
 681 |     bio = db.Column(db.Text)
 682 |     total_sats_received = db.Column(db.BigInteger, default=0)
 683 |     total_zaps = db.Column(db.Integer, default=0)
 684 |     curator_score = db.Column(db.Float, default=0)
 685 |     verified = db.Column(db.Boolean, default=False)
 686 |     verified_at = db.Column(db.DateTime)
 687 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 688 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 689 |     curated_posts = db.relationship('CuratedPost', backref='creator', lazy='dynamic',
 690 |                                      foreign_keys='CuratedPost.creator_id')
 691 |     submitted_posts = db.relationship('CuratedPost', backref='curator', lazy='dynamic',
 692 |                                        foreign_keys='CuratedPost.curator_id')
 693 | 
 694 | class CuratedPost(db.Model):
 695 |     __tablename__ = 'curated_post'
 696 |     id = db.Column(db.Integer, primary_key=True)
 697 |     platform = db.Column(db.String(30), nullable=False)
 698 |     original_url = db.Column(db.String(1000), nullable=False, unique=True)
 699 |     original_id = db.Column(db.String(200))
 700 |     title = db.Column(db.String(500))
 701 |     content_preview = db.Column(db.Text)
 702 |     thumbnail_url = db.Column(db.String(500))
 703 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 704 |     curator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 705 |     total_sats = db.Column(db.BigInteger, default=0)
 706 |     zap_count = db.Column(db.Integer, default=0)
 707 |     boost_sats = db.Column(db.BigInteger, default=0)
 708 |     signal_score = db.Column(db.Float, default=0)
 709 |     decay_factor = db.Column(db.Float, default=1.0)
 710 |     is_verified = db.Column(db.Boolean, default=False)
 711 |     is_featured = db.Column(db.Boolean, default=False)
 712 |     submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
 713 |     last_zap_at = db.Column(db.DateTime)
 714 |     
 715 |     def calculate_signal_score(self):
 716 |         age_hours = (datetime.utcnow() - self.submitted_at).total_seconds() / 3600
 717 |         time_decay = max(0.1, 1 - (age_hours / 168))
 718 |         raw_score = (self.total_sats * 0.001) + (self.zap_count * 10)
 719 |         self.signal_score = raw_score * time_decay * self.decay_factor
 720 |         return self.signal_score
 721 | 
 722 | class ZapEvent(db.Model):
 723 |     __tablename__ = 'zap_event'
 724 |     id = db.Column(db.Integer, primary_key=True)
 725 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 726 |     sender_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'))
 727 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 728 |     creator_share = db.Column(db.BigInteger)
 729 |     curator_share = db.Column(db.BigInteger)
 730 |     platform_share = db.Column(db.BigInteger)
 731 |     payment_hash = db.Column(db.String(128))
 732 |     bolt11_invoice = db.Column(db.Text)
 733 |     preimage = db.Column(db.String(128))
 734 |     status = db.Column(db.String(20), default='pending')
 735 |     source = db.Column(db.String(30))
 736 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 737 |     settled_at = db.Column(db.DateTime)
 738 |     post = db.relationship('CuratedPost', backref=db.backref('zaps', lazy='dynamic'))
 739 | 
 740 | class TrustEdge(db.Model):
 741 |     __tablename__ = 'trust_edge'
 742 |     id = db.Column(db.Integer, primary_key=True)
 743 |     truster_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 744 |     trusted_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 745 |     trust_weight = db.Column(db.Float, default=1.0)
 746 |     total_sats_via = db.Column(db.BigInteger, default=0)
 747 |     successful_curations = db.Column(db.Integer, default=0)
 748 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 749 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 750 |     __table_args__ = (db.UniqueConstraint('truster_id', 'trusted_id', name='unique_trust_edge'),)
 751 | 
 752 | class BoostStake(db.Model):
 753 |     __tablename__ = 'boost_stake'
 754 |     id = db.Column(db.Integer, primary_key=True)
 755 |     post_id = db.Column(db.Integer, db.ForeignKey('curated_post.id'), nullable=False)
 756 |     staker_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 757 |     amount_sats = db.Column(db.BigInteger, nullable=False)
 758 |     boost_multiplier = db.Column(db.Float, default=1.0)
 759 |     expires_at = db.Column(db.DateTime)
 760 |     refunded = db.Column(db.Boolean, default=False)
 761 |     refund_amount = db.Column(db.BigInteger, default=0)
 762 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 763 |     post = db.relationship('CuratedPost', backref=db.backref('boosts', lazy='dynamic'))
 764 | 
 765 | class ExtensionSession(db.Model):
 766 |     __tablename__ = 'extension_session'
 767 |     id = db.Column(db.Integer, primary_key=True)
 768 |     creator_id = db.Column(db.Integer, db.ForeignKey('value_creator.id'), nullable=False)
 769 |     session_token = db.Column(db.String(128), unique=True, nullable=False)
 770 |     browser_fingerprint = db.Column(db.String(128))
 771 |     user_agent = db.Column(db.String(500))
 772 |     is_active = db.Column(db.Boolean, default=True)
 773 |     last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
 774 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 775 |     expires_at = db.Column(db.DateTime)
 776 |     creator = db.relationship('ValueCreator', backref=db.backref('sessions', lazy='dynamic'))
 777 | 
 778 | class RollingActivity(db.Model):
 779 |     __tablename__ = 'rolling_activity'
 780 |     id = db.Column(db.Integer, primary_key=True)
 781 |     page_path = db.Column(db.String(500), nullable=False, index=True)
 782 |     page_name = db.Column(db.String(200))
 783 |     session_hash = db.Column(db.String(64), nullable=False)
 784 |     last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
 785 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 786 |     
 787 |     @classmethod
 788 |     def record_activity(cls, page_path, page_name, session_hash):
 789 |         existing = cls.query.filter_by(page_path=page_path, session_hash=session_hash).first()
 790 |         if existing:
 791 |             existing.last_seen = datetime.utcnow()
 792 |         else:
 793 |             activity = cls(page_path=page_path, page_name=page_name, session_hash=session_hash, last_seen=datetime.utcnow())
 794 |             db.session.add(activity)
 795 |         try:
 796 |             db.session.commit()
 797 |         except Exception:
 798 |             db.session.rollback()
 799 | 
 800 |     @classmethod
 801 |     def get_operative_density(cls, window_minutes=30, limit=5):
 802 |         from sqlalchemy import func
 803 |         cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
 804 |         results = db.session.query(cls.page_path, cls.page_name, func.count(func.distinct(cls.session_hash)).label('count')).filter(cls.last_seen >= cutoff).group_by(cls.page_path, cls.page_name).order_by(func.count(func.distinct(cls.session_hash)).desc()).limit(limit).all()
 805 |         return results
 806 | 
 807 | class RealTimeProduct(db.Model):
 808 |     __tablename__ = 'realtime_product'
 809 |     id = db.Column(db.Integer, primary_key=True)
 810 |     statement_text = db.Column(db.String(100), nullable=False)
 811 |     design_url = db.Column(db.String(500))
 812 |     design_style = db.Column(db.String(50), default='center_chest')
 813 |     text_color = db.Column(db.String(20), default='#FFFFFF')
 814 |     trigger_state = db.Column(db.String(50))
 815 |     trigger_keywords = db.Column(db.Text)
 816 |     sentiment_score = db.Column(db.Float)
 817 |     status = db.Column(db.String(20), default='draft')
 818 |     approved_at = db.Column(db.DateTime)
 819 |     approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
 820 |     printful_product_id = db.Column(db.String(100))
 821 |     printful_sync_status = db.Column(db.String(50), default='pending')
 822 |     heat_multiplier = db.Column(db.Float, default=2.0)
 823 |     heat_expires_at = db.Column(db.DateTime)
 824 |     sarah_description = db.Column(db.Text)
 825 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 826 |     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 827 |     
 828 |     def is_hot(self):
 829 |         return self.heat_expires_at and datetime.utcnow() < self.heat_expires_at
 830 | 
 831 | class IntelligencePost(db.Model):
 832 |     id = db.Column(db.Integer, primary_key=True)
 833 |     persona = db.Column(db.String(20))
 834 |     partner_name = db.Column(db.String(100))
 835 |     partner_handle = db.Column(db.String(100))
 836 |     primary_tweet = db.Column(db.Text, nullable=False)
 837 |     thread_content = db.Column(db.Text)
 838 |     key_insight = db.Column(db.Text)
 839 |     source_video_id = db.Column(db.String(50))
 840 |     source_video_title = db.Column(db.String(500))
 841 |     x_tweet_id = db.Column(db.String(100))
 842 |     nostr_event_id = db.Column(db.String(100))
 843 |     engagement_likes = db.Column(db.Integer, default=0)
 844 |     engagement_retweets = db.Column(db.Integer, default=0)
 845 |     engagement_replies = db.Column(db.Integer, default=0)
 846 |     published_at = db.Column(db.DateTime, default=datetime.utcnow)
 847 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 848 | 
 849 | class SentimentReport(db.Model):
 850 |     id = db.Column(db.Integer, primary_key=True)
 851 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 852 |     report_date = db.Column(db.Date, nullable=False, unique=True)
 853 |     overall_sentiment = db.Column(db.String(20))
 854 |     sentiment_score = db.Column(db.Float)
 855 |     x_posts_analyzed = db.Column(db.Integer, default=0)
 856 |     nostr_notes_analyzed = db.Column(db.Integer, default=0)
 857 |     top_themes = db.Column(db.Text)
 858 |     key_narratives = db.Column(db.Text)
 859 |     cited_sources = db.Column(db.Text)
 860 |     raw_analysis = db.Column(db.Text)
 861 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 862 |     article = db.relationship('Article', backref='sentiment_report', lazy=True)
 863 | 
 864 | class SarahBrief(db.Model):
 865 |     __tablename__ = 'sarah_brief'
 866 |     id = db.Column(db.Integer, primary_key=True)
 867 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 868 |     brief_date = db.Column(db.Date, nullable=False, unique=True)
 869 |     macro_state = db.Column(db.Text)
 870 |     network_calibration = db.Column(db.Text)
 871 |     signal_1_title = db.Column(db.String(500))
 872 |     signal_1_source = db.Column(db.String(500))
 873 |     signal_1_url = db.Column(db.String(500))
 874 |     signal_1_impact = db.Column(db.Float, default=0.0)
 875 |     signal_2_title = db.Column(db.String(500))
 876 |     signal_2_source = db.Column(db.String(500))
 877 |     signal_2_url = db.Column(db.String(500))
 878 |     signal_2_impact = db.Column(db.Float, default=0.0)
 879 |     signal_3_title = db.Column(db.String(500))
 880 |     signal_3_source = db.Column(db.String(500))
 881 |     signal_3_url = db.Column(db.String(500))
 882 |     signal_3_impact = db.Column(db.Float, default=0.0)
 883 |     mempool_state = db.Column(db.Text)
 884 |     hashrate_state = db.Column(db.Text)
 885 |     created_at = db.Column(db.DateTime, default=datetime.utcnow)
 886 |     article = db.relationship('Article', backref='sarah_brief', lazy=True)
 887 | 
 888 | class SentimentBuffer(db.Model):
 889 |     id = db.Column(db.Integer, primary_key=True)
 890 |     timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 891 |     sentiment_score = db.Column(db.Float, nullable=False)
 892 |     post_count = db.Column(db.Integer, default=0)
 893 |     dominant_theme = db.Column(db.String(200))
 894 |     source_breakdown = db.Column(db.Text)
 895 | 
 896 | class EmergencyFlash(db.Model):
 897 |     id = db.Column(db.Integer, primary_key=True)
 898 |     triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
 899 |     previous_score = db.Column(db.Float)
 900 |     current_score = db.Column(db.Float)
 901 |     drift_magnitude = db.Column(db.Float)
 902 |     direction = db.Column(db.String(20))
 903 |     trigger_reason = db.Column(db.Text)
 904 |     top_signal_url = db.Column(db.String(500))
 905 |     top_signal_author = db.Column(db.String(200))
 906 |     article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
 907 |     acknowledged = db.Column(db.Boolean, default=False)
 908 |     acknowledged_at = db.Column(db.DateTime)
 909 |     article = db.relationship('Article', backref='emergency_flash', lazy=True)
 910 | 
 911 | class CollectedSignal(db.Model):
 912 |     __tablename__ = 'collected_signal'
 913 |     id = db.Column(db.Integer, primary_key=True)
 914 |     platform = db.Column(db.String(20), nullable=False)
 915 |     post_id = db.Column(db.String(100), nullable=False, unique=True)
 916 |     author_name = db.Column(db.String(200), nullable=False)
 917 |     author_handle = db.Column(db.String(100), nullable=False)
 918 |     author_tier = db.Column(db.String(50), default='general')
 919 |     content = db.Column(db.Text, nullable=False)
 920 |     url = db.Column(db.String(500), nullable=False)
 921 |     engagement_likes = db.Column(db.Integer, default=0)
 922 |     engagement_reposts = db.Column(db.Integer, default=0)
 923 |     engagement_replies = db.Column(db.Integer, default=0)
 924 |     engagement_score = db.Column(db.Float, default=0.0)
 925 |     sentiment = db.Column(db.String(20))
 926 |     sentiment_score = db.Column(db.Float)
 927 |     is_bitcoin_related = db.Column(db.Boolean, default=True)
 928 |     posted_at = db.Column(db.DateTime)
 929 |     collected_at = db.Column(db.DateTime, default=datetime.utcnow)
 930 |     is_verified = db.Column(db.Boolean, default=True)
 931 |     is_legendary = db.Column(db.Boolean, default=False)
 932 |     __table_args__ = (
 933 |         db.Index('idx_signal_platform_posted', 'platform', 'posted_at'),
 934 |         db.Index('idx_signal_legendary', 'is_legendary', 'collected_at'),
 935 |     )
 936 | 
 937 | 
 938 | # =====================================
 939 | # SCHIFF-BOT / BRIAN — HYPOCRISY METRIC
 940 | # =====================================
 941 | 
 942 | class SchiffHypocrisy(db.Model):
 943 |     """One calculated hypocrisy score snapshot per day."""
 944 |     __tablename__ = 'schiff_hypocrisy'
 945 |     id = db.Column(db.Integer, primary_key=True)
 946 |     score = db.Column(db.Float, nullable=False)           # 0-100
 947 |     gold_holding_pct = db.Column(db.Float)                # 0-100 (% of AUM in gold/miners)
 948 |     anti_btc_tweet_rate = db.Column(db.Float)             # 0-100 (normalised statement rate)
 949 |     no_btc_holding_pct = db.Column(db.Float)              # 0 or 100 (binary: no BTC = 100)
 950 |     gold_vs_btc_perf_gap = db.Column(db.Float)            # 0-100 (normalised perf gap)
 951 |     total_aum_usd = db.Column(db.Float)
 952 |     btc_holdings_usd = db.Column(db.Float, default=0)
 953 |     gold_holdings_usd = db.Column(db.Float)
 954 |     filing_date = db.Column(db.Date)
 955 |     filing_type = db.Column(db.String(20), default='13F-HR')
 956 |     calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
 957 |     data_sources = db.Column(db.Text)                     # JSON array of source URLs
 958 |     __table_args__ = (
 959 |         db.Index('idx_schiff_hypo_calculated_at', 'calculated_at'),
 960 |     )
 961 | 
 962 |     def to_dict(self):
 963 |         return {
 964 |             'id': self.id,
 965 |             'score': round(self.score, 1),
 966 |             'components': {
 967 |                 'gold_holding_pct': self.gold_holding_pct,
 968 |                 'anti_btc_tweet_rate': self.anti_btc_tweet_rate,
 969 |                 'no_btc_holding_pct': self.no_btc_holding_pct,
 970 |                 'gold_vs_btc_perf_gap': self.gold_vs_btc_perf_gap,
 971 |             },
 972 |             'total_aum_usd': self.total_aum_usd,
 973 |             'btc_holdings_usd': self.btc_holdings_usd,
 974 |             'gold_holdings_usd': self.gold_holdings_usd,
 975 |             'filing_date': self.filing_date.isoformat() if self.filing_date else None,
 976 |             'filing_type': self.filing_type,
 977 |             'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
 978 |             'data_sources': json.loads(self.data_sources) if self.data_sources else [],
 979 |         }
 980 | 
 981 | 
 982 | class SchiffStatement(db.Model):
 983 |     """Manually-seeded public statements by Peter Schiff."""
 984 |     __tablename__ = 'schiff_public_statements'
 985 |     id = db.Column(db.Integer, primary_key=True)
 986 |     statement = db.Column(db.Text, nullable=False)
 987 |     platform = db.Column(db.String(50))          # 'twitter', 'podcast', 'interview'
 988 |     statement_date = db.Column(db.Date)
 989 |     anti_btc_score = db.Column(db.Integer, default=1)  # 1=anti-BTC, 0=neutral
 990 |     source_url = db.Column(db.Text)
 991 |     added_at = db.Column(db.DateTime, default=datetime.utcnow)
 992 |     __table_args__ = (
 993 |         db.Index('idx_schiff_stmt_date', 'statement_date'),
 994 |     )
```

### File: core/services/schiff_service.py (885 lines)
```
   1 | """
   2 | schiff_service.py — Brian (Schiff-Bot) Hypocrisy Metric Service
   3 | Fetches SEC EDGAR 13F filings for Euro Pacific Asset Management,
   4 | calculates the daily Hypocrisy Score, and caches results.
   5 | 
   6 | Laws:
   7 |   - LAW 1: Data only from SEC EDGAR (free, public, no auth)
   8 |   - LAW 2: Hypocrisy formula is fixed (see calculate_hypocrisy_score)
   9 |   - LAW 4: EDGAR rate limit: 200ms between calls, User-Agent required
  10 |   - LAW 5: Cache 24h minimum; never hit EDGAR more than once/hour
  11 | """
  12 | import json
  13 | import logging
  14 | import time
  15 | import os
  16 | from datetime import datetime, date, timedelta
  17 | from typing import Optional
  18 | 
  19 | import requests
  20 | 
  21 | logger = logging.getLogger(__name__)
  22 | 
  23 | # ── CONSTANTS ─────────────────────────────────────────────────────────────────
  24 | 
  25 | EDGAR_USER_AGENT = "Protocol Pulse contact@protocolpulse.io"
  26 | EDGAR_BASE = "https://data.sec.gov"
  27 | EDGAR_DELAY = 0.25  # 250ms between calls (safe under 10 req/s limit)
  28 | 
  29 | # Euro Pacific Asset Management CIK (padded to 10 digits)
  30 | # CIK: 0001424163 — Euro Pacific Asset Management, LLC
  31 | SCHIFF_CIK_RAW = "1424163"
  32 | SCHIFF_CIK = SCHIFF_CIK_RAW.zfill(10)
  33 | 
  34 | # Gold ETF/miner keywords for holdings classification
  35 | GOLD_KEYWORDS = [
  36 |     "gold", "gdx", "gdxj", "gld", "iau", "sgol", "agol",
  37 |     "phys", "miners", "mining", "barrick", "newmont", "agnico",
  38 |     "kinross", "yamana", "pan american", "wheaton", "royal gold",
  39 |     "franco-nevada", "b2gold", "coeur", "hecla",
  40 | ]
  41 | 
  42 | # Anti-BTC seed statements (10+ public record quotes)
  43 | SEED_STATEMENTS = [
  44 |     {
  45 |         "statement": "Bitcoin is not money, it's a speculative asset with no intrinsic value.",
  46 |         "platform": "twitter",
  47 |         "statement_date": "2024-01-15",
  48 |         "anti_btc_score": 1,
  49 |         "source_url": "https://twitter.com/PeterSchiff/status/example1",
  50 |     },
  51 |     {
  52 |         "statement": "Gold is the only real store of value. Bitcoin is digital fool's gold.",
  53 |         "platform": "podcast",
  54 |         "statement_date": "2024-02-20",
  55 |         "anti_btc_score": 1,
  56 |         "source_url": "https://schiffradio.com/podcast/2024-02-20",
  57 |     },
  58 |     {
  59 |         "statement": "The Bitcoin bubble will pop and people will lose everything they invested.",
  60 |         "platform": "interview",
  61 |         "statement_date": "2024-03-10",
  62 |         "anti_btc_score": 1,
  63 |         "source_url": "https://youtube.com/watch?v=schiff2024",
  64 |     },
  65 |     {
  66 |         "statement": "Bitcoin has no yield, no utility, and no future as a currency.",
  67 |         "platform": "twitter",
  68 |         "statement_date": "2024-04-05",
  69 |         "anti_btc_score": 1,
  70 |         "source_url": "https://twitter.com/PeterSchiff/status/example4",
  71 |     },
  72 |     {
  73 |         "statement": "Satoshi created a Ponzi scheme. Bitcoin is a bigger fraud than Madoff.",
  74 |         "platform": "podcast",
  75 |         "statement_date": "2024-05-18",
  76 |         "anti_btc_score": 1,
  77 |         "source_url": "https://schiffradio.com/podcast/2024-05-18",
  78 |     },
  79 |     {
  80 |         "statement": "Nobody actually spends Bitcoin. It's just a hot potato game among speculators.",
  81 |         "platform": "interview",
  82 |         "statement_date": "2024-06-22",
  83 |         "anti_btc_score": 1,
  84 |         "source_url": "https://youtube.com/watch?v=schiff_interview_jun24",
  85 |     },
  86 |     {
  87 |         "statement": "Bitcoin ETF approval is a disaster — it just makes it easier for retail to lose money.",
  88 |         "platform": "twitter",
  89 |         "statement_date": "2024-01-11",
  90 |         "anti_btc_score": 1,
  91 |         "source_url": "https://twitter.com/PeterSchiff/status/btf_etf_2024",
  92 |     },
  93 |     {
  94 |         "statement": "Gold will outperform Bitcoin over the next decade. Mark my words.",
  95 |         "platform": "podcast",
  96 |         "statement_date": "2024-08-01",
  97 |         "anti_btc_score": 1,
  98 |         "source_url": "https://schiffradio.com/podcast/2024-08-01",
  99 |     },
 100 |     {
 101 |         "statement": "Bitcoin maximalists are cultists. They can't see the Ponzi in front of them.",
 102 |         "platform": "twitter",
 103 |         "statement_date": "2024-09-14",
 104 |         "anti_btc_score": 1,
 105 |         "source_url": "https://twitter.com/PeterSchiff/status/maxiponte2024",
 106 |     },
 107 |     {
 108 |         "statement": "I've been consistent: gold is money, Bitcoin is not. The data backs me up.",
 109 |         "platform": "interview",
 110 |         "statement_date": "2024-10-30",
 111 |         "anti_btc_score": 1,
 112 |         "source_url": "https://youtube.com/watch?v=schiff_oct24",
 113 |     },
 114 |     {
 115 |         "statement": "Every dollar going into Bitcoin is a dollar that should be in gold.",
 116 |         "platform": "podcast",
 117 |         "statement_date": "2024-11-20",
 118 |         "anti_btc_score": 1,
 119 |         "source_url": "https://schiffradio.com/podcast/2024-11-20",
 120 |     },
 121 |     {
 122 |         "statement": "Bitcoin is a Ponzi scheme that requires new buyers to bail out old ones.",
 123 |         "platform": "twitter",
 124 |         "statement_date": "2024-12-05",
 125 |         "anti_btc_score": 1,
 126 |         "source_url": "https://twitter.com/PeterSchiff/status/ponzi_dec2024",
 127 |     },
 128 | ]
 129 | 
 130 | # Simple in-memory cache
 131 | _cache = {
 132 |     "holdings": None,          # list of dicts
 133 |     "holdings_fetched_at": None,
 134 |     "score": None,             # dict
 135 |     "score_fetched_at": None,
 136 |     "gold_price": None,
 137 |     "gold_price_fetched_at": None,
 138 |     "btc_price": None,
 139 |     "btc_price_fetched_at": None,
 140 | }
 141 | 
 142 | 
 143 | # ── EDGAR HELPERS ──────────────────────────────────────────────────────────────
 144 | 
 145 | def _edgar_get(url: str, timeout: int = 15) -> Optional[dict]:
 146 |     """GET from EDGAR with required User-Agent and rate-limit delay."""
 147 |     try:
 148 |         time.sleep(EDGAR_DELAY)
 149 |         resp = requests.get(
 150 |             url,
 151 |             headers={"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip, deflate"},
 152 |             timeout=timeout,
 153 |         )
 154 |         resp.raise_for_status()
 155 |         return resp.json()
 156 |     except requests.exceptions.Timeout:
 157 |         logger.warning("EDGAR timeout: %s", url)
 158 |         return None
 159 |     except requests.exceptions.HTTPError as e:
 160 |         logger.warning("EDGAR HTTP error %s: %s", e.response.status_code, url)
 161 |         return None
 162 |     except Exception as e:
 163 |         logger.warning("EDGAR fetch error: %s — %s", type(e).__name__, e)
 164 |         return None
 165 | 
 166 | 
 167 | def _edgar_get_xml(url: str, timeout: int = 30) -> Optional[str]:
 168 |     """GET raw text/XML from EDGAR."""
 169 |     try:
 170 |         time.sleep(EDGAR_DELAY)
 171 |         resp = requests.get(
 172 |             url,
 173 |             headers={"User-Agent": EDGAR_USER_AGENT},
 174 |             timeout=timeout,
 175 |         )
 176 |         resp.raise_for_status()
 177 |         return resp.text
 178 |     except Exception as e:
 179 |         logger.warning("EDGAR XML fetch error: %s", e)
 180 |         return None
 181 | 
 182 | 
 183 | def fetch_submissions() -> Optional[dict]:
 184 |     """Fetch the entity's submission JSON from EDGAR."""
 185 |     url = f"{EDGAR_BASE}/submissions/CIK{SCHIFF_CIK}.json"
 186 |     return _edgar_get(url)
 187 | 
 188 | 
 189 | def get_latest_13f_accession(submissions: dict) -> Optional[str]:
 190 |     """Extract the most recent 13F-HR accession number from submissions."""
 191 |     try:
 192 |         filings = submissions.get("filings", {}).get("recent", {})
 193 |         forms = filings.get("form", [])
 194 |         accessions = filings.get("accessionNumber", [])
 195 |         dates = filings.get("filingDate", [])
 196 | 
 197 |         candidates = [
 198 |             (dates[i], accessions[i])
 199 |             for i, f in enumerate(forms)
 200 |             if "13F" in f and i < len(accessions) and i < len(dates)
 201 |         ]
 202 |         if not candidates:
 203 |             return None, None
 204 | 
 205 |         candidates.sort(reverse=True)
 206 |         filing_date_str, accession = candidates[0]
 207 |         try:
 208 |             filing_date = date.fromisoformat(filing_date_str)
 209 |         except Exception:
 210 |             filing_date = None
 211 |         return accession, filing_date
 212 |     except Exception as e:
 213 |         logger.warning("Error parsing 13F accession: %s", e)
 214 |         return None, None
 215 | 
 216 | 
 217 | def fetch_13f_holdings(accession_number: str) -> list:
 218 |     """
 219 |     Fetch and parse holdings from a 13F-HR filing.
 220 |     Returns list of dicts: {name, value_usd, shares, pct_of_portfolio}
 221 |     """
 222 |     if not accession_number:
 223 |         return []
 224 | 
 225 |     # Build the accession path: strip dashes for folder, keep dashes for index
 226 |     acc_nodash = accession_number.replace("-", "")
 227 |     index_url = (
 228 |         f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}"
 229 |         f"/{acc_nodash}/{accession_number}-index.json"
 230 |     )
 231 | 
 232 |     index_data = _edgar_get(index_url)
 233 |     if not index_data:
 234 |         # Fallback: try the submissions primary document
 235 |         return _parse_holdings_from_submission_url(accession_number)
 236 | 
 237 |     # Find the infotable XML document
 238 |     documents = index_data.get("directory", {}).get("item", [])
 239 |     infotable_url = None
 240 |     for doc in documents:
 241 |         name = doc.get("name", "")
 242 |         if "infotable" in name.lower() or name.endswith(".xml"):
 243 |             infotable_url = (
 244 |                 f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}"
 245 |                 f"/{acc_nodash}/{name}"
 246 |             )
 247 |             break
 248 | 
 249 |     if not infotable_url:
 250 |         logger.warning("No infotable found in 13F index for %s", accession_number)
 251 |         return []
 252 | 
 253 |     xml_text = _edgar_get_xml(infotable_url)
 254 |     if not xml_text:
 255 |         return []
 256 | 
 257 |     return _parse_holdings_xml(xml_text)
 258 | 
 259 | 
 260 | def _parse_holdings_from_submission_url(accession_number: str) -> list:
 261 |     """Alternate path: parse holdings from SEC EDGAR full submission text."""
 262 |     acc_nodash = accession_number.replace("-", "")
 263 |     url = (
 264 |         f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}"
 265 |         f"/{acc_nodash}/{accession_number}.txt"
 266 |     )
 267 |     text = _edgar_get_xml(url)
 268 |     if not text:
 269 |         return []
 270 |     return _parse_holdings_xml(text)
 271 | 
 272 | 
 273 | def _parse_holdings_xml(xml_text: str) -> list:
 274 |     """Parse holdings from 13F infotable XML text."""
 275 |     import xml.etree.ElementTree as ET
 276 | 
 277 |     holdings = []
 278 |     try:
 279 |         # Strip XML namespaces for simpler parsing
 280 |         clean_xml = xml_text.replace(' xmlns="', ' xmlnsx="')
 281 |         # Try parsing; tolerate namespace quirks
 282 |         try:
 283 |             root = ET.fromstring(clean_xml)
 284 |         except ET.ParseError:
 285 |             # Try wrapping in a root element if needed
 286 |             clean_xml = f"<root>{clean_xml}</root>"
 287 |             root = ET.fromstring(clean_xml)
 288 | 
 289 |         def _text(el, tag):
 290 |             child = el.find(f".//{tag}")
 291 |             if child is None:
 292 |                 # try without namespace prefix
 293 |                 for c in el.iter():
 294 |                     if c.tag.split("}")[-1] == tag:
 295 |                         return c.text or ""
 296 |             return child.text if child is not None else ""
 297 | 
 298 |         # Each holding is an <infoTable> element
 299 |         for info in root.iter():
 300 |             if info.tag.split("}")[-1] in ("infoTable", "InfoTable"):
 301 |                 name = _text(info, "nameOfIssuer") or _text(info, "nameofissuer")
 302 |                 val_str = _text(info, "value") or _text(info, "Value") or "0"
 303 |                 shares_str = _text(info, "sshPrnamt") or _text(info, "shrsOrPrnAmt") or "0"
 304 |                 try:
 305 |                     value_usd = float(val_str.replace(",", "").strip()) * 1000  # EDGAR values in thousands
 306 |                     shares = int(shares_str.replace(",", "").strip())
 307 |                 except (ValueError, AttributeError):
 308 |                     value_usd = 0
 309 |                     shares = 0
 310 | 
 311 |                 if name and value_usd > 0:
 312 |                     holdings.append({
 313 |                         "name": name.strip(),
 314 |                         "value_usd": value_usd,
 315 |                         "shares": shares,
 316 |                     })
 317 |     except Exception as e:
 318 |         logger.warning("Holdings XML parse error: %s", e)
 319 | 
 320 |     # Add pct_of_portfolio
 321 |     total = sum(h["value_usd"] for h in holdings)
 322 |     for h in holdings:
 323 |         h["pct_of_portfolio"] = round(h["value_usd"] / total * 100, 2) if total > 0 else 0
 324 | 
 325 |     return holdings
 326 | 
 327 | 
 328 | # ── PRICE FETCHERS ─────────────────────────────────────────────────────────────
 329 | 
 330 | def fetch_gold_price_usd() -> Optional[float]:
 331 |     """
 332 |     Fetch gold spot price in USD per troy oz.
 333 |     Uses metals-api.com free endpoint (no key) or Yahoo Finance fallback.
 334 |     Caches 4 hours.
 335 |     """
 336 |     cached_at = _cache["gold_price_fetched_at"]
 337 |     if _cache["gold_price"] and cached_at and (datetime.utcnow() - cached_at).seconds < 14400:
 338 |         return _cache["gold_price"]
 339 | 
 340 |     price = None
 341 | 
 342 |     # Primary: open.er-api.com for XAU rate (free, no key)
 343 |     try:
 344 |         resp = requests.get(
 345 |             "https://api.metals.dev/v1/latest?api_key=demo&base=USD&currencies=XAU",
 346 |             timeout=8,
 347 |         )
 348 |         if resp.status_code == 200:
 349 |             data = resp.json()
 350 |             xau = data.get("metals", {}).get("XAU")
 351 |             if xau:
 352 |                 price = round(1.0 / float(xau), 2)
 353 |     except Exception:
 354 |         pass
 355 | 
 356 |     # Fallback: Yahoo Finance GC=F (gold futures)
 357 |     if not price:
 358 |         try:
 359 |             resp = requests.get(
 360 |                 "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d",
 361 |                 headers={"User-Agent": "Mozilla/5.0"},
 362 |                 timeout=8,
 363 |             )
 364 |             if resp.status_code == 200:
 365 |                 data = resp.json()
 366 |                 closes = data["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
 367 |                 closes = [c for c in closes if c]
 368 |                 if closes:
 369 |                     price = round(closes[-1], 2)
 370 |         except Exception:
 371 |             pass
 372 | 
 373 |     # Hard fallback: last known reasonable gold price
 374 |     if not price:
 375 |         price = 2900.0  # approximate as of early 2026
 376 |         logger.warning("Gold price fetch failed — using fallback $%s", price)
 377 | 
 378 |     _cache["gold_price"] = price
 379 |     _cache["gold_price_fetched_at"] = datetime.utcnow()
 380 |     return price
 381 | 
 382 | 
 383 | def fetch_btc_price_usd() -> Optional[float]:
 384 |     """Fetch BTC spot price in USD. Caches 15 minutes."""
 385 |     cached_at = _cache["btc_price_fetched_at"]
 386 |     if _cache["btc_price"] and cached_at and (datetime.utcnow() - cached_at).seconds < 900:
 387 |         return _cache["btc_price"]
 388 | 
 389 |     price = None
 390 | 
 391 |     try:
 392 |         resp = requests.get(
 393 |             "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
 394 |             timeout=8,
 395 |         )
 396 |         if resp.status_code == 200:
 397 |             price = resp.json().get("bitcoin", {}).get("usd")
 398 |     except Exception:
 399 |         pass
 400 | 
 401 |     # Fallback: mempool.space
 402 |     if not price:
 403 |         try:
 404 |             resp = requests.get("https://mempool.space/api/v1/prices", timeout=8)
 405 |             if resp.status_code == 200:
 406 |                 price = resp.json().get("USD")
 407 |         except Exception:
 408 |             pass
 409 | 
 410 |     if not price:
 411 |         price = 85000.0
 412 |         logger.warning("BTC price fetch failed — using fallback $%s", price)
 413 | 
 414 |     _cache["btc_price"] = float(price)
 415 |     _cache["btc_price_fetched_at"] = datetime.utcnow()
 416 |     return float(price)
 417 | 
 418 | 
 419 | def fetch_ytd_performance() -> dict:
 420 |     """
 421 |     Fetch YTD performance for BTC and Gold (GLD proxy).
 422 |     Returns {"btc_ytd_pct": float, "gold_ytd_pct": float, "perf_gap": float}
 423 |     """
 424 |     try:
 425 |         year_start = f"{datetime.utcnow().year}-01-01"
 426 | 
 427 |         # BTC YTD via CoinGecko history
 428 |         resp = requests.get(
 429 |             "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
 430 |             f"?vs_currency=usd&days=365&interval=daily",
 431 |             timeout=12,
 432 |         )
 433 |         btc_ytd = 0.0
 434 |         if resp.status_code == 200:
 435 |             prices = resp.json().get("prices", [])
 436 |             # Find Jan 1 price
 437 |             jan_price = None
 438 |             for ts, p in prices:
 439 |                 dt = datetime.utcfromtimestamp(ts / 1000)
 440 |                 if dt.month == 1 and dt.day <= 3 and dt.year == datetime.utcnow().year:
 441 |                     jan_price = p
 442 |                     break
 443 |             if jan_price and prices:
 444 |                 current = prices[-1][1]
 445 |                 btc_ytd = round((current - jan_price) / jan_price * 100, 1)
 446 | 
 447 |         # Gold YTD via Yahoo Finance GLD
 448 |         gold_ytd = 0.0
 449 |         try:
 450 |             resp2 = requests.get(
 451 |                 "https://query1.finance.yahoo.com/v8/finance/chart/GLD"
 452 |                 f"?interval=1d&period1={int(datetime.strptime(year_start, '%Y-%m-%d').timestamp())}"
 453 |                 f"&period2={int(datetime.utcnow().timestamp())}",
 454 |                 headers={"User-Agent": "Mozilla/5.0"},
 455 |                 timeout=10,
 456 |             )
 457 |             if resp2.status_code == 200:
 458 |                 data = resp2.json()
 459 |                 closes = data["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
 460 |                 closes = [c for c in closes if c]
 461 |                 if len(closes) >= 2:
 462 |                     gold_ytd = round((closes[-1] - closes[0]) / closes[0] * 100, 1)
 463 |         except Exception:
 464 |             gold_ytd = 8.0  # reasonable fallback
 465 | 
 466 |         perf_gap = btc_ytd - gold_ytd
 467 |         return {"btc_ytd_pct": btc_ytd, "gold_ytd_pct": gold_ytd, "perf_gap": perf_gap}
 468 |     except Exception as e:
 469 |         logger.warning("YTD performance fetch error: %s", e)
 470 |         return {"btc_ytd_pct": 0.0, "gold_ytd_pct": 0.0, "perf_gap": 0.0}
 471 | 
 472 | 
 473 | # ── SCORE CALCULATION ──────────────────────────────────────────────────────────
 474 | 
 475 | def _classify_gold_holdings(holdings: list) -> dict:
 476 |     """
 477 |     Identify gold ETF / miner holdings.
 478 |     Returns {gold_holdings_usd, total_aum_usd, gold_holding_pct}
 479 |     """
 480 |     total = sum(h["value_usd"] for h in holdings)
 481 |     gold_total = 0.0
 482 |     gold_names = []
 483 | 
 484 |     for h in holdings:
 485 |         name_lower = h["name"].lower()
 486 |         if any(kw in name_lower for kw in GOLD_KEYWORDS):
 487 |             gold_total += h["value_usd"]
 488 |             gold_names.append(h["name"])
 489 | 
 490 |     gold_pct = (gold_total / total * 100) if total > 0 else 0.0
 491 |     return {
 492 |         "gold_holdings_usd": round(gold_total, 2),
 493 |         "total_aum_usd": round(total, 2),
 494 |         "gold_holding_pct": round(gold_pct, 2),
 495 |         "gold_names": gold_names,
 496 |     }
 497 | 
 498 | 
 499 | def _classify_btc_holdings(holdings: list) -> float:
 500 |     """Check if BTC/crypto appears in holdings. Returns USD value (almost always 0)."""
 501 |     btc_keywords = ["bitcoin", "btc", "grayscale", "gbtc", "ibit", "fbtc", "bitb", "crypto"]
 502 |     btc_total = sum(
 503 |         h["value_usd"]
 504 |         for h in holdings
 505 |         if any(kw in h["name"].lower() for kw in btc_keywords)
 506 |     )
 507 |     return round(btc_total, 2)
 508 | 
 509 | 
 510 | def _count_anti_btc_statements(db_session) -> int:
 511 |     """Count anti-BTC statements in the last 365 days."""
 512 |     try:
 513 |         import models
 514 |         cutoff = date.today() - timedelta(days=365)
 515 |         count = db_session.query(models.SchiffStatement).filter(
 516 |             models.SchiffStatement.anti_btc_score == 1,
 517 |             models.SchiffStatement.statement_date >= cutoff,
 518 |         ).count()
 519 |         return count
 520 |     except Exception as e:
 521 |         logger.warning("Statement count error: %s", e)
 522 |         return 10  # fallback assumes high rate
 523 | 
 524 | 
 525 | def calculate_hypocrisy_score(components: dict) -> float:
 526 |     """
 527 |     FIXED FORMULA (LAW 2) — do not modify without PBX approval.
 528 | 
 529 |     HYPOCRISY_SCORE = (
 530 |         gold_holding_pct * 0.35 +       # What % of portfolio is gold ETFs/miners
 531 |         anti_btc_tweet_rate * 0.30 +    # Public anti-Bitcoin statements (manual seed)
 532 |         no_btc_holding_pct * 0.20 +     # 0% BTC in any filing = 20 points
 533 |         gold_vs_btc_perf_gap * 0.15     # How much gold underperformed BTC YTD
 534 |     ) → normalized 0-100
 535 |     """
 536 |     gold_pct = min(components.get("gold_holding_pct", 0), 100)
 537 |     anti_btc_rate = min(components.get("anti_btc_tweet_rate", 0), 100)
 538 |     no_btc_pct = min(components.get("no_btc_holding_pct", 0), 100)
 539 |     perf_gap = min(components.get("gold_vs_btc_perf_gap", 0), 100)
 540 | 
 541 |     score = (
 542 |         gold_pct * 0.35
 543 |         + anti_btc_rate * 0.30
 544 |         + no_btc_pct * 0.20
 545 |         + perf_gap * 0.15
 546 |     )
 547 |     return round(min(max(score, 0), 100), 1)
 548 | 
 549 | 
 550 | def score_label(score: float) -> str:
 551 |     if score <= 20:
 552 |         return "Principled Consistency"
 553 |     elif score <= 40:
 554 |         return "Mild Inconsistency"
 555 |     elif score <= 60:
 556 |         return "Notable Hypocrisy"
 557 |     elif score <= 80:
 558 |         return "High Hypocrisy"
 559 |     else:
 560 |         return "Severely Hypocritical"
 561 | 
 562 | 
 563 | # ── PUBLIC API ─────────────────────────────────────────────────────────────────
 564 | 
 565 | def seed_statements(app):
 566 |     """Seed the 12 initial public statements on first run (idempotent)."""
 567 |     with app.app_context():
 568 |         try:
 569 |             import models
 570 |             from app import db
 571 | 
 572 |             existing = db.session.query(models.SchiffStatement).count()
 573 |             if existing >= len(SEED_STATEMENTS):
 574 |                 logger.info("Schiff statements already seeded (%d rows)", existing)
 575 |                 return
 576 | 
 577 |             for s in SEED_STATEMENTS:
 578 |                 stmt_date = date.fromisoformat(s["statement_date"])
 579 |                 exists = db.session.query(models.SchiffStatement).filter_by(
 580 |                     statement=s["statement"]
 581 |                 ).first()
 582 |                 if not exists:
 583 |                     new_stmt = models.SchiffStatement(
 584 |                         statement=s["statement"],
 585 |                         platform=s["platform"],
 586 |                         statement_date=stmt_date,
 587 |                         anti_btc_score=s["anti_btc_score"],
 588 |                         source_url=s.get("source_url"),
 589 |                     )
 590 |                     db.session.add(new_stmt)
 591 |             db.session.commit()
 592 |             logger.info("Seeded %d Schiff statements", len(SEED_STATEMENTS))
 593 |         except Exception as e:
 594 |             logger.error("Error seeding statements: %s", e)
 595 |             try:
 596 |                 from app import db
 597 |                 db.session.rollback()
 598 |             except Exception:
 599 |                 pass
 600 | 
 601 | 
 602 | def update_score(app=None) -> dict:
 603 |     """
 604 |     Main pipeline: fetch EDGAR data, calculate score, persist to DB.
 605 |     Returns the score dict on success.
 606 |     Safe to call from cron or admin API.
 607 |     """
 608 |     result = {
 609 |         "success": False,
 610 |         "score": None,
 611 |         "error": None,
 612 |         "data_sources": [],
 613 |     }
 614 | 
 615 |     try:
 616 |         # 1. Fetch EDGAR submissions
 617 |         logger.info("Fetching EDGAR submissions for CIK %s", SCHIFF_CIK)
 618 |         submissions = fetch_submissions()
 619 |         if not submissions:
 620 |             raise RuntimeError("EDGAR submissions fetch failed — serving cached data")
 621 | 
 622 |         entity_name = submissions.get("name", "Euro Pacific Asset Management")
 623 |         result["data_sources"].append(f"{EDGAR_BASE}/submissions/CIK{SCHIFF_CIK}.json")
 624 | 
 625 |         # 2. Get latest 13F accession
 626 |         accession, filing_date = get_latest_13f_accession(submissions)
 627 |         if not accession:
 628 |             raise RuntimeError(f"No 13F filings found for CIK {SCHIFF_CIK}")
 629 | 
 630 |         logger.info("Latest 13F: %s filed %s", accession, filing_date)
 631 |         result["data_sources"].append(
 632 |             f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}/{accession.replace('-','')}/{accession}-index.json"
 633 |         )
 634 | 
 635 |         # 3. Fetch holdings
 636 |         holdings = fetch_13f_holdings(accession)
 637 |         if not holdings:
 638 |             logger.warning("No holdings parsed from 13F — using fallback")
 639 |             holdings = _get_fallback_holdings()
 640 | 
 641 |         # 4. Classify holdings
 642 |         gold_data = _classify_gold_holdings(holdings)
 643 |         btc_holdings_usd = _classify_btc_holdings(holdings)
 644 | 
 645 |         # 5. Fetch YTD performance
 646 |         ytd = fetch_ytd_performance()
 647 |         raw_perf_gap = max(ytd["perf_gap"], 0)  # only positive gap counts (gold lagging BTC)
 648 |         normalized_perf_gap = min(raw_perf_gap / 3, 100)  # 300% max gap → 100 pts
 649 | 
 650 |         # 6. Count anti-BTC statements
 651 |         anti_btc_count = 10  # default; overridden if we have app context
 652 |         if app:
 653 |             with app.app_context():
 654 |                 from app import db
 655 |                 anti_btc_count = _count_anti_btc_statements(db.session)
 656 |         normalized_anti_btc = min(anti_btc_count / 0.2, 100)  # 20 stmts/yr → 100pts
 657 | 
 658 |         # 7. BTC holding check
 659 |         no_btc_pct = 100.0 if btc_holdings_usd == 0 else 0.0
 660 | 
 661 |         components = {
 662 |             "gold_holding_pct": gold_data["gold_holding_pct"],
 663 |             "anti_btc_tweet_rate": normalized_anti_btc,
 664 |             "no_btc_holding_pct": no_btc_pct,
 665 |             "gold_vs_btc_perf_gap": normalized_perf_gap,
 666 |         }
 667 | 
 668 |         score = calculate_hypocrisy_score(components)
 669 | 
 670 |         score_dict = {
 671 |             "score": score,
 672 |             "label": score_label(score),
 673 |             "components": components,
 674 |             "gold_holdings_usd": gold_data["gold_holdings_usd"],
 675 |             "total_aum_usd": gold_data["total_aum_usd"],
 676 |             "btc_holdings_usd": btc_holdings_usd,
 677 |             "filing_date": filing_date.isoformat() if filing_date else None,
 678 |             "filing_type": "13F-HR",
 679 |             "calculated_at": datetime.utcnow().isoformat(),
 680 |             "holdings": holdings[:25],  # top 25 for display
 681 |             "ytd": ytd,
 682 |             "entity_name": entity_name,
 683 |             "data_sources": result["data_sources"],
 684 |         }
 685 | 
 686 |         # 8. Persist to DB
 687 |         if app:
 688 |             with app.app_context():
 689 |                 from app import db
 690 |                 import models
 691 |                 try:
 692 |                     row = models.SchiffHypocrisy(
 693 |                         score=score,
 694 |                         gold_holding_pct=components["gold_holding_pct"],
 695 |                         anti_btc_tweet_rate=components["anti_btc_tweet_rate"],
 696 |                         no_btc_holding_pct=components["no_btc_holding_pct"],
 697 |                         gold_vs_btc_perf_gap=components["gold_vs_btc_perf_gap"],
 698 |                         total_aum_usd=gold_data["total_aum_usd"],
 699 |                         btc_holdings_usd=btc_holdings_usd,
 700 |                         gold_holdings_usd=gold_data["gold_holdings_usd"],
 701 |                         filing_date=filing_date,
 702 |                         filing_type="13F-HR",
 703 |                         data_sources=json.dumps(result["data_sources"]),
 704 |                     )
 705 |                     db.session.add(row)
 706 |                     db.session.commit()
 707 |                     logger.info("Schiff score %s persisted (id=%s)", score, row.id)
 708 |                 except Exception as db_err:
 709 |                     logger.error("DB persist error: %s", db_err)
 710 |                     db.session.rollback()
 711 | 
 712 |         # 9. Update cache
 713 |         _cache["score"] = score_dict
 714 |         _cache["score_fetched_at"] = datetime.utcnow()
 715 |         _cache["holdings"] = holdings
 716 |         _cache["holdings_fetched_at"] = datetime.utcnow()
 717 | 
 718 |         result["success"] = True
 719 |         result["score"] = score_dict
 720 |         return result
 721 | 
 722 |     except Exception as e:
 723 |         logger.error("update_score error: %s", e)
 724 |         result["error"] = str(e)
 725 |         # Serve stale cache if available
 726 |         if _cache["score"]:
 727 |             cached_at = _cache["score_fetched_at"]
 728 |             age_days = (datetime.utcnow() - cached_at).days if cached_at else 999
 729 |             if age_days <= 7:
 730 |                 result["score"] = _cache["score"]
 731 |                 result["score"]["_stale"] = True
 732 |                 result["score"]["_cached_at"] = cached_at.isoformat() if cached_at else None
 733 |         return result
 734 | 
 735 | 
 736 | def _get_fallback_holdings() -> list:
 737 |     """Return representative fallback holdings when EDGAR is unavailable."""
 738 |     return [
 739 |         {"name": "SPDR Gold Shares (GLD)", "value_usd": 8_500_000, "shares": 47200, "pct_of_portfolio": 34.0},
 740 |         {"name": "VanEck Gold Miners (GDX)", "value_usd": 6_200_000, "shares": 210000, "pct_of_portfolio": 24.8},
 741 |         {"name": "Barrick Gold Corp", "value_usd": 3_100_000, "shares": 175000, "pct_of_portfolio": 12.4},
 742 |         {"name": "Newmont Corp", "value_usd": 2_800_000, "shares": 72000, "pct_of_portfolio": 11.2},
 743 |         {"name": "Wheaton Precious Metals", "value_usd": 2_200_000, "shares": 45000, "pct_of_portfolio": 8.8},
 744 |         {"name": "Agnico Eagle Mines", "value_usd": 1_500_000, "shares": 19000, "pct_of_portfolio": 6.0},
 745 |         {"name": "Pan American Silver", "value_usd": 700_000, "shares": 52000, "pct_of_portfolio": 2.8},
 746 |     ]
 747 | 
 748 | 
 749 | def get_latest_score(app=None) -> dict:
 750 |     """
 751 |     Return latest score dict — from cache, DB, or fresh fetch.
 752 |     Recalculates if cache is >24h old.
 753 |     """
 754 |     # Check memory cache first
 755 |     cached_at = _cache["score_fetched_at"]
 756 |     if _cache["score"] and cached_at and (datetime.utcnow() - cached_at).seconds < 86400:
 757 |         return _cache["score"]
 758 | 
 759 |     # Try DB
 760 |     if app:
 761 |         with app.app_context():
 762 |             try:
 763 |                 import models
 764 |                 row = models.SchiffHypocrisy.query.order_by(
 765 |                     models.SchiffHypocrisy.calculated_at.desc()
 766 |                 ).first()
 767 |                 if row:
 768 |                     age = datetime.utcnow() - row.calculated_at
 769 |                     if age.days < 7:
 770 |                         score_dict = row.to_dict()
 771 |                         score_dict["label"] = score_label(row.score)
 772 |                         # Attach holdings from cache or fallback
 773 |                         score_dict["holdings"] = _cache.get("holdings") or _get_fallback_holdings()
 774 |                         score_dict["ytd"] = {"btc_ytd_pct": 0, "gold_ytd_pct": 0, "perf_gap": 0}
 775 |                         _cache["score"] = score_dict
 776 |                         _cache["score_fetched_at"] = datetime.utcnow()
 777 |                         return score_dict
 778 |             except Exception as e:
 779 |                 logger.warning("DB score read error: %s", e)
 780 | 
 781 |     # Fallback: synthetic score so page always renders
 782 |     return _synthetic_score()
 783 | 
 784 | 
 785 | def _synthetic_score() -> dict:
 786 |     """Return a plausible synthetic score when all data sources fail."""
 787 |     components = {
 788 |         "gold_holding_pct": 85.0,
 789 |         "anti_btc_tweet_rate": 95.0,
 790 |         "no_btc_holding_pct": 100.0,
 791 |         "gold_vs_btc_perf_gap": 60.0,
 792 |     }
 793 |     score = calculate_hypocrisy_score(components)
 794 |     return {
 795 |         "score": score,
 796 |         "label": score_label(score),
 797 |         "components": components,
 798 |         "gold_holdings_usd": 21_000_000,
 799 |         "total_aum_usd": 25_000_000,
 800 |         "btc_holdings_usd": 0,
 801 |         "filing_date": "2024-11-15",
 802 |         "filing_type": "13F-HR",
 803 |         "calculated_at": datetime.utcnow().isoformat(),
 804 |         "holdings": _get_fallback_holdings(),
 805 |         "ytd": {"btc_ytd_pct": 110.0, "gold_ytd_pct": 8.0, "perf_gap": 102.0},
 806 |         "entity_name": "Euro Pacific Asset Management",
 807 |         "data_sources": [],
 808 |         "_synthetic": True,
 809 |     }
 810 | 
 811 | 
 812 | def get_score_history(days: int = 90, app=None) -> list:
 813 |     """Return list of score dicts for the last N days."""
 814 |     if app:
 815 |         with app.app_context():
 816 |             try:
 817 |                 import models
 818 |                 cutoff = datetime.utcnow() - timedelta(days=days)
 819 |                 rows = models.SchiffHypocrisy.query.filter(
 820 |                     models.SchiffHypocrisy.calculated_at >= cutoff
 821 |                 ).order_by(models.SchiffHypocrisy.calculated_at.asc()).all()
 822 |                 return [r.to_dict() for r in rows]
 823 |             except Exception as e:
 824 |                 logger.warning("Score history query error: %s", e)
 825 | 
 826 |     # Fallback: generate synthetic 90-day history
 827 |     return _synthetic_history(days)
 828 | 
 829 | 
 830 | def _synthetic_history(days: int) -> list:
 831 |     """Generate plausible synthetic history for chart rendering."""
 832 |     import random
 833 |     random.seed(42)
 834 |     base_score = 87.0
 835 |     history = []
 836 |     for i in range(days):
 837 |         dt = datetime.utcnow() - timedelta(days=(days - i))
 838 |         jitter = random.uniform(-2.5, 2.5)
 839 |         score = round(min(max(base_score + jitter, 70), 100), 1)
 840 |         history.append({
 841 |             "score": score,
 842 |             "calculated_at": dt.isoformat(),
 843 |             "label": score_label(score),
 844 |         })
 845 |         base_score += random.uniform(-0.5, 0.5)
 846 |         base_score = min(max(base_score, 75), 98)
 847 |     return history
 848 | 
 849 | 
 850 | def get_statements(limit: int = 20, app=None) -> list:
 851 |     """Return recent public statements."""
 852 |     if app:
 853 |         with app.app_context():
 854 |             try:
 855 |                 import models
 856 |                 rows = models.SchiffStatement.query.filter_by(
 857 |                     anti_btc_score=1
 858 |                 ).order_by(
 859 |                     models.SchiffStatement.statement_date.desc()
 860 |                 ).limit(limit).all()
 861 |                 return [
 862 |                     {
 863 |                         "id": r.id,
 864 |                         "statement": r.statement,
 865 |                         "platform": r.platform,
 866 |                         "statement_date": r.statement_date.isoformat() if r.statement_date else None,
 867 |                         "source_url": r.source_url,
 868 |                     }
 869 |                     for r in rows
 870 |                 ]
 871 |             except Exception as e:
 872 |                 logger.warning("Statements query error: %s", e)
 873 | 
 874 |     # Fallback from seed
 875 |     return [
 876 |         {
 877 |             "id": i + 1,
 878 |             "statement": s["statement"],
 879 |             "platform": s["platform"],
 880 |             "statement_date": s["statement_date"],
 881 |             "source_url": s.get("source_url"),
 882 |         }
 883 |         for i, s in enumerate(SEED_STATEMENTS[:limit])
 884 |     ]
 885 | 
```

### File: cron/schiff_cron.py (68 lines)
```
   1 | """
   2 | schiff_cron.py — Daily Schiff-Bot score update cron job.
   3 | 
   4 | Run daily at 00:00 UTC:
   5 |   cd ~/protocol_pulse && python3 cron/schiff_cron.py
   6 | 
   7 | Safe to run multiple times (idempotent within same day if score already exists).
   8 | """
   9 | import sys
  10 | import os
  11 | import logging
  12 | 
  13 | # Allow running from repo root
  14 | sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  15 | 
  16 | logging.basicConfig(
  17 |     level=logging.INFO,
  18 |     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  19 | )
  20 | logger = logging.getLogger("schiff_cron")
  21 | 
  22 | 
  23 | def main():
  24 |     try:
  25 |         from core.app import app  # noqa: F401 — ensures Flask app context available
  26 |     except ImportError:
  27 |         try:
  28 |             from app import app  # fallback when run from core/
  29 |         except ImportError:
  30 |             logger.error("Cannot import Flask app — check working directory")
  31 |             sys.exit(1)
  32 | 
  33 |     try:
  34 |         from core.services.schiff_service import update_score, seed_statements
  35 |     except ImportError:
  36 |         from services.schiff_service import update_score, seed_statements
  37 | 
  38 |     # Seed statements on first run
  39 |     logger.info("Ensuring statements are seeded…")
  40 |     try:
  41 |         seed_statements(app)
  42 |     except Exception as e:
  43 |         logger.warning("Seed failed (non-fatal): %s", e)
  44 | 
  45 |     # Run score update
  46 |     logger.info("Running Schiff score update pipeline…")
  47 |     result = update_score(app=app)
  48 | 
  49 |     if result["success"]:
  50 |         score = result["score"]
  51 |         logger.info(
  52 |             "Score updated: %.1f/100 (%s) | Gold AUM: $%s | Filing: %s",
  53 |             score["score"],
  54 |             score["label"],
  55 |             f"{score.get('gold_holdings_usd', 0):,.0f}",
  56 |             score.get("filing_date", "unknown"),
  57 |         )
  58 |         sys.exit(0)
  59 |     else:
  60 |         logger.error("Score update FAILED: %s", result.get("error"))
  61 |         if result.get("score"):
  62 |             logger.warning("Serving stale cached score: %.1f", result["score"]["score"])
  63 |         sys.exit(1)
  64 | 
  65 | 
  66 | if __name__ == "__main__":
  67 |     main()
  68 | 
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
