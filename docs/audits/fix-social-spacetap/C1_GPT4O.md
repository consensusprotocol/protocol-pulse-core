## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### `daily_producer.py`

1. **Startup / mode handling**
   - `fast_test` correctly implies `test_mode=True` and `skip_scan=True` at lines 176-179.
   - It wipes `tts_cache` globally on every run at lines 181-185.  
     **Problem:** this is unsafe if two pipeline runs overlap. One run can delete another run’s cache mid-render.

2. **Run directory creation**
   - Test runs use timestamped directories; production uses a date directory at lines 191-195.
   - **Problem:** production always writes to `output/YYYY-MM-DD` and `pulse_check_YYYYMMDD.mp4` (lines 194, 197). A second production run the same day will overwrite/contaminate the first run. This is a real race/corruption risk.

3. **BTC price fetch**
   - `get_btc_price()` has timeouts and fallback (lines 53-71). Good graceful degradation.
   - No retries, but acceptable for non-critical enrichment.

4. **Channel scan / cached transcript load**
   - `skip_scan` loads up to 60 transcript JSON files (lines 230-248).
   - **Edge case:** no validation that transcript JSON has required keys or non-empty transcript text.
   - `open(tf)` at line 236 has no explicit encoding; minor portability issue.

5. **Clip selection**
   - Fast test path is straightforward (lines 263-283).
   - Normal path calls `select_clips(videos)` (line 287).
   - Failure handling for no clips is correct (lines 294-299).

6. **Montage selection**
   - Non-blocking try/except at lines 312-325 is fine.

7. **Clip extraction**
   - Clears `clips/` and stale `pip_preview_*.mp4` in `work/` (lines 329-345).
   - **Good:** avoids stale artifact reuse.
   - Fallback extraction logic (lines 348-406) is reasonable.
   - **Critical logic bug:** hard-fail message says “Need 5 clips from 5 unique channels” (lines 411-412), but actual condition is:
     - fail if `< 3 clips` or `< 2 unique channels` (lines 407-414)
     - This does **not** enforce the stated law/message. It allows 3 clips from 2 channels while claiming 5/5 is required.

8. **Mood/music**
   - Works, but `open(last_track_file).read()` at line 462 leaks a file handle pattern-wise; use context manager.
   - Random selection is fine.

9. **Live signals**
   - Reads JSON and filters streams newer than 6h (lines 502-540).
   - Good defensive parsing.

10. **Social fetch + Space Tap**
   - Social posts fetched once and sorted by likes (lines 541-553). Good single-source-of-truth intent.
   - Space Tap fetched before script generation (lines 554-573), which matches the feature goal.
   - **Potential import fragility:** manually mutating `sys.path` and importing `from scraper import get_best_space_clips` (lines 557-562) is brittle and can import the wrong module if another `scraper.py` exists earlier on path.

11. **Script generation**
   - Fast test uses `_build_fast_test_script()` (lines 575-579).
   - Normal mode calls `generate_from_clips(...)` with `social_posts_sorted` and `live_context` (lines 581-586).
   - **Correctness issue:** Space Tap clips are added to `selections` before script generation (line 564), but after script generation the code comments “Space Tap entries may be in script” (line 592) without validating they actually were included. If LLM ignores them, no enforcement exists.

12. **TTS**
   - `generate_dialogue_audio(dialogue, audio_dir)` at line 609.
   - **Likely bug:** `dialogue` is assigned only after script generation at line 593. In fast-test mode, that’s okay because assignment happens before Step 6. No issue there.
   - Success count compares generated files against `speech_lines` count (lines 610-613), but `speech_lines` includes all host lines from script, including possibly malformed entries with missing text. Minor mismatch risk.

13. **Manifest / preflight**
   - Manifest build is non-blocking (lines 616-630).
   - Preflight only runs if `episode_manifest.json` exists (lines 633-644).
   - **Issue:** if `build_manifest()` silently fails to write the JSON but returns a dict, preflight is skipped with no warning that the file is missing.

14. **Assembly**
   - `assemble_episode(...)` called at lines 649-651.
   - Failure handling is okay.

15. **Shorts / thumbnail / chapters / podcast / newsletter**
   - All are executed after full render.
   - **Issue:** failures in shorts, thumbnail, podcast, newsletter are not individually guarded. Any exception in these steps aborts the whole pipeline because there is no try/except around them.
   - For a production media pipeline, these should be degradable outputs, not fatal unless explicitly required.

