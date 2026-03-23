# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pipeline-comprehensive-audit
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
### SECTION 1: CORRECTNESS

1. **Logic Errors and Edge Cases:**
   - In `overnight_render_loop.py`, the `run_render` function (lines 287-311) assumes that the `daily_producer.py` script will always produce output files. If no output is generated, the function logs a fatal error but does not handle it gracefully, which could lead to a loop without progress.
   - The `grade_with_gemini` function (lines 416-450) relies on a JSON response from an external API. If the response is malformed or missing expected fields, it could lead to a failure without a clear fallback mechanism.
   - In `video_pipeline_v3/daily_producer.py`, the `_post_render_health_check` function (lines 172-218) checks for video file existence and size but does not handle the case where the video file is corrupt or unreadable.

2. **Race Conditions:**
   - The use of `os.makedirs` without exception handling in multiple places (e.g., lines 37-38 in `overnight_render_loop.py`) could lead to race conditions if multiple processes attempt to create the same directory simultaneously.

3. **N+1 Query Problems:**
   - The code does not appear to have N+1 query problems as it primarily deals with file operations and subprocess calls rather than direct database queries.

4. **API Timeout and Bad Input:**
   - The `gemini_call` function (lines 253-284) implements retries with exponential backoff, which is good practice. However, it does not handle cases where the API consistently fails or returns unexpected data structures.

### SECTION 2: LAW COMPLIANCE

1. **Technology Stack Compliance:**
   - **COMPLIANT**: The code uses Python 3.12, Flask, and SQLAlchemy as specified.
   - **PARTIAL**: The code uses ElevenLabs TTS and other external services but does not explicitly handle rate limiting or quota exhaustion for these services.

2. **Database Indexing:**
   - **VIOLATION**: There is no evidence in the provided code that database queries on sort/filter columns have indexes applied.

3. **UI Technology Compliance:**
   - **COMPLIANT**: The code does not use Three.js, WebGL, or Canvas for UI animations, adhering to the specified technology stack.

### SECTION 3: SECURITY

1. **SQL Injection:**
   - **COMPLIANT**: The code does not contain raw SQL queries or user input reaching the database directly.

2. **Authentication Bypasses:**
   - **COMPLIANT**: The code does not include any routes or endpoints that suggest authentication bypasses.

3. **Rate Limiting Gaps:**
   - **VIOLATION**: The code does not implement rate limiting for API calls to external services, which could lead to exhaustion of paid API limits.

4. **Secrets in Code:**
   - **PARTIAL**: The code uses environment variables for API keys but does not ensure they are securely loaded or managed.

5. **Unvalidated User Input:**
   - **COMPLIANT**: There is no evidence of unvalidated user input reaching the filesystem or shell.

### SECTION 4: FRONTEND QUALITY

- **UI Layout and Responsiveness:**
  - **PARTIAL**: The code does not include frontend UI code, so compliance with UI layout specifications cannot be assessed.

- **Dynamic Values and Error Handling:**
  - **PARTIAL**: The code handles some dynamic values (e.g., BTC price) but lacks comprehensive error handling for UI-related operations.

### SECTION 5: BACKEND QUALITY

1. **DB Operations:**
   - **PARTIAL**: The code does not demonstrate explicit transaction management or rollback mechanisms for database writes.

2. **External API Calls:**
   - **COMPLIANT**: API calls have timeouts and retries, but graceful degradation is not fully implemented.

3. **Cron Job Failure Handling:**
   - **COMPLIANT**: The code includes mechanisms to restart processes if they fail, such as in the watchdog script.

4. **Memory Leaks:**
   - **COMPLIANT**: There is no evidence of memory leaks in the provided code.

5. **Logging:**
   - **COMPLIANT**: The code uses logging extensively to capture errors and operational information.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

- **Professional Features:**
  - **MISSING**: Advanced analytics and reporting features that provide insights into system performance and usage trends.
  - **MISSING**: Comprehensive monitoring and alerting system for real-time operational intelligence.
  - **MISSING**: User-friendly configuration and management interface for non-technical users.

### SECTION 7: SCORES

- Backend logic:    75/100
- Frontend/UI:      N/A (not applicable due to lack of UI code)
- Error handling:   70/100
- Security:         65/100
- Performance:      80/100
- Law compliance:   60/100
- World-class gap:  50/100
- OVERALL:          67/100

### SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Implement rate limiting for external API calls | `video_pipeline_v3/tts_engine.py:1082` | To prevent exhaustion of paid API limits.
P1 HIGH     | Ensure database indexing on sort/filter columns | N/A | To improve query performance and comply with specifications.
P2 MEDIUM   | Add comprehensive error handling for API responses |

## GROK — CYCLE 1 OUTPUT
### CODE REVIEW REPORT: PROTOCOL PULSE — CODE AUDIT PACKAGE

**Feature: pipeline-comprehensive-audit**  
**Branch: main**  
**Generated: 2026-03-23 00:01 UTC**  
**Purpose: Pre-merge quality gate**

I am conducting a forensic code review of the provided codebase for Protocol Pulse, focusing on correctness, compliance, security, quality, and production readiness. My analysis is brutally honest, citing specific line numbers and prioritizing actionable insights over diplomacy. Below is a structured evaluation across the required sections.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis (overnight_render_loop.py and daily_producer.py):**

1. **Overnight Render Loop (overnight_render_loop.py):**
   - **Purpose:** Automates video rendering in a perfection loop (max 8 iterations, 6 hours) until a Grade A is achieved or limits are hit.
   - **Flow Walkthrough:**
     - Startup checks (lines 92-167) validate environment (FFmpeg, tmux, API keys, TTS provider). Correct, but incomplete error handling for missing binaries could silently fail if `shutil.which` returns None (line 114).
     - Single render cycle (lines 489-584) runs iterations, calling `run_render`, `run_forensics`, and `grade_with_gemini`. Logic is sound, but there's a race condition risk in `write_heartbeat` (line 176-205) due to non-atomic updates of global counters (`_total_episodes`, `_consecutive_failures`) without locks, potentially corrupting counts under concurrent runs.
     - Gemini grading (lines 417-451) parses JSON responses but lacks robust fallback for malformed JSON beyond a basic retry (line 450). Edge case: if Gemini consistently returns invalid JSON, the loop skips iterations without a deeper fallback (line 549).
     - CC fix session (lines 454-486) launches tmux for fixes but doesn't validate if tmux actually starts, risking silent failure if tmux is misconfigured (line 472).
   - **Edge Cases:**
     - Empty video output (line 309) logs a failure but continues the loop without deeper recovery, risking max iterations without progress.
     - API timeouts in `gemini_call` (line 268) retry 3 times, but if all fail, it silently returns None, leading to skipped grading (line 513-549). No escalation mechanism for persistent API downtime.

2. **Daily Producer (daily_producer.py):**
   - **Purpose:** Builds daily Bitcoin video episodes from YouTube clips, host dialogue, and assembly.
   - **Flow Walkthrough:**
     - Pipeline steps (lines 265-1052) are sequential: BTC price fetch, channel scan, clip selection, extraction, script generation, TTS, assembly, and quality checks. Logic is correct for the main path, but silent failures in external API calls (e.g., BTC price fetch, line 99-116) default to "N/A" without alerting, masking data quality issues.
     - Clip extraction fallback (lines 396-453) retries with alternates if fewer than 5 clips pass quality, which is correct but risks infinite loops if no candidates remain (no hard cap on retries).
     - Quality gate (lines 923-975) computes a score and uploads if above threshold, but there's an N+1-like issue in repeated `ffprobe` calls (lines 845-861) per render without caching, slowing down large pipelines.
   - **Edge Cases:**
     - Empty video list (line 302) fails the pipeline correctly, but no recovery mechanism (e.g., fallback to cached data) exists for production resilience.
     - Nuclear re-encode for AV sync (lines 787-805) is a good fix but lacks validation that the re-encoded file isn't corrupt before replacing the original, risking data loss if `nuclear_tmp` is broken.

**Summary of Correctness Issues:**
- Logic is mostly sound for main flows, but silent failures (e.g., API timeouts, missing binaries) and race conditions (e.g., heartbeat counters) pose risks.
- Edge cases like persistent API failures or empty datasets aren't handled robustly, leading to potential production stalls.

---

### SECTION 2: LAW COMPLIANCE

**Note:** Since no specific governing laws were provided in the "GOVERNING LAWS" section of the audit request, I will assume compliance with general best practices and the implied requirements from the technology stack and purpose. If specific laws were intended, they should be explicitly listed for accurate assessment. Below, I evaluate against implied requirements from the spec.

- **Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM Compliance:** COMPLIANT
  - Code uses Python 3.12 features and Flask as implied by the stack (no explicit Flask version issues found). SQLite usage via SQLAlchemy is not directly visible in provided files but assumed compliant based on context.
- **Ubuntu 24.04 on Ultron Server Compliance:** COMPLIANT
  - Scripts like `overnight_render_loop.py` and `local_watchdog.py` use system commands (e.g., `tmux`, `ffmpeg`) compatible with Ubuntu 24.04, with checks for binary presence (line 113-119 in `overnight_render_loop.py`).
- **UI Animations (CSS/SVG only, no Three.js/WebGL/Canvas):** NOT APPLICABLE
  - No frontend UI code pr

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PIPELINE-COMPREHENSIVE-AUDIT — CYCLE 1
Generated: 2026-03-23 00:02
Models: gpt4o, grok (+1 failed — Gemini 2.5 Pro: 403 PERMISSION_DENIED, leaked API key)

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok  | Consensus |
|------------------|--------|--------|-------|-----------|
| Backend logic    | N/A    | 75/100 | ~72   | **73/100** |
| Frontend/UI      | N/A    | N/A    | N/A   | **N/A — no UI code reviewed** |
| Error handling   | N/A    | 70/100 | ~65   | **67/100** |
| Security         | N/A    | 65/100 | ~60   | **62/100** |
| Performance      | N/A    | 80/100 | ~75   | **77/100** |
| Law compliance   | N/A    | 60/100 | ~55   | **57/100** |
| World-class gap  | N/A    | 50/100 | ~50   | **50/100** |
| **OVERALL**      | N/A    | **67** | **~65** | **66/100** |

> ⚠️ **Confidence note:** Gemini failed with a leaked API key error. All consensus determinations are drawn from 2/3 models. Confidence is **moderate** — not high. Cycle 2 should include a functioning third model before merging to production.

---

## UNANIMOUS FINDINGS
*(Both available models agree — implement unconditionally)*

### U1 — No Rate Limiting on External API Calls
**What:** Neither model found any rate limiting or quota guards on external API calls — specifically Gemini API calls in `overnight_render_loop.py` and Telegram alerts in `local_watchdog.py`. A runaway failure loop or a misconfigured retry can exhaust paid quotas silently.
**Files/Lines:**
- `overnight_render_loop.py:266-284` — Gemini API call with retries but no per-hour/per-day cap
- `local_watchdog.py:207-221` — Telegram alerts fire without cooldown or deduplication
- `video_pipeline_v3/tts_engine.py:1082` (GPT-4o cited) — ElevenLabs TTS with no quota guard

**What to change:**
- Implement a token-bucket or sliding-window rate limiter for all external API call sites
- Add a minimum cooldown (e.g., 60s) and deduplication key for Telegram alert dispatch
- Track cumulative API usage per run and abort with a clear error if approaching known quota limits

---

### U2 — Silent Failures on API Timeouts / Malformed Responses
**What:** Both models flagged that when `gemini_call` exhausts its 3 retries it returns `None`, and this `None` propagates silently — grading is skipped, the loop continues, and the operator has no escalation signal. Similarly, malformed JSON from Gemini has no deep fallback.
**Files/Lines:**
- `overnight_render_loop.py:417-451` — `grade_with_gemini` JSON parse without structural validation
- `overnight_render_loop.py:513-549` — caller of grading skips iteration silently on `None` return
- `overnight_render_loop.py:253-284` — `gemini_call` returns `None` after all retries with no escalation

