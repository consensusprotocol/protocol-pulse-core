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

## LAW 14c: WHISPER TRAILING-SYLLABLE OUT POINT (ADDED 2026-11-03)

A clip's OUT point is never the last word's whisper `word_end` timestamp.
Whisper `word_end` runs 100-250ms early on trailing syllables ("account" → "acc-", "Bitcoin" → "bit-").

**OUT = max(next_word_start - 60ms, waveform_decay_point)**

Where:
- `next_word_start` = the start timestamp of the word immediately following the last EDL word
- `waveform_decay_point` = first 10ms window after the last word whose RMS stays below noise_floor+6dB for 120ms, plus 150ms room tone

**Hard gate:** Transcribe the final 700ms of every cut clip with faster-whisper; confirm the final word matches the EDL `last_word` in full. Mismatch = FAIL → widen 100ms, retry up to 4×.

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

---

## GRADE-DRIVEN LAWS (2026-03-26)

### LAW G-1: MAX EPISODE DURATION = 900s
- Hard cap enforced at Step 7a. Render > 900s is auto-trimmed.
- Never negotiate this. 15 minutes is the absolute ceiling.

### LAW G-2: TRUE PEAK < -1.5 dBTP
- `alimiter=limit=0.891:level=false` MUST precede ALL loudnorm calls. No exceptions.

### LAW G-3: noise=c0s=3 IS PERMANENTLY BANNED
- Freeze fix = `fps=30,setpts=PTS-STARTPTS` only.
- See LAW: FREEZE FRAMES AT SOURCE for the approved Ken Burns approach.

### LAW G-4: PBX IS THE SOLE HOST
- `host_num=2` hardcoded in tts_engine.py.
- `SPACE_CLIP` treated as `CLIP`. External clips = B-roll only, never narrated by any other voice.

### LAW G-5: GRADE TARGET = B (80+)
- C (70-79) = acceptable interim.
- D or F = DO NOT PUBLISH. Fix before next render.

### LAW G-6: GRADING IS MANDATORY
- Every render must produce a `grades/*.json` file.
- If grading fails, log it and alert — never silently skip.

---

## SEGMENT BUILD LAWS (added 2026-11-03, updated 2026-11-04)

### LAW 15: VO PRE-ROLL
- Every VO segment has 1.0s of silence prepended before the voice stem.
- Gate G6 enforces `onset >= 0.95s`.
- Law 15a: the VO visual extends by 1.0s at the head with zero waveform energy (blurred freeze + slow zoom).

### LAW 17: QA GATES MANDATORY
- Every final render (16:9 and 9:16) must pass qa_gates.py G1-G6 before approval.
- Gate failures block shipping.

### LAW 18: VERTICAL LAYOUT CLASSIFICATION (v3 — shotmap-driven, per-shot, replaces per-clip rules)
- Classify per SHOT (shotmap hard-cut boundaries, not per clip) using batched face detection on SOURCE frames (SCRFD/insightface ONNX GPU preferred, MediaPipe GPU delegate fallback) and screen-share detection.
- Detection runs once at shot entry + every 2s within a shot; results cached in `vertical/cache/<source_md5>.json`.
  - **1 face** → fixed face-centered 9:16 crop (no panning, Law 18a below).
  - **2 faces** → two stacked bands, each the tile/face crop from source, 1080 wide; equal bands unless speaker confidence HIGH (see 18b).
  - **3 faces** → three stacked bands, each 1080×607, 2 gutters 12px orange, centered vertically in 1920.
  - **4+ faces or screen-share** → full 16:9 frame letterboxed on top (~608px) + enlarged guest column below (~1308px), orange 4px divider.
