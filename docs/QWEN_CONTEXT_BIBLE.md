# QWEN AUTONOMOUS REPAIR CONTEXT BIBLE
# Protocol Pulse — Ultron Server — Auto-injected into every watchdog repair session
# Last updated: 2026-03-22
# DO NOT EDIT MANUALLY — updated by watchdog after every successful repair

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1: ARCHITECTURE MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE FLOW (in order):
  daily_producer.py --skip-scan
    → clip_selector.py         (selects best YouTube clips via Claude)
    → clip_extractor.py        (downloads clips via yt-dlp)
    → script_writer.py         (generates dialogue via Claude Sonnet)
    → tts_engine.py            (ElevenLabs PBX voice + Kokoro fallback)
    → assembler.py             (FFmpeg assembly — 1800+ lines)
    → gemini_grade.py          (Gemini grades 24 dimensions)
  overnight_render_loop.py     (orchestrates: render → forensics → grade → CC fix → repeat)
  services/local_watchdog.py   (monitors every 60s, auto-repairs, spawns CC sessions)

KEY FILES AND OWNERS:
  ~/protocol_pulse/video_pipeline_v3/
    daily_producer.py     — orchestrates all pipeline steps
    script_writer.py      — generates dialogue JSON from clips
    tts_engine.py         — text-to-speech, ElevenLabs primary
    assembler.py          — FFmpeg video assembly (COMPLEX — touch carefully)
    clip_selector.py      — Claude selects best clip moments
    clip_extractor.py     — yt-dlp downloads, also montage clips
    gemini_grade.py       — Gemini grades finished video
  ~/protocol_pulse/
    overnight_render_loop.py   — main render loop daemon
    services/local_watchdog.py — autonomous watchdog (this file)
    services/morning_brief.py  — morning intel brief (Qwen primary, Haiku fallback)
    services/tweet_machine.py  — tweet posting (GPT-4o)
    .env                       — API keys (NEVER TOUCH)

RUNTIME FILES (generated per render):
  /tmp/producer_debug.log           — STEP-by-step producer output + tracebacks
  video_pipeline_v3/logs/overnight_loop.log — loop orchestration log
  video_pipeline_v3/output/YYYY-MM-DD/
    script.json                     — generated dialogue
    selections.json                 — chosen clips
    audio/                          — per-line TTS audio files
    work/                           — assembled video segments
    pulse_check_YYYYMMDD.mp4        — final output
  /tmp/render_context_YYYYMMDD.json — PER-RENDER QWEN CONTEXT FILE (see Section 7)

