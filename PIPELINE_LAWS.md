# PROTOCOL PULSE — PIPELINE LAWS
## Status: ACTIVE (being refined via 10-cycle gauntlet)

---

## PIXEL ZONES (confirmed spec)
- Background: full 1920×1080, color #0A0A0F (never pure black #000000)
- Text zone (narration): x=40-960, y=80-760 (left half only)
- PiP zone: x=960-1880, y=0-540 (top right)
- Subtitle band: y=778-885, full width (1920px), dark glass rgba(0,0,0,0.75), 4px red left bar
- Info rail (gold): bottom, y≈1032-1080, full width, #F8C15C text
- Title card: full canvas, no thumbnail bleed

## COLOR PALETTE (locked)
- Background: #0A0A0F (VDS dark navy)
- Accent / border: #FF3333 (red, 2px borders)
- Gold info text: #F8C15C
- Primary text: #FFFFFF
- Subtitle band bg: rgba(0,0,0,0.75) + blur

## AUDIO TARGETS (locked)
- Integrated LUFS: -14 ±2
- True peak: ≤ -2.0dBTP
- LRA: 7 LU
- Single loudnorm: only in concatenate_parts() — no per-segment loudnorm
- Sample rate: 48000 Hz
- Bitrate: 192k (audio)

## TTS (locked)
- Host 1 (Eryn): ID kdnRe2koJdOK4Ovxn2DI at 1.12x speed — sharp female setup/bridge host
- Host 2 (PBX): ID HmUVvDlHsEz0m3eUGLgu at 1.0x speed — male contrarian/react host, ALWAYS opens episode
- DUAL HOST RESTORED 2026-03-10: both voices MUST render in every episode
- Speed param: top-level body param, NOT inside voice_settings
- Fallback chain: ElevenLabs → pyttsx3 → gTTS → silence
- TTS cache: tts_cache/ SHA256(voice_id:segment_type:text)[:16].m4a

## FFMPEG TIMEOUTS (locked)
- Default run_ffmpeg_filtergraph() timeout: 300s (was 120s)
- Heavy filtergraphs (make_intro_coldopen, PiP): 300s minimum
- concatenate_parts(): 600s

## TIMING SPEC
- Title card: 2.0s exactly
- Cold open: 10-14s
- Narration segments: 15-35s each
- Clip segments: natural duration
- Tweet cards: 8-12s
- Outro: 10-15s
- Total: 8-15 minutes

## PRODUCTION RULES
- debug_mode = False in all production renders
- No debug overlays ("ORACLE NARRATION ACTIVE" etc.) — instant F grade if visible
- Cold open: NO logos, bars, watermarks — pure dramatic clip
- Clip segments: full-screen 1920×1080, NO narration overlays bleeding through
- Continuous BGM: music mixed ONCE in concatenate_parts(), not per-segment
- AV sync: nuclear PTS in fix_av_sync() + concatenate_parts()

## PRESERVED ELEMENTS (never touch)
- Gold bottom bar text color #F8C15C
- Red border thickness 2px where intentionally present
- Watermark: "PROTOCOL PULSE" white, lower-right, opacity 0.5
- PiP position: top-right, no text overlap

---

## CYCLE LEARNINGS

---

## ADDED MARCH 17 2026

### LAW: AUDIO MIX
- `amix` BGM must use `duration=first` and `weight>=0.08`
- Audio stream guard MUST verify audio stream exists before mix (`if "audio" not in _ac.stdout` → skip mix)
- TTS-anchored mix ensures BGM never outlives narration

### LAW: HOST DEFAULT
- Segment host default MUST be `2` (PBX), never `1`
- Any `host:1` in script output is normalized to `host:2`

### LAW: TTS FALLBACK BANNED
- `_generate_fallback_silent_audio` MUST raise `RuntimeError`, never generate silence
- Silent renders are pipeline-killing defects — fail fast, never ship silence

### LAW: GEMINI GRADING
- Exclude `.mp4`, `bgl_audio/`, archived files, and `test_` directories from grading candidates
- Gemini grades only the real final render, not intermediate artifacts

### LAW: VOICE LOCK
- Only voice ID `HmUVvDlHsEz0m3eUGLgu` (PBX) is permitted
- Validate voice exists and is active via ElevenLabs `/v1/voices/{voice_id}` API in preflight

### LAW: PREFLIGHT MANDATORY
- Before every render, preflight MUST validate:
  1. Voice ID is live (ElevenLabs API check)
  2. ElevenLabs quota usage < 95%
  3. Disk free space > 5 GB
  4. `ffprobe` and `ffmpeg` binaries are accessible
  5. Anthropic API ping succeeds
- Render MUST NOT proceed if any preflight check fails

### LAW: SOLO HOST
- PBX only — no dual host in current pipeline
- Script writer outputs only `host:2` segments
- No `host:1` voice rendering permitted

### LAW: JSON RETRY
- `script_writer` JSON parse uses 3-attempt retry
- On `JSONDecodeError`, send raw output back to LLM for repair before next attempt
- After 3 failures, raise and abort render

