# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: fix-social-spacetap
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REVIEW: PROTOCOL PULSE - FIX-SOCIAL-SPACETAP

I have conducted a thorough forensic review of the provided codebase for the `fix-social-spacetap` feature in the `main` branch of Protocol Pulse. Below, I address each section of the review task with detailed analysis, specific line citations, and actionable recommendations. My goal is to ensure the highest quality for this premium Bitcoin intelligence product.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis (daily_producer.py):**
The primary user flow in `daily_producer.py` involves generating a daily Bitcoin highlight video by scanning channels, selecting clips, generating scripts, producing audio, assembling videos, and handling post-production tasks like shorts and uploads. Here's a step-by-step evaluation:

1. **Channel Scanning (Lines 227-253):** The logic correctly handles both live scanning and cached transcript loading based on the `--skip-scan` flag. However, there's a potential silent failure if `glob.glob()` returns no files or if cached JSON files are malformed—there's no validation of JSON content before appending to `videos` (Lines 235-247). This could lead to runtime errors later.
2. **Clip Selection (Lines 263-305):** The `select_clips()` function is called with proper fallback for fast-test mode. However, there's no explicit check for API failures beyond returning an empty list, which could silently fail if `select_clips()` encounters an unhandled exception (Line 287).
3. **Clip Extraction (Lines 327-417):** The extraction process wipes stale files (Lines 330-344), which is good for correctness, but the fallback mechanism for quality issues (Lines 349-406) might loop indefinitely if no suitable clips are found due to exhausted candidates (Line 405). There's no cap on retry attempts.
4. **Script Generation (Lines 575-587):** The script generation correctly uses a fallback for fast-test mode (Line 578), but relies on external API calls (Claude) without explicit retry logic for transient failures (Line 583).
5. **Assembly and Verification (Lines 647-754):** The assembly process (Line 649) and verification (Line 712) are robust, with a nuclear re-encode fallback for AV sync issues (Lines 719-738). However, if `nuclear_tmp` exists but fails to replace `final_video` due to permissions, it could leave stale files (Line 734).
6. **Quality Gate and Upload (Lines 854-905):** The quality gate logic correctly computes a score and decides on upload (Line 860), but there's no handling for upload failures beyond logging the result (Line 883), which could leave the pipeline in an inconsistent state.

**Potential Issues:**
- **Race Conditions:** No explicit handling of concurrent pipeline runs. If multiple instances of `daily_producer.py` run simultaneously, they could overwrite each other's `run_dir` (Line 190-194) or interfere with shared resources like `tts_cache` (Line 182).
- **Edge Cases:** Empty input handling is partial. If `videos` is empty after scanning (Line 256), the pipeline fails gracefully, but if `extracted_clips` is empty after extraction (Line 428), it fails without a fallback script generation.
- **Silent Failures:** Several external API calls (e.g., BTC price fetch, Lines 55-71) catch exceptions but return fallback values without logging the root cause, making debugging difficult in production.

---

### SECTION 2: LAW COMPLIANCE

Since no specific governing laws were provided in the audit package under "GOVERNING LAWS," I will assume compliance is based on internal pipeline laws mentioned in the code comments (e.g., duration, solo host). If specific laws are intended, they should be explicitly listed in future audits.

- **Solo Host Law (daily_producer.py, Line 78):** COMPLIANT. The script enforces PBX as the sole host (host: 2) in fast-test mode and script generation (Lines 78, 224 in `script_writer.py`).
- **Episode Duration Law (daily_producer.py, Line 153):** PARTIAL. The post-render health check enforces a duration of 8-15 minutes (480-900s, Lines 152-155), but there's no proactive adjustment during script generation or assembly if the estimated duration is outside this range.
- **Bitcoin-Only Content (script_writer.py, Line 39):** COMPLIANT. The script prompt explicitly restricts content to Bitcoin, excluding altcoins and other crypto topics (Line 39).
- **Quality Threshold (daily_producer.py, Line 899):** COMPLIANT. The quality gate holds episodes with scores below 85 for review (Line 899), adhering to implicit quality laws.

**Violation Note:** Without explicit laws in the spec, I cannot fully assess compliance. Future audits should include the full list of governing laws for precise evaluation.

---

### SECTION 3: SECURITY

- **SQL Injection:** No direct SQL queries are present in the provided code. SQLAlchemy ORM is mentioned in the tech stack, but not used in these files. If user input reaches ORM elsewhere, it should be validated.
- **Authentication Bypasses:** Not applicable in these scripts as the

## GPT4O — CYCLE 1 OUTPUT
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

17. **Post-render

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — FIX-SOCIAL-SPACETAP — CYCLE 1
Generated: 2026-03-22 07:04
Models: grok, gpt4o (+1 failed: gemini — 403 PERMISSION_DENIED / leaked API key)

---

## SCORES

*Note: Neither model provided explicit numeric scores. Scores below are synthesized from severity language, issue density, and qualitative judgments expressed in each review.*

| Subsystem        | Gemini | GPT-4o | Grok  | Consensus |
|------------------|--------|--------|-------|-----------|
| Correctness      | N/A    | 52/100 | 61/100| **56/100** |
| Law Compliance   | N/A    | 55/100 | 70/100| **62/100** |
| Security         | N/A    | 60/100 | 65/100| **62/100** |
| Frontend Quality | N/A    | N/A    | N/A   | **N/A (no frontend code reviewed)** |
| Backend Quality  | N/A    | 58/100 | 62/100| **60/100** |
| **Overall**      | N/A    | **56/100** | **63/100** | **59/100** |

> Gemini failed entirely. Consensus is derived from 2 models. All findings carry reduced certainty compared to a full 3-model cycle. Second-pass confidence is moderate.

---

## UNANIMOUS FINDINGS
*(Both grok AND gpt4o flagged these — implement unconditionally)*

---

### U1 — Same-Day Production Run Overwrites Prior Output
**File:** `daily_producer.py` · Lines 191–197
**Both models flagged:** Production runs always write to `output/YYYY-MM-DD/` and `pulse_check_YYYYMMDD.mp4`. A second run the same day silently overwrites the first.
**Fix:** Append a short UUID or run-index suffix to production `run_dir` and output filename, or lock the directory with a PID file that fails fast if already present. At minimum, check for directory existence and abort or rotate before writing.

---

### U2 — `tts_cache` Wipe Is Unsafe Under Concurrent Runs
**File:** `daily_producer.py` · Lines 181–185
**Both models flagged:** Cache is wiped globally at startup with no lock. A second overlapping run deletes the first run's TTS audio mid-render, causing silent corruption.
**Fix:** Scope the TTS cache wipe to the current `run_dir` only, or acquire a file-system lock before wiping. Never wipe a shared directory unconditionally at startup.

---

### U3 — No Input Validation on Cached Transcript JSON
**File:** `daily_producer.py` · Lines 230–248
**Both models flagged:** Transcript JSON files are loaded and appended to `videos` without validating required keys or non-empty transcript text. Malformed files propagate silently.
**Fix:** Add a schema check after `json.load()`. At minimum, assert required keys (`transcript`, `channel_id`, `title`) exist and `transcript` is non-empty before appending. Log and skip invalid files.

---