GPU ALLOCATION (SACRED — never change):
  GPU 0: Kokoro TTS (render pipeline)
  GPU 1: F5-TTS / BigVGAN2 (render pipeline)
  GPU 2: Qwen3-Coder:30b via Ollama port 11435 (watchdog — THIS IS YOU)
  GPU 3: Free for escalation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2: SACRED LAWS (never violate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. AUDIT FIRST: cross_llm_audit.py fires before any fix. No exceptions.
2. REGRESSION: bash regression_test.sh must show 0 FAILs before any commit.
3. ONE SESSION: never run parallel CC sessions on same repo.
4. NO RELAY PATCHES: fixes go through CC sessions only.
5. NO .FORMAT() ON USER CONTENT: always use .replace() in script_writer.py
6. PIPELINE_LAWS.md is gospel: load into every CC session touching pipeline.
7. NEVER TOUCH: .env, PIPELINE_LAWS.md, VISUAL_DESIGN_SYSTEM.md, gospels/
8. GIT: every fix = git add + commit + push from Ultron.
9. HOTFIX_EXEMPT=1 to bypass pre-commit hook when needed urgently.
10. PYC: always delete all .pyc after any fix before restarting.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3: KNOWN FAILURE PATTERNS (root causes + fixes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERN: KeyError: 'Name' (or any {word}) in script_writer.py
ROOT CAUSE: .format() called on SCRIPT_PROMPT or NARRATIVE_INJECTION while
  user content (tweets, clip quotes) contains {curly braces}
FIX: Replace ALL .format() calls in script_writer.py with .replace() chains:
  prompt = (SCRIPT_PROMPT
    .replace('{clips_info}', str(clips_info))
    .replace('{btc_price}', str(btc_price))
    .replace('{social_posts}', str(social_posts))
    .replace('{live_context}', str(live_context))
  )
  AND for NARRATIVE_INJECTION — same pattern, .replace() for each variable
VERIFY: grep -c '.format(' script_writer.py should return 0
STALE PYC WARNING: always delete .pyc after fixing script_writer.py

PATTERN: 31/14/5/4 freeze frames in video
ROOT CAUSE: stream_loop=-1 on video inputs causes PTS timestamp discontinuities
  at loop boundaries. FFmpeg freezedetect flags these as freeze frames.
FIX: Add trim=0:{total_dur},setpts=PTS-STARTPTS immediately after any video
  stream_loop=-1 input before scale filter:
  f"[{idx}:v]trim=0:{total_dur},setpts=PTS-STARTPTS,scale=..."
LOCATIONS: _get_bg_layer(), make_pip_scene(), make_narrator_pip_scene()
NOTE: Audio stream_loops (music) do NOT cause freeze frames — skip those.

PATTERN: 4+ silence gaps >0.8s in audio
ROOT CAUSE: ElevenLabs API latency between sequential TTS calls stacks up.
  Also: 0.3s inter-line silence too long for ElevenLabs (which has natural pauses).
FIX: Reduce inter-line silence to 0.1s when TTS_PROVIDER=elevenlabs.
  Add retry logic: if ElevenLabs fails, wait 2s and retry once, then fall back to Kokoro.
  Add leading silence trim: silenceremove=start_periods=1:start_threshold=-40dB

PATTERN: Render loop dies in forensics (loop process terminated)
ROOT CAUSE: subprocess.TimeoutExpired not caught in run() function — bubbles up
  and kills the entire overnight_render_loop process.
FIX: Wrap run() in try/except subprocess.TimeoutExpired — return failed result.
  Also wrap run_forensics() and grade_with_gemini() in try/except in main loop.

PATTERN: Loop stops after 6h without Grade A, sleeps until 8am next day
ROOT CAUSE: daemon mode calls sleep_until_next_8am_et() unconditionally after
  every cycle regardless of grade outcome.
FIX: Only call sleep_until_next_8am_et() if verdict == "PASS" (Grade A).
  Otherwise: time.sleep(1800) and retry.

PATTERN: Social segment never appears in episodes
ROOT CAUSE: get_todays_social_posts() called AFTER generate_from_clips() —
  Claude generates script without seeing tweet data, skips social segment.
FIX: Move social fetch to BEFORE generate_from_clips() call in daily_producer.py.
  Pass as parameter: generate_from_clips(..., social_posts_sorted=sorted_social)

PATTERN: Space tap never appears in episodes
ROOT CAUSE 1: TIER1_HANDLES in x_spaces_scraper/scraper.py missing quotes —
  {martybent,...} causes NameError on import, scraper never ran.
FIX: Add quotes: {"martybent","stephanlivera",...}
ROOT CAUSE 2: No active X Space in monitoring window.
NORMAL: Space tap only appears when a qualifying space is live/recent.

PATTERN: TTS reads [pause], [breath], [emphasis] aloud
ROOT CAUSE: prosody_plan() in tts_engine.py calls Claude to add SSML markers
  that Kokoro reads literally as words.
FIX: Disable prosody_plan() — strip all [bracket] markers, return clean text:
  import re; return re.sub(r'\[.*?\]', '', text).strip()

PATTERN: FATAL: no output file produced
ROOT CAUSE: assembler.py crashed silently before writing final output.
  Often caused by missing work/ directory or stale pyc importing broken assembler.
FIX: Delete work/ directory, clear all .pyc, git pull, restart loop.

PATTERN: Multiple daily_producer processes running simultaneously
ROOT CAUSE: Previous render didn't clean up properly, new render spawned on top.
FIX: pkill -f daily_producer && sleep 3 before any restart.

PATTERN: Watchdog reports "all clear" while render is crashing
ROOT CAUSE (FIXED 2026-03-22): Watchdog only scanned overnight_loop.log —
  KeyError tracebacks live in /tmp/producer_debug.log which it never read.
FIX: Added producer_debug.log scan to reactive check.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4: GRADE A CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Target: score >= 88, zero critical failures, broadcast_ready=true
Critical failure triggers (any one = F grade):
  - freeze_check: >1 freeze frame detected (threshold n=0.003:d=1.5)
  - no_artifacts: any severe visual artifact
  - silence_check: >1 mid-video silence gap >0.8s
  - audio_quality: clipping or severe loudness issues
  - duration_check: under 7 minutes

Target metrics:
  - Duration: 8-12 minutes
  - Loudness: -16 to -14 LUFS integrated
  - True peak: <= -1.0 dBFS
  - Resolution: 1920x1080 @ 30fps
  - Segments: cold_open, 4-5 clip setups, social_segment, wrap

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5: OFF-LIMITS (never modify without explicit instruction)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ~/protocol_pulse/.env (API keys)
- ~/protocol_pulse/docs/gospels/*.md (gospel documents)
- ~/protocol_pulse/docs/PIPELINE_LAWS.md
- ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md
- Any file outside ~/protocol_pulse/ (system files)
- GPU allocation (GPUs 0,1 are for TTS render — never reassign)
- Ollama port 11435 (Qwen on GPU 2 — that's you)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6: FIX PROTOCOL (follow every time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Read the affected file fully before touching anything
2. Run cross_llm_audit.py on affected files (Gemini+GPT-4o+Grok)
3. Implement ONLY what audit consensus confirms broken
4. python3 -m py_compile [file] — syntax check
5. bash regression_test.sh — must show 0 FAILs
6. find ~/protocol_pulse -name "*.pyc" -delete
7. git add + commit + push
8. echo WATCHDOG_FIX_COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7: PER-RENDER CONTEXT FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
At the start of every render, daily_producer.py writes:
  /tmp/render_context_YYYYMMDD.json

This file contains:
  - episode_date: today's date
  - episode_title: the selected episode title
  - clips: [{channel, title, duration, score}] — what clips were selected
  - btc_price: BTC price at render time
  - mood: tense/bullish/neutral
  - music_track: which Suno track selected
  - tts_provider: elevenlabs or local
  - steps_completed: [1,2,3...] — which steps finished successfully
  - steps_failed: [{step, error, timestamp}] — what failed and when
  - social_posts_count: how many tweets available for social segment
  - space_tap_available: true/false
  - render_start_time: ISO timestamp
  - iteration: which loop iteration this is (1-8)
  - previous_grades: last 3 grades for context

When the watchdog detects a crash, it reads this file and includes it
in the CC repair prompt so Claude Code knows exactly what was being built.

FORMAT EXAMPLE:
{
  "episode_date": "2026-03-22",
  "episode_title": "Bitcoin Chart Signals Move to $85K",
  "clips": [
    {"channel": "TheStreet", "duration": 40.9, "score": 117},
    {"channel": "Bitcoin Magazine Pro", "duration": 26.8, "score": 100}
  ],
  "btc_price": "68650",
  "mood": "tense",
  "tts_provider": "elevenlabs",
  "steps_completed": [1, 2, 3, 4],
  "steps_failed": [{"step": 5, "error": "KeyError: Name", "timestamp": "..."}],
  "social_posts_count": 5,
  "space_tap_available": false,
  "iteration": 1,
  "previous_grades": ["F(77)", "F(76)", "D(76)"]
}

PATTERN: KeyError persists even after .format() replaced with .replace() in source
ROOT CAUSE: Git worktrees at /home/ultron/worktrees/ have their own __pycache__
  with stale script_writer.cpython-310.pyc compiled from old .format() code.
  Python imports this cached bytecode instead of recompiling from source.
  Also: PYTHONDONTWRITEBYTECODE not set, so new .pyc files get written on each run.
FIX:
  1. find /home/ultron -name "script_writer*.pyc" -delete
  2. export PYTHONDONTWRITEBYTECODE=1 (add to ~/.bashrc permanently)
  3. Verify script_writer.py line 1: import sys; sys.dont_write_bytecode = True
  4. Restart render loop
VERIFY: find /home/ultron -name "script_writer*.pyc" 2>/dev/null should return empty
WORKTREE LOCATIONS: /home/ultron/worktrees/cc_s2_articles/
                    /home/ultron/worktrees/cc_s5_alerts/

WATCHDOG ACTION FOR THIS PATTERN:
  When KeyError persists after source file looks clean:
  1. Run: find /home/ultron -name "*.pyc" -delete
  2. Run: pkill -f daily_producer
  3. Restart render loop with PYTHONDONTWRITEBYTECODE=1
  Do NOT launch CC session — this is a cache issue, not a code issue.
PATTERN: pyc stale cache KeyError — STATUS: PERMANENTLY CLOSED. sys.dont_write_bytecode=True in overnight_render_loop.py + daily_producer.py at startup. Cannot recur. Watchdog action: none needed.
## INTELLIGENCE TERMINAL PHASE 1 — 2026-03-23

BUG 1: `services.sentinel` import fails inside blueprints/intelligence.py
  ROOT CAUSE: Two `services/` packages exist — `core/services/` (has __init__.py) and
  project-root `services/` (also has __init__.py). When gunicorn runs from `core/`,
  `from services.sentinel import ...` resolves to `core/services/sentinel` which doesn't
  exist. Python's `sys.path.insert(0, project_root)` doesn't help because `core/services`
  is already loaded as the `services` package.
  FIX: Use `importlib.util.spec_from_file_location()` to load sentinel.py by absolute
  file path, bypassing the package resolution entirely.
  VERIFY: `curl -s http://localhost:5000/api/intelligence/state/public | python3 -m json.tool`

BUG 2: `/intelligence` route conflict with routes.py Session 12
  ROOT CAUSE: routes.py line 3060 had `@app.route('/intelligence')` which was registered
  before the blueprint, so Flask served the old page.
  FIX: Changed old route to `/intelligence/legacy`, freeing the path for the blueprint.
  VERIFY: `curl -s http://localhost:5000/intelligence | grep -c "Intelligence Terminal"`

PATTERN: Render loop starts but daily_producer never spawns — flock blocked. ROOT CAUSE: golden_path.py CHECK 4 tests flock by spawning two producers; if golden_path is killed mid-test, the lock file /tmp/daily_producer.lock stays held. FIX: fuser -k /tmp/daily_producer.lock && rm -f /tmp/daily_producer.lock, then restart loop. PREVENTION: golden_path.py CHECK 4 must clean up lock in finally: block. WATCHDOG ACTION: If daily_producer never starts within 60s of RENDER START, check fuser /tmp/daily_producer.lock and kill holder.

BUG 3: Gunicorn started from wrong working directory
  ROOT CAUSE: Two app.py files exist — ~/protocol_pulse/app.py (legacy root-level)
  and ~/protocol_pulse/core/app.py (active app with all blueprints). CC restarted
  gunicorn from ~/protocol_pulse/ root, loading the wrong app. Intelligence blueprint
  and all core/ blueprints invisible. Site returns wrong routes.
  FIX: Always start gunicorn from ~/protocol_pulse/core/:
    cd ~/protocol_pulse/core && gunicorn ... app:app
  NEVER run gunicorn from ~/protocol_pulse/ root — it loads the legacy app.
  VERIFY: ls /proc/12/cwd -la
    should show -> /home/ultron/protocol_pulse/core
  WATCHDOG ACTION: If /intelligence returns 404 or wrong page, check gunicorn cwd first.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CONVERGENCE DETECTION BUILD -- 2026-03-23
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES CREATED:
  services/signal_feeds.py     — 8 async feed fetchers (VIX, SPY, WTI, Deribit, Stablecoin, HodlHodl, RSS, Custodian)
  services/baseline_store.py   — Rolling 30-day SQLite store (WAL mode, check_same_thread=False)
  services/convergence_engine.py — State machine (IDLE→WATCH→ALERT→CRITICAL), SignalExtractor, PatternEvaluator
  data/convergence_config.yaml — All thresholds externalized (patterns, feeds, contradictions, state machine)
  data/custodian_wallets.json  — ETF custodian wallet addresses for flow monitoring
  data/miner_wallets.json      — Mining pool payout addresses for capitulation detection

FILES MODIFIED:
  services/config_loader.py    — Added ConvergenceConfig class (YAML loader, thread-safe, hot-reload, startup validation)
  services/sentinel.py         — Added convergence field to SentinelState, ConvergenceEngine runs every 60s in main loop
  core/blueprints/intelligence.py — Convergence state included in SSE stream (auth + public)
  core/templates/intelligence_terminal.html — Convergence Matrix panel (state, signals, patterns, contradiction indicator)

BUGS FIXED (from audit):
  BUG-2: All signal_feeds.py fetchers are async (no requests.get anywhere)
  BUG-3: SQLite WAL mode + synchronous=NORMAL + busy_timeout=10000 + check_same_thread=False on every connection
  BUG-4: Explicit ClientTimeout on every fetcher
  BUG-5: Yahoo Finance fallback to Alpha Vantage for VIX + SPY
  BUG-6: All thresholds from convergence_config.yaml — no hardcoded fallbacks, startup validation rejects incomplete config
  IMP-1: aiohttp session injected from sentinel.py, not created per-cycle
  IMP-2: Per-feed circuit breaker (3 failures → 5min cooldown)
  IMP-5: Contradiction gate blocks escalation when contradictions detected
  IMP-7: SSE payload versioning (schema_version: 1)

STATE MACHINE RULES:
  IDLE→WATCH only. WATCH→IDLE or ALERT. ALERT→WATCH or CRITICAL. CRITICAL→ALERT or IDLE.
  IDLE→CRITICAL raises ValueError (no skip). Contradiction gate forces step-down to WATCH.
  minimum_confirmation_window must pass before escalation (per-pattern, 1h–12h).

SIGNAL FRESHNESS:
  decay_onset: 3600s (1h). max_valid_age: 7200s (2h). Linear decay between onset and max.
  Expired signals (age >= max_valid_age) excluded from pattern evaluation.

ALL 9 TESTS PASSED.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PRE-FLIGHT QC LOOP — 2026-03-23
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERN: Pre-flight QC loop
PURPOSE: Ensures grading never sees a video with freeze frames/silence/loudness issues.
  Saves 45-90 min per failed render by catching issues before Gemini grading.
LOCATION: daily_producer.py run_preflight_qc() called after Step 7 (assembly) before Step 8.
  Wired as Step 7b with up to 3 attempts and auto-fix between each attempt.
THRESHOLDS: 0 freeze frames (freezedetect n=0.003:d=1.5), 0 silence gaps >0.8s in middle 80%,
  LUFS -17 to -12 integrated, true peak <= -1.0 dBTP, 7-15 min duration, 1920x1080 resolution.
AUTO-FIX:
  freeze_frames → full video re-encode with -r 30 -vsync cfr + setpts reset
  silence_gaps → silenceremove filter + apad
  loudness → loudnorm=I=-14:TP=-2.0:LRA=7:linear=true (audio only, no video re-encode)
LOG: video_pipeline_v3/logs/preflight_YYYYMMDD.log
MAX ATTEMPTS: 3 — after 3 failures, sends Telegram warning and proceeds to grading.

PATTERN: services.* import shadowing in Phase 2 files -- PERMANENT RULE
  ROOT CAUSE: Files in services/ using importlib.util to load other services/
  files must use Path(__file__).resolve().parent as base, not from services.X.
  When gunicorn runs from core/, Python resolves services to core/services/
  which shadows top-level services/.
  RULE: NEVER write from services.X import Y anywhere in services/*.py
  ALWAYS use:
    _svc_dir = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(name, str(_svc_dir / file))
  FIXED IN: sentinel.py lines 22-40, convergence_engine.py lines 19-38
  VERIFY: cd ~/protocol_pulse/core && python3 -c from blueprints.intelligence import intelligence_bp; print(OK)
  WATCHDOG: /intelligence 404 after new Phase 2 file? Check for from services. in new file.
PATTERN: SpaceTap hang — get_best_space_clips() blocks forever on Whisper. ROOT CAUSE: No timeout on get_best_space_clips() call in daily_producer.py line 939. FIX: Wrap in threading.Thread with 120s join timeout. WATCHDOG: If producer runs >90min with 0 audio files, check ps cpu — if 80%+ CPU with no output, SpaceTap is hung, pkill -9 daily_producer.
PATTERN: Freeze frames surviving CFR re-encode (5 per render, all in final 75s)
  ROOT CAUSE: make_social_card_visual() and make_signal_active_scene() in assembler.py
    render static drawtext/drawbox overlays on procedural backgrounds. After the 0.3s
    fade-in, every frame is pixel-identical — content-level freezes, not PTS issues.
    CFR re-encode (the old preflight fix) cannot fix content-level freezes.
  LOCATION: assembler.py — make_social_card_visual() line ~3421, make_signal_active_scene() line ~2936
  FIX: Added noise=c0s=3:c0f=t filter before format=yuv420p in both functions.
    Imperceptible temporal noise (3/255 luma variation) breaks pixel-identical frames.
    Also updated _apply_preflight_fixes() in daily_producer.py as belt-and-suspenders.
  VERIFY: run_preflight_qc() must show freeze_frames=0
  WATCHDOG: If freeze_frames > 0 reappears, check for new static scenes missing the noise filter.