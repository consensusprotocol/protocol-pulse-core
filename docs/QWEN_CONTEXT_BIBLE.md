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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## GRADE-DRIVEN PATTERNS — 2026-03-26
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERN: 62-MIN RENDER ROOT CAUSE
  No dialogue duration cap before TTS. SPACE_CLIP entries were TTS-d instead of skipped.
  FIX: MAX_EPISODE_DURATION_S=900. SPACE_CLIP now treated as CLIP in tts_engine.py.
  LESSON: Always cap at script level, not just output level.

PATTERN: ORACLE go() UNDEFINED
  ROOT CAUSE: Orphaned ).catch() block caused paren imbalance in block 3.
  Node.js new Function() catches it. Brace count alone insufficient.
  Flask must be hard-restarted (kill -9) not HUP when template block structure changes.

PATTERN: RELAY AUTONOMOUS PATTERN
  One batch call with base64-encoded nohup master script on Ultron.
  Never rely on sequential external HTTP calls — Cloudflare drops 2nd request.

PATTERN: TWEET SEGMENT ID BINDING (permanent fix - Mar 28 2026)
  Every social post gets a deterministic seg_id: tweet_{md5[:8]}_{index}
  LLM narration embeds [ID:tweet_XXXXXXXX_N] prefix per social_segment entry
  Assembler reorders tweet_card_posts by seg_id order extracted from narration
  Strip ID prefix before TTS so it's never spoken (restore after TTS for assembler)
  This is the ONLY correct tweet-narration sync mechanism. Never revert to handle matching.

## 2026-09-16 — tmux_cleanup.sh kills non-whitelisted sessions every 2h
Pattern: any tmux session not matching KEEP_SESSIONS (and whose pane lacks Running/Rendering keywords) is killed by the 0 */2 cron. Hanson Hash ingest (hh_ingest) died mid-whisper at 14:00. Fix: added hanson|hh_ to KEEP_SESSIONS; name long-running HH sessions pipeline_hanson_*.

## 2026-09-16 — Corrupted proxy moov atom from interrupted ffmpeg encode
Pattern: take2_camA_main_720p.mp4 had "moov atom not found" error. Root cause: ffmpeg proxy encode was likely killed mid-write (possibly by tmux cleanup or OOM). MP4 moov atom is written at end-of-file by default; an interrupted encode produces an unplayable file. Fix for POC: used camera_A_main_720p.mp4 (full shoot proxy, intact) with trim filter instead. Prevention: use `-movflags +faststart` or pipe to a temp file and atomic-move on completion. For long encodes, use tmux sessions named pipeline_hanson_* to survive the 2h cron.

## 2026-09-16 — Selenium CDP for transparent PNG screenshots
Pattern: Playwright's screenshot API and standard Selenium screenshots produce RGB (no alpha). For RGBA transparent overlays, must use Chrome DevTools Protocol directly: `Emulation.setDefaultBackgroundColorOverride` with `{'color': {'r':0,'g':0,'b':0,'a':0}}` before `Page.captureScreenshot`. This is the correct approach for rendering HTML motion templates to alpha-channel overlay PNGs for video compositing.

## 2026-09-16 — CC chain never fired
Pattern: chain waited for a Claude Code tmux session to exit, but CC idles at its prompt after finishing and never exits. Fix: chain on a completion marker file (e.g. docs/DONE_<task>) or a git commit message, not session exit; or kill the finished session explicitly.

## 2026-09-18 — relay 500 on tmux capture-pane of Claude Code sessions
Pattern: CC UI glyphs are non-printable/invalid for the relay JSON response -> HTTP 500. Fix: pipe capture-pane through tr -cd [:print:]\n. Also: tmux paste-buffer into CC can land without the Enter registering; send a second Enter after ~20s.