16. **Verify / AV sync / bitrate**
   - `verify_video(final_video)` at line 712.
   - AV sync check and nuclear re-encode are sensible (lines 715-739).
   - **Bug:** after nuclear re-encode, `final_offset` is not updated to `recheck`; analytics later stores stale offset (line 941).
   - **Bug:** low bitrate only logs an error (lines 749-750) but does not affect `passed`, quality gate, or return value.

17. **Post-render QC**
   - Non-blocking (lines 756-770).
   - **Issue:** QC failure does not affect `passed` either. The pipeline can report success despite QC FAIL.

18. **Summary / manifest / quality gate**
   - Writes manifest before quality gate (lines 834-851), then rewrites after adding quality score (lines 903-905).
   - Fine.
   - **Bug:** `timing["13_quality_gate"]` is set after manifest rewrite, but manifest is not rewritten again afterward, so final manifest misses that timing field.

19. **Upload logic**
   - Upload only if feature flag enabled and `should_upload(quality_score)` true (lines 860-887).
   - `elif quality_score < 85` at line 888 is inconsistent with `should_upload(...)` abstraction. If `should_upload()` threshold differs from 85, behavior diverges.
   - If auto-upload disabled and score >=85, logs “disabled”; okay.

20. **Stage brief / analytics / format multiplier**
   - Stage brief gated on score >=85 (lines 908-929).
   - Analytics save is non-blocking (lines 930-947).
   - Format multiplier launches detached subprocess (lines 954-982).
   - **Resource leak:** `stdout=open(..., "w")` at line 971 leaves file descriptor unmanaged in parent.
   - **Correctness issue:** both stage brief and format multiplier are labeled `[STEP 14]` (lines 912, 958). Cosmetic but confusing.

21. **Post-render health check**
   - `_post_render_health_check()` checks file existence, size, duration, audio stream (lines 127-171).
   - **Critical inconsistency:** this runs *after* quality gate, upload, stage brief, analytics, and format multiplier (lines 983-1009). So an episode can be uploaded and distributed before failing health check.
   - Return value is `passed and hc_passed` (line 1010), but by then side effects already happened.

22. **`main()`**
   - Runs pipeline, then always fires tweet machine asynchronously regardless of success (lines 1050-1058).
   - **Bug:** tweet machine should probably not run if pipeline failed. Current behavior can publish downstream content from a failed render state.

---

#### `script_writer.py`

1. **Prompting**
   - Prompt is detailed and strongly constrains output. Good.
   - It explicitly supports Space Tap and social ordering.

2. **Tag extraction**
   - `_extract_segment_tags()` strips `[TAG]` prefixes and maps them to `type` (lines 215-234).
   - **Mismatch with prompt/spec:** prompt says tag must remain inside text for TTS (lines 138-146 in prompt), but code strips it out. Maybe intended, but the code and prompt disagree.

3. **Clip formatting**
   - `_format_clips_info()` uses `video_title` (line 245), but upstream selections in `daily_producer` use `title` in some places. This may reduce prompt quality if `video_title` is absent.

4. **Narrative context**
   - Loads and staleness-checks context correctly.

5. **Social order validation**
   - `_validate_social_tweet_order()` parses handles from `social_posts_raw` and narration (lines 302-375).
   - **Major logic flaw:** it “fixes” mismatches by reordering `social_segment` dialogue entries (lines 356-373), but does **not** rewrite the text inside those entries. If line A mentions @foo and line B mentions @bar, swapping entries may preserve order only superficially and can break surrounding narrative continuity.
   - Also relies on `@handle` appearing in narration, while prompt explicitly says not to read handles aloud and use natural names (prompt lines 70, 162). So this validator may often do nothing.

6. **Headline generation**
   - Good defensive cleanup.

7. **`generate_from_clips()`**
   - Social data fallback is okay.
   - Prompt assembly is okay.
   - Calls `call_llm(...)` and retries malformed JSON (lines 647-671). Good.
   - **Critical issue:** after parsing, there is almost no structural validation:
     - no guarantee first line is host 2
     - no guarantee all non-clip lines are host 2
     - no guarantee every clip rank appears exactly once
     - no guarantee Space Tap clip indices align with provided clips
     - no guarantee social segment is skipped when no data
   - `_enforce_setup_per_clip()` only ensures missing setup lines, not full structure.