### LAW: YT-DLP COOKIES
- Use `data/yt_cookies.txt` if present and non-empty
- Export from logged-in YouTube browser session (`yt-dlp --cookies-from-browser chrome`)
- Prevents rate limiting on high-frequency extraction runs

### LAW: CLIP MINIMUM
- Hard fail is 3 clips from 2 channels minimum — never require 5/5
- Quality-aware fallback fills gaps before hard fail gate

### LAW: EPISODE SCHEDULE
- Three daily episodes at 06:00, 12:00, 18:00 UTC via cron
- Separate log files per run: `episode_morning.log`, `episode_noon.log`, `episode_evening.log`

### LAW: CLIP ARCHIVE
- Every extracted clip archived to `data/clip_archive/CHANNEL/VIDEO_ID.mp4`
- On yt-dlp failure, always try archive fallback (max 7 days old) before skipping clip
- `utils/clip_archive.py`: `save_clip()`, `get_fallback_clip()`, `list_archive()`

---

### PRE-GAUNTLET (cycles 1-3 on feature/video-audio-fix)
- Fixed: ElevenLabs fallback chain (gTTS added), AV sync, gold rail in make_host_visual, subtitle band in make_host_visual, per-segment loudnorm removed, bg color 0x0A0A0F, ffmpeg timeout raised to 300s
- Locked: Single loudnorm in concatenate_parts()
- Open: Subtitle band inconsistency (~50% of frames missing it), LUFS low (-17.7) due to cached silence audio


---

## LAWS ADDED 2026-03-24 — SESSION 5 INTENSIVE (ENFORCE PERMANENTLY)

### LAW: GPU ISOLATION (INVIOLABLE)
- Pipeline (daily_producer.py) runs on cuda:0 ONLY via CUDA_VISIBLE_DEVICES=0 set in load_env()
- Avatar server (oracle/avatar_server.py) runs on cuda:1 ONLY
- Stage avatar runs on cuda:2 or cuda:3 — NEVER cuda:1
- SadTalker is BANNED and must NEVER run — kill on sight (it consumes 3GB+ on cuda:1)
- Duplicate avatar_server processes must NEVER coexist — one process per avatar system
- If any GPU assignment drifts: pipeline will 503 avatar, avatar will 503 stage — verify with nvidia-smi before every render cycle

### LAW: FREEZE FRAMES AT SOURCE (NOT AT OUTPUT)
- Freeze frames MUST be fixed in clip_extractor.py at generation time, NOT in assembler.py at output
- All static image-to-video conversions MUST use Ken Burns zoompan motion:
  `zoompan=z=min(zoom+0.002,1.05):d=125:s=1920x1080,setsar=1`
- noise=c0s=3 freeze frame patches in assembler.py are PERMANENTLY BANNED
- Gemini penalizes output-level freeze patching as evidence of poor source quality (score 1/10)
- The _ken_burns_motion() helper in assembler.py is the ONLY approved static-to-video method
- After any clip generation change: run ffmpeg freezedetect on output before committing

### LAW: CROSS-LLM AUDIT BEFORE ANY CODE CHANGE
- Every CC session that touches pipeline code MUST run the full 2-cycle cross-LLM audit via utils/cross_llm_audit.py BEFORE implementing any fix
- Audit order: register feature in FEATURE_MAP → cycle 1 (Gemini+GPT-4o+Grok parallel) → save c1.json → cycle 2 cross-examination → save c2.json → synthesize consensus → implement consensus fixes ONLY
- No fix gets implemented without 2-cycle audit consensus. No exceptions. No shortcuts.
- Vague agreement is NOT consensus. Consensus = same file, same function, same root cause from Qwen + 1 external LLM minimum

### LAW: QWEN FIRST (COST LAW)
- Qwen3 runs locally on cuda:2/3 via Ollama at localhost:11434 — $0 per call
- Qwen reads all files and identifies candidates BEFORE any external LLM call
- External LLMs (Gemini, GPT-4o, Grok) receive ONLY Qwen's pre-filtered findings (≤120 lines max)
- Full file sends to external LLMs are BANNED — surgical payloads only
- If Qwen confidence ≥ 0.85 and no external LLM disagrees: implement without external call
- Token budget: $2 soft limit per improvement cycle. $5 hard limit. Above hard limit: pause + Telegram alert

### LAW: GEMINI GRADING — TWO-PASS MANDATORY
- PASS 1: Technical dimensions (ffprobe hard data only) — deterministic, no LLM hallucination possible
- PASS 2: Content dimensions — upload actual MP4 to Gemini via Files API for genuine multimodal evaluation
- "Assumed acceptable based on lack of specific error data" notes in grade output = GRADING FAILURE
- Content scores (script_quality, cold_open_hook, narrative_arc, host_authenticity, visual_polish, pacing) MUST come from Gemini watching the actual video, not from render log inference
- Any grade where 3+ content dimensions show "assumed" = discard and re-grade with video upload