- Never a subset of visible faces. Bands ordered left-to-right from source. No animated panning ever.
- Re-composition only at shotmap hard cuts. Lower-thirds re-rendered per composition. VO visuals/outro native 9:16.
- **18a (NO ANIMATED PANNING):** 9:16 talking-head shots get ONE fixed crop per shot: face-centered median over all sampled frames. No continuous panning, no OneEuroFilter, no animated crop motion. Re-center only at a hard cut.
- **18b (SPEAKER-DOMINANT BANDS):** When speaker confidence is HIGH (lip-activity margin >= 0.35 sustained >= 1.5s), the speaker's band takes ~60% of available height and other faces share the remainder. When confidence is LOW or indeterminate, all bands are equal height. Log mode (equal/dominant) per shot.

### LAW 19: VERTICAL FACE COUNT GATE (G4 for stacked layouts, v3)
- For every talking-head shot, the rendered vertical frame must show face_count == source_face_count (from shotmap) on 6 sampled frames (4 of 6 must match).
- G4 classifies layout from the SOURCE clip (>= 3 faces or screen-share = "grid"); for grid segments in vertical, require >= 4 faces in the rendered frame.
- Never crop or subset visible faces.
- **Unit test T1:** every output frame's face set == shot_map faces for that shot (catches wrong face, dropped column, 3-band from 5-tile).

### LAW 20: GATE THRESHOLDS ARE LAW CONSTANTS
- G1 voice similarity >= 0.75, transcript overlap >= 0.80
- G6 pre-roll onset >= 0.95s
- G5 LUFS = -14 +/- 1.0, true peak <= -2.0 dBFS
- Sessions fix measurement bugs, never lower thresholds.

### LAW 21: STAGE TIME BUDGETS (added 2026-11-04)
- Every pipeline stage has a stated wall-clock time budget. GPU/cached path is the default.
- A CPU-only per-frame loop over video frames is a DEFECT — use GPU-accelerated detection (SCRFD ONNX CUDA or MediaPipe GPU delegate), batch processing, and per-shot caching.
- Face detection cache: `vertical/cache/<source_md5>.json` — re-renders never re-detect.
- Target: full v14 vertical render (shotmap + compose + assemble + qa + critic) under 8 minutes wall-clock on GPU 0.
- Timing breakdown per stage printed in REPORT_vertical_v1.md.
- Shotmap hardening for YouTube re-encodes: detect letterbox bars and crop them before seam measurement; derive SEAM_ROWS from the active picture area (not hardcoded 120-900); mask burned-in lower-third bands (bottom 18%) when measuring gutters.

### LAW 22: EDL IS THE SINGLE SOURCE OF TRUTH (added 2026-11-04)
- The EDL file (`cuts_final.json`) is the **sole authority** for cut points (cut_in, cut_out, word_start, word_end).
- Renderers (reframe.py, assembler, render_clip, etc.) **MUST read** cut points from the EDL. They **MUST NEVER** hardcode, override, or compute alternative cut points inside render scripts.
- All cut point corrections go into the EDL file and nowhere else. Mark corrections with a `correction` field documenting what changed and why.
- Every EDL entry carries `verified: true` once whisper-checked. Unverified cuts must be flagged.
- `cuts_v3.json` is frozen history. Production uses `cuts_final.json`.
- If a cut point must change, update `cuts_final.json`, invalidate the shotmap/compose cache for that clip, and re-render.

### LAW 23: VERTICAL PARITY LAW (added 2026-11-04, updated 2026-11-05)
- The 9:16 mirrors the 16:9 shot-for-shot with the horizontal's mixed audio; layouts come from the hand table per source layout, never from a detector; gates G8-G12 measure the output picture, never input metadata; a vertical that fails parity never reaches Telegram.
- Canonical renderer: `vertical/render_vertical.py` (v1.0 locked 2026-11-04, PBX A+).
- Layout tables: `vertical/layout_tables/<channel>_<tile_count>.json`. Unknown channel/tile_count falls back to layout "single" on lip-activity face + WARN line.
- G10 is IMAGE-BASED: Canny edge density + white fraction on bottom 12% band. G12 counts the brand-red ring masks at the card layout positions (DEC-11, pipeline/credit_rings.py). G8 floor is per-segment: `60 * (crop_w/1080)^2`.
- Audio is extracted from the horizontal final and muxed over the vertical picture — identical by construction.
- **23a (VO VISUAL SOURCE):** Every VO visual (intro, bridge, signoff) in the 9:16 render MUST use the vertical's own composited frame as background — never the raw 16:9 source frame. The vertical composited frame is chyron-safe by construction (chyrons cropped out during reframe). Using a 16:9 source frame leaks channel chyrons/tickers through the blur. Unit test T-VO-VIS enforces this.

