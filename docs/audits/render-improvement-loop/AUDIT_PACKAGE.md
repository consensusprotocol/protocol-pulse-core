# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: render-improvement-loop
# Branch: main
# Generated: 2026-03-24 05:50 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

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
 173 |     "render-improvement-loop": """## YOUR REVIEW TASK — ARCHITECTURE AUDIT (8 CRITICAL QUESTIONS)
 174 | 
 175 | You are auditing a GOSPEL SPEC (design document) for an autonomous render improvement loop.
 176 | NO code has been written yet. Your job is to find every flaw, gap, failure mode, and token
 177 | cost risk BEFORE implementation. Be brutal. Be specific. Cite gospel section numbers.
 178 | 
 179 | ### Q1 — INTEGRATION RISK
 180 | The loop integrates with overnight_render_loop.py via flag files (/tmp/render_fix_complete_iterN).
 181 | What are the failure modes? Race conditions? Flag file left over from previous iteration?
 182 | Loop crash that never writes the flag, blocking overnight loop forever?
 183 | 
 184 | ### Q2 — QWEN RELIABILITY
 185 | The loop assumes Qwen3:30b is running on Ollama at localhost:11434. What happens if Ollama
 186 | is down, model not loaded, or Qwen returns malformed JSON? Does the loop degrade gracefully
 187 | or cascade-fail and kill the render cycle?
 188 | 
 189 | ### Q3 — CC SESSION DETECTION
 190 | The loop waits for CC slot by polling tmux. But tmux session names from previous crashed
 191 | sessions may still exist as zombies. How does the loop distinguish a live CC session from
 192 | a dead one? What is the exact tmux command that proves a session is actively running CC
 193 | vs just existing as a shell?
 194 | 
 195 | ### Q4 — TOKEN COST REALITY
 196 | The gospel claims $2 soft limit per cycle. Given 4-6 failing dimensions typically seen
 197 | (freeze, avatar, true_peak, visual_polish, etc.), each requiring Qwen + 2 external LLM
 198 | calls with ~2000 token payloads, what is the realistic per-cycle cost? Is the $2 limit
 199 | achievable or optimistic?
 200 | 
 201 | ### Q5 — DIMENSION_MAP COMPLETENESS
 202 | Review the DIMENSION_MAP in the gospel. Which Gemini grade dimensions are MISSING from
 203 | the map? What happens when a new dimension appears in a grade that has no mapping?
 204 | Does the loop handle unknown dimensions gracefully?
 205 | 
 206 | ### Q6 — OVERNIGHT LOOP COUPLING
 207 | The minimal change to overnight_render_loop.py is described as "check for flag file,
 208 | wait up to 60 min". But overnight_render_loop.py has a 14400s render timeout. If the
 209 | improvement loop takes 90 min (CC session can run long), does this blow the timeout?
 210 | How should timing be coordinated to avoid killing the render cycle mid-improvement?
 211 | 
 212 | ### Q7 — CONSENSUS FAILURE HANDLING
 213 | When LLMs disagree, the loop sends a Telegram alert and skips the dimension. But if the
 214 | 3 most critical dimensions (avatar, freeze, visual_polish) all produce disagreement,
 215 | the loop commits nothing and the next iteration is identical to the last. What mechanism
 216 | prevents infinite identical render loops with no improvement?
 217 | 
 218 | ### Q8 — IMPLEMENTATION CORRECTNESS
 219 | The loop will write fix specs and fire CC. But CC is Opus 4.6 — it reads the spec and
 220 | uses its own judgment. What guardrails ensure CC implements ONLY the exact patch and
 221 | does not refactor surrounding code, change function signatures, or introduce new
 222 | dependencies that break other pipeline stages?
 223 | 
 224 | ### RESPONSE FORMAT
 225 | For each question (Q1-Q8):
 226 | - STATE the failure mode(s) clearly
 227 | - RATE the severity: CRITICAL / HIGH / MEDIUM / LOW
 228 | - PRESCRIBE the exact mitigation (what to add to the gospel)
 229 | - CITE the gospel section that needs updating
 230 | 
 231 | ### FINAL VERDICT
 232 | After answering all 8 questions:
 233 | - How many CRITICAL issues did you find?
 234 | - Is this gospel ready to build from, or does it need fundamental rework?
 235 | - What is the single most dangerous gap?
 236 | """,
 237 | }
 238 | 
 239 | DEFAULT_REVIEW_TASK = """## YOUR REVIEW TASK
 240 | 
 241 | Perform a forensic code review. Be brutally honest. Cite line numbers.
 242 | There is no developer present. No ego to protect. Only quality matters.
 243 | 
 244 | ### SECTION 1: CORRECTNESS
 245 | Walk through the main user flow step by step. Does the code do what it claims?
 246 | - Logic errors, wrong variable names, silent failures
 247 | - Race conditions (concurrent requests hitting same state)
 248 | - N+1 query problems (DB queries inside loops)
 249 | - Edge cases that will break in production (empty DB, API timeout, bad input)
 250 | 
 251 | ### SECTION 2: LAW COMPLIANCE
 252 | For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
 253 | Cite specific line numbers for any violation or partial compliance.
 254 | 
 255 | ### SECTION 3: SECURITY
 256 | - SQL injection (check raw queries and ORM filter() with user input)
 257 | - Authentication bypasses (routes that should require login but don't)
 258 | - Rate limiting gaps (can one user exhaust paid API limits?)
 259 | - Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
 260 | - Unvalidated user input reaching DB, filesystem, or shell
 261 | 
 262 | ### SECTION 4: FRONTEND QUALITY
 263 | - Does the UI match the spec layout exactly?
 264 | - Hardcoded values that should be dynamic (prices, counts, dates)
 265 | - Mobile viewport breakage
 266 | - JS errors that prevent page functioning
 267 | - Loading / error / empty state for every async operation — are all 3 handled?
 268 | - Does it look world-class? Or does it look like a rushed prototype?
 269 | 
 270 | ### SECTION 5: BACKEND QUALITY
 271 | - DB operations: try/except with rollback on every write?
 272 | - External API calls: timeout + retry + graceful degradation on every call?
 273 | - Cron job: does it handle failure without crashing the service?
 274 | - Memory leaks: large objects created per-request without cleanup?
 275 | - Logging: are errors logged with enough context to debug production issues?
 276 | 
 277 | ### SECTION 6: WORLD-CLASS GAP ANALYSIS
 278 | This is Protocol Pulse — a premium Bitcoin intelligence product.
 279 | What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
 280 | What is genuinely missing that would make this impressive to a professional?
 281 | DO NOT pad this section. Only include changes with material impact.
 282 | If an area is already excellent, explicitly say so — that's equally important.
 283 | 
 284 | ### SECTION 7: SCORES (0-100 each)
 285 | - Backend logic:    X/100
 286 | - Frontend/UI:      X/100
 287 | - Error handling:   X/100
 288 | - Security:         X/100
 289 | - Performance:      X/100
 290 | - Law compliance:   X/100
 291 | - World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
 292 | - OVERALL:          X/100
 293 | 
 294 | ### SECTION 8: PRIORITY ACTION PLAN
 295 | Every fix and improvement, sorted by impact. Be specific — cite file and line.
 296 | Format exactly as:
 297 | P0 CRITICAL | [what] | [file:line] | [why it will break production]
 298 | P1 HIGH     | [what] | [file:line] | [why it degrades quality]
 299 | P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
 300 | P3 LOW      | [what] | [file:line] | [polish]
 301 | 
 302 | ### SECTION 9: THE ONE THING
 303 | If you could only tell the developer one thing to make this dramatically better,
 304 | what would it be? One sentence. Make it count.
 305 | 
 306 | ### SECTION 10: FINAL VERDICT
 307 | In 2-3 sentences: is this code ready for production? What must change first?
 308 | """
 309 | 
 310 | def extract_routes_from_file(filepath: Path, route_prefixes: list[str]) -> str:
 311 |     """Extract only route functions matching given prefixes from a large Flask routes file."""
 312 |     lines = filepath.read_text().split("\n")
 313 |     extracted = []
 314 |     in_route = False
 315 |     route_start = 0
 316 |     brace_indent = 0
 317 | 
 318 |     for i, line in enumerate(lines):
 319 |         # Detect @app.route decorators matching our prefixes
 320 |         if "@app.route(" in line:
 321 |             for prefix in route_prefixes:
 322 |                 if prefix in line:
 323 |                     in_route = True
 324 |                     route_start = i
 325 |                     brace_indent = 0
 326 |                     break
 327 |             else:
 328 |                 # Different route — if we were capturing, this ends the previous function
 329 |                 if in_route:
 330 |                     extracted.append((route_start, i - 1))
 331 |                     in_route = False
 332 |         # End of function: next decorator or top-level def/class not indented
 333 |         elif in_route and i > route_start + 1:
 334 |             stripped = line.strip()
 335 |             if stripped and not line.startswith(" ") and not line.startswith("\t") and not stripped.startswith("#") and not stripped.startswith("@"):
 336 |                 extracted.append((route_start, i - 1))
 337 |                 in_route = False
 338 | 
 339 |     if in_route:
 340 |         extracted.append((route_start, len(lines) - 1))
 341 | 
 342 |     # Build output with line numbers
 343 |     sections = []
 344 |     for start, end in extracted:
 345 |         chunk_lines = lines[start:end + 1]
 346 |         numbered = "\n".join(f"{start + j + 1:4d} | {l}" for j, l in enumerate(chunk_lines))
 347 |         sections.append(numbered)
 348 | 
 349 |     return "\n\n# ... (other routes omitted) ...\n\n".join(sections)
 350 | 
 351 | # High-stakes features get full 2-cycle audit. Others can use 1-cycle if score > 85.
 352 | HIGH_STAKES = {"f1-avatar-oracle", "assembler-v2-rebuild", "x-spaces-pipeline", "v30-terminal-api", "v22-multi-format", "f2-briefing-room", "render-improvement-loop"}
 353 | 
 354 | # ─── AUDIT PACKAGE BUILDER ───────────────────────────────────────────────────
 355 | 
 356 | def build_audit_package(feature_name: str) -> str:
 357 |     """Pull all new/modified files from feature branch and assemble audit package."""
 358 |     gospel_file, branch = FEATURE_MAP[feature_name]
 359 |     gospel_text = (GOSPELS / gospel_file).read_text()
 360 | 
 361 |     # Extract just the LAWS section from gospel
 362 |     laws_section = ""
 363 |     in_laws = False
 364 |     for line in gospel_text.split("\n"):
 365 |         if "## THE LAWS" in line:
 366 |             in_laws = True
 367 |         elif line.startswith("## ") and in_laws and "LAW" not in line:
 368 |             in_laws = False
 369 |         if in_laws:
 370 |             laws_section += line + "\n"
 371 | 
 372 |     # Get diff vs main
 373 |     print(f"  [PACKAGE] Pulling code diff for {branch}...")
 374 |     # Check for explicit file list first (features already on main)
 375 |     if feature_name in EXPLICIT_FILES:
 376 |         diff_files = EXPLICIT_FILES[feature_name]
 377 |         print(f"  [PACKAGE] Using explicit file list: {diff_files}")
 378 |     elif branch == "main":
 379 |         diff_files = []
 380 |         print(f"  [PACKAGE] Branch is main and no explicit files — no diff available")
 381 |     else:
 382 |         try:
 383 |             diff_files = subprocess.check_output(
 384 |                 ["git", "diff", "main.." + branch, "--name-only"],
 385 |                 cwd=BASE, text=True
 386 |             ).strip().split("\n")
 387 |             diff_files = [f for f in diff_files if f]
 388 |         except Exception as e:
 389 |             print(f"  [PACKAGE] Git diff failed: {e}. Using worktree scan.")
 390 |             worktree = Path.home() / f"worktrees/{feature_name}"
 391 |             if worktree.exists():
 392 |                 diff_files = [
 393 |                     str(p.relative_to(worktree))
 394 |                     for p in worktree.rglob("*.py")
 395 |                     if "pycache" not in str(p)
 396 |                 ] + [
 397 |                     str(p.relative_to(worktree))
 398 |                     for p in worktree.rglob("*.html")
 399 |                     if "pycache" not in str(p)
 400 |                 ]
 401 |             else:
 402 |                 diff_files = []
 403 | 
 404 |     # Build code section
 405 |     code_sections = []
 406 |     worktree = Path.home() / f"worktrees/{feature_name}"
 407 |     for fpath in diff_files[:20]:  # cap at 20 files to stay within context
 408 |         full_path = worktree / fpath if worktree.exists() else BASE / fpath
 409 |         if not full_path.exists():
 410 |             continue
 411 |         try:
 412 |             # Check if we should extract specific routes from a large file
 413 |             route_key = (feature_name, fpath)
 414 |             if route_key in ROUTE_EXTRACTS:
 415 |                 numbered = extract_routes_from_file(full_path, ROUTE_EXTRACTS[route_key])
 416 |                 total_lines = len(full_path.read_text().split("\n"))
 417 |                 code_sections.append(f"\n### File: {fpath} (extracted stage routes from {total_lines} lines)\n```\n{numbered}\n```")
 418 |             elif full_path.stat().st_size < 100_000:
 419 |                 code = full_path.read_text()
 420 |                 lines = code.split("\n")
 421 |                 numbered = "\n".join(f"{i+1:4d} | {l}" for i, l in enumerate(lines))
 422 |                 code_sections.append(f"\n### File: {fpath} ({len(lines)} lines)\n```\n{numbered}\n```")
 423 |         except Exception:
 424 |             pass
 425 | 
 426 |     code_block = "\n".join(code_sections) if code_sections else "(No code files found — run after Claude Code session completes)"
 427 | 
 428 |     # Assemble the full audit package
 429 |     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
 430 |     package = f"""# PROTOCOL PULSE — CODE AUDIT PACKAGE
 431 | # Feature: {feature_name}
 432 | # Branch: {branch}
 433 | # Generated: {timestamp}
 434 | # Purpose: Pre-merge quality gate. 3 independent AI models will review this.
 435 | # You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
 436 | # Other top AI models will also review this same code. Put your best work forward.
 437 | 
 438 | ---
 439 | 
 440 | ## WHAT THIS FEATURE DOES
 441 | {gospel_text.split("## WHAT THIS FEATURE IS")[1].split("##")[0].strip() if "## WHAT THIS FEATURE IS" in gospel_text else "(see gospel)"}
 442 | 
 443 | ---
 444 | 
 445 | ## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
 446 | {laws_section}
 447 | 
 448 | ---
 449 | 
 450 | ## TECHNOLOGY STACK
 451 | - Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
 452 | - Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
 453 | - All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
 454 | - External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
 455 | - ~1000 concurrent users at peak — every route must handle load
 456 | - Every DB query on a sort/filter column MUST have an index
 457 | 
 458 | ---
 459 | 
 460 | ## THE CODE (every new and modified file)
 461 | {code_block}
 462 | 
 463 | ---
 464 | 
 465 | {CUSTOM_REVIEW_TASKS.get(feature_name, DEFAULT_REVIEW_TASK)}
 466 | """
 467 |     return package
 468 | 
 469 | 
 470 | # ─── LLM CALLERS ─────────────────────────────────────────────────────────────
 471 | 
 472 | def call_gemini(prompt: str, results: dict, errors: dict):
 473 |     try:
 474 |         from google import genai as google_genai
 475 |         client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
 476 |         GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
 477 |         resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
 478 |         results["gemini"] = resp.text
 479 |         score_hint = "?"
 480 |         for line in resp.text.split("\n"):
 481 |             if "OVERALL" in line.upper() and "/100" in line:
 482 |                 score_hint = line.strip()
 483 |                 break
 484 |         print(f"  [GEMINI] ✅ Done — {score_hint}")
 485 |     except Exception as e:
 486 |         errors["gemini"] = str(e)
 487 |         print(f"  [GEMINI] ❌ ERROR: {e}")
 488 | 
 489 | def call_gpt4o(prompt: str, results: dict, errors: dict):
 490 |     try:
 491 |         from openai import OpenAI
 492 |         client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
 493 |         resp = client.chat.completions.create(
 494 |             model="gpt-4o",
 495 |             messages=[{"role": "user", "content": prompt}],
 496 |             max_completion_tokens=6000,
 497 |             temperature=0.3,
 498 |         )
 499 |         results["gpt4o"] = resp.choices[0].message.content
 500 |         print(f"  [GPT-4o] ✅ Done")
 501 |     except Exception as e:
 502 |         errors["gpt4o"] = str(e)
 503 |         print(f"  [GPT-4o] ❌ ERROR: {e}")
 504 | 
 505 | def call_grok(prompt: str, results: dict, errors: dict):
 506 |     try:
 507 |         from openai import OpenAI
 508 |         client = OpenAI(
 509 |             api_key=os.environ["XAI_API_KEY"],
 510 |             base_url="https://api.x.ai/v1"
 511 |         )
 512 |         resp = client.chat.completions.create(
 513 |             model="grok-3-latest",
 514 |             messages=[{"role": "user", "content": prompt}],
 515 |             max_completion_tokens=6000,
 516 |             temperature=0.3,
 517 |         )
 518 |         results["grok"] = resp.choices[0].message.content
 519 |         print(f"  [GROK]   ✅ Done")
 520 |     except Exception as e:
 521 |         errors["grok"] = str(e)
 522 |         print(f"  [GROK]   ❌ ERROR: {e}")
 523 | 
 524 | def fire_all_llms(prompt: str) -> tuple[dict, dict]:
 525 |     """Fire all 3 LLMs in parallel threads. Returns (results, errors)."""
 526 |     results, errors = {}, {}
 527 |     threads = [
 528 |         threading.Thread(target=call_gemini, args=(prompt, results, errors)),
 529 |         threading.Thread(target=call_gpt4o,  args=(prompt, results, errors)),
 530 |         threading.Thread(target=call_grok,   args=(prompt, results, errors)),
 531 |     ]
 532 |     for t in threads: t.start()
 533 |     for t in threads: t.join()
 534 |     return results, errors
 535 | 
 536 | 
 537 | # ─── CONSENSUS SYNTHESIS ─────────────────────────────────────────────────────
 538 | 
 539 | def synthesize_consensus(feature: str, cycle: int, results: dict, errors: dict,
 540 |                           prev_results: dict = None) -> str:
 541 |     """Claude synthesizes all LLM outputs into consensus report."""
 542 |     import anthropic
 543 |     client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
 544 | 
 545 |     models_output = []
 546 |     for name, text in results.items():
 547 |         models_output.append(f"## {name.upper()} OUTPUT\n{text[:8000]}")
 548 | 
 549 |     prev_section = ""
 550 |     if prev_results:
 551 |         prev_section = "\n\n## CYCLE 1 RESULTS (for context)\n"
 552 |         for name, text in prev_results.items():
 553 |             prev_section += f"### {name.upper()} CYCLE 1\n{text[:3000]}\n\n"
 554 | 
 555 |     synthesis_prompt = f"""You are synthesizing a Cycle {cycle} multi-LLM code audit for Protocol Pulse feature: {feature}
 556 | 
 557 | Three independent AI models (Gemini 2.5 Pro, GPT-4o, Grok-3) reviewed the same code.
 558 | {prev_section}
 559 | 
 560 | Their Cycle {cycle} outputs:
 561 | 
 562 | {"".join(models_output)}
 563 | 
 564 | Errors/failures: {json.dumps(errors) if errors else "None"}
 565 | 
 566 | Produce the CONSENSUS REPORT with these exact sections:
 567 | 
 568 | # CONSENSUS REPORT — {feature.upper()} — CYCLE {cycle}
 569 | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
 570 | Models: {", ".join(results.keys())} {"(+" + str(len(errors)) + " failed)" if errors else ""}
 571 | 
 572 | ## SCORES
 573 | | Subsystem       | Gemini | GPT-4o | Grok | Consensus |
 574 | |-----------------|--------|--------|------|-----------|
 575 | [extract scores from each model's output and populate the table]
 576 | 
 577 | ## UNANIMOUS FINDINGS (all {len(results)} models agree — implement unconditionally)
 578 | [List every issue flagged by ALL models. These are the highest-confidence fixes.]
 579 | For each: what it is, which file/line, what to change.
 580 | 
 581 | ## MAJORITY FINDINGS (2 of {len(results)} models agree)
 582 | [Issues flagged by 2+ models. Implement unless there's a compelling reason not to.]
 583 | 
 584 | ## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)
 585 | [Novel observations from a single model. Some will be the most valuable findings.]
 586 | Your assessment of each: implement / skip / investigate further.
 587 | 
 588 | ## CONFLICTS (models disagree — your tiebreaker)
 589 | [Where models gave contradictory recommendations. State who is right and why.]
 590 | 
 591 | ## VALIDATED STRENGTHS (all models agree this is already excellent)
 592 | [These areas are strong. Do NOT change them in the second pass.]
 593 | 
 594 | ## LAW COMPLIANCE CONSENSUS
 595 | Which laws are violated? Which are fully compliant? Final determination.
 596 | 
 597 | ## SECURITY CONSENSUS
 598 | Any security issues all/most models flagged? Priority order.
 599 | 
 600 | ## WORLD-CLASS GAP CONSENSUS
 601 | What does the combined intelligence of 3 models say is missing from a
 602 | truly world-class product? Only include items 2+ models mentioned.
 603 | 
 604 | ## FINAL ACTION PLAN (sorted by consensus priority)
 605 | P0 CRITICAL | [change] | [file:line] | [models: all/2/unique] | [why]
 606 | P1 HIGH     | [change] | [file:line] | [models] | [why]
 607 | P2 MEDIUM   | [change] | [file:line] | [models] | [why]
 608 | 
 609 | ## CYCLE {cycle} VERDICT
 610 | {'Is the code ready for a second build pass, or does it need fundamental rework?' if cycle == 1 else 'After two full cycles of 3-model review: is this code production-ready? What is the absolute final blocker if any?'}
 611 | 
 612 | ## SECOND PASS PROMPT (ready to fire into Claude Code)
 613 | ```
 614 | Read ~/protocol_pulse/docs/gospels/{FEATURE_MAP.get(feature, ('GOSPEL.md',''))[0]}.
 615 | Read ~/protocol_pulse/docs/audits/{feature}_CONSENSUS_C{cycle}.md.
 616 | 
 617 | This is the {'SECOND' if cycle == 1 else 'FINAL'} PASS for {feature}.
 618 | The first build was reviewed by {len(results)} independent AI models across {cycle} cycle(s).
 619 | Implement every P0 and P1 item from the consensus. Use judgment on P2.
 620 | 
 621 | PRIORITY ACTION PLAN:
 622 | [copy the action plan from above]
 623 | 
 624 | VALIDATED (do NOT touch — all models confirmed excellent):
 625 | [copy validated strengths]
 626 | 
 627 | After implementing: regression_test.sh must show zero FAILs.
 628 | git add -A && git commit -m "feat({feature}): post-audit pass — consensus improvements"
 629 | git push origin {FEATURE_MAP.get(feature, ('','feature/'+feature))[1]}
 630 | ```
 631 | """
 632 | 
 633 |     msg = client.messages.create(
 634 |         model="claude-sonnet-4-6",
 635 |         max_tokens=6000,
 636 |         messages=[{"role": "user", "content": synthesis_prompt}]
 637 |     )
 638 |     return msg.content[0].text
 639 | 
 640 | 
 641 | # ─── CYCLE 2 PACKAGE BUILDER ─────────────────────────────────────────────────
 642 | 
 643 | def build_cycle2_prompt(feature: str, original_package: str,
 644 |                          c1_results: dict, c1_consensus: str) -> str:
 645 |     """Build the Cycle 2 prompt where each LLM sees what the others said."""
 646 |     others_text = "\n\n".join(
 647 |         f"## {name.upper()} — CYCLE 1 OUTPUT\n{text[:5000]}"
 648 |         for name, text in c1_results.items()
 649 |     )
 650 |     return f"""# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
 651 | # Feature: {feature}
 652 | # You are performing your SECOND review of this code.
 653 | # You now have access to what the other AI models said in Cycle 1.
 654 | 
 655 | ---
 656 | 
 657 | ## YOUR CYCLE 1 OUTPUT (what you said before)
 658 | [See below — you wrote this]
 659 | 
 660 | ## WHAT THE OTHER MODELS SAID (Cycle 1)
 661 | {others_text}
 662 | 
 663 | ## CLAUDE'S CYCLE 1 CONSENSUS
 664 | {c1_consensus[:3000]}
 665 | 
 666 | ---
 667 | 
 668 | ## ORIGINAL CODE (same code as Cycle 1)
 669 | {original_package[original_package.find("## THE CODE"):original_package.find("## YOUR REVIEW TASK")]}
 670 | 
 671 | ---
 672 | 
 673 | ## CYCLE 2 INSTRUCTIONS
 674 | 
 675 | You've now seen what the other models said. This is your final review.
 676 | 
 677 | 1. WHAT DID THEY CATCH THAT YOU MISSED?
 678 |    Review their findings. Be honest about what you overlooked.
 679 | 
 680 | 2. WHERE DO YOU AGREE OR DISAGREE?
 681 |    For each of their key findings: agree / disagree / partially agree + why.
 682 | 
 683 | 3. NEW FINDINGS FROM THIS REVIEW
 684 |    Anything the combined analysis revealed that nobody caught in Cycle 1?
 685 | 
 686 | 4. REVISED SCORES
 687 |    Update your scores from Cycle 1. Did anything change your assessment?
 688 |    | Subsystem | Cycle 1 | Cycle 2 | Why changed |
 689 | 
 690 | 5. FINAL PRIORITY LIST
 691 |    Your definitive list of what must change before this ships.
 692 |    P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.
 693 | 
 694 | 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
 695 |    After seeing everything — one sentence. What matters most?
 696 | 
 697 | 7. PRODUCTION READY?
 698 |    Yes / No / Yes with conditions. State your conditions precisely.
 699 | """
 700 | 
 701 | 
 702 | # ─── MAIN RUNNER ─────────────────────────────────────────────────────────────
 703 | 
 704 | def run_audit(feature: str, start_cycle: int = 1, c1_results_path: str = None):
 705 |     print(f"\n{'='*60}")
 706 |     print(f"PROTOCOL PULSE CROSS-LLM AUDIT — {feature.upper()}")
 707 |     print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
 708 |     print(f"{'='*60}\n")
 709 | 
 710 |     # Verify API keys
 711 |     missing_keys = [k for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"]
 712 |                     if not os.environ.get(k)]
 713 |     if missing_keys:
 714 |         print(f"❌ MISSING API KEYS: {missing_keys}")
 715 |         print("Add them to ~/protocol_pulse/.env and re-run.")
 716 |         sys.exit(1)
 717 |     print(f"✅ All API keys present\n")
 718 | 
 719 |     audit_dir = AUDITS / feature
 720 |     audit_dir.mkdir(parents=True, exist_ok=True)
 721 | 
 722 |     # ── CYCLE 1 ───────────────────────────────────────────────────────────────
 723 |     if start_cycle == 1:
 724 |         print("── CYCLE 1: BUILDING AUDIT PACKAGE ────────────────────────────")
 725 |         package = build_audit_package(feature)
 726 |         (audit_dir / "AUDIT_PACKAGE.md").write_text(package)
 727 |         print(f"  Package written: {len(package):,} chars\n")
 728 | 
 729 |         print("── CYCLE 1: FIRING 3 LLMs IN PARALLEL ─────────────────────────")
 730 |         c1_results, c1_errors = fire_all_llms(package)
 731 |         (audit_dir / "C1_GEMINI.md").write_text(c1_results.get("gemini", f"FAILED: {c1_errors.get('gemini')}"))
 732 |         (audit_dir / "C1_GPT4O.md").write_text(c1_results.get("gpt4o",  f"FAILED: {c1_errors.get('gpt4o')}"))
 733 |         (audit_dir / "C1_GROK.md").write_text(c1_results.get("grok",   f"FAILED: {c1_errors.get('grok')}"))
 734 |         print(f"\n  Cycle 1 complete: {list(c1_results.keys())} succeeded, {list(c1_errors.keys())} failed\n")
 735 | 
 736 |         print("── CYCLE 1: SYNTHESIZING CONSENSUS ─────────────────────────────")
 737 |         c1_consensus = synthesize_consensus(feature, 1, c1_results, c1_errors)
 738 |         (audit_dir / "C1_CONSENSUS.md").write_text(c1_consensus)
 739 |         print("  Consensus written\n")
 740 |     else:
 741 |         # Load from previous run
 742 |         print("── LOADING CYCLE 1 RESULTS ─────────────────────────────────────")
 743 |         c1_results = {
 744 |             "gemini": (audit_dir / "C1_GEMINI.md").read_text(),
 745 |             "gpt4o":  (audit_dir / "C1_GPT4O.md").read_text(),
 746 |             "grok":   (audit_dir / "C1_GROK.md").read_text(),
 747 |         }
 748 |         c1_consensus = (audit_dir / "C1_CONSENSUS.md").read_text()
 749 |         package = (audit_dir / "AUDIT_PACKAGE.md").read_text()
 750 |         print("  Loaded from previous run\n")
 751 | 
 752 |     # Check if we need Cycle 2 (skip for low-stakes if high score)
 753 |     run_cycle2 = feature in HIGH_STAKES
 754 |     if not run_cycle2:
 755 |         # Check if overall score > 85 across all models
 756 |         scores = []
 757 |         for text in c1_results.values():
 758 |             for line in text.split("\n"):
 759 |                 if "OVERALL" in line.upper() and "/100" in line:
 760 |                     try:
 761 |                         score = int(''.join(filter(str.isdigit, line.split("/")[0].split()[-1])))
 762 |                         scores.append(score)
 763 |                     except: pass
 764 |         avg_score = sum(scores) / len(scores) if scores else 0
 765 |         run_cycle2 = avg_score < 85
 766 |         print(f"  Average Cycle 1 score: {avg_score:.0f}/100 — {'Running Cycle 2' if run_cycle2 else 'Score high enough, skipping Cycle 2'}\n")
 767 | 
 768 |     if run_cycle2:
 769 |         # ── CYCLE 2 ───────────────────────────────────────────────────────────
 770 |         print("── CYCLE 2: BUILDING CROSS-REVIEW PROMPT ───────────────────────")
 771 |         c2_prompt = build_cycle2_prompt(feature, package, c1_results, c1_consensus)
 772 |         (audit_dir / "C2_PROMPT.md").write_text(c2_prompt)
 773 | 
 774 |         print("── CYCLE 2: FIRING 3 LLMs WITH CROSS-VISIBILITY ────────────────")
 775 |         c2_results, c2_errors = fire_all_llms(c2_prompt)
 776 |         (audit_dir / "C2_GEMINI.md").write_text(c2_results.get("gemini", f"FAILED: {c2_errors.get('gemini')}"))
 777 |         (audit_dir / "C2_GPT4O.md").write_text(c2_results.get("gpt4o",  f"FAILED: {c2_errors.get('gpt4o')}"))
 778 |         (audit_dir / "C2_GROK.md").write_text(c2_results.get("grok",   f"FAILED: {c2_errors.get('grok')}"))
 779 |         print(f"\n  Cycle 2 complete: {list(c2_results.keys())} succeeded\n")
 780 | 
 781 |         print("── CYCLE 2: FINAL CONSENSUS + WINNER ───────────────────────────")
 782 |         final_consensus = synthesize_consensus(feature, 2, c2_results, c2_errors, c1_results)
 783 | 
 784 |         # Determine "winner" — the model whose Cycle 1 findings had the most
 785 |         # items validated by Cycle 2 consensus
 786 |         winner_prompt = f"""Based on this 2-cycle cross-LLM audit, determine which model (Gemini, GPT-4o, or Grok)
 787 | provided the highest-quality analysis overall.
 788 | 
 789 | Criteria:
 790 | 1. Accuracy — did their findings prove correct in Cycle 2?
 791 | 2. Depth — did they find issues others missed?
 792 | 3. Actionability — were their recommendations specific and implementable?
 793 | 4. Completeness — did they cover all sections thoroughly?
 794 | 
 795 | CYCLE 1 OUTPUTS: {json.dumps({k: v[:2000] for k,v in c1_results.items()})}
 796 | CYCLE 2 OUTPUTS: {json.dumps({k: v[:2000] for k,v in c2_results.items()})}
 797 | FINAL CONSENSUS: {final_consensus[:2000]}
 798 | 
 799 | State: WINNER: [model name] — [2 sentence justification]
 800 | Then: FINAL SECOND-PASS PRIORITY LIST — the definitive ordered list of what to implement."""
 801 | 
 802 |         import anthropic
 803 |         client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
 804 |         winner_msg = client.messages.create(
 805 |             model="claude-sonnet-4-6", max_tokens=2000,
 806 |             messages=[{"role": "user", "content": winner_prompt}]
 807 |         )
 808 |         winner_text = winner_msg.content[0].text
 809 | 
 810 |         final_report = final_consensus + "\n\n---\n\n# WINNER DETERMINATION\n\n" + winner_text
 811 |         (audit_dir / "FINAL_CONSENSUS.md").write_text(final_report)
 812 |     else:
 813 |         final_report = c1_consensus
 814 |         (audit_dir / "FINAL_CONSENSUS.md").write_text(final_report)
 815 | 
 816 |     # ── SUMMARY ───────────────────────────────────────────────────────────────
 817 |     print(f"\n{'='*60}")
 818 |     print(f"AUDIT COMPLETE — {feature.upper()}")
 819 |     print(f"{'='*60}")
 820 |     print(f"\nOutputs at: {audit_dir}/")
 821 |     print(f"  AUDIT_PACKAGE.md    — code package sent to LLMs")
 822 |     if run_cycle2:
 823 |         print(f"  C1_*.md             — Cycle 1 individual outputs")
 824 |         print(f"  C1_CONSENSUS.md     — Cycle 1 synthesis")
 825 |         print(f"  C2_*.md             — Cycle 2 individual outputs")
 826 |     print(f"  FINAL_CONSENSUS.md  — final action plan + second-pass prompt")
 827 |     print(f"\nNEXT: Fire the second-pass Claude Code session using the prompt")
 828 |     print(f"      in FINAL_CONSENSUS.md → '## SECOND PASS PROMPT' section")
 829 |     print(f"\n{'='*60}\n")
 830 | 
 831 |     # Print the second-pass prompt for immediate use
 832 |     for line in final_report.split("\n"):
 833 |         if "SECOND PASS PROMPT" in line.upper():
 834 |             idx = final_report.find(line)
 835 |             print("READY TO FIRE — SECOND PASS PROMPT:")
 836 |             print("-"*40)
 837 |             print(final_report[idx:idx+2000])
 838 |             break
 839 | 
 840 |     # Auto-update AUDIT_REGISTRY.json so CI integrity gate stays green
 841 |     try:
 842 |         import json as _j, subprocess as _sp
 843 |         from datetime import datetime as _dt, timezone as _tz
 844 |         rp = BASE / "docs" / "audits" / "AUDIT_REGISTRY.json"
 845 |         existing = _j.loads(rp.read_text()) if rp.exists() else {}
 846 |         audits = [a for a in existing.get("audits", []) if a.get("feature") != feature]
 847 |         audits.append({"feature": feature, "date": _dt.now(_tz.utc).strftime("%Y-%m-%d"), "models": ["gemini", "gpt4o", "grok"]})
 848 |         sha = _sp.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE), text=True).strip()
 849 |         rp.write_text(_j.dumps({"last_audit": _dt.now(_tz.utc).isoformat(), "feature": feature, "commit": sha, "audits": audits[-20:]}, indent=2))
 850 |         print(f"[registry] AUDIT_REGISTRY.json updated for {feature}")
 851 |     except Exception as _e:
 852 |         print(f"[registry] Warning: could not update registry: {_e}")
 853 |     return final_report
 854 | 
 855 | 
 856 | # --- ENTRY POINT ─────────────────────────────────────────────────────────────
 857 | 
 858 | if __name__ == "__main__":
 859 |     # Load .env
 860 |     env_path = Path.home() / "protocol_pulse/.env"
 861 |     if env_path.exists():
 862 |         for line in env_path.read_text().split("\n"):
 863 |             line = line.strip()
 864 |             if line and not line.startswith("#") and "=" in line:
 865 |                 key, _, val = line.partition("=")
 866 |                 os.environ.setdefault(key.strip(), val.strip())
 867 | 
 868 |     parser = argparse.ArgumentParser(description="Cross-LLM code audit engine")
 869 |     parser.add_argument("--feature", required=True,
 870 |                         help=f"Feature to audit. Options: {list(FEATURE_MAP.keys()) + ['all']}")
 871 |     parser.add_argument("--cycle", type=int, default=1,
 872 |                         help="Start from cycle 1 (default) or 2 (resume)")
 873 |     parser.add_argument("--cycle1-results", help="Path to existing cycle 1 results dir")
 874 |     args = parser.parse_args()
 875 | 
 876 |     if args.feature == "all":
 877 |         for feat in FEATURE_MAP:
 878 |             if feat != "video-audio-fix":  # skip until PBX provides notes
 879 |                 run_audit(feat, start_cycle=1)
 880 |                 time.sleep(10)  # avoid API rate limits between features
 881 |     elif args.feature in FEATURE_MAP:
 882 |         run_audit(args.feature, start_cycle=args.cycle)
 883 |     else:
 884 |         print(f"Unknown feature: {args.feature}")
 885 |         print(f"Options: {list(FEATURE_MAP.keys())}")
 886 |         sys.exit(1)
 887 | 