### LAW: CRITICAL FAILURE GATING
- Any single dimension scoring 0/10 on: host_authenticity, black_frames_check, true_peak_check, freeze_check = broadcast_ready MUST be False regardless of overall weighted score
- A high overall score with one 0/10 critical dimension is NOT a Grade A
- Grade A requires: overall_score ≥ 88 AND zero 0/10 scores on critical dimensions AND broadcast_ready = True

### LAW: 10-CONSECUTIVE-A CONVERGENCE
- Pipeline is NOT locked until 10 CONSECUTIVE Grade A renders (score ≥ 88, broadcast_ready=True)
- Consecutive counter tracked in: video_pipeline_v3/logs/consecutive_a_grades.txt
- Counter resets to 0 on ANY non-A grade
- On each Grade A: Telegram "Grade A #{n}/10 — {n} more to lock"
- On 10/10: Telegram "PIPELINE LOCKED — 10 consecutive Grade A renders" then exit improvement loop

### LAW: RENDER IMPROVEMENT LOOP INTEGRATION
- render_improvement_loop.py runs automatically after every failed grade
- It reads the grade JSON, identifies failing dimensions, maps to DIMENSION_MAP, runs Qwen→LLM audit, implements consensus fix, verifies, git pulls into render_main, signals next iteration
- overnight_render_loop.py polls for /tmp/fix_complete_iterN flag before firing next iteration
- The loop NEVER touches render_main tmux session — read-only access to logs only
- The loop runs as a detached subprocess — does NOT block the overnight render timeout

### LAW: SESSION CONTEXT DISCIPLINE
- Every CC session starts fresh — never reuse a session that has burned >80% context
- Context warning at 11%: kill immediately and relaunch fresh
- Prompt delivery always via tmux load-buffer, never send-keys for complex prompts
- One CC session at a time on the same repo — no parallel sessions

### LAW: AVATAR SERVER UPTIME
- avatar_server must be running at all times via systemd or watchdog
- Health check: curl http://localhost:8200/health must return {"status":"ok"} before render starts
- If health check fails at render preflight: abort render, alert Telegram, attempt restart
- The watchdog_llm tmux session must verify avatar health every 5 minutes

### LAW: ANTI-HALLUCINATION IN AUDIT SESSIONS
- Audit prompts MUST include: "Only report issues you can verify from the code/data provided. Do not speculate."
- Issues ranked by impact: CRITICAL (0/10) → HIGH (1-4) → MEDIUM (5-7) → LOW (8-9)
- CRITICAL issues fixed first. HIGH only after CRITICAL resolved. MEDIUM only after HIGH eliminated.
- LOW issues (score 8-9) are NEVER touched while any CRITICAL or HIGH issue exists
- Focus is always on the biggest score impact, not the most interesting technical problem


### LAW: CONTENT LOCK — ITERATE ON ASSEMBLY, NOT CONTENT
The single most important law for grade stability:

- Iteration 1: Full pipeline run — fetch content, scan channels, select clips, generate script, TTS
  Saves: script.json, clips/, tts_cache/ to video_pipeline_v3/output/YYYY-MM-DD/locked_content/
- Iterations 2-N: Skip Steps 1-6 entirely. Load from locked_content/. Re-run ONLY Step 7+ (assembly/encode)
  Flag: daily_producer.py --reuse-content
  overnight_render_loop.py passes --reuse-content on all iterations > 1
- Grade A achieved: delete locked_content/, start fresh next cycle with new content fetch
- RATIONALE: Every re-fetch introduces new variables (different clips, script, TTS) making it
  impossible to isolate whether an assembly fix worked. Content must be locked so each iteration
  is a controlled experiment — same content, only assembly changes.
- NEVER wipe tts_cache on iterations > 1 (currently: rm -rf tts_cache every iteration — FIX THIS)

### LAW: LIVE ENDPOINT TESTING MANDATORY BEFORE ANY COMMIT
For any fix touching oracle/avatar_server.py or any user-facing avatar endpoint:
ALL 5 tests below MUST pass before git commit. Results MUST appear in commit message.

ORACLE MANDATORY TESTS:
  1. curl -s http://localhost:8200/health | python3 -m json.tool | grep status
     EXPECTED: "status": "ok"
  2. curl -s -X POST http://localhost:8200/oracle/speak
     EXPECTED: HTTP 200, text or video in response
  3. curl -s -X POST http://localhost:8200/oracle/chat -d '{"text":"what is bitcoin","session_id":"test"}'
     EXPECTED: HTTP 200, job_id present
  4. curl -s http://localhost:8200/oracle/job/$JOB_ID (after 20s)
     EXPECTED: 200 or 202, NOT 404
  5. Second speak request after first: must be 200 not 503
     EXPECTED: semaphore released, GPU not stuck

NEVER commit oracle changes without all 5 tests passing.
This law exists because commit 2c542a0d looked correct but silenced Oracle in production.
Theoretical fixes that break in practice are worse than no fix.