### U4 — Tweet Machine Fires Regardless of Pipeline Success
**File:** `daily_producer.py` · Lines 1050–1058 (gpt4o) / Lines 951+ (grok)
**Both models flagged:** The tweet/notification machine launches asynchronously after the main pipeline block, unconditionally. A failed render can publish downstream social content.
**Fix:** Gate the tweet machine launch behind `if pipeline_success:` (or equivalen

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: video_pipeline_v3/daily_producer.py (1064 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Daily Pulse Check Producer V5 — clip-first pipeline.
   3 | 
   4 | Real YouTube clips from partner channels, host dialogue around them,
   5 | music integration, cold open, avatar shorts.
   6 | 
   7 | Usage:
   8 |   python3 daily_producer.py               # Full daily episode
   9 |   python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  10 |   python3 daily_producer.py --skip-scan   # Use cached transcripts only
  11 |   python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
  12 | """
  13 | import argparse
  14 | import json
  15 | import logging
  16 | import os
  17 | import shutil
  18 | import subprocess
  19 | import sys
  20 | import time
  21 | from datetime import datetime, timezone
  22 | 
  23 | BASE = os.path.dirname(os.path.abspath(__file__))
  24 | sys.path.insert(0, BASE)
  25 | 
  26 | from channel_scanner import scan_all_channels
  27 | from clip_selector import select_clips
  28 | from clip_extractor import extract_all, extract_montage_all, check_av_sync
  29 | from script_writer import generate_from_clips
  30 | from tts_engine import generate_dialogue_audio
  31 | from assembler import assemble_episode, verify_video
  32 | from shorts_cutter import generate_shorts
  33 | from thumbnail_gen import generate_thumbnail
  34 | from chapters import generate_chapters
  35 | from podcast_feed import extract_podcast_audio, generate_rss_item
  36 | from newsletter_embed import generate_email_html, save_newsletter_html
  37 | from music import ensure_music_dir, has_music, has_intro, has_outro
  38 | from utils.feature_flags import is_enabled, load_all as load_flags
  39 | from utils.quality_gate import compute_quality_score, should_upload, format_score_report
  40 | from utils.telegram_alerts import (
  41 |     alert_pipeline_start, alert_pipeline_success,
  42 |     alert_pipeline_failure, alert_quality_hold, alert_upload_success,
  43 | )
  44 | 
  45 | # Setup logging
  46 | logging.basicConfig(
  47 |     level=logging.INFO,
  48 |     format="%(message)s",
  49 | )
  50 | logger = logging.getLogger("Producer")
  51 | 
  52 | 
  53 | def get_btc_price() -> str:
  54 |     """Fetch current BTC price (CoinGecko primary + mempool.space fallback)."""
  55 |     try:
  56 |         import requests
  57 |         r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
  58 |         if r.status_code == 200:
  59 |             usd = r.json()["bitcoin"]["usd"]
  60 |             return f"${usd:,.0f}"
  61 |     except Exception:
  62 |         pass
  63 |     try:
  64 |         import requests
  65 |         r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
  66 |         if r.status_code == 200:
  67 |             usd = r.json().get("USD", 0)
  68 |             return f"${usd:,.0f}"
  69 |     except Exception:
  70 |         pass
  71 |     return "$N/A"  # Fallback - no hardcoded stale price
  72 | 
  73 | 
  74 | def _build_fast_test_script(clips_info: dict, btc_price: str) -> dict:
  75 |     """Build a minimal hardcoded script for fast-test mode (no Claude API call)."""
  76 |     dialogue = []
  77 |     # Cold open — PBX-only (host 2) per SOLO HOST law
  78 |     dialogue.append({
  79 |         "host": 2, "type": "cold_open",
  80 |         "text": f"[COLD_OPEN] Bitcoin at {btc_price}. Let's get into today's pulse check.",
  81 |     })
  82 |     # For each clip, add a setup + clip marker + react
  83 |     for rank, info in sorted(clips_info.items()):
  84 |         channel = info.get("channel", "Unknown")
  85 |         dialogue.append({
  86 |             "host": 2, "type": "setup",
  87 |             "text": f"[NARRATION] Here's what {channel} had to say.",
  88 |         })
  89 |         dialogue.append({
  90 |             "host": "CLIP", "type": "clip",
  91 |             "rank": rank, "source_id": info.get("video_id", ""),
  92 |         })
  93 |         dialogue.append({
  94 |             "host": 2, "type": "react",
  95 |             "text": "[NARRATION] Interesting take. Let's keep moving.",
  96 |         })
  97 |     # Wrap
  98 |     dialogue.append({
  99 |         "host": 2, "type": "wrap",
 100 |         "text": "[WARM] That's the pulse check for today. Stay sovereign.",
 101 |     })
 102 |     return {
 103 |         "episode_title": f"Fast Test — {btc_price}",
 104 |         "dialogue": dialogue,
 105 |         "thumbnail": {"headline": "FAST TEST", "subtext": btc_price},
 106 |     }
 107 | 
 108 | 
 109 | def _send_resend_alert(subject: str, body: str):
 110 |     """Send a non-blocking email alert via Resend."""
 111 |     try:
 112 |         import resend
 113 |         resend.api_key = os.environ.get("RESEND_API_KEY", "")
 114 |         if not resend.api_key:
 115 |             logger.warning("RESEND_API_KEY not set — skipping email alert")
 116 |             return
 117 |         resend.Emails.send({
 118 |             "from": "pulse@protocolpulse.io",
 119 |             "to": ["contact@consensusprotocol.org"],
 120 |             "subject": subject,
 121 |             "html": f"<pre>{body}</pre>",
 122 |         })
 123 |     except Exception as e:
 124 |         logger.warning(f"Resend alert failed: {e}")
 125 | 
 126 | 
 127 | def _post_render_health_check(video_path: str) -> tuple[bool, list[str]]:
 128 |     """Verify rendered video meets quality thresholds.
 129 | 
 130 |     Returns (passed, errors).
 131 |     """
 132 |     errors = []
 133 |     if not os.path.exists(video_path):
 134 |         return False, ["Video file does not exist"]
 135 | 
 136 |     # File size > 50MB
 137 |     size_mb = os.path.getsize(video_path) / (1024 * 1024)
 138 |     if size_mb < 50:
 139 |         errors.append(f"File size {size_mb:.1f}MB < 50MB minimum")
 140 | 
 141 |     # ffprobe checks
 142 |     try:
 143 |         probe = subprocess.run(
 144 |             ["ffprobe", "-v", "quiet", "-print_format", "json",
 145 |              "-show_format", "-show_streams", video_path],
 146 |             capture_output=True, text=True, timeout=30,
 147 |         )
 148 |         info = json.loads(probe.stdout)
 149 |         fmt = info.get("format", {})
 150 |         streams = info.get("streams", [])
 151 | 
 152 |         # Duration 480-900s (PIPELINE_LAWS: 8-15 min)
 153 |         duration = float(fmt.get("duration", 0))
 154 |         if duration < 480 or duration > 900:
 155 |             errors.append(f"Duration {duration:.0f}s outside 480-900s range (8-15 min law)")
 156 | 
 157 |         # Audio stream present
 158 |         audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
 159 |         if not audio_streams:
 160 |             errors.append("No audio stream found")
 161 |     except Exception as e:
 162 |         errors.append(f"ffprobe failed: {e}")
 163 | 
 164 |     passed = len(errors) == 0
 165 |     if not passed:
 166 |         logger.critical(f"POST-RENDER HEALTH CHECK FAILED: {errors}")
 167 |         _send_resend_alert(
 168 |             "CRITICAL: Pulse Check render failed health check",
 169 |             f"Video: {video_path}\nErrors:\n" + "\n".join(f"  - {e}" for e in errors),
 170 |         )
 171 |     return passed, errors
 172 | 
 173 | 
 174 | def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
 175 |                  fast_test: bool = False) -> bool:
 176 |     # Fast test implies test + skip-scan
 177 |     if fast_test:
 178 |         test_mode = True
 179 |         skip_scan = True
 180 | 
 181 |     # Wipe TTS cache before each run to prevent stale audio
 182 |     tts_cache = os.path.join(BASE, "tts_cache")
 183 |     shutil.rmtree(tts_cache, ignore_errors=True)
 184 |     os.makedirs(tts_cache, exist_ok=True)
 185 |     logger.info("TTS cache wiped")
 186 | 
 187 |     ts = datetime.now(timezone.utc)
 188 |     date_str = ts.strftime("%Y%m%d")
 189 |     time_str = ts.strftime("%Y%m%d_%H%M%S")
 190 | 
 191 |     if test_mode:
 192 |         run_dir = os.path.join(BASE, "output", f"test_{time_str}")
 193 |     else:
 194 |         run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))
 195 | 
 196 |     os.makedirs(run_dir, exist_ok=True)
 197 |     final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
 198 |     timing = {}
 199 |     t_pipeline_start = time.time()
 200 | 
 201 |     # Ensure music directory exists
 202 |     ensure_music_dir()
 203 | 
 204 |     # Log feature flags at startup
 205 |     flags = load_flags()
 206 |     logger.info(f"Feature flags: {json.dumps(flags)}")
 207 | 
 208 |     # Telegram alert at pipeline start
 209 |     if is_enabled("telegram_alerts"):
 210 |         alert_pipeline_start(date_str, test_mode)
 211 | 
 212 |     print("\n" + "=" * 70)
 213 |     print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
 214 |     mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
 215 |     print(f"  {mode_label}Run {time_str}")
 216 |     print(f"  Output: {run_dir}")
 217 |     print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
 218 |     print("=" * 70)
 219 | 
 220 |     # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
 221 |     print("\n[STEP 1/12] FETCHING BTC PRICE...")
 222 |     t0 = time.time()
 223 |     btc_price = get_btc_price()
 224 |     print(f"  BTC: {btc_price}")
 225 |     timing["1_price"] = round(time.time() - t0, 2)
 226 | 
 227 |     # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
 228 |     print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
 229 |     t0 = time.time()
 230 |     if skip_scan:
 231 |         # Load cached transcripts from transcript dir
 232 |         import glob
 233 |         transcript_dir = os.path.join(BASE, "transcripts")
 234 |         videos = []
 235 |         for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:60]:
 236 |             with open(tf) as f:
 237 |                 data = json.load(f)
 238 |                 videos.append({
 239 |                     "video_id": data.get("video_id", ""),
 240 |                     "title": data.get("title", ""),
 241 |                     "channel": data.get("channel", ""),
 242 |                     "duration": data.get("duration", 0),
 243 |                     "upload_date": "",
 244 |                     "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
 245 |                     "transcript_text": data.get("text", ""),
 246 |                     "timestamped_text": data.get("timestamped_text", ""),
 247 |                 })
 248 |         print(f"  Loaded {len(videos)} cached transcripts")
 249 |     else:
 250 |         whisper_model = "tiny" if test_mode else "base"
 251 |         videos = scan_all_channels(model_size=whisper_model)
 252 |         print(f"  Scanned: {len(videos)} videos with transcripts")
 253 |     timing["2_scan"] = round(time.time() - t0, 2)
 254 | 
 255 |     if not videos:
 256 |         print("\n  [FAIL] No videos found — cannot produce episode")
 257 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 258 |         if is_enabled("telegram_alerts"):
 259 |             alert_pipeline_failure(date_str, "scan", "No videos found")
 260 |         return False
 261 | 
 262 |     # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
 263 |     if fast_test:
 264 |         print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
 265 |         t0 = time.time()
 266 |         # Build minimal selections from cached videos without calling Claude
 267 |         fast_clips = []
 268 |         for i, v in enumerate(videos[:2], 1):
 269 |             text = v.get("transcript_text", "")
 270 |             fast_clips.append({
 271 |                 "rank": i,
 272 |                 "video_id": v["video_id"],
 273 |                 "channel": v.get("channel", ""),
 274 |                 "title": v.get("title", ""),
 275 |                 "quote": text[:100] if text else "No transcript",
 276 |                 "why": "fast-test auto-select",
 277 |                 "start_seconds": 60,
 278 |                 "end_seconds": 90,
 279 |             })
 280 |         selections = {"clips": fast_clips}
 281 |         clips = fast_clips
 282 |         print(f"  Auto-selected: {len(clips)} clips (no API call)")
 283 |         timing["3_select"] = round(time.time() - t0, 2)
 284 |     else:
 285 |         print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
 286 |         t0 = time.time()
 287 |         selections = select_clips(videos)
 288 |         clips = selections.get("clips", [])
 289 |         print(f"  Selected: {len(clips)} clips")
 290 |         for c in clips:
 291 |             print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
 292 |         timing["3_select"] = round(time.time() - t0, 2)
 293 | 
 294 |     if not clips:
 295 |         print("\n  [FAIL] No clips selected — cannot produce episode")
 296 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 297 |         if is_enabled("telegram_alerts"):
 298 |             alert_pipeline_failure(date_str, "select", "No clips selected")
 299 |         return False
 300 | 
 301 |     # In test mode, use only top 2 clips
 302 |     if not fast_test and test_mode and len(clips) > 2:
 303 |         selections["clips"] = clips[:2]
 304 |         clips = selections["clips"]
 305 |         print(f"  [test] Truncated to {len(clips)} clips")
 306 | 
 307 |     # Save selections
 308 |     sel_path = os.path.join(run_dir, "selections.json")
 309 |     with open(sel_path, "w") as f:
 310 |         json.dump(selections, f, indent=2)
 311 | 
 312 |     # ── Step 3b: Select independent montage clips (Qwen, free) ──────────
 313 |     print("\n[STEP 3b] SELECTING MONTAGE CLIPS (local Qwen)...")
 314 |     try:
 315 |         from clip_selector import select_montage_clips
 316 |         montage_selections = select_montage_clips(videos)
 317 |         montage_clips_sel = montage_selections.get("clips", [])
 318 |         montage_sel_path = os.path.join(run_dir, "montage_selections.json")
 319 |         with open(montage_sel_path, "w") as f:
 320 |             json.dump(montage_selections, f, indent=2)
 321 |         print(f"  Montage: {len(montage_clips_sel)} independent clips selected")
 322 |     except Exception as e:
 323 |         print(f"  Montage selection failed ({e}) — montage will reuse Pulse Check clips")
 324 |         montage_selections = None
 325 | 
 326 |     # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
 327 |     print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
 328 |     t0 = time.time()
 329 |     # FIX 2: Wipe clips/ dir completely to prevent stale files from prior renders
 330 |     clip_dir = os.path.join(run_dir, "clips")
 331 |     if os.path.exists(clip_dir):
 332 |         shutil.rmtree(clip_dir)
 333 |         logger.info(f"  Wiped stale clips dir: {clip_dir}")
 334 |     os.makedirs(clip_dir, exist_ok=True)
 335 |     # Also wipe stale pip_preview files from work dir
 336 |     work_dir = os.path.join(run_dir, "work")
 337 |     if os.path.exists(work_dir):
 338 |         import glob as _pip_glob
 339 |         for stale_pip in _pip_glob.glob(os.path.join(work_dir, "pip_preview_*.mp4")):
 340 |             try:
 341 |                 os.remove(stale_pip)
 342 |             except OSError:
 343 |                 pass
 344 |         logger.info("  Wiped stale pip_preview files from work/")
 345 |     extracted_clips = extract_all(selections, clip_dir)
 346 |     print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")
 347 | 
 348 |     # ── Quality-aware fallback: retry with ranked alternates ──────────
 349 |     if not test_mode and not fast_test and len(extracted_clips) < 5:
 350 |         used_video_ids = {info["video_id"] for info in extracted_clips.values()}
 351 |         used_channels = {info["channel"] for info in extracted_clips.values()}
 352 |         tried_video_ids = {c["video_id"] for c in clips} | used_video_ids
 353 | 
 354 |         remaining = [v for v in videos
 355 |                      if v["video_id"] not in tried_video_ids
 356 |                      and v.get("channel", "") not in used_channels]
 357 | 
 358 |         if remaining:
 359 |             need = 5 - len(extracted_clips)
 360 |             logger.info(
 361 |                 f"[extractor] Only {len(extracted_clips)}/5 clips passed quality "
 362 |                 f"— selecting fallbacks from {len(remaining)} candidates (need {need})"
 363 |             )
 364 |             fallback_sel = select_clips(remaining)
 365 |             fallback_clips = fallback_sel.get("clips", [])
 366 | 
 367 |             max_rank = max(extracted_clips.keys()) if extracted_clips else 0
 368 |             for fc in fallback_clips:
 369 |                 if len(extracted_clips) >= 5:
 370 |                     break
 371 |                 fc_ch = fc.get("channel", "")
 372 |                 fc_vid = fc.get("video_id", "")
 373 |                 if fc_ch in used_channels or fc_vid in tried_video_ids:
 374 |                     continue
 375 |                 max_rank += 1
 376 |                 fc["rank"] = max_rank
 377 |                 logger.info(
 378 |                     f"[extractor] Clip failed quality — trying fallback candidate "
 379 |                     f"#{max_rank} [{fc_ch}] from selections"
 380 |                 )
 381 |                 fb_result = extract_all({"clips": [fc]}, clip_dir)
 382 |                 if fb_result:
 383 |                     for r, info in fb_result.items():
 384 |                         extracted_clips[r] = info
 385 |                         used_video_ids.add(info["video_id"])
 386 |                         used_channels.add(info["channel"])
 387 |                         tried_video_ids.add(fc_vid)
 388 |                         selections["clips"].append(fc)
 389 |                         logger.info(
 390 |                             f"[extractor] Fallback clip #{r} passed quality — "
 391 |                             f"{info['channel']} ({info['duration']:.1f}s)"
 392 |                         )
 393 |                 else:
 394 |                     tried_video_ids.add(fc_vid)
 395 |                     logger.warning(
 396 |                         f"[extractor] Fallback [{fc_ch}] also failed quality — trying next"
 397 |                     )
 398 | 
 399 |             # Update clips list and re-save selections
 400 |             clips = selections.get("clips", [])
 401 |             with open(sel_path, "w") as f:
 402 |                 json.dump(selections, f, indent=2)
 403 |             logger.info(f"[extractor] After fallback: {len(extracted_clips)}/5 clips")
 404 |         else:
 405 |             logger.warning("[extractor] No fallback candidates — all channels/videos exhausted")
 406 | 
 407 |     if not test_mode:
 408 |         _unique_ch = len({info.get("channel", f"unk_{i}") for i, info in enumerate(extracted_clips.values())})
 409 |         if len(extracted_clips) < 3 or _unique_ch < 2:
 410 |             logger.critical(
 411 |                 f"[PIPELINE] HARD FAIL: Need 5 clips from 5 unique channels, "
 412 |                 f"got {len(extracted_clips)} clips from {_unique_ch} channels."
 413 |             )
 414 |             return False
 415 |     for rank, info in sorted(extracted_clips.items()):
 416 |         print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
 417 |     timing["4_extract"] = round(time.time() - t0, 2)
 418 | 
 419 |     # ── Step 4m: Extract montage clips ───────────────────────────────────
 420 |     if montage_selections and montage_selections.get("clips"):
 421 |         print("\n[STEP 4m] EXTRACTING MONTAGE CLIPS...")
 422 |         try:
 423 |             extract_montage_all(montage_selections, clip_dir)
 424 |             print(f"  Montage clips extracted to {clip_dir}")
 425 |         except Exception as e:
 426 |             print(f"  Montage extraction failed ({e}) — skipping")
 427 | 
 428 |     if not extracted_clips:
 429 |         print("\n  [FAIL] No clips extracted — cannot produce episode")
 430 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 431 |         if is_enabled("telegram_alerts"):
 432 |             alert_pipeline_failure(date_str, "extract", "No clips extracted")
 433 |         return False
 434 | 
 435 |     # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
 436 |     import glob as _glob
 437 |     import random as _random
 438 | 
 439 |     def classify_episode_mood(script_text: str) -> str:
 440 |         """Classify episode mood from clip quotes."""
 441 |         moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
 442 |         lower = script_text.lower()
 443 |         if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
 444 |             moods["tense"] += 3
 445 |         if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
 446 |             moods["confident"] += 3
 447 |         if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
 448 |             moods["contemplative"] += 2
 449 |         if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
 450 |             moods["upbeat"] += 2
 451 |         if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
 452 |             moods["edge"] += 2
 453 |         best = max(moods, key=moods.get)
 454 |         return best if moods[best] > 0 else "confident"
 455 | 
 456 |     def select_music_bed(mood: str, music_dir: str) -> str:
 457 |         # Sprint 1.10: Randomize music, avoid repeating last track
 458 |         last_track_file = os.path.join(music_dir, ".last_track.txt")
 459 |         last_track = ""
 460 |         if os.path.exists(last_track_file):
 461 |             try:
 462 |                 last_track = open(last_track_file).read().strip()
 463 |             except Exception:
 464 |                 pass
 465 | 
 466 |         tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
 467 |         if not tracks:
 468 |             tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
 469 |         if not tracks:
 470 |             # Get all tracks except reserved ones
 471 |             all_tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
 472 |             tracks = [t for t in all_tracks
 473 |                       if os.path.basename(t) not in ("pp_outro.mp3", "pp_background.mp3",
 474 |                                                        "pp_intro.mp3", "pp_transition.mp3")]
 475 |         if not tracks:
 476 |             return ""
 477 | 
 478 |         # Avoid repeating last track
 479 |         if last_track and len(tracks) > 1:
 480 |             tracks = [t for t in tracks if os.path.basename(t) != last_track] or tracks
 481 | 
 482 |         chosen = _random.choice(tracks)
 483 |         try:
 484 |             with open(last_track_file, "w") as f:
 485 |                 f.write(os.path.basename(chosen))
 486 |         except Exception:
 487 |             pass
 488 |         return chosen
 489 | 
 490 |     def select_intro_music(music_dir: str) -> str:
 491 |         tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
 492 |         return _random.choice(tracks) if tracks else ""
 493 | 
 494 |     # Classify mood from clip quotes
 495 |     clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
 496 |     episode_mood = classify_episode_mood(clip_quotes)
 497 |     music_dir = os.path.join(BASE, "assets", "music")
 498 |     music_bed = select_music_bed(episode_mood, music_dir)
 499 |     intro_music = select_intro_music(music_dir)
 500 |     print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")
 501 | 
 502 |     # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
 503 |     live_context = ""
 504 |     live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
 505 |     try:
 506 |         if os.path.exists(live_signals_path):
 507 |             with open(live_signals_path) as f:
 508 |                 live_data = json.load(f)
 509 |             from datetime import timezone as _tz
 510 |             now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
 511 |             active_streams = []
 512 |             for s in live_data.get("live_streams", []):
 513 |                 # Only include streams from last 6 hours
 514 |                 started = s.get("started_at", "")
 515 |                 try:
 516 |                     started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
 517 |                     age_hours = (now - started_dt).total_seconds() / 3600
 518 |                     if age_hours > 6:
 519 |                         continue
 520 |                 except (ValueError, AttributeError):
 521 |                     continue
 522 |                 source = s.get("source", "youtube_live")
 523 |                 channel = s.get("channel", "unknown")
 524 |                 title = s.get("title", "")
 525 |                 topics = ", ".join(s.get("topics", []))
 526 |                 sentiment = s.get("current_sentiment", 50)
 527 |                 sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
 528 |                 active_streams.append(
 529 |                     f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
 530 |                 )
 531 |             if active_streams:
 532 |                 live_context = "\n".join(active_streams)
 533 |                 print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
 534 |                 for line in active_streams:
 535 |                     print(f"    {line}")
 536 |             else:
 537 |                 print("  Live signals: no active streams in last 6 hours")
 538 |     except Exception as e:
 539 |         logger.warning(f"Live signals read failed: {e}")
 540 | 
 541 |     # ── Step 5a: Fetch social posts + Space Tap BEFORE script generation ──
 542 |     # Social posts: fetch once, sort by likes desc, pass to script_writer
 543 |     sorted_social = []
 544 |     try:
 545 |         from utils.social_fetcher import get_todays_social_posts
 546 |         sorted_social = get_todays_social_posts(max_posts=5)
 547 |         if sorted_social:
 548 |             sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
 549 |             for si, sp in enumerate(sorted_social):
 550 |                 logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
 551 |     except Exception as e:
 552 |         logger.warning(f"Social posts fetch failed: {e}")
 553 | 
 554 |     # Space Tap: fetch X Spaces clips BEFORE script generation so LLM can write dialogue
 555 |     print("[STEP 5a] SPACE TAP -- LIVE X SPACES INTERCEPT...")
 556 |     try:
 557 |         import sys as _sys, os as _os
 558 |         _spaces_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "x_spaces_scraper")
 559 |         if _spaces_path not in _sys.path:
 560 |             _sys.path.insert(0, _spaces_path)
 561 |         from scraper import get_best_space_clips
 562 |         _st = get_best_space_clips(max_clips=3)
 563 |         if _st and _st.get("clips"):
 564 |             selections["space_tap_clips"] = _st["clips"]
 565 |             print(f"  Space Tap: {len(_st['clips'])} clips from {_st.get('spaces_count', 0)} spaces")
 566 |         else:
 567 |             print("  Space Tap: no live spaces — segment skipped")
 568 |     except ImportError as _ste:
 569 |         print(f"  Space Tap: scraper not available ({_ste})")
 570 |     except Exception as _ste:
 571 |         logger.error(f"Space Tap fetch error: {type(_ste).__name__}: {_ste}")
 572 |         print(f"  Space Tap: skipped ({_ste})")
 573 | 
 574 |     # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
 575 |     if fast_test:
 576 |         print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
 577 |         t0 = time.time()
 578 |         script = _build_fast_test_script(extracted_clips, btc_price)
 579 |         timing["5_script"] = round(time.time() - t0, 2)
 580 |     else:
 581 |         print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
 582 |         t0 = time.time()
 583 |         script = generate_from_clips(selections, btc_price=btc_price,
 584 |                                      live_context=live_context,
 585 |                                      social_posts_sorted=sorted_social)
 586 |         timing["5_script"] = round(time.time() - t0, 2)
 587 | 
 588 |     # Attach social posts to script for assembler (single source of truth)
 589 |     if sorted_social:
 590 |         script["social_posts"] = sorted_social
 591 | 
 592 |     # Re-read dialogue AFTER all mutations (Space Tap entries may be in script)
 593 |     dialogue = script.get("dialogue", [])
 594 |     speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
 595 |     clip_markers = [d for d in dialogue if d.get("host") in ("CLIP", "SPACE_CLIP")]
 596 |     print(f"  Title: {script.get('episode_title', 'Untitled')}")
 597 |     print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
 598 | 
 599 |     # Save script
 600 |     script_path = os.path.join(run_dir, "script.json")
 601 |     with open(script_path, "w") as f:
 602 |         json.dump(script, f, indent=2)
 603 | 
 604 | 
 605 |     # ── Step 6: TTS ───────────────────────────────────────────────────────
 606 |     print("\n[STEP 6/12] GENERATING PBX NARRATION AUDIO (ElevenLabs)...")
 607 |     t0 = time.time()
 608 |     audio_dir = os.path.join(run_dir, "audio")
 609 |     audio_data = generate_dialogue_audio(dialogue, audio_dir)
 610 |     successful = sum(1 for l in audio_data.get("lines", [])
 611 |                      if l.get("path") and os.path.exists(l.get("path", "")))
 612 |     print(f"  Audio: {successful}/{len(speech_lines)} lines")
 613 |     print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
 614 |     timing["6_tts"] = round(time.time() - t0, 2)
 615 | 
 616 |     # ── Step 6b: BUILD MANIFEST ─────────────────────────────────────────
 617 |     print("\n[STEP 6b/12] BUILDING EPISODE MANIFEST...")
 618 |     t0 = time.time()
 619 |     try:
 620 |         from manifest_builder import build_manifest
 621 |         episode_manifest = build_manifest(
 622 |             script, audio_data, extracted_clips, run_dir,
 623 |             music_bed=music_bed, btc_price=btc_price,
 624 |         )
 625 |         print(f"  Manifest: {episode_manifest.get('total_segments', 0)} segments, "
 626 |               f"~{episode_manifest.get('total_duration_estimate', 0):.0f}s estimated")
 627 |     except Exception as e:
 628 |         logger.warning(f"Manifest build failed (non-blocking): {e}")
 629 |         episode_manifest = {}
 630 |     timing["6b_manifest"] = round(time.time() - t0, 2)
 631 | 
 632 |     # ── Step 6c: PREFLIGHT CHECK ─────────────────────────────────────────
 633 |     manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
 634 |     if os.path.exists(manifest_json_path):
 635 |         print("\n[STEP 6c/12] PREFLIGHT QC CHECK...")
 636 |         t0 = time.time()
 637 |         try:
 638 |             from qc_pipeline import preflight_check
 639 |             pf_passed, pf_errors, pf_warnings = preflight_check(manifest_json_path)
 640 |             print(f"  Preflight: {'PASS' if pf_passed else 'FAIL'} — "
 641 |                   f"{len(pf_errors)} errors, {len(pf_warnings)} warnings")
 642 |         except Exception as e:
 643 |             logger.warning(f"Preflight check failed (non-blocking): {e}")
 644 |         timing["6c_preflight"] = round(time.time() - t0, 2)
 645 | 
 646 |     # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
 647 |     print("\n[STEP 7/12] ASSEMBLING VIDEO...")
 648 |     t0 = time.time()
 649 |     result = assemble_episode(script, audio_data, extracted_clips, final_video,
 650 |                               btc_price=btc_price, music_bed=music_bed,
 651 |                               intro_music=intro_music)
 652 |     timing["7_assemble"] = round(time.time() - t0, 2)
 653 | 
 654 |     if not result or not os.path.exists(final_video):
 655 |         print("\n  [FAIL] Assembly failed")
 656 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 657 |         if is_enabled("telegram_alerts"):
 658 |             alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
 659 |         return False
 660 | 
 661 |     # ── Step 8: SHORTS ────────────────────────────────────────────────────
 662 |     print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
 663 |     t0 = time.time()
 664 |     shorts_dir = os.path.join(run_dir, "shorts")
 665 |     shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
 666 |                              max_shorts=3 if not test_mode else 1)
 667 |     print(f"  Shorts: {len(shorts)}")
 668 |     timing["8_shorts"] = round(time.time() - t0, 2)
 669 | 
 670 |     # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
 671 |     print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
 672 |     t0 = time.time()
 673 |     thumb_data = script.get("thumbnail", {})
 674 |     top_quote = ""
 675 |     if clips:
 676 |         top_quote = clips[0].get("quote", "")
 677 |     thumb_path = os.path.join(run_dir, "thumbnail.png")
 678 |     generate_thumbnail(
 679 |         thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
 680 |         thumb_data.get("subtext", ""),
 681 |         thumb_path,
 682 |         btc_price=btc_price,
 683 |         top_quote=top_quote,
 684 |     )
 685 |     timing["9_thumbnail"] = round(time.time() - t0, 2)
 686 | 
 687 |     # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
 688 |     print("\n[STEP 10/12] GENERATING CHAPTERS...")
 689 |     t0 = time.time()
 690 |     chapters_path = os.path.join(run_dir, "chapters.txt")
 691 |     generate_chapters(script, audio_data, chapters_path)
 692 |     timing["10_chapters"] = round(time.time() - t0, 2)
 693 | 
 694 |     # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
 695 |     print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
 696 |     t0 = time.time()
 697 |     podcast_path = os.path.join(run_dir, "podcast.mp3")
 698 |     extract_podcast_audio(final_video, podcast_path)
 699 | 
 700 |     email_html = generate_email_html(
 701 |         script.get("episode_title", "Pulse Check"),
 702 |         segments_summary=script.get("segments_summary", []),
 703 |         btc_price=btc_price,
 704 |     )
 705 |     newsletter_path = os.path.join(run_dir, "newsletter.html")
 706 |     save_newsletter_html(email_html, newsletter_path)
 707 |     timing["11_podcast_newsletter"] = round(time.time() - t0, 2)
 708 | 
 709 |     # ── Step 12: VERIFY ───────────────────────────────────────────────────
 710 |     print("\n[STEP 12/12] VERIFYING OUTPUT...")
 711 |     t0 = time.time()
 712 |     passed = verify_video(final_video)
 713 | 
 714 |     # Final AV sync validation
 715 |     final_offset = check_av_sync(final_video)
 716 |     print(f"  Final AV sync offset: {final_offset:+.3f}s")
 717 |     if abs(final_offset) > 0.05:
 718 |         logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
 719 |         nuclear_tmp = final_video + ".nuclear.mp4"
 720 |         nuclear_cmd = subprocess.run([
 721 |             "ffmpeg", "-y",
 722 |             "-fflags", "+genpts+igndts",
 723 |             "-i", final_video,
 724 |             "-c:v", "libx264", "-preset", "medium",
 725 |             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
 726 |             "-r", "30", "-vsync", "cfr",
 727 |             "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
 728 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
 729 |             "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
 730 |             "-movflags", "+faststart",
 731 |             nuclear_tmp,
 732 |         ], capture_output=True, text=True, timeout=600)
 733 |         if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
 734 |             os.replace(nuclear_tmp, final_video)
 735 |             recheck = check_av_sync(final_video)
 736 |             print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
 737 |         elif os.path.exists(nuclear_tmp):
 738 |             os.remove(nuclear_tmp)
 739 | 
 740 |     # Final bitrate validation
 741 |     br_result = subprocess.run(
 742 |         ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
 743 |         capture_output=True, text=True,
 744 |     )
 745 |     try:
 746 |         br_info = json.loads(br_result.stdout)
 747 |         bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
 748 |         print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
 749 |         if bitrate < 3_000_000:
 750 |             logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
 751 |     except Exception:
 752 |         pass
 753 | 
 754 |     timing["12_verify"] = round(time.time() - t0, 2)
 755 | 
 756 |     # ── Step 12b: POST-RENDER QC ─────────────────────────────────────────
 757 |     print("\n[STEP 12b] POST-RENDER QC...")
 758 |     t0 = time.time()
 759 |     try:
 760 |         from qc_pipeline import post_render_qc, save_qc_report
 761 |         manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
 762 |         qc_report = post_render_qc(final_video, manifest_json_path)
 763 |         save_qc_report(qc_report, run_dir)
 764 |         print(f"  QC: {'PASS' if qc_report.get('passed') else 'FAIL'}")
 765 |         for check, val in qc_report.get("checks", {}).items():
 766 |             status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
 767 |             print(f"    [{status}] {check}")
 768 |     except Exception as e:
 769 |         logger.warning(f"Post-render QC failed (non-blocking): {e}")
 770 |     timing["12b_qc"] = round(time.time() - t0, 2)
 771 | 
 772 |     # ── Summary ──────────────────────────────────────────────────────────
 773 |     timing["total"] = round(time.time() - t_pipeline_start, 2)
 774 | 
 775 |     # Video stats
 776 |     r = subprocess.run(
 777 |         ["ffprobe", "-v", "quiet", "-print_format", "json",
 778 |          "-show_format", "-show_streams", final_video],
 779 |         capture_output=True, text=True,
 780 |     )
 781 |     try:
 782 |         info = json.loads(r.stdout)
 783 |         fmt = info.get("format", {})
 784 |         streams = info.get("streams", [])
 785 |         vid = next((s for s in streams if s.get("codec_type") == "video"), {})
 786 |         aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
 787 |         dur = float(fmt.get("duration", 0))
 788 |         sz = int(fmt.get("size", 0)) / 1024 / 1024
 789 |         timing["video_duration"] = round(dur, 1)
 790 |         timing["video_size_mb"] = round(sz, 1)
 791 |     except Exception:
 792 |         vid, aud, dur, sz = {}, {}, 0, 0
 793 | 
 794 |     print("\n" + "=" * 70)
 795 |     print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
 796 |     print(f"  Title:    {script.get('episode_title', 'Untitled')}")
 797 |     print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
 798 |     print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
 799 |     print(f"  Size:     {sz:.1f}MB")
 800 |     print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
 801 |     print(f"  Shorts:   {len(shorts)}")
 802 |     print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")
 803 | 
 804 |     outputs = {
 805 |         "video": final_video,
 806 |         "shorts": [s for s in shorts],
 807 |         "thumbnail": thumb_path,
 808 |         "chapters": chapters_path,
 809 |         "podcast": podcast_path,
 810 |         "newsletter": newsletter_path,
 811 |         "script": script_path,
 812 |         "selections": sel_path,
 813 |     }
 814 | 
 815 |     print(f"\n  OUTPUT FILES:")
 816 |     for name, path in outputs.items():
 817 |         if isinstance(path, list):
 818 |             for p in path:
 819 |                 exists = "Y" if os.path.exists(p) else "N"
 820 |                 print(f"    [{exists}] {os.path.basename(p)}")
 821 |         else:
 822 |             exists = "Y" if os.path.exists(path) else "N"
 823 |             print(f"    [{exists}] {os.path.basename(path)}")
 824 | 
 825 |     print(f"\n  TIMING:")
 826 |     for step, secs in timing.items():
 827 |         if step not in ("video_duration", "video_size_mb"):
 828 |             print(f"    {step:25s}: {secs:.1f}s")
 829 |     print(f"\n  Output: {run_dir}")
 830 |     print("=" * 70)
 831 | 
 832 |     _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)
 833 | 
 834 |     # Save manifest
 835 |     manifest = {
 836 |         "version": "v5",
 837 |         "episode_title": script.get("episode_title", ""),
 838 |         "btc_price": btc_price,
 839 |         "test_mode": test_mode,
 840 |         "timestamp": time_str,
 841 |         "clips_used": [
 842 |             {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
 843 |             for r, info in sorted(extracted_clips.items())
 844 |         ],
 845 |         "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
 846 |         "timing": timing,
 847 |         "success": passed,
 848 |     }
 849 |     manifest_path = os.path.join(run_dir, "manifest.json")
 850 |     with open(manifest_path, "w") as f:
 851 |         json.dump(manifest, f, indent=2)
 852 | 
 853 |     # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
 854 |     print("\n[STEP 13] QUALITY GATE...")
 855 |     t0 = time.time()
 856 |     quality_score = compute_quality_score(manifest_path, video_path=final_video)
 857 |     print(f"  {format_score_report(quality_score)}")
 858 |     manifest["quality_score"] = quality_score
 859 | 
 860 |     if is_enabled("youtube_auto_upload") and should_upload(quality_score):
 861 |         from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
 862 |         # Build YouTube metadata
 863 |         ep_title = script.get("episode_title", "Pulse Check")
 864 |         yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
 865 |         chapters_text = ""
 866 |         if os.path.exists(chapters_path):
 867 |             with open(chapters_path) as f:
 868 |                 chapters_text = f.read()
 869 |         yt_description = build_description(
 870 |             summary=f"{ep_title}\n\nBTC Price: {btc_price}",
 871 |             chapters_text=chapters_text,
 872 |             clips=clips,
 873 |         )
 874 |         topics = [c.get("channel", "") for c in clips]
 875 |         yt_tags = build_tags(topics)
 876 | 
 877 |         print(f"  Uploading to YouTube (unlisted)...")
 878 |         upload_result = yt_upload(
 879 |             final_video, yt_title, yt_description,
 880 |             tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
 881 |         )
 882 |         print(f"  Upload result: {upload_result.get('status')}")
 883 |         if upload_result.get("url"):
 884 |             print(f"  URL: {upload_result['url']}")
 885 |         manifest["upload_result"] = upload_result
 886 |         if is_enabled("telegram_alerts") and upload_result.get("url"):
 887 |             alert_upload_success(date_str, upload_result["url"])
 888 |     elif quality_score < 85:
 889 |         logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
 890 |         hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
 891 |         with open(hold_path, "w") as f:
 892 |             f.write(f"Quality score: {quality_score}/100\n")
 893 |             f.write(f"Threshold: 85\n")
 894 |             f.write(f"Reason: Below quality threshold\n")
 895 |             f.write(f"Episode: {script.get('episode_title', '')}\n")
 896 |             f.write(f"Video: {final_video}\n")
 897 |         manifest["held_for_review"] = True
 898 |         if is_enabled("telegram_alerts"):
 899 |             alert_quality_hold(date_str, quality_score)
 900 |     else:
 901 |         logger.info("YouTube auto-upload disabled in feature flags")
 902 | 
 903 |     # Write final manifest with quality score
 904 |     with open(manifest_path, "w") as f:
 905 |         json.dump(manifest, f, indent=2)
 906 |     timing["13_quality_gate"] = round(time.time() - t0, 2)
 907 | 
 908 |     # ── Step 14: STAGE BRIEF (post Grade-A render) ─────────────────────────
 909 |     if quality_score >= 85:
 910 |         try:
 911 |             from generate_stage_brief import generate_brief
 912 |             print("\n[STEP 14] GENERATING STAGE BRIEF...")
 913 |             t0 = time.time()
 914 |             brief_path = generate_brief(run_dir)
 915 |             if brief_path:
 916 |                 logger.info(f"Stage brief generated: {brief_path}")
 917 |                 print(f"  Stage brief: {brief_path}")
 918 |                 manifest["stage_brief"] = brief_path
 919 |             else:
 920 |                 logger.warning("Stage brief returned None")
 921 |                 print("  Stage brief: skipped (returned None)")
 922 |             timing["14_stage_brief"] = round(time.time() - t0, 2)
 923 |         except Exception as e:
 924 |             logger.warning(f"Stage brief generation failed (non-fatal): {e}")
 925 |             print(f"  Stage brief failed (non-fatal): {e}")
 926 |             timing["14_stage_brief"] = 0
 927 |     else:
 928 |         logger.info(f"Skipping stage brief — quality score {quality_score} < 85")
 929 | 
 930 |     # Save episode performance data (V17)
 931 |     try:
 932 |         from utils.analytics_store import save_episode_performance
 933 |         perf_data = {
 934 |             "date": ts.strftime("%Y-%m-%d"),
 935 |             "episode_title": script.get("episode_title", ""),
 936 |             "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
 937 |             "quality_score": manifest.get("quality_score", 0),
 938 |             "clips_count": len(manifest.get("clips_used", [])),
 939 |             "duration_seconds": round(timing.get("video_duration", 0), 1),
 940 |             "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
 941 |             "av_sync_offset": round(final_offset, 3),
 942 |             "music_mood": episode_mood,
 943 |             "test_mode": test_mode,
 944 |         }
 945 |         save_episode_performance(date_str, perf_data)
 946 |     except Exception as e:
 947 |         logger.warning(f"Performance data save failed: {e}")
 948 | 
 949 |     # Telegram success alert
 950 |     if is_enabled("telegram_alerts") and passed:
 951 |         alert_pipeline_success(date_str, quality_score,
 952 |                                timing.get("video_duration", 0), final_video)
 953 | 
 954 |     # ── Step 14: FORMAT MULTIPLIER (V22) ───────────────────────────────────
 955 |     # LAW 1: Only runs AFTER episode is fully rendered and QC-passed.
 956 |     # LAW 2: Runs as a detached subprocess — never blocks or delays the main render.
 957 |     if is_enabled("multi_format_output") and passed:
 958 |         print("\n[STEP 14] FORMAT MULTIPLIER — launching secondary formats...")
 959 |         try:
 960 |             fmt_script = os.path.join(BASE, "format_multiplier.py")
 961 |             fmt_args = [
 962 |                 sys.executable, fmt_script,
 963 |                 "--manifest", manifest_path,
 964 |                 "--video", final_video,
 965 |             ]
 966 |             if test_mode:
 967 |                 fmt_args.append("--test")
 968 |             # Detached subprocess: does not block main pipeline return
 969 |             fmt_proc = subprocess.Popen(
 970 |                 fmt_args,
 971 |                 stdout=open(os.path.join(run_dir, "format_multiplier.log"), "w"),
 972 |                 stderr=subprocess.STDOUT,
 973 |                 start_new_session=True,  # detach from parent process group
 974 |             )
 975 |             print(f"  Format multiplier launched (PID {fmt_proc.pid}) — 5 formats running in background")
 976 |             print(f"  Log: {run_dir}/format_multiplier.log")
 977 |             manifest["format_multiplier_pid"] = fmt_proc.pid
 978 |         except Exception as e:
 979 |             logger.warning(f"Format multiplier launch failed (non-blocking): {e}")
 980 |     elif not is_enabled("multi_format_output"):
 981 |         logger.info("multi_format_output feature flag is disabled — skipping format multiplier")
 982 | 
 983 |     # ── Post-render health check + Resend notification ─────────────────────
 984 |     hc_passed = True  # default for test mode; overridden below for production
 985 |     if not test_mode:
 986 |         hc_passed, hc_errors = _post_render_health_check(final_video)
 987 |         dur_s = timing.get("video_duration", 0)
 988 |         size_mb = timing.get("video_size_mb", 0)
 989 |         dur_min = int(dur_s // 60)
 990 |         dur_sec = int(dur_s % 60)
 991 |         if passed and hc_passed:
 992 |             _send_resend_alert(
 993 |                 f"Pulse Check rendered: {dur_min}m {dur_sec}s, {size_mb:.0f}MB",
 994 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
 995 |                 f"Duration: {dur_min}m {dur_sec}s\n"
 996 |                 f"Size: {size_mb:.1f}MB\n"
 997 |                 f"Quality: {quality_score}/100\n"
 998 |                 f"Video: {final_video}",
 999 |             )
1000 |         else:
1001 |             _send_resend_alert(
1002 |                 "ALERT: Pulse Check render issues detected",
1003 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1004 |                 f"Pipeline passed: {passed}\n"
1005 |                 f"Health check passed: {hc_passed}\n"
1006 |                 f"Errors: {hc_errors}\n"
1007 |                 f"Video: {final_video}",
1008 |             )
1009 | 
1010 |     return passed and hc_passed
1011 | 
1012 | 
1013 | def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
1014 |     report_path = os.path.join(run_dir, "timing_report.txt")
1015 |     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
1016 |     lines = [
1017 |         "PULSE CHECK V5 — Timing Report",
1018 |         f"Generated: {ts}",
1019 |         f"Status: {'SUCCESS' if success else 'FAILED'}",
1020 |         "",
1021 |         "STEP TIMINGS:",
1022 |     ]
1023 |     for step, val in timing.items():
1024 |         if step in ("video_duration", "video_size_mb"):
1025 |             continue
1026 |         lines.append(f"  {step:<25}: {val:.1f}s")
1027 |     lines += [
1028 |         "",
1029 |         "OUTPUT STATS:",
1030 |         f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
1031 |         f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
1032 |         f"  total_wall_time_s    : {time.time() - t_start:.1f}",
1033 |     ]
1034 |     with open(report_path, "w") as f:
1035 |         f.write("\n".join(lines) + "\n")
1036 | 
1037 | 
1038 | def main():
1039 |     parser = argparse.ArgumentParser(
1040 |         description="Pulse Check V5 — Clip-First Video Producer")
1041 |     parser.add_argument("--test", action="store_true",
1042 |                         help="Test mode: fewer clips, truncated, test output dir")
1043 |     parser.add_argument("--skip-scan", action="store_true",
1044 |                         help="Skip channel scanning, use cached transcripts")
1045 |     parser.add_argument("--fast-test", action="store_true",
1046 |                         help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
1047 |     args = parser.parse_args()
1048 |     success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
1049 |                            fast_test=args.fast_test)
1050 |     # ── Post-render: fire tweet machine from morning brief ──────────────
1051 |     try:
1052 |         import subprocess as _sp
1053 |         _sp.Popen(["python3", "/home/ultron/protocol_pulse/services/tweet_machine.py"],
1054 |                   stdout=open("/home/ultron/protocol_pulse/logs/tweet_machine.log", "a"),
1055 |                   stderr=subprocess.STDOUT)
1056 |         print("  Tweet machine: fired (async)")
1057 |     except Exception as _te:
1058 |         print(f"  Tweet machine: skipped ({_te})")
1059 |     sys.exit(0 if success else 1)
1060 | 
1061 | 
1062 | if __name__ == "__main__":
1063 |     main()
1064 | 
```

### File: video_pipeline_v3/script_writer.py (815 lines)
```
   1 | import sys; sys.dont_write_bytecode = True
   2 | #!/usr/bin/env python3
   3 | """Script Writer V5 — generates host dialogue AROUND real YouTube clips.
   4 | 
   5 | Takes the 5 clips selected by clip_selector and generates:
   6 | - Cold open teasing clip #1
   7 | - Setup → Clip → React dialogue for each clip
   8 | - Wrap-up and sign-off
   9 | 
  10 | Host dialogue supports the clips, not the other way around.
  11 | """
  12 | import json
  13 | import logging
  14 | import os
  15 | import re
  16 | import sys
  17 | 
  18 | try:
  19 |     import anthropic
  20 |     HAS_ANTHROPIC = True
  21 | except ImportError:
  22 |     HAS_ANTHROPIC = False
  23 | 
  24 | from relay import get_key
  25 | 
  26 | logger = logging.getLogger("ScriptWriter")
  27 | if not logger.handlers:
  28 |     handler = logging.StreamHandler()
  29 |     handler.setFormatter(logging.Formatter("[script] %(message)s"))
  30 |     logger.addHandler(handler)
  31 |     logger.setLevel(logging.INFO)
  32 | 
  33 | SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
  34 | Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.
  35 | 
  36 | === SHOW BIBLE — IDENTITY ===
  37 | PBX is a Bitcoin operator and cypherpunk. He sees the world through an Austrian economics lens. He is NOT a financial analyst — he is a sovereign individual who runs nodes, understands mining, and lives on a Bitcoin standard.
  38 | EDITORIAL LAWS:
  39 | - Bitcoin ONLY. Never cover altcoins, crypto, DeFi, NFTs, or tokens.
  40 | - Never write "BTC" — always write "Bitcoin" in full.
  41 | - Never hedge. PBX states opinions directly. No "could", "might", "it remains to be seen."
  42 | - Respect the audience — they know what a UTXO is. Never explain basics.
  43 | - Every episode must contain ONE original PBX observation that nobody else said today.
  44 | - Cold open: single most important signal in ONE sentence. No warmup.
  45 | - PBX Close: an actual opinion, not a summary of what was covered.
  46 | NEVER COVER: mainstream media Bitcoin takes, institutional ETF obsession as the main story, fear-mongering narratives.
  47 | TIER 1 SOURCES (highest editorial weight): Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, Stephan Livera.
  48 | TIER 2 SOURCES: Simply Bitcoin, Bitcoin Magazine, Natalie Brunell, Swan Bitcoin.
  49 | NORTH STAR: This is a sovereign Bitcoin holders' morning show. Under 12 minutes. All signal, no noise.
  50 | === END SHOW BIBLE ===
  51 | 
  52 | HOST (PBX) — Hot takes, contrarian, dry wit. Warm strong male voice. PBX is the SOLE host. There is NO second host. PBX handles ALL segments: setup, react, data, social, wrap.
  53 | 
  54 | PBX is ALWAYS the FIRST voice. PBX opens every episode with the cold open and handles ALL narration segments. PBX closes with the final sign-off. The first dialogue entry MUST be host: 2 (PBX). ALL dialogue entries MUST be host: 2.
  55 | 
  56 | CRITICAL JSON RULE: NEVER output "host": 1 anywhere in your response. The ONLY valid host values are 2 (PBX) and "CLIP". Any entry with host:1 will cause a catastrophic render failure. Use ONLY host:2.
  57 | 
  58 | TONE RULES (NON-NEGOTIABLE):
  59 | - NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
  60 | - SETUP lines = 2-4 sentences, MAX 60 WORDS. A sharp framing angle + one specific data point. Leave them wanting the clip.
  61 | - REACT lines = 2-4 sentences. A hot take with substance — specific implication, not a vague platitude.
  62 | - Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
  63 | - Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
  64 | - Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
  65 | - Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
  66 | - After clips 2 and 4, add a BRIDGE line (type: "bridge") connecting that clip's theme to the next. 1-2 sentences. PBX only. Elevate the stakes or pivot the angle.
  67 | - REACT lines: when a clip lands something genuinely significant, give it 2-3 sharp sentences. Brief is not always best. Incisive > terse.
  68 | - NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
  69 | - CRITICAL: NEVER write "BTC" in any narration line. Always write "Bitcoin" in full. The ticker abbreviation sounds robotic when read aloud.
  70 | - When referencing a social media handle, write it in natural spoken form. NEVER write "@MaxKeiser". Write "Max Kaiser on X" or "Preston Pysh posted". Do not read handles aloud — reference the person by name.
  71 | - End with "Stay sovereign."
  72 | 
  73 | CRITICAL EPISODE ARC RULES (NON-NEGOTIABLE):
  74 | - Start with the most shocking/interesting fact. NO intro. NO "welcome to Protocol Pulse."
  75 | - At minute 3 (after Clip 2 setup), include a re-engagement hook: "But here's where it gets interesting..."
  76 | - At the halfway point, pivot to something unexpected or contrarian.
  77 | - End ABRUPTLY after the call to action. NEVER say "thanks for watching" or "see you next time."
  78 |   These phrases signal the video is ending and cause immediate viewer drop-off.
  79 | - Each narrator line should be 1-3 sentences. Never more than 4 sentences per turn.
  80 | - Include at least one specific number/metric in every other segment.
  81 | 
  82 | DELIVERY RULES:
  83 | - ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
  84 | - The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
  85 | - REACT lines = PBX's direct hot take on what was just shown. He speaks to the AUDIENCE, not to a co-host.
  86 | - NO conversational openers that imply a partner: NEVER use "Exactly.", "100%.", "I mean—", "Right, and—", "Yeah."
  87 | - React lines start with the IMPLICATION: "What this means is—", "The signal here is—", "Nobody's talking about—", "That's the tell.", "Here's what this means."
  88 | - Each new segment opens with a LIFT — a single high-energy sentence that raises the stakes. Think: news anchor tossing to the next story.
  89 | - Tone = investigative gossip journalist who happens to understand Austrian economics.
  90 | - Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
  91 | - Min 3, max 4 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.
  92 | 
  93 | EPISODE STRUCTURE (follow this order):
  94 | 1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
  95 | 2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
  96 | 3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
  97 | 4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
  98 | 5. [NARRATION] — Analysis after Clip 2.
  99 | 6. [DATA] — Hard metrics segment. MINIMUM 3 exchanges (all PBX). Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. Target: 45-60 seconds of spoken content.
 100 | 7. [SOCIAL] — "WHAT BITCOIN IS SAYING" — PBX reporting back from Bitcoin Twitter as live intelligence. Maximum 3 tweets, 20-25 seconds narration each (~75 seconds total). PBX treats each tweet as a signal:
 101 |   - PBX: 'Saylor just posted this to 65,000 likes — [quote]. Here's what that signals — conviction accumulation during extreme fear. That's the Saylor playbook and it's never been wrong.'
 102 |   - PBX: 'Lyn Alden weighed in on the macro picture — [paraphrase]. This aligns with what we're seeing in the bond market data. When she flips bullish on a timeline, institutions listen.'
 103 |   - PBX: 'This one caught my eye — [Name] is saying [quote]. The reason this matters is [2-3 sentences of sharp context].'
 104 |   PBX decodes the signal, he doesn't repeat the text. The tweet card is on screen — viewers read it themselves.
 105 |   CRITICAL: First tweet card shown = first referenced in narration. Maintain strict order.
 106 | 8. [SPACE_TAP] — "SPACE TAP: SIGNAL INTERCEPT" (only if space_tap_clips provided below)
 107 |    PBX opens: "Right now in the Bitcoin ecosphere..." or similar intelligence briefing opener.
 108 |    For each clip (3-4 clips provided):
 109 |    - One sentence intro: who is speaking, what space, why it matters NOW. 10-15 words.
 110 |    - The clip plays (assembler handles this — do NOT write clip text).
 111 |    - One sentence reaction: PBX adds value, contrarian take, or context. 10-15 words.
 112 |    Target: 10-15 seconds of narration per clip (intro + reaction combined).
 113 |    Segment tone: intelligence briefing. You are intercepting a live signal.
 114 |    Never say "I found" or "we discovered" — say "we're intercepting" or "signal captured from".
 115 |    Format each entry as:
 116 |    {{"host": 2, "text": "[SPACE_TAP] Right now in the ecosphere...", "type": "space_tap_intro"}},
 117 |    {{"host": "SPACE_CLIP", "clip_index": 0}},
 118 |    {{"host": 2, "text": "[SPACE_TAP] ...", "type": "space_tap_react"}},
 119 |    {{"host": "SPACE_CLIP", "clip_index": 1}},
 120 |    ... and so on for all clips.
 121 | 9. [WARM] — 2-3 sentences synthesizing the day's theme, then abrupt CTA. Target: 20-30 seconds. End ABRUPTLY. No "thanks for watching."
 122 | 
 123 | NARRATION PHILOSOPHY — Simon Dixon / Preston Pysh standard:
 124 | - Every line must contain ONE specific insight, data point, or evaluated observation
 125 | - Never state what already happened — analyze WHY it matters and WHAT COMES NEXT
 126 | - PBX sets up the angle with a sharp framing line + 1 specific number or fact
 127 | - PBX delivers the contrarian take, macro context, or on-chain implication
 128 | - Forbidden phrases: "Bitcoin continues to", "the market is watching", "this is significant",
 129 |   "interesting to note", "worth keeping an eye on", any pure restatement of price
 130 | - Required: each exchange references at least one of: hashrate, difficulty adjustment,
 131 |   miner profitability, HODLer behavior, lightning adoption, ETF flows, or macro correlation
 132 | - Minimum 3 sentences per speaker turn. Never 1-2 sentence fluff turns.
 133 | - Bridges between clips must connect thematic dots — not just "next up"
 134 | - DATA segment minimum: 4 lines from PBX, each with a specific metric, each with an implication
 135 | 
 136 | EPISODE LENGTH LAW: Target 550-680 narration words total. Never truncate a sentence. Every segment must be complete. Sharp means efficient — every sentence must earn its place. NO padding. NO repetition.
 137 | 
 138 | SEGMENT TAGGING (MANDATORY — controls PBX's voice dynamics):
 139 | Every dialogue text line MUST start with a segment type tag in brackets. The TTS engine reads this tag to adjust vocal delivery. If missing, the voice defaults to CLEAR which is safe but loses dramatic range.
 140 |   [COLD_OPEN] — opening hook only (first 1-2 sentences). Dramatic whisper. MAX 2 per episode.
 141 |   [NARRATION] — standard narration, setup, and analysis. Clear and confident. This is 70-80% of lines.
 142 |   [DATA] — specific metrics, prices, hashrates, on-chain numbers. Authoritative.
 143 |   [SOCIAL] — social segment commentary. Slightly warmer tone.
 144 |   [WARM] — outros, calls to action, sign-offs. Inviting.
 145 | Example: {{"host": 2, "text": "[NARRATION] Bitcoin miners are facing a squeeze as difficulty adjusts upward.", "type": "setup"}}
 146 | The tag is INSIDE the text string, not the type field. Both must be present.
 147 | 
 148 | SOCIAL SEGMENT — "WHAT BITCOIN IS SAYING":
 149 | If social posts data is provided below, add a "WHAT BITCOIN IS SAYING" segment after the last clip.
 150 | PBX has been on Bitcoin Twitter all morning and is REPORTING BACK as live intelligence.
 151 | This is NOT passive card display — PBX explicitly REACTS to each post as a signal analyst:
 152 | 
 153 | STYLE — PBX treats each tweet as intelligence, not content:
 154 |   - "{{Name}} just posted this to {{likes}} likes — [direct quote or tight paraphrase]. Here's what that signals..."
 155 |   - "{{Name}} weighed in on {{topic}} — [paraphrase]. This aligns with what we're seeing in the data..."
 156 |   - "This one caught my eye — {{Name}} is saying [quote]. The reason this matters is..."
 157 | PBX adds 2-3 sentences of sharp CONTEXT per tweet: why it matters NOW, what it signals about market positioning, how it connects to today's data. Maximum 3 posts, 20-25 seconds narration each, ~75 seconds total.
 158 | The tweet card is on screen — viewers can read the text. PBX's job is to DECODE the signal, not repeat the words.
 159 | Each entry uses type: "social_segment".
 160 | 
 161 | CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.
 162 | TWEET LAW — IRON LAW: Before writing ANY tweet narration, read the actual social_posts list in order. Tweet segment narration MUST reference social_posts[0]['handle'] for the first tweet, social_posts[1]['handle'] for the second, etc. NEVER reference a name not in the list. NEVER assume who tweeted. Read the handle from the data and use it verbatim.
 163 | 
 164 | {clips_info}
 165 | 
 166 | BTC Price Today: {btc_price}
 167 | Top Tweets/Nostr Posts Today: {social_posts}
 168 | {live_context}
 169 | Return ONLY valid JSON (no markdown, no code fences):
 170 | {{
 171 |   "cold_open": "explosive 1-sentence cold open",
 172 |   "dialogue": [
 173 |     {{"host": 2, "text": "...", "type": "cold_open"}},
 174 |     {{"host": 2, "text": "...", "type": "setup", "clip_rank": 1}},
 175 |     {{"host": "CLIP", "rank": 1}},
 176 |     {{"host": 2, "text": "...", "type": "react", "clip_rank": 1}},
 177 |     {{"host": 2, "text": "...", "type": "setup", "clip_rank": 2}},
 178 |     {{"host": "CLIP", "rank": 2}},
 179 |     {{"host": 2, "text": "...", "type": "react", "clip_rank": 2}},
 180 |     ...and so on for all clips...
 181 |     {{"host": 2, "text": "...", "type": "social_segment"}},
 182 |     {{"host": 2, "text": "...", "type": "social_segment"}},
 183 |     {{"host": 2, "text": "Final wrap. Stay sovereign.", "type": "wrap"}}
 184 |   ],
 185 |   "episode_title": "Short punchy title (5-8 words)",
 186 |   "thumbnail": {{
 187 |     "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
 188 |     "subtext": "secondary line"
 189 |   }},
 190 |   "segments_summary": ["4-8 WORD ALL CAPS EDITORIAL HEADLINE FOR EACH CLIP — like 'SAYLOR BETS BIG ON BITCOIN DIP' not a quote from the segment"],
 191 |   "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
 192 | }}
 193 | 
 194 | IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5)."""
 195 | 
 196 | 
 197 | # Maps bracket tags in text to segment types for TTS voice modes
 198 | _TAG_TO_TYPE = {
 199 |     "COLD_OPEN": "cold_open",
 200 |     "NARRATION": "setup",
 201 |     "DATA": "data",
 202 |     "SOCIAL": "social_segment",
 203 |     "WARM": "wrap",
 204 |     "BRIDGE": "setup",  # inter-clip context bridges treated as narration
 205 |     "SPACE_TAP": "space_tap_intro",
 206 |     "SETUP": "setup",
 207 |     "REACT": "react",
 208 |     "CTA": "wrap",
 209 |     "COLD": "cold_open",
 210 | }
 211 | 
 212 | _TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")
 213 | 
 214 | 
 215 | def _extract_segment_tags(result: dict) -> dict:
 216 |     """Extract [TAG] prefixes from dialogue text and set entry type accordingly.
 217 | 
 218 |     If a dialogue line starts with [NARRATION], [DATA], etc., strip the tag
 219 |     from the text and set/override the type field for TTS voice mode selection.
 220 |     """
 221 |     dialogue = result.get("dialogue", [])
 222 |     # Force PBX-only: normalize any host:1 → host:2
 223 |     for _e in dialogue:
 224 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 225 |     for entry in dialogue:
 226 |         text = entry.get("text", "")
 227 |         if not text:
 228 |             continue
 229 |         m = _TAG_PATTERN.match(text)
 230 |         if m:
 231 |             tag = m.group(1)
 232 |             entry["text"] = text[m.end():]
 233 |             entry["type"] = _TAG_TO_TYPE[tag]
 234 |     return result
 235 | 
 236 | 
 237 | def _format_clips_info(selections: dict) -> str:
 238 |     """Format clip selections for the script prompt."""
 239 |     clips = selections.get("clips", [])
 240 |     parts = []
 241 |     for c in clips:
 242 |         parts.append(
 243 |             f"CLIP #{c['rank']}:\n"
 244 |             f"  Channel: {c.get('channel', 'Unknown')}\n"
 245 |             f"  Video: {c.get('video_title', 'Untitled')}\n"
 246 |             f"  Quote: \"{c.get('quote', '')}\"\n"
 247 |             f"  Why selected: {c.get('why', '')}\n"
 248 |             f"  Suggested setup: {c.get('host_setup', '')}\n"
 249 |             f"  Suggested reaction: {c.get('host_react', '')}\n"
 250 |         )
 251 |     return "\n".join(parts)
 252 | 
 253 | 
 254 | def _load_narrative_context() -> dict:
 255 |     """Load narrative_context.json for narrative-aware script generation.
 256 |     Returns empty dict if missing or stale (>6hr old)."""
 257 |     import os
 258 |     from datetime import datetime, timezone
 259 |     ctx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
 260 |                             "data", "intelligence", "narrative_context.json")
 261 |     try:
 262 |         with open(ctx_path) as f:
 263 |             ctx = json.load(f)
 264 |         # Check staleness
 265 |         computed = ctx.get("computed_at", "")
 266 |         if computed:
 267 |             computed_dt = datetime.fromisoformat(computed.replace("Z", "+00:00"))
 268 |             age_hours = (datetime.now(timezone.utc) - computed_dt).total_seconds() / 3600
 269 |             if age_hours > 6:
 270 |                 logger.warning(f"Narrative context is {age_hours:.1f}h old (>6h) — using generic prompt")
 271 |                 return {}
 272 |         return ctx
 273 |     except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
 274 |         logger.warning(f"Narrative context unavailable: {e}")
 275 |         return {}
 276 | 
 277 | 
 278 | NARRATIVE_INJECTION = """
 279 | TODAY'S LIVE NARRATIVE CONTEXT (from real-time thought leader monitoring):
 280 | Dominant narrative: {dominant_narrative}
 281 | Market mood: {market_mood}
 282 | What thought leaders are saying: {episode_narrative}
 283 | PBX cold open hook: {pbx_intro_hook}
 284 | PBX analysis angle: {pbx_context}
 285 | Suggested bridge lines: {narrative_bridge_lines}
 286 | 
 287 | MANDATORY SCRIPT RULES (from narrative context):
 288 | - PBX's cold open MUST reference the dominant narrative in his first sentence
 289 | - At least ONE of the clips must be explicitly connected to the X discourse
 290 |   (e.g., "This is what everyone on Crypto Twitter has been discussing all morning...")
 291 | - PBX must cite at least one specific data point from the narrative context (not generic)
 292 | - Avoid topics flagged in: {avoid_topics}
 293 | - The show must feel LIVE — like PBX has been tracking this story all morning
 294 | 
 295 | DATA SEGMENT REQUIREMENT: The data/metrics discussed must relate to today's
 296 | dominant narrative ({dominant_narrative}). If narrative is "ETF inflows",
 297 | cite actual ETF flow numbers. If "mining difficulty", cite actual hashrate/difficulty data.
 298 | PBX must sound like an analyst who read the numbers this morning, not a generalist.
 299 | """
 300 | 
 301 | 
 302 | def _validate_social_tweet_order(result: dict, social_posts_raw: str) -> dict:
 303 |     """Render11 FIX 5: Ensure narrator tweet references match tweet display order.
 304 | 
 305 |     If narrator mentions @handle that doesn't match the expected tweet position,
 306 |     reorder social_segment entries so card display matches narration order.
 307 |     Tags each social entry with _social_handle_ref for assembler card matching.
 308 |     """
 309 |     if not social_posts_raw or social_posts_raw.startswith("NONE"):
 310 |         return result
 311 | 
 312 |     dialogue = result.get("dialogue", [])
 313 |     # Force PBX-only: normalize any host:1 → host:2
 314 |     for _e in dialogue:
 315 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 316 |     if not dialogue:
 317 |         return result
 318 | 
 319 |     # Extract ordered handles from social_posts_raw (sorted by likes in generate_from_clips)
 320 |     social_handles = []
 321 |     for line in social_posts_raw.split("\n"):
 322 |         m = re.match(r'(?:Tweet \d+: )?@(\w+)\s+tweeted:', line)
 323 |         if m:
 324 |             social_handles.append(m.group(1).lower())
 325 | 
 326 |     # Extract @handle references from social_segment narration lines
 327 |     social_entries = [(i, e) for i, e in enumerate(dialogue)
 328 |                       if e.get("type") == "social_segment" and e.get("host") in (1, 2, "1", "2")]
 329 | 
 330 |     narrator_handles = []
 331 |     for _, entry in social_entries:
 332 |         text = entry.get("text", "")
 333 |         handles_in_text = re.findall(r'@(\w+)', text)
 334 |         for h in handles_in_text:
 335 |             h_lower = h.lower()
 336 |             if h_lower in social_handles and h_lower not in narrator_handles:
 337 |                 narrator_handles.append(h_lower)
 338 | 
 339 |     # Tag each social entry with its referenced handle
 340 |     for idx, entry in social_entries:
 341 |         text = entry.get("text", "")
 342 |         handles_in_text = [h.lower() for h in re.findall(r'@(\w+)', text)]
 343 |         matched = [h for h in handles_in_text if h in social_handles]
 344 |         if matched:
 345 |             entry["_social_handle_ref"] = matched[0]
 346 |             logger.info(f"[script] Social segment line {idx} references @{matched[0]}")
 347 | 
 348 |     # Render12 FIX 2: Assert strict tweet order — first card shown = first referenced
 349 |     if narrator_handles and social_handles:
 350 |         expected = social_handles[:len(narrator_handles)]
 351 |         if narrator_handles != expected:
 352 |             logger.warning(f"[script] TWEET ORDER VIOLATION: narrator={narrator_handles}, expected={expected} — reordering")
 353 |         else:
 354 |             logger.info(f"[script] TWEET ORDER OK: {narrator_handles}")
 355 | 
 356 |     # FIX 5: Reorder social_segment entries so narration order matches display order
 357 |     # The social_posts were sorted by likes desc — narrator should mention them in that order
 358 |     if narrator_handles and social_handles and narrator_handles != social_handles[:len(narrator_handles)]:
 359 |         logger.warning(f"[script] TWEET MISMATCH: narrator={narrator_handles}, data={social_handles[:len(narrator_handles)]}")
 360 |         # Reorder social_segment dialogue entries to match data order
 361 |         social_with_handle = [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]
 362 |         if social_with_handle:
 363 |             # Sort by position in social_handles (data order = likes desc)
 364 |             social_with_handle.sort(
 365 |                 key=lambda x: social_handles.index(x[1]["_social_handle_ref"])
 366 |                 if x[1]["_social_handle_ref"] in social_handles else 999
 367 |             )
 368 |             # Swap entries in-place in dialogue
 369 |             original_indices = [i for i, _ in [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]]
 370 |             for new_pos, (_, entry) in enumerate(social_with_handle):
 371 |                 if new_pos < len(original_indices):
 372 |                     dialogue[original_indices[new_pos]] = entry
 373 |             logger.info(f"[script] Reordered social entries to match data order")
 374 | 
 375 |     return result
 376 | 
 377 | 
 378 | def _make_editorial_headline(raw: str) -> str:
 379 |     """Convert a raw summary/title into a 3-7 word ALL CAPS editorial headline.
 380 | 
 381 |     Render11 FIX 8: Strict Bloomberg/newspaper front page format.
 382 |     No punctuation except dash. 3-7 words. Always ALL CAPS.
 383 |     BAD: 'Saylor talks about sonic boom theory'
 384 |     GOOD: 'SAYLOR SONIC BOOM BITCOIN THESIS'
 385 |     """
 386 |     import re
 387 |     # Strip quotes, URLs, timestamps, punctuation (except dash)
 388 |     clean = re.sub(r'https?://\S+', '', raw)
 389 |     clean = re.sub(r'["\'\[\]().,;:!?]', '', clean)
 390 |     clean = re.sub(r'\s+', ' ', clean).strip()
 391 |     # Take first 7 words, uppercase
 392 |     words = clean.split()[:7]
 393 |     headline = " ".join(words).upper()
 394 |     # Ensure minimum 3 words
 395 |     if len(words) < 3:
 396 |         headline = headline + " - BREAKING"
 397 |     # FIX 8: Post-generation validation — force ALL CAPS, strip non-conforming chars
 398 |     headline = re.sub(r'[^A-Z0-9 \-/]', '', headline).strip()
 399 |     if not headline or len(headline) < 5:
 400 |         headline = "BREAKING SIGNAL DETECTED"
 401 |     return headline[:55]
 402 | 
 403 | 
 404 | def _populate_segment_headlines(result: dict) -> dict:
 405 |     """Session 4 Fix 2: Add 'headline' key to each dialogue entry.
 406 | 
 407 |     Maps segment type + clip rank to a meaningful headline so _smart_headline()
 408 |     in assembler.py gets a real headline instead of truncated spoken text.
 409 |     Render11 FIX 8: Headlines are 3-7 word ALL CAPS editorial style with regex validation.
 410 |     """
 411 |     dialogue = result.get("dialogue", [])
 412 |     # Force PBX-only: normalize any host:1 → host:2
 413 |     for _e in dialogue:
 414 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 415 |     summaries = result.get("segments_summary", [])
 416 |     episode_title = result.get("episode_title", "Pulse Check Daily")
 417 | 
 418 |     for entry in dialogue:
 419 |         if entry.get("headline"):
 420 |             continue  # already has one
 421 |         host = entry.get("host")
 422 |         if host == "CLIP":
 423 |             continue  # clip markers don't need headlines
 424 | 
 425 |         seg_type = entry.get("type", "")
 426 |         clip_rank = entry.get("clip_rank", 0)
 427 | 
 428 |         if seg_type == "cold_open":
 429 |             entry["headline"] = _make_editorial_headline(episode_title)
 430 |         elif seg_type in ("setup", "react") and clip_rank:
 431 |             # Use segments_summary keyed by rank — force editorial style
 432 |             idx = clip_rank - 1
 433 |             if 0 <= idx < len(summaries) and summaries[idx]:
 434 |                 entry["headline"] = _make_editorial_headline(summaries[idx])
 435 |             else:
 436 |                 entry["headline"] = _make_editorial_headline(episode_title)
 437 |         elif seg_type == "data":
 438 |             entry["headline"] = "TODAY'S INTELLIGENCE"
 439 |         elif seg_type == "social_segment":
 440 |             entry["headline"] = "SIGNAL FROM THE FIELD"
 441 |         elif seg_type in ("wrap", "outro"):
 442 |             entry["headline"] = "STAY SOVEREIGN"
 443 |         elif seg_type == "bridge":
 444 |             entry["headline"] = _make_editorial_headline(episode_title)
 445 |         else:
 446 |             # Generic narrator — use episode title
 447 |             entry["headline"] = _make_editorial_headline(episode_title)
 448 | 
 449 |     # Render11 FIX 8: Post-validation — force ALL CAPS, reject >8 words or lowercase
 450 |     for entry in dialogue:
 451 |         h = entry.get("headline", "")
 452 |         if not h or entry.get("host") == "CLIP":
 453 |             continue
 454 |         # Force uppercase and strip non-conforming chars
 455 |         h = re.sub(r'[^A-Z0-9 \-/]', '', h.upper()).strip()
 456 |         words = h.split()
 457 |         if len(words) > 8:
 458 |             h = " ".join(words[:7])
 459 |         if not h or len(h) < 5:
 460 |             h = "BREAKING SIGNAL DETECTED"
 461 |         entry["headline"] = h
 462 | 
 463 |     return result
 464 | 
 465 | 
 466 | def generate_from_clips(selections: dict, btc_price: str = "N/A",
 467 |                         live_context: str = "", morning_brief: dict = None,
 468 |                         social_posts_sorted: list = None) -> dict:
 469 |     """Generate host dialogue script around the selected clips.
 470 | 
 471 |     Args:
 472 |         selections: Output from clip_selector.select_clips()
 473 |         btc_price: Current BTC price string
 474 |         live_context: Real-time live stream/Spaces intelligence (optional)
 475 |         social_posts_sorted: Pre-fetched, sorted social posts (single source of truth from daily_producer)
 476 | 
 477 |     Returns:
 478 |         Script dict with dialogue array
 479 |     """
 480 |     clips = selections.get("clips", [])
 481 |     if not clips:
 482 |         logger.error("No clips provided for script generation")
 483 |         return _fallback_script(selections)
 484 | 
 485 |     from relay import call_llm
 486 | 
 487 |     clips_info = _format_clips_info(selections)
 488 | 
 489 |     # Social data — use pre-fetched sorted list from daily_producer (single source of truth)
 490 |     # Fallback: fetch here if caller didn't provide (backwards compat)
 491 |     social_data_sorted = social_posts_sorted or []
 492 |     if not social_data_sorted:
 493 |         try:
 494 |             from utils.social_fetcher import get_todays_social_posts
 495 |             social_data = get_todays_social_posts(max_posts=5)
 496 |             if social_data:
 497 |                 social_data_sorted = sorted(social_data, key=lambda x: x.get('likes', 0), reverse=True)
 498 |         except Exception as e:
 499 |             logger.warning(f"Social data fetch failed: {e}")
 500 | 
 501 |     if social_data_sorted:
 502 |         social_posts = "\n".join([
 503 |             f"Tweet {ti+1}: @{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
 504 |             for ti, p in enumerate(social_data_sorted)
 505 |         ])
 506 |         social_posts += (
 507 |             "\n\nCRITICAL SOCIAL RULES:"
 508 |             "\n- Read ONLY what is written above. Do NOT paraphrase, add, or invent words."
 509 |             "\n- Quote tweet text DIRECTLY and verbatim."
 510 |             "\n- Reference tweets BY POSITION: 'Tweet 1 from @handle' matches the first tweet listed above."
 511 |             "\n- If you mention @handle, the DISPLAYED tweet card MUST match that handle."
 512 |             "\n- Never attribute words from one tweet to a different person."
 513 |         )
 514 |     else:
 515 |         social_posts = "NONE — skip social segment entirely"
 516 | 
 517 |     # Build live context block
 518 |     live_block = ""
 519 |     if live_context:
 520 |         live_block = (
 521 |             "\nLIVE INTELLIGENCE: The following events are happening RIGHT NOW or happened "
 522 |             "in the last few hours on Bitcoin YouTube/X Spaces. Reference these naturally "
 523 |             "in your narration to make the episode feel current and urgent:\n"
 524 |             f"{live_context}\n"
 525 |         )
 526 | 
 527 |     # Inject narrative context from thought leader monitoring
 528 |     narrative_ctx = _load_narrative_context()
 529 |     if narrative_ctx and narrative_ctx.get("dominant_narrative"):
 530 |         try:
 531 |             bridge_lines = narrative_ctx.get("narrative_bridge_lines", [])
 532 |             narrative_block = (NARRATIVE_INJECTION
 533 |                 .replace("{dominant_narrative}", narrative_ctx.get("dominant_narrative", ""))
 534 |                 .replace("{market_mood}", narrative_ctx.get("market_mood", ""))
 535 |                 .replace("{episode_narrative}", narrative_ctx.get("episode_narrative", ""))
 536 |                 .replace("{pbx_intro_hook}", narrative_ctx.get("eryn_intro_hook", narrative_ctx.get("pbx_intro_hook", "")))
 537 |                 .replace("{pbx_context}", narrative_ctx.get("mark_context", narrative_ctx.get("pbx_context", "")))
 538 |                 .replace("{narrative_bridge_lines}", "\n".join(bridge_lines) if bridge_lines else "none")
 539 |                 .replace("{avoid_topics}", ", ".join(narrative_ctx.get("avoid_topics", [])))
 540 |             )
 541 |             live_block = narrative_block + "\n" + live_block
 542 |             logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")
 543 |         except Exception as e:
 544 |             logger.warning(f"Failed to inject narrative context: {e}")
 545 | 
 546 |     # Inject morning intelligence brief (Nitter-sourced Twitter analysis)
 547 |     morning_block = ""
 548 |     if morning_brief and isinstance(morning_brief, dict):
 549 |         parts = ["\nMORNING INTELLIGENCE BRIEF (from today's Bitcoin Twitter analysis — use as context):"]
 550 |         dom_narr = morning_brief.get("dominant_narratives", [])
 551 |         if dom_narr:
 552 |             parts.append(f"- Dominant narratives today: {'; '.join(dom_narr[:3])}")
 553 |         trending_lang = morning_brief.get("trending_language", [])
 554 |         if trending_lang:
 555 |             parts.append(f"- Trending language on Bitcoin Twitter: {', '.join(trending_lang[:7])}")
 556 |             parts.append("  USE these phrases naturally in narration where they fit — they resonate with the audience today.")
 557 |         sentiment = morning_brief.get("sentiment", "")
 558 |         reasoning = morning_brief.get("sentiment_reasoning", "")
 559 |         if sentiment:
 560 |             parts.append(f"- Market sentiment: {sentiment}")
 561 |         if reasoning:
 562 |             parts.append(f"  Reasoning: {reasoning[:200]}")
 563 |         voice_guidance = morning_brief.get("protocol_pulse_voice_guidance", "")
 564 |         if voice_guidance:
 565 |             parts.append(f"- Voice guidance: {voice_guidance[:250]}")
 566 |         morning_block = "\n".join(parts) + "\n"
 567 |         logger.info(f"Morning brief injected: {len(dom_narr)} narratives, {len(trending_lang)} trending phrases")
 568 | 
 569 |     # Inject audience engagement intelligence
 570 |     engagement_block = ""
 571 |     try:
 572 |         import sys as _sys
 573 |         _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
 574 |         if _data_dir not in _sys.path:
 575 |             _sys.path.insert(0, _data_dir)
 576 |         from engagement_scorer import get_trending_topics, get_top_channels
 577 |         trending = get_trending_topics()[:3]
 578 |         top_chs = get_top_channels(5)
 579 |         if trending or top_chs:
 580 |             parts = ["\nAUDIENCE ENGAGEMENT INTELLIGENCE (from real audience data — use naturally):"]
 581 |             if trending:
 582 |                 topics_str = ", ".join(f"{t[0]} ({t[1]:.1f}/10)" for t in trending)
 583 |                 parts.append(f"- Currently trending in our audience: {topics_str} — weight these if relevant.")
 584 |             if top_chs:
 585 |                 chs_str = ", ".join(f"{c[0]} ({c[1]:.1f})" for c in top_chs)
 586 |                 parts.append(f"- Highest engagement channels this week: {chs_str} — prioritize their clips.")
 587 |             engagement_block = "\n".join(parts) + "\n"
 588 |             logger.info(f"Engagement intelligence injected: {len(trending)} topics, {len(top_chs)} channels")
 589 |     except Exception as e:
 590 |         logger.debug(f"Engagement scorer unavailable: {e}")
 591 | 
 592 |     # Inject episode memory feedback if enough history exists
 593 |     memory_block = ""
 594 |     try:
 595 |         from episode_memory import get_episode_count, get_weak_dimensions, get_strong_dimensions, get_best_channels
 596 |         if get_episode_count() >= 5:
 597 |             weak = get_weak_dimensions(threshold=6.0)
 598 |             strong = get_strong_dimensions(threshold=8.0)
 599 |             top_ch = get_best_channels(5)
 600 |             parts = ["\nEPISODE MEMORY FEEDBACK (from past renders — adapt accordingly):"]
 601 |             if weak:
 602 |                 dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in weak[:5])
 603 |                 parts.append(f"- WEAK AREAS (improve these): {dims}")
 604 |             if strong:
 605 |                 dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in strong[:5])
 606 |                 parts.append(f"- STRONG AREAS (maintain these): {dims}")
 607 |             if top_ch:
 608 |                 chs = ", ".join(f"{c['channel']} ({c['avg_score']})" for c in top_ch)
 609 |                 parts.append(f"- TOP CHANNELS by quality score: {chs}")
 610 |             memory_block = "\n".join(parts) + "\n"
 611 |             logger.info(f"Episode memory injected: {len(weak)} weak, {len(strong)} strong dimensions")
 612 |     except Exception as e:
 613 |         logger.warning(f"Episode memory unavailable: {e}")
 614 | 
 615 |     # Inject Space Tap clips context if available
 616 |     space_tap_block = ""
 617 |     space_tap_clips = selections.get("space_tap_clips", [])
 618 |     if space_tap_clips:
 619 |         parts = ["\nSPACE TAP CLIPS (X Spaces intercepts — generate [SPACE_TAP] segment):"]
 620 |         for i, sc in enumerate(space_tap_clips):
 621 |             handle = sc.get("host_handle", "unknown")
 622 |             text_preview = sc.get("text", "")[:150]
 623 |             parts.append(f"  Clip {i}: @{handle} — \"{text_preview}\"")
 624 |         parts.append(f"Generate intro + react for each of the {len(space_tap_clips)} clips above.")
 625 |         space_tap_block = "\n".join(parts) + "\n"
 626 | 
 627 |     prompt = (SCRIPT_PROMPT
 628 |         .replace("{clips_info}", str(clips_info))
 629 |         .replace("{btc_price}", str(btc_price))
 630 |         .replace("{social_posts}", str(social_posts))
 631 |         .replace("{live_context}", str(live_block+morning_block+engagement_block+memory_block+space_tap_block))
 632 |     )
 633 | 
 634 |     logger.info(f"Generating script for {len(clips)} clips...")
 635 |     text = call_llm(prompt, max_tokens=8000, model="claude-sonnet-4-6")
 636 |     if text is None:
 637 |         logger.warning("All LLM providers failed, using fallback script")
 638 |         return _fallback_script(selections)
 639 | 
 640 |     try:
 641 | 
 642 |         if "```json" in text:
 643 |             text = text.split("```json")[1].split("```")[0]
 644 |         elif "```" in text:
 645 |             text = text.split("```")[1].split("```")[0]
 646 | 
 647 |         # FIX 4: JSON retry loop — send malformed JSON back for repair, max 3 retries
 648 |         json_text = text
 649 |         result = None
 650 |         for _retry in range(4):  # attempt 0 = first try, 1-3 = retries
 651 |             try:
 652 |                 result = json.loads(json_text)
 653 |                 break
 654 |             except json.JSONDecodeError as je:
 655 |                 if _retry >= 3:
 656 |                     raise RuntimeError(f"JSON repair failed after 3 retries: {je}") from je
 657 |                 logger.warning(f"JSON parse error (retry {_retry+1}/3): {je}")
 658 |                 repair_prompt = (
 659 |                     f"The following JSON is malformed. Fix it and return ONLY valid JSON, "
 660 |                     f"no markdown, no explanation:\n\n{json_text}\n\n"
 661 |                     f"Error was: {je}"
 662 |                 )
 663 |                 json_text = call_llm(repair_prompt, max_tokens=8000, model="claude-sonnet-4-6")
 664 |                 if json_text is None:
 665 |                     raise RuntimeError("JSON repair LLM call returned None")
 666 |                 # Strip code fences from repair response
 667 |                 if "```json" in json_text:
 668 |                     json_text = json_text.split("```json")[1].split("```")[0]
 669 |                 elif "```" in json_text:
 670 |                     json_text = json_text.split("```")[1].split("```")[0]
 671 | 
 672 |         # Extract [TAG] prefixes from text and set type fields for TTS
 673 |         result = _extract_segment_tags(result)
 674 | 
 675 |         # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
 676 |         result = _populate_segment_headlines(result)
 677 | 
 678 |         # Round 2 Fix 5: Validate social segment tweet order matches narration references
 679 |         result = _validate_social_tweet_order(result, social_posts)
 680 |         result = _enforce_setup_per_clip(result, selections)
 681 | 
 682 |         # Validate structure
 683 |         dialogue = result.get("dialogue", [])
 684 |         # Force PBX-only: normalize any host:1 â host:2
 685 |         for _e in dialogue:
 686 |             if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 687 |         clip_entries = [d for d in dialogue if d.get("host") == "CLIP"]
 688 |         speech_entries = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
 689 | 
 690 |         logger.info(f"Script generated: {len(dialogue)} entries "
 691 |                     f"({len(speech_entries)} speech, {len(clip_entries)} clips)")
 692 |         logger.info(f"Title: {result.get('episode_title', 'Untitled')}")
 693 | 
 694 |         return result
 695 | 
 696 |     except json.JSONDecodeError as e:
 697 |         logger.error(f"JSON parse error: {e}")
 698 |         return _fallback_script(selections)
 699 |     except Exception as e:
 700 |         logger.error(f"Claude API error: {e}")
 701 |         return _fallback_script(selections)
 702 | 
 703 | 
 704 | 
 705 | def _enforce_setup_per_clip(result: dict, selections: dict) -> dict:
 706 |     """IRON LAW: Every clip rank must have exactly one SETUP segment before it.
 707 |     If the LLM collapses two setups onto clip_rank 1 and skips clip_rank 2,
 708 |     this function detects and repairs it by inserting a bridging setup."""
 709 |     import logging
 710 |     _log = logging.getLogger(__name__)
 711 |     dialogue = result.get("dialogue", [])
 712 |     clips = selections.get("clips", [])
 713 |     clip_ranks = [c.get("rank", 0) for c in clips if c.get("rank")]
 714 | 
 715 |     # Find which ranks have a setup
 716 |     setup_ranks = set()
 717 |     for entry in dialogue:
 718 |         if isinstance(entry, dict) and entry.get("type") == "setup":
 719 |             cr = entry.get("clip_rank")
 720 |             if cr:
 721 |                 setup_ranks.add(cr)
 722 | 
 723 |     missing = [r for r in clip_ranks if r not in setup_ranks]
 724 |     if not missing:
 725 |         return result
 726 | 
 727 |     _log.warning(f"[script] SETUP MISSING for clip ranks: {missing} — inserting bridge narration")
 728 |     clips_by_rank = {c.get("rank"): c for c in clips}
 729 |     new_dialogue = []
 730 |     for entry in dialogue:
 731 |         if isinstance(entry, dict) and entry.get("host") == "CLIP":
 732 |             rank = entry.get("rank", 0)
 733 |             if rank in missing:
 734 |                 ch = clips_by_rank.get(rank, {}).get("channel", "our next source")
 735 |                 bridge = {
 736 |                     "host": 2,
 737 |                     "text": f"[NARRATION] Now — {ch} brings a signal you need to hear.",
 738 |                     "type": "setup",
 739 |                     "clip_rank": rank,
 740 |                     "headline": f"{ch.upper()} SIGNAL"
 741 |                 }
 742 |                 new_dialogue.append(bridge)
 743 |                 missing.remove(rank)
 744 |         new_dialogue.append(entry)
 745 |     result["dialogue"] = new_dialogue
 746 |     return result
 747 | 
 748 | def _fallback_script(selections: dict) -> dict:
 749 |     """Generate a basic script from clip selections without Claude."""
 750 |     clips = selections.get("clips", [])
 751 |     cold_open = selections.get("cold_open", "Breaking developments in Bitcoin today.")
 752 | 
 753 |     dialogue = [
 754 |         {"host": 2, "text": cold_open, "type": "cold_open"},  # IRON LAW: PBX always opens
 755 |     ]
 756 | 
 757 |     for c in clips:
 758 |         rank = c.get("rank", 0)
 759 |         setup = c.get("host_setup", f"Check out what {c.get('channel', 'this channel')} just dropped.")
 760 |         react = c.get("host_react", "That's a big deal. The market hasn't priced this in yet.")
 761 | 
 762 |         dialogue.append({"host": 2, "text": setup, "type": "setup", "clip_rank": rank})
 763 |         dialogue.append({"host": "CLIP", "rank": rank})
 764 |         dialogue.append({"host": 2, "text": react, "type": "react", "clip_rank": rank})
 765 | 
 766 |     dialogue.append({
 767 |         "host": 2,
 768 |         "text": "That's your Pulse Check for today. Stay sovereign.",
 769 |         "type": "wrap",
 770 |     })
 771 | 
 772 |     title = selections.get("episode_title", "Pulse Check Daily")
 773 | 
 774 |     return {
 775 |         "cold_open": cold_open,
 776 |         "dialogue": dialogue,
 777 |         "episode_title": title,
 778 |         "thumbnail": {"headline": title.upper(), "subtext": "Daily Bitcoin Intelligence"},
 779 |         "segments_summary": [c.get("why", "") for c in clips],
 780 |         "shorts_quotes": [c.get("quote", "")[:80] for c in clips[:3]],
 781 |     }
 782 | 
 783 | 
 784 | # Legacy compatibility
 785 | def generate_script(stories=None, style="default", btc_price="N/A"):
 786 |     """Legacy wrapper — generate a sample script for testing."""
 787 |     logger.info("Legacy generate_script called — use generate_from_clips for V5 pipeline")
 788 |     return generate_sample_script(style)
 789 | 
 790 | 
 791 | def generate_sample_script(style="default"):
 792 |     """Sample script for testing without live data."""
 793 |     return {
 794 |         "episode_title": "The Quiet Accumulation",
 795 |         "cold_open": "Three sovereign wealth funds just disclosed Bitcoin positions worth twelve billion dollars.",
 796 |         "dialogue": [
 797 |             {"host": 2, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},  # IRON LAW: PBX always opens
 798 |             {"host": 2, "text": "Bitcoin Magazine just dropped this bombshell.", "type": "setup", "clip_rank": 1},
 799 |             {"host": "CLIP", "rank": 1},
 800 |             {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything.", "type": "react", "clip_rank": 1},
 801 |             {"host": 2, "text": "And look at what Simply Bitcoin is reporting on hash rate.", "type": "setup", "clip_rank": 2},
 802 |             {"host": "CLIP", "rank": 2},
 803 |             {"host": 2, "text": "Record high hash rate. Miners aren't leaving. They're doubling down.", "type": "react", "clip_rank": 2},
 804 |             {"host": 2, "text": "That's your Pulse Check. Stay sovereign.", "type": "wrap"},
 805 |         ],
 806 |         "thumbnail": {"headline": "SMART MONEY IS MOVING", "subtext": "Nations are stacking"},
 807 |         "segments_summary": ["Sovereign wealth funds buying BTC", "Hash rate hits record"],
 808 |         "shorts_quotes": ["When the entities that print fiat start hoarding the exit asset", "Miners aren't leaving"],
 809 |     }
 810 | 
 811 | 
 812 | if __name__ == "__main__":
 813 |     script = generate_sample_script()
 814 |     print(json.dumps(script, indent=2))
 815 | 
```

### File: video_pipeline_v3/utils/social_fetcher.py (112 lines)
```
   1 | """Social Data Fetcher — real tweet/Nostr data for the social segment.
   2 | 
   3 | Per Law A1: if no real data exists, return empty list. Never fabricate.
   4 | 
   5 | Priority:
   6 |   1. data/daily_tweets.json (manually curated by operator)
   7 |   2. High-engagement tweets from data/tweet_study/raw_tweets.json
   8 |   3. Empty list (social segment skipped)
   9 | """
  10 | import json
  11 | import logging
  12 | import os
  13 | from datetime import datetime, timedelta
  14 | 
  15 | logger = logging.getLogger(__name__)
  16 | 
  17 | BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  18 | TWEET_STUDY_PATH = os.path.join(BASE, "..", "data", "tweet_study", "raw_tweets.json")
  19 | DAILY_TWEETS_PATH = os.path.join(BASE, "data", "daily_tweets.json")
  20 | 
  21 | 
  22 | def get_todays_social_posts(max_posts=5):
  23 |     """Get real tweet data for the social segment.
  24 | 
  25 |     Returns:
  26 |         List of dicts with keys: handle, text, likes, retweets, source
  27 |         Empty list if no real data available (Law A1).
  28 |     """
  29 |     # Priority 1: Operator-curated daily tweets
  30 |     if os.path.exists(DAILY_TWEETS_PATH):
  31 |         try:
  32 |             with open(DAILY_TWEETS_PATH) as f:
  33 |                 data = json.load(f)
  34 |             posts = data.get("tweets", data if isinstance(data, list) else [])
  35 |             if posts:
  36 |                 # Dedup by handle FIRST, then truncate to max_posts
  37 |                 seen_handles = set()
  38 |                 deduped = []
  39 |                 for p in posts:
  40 |                     h = p.get('handle', '').lower().strip('@')
  41 |                     if h and h not in seen_handles:
  42 |                         seen_handles.add(h)
  43 |                         deduped.append(p)
  44 |                 deduped = deduped[:max_posts]
  45 |                 logger.info(f"Social: {len(deduped)} curated tweets loaded")
  46 |                 return deduped
  47 |         except Exception as e:
  48 |             logger.warning(f"Error reading daily_tweets.json: {e}")
  49 | 
  50 |     # Priority 2: Raw study data — highest engagement tweets
  51 |     if os.path.exists(TWEET_STUDY_PATH):
  52 |         try:
  53 |             with open(TWEET_STUDY_PATH) as f:
  54 |                 raw = json.load(f)
  55 |             from datetime import datetime, timezone, timedelta
  56 |             now_utc = datetime.now(timezone.utc)
  57 |             def _sort_key(t):
  58 |                 raw_ts = t.get('created_at', '')
  59 |                 try:
  60 |                     ts = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
  61 |                     age_h = (now_utc - ts).total_seconds() / 3600
  62 |                 except Exception:
  63 |                     age_h = 9999
  64 |                 er = t.get('engagement_rate', 0) or 0
  65 |                 likes = t.get('likes', 0) or 0
  66 |                 recency = 10.0 if age_h < 24 else (1.0 if age_h < 168 else 0.0)
  67 |                 return recency + er + (likes / 100000.0)
  68 |             tweets = sorted(raw, key=_sort_key, reverse=True)
  69 | 
  70 |             # Prefer recent tweets (last 7 days) if available
  71 |             cutoff = datetime.utcnow() - timedelta(days=7)
  72 |             recent = []
  73 |             for t in tweets:
  74 |                 try:
  75 |                     created = datetime.fromisoformat(
  76 |                         t.get("created_at", "").replace("Z", "+00:00")
  77 |                     )
  78 |                     if created.replace(tzinfo=None) > cutoff:
  79 |                         recent.append(t)
  80 |                 except (ValueError, TypeError):
  81 |                     continue
  82 | 
  83 |             # DIVERSITY FIX: max 1 tweet per handle, varied accounts
  84 |             pool = recent if recent else tweets
  85 |             seen_h = set()
  86 |             deduped_pool = []
  87 |             for t in pool:
  88 |                 h = t.get('handle', '').lower().strip('@')
  89 |                 if h and h not in seen_h:
  90 |                     seen_h.add(h)
  91 |                     deduped_pool.append(t)
  92 |             source = deduped_pool[:max_posts]
  93 |             posts = [
  94 |                 {
  95 |                     "handle": t.get("handle", "unknown"),
  96 |                     "text": t.get("text", "")[:280],
  97 |                     "likes": t.get("likes", t.get("like_count", 0)),
  98 |                     "retweets": t.get("retweets", t.get("retweet_count", 0)),
  99 |                     "source": "raw_study",
 100 |                 }
 101 |                 for t in source
 102 |             ]
 103 |             if posts:
 104 |                 logger.info(f"Social: {len(posts)} tweets from raw study data")
 105 |                 return posts
 106 |         except Exception as e:
 107 |             logger.warning(f"Error reading raw_tweets.json: {e}")
 108 | 
 109 |     # No real data — return empty per Law A1
 110 |     logger.warning("Social: No real tweet data available. Segment will be skipped.")
 111 |     return []
 112 | 
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
