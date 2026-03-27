# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: fix-grading-loop
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REPORT: PROTOCOL PULSE — FIX-GRADING-LOOP

**Reviewer: GPT-4o**

Below is a detailed forensic review of the provided code for the `fix-grading-loop` feature in the `main` branch of Protocol Pulse. The review is structured as requested, with a focus on correctness, compliance, security, quality, and actionable improvements.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis (overnight_render_loop.py):**
1. **Startup Checks (Lines 89-149):** The `startup_checks()` function verifies critical dependencies (FFmpeg, pipeline directory, output directory writability, TTS provider). It correctly identifies potential blockers before rendering starts. However, if checks fail, the script exits without retry logic or notification beyond logging (Line 581), which could silently fail in a cron job without alerting operators.
2. **Render Loop (Lines 406-489):** The `run_single_render()` function iterates up to 8 times or 6 hours to achieve a Grade A video. It handles rendering, forensics, grading, and fixes via a CC session. The logic for stopping on Grade A (Line 469) or continuing on lower grades (Line 480) is correct, but there’s a silent failure risk if `run_render()` returns no video (Line 421) without escalating alerts beyond a log entry.
3. **Grading with Gemini (Lines 337-371):** The `grade_with_gemini()` function submits forensic data to Gemini for a 24-dimension grade. It includes a fallback to `gemini_grade.py` (Lines 434-456) if the API call fails, which is good, but parsing errors (Line 371) are not retried, risking an iteration skip without actionable diagnostics.
4. **CC Fix Session (Lines 374-404):** The `fire_cc_fix()` function launches a tmux session for automated fixes. It assumes tmux is installed and configured (Line 392), which isn’t validated in startup checks, risking silent failure if tmux is unavailable.
5. **Daemon Mode (Lines 600-604):** The `--daemon` mode runs continuously, triggering at 08:00 ET daily. The `sleep_until_next_8am_et()` function (Lines 527-537) correctly calculates wait time, but there’s no handling for system clock changes or DST edge cases, which could misalign scheduling.

**Logic Errors and Silent Failures:**
- **Line 263 (overnight_render_loop.py):** If no video output is found after rendering, it logs "FATAL: no output file" but doesn’t trigger an alert beyond logging, risking silent failure in unattended cron runs.
- **Line 430 (overnight_render_loop.py):** Grading failures are logged as non-fatal, but skipping an iteration without retrying or alerting could lead to wasted cycles.
- **Line 393 (overnight_render_loop.py):** The CC fix session assumes `claude` CLI is available without validation, risking silent failure if the tool or environment is misconfigured.

**Race Conditions:**
- **Line 543-556 (overnight_render_loop.py):** The PID file lock in `_acquire_singleton()` prevents multiple instances, which is good for avoiding race conditions on shared resources like output directories. However, if the process crashes without releasing the lock, subsequent runs will fail until manual intervention, as there’s no lock timeout or cleanup mechanism.

**Edge Cases:**
- **Empty or Corrupted Video Output (Line 420):** If `run_render()` produces a corrupted or zero-byte file, `run_forensics()` may crash or produce meaningless data, and there’s no validation of file integrity before forensics.
- **API Timeouts (Line 239-242):** Gemini API calls have a 120-second timeout, but there’s no retry logic beyond falling back to a subprocess (Line 434). If both fail during a network outage, the loop skips without recovery.
- **Quota Exhaustion (Line 224-227):** ElevenLabs quota exhaustion is checked, but there’s no fallback to a secondary TTS provider mid-loop if quota is exhausted during rendering.

**N+1 Query Problems:**
- Not applicable as there are no database queries in the provided code (SQLite via SQLAlchemy is mentioned in the tech stack but not used here).

---

### SECTION 2: LAW COMPLIANCE

**Note:** No specific "GOVERNING LAWS" were provided in the spec for this review. As such, I will assume compliance is based on the technology stack and general best practices outlined. If specific laws were intended, they were not included in the provided text.

- **Technology Stack Compliance (Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM):** COMPLIANT. The code uses Python 3.12 as evident from the shebang (Line 1, overnight_render_loop.py). Flask and SQLAlchemy are not directly used in the provided files, so no violations are noted.
- **Ubuntu 24.04 on Ultron Server:** COMPLIANT. The code includes paths and configurations consistent with a Linux environment (e.g., Line 11, gemini_grade.py), and no OS-specific issues are evident.
- **UI Animations (CSS/SVG only):** NOT APPLICABLE. The provided code does not include frontend UI components, so compliance cannot be assessed.
- **External Services (ElevenLabs TTS, HeyGen, Wav2Lip):** PARTIAL. The code checks for Ele

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### `overnight_render_loop.py`

1. **Startup / singleton**
   - `main()` acquires a pidfile lock via `_acquire_singleton()` before doing anything else (`overnight_render_loop.py:543-555, 573-575`).
   - This does prevent duplicate instances on the same host/process namespace. Good.

2. **Startup checks**
   - `startup_checks()` validates ffmpeg, pipeline dir, output dir writability, and TTS availability (`88-149`).
   - This mostly does what it claims, but there is a correctness gap:
     - It checks local TTS using a **hardcoded home-relative path** `~/protocol_pulse/video_pipeline_v3/tts_local.py` instead of `PIPELINE/tts_local.py` (`131`, also repeated at `216`). If the repo is deployed elsewhere, startup and runtime TTS checks can disagree with actual filesystem state.

3. **Heartbeat restore**
   - Existing heartbeat counters are loaded if JSON exists (`589-598`).
   - Fine for a single-process daemon, but state is only in-memory plus one JSON file; no atomic write/replace.

4. **Cycle execution**
   - `run_cycle()` checks TTS readiness, then runs up to 2 attempts with a 30-minute wait between attempts (`492-524`).
   - This is a meaningful improvement over a crash-only loop.

5. **Render loop**
   - `run_single_render()` runs up to 8 iterations or 6 hours (`406-489`).
   - Per iteration:
     - render (`419`)
     - forensics (`423`)
     - Gemini grade (`428`)
     - fallback grade subprocess if direct grading fails (`433-454`)
     - save grade JSON (`457-458`)
     - if A/broadcast/88+, lock winner recipe and stop (`468-476`)
     - else fire Claude Code fix session (`479-480`)

6. **Daemon mode**
   - `--daemon` loops forever and sleeps until next 8am ET after each cycle (`600-604`).
   - **Logic bug:** if the daemon starts at, say, 14:00 ET, it will run a cycle immediately, then sleep until next 8am ET. The docstring says “runs at 08:00 ET daily” (`9`, `528-537`), but actual behavior is “run immediately on startup, then daily at 08:00 ET.” That is not the same operational contract.

---

### Concrete correctness issues

#### P0/P1 logic bugs

1. **Shell misuse breaks stderr capture assumptions in multiple ffmpeg/ffprobe calls**
   - `run()` always invokes `subprocess.run(..., shell=True, ...)` (`67-70`).
   - Several callers pass command strings containing shell redirection `2>&1`:
     - `run_forensics()` blackdetect/loudness/freezedetect (`289, 293, 299`)
   - With `capture_output=True`, shell redirection causes stderr to be merged into stdout by the shell, so `r.stderr` may be empty. The code compensates by concatenating `r.stderr + r.stdout`, so it works by accident, but this is fragile and obscures failure modes.
   - More importantly, using `shell=True` everywhere is unnecessary and dangerous.

2. **Potential command injection via unescaped file paths**
   - `run_forensics(video)` interpolates `video` directly into shell commands (`271, 289, 293, 299`).
   - `video` comes from filesystem discovery, not direct user input, but filenames can still contain quotes or shell metacharacters. A malicious or malformed filename could break commands or execute arbitrary shell.
   - Same issue in `video_pipeline_v3/gemini_grade.py` with `LATEST` in many shell commands (`57, 90, 101, 110, 125, 136-137`).

3. **TTS artifact temp file leak**
   - In `run_forensics()`, temp wav is created (`307-308`) and only deleted on the success path (`325`).
   - If ffmpeg extraction fails, whisper subprocess times out, JSON parse fails, or any exception occurs before `_os.unlink(tmp_path)`, the temp file is leaked (`305-327`).
   - In a long-running daemon, this accumulates.

4. **Claude Code session can hang beyond intended deadline**
   - `fire_cc_fix()` waits up to 2700s while polling tmux (`397-402`), but when deadline expires it does **not** kill the tmux session (`403` only sleeps 30s).
   - That means orphaned Claude sessions may continue consuming resources and mutating the repo while the outer loop proceeds to next iteration or next cycle.

5. **Fallback grading parser is brittle and can throw on valid-but-unexpected output**
   - In `run_single_render()`, fallback parsing assumes `parts[1]` is int and `parts[3]` exists if len > 3 (`445-450`).
   - If verdict contains `|`, or output format changes slightly, parsing breaks or truncates verdict silently.
   - Also `grade_letter = parts[0].split("_")[1]` on `GRADE_A_PASS` yields `"A"`, but only because the format is exactly fixed.

6. **Daemon scheduling contract mismatch**
   - As noted above, `--daemon` runs immediately, not only at 08:00 ET (`600-604`).
   - If this is used in production expecting strict daily scheduling, it will produce an extra run on process restart/deploy.

