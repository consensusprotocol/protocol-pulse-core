# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: render-improvement-loop
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
# ARCHITECTURE AUDIT REPORT — RENDER IMPROVEMENT LOOP

Below is a detailed analysis of the Gospel Spec for the autonomous render improvement loop, addressing the 8 critical questions with specific failure modes, severity ratings, mitigations, and citations to the relevant sections of the gospel (assumed structure based on context since the gospel text is not provided in full).

---

### Q1 — INTEGRATION RISK
- **STATE the failure mode(s) clearly**: The use of flag files (`/tmp/render_fix_complete_iterN`) for integration with `overnight_render_loop.py` introduces several risks: (1) Race conditions where the render loop checks for the flag file before the improvement loop writes it, causing premature continuation or timeout; (2) Stale flag files from previous iterations or crashes not being cleaned up, leading to false positives; (3) A crash in the improvement loop preventing the flag file from being written, potentially blocking the overnight loop indefinitely if it waits for the flag.
- **RATE the severity**: CRITICAL
- **PRESCRIBE the exact mitigation**: Implement a robust file locking mechanism (e.g., using `fcntl` or a dedicated lock file) to prevent race conditions. Add a cleanup routine at the start of each iteration to remove stale flag files based on timestamp or iteration number. Introduce a timeout mechanism in the overnight loop to proceed if the flag isn't written within a specified window (e.g., 60 minutes), logging the event as a failure. Define a heartbeat file updated by the improvement loop to signal it is alive, allowing the overnight loop to detect crashes.
- **CITE the gospel section that needs updating**: Section on "Integration with Overnight Render Loop" (assumed title). Add a subsection titled "Flag File Management and Failure Recovery" detailing the locking, cleanup, timeout, and heartbeat mechanisms.

---

### Q2 — QWEN RELIABILITY
- **STATE the failure mode(s) clearly**: The loop's dependency on Qwen3:30b via Ollama at `localhost:11434` risks failure if (1) Ollama is down or unreachable, (2) the Qwen model is not loaded or crashes during inference, or (3) Qwen returns malformed JSON, causing parsing errors downstream. Without graceful degradation, this could halt the entire render cycle.
- **RATE the severity**: HIGH
- **PRESCRIBE the exact mitigation**: Implement a fallback mechanism where, if Qwen fails (connection error, timeout, or malformed output), the loop defaults to a predefined heuristic or skips the dimension with a logged warning, ensuring the render cycle continues. Add a health check for Ollama before starting the loop (e.g., a simple API ping). Include retry logic (e.g., 3 attempts with exponential backoff) for transient failures. Document a manual override to use an alternative local model or external API if Qwen is persistently unavailable.
- **CITE the gospel section that needs updating**: Section on "Qwen3:30b Integration" (assumed title). Add a subsection titled "Reliability and Fallbacks" to specify health checks, retries, fallback heuristics, and manual overrides.

---

### Q3 — CC SESSION DETECTION
- **STATE the failure mode(s) clearly**: Polling tmux for CC session slots risks misidentification if zombie sessions from previous crashes persist, leading to the loop waiting indefinitely or incorrectly assuming a slot is occupied. The gospel does not specify how to differentiate live CC sessions from dead ones, risking deadlock or resource waste.
- **RATE the severity**: HIGH
- **PRESCRIBE the exact mitigation**: Use `tmux list-sessions -F '#{session_name} #{session_attached} #{session_activity}'` to check if a session is actively attached and recently active (based on timestamp). Define a threshold (e.g., no activity for 30 minutes = zombie) to consider a session dead, and forcefully terminate such sessions with `tmux kill-session`. Add a validation step to check if the session is running the expected CC command by inspecting `tmux capture-pane` output for specific CC process signatures.
- **CITE the gospel section that needs updating**: Section on "CC Session Polling" (assumed title). Add a subsection titled "Zombie Session Detection and Cleanup" detailing the tmux commands, activity thresholds, and validation logic.

---

### Q4 — TOKEN COST REALITY
- **STATE the failure mode(s) clearly**: The gospel's $2 soft limit per cycle appears optimistic. With 4-6 failing dimensions per cycle, each requiring Qwen (local, free) plus 2 external LLM calls (~2000 tokens each), at typical API rates (e.g., $0.005/1000 tokens for input, $0.015/1000 for output), a single dimension fix costs ~$0.04-$0.06 (4000 tokens total). For 6 dimensions, this is $0.24-$0.36 per cycle, but retries or additional context could push costs to $0.50-$1.00 per cycle, far exceeding $2 over multiple cycles or days.
- **RATE the severity**: MEDIUM
- **PRESCRIBE the exact mitigation**: Revise the cost estimate to a realistic $1 per cycle cap with a hard $5 daily limit, logging a warning and pausing e

## GEMINI — CYCLE 1 OUTPUT
Excellent. As an AI model specializing in code and architecture review, I will now perform the requested forensic audit of the GOSPEL SPEC for the `render-improvement-loop` feature.

My analysis is based on the design described in the 8 critical questions and the operational context provided by the existing code files (`overnight_render_loop.py`, `cross_llm_audit.py`, `clip_extractor.py`).

---

### **Q1 — INTEGRATION RISK**
The loop integrates with `overnight_render_loop.py` via flag files (`/tmp/render_fix_complete_iterN`).

*   **FAILURE MODE(S):**
    1.  **Indefinite Stall:** The improvement loop crashes or hangs before writing the success flag. `overnight_render_loop.py` enters its wait state and never exits, as the flag file is never created. This blocks all subsequent renders until a human intervenes.
    2.  **Stale Flag Misdirection:** A flag file from a previous day's crashed run (`/tmp/render_fix_complete_iter3`) is left behind. The next day, when the main loop reaches iteration 3, it sees this old flag, incorrectly assumes the fix was successful for the *current* run, and proceeds with the unimproved, faulty code, leading to repeated failures.
    3.  **Race Condition:** The main loop checks for the flag's existence, a system cleanup job (`tmpwatch`/`tmpreaper`) removes it, and then the main loop enters its wait state. This is a low probability but a valid race condition.

*   **SEVERITY:** CRITICAL

*   **MITIGATION:**
    1.  **Stateful Hand-off, Not Just Existence:** The flag-based system is too primitive. It should be replaced with a stateful JSON file. The main loop writes a "request for fix" file (`/tmp/fix_request_iterN.json`) containing its `pid`, `iteration`, and a `request_timestamp`. The improvement loop reads this, performs its work, and then writes a "fix complete" file (`/tmp/fix_complete_iterN.json`) containing the original `request_timestamp` and a `completion_timestamp`.
    2.  **Scoped Timeouts:** The main loop's "wait" must not be indefinite. It should have a hard timeout (e.g., 90 minutes) that is independent of the main render timeout. If this timeout is breached, it must log a critical error, send a Telegram alert, and either fail the entire cycle or proceed to the next iteration without the fix.
    3.  **Cleanup on Start:** The main `overnight_render_loop.py` should, on startup, perform a glob search for any `/tmp/render_fix_*.json` files and remove them to ensure a clean slate.

*   **GOSPEL SECTION:** Section 4.1: Inter-Process Communication Protocol

---

### **Q2 — QWEN RELIABILITY**
The loop depends on a local Qwen model via Ollama.

*   **FAILURE MODE(S):**
    1.  **Hard Failure:** The Ollama service is down, the model is not loaded, or it consistently OOMs. Any network call to `localhost:11434` will fail.
    2.  **Malformed Output:** Qwen returns non-JSON output, incomplete JSON, or a text refusal instead of the structured data required. This will cause a `json.JSONDecodeError` downstream.
    3.  **Silent Failure:** Qwen returns a structurally valid but semantically useless JSON (`{"fix_spec": null, "reason": "I cannot fulfill this request."}`). The loop might interpret this as "no fix needed" and proceed, failing to correct the underlying issue.

*   **SEVERITY:** HIGH

*   **MITIGATION:**
    1.  **Resilience Wrapper:** All calls to the local LLM must be wrapped in a resilience pattern: a `try/except` block with a connection timeout, a retry mechanism with exponential backoff (e.g., 3 retries over 90 seconds), and a final failure state.
    2.  **Graceful Degradation:** If the local LLM is definitively unavailable after retries, the system must not crash. It should log the error, send a Telegram alert (`"Qwen unavailable, skipping dimension fix for [dimension_name]"`), and gracefully skip the improvement for that *specific dimension*, moving on to the next one. This prevents a local model outage from killing the entire render improvement cycle.
    3.  **Schema Validation:** The JSON response from Qwen must be validated against a known schema (e.g., using `jsonschema`). If validation fails, it should be treated as a hard failure and trigger the retry/degradation logic.

*   **GOSPEL SECTION:** Section 5.3: Local LLM Interaction & Fault Tolerance

