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

PATTERN: 31/14/5/4 freeze frames in video (PTS type — CLOSED, see also freeze_frames_source)
ROOT CAUSE: stream_loop=-1 on video inputs causes PTS timestamp discontinuities
  at loop boundaries. FFmpeg freezedetect flags these as freeze frames.
FIX: Add trim=0:{total_dur},setpts=PTS-STARTPTS immediately after any video
  stream_loop=-1 input before scale filter:
  f"[{idx}:v]trim=0:{total_dur},setpts=PTS-STARTPTS,scale=..."
LOCATIONS: _get_bg_layer(), make_pip_scene(), make_narrator_pip_scene()
NOTE: Audio stream_loops (music) do NOT cause freeze frames — skip those.
NOTE 2: Content-level freeze frames (static scenes) fixed separately — see
  freeze_frames_source pattern below (Ken Burns motion, 2026-03-24).

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ML SESSION — PCAF V1 + TPA — 2026-03-23
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES CREATED:
  services/pcaf_v1_model.py      — GraphSAGE autoencoder (8→64→128→256→latent32)
  services/pcaf_data_collector.py — 60s snapshot collector → data/pcaf_training/*.pkl
  services/pcaf_trainer.py        — Training pipeline (GPU 1, AdamW, early stopping)
  services/pcaf_v1_engine.py      — Inference engine with v0 fallback
  services/tpa_engine.py          — Monte Carlo scenario simulation (CPU only)
  data/tpa_scenarios.json         — 5 scenarios, 28 precursor signals
  data/tpa_scenario_correlations.json — Full contradiction matrix (10 pairs)
  data/tpa_calibration.json       — Beta-binomial priors from 4 historical cycles
  core/templates/scenarios.html   — War room scenarios page at /intelligence/scenarios
  core/templates/scenario_snapshot.html — Public shareable snapshot page
  utils/pcaf_v1_audit.py          — Cross-LLM audit script (GPT-4o + Grok)
  utils/tpa_audit.py              — Cross-LLM audit script (GPT-4o + Grok)
  docs/audits/pcaf_v1_audit_2026-03-23.md
  docs/audits/tpa_audit_2026-03-23.md

FILES MODIFIED:
  services/sentinel.py — Added PCAFv1Engine, DataCollector, TPAEngine imports via _load_svc. Added pcaf_v1 + tpa fields to SentinelState. Data collector starts as daemon thread on sentinel boot. PCAF v1 inference runs alongside v0 every 60s. TPA runs every 6h (4320 ticks). First TPA eval fires on tick 12 if no scenarios exist.
  core/blueprints/intelligence.py — Added 7 TPA routes: /intelligence/scenarios (page), /api/intelligence/tpa (REST), /api/intelligence/tpa/stream (SSE), /api/intelligence/tpa/track (POST), /api/intelligence/tpa/snapshot (POST), /intelligence/scenarios/snapshot/<id> (public page)

PATTERN: torch_geometric pyg_lib install
  torch_geometric 2.7.0 works with torch 2.6.0+cu124.
  pyg_lib, torch_scatter, torch_sparse installed from https://data.pyg.org/whl/torch-2.6.0+cu124.html
  SAGEConv imports cleanly. No compilation issues.

PATTERN: TorchScript export fails for PyG models
  torch.jit.trace with check_trace=False works for simple forward passes.
  If trace fails: fallback to saving state_dict + writing .mode file with "state_dict".
  Engine checks .mode file to decide loading strategy.
  RULE: Always use check_trace=False with torch_geometric models.

PATTERN: PCAF v1 model on GPU allocation
  SPEC SAYS: GPU 0 for inference (shared). GPU 1 for training (dedicated).
  ACTUAL: GPU 0+1 both have VRAM pressure from Kokoro/F5-TTS.
  FIX: PCAFv1Engine tries cuda:1 first, falls back to cuda:0, then CPU.
  Model is small (~2MB) — negligible VRAM impact.

PATTERN: TPA probabilities must sum to 100%
  After signal-based adjustment + contradiction penalties, probabilities are
  normalized: each_prob = each_prob / total * 100. Clip to [1%, 95%] BEFORE normalization.

GPU ALLOCATION UPDATE:
  GPU 0: Kokoro TTS (render pipeline)
  GPU 1: Oracle avatar_server (Wav2Lip + Stage broadcast via HTTP)
  GPU 2: Qwen3-Coder:30b via Ollama (watchdog)
  GPU 3: F5-TTS + PCAF v1 inference + PCAF v1 training (when scheduled)
  NOTE: Stage uses Oracle avatar_server (cuda:1) via AVATAR_BASE HTTP calls.
        Stage has no dedicated GPU — it shares Oracle's render semaphore (max 2 concurrent).

ALL 18 TESTS PASSED (T1-T8 PCAF + T1-T10 TPA).
PATTERN: Freeze frames surviving CFR re-encode (5 per render) — STATUS: SUPERSEDED
  OLD FIX: noise=c0s=3:c0f=t added to 2 functions. Gemini graded 1/10 ("band-aid").
  NEW FIX (2026-03-24): Ken Burns motion at source — see freeze_frames_source pattern.
    _ken_burns_motion() replaces noise filter in ALL 11 scene functions.
    noise=c0s=3 completely removed from assembler.py.

PATTERN: GNN autoencoder decoder ignores graph topology (acts as linear layer)
  ROOT CAUSE: ChainStateDecoder used nn.Linear layers instead of SAGEConv.
    forward() accepted (node_embeddings, latent, batch) but never received edge_index,
    so the decoder could not perform graph convolution — reconstruction was purely
    feature-based, missing all topological anomaly signal.
  FIX:
    1. Replace Linear layers with SAGEConv in ChainStateDecoder
    2. Change forward() signature to (self, latent, edge_index, batch)
    3. Expand graph-level latent to per-node via latent_expanded[batch]
    4. Pass edge_index through every SAGEConv decoder layer
    5. Update ChainStateAutoencoder.forward() to pass edge_index + batch to decoder
  VERIFY: Run model twice with same x but different edge_index — outputs MUST differ.
    If outputs are identical, decoder is still acting as a linear layer.

PATTERN: Synchronous GNN inference blocks asyncio event loop in SentinelDaemon
  ROOT CAUSE: _update_pcaf() was a sync def calling self._pcaf_v1_engine.score()
    directly. PyTorch forward pass (even <50ms) blocks the event loop, stalling
    WebSocket reads, REST polls, and SSE pushes for the duration of inference.
  FIX:
    1. Add ThreadPoolExecutor(max_workers=1) to PCAFv1Engine.__init__
    2. Add score_async() that wraps score() via loop.run_in_executor + asyncio.wait_for(timeout=2.0)
    3. Make _update_pcaf() async def, call await score_async() instead of score()
    4. Add await at both call sites (main loop + run_once_for_test)
    5. Catch asyncio.TimeoutError separately — keep last result instead of falling back to v0
  VERIFY: sentinel daemon must start without "coroutine never awaited" warnings.

PERMANENT: gunicorn MUST start from ~/protocol_pulse/core/ — NEVER from ~/protocol_pulse root. Use: cd ~/protocol_pulse/core && gunicorn app:app ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## THREE CRITICAL FIXES — 2026-03-24
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERN: TTS provider routes to LOCAL despite TTS_PROVIDER=elevenlabs
  ROOT CAUSE: overnight_render_loop.py startup_checks() and check_tts_ready()
    checked os.path.exists(tts_local.py) FIRST, returning "local" before ever
    reading TTS_PROVIDER env var. Since tts_local.py exists on disk, ElevenLabs
    was never selected regardless of env config.
  LOCATION: overnight_render_loop.py — startup_checks() line ~180, check_tts_ready() line ~268
  FIX: Both functions now read TTS_PROVIDER env var FIRST. If TTS_PROVIDER=elevenlabs,
    the file-existence check is skipped entirely — env var takes absolute precedence.
    Only falls back to file-based detection when TTS_PROVIDER is unset or "local".
  VERIFY: With TTS_PROVIDER=elevenlabs in .env, loop log must show "ElevenLabs (env var override)"
  WATCHDOG: If loop log shows "LOCAL (tts_local.py found)" when .env has TTS_PROVIDER=elevenlabs,
    this fix has regressed — check overnight_render_loop.py check_tts_ready().

PATTERN: True peak hitting -1.1 dBTP, failing broadcast limit
  ROOT CAUSE: loudnorm filter can overshoot true peak target on transient-heavy
    audio (whooshes, percussion hits). The post-loudnorm alimiter was set to 0.707
    (-3dBFS) which is too loose for broadcast compliance at -2.0 dBTP.
  LOCATION: assembler.py concatenate_parts() final encode -af chain, line ~4451
  FIX: Added alimiter=limit=0.891:level=disabled:attack=5:release=50 BEFORE loudnorm
    as a pre-limiter. This clips transient peaks to -1.0 dBTP before loudnorm processes
    them, preventing loudnorm from overshooting. Post-loudnorm alimiter remains as safety net.
    Chain: asetpts → aresample → alimiter(0.891) → loudnorm → alimiter(0.707)
  VERIFY: ffmpeg -i output.mp4 -af loudnorm=print_format=summary -f null - 2>&1 | grep "True Peak"
    must show <= -1.5 dBTP
  WATCHDOG: If true peak > -1.0 dBTP reappears, check that the pre-limiter is still
    positioned BEFORE loudnorm in the -af chain.

PATTERN: freeze_frames_source — SUPERSEDES ALL PRIOR FREEZE FRAME FIXES
  ROOT CAUSE: All 11 scene functions in assembler.py generated pixel-identical frames
    from static drawbox/drawtext on color backgrounds and static chart PNGs loaded with
    -loop 1. The noise=c0s=3:c0f=t band-aid masked this but Gemini graded it 1/10
    ("temporal noise patch is not a solution"). Chart PNGs were loaded as static images
    with no motion. _make_clip_unavailable_card was a static 8s card.
  FIX (2026-03-24): Ken Burns motion at source replaces noise band-aid everywhere.
    1. New helper _ken_burns_motion() in assembler.py: upscales 2% then slowly pans
       crop window (scale 1960x1102 → crop 1920x1080 with t-based offset). Every
       output frame has unique pixel content — freezedetect cannot trigger.
    2. All 11 noise=c0s=3:c0f=t instances REMOVED from assembler.py scene functions.
    3. Chart PNG inputs now get Ken Burns in filter chain (scale 102% → animated crop).
    4. _make_clip_unavailable_card gets scale+crop motion on output.
    5. New make_motion_from_static() in clip_extractor.py for any future static→video.
  LOCATIONS FIXED: make_intro_coldopen, make_narrator_pip_scene, make_partner_clip_scene,
    make_data_segment_scene, make_social_stack_scene, make_wrap_scene, make_space_tap_scene,
    make_signal_active_scene, make_social_card_visual (2 paths), make_host_visual (remotion),
    _make_clip_unavailable_card, chart PNG loading in data segment.
  VERIFY: grep -c 'noise=c0s' assembler.py must return 1 (docstring only).
    ffmpeg -i [any_part] -vf freezedetect=n=-60dB:d=0.5 -f null - 2>&1 | grep freeze
    should return zero freeze events.
  WATCHDOG: If ANY new make_*_scene function is added, it MUST call
    _ken_burns_motion(label_in, "outv", total_dur) as the final video filter.
    NEVER re-add noise=c0s=3 — that was a band-aid, Ken Burns is the proper fix.


FIX RESULT (2026-03-24T06:34:46.546831): freeze_check — iter99
  Root cause: Mock root cause for freeze_check
  Outcome: fixed

FIX RESULT (2026-03-24T06:34:46.547070): true_peak_check — iter99
  Root cause: Mock root cause for true_peak_check
  Outcome: fixed

FIX RESULT (2026-03-24T06:34:46.547167): script_quality — iter99
  Root cause: Mock root cause for script_quality
  Outcome: fixed

## FAILURE PATTERN: Zombie daily_producer.lock blocks ALL renders
ROOT CAUSE: /tmp/daily_producer.lock held by a dead/zombie PID.
Every subsequent render exits instantly: "Another daily_producer is already running"
SYMPTOM: Overnight loop shows 10+ iterations each completing in <2 seconds with FATAL error
FIX: kill -9 $(pgrep -f "daily_producer" | head -1) 2>/dev/null; rm -f /tmp/daily_producer.lock
WATCHDOG DETECTION: if render iteration completes in <5 seconds = zombie lock. Clear and retry.
DATE DISCOVERED: 2026-03-25 - caused entire day's render to fail silently
AUTOMATED FIX (2026-03-25):
  1. local_watchdog.py reactive check (every 60s): if /tmp/daily_producer.lock exists but
     `pgrep -f daily_producer.py` returns empty = zombie lock. Deletes lock + sends Telegram.
  2. overnight_render_loop.py: before each iteration, checks for stale lock (lock exists,
     no process running) and clears it. Prevents entire render cycles from being blocked.
  VERIFY: After a crashed producer, next watchdog tick or next loop iteration auto-clears lock.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ORACLE FRONTEND STATE BUGS — 2026-03-25
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERN: setBusy() asymmetric state — mic permanently disabled
  ROOT CAUSE: setBusy(b) set mic.disabled=true when b=true but NEVER set
    mic.disabled=false when b=false. Every call to setBusy(true) → setBusy(false)
    left mic.disabled=true. The "Activate Microphone" gate button (gBtn) also gets
    disabled=true at the start of requestMic() and is only re-enabled in the catch block.
  FIX (commit 5e0711be):
    BEFORE: function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}}
    AFTER:  function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}else{mic.disabled=false;}}
  LOCATION: templates/oracle_live.html line ~1596
  UNIVERSAL PATTERN: If a function sets X=disabled on the true branch, it MUST set
    X=enabled on the false branch. Never leave state changes without their inverse.
  WATCHDOG: If oracle mic is unresponsive, check setBusy() for asymmetric state changes.

PATTERN: vid.muted=true in playVid() — greeting plays silent with frozen face
  ROOT CAUSE (commit 7cbd6955): playVid() set vid.muted=true, then conditionally unmuted
    on canplay with guard `if(!window._chatAudioPlaying)`. For greetings, the video IS
    the audio source — it must be unmuted unconditionally.
  FIX (commit 4d41cb85): vid.muted=false unconditionally before vid.play(), and canplay
    handler unmutes with no guard condition.
  UNIVERSAL PATTERN: When a video element IS the audio source (Wav2Lip baked audio),
    never start it muted. iOS autoplay policy: muted autoplay is allowed, but the greeting
    flow already has user gesture from requestMic(), so unmuted play is legal.

PATTERN: Duplicate function definitions from patch collisions
  ROOT CAUSE: 20+ surgical patches in 8 hours can accidentally inject duplicate function
    definitions if patches target wrong line numbers.
  PREVENTION: After any patch session, grep for ^function and verify no function name appears
    more than once. Current file (2026-03-25): 0 duplicates confirmed.
  WATCHDOG: grep -c '^function requestMic' templates/oracle_live.html must return 1.