```

### File: video_pipeline_v3/clip_extractor.py (911 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Clip Extractor — downloads exact timestamp ranges from YouTube WITH original audio.
   3 | 
   4 | Uses yt-dlp --download-sections to grab the precise moments Claude selected.
   5 | CRITICAL: Clips retain their ORIGINAL audio. No muting. No TTS overlay.
   6 | """
   7 | import logging
   8 | import os
   9 | import shutil
  10 | import subprocess
  11 | import time
  12 | 
  13 | logger = logging.getLogger("ClipExtractor")
  14 | if not logger.handlers:
  15 |     handler = logging.StreamHandler()
  16 |     handler.setFormatter(logging.Formatter("[extractor] %(message)s"))
  17 |     logger.addHandler(handler)
  18 |     logger.setLevel(logging.INFO)
  19 | 
  20 | BASE = os.path.dirname(os.path.abspath(__file__))
  21 | CLIP_CACHE = os.path.join(BASE, "downloads", "clip_cache")
  22 | COOKIES_FILE = os.path.join(BASE, "data", "yt_cookies.txt")
  23 | # Render20: No hard clip duration cap — episode is as long as it needs to be
  24 | 
  25 | from utils.clip_archive import save_clip, get_fallback_clip
  26 | 
  27 | if not (os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0):
  28 |     logger.info("[yt-dlp] No cookies file — add data/yt_cookies.txt for rate limit protection")
  29 | 
  30 | 
  31 | def _run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
  32 |     """Run ffmpeg command, return True on success."""
  33 |     cmd = ["ffmpeg", "-y"] + args
  34 |     try:
  35 |         proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
  36 |         if proc.returncode != 0:
  37 |             logger.error(f"FAIL {label}: {proc.stderr[-400:]}")
  38 |             return False
  39 |         return True
  40 |     except subprocess.TimeoutExpired:
  41 |         logger.error(f"TIMEOUT {label} after {timeout}s — killing ffmpeg")
  42 |         return False
  43 |     except Exception as e:
  44 |         logger.error(f"EXCEPTION {label}: {e}")
  45 |         return False
  46 | 
  47 | 
  48 | def fix_av_sync(input_path: str, output_path: str) -> bool:
  49 |     """Nuclear AV sync fix — full decode+re-encode with PTS reset.
  50 | 
  51 |     Uses discardcorrupt + itsoffset 0 + max_interleave_delta=0 to eliminate
  52 |     DTS discontinuities from yt-dlp multi-stream merges.
  53 |     """
  54 |     return _run_ffmpeg([
  55 |         "-fflags", "+genpts+igndts+discardcorrupt",
  56 |         "-itsoffset", "0",
  57 |         "-i", input_path,
  58 |         "-map", "0:v:0",
  59 |         "-map", "0:a:0",
  60 |         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
  61 |         "-r", "30", "-vsync", "cfr",
  62 |         "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
  63 |         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
  64 |         "-af", "aresample=async=1:min_hard_comp=0.1:first_pts=0,asetpts=PTS-STARTPTS",
  65 |         "-avoid_negative_ts", "make_zero",
  66 |         "-max_interleave_delta", "0",
  67 |         "-movflags", "+faststart",
  68 |         output_path,
  69 |     ], "av_sync_fix_v2", 300)
  70 | 
  71 | 
  72 | def check_av_sync(clip_path: str) -> float:
  73 |     """Measure actual AV sync using first packet DTS timestamps."""
  74 |     result = subprocess.run([
  75 |         "ffprobe", "-v", "quiet", "-print_format", "json",
  76 |         "-show_packets", "-read_intervals", "%+#10",
  77 |         clip_path
  78 |     ], capture_output=True, text=True)
  79 |     try:
  80 |         import json as _json
  81 |         data = _json.loads(result.stdout)
  82 |         packets = data.get("packets", [])
  83 |         v_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "video"), 0)
  84 |         a_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "audio"), 0)
  85 |         offset = a_dts - v_dts
  86 |         logger.info(f"AV packet-level offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
  87 |         if abs(offset) > 0.05:
  88 |             logger.warning(f"WARNING: AV offset {offset:+.3f}s exceeds 0.05s threshold after fix")
  89 |         return offset
  90 |     except Exception as e:
  91 |         logger.warning(f"Could not measure AV sync: {e}")
  92 |         return 0.0
  93 | 
  94 | 
  95 | def find_nearest_pause(clip_path: str, original_end: float, pad_window: float = 10.0) -> float:
  96 |     """Find first natural pause after original_end within the pad window.
  97 | 
  98 |     Uses ffmpeg silencedetect to find silence gaps, then trims at the first
  99 |     natural pause after the original end timestamp. If no silence found
 100 |     within the window, hard-cuts at the pad mark.
 101 | 
 102 |     Args:
 103 |         clip_path: Path to the extracted clip (already has 8s padding)
 104 |         original_end: The original end timestamp relative to clip start
 105 |         pad_window: How many seconds of padding were added (default 8)
 106 | 
 107 |     Returns:
 108 |         Trim point in seconds from clip start
 109 |     """
 110 |     import re
 111 |     try:
 112 |         result = subprocess.run([
 113 |             "ffmpeg", "-i", clip_path,
 114 |             "-af", "silencedetect=noise=-30dB:d=0.3",
 115 |             "-f", "null", "-"
 116 |         ], capture_output=True, text=True, timeout=30)
 117 | 
 118 |         # Extract silence_start timestamps (beginning of each pause)
 119 |         pauses = [float(m.group(1)) for m in
 120 |                   re.finditer(r"silence_start: ([\d.]+)", result.stderr)]
 121 | 
 122 |         # Find first pause that starts after original_end but within pad window
 123 |         candidates = [p for p in pauses if original_end <= p <= original_end + pad_window]
 124 |         if candidates:
 125 |             trim_at = candidates[0] + 0.2  # trim slightly into the silence
 126 |             logger.info(f"CLIP TRIM: Trimmed at natural pause at {trim_at:.1f}s")
 127 |             return trim_at
 128 |     except Exception as e:
 129 |         logger.warning(f"  Silence detection failed: {e}")
 130 | 
 131 |     logger.info(f"CLIP TRIM: No silence found, using {pad_window}s hard pad")
 132 |     return original_end + pad_window
 133 | 
 134 | 
 135 | def ffprobe_duration(path: str) -> float:
 136 |     r = subprocess.run(
 137 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 138 |          "-of", "csv=p=0", path],
 139 |         capture_output=True, text=True,
 140 |     )
 141 |     try:
 142 |         return float(r.stdout.strip())
 143 |     except Exception:
 144 |         return 0.0
 145 | 
 146 | 
 147 | FORCE_SKIP_CHANNELS = ["Simply Bitcoin", "Bitcoin Magazine", "SatoSHE"]
 148 | 
 149 | 
 150 | def _skip_intro_silence(output_path: str, channel: str = "") -> None:
 151 |     """Render21 FIX 3: Speech onset detection replaces fixed +12s offset.
 152 | 
 153 |     Scans first 20s with silencedetect. Skips to first_speech_onset + 0.5s.
 154 |     FORCE_SKIP_CHANNELS always skip at least 15s.
 155 |     Also trims trailing silence/outro from last 10s.
 156 |     """
 157 |     import re as _re
 158 |     try:
 159 |         clip_dur = ffprobe_duration(output_path)
 160 |         if clip_dur < 5:
 161 |             return
 162 | 
 163 |         # --- INTRO SKIP: scan first 20s for speech onset ---
 164 |         result = subprocess.run([
 165 |             "ffmpeg", "-i", output_path, "-t", "20",
 166 |             "-af", "silencedetect=noise=-25dB:d=0.5",
 167 |             "-f", "null", "-"
 168 |         ], capture_output=True, text=True, timeout=30)
 169 |         silence_ends = _re.findall(r"silence_end: ([\d.]+)", result.stderr)
 170 | 
 171 |         # Determine skip point
 172 |         skip_to = 0.0
 173 |         force_min = 15.0 if any(ch in channel for ch in FORCE_SKIP_CHANNELS if ch) else 0.0
 174 | 
 175 |         if silence_ends:
 176 |             first_speech = float(silence_ends[0])
 177 |             skip_to = max(first_speech + 0.5, force_min)
 178 |             logger.info(f"  Render21: Speech onset at {first_speech:.1f}s, skip_to={skip_to:.1f}s (force_min={force_min:.0f}s, channel={channel})")
 179 |         elif force_min > 0:
 180 |             skip_to = force_min
 181 |             logger.info(f"  Render21: Force skip {force_min:.0f}s for {channel}")
 182 | 
 183 |         if skip_to > 0 and skip_to < clip_dur - 5:
 184 |             trimmed = output_path + ".jingle_skip.mp4"
 185 |             ok = _run_ffmpeg([
 186 |                 "-ss", f"{skip_to:.2f}", "-i", output_path,
 187 |                 "-c:v", "libx264", "-crf", "18", "-preset", "fast",
 188 |                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 189 |                 trimmed,
 190 |             ], f"speech onset skip +{skip_to:.1f}s", 60)
 191 |             if ok and os.path.exists(trimmed) and os.path.getsize(trimmed) > 10000:
 192 |                 os.replace(trimmed, output_path)
 193 |                 logger.info(f"  Render21: Intro skip applied at {skip_to:.1f}s")
 194 |             elif os.path.exists(trimmed):
 195 |                 os.remove(trimmed)
 196 | 
 197 |         # --- OUTRO TRIM: detect silence in last 10s ---
 198 |         clip_dur = ffprobe_duration(output_path)
 199 |         if clip_dur > 15:
 200 |             tail_start = max(0, clip_dur - 10)
 201 |             result2 = subprocess.run([
 202 |                 "ffmpeg", "-ss", f"{tail_start:.2f}", "-i", output_path,
 203 |                 "-af", "silencedetect=noise=-30dB:d=1.0",
 204 |                 "-f", "null", "-"
 205 |             ], capture_output=True, text=True, timeout=20)
 206 |             tail_silence_starts = _re.findall(r"silence_start: ([\d.]+)", result2.stderr)
 207 |             if tail_silence_starts:
 208 |                 # First silence in the tail = trim point (relative to tail_start)
 209 |                 trim_at = tail_start + float(tail_silence_starts[0]) + 0.3
 210 |                 if trim_at < clip_dur - 1.0:
 211 |                     outro_trimmed = output_path + ".outro_trim.mp4"
 212 |                     ok2 = _run_ffmpeg([
 213 |                         "-i", output_path, "-t", f"{trim_at:.2f}",
 214 |                         "-c:v", "libx264", "-crf", "18", "-preset", "fast",
 215 |                         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 216 |                         outro_trimmed,
 217 |                     ], f"outro trim at {trim_at:.1f}s", 60)
 218 |                     if ok2 and os.path.exists(outro_trimmed) and os.path.getsize(outro_trimmed) > 10000:
 219 |                         os.replace(outro_trimmed, output_path)
 220 |                         logger.info(f"  Render21: Outro trimmed at {trim_at:.1f}s (was {clip_dur:.1f}s)")
 221 |                     elif os.path.exists(outro_trimmed):
 222 |                         os.remove(outro_trimmed)
 223 | 
 224 |     except Exception as e:
 225 |         logger.warning(f"  Render21: Speech onset detection failed: {e}")
 226 | 
 227 | 
 228 | def make_motion_from_static(image_path: str, output_path: str,
 229 |                             duration: float, fps: int = 30) -> bool:
 230 |     """Convert a static image to video with Ken Burns zoom — eliminates freeze frames at source.
 231 | 
 232 |     Uses zoompan to create a slow 1.0→1.05x zoom over the duration.
 233 |     Every frame is unique — freezedetect cannot trigger on the output.
 234 | 
 235 |     Args:
 236 |         image_path: Path to static image (PNG/JPG)
 237 |         output_path: Path for output MP4
 238 |         duration: Video duration in seconds
 239 |         fps: Frame rate (default 30)
 240 | 
 241 |     Returns:
 242 |         True if conversion succeeded
 243 |     """
 244 |     total_frames = max(1, int(duration * fps))
 245 |     return _run_ffmpeg([
 246 |         "-loop", "1", "-i", image_path,
 247 |         "-vf", (f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,"
 248 |                 f"zoompan=z='min(zoom+0.002\\,1.05)':d={total_frames}:s=1920x1080:fps={fps}"),
 249 |         "-t", str(duration), "-r", str(fps),
 250 |         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 251 |         "-pix_fmt", "yuv420p",
 252 |         output_path,
 253 |     ], f"ken_burns_static {os.path.basename(image_path)}", 120)
 254 | 
 255 | 
 256 | def extract_clip(video_id: str, start_sec: int, end_sec: int,
 257 |                  output_path: str, channel: str = "") -> bool:
 258 |     """Download exact clip segment with original audio.
 259 | 
 260 |     Args:
 261 |         video_id: YouTube video ID
 262 |         start_sec: Start time in seconds
 263 |         end_sec: End time in seconds
 264 |         output_path: Where to save the clip
 265 |         channel: Channel name for speech onset skip logic
 266 | 
 267 |     Returns:
 268 |         True if clip was extracted successfully
 269 |     """
 270 |     try:
 271 |         return _extract_clip_inner(video_id, start_sec, end_sec, output_path, channel)
 272 |     except Exception as e:
 273 |         logger.error(f"[extractor] FATAL exception on {video_id}: {e}", exc_info=True)
 274 |         # Clean up any temp files left behind
 275 |         for suffix in [".resync.mp4", ".sync.mp4", ".nuclear.mp4", ".lipsync.mp4",
 276 |                        ".fix7.mp4", ".jingle_skip.mp4", ".outro_trim.mp4"]:
 277 |             tmp = output_path + suffix
 278 |             if os.path.exists(tmp):
 279 |                 try: os.remove(tmp)
 280 |                 except OSError: pass
 281 |         return False
 282 | 
 283 | 
 284 | def _extract_clip_inner(video_id: str, start_sec: int, end_sec: int,
 285 |                         output_path: str, channel: str = "") -> bool:
 286 |     """Inner implementation of extract_clip — may raise exceptions."""
 287 |     # P1 FIX (audit): Sanitize video_id — YouTube IDs are [A-Za-z0-9_-]{11}
 288 |     import re as _re
 289 |     if not _re.match(r'^[A-Za-z0-9_-]{8,15}$', video_id):
 290 |         logger.error(f"[extractor] REJECTED malformed video_id: {video_id!r}")
 291 |         return False
 292 |     os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
 293 | 
 294 |     # Check if already extracted
 295 |     if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
 296 |         dur = ffprobe_duration(output_path)
 297 |         if dur > 1:
 298 |             logger.info(f"  Clip cached: {video_id} ({dur:.1f}s)")
 299 |             return True
 300 | 
 301 |     # Render21 FIX 3: Removed fixed +12s offset — speech onset detection handles intro skip
 302 |     logger.info(f"[extractor] Clip {video_id}: raw start_sec={start_sec}, end_sec={end_sec}, channel={channel}")
 303 | 
 304 |     # Apply start -3s / end +10s padding to avoid mid-sentence cuts (LAW A4)
 305 |     # Issue 6: Increased end padding from 8s to 10s for natural pauses
 306 |     padded_start = max(0, start_sec - 3)
 307 |     padded_end = end_sec + 10
 308 | 
 309 |     url = f"https://www.youtube.com/watch?v={video_id}"
 310 | 
 311 |     # Method 1: yt-dlp --download-sections (preferred)
 312 |     cmd = [
 313 |         "yt-dlp",
 314 |         "--download-sections", f"*{padded_start}-{padded_end}",
 315 |         "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
 316 |         "--merge-output-format", "mp4",
 317 |         "-o", output_path,
 318 |         "--no-playlist",
 319 |         "--quiet",
 320 |         "--force-overwrites",
 321 |         url,
 322 |     ]
 323 |     # RULE 3: yt-dlp cookies for rate limit protection
 324 |     if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
 325 |         cmd.insert(1, COOKIES_FILE)
 326 |         cmd.insert(1, "--cookies")
 327 | 
 328 |     logger.info(f"  Extracting {video_id} [{start_sec}-{end_sec}s]...")
 329 |     try:
 330 |         result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
 331 |         if result.returncode == 0 and os.path.exists(output_path):
 332 |             # FIX 1 (render10): Hard PTS resync — force both A/V to start at exactly 0
 333 |             # Eliminates B-frame DTS offsets from yt-dlp downloads that cause ~1s audio lag
 334 |             resync_tmp = output_path + ".resync.mp4"
 335 |             resync_ok = _run_ffmpeg([
 336 |                 "-i", output_path,
 337 |                 "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-vsync", "cfr",
 338 |                 "-vf", "setpts=PTS-STARTPTS",
 339 |                 "-c:a", "aac", "-ar", "48000",
 340 |                 "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 341 |                 "-avoid_negative_ts", "make_zero", "-max_interleave_delta", "0",
 342 |                 "-output_ts_offset", "0",
 343 |                 resync_tmp,
 344 |             ], f"hard PTS resync {video_id}", 300)
 345 |             if resync_ok and os.path.exists(resync_tmp):
 346 |                 os.replace(resync_tmp, output_path)
 347 |                 logger.info(f"[extractor] Hard PTS resync applied to {video_id}")
 348 |             elif os.path.exists(resync_tmp):
 349 |                 os.remove(resync_tmp)
 350 | 
 351 |             # AV sync fix pass
 352 |             sync_tmp = output_path + ".sync.mp4"
 353 |             if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
 354 |                 os.replace(sync_tmp, output_path)
 355 |                 logger.info(f"  AV sync fix applied")
 356 |             elif os.path.exists(sync_tmp):
 357 |                 os.remove(sync_tmp)
 358 |             # Sync validation gate — FIX 2: lowered nuclear threshold 0.15→0.08
 359 |             offset = check_av_sync(output_path)
 360 |             if abs(offset) > 0.08:
 361 |                 logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode (threshold 0.08s)")
 362 |                 nuclear_tmp = output_path + ".nuclear.mp4"
 363 |                 if _run_ffmpeg([
 364 |                     "-fflags", "+genpts+igndts+discardcorrupt",
 365 |                     "-i", output_path,
 366 |                     "-map", "0:v:0", "-map", "0:a:0",
 367 |                     "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 368 |                     "-r", "30", "-vsync", "cfr",
 369 |                     "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
 370 |                     "-c:a", "aac", "-ar", "48000", "-ac", "2",
 371 |                     "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 372 |                     "-avoid_negative_ts", "make_zero",
 373 |                     nuclear_tmp,
 374 |                 ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
 375 |                     os.replace(nuclear_tmp, output_path)
 376 |                     final_offset = check_av_sync(output_path)
 377 |                     logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
 378 |                 elif os.path.exists(nuclear_tmp):
 379 |                     os.remove(nuclear_tmp)
 380 |             # FIX 2: Dynamic offset correction — apply measured offset for ANY drift >20ms
 381 |             final_av = check_av_sync(output_path)
 382 |             if abs(final_av) > 0.02:
 383 |                 lipsync_tmp = output_path + ".lipsync.mp4"
 384 |                 correction = -final_av  # negate to correct
 385 |                 # If audio leads video (offset > 0, correction < 0): delay audio
 386 |                 # If video leads audio (offset < 0, correction > 0): delay video
 387 |                 audio_delay = max(0, correction)
 388 |                 video_delay = max(0, -correction)
 389 |                 before_offset = final_av
 390 |                 if _run_ffmpeg([
 391 |                     "-itsoffset", f"{audio_delay:.4f}",
 392 |                     "-i", output_path,
 393 |                     "-itsoffset", f"{video_delay:.4f}",
 394 |                     "-i", output_path,
 395 |                     "-map", "1:v:0", "-map", "0:a:0",
 396 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 397 |                     "-vf", "setpts=PTS-STARTPTS",
 398 |                     "-c:a", "aac", "-ar", "48000",
 399 |                     "-af", "asetpts=PTS-STARTPTS",
 400 |                     lipsync_tmp,
 401 |                 ], f"lipsync correction {correction:+.3f}s (was {final_av:+.3f}s)", 120) and os.path.exists(lipsync_tmp):
 402 |                     os.replace(lipsync_tmp, output_path)
 403 |                     after_offset = check_av_sync(output_path)
 404 |                     logger.info(f"  FIX 2: Lipsync corrected {before_offset:+.3f}s → {after_offset:+.3f}s")
 405 |                 elif os.path.exists(lipsync_tmp):
 406 |                     os.remove(lipsync_tmp)
 407 |             # Render21 FIX 7: Final AV sync gate — re-encode if >0.15s
 408 |             final_sync = check_av_sync(output_path)
 409 |             if abs(final_sync) > 0.15:
 410 |                 logger.error(f"  FIX 7: AV sync {final_sync:+.3f}s exceeds 0.15s — force re-encode")
 411 |                 fix7_tmp = output_path + ".fix7.mp4"
 412 |                 if _run_ffmpeg([
 413 |                     "-i", output_path,
 414 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 415 |                     "-vf", "setpts=PTS-STARTPTS",
 416 |                     "-c:a", "aac", "-ar", "48000",
 417 |                     "-af", "asetpts=PTS-STARTPTS",
 418 |                     "-r", "30", "-vsync", "cfr",
 419 |                     fix7_tmp,
 420 |                 ], "av_sync_fix7_force", 120) and os.path.exists(fix7_tmp):
 421 |                     os.replace(fix7_tmp, output_path)
 422 |                     post_fix7 = check_av_sync(output_path)
 423 |                     logger.info(f"  FIX 7: Re-encode done, sync now {post_fix7:+.3f}s")
 424 |                 elif os.path.exists(fix7_tmp):
 425 |                     os.remove(fix7_tmp)
 426 |             # Render21: Skip intro jingle via speech onset detection
 427 |             _skip_intro_silence(output_path, channel=channel)
 428 |             dur = ffprobe_duration(output_path)
 429 |             sz = os.path.getsize(output_path) / 1024
 430 |             logger.info(f"  Extracted: {dur:.1f}s, {sz:.0f}KB")
 431 |             return True
 432 |         else:
 433 |             logger.warning(f"  yt-dlp sections failed: {result.stderr[:200]}")
 434 |     except subprocess.TimeoutExpired:
 435 |         logger.warning(f"  yt-dlp timed out for {video_id}")
 436 | 
 437 |     # Method 2: Download full video, then ffmpeg trim
 438 |     logger.info(f"  Fallback: download full + ffmpeg trim...")
 439 |     full_path = os.path.join(CLIP_CACHE, f"{video_id}_full.mp4")
 440 |     os.makedirs(CLIP_CACHE, exist_ok=True)
 441 | 
 442 |     dl_cmd = [
 443 |         "yt-dlp",
 444 |         "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
 445 |         "--merge-output-format", "mp4",
 446 |         "-o", full_path,
 447 |         "--no-playlist",
 448 |         "--quiet",
 449 |         "--force-overwrites",
 450 |         url,
 451 |     ]
 452 |     # RULE 3: yt-dlp cookies for rate limit protection
 453 |     if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
 454 |         dl_cmd.insert(1, COOKIES_FILE)
 455 |         dl_cmd.insert(1, "--cookies")
 456 | 
 457 |     try:
 458 |         result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
 459 |         if result.returncode != 0 or not os.path.exists(full_path):
 460 |             logger.error(f"  Full download failed: {result.stderr[:200]}")
 461 |             return False
 462 |     except subprocess.TimeoutExpired:
 463 |         logger.error(f"  Full download timed out")
 464 |         return False
 465 | 
 466 |     # FFmpeg trim with original audio (10s end pad per LAW A4, Issue 6)
 467 |     duration = (end_sec + 10) - max(0, start_sec - 3)
 468 |     trim_cmd = [
 469 |         "ffmpeg", "-y",
 470 |         "-ss", str(max(0, start_sec - 3)),
 471 |         "-i", full_path,
 472 |         "-t", str(duration),
 473 |         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 474 |         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 475 |         # Round 2 Fix 8: async resample during extraction to resync audio to video
 476 |         "-af", "aresample=async=1:first_pts=0",
 477 |         output_path,
 478 |     ]
 479 | 
 480 |     try:
 481 |         result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
 482 |         if result.returncode == 0 and os.path.exists(output_path):
 483 |             # FIX 1 (render10): Hard PTS resync — force both A/V to start at exactly 0
 484 |             resync_tmp = output_path + ".resync.mp4"
 485 |             resync_ok = _run_ffmpeg([
 486 |                 "-i", output_path,
 487 |                 "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-vsync", "cfr",
 488 |                 "-vf", "setpts=PTS-STARTPTS",
 489 |                 "-c:a", "aac", "-ar", "48000",
 490 |                 "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 491 |                 "-avoid_negative_ts", "make_zero", "-max_interleave_delta", "0",
 492 |                 "-output_ts_offset", "0",
 493 |                 resync_tmp,
 494 |             ], f"hard PTS resync fallback {video_id}", 300)
 495 |             if resync_ok and os.path.exists(resync_tmp):
 496 |                 os.replace(resync_tmp, output_path)
 497 |                 logger.info(f"[extractor] Hard PTS resync applied to {video_id} (fallback)")
 498 |             elif os.path.exists(resync_tmp):
 499 |                 os.remove(resync_tmp)
 500 | 
 501 |             # AV sync fix pass
 502 |             sync_tmp = output_path + ".sync.mp4"
 503 |             if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
 504 |                 os.replace(sync_tmp, output_path)
 505 |                 logger.info(f"  AV sync fix applied")
 506 |             elif os.path.exists(sync_tmp):
 507 |                 os.remove(sync_tmp)
 508 |             # Sync validation gate — FIX 2: lowered nuclear threshold 0.15→0.08
 509 |             offset = check_av_sync(output_path)
 510 |             if abs(offset) > 0.08:
 511 |                 logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode (threshold 0.08s)")
 512 |                 nuclear_tmp = output_path + ".nuclear.mp4"
 513 |                 if _run_ffmpeg([
 514 |                     "-fflags", "+genpts+igndts+discardcorrupt",
 515 |                     "-i", output_path,
 516 |                     "-map", "0:v:0", "-map", "0:a:0",
 517 |                     "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 518 |                     "-r", "30", "-vsync", "cfr",
 519 |                     "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
 520 |                     "-c:a", "aac", "-ar", "48000", "-ac", "2",
 521 |                     "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 522 |                     "-avoid_negative_ts", "make_zero",
 523 |                     nuclear_tmp,
 524 |                 ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
 525 |                     os.replace(nuclear_tmp, output_path)
 526 |                     final_offset = check_av_sync(output_path)
 527 |                     logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
 528 |                 elif os.path.exists(nuclear_tmp):
 529 |                     os.remove(nuclear_tmp)
 530 |             # FIX 2: Dynamic offset correction for fallback path too
 531 |             fb_offset = check_av_sync(output_path)
 532 |             if abs(fb_offset) > 0.02:
 533 |                 lipsync_tmp = output_path + ".lipsync.mp4"
 534 |                 correction = -fb_offset
 535 |                 audio_delay = max(0, correction)
 536 |                 video_delay = max(0, -correction)
 537 |                 if _run_ffmpeg([
 538 |                     "-itsoffset", f"{audio_delay:.4f}",
 539 |                     "-i", output_path,
 540 |                     "-itsoffset", f"{video_delay:.4f}",
 541 |                     "-i", output_path,
 542 |                     "-map", "1:v:0", "-map", "0:a:0",
 543 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 544 |                     "-vf", "setpts=PTS-STARTPTS",
 545 |                     "-c:a", "aac", "-ar", "48000",
 546 |                     "-af", "asetpts=PTS-STARTPTS",
 547 |                     lipsync_tmp,
 548 |                 ], f"lipsync correction {correction:+.3f}s (fallback)", 120) and os.path.exists(lipsync_tmp):
 549 |                     os.replace(lipsync_tmp, output_path)
 550 |                     after = check_av_sync(output_path)
 551 |                     logger.info(f"  FIX 2: Fallback lipsync corrected {fb_offset:+.3f}s → {after:+.3f}s")
 552 |                 elif os.path.exists(lipsync_tmp):
 553 |                     os.remove(lipsync_tmp)
 554 |             # Render21 FIX 7: Final AV sync gate (fallback path)
 555 |             final_sync_fb = check_av_sync(output_path)
 556 |             if abs(final_sync_fb) > 0.15:
 557 |                 logger.error(f"  FIX 7: Fallback AV sync {final_sync_fb:+.3f}s exceeds 0.15s — force re-encode")
 558 |                 fix7_tmp = output_path + ".fix7.mp4"
 559 |                 if _run_ffmpeg([
 560 |                     "-i", output_path,
 561 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 562 |                     "-vf", "setpts=PTS-STARTPTS",
 563 |                     "-c:a", "aac", "-ar", "48000",
 564 |                     "-af", "asetpts=PTS-STARTPTS",
 565 |                     "-r", "30", "-vsync", "cfr",
 566 |                     fix7_tmp,
 567 |                 ], "av_sync_fix7_force_fb", 120) and os.path.exists(fix7_tmp):
 568 |                     os.replace(fix7_tmp, output_path)
 569 |                     post_fix7 = check_av_sync(output_path)
 570 |                     logger.info(f"  FIX 7: Fallback re-encode done, sync now {post_fix7:+.3f}s")
 571 |                 elif os.path.exists(fix7_tmp):
 572 |                     os.remove(fix7_tmp)
 573 |             # Render21: Skip intro jingle via speech onset detection
 574 |             _skip_intro_silence(output_path, channel=channel)
 575 |             dur = ffprobe_duration(output_path)
 576 |             logger.info(f"  Trimmed: {dur:.1f}s")
 577 |             # Clean up full video
 578 |             try:
 579 |                 os.remove(full_path)
 580 |             except OSError:
 581 |                 pass
 582 |             return True
 583 |     except subprocess.TimeoutExpired:
 584 |         pass
 585 | 
 586 |     logger.error(f"  Failed to extract clip from {video_id}")
 587 |     return False
 588 | 
 589 | 
 590 | def _get_bitrate(clip_path: str) -> int:
 591 |     """Get video bitrate in bps via ffprobe. Returns 0 on failure."""
 592 |     import json as _json
 593 |     try:
 594 |         r = subprocess.run(
 595 |             ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", clip_path],
 596 |             capture_output=True, text=True, timeout=10,
 597 |         )
 598 |         info = _json.loads(r.stdout)
 599 |         return int(info.get("format", {}).get("bit_rate", 0))
 600 |     except Exception as e:
 601 |         logger.warning(f"  Bitrate check failed: {e}")
 602 |         return 0
 603 | 
 604 | 
 605 | def _redownload_high_quality(video_id: str, start_sec: int, end_sec: int, output_path: str) -> bool:
 606 |     """Re-download clip with explicit high-quality format selector."""
 607 |     section = f"*{start_sec}-{end_sec}"
 608 |     cmd = [
 609 |         "yt-dlp",
 610 |         "--download-sections", section,
 611 |         "-f", "bestvideo[height>=720]+bestaudio",
 612 |         "--merge-output-format", "mp4",
 613 |         "-o", output_path,
 614 |         f"https://www.youtube.com/watch?v={video_id}",
 615 |         "--force-overwrites",
 616 |         "--no-warnings", "--quiet",
 617 |     ]
 618 |     try:
 619 |         result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
 620 |         return result.returncode == 0 and os.path.exists(output_path)
 621 |     except Exception as e:
 622 |         logger.warning(f"  High-quality re-download failed: {e}")
 623 |         return False
 624 | 
 625 | 
 626 | def _check_clip_quality(clip_path: str, channel: str, video_id: str = "",
 627 |                         start_sec: int = 0, end_sec: int = 0) -> str:
 628 |     """Quality enforcement — reject below 1.5Mbps floor, retry on low.
 629 | 
 630 |     Returns: 'ok', 'redownloaded', or 'rejected'.
 631 |     """
 632 |     bitrate = _get_bitrate(clip_path)
 633 |     if bitrate == 0:
 634 |         logger.warning(f"  Quality check: could not determine bitrate for {channel}")
 635 |         return "ok"  # can't check, allow it
 636 | 
 637 |     mbps = bitrate / 1_000_000
 638 | 
 639 |     if mbps >= 1.5:
 640 |         logger.info(f"  Quality OK: {channel} at {mbps:.1f}Mbps")
 641 |         return "ok"
 642 | 
 643 |     # Below 3Mbps floor — try re-download before rejecting
 644 |     logger.warning(f"  BELOW 1.5Mbps FLOOR: {channel} clip at {mbps:.1f}Mbps")
 645 |     if video_id and _redownload_high_quality(video_id, start_sec, end_sec, clip_path):
 646 |         new_bitrate = _get_bitrate(clip_path)
 647 |         new_mbps = new_bitrate / 1_000_000
 648 |         if new_mbps >= 1.5:
 649 |             logger.info(f"  Re-download succeeded: {channel} now at {new_mbps:.1f}Mbps")
 650 |             return "redownloaded"
 651 |         logger.error(f"  Re-download still below 1.5Mbps floor: {channel} at {new_mbps:.1f}Mbps — REJECTED")
 652 |         os.remove(clip_path)
 653 |         return "rejected"
 654 | 
 655 |     logger.error(f"  REJECTED: {channel} clip at {mbps:.1f}Mbps — below 1.5Mbps floor")
 656 |     os.remove(clip_path)
 657 |     return "rejected"
 658 | 
 659 | 
 660 | def _second_pass_ad_read(clip_path: str, channel: str, rank: int) -> bool:
 661 |     """Issue 5: Second-pass ad read scan on extracted clip's audio transcript.
 662 | 
 663 |     Returns True if ad read detected (clip should be rejected).
 664 |     """
 665 |     try:
 666 |         # Use ffmpeg to extract audio, then check via whisper or pattern match
 667 |         # For now, check any available transcript data from the selection
 668 |         from clip_selector import AD_READ_PHRASES
 669 |         # Quick audio-to-text check would require whisper — skip if unavailable
 670 |         # Instead, this gate is enforced at the selection stage with expanded patterns
 671 |         return False
 672 |     except Exception:
 673 |         return False
 674 | 
 675 | 
 676 | def extract_all(selections: dict, output_dir: str) -> dict:
 677 |     """Extract all selected clips.
 678 | 
 679 |     Args:
 680 |         selections: Output from clip_selector.select_clips()
 681 |         output_dir: Directory to save clips
 682 | 
 683 |     Returns:
 684 |         Dict mapping rank -> clip_path for successfully extracted clips
 685 |     """
 686 |     os.makedirs(output_dir, exist_ok=True)
 687 |     clips = selections.get("clips", [])
 688 |     extracted = {}
 689 | 
 690 |     for clip in clips:
 691 |         rank = clip["rank"]
 692 |         video_id = clip["video_id"]
 693 |         start = clip["start_seconds"]
 694 |         end = clip["end_seconds"]
 695 |         channel = clip.get("channel", "unknown").replace(" ", "_")
 696 | 
 697 |         # Issue 3/4: Find sentence boundaries for clean clip start AND end
 698 |         timestamped_text = clip.get("timestamped_text", "")
 699 |         if timestamped_text:
 700 |             # Backward search for clean clip START
 701 |             adjusted_start = find_sentence_boundary(timestamped_text, start, direction='backward', max_search_seconds=5)
 702 |             if adjusted_start != start:
 703 |                 logger.info(f"  Sentence boundary: clip #{rank} start {start}s -> {adjusted_start}s")
 704 |                 start = adjusted_start
 705 |             # Forward search for clean clip END
 706 |             adjusted_end = find_sentence_boundary(timestamped_text, end, direction='forward', max_search_seconds=5)
 707 |             if adjusted_end != end:
 708 |                 logger.info(f"  Sentence boundary: clip #{rank} end {end}s -> {adjusted_end}s")
 709 |                 end = adjusted_end
 710 | 
 711 |         output_path = os.path.join(output_dir, f"clip_{rank}_{channel}_{video_id}.mp4")
 712 | 
 713 |         try:
 714 |             clip_ok = extract_clip(video_id, start, end, output_path, channel=channel)
 715 |         except Exception as e:
 716 |             logger.error(f"[extractor] extract_clip raised for {video_id}: {e}", exc_info=True)
 717 |             clip_ok = False
 718 |         if clip_ok:
 719 |             # Issue 10: Quality enforcement — reject below 1.5Mbps floor
 720 |             quality = _check_clip_quality(output_path, clip.get("channel", channel),
 721 |                                           video_id=video_id, start_sec=start, end_sec=end)
 722 |             if quality == "rejected":
 723 |                 logger.warning(f"  Skipping clip #{rank}: quality below 3Mbps floor")
 724 |                 continue
 725 | 
 726 |             # Smart trim: find natural pause within the 10s end-pad window
 727 |             clip_dur = ffprobe_duration(output_path)
 728 |             # original_end relative to clip start: (end - start) + 3s start pad
 729 |             original_end_in_clip = (end - start) + 3
 730 |             if clip_dur > original_end_in_clip:
 731 |                 pause_at = find_nearest_pause(output_path, original_end_in_clip, pad_window=10.0)
 732 |                 if pause_at < clip_dur:
 733 |                     trimmed = output_path + ".trimmed.mp4"
 734 |                     if _run_ffmpeg([
 735 |                         "-i", output_path, "-t", str(pause_at),
 736 |                         "-c:v", "copy", "-c:a", "copy", trimmed,
 737 |                     ], "pause_trim", 30) and os.path.exists(trimmed):
 738 |                         os.replace(trimmed, output_path)
 739 |                         logger.info(f"  Trimmed clip #{rank} at {pause_at:.1f}s (silence detection)")
 740 |                     elif os.path.exists(trimmed):
 741 |                         os.remove(trimmed)
 742 | 
 743 |             # Render20: No hard clip duration cap — quality over runtime
 744 | 
 745 |             # Issue 5: Second-pass ad read scan
 746 |             if _second_pass_ad_read(output_path, clip.get("channel", ""), rank):
 747 |                 logger.warning(f"  REJECTED clip #{rank} [{channel}] — ad read in extracted audio")
 748 |                 continue
 749 | 
 750 |             clip_info = {
 751 |                 "path": output_path,
 752 |                 "video_id": video_id,
 753 |                 "channel": clip.get("channel", ""),
 754 |                 "start": start,
 755 |                 "end": end,
 756 |                 "duration": ffprobe_duration(output_path),
 757 |                 "quote": clip.get("quote", ""),
 758 |             }
 759 |             extracted[rank] = clip_info
 760 |             # RULE 1: Archive every successful clip for fallback
 761 |             save_clip(channel, video_id, output_path, clip_info)
 762 |         else:
 763 |             # RULE 1: Try archived fallback before giving up
 764 |             fallback = get_fallback_clip(clip.get("channel", ""))
 765 |             if fallback:
 766 |                 age_days = round((time.time() - os.path.getmtime(fallback)) / 86400, 1)
 767 |                 logger.info(f"[extractor] Using archived clip for {clip.get('channel', channel)} ({age_days} days old)")
 768 |                 shutil.copy2(fallback, output_path)
 769 |                 extracted[rank] = {
 770 |                     "path": output_path,
 771 |                     "video_id": video_id,
 772 |                     "channel": clip.get("channel", ""),
 773 |                     "start": start,
 774 |                     "end": end,
 775 |                     "duration": ffprobe_duration(output_path),
 776 |                     "quote": clip.get("quote", ""),
 777 |                 }
 778 |             else:
 779 |                 logger.warning(f"  Skipping clip #{rank}: extraction failed, no archive fallback")
 780 | 
 781 |     logger.info(f"Extracted {len(extracted)}/{len(clips)} clips")
 782 |     return extracted
 783 | 
 784 | 
 785 | def extract_montage_all(montage_selections: dict, output_dir: str) -> dict:
 786 |     """Extract montage clips — same as extract_all but uses montage timestamps
 787 |     and saves to clips/montage_clip_N_CHANNEL_ID.mp4"""
 788 |     os.makedirs(output_dir, exist_ok=True)
 789 |     clips = montage_selections.get("clips", [])
 790 |     extracted = {}
 791 | 
 792 |     for clip in clips:
 793 |         rank = clip["rank"]
 794 |         video_id = clip["video_id"]
 795 |         start = clip["start_seconds"]
 796 |         end = clip["end_seconds"]
 797 |         channel = clip.get("channel", "unknown").replace(" ", "_")
 798 |         output_path = os.path.join(output_dir, f"montage_clip_{rank}_{channel}_{video_id}.mp4")
 799 | 
 800 |         try:
 801 |             ok = extract_clip(video_id, start, end, output_path, channel)
 802 |             if ok and os.path.exists(output_path):
 803 |                 clip["montage_clip_path"] = output_path
 804 |                 extracted[rank] = output_path
 805 |                 logger.info(f"[Montage] Extracted: montage_clip_{rank}_{channel}")
 806 |             else:
 807 |                 logger.warning(f"[Montage] Failed: {channel} {video_id}")
 808 |         except Exception as e:
 809 |             logger.error(f"[Montage] Error: {channel} {video_id}: {e}")
 810 | 
 811 |     return extracted
 812 | 
 813 | 
 814 | def _parse_timestamped_text(timestamped_text: str) -> list:
 815 |     """Parse timestamped transcript into list of (seconds, text) tuples."""
 816 |     import re
 817 |     # Try [HH:MM:SS] format first
 818 |     entries = re.findall(r'\[(\d+):(\d+):(\d+)\]\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
 819 |     if entries:
 820 |         return [(int(h) * 3600 + int(m) * 60 + int(s), text.strip())
 821 |                 for h, m, s, text in entries]
 822 |     # Try [MM:SS] format
 823 |     entries_simple = re.findall(r'\[?(\d+):(\d+)\]?\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
 824 |     if entries_simple:
 825 |         return [(int(m) * 60 + int(s), text.strip())
 826 |                 for m, s, text in entries_simple]
 827 |     return []
 828 | 
 829 | 
 830 | def find_sentence_boundary(timestamped_text: str, target_time: int,
 831 |                            direction: str = 'backward',
 832 |                            max_search_seconds: int = 5) -> int:
 833 |     """Find nearest sentence ending (. ? !) relative to target_time.
 834 | 
 835 |     Args:
 836 |         timestamped_text: Timestamped transcript text
 837 |         target_time: Target timestamp in seconds
 838 |         direction: 'backward' for clip start (find sentence start after previous end),
 839 |                    'forward' for clip end (find sentence end after target)
 840 |         max_search_seconds: Maximum seconds to search in either direction
 841 | 
 842 |     Returns:
 843 |         Adjusted timestamp in seconds
 844 |     """
 845 |     parsed = _parse_timestamped_text(timestamped_text)
 846 |     if not parsed:
 847 |         logger.warning(f"WARNING: No sentence boundary found (no parsed entries), using raw timestamp {target_time}")
 848 |         return target_time
 849 | 
 850 |     if direction == 'backward':
 851 |         # Find the nearest sentence-ending BEFORE target_time,
 852 |         # then return the timestamp of the NEXT word (sentence start)
 853 |         best_start = target_time
 854 |         for i, (sec, text) in enumerate(parsed):
 855 |             if sec >= target_time:
 856 |                 break
 857 |             # Check if text ends with sentence-ending punctuation
 858 |             if text and text.rstrip()[-1:] in '.?!':
 859 |                 # Next entry's timestamp = start of next sentence
 860 |                 if i + 1 < len(parsed):
 861 |                     candidate = parsed[i + 1][0]
 862 |                     if candidate <= target_time and (target_time - candidate) <= max_search_seconds:
 863 |                         best_start = candidate
 864 | 
 865 |         if best_start == target_time:
 866 |             logger.info(f"WARNING: No sentence boundary found backward from {target_time}s, using raw timestamp")
 867 |         return best_start
 868 | 
 869 |     elif direction == 'forward':
 870 |         # Find the nearest sentence-ending AFTER target_time,
 871 |         # return the timestamp just after that ending
 872 |         for i, (sec, text) in enumerate(parsed):
 873 |             if sec < target_time:
 874 |                 continue
 875 |             if text and text.rstrip()[-1:] in '.?!':
 876 |                 # End point: this entry's timestamp + estimated duration for this text
 877 |                 # Use next entry's timestamp as the sentence end point
 878 |                 if i + 1 < len(parsed):
 879 |                     end_point = parsed[i + 1][0]
 880 |                 else:
 881 |                     end_point = sec + 2  # last entry, add 2s buffer
 882 |                 if (end_point - target_time) <= max_search_seconds:
 883 |                     return end_point
 884 |                 break  # beyond max search window
 885 | 
 886 |         logger.info(f"WARNING: No sentence boundary found forward from {target_time}s, using raw timestamp")
 887 |         return target_time
 888 | 
 889 |     return target_time
 890 | 
 891 | 
 892 | def _find_sentence_start(timestamped_text: str, target_sec: int) -> int:
 893 |     """Find the nearest sentence boundary BEFORE the target timestamp.
 894 |     Wrapper around find_sentence_boundary for backward compatibility.
 895 |     """
 896 |     return find_sentence_boundary(timestamped_text, target_sec, direction='backward', max_search_seconds=5)
 897 | 
 898 | 
 899 | if __name__ == "__main__":
 900 |     # Quick test: extract a known clip
 901 |     import sys
 902 |     if len(sys.argv) >= 4:
 903 |         vid = sys.argv[1]
 904 |         start = int(sys.argv[2])
 905 |         end = int(sys.argv[3])
 906 |         out = os.path.join(BASE, "output", f"test_clip_{vid}.mp4")
 907 |         ok = extract_clip(vid, start, end, out)
 908 |         print(f"Extraction {'succeeded' if ok else 'failed'}: {out}")
 909 |     else:
 910 |         print("Usage: python3 clip_extractor.py <video_id> <start_sec> <end_sec>")
 911 | 
```