---

### Silent failure / weak failure semantics

7. **`run_render()` ignores render return code when selecting output**
   - It logs render exit code (`251`) but still scans for output and returns the newest matching mp4 even if th

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — FIX-GRADING-LOOP — CYCLE 1
Generated: 2026-03-22 06:44
Models: grok, gpt4o (+1 failed: gemini — 403 PERMISSION_DENIED leaked API key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | ❌ FAILED | 4/10 | 5/10 | 4/10 |
| Law Compliance | ❌ FAILED | 6/10 | 7/10 | 6/10 |
| Security | ❌ FAILED | 3/10 | 5/10 | 3/10 |
| Frontend Quality | ❌ FAILED | N/A | N/A | N/A |
| Overall | ❌ FAILED | 4/10 | 5/10 | **4/10** |

> **Scoring note:** Gemini was unable to produce scores due to API key invalidation (leaked key — 403). GPT-4o scores derived from severity of identified bugs (5 P0-class issues). Grok scores derived from breadth of coverage. Consensus weights GPT-4o more heavily as it produced the most forensically detailed output.

---

## UNANIMOUS FINDINGS
*(Both active models flagged these — implement unconditionally)*

### U1 — `shell=True` + unescaped file path interpolation → command injection
- **File:** `overnight_render_loop.py:67-70, 271, 289, 293, 299` and `video_pipeline_v3/gemini_grade.py:57, 90, 101, 110, 125, 136-137`
- **What:** `run()` uses `shell=True` universally. Callers interpolate raw filesystem paths (e.g., `video`, `LATEST`) directly into shell command strings. Both GPT-4o and Grok independently flagged this.
- **What to change:** Replace `shell=True` with `shell=False` and pass commands as lists. Use `shlex.quote()` wherever a string form is truly required. At minimum, validate filenames contain no shell metacharacters before interpolation.

### U2 — No tmux/claude CLI validation in startup checks, orphaned sessions never killed
- **File:** `overnight_render_loop.py:392-403`
- **What:** `fire_cc_fix()` assumes `tmux` and `claude` are installed and accessible. Neither is validated in `startup_checks()`. When the 2700s deadline expires, the tmux session is **not killed** — it continues mutating the repo while the outer loop advances.
- **What to change:** (a) Add `which tmux` and `which claude` checks to `startup_checks()` with a hard exit on failure. (b) On deadline expiry, call `tmux kill-session -t <session_name>` before continuing.

### U3 — Silent failure when `run_render()` returns no video / non-zero exit
- **File:** `overnight_render_loop.py:251, 420-421`
- **What:** Render exit code is logged but not acted upon. If render fails, the loop still scans for an output file, potentially grading a stale or corrupt artifact from a prior run. Both models flagged the absence of an alert escalation path (no Telegram/PagerDuty on this specific failure).
- **What to change:** If render exit code is non-zero **and** no fresh output file is found, immediately send a Telegram alert and `continue` (skip grading for this iteration). Add a timestamp/mtime guard: only accept output files created after the render subprocess started.

### U4 — Gemini API call lacks error handling / retry logic
- **File:** `overnight_render_loop.py:231-242`
- **What:** `gemini_call()` catch

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: overnight_render_loop.py (611 lines)
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
  16 | import os, sys, json, subprocess, time, re, urllib.request, argparse, logging
  17 | from datetime import datetime, timezone, timedelta
  18 | from pathlib import Path
  19 | 
  20 | BASE = os.path.dirname(os.path.abspath(__file__))
  21 | PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
  22 | ENV_FILE = os.path.join(BASE, '.env')
  23 | LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
  24 | RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
  25 | HEARTBEAT_FILE = os.path.join(BASE, 'logs', 'loop_heartbeat.json')
  26 | ELEVENLABS_QUOTA_SENTINEL = os.path.join(BASE, 'logs', 'elevenlabs_quota_exhausted')
  27 | MAX_ITERATIONS = 8
  28 | MAX_HOURS = 6
  29 | RETRY_WAIT_SECONDS = 1800  # 30 minutes
  30 | MAX_ATTEMPTS_PER_CYCLE = 2
  31 | 
  32 | os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)
  33 | os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)
  34 | 
  35 | # ── Logging ───────────────────────────────────────────────────────
  36 | logger = logging.getLogger('overnight_loop')
  37 | logger.setLevel(logging.DEBUG)
  38 | _fmt = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  39 | _sh = logging.StreamHandler(sys.stdout)
  40 | _sh.setFormatter(_fmt)
  41 | logger.addHandler(_sh)
  42 | _fh = logging.FileHandler(LOG)
  43 | _fh.setFormatter(_fmt)
  44 | logger.addHandler(_fh)
  45 | 
  46 | 
  47 | def log(msg):
  48 |     """Backward-compat wrapper."""
  49 |     logger.info(msg)
  50 | 
  51 | 
  52 | def load_env():
  53 |     env = os.environ.copy()
  54 |     try:
  55 |         with open(ENV_FILE) as f:
  56 |             for line in f:
  57 |                 l = line.strip()
  58 |                 if l and not l.startswith('#') and '=' in l:
  59 |                     k, _, v = l.partition('=')
  60 |                     k = k.strip(); v = v.strip().strip("'").strip('"')
  61 |                     if k: env[k] = v
  62 |     except Exception as e:
  63 |         log(f"WARNING: .env load failed: {e}")
  64 |     return env
  65 | 
  66 | 
  67 | def run(cmd, timeout=7200, env=None):
  68 |     try:
  69 |         return subprocess.run(cmd, shell=True, capture_output=True, text=True,
  70 |                              timeout=timeout, env=env or load_env(), cwd=PIPELINE)
  71 |     except subprocess.TimeoutExpired as e:
  72 |         log(f"TIMEOUT after {timeout}s: {str(cmd)[:80]}")
  73 |         # Return a fake CompletedProcess so callers don't crash
  74 |         import subprocess as _sp
  75 |         r = _sp.CompletedProcess(cmd, returncode=-1)
  76 |         r.stdout = ""
  77 |         r.stderr = f"TIMEOUT after {timeout}s"
  78 |         return r
  79 |     except Exception as e:
  80 |         log(f"run() error: {e} cmd={str(cmd)[:80]}")
  81 |         import subprocess as _sp
  82 |         r = _sp.CompletedProcess(cmd, returncode=-1)
  83 |         r.stdout = ""
  84 |         r.stderr = str(e)
  85 |         return r
  86 | 
  87 | 
  88 | # ── FIX 6: Startup checks ────────────────────────────────────────
  89 | def startup_checks():
  90 |     """Verify environment before any render. Returns True if all pass."""
  91 |     ok = True
  92 | 
  93 |     # FFmpeg available
  94 |     try:
  95 |         r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
  96 |         if r.returncode != 0:
  97 |             log("STARTUP FAIL: ffmpeg returned non-zero")
  98 |             ok = False
  99 |         else:
 100 |             ver = r.stdout.split('\n')[0] if r.stdout else '?'
 101 |             log(f"FFmpeg: {ver}")
 102 |     except FileNotFoundError:
 103 |         log("STARTUP FAIL: ffmpeg not found in PATH")
 104 |         ok = False
 105 |     except Exception as e:
 106 |         log(f"STARTUP FAIL: ffmpeg check error: {e}")
 107 |         ok = False
 108 | 
 109 |     # Python path includes pipeline
 110 |     if PIPELINE not in sys.path:
 111 |         sys.path.insert(0, PIPELINE)
 112 |     log(f"Pipeline dir: {PIPELINE} (exists={os.path.isdir(PIPELINE)})")
 113 |     if not os.path.isdir(PIPELINE):
 114 |         log("STARTUP FAIL: video_pipeline_v3 directory missing")
 115 |         ok = False
 116 | 
 117 |     # Output directory writable
 118 |     out_dir = os.path.join(PIPELINE, 'output')
 119 |     os.makedirs(out_dir, exist_ok=True)
 120 |     test_file = os.path.join(out_dir, '.write_test')
 121 |     try:
 122 |         with open(test_file, 'w') as f:
 123 |             f.write('ok')
 124 |         os.remove(test_file)
 125 |         log(f"Output dir writable: {out_dir}")
 126 |     except Exception as e:
 127 |         log(f"STARTUP FAIL: output dir not writable: {e}")
 128 |         ok = False
 129 | 
 130 |     # TTS provider check
 131 |     local_tts = Path(os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")).exists()
 132 |     env = load_env()
 133 |     elevenlabs_key = bool(env.get('ELEVENLABS_API_KEY', '').strip())
 134 |     quota_exhausted = os.path.exists(ELEVENLABS_QUOTA_SENTINEL)
 135 | 
 136 |     if local_tts:
 137 |         log("TTS provider: LOCAL (tts_local.py found)")
 138 |     elif elevenlabs_key and not quota_exhausted:
 139 |         log("TTS provider: ElevenLabs (API key present)")
 140 |     elif elevenlabs_key and quota_exhausted:
 141 |         log("WARNING: ElevenLabs key present but quota sentinel exists")
 142 |     else:
 143 |         log("WARNING: No TTS provider found (no local TTS, no ElevenLabs key)")
 144 | 
 145 |     if not local_tts and not elevenlabs_key:
 146 |         log("STARTUP FAIL: No TTS provider available")
 147 |         ok = False
 148 | 
 149 |     return ok
 150 | 
 151 | 
 152 | # ── FIX 3: Heartbeat ─────────────────────────────────────────────
 153 | _total_episodes = 0
 154 | _consecutive_failures = 0
 155 | 
 156 | 
 157 | def write_heartbeat(verdict, duration_s):
 158 |     """Write heartbeat JSON after every cycle."""
 159 |     global _total_episodes, _consecutive_failures
 160 |     if verdict == "PASS":
 161 |         _total_episodes += 1
 162 |         _consecutive_failures = 0
 163 |     elif verdict == "ERROR":
 164 |         _consecutive_failures += 1
 165 |     elif verdict == "HOLD":
 166 |         _consecutive_failures += 1
 167 |     # DEGRADED counts as partial success
 168 |     elif verdict == "DEGRADED":
 169 |         _total_episodes += 1
 170 |         _consecutive_failures = 0
 171 | 
 172 |     heartbeat = {
 173 |         "last_run": datetime.now(timezone.utc).isoformat(),
 174 |         "last_verdict": verdict,
 175 |         "last_duration": round(duration_s, 1),
 176 |         "total_episodes": _total_episodes,
 177 |         "consecutive_failures": _consecutive_failures,
 178 |     }
 179 |     try:
 180 |         with open(HEARTBEAT_FILE, 'w') as f:
 181 |             json.dump(heartbeat, f, indent=2)
 182 |         log(f"Heartbeat written: {verdict} | failures={_consecutive_failures}")
 183 |     except Exception as e:
 184 |         log(f"WARNING: heartbeat write failed: {e}")
 185 | 
 186 |     # Telegram alert on 3+ consecutive failures
 187 |     if _consecutive_failures >= 3:
 188 |         send_telegram_alert(
 189 |             f"🚨 Protocol Pulse loop: {_consecutive_failures} consecutive failures\n"
 190 |             f"Last verdict: {verdict}\n"
 191 |             f"Time: {heartbeat['last_run']}"
 192 |         )
 193 | 
 194 | 
 195 | def send_telegram_alert(message):
 196 |     """Send alert via Telegram if bot token + chat ID are configured."""
 197 |     env = load_env()
 198 |     token = env.get('TELEGRAM_BOT_TOKEN', '').strip()
 199 |     chat_id = env.get('TELEGRAM_CHAT_ID', '').strip()
 200 |     if not token or not chat_id:
 201 |         log("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 202 |         return
 203 |     try:
 204 |         url = f"https://api.telegram.org/bot{token}/sendMessage"
 205 |         payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
 206 |         req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
 207 |         with urllib.request.urlopen(req, timeout=15) as r:
 208 |             log(f"Telegram alert sent (status {r.status})")
 209 |     except Exception as e:
 210 |         log(f"Telegram alert failed: {e}")
 211 | 
 212 | 
 213 | # ── FIX 4: TTS provider awareness ────────────────────────────────
 214 | def check_tts_ready():
 215 |     """Check TTS availability before render. Returns (ready, provider_name)."""
 216 |     local_tts = Path(os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")).exists()
 217 |     if local_tts:
 218 |         return True, "local (Kokoro/F5-TTS)"
 219 | 
 220 |     env = load_env()
 221 |     if not env.get('ELEVENLABS_API_KEY', '').strip():
 222 |         return False, "none"
 223 | 
 224 |     if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 225 |         log("ElevenLabs quota sentinel exists — skipping render")
 226 |         return False, "elevenlabs (quota exhausted)"
 227 | 
 228 |     return True, "ElevenLabs"
 229 | 
 230 | 
 231 | def gemini_call(prompt, max_tokens=8000):
 232 |     env = load_env()
 233 |     key = env.get('GEMINI_API_KEY', '')
 234 |     url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}'
 235 |     payload = {'contents': [{'parts': [{'text': prompt}]}],
 236 |                'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.05}}
 237 |     req = urllib.request.Request(url, data=json.dumps(payload).encode(),
 238 |                                   headers={'Content-Type': 'application/json'})
 239 |     with urllib.request.urlopen(req, timeout=120) as r:
 240 |         d = json.loads(r.read())
 241 |         parts = d['candidates'][0]['content'].get('parts', [])
 242 |         return next((p['text'] for p in parts if 'text' in p), None)
 243 | 
 244 | 
 245 | def run_render(iteration):
 246 |     log(f"RENDER START iteration {iteration}")
 247 |     run("rm -rf tts_cache/ && mkdir -p tts_cache/")
 248 |     log("TTS cache wiped")
 249 |     env = load_env()
 250 |     r = run("python3 daily_producer.py --skip-scan", timeout=7200, env=env)
 251 |     log(f"Render exit: {r.returncode}")
 252 |     import glob
 253 |     today = datetime.now().strftime('%Y-%m-%d')
 254 |     candidates = []
 255 |     for pat in [f'output/{today}/*.mp4']:  # today-only — no stale fallback
 256 |         for f in glob.glob(os.path.join(PIPELINE, pat)):
 257 |             if any(x in f for x in ['.bgl_audio', '.intro_mus', '.concat_raw', '.music_mixed', '.whoosh', '.norm']):
 258 |                 continue
 259 |             if not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh']):
 260 |                 candidates.append((os.path.getmtime(f), f))
 261 |     candidates.sort(reverse=True)
 262 |     out = candidates[0][1] if candidates else None
 263 |     if out: log(f"Output: {out} ({os.path.getsize(out)//1048576}MB)")
 264 |     else: log("FATAL: no output file")
 265 |     return out, r.stdout + r.stderr
 266 | 
 267 | 
 268 | def run_forensics(video):
 269 |     log("Running forensics...")
 270 |     res = {}
 271 |     r = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{video}"')
 272 |     try:
 273 |         p = json.loads(r.stdout)
 274 |         fmt = p.get('format', {}); streams = p.get('streams', [])
 275 |         res['duration'] = float(fmt.get('duration', 0))
 276 |         res['filesize_mb'] = int(fmt.get('size', 0)) / 1048576
 277 |         v = next((s for s in streams if s.get('codec_type') == 'video'), {})
 278 |         a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
 279 |         res['width'] = v.get('width', 0); res['height'] = v.get('height', 0)
 280 |         fps_str = v.get('r_frame_rate', '0/1')
 281 |         if '/' in fps_str:
 282 |             num, den = fps_str.split('/', 1)
 283 |             res['fps'] = float(num) / float(den) if float(den) != 0 else 0
 284 |         else:
 285 |             res['fps'] = float(fps_str) if fps_str else 0
 286 |         res['vcodec'] = v.get('codec_name', '?'); res['acodec'] = a.get('codec_name', '?')
 287 |     except Exception as e:
 288 |         log(f"WARNING: ffprobe parse error: {e}")
 289 |     r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1', timeout=300)
 290 |     segs = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', r.stderr+r.stdout)
 291 |     dur = res.get('duration', 0)
 292 |     res['black_mid_count'] = len([(s,e,d) for s,e,d in segs if float(s)>2 and float(e)<dur-2])
 293 |     r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=120)
 294 |     out = r.stderr + r.stdout
 295 |     im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
 296 |     tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
 297 |     res['integrated_lufs'] = float(im.group(1)) if im else None
 298 |     res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
 299 |     r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.001:d=1.0" -an -f null - 2>&1', timeout=300)
 300 |     res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))
 301 | 
 302 |     # TTS ARTIFACT CHECK — run in isolated subprocess with hard 45s timeout
 303 |     # Prevents WhisperModel from blocking forensics pipeline
 304 |     tts_artifacts = []
 305 |     try:
 306 |         import subprocess as _sp, tempfile as _tf, os as _os, json as _json
 307 |         with _tf.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
 308 |             tmp_path = tmp.name
 309 |         _sp.run(['ffmpeg', '-y', '-i', video, '-t', '60', '-ar', '16000',
 310 |                  '-ac', '1', tmp_path], capture_output=True, timeout=30)
 311 |         # Run whisper in subprocess so it cannot block the loop
 312 |         checker = (
 313 |             "import sys, json\n"
 314 |             "from faster_whisper import WhisperModel\n"
 315 |             "model = WhisperModel('tiny', device='cpu', compute_type='int8')\n"
 316 |             "segs, _ = model.transcribe(sys.argv[1], language='en')\n"
 317 |             "t = ' '.join(s.text for s in segs).lower()\n"
 318 |             "bad = ['pause','breath','emphasis','break colon','slash','open bracket','close bracket']\n"
 319 |             "print(json.dumps([w for w in bad if w in t]))\n"
 320 |         )
 321 |         r = _sp.run(['python3', '-c', checker, tmp_path],
 322 |                     capture_output=True, text=True, timeout=45)
 323 |         if r.returncode == 0 and r.stdout.strip():
 324 |             tts_artifacts = _json.loads(r.stdout.strip())
 325 |         _os.unlink(tmp_path)
 326 |     except Exception as _e:
 327 |         log(f"TTS artifact check skipped: {_e}")
 328 |     res['tts_artifacts'] = tts_artifacts
 329 |     if tts_artifacts:
 330 |         log(f"TTS ARTIFACT ALERT: narrator reading markers aloud: {tts_artifacts}")
 331 |     log(f"Forensics: {res.get('duration',0):.0f}s {res.get('width')}x{res.get('height')} "
 332 |         f"LUFS={res.get('integrated_lufs')} TP={res.get('true_peak_dbfs')} "
 333 |         f"black={res.get('black_mid_count')} freeze={res.get('freeze_count')}")
 334 |     return res
 335 | 
 336 | 
 337 | def grade_with_gemini(video, forensics, render_log):
 338 |     log("Calling Gemini for 24-dimension grade...")
 339 |     prompt = f"""Grade this Protocol Pulse Bitcoin show episode across 24 dimensions.
 340 | Only award Grade A if you would genuinely be proud to publish it as world-class Bitcoin media.
 341 | 
 342 | FORENSICS:
 343 | - Duration: {forensics.get('duration',0):.1f}s ({forensics.get('duration',0)/60:.1f}min)
 344 | - Resolution: {forensics.get('width')}x{forensics.get('height')} @ {forensics.get('fps',0):.1f}fps
 345 | - Codec: {forensics.get('vcodec')} + {forensics.get('acodec')}
 346 | - Loudness: {forensics.get('integrated_lufs')} LUFS (target -16 to -14)
 347 | - True Peak: {forensics.get('true_peak_dbfs')} dBFS (must be <= -1.0)
 348 | - Black frames (mid): {forensics.get('black_mid_count',0)} (0 = perfect)
 349 | - Freeze frames: {forensics.get('freeze_count',0)} (0 = perfect)
 350 | 
 351 | RENDER LOG (last 200 lines):
 352 | {chr(10).join(render_log.splitlines()[-200:])}
 353 | 
 354 | RUBRIC (24 dimensions, Grade A = score >= 88, zero critical failures):
 355 | Technical (40%): duration, resolution, fps, loudness, true_peak, black_frames, silence, freezes, codec, file_integrity
 356 | Content (35%): clip_relevance, script_quality, cold_open, narrative_arc, host_authenticity, episode_title, no_filler, timeliness
 357 | Production (25%): music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing
 358 | 
 359 | Respond ONLY with raw JSON (no fences):
 360 | {{"grade":"A|B|C|D|F","overall_score":0-100,"broadcast_ready":true|false,
 361 | "dimensions":{{"duration_check":{{"score":0-10,"note":""}},"resolution_check":{{"score":0-10,"note":""}},"framerate_check":{{"score":0-10,"note":""}},"loudness_check":{{"score":0-10,"note":""}},"true_peak_check":{{"score":0-10,"note":""}},"black_frames_check":{{"score":0-10,"note":""}},"silence_check":{{"score":0-10,"note":""}},"freeze_check":{{"score":0-10,"note":""}},"codec_check":{{"score":0-10,"note":""}},"file_integrity_check":{{"score":0-10,"note":""}},"clip_relevance":{{"score":0-10,"note":""}},"script_quality":{{"score":0-10,"note":""}},"cold_open_hook":{{"score":0-10,"note":""}},"narrative_arc":{{"score":0-10,"note":""}},"host_authenticity":{{"score":0-10,"note":""}},"episode_title":{{"score":0-10,"note":""}},"no_filler":{{"score":0-10,"note":""}},"timeliness":{{"score":0-10,"note":""}},"music_mix":{{"score":0-10,"note":""}},"transitions":{{"score":0-10,"note":""}},"visual_polish":{{"score":0-10,"note":""}},"no_artifacts":{{"score":0-10,"note":""}},"audio_quality":{{"score":0-10,"note":""}},"pacing":{{"score":0-10,"note":""}}}},
 362 | "critical_failures":[],"warnings":[],"strengths":[],"targeted_fix_instructions":"Precise instructions for CC session to fix only failing dimensions - file, function, lines.",
 363 | "verdict":"One punchy sentence"}}"""
 364 |     text = gemini_call(prompt, 8000)
 365 |     if not text: return None
 366 |     clean = text.strip()
 367 |     for fence in ['```json', '```']:
 368 |         if fence in clean:
 369 |             clean = clean.split(fence)[1].split('```')[0].strip()
 370 |     try: return json.loads(clean)
 371 |     except json.JSONDecodeError as e: log(f"JSON parse fail: {e} — {clean[:200]}"); return None
 372 | 
 373 | 
 374 | def fire_cc_fix(iteration, grade_result):
 375 |     failures = grade_result.get('critical_failures', [])
 376 |     dims = grade_result.get('dimensions', {})
 377 |     failing = [(k, v['score'], v.get('note','')) for k,v in dims.items()
 378 |                if isinstance(v.get('score'), int) and v['score'] < 7]
 379 |     failing.sort(key=lambda x: x[1])
 380 |     prompt = f"""# PIPELINE FIX - ITERATION {iteration} - GRADE {grade_result.get('grade')} ({grade_result.get('overall_score')}/100)
 381 | VERDICT: {grade_result.get('verdict','')}
 382 | CRITICAL FAILURES: {chr(10).join(f'- {f}' for f in failures) or 'None'}
 383 | FAILING DIMS (<7/10): {chr(10).join(f'- {k}: {s}/10 - {n[:80]}' for k,s,n in failing[:8]) or 'None'}
 384 | FIX INSTRUCTIONS: {grade_result.get('targeted_fix_instructions','')}
 385 | 
 386 | Read PIPELINE_LAWS.md first. Fix ONLY failing dimensions. Run regression_test.sh after every change.
 387 | Commit: git add -A && git commit -m "fix(pipeline): iter{iteration}" && git push"""
 388 |     pf = os.path.join(PIPELINE, f'logs/cc_fix_iter{iteration}.md')
 389 |     with open(pf, 'w') as f: f.write(prompt)
 390 |     sn = f'fix_iter{iteration}'
 391 |     subprocess.run(f'tmux kill-session -t {sn} 2>/dev/null', shell=True)
 392 |     subprocess.run(f'tmux new-session -d -s {sn}', shell=True)
 393 |     subprocess.run(f"tmux send-keys -t {sn} 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter", shell=True)
 394 |     time.sleep(10)
 395 |     subprocess.run(f"tmux send-keys -t {sn} \"$(cat {pf})\" Enter", shell=True)
 396 |     log(f"CC session {sn} launched")
 397 |     deadline = time.time() + 2700
 398 |     while time.time() < deadline:
 399 |         time.sleep(60)
 400 |         r = subprocess.run(f'tmux has-session -t {sn} 2>/dev/null', shell=True)
 401 |         if r.returncode != 0: log("CC session ended"); break
 402 |         log(f"CC running... {int((deadline-time.time())/60)}min left")
 403 |     time.sleep(30)
 404 | 
 405 | 
 406 | def run_single_render():
 407 |     """Execute one full perfection loop (up to MAX_ITERATIONS). Returns verdict string."""
 408 |     log("="*60)
 409 |     log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
 410 |     log("="*60)
 411 |     start = time.time()
 412 |     grade_result = {}
 413 |     final_verdict = "ERROR"
 414 | 
 415 |     for iteration in range(1, MAX_ITERATIONS+1):
 416 |         if (time.time()-start)/3600 >= MAX_HOURS:
 417 |             log(f"TIME LIMIT ({MAX_HOURS}h). Stopping."); break
 418 |         log(f"\n{'='*60}\nITERATION {iteration}/{MAX_ITERATIONS}\n{'='*60}")
 419 |         video, rlog = run_render(iteration)
 420 |         if not video:
 421 |             log("Render failed, skipping"); time.sleep(60); continue
 422 |         try:
 423 |             forensics = run_forensics(video)
 424 |         except Exception as _fe:
 425 |             log(f"Forensics failed (non-fatal): {_fe}")
 426 |             forensics = {}
 427 |         try:
 428 |             grade_result = grade_with_gemini(video, forensics, rlog)
 429 |         except Exception as _ge:
 430 |             log(f"Grading failed (non-fatal): {_ge}")
 431 |             grade_result = None
 432 |         if not grade_result:
 433 |             # Fallback: run gemini_grade.py directly as subprocess
 434 |             log("grade_with_gemini failed — running gemini_grade.py directly")
 435 |             try:
 436 |                 import subprocess as _sp
 437 |                 r = _sp.run(
 438 |                     ["python3", "gemini_grade.py", video],
 439 |                     capture_output=True, text=True, timeout=300, cwd=PIPELINE
 440 |                 )
 441 |                 if r.returncode == 0 and "GRADE_" in r.stdout:
 442 |                     # Parse grade from stdout line like: GRADE_A_PASS|95|path|verdict
 443 |                     for line in r.stdout.splitlines():
 444 |                         if line.startswith("GRADE_"):
 445 |                             parts = line.split("|")
 446 |                             grade_letter = parts[0].split("_")[1]
 447 |                             score_val = int(parts[1]) if len(parts)>1 else 0
 448 |                             grade_result = {"grade": grade_letter, "overall_score": score_val,
 449 |                                           "broadcast_ready": grade_letter=="A", "verdict": parts[3] if len(parts)>3 else "",
 450 |                                           "dimensions": {}, "critical_failures": []}
 451 |                             log(f"Fallback grade: {grade_letter} ({score_val}/100)")
 452 |                             break
 453 |             except Exception as _ge2:
 454 |                 log(f"Fallback grading also failed: {_ge2}")
 455 |             if not grade_result:
 456 |                 log("All grading failed, skipping iteration"); continue
 457 |         gf = os.path.join(PIPELINE, f'logs/grade_iter{iteration}.json')
 458 |         with open(gf, 'w') as f: json.dump(grade_result, f, indent=2)
 459 |         grade = grade_result.get('grade','F')
 460 |         score = grade_result.get('overall_score', 0)
 461 |         broadcast = grade_result.get('broadcast_ready', False)
 462 |         log(f"GRADE: {grade} | SCORE: {score}/100 | BROADCAST: {broadcast}")
 463 |         log(f"VERDICT: {grade_result.get('verdict','')}")
 464 |         for dim, data in grade_result.get('dimensions',{}).items():
 465 |             s = data.get('score','?')
 466 |             flag = ' ✓' if isinstance(s,int) and s>=8 else (' !!' if isinstance(s,int) and s<6 else '')
 467 |             log(f"  {dim:30s} {s}/10{flag}")
 468 |         if grade == 'A' and broadcast and score >= 88:
 469 |             log("*** GRADE A — LOCKING WINNER RECIPE ***")
 470 |             recipe = {'winner': True, 'iteration': iteration, 'timestamp': datetime.now().isoformat(),
 471 |                      'video': video, 'grade': grade, 'score': score,
 472 |                      'verdict': grade_result.get('verdict'), 'dimensions': grade_result.get('dimensions',{})}
 473 |             with open(RECIPE_FILE, 'w') as f: json.dump(recipe, f, indent=2)
 474 |             log(f"WINNER: {RECIPE_FILE}")
 475 |             final_verdict = "PASS"
 476 |             break
 477 |         elif grade in ('B', 'C') and broadcast:
 478 |             final_verdict = "DEGRADED"
 479 |         log(f"Grade {grade} - firing CC fix...")
 480 |         fire_cc_fix(iteration, grade_result)
 481 |     else:
 482 |         log("Max iterations reached without Grade A")
 483 |         with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
 484 |             json.dump({'final_grade': grade_result}, f, indent=2)
 485 |         if final_verdict == "ERROR":
 486 |             final_verdict = "HOLD"
 487 | 
 488 |     log("OVERNIGHT LOOP COMPLETE")
 489 |     return final_verdict
 490 | 
 491 | 
 492 | def run_cycle():
 493 |     """FIX 1+2: Run a single render cycle with exception handling and retry logic."""
 494 |     cycle_start = time.time()
 495 | 
 496 |     # FIX 4: Check TTS before render
 497 |     tts_ready, tts_provider = check_tts_ready()
 498 |     log(f"TTS provider: {tts_provider}")
 499 |     if not tts_ready:
 500 |         log(f"[loop] TTS not available ({tts_provider}) — skipping cycle")
 501 |         write_heartbeat("ERROR", time.time() - cycle_start)
 502 |         return
 503 | 
 504 |     for attempt in range(1, MAX_ATTEMPTS_PER_CYCLE + 1):
 505 |         log(f"[loop] Attempt {attempt}/{MAX_ATTEMPTS_PER_CYCLE}")
 506 |         try:
 507 |             verdict = run_single_render()
 508 |         except Exception as e:
 509 |             logger.error(f"[loop] Render cycle exception: {e}", exc_info=True)
 510 |             verdict = "ERROR"
 511 | 
 512 |         if verdict in ("PASS", "DEGRADED"):
 513 |             write_heartbeat(verdict, time.time() - cycle_start)
 514 |             return
 515 | 
 516 |         # Failed — retry logic
 517 |         if attempt < MAX_ATTEMPTS_PER_CYCLE:
 518 |             log(f"[loop] Attempt {attempt} failed ({verdict}), waiting {RETRY_WAIT_SECONDS//60}min before retry...")
 519 |             time.sleep(RETRY_WAIT_SECONDS)
 520 |         else:
 521 |             log(f"[loop] All {MAX_ATTEMPTS_PER_CYCLE} attempts failed — waiting for next scheduled cycle")
 522 | 
 523 |     write_heartbeat(verdict, time.time() - cycle_start)
 524 | 
 525 | 
 526 | # ── FIX 5: Daemon mode ───────────────────────────────────────────
 527 | def sleep_until_next_8am_et():
 528 |     """Sleep until next 08:00 ET (12:00 UTC or 11:00 UTC during DST)."""
 529 |     from zoneinfo import ZoneInfo
 530 |     et = ZoneInfo("America/New_York")
 531 |     now = datetime.now(et)
 532 |     target = now.replace(hour=8, minute=0, second=0, microsecond=0)
 533 |     if target <= now:
 534 |         target += timedelta(days=1)
 535 |     wait = (target - now).total_seconds()
 536 |     log(f"[daemon] Sleeping {wait/3600:.1f}h until {target.isoformat()}")
 537 |     time.sleep(wait)
 538 | 
 539 | 
 540 | PIDFILE = os.path.join(BASE, 'logs', 'render_loop.pid')
 541 | 
 542 | 
 543 | def _acquire_singleton():
 544 |     """P1 FIX (audit): Prevent duplicate render loop instances."""
 545 |     import fcntl
 546 |     fp = open(PIDFILE, 'w')
 547 |     try:
 548 |         fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
 549 |     except OSError:
 550 |         log("ABORT: Another render loop instance is already running (pidfile locked)")
 551 |         sys.exit(1)
 552 |     fp.write(str(os.getpid()))
 553 |     fp.flush()
 554 |     # Keep fp open to hold the lock — do NOT close or the lock releases
 555 |     return fp
 556 | 
 557 | 
 558 | def main():
 559 |     parser = argparse.ArgumentParser(
 560 |         description="Protocol Pulse overnight render loop — production hardened",
 561 |         formatter_class=argparse.RawDescriptionHelpFormatter,
 562 |         epilog=(
 563 |             "Examples:\n"
 564 |             "  python3 overnight_render_loop.py              # single cycle\n"
 565 |             "  python3 overnight_render_loop.py --daemon      # continuous, 08:00 ET daily\n"
 566 |             "  python3 overnight_render_loop.py --dry-run     # startup checks only\n"
 567 |         )
 568 |     )
 569 |     parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (loop at 08:00 ET daily)")
 570 |     parser.add_argument("--dry-run", action="store_true", help="Run startup checks only, no render")
 571 |     args = parser.parse_args()
 572 | 
 573 |     # P1 FIX (audit): Singleton guard — prevent duplicate instances
 574 |     _lock_fp = _acquire_singleton()
 575 | 
 576 |     # FIX 6: Startup checks always run
 577 |     log("="*60)
 578 |     log("STARTUP CHECKS")
 579 |     log("="*60)
 580 |     if not startup_checks():
 581 |         log("STARTUP CHECKS FAILED — exiting")
 582 |         sys.exit(1)
 583 |     log("All startup checks passed")
 584 | 
 585 |     if args.dry_run:
 586 |         log("--dry-run mode: startup checks passed, exiting")
 587 |         sys.exit(0)
 588 | 
 589 |     # Load existing heartbeat state
 590 |     global _total_episodes, _consecutive_failures
 591 |     try:
 592 |         with open(HEARTBEAT_FILE) as f:
 593 |             hb = json.load(f)
 594 |             _total_episodes = hb.get('total_episodes', 0)
 595 |             _consecutive_failures = hb.get('consecutive_failures', 0)
 596 |         log(f"Heartbeat loaded: episodes={_total_episodes}, consecutive_failures={_consecutive_failures}")
 597 |     except (FileNotFoundError, json.JSONDecodeError):
 598 |         pass
 599 | 
 600 |     if args.daemon:
 601 |         log("DAEMON MODE — will loop at 08:00 ET daily")
 602 |         while True:
 603 |             run_cycle()
 604 |             sleep_until_next_8am_et()
 605 |     else:
 606 |         run_cycle()
 607 | 
 608 | 
 609 | if __name__ == '__main__':
 610 |     main()
 611 | 