8. **Fallback script**
   - Functional, but does not include required bracket tags in text except not at all (lines 753-770). If TTS depends on tags, fallback loses voice-mode behavior.
   - Also does not support social or Space Tap fallback.

---

#### `social_fetcher.py`

1. **Curated daily tweets**
   - Loads and dedups by handle (lines 29-46).
   - **Correctness issue:** dedup happens before sorting by likes. If curated file contains multiple tweets from same handle, the first one wins even if lower quality.

2. **Raw tweet study**
   - Sorts by recency + engagement (lines 57-68).
   - Filters recent tweets within 7 days (lines 70-81).
   - Dedups by handle and truncates (lines 83-102).
   - Good enough.

3. **Timezone handling**
   - Uses `datetime.utcnow()` at line 71 while also using aware datetimes elsewhere. It normalizes with `replace(tzinfo=None)` at line 78, so it works, but it’s messy.

---

## SECTION 2: LAW COMPLIANCE

The “governing laws” section in the package is blank, so only laws explicitly embedded in code/comments/spec can be assessed.

### 1. **SOLE HOST / PBX-only**
**PARTIAL**
- Prompt enforces PBX-only and host 2 only: `script_writer.py:52-57`
- Code normalizes `host:1 -> host:2`: `script_writer.py:222-224`, `313-315`, `413-415`, `684-686`
- Fast test script uses only host 2: `daily_producer.py:77-101`
- **Partial because** there is no hard validation rejecting any non-`2` non-clip host values after LLM output. A malformed `"host": 3` or `"host": "PBX"` would slip through.

### 2. **Space Tap fetched before script generation**
**COMPLIANT**
- Fetch occurs before Step 5 script generation: `daily_producer.py:541-573`
- Added to `selections["space_tap_clips"]`: `daily_producer.py:564`

### 3. **No fabricated social data**
**COMPLIANT**
- `social_fetcher.py` returns empty list if no real data: `109-111`
- Prompt explicitly says skip if none: `script_writer.py:161-162`
- `generate_from_clips()` passes `"NONE — skip social segment entirely"` when empty: `514-515`

### 4. **Tweet order: first tweet card shown = first referenced**
**PARTIAL**
- Sorting by likes in producer: `daily_producer.py:546-550`
- Prompt explicitly requires strict order: `script_writer.py:105`, `162`
- Validator attempts enforcement: `script_writer.py:302-375`
- **Partial because** enforcement is weak and text/order can still diverge; swapping entries is not a reliable semantic fix.

### 5. **Bitcoin only / never write BTC in narration**
**PARTIAL**
- Prompt strongly enforces this: `script_writer.py:39-40`, `69`
- But producer itself uses `btc_price` labels and fast-test title `"Fast Test — {btc_price}"`: `daily_producer.py:103`, `221-224`
- **Partial because** no post-generation validation scans narration text for forbidden “BTC”.

### 6. **Under 12 minutes / 8-15 min law**
**PARTIAL / internally inconsistent**
- Prompt says “Under 12 minutes”: `script_writer.py:49`
- Health check enforces 8-15 min: `daily_producer.py:152-156`
- These conflict. The code is not aligned with its own law set.

### 7. **End with “Stay sovereign.”**
**PARTIAL**
- Prompt requires it: `script_writer.py:71`
- Fast test and fallback do it: `daily_producer.py:100`, `script_writer.py:768`
- **Partial because** no validator ensures LLM output actually ends that way.

### 8. **Every clip must have a setup before it**
**PARTIAL**
- Repair function exists: `script_writer.py:705-746`
- **Partial because** it only inserts missing setups; it does not ensure exactly one setup per clip, nor verify ordering beyond insertion before `CLIP`.

### 9. **Only run format multiplier after episode fully rendered and QC-passed**
**VIOLATION**
- Comment says QC-passed required: `daily_producer.py:955-956`
- Actual condition is only `is_enabled("multi_format_output") and passed`: `957`
- Post-render QC result is never incorporated into `passed`: `756-770`
- So format multiplier can run even when QC fails.

### 10. **Post-render health/quality gate before distribution**
**VIOLATION**
- Upload happens before health check: `daily_producer.py:860-887`
- Health check runs later: `983-1009`
- This violates sane release gating.

---

## SECTION 3: SECURITY

### Findings