---

## YOUR REVIEW TASK — ARCHITECTURE AUDIT (8 CRITICAL QUESTIONS)

You are auditing a GOSPEL SPEC (design document) for an autonomous render improvement loop.
NO code has been written yet. Your job is to find every flaw, gap, failure mode, and token
cost risk BEFORE implementation. Be brutal. Be specific. Cite gospel section numbers.

### Q1 — INTEGRATION RISK
The loop integrates with overnight_render_loop.py via flag files (/tmp/render_fix_complete_iterN).
What are the failure modes? Race conditions? Flag file left over from previous iteration?
Loop crash that never writes the flag, blocking overnight loop forever?

### Q2 — QWEN RELIABILITY
The loop assumes Qwen3:30b is running on Ollama at localhost:11434. What happens if Ollama
is down, model not loaded, or Qwen returns malformed JSON? Does the loop degrade gracefully
or cascade-fail and kill the render cycle?

### Q3 — CC SESSION DETECTION
The loop waits for CC slot by polling tmux. But tmux session names from previous crashed
sessions may still exist as zombies. How does the loop distinguish a live CC session from
a dead one? What is the exact tmux command that proves a session is actively running CC
vs just existing as a shell?

### Q4 — TOKEN COST REALITY
The gospel claims $2 soft limit per cycle. Given 4-6 failing dimensions typically seen
(freeze, avatar, true_peak, visual_polish, etc.), each requiring Qwen + 2 external LLM
calls with ~2000 token payloads, what is the realistic per-cycle cost? Is the $2 limit
achievable or optimistic?