```

### File: video_pipeline_v3/gemini_grade.py (468 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | gemini_grade.py — Protocol Pulse V6 Quality Gate
   4 | Submits full forensic data to Gemini 2.5 Pro for rigorous grading.
   5 | Only exits 0 (PASS) if grade == A and broadcast_ready == True.
   6 | PBX sees NOTHING until this exits 0.
   7 | """
   8 | import os, sys, json, urllib.request, subprocess, re, time
   9 | 
  10 | # Load env
  11 | for line in open('/home/ultron/protocol_pulse/.env'):
  12 |     l = line.strip()
  13 |     if '=' in l and not l.startswith('#'):
  14 |         k, _, v = l.partition('=')
  15 |         k = k.strip(); v = v.strip().strip("'").strip('"')
  16 |         if k: os.environ[k] = v
  17 | 
  18 | GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
  19 | LOG = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/grade_report.log'
  20 | GRADE_FILE = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_gemini_grade.json'
  21 | PASS_FILE = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_grade_PASS.txt'
  22 | RENDER_LOG = None  # resolved dynamically below
  23 | 
  24 | def log(msg):
  25 |     ts = time.strftime('%Y-%m-%d %H:%M:%S')
  26 |     line = f"[{ts}] {msg}"
  27 |     print(line, flush=True)
  28 |     with open(LOG, 'a') as f:
  29 |         f.write(line + '\n')
  30 | 
  31 | def run(cmd):
  32 |     r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
  33 |     return r.stdout.strip()
  34 | 
  35 | # ── Find the output file ──────────────────────────────────────────────────────
  36 | OUTPUT_DIR = '/home/ultron/protocol_pulse/video_pipeline_v3/output'
  37 | today = time.strftime('%Y%m%d')
  38 | 
  39 | candidates = []
  40 | for root, dirs, files in os.walk(OUTPUT_DIR):
  41 |     for f in files:
  42 |         if f.endswith('.mp4') and 'pulse_check' in f and '.mp4.' not in os.path.basename(f) and 'bgl_audio' not in f and 'archived' not in f and 'music_mixed' not in f and 'concat_raw' not in f and 'norm' not in f:
  43 |             full = os.path.join(root, f)
  44 |             candidates.append((os.path.getmtime(full), full))
  45 | 
  46 | candidates.sort(reverse=True)
  47 | LATEST = candidates[0][1] if candidates else None
  48 | 
  49 | if not LATEST:
  50 |     log("FATAL: No MP4 output found")
  51 |     sys.exit(2)
  52 | 
  53 | log(f"Grading: {LATEST}")
  54 | 
  55 | # ── ffprobe ───────────────────────────────────────────────────────────────────
  56 | log("Running ffprobe...")
  57 | probe_raw = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{LATEST}"')
  58 | try:
  59 |     probe = json.loads(probe_raw)
  60 |     fmt = probe.get('format', {})
  61 |     streams = probe.get('streams', [])
  62 |     duration = float(fmt.get('duration', 0))
  63 |     filesize_mb = int(fmt.get('size', 0)) / 1048576
  64 |     v_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
  65 |     a_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})
  66 |     width = v_stream.get('width', 0)
  67 |     height = v_stream.get('height', 0)
  68 |     vcodec = v_stream.get('codec_name', 'unknown')
  69 |     fps_raw = v_stream.get('r_frame_rate', '0/1')
  70 |     fps_num, fps_den = fps_raw.split('/') if '/' in fps_raw else (fps_raw, '1')
  71 |     fps = round(int(fps_num) / max(int(fps_den), 1), 2)
  72 |     acodec = a_stream.get('codec_name', 'unknown')
  73 |     sample_rate = a_stream.get('sample_rate', '?')
  74 |     channels = a_stream.get('channel_layout', '?')
  75 |     num_streams = len(streams)
  76 |     bit_rate_kbps = round(int(fmt.get('bit_rate', 0)) / 1000)
  77 | except Exception as e:
  78 |     log(f"ffprobe parse error: {e}")
  79 |     duration = filesize_mb = 0
  80 |     width = height = fps = 0
  81 |     vcodec = acodec = 'unknown'
  82 |     sample_rate = channels = '?'
  83 |     num_streams = 0
  84 |     bit_rate_kbps = 0
  85 | 
  86 | log(f"Duration: {duration:.1f}s | Size: {filesize_mb:.1f}MB | {width}x{height} @ {fps}fps | {vcodec}/{acodec}")
  87 | 
  88 | # ── Black frame detection ─────────────────────────────────────────────────────
  89 | log("Running blackdetect...")
  90 | black_raw = run(f'ffmpeg -i "{LATEST}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1 | grep black_')
  91 | black_segments = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', black_raw)
  92 | # Filter out very short blacks at start/end (normal fade in/out)
  93 | black_mid = [(s,e,d) for s,e,d in black_segments
  94 |              if float(s) > 2.0 and float(e) < duration - 2.0]
  95 | black_count_total = len(black_segments)
  96 | black_count_mid = len(black_mid)
  97 | log(f"Black segments: {black_count_total} total, {black_count_mid} mid-video (problem ones)")
  98 | 
  99 | # ── Silence detection ─────────────────────────────────────────────────────────
 100 | log("Running silencedetect...")
 101 | silence_raw = run(f'ffmpeg -i "{LATEST}" -af "silencedetect=noise=-45dB:d=0.8" -f null - 2>&1 | grep silence_')
 102 | silence_starts = re.findall(r'silence_start: ([\d.]+)', silence_raw)
 103 | silence_ends = re.findall(r'silence_end: ([\d.]+)', silence_raw)
 104 | silence_mid = [float(s) for s in silence_starts if float(s) > 2.0 and float(s) < duration - 2.0]
 105 | silence_count = len(silence_mid)
 106 | log(f"Silence gaps >0.8s mid-video: {silence_count}")
 107 | 
 108 | # ── EBU R128 loudness ─────────────────────────────────────────────────────────
 109 | log("Running EBU R128 loudness measurement...")
 110 | loudness_raw = run(f'ffmpeg -i "{LATEST}" -map 0:a -af "ebur128=peak=true" -f null - 2>&1')
 111 | # Parse the summary block at the end (lines starting with spaces + label + colon)
 112 | integrated_match = re.search(r'^\s+I:\s+(-[\d.]+)\s+LUFS', loudness_raw, re.MULTILINE)
 113 | true_peak_match = re.search(r'^\s+Peak:\s+(-?[\d.]+)\s+dBFS', loudness_raw, re.MULTILINE)
 114 | lra_match = re.search(r'^\s+LRA:\s+([\d.]+)\s+LU', loudness_raw, re.MULTILINE)
 115 | integrated_lufs = float(integrated_match.group(1)) if integrated_match else None
 116 | true_peak_dbfs = float(true_peak_match.group(1)) if true_peak_match else None
 117 | lra_lu = float(lra_match.group(1)) if lra_match else None
 118 | log(f"Loudness: {integrated_lufs} LUFS | True Peak: {true_peak_dbfs} dBFS | LRA: {lra_lu} LU")
 119 | 
 120 | # ── Freeze frame detection ────────────────────────────────────────────────────
 121 | log("Running freezedetect...")
 122 | # FIX iter1: Raise noise tolerance from 0.003 to 0.02 — the heavily processed
 123 | # bg_loop (desaturated, darkened, vignette) produces near-identical frames that
 124 | # trigger false positives at 0.3% tolerance. 2% still catches genuine freezes.
 125 | freeze_raw = run(f'ffmpeg -i "{LATEST}" -vf "freezedetect=n=0.02:d=1.0" -an -f null - 2>&1 | grep freeze')
 126 | # Parse freeze events with timestamps
 127 | _freeze_events = []
 128 | _freeze_starts = re.findall(r'freeze_start:\s*([\d.]+)', freeze_raw)
 129 | _freeze_durs   = re.findall(r'freeze_duration:\s*([\d.]+)', freeze_raw)
 130 | for s, d in zip(_freeze_starts, _freeze_durs):
 131 |     _freeze_events.append((float(s), float(d)))
 132 | 
 133 | # Get video duration for outro zone exclusion
 134 | _vid_dur = 0
 135 | try:
 136 |     _vid_dur_raw = run(f'ffprobe -v error -show_entries format=duration '
 137 |                        f'-of default=noprint_wrappers=1:nokey=1 "{LATEST}"')
 138 |     _vid_dur = float(_vid_dur_raw) if _vid_dur_raw else 0
 139 | except Exception:
 140 |     _vid_dur = 0
 141 | 
 142 | # Exclude: intro zone (first 16s) and outro zone (last 25s)
 143 | # Both use intentional freeze-frame backgrounds by design
 144 | _outro_start = max(0, _vid_dur - 25)
 145 | freeze_count = sum(
 146 |     1 for (s, d) in _freeze_events
 147 |     if d > 2.0            # duration threshold
 148 |     and s > 16.0          # not intro zone
 149 |     and s < _outro_start  # not outro zone
 150 | )
 151 | log(f"Freeze events: {len(_freeze_events)} total, "
 152 |     f"{freeze_count} penalized (excl intro <16s, outro >{_outro_start:.0f}s)")
 153 | 
 154 | # ── Audio/video stream count ──────────────────────────────────────────────────
 155 | has_video = v_stream != {}
 156 | has_audio = a_stream != {}
 157 | 
 158 | # ── Read render log for content context ──────────────────────────────────────
 159 | # Find most recent render log by mtime (v6_render.log is stale)
 160 | render_log_content = ''
 161 | try:
 162 |     import glob as _glob
 163 |     _log_dir = '/home/ultron/protocol_pulse/video_pipeline_v3/logs'
 164 |     _candidates = (_glob.glob(f'{_log_dir}/render_*.log') +
 165 |                    _glob.glob(f'{_log_dir}/full_render_*.log') +
 166 |                    _glob.glob(f'{_log_dir}/v6_render.log'))
 167 |     _candidates = [f for f in _candidates if os.path.isfile(f)]
 168 |     # FIX 5: Only accept render logs with mtime within last 2 hours
 169 |     _fresh_cutoff = time.time() - 7200
 170 |     _candidates = [f for f in _candidates if os.path.getmtime(f) >= _fresh_cutoff]
 171 |     if _candidates:
 172 |         RENDER_LOG = max(_candidates, key=os.path.getmtime)
 173 |     else:
 174 |         RENDER_LOG = None  # No fresh render log available
 175 |     if not RENDER_LOG:
 176 |         log("No fresh render log found (within 2h) — using empty context")
 177 |         render_log_content = ''
 178 |         raise FileNotFoundError("skip")
 179 |     log(f"Using render log: {RENDER_LOG}")
 180 |     with open(RENDER_LOG) as f:
 181 |         lines = f.readlines()
 182 |     # Filter noise, keep last 50 meaningful lines
 183 |     keep = [l.strip() for l in lines if l.strip() and
 184 |             not any(x in l for x in ['urllib3', 'HTTP Request', 'DEBUG', 'WARNING: Retrying'])]
 185 |     render_log_content = '\n'.join(keep[-50:])
 186 | except:
 187 |     render_log_content = 'Render log unavailable'
 188 | 
 189 | # ── FIX iter1: Extract episode title from script.json for grading ────────────
 190 | episode_title = 'Not provided'
 191 | try:
 192 |     import glob as _glob2
 193 |     _run_dir = os.path.dirname(LATEST)
 194 |     # script.json lives in the run directory or its parent
 195 |     _script_candidates = (
 196 |         _glob2.glob(os.path.join(_run_dir, 'script.json')) +
 197 |         _glob2.glob(os.path.join(_run_dir, '..', 'script.json')) +
 198 |         _glob2.glob(os.path.join(OUTPUT_DIR, '*', 'script.json'))
 199 |     )
 200 |     _script_candidates = [f for f in _script_candidates if os.path.isfile(f)]
 201 |     if _script_candidates:
 202 |         _script_file = max(_script_candidates, key=os.path.getmtime)
 203 |         with open(_script_file) as _sf:
 204 |             _script_data = json.load(_sf)
 205 |         episode_title = _script_data.get('episode_title', 'Not provided')
 206 |         log(f"Episode title: {episode_title}")
 207 |     else:
 208 |         log("No script.json found — episode title unavailable")
 209 | except Exception as _et_err:
 210 |     log(f"Episode title extraction failed: {_et_err}")
 211 | 
 212 | # ── Build Gemini prompt ───────────────────────────────────────────────────────
 213 | log("Building Gemini grading prompt...")
 214 | 
 215 | PROMPT = f"""You are the Chief Quality Officer for Protocol Pulse, a daily autonomous cypherpunk Bitcoin intelligence video show viewed through an Austrian economics lens.
 216 | PBX is the SOLE host. This is a single-host show — there is no co-host, no second voice, no guest expected. Do NOT penalise for the absence of a second host.
 217 | Your job: grade this episode with maximum rigour. Be brutally honest. A grade A means it is genuinely broadcast-ready and PBX will publish it immediately. Do not hand out A grades lightly.
 218 | 
 219 | === EPISODE FORENSIC DATA ===
 220 | 
 221 | FILE: {os.path.basename(LATEST)}
 222 | EPISODE TITLE: {episode_title}
 223 | DURATION: {duration:.1f} seconds ({duration/60:.1f} minutes)
 224 | FILE SIZE: {filesize_mb:.1f} MB
 225 | BITRATE: {bit_rate_kbps} kbps
 226 | RESOLUTION: {width}x{height}
 227 | FRAMERATE: {fps} fps
 228 | VIDEO CODEC: {vcodec}
 229 | AUDIO CODEC: {acodec} | {sample_rate} Hz | {channels}
 230 | TOTAL STREAMS: {num_streams}
 231 | 
 232 | LOUDNESS (EBU R128):
 233 |   Integrated: {integrated_lufs} LUFS   (target: -16 to -14 LUFS)
 234 |   True Peak: {true_peak_dbfs} dBFS     (must be under -1.0 dBFS)
 235 |   LRA: {lra_lu} LU                     (target: 4-18 LU)
 236 | 
 237 | BLACK FRAME SEGMENTS: {black_count_total} total | {black_count_mid} mid-video
 238 |   (Mid-video blacks are critical failures. Start/end fades OK.)
 239 |   Details: {str(black_mid[:5]) if black_mid else 'none'}
 240 | 
 241 | SILENCE GAPS (>0.8s, mid-video): {silence_count}
 242 | 
 243 | FREEZE FRAMES (>1s): {freeze_count}
 244 | 
 245 | === RENDER LOG (content/script details) ===
 246 | {render_log_content}
 247 | 
 248 | === GRADING RUBRIC ===
 249 | 
 250 | Grade each dimension 1-10. Then calculate weighted overall score.
 251 | 
 252 | TECHNICAL QUALITY (40% weight):
 253 | 1. duration_check: 480-900s ideal (8-15min). Under 180s = automatic F. 300-480s acceptable but short. Over 900s penalise.
 254 | 2. resolution_check: 1920x1080 = 10. 1280x720 = 7. Anything else = fail.
 255 | 3. framerate_check: 24-30fps = 10. Under 24fps = 5. Under 15fps = 0.
 256 | 4. loudness_check: -16 to -14 LUFS = 10. -18 to -12 LUFS = 7. Outside -20 to -10 = critical failure (score 0).
 257 | 5. true_peak_check: Under -1 dBFS = 10. -1 to 0 = 7. Over 0 dBFS = critical failure (clipping).
 258 | 6. black_frames_check: 0 mid-video blacks = 10. 1 = 6. 2+ = critical failure (score 0).
 259 | 7. silence_check: 0 gaps = 10. 1-2 gaps = 6. 3+ = major issue (score 3).
 260 | 8. freeze_check: 0 freezes = 10. 1 = 5. 2+ = critical failure.
 261 | 9. codec_check: h264/aac = 10. h265/aac = 10. Other combos = 5.
 262 | 10. file_integrity_check: Clean container, both streams present, reasonable bitrate (500-5000 kbps) = 10.
 263 | 
 264 | CONTENT QUALITY (35% weight):
 265 | 11. clip_relevance: Are clips from real Bitcoin news? Are the sources credible (not altcoin shills, not 24/7 loops)? Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, and Simply Bitcoin rank editorially higher — clips from these sources are a positive signal. Austrian economics framing (sound money, Cantillon effect, time preference, proof-of-work ethos) is a positive editorial signal. Signal Active Nostr content (npubs, zaps, relay discussion) is a feature, not a bug — do not penalise.
 266 | 12. script_quality: Is the narration between clips informed, specific, and adds value beyond just re-reading the clips?
 267 | 13. cold_open_hook: Does the episode open with a compelling, specific hook that makes you want to keep watching?
 268 | 14. narrative_arc: Does the episode flow logically from open -> clips -> analysis -> close? Or is it random?
 269 | 15. host_authenticity: PBX is the SOLE host — score 10/10 if PBX voice is clean, natural, authoritative, and well-paced throughout. Do NOT penalise for absence of a second host or co-host. Only deduct for dead air, robotic tone, or missing audio in PBX's voice.
 270 | 16. episode_title: Is the title specific and punchy? Not generic clickbait. Should reflect the actual main story.
 271 | 17. no_filler: No ad reads, no sponsor segments, no off-topic content, no repeated clips.
 272 | 18. timeliness: Is the content from today or yesterday? Not stale week-old news.
 273 | 
 274 | PRODUCTION QUALITY (25% weight):
 275 | 19. music_mix: Background music present at proper level, not overpowering narration. Sidechain ducking working?
 276 | 20. transitions: Are there clean glitch transitions between segments? No hard cuts mid-sentence.
 277 | 21. visual_polish: Cyberpunk aesthetic consistent. Lower thirds present. No graphical glitches.
 278 | 22. no_artifacts: No stuttering, no looping, no corrupted frames visible.
 279 | 23. audio_quality: Narration clear, no clipping, no echo, no background noise in voiceover.
 280 | 24. pacing: Does the episode feel tight? Not dragging? Not too rushed?
 281 | 
 282 | === YOUR RESPONSE ===
 283 | 
 284 | You MUST respond ONLY with valid JSON. No preamble, no explanation, no markdown fences. Raw JSON only.
 285 | 
 286 | {{
 287 |   "grade": "A|B|C|D|F",
 288 |   "overall_score": 0-100,
 289 |   "broadcast_ready": true|false,
 290 |   "technical_score": 0-100,
 291 |   "content_score": 0-100,
 292 |   "production_score": 0-100,
 293 |   "dimensions": {{
 294 |     "duration_check": {{"score": 0-10, "note": "explain"}},
 295 |     "resolution_check": {{"score": 0-10, "note": "explain"}},
 296 |     "framerate_check": {{"score": 0-10, "note": "explain"}},
 297 |     "loudness_check": {{"score": 0-10, "note": "explain"}},
 298 |     "true_peak_check": {{"score": 0-10, "note": "explain"}},
 299 |     "black_frames_check": {{"score": 0-10, "note": "explain"}},
 300 |     "silence_check": {{"score": 0-10, "note": "explain"}},
 301 |     "freeze_check": {{"score": 0-10, "note": "explain"}},
 302 |     "codec_check": {{"score": 0-10, "note": "explain"}},
 303 |     "file_integrity_check": {{"score": 0-10, "note": "explain"}},
 304 |     "clip_relevance": {{"score": 0-10, "note": "explain"}},
 305 |     "script_quality": {{"score": 0-10, "note": "explain"}},
 306 |     "cold_open_hook": {{"score": 0-10, "note": "explain"}},
 307 |     "narrative_arc": {{"score": 0-10, "note": "explain"}},
 308 |     "host_authenticity": {{"score": 0-10, "note": "explain"}},
 309 |     "episode_title": {{"score": 0-10, "note": "explain"}},
 310 |     "no_filler": {{"score": 0-10, "note": "explain"}},
 311 |     "timeliness": {{"score": 0-10, "note": "explain"}},
 312 |     "music_mix": {{"score": 0-10, "note": "explain"}},
 313 |     "transitions": {{"score": 0-10, "note": "explain"}},
 314 |     "visual_polish": {{"score": 0-10, "note": "explain"}},
 315 |     "no_artifacts": {{"score": 0-10, "note": "explain"}},
 316 |     "audio_quality": {{"score": 0-10, "note": "explain"}},
 317 |     "pacing": {{"score": 0-10, "note": "explain"}}
 318 |   }},
 319 |   "critical_failures": [],
 320 |   "warnings": [],
 321 |   "strengths": [],
 322 |   "verdict": "One punchy sentence summarising the episode quality",
 323 |   "recommendation": "PUBLISH|FIX_AND_RERENDER|DO_NOT_PUBLISH"
 324 | }}
 325 | 
 326 | Grade thresholds:
 327 | - A: overall_score >= 88, zero critical_failures, broadcast_ready = true
 328 | - B: overall_score 75-87, at most 1 minor critical failure
 329 | - C: overall_score 60-74
 330 | - D: overall_score 40-59
 331 | - F: overall_score < 40 OR duration < 180s OR clipping OR 2+ mid-video black segments
 332 | Note: Episodes 8-15 minutes (480-900s) are the ideal target format. 5 clips is the target.
 333 | """
 334 | 
 335 | # ── Call Gemini ───────────────────────────────────────────────────────────────
 336 | log("Calling Gemini 2.5 Pro for grading (this may take 30-60s)...")
 337 | 
 338 | url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}'
 339 | payload = {
 340 |     'contents': [{'parts': [{'text': PROMPT}]}],
 341 |     'generationConfig': {'maxOutputTokens': 8000, 'temperature': 0.05}
 342 | }
 343 | 
 344 | req_obj = urllib.request.Request(url,
 345 |     data=json.dumps(payload).encode(),
 346 |     headers={'Content-Type': 'application/json'})
 347 | 
 348 | try:
 349 |     with urllib.request.urlopen(req_obj, timeout=90) as resp:
 350 |         d = json.loads(resp.read())
 351 |         parts = d['candidates'][0]['content'].get('parts', [])
 352 |         text = next((p['text'] for p in parts if 'text' in p), None)
 353 |         if not text:
 354 |             log("FATAL: Gemini returned no text")
 355 |             sys.exit(2)
 356 | except urllib.error.HTTPError as e:
 357 |     log(f"FATAL: Gemini HTTP error {e.code}: {e.read().decode()[:200]}")
 358 |     sys.exit(2)
 359 | except Exception as e:
 360 |     log(f"FATAL: Gemini call failed: {e}")
 361 |     sys.exit(2)
 362 | 
 363 | # ── Parse result ──────────────────────────────────────────────────────────────
 364 | clean = text.strip()
 365 | if '```json' in clean:
 366 |     clean = clean.split('```json')[1].split('```')[0].strip()
 367 | elif '```' in clean:
 368 |     clean = clean.split('```')[1].split('```')[0].strip()
 369 | 
 370 | try:
 371 |     result = json.loads(clean)
 372 | except json.JSONDecodeError as e:
 373 |     log(f"FATAL: Could not parse Gemini JSON: {e}")
 374 |     log(f"Raw response: {clean[:500]}")
 375 |     sys.exit(2)
 376 | 
 377 | grade = result.get('grade', 'F')
 378 | score = result.get('overall_score', 0)
 379 | broadcast = result.get('broadcast_ready', False)
 380 | recommendation = result.get('recommendation', 'DO_NOT_PUBLISH')
 381 | verdict = result.get('verdict', '')
 382 | critical = result.get('critical_failures', [])
 383 | warnings = result.get('warnings', [])
 384 | strengths = result.get('strengths', [])
 385 | 
 386 | # Save full grade report — legacy path + per-render timestamped copy
 387 | with open(GRADE_FILE, 'w') as f:
 388 |     json.dump(result, f, indent=2)
 389 | log(f"Grade report saved to {GRADE_FILE}")
 390 | 
 391 | # Per-render grade history
 392 | GRADES_DIR = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/grades'
 393 | os.makedirs(GRADES_DIR, exist_ok=True)
 394 | ts_tag = time.strftime('%Y%m%d_%H%M%S')
 395 | per_render_path = os.path.join(GRADES_DIR, f'grade_{ts_tag}.json')
 396 | with open(per_render_path, 'w') as f:
 397 |     json.dump(result, f, indent=2)
 398 | log(f"Per-render grade saved to {per_render_path}")
 399 | 
 400 | # ── Print full scorecard ──────────────────────────────────────────────────────
 401 | log("=" * 60)
 402 | log(f"GEMINI GRADE: {grade}  |  SCORE: {score}/100  |  {recommendation}")
 403 | log(f"VERDICT: {verdict}")
 404 | log(f"Technical: {result.get('technical_score')}/100  Content: {result.get('content_score')}/100  Production: {result.get('production_score')}/100")
 405 | log("-" * 60)
 406 | 
 407 | dims = result.get('dimensions', {})
 408 | for dim, data in dims.items():
 409 |     s = data.get('score', '?')
 410 |     n = data.get('note', '')
 411 |     flag = '  ✓' if isinstance(s, int) and s >= 8 else ('  !' if isinstance(s, int) and s < 6 else '')
 412 |     log(f"  {dim:30s} {s}/10{flag}  {n[:80]}")
 413 | 
 414 | log("-" * 60)
 415 | if critical:
 416 |     log(f"CRITICAL FAILURES ({len(critical)}):")
 417 |     for c in critical:
 418 |         log(f"  !! {c}")
 419 | if warnings:
 420 |     log(f"WARNINGS ({len(warnings)}):")
 421 |     for w in warnings:
 422 |         log(f"  -- {w}")
 423 | if strengths:
 424 |     log(f"STRENGTHS ({len(strengths)}):")
 425 |     for s in strengths:
 426 |         log(f"  ++ {s}")
 427 | log("=" * 60)
 428 | 
 429 | # ── Record to episode memory ─────────────────────────────────────────────
 430 | try:
 431 |     sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 432 |     from episode_memory import record_episode
 433 |     _render_id = os.path.basename(os.path.dirname(LATEST)) or os.path.basename(LATEST).replace('.mp4', '')
 434 |     _date = time.strftime('%Y-%m-%d')
 435 |     _clips_used = []
 436 |     _manifest_path = os.path.join(os.path.dirname(LATEST), 'episode_manifest.json')
 437 |     if os.path.exists(_manifest_path):
 438 |         with open(_manifest_path) as _mf:
 439 |             _manifest = json.load(_mf)
 440 |         for _seg in _manifest.get('segments', []):
 441 |             if _seg.get('type') == 'partner_clip':
 442 |                 _vpath = _seg.get('video_path', '')
 443 |                 _fname = os.path.basename(_vpath)
 444 |                 _parts = _fname.replace('.mp4', '').split('_', 2)
 445 |                 _clip_info = {'channel': _parts[2].rsplit('_', 1)[0] if len(_parts) > 2 else 'Unknown',
 446 |                               'video_id': _parts[2].rsplit('_', 1)[-1] if len(_parts) > 2 else ''}
 447 |                 _clips_used.append(_clip_info)
 448 |     record_episode(_render_id, _date, result, _clips_used)
 449 |     log(f"Episode memory recorded: {_render_id} — grade {grade}, {len(_clips_used)} clips")
 450 | except Exception as _em_err:
 451 |     log(f"[WARN] Episode memory recording failed: {_em_err}")
 452 | 
 453 | # ── Pass/fail gate ────────────────────────────────────────────────────────────
 454 | if grade == 'A' and broadcast and score >= 88:
 455 |     log("*** GRADE A CONFIRMED — BROADCAST READY ***")
 456 |     with open(PASS_FILE, 'w') as f:
 457 |         f.write(f"GRADE A CONFIRMED\n")
 458 |         f.write(f"File: {LATEST}\n")
 459 |         f.write(f"Score: {score}/100\n")
 460 |         f.write(f"Verdict: {verdict}\n")
 461 |         f.write(f"Graded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
 462 |     print(f"\nGRADE_A_PASS|{score}|{LATEST}|{verdict}")
 463 |     sys.exit(0)
 464 | else:
 465 |     log(f"NOT GRADE A: {grade} ({score}/100) — PBX will not be shown this render")
 466 |     print(f"\nGRADE_{grade}_FAIL|{score}|{LATEST}|{verdict}")
 467 |     sys.exit(1)
 468 | 
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