**What to change:**
- On exhausted retries, raise a typed exception (`GradingUnavailableError`) rather than returning `None`
- Validate required JSON keys before using the response; log the raw response on structural mismatch
- Escalate (Telegram alert + hard abort after N 

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: overnight_render_loop.py (726 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | overnight_render_loop.py - Autonomous video engine perfection loop.
   4 | Max 8 iterations, max 6 hours. Each: render -> forensics -> Gemini grade -> CC fix -> repeat.
   5 | Grade A = stop and lock WINNER_RECIPE.json.
   6 | 
   7 | Production modes:
   8 |   python3 overnight_render_loop.py              # single cycle (for cron)
   9 |   python3 overnight_render_loop.py --daemon     # continuous loop, runs at 08:00 ET daily
  10 |   python3 overnight_render_loop.py --dry-run    # startup checks only, no render
  11 |   python3 overnight_render_loop.py --help       # show args
  12 | 
  13 | Cron entry:
  14 |   0 12 * * * cd /home/ultron/protocol_pulse && python3 overnight_render_loop.py >> /tmp/overnight_loop.log 2>&1
  15 | """
  16 | import sys; sys.dont_write_bytecode=True
  17 | import os, sys, json, subprocess, time, re, urllib.request, argparse, logging, shutil, tempfile
  18 | import html as _html
  19 | import threading
  20 | from datetime import datetime, timezone, timedelta
  21 | from pathlib import Path
  22 | 
  23 | BASE = os.path.dirname(os.path.abspath(__file__))
  24 | PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
  25 | ENV_FILE = os.path.join(BASE, '.env')
  26 | LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
  27 | RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
  28 | HEARTBEAT_FILE = os.path.join(BASE, 'logs', 'loop_heartbeat.json')
  29 | ELEVENLABS_QUOTA_SENTINEL = os.path.join(BASE, 'logs', 'elevenlabs_quota_exhausted')
  30 | TTS_SCRIPT = os.path.join(PIPELINE, 'tts_local.py')
  31 | FORENSICS_TIMEOUT = 600  # 10-minute hard timeout for entire forensics
  32 | MAX_ITERATIONS = 8
  33 | MAX_HOURS = 6
  34 | RETRY_WAIT_SECONDS = 1800  # 30 minutes
  35 | MAX_ATTEMPTS_PER_CYCLE = 2
  36 | 
  37 | os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)
  38 | os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)
  39 | 
  40 | # ── Logging ───────────────────────────────────────────────────────
  41 | logger = logging.getLogger('overnight_loop')
  42 | if not logger.handlers:
  43 |     logger.setLevel(logging.DEBUG)
  44 |     _fmt = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  45 |     _sh = logging.StreamHandler(sys.stdout)
  46 |     _sh.setFormatter(_fmt)
  47 |     logger.addHandler(_sh)
  48 |     _fh = logging.FileHandler(LOG)
  49 |     _fh.setFormatter(_fmt)
  50 |     logger.addHandler(_fh)
  51 | 
  52 | 
  53 | def log(msg):
  54 |     """Backward-compat wrapper."""
  55 |     logger.info(msg)
  56 | 
  57 | 
  58 | def load_env():
  59 |     env = os.environ.copy()
  60 |     try:
  61 |         with open(ENV_FILE) as f:
  62 |             for line in f:
  63 |                 l = line.strip()
  64 |                 if l and not l.startswith('#') and '=' in l:
  65 |                     k, _, v = l.partition('=')
  66 |                     k = k.strip(); v = v.strip().strip("'").strip('"')
  67 |                     if k: env[k] = v
  68 |     except Exception as e:
  69 |         log(f"WARNING: .env load failed: {e}")
  70 |     return env
  71 | 
  72 | 
  73 | def run(cmd, timeout=7200, env=None):
  74 |     try:
  75 |         return subprocess.run(cmd, shell=True, capture_output=True, text=True,
  76 |                              timeout=timeout, env=env or load_env(), cwd=PIPELINE)
  77 |     except subprocess.TimeoutExpired:
  78 |         log(f"TIMEOUT after {timeout}s: {str(cmd)[:80]}")
  79 |         r = subprocess.CompletedProcess(cmd, returncode=-1)
  80 |         r.stdout = ""
  81 |         r.stderr = f"TIMEOUT after {timeout}s"
  82 |         return r
  83 |     except Exception as e:
  84 |         log(f"run() error: {e} cmd={str(cmd)[:80]}")
  85 |         r = subprocess.CompletedProcess(cmd, returncode=-1)
  86 |         r.stdout = ""
  87 |         r.stderr = str(e)
  88 |         return r
  89 | 
  90 | 
  91 | # ── Startup checks ────────────────────────────────────────────────
  92 | def startup_checks():
  93 |     """Verify environment before any render. Returns True if all pass."""
  94 |     ok = True
  95 | 
  96 |     # FFmpeg available
  97 |     try:
  98 |         r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
  99 |         if r.returncode != 0:
 100 |             log("STARTUP FAIL: ffmpeg returned non-zero")
 101 |             ok = False
 102 |         else:
 103 |             ver = r.stdout.split('\n')[0] if r.stdout else '?'
 104 |             log(f"FFmpeg: {ver}")
 105 |     except FileNotFoundError:
 106 |         log("STARTUP FAIL: ffmpeg not found in PATH")
 107 |         ok = False
 108 |     except Exception as e:
 109 |         log(f"STARTUP FAIL: ffmpeg check error: {e}")
 110 |         ok = False
 111 | 
 112 |     # tmux + claude binary validation (audit U2)
 113 |     for binary in ['tmux', 'claude']:
 114 |         if not shutil.which(binary):
 115 |             log(f"STARTUP FAIL: {binary} not found in PATH")
 116 |             ok = False
 117 |         else:
 118 |             log(f"{binary}: found")
 119 | 
 120 |     # Gemini API key check (audit UI-7)
 121 |     env = load_env()
 122 |     if not env.get('GEMINI_API_KEY', '').strip():
 123 |         log("STARTUP FAIL: GEMINI_API_KEY not set")
 124 |         ok = False
 125 |     else:
 126 |         log("GEMINI_API_KEY: present")
 127 | 
 128 |     # Python path includes pipeline
 129 |     if PIPELINE not in sys.path:
 130 |         sys.path.insert(0, PIPELINE)
 131 |     log(f"Pipeline dir: {PIPELINE} (exists={os.path.isdir(PIPELINE)})")
 132 |     if not os.path.isdir(PIPELINE):
 133 |         log("STARTUP FAIL: video_pipeline_v3 directory missing")
 134 |         ok = False
 135 | 
 136 |     # Output directory writable
 137 |     out_dir = os.path.join(PIPELINE, 'output')
 138 |     os.makedirs(out_dir, exist_ok=True)
 139 |     test_file = os.path.join(out_dir, '.write_test')
 140 |     try:
 141 |         with open(test_file, 'w') as f:
 142 |             f.write('ok')
 143 |         os.remove(test_file)
 144 |         log(f"Output dir writable: {out_dir}")
 145 |     except Exception as e:
 146 |         log(f"STARTUP FAIL: output dir not writable: {e}")
 147 |         ok = False
 148 | 
 149 |     # TTS provider check — use PIPELINE-derived path (audit M1)
 150 |     local_tts = os.path.exists(TTS_SCRIPT)
 151 |     elevenlabs_key = bool(env.get('ELEVENLABS_API_KEY', '').strip())
 152 |     quota_exhausted = os.path.exists(ELEVENLABS_QUOTA_SENTINEL)
 153 | 
 154 |     if local_tts:
 155 |         log("TTS provider: LOCAL (tts_local.py found)")
 156 |     elif elevenlabs_key and not quota_exhausted:
 157 |         log("TTS provider: ElevenLabs (API key present)")
 158 |     elif elevenlabs_key and quota_exhausted:
 159 |         log("WARNING: ElevenLabs key present but quota sentinel exists")
 160 |     else:
 161 |         log("WARNING: No TTS provider found (no local TTS, no ElevenLabs key)")
 162 | 
 163 |     if not local_tts and not elevenlabs_key:
 164 |         log("STARTUP FAIL: No TTS provider available")
 165 |         ok = False
 166 | 
 167 |     return ok
 168 | 
 169 | 
 170 | # ── Heartbeat ─────────────────────────────────────────────────────
 171 | _total_episodes = 0
 172 | _consecutive_failures = 0
 173 | 
 174 | 
 175 | def write_heartbeat(verdict, duration_s):
 176 |     """Write heartbeat JSON atomically after every cycle."""
 177 |     global _total_episodes, _consecutive_failures
 178 |     if verdict == "PASS":
 179 |         _total_episodes += 1
 180 |         _consecutive_failures = 0
 181 |     elif verdict == "ERROR":
 182 |         _consecutive_failures += 1
 183 |     elif verdict == "HOLD":
 184 |         _consecutive_failures += 1
 185 |     elif verdict == "DEGRADED":
 186 |         _total_episodes += 1
 187 |         _consecutive_failures = 0
 188 | 
 189 |     heartbeat = {
 190 |         "last_run": datetime.now(timezone.utc).isoformat(),
 191 |         "last_verdict": verdict,
 192 |         "last_duration": round(duration_s, 1),
 193 |         "total_episodes": _total_episodes,
 194 |         "consecutive_failures": _consecutive_failures,
 195 |     }
 196 |     try:
 197 |         # Atomic write via temp file + rename (audit UI-6)
 198 |         tmp_path = HEARTBEAT_FILE + '.tmp'
 199 |         with open(tmp_path, 'w') as f:
 200 |             json.dump(heartbeat, f, indent=2)
 201 |         os.replace(tmp_path, HEARTBEAT_FILE)
 202 |         log(f"Heartbeat written: {verdict} | failures={_consecutive_failures}")
 203 |     except Exception as e:
 204 |         log(f"WARNING: heartbeat write failed: {e}")
 205 | 
 206 |     # Telegram alert on 3+ consecutive failures
 207 |     if _consecutive_failures >= 3:
 208 |         send_telegram_alert(
 209 |             f"Protocol Pulse loop: {_consecutive_failures} consecutive failures\n"
 210 |             f"Last verdict: {verdict}\n"
 211 |             f"Time: {heartbeat['last_run']}"
 212 |         )
 213 | 
 214 | 
 215 | def send_telegram_alert(message):
 216 |     """Send alert via Telegram if bot token + chat ID are configured."""
 217 |     env = load_env()
 218 |     token = env.get('TELEGRAM_BOT_TOKEN', '').strip()
 219 |     chat_id = env.get('TELEGRAM_CHAT_ID', '').strip()
 220 |     if not token or not chat_id:
 221 |         log("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 222 |         return
 223 |     try:
 224 |         url = f"https://api.telegram.org/bot{token}/sendMessage"
 225 |         # Use plain text to avoid HTML injection from dynamic content (audit UI-3)
 226 |         payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
 227 |         req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
 228 |         with urllib.request.urlopen(req, timeout=15) as r:
 229 |             log(f"Telegram alert sent (status {r.status})")
 230 |     except Exception as e:
 231 |         log(f"Telegram alert failed: {e}")
 232 | 
 233 | 
 234 | # ── TTS provider awareness ────────────────────────────────────────
 235 | def check_tts_ready():
 236 |     """Check TTS availability before render. Returns (ready, provider_name)."""
 237 |     # Use PIPELINE-derived path (audit M1)
 238 |     local_tts = os.path.exists(TTS_SCRIPT)
 239 |     if local_tts:
 240 |         return True, "local (Kokoro/F5-TTS)"
 241 | 
 242 |     env = load_env()
 243 |     if not env.get('ELEVENLABS_API_KEY', '').strip():
 244 |         return False, "none"
 245 | 
 246 |     if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 247 |         log("ElevenLabs quota sentinel exists — skipping render")
 248 |         return False, "elevenlabs (quota exhausted)"
 249 | 
 250 |     return True, "ElevenLabs"
 251 | 
 252 | 
 253 | def gemini_call(prompt, max_tokens=8000):
 254 |     """Call Gemini API with retry + exponential backoff (audit U4)."""
 255 |     env = load_env()
 256 |     key = env.get('GEMINI_API_KEY', '')
 257 |     url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}'
 258 |     payload = {'contents': [{'parts': [{'text': prompt}]}],
 259 |                'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.05}}
 260 |     data = json.dumps(payload).encode()
 261 | 
 262 |     backoff = [5, 15, 45]
 263 |     last_err = None
 264 |     for attempt in range(3):
 265 |         try:
 266 |             req = urllib.request.Request(url, data=data,
 267 |                                         headers={'Content-Type': 'application/json'})
 268 |             with urllib.request.urlopen(req, timeout=120) as r:
 269 |                 d = json.loads(r.read())
 270 |                 parts = d['candidates'][0]['content'].get('parts', [])
 271 |                 return next((p['text'] for p in parts if 'text' in p), None)
 272 |         except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
 273 |             last_err = e
 274 |             if attempt < 2:
 275 |                 wait = backoff[attempt]
 276 |                 log(f"Gemini API attempt {attempt+1} failed ({type(e).__name__}: {e}), retrying in {wait}s...")
 277 |                 time.sleep(wait)
 278 |             else:
 279 |                 log(f"Gemini API all 3 attempts failed. Last error: {e}")
 280 |         except Exception as e:
 281 |             last_err = e
 282 |             log(f"Gemini API unexpected error: {e}")
 283 |             break
 284 |     return None
 285 | 
 286 | 
 287 | def run_render(iteration):
 288 |     log(f"RENDER START iteration {iteration}")
 289 |     run("rm -rf tts_cache/ && mkdir -p tts_cache/")
 290 |     log("TTS cache wiped")
 291 |     env = load_env()
 292 |     render_start = time.time()
 293 |     r = run("python3 daily_producer.py --skip-scan", timeout=7200, env=env)
 294 |     log(f"Render exit: {r.returncode}")
 295 |     import glob
 296 |     today = datetime.now().strftime('%Y-%m-%d')
 297 |     candidates = []
 298 |     for pat in [f'output/{today}/*.mp4']:  # today-only — no stale fallback
 299 |         for f in glob.glob(os.path.join(PIPELINE, pat)):
 300 |             if any(x in f for x in ['.bgl_audio', '.intro_mus', '.concat_raw', '.music_mixed', '.whoosh', '.norm']):
 301 |                 continue
 302 |             if not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh']):
 303 |                 # Only accept files produced after render started (audit U3)
 304 |                 if os.path.getmtime(f) >= render_start:
 305 |                     candidates.append((os.path.getmtime(f), f))
 306 |     candidates.sort(reverse=True)
 307 |     out = candidates[0][1] if candidates else None
 308 |     if out: log(f"Output: {out} ({os.path.getsize(out)//1048576}MB)")
 309 |     else: log("FATAL: no output file produced by this render")
 310 |     return out, r.stdout + r.stderr
 311 | 
 312 | 
 313 | def _run_forensics_inner(video):
 314 |     """Inner forensics logic — called within a thread timeout wrapper."""
 315 |     res = {}
 316 |     r = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{video}"')
 317 |     try:
 318 |         p = json.loads(r.stdout)
 319 |         fmt = p.get('format', {}); streams = p.get('streams', [])
 320 |         res['duration'] = float(fmt.get('duration', 0))
 321 |         res['filesize_mb'] = int(fmt.get('size', 0)) / 1048576
 322 |         v = next((s for s in streams if s.get('codec_type') == 'video'), {})
 323 |         a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
 324 |         res['width'] = v.get('width', 0); res['height'] = v.get('height', 0)
 325 |         fps_str = v.get('r_frame_rate', '0/1')
 326 |         if '/' in fps_str:
 327 |             num, den = fps_str.split('/', 1)
 328 |             res['fps'] = float(num) / float(den) if float(den) != 0 else 0
 329 |         else:
 330 |             res['fps'] = float(fps_str) if fps_str else 0
 331 |         res['vcodec'] = v.get('codec_name', '?'); res['acodec'] = a.get('codec_name', '?')
 332 |     except Exception as e:
 333 |         log(f"WARNING: ffprobe parse error: {e}")
 334 |     r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1', timeout=300)
 335 |     segs = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', r.stderr+r.stdout)
 336 |     dur = res.get('duration', 0)
 337 |     res['black_mid_count'] = len([(s,e,d) for s,e,d in segs if float(s)>2 and float(e)<dur-2])
 338 |     r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=120)
 339 |     out = r.stderr + r.stdout
 340 |     im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
 341 |     tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
 342 |     res['integrated_lufs'] = float(im.group(1)) if im else None
 343 |     res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
 344 |     # FIX: freeze threshold n=0.003 (was 0.001 — too sensitive for bg_loop transitions)
 345 |     r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.003:d=1.0" -an -f null - 2>&1', timeout=300)
 346 |     res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))
 347 | 
 348 |     # TTS ARTIFACT CHECK — run in isolated subprocess with hard 45s timeout
 349 |     # Prevents WhisperModel from blocking forensics pipeline
 350 |     tts_artifacts = []
 351 |     tmp_path = None
 352 |     try:
 353 |         tmp_fd, tmp_path = tempfile.mkstemp(suffix='.wav')
 354 |         os.close(tmp_fd)
 355 |         subprocess.run(['ffmpeg', '-y', '-i', video, '-t', '60', '-ar', '16000',
 356 |                  '-ac', '1', tmp_path], capture_output=True, timeout=30)
 357 |         checker = (
 358 |             "import sys, json\n"
 359 |             "from faster_whisper import WhisperModel\n"
 360 |             "model = WhisperModel('tiny', device='cpu', compute_type='int8')\n"
 361 |             "segs, _ = model.transcribe(sys.argv[1], language='en')\n"
 362 |             "t = ' '.join(s.text for s in segs).lower()\n"
 363 |             "bad = ['pause','breath','emphasis','break colon','slash','open bracket','close bracket']\n"
 364 |             "print(json.dumps([w for w in bad if w in t]))\n"
 365 |         )
 366 |         r = subprocess.run(['python3', '-c', checker, tmp_path],
 367 |                     capture_output=True, text=True, timeout=45)
 368 |         if r.returncode == 0 and r.stdout.strip():
 369 |             tts_artifacts = json.loads(r.stdout.strip())
 370 |     except Exception as _e:
 371 |         log(f"TTS artifact check skipped: {_e}")
 372 |     finally:
 373 |         # Guaranteed cleanup (audit M3)
 374 |         if tmp_path and os.path.exists(tmp_path):
 375 |             try:
 376 |                 os.unlink(tmp_path)
 377 |             except OSError:
 378 |                 pass
 379 |     res['tts_artifacts'] = tts_artifacts
 380 |     if tts_artifacts:
 381 |         log(f"TTS ARTIFACT ALERT: narrator reading markers aloud: {tts_artifacts}")
 382 |     log(f"Forensics: {res.get('duration',0):.0f}s {res.get('width')}x{res.get('height')} "
 383 |         f"LUFS={res.get('integrated_lufs')} TP={res.get('true_peak_dbfs')} "
 384 |         f"black={res.get('black_mid_count')} freeze={res.get('freeze_count')}")
 385 |     return res
 386 | 
 387 | 
 388 | def run_forensics(video):
 389 |     """Run forensics with a 10-minute hard thread timeout (task issue #1).
 390 |     If forensics hangs, returns {} so the loop can continue to grading."""
 391 |     log("Running forensics...")
 392 |     result_holder = [None]
 393 |     error_holder = [None]
 394 | 
 395 |     def _target():
 396 |         try:
 397 |             result_holder[0] = _run_forensics_inner(video)
 398 |         except Exception as e:
 399 |             error_holder[0] = e
 400 | 
 401 |     t = threading.Thread(target=_target, daemon=True)
 402 |     t.start()
 403 |     t.join(timeout=FORENSICS_TIMEOUT)
 404 | 
 405 |     if t.is_alive():
 406 |         log(f"WARNING: Forensics exceeded {FORENSICS_TIMEOUT}s hard timeout — returning empty result")
 407 |         return {}
 408 | 
 409 |     if error_holder[0]:
 410 |         log(f"WARNING: Forensics thread raised: {error_holder[0]}")
 411 |         return {}
 412 | 
 413 |     return result_holder[0] or {}
 414 | 
 415 | 
 416 | def grade_with_gemini(video, forensics, render_log):
 417 |     log("Calling Gemini for 24-dimension grade...")
 418 |     prompt = f"""Grade this Protocol Pulse Bitcoin show episode across 24 dimensions.
 419 | Only award Grade A if you would genuinely be proud to publish it as world-class Bitcoin media.
 420 | 
 421 | FORENSICS:
 422 | - Duration: {forensics.get('duration',0):.1f}s ({forensics.get('duration',0)/60:.1f}min)
 423 | - Resolution: {forensics.get('width')}x{forensics.get('height')} @ {forensics.get('fps',0):.1f}fps
 424 | - Codec: {forensics.get('vcodec')} + {forensics.get('acodec')}
 425 | - Loudness: {forensics.get('integrated_lufs')} LUFS (target -16 to -14)
 426 | - True Peak: {forensics.get('true_peak_dbfs')} dBFS (must be <= -1.0)
 427 | - Black frames (mid): {forensics.get('black_mid_count',0)} (0 = perfect)
 428 | - Freeze frames: {forensics.get('freeze_count',0)} (0 = perfect)
 429 | 
 430 | RENDER LOG (last 200 lines):
 431 | {chr(10).join(render_log.splitlines()[-200:])}
 432 | 
 433 | RUBRIC (24 dimensions, Grade A = score >= 88, zero critical failures):
 434 | Technical (40%): duration, resolution, fps, loudness, true_peak, black_frames, silence, freezes, codec, file_integrity
 435 | Content (35%): clip_relevance, script_quality, cold_open, narrative_arc, host_authenticity, episode_title, no_filler, timeliness
 436 | Production (25%): music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing
 437 | 
 438 | Respond ONLY with raw JSON (no fences):
 439 | {{"grade":"A|B|C|D|F","overall_score":0-100,"broadcast_ready":true|false,
 440 | "dimensions":{{"duration_check":{{"score":0-10,"note":""}},"resolution_check":{{"score":0-10,"note":""}},"framerate_check":{{"score":0-10,"note":""}},"loudness_check":{{"score":0-10,"note":""}},"true_peak_check":{{"score":0-10,"note":""}},"black_frames_check":{{"score":0-10,"note":""}},"silence_check":{{"score":0-10,"note":""}},"freeze_check":{{"score":0-10,"note":""}},"codec_check":{{"score":0-10,"note":""}},"file_integrity_check":{{"score":0-10,"note":""}},"clip_relevance":{{"score":0-10,"note":""}},"script_quality":{{"score":0-10,"note":""}},"cold_open_hook":{{"score":0-10,"note":""}},"narrative_arc":{{"score":0-10,"note":""}},"host_authenticity":{{"score":0-10,"note":""}},"episode_title":{{"score":0-10,"note":""}},"no_filler":{{"score":0-10,"note":""}},"timeliness":{{"score":0-10,"note":""}},"music_mix":{{"score":0-10,"note":""}},"transitions":{{"score":0-10,"note":""}},"visual_polish":{{"score":0-10,"note":""}},"no_artifacts":{{"score":0-10,"note":""}},"audio_quality":{{"score":0-10,"note":""}},"pacing":{{"score":0-10,"note":""}}}},
 441 | "critical_failures":[],"warnings":[],"strengths":[],"targeted_fix_instructions":"Precise instructions for CC session to fix only failing dimensions - file, function, lines.",
 442 | "verdict":"One punchy sentence"}}"""
 443 |     text = gemini_call(prompt, 8000)
 444 |     if not text: return None
 445 |     clean = text.strip()
 446 |     for fence in ['```json', '```']:
 447 |         if fence in clean:
 448 |             clean = clean.split(fence)[1].split('```')[0].strip()
 449 |     try: return json.loads(clean)
 450 |     except json.JSONDecodeError as e: log(f"JSON parse fail: {e} — {clean[:200]}"); return None
 451 | 
 452 | 
 453 | def fire_cc_fix(iteration, grade_result):
 454 |     failures = grade_result.get('critical_failures', [])
 455 |     dims = grade_result.get('dimensions', {})
 456 |     failing = [(k, v['score'], v.get('note','')) for k,v in dims.items()
 457 |                if isinstance(v.get('score'), int) and v['score'] < 7]
 458 |     failing.sort(key=lambda x: x[1])
 459 |     prompt = f"""# PIPELINE FIX - ITERATION {iteration} - GRADE {grade_result.get('grade')} ({grade_result.get('overall_score')}/100)
 460 | VERDICT: {grade_result.get('verdict','')}
 461 | CRITICAL FAILURES: {chr(10).join(f'- {f}' for f in failures) or 'None'}
 462 | FAILING DIMS (<7/10): {chr(10).join(f'- {k}: {s}/10 - {n[:80]}' for k,s,n in failing[:8]) or 'None'}
 463 | FIX INSTRUCTIONS: {grade_result.get('targeted_fix_instructions','')}
 464 | 
 465 | Read PIPELINE_LAWS.md first. Fix ONLY failing dimensions. Run regression_test.sh after every change.
 466 | Commit: git add -A && git commit -m "fix(pipeline): iter{iteration}" && git push"""
 467 |     pf = os.path.join(PIPELINE, f'logs/cc_fix_iter{iteration}.md')
 468 |     with open(pf, 'w') as f: f.write(prompt)
 469 |     sn = f'fix_iter{iteration}'
 470 |     subprocess.run(f'tmux kill-session -t {sn} 2>/dev/null', shell=True)
 471 |     subprocess.run(f'tmux new-session -d -s {sn}', shell=True)
 472 |     subprocess.run(f"tmux send-keys -t {sn} 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter", shell=True)
 473 |     time.sleep(10)
 474 |     subprocess.run(f"tmux send-keys -t {sn} \"$(cat {pf})\" Enter", shell=True)
 475 |     log(f"CC session {sn} launched")
 476 |     deadline = time.time() + 2700
 477 |     while time.time() < deadline:
 478 |         time.sleep(60)
 479 |         r = subprocess.run(f'tmux has-session -t {sn} 2>/dev/null', shell=True)
 480 |         if r.returncode != 0: log("CC session ended"); break
 481 |         log(f"CC running... {int((deadline-time.time())/60)}min left")
 482 |     # Kill orphaned tmux session on timeout (audit U2)
 483 |     subprocess.run(['tmux', 'kill-session', '-t', sn], capture_output=True)
 484 |     log(f"CC session {sn} cleaned up")
 485 |     time.sleep(30)
 486 | 
 487 | 
 488 | def run_single_render():
 489 |     """Execute one full perfection loop (up to MAX_ITERATIONS). Returns verdict string."""
 490 |     log("="*60)
 491 |     log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
 492 |     log("="*60)
 493 |     start = time.time()
 494 |     grade_result = {}
 495 |     final_verdict = "ERROR"
 496 | 
 497 |     for iteration in range(1, MAX_ITERATIONS+1):
 498 |         if (time.time()-start)/3600 >= MAX_HOURS:
 499 |             log(f"TIME LIMIT ({MAX_HOURS}h). Stopping."); break
 500 |         log(f"\n{'='*60}\nITERATION {iteration}/{MAX_ITERATIONS}\n{'='*60}")
 501 |         video, rlog = run_render(iteration)
 502 |         if not video:
 503 |             log("Render failed, skipping"); time.sleep(60); continue
 504 |         # Forensics with 10-min hard timeout (task issue #1)
 505 |         forensics = run_forensics(video)
 506 |         # Grade ALWAYS fires after forensics — even if forensics returned {} (task issue main)
 507 |         try:
 508 |             grade_result = grade_with_gemini(video, forensics, rlog)
 509 |         except Exception as _ge:
 510 |             log(f"Grading failed (non-fatal): {_ge}")
 511 |             grade_result = None
 512 |         if not grade_result:
 513 |             # Fallback: run gemini_grade.py directly as subprocess (task issue #2)
 514 |             log("grade_with_gemini failed — running gemini_grade.py directly")
 515 |             try:
 516 |                 r = subprocess.run(
 517 |                     ["python3", "gemini_grade.py", video],
 518 |                     capture_output=True, text=True, timeout=300, cwd=PIPELINE
 519 |                 )
 520 |                 # Parse both PASS and FAIL lines
 521 |                 if "GRADE_" in (r.stdout or ''):
 522 |                     for line in r.stdout.splitlines():
 523 |                         if line.startswith("GRADE_"):
 524 |                             # Format: GRADE_A_PASS|95|path|verdict or GRADE_B_FAIL|72|path|verdict
 525 |                             parts = line.split("|", 3)  # maxsplit=3 (audit M4)
 526 |                             if len(parts) < 2:
 527 |                                 log(f"Unexpected grade line format: {line!r}")
 528 |                                 continue
 529 |                             grade_tag = parts[0]  # e.g. GRADE_A_PASS
 530 |                             tag_parts = grade_tag.split("_")
 531 |                             grade_letter = tag_parts[1] if len(tag_parts) > 1 else "F"
 532 |                             try:
 533 |                                 score_val = int(parts[1])
 534 |                             except (ValueError, IndexError):
 535 |                                 score_val = 0
 536 |                             grade_result = {
 537 |                                 "grade": grade_letter,
 538 |                                 "overall_score": score_val,
 539 |                                 "broadcast_ready": grade_letter == "A",
 540 |                                 "verdict": parts[3] if len(parts) > 3 else "",
 541 |                                 "dimensions": {},
 542 |                                 "critical_failures": []
 543 |                             }
 544 |                             log(f"Fallback grade: {grade_letter} ({score_val}/100)")
 545 |                             break
 546 |             except Exception as _ge2:
 547 |                 log(f"Fallback grading also failed: {_ge2}")
 548 |             if not grade_result:
 549 |                 log("All grading failed, skipping iteration"); continue
 550 |         gf = os.path.join(PIPELINE, f'logs/grade_iter{iteration}.json')
 551 |         with open(gf, 'w') as f: json.dump(grade_result, f, indent=2)
 552 |         grade = grade_result.get('grade','F')
 553 |         score = grade_result.get('overall_score', 0)
 554 |         broadcast = grade_result.get('broadcast_ready', False)
 555 |         # Explicit GRADE: logging after every grade result (task issue #4)
 556 |         log(f"GRADE: {grade} | SCORE: {score}/100 | BROADCAST: {broadcast}")
 557 |         log(f"GRADE: iteration={iteration} grade={grade} score={score} broadcast={broadcast}")
 558 |         log(f"VERDICT: {grade_result.get('verdict','')}")
 559 |         for dim, data in grade_result.get('dimensions',{}).items():
 560 |             s = data.get('score','?')
 561 |             flag = ' ✓' if isinstance(s,int) and s>=8 else (' !!' if isinstance(s,int) and s<6 else '')
 562 |             log(f"  {dim:30s} {s}/10{flag}")
 563 |         if grade == 'A' and broadcast and score >= 88:
 564 |             log("*** GRADE A — LOCKING WINNER RECIPE ***")
 565 |             recipe = {'winner': True, 'iteration': iteration, 'timestamp': datetime.now().isoformat(),
 566 |                      'video': video, 'grade': grade, 'score': score,
 567 |                      'verdict': grade_result.get('verdict'), 'dimensions': grade_result.get('dimensions',{})}
 568 |             with open(RECIPE_FILE, 'w') as f: json.dump(recipe, f, indent=2)
 569 |             log(f"WINNER: {RECIPE_FILE}")
 570 |             final_verdict = "PASS"
 571 |             break
 572 |         elif grade in ('B', 'C') and broadcast:
 573 |             final_verdict = "DEGRADED"
 574 |         log(f"Grade {grade} - firing CC fix...")
 575 |         fire_cc_fix(iteration, grade_result)
 576 |     else:
 577 |         log("Max iterations reached without Grade A")
 578 |         with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
 579 |             json.dump({'final_grade': grade_result}, f, indent=2)
 580 |         if final_verdict == "ERROR":
 581 |             final_verdict = "HOLD"
 582 | 
 583 |     log("OVERNIGHT LOOP COMPLETE")
 584 |     return final_verdict
 585 | 
 586 | 
 587 | def run_cycle():
 588 |     """Run a single render cycle with exception handling and retry logic."""
 589 |     cycle_start = time.time()
 590 | 
 591 |     # Check TTS before render
 592 |     tts_ready, tts_provider = check_tts_ready()
 593 |     log(f"TTS provider: {tts_provider}")
 594 |     if not tts_ready:
 595 |         log(f"[loop] TTS not available ({tts_provider}) — skipping cycle")
 596 |         write_heartbeat("ERROR", time.time() - cycle_start)
 597 |         return
 598 | 
 599 |     for attempt in range(1, MAX_ATTEMPTS_PER_CYCLE + 1):
 600 |         log(f"[loop] Attempt {attempt}/{MAX_ATTEMPTS_PER_CYCLE}")
 601 |         try:
 602 |             verdict = run_single_render()
 603 |         except Exception as e:
 604 |             logger.error(f"[loop] Render cycle exception: {e}", exc_info=True)
 605 |             verdict = "ERROR"
 606 | 
 607 |         if verdict in ("PASS", "DEGRADED"):
 608 |             write_heartbeat(verdict, time.time() - cycle_start)
 609 |             return
 610 | 
 611 |         # Failed — retry logic
 612 |         if attempt < MAX_ATTEMPTS_PER_CYCLE:
 613 |             log(f"[loop] Attempt {attempt} failed ({verdict}), waiting {RETRY_WAIT_SECONDS//60}min before retry...")
 614 |             time.sleep(RETRY_WAIT_SECONDS)
 615 |         else:
 616 |             log(f"[loop] All {MAX_ATTEMPTS_PER_CYCLE} attempts failed — waiting for next scheduled cycle")
 617 | 
 618 |     write_heartbeat(verdict, time.time() - cycle_start)
 619 | 
 620 | 
 621 | # ── Daemon mode ───────────────────────────────────────────────────
 622 | def sleep_until_next_8am_et():
 623 |     """Sleep until next 08:00 ET (12:00 UTC or 11:00 UTC during DST)."""
 624 |     from zoneinfo import ZoneInfo
 625 |     et = ZoneInfo("America/New_York")
 626 |     now = datetime.now(et)
 627 |     target = now.replace(hour=8, minute=0, second=0, microsecond=0)
 628 |     if target <= now:
 629 |         target += timedelta(days=1)
 630 |     wait = (target - now).total_seconds()
 631 |     log(f"[daemon] Sleeping {wait/3600:.1f}h until {target.isoformat()}")
 632 |     time.sleep(wait)
 633 | 
 634 | 
 635 | PIDFILE = os.path.join(BASE, 'logs', 'render_loop.pid')
 636 | 
 637 | 
 638 | def _acquire_singleton():
 639 |     """Prevent duplicate render loop instances. Checks for stale PID (audit UI-4)."""
 640 |     import fcntl
 641 |     # Check for stale PID before locking
 642 |     if os.path.exists(PIDFILE):
 643 |         try:
 644 |             with open(PIDFILE) as f:
 645 |                 old_pid = int(f.read().strip())
 646 |             os.kill(old_pid, 0)  # check if process is alive
 647 |         except (ValueError, ProcessLookupError, PermissionError):
 648 |             # Process is dead — stale lockfile, remove it
 649 |             log(f"Removing stale PID file (pid {old_pid if 'old_pid' in dir() else '?'} not running)")
 650 |             try:
 651 |                 os.remove(PIDFILE)
 652 |             except OSError:
 653 |                 pass
 654 |         except OSError:
 655 |             pass  # Process exists, let flock handle it
 656 | 
 657 |     fp = open(PIDFILE, 'w')
 658 |     try:
 659 |         fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
 660 |     except OSError:
 661 |         log("ABORT: Another render loop instance is already running (pidfile locked)")
 662 |         sys.exit(1)
 663 |     fp.write(str(os.getpid()))
 664 |     fp.flush()
 665 |     # Keep fp open to hold the lock — do NOT close or the lock releases
 666 |     return fp
 667 | 
 668 | 
 669 | def main():
 670 |     parser = argparse.ArgumentParser(
 671 |         description="Protocol Pulse overnight render loop — production hardened",
 672 |         formatter_class=argparse.RawDescriptionHelpFormatter,
 673 |         epilog=(
 674 |             "Examples:\n"
 675 |             "  python3 overnight_render_loop.py              # single cycle\n"
 676 |             "  python3 overnight_render_loop.py --daemon      # continuous, 08:00 ET daily\n"
 677 |             "  python3 overnight_render_loop.py --dry-run     # startup checks only\n"
 678 |         )
 679 |     )
 680 |     parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (loop at 08:00 ET daily)")
 681 |     parser.add_argument("--dry-run", action="store_true", help="Run startup checks only, no render")
 682 |     args = parser.parse_args()
 683 | 
 684 |     # Singleton guard — prevent duplicate instances
 685 |     _lock_fp = _acquire_singleton()
 686 | 
 687 |     # Startup checks always run
 688 |     log("="*60)
 689 |     log("STARTUP CHECKS")
 690 |     log("="*60)
 691 |     if not startup_checks():
 692 |         log("STARTUP CHECKS FAILED — exiting")
 693 |         sys.exit(1)
 694 |     log("All startup checks passed")
 695 | 
 696 |     if args.dry_run:
 697 |         log("--dry-run mode: startup checks passed, exiting")
 698 |         sys.exit(0)
 699 | 
 700 |     # Load existing heartbeat state
 701 |     global _total_episodes, _consecutive_failures
 702 |     try:
 703 |         with open(HEARTBEAT_FILE) as f:
 704 |             hb = json.load(f)
 705 |             _total_episodes = hb.get('total_episodes', 0)
 706 |             _consecutive_failures = hb.get('consecutive_failures', 0)
 707 |         log(f"Heartbeat loaded: episodes={_total_episodes}, consecutive_failures={_consecutive_failures}")
 708 |     except (FileNotFoundError, json.JSONDecodeError):
 709 |         pass
 710 | 
 711 |     if args.daemon:
 712 |         log("DAEMON MODE — will loop at 08:00 ET daily")
 713 |         while True:
 714 |             verdict = run_cycle() or "DEGRADED"
 715 |             if verdict == "PASS":
 716 |                 sleep_until_next_8am_et()
 717 |             else:
 718 |                 log("[daemon] No Grade A — retrying in 30 min")
 719 |                 time.sleep(1800)
 720 |     else:
 721 |         run_cycle()
 722 | 
 723 | 
 724 | if __name__ == '__main__':
 725 |     main()
 726 | 
```

### File: video_pipeline_v3/daily_producer.py (1133 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Daily Pulse Check Producer V5 — clip-first pipeline.
   3 | 
   4 | Real YouTube clips from partner channels, host dialogue around them,
   5 | music integration, cold open, avatar shorts.
   6 | 
   7 | Usage:
   8 |   python3 daily_producer.py               # Full daily episode
   9 |   python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  10 |   python3 daily_producer.py --skip-scan   # Use cached transcripts only
  11 |   python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
  12 | """
  13 | import sys; sys.dont_write_bytecode=True
  14 | import argparse
  15 | import json
  16 | import logging
  17 | import os
  18 | import shutil
  19 | import subprocess
  20 | import sys
  21 | import time
  22 | from datetime import datetime, timezone
  23 | 
  24 | BASE = os.path.dirname(os.path.abspath(__file__))
  25 | sys.path.insert(0, BASE)
  26 | 
  27 | from channel_scanner import scan_all_channels
  28 | from clip_selector import select_clips
  29 | from clip_extractor import extract_all, extract_montage_all, check_av_sync
  30 | from script_writer import generate_from_clips
  31 | from tts_engine import generate_dialogue_audio
  32 | from assembler import assemble_episode, verify_video
  33 | from shorts_cutter import generate_shorts
  34 | from thumbnail_gen import generate_thumbnail
  35 | from chapters import generate_chapters
  36 | from podcast_feed import extract_podcast_audio, generate_rss_item
  37 | from newsletter_embed import generate_email_html, save_newsletter_html
  38 | from music import ensure_music_dir, has_music, has_intro, has_outro
  39 | from utils.feature_flags import is_enabled, load_all as load_flags
  40 | from utils.quality_gate import compute_quality_score, should_upload, format_score_report
  41 | from utils.telegram_alerts import (
  42 |     alert_pipeline_start, alert_pipeline_success,
  43 |     alert_pipeline_failure, alert_quality_hold, alert_upload_success,
  44 | )
  45 | 
  46 | # Setup logging
  47 | logging.basicConfig(
  48 |     level=logging.INFO,
  49 |     format="%(message)s",
  50 | )
  51 | logger = logging.getLogger("Producer")
  52 | 
  53 | 
  54 | # ---------------------------------------------------------------------------
  55 | # Per-Render Context File (consumed by watchdog for CC repair specs)
  56 | # ---------------------------------------------------------------------------
  57 | 
  58 | def write_render_context(step, status, error=None, **extra):
  59 |     """Write/update /tmp/render_context_YYYYMMDD.json for watchdog consumption.
  60 | 
  61 |     Called after every pipeline step completes or fails. The watchdog reads this
  62 |     file to give Claude Code full context about what was being built when a crash
  63 |     occurred. See QWEN_CONTEXT_BIBLE.md Section 7.
  64 |     """
  65 |     ctx_path = f"/tmp/render_context_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
  66 |     try:
  67 |         with open(ctx_path) as f:
  68 |             ctx = json.load(f)
  69 |     except Exception:
  70 |         ctx = {
  71 |             "episode_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
  72 |             "steps_completed": [],
  73 |             "steps_failed": [],
  74 |             "render_start_time": datetime.now(timezone.utc).isoformat(),
  75 |         }
  76 | 
  77 |     if status == "ok":
  78 |         if step not in ctx["steps_completed"]:
  79 |             ctx["steps_completed"].append(step)
  80 |     else:
  81 |         ctx["steps_failed"].append({
  82 |             "step": step,
  83 |             "error": str(error)[:500],
  84 |             "timestamp": datetime.now(timezone.utc).isoformat(),
  85 |         })
  86 | 
  87 |     # Merge any extra context (episode_title, btc_price, clips, mood, etc.)
  88 |     for k, v in extra.items():
  89 |         ctx[k] = v
  90 | 
  91 |     try:
  92 |         with open(ctx_path, "w") as f:
  93 |             json.dump(ctx, f, indent=2)
  94 |     except Exception as e:
  95 |         logger.warning(f"write_render_context failed: {e}")
  96 | 
  97 | 
  98 | def get_btc_price() -> str:
  99 |     """Fetch current BTC price (CoinGecko primary + mempool.space fallback)."""
 100 |     try:
 101 |         import requests
 102 |         r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
 103 |         if r.status_code == 200:
 104 |             usd = r.json()["bitcoin"]["usd"]
 105 |             return f"${usd:,.0f}"
 106 |     except Exception:
 107 |         pass
 108 |     try:
 109 |         import requests
 110 |         r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
 111 |         if r.status_code == 200:
 112 |             usd = r.json().get("USD", 0)
 113 |             return f"${usd:,.0f}"
 114 |     except Exception:
 115 |         pass
 116 |     return "$N/A"  # Fallback - no hardcoded stale price
 117 | 
 118 | 
 119 | def _build_fast_test_script(clips_info: dict, btc_price: str) -> dict:
 120 |     """Build a minimal hardcoded script for fast-test mode (no Claude API call)."""
 121 |     dialogue = []
 122 |     # Cold open — PBX-only (host 2) per SOLO HOST law
 123 |     dialogue.append({
 124 |         "host": 2, "type": "cold_open",
 125 |         "text": f"[COLD_OPEN] Bitcoin at {btc_price}. Let's get into today's pulse check.",
 126 |     })
 127 |     # For each clip, add a setup + clip marker + react
 128 |     for rank, info in sorted(clips_info.items()):
 129 |         channel = info.get("channel", "Unknown")
 130 |         dialogue.append({
 131 |             "host": 2, "type": "setup",
 132 |             "text": f"[NARRATION] Here's what {channel} had to say.",
 133 |         })
 134 |         dialogue.append({
 135 |             "host": "CLIP", "type": "clip",
 136 |             "rank": rank, "source_id": info.get("video_id", ""),
 137 |         })
 138 |         dialogue.append({
 139 |             "host": 2, "type": "react",
 140 |             "text": "[NARRATION] Interesting take. Let's keep moving.",
 141 |         })
 142 |     # Wrap
 143 |     dialogue.append({
 144 |         "host": 2, "type": "wrap",
 145 |         "text": "[WARM] That's the pulse check for today. Stay sovereign.",
 146 |     })
 147 |     return {
 148 |         "episode_title": f"Fast Test — {btc_price}",
 149 |         "dialogue": dialogue,
 150 |         "thumbnail": {"headline": "FAST TEST", "subtext": btc_price},
 151 |     }
 152 | 
 153 | 
 154 | def _send_resend_alert(subject: str, body: str):
 155 |     """Send a non-blocking email alert via Resend."""
 156 |     try:
 157 |         import resend
 158 |         resend.api_key = os.environ.get("RESEND_API_KEY", "")
 159 |         if not resend.api_key:
 160 |             logger.warning("RESEND_API_KEY not set — skipping email alert")
 161 |             return
 162 |         resend.Emails.send({
 163 |             "from": "pulse@protocolpulse.io",
 164 |             "to": ["contact@consensusprotocol.org"],
 165 |             "subject": subject,
 166 |             "html": f"<pre>{body}</pre>",
 167 |         })
 168 |     except Exception as e:
 169 |         logger.warning(f"Resend alert failed: {e}")
 170 | 
 171 | 
 172 | def _post_render_health_check(video_path: str) -> tuple[bool, list[str]]:
 173 |     """Verify rendered video meets quality thresholds.
 174 | 
 175 |     Returns (passed, errors).
 176 |     """
 177 |     errors = []
 178 |     if not os.path.exists(video_path):
 179 |         return False, ["Video file does not exist"]
 180 | 
 181 |     # File size > 50MB
 182 |     size_mb = os.path.getsize(video_path) / (1024 * 1024)
 183 |     if size_mb < 50:
 184 |         errors.append(f"File size {size_mb:.1f}MB < 50MB minimum")
 185 | 
 186 |     # ffprobe checks
 187 |     try:
 188 |         probe = subprocess.run(
 189 |             ["ffprobe", "-v", "quiet", "-print_format", "json",
 190 |              "-show_format", "-show_streams", video_path],
 191 |             capture_output=True, text=True, timeout=30,
 192 |         )
 193 |         info = json.loads(probe.stdout)
 194 |         fmt = info.get("format", {})
 195 |         streams = info.get("streams", [])
 196 | 
 197 |         # Duration 480-900s (PIPELINE_LAWS: 8-15 min)
 198 |         duration = float(fmt.get("duration", 0))
 199 |         if duration < 480 or duration > 900:
 200 |             errors.append(f"Duration {duration:.0f}s outside 480-900s range (8-15 min law)")
 201 | 
 202 |         # Audio stream present
 203 |         audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
 204 |         if not audio_streams:
 205 |             errors.append("No audio stream found")
 206 |     except Exception as e:
 207 |         errors.append(f"ffprobe failed: {e}")
 208 | 
 209 |     passed = len(errors) == 0
 210 |     if not passed:
 211 |         logger.critical(f"POST-RENDER HEALTH CHECK FAILED: {errors}")
 212 |         _send_resend_alert(
 213 |             "CRITICAL: Pulse Check render failed health check",
 214 |             f"Video: {video_path}\nErrors:\n" + "\n".join(f"  - {e}" for e in errors),
 215 |         )
 216 |     return passed, errors
 217 | 
 218 | 
 219 | def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
 220 |                  fast_test: bool = False) -> bool:
 221 |     # Fast test implies test + skip-scan
 222 |     if fast_test:
 223 |         test_mode = True
 224 |         skip_scan = True
 225 | 
 226 |     # Wipe TTS cache before each run to prevent stale audio
 227 |     tts_cache = os.path.join(BASE, "tts_cache")
 228 |     shutil.rmtree(tts_cache, ignore_errors=True)
 229 |     os.makedirs(tts_cache, exist_ok=True)
 230 |     logger.info("TTS cache wiped")
 231 | 
 232 |     ts = datetime.now(timezone.utc)
 233 |     date_str = ts.strftime("%Y%m%d")
 234 |     time_str = ts.strftime("%Y%m%d_%H%M%S")
 235 | 
 236 |     if test_mode:
 237 |         run_dir = os.path.join(BASE, "output", f"test_{time_str}")
 238 |     else:
 239 |         run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))
 240 | 
 241 |     os.makedirs(run_dir, exist_ok=True)
 242 |     final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
 243 |     timing = {}
 244 |     t_pipeline_start = time.time()
 245 | 
 246 |     # Ensure music directory exists
 247 |     ensure_music_dir()
 248 | 
 249 |     # Log feature flags at startup
 250 |     flags = load_flags()
 251 |     logger.info(f"Feature flags: {json.dumps(flags)}")
 252 | 
 253 |     # Telegram alert at pipeline start
 254 |     if is_enabled("telegram_alerts"):
 255 |         alert_pipeline_start(date_str, test_mode)
 256 | 
 257 |     print("\n" + "=" * 70)
 258 |     print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
 259 |     mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
 260 |     print(f"  {mode_label}Run {time_str}")
 261 |     print(f"  Output: {run_dir}")
 262 |     print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
 263 |     print("=" * 70)
 264 | 
 265 |     # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
 266 |     print("\n[STEP 1/12] FETCHING BTC PRICE...")
 267 |     t0 = time.time()
 268 |     btc_price = get_btc_price()
 269 |     print(f"  BTC: {btc_price}")
 270 |     timing["1_price"] = round(time.time() - t0, 2)
 271 |     write_render_context(1, "ok", btc_price=btc_price)
 272 | 
 273 |     # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
 274 |     print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
 275 |     t0 = time.time()
 276 |     if skip_scan:
 277 |         # Load cached transcripts from transcript dir
 278 |         import glob
 279 |         transcript_dir = os.path.join(BASE, "transcripts")
 280 |         videos = []
 281 |         for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:60]:
 282 |             with open(tf) as f:
 283 |                 data = json.load(f)
 284 |                 videos.append({
 285 |                     "video_id": data.get("video_id", ""),
 286 |                     "title": data.get("title", ""),
 287 |                     "channel": data.get("channel", ""),
 288 |                     "duration": data.get("duration", 0),
 289 |                     "upload_date": "",
 290 |                     "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
 291 |                     "transcript_text": data.get("text", ""),
 292 |                     "timestamped_text": data.get("timestamped_text", ""),
 293 |                 })
 294 |         print(f"  Loaded {len(videos)} cached transcripts")
 295 |     else:
 296 |         whisper_model = "tiny" if test_mode else "base"
 297 |         videos = scan_all_channels(model_size=whisper_model)
 298 |         print(f"  Scanned: {len(videos)} videos with transcripts")
 299 |     timing["2_scan"] = round(time.time() - t0, 2)
 300 |     write_render_context(2, "ok")
 301 | 
 302 |     if not videos:
 303 |         print("\n  [FAIL] No videos found — cannot produce episode")
 304 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 305 |         if is_enabled("telegram_alerts"):
 306 |             alert_pipeline_failure(date_str, "scan", "No videos found")
 307 |         return False
 308 | 
 309 |     # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
 310 |     if fast_test:
 311 |         print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
 312 |         t0 = time.time()
 313 |         # Build minimal selections from cached videos without calling Claude
 314 |         fast_clips = []
 315 |         for i, v in enumerate(videos[:2], 1):
 316 |             text = v.get("transcript_text", "")
 317 |             fast_clips.append({
 318 |                 "rank": i,
 319 |                 "video_id": v["video_id"],
 320 |                 "channel": v.get("channel", ""),
 321 |                 "title": v.get("title", ""),
 322 |                 "quote": text[:100] if text else "No transcript",
 323 |                 "why": "fast-test auto-select",
 324 |                 "start_seconds": 60,
 325 |                 "end_seconds": 90,
 326 |             })
 327 |         selections = {"clips": fast_clips}
 328 |         clips = fast_clips
 329 |         print(f"  Auto-selected: {len(clips)} clips (no API call)")
 330 |         timing["3_select"] = round(time.time() - t0, 2)
 331 |     else:
 332 |         print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
 333 |         t0 = time.time()
 334 |         selections = select_clips(videos)
 335 |         clips = selections.get("clips", [])
 336 |         print(f"  Selected: {len(clips)} clips")
 337 |         for c in clips:
 338 |             print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
 339 |         timing["3_select"] = round(time.time() - t0, 2)
 340 | 
 341 |     if not clips:
 342 |         print("\n  [FAIL] No clips selected — cannot produce episode")
 343 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 344 |         if is_enabled("telegram_alerts"):
 345 |             alert_pipeline_failure(date_str, "select", "No clips selected")
 346 |         return False
 347 | 
 348 |     # In test mode, use only top 2 clips
 349 |     if not fast_test and test_mode and len(clips) > 2:
 350 |         selections["clips"] = clips[:2]
 351 |         clips = selections["clips"]
 352 |         print(f"  [test] Truncated to {len(clips)} clips")
 353 | 
 354 |     # Save selections
 355 |     sel_path = os.path.join(run_dir, "selections.json")
 356 |     with open(sel_path, "w") as f:
 357 |         json.dump(selections, f, indent=2)
 358 | 
 359 |     # ── Step 3b: Select independent montage clips (Qwen, free) ──────────
 360 |     print("\n[STEP 3b] SELECTING MONTAGE CLIPS (local Qwen)...")
 361 |     try:
 362 |         from clip_selector import select_montage_clips
 363 |         montage_selections = select_montage_clips(videos)
 364 |         montage_clips_sel = montage_selections.get("clips", [])
 365 |         montage_sel_path = os.path.join(run_dir, "montage_selections.json")
 366 |         with open(montage_sel_path, "w") as f:
 367 |             json.dump(montage_selections, f, indent=2)
 368 |         print(f"  Montage: {len(montage_clips_sel)} independent clips selected")
 369 |     except Exception as e:
 370 |         print(f"  Montage selection failed ({e}) — montage will reuse Pulse Check clips")
 371 |         montage_selections = None
 372 | 
 373 |     # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
 374 |     print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
 375 |     t0 = time.time()
 376 |     # FIX 2: Wipe clips/ dir completely to prevent stale files from prior renders
 377 |     clip_dir = os.path.join(run_dir, "clips")
 378 |     if os.path.exists(clip_dir):
 379 |         shutil.rmtree(clip_dir)
 380 |         logger.info(f"  Wiped stale clips dir: {clip_dir}")
 381 |     os.makedirs(clip_dir, exist_ok=True)
 382 |     # Also wipe stale pip_preview files from work dir
 383 |     work_dir = os.path.join(run_dir, "work")
 384 |     if os.path.exists(work_dir):
 385 |         import glob as _pip_glob
 386 |         for stale_pip in _pip_glob.glob(os.path.join(work_dir, "pip_preview_*.mp4")):
 387 |             try:
 388 |                 os.remove(stale_pip)
 389 |             except OSError:
 390 |                 pass
 391 |         logger.info("  Wiped stale pip_preview files from work/")
 392 |     extracted_clips = extract_all(selections, clip_dir)
 393 |     print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")
 394 | 
 395 |     # ── Quality-aware fallback: retry with ranked alternates ──────────
 396 |     if not test_mode and not fast_test and len(extracted_clips) < 5:
 397 |         used_video_ids = {info["video_id"] for info in extracted_clips.values()}
 398 |         used_channels = {info["channel"] for info in extracted_clips.values()}
 399 |         tried_video_ids = {c["video_id"] for c in clips} | used_video_ids
 400 | 
 401 |         remaining = [v for v in videos
 402 |                      if v["video_id"] not in tried_video_ids
 403 |                      and v.get("channel", "") not in used_channels]
 404 | 
 405 |         if remaining:
 406 |             need = 5 - len(extracted_clips)
 407 |             logger.info(
 408 |                 f"[extractor] Only {len(extracted_clips)}/5 clips passed quality "
 409 |                 f"— selecting fallbacks from {len(remaining)} candidates (need {need})"
 410 |             )
 411 |             fallback_sel = select_clips(remaining)
 412 |             fallback_clips = fallback_sel.get("clips", [])
 413 | 
 414 |             max_rank = max(extracted_clips.keys()) if extracted_clips else 0
 415 |             for fc in fallback_clips:
 416 |                 if len(extracted_clips) >= 5:
 417 |                     break
 418 |                 fc_ch = fc.get("channel", "")
 419 |                 fc_vid = fc.get("video_id", "")
 420 |                 if fc_ch in used_channels or fc_vid in tried_video_ids:
 421 |                     continue
 422 |                 max_rank += 1
 423 |                 fc["rank"] = max_rank
 424 |                 logger.info(
 425 |                     f"[extractor] Clip failed quality — trying fallback candidate "
 426 |                     f"#{max_rank} [{fc_ch}] from selections"
 427 |                 )
 428 |                 fb_result = extract_all({"clips": [fc]}, clip_dir)
 429 |                 if fb_result:
 430 |                     for r, info in fb_result.items():
 431 |                         extracted_clips[r] = info
 432 |                         used_video_ids.add(info["video_id"])
 433 |                         used_channels.add(info["channel"])
 434 |                         tried_video_ids.add(fc_vid)
 435 |                         selections["clips"].append(fc)
 436 |                         logger.info(
 437 |                             f"[extractor] Fallback clip #{r} passed quality — "
 438 |                             f"{info['channel']} ({info['duration']:.1f}s)"
 439 |                         )
 440 |                 else:
 441 |                     tried_video_ids.add(fc_vid)
 442 |                     logger.warning(
 443 |                         f"[extractor] Fallback [{fc_ch}] also failed quality — trying next"
 444 |                     )
 445 | 
 446 |             # Update clips list and re-save selections
 447 |             clips = selections.get("clips", [])
 448 |             with open(sel_path, "w") as f:
 449 |                 json.dump(selections, f, indent=2)
 450 |             logger.info(f"[extractor] After fallback: {len(extracted_clips)}/5 clips")
 451 |         else:
 452 |             logger.warning("[extractor] No fallback candidates — all channels/videos exhausted")
 453 | 
 454 |     if not test_mode:
 455 |         _unique_ch = len({info.get("channel", f"unk_{i}") for i, info in enumerate(extracted_clips.values())})
 456 |         if len(extracted_clips) < 3 or _unique_ch < 2:
 457 |             logger.critical(
 458 |                 f"[PIPELINE] HARD FAIL: Need 5 clips from 5 unique channels, "
 459 |                 f"got {len(extracted_clips)} clips from {_unique_ch} channels."
 460 |             )
 461 |             return False
 462 |     for rank, info in sorted(extracted_clips.items()):
 463 |         print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
 464 |     timing["4_extract"] = round(time.time() - t0, 2)
 465 | 
 466 |     # ── Step 4m: Extract montage clips ───────────────────────────────────
 467 |     if montage_selections and montage_selections.get("clips"):
 468 |         print("\n[STEP 4m] EXTRACTING MONTAGE CLIPS...")
 469 |         try:
 470 |             extract_montage_all(montage_selections, clip_dir)
 471 |             print(f"  Montage clips extracted to {clip_dir}")
 472 |         except Exception as e:
 473 |             print(f"  Montage extraction failed ({e}) — skipping")
 474 | 
 475 |     if not extracted_clips:
 476 |         print("\n  [FAIL] No clips extracted — cannot produce episode")
 477 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 478 |         if is_enabled("telegram_alerts"):
 479 |             alert_pipeline_failure(date_str, "extract", "No clips extracted")
 480 |         return False
 481 | 
 482 |     # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
 483 |     import glob as _glob
 484 |     import random as _random
 485 | 
 486 |     def classify_episode_mood(script_text: str) -> str:
 487 |         """Classify episode mood from clip quotes."""
 488 |         moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
 489 |         lower = script_text.lower()
 490 |         if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
 491 |             moods["tense"] += 3
 492 |         if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
 493 |             moods["confident"] += 3
 494 |         if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
 495 |             moods["contemplative"] += 2
 496 |         if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
 497 |             moods["upbeat"] += 2
 498 |         if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
 499 |             moods["edge"] += 2
 500 |         best = max(moods, key=moods.get)
 501 |         return best if moods[best] > 0 else "confident"
 502 | 
 503 |     def select_music_bed(mood: str, music_dir: str) -> str:
 504 |         # Sprint 1.10: Randomize music, avoid repeating last track
 505 |         last_track_file = os.path.join(music_dir, ".last_track.txt")
 506 |         last_track = ""
 507 |         if os.path.exists(last_track_file):
 508 |             try:
 509 |                 last_track = open(last_track_file).read().strip()
 510 |             except Exception:
 511 |                 pass
 512 | 
 513 |         tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
 514 |         if not tracks:
 515 |             tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
 516 |         if not tracks:
 517 |             # Get all tracks except reserved ones
 518 |             all_tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
 519 |             tracks = [t for t in all_tracks
 520 |                       if os.path.basename(t) not in ("pp_outro.mp3", "pp_background.mp3",
 521 |                                                        "pp_intro.mp3", "pp_transition.mp3")]
 522 |         if not tracks:
 523 |             return ""
 524 | 
 525 |         # Avoid repeating last track
 526 |         if last_track and len(tracks) > 1:
 527 |             tracks = [t for t in tracks if os.path.basename(t) != last_track] or tracks
 528 | 
 529 |         chosen = _random.choice(tracks)
 530 |         try:
 531 |             with open(last_track_file, "w") as f:
 532 |                 f.write(os.path.basename(chosen))
 533 |         except Exception:
 534 |             pass
 535 |         return chosen
 536 | 
 537 |     def select_intro_music(music_dir: str) -> str:
 538 |         tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
 539 |         return _random.choice(tracks) if tracks else ""
 540 | 
 541 |     # Classify mood from clip quotes
 542 |     clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
 543 |     episode_mood = classify_episode_mood(clip_quotes)
 544 |     music_dir = os.path.join(BASE, "assets", "music")
 545 |     music_bed = select_music_bed(episode_mood, music_dir)
 546 |     intro_music = select_intro_music(music_dir)
 547 |     print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")
 548 | 
 549 |     # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
 550 |     live_context = ""
 551 |     live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
 552 |     try:
 553 |         if os.path.exists(live_signals_path):
 554 |             with open(live_signals_path) as f:
 555 |                 live_data = json.load(f)
 556 |             from datetime import timezone as _tz
 557 |             now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
 558 |             active_streams = []
 559 |             for s in live_data.get("live_streams", []):
 560 |                 # Only include streams from last 6 hours
 561 |                 started = s.get("started_at", "")
 562 |                 try:
 563 |                     started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
 564 |                     age_hours = (now - started_dt).total_seconds() / 3600
 565 |                     if age_hours > 6:
 566 |                         continue
 567 |                 except (ValueError, AttributeError):
 568 |                     continue
 569 |                 source = s.get("source", "youtube_live")
 570 |                 channel = s.get("channel", "unknown")
 571 |                 title = s.get("title", "")
 572 |                 topics = ", ".join(s.get("topics", []))
 573 |                 sentiment = s.get("current_sentiment", 50)
 574 |                 sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
 575 |                 active_streams.append(
 576 |                     f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
 577 |                 )
 578 |             if active_streams:
 579 |                 live_context = "\n".join(active_streams)
 580 |                 print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
 581 |                 for line in active_streams:
 582 |                     print(f"    {line}")
 583 |             else:
 584 |                 print("  Live signals: no active streams in last 6 hours")
 585 |     except Exception as e:
 586 |         logger.warning(f"Live signals read failed: {e}")
 587 | 
 588 |     # ── Step 5a: Fetch social posts + Space Tap BEFORE script generation ──
 589 |     # Social posts: fetch once, sort by likes desc, pass to script_writer
 590 |     sorted_social = []
 591 |     try:
 592 |         from utils.social_fetcher import get_todays_social_posts
 593 |         sorted_social = get_todays_social_posts(max_posts=5)
 594 |         if sorted_social:
 595 |             sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
 596 |             for si, sp in enumerate(sorted_social):
 597 |                 logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
 598 |     except Exception as e:
 599 |         logger.warning(f"Social posts fetch failed: {e}")
 600 | 
 601 |     # Space Tap: fetch X Spaces clips BEFORE script generation so LLM can write dialogue
 602 |     print("[STEP 5a] SPACE TAP -- LIVE X SPACES INTERCEPT...")
 603 |     try:
 604 |         import importlib.util
 605 |         _spaces_scraper_path = os.path.join(
 606 |             os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
 607 |             "x_spaces_scraper", "scraper.py"
 608 |         )
 609 |         if os.path.exists(_spaces_scraper_path):
 610 |             _spec = importlib.util.spec_from_file_location("x_spaces_scraper", _spaces_scraper_path)
 611 |             _mod = importlib.util.module_from_spec(_spec)
 612 |             _spec.loader.exec_module(_mod)
 613 |             _st = _mod.get_best_space_clips(max_clips=3)
 614 |             if _st and _st.get("clips"):
 615 |                 selections["space_tap_clips"] = _st["clips"]
 616 |                 print(f"  Space Tap: {len(_st['clips'])} clips from {_st.get('spaces_count', 0)} spaces")
 617 |             else:
 618 |                 print("  Space Tap: no live spaces — segment skipped")
 619 |         else:
 620 |             print("  Space Tap: scraper not installed — segment skipped")
 621 |     except Exception as _ste:
 622 |         logger.error(f"Space Tap fetch error: {type(_ste).__name__}: {_ste}")
 623 |         print(f"  Space Tap: skipped ({_ste})")
 624 | 
 625 |     # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
 626 |     if fast_test:
 627 |         print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
 628 |         t0 = time.time()
 629 |         script = _build_fast_test_script(extracted_clips, btc_price)
 630 |         timing["5_script"] = round(time.time() - t0, 2)
 631 |     else:
 632 |         print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
 633 |         t0 = time.time()
 634 |         script = generate_from_clips(selections, btc_price=btc_price,
 635 |                                      live_context=live_context,
 636 |                                      social_posts_sorted=sorted_social)
 637 |         timing["5_script"] = round(time.time() - t0, 2)
 638 | 
 639 |     # Attach social posts to script for assembler (single source of truth)
 640 |     if sorted_social:
 641 |         script["social_posts"] = sorted_social
 642 | 
 643 |     # Re-read dialogue AFTER all mutations (Space Tap entries may be in script)
 644 |     dialogue = script.get("dialogue", [])
 645 |     speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
 646 |     clip_markers = [d for d in dialogue if d.get("host") in ("CLIP", "SPACE_CLIP")]
 647 |     social_seg_count = sum(1 for d in dialogue if d.get("type") == "social_segment")
 648 |     space_tap_count = sum(1 for d in dialogue if d.get("host") == "SPACE_CLIP"
 649 |                          or (d.get("type") or "").startswith("space_tap"))
 650 |     print(f"  Title: {script.get('episode_title', 'Untitled')}")
 651 |     print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
 652 |     print(f"  SOCIAL segments: {social_seg_count} (input tweets: {len(sorted_social)})")
 653 |     print(f"  SPACE TAP entries: {space_tap_count} (input clips: {len(selections.get('space_tap_clips', []))})")
 654 |     if sorted_social and social_seg_count == 0:
 655 |         logger.error("SOCIAL SEGMENT ABSENT despite having tweet data — check script_writer enforcement")
 656 |     if selections.get("space_tap_clips") and space_tap_count == 0:
 657 |         logger.error("SPACE TAP ABSENT despite having clip data — check script_writer enforcement")
 658 | 
 659 |     # Save script
 660 |     script_path = os.path.join(run_dir, "script.json")
 661 |     with open(script_path, "w") as f:
 662 |         json.dump(script, f, indent=2)
 663 | 
 664 |     write_render_context(5, "ok",
 665 |                          episode_title=script.get("episode_title", ""),
 666 |                          social_posts_count=len(sorted_social),
 667 |                          space_tap_available=bool(selections.get("space_tap_clips")))
 668 | 
 669 |     # ── Step 6: TTS ───────────────────────────────────────────────────────
 670 |     print("\n[STEP 6/12] GENERATING PBX NARRATION AUDIO (ElevenLabs)...")
 671 |     t0 = time.time()
 672 |     audio_dir = os.path.join(run_dir, "audio")
 673 |     audio_data = generate_dialogue_audio(dialogue, audio_dir)
 674 |     successful = sum(1 for l in audio_data.get("lines", [])
 675 |                      if l.get("path") and os.path.exists(l.get("path", "")))
 676 |     print(f"  Audio: {successful}/{len(speech_lines)} lines")
 677 |     print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
 678 |     timing["6_tts"] = round(time.time() - t0, 2)
 679 |     write_render_context(6, "ok", tts_provider="elevenlabs")
 680 | 
 681 |     # ── Step 6b: BUILD MANIFEST ─────────────────────────────────────────
 682 |     print("\n[STEP 6b/12] BUILDING EPISODE MANIFEST...")
 683 |     t0 = time.time()
 684 |     try:
 685 |         from manifest_builder import build_manifest
 686 |         episode_manifest = build_manifest(
 687 |             script, audio_data, extracted_clips, run_dir,
 688 |             music_bed=music_bed, btc_price=btc_price,
 689 |         )
 690 |         print(f"  Manifest: {episode_manifest.get('total_segments', 0)} segments, "
 691 |               f"~{episode_manifest.get('total_duration_estimate', 0):.0f}s estimated")
 692 |     except Exception as e:
 693 |         logger.warning(f"Manifest build failed (non-blocking): {e}")
 694 |         episode_manifest = {}
 695 |     timing["6b_manifest"] = round(time.time() - t0, 2)
 696 | 
 697 |     # ── Step 6c: PREFLIGHT CHECK ─────────────────────────────────────────
 698 |     manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
 699 |     if os.path.exists(manifest_json_path):
 700 |         print("\n[STEP 6c/12] PREFLIGHT QC CHECK...")
 701 |         t0 = time.time()
 702 |         try:
 703 |             from qc_pipeline import preflight_check
 704 |             pf_passed, pf_errors, pf_warnings = preflight_check(manifest_json_path)
 705 |             print(f"  Preflight: {'PASS' if pf_passed else 'FAIL'} — "
 706 |                   f"{len(pf_errors)} errors, {len(pf_warnings)} warnings")
 707 |         except Exception as e:
 708 |             logger.warning(f"Preflight check failed (non-blocking): {e}")
 709 |         timing["6c_preflight"] = round(time.time() - t0, 2)
 710 | 
 711 |     # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
 712 |     print("\n[STEP 7/12] ASSEMBLING VIDEO...")
 713 |     t0 = time.time()
 714 |     result = assemble_episode(script, audio_data, extracted_clips, final_video,
 715 |                               btc_price=btc_price, music_bed=music_bed,
 716 |                               intro_music=intro_music)
 717 |     timing["7_assemble"] = round(time.time() - t0, 2)
 718 | 
 719 |     if not result or not os.path.exists(final_video):
 720 |         print("\n  [FAIL] Assembly failed")
 721 |         write_render_context(7, "fail", error="Video assembly failed or no output file")
 722 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 723 |         if is_enabled("telegram_alerts"):
 724 |             alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
 725 |         return False
 726 |     write_render_context(7, "ok")
 727 | 
 728 |     # ── Step 8: SHORTS ────────────────────────────────────────────────────
 729 |     print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
 730 |     t0 = time.time()
 731 |     shorts_dir = os.path.join(run_dir, "shorts")
 732 |     shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
 733 |                              max_shorts=3 if not test_mode else 1)
 734 |     print(f"  Shorts: {len(shorts)}")
 735 |     timing["8_shorts"] = round(time.time() - t0, 2)
 736 | 
 737 |     # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
 738 |     print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
 739 |     t0 = time.time()
 740 |     thumb_data = script.get("thumbnail", {})
 741 |     top_quote = ""
 742 |     if clips:
 743 |         top_quote = clips[0].get("quote", "")
 744 |     thumb_path = os.path.join(run_dir, "thumbnail.png")
 745 |     generate_thumbnail(
 746 |         thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
 747 |         thumb_data.get("subtext", ""),
 748 |         thumb_path,
 749 |         btc_price=btc_price,
 750 |         top_quote=top_quote,
 751 |     )
 752 |     timing["9_thumbnail"] = round(time.time() - t0, 2)
 753 | 
 754 |     # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
 755 |     print("\n[STEP 10/12] GENERATING CHAPTERS...")
 756 |     t0 = time.time()
 757 |     chapters_path = os.path.join(run_dir, "chapters.txt")
 758 |     generate_chapters(script, audio_data, chapters_path)
 759 |     timing["10_chapters"] = round(time.time() - t0, 2)
 760 | 
 761 |     # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
 762 |     print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
 763 |     t0 = time.time()
 764 |     podcast_path = os.path.join(run_dir, "podcast.mp3")
 765 |     extract_podcast_audio(final_video, podcast_path)
 766 | 
 767 |     email_html = generate_email_html(
 768 |         script.get("episode_title", "Pulse Check"),
 769 |         segments_summary=script.get("segments_summary", []),
 770 |         btc_price=btc_price,
 771 |     )
 772 |     newsletter_path = os.path.join(run_dir, "newsletter.html")
 773 |     save_newsletter_html(email_html, newsletter_path)
 774 |     timing["11_podcast_newsletter"] = round(time.time() - t0, 2)
 775 | 
 776 |     # ── Step 12: VERIFY ───────────────────────────────────────────────────
 777 |     print("\n[STEP 12/12] VERIFYING OUTPUT...")
 778 |     t0 = time.time()
 779 |     passed = verify_video(final_video)
 780 | 
 781 |     # Final AV sync validation
 782 |     final_offset = check_av_sync(final_video)
 783 |     print(f"  Final AV sync offset: {final_offset:+.3f}s")
 784 |     if abs(final_offset) > 0.05:
 785 |         logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
 786 |         nuclear_tmp = final_video + ".nuclear.mp4"
 787 |         nuclear_cmd = subprocess.run([
 788 |             "ffmpeg", "-y",
 789 |             "-fflags", "+genpts+igndts",
 790 |             "-i", final_video,
 791 |             "-c:v", "libx264", "-preset", "medium",
 792 |             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
 793 |             "-r", "30", "-vsync", "cfr",
 794 |             "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
 795 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 796 |             "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
 797 |             "-movflags", "+faststart",
 798 |             nuclear_tmp,
 799 |         ], capture_output=True, text=True, timeout=600)
 800 |         if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
 801 |             os.replace(nuclear_tmp, final_video)
 802 |             recheck = check_av_sync(final_video)
 803 |             print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
 804 |         elif os.path.exists(nuclear_tmp):
 805 |             os.remove(nuclear_tmp)
 806 | 
 807 |     # Final bitrate validation
 808 |     br_result = subprocess.run(
 809 |         ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
 810 |         capture_output=True, text=True,
 811 |     )
 812 |     try:
 813 |         br_info = json.loads(br_result.stdout)
 814 |         bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
 815 |         print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
 816 |         if bitrate < 3_000_000:
 817 |             logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
 818 |     except Exception:
 819 |         pass
 820 | 
 821 |     timing["12_verify"] = round(time.time() - t0, 2)
 822 |     write_render_context(12, "ok" if passed else "fail",
 823 |                          error="verify failed" if not passed else None)
 824 | 
 825 |     # ── Step 12b: POST-RENDER QC ─────────────────────────────────────────
 826 |     print("\n[STEP 12b] POST-RENDER QC...")
 827 |     t0 = time.time()
 828 |     try:
 829 |         from qc_pipeline import post_render_qc, save_qc_report
 830 |         manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
 831 |         qc_report = post_render_qc(final_video, manifest_json_path)
 832 |         save_qc_report(qc_report, run_dir)
 833 |         print(f"  QC: {'PASS' if qc_report.get('passed') else 'FAIL'}")
 834 |         for check, val in qc_report.get("checks", {}).items():
 835 |             status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
 836 |             print(f"    [{status}] {check}")
 837 |     except Exception as e:
 838 |         logger.warning(f"Post-render QC failed (non-blocking): {e}")
 839 |     timing["12b_qc"] = round(time.time() - t0, 2)
 840 | 
 841 |     # ── Summary ──────────────────────────────────────────────────────────
 842 |     timing["total"] = round(time.time() - t_pipeline_start, 2)
 843 | 
 844 |     # Video stats
 845 |     r = subprocess.run(
 846 |         ["ffprobe", "-v", "quiet", "-print_format", "json",
 847 |          "-show_format", "-show_streams", final_video],
 848 |         capture_output=True, text=True,
 849 |     )
 850 |     try:
 851 |         info = json.loads(r.stdout)
 852 |         fmt = info.get("format", {})
 853 |         streams = info.get("streams", [])
 854 |         vid = next((s for s in streams if s.get("codec_type") == "video"), {})
 855 |         aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
 856 |         dur = float(fmt.get("duration", 0))
 857 |         sz = int(fmt.get("size", 0)) / 1024 / 1024
 858 |         timing["video_duration"] = round(dur, 1)
 859 |         timing["video_size_mb"] = round(sz, 1)
 860 |     except Exception:
 861 |         vid, aud, dur, sz = {}, {}, 0, 0
 862 | 
 863 |     print("\n" + "=" * 70)
 864 |     print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
 865 |     print(f"  Title:    {script.get('episode_title', 'Untitled')}")
 866 |     print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
 867 |     print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
 868 |     print(f"  Size:     {sz:.1f}MB")
 869 |     print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
 870 |     print(f"  Shorts:   {len(shorts)}")
 871 |     print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")
 872 | 
 873 |     outputs = {
 874 |         "video": final_video,
 875 |         "shorts": [s for s in shorts],
 876 |         "thumbnail": thumb_path,
 877 |         "chapters": chapters_path,
 878 |         "podcast": podcast_path,
 879 |         "newsletter": newsletter_path,
 880 |         "script": script_path,
 881 |         "selections": sel_path,
 882 |     }
 883 | 
 884 |     print(f"\n  OUTPUT FILES:")
 885 |     for name, path in outputs.items():
 886 |         if isinstance(path, list):
 887 |             for p in path:
 888 |                 exists = "Y" if os.path.exists(p) else "N"
 889 |                 print(f"    [{exists}] {os.path.basename(p)}")
 890 |         else:
 891 |             exists = "Y" if os.path.exists(path) else "N"
 892 |             print(f"    [{exists}] {os.path.basename(path)}")
 893 | 
 894 |     print(f"\n  TIMING:")
 895 |     for step, secs in timing.items():
 896 |         if step not in ("video_duration", "video_size_mb"):
 897 |             print(f"    {step:25s}: {secs:.1f}s")
 898 |     print(f"\n  Output: {run_dir}")
 899 |     print("=" * 70)
 900 | 
 901 |     _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)
 902 | 
 903 |     # Save manifest
 904 |     manifest = {
 905 |         "version": "v5",
 906 |         "episode_title": script.get("episode_title", ""),
 907 |         "btc_price": btc_price,
 908 |         "test_mode": test_mode,
 909 |         "timestamp": time_str,
 910 |         "clips_used": [
 911 |             {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
 912 |             for r, info in sorted(extracted_clips.items())
 913 |         ],
 914 |         "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
 915 |         "timing": timing,
 916 |         "success": passed,
 917 |     }
 918 |     manifest_path = os.path.join(run_dir, "manifest.json")
 919 |     with open(manifest_path, "w") as f:
 920 |         json.dump(manifest, f, indent=2)
 921 | 
 922 |     # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
 923 |     print("\n[STEP 13] QUALITY GATE...")
 924 |     t0 = time.time()
 925 |     quality_score = compute_quality_score(manifest_path, video_path=final_video)
 926 |     print(f"  {format_score_report(quality_score)}")
 927 |     manifest["quality_score"] = quality_score
 928 | 
 929 |     if is_enabled("youtube_auto_upload") and should_upload(quality_score):
 930 |         from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
 931 |         # Build YouTube metadata
 932 |         ep_title = script.get("episode_title", "Pulse Check")
 933 |         yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
 934 |         chapters_text = ""
 935 |         if os.path.exists(chapters_path):
 936 |             with open(chapters_path) as f:
 937 |                 chapters_text = f.read()
 938 |         yt_description = build_description(
 939 |             summary=f"{ep_title}\n\nBTC Price: {btc_price}",
 940 |             chapters_text=chapters_text,
 941 |             clips=clips,
 942 |         )
 943 |         topics = [c.get("channel", "") for c in clips]
 944 |         yt_tags = build_tags(topics)
 945 | 
 946 |         print(f"  Uploading to YouTube (unlisted)...")
 947 |         upload_result = yt_upload(
 948 |             final_video, yt_title, yt_description,
 949 |             tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
 950 |         )
 951 |         print(f"  Upload result: {upload_result.get('status')}")
 952 |         if upload_result.get("url"):
 953 |             print(f"  URL: {upload_result['url']}")
 954 |         manifest["upload_result"] = upload_result
 955 |         if is_enabled("telegram_alerts") and upload_result.get("url"):
 956 |             alert_upload_success(date_str, upload_result["url"])
 957 |     elif quality_score < 85:
 958 |         logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
 959 |         hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
 960 |         with open(hold_path, "w") as f:
 961 |             f.write(f"Quality score: {quality_score}/100\n")
 962 |             f.write(f"Threshold: 85\n")
 963 |             f.write(f"Reason: Below quality threshold\n")
 964 |             f.write(f"Episode: {script.get('episode_title', '')}\n")
 965 |             f.write(f"Video: {final_video}\n")
 966 |         manifest["held_for_review"] = True
 967 |         if is_enabled("telegram_alerts"):
 968 |             alert_quality_hold(date_str, quality_score)
 969 |     else:
 970 |         logger.info("YouTube auto-upload disabled in feature flags")
 971 | 
 972 |     # Write final manifest with quality score
 973 |     with open(manifest_path, "w") as f:
 974 |         json.dump(manifest, f, indent=2)
 975 |     timing["13_quality_gate"] = round(time.time() - t0, 2)
 976 | 
 977 |     # ── Step 14: STAGE BRIEF (post Grade-A render) ─────────────────────────
 978 |     if quality_score >= 85:
 979 |         try:
 980 |             from generate_stage_brief import generate_brief
 981 |             print("\n[STEP 14] GENERATING STAGE BRIEF...")
 982 |             t0 = time.time()
 983 |             brief_path = generate_brief(run_dir)
 984 |             if brief_path:
 985 |                 logger.info(f"Stage brief generated: {brief_path}")
 986 |                 print(f"  Stage brief: {brief_path}")
 987 |                 manifest["stage_brief"] = brief_path
 988 |             else:
 989 |                 logger.warning("Stage brief returned None")
 990 |                 print("  Stage brief: skipped (returned None)")
 991 |             timing["14_stage_brief"] = round(time.time() - t0, 2)
 992 |         except Exception as e:
 993 |             logger.warning(f"Stage brief generation failed (non-fatal): {e}")
 994 |             print(f"  Stage brief failed (non-fatal): {e}")
 995 |             timing["14_stage_brief"] = 0
 996 |     else:
 997 |         logger.info(f"Skipping stage brief — quality score {quality_score} < 85")
 998 | 
 999 |     # Save episode performance data (V17)
1000 |     try:
1001 |         from utils.analytics_store import save_episode_performance
1002 |         perf_data = {
1003 |             "date": ts.strftime("%Y-%m-%d"),
1004 |             "episode_title": script.get("episode_title", ""),
1005 |             "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
1006 |             "quality_score": manifest.get("quality_score", 0),
1007 |             "clips_count": len(manifest.get("clips_used", [])),
1008 |             "duration_seconds": round(timing.get("video_duration", 0), 1),
1009 |             "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
1010 |             "av_sync_offset": round(final_offset, 3),
1011 |             "music_mood": episode_mood,
1012 |             "test_mode": test_mode,
1013 |         }
1014 |         save_episode_performance(date_str, perf_data)
1015 |     except Exception as e:
1016 |         logger.warning(f"Performance data save failed: {e}")
1017 | 
1018 |     # Telegram success alert
1019 |     if is_enabled("telegram_alerts") and passed:
1020 |         alert_pipeline_success(date_str, quality_score,
1021 |                                timing.get("video_duration", 0), final_video)
1022 | 
1023 |     # ── Step 14: FORMAT MULTIPLIER (V22) ───────────────────────────────────
1024 |     # LAW 1: Only runs AFTER episode is fully rendered and QC-passed.
1025 |     # LAW 2: Runs as a detached subprocess — never blocks or delays the main render.
1026 |     if is_enabled("multi_format_output") and passed:
1027 |         print("\n[STEP 14] FORMAT MULTIPLIER — launching secondary formats...")
1028 |         try:
1029 |             fmt_script = os.path.join(BASE, "format_multiplier.py")
1030 |             fmt_args = [
1031 |                 sys.executable, fmt_script,
1032 |                 "--manifest", manifest_path,
1033 |                 "--video", final_video,
1034 |             ]
1035 |             if test_mode:
1036 |                 fmt_args.append("--test")
1037 |             # Detached subprocess: does not block main pipeline return
1038 |             fmt_proc = subprocess.Popen(
1039 |                 fmt_args,
1040 |                 stdout=open(os.path.join(run_dir, "format_multiplier.log"), "w"),
1041 |                 stderr=subprocess.STDOUT,
1042 |                 start_new_session=True,  # detach from parent process group
1043 |             )
1044 |             print(f"  Format multiplier launched (PID {fmt_proc.pid}) — 5 formats running in background")
1045 |             print(f"  Log: {run_dir}/format_multiplier.log")
1046 |             manifest["format_multiplier_pid"] = fmt_proc.pid
1047 |         except Exception as e:
1048 |             logger.warning(f"Format multiplier launch failed (non-blocking): {e}")
1049 |     elif not is_enabled("multi_format_output"):
1050 |         logger.info("multi_format_output feature flag is disabled — skipping format multiplier")
1051 | 
1052 |     # ── Post-render health check + Resend notification ─────────────────────
1053 |     hc_passed = True  # default for test mode; overridden below for production
1054 |     if not test_mode:
1055 |         hc_passed, hc_errors = _post_render_health_check(final_video)
1056 |         dur_s = timing.get("video_duration", 0)
1057 |         size_mb = timing.get("video_size_mb", 0)
1058 |         dur_min = int(dur_s // 60)
1059 |         dur_sec = int(dur_s % 60)
1060 |         if passed and hc_passed:
1061 |             _send_resend_alert(
1062 |                 f"Pulse Check rendered: {dur_min}m {dur_sec}s, {size_mb:.0f}MB",
1063 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1064 |                 f"Duration: {dur_min}m {dur_sec}s\n"
1065 |                 f"Size: {size_mb:.1f}MB\n"
1066 |                 f"Quality: {quality_score}/100\n"
1067 |                 f"Video: {final_video}",
1068 |             )
1069 |         else:
1070 |             _send_resend_alert(
1071 |                 "ALERT: Pulse Check render issues detected",
1072 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1073 |                 f"Pipeline passed: {passed}\n"
1074 |                 f"Health check passed: {hc_passed}\n"
1075 |                 f"Errors: {hc_errors}\n"
1076 |                 f"Video: {final_video}",
1077 |             )
1078 | 
1079 |     return passed and hc_passed
1080 | 
1081 | 
1082 | def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
1083 |     report_path = os.path.join(run_dir, "timing_report.txt")
1084 |     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
1085 |     lines = [
1086 |         "PULSE CHECK V5 — Timing Report",
1087 |         f"Generated: {ts}",
1088 |         f"Status: {'SUCCESS' if success else 'FAILED'}",
1089 |         "",
1090 |         "STEP TIMINGS:",
1091 |     ]
1092 |     for step, val in timing.items():
1093 |         if step in ("video_duration", "video_size_mb"):
1094 |             continue
1095 |         lines.append(f"  {step:<25}: {val:.1f}s")
1096 |     lines += [
1097 |         "",
1098 |         "OUTPUT STATS:",
1099 |         f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
1100 |         f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
1101 |         f"  total_wall_time_s    : {time.time() - t_start:.1f}",
1102 |     ]
1103 |     with open(report_path, "w") as f:
1104 |         f.write("\n".join(lines) + "\n")
1105 | 
1106 | 
1107 | def main():
1108 |     parser = argparse.ArgumentParser(
1109 |         description="Pulse Check V5 — Clip-First Video Producer")
1110 |     parser.add_argument("--test", action="store_true",
1111 |                         help="Test mode: fewer clips, truncated, test output dir")
1112 |     parser.add_argument("--skip-scan", action="store_true",
1113 |                         help="Skip channel scanning, use cached transcripts")
1114 |     parser.add_argument("--fast-test", action="store_true",
1115 |                         help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
1116 |     args = parser.parse_args()
1117 |     success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
1118 |                            fast_test=args.fast_test)
1119 |     # ── Post-render: fire tweet machine from morning brief ──────────────
1120 |     try:
1121 |         import subprocess as _sp
1122 |         _sp.Popen(["python3", "/home/ultron/protocol_pulse/services/tweet_machine.py"],
1123 |                   stdout=open("/home/ultron/protocol_pulse/logs/tweet_machine.log", "a"),
1124 |                   stderr=subprocess.STDOUT)
1125 |         print("  Tweet machine: fired (async)")
1126 |     except Exception as _te:
1127 |         print(f"  Tweet machine: skipped ({_te})")
1128 |     sys.exit(0 if success else 1)
1129 | 
1130 | 
1131 | if __name__ == "__main__":
1132 |     main()
1133 | 
```

### File: video_pipeline_v3/script_writer.py (924 lines)
```
   1 | import sys; sys.dont_write_bytecode = True
   2 | #!/usr/bin/env python3
   3 | """Script Writer V5 — generates host dialogue AROUND real YouTube clips.
   4 | 
   5 | Takes the 5 clips selected by clip_selector and generates:
   6 | - Cold open teasing clip #1
   7 | - Setup → Clip → React dialogue for each clip
   8 | - Wrap-up and sign-off
   9 | 
  10 | Host dialogue supports the clips, not the other way around.
  11 | """
  12 | import json
  13 | import logging
  14 | import os
  15 | import re
  16 | import sys
  17 | 
  18 | try:
  19 |     import anthropic
  20 |     HAS_ANTHROPIC = True
  21 | except ImportError:
  22 |     HAS_ANTHROPIC = False
  23 | 
  24 | from relay import get_key
  25 | 
  26 | logger = logging.getLogger("ScriptWriter")
  27 | if not logger.handlers:
  28 |     handler = logging.StreamHandler()
  29 |     handler.setFormatter(logging.Formatter("[script] %(message)s"))
  30 |     logger.addHandler(handler)
  31 |     logger.setLevel(logging.INFO)
  32 | 
  33 | SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
  34 | Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.
  35 | 
  36 | === SHOW BIBLE — IDENTITY ===
  37 | PBX is a Bitcoin operator and cypherpunk. He sees the world through an Austrian economics lens. He is NOT a financial analyst — he is a sovereign individual who runs nodes, understands mining, and lives on a Bitcoin standard.
  38 | EDITORIAL LAWS:
  39 | - Bitcoin ONLY. Never cover altcoins, crypto, DeFi, NFTs, or tokens.
  40 | - Never write "BTC" — always write "Bitcoin" in full.
  41 | - Never hedge. PBX states opinions directly. No "could", "might", "it remains to be seen."
  42 | - Respect the audience — they know what a UTXO is. Never explain basics.
  43 | - Every episode must contain ONE original PBX observation that nobody else said today.
  44 | - Cold open: single most important signal in ONE sentence. No warmup.
  45 | - PBX Close: an actual opinion, not a summary of what was covered.
  46 | NEVER COVER: mainstream media Bitcoin takes, institutional ETF obsession as the main story, fear-mongering narratives.
  47 | TIER 1 SOURCES (highest editorial weight): Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, Stephan Livera.
  48 | TIER 2 SOURCES: Simply Bitcoin, Bitcoin Magazine, Natalie Brunell, Swan Bitcoin.
  49 | NORTH STAR: This is a sovereign Bitcoin holders' morning show. Under 12 minutes. All signal, no noise.
  50 | === END SHOW BIBLE ===
  51 | 
  52 | HOST (PBX) — Hot takes, contrarian, dry wit. Warm strong male voice. PBX is the SOLE host. There is NO second host. PBX handles ALL segments: setup, react, data, social, wrap.
  53 | 
  54 | PBX is ALWAYS the FIRST voice. PBX opens every episode with the cold open and handles ALL narration segments. PBX closes with the final sign-off. The first dialogue entry MUST be host: 2 (PBX). ALL dialogue entries MUST be host: 2.
  55 | 
  56 | CRITICAL JSON RULE: NEVER output "host": 1 anywhere in your response. The ONLY valid host values are 2 (PBX) and "CLIP". Any entry with host:1 will cause a catastrophic render failure. Use ONLY host:2.
  57 | 
  58 | TONE RULES (NON-NEGOTIABLE):
  59 | - NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
  60 | - SETUP lines = 2-4 sentences, MAX 60 WORDS. A sharp framing angle + one specific data point. Leave them wanting the clip.
  61 | - REACT lines = 2-4 sentences. A hot take with substance — specific implication, not a vague platitude.
  62 | - Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
  63 | - Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
  64 | - Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
  65 | - Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
  66 | - After clips 2 and 4, add a BRIDGE line (type: "bridge") connecting that clip's theme to the next. 1-2 sentences. PBX only. Elevate the stakes or pivot the angle.
  67 | - REACT lines: when a clip lands something genuinely significant, give it 2-3 sharp sentences. Brief is not always best. Incisive > terse.
  68 | - NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
  69 | - CRITICAL: NEVER write "BTC" in any narration line. Always write "Bitcoin" in full. The ticker abbreviation sounds robotic when read aloud.
  70 | - When referencing a social media handle, write it in natural spoken form. NEVER write "@MaxKeiser". Write "Max Kaiser on X" or "Preston Pysh posted". Do not read handles aloud — reference the person by name.
  71 | - End with "Stay sovereign."
  72 | 
  73 | CRITICAL EPISODE ARC RULES (NON-NEGOTIABLE):
  74 | - Start with the most shocking/interesting fact. NO intro. NO "welcome to Protocol Pulse."
  75 | - At minute 3 (after Clip 2 setup), include a re-engagement hook: "But here's where it gets interesting..."
  76 | - At the halfway point, pivot to something unexpected or contrarian.
  77 | - End ABRUPTLY after the call to action. NEVER say "thanks for watching" or "see you next time."
  78 |   These phrases signal the video is ending and cause immediate viewer drop-off.
  79 | - Each narrator line should be 1-3 sentences. Never more than 4 sentences per turn.
  80 | - Include at least one specific number/metric in every other segment.
  81 | 
  82 | DELIVERY RULES:
  83 | - ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
  84 | - The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
  85 | - REACT lines = PBX's direct hot take on what was just shown. He speaks to the AUDIENCE, not to a co-host.
  86 | - NO conversational openers that imply a partner: NEVER use "Exactly.", "100%.", "I mean—", "Right, and—", "Yeah."
  87 | - React lines start with the IMPLICATION: "What this means is—", "The signal here is—", "Nobody's talking about—", "That's the tell.", "Here's what this means."
  88 | - Each new segment opens with a LIFT — a single high-energy sentence that raises the stakes. Think: news anchor tossing to the next story.
  89 | - Tone = investigative gossip journalist who happens to understand Austrian economics.
  90 | - Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
  91 | - Min 3, max 4 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.
  92 | 
  93 | EPISODE STRUCTURE (follow this order):
  94 | 1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
  95 | 2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
  96 | 3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
  97 | 4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
  98 | 5. [NARRATION] — Analysis after Clip 2.
  99 | 6. [DATA] — Hard metrics segment. MINIMUM 3 exchanges (all PBX). Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. Target: 45-60 seconds of spoken content.
 100 | 7. [SOCIAL] — "WHAT BITCOIN IS SAYING" — PBX reporting back from Bitcoin Twitter as live intelligence. Maximum 3 tweets, 20-25 seconds narration each (~75 seconds total). PBX treats each tweet as a signal:
 101 |   - PBX: 'Saylor just posted this to 65,000 likes — [quote]. Here's what that signals — conviction accumulation during extreme fear. That's the Saylor playbook and it's never been wrong.'
 102 |   - PBX: 'Lyn Alden weighed in on the macro picture — [paraphrase]. This aligns with what we're seeing in the bond market data. When she flips bullish on a timeline, institutions listen.'
 103 |   - PBX: 'This one caught my eye — [Name] is saying [quote]. The reason this matters is [2-3 sentences of sharp context].'
 104 |   PBX decodes the signal, he doesn't repeat the text. The tweet card is on screen — viewers read it themselves.
 105 |   CRITICAL: First tweet card shown = first referenced in narration. Maintain strict order.
 106 | 8. [SPACE_TAP] — "SPACE TAP: SIGNAL INTERCEPT" (only if space_tap_clips provided below)
 107 |    PBX opens: "Right now in the Bitcoin ecosphere..." or similar intelligence briefing opener.
 108 |    For each clip (3-4 clips provided):
 109 |    - One sentence intro: who is speaking, what space, why it matters NOW. 10-15 words.
 110 |    - The clip plays (assembler handles this — do NOT write clip text).
 111 |    - One sentence reaction: PBX adds value, contrarian take, or context. 10-15 words.
 112 |    Target: 10-15 seconds of narration per clip (intro + reaction combined).
 113 |    Segment tone: intelligence briefing. You are intercepting a live signal.
 114 |    Never say "I found" or "we discovered" — say "we're intercepting" or "signal captured from".
 115 |    Format each entry as:
 116 |    {{"host": 2, "text": "[SPACE_TAP] Right now in the ecosphere...", "type": "space_tap_intro"}},
 117 |    {{"host": "SPACE_CLIP", "clip_index": 0}},
 118 |    {{"host": 2, "text": "[SPACE_TAP] ...", "type": "space_tap_react"}},
 119 |    {{"host": "SPACE_CLIP", "clip_index": 1}},
 120 |    ... and so on for all clips.
 121 | 9. [WARM] — 2-3 sentences synthesizing the day's theme, then abrupt CTA. Target: 20-30 seconds. End ABRUPTLY. No "thanks for watching."
 122 | 
 123 | NARRATION PHILOSOPHY — Simon Dixon / Preston Pysh standard:
 124 | - Every line must contain ONE specific insight, data point, or evaluated observation
 125 | - Never state what already happened — analyze WHY it matters and WHAT COMES NEXT
 126 | - PBX sets up the angle with a sharp framing line + 1 specific number or fact
 127 | - PBX delivers the contrarian take, macro context, or on-chain implication
 128 | - Forbidden phrases: "Bitcoin continues to", "the market is watching", "this is significant",
 129 |   "interesting to note", "worth keeping an eye on", any pure restatement of price
 130 | - Required: each exchange references at least one of: hashrate, difficulty adjustment,
 131 |   miner profitability, HODLer behavior, lightning adoption, ETF flows, or macro correlation
 132 | - Minimum 3 sentences per speaker turn. Never 1-2 sentence fluff turns.
 133 | - Bridges between clips must connect thematic dots — not just "next up"
 134 | - DATA segment minimum: 4 lines from PBX, each with a specific metric, each with an implication
 135 | 
 136 | EPISODE LENGTH LAW: Target 550-680 narration words total. Never truncate a sentence. Every segment must be complete. Sharp means efficient — every sentence must earn its place. NO padding. NO repetition.
 137 | 
 138 | SEGMENT TAGGING (MANDATORY — controls PBX's voice dynamics):
 139 | Every dialogue text line MUST start with a segment type tag in brackets. The TTS engine reads this tag to adjust vocal delivery. If missing, the voice defaults to CLEAR which is safe but loses dramatic range.
 140 |   [COLD_OPEN] — opening hook only (first 1-2 sentences). Dramatic whisper. MAX 2 per episode.
 141 |   [NARRATION] — standard narration, setup, and analysis. Clear and confident. This is 70-80% of lines.
 142 |   [DATA] — specific metrics, prices, hashrates, on-chain numbers. Authoritative.
 143 |   [SOCIAL] — social segment commentary. Slightly warmer tone.
 144 |   [WARM] — outros, calls to action, sign-offs. Inviting.
 145 | Example: {{"host": 2, "text": "[NARRATION] Bitcoin miners are facing a squeeze as difficulty adjusts upward.", "type": "setup"}}
 146 | The tag is INSIDE the text string, not the type field. Both must be present.
 147 | 
 148 | SOCIAL SEGMENT — "WHAT BITCOIN IS SAYING":
 149 | If social posts data is provided below, add a "WHAT BITCOIN IS SAYING" segment after the last clip.
 150 | PBX has been on Bitcoin Twitter all morning and is REPORTING BACK as live intelligence.
 151 | This is NOT passive card display — PBX explicitly REACTS to each post as a signal analyst:
 152 | 
 153 | STYLE — PBX treats each tweet as intelligence, not content:
 154 |   - "{{Name}} just posted this to {{likes}} likes — [direct quote or tight paraphrase]. Here's what that signals..."
 155 |   - "{{Name}} weighed in on {{topic}} — [paraphrase]. This aligns with what we're seeing in the data..."
 156 |   - "This one caught my eye — {{Name}} is saying [quote]. The reason this matters is..."
 157 | PBX adds 2-3 sentences of sharp CONTEXT per tweet: why it matters NOW, what it signals about market positioning, how it connects to today's data. Maximum 3 posts, 20-25 seconds narration each, ~75 seconds total.
 158 | The tweet card is on screen — viewers can read the text. PBX's job is to DECODE the signal, not repeat the words.
 159 | Each entry uses type: "social_segment".
 160 | 
 161 | CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.
 162 | TWEET LAW — IRON LAW: Before writing ANY tweet narration, read the actual social_posts list in order. Tweet segment narration MUST reference social_posts[0]['handle'] for the first tweet, social_posts[1]['handle'] for the second, etc. NEVER reference a name not in the list. NEVER assume who tweeted. Read the handle from the data and use it verbatim.
 163 | 
 164 | {clips_info}
 165 | 
 166 | BTC Price Today: {btc_price}
 167 | Top Tweets/Nostr Posts Today: {social_posts}
 168 | {live_context}
 169 | Return ONLY valid JSON (no markdown, no code fences):
 170 | {{
 171 |   "cold_open": "explosive 1-sentence cold open",
 172 |   "dialogue": [
 173 |     {{"host": 2, "text": "...", "type": "cold_open"}},
 174 |     {{"host": 2, "text": "...", "type": "setup", "clip_rank": 1}},
 175 |     {{"host": "CLIP", "rank": 1}},
 176 |     {{"host": 2, "text": "...", "type": "react", "clip_rank": 1}},
 177 |     {{"host": 2, "text": "...", "type": "setup", "clip_rank": 2}},
 178 |     {{"host": "CLIP", "rank": 2}},
 179 |     {{"host": 2, "text": "...", "type": "react", "clip_rank": 2}},
 180 |     ...and so on for all clips...
 181 |     {{"host": 2, "text": "...", "type": "social_segment"}},
 182 |     {{"host": 2, "text": "...", "type": "social_segment"}},
 183 |     {{"host": 2, "text": "Final wrap. Stay sovereign.", "type": "wrap"}}
 184 |   ],
 185 |   "episode_title": "Short punchy title (5-8 words)",
 186 |   "thumbnail": {{
 187 |     "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
 188 |     "subtext": "secondary line"
 189 |   }},
 190 |   "segments_summary": ["4-8 WORD ALL CAPS EDITORIAL HEADLINE FOR EACH CLIP — like 'SAYLOR BETS BIG ON BITCOIN DIP' not a quote from the segment"],
 191 |   "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
 192 | }}
 193 | 
 194 | IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5)."""
 195 | 
 196 | 
 197 | # Maps bracket tags in text to segment types for TTS voice modes
 198 | _TAG_TO_TYPE = {
 199 |     "COLD_OPEN": "cold_open",
 200 |     "NARRATION": "setup",
 201 |     "DATA": "data",
 202 |     "SOCIAL": "social_segment",
 203 |     "WARM": "wrap",
 204 |     "BRIDGE": "setup",  # inter-clip context bridges treated as narration
 205 |     "SPACE_TAP": "space_tap",
 206 |     "SETUP": "setup",
 207 |     "REACT": "react",
 208 |     "CTA": "wrap",
 209 |     "COLD": "cold_open",
 210 | }
 211 | 
 212 | _TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")
 213 | 
 214 | 
 215 | def _extract_segment_tags(result: dict) -> dict:
 216 |     """Extract [TAG] prefixes from dialogue text and set entry type accordingly.
 217 | 
 218 |     If a dialogue line starts with [NARRATION], [DATA], etc., strip the tag
 219 |     from the text and set/override the type field for TTS voice mode selection.
 220 |     """
 221 |     dialogue = result.get("dialogue", [])
 222 |     # Force PBX-only: normalize any host:1 → host:2
 223 |     for _e in dialogue:
 224 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 225 |     for entry in dialogue:
 226 |         text = entry.get("text", "")
 227 |         if not text:
 228 |             continue
 229 |         m = _TAG_PATTERN.match(text)
 230 |         if m:
 231 |             tag = m.group(1)
 232 |             entry["text"] = text[m.end():]
 233 |             entry["type"] = _TAG_TO_TYPE[tag]
 234 |     # Normalize space_tap subtypes to "space_tap" so assembler _segment_to_scene matches
 235 |     for entry in dialogue:
 236 |         if entry.get("type", "") in ("space_tap_intro", "space_tap_react"):
 237 |             entry["type"] = "space_tap"
 238 |     return result
 239 | 
 240 | 
 241 | def _format_clips_info(selections: dict) -> str:
 242 |     """Format clip selections for the script prompt."""
 243 |     clips = selections.get("clips", [])
 244 |     parts = []
 245 |     for c in clips:
 246 |         parts.append(
 247 |             f"CLIP #{c['rank']}:\n"
 248 |             f"  Channel: {c.get('channel', 'Unknown')}\n"
 249 |             f"  Video: {c.get('video_title', 'Untitled')}\n"
 250 |             f"  Quote: \"{c.get('quote', '')}\"\n"
 251 |             f"  Why selected: {c.get('why', '')}\n"
 252 |             f"  Suggested setup: {c.get('host_setup', '')}\n"
 253 |             f"  Suggested reaction: {c.get('host_react', '')}\n"
 254 |         )
 255 |     return "\n".join(parts)
 256 | 
 257 | 
 258 | def _load_narrative_context() -> dict:
 259 |     """Load narrative_context.json for narrative-aware script generation.
 260 |     Returns empty dict if missing or stale (>6hr old)."""
 261 |     import os
 262 |     from datetime import datetime, timezone
 263 |     ctx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
 264 |                             "data", "intelligence", "narrative_context.json")
 265 |     try:
 266 |         with open(ctx_path) as f:
 267 |             ctx = json.load(f)
 268 |         # Check staleness
 269 |         computed = ctx.get("computed_at", "")
 270 |         if computed:
 271 |             computed_dt = datetime.fromisoformat(computed.replace("Z", "+00:00"))
 272 |             age_hours = (datetime.now(timezone.utc) - computed_dt).total_seconds() / 3600
 273 |             if age_hours > 6:
 274 |                 logger.warning(f"Narrative context is {age_hours:.1f}h old (>6h) — using generic prompt")
 275 |                 return {}
 276 |         return ctx
 277 |     except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
 278 |         logger.warning(f"Narrative context unavailable: {e}")
 279 |         return {}
 280 | 
 281 | 
 282 | NARRATIVE_INJECTION = """
 283 | TODAY'S LIVE NARRATIVE CONTEXT (from real-time thought leader monitoring):
 284 | Dominant narrative: {dominant_narrative}
 285 | Market mood: {market_mood}
 286 | What thought leaders are saying: {episode_narrative}
 287 | PBX cold open hook: {pbx_intro_hook}
 288 | PBX analysis angle: {pbx_context}
 289 | Suggested bridge lines: {narrative_bridge_lines}
 290 | 
 291 | MANDATORY SCRIPT RULES (from narrative context):
 292 | - PBX's cold open MUST reference the dominant narrative in his first sentence
 293 | - At least ONE of the clips must be explicitly connected to the X discourse
 294 |   (e.g., "This is what everyone on Crypto Twitter has been discussing all morning...")
 295 | - PBX must cite at least one specific data point from the narrative context (not generic)
 296 | - Avoid topics flagged in: {avoid_topics}
 297 | - The show must feel LIVE — like PBX has been tracking this story all morning
 298 | 
 299 | DATA SEGMENT REQUIREMENT: The data/metrics discussed must relate to today's
 300 | dominant narrative ({dominant_narrative}). If narrative is "ETF inflows",
 301 | cite actual ETF flow numbers. If "mining difficulty", cite actual hashrate/difficulty data.
 302 | PBX must sound like an analyst who read the numbers this morning, not a generalist.
 303 | """
 304 | 
 305 | 
 306 | def _validate_social_tweet_order(result: dict, social_posts_raw: str) -> dict:
 307 |     """Render11 FIX 5: Ensure narrator tweet references match tweet display order.
 308 | 
 309 |     If narrator mentions @handle that doesn't match the expected tweet position,
 310 |     reorder social_segment entries so card display matches narration order.
 311 |     Tags each social entry with _social_handle_ref for assembler card matching.
 312 |     """
 313 |     if not social_posts_raw or social_posts_raw.startswith("NONE"):
 314 |         return result
 315 | 
 316 |     dialogue = result.get("dialogue", [])
 317 |     # Force PBX-only: normalize any host:1 → host:2
 318 |     for _e in dialogue:
 319 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 320 |     if not dialogue:
 321 |         return result
 322 | 
 323 |     # Extract ordered handles from social_posts_raw (sorted by likes in generate_from_clips)
 324 |     social_handles = []
 325 |     for line in social_posts_raw.split("\n"):
 326 |         m = re.match(r'(?:Tweet \d+: )?@(\w+)\s+tweeted:', line)
 327 |         if m:
 328 |             social_handles.append(m.group(1).lower())
 329 | 
 330 |     # Extract @handle references from social_segment narration lines
 331 |     social_entries = [(i, e) for i, e in enumerate(dialogue)
 332 |                       if e.get("type") == "social_segment" and e.get("host") in (1, 2, "1", "2")]
 333 | 
 334 |     narrator_handles = []
 335 |     for _, entry in social_entries:
 336 |         text = entry.get("text", "")
 337 |         handles_in_text = re.findall(r'@(\w+)', text)
 338 |         for h in handles_in_text:
 339 |             h_lower = h.lower()
 340 |             if h_lower in social_handles and h_lower not in narrator_handles:
 341 |                 narrator_handles.append(h_lower)
 342 | 
 343 |     # Tag each social entry with its referenced handle
 344 |     for idx, entry in social_entries:
 345 |         text = entry.get("text", "")
 346 |         handles_in_text = [h.lower() for h in re.findall(r'@(\w+)', text)]
 347 |         matched = [h for h in handles_in_text if h in social_handles]
 348 |         if matched:
 349 |             entry["_social_handle_ref"] = matched[0]
 350 |             logger.info(f"[script] Social segment line {idx} references @{matched[0]}")
 351 | 
 352 |     # Render12 FIX 2: Assert strict tweet order — first card shown = first referenced
 353 |     if narrator_handles and social_handles:
 354 |         expected = social_handles[:len(narrator_handles)]
 355 |         if narrator_handles != expected:
 356 |             logger.warning(f"[script] TWEET ORDER VIOLATION: narrator={narrator_handles}, expected={expected} — reordering")
 357 |         else:
 358 |             logger.info(f"[script] TWEET ORDER OK: {narrator_handles}")
 359 | 
 360 |     # FIX 5: Reorder social_segment entries so narration order matches display order
 361 |     # The social_posts were sorted by likes desc — narrator should mention them in that order
 362 |     if narrator_handles and social_handles and narrator_handles != social_handles[:len(narrator_handles)]:
 363 |         logger.warning(f"[script] TWEET MISMATCH: narrator={narrator_handles}, data={social_handles[:len(narrator_handles)]}")
 364 |         # Reorder social_segment dialogue entries to match data order
 365 |         social_with_handle = [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]
 366 |         if social_with_handle:
 367 |             # Sort by position in social_handles (data order = likes desc)
 368 |             social_with_handle.sort(
 369 |                 key=lambda x: social_handles.index(x[1]["_social_handle_ref"])
 370 |                 if x[1]["_social_handle_ref"] in social_handles else 999
 371 |             )
 372 |             # Swap entries in-place in dialogue
 373 |             original_indices = [i for i, _ in [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]]
 374 |             for new_pos, (_, entry) in enumerate(social_with_handle):
 375 |                 if new_pos < len(original_indices):
 376 |                     dialogue[original_indices[new_pos]] = entry
 377 |             logger.info(f"[script] Reordered social entries to match data order")
 378 | 
 379 |     return result
 380 | 
 381 | 
 382 | def _make_editorial_headline(raw: str) -> str:
 383 |     """Convert a raw summary/title into a 3-7 word ALL CAPS editorial headline.
 384 | 
 385 |     Render11 FIX 8: Strict Bloomberg/newspaper front page format.
 386 |     No punctuation except dash. 3-7 words. Always ALL CAPS.
 387 |     BAD: 'Saylor talks about sonic boom theory'
 388 |     GOOD: 'SAYLOR SONIC BOOM BITCOIN THESIS'
 389 |     """
 390 |     import re
 391 |     # Strip quotes, URLs, timestamps, punctuation (except dash)
 392 |     clean = re.sub(r'https?://\S+', '', raw)
 393 |     clean = re.sub(r'["\'\[\]().,;:!?]', '', clean)
 394 |     clean = re.sub(r'\s+', ' ', clean).strip()
 395 |     # Take first 7 words, uppercase
 396 |     words = clean.split()[:7]
 397 |     headline = " ".join(words).upper()
 398 |     # Ensure minimum 3 words
 399 |     if len(words) < 3:
 400 |         headline = headline + " - BREAKING"
 401 |     # FIX 8: Post-generation validation — force ALL CAPS, strip non-conforming chars
 402 |     headline = re.sub(r'[^A-Z0-9 \-/]', '', headline).strip()
 403 |     if not headline or len(headline) < 5:
 404 |         headline = "BREAKING SIGNAL DETECTED"
 405 |     return headline[:55]
 406 | 
 407 | 
 408 | def _populate_segment_headlines(result: dict) -> dict:
 409 |     """Session 4 Fix 2: Add 'headline' key to each dialogue entry.
 410 | 
 411 |     Maps segment type + clip rank to a meaningful headline so _smart_headline()
 412 |     in assembler.py gets a real headline instead of truncated spoken text.
 413 |     Render11 FIX 8: Headlines are 3-7 word ALL CAPS editorial style with regex validation.
 414 |     """
 415 |     dialogue = result.get("dialogue", [])
 416 |     # Force PBX-only: normalize any host:1 → host:2
 417 |     for _e in dialogue:
 418 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 419 |     summaries = result.get("segments_summary", [])
 420 |     episode_title = result.get("episode_title", "Pulse Check Daily")
 421 | 
 422 |     for entry in dialogue:
 423 |         if entry.get("headline"):
 424 |             continue  # already has one
 425 |         host = entry.get("host")
 426 |         if host == "CLIP":
 427 |             continue  # clip markers don't need headlines
 428 | 
 429 |         seg_type = entry.get("type", "")
 430 |         clip_rank = entry.get("clip_rank", 0)
 431 | 
 432 |         if seg_type == "cold_open":
 433 |             entry["headline"] = _make_editorial_headline(episode_title)
 434 |         elif seg_type in ("setup", "react") and clip_rank:
 435 |             # Use segments_summary keyed by rank — force editorial style
 436 |             idx = clip_rank - 1
 437 |             if 0 <= idx < len(summaries) and summaries[idx]:
 438 |                 entry["headline"] = _make_editorial_headline(summaries[idx])
 439 |             else:
 440 |                 entry["headline"] = _make_editorial_headline(episode_title)
 441 |         elif seg_type == "data":
 442 |             entry["headline"] = "TODAY'S INTELLIGENCE"
 443 |         elif seg_type == "social_segment":
 444 |             entry["headline"] = "SIGNAL FROM THE FIELD"
 445 |         elif seg_type == "space_tap":
 446 |             entry["headline"] = "SPACE TAP SIGNAL INTERCEPT"
 447 |         elif seg_type in ("wrap", "outro"):
 448 |             entry["headline"] = "STAY SOVEREIGN"
 449 |         elif seg_type == "bridge":
 450 |             entry["headline"] = _make_editorial_headline(episode_title)
 451 |         else:
 452 |             # Generic narrator — use episode title
 453 |             entry["headline"] = _make_editorial_headline(episode_title)
 454 | 
 455 |     # Render11 FIX 8: Post-validation — force ALL CAPS, reject >8 words or lowercase
 456 |     for entry in dialogue:
 457 |         h = entry.get("headline", "")
 458 |         if not h or entry.get("host") == "CLIP":
 459 |             continue
 460 |         # Force uppercase and strip non-conforming chars
 461 |         h = re.sub(r'[^A-Z0-9 \-/]', '', h.upper()).strip()
 462 |         words = h.split()
 463 |         if len(words) > 8:
 464 |             h = " ".join(words[:7])
 465 |         if not h or len(h) < 5:
 466 |             h = "BREAKING SIGNAL DETECTED"
 467 |         entry["headline"] = h
 468 | 
 469 |     return result
 470 | 
 471 | 
 472 | def generate_from_clips(selections: dict, btc_price: str = "N/A",
 473 |                         live_context: str = "", morning_brief: dict = None,
 474 |                         social_posts_sorted: list = None) -> dict:
 475 |     """Generate host dialogue script around the selected clips.
 476 | 
 477 |     Args:
 478 |         selections: Output from clip_selector.select_clips()
 479 |         btc_price: Current BTC price string
 480 |         live_context: Real-time live stream/Spaces intelligence (optional)
 481 |         social_posts_sorted: Pre-fetched, sorted social posts (single source of truth from daily_producer)
 482 | 
 483 |     Returns:
 484 |         Script dict with dialogue array
 485 |     """
 486 |     clips = selections.get("clips", [])
 487 |     if not clips:
 488 |         logger.error("No clips provided for script generation")
 489 |         return _fallback_script(selections)
 490 | 
 491 |     from relay import call_llm
 492 | 
 493 |     clips_info = _format_clips_info(selections)
 494 | 
 495 |     # Social data — use pre-fetched sorted list from daily_producer (single source of truth)
 496 |     # Fallback: fetch here if caller didn't provide (backwards compat)
 497 |     social_data_sorted = social_posts_sorted or []
 498 |     if not social_data_sorted:
 499 |         try:
 500 |             from utils.social_fetcher import get_todays_social_posts
 501 |             social_data = get_todays_social_posts(max_posts=5)
 502 |             if social_data:
 503 |                 social_data_sorted = sorted(social_data, key=lambda x: x.get('likes', 0), reverse=True)
 504 |         except Exception as e:
 505 |             logger.warning(f"Social data fetch failed: {e}")
 506 | 
 507 |     if social_data_sorted:
 508 |         social_posts = "\n".join([
 509 |             f"Tweet {ti+1}: @{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
 510 |             for ti, p in enumerate(social_data_sorted)
 511 |         ])
 512 |         social_posts += (
 513 |             "\n\nCRITICAL SOCIAL RULES:"
 514 |             "\n- Read ONLY what is written above. Do NOT paraphrase, add, or invent words."
 515 |             "\n- Quote tweet text DIRECTLY and verbatim."
 516 |             "\n- Reference tweets BY POSITION: 'Tweet 1 from @handle' matches the first tweet listed above."
 517 |             "\n- If you mention @handle, the DISPLAYED tweet card MUST match that handle."
 518 |             "\n- Never attribute words from one tweet to a different person."
 519 |         )
 520 |     else:
 521 |         social_posts = "NONE — skip social segment entirely"
 522 | 
 523 |     # Build live context block
 524 |     live_block = ""
 525 |     if live_context:
 526 |         live_block = (
 527 |             "\nLIVE INTELLIGENCE: The following events are happening RIGHT NOW or happened "
 528 |             "in the last few hours on Bitcoin YouTube/X Spaces. Reference these naturally "
 529 |             "in your narration to make the episode feel current and urgent:\n"
 530 |             f"{live_context}\n"
 531 |         )
 532 | 
 533 |     # Inject narrative context from thought leader monitoring
 534 |     narrative_ctx = _load_narrative_context()
 535 |     if narrative_ctx and narrative_ctx.get("dominant_narrative"):
 536 |         try:
 537 |             bridge_lines = narrative_ctx.get("narrative_bridge_lines", [])
 538 |             narrative_block = (NARRATIVE_INJECTION
 539 |                 .replace("{dominant_narrative}", narrative_ctx.get("dominant_narrative", ""))
 540 |                 .replace("{market_mood}", narrative_ctx.get("market_mood", ""))
 541 |                 .replace("{episode_narrative}", narrative_ctx.get("episode_narrative", ""))
 542 |                 .replace("{pbx_intro_hook}", narrative_ctx.get("eryn_intro_hook", narrative_ctx.get("pbx_intro_hook", "")))
 543 |                 .replace("{pbx_context}", narrative_ctx.get("mark_context", narrative_ctx.get("pbx_context", "")))
 544 |                 .replace("{narrative_bridge_lines}", "\n".join(bridge_lines) if bridge_lines else "none")
 545 |                 .replace("{avoid_topics}", ", ".join(narrative_ctx.get("avoid_topics", [])))
 546 |             )
 547 |             live_block = narrative_block + "\n" + live_block
 548 |             logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")
 549 |         except Exception as e:
 550 |             logger.warning(f"Failed to inject narrative context: {e}")
 551 | 
 552 |     # Inject morning intelligence brief (Nitter-sourced Twitter analysis)
 553 |     morning_block = ""
 554 |     if morning_brief and isinstance(morning_brief, dict):
 555 |         parts = ["\nMORNING INTELLIGENCE BRIEF (from today's Bitcoin Twitter analysis — use as context):"]
 556 |         dom_narr = morning_brief.get("dominant_narratives", [])
 557 |         if dom_narr:
 558 |             parts.append(f"- Dominant narratives today: {'; '.join(dom_narr[:3])}")
 559 |         trending_lang = morning_brief.get("trending_language", [])
 560 |         if trending_lang:
 561 |             parts.append(f"- Trending language on Bitcoin Twitter: {', '.join(trending_lang[:7])}")
 562 |             parts.append("  USE these phrases naturally in narration where they fit — they resonate with the audience today.")
 563 |         sentiment = morning_brief.get("sentiment", "")
 564 |         reasoning = morning_brief.get("sentiment_reasoning", "")
 565 |         if sentiment:
 566 |             parts.append(f"- Market sentiment: {sentiment}")
 567 |         if reasoning:
 568 |             parts.append(f"  Reasoning: {reasoning[:200]}")
 569 |         voice_guidance = morning_brief.get("protocol_pulse_voice_guidance", "")
 570 |         if voice_guidance:
 571 |             parts.append(f"- Voice guidance: {voice_guidance[:250]}")
 572 |         morning_block = "\n".join(parts) + "\n"
 573 |         logger.info(f"Morning brief injected: {len(dom_narr)} narratives, {len(trending_lang)} trending phrases")
 574 | 
 575 |     # Inject audience engagement intelligence
 576 |     engagement_block = ""
 577 |     try:
 578 |         import sys as _sys
 579 |         _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
 580 |         if _data_dir not in _sys.path:
 581 |             _sys.path.insert(0, _data_dir)
 582 |         from engagement_scorer import get_trending_topics, get_top_channels
 583 |         trending = get_trending_topics()[:3]
 584 |         top_chs = get_top_channels(5)
 585 |         if trending or top_chs:
 586 |             parts = ["\nAUDIENCE ENGAGEMENT INTELLIGENCE (from real audience data — use naturally):"]
 587 |             if trending:
 588 |                 topics_str = ", ".join(f"{t[0]} ({t[1]:.1f}/10)" for t in trending)
 589 |                 parts.append(f"- Currently trending in our audience: {topics_str} — weight these if relevant.")
 590 |             if top_chs:
 591 |                 chs_str = ", ".join(f"{c[0]} ({c[1]:.1f})" for c in top_chs)
 592 |                 parts.append(f"- Highest engagement channels this week: {chs_str} — prioritize their clips.")
 593 |             engagement_block = "\n".join(parts) + "\n"
 594 |             logger.info(f"Engagement intelligence injected: {len(trending)} topics, {len(top_chs)} channels")
 595 |     except Exception as e:
 596 |         logger.debug(f"Engagement scorer unavailable: {e}")
 597 | 
 598 |     # Inject episode memory feedback if enough history exists
 599 |     memory_block = ""
 600 |     try:
 601 |         from episode_memory import get_episode_count, get_weak_dimensions, get_strong_dimensions, get_best_channels
 602 |         if get_episode_count() >= 5:
 603 |             weak = get_weak_dimensions(threshold=6.0)
 604 |             strong = get_strong_dimensions(threshold=8.0)
 605 |             top_ch = get_best_channels(5)
 606 |             parts = ["\nEPISODE MEMORY FEEDBACK (from past renders — adapt accordingly):"]
 607 |             if weak:
 608 |                 dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in weak[:5])
 609 |                 parts.append(f"- WEAK AREAS (improve these): {dims}")
 610 |             if strong:
 611 |                 dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in strong[:5])
 612 |                 parts.append(f"- STRONG AREAS (maintain these): {dims}")
 613 |             if top_ch:
 614 |                 chs = ", ".join(f"{c['channel']} ({c['avg_score']})" for c in top_ch)
 615 |                 parts.append(f"- TOP CHANNELS by quality score: {chs}")
 616 |             memory_block = "\n".join(parts) + "\n"
 617 |             logger.info(f"Episode memory injected: {len(weak)} weak, {len(strong)} strong dimensions")
 618 |     except Exception as e:
 619 |         logger.warning(f"Episode memory unavailable: {e}")
 620 | 
 621 |     # Inject Space Tap clips context if available
 622 |     space_tap_block = ""
 623 |     space_tap_clips = selections.get("space_tap_clips", [])
 624 |     if space_tap_clips:
 625 |         parts = ["\nSPACE TAP CLIPS (X Spaces intercepts — generate [SPACE_TAP] segment):"]
 626 |         for i, sc in enumerate(space_tap_clips):
 627 |             handle = sc.get("host_handle", "unknown")
 628 |             text_preview = sc.get("text", "")[:150]
 629 |             parts.append(f"  Clip {i}: @{handle} — \"{text_preview}\"")
 630 |         parts.append(f"Generate intro + react for each of the {len(space_tap_clips)} clips above.")
 631 |         space_tap_block = "\n".join(parts) + "\n"
 632 | 
 633 |     prompt = (SCRIPT_PROMPT
 634 |         .replace("{clips_info}", str(clips_info))
 635 |         .replace("{btc_price}", str(btc_price))
 636 |         .replace("{social_posts}", str(social_posts))
 637 |         .replace("{live_context}", str(live_block+morning_block+engagement_block+memory_block+space_tap_block))
 638 |     )
 639 | 
 640 |     logger.info(f"Generating script for {len(clips)} clips...")
 641 |     text = call_llm(prompt, max_tokens=8000, model="claude-sonnet-4-6")
 642 |     if text is None:
 643 |         logger.warning("All LLM providers failed, using fallback script")
 644 |         return _fallback_script(selections)
 645 | 
 646 |     try:
 647 | 
 648 |         if "```json" in text:
 649 |             text = text.split("```json")[1].split("```")[0]
 650 |         elif "```" in text:
 651 |             text = text.split("```")[1].split("```")[0]
 652 | 
 653 |         # FIX 4: JSON retry loop — send malformed JSON back for repair, max 3 retries
 654 |         json_text = text
 655 |         result = None
 656 |         for _retry in range(4):  # attempt 0 = first try, 1-3 = retries
 657 |             try:
 658 |                 result = json.loads(json_text)
 659 |                 break
 660 |             except json.JSONDecodeError as je:
 661 |                 if _retry >= 3:
 662 |                     raise RuntimeError(f"JSON repair failed after 3 retries: {je}") from je
 663 |                 logger.warning(f"JSON parse error (retry {_retry+1}/3): {je}")
 664 |                 repair_prompt = (
 665 |                     f"The following JSON is malformed. Fix it and return ONLY valid JSON, "
 666 |                     f"no markdown, no explanation:\n\n{json_text}\n\n"
 667 |                     f"Error was: {je}"
 668 |                 )
 669 |                 json_text = call_llm(repair_prompt, max_tokens=8000, model="claude-sonnet-4-6")
 670 |                 if json_text is None:
 671 |                     raise RuntimeError("JSON repair LLM call returned None")
 672 |                 # Strip code fences from repair response
 673 |                 if "```json" in json_text:
 674 |                     json_text = json_text.split("```json")[1].split("```")[0]
 675 |                 elif "```" in json_text:
 676 |                     json_text = json_text.split("```")[1].split("```")[0]
 677 | 
 678 |         # Extract [TAG] prefixes from text and set type fields for TTS
 679 |         result = _extract_segment_tags(result)
 680 | 
 681 |         # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
 682 |         result = _populate_segment_headlines(result)
 683 | 
 684 |         # Round 2 Fix 5: Validate social segment tweet order matches narration references
 685 |         result = _validate_social_tweet_order(result, social_posts)
 686 |         result = _enforce_setup_per_clip(result, selections)
 687 | 
 688 |         # Enforce social segment presence when social data was provided
 689 |         result = _enforce_social_segment(result, social_data_sorted)
 690 | 
 691 |         # Enforce space tap segment presence when space tap clips were provided
 692 |         result = _enforce_space_tap_segment(result, selections.get("space_tap_clips", []))
 693 | 
 694 |         # Validate structure
 695 |         dialogue = result.get("dialogue", [])
 696 |         # Force PBX-only: normalize any host:1 â host:2
 697 |         for _e in dialogue:
 698 |             if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 699 |         clip_entries = [d for d in dialogue if d.get("host") == "CLIP"]
 700 |         speech_entries = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
 701 | 
 702 |         logger.info(f"Script generated: {len(dialogue)} entries "
 703 |                     f"({len(speech_entries)} speech, {len(clip_entries)} clips)")
 704 |         logger.info(f"Title: {result.get('episode_title', 'Untitled')}")
 705 | 
 706 |         return result
 707 | 
 708 |     except json.JSONDecodeError as e:
 709 |         logger.error(f"JSON parse error: {e}")
 710 |         return _fallback_script(selections)
 711 |     except Exception as e:
 712 |         logger.error(f"Claude API error: {e}")
 713 |         return _fallback_script(selections)
 714 | 
 715 | 
 716 | 
 717 | def _enforce_setup_per_clip(result: dict, selections: dict) -> dict:
 718 |     """IRON LAW: Every clip rank must have exactly one SETUP segment before it.
 719 |     If the LLM collapses two setups onto clip_rank 1 and skips clip_rank 2,
 720 |     this function detects and repairs it by inserting a bridging setup."""
 721 |     import logging
 722 |     _log = logging.getLogger(__name__)
 723 |     dialogue = result.get("dialogue", [])
 724 |     clips = selections.get("clips", [])
 725 |     clip_ranks = [c.get("rank", 0) for c in clips if c.get("rank")]
 726 | 
 727 |     # Find which ranks have a setup
 728 |     setup_ranks = set()
 729 |     for entry in dialogue:
 730 |         if isinstance(entry, dict) and entry.get("type") == "setup":
 731 |             cr = entry.get("clip_rank")
 732 |             if cr:
 733 |                 setup_ranks.add(cr)
 734 | 
 735 |     missing = [r for r in clip_ranks if r not in setup_ranks]
 736 |     if not missing:
 737 |         return result
 738 | 
 739 |     _log.warning(f"[script] SETUP MISSING for clip ranks: {missing} — inserting bridge narration")
 740 |     clips_by_rank = {c.get("rank"): c for c in clips}
 741 |     new_dialogue = []
 742 |     for entry in dialogue:
 743 |         if isinstance(entry, dict) and entry.get("host") == "CLIP":
 744 |             rank = entry.get("rank", 0)
 745 |             if rank in missing:
 746 |                 ch = clips_by_rank.get(rank, {}).get("channel", "our next source")
 747 |                 bridge = {
 748 |                     "host": 2,
 749 |                     "text": f"[NARRATION] Now — {ch} brings a signal you need to hear.",
 750 |                     "type": "setup",
 751 |                     "clip_rank": rank,
 752 |                     "headline": f"{ch.upper()} SIGNAL"
 753 |                 }
 754 |                 new_dialogue.append(bridge)
 755 |                 missing.remove(rank)
 756 |         new_dialogue.append(entry)
 757 |     result["dialogue"] = new_dialogue
 758 |     return result
 759 | 
 760 | def _enforce_social_segment(result: dict, social_data: list) -> dict:
 761 |     """Postcondition: if social_data was non-empty, at least one social_segment MUST exist.
 762 |     If the LLM omitted social segments, inject them before the wrap."""
 763 |     if not social_data:
 764 |         return result
 765 | 
 766 |     dialogue = result.get("dialogue", [])
 767 |     social_entries = [d for d in dialogue if d.get("type") == "social_segment"]
 768 |     if social_entries:
 769 |         return result  # LLM did its job
 770 | 
 771 |     logger.warning(f"[script] SOCIAL SEGMENT MISSING — LLM omitted {len(social_data)} tweets. Injecting.")
 772 | 
 773 |     # Build social_segment entries from the actual tweet data
 774 |     inject = []
 775 |     for i, post in enumerate(social_data[:3]):
 776 |         handle = post.get("handle", "unknown")
 777 |         text = post.get("text", "")[:200]
 778 |         likes = post.get("likes", 0)
 779 |         narration = (
 780 |             f"[SOCIAL] {handle} posted this to {likes:,} likes — \"{text}\". "
 781 |             f"The signal here is clear."
 782 |         )
 783 |         inject.append({
 784 |             "host": 2,
 785 |             "text": narration,
 786 |             "type": "social_segment",
 787 |         })
 788 | 
 789 |     # Insert before the final wrap entry
 790 |     wrap_idx = None
 791 |     for i in range(len(dialogue) - 1, -1, -1):
 792 |         if dialogue[i].get("type") == "wrap":
 793 |             wrap_idx = i
 794 |             break
 795 | 
 796 |     if wrap_idx is not None:
 797 |         for j, entry in enumerate(inject):
 798 |             dialogue.insert(wrap_idx + j, entry)
 799 |     else:
 800 |         dialogue.extend(inject)
 801 | 
 802 |     result["dialogue"] = dialogue
 803 |     logger.info(f"[script] Injected {len(inject)} social_segment entries")
 804 |     return result
 805 | 
 806 | 
 807 | def _enforce_space_tap_segment(result: dict, space_tap_clips: list) -> dict:
 808 |     """Postcondition: if space_tap_clips was non-empty, at least one SPACE_CLIP must exist.
 809 |     If the LLM omitted space tap, inject intro/clip/react entries before the wrap."""
 810 |     if not space_tap_clips:
 811 |         return result
 812 | 
 813 |     dialogue = result.get("dialogue", [])
 814 |     space_entries = [d for d in dialogue if d.get("host") == "SPACE_CLIP"
 815 |                      or (d.get("type") or "").startswith("space_tap")]
 816 |     if space_entries:
 817 |         return result  # LLM included space tap
 818 | 
 819 |     logger.warning(f"[script] SPACE TAP MISSING — LLM omitted {len(space_tap_clips)} clips. Injecting.")
 820 | 
 821 |     inject = []
 822 |     for i, clip in enumerate(space_tap_clips):
 823 |         handle = clip.get("host_handle", "unknown")
 824 |         inject.append({
 825 |             "host": 2,
 826 |             "text": f"[SPACE_TAP] Signal intercepted from {handle}'s space.",
 827 |             "type": "space_tap_intro",
 828 |         })
 829 |         inject.append({
 830 |             "host": "SPACE_CLIP",
 831 |             "clip_index": i,
 832 |         })
 833 |         inject.append({
 834 |             "host": 2,
 835 |             "text": "[SPACE_TAP] That's a signal worth tracking.",
 836 |             "type": "space_tap_react",
 837 |         })
 838 | 
 839 |     # Insert before the wrap (after social if present)
 840 |     wrap_idx = None
 841 |     for i in range(len(dialogue) - 1, -1, -1):
 842 |         if dialogue[i].get("type") == "wrap":
 843 |             wrap_idx = i
 844 |             break
 845 | 
 846 |     if wrap_idx is not None:
 847 |         for j, entry in enumerate(inject):
 848 |             dialogue.insert(wrap_idx + j, entry)
 849 |     else:
 850 |         dialogue.extend(inject)
 851 | 
 852 |     result["dialogue"] = dialogue
 853 |     logger.info(f"[script] Injected {len(inject)} space_tap entries for {len(space_tap_clips)} clips")
 854 |     return result
 855 | 
 856 | 
 857 | def _fallback_script(selections: dict) -> dict:
 858 |     """Generate a basic script from clip selections without Claude."""
 859 |     clips = selections.get("clips", [])
 860 |     cold_open = selections.get("cold_open", "Breaking developments in Bitcoin today.")
 861 | 
 862 |     dialogue = [
 863 |         {"host": 2, "text": f"[COLD_OPEN] {cold_open}", "type": "cold_open"},  # IRON LAW: PBX always opens
 864 |     ]
 865 | 
 866 |     for c in clips:
 867 |         rank = c.get("rank", 0)
 868 |         setup = c.get("host_setup", f"Check out what {c.get('channel', 'this channel')} just dropped.")
 869 |         react = c.get("host_react", "That's a big deal. The market hasn't priced this in yet.")
 870 | 
 871 |         dialogue.append({"host": 2, "text": f"[NARRATION] {setup}", "type": "setup", "clip_rank": rank})
 872 |         dialogue.append({"host": "CLIP", "rank": rank})
 873 |         dialogue.append({"host": 2, "text": f"[NARRATION] {react}", "type": "react", "clip_rank": rank})
 874 | 
 875 |     dialogue.append({
 876 |         "host": 2,
 877 |         "text": "[WARM] That's your Pulse Check for today. Stay sovereign.",
 878 |         "type": "wrap",
 879 |     })
 880 | 
 881 |     title = selections.get("episode_title", "Pulse Check Daily")
 882 | 
 883 |     return {
 884 |         "cold_open": cold_open,
 885 |         "dialogue": dialogue,
 886 |         "episode_title": title,
 887 |         "thumbnail": {"headline": title.upper(), "subtext": "Daily Bitcoin Intelligence"},
 888 |         "segments_summary": [c.get("why", "") for c in clips],
 889 |         "shorts_quotes": [c.get("quote", "")[:80] for c in clips[:3]],
 890 |     }
 891 | 
 892 | 
 893 | # Legacy compatibility
 894 | def generate_script(stories=None, style="default", btc_price="N/A"):
 895 |     """Legacy wrapper — generate a sample script for testing."""
 896 |     logger.info("Legacy generate_script called — use generate_from_clips for V5 pipeline")
 897 |     return generate_sample_script(style)
 898 | 
 899 | 
 900 | def generate_sample_script(style="default"):
 901 |     """Sample script for testing without live data."""
 902 |     return {
 903 |         "episode_title": "The Quiet Accumulation",
 904 |         "cold_open": "Three sovereign wealth funds just disclosed Bitcoin positions worth twelve billion dollars.",
 905 |         "dialogue": [
 906 |             {"host": 2, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},  # IRON LAW: PBX always opens
 907 |             {"host": 2, "text": "Bitcoin Magazine just dropped this bombshell.", "type": "setup", "clip_rank": 1},
 908 |             {"host": "CLIP", "rank": 1},
 909 |             {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything.", "type": "react", "clip_rank": 1},
 910 |             {"host": 2, "text": "And look at what Simply Bitcoin is reporting on hash rate.", "type": "setup", "clip_rank": 2},
 911 |             {"host": "CLIP", "rank": 2},
 912 |             {"host": 2, "text": "Record high hash rate. Miners aren't leaving. They're doubling down.", "type": "react", "clip_rank": 2},
 913 |             {"host": 2, "text": "That's your Pulse Check. Stay sovereign.", "type": "wrap"},
 914 |         ],
 915 |         "thumbnail": {"headline": "SMART MONEY IS MOVING", "subtext": "Nations are stacking"},
 916 |         "segments_summary": ["Sovereign wealth funds buying BTC", "Hash rate hits record"],
 917 |         "shorts_quotes": ["When the entities that print fiat start hoarding the exit asset", "Miners aren't leaving"],
 918 |     }
 919 | 
 920 | 
 921 | if __name__ == "__main__":
 922 |     script = generate_sample_script()
 923 |     print(json.dumps(script, indent=2))
 924 | 
```

### File: video_pipeline_v3/tts_engine.py (1479 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V11 — Dual-host local TTS pipeline.
   3 | Host 1: Kokoro af_heart (female) — setup/bridge.
   4 | Host 2: Kokoro am_onyx (male) — react/wrap. F5-TTS PBX when ready.
   5 | Fallback: ElevenLabs per-line. TTS_PROVIDER=local (default) or elevenlabs.
   6 | Inter-line silence: 0.08s (ElevenLabs has natural pauses built in).
   7 | Parallel TTS pre-generation via ThreadPoolExecutor."""
   8 | import os, sys, json, subprocess, tempfile, time, struct, shutil, logging, re
   9 | from concurrent.futures import ThreadPoolExecutor, as_completed
  10 | from pathlib import Path
  11 | 
  12 | try:
  13 |     import requests
  14 |     HAS_REQUESTS = True
  15 | except ImportError:
  16 |     HAS_REQUESTS = False
  17 | 
  18 | from relay import get_key
  19 | 
  20 | logger = logging.getLogger(__name__)
  21 | 
  22 | # ── LOCAL TTS BACKENDS ──────────────────────────────────────────────────────
  23 | _KOKORO_PIPELINE = None
  24 | _KOKORO_BACKEND = None
  25 | _KOKORO_INSTANCE = None
  26 | _F5_MODEL = None
  27 | _BIGVGAN_MODEL = None
  28 | _CHATTERBOX_MODEL = None
  29 | _PROSODY_CACHE = {}  # hash(text) -> prosody-planned text
  30 | 
  31 | 
  32 | def _init_kokoro():
  33 |     """Lazy-initialize Kokoro (PyTorch first, ONNX fallback)."""
  34 |     global _KOKORO_PIPELINE, _KOKORO_BACKEND, _KOKORO_INSTANCE
  35 |     if _KOKORO_BACKEND is not None:
  36 |         return _KOKORO_BACKEND
  37 |     try:
  38 |         from kokoro import KPipeline
  39 |         _KOKORO_PIPELINE = KPipeline(lang_code='a')
  40 |         _KOKORO_BACKEND = "pytorch"
  41 |         logger.info("[TTS/Kokoro] Backend: PyTorch")
  42 |         return "pytorch"
  43 |     except Exception as e_pt:
  44 |         logger.warning(f"[TTS/Kokoro] PyTorch failed: {e_pt} — trying ONNX")
  45 |     try:
  46 |         from kokoro_onnx import Kokoro as _KokoroONNX
  47 |         _VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
  48 |         _onnx_model = os.path.join(_VOICES_DIR, "kokoro-v0_19.onnx")
  49 |         _onnx_voices = os.path.join(_VOICES_DIR, "voices-v1.0.bin")
  50 |         if not os.path.exists(_onnx_model):
  51 |             logger.info("[TTS/Kokoro] Downloading ONNX model files...")
  52 |             subprocess.run([
  53 |                 "python3", "-c",
  54 |                 "from huggingface_hub import hf_hub_download; "
  55 |                 f"hf_hub_download('hexgrad/Kokoro-82M', 'kokoro-v0_19.onnx', local_dir='{_VOICES_DIR}'); "
  56 |                 f"hf_hub_download('hexgrad/Kokoro-82M', 'voices-v1.0.bin', local_dir='{_VOICES_DIR}')"
  57 |             ], timeout=300)
  58 |         _KOKORO_INSTANCE = _KokoroONNX(_onnx_model, _onnx_voices)
  59 |         _KOKORO_BACKEND = "onnx"
  60 |         logger.info("[TTS/Kokoro] Backend: ONNX")
  61 |         return "onnx"
  62 |     except Exception as e_onnx:
  63 |         logger.error(f"[TTS/Kokoro] Both backends failed: {e_onnx}")
  64 |         _KOKORO_BACKEND = "unavailable"
  65 |         return "unavailable"
  66 | 
  67 | 
  68 | def _init_f5():
  69 |     """Lazy-initialize fine-tuned F5-TTS model."""
  70 |     global _F5_MODEL
  71 |     if _F5_MODEL is not None:
  72 |         return True
  73 |     ckpt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "pbx_voice.pt")
  74 |     if not os.path.exists(ckpt):
  75 |         logger.warning(f"[TTS/F5] Fine-tuned checkpoint missing: {ckpt}")
  76 |         return False
  77 |     try:
  78 |         from f5_tts.api import F5TTS
  79 |         _F5_MODEL = F5TTS(model="F5TTS_v1_Base", ckpt_file=ckpt, device="cuda:1")
  80 |         logger.info(f"[TTS/F5] Fine-tuned model loaded: {ckpt}")
  81 |         return True
  82 |     except Exception as e:
  83 |         logger.error(f"[TTS/F5] Failed to load checkpoint: {e}")
  84 |         return False
  85 | 
  86 | 
  87 | def _init_chatterbox():
  88 |     """Lazy-initialize Chatterbox TTS on cuda:0."""
  89 |     global _CHATTERBOX_MODEL
  90 |     if _CHATTERBOX_MODEL is not None:
  91 |         return True
  92 |     try:
  93 |         from chatterbox.tts import ChatterboxTTS
  94 |         _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device="cuda:0")
  95 |         logger.info("[TTS/Chatterbox] Model loaded on cuda:0")
  96 |         return True
  97 |     except Exception as e:
  98 |         logger.error(f"[TTS/Chatterbox] Failed to load: {e}")
  99 |         return False
 100 | 
 101 | 
 102 | def _init_bigvgan():
 103 |     """Lazy-initialize BigVGAN2 44kHz vocoder on cuda:1."""
 104 |     global _BIGVGAN_MODEL
 105 |     if _BIGVGAN_MODEL is not None:
 106 |         return True
 107 |     try:
 108 |         import bigvgan as _bv
 109 |         _BIGVGAN_MODEL = _bv.BigVGAN.from_pretrained(
 110 |             "nvidia/bigvgan_v2_44khz_128band_512x",
 111 |             use_cuda_kernel=False,
 112 |         )
 113 |         _BIGVGAN_MODEL = _BIGVGAN_MODEL.eval().to("cuda:1")
 114 |         logger.info("[TTS/BigVGAN2] 44kHz vocoder loaded on cuda:1")
 115 |         return True
 116 |     except Exception as e:
 117 |         logger.error(f"[TTS/BigVGAN2] Init failed: {e}")
 118 |         return False
 119 | 
 120 | 
 121 | def _bigvgan_upsample(wav_path_24k: str) -> str:
 122 |     """Upsample 24kHz WAV to 44kHz via BigVGAN2. Returns path to 44kHz WAV.
 123 |     Graceful fallback: returns original path if BigVGAN2 fails."""
 124 |     if not _init_bigvgan():
 125 |         return wav_path_24k
 126 |     try:
 127 |         import torch
 128 |         import soundfile as sf
 129 |         import librosa
 130 |         wav_data, sr = sf.read(wav_path_24k)
 131 |         if sr != 24000:
 132 |             wav_data = librosa.resample(wav_data, orig_sr=sr, target_sr=24000)
 133 |         # BigVGAN expects mel spectrogram input — compute from audio
 134 |         import torchaudio
 135 |         wav_tensor = torch.FloatTensor(wav_data).unsqueeze(0).to("cuda:1")
 136 |         # Use torchaudio to compute mel spectrogram matching BigVGAN's expected input
 137 |         mel_transform = torchaudio.transforms.MelSpectrogram(
 138 |             sample_rate=24000, n_fft=2048, hop_length=256, n_mels=128,
 139 |             f_min=0, f_max=12000,
 140 |         ).to("cuda:1")
 141 |         mel = mel_transform(wav_tensor)
 142 |         mel = torch.log(torch.clamp(mel, min=1e-5))
 143 |         with torch.inference_mode():
 144 |             wav_out = _BIGVGAN_MODEL(mel)
 145 |         wav_np = wav_out.squeeze().cpu().numpy()
 146 |         out_path = wav_path_24k.replace(".wav", ".44k.wav")
 147 |         sf.write(out_path, wav_np, 44100)
 148 |         logger.info(f"[TTS/BigVGAN2] Upsampled {wav_path_24k} → {out_path}")
 149 |         return out_path
 150 |     except Exception as e:
 151 |         logger.warning(f"[TTS/BigVGAN2] Upsample failed: {e} — using 24kHz")
 152 |         return wav_path_24k
 153 | 
 154 | 
 155 | def prosody_plan(text: str, host: int = 2) -> str:
 156 |     """Strip all [bracket] prosody markers and return clean text.
 157 |     Prosody injection disabled — markers caused TTS artifacts."""
 158 |     import re
 159 |     return re.sub(r'\[.*?\]', '', text).strip()
 160 | 
 161 | 
 162 | PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"
 163 | 
 164 | _PBX_VOICE = {
 165 |     "voice_id": PBX_VOICE_ID,
 166 |     "name": "PBX",
 167 |     "model_id": "eleven_multilingual_v2",
 168 |     "speed": 1.0,  # Multilingual v2: natural broadcast pace, no speedup needed
 169 |     "voice_settings": {
 170 |         "stability": 0.50,
 171 |         "similarity_boost": 0.85,
 172 |         "style": 0.30,
 173 |         "use_speaker_boost": True,
 174 |     },
 175 | }
 176 | 
 177 | # ── LOCAL TTS VOICE CONFIG ──────────────────────────────────────────────────
 178 | VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
 179 | PBX_CHECKPOINT = "/home/ultron/.local/lib/python3.10/ckpts/pbx_voice/model_500.pt"  # PBX voice model_500
 180 | PBX_REFERENCE_CLIP = os.path.join(VOICES_DIR, "pbx_reference.wav")
 181 | KOKORO_HOST1_VOICE = "af_heart"
 182 | KOKORO_HOST2_VOICE = "am_onyx"   # primary; swap for PBX F5 when ready
 183 | F5_SPEED = 1.1
 184 | KOKORO_SPEED_H1 = 1.0
 185 | KOKORO_SPEED_H2 = 1.1
 186 | 
 187 | _ERYN_VOICE = {
 188 |     "voice_id": "kdnRe2koJdOK4Ovxn2DI",
 189 |     "name": "Eryn",
 190 |     "model_id": "eleven_turbo_v2_5",
 191 |     "speed": 1.0,
 192 |     "voice_settings": {
 193 |         "stability": 0.55,
 194 |         "similarity_boost": 0.80,
 195 |         "style": 0.15,
 196 |         "use_speaker_boost": True,
 197 |     },
 198 | }
 199 | # Dual-host: HOST_1 = Eryn/af_heart (female), HOST_2 = PBX (fine-tuned F5 / ElevenLabs fallback)
 200 | VOICES = {
 201 |     1: _ERYN_VOICE,
 202 |     2: _PBX_VOICE,
 203 | }
 204 | 
 205 | def _get_tts_provider() -> str:
 206 |     """TTS provider selector.
 207 |     'local'      → Kokoro af_heart (host1) + Chatterbox PBX (host2) + ElevenLabs fallback
 208 |     'elevenlabs' → ElevenLabs only (emergency override, preserves single-host Option A)
 209 |     """
 210 |     val = os.environ.get("TTS_PROVIDER", "local").lower().strip()
 211 |     if val not in ("local", "elevenlabs"):
 212 |         logger.warning(f"[TTS] Unknown TTS_PROVIDER='{val}', defaulting to 'local'")
 213 |         return "local"
 214 |     return val
 215 | 
 216 | 
 217 | _KEY_CACHE: dict = {}
 218 | 
 219 | def _get_cached_key(name: str) -> str:
 220 |     if name not in _KEY_CACHE:
 221 |         k = get_key(name)
 222 |         if k:
 223 |             _KEY_CACHE[name] = k.strip()
 224 |     return _KEY_CACHE.get(name, "")
 225 | 
 226 | 
 227 | def ffprobe_duration(path: str) -> float:
 228 |     r = subprocess.run(
 229 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 230 |          "-of", "csv=p=0", path],
 231 |         capture_output=True, text=True,
 232 |     )
 233 |     try:
 234 |         return float(r.stdout.strip())
 235 |     except Exception:
 236 |         logger.warning(f"[TTS] ffprobe_duration failed for {path}")
 237 |         return -1.0
 238 | 
 239 | 
 240 | def _generate_silence(output_path: str, duration: float) -> bool:
 241 |     """Generate a silent audio file."""
 242 |     r = subprocess.run(
 243 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
 244 |          f"anullsrc=r=48000:cl=stereo", "-t", str(duration),
 245 |          "-c:a", "aac", "-b:a", "192k", output_path],
 246 |         capture_output=True, text=True, timeout=30,
 247 |     )
 248 |     return r.returncode == 0 and os.path.exists(output_path)
 249 | 
 250 | 
 251 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 252 |     # eleven_multilingual_v2 at speed=1.0 — no atempo needed (natural broadcast pace)
 253 |     r = subprocess.run(
 254 |         ["ffmpeg", "-y", "-i", mp3_path,
 255 |          "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", m4a_path],
 256 |         capture_output=True, text=True, timeout=120,
 257 |     )
 258 |     return r.returncode == 0 and os.path.exists(m4a_path)
 259 | 
 260 | 
 261 | MAX_CHUNK_CHARS = 500  # ElevenLabs safe chunk size
 262 | SILENCE_GAP = 0.08  # seconds between lines — ElevenLabs has natural pauses built in
 263 | 
 264 | # Voice mode overrides per segment type (applied to whichever host speaks)
 265 | VOICE_MODES = {
 266 |     "cold_open":       {"stability": 0.42, "similarity_boost": 0.85, "style": 0.35},
 267 |     "setup":           {"stability": 0.50, "similarity_boost": 0.85, "style": 0.30},
 268 |     "react":           {"stability": 0.48, "similarity_boost": 0.85, "style": 0.32},
 269 |     "bridge":          {"stability": 0.50, "similarity_boost": 0.85, "style": 0.28},
 270 |     "social_segment":  {"stability": 0.48, "similarity_boost": 0.85, "style": 0.32},
 271 |     "wrap":            {"stability": 0.45, "similarity_boost": 0.85, "style": 0.35},
 272 | }
 273 | 
 274 | 
 275 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 276 |     if len(text) <= max_chars:
 277 |         return [text]
 278 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 279 |     sentences = raw.split("\x00")
 280 |     chunks, current = [], ""
 281 |     for sent in sentences:
 282 |         if len(current) + len(sent) + 1 <= max_chars:
 283 |             current = f"{current} {sent}".strip() if current else sent
 284 |         else:
 285 |             if current:
 286 |                 chunks.append(current)
 287 |             current = sent
 288 |     if current:
 289 |         chunks.append(current)
 290 |     return [c for c in chunks if c.strip()]
 291 | 
 292 | 
 293 | def expand_numbers_for_tts(text: str) -> str:
 294 |     """Round 2 Fix 1: Full num2words preprocessing — converts ALL numbers >999 to spoken form.
 295 | 
 296 |     Previous version used manual thousand/million/billion templates which caused garbled
 297 |     speech on numbers like "1,056 EH/s" or "$74,000". Now uses num2words for natural
 298 |     spoken-word output: "$74,000" → "seventy-four thousand dollars".
 299 |     """
 300 |     import re as _re
 301 |     try:
 302 |         from num2words import num2words as _n2w
 303 |     except ImportError:
 304 |         logger.warning("[TTS] num2words not installed — falling back to basic expansion")
 305 |         return _expand_numbers_basic(text)
 306 | 
 307 |     # Issue 12: Year detection BEFORE general number expansion
 308 |     # 4-digit numbers 1600-2099 not preceded by $ or currency → spoken as years
 309 |     def _year_to_words(y: int) -> str:
 310 |         """Convert year number to spoken form: 1602→sixteen oh two, 2024→twenty twenty-four."""
 311 |         if 2000 <= y <= 2009:
 312 |             return f"two thousand {_n2w(y - 2000) if y > 2000 else ''}".strip()
 313 |         if 2010 <= y <= 2099:
 314 |             return f"twenty {_n2w(y - 2000)}"
 315 |         hi = y // 100
 316 |         lo = y % 100
 317 |         hi_word = _n2w(hi)
 318 |         if lo == 0:
 319 |             return f"{hi_word} hundred"
 320 |         elif lo < 10:
 321 |             return f"{hi_word} oh {_n2w(lo)}"
 322 |         else:
 323 |             return f"{hi_word} {_n2w(lo)}"
 324 | 
 325 |     def _year_sub(m):
 326 |         val = int(m.group(0))
 327 |         return _year_to_words(val)
 328 |     # Match 1600-2099 NOT preceded by $ or digits
 329 |     text = _re.sub(r'(?<!\$)(?<!\d)\b(1[6-9]\d{2}|20[0-9]\d)\b(?!\s*(?:EH|TH|PH|dollars|percent|%|K\b))', _year_sub, text)
 330 | 
 331 |     # Dollar + billion/million shorthand first: $308 billion → "three hundred and eight billion dollars"
 332 |     def _dollar_scale(m):
 333 |         num_str = m.group(1)
 334 |         scale = m.group(2).lower()
 335 |         try:
 336 |             val = float(num_str)
 337 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 338 |             return f"{spoken} {scale} dollars"
 339 |         except Exception:
 340 |             return m.group(0)
 341 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _dollar_scale, text)
 342 | 
 343 |     # Dollar amounts: $74,000 → "seventy-four thousand dollars"
 344 |     def _dollar(m):
 345 |         val_str = m.group(1).replace(",", "")
 346 |         try:
 347 |             val = int(float(val_str))
 348 |             if val > 999:
 349 |                 return f"{_n2w(val)} dollars"
 350 |             return f"{val} dollars"
 351 |         except Exception:
 352 |             return m.group(0)
 353 |     text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)
 354 | 
 355 |     # Hashrate units BEFORE plain numbers (so "1,056 EH/s" is caught here)
 356 |     def _hashrate(m):
 357 |         val_str = m.group(1).replace(",", "")
 358 |         unit = m.group(2)
 359 |         unit_map = {"EH": "exahashes", "TH": "terahashes", "PH": "petahashes"}
 360 |         try:
 361 |             val = float(val_str)
 362 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 363 |             return f"{spoken} {unit_map.get(unit, unit)} per second"
 364 |         except Exception:
 365 |             return m.group(0)
 366 |     text = _re.sub(r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(EH|TH|PH)/?s', _hashrate, text)
 367 | 
 368 |     # Percentages: 42% → "forty-two percent"
 369 |     def _pct(m):
 370 |         val_str = m.group(1)
 371 |         try:
 372 |             val = float(val_str)
 373 |             if val == int(val):
 374 |                 return f"{_n2w(int(val))} percent"
 375 |             # 8.4% → "eight point four percent"
 376 |             whole = int(val)
 377 |             frac = val_str.split('.')[1] if '.' in val_str else ''
 378 |             if frac:
 379 |                 frac_spoken = ' '.join(_n2w(int(d)) for d in frac)
 380 |                 return f"{_n2w(whole)} point {frac_spoken} percent"
 381 |             return f"{_n2w(int(val))} percent"
 382 |         except Exception:
 383 |             return m.group(0)
 384 |     text = _re.sub(r'([\d.]+)%', _pct, text)
 385 | 
 386 |     # Large plain numbers with commas: 70,015 → "seventy thousand and fifteen"
 387 |     def _plain_num(m):
 388 |         val_str = m.group(0).replace(",", "")
 389 |         try:
 390 |             val = int(val_str)
 391 |             if val > 999:
 392 |                 return _n2w(val)
 393 |             return m.group(0)
 394 |         except Exception:
 395 |             return m.group(0)
 396 |     text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)
 397 | 
 398 |     # Billion/million shorthand in text (no dollar): 1.2 billion → "one point two billion"
 399 |     def _scale(m):
 400 |         val_str = m.group(1)
 401 |         scale = m.group(2).lower()
 402 |         try:
 403 |             val = float(val_str)
 404 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 405 |             return f"{spoken} {scale}"
 406 |         except Exception:
 407 |             return m.group(0)
 408 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _scale, text)
 409 | 
 410 |     # K shorthand: 74K → "seventy-four thousand"
 411 |     def _k(m):
 412 |         try:
 413 |             val = float(m.group(1))
 414 |             return _n2w(int(val * 1000))
 415 |         except Exception:
 416 |             return m.group(0)
 417 |     text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)
 418 | 
 419 |     # Standalone large numbers without commas (e.g. 74000)
 420 |     def _bare_num(m):
 421 |         try:
 422 |             val = int(m.group(0))
 423 |             if val > 999:
 424 |                 return _n2w(val)
 425 |             return m.group(0)
 426 |         except Exception:
 427 |             return m.group(0)
 428 |     text = _re.sub(r'\b\d{4,}\b', _bare_num, text)
 429 | 
 430 |     # Issue 6: Strip commas and "and" from num2words output to prevent micro-pauses
 431 |     text = _re.sub(r'(\w),\s', r'\1 ', text)  # remove commas in spoken numbers
 432 |     text = _re.sub(r'\band\b\s*', '', text)  # remove "and" (e.g. "one hundred and fifty" → "one hundred fifty")
 433 |     text = _re.sub(r'\s{2,}', ' ', text)  # collapse double spaces
 434 | 
 435 |     return text
 436 | 
 437 | 
 438 | def _expand_numbers_basic(text: str) -> str:
 439 |     """Fallback number expansion without num2words (original logic)."""
 440 |     import re as _re
 441 | 
 442 |     def _dollar(m):
 443 |         val_str = m.group(1).replace(",", "")
 444 |         try:
 445 |             val = int(float(val_str))
 446 |         except ValueError:
 447 |             return m.group(0)
 448 |         if val >= 1_000_000_000:
 449 |             return f"{val/1_000_000_000:.1f} billion dollars".replace(".0 ", " ")
 450 |         if val >= 1_000_000:
 451 |             return f"{val/1_000_000:.1f} million dollars".replace(".0 ", " ")
 452 |         if val >= 1_000:
 453 |             b = val // 1000
 454 |             r = val % 1000
 455 |             if r == 0:
 456 |                 return f"{b} thousand dollars"
 457 |             return f"{b} thousand {r} dollars"
 458 |         return f"{val} dollars"
 459 | 
 460 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)
 461 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)
 462 |     text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)
 463 | 
 464 |     def _plain_num(m):
 465 |         val_str = m.group(0).replace(",", "")
 466 |         try:
 467 |             val = int(val_str)
 468 |         except ValueError:
 469 |             return m.group(0)
 470 |         if val >= 1_000_000_000:
 471 |             return f"{val/1_000_000_000:.1f} billion".replace(".0 ", " ")
 472 |         if val >= 1_000_000:
 473 |             return f"{val/1_000_000:.1f} million".replace(".0 ", " ")
 474 |         if val >= 10_000:
 475 |             b = val // 1000
 476 |             r = val % 1000
 477 |             if r == 0:
 478 |                 return f"{b} thousand"
 479 |             return f"{b} thousand {r}"
 480 |         return m.group(0)
 481 |     text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)
 482 | 
 483 |     def _pct(m):
 484 |         return m.group(1).replace(".", " point ") + " percent"
 485 |     text = _re.sub(r'([\d.]+)%', _pct, text)
 486 | 
 487 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*EH/?s', lambda m: f"{m.group(1)} exahash per second", text)
 488 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*TH/?s', lambda m: f"{m.group(1)} terahash per second", text)
 489 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*PH/?s', lambda m: f"{m.group(1)} petahash per second", text)
 490 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion", text)
 491 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million", text)
 492 | 
 493 |     def _k(m):
 494 |         val = float(m.group(1))
 495 |         if val == int(val):
 496 |             return f"{int(val)} thousand"
 497 |         return f"{val} thousand"
 498 |     text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)
 499 | 
 500 |     return text
 501 | 
 502 | 
 503 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 504 | 
 505 | 
 506 | 
 507 | # ── Bitcoin Ecosystem Pronunciation Map ────────────────────────────────────
 508 | # ElevenLabs renders these phonetic substitutions naturally.
 509 | # Longer/more specific entries first to avoid partial replacements.
 510 | PRONUNCIATION_MAP = {
 511 |     # Satoshi
 512 |     "Satoshi Nakamoto": "sah TOE shee nah kah MOE toe",
 513 |     "Satoshi": "sah TOE shee",
 514 |     "Nakamoto": "nah kah MOE toe",
 515 |     # Saylor
 516 |     "Michael Saylor": "Michael Sayler",
 517 |     "Saylor": "Sayler",
 518 |     # Lyn Alden
 519 |     "Lyn Alden": "Lin AWL-den",
 520 |     # Lummis
 521 |     "Cynthia Lummis": "SIN-thee-ah LUM-iss",
 522 |     "Lummis": "LUM-iss",
 523 |     # Brunell
 524 |     "Natalie Brunell": "Natalie Brunelle",
 525 |     "Brunell": "Brunelle",
 526 |     # Preston Pysh
 527 |     "Preston Pysh": "Preston PISH",
 528 |     "Pysh": "PISH",
 529 |     # Max Keiser
 530 |     "Max Keiser": "MAX KY-zer",
 531 |     "Keiser": "KY-zer",
 532 |     # Nayib Bukele
 533 |     "Nayib Bukele": "NYE-eeb boo-KEH-leh",
 534 |     "Bukele": "boo-KEH-leh",
 535 |     # Saifedean Ammous
 536 |     "Saifedean Ammous": "sy-feh-DEAN AH-moos",
 537 |     "Saifedean": "sy-feh-DEAN",
 538 |     "Ammous": "AH-moos",
 539 |     # Robert Breedlove
 540 |     "Robert Breedlove": "Robert BREED love",
 541 |     "Breedlove": "BREED love",
 542 |     # Alex Gladstein
 543 |     "Alex Gladstein": "AL-ex GLAD-steen",
 544 |     "Gladstein": "GLAD-steen",
 545 |     # Knut Svanholm
 546 |     "Knut Svanholm": "kuh-NOOT SVAHN-holm",
 547 |     "Svanholm": "SVAHN-holm",
 548 |     # Luke Dashjr
 549 |     "Luke Dashjr": "LUKE DASH-junior",
 550 |     "Dashjr": "DASH-junior",
 551 |     # Andreas Antonopoulos
 552 |     "Andreas Antonopoulos": "ahn-DRAY-us an-TON-oh-POO-lus",
 553 |     "Antonopoulos": "an-TON-oh-POO-lus",
 554 |     "Andreas": "ahn-DRAY-us",
 555 |     # Charlie Shrem
 556 |     "Charlie Shrem": "CHAR-lee SHREM",
 557 |     "Shrem": "SHREM",
 558 |     # Lawrence Lepard
 559 |     "Lawrence Lepard": "LAW-rents leh-PARD",
 560 |     "Larry Lepard": "LAIR-ee leh-PARD",
 561 |     "Lepard": "leh-PARD",
 562 |     # Erik Voorhees
 563 |     "Erik Voorhees": "AIR-ik VOR-hees",
 564 |     "Voorhees": "VOR-hees",
 565 |     # Gabor Gurbacs
 566 |     "Gabor Gurbacs": "GAH-bor GUR-bacs",
 567 |     "Gurbacs": "GUR-bacs",
 568 |     # Gary Gensler
 569 |     "Gary Gensler": "GAIR-ee GENZ-ler",
 570 |     "Gensler": "GENZ-ler",
 571 |     # Jerome Powell
 572 |     "Jerome Powell": "jeh-ROME POW-ul",
 573 |     "Powell": "POW-ul",
 574 |     # CJ Konstantinos
 575 |     "CJ Konstantinos": "see-JAY kon-stan-TEE-nos",
 576 |     "Konstantinos": "kon-stan-TEE-nos",
 577 |     # Bob Iaccino
 578 |     "Bob Iaccino": "BOB ee-ah-CHEE-no",
 579 |     "Iaccino": "ee-ah-CHEE-no",
 580 |     # Alex Stanczyk
 581 |     "Alex Stanczyk": "AL-ex STAN-chik",
 582 |     "Stanczyk": "STAN-chik",
 583 |     # Matt Odell
 584 |     "Matt Odell": "MAT OH-dell",
 585 |     "Odell": "OH-dell",
 586 |     # Marty Bent
 587 |     "Marty Bent": "MAR-tee BENT",
 588 |     # Willy Woo
 589 |     "Willy Woo": "WIL-ee WOO",
 590 |     # Technical terms
 591 |     "EH/s": "exahashes per second",
 592 |     "TH/s": "terahashes per second",
 593 |     "PH/s": "petahashes per second",
 594 |     "UTXO": "you-tee-ex-oh",
 595 |     "HODL": "HODDLE",
 596 |     "blockchain": "blockchain",
 597 |     "halving": "HAV-ing",
 598 |     "SegWit": "SEG-wit",
 599 |     "Segwit": "SEG-wit",
 600 |     "hodl": "HODDLE",
 601 |     "mempool": "mem-pool",
 602 |     "multisig": "MUL-tee-sig",
 603 |     "satoshis": "sah-TOH-sheez",
 604 |     "MicroStrategy": "MY-crow-STRAT-uh-jee",
 605 |     "Coinbase": "KOYN-base",
 606 |     "Binance": "BY-nance",
 607 |     "Chainalysis": "CHAIN-uh-LY-sis",
 608 |     # Issue 10: BTC → Bitcoin spoken form
 609 |     "BTC": "Bitcoin",
 610 | }
 611 | 
 612 | 
 613 | def _expand_handle(handle: str) -> str:
 614 |     """Issue 11: Convert @handle to spoken form.
 615 |     CamelCase → separate words, underscores → spaces, ALL CAPS → spelled out."""
 616 |     import re as _re
 617 |     name = handle.lstrip("@")
 618 |     # ALL CAPS (like TFTC, WBD) → spelled out with dashes
 619 |     if name.isupper() and len(name) <= 6:
 620 |         return "at " + "-".join(name)
 621 |     # Split camelCase: MaxKeiser → Max Keiser
 622 |     name = _re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
 623 |     # Split underscores
 624 |     name = name.replace("_", " ")
 625 |     return "at " + name
 626 | 
 627 | 
 628 | # Known handles with correct spoken forms
 629 | _HANDLE_PRONUNCIATIONS = {
 630 |     "@maxkeiser": "at Max Kaiser",
 631 |     "@prestopysh": "at Preston Pish",
 632 |     "@tftc": "at T-F-T-C",
 633 |     "@wbd": "at W-B-D",
 634 |     "@saborchain": "at Sabor Chain",
 635 | }
 636 | 
 637 | 
 638 | _ORDINAL_MAP = {
 639 |     "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
 640 |     "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
 641 |     "9th": "ninth", "10th": "tenth", "11th": "eleventh", "12th": "twelfth",
 642 |     "13th": "thirteenth", "14th": "fourteenth", "15th": "fifteenth",
 643 |     "16th": "sixteenth", "17th": "seventeenth", "18th": "eighteenth",
 644 |     "19th": "nineteenth", "20th": "twentieth", "21st": "twenty-first",
 645 |     "22nd": "twenty-second", "23rd": "twenty-third", "24th": "twenty-fourth",
 646 |     "25th": "twenty-fifth", "26th": "twenty-sixth", "27th": "twenty-seventh",
 647 |     "28th": "twenty-eighth", "29th": "twenty-ninth", "30th": "thirtieth",
 648 |     "31st": "thirty-first",
 649 | }
 650 | 
 651 | 
 652 | def _expand_ordinals(text: str) -> str:
 653 |     """Pre-process ordinal numbers (e.g. '27th') to spoken form to prevent TTS splitting."""
 654 |     import re as _re
 655 |     def _ordinal_sub(m):
 656 |         key = m.group(0).lower()
 657 |         return _ORDINAL_MAP.get(key, m.group(0))
 658 |     return _re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b', _ordinal_sub, text, flags=_re.IGNORECASE)
 659 | 
 660 | 
 661 | def apply_pronunciation_map(text: str) -> str:
 662 |     """Replace names/terms with phonetic versions ElevenLabs renders correctly.
 663 |     Processes longer entries first to avoid partial replacements."""
 664 |     import re
 665 |     # Pre-process ordinals before pronunciation map
 666 |     text = _expand_ordinals(text)
 667 |     # Issue 11: Pre-process @handles before pronunciation map
 668 |     def _handle_sub(m):
 669 |         raw = m.group(0).lower()
 670 |         if raw in _HANDLE_PRONUNCIATIONS:
 671 |             return _HANDLE_PRONUNCIATIONS[raw]
 672 |         return _expand_handle(m.group(0))
 673 |     text = re.sub(r'@[A-Za-z0-9_]+', _handle_sub, text)
 674 | 
 675 |     # Sort by length descending so longer matches take priority
 676 |     for written, phonetic in sorted(PRONUNCIATION_MAP.items(), key=lambda x: -len(x[0])):
 677 |         # Word-boundary aware replacement (case-insensitive)
 678 |         pattern = re.compile(r'\b' + re.escape(written) + r'\b', re.IGNORECASE)
 679 |         text = pattern.sub(phonetic, text)
 680 |     return text
 681 | 
 682 | 
 683 | def _trim_trailing_silence(audio_path: str) -> None:
 684 |     """Round 2 Fix 2: Trim trailing silence/vowel-stretch from TTS output.
 685 | 
 686 |     Detects if the last 0.5s is significantly quieter than the body (trailing off)
 687 |     and trims it to avoid the stretched-vowel artifact common in ElevenLabs output.
 688 |     """
 689 |     try:
 690 |         import re as _re
 691 |         # Measure RMS of last 0.5s vs body
 692 |         result = subprocess.run(
 693 |             ["ffmpeg", "-i", audio_path, "-af",
 694 |              "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"],
 695 |             capture_output=True, text=True, timeout=15,
 696 |         )
 697 |         # Find silence at end of file
 698 |         dur = ffprobe_duration(audio_path)
 699 |         if dur <= 1.0:
 700 |             return
 701 |         silences = [float(m.group(1)) for m in
 702 |                     _re.finditer(r"silence_start: ([\d.]+)", result.stderr)]
 703 |         if not silences:
 704 |             return
 705 |         last_silence = silences[-1]
 706 |         # If silence starts within last 0.5s, trim there
 707 |         if dur - last_silence <= 0.5 and last_silence > dur * 0.8:
 708 |             trimmed = audio_path + ".trimmed.m4a"
 709 |             trim_ok = subprocess.run(
 710 |                 ["ffmpeg", "-y", "-i", audio_path,
 711 |                  "-t", f"{last_silence + 0.05:.3f}",
 712 |                  "-c:a", "aac", "-ar", "48000", "-b:a", "192k", trimmed],
 713 |                 capture_output=True, text=True, timeout=15,
 714 |             )
 715 |             if trim_ok.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
 716 |                 os.replace(trimmed, audio_path)
 717 |                 logger.info(f"[TTS] Trimmed trailing silence: {dur:.2f}s → {last_silence + 0.05:.2f}s")
 718 |             elif os.path.exists(trimmed):
 719 |                 os.remove(trimmed)
 720 |     except Exception as e:
 721 |         logger.debug(f"[TTS] Trailing silence trim skipped: {e}")
 722 | 
 723 | 
 724 | def _trim_leading_silence(audio_path: str) -> None:
 725 |     """Remove leading silence (<-40dB) from TTS output.
 726 | 
 727 |     ElevenLabs often pads 0.1-0.2s silence at the start of each clip.
 728 |     This accumulates across lines, creating noticeable gaps in the final mix.
 729 |     Uses ffmpeg silenceremove filter to strip sub-40dB audio from the start.
 730 |     """
 731 |     try:
 732 |         dur_before = ffprobe_duration(audio_path)
 733 |         if dur_before <= 0.5:
 734 |             return
 735 |         trimmed = audio_path + ".ltrimmed.m4a"
 736 |         r = subprocess.run(
 737 |             ["ffmpeg", "-y", "-i", audio_path,
 738 |              "-af", "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-40dB",
 739 |              "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", trimmed],
 740 |             capture_output=True, text=True, timeout=15,
 741 |         )
 742 |         if r.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
 743 |             dur_after = ffprobe_duration(trimmed)
 744 |             if dur_after >= dur_before * 0.7:  # sanity: don't trim more than 30%
 745 |                 os.replace(trimmed, audio_path)
 746 |                 if dur_before - dur_after > 0.02:
 747 |                     logger.info(f"[TTS] Trimmed leading silence: {dur_before:.3f}s → {dur_after:.3f}s")
 748 |             else:
 749 |                 os.remove(trimmed)
 750 |         elif os.path.exists(trimmed):
 751 |             os.remove(trimmed)
 752 |     except Exception as e:
 753 |         logger.debug(f"[TTS] Leading silence trim skipped: {e}")
 754 | 
 755 | 
 756 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 757 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 758 |     import hashlib
 759 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 760 |     return hashlib.sha256(payload).hexdigest()[:16]
 761 | 
 762 | 
 763 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 764 |     """Return True if valid cached file exists and passes validation."""
 765 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 766 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10240:
 767 |         shutil.copy2(cache_file, output_path)
 768 |         try:
 769 |             validate_tts_output(output_path)
 770 |             return True
 771 |         except RuntimeError:
 772 |             logger.warning(f"[TTS] Corrupt cache deleted: {cache_file}")
 773 |             try:
 774 |                 os.remove(cache_file)
 775 |                 os.remove(output_path)
 776 |             except Exception:
 777 |                 pass
 778 |     return False
 779 | 
 780 | 
 781 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 782 |     """Save audio to TTS cache for future runs."""
 783 |     import shutil
 784 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 785 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 786 |     if not os.path.exists(cache_file):
 787 |         shutil.copy2(audio_path, cache_file)
 788 | 
 789 | 
 790 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 791 |     """HARD FAIL: silence fallback is no longer allowed.
 792 | 
 793 |     Previously generated silent AAC as a last resort, masking total TTS failure.
 794 |     This caused downstream black frames and F-grade renders that QC scored 94/100.
 795 |     Now raises RuntimeError so the pipeline fails fast instead of rendering garbage.
 796 |     """
 797 |     snippet = (text[:80] + "...") if len(text) > 80 else text
 798 |     raise RuntimeError(
 799 |         f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
 800 |         f"Text: \"{snippet}\". Fix the TTS provider before re-running."
 801 |     )
 802 | 
 803 | 
 804 | def tts_kokoro(text: str, output_path: str, voice: str = "af_heart",
 805 |                speed: float = 1.0) -> bool:
 806 |     """Generate TTS via Kokoro GPU inference. Output: M4A 48kHz AAC 192k."""
 807 |     backend = _init_kokoro()
 808 |     if backend == "unavailable":
 809 |         return False
 810 |     try:
 811 |         import soundfile as sf
 812 |         import numpy as np
 813 |         wav_tmp = output_path + ".kokoro.wav"
 814 |         if backend == "pytorch":
 815 |             samples_list = []
 816 |             for _, _, audio in _KOKORO_PIPELINE(text, voice=voice, speed=speed):
 817 |                 samples_list.append(audio)
 818 |             if not samples_list:
 819 |                 return False
 820 |             audio_np = np.concatenate(samples_list) if len(samples_list) > 1 else samples_list[0]
 821 |             sf.write(wav_tmp, audio_np, 24000)
 822 |         else:
 823 |             samples, sr = _KOKORO_INSTANCE.create(text, voice=voice, speed=speed, lang="en-us")
 824 |             sf.write(wav_tmp, samples, sr)
 825 | 
 826 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 827 |             return False
 828 |         # Direct encode: 24kHz WAV → 48kHz AAC (no BigVGAN2 — causes double-vocoding)
 829 |         r = subprocess.run([
 830 |             "ffmpeg", "-y", "-i", wav_tmp,
 831 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 832 |         ], capture_output=True, text=True, timeout=60)
 833 |         try:
 834 |             if os.path.exists(wav_tmp):
 835 |                 os.remove(wav_tmp)
 836 |         except Exception:
 837 |             pass
 838 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 839 |         if ok:
 840 |             logger.info(f"[TTS/Kokoro] OK: {ffprobe_duration(output_path):.2f}s, voice={voice}")
 841 |         return ok
 842 |     except Exception as e:
 843 |         logger.error(f"[TTS/Kokoro] Exception: {e}")
 844 |         return False
 845 | 
 846 | 
 847 | def tts_chatterbox(text: str, output_path: str, exaggeration: float = 0.4,
 848 |                     cfg_weight: float = 0.5) -> bool:
 849 |     """Generate TTS using Chatterbox for PBX (Host 2).
 850 | 
 851 |     Chatterbox produces clean audio — no post-processing EQ needed.
 852 |     Output: M4A 48kHz AAC 192k.
 853 |     """
 854 |     if not _init_chatterbox():
 855 |         logger.warning("[TTS/Chatterbox] Model not loaded")
 856 |         return False
 857 | 
 858 |     try:
 859 |         import torchaudio
 860 |         wav_tmp = output_path + ".cb.wav"
 861 | 
 862 |         wav = _CHATTERBOX_MODEL.generate(text, exaggeration=exaggeration,
 863 |                                           cfg_weight=cfg_weight)
 864 |         torchaudio.save(wav_tmp, wav, 24000)
 865 | 
 866 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 867 |             logger.error("[TTS/Chatterbox] Zero output from inference")
 868 |             return False
 869 | 
 870 |         # Convert WAV to M4A (48kHz AAC 192k)
 871 |         r = subprocess.run([
 872 |             "ffmpeg", "-y", "-i", wav_tmp,
 873 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 874 |         ], capture_output=True, text=True, timeout=60)
 875 | 
 876 |         try:
 877 |             if os.path.exists(wav_tmp):
 878 |                 os.remove(wav_tmp)
 879 |         except Exception:
 880 |             pass
 881 | 
 882 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 883 |         if ok:
 884 |             logger.info(f"[TTS/Chatterbox] OK: {ffprobe_duration(output_path):.2f}s (PBX)")
 885 |         return ok
 886 |     except Exception as e:
 887 |         logger.error(f"[TTS/Chatterbox] Exception: {e}")
 888 |         return False
 889 | 
 890 | 
 891 | def tts_f5_finetuned(text: str, output_path: str, speed: float = None) -> bool:
 892 |     """Generate TTS using fine-tuned F5-TTS for PBX (Host 2).
 893 | 
 894 |     Uses pbx_voice.pt checkpoint with pbx_reference.wav for voice cloning.
 895 |     Output: M4A 48kHz AAC 192k.
 896 |     CRITICAL: show_info MUST be print or a callable — False crashes F5 (bool not callable).
 897 |     """
 898 |     if not _init_f5():
 899 |         logger.warning("[TTS/F5] Model not loaded")
 900 |         return False
 901 | 
 902 |     if not os.path.exists(PBX_REFERENCE_CLIP):
 903 |         logger.warning(f"[TTS/F5] Reference clip missing: {PBX_REFERENCE_CLIP}")
 904 |         return False
 905 | 
 906 |     if speed is None:
 907 |         speed = F5_SPEED
 908 | 
 909 |     try:
 910 |         import soundfile as sf
 911 |         wav_tmp = output_path + ".f5.wav"
 912 | 
 913 |         wav, sr, _ = _F5_MODEL.infer(
 914 |             ref_file=PBX_REFERENCE_CLIP,
 915 |             ref_text="",
 916 |             gen_text=text,
 917 |             speed=speed,
 918 |             show_info=print,
 919 |         )
 920 |         sf.write(wav_tmp, wav, sr)
 921 | 
 922 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 923 |             logger.error("[TTS/F5] Zero output from inference")
 924 |             return False
 925 | 
 926 |         # Convert WAV to M4A (48kHz AAC 192k)
 927 |         r = subprocess.run([
 928 |             "ffmpeg", "-y", "-i", wav_tmp,
 929 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 930 |         ], capture_output=True, text=True, timeout=60)
 931 | 
 932 |         try:
 933 |             if os.path.exists(wav_tmp):
 934 |                 os.remove(wav_tmp)
 935 |         except Exception:
 936 |             pass
 937 | 
 938 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 939 |         if ok:
 940 |             logger.info(f"[TTS/F5] OK: {ffprobe_duration(output_path):.2f}s (PBX fine-tuned)")
 941 |         return ok
 942 |     except Exception as e:
 943 |         logger.error(f"[TTS/F5] Exception: {e}")
 944 |         return False
 945 | 
 946 | 
 947 | def tts_local(text: str, output_path: str, host: int = 1,
 948 |               segment_type: str = "") -> bool:
 949 |     """Primary TTS dispatcher — local GPU inference with per-line ElevenLabs fallback.
 950 | 
 951 |     Host 1 → Kokoro af_heart → ElevenLabs Eryn fallback
 952 |     Host 2 → Chatterbox PBX → Kokoro am_adam → ElevenLabs PBX fallback
 953 |     """
 954 |     # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
 955 |     text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
 956 |     text = expand_numbers_for_tts(text)
 957 |     text = apply_pronunciation_map(text)
 958 |     # Prosody planner: add natural delivery markers before TTS
 959 |     text = prosody_plan(text, host=host)
 960 |     try:
 961 |         _oracle_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oracle")
 962 |         if _oracle_path not in sys.path:
 963 |             sys.path.insert(0, _oracle_path)
 964 |         from oracle_dialogue_engine import normalize_pronunciation
 965 |         text = normalize_pronunciation(text)
 966 |     except Exception as _e:
 967 |         logger.warning(f"[TTS/Local] normalize_pronunciation unavailable: {_e}")
 968 | 
 969 |     cache_key = _tts_cache_key(text, f"local_h{host}", segment_type)
 970 |     if _tts_cache_get(cache_key, output_path):
 971 |         print(f"  [tts/local] Cache HIT (host{host}): {text[:50]}")
 972 |         return True
 973 | 
 974 |     start_t = time.time()
 975 |     ok = False
 976 | 
 977 |     if host == 1:
 978 |         ok = tts_kokoro(text, output_path, voice=KOKORO_HOST1_VOICE, speed=KOKORO_SPEED_H1)
 979 |         if not ok:
 980 |             logger.warning("[TTS/Local] Kokoro host1 FAILED → ElevenLabs Eryn fallback")
 981 |             ok = tts_elevenlabs(text, output_path, host=1, segment_type=segment_type)
 982 |     else:
 983 |         # Kokoro am_onyx primary; F5-TTS PBX fallback when checkpoint confirmed ready
 984 |         ok = tts_kokoro(text, output_path, voice=KOKORO_HOST2_VOICE, speed=KOKORO_SPEED_H2)
 985 |         if not ok:
 986 |             logger.warning("[TTS/Local] Kokoro am_onyx FAILED → F5-TTS fallback")
 987 |             ok = tts_f5_finetuned(text, output_path)
 988 |         if not ok:
 989 |             logger.warning("[TTS/Local] Kokoro host2 FAILED → ElevenLabs PBX fallback")
 990 |             ok = tts_elevenlabs(text, output_path, host=2, segment_type=segment_type)
 991 | 
 992 |     if ok and os.path.exists(output_path):
 993 |         _trim_leading_silence(output_path)
 994 |         _trim_trailing_silence(output_path)
 995 |         validate_tts_output(output_path)
 996 |         _tts_cache_put(cache_key, output_path)
 997 |         elapsed = time.time() - start_t
 998 |         dur = ffprobe_duration(output_path)
 999 |         print(f"  [tts/local] host{host} OK: {dur:.1f}s audio in {elapsed:.1f}s wall ← {text[:50]}")