### LAW 24: PARAMETERISED PIPELINE (added 2026-11-05)
- The `pipeline/` package is the parameterised Pulse Check pipeline. It wraps segment_v1's frozen scripts (render_v12.py, gen_vo.py, scene_shoutout.py, qa_gates.py) with path resolution from `--segment <dir>`.
- segment_v1 scripts are NEVER modified. pipeline/ imports or patches them at runtime.
- Every new segment directory must have: `edl.json`, `cuts_final.json`, `vo_audio/VO_MANIFEST.json`, `sources/`, at minimum.
- `pipeline/channels.json` is the channel registry: slug, display_name, handles, avatar_path, avatar_sha256_prefix, has_chyron, layout_table_key. Every channel appearing in an EDL must be registered.
- Reproduction proof: running pipeline on segment_v1 data must produce output within 0.05s duration and SSIM >= 0.97 vs the approved segment_v12.mp4.

### LAW 25: EDL EDITORIAL RULES (added 2026-11-05)
- `pipeline/edl_rules.py` validates every EDL before it reaches the renderer.
- R1: Hook must end on a statement, not a question.
- R2: No temporal overlap > 1.0s between any clips. Hook may NOT be reused as clip 1.
- R3: VO bridges only after clips ending on statements.
- R4: VO <= 25% runtime. Intro <= 30 words, bridge <= 20, signoff <= 18. One bridge per channel transition.
- R5: 8-25s per clip, >= 2 distinct channels, every channel >= 8s screen time.
- R6: Credits in signoff must match EDL channels in order. Unique avatar hashes.
- R7: Every (channel, tile_count) must have an explicit layout table entry.