---

### **Q3 — CC SESSION DETECTION**
The loop polls `tmux` to detect if a Claude Code session is active.

*   **FAILURE MODE(S):**
    1.  **Zombie Session Deadlock:** A previous `cc_session` crashed, but the tmux session itself (and the shell within it) persists. The polling script sees the session via `tmux ls` and incorrectly assumes it's busy, waiting indefinitely for a zombie process to finish.
    2.  **Ambiguous State:** A human developer might be using a session named `cc_session` for unrelated work, causing the loop to falsely detect a busy state.

*   **SEVERITY:** HIGH

*   **MITIGATION:**
    1.  **Process-Level Verification:** Do not just check for session existence. The definitive check is to inspect

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — RENDER-IMPROVEMENT-LOOP — CYCLE 1
Generated: 2026-03-24 05:51
Models: grok, gemini (+1 failed — GPT-4o TPM limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Integration (Flag IPC) | 2/10 | N/A | 2/10 | **2/10** |
| Qwen Reliability | 4/10 | N/A | 4/10 | **4/10** |
| CC Session Detection | 3/10 | N/A | 3/10 | **3/10** |
| Token Cost Reality | 3/10 | N/A | 4/10 | **3/10** |
| DIMENSION_MAP Completeness | 5/10 | N/A | 4/10 | **4/10** |
| Overnight Loop Coupling | 2/10 | N/A | 2/10 | **2/10** |
| Consensus Failure Handling | N/A (cut off) | N/A | N/A (cut off) | **TBD** |
| Overall Architecture | 3/10 | N/A | 3/10 | **3/10** |

> **Note:** GPT-4o failed due to rate limiting (TPM exceeded). All consensus determinations are based on 2 of 3 models. Where both Gemini and Grok agree, confidence is rated HIGH. No findings are rated UNANIMOUS (requires all 3); they are instead rated MAJORITY (2/2 available models).

---

## UNANIMOUS FINDINGS (all 2 available models agree — implement unconditionally)

### U1 — Flag-File IPC Is Fatally Fragile
**What it is:** Both models independently flagged the `/tmp/render_fix_complete_iterN` flag-file mechanism as critically broken. A crash before the flag is written causes `overnight_render_loop.py` to stall forever. A stale flag from a previous crash causes the main loop to falsely believe the current iteration was fixed and proceed with unfixed code.

**Which file/line:** `overnight_render_loop.py` — flag-write/flag-read logic; gospel Section on Inter-Process Communication.

**What to change:**
- Replace bare flag-file existence checks with a **stateful JSON handshake**:
  - Main loop writes `/tmp/fix_request_iterN.json` containing `{pid, iteration, request_timestamp}`.
  - Improvement loop reads it, executes, then writes `/tmp/fix_complete_iterN.json` containing `{original_request_timestamp, completion_timestamp, status, dimensions_fixed[]}`.
  - Main loop validates that `fix_complete.request_timestamp == fix_request.request_timestamp` before accepting the result as valid for *this* run.
- `overnight_render_loop.py` must **glob-delete all `/tmp/fix_*.json` files on startup** to ensure clean state.
- The main loop's wait must have a **hard 90-minute per-iteration timeout** independent of the render timeout, with Telegram alert and graceful fail-forward on breach.

---

### U2 — Qwen Has No Fault Tolerance
**What it is:** Both models flagged that if Ollama is down, OOM-killed, returns malformed JSON, or returns a valid-structure but semantically null response, the entire loop crashes or silently produces no fix with no operator awareness.

**Which file/line:** Improvement loop — all `ollama` / `localhost:11434` call sites; gospel Section on Local LLM Integration.

**What to change:**
- Wrap every Ollama call in a resilience block: `try/except` with connection timeout (30s), **3 retries with exponential backoff** (15s, 30s, 60s).
- Validate J

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: overnight_render_loop.py (859 lines)
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
  23 | # ── Rate limiter (audit P0-U1) ────────────────────────────────
  24 | _rate_lock = threading.Lock()
  25 | _rate_calls = []  # list of timestamps
  26 | RATE_LIMIT_CALLS_PER_MINUTE = int(os.getenv("RATE_LIMIT_CALLS_PER_MINUTE", "20"))
  27 | 
  28 | 
  29 | def _rate_limit_wait():
  30 |     """Token-bucket rate limiter for external API calls. Blocks if limit exceeded."""
  31 |     with _rate_lock:
  32 |         now = time.time()
  33 |         _rate_calls[:] = [t for t in _rate_calls if now - t < 60]
  34 |         if len(_rate_calls) >= RATE_LIMIT_CALLS_PER_MINUTE:
  35 |             wait = 60 - (now - _rate_calls[0])
  36 |             if wait > 0:
  37 |                 logging.getLogger('overnight_loop').warning(
  38 |                     f"Rate limit hit ({RATE_LIMIT_CALLS_PER_MINUTE}/min) — waiting {wait:.1f}s"
  39 |                 )
  40 |                 time.sleep(wait)
  41 |         _rate_calls.append(time.time())
  42 | 
  43 | BASE = os.path.dirname(os.path.abspath(__file__))
  44 | PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
  45 | ENV_FILE = os.path.join(BASE, '.env')
  46 | LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
  47 | RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
  48 | HEARTBEAT_FILE = os.path.join(BASE, 'logs', 'loop_heartbeat.json')
  49 | ELEVENLABS_QUOTA_SENTINEL = os.path.join(BASE, 'logs', 'elevenlabs_quota_exhausted')
  50 | TTS_SCRIPT = os.path.join(PIPELINE, 'tts_local.py')
  51 | FORENSICS_TIMEOUT = 600  # 10-minute hard timeout for entire forensics
  52 | MAX_ITERATIONS = 8
  53 | MAX_HOURS = 6
  54 | RETRY_WAIT_SECONDS = 1800  # 30 minutes
  55 | MAX_ATTEMPTS_PER_CYCLE = 2
  56 | CONSECUTIVE_GRADE_FAILURES_THRESHOLD = int(os.getenv("CONSECUTIVE_GRADE_FAILURES_THRESHOLD", "3"))
  57 | CONSECUTIVE_RENDER_ABSENT_THRESHOLD = int(os.getenv("CONSECUTIVE_RENDER_ABSENT_THRESHOLD", "3"))
  58 | 
  59 | # Required env vars — fail fast if missing (audit P1-X5)
  60 | REQUIRED_ENV_VARS = ["GEMINI_API_KEY"]  # others are soft-checked at startup
  61 | 
  62 | os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)
  63 | os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)
  64 | 
  65 | # ── Logging ───────────────────────────────────────────────────────
  66 | logger = logging.getLogger('overnight_loop')
  67 | if not logger.handlers:
  68 |     logger.setLevel(logging.DEBUG)
  69 |     _fmt = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  70 |     _sh = logging.StreamHandler(sys.stdout)
  71 |     _sh.setFormatter(_fmt)
  72 |     logger.addHandler(_sh)
  73 |     _fh = logging.FileHandler(LOG)
  74 |     _fh.setFormatter(_fmt)
  75 |     logger.addHandler(_fh)
  76 | 
  77 | 
  78 | def log(msg):
  79 |     """Backward-compat wrapper."""
  80 |     logger.info(msg)
  81 | 
  82 | 
  83 | def load_env():
  84 |     env = os.environ.copy()
  85 |     env['CUDA_VISIBLE_DEVICES'] = '0'  # Pin pipeline to GPU 0 -- avatar_server owns GPU 1
  86 |     try:
  87 |         with open(ENV_FILE) as f:
  88 |             for line in f:
  89 |                 l = line.strip()
  90 |                 if l and not l.startswith('#') and '=' in l:
  91 |                     k, _, v = l.partition('=')
  92 |                     k = k.strip(); v = v.strip().strip("'").strip('"')
  93 |                     if k: env[k] = v
  94 |     except FileNotFoundError:
  95 |         log(f"CRITICAL: .env file not found at {ENV_FILE}")
  96 |     except Exception as e:
  97 |         log(f"WARNING: .env load failed: {e}")
  98 |     # Validate required env vars (audit P1-X5)
  99 |     missing = [k for k in REQUIRED_ENV_VARS if not env.get(k, '').strip()]
 100 |     if missing:
 101 |         log(f"CRITICAL: Required env vars missing after .env load: {missing}")
 102 |     return env
 103 | 
 104 | 
 105 | def run(cmd, timeout=7200, env=None):
 106 |     try:
 107 |         return subprocess.run(cmd, shell=True, capture_output=True, text=True,
 108 |                              timeout=timeout, env=env or load_env(), cwd=PIPELINE)
 109 |     except subprocess.TimeoutExpired:
 110 |         log(f"TIMEOUT after {timeout}s: {str(cmd)[:80]}")
 111 |         r = subprocess.CompletedProcess(cmd, returncode=-1)
 112 |         r.stdout = ""
 113 |         r.stderr = f"TIMEOUT after {timeout}s"
 114 |         return r
 115 |     except Exception as e:
 116 |         log(f"run() error: {e} cmd={str(cmd)[:80]}")
 117 |         r = subprocess.CompletedProcess(cmd, returncode=-1)
 118 |         r.stdout = ""
 119 |         r.stderr = str(e)
 120 |         return r
 121 | 
 122 | 
 123 | # ── Startup checks ────────────────────────────────────────────────
 124 | def startup_checks():
 125 |     """Verify environment before any render. Returns True if all pass."""
 126 |     ok = True
 127 | 
 128 |     # FFmpeg available
 129 |     try:
 130 |         r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
 131 |         if r.returncode != 0:
 132 |             log("STARTUP FAIL: ffmpeg returned non-zero")
 133 |             ok = False
 134 |         else:
 135 |             ver = r.stdout.split('\n')[0] if r.stdout else '?'
 136 |             log(f"FFmpeg: {ver}")
 137 |     except FileNotFoundError:
 138 |         log("STARTUP FAIL: ffmpeg not found in PATH")
 139 |         ok = False
 140 |     except Exception as e:
 141 |         log(f"STARTUP FAIL: ffmpeg check error: {e}")
 142 |         ok = False
 143 | 
 144 |     # tmux + claude binary validation (audit U2)
 145 |     for binary in ['tmux', 'claude']:
 146 |         if not shutil.which(binary):
 147 |             log(f"STARTUP FAIL: {binary} not found in PATH")
 148 |             ok = False
 149 |         else:
 150 |             log(f"{binary}: found")
 151 | 
 152 |     # Gemini API key check (audit UI-7)
 153 |     env = load_env()
 154 |     if not env.get('GEMINI_API_KEY', '').strip():
 155 |         log("STARTUP FAIL: GEMINI_API_KEY not set")
 156 |         ok = False
 157 |     else:
 158 |         log("GEMINI_API_KEY: present")
 159 | 
 160 |     # Python path includes pipeline
 161 |     if PIPELINE not in sys.path:
 162 |         sys.path.insert(0, PIPELINE)
 163 |     log(f"Pipeline dir: {PIPELINE} (exists={os.path.isdir(PIPELINE)})")
 164 |     if not os.path.isdir(PIPELINE):
 165 |         log("STARTUP FAIL: video_pipeline_v3 directory missing")
 166 |         ok = False
 167 | 
 168 |     # Output directory writable
 169 |     out_dir = os.path.join(PIPELINE, 'output')
 170 |     os.makedirs(out_dir, exist_ok=True)
 171 |     test_file = os.path.join(out_dir, '.write_test')
 172 |     try:
 173 |         with open(test_file, 'w') as f:
 174 |             f.write('ok')
 175 |         os.remove(test_file)
 176 |         log(f"Output dir writable: {out_dir}")
 177 |     except Exception as e:
 178 |         log(f"STARTUP FAIL: output dir not writable: {e}")
 179 |         ok = False
 180 | 
 181 |     # TTS provider check — TTS_PROVIDER env var takes ABSOLUTE precedence (FIX: TTS LOCK)
 182 |     tts_provider_env = env.get('TTS_PROVIDER', '').lower().strip()
 183 |     local_tts = os.path.exists(TTS_SCRIPT)
 184 |     elevenlabs_key = bool(env.get('ELEVENLABS_API_KEY', '').strip())
 185 |     quota_exhausted = os.path.exists(ELEVENLABS_QUOTA_SENTINEL)
 186 | 
 187 |     if tts_provider_env == 'elevenlabs':
 188 |         # Explicit env override — NEVER fall back to local even if tts_local.py exists
 189 |         if elevenlabs_key and not quota_exhausted:
 190 |             log("TTS provider: ElevenLabs (TTS_PROVIDER=elevenlabs, env var override)")
 191 |         elif elevenlabs_key and quota_exhausted:
 192 |             log("WARNING: TTS_PROVIDER=elevenlabs but quota sentinel exists")
 193 |         else:
 194 |             log("STARTUP FAIL: TTS_PROVIDER=elevenlabs but no ELEVENLABS_API_KEY")
 195 |             ok = False
 196 |     elif local_tts:
 197 |         log("TTS provider: LOCAL (tts_local.py found)")
 198 |     elif elevenlabs_key and not quota_exhausted:
 199 |         log("TTS provider: ElevenLabs (API key present)")
 200 |     elif elevenlabs_key and quota_exhausted:
 201 |         log("WARNING: ElevenLabs key present but quota sentinel exists")
 202 |     else:
 203 |         log("WARNING: No TTS provider found (no local TTS, no ElevenLabs key)")
 204 | 
 205 |     if not local_tts and not elevenlabs_key:
 206 |         log("STARTUP FAIL: No TTS provider available")
 207 |         ok = False
 208 | 
 209 |     return ok
 210 | 
 211 | 
 212 | # ── Heartbeat ─────────────────────────────────────────────────────
 213 | _total_episodes = 0
 214 | _consecutive_failures = 0
 215 | _counter_lock = threading.Lock()  # Guard global counters (audit P1-M1)
 216 | 
 217 | 
 218 | def write_heartbeat(verdict, duration_s):
 219 |     """Write heartbeat JSON atomically after every cycle."""
 220 |     global _total_episodes, _consecutive_failures
 221 |     with _counter_lock:
 222 |         if verdict == "PASS":
 223 |             _total_episodes += 1
 224 |             _consecutive_failures = 0
 225 |         elif verdict == "ERROR":
 226 |             _consecutive_failures += 1
 227 |         elif verdict == "HOLD":
 228 |             _consecutive_failures += 1
 229 |         elif verdict == "DEGRADED":
 230 |             _total_episodes += 1
 231 |             _consecutive_failures = 0
 232 | 
 233 |     heartbeat = {
 234 |         "last_run": datetime.now(timezone.utc).isoformat(),
 235 |         "last_verdict": verdict,
 236 |         "last_duration": round(duration_s, 1),
 237 |         "total_episodes": _total_episodes,
 238 |         "consecutive_failures": _consecutive_failures,
 239 |     }
 240 |     try:
 241 |         # Atomic write via temp file + rename (audit UI-6)
 242 |         tmp_path = HEARTBEAT_FILE + '.tmp'
 243 |         with open(tmp_path, 'w') as f:
 244 |             json.dump(heartbeat, f, indent=2)
 245 |         os.replace(tmp_path, HEARTBEAT_FILE)
 246 |         log(f"Heartbeat written: {verdict} | failures={_consecutive_failures}")
 247 |     except Exception as e:
 248 |         log(f"WARNING: heartbeat write failed: {e}")
 249 | 
 250 |     # Telegram alert on 3+ consecutive failures
 251 |     if _consecutive_failures >= 3:
 252 |         send_telegram_alert(
 253 |             f"Protocol Pulse loop: {_consecutive_failures} consecutive failures\n"
 254 |             f"Last verdict: {verdict}\n"
 255 |             f"Time: {heartbeat['last_run']}"
 256 |         )
 257 | 
 258 | 
 259 | def send_telegram_alert(message):
 260 |     """Send alert via Telegram if bot token + chat ID are configured."""
 261 |     env = load_env()
 262 |     token = env.get('TELEGRAM_BOT_TOKEN', '').strip()
 263 |     chat_id = env.get('TELEGRAM_CHAT_ID', '').strip()
 264 |     if not token or not chat_id:
 265 |         log("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 266 |         return
 267 |     try:
 268 |         url = f"https://api.telegram.org/bot{token}/sendMessage"
 269 |         # Use plain text to avoid HTML injection from dynamic content (audit UI-3)
 270 |         payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
 271 |         req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
 272 |         with urllib.request.urlopen(req, timeout=15) as r:
 273 |             log(f"Telegram alert sent (status {r.status})")
 274 |     except Exception as e:
 275 |         log(f"Telegram alert failed: {e}")
 276 | 
 277 | 
 278 | # ── TTS provider awareness ────────────────────────────────────────
 279 | def check_tts_ready():
 280 |     """Check TTS availability before render. Returns (ready, provider_name).
 281 |     TTS_PROVIDER env var takes ABSOLUTE precedence — never fall back to local
 282 |     if TTS_PROVIDER=elevenlabs (FIX: TTS LOCK).
 283 |     """
 284 |     env = load_env()
 285 |     tts_provider_env = env.get('TTS_PROVIDER', '').lower().strip()
 286 | 
 287 |     # TTS_PROVIDER=elevenlabs takes absolute precedence over tts_local.py on disk
 288 |     if tts_provider_env == 'elevenlabs':
 289 |         if not env.get('ELEVENLABS_API_KEY', '').strip():
 290 |             return False, "none (TTS_PROVIDER=elevenlabs but no API key)"
 291 |         if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 292 |             log("ElevenLabs quota sentinel exists — skipping render")
 293 |             return False, "elevenlabs (quota exhausted)"
 294 |         return True, "ElevenLabs (env override)"
 295 | 
 296 |     # Default: check local first, then ElevenLabs
 297 |     local_tts = os.path.exists(TTS_SCRIPT)
 298 |     if local_tts:
 299 |         return True, "local (Kokoro/F5-TTS)"
 300 | 
 301 |     if not env.get('ELEVENLABS_API_KEY', '').strip():
 302 |         return False, "none"
 303 | 
 304 |     if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 305 |         log("ElevenLabs quota sentinel exists — skipping render")
 306 |         return False, "elevenlabs (quota exhausted)"
 307 | 
 308 |     return True, "ElevenLabs"
 309 | 
 310 | 
 311 | def gemini_call(prompt, max_tokens=8000):
 312 |     """Call Gemini API with retry + exponential backoff (audit U4)."""
 313 |     env = load_env()
 314 |     key = env.get('GEMINI_API_KEY', '')
 315 |     url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}'
 316 |     payload = {'contents': [{'parts': [{'text': prompt}]}],
 317 |                'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.05}}
 318 |     data = json.dumps(payload).encode()
 319 | 
 320 |     backoff = [5, 15, 45]
 321 |     last_err = None
 322 |     for attempt in range(3):
 323 |         _rate_limit_wait()  # audit P0-U1: rate limit external API calls
 324 |         try:
 325 |             req = urllib.request.Request(url, data=data,
 326 |                                         headers={'Content-Type': 'application/json'})
 327 |             with urllib.request.urlopen(req, timeout=120) as r:
 328 |                 d = json.loads(r.read())
 329 |                 parts = d['candidates'][0]['content'].get('parts', [])
 330 |                 return next((p['text'] for p in parts if 'text' in p), None)
 331 |         except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
 332 |             last_err = e
 333 |             if attempt < 2:
 334 |                 wait = backoff[attempt]
 335 |                 log(f"Gemini API attempt {attempt+1} failed ({type(e).__name__}: {e}), retrying in {wait}s...")
 336 |                 time.sleep(wait)
 337 |             else:
 338 |                 log(f"Gemini API all 3 attempts failed. Last error: {e}")
 339 |         except Exception as e:
 340 |             last_err = e
 341 |             log(f"Gemini API unexpected error: {e}")
 342 |             break
 343 |     return None
 344 | 
 345 | 
 346 | def run_render(iteration):
 347 |     log(f"RENDER START iteration {iteration}")
 348 |     run("rm -rf tts_cache/ && mkdir -p tts_cache/")
 349 |     log("TTS cache wiped")
 350 |     env = load_env()
 351 |     render_start = time.time()
 352 |     r = run("python3 daily_producer.py --skip-scan", timeout=14400, env=env)
 353 |     log(f"Render exit: {r.returncode}")
 354 |     import glob
 355 |     today = datetime.now().strftime('%Y-%m-%d')
 356 |     candidates = []
 357 |     for pat in [f'output/{today}/*.mp4']:  # today-only — no stale fallback
 358 |         for f in glob.glob(os.path.join(PIPELINE, pat)):
 359 |             if any(x in f for x in ['.bgl_audio', '.intro_mus', '.concat_raw', '.music_mixed', '.whoosh', '.norm']):
 360 |                 continue
 361 |             if not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh']):
 362 |                 # Only accept files produced after render started (audit U3)
 363 |                 if os.path.getmtime(f) >= render_start:
 364 |                     candidates.append((os.path.getmtime(f), f))
 365 |     candidates.sort(reverse=True)
 366 |     out = candidates[0][1] if candidates else None
 367 |     if out:
 368 |         log(f"Output: {out} ({os.path.getsize(out)//1048576}MB)")
 369 |         # Validate render output with ffprobe (audit P2-X3)
 370 |         try:
 371 |             probe = subprocess.run(
 372 |                 ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 373 |                  "-of", "default=noprint_wrappers=1:nokey=1", out],
 374 |                 capture_output=True, text=True, timeout=30
 375 |             )
 376 |             if probe.returncode != 0 or not probe.stdout.strip():
 377 |                 log(f"WARNING: ffprobe rejected output file — corrupt or invalid: {out}")
 378 |                 out = None
 379 |         except Exception as e:
 380 |             log(f"WARNING: ffprobe validation failed: {e}")
 381 |     else:
 382 |         log("FATAL: no output file produced by this render")
 383 |     return out, r.stdout + r.stderr
 384 | 
 385 | 
 386 | def _run_forensics_inner(video):
 387 |     """Inner forensics logic — called within a thread timeout wrapper."""
 388 |     res = {}
 389 |     r = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{video}"')
 390 |     try:
 391 |         p = json.loads(r.stdout)
 392 |         fmt = p.get('format', {}); streams = p.get('streams', [])
 393 |         res['duration'] = float(fmt.get('duration', 0))
 394 |         res['filesize_mb'] = int(fmt.get('size', 0)) / 1048576
 395 |         v = next((s for s in streams if s.get('codec_type') == 'video'), {})
 396 |         a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
 397 |         res['width'] = v.get('width', 0); res['height'] = v.get('height', 0)
 398 |         fps_str = v.get('r_frame_rate', '0/1')
 399 |         if '/' in fps_str:
 400 |             num, den = fps_str.split('/', 1)
 401 |             res['fps'] = float(num) / float(den) if float(den) != 0 else 0
 402 |         else:
 403 |             res['fps'] = float(fps_str) if fps_str else 0
 404 |         res['vcodec'] = v.get('codec_name', '?'); res['acodec'] = a.get('codec_name', '?')
 405 |     except Exception as e:
 406 |         log(f"WARNING: ffprobe parse error: {e}")
 407 |     r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1', timeout=300)
 408 |     segs = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', r.stderr+r.stdout)
 409 |     dur = res.get('duration', 0)
 410 |     res['black_mid_count'] = len([(s,e,d) for s,e,d in segs if float(s)>2 and float(e)<dur-2])
 411 |     r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=120)
 412 |     out = r.stderr + r.stdout
 413 |     im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
 414 |     tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
 415 |     res['integrated_lufs'] = float(im.group(1)) if im else None
 416 |     res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
 417 |     # FIX: freeze threshold n=0.003 (was 0.001 — too sensitive for bg_loop transitions)
 418 |     r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.003:d=1.0" -an -f null - 2>&1', timeout=300)
 419 |     res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))
 420 | 
 421 |     # TTS ARTIFACT CHECK — run in isolated subprocess with hard 45s timeout
 422 |     # Prevents WhisperModel from blocking forensics pipeline
 423 |     tts_artifacts = []
 424 |     tmp_path = None
 425 |     try:
 426 |         tmp_fd, tmp_path = tempfile.mkstemp(suffix='.wav')
 427 |         os.close(tmp_fd)
 428 |         subprocess.run(['ffmpeg', '-y', '-i', video, '-t', '60', '-ar', '16000',
 429 |                  '-ac', '1', tmp_path], capture_output=True, timeout=30)
 430 |         checker = (
 431 |             "import sys, json\n"
 432 |             "from faster_whisper import WhisperModel\n"
 433 |             "model = WhisperModel('tiny', device='cpu', compute_type='int8')\n"
 434 |             "segs, _ = model.transcribe(sys.argv[1], language='en')\n"
 435 |             "t = ' '.join(s.text for s in segs).lower()\n"
 436 |             "bad = ['pause','breath','emphasis','break colon','slash','open bracket','close bracket']\n"
 437 |             "print(json.dumps([w for w in bad if w in t]))\n"
 438 |         )
 439 |         r = subprocess.run(['python3', '-c', checker, tmp_path],
 440 |                     capture_output=True, text=True, timeout=45)
 441 |         if r.returncode == 0 and r.stdout.strip():
 442 |             tts_artifacts = json.loads(r.stdout.strip())
 443 |     except Exception as _e:
 444 |         log(f"TTS artifact check skipped: {_e}")
 445 |     finally:
 446 |         # Guaranteed cleanup (audit M3)
 447 |         if tmp_path and os.path.exists(tmp_path):
 448 |             try:
 449 |                 os.unlink(tmp_path)
 450 |             except OSError:
 451 |                 pass
 452 |     res['tts_artifacts'] = tts_artifacts
 453 |     if tts_artifacts:
 454 |         log(f"TTS ARTIFACT ALERT: narrator reading markers aloud: {tts_artifacts}")
 455 |     log(f"Forensics: {res.get('duration',0):.0f}s {res.get('width')}x{res.get('height')} "
 456 |         f"LUFS={res.get('integrated_lufs')} TP={res.get('true_peak_dbfs')} "
 457 |         f"black={res.get('black_mid_count')} freeze={res.get('freeze_count')}")
 458 |     return res
 459 | 
 460 | 
 461 | def run_forensics(video):
 462 |     """Run forensics with a 10-minute hard thread timeout (task issue #1).
 463 |     If forensics hangs, returns {} so the loop can continue to grading."""
 464 |     log("Running forensics...")
 465 |     result_holder = [None]
 466 |     error_holder = [None]
 467 | 
 468 |     def _target():
 469 |         try:
 470 |             result_holder[0] = _run_forensics_inner(video)
 471 |         except Exception as e:
 472 |             error_holder[0] = e
 473 | 
 474 |     t = threading.Thread(target=_target, daemon=True)
 475 |     t.start()
 476 |     t.join(timeout=FORENSICS_TIMEOUT)
 477 | 
 478 |     if t.is_alive():
 479 |         log(f"WARNING: Forensics exceeded {FORENSICS_TIMEOUT}s hard timeout — returning empty result")
 480 |         return {}
 481 | 
 482 |     if error_holder[0]:
 483 |         log(f"WARNING: Forensics thread raised: {error_holder[0]}")
 484 |         return {}
 485 | 
 486 |     return result_holder[0] or {}
 487 | 
 488 | 
 489 | def grade_with_gemini(video, forensics, render_log):
 490 |     log("Calling Gemini for 24-dimension grade...")
 491 |     prompt = f"""Grade this Protocol Pulse Bitcoin show episode across 24 dimensions.
 492 | Only award Grade A if you would genuinely be proud to publish it as world-class Bitcoin media.
 493 | 
 494 | FORENSICS:
 495 | - Duration: {forensics.get('duration',0):.1f}s ({forensics.get('duration',0)/60:.1f}min)
 496 | - Resolution: {forensics.get('width')}x{forensics.get('height')} @ {forensics.get('fps',0):.1f}fps
 497 | - Codec: {forensics.get('vcodec')} + {forensics.get('acodec')}
 498 | - Loudness: {forensics.get('integrated_lufs')} LUFS (target -16 to -14)
 499 | - True Peak: {forensics.get('true_peak_dbfs')} dBFS (must be <= -1.0)
 500 | - Black frames (mid): {forensics.get('black_mid_count',0)} (0 = perfect)
 501 | - Freeze frames: {forensics.get('freeze_count',0)} (0 = perfect)
 502 | 
 503 | RENDER LOG (last 200 lines):
 504 | {chr(10).join(render_log.splitlines()[-200:])}
 505 | 
 506 | RUBRIC (24 dimensions, Grade A = score >= 88, zero critical failures):
 507 | Technical (40%): duration, resolution, fps, loudness, true_peak, black_frames, silence, freezes, codec, file_integrity
 508 | Content (35%): clip_relevance, script_quality, cold_open, narrative_arc, host_authenticity, episode_title, no_filler, timeliness
 509 | Production (25%): music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing
 510 | 
 511 | Respond ONLY with raw JSON (no fences):
 512 | {{"grade":"A|B|C|D|F","overall_score":0-100,"broadcast_ready":true|false,
 513 | "dimensions":{{"duration_check":{{"score":0-10,"note":""}},"resolution_check":{{"score":0-10,"note":""}},"framerate_check":{{"score":0-10,"note":""}},"loudness_check":{{"score":0-10,"note":""}},"true_peak_check":{{"score":0-10,"note":""}},"black_frames_check":{{"score":0-10,"note":""}},"silence_check":{{"score":0-10,"note":""}},"freeze_check":{{"score":0-10,"note":""}},"codec_check":{{"score":0-10,"note":""}},"file_integrity_check":{{"score":0-10,"note":""}},"clip_relevance":{{"score":0-10,"note":""}},"script_quality":{{"score":0-10,"note":""}},"cold_open_hook":{{"score":0-10,"note":""}},"narrative_arc":{{"score":0-10,"note":""}},"host_authenticity":{{"score":0-10,"note":""}},"episode_title":{{"score":0-10,"note":""}},"no_filler":{{"score":0-10,"note":""}},"timeliness":{{"score":0-10,"note":""}},"music_mix":{{"score":0-10,"note":""}},"transitions":{{"score":0-10,"note":""}},"visual_polish":{{"score":0-10,"note":""}},"no_artifacts":{{"score":0-10,"note":""}},"audio_quality":{{"score":0-10,"note":""}},"pacing":{{"score":0-10,"note":""}}}},
 514 | "critical_failures":[],"warnings":[],"strengths":[],"targeted_fix_instructions":"Precise instructions for CC session to fix only failing dimensions - file, function, lines.",
 515 | "verdict":"One punchy sentence"}}"""
 516 |     text = gemini_call(prompt, 8000)
 517 |     if not text: return None
 518 |     clean = text.strip()
 519 |     for fence in ['```json', '```']:
 520 |         if fence in clean:
 521 |             clean = clean.split(fence)[1].split('```')[0].strip()
 522 |     try: return json.loads(clean)
 523 |     except json.JSONDecodeError as e: log(f"JSON parse fail: {e} — {clean[:200]}"); return None
 524 | 
 525 | 
 526 | def fire_cc_fix(iteration, grade_result):
 527 |     """P0 Fix 2: No more CC self-healing from the render loop.
 528 |     CLASS A/B: log failure details for Qwen watchdog to handle.
 529 |     CLASS C: log + Telegram alert + stop iteration. Let the watchdog decide.
 530 |     """
 531 |     failures = grade_result.get('critical_failures', [])
 532 |     dims = grade_result.get('dimensions', {})
 533 |     failing = [(k, v['score'], v.get('note','')) for k,v in dims.items()
 534 |                if isinstance(v.get('score'), int) and v['score'] < 7]
 535 |     failing.sort(key=lambda x: x[1])
 536 |     grade = grade_result.get('grade', 'F')
 537 |     score = grade_result.get('overall_score', 0)
 538 |     verdict = grade_result.get('verdict', '')
 539 | 
 540 |     # Write fix spec for the watchdog (Qwen) to pick up
 541 |     pf = os.path.join(PIPELINE, f'logs/cc_fix_iter{iteration}.md')
 542 |     spec = (
 543 |         f"# PIPELINE FIX NEEDED - ITERATION {iteration} - GRADE {grade} ({score}/100)\n"
 544 |         f"VERDICT: {verdict}\n"
 545 |         f"CRITICAL FAILURES: {chr(10).join(f'- {f}' for f in failures) or 'None'}\n"
 546 |         f"FAILING DIMS (<7/10): {chr(10).join(f'- {k}: {s}/10 - {n[:80]}' for k,s,n in failing[:8]) or 'None'}\n"
 547 |         f"FIX INSTRUCTIONS: {grade_result.get('targeted_fix_instructions','')}\n"
 548 |     )
 549 |     with open(pf, 'w') as f:
 550 |         f.write(spec)
 551 |     log(f"Fix spec written to {pf} — watchdog will handle repair")
 552 | 
 553 |     # Telegram alert so human/watchdog can decide
 554 |     send_telegram_alert(
 555 |         f"Pulse Check iter {iteration}: Grade {grade} ({score}/100)\n"
 556 |         f"Verdict: {verdict}\n"
 557 |         f"Failing: {', '.join(k for k,s,n in failing[:5])}\n"
 558 |         f"Fix spec: {pf}\n"
 559 |         f"Waiting for watchdog or manual fix."
 560 |     )
 561 | 
 562 |     # Brief pause before next iteration — no CC session spawn
 563 |     time.sleep(30)
 564 | 
 565 | 
 566 | def run_single_render():
 567 |     """Execute one full perfection loop (up to MAX_ITERATIONS). Returns verdict string."""
 568 |     log("="*60)
 569 |     log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
 570 |     log("="*60)
 571 |     # P0 Fix 5: Resume from saved state if available
 572 |     start_iter, start = _load_render_state()
 573 |     grade_result = {}
 574 |     final_verdict = "ERROR"
 575 |     _consecutive_no_output = 0  # audit P1-M3: track render-absent streaks
 576 |     _consecutive_grade_fail = 0  # audit P0-U2: track grade failure streaks
 577 | 
 578 |     for iteration in range(start_iter, MAX_ITERATIONS+1):
 579 |         if (time.time()-start)/3600 >= MAX_HOURS:
 580 |             log(f"TIME LIMIT ({MAX_HOURS}h). Stopping."); break
 581 |         log(f"\n{'='*60}\nITERATION {iteration}/{MAX_ITERATIONS}\n{'='*60}")
 582 |         _save_render_state(iteration, start)  # P0 Fix 5
 583 |         video, rlog = run_render(iteration)
 584 |         if not video:
 585 |             _consecutive_no_output += 1
 586 |             if _consecutive_no_output >= CONSECUTIVE_RENDER_ABSENT_THRESHOLD:
 587 |                 log(f"ABORT: {_consecutive_no_output} consecutive renders produced no output — stopping loop")
 588 |                 send_telegram_alert(
 589 |                     f"PIPELINE ABORT: {_consecutive_no_output} consecutive renders produced no output file. "
 590 |                     f"Iteration {iteration}/{MAX_ITERATIONS}. Manual investigation required."
 591 |                 )
 592 |                 break
 593 |             log("Render failed, skipping"); time.sleep(60); continue
 594 |         _consecutive_no_output = 0  # reset on successful output
 595 |         # Forensics with 10-min hard timeout (task issue #1)
 596 |         forensics = run_forensics(video)
 597 |         # Grade ALWAYS fires after forensics — even if forensics returned {} (task issue main)
 598 |         try:
 599 |             grade_result = grade_with_gemini(video, forensics, rlog)
 600 |         except Exception as _ge:
 601 |             log(f"Grading failed (non-fatal): {_ge}")
 602 |             grade_result = None
 603 |         if not grade_result:
 604 |             _consecutive_grade_fail += 1
 605 |             if _consecutive_grade_fail >= CONSECUTIVE_GRADE_FAILURES_THRESHOLD:
 606 |                 log(f"ABORT: {_consecutive_grade_fail} consecutive grade failures — grading system is broken")
 607 |                 send_telegram_alert(
 608 |                     f"PIPELINE ABORT: {_consecutive_grade_fail} consecutive grade failures. "
 609 |                     f"Gemini grading unavailable. Manual investigation required."
 610 |                 )
 611 |                 break
 612 |             # Fallback: run gemini_grade.py directly as subprocess (task issue #2)
 613 |             log("grade_with_gemini failed — running gemini_grade.py directly")
 614 |             try:
 615 |                 r = subprocess.run(
 616 |                     ["python3", "gemini_grade.py", video],
 617 |                     capture_output=True, text=True, timeout=300, cwd=PIPELINE
 618 |                 )
 619 |                 # Parse both PASS and FAIL lines
 620 |                 if "GRADE_" in (r.stdout or ''):
 621 |                     for line in r.stdout.splitlines():
 622 |                         if line.startswith("GRADE_"):
 623 |                             # Format: GRADE_A_PASS|95|path|verdict or GRADE_B_FAIL|72|path|verdict
 624 |                             parts = line.split("|", 3)  # maxsplit=3 (audit M4)
 625 |                             if len(parts) < 2:
 626 |                                 log(f"Unexpected grade line format: {line!r}")
 627 |                                 continue
 628 |                             grade_tag = parts[0]  # e.g. GRADE_A_PASS
 629 |                             tag_parts = grade_tag.split("_")
 630 |                             grade_letter = tag_parts[1] if len(tag_parts) > 1 else "F"
 631 |                             try:
 632 |                                 score_val = int(parts[1])
 633 |                             except (ValueError, IndexError):
 634 |                                 score_val = 0
 635 |                             grade_result = {
 636 |                                 "grade": grade_letter,
 637 |                                 "overall_score": score_val,
 638 |                                 "broadcast_ready": grade_letter == "A",
 639 |                                 "verdict": parts[3] if len(parts) > 3 else "",
 640 |                                 "dimensions": {},
 641 |                                 "critical_failures": []
 642 |                             }
 643 |                             log(f"Fallback grade: {grade_letter} ({score_val}/100)")
 644 |                             break
 645 |             except Exception as _ge2:
 646 |                 log(f"Fallback grading also failed: {_ge2}")
 647 |             if not grade_result:
 648 |                 log("All grading failed, skipping iteration"); continue
 649 |         _consecutive_grade_fail = 0  # reset on successful grade
 650 |         gf = os.path.join(PIPELINE, f'logs/grade_iter{iteration}.json')
 651 |         with open(gf, 'w') as f: json.dump(grade_result, f, indent=2)
 652 |         grade = grade_result.get('grade','F')
 653 |         score = grade_result.get('overall_score', 0)
 654 |         broadcast = grade_result.get('broadcast_ready', False)
 655 |         # Explicit GRADE: logging after every grade result (task issue #4)
 656 |         log(f"GRADE: {grade} | SCORE: {score}/100 | BROADCAST: {broadcast}")
 657 |         log(f"GRADE: iteration={iteration} grade={grade} score={score} broadcast={broadcast}")
 658 |         log(f"VERDICT: {grade_result.get('verdict','')}")
 659 |         for dim, data in grade_result.get('dimensions',{}).items():
 660 |             s = data.get('score','?')
 661 |             flag = ' ✓' if isinstance(s,int) and s>=8 else (' !!' if isinstance(s,int) and s<6 else '')
 662 |             log(f"  {dim:30s} {s}/10{flag}")
 663 |         if grade == 'A' and broadcast and score >= 88:
 664 |             log("*** GRADE A — LOCKING WINNER RECIPE ***")
 665 |             recipe = {'winner': True, 'iteration': iteration, 'timestamp': datetime.now().isoformat(),
 666 |                      'video': video, 'grade': grade, 'score': score,
 667 |                      'verdict': grade_result.get('verdict'), 'dimensions': grade_result.get('dimensions',{})}
 668 |             with open(RECIPE_FILE, 'w') as f: json.dump(recipe, f, indent=2)
 669 |             log(f"WINNER: {RECIPE_FILE}")
 670 |             final_verdict = "PASS"
 671 |             break
 672 |         elif grade in ('B', 'C') and broadcast:
 673 |             final_verdict = "DEGRADED"
 674 |         log(f"Grade {grade} - firing CC fix...")
 675 |         fire_cc_fix(iteration, grade_result)
 676 |     else:
 677 |         log("Max iterations reached without Grade A")
 678 |         with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
 679 |             json.dump({'final_grade': grade_result}, f, indent=2)
 680 |         if final_verdict == "ERROR":
 681 |             final_verdict = "HOLD"
 682 | 
 683 |     log("OVERNIGHT LOOP COMPLETE")
 684 |     return final_verdict
 685 | 
 686 | 
 687 | def run_cycle():
 688 |     """Run a single render cycle with exception handling and retry logic."""
 689 |     cycle_start = time.time()
 690 | 
 691 |     # Check TTS before render
 692 |     tts_ready, tts_provider = check_tts_ready()
 693 |     log(f"TTS provider: {tts_provider}")
 694 |     if not tts_ready:
 695 |         log(f"[loop] TTS not available ({tts_provider}) — skipping cycle")
 696 |         write_heartbeat("ERROR", time.time() - cycle_start)
 697 |         return
 698 | 
 699 |     for attempt in range(1, MAX_ATTEMPTS_PER_CYCLE + 1):
 700 |         log(f"[loop] Attempt {attempt}/{MAX_ATTEMPTS_PER_CYCLE}")
 701 |         try:
 702 |             verdict = run_single_render()
 703 |         except Exception as e:
 704 |             logger.error(f"[loop] Render cycle exception: {e}", exc_info=True)
 705 |             verdict = "ERROR"
 706 | 
 707 |         if verdict in ("PASS", "DEGRADED"):
 708 |             write_heartbeat(verdict, time.time() - cycle_start)
 709 |             return
 710 | 
 711 |         # Failed — retry logic
 712 |         if attempt < MAX_ATTEMPTS_PER_CYCLE:
 713 |             log(f"[loop] Attempt {attempt} failed ({verdict}), waiting {RETRY_WAIT_SECONDS//60}min before retry...")
 714 |             time.sleep(RETRY_WAIT_SECONDS)
 715 |         else:
 716 |             log(f"[loop] All {MAX_ATTEMPTS_PER_CYCLE} attempts failed — waiting for next scheduled cycle")
 717 | 
 718 |     write_heartbeat(verdict, time.time() - cycle_start)
 719 | 
 720 | 
 721 | # ── Daemon mode ───────────────────────────────────────────────────
 722 | def sleep_until_next_8am_et():
 723 |     """Sleep until next 08:00 ET (12:00 UTC or 11:00 UTC during DST)."""
 724 |     from zoneinfo import ZoneInfo
 725 |     et = ZoneInfo("America/New_York")
 726 |     now = datetime.now(et)
 727 |     target = now.replace(hour=8, minute=0, second=0, microsecond=0)
 728 |     if target <= now:
 729 |         target += timedelta(days=1)
 730 |     wait = (target - now).total_seconds()
 731 |     log(f"[daemon] Sleeping {wait/3600:.1f}h until {target.isoformat()}")
 732 |     time.sleep(wait)
 733 | 
 734 | 
 735 | PIDFILE = os.path.join(BASE, 'logs', 'render_loop.pid')
 736 | RENDER_STATE_FILE = '/tmp/render_state.json'
 737 | 
 738 | 
 739 | def _save_render_state(iteration, start_time):
 740 |     """P0 Fix 5: Persist iteration + start_time across daemon restarts."""
 741 |     try:
 742 |         state = {
 743 |             "iteration": iteration,
 744 |             "start_time": start_time,
 745 |             "saved_at": datetime.now(timezone.utc).isoformat(),
 746 |         }
 747 |         with open(RENDER_STATE_FILE, 'w') as f:
 748 |             json.dump(state, f)
 749 |     except Exception as e:
 750 |         log(f"WARNING: save_render_state failed: {e}")
 751 | 
 752 | 
 753 | def _load_render_state():
 754 |     """P0 Fix 5: Load saved state. Returns (iteration, start_time) or (1, now)."""
 755 |     try:
 756 |         with open(RENDER_STATE_FILE) as f:
 757 |             state = json.load(f)
 758 |         saved_start = state.get("start_time", 0)
 759 |         saved_iter = state.get("iteration", 1)
 760 |         age_hours = (time.time() - saved_start) / 3600
 761 |         if age_hours < MAX_HOURS and saved_iter < MAX_ITERATIONS:
 762 |             log(f"Resuming from saved state: iteration={saved_iter}, age={age_hours:.1f}h")
 763 |             return saved_iter, saved_start
 764 |         else:
 765 |             log(f"Saved state too old ({age_hours:.1f}h) or exhausted (iter={saved_iter}) — starting fresh")
 766 |     except (FileNotFoundError, json.JSONDecodeError, KeyError):
 767 |         pass
 768 |     return 1, time.time()
 769 | 
 770 | 
 771 | def _acquire_singleton():
 772 |     """Prevent duplicate render loop instances. Checks for stale PID (audit UI-4)."""
 773 |     import fcntl
 774 |     # Check for stale PID before locking
 775 |     if os.path.exists(PIDFILE):
 776 |         try:
 777 |             with open(PIDFILE) as f:
 778 |                 old_pid = int(f.read().strip())
 779 |             os.kill(old_pid, 0)  # check if process is alive
 780 |         except (ValueError, ProcessLookupError, PermissionError):
 781 |             # Process is dead — stale lockfile, remove it
 782 |             log(f"Removing stale PID file (pid {old_pid if 'old_pid' in dir() else '?'} not running)")
 783 |             try:
 784 |                 os.remove(PIDFILE)
 785 |             except OSError:
 786 |                 pass
 787 |         except OSError:
 788 |             pass  # Process exists, let flock handle it
 789 | 
 790 |     fp = open(PIDFILE, 'w')
 791 |     try:
 792 |         fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
 793 |     except OSError:
 794 |         log("ABORT: Another render loop instance is already running (pidfile locked)")
 795 |         sys.exit(1)
 796 |     fp.write(str(os.getpid()))
 797 |     fp.flush()
 798 |     # Keep fp open to hold the lock — do NOT close or the lock releases
 799 |     return fp
 800 | 
 801 | 
 802 | def main():
 803 |     parser = argparse.ArgumentParser(
 804 |         description="Protocol Pulse overnight render loop — production hardened",
 805 |         formatter_class=argparse.RawDescriptionHelpFormatter,
 806 |         epilog=(
 807 |             "Examples:\n"
 808 |             "  python3 overnight_render_loop.py              # single cycle\n"
 809 |             "  python3 overnight_render_loop.py --daemon      # continuous, 08:00 ET daily\n"
 810 |             "  python3 overnight_render_loop.py --dry-run     # startup checks only\n"
 811 |         )
 812 |     )
 813 |     parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (loop at 08:00 ET daily)")
 814 |     parser.add_argument("--dry-run", action="store_true", help="Run startup checks only, no render")
 815 |     args = parser.parse_args()
 816 | 
 817 |     # Singleton guard — prevent duplicate instances
 818 |     _lock_fp = _acquire_singleton()
 819 | 
 820 |     # Startup checks always run
 821 |     log("="*60)
 822 |     log("STARTUP CHECKS")
 823 |     log("="*60)
 824 |     if not startup_checks():
 825 |         log("STARTUP CHECKS FAILED — exiting")
 826 |         sys.exit(1)
 827 |     log("All startup checks passed")
 828 | 
 829 |     if args.dry_run:
 830 |         log("--dry-run mode: startup checks passed, exiting")
 831 |         sys.exit(0)
 832 | 
 833 |     # Load existing heartbeat state
 834 |     global _total_episodes, _consecutive_failures
 835 |     try:
 836 |         with open(HEARTBEAT_FILE) as f:
 837 |             hb = json.load(f)
 838 |             _total_episodes = hb.get('total_episodes', 0)
 839 |             _consecutive_failures = hb.get('consecutive_failures', 0)
 840 |         log(f"Heartbeat loaded: episodes={_total_episodes}, consecutive_failures={_consecutive_failures}")
 841 |     except (FileNotFoundError, json.JSONDecodeError):
 842 |         pass
 843 | 
 844 |     if args.daemon:
 845 |         log("DAEMON MODE — will loop at 08:00 ET daily")
 846 |         while True:
 847 |             verdict = run_cycle() or "DEGRADED"
 848 |             if verdict == "PASS":
 849 |                 sleep_until_next_8am_et()
 850 |             else:
 851 |                 log("[daemon] No Grade A — retrying in 30 min")
 852 |                 time.sleep(1800)
 853 |     else:
 854 |         run_cycle()
 855 | 
 856 | 
 857 | if __name__ == '__main__':
 858 |     main()
 859 | 