1. **Shell / subprocess safety**
   - Most subprocess calls use argument lists, not shell strings: good.
   - No obvious shell injection in shown files.
   - Paths passed to ffmpeg/ffprobe are internally generated, not user input.

2. **Secrets**
   - No hardcoded API keys found.
   - Reads `RESEND_API_KEY` from env: `daily_producer.py:113-116`
   - Hardcoded email addresses are present (`pulse@protocolpulse.io`, `contact@consensusprotocol.org`) at lines 118-120; not secret, but should be config.

3. **Unvalidated filesystem writes**
   - Writes many files under `run_dir`, which is internally generated.
   - No direct user-controlled path injection in shown code.

4. **Import path manipulation**
   - `sys.path.insert(0, BASE)` at `daily_producer.py:24`
   - Dynamic insertion of `x_spaces_scraper` path at `557-560`
   - This is a supply-chain / module shadowing risk if filesystem contents are compromised.

5. **Rate limiting / API exhaustion**
   - No throttling, locking, or singleton protection around expensive external calls:
     - channel scan
     - Claude/LLM calls
     - ElevenLabs TTS
     - YouTube upload
   - If this script can be triggered concurrently, one operator mistake or scheduler bug can burn paid API quota fast.

6. **Authentication bypass / SQL injection**
   - Not applicable in shown files; no routes or SQL here.

### Security assessment
- No obvious injection vulnerability in these files.
- Main security weakness is **operational safety**: uncontrolled concurrent runs, dynamic import path mutation, and no guardrails around paid external services.

---

## SECTION 4: FRONTEND QUALITY

No frontend/UI code was provided. Cannot assess layout, responsiveness, async states, or visual quality.

**Verdict:** N/A for this package.

---

## SECTION 5: BACKEND QUALITY

### Strengths
- Many external calls have timeouts (`requests.get(..., timeout=5)`, ffprobe timeout 30, ffmpeg timeout 600).
- Several non-critical steps degrade gracefully with warnings instead of crashing.
- Logging is generally present and readable.

### Weaknesses

1. **Concurrency safety is poor**
   - Global TTS cache wipe: `daily_producer.py:181-185`
   - Shared production output dir per day: `191-197`
   - Shared `.last_track.txt`: `456-488`
   - These are all race-prone.

2. **Failure isolation is inconsistent**
   - Some steps are non-blocking (manifest, preflight, QC, stage brief).
   - Others like shorts/thumbnail/newsletter/podcast are unguarded and can crash the whole pipeline.

3. **Quality gates are not real gates**
   - `verify_video()` determines `passed`, but bitrate failure and QC failure do not change it: `712-770`
   - Health check happens after upload/distribution: `860-887`, `983-1009`

4. **Logging context**
   - Generally decent, but some broad `except Exception` blocks suppress root causes too much:
     - BTC fetch: `55-70`
     - social fetch: `544-552`
     - stage brief, analytics, etc.
   - For production debugging, include exception type and context consistently.

5. **Resource handling**
   - Unmanaged file opens:
     - `open(last_track_file).read()` at `462`
     - `stdout=open(..., "w")` in `Popen` at `971`
     - tweet machine log file at `1054`
   - Not catastrophic in a one-shot script, but sloppy.

6. **Cron/job behavior**
   - If this is cron-driven, it exits nonzero on failure, good.
   - But it also launches tweet machine regardless of success: `1050-1058`, which is bad job hygiene.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

Material gaps only:

1. **No hard structural validator after LLM generation**
   - A professional pipeline would validate and repair the script against a schema and business rules before TTS/render:
     - host values
     - clip order
     - social order
     - Space Tap alignment
     - required outro
     - forbidden terms
   - Right now too much is “prompt and pray.”

2. **No true release gating**
   - Bloomberg/Blockworks-grade systems do not upload before health/QC pass.
   - Here, upload can happen before final health check and despite QC failure.

3. **No run isolation / idempotency**
   - World-class pipelines are safe under retries and concurrent runs.
   - This one uses shared caches and shared daily output paths.

4. **Weak observability**
   - There is logging, but no structured event log, no per-step status artifact, no machine-readable failure taxonomy, no lockfile/run-state tracking.

### What is already good
- The pipeline is thoughtfully decomposed into stages.
- There is meaningful graceful degradation in several places.
- The social + Space Tap integration order is conceptually correct.
- The prompt quality is strong and editorially specific.

---

## SECTION 7: SCORES