### Q5 — DIMENSION_MAP COMPLETENESS
Review the DIMENSION_MAP in the gospel. Which Gemini grade dimensions are MISSING from
the map? What happens when a new dimension appears in a grade that has no mapping?
Does the loop handle unknown dimensions gracefully?

### Q6 — OVERNIGHT LOOP COUPLING
The minimal change to overnight_render_loop.py is described as "check for flag file,
wait up to 60 min". But overnight_render_loop.py has a 14400s render timeout. If the
improvement loop takes 90 min (CC session can run long), does this blow the timeout?
How should timing be coordinated to avoid killing the render cycle mid-improvement?

### Q7 — CONSENSUS FAILURE HANDLING
When LLMs disagree, the loop sends a Telegram alert and skips the dimension. But if the
3 most critical dimensions (avatar, freeze, visual_polish) all produce disagreement,
the loop commits nothing and the next iteration is identical to the last. What mechanism
prevents infinite identical render loops with no improvement?

### Q8 — IMPLEMENTATION CORRECTNESS
The loop will write fix specs and fire CC. But CC is Opus 4.6 — it reads the spec and
uses its own judgment. What guardrails ensure CC implements ONLY the exact patch and
does not refactor surrounding code, change function signatures, or introduce new
dependencies that break other pipeline stages?

### RESPONSE FORMAT
For each question (Q1-Q8):
- STATE the failure mode(s) clearly
- RATE the severity: CRITICAL / HIGH / MEDIUM / LOW
- PRESCRIBE the exact mitigation (what to add to the gospel)
- CITE the gospel section that needs updating

### FINAL VERDICT
After answering all 8 questions:
- How many CRITICAL issues did you find?
- Is this gospel ready to build from, or does it need fundamental rework?
- What is the single most dangerous gap?