```

### File: utils/cross_llm_audit.py (887 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | PROTOCOL PULSE — CROSS-LLM CODE AUDIT ENGINE
   4 | Full two-cycle audit: build code → Cycle 1 (3 LLMs) → consensus → Cycle 2 (3 LLMs review each other)
   5 | → final winner determination → second Claude Code pass prompt generated
   6 | 
   7 | Usage:
   8 |     python3 cross_llm_audit.py --feature f1-avatar-oracle
   9 |     python3 cross_llm_audit.py --feature all
  10 |     python3 cross_llm_audit.py --feature f1-avatar-oracle --cycle 2 --cycle1-results /path/to/c1.json
  11 | 
  12 | Requirements in .env:
  13 |     GEMINI_API_KEY=...
  14 |     OPENAI_API_KEY=...
  15 |     XAI_API_KEY=...
  16 |     ANTHROPIC_API_KEY=...
  17 | 
  18 | Created: 2026-03-09
  19 | """
  20 | 
  21 | import os, sys, json, time, threading, argparse, subprocess
  22 | from pathlib import Path
  23 | from datetime import datetime
  24 | 
  25 | # ─── CONFIG ──────────────────────────────────────────────────────────────────
  26 | 
  27 | BASE = Path.home() / "protocol_pulse"
  28 | GOSPELS = BASE / "docs/gospels"
  29 | AUDITS  = BASE / "docs/audits"
  30 | AUDITS.mkdir(parents=True, exist_ok=True)
  31 | 
  32 | FEATURE_MAP = {
  33 |     "fix-freeze-frames": ("PIPELINE_LAWS.md", "main"),
  34 |     "fix-silence-gaps":  ("PIPELINE_LAWS.md", "main"),
  35 |     "fix-social-spacetap":  ("PIPELINE_LAWS.md", "main"),
  36 |     "fix-pip-left-panel":    ("VISUAL_DESIGN_SYSTEM.md", "main"),
  37 |     "fix-grading-loop":      ("PIPELINE_LAWS.md", "main"),
  38 |     "fix-elevenlabs-voice":  ("PIPELINE_LAWS.md", "main"),
  39 |     "f1-avatar-oracle":  ("F1_AVATAR_ORACLE_GOSPEL.md",  "feature/f1-avatar-oracle"),
  40 |     "f2-briefing-room":  ("F2_BRIEFING_ROOM_GOSPEL.md",  "feature/f2-briefing-room"),
  41 |     "f3-schiff-bot":     ("F3_SCHIFF_BOT_GOSPEL.md",     "feature/f3-schiff-bot"),
  42 |     "f4-nostr":          ("F4_NOSTR_GOSPEL.md",          "feature/f4-nostr"),
  43 |     "f5-node-watch":     ("F5_NODE_WATCH_GOSPEL.md",     "feature/f5-node-watch"),
  44 |     "f6-marketing-os":   ("F6_MARKETING_OS_GOSPEL.md",   "feature/f6-marketing-os"),
  45 |     "v30-terminal-api":  ("V30_TERMINAL_API_GOSPEL.md",  "feature/v30-terminal-api"),
  46 |     "b1-newsletter":     ("B1_NEWSLETTER_GOSPEL.md",     "feature/b1-newsletter"),
  47 |     "v22-multi-format":  ("V22_MULTI_FORMAT_GOSPEL.md",  "feature/v22-multi-format"),
  48 |     "video-audio-fix":   ("VIDEO_AUDIO_FIX_GOSPEL.md",   "feature/video-audio-fix"),
  49 |     "assembler-v2-rebuild": ("ASSEMBLER_V2_GOSPEL.md", "main"),
  50 |     "x-spaces-pipeline": ("X_SPACES_PIPELINE_GOSPEL.md", "main"),
  51 |     "f6-price-alerts":  ("F6_PRICE_ALERTS_GOSPEL.md",   "feature/f6-price-alerts"),
  52 |     "f8-sponsor-agent": ("P3_SPONSOR_AGENT_GOSPEL.md",  "feature/f8-sponsor-agent"),
  53 |     "f4-cron-heygen":   ("F4_CRON_HEYGEN_GOSPEL.md",   "feature/f4-cron-heygen"),
  54 |     "stripe_commander": ("F1_STRIPE_COMMANDER_GOSPEL.md", "feature/f1-stripe-commander"),
  55 |     "article_page_laws": ("ARTICLE_PAGE_LAWS.md", "feature/f2-article-laws"),
  56 |     "tts-pipeline": ("TTS_PIPELINE_AUDIT_GOSPEL.md", "feature/tts-pipeline"),
  57 |     "oracle-stage": ("ORACLE_STAGE_GOSPEL.md", "main"),
  58 |     "stage-broadcast": ("STAGE_BROADCAST_GOSPEL.md", "main"),
  59 |     "pipeline-day3-audit": ("WATCHDOG_LLM_GOSPEL.md", "main"),
  60 |     "watchdog-cc-healing": ("WATCHDOG_LLM_GOSPEL.md", "main"),
  61 |     "commander-product-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
  62 |     "pipeline-comprehensive-audit": ("PIPELINE_LAWS.md", "main"),
  63 |     "intelligence-terminal": ("VISUAL_DESIGN_SYSTEM.md", "main"),
  64 |     "convergence-detection": ("VISUAL_DESIGN_SYSTEM.md", "main"),
  65 |     "convergence-build-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
  66 |     "ml-session-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
  67 |     "render-improvement-loop": ("RENDER_IMPROVEMENT_LOOP_GOSPEL.md", "main"),
  68 | }
  69 | 
  70 | # Explicit file lists for features already merged to main (no branch diff available)
  71 | EXPLICIT_FILES = {
  72 |     "fix-freeze-frames": ["video_pipeline_v3/assembler.py"],
  73 |     "fix-silence-gaps":  ["video_pipeline_v3/tts_engine.py"],
  74 |     "x-spaces-pipeline": ["x_spaces_scraper/scraper.py","x_spaces_scraper/transcript_fetcher.py","x_spaces_scraper/whisper_worker.py","x_spaces_scraper/diarizer.py","x_spaces_scraper/spaces_state.py","x_spaces_scraper/run_scraper.py","x_spaces_scraper/article_generator.py","x_spaces_pipeline/monitor.py","x_spaces_pipeline/recorder.py","x_spaces_pipeline/transcriber.py","x_spaces_pipeline/curator.py","video_pipeline_v3/utils/spaces_pipeline.py","video_pipeline_v3/utils/spaces_monitor.py","video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py"],
  75 |     "assembler-v2-rebuild": [
  76 |         "video_pipeline_v3/assembler_v2/constants.py",
  77 |         "video_pipeline_v3/assembler_v2/helpers.py",
  78 |         "video_pipeline_v3/assembler_v2/manifest.py",
  79 |         "video_pipeline_v3/assembler_v2/state.py",
  80 |         "video_pipeline_v3/assembler_v2/preflight.py",
  81 |         "video_pipeline_v3/assembler_v2/ffmpeg_core/encode.py",
  82 |         "video_pipeline_v3/assembler_v2/ffmpeg_core/filters.py",
  83 |         "video_pipeline_v3/assembler_v2/ffmpeg_core/probe.py",
  84 |         "video_pipeline_v3/assembler_v2/segments/base.py",
  85 |         "video_pipeline_v3/assembler_v2/segments/transition.py",
  86 |         "video_pipeline_v3/assembler_v2/segments/wrap.py",
  87 |         "video_pipeline_v3/assembler_v2/segments/cold_open.py",
  88 |         "video_pipeline_v3/assembler_v2/segments/narration.py",
  89 |         "video_pipeline_v3/assembler_v2/segments/partner_clip.py",
  90 |         "video_pipeline_v3/assembler_v2/segments/data_segment.py",
  91 |         "video_pipeline_v3/assembler_v2/segments/social.py",
  92 |         "video_pipeline_v3/assembler_v2/segments/signal_active.py",
  93 |         "video_pipeline_v3/assembler_v2/episode.py",
  94 |         "video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py",
  95 |         "video_pipeline_v3/utils/spaces_pipeline.py",
  96 |         "video_pipeline_v3/utils/spaces_monitor.py",
  97 |     ],
  98 |     "fix-pip-left-panel": ["video_pipeline_v3/assembler.py"],
  99 |     "fix-social-spacetap": [
 100 |         "video_pipeline_v3/daily_producer.py",
 101 |         "video_pipeline_v3/script_writer.py",
 102 |         "video_pipeline_v3/utils/social_fetcher.py",
 103 |     ],
 104 |     "fix-grading-loop": ["overnight_render_loop.py", "video_pipeline_v3/gemini_grade.py"],
 105 |     "stage-broadcast": ["services/stage_broadcast_service.py","core/routes.py","templates/stage.html"],
 106 |     "oracle-stage": [
 107 |         "templates/stage.html",
 108 |         "routes.py",
 109 |     ],
 110 |     "pipeline-day3-audit": [
 111 |         "video_pipeline_v3/script_writer.py",
 112 |         "video_pipeline_v3/tts_engine.py",
 113 |         "overnight_render_loop.py",
 114 |         "services/local_watchdog.py",
 115 |         "video_pipeline_v3/clip_selector.py",
 116 |         "video_pipeline_v3/clip_extractor.py",
 117 |         "services/montage_producer.py",
 118 |     ],
 119 |     "watchdog-cc-healing": ["services/local_watchdog.py"],
 120 |     "pipeline-comprehensive-audit": [
 121 |         "overnight_render_loop.py",
 122 |         "video_pipeline_v3/daily_producer.py",
 123 |         "video_pipeline_v3/script_writer.py",
 124 |         "video_pipeline_v3/tts_engine.py",
 125 |         "video_pipeline_v3/assembler.py",
 126 |         "services/local_watchdog.py",
 127 |     ],
 128 |     "commander-product-audit": [
 129 |         "docs/cc_commander_premium.md",
 130 |         "templates/commander_dashboard.html",
 131 |     ],
 132 |     "intelligence-terminal": [
 133 |         "docs/VISUAL_DESIGN_SYSTEM.md",
 134 |         "services/morning_brief.py",
 135 |         "video_pipeline_v3/daily_producer.py",
 136 |     ],
 137 |     "convergence-detection": [
 138 |         "docs/phase2/convergence_detection_foundation.md",
 139 |         "docs/intelligence_terminal_v1_spec.md",
 140 |         "services/sentinel.py",
 141 |         "core/blueprints/intelligence.py",
 142 |         "core/templates/intelligence_terminal.html",
 143 |     ],
 144 |     "convergence-build-audit": [
 145 |         "docs/phase2/convergence_detection_v1_spec.md",
 146 |         "services/sentinel.py",
 147 |         "core/blueprints/intelligence.py",
 148 |         "core/app.py",
 149 |         "core/templates/intelligence_terminal.html",
 150 |     ],
 151 |     "ml-session-audit": [
 152 |         "docs/cc_ml_session.md",
 153 |         "docs/phase_ml/pcaf_v1_foundation.md",
 154 |         "docs/phase_ml/tpa_foundation.md",
 155 |         "services/sentinel.py",
 156 |         "core/blueprints/intelligence.py",
 157 |     ],
 158 |     "render-improvement-loop": [
 159 |         "overnight_render_loop.py",
 160 |         "utils/cross_llm_audit.py",
 161 |         "video_pipeline_v3/assembler.py",
 162 |         "video_pipeline_v3/clip_extractor.py",
 163 |     ],
 164 | }
 165 | 
 166 | # For large files, extract only relevant route functions instead of the whole file.
 167 | # Key: (feature_name, filename) → list of route prefixes to extract
 168 | ROUTE_EXTRACTS = {
 169 |     ("oracle-stage", "routes.py"): ["/stage", "/api/stage/", "/api/oracle/"],
 170 | }
 171 | 
 172 | CUSTOM_REVIEW_TASKS = {
 173 |     "render-improvement-loop": """

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