- Backend logic:    68/100
- Frontend/UI:      N/A
- Error handling:   64/100
- Security:         74/100
- Performance:      66/100
- Law compliance:   61/100
- World-class gap:  58/100
- OVERALL:          66/100

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Move post-render health/QC before upload and downstream distribution | `video_pipeline_v3/daily_producer.py:860-887, 983-1009` | episodes can be uploaded and propagated before failing health checks or QC

P0 CRITICAL | Fix production run isolation by using unique run directories and per-run artifact names | `video_pipeline_v3/daily_producer.py:191-197` | concurrent or repeated same-day runs will overwrite outputs and corrupt state

P0 CRITICAL | Stop wiping shared global TTS cache; use per-run cache directory | `video_pipeline_v3/daily_producer.py:181-185` | overlapping runs can delete each other’s audio mid-pipeline

P0 CRITICAL | Enforce actual clip/channel minimums instead of misleading weak check | `video_pipeline_v3/daily_producer.py:407-414` | pipeline claims 5 unique clips/channels but can pass with only 3 clips from 2 channels

P1 HIGH     | Make post-render QC affect `passed` and format-multiplier gating | `video_pipeline_v3/daily_producer.py:756-770, 955-979` | secondary outputs can launch from QC-failed renders despite comments claiming otherwise

P1 HIGH     | Add strict schema/business-rule validation for LLM output | `video_pipeline_v3/script_writer.py:640-694` | malformed scripts can silently pass into TTS/render and create broken episodes

P1 HIGH     | Replace social-order “reordering” with actual validation/fail-or-rewrite logic | `video_pipeline_v3/script_writer.py:356-373` | current fix can preserve semantic mismatches and still show wrong tweet/card pairing

P1 HIGH     | Do not fire tweet machine when pipeline fails | `video_pipeline_v3/daily_producer.py:1050-1058` | downstream publishing can occur from failed or incomplete runs

P1 HIGH     | Guard shorts/thumbnail/podcast/newsletter steps individually with graceful degradation | `video_pipeline_v3/daily_producer.py:661-707` | non-core asset failure can crash an otherwise successful render

P1 HIGH     | Update `final_offset` after nuclear re-encode | `video_pipeline_v3/daily_producer.py:733-736, 941` | analytics and final reporting can store stale AV-sync data

P2 MEDIUM   | Rewrite manifest after adding `timing["13_quality_gate"]` or set timing before writing | `video_pipeline_v3/daily_producer.py:903-906` | final manifest is internally inconsistent and misses final timing data

P2 MEDIUM   | Validate forbidden narration terms and required ending text post-generation | `video_pipeline_v3/script_writer.py:682-694` | prompt-only enforcement is insufficient for editorial laws

P2 MEDIUM   | Use context managers for all file opens, including subprocess log handles | `video_pipeline_v3/daily_producer.py:462, 971, 1054` | leaks descriptors and reduces operational cleanliness

P2 MEDIUM   | Sort curated social posts by likes before dedup/truncation | `video_pipeline_v3/utils/social_fetcher.py:35-45` | current selection can choose weaker tweets from the same handle

P2 MEDIUM   | Replace dynamic `sys.path` import hack for Space Tap with explicit package/module import | `video_pipeline_v3/daily_producer.py:557-562` | brittle import behavior and module shadowing risk

P3 LOW      | Resolve conflicting duration laws (“under 12 minutes” vs 8-15 minutes) | `video_pipeline_v3/script_writer.py:49, 136`, `video_pipeline_v3/daily_producer.py:152-156` | creates editorial confusion and inconsistent gating

P3 LOW      | Fix duplicate step numbering for stage brief and format multiplier | `video_pipeline_v3/daily_producer.py:908-929, 954-982` | confusing logs and operator UX

P3 LOW      | Align prompt claim about tags staying in text with actual tag-stripping behavior | `video_pipeline_v3/script_writer.py:138-146, 215-234` | documentation/code mismatch increases maintenance risk

---

## SECTION 9: THE ONE THING

Build a hard post-LLM/post-render validation gate that can block upload unless the script structure, social/Space ordering, QC, and health checks all pass.

---

## SECTION 10: FINAL VERDICT

No, this is not production-ready yet for a premium automated media pipeline. The biggest issues are broken release gating, unsafe concurrent-run behavior, and overreliance on prompt compliance without hard validation; fix those first before merging.