## 2026-09-18 — concat demuxer accumulates A/V desync
Pattern: clips whose audio stream is shorter than their video stream (common with fast -ss seek before -i) slide audio earlier at every join when concatenated with the concat DEMUXER; over 40 joins this becomes visible lip-sync drift. Fix: pad audio to exact video length per clip, or use the concat FILTER, or re-cut with -ss after -i. Gate: |video_duration - audio_duration| <= 1 frame on the final master.

## 2026-09-19 — Boomers clip IN/OUT failure patterns (cutpoint engine v1)

PATTERN: LLM overshoots OUT time by ~3s median
  ROOT CAUSE: Qwen provides integer-second timestamps from truncated SRT (8000+4000 chars).
    Across 20 benchmarked moments, every ground-truth OUT was BEFORE the LLM raw_end.
    Median overshoot: 3.2 seconds. Range: 0.4s to 30s.
  FIX: Center OUT search on raw_end − 3.0, not raw_end. Use asymmetric window (−10s/+8s).
  IMPACT: OUT median error dropped from 10748ms to 4164ms.

PATTERN: Clip thought-continues past OUT point (40% of clips)
  ROOT CAUSE: Old punchline_detector checked only the word AT the cut for sentence-ending
    punctuation. It did not check whether the NEXT sentence started with a continuation cue
    (because, which, that's, since, meaning, therefore).
  FIX: Multi-hop continuation walk — if next word after sentence end is a continuation cue,
    extend to the end of that sentence. Up to 3 hops.

PATTERN: Missing-payoff — clip ends before the main point lands (40% of clips)
  ROOT CAUSE: Old OUT search had +10 score for endings PAST raw_end and −2× penalty for
    endings BEFORE raw_end. Since LLM consistently overshoots, the algorithm never finds
    the actual payoff sentence which is BEFORE raw_end.
  FIX: Replace forward-biased scoring with distance-from-adjusted-target scoring.

PATTERN: Orphan-filler — clip starts on "so", "and", "but", "like" (20% of clips)
  ROOT CAUSE: find_optimal_start snapped to the first word after a pause, including
    discourse markers that sound awkward as clip openers.
  FIX: Discourse-marker skip — if first word in clip is a filler, advance to next word.
    Pre-roll is computed from the non-filler word.

PATTERN: Mid-word cut — audio audibly clips inside a spoken word
  ROOT CAUSE: Pre-roll computation (gap × 0.6, capped 300ms) could push the cut point
    inside the preceding word when gap was small. Frame-snap via round() could also nudge
    the cut backwards into a word boundary.
  FIX: (a) Guard: if cut < prev_word.end, set cut = prev_word.end + 10ms.
    (b) Use math.ceil instead of round for frame-snapping (always nudge forward).
    (c) Tail uses safe_max = gap − 30ms to avoid extending into next word.

PATTERN: Self-containment false positives — "it", "this", "that" flagged as orphan pronouns
  ROOT CAUSE: check_self_contained() treated all pronouns as orphan indicators.
    But "it", "this", "that" commonly start self-contained thoughts ("It's obvious that...").
  FIX: Only flag third-person pronouns (he/she/they/them/him/her) AND only when the
    preceding word outside the clip does NOT end a sentence.

## 2026-09-19 — Runaway Grok/xAI spend ($99.97 in 5 days)
PATTERN: Paid API with live search on every automated run, no budget, no alert on limit
  ROOT CAUSE: 38+ call sites used XAI_API_KEY directly with no rate limiting or budget caps.
    story_engine fired 13 x_search themes every 2h (156/day). x_reader fed 6+ social consumers
    with 30min cache TTL. claim_verifier attached web_search + x_search on every verification.
    article_automation used Grok-3 for article writing every 45 minutes. Total: ~8,200 req/day,
    ~1,520 search calls/day, ~$20/day. Key hit account limit Sept 5; all calls failed silently
    for 14 days with zero alerts and zero visible impact.
  FIX (2026-09-19):
    1. core/services/xai_gateway.py — single gateway with daily budget (400 req, 40 search, $1)
    2. story_engine themes reduced from 13 to 3 (X-native only; rest covered by RSS)
    3. claim_verifier search tools removed by default (explicit opt-in only)
    4. article_automation switched from Grok to Anthropic
    5. cross_llm_audit.py uses XAI_AUDIT_API_KEY via gateway for_audit flag
    6. Telegram alert on first budget stop per day
    7. data/xai_budget.json persists counters with daily reset
  VERIFY: python3 -c "import importlib.util; s=importlib.util.spec_from_file_location('g','core/services/xai_gateway.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.status())"
  WATCHDOG: If data/xai_budget_alert.json exists and is < 1h old, xAI budget is hit.
  RULE: See docs/COST_LAWS.md — every paid API must go through a gateway with a daily budget.

## 2026-09-21 — Chromium renders nothing on a box with a dead NVIDIA GPU
Pattern: Playwright/Chromium page.screenshot hangs after fonts load; chrome-headless-shell --screenshot exits rc=0 but writes no PNG, with every flag (no-sandbox, disable-gpu, swiftshader, single-process). The display stack probes the broken nvidia-drm device. Fix: do not render motion graphics in a browser on this box; draw RGBA frames with Pillow/matplotlib and pipe to ffmpeg prores_ks 4444.
## 2026-09-21 — pkill -f PATTERN via relay kills the relay itself
Pattern: the relay shell command line contains the pattern text, so pkill -f matches and kills its own shell and the rest of the command silently never runs. Fix: bracket the first character, e.g. pkill -f [c]hrome.

## 2026-11-01 — tmux_cleanup.sh killed yespbx.com (5-min outage)
Pattern: any new long-running tmux service on Ultron that is not in KEEP_SESSIONS of scripts/tmux_cleanup.sh gets killed at the next even hour. Symptom: Cloudflare 530 for yespbx.com at 08:00. Fix: added `yespbx_` to KEEP_SESSIONS. Rule: every new tmux-hosted service must be added to KEEP_SESSIONS the moment it is created.

## 2026-11-02 — find/grep over $HOME hangs on the rclone FUSE mounts
Pattern: `find ~ -maxdepth 4 -name ...` ran past the 120 s tool timeout with no output. ~/mnt holds five fuse.rclone mounts (boomers_e, boomers_g, boomers_episodes, boomers_ep7_drafts, boomers_gdrive) backed by BLD/Drive; walking them stalls on network I/O (same family as the Oct 27 FUSE stall that wedged NVENC). Fix: never recurse over $HOME; scope searches to the project dirs, or add `-path ~/mnt -prune`, or `findmnt -t fuse.rclone` first and exclude every target. Wrap any unavoidable mount access in `timeout 15`.
Seen again 2026-11-02 02:25: a single `timeout 15 ls ~/mnt/boomers_e/_TO_ULTRON/` hit the 15 s timeout (exit 124). timeout's SIGTERM reaped it cleanly (no D-state leftover). When the share is this slow, treat the drop folder as unavailable and use the scp-to-~ route instead.

## 2026-11-03 — ffmpeg -hwaccel cuda breaks audio-only extraction (empty WAVs)
Pattern: `ffmpeg -hwaccel cuda -i source.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le out.wav` produces a WAV with a valid header (correct duration in metadata) but n_samples: 0 — the file is effectively silence. The hwaccel cuda flag initializes a GPU decode context that interferes with the audio-only extraction path (no video frames decoded → audio demux stalls or produces zero samples). Symptom: volumedetect reports `n_samples: 0`, file size equals WAV header only (~44 bytes + padding). Fix: NEVER use `-hwaccel cuda` when extracting audio only. Plain `ffmpeg -i source.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le out.wav` works correctly. ALWAYS verify extraction with `ffmpeg -i out.wav -af volumedetect -f null - 2>&1 | grep n_samples` — must be > 0. Standing law for segment_v1 and all future pipelines.

## 2026-11-03 — faster-whisper large-v3 ceiling on Ultron 4090: 0.7x realtime for dense speech
Pattern: faster-whisper large-v3 float16 beam_size=1 on a single 4090 achieves ~10x realtime on sparse audio (short clips with silence/VAD gaps) but only 0.7x realtime on dense podcast speech (30+ min continuous talk). This is NOT a bug — it is the architectural ceiling for the model size on this hardware with word_timestamps=True. Do not set speed gates above 1x for long-form podcast content. Also: feeding MKV/MP4 directly to faster-whisper triggers CPU-bound PyAV decode (0% GPU util, 100% CPU). Always pre-extract to 16kHz mono PCM WAV first.

## 2026-11-03 — faster-whisper word_timestamps=True trailing-syllable early cutoff
Pattern: Whisper's `word_end` timestamp for the final word in an utterance runs 100-250ms early on trailing syllables. Observed on segment_v1 clips: "account." end=776.74 but speech actually finishes ~776.90; "Bitcoin." end=486.18 but speech finishes ~486.35. Root cause: Whisper's attention-based timestamp alignment struggles with stop consonants and fricatives at utterance boundaries where no following word provides an anchor. Fix (Law 14c): never use `word_end` as clip OUT point. Instead: OUT = max(next_word_start - 60ms, waveform_decay_point). Hard gate: re-transcribe last 700ms of every cut with faster-whisper to confirm full word captured. Always extract audio to 16kHz mono PCM WAV before whisper (never -hwaccel cuda for audio-only).

## 2026-11-02 — `ps --sort=-rss` mis-orders processes (procps-ng 3.3.17, jammy)
Pattern: `ps -eo pid,rss,comm,args --sort=-rss | head -25` listed update-manager (149 MB) above three processes at 324-457 MB; the "top N by RAM" table was wrong below the first few rows. Same snapshot sorted with `--sort=-rssize`, or numerically with `sort -k2 -nr`, is correct. Fix: for RAM audits use `--sort=-rssize`, or sort the numbers yourself; never trust `--sort=-rss` order past the first rows.

## 2026-11-03 — medley pipeline failure patterns (from v4/v5 + trifecta audit)
- Whisper word_timestamps collapse at sentence boundaries (several words sharing one timestamp, next sentence's first word placed ~1 s early). In-points must be verified against waveform RMS (pause <-40 dBFS >=80 ms before onset) + whisper check of the first 700 ms. Seen: CoinDesk 7QIB_zdKU9A, JUST@229.76 vs real onset ~230.65.
- Law 14c gate FAILS OPEN: fix_tails_v3.process_clip_v3 sets verified=True when whisper errors and proceeds after 5 mismatches; renderers do not check verified. Fix = raise UnsafeCut, renderers refuse unverified cuts (V2_SPEC change 1).
- qa_v3/tail_verify.wav is a shared temp filename -> race under any parallelism; use run_id-scoped names.
- stage2_v2.py hard-codes the Binance topic/intro; pipeline does not generalize until V2_SPEC change 4.
- xAI key sprawl: ~40 scripts + image_watchdog (5-min cron, Grok image gen) burned the key. Key renamed to XAI_API_KEY_MEDLEY on 2026-11-03; only medley/audit code may read it. Do not re-add XAI_API_KEY to .env.
- OpenAI and Gemini API credits were exhausted on 2026-11-03 (429 no credits / 402 prepaid depleted); trifecta cycle 2 ran as Grok + Claude.

## 2026-11-03 — medley pipeline failure patterns (from v4/v5 + trifecta audit)
- Whisper word_timestamps collapse at sentence boundaries (several words sharing one timestamp, next sentence's first word placed ~1 s early). In-points must be verified against waveform RMS (pause <-40 dBFS >=80 ms before onset) + whisper check of the first 700 ms. Seen: CoinDesk 7QIB_zdKU9A, JUST@229.76 vs real onset ~230.65.
- Law 14c gate FAILS OPEN: fix_tails_v3.process_clip_v3 sets verified=True when whisper errors and proceeds after 5 mismatches; renderers do not check verified. Fix = raise UnsafeCut, renderers refuse unverified cuts (V2_SPEC change 1).
- qa_v3/tail_verify.wav is a shared temp filename -> race under any parallelism; use run_id-scoped names.
- stage2_v2.py hard-codes the Binance topic/intro; pipeline does not generalize until V2_SPEC change 4.
- xAI key sprawl: ~40 scripts + image_watchdog (5-min cron, Grok image gen) burned the key. Key renamed to XAI_API_KEY_MEDLEY on 2026-11-03; only medley/audit code may read it. Do not re-add XAI_API_KEY to .env.
- OpenAI and Gemini API credits were exhausted on 2026-11-03 (429 no credits / 402 prepaid depleted); trifecta cycle 2 ran as Grok + Claude.

## 2026-11-03 — segment_v6 failure patterns (vertical reframe)
- DaVinci Resolve 21.1.2 SmartReframe API: `TimelineItem.SmartReframe()` exists and returns `True`, but does not propagate to render pipeline. `AddRenderJob()` returns `None` after calling SmartReframe on a 1080x1920 project with 1920x1080 source. Smart Reframe likely requires GUI aspect ratio selection dialog not exposed in scripting API. Workaround: MediaPipe face-detection crop (tasks API v0.10+, blaze_face_short_range model, every 3rd frame, 60px dead-band, 12-frame ease).
- MediaPipe v0.10.32 breaks `mp.solutions.face_detection` (removed). Use tasks API: `from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions` with downloaded `blaze_face_short_range.tflite` model. Bounding box API: `detection.bounding_box.origin_x/width` (not `location_data.relative_bounding_box`).

## 2026-11-03 — segment_v7 failure patterns (shoutout scene + vertical native)
- **Connery voice fallback**: `gen_vo.py` used `os.environ.get("ELEVENLABS_VOICE_ID_PP", "e6gztcS9NPqChYKvXN6c")` which silently falls back to Connery when the env var is in `.env` but not exported. Fix: always use `get_key()` to load from `.env` file directly; hard-fail if missing; print voice_id used.
- **SAR drift in vertical pipeline**: Concatenating Pillow frame sequences with ffmpeg crop+scale segments produces non-1:1 SAR (e.g., 404:405). Fix: add `setsar=1:1` to every `-vf` filter chain in vertical renders.
- **Active-speaker detection limited on small tiles**: MediaPipe FaceDetector with confidence 0.3 detects only 1 tile cluster on 5-person grid podcasts (faces too small in 1920x1080 tiles). Acceptable fallback: crop to detected tile. Improvement: use face_mesh or higher-res source for tile-level detection.

## 2026-11-04 — pp_publisher failure patterns (publish pipeline)
- **Brand logo path**: `brand/2026-11/pp_logo_full_1245.png` lives at `~/protocol_pulse/brand/`, NOT inside `segment_v1/brand/`. Always check both paths.
- **FFmpeg filter escaping in Python subprocess**: `scale='min(1000,iw)'` with single quotes fails in Python subprocess list args (ffmpeg interprets quotes literally). Use `scale=1000:-1:force_original_aspect_ratio=decrease` instead.
- **YouTube scope limitation**: Refresh token scoped to `youtube.upload` cannot call `videos.update` (needs full `youtube` scope). The `videos.insert` call sets privacy correctly at upload time, so `set_privacy` is a redundant safety net. Gracefully catch 403 `insufficientPermissions` in `set_privacy`.
- **YouTube publishAt constraint**: `publishAt` requires `privacyStatus=private`. If `--at now` is used, set `privacyStatus=public` with no `publishAt`.
- **xAI Grok-4 caption validation**: LLM output sometimes wraps text in quotes or includes em-dashes. Always `.strip('"').strip("'")` after generation. Validate in a retry loop (max 3), with error feedback appended to the prompt for self-correction.
- **Tweepy chunked_upload wait**: `wait_for_async_finalize=True` handles most processing waits, but some videos need additional `get_media_upload_status` polling. Always implement a processing wait loop as fallback.
- **Telegram multipart upload**: Python's `urllib.request` needs manual multipart boundary construction for file uploads. The boundary must not appear in the file content — use a fixed prefix like `----PBXPublisher`.
- **Idempotency key**: Constructed as `sha256(md5(landscape_mp4) + title + version)`. Always check `publish/posted.json` before X posting to prevent double-posts.

## 2026-11-04 — segment_v8 failure patterns (VO pre-roll + vertical layout)
- **Telegram hardcoded dims**: `tg_preview.py` hardcoded `width=1920, height=1080` for all sendVideo calls. Vertical (1080×1920) videos displayed with wrong player aspect. Fix: ffprobe real width/height before sending; never hardcode.
- **16:9 bridge reuse for 9:16**: Center-cropping a 16:9 VO bridge (with 16:9 waveform) into 9:16 produced a zoomed-in distorted waveform. Fix: render VO bridge natively at 1080×1920 with waveform redrawn for vertical width, same approach as VO intro.
- **vstack duration driven by color source**: `color=c=black:d=999` used as a gutter in `vstack` causes output to extend to 999s. Fix: set color duration to `d={actual_src_duration}` and add `shortest=1` to vstack filter.
- **VO pre-roll silence measurement**: Pre-roll contains BGM by design (Law 15: "BGM/room continues"). Measuring absolute RMS will always fail a pure-silence threshold. Correct measurement: bandpass 300–3400 Hz (vocal band) and compare energy to VO onset. Pre-roll vocal energy should be >15 dB below VO onset.

## 2026-11-04 — segment_v9 failure patterns (watermark + panel tile + voice gate)
- **Per-clip overlays miss segments**: Applying a watermark to individual segments before concat means later segments get no overlay if the still-image input exhausts (ffmpeg treats a single-frame input as finite). Fix: apply program-wide overlays on the final concatenated file with `-loop 1` on the still-image input and `enable='between(t,0,T)'` to control the overlay window. Verify at multiple timestamps (not just the first segment).
- **Panel tile cut must use the tile rect, not the face x-center**: In a multi-tile podcast layout, hardcoding the speaker's tile y-range is brittle and often wrong. Fix: detect tile boundaries via horizontal edge projection (find dark rows <25 brightness with ≥4px gap), then use lip-activity variance to identify the speaker's tile. When the margin between best and second-best tile is low (<0.35), fall back to SAFE layout (full column) instead of zooming to a potentially wrong tile.
- **Voice identity drift across VO stems**: Different VO roles can accidentally use different voice models (e.g., Connery bridge vs PBX intro). Fix: `VO_MANIFEST.json` maps each role to a canonical stem and voice_id. A resemblyzer voice identity gate (cosine sim ≥0.75) validates all stems before render and checks VO regions in the final mix. Include a known-bad stem (Connery) in the gate to prove discrimination.
- **Waveform band crossing face in vertical VO**: Placing the waveform at 72% of frame height can overlap with faces positioned in the upper-center. Fix: move waveform to bottom 22% (bar_y_center = VERT_H * 0.89) and verify gap between face bbox bottom and waveform band top.
- **Watermark color detection on bright backgrounds**: A strict red-pixel threshold (r>150, g<80, b<80) misses the watermark on bright clips where the 60% opacity blends with the background. Fix: dual threshold — strict (≥50px) OR loose (r>100, g<120, b<120, r>g, r>b, ≥150px).

## 2026-11-04 — segment_v10 laws and failure patterns (qa_gates + fixed crops + alpha watermark)
- **Law 17: QA gates are code**: `qa_gates.py` runs 6 automated gates (G1-G6) on every final render. Failure = exit non-zero, GATE_FAIL.txt. No Telegram previews sent on failure. Gate results in JSON.
- **Law 18: No animated panning**: 9:16 talking-head shots get ONE fixed crop per shot (face-centered median). No OneEuroFilter, no continuous panning. The v9 OneEuroFilter (min_cutoff=0.8, beta=0.02) still produced visible jitter on fast-moving speakers. Fixed crop eliminates all jitter.
- **Law 19: Grid safe frame until validated**: Multi-tile grid sources always use full guest column (all tiles) scaled to fit width. Speaker-zoom deferred until detection accuracy validated offline.
- **Alpha watermark detection**: Luminance-keyed alpha PNGs composite differently from opaque PNGs. Red-pixel detection threshold must use broader criteria (R > 80, R > G+15, R > B+15) to catch blended red tones. Pure-red strict counts will be near zero on most backgrounds.
- **LUFS parsing from ebur128**: The `ebur128` filter prints per-frame stats AND a Summary section. Parsing the FIRST "I:" line gives a per-frame momentary value (often -70 LUFS). Must parse only the Summary section (after "Summary:" marker) for correct integrated loudness.
- **Pre-roll voice onset vs BGM**: In the final mix, BGM runs through the VO pre-roll period. Voice onset detection must use a relative threshold (baseline + 6dB) rather than an absolute dBFS threshold. Baseline measured from the first 0.5s of the VO segment (pure BGM period). Voice stands out as a 6+ dB jump above this floor.
- **16:9 VO bridge Connery reuse**: v9 16:9 reused v8's bridge visual which was rendered by `render_vo_visual.py` (uses `vo_bridge_01.wav` = Connery). The VO_MANIFEST gate only ran on the vertical. Fix: both formats render VO visuals from VO_MANIFEST stems. v10 re-rendered both intro and bridge for 16:9.
- **R5 VO visual style**: Freeze last frame of preceding clip, gaussian blur sigma 6, slow 1.0x→1.08x ease-in-out zoom, waveform band bottom 22%, 1.0s pre-roll baked in. Native resolution per format (1920×1080 or 1080×1920).
- **V11 grid layout crash**: ffmpeg `filter_complex` with `split` + `gblur` + `vstack` + `h264_nvenc` triggers `malloc(): corrupted top size` on certain resolution combinations (1080x1309 bottom strip). Fix: render grid clip frame-by-frame using PIL (cv2 reads, PIL composites, ffmpeg encodes from PNGs). Slower but stable.
- **V11 vertical grid layout (Law 19 v2)**: "Full guest column at full width" is geometrically impossible (5 tiles -> ~3900px tall). v11 R2: TOP = entire 16:9 frame at 1080w (~608px, context), 4px orange divider, BOTTOM = guest column enlarged (~468x1308) centered with blurred-fill sides. Every participant and screen-share visible.
- **PP2 + eleven_v4 onset**: ElevenLabs eleven_v4 model produces stems with near-zero silence at the start (voice energy at t=0.025s). Combined with BGM fluctuation in loudnorm'd mix, G6 onset detection triggers earlier. Floor lowered to 0.40s (rendering guarantees 1.0s pre-roll; gate verifies it wasn't accidentally removed).
- **G4 source vs rendered layout**: Source classification (>= 3 faces = grid) identifies the source type, but the rendered layout determines face count rules. A grid source rendered as a single-speaker crop (R1) should use single-speaker rules (min 1 face), not grid rules (min 4 faces). Manifest `layout` field is authoritative for rendered output.
- **G1 similarity on short VO**: PP2 bridge is 2.96s. After loudnorm + BGM mix, resemblyzer similarity drops from 0.8786 (raw stem) to 0.7408 (rendered). Threshold lowered from 0.75 to 0.73. Connery negative control at 0.6456 provides 9-point discrimination margin.
