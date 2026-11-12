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
- L-c DISSENT IS RIGHT UNTIL DISPROVED: a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise. CHECK: run_fresh.stage_gates: a dissenting G3b reading (DEC-12f) or a G3c head / tail failure on an edge stands (HOLD / FAIL) unless G16's neighbour_clear passes and G17c, MEASURED ON THE FINAL FILE OF THAT FORMAT (sentence_law.edges_on_final: the bytes being approved, their constant gain removed, every frame of the edge word compared), passes for that edge; a proof from the prepared clip is never accepted (amended by the orchestrator addendum 2026-11-11 '22:00', GPT-cut F03). Test: test_release_auth / test_word_diff TestSpanMatches; sentence_law.edge_word_fidelity refuses an alignment that leaves a word frame uncompared (GPT-cut F07).
- L-d PROTECTED PREVIEW: the PBX-approved preview of 2026-11-11 is a protected reference. CHECK: pipeline/regression.sh step 6 (pipeline/check_preview_reference.py): its selection locks, cut points and 9:16 layout must reproduce with the current code; tag ref-pulse-preview-2026-11-11; references/pulse_preview_2026-11-11 (read-only, SHA256SUMS).
- L-e PUNCTUATED BEFORE READ: every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read. CHECK: transcript_store.acquire(prefer_words) returns only a sentence_ready record: the verbatim decode where no stretch reads unpunctuated, else a whisper_words_punct record (marks from a large-v3 batched reference decode with punctuation.PROMPT, onto aligned words only, plus a sentence-initial capital where both decodes end a sentence right before the word, so editorial start_is_boundary reads the reference's own evidence; word keys and timings unchanged; the verbatim record kept; one Whisper model on GPU0 at a time); editorial_select's word pass treats any other record as failed. Must-fail: Altcoin Daily Ov5jg52HqIY's verbatim record (its quote read as one 35.28 s sentence). Must-pass: its restored record (the quote's sentence 161.14-170.08, "Even thinking about the seasonality, ... the midterms.", a valid 8.94 s hook window). Test: pipeline/test_punct_word_pass.py.
- L-f CHANNELS FIRST (DEC-13): story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted. CHECK: editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (a pool runs only when every earlier one produced nothing); cluster_entry (>= 2 channels with a Bitcoin statement, 48 h tier then 72 h max, else stopped with no model call; one statement per channel); a cluster's coverage adjudicates its own statements; every cluster's ledger entry names its channels, claim, statements, counted quotes and the gate that stopped it; a validated model reply is cached by sha256(model, its Ollama digest, context, max_tokens, prompt). MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. Must-produce: today's $74K-pullback statements (4 channels) and ETF-outflow statements (2 channels) reach the model (under the old rule they were in no cluster). Must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements never share a cluster. Test: pipeline/test_dec13_clusters.py.
- L-g WRITTEN FORMS: a check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way. CHECK: segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order, abbreviated scales too ('$40M' = '40 million dollars'), a 'dollars' the ASR also wrote never doubled; thousands separators and trailing full stops dropped, other commas split words, decimals kept; a leak is any word of the next source word heard after the last word); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py.
- L-h TEXT READ AS SPOKEN: transcript text is read as the words it stands for before any chunk, quote check or model sees it: caption HTML entities are decoded ('S&amp;P' = 'S&P') and a Whisper word split into tokens is read whole ('$81 ,000' = '$81,000'); the stored record is never rewritten. CHECK: transcript_store.read_text builds every chunk's text; story_semantics._norm decodes entities and joins split tokens for quote checks; the embedding cache is versioned (t2) so vectors match the read text. Must-fail / must-pass: Altcoin Daily's 'S&P 500' quote and Natalie Brunell's '$81,000' quote against their real excerpts (pipeline/test_caption_entities.py).
- L-i THE CLAIM IS THE EVENT (DEC-13 a): a channel cluster's claim is the event its coverage is judged against: its query is derived from the claim alone and the model never re-reads it as another event. CHECK: story_semantics.derive_story_query: a transcript_cluster item is derived from the claim with CLUSTER_NOTE (no label summary) and its underlying_event is the claim verbatim (the model's reading kept as underlying_event_derived); wire items byte-identical. Test: test_caption_entities TestClusterClaimIsTheEvent; real model (DoD 20:13): Natalie Brunell and Coin Bureau then both count for the election sell-off / ETF-outflow claim.
- L-j RELEASE IS AUTHORISED ON THESE BYTES (red-team order 2026-11-11 '21:55', A): 'all release gates passed' means every REQUIRED gate ran, on samples, unwaived, on exactly the bytes that are sent. CHECK: pipeline/release_auth.py is the one authorisation every send path uses: exact gate inventory v1 (REQUIRED rows exactly 'PASS' with evidence executed and samples >= 1; MONITORING rows present with an exact verdict, reported, not deciding: addendum '22:15' item 4; any other or missing row = blocker); run_fresh writes ATTESTATION.json last (holds anywhere = HOLD; executed code at the launch revision; the finals and manifests must be the bytes the gates measured); authorise() re-hashes both finals, EDL, manifests, gate report, verification pack and sheets before the first send; telegram.deliver_run checks each file's digest again before its send, checkpoints every message, never resends an unknown outcome; the legacy send_telegram_preview is removed; replays are never deliverable. Tests: test_release_auth.py (the fail-closed mutation family), test_telegram_delivery.py, test_failure_blocks.py.
- L-k ONE CANONICAL FORM (orchestrator 2026-11-11 '21:10'): every text comparison in the pipeline uses pipeline/canon.py; two strings a listener hears as the same words compare equal, and a different number, unit, sign, name, negation or dropped word never does. CHECK: canon.canon_tokens / canon_aligned / same (entities, unicode, split tokens, numbers as values, currency and percent spoken order, signs, apostrophes kept); routed into quote verification, selection anchors, edge words, G3 / G3b, G18 (word_diff keeps units and signs; a repeat-only difference is decided by the audio, sentence_law.span_matches: GPT-cut F04 / F05), G20, G1 / G13 (token runs, never substrings), PIN approved text. Tests: test_canon.py (200 real sentences x mutations equal; real differences unequal; TestSites fails any ad-hoc normaliser outside canon.py).
- L-n DELIVERY IS THE MEASURE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "pls lock these changes into law"): the pipeline exists to deliver publishable videos, and the one number reported to PBX is videos delivered per day. A HOLD on a day when a line-up that passes our rules existed in the sources is a DEFECT of the selector (a miss), not a safe outcome. CHECK: every HOLD at editorial (or, under L-q, at mining / packaging) runs the blind oracle + judge on that run's universe (pipeline/oracle, branch pp-backtest, once merged); when it finds an accepted line-up the miss is logged with the first stage that lost it (MISS record in the run dir) and goes to the bible. Not yet wired. Tonight's instance: fresh_20261112_050611 HELD at editorial while the oracle's line-up 1 was judged to pass our rules (ORACLE.json sha256 e923e91fa3d05621844449244100ded681c916bf8d06d0aa4a7ec3f9e64bc77a): a miss (E-FAIL-043 family).
- L-o INTEGRITY IS HARD, TASTE BENDS (orchestrator 2026-11-12 '01:50', amended '01:55' with L-q): two classes of rule, never mixed. INTEGRITY (hard, fail closed, never relaxed to ship): (1) every clip is verbatim whole sentences, what is spoken matching the locked sentences word for word (G16 / G18); (2) intact edges: no clipped or faded edge word (G17, L-b); (3) each clip stands alone, or is made to stand by the VO line before it WITHOUT changing its meaning; (4) Bitcoin-only; (5) >= 2 channels per video; (6) recent content (currentness); (7) credits card = EDL set = spoken sign-off set (G12 / G15 / G20, L-a); (8) release authorisation bound to the exact bytes (L-j); (9) nothing measured is never a pass (L-m, branch hardening-redteam); (10) the partner / guest source rule; (11) VO FIDELITY (new, '01:55'): the VO never puts words in a speaker's mouth: it may not attribute to a speaker a claim, stance or number that is not in that speaker's clip, may not imply two speakers were answering each other when they were not, and every fact the VO itself asserts is supported by a clip in the video or a verified source in PROVENANCE; a VO-fidelity check with must-fail fixtures must exist before any moments-first video is labelled a pass. REMOVED from integrity by the '01:55' amendment: 'same development from >= 2 channels' (now one packaging style among several, L-q). TASTE (targets that RANK candidates, never reject one when nothing better exists): the 8-12 s hook and 12-20 s clip duration windows; the hook / clip score floors; a sentence opening on a conjunction ('And', 'So', 'But') when it still stands alone in context. A whole sentence always beats a duration window: selection prefers passages inside the targets, and when no line-up fits inside them it takes the best line-up that passes our rules outside them and records each deviation and its size in PROVENANCE and in the Telegram caption. The only hard duration rule is the format: total runtime 60-70 s (PBX's format). CHECK: EVIDENCE asked by the '01:50' order (no number invented): CLOCK: the windows are measured on SENTENCE-LOCKED WHISPER WORD timing, never caption timing (editorial_select.py:49-50 define them, :1180 applies them; the words come from transcript_store.acquire(prefer_words=True), editorial_select.py:880, and only a sentence_ready record, whisper_words / whisper_words_punct, transcript_store.py:404-410, counts); the blind oracle's durations are caption-line timing, another clock, which a pinned run re-measures on locked words. APPROVED PASSAGES (locked word span): Nov 11 preview hook 9.08 s, clips 12.34 / 18.70 / 16.66 s; v2f hook 9.02 s, clips 10.70 / 11.54 / 14.44 s: PBX approved every length from 9.02 to 18.70 s, two clips under today's 12 s minimum among them; tonight's near-misses missed a window by 0.10-1.86 s (hooks 12.12, 12.74, 7.88, 7.0, 6.14 s; clips 11.9, 11.14, 11.02, 8.74 s). FORMAT: the approved preview's finals run 71.08 s (both formats), 1.08 s over 70; its four passages fill 58.17 s of the final, leaving 12.91 s of VO, cards and transitions. PROPOSAL: no fixed per-passage outer bound (no evidence supports one: nothing was ever rejected for a passage's length, and the approved range already spans 9.02-18.70 s); the one hard bound is the line-up total, checked BEFORE render where the line-up is chosen (selector / packager): passages + VO + fixed cards inside the 60-70 s format, i.e. at the preview's measured 12.91 s of non-passage time, passages totalling about 47-57 s; any per-passage limit is then arithmetic (70 s minus the fixed time minus the other passages), never a constant. For PBX: the approved preview itself ran 71.08 s; whether the format is checked on the final's runtime with a tolerance is PBX's call. WIRING (code change; two audit cycles; must-fail tests proving every INTEGRITY rule still rejects): into the moments-first miner / packager (L-q) and the shared validation (sentence lock, pinned validation); the story-first selector is retired ('01:58'). Until wired, the existing code still applies the windows and floors as hard filters.
- L-p CADENCE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "i need one new video every few hrs once this thing is live and operational. ideally every 3-5 hrs"): once operational the target is one NEW video every 3-5 hours; it supersedes the daily target as the goal, and the daily rate remains the first milestone. No schedule is installed without PBX. CHECK: design consequences, requests and notes, no code yet: (1) NOVELTY: a video is NEW when its development differs from every video delivered in the previous 24 h, or it carries a materially new fact on the same development; the story ledger enforces it (integrity class). Under L-q the proposed reading is: none of its sentence ids was delivered in the previous 24 h and its angle differs from every delivered video's, or it carries a materially new fact (open for the orchestrator). (2) SUPPLY: the 72 h universe barely moves in 3-5 h, so each cycle ingests what was published since the last one and the channel universe must be wide enough; pipeline_pp_backtest is asked (its REQUESTS file) for the DISTINCT developments per day with a line-up that passes our rules, as the oracle finds them in the saved universes. (3) RUN TIME: a full cycle must fit comfortably inside 3 h on GPU0 alone. Measured: tonight's editorial stage took 70.2 min (fresh_20261112_050611, 4213 s): about 50 min of gemma3:27b calls (397 calls, 230 cache hits; reply-cache writes from +1.4 to +70.2 min), about 19 min in three Whisper word passes, each a GPU0 swap (48 h pool +20 to +29 min, 72 h pool +33 to +39, wire pool +64 to +67), under 1 min universe + embeddings (cached). The last complete render path (pinned_20261111_172202) took 51.3 min after selection: render 17.9, gates 15.6, verify 13.4, prepare 1.6, layout 1.2, cut + sentence law + voice 1.1, review 0.6 min. A cycle is about 2 h: inside 3 h, not comfortably (no room for a second candidate after a HOLD). The time goes to model calls (~50 min), render + gates + verify (~47 min) and Whisper swaps (~19 min).
- L-q MOMENTS FIRST, THEN PACKAGE (orchestrator 2026-11-12 '01:55'; PBX 01:48: "i want you to start looking for the stuff that is most social media and engagement friendly. not all segments you clip need to be 100% same exact topic so long as any PBX MAX VO can stitch the two in a logical clever way that actually allows for points to be made etc. perhaps we analyze best of moments across every few hrs new content first.. then decide how to package it and how to optimzie for views etc. now THIS is the strategy"; '01:58': "pls drop the old video and start this new process"): moments-first selection is the product; story-first selection is retired, and the DEC-13 clusters (L-f) become one input, not the gate. STEP 1 MINE: each cycle, over the content published since the last cycle (plus the recent window), find the best MOMENTS: whole stand-alone sentences from partner / guest sources, scored for social engagement (a strong opinion, a surprising number, a quotable line, a named figure, stakes, emotion, a clean hook in the first 2 s), by sentence id, never rewritten. STEP 2 PACKAGE: choose the set of moments that makes the best video and the angle that ties them; the moments need not be the same development: the PBX MAX voiceover stitches them with bridges that make a point, logically and cleverly. STEP 3 OPTIMISE: hook choice, order, title / caption for views. Integrity is L-o's amended class, VO fidelity included. CHECK: a moments-first run replaces the gates that assumed one development (any same-event / topic check on the line-up) with the VO-fidelity gate, ONLY for moments-first runs and only once that gate exists with its must-fail corpus passing; every other integrity gate is unchanged ('01:58'). Build: pipeline_pp_selectid builds the miner and packager (pipeline/moments.py, package.py, trend_brief.py, the VO-fidelity checker) on its ids-only contract (pipeline/select_by_id.py, eligibility.py); pipeline_pp_backtest measures supply under this rule; the integrator wires and audits them when they report DONE. The first delivery goes to Telegram as REVIEW ONLY ('first moments-first package; selection + VO by the new path, not yet merged/audited') with its duration deviations listed per L-o. Not yet built.
- L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's out-of-memory: "let's make sure that never happens again. what can we do rn to fix this??"): (1) ONE OWNER: every code path that loads anything on GPU0 (gemma via Ollama, Whisper, the face detector / vision gates, NVENC, the preflight's own model checks, GPU test sessions, the backtest) takes the gpu0.py lease first: no lease, no load; (2) ONE MODEL AT A TIME by construction: one function swap_to(model) unloads whatever is resident (Ollama keep_alive=0 confirmed via the GPU0 listener, torch empty_cache, the Whisper object deleted), then VERIFIES by nvidia-smi that GPU0's free memory is at least the incoming model's known requirement plus margin before loading; every stage calls it, nothing calls a loader directly; the preflight leaves GPU0 as empty as it found it and asserts that; (3) BOUNDED SELF-HEAL, not a silent retry: on CUDA out-of-memory, release everything this run owns, wait until nvidia-smi shows the memory free (timeout), retry the SAME step ONCE, both attempts in PROVENANCE; a second failure is a HOLD naming every process on GPU0 (pid, name, MiB); an out-of-memory never surfaces as a different error: the HOLD reason carries the real cause; (4) FOREIGN PROCESSES: at run start and before every swap, a process using GPU0 memory without the lease HOLDs the run at once, named; nothing is killed that the run did not start; GPU1 stays quarantined and untouched; (5) TESTS: a must-fail that loads a dummy allocation on GPU0 before each stage and proves the stage refuses or recovers as specified, and a test that runs env -> pinned -> render -> gates back to back twice and shows peak GPU0 memory per stage in a table, which every REPORT.md carries from now on. CHECK: in progress; it outranks hardening batches 18 / 19 and must be in place before the first moments-first render ('01:58'). Done so far: stage_pinned releases GPU0 before Whisper (456a440f, E-FAIL-052). The GPU0 paths are enumerated in the DoD (file:line, wired or not). It supersedes branch hardening-redteam's uncommitted GPU0 lease draft (batch 20), which is rebuilt to this law.
- L-s CONTEXT INTEGRITY (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; a new HARD gate, separate from VO fidelity; the reviewers' unanimous #1 blind spot): a verbatim whole sentence can still misrepresent its speaker once lifted. For every selected moment the inputs are the source's speaker-turn-aware transcript from at least 90 s before (back to the start of the question / turn) to 60 s after, the video's title and description, the selected sentence ids, and the finished package (order, adjacent clips, VO, title, caption). STEP A (context only, the package hidden): a model from a different vendor than the writer states who is speaking; whose view it is (own sincere / attributed to someone else / hypothetical / conditional / sarcastic / question / reading aloud / ad read); the referent of every pronoun and of 'this / that / today'; any governing condition or time frame; any retraction or qualification in the window. STEP B (the package only): what an ordinary viewer concludes the speaker asserts. PASS only if: the speaker's own sincere assertion; every referent inside the clip; no unmet condition and no reversal; the in-context proposition entails the viewer takeaway with the same polarity and no stronger certainty; no implied relation (agreeing / answering / rebutting) between speakers who were not in the same source video, whether by sequence, bridge or title, not only by banned words. Any 'uncertain' is a FAIL. Repair is ONLY extending the clip by whole locked sentences and re-checking, or dropping the MOMENT and repacking; never writing the missing context into the VO. CHECK: must-fail corpus >= 40 (steelman, quoting an opponent, sarcasm, a conditional split across sentences, an unresolved pronoun, 'some people say', a stale 'today / just', an answer without its question, a later retraction, false dialogue by sequence, the wrong speaker) AND a must-pass corpus >= 20 with the false-reject rate reported (a checker that rejects everything is a broken selector). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): the title, the caption and any on-screen text are free text exactly like the VO: every number, name and claim is audible in a clip of this video; quotes are verbatim; no stronger certainty; the framing verbs destroys / slams / exposes / admits / confirms / caught are banned unless they are the source's own word; no name of a person who does not appear; no second-person financial imperative. ONE title and ONE caption go through VO fidelity and context integrity (L-s) with the video, and are bound into the release authorisation (L-j) with BOTH files: one manifest holds both renders, the title, the caption, the source intervals, the credits and the gate results; any change after the gates re-runs them. CHECK: release_auth's attested set grows by the title, caption and manifest; telegram.deliver_run sends that one title and caption. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-u HARD EXCLUSIONS AND SCORING (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; engagement scoring otherwise selects exactly what burns partners): never auto-selected: accusations of crime / fraud / insolvency / dishonesty against a named person or company; one partner attacking another; buy / sell / leverage imperatives and guaranteed-return claims; single-source 'breaking' factual claims; ad reads and sponsor segments; third-party media played inside a partner's video. Down-weighted and capped: price predictions (at most one per video, always framed as that speaker's prediction, never as fact in the title), doom, politics not about Bitcoin policy. 'Named figure' stops being a positive axis on its own; contempt / outrage is a penalty, not a boost. Per-channel fairness: at most ONE clip per channel per video, at most 20 s per source video, per-channel daily and weekly appearance caps (numbers proposed from the saved universes), topic and speaker cooldowns beyond the 24 h moment rule. CHECK: exclusions in code, before any score (a rank weight is not an exclusion); the cap numbers come from the saved universes (pp-backtest). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-v SPEAKER AND TRANSCRIPT TRUTH (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) WHO IS SPEAKING: a moment may not span a speaker change; a person is NAMED in VO / title only when verified (title / description metadata, or diarisation above a stated confidence), otherwise the show is credited. (2) every gate today trusts one Whisper transcript: for the selected sentences only, a second independent recognition pass (a different model / settings) runs against the SOURCE audio; any disagreement on a number, a name or a negation makes that token unusable in VO / title or drops the moment. (3) time-sensitive language ('just', 'today', price levels) requires the source's original publish time inside the window; re-uploads are excluded. CHECK: the second pass is a GPU0 load (law L-r: through gpu0.swap_to); diarisation confidence threshold stated with its evidence. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-w OPERATING RULES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) DIVISION OF LABOUR: the local gemma mines and scores by id; CODE does the duration packing (VO length and the credits absorb the slack, so 60-70 s is met by arithmetic, not by the model); a FRONTIER model picks the angle and writes VO / title / caption; a different vendor rules fidelity and context; measured dollars per video are reported. (2) NO ZERO-VIDEO NIGHTS FROM THE CHECKER: on a VO reject, regenerate once, then fall back to a plain factual VO ('Next, <show> on <topic>.') rather than dropping the package; a package is dropped only for a context-integrity or exclusion failure, and then repacked from the next moments. (3) STORY-FIRST IS KEPT as a preferred package TYPE when >= 2 channels cover one development (the safest format); the packager chooses the type. (4) the trend brief runs in SHADOW first (logged, zero weight) next to a free baseline signal from our own corpus (topic frequency across partner channels, last 24 h); when enabled its weight is capped at ~10-15% of the score, its output forced into a closed Bitcoin topic taxonomy, raw post text never enters any prompt, and a person-trend may boost only moments where that person is the speaker. (5) the Telegram approval message carries, per clip, a link to the source video ~30 s before the clip, the flagged risks, both file hashes, the one title and caption. (6) REPORTED NUMBERS: generated, delivered, approved-without-edit, published, rejected with reason, corrected / challenged; not delivered alone. A hold is a selector defect only when the blind oracle's witness package ALSO passes context integrity, exclusions and fidelity; the oracle runs on selector holds only (not ingestion / GPU holds). No integrity rule is ever demoted to ranking without PBX in writing. CHECK: amends L-n (the reported numbers; the oracle on selector holds only, its witness under L-s / L-u / VO fidelity) and L-q (story-first kept as a package type). The backtest session is asked separately to compare, on the same saved universes, story-first with bent taste rules vs moments-first vs frontier packaging, blind-judged for publishability. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built.
- L-x NO SINGLE MODEL, ULTRON FIRST (orchestrator note 2026-11-12 '02:45'; PBX: "work this video pipeline to get us off of any one llm and onto ultron and to be fully autonomous and top notch"): every model role (mining, scoring, packaging / angle, VO / title writing, fidelity verdict, context verdict, trend brief) sits behind ONE provider interface with at least two interchangeable back-ends, and the run continues when any one vendor is down or out of credit (OpenAI ran dry mid-run on Nov 12). The DEFAULT back-end of each role is the local model on Ultron wherever it meets the quality bar; a frontier model or Heimdall is used only where a measured comparison shows local is not good enough, and that comparison is re-run so roles migrate to local as it improves. No role hard-codes a vendor or a model name outside the provider config. Generator and blind judge are always different models. CHECK: per role, a blind A/B on saved data: local gemma3:27b (run by the integrator under the GPU0 lease, law L-r; the builders provide the harness and prompts) vs frontier vs Heimdall: quality verdict, failures, latency, dollars. Heimdall spend: the 90% tripwire is a NOTIFY ('HEIMDALL SPEND AT 90%' at the top of the session's STATE) and the role falls back to its other back-ends; work never halts for the cap. Not yet built (pp-selectid phase 2 and pp-ingest build behind the interface; the integrator runs the local legs).
- AMENDMENTS 2026-11-12 '02:30': L-n by L-w (6) (reported numbers: generated / delivered / approved-without-edit / published / rejected with reason / corrected or challenged; the blind oracle runs on selector holds only, and a hold is a selector defect only when its witness package also passes L-s, L-u and VO fidelity); L-o by L-s and L-t (context integrity and all audience-facing text join the integrity class; an integrity rule is never demoted to ranking without PBX in writing, L-w (6)); L-q by L-w (3) (story-first is kept as a preferred package type when >= 2 channels cover one development; the packager chooses the type).
- AMENDMENT 2026-11-12 '06:00' (orchestrator, on PBX's instruction; L-o / L-q, a TASTE rule re-set for the new product, never an integrity rule): EDL rule R4 was written for the story-first product, where the VO was glue; under L-q the host makes points. For packages of type 'moments' ONLY (EDL package_type, recorded by pinned.build_edl from the package): VO share <= 45 % of the TOTAL estimated runtime (orchestrator '06:22'; RULING 9 '08:29': 45 %, was 40 %, for a 3.5 s punchline clip to reach PBX's hard 60 s; intro + lines, each words / 2.5 + the renderers' 1.0 s pre-roll); one VO line per slot: after the hook (intro), after each clip, and after the LAST clip (the takeaway; render16 and render_vertical play it before the shout-out, and render a VO line of any length); a line with no slot fails; the estimated runtime (hook + clips + VO + 14.30 s, the approved preview's measured tail) stays HARD inside 60-70 s; word caps unchanged. Story-type and untyped pins keep the old R4 (25 %, one bridge per channel transition). CHECK: edl_rules._r4_moments, pinned.moments_vo (after the last clip only for type 'moments'); must-fail tests test_edl_rules TestR4Moments (VO share 45.1 % and 45.5 % rejected, 45 % passes; runtime 59.9 and 70.1 rejected, 60.0 and 70.0 pass; a line with no slot rejected) and test_pinned test_a_moments_package_may_close_on_a_takeaway_after_the_last_clip.
- AMENDMENT 2026-11-12 '08:40' (RULING 10; the code is 1136e56d, recorded here with ruling 12): for packages of type 'moments' the TAKEAWAY (the VO line after the LAST clip) has its own word cap MOMENTS_TAKEAWAY_WORD_CAP = 30 (the intro's); bridges BETWEEN clips keep BRIDGE_WORD_CAP = 20. CHECK: edl_rules._r4_moments; must-fail test test_edl_rules TestR4Moments test_the_takeaway_has_its_own_cap_and_bridges_keep_theirs (31 takeaway words rejected, 30 pass; a 21-word bridge between clips rejected).
- AMENDMENT 2026-11-12 '09:32' (RULING 12, the orchestrator under PBX's delegation; a named exception to Law 20 / M2; corrects L-o's format line): 60-70 s is PBX's FORMAT TARGET, not a hard limit on the measured final ('hard' in L-o was a mislabel). Packaging arithmetic keeps aiming at 60-70 s (R4's estimated runtime above is unchanged). The MEASURED final runtime is ACCEPTED from 58.0 to 72.0 s in both aspects; a value outside 60-70 s is recorded as a deviation (G5 data 'duration_deviation') and named in the Telegram caption; outside 58-72 s it fails. 16:9 and 9:16 still agree within the existing parity tolerance (G14c, unchanged). CHECK: segment_v1/qa_gates.gate_g5 (G5_DURATION_ACCEPT_S, G5_DURATION_TARGET_S; was 60-120 s, R2-14); must-fail tests test_round2_mustfail TestDurationWindow (57.9 and 72.1 rejected, 58.0 and 72.0 accepted, both aspects; exact deviation strings; the old 102.9 s vertical now rejected). Cause for next time, assigned to the builder: packaging uses the MEASURED VO audio durations once the voice stage has produced them, before render (tonight R4's 2.5 w/s made the VO 3.14 s too long; the voice measured 2.91 w/s; E-FAIL-061).
- AMENDMENT 2026-11-12 '10:02' (RULINGS 13-15, the orchestrator under PBX's delegation; RULING 11 of '08:55' implemented with 13). RULING 13 (G14 samples speech, per window): a G14 sample window counts only if at least 60 % of it lies inside the LOCKED words' speech (the lock's word timestamps minus the cut's measured pauses, gates.g14_run_speech). A window below that is not a sample (not pass, not fail, not counted), and a retake must qualify the same way. Unchanged: >= 3 conclusive samples per talking head, every conclusive one in sync, fewer = HOLD (nothing measured is never a pass). RULING 11: a talking head whose clear region (outside VO and dissolves) is shorter than 6.75 s gets its sample windows spread evenly over that region at a stride >= 0.75 s (the windows may overlap), inside G14's own margins; a region that cannot hold 3 such windows is not measurable (HOLD). CHECK: gates.gate_g14 (G14_MIN_SPEECH 0.6, G14_EVEN_BELOW_S 6.75, G14_MIN_STRIDE_S 0.75; g14_locked_speech, g14_run_speech, g14_even_offsets) and run_fresh.stage_gates. Tests: test_g14_sampling TestRulings13And11 and its 9:16 twin, on the Nov 12 moments render: clip_02 (4.666 s) passes on its 4 speech windows and its near-end window over the pause is not a sample; clip_02 200 ms late FAILS; 2 qualifying windows HOLD; a 2 s clear region is not measurable. Protected references: the same per-segment verdicts before and after (the Nov 11 preview, the corrected Nov 10 cut, v2f). RULING 14 (G20, spelling): an unusual proper name gets spoken-form aliases in the channel registry when it enters it. Saifedean Ammous: 'seifedean amos', 'saifedean amos', 'safedean ammous', 'saifedean ammus'. G20_NAME_RATIO stays 0.85. CHECK: pipeline/channels.json; test_g20_signoff test_ruling_14_spoken_form_aliases_are_heard_and_an_absent_name_still_fails. RULING 15 (what is gated is what is spoken): the renderer speaks its own sign-off template. For the 37c5b5f5 render it is kept (it names every channel, so L-a holds), and its difference from the package's sealed sign-off line is a named caption deviation. REQUEST to the builder: the package seals the renderer's actual template text, generated by the same code, so VO fidelity judges the words that will be heard.
- AMENDMENT 2026-11-12 '10:20' (RULINGS 16-17, the orchestrator under PBX's delegation). RULING 16 (G17c, law L-b): a frame is compared only if the SOURCE frame is above max(the local gap level, -96 dBFS), the 16-bit quantisation floor below which no audio exists to clip; the 1.0 dB bar and everything else are unchanged. CHECK: sentence_law.EDGE_WORD_FLOOR_DBFS in edge_word_fidelity; tests: test_edge_words TestRuling16Floor (a real 3 dB onset loss at -50 dBFS FAILS; differences only below -96 dBFS PASS) and TestRuling16Nov12; the 'rally' must-fail unchanged. RULING 17 (sentence-lock text adjudication, integrity fail-closed): when a pinned run's own decode differs from the pin's approved text inside a locked span, a difference on a number, a name or a negation ALWAYS holds (L-v 2). Otherwise the independent second recogniser (scribe_v1) on the acquired window decides. If it reads the approved words at every difference, the lock takes the approved text (two independent decodes agree) and G18 compares the final against that text. If it reads the run's decode, or neither, the run HOLDs naming the three readings. CHECK: pinned.adjudicate_lock (build_edl), word_diff.gate_g18 (the adjudicated lock is the identity reference), pipeline/second_recogniser.py; tests: test_ruling17_lock (the real Nov 12 clip_01 head, where scribe_v1 reads 'I think' against the pin's 'I mean,', HOLDS; a negation flip holds at 2-1); the Nov 10 G18 fixtures still fail.
- AMENDMENT 2026-11-12 '10:36' / '10:51' (RULINGS 18-19, the orchestrator under PBX's delegation). RULING 18 (extends DEC-12f to G18 and the sentence lock; integrity fail-closed): when independent decodes of the SOURCE split on ONE non-critical token inside a locked span, the lock records both attested readings. That is the case where the run's decode and the second recogniser read one word and the pin's approved text another. G18 passes that token only if the final's decode reads one of the readings AND the prepared clip's audio over the token is the source's (G17c's frame comparison: 1 dB above the floor, best alignment). The final bytes' reading is kept as evidence only: the music bed and loudnorm make a 1 dB frame test impossible there. An unattested word or an acoustic mismatch FAILS. A number, name or negation difference (L-v 2), or two or more ambiguous tokens in one span, HOLD. The ambiguity is recorded in PROVENANCE (lock_alternatives) and named in the caption. RULING 19: the frame-comparison floor for G17c and the token check is -90 dBFS, set from a measured pause frame of AAC codec noise in run pinned_20261112_135315 (-92.9 / -94.2 dBFS, 1.22 dB apart; every frame above -90 within 0.52 dB); it replaces ruling 16's -96. CHECK: pinned.adjudicate_lock, word_diff.gate_g18 / edges / diff (alts), sentence_law.span_fidelity and EDGE_WORD_FLOOR_DBFS. Tests: test_ruling17_lock (19: a third word, the token's audio 3 dB down or silenced, can/can't, 15/50, one/two and two ambiguous tokens all fail or hold; either reading on the untouched audio passes) and test_edge_words TestRuling16Floor (codec noise between -96 and -90 passes; a 3 dB onset loss at -50 fails).
- LETTERS: L-l (batch B) and L-m (batch C) are in branch hardening-redteam and arrive with its merge; its drafted E law becomes L-y (L-s..L-x were taken by the '02:30' and '02:45' orders) and its GPU0 draft is superseded by L-r.
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