### LAW 26: PULSE CHECK STANDING LAWS (added 2026-11-11, PBX: obvious corrections are applied and written here at once)
- L-a SIGN-OFF NAMES ALL: the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical. CHECK: run_fresh.stage_voice HOLDs before render unless the script names exactly credit_rings.credit_channels(edl) (hook first, then clips); G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off and requires spoken == credited (registry names + aliases); VO stems are keyed by hash(text, voice, model). Must-fail: the 2026-11-11 preview (DataDash missing). Must-pass: v2f.
- L-b EDGE WORDS WHOLE: a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay. CHECK: sentence_law.edge_fades places each machine-cut fade (2 frames, shortened down to 10 ms) inside the gap next to the cut, measured from the cut point's level; G17c (sentence_law.gate_g17_edges) requires every frame of both edge words within 1 dB of the unfaded source. Must-fail: the preview's Natalie Brunell tail ('...participated in the Monday rally.'). Must-pass: the L-b re-cut of it; v2f's edges except its two recorded legacy edges.
- L-c DISSENT IS RIGHT UNTIL DISPROVED: a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise. CHECK: run_fresh.stage_gates: a dissenting G3b reading (DEC-12f) or a G3c head / tail failure on an edge stands (HOLD / FAIL) unless G17c and G16's neighbour_clear both pass for that edge.
- L-d PROTECTED PREVIEW: the PBX-approved preview of 2026-11-11 is a protected reference. CHECK: pipeline/regression.sh step 6 (pipeline/check_preview_reference.py): its selection locks, cut points and 9:16 layout must reproduce with the current code; tag ref-pulse-preview-2026-11-11; references/pulse_preview_2026-11-11 (read-only, SHA256SUMS).
- L-e PUNCTUATED BEFORE READ: every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read. CHECK: transcript_store.acquire(prefer_words) returns only a sentence_ready record: the verbatim decode where no stretch reads unpunctuated, else a whisper_words_punct record (marks from a large-v3 batched reference decode with punctuation.PROMPT, onto aligned words only, plus a sentence-initial capital where both decodes end a sentence right before the word, so editorial start_is_boundary reads the reference's own evidence; word keys and timings unchanged; the verbatim record kept; one Whisper model on GPU0 at a time); editorial_select's word pass treats any other record as failed. Must-fail: Altcoin Daily Ov5jg52HqIY's verbatim record (its quote read as one 35.28 s sentence). Must-pass: its restored record (the quote's sentence 161.14-170.08, "Even thinking about the seasonality, ... the midterms.", a valid 8.94 s hook window). Test: pipeline/test_punct_word_pass.py.
- L-f CHANNELS FIRST (DEC-13): story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted. CHECK: editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (a pool runs only when every earlier one produced nothing); cluster_entry (>= 2 channels with a Bitcoin statement, 48 h tier then 72 h max, else stopped with no model call; one statement per channel); a cluster's coverage adjudicates its own statements; every cluster's ledger entry names its channels, claim, statements, counted quotes and the gate that stopped it; a validated model reply is cached by sha256(model, its Ollama digest, context, max_tokens, prompt). MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. Must-produce: today's $74K-pullback statements (4 channels) and ETF-outflow statements (2 channels) reach the model (under the old rule they were in no cluster). Must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements never share a cluster. Test: pipeline/test_dec13_clusters.py.
- L-g WRITTEN FORMS: a check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way. CHECK: segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order, abbreviated scales too ('$40M' = '40 million dollars'), a 'dollars' the ASR also wrote never doubled; thousands separators and trailing full stops dropped, other commas split words, decimals kept; a leak is any word of the next source word heard after the last word); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py.
- R8: Only channels with `has_chyron=true` trigger G10 chyron gate.
- An EDL that fails ANY rule is rejected. The renderer MUST NOT run on a rejected EDL.

### LAW 27 (M20): COMMENTARY MUST EARN ITS PLACE (added 2026-11-06)
- The LLM proposes VO lines; each line must carry a one-line justification.
- Drop any VO line whose justification merely restates what a clip already says.
- Zero bridges allowed. Intro only if the hook needs framing. Sign-off always (signoff.py).
- If a keyword run's passages are self-explanatory, the intro is suppressed entirely.
- Every VO word is a tax on the viewer. Fewer words = better episode.

### LAW 28 (M21): LETTERBOX FOR UNAPPROVED CHANNELS (added 2026-11-06)
- Channels with an approved hand table (layout_status=approved) use their table.
- Every other channel uses layout "letterbox": the full 16:9 frame scaled to 1080 wide, centred on a blurred, darkened (-35%), 1.25x zoomed copy of the same frame. No crop.
- This prevents face-crop artifacts on unknown layouts and preserves all on-screen information.
- The letterbox layout is logged per shot in the vertical override file.
- To promote a channel from letterbox to custom layout: build a hand table, verify via test render, set layout_status=approved in channels.json.

### LAW 26: NEVER RATIONALISE A FAILED GATE (added 2026-11-05)
- A failed gate is a HARD STOP. No "false positive" arguments, no "known limitation" overrides.
- If a gate is wrong, fix the gate BEFORE re-running. Never bypass it.
- Telegram/publishing ONLY after ALL gates PASS AND a vision second-opinion review has no NO verdict.
- If a gate threshold seems wrong (e.g. duration cap for full episodes), add a format flag to the gate — do not lower or skip the threshold.
- The overnight v2 run (commit ba125e19) is the canonical example of what happens when this law is violated: 7 new scripts written instead of using the locked chain, 4 gates rationalised as false positives, Telegram sent anyway. REJECTED by PBX.