1000 | 
1001 |     return ok
1002 | 
1003 | 
1004 | def tts_preflight_local() -> bool:
1005 |     """Preflight for TTS_PROVIDER=local: verify Kokoro works, report F5 status."""
1006 |     test_text = "Bitcoin signal confirmed today."
1007 |     test_out = "/tmp/tts_preflight_local.m4a"
1008 |     try:
1009 |         ok = tts_kokoro(test_text, test_out, voice=KOKORO_HOST1_VOICE, speed=1.0)
1010 |         if not ok or not os.path.exists(test_out):
1011 |             raise RuntimeError("[TTS/Local] Kokoro preflight failed to generate audio")
1012 |         dur = ffprobe_duration(test_out)
1013 |         if dur < 0.5:
1014 |             raise RuntimeError(f"[TTS/Local] Kokoro output too short: {dur:.2f}s")
1015 |         logger.info(f"[TTS/Local] Kokoro preflight PASS: {dur:.2f}s")
1016 |         try:
1017 |             os.remove(test_out)
1018 |         except Exception:
1019 |             pass
1020 |         if os.path.exists(PBX_CHECKPOINT) and os.path.exists(PBX_REFERENCE_CLIP):
1021 |             logger.info("[TTS/Local] F5 ready: checkpoint + reference clip")
1022 |         elif os.path.exists(PBX_CHECKPOINT):
1023 |             logger.warning(f"[TTS/Local] F5 checkpoint found but reference clip missing: {PBX_REFERENCE_CLIP}")
1024 |         else:
1025 |             logger.warning("[TTS/Local] F5 checkpoint missing — host2 using Kokoro am_adam")
1026 |         return True
1027 |     except Exception as e:
1028 |         raise RuntimeError(f"[TTS/Local] Preflight FAILED: {e}")
1029 | 
1030 | 
1031 | def validate_tts_output(path: str, min_size: int = 10240) -> None:
1032 |     """Validate TTS output file is real audio, not empty/corrupt.
1033 | 
1034 |     Raises RuntimeError if:
1035 |       - File doesn't exist
1036 |       - File < min_size bytes (10KB default)
1037 |       - ffprobe duration < 0.5s
1038 |     """
1039 |     if not os.path.exists(path):
1040 |         raise RuntimeError(f"TTS output missing: {path}")
1041 |     size = os.path.getsize(path)
1042 |     if size < min_size:
1043 |         raise RuntimeError(
1044 |             f"TTS output too small ({size} bytes < {min_size}): {path} — "
1045 |             f"ElevenLabs likely returned empty audio"
1046 |         )
1047 |     dur = ffprobe_duration(path)
1048 |     if dur < 0.5:
1049 |         raise RuntimeError(
1050 |             f"TTS output too short ({dur:.2f}s < 0.5s): {path} — "
1051 |             f"audio is effectively silent/corrupt"
1052 |         )
1053 | 
1054 | 
1055 | def tts_preflight_test() -> bool:
1056 |     """Preflight: call ElevenLabs with a 5-word test phrase, confirm >1000 bytes returned.
1057 |     Raises RuntimeError on failure so the pipeline aborts before wasting render time."""
1058 |     if not HAS_REQUESTS:
1059 |         raise RuntimeError("TTS preflight: 'requests' library not installed")
1060 |     key = _get_cached_key("ELEVENLABS_API_KEY")
1061 |     if not key:
1062 |         raise RuntimeError("TTS preflight: ELEVENLABS_API_KEY not available")
1063 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
1064 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
1065 |     body = {
1066 |         "text": "Bitcoin signal confirmed today.",
1067 |         "model_id": _PBX_VOICE["model_id"],
1068 |         "voice_settings": dict(_PBX_VOICE["voice_settings"]),
1069 |     }
1070 |     try:
1071 |         r = requests.post(url, json=body, headers=headers, timeout=20)
1072 |         if r.status_code != 200:
1073 |             raise RuntimeError(f"TTS preflight: ElevenLabs returned HTTP {r.status_code}: {r.text[:200]}")
1074 |         if len(r.content) < 1000:
1075 |             raise RuntimeError(f"TTS preflight: ElevenLabs returned only {len(r.content)} bytes (need >1000)")
1076 |         logger.info(f"[TTS] Preflight PASS: PBX voice returned {len(r.content)} bytes")
1077 |         return True
1078 |     except requests.RequestException as e:
1079 |         raise RuntimeError(f"TTS preflight: ElevenLabs unreachable: {e}")
1080 | 
1081 | 
1082 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
1083 |                    segment_type: str = "") -> bool:
1084 |     """Generate TTS for a single line using the specified host voice.
1085 | 
1086 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
1087 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
1088 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
1089 |     """
1090 |     if not HAS_REQUESTS:
1091 |         # No requests lib — try pyttsx3 or silence
1092 |         return _tts_generate_silence_fallback(text, output_path)
1093 | 
1094 |     key = _get_cached_key("ELEVENLABS_API_KEY")
1095 |     if not key:
1096 |         return _tts_generate_silence_fallback(text, output_path)
1097 | 
1098 |     # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
1099 |     # These tags are for script structure — narrator should never read them aloud
1100 |     text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
1101 |     # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
1102 |     text = expand_numbers_for_tts(text)
1103 |     # R25 FIX 7: Apply pronunciation map (Pysh→PISH, etc.) — was defined but never called
1104 |     text = apply_pronunciation_map(text)
1105 | 
1106 |     voice = VOICES.get(host, VOICES[2])  # All hosts → PBX
1107 |     # Check TTS cache first — avoid API call if same text+voice was generated before
1108 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
1109 |     if _tts_cache_get(cache_key, output_path):
1110 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
1111 |         return True
1112 | 
1113 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
1114 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
1115 | 
1116 |     # Apply voice mode overrides based on segment type (both hosts)
1117 |     voice_settings = dict(voice["voice_settings"])
1118 |     if segment_type in VOICE_MODES:
1119 |         mode = VOICE_MODES[segment_type]
1120 |         for k, v in mode.items():
1121 |             if k != "speed":
1122 |                 voice_settings[k] = v
1123 | 
1124 |     chunks = _chunk_text(text)
1125 |     chunk_files = []
1126 | 
1127 |     for ci, chunk in enumerate(chunks):
1128 |         body = {
1129 |             "text": chunk,
1130 |             "model_id": voice["model_id"],
1131 |             "voice_settings": voice_settings,
1132 |         }
1133 |         # Add speed parameter from voice config (host-specific)
1134 |         speed = voice.get("speed", 1.0)
1135 |         if speed != 1.0:
1136 |             body["speed"] = speed
1137 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
1138 |         success = False
1139 | 
1140 |         # FIX iter1: Increase retries from 3 to 5 with longer backoff to survive
1141 |         # transient ElevenLabs outages that were causing grade failures
1142 |         max_retries = 5
1143 |         for attempt in range(max_retries):
1144 |             try:
1145 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
1146 |                 if r.status_code == 200:
1147 |                     with open(mp3_tmp, "wb") as f:
1148 |                         f.write(r.content)
1149 |                     # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
1150 |                     if os.path.getsize(mp3_tmp) < 1000:
1151 |                         print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
1152 |                         if attempt < max_retries - 1:
1153 |                             time.sleep(2 ** attempt)
1154 |                             continue
1155 |                     success = True
1156 |                     break
1157 |                 elif r.status_code == 429:
1158 |                     wait = min(2 ** (attempt + 1), 30)  # cap at 30s
1159 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
1160 |                     time.sleep(wait)
1161 |                 else:
1162 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
1163 |                     if attempt < max_retries - 1:
1164 |                         time.sleep(2 ** attempt)
1165 |             except Exception as e:
1166 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
1167 |                 if attempt < max_retries - 1:
1168 |                     time.sleep(2 ** attempt)
1169 | 
1170 |         if not success:
1171 |             for f in chunk_files:
1172 |                 try:
1173 |                     os.remove(f)
1174 |                 except Exception:
1175 |                     pass
1176 |             logger.error(f"[tts] ElevenLabs failed after {max_retries} retries for chunk {ci} — returning False")
1177 |             return False
1178 |         chunk_files.append(mp3_tmp)
1179 | 
1180 |     # Single chunk
1181 |     if len(chunk_files) == 1:
1182 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
1183 |         try:
1184 |             os.remove(chunk_files[0])
1185 |         except Exception:
1186 |             pass
1187 |         if ok and os.path.exists(output_path):
1188 |             _trim_leading_silence(output_path)
1189 |             _trim_trailing_silence(output_path)
1190 |             validate_tts_output(output_path)
1191 |             _tts_cache_put(cache_key, output_path)
1192 |         return ok
1193 | 
1194 |     # Multi-chunk concat
1195 |     concat_list = output_path + ".concat.txt"
1196 |     mp3_combined = output_path + ".combined.mp3"
1197 |     with open(concat_list, "w") as f:
1198 |         for p in chunk_files:
1199 |             f.write(f"file '{os.path.abspath(p)}'\n")
1200 |     subprocess.run(
1201 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
1202 |          "-c", "copy", mp3_combined],
1203 |         capture_output=True, text=True,
1204 |     )
1205 |     ok = _mp3_to_m4a(mp3_combined, output_path)
1206 |     for f in chunk_files + [concat_list, mp3_combined]:
1207 |         try:
1208 |             if os.path.exists(f):
1209 |                 os.remove(f)
1210 |         except Exception:
1211 |             pass
1212 |     if ok and os.path.exists(output_path):
1213 |         _trim_leading_silence(output_path)
1214 |         _trim_trailing_silence(output_path)
1215 |         validate_tts_output(output_path)
1216 |         _tts_cache_put(cache_key, output_path)
1217 |     return ok
1218 | 
1219 | 
1220 | def _synthesize_line(i: int, entry: dict, output_dir: str, provider: str) -> dict:
1221 |     """Synthesize a single dialogue line. Used by ThreadPoolExecutor for parallel TTS.
1222 | 
1223 |     Returns metadata dict with path, duration, host, tts_ok flag.
1224 |     On primary TTS failure, falls back to Kokoro — never produces silence (LAW: TTS FALLBACK BANNED).
1225 |     """
1226 |     host = entry.get("host")
1227 |     text = entry.get("text", "")
1228 | 
1229 |     if provider == "local":
1230 |         host_num = host if host in (1, 2) else 2
1231 |     else:
1232 |         host_num = 2  # ElevenLabs: single-host Option A preserved
1233 | 
1234 |     voice = VOICES[host_num]
1235 |     segment_type = entry.get("type", "")
1236 |     line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
1237 | 
1238 |     mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
1239 |     print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
1240 | 
1241 |     _tts_ok = False
1242 |     dur = 0.0
1243 | 
1244 |     if provider == "local":
1245 |         _tts_ok = tts_local(text, line_path, host_num, segment_type=segment_type)
1246 |     else:
1247 |         _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
1248 | 
1249 |     # Validate output
1250 |     if _tts_ok:
1251 |         if not os.path.exists(line_path) or os.path.getsize(line_path) < 1000:
1252 |             logger.warning(f"[tts] Line {i} zero/tiny audio — trying Kokoro fallback")
1253 |             _tts_ok = False
1254 |         else:
1255 |             dur = ffprobe_duration(line_path)
1256 |             if dur < 0.5 and len(text) > 10:
1257 |                 logger.warning(f"[tts] Line {i} too short ({dur:.2f}s) — trying Kokoro fallback")
1258 |                 _tts_ok = False
1259 | 
1260 |     # Fallback to Kokoro on any failure — never produce silence (LAW: TTS FALLBACK BANNED)
1261 |     if not _tts_ok:
1262 |         kokoro_voice = KOKORO_HOST1_VOICE if host_num == 1 else KOKORO_HOST2_VOICE
1263 |         kokoro_speed = KOKORO_SPEED_H1 if host_num == 1 else KOKORO_SPEED_H2
1264 |         logger.warning(f"[tts] Line {i} primary TTS failed — Kokoro fallback (voice={kokoro_voice})")
1265 |         _tts_ok = tts_kokoro(text, line_path, voice=kokoro_voice, speed=kokoro_speed)
1266 |         if _tts_ok and os.path.exists(line_path) and os.path.getsize(line_path) >= 1000:
1267 |             dur = ffprobe_duration(line_path)
1268 |             if dur < 0.5 and len(text) > 10:
1269 |                 _tts_ok = False
1270 | 
1271 |     if not _tts_ok:
1272 |         raise RuntimeError(
1273 |             f"TTS FATAL: All providers failed for line {i} (host {host_num}). "
1274 |             f"Text: \"{text[:80]}...\". Refusing to render silence."
1275 |         )
1276 | 
1277 |     return {
1278 |         "index": i,
1279 |         "path": line_path,
1280 |         "host": host_num,
1281 |         "duration": dur,
1282 |         "text": text,
1283 |         "type": segment_type,
1284 |         "tts_ok": True,
1285 |         "clip_rank": entry.get("clip_rank", 0),
1286 |     }
1287 | 
1288 | 
1289 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
1290 |     """Generate audio for the entire dual-host dialogue.
1291 | 
1292 |     Pre-generates ALL TTS lines in parallel via ThreadPoolExecutor to eliminate
1293 |     sequential API latency stacking. Then assembles timeline and concatenates.
1294 | 
1295 |     Args:
1296 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
1297 |         output_dir: Directory for audio files
1298 | 
1299 |     Returns:
1300 |         {
1301 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
1302 |             "full": str,  # path to concatenated full audio
1303 |             "total_duration": float,
1304 |         }
1305 |     """
1306 |     os.makedirs(output_dir, exist_ok=True)
1307 | 
1308 |     _active_provider = _get_tts_provider()
1309 |     if _active_provider == "local":
1310 |         tts_preflight_local()
1311 |     else:
1312 |         key = _get_cached_key("ELEVENLABS_API_KEY")
1313 |         if not key:
1314 |             raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
1315 | 
1316 |     silence_path = os.path.join(output_dir, "silence.m4a")
1317 |     if not _generate_silence(silence_path, SILENCE_GAP):
1318 |         raise RuntimeError("Failed to generate inter-line silence gap audio")
1319 | 
1320 |     # ── Phase 1: Parallel TTS pre-generation ──
1321 |     # Generate ALL spoken lines concurrently — prevents API latency stacking
1322 |     tts_jobs = []  # (dialogue_index, entry) for lines needing TTS
1323 |     clip_entries = {}  # dialogue_index → clip metadata
1324 | 
1325 |     for i, entry in enumerate(dialogue):
1326 |         if entry.get("host") == "CLIP":
1327 |             clip_entries[i] = entry
1328 |         else:
1329 |             tts_jobs.append((i, entry))
1330 | 
1331 |     # Parallel TTS: 4 workers for ElevenLabs (rate-safe), 6 for local
1332 |     max_workers = 4 if _active_provider == "elevenlabs" else 6
1333 |     tts_results = {}  # index → result dict
1334 | 
1335 |     if tts_jobs:
1336 |         print(f"  [tts] Pre-generating {len(tts_jobs)} lines in parallel (workers={max_workers})...")
1337 |         with ThreadPoolExecutor(max_workers=max_workers) as executor:
1338 |             futures = {
1339 |                 executor.submit(_synthesize_line, idx, entry, output_dir, _active_provider): idx
1340 |                 for idx, entry in tts_jobs
1341 |             }
1342 |             for future in as_completed(futures):
1343 |                 idx = futures[future]
1344 |                 try:
1345 |                     result = future.result()
1346 |                     tts_results[result["index"]] = result
1347 |                 except Exception as e:
1348 |                     logger.error(f"[tts] Parallel TTS line {idx} failed: {e}")
1349 |                     raise
1350 | 
1351 |     # ── Phase 2: Assemble timeline in original order ──
1352 |     lines = []
1353 |     parts_for_concat = []
1354 |     current_time = 0.0
1355 | 
1356 |     for i, entry in enumerate(dialogue):
1357 |         host = entry.get("host")
1358 |         text = entry.get("text", "")
1359 | 
1360 |         if host == "CLIP":
1361 |             clip_duration = float(entry.get("duration", 30.0))
1362 |             lines.append({
1363 |                 "path": None,
1364 |                 "host": "CLIP",
1365 |                 "duration": clip_duration,
1366 |                 "start": current_time,
1367 |                 "source": entry.get("source", ""),
1368 |                 "query": entry.get("query", ""),
1369 |                 "text": text,
1370 |             })
1371 |             current_time += clip_duration
1372 |             continue
1373 | 
1374 |         result = tts_results[i]
1375 |         dur = result["duration"]
1376 | 
1377 |         lines.append({
1378 |             "path": result["path"],
1379 |             "host": result["host"],
1380 |             "duration": dur,
1381 |             "start": current_time,
1382 |             "text": text,
1383 |             "type": result["type"],
1384 |             "tts_ok": result["tts_ok"],
1385 |             "clip_rank": result.get("clip_rank", 0),
1386 |         })
1387 |         parts_for_concat.append(result["path"])
1388 |         current_time += dur
1389 | 
1390 |         # Add silence gap between lines (not after last line, not before CLIP)
1391 |         next_entry = dialogue[i + 1] if i < len(dialogue) - 1 else None
1392 |         if next_entry is not None and next_entry.get("host") != "CLIP":
1393 |             parts_for_concat.append(silence_path)
1394 |             current_time += SILENCE_GAP
1395 | 
1396 |     # Concatenate all lines into full audio
1397 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
1398 |     if parts_for_concat:
1399 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
1400 |         with open(concat_file, "w") as f:
1401 |             for p in parts_for_concat:
1402 |                 f.write(f"file '{os.path.abspath(p)}'\n")
1403 |         concat_result = subprocess.run(
1404 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
1405 |              "-c", "copy", full_path],
1406 |             capture_output=True, text=True,
1407 |         )
1408 |         if concat_result.returncode != 0:
1409 |             logger.error(f"[tts] FFmpeg concat failed: {concat_result.stderr[:500]}")
1410 |         if os.path.exists(concat_file):
1411 |             os.remove(concat_file)
1412 | 
1413 |     # Guard: full_dialogue.m4a must not be zero-byte or tiny
1414 |     if os.path.exists(full_path):
1415 |         full_size = os.path.getsize(full_path)
1416 |         if full_size < 10240:
1417 |             raise RuntimeError(
1418 |                 f"full_dialogue.m4a is {full_size} bytes (<10KB) — "
1419 |                 f"FFmpeg concat produced empty/corrupt audio. Aborting before render."
1420 |             )
1421 | 
1422 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
1423 |     successful = sum(1 for l in lines if l.get("tts_ok", False))
1424 | 
1425 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
1426 | 
1427 |     # ── Per-host TTS validation: catch silent hosts BEFORE render starts ──
1428 |     host_stats = {}  # {host_num: {"total": N, "ok": N}}
1429 |     for l in lines:
1430 |         h = l.get("host")
1431 |         if h == "CLIP":
1432 |             continue
1433 |         if h not in host_stats:
1434 |             host_stats[h] = {"total": 0, "ok": 0}
1435 |         host_stats[h]["total"] += 1
1436 |         if l.get("tts_ok", False):
1437 |             host_stats[h]["ok"] += 1
1438 | 
1439 |     for h, stats in host_stats.items():
1440 |         voice_name = VOICES.get(h, {}).get("name", f"Host{h}")
1441 |         if stats["ok"] == 0 and stats["total"] > 0:
1442 |             raise RuntimeError(
1443 |                 f"TTS FATAL: {voice_name} (host {h}) has 0/{stats['total']} successful lines. "
1444 |                 f"All audio is missing/silent. Aborting before render."
1445 |             )
1446 |         if stats["total"] > 0 and stats["ok"] / stats["total"] < 0.5:
1447 |             raise RuntimeError(
1448 |                 f"TTS FATAL: {voice_name} (host {h}) has only {stats['ok']}/{stats['total']} "
1449 |                 f"successful lines (<50%). Too many failures to produce a quality render."
1450 |             )
1451 | 
1452 |     return {
1453 |         "lines": lines,
1454 |         "full": full_path if os.path.exists(full_path) else None,
1455 |         "total_duration": total_dur,
1456 |     }
1457 | 
1458 | 
1459 | # Legacy compatibility — V3 pipeline used generate_all_audio
1460 | def generate_all_audio(script: dict, output_dir: str) -> dict:
1461 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
1462 |     if "dialogue" in script:
1463 |         return generate_dialogue_audio(script["dialogue"], output_dir)
1464 |     # V3 fallback
1465 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
1466 | 
1467 | 
1468 | if __name__ == "__main__":
1469 |     from script_writer import generate_script
1470 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
1471 |     script = generate_script(style=style)
1472 |     base = os.path.dirname(os.path.abspath(__file__))
1473 |     audio_dir = os.path.join(base, "output", "audio_test")
1474 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
1475 |     print(json.dumps(
1476 |         {k: v for k, v in result.items() if k != "lines"},
1477 |         indent=2,
1478 |     ))
1479 | 
```

### File: services/local_watchdog.py (1231 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Protocol Pulse — Local LLM Watchdog (4-Layer Autonomous System)
   4 | GPU 2: Qwen3-Coder-30B via Ollama on port 11435
   5 | 
   6 | Modes (each runs independently via cron):
   7 |   --mode reactive   : every 60s  — crash detection + auto-patch
   8 |   --mode health     : every 15m  — system health scan
   9 |   --mode pattern    : every 6h   — trend analysis over 7 days
  10 |   --mode audit      : Monday 08:00 UTC — weekly deep audit
  11 |   --mode briefing   : daily 13:00 UTC (09:00 ET) — Telegram daily summary
  12 | 
  13 | Gospel: docs/gospels/WATCHDOG_LLM_GOSPEL.md
  14 | """
  15 | 
  16 | import argparse
  17 | import glob
  18 | import json
  19 | import logging
  20 | import os
  21 | import re
  22 | import shutil
  23 | import subprocess
  24 | import sys
  25 | import time
  26 | from datetime import datetime, timezone, timedelta
  27 | from pathlib import Path
  28 | 
  29 | # ---------------------------------------------------------------------------
  30 | # Paths
  31 | # ---------------------------------------------------------------------------
  32 | 
  33 | BASE = Path(__file__).resolve().parent.parent
  34 | LOGS_DIR = BASE / "logs"
  35 | LOGS_DIR.mkdir(exist_ok=True)
  36 | 
  37 | LOG_FILE = LOGS_DIR / "watchdog_llm.log"
  38 | PATCH_LOG = LOGS_DIR / "watchdog_patches.jsonl"
  39 | OVERNIGHT_LOG = BASE / "video_pipeline_v3" / "logs" / "overnight_loop.log"
  40 | REGRESSION_SCRIPT = BASE / "regression_test.sh"
  41 | 
  42 | # ---------------------------------------------------------------------------
  43 | # Config
  44 | # ---------------------------------------------------------------------------
  45 | 
  46 | OLLAMA_URL = "http://127.0.0.1:11435"
  47 | MODEL = os.environ.get("WATCHDOG_MODEL", "qwen3-coder:30b")
  48 | 
  49 | # Files we NEVER patch — gospel law
  50 | NEVER_PATCH = {"assembler.py", "tts_engine.py", "gemini_grade.py", "routes.py"}
  51 | 
  52 | # Cooldown: 600s per file, max 3 patches/hour
  53 | COOLDOWN_SECONDS = 600
  54 | MAX_PATCHES_PER_HOUR = 3
  55 | 
  56 | # ---------------------------------------------------------------------------
  57 | # Logging
  58 | # ---------------------------------------------------------------------------
  59 | 
  60 | logger = logging.getLogger("watchdog")
  61 | logger.setLevel(logging.INFO)
  62 | 
  63 | _fh = logging.FileHandler(str(LOG_FILE))
  64 | _fh.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(levelname)s: %(message)s"))
  65 | logger.addHandler(_fh)
  66 | 
  67 | _sh = logging.StreamHandler()
  68 | _sh.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(levelname)s: %(message)s"))
  69 | logger.addHandler(_sh)
  70 | 
  71 | # ---------------------------------------------------------------------------
  72 | # Telegram
  73 | # ---------------------------------------------------------------------------
  74 | 
  75 | def _load_env():
  76 |     """Load .env file into os.environ."""
  77 |     env_path = BASE / ".env"
  78 |     if env_path.exists():
  79 |         for line in env_path.read_text().splitlines():
  80 |             line = line.strip()
  81 |             if line and not line.startswith("#") and "=" in line:
  82 |                 key, val = line.split("=", 1)
  83 |                 os.environ.setdefault(key.strip(), val.strip().strip("'\""))
  84 | 
  85 | 
  86 | def send_telegram(msg):
  87 |     """Send a Telegram message. Returns True on success."""
  88 |     _load_env()
  89 |     token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
  90 |     chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
  91 |     if not token or not chat_id:
  92 |         logger.warning("Telegram not configured — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing")
  93 |         return False
  94 |     try:
  95 |         import requests
  96 |         resp = requests.post(
  97 |             f"https://api.telegram.org/bot{token}/sendMessage",
  98 |             json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
  99 |             timeout=10,
 100 |         )
 101 |         resp.raise_for_status()
 102 |         return True
 103 |     except Exception as e:
 104 |         logger.error("Telegram send failed: %s", e)
 105 |         return False
 106 | 
 107 | # ---------------------------------------------------------------------------
 108 | # Ollama Interface
 109 | # ---------------------------------------------------------------------------
 110 | 
 111 | def ollama_chat(system_prompt, user_prompt, temperature=0.3):
 112 |     """Fresh Ollama conversation — zero prior context (gospel: Fresh Perspective)."""
 113 |     import requests
 114 |     try:
 115 |         resp = requests.post(
 116 |             f"{OLLAMA_URL}/api/chat",
 117 |             json={
 118 |                 "model": MODEL,
 119 |                 "messages": [
 120 |                     {"role": "system", "content": system_prompt},
 121 |                     {"role": "user", "content": user_prompt},
 122 |                 ],
 123 |                 "stream": False,
 124 |                 "options": {"temperature": temperature},
 125 |             },
 126 |             timeout=120,
 127 |         )
 128 |         resp.raise_for_status()
 129 |         return resp.json().get("message", {}).get("content", "").strip()
 130 |     except Exception as e:
 131 |         logger.error("Ollama call failed: %s", e)
 132 |         return None
 133 | 
 134 | 
 135 | def ollama_healthy():
 136 |     """Check if Ollama is responding."""
 137 |     import requests
 138 |     try:
 139 |         resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
 140 |         return resp.status_code == 200
 141 |     except Exception:
 142 |         return False
 143 | 
 144 | # ---------------------------------------------------------------------------
 145 | # Utility
 146 | # ---------------------------------------------------------------------------
 147 | 
 148 | def tail_file(path, n=50):
 149 |     """Read last n lines of a file."""
 150 |     p = Path(path)
 151 |     if not p.exists():
 152 |         return ""
 153 |     try:
 154 |         result = subprocess.run(
 155 |             ["tail", "-n", str(n), str(p)],
 156 |             capture_output=True, text=True, timeout=10,
 157 |         )
 158 |         return result.stdout
 159 |     except Exception:
 160 |         return ""
 161 | 
 162 | 
 163 | def read_file_content(path):
 164 |     """Read file content, capped at 200 lines."""
 165 |     try:
 166 |         lines = Path(path).read_text().splitlines()[:200]
 167 |         return "\n".join(lines)
 168 |     except Exception:
 169 |         return ""
 170 | 
 171 | 
 172 | def gpu_vram():
 173 |     """Get GPU VRAM usage as list of dicts."""
 174 |     try:
 175 |         result = subprocess.run(
 176 |             ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
 177 |              "--format=csv,nounits,noheader"],
 178 |             capture_output=True, text=True, timeout=10,
 179 |         )
 180 |         gpus = []
 181 |         for line in result.stdout.strip().splitlines():
 182 |             parts = [p.strip() for p in line.split(",")]
 183 |             if len(parts) >= 4:
 184 |                 gpus.append({
 185 |                     "index": int(parts[0]),
 186 |                     "vram_used_mb": int(parts[1]),
 187 |                     "vram_total_mb": int(parts[2]),
 188 |                     "utilization_pct": int(parts[3]),
 189 |                 })
 190 |         return gpus
 191 |     except Exception:
 192 |         return []
 193 | 
 194 | 
 195 | def disk_free_gb():
 196 |     """Get free disk space in GB for the base directory."""
 197 |     try:
 198 |         stat = shutil.disk_usage(str(BASE))
 199 |         return round(stat.free / (1024 ** 3), 1)
 200 |     except Exception:
 201 |         return -1
 202 | 
 203 | 
 204 | def process_alive(name):
 205 |     """Check if a process matching name is running."""
 206 |     try:
 207 |         result = subprocess.run(["pgrep", "-f", name], capture_output=True, timeout=5)
 208 |         return result.returncode == 0
 209 |     except Exception:
 210 |         return False
 211 | 
 212 | 
 213 | def flask_alive():
 214 |     """Check if Flask is responding on localhost:5000."""
 215 |     import requests
 216 |     try:
 217 |         resp = requests.get("http://localhost:5000/", timeout=5)
 218 |         return resp.status_code < 500
 219 |     except Exception:
 220 |         return False
 221 | 
 222 | 
 223 | # ---------------------------------------------------------------------------
 224 | # Safety Gates
 225 | # ---------------------------------------------------------------------------
 226 | 
 227 | def check_cooldown(filepath):
 228 |     """Return True if file is on cooldown (patched within last 600s)."""
 229 |     fname = Path(filepath).name
 230 |     stamp_file = Path(f"/tmp/watchdog_last_patch_{fname}.txt")
 231 |     if stamp_file.exists():
 232 |         try:
 233 |             last = float(stamp_file.read_text().strip())
 234 |             if time.time() - last < COOLDOWN_SECONDS:
 235 |                 return True
 236 |         except (ValueError, IOError):
 237 |             pass
 238 |     return False
 239 | 
 240 | 
 241 | def record_patch(filepath):
 242 |     """Record patch timestamp for cooldown tracking."""
 243 |     fname = Path(filepath).name
 244 |     stamp_file = Path(f"/tmp/watchdog_last_patch_{fname}.txt")
 245 |     stamp_file.write_text(str(time.time()))
 246 | 
 247 | 
 248 | def patches_this_hour():
 249 |     """Count patches applied in the current hour."""
 250 |     hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
 251 |     count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
 252 |     if count_file.exists():
 253 |         try:
 254 |             return int(count_file.read_text().strip())
 255 |         except (ValueError, IOError):
 256 |             pass
 257 |     return 0
 258 | 
 259 | 
 260 | def increment_patch_count():
 261 |     """Increment the hourly patch counter."""
 262 |     hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
 263 |     count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
 264 |     current = patches_this_hour()
 265 |     count_file.write_text(str(current + 1))
 266 | 
 267 | 
 268 | def is_patchable(filepath):
 269 |     """Check all safety gates for patching a file."""
 270 |     fname = Path(filepath).name
 271 | 
 272 |     if fname in NEVER_PATCH:
 273 |         logger.info("GATE: %s is in NEVER_PATCH list — skipping", fname)
 274 |         return False
 275 | 
 276 |     if process_alive("daily_producer"):
 277 |         logger.info("GATE: daily_producer is running — skipping patch")
 278 |         return False
 279 | 
 280 |     if check_cooldown(filepath):
 281 |         logger.info("GATE: %s on cooldown — skipping", fname)
 282 |         return False
 283 | 
 284 |     if patches_this_hour() >= MAX_PATCHES_PER_HOUR:
 285 |         logger.info("GATE: max %d patches/hour reached — skipping", MAX_PATCHES_PER_HOUR)
 286 |         return False
 287 | 
 288 |     return True
 289 | 
 290 | 
 291 | # ---------------------------------------------------------------------------
 292 | # Crash Classification
 293 | # ---------------------------------------------------------------------------
 294 | 
 295 | def classify_crash(log_tail):
 296 |     """Classify crash from log lines. Returns (class, pattern_matched) or (None, None)."""
 297 |     lines = log_tail.strip()
 298 |     if not lines:
 299 |         return None, None
 300 | 
 301 |     # CLASS C — check protected files first (takes priority)
 302 |     for protected in NEVER_PATCH:
 303 |         if (f'File "' in lines and protected in lines and "Traceback" in lines):
 304 |             return "C", f"crash_in_{protected}"
 305 | 
 306 |     # Check for multi-file crashes (>1 unique repo file in traceback)
 307 |     file_matches = re.findall(r'File "([^"]*protocol_pulse[^"]*)"', lines)
 308 |     unique_files = set(Path(f).name for f in file_matches)
 309 |     # Remove __init__.py and test files from uniqueness check
 310 |     meaningful = {f for f in unique_files if f != "__init__.py" and not f.startswith("test_")}
 311 |     if len(meaningful) > 1:
 312 |         return "C", f"multi_file_crash({','.join(sorted(meaningful)[:3])})"
 313 | 
 314 |     # CLASS A patterns (safe auto-patch)
 315 |     if "KeyError" in lines:
 316 |         return "A", "KeyError"
 317 |     if "ImportError" in lines or "ModuleNotFoundError" in lines:
 318 |         return "A", "ImportError"
 319 |     if "FileNotFoundError" in lines:
 320 |         return "A", "FileNotFoundError"
 321 |     if "SyntaxError" in lines:
 322 |         return "A", "SyntaxError"
 323 | 
 324 |     # CLASS B patterns (patch + test)
 325 |     if "Traceback" in lines and "daily_producer" in lines:
 326 |         return "B", "Traceback+daily_producer"
 327 |     if "exit: -15" in lines and "FATAL" in lines:
 328 |         return "B", "exit:-15+FATAL"
 329 |     if "GRADE: F" in lines:
 330 |         return "B", "GRADE:F"
 331 | 
 332 |     # Check for 3x consecutive "Render failed"
 333 |     render_fails = re.findall(r"Render failed", lines)
 334 |     if len(render_fails) >= 3:
 335 |         return "B", "Render_failed_3x"
 336 | 
 337 |     return None, None
 338 | 
 339 | 
 340 | def extract_affected_file(log_tail):
 341 |     """Try to extract the crashing file from a traceback."""
 342 |     matches = re.findall(r'File "([^"]+)"', log_tail)
 343 |     # Filter to our repo files, exclude NEVER_PATCH
 344 |     repo_files = [
 345 |         m for m in matches
 346 |         if str(BASE) in m and Path(m).name not in NEVER_PATCH
 347 |     ]
 348 |     if repo_files:
 349 |         return repo_files[-1]  # Last file in traceback is usually the culprit
 350 |     return None
 351 | 
 352 | 
 353 | # ---------------------------------------------------------------------------
 354 | # Patch Engine
 355 | # ---------------------------------------------------------------------------
 356 | 
 357 | def diagnose_and_patch(log_tail, crash_class, pattern):
 358 |     """Use Ollama to diagnose crash, optionally apply patch."""
 359 |     affected_file = extract_affected_file(log_tail)
 360 | 
 361 |     if not affected_file:
 362 |         logger.info("Could not determine affected file from traceback")
 363 |         send_telegram(
 364 |             f"\U0001f534 <b>CRASH DETECTED</b> — CLASS {crash_class}\n"
 365 |             f"\U0001f4cb Pattern: {pattern}\n"
 366 |             f"\u26a0\ufe0f Could not identify affected file\n"
 367 |             f"\U0001f527 Manual intervention needed"
 368 |         )
 369 |         return
 370 | 
 371 |     fname = Path(affected_file).name
 372 | 
 373 |     # Clear .pyc on any crash detection
 374 |     clear_pyc()
 375 | 
 376 |     # CLASS C — escalate to CC fix session
 377 |     if crash_class == "C":
 378 |         logger.info("CLASS C crash in %s — escalating to CC fix session", fname)
 379 |         send_telegram(
 380 |             f"\U0001f534 <b>CLASS C CRASH</b> in <code>{fname}</code>\n"
 381 |             f"\U0001f4cb Pattern: {pattern}\n"
 382 |             f"\u26a0\ufe0f Protected file — escalating to Claude Code"
 383 |         )
 384 |         launch_cc_fix_session(crash_class, pattern, log_tail, affected_file)
 385 |         return
 386 | 
 387 |     # Check safety gates
 388 |     if not is_patchable(affected_file):
 389 |         send_telegram(
 390 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 391 |             f"\U0001f4cb Pattern: {pattern}\n"
 392 |             f"\U0001f6ab Safety gate blocked auto-patch\n"
 393 |             f"\U0001f527 Manual intervention needed"
 394 |         )
 395 |         return
 396 | 
 397 |     # Read affected file content
 398 |     file_content = read_file_content(affected_file)
 399 | 
 400 |     # Ask Ollama for diagnosis
 401 |     system_prompt = (
 402 |         "You are a Python/FFmpeg expert debugging a video production pipeline. "
 403 |         "Analyze the crash log and return ONLY valid JSON:\n"
 404 |         '{"diagnosis": "str", "affected_file": "str", "patch_diff": "str", "confidence": float}\n'
 405 |         "The patch_diff must be a unified diff that can be applied with `patch -p0`.\n"
 406 |         "If you cannot determine a fix with high confidence, set confidence to 0.0."
 407 |     )
 408 |     user_prompt = f"CRASH LOG:\n{log_tail}\n\nFILE CONTENT ({affected_file}):\n{file_content}"
 409 | 
 410 |     logger.info("Requesting Ollama diagnosis for %s...", fname)
 411 |     raw_response = ollama_chat(system_prompt, user_prompt)
 412 | 
 413 |     if not raw_response:
 414 |         send_telegram(
 415 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 416 |             f"\U0001f4cb {pattern}\n"
 417 |             f"\u274c Ollama diagnosis failed — model unresponsive"
 418 |         )
 419 |         return
 420 | 
 421 |     # Parse JSON from response (may be wrapped in markdown code block)
 422 |     json_text = None
 423 |     # Try code block first
 424 |     code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
 425 |     if code_match:
 426 |         json_text = code_match.group(1)
 427 |     else:
 428 |         # Try bare JSON
 429 |         json_match = re.search(r'\{[^{}]*"diagnosis"[^}]*\}', raw_response, re.DOTALL)
 430 |         if json_match:
 431 |             json_text = json_match.group()
 432 | 
 433 |     if not json_text:
 434 |         logger.warning("Could not parse JSON from Ollama response")
 435 |         send_telegram(
 436 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 437 |             f"\U0001f4cb {pattern}\n"
 438 |             f"\u274c Ollama returned unparseable response"
 439 |         )
 440 |         return
 441 | 
 442 |     try:
 443 |         diagnosis = json.loads(json_text)
 444 |     except json.JSONDecodeError:
 445 |         logger.warning("JSON parse failed on Ollama response")
 446 |         send_telegram(
 447 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 448 |             f"\U0001f4cb {pattern}\n"
 449 |             f"\u274c Ollama JSON malformed"
 450 |         )
 451 |         return
 452 | 
 453 |     confidence = float(diagnosis.get("confidence", 0))
 454 |     diag_text = diagnosis.get("diagnosis", "No diagnosis")
 455 |     patch_diff = diagnosis.get("patch_diff", "")
 456 | 
 457 |     logger.info("Diagnosis: %s (confidence: %.2f)", diag_text[:100], confidence)
 458 | 
 459 |     # Gate 1: confidence check
 460 |     if confidence < 0.8:
 461 |         logger.info("Confidence %.2f < 0.8 — escalating to CC", confidence)
 462 |         send_telegram(
 463 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 464 |             f"\U0001f4cb {diag_text[:200]}\n"
 465 |             f"\U0001f3af Confidence: {confidence:.0%} (below 80% threshold)\n"
 466 |             f"\U0001f527 Escalating to Claude Code..."
 467 |         )
 468 |         launch_cc_fix_session(crash_class, pattern, log_tail, affected_file)
 469 |         return
 470 | 
 471 |     if not patch_diff.strip():
 472 |         logger.info("No patch provided despite high confidence")
 473 |         send_telegram(
 474 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 475 |             f"\U0001f4cb {diag_text[:200]}\n"
 476 |             f"\U0001f3af Confidence: {confidence:.0%}\n"
 477 |             f"\u26a0\ufe0f No patch diff provided"
 478 |         )
 479 |         return
 480 | 
 481 |     # Apply patch
 482 |     logger.info("Applying patch to %s...", fname)
 483 |     patch_file = Path("/tmp/watchdog_patch.diff")
 484 |     patch_file.write_text(patch_diff)
 485 | 
 486 |     try:
 487 |         result = subprocess.run(
 488 |             ["patch", "-p0", "--dry-run", "-i", str(patch_file)],
 489 |             capture_output=True, text=True, timeout=10, cwd=str(BASE),
 490 |         )
 491 |         if result.returncode != 0:
 492 |             logger.warning("Patch dry-run failed: %s", result.stderr)
 493 |             send_telegram(
 494 |                 f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 495 |                 f"\U0001f4cb {diag_text[:200]}\n"
 496 |                 f"\u274c Patch dry-run failed\n"
 497 |                 f"\U0001f527 Manual fix needed"
 498 |             )
 499 |             return
 500 | 
 501 |         # Apply for real
 502 |         result = subprocess.run(
 503 |             ["patch", "-p0", "-i", str(patch_file)],
 504 |             capture_output=True, text=True, timeout=10, cwd=str(BASE),
 505 |         )
 506 |         if result.returncode != 0:
 507 |             logger.error("Patch apply failed: %s", result.stderr)
 508 |             send_telegram(
 509 |                 f"\U0001f534 <b>PATCH FAILED</b> for <code>{fname}</code>\n"
 510 |                 f"\u274c {result.stderr[:200]}"
 511 |             )
 512 |             return
 513 |     except Exception as e:
 514 |         logger.error("Patch subprocess error: %s", e)
 515 |         return
 516 | 
 517 |     logger.info("Patch applied — running regression tests...")
 518 | 
 519 |     # Gate 2: regression test
 520 |     try:
 521 |         test_result = subprocess.run(
 522 |             ["bash", str(REGRESSION_SCRIPT)],
 523 |             capture_output=True, text=True, timeout=300, cwd=str(BASE),
 524 |         )
 525 |         test_output = test_result.stdout + test_result.stderr
 526 |         fail_count = len(re.findall(r"FAIL", test_output))
 527 |     except Exception as e:
 528 |         logger.error("Regression test error: %s", e)
 529 |         fail_count = 999
 530 | 
 531 |     if fail_count > 0:
 532 |         # Gate 3: revert on failure
 533 |         logger.warning("Regression tests failed (%d FAILs) — reverting patch", fail_count)
 534 |         subprocess.run(
 535 |             ["git", "checkout", "--", affected_file],
 536 |             capture_output=True, cwd=str(BASE),
 537 |         )
 538 |         send_telegram(
 539 |             f"\U0001f534 <b>PATCH REVERTED</b> for <code>{fname}</code>\n"
 540 |             f"\U0001f4cb {diag_text[:200]}\n"
 541 |             f"\U0001f9ea Regression: {fail_count} FAILs\n"
 542 |             f"\u21a9\ufe0f Escalating to Claude Code..."
 543 |         )
 544 |         # Qwen failed — escalate to CC
 545 |         launch_cc_fix_session(crash_class, pattern, log_tail, affected_file)
 546 |         return
 547 | 
 548 |     # Success — commit + record
 549 |     logger.info("All tests passed — committing patch")
 550 |     record_patch(affected_file)
 551 |     increment_patch_count()
 552 | 
 553 |     subprocess.run(
 554 |         ["git", "add", affected_file],
 555 |         capture_output=True, cwd=str(BASE),
 556 |     )
 557 |     commit_msg = f"fix(watchdog): auto-patch {fname} — {diag_text[:80]}"
 558 |     subprocess.run(
 559 |         ["git", "commit", "-m", commit_msg],
 560 |         capture_output=True, cwd=str(BASE),
 561 |     )
 562 | 
 563 |     # Log patch to JSONL
 564 |     patch_record = {
 565 |         "timestamp": datetime.now(timezone.utc).isoformat(),
 566 |         "crash_class": crash_class,
 567 |         "pattern": pattern,
 568 |         "file": affected_file,
 569 |         "diagnosis": diag_text,
 570 |         "confidence": confidence,
 571 |         "tests_passed": True,
 572 |     }
 573 |     with open(PATCH_LOG, "a") as f:
 574 |         f.write(json.dumps(patch_record) + "\n")
 575 | 
 576 |     # Restart render loop if it was dead
 577 |     if not process_alive("overnight_render_loop"):
 578 |         logger.info("Render loop is dead — attempting restart")
 579 |         subprocess.Popen(
 580 |             ["bash", "-c",
 581 |              f"cd {BASE} && nohup python3 overnight_render_loop.py "
 582 |              f">> {LOGS_DIR}/overnight_loop.log 2>&1 &"],
 583 |         )
 584 | 
 585 |     send_telegram(
 586 |         f"\u2705 <b>PATCH APPLIED</b> — <code>{fname}</code>\n"
 587 |         f"\U0001f4cb {diag_text[:200]}\n"
 588 |         f"\U0001f3af Confidence: {confidence:.0%}\n"
 589 |         f"\U0001f9ea Regression: ALL PASS\n"
 590 |         f"\U0001f4dd Committed: {commit_msg[:80]}"
 591 |     )
 592 | 
 593 | 
 594 | # ---------------------------------------------------------------------------
 595 | # .pyc Cleanup
 596 | # ---------------------------------------------------------------------------
 597 | 
 598 | def clear_pyc():
 599 |     """Delete all .pyc files and __pycache__ dirs — gospel law 10."""
 600 |     subprocess.run(
 601 |         ["find", str(BASE), "-name", "*.pyc", "-delete"],
 602 |         capture_output=True, timeout=30,
 603 |     )
 604 |     subprocess.run(
 605 |         ["find", str(BASE), "-name", "__pycache__", "-type", "d",
 606 |          "-exec", "rm", "-rf", "{}", "+"],
 607 |         capture_output=True, timeout=30,
 608 |     )
 609 |     logger.info("Cleared all .pyc files and __pycache__ dirs")
 610 | 
 611 | 
 612 | # ---------------------------------------------------------------------------
 613 | # CC Healing Loop — Autonomous Claude Code Repair
 614 | # ---------------------------------------------------------------------------
 615 | 
 616 | def launch_cc_fix_session(crash_class, pattern, log_tail, affected_file):
 617 |     """Write spec and launch CC session to fix crash autonomously.
 618 | 
 619 |     Triggers when Qwen's own patch fails or for Class C crashes.
 620 |     Reads QWEN_CONTEXT_BIBLE.md + per-render context into the spec.
 621 |     """
 622 |     logger.info("Launching CC fix session for %s — %s", crash_class, pattern)
 623 | 
 624 |     # 1. Load the context bible
 625 |     bible_path = BASE / "docs" / "QWEN_CONTEXT_BIBLE.md"
 626 |     bible = ""
 627 |     if bible_path.exists():
 628 |         try:
 629 |             bible = bible_path.read_text()
 630 |         except Exception as e:
 631 |             logger.warning("Could not read QWEN_CONTEXT_BIBLE.md: %s", e)
 632 | 
 633 |     # 2. Load per-render context file
 634 |     ctx_file = Path(f"/tmp/render_context_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json")
 635 |     render_ctx = ""
 636 |     if ctx_file.exists():
 637 |         try:
 638 |             render_ctx = json.dumps(json.loads(ctx_file.read_text()), indent=2)
 639 |         except Exception:
 640 |             pass
 641 | 
 642 |     # 3. Build targeted CC spec from crash context
 643 |     spec_name = f"cc_watchdog_autofix_{int(time.time())}.md"
 644 |     spec_path = BASE / "docs" / spec_name
 645 | 
 646 |     crash_spec = f"""Read ~/protocol_pulse/PIPELINE_LAWS.md first.
 647 | 
 648 | AUTONOMOUS WATCHDOG REPAIR — {pattern}
 649 | Triggered by: {crash_class} crash detected at {datetime.now(timezone.utc).isoformat()}
 650 | 
 651 | CRASH LOG (last 50 lines):
 652 | {log_tail}
 653 | 
 654 | AFFECTED FILE: {affected_file}
 655 | 
 656 | TASK:
 657 | 1. Read {affected_file} in full
 658 | 2. Run cross_llm_audit.py --feature pipeline-day3-audit
 659 | 3. Find the exact root cause of: {pattern}
 660 | 4. Fix it. Only fix what the audit confirms broken.
 661 | 5. python3 -m py_compile {affected_file} — must pass
 662 | 6. bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs
 663 | 7. git add {affected_file} && git commit -m "fix(watchdog-auto): {pattern}" && git push
 664 | 8. echo WATCHDOG_FIX_COMPLETE to signal completion
 665 | """
 666 | 
 667 |     # Assemble full spec: bible + render context + crash spec
 668 |     full_spec = bible
 669 |     if render_ctx:
 670 |         full_spec += "\n\nCURRENT RENDER CONTEXT:\n" + render_ctx
 671 |     full_spec += "\n\n" + crash_spec
 672 | 
 673 |     spec_path.write_text(full_spec)
 674 |     logger.info("CC spec written to %s", spec_path)
 675 | 
 676 |     # 4. Kill any existing watchdog-fix session
 677 |     subprocess.run(["tmux", "kill-session", "-t", "watchdog_fix"], capture_output=True)
 678 |     time.sleep(1)
 679 | 
 680 |     # 5. Launch CC session with spec
 681 |     subprocess.run(["tmux", "new-session", "-d", "-s", "watchdog_fix"], capture_output=True)
 682 |     subprocess.run([
 683 |         "tmux", "send-keys", "-t", "watchdog_fix",
 684 |         f"cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions",
 685 |         "Enter",
 686 |     ], capture_output=True)
 687 |     time.sleep(5)
 688 |     subprocess.run([
 689 |         "tmux", "send-keys", "-t", "watchdog_fix",
 690 |         f"/read docs/{spec_name}",
 691 |         "Enter",
 692 |     ], capture_output=True)
 693 | 
 694 |     # 6. Telegram alert
 695 |     send_telegram(
 696 |         "\U0001f527 <b>WATCHDOG AUTO-REPAIR LAUNCHED</b>\n"
 697 |         f"Crash: <code>{pattern}</code>\n"
 698 |         f"Class: {crash_class}\n"
 699 |         f"File: <code>{Path(affected_file).name if affected_file else 'unknown'}</code>\n"
 700 |         f"CC session: <code>watchdog_fix</code>\n"
 701 |         f"Monitoring for up to 45 minutes..."
 702 |     )
 703 | 
 704 |     # 7. Monitor CC session for up to 45 minutes
 705 |     deadline = time.time() + 2700  # 45 min
 706 |     fix_detected = False
 707 |     while time.time() < deadline:
 708 |         time.sleep(60)
 709 |         try:
 710 |             pane = subprocess.run(
 711 |                 ["tmux", "capture-pane", "-t", "watchdog_fix", "-p"],
 712 |                 capture_output=True, text=True, timeout=10,
 713 |             ).stdout
 714 |             if "WATCHDOG_FIX_COMPLETE" in pane:
 715 |                 fix_detected = True
 716 |                 break
 717 |             if "regression_test" in pane.lower() and "0 FAIL" in pane:
 718 |                 fix_detected = True
 719 |                 break
 720 |         except Exception:
 721 |             pass
 722 | 
 723 |     # 8. Clear .pyc before restart
 724 |     clear_pyc()
 725 | 
 726 |     # 9. Restart render loop after fix
 727 |     subprocess.run(["pkill", "-f", "overnight_render_loop"], capture_output=True)
 728 |     subprocess.run(["pkill", "-f", "daily_producer"], capture_output=True)
 729 |     time.sleep(3)
 730 | 
 731 |     subprocess.run([
 732 |         "tmux", "send-keys", "-t", "render_main",
 733 |         "cd ~/protocol_pulse && git pull && python3 overnight_render_loop.py --daemon",
 734 |         "Enter",
 735 |     ], capture_output=True)
 736 | 
 737 |     status = "FIX DETECTED" if fix_detected else "TIMEOUT (45min)"
 738 |     send_telegram(
 739 |         "\u2705 <b>WATCHDOG REPAIR COMPLETE</b>\n"
 740 |         f"Status: {status}\n"
 741 |         f"Crash: <code>{pattern}</code>\n"
 742 |         f"Render loop restarted.\n"
 743 |         f"Next grade in ~90 minutes."
 744 |     )
 745 |     logger.info("CC fix session complete — status: %s", status)
 746 | 
 747 | 
 748 | # ===================================================================
 749 | # LAYER 1 — REACTIVE CHECK (every 60s)
 750 | # ===================================================================
 751 | 
 752 | def run_reactive_check():
 753 |     """Tail overnight_loop.log, detect crashes, diagnose + patch."""
 754 |     logger.info("-- REACTIVE CHECK --")
 755 | 
 756 |     # Self-health: is Ollama alive?
 757 |     if not ollama_healthy():
 758 |         logger.error("Ollama not responding on %s", OLLAMA_URL)
 759 |         send_telegram(
 760 |             "\u26a0\ufe0f <b>WATCHDOG ALERT</b>: Ollama not responding on GPU 2 "
 761 |             "— self-restart attempted"
 762 |         )
 763 |         subprocess.Popen(
 764 |             ["bash", "-c",
 765 |              "CUDA_VISIBLE_DEVICES=2 OLLAMA_HOST=127.0.0.1:11435 "
 766 |              "/usr/local/bin/ollama serve &"],
 767 |         )
 768 |         return
 769 | 
 770 |     # Write last-run timestamp for self-health monitoring
 771 |     Path("/tmp/watchdog_last_run.txt").write_text(
 772 |         datetime.now(timezone.utc).isoformat()
 773 |     )
 774 | 
 775 |     # Check render loop alive — auto-restart during active hours (8am-11pm ET)
 776 |     loop_alive = process_alive("overnight_render_loop")
 777 |     if not loop_alive:
 778 |         # ET = UTC-4 (EDT) or UTC-5 (EST). Use UTC-4 for summer.
 779 |         et_hour = (datetime.now(timezone.utc) - timedelta(hours=4)).hour
 780 |         if 8 <= et_hour <= 23:
 781 |             logger.warning("Render loop DEAD during active hours (ET %d:00) — auto-restarting", et_hour)
 782 |             clear_pyc()
 783 |             subprocess.run([
 784 |                 "tmux", "send-keys", "-t", "render_main",
 785 |                 "cd ~/protocol_pulse && git pull && python3 overnight_render_loop.py --daemon",
 786 |                 "Enter",
 787 |             ], capture_output=True)
 788 |             send_telegram(
 789 |                 "\u26a0\ufe0f <b>WATCHDOG AUTO-RESTART</b>\n"
 790 |                 f"Render loop was dead at ET {et_hour}:00\n"
 791 |                 "Auto-restarted in tmux <code>render_main</code>"
 792 |             )
 793 |         else:
 794 |             logger.info("Render loop dead but outside active hours (ET %d:00) — skipping restart", et_hour)
 795 | 
 796 |     # Tail the log
 797 |     log_tail = tail_file(OVERNIGHT_LOG, 50)
 798 |     # CRITICAL FIX: also scan producer_debug.log — KeyErrors live there not in loop log
 799 |     producer_log = Path("/tmp/producer_debug.log")
 800 |     if producer_log.exists():
 801 |         producer_tail = tail_file(producer_log, 30)
 802 |         if "KeyError" in producer_tail or "Traceback" in producer_tail:
 803 |             log_tail = log_tail + chr(10) + producer_tail
 804 |     if not log_tail.strip():
 805 |         logger.info("No log content to analyze")
 806 |         return
 807 | 
 808 |     # Classify
 809 |     crash_class, pattern = classify_crash(log_tail)
 810 |     if not crash_class:
 811 |         logger.info("No crash patterns detected — all clear")
 812 |         return
 813 | 
 814 |     logger.info("CRASH DETECTED: CLASS %s — %s", crash_class, pattern)
 815 |     diagnose_and_patch(log_tail, crash_class, pattern)
 816 | 
 817 | 
 818 | # ===================================================================
 819 | # LAYER 2 — PERIODIC HEALTH SCAN (every 15 min)
 820 | # ===================================================================
 821 | 
 822 | def run_health_scan():
 823 |     """Fresh system health check — reads everything from scratch."""
 824 |     logger.info("-- HEALTH SCAN --")
 825 | 
 826 |     checks = {}
 827 | 
 828 |     # Render loop alive?
 829 |     checks["render_loop"] = process_alive("overnight_render_loop")
 830 | 
 831 |     # Flask alive?
 832 |     checks["flask"] = flask_alive()
 833 | 
 834 |     # Ollama alive?
 835 |     checks["ollama"] = ollama_healthy()
 836 | 
 837 |     # GPU VRAM
 838 |     gpus = gpu_vram()
 839 |     checks["gpus"] = []
 840 |     for g in gpus:
 841 |         pct = round(g["vram_used_mb"] / g["vram_total_mb"] * 100, 1) if g["vram_total_mb"] > 0 else 0
 842 |         checks["gpus"].append({
 843 |             "index": g["index"],
 844 |             "used_mb": g["vram_used_mb"],
 845 |             "total_mb": g["vram_total_mb"],
 846 |             "pct": pct,
 847 |         })
 848 |         if g["index"] in (0, 1) and pct > 90:
 849 |             send_telegram(
 850 |                 f"\u26a0\ufe0f <b>GPU {g['index']} VRAM HIGH</b>: {pct}% "
 851 |                 f"({g['vram_used_mb']}MB / {g['vram_total_mb']}MB)"
 852 |             )
 853 | 
 854 |     # Disk space
 855 |     free_gb = disk_free_gb()
 856 |     checks["disk_free_gb"] = free_gb
 857 |     if 0 < free_gb < 200:
 858 |         send_telegram(f"\u26a0\ufe0f <b>LOW DISK</b>: {free_gb}GB free (threshold: 200GB)")
 859 | 
 860 |     # Last successful grade from loop log
 861 |     last_grade = "UNKNOWN"
 862 |     if OVERNIGHT_LOG.exists():
 863 |         try:
 864 |             result = subprocess.run(
 865 |                 ["grep", "-oP", r"GRADE: [A-F]", str(OVERNIGHT_LOG)],
 866 |                 capture_output=True, text=True, timeout=10,
 867 |             )
 868 |             grades = result.stdout.strip().splitlines()
 869 |             if grades:
 870 |                 last_grade = grades[-1]
 871 |         except Exception:
 872 |             pass
 873 |     checks["last_grade"] = last_grade
 874 | 
 875 |     # Audio lines in TTS cache
 876 |     audio_pattern = str(BASE / "video_pipeline_v3" / "tts_cache" / "*.m4a")
 877 |     audio_count = len(glob.glob(audio_pattern))
 878 |     checks["audio_files_in_cache"] = audio_count
 879 | 
 880 |     # Patches in last 24h
 881 |     patches_24h = 0
 882 |     if PATCH_LOG.exists():
 883 |         cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
 884 |         for line in PATCH_LOG.read_text().splitlines():
 885 |             try:
 886 |                 rec = json.loads(line)
 887 |                 if rec.get("timestamp", "") > cutoff:
 888 |                     patches_24h += 1
 889 |             except json.JSONDecodeError:
 890 |                 pass
 891 |     checks["patches_24h"] = patches_24h
 892 | 
 893 |     logger.info(
 894 |         "Health: loop=%s flask=%s ollama=%s disk=%.0fGB grade=%s patches_24h=%d",
 895 |         checks["render_loop"], checks["flask"], checks["ollama"],
 896 |         free_gb, last_grade, patches_24h,
 897 |     )
 898 | 
 899 |     # Alert if critical services down
 900 |     issues = []
 901 |     if not checks["render_loop"]:
 902 |         issues.append("\u274c Render loop DOWN")
 903 |     if not checks["flask"]:
 904 |         issues.append("\u274c Flask DOWN")
 905 |     if not checks["ollama"]:
 906 |         issues.append("\u274c Ollama DOWN")
 907 | 
 908 |     if issues:
 909 |         send_telegram(
 910 |             "\u26a0\ufe0f <b>HEALTH SCAN ALERT</b>\n" + "\n".join(issues)
 911 |         )
 912 | 
 913 |     # Ask Ollama for health assessment (fresh context)
 914 |     if ollama_healthy():
 915 |         health_prompt = (
 916 |             f"System health snapshot:\n{json.dumps(checks, indent=2)}\n\n"
 917 |             "Briefly assess: any concerning patterns? One paragraph max."
 918 |         )
 919 |         assessment = ollama_chat(
 920 |             "You are a DevOps engineer monitoring a video production pipeline. Be concise.",
 921 |             health_prompt,
 922 |         )
 923 |         if assessment:
 924 |             logger.info("Health assessment: %s", assessment[:200])
 925 | 
 926 |     return checks
 927 | 
 928 | 
 929 | # ===================================================================
 930 | # LAYER 3 — PATTERN ANALYSIS (every 6 hours)
 931 | # ===================================================================
 932 | 
 933 | def run_pattern_analysis():
 934 |     """Analyze 7 days of logs for trends — fresh Ollama conversation."""
 935 |     logger.info("-- PATTERN ANALYSIS --")
 936 | 
 937 |     if not ollama_healthy():
 938 |         logger.error("Ollama not available for pattern analysis")
 939 |         return
 940 | 
 941 |     # Gather last 7 days of loop logs (tail 2000 lines)
 942 |     log_content = tail_file(OVERNIGHT_LOG, 2000)
 943 | 
 944 |     # Also check episode log files
 945 |     extra_logs = ""
 946 |     for logname in ["episode_morning.log", "episode_noon.log", "episode_evening.log"]:
 947 |         logpath = LOGS_DIR / logname
 948 |         if logpath.exists():
 949 |             extra_logs += f"\n--- {logname} ---\n" + tail_file(logpath, 500)
 950 | 
 951 |     # Read patch history
 952 |     patch_history = ""
 953 |     if PATCH_LOG.exists():
 954 |         patch_history = tail_file(PATCH_LOG, 100)
 955 | 
 956 |     analysis_prompt = (
 957 |         "Analyze these 7 days of render logs. Identify:\n"
 958 |         "1. Most frequent crash type and root cause\n"
 959 |         "2. Time-of-day patterns in failures\n"
 960 |         "3. Any silent degradation in grades\n"
 961 |         "4. Files that appear in >50% of crashes\n"
 962 |         "5. Recommended preventive fixes\n\n"
 963 |         f"OVERNIGHT LOOP LOG (last 2000 lines):\n{log_content[:8000]}\n\n"
 964 |         f"ADDITIONAL EPISODE LOGS:\n{extra_logs[:4000]}\n\n"
 965 |         f"PATCH HISTORY:\n{patch_history[:2000]}"
 966 |     )
 967 | 
 968 |     response = ollama_chat(
 969 |         "You are a senior SRE analyzing production pipeline logs. "
 970 |         "Focus on patterns and trends, not individual events. Be specific with data.",
 971 |         analysis_prompt,
 972 |     )
 973 | 
 974 |     if not response:
 975 |         logger.error("Pattern analysis failed — no Ollama response")
 976 |         return
 977 | 
 978 |     # Write analysis file
 979 |     date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
 980 |     analysis_path = LOGS_DIR / f"watchdog_analysis_{date_str}.md"
 981 |     analysis_path.write_text(
 982 |         f"# Watchdog Pattern Analysis — {date_str}\n\n{response}\n"
 983 |     )
 984 |     logger.info("Analysis written to %s", analysis_path)
 985 | 
 986 |     # Check for P0 patterns
 987 |     if any(kw in response.lower() for kw in ["critical", "p0", "urgent", "data loss", "cascade"]):
 988 |         send_telegram(
 989 |             f"\U0001f4ca <b>PATTERN ANALYSIS — P0 FOUND</b>\n\n"
 990 |             f"{response[:800]}"
 991 |         )
 992 |     else:
 993 |         logger.info("No P0 patterns found in analysis")
 994 | 
 995 | 
 996 | # ===================================================================
 997 | # LAYER 4 — WEEKLY DEEP AUDIT (Monday 08:00 UTC)
 998 | # ===================================================================
 999 | 
1000 | def run_weekly_audit():
1001 |     """Deep audit: compare gospels vs actual behavior over 30 days."""
1002 |     logger.info("-- WEEKLY AUDIT --")
1003 | 
1004 |     if not ollama_healthy():
1005 |         logger.error("Ollama not available for weekly audit")
1006 |         return
1007 | 
1008 |     # Read gospels
1009 |     gospels_dir = BASE / "docs" / "gospels"
1010 |     gospel_content = ""
1011 |     if gospels_dir.exists():
1012 |         for gf in sorted(gospels_dir.glob("*.md")):
1013 |             text = gf.read_text()[:3000]
1014 |             gospel_content += f"\n--- {gf.name} ---\n{text}\n"
1015 | 
1016 |     # Pipeline laws
1017 |     laws_path = BASE / "PIPELINE_LAWS.md"
1018 |     laws_content = ""
1019 |     if laws_path.exists():
1020 |         laws_content = laws_path.read_text()[:4000]
1021 | 
1022 |     # Last 30 days log (tail 5000 lines)
1023 |     log_content = tail_file(OVERNIGHT_LOG, 5000)
1024 | 
1025 |     # Git log last 50 commits
1026 |     try:
1027 |         git_result = subprocess.run(
1028 |             ["git", "log", "--oneline", "-50"],
1029 |             capture_output=True, text=True, timeout=10, cwd=str(BASE),
1030 |         )
1031 |         git_log = git_result.stdout
1032 |     except Exception:
1033 |         git_log = "(unavailable)"
1034 | 
1035 |     # Patch history
1036 |     patch_history = ""
1037 |     if PATCH_LOG.exists():
1038 |         patch_history = PATCH_LOG.read_text()[-3000:]
1039 | 
1040 |     audit_prompt = (
1041 |         "You are auditing the Protocol Pulse pipeline. Read the gospel docs "
1042 |         "and compare against actual behavior in logs. Identify:\n"
1043 |         "1. Gospel violations (rules being broken)\n"
1044 |         "2. Technical debt accumulating\n"
1045 |         "3. Costs trending up or down\n"
1046 |         "4. Modules that have had >3 patches in 30 days (fragile code)\n"
1047 |         "5. Recommended refactors\n\n"
1048 |         f"GOSPEL DOCS:\n{gospel_content[:6000]}\n\n"
1049 |         f"PIPELINE LAWS:\n{laws_content[:4000]}\n\n"
1050 |         f"LOOP LOG (recent):\n{log_content[:6000]}\n\n"
1051 |         f"GIT LOG:\n{git_log[:2000]}\n\n"
1052 |         f"PATCH HISTORY:\n{patch_history[:2000]}"
1053 |     )
1054 | 
1055 |     response = ollama_chat(
1056 |         "You are a senior engineer auditing a production video pipeline. "
1057 |         "Compare documented rules against actual system behavior. Be specific.",
1058 |         audit_prompt,
1059 |     )
1060 | 
1061 |     if not response:
1062 |         logger.error("Weekly audit failed — no Ollama response")
1063 |         return
1064 | 
1065 |     # Write audit file
1066 |     date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
1067 |     audit_path = LOGS_DIR / f"weekly_audit_{date_str}.md"
1068 |     audit_path.write_text(
1069 |         f"# Watchdog Weekly Audit — {date_str}\n\n{response}\n"
1070 |     )
1071 |     logger.info("Audit written to %s", audit_path)
1072 | 
1073 |     # Telegram with top findings
1074 |     send_telegram(
1075 |         f"\U0001f4cb <b>WEEKLY AUDIT — {date_str}</b>\n\n"
1076 |         f"{response[:800]}"
1077 |     )
1078 | 
1079 | 
1080 | # ===================================================================
1081 | # DAILY BRIEFING (09:00 ET / 13:00 UTC)
1082 | # ===================================================================
1083 | 
1084 | def send_daily_briefing():
1085 |     """Morning Telegram summary — gospel format."""
1086 |     logger.info("-- DAILY BRIEFING --")
1087 | 
1088 |     date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
1089 | 
1090 |     # Last grade
1091 |     last_grade = "UNKNOWN"
1092 |     last_score = "?"
1093 |     last_time = "?"
1094 |     if OVERNIGHT_LOG.exists():
1095 |         try:
1096 |             result = subprocess.run(
1097 |                 ["grep", "-P", r"GRADE:", str(OVERNIGHT_LOG)],
1098 |                 capture_output=True, text=True, timeout=10,
1099 |             )
1100 |             lines = result.stdout.strip().splitlines()
1101 |             if lines:
1102 |                 last_line = lines[-1]
1103 |                 grade_match = re.search(r"GRADE:\s*([A-F])", last_line)
1104 |                 if grade_match:
1105 |                     last_grade = grade_match.group(1)
1106 |                 score_match = re.search(r"(\d+)/100", last_line)
1107 |                 if score_match:
1108 |                     last_score = score_match.group(1)
1109 |                 time_match = re.search(r"(\d{2}:\d{2})", last_line)
1110 |                 if time_match:
1111 |                     last_time = time_match.group(1)
1112 |         except Exception:
1113 |             pass
1114 | 
1115 |     # Patches in 24h
1116 |     patches_24h = 0
1117 |     if PATCH_LOG.exists():
1118 |         cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
1119 |         for line in PATCH_LOG.read_text().splitlines():
1120 |             try:
1121 |                 rec = json.loads(line)
1122 |                 if rec.get("timestamp", "") > cutoff:
1123 |                     patches_24h += 1
1124 |             except json.JSONDecodeError:
1125 |                 pass
1126 | 
1127 |     # Disk
1128 |     free_gb = disk_free_gb()
1129 | 
1130 |     # GPU 2 VRAM
1131 |     gpu2_vram = "?"
1132 |     for g in gpu_vram():
1133 |         if g["index"] == 2:
1134 |             gpu2_vram = f"{g['vram_used_mb'] / 1024:.1f}GB"
1135 | 
1136 |     # Articles count today
1137 |     article_count = "?"
1138 |     db_path = BASE / "instance" / "protocol_pulse.db"
1139 |     if db_path.exists():
1140 |         try:
1141 |             import sqlite3
1142 |             conn = sqlite3.connect(str(db_path))
1143 |             today_start = datetime.now(timezone.utc).replace(
1144 |                 hour=0, minute=0, second=0
1145 |             ).isoformat()
1146 |             row = conn.execute(
1147 |                 "SELECT COUNT(*) FROM articles WHERE created_at > ?",
1148 |                 (today_start,)
1149 |             ).fetchone()
1150 |             article_count = str(row[0]) if row else "0"
1151 |             conn.close()
1152 |         except Exception:
1153 |             pass
1154 | 
1155 |     # Alerts in 24h
1156 |     alert_count = 0
1157 |     if LOG_FILE.exists():
1158 |         try:
1159 |             result = subprocess.run(
1160 |                 ["grep", "-c", "-E", "CRASH DETECTED|PATCH|ALERT", str(LOG_FILE)],
1161 |                 capture_output=True, text=True, timeout=10,
1162 |             )
1163 |             alert_count = int(result.stdout.strip()) if result.stdout.strip() else 0
1164 |         except Exception:
1165 |             pass
1166 | 
1167 |     # Determine status
1168 |     issues = []
1169 |     if not process_alive("overnight_render_loop"):
1170 |         issues.append("render loop down")
1171 |     if not flask_alive():
1172 |         issues.append("Flask down")
1173 |     if not ollama_healthy():
1174 |         issues.append("Ollama down")
1175 | 
1176 |     status = "\u2705 All systems nominal" if not issues else f"\u274c Issues: {', '.join(issues)}"
1177 | 
1178 |     briefing = (
1179 |         f"\U0001f916 <b>WATCHDOG DAILY — {date_str}</b>\n"
1180 |         f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
1181 |         f"\U0001f3ac Render: {last_grade} ({last_score}/100) at {last_time}\n"
1182 |         f"\U0001f527 Patches applied: {patches_24h} (last 24h)\n"
1183 |         f"\U0001f4be Disk free: {free_gb}GB\n"
1184 |         f"\U0001f9e0 GPU 2 (Watchdog): {gpu2_vram} / 24GB\n"
1185 |         f"\U0001f4ca Articles generated: {article_count}\n"
1186 |         f"\u26a0\ufe0f Alerts: {alert_count}\n"
1187 |         f"{status}"
1188 |     )
1189 | 
1190 |     send_telegram(briefing)
1191 |     logger.info("Daily briefing sent")
1192 | 
1193 | 
1194 | # ===================================================================
1195 | # MAIN — route by --mode flag
1196 | # ===================================================================
1197 | 
1198 | def main():
1199 |     parser = argparse.ArgumentParser(description="Protocol Pulse Local LLM Watchdog")
1200 |     parser.add_argument(
1201 |         "--mode",
1202 |         choices=["reactive", "health", "pattern", "audit", "briefing"],
1203 |         default="reactive",
1204 |         help="Check layer to run",
1205 |     )
1206 |     args = parser.parse_args()
1207 | 
1208 |     logger.info("=" * 50)
1209 |     logger.info(
1210 |         "WATCHDOG RUN — mode=%s — %s",
1211 |         args.mode, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
1212 |     )
1213 |     logger.info("=" * 50)
1214 | 
1215 |     if args.mode == "reactive":
1216 |         run_reactive_check()
1217 |     elif args.mode == "health":
1218 |         run_health_scan()
1219 |     elif args.mode == "pattern":
1220 |         run_pattern_analysis()
1221 |     elif args.mode == "audit":
1222 |         run_weekly_audit()
1223 |     elif args.mode == "briefing":
1224 |         send_daily_briefing()
1225 | 
1226 |     logger.info("WATCHDOG RUN COMPLETE — mode=%s", args.mode)
1227 | 
1228 | 
1229 | if __name__ == "__main__":
1230 |     main()
1231 | 
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